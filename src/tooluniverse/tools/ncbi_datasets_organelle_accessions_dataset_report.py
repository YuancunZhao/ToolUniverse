"""
ncbi_datasets_organelle_accessions_dataset_report

Get Organelle dataset report by accession
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_organelle_accessions_dataset_report(
    accessions: str,
    taxons: Optional[list[str]] = None,
    organelle_types: Optional[list[str]] = None,
    first_release_date: Optional[str] = None,
    last_release_date: Optional[str] = None,
    tax_exact_match: Optional[bool] = False,
    sort_field: Optional[str] = None,
    sort_direction: Optional[str] = "SORT_DIRECTION_UNSPECIFIED",
    returned_content: Optional[str] = "COMPLETE",
    table_format: Optional[str] = "ORGANELLE_TABLE_FORMAT_NO_TABLE",
    include_tabular_header: Optional[str] = "INCLUDE_TABULAR_HEADER_FIRST_PAGE_ONLY",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get Organelle dataset report by accession

    Parameters
    ----------
    taxons : list[str]
        NCBI Taxonomy ID or name (common or scientific) at any taxonomic rank
    accessions : str
        One or more ncbi (e.g., 'NM_021803.4' or ['NM_021803.4', 'NM_000546.6'])
    organelle_types : list[str]

    first_release_date : str
        Only return organelle assemblies that were released on or after the specified...
    last_release_date : str
        Only return organelle assemblies that were released on or before to the speci...
    tax_exact_match : bool
        If true, only return assemblies with the given NCBI Taxonomy ID, or name. Oth...
    sort_field : str

    sort_direction : str

    returned_content : str
        Return either assembly accessions, or entire assembly-metadata records
    table_format : str
        Optional pre-defined template for processing a tabular data request
    include_tabular_header : str
        Whether this request for tabular data should include the header row
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
            "accessions": accessions,
            "organelle_types": organelle_types,
            "first_release_date": first_release_date,
            "last_release_date": last_release_date,
            "tax_exact_match": tax_exact_match,
            "sort_field": sort_field,
            "sort_direction": sort_direction,
            "returned_content": returned_content,
            "table_format": table_format,
            "include_tabular_header": include_tabular_header,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_organelle_accessions_dataset_report",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_organelle_accessions_dataset_report"]
