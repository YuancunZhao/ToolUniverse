"""MCP tool: ACMG_overlay_functional_assay"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_functional_assay


def ACMG_overlay_functional_assay(
    functional_evidence='',
    assay_type='',
    assay_category='',
    assay_applicable_to_disease_mechanism=False,
    variant_specific=False,
    replicated=False,
    has_controls=False,
    statistically_significant=False,
    effect_direction='',
    vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_functional_assay(
        functional_evidence=functional_evidence,
        assay_type=assay_type,
        assay_category=assay_category,
        assay_applicable_to_disease_mechanism=assay_applicable_to_disease_mechanism,
        variant_specific=variant_specific,
        replicated=replicated,
        has_controls=has_controls,
        statistically_significant=statistically_significant,
        effect_direction=effect_direction,
        vcep_override=vcep_override,
    )


__all__ = ["ACMG_overlay_functional_assay"]
