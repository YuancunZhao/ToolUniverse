"""
ncbi_datasets_genome_accession_download_summary

Preview genome dataset download
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_genome_accession_download_summary(
    accessions: str,
    chromosomes: Optional[list[str]] = None,
    include_annotation_type: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Preview genome dataset download

    Parameters
    ----------
    accessions : str
        One or more ncbi (e.g., 'NM_021803.4' or ['NM_021803.4', 'NM_000546.6'])
    chromosomes : list[str]
        The default setting is all chromosome. Specify individual chromosome by strin...
    include_annotation_type : list[str]
        Select additional types of annotation to include in the data package.  If uns...
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
            "accessions": accessions,
            "chromosomes": chromosomes,
            "include_annotation_type": include_annotation_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_genome_accession_download_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_genome_accession_download_summary"]
