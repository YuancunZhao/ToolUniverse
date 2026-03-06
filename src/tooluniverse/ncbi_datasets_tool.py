import os
import requests
from typing import List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool


# Constants for NCBI Datasets API
NCBI_DATASETS_BASE_URL = "https://api.ncbi.nlm.nih.gov/datasets/v2"
NCBI_DATASETS_ACCEPT_JSON = "application/json"


@register_tool("NCBIDatasetsGeneByIdTool")
class NCBIDatasetsGeneByIdTool(BaseTool):
    """
    Tool to retrieve gene metadata from NCBI Datasets API by gene ID.

    Rate Limits:
    - Default: 5 requests per second (rps)
    - With API key: 10 requests per second (rps)

    API Key:
    Set via NCBI_API_KEY environment variable or pass in tool_config.
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.timeout_seconds = int(
            os.environ.get("NCBI_DATASETS_TIMEOUT", "30"))
        # Get API key from environment or config
        self.api_key = os.environ.get(
            "NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        gene_ids = arguments.get("gene_ids")
        page_size = arguments.get("page_size", 20)
        page_token = arguments.get("page_token")
        accession_filter = arguments.get("accession_filter")
        include_tabular_header = arguments.get("include_tabular_header")
        locus_tags = arguments.get("locus_tags")
        returned_content = arguments.get("returned_content")
        sort_direction = arguments.get("sort_direction")
        sort_field = arguments.get("sort_field")
        table_fields = arguments.get("table_fields")
        tax_search_subtree = arguments.get("tax_search_subtree")

        if not gene_ids:
            return {"error": "`gene_ids` parameter is required."}

        # Ensure gene_ids is a list
        if isinstance(gene_ids, (str, int)):
            gene_ids = [str(gene_ids)]
        else:
            gene_ids = [str(gid) for gid in gene_ids]

        return self._fetch_gene_data_by_id(
            gene_ids=gene_ids,
            page_size=page_size,
            page_token=page_token,
            accession_filter=accession_filter,
            include_tabular_header=include_tabular_header,
            locus_tags=locus_tags,
            returned_content=returned_content,
            sort_direction=sort_direction,
            sort_field=sort_field,
            table_fields=table_fields,
            tax_search_subtree=tax_search_subtree,
        )

    def _fetch_gene_data_by_id(
        self,
        gene_ids: List[str],
        page_size: int,
        page_token: Optional[str],
        accession_filter: Optional[List[str]],
        include_tabular_header: Optional[str],
        locus_tags: Optional[List[str]],
        returned_content: Optional[str],
        sort_direction: Optional[str],
        sort_field: Optional[str],
        table_fields: Optional[List[str]],
        tax_search_subtree: Optional[bool],
    ):
        """
        Fetch gene metadata by NCBI Gene IDs using the
        /gene/id/{gene_ids} endpoint with complete parameter support.
        """
        try:
            # Join gene IDs with commas for URL path
            gene_ids_str = ",".join(gene_ids)
            url = f"{self.base_url}/gene/id/{gene_ids_str}"

            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            if accession_filter:
                params["accession_filter"] = accession_filter
            if include_tabular_header:
                params["include_tabular_header"] = include_tabular_header
            if locus_tags:
                params["locus_tags"] = locus_tags
            if returned_content:
                params["returned_content"] = returned_content
            if sort_direction:
                params["sort.direction"] = sort_direction
            if sort_field:
                params["sort.field"] = sort_field
            if table_fields:
                params["table_fields"] = table_fields
            if tax_search_subtree is not None:
                params["tax_search_subtree"] = (
                    "true" if tax_search_subtree else "false"
                )

            # Add API key as query parameter if available
            if self.api_key:
                params["api_key"] = self.api_key

            headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
            # Alternative: Add API key as header (commented out, using param)
            # if self.api_key:
            #     headers["api-key"] = self.api_key

            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "success": True,
                "data": data,
                "gene_ids": gene_ids,
            }
        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            return {"error": f"HTTP {status}: {http_err}"}
        except Exception as e:
            return {"error": str(e)}


@register_tool("NCBIDatasetsGeneBySymbolTool")
class NCBIDatasetsGeneBySymbolTool(BaseTool):
    """
    Tool to retrieve gene metadata from NCBI Datasets API by gene symbol
    and taxon.

    Rate Limits:
    - Default: 5 requests per second (rps)
    - With API key: 10 requests per second (rps)

    API Key:
    Set via NCBI_API_KEY environment variable or pass in tool_config.
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.timeout_seconds = int(
            os.environ.get("NCBI_DATASETS_TIMEOUT", "30"))
        self.api_key = os.environ.get(
            "NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        symbols = arguments.get("symbols")
        taxon = arguments.get("taxon")
        page_size = arguments.get("page_size", 20)
        page_token = arguments.get("page_token")
        accession_filter = arguments.get("accession_filter")
        include_tabular_header = arguments.get("include_tabular_header")
        locus_tags = arguments.get("locus_tags")
        returned_content = arguments.get("returned_content")
        sort_direction = arguments.get("sort_direction")
        sort_field = arguments.get("sort_field")
        table_fields = arguments.get("table_fields")
        tax_search_subtree = arguments.get("tax_search_subtree")

        if not symbols:
            return {"error": "`symbols` parameter is required."}
        if not taxon:
            return {"error": "`taxon` parameter is required."}

        # Ensure symbols is a list
        if isinstance(symbols, str):
            symbols = [symbols]

        return self._fetch_gene_data_by_symbol(
            symbols=symbols,
            taxon=taxon,
            page_size=page_size,
            page_token=page_token,
            accession_filter=accession_filter,
            include_tabular_header=include_tabular_header,
            locus_tags=locus_tags,
            returned_content=returned_content,
            sort_direction=sort_direction,
            sort_field=sort_field,
            table_fields=table_fields,
            tax_search_subtree=tax_search_subtree,
        )

    def _fetch_gene_data_by_symbol(
        self,
        symbols: List[str],
        taxon: str,
        page_size: int,
        page_token: Optional[str],
        accession_filter: Optional[List[str]],
        include_tabular_header: Optional[str],
        locus_tags: Optional[List[str]],
        returned_content: Optional[str],
        sort_direction: Optional[str],
        sort_field: Optional[str],
        table_fields: Optional[List[str]],
        tax_search_subtree: Optional[bool],
    ):
        """
        Fetch gene metadata by gene symbol and taxon using the
        /gene/symbol/{symbols}/taxon/{taxon} endpoint with complete
        parameter support.
        """
        try:
            # Join symbols with commas for URL path
            symbols_str = ",".join(symbols)
            url = f"{self.base_url}/gene/symbol/{symbols_str}/taxon/{taxon}"

            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            if accession_filter:
                params["accession_filter"] = accession_filter
            if include_tabular_header:
                params["include_tabular_header"] = include_tabular_header
            if locus_tags:
                params["locus_tags"] = locus_tags
            if returned_content:
                params["returned_content"] = returned_content
            if sort_direction:
                params["sort.direction"] = sort_direction
            if sort_field:
                params["sort.field"] = sort_field
            if table_fields:
                params["table_fields"] = table_fields
            if tax_search_subtree is not None:
                params["tax_search_subtree"] = (
                    "true" if tax_search_subtree else "false"
                )
            if self.api_key:
                params["api_key"] = self.api_key

            headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "success": True,
                "data": data,
                "symbols": symbols,
                "taxon": taxon,
            }
        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            return {"error": f"HTTP {status}: {http_err}"}
        except Exception as e:
            return {"error": str(e)}


@register_tool("NCBIDatasetsGeneByAccessionTool")
class NCBIDatasetsGeneByAccessionTool(BaseTool):
    """
    Tool to retrieve gene metadata from NCBI Datasets API by RefSeq
    accession.

    Rate Limits:
    - Default: 5 requests per second (rps)
    - With API key: 10 requests per second (rps)

    API Key:
    Set via NCBI_API_KEY environment variable or pass in tool_config.
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.timeout_seconds = int(
            os.environ.get("NCBI_DATASETS_TIMEOUT", "30"))
        self.api_key = os.environ.get(
            "NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        accessions = arguments.get("accessions")
        page_size = arguments.get("page_size", 20)
        page_token = arguments.get("page_token")
        accession_filter = arguments.get("accession_filter")
        include_tabular_header = arguments.get("include_tabular_header")
        locus_tags = arguments.get("locus_tags")
        returned_content = arguments.get("returned_content")
        sort_direction = arguments.get("sort_direction")
        sort_field = arguments.get("sort_field")
        table_fields = arguments.get("table_fields")
        tax_search_subtree = arguments.get("tax_search_subtree")

        if not accessions:
            return {"error": "`accessions` parameter is required."}

        # Ensure accessions is a list
        if isinstance(accessions, str):
            accessions = [accessions]

        return self._fetch_gene_data_by_accession(
            accessions=accessions,
            page_size=page_size,
            page_token=page_token,
            accession_filter=accession_filter,
            include_tabular_header=include_tabular_header,
            locus_tags=locus_tags,
            returned_content=returned_content,
            sort_direction=sort_direction,
            sort_field=sort_field,
            table_fields=table_fields,
            tax_search_subtree=tax_search_subtree,
        )

    def _fetch_gene_data_by_accession(
        self,
        accessions: List[str],
        page_size: int,
        page_token: Optional[str],
        accession_filter: Optional[List[str]],
        include_tabular_header: Optional[str],
        locus_tags: Optional[List[str]],
        returned_content: Optional[str],
        sort_direction: Optional[str],
        sort_field: Optional[str],
        table_fields: Optional[List[str]],
        tax_search_subtree: Optional[bool],
    ):
        """
        Fetch gene metadata by RefSeq accession using the
        /gene/accession/{accessions} endpoint with complete parameter support.
        """
        try:
            # Join accessions with commas for URL path
            accessions_str = ",".join(accessions)
            url = f"{self.base_url}/gene/accession/{accessions_str}"

            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            if accession_filter:
                params["accession_filter"] = accession_filter
            if include_tabular_header:
                params["include_tabular_header"] = include_tabular_header
            if locus_tags:
                params["locus_tags"] = locus_tags
            if returned_content:
                params["returned_content"] = returned_content
            if sort_direction:
                params["sort.direction"] = sort_direction
            if sort_field:
                params["sort.field"] = sort_field
            if table_fields:
                params["table_fields"] = table_fields
            if tax_search_subtree is not None:
                params["tax_search_subtree"] = (
                    "true" if tax_search_subtree else "false"
                )
            if self.api_key:
                params["api_key"] = self.api_key

            headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "success": True,
                "data": data,
                "accessions": accessions,
            }
        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            return {"error": f"HTTP {status}: {http_err}"}
        except Exception as e:
            return {"error": str(e)}


@register_tool("NCBIDatasetsGenomeReportTool")
class NCBIDatasetsGenomeReportTool(BaseTool):
    """
    Tool to retrieve genome assembly reports from NCBI Datasets API by
    accession.

    Rate Limits:
    - Default: 5 requests per second (rps)
    - With API key: 10 requests per second (rps)

    API Key:
    Set via NCBI_API_KEY environment variable or pass in tool_config.
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.timeout_seconds = int(
            os.environ.get("NCBI_DATASETS_TIMEOUT", "30"))
        self.api_key = os.environ.get(
            "NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        accessions = arguments.get("accessions")
        page_size = arguments.get("page_size", 20)
        page_token = arguments.get("page_token")
        filters_assembly_level = arguments.get("filters_assembly_level")
        filters_assembly_source = arguments.get("filters_assembly_source")
        filters_assembly_version = arguments.get("filters_assembly_version")
        filters_exclude_atypical = arguments.get("filters_exclude_atypical")
        filters_exclude_multi_isolate = arguments.get(
            "filters_exclude_multi_isolate"
        )
        filters_exclude_paired_reports = arguments.get(
            "filters_exclude_paired_reports"
        )
        filters_first_release_date = arguments.get(
            "filters_first_release_date")
        filters_has_annotation = arguments.get("filters_has_annotation")
        filters_is_ictv_exemplar = arguments.get("filters_is_ictv_exemplar")
        filters_is_metagenome_derived = arguments.get(
            "filters_is_metagenome_derived"
        )
        filters_is_type_material = arguments.get("filters_is_type_material")
        filters_last_release_date = arguments.get("filters_last_release_date")
        filters_reference_only = arguments.get("filters_reference_only")
        filters_search_text = arguments.get("filters_search_text")
        filters_type_material_category = arguments.get(
            "filters_type_material_category"
        )
        include_tabular_header = arguments.get("include_tabular_header")
        returned_content = arguments.get("returned_content")
        sort_direction = arguments.get("sort_direction")
        sort_field = arguments.get("sort_field")
        table_fields = arguments.get("table_fields")
        tax_exact_match = arguments.get("tax_exact_match")

        if not accessions:
            return {"error": "`accessions` parameter is required."}

        # Ensure accessions is a list
        if isinstance(accessions, str):
            accessions = [accessions]

        return self._fetch_genome_report(
            accessions=accessions,
            page_size=page_size,
            page_token=page_token,
            filters_assembly_level=filters_assembly_level,
            filters_assembly_source=filters_assembly_source,
            filters_assembly_version=filters_assembly_version,
            filters_exclude_atypical=filters_exclude_atypical,
            filters_exclude_multi_isolate=filters_exclude_multi_isolate,
            filters_exclude_paired_reports=filters_exclude_paired_reports,
            filters_first_release_date=filters_first_release_date,
            filters_has_annotation=filters_has_annotation,
            filters_is_ictv_exemplar=filters_is_ictv_exemplar,
            filters_is_metagenome_derived=filters_is_metagenome_derived,
            filters_is_type_material=filters_is_type_material,
            filters_last_release_date=filters_last_release_date,
            filters_reference_only=filters_reference_only,
            filters_search_text=filters_search_text,
            filters_type_material_category=filters_type_material_category,
            include_tabular_header=include_tabular_header,
            returned_content=returned_content,
            sort_direction=sort_direction,
            sort_field=sort_field,
            table_fields=table_fields,
            tax_exact_match=tax_exact_match,
        )

    def _fetch_genome_report(
        self,
        accessions: List[str],
        page_size: int,
        page_token: Optional[str],
        filters_assembly_level: Optional[List[str]],
        filters_assembly_source: Optional[str],
        filters_assembly_version: Optional[str],
        filters_exclude_atypical: Optional[bool],
        filters_exclude_multi_isolate: Optional[bool],
        filters_exclude_paired_reports: Optional[bool],
        filters_first_release_date: Optional[str],
        filters_has_annotation: Optional[bool],
        filters_is_ictv_exemplar: Optional[bool],
        filters_is_metagenome_derived: Optional[str],
        filters_is_type_material: Optional[bool],
        filters_last_release_date: Optional[str],
        filters_reference_only: Optional[bool],
        filters_search_text: Optional[List[str]],
        filters_type_material_category: Optional[str],
        include_tabular_header: Optional[str],
        returned_content: Optional[str],
        sort_direction: Optional[str],
        sort_field: Optional[str],
        table_fields: Optional[List[str]],
        tax_exact_match: Optional[bool],
    ):
        """
        Fetch genome assembly report by accession using the
        /genome/accession/{accessions}/dataset_report endpoint with complete
        parameter support.
        """
        try:
            # Join accessions with commas for URL path
            accessions_str = ",".join(accessions)
            url = (
                f"{self.base_url}/genome/accession/"
                f"{accessions_str}/dataset_report"
            )

            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            if filters_assembly_level:
                params["filters.assembly_level"] = filters_assembly_level
            if filters_assembly_source:
                params["filters.assembly_source"] = filters_assembly_source
            if filters_assembly_version:
                params["filters.assembly_version"] = filters_assembly_version
            if filters_exclude_atypical is not None:
                params["filters.exclude_atypical"] = (
                    "true" if filters_exclude_atypical else "false"
                )
            if filters_exclude_multi_isolate is not None:
                params["filters.exclude_multi_isolate"] = (
                    "true" if filters_exclude_multi_isolate else "false"
                )
            if filters_exclude_paired_reports is not None:
                params["filters.exclude_paired_reports"] = (
                    "true" if filters_exclude_paired_reports else "false"
                )
            if filters_first_release_date:
                params["filters.first_release_date"] = (
                    filters_first_release_date
                )
            if filters_has_annotation is not None:
                params["filters.has_annotation"] = (
                    "true" if filters_has_annotation else "false"
                )
            if filters_is_ictv_exemplar is not None:
                params["filters.is_ictv_exemplar"] = (
                    "true" if filters_is_ictv_exemplar else "false"
                )
            if filters_is_metagenome_derived:
                params["filters.is_metagenome_derived"] = (
                    filters_is_metagenome_derived
                )
            if filters_is_type_material is not None:
                params["filters.is_type_material"] = (
                    "true" if filters_is_type_material else "false"
                )
            if filters_last_release_date:
                params["filters.last_release_date"] = filters_last_release_date
            if filters_reference_only is not None:
                params["filters.reference_only"] = (
                    "true" if filters_reference_only else "false"
                )
            if filters_search_text:
                params["filters.search_text"] = filters_search_text
            if filters_type_material_category:
                params["filters.type_material_category"] = (
                    filters_type_material_category
                )
            if include_tabular_header:
                params["include_tabular_header"] = include_tabular_header
            if returned_content:
                params["returned_content"] = returned_content
            if sort_direction:
                params["sort.direction"] = sort_direction
            if sort_field:
                params["sort.field"] = sort_field
            if table_fields:
                params["table_fields"] = table_fields
            if tax_exact_match is not None:
                params["tax_exact_match"] = (
                    "true" if tax_exact_match else "false"
                )
            if self.api_key:
                params["api_key"] = self.api_key

            headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "success": True,
                "data": data,
                "accessions": accessions,
            }
        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            return {"error": f"HTTP {status}: {http_err}"}
        except Exception as e:
            return {"error": str(e)}


@register_tool("NCBIDatasetsTaxonomyMetadataTool")
class NCBIDatasetsTaxonomyMetadataTool(BaseTool):
    """
    Tool to retrieve taxonomy metadata from NCBI Datasets API by taxon
    identifier.

    Rate Limits:
    - Default: 5 requests per second (rps)
    - With API key: 10 requests per second (rps)

    API Key:
    Set via NCBI_API_KEY environment variable or pass in tool_config.
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.timeout_seconds = int(
            os.environ.get("NCBI_DATASETS_TIMEOUT", "30"))
        self.api_key = os.environ.get(
            "NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        taxons = arguments.get("taxons")
        page_size = arguments.get("page_size", 20)
        page_token = arguments.get("page_token")
        children = arguments.get("children")
        include_tabular_header = arguments.get("include_tabular_header")
        ranks = arguments.get("ranks")
        returned_content = arguments.get("returned_content")
        table_format = arguments.get("table_format")

        if not taxons:
            return {"error": "`taxons` parameter is required."}

        # Ensure taxons is a list
        if isinstance(taxons, str):
            taxons = [taxons]

        return self._fetch_taxonomy_metadata(
            taxons=taxons,
            page_size=page_size,
            page_token=page_token,
            children=children,
            include_tabular_header=include_tabular_header,
            ranks=ranks,
            returned_content=returned_content,
            table_format=table_format,
        )

    def _fetch_taxonomy_metadata(
        self,
        taxons: List[str],
        page_size: int,
        page_token: Optional[str],
        children: Optional[bool],
        include_tabular_header: Optional[str],
        ranks: Optional[List[str]],
        returned_content: Optional[str],
        table_format: Optional[str],
    ):
        """
        Fetch taxonomy metadata by taxon identifiers using the
        /taxonomy/taxon/{taxons} endpoint with complete parameter support.
        """
        try:
            # Join taxons with commas for URL path
            taxons_str = ",".join(taxons)
            url = f"{self.base_url}/taxonomy/taxon/{taxons_str}"

            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            if children is not None:
                params["children"] = "true" if children else "false"
            if include_tabular_header:
                params["include_tabular_header"] = include_tabular_header
            if ranks:
                params["ranks"] = ranks
            if returned_content:
                params["returned_content"] = returned_content
            if table_format:
                params["table_format"] = table_format
            if self.api_key:
                params["api_key"] = self.api_key

            headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "success": True,
                "data": data,
                "taxons": taxons,
            }
        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            return {"error": f"HTTP {status}: {http_err}"}
        except Exception as e:
            return {"error": str(e)}


@register_tool("NCBIDatasetsVirusGenomeSummaryTool")
class NCBIDatasetsVirusGenomeSummaryTool(BaseTool):
    """
    Tool to retrieve virus genome summary from NCBI Datasets API.

    Rate Limits:
    - Default: 5 requests per second (rps)
    - With API key: 10 requests per second (rps)

    API Key:
    Set via NCBI_API_KEY environment variable or pass in tool_config.
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.timeout_seconds = int(
            os.environ.get("NCBI_DATASETS_TIMEOUT", "30"))
        self.api_key = os.environ.get(
            "NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        taxon = arguments.get("taxon")
        accessions = arguments.get("accessions")
        refseq_only = arguments.get("refseq_only", False)
        annotated_only = arguments.get("annotated_only", False)
        released_since = arguments.get("released_since")
        updated_since = arguments.get("updated_since")
        host = arguments.get("host")
        pangolin_classification = arguments.get("pangolin_classification")
        geo_location = arguments.get("geo_location")
        usa_state = arguments.get("usa_state")
        complete_only = arguments.get("complete_only", False)
        include_sequence = arguments.get("include_sequence")
        aux_report = arguments.get("aux_report")

        if not taxon:
            return {"error": "`taxon` parameter is required."}

        return self._fetch_virus_genome_summary(
            taxon=taxon,
            accessions=accessions,
            refseq_only=refseq_only,
            annotated_only=annotated_only,
            released_since=released_since,
            updated_since=updated_since,
            host=host,
            pangolin_classification=pangolin_classification,
            geo_location=geo_location,
            usa_state=usa_state,
            complete_only=complete_only,
            include_sequence=include_sequence,
            aux_report=aux_report,
        )

    def _fetch_virus_genome_summary(
        self,
        taxon: str,
        accessions: Optional[List[str]],
        refseq_only: bool,
        annotated_only: bool,
        released_since: Optional[str],
        updated_since: Optional[str],
        host: Optional[str],
        pangolin_classification: Optional[str],
        geo_location: Optional[str],
        usa_state: Optional[str],
        complete_only: bool,
        include_sequence: Optional[List[str]],
        aux_report: Optional[List[str]],
    ):
        """
        Fetch virus genome summary by taxon using the
        /virus/taxon/{taxon}/genome endpoint with complete parameter support.
        """
        try:
            url = f"{self.base_url}/virus/taxon/{taxon}/genome"

            params = {}
            if accessions:
                params["accessions"] = accessions
            if refseq_only:
                params["refseq_only"] = "true"
            if annotated_only:
                params["annotated_only"] = "true"
            if released_since:
                params["released_since"] = released_since
            if updated_since:
                params["updated_since"] = updated_since
            if host:
                params["host"] = host
            if pangolin_classification:
                params["pangolin_classification"] = pangolin_classification
            if geo_location:
                params["geo_location"] = geo_location
            if usa_state:
                params["usa_state"] = usa_state
            if complete_only:
                params["complete_only"] = "true"
            if include_sequence:
                params["include_sequence"] = include_sequence
            if aux_report:
                params["aux_report"] = aux_report
            if self.api_key:
                params["api_key"] = self.api_key

            headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "success": True,
                "data": data,
                "taxon": taxon,
            }
        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            return {"error": f"HTTP {status}: {http_err}"}
        except Exception as e:
            return {"error": str(e)}


# ============================================================================
# AUTO-GENERATED TOOLS - Generated by discover_and_generate.py
# ============================================================================

@register_tool("NCBIDatasetsTaxonomyTaxonDatasetReportTool")
class NCBIDatasetsTaxonomyTaxonDatasetReportTool(BaseTool):
    """
    Tool to retrieve taxonomy data report from NCBI Datasets API by taxon.

    Rate Limits:
    - Default: 5 requests per second (rps)
    - With API key: 10 requests per second (rps)

    API Key:
    Set via NCBI_API_KEY environment variable or pass in tool_config.
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.timeout_seconds = int(
            os.environ.get("NCBI_DATASETS_TIMEOUT", "30"))
        self.api_key = os.environ.get(
            "NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        taxons = arguments.get("taxons")
        returned_content = arguments.get("returned_content")
        page_size = arguments.get("page_size", 20)
        include_tabular_header = arguments.get("include_tabular_header")
        page_token = arguments.get("page_token")
        table_format = arguments.get("table_format")
        children = arguments.get("children")
        ranks = arguments.get("ranks")

        if not taxons:
            return {"error": "`taxons` parameter is required."}

        # Ensure taxons is a list
        if isinstance(taxons, str):
            taxons = [taxons]

        return self._fetch_taxonomy_dataset_report(
            taxons=taxons,
            returned_content=returned_content,
            page_size=page_size,
            include_tabular_header=include_tabular_header,
            page_token=page_token,
            table_format=table_format,
            children=children,
            ranks=ranks,
        )

    def _fetch_taxonomy_dataset_report(
        self,
        taxons: List[str],
        returned_content: Optional[str],
        page_size: int,
        include_tabular_header: Optional[str],
        page_token: Optional[str],
        table_format: Optional[str],
        children: Optional[bool],
        ranks: Optional[List[str]],
    ):
        """
        Fetch taxonomy data report by taxon identifiers using the
        /taxonomy/taxon/{taxons}/dataset_report endpoint.
        """
        try:
            # Join taxons with commas for URL path
            taxons_str = ",".join(taxons)
            url = f"{self.base_url}/taxonomy/taxon/{taxons_str}/dataset_report"

            params = {"page_size": page_size}
            if returned_content:
                params["returned_content"] = returned_content
            if page_token:
                params["page_token"] = page_token
            if include_tabular_header:
                params["include_tabular_header"] = include_tabular_header
            if table_format:
                params["table_format"] = table_format
            if children is not None:
                params["children"] = "true" if children else "false"
            if ranks:
                params["ranks"] = ranks
            if self.api_key:
                params["api_key"] = self.api_key

            headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "success": True,
                "data": data,
                "taxons": taxons,
            }
        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            return {"error": f"HTTP {status}: {http_err}"}
        except Exception as e:
            return {"error": str(e)}


# ============================================================================
# AUTO-GENERATED TOOLS - Generated by discover_and_generate.py
# ============================================================================

@register_tool("NCBIDatasetsGeneIdDatasetReportTool")
class NCBIDatasetsGeneIdDatasetReportTool(BaseTool):
    """
    Get dataset reports by gene IDs.
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/id/{gene_ids}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        returned_content = arguments.get("returned_content")
        gene_ids = arguments.get("gene_ids")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(gene_ids, returned_content, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["gene_ids"] = gene_ids
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        gene_ids: str,
        returned_content: Optional[str] = None,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if gene_ids is None:
            raise ValueError("`gene_ids` is required")
        if isinstance(gene_ids, (str, int)):
            gene_ids = [str(gene_ids)]
        else:
            gene_ids = [str(x) for x in gene_ids]
        gene_ids = ",".join(gene_ids)
        
        # Build URL
        url = self.base_url + "/gene/id/{gene_ids}/dataset_report".format(gene_ids=gene_ids)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if returned_content is not None:
            params["returned_content"] = returned_content
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneAccessionDatasetReportTool")
class NCBIDatasetsGeneAccessionDatasetReportTool(BaseTool):
    """
    Get dataset reports by accession IDs
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/accession/{accessions}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        returned_content = arguments.get("returned_content")
        accessions = arguments.get("accessions")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(accessions, returned_content, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str,
        returned_content: Optional[str] = None,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/gene/accession/{accessions}/dataset_report".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if returned_content is not None:
            params["returned_content"] = returned_content
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneTaxonDatasetReportTool")
class NCBIDatasetsGeneTaxonDatasetReportTool(BaseTool):
    """
    Get gene dataset reports by taxonomic identifier
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/taxon/{taxon}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        returned_content = arguments.get("returned_content")
        taxon = arguments.get("taxon")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(taxon, returned_content, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon: str,
        returned_content: Optional[str] = None,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if taxon is None:
            raise ValueError("`taxon` is required")
        # Build URL
        url = self.base_url + "/gene/taxon/{taxon}/dataset_report".format(taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if returned_content is not None:
            params["returned_content"] = returned_content
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneLocusTagDatasetReportTool")
class NCBIDatasetsGeneLocusTagDatasetReportTool(BaseTool):
    """
    Get gene dataset reports by locus tag
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/locus_tag/{locus_tags}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        returned_content = arguments.get("returned_content")
        locus_tags = arguments.get("locus_tags")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(locus_tags, returned_content, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["locus_tags"] = locus_tags
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        locus_tags: str,
        returned_content: Optional[str] = None,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if locus_tags is None:
            raise ValueError("`locus_tags` is required")
        if isinstance(locus_tags, (str, int)):
            locus_tags = [str(locus_tags)]
        else:
            locus_tags = [str(x) for x in locus_tags]
        locus_tags = ",".join(locus_tags)
        
        # Build URL
        url = self.base_url + "/gene/locus_tag/{locus_tags}/dataset_report".format(locus_tags=locus_tags)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if returned_content is not None:
            params["returned_content"] = returned_content
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsVirusTaxonDatasetReportTool")
class NCBIDatasetsVirusTaxonDatasetReportTool(BaseTool):
    """
    Get virus metadata by taxon
    
    Auto-generated by discover_and_generate.py
    Endpoint: /virus/taxon/{taxon}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxon = arguments.get("taxon")
        filter_refseq_only = arguments.get("filter.refseq_only")
        filter_annotated_only = arguments.get("filter.annotated_only")
        filter_released_since = arguments.get("filter.released_since")
        filter_updated_since = arguments.get("filter.updated_since")
        filter_host = arguments.get("filter.host")
        filter_pangolin_classification = arguments.get("filter.pangolin_classification")
        filter_geo_location = arguments.get("filter.geo_location")
        filter_usa_state = arguments.get("filter.usa_state")
        filter_complete_only = arguments.get("filter.complete_only")
        returned_content = arguments.get("returned_content")
        table_fields = arguments.get("table_fields")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        
        try:
            result = self._fetch_data(taxon, filter_refseq_only, filter_annotated_only, filter_released_since, filter_updated_since, filter_host, filter_pangolin_classification, filter_geo_location, filter_usa_state, filter_complete_only, returned_content, table_fields, page_size, page_token)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon: str,
        filter_refseq_only: Optional[str] = None,
        filter_annotated_only: Optional[str] = None,
        filter_released_since: Optional[str] = None,
        filter_updated_since: Optional[str] = None,
        filter_host: Optional[str] = None,
        filter_pangolin_classification: Optional[str] = None,
        filter_geo_location: Optional[str] = None,
        filter_usa_state: Optional[str] = None,
        filter_complete_only: Optional[str] = None,
        returned_content: Optional[str] = None,
        table_fields: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if taxon is None:
            raise ValueError("`taxon` is required")
        # Build URL
        url = self.base_url + "/virus/taxon/{taxon}/dataset_report".format(taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if filter_refseq_only is not None:
            params["filter.refseq_only"] = filter_refseq_only
        if filter_annotated_only is not None:
            params["filter.annotated_only"] = filter_annotated_only
        if filter_released_since is not None:
            params["filter.released_since"] = filter_released_since
        if filter_updated_since is not None:
            params["filter.updated_since"] = filter_updated_since
        if filter_host is not None:
            params["filter.host"] = filter_host
        if filter_pangolin_classification is not None:
            params["filter.pangolin_classification"] = filter_pangolin_classification
        if filter_geo_location is not None:
            params["filter.geo_location"] = filter_geo_location
        if filter_usa_state is not None:
            params["filter.usa_state"] = filter_usa_state
        if filter_complete_only is not None:
            params["filter.complete_only"] = filter_complete_only
        if returned_content is not None:
            params["returned_content"] = returned_content
        if table_fields is not None:
            params["table_fields"] = table_fields
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsVirusAccessionDatasetReportTool")
class NCBIDatasetsVirusAccessionDatasetReportTool(BaseTool):
    """
    Get virus metadata by accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /virus/accession/{accessions}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accessions = arguments.get("accessions")
        filter_refseq_only = arguments.get("filter.refseq_only")
        filter_annotated_only = arguments.get("filter.annotated_only")
        filter_released_since = arguments.get("filter.released_since")
        filter_updated_since = arguments.get("filter.updated_since")
        filter_host = arguments.get("filter.host")
        filter_pangolin_classification = arguments.get("filter.pangolin_classification")
        filter_geo_location = arguments.get("filter.geo_location")
        filter_usa_state = arguments.get("filter.usa_state")
        filter_complete_only = arguments.get("filter.complete_only")
        returned_content = arguments.get("returned_content")
        table_fields = arguments.get("table_fields")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        
        try:
            result = self._fetch_data(accessions, filter_refseq_only, filter_annotated_only, filter_released_since, filter_updated_since, filter_host, filter_pangolin_classification, filter_geo_location, filter_usa_state, filter_complete_only, returned_content, table_fields, page_size, page_token)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str,
        filter_refseq_only: Optional[str] = None,
        filter_annotated_only: Optional[str] = None,
        filter_released_since: Optional[str] = None,
        filter_updated_since: Optional[str] = None,
        filter_host: Optional[str] = None,
        filter_pangolin_classification: Optional[str] = None,
        filter_geo_location: Optional[str] = None,
        filter_usa_state: Optional[str] = None,
        filter_complete_only: Optional[str] = None,
        returned_content: Optional[str] = None,
        table_fields: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/virus/accession/{accessions}/dataset_report".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if filter_refseq_only is not None:
            params["filter.refseq_only"] = filter_refseq_only
        if filter_annotated_only is not None:
            params["filter.annotated_only"] = filter_annotated_only
        if filter_released_since is not None:
            params["filter.released_since"] = filter_released_since
        if filter_updated_since is not None:
            params["filter.updated_since"] = filter_updated_since
        if filter_host is not None:
            params["filter.host"] = filter_host
        if filter_pangolin_classification is not None:
            params["filter.pangolin_classification"] = filter_pangolin_classification
        if filter_geo_location is not None:
            params["filter.geo_location"] = filter_geo_location
        if filter_usa_state is not None:
            params["filter.usa_state"] = filter_usa_state
        if filter_complete_only is not None:
            params["filter.complete_only"] = filter_complete_only
        if returned_content is not None:
            params["returned_content"] = returned_content
        if table_fields is not None:
            params["table_fields"] = table_fields
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeTaxonDatasetReportTool")
class NCBIDatasetsGenomeTaxonDatasetReportTool(BaseTool):
    """
    Get dataset reports by taxons
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/taxon/{taxons}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxons = arguments.get("taxons")
        filters_reference_only = arguments.get("filters.reference_only")
        filters_assembly_source = arguments.get("filters.assembly_source")
        filters_has_annotation = arguments.get("filters.has_annotation")
        filters_exclude_paired_reports = arguments.get("filters.exclude_paired_reports")
        filters_exclude_atypical = arguments.get("filters.exclude_atypical")
        filters_assembly_version = arguments.get("filters.assembly_version")
        filters_assembly_level = arguments.get("filters.assembly_level")
        filters_first_release_date = arguments.get("filters.first_release_date")
        filters_last_release_date = arguments.get("filters.last_release_date")
        filters_search_text = arguments.get("filters.search_text")
        filters_is_metagenome_derived = arguments.get("filters.is_metagenome_derived")
        filters_is_type_material = arguments.get("filters.is_type_material")
        filters_is_ictv_exemplar = arguments.get("filters.is_ictv_exemplar")
        filters_exclude_multi_isolate = arguments.get("filters.exclude_multi_isolate")
        filters_type_material_category = arguments.get("filters.type_material_category")
        tax_exact_match = arguments.get("tax_exact_match")
        table_fields = arguments.get("table_fields")
        returned_content = arguments.get("returned_content")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        include_tabular_header = arguments.get("include_tabular_header")
        
        try:
            result = self._fetch_data(taxons, filters_reference_only, filters_assembly_source, filters_has_annotation, filters_exclude_paired_reports, filters_exclude_atypical, filters_assembly_version, filters_assembly_level, filters_first_release_date, filters_last_release_date, filters_search_text, filters_is_metagenome_derived, filters_is_type_material, filters_is_ictv_exemplar, filters_exclude_multi_isolate, filters_type_material_category, tax_exact_match, table_fields, returned_content, page_size, page_token, sort_field, sort_direction, include_tabular_header)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxons"] = taxons
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxons: str,
        filters_reference_only: Optional[str] = None,
        filters_assembly_source: Optional[str] = None,
        filters_has_annotation: Optional[str] = None,
        filters_exclude_paired_reports: Optional[str] = None,
        filters_exclude_atypical: Optional[str] = None,
        filters_assembly_version: Optional[str] = None,
        filters_assembly_level: Optional[str] = None,
        filters_first_release_date: Optional[str] = None,
        filters_last_release_date: Optional[str] = None,
        filters_search_text: Optional[str] = None,
        filters_is_metagenome_derived: Optional[str] = None,
        filters_is_type_material: Optional[str] = None,
        filters_is_ictv_exemplar: Optional[str] = None,
        filters_exclude_multi_isolate: Optional[str] = None,
        filters_type_material_category: Optional[str] = None,
        tax_exact_match: Optional[str] = None,
        table_fields: Optional[str] = None,
        returned_content: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        include_tabular_header: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if taxons is None:
            raise ValueError("`taxons` is required")
        if isinstance(taxons, (str, int)):
            taxons = [str(taxons)]
        else:
            taxons = [str(x) for x in taxons]
        taxons = ",".join(taxons)
        
        # Build URL
        url = self.base_url + "/genome/taxon/{taxons}/dataset_report".format(taxons=taxons)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if filters_reference_only is not None:
            params["filters.reference_only"] = filters_reference_only
        if filters_assembly_source is not None:
            params["filters.assembly_source"] = filters_assembly_source
        if filters_has_annotation is not None:
            params["filters.has_annotation"] = filters_has_annotation
        if filters_exclude_paired_reports is not None:
            params["filters.exclude_paired_reports"] = filters_exclude_paired_reports
        if filters_exclude_atypical is not None:
            params["filters.exclude_atypical"] = filters_exclude_atypical
        if filters_assembly_version is not None:
            params["filters.assembly_version"] = filters_assembly_version
        if filters_assembly_level is not None:
            params["filters.assembly_level"] = filters_assembly_level
        if filters_first_release_date is not None:
            params["filters.first_release_date"] = filters_first_release_date
        if filters_last_release_date is not None:
            params["filters.last_release_date"] = filters_last_release_date
        if filters_search_text is not None:
            params["filters.search_text"] = filters_search_text
        if filters_is_metagenome_derived is not None:
            params["filters.is_metagenome_derived"] = filters_is_metagenome_derived
        if filters_is_type_material is not None:
            params["filters.is_type_material"] = filters_is_type_material
        if filters_is_ictv_exemplar is not None:
            params["filters.is_ictv_exemplar"] = filters_is_ictv_exemplar
        if filters_exclude_multi_isolate is not None:
            params["filters.exclude_multi_isolate"] = filters_exclude_multi_isolate
        if filters_type_material_category is not None:
            params["filters.type_material_category"] = filters_type_material_category
        if tax_exact_match is not None:
            params["tax_exact_match"] = tax_exact_match
        if table_fields is not None:
            params["table_fields"] = table_fields
        if returned_content is not None:
            params["returned_content"] = returned_content
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeBioprojectDatasetReportTool")
class NCBIDatasetsGenomeBioprojectDatasetReportTool(BaseTool):
    """
    Get dataset reports by bioproject
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/bioproject/{bioprojects}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        bioprojects = arguments.get("bioprojects")
        filters_reference_only = arguments.get("filters.reference_only")
        filters_assembly_source = arguments.get("filters.assembly_source")
        filters_has_annotation = arguments.get("filters.has_annotation")
        filters_exclude_paired_reports = arguments.get("filters.exclude_paired_reports")
        filters_exclude_atypical = arguments.get("filters.exclude_atypical")
        filters_assembly_version = arguments.get("filters.assembly_version")
        filters_assembly_level = arguments.get("filters.assembly_level")
        filters_first_release_date = arguments.get("filters.first_release_date")
        filters_last_release_date = arguments.get("filters.last_release_date")
        filters_search_text = arguments.get("filters.search_text")
        filters_is_metagenome_derived = arguments.get("filters.is_metagenome_derived")
        filters_is_type_material = arguments.get("filters.is_type_material")
        filters_is_ictv_exemplar = arguments.get("filters.is_ictv_exemplar")
        filters_exclude_multi_isolate = arguments.get("filters.exclude_multi_isolate")
        filters_type_material_category = arguments.get("filters.type_material_category")
        tax_exact_match = arguments.get("tax_exact_match")
        table_fields = arguments.get("table_fields")
        returned_content = arguments.get("returned_content")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        include_tabular_header = arguments.get("include_tabular_header")
        
        try:
            result = self._fetch_data(bioprojects, filters_reference_only, filters_assembly_source, filters_has_annotation, filters_exclude_paired_reports, filters_exclude_atypical, filters_assembly_version, filters_assembly_level, filters_first_release_date, filters_last_release_date, filters_search_text, filters_is_metagenome_derived, filters_is_type_material, filters_is_ictv_exemplar, filters_exclude_multi_isolate, filters_type_material_category, tax_exact_match, table_fields, returned_content, page_size, page_token, sort_field, sort_direction, include_tabular_header)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["bioprojects"] = bioprojects
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        bioprojects: str,
        filters_reference_only: Optional[str] = None,
        filters_assembly_source: Optional[str] = None,
        filters_has_annotation: Optional[str] = None,
        filters_exclude_paired_reports: Optional[str] = None,
        filters_exclude_atypical: Optional[str] = None,
        filters_assembly_version: Optional[str] = None,
        filters_assembly_level: Optional[str] = None,
        filters_first_release_date: Optional[str] = None,
        filters_last_release_date: Optional[str] = None,
        filters_search_text: Optional[str] = None,
        filters_is_metagenome_derived: Optional[str] = None,
        filters_is_type_material: Optional[str] = None,
        filters_is_ictv_exemplar: Optional[str] = None,
        filters_exclude_multi_isolate: Optional[str] = None,
        filters_type_material_category: Optional[str] = None,
        tax_exact_match: Optional[str] = None,
        table_fields: Optional[str] = None,
        returned_content: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        include_tabular_header: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if bioprojects is None:
            raise ValueError("`bioprojects` is required")
        if isinstance(bioprojects, (str, int)):
            bioprojects = [str(bioprojects)]
        else:
            bioprojects = [str(x) for x in bioprojects]
        bioprojects = ",".join(bioprojects)
        
        # Build URL
        url = self.base_url + "/genome/bioproject/{bioprojects}/dataset_report".format(bioprojects=bioprojects)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if filters_reference_only is not None:
            params["filters.reference_only"] = filters_reference_only
        if filters_assembly_source is not None:
            params["filters.assembly_source"] = filters_assembly_source
        if filters_has_annotation is not None:
            params["filters.has_annotation"] = filters_has_annotation
        if filters_exclude_paired_reports is not None:
            params["filters.exclude_paired_reports"] = filters_exclude_paired_reports
        if filters_exclude_atypical is not None:
            params["filters.exclude_atypical"] = filters_exclude_atypical
        if filters_assembly_version is not None:
            params["filters.assembly_version"] = filters_assembly_version
        if filters_assembly_level is not None:
            params["filters.assembly_level"] = filters_assembly_level
        if filters_first_release_date is not None:
            params["filters.first_release_date"] = filters_first_release_date
        if filters_last_release_date is not None:
            params["filters.last_release_date"] = filters_last_release_date
        if filters_search_text is not None:
            params["filters.search_text"] = filters_search_text
        if filters_is_metagenome_derived is not None:
            params["filters.is_metagenome_derived"] = filters_is_metagenome_derived
        if filters_is_type_material is not None:
            params["filters.is_type_material"] = filters_is_type_material
        if filters_is_ictv_exemplar is not None:
            params["filters.is_ictv_exemplar"] = filters_is_ictv_exemplar
        if filters_exclude_multi_isolate is not None:
            params["filters.exclude_multi_isolate"] = filters_exclude_multi_isolate
        if filters_type_material_category is not None:
            params["filters.type_material_category"] = filters_type_material_category
        if tax_exact_match is not None:
            params["tax_exact_match"] = tax_exact_match
        if table_fields is not None:
            params["table_fields"] = table_fields
        if returned_content is not None:
            params["returned_content"] = returned_content
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeBiosampleDatasetReportTool")
class NCBIDatasetsGenomeBiosampleDatasetReportTool(BaseTool):
    """
    Get dataset reports by biosample id
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/biosample/{biosample_ids}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        biosample_ids = arguments.get("biosample_ids")
        filters_reference_only = arguments.get("filters.reference_only")
        filters_assembly_source = arguments.get("filters.assembly_source")
        filters_has_annotation = arguments.get("filters.has_annotation")
        filters_exclude_paired_reports = arguments.get("filters.exclude_paired_reports")
        filters_exclude_atypical = arguments.get("filters.exclude_atypical")
        filters_assembly_version = arguments.get("filters.assembly_version")
        filters_assembly_level = arguments.get("filters.assembly_level")
        filters_first_release_date = arguments.get("filters.first_release_date")
        filters_last_release_date = arguments.get("filters.last_release_date")
        filters_search_text = arguments.get("filters.search_text")
        filters_is_metagenome_derived = arguments.get("filters.is_metagenome_derived")
        filters_is_type_material = arguments.get("filters.is_type_material")
        filters_is_ictv_exemplar = arguments.get("filters.is_ictv_exemplar")
        filters_exclude_multi_isolate = arguments.get("filters.exclude_multi_isolate")
        filters_type_material_category = arguments.get("filters.type_material_category")
        tax_exact_match = arguments.get("tax_exact_match")
        table_fields = arguments.get("table_fields")
        returned_content = arguments.get("returned_content")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        include_tabular_header = arguments.get("include_tabular_header")
        
        try:
            result = self._fetch_data(biosample_ids, filters_reference_only, filters_assembly_source, filters_has_annotation, filters_exclude_paired_reports, filters_exclude_atypical, filters_assembly_version, filters_assembly_level, filters_first_release_date, filters_last_release_date, filters_search_text, filters_is_metagenome_derived, filters_is_type_material, filters_is_ictv_exemplar, filters_exclude_multi_isolate, filters_type_material_category, tax_exact_match, table_fields, returned_content, page_size, page_token, sort_field, sort_direction, include_tabular_header)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["biosample_ids"] = biosample_ids
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        biosample_ids: str,
        filters_reference_only: Optional[str] = None,
        filters_assembly_source: Optional[str] = None,
        filters_has_annotation: Optional[str] = None,
        filters_exclude_paired_reports: Optional[str] = None,
        filters_exclude_atypical: Optional[str] = None,
        filters_assembly_version: Optional[str] = None,
        filters_assembly_level: Optional[str] = None,
        filters_first_release_date: Optional[str] = None,
        filters_last_release_date: Optional[str] = None,
        filters_search_text: Optional[str] = None,
        filters_is_metagenome_derived: Optional[str] = None,
        filters_is_type_material: Optional[str] = None,
        filters_is_ictv_exemplar: Optional[str] = None,
        filters_exclude_multi_isolate: Optional[str] = None,
        filters_type_material_category: Optional[str] = None,
        tax_exact_match: Optional[str] = None,
        table_fields: Optional[str] = None,
        returned_content: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        include_tabular_header: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if biosample_ids is None:
            raise ValueError("`biosample_ids` is required")
        if isinstance(biosample_ids, (str, int)):
            biosample_ids = [str(biosample_ids)]
        else:
            biosample_ids = [str(x) for x in biosample_ids]
        biosample_ids = ",".join(biosample_ids)
        
        # Build URL
        url = self.base_url + "/genome/biosample/{biosample_ids}/dataset_report".format(biosample_ids=biosample_ids)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if filters_reference_only is not None:
            params["filters.reference_only"] = filters_reference_only
        if filters_assembly_source is not None:
            params["filters.assembly_source"] = filters_assembly_source
        if filters_has_annotation is not None:
            params["filters.has_annotation"] = filters_has_annotation
        if filters_exclude_paired_reports is not None:
            params["filters.exclude_paired_reports"] = filters_exclude_paired_reports
        if filters_exclude_atypical is not None:
            params["filters.exclude_atypical"] = filters_exclude_atypical
        if filters_assembly_version is not None:
            params["filters.assembly_version"] = filters_assembly_version
        if filters_assembly_level is not None:
            params["filters.assembly_level"] = filters_assembly_level
        if filters_first_release_date is not None:
            params["filters.first_release_date"] = filters_first_release_date
        if filters_last_release_date is not None:
            params["filters.last_release_date"] = filters_last_release_date
        if filters_search_text is not None:
            params["filters.search_text"] = filters_search_text
        if filters_is_metagenome_derived is not None:
            params["filters.is_metagenome_derived"] = filters_is_metagenome_derived
        if filters_is_type_material is not None:
            params["filters.is_type_material"] = filters_is_type_material
        if filters_is_ictv_exemplar is not None:
            params["filters.is_ictv_exemplar"] = filters_is_ictv_exemplar
        if filters_exclude_multi_isolate is not None:
            params["filters.exclude_multi_isolate"] = filters_exclude_multi_isolate
        if filters_type_material_category is not None:
            params["filters.type_material_category"] = filters_type_material_category
        if tax_exact_match is not None:
            params["tax_exact_match"] = tax_exact_match
        if table_fields is not None:
            params["table_fields"] = table_fields
        if returned_content is not None:
            params["returned_content"] = returned_content
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeWgsDatasetReportTool")
class NCBIDatasetsGenomeWgsDatasetReportTool(BaseTool):
    """
    Get dataset reports by wgs accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/wgs/{wgs_accessions}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        wgs_accessions = arguments.get("wgs_accessions")
        filters_reference_only = arguments.get("filters.reference_only")
        filters_assembly_source = arguments.get("filters.assembly_source")
        filters_has_annotation = arguments.get("filters.has_annotation")
        filters_exclude_paired_reports = arguments.get("filters.exclude_paired_reports")
        filters_exclude_atypical = arguments.get("filters.exclude_atypical")
        filters_assembly_version = arguments.get("filters.assembly_version")
        filters_assembly_level = arguments.get("filters.assembly_level")
        filters_first_release_date = arguments.get("filters.first_release_date")
        filters_last_release_date = arguments.get("filters.last_release_date")
        filters_search_text = arguments.get("filters.search_text")
        filters_is_metagenome_derived = arguments.get("filters.is_metagenome_derived")
        filters_is_type_material = arguments.get("filters.is_type_material")
        filters_is_ictv_exemplar = arguments.get("filters.is_ictv_exemplar")
        filters_exclude_multi_isolate = arguments.get("filters.exclude_multi_isolate")
        filters_type_material_category = arguments.get("filters.type_material_category")
        tax_exact_match = arguments.get("tax_exact_match")
        table_fields = arguments.get("table_fields")
        returned_content = arguments.get("returned_content")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        include_tabular_header = arguments.get("include_tabular_header")
        
        try:
            result = self._fetch_data(wgs_accessions, filters_reference_only, filters_assembly_source, filters_has_annotation, filters_exclude_paired_reports, filters_exclude_atypical, filters_assembly_version, filters_assembly_level, filters_first_release_date, filters_last_release_date, filters_search_text, filters_is_metagenome_derived, filters_is_type_material, filters_is_ictv_exemplar, filters_exclude_multi_isolate, filters_type_material_category, tax_exact_match, table_fields, returned_content, page_size, page_token, sort_field, sort_direction, include_tabular_header)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["wgs_accessions"] = wgs_accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        wgs_accessions: str,
        filters_reference_only: Optional[str] = None,
        filters_assembly_source: Optional[str] = None,
        filters_has_annotation: Optional[str] = None,
        filters_exclude_paired_reports: Optional[str] = None,
        filters_exclude_atypical: Optional[str] = None,
        filters_assembly_version: Optional[str] = None,
        filters_assembly_level: Optional[str] = None,
        filters_first_release_date: Optional[str] = None,
        filters_last_release_date: Optional[str] = None,
        filters_search_text: Optional[str] = None,
        filters_is_metagenome_derived: Optional[str] = None,
        filters_is_type_material: Optional[str] = None,
        filters_is_ictv_exemplar: Optional[str] = None,
        filters_exclude_multi_isolate: Optional[str] = None,
        filters_type_material_category: Optional[str] = None,
        tax_exact_match: Optional[str] = None,
        table_fields: Optional[str] = None,
        returned_content: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        include_tabular_header: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if wgs_accessions is None:
            raise ValueError("`wgs_accessions` is required")
        if isinstance(wgs_accessions, (str, int)):
            wgs_accessions = [str(wgs_accessions)]
        else:
            wgs_accessions = [str(x) for x in wgs_accessions]
        wgs_accessions = ",".join(wgs_accessions)
        
        # Build URL
        url = self.base_url + "/genome/wgs/{wgs_accessions}/dataset_report".format(wgs_accessions=wgs_accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if filters_reference_only is not None:
            params["filters.reference_only"] = filters_reference_only
        if filters_assembly_source is not None:
            params["filters.assembly_source"] = filters_assembly_source
        if filters_has_annotation is not None:
            params["filters.has_annotation"] = filters_has_annotation
        if filters_exclude_paired_reports is not None:
            params["filters.exclude_paired_reports"] = filters_exclude_paired_reports
        if filters_exclude_atypical is not None:
            params["filters.exclude_atypical"] = filters_exclude_atypical
        if filters_assembly_version is not None:
            params["filters.assembly_version"] = filters_assembly_version
        if filters_assembly_level is not None:
            params["filters.assembly_level"] = filters_assembly_level
        if filters_first_release_date is not None:
            params["filters.first_release_date"] = filters_first_release_date
        if filters_last_release_date is not None:
            params["filters.last_release_date"] = filters_last_release_date
        if filters_search_text is not None:
            params["filters.search_text"] = filters_search_text
        if filters_is_metagenome_derived is not None:
            params["filters.is_metagenome_derived"] = filters_is_metagenome_derived
        if filters_is_type_material is not None:
            params["filters.is_type_material"] = filters_is_type_material
        if filters_is_ictv_exemplar is not None:
            params["filters.is_ictv_exemplar"] = filters_is_ictv_exemplar
        if filters_exclude_multi_isolate is not None:
            params["filters.exclude_multi_isolate"] = filters_exclude_multi_isolate
        if filters_type_material_category is not None:
            params["filters.type_material_category"] = filters_type_material_category
        if tax_exact_match is not None:
            params["tax_exact_match"] = tax_exact_match
        if table_fields is not None:
            params["table_fields"] = table_fields
        if returned_content is not None:
            params["returned_content"] = returned_content
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()




# ============================================================================
# AUTO-GENERATED TOOLS - Generated by discover_and_generate.py
# ============================================================================

@register_tool("NCBIDatasetsGenomeAssemblyNameDatasetReportTool")
class NCBIDatasetsGenomeAssemblyNameDatasetReportTool(BaseTool):
    """
    Get dataset reports by assembly name (exact)
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/assembly_name/{assembly_names}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        assembly_names = arguments.get("assembly_names")
        filters_reference_only = arguments.get("filters.reference_only")
        filters_assembly_source = arguments.get("filters.assembly_source")
        filters_has_annotation = arguments.get("filters.has_annotation")
        filters_exclude_paired_reports = arguments.get("filters.exclude_paired_reports")
        filters_exclude_atypical = arguments.get("filters.exclude_atypical")
        filters_assembly_version = arguments.get("filters.assembly_version")
        filters_assembly_level = arguments.get("filters.assembly_level")
        filters_first_release_date = arguments.get("filters.first_release_date")
        filters_last_release_date = arguments.get("filters.last_release_date")
        filters_search_text = arguments.get("filters.search_text")
        filters_is_metagenome_derived = arguments.get("filters.is_metagenome_derived")
        filters_is_type_material = arguments.get("filters.is_type_material")
        filters_is_ictv_exemplar = arguments.get("filters.is_ictv_exemplar")
        filters_exclude_multi_isolate = arguments.get("filters.exclude_multi_isolate")
        filters_type_material_category = arguments.get("filters.type_material_category")
        tax_exact_match = arguments.get("tax_exact_match")
        table_fields = arguments.get("table_fields")
        returned_content = arguments.get("returned_content")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        include_tabular_header = arguments.get("include_tabular_header")
        
        try:
            result = self._fetch_data(assembly_names, filters_reference_only, filters_assembly_source, filters_has_annotation, filters_exclude_paired_reports, filters_exclude_atypical, filters_assembly_version, filters_assembly_level, filters_first_release_date, filters_last_release_date, filters_search_text, filters_is_metagenome_derived, filters_is_type_material, filters_is_ictv_exemplar, filters_exclude_multi_isolate, filters_type_material_category, tax_exact_match, table_fields, returned_content, page_size, page_token, sort_field, sort_direction, include_tabular_header)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["assembly_names"] = assembly_names
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        assembly_names: str,
        filters_reference_only: Optional[str] = None,
        filters_assembly_source: Optional[str] = None,
        filters_has_annotation: Optional[str] = None,
        filters_exclude_paired_reports: Optional[str] = None,
        filters_exclude_atypical: Optional[str] = None,
        filters_assembly_version: Optional[str] = None,
        filters_assembly_level: Optional[str] = None,
        filters_first_release_date: Optional[str] = None,
        filters_last_release_date: Optional[str] = None,
        filters_search_text: Optional[str] = None,
        filters_is_metagenome_derived: Optional[str] = None,
        filters_is_type_material: Optional[str] = None,
        filters_is_ictv_exemplar: Optional[str] = None,
        filters_exclude_multi_isolate: Optional[str] = None,
        filters_type_material_category: Optional[str] = None,
        tax_exact_match: Optional[str] = None,
        table_fields: Optional[str] = None,
        returned_content: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        include_tabular_header: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if assembly_names is None:
            raise ValueError("`assembly_names` is required")
        if isinstance(assembly_names, (str, int)):
            assembly_names = [str(assembly_names)]
        else:
            assembly_names = [str(x) for x in assembly_names]
        assembly_names = ",".join(assembly_names)
        
        # Build URL
        url = self.base_url + "/genome/assembly_name/{assembly_names}/dataset_report".format(assembly_names=assembly_names)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if filters_reference_only is not None:
            params["filters.reference_only"] = filters_reference_only
        if filters_assembly_source is not None:
            params["filters.assembly_source"] = filters_assembly_source
        if filters_has_annotation is not None:
            params["filters.has_annotation"] = filters_has_annotation
        if filters_exclude_paired_reports is not None:
            params["filters.exclude_paired_reports"] = filters_exclude_paired_reports
        if filters_exclude_atypical is not None:
            params["filters.exclude_atypical"] = filters_exclude_atypical
        if filters_assembly_version is not None:
            params["filters.assembly_version"] = filters_assembly_version
        if filters_assembly_level is not None:
            params["filters.assembly_level"] = filters_assembly_level
        if filters_first_release_date is not None:
            params["filters.first_release_date"] = filters_first_release_date
        if filters_last_release_date is not None:
            params["filters.last_release_date"] = filters_last_release_date
        if filters_search_text is not None:
            params["filters.search_text"] = filters_search_text
        if filters_is_metagenome_derived is not None:
            params["filters.is_metagenome_derived"] = filters_is_metagenome_derived
        if filters_is_type_material is not None:
            params["filters.is_type_material"] = filters_is_type_material
        if filters_is_ictv_exemplar is not None:
            params["filters.is_ictv_exemplar"] = filters_is_ictv_exemplar
        if filters_exclude_multi_isolate is not None:
            params["filters.exclude_multi_isolate"] = filters_exclude_multi_isolate
        if filters_type_material_category is not None:
            params["filters.type_material_category"] = filters_type_material_category
        if tax_exact_match is not None:
            params["tax_exact_match"] = tax_exact_match
        if table_fields is not None:
            params["table_fields"] = table_fields
        if returned_content is not None:
            params["returned_content"] = returned_content
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneSymbolTaxonDatasetReportTool")
class NCBIDatasetsGeneSymbolTaxonDatasetReportTool(BaseTool):
    """
    Get dataset reports by taxons.
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/symbol/{symbols}/taxon/{taxon}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        returned_content = arguments.get("returned_content")
        symbols = arguments.get("symbols")
        taxon = arguments.get("taxon")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(symbols, taxon, returned_content, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["symbols"] = symbols
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        symbols: str,
        taxon: str,
        returned_content: Optional[str] = None,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if symbols is None:
            raise ValueError("`symbols` is required")
        if isinstance(symbols, (str, int)):
            symbols = [str(symbols)]
        else:
            symbols = [str(x) for x in symbols]
        symbols = ",".join(symbols)
        
        # Build URL
        url = self.base_url + "/gene/symbol/{symbols}/taxon/{taxon}/dataset_report".format(symbols=symbols, taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if returned_content is not None:
            params["returned_content"] = returned_content
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeAccessionRevisionHistoryTool")
class NCBIDatasetsGenomeAccessionRevisionHistoryTool(BaseTool):
    """
    Get a revision history for a genome assembly by genome assembly accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/accession/{accession}/revision_history
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accession = arguments.get("accession")
        
        try:
            result = self._fetch_data(accession)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accession"] = accession
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accession: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if accession is None:
            raise ValueError("`accession` is required")
        # Build URL
        url = self.base_url + "/genome/accession/{accession}/revision_history".format(accession=accession)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeSequenceAccessionSequenceAssembliesTool")
class NCBIDatasetsGenomeSequenceAccessionSequenceAssembliesTool(BaseTool):
    """
    Get assembly accessions for a sequence accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/sequence_accession/{accession}/sequence_assemblies
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accession = arguments.get("accession")
        
        try:
            result = self._fetch_data(accession)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accession"] = accession
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accession: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if accession is None:
            raise ValueError("`accession` is required")
        # Build URL
        url = self.base_url + "/genome/sequence_accession/{accession}/sequence_assemblies".format(accession=accession)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeAccessionLinksTool")
class NCBIDatasetsGenomeAccessionLinksTool(BaseTool):
    """
    Get assembly links by accessions
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/accession/{accessions}/links
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accessions = arguments.get("accessions")
        
        try:
            result = self._fetch_data(accessions)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/genome/accession/{accessions}/links".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeTaxonCheckmHistogramTool")
class NCBIDatasetsGenomeTaxonCheckmHistogramTool(BaseTool):
    """
    Get CheckM histogram by species taxon
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/taxon/{species_taxon}/checkm_histogram
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        species_taxon = arguments.get("species_taxon")
        
        try:
            result = self._fetch_data(species_taxon)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["species_taxon"] = species_taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        species_taxon: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if species_taxon is None:
            raise ValueError("`species_taxon` is required")
        # Build URL
        url = self.base_url + "/genome/taxon/{species_taxon}/checkm_histogram".format(species_taxon=species_taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeAccessionCheckTool")
class NCBIDatasetsGenomeAccessionCheckTool(BaseTool):
    """
    Check the validity of genome accessions
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/accession/{accessions}/check
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accessions = arguments.get("accessions")
        
        try:
            result = self._fetch_data(accessions)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/genome/accession/{accessions}/check".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneTaxonCountsTool")
class NCBIDatasetsGeneTaxonCountsTool(BaseTool):
    """
    Get gene counts by taxonomic identifier
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/taxon/{taxon}/counts
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxon = arguments.get("taxon")
        
        try:
            result = self._fetch_data(taxon)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if taxon is None:
            raise ValueError("`taxon` is required")
        # Build URL
        url = self.base_url + "/gene/taxon/{taxon}/counts".format(taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneIdLinksTool")
class NCBIDatasetsGeneIdLinksTool(BaseTool):
    """
    Get gene links by gene ID
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/id/{gene_ids}/links
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        gene_ids = arguments.get("gene_ids")
        
        try:
            result = self._fetch_data(gene_ids)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["gene_ids"] = gene_ids
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        gene_ids: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if gene_ids is None:
            raise ValueError("`gene_ids` is required")
        if isinstance(gene_ids, (str, int)):
            gene_ids = [str(gene_ids)]
        else:
            gene_ids = [str(x) for x in gene_ids]
        gene_ids = ",".join(gene_ids)
        
        # Build URL
        url = self.base_url + "/gene/id/{gene_ids}/links".format(gene_ids=gene_ids)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeAccessionAnnotationSummaryTool")
class NCBIDatasetsGenomeAccessionAnnotationSummaryTool(BaseTool):
    """
    Get genome annotation report summary information by genome assembly accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/accession/{accession}/annotation_summary
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accession = arguments.get("accession")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(accession, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accession"] = accession
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accession: str,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if accession is None:
            raise ValueError("`accession` is required")
        # Build URL
        url = self.base_url + "/genome/accession/{accession}/annotation_summary".format(accession=accession)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsTaxonomyTaxonFilteredSubtreeTool")
class NCBIDatasetsTaxonomyTaxonFilteredSubtreeTool(BaseTool):
    """
    Use taxonomic identifiers to get a filtered taxonomic subtree
    
    Auto-generated by discover_and_generate.py
    Endpoint: /taxonomy/taxon/{taxons}/filtered_subtree
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxons = arguments.get("taxons")
        rank_limits = arguments.get("rank_limits")
        include_incertae_sedis = arguments.get("include_incertae_sedis")
        
        try:
            result = self._fetch_data(taxons, rank_limits, include_incertae_sedis)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxons"] = taxons
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxons: str,
        rank_limits: Optional[str] = None,
        include_incertae_sedis: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if taxons is None:
            raise ValueError("`taxons` is required")
        if isinstance(taxons, (str, int)):
            taxons = [str(taxons)]
        else:
            taxons = [str(x) for x in taxons]
        taxons = ",".join(taxons)
        
        # Build URL
        url = self.base_url + "/taxonomy/taxon/{taxons}/filtered_subtree".format(taxons=taxons)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if rank_limits is not None:
            params["rank_limits"] = rank_limits
        if include_incertae_sedis is not None:
            params["include_incertae_sedis"] = include_incertae_sedis
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsTaxonomyTaxonSuggestTool")
class NCBIDatasetsTaxonomyTaxonSuggestTool(BaseTool):
    """
    Get a list of taxonomy names and IDs given a partial taxonomic name
    
    Auto-generated by discover_and_generate.py
    Endpoint: /taxonomy/taxon_suggest/{taxon_query}
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxon_query = arguments.get("taxon_query")
        tax_rank_filter = arguments.get("tax_rank_filter")
        taxon_resource_filter = arguments.get("taxon_resource_filter")
        exact_match = arguments.get("exact_match")
        
        try:
            result = self._fetch_data(taxon_query, tax_rank_filter, taxon_resource_filter, exact_match)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon_query"] = taxon_query
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon_query: str,
        tax_rank_filter: Optional[str] = None,
        taxon_resource_filter: Optional[str] = None,
        exact_match: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if taxon_query is None:
            raise ValueError("`taxon_query` is required")
        # Build URL
        url = self.base_url + "/taxonomy/taxon_suggest/{taxon_query}".format(taxon_query=taxon_query)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if tax_rank_filter is not None:
            params["tax_rank_filter"] = tax_rank_filter
        if taxon_resource_filter is not None:
            params["taxon_resource_filter"] = taxon_resource_filter
        if exact_match is not None:
            params["exact_match"] = exact_match
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsTaxonomyTaxonLinksTool")
class NCBIDatasetsTaxonomyTaxonLinksTool(BaseTool):
    """
    Retrieve external links associated with a taxonomic identifier.
    
    Auto-generated by discover_and_generate.py
    Endpoint: /taxonomy/taxon/{taxon}/links
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxon = arguments.get("taxon")
        
        try:
            result = self._fetch_data(taxon)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if taxon is None:
            raise ValueError("`taxon` is required")
        # Build URL
        url = self.base_url + "/taxonomy/taxon/{taxon}/links".format(taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsTaxonomyTaxonImageMetadataTool")
class NCBIDatasetsTaxonomyTaxonImageMetadataTool(BaseTool):
    """
    Retrieve image metadata associated with a taxonomic identifier
    
    Auto-generated by discover_and_generate.py
    Endpoint: /taxonomy/taxon/{taxon}/image/metadata
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxon = arguments.get("taxon")
        
        try:
            result = self._fetch_data(taxon)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if taxon is None:
            raise ValueError("`taxon` is required")
        # Build URL
        url = self.base_url + "/taxonomy/taxon/{taxon}/image/metadata".format(taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsVirusAccessionCheckTool")
class NCBIDatasetsVirusAccessionCheckTool(BaseTool):
    """
    Check available viruses by accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /virus/accession/{accessions}/check
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accessions = arguments.get("accessions")
        
        try:
            result = self._fetch_data(accessions)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/virus/accession/{accessions}/check".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeAccessionSequenceReportsTool")
class NCBIDatasetsGenomeAccessionSequenceReportsTool(BaseTool):
    """
    Get genome sequence reports by genome assembly accessions
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/accession/{accession}/sequence_reports
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accession = arguments.get("accession")
        chromosomes = arguments.get("chromosomes")
        role_filters = arguments.get("role_filters")
        table_fields = arguments.get("table_fields")
        count_assembly_unplaced = arguments.get("count_assembly_unplaced")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        include_tabular_header = arguments.get("include_tabular_header")
        
        try:
            result = self._fetch_data(accession, chromosomes, role_filters, table_fields, count_assembly_unplaced, page_size, page_token, include_tabular_header)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accession"] = accession
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accession: str,
        chromosomes: Optional[str] = None,
        role_filters: Optional[str] = None,
        table_fields: Optional[str] = None,
        count_assembly_unplaced: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        include_tabular_header: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if accession is None:
            raise ValueError("`accession` is required")
        # Build URL
        url = self.base_url + "/genome/accession/{accession}/sequence_reports".format(accession=accession)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if chromosomes is not None:
            params["chromosomes"] = chromosomes
        if role_filters is not None:
            params["role_filters"] = role_filters
        if table_fields is not None:
            params["table_fields"] = table_fields
        if count_assembly_unplaced is not None:
            params["count_assembly_unplaced"] = count_assembly_unplaced
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneIdOrthologsTool")
class NCBIDatasetsGeneIdOrthologsTool(BaseTool):
    """
    Get gene orthologs by gene ID
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/id/{gene_id}/orthologs
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        gene_id = arguments.get("gene_id")
        returned_content = arguments.get("returned_content")
        taxon_filter = arguments.get("taxon_filter")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        
        try:
            result = self._fetch_data(gene_id, returned_content, taxon_filter, page_size, page_token)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["gene_id"] = gene_id
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        gene_id: str,
        returned_content: Optional[str] = None,
        taxon_filter: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if gene_id is None:
            raise ValueError("`gene_id` is required")
        # Build URL
        url = self.base_url + "/gene/id/{gene_id}/orthologs".format(gene_id=gene_id)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if returned_content is not None:
            params["returned_content"] = returned_content
        if taxon_filter is not None:
            params["taxon_filter"] = taxon_filter
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsTaxonomyTaxonNameReportTool")
class NCBIDatasetsTaxonomyTaxonNameReportTool(BaseTool):
    """
    Use taxonomic identifiers to get taxonomic names data report
    
    Auto-generated by discover_and_generate.py
    Endpoint: /taxonomy/taxon/{taxons}/name_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxons = arguments.get("taxons")
        returned_content = arguments.get("returned_content")
        page_size = arguments.get("page_size")
        include_tabular_header = arguments.get("include_tabular_header")
        page_token = arguments.get("page_token")
        table_format = arguments.get("table_format")
        children = arguments.get("children")
        ranks = arguments.get("ranks")
        
        try:
            result = self._fetch_data(taxons, returned_content, page_size, include_tabular_header, page_token, table_format, children, ranks)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxons"] = taxons
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxons: str,
        returned_content: Optional[str] = None,
        page_size: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_token: Optional[str] = None,
        table_format: Optional[str] = None,
        children: Optional[str] = None,
        ranks: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if taxons is None:
            raise ValueError("`taxons` is required")
        if isinstance(taxons, (str, int)):
            taxons = [str(taxons)]
        else:
            taxons = [str(x) for x in taxons]
        taxons = ",".join(taxons)
        
        # Build URL
        url = self.base_url + "/taxonomy/taxon/{taxons}/name_report".format(taxons=taxons)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if returned_content is not None:
            params["returned_content"] = returned_content
        if page_size is not None:
            params["page_size"] = page_size
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_token is not None:
            params["page_token"] = page_token
        if table_format is not None:
            params["table_format"] = table_format
        if children is not None:
            params["children"] = children
        if ranks is not None:
            params["ranks"] = ranks
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsTaxonomyTaxonRelatedIdsTool")
class NCBIDatasetsTaxonomyTaxonRelatedIdsTool(BaseTool):
    """
    Use taxonomic identifier to get related taxonomic identifiers, such as children
    
    Auto-generated by discover_and_generate.py
    Endpoint: /taxonomy/taxon/{tax_id}/related_ids
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        tax_id = arguments.get("tax_id")
        include_lineage = arguments.get("include_lineage")
        include_subtree = arguments.get("include_subtree")
        ranks = arguments.get("ranks")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        
        try:
            result = self._fetch_data(tax_id, include_lineage, include_subtree, ranks, page_size, page_token)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["tax_id"] = tax_id
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        tax_id: str,
        include_lineage: Optional[str] = None,
        include_subtree: Optional[str] = None,
        ranks: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if tax_id is None:
            raise ValueError("`tax_id` is required")
        # Build URL
        url = self.base_url + "/taxonomy/taxon/{tax_id}/related_ids".format(tax_id=tax_id)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if include_lineage is not None:
            params["include_lineage"] = include_lineage
        if include_subtree is not None:
            params["include_subtree"] = include_subtree
        if ranks is not None:
            params["ranks"] = ranks
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()




# ============================================================================
# AUTO-GENERATED TOOLS - Generated by discover_and_generate.py
# ============================================================================

@register_tool("NCBIDatasetsGeneTaxonTool")
class NCBIDatasetsGeneTaxonTool(BaseTool):
    """
    Get gene reports by taxonomic identifier
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/taxon/{taxon}
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        returned_content = arguments.get("returned_content")
        taxon = arguments.get("taxon")
        locus_tags = arguments.get("locus_tags")
        table_fields = arguments.get("table_fields")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        accession_filter = arguments.get("accession_filter")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(taxon, returned_content, locus_tags, table_fields, include_tabular_header, page_size, page_token, query, types, accession_filter, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon: str,
        returned_content: Optional[str] = None,
        locus_tags: Optional[str] = None,
        table_fields: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        accession_filter: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if taxon is None:
            raise ValueError("`taxon` is required")
        # Build URL
        url = self.base_url + "/gene/taxon/{taxon}".format(taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if returned_content is not None:
            params["returned_content"] = returned_content
        if locus_tags is not None:
            params["locus_tags"] = locus_tags
        if table_fields is not None:
            params["table_fields"] = table_fields
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if accession_filter is not None:
            params["accession_filter"] = accession_filter
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneIdProductReportTool")
class NCBIDatasetsGeneIdProductReportTool(BaseTool):
    """
    Get gene product reports by gene IDs.
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/id/{gene_ids}/product_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        gene_ids = arguments.get("gene_ids")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        accession_filter = arguments.get("accession_filter")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(gene_ids, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, accession_filter, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["gene_ids"] = gene_ids
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        gene_ids: str,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        accession_filter: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if gene_ids is None:
            raise ValueError("`gene_ids` is required")
        if isinstance(gene_ids, (str, int)):
            gene_ids = [str(gene_ids)]
        else:
            gene_ids = [str(x) for x in gene_ids]
        gene_ids = ",".join(gene_ids)
        
        # Build URL
        url = self.base_url + "/gene/id/{gene_ids}/product_report".format(gene_ids=gene_ids)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if accession_filter is not None:
            params["accession_filter"] = accession_filter
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneAccessionProductReportTool")
class NCBIDatasetsGeneAccessionProductReportTool(BaseTool):
    """
    Get gene product reports by accession IDs
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/accession/{accessions}/product_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accessions = arguments.get("accessions")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        accession_filter = arguments.get("accession_filter")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(accessions, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, accession_filter, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        accession_filter: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/gene/accession/{accessions}/product_report".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if accession_filter is not None:
            params["accession_filter"] = accession_filter
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneTaxonProductReportTool")
class NCBIDatasetsGeneTaxonProductReportTool(BaseTool):
    """
    Get gene product reports by taxonomic identifier
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/taxon/{taxon}/product_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxon = arguments.get("taxon")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        accession_filter = arguments.get("accession_filter")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(taxon, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, accession_filter, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon: str,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        accession_filter: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if taxon is None:
            raise ValueError("`taxon` is required")
        # Build URL
        url = self.base_url + "/gene/taxon/{taxon}/product_report".format(taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if accession_filter is not None:
            params["accession_filter"] = accession_filter
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneLocusTagProductReportTool")
class NCBIDatasetsGeneLocusTagProductReportTool(BaseTool):
    """
    Get gene product reports by locus tags
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/locus_tag/{locus_tags}/product_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        locus_tags = arguments.get("locus_tags")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        accession_filter = arguments.get("accession_filter")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(locus_tags, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, accession_filter, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["locus_tags"] = locus_tags
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        locus_tags: str,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        accession_filter: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if locus_tags is None:
            raise ValueError("`locus_tags` is required")
        if isinstance(locus_tags, (str, int)):
            locus_tags = [str(locus_tags)]
        else:
            locus_tags = [str(x) for x in locus_tags]
        locus_tags = ",".join(locus_tags)
        
        # Build URL
        url = self.base_url + "/gene/locus_tag/{locus_tags}/product_report".format(locus_tags=locus_tags)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if accession_filter is not None:
            params["accession_filter"] = accession_filter
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneTaxonAnnotationChromosomeSummaryTool")
class NCBIDatasetsGeneTaxonAnnotationChromosomeSummaryTool(BaseTool):
    """
    Get summary of chromosomes for a particular taxon's annotation
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/taxon/{taxon}/annotation/{annotation_name}/chromosome_summary
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxon = arguments.get("taxon")
        annotation_name = arguments.get("annotation_name")
        
        try:
            result = self._fetch_data(taxon, annotation_name)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon"] = taxon
            response["annotation_name"] = annotation_name
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon: str,
        annotation_name: str
    ):
        """Fetch data from NCBI Datasets API."""
        if taxon is None:
            raise ValueError("`taxon` is required")
        if annotation_name is None:
            raise ValueError("`annotation_name` is required")
        # Convert flexible path parameters to comma-separated strings

        # Build URL
        url = self.base_url + "/gene/taxon/{taxon}/annotation/{annotation_name}/chromosome_summary".format(taxon=taxon, annotation_name=annotation_name)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeAccessionAnnotationReportTool")
class NCBIDatasetsGenomeAccessionAnnotationReportTool(BaseTool):
    """
    Get genome annotation reports by genome assembly accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/accession/{accession}/annotation_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accession = arguments.get("accession")
        annotation_ids = arguments.get("annotation_ids")
        symbols = arguments.get("symbols")
        locations = arguments.get("locations")
        gene_types = arguments.get("gene_types")
        search_text = arguments.get("search_text")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        page_size = arguments.get("page_size")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_token = arguments.get("page_token")
        
        try:
            result = self._fetch_data(accession, annotation_ids, symbols, locations, gene_types, search_text, sort_field, sort_direction, page_size, table_format, include_tabular_header, page_token)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accession"] = accession
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accession: str,
        annotation_ids: Optional[str] = None,
        symbols: Optional[str] = None,
        locations: Optional[str] = None,
        gene_types: Optional[str] = None,
        search_text: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        page_size: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_token: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if accession is None:
            raise ValueError("`accession` is required")
        # Build URL
        url = self.base_url + "/genome/accession/{accession}/annotation_report".format(accession=accession)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if annotation_ids is not None:
            params["annotation_ids"] = annotation_ids
        if symbols is not None:
            params["symbols"] = symbols
        if locations is not None:
            params["locations"] = locations
        if gene_types is not None:
            params["gene_types"] = gene_types
        if search_text is not None:
            params["search_text"] = search_text
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        if page_size is not None:
            params["page_size"] = page_size
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_token is not None:
            params["page_token"] = page_token
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsOrganelleAccessionsDatasetReportTool")
class NCBIDatasetsOrganelleAccessionsDatasetReportTool(BaseTool):
    """
    Get Organelle dataset report by accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /organelle/accessions/{accessions}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxons = arguments.get("taxons")
        accessions = arguments.get("accessions")
        organelle_types = arguments.get("organelle_types")
        first_release_date = arguments.get("first_release_date")
        last_release_date = arguments.get("last_release_date")
        tax_exact_match = arguments.get("tax_exact_match")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        returned_content = arguments.get("returned_content")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        
        try:
            result = self._fetch_data(accessions, taxons, organelle_types, first_release_date, last_release_date, tax_exact_match, sort_field, sort_direction, returned_content, table_format, include_tabular_header)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str,
        taxons: Optional[str] = None,
        organelle_types: Optional[str] = None,
        first_release_date: Optional[str] = None,
        last_release_date: Optional[str] = None,
        tax_exact_match: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        returned_content: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/organelle/accessions/{accessions}/dataset_report".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if taxons is not None:
            params["taxons"] = taxons
        if organelle_types is not None:
            params["organelle_types"] = organelle_types
        if first_release_date is not None:
            params["first_release_date"] = first_release_date
        if last_release_date is not None:
            params["last_release_date"] = last_release_date
        if tax_exact_match is not None:
            params["tax_exact_match"] = tax_exact_match
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        if returned_content is not None:
            params["returned_content"] = returned_content
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsOrganelleTaxonDatasetReportTool")
class NCBIDatasetsOrganelleTaxonDatasetReportTool(BaseTool):
    """
    Get Organelle dataset report by taxons
    
    Auto-generated by discover_and_generate.py
    Endpoint: /organelle/taxon/{taxons}/dataset_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxons = arguments.get("taxons")
        organelle_types = arguments.get("organelle_types")
        first_release_date = arguments.get("first_release_date")
        last_release_date = arguments.get("last_release_date")
        tax_exact_match = arguments.get("tax_exact_match")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        returned_content = arguments.get("returned_content")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        
        try:
            result = self._fetch_data(taxons, organelle_types, first_release_date, last_release_date, tax_exact_match, sort_field, sort_direction, returned_content, page_size, page_token, table_format, include_tabular_header)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxons"] = taxons
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxons: str,
        organelle_types: Optional[str] = None,
        first_release_date: Optional[str] = None,
        last_release_date: Optional[str] = None,
        tax_exact_match: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        returned_content: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if taxons is None:
            raise ValueError("`taxons` is required")
        if isinstance(taxons, (str, int)):
            taxons = [str(taxons)]
        else:
            taxons = [str(x) for x in taxons]
        taxons = ",".join(taxons)
        
        # Build URL
        url = self.base_url + "/organelle/taxon/{taxons}/dataset_report".format(taxons=taxons)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if organelle_types is not None:
            params["organelle_types"] = organelle_types
        if first_release_date is not None:
            params["first_release_date"] = first_release_date
        if last_release_date is not None:
            params["last_release_date"] = last_release_date
        if tax_exact_match is not None:
            params["tax_exact_match"] = tax_exact_match
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        if returned_content is not None:
            params["returned_content"] = returned_content
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsVirusTaxonAnnotationReportTool")
class NCBIDatasetsVirusTaxonAnnotationReportTool(BaseTool):
    """
    Get virus annotation report by taxon
    
    Auto-generated by discover_and_generate.py
    Endpoint: /virus/taxon/{taxon}/annotation_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        taxon = arguments.get("taxon")
        filter_refseq_only = arguments.get("filter.refseq_only")
        filter_annotated_only = arguments.get("filter.annotated_only")
        filter_released_since = arguments.get("filter.released_since")
        filter_updated_since = arguments.get("filter.updated_since")
        filter_host = arguments.get("filter.host")
        filter_pangolin_classification = arguments.get("filter.pangolin_classification")
        filter_geo_location = arguments.get("filter.geo_location")
        filter_usa_state = arguments.get("filter.usa_state")
        filter_complete_only = arguments.get("filter.complete_only")
        table_fields = arguments.get("table_fields")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        
        try:
            result = self._fetch_data(taxon, filter_refseq_only, filter_annotated_only, filter_released_since, filter_updated_since, filter_host, filter_pangolin_classification, filter_geo_location, filter_usa_state, filter_complete_only, table_fields, page_size, page_token)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        taxon: str,
        filter_refseq_only: Optional[str] = None,
        filter_annotated_only: Optional[str] = None,
        filter_released_since: Optional[str] = None,
        filter_updated_since: Optional[str] = None,
        filter_host: Optional[str] = None,
        filter_pangolin_classification: Optional[str] = None,
        filter_geo_location: Optional[str] = None,
        filter_usa_state: Optional[str] = None,
        filter_complete_only: Optional[str] = None,
        table_fields: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if taxon is None:
            raise ValueError("`taxon` is required")
        # Build URL
        url = self.base_url + "/virus/taxon/{taxon}/annotation_report".format(taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if filter_refseq_only is not None:
            params["filter.refseq_only"] = filter_refseq_only
        if filter_annotated_only is not None:
            params["filter.annotated_only"] = filter_annotated_only
        if filter_released_since is not None:
            params["filter.released_since"] = filter_released_since
        if filter_updated_since is not None:
            params["filter.updated_since"] = filter_updated_since
        if filter_host is not None:
            params["filter.host"] = filter_host
        if filter_pangolin_classification is not None:
            params["filter.pangolin_classification"] = filter_pangolin_classification
        if filter_geo_location is not None:
            params["filter.geo_location"] = filter_geo_location
        if filter_usa_state is not None:
            params["filter.usa_state"] = filter_usa_state
        if filter_complete_only is not None:
            params["filter.complete_only"] = filter_complete_only
        if table_fields is not None:
            params["table_fields"] = table_fields
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsVirusAccessionAnnotationReportTool")
class NCBIDatasetsVirusAccessionAnnotationReportTool(BaseTool):
    """
    Get virus annotation report by accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /virus/accession/{accessions}/annotation_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accessions = arguments.get("accessions")
        filter_refseq_only = arguments.get("filter.refseq_only")
        filter_annotated_only = arguments.get("filter.annotated_only")
        filter_released_since = arguments.get("filter.released_since")
        filter_updated_since = arguments.get("filter.updated_since")
        filter_host = arguments.get("filter.host")
        filter_pangolin_classification = arguments.get("filter.pangolin_classification")
        filter_geo_location = arguments.get("filter.geo_location")
        filter_usa_state = arguments.get("filter.usa_state")
        filter_complete_only = arguments.get("filter.complete_only")
        table_fields = arguments.get("table_fields")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        
        try:
            result = self._fetch_data(accessions, filter_refseq_only, filter_annotated_only, filter_released_since, filter_updated_since, filter_host, filter_pangolin_classification, filter_geo_location, filter_usa_state, filter_complete_only, table_fields, page_size, page_token)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str,
        filter_refseq_only: Optional[str] = None,
        filter_annotated_only: Optional[str] = None,
        filter_released_since: Optional[str] = None,
        filter_updated_since: Optional[str] = None,
        filter_host: Optional[str] = None,
        filter_pangolin_classification: Optional[str] = None,
        filter_geo_location: Optional[str] = None,
        filter_usa_state: Optional[str] = None,
        filter_complete_only: Optional[str] = None,
        table_fields: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/virus/accession/{accessions}/annotation_report".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if filter_refseq_only is not None:
            params["filter.refseq_only"] = filter_refseq_only
        if filter_annotated_only is not None:
            params["filter.annotated_only"] = filter_annotated_only
        if filter_released_since is not None:
            params["filter.released_since"] = filter_released_since
        if filter_updated_since is not None:
            params["filter.updated_since"] = filter_updated_since
        if filter_host is not None:
            params["filter.host"] = filter_host
        if filter_pangolin_classification is not None:
            params["filter.pangolin_classification"] = filter_pangolin_classification
        if filter_geo_location is not None:
            params["filter.geo_location"] = filter_geo_location
        if filter_usa_state is not None:
            params["filter.usa_state"] = filter_usa_state
        if filter_complete_only is not None:
            params["filter.complete_only"] = filter_complete_only
        if table_fields is not None:
            params["table_fields"] = table_fields
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()



@register_tool("NCBIDatasetsGeneSymbolTaxonProductReportTool")
class NCBIDatasetsGeneSymbolTaxonProductReportTool(BaseTool):
    """
    Get product reports by taxon.
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/symbol/{symbols}/taxon/{taxon}/product_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        symbols = arguments.get("symbols")
        taxon = arguments.get("taxon")
        table_fields = arguments.get("table_fields")
        table_format = arguments.get("table_format")
        include_tabular_header = arguments.get("include_tabular_header")
        page_size = arguments.get("page_size")
        page_token = arguments.get("page_token")
        query = arguments.get("query")
        types = arguments.get("types")
        accession_filter = arguments.get("accession_filter")
        tax_search_subtree = arguments.get("tax_search_subtree")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        
        try:
            result = self._fetch_data(symbols, taxon, table_fields, table_format, include_tabular_header, page_size, page_token, query, types, accession_filter, tax_search_subtree, sort_field, sort_direction)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["symbols"] = symbols
            response["taxon"] = taxon
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        symbols: str,
        taxon: str,
        table_fields: Optional[str] = None,
        table_format: Optional[str] = None,
        include_tabular_header: Optional[str] = None,
        page_size: Optional[str] = None,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        types: Optional[str] = None,
        accession_filter: Optional[str] = None,
        tax_search_subtree: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if symbols is None:
            raise ValueError("`symbols` is required")
        if isinstance(symbols, (str, int)):
            symbols = [str(symbols)]
        else:
            symbols = [str(x) for x in symbols]
        symbols = ",".join(symbols)
        
        # Build URL
        url = self.base_url + "/gene/symbol/{symbols}/taxon/{taxon}/product_report".format(symbols=symbols, taxon=taxon)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_format is not None:
            params["table_format"] = table_format
        if include_tabular_header is not None:
            params["include_tabular_header"] = include_tabular_header
        if page_size is not None:
            params["page_size"] = page_size
        if page_token is not None:
            params["page_token"] = page_token
        if query is not None:
            params["query"] = query
        if types is not None:
            params["types"] = types
        if accession_filter is not None:
            params["accession_filter"] = accession_filter
        if tax_search_subtree is not None:
            params["tax_search_subtree"] = tax_search_subtree
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsBiosampleAccessionBiosampleReportTool")
class NCBIDatasetsBiosampleAccessionBiosampleReportTool(BaseTool):
    """
    Get BioSample dataset reports by accession(s)
    
    Auto-generated by discover_and_generate.py
    Endpoint: /biosample/accession/{accessions}/biosample_report
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accessions = arguments.get("accessions")
        
        try:
            result = self._fetch_data(accessions)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/biosample/accession/{accessions}/biosample_report".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsVersionTool")
class NCBIDatasetsVersionTool(BaseTool):
    """
    Retrieve service version
    
    Auto-generated by discover_and_generate.py
    Endpoint: /version
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""

        
        try:
            result = self._fetch_data()
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        # Build URL
        url = self.base_url + "/version"
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeAccessionDownloadSummaryTool")
class NCBIDatasetsGenomeAccessionDownloadSummaryTool(BaseTool):
    """
    Preview genome dataset download
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/accession/{accessions}/download_summary
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accessions = arguments.get("accessions")
        chromosomes = arguments.get("chromosomes")
        include_annotation_type = arguments.get("include_annotation_type")
        
        try:
            result = self._fetch_data(accessions, chromosomes, include_annotation_type)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accessions"] = accessions
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accessions: str,
        chromosomes: Optional[str] = None,
        include_annotation_type: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if accessions is None:
            raise ValueError("`accessions` is required")
        if isinstance(accessions, (str, int)):
            accessions = [str(accessions)]
        else:
            accessions = [str(x) for x in accessions]
        accessions = ",".join(accessions)
        
        # Build URL
        url = self.base_url + "/genome/accession/{accessions}/download_summary".format(accessions=accessions)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if chromosomes is not None:
            params["chromosomes"] = chromosomes
        if include_annotation_type is not None:
            params["include_annotation_type"] = include_annotation_type
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGeneIdDownloadSummaryTool")
class NCBIDatasetsGeneIdDownloadSummaryTool(BaseTool):
    """
    Get gene download summary by GeneID
    
    Auto-generated by discover_and_generate.py
    Endpoint: /gene/id/{gene_ids}/download_summary
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        gene_ids = arguments.get("gene_ids")
        include_annotation_type = arguments.get("include_annotation_type")
        returned_content = arguments.get("returned_content")
        fasta_filter = arguments.get("fasta_filter")
        accession_filter = arguments.get("accession_filter")
        aux_report = arguments.get("aux_report")
        tabular_reports = arguments.get("tabular_reports")
        table_fields = arguments.get("table_fields")
        table_report_type = arguments.get("table_report_type")
        
        try:
            result = self._fetch_data(gene_ids, include_annotation_type, returned_content, fasta_filter, accession_filter, aux_report, tabular_reports, table_fields, table_report_type)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["gene_ids"] = gene_ids
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        gene_ids: str,
        include_annotation_type: Optional[str] = None,
        returned_content: Optional[str] = None,
        fasta_filter: Optional[str] = None,
        accession_filter: Optional[str] = None,
        aux_report: Optional[str] = None,
        tabular_reports: Optional[str] = None,
        table_fields: Optional[str] = None,
        table_report_type: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        if gene_ids is None:
            raise ValueError("`gene_ids` is required")
        if isinstance(gene_ids, (str, int)):
            gene_ids = [str(gene_ids)]
        else:
            gene_ids = [str(x) for x in gene_ids]
        gene_ids = ",".join(gene_ids)
        
        # Build URL
        url = self.base_url + "/gene/id/{gene_ids}/download_summary".format(gene_ids=gene_ids)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if include_annotation_type is not None:
            params["include_annotation_type"] = include_annotation_type
        if returned_content is not None:
            params["returned_content"] = returned_content
        if fasta_filter is not None:
            params["fasta_filter"] = fasta_filter
        if accession_filter is not None:
            params["accession_filter"] = accession_filter
        if aux_report is not None:
            params["aux_report"] = aux_report
        if tabular_reports is not None:
            params["tabular_reports"] = tabular_reports
        if table_fields is not None:
            params["table_fields"] = table_fields
        if table_report_type is not None:
            params["table_report_type"] = table_report_type
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


@register_tool("NCBIDatasetsGenomeAccessionAnnotationReportDownloadSummaryTool")
class NCBIDatasetsGenomeAccessionAnnotationReportDownloadSummaryTool(BaseTool):
    """
    Get a download summary (preview) of a genome annotation data package by genome assembly accession
    
    Auto-generated by discover_and_generate.py
    Endpoint: /genome/accession/{accession}/annotation_report/download_summary
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
        accession = arguments.get("accession")
        annotation_ids = arguments.get("annotation_ids")
        symbols = arguments.get("symbols")
        locations = arguments.get("locations")
        gene_types = arguments.get("gene_types")
        search_text = arguments.get("search_text")
        sort_field = arguments.get("sort.field")
        sort_direction = arguments.get("sort.direction")
        include_annotation_type = arguments.get("include_annotation_type")
        
        try:
            result = self._fetch_data(accession, annotation_ids, symbols, locations, gene_types, search_text, sort_field, sort_direction, include_annotation_type)
            response = {"success": True, "data": result}
            # Add path parameters to response
            
            response["accession"] = accession
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_data(
        self,

        accession: str,
        annotation_ids: Optional[str] = None,
        symbols: Optional[str] = None,
        locations: Optional[str] = None,
        gene_types: Optional[str] = None,
        search_text: Optional[str] = None,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        include_annotation_type: Optional[str] = None
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings
        
        if accession is None:
            raise ValueError("`accession` is required")
        # Build URL
        url = self.base_url + "/genome/accession/{accession}/annotation_report/download_summary".format(accession=accession)
        
        # Build parameters
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        
        if annotation_ids is not None:
            params["annotation_ids"] = annotation_ids
        if symbols is not None:
            params["symbols"] = symbols
        if locations is not None:
            params["locations"] = locations
        if gene_types is not None:
            params["gene_types"] = gene_types
        if search_text is not None:
            params["search_text"] = search_text
        if sort_field is not None:
            params["sort.field"] = sort_field
        if sort_direction is not None:
            params["sort.direction"] = sort_direction
        if include_annotation_type is not None:
            params["include_annotation_type"] = include_annotation_type
        
        # Make request
        headers = {"Accept": NCBI_DATASETS_ACCEPT_JSON}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


