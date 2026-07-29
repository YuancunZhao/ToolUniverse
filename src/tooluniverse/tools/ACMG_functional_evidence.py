"""
ACMG_functional_evidence

Review structured functional assays under Brnich OddsPath; only the collector can validate and co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACMG_functional_evidence(
    variant_type: Optional[str] = None,
    functional_assays: Optional[list[Any]] = None,
    consequence_profile: Optional[dict[str, Any]] = None,
    protein_context: Optional[dict[str, Any]] = None,
    pvs1_facts: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Review structured functional assays under Brnich OddsPath; only the collector can validate and co...

    Parameters
    ----------
    variant_type : str
        
    functional_assays : list[Any]
        
    consequence_profile : dict[str, Any]
        Review-only normalized consequence context. Caller-provided values cannot mak...
    protein_context : dict[str, Any]
        Review-only protein mapping and domain/site facts. Collector-verified SourceF...
    pvs1_facts : dict[str, Any]
        Review-only structured facts for the deterministic ClinGen SVI PVS1 decision ...
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
        "variant_type": variant_type,
                "functional_assays": functional_assays,
                "consequence_profile": consequence_profile,
                "protein_context": protein_context,
                "pvs1_facts": pvs1_facts
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ACMG_functional_evidence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ACMG_functional_evidence"]
