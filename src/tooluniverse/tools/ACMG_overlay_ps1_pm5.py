"""MCP tool: ACMG_overlay_ps1_pm5"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.ps1_pm5 import overlay_ps1_pm5


def ACMG_overlay_ps1_pm5(
    clinvar_same_aa_pathogenic=False, clinvar_same_aa_pathogenic_count=0, clinvar_same_residue_pathogenic=False, clinvar_same_residue_pathogenic_count=0, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_ps1_pm5(
        clinvar_same_aa_pathogenic=clinvar_same_aa_pathogenic, clinvar_same_aa_pathogenic_count=clinvar_same_aa_pathogenic_count, clinvar_same_residue_pathogenic=clinvar_same_residue_pathogenic, clinvar_same_residue_pathogenic_count=clinvar_same_residue_pathogenic_count, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_ps1_pm5"]
