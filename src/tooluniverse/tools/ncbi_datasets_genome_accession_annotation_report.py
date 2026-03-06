"""
ncbi_datasets_genome_accession_annotation_report

Get genome annotation reports by genome assembly accession
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_genome_accession_annotation_report(
    accession: str,
    annotation_ids: Optional[list[str]] = None,
    symbols: Optional[list[str]] = None,
    locations: Optional[list[str]] = None,
    gene_types: Optional[list[str]] = None,
    search_text: Optional[list[str]] = None,
    sort_field: Optional[str] = None,
    sort_direction: Optional[str] = "SORT_DIRECTION_UNSPECIFIED",
    page_size: Optional[int] = 20,
    table_format: Optional[str] = "NO_TABLE",
    include_tabular_header: Optional[str] = "INCLUDE_TABULAR_HEADER_FIRST_PAGE_ONLY",
    page_token: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get genome annotation reports by genome assembly accession

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

    page_size : int
        The maximum number of features to return. Default is 20 and maximum is 1000. ...
    table_format : str
        Optional pre-defined template for processing a tabular data request
    include_tabular_header : str
        Whether this request for tabular data should include the header row
    page_token : str
        A page token is returned from a `GetFeatures` call with more than `page_size`...
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
            "page_size": page_size,
            "table_format": table_format,
            "include_tabular_header": include_tabular_header,
            "page_token": page_token,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_genome_accession_annotation_report",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_genome_accession_annotation_report"]
