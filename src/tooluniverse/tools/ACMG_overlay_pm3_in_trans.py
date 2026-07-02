"""MCP tool: ACMG_overlay_pm3_in_trans"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_pm3_in_trans


def ACMG_overlay_pm3_in_trans(
    second_variant_pathogenic=False, phase_confirmed=False, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_pm3_in_trans(
        second_variant_pathogenic=second_variant_pathogenic, phase_confirmed=phase_confirmed, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_pm3_in_trans"]
