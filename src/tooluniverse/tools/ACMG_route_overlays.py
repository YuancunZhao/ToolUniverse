"""MCP tool: acmg_route_overlays"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.router import route_overlays


def ACMG_route_overlays(
    variant: str = "",
    gene: str = "",
    hgvs_c: str = "",
    variant_type: str = "",
    consequence: str = "",
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return route_overlays(
        variant=variant,
        gene=gene,
        hgvs_c=hgvs_c,
        variant_type=variant_type,
        consequence=consequence,
    )


__all__ = ["ACMG_route_overlays"]
