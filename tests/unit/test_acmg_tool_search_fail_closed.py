#!/usr/bin/env python3
"""Direct python tests for ACMG fail-closed tool search behavior."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[2] / "src/tooluniverse/acmg_gate_search.py"
    spec = importlib.util.spec_from_file_location("acmg_gate_search_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_fail_closed_search() -> None:
    search = _load()
    payload = {
        "tools": [
            {"name": "GeneBe_classify_variant"},
            {"name": "ClinVar_get_clinical_significance"},
            {"name": "CADD_get_variant_score"},
            {"name": "AlphaMissense_get_variant_score"},
            {"name": "OpenCRAVAT_annotate_variant"},
            {"name": "SomeGenericVariantTool"},
        ],
        "limit": 10,
    }
    updated = search.add_acmg_gate_to_search_payload(
        payload,
        intent=search.detect_acmg_intent("Is this variant likely pathogenic?"),
    )
    names = [row["name"] for row in updated["tools"]]
    assert names == [
        "ACMG_overlay_gate_assess_variant",
        "GeneBe_classify_variant",
        "ClinVar_get_clinical_significance",
        "CADD_get_variant_score",
        "AlphaMissense_get_variant_score",
        "OpenCRAVAT_annotate_variant",
    ]
    for row in updated["tools"][1:]:
        assert row["source_lead_only"] is True
        assert row["final_classification_allowed"] is False
        assert row["acmg_countable_evidence"] is False
        assert row["must_route_through"] == "ACMG_overlay_gate_assess_variant"
        assert row["source_tools_must_use_sandbox"] is True
        assert row["may_emit_final_label"] is False


def test_query_string_positional_argument_is_safe() -> None:
    search = _load()
    payload = {"tools": [{"name": "GeneBe_classify_variant"}, {"name": "SomeGenericVariantTool"}]}
    updated = search.add_acmg_gate_to_search_payload(payload, "Is this variant likely pathogenic?")
    assert [row["name"] for row in updated["tools"]] == [
        "ACMG_overlay_gate_assess_variant",
        "GeneBe_classify_variant",
    ]


def test_query_helper_routes_through_intent_detector() -> None:
    search = _load()
    payload = {"tools": [{"name": "GeneBe_classify_variant"}, {"name": "SomeGenericVariantTool"}]}
    updated = search.add_acmg_gate_to_search_payload_for_query(payload, "variant pathogenicity")
    assert [row["name"] for row in updated["tools"]] == [
        "ACMG_overlay_gate_assess_variant",
        "GeneBe_classify_variant",
    ]


if __name__ == "__main__":
    test_fail_closed_search()
    test_query_string_positional_argument_is_safe()
    test_query_helper_routes_through_intent_detector()
    print("PASS test_acmg_tool_search_fail_closed")
