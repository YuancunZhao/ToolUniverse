"""MCP tool: ACMG_overlay_case_enrichment"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_case_enrichment


def ACMG_overlay_case_enrichment(
    case_count=0,
    control_count=0,
    case_af=0.0,
    control_af=0.0,
    odds_ratio=None,
    confidence_interval_lower=None,
    phenotype_consistent=False,
    vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_case_enrichment(
        case_count=case_count,
        control_count=control_count,
        case_af=case_af,
        control_af=control_af,
        odds_ratio=odds_ratio,
        confidence_interval_lower=confidence_interval_lower,
        phenotype_consistent=phenotype_consistent,
        vcep_override=vcep_override,
    )


__all__ = ["ACMG_overlay_case_enrichment"]
