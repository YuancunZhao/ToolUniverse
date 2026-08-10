"""Evidence compatibility resolution before v3 Bayesian multiplication."""

from __future__ import annotations

from tooluniverse.acmg.compatibility import resolve_evidence_compatibility
from tooluniverse.acmg.rule_catalog import rule_for_criterion


def _row(card_id: str, criterion: str, source_pmid: str | None = None, **extra):
    rule = rule_for_criterion(criterion)
    row = {
        "card_id": card_id,
        "criterion": criterion,
        "strength": f"{criterion}_Supporting",
        "evidence_status": "rule_mapped",
        "strength_source": "versioned_rule",
        "rule_source": {"type": "versioned_svi"},
        "verification_dimensions": {
            "identity_status": "matched",
            "source_status": "available",
            "extraction_status": "structured",
            "version_status": "versioned",
            "disease_match_status": "matched",
            "independence_status": "independent",
        },
        "calculation_roles": {
            "automatic": True,
            "verified": True,
            "user_selected": False,
        },
        "source_fact_ids": [f"{card_id}-fact"],
        "source_pmid": source_pmid,
        "rule_id": rule["rule_id"],
        "rule_version": rule["version"],
    }
    row.update(extra)
    return row


def _resolve(rows):
    known = {
        fact_id
        for row in rows
        for fact_id in row.get("source_fact_ids", [])
        if isinstance(fact_id, str)
    }
    return resolve_evidence_compatibility(
        rows,
        known_source_fact_ids=known,
        eligibility="automatic",
        calculation_role="automatic",
    )


def test_exact_duplicate_card_is_included_once():
    row = _row("same", "PP3")
    resolved = _resolve([row, dict(row)])
    assert [item["card_id"] for item in resolved["compatible_evidence"]] == ["same"]
    assert resolved["excluded_evidence"][0]["reason"] == "duplicate_card_id"


def test_same_criterion_and_overlapping_cases_are_not_multiplied():
    resolved = _resolve(
        [
            _row("a", "PS2", source_case_ids=["case-1", "case-2"]),
            _row("b", "PS2", source_case_ids=["case-2", "case-3"]),
        ]
    )
    assert len(resolved["compatible_evidence"]) == 1
    assert resolved["excluded_evidence"][0]["reason"] == "overlapping_cases"


def test_hard_identity_error_is_excluded():
    row = _row("a", "PP3")
    row["verification_dimensions"]["identity_status"] = "conflict"
    resolved = _resolve([row])
    assert resolved["compatible_evidence"] == []
    assert resolved["excluded_evidence"][0]["reason"] == (
        "not_eligible_for_candidate_bayesian"
    )


def test_dynamic_cspec_mutual_exclusion_is_enforced():
    pp3 = _row(
        "pp3",
        "PP3",
        observed_facts={"cspec_contract_applied": {"mutually_exclusive_with": ["BP4"]}},
    )
    bp4 = _row("bp4", "BP4")
    resolved = _resolve([pp3, bp4])
    assert len(resolved["compatible_evidence"]) == 1
    assert resolved["excluded_evidence"][0]["reason"] == (
        "cspec_mutually_exclusive_criteria"
    )


def test_duplicate_criterion_keeps_stronger_card_independent_of_input_order():
    supporting = _row("supporting", "PS3", strength="PS3_Supporting")
    strong = _row("strong", "PS3", strength="PS3")
    resolved = _resolve([supporting, strong])
    assert resolved["compatible_evidence"] == [strong]
    assert resolved["excluded_evidence"][0]["reason"] == "duplicate_criterion"


def test_shared_source_fact_is_not_multiplied_across_criteria():
    resolved = _resolve(
        [
            _row("ps2", "PS2", source_fact_ids=["fact-1"]),
            _row("ps3", "PS3", source_fact_ids=["fact-1"]),
        ]
    )
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
    resolved = _resolve([bp4, bp7])
    assert {row["criterion"] for row in resolved["compatible_evidence"]} == {
        "BP4",
        "BP7",
    }


def test_overlapping_clinical_cases_are_not_independent_across_criteria():
    resolved = _resolve(
        [
            _row("ps2", "PS2", source_case_ids=["case-1"]),
            _row("pm6", "PM6", source_case_ids=["case-1"]),
        ]
    )
    assert len(resolved["compatible_evidence"]) == 1
    assert resolved["excluded_evidence"][0]["reason"] == "overlapping_clinical_case"


def test_same_assay_instance_is_not_multiplied_across_criteria():
    resolved = _resolve(
        [
            _row("ps3", "PS3", assay_instance_id="assay-1"),
            _row("bs3", "BS3", assay_instance_id="assay-1"),
        ]
    )
    assert len(resolved["compatible_evidence"]) == 1
    assert resolved["excluded_evidence"][0]["reason"] == "duplicate_assay_instance"


def test_conflicting_independent_functional_assays_both_exit_bayesian():
    resolved = _resolve(
        [
            _row("ps3", "PS3", assay_instance_id="assay-path"),
            _row("bs3", "BS3", assay_instance_id="assay-benign"),
        ]
    )
    assert resolved["compatible_evidence"] == []
    assert {row["reason"] for row in resolved["excluded_evidence"]} == {
        "unresolved_directional_conflict"
    }


def test_rule_scenarios_do_not_mix():
    first = _row("scenario-a", "PM2", scenario_id="vcep:a")
    second = _row("scenario-b", "PP3", scenario_id="vcep:b")
    resolved = _resolve([first, second])
    assert len(resolved["compatible_evidence"]) == 1
    assert resolved["excluded_evidence"][0]["reason"] == "cross_scenario_rule_mix"
