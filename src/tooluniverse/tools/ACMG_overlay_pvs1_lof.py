"""MCP tool: ACMG_overlay_pvs1_lof"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_pvs1_lof


def ACMG_overlay_pvs1_lof(
    variant_type='', gene_lof_mechanism=False, lof_intolerant=False, nmd_predicted=None, exon_position='', truncated_region_percent=100.0, region_criticality='unknown', rescue_transcript=False, spliceai_dl=None, ar_disease=False, second_allele_found=False, vcep_override = None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_pvs1_lof(
        variant_type=variant_type, gene_lof_mechanism=gene_lof_mechanism, lof_intolerant=lof_intolerant, nmd_predicted=nmd_predicted, exon_position=exon_position, truncated_region_percent=truncated_region_percent, region_criticality=region_criticality, rescue_transcript=rescue_transcript, spliceai_dl=spliceai_dl, ar_disease=ar_disease, second_allele_found=second_allele_found, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_pvs1_lof"]
