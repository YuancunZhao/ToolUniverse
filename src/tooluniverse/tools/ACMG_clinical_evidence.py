"""
ACMG_clinical_evidence

Review structured de novo and PM3 observations; only the collector can validate and count them.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACMG_clinical_evidence(
    inheritance_mode: Optional[str] = None,
    de_novo_probands: Optional[list[Any]] = None,
    pm3_frequency_eligible: Optional[bool] = None,
    pm3_observations: Optional[list[Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Review structured de novo and PM3 observations; only the collector can validate and count them.

    Parameters
    ----------
    inheritance_mode : str
        
    de_novo_probands : list[Any]
        
    pm3_frequency_eligible : bool
        
    pm3_observations : list[Any]
        
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
        "inheritance_mode": inheritance_mode,
                "de_novo_probands": de_novo_probands,
                "pm3_frequency_eligible": pm3_frequency_eligible,
                "pm3_observations": pm3_observations
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ACMG_clinical_evidence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ACMG_clinical_evidence"]
