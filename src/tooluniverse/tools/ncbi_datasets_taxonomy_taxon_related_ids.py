"""
ncbi_datasets_taxonomy_taxon_related_ids

Use taxonomic identifier to get related taxonomic identifiers, such as children
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_taxonomy_taxon_related_ids(
    tax_id: int,
    include_lineage: Optional[bool] = False,
    include_subtree: Optional[bool] = False,
    ranks: Optional[list[str]] = None,
    page_size: Optional[int] = 20,
    page_token: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Use taxonomic identifier to get related taxonomic identifiers, such as children

    Parameters
    ----------
    tax_id : int

    include_lineage : bool
        If true, return reports for all taxonomy nodes in the lineages of the request...
    include_subtree : bool
        This field is deprecated because all requests include the subtree, so it has ...
    ranks : list[str]
        Only include taxons of the provided ranks. If empty, return all ranks.
    page_size : int
        The maximum number of taxids to return. Default is 20 and maximum is 1000. If...
    page_token : str
        A page token is returned from a `GetRelatedTaxids` call with more than `page_...
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
            "tax_id": tax_id,
            "include_lineage": include_lineage,
            "include_subtree": include_subtree,
            "ranks": ranks,
            "page_size": page_size,
            "page_token": page_token,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_taxonomy_taxon_related_ids",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_taxonomy_taxon_related_ids"]
