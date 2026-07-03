"""MCP tool: ACMG_overlay_pp3_bp4"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.pp3_bp4 import overlay_pp3_bp4


def ACMG_overlay_pp3_bp4(
    revel_score=None,
    cadd_phred=None,
    spliceai_ds_dg=None,
    sift_score=None,
    polyphen_score=None,
    bayesdel_noaf_score=None,
    mutpred2_score=None,
    vest4_score=None,
    evolutionary_action_score=None,
    fathmm_score=None,
    gerp_score=None,
    mpc_score=None,
    phylop_score=None,
    primateai_score=None,
    selected_tool=None,
    vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_pp3_bp4(
        revel_score=revel_score,
        cadd_phred=cadd_phred,
        spliceai_ds_dg=spliceai_ds_dg,
        sift_score=sift_score,
        polyphen_score=polyphen_score,
        bayesdel_noaf_score=bayesdel_noaf_score,
        mutpred2_score=mutpred2_score,
        vest4_score=vest4_score,
        evolutionary_action_score=evolutionary_action_score,
        fathmm_score=fathmm_score,
        gerp_score=gerp_score,
        mpc_score=mpc_score,
        phylop_score=phylop_score,
        primateai_score=primateai_score,
        selected_tool=selected_tool,
        vcep_override=vcep_override,
    )


__all__ = ["ACMG_overlay_pp3_bp4"]
