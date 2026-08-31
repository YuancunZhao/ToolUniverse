#!/usr/bin/env python3
"""Post-install ACMG smoke test: verify the INSTALLED package, not the source tree.

Builds an isolated install from either the local project or an exact Git ref
into a temporary directory, then runs the same offline behavior checks against
that installed copy in a subprocess whose ``tooluniverse`` resolves to the
installed files:

- all eight public ACMG tools, including the thin overlay alias, are discoverable;
- the five evidence group tools are discoverable and their Python wrapper
  parameters are covered by the installed JSON schemas;
- ``ACMG_guard_final_answer`` blocks five-tier labels;
- the PMM2 rs104894531 multi-allele regression input fails closed with an
  explicit ambiguity reason and zero downstream evidence-provider calls (offline
  fixture executor, no network);
- the installed runtime version, tool registry, and packaged data files are
  consistent with the source tree release.

The default local-source mode is offline. Git-ref mode uses the network only to
install the explicitly requested repository revision; behavior checks remain
offline unless ``--online-providers`` is supplied. The optional online gate
retries each required provider once and validates stable identity/shape
contracts rather than mutable scores or result counts.
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

CHECKS_PROGRAM = r"""
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
    "ACMG_population_evidence",
    "ACMG_computational_evidence",
    "ACMG_clinical_evidence",
    "ACMG_functional_evidence",
    "ACMG_literature_evidence",
    "ACMG_guard_final_answer",
    "ACMG_overlay_gate_assess_variant",
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
    "ACMG_evidence_collector",
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
check(
    "collector_return_fields_declared",
    "consequence_profile" in collector_required,
    "",
)
collector_parameters = set(
    by_name["ACMG_evidence_collector"]["parameter"]["properties"]
)
removed_inputs = {"literature_facts", "spliceai_dl", "mode"}
removed_outputs = {
    "counted",
    "included_in_candidate_bayesian",
    "counted_criteria",
    "bayesian_estimate",
    "system_preview_bayesian",
    "validated_subset_bayesian",
}
check(
    "removed_input_fields_absent",
    not (removed_inputs & collector_parameters),
    ",".join(sorted(removed_inputs & collector_parameters)),
)
collector_outputs = set(
    by_name["ACMG_evidence_collector"]["return_schema"]["properties"]
)
check(
    "removed_output_fields_absent",
    not (removed_outputs & collector_outputs),
    ",".join(sorted(removed_outputs & collector_outputs)),
)
check(
    "runtime_manifest_declared",
    "runtime_manifest" in collector_required,
    "",
)
v3_outputs = {
    "vcep_context",
    "vcep_assertions",
    "rule_scenarios",
    "automatic_bayesian",
    "verified_bayesian",
    "user_selected_bayesian",
    "scenario_estimates",
    "automation_report",
}
check(
    "v3_output_contract_declared",
    v3_outputs <= collector_outputs,
    "missing: " + ",".join(sorted(v3_outputs - collector_outputs)),
)
check(
    "clinical_observations_declared",
    "clinical_observations" in collector_parameters,
    "",
)

from tooluniverse.acmg.guard import GUARD_CONTEXT_SCHEMA_VERSION, guard_context_hash
from tooluniverse.acmg.runtime_manifest import ACMG_RUNTIME_VERSION, ruleset_hash

check(
    "v4_runtime_version",
    ACMG_RUNTIME_VERSION == "evidence-automation-4.2",
    ACMG_RUNTIME_VERSION,
)

guard_context = {
    "schema_version": GUARD_CONTEXT_SCHEMA_VERSION,
    "variant_identity_hash": "a" * 64,
    "ruleset_hash": ruleset_hash(),
    "claims": [],
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
    "pmm2_no_evidence_provider_calls",
    not (called & evidence_source_tools)
    and called
    <= {
        "HGNC_fetch_gene_by_symbol",
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
"""

ONLINE_CHECKS_PROGRAM = r"""
import json
import sys
import time

install_dir = sys.argv[1]
report = []


def _urls(value):
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in {"url", "source_url", "request_url"} and isinstance(item, str):
                if item.startswith(("http://", "https://")):
                    found.add(item)
            found.update(_urls(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_urls(item))
    return sorted(found)


def _nonempty(value):
    return value not in (None, "", [], {})


def _walk_key_values(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            current = f"{path}.{key}" if path else str(key)
            yield current, item
            yield from _walk_key_values(item, current)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_key_values(item, f"{path}[{index}]")


def _run_check(name, tool_name, arguments, validator):
    attempts = []
    final_result = None
    final_detail = ""
    for attempt in range(1, 3):
        started = time.monotonic()
        try:
            result = tu.run_one_function(
                {"name": tool_name, "arguments": arguments},
                use_cache=False,
            )
            ok, detail = validator(result)
            error = ""
            if isinstance(result, dict):
                error = str(result.get("error") or result.get("reason") or "")
            attempts.append(
                {
                    "attempt": attempt,
                    "status": "pass" if ok else "fail",
                    "provider_status": result.get("status") if isinstance(result, dict) else None,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "urls": _urls(result),
                    "detail": detail,
                    "error": error[:500],
                }
            )
            final_result = result
            final_detail = detail
            if ok:
                report.append({"name": name, "status": "pass", "attempts": attempts})
                print(f"PASS: online_{name}")
                return True, result
        except Exception as exc:
            attempts.append(
                {
                    "attempt": attempt,
                    "status": "error",
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "urls": [],
                    "detail": "provider call raised",
                    "error": f"{type(exc).__name__}: {exc}"[:500],
                }
            )
            final_detail = str(exc)
        if attempt == 1:
            time.sleep(1)
    report.append(
        {
            "name": name,
            "status": "fail",
            "attempts": attempts,
            "final_detail": final_detail,
        }
    )
    print(f"FAIL: online_{name} ({final_detail})")
    return False, final_result


def _validate_cspec(result):
    if not isinstance(result, dict) or result.get("status") != "success":
        return False, "provider did not return success"
    rows = result.get("data") or []
    valid = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("gene") or "").upper() == "BRCA2"
        and str(row.get("status") or "").casefold() == "released"
        and _nonempty(row.get("specification_id"))
        and _nonempty(row.get("version"))
        and str(row.get("url") or "").startswith("http")
        and bool(row.get("criterion_modifications"))
    ]
    return bool(valid), f"released_structured_records={len(valid)}"


def _validate_erepo(result):
    if not isinstance(result, dict) or result.get("status") != "success":
        return False, "provider did not return success"
    rows = result.get("data") or []
    exact = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("CAID") or "").upper().removeprefix("CAR:") == "CA114360"
        and str(row.get("Status") or "released").casefold() == "released"
    ]
    structured = [row for row in exact if bool(row.get("Applied Criteria"))]
    return bool(structured), f"exact={len(exact)} structured={len(structured)}"


def _validate_clinvar(result):
    if not isinstance(result, dict) or result.get("status") != "success":
        return False, "provider did not return success"
    data = result.get("data") or {}
    params = data.get("search_params") or {}
    ids = data.get("variant_ids") or []
    variants = data.get("variants") or []
    returned_text = json.dumps(variants, ensure_ascii=False).upper().replace(" ", "")
    gene_ok = str(params.get("gene") or "").upper() == "HBB" and "HBB" in returned_text
    variant_ok = "C.20A>T" in returned_text or "P.GLU7VAL" in returned_text
    return bool(ids and gene_ok and variant_ok), f"ids={len(ids)} gene={gene_ok} variant={variant_ok}"


def _validate_gnomad(result):
    if not isinstance(result, dict):
        return False, "provider result is not an object"
    variant = result.get("variant") or (result.get("data") or {}).get("variant") or {}
    allele_ok = (
        str(variant.get("variant_id") or "") == "19-44908822-C-T"
        and str(variant.get("chrom") or "") == "19"
        and int(variant.get("pos") or 0) == 44908822
        and str(variant.get("ref") or "").upper() == "C"
        and str(variant.get("alt") or "").upper() == "T"
    )
    callsets = [value for value in (variant.get("genome"), variant.get("exome")) if isinstance(value, dict)]
    frequency_ok = any(all(key in callset for key in ("ac", "an", "af")) for callset in callsets)
    return allele_ok and frequency_ok, f"allele={allele_ok} frequency_shape={frequency_ok}"


def _validate_myvariant(result):
    if not isinstance(result, dict) or not isinstance(result.get("data"), dict):
        return False, "provider did not return data object"
    data = result["data"]
    dbnsfp_present = any(path.casefold().endswith("dbnsfp") for path, _ in _walk_key_values(data))
    predictor_tokens = (
        "revel",
        "cadd",
        "alphamissense",
        "sift",
        "polyphen",
        "metarnn",
        "vest4",
        "mutationtaster",
    )
    predictor_values = [
        path
        for path, value in _walk_key_values(data)
        if any(token in path.casefold() for token in predictor_tokens) and _nonempty(value)
    ]
    return dbnsfp_present and bool(predictor_values), f"predictor_values={len(predictor_values)}"


def _validate_full_text(result):
    if not isinstance(result, dict) or result.get("status") != "success":
        return False, "provider did not return success"
    data = result.get("data") or {}
    text_values = [
        value
        for path, value in _walk_key_values(data)
        if isinstance(value, str)
        and any(token in path.casefold() for token in ("title", "abstract", "section", "text"))
    ]
    provenance_ok = (
        _nonempty(result.get("source"))
        and _nonempty(result.get("format"))
        and str(result.get("url") or "").startswith("http")
        and bool(result.get("retrieval_trace"))
    )
    return bool("".join(text_values).strip()) and provenance_ok, (
        f"text_chars={sum(len(value) for value in text_values)} provenance={provenance_ok}"
    )


def _validate_collector(result):
    if not isinstance(result, dict):
        return False, "collector result is not an object"
    facts = result.get("source_facts") or []
    coverage = (
        result.get("coverage_summary")
        or result.get("coverage")
        or result.get("source_manifest")
        or {}
    )
    contract_ok = (
        result.get("status") in {"success", "degraded"}
        and result.get("final_classification_allowed") is False
        and isinstance(facts, list)
        and bool(facts)
        and bool(coverage)
        and "automatic_bayesian" in result
        and "verified_bayesian" in result
    )
    failures_visible = any(
        isinstance(fact, dict)
        and (
            fact.get("source_status") in {"failed", "unavailable"}
            or fact.get("status") in {"failed", "unavailable", "error"}
            or bool(fact.get("limitations"))
        )
        for fact in facts
    ) or bool(result.get("limitations"))
    return contract_ok and failures_visible, (
        f"status={result.get('status')} contract={contract_ok} "
        f"facts={len(facts)} failures_visible={failures_visible}"
    )


from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()
checks = [
    ("cspec", "ClinGen_search_cspec", {"gene": "BRCA2"}, _validate_cspec),
    (
        "erepo",
        "ClinGen_get_variant_classifications",
        {"variant": "CA114360"},
        _validate_erepo,
    ),
    (
        "clinvar",
        "ClinVar_search_variants",
        {"gene": "HBB", "variant_name": "NM_000518.5:c.20A>T", "max_results": 20},
        _validate_clinvar,
    ),
    (
        "gnomad",
        "gnomad_get_variant",
        {"variant_id": "19-44908822-C-T", "dataset": "gnomad_r3"},
        _validate_gnomad,
    ),
    (
        "myvariant",
        "MyVariant_get_pathogenicity_scores",
        {"variant_id": "rs45478192"},
        _validate_myvariant,
    ),
    (
        "europe_pmc",
        "EuropePMC_get_full_text",
        {"pmcid": "PMC7096075", "max_section_chars": 500000},
        _validate_full_text,
    ),
    (
        "collector",
        "ACMG_evidence_collector",
        {
            "variant": "NM_000059.4:c.5946delT",
            "gene": "BRCA2",
            "transcript": "NM_000059.4",
            "genome_build": "GRCh38",
            "response_detail": "summary",
        },
        _validate_collector,
    ),
]
all_ok = True
for item in checks:
    ok, _ = _run_check(*item)
    all_ok = all_ok and ok

print("ONLINE_PROVIDER_REPORT: " + json.dumps(report, ensure_ascii=False, sort_keys=True))
if not all_ok:
    sys.exit(1)
print("ONLINE PROVIDER SMOKE OK")
"""


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
    parser.add_argument(
        "--online-providers",
        action="store_true",
        help=(
            "After offline checks, call the required live ACMG providers and "
            "collector. Each check is attempted at most twice."
        ),
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
        str(ROOT) if args.source == "local" else f"git+{args.repo_url}@{args.git_ref}"
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
        if run.returncode != 0:
            if run.stderr:
                sys.stderr.write(run.stderr[-3000:])
            return run.returncode
        if not args.online_providers:
            return 0
        online = subprocess.run(
            [sys.executable, "-c", ONLINE_CHECKS_PROGRAM, install_dir],
            capture_output=True,
            text=True,
            env=env,
            cwd=tmp,
        )
        sys.stdout.write(online.stdout)
        if online.returncode != 0 and online.stderr:
            sys.stderr.write(online.stderr[-3000:])
        return online.returncode


if __name__ == "__main__":
    raise SystemExit(main())
