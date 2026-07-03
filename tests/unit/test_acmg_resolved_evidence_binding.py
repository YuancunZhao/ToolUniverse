#!/usr/bin/env python3
"""Resolved evidence must bind exactly to counted route audit rows."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.validate_acmg_overlay_bundle import (
    _normalized_evidence_strength,
    criterion_code,
    validate,
    validate_minimal,
)


def _registry() -> list[dict[str, object]]:
    return [
        {
            "criterion_group": "pp3_bp4_missense_prediction",
            "route_kind": "evidence_scoring",
            "trigger_policy": "variant_type_baseline",
            "enforcement_level": "must_plan",
            "applies_when": ["missense_variant"],
            "covered_criteria": ["PP3", "BP4"],
        },
    ]


def _bundle() -> dict[str, object]:
    return {
        "classification": "VUS",
        "classification_status": "final classification",
        "variant": {
            "gene": "GENE",
            "consequence": "intronic_variant",
            "variant_type": "SNV",
        },
        "disease_context": {"status": "resolved"},
        "vcep_context": {
            "scope_match": "none",
            "criteria_overridden": [],
            "generic_overlay_responsibilities": [],
        },
        "route_plan": [],
        "coverage_audit": [
            {
                "source_category": "computational",
                "query_status": "success",
                "queried_sources": ["SpliceAI"],
                "triggered_routes": ["pp3_bp4_missense_prediction"],
                "hits": [],
            },
            {
                "source_category": "literature",
                "query_status": "no_hit",
                "queried_sources": ["PubMed"],
                "query_terms": ["GENE variant ACMG"],
                "query_tool": "pubmed",
                "reason": "No discovery triggers found.",
                "not_triggered_routes": [
                    "pp1_bs4_pp4_segregation",
                    "ps4_case_enrichment",
                    "de_novo_ps2_pm6",
                    "pm3_in_trans",
                    "ps3_bs3_functional_assay",
                ],
                "hits": [],
            },
        ],
        "overlay_results": [],
        "route_audit": [
            {
                "criterion": "PP3",
                "proposed_evidence": "PP3_Supporting",
                "counted": True,
                "route_outcome": "overlay_applied",
                "guidance_authority": "ClinGen/SVI primary",
                "overlay_or_vcep_source": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement",
            },
        ],
        "compatibility_resolution": {
            "current_counted_evidence_resolved": [
                {"criterion": "PP3", "strength": "PP3_Strong", "source": "manual"},
            ],
        },
    }


def test_resolved_counted_evidence_requires_exact_strength_binding() -> None:
    result = validate(_bundle(), _registry())

    assert result["status"] != "PASS", result
    assert any(
        violation["code"] == "resolved_evidence_strength_mismatch"
        for violation in result["violations"]
    ), result


def _violation_codes(result: dict[str, object]) -> set[str]:
    return {
        str(violation["code"])
        for violation in result["violations"]
        if isinstance(violation, dict)
    }


def test_each_resolved_counted_evidence_item_must_bind_to_counted_audit_row() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {
                "criterion": "PP3",
                "strength": "PP3_Supporting",
                "source": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement",
            },
            {"criterion": "PP3", "strength": "PP3_Strong", "source": "manual"},
        ],
    }

    result = validate(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_strength_mismatch" in _violation_codes(result)


def test_minimal_validation_rejects_extra_unbound_resolved_evidence_item() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {
                "criterion": "PP3",
                "strength": "PP3_Supporting",
                "source": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement",
            },
            {"criterion": "PP3", "strength": "PP3_Strong", "source": "manual"},
        ],
    }

    result = validate_minimal(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_strength_mismatch" in _violation_codes(result)


def test_resolved_source_must_match_counted_audit_source() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {"criterion": "PP3", "strength": "PP3_Supporting", "source": "manual"},
        ],
    }

    result = validate(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_source_mismatch" in _violation_codes(result)
    assert "resolved_evidence_strength_mismatch" not in _violation_codes(result)


def test_resolved_source_must_not_be_omitted_when_counted_audit_has_source() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {"criterion": "PP3", "strength": "PP3_Supporting"},
        ],
    }

    result = validate(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_source_mismatch" in _violation_codes(result)
    assert "resolved_evidence_strength_mismatch" not in _violation_codes(result)


def test_minimal_validation_reports_source_mismatch_separately_from_strength_mismatch() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {"criterion": "PP3", "strength": "PP3_Supporting", "source": "manual"},
        ],
    }

    result = validate_minimal(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_source_mismatch" in _violation_codes(result)
    assert "resolved_evidence_strength_mismatch" not in _violation_codes(result)


def test_non_ba1_resolved_item_that_mentions_ba1_is_still_validated() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {
                "criterion": "PP3",
                "strength": "PP3_Strong",
                "evidence": "mentions BA1",
            },
        ],
    }

    result = validate(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_strength_mismatch" in _violation_codes(result)


def test_resolved_criterion_without_counted_route_match_reports_missing_audit_match() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {"criterion": "PM5_Moderate", "strength": "Moderate"},
        ],
    }

    result = validate(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_without_counted_audit_match" in _violation_codes(result)


def test_strength_normalization_handles_multiword_pvs1_suffixes() -> None:
    assert _normalized_evidence_strength("PVS1_Very_Strong", "PVS1") == "very_strong"
    assert _normalized_evidence_strength("PVS1-Very-Strong", "PVS1") == "very_strong"
    assert _normalized_evidence_strength("PVS1 Very Strong", "PVS1") == "very_strong"
    assert _normalized_evidence_strength("PP3 Supporting evidence", "PP3") == "supporting"
    assert _normalized_evidence_strength("BA1", "BA1") == "standalone"
    assert _normalized_evidence_strength("PVS1", "PVS1") == ""
    assert _normalized_evidence_strength("PM2", "PM2") == ""
    assert _normalized_evidence_strength("manual_note", "PP3") == ""
    assert _normalized_evidence_strength("PS1 not strong", "PS1") == ""
    assert _normalized_evidence_strength("PP3 non-supporting", "PP3") == ""
    assert _normalized_evidence_strength("not PP3 supporting", "PP3") == ""
    assert _normalized_evidence_strength("without PVS1 very strong", "PVS1") == ""


def test_criterion_code_recognizes_full_acmg_set_and_strength_suffixes() -> None:
    for code in (
        "BA1",
        "BS1",
        "BS2",
        "BS3",
        "BS4",
        "BP1",
        "BP2",
        "BP3",
        "BP4",
        "BP5",
        "BP6",
        "BP7",
        "PVS1",
        "PS1",
        "PS2",
        "PS3",
        "PS4",
        "PM1",
        "PM2",
        "PM3",
        "PM4",
        "PM5",
        "PM6",
        "PP1",
        "PP2",
        "PP3",
        "PP4",
        "PP5",
    ):
        assert criterion_code(f"{code}_Strong") == code
        assert criterion_code(f"resolved {code} evidence") == code

    assert criterion_code("PM5_Moderate") == "PM5"
    assert criterion_code("PS1_Strong") == "PS1"


def test_dict_resolved_criterion_with_strength_suffix_binds_to_base_criterion() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {
                "criterion": "PP3_Supporting",
                "strength": "Supporting",
                "source": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement",
            },
        ],
    }

    result = validate(bundle, _registry())

    assert "resolved_evidence_without_counted_audit_match" not in _violation_codes(result)
    assert "resolved_evidence_strength_mismatch" not in _violation_codes(result)


def test_row_criterion_with_strength_suffix_binds_to_base_resolved_criterion() -> None:
    bundle = _bundle()
    route_row = bundle["route_audit"][0]
    route_row["criterion"] = "PP3_Supporting"
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {
                "criterion": "PP3",
                "strength": "Supporting",
                "source": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement",
            },
        ],
    }

    result = validate(bundle, _registry())

    assert "resolved_evidence_without_counted_audit_match" not in _violation_codes(result)
    assert "resolved_evidence_strength_mismatch" not in _violation_codes(result)


def test_ba1_resolved_item_requires_matching_counted_audit_row() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {"criterion": "BA1", "strength": "standalone"},
        ],
    }

    result = validate(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_without_counted_audit_match" in _violation_codes(result)


def test_bare_ba1_resolved_item_binds_to_matching_counted_audit_row() -> None:
    bundle = _bundle()
    bundle["route_audit"] = [
        {
            "criterion": "BA1",
            "proposed_evidence": "BA1",
            "counted": True,
            "route_outcome": "overlay_applied",
            "guidance_authority": "ClinGen/SVI primary",
            "overlay_or_vcep_source": "tooluniverse-acmg-ba1-frequency-exception",
        },
    ]
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {
                "criterion": "BA1",
                "strength": "BA1",
                "source": "tooluniverse-acmg-ba1-frequency-exception",
            },
        ],
    }
    bundle["classification"] = "Benign"

    result = validate(bundle, _registry())

    assert "resolved_evidence_without_counted_audit_match" not in _violation_codes(result)
    assert "resolved_evidence_strength_mismatch" not in _violation_codes(result)
    assert "resolved_evidence_source_mismatch" not in _violation_codes(result)


def test_bare_non_ba1_resolved_item_does_not_bind_without_explicit_strength() -> None:
    bundle = _bundle()
    bundle["route_audit"] = [
        {
            "criterion": "PVS1",
            "proposed_evidence": "PVS1",
            "counted": True,
            "route_outcome": "overlay_applied",
            "guidance_authority": "ClinGen/SVI primary",
            "overlay_or_vcep_source": "tooluniverse-acmg-pvs1-lof-decision-tree-refinement",
        },
    ]
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {
                "criterion": "PVS1",
                "strength": "PVS1",
                "source": "tooluniverse-acmg-pvs1-lof-decision-tree-refinement",
            },
        ],
    }

    result = validate_minimal(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_strength_mismatch" in _violation_codes(result)
    assert "resolved_evidence_source_mismatch" not in _violation_codes(result)


def test_unparsed_matching_strength_tokens_do_not_bind() -> None:
    bundle = _bundle()
    bundle["route_audit"][0]["proposed_evidence"] = "manual_note"
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {
                "criterion": "PP3",
                "strength": "manual_note",
                "source": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement",
            },
        ],
    }

    result = validate_minimal(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_strength_mismatch" in _violation_codes(result)
    assert "resolved_evidence_source_mismatch" not in _violation_codes(result)


def test_negated_free_text_strength_does_not_bind_to_counted_route() -> None:
    bundle = _bundle()
    bundle["route_audit"][0]["criterion"] = "PS1"
    bundle["route_audit"][0]["proposed_evidence"] = "PS1_Strong"
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": ["PS1 not strong"],
    }

    result = validate_minimal(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_strength_mismatch" in _violation_codes(result)


def test_precriterion_negated_free_text_strength_does_not_bind_to_counted_route() -> None:
    bundle = _bundle()
    bundle["compatibility_resolution"] = {
        "current_counted_evidence_resolved": [
            {
                "criterion": "PP3",
                "strength": "not PP3 supporting",
                "source": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement",
            },
        ],
    }

    result = validate_minimal(bundle, _registry())

    assert result["status"] != "PASS", result
    assert "resolved_evidence_strength_mismatch" in _violation_codes(result)
    assert "resolved_evidence_source_mismatch" not in _violation_codes(result)


if __name__ == "__main__":
    test_resolved_counted_evidence_requires_exact_strength_binding()
    test_each_resolved_counted_evidence_item_must_bind_to_counted_audit_row()
    test_no_counted_evidence_yields_counting_violation()
    print("PASS test_acmg_resolved_evidence_binding (smoke 3/18)")
