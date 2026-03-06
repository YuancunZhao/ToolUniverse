"""
ncbi_datasets_gene_by_accession

Retrieve gene metadata from NCBI Datasets API using RefSeq RNA or protein accessions. Returns gen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_gene_by_accession(
    accessions: str,
    returned_content: Optional[str] = "COMPLETE",
    locus_tags: Optional[list[str]] = None,
    table_fields: Optional[list[str]] = None,
    include_tabular_header: Optional[str] = "INCLUDE_TABULAR_HEADER_FIRST_PAGE_ONLY",
    page_size: Optional[int] = 20,
    page_token: Optional[str] = None,
    accession_filter: Optional[list[str]] = None,
    tax_search_subtree: Optional[bool] = False,
    sort_field: Optional[str] = None,
    sort_direction: Optional[str] = "SORT_DIRECTION_UNSPECIFIED",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve gene metadata from NCBI Datasets API using RefSeq RNA or protein accessions. Returns gen...

    Parameters
    ----------
    returned_content : str
        Return either gene-ids, or entire gene metadata
    accessions : str
        One or more rna (e.g., 'NM_021803.4' or ['NM_021803.4', 'NM_000546.6'])
    locus_tags : list[str]
        Gene locus tags
    table_fields : list[str]
        Specify which fields to include in the tabular report
    include_tabular_header : str
        Whether this request for tabular data should include the header row
    page_size : int
        The maximum number of gene reports to return. Default is 20 and maximum is 10...
    page_token : str
        A page token is returned from an `AssemblyDatasetReportsRequest` call with mo...
    accession_filter : list[str]
        Filter tabular product report to only include the selected accessions
    tax_search_subtree : bool
        For queries including a tax-id, include any matching genes annotated on taxa ...
    sort_field : str
        Parameter: sort.field
    sort_direction : str
        Parameter: sort.direction
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
            "returned_content": returned_content,
            "accessions": accessions,
            "locus_tags": locus_tags,
            "table_fields": table_fields,
            "include_tabular_header": include_tabular_header,
            "page_size": page_size,
            "page_token": page_token,
            "accession_filter": accession_filter,
            "tax_search_subtree": tax_search_subtree,
            "sort_field": sort_field,
            "sort_direction": sort_direction,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_gene_by_accession",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_gene_by_accession"]
