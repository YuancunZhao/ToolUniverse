"""Conflict and Bayesian review summaries for validated EvidenceCards."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .models import is_candidate_evidence
from .rule_catalog import bayesian_odds_for_output, generic_bayesian_odds_for
from .runtime_manifest import BAYESIAN_PRIOR


def _candidate(row: dict[str, Any], trusted_source_fact_ids: set[str] | None) -> bool:
    return is_candidate_evidence(
        row, trusted_source_fact_ids=trusted_source_fact_ids
    )


def summarize_strengths(
    rows: list[dict[str, Any]],
    *,
    trusted_source_fact_ids: set[str] | None = None,
) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if isinstance(row, dict)
        and _candidate(row, trusted_source_fact_ids)
    ]
    strengths = Counter(str(row.get("strength") or "") for row in selected)
    return {
        "system_preview_criteria": [
            str(row.get("criterion") or "") for row in selected
        ],
        "strength_counts": dict(sorted(strengths.items())),
        "strength_summary": (
            ", ".join(f"{key}={value}" for key, value in sorted(strengths.items()))
            if strengths
            else "No compatible candidate evidence."
        ),
    }


def compute_bayesian_score(
    rows: list[dict[str, Any]],
    *,
    trusted_source_fact_ids: set[str] | None = None,
    estimate_type: str = "candidate_review_only",
    selection_field: str = "system_preview_included",
) -> dict[str, Any]:
    odds_path = 1.0
    strengths_used: list[str] = []
    unsupported_strengths: list[str] = []
    special_criteria: list[dict[str, Any]] = []
    included_cards: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidate_row = row
        if selection_field == "user_selected_included":
            if row.get("user_selected_included") is not True:
                continue
            candidate_row = {
                **row,
                "system_preview_included": True,
            }
        if not _candidate(candidate_row, trusted_source_fact_ids):
            continue
        strength = str(row.get("effective_strength") or row.get("strength") or "")
        criterion = str(row.get("criterion") or "")
        dynamic_odds = None
        for container_key in ("observed_facts", "input_values"):
            container = row.get(container_key)
            if not isinstance(container, dict):
                continue
            applied = container.get("cspec_contract_applied")
            if not isinstance(applied, dict):
                continue
            value = applied.get("bayesian_odds")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                dynamic_odds = float(value)
                break
        odds = dynamic_odds
        odds_source = "dynamic_cspec_strength"
        if odds is None:
            odds = bayesian_odds_for_output(
                criterion,
                strength,
                rule_id=str(row.get("rule_id") or ""),
                rule_version=str(row.get("rule_version") or ""),
            )
            odds_source = "versioned_rule_catalog"
        if odds is None:
            odds = generic_bayesian_odds_for(criterion, strength)
            odds_source = "tavtigian_generic_strength"
        if criterion == "BA1" and strength == "BA1":
            special_criteria.append(
                {
                    "card_id": str(row.get("card_id") or ""),
                    "criterion": criterion,
                    "strength": strength,
                    "reason": "stand_alone_criterion_not_multiplied",
                }
            )
            continue
        if odds is None:
            unsupported_strengths.append(strength)
            continue
        odds_path *= odds
        strengths_used.append(strength)
        included_cards.append(
            {
                "card_id": str(row.get("card_id") or ""),
                "criterion": criterion,
                "strength": strength,
                "odds_path": odds,
                "odds_source": odds_source,
            }
        )
    prior = BAYESIAN_PRIOR
    posterior = odds_path * prior / ((odds_path - 1.0) * prior + 1.0)
    strength_counts = Counter(row["strength"] for row in included_cards)
    strength_summary = (
        ", ".join(
            f"{key}={value}" for key, value in sorted(strength_counts.items())
        )
        if strength_counts
        else "No compatible candidate evidence."
    )
    return {
        "status": "computed",
        "estimate_type": estimate_type,
        "prior_probability": prior,
        "posterior_probability": round(posterior, 4),
        "odds_path": round(odds_path, 6),
        "strength_summary": strength_summary,
        "strengths_used": strengths_used,
        "included_card_ids": [row["card_id"] for row in included_cards],
        "evidence_odds": included_cards,
        "unsupported_strengths": unsupported_strengths,
        "special_criteria": special_criteria,
        "not_a_final_classification": True,
    }


def detect_conflicts(
    rows: list[dict[str, Any]],
    *,
    trusted_source_fact_ids: set[str] | None = None,
) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if isinstance(row, dict)
        and _candidate(row, trusted_source_fact_ids)
    ]
    pathogenic = [
        str(row.get("criterion") or "")
        for row in selected
        if str(row.get("criterion") or "").startswith(("PVS1", "PS", "PM", "PP"))
    ]
    benign = [
        str(row.get("criterion") or "")
        for row in selected
        if str(row.get("criterion") or "").startswith(("BA1", "BS", "BP"))
    ]
    conflicts: list[dict[str, Any]] = []
    if pathogenic and benign:
        conflicts.append(
            {
                "type": "pathogenic_vs_benign",
                "criteria": pathogenic + benign,
                "description": "Candidate pathogenic- and benign-side evidence are both present.",
            }
        )
    return {
        "has_conflicts": bool(conflicts),
        "conflicts": conflicts,
        "recommendation": (
            "Review source compatibility and resolve conflicting evidence manually."
            if conflicts
            else ""
        ),
    }


__all__ = [
    "compute_bayesian_score",
    "detect_conflicts",
    "summarize_strengths",
]
