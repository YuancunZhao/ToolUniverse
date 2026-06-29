#!/usr/bin/env python3
"""Check entrypoint transcripts for ACMG overlay-gate bypass patterns.

This is a prompt/entrypoint regression check, not a medical validator. It
detects final-classification wording that appears without a machine-checkable
assessment bundle and validator PASS summary, plus static skill-routing text
that points final ACMG/pathogenicity work at non-gate entrypoints.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


PASS = "PASS"
FAIL = "FAIL"

FULL_FINAL_LABEL_RE = re.compile(
    r"\b("
    r"Likely\s+Pathogenic|Likely\s+Benign|"
    r"Pathogenic|Benign|VUS|"
    r"Variants?\s+of\s+(?:Uncertain|Unknown)\s+Significance|"
    r"Uncertain\s+Significance"
    r")\b",
    re.IGNORECASE,
)
PAIRED_ABBREVIATION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:P\s*/\s*LP|LP\s*/\s*P|LB\s*/\s*B|B\s*/\s*LB)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
STANDALONE_ABBREVIATION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:LP|LB|VUS)(?![A-Za-z0-9])"
    r"(?!(?:\s+(?:score|value|cell|phenotype|domain|gene|frequency|population|protein))\b)",
    re.IGNORECASE,
)
CONTEXTUAL_SINGLE_LETTER_RE = re.compile(
    r"\b(?:ACMG(?:\s+classification)?|final(?:\s+classification)?|classification|"
    r"classified\s+as|result|verdict)\b"
    r"\s*(?::|=|\bis\b|\bas\b)?\s*['\"]?(?:P|B)['\"]?"
    r"(?=$|[\s.;,)\]])",
    re.IGNORECASE,
)
FINAL_CONTEXT_RE = re.compile(
    r"\b(final\s+classification|ACMG\s+classification|overall\s+classification|"
    r"classification_status\s*[:=]\s*['\"]?final\s+classification|"
    r"final\s+ACMG|five-tier|5-tier)\b|"
    r"最终\s*ACMG\s*分类|最终分类|ACMG\s*分类|致病性评级",
    re.IGNORECASE,
)
VALIDATOR_PASS_RE = re.compile(r'"validator_status"\s*:\s*"PASS"', re.IGNORECASE)
SEMANTIC_PASS_RE = re.compile(r'"semantic_combiner_status"\s*:\s*"PASS"', re.IGNORECASE)
EMPTY_VIOLATIONS_RE = re.compile(r'"violations"\s*:\s*\[\s*\]', re.IGNORECASE)
SOURCE_LABEL_RE = re.compile(r"\b(GeneBe|ClinVar|HGMD|LOVD|VCEP|lab\s+assertion|paper\s+label)\b", re.IGNORECASE)
COUNTED_SOURCE_RE = re.compile(
    r"\b(counted\s+evidence|current\s+counted\s+evidence|applied\s+evidence|"
    r"PVS1|PS1|PS3|PM1|PM2|PM5|PP3|score\s*[0-9]+)\b",
    re.IGNORECASE,
)
DIRECT_MCP_TOOL_RE = re.compile(
    r"\b(mcp__tooluniverse__(?:find_tools|execute_tool)|"
    r"GeneBe_classify_variant|GeneBe_classify_variants_batch|"
    r"InterVar_classify_variant|"
    r"SpliceAI_predict_splice|SpliceAI_get_max_delta|"
    r"MyVariant_get_pathogenicity_scores|EnsemblVEP_annotate_hgvs|"
    r"ClinVar_get_clinical_significance|"
    r"gnomAD|EnsemblVar_get_population_frequencies|MaveDB|DMS|"
    r"ClinGen_search_gene_validity|G2P_search|GeneReviews)\b",
    re.IGNORECASE,
)
ONLINE_LITERATURE_COVERAGE_RE = re.compile(
    r"\b(tooluniverse-literature-deep-research|"
    r"source_category\s*['\"]?\s*:\s*['\"]?literature|"
    r"query_terms|queried_sources)\b",
    re.IGNORECASE,
)
NO_ONLINE_LITERATURE_RE = re.compile(
    r"\b(no|without|missing)\s+(?:online\s+)?(?:PubMed|PMC|EuropePMC|literature|literature\s+coverage)",
    re.IGNORECASE,
)
FORBIDDEN_VARIANT_INTERPRETATION_ROUTE_RE = re.compile(
    r"(ACMG\s+(?:clinical\s+)?classification|ACMG\s+pathogenicity\s+classification|"
    r"pathogenicity\s+classification|complete\s+ACMG|final\s+ACMG|"
    r"ClinVar\s*/\s*OMIM\s+variant\s+interpretation).*tooluniverse-variant-interpretation|"
    r"tooluniverse-variant-interpretation.*(ACMG\s+(?:clinical\s+)?classification|"
    r"pathogenicity\s+classification|complete\s+ACMG|final\s+ACMG)",
    re.IGNORECASE,
)
VARIANT_INTERPRETATION_FRONTMATTER_FORBIDDEN_RE = re.compile(
    r"ACMG[- ]classified|VUS classification|pathogenicity assessment|clinical[- ]grade",
    re.IGNORECASE,
)
HIGH_RISK_TOOL_NOTICE_PATTERNS = (
    re.compile(r"source[_ -]?lead", re.IGNORECASE),
    re.compile(r"not\s+(?:ACMG\s+)?counted\s+evidence", re.IGNORECASE),
    re.compile(r"validator_status\s*:\s*PASS|validator\s+PASS", re.IGNORECASE),
)
HIGH_RISK_TOOL_DEFINITION_FILES = (
    "genebe_tools.json",
    "intervar_tools.json",
    "clinvar_tools.json",
    "spliceai_tools.json",
    "biothings_tools.json",
    "ensembl_vep_tools.json",
)
HIGH_RISK_TOOL_NAMES = (
    "GeneBe_classify_variant",
    "GeneBe_classify_variants_batch",
    "InterVar_classify_variant",
    "ClinVar_get_clinical_significance",
    "SpliceAI_predict_splice",
    "SpliceAI_get_max_delta",
    "MyVariant_get_pathogenicity_scores",
    "EnsemblVEP_annotate_hgvs",
)
HIGH_RISK_EXECUTE_GUARD_TOOLS = (
    *HIGH_RISK_TOOL_NAMES,
    "EnsemblVEP_variant_recoder",
    "gnomad_search_variants",
    "gnomad_get_variant",
    "gnomad_get_variant_populations",
    "MaveDB_search_score_sets",
    "MaveDB_get_variant_scores",
    "MaveDB_get_effect_matrix",
    "MaveDB_get_clinical_controls",
    "ClinGen_search_gene_validity",
    "G2P_search",
    "G2P_get_record",
    "G2P_get_gene",
)
FRONT_DOOR_TOOL_NAME = "ACMG_overlay_gate_assess_variant"
CHINESE_GATE_QUERY = "根据ACMG规则评估 FGFR3;NM_000142.5:c.1075+95C>G 杂合变异致病性"
ENGLISH_GATE_QUERY = "ACMG pathogenicity classification FGFR3 variant"
NON_ACMG_QUERY = "protein structure prediction for kinase domain"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def has_validator_pass(text: str) -> bool:
    return bool(VALIDATOR_PASS_RE.search(text) and EMPTY_VIOLATIONS_RE.search(text))


def has_semantic_pass(text: str) -> bool:
    return bool(SEMANTIC_PASS_RE.search(text))


def has_final_like_label(text: str) -> bool:
    if PAIRED_ABBREVIATION_RE.search(text):
        return True
    if STANDALONE_ABBREVIATION_RE.search(text):
        return True
    if CONTEXTUAL_SINGLE_LETTER_RE.search(text):
        return True
    return bool(FULL_FINAL_LABEL_RE.search(text) and FINAL_CONTEXT_RE.search(text))


def has_online_literature_coverage(text: str) -> bool:
    if not ONLINE_LITERATURE_COVERAGE_RE.search(text):
        return False
    if NO_ONLINE_LITERATURE_RE.search(text) and "source_category" not in text and "query_terms" not in text:
        return False
    return True


def check_text(text: str) -> list[str]:
    violations: list[str] = []
    has_bundle = "acmg_assessment_bundle" in text
    final_like = has_final_like_label(text)

    if final_like and not has_bundle:
        violations.append("final_classification_without_acmg_assessment_bundle")
    if final_like and not has_validator_pass(text):
        violations.append("final_classification_without_validator_pass")
    if final_like and has_validator_pass(text) and not has_semantic_pass(text):
        violations.append("final_classification_without_semantic_combiner_pass")

    if final_like and DIRECT_MCP_TOOL_RE.search(text) and not has_validator_pass(text):
        violations.append("direct_mcp_variant_tool_final_classification_without_validator_pass")
        if not has_online_literature_coverage(text):
            violations.append("direct_mcp_final_without_online_literature_coverage")

    source_assertion_lead = "source_assertions_or_leads" in text or "source assertions / leads" in text.lower()
    if SOURCE_LABEL_RE.search(text) and COUNTED_SOURCE_RE.search(text) and not source_assertion_lead:
        violations.append("source_label_or_automated_classifier_used_as_counted_evidence")

    natural_language_bundle = "Bundle Route Plan" in text and "overlay_applied" in text
    if natural_language_bundle and not has_bundle:
        violations.append("natural_language_route_table_without_json_bundle")

    if FORBIDDEN_VARIANT_INTERPRETATION_ROUTE_RE.search(text):
        violations.append("final_acmg_route_points_to_variant_interpretation")

    return violations


def _iter_json_tool_objects(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _definition_has_gate_notice(tool: dict[str, Any]) -> bool:
    text = json.dumps(tool, ensure_ascii=False)
    return all(pattern.search(text) for pattern in HIGH_RISK_TOOL_NOTICE_PATTERNS)


def scan_high_risk_tool_definitions(root: Path) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    data_root = root / "src" / "tooluniverse" / "data"
    if not data_root.exists():
        return violations

    gate_path = data_root / "acmg_overlay_gate_tools.json"
    if not gate_path.exists():
        violations.append(
            {
                "file": str(gate_path),
                "tool": FRONT_DOOR_TOOL_NAME,
                "violation": "acmg_front_door_gate_tool_definition_not_found",
            }
        )
    else:
        gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
        gate_tools = [tool for tool in _iter_json_tool_objects(gate_payload) if tool.get("name") == FRONT_DOOR_TOOL_NAME]
        if not gate_tools:
            violations.append(
                {
                    "file": str(gate_path),
                    "tool": FRONT_DOOR_TOOL_NAME,
                    "violation": "acmg_front_door_gate_tool_definition_not_found",
                }
            )
        else:
            gate_tool = gate_tools[0]
            gate_text = json.dumps(gate_tool, ensure_ascii=False)
            if "not an ACMG classifier" not in gate_text or "validator_status: PASS" not in gate_text:
                violations.append(
                    {
                        "file": str(gate_path),
                        "tool": FRONT_DOOR_TOOL_NAME,
                        "violation": "acmg_front_door_gate_tool_missing_role_or_validator_wording",
                    }
                )
            output_mode = (
                gate_tool.get("parameter", {})
                .get("properties", {})
                .get("output_mode", {})
            )
            if output_mode.get("default") != "compact" or set(output_mode.get("enum", [])) != {"compact", "full"}:
                violations.append(
                    {
                        "file": str(gate_path),
                        "tool": FRONT_DOOR_TOOL_NAME,
                        "violation": "acmg_front_door_gate_tool_missing_compact_full_output_mode",
                    }
                )

    found: set[str] = set()
    for filename in HIGH_RISK_TOOL_DEFINITION_FILES:
        path = data_root / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for tool in _iter_json_tool_objects(payload):
            name = str(tool.get("name", ""))
            if name not in HIGH_RISK_TOOL_NAMES:
                continue
            found.add(name)
            if not _definition_has_gate_notice(tool):
                violations.append(
                    {
                        "file": str(path),
                        "tool": name,
                        "violation": "high_risk_variant_tool_missing_acmg_gate_notice",
                    }
                )

    for name in sorted(set(HIGH_RISK_TOOL_NAMES) - found):
        violations.append(
            {
                "file": str(data_root),
                "tool": name,
                "violation": "high_risk_variant_tool_definition_not_found",
            }
        )

    return violations


def scan_gate_priority_implementation(root: Path) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    src_root = root / "src" / "tooluniverse"
    helper = src_root / "acmg_gate_search.py"
    keyword = src_root / "tool_finder_keyword.py"
    smcp = src_root / "smcp.py"
    execute_function = src_root / "execute_function.py"
    tool_discovery = src_root / "tool_discovery_tools.py"

    if not helper.exists():
        return [
            {
                "file": str(helper),
                "violation": "acmg_gate_search_helper_not_found",
            }
        ]

    spec = importlib.util.spec_from_file_location("acmg_gate_search_check", helper)
    module = importlib.util.module_from_spec(spec) if spec and spec.loader else None
    if module is None or spec is None or spec.loader is None:
        violations.append(
            {
                "file": str(helper),
                "violation": "acmg_gate_search_helper_not_importable",
            }
        )
    else:
        spec.loader.exec_module(module)
        detector = getattr(module, "looks_like_acmg_gate_query", None)
        result_guard = getattr(module, "attach_acmg_gate_notice", None)
        high_risk_detector = getattr(module, "is_high_risk_acmg_tool", None)
        if not callable(detector):
            violations.append(
                {
                    "file": str(helper),
                    "violation": "acmg_gate_query_detector_not_found",
                }
            )
        else:
            if not detector(CHINESE_GATE_QUERY):
                violations.append(
                    {
                        "file": str(helper),
                        "violation": "chinese_hgvs_acmg_query_not_detected",
                    }
                )
            if not detector(ENGLISH_GATE_QUERY):
                violations.append(
                    {
                        "file": str(helper),
                        "violation": "english_acmg_query_not_detected",
                    }
                )
            if detector(NON_ACMG_QUERY):
                violations.append(
                    {
                        "file": str(helper),
                        "violation": "non_acmg_query_detected_as_gate_query",
                    }
                )
        if not callable(result_guard) or not callable(high_risk_detector):
            violations.append(
                {
                    "file": str(helper),
                    "violation": "acmg_execute_result_guard_not_found",
                }
            )
        else:
            for tool_name in HIGH_RISK_EXECUTE_GUARD_TOOLS:
                if not high_risk_detector(tool_name):
                    violations.append(
                        {
                            "file": str(helper),
                            "tool": tool_name,
                            "violation": "high_risk_tool_missing_execute_guard",
                        }
                    )
            guarded = result_guard("GeneBe_classify_variant", {"status": "success"})
            if not isinstance(guarded, dict) or guarded.get("recommended_front_door_tool") != FRONT_DOOR_TOOL_NAME:
                violations.append(
                    {
                        "file": str(helper),
                        "violation": "acmg_execute_result_guard_missing_front_door_marker",
                    }
                )

    if not keyword.exists() or "add_acmg_gate_to_search_payload" not in keyword.read_text(encoding="utf-8"):
        violations.append(
            {
                "file": str(keyword),
                "violation": "tool_finder_keyword_missing_acmg_gate_prepend",
            }
        )
    if not smcp.exists() or "add_acmg_gate_notice_to_search" not in smcp.read_text(encoding="utf-8"):
        violations.append(
            {
                "file": str(smcp),
                "violation": "smcp_find_tools_missing_acmg_gate_notice",
            }
        )
    execute_text = execute_function.read_text(encoding="utf-8") if execute_function.exists() else ""
    if "attach_acmg_gate_notice" not in execute_text:
        violations.append(
            {
                "file": str(execute_function),
                "violation": "execute_function_missing_acmg_result_guard",
            }
        )
    if execute_text.count("attach_acmg_gate_notice(function_name") < 4:
        violations.append(
            {
                "file": str(execute_function),
                "violation": "execute_function_missing_sync_async_or_cache_acmg_guard",
            }
        )
    if not tool_discovery.exists() or "attach_acmg_gate_notice(tool_name" not in tool_discovery.read_text(encoding="utf-8"):
        violations.append(
            {
                "file": str(tool_discovery),
                "violation": "execute_tool_wrapper_missing_acmg_result_guard",
            }
        )

    return violations


def run_fixture(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    text = str(payload.get("text", ""))
    expected = str(payload.get("expected_entrypoint_status", "")).strip().upper()
    if expected not in {PASS, FAIL}:
        raise ValueError(f"{path} expected_entrypoint_status must be PASS or FAIL")

    violations = check_text(text)
    actual = FAIL if violations else PASS
    return {
        "fixture": path.name,
        "id": payload.get("id", path.stem),
        "expected": expected,
        "actual": actual,
        "ok": actual == expected,
        "violations": violations,
    }


def scan_static_gate_violations(skills_root: Path) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    variant_skill = skills_root / "tooluniverse-variant-interpretation" / "SKILL.md"
    if variant_skill.exists():
        head = "\n".join(variant_skill.read_text(encoding="utf-8").splitlines()[:8])
        if VARIANT_INTERPRETATION_FRONTMATTER_FORBIDDEN_RE.search(head):
            violations.append(
                {
                    "file": str(variant_skill),
                    "line": 3,
                    "violation": "variant_interpretation_frontmatter_promises_final_acmg",
                }
            )

    bayes_skill = skills_root / "tooluniverse-acmg-bayesian-classification-framework" / "SKILL.md"
    if bayes_skill.exists():
        text = bayes_skill.read_text(encoding="utf-8")
        if "acmg_assessment_bundle" not in text or "validator_status" not in text:
            violations.append(
                {
                    "file": str(bayes_skill),
                    "line": 1,
                    "violation": "bayesian_final_output_missing_validator_gate",
                }
            )

    for path in sorted(skills_root.glob("tooluniverse*/**/*")):
        if not path.is_file() or path.suffix not in {".md", ".py", ".json"}:
            continue
        if "entrypoint_bypass_fixtures" in path.parts:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "Do not stop at `tooluniverse-variant-interpretation`" in line:
                continue
            if FORBIDDEN_VARIANT_INTERPRETATION_ROUTE_RE.search(line):
                violations.append(
                    {
                        "file": str(path),
                        "line": line_no,
                        "violation": "final_acmg_route_points_to_variant_interpretation",
                        "text": line.strip(),
                    }
                )

    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_dir = Path(__file__).resolve().parents[1] / "evals" / "entrypoint_bypass_fixtures"
    parser.add_argument("fixtures_dir", nargs="?", default=str(default_dir))
    parser.add_argument("--fixtures", dest="fixtures_dir_flag", help="Run fixtures from this directory. Kept for compatibility with ACMG validation docs.")
    parser.add_argument(
        "--skills-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Path to the ToolUniverse skills root for static gate checks.",
    )
    parser.add_argument(
        "--tooluniverse-root",
        default="",
        help="Optional ToolUniverse repository root for high-risk direct-MCP tool definition checks.",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    fixtures_dir = Path(args.fixtures_dir_flag or args.fixtures_dir)
    results = [run_fixture(path) for path in sorted(fixtures_dir.glob("*.json"))]
    static_violations = scan_static_gate_violations(Path(args.skills_root))
    tool_definition_violations = (
        scan_high_risk_tool_definitions(Path(args.tooluniverse_root))
        if args.tooluniverse_root
        else []
    )
    gate_priority_violations = (
        scan_gate_priority_implementation(Path(args.tooluniverse_root))
        if args.tooluniverse_root
        else []
    )
    summary = {
        "status": PASS
        if all(row["ok"] for row in results)
        and not static_violations
        and not tool_definition_violations
        and not gate_priority_violations
        else FAIL,
        "fixture_count": len(results),
        "results": results,
        "static_violation_count": len(static_violations),
        "static_violations": static_violations,
        "tool_definition_violation_count": len(tool_definition_violations),
        "tool_definition_violations": tool_definition_violations,
        "gate_priority_violation_count": len(gate_priority_violations),
        "gate_priority_violations": gate_priority_violations,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if summary["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
