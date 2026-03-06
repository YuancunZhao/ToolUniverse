"""
ncbi_datasets_gene_id_links

Get gene links by gene ID
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_gene_id_links(
    gene_ids: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get gene links by gene ID

    Parameters
    ----------
    gene_ids : str
        One or more ncbi (e.g., 59067 for IL21, or [59067, 50615] for multiple genes)
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
    _args = {k: v for k, v in {"gene_ids": gene_ids}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_gene_id_links",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_gene_id_links"]
