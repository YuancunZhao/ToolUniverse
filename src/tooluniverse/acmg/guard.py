"""ACMG Final Answer Guard.

Enforces: no ACMG criteria without EvidenceCard.
LLM can reason, but cannot create unsupported ACMG evidence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .models import EvidenceCard, is_candidate_evidence
from .rule_catalog import ACMG_CRITERIA


_LABEL_SEPARATORS_RE = re.compile(r"[_\-\u2010-\u2015\u2212]+")
_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200d\u2060\ufeff]")


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
        "assessment_status": card.assessment_status,
        "proposal_status": card.proposal_status,
        "proposal_origin": card.proposal_origin,
        "rule_mapping_status": card.rule_mapping_status,
        "system_preview_included": card.system_preview_included,
        "user_decision": card.user_decision,
        "overlay_validated": card.overlay_validated is True,
        "source_fact_ids": card.source_fact_ids,
        "rule_id": card.rule_id,
        "rule_version": card.rule_version,
    }


def guard_acmg_answer(
    answer_text: str,
    evidence_cards: list[EvidenceCard | dict[str, Any]],
    *,
    trusted_source_fact_ids: set[str] | None = None,
    known_source_fact_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Validate that answer's ACMG claims are supported by EvidenceCards.

    Rules:
    1. Final five-tier labels (Pathogenic/LP/VUS/LB/Benign, 致病/可能致病...)
       MUST have corresponding EvidenceCards.
    2. ACMG criterion codes (PM2, PP3, PS2, PVS1, etc.) in the answer
       MUST be present in the EvidenceCards.
    3. Source labels (GeneBe, ClinVar, InterVar) cited as external references
       are allowed but flagged.
    4. Missing or untrusted SourceFact provenance is treated as unsupported.

    Returns:
        {"status": "PASS" | "BLOCK", "blocking_reasons": [...], "cards_used": [...]}
    """
    reasons = []

    normalized_answer = unicodedata.normalize("NFKC", str(answer_text or ""))
    answer_upper = _normalized_label_text(normalized_answer)
    cited_codes = {
        code
        for code in ACMG_CRITERIA
        if re.search(rf"(?<![A-Z0-9]){re.escape(code)}(?![A-Z0-9])", answer_upper)
    }
    rows = [_card_row(card) for card in evidence_cards]
    candidate_rows = [
        row
        for row in rows
        if is_candidate_evidence(
            row, trusted_source_fact_ids=trusted_source_fact_ids
        )
    ]
    referenceable_statuses = {
        "suggested",
        "not_suggested",
        "requires_user_review",
        "insufficient_information",
        "not_applicable",
        "deprecated",
    }
    known_ids = {
        str(value)
        for value in (known_source_fact_ids or trusted_source_fact_ids or set())
        if value
    }
    referenceable_rows = [
        row
        for row in rows
        if row in candidate_rows
        or (
            str(row.get("card_id") or "").startswith("acmg-card:v1:")
            and str(row.get("proposal_status") or "") in referenceable_statuses
            and bool(row.get("source_fact_ids"))
            and {
                str(value) for value in row.get("source_fact_ids") or [] if value
            }
            <= known_ids
        )
    ]
    card_codes = {str(row.get("criterion", "")) for row in referenceable_rows}

    # Check: cited codes that don't have EvidenceCards
    unsupported = cited_codes - card_codes
    if unsupported:
        reasons.append(
            f"Unsupported ACMG criteria cited without EvidenceCards: {sorted(unsupported)}. "
            "Every ACMG criterion MUST have a corresponding EvidenceCard from overlay tools."
        )

    # Check for final classification labels
    FINAL_LABELS_CN = {
        "可能致病",
        "可能良性",
        "致病",
        "良性",
        "临床意义不明",
        "意义不明",
    }
    FINAL_LABELS_EN = {
        "LIKELY PATHOGENIC",
        "LIKELY BENIGN",
        "PATHOGENIC",
        "BENIGN",
        "VUS",
        "UNCERTAIN SIGNIFICANCE",
        "VARIANT OF UNCERTAIN SIGNIFICANCE",
    }

    has_final_label = any(label in answer_upper for label in FINAL_LABELS_EN) or any(
        label in normalized_answer for label in FINAL_LABELS_CN
    )
    has_final_label = has_final_label or bool(
        re.search(r"(?<![A-Z])(?:LP|LB|VUS)(?![A-Z])", answer_upper)
    )
    # P/B are only unambiguous shorthand in a classification context. Avoid
    # treating ordinary p-values or isolated prose letters as final labels.
    classification_context = re.search(
        r"(?:ACMG|CLASSIF(?:ICATION|Y)|SIGNIFICANCE|VARIANT)\b", answer_upper
    )
    if classification_context and re.search(r"(?<![A-Z])(?:P|B)(?![A-Z])", answer_upper):
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
                "proposal_origin": row.get("proposal_origin"),
                "proposal_status": row.get("proposal_status"),
                "rule_mapping_status": row.get("rule_mapping_status"),
                "system_preview_included": row.get("system_preview_included") is True,
                "user_decision": row.get("user_decision") or "pending",
            }
            for row in referenceable_rows
        ],
        "unsupported_codes": sorted(unsupported),
        "message": (
            "All ACMG claims verified against EvidenceCards."
            if status == "PASS"
            else f"BLOCKED: {len(reasons)} violations found."
        ),
    }


__all__ = ["guard_acmg_answer"]
