"""MCP tool: ACMG_overlay_pp3_bp4"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.pp3_bp4 import overlay_pp3_bp4


def ACMG_overlay_pp3_bp4(
    revel_score=None, cadd_phred=None, spliceai_ds_dg=None, sift_score=None, polyphen_score=None, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_pp3_bp4(
        revel_score=revel_score, cadd_phred=cadd_phred, spliceai_ds_dg=spliceai_ds_dg, sift_score=sift_score, polyphen_score=polyphen_score, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_pp3_bp4"]
