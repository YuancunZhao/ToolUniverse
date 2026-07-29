"""
ACMG_computational_evidence

Apply the pre-specified computational predictor policy and return EvidenceCards only.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACMG_computational_evidence(
    revel_score: Optional[float] = None,
    cadd_phred: Optional[float] = None,
    spliceai_max_delta: Optional[float] = None,
    spliceai_profile: Optional[dict[str, Any]] = None,
    spliceai_scores: Optional[dict[str, Any]] = None,
    spliceai_run_metadata: Optional[dict[str, Any]] = None,
    predictor_scores: Optional[dict[str, Any]] = None,
    variant_type: Optional[str] = None,
    consequence_terms: Optional[list[str]] = None,
    hgvs_c: Optional[str] = None,
    hgvs_p: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Apply the pre-specified computational predictor policy and return EvidenceCards only.

    Parameters
    ----------
    revel_score : float
        
    cadd_phred : float
        
    spliceai_max_delta : float
        Explicit four-channel maximum delta score. Complete DS_*/DP_* values are stil...
    spliceai_profile : dict[str, Any]
        Normalized selected-transcript SpliceAI profile containing all four DS_*/DP_*...
    spliceai_scores : dict[str, Any]
        Selected-transcript SpliceAI score row. DS_AG/DS_AL/DS_DG/DS_DL are delta sco...
    spliceai_run_metadata : dict[str, Any]
        Walker 2023 run provenance. Missing or incomplete metadata keeps SpliceAI PP3...
    predictor_scores : dict[str, Any]
        
    variant_type : str
        
    consequence_terms : list[str]
        
    hgvs_c : str
        
    hgvs_p : str
        
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
        "revel_score": revel_score,
                "cadd_phred": cadd_phred,
                "spliceai_max_delta": spliceai_max_delta,
                "spliceai_profile": spliceai_profile,
                "spliceai_scores": spliceai_scores,
                "spliceai_run_metadata": spliceai_run_metadata,
                "predictor_scores": predictor_scores,
                "variant_type": variant_type,
                "consequence_terms": consequence_terms,
                "hgvs_c": hgvs_c,
                "hgvs_p": hgvs_p
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ACMG_computational_evidence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ACMG_computational_evidence"]
