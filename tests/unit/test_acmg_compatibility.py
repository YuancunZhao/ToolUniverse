"""Evidence compatibility resolution before Bayesian multiplication."""

from __future__ import annotations

from tooluniverse.acmg.compatibility import resolve_evidence_compatibility
from tooluniverse.acmg.rule_catalog import rule_for_criterion


def _row(card_id: str, criterion: str, source_pmid: str | None = None, **extra):
    rule = rule_for_criterion(criterion)
    return {
        "card_id": card_id,
        "criterion": criterion,
        "strength": f"{criterion}_Supporting",
        "assessment_status": "met",
        "system_preview_included": True,
        "overlay_validated": True,
        "source_fact_ids": [f"{card_id}-fact"],
        "source_pmid": source_pmid,
        "rule_id": rule["rule_id"],
        "rule_version": rule["version"],
        **extra,
    }


def _resolve(rows):
    trusted = {
        fact_id
        for row in rows
        for fact_id in row.get("source_fact_ids", [])
        if isinstance(fact_id, str)
    }
    return resolve_evidence_compatibility(rows, trusted_source_fact_ids=trusted)


def test_exact_duplicate_card_is_included_once():
    row = _row("same", "PP3")
    resolved = _resolve([row, dict(row)])
    assert [item["card_id"] for item in resolved["compatible_evidence"]] == ["same"]
    assert len(resolved["excluded_evidence"]) == 1


def test_same_criterion_and_overlapping_cases_are_not_multiplied():
    first = _row("a", "PS2", source_case_ids=["case-1", "case-2"])
    second = _row("b", "PS2", source_case_ids=["case-2", "case-3"])
    resolved = _resolve([first, second])
    assert len(resolved["compatible_evidence"]) == 1
    assert resolved["excluded_evidence"][0]["reason"] == "overlapping_cases"


def test_unvalidated_rows_are_excluded_fail_closed():
    row = {**_row("a", "PP3"), "overlay_validated": False}
    resolved = _resolve([row])
    assert resolved["compatible_evidence"] == []
    assert (
        resolved["excluded_evidence"][0]["reason"]
        == "not_eligible_for_candidate_bayesian"
    )


def test_not_assessed_preview_row_is_excluded_fail_closed():
    row = {
        **_row("not-assessed", "PP3"),
        "assessment_status": "not_assessed",
    }
    resolved = _resolve([row])
    assert resolved["compatible_evidence"] == []
    assert resolved["excluded_evidence"][0]["reason"] == (
        "not_eligible_for_candidate_bayesian"
    )


def test_non_catalogued_population_cards_are_rejected_fail_closed():
    resolved = _resolve(
        [
            _row("ba1", "BA1"),
            _row("bs1", "BS1"),
        ]
    )
    assert resolved["compatible_evidence"] == []
    assert {row["reason"] for row in resolved["excluded_evidence"]} == {
        "not_eligible_for_candidate_bayesian"
    }


def test_bs1_cannot_be_forged_as_catalogued_evidence():
    ba1 = {
        **_row("ba1", "BA1"),
        "assessment_status": "not_met",
        "system_preview_included": False,
    }
    bs1 = _row("bs1", "BS1")

    resolved = _resolve([ba1, bs1])

    assert resolved["compatible_evidence"] == []
    assert all(
        row["reason"] == "not_eligible_for_candidate_bayesian"
        for row in resolved["excluded_evidence"]
    )


def test_duplicate_criterion_keeps_stronger_card_independent_of_input_order():
    supporting = _row("supporting", "PS3", strength="PS3_Supporting")
    strong = _row("strong", "PS3", strength="PS3")

    resolved = _resolve([supporting, strong])

    assert resolved["compatible_evidence"] == [strong]
    assert resolved["excluded_evidence"][0]["reason"] == "duplicate_criterion"


def test_shared_source_fact_is_not_multiplied_across_criteria():
    first = _row("ps2", "PS2", source_fact_ids=["fact-1"])
    second = _row("ps3", "PS3", source_fact_ids=["fact-1"])

    resolved = _resolve([first, second])

    assert len(resolved["compatible_evidence"]) == 1
    assert resolved["excluded_evidence"][0]["reason"] == "shared_source_fact"


def test_versioned_walker_bp4_bp7_pair_may_share_spliceai_source_fact():
    shared = "acmg-source:v1:walker"
    bp4 = _row("walker-bp4", "BP4", strength="BP4_Supporting", source_fact_ids=[shared])
    bp4.update(
        rule_id="clingen-svi-walker-spliceai-pp3-bp4",
        rule_version="2023.1",
    )
    bp7 = _row("walker-bp7", "BP7", strength="BP7_Supporting", source_fact_ids=[shared])
    bp7.update(rule_id="clingen-svi-walker-bp7", rule_version="2023.1")

    resolved = resolve_evidence_compatibility(
        [bp4, bp7], trusted_source_fact_ids={shared}
    )

    assert {row["criterion"] for row in resolved["compatible_evidence"]} == {
        "BP4",
        "BP7",
    }


def test_overlapping_clinical_cases_are_not_independent_across_criteria():
    first = _row("ps2", "PS2", source_case_ids=["case-1"])
    second = _row("pm6", "PM6", source_case_ids=["case-1"])

    resolved = _resolve([first, second])

    assert len(resolved["compatible_evidence"]) == 1
    assert resolved["excluded_evidence"][0]["reason"] == ("overlapping_clinical_case")


def test_same_assay_instance_is_not_multiplied_across_criteria():
    first = _row("ps3", "PS3", assay_instance_id="assay-1")
    second = _row("bs3", "BS3", assay_instance_id="assay-1")

    resolved = _resolve([first, second])

    assert len(resolved["compatible_evidence"]) == 1
    assert resolved["excluded_evidence"][0]["reason"] == "duplicate_assay_instance"
    assert resolved["excluded_evidence"][0]["system_preview_included"] is False


def test_conflicting_independent_functional_assays_both_exit_bayesian():
    pathogenic = _row("ps3", "PS3", assay_instance_id="assay-path")
    benign = _row("bs3", "BS3", assay_instance_id="assay-benign")

    resolved = _resolve([pathogenic, benign])

    assert resolved["compatible_evidence"] == []
    assert {row["reason"] for row in resolved["excluded_evidence"]} == {
        "unresolved_directional_conflict"
    }
    assert all(
        row["system_preview_included"] is False
        for row in resolved["excluded_evidence"]
    )
