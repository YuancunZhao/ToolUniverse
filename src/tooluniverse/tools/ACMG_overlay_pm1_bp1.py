"""MCP tool: ACMG_overlay_pm1_bp1"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_pm1_bp1


def ACMG_overlay_pm1_bp1(
    in_functional_domain=False, domain_has_pathogenic_enrichment=False, gene_missense_mechanism=False, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_pm1_bp1(
        in_functional_domain=in_functional_domain, domain_has_pathogenic_enrichment=domain_has_pathogenic_enrichment, gene_missense_mechanism=gene_missense_mechanism, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_pm1_bp1"]
