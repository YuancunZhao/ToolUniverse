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


def _case_threshold_met(
    contract: dict[str, Any], case_count: float | None
) -> bool | None:
    threshold = _finite(contract.get("case_count_threshold"))
    if threshold is None:
        return None
    if case_count is None:
        return False
    operator = str(contract.get("operator") or ">=")
    return {
        ">=": case_count >= threshold,
        ">": case_count > threshold,
        "<=": case_count <= threshold,
        "<": case_count < threshold,
    }.get(operator, False)


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
    contract_executable = bool(
        contract
        and (
            contract.get("verification") == "compiled_hash_verified"
            or contract.get("deterministic_parse_status") == "parsed"
            or not contract.get("source_text")
        )
    )
    for fact in case_control_facts or []:
        if not isinstance(fact, dict):
            continue
        fact_id = str(fact.get("fact_id") or "")
        fact_type = str(fact.get("fact_type") or "case_control")
        duplicate_fact = bool(fact_id and fact_id in seen)
        valid_identity = (
            bool(expected_variant and expected_gene)
            and str(fact.get("variant_identity") or "").casefold()
            == expected_variant.casefold()
            and str(fact.get("gene") or "").casefold() == expected_gene.casefold()
        )
        strength = _suggested_strength(fact, contract if contract_executable else {})
        anchor_status = str(fact.get("anchor_status") or "unavailable")
        semantic_status = str(fact.get("semantic_status") or "unresolved")
        document_truncated = fact.get("document_truncated") is True
        reason = ""
        if not fact_id:
            reason = "PS4: fact_id is required for deduplication"
        elif duplicate_fact:
            reason = "PS4: duplicate fact_id was not assessed twice"
        elif not valid_identity:
            reason = "PS4: fact identity does not match the assessed variant"
        elif fact.get("evidence_verified") is False:
            reason = "PS4: source fact was not independently verified"
        elif semantic_status == "contradicted":
            reason = "PS4: submitted values contradict the cited source"
        elif anchor_status == "mismatch":
            reason = "PS4: the cited source does not match the submitted identity"
        elif fact.get("source_available") is False:
            reason = (
                "PS4: source-backed case evidence requires further full-text or "
                "semantic verification"
            )
        elif not strength:
            reason = "PS4: no valid strength could be mapped"
        elif fact_type == "case_control":
            odds_ratio = _finite(fact.get("odds_ratio"))
            ci_lower = _finite(fact.get("ci_lower"))
            if odds_ratio is None or ci_lower is None:
                reason = (
                    "PS4: numeric odds ratio and lower confidence bound are required"
                )
            elif odds_ratio > 1.0 and ci_lower > 1.0:
                reason = (
                    "PS4: anchored case-control enrichment supports a review proposal"
                )
            else:
                strength = "not_met"
                reason = "PS4: case-control enrichment does not exclude the null"
        elif fact_type == "case_series":
            case_count = _finite(fact.get("case_count"))
            threshold_met = _case_threshold_met(
                contract if contract_executable else {}, case_count
            )
            if threshold_met is False:
                strength = "not_met"
                reason = (
                    "PS4: case-series count does not meet the parsed CSpec threshold"
                )
            elif not case_count or fact.get("cases_independent") is not True:
                reason = "PS4: an independent case series is required"
            else:
                reason = "PS4: anchored independent case series supports user review"
        else:
            reason = f"PS4: unsupported fact type {fact_type}"
        seen.add(fact_id)
        dynamic = contract_executable
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
        source_backed_suggestion = bool(
            fact_id
            and not duplicate_fact
            and valid_identity
            and strength
            and anchor_status != "mismatch"
            and semantic_status != "contradicted"
        )
        missing_requirements: list[str] = []
        if anchor_status != "verified":
            missing_requirements.append("identity-bound full-text anchor")
        if semantic_status == "unresolved":
            missing_requirements.append("semantically verified extracted values")
        if document_truncated:
            missing_requirements.append("complete untruncated full-text retrieval")
        extraction_method = str(fact.get("extraction_method") or "")
        strict_mapping = bool(
            source_backed_suggestion
            and anchor_status == "verified"
            and semantic_status == "verified"
            and fact.get("source_available") is not False
            and not document_truncated
            and extraction_method in {"structured", "rule_extracted"}
        )
        evidence_status = (
            "excluded"
            if duplicate_fact
            or anchor_status == "mismatch"
            or semantic_status == "contradicted"
            else "not_met"
            if strength == "not_met"
            else "rule_mapped"
            if strict_mapping
            else "source_backed_candidate"
            if source_backed_suggestion
            else "excluded"
        )
        caveats = (
            []
            if dynamic
            else [
                "No uniquely applicable disease-specific PS4 threshold was "
                "available; the proposed strength uses general SVI review."
            ]
        )
        if document_truncated:
            caveats.append(
                "The retrieved document was truncated; this proposal is excluded "
                "from the verified estimate."
            )
        cards.append(
            EvidenceCard(
                criterion="PS4",
                strength=strength or "not_assessed",
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
                    [str(fact["source_fact_id"])] if fact.get("source_fact_id") else []
                ),
                evidence_status=evidence_status,
                exclusion_reason=reason if evidence_status == "excluded" else "",
                strength_source=(
                    "dynamic_cspec" if dynamic else "acmg_2015_default_candidate"
                ),
                rule_source={
                    "type": "dynamic_cspec" if dynamic else "generic_acmg_candidate",
                    "rule_id": rule_id or "acmg-2015-ps4-candidate",
                    "version": rule_version or "2026-08-08-v3",
                },
                rule_id=rule_id,
                rule_version=rule_version,
                rule_reference=(
                    str(rule_override.get("primary_reference") or "")
                    if dynamic and isinstance(rule_override, dict)
                    else ""
                ),
                origin=(
                    "deterministic_svi"
                    if extraction_method in {"structured", "rule_extracted"}
                    else "llm_literature"
                ),
                llm_suggestion=dict(fact.get("llm_suggestion") or {}),
                caveats=caveats,
                missing_requirements=missing_requirements,
                verification_dimensions={
                    "identity_status": (
                        "conflict"
                        if anchor_status == "mismatch"
                        else "matched"
                        if valid_identity
                        else "partial"
                    ),
                    "source_status": (
                        "unavailable"
                        if anchor_status == "unavailable"
                        else str(fact.get("source_status") or "available")
                    ),
                    "extraction_status": (
                        "contradicted"
                        if semantic_status == "contradicted"
                        else extraction_method
                        if extraction_method
                        in {"structured", "rule_extracted", "llm_extracted"}
                        else "unresolved"
                    ),
                    "version_status": (
                        "versioned" if fact.get("document_hash") else "unversioned"
                    ),
                    "disease_match_status": str(
                        fact.get("disease_match_status") or "unspecified"
                    ),
                    "independence_status": (
                        "independent"
                        if fact.get("cases_independent") is True
                        else "overlapping"
                        if fact.get("confirmed_overlap") is True
                        else "unknown"
                    ),
                },
                correlation_keys={
                    "case_id": [str(fact.get("case_id"))]
                    if fact.get("case_id")
                    else [],
                    "cohort_id": [str(fact.get("cohort_id"))]
                    if fact.get("cohort_id")
                    else [],
                },
            )
        )
    return cards


__all__ = ["literature_evidence"]
