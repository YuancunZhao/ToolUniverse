"""Resolve duplicate and correlated evidence before Bayesian estimation."""

from __future__ import annotations

from typing import Any

from .models import is_automatic_evidence, is_verified_evidence


COMPATIBILITY_POLICY_VERSION = "2026-08-08-v3"


def _criterion(row: dict[str, Any]) -> str:
    return str(row.get("criterion") or "")


def _strength_rank(row: dict[str, Any]) -> int:
    strength = str(row.get("strength") or "")
    if "VeryStrong" in strength or strength in {"PVS1", "BA1"}:
        return 4
    if "Strong" in strength:
        return 3
    if "Moderate" in strength:
        return 2
    if "Supporting" in strength:
        return 1
    if strength.startswith(("PS", "BS")):
        return 3
    if strength.startswith("PM"):
        return 2
    if strength.startswith(("PP", "BP")):
        return 1
    return 0


def _evidence_priority(row: dict[str, Any]) -> int:
    return {
        "expert_panel_applied": 3,
        "rule_mapped": 2,
        "source_backed_candidate": 1,
    }.get(str(row.get("evidence_status") or ""), 0)


def _semantic_ids(row: dict[str, Any], key: str) -> set[str]:
    values: list[Any] = [row.get(key)]
    for container_key in ("observed_facts", "input_values"):
        container = row.get(container_key)
        if isinstance(container, dict):
            values.append(container.get(key))
    normalized: set[str] = set()
    for value in values:
        if isinstance(value, (list, tuple, set)):
            normalized.update(str(item) for item in value if item)
        elif value:
            normalized.add(str(value))
    return normalized


def _contract_exclusions(row: dict[str, Any]) -> set[str]:
    for container_key in ("observed_facts", "input_values"):
        container = row.get(container_key)
        if not isinstance(container, dict):
            continue
        contract = container.get("cspec_contract_applied")
        if isinstance(contract, dict):
            return {
                str(value)
                for value in contract.get("mutually_exclusive_with") or []
                if value
            }
    return set()


def _is_walker_bp4_bp7_pair(current: dict[str, Any], accepted: dict[str, Any]) -> bool:
    """Allow the explicit Walker BP4 -> BP7 decision-tree combination only."""
    rows = {_criterion(current): current, _criterion(accepted): accepted}
    if set(rows) != {"BP4", "BP7"}:
        return False
    return (
        rows["BP4"].get("rule_id") == "clingen-svi-walker-spliceai-pp3-bp4"
        and rows["BP7"].get("rule_id") == "clingen-svi-walker-bp7"
        and rows["BP4"].get("rule_version") == "2023.1"
        and rows["BP7"].get("rule_version") == "2023.1"
    )


def resolve_evidence_compatibility(
    rows: list[dict[str, Any]],
    *,
    verified_source_fact_ids: set[str] | None = None,
    known_source_fact_ids: set[str] | None = None,
    eligibility: str = "verified",
    calculation_role: str = "automatic",
    scenario_id: str | None = None,
) -> dict[str, Any]:
    compatible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    accepted_criteria: set[str] = set()
    clinical_criteria = {
        "PS1",
        "PS2",
        "PS4",
        "PM3",
        "PM5",
        "PM6",
        "PP1",
        "PP4",
        "BS2",
        "BS4",
        "BP2",
        "BP5",
    }

    ordered_rows = sorted(
        enumerate(rows),
        key=lambda item: (
            -_evidence_priority(item[1]),
            -_strength_rank(item[1]),
            item[0],
        ),
    )
    accepted_non_generic_scenarios: set[str] = set()
    for _index, row in ordered_rows:
        row_scenario = str(row.get("scenario_id") or "generic-svi")
        if scenario_id is not None and row_scenario != scenario_id:
            excluded.append({**row, "reason": "different_rule_scenario"})
            continue
        if (
            scenario_id is None
            and row_scenario != "generic-svi"
            and accepted_non_generic_scenarios
            and row_scenario not in accepted_non_generic_scenarios
        ):
            excluded.append({**row, "reason": "cross_scenario_rule_mix"})
            continue
        eligible = (
            is_automatic_evidence(row, known_source_fact_ids=known_source_fact_ids)
            if eligibility == "automatic"
            else is_verified_evidence(
                row, verified_source_fact_ids=verified_source_fact_ids
            )
        )
        if not eligible:
            excluded.append({**row, "reason": "not_eligible_for_candidate_bayesian"})
            continue
        card_id = str(row.get("card_id") or "")
        if card_id and card_id in seen_ids:
            excluded.append({**row, "reason": "duplicate_card_id"})
            continue

        criterion = _criterion(row)
        case_ids = {str(value) for value in row.get("source_case_ids", []) if value}
        assay_ids = _semantic_ids(row, "assay_instance_id")
        family_ids = _semantic_ids(row, "family_id")
        cohort_ids = _semantic_ids(row, "cohort_id")
        prior_variant_ids = _semantic_ids(row, "prior_variant_identity")
        pmids = {
            str(value)
            for value in [row.get("source_pmid"), *row.get("source_pmids", [])]
            if value
        }
        reason = ""
        for accepted in compatible:
            accepted_criterion = _criterion(accepted)
            accepted_fact_ids = {
                str(value) for value in accepted.get("source_fact_ids", []) if value
            }
            current_fact_ids = {
                str(value) for value in row.get("source_fact_ids", []) if value
            }
            if (
                current_fact_ids
                and accepted_fact_ids
                and current_fact_ids & accepted_fact_ids
                and not _is_walker_bp4_bp7_pair(row, accepted)
            ):
                reason = "shared_source_fact"
                break

            if accepted_criterion in _contract_exclusions(
                row
            ) or criterion in _contract_exclusions(accepted):
                reason = "cspec_mutually_exclusive_criteria"
                break
            accepted_assay_ids = _semantic_ids(accepted, "assay_instance_id")
            if assay_ids and accepted_assay_ids and assay_ids & accepted_assay_ids:
                reason = "duplicate_assay_instance"
                break
            accepted_family_ids = _semantic_ids(accepted, "family_id")
            if family_ids and accepted_family_ids and family_ids & accepted_family_ids:
                reason = "duplicate_family"
                break
            accepted_cohort_ids = _semantic_ids(accepted, "cohort_id")
            if cohort_ids and accepted_cohort_ids and cohort_ids & accepted_cohort_ids:
                reason = "overlapping_cohort"
                break
            accepted_prior_variant_ids = _semantic_ids(
                accepted, "prior_variant_identity"
            )
            if (
                prior_variant_ids
                and accepted_prior_variant_ids
                and prior_variant_ids & accepted_prior_variant_ids
            ):
                reason = "duplicate_prior_variant"
                break
            if (
                accepted_criterion == criterion
                and case_ids
                and accepted.get("source_case_ids")
            ):
                if case_ids & {
                    str(value) for value in accepted.get("source_case_ids", []) if value
                }:
                    reason = "overlapping_cases"
                    break
            if (
                criterion in clinical_criteria
                and accepted_criterion in clinical_criteria
                and accepted_criterion != criterion
                and case_ids
                and accepted.get("source_case_ids")
                and case_ids
                & {str(value) for value in accepted.get("source_case_ids", []) if value}
            ):
                reason = "overlapping_clinical_case"
                break

            if accepted_criterion != criterion:
                continue
            accepted_pmids = {
                str(value)
                for value in [
                    accepted.get("source_pmid"),
                    *accepted.get("source_pmids", []),
                ]
                if value
            }
            if pmids and accepted_pmids and pmids & accepted_pmids:
                reason = "same_source_same_criterion"
                break
            if criterion in {"PP3", "BP4", "PP3/BP4"}:
                reason = "correlated_computational_evidence"
                break
        if reason:
            excluded.append(
                {
                    **row,
                    "reason": reason,
                    **(
                        {"role": "corroborating"}
                        if accepted_criterion == criterion
                        else {}
                    ),
                }
            )
            continue
        if criterion in accepted_criteria:
            excluded.append(
                {
                    **row,
                    "reason": "duplicate_criterion",
                    "role": "corroborating",
                }
            )
            continue
        compatible.append(row)
        if row_scenario != "generic-svi":
            accepted_non_generic_scenarios.add(row_scenario)
        accepted_criteria.add(criterion)
        if card_id:
            seen_ids.add(card_id)

    criteria = {_criterion(row) for row in compatible}
    conflicting_pairs = ({"PP3", "BP4"}, {"PS3", "BS3"})
    for pair in conflicting_pairs:
        if not pair <= criteria:
            continue
        retained = []
        for row in compatible:
            if _criterion(row) in pair:
                excluded.append({**row, "reason": "unresolved_directional_conflict"})
            else:
                retained.append(row)
        compatible = retained

    for row in excluded:
        roles = row.get("calculation_roles")
        roles = dict(roles) if isinstance(roles, dict) else {}
        roles[calculation_role] = False
        row["calculation_roles"] = roles
        row["exclusion_reason"] = row.get("reason") or row.get("exclusion_reason")
    return {
        "compatible_evidence": compatible,
        "excluded_evidence": excluded,
        "decisions": [
            {
                "card_id": row.get("card_id"),
                "criterion": _criterion(row),
                "decision": "excluded",
                "reason": row.get("reason"),
            }
            for row in excluded
        ],
    }


__all__ = ["resolve_evidence_compatibility"]
