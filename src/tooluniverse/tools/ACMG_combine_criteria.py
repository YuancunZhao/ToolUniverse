"""MCP tool: acmg_combine_criteria"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.combine import combine_criteria


def ACMG_combine_criteria(
    criteria: list[dict[str, Any]] | None = None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return combine_criteria(criteria or [])


__all__ = ["ACMG_combine_criteria"]
