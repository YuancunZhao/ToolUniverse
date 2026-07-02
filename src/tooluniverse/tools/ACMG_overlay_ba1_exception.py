"""MCP tool: ACMG_overlay_ba1_exception"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.ba1_exception import overlay_ba1_exception


def ACMG_overlay_ba1_exception(
    gnomad_af_popmax=0.0, gnomad_af_global=0.0, gene_disease_prevalence='rare', vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_ba1_exception(
        gnomad_af_popmax=gnomad_af_popmax, gnomad_af_global=gnomad_af_global, gene_disease_prevalence=gene_disease_prevalence, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_ba1_exception"]
