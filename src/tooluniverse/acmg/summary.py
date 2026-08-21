"""Conflict and Bayesian summaries for ACMG v4 EvidenceCards."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .models import is_automatic_evidence, is_verified_evidence
from .rule_catalog import bayesian_odds_for_output, generic_bayesian_odds_for
from .runtime_manifest import BAYESIAN_PRIOR


def _selected(row: dict[str, Any], role: str) -> bool:
    roles = row.get("calculation_roles")
    return isinstance(roles, dict) and roles.get(role) is True


def compute_bayesian_score(
    rows: list[dict[str, Any]],
    *,
    verified_source_fact_ids: set[str] | None = None,
    known_source_fact_ids: set[str] | None = None,
    estimate_type: str = "automatic",
    calculation_role: str = "automatic",
    eligibility: str = "automatic",
) -> dict[str, Any]:
    odds_path = 1.0
    strengths_used: list[str] = []
    unsupported_strengths: list[str] = []
    special_criteria: list[dict[str, Any]] = []
    included_cards: list[dict[str, Any]] = []
    dimension_counts: Counter[str] = Counter()
    for row in rows:
        if not isinstance(row, dict) or not _selected(row, calculation_role):
            continue
        eligible = (
            is_automatic_evidence(row, known_source_fact_ids=known_source_fact_ids)
            if eligibility == "automatic"
            else is_verified_evidence(
                row, verified_source_fact_ids=verified_source_fact_ids
            )
        )
        if not eligible:
            continue
        strength = str(row.get("strength") or "")
        criterion = str(row.get("criterion") or "")
        if criterion == "BA1" and strength == "BA1":
            special_criteria.append(
                {
                    "card_id": row.get("card_id"),
                    "criterion": criterion,
                    "strength": strength,
                    "reason": "standalone_criterion_not_multiplied",
                }
            )
            continue
        dynamic_odds = None
        for container_key in ("observed_facts",):
            container = row.get(container_key)
            if not isinstance(container, dict):
                continue
            applied = container.get("cspec_contract_applied")
            if isinstance(applied, dict) and isinstance(
                applied.get("bayesian_odds"), (int, float)
            ):
                dynamic_odds = float(applied["bayesian_odds"])
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
            odds_source = "generic_tavtigian_strength"
        if odds is None:
            unsupported_strengths.append(strength)
            continue
        odds_path *= odds
        strengths_used.append(strength)
        dimensions = row.get("verification_dimensions")
        dimensions = dimensions if isinstance(dimensions, dict) else {}
        dimension_counts.update(
            f"{key}:{value}" for key, value in dimensions.items() if value
        )
        included_cards.append(
            {
                "card_id": str(row.get("card_id") or ""),
                "criterion": criterion,
                "strength": strength,
                "odds_path": odds,
                "odds_source": odds_source,
                "evidence_status": row.get("evidence_status"),
                "strength_source": row.get("strength_source"),
            }
        )
    prior = BAYESIAN_PRIOR
    posterior = odds_path * prior / ((odds_path - 1.0) * prior + 1.0)
    counts = Counter(row["strength"] for row in included_cards)
    return {
        "status": "computed",
        "estimate_type": estimate_type,
        "estimate_policy": (
            "source_backed_candidates"
            if eligibility == "automatic"
            else "verified_rules"
        ),
        "prior_probability": prior,
        "posterior_probability": round(posterior, 4),
        "odds_path": round(odds_path, 6),
        "strength_summary": ", ".join(
            f"{key}={value}" for key, value in sorted(counts.items())
        )
        or "No compatible evidence.",
        "strengths_used": strengths_used,
        "included_card_ids": [row["card_id"] for row in included_cards],
        "evidence_odds": included_cards,
        "unsupported_strengths": unsupported_strengths,
        "special_criteria": special_criteria,
        "verification_dimension_counts": dict(dimension_counts),
        "not_a_final_classification": True,
    }


def detect_conflicts(
    rows: list[dict[str, Any]],
    *,
    verified_source_fact_ids: set[str] | None = None,
    known_source_fact_ids: set[str] | None = None,
    eligibility: str = "automatic",
) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if isinstance(row, dict)
        and (
            is_automatic_evidence(row, known_source_fact_ids=known_source_fact_ids)
            if eligibility == "automatic"
            else is_verified_evidence(
                row, verified_source_fact_ids=verified_source_fact_ids
            )
        )
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
                "description": "Pathogenic- and benign-side evidence are both present.",
            }
        )
    return {
        "has_conflicts": bool(conflicts),
        "conflicts": conflicts,
        "recommendation": (
            "Review source compatibility and conflicting evidence." if conflicts else ""
        ),
    }


__all__ = ["compute_bayesian_score", "detect_conflicts"]
