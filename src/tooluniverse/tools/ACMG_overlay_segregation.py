"""MCP tool: ACMG_overlay_segregation"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_segregation


def ACMG_overlay_segregation(
    segregation_present=False, affected_relatives=0, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_segregation(
        segregation_present=segregation_present, affected_relatives=affected_relatives, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_segregation"]
