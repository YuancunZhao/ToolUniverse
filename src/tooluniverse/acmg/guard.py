"""ACMG Final Answer Guard.

Enforces: no ACMG criteria without EvidenceCard.
LLM can reason, but cannot create unsupported ACMG evidence.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import unicodedata
from typing import Any

from .models import EVIDENCE_STATUSES, EvidenceCard
from .rule_catalog import ACMG_CRITERIA, is_valid_strength_for_criterion


_LABEL_SEPARATORS_RE = re.compile(r"[_\-\u2010-\u2015\u2212]+")
_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200d\u2060\ufeff]")
GUARD_CONTEXT_SCHEMA_VERSION = "2026-08-15-v3-light"
_GUARD_CONTEXT_HASH_FIELDS = (
    "schema_version",
    "variant_identity_hash",
    "ruleset_hash",
    "claims",
    "criterion_review_claims",
)
_GUARD_CLAIM_FIELDS = {
    "card_id",
    "criterion",
    "strength",
    "evidence_status",
    "role",
}
_GUARD_ROLES = {"automatic", "verified", "user_selected", "not_met", "excluded"}
_REVIEW_ROUTE_STATUSES = {
    "assessed",
    "proposal_validated",
    "candidate_available",
    "review_pending",
    "insufficient_information",
    "not_applicable",
    "deprecated",
}
_REVIEW_EVIDENCE_STATUSES = {*EVIDENCE_STATUSES, "no_information"}
_CRITERION_REVIEW_FIELDS = {"criterion", "route_status", "evidence_status"}


def guard_context_hash(context: dict[str, Any]) -> str:
    """Hash the complete visible Guard context contract."""
    payload = {key: context.get(key) for key in _GUARD_CONTEXT_HASH_FIELDS}
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def validate_guard_context(context: Any) -> tuple[bool, str]:
    """Validate a compact Guard context and its accidental-mutation checksum."""
    if not isinstance(context, dict):
        return False, "guard_context must be an object"
    missing = [
        key
        for key in (*_GUARD_CONTEXT_HASH_FIELDS, "context_hash")
        if key not in context
    ]
    if missing:
        return False, f"guard_context missing fields: {', '.join(missing)}"
    expected_fields = {*_GUARD_CONTEXT_HASH_FIELDS, "context_hash"}
    unexpected = sorted(set(context) - expected_fields)
    if unexpected:
        return False, f"guard_context has unexpected fields: {', '.join(unexpected)}"
    if context.get("schema_version") != GUARD_CONTEXT_SCHEMA_VERSION:
        return False, "guard_context schema_version is unsupported"
    for key in ("variant_identity_hash", "ruleset_hash", "context_hash"):
        value = context.get(key)
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            return False, f"guard_context {key} must be a SHA-256 hex digest"
    claims = context.get("claims")
    if not isinstance(claims, list) or not all(
        isinstance(row, dict) for row in claims
    ):
        return False, "guard_context claims must be an array of objects"
    card_ids: list[str] = []
    for row in claims:
        unexpected_claim_fields = sorted(set(row) - _GUARD_CLAIM_FIELDS)
        if unexpected_claim_fields:
            return False, (
                "guard_context claim has unexpected fields: "
                + ", ".join(unexpected_claim_fields)
            )
        missing_claim_fields = sorted(_GUARD_CLAIM_FIELDS - set(row))
        if missing_claim_fields:
            return False, (
                "guard_context claim missing fields: "
                + ", ".join(missing_claim_fields)
            )
        card_id = row.get("card_id")
        if not isinstance(card_id, str) or not card_id:
            return False, "guard_context claim card_id must be a non-empty string"
        if not _criterion_codes(row.get("criterion")):
            return False, "guard_context claim criterion is unsupported"
        strength = str(row.get("strength") or "")
        status = str(row.get("evidence_status") or "")
        role = str(row.get("role") or "")
        if not strength:
            return False, "guard_context claim strength must be non-empty"
        if status not in EVIDENCE_STATUSES:
            return False, "guard_context claim evidence_status is unsupported"
        if role not in _GUARD_ROLES:
            return False, "guard_context claim role is unsupported"
        card_ids.append(card_id)
    if len(card_ids) != len(set(card_ids)):
        return False, "guard_context claim card_ids must be unique"
    review_claims = context.get("criterion_review_claims")
    if not isinstance(review_claims, list) or not all(
        isinstance(row, dict) for row in review_claims
    ):
        return False, "guard_context criterion_review_claims must be an array of objects"
    review_criteria: list[str] = []
    for row in review_claims:
        if set(row) != _CRITERION_REVIEW_FIELDS:
            return False, "guard_context criterion review claim fields are invalid"
        criterion = str(row.get("criterion") or "")
        if criterion not in ACMG_CRITERIA:
            return False, "guard_context criterion review claim criterion is unsupported"
        if str(row.get("route_status") or "") not in _REVIEW_ROUTE_STATUSES:
            return False, "guard_context criterion review claim route_status is unsupported"
        if str(row.get("evidence_status") or "") not in _REVIEW_EVIDENCE_STATUSES:
            return False, "guard_context criterion review claim evidence_status is unsupported"
        review_criteria.append(criterion)
    if len(review_criteria) != len(set(review_criteria)):
        return False, "guard_context criterion review claims must be unique"
    from .runtime_manifest import ruleset_hash

    if context.get("ruleset_hash") != ruleset_hash():
        return False, "guard_context ruleset_hash does not match this runtime"
    try:
        expected = guard_context_hash(context)
    except (TypeError, ValueError):
        return False, "guard_context is not canonical JSON"
    if not hmac.compare_digest(str(context.get("context_hash") or ""), expected):
        return False, "guard_context checksum mismatch"
    return True, ""


def _normalized_label_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    normalized = _ZERO_WIDTH_RE.sub("", normalized)
    normalized = _LABEL_SEPARATORS_RE.sub(" ", normalized)
    return " ".join(normalized.upper().split())


def _card_row(card: EvidenceCard | dict[str, Any]) -> dict[str, Any]:
    if isinstance(card, dict):
        return card
    return {
        "criterion": card.criterion,
        "strength": card.strength,
        "card_id": card.card_id,
        "evidence_status": card.evidence_status,
        "strength_source": card.strength_source,
        "rule_source": card.rule_source,
        "verification_dimensions": card.verification_dimensions,
        "calculation_roles": card.calculation_roles,
        "scenario_id": card.scenario_id,
        "user_decision": card.user_decision,
        "source_fact_ids": card.source_fact_ids,
        "rule_id": card.rule_id,
        "rule_version": card.rule_version,
    }


def _criterion_codes(value: Any) -> set[str]:
    return {
        token
        for token in re.split(r"[/,\s]+", str(value or "").upper())
        if token in ACMG_CRITERIA
    }


def _referenceable_card(
    row: dict[str, Any],
    *,
    known_source_fact_ids: set[str] | None,
    validated_claim: bool,
) -> bool:
    """Return whether a card or validated compact claim may support discussion."""
    codes = _criterion_codes(row.get("criterion"))
    status = str(row.get("evidence_status") or "")
    strength = str(row.get("strength") or "")
    if not codes or not str(row.get("card_id") or "") or status not in EVIDENCE_STATUSES:
        return False
    if validated_claim:
        return str(row.get("role") or "") in _GUARD_ROLES
    source_ids = {
        str(value)
        for value in row.get("source_fact_ids") or []
        if isinstance(value, str) and value
    }
    if not source_ids:
        return False
    if known_source_fact_ids is not None and not source_ids <= known_source_fact_ids:
        return False
    dimensions = row.get("verification_dimensions")
    if isinstance(dimensions, dict) and any(
        str(dimensions.get(key) or "") in blocked
        for key, blocked in {
            "identity_status": {"conflict"},
            "extraction_status": {"contradicted"},
            "disease_match_status": {"mismatch"},
            "independence_status": {"overlapping"},
        }.items()
    ):
        return False
    if status in {"not_met", "excluded", "deprecated"}:
        return bool(strength)
    rule_valid = any(
        is_valid_strength_for_criterion(code, strength) for code in codes
    )
    return rule_valid


def _has_final_classification_label(answer_text: str) -> bool:
    normalized = _normalized_label_text(answer_text)
    stripped = normalized.strip(" .,:;()[]{}")
    labels = {
        "PATHOGENIC",
        "LIKELY PATHOGENIC",
        "VUS",
        "UNCERTAIN SIGNIFICANCE",
        "VARIANT OF UNCERTAIN SIGNIFICANCE",
        "LIKELY BENIGN",
        "BENIGN",
        "LP",
        "LB",
    }
    if stripped in labels:
        return True
    label_expression = (
        r"(?:LIKELY PATHOGENIC|PATHOGENIC|VUS|VARIANT OF UNCERTAIN "
        r"SIGNIFICANCE|UNCERTAIN SIGNIFICANCE|LIKELY BENIGN|BENIGN|LP|LB)"
    )
    if re.search(
        rf"(?:CLASSIFICATION|CLASS|CONCLUSION|FINAL ASSESSMENT|SIGNIFICANCE)"
        rf"\s*(?::|=|IS|WAS|AS)?\s*{label_expression}(?![A-Z])",
        normalized,
    ):
        return True
    if re.search(
        rf"\b(?:THIS\s+)?VARIANT\s+(?:IS|WAS|IS CLASSIFIED AS|WAS CLASSIFIED AS)"
        rf"\s+{label_expression}(?![A-Z])",
        normalized,
    ):
        return True
    chinese = unicodedata.normalize("NFKC", str(answer_text or ""))
    chinese_labels = "(?:可能致病|可能良性|临床意义不明|意义不明|致病|良性)"
    return bool(
        re.search(
            rf"(?:分类|结论|判定|该?变异).{{0,12}}(?:为|是|[:：=])\s*{chinese_labels}",
            chinese,
        )
        or chinese.strip(" 。；：，")
        in {"可能致病", "可能良性", "临床意义不明", "意义不明", "致病", "良性"}
    )


def _strip_attributed_external_assertions(answer_text: str) -> str:
    """Remove sentences that clearly attribute a label to an external source."""
    retained: list[str] = []
    for sentence in re.split(r"(?<=[.!?。！？;；])\s*|\n+", str(answer_text or "")):
        normalized = _normalized_label_text(sentence)
        has_source = bool(
            re.search(
                r"\b(?:VCEP|CLINGEN|CLINVAR|EXPERT PANEL|EXTERNAL ASSERTION)\b",
                normalized,
            )
            or re.search(
                r"(?:外部|专家组|来源|数据库).{0,12}(?:判定|分类|结论)", sentence
            )
        )
        has_attribution = bool(
            re.search(
                r"(?:CLASSIFIED|CLASSIFIES|ASSERTED|REPORTED|CONCLUDED|判定为|分类为|报告为|结论为)",
                normalized,
            )
        )
        if not (has_source and has_attribution):
            retained.append(sentence)
    return "\n".join(retained)


def guard_acmg_answer(
    answer_text: str,
    evidence_cards: list[EvidenceCard | dict[str, Any]],
    *,
    verified_source_fact_ids: set[str] | None = None,
    known_source_fact_ids: set[str] | None = None,
    validated_claims: bool = False,
    criterion_review_claims: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate ACMG claims against cards and block final five-tier labels.

    Criterion codes must have a corresponding source-backed card. Database
    labels may be discussed as external references, but missing or unknown
    SourceFact provenance remains unsupported. The returned mapping contains
    the PASS or BLOCK status, reasons, referenced cards, and card roles.
    """
    reasons = []

    normalized_answer = unicodedata.normalize("NFKC", str(answer_text or ""))
    answer_upper = _normalized_label_text(normalized_answer)
    cited_like_codes = set(
        re.findall(r"(?<![A-Z0-9])(?:PVS|PS|PM|PP|BA|BS|BP)\d+(?![A-Z0-9])", answer_upper)
    )
    known_criteria = set(ACMG_CRITERIA)
    cited_codes = cited_like_codes & known_criteria
    rows = [_card_row(card) for card in evidence_cards]
    referenceable_rows = [
        row
        for row in rows
        if _referenceable_card(
            row,
            known_source_fact_ids=known_source_fact_ids,
            validated_claim=validated_claims,
        )
    ]
    card_codes = {
        code
        for row in referenceable_rows
        for code in _criterion_codes(row.get("criterion"))
    }
    review_rows = [
        row
        for row in criterion_review_claims or []
        if isinstance(row, dict)
        and str(row.get("criterion") or "") in ACMG_CRITERIA
        and str(row.get("route_status") or "") in _REVIEW_ROUTE_STATUSES
        and str(row.get("evidence_status") or "") in _REVIEW_EVIDENCE_STATUSES
    ]
    review_codes = {str(row["criterion"]) for row in review_rows}

    # Check: cited codes that don't have EvidenceCards
    unsupported = (cited_codes - card_codes - review_codes) | (
        cited_like_codes - known_criteria
    )
    if unsupported:
        reasons.append(
            f"Unsupported ACMG criteria cited without an EvidenceCard or criterion review: "
            f"{sorted(unsupported)}."
        )

    own_assertion_text = _strip_attributed_external_assertions(normalized_answer)
    has_final_label = _has_final_classification_label(own_assertion_text)
    if re.search(
        r"(?:CLASSIFICATION|CLASS|分类|结论)\s*[:：=]\s*(?:P|B)(?![A-Z0-9])",
        _normalized_label_text(own_assertion_text),
    ):
        has_final_label = True

    if has_final_label:
        reasons.append(
            "Final five-tier ACMG labels are not allowed in the evidence-collection "
            "runtime. This tool collects and evaluates evidence only."
        )

    cards_used = [
        f"{row.get('criterion', '')}({row.get('strength', '')})"
        for row in referenceable_rows
    ]
    status = "PASS" if not reasons else "BLOCK"

    return {
        "status": status,
        "blocking_reasons": reasons,
        "cards_used": cards_used,
        "card_roles": [
            {
                "card_id": row.get("card_id"),
                "criterion": row.get("criterion"),
                "evidence_status": row.get("evidence_status"),
                "strength_source": row.get("strength_source"),
                "scenario_id": row.get("scenario_id"),
                "role": (
                    row.get("role")
                    or (
                        "verified"
                        if (row.get("calculation_roles") or {}).get("verified") is True
                        else "automatic"
                        if (row.get("calculation_roles") or {}).get("automatic") is True
                        else "excluded"
                    )
                ),
                "verification_dimensions": row.get("verification_dimensions") or {},
                "calculation_roles": row.get("calculation_roles") or {},
                "user_decision": row.get("user_decision") or "pending",
            }
            for row in referenceable_rows
        ],
        "criterion_review_roles": [
            {
                "criterion": row.get("criterion"),
                "route_status": row.get("route_status"),
                "evidence_status": row.get("evidence_status"),
                "role": "review_only",
            }
            for row in review_rows
            if row.get("criterion") in cited_codes
        ],
        "unsupported_codes": sorted(unsupported),
        "message": (
            "All ACMG claims verified against EvidenceCards."
            if status == "PASS"
            else f"BLOCKED: {len(reasons)} violations found."
        ),
    }


__all__ = [
    "GUARD_CONTEXT_SCHEMA_VERSION",
    "guard_acmg_answer",
    "guard_context_hash",
    "validate_guard_context",
]
