#!/usr/bin/env python3
"""Check entrypoint transcripts for ACMG overlay-gate bypass patterns.

This is a prompt/entrypoint regression check, not a medical validator. It
detects final-classification wording that appears without a machine-checkable
assessment bundle and validator PASS summary, plus static skill-routing text
that points final ACMG/pathogenicity work at non-gate entrypoints.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PASS = "PASS"
FAIL = "FAIL"

FINAL_LABEL_RE = re.compile(
    r"\b(Pathogenic|Likely\s+Pathogenic|VUS|Variant\s+of\s+Uncertain\s+Significance|"
    r"Likely\s+Benign|Benign)\b",
    re.IGNORECASE,
)
FINAL_CONTEXT_RE = re.compile(
    r"\b(final\s+classification|ACMG\s+classification|overall\s+classification|"
    r"classification_status\s*[:=]\s*['\"]?final\s+classification|"
    r"final\s+ACMG|five-tier|5-tier)\b",
    re.IGNORECASE,
)
VALIDATOR_PASS_RE = re.compile(r'"validator_status"\s*:\s*"PASS"', re.IGNORECASE)
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
    r"SpliceAI_predict_splice|SpliceAI_get_max_delta|"
    r"MyVariant_get_pathogenicity_scores|EnsemblVEP_annotate_hgvs|"
    r"ClinVar_get_clinical_significance)\b",
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
    r"ACMG-classified|VUS classification|pathogenicity assessment|clinical-grade",
    re.IGNORECASE,
)
HIGH_RISK_TOOL_NOTICE_PATTERNS = (
    re.compile(r"source[_ -]?lead", re.IGNORECASE),
    re.compile(r"not\s+(?:ACMG\s+)?counted\s+evidence", re.IGNORECASE),
    re.compile(r"validator_status\s*:\s*PASS|validator\s+PASS", re.IGNORECASE),
)
HIGH_RISK_TOOL_DEFINITION_FILES = (
    "genebe_tools.json",
    "clinvar_tools.json",
    "spliceai_tools.json",
    "biothings_tools.json",
    "ensembl_vep_tools.json",
)
HIGH_RISK_TOOL_NAMES = (
    "GeneBe_classify_variant",
    "GeneBe_classify_variants_batch",
    "ClinVar_get_clinical_significance",
    "SpliceAI_predict_splice",
    "SpliceAI_get_max_delta",
    "MyVariant_get_pathogenicity_scores",
    "EnsemblVEP_annotate_hgvs",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def has_validator_pass(text: str) -> bool:
    return bool(VALIDATOR_PASS_RE.search(text) and EMPTY_VIOLATIONS_RE.search(text))


def check_text(text: str) -> list[str]:
    violations: list[str] = []
    has_bundle = "acmg_assessment_bundle" in text
    final_like = bool(FINAL_LABEL_RE.search(text) and FINAL_CONTEXT_RE.search(text))

    if final_like and not has_bundle:
        violations.append("final_classification_without_acmg_assessment_bundle")
    if final_like and not has_validator_pass(text):
        violations.append("final_classification_without_validator_pass")

    if final_like and DIRECT_MCP_TOOL_RE.search(text) and not has_validator_pass(text):
        violations.append("direct_mcp_variant_tool_final_classification_without_validator_pass")

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

    fixtures_dir = Path(args.fixtures_dir)
    results = [run_fixture(path) for path in sorted(fixtures_dir.glob("*.json"))]
    static_violations = scan_static_gate_violations(Path(args.skills_root))
    tool_definition_violations = (
        scan_high_risk_tool_definitions(Path(args.tooluniverse_root))
        if args.tooluniverse_root
        else []
    )
    summary = {
        "status": PASS
        if all(row["ok"] for row in results)
        and not static_violations
        and not tool_definition_violations
        else FAIL,
        "fixture_count": len(results),
        "results": results,
        "static_violation_count": len(static_violations),
        "static_violations": static_violations,
        "tool_definition_violation_count": len(tool_definition_violations),
        "tool_definition_violations": tool_definition_violations,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if summary["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
