"""
ncbi_datasets_taxonomy_taxon_suggest

Get a list of taxonomy names and IDs given a partial taxonomic name
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_taxonomy_taxon_suggest(
    taxon_query: str,
    tax_rank_filter: Optional[str] = "species",
    taxon_resource_filter: Optional[str] = "TAXON_RESOURCE_FILTER_ALL",
    exact_match: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get a list of taxonomy names and IDs given a partial taxonomic name

    Parameters
    ----------
    taxon_query : str
        NCBI Taxonomy ID or name (common or scientific) at any taxonomic rank
    tax_rank_filter : str
        Set the scope of searched tax ranks when filtering by gene or genome.  Not us...
    taxon_resource_filter : str
        Limit results to those with gene or genome counts (no filter by default)
    exact_match : bool
        If true, only return results that exactly match the provided name or tax-id
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
            "taxon_query": taxon_query,
            "tax_rank_filter": tax_rank_filter,
            "taxon_resource_filter": taxon_resource_filter,
            "exact_match": exact_match,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_taxonomy_taxon_suggest",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_taxonomy_taxon_suggest"]
