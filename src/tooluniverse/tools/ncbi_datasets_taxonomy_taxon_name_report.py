"""
ncbi_datasets_taxonomy_taxon_name_report

Use taxonomic identifiers to get taxonomic names data report
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_taxonomy_taxon_name_report(
    taxons: str,
    returned_content: Optional[str] = "COMPLETE",
    page_size: Optional[int] = 20,
    include_tabular_header: Optional[str] = "INCLUDE_TABULAR_HEADER_FIRST_PAGE_ONLY",
    page_token: Optional[str] = None,
    table_format: Optional[str] = "SUMMARY",
    children: Optional[bool] = None,
    ranks: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Use taxonomic identifiers to get taxonomic names data report

    Parameters
    ----------
    taxons : str
        One or more taxons (e.g., '9606' for human, or ['9606', '10090'] for human an...
    returned_content : str
        Return either tax-ids alone, or entire taxononmy-metadata records
    page_size : int
        The maximum number of taxons to return. Default is 20 and maximum is 1000. If...
    include_tabular_header : str
        Whether this request for tabular data should include the header row
    page_token : str
        A page token is returned from `GetTaxonomyDataReportFor` and `GetTaxonomyName...
    table_format : str

    children : bool
        Flag for tax explosion.
    ranks : list[str]
        Only include taxons of the provided ranks. If empty, return all ranks.
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
            "taxons": taxons,
            "returned_content": returned_content,
            "page_size": page_size,
            "include_tabular_header": include_tabular_header,
            "page_token": page_token,
            "table_format": table_format,
            "children": children,
            "ranks": ranks,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_taxonomy_taxon_name_report",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_taxonomy_taxon_name_report"]
