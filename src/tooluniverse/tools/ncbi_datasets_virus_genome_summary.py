"""
ncbi_datasets_virus_genome_summary

Retrieve virus genome summary information from NCBI Datasets API by taxon. Returns metadata about...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_virus_genome_summary(
    taxon: str,
    accessions: Optional[list[str]] = None,
    refseq_only: Optional[bool] = False,
    annotated_only: Optional[bool] = False,
    released_since: Optional[str] = None,
    updated_since: Optional[str] = None,
    host: Optional[str] = None,
    pangolin_classification: Optional[str] = None,
    geo_location: Optional[str] = None,
    usa_state: Optional[str] = None,
    complete_only: Optional[bool] = False,
    include_sequence: Optional[list[str]] = None,
    aux_report: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve virus genome summary information from NCBI Datasets API by taxon. Returns metadata about...

    Parameters
    ----------
    accessions : list[str]
        genome sequence accessions
    taxon : str
        NCBI Taxonomy ID or name (common or scientific) at any taxonomic rank
    refseq_only : bool
        If true, limit results to RefSeq genomes.
    annotated_only : bool
        If true, limit results to annotated genomes.
    released_since : str
        If set, limit results to viral genomes that have been released after a specif...
    updated_since : str
        Parameter: updated_since
    host : str
        If set, limit results to genomes extracted from this host (Taxonomy ID or nam...
    pangolin_classification : str
        If set, limit results to genomes classified to this lineage by the PangoLearn...
    geo_location : str
        Assemblies from this location (country or continent)
    usa_state : str
        Assemblies from this state (official two letter code only)
    complete_only : bool
        only include complete genomes.
    include_sequence : list[str]
        specify which sequence files to include in the download
    aux_report : list[str]
        list additional reports to include with download. Data report is included by ...
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
            "accessions": accessions,
            "taxon": taxon,
            "refseq_only": refseq_only,
            "annotated_only": annotated_only,
            "released_since": released_since,
            "updated_since": updated_since,
            "host": host,
            "pangolin_classification": pangolin_classification,
            "geo_location": geo_location,
            "usa_state": usa_state,
            "complete_only": complete_only,
            "include_sequence": include_sequence,
            "aux_report": aux_report,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_virus_genome_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_virus_genome_summary"]
