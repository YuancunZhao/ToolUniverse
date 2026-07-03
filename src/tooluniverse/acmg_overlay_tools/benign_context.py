"""Benign Context overlay tool. Covers BS1/BS2/BP2/BP5."""
from __future__ import annotations
from typing import Any


def overlay_benign_context(
    gnomad_af_popmax: float = 0.0,
    unaffected_carrier: bool = False,
    alternate_diagnosis: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    from .base import output_template, vcep_deferred_template
    if vcep_override:
        return vcep_deferred_template(
            "BS1/BS2/BP2/BP5",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    results = []
    criteria = []
    if 0.01 < gnomad_af_popmax <= 0.05:
        results.append("BS1 criteria may apply")
        criteria.append("BS1")
    if unaffected_carrier:
        results.append("BS2: observed in healthy adult")
        criteria.append("BS2")
    if alternate_diagnosis:
        results.append("BP5: alternate molecular diagnosis")
        criteria.append("BP5")
    if not results:
        return output_template("BS1/BS2/BP2/BP5", "not_met", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No benign context criteria met.")
    strength = "BS2" if "BS2" in criteria else ("BP5" if criteria else "not_met")
    return output_template("BS1/BS2/BP2/BP5", strength, status="applied",
        route_outcome="overlay_applied",
        reason="; ".join(results) + ".",
        source_of_truth="ClinGen, clinical observation")

__all__ = ["overlay_benign_context"]
