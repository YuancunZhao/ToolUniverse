"""
ClinGen Database REST API Tool

This tool provides access to ClinGen (Clinical Genome Resource) data including:
- Gene-Disease Validity curations
- Dosage Sensitivity curations
- Clinical Actionability curations
- Variant Pathogenicity data

ClinGen is a NIH-funded resource providing authoritative information on
gene-disease relationships for use in clinical genomics.
"""

import requests
import csv
import io
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URLs for ClinGen APIs
CLINGEN_BASE_URL = "https://search.clinicalgenome.org"
ACTIONABILITY_ADULT_URL = "https://actionability.clinicalgenome.org/ac/Adult/api"
ACTIONABILITY_PEDIATRIC_URL = (
    "https://actionability.clinicalgenome.org/ac/Pediatric/api"
)
EREPO_BASE_URL = "https://erepo.clinicalgenome.org/evrepo/api"
CSPEC_API_BASE_URL = "https://cspec.genome.network/cspec/api"


@register_tool("ClinGenTool")
class ClinGenTool(BaseTool):
    """
    ClinGen Database REST API tool.

    Provides access to ClinGen curated data including gene-disease validity,
    dosage sensitivity, and clinical actionability.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "")
        self.timeout = fields.get("timeout", 60)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to operation handler based on config."""
        operation = self.operation or arguments.get("operation")

        if not operation:
            return {"status": "error", "error": "Missing: operation"}

        operation_map = {
            "get_gene_validity": self._get_gene_validity,
            "search_gene_validity": self._search_gene_validity,
            "get_dosage_sensitivity": self._get_dosage_sensitivity,
            "search_dosage_sensitivity": self._search_dosage_sensitivity,
            "get_actionability_adult": self._get_actionability_adult,
            "get_actionability_pediatric": self._get_actionability_pediatric,
            "search_actionability": self._search_actionability,
            "get_variant_classifications": self._get_variant_classifications,
            "search_cspec": self._search_cspec,
        }

        handler = operation_map.get(operation)
        if not handler:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return handler(arguments)

    @staticmethod
    def _released_cspec(record: Dict[str, Any]) -> bool:
        return str(record.get("status") or "").strip().casefold() == "released"

    @staticmethod
    def _cspec_gene_entries(record: Dict[str, Any]) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for rule_set in record.get("ruleSets") or []:
            if not isinstance(rule_set, dict):
                continue
            for gene in rule_set.get("genes") or []:
                if isinstance(gene, dict):
                    entries.append(gene)
        return entries

    @staticmethod
    def _cspec_organization(record: Dict[str, Any]) -> str:
        affiliation = record.get("affiliation")
        if isinstance(affiliation, dict) and affiliation.get("label"):
            return str(affiliation["label"])
        return ""

    @staticmethod
    def _cspec_criteria(detail: Any) -> List[Dict[str, Any]]:
        if not isinstance(detail, dict):
            return []
        normalized: List[Dict[str, Any]] = []
        for rule_set in detail.get("ruleSets") or []:
            if not isinstance(rule_set, dict):
                continue
            for item in rule_set.get("criteriaCodes") or []:
                if not isinstance(item, dict):
                    continue
                strengths = []
                for descriptor in item.get("evidenceStrengths") or []:
                    if not isinstance(descriptor, dict):
                        continue
                    strengths.append(
                        {
                            "strength": descriptor.get("label"),
                            "applicability": descriptor.get("applicability"),
                            "specification_type": descriptor.get("specificationType"),
                            "instructions": descriptor.get("instructionsToUse"),
                            "text": descriptor.get("description"),
                        }
                    )
                normalized.append(
                    {
                        "criterion": item.get("label"),
                        "applicability": item.get("applicability"),
                        "default_strength": item.get("defaultStrength"),
                        "instructions": item.get("description"),
                        "strengths": strengths,
                        "criterion_id": item.get("@id"),
                    }
                )
        return normalized

    @staticmethod
    def _cspec_version(content: Dict[str, Any]) -> str:
        version = str(content.get("version") or "").strip()
        if version:
            return version
        match = re.search(
            r"\bversion\s+([0-9]+(?:\.[0-9]+){1,2})\b",
            str(content.get("label") or content.get("title") or ""),
            re.IGNORECASE,
        )
        return match.group(1) if match else ""

    def _search_cspec(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Discover current released ClinGen CSpec documents for a gene."""
        gene = str(arguments.get("gene") or "").strip().upper()
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}
        index_url = f"{CSPEC_API_BASE_URL}/svis"
        try:
            response = requests.get(index_url, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            records = payload.get("data") if isinstance(payload, dict) else None
            matches: List[Dict[str, Any]] = []
            for record in records or []:
                if not isinstance(record, dict) or not self._released_cspec(record):
                    continue
                gene_entries = [
                    item
                    for item in self._cspec_gene_entries(record)
                    if str(item.get("label") or "").strip().upper() == gene
                ]
                if not gene_entries:
                    continue
                specification_id = (
                    str(record.get("@id") or "").rstrip("/").rsplit("/", 1)[-1]
                )
                if not specification_id:
                    continue
                detail_url = (
                    f"{CSPEC_API_BASE_URL}/SequenceVariantInterpretation/id/"
                    f"{specification_id}"
                )
                detail_response = requests.get(detail_url, timeout=self.timeout)
                detail_response.raise_for_status()
                detail = detail_response.json()
                detail = detail if isinstance(detail, dict) else {}
                diseases: List[Dict[str, Any]] = []
                for entry in gene_entries:
                    for disease in entry.get("diseases") or []:
                        if not isinstance(disease, dict):
                            continue
                        inheritance = [
                            str(item.get("@label") or "")
                            for item in disease.get("modeOfInheritance") or []
                            if isinstance(item, dict)
                        ]
                        mondo_id = str(disease.get("label") or "")
                        diseases.append(
                            {
                                "name": mondo_id,
                                "mondo_id": mondo_id,
                                "inheritance": inheritance,
                            }
                        )
                matches.append(
                    {
                        "specification_id": specification_id,
                        "gene": gene,
                        "vcep": self._cspec_organization(record),
                        "title": str(detail.get("label") or ""),
                        "version": self._cspec_version(record)
                        or self._cspec_version(detail),
                        "status": str(record.get("status") or "Released"),
                        "diseases": diseases,
                        "url": str(
                            record.get("url")
                            or (
                                "https://cspec.genome.network/cspec/ui/svi/doc/"
                                f"{specification_id}"
                            )
                        ),
                        "criterion_modifications": self._cspec_criteria(detail),
                        "specification": detail,
                    }
                )
            provider_version = ""
            if isinstance(payload, dict):
                metadata = payload.get("metadata")
                if isinstance(metadata, dict):
                    rendered = metadata.get("rendered")
                    if isinstance(rendered, dict):
                        provider_version = str(rendered.get("by") or "")
            return {
                "status": "success" if matches else "no_hit",
                "gene": gene,
                "data": matches,
                "total": len(matches),
                "provider": "ClinGen CSpec Registry",
                "provider_version": provider_version,
                "request_url": response.url,
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.RequestException as exc:
            return {"status": "error", "error": f"ClinGen CSpec request failed: {exc}"}

    def _get_gene_validity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all gene-disease validity curations from ClinGen."""
        try:
            url = f"{CLINGEN_BASE_URL}/kb/gene-validity/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Optional filtering by gene
            gene = arguments.get("gene")
            if gene:
                gene_upper = gene.upper()
                # Handle both "GENE SYMBOL" (from CSV) and "Gene Symbol" key formats
                curations = [
                    c
                    for c in curations
                    if c.get("GENE SYMBOL", c.get("Gene Symbol", "")).upper()
                    == gene_upper
                ]

            return {
                "status": "success",
                "data": curations[:100],  # Limit to first 100 for performance
                "total": len(curations),
                "source": "ClinGen Gene-Disease Validity",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_gene_validity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search gene-disease validity curations by gene symbol."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            url = f"{CLINGEN_BASE_URL}/kb/gene-validity/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Filter by gene symbol (case-insensitive, EXACT match -- this
            # column holds a single precise HGNC symbol, not free text, and
            # substring matching silently pulled in unrelated genes whose
            # symbol happens to contain the query, e.g. "OTC" -> "NOTCH1"/
            # "NOTCH2" (confirmed live). Mirrors _get_gene_validity's already-
            # correct exact-match filter above.
            gene_upper = gene.upper()
            matches = [
                c
                for c in curations
                if c.get("GENE SYMBOL", c.get("Gene Symbol", "")).upper() == gene_upper
            ]

            return {
                "status": "success",
                "data": matches,
                "total": len(matches),
                "gene_searched": gene,
                "source": "ClinGen Gene-Disease Validity",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_dosage_sensitivity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all dosage sensitivity curations from ClinGen."""
        include_regions = arguments.get("include_regions", False)

        try:
            if include_regions:
                url = f"{CLINGEN_BASE_URL}/kb/gene-dosage/downloadall"
            else:
                url = f"{CLINGEN_BASE_URL}/kb/gene-dosage/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Optional filtering by gene -- EXACT match (case-insensitive):
            # this column holds a single precise HGNC symbol, not free text,
            # and substring matching silently pulled in unrelated genes
            # whose symbol happens to contain the query, e.g. "OTC" ->
            # "NOTCH1"/"NOTCH2" (confirmed live).
            gene = arguments.get("gene")
            if gene:
                gene_upper = gene.upper()
                # Handle both "GENE SYMBOL" and "Gene Symbol" key formats
                curations = [
                    c
                    for c in curations
                    if c.get("GENE SYMBOL", c.get("Gene Symbol", "")).upper()
                    == gene_upper
                ]

            return {
                "status": "success",
                "data": curations[:100],  # Limit for performance
                "total": len(curations),
                "include_regions": include_regions,
                "source": "ClinGen Dosage Sensitivity",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_dosage_sensitivity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search dosage sensitivity curations by gene symbol."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            # Use the simpler download endpoint (genes only) for searching
            url = f"{CLINGEN_BASE_URL}/kb/gene-dosage/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Filter by gene symbol (case-insensitive, EXACT match -- this
            # column holds a single precise HGNC symbol, not free text, and
            # substring matching silently pulled in unrelated genes whose
            # symbol happens to contain the query, e.g. "OTC" -> "NOTCH1"/
            # "NOTCH2" (confirmed live).
            # Handle different column name formats from different endpoints
            gene_upper = gene.upper()
            matches = [
                c
                for c in curations
                if c.get(
                    "GENE SYMBOL", c.get("GENE/REGION", c.get("Gene Symbol", ""))
                ).upper()
                == gene_upper
            ]

            return {
                "status": "success",
                "data": matches,
                "total": len(matches),
                "gene_searched": gene,
                "source": "ClinGen Dosage Sensitivity",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_actionability_adult(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical actionability curations for adult context."""
        return self._get_actionability(arguments, "Adult")

    def _get_actionability_pediatric(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical actionability curations for pediatric context."""
        return self._get_actionability(arguments, "Pediatric")

    @staticmethod
    def _actionability_rows_to_dicts(data: Any) -> list:
        """The ?flavor=flat actionability API returns a columnar table --
        {"columns": [...], "rows": [[...], ...]} -- not a list of record
        dicts (confirmed live). Neither older code path recognized this
        shape (isinstance(data, list) is False and there's no "data" key),
        so the gene filter silently matched nothing and the raw un-parsed
        table was returned as-is. Zip columns with each row into dicts.
        """
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("columns"), list):
            columns = data["columns"]
            return [
                dict(zip(columns, row))
                for row in data.get("rows", [])
                if isinstance(row, list)
            ]
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        return []

    def _get_actionability(
        self, arguments: Dict[str, Any], context: str
    ) -> Dict[str, Any]:
        """Get clinical actionability curations for a specific context."""
        try:
            base_url = (
                ACTIONABILITY_ADULT_URL
                if context == "Adult"
                else ACTIONABILITY_PEDIATRIC_URL
            )

            # Use flat format for easier parsing
            url = f"{base_url}/summ?flavor=flat"

            headers = {"Accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            curations = self._actionability_rows_to_dicts(response.json())

            # Optional filtering by gene. geneOrVariant is a comma-joined
            # multi-gene field for panel curations (e.g. "BRCA1,BRCA2"), so
            # substring match rather than exact-match the whole field.
            gene = arguments.get("gene")
            if gene:
                gene_upper = gene.upper()
                curations = [
                    c
                    for c in curations
                    if gene_upper in str(c.get("geneOrVariant", "")).upper()
                    or gene_upper in str(c.get("gene", "")).upper()
                    or gene_upper in str(c.get("Gene", "")).upper()
                    or gene_upper in str(c.get("hgncId", "")).upper()
                ]

            return {
                "status": "success",
                "data": curations[:100],
                "total": len(curations),
                "context": context,
                "source": f"ClinGen Clinical Actionability ({context})",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _fetch_actionability_context(
        self, base_url: str, gene: str
    ) -> List[Dict[str, Any]]:
        """Fetch and gene-filter one actionability context (Adult/Pediatric).
        Raises on failure -- the caller decides how to handle a failed context."""
        url = f"{base_url}/summ?flavor=flat"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        curations = self._actionability_rows_to_dicts(response.json())

        # Filter by gene. geneOrVariant is a comma-joined multi-gene field
        # for panel curations, so substring match rather than exact-match
        # the whole field.
        gene_upper = gene.upper()
        return [
            c
            for c in curations
            if gene_upper in str(c.get("geneOrVariant", "")).upper()
            or gene_upper in str(c.get("gene", "")).upper()
            or gene_upper in str(c.get("Gene", "")).upper()
            or gene_upper in str(c.get("hgncId", "")).upper()
        ]

    def _search_actionability(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search clinical actionability across both adult and pediatric contexts."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            # Fix-R53A-1: the Adult and Pediatric actionability endpoints are
            # each independently slow (confirmed live: the Adult endpoint
            # alone took ~124s for a 138KB response -- expensive server-side
            # computation, not a network issue) but are fetched one after
            # the other despite being fully independent requests, so a
            # caller paid the sum of both (up to ~4 minutes, and close to
            # this tool's own 120s per-request timeout budget even for a
            # single context). Fetching them concurrently bounds the wait
            # to the slower of the two instead of the sum of both.
            contexts = [
                ("Adult", ACTIONABILITY_ADULT_URL),
                ("Pediatric", ACTIONABILITY_PEDIATRIC_URL),
            ]
            results = {"Adult": [], "Pediatric": []}
            with ThreadPoolExecutor(max_workers=len(contexts)) as executor:
                futures = {
                    executor.submit(
                        self._fetch_actionability_context, base_url, gene
                    ): context
                    for context, base_url in contexts
                }
                for future in futures:
                    context = futures[future]
                    try:
                        results[context] = future.result()
                    except Exception:
                        # Continue with other context if one fails
                        pass

            return {
                "status": "success",
                "data": results,
                "gene_searched": gene,
                "adult_count": len(results["Adult"]),
                "pediatric_count": len(results["Pediatric"]),
                "source": "ClinGen Clinical Actionability",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _flatten_classification(item: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve the complete released VCEP assertion in a stable envelope."""
        hgvs = item.get("hgvs") or []
        gene = item.get("gene") or {}
        condition = item.get("condition") or {}
        guidelines = item.get("guidelines") or []
        first_guideline = guidelines[0] if guidelines else {}
        agents = first_guideline.get("agents") or []
        first_agent = agents[0] if agents else {}
        evidence_summaries = [
            value
            for guideline in guidelines
            if isinstance(guideline, dict)
            for key in ("evidenceSummary", "evidence_summary", "description")
            for value in [guideline.get(key)]
            if value not in (None, "", [], {})
        ]
        criteria: List[Dict[str, Any]] = []
        criterion_pattern = re.compile(
            r"^(PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7])"
            r"(?:[_\s-]*(Very\s*Strong|Strong|Moderate|Supporting))?$",
            re.IGNORECASE,
        )
        for guideline in guidelines:
            if not isinstance(guideline, dict):
                continue
            for key in (
                "criteria",
                "appliedCriteria",
                "evidenceCriteria",
                "classificationContributions",
            ):
                values = guideline.get(key)
                values = values if isinstance(values, list) else [values]
                criteria.extend(value for value in values if isinstance(value, dict))

            # Current ERepo records expose the actual applied criteria under
            # guideline.agents[].evidenceCodes rather than the older
            # guideline-level keys. Preserve both met and negative rows here;
            # the ACMG VCEP parser is responsible for excluding Not Met / N/A.
            for agent in guideline.get("agents") or []:
                if not isinstance(agent, dict):
                    continue
                for code in agent.get("evidenceCodes") or []:
                    if not isinstance(code, dict):
                        continue
                    label = str(code.get("label") or code.get("code") or "").strip()
                    match = criterion_pattern.fullmatch(label)
                    if not match:
                        continue
                    criteria.append(
                        {
                            "criterion": match.group(1).upper(),
                            "strength": "".join((match.group(2) or "").split()),
                            "status": code.get("status"),
                            "evidenceSummary": code.get("evidenceSummary")
                            or code.get("description"),
                            "pmids": code.get("pmids")
                            or code.get("publications")
                            or [],
                            "source_id": code.get("@id"),
                            "source_label": label,
                        }
                    )
        return {
            # The last hgvs entry is the gene-and-protein-notation form,
            # e.g. "NM_000277.2(PAH):c.1A>G (p.Met1Val)" -- matches the old
            # TSV "Variation" column's format.
            "Variation": hgvs[-1] if hgvs else None,
            "ClinVar Variation Id": item.get("variationId"),
            "HGNC Gene Symbol": gene.get("label"),
            "Disease": condition.get("label"),
            "Mondo Id": condition.get("@id"),
            "Assertion": (first_guideline.get("outcome") or {}).get("label"),
            "Expert Panel": first_agent.get("affiliation"),
            "CAID": item.get("caid"),
            "HGVS": list(hgvs),
            "MOI": condition.get("modeOfInheritance") or item.get("modeOfInheritance"),
            "Version": item.get("version") or first_guideline.get("version"),
            "Release Date": item.get("releaseDate")
            or item.get("date")
            or first_guideline.get("date"),
            "Status": item.get("status") or first_guideline.get("status") or "released",
            "Evidence Summaries": evidence_summaries,
            "Applied Criteria": criteria,
            "Guidelines": [
                dict(value) for value in guidelines if isinstance(value, dict)
            ],
            "Source Record": dict(item),
        }

    def _get_variant_classifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get variant pathogenicity classifications from ClinGen Evidence Repository.

        classifications/all fetches the *entire* ~22MB, ~10k-row repository
        with no server-side filter and filters client-side -- confirmed live
        this routinely took 2-5+ minutes (and sometimes hung past a 300s
        client timeout) even for a gene with zero curated variants. The
        classifications endpoint (no /all) supports server-side gene=/
        variant= filtering and returns in ~1s -- confirmed live for both a
        curated gene (PAH) and an uncurated one (empty result, still ~1s).
        Calling it with neither gene nor variant set is just as unbounded as
        classifications/all (confirmed live: also hangs past 30s with no
        params), so require at least one.
        """
        gene = arguments.get("gene")
        variant = arguments.get("variant")
        if not gene and not variant:
            return {
                "status": "error",
                "error": (
                    "gene or variant parameter is required. The ClinGen "
                    "Evidence Repository's classifications endpoint has no "
                    "working unfiltered listing (an unfiltered request is "
                    "just as unbounded as the bulk classifications/all "
                    "download) -- query by gene and/or variant instead."
                ),
            }
        try:
            params = {}
            if gene:
                params["gene"] = gene
            if variant:
                params["variant"] = variant

            response = requests.get(
                f"{EREPO_BASE_URL}/classifications", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("variantInterpretations", [])

            # The upstream `variant=` param resolves to that variant's gene
            # and returns every variant for the gene, not just the one
            # requested (confirmed live: variant=CA114360 returns 25 PAH
            # rows, not 1) -- narrow back down to an exact match on the
            # variant's own identifiers/HGVS forms.
            if variant:
                variant_str = str(variant).upper()
                items = [
                    item
                    for item in items
                    if variant_str in str(item.get("caid", "")).upper()
                    or variant_str == str(item.get("variationId", "")).upper()
                    or any(variant_str in h.upper() for h in item.get("hgvs") or [])
                ]

            data = [self._flatten_classification(item) for item in items]

            result = {
                "status": "success",
                "data": data[:100],
                "total": len(data),
                "source": "ClinGen Evidence Repository",
            }
            if not data:
                queried = f"gene '{gene}'" if gene else f"variant '{variant}'"
                result["note"] = (
                    f"No variant classifications found for {queried}. "
                    "The ClinGen Evidence Repository only contains variants "
                    "curated by Variant Curation Expert Panels (VCEPs). "
                    "Not all genes have active VCEPs. Try ClinGen_get_gene_validity "
                    "for gene-disease validity or clinvar_search_variants for "
                    "ClinVar variant classifications."
                )
            return result
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _parse_csv(self, csv_text: str) -> List[Dict[str, Any]]:
        """Parse CSV text into list of dictionaries.

        Handles ClinGen's special CSV format which has metadata headers
        before the actual data rows.
        """
        result = []
        try:
            lines = csv_text.strip().split("\n")

            # Find the header row (contains "GENE SYMBOL" or similar)
            header_idx = None
            for i, line in enumerate(lines):
                if "GENE SYMBOL" in line.upper():
                    header_idx = i
                    break

            if header_idx is None:
                # Fallback - try standard CSV parsing
                reader = csv.DictReader(io.StringIO(csv_text))
                for row in reader:
                    cleaned = {k: v for k, v in row.items() if v and k}
                    if cleaned:
                        result.append(cleaned)
                return result

            # Find where actual data starts (skip separator row after header)
            data_start = header_idx + 1
            if data_start < len(lines) and "+++++" in lines[data_start]:
                data_start += 1

            # Build new CSV content: header + data rows
            header_line = lines[header_idx]
            data_lines = [line for line in lines[data_start:] if "+++++" not in line]
            csv_content = header_line + "\n" + "\n".join(data_lines)

            # Use StringIO to read CSV from string
            reader = csv.DictReader(io.StringIO(csv_content))
            for row in reader:
                # Clean up the row - remove empty values
                cleaned = {}
                for k, v in row.items():
                    if v and k:
                        # Strip whitespace
                        k = k.strip()
                        v = v.strip()
                        if v:
                            cleaned[k] = v
                if cleaned and len(cleaned) > 2:  # Must have meaningful data
                    result.append(cleaned)
        except Exception:
            # Log but don't fail
            pass
        return result
