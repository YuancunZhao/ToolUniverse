"""
ncbi_datasets_gene_id_orthologs

Get gene orthologs by gene ID
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_gene_id_orthologs(
    gene_id: int,
    returned_content: Optional[str] = "COMPLETE",
    taxon_filter: Optional[list[str]] = None,
    page_size: Optional[int] = 20,
    page_token: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get gene orthologs by gene ID

    Parameters
    ----------
    gene_id : int

    returned_content : str
        Return either gene-ids, or entire gene metadata
    taxon_filter : list[str]
        Filter genes by taxa
    page_size : int
        The maximum number of gene reports to return. Default is 20 and maximum is 10...
    page_token : str
        A page token is returned from an `OrthologRequest` call with more than `page_...
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
            "gene_id": gene_id,
            "returned_content": returned_content,
            "taxon_filter": taxon_filter,
            "page_size": page_size,
            "page_token": page_token,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_gene_id_orthologs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_gene_id_orthologs"]
