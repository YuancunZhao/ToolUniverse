"""
ncbi_datasets_genome_accession_annotation_report_download_summary

Get a download summary (preview) of a genome annotation data package by genome assembly accession
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_genome_accession_annotation_report_download_summary(
    accession: str,
    annotation_ids: Optional[list[str]] = None,
    symbols: Optional[list[str]] = None,
    locations: Optional[list[str]] = None,
    gene_types: Optional[list[str]] = None,
    search_text: Optional[list[str]] = None,
    sort_field: Optional[str] = None,
    sort_direction: Optional[str] = "SORT_DIRECTION_UNSPECIFIED",
    include_annotation_type: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get a download summary (preview) of a genome annotation data package by genome assembly accession

    Parameters
    ----------
    accession : str

    annotation_ids : list[str]
        Limit to one or more features annotated on the genome by specifying a number ...
    symbols : list[str]
        Limit to annotated features matching the given gene symbol (case-sensitive).
    locations : list[str]
        Limit to features annotated at a specific location on the genome, by specifyi...
    gene_types : list[str]
        Limit to features of a specified gene locus type.
    search_text : list[str]
        Limit to features that match the specified gene symbol, gene name or protein ...
    sort_field : str

    sort_direction : str

    include_annotation_type : list[str]
        Specify which sequences files to include in the data package. Options include...
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
            "annotation_ids": annotation_ids,
            "symbols": symbols,
            "locations": locations,
            "gene_types": gene_types,
            "search_text": search_text,
            "sort_field": sort_field,
            "sort_direction": sort_direction,
            "include_annotation_type": include_annotation_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_genome_accession_annotation_report_download_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_genome_accession_annotation_report_download_summary"]
