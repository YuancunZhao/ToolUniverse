"""
ncbi_datasets_gene_id_download_summary

Get gene download summary by GeneID
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ncbi_datasets_gene_id_download_summary(
    gene_ids: str,
    include_annotation_type: Optional[list[str]] = None,
    returned_content: Optional[str] = "COMPLETE",
    fasta_filter: Optional[list[str]] = None,
    accession_filter: Optional[list[str]] = None,
    aux_report: Optional[list[str]] = None,
    tabular_reports: Optional[list[str]] = None,
    table_fields: Optional[list[str]] = None,
    table_report_type: Optional[str] = "DATASET_REPORT",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get gene download summary by GeneID

    Parameters
    ----------
    gene_ids : str
        One or more ncbi (e.g., 59067 for IL21, or [59067, 50615] for multiple genes)
    include_annotation_type : list[str]
        Select additional types of annotation to include in the data package.  If uns...
    returned_content : str
        Return either gene-ids, or entire gene metadata
    fasta_filter : list[str]
        Limit the FASTA sequences in the datasets package to these transcript and pro...
    accession_filter : list[str]
        Limit the FASTA sequences and tabular product report in the datasets package ...
    aux_report : list[str]
        list additional reports to include with download. Data report is included by ...
    tabular_reports : list[str]

    table_fields : list[str]
        Specify which fields to include in the tabular report. This is currently depr...
    table_report_type : str
        Specify the report from which the table fields will be taken. This is current...
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
            "gene_ids": gene_ids,
            "include_annotation_type": include_annotation_type,
            "returned_content": returned_content,
            "fasta_filter": fasta_filter,
            "accession_filter": accession_filter,
            "aux_report": aux_report,
            "tabular_reports": tabular_reports,
            "table_fields": table_fields,
            "table_report_type": table_report_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ncbi_datasets_gene_id_download_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ncbi_datasets_gene_id_download_summary"]
