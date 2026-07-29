"""
ClinGen_search_cspec

Discover current released ClinGen Criteria Specification Registry documents for a gene. Returns V...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGen_search_cspec(
    gene: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Discover current released ClinGen Criteria Specification Registry documents for a gene. Returns V...

    Parameters
    ----------
    gene : str
        HGNC gene symbol
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "gene": gene
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ClinGen_search_cspec",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ClinGen_search_cspec"]
