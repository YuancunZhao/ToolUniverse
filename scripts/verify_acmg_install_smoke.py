#!/usr/bin/env python3
"""Post-install ACMG smoke test: verify the INSTALLED package, not the source tree.

Builds an isolated install from either the local project or an exact Git ref
into a temporary directory, then runs the same offline behavior checks against
that installed copy in a subprocess whose ``tooluniverse`` resolves to the
installed files:

- collector entry point and backward-compatible alias are discoverable;
- the five evidence group tools are discoverable and their Python wrapper
  parameters are covered by the installed JSON schemas;
- ``ACMG_guard_final_answer`` blocks five-tier labels;
- the PMM2 rs104894531 multi-allele regression input fails closed with an
  explicit ambiguity reason and zero downstream evidence calls (offline
  fixture executor, no network);
- the installed runtime version, tool registry, and packaged data files are
  consistent with the source tree release.

The default local-source mode is offline. Git-ref mode uses the network only to
install the explicitly requested repository revision; behavior checks remain
offline and never use a provider fallback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS_PROGRAM = r'''
import hashlib
import inspect
from importlib import metadata
import json
import sys
from pathlib import Path

install_dir = sys.argv[1]
expected_version = sys.argv[2]
expected_commit = sys.argv[3]
expected_schema_hash = sys.argv[4]
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


import tooluniverse

check(
    "installed_package_resolved",
    tooluniverse.__file__.startswith(install_dir),
    tooluniverse.__file__,
)
check(
    "version_consistent",
    tooluniverse.__version__ == expected_version,
    f"installed={tooluniverse.__version__} expected={expected_version}",
)
distribution = metadata.distribution("tooluniverse")
direct_url_text = distribution.read_text("direct_url.json") or ""
try:
    direct_url = json.loads(direct_url_text) if direct_url_text else {}
except json.JSONDecodeError:
    direct_url = {}
installed_commit = str((direct_url.get("vcs_info") or {}).get("commit_id") or "")
check(
    "vcs_commit_consistent",
    not expected_commit or installed_commit == expected_commit,
    f"installed={installed_commit or '<missing>'} expected={expected_commit}",
)

from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()
names = {tool.get("name") for tool in tu.all_tools}
expected_tools = {
    "ACMG_evidence_collector",
    "ACMG_overlay_gate_assess_variant",
    "ACMG_population_evidence",
    "ACMG_computational_evidence",
    "ACMG_clinical_evidence",
    "ACMG_functional_evidence",
    "ACMG_literature_evidence",
    "ACMG_guard_final_answer",
}
check(
    "eight_acmg_tools_discoverable",
    expected_tools <= names,
    "missing: " + ",".join(sorted(expected_tools - names)),
)

data_path = Path(tooluniverse.__file__).parent / "data" / "acmg_overlay_gate_tools.json"
configs = json.loads(data_path.read_text())
by_name = {row["name"]: row for row in configs}
check("config_has_eight_tools", len(configs) == 8, f"count={len(configs)}")
schema_hash = hashlib.sha256(
    json.dumps(configs, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
check(
    "schema_fingerprint_consistent",
    schema_hash == expected_schema_hash,
    f"installed={schema_hash} expected={expected_schema_hash}",
)

from tooluniverse import tools as tool_wrappers

ignored = {"stream_callback", "use_cache", "validate"}
schema_gaps = []
for name in (
    "ACMG_population_evidence",
    "ACMG_computational_evidence",
    "ACMG_clinical_evidence",
    "ACMG_functional_evidence",
    "ACMG_literature_evidence",
):
    wrapper = getattr(tool_wrappers, name)
    params = set(inspect.signature(wrapper).parameters) - ignored
    schema_params = set(by_name[name]["parameter"]["properties"])
    if not params <= schema_params:
        schema_gaps.append(f"{name}:{sorted(params - schema_params)}")
check("group_wrapper_schema_consistent", not schema_gaps, ";".join(schema_gaps))

collector_required = set(by_name["ACMG_evidence_collector"]["return_schema"]["required"])
alias_required = set(
    by_name["ACMG_overlay_gate_assess_variant"]["return_schema"]["required"]
)
check(
    "collector_alias_return_fields_converged",
    collector_required == alias_required
    and "consequence_profile" in collector_required,
    "",
)
collector_parameters = set(
    by_name["ACMG_evidence_collector"]["parameter"]["properties"]
)
alias_parameters = set(
    by_name["ACMG_overlay_gate_assess_variant"]["parameter"]["properties"]
)
removed_inputs = {"literature_facts", "spliceai_dl", "mode"}
removed_outputs = {
    "counted",
    "included_in_candidate_bayesian",
    "counted_criteria",
    "bayesian_estimate",
}
check(
    "collector_alias_parameter_fields_converged",
    collector_parameters == alias_parameters,
    "",
)
check(
    "removed_input_fields_absent",
    not (removed_inputs & (collector_parameters | alias_parameters)),
    ",".join(sorted(removed_inputs & (collector_parameters | alias_parameters))),
)
collector_outputs = set(
    by_name["ACMG_evidence_collector"]["return_schema"]["properties"]
)
alias_outputs = set(
    by_name["ACMG_overlay_gate_assess_variant"]["return_schema"]["properties"]
)
check(
    "removed_output_fields_absent",
    not (removed_outputs & (collector_outputs | alias_outputs)),
    ",".join(sorted(removed_outputs & (collector_outputs | alias_outputs))),
)
check(
    "runtime_manifest_declared",
    "runtime_manifest" in collector_required
    and "runtime_manifest" in alias_required,
    "",
)

from tooluniverse.acmg.guard import guard_context_hash
from tooluniverse.acmg.runtime_manifest import ruleset_hash

guard_context = {
    "schema_version": "2026-08-07",
    "variant_identity_hash": "a" * 64,
    "ruleset_hash": ruleset_hash(),
    "cards": [],
    "known_source_fact_ids": [],
    "trusted_source_fact_ids": [],
}
guard_context["context_hash"] = guard_context_hash(guard_context)
guard = tu.run_one_function(
    {
        "name": "ACMG_guard_final_answer",
        "arguments": {
            "final_answer_text": "This variant is classified as Pathogenic.",
            "guard_context": guard_context,
        },
    }
)
check("guard_blocks_five_tier_label", guard.get("status") == "BLOCK", guard.get("status"))

tampered_context = {**guard_context, "ruleset_hash": "c" * 64}
tampered = tu.run_one_function(
    {
        "name": "ACMG_guard_final_answer",
        "arguments": {
            "final_answer_text": "PP3 is a candidate.",
            "guard_context": tampered_context,
        },
    }
)
check(
    "guard_context_tampering_fails_closed",
    tampered.get("blocking_reasons") == ["guard_context_invalid"],
    tampered.get("blocking_reasons"),
)

# --- PMM2 rs104894531 multi-allele regression, offline fixture executor ---
from tooluniverse.acmg.collector import ACMGEvidencePipeline


class _MultiAlleleFixture:
    def __init__(self):
        self.calls = []

    def run_one_function(self, call, **kwargs):
        self.calls.append(call["name"])
        name = call["name"]
        if name == "EnsemblVEP_variant_recoder":
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "rsid": "rs104894531",
                        "provider_version": "Ensembl Variant Recoder REST",
                        "hgvs_c": "NM_000303.3:c.669C>T",
                        "hgvs_g": "NC_000016.10:g.8847753C>T",
                        "hgvsc_candidates": [
                            "NM_000303.3:c.669C>T",
                            "NM_000303.3:c.669C>G",
                        ],
                        "allele_candidates": [
                            {
                                "hgvsg": ["NC_000016.10:g.8847753C>T"],
                                "hgvsc": ["NM_000303.3:c.669C>T"],
                                "hgvsp": [],
                            },
                            {
                                "hgvsg": ["NC_000016.10:g.8847753C>G"],
                                "hgvsc": ["NM_000303.3:c.669C>G"],
                                "hgvsp": [],
                            },
                        ],
                    }
                },
            }
        if name == "VariantValidator_gene2transcripts":
            return [
                {
                    "current_symbol": "PMM2",
                    "transcripts": [
                        {
                            "reference": "NM_000303.3",
                            "annotations": {"mane_select": True},
                        }
                    ],
                }
            ]
        return {"status": "unavailable", "reason": "offline fixture"}


fixture = _MultiAlleleFixture()
pipeline = ACMGEvidencePipeline(fixture)
_, identity = pipeline._identity("rs104894531", "PMM2", "", "GRCh38")
check(
    "pmm2_multi_allele_fails_closed",
    identity.get("identity_verified") is False
    and identity.get("identity_error") == "ambiguous_rsid_allele",
    identity.get("identity_error"),
)
normalization = identity.get("normalization", {})
check(
    "pmm2_alternatives_preserved",
    normalization.get("allele_alternatives")
    == ["NM_000303.3:c.669C>T", "NM_000303.3:c.669C>G"]
    and bool(normalization.get("resolution_reason")),
    json.dumps(normalization.get("allele_alternatives")),
)
evidence_source_tools = {
    "ClinVar_search_variants",
    "ClinVar_get_clinical_significance",
    "gnomad_get_variant",
    "gnomad_get_variant_populations",
    "gnomad_get_site_callability",
    "SpliceAI_predict_splice",
    "MyVariant_get_pathogenicity_scores",
    "LitVar_search_variants",
    "EuropePMC_search_articles",
}
called = set(fixture.calls)
check(
    "pmm2_zero_downstream_calls",
    not (called & evidence_source_tools)
    and called
    <= {
        "NCBIVariation_rsid_lookup",
        "EnsemblVEP_variant_recoder",
        "VariantValidator_gene2transcripts",
        "VariantValidator_format_genomic_to_transcripts",
    },
    ",".join(fixture.calls),
)

failed = [row for row in results if not row[1]]
for name, ok, detail in results:
    mark = "PASS" if ok else "FAIL"
    suffix = f" ({detail})" if detail and not ok else ""
    print(f"{mark}: {name}{suffix}")
if failed:
    sys.exit(1)
print(
    "PROVENANCE: "
    + json.dumps(
        {
            "package_path": tooluniverse.__file__,
            "package_version": tooluniverse.__version__,
            "distribution_vcs_commit": installed_commit,
            "schema_fingerprint": schema_hash,
        },
        sort_keys=True,
    )
)
print("SMOKE OK")
'''


def _expected_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else ""


def _expected_schema_hash() -> str:
    data_path = ROOT / "src" / "tooluniverse" / "data" / "acmg_overlay_gate_tools.json"
    configs = json.loads(data_path.read_text(encoding="utf-8"))
    canonical = json.dumps(
        configs,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=("local", "git-ref"),
        default="local",
        help="Install the current checkout or an explicit Git revision.",
    )
    parser.add_argument(
        "--git-ref",
        help="Exact commit SHA or other immutable Git ref (required for git-ref).",
    )
    parser.add_argument(
        "--repo-url",
        default="https://github.com/YuancunZhao/ToolUniverse.git",
        help="Repository URL used by git-ref mode.",
    )
    parser.add_argument(
        "--expected-version",
        default="",
        help="Expected installed version; defaults to this checkout's pyproject.",
    )
    args = parser.parse_args()
    if args.source == "git-ref" and not args.git_ref:
        parser.error("--git-ref is required when --source=git-ref")
    if args.source == "git-ref" and not re.fullmatch(r"[0-9a-fA-F]{40}", args.git_ref):
        parser.error("--git-ref must be a full 40-character commit SHA")
    return args


def main() -> int:
    args = _parse_args()
    expected = args.expected_version or _expected_version()
    install_source = (
        str(ROOT)
        if args.source == "local"
        else f"git+{args.repo_url}@{args.git_ref}"
    )
    with tempfile.TemporaryDirectory(prefix="acmg_smoke_") as tmp:
        install_dir = str(Path(tmp) / "install")
        build = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                install_source,
                "--no-deps",
                "--no-build-isolation",
                "--no-cache-dir",
                "--target",
                install_dir,
                "-q",
            ],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        if build.returncode != 0:
            print("FAIL: isolated install failed")
            print(build.stdout[-2000:])
            print(build.stderr[-2000:])
            return 1
        env = {
            **os.environ,
            "PYTHONPATH": install_dir,
            "PYTHONNOUSERSITE": "1",
            "TOOLUNIVERSE_CACHE_DIR": str(Path(tmp) / "cache"),
            "TOOLUNIVERSE_CACHE_PERSIST": "false",
        }
        run = subprocess.run(
            [
                sys.executable,
                "-c",
                CHECKS_PROGRAM,
                install_dir,
                expected,
                args.git_ref or "",
                _expected_schema_hash(),
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=tmp,
        )
        sys.stdout.write(run.stdout)
        if run.returncode != 0 and run.stderr:
            sys.stderr.write(run.stderr[-3000:])
        return run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
