"""Shared data contracts for deterministic ACMG evidence rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any

from .rule_catalog import (
    generic_bayesian_odds_for,
    rule_allows_system_preview_strength,
    rule_for_criterion,
    rule_for_output,
)


ASSESSMENT_STATUSES = {
    "met",
    "not_met",
    "indeterminate",
    "not_assessed",
    "not_applicable",
    "deprecated",
}

PROPOSAL_STATUSES = {
    "suggested",
    "not_suggested",
    "requires_user_review",
    "insufficient_information",
    "not_applicable",
    "deprecated",
}


@dataclass
class EvidenceCard:
    criterion: str
    strength: str
    input_source: str
    input_values: dict[str, Any]
    clinvar_rule_applied: str
    card_id: str = ""
    assessment_status: str = ""
    # Public group tools produce review cards. The collector promotes cards only
    # after it has validated the referenced SourceFacts.
    overlay_validated: bool = False
    rule_id: str = ""
    rule_version: str = ""
    rule_reference: str = ""
    variant_identity: dict[str, Any] = field(default_factory=dict)
    provenance_chain: list[str] = field(default_factory=list)
    source_pmid: str | None = None
    source_pmids: list[str] = field(default_factory=list)
    source_case_ids: list[str] = field(default_factory=list)
    source_fact_ids: list[str] = field(default_factory=list)
    observed_facts: dict[str, Any] = field(default_factory=dict)
    suggested_criterion: str = ""
    suggested_strength: str = ""
    rule_basis: str = ""
    exclusion_reason: str = ""
    proposal_origin: str = "deterministic_svi"
    proposal_status: str = ""
    rule_verification: str = ""
    rule_mapping_status: str = ""
    llm_suggestion: dict[str, Any] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)
    system_preview_included: bool = False
    user_decision: str = "pending"
    effective_strength: str = ""
    user_selected_included: bool = False
    decision_reason: str = ""


@dataclass(frozen=True)
class SourceFact:
    """Normalized, traceable source data consumed by an ACMG rule."""

    fact_id: str
    tool_name: str
    status: str
    query_identity: dict[str, Any]
    result_identity: dict[str, Any]
    identity_verified: bool
    features: dict[str, Any]
    raw_result_hash: str
    provider_version: str = ""
    request_arguments: dict[str, Any] = field(default_factory=dict)
    provenance: tuple[str, ...] = ()
    excerpt: str = ""
    locator: str = ""
    assessment_ready: bool = False
    verification_level: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assessment_status_for_strength(strength: str, criterion: str = "") -> str:
    normalized = str(strength or "").strip()
    if normalized == "not_met":
        return "not_met"
    if normalized in {"", "none", "not_assessed", "insufficient_evidence"}:
        return "not_assessed"
    if normalized == "indeterminate":
        return "indeterminate"
    if normalized == "not_applicable":
        return "not_applicable"
    if normalized == "deprecated":
        return "deprecated"
    if criterion and not rule_for_criterion(criterion):
        return "not_assessed"
    return "met"


def _source_fact_ids(value: Any) -> set[str] | None:
    """Normalize source IDs and reject caller-controlled non-string values."""
    if not isinstance(value, (list, tuple, set)) or not value:
        return None
    normalized = {
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    }
    return normalized if len(normalized) == len(value) else None


def _default_proposal_status(assessment_status: str) -> str:
    return {
        "met": "suggested",
        "not_met": "not_suggested",
        "indeterminate": "insufficient_information",
        "not_assessed": "insufficient_information",
        "not_applicable": "not_applicable",
        "deprecated": "deprecated",
    }.get(assessment_status, "insufficient_information")


def _proposal_strength_supported(
    criterion: str,
    strength: str,
    *,
    rule_id: str = "",
    rule_version: str = "",
    allow_generic: bool = True,
) -> bool:
    return bool(
        rule_allows_system_preview_strength(
            criterion,
            strength,
            rule_id=rule_id,
            rule_version=rule_version,
        )
        or (
            allow_generic
            and (
                generic_bayesian_odds_for(criterion, strength) is not None
                or (criterion == "BA1" and strength == "BA1")
            )
        )
    )


def is_candidate_evidence(
    row: EvidenceCard | dict[str, Any],
    *,
    trusted_source_fact_ids: set[str] | None = None,
) -> bool:
    """Return whether a rule suggestion may enter the review-only estimate."""
    if trusted_source_fact_ids is None:
        return False
    trusted_ids = {value for value in trusted_source_fact_ids if value}
    if isinstance(row, EvidenceCard):
        source_fact_ids = _source_fact_ids(row.source_fact_ids)
        proposal_status = row.proposal_status or _default_proposal_status(
            row.assessment_status
        )
        return bool(
            source_fact_ids
            and source_fact_ids <= trusted_ids
            and proposal_status in {"suggested", "requires_user_review"}
            and row.overlay_validated is True
            and _proposal_strength_supported(
                row.criterion,
                row.strength,
                rule_id=row.rule_id,
                rule_version=row.rule_version,
                allow_generic=row.rule_verification
                in {
                    "generic_svi",
                    "review_only",
                    "dynamic_cspec_structured",
                    "dynamic_cspec_llm",
                    "compiled_hash_verified",
                }
                or not (row.rule_id or row.rule_version),
            )
        )
    if not isinstance(row, dict):
        return False
    source_fact_ids = _source_fact_ids(row.get("source_fact_ids"))
    proposal_status = str(row.get("proposal_status") or "")
    return bool(
        source_fact_ids
        and source_fact_ids <= trusted_ids
        and (
            proposal_status in {"suggested", "requires_user_review"}
            or (not proposal_status and row.get("assessment_status") == "met")
        )
        and (
            row.get("system_preview_included") is True
        )
        and row.get("overlay_validated") is True
        and _proposal_strength_supported(
            str(row.get("criterion") or ""),
            str(row.get("effective_strength") or row.get("strength") or ""),
            rule_id=str(row.get("rule_id") or ""),
            rule_version=str(row.get("rule_version") or ""),
            allow_generic=str(row.get("rule_verification") or "")
            in {
                "generic_svi",
                "review_only",
                "dynamic_cspec_structured",
                "dynamic_cspec_llm",
                "compiled_hash_verified",
            }
            or str(row.get("user_decision") or "") == "modified"
        )
    )


def _stable_card_id(card: EvidenceCard, assessment_status: str) -> str:
    payload = {
        "variant_identity": card.variant_identity,
        "criterion": card.criterion,
        "strength": card.strength,
        "assessment_status": assessment_status,
        "input_source": card.input_source,
        "input_values": card.input_values,
        "rule_id": card.rule_id,
        "rule_version": card.rule_version,
        "rule_reference": card.rule_reference or card.clinvar_rule_applied,
        "source_pmid": card.source_pmid,
        "source_pmids": sorted(card.source_pmids),
        "source_case_ids": sorted(card.source_case_ids),
        "source_fact_ids": sorted(card.source_fact_ids),
        "rule_mapping_status": card.rule_mapping_status,
        "llm_suggestion": card.llm_suggestion,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]
    return f"acmg-card:v1:{digest}"


def evidence_cards_to_result(
    cards: list[EvidenceCard],
    *,
    variant_identity: dict[str, Any] | None = None,
    trusted_source_fact_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Serialize cards for system preview and user review."""
    serialized = []
    for card in cards:
        if variant_identity and not card.variant_identity:
            card.variant_identity = dict(variant_identity)
        rule = rule_for_output(
            card.criterion,
            rule_id=card.rule_id,
            rule_version=card.rule_version,
        ) if card.rule_id or card.rule_version else rule_for_criterion(card.criterion)
        if rule:
            card.rule_id = card.rule_id or str(rule["rule_id"])
            card.rule_version = card.rule_version or str(rule["version"])
            card.rule_reference = card.rule_reference or str(rule["primary_reference"])
        assessment_status = card.assessment_status or assessment_status_for_strength(
            card.strength, card.criterion
        )
        if assessment_status not in ASSESSMENT_STATUSES:
            assessment_status = "not_assessed"
        row = asdict(card)
        row["observed_facts"] = dict(card.observed_facts or card.input_values)
        row["suggested_criterion"] = card.suggested_criterion or card.criterion
        row["suggested_strength"] = card.suggested_strength or (
            card.strength if assessment_status == "met" else ""
        )
        row["rule_basis"] = (
            card.rule_basis or card.rule_reference or card.clinvar_rule_applied
        )
        row["assessment_status"] = assessment_status
        proposal_status = card.proposal_status or _default_proposal_status(
            assessment_status
        )
        if proposal_status not in PROPOSAL_STATUSES:
            proposal_status = "insufficient_information"
        row["proposal_status"] = proposal_status
        row["proposal_origin"] = card.proposal_origin or "deterministic_svi"
        exact_rule_strength = rule_allows_system_preview_strength(
            card.criterion,
            card.strength,
            rule_id=card.rule_id,
            rule_version=card.rule_version,
        )
        row["rule_verification"] = card.rule_verification or (
            "versioned_deterministic"
            if exact_rule_strength
            else "generic_svi"
            if _proposal_strength_supported(card.criterion, card.strength)
            else "review_only"
        )
        row["rule_mapping_status"] = card.rule_mapping_status or (
            "deterministic_mapped"
            if row["rule_verification"] == "versioned_deterministic"
            else "llm_review_required"
            if row["proposal_origin"] in {"llm_literature", "llm_cspec"}
            else "unmapped"
        )
        row["llm_suggestion"] = dict(card.llm_suggestion)
        row["caveats"] = list(card.caveats)
        row["missing_requirements"] = list(card.missing_requirements)
        row["user_decision"] = card.user_decision or "pending"
        row["effective_strength"] = card.effective_strength or card.strength
        row["user_selected_included"] = card.user_selected_included is True
        row["decision_reason"] = card.decision_reason
        row["card_id"] = _stable_card_id(card, assessment_status)
        has_trusted_sources = bool(card.source_fact_ids) and all(
            fact_id in (trusted_source_fact_ids or set())
            for fact_id in card.source_fact_ids
        )
        row["overlay_validated"] = (
            card.overlay_validated is True and has_trusted_sources
        )
        row["system_preview_included"] = (
            proposal_status in {"suggested", "requires_user_review"}
            and row["overlay_validated"]
            and _proposal_strength_supported(
                card.criterion,
                card.strength,
                rule_id=card.rule_id,
                rule_version=card.rule_version,
                allow_generic=row["rule_verification"]
                in {
                    "generic_svi",
                    "review_only",
                    "dynamic_cspec_structured",
                    "dynamic_cspec_llm",
                    "compiled_hash_verified",
                }
                and row["rule_mapping_status"] != "unmapped",
            )
        )
        if (
            proposal_status in {"suggested", "requires_user_review"}
            and not row["system_preview_included"]
        ):
            row["exclusion_reason"] = row.get("exclusion_reason") or (
                "suggestion_not_eligible_for_candidate_bayesian"
            )
        serialized.append(row)
    return {"evidence_cards": serialized}


__all__ = [
    "ASSESSMENT_STATUSES",
    "EvidenceCard",
    "PROPOSAL_STATUSES",
    "SourceFact",
    "assessment_status_for_strength",
    "evidence_cards_to_result",
    "is_candidate_evidence",
]
