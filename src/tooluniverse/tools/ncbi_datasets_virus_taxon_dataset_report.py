"""
ncbi_datasets_virus_taxon_dataset_report

Get virus metadata by taxon
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_virus_taxon_dataset_report(
    taxon: str,
    filter_refseq_only: Optional[bool] = False,
    filter_annotated_only: Optional[bool] = False,
    filter_released_since: Optional[str] = None,
    filter_updated_since: Optional[str] = None,
    filter_host: Optional[str] = None,
    filter_pangolin_classification: Optional[str] = None,
    filter_geo_location: Optional[str] = None,
    filter_usa_state: Optional[str] = None,
    filter_complete_only: Optional[bool] = False,
    returned_content: Optional[str] = "COMPLETE",
    table_fields: Optional[list[str]] = None,
    page_size: Optional[int] = 20,
    page_token: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get virus metadata by taxon

    Parameters
    ----------
    taxon : str
        NCBI Taxonomy ID or name (common or scientific) at any taxonomic rank
    filter_refseq_only : bool
        If true, limit results to RefSeq genomes.
    filter_annotated_only : bool
        If true, limit results to annotated genomes.
    filter_released_since : str
        If set, limit results to viral genomes that have been released after a specif...
    filter_updated_since : str

    filter_host : str
        If set, limit results to genomes extracted from this host (Taxonomy ID or nam...
    filter_pangolin_classification : str
        If set, limit results to genomes classified to this lineage by the PangoLearn...
    filter_geo_location : str
        Assemblies from this location (country or continent)
    filter_usa_state : str
        Assemblies from this state (official two letter code only)
    filter_complete_only : bool
        only include complete genomes.
    returned_content : str
        Return either virus genome accessions, or complete virus metadata
    table_fields : list[str]
        Specify which fields to include in the tabular report
    page_size : int
        The maximum number of virus data reports to return. Default is 20 and maximum...
    page_token : str
        A page token is returned from a `GetVirusDataReports` call with more than `pa...
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
            "taxon": taxon,
            "filter_refseq_only": filter_refseq_only,
            "filter_annotated_only": filter_annotated_only,
            "filter_released_since": filter_released_since,
            "filter_updated_since": filter_updated_since,
            "filter_host": filter_host,
            "filter_pangolin_classification": filter_pangolin_classification,
            "filter_geo_location": filter_geo_location,
            "filter_usa_state": filter_usa_state,
            "filter_complete_only": filter_complete_only,
            "returned_content": returned_content,
            "table_fields": table_fields,
            "page_size": page_size,
            "page_token": page_token,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_virus_taxon_dataset_report",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_virus_taxon_dataset_report"]
