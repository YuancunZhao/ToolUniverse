"""MCP tool: ACMG_overlay_pvs1_splicing"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_pvs1_splicing


def ACMG_overlay_pvs1_splicing(
    spliceai_dl=None,
    spliceai_da=None,
    is_canonical_gt_ag=False,
    rna_evidence=False,
    nmd_predicted=None,
    vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_pvs1_splicing(
        spliceai_dl=spliceai_dl,
        spliceai_da=spliceai_da,
        is_canonical_gt_ag=is_canonical_gt_ag,
        rna_evidence=rna_evidence,
        nmd_predicted=nmd_predicted,
        vcep_override=vcep_override,
    )


__all__ = ["ACMG_overlay_pvs1_splicing"]
