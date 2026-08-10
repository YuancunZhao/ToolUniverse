#!/usr/bin/env python3
"""Verify ACMG overlay MCP tool JSON registration matches Python wrappers."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "src" / "tooluniverse" / "data" / "acmg_overlay_gate_tools.json"
TOOLS_DIR = ROOT / "src" / "tooluniverse" / "tools"

COLLECTOR_NAMES = {
    "ACMG_evidence_collector",
    "ACMG_overlay_gate_assess_variant",
}
REQUIRED_COLLECTOR_RETURN_FIELDS = {
    "status",
    "execution_status",
    "coverage_status",
    "variant",
    "variant_identity",
    "variant_scope",
    "consequence_profile",
    "rule_context",
    "runtime_manifest",
    "guard_context",
    "coverage_summary",
    "source_facts",
    "source_assertions",
    "prior_variant_candidates",
    "literature_candidates",
    "literature_review",
    "recoverable_gaps",
    "workflow_status",
    "review_readiness",
    "next_actions",
    "predictor_scores",
    "criterion_reviews",
    "evidence_cards",
    "compatibility_report",
    "conflict_report",
    "vcep_context",
    "vcep_assertions",
    "rule_scenarios",
    "automatic_bayesian",
    "verified_bayesian",
    "scenario_estimates",
    "automation_report",
    "user_selected_bayesian",
    "decision_report",
    "limitations",
    "final_classification_allowed",
}

PY_TO_JSON_TYPE = {
    "float": "number",
    "int": "integer",
    "str": "string",
    "bool": "boolean",
}
SKIP_PARAMS = {"stream_callback", "use_cache", "validate"}


def _normalize_type(annot) -> str:
    if annot is None:
        return "any"
    raw = ast.unparse(annot)
    m = re.search(r"Optional\[(\w+)\]", raw)
    if m:
        inner = m.group(1)
        return PY_TO_JSON_TYPE.get(inner.lower(), inner.lower())
    m = re.search(r"(\w+)\s*\|\s*None", raw)
    if m:
        inner = m.group(1)
        return PY_TO_JSON_TYPE.get(inner.lower(), inner.lower())
    if "list" in raw.lower():
        return "array"
    if "dict" in raw.lower():
        return "object"
    simplified = raw.replace(" ", "")
    return PY_TO_JSON_TYPE.get(simplified.lower(), simplified.lower())


def extract_py_params(filepath: Path) -> dict[str, dict]:
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        params: dict[str, dict] = {}
        for arg in node.args.args:
            name = arg.arg
            if name == "self" or name.startswith("*"):
                continue
            typ = _normalize_type(getattr(arg, "annotation", None))
            params[name] = {"type": typ, "default": None}

        defaults = node.args.defaults
        if defaults:
            offset = len(node.args.args) - len(defaults)
            for i, d in enumerate(defaults):
                idx = offset + i
                if idx < len(node.args.args):
                    name = node.args.args[idx].arg
                    if name not in params:
                        params[name] = {"type": "any"}
                    try:
                        params[name]["default"] = ast.literal_eval(d)
                    except (ValueError, TypeError):
                        pass

        for arg in node.args.kwonlyargs:
            typ = _normalize_type(getattr(arg, "annotation", None))
            params[arg.arg] = {"type": typ, "default": None}
        return params
    return {}


def main() -> int:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []

    for entry in data:
        name = entry.get("name", "")
        if not name:
            continue

        wrapper_path = TOOLS_DIR / f"{name}.py"
        if not wrapper_path.exists():
            continue  # registry entries without generated client wrappers are valid

        py_params = extract_py_params(wrapper_path)
        json_params = entry.get("parameter", {}).get("properties", {})

        for pname, pinfo in py_params.items():
            if pname in SKIP_PARAMS:
                continue
            if pname not in json_params:
                problems.append(f"MISSING_JSON_PARAM: {name}.{pname}")
                continue
            jt = json_params[pname].get("type", "")
            pt = pinfo.get("type", "")
            if jt and pt and pt != "any" and jt != pt:
                problems.append(f"TYPE_MISMATCH: {name}.{pname} json={jt} py={pt}")

        for pname in json_params:
            if pname not in py_params:
                problems.append(f"EXTRA_JSON_PARAM: {name}.{pname}")

        if name in COLLECTOR_NAMES:
            ret = entry.get("return_schema", {}).get("properties", {})
            missing = REQUIRED_COLLECTOR_RETURN_FIELDS - set(ret)
            for field in sorted(missing):
                problems.append(f"MISSING_RETURN: {name}.{field}")

            final_field = ret.get("final_classification_allowed", {})
            if final_field.get("const") is not False:
                problems.append(
                    f"INVALID_RETURN: {name}.final_classification_allowed must be false"
                )

    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        for p in problems:
            print(f"  {p}")
        return 1

    print(f"PASS: all {len(data)} ACMG MCP tools verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
