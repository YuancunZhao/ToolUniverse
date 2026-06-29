"""ACMG_guard_final_answer"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ._shared_client import get_shared_client


def ACMG_guard_final_answer(
    final_answer_text: Optional[str] = None,
    harness_result: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    args = {
        k: v
        for k, v in {
            "final_answer_text": final_answer_text,
            "harness_result": harness_result,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {"name": "ACMG_guard_final_answer", "arguments": args},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ACMG_guard_final_answer"]
