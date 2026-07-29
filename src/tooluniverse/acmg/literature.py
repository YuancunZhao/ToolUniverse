"""Document-backed PS4 evidence proposals."""

from __future__ import annotations

import math
from typing import Any

from .models import EvidenceCard
from .rule_catalog import is_valid_strength_for_criterion


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _ps4_contract(rule_override: dict[str, Any] | None) -> dict[str, Any]:
    criteria = (
        rule_override.get("criteria") if isinstance(rule_override, dict) else None
    )
    contract = criteria.get("PS4") if isinstance(criteria, dict) else None
    return dict(contract) if isinstance(contract, dict) else {}


def _suggested_strength(fact: dict[str, Any], contract: dict[str, Any]) -> str:
    for value in (
        contract.get("strength"),
        fact.get("suggested_strength"),
        "PS4"
        if str(fact.get("fact_type") or "case_control") == "case_control"
        else "PS4_Supporting",
    ):
        strength = str(value or "")
        if is_valid_strength_for_criterion("PS4", strength):
            return strength
    return ""


def literature_evidence(
    case_control_facts: list[dict[str, Any]] | None = None,
    expected_variant: str = "",
    expected_gene: str = "",
    rule_override: dict[str, Any] | None = None,
) -> list[EvidenceCard]:
    """Map anchored case-control or case-series facts onto one PS4 proposal."""
    cards: list[EvidenceCard] = []
    seen: set[str] = set()
    contract = _ps4_contract(rule_override)
    for fact in case_control_facts or []:
        if not isinstance(fact, dict):
            continue
        fact_id = str(fact.get("fact_id") or "")
        fact_type = str(fact.get("fact_type") or "case_control")
        valid_identity = (
            bool(expected_variant and expected_gene)
            and str(fact.get("variant_identity") or "").casefold()
            == expected_variant.casefold()
            and str(fact.get("gene") or "").casefold() == expected_gene.casefold()
        )
        strength = _suggested_strength(fact, contract)
        assessment_status = "not_assessed"
        proposal_status = "insufficient_information"
        reason = ""
        if not fact_id:
            reason = "PS4: fact_id is required for deduplication"
        elif fact_id in seen:
            reason = "PS4: duplicate fact_id was not assessed twice"
        elif not valid_identity:
            reason = "PS4: fact identity does not match the assessed variant"
        elif fact.get("evidence_verified") is False:
            reason = "PS4: source fact was not independently verified"
        elif fact.get("assessment_ready") is False:
            reason = (
                "PS4: full-text identity, anchor, or semantic verification failed"
            )
        elif not strength:
            reason = "PS4: no valid strength could be mapped"
        elif fact_type == "case_control":
            odds_ratio = _finite(fact.get("odds_ratio"))
            ci_lower = _finite(fact.get("ci_lower"))
            if odds_ratio is None or ci_lower is None:
                reason = "PS4: numeric odds ratio and lower confidence bound are required"
            elif odds_ratio > 1.0 and ci_lower > 1.0:
                assessment_status = "met"
                proposal_status = "requires_user_review"
                reason = (
                    "PS4: anchored case-control enrichment supports a review proposal"
                )
            else:
                assessment_status = "not_met"
                proposal_status = "not_suggested"
                strength = "not_met"
                reason = "PS4: case-control enrichment does not exclude the null"
        elif fact_type == "case_series":
            case_count = _finite(fact.get("case_count"))
            if not case_count or fact.get("cases_independent") is not True:
                reason = "PS4: an independent case series is required"
            else:
                assessment_status = "met"
                proposal_status = "requires_user_review"
                reason = "PS4: anchored independent case series supports user review"
        else:
            reason = f"PS4: unsupported fact type {fact_type}"
        seen.add(fact_id)
        dynamic = bool(contract)
        rule_id = (
            str(rule_override.get("rule_id") or "")
            if dynamic and isinstance(rule_override, dict)
            else ""
        )
        rule_version = (
            str(rule_override.get("version") or "")
            if dynamic and isinstance(rule_override, dict)
            else ""
        )
        cards.append(
            EvidenceCard(
                criterion="PS4",
                strength=strength or "not_assessed",
                assessment_status=assessment_status,
                input_source="Document-backed case evidence",
                input_values=dict(fact),
                clinvar_rule_applied=(
                    str(rule_override.get("primary_reference") or "")
                    if dynamic and isinstance(rule_override, dict)
                    else "ACMG/AMP PS4; strength requires user review"
                ),
                provenance_chain=[reason],
                source_pmid=str(fact.get("pmid") or "") or None,
                source_pmids=[
                    str(value)
                    for value in (fact.get("pmid"), fact.get("pmcid"))
                    if value
                ],
                source_case_ids=[
                    str(value)
                    for value in (
                        fact.get("cohort_id"),
                        fact.get("case_id"),
                        fact_id,
                    )
                    if value
                ],
                source_fact_ids=(
                    [str(fact["source_fact_id"])]
                    if fact.get("source_fact_id")
                    else []
                ),
                proposal_origin="llm_literature",
                proposal_status=proposal_status,
                rule_id=rule_id,
                rule_version=rule_version,
                rule_reference=(
                    str(rule_override.get("primary_reference") or "")
                    if dynamic and isinstance(rule_override, dict)
                    else ""
                ),
                rule_verification=(
                    "dynamic_cspec_llm"
                    if contract.get("verification") == "dynamic_cspec_llm"
                    else "dynamic_cspec_structured"
                    if dynamic
                    else "generic_svi"
                ),
                rule_mapping_status=(
                    "dynamic_cspec_structured"
                    if dynamic
                    else "llm_review_required"
                ),
                llm_suggestion=dict(fact.get("llm_suggestion") or {}),
                caveats=(
                    []
                    if dynamic
                    else [
                        "No uniquely applicable disease-specific PS4 threshold was "
                        "available; the proposed strength uses general SVI review."
                    ]
                ),
            )
        )
    if not cards:
        cards.append(
            EvidenceCard(
                criterion="PS4",
                strength="not_assessed",
                assessment_status="not_assessed",
                input_source="Document-backed case evidence",
                input_values={},
                clinvar_rule_applied="ACMG/AMP PS4",
                provenance_chain=[
                    "PS4: no verified case-control or case-series facts were supplied"
                ],
                rule_mapping_status="unmapped",
            )
        )
    return cards


__all__ = ["literature_evidence"]
