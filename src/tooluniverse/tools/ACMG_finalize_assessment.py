"""ACMG_finalize_assessment"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ._shared_client import get_shared_client


def ACMG_finalize_assessment(
    acmg_assessment_bundle: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    args = {
        "acmg_assessment_bundle": acmg_assessment_bundle,
    }
    return get_shared_client().run_one_function(
        {"name": "ACMG_finalize_assessment", "arguments": {k: v for k, v in args.items() if v is not None}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ACMG_finalize_assessment"]
