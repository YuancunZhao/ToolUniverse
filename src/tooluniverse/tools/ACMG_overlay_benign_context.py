"""MCP tool: ACMG_overlay_benign_context"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.benign_context import overlay_benign_context


def ACMG_overlay_benign_context(
    gnomad_af_popmax=0.0, unaffected_carrier=False, alternate_diagnosis=False, vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_benign_context(
        gnomad_af_popmax=gnomad_af_popmax, unaffected_carrier=unaffected_carrier, alternate_diagnosis=alternate_diagnosis, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_benign_context"]
