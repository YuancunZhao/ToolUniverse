"""
ncbi_datasets_taxonomy_taxon_filtered_subtree

Use taxonomic identifiers to get a filtered taxonomic subtree
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_taxonomy_taxon_filtered_subtree(
    taxons: str,
    rank_limits: Optional[list[str]] = None,
    include_incertae_sedis: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Use taxonomic identifiers to get a filtered taxonomic subtree

    Parameters
    ----------
    taxons : str
        One or more taxons (e.g., '9606' for human, or ['9606', '10090'] for human an...
    rank_limits : list[str]
        Limit to the provided ranks.  If empty, accept any rank.
    include_incertae_sedis : bool
        Include nodes with ranks not in 'rank_limits' if their names meet criteria fo...
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
            "rank_limits": rank_limits,
            "include_incertae_sedis": include_incertae_sedis,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_taxonomy_taxon_filtered_subtree",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_taxonomy_taxon_filtered_subtree"]
