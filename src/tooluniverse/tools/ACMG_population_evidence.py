"""
ACMG_population_evidence

Apply deterministic ClinGen/SVI population evidence rules and return EvidenceCards only.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACMG_population_evidence(
    gnomad_af_global: Optional[float] = None,
    gnomad_af_popmax: Optional[float] = None,
    gnomad_ac: Optional[int] = None,
    gnomad_an: Optional[int] = None,
    coverage_adequate: Optional[bool] = None,
    callability_available: Optional[bool] = None,
    population_details: Optional[dict[str, Any]] = None,
    callability_metrics: Optional[dict[str, Any]] = None,
    maximum_credible_af: Optional[float] = None,
    ba1_exception: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Apply deterministic ClinGen/SVI population evidence rules and return EvidenceCards only.

    Parameters
    ----------
    gnomad_af_global : float
        
    gnomad_af_popmax : float
        
    gnomad_ac : int
        
    gnomad_an : int
        
    coverage_adequate : bool
        
    callability_available : bool
        Whether auditable site callability rows were supplied; this is not a coverage...
    population_details : dict[str, Any]
        Raw dataset, callset, homozygote, and ancestry-frequency audit fields.
    callability_metrics : dict[str, Any]
        Raw gnomAD site coverage metrics; no adequacy threshold is inferred.
    maximum_credible_af : float
        
    ba1_exception : bool
        
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
        "gnomad_af_global": gnomad_af_global,
                "gnomad_af_popmax": gnomad_af_popmax,
                "gnomad_ac": gnomad_ac,
                "gnomad_an": gnomad_an,
                "coverage_adequate": coverage_adequate,
                "callability_available": callability_available,
                "population_details": population_details,
                "callability_metrics": callability_metrics,
                "maximum_credible_af": maximum_credible_af,
                "ba1_exception": ba1_exception
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ACMG_population_evidence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ACMG_population_evidence"]
