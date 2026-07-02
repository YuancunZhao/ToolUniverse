"""MCP tool: ACMG_overlay_source_review"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_source_review


def ACMG_overlay_source_review(
    clinvar_review_stars=0, clinvar_pathogenic_submitters=0, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_source_review(
        clinvar_review_stars=clinvar_review_stars, clinvar_pathogenic_submitters=clinvar_pathogenic_submitters, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_source_review"]
