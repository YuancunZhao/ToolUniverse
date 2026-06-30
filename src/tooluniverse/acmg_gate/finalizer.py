"""Canonical finalization gate for ACMG overlay outputs."""

from __future__ import annotations

from typing import Any


def compute_finalization_gate(
    validator_status: str | None,
    semantic_combiner_status: str | None,
    final_classification_allowed: bool,
    bundle_final_requested: bool,
    counted_evidence: list[Any] | None,
    literature_ready: bool,
) -> dict[str, Any]:
    """Compute whether final ACMG classification wording is allowed."""

    has_counted_evidence = bool(counted_evidence)
    gates = {
        "validator_status": validator_status,
        "semantic_combiner_status": semantic_combiner_status,
        "final_classification_allowed": final_classification_allowed,
        "bundle_final_requested": bundle_final_requested,
        "has_counted_evidence": has_counted_evidence,
        "literature_ready": literature_ready,
    }
    blocking_reasons: list[str] = []
    if validator_status != "PASS":
        blocking_reasons.append("validator_status is not PASS")
    if semantic_combiner_status != "PASS":
        blocking_reasons.append("semantic_combiner_status is not PASS")
    if final_classification_allowed is not True:
        blocking_reasons.append("final_classification_allowed is not true")
    if not bundle_final_requested:
        blocking_reasons.append("bundle classification_status is not final classification")
    if not has_counted_evidence:
        blocking_reasons.append("no compatibility-resolved counted evidence")
    if not literature_ready:
        blocking_reasons.append("literature hits are not fully reviewed or no literature coverage is documented")
    return {
        "final_allowed": not blocking_reasons,
        "gates": gates,
        "blocking_reasons": blocking_reasons,
    }
