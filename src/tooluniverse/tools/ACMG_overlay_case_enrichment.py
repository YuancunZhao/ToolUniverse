"""MCP tool: ACMG_overlay_case_enrichment"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_case_enrichment


def ACMG_overlay_case_enrichment(
    case_count=0, control_count=0, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_case_enrichment(
        case_count=case_count, control_count=control_count, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_case_enrichment"]
