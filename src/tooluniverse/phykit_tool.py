"""PhyKIT phylogenetics analysis tool.

Wraps PhyKIT command-line functions (treeness, saturation, dvmc,
long_branch_score, total_tree_length, parsimony_informative) for
single files or batch processing on directories.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool


# Some user-facing metric names don't match phykit's CLI subcommand names.
# `parsimony_informative` is the canonical scientific name but phykit exposes
# it as `parsimony_informative_sites` (alias `pis`). Calling the wrong name
# returns the help banner with non-zero exit, silently producing zero values.
PHYKIT_CLI_ALIAS = {
    "parsimony_informative": "parsimony_informative_sites",
    # BixBench asks for "treeness/RCV", which is a distinct phykit function from
    # plain `treeness` and was not exposed at all.
    "treeness_over_rcv": "treeness_over_rcv",
    "toverr": "treeness_over_rcv",
}


# `saturation` takes its alignment through -a, not positionally:
#   phykit saturation -a <alignment> -t <tree>
# Passing it positionally makes phykit exit 2 with
# "the following arguments are required: -a/--alignment", so the function could
# never run. Functions not listed here take the file positionally as before.
PHYKIT_ALIGNMENT_FLAG = {"saturation", "treeness_over_rcv"}


def _run_phykit(
    function: str, filepath: str, extra_args: list = None
) -> "tuple[str | None, str]":
    """Run one phykit command; return (stdout, error_reason).

    The reason is returned rather than swallowed: every failure used to collapse to
    None, so a wrong flag or an unreadable file both surfaced as "no values
    computed" with nothing to act on.
    """
    cli = PHYKIT_CLI_ALIAS.get(function, function)
    if function in PHYKIT_ALIGNMENT_FLAG:
        cmd = ["phykit", cli, "-a", filepath]
    else:
        cmd = ["phykit", cli, filepath]
    if extra_args:
        cmd.extend(extra_args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return r.stdout.strip(), ""
        detail = (r.stderr or r.stdout or "").strip().splitlines()
        return None, (detail[0][:200] if detail else f"exit {r.returncode}")
    except subprocess.TimeoutExpired:
        return None, "phykit timed out after 120s"
    except FileNotFoundError:
        return None, "phykit executable not found on PATH"


@register_tool("PhyKITTool")
class PhyKITTool(BaseTool):
    """Run PhyKIT phylogenetics functions on tree/alignment files."""

    SUPPORTED_FUNCTIONS = [
        "treeness",
        "saturation",
        "dvmc",
        "long_branch_score",
        "total_tree_length",
        "parsimony_informative",
    ]

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", "batch")
        function = arguments.get("function", "")
        if function not in self.SUPPORTED_FUNCTIONS:
            return {
                "status": "error",
                "error": f"Unsupported function: {function}. Use one of {self.SUPPORTED_FUNCTIONS}",
            }

        if operation == "single":
            return self._run_single(arguments)
        elif operation == "batch":
            return self._run_batch(arguments)
        elif operation == "gap_percentage":
            return self._gap_percentage(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _run_single(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run PhyKIT on a single file."""
        function = arguments["function"]
        filepath = arguments.get("file", "")
        if not filepath or not os.path.exists(filepath):
            return {"status": "error", "error": f"File not found: {filepath}"}

        extra = []
        if function == "saturation":
            tree_file = arguments.get("tree_file", "")
            if tree_file:
                extra = ["-t", tree_file]

        output, reason = _run_phykit(function, filepath, extra)
        if output is None:
            return {
                "status": "error",
                "error": f"PhyKIT {function} failed on {filepath}: {reason}",
            }

        return {
            "status": "success",
            "data": {"function": function, "file": filepath, "output": output},
        }

    def _run_batch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run PhyKIT on all files in a directory."""
        function = arguments["function"]
        directory = arguments.get("directory", "")
        ext = arguments.get("extension", ".treefile")
        tree_dir = arguments.get("tree_directory", "")
        tree_ext = arguments.get("tree_extension", ".treefile")
        per_tree_stat = arguments.get("per_tree_stat", "mean")

        if not directory or not os.path.isdir(directory):
            return {"status": "error", "error": f"Directory not found: {directory}"}

        files = sorted(Path(directory).glob(f"*{ext}"))
        if not files:
            return {
                "status": "error",
                "error": f"No files matching *{ext} in {directory}",
            }

        values: List[float] = []
        processed = 0
        errors = 0
        first_error = ""

        for f in files:
            extra = []
            if function == "saturation" and tree_dir:
                # Path.stem drops only the LAST suffix, but these files carry
                # multi-part extensions (foo.faa.mafft.clipkit). Using .stem built
                # foo.faa.mafft + .faa.mafft.clipkit.treefile, which never exists,
                # so every file was skipped silently and the batch reported
                # "0 files (0 errors)". Strip the caller's own extension instead.
                base = f.name[: -len(ext)] if ext and f.name.endswith(ext) else f.stem
                tree_path = str(Path(tree_dir) / f"{base}{tree_ext}")
                if not os.path.exists(tree_path):
                    errors += 1
                    if not first_error:
                        first_error = f"{f.name}: no matching tree at {tree_path}"
                    continue
                extra = ["-t", tree_path]

            output, reason = _run_phykit(function, str(f), extra)
            if output is None:
                errors += 1
                if not first_error:
                    first_error = f"{f.name}: {reason}"
                continue

            processed += 1

            if function == "long_branch_score":
                lines = [ln for ln in output.split("\n") if ln.strip()]
                taxon_values = []
                for line in lines:
                    parts = line.split("\t")
                    try:
                        taxon_values.append(float(parts[-1]))
                    except (ValueError, IndexError):
                        pass
                if not taxon_values:
                    continue
                if per_tree_stat == "mean":
                    values.append(sum(taxon_values) / len(taxon_values))
                elif per_tree_stat == "median":
                    taxon_values.sort()
                    n = len(taxon_values)
                    values.append(
                        taxon_values[n // 2]
                        if n % 2
                        else (taxon_values[n // 2 - 1] + taxon_values[n // 2]) / 2
                    )
                else:
                    values.extend(taxon_values)
            else:
                try:
                    parts = output.split("\n")[0].split("\t")
                    # Saturation outputs slope<TAB>1-slope; use 1-slope (col 1)
                    if function == "saturation" and len(parts) >= 2:
                        val = float(parts[1])
                    elif function in ("treeness_over_rcv", "toverr") and parts:
                        # phykit toverr prints: treeness/RCV <TAB> treeness <TAB> RCV.
                        # The question asks for treeness/RCV, i.e. column 1.
                        val = float(parts[0])
                    elif function == "parsimony_informative" and len(parts) >= 3:
                        # phykit pis output: n_pi <TAB> n_total <TAB> percent.
                        # The "%PIS" column (col 3) is what scientific
                        # questions ask for, not the raw count.
                        val = float(parts[2])
                    else:
                        val = float(parts[0])
                    values.append(val)
                except (ValueError, IndexError):
                    errors += 1

        if not values:
            return {
                "status": "error",
                "error": (
                    f"No values computed from {processed} files ({errors} errors)"
                    + (f". First failure -- {first_error}" if first_error else "")
                    + (f". No files matched '*{ext}' in {directory}" if not processed and not errors else "")
                ),
            }

        values.sort()
        n = len(values)
        mean_val = sum(values) / n
        median_val = (
            values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2
        )

        return {
            "status": "success",
            "data": {
                "function": function,
                "n_files": processed,
                "n_errors": errors,
                "n_values": n,
                "mean": round(mean_val, 6),
                "median": round(median_val, 6),
                "min": round(min(values), 6),
                "max": round(max(values), 6),
                "values": [round(v, 6) for v in values] if n <= 50 else None,
            },
        }

    def _gap_percentage(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Compute gap percentage across all alignments in a directory."""
        directory = arguments.get("directory", "")
        ext = arguments.get("extension", ".fa")

        if not directory or not os.path.isdir(directory):
            return {"status": "error", "error": f"Directory not found: {directory}"}

        total_gaps = 0
        total_positions = 0
        files_processed = 0

        for f in sorted(Path(directory).glob(f"*{ext}")):
            with open(f) as fh:
                seqs: List[str] = []
                current: List[str] = []
                for line in fh:
                    line = line.strip()
                    if line.startswith(">"):
                        if current:
                            seqs.append("".join(current))
                        current = []
                    else:
                        current.append(line)
                if current:
                    seqs.append("".join(current))

            for seq in seqs:
                total_positions += len(seq)
                total_gaps += seq.count("-")
            files_processed += 1

        if total_positions == 0:
            return {"status": "error", "error": "No alignment data found"}

        pct = total_gaps / total_positions * 100

        return {
            "status": "success",
            "data": {
                "total_gaps": total_gaps,
                "total_positions": total_positions,
                "gap_percentage": round(pct, 2),
                "files_processed": files_processed,
            },
        }
