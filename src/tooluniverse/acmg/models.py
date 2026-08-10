"""Shared ACMG v3 facts and evidence contracts.

Facts are never hidden merely because one verification dimension is incomplete.
Evidence display, automatic calculation, and strict calculation are independent
decisions derived from the dimensions below.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any

from .rule_catalog import (
    generic_bayesian_odds_for,
    rule_allows_verified_strength,
    rule_for_criterion,
    rule_for_output,
)


EVIDENCE_STATUSES = {
    "expert_panel_applied",
    "rule_mapped",
    "source_backed_candidate",
    "not_met",
    "excluded",
    "deprecated",
}
IDENTITY_STATUSES = {"matched", "partial", "conflict", "unknown"}
SOURCE_STATUSES = {
    "available",
    "abstract_only",
    "snippet_only",
    "unavailable",
    "failed",
}
EXTRACTION_STATUSES = {
    "structured",
    "rule_extracted",
    "llm_extracted",
    "unresolved",
    "contradicted",
}
VERSION_STATUSES = {"versioned", "unversioned", "stale"}
DISEASE_MATCH_STATUSES = {"matched", "candidate", "mismatch", "unspecified"}
INDEPENDENCE_STATUSES = {"independent", "overlapping", "unknown"}

AUTOMATIC_EVIDENCE_STATUSES = frozenset(
    {"expert_panel_applied", "rule_mapped", "source_backed_candidate"}
)
VERIFIED_EVIDENCE_STATUSES = frozenset({"expert_panel_applied", "rule_mapped"})
HARD_EXCLUSION_DIMENSIONS = {
    "identity_status": {"conflict"},
    "extraction_status": {"contradicted"},
    "disease_match_status": {"mismatch"},
    "independence_status": {"overlapping"},
}
AUTOMATIC_EVIDENCE_POLICY_VERSION = "2026-08-08-v3"
VERIFIED_EVIDENCE_POLICY_VERSION = "2026-08-08-v3"


@dataclass
class EvidenceCard:
    criterion: str
    strength: str
    input_source: str
    input_values: dict[str, Any]
    clinvar_rule_applied: str
    card_id: str = ""
    evidence_status: str = ""
    strength_source: str = ""
    rule_source: dict[str, Any] = field(default_factory=dict)
    verification_dimensions: dict[str, str] = field(default_factory=dict)
    calculation_roles: dict[str, bool] = field(default_factory=dict)
    correlation_keys: dict[str, list[str]] = field(default_factory=dict)
    scenario_id: str = "generic-svi"
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
    rule_basis: str = ""
    exclusion_reason: str = ""
    origin: str = "deterministic_svi"
    llm_suggestion: dict[str, Any] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)
    user_decision: str = "pending"
    decision_reason: str = ""


@dataclass(frozen=True)
class SourceFact:
    """Normalized, traceable source data; incomplete dimensions stay visible."""

    fact_id: str
    tool_name: str
    status: str
    query_identity: dict[str, Any]
    result_identity: dict[str, Any]
    features: dict[str, Any]
    raw_result_hash: str
    provider_version: str = ""
    request_arguments: dict[str, Any] = field(default_factory=dict)
    provenance: tuple[str, ...] = ()
    excerpt: str = ""
    locator: str = ""
    verification_level: str = ""
    identity_status: str = "unknown"
    source_status: str = "unavailable"
    extraction_status: str = "unresolved"
    version_status: str = "unversioned"
    disease_match_status: str = "unspecified"
    independence_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fact_identity_matches(fact: SourceFact) -> bool:
    return fact.identity_status == "matched"


def fact_is_available(fact: SourceFact) -> bool:
    return fact.status == "success" and fact.source_status in {
        "available",
        "abstract_only",
        "snippet_only",
    }


def fact_is_strictly_verified(fact: SourceFact) -> bool:
    extraction_verified = fact.extraction_status in {"structured", "rule_extracted"}
    if fact.extraction_status == "rule_extracted":
        extraction_verified = bool(
            str(fact.features.get("semantic_status") or "") == "verified"
            and str(fact.features.get("requirements_status") or "complete")
            == "complete"
            and str(fact.features.get("target_link_status") or "direct_variant")
            in {
                "direct_variant",
                "adjacent_explicit_referent",
                "direct_gene",
                "same_residue",
            }
            and str(fact.features.get("negation_status") or "not_negated")
            == "not_negated"
        )
    if fact.extraction_status == "llm_extracted":
        extraction_verified = bool(
            fact.verification_level == "host_verified"
            and str(fact.features.get("anchor_status") or "") == "verified"
            and str(fact.features.get("semantic_status") or "") == "verified"
            and str(fact.features.get("requirements_status") or "") == "complete"
            and str(fact.features.get("target_link_status") or "")
            in {
                "direct_variant",
                "adjacent_explicit_referent",
                "direct_gene",
                "same_residue",
            }
            and str(fact.features.get("negation_status") or "") == "not_negated"
        )
    return bool(
        fact_is_available(fact)
        and fact.identity_status == "matched"
        and fact.source_status == "available"
        and fact.features.get("document_truncated") is not True
        and extraction_verified
        and fact.version_status == "versioned"
        and fact.disease_match_status not in {"candidate", "mismatch"}
        and fact.independence_status != "overlapping"
    )


def _source_fact_ids(value: Any) -> set[str] | None:
    if not isinstance(value, (list, tuple, set)) or not value:
        return None
    normalized = {
        item.strip() for item in value if isinstance(item, str) and item.strip()
    }
    return normalized if len(normalized) == len(value) else None


def _strength_supported(
    criterion: str,
    strength: str,
    *,
    rule_id: str = "",
    rule_version: str = "",
) -> bool:
    return bool(
        rule_allows_verified_strength(
            criterion,
            strength,
            rule_id=rule_id,
            rule_version=rule_version,
        )
        or generic_bayesian_odds_for(criterion, strength) is not None
        or (criterion == "BA1" and strength == "BA1")
    )


def _dimensions_have_hard_error(dimensions: dict[str, Any]) -> bool:
    return any(
        str(dimensions.get(key) or "") in excluded
        for key, excluded in HARD_EXCLUSION_DIMENSIONS.items()
    )


def is_automatic_evidence(
    row: EvidenceCard | dict[str, Any],
    *,
    known_source_fact_ids: set[str] | None,
) -> bool:
    """Whether a source-backed card may enter the default automatic estimate."""
    if known_source_fact_ids is None:
        return False
    if isinstance(row, EvidenceCard):
        source_ids = _source_fact_ids(row.source_fact_ids)
        criterion = row.criterion
        strength = row.strength
        evidence_status = row.evidence_status
        dimensions = row.verification_dimensions
        rule_id = row.rule_id
        rule_version = row.rule_version
    elif isinstance(row, dict):
        source_ids = _source_fact_ids(row.get("source_fact_ids"))
        criterion = str(row.get("criterion") or "")
        strength = str(row.get("strength") or "")
        evidence_status = str(row.get("evidence_status") or "")
        dimensions = (
            row.get("verification_dimensions")
            if isinstance(row.get("verification_dimensions"), dict)
            else {}
        )
        rule_id = str(row.get("rule_id") or "")
        rule_version = str(row.get("rule_version") or "")
    else:
        return False
    return bool(
        source_ids
        and source_ids <= {value for value in known_source_fact_ids if value}
        and evidence_status in AUTOMATIC_EVIDENCE_STATUSES
        and not _dimensions_have_hard_error(dimensions)
        and _strength_supported(
            criterion,
            strength,
            rule_id=rule_id,
            rule_version=rule_version,
        )
    )


def is_verified_evidence(
    row: EvidenceCard | dict[str, Any],
    *,
    verified_source_fact_ids: set[str] | None,
) -> bool:
    """Whether a card may enter the strict verified comparison estimate."""
    if verified_source_fact_ids is None:
        return False
    if isinstance(row, EvidenceCard):
        source_ids = _source_fact_ids(row.source_fact_ids)
        evidence_status = row.evidence_status
        dimensions = row.verification_dimensions
        criterion = row.criterion
        strength = row.strength
        rule_id = row.rule_id
        rule_version = row.rule_version
        rule_source = row.rule_source
    elif isinstance(row, dict):
        source_ids = _source_fact_ids(row.get("source_fact_ids"))
        evidence_status = str(row.get("evidence_status") or "")
        dimensions = (
            row.get("verification_dimensions")
            if isinstance(row.get("verification_dimensions"), dict)
            else {}
        )
        criterion = str(row.get("criterion") or "")
        strength = str(row.get("strength") or "")
        rule_id = str(row.get("rule_id") or "")
        rule_version = str(row.get("rule_version") or "")
        rule_source = (
            row.get("rule_source") if isinstance(row.get("rule_source"), dict) else {}
        )
    else:
        return False
    return bool(
        source_ids
        and source_ids <= {value for value in verified_source_fact_ids if value}
        and evidence_status in VERIFIED_EVIDENCE_STATUSES
        and not _dimensions_have_hard_error(dimensions)
        and str(dimensions.get("source_status") or "available") == "available"
        and str(dimensions.get("extraction_status") or "structured")
        in {"structured", "rule_extracted"}
        and str(dimensions.get("version_status") or "versioned") == "versioned"
        and str(dimensions.get("disease_match_status") or "unspecified")
        not in {"candidate", "mismatch"}
        and str(rule_source.get("type") or "")
        in {
            "versioned_svi",
            "dynamic_cspec",
            "dynamic_cspec_structured",
            "compiled_hash_verified",
            "vcep_assertion",
            "expert_panel",
        }
        and _strength_supported(
            criterion,
            strength,
            rule_id=rule_id,
            rule_version=rule_version,
        )
    )


def _default_dimensions(
    card: EvidenceCard,
    *,
    has_known_sources: bool,
    has_verified_sources: bool,
) -> dict[str, str]:
    values = card.input_values if isinstance(card.input_values, dict) else {}
    anchor = str(values.get("anchor_status") or "")
    semantic = str(values.get("semantic_status") or "")
    dimensions = {
        "identity_status": (
            "conflict"
            if anchor == "mismatch"
            else "matched"
            if has_known_sources
            else "unknown"
        ),
        "source_status": (
            "unavailable"
            if anchor == "unavailable"
            else "available"
            if has_known_sources
            else "unavailable"
        ),
        "extraction_status": (
            "contradicted"
            if semantic == "contradicted"
            else "structured"
            if has_verified_sources
            else "unresolved"
        ),
        "version_status": "versioned" if has_verified_sources else "unversioned",
        "disease_match_status": "unspecified",
        "independence_status": "unknown",
    }
    dimensions.update(
        {
            key: str(value)
            for key, value in card.verification_dimensions.items()
            if value not in (None, "")
        }
    )
    return dimensions


def _stable_card_id(card: EvidenceCard, evidence_status: str) -> str:
    payload = {
        "variant_identity": card.variant_identity,
        "criterion": card.criterion,
        "strength": card.strength,
        "evidence_status": evidence_status,
        "input_source": card.input_source,
        "input_values": card.input_values,
        "rule_id": card.rule_id,
        "rule_version": card.rule_version,
        "source_fact_ids": sorted(card.source_fact_ids),
        "scenario_id": card.scenario_id,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]
    return f"acmg-card:v3:{digest}"


def evidence_cards_to_result(
    cards: list[EvidenceCard],
    *,
    variant_identity: dict[str, Any] | None = None,
    verified_source_fact_ids: set[str] | None = None,
    known_source_fact_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Serialize all substantive cards and derive independent calculation roles."""
    serialized: list[dict[str, Any]] = []
    known = known_source_fact_ids or set()
    verified = verified_source_fact_ids or set()
    for card in cards:
        if variant_identity and not card.variant_identity:
            card.variant_identity = dict(variant_identity)
        rule = (
            rule_for_output(
                card.criterion,
                rule_id=card.rule_id,
                rule_version=card.rule_version,
            )
            if card.rule_id or card.rule_version
            else rule_for_criterion(card.criterion)
        )
        if rule:
            card.rule_id = card.rule_id or str(rule.get("rule_id") or "")
            card.rule_version = card.rule_version or str(rule.get("version") or "")
            card.rule_reference = card.rule_reference or str(
                rule.get("primary_reference") or ""
            )
        source_ids = _source_fact_ids(card.source_fact_ids) or set()
        has_known_sources = bool(source_ids and source_ids <= known)
        has_verified_sources = bool(source_ids and source_ids <= verified)
        strength_supported = _strength_supported(
            card.criterion,
            card.strength,
            rule_id=card.rule_id,
            rule_version=card.rule_version,
        )
        dimensions = _default_dimensions(
            card,
            has_known_sources=has_known_sources,
            has_verified_sources=has_verified_sources,
        )
        evidence_status = card.evidence_status
        if (
            not evidence_status
            and not strength_supported
            and card.strength not in {"not_met", "not_applicable", "deprecated"}
        ):
            # Criteria without a substantive result are represented only in
            # criterion_reviews; pure v3 does not serialize placeholder cards.
            continue
        if not evidence_status:
            if card.strength == "deprecated":
                evidence_status = "deprecated"
            elif card.strength in {"not_met", "not_applicable"}:
                evidence_status = "not_met"
            elif _dimensions_have_hard_error(dimensions):
                evidence_status = "excluded"
            elif strength_supported and has_verified_sources:
                evidence_status = "rule_mapped"
            elif strength_supported and has_known_sources:
                evidence_status = "source_backed_candidate"
            else:
                evidence_status = "excluded"
        if evidence_status not in EVIDENCE_STATUSES:
            evidence_status = "excluded"
        if not strength_supported and evidence_status not in {
            "not_met",
            "excluded",
            "deprecated",
        }:
            continue
        rule_source = dict(card.rule_source)
        if not rule_source:
            rule_source = {
                "type": (
                    "versioned_svi"
                    if card.rule_id and card.rule_version
                    else "generic_acmg_candidate"
                ),
                "rule_id": card.rule_id,
                "version": card.rule_version,
                "reference": card.rule_reference or card.clinvar_rule_applied,
            }
        strength_source = card.strength_source or (
            "versioned_rule"
            if card.rule_id and card.rule_version
            else "acmg_2015_default_candidate"
        )
        row = asdict(card)
        row.update(
            {
                "card_id": _stable_card_id(card, evidence_status),
                "evidence_status": evidence_status,
                "observed_facts": dict(card.observed_facts or card.input_values),
                "rule_basis": card.rule_basis
                or card.rule_reference
                or card.clinvar_rule_applied,
                "strength_source": strength_source,
                "rule_source": rule_source,
                "verification_dimensions": dimensions,
            }
        )
        automatic = is_automatic_evidence(
            row, known_source_fact_ids=known_source_fact_ids
        )
        strict = is_verified_evidence(
            row, verified_source_fact_ids=verified_source_fact_ids
        )
        row["calculation_roles"] = {
            "automatic": automatic,
            "verified": strict,
            "user_selected": card.calculation_roles.get("user_selected") is True,
        }
        serialized.append(row)
    return {"evidence_cards": serialized}


__all__ = [
    "AUTOMATIC_EVIDENCE_POLICY_VERSION",
    "AUTOMATIC_EVIDENCE_STATUSES",
    "DISEASE_MATCH_STATUSES",
    "EVIDENCE_STATUSES",
    "EXTRACTION_STATUSES",
    "EvidenceCard",
    "HARD_EXCLUSION_DIMENSIONS",
    "IDENTITY_STATUSES",
    "INDEPENDENCE_STATUSES",
    "SOURCE_STATUSES",
    "SourceFact",
    "VERIFIED_EVIDENCE_POLICY_VERSION",
    "VERIFIED_EVIDENCE_STATUSES",
    "VERSION_STATUSES",
    "evidence_cards_to_result",
    "fact_identity_matches",
    "fact_is_available",
    "fact_is_strictly_verified",
    "is_automatic_evidence",
    "is_verified_evidence",
]
