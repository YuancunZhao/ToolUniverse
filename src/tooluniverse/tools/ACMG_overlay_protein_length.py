"""MCP tool: ACMG_overlay_protein_length"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_protein_length


def ACMG_overlay_protein_length(
    variant_type='', in_repeat_region=False, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_protein_length(
        variant_type=variant_type, in_repeat_region=in_repeat_region, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_protein_length"]
