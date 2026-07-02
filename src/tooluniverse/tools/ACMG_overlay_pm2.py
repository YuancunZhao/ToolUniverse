"""MCP tool: acmg_overlay_pm2"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.pm2 import overlay_pm2


def ACMG_overlay_pm2(
    gnomad_af_global: float = 0.0,
    gnomad_af_popmax: float = 0.0,
    gnomad_ac: int = 0,
    gnomad_an: int = 0,
    coverage_adequate: bool = True,
    disease_prevalence: str = "rare",
    vcep_override: str | None = None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_pm2(
        gnomad_af_global=gnomad_af_global,
        gnomad_af_popmax=gnomad_af_popmax,
        gnomad_ac=gnomad_ac,
        gnomad_an=gnomad_an,
        coverage_adequate=coverage_adequate,
        disease_prevalence=disease_prevalence,
        vcep_override=vcep_override,
    )


__all__ = ["ACMG_overlay_pm2"]
