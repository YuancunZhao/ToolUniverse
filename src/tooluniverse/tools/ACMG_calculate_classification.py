"""
ACMG_calculate_classification

Deterministic ACMG/AMP germline variant classification using the Tavtigian 2020 point system (Sup...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACMG_calculate_classification(
    variant_context: dict[str, Any],
    rule_context: dict[str, Any],
    evidence: list[Any],
    blocking_issues: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Deterministic ACMG/AMP germline variant classification using the Tavtigian 2020 point system (Sup...

    Parameters
    ----------
    variant_context : dict[str, Any]
        Single normalized variant and its context: variant (required, e.g. 'NM_000715...
    rule_context : dict[str, Any]
        cspec_lookup_status: 'released_spec_found' | 'no_released_spec' | 'unresolved...
    evidence : list[Any]
        Exactly 28 records, one per ACMG/AMP code (PVS1, PS1-PS4, PM1-PM6, PP1-PP5, B...
    blocking_issues : list[Any]
        Unresolved problems that would affect the classification (e.g. ambiguous vari...
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
    _args = {
        k: v
        for k, v in {
            "variant_context": variant_context,
            "rule_context": rule_context,
            "evidence": evidence,
            "blocking_issues": blocking_issues,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ACMG_calculate_classification",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ACMG_calculate_classification"]
