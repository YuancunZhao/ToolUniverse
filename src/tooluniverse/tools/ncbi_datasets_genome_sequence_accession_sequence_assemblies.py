"""
ncbi_datasets_genome_sequence_accession_sequence_assemblies

Get assembly accessions for a sequence accession
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_genome_sequence_accession_sequence_assemblies(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get assembly accessions for a sequence accession

    Parameters
    ----------
    accession : str

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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_genome_sequence_accession_sequence_assemblies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_genome_sequence_accession_sequence_assemblies"]
