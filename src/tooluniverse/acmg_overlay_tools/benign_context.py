"""Benign Context overlay tool. Covers BS1/BS2/BP2/BP5."""
from __future__ import annotations
from typing import Any


def overlay_benign_context(
    gnomad_af_popmax: float = 0.0,
    unaffected_carrier: bool = False,
    alternate_diagnosis: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    from .base import output_template
    if vcep_override:
        return output_template("BS1/BS2/BP2/BP5", vcep_override, reason=f"VCEP: {vcep_override}")
    results = []
    if 0.01 < gnomad_af_popmax <= 0.05:
        results.append("BS1 criteria may apply")
    if unaffected_carrier:
        results.append("BS2: observed in healthy adult")
    if alternate_diagnosis:
        results.append("BP5: alternate molecular diagnosis")
    if not results:
        return output_template("BS1/BS2/BP2/BP5", "not_met", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No benign context criteria met.")
    return output_template("BS1/BS2/BP2/BP5", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason="; ".join(results) + ". Requires clinical context for final determination.",
        source_of_truth="ClinGen, user context")

__all__ = ["overlay_benign_context"]
