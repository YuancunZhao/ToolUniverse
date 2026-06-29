"""ACMG_apply_overlay_routes"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ._shared_client import get_shared_client


def ACMG_apply_overlay_routes(
    route_triggers: Optional[list[Any]] = None,
    candidate_evidence: Optional[list[Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    args = {
        k: v
        for k, v in {
            "route_triggers": route_triggers,
            "candidate_evidence": candidate_evidence,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {"name": "ACMG_apply_overlay_routes", "arguments": args},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ACMG_apply_overlay_routes"]
