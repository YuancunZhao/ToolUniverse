"""
ACMG_literature_evidence

Review structured case-control facts. Direct group-tool cards are always review-only; the collect...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACMG_literature_evidence(
    case_control_facts: Optional[list[Any]] = None,
    expected_variant: Optional[str] = None,
    expected_gene: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Review structured case-control facts. Direct group-tool cards are always review-only; the collect...

    Parameters
    ----------
    case_control_facts : list[Any]
        Standalone review facts. They remain outside the system preview until collect...
    expected_variant : str
        Variant identity used to bind standalone structured facts.
    expected_gene : str
        Gene symbol used to bind standalone structured facts.
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
    _args = {k: v for k, v in {
        "case_control_facts": case_control_facts,
                "expected_variant": expected_variant,
                "expected_gene": expected_gene
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ACMG_literature_evidence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ACMG_literature_evidence"]
