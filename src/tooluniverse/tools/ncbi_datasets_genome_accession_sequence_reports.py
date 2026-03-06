"""
ncbi_datasets_genome_accession_sequence_reports

Get genome sequence reports by genome assembly accessions
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_genome_accession_sequence_reports(
    accession: str,
    chromosomes: Optional[list[str]] = None,
    role_filters: Optional[list[str]] = None,
    table_fields: Optional[list[str]] = None,
    count_assembly_unplaced: Optional[bool] = False,
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    include_tabular_header: Optional[str] = "INCLUDE_TABULAR_HEADER_FIRST_PAGE_ONLY",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get genome sequence reports by genome assembly accessions

    Parameters
    ----------
    accession : str

    chromosomes : list[str]
        Limit to sequences with the specified chromosome names
    role_filters : list[str]
        Limit to sequences with the specified "role", where possible roles are `assem...
    table_fields : list[str]

    count_assembly_unplaced : bool
        Include the count of unplaced scaffold sequences
    page_size : int
        The maximum number of genome assemblies to return. Maximum is 1000. If the nu...
    page_token : str
        A page token is returned from an `GetSequenceReports` call with more than `pa...
    include_tabular_header : str

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
            "chromosomes": chromosomes,
            "role_filters": role_filters,
            "table_fields": table_fields,
            "count_assembly_unplaced": count_assembly_unplaced,
            "page_size": page_size,
            "page_token": page_token,
            "include_tabular_header": include_tabular_header,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_genome_accession_sequence_reports",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_genome_accession_sequence_reports"]
