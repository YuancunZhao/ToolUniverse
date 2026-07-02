"""MCP tool: ACMG_overlay_functional_assay"""

from __future__ import annotations

from typing import Any, Callable

from ..acmg_overlay_tools.overlays import overlay_functional_assay


def ACMG_overlay_functional_assay(
    functional_evidence='', assay_type='', effect_magnitude='', vcep_override=None,
    *,
    stream_callback: Callable[[str], None] | None = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    return overlay_functional_assay(
        functional_evidence=functional_evidence, assay_type=assay_type, effect_magnitude=effect_magnitude, vcep_override=vcep_override
    )


__all__ = ["ACMG_overlay_functional_assay"]
