"""MCP tool: ACMG_overlay_ps1_splicing"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_ps1_splicing


def ACMG_overlay_ps1_splicing(
    same_splice_event_pathogenic=False, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_ps1_splicing(
        same_splice_event_pathogenic=same_splice_event_pathogenic, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_ps1_splicing"]
