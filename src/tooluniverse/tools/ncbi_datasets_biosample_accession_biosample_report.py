"""
ncbi_datasets_biosample_accession_biosample_report

Get BioSample dataset reports by accession(s)
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_biosample_accession_biosample_report(
    accessions: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get BioSample dataset reports by accession(s)

    Parameters
    ----------
    accessions : str
        One or more accessions (e.g., 'NM_021803.4' or ['NM_021803.4', 'NM_000546.6'])
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
    _args = {k: v for k, v in {"accessions": accessions}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_biosample_accession_biosample_report",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_biosample_accession_biosample_report"]
