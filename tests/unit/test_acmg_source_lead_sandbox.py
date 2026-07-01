#!/usr/bin/env python3
"""Direct tests for source-lead sandbox preservation and quarantine."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.source_lead_sandbox import sandbox_source_output


def test_source_lead_sandbox() -> None:
    splice = sandbox_source_output(
        tool_name="SpliceAI_predict_splice",
        raw_output={"DS_DG": 0.97, "DP_DG": -5, "interpretation": "pathogenic"},
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert splice["reviewable_features"]["DS_DG"] == 0.97
    assert splice["reviewable_features"]["DP_DG"] == -5
    assert splice["acmg_countable_evidence"] is False
    assert "interpretation" in splice["quarantined_conclusions"]

    genebe = sandbox_source_output(
        tool_name="GeneBe_classify_variant",
        raw_output={"acmg_classification": "Likely_pathogenic", "acmg_criteria": ["PS3", "PM2", "PP3_Moderate", "PP5"]},
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert genebe["quarantined_conclusions"]["acmg_classification"] == "Likely_pathogenic"
    assert genebe["counted"] is False
    assert all(row["counted"] is False for row in genebe["candidate_routes"])

    clinvar = sandbox_source_output(
        tool_name="ClinVar_get_clinical_significance",
        raw_output={"clinical_significance": "Pathogenic", "review_status": "criteria provided"},
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert clinvar["reviewable_features"]["review_status"] == "criteria provided"
    assert clinvar["final_classification_allowed"] is False

    gnomad = sandbox_source_output(
        tool_name="gnomad_get_variant",
        raw_output={"AF": 0.0, "AC": 0, "AN": 200000, "suggestion": "PM2"},
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert gnomad["reviewable_features"]["AF"] == 0.0
    assert gnomad["quarantined_conclusions"]["suggestion"] == "PM2"

    literature = sandbox_source_output(
        tool_name="PubMed_literature_search",
        raw_output={"PMID": "123", "title": "minigene assay", "functional_assay_details": "RNA minigene", "criteria": ["PS3"]},
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert literature["reviewable_features"]["functional_assay_details"] == "RNA minigene"
    assert literature["candidate_routes"][0]["counted"] is False

    user = sandbox_source_output(
        tool_name="user_context",
        raw_output={"de_novo": True, "phenotype": "short stature"},
        intent="ACMG_FINAL_CLASSIFICATION",
    )
    assert any(row["route"] == "ps2_pm6_de_novo_review" and row["counted"] is False for row in user["candidate_routes"])


if __name__ == "__main__":
    test_source_lead_sandbox()
    print("PASS test_acmg_source_lead_sandbox")
