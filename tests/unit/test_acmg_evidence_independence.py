#!/usr/bin/env python3
"""Evidence independence guard tests for ACMG finalization."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.evidence_independence import evaluate_evidence_independence
from tooluniverse.acmg_gate.source_lead_sandbox import sandbox_source_output


def test_pp1_not_counted_without_relative_genotypes() -> None:
    result = evaluate_evidence_independence(
        {
            "counted_evidence": [
                {"criterion": "PP1", "source_id": "family-text", "confirmed_relative_genotypes": False}
            ]
        }
    )
    assert result["status"] == "BLOCK", result
    assert any("PP1 requires genotype-supported segregation" in reason for reason in result["blocking_reasons"])


def test_pp4_still_allowed_from_phenotype() -> None:
    result = evaluate_evidence_independence(
        {"counted_evidence": [{"criterion": "PP4", "source_id": "phenotype", "phenotype_specific": True}]}
    )
    assert result["status"] == "PASS", result


def test_pp1_pp4_overlap_warning() -> None:
    result = evaluate_evidence_independence(
        {
            "counted_evidence": [
                {"criterion": "PP1", "source_id": "family-phenotype", "confirmed_relative_genotypes": False},
                {"criterion": "PP4", "source_id": "family-phenotype", "phenotype_specific": True},
            ]
        }
    )
    assert result["status"] == "BLOCK", result
    assert any(row["code"] == "pp1_pp4_overlap" for row in result["warnings"])


def test_ps3_pm4_same_minigene_source_does_not_double_count() -> None:
    result = evaluate_evidence_independence(
        {
            "counted_evidence": [
                {"criterion": "PS3", "source_id": "minigene-1"},
                {"criterion": "PM4", "source_id": "minigene-1"},
            ]
        }
    )
    assert result["status"] == "BLOCK", result
    assert any(row["code"] == "ps3_pm4_same_source_overlap" for row in result["warnings"])


def test_ps4_duplicated_cases_capped() -> None:
    result = evaluate_evidence_independence(
        {
            "counted_evidence": [
                {"criterion": "PS4", "case_ids": ["case-1", "case-2"]},
                {"criterion": "PS4", "case_ids": ["case-2", "case-3"]},
            ]
        }
    )
    assert result["status"] == "BLOCK", result
    assert any(row["code"] == "ps4_duplicate_cases" and row["max_strength"] == "Supporting" for row in result["warnings"])


def test_pm2_deep_intronic_absent_with_coverage_uncertainty_stays_supporting() -> None:
    result = evaluate_evidence_independence(
        {
            "counted_evidence": [
                {"criterion": "PM2", "strength": "moderate", "variant_region": "deep_intronic", "coverage_adequacy": False}
            ]
        }
    )
    assert result["status"] == "PASS", result
    row = result["counted_evidence"][0]
    assert row["strength"] == "supporting"
    assert row["population_absence_status"] == "absent_but_intronic_coverage_uncertain"


def test_genebe_criteria_remain_counted_false() -> None:
    genebe = sandbox_source_output(
        tool_name="GeneBe_classify_variant",
        raw_output={"acmg_classification": "Likely_pathogenic", "acmg_criteria": ["PS3", "PM2", "PP3_Moderate", "PP5"]},
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    result = evaluate_evidence_independence({"source_lead_sandbox": [genebe], "route_candidates": genebe["candidate_routes"]})
    assert result["status"] == "PASS", result
    assert any(row["code"] == "genebe_criteria_source_lead_only" for row in result["warnings"])
    assert all(row["counted"] is False for row in genebe["candidate_routes"])


if __name__ == "__main__":
    test_pp1_not_counted_without_relative_genotypes()
    test_pp4_still_allowed_from_phenotype()
    test_pp1_pp4_overlap_warning()
    test_ps3_pm4_same_minigene_source_does_not_double_count()
    test_ps4_duplicated_cases_capped()
    test_pm2_deep_intronic_absent_with_coverage_uncertainty_stays_supporting()
    test_genebe_criteria_remain_counted_false()
    print("PASS test_acmg_evidence_independence")
