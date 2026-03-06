"""
ncbi_datasets_genome_accession_annotation_summary

Get genome annotation report summary information by genome assembly accession
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_genome_accession_annotation_summary(
    accession: str,
    sort_field: Optional[str] = None,
    sort_direction: Optional[str] = "SORT_DIRECTION_UNSPECIFIED",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get genome annotation report summary information by genome assembly accession

    Parameters
    ----------
    accession : str

    sort_field : str

    sort_direction : str

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
            "accession": accession,
            "sort_field": sort_field,
            "sort_direction": sort_direction,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_genome_accession_annotation_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_genome_accession_annotation_summary"]
