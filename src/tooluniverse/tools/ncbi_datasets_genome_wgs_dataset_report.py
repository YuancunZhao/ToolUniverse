"""
ncbi_datasets_genome_wgs_dataset_report

Get dataset reports by wgs accession
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_genome_wgs_dataset_report(
    wgs_accessions: str,
    filters_reference_only: Optional[bool] = False,
    filters_assembly_source: Optional[str] = "all",
    filters_has_annotation: Optional[bool] = False,
    filters_exclude_paired_reports: Optional[bool] = False,
    filters_exclude_atypical: Optional[bool] = False,
    filters_assembly_version: Optional[str] = "current",
    filters_assembly_level: Optional[list[str]] = None,
    filters_first_release_date: Optional[str] = None,
    filters_last_release_date: Optional[str] = None,
    filters_search_text: Optional[list[str]] = None,
    filters_is_metagenome_derived: Optional[str] = "METAGENOME_DERIVED_UNSET",
    filters_is_type_material: Optional[bool] = False,
    filters_is_ictv_exemplar: Optional[bool] = False,
    filters_exclude_multi_isolate: Optional[bool] = False,
    filters_type_material_category: Optional[str] = "NONE",
    tax_exact_match: Optional[bool] = False,
    table_fields: Optional[list[str]] = None,
    returned_content: Optional[str] = "COMPLETE",
    page_size: Optional[int] = 20,
    page_token: Optional[str] = None,
    sort_field: Optional[str] = None,
    sort_direction: Optional[str] = "SORT_DIRECTION_UNSPECIFIED",
    include_tabular_header: Optional[str] = "INCLUDE_TABULAR_HEADER_FIRST_PAGE_ONLY",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get dataset reports by wgs accession

    Parameters
    ----------
    wgs_accessions : str
        One or more wgs accessions (e.g., 'AAAA01' or ['AAAA01', 'AAAB01'])
    filters_reference_only : bool
        If true, only return reference genome assemblies
    filters_assembly_source : str
        Return only RefSeq (GCF_) or GenBank (GCA_) genome assemblies
    filters_has_annotation : bool
        Return only annotated genome assemblies
    filters_exclude_paired_reports : bool
        For paired (GCA/GCF) records, only return the primary record
    filters_exclude_atypical : bool
        If true, exclude atypical genomes, i.e. genomes that have assembly issues or ...
    filters_assembly_version : str
        Return all assemblies, including replaced and suppressed, or only current ass...
    filters_assembly_level : list[str]
        Only return genome assemblies that have one of the specified assembly levels....
    filters_first_release_date : str
        Only return genome assemblies that were released on or after the specified da...
    filters_last_release_date : str
        Only return genome assemblies that were released on or before to the specifie...
    filters_search_text : list[str]
        Only return results whose fields contain the specified search terms in their ...
    filters_is_metagenome_derived : str

    filters_is_type_material : bool
        If true, include only type materials
    filters_is_ictv_exemplar : bool
        If true, include only ICTV Exemplars
    filters_exclude_multi_isolate : bool
        If true, exclude large multi-isolate projects
    filters_type_material_category : str

    tax_exact_match : bool
        If true, only return assemblies with the given NCBI Taxonomy ID, or name. Oth...
    table_fields : list[str]

    returned_content : str
        Return either assembly accessions, or complete assembly reports
    page_size : int
        The maximum number of genome assembly reports to return. Default is 20 and ma...
    page_token : str
        A page token is returned from an `AssemblyDatasetReportsRequest` call with mo...
    sort_field : str

    sort_direction : str

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
            "wgs_accessions": wgs_accessions,
            "filters_reference_only": filters_reference_only,
            "filters_assembly_source": filters_assembly_source,
            "filters_has_annotation": filters_has_annotation,
            "filters_exclude_paired_reports": filters_exclude_paired_reports,
            "filters_exclude_atypical": filters_exclude_atypical,
            "filters_assembly_version": filters_assembly_version,
            "filters_assembly_level": filters_assembly_level,
            "filters_first_release_date": filters_first_release_date,
            "filters_last_release_date": filters_last_release_date,
            "filters_search_text": filters_search_text,
            "filters_is_metagenome_derived": filters_is_metagenome_derived,
            "filters_is_type_material": filters_is_type_material,
            "filters_is_ictv_exemplar": filters_is_ictv_exemplar,
            "filters_exclude_multi_isolate": filters_exclude_multi_isolate,
            "filters_type_material_category": filters_type_material_category,
            "tax_exact_match": tax_exact_match,
            "table_fields": table_fields,
            "returned_content": returned_content,
            "page_size": page_size,
            "page_token": page_token,
            "sort_field": sort_field,
            "sort_direction": sort_direction,
            "include_tabular_header": include_tabular_header,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_genome_wgs_dataset_report",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_genome_wgs_dataset_report"]
