"""
ACMG_guard_final_answer

Fail-closed guard for ACMG wording. Criterion discussion is allowed when it references an Evidenc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACMG_guard_final_answer(
    final_answer_text: str,
    evidence_cards: Optional[list[Any]] = None,
    collector_result: Optional[dict[str, Any]] = None,
    guard_context: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fail-closed guard for ACMG wording. Criterion discussion is allowed when it references an Evidenc...

    Parameters
    ----------
    final_answer_text : str

    evidence_cards : list[Any]
        Compatibility input. Each bare card must contain a legal criterion, strength,...
    collector_result : dict[str, Any]

    guard_context : dict[str, Any]
        Preferred lightweight input. Pass the collector's schema_version, variant_ide...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "final_answer_text": final_answer_text,
            "evidence_cards": evidence_cards,
            "collector_result": collector_result,
            "guard_context": guard_context,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ACMG_guard_final_answer",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ACMG_guard_final_answer"]
