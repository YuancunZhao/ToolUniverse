"""
ClinVar REST API Tool

This tool provides access to the ClinVar database for clinical variant information,
disease associations, and clinical significance data.
"""

import json
import re
import requests
import time
from typing import Dict, Any, List, Optional, Tuple
from .base_tool import BaseTool
from .clinvar_submitted_tool import ClinVarSubmittedRecordsTool
from .tool_registry import register_tool

# Human-readable clinical-significance classes whose NCBI clinsig [prop] token is
# NOT the naive underscore form. Confirmed live: "Uncertain significance" ->
# clinsig_vus[prop] (BRCA2: 4345), while clinsig_uncertain_significance[prop]
# returns 0 -- so filtering for VUS, the single LARGEST ClinVar category,
# silently returned an empty success. Keyed by the normalized (lowercased,
# spaces) class name.
_CLINSIG_PROP_ALIASES = {
    "uncertain significance": "vus",
}

# The clinical-significance classes ClinVar's Entrez index ACTUALLY accepts.
# Enumerated by live-probing every documented germline/oncogenicity class
# through the exact clause this module builds
# (`"clinsig <v>"[Filter] OR clinsig_<v>[prop]`, plus the alias above) against
# db=clinvar with no other term, 2026-08. Only these returned a non-zero,
# non-parenthesised (i.e. index-recognised) translation:
#   pathogenic 256608 | likely pathogenic 165559 | uncertain significance
#   2367938 | vus 2368057 | likely benign 1165994 | benign 281217 |
#   established risk allele 6 | likely risk allele 119 | uncertain risk allele
#   180 | drug response 2612 | not provided 7616 | other 2209 |
#   risk factor 520
# Documented-but-unindexed spellings ("Affects", "association", "protective",
# "confers sensitivity", "Conflicting classifications of pathogenicity",
# "Oncogenic", "Likely oncogenic", "Pathogenic, low penetrance", ...) all came
# back 0 with Entrez wrapping the term in parentheses -- its signal for "this
# term is not in the index". Accepting them would paste an unmatchable token
# into the query and return a silent, filtered-to-nothing success, which is
# exactly the failure this list exists to prevent.
_CLINSIG_ACCEPTED = (
    "Pathogenic",
    "Likely pathogenic",
    "Uncertain significance",
    "VUS",
    "Likely benign",
    "Benign",
    "Established risk allele",
    "Likely risk allele",
    "Uncertain risk allele",
    "drug response",
    "risk factor",
    "not provided",
    "other",
)
_CLINSIG_ACCEPTED_NORMALIZED = {v.lower() for v in _CLINSIG_ACCEPTED}


def _normalize_clinsig(value: Any) -> list:
    """Split a clinical-significance value on '/' and normalize each component
    exactly the way the query builder does (lowercase, underscores/hyphens ->
    spaces), so validation can never accept a spelling the builder would then
    mangle. No accepted class contains a hyphen, and sibling variant tools emit
    hyphenated spellings (dbSNP reports "risk-factor"), so folding them keeps a
    chained call working instead of silently filtering to nothing."""
    return [
        re.sub(r"\s+", " ", re.sub(r"[_-]", " ", comp.strip().lower()))
        for comp in str(value).split("/")
        if comp.strip()
    ]


def _clinsig_query_clause(components: list) -> str:
    """Build the Entrez clause for already-normalized clinsig components.

    Single-word values are indexed under `"clinsig <v>"[Filter]`, compound ones
    under `clinsig_<v_with_underscores>[prop]`, and a few classes under a
    different NCBI token entirely (VUS); OR all applicable forms so a valid
    class is never a silent false-empty. Multiple components (from a '/'
    aggregate class) are OR'd into their union.
    """
    clauses = []
    for comp in components:
        forms = f'"clinsig {comp}"[Filter] OR clinsig_{comp.replace(" ", "_")}[prop]'
        alias = _CLINSIG_PROP_ALIASES.get(comp)
        if alias:
            forms += f" OR clinsig_{alias}[prop]"
        clauses.append(f"({forms})")
    if not clauses:
        return ""
    return "(" + " OR ".join(clauses) + ")" if len(clauses) > 1 else clauses[0]


def _invalid_clinsig_error(param_name: str, raw_value: Any, invalid: list) -> dict:
    """Reject an unrecognised clinical-significance value at the input, naming
    the offending PARAMETER.

    Previously such a value was pasted straight into the Entrez term, matched
    nothing, and the zero-result response then blamed the *gene* symbol -- so
    `{"gene": "TP53", "clinical_significance": "Banana"}` told the caller to
    go re-verify TP53, the one input that was never wrong.
    """
    return {
        "status": "error",
        "error": (
            f"Unrecognized {param_name} value(s): "
            + ", ".join(repr(i) for i in invalid)
            + f" (from {str(raw_value)!r}). No filter was applied and no search "
            "was run -- an unrecognized class matches nothing in ClinVar's "
            "index, which would look like 'this gene has no such variants'. "
            "ClinVar's clinical-significance index accepts only: "
            + ", ".join(_CLINSIG_ACCEPTED)
            + ". Case-insensitive; underscores are treated as spaces "
            "(e.g. 'likely_pathogenic'). Combine two classes with '/' to search "
            "their union (e.g. 'Pathogenic/Likely pathogenic')."
        ),
        "parameter": param_name,
        "invalid_values": invalid,
        "valid_values": list(_CLINSIG_ACCEPTED),
    }


# One term of an Entrez query translation together with the field tag Entrez
# actually applied to it: either a quoted phrase or a bare token, followed by
# "[<field>]". Entrez echoes its translation verbatim in `querytranslation`
# (confirmed live: 'RB1[gene] AND retinoblastoma[dis]' comes back unchanged),
# which is how a term's real search field can be read off a response that has
# already been fetched, with no extra request.
_TRANSLATED_TERM_RE = re.compile(r'("[^"]*"|[^\s()\[\]]+)\s*\[([^\]]+)\]')


def _normalize_translated_term(text: Any) -> str:
    """Fold a query term to a comparable form (unquoted, lowercase, single
    spaces) so a term this module emitted can be located in Entrez's echo of
    it regardless of quoting or case."""
    return re.sub(r"\s+", " ", str(text).replace('"', "").strip().lower())


def _field_tags_for_term(query_translation: str, term: str) -> list:
    """The field tag(s) Entrez actually attached to `term` in the translation
    it returned. Empty when the term is absent or carries no tag at all."""
    wanted = _normalize_translated_term(term)
    if not wanted or not query_translation:
        return []
    return [
        tag.strip()
        for raw, tag in _TRANSLATED_TERM_RE.findall(query_translation)
        if _normalize_translated_term(raw) == wanted
    ]


# ClinVar's [dis] index carries MedGen's concept names, not free clinical
# phrasing, and it has no fuzzy matching: confirmed live via raw E-utils that
# '"Leber congenital amaurosis"[dis]' returns 996 RPE65 records while the
# one-letter-different '"Lebers congenital amaurosis"[dis]' and the locus name
# 'RP20[dis]' each return 0. Any disclosure about a condition term points the
# caller at the index that decides the answer.
_CONDITION_INDEX_GUIDANCE = (
    "ClinVar's disease index carries MedGen's own condition names, matched "
    "exactly -- a synonym, a locus name or a one-letter misspelling matches "
    "nothing there. Look the condition up (e.g. via MedGen_search_conditions) "
    "and re-run with the indexed name to get a disease-filtered answer."
)


def _condition_filter_disclosure(
    condition: Any,
    condition_term: str,
    query_translation: str,
    freetext_retry: bool,
) -> Dict[str, Any]:
    """State, at the top level of the response, whether the caller's
    `condition` actually acted as a DISEASE filter on the count being returned.

    A disease-filtered count and a free-text count are indistinguishable in the
    payload but mean entirely different things -- "996 RPE65 records classified
    for Leber congenital amaurosis" versus "1 RPE65 record that happens to
    contain this text somewhere". Either the tool's own untagged retry below or
    an Entrez rewrite of the field tag can turn one into the other, and both
    are visible in the `querytranslation` Entrez already returned, so the
    distinction is disclosed without a second request.
    """
    fields = _field_tags_for_term(query_translation, condition_term)
    if any(f.lower() == "dis" for f in fields):
        return {"condition_filter_applied": True}
    if freetext_retry:
        field = fields[0] if fields else "All Fields"
        return {
            "condition_filter_applied": False,
            "condition_search_field": field,
            "condition_filter_warning": (
                f"total_count is NOT disease-filtered. The disease-restricted "
                f"search for condition '{condition}' returned no records, so the "
                f"term was automatically retried unrestricted (Entrez searched it "
                f"as [{field}]) and that free-text count is what is reported here: "
                "it counts records merely mentioning this text anywhere -- variant "
                "names, submitter comments, other linked conditions -- rather than "
                "records classified for this condition. " + _CONDITION_INDEX_GUIDANCE
            ),
        }
    if fields:
        field = fields[0]
        return {
            "condition_filter_applied": False,
            "condition_search_field": field,
            "condition_filter_warning": (
                f"total_count is NOT disease-filtered. Entrez did not keep the "
                f"[dis] field tag for condition '{condition}' -- it searched the "
                f"term as [{field}] instead (see query_translation), which matches "
                "the text anywhere in a record rather than restricting to records "
                "classified for this condition. " + _CONDITION_INDEX_GUIDANCE
            ),
        }
    # No translation echoed back (or the term is unrecognisable in it): there
    # is no evidence either way, and inventing a warning would be as misleading
    # as omitting a real one.
    return {}


def _optional_record_list(record: Dict[str, Any], field: str) -> list:
    """Return an optional record-list field, validating its shape.

    Follow-up 2026-10-23 (Batch C): absence, null and empty list mean
    "optional information not provided" and yield ``[]`` (the detail
    assemblies keep their existing empty output fields). A PRESENT,
    non-empty value of any other shape -- or holding non-object
    elements -- is corrupted input and raises ``ValueError`` naming the
    field, instead of the IndexError/AttributeError the ``[0]``/``.get``
    indexing used to throw deep inside the detail assembly.
    """
    value = record.get(field)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(
            f"'{field}' must be a list of objects when present, got "
            f"{type(value).__name__}"
        )
    for element in value:
        if not isinstance(element, dict):
            raise ValueError(
                f"'{field}' entries must be objects, got "
                f"{type(element).__name__} ({element!r})"
            )
    return value


def _validate_optional_detail_containers(variant_data: Dict[str, Any]) -> None:
    """Validate the optional containers the single-DETAIL tools index into.

    Pairs with ``_parse_variant_summary`` (which has already validated the
    record object itself plus ``genes`` and ``germline_classification``):
    the fields below are only read by the details / clinical-significance
    assemblies, so their shape contract lives here. Null-or-absent means
    optional-not-provided; a present value of the wrong shape is an
    explicit error. First-record selection semantics and every public
    output field are unchanged; no position inference or assembly
    auto-selection is added.
    """
    variation_set = _optional_record_list(variant_data, "variation_set")
    if variation_set:
        # Only the FIRST record is ever read by the details assembly, so
        # only its nested loc container needs the shape contract here.
        _optional_record_list(variation_set[0], "variation_loc")
    germline = variant_data.get("germline_classification")
    if germline:
        _optional_record_list(germline, "trait_set")
    for field in (
        "clinical_impact_classification",
        "oncogenicity_classification",
    ):
        value = variant_data.get(field)
        if value is not None and not isinstance(value, dict):
            raise ValueError(
                f"'{field}' must be an object when present, got "
                f"{type(value).__name__}"
            )


class ClinVarRESTTool(BaseTool):
    """Base class for ClinVar REST API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None, max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make a request to the ClinVar API with automatic retry for rate limiting."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)

                # Handle rate limiting (429 error)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        # Default exponential backoff: 1, 2, 4 seconds
                        wait_time = 2**attempt

                    if attempt < max_retries:
                        print(
                            f"Rate limited (429). Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        return {
                            "status": "error",
                            "error": f"Rate limited after {max_retries} retries. Please wait before making more requests.",
                            "url": response.url,
                            "retry_after": retry_after,
                        }

                response.raise_for_status()

                # ClinVar API returns XML by default, but we can request JSON
                if params and params.get("retmode") == "json":
                    data = response.json()
                else:
                    # Parse XML response
                    data = response.text

                return {
                    "status": "success",
                    "data": data,
                    # response.url includes the query string that params=
                    # adds; the pre-request url does not.
                    "url": response.url,
                    "content_type": response.headers.get(
                        "content-type", "application/xml"
                    ),
                    "rate_limit_info": {
                        "limit": response.headers.get("X-RateLimit-Limit"),
                        "remaining": response.headers.get("X-RateLimit-Remaining"),
                    },
                }

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    wait_time = 2**attempt
                    print(
                        f"Request failed: {str(e)}. Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        "status": "error",
                        "error": f"ClinVar API request failed after {max_retries} retries: {str(e)}",
                        "url": url,
                    }

        return {"status": "error", "error": "Maximum retries exceeded", "url": url}

    def _parse_variant_summary(self, vdata: Dict[str, Any]) -> Dict[str, Any]:
        """Strictly validate and extract fields from ONE esummary record.

        Follow-up 2026-10-14: this parser is shared by the search tool's
        per-record loop and the details tool. Structural damage used to
        escape as a raw TypeError/AttributeError (``genes=None``,
        ``genes={}``, a non-object list entry, ``germline_classification``
        of non-object type) or pass silently as an all-blank "valid"
        detail (an empty object). Now the record's SHAPE is validated
        first and damage raises ``ValueError`` naming the offending
        field; callers isolate or surface it explicitly.

        No biological applicability condition is added: a record may
        legitimately lack ``genes``, ``germline_classification`` (no
        classification yet) or any other optional field -- omitted keys
        yield blank values and the record stays valid.
        """
        if not isinstance(vdata, dict) or not vdata:
            raise ValueError("record is empty or not a JSON object")
        if "genes" in vdata:
            genes = vdata["genes"]
            if genes is None:
                raise ValueError("'genes' is null; omit the key or use a list")
            if not isinstance(genes, list):
                raise ValueError(
                    f"'genes' must be a list of objects, got "
                    f"{type(genes).__name__}"
                )
            for gene in genes:
                if not isinstance(gene, dict):
                    raise ValueError(
                        f"'genes' entries must be objects, got "
                        f"{type(gene).__name__} ({gene!r})"
                    )
        if "germline_classification" in vdata:
            gc_value = vdata["germline_classification"]
            if gc_value is None:
                raise ValueError(
                    "'germline_classification' is null; omit the key or "
                    "use an object"
                )
            if not isinstance(gc_value, dict):
                raise ValueError(
                    f"'germline_classification' must be an object, got "
                    f"{type(gc_value).__name__}"
                )
        gc = vdata.get("germline_classification") or {}
        genes = vdata.get("genes") or []
        return {
            "title": vdata.get("title", ""),
            "genes": [g.get("symbol", "") for g in genes],
            "clinical_significance": gc.get("description", ""),
            "review_status": gc.get("review_status", ""),
        }

    def _fetch_variant(self, variant_id: str) -> Dict[str, Any]:
        """Fetch a single variant by ID via esummary. Returns (variant_data, error_result) tuple-style dict.

        On success: {"variant_data": {...}, "result": {...}}
        On error: {"error_result": {...}}
        """
        params = {"db": "clinvar", "id": variant_id, "retmode": "json"}
        result = self._make_request("/esummary.fcgi", params)

        if result.get("status") != "success":
            return {"error_result": result}

        # Follow-up 2026-10-23 (Batch C): type-check the envelope BEFORE
        # any nested ``.get``. A present-but-wrong-type ``data``/``result``
        # (e.g. ``data: []`` or ``result: null``) used to crash with a raw
        # AttributeError; a UID key mapped to a list crashed on the record's
        # own ``.get``. Each now surfaces as an explicit malformed-envelope
        # error -- present-null follows the parser's house rule that a
        # declared-but-null container is damaged, not "absent". A MISSING
        # key keeps the pre-existing not-found path.
        envelope_problems = []
        if "data" in result and not isinstance(result["data"], dict):
            envelope_problems.append(
                f"'data' must be a JSON object, got {type(result['data']).__name__}"
            )
        data = result.get("data")
        if data is None:
            data = {}
        if isinstance(data, dict) and "result" in data and not isinstance(
            data["result"], dict
        ):
            envelope_problems.append(
                f"'result' must be a JSON object, got {type(data['result']).__name__}"
            )
        if envelope_problems:
            return {
                "error_result": {
                    "status": "error",
                    "error": "ClinVar esummary response is malformed: "
                    + "; ".join(envelope_problems),
                    "url": result.get("url"),
                }
            }
        inner = data.get("result") or {}
        variant_data = inner.get(variant_id)
        if variant_data is not None and not isinstance(variant_data, dict):
            return {
                "error_result": {
                    "status": "error",
                    "error": (
                        f"ClinVar esummary record for uid '{variant_id}' "
                        f"must be a JSON object, got {type(variant_data).__name__}"
                    ),
                    "url": result.get("url"),
                }
            }

        if not variant_data:
            # NCBI returns HTTP 200 with an empty uids list and an inline
            # "Invalid uid ..." message when the id is not a numeric ClinVar
            # Variation ID (e.g. a dbSNP rsID was passed). Surface this as a
            # real error instead of forwarding the raw success envelope.
            ncbi_err = data.get("error") or inner.get("error")
            msg = f"No ClinVar record found for variant_id '{variant_id}'."
            if isinstance(variant_id, str) and variant_id.lower().startswith("rs"):
                msg += (
                    " Pass a numeric ClinVar Variation ID (e.g. 12345), not a"
                    " dbSNP rsID."
                )
            if ncbi_err:
                msg += f" NCBI: {ncbi_err}"
            return {
                "error_result": {
                    "status": "error",
                    "error": msg,
                    "url": result.get("url"),
                }
            }

        # Check for NCBI inline error (HTTP 200 but variant not found)
        if variant_data.get("error"):
            return {
                "error_result": {
                    "status": "error",
                    "error": f"Variant {variant_id} not found in ClinVar: {variant_data['error']}",
                    "url": result.get("url"),
                }
            }

        # Follow-up 2026-10-14: validate the record's SHAPE with the shared
        # strict parser BEFORE the caller assembles details or fetches
        # submitter citations -- a malformed record surfaces as an explicit
        # error here instead of a raw AttributeError or an empty-details
        # "success" downstream. Only the parser's ValueError is caught.
        # Follow-up 2026-10-23 (Batch C): the optional detail containers
        # (variation_set/variation_loc, trait_set, clinical_impact and
        # oncogenicity classifications) are validated in the same step so a
        # corrupt detail errors out BEFORE any citation fetch; a citation
        # fetch that merely fails still degrades to a healthy detail with
        # citations_complete=false downstream.
        try:
            variant_summary = self._parse_variant_summary(variant_data)
            _validate_optional_detail_containers(variant_data)
        except ValueError as exc:
            return {
                "error_result": {
                    "status": "error",
                    "error": (
                        f"Variant {variant_id} esummary record is "
                        f"malformed: {exc}"
                    ),
                    "url": result.get("url"),
                }
            }

        return {
            "variant_data": variant_data,
            "variant_summary": variant_summary,
            "result": result,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(self.endpoint, arguments)


@register_tool("ClinVarSearchVariants")
class ClinVarSearchVariants(ClinVarRESTTool):
    """Search for variants in ClinVar by gene or condition."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/esearch.fcgi"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search variants by gene or condition."""
        # Normalize aliases before dispatch
        if not arguments.get("gene") and arguments.get("gene_symbol"):
            arguments = dict(arguments, gene=arguments["gene_symbol"])
        _clnsig_param = "clinical_significance"
        if not arguments.get("clinical_significance") and arguments.get("significance"):
            arguments = dict(arguments, clinical_significance=arguments["significance"])
            _clnsig_param = "significance"
        # Validate the clinical-significance filter BEFORE anything is queried:
        # an unrecognized class used to be pasted into the Entrez term, match
        # nothing, and come back as a `status: success` with 0 results whose
        # hint blamed the (perfectly valid) gene symbol instead.
        clnsig_components = []
        if str(arguments.get("clinical_significance") or "").strip():
            clnsig_components = _normalize_clinsig(arguments["clinical_significance"])
            invalid_clnsig = [
                c for c in clnsig_components if c not in _CLINSIG_ACCEPTED_NORMALIZED
            ]
            if invalid_clnsig:
                return _invalid_clinsig_error(
                    _clnsig_param,
                    arguments["clinical_significance"],
                    invalid_clnsig,
                )
        # An rsID (e.g. rs4244285) passed as `query` was aliased to `condition`
        # and searched as a DISEASE term ('rs4244285[dis]'), silently returning
        # 0 -- but ClinVar's free-text index DOES match a bare rsID (confirmed
        # live: term=rs4244285 -> 37 records). Route an rsID to a bare-term
        # search so the standard PGx chain rsID -> ClinVar works instead of a
        # false 'not found'.
        _rsid_src = arguments.get("rsid") or arguments.get("query")
        if (
            not arguments.get("rsid")
            and isinstance(_rsid_src, str)
            and re.fullmatch(r"rs\d+", _rsid_src.strip(), re.IGNORECASE)
        ):
            arguments = dict(arguments, rsid=_rsid_src.strip())
            arguments.pop("query", None)
        # A `query` carrying Entrez field tags ("7[chr] AND 1000:2000[chrpos37]")
        # is a search expression, not a disease name. Aliasing it to `condition`
        # wrapped the whole string in [dis] and returned 0 with no hint why.
        _q = arguments.get("query")
        if isinstance(_q, str) and re.search(r"\[[a-z0-9]+\]", _q, re.IGNORECASE):
            arguments = dict(arguments, raw_term=_q)
            arguments.pop("query", None)
        if not arguments.get("condition") and arguments.get("query"):
            arguments = dict(arguments, condition=arguments["query"])
        # `variant` is the intuitive name for the variant filter (the schema
        # calls it `variant_name`). Passing `variant` used to be silently
        # dropped whenever a valid param like `gene` was also present, so
        # {"gene":"KRAS","variant":"G12C"} returned ALL 599 KRAS variants
        # instead of the 2 G12C ones -- a dangerous silent full-gene dump.
        # Alias it, mirroring the gene_symbol/significance/query aliases above.
        if not arguments.get("variant_name") and arguments.get("variant"):
            arguments = dict(arguments, variant_name=arguments["variant"])

        params = {
            "db": "clinvar",
            "retmode": "json",
            "retmax": arguments.get("max_results") or arguments.get("limit", 20),
        }

        # Build search query
        query_parts = []
        compound_clnsig = False
        # Fix-C-20260918 diagnostics: what variant_name actually arrived as
        # (string vs list) and, when a stringified JSON array was compat-
        # parsed, which names were used. Attached to search_params below.
        variant_name_compat = None
        variant_names_used = None
        variant_id_normalized = None

        # An expression the caller wrote themselves goes to Entrez untouched.
        if arguments.get("raw_term"):
            query_parts.append(str(arguments["raw_term"]))

        gene = None
        gene_hyphen_variant = None
        if "gene" in arguments:
            # Fix-R10D-1: ClinVar's [gene] index only matches a bare HGNC
            # symbol, but a natural clinical phrasing like "NF2 gene" (used
            # verbatim in real research questions -- e.g. "look up the NF2
            # gene") silently returns 0 results, since the literal trailing
            # word "gene" becomes part of the queried string (confirmed
            # live and via raw NCBI E-utils curl: "Nf2 gene[gene]" -> 0
            # hits, "NF2[gene]" -> 2612 hits). Strip a trailing/leading
            # "gene"/"protein" qualifier word before querying.
            gene = re.sub(
                r"^\s*(?:gene|protein)\s+|\s+(?:gene|protein)\s*$",
                "",
                arguments["gene"],
                flags=re.IGNORECASE,
            ).strip()

            # Fix-R8B-1 (revised, Fix-R49A-1): some genes are informally
            # hyphenated even though their current HGNC symbol has none (e.g.
            # "BRCA-2" for "BRCA2", "HER-2" for "HER2" -- confirmed live via
            # raw NCBI E-utils: "BRCA-2[gene]" -> 0 hits, "BRCA2[gene]" ->
            # 21879 hits). R8B-1 originally handled this by unconditionally
            # stripping every hyphen, but that silently broke every gene
            # whose CURRENT official HGNC symbol genuinely contains one --
            # confirmed live for the entire HLA family (HLA-B[gene] -> 130
            # hits, HLAB[gene] -> 0), the NKX homeobox family (NKX2-5[gene]
            # -> real hits, NKX25[gene] -> 0), and MT- mitochondrial genes
            # (MT-ND1[gene] -> 194 hits, MTND1[gene] -> 0) -- all clinically
            # significant gene families (HLA pharmacogenomics/transplant,
            # NKX cardiac/pancreatic development, MT- mitochondrial disease).
            # Query with the hyphen preserved first; only fall back to the
            # stripped form if that returns zero results, so both the old
            # informally-hyphenated-name case and genuinely-hyphenated
            # official symbols work.
            if "-" in gene:
                gene_hyphen_variant = gene.replace("-", "")
            # F05 (2026-10-13): record WHERE the gene term sits instead of
            # assuming index 0 -- a raw_term Entrez expression (via `query`)
            # is appended before it, and the retries below used
            # query_parts[1:], which dropped the caller's expression and
            # kept the OLD gene term ({"gene":"GBA","query":"1[chr]"}
            # retried as "GBA1[gene] AND GBA[gene]").
            gene_query_index = len(query_parts)
            query_parts.append(f"{gene}[gene]")

        condition_dis_index = None
        condition_query_term = None
        condition_freetext_retry = False
        if "condition" in arguments:
            # Feature-70B-005: [disease/phenotype] is not a valid ClinVar eSearch field.
            # Use [dis] (disease/phenotype) field tag for condition searches.
            # Quote multi-word conditions so ClinVar treats them as a phrase.
            condition = arguments["condition"].strip()
            if " " in condition and not condition.startswith('"'):
                condition = f'"{condition}"'
            condition_query_term = condition
            condition_dis_index = len(query_parts)
            query_parts.append(f"{condition}[dis]")

        if arguments.get("rsid"):
            # Search a dbSNP rsID as a bare free-text term -- ClinVar matches it
            # across the record (not via [dis]/[gene]/[Variant name]).
            query_parts.append(str(arguments["rsid"]).strip())

        if "variant_id" in arguments and arguments["variant_id"] is not None:
            # Feature-70B-004: [variant_id] is not recognized by ClinVar
            # eSearch. Use [uid] to look up by numeric variation ID.
            # Fix-D-20260918: anything other than a positive numeric ID or
            # a suffix-free VCV accession pasted into "<N>[uid]" silently
            # returned count 0 with an empty translation (confirmed live:
            # "rs2151556776[uid]" -> 0 hits, while the same rsID as free
            # text hits VCV 2737810). Validate and normalize BEFORE the
            # request instead of letting eSearch answer a query that
            # cannot match; never silently rewrite the caller's argument.
            uid, vid_error = _normalize_variant_id(arguments["variant_id"])
            if vid_error is not None:
                return {"status": "error", "error": vid_error}
            variant_id_normalized = uid
            query_parts.append(f"{uid}[uid]")

        if arguments.get("variant_name") is not None:
            # Fix-R78B-1: the Fix-R5D-1/R8C-1 comment above assumed there was
            # "no such parameter" -- but ClinVar eSearch DOES support a real
            # [Variant name] field tag (confirmed live: "HBB[gene] AND
            # Glu7Val[Variant name]" -> 9 hits including VCV 15333, the
            # canonical sickle-cell NM_000518.5(HBB):c.20A>T (p.Glu7Val)
            # Pathogenic record). Without this, an exact-match lookup for a
            # specific protein change/HGVS notation could only be done by
            # fetching gene-level rows (capped at 100) and filtering
            # client-side -- which silently misses old/low-ID records in any
            # variant-dense gene, since ClinVar's default gene-level order
            # isn't clinical-significance- or fame-ranked (confirmed live:
            # HBB's own sickle-cell record, one of the best-known variants in
            # human genetics, isn't within the first 100 or even the first
            # 425-Pathogenic-filtered gene-level rows). Accepts either a
            # single name or a list (a multi-allelic site yields one protein
            # change per allele; only the queried allele's name will hit, so
            # every candidate must be tried) -- combined with OR so one
            # request covers all candidates.
            names = arguments["variant_name"]
            # Fix-C-20260918: some MCP hosts serialize a JSON-array
            # argument into a single string. Without this compat step the
            # whole string was treated as ONE name and the quote-stripping
            # below folded it into a single malformed term that matches
            # nothing (see _coerce_stringified_name_array). Only the exact
            # stringified-array shape is parsed; plain names and legal HGVS
            # internal brackets are never touched, and malformed arrays are
            # reported rather than comma-split.
            if isinstance(names, str):
                try:
                    names, variant_name_compat = _coerce_stringified_name_array(
                        names
                    )
                except ValueError as exc:
                    return {"status": "error", "error": str(exc)}
            names = names if isinstance(names, list) else [names]
            names = [str(n).strip() for n in names if str(n).strip()]
            # An rsID passed as variant_name (e.g. rs776746) belongs in a bare
            # free-text search, not the [Variant name] field, which returns 0 for
            # it -- route it like the rsid param instead of a false-empty.
            rsid_names = [n for n in names if re.fullmatch(r"rs\d+", n, re.IGNORECASE)]
            names = [n for n in names if n not in rsid_names]
            variant_names_used = names + rsid_names
            # A variant_name that yields no usable term at all (blank string,
            # empty array, nothing but whitespace) used to be silently
            # dropped -- the same silent-ignore class as Fix-R5D-1. Report it
            # instead, unless every element routed to the rsid path above.
            if not names and not rsid_names:
                return {
                    "status": "error",
                    "error": (
                        "variant_name was provided but contained no usable "
                        "names: pass a non-empty string or a JSON array of "
                        "non-empty strings"
                    ),
                }
            # NCBI's [Variant name] index mangles the '.' in an unquoted HGVS
            # reference prefix ('p.Glu342Lys' -> 'p0x2eGlu342Lys') and matches
            # nothing, so a clinician typing standard HGVS got a silent
            # false-empty. Stripping the prefix fixed the protein case, but
            # Fix-R3-07: it silently BROKE the coding case, because c. notation
            # also carries '+'/'>' that Entrez only treats literally inside
            # quotes. Confirmed live -- there is no single spelling that works
            # for both:
            #     DPYD "c.1905+1G>A"[Variant name] -> 1 ; "1905+1G>A" -> 0
            #     SERPINA1 "p.Glu342Lys"    -> 0 ; "Glu342Lys"  -> 2
            # so `tu run ClinVar_search_variants '{"gene":"DPYD",
            # "variant_name":"c.1905+1G>A"}'` reported total_count 0 for
            # VCV000000432, one of the best-known pharmacogenomic variants.
            # Emit BOTH spellings, quoted, OR'd together: an OR can only add
            # matches the old query missed, never drop ones it already found.
            # Verified live: DPYD c.1905+1G>A 0->1, CYP2C19 c.681G>A 0->36,
            # SERPINA1 p.Glu342Lys still 2, HBB p.Glu7Val still 9.
            spellings = []
            for name in names:
                stripped = re.sub(r"(?i)^[pcgmnor]\.", "", name)
                for form in (name, stripped):
                    # Strip embedded quotes so they cannot break out of the
                    # quoted Entrez term.
                    form = form.replace('"', "").strip()
                    if form and form not in spellings:
                        spellings.append(form)
            # F04 (2026-10-13): every variant_name candidate -- bare rsID
            # terms AND the [Variant name] spellings -- is ONE OR group.
            # The old code appended each rsID as its own query part, so
            # " AND " joined them into an intersection: two rsIDs returned
            # the (usually empty) overlap, and rsID+HGVS searched
            # rsID AND names instead of any-of, turning the documented
            # candidate OR into needless false empties.
            candidate_terms = list(rsid_names) + [
                f'"{s}"[Variant name]' for s in spellings
            ]
            if candidate_terms:
                terms = " OR ".join(candidate_terms)
                query_parts.append(
                    f"({terms})" if len(candidate_terms) > 1 else terms
                )

        if "clinical_significance" in arguments:
            # Feature-82A-002: NCBI silently translates [clnsig] to [All Fields],
            # returning unrelated variants. The correct syntax is the [Filter] field:
            # "clinsig pathogenic"[Filter] which properly restricts to the clinsig index.
            #
            # Fix-R6C-1: that [Filter] form only indexes single-word clinsig
            # values -- confirmed live that "clinsig risk factor"[Filter] and
            # "clinsig likely pathogenic"[Filter] both silently return 0
            # results even though matching variants exist (e.g. HFE C282Y,
            # whose own classification literally contains "risk factor").
            # ClinVar separately indexes compound values via clinsig_<value
            # with underscores>[prop] (confirmed live for risk_factor and
            # likely_pathogenic). OR both forms so single-word values keep
            # using the already-verified [Filter] path while compound values
            # fall through to the [prop] path -- this can only add matches
            # the old query missed, never drop ones it already found.
            # A COMPOUND aggregate class like "Pathogenic/Likely pathogenic" has
            # no single NCBI clinsig token -- the slash breaks BOTH the [Filter]
            # phrase and the [prop] token, so the old query silently returned 0
            # even though the tool's OWN get_clinical_significance emits that exact
            # value. Treat "/" as OR and expand to the individual clinsig classes
            # (the clinically-actionable union), each via the proven
            # [Filter]-OR-[prop] path.
            # Values were normalized and validated against the live-verified
            # accepted set up front (see _CLINSIG_ACCEPTED), so every component
            # reaching here is known to exist in ClinVar's index.
            compound_clnsig = len(clnsig_components) > 1
            _clause = _clinsig_query_clause(clnsig_components)
            if _clause:
                query_parts.append(_clause)

        # Fix-R5D-1/R8C-1: a caller-supplied param that doesn't match any
        # recognized name/alias (e.g. "gene_name" instead of "gene") was
        # silently dropped. (Fix-R78B-1: "variant_name" -- originally called
        # out here as "no such parameter" -- is now a real, supported param;
        # see above.) When it's the ONLY param supplied, this
        # produced a generic "at least one search parameter is required"
        # error with no hint the parameter itself was misnamed. When OTHER
        # valid params are also supplied, the query still runs but silently
        # ignores the unrecognized one -- confirmed live that
        # {"gene": "GJB2", "made_up_param": "35delG"} returns all 739 GJB2
        # variants with no indication the made_up_param filter had zero
        # effect. Name unrecognized parameter(s) in both cases.
        recognized = {
            "gene",
            "gene_symbol",
            "condition",
            "query",
            "variant_id",
            "variant_name",
            "variant",
            "rsid",
            "clinical_significance",
            "significance",
            "max_results",
            "limit",
        }
        unrecognized = sorted(set(arguments) - recognized)

        if not query_parts:
            if unrecognized:
                return {
                    "status": "error",
                    "error": (
                        f"Unrecognized parameter(s): {', '.join(unrecognized)}. "
                        "Valid search parameters: gene (or gene_symbol), "
                        "condition (or query), variant_id, variant_name, "
                        "clinical_significance (or significance)."
                    ),
                }
            return {
                "status": "error",
                "error": "At least one search parameter is required",
            }

        params["term"] = " AND ".join(query_parts)

        result = self._make_request(self.endpoint, params)

        if result.get("status") != "success":
            return result

        data = result.get("data", {})
        # Fix-D-20260918: a broken/truncated eSearch payload must not
        # degrade into "query succeeded, zero results". Fix-R1-20260922:
        # the validator now also rejects explicit API errors and malformed
        # count/idlist/translation, and returns the retainable
        # errorlist/warninglist entries to disclose with the result.
        structural_error, query_warnings = _validate_esearch_payload(data)
        if structural_error is not None:
            return {
                "status": "error",
                "error": structural_error,
                "raw_response": data,
            }
        # Warnings from lookups that only EXPLAIN an already-established
        # zero (never replace the result) -- see Fix-R1-20260922.
        auxiliary_warnings: List[str] = []

        # Fix-R49A-1: the hyphen-preserved gene query above found nothing --
        # retry once with the hyphen stripped, for the informally-hyphenated
        # BRCA-2/HER-2-style names ClinVar's index doesn't recognize.
        if gene_hyphen_variant and int(data["esearchresult"].get("count", 0)) == 0:
            # "gene" is always the first query part appended when present.
            fallback_query_parts = (
                query_parts[:gene_query_index]
                + [f"{gene_hyphen_variant}[gene]"]
                + query_parts[gene_query_index + 1:]
            )
            fallback_params = dict(params, term=" AND ".join(fallback_query_parts))
            retry_data, retry_error, retry_warnings = self._replacement_retry(
                fallback_params, "hyphen-stripped gene"
            )
            if retry_error is not None:
                return {"status": "error", "error": retry_error}
            if int(retry_data["esearchresult"].get("count", 0)) > 0:
                data = retry_data
                query_warnings = retry_warnings

        # Fix-R62A-1: some gene symbols are HGNC-deprecated/renamed entirely,
        # not just informally hyphenated -- e.g. "GBA" (glucocerebrosidase,
        # Gaucher disease) was renamed to "GBA1" in 2023 to disambiguate from
        # the GBA2/GBA3 gene family, and ClinVar's own [gene] index has fully
        # absorbed the rename with no backward-compat alias (confirmed live
        # and via raw NCBI E-utils: "GBA[gene]" -> 0 hits, not even recognized
        # as a search phrase; "GBA1[gene]" -> 786 hits). Unlike the hyphen
        # case above, no string transform recovers the current symbol --
        # resolve it via NCBI's own gene database (which tracks "GBA" as an
        # alias of gene ID 2629, current official symbol "GBA1") instead of
        # hardcoding a growing alias list.
        if "gene" in arguments and int(data["esearchresult"].get("count", 0)) == 0:
            resolved_gene, alias_warning = self._resolve_deprecated_gene_symbol(gene)
            if alias_warning:
                auxiliary_warnings.append(alias_warning)
            if resolved_gene and resolved_gene.upper() != gene.upper():
                resolved_query_parts = (
                    query_parts[:gene_query_index]
                    + [f"{resolved_gene}[gene]"]
                    + query_parts[gene_query_index + 1:]
                )
                resolved_params = dict(params, term=" AND ".join(resolved_query_parts))
                retry_data, retry_error, retry_warnings = self._replacement_retry(
                    resolved_params, f"alias-resolved gene {resolved_gene}"
                )
                if retry_error is not None:
                    return {"status": "error", "error": retry_error}
                if int(retry_data["esearchresult"].get("count", 0)) > 0:
                    data = retry_data
                    query_warnings = retry_warnings

        # Fix-R9B-1: the [dis] field only matches ClinVar's own indexed
        # disease/phenotype name for a record, which frequently differs from
        # the name clinicians actually use -- confirmed live that
        # "MECP2 duplication syndrome"[dis] (arguably the most natural way to
        # refer to this exact condition) returns 0 even though ClinVar has
        # 101+ MECP2 records that reference that phrase in free text (under
        # its indexed name "Xq28 duplication syndrome" instead). Retry once
        # with the condition term unrestricted to any field ([All Fields])
        # when the [dis]-restricted search comes back empty -- this can only
        # add matches the strict query missed, never drop ones it found.
        #
        # ...but the count it produces is a free-text count, not a
        # disease-filtered one, and the two used to be reported identically:
        # `{"gene":"RPE65","condition":"Lebers congenital amaurosis"}` (one
        # letter off the indexed name) came back a plain success with
        # total_count 1 next to the 996 of the correctly-spelled query, with
        # nothing saying the second number was a substring match. Record that
        # this retry happened so the response can say so.
        if (
            condition_dis_index is not None
            and int(data["esearchresult"].get("count", 0)) == 0
        ):
            freetext_query_parts = list(query_parts)
            # The stored term is "<condition>[dis]" -- drop the field tag to
            # search it unrestricted instead.
            freetext_query_parts[condition_dis_index] = query_parts[
                condition_dis_index
            ][: -len("[dis]")]
            freetext_params = dict(params, term=" AND ".join(freetext_query_parts))
            retry_data, retry_error, retry_warnings = self._replacement_retry(
                freetext_params, "condition free-text"
            )
            if retry_error is not None:
                return {"status": "error", "error": retry_error}
            if int(retry_data["esearchresult"].get("count", 0)) > 0:
                data = retry_data
                query_warnings = retry_warnings
                condition_freetext_retry = True

        esearch = data["esearchresult"]
        ids = esearch["idlist"]
        count = int(esearch["count"])
        # Fix-D-20260918: retainable query warnings are surfaced, not fatal
        # -- a real OR query with phrasesnotfound (errorlist, its REAL
        # position in eSearch responses) can still have valid hits, so
        # errorlist/warninglist must never turn a populated result into an
        # error. The warnings tracked here are the ADOPTED payload's; the
        # auxiliary explain-zero warnings collected above are appended below.
        query_warnings = list(query_warnings) + auxiliary_warnings

        variants = []
        # F06 (2026-10-13): a failing or partially broken details (esummary)
        # fetch after a successful search used to be silently swallowed --
        # counts and IDs came back with variants: [] and nothing said the
        # details were missing. Completeness is measured against the
        # RETURNED ids only (a total_count above the page size is
        # pagination, not missing details); reasons go to `warnings`, never
        # query_warnings; a healthy empty query is complete.
        missing_variant_ids: List[str] = []
        detail_warnings: List[str] = []
        if ids:
            summary_result = self._make_request(
                "/esummary.fcgi",
                {"db": "clinvar", "id": ",".join(ids[:200]), "retmode": "json"},
            )
            result_map = None
            if summary_result.get("status") != "success":
                detail_warnings.append(
                    "variant details (esummary) request failed: "
                    + str(summary_result.get("error") or "request failed")
                    + "; search counts and IDs are kept but no details "
                    "could be parsed"
                )
            else:
                summary_data = summary_result.get("data")
                container = (
                    summary_data.get("result")
                    if isinstance(summary_data, dict)
                    else None
                )
                if isinstance(container, dict):
                    result_map = container
                else:
                    detail_warnings.append(
                        "variant details (esummary) response was missing or "
                        "malformed at the top level (no result object); "
                        "search counts and IDs are kept but no details "
                        "could be parsed"
                    )
            if result_map is not None:
                for vid in ids:
                    vdata = result_map.get(vid)
                    if not isinstance(vdata, dict):
                        missing_variant_ids.append(vid)
                        continue
                    if vdata.get("error"):
                        missing_variant_ids.append(vid)
                        detail_warnings.append(
                            f"esummary record for variant id {vid} returned "
                            f"an error: {vdata['error']}"
                        )
                        continue
                    # Follow-up 2026-10-14: the shared parser validates the
                    # record's SHAPE (genes list-of-objects,
                    # germline_classification object, non-empty record). One
                    # damaged record is isolated -- counts, IDs and the
                    # other healthy details are kept, the failed UID is
                    # disclosed as missing with its field-level reason.
                    # Only ValueError from the parser is caught; other
                    # programming errors still propagate.
                    try:
                        summary = self._parse_variant_summary(vdata)
                    except ValueError as exc:
                        missing_variant_ids.append(vid)
                        detail_warnings.append(
                            f"esummary record for variant id {vid} is "
                            f"malformed: {exc}"
                        )
                        continue
                    variants.append({"variant_id": vid, **summary})
            else:
                missing_variant_ids = list(dict.fromkeys(ids))
        # Order-preserving dedup of the missing IDs (the idlist is normally
        # unique already; this guards against pathological payloads).
        missing_variant_ids = list(dict.fromkeys(missing_variant_ids))
        if missing_variant_ids and not detail_warnings:
            detail_warnings.append(
                "no parseable details for "
                f"{len(missing_variant_ids)} of {len(ids)} returned "
                "variant id(s): " + ", ".join(missing_variant_ids)
            )
        details_complete = not missing_variant_ids and not detail_warnings

        search_params = {
            k: v
            for k, v in {
                "gene": arguments.get("gene"),
                "condition": arguments.get("condition"),
                "variant_id": arguments.get("variant_id"),
                "clinical_significance": arguments.get("clinical_significance"),
            }.items()
            if v is not None
        }
        # Fix-C-20260918: disclose what variant_name arrived as and what was
        # actually queried, and warn when a stringified JSON array had to be
        # compat-parsed -- the caller should fix the serialization, but the
        # query itself is now correct either way.
        response_warnings = []
        response_warnings.extend(detail_warnings)
        if variant_names_used is not None:
            search_params["variant_name_received_type"] = (
                variant_name_compat["received_type"]
                if variant_name_compat
                else ("list" if isinstance(arguments.get("variant_name"), list) else "string")
            )
            search_params["variant_names_used"] = variant_names_used
        if variant_name_compat is not None:
            response_warnings.append(
                "variant_name arrived as a string containing a stringified "
                "JSON array and was parsed with json.loads; pass a real "
                "JSON array to avoid ambiguity"
            )
        if variant_id_normalized is not None:
            search_params["variant_id_used"] = variant_id_normalized
        query_translation = esearch.get("querytranslation", "")
        response_data = {
            "total_count": count,
            "variant_ids": ids,
            "variants": variants,
            "details_complete": details_complete,
            "missing_variant_ids": missing_variant_ids,
            "query_translation": query_translation,
            "search_params": search_params,
        }
        if response_warnings:
            response_data["warnings"] = response_warnings
        if query_warnings:
            response_data["query_warnings"] = query_warnings
        # Whether `condition` acted as a disease filter on the count above is
        # part of what the count MEANS, so it belongs beside it at the top
        # level rather than inside a note the caller has to read to notice.
        condition_applied = None
        if condition_query_term is not None:
            disclosure = _condition_filter_disclosure(
                arguments.get("condition"),
                condition_query_term,
                query_translation,
                condition_freetext_retry,
            )
            response_data.update(disclosure)
            condition_applied = disclosure.get("condition_filter_applied")
        if count == 0:
            extras = self._explain_empty_result(
                arguments=arguments,
                gene=gene,
                condition_term=condition_query_term,
                condition_applied=condition_applied,
                clnsig_param=_clnsig_param,
                clnsig_components=clnsig_components,
            )
            # Fix-R1-20260922: auxiliary explain-zero failures ride along as
            # query_warnings; the zero result itself is untouched.
            zero_warnings = extras.pop("zero_result_warnings", None)
            response_data.update(extras)
            if zero_warnings:
                response_data.setdefault("query_warnings", []).extend(zero_warnings)
        if unrecognized:
            response_data["ignored_parameters"] = unrecognized
        if compound_clnsig:
            response_data["clinical_significance_note"] = (
                "The '/' in the requested clinical_significance was treated as OR: "
                "results are the union of the individual classes (e.g. Pathogenic "
                "AND Likely pathogenic), which is broader than only the aggregate "
                "'Pathogenic/Likely pathogenic' review class."
            )
        return {"status": "success", "data": response_data}

    def _explain_empty_result(
        self,
        *,
        arguments: Dict[str, Any],
        gene: Optional[str],
        condition_term: Optional[str],
        condition_applied: Optional[bool],
        clnsig_param: str,
        clnsig_components: list,
    ) -> Dict[str, Any]:
        """Attribute an empty result to the input that actually caused it.

        A 0-count is only usable if the caller can tell "ClinVar holds no such
        record" from "one of my inputs is not something ClinVar indexes", so
        the evidence is established with count-only queries (retmax=0) on a
        path that has already come back empty, rather than assumed. Both the
        gene symbol and -- since a disease NAME missing from ClinVar's index
        empties a result exactly as silently as a wrong symbol does -- the
        condition are checked on their own before anything is blamed.
        """
        extras: Dict[str, Any] = {}
        # Fix-R1-20260922: these evidence lookups only explain an
        # already-valid zero; their failures are warnings, never errors,
        # and the caller merges them into query_warnings.
        zero_warnings: List[str] = []
        condition = arguments.get("condition")
        has_gene = "gene" in arguments

        # Fix-R9B-2: a 0-count response for a `gene` filter is
        # indistinguishable from "this gene truly has no ClinVar
        # entries" whether the symbol was a typo (e.g. "MEPC2"), a
        # protein/full name instead of the HGNC gene symbol (e.g.
        # "dystrophin" instead of "DMD"), or a species mismatch --
        # confirmed live that ClinVar's [gene] index only matches an
        # exact current HGNC symbol and has no fuzzy/synonym fallback of
        # its own. Automatically retrying with an unrestricted free-text
        # search was tried and rejected: "dystrophin[All Fields]"
        # matches 12,000+ unrelated ClinVar records that merely mention
        # the word, which would silently swap a false-empty for a
        # false-positive result set -- worse than reporting nothing.
        # Surface the ambiguity instead of guessing.
        #
        # ...but only blame the GENE when the gene is actually what failed.
        # When other filters narrowed the query, a 0 count says nothing
        # about the symbol, and the hint used to send callers off to
        # re-verify a symbol that was never the problem. Establish the
        # facts with one cheap count-only query on the bare gene term
        # before attributing the empty result to anything.
        other_filters = [
            name
            for name, present in (
                ("condition", bool(condition)),
                ("variant_id", "variant_id" in arguments),
                ("variant_name", bool(arguments.get("variant_name"))),
                ("rsid", bool(arguments.get("rsid"))),
                ("raw_term", bool(arguments.get("raw_term"))),
                (clnsig_param, bool(clnsig_components)),
            )
            if present
        ]
        gene_only_count: Optional[int] = None
        if has_gene and other_filters:
            gene_only_count, gene_check_warning = self._count_for_term(
                f"{gene}[gene]"
            )
            if gene_check_warning:
                zero_warnings.append(gene_check_warning)
        if gene_only_count is not None:
            extras["gene_only_match_count"] = gene_only_count
        # The same evidence, for the condition: `condition` is the only other
        # input whose value has to exist in an NCBI-curated index to match
        # anything, and a name that index does not carry (a synonym, a locus
        # name, a misspelling) empties the result just as silently as a wrong
        # gene symbol -- yet it used to go unmentioned while the hint sent the
        # caller off to re-verify the symbol.
        condition_only_count: Optional[int] = None
        if condition_term is not None:
            condition_only_count, condition_check_warning = self._count_for_term(
                f"{condition_term}[dis]"
            )
            if condition_check_warning:
                zero_warnings.append(condition_check_warning)
        if condition_only_count is not None:
            extras["condition_only_match_count"] = condition_only_count
        if zero_warnings:
            extras["zero_result_warnings"] = zero_warnings

        gene_verdict = ""
        if has_gene and gene_only_count:
            gene_verdict = (
                f" The gene symbol '{arguments['gene']}' is not the problem: it "
                f"matches {gene_only_count} ClinVar record(s) on its own."
            )

        # 1. The condition never acted as a disease filter at all -- whatever
        #    else is true, this result is not the disease-filtered answer the
        #    caller asked for.
        if condition_term is not None and condition_applied is False:
            extras["zero_result_hint"] = (
                f"No ClinVar records matched, and the condition '{condition}' was "
                "not applied as a disease filter: Entrez did not keep the [dis] "
                "field tag for it (see query_translation), so this empty result "
                "says nothing about whether ClinVar holds records for this "
                f"condition.{gene_verdict} " + _CONDITION_INDEX_GUIDANCE
            )
            return extras
        # 2. Fix-B-20260922: the condition-only evidence query itself
        #    failed (request error or a broken payload). Without that
        #    count it is UNKNOWN whether the condition name (a synonym, a
        #    locus name, a misspelling ClinVar's disease index does not
        #    carry) is what emptied the result -- so no "recognized
        #    disease term" claim, no "(None record(s))" placeholder, and
        #    no definitive attribution to the other filter(s). The
        #    already-established gene-only count, if any, is kept and
        #    reported; the failure itself also rides along as a
        #    query_warning via zero_warnings above.
        if condition_term is not None and condition_only_count is None:
            hint = (
                f"No ClinVar records matched. The zero-result check for the "
                f"condition '{condition}' could not be completed, so it is "
                "unknown whether the condition name is something ClinVar's "
                "disease index does not carry (a synonym, a locus name, a "
                "misspelling) or whether the other search input(s) produced "
                "the empty result -- retry with the condition removed to "
                "tell them apart."
            )
            extras["zero_result_hint"] = hint + gene_verdict + " " + _CONDITION_INDEX_GUIDANCE
            return extras
        # 3. The condition name matches nothing in ClinVar's disease index at
        #    all, so it -- not the gene, not the other filters -- is what
        #    emptied the result.
        if condition_term is not None and condition_only_count == 0:
            extras["zero_result_hint"] = (
                f"The condition '{condition}' matches no ClinVar records at all on "
                f"its own ({condition_term}[dis] returns 0 across every gene), so "
                "the empty result is attributable to the condition name rather "
                f"than to the other search inputs.{gene_verdict} "
                + _CONDITION_INDEX_GUIDANCE
            )
            return extras

        if has_gene and other_filters and gene_only_count is None:
            extras["zero_result_hint"] = (
                f"No ClinVar records matched gene '{arguments['gene']}' "
                f"combined with {', '.join(other_filters)}. The gene symbol "
                "could not be checked on its own (follow-up query failed), "
                "so it is unknown whether the symbol or the other filter(s) "
                "produced the empty result -- retry with the filters removed "
                "to tell them apart."
            )
        elif has_gene and gene_only_count:
            hint = (
                f"The gene symbol '{arguments['gene']}' is fine: it matches "
                f"{gene_only_count} ClinVar record(s) on its own. The empty "
                f"result comes from the other filter(s) -- "
                f"{', '.join(other_filters)} -- which no record for this gene "
                "satisfies. Relax or correct them (or drop them to see the "
                "gene's full record set) rather than re-checking the symbol."
            )
            if condition_only_count:
                hint += (
                    f" The condition '{condition}' is itself a recognized ClinVar "
                    f"disease term ({condition_only_count} record(s) across all "
                    "genes), so this gene and this condition simply have no record "
                    "in common."
                )
            extras["zero_result_hint"] = hint
        elif has_gene:
            extras["zero_result_hint"] = (
                f"No ClinVar records matched gene '{arguments['gene']}'. "
                "ClinVar's gene index only recognizes the current official "
                "HGNC symbol (e.g. 'DMD', not the protein name 'dystrophin' "
                "or an outdated/misspelled symbol) -- verify the symbol "
                "(e.g. via HGNC_search_genes or NCBIDatasets_get_gene) "
                "before concluding this gene has no reported variants."
            )
        elif condition_term is not None:
            remaining = [f for f in other_filters if f != "condition"]
            extras["zero_result_hint"] = (
                f"The condition '{condition}' is a recognized ClinVar disease term "
                f"({condition_only_count} record(s) on its own), so the empty "
                "result comes from the other filter(s)"
                + (f" -- {', '.join(remaining)} -- " if remaining else " ")
                + "rather than from the condition name."
            )
        return extras

    def _count_for_term(self, term: str) -> Tuple[Optional[int], Optional[str]]:
        """Count-only eSearch for `term` (retmax=0, no summaries fetched).

        Used to establish, rather than assume, which input caused an empty
        result. Fix-R1-20260922: this lookup only EXPLAINS an already-valid
        zero, so its failure keeps the original result and yields a warning
        -- the zero stands but its attribution is unknown, and the caller
        must not read it as "this gene/condition has no records". Returns
        ``(count, failure_warning)``; ``(None, None)`` never happens for a
        completed check, and the method never raises.
        """
        try:
            result = self._make_request(
                self.endpoint,
                {"db": "clinvar", "term": term, "retmode": "json", "retmax": 0},
            )
            if result.get("status") != "success":
                return None, self._zero_check_warning(term, "request failed")
            data = result.get("data", {})
            error, _warnings = _validate_esearch_payload(data)
            if error is not None:
                return None, self._zero_check_warning(term, error)
            # retmax=0 legitimately pairs a positive count with an empty
            # idlist -- the validator above allows exactly that.
            return int(data["esearchresult"]["count"]), None
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return None, self._zero_check_warning(term, f"{type(exc).__name__}")

    @staticmethod
    def _zero_check_warning(term: str, reason: str) -> str:
        return (
            f"zero-result attribution check for '{term}' failed ({reason}): "
            "total_count 0 is reported from the original query, but it could "
            "not be verified against this term, so do not read it as "
            "'no ClinVar records exist for this input'"
        )

    def _replacement_retry(
        self, retry_params: Dict[str, Any], label: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], List[str]]:
        """Run one replacement retry and validate it through the SAME
        eSearch validator as the first query.

        Fix-R1-20260922: the replacement retries (hyphen-stripped gene,
        alias-resolved gene, condition free-text) exist because a zero on
        the strict query may be an index artifact -- so a retry that itself
        fails (request error or a structurally broken payload) must surface
        as an explicit error instead of silently keeping the original zero:
        reporting that zero would attribute it to biology when the retry
        pipeline is broken. A VALID zero retry still just leaves the
        original (valid) zero in place. Returns ``(data, error,
        query_warnings)``; exactly one of data/error is None.
        """
        retry_result = self._make_request(self.endpoint, retry_params)
        if retry_result.get("status") != "success":
            return (
                None,
                f"{label} retry failed: "
                f"{retry_result.get('error', retry_result.get('status'))}",
                [],
            )
        retry_data = retry_result.get("data", {})
        retry_error, retry_warnings = _validate_esearch_payload(retry_data)
        if retry_error is not None:
            return None, f"{label} retry returned an invalid response: {retry_error}", []
        return retry_data, None, retry_warnings

    def _resolve_deprecated_gene_symbol(
        self, gene: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Look up `gene` in NCBI's own gene database (which tracks
        deprecated/previous symbols as aliases, e.g. "GBA" -> current
        official symbol "GBA1") and return ``(current_symbol, warning)``.

        Fix-R1-20260922: this lookup is auxiliary -- it only runs to explain
        an already-valid zero, so a request/payload failure returns a
        warning (the zero cannot be checked against a renamed symbol) while
        a healthy empty lookup still means "not renamed" and yields
        ``(None, None)``. Never raises.

        Fix-A-20260922: the gene-db eSearch response is validated through
        the SAME ``_validate_esearch_payload`` entry as the ClinVar queries
        (an API error, blank translation, malformed count or non-UID idlist
        entry is a broken response, not a healthy "no alias found"), and
        the validator's non-fatal reminders (errorlist/warninglist) are
        retained labelled with the alias-lookup provenance instead of being
        dropped. The gene esummary hit record must likewise provide a
        non-blank string ``name`` -- a missing/blank/wrong-typed name (or
        a corrupted result object) warns rather than silently reporting
        "no alias", and a numeric name can never reach the caller's
        ``.upper()``."""
        try:
            search_result = self._make_request(
                "/esearch.fcgi",
                {
                    "db": "gene",
                    "term": f"{gene}[sym] AND human[orgn]",
                    "retmode": "json",
                },
            )
            if search_result.get("status") != "success":
                return None, self._gene_alias_warning("gene-database search failed")
            search_data = search_result.get("data", {})
            search_error, search_warnings = _validate_esearch_payload(search_data)
            if search_error is not None:
                return None, self._gene_alias_warning(
                    f"gene-database response was invalid ({search_error})"
                )
            notes = [f"gene-alias lookup reported: {w}" for w in search_warnings]
            ids = search_data["esearchresult"]["idlist"]
            if not ids:
                return None, ("\n".join(notes) if notes else None)
            summary_result = self._make_request(
                "/esummary.fcgi", {"db": "gene", "id": ids[0], "retmode": "json"}
            )
            if summary_result.get("status") != "success":
                return None, self._gene_alias_warning("gene summary fetch failed")
            gene_data = summary_result.get("data", {}).get("result", {})
            entry = gene_data.get(ids[0]) if isinstance(gene_data, dict) else None
            name = entry.get("name") if isinstance(entry, dict) else None
            if not isinstance(name, str) or not name.strip():
                return None, self._gene_alias_warning(
                    "gene summary record lacked a usable symbol name"
                )
            return name, ("\n".join(notes) if notes else None)
        except Exception as exc:
            return None, self._gene_alias_warning(f"{type(exc).__name__} raised")

    @staticmethod
    def _gene_alias_warning(reason: str) -> str:
        return (
            f"gene-alias lookup failed ({reason}): the possibility that the "
            "gene symbol is HGNC-deprecated/renamed could not be checked, so "
            "do not read total_count 0 as 'ClinVar holds no records for "
            "this gene'"
        )


@register_tool("ClinVarGetVariantDetails")
class ClinVarGetVariantDetails(ClinVarRESTTool):
    """Get detailed variant information by ClinVar ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/esummary.fcgi"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get variant details by ClinVar ID."""
        variant_id = arguments.get("variant_id", "")
        if not variant_id:
            return {"status": "error", "error": "variant_id is required"}

        fetch = self._fetch_variant(variant_id)
        if "error_result" in fetch:
            return fetch["error_result"]

        variant_data = fetch["variant_data"]
        variant_summary = fetch["variant_summary"]
        result = fetch["result"]
        result["variant_id"] = variant_id
        # Follow-up 2026-10-23 (Batch C): the optional location containers
        # were already shape-validated in _fetch_variant (absent/null/empty
        # list = optional info not provided), so this first-record selection
        # is safe without a [0] on a possibly-empty list. Selection
        # semantics are unchanged: FIRST variation_set entry, FIRST loc.
        variation_set = variant_data.get("variation_set") or []
        first_variation = variation_set[0] if variation_set else {}
        variation_loc = first_variation.get("variation_loc") or []
        first_loc = variation_loc[0] if variation_loc else {}
        # Fix-R8E-1/R6C-2: assign the formatted payload *over* `result["data"]`
        # (the full, unprocessed esummary envelope from _make_request) instead
        # of publishing it alongside under a second key. Keeping both roughly
        # tripled payload size for no informational gain and made this tool's
        # output nearly indistinguishable from ClinVarGetClinicalSignificance's,
        # which had the identical duplication. Overwriting preserves that
        # de-duplication -- raw access remains at data["raw_data"] -- while
        # delivering the payload under the `data` key the return_schema
        # declares and every other tool in the registry uses.
        # Follow-up 2026-10-14: the summary fields come from the strict
        # parse already performed (and validated) in _fetch_variant.
        result["data"] = {
            "variant_id": variant_id,
            "accession": variant_data.get("accession", ""),
            "obj_type": variant_data.get("obj_type", ""),
            "chromosome": variant_data.get("chr_sort", ""),
            "location": first_loc.get("band", ""),
            "variation_name": first_variation.get("variation_name", ""),
            **variant_summary,
            "raw_data": variant_data,
        }

        # Fix-R3-20260922: submitter citations, obtained by reusing the
        # submitted-records tool's fetch+parse path (one VCV efetch plus
        # one batched PubMed esummary) exactly once -- no second XML or
        # PubMed implementation here. A details (esummary) failure returned
        # above; a citation-fetch failure below keeps the details with
        # empty citations, citations_complete=false and a warning.
        citations = self._submitter_citations(variant_id)
        result["data"]["citations"] = citations["citations"]
        result["data"]["citations_complete"] = citations["citations_complete"]
        if citations["citation_warnings"]:
            result["data"]["citation_warnings"] = citations["citation_warnings"]

        return result

    def _submitter_citations(self, variant_id) -> Dict[str, Any]:
        """Flatten submitter citations via ClinVarSubmittedRecordsTool.

        Fix-R3-20260922: the flattened ``citations`` list keeps PER-SUBMITTER
        attribution -- two submitters citing the same PMID appear as two
        entries (unlike the submitted-records tool's dedup within one
        submission), each carrying its scv_accession and submitter. Any
        failure of the citation fetch degrades to empty citations +
        ``citations_complete=False`` + an explicit warning; it never touches
        the already-retrieved variant details.
        """
        submitted = ClinVarSubmittedRecordsTool(
            {"name": "ClinVar_get_submitted_records"}
        ).run({"variant_id": variant_id})
        if submitted.get("status") != "success":
            return {
                "citations": [],
                "citations_complete": False,
                "citation_warnings": [
                    "Submitter citation fetch failed: "
                    f"{submitted.get('error', 'unknown error')}"
                ],
            }
        data = submitted.get("data", {})
        citations: List[Dict[str, Any]] = []
        for submission in data.get("submissions", []):
            for citation in submission.get("citations", []):
                citations.append(
                    {
                        "pmid": citation.get("pmid"),
                        "title": citation.get("title"),
                        "source_path": citation.get("source_path"),
                        "scv_accession": submission.get("scv_accession"),
                        "submitter": submission.get("submitter"),
                    }
                )
        return {
            "citations": citations,
            "citations_complete": bool(data.get("citations_complete", False)),
            "citation_warnings": list(data.get("citation_warnings", [])),
        }


@register_tool("ClinVarGetClinicalSignificance")
class ClinVarGetClinicalSignificance(ClinVarRESTTool):
    """Get clinical significance information for variants."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/esummary.fcgi"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical significance by variant ID."""
        variant_id = arguments.get("variant_id", "")
        if not variant_id:
            return {"status": "error", "error": "variant_id is required"}

        fetch = self._fetch_variant(variant_id)
        if "error_result" in fetch:
            return fetch["error_result"]

        variant_data = fetch["variant_data"]
        result = fetch["result"]
        result["variant_id"] = variant_id

        # Extract clinical significance information. Follow-up 2026-10-23
        # (Batch C): every container below was shape-validated in
        # _fetch_variant, so null-or-absent degrades to empty output via
        # ``or`` -- a present-but-corrupt value already errored there.
        germline_class = variant_data.get("germline_classification") or {}
        clinical_impact = variant_data.get("clinical_impact_classification") or {}
        oncogenicity = variant_data.get("oncogenicity_classification") or {}
        trait_set = germline_class.get("trait_set") or []

        # Fix-R8E-1/R6C-2: see the matching fix in ClinVarGetVariantDetails --
        # assigning over `result["data"]` (the raw esummary envelope) both
        # de-duplicates the payload and honours the `data` key declared in the
        # return_schema. Raw access remains at data["raw_data"].
        result["data"] = {
            "variant_id": variant_id,
            "germline_classification": {
                "description": germline_class.get("description", ""),
                "review_status": germline_class.get("review_status", ""),
                "last_evaluated": germline_class.get("last_evaluated", ""),
                "fda_recognized": germline_class.get("fda_recognized_database", ""),
                "traits": [
                    trait.get("trait_name", "") for trait in trait_set
                ],
            },
            "clinical_impact": {
                "description": clinical_impact.get("description", ""),
                "review_status": clinical_impact.get("review_status", ""),
                "last_evaluated": clinical_impact.get("last_evaluated", ""),
            },
            "oncogenicity": {
                "description": oncogenicity.get("description", ""),
                "review_status": oncogenicity.get("review_status", ""),
                "last_evaluated": oncogenicity.get("last_evaluated", ""),
            },
            "raw_data": variant_data,
        }

        return result


# How many matching records one call fetches summaries for (500 ids = 3
# esummary requests). Entrez returns ids in Variation-ID order and db=clinvar
# has no sort field, so whatever falls off this cap is arbitrary with respect to
# span -- hence the cap is disclosed rather than silently applied.
_CANDIDATE_CAP = 500

# Bases immediately upstream of the region searched with NO length filter.
# Entrez's VLEN is "the difference between reference and alternate, except when
# there is no length difference (then the length of the allele itself)" (einfo,
# db=clinvar), so a 1 nt insertion recorded between two bases can be VLEN=1 even
# though ClinVar's own start/stop span two. This pad keeps such records out of
# the filtered part of the query, so the filter can never cost a real overlap.
_EDGE_PAD = 10


def _normalize_variant_id(raw):
    """Validate/normalize a ClinVar ``variant_id`` into a numeric UID.

    Fix-D-20260918: an rsID (or any malformed value) pasted into
    ``<N>[uid]`` silently returned count 0 with an empty translation --
    ``rs2151556776[uid]`` finds nothing while the free-text form hits VCV
    2737810. Accepted forms, normalized to the numeric variation ID:

    - a positive integer (JSON number) or its digit-string form (``2737810``)
    - a suffix-free VCV accession (``VCV002737810``)

    Everything else returns an explicit error: rsIDs point at dbSNP, not the
    ClinVar variation-ID index (the message names the free-text form that
    works); versioned VCV accessions, zeros, blanks, booleans and other
    types are rejected before any request is made. Returns
    ``(uid, None)`` or ``(None, error_message)``.
    """
    if isinstance(raw, bool):
        return None, (
            f"variant_id must be a ClinVar variation ID or suffix-free "
            f"VCV accession, got boolean {raw}"
        )
    if isinstance(raw, int):
        number: int = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None, "variant_id is blank: pass a ClinVar variation ID or VCV accession"
        m = re.fullmatch(r"(?i)VCV\.?(\d+)(\.\d+)?", text)
        if m:
            if m.group(2):
                return None, (
                    f"variant_id {text!r} carries a version suffix; use the "
                    "accession without it (e.g. VCV002737810)"
                )
            number = int(m.group(1))
        elif re.fullmatch(r"(?i)rs\d+", text):
            return None, (
                f"variant_id {text!r} is a dbSNP rsID, but the ClinVar "
                "[uid] index only matches numeric variation IDs; search the "
                f'rsID as free text instead: query="{text}"'
            )
        elif text.isdigit():
            number = int(text)
        else:
            return None, (
                f"variant_id must be a positive ClinVar variation ID or a "
                f"suffix-free VCV accession, got {raw!r}"
            )
    else:
        return None, (
            f"variant_id must be a positive integer or VCV accession "
            f"string, got {type(raw).__name__}"
        )
    if number <= 0:
        return None, f"variant_id must be a positive ID, got {number}"
    return number, None


_ESEARCH_COUNT_RE = re.compile(r"\d+")


def _validate_esearch_payload(data):
    """Validate an eSearch payload; return ``(error, query_warnings)``.

    Fix-D-20260918 / Fix-R1-20260922: a missing/malformed ``esearchresult``
    used to pass through as the caller's (fake) success -- ``{"status":
    "success", "data": {}}`` from a broken proxy or a truncated response
    degraded to "query succeeded, zero results". Required structure: an
    ``esearchresult`` object carrying a non-negative integer ``count``
    (bool/negative/float/"--1" are broken payloads, not zero results), a
    list ``idlist`` of UID strings, and a non-blank ``querytranslation``
    string, with no explicit API ``error`` at the top level or inside
    ``esearchresult``. Retainable query warnings -- ``errorlist`` entries
    (a real OR query can report ``phrasesnotfound`` and still return valid
    hits) and ``warninglist`` entries -- are NOT structural faults; they
    are returned separately for the caller to disclose. A count-only
    query (``retmax=0``) legitimately pairs a positive ``count`` with an
    empty ``idlist``, so ``count`` is never checked against the idlist
    length.
    """
    if not isinstance(data, dict):
        return (
            "eSearch response is structurally invalid: 'esearchresult' "
            f"missing from data ({type(data).__name__}) -- this is a "
            "broken response, not an empty result",
            [],
        )
    # An explicit API error is checked BEFORE structure: an error response
    # carries no esearchresult to validate.
    error_value = data.get("error")
    if isinstance(error_value, str) and error_value.strip():
        return (f"eSearch API error: {error_value.strip()}", [])
    if isinstance(error_value, list) and error_value:
        joined = "; ".join(str(entry) for entry in error_value)
        return (f"eSearch API error: {joined}", [])
    if "esearchresult" not in data:
        return (
            "eSearch response is structurally invalid: 'esearchresult' "
            f"missing from data ({type(data).__name__}) -- this is a "
            "broken response, not an empty result",
            [],
        )
    esearch = data["esearchresult"]
    if not isinstance(esearch, dict):
        return (
            "eSearch response is structurally invalid: 'esearchresult' is "
            f"{type(esearch).__name__}, not an object",
            [],
        )
    inner_error = esearch.get("error")
    if isinstance(inner_error, str) and inner_error.strip():
        return (f"eSearch API error: {inner_error.strip()}", [])
    if isinstance(inner_error, list) and inner_error:
        joined = "; ".join(str(entry) for entry in inner_error)
        return (f"eSearch API error: {joined}", [])
    count = esearch.get("count")
    # bool is an int subclass -- reject it explicitly alongside negatives,
    # floats and non-decimal strings ("--1" must not survive a sign-strip).
    if isinstance(count, bool) or not (
        (isinstance(count, int) and count >= 0)
        or (
            isinstance(count, str)
            and _ESEARCH_COUNT_RE.fullmatch(count.strip()) is not None
        )
    ):
        return (
            "eSearch response is structurally invalid: 'count' missing or "
            f"not a non-negative integer ({count!r})",
            [],
        )
    idlist = esearch.get("idlist")
    if not isinstance(idlist, list):
        return (
            "eSearch response is structurally invalid: 'idlist' missing or "
            f"not a list ({type(idlist).__name__})",
            [],
        )
    for uid in idlist:
        if isinstance(uid, bool) or not isinstance(uid, str) or not uid.strip().isdigit():
            return (
                "eSearch response is structurally invalid: 'idlist' "
                f"contains a non-UID entry ({uid!r})",
                [],
            )
    translation = esearch.get("querytranslation")
    if not isinstance(translation, str) or not translation.strip():
        return (
            "eSearch response is structurally invalid: 'querytranslation' "
            "missing, null, or blank -- eSearch always returns one for a "
            "real query",
            [],
        )
    query_warnings = []
    for section in ("errorlist", "warninglist"):
        entries = esearch.get(section)
        if isinstance(entries, dict):
            for key, value in entries.items():
                if isinstance(value, list):
                    query_warnings.extend(f"{key}: {v}" for v in value)
    return None, query_warnings


def _overlap_search_term(chrom, start, end, tag, margin):
    """The Entrez term for records that could overlap [start, end].

    One flat window widened by `margin` matches every record that merely STARTS
    in it -- 15,327 for a 4 Mb window on chr11:47332696, ~97% single-base
    substitutions that stop long before the region. A record starting upstream
    can only reach the region by occupying more than one base, so the upstream
    part of the window carries `NOT 1:1[VLEN]`, which drops the candidate set to
    245 in the same single esearch request.

    Written as a NOT rather than a positive `2:...[VLEN]` range on purpose:
    records with no VLEN indexed at all exist, and this tool's flagship example
    is one -- `1703527[VID] AND 0:1000000000[VLEN]` (the 1.5 Mb copy-number loss
    over chr7:155593770) returns 0 hits. A positive range would drop exactly the
    variant class this tool was built for.
    """
    edge_lo = max(1, int(start) - _EDGE_PAD)
    parts = [f"{chrom}[chr] AND {edge_lo}:{int(end)}[{tag}]"]
    upstream_lo = max(1, int(start) - int(margin))
    upstream_hi = edge_lo - 1
    if upstream_hi >= upstream_lo:
        parts.append(
            f"{chrom}[chr] AND {upstream_lo}:{upstream_hi}[{tag}] NOT 1:1[VLEN]"
        )
    return " OR ".join(f"({p})" for p in parts)


def _coerce_stringified_name_array(raw):
    """Compatibility-parse a stringified JSON array of variant names.

    Some MCP hosts serialize a JSON-array argument into a single string
    before it reaches the server (observed live:
    ``'["NM_001042492.3:c.6642+26C>G", "c.6642+26C>G"]'``). Treated as one
    name, the quote-stripping further down folded it into the malformed
    single term ``"[NM_...c.6642+26C>G, c.6642+26C>G]"[Variant name]``
    that matches nothing.

    Only the exact stringified-array shape is parsed -- the string must
    BOTH start with ``[`` and end with ``]`` AND parse via stdlib
    ``json.loads`` into a list whose elements are all strings. Everything
    else keeps its original meaning: a plain name (even one with legal
    internal HGVS brackets such as ``NM_000518.5(HBB):c.20A>T``) never
    starts with ``[``, so it is never touched. Malformed arrays (e.g.
    ``[A, B]`` without JSON quoting) raise a ValueError instead of being
    comma-split, and non-string or nested-array elements are rejected
    with the offending positions named.

    Returns ``(names_list, {"received_type": ..., "parsed_from": ...})``
    for the search-params disclosure; raises ValueError on malformed or
    non-string content.
    """
    if not isinstance(raw, str):
        # Non-strings (a real list already, or a scalar) keep the existing
        # list-wrapping/coercion path untouched.
        return raw, None
    text = raw.strip()
    # A string that STARTS with '[' can only be an attempted array -- no
    # legitimate ClinVar variant name begins with a bracket -- so attempt
    # the JSON parse and report failure instead of querying a guaranteed-
    # zero malformed name. Plain names and HGVS with INTERNAL brackets
    # never start with '[' and are untouched.
    if not text.startswith("["):
        return raw, None
    try:
        parsed = json.loads(text)
    except ValueError:
        raise ValueError(
            "variant_name looks like a stringified JSON array but is not "
            f"valid JSON: {text!r}. Pass a real JSON array "
            '(["name1", "name2"]) or a single name; comma-splitting is '
            "not guessed."
        )
    if not isinstance(parsed, list):
        # json.loads of a '['-prefixed string can only yield an array or
        # fail, so this is defensive: anything else is not a name list.
        raise ValueError(
            f"variant_name stringified payload is a JSON "
            f"{type(parsed).__name__}, not an array: {text!r}"
        )
    bad = [
        (i, item)
        for i, item in enumerate(parsed)
        if not isinstance(item, str)
    ]
    if bad:
        raise ValueError(
            "variant_name stringified array must contain only strings; "
            "got "
            + ", ".join(f"[{i}]={item!r}" for i, item in bad)
            + f" in {text!r}"
        )
    return parsed, {"received_type": "string", "parsed_from": "stringified_json_array"}


_OVERLAP_NOTE = (
    "Entrez matches a variant's START position, so this searches a window widened "
    "upstream by `margin` and keeps only variants whose span actually overlaps the "
    "region. Single-base records (VLEN=1) are excluded from the upstream part of "
    "that window -- occupying one base, they cannot reach the region from outside "
    "it -- which is what keeps widening `margin` cheap. Sorted smallest span first; "
    "`variants` is capped at `max_results`, `n_overlapping` is how many were found."
)

_OVERLAP_REMEDY = (
    "Narrow the region, or lower `margin`, to bring the match set under "
    f"{_CANDIDATE_CAP}; widening either makes the truncation worse."
)


def _truncation_disclosure(total, inspected, how_to_get_more):
    """The keys that tell a partial scan apart from a complete one.

    A dict fragment the caller merges, like `_condition_filter_disclosure`
    above, so any capped path here can disclose the same way. Field names follow
    the repo-wide convention (`total_available` / `truncated` /
    `truncation_note`; see cbioportal_tool._truncation_fields).
    """
    if total is None:
        return {
            "total_available": None,
            "truncated": True,
            "truncation_note": (
                f"Only the first {inspected} matching records were fetched and "
                "checked for overlap, and Entrez did not report how many matched "
                f"in total, so this may be a partial answer. {how_to_get_more}"
            ),
        }
    if inspected >= total:
        return {"total_available": total, "truncated": False}
    return {
        "total_available": total,
        "truncated": True,
        "truncation_note": (
            f"INCOMPLETE SCAN: {inspected} of {total} matching records "
            f"({100.0 * inspected / total:.1f}%) were fetched and checked for "
            "overlap. Entrez returns records in Variation-ID order and db=clinvar "
            "has no sort field, so the rest are arbitrary with respect to span -- a "
            "short or empty `variants` list is NOT evidence that nothing overlaps "
            f"this region. {how_to_get_more}"
        ),
    }


def _require_http_ok(response, stage: str) -> None:
    """Raise unless the Entrez response reports a healthy HTTP status.

    Follow-up 2026-10-23 (Batch A): the region scan used to call .json()
    directly, so an HTTP error page either raised somewhere deep inside
    parsing or -- worse -- parsed into something the loose readers treated
    as "zero matches", producing a success envelope with n_overlapping=0.
    """
    raise_for_status = getattr(response, "raise_for_status", None)
    if raise_for_status is None:
        return  # test doubles predating this contract
    try:
        raise_for_status()
    except Exception as exc:  # requests.HTTPError and lookalikes
        raise ValueError(f"{stage} request failed: {exc}") from exc


def _parse_span_int(value, uid: str, field: str) -> int:
    """Parse one variation_loc coordinate; accept only parseable integers.

    Follow-up 2026-10-23 (Batch A): the old bare ``int(...)`` accepted
    booleans (bool is an int subclass -> True became start=1) and silently
    truncated floats; both are now explicit errors. Integral strings are
    accepted -- esummary legitimately serializes coordinates as strings --
    but non-numeric strings, None, bools and floats are rejected.
    """
    if isinstance(value, bool):
        raise ValueError(
            f"eSummary stage: uid {uid} has a boolean {field} coordinate "
            f"({value!r})"
        )
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"[+-]?\d+", text):
            return int(text)
    raise ValueError(
        f"eSummary stage: uid {uid} has a non-integer {field} "
        f"coordinate ({value!r})"
    )


def clinvar_variants_overlapping(
    session,
    chrom,
    start,
    end,
    assembly="GRCh37",
    margin=2_000_000,
    significance=None,
    max_results=50,
    timeout=60,
):
    """ClinVar variants whose span OVERLAPS a region.

    Entrez `chrpos37`/`chrpos38` match a variant's START position, so a narrow
    window finds nothing that begins upstream of it -- and a pathogenic CNV can
    begin megabases away while still covering the region asked about. Searching
    an 11 bp window for chr7:155593770-155593780 returns 0 hits even though a
    1.5 Mb copy-number loss (Variation 1703527, chr7:154831466-156356088)
    covers it.

    So: search a window widened by `margin` (`_overlap_search_term` builds the
    query), then keep only records whose [start, stop] genuinely overlaps.

    Only the first `_CANDIDATE_CAP` matching records are inspected, so the
    envelope reports `total_available` beside `n_candidates` and flags any
    shortfall: a caller concluding "no pathogenic deletion overlaps this locus"
    needs to know when that rests on a partial scan.
    """
    tag = "chrpos38" if str(assembly).upper() in ("GRCH38", "HG38") else "chrpos37"
    term = _overlap_search_term(chrom, start, end, tag, margin)
    if significance:
        # [clinsig] is not a ClinVar eSearch field -- Entrez silently degraded
        # it to [All Fields] (confirmed live: chr17 BRCA1 window, 15508 hits
        # unfiltered vs 13782 with '"Pathogenic"[clinsig]', i.e. a free-text
        # match that also keeps "Likely pathogenic" and "Conflicting
        # classifications of pathogenicity" records). Use the same verified
        # [Filter]/[prop] clause the gene search uses. Values are validated by
        # the caller against _CLINSIG_ACCEPTED.
        components = (
            significance
            if isinstance(significance, list)
            else _normalize_clinsig(significance)
        )
        clause = _clinsig_query_clause(components)
        if clause:
            term = f"({term}) AND {clause}"

    # Follow-up 2026-10-23 (Batch A): an incomplete scan is a WHOLE-CALL
    # error, never a healthy-looking negative. Every request checks its
    # HTTP status; the eSearch JSON is validated by the shared
    # _validate_esearch_payload; and because the region query pins a
    # POSITIVE retmax, `count` is additionally checked against the idlist
    # (count>0 with no ids, or count<len(idlist), are broken payloads
    # here -- count>len(idlist) is legitimate truncation). Every returned
    # UID must yield a usable detail record, and that record must carry at
    # least one parseable current-assembly coordinate pair; a record
    # visibly on another assembly is skipped WITHOUT its coordinates being
    # touched. Damage raises ValueError with the stage/UID/field path,
    # which ClinVarSearchByRegion.run turns into status:"error".
    es_response = session.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={
            "db": "clinvar",
            "term": term,
            "retmax": _CANDIDATE_CAP,
            "retmode": "json",
        },
        timeout=timeout,
    )
    _require_http_ok(es_response, "eSearch")
    es = es_response.json()
    esearch_error, _query_warnings = _validate_esearch_payload(es)
    if esearch_error:
        raise ValueError(f"eSearch stage: {esearch_error}")
    esearchresult = es["esearchresult"]
    ids = esearchresult["idlist"]
    # esearch reports the size of the whole match set in `count` whatever retmax
    # is, so the honest denominator costs no extra request.
    try:
        total_available = int(esearchresult.get("count"))
    except (TypeError, ValueError):
        total_available = None
    # Region queries pin a positive retmax, so the count/idlist pairing
    # can be checked here (the shared validator cannot: a retmax=0
    # count-only query legitimately pairs count>0 with an empty idlist).
    if total_available is not None:
        if total_available > 0 and not ids:
            raise ValueError(
                "eSearch stage: esearchresult reports count="
                f"{total_available} but an empty idlist under a positive "
                "retmax -- a broken response, not an empty result"
            )
        if 0 < total_available < len(ids):
            raise ValueError(
                "eSearch stage: esearchresult reports count="
                f"{total_available}, smaller than the {len(ids)} ids "
                "returned -- a broken payload, not a truncated page"
            )

    out = []
    for chunk_start in range(0, len(ids), 200):
        chunk = ids[chunk_start : chunk_start + 200]
        summ_response = session.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "clinvar", "id": ",".join(chunk), "retmode": "json"},
            timeout=timeout,
        )
        _require_http_ok(
            summ_response, f"eSummary (uids {chunk[0]}..{chunk[-1]})"
        )
        summ = summ_response.json().get("result")
        if not isinstance(summ, dict):
            raise ValueError(
                "eSummary stage: response is missing the 'result' object "
                f"(got {type(summ).__name__}) for uids {chunk[0]}.."
                f"{chunk[-1]} -- a broken response, not an empty overlap set"
            )
        for vid in chunk:
            rec = summ.get(vid)
            if not isinstance(rec, dict) or not rec:
                raise ValueError(
                    f"eSummary stage: uid {vid} has no detail record in "
                    "the esummary response -- the scan cannot decide "
                    "overlap for it, so no complete-negative claim is made"
                )
            if rec.get("error"):
                raise ValueError(
                    f"eSummary stage: uid {vid} returned an API error: "
                    f"{rec['error']}"
                )
            matched = False
            current_assembly_loc = False
            for vset in rec.get("variation_set") or []:
                if not isinstance(vset, dict):
                    raise ValueError(
                        f"eSummary stage: uid {vid} has a non-object "
                        "variation_set entry"
                    )
                for loc in vset.get("variation_loc") or []:
                    if not isinstance(loc, dict):
                        raise ValueError(
                            f"eSummary stage: uid {vid} has a non-object "
                            "variation_loc entry"
                        )
                    if (
                        str(loc.get("assembly_name", "")).upper()
                        != str(assembly).upper()
                    ):
                        continue
                    current_assembly_loc = True
                    v_start = _parse_span_int(loc.get("start"), vid, "start")
                    v_stop = _parse_span_int(loc.get("stop"), vid, "stop")
                    if v_stop < v_start:
                        raise ValueError(
                            f"eSummary stage: uid {vid} has an inverted "
                            f"interval start={v_start} > stop={v_stop}"
                        )
                    matched = True
                    if v_start <= int(end) and v_stop >= int(start):
                        out.append(
                            {
                                "variation_id": vid,
                                "title": rec.get("title"),
                                "obj_type": rec.get("obj_type"),
                                "chr": loc.get("chr"),
                                "start": v_start,
                                "stop": v_stop,
                                "span": v_stop - v_start + 1,
                                "classification": (
                                    rec.get("germline_classification") or {}
                                ).get("description"),
                            }
                        )
                    break
                if matched:
                    break
            if not current_assembly_loc:
                raise ValueError(
                    f"eSummary stage: uid {vid} exposes no "
                    f"{assembly} variation_loc, so its overlap with the "
                    "region cannot be decided -- no complete-negative "
                    "claim is made"
                )
    # Smallest span first: the most specific variant covering the region.
    out.sort(key=lambda v: v["span"])
    return {
        "term": term,
        **_truncation_disclosure(total_available, len(ids), _OVERLAP_REMEDY),
        "n_candidates": len(ids),
        "n_overlapping": len(out),
        "variants": out[:max_results],
        "note": _OVERLAP_NOTE,
    }


@register_tool("ClinVarSearchByRegion")
class ClinVarSearchByRegion(ClinVarRESTTool):
    """ClinVar variants overlapping a genomic region, including spanning CNVs."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        chrom = (
            str(arguments.get("chrom") or arguments.get("chromosome") or "")
            .replace("chr", "")
            .strip()
        )
        start, end = arguments.get("start"), arguments.get("end")
        region = arguments.get("region")
        if region and (start is None or end is None):
            m = re.match(
                r"^\s*chr?([\w]+)\s*[:\s]\s*([\d,]+)\s*[-.]+\s*([\d,]+)", str(region)
            )
            if m:
                chrom = chrom or m.group(1)
                start, end = (
                    int(m.group(2).replace(",", "")),
                    int(m.group(3).replace(",", "")),
                )
        if not chrom or start is None or end is None:
            return {
                "status": "error",
                "error": "Provide chrom/start/end, or region like 'chr7:155593770-155593780'.",
            }
        # Same input validation as ClinVar_search_variants: an unrecognized
        # class must not reach the query, where it would silently filter the
        # region's variants down to nothing under a `status: success`.
        clnsig_param = (
            "clinical_significance"
            if arguments.get("clinical_significance")
            else "significance"
        )
        raw_clnsig = arguments.get("clinical_significance") or arguments.get(
            "significance"
        )
        clnsig_components = []
        if str(raw_clnsig or "").strip():
            clnsig_components = _normalize_clinsig(raw_clnsig)
            invalid_clnsig = [
                c for c in clnsig_components if c not in _CLINSIG_ACCEPTED_NORMALIZED
            ]
            if invalid_clnsig:
                return _invalid_clinsig_error(clnsig_param, raw_clnsig, invalid_clnsig)
        try:
            result = clinvar_variants_overlapping(
                self.session,
                chrom,
                int(start),
                int(end),
                assembly=arguments.get("assembly", "GRCh37"),
                margin=int(arguments.get("margin", 2_000_000)),
                significance=clnsig_components or None,
                max_results=int(arguments.get("max_results", 50)),
                timeout=self.timeout,
            )
        except Exception as e:
            return {
                "status": "error",
                "error": f"ClinVar region search failed: {str(e)[:200]}",
            }
        return {"status": "success", "data": result}
