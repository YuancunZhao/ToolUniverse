"""MCP tool: ACMG_overlay_pvs1_lof"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_pvs1_lof


def ACMG_overlay_pvs1_lof(
    variant_type='', gene_lof_mechanism=False, lof_intolerant=False, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_pvs1_lof(
        variant_type=variant_type, gene_lof_mechanism=gene_lof_mechanism, lof_intolerant=lof_intolerant, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_pvs1_lof"]
