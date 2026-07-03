"""MCP tool: ACMG_overlay_de_novo"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_de_novo


def ACMG_overlay_de_novo(
    de_novo_confirmed=False,
    paternity_confirmed=False,
    phenotype_highly_specific=False,
    phenotype_consistent=False,
    genetic_heterogeneity_low=False,
    vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_de_novo(
        de_novo_confirmed=de_novo_confirmed,
        paternity_confirmed=paternity_confirmed,
        phenotype_highly_specific=phenotype_highly_specific,
        phenotype_consistent=phenotype_consistent,
        genetic_heterogeneity_low=genetic_heterogeneity_low,
        vcep_override=vcep_override,
    )


__all__ = ["ACMG_overlay_de_novo"]
