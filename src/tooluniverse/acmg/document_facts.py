"""Verify structured literature facts against ToolUniverse full text."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from .identity import normalize_hgvs_token, protein_change


PROPOSAL_REANCHOR_POLICY_VERSION = "2026-09-03-v1"

_FACT_REQUIREMENTS = {
    "case_control": {
        "case_count",
        "control_count",
        "odds_ratio",
        "ci_lower",
    },
    "case_series": {
        "case_count",
        "cases_independent",
        "phenotype_consistency",
    },
    "de_novo": {
        "case_id",
        "parental_relationships",
        "phenotype_consistency",
        "inheritance_mode",
    },
    "pm3": {
        "case_id",
        "zygosity",
        "phase",
        "other_variant_classification",
        "other_variant_frequency_eligible",
    },
    "recessive_allelic": {
        "case_id",
        "zygosity",
        "phase",
        "other_variant_classification",
        "other_variant_frequency_eligible",
    },
    "mechanism": {
        "gene_disease_mechanism",
    },
    "functional": {
        "gene_disease_mechanism",
        "assay_scope",
        "assay_effect_consistent",
        "assay_class",
        "assay_instance_id",
        "model_system",
        "disease_relevance",
        "readout_name",
        "readout_unit",
        "normal_threshold",
        "abnormal_threshold",
        "variant_result",
        "positive_experimental_controls",
        "negative_experimental_controls",
        "technical_replicates",
        "biological_replicates",
        "pathogenic_validation_controls",
        "benign_validation_controls",
        "validation_control_provenance",
        "dynamic_range",
        "calibration_method",
        "reported_odds_path",
        "direction",
    },
    "segregation": {
        "family_id",
        "segregation_direction",
        "informative_meioses",
        "phenotype_consistency",
    },
    "phenotype_specificity": {
        "disease",
        "inheritance_mode",
        "phenotype_specificity",
    },
    "healthy_observation": {
        "cohort_id",
        "unaffected_count",
        "age_appropriate",
        "penetrance_context",
    },
    "allelic_phase": {
        "case_id",
        "phase",
        "other_variant_classification",
    },
    "alternative_cause": {
        "case_id",
        "alternative_cause_established",
    },
    "prior_variant": {
        "prior_variant_identity",
        "amino_acid_relation",
        "independent_pathogenic_evidence",
    },
    "region_hotspot": {
        "protein_region",
        "pathogenic_enrichment",
        "benign_variation_depleted",
    },
    "protein_length_repeat": {
        "effect_type",
        "repeat_context",
    },
    "rna_splicing": {
        "assay_instance_id",
        "splice_effect",
        "assay_quality",
    },
}


LITERATURE_FACT_CRITERIA: dict[str, tuple[str, ...]] = {
    "case_control": ("PS4",),
    "case_series": ("PS4",),
    "de_novo": ("PS2", "PM6"),
    "pm3": ("PM3",),
    "recessive_allelic": ("PM3",),
    "functional": ("PS3", "BS3"),
    "segregation": ("PP1", "BS4"),
    "phenotype_specificity": ("PP4",),
    "healthy_observation": ("BS2",),
    "allelic_phase": ("PM3", "BP2"),
    "alternative_cause": ("BP5",),
    "prior_variant": ("PS1", "PM5"),
    "mechanism": ("PVS1", "PP2", "BP1"),
    "region_hotspot": ("PM1",),
    "protein_length_repeat": ("PM4", "BP3"),
    "rna_splicing": (),
}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _contains(text: str, excerpt: Any) -> bool:
    return bool(_norm(excerpt)) and _norm(excerpt) in _norm(text)


def _same(value: Any, expected: str) -> bool:
    if not expected:
        return True
    if isinstance(value, (list, tuple, set)):
        return any(_same(item, expected) for item in value)
    return _norm(value) == _norm(expected)


def _protein_alias_in_text(text: str, expected_protein: str) -> bool:
    expected = protein_change(expected_protein)
    if not expected[0] or expected[1] is None or not expected[2]:
        return False
    return any(
        protein_change(match.group(0)) == expected
        for match in re.finditer(
            r"(?<![A-Za-z0-9])(?:p\.\s*)?\(?[A-Za-z]{1,3}\s*\d+\s*"
            r"[A-Za-z*]{1,3}\)?(?![A-Za-z0-9])",
            str(text or ""),
            re.IGNORECASE,
        )
    )


def _variant_binding_status(
    item: dict[str, Any],
    *,
    expected_variant: str,
    expected_variant_aliases: tuple[str, ...],
    expected_protein: str,
    expected_gene: str,
) -> tuple[str, str]:
    values = item.get("values") if isinstance(item.get("values"), dict) else {}
    submitted = [item.get("variant_identity"), values.get("variant_identity")]
    submitted = [str(value).strip() for value in submitted if str(value or "").strip()]
    submitted_gene = str(item.get("gene") or values.get("gene") or "").strip()
    if submitted_gene and expected_gene and _norm(submitted_gene) != _norm(expected_gene):
        return "mismatch", "submitted_gene_differs_from_assessed_gene"

    exact = normalize_hgvs_token(expected_variant).casefold()
    aliases = {
        normalized.casefold()
        for value in expected_variant_aliases
        if (normalized := normalize_hgvs_token(value))
    }
    if exact:
        aliases.add(exact)
    saw_hgvs = False
    for value in submitted:
        normalized = normalize_hgvs_token(value).casefold()
        observed_protein = protein_change(value)
        if not normalized:
            if (
                observed_protein == protein_change(expected_protein)
                and observed_protein[1] is not None
            ):
                return (
                    "equivocal",
                    "protein_change_matches_without_genomic_allele_confirmation",
                )
            continue
        saw_hgvs = True
        if normalized == exact:
            return "exact", "submitted_c_or_g_hgvs_matches_assessed_variant"
        if normalized in aliases:
            return "equivalent", "submitted_hgvs_matches_verified_alias"
        if (
            observed_protein == protein_change(expected_protein)
            and observed_protein[1] is not None
        ):
            return "equivocal", "protein_change_matches_without_genomic_allele_confirmation"
    if saw_hgvs:
        return "mismatch", "submitted_hgvs_differs_from_assessed_variant"
    return "unknown", "submitted_variant_could_not_be_compared"


def _target_link_status(
    excerpt: str,
    *,
    fact_type: str,
    expected_variant: str,
    expected_variant_aliases: tuple[str, ...] = (),
    expected_protein: str = "",
    expected_gene: str,
) -> str:
    """Classify only links visible in the submitted, re-anchored excerpt."""
    compact_excerpt = re.sub(r"\s+", "", str(excerpt or "")).casefold()
    exact = normalize_hgvs_token(expected_variant).casefold()
    if exact and exact in compact_excerpt:
        return "direct_variant"
    if any(
        (alias := normalize_hgvs_token(value).casefold()) and alias in compact_excerpt
        for value in expected_variant_aliases
    ):
        return "equivalent_variant"
    if _protein_alias_in_text(excerpt, expected_protein):
        return "protein_alias"
    if fact_type in {"mechanism", "region_hotspot", "protein_length_repeat"}:
        if expected_gene and re.search(
            rf"(?<![A-Za-z0-9_-]){re.escape(expected_gene)}(?![A-Za-z0-9_-])",
            excerpt,
            re.IGNORECASE,
        ):
            return "direct_gene"
    return "unlinked"


def _negation_status(excerpt: str) -> str:
    """Conservatively flag explicit negation in an evidence-bearing excerpt."""
    if re.search(
        r"\b(?:no|not|without|neither|nor|failed\s+to)\b",
        excerpt,
        re.IGNORECASE,
    ):
        return "negated"
    return "not_negated"


def _payload(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    data = result.get("data")
    return data if isinstance(data, dict) else result


def retrieved_document_status(
    result: Any, provenance: dict[str, Any] | None = None
) -> str:
    """Classify the document content actually returned by a provider."""
    data = _payload(result)
    provenance = provenance or {}

    def has_body(value: Any) -> bool:
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, list):
            return any(has_body(item) for item in value)
        if isinstance(value, dict):
            return any(
                has_body(item)
                for key, item in value.items()
                if key not in {"title", "id", "label", "url", "href"}
            )
        return False

    has_full_text = any(
        has_body(data.get(key)) for key in ("sections", "text", "content")
    )
    passages = [row for row in data.get("passages") or [] if isinstance(row, dict)]
    if any(
        str((row.get("infons") or {}).get("type") or "").casefold()
        not in {"", "title", "abstract", "front"}
        and str(row.get("text") or "").strip()
        for row in passages
    ):
        has_full_text = True
    if has_full_text:
        return "partial" if provenance.get("truncated") else "complete"
    if any(has_body(data.get(key)) for key in ("tables", "figures")):
        return "partial"
    if data.get("abstract") not in (None, "", [], {}):
        return "abstract_only"
    if data.get("snippet") not in (None, "", [], {}) or data.get(
        "snippets"
    ) not in (None, "", [], {}):
        return "snippet_only"
    return "unavailable"


def _document_identity_matches(
    result: Any,
    *,
    pmid: str,
    pmcid: str,
) -> bool:
    data = _payload(result)
    metadata = result.get("metadata") if isinstance(result, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    returned_pmid = str(
        data.get("pmid") or data.get("PMID") or metadata.get("pmid") or ""
    ).strip()
    returned_pmcid = str(
        data.get("pmcid") or data.get("PMCID") or metadata.get("pmcid") or ""
    ).strip()
    returned_pmid = returned_pmid or str(data.get("id") or data.get("_id") or "")
    if pmid and returned_pmid and pmid != returned_pmid:
        return False
    if pmcid and returned_pmcid and pmcid.casefold() != returned_pmcid.casefold():
        return False
    return bool(
        (pmid and returned_pmid == pmid)
        or (pmcid and returned_pmcid.casefold() == pmcid.casefold())
    )


def document_text_for_locator(result: Any, locator: str) -> str:
    """Return the exact section, table, or figure text named by a locator."""
    data = _payload(result)
    key = _norm(locator)
    if not key:
        return ""
    if key in {"abstract", "summary"}:
        abstract = data.get("abstract")
        if isinstance(abstract, str) and abstract.strip():
            return abstract
    if key in {"snippet", "search snippet"}:
        snippet = data.get("snippet")
        if isinstance(snippet, str) and snippet.strip():
            return snippet
    for passage in data.get("passages") or []:
        if not isinstance(passage, dict):
            continue
        passage_key = f"passage:{passage.get('offset', '')}"
        passage_type = str((passage.get("infons") or {}).get("type") or "")
        if key in {_norm(passage_key), _norm(passage_type)}:
            return str(passage.get("text") or "")
    for row in data.get("snippets") or []:
        if not isinstance(row, dict):
            continue
        if key in {_norm(row.get("term")), "snippet", "search snippet"}:
            return str(row.get("snippet") or "")
    unstructured_text = data.get("text") or data.get("content")
    if isinstance(unstructured_text, str) and unstructured_text.strip():
        # Plain-text/HTML fallbacks cannot expose stable section nodes.  The
        # submitted locator remains auditable, while the excerpt is re-anchored
        # against the complete normalized document text below.
        return unstructured_text
    for container_name in ("sections", "tables", "figures"):
        container = data.get(container_name)
        if isinstance(container, dict):
            for name, value in container.items():
                if _norm(name) == key:
                    if isinstance(value, str):
                        return value
                    if isinstance(value, dict):
                        return " ".join(
                            str(item)
                            for item in value.values()
                            if isinstance(item, (str, int, float))
                        )
        elif isinstance(container, list):
            for row in container:
                if not isinstance(row, dict):
                    continue
                name = row.get("id") or row.get("label") or row.get("title")
                if _norm(name) == key:
                    return str(row.get("text") or row.get("caption") or "")
                for nested in row.get("rows") or []:
                    if isinstance(nested, dict) and _norm(nested.get("locator")) == key:
                        return str(nested.get("text") or "")
    return ""


def document_content_hash(result: Any) -> str:
    """Hash normalized document content independently of the retrieval route."""
    data = _payload(result)
    content = {
        key: data.get(key)
        for key in (
            "title",
            "abstract",
            "sections",
            "tables",
            "figures",
            "text",
            "content",
            "passages",
            "snippets",
        )
        if data.get(key) not in (None, "", [], {})
    }
    if not content:
        return ""
    normalized = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    normalized = " ".join(normalized.split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _finite_positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )


def _semantic_errors(fact_type: str, values: dict[str, Any]) -> list[str]:
    required = _FACT_REQUIREMENTS.get(fact_type)
    if required is None:
        return ["unsupported_fact_type"]
    errors = [
        f"missing_value:{key}"
        for key in sorted(required)
        if values.get(key) in (None, "", [])
    ]
    if fact_type == "functional":
        if _norm(values.get("assay_scope")) not in {
            "protein_or_cell_function",
            "direct_rna_splicing",
        }:
            errors.append("invalid_assay_scope")
        for key in (
            "assay_effect_consistent",
            "disease_relevance",
        ):
            if values.get(key) is not True:
                errors.append(f"invalid_true_boolean:{key}")
        for key in (
            "technical_replicates",
            "biological_replicates",
            "pathogenic_validation_controls",
            "benign_validation_controls",
        ):
            if not _positive_int(values.get(key)):
                errors.append(f"invalid_positive_integer:{key}")
        if not _finite_positive(values.get("dynamic_range")):
            errors.append("invalid_dynamic_range")
        if values.get("calibration_method") != "reported_odds_path":
            errors.append("invalid_calibration_method")
        if not _finite_positive(values.get("reported_odds_path")):
            errors.append("invalid_reported_odds_path")
        if _norm(values.get("direction")) not in {"damaging", "normal"}:
            errors.append("invalid_direction")
    if fact_type in {"functional", "mechanism"}:
        mechanism = _semantic_text(values.get("gene_disease_mechanism"))
        if mechanism not in {
            "loss of function",
            "lof",
            "haploinsufficiency",
            "gain of function",
            "dominant negative",
            "missense",
            "missense constrained",
            "unknown",
        }:
            errors.append("invalid_gene_disease_mechanism")
    return errors


_ENUM_GROUPS = (
    {"confirmed", "assumed"},
    {
        "highly specific",
        "consistent",
        "consistent high heterogeneity",
        "not consistent",
    },
    {"compound heterozygous", "homozygous"},
    {"confirmed in trans", "unknown"},
    {
        "pathogenic",
        "likely pathogenic",
        "vus",
        "uncertain significance",
    },
    {"damaging", "normal"},
    {"segregates", "does not segregate"},
    {"same amino acid change", "same residue different change"},
    {"loss of function", "gain of function", "dominant negative", "unknown"},
    {"length change outside repeat", "inframe change in repeat"},
)


def _semantic_text(value: Any) -> str:
    return " ".join(
        str(value or "").casefold().replace("_", " ").replace("-", " ").split()
    )


def _numbers(text: str) -> list[float]:
    values: list[float] = []
    for token in re.findall(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?", text):
        try:
            values.append(float(token.replace(",", "")))
        except ValueError:
            continue
    return values


def _field_semantic_status(value: Any, excerpt: str) -> str:
    """Return verified/unresolved/contradicted for one value/excerpt pair."""
    if isinstance(value, bool):
        normalized = _semantic_text(excerpt)
        expected = "true" if value else "false"
        opposite = "false" if value else "true"
        if expected in normalized:
            return "verified"
        return "contradicted" if opposite in normalized else "unresolved"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        observed = _numbers(excerpt)
        if not observed:
            return "unresolved"
        expected = float(value)
        return (
            "verified"
            if any(
                math.isclose(expected, item, rel_tol=1e-9, abs_tol=1e-12)
                for item in observed
            )
            else "contradicted"
        )
    if isinstance(value, str):
        expected = _semantic_text(value)
        observed = _semantic_text(excerpt)
        if expected and expected in observed:
            return "verified"
        for group in _ENUM_GROUPS:
            if expected not in group:
                continue
            if any(option in observed for option in group - {expected}):
                return "contradicted"
            return "unresolved"
    return "unresolved"


def stable_document_fact_id(
    *,
    fact_type: str,
    pmid: str,
    pmcid: str,
    locator: str,
    variant: str,
    gene: str,
    values: dict[str, Any],
) -> str:
    semantic_identity = {
        key: values.get(key)
        for key in (
            "case_id",
            "assay_instance_id",
            "cohort_id",
            "family_id",
        )
        if values.get(key) not in (None, "")
    }
    payload = {
        "fact_type": fact_type,
        "pmid": pmid,
        "pmcid": pmcid,
        "locator": locator,
        "variant": variant,
        "gene": gene,
        "semantic_identity": semantic_identity,
        "values": values,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"document-fact:v1:{hashlib.sha256(encoded.encode()).hexdigest()[:24]}"


def verify_document_fact(
    item: dict[str, Any],
    document_result: Any,
    *,
    expected_variant: str,
    expected_variant_aliases: tuple[str, ...] = (),
    expected_protein: str = "",
    expected_gene: str,
    expected_disease: str = "",
    expected_inheritance: str = "",
) -> dict[str, Any]:
    """Return a machine-computed verification record; caller trust flags are ignored."""
    pmid = str(item.get("pmid") or "").strip()
    pmcid = str(item.get("pmcid") or "").strip()
    locator = str(item.get("locator") or "").strip()
    excerpt = str(item.get("excerpt") or "").strip()
    fact_type = str(item.get("fact_type") or "").strip().lower()
    values = item.get("values") if isinstance(item.get("values"), dict) else {}
    field_excerpts = (
        item.get("field_excerpts")
        if isinstance(item.get("field_excerpts"), dict)
        else {}
    )
    extractor = item.get("extractor") if isinstance(item.get("extractor"), dict) else {}
    document_status = retrieved_document_status(document_result)
    document_available = document_status != "unavailable"
    text = (
        document_text_for_locator(document_result, locator)
        if document_available
        else ""
    )
    semantic_errors = _semantic_errors(fact_type, values)
    requirements_status = "complete" if not semantic_errors else "incomplete"
    target_link_status = _target_link_status(
        excerpt,
        fact_type=fact_type,
        expected_variant=expected_variant,
        expected_variant_aliases=expected_variant_aliases,
        expected_protein=expected_protein,
        expected_gene=expected_gene,
    )
    identity_binding_status, identity_binding_basis = _variant_binding_status(
        item,
        expected_variant=expected_variant,
        expected_variant_aliases=expected_variant_aliases,
        expected_protein=expected_protein,
        expected_gene=expected_gene,
    )
    negation_status = _negation_status(excerpt)
    anchor_errors: list[str] = []
    if document_available:
        if not _document_identity_matches(document_result, pmid=pmid, pmcid=pmcid):
            anchor_errors.append("document_identity_mismatch")
        if not locator or not text:
            anchor_errors.append("reanchor_failed_locator_not_found")
        if not excerpt or not _contains(text, excerpt):
            anchor_errors.append("reanchor_failed_excerpt_not_found")
    if identity_binding_status == "mismatch":
        anchor_errors.append("identity_mismatch")
    supplied_disease = values.get("disease") or item.get("disease")
    if (
        expected_disease
        and supplied_disease
        and not _same(supplied_disease, expected_disease)
    ):
        anchor_errors.append("disease_identity_mismatch")
    supplied_inheritance = (
        values.get("inheritance")
        or values.get("inheritance_mode")
        or item.get("inheritance")
    )
    if (
        expected_inheritance
        and supplied_inheritance
        and not _same(supplied_inheritance, expected_inheritance)
    ):
        anchor_errors.append("inheritance_mismatch")
    if not extractor.get("name") or not extractor.get("version"):
        semantic_errors.append("extractor_version_missing")
    consumed_fields = set(values) - {
        "variant_identity",
        "gene",
        "disease",
        "inheritance",
        "inheritance_mode",
    }
    field_semantics: dict[str, str] = {}
    for key in sorted(consumed_fields):
        field_excerpt = field_excerpts.get(key)
        if not isinstance(field_excerpt, str):
            semantic_errors.append(f"field_excerpt_missing:{key}")
            continue
        if document_available and not _contains(text, field_excerpt):
            anchor_errors.append(f"reanchor_failed_field_excerpt_not_found:{key}")
            continue
        field_semantics[key] = _field_semantic_status(values.get(key), field_excerpt)
    anchor_errors = list(dict.fromkeys(anchor_errors))
    semantic_errors = list(dict.fromkeys(semantic_errors))
    requirements_status = "complete" if not semantic_errors else "incomplete"
    if any(value == "contradicted" for value in field_semantics.values()):
        semantic_status = "contradicted"
    elif semantic_errors:
        semantic_status = "unresolved"
    elif field_semantics and all(
        value == "verified" for value in field_semantics.values()
    ):
        semantic_status = "verified"
    else:
        semantic_status = "unresolved"
    submitted_document_hash = str(item.get("document_hash") or "").strip().casefold()
    retrieved_document_hash = (
        document_content_hash(document_result) if document_available else ""
    )
    external_anchor_complete = bool(
        re.fullmatch(r"[0-9a-f]{64}", submitted_document_hash)
        and excerpt
        and locator
        and (pmid or pmcid)
        and extractor.get("name")
        and extractor.get("version")
    )
    if (
        document_available
        and submitted_document_hash
        and submitted_document_hash != retrieved_document_hash
    ):
        anchor_errors.append("reanchor_failed_document_hash_mismatch")
    anchor_errors = list(dict.fromkeys(anchor_errors))
    if identity_binding_status == "mismatch":
        reanchor_status = "rejected"
        anchor_status = "mismatch"
    elif document_available and not anchor_errors:
        reanchor_status = "verified"
        anchor_status = "verified"
    elif document_available:
        reanchor_status = "reanchor_failed"
        anchor_status = "reanchor_failed"
    elif external_anchor_complete and semantic_status != "contradicted":
        reanchor_status = "externally_anchored"
        anchor_status = "externally_anchored"
    else:
        reanchor_status = "document_unreachable"
        anchor_status = "unavailable"
        anchor_errors.append("document_unreachable")
    errors = [
        *anchor_errors,
        *semantic_errors,
        *[
            f"field_value_contradicted:{key}"
            for key, status in field_semantics.items()
            if status == "contradicted"
        ],
    ]
    fact_id = stable_document_fact_id(
        fact_type=fact_type,
        pmid=pmid,
        pmcid=pmcid,
        locator=locator,
        variant=expected_variant,
        gene=expected_gene,
        values=values,
    )
    return {
        "verified": reanchor_status == "verified" and semantic_status != "contradicted",
        "verification_level": (
            "machine_document_anchored"
            if anchor_status == "verified" and semantic_status != "contradicted"
            else "externally_anchored_unverified"
            if reanchor_status == "externally_anchored"
            else "unverified"
        ),
        "validation_errors": errors,
        "anchor_status": anchor_status,
        "reanchor_status": reanchor_status,
        "reanchor_failure_code": next(
            (
                error
                for error in anchor_errors
                if error.startswith("reanchor_failed")
                or error
                in {
                    "document_unreachable",
                    "document_identity_mismatch",
                    "identity_mismatch",
                }
            ),
            "document_unreachable"
            if reanchor_status in {"externally_anchored", "document_unreachable"}
            else "",
        ),
        "identity_binding_status": identity_binding_status,
        "identity_binding_basis": identity_binding_basis,
        "submitted_document_hash": submitted_document_hash,
        "retrieved_document_hash": retrieved_document_hash,
        "semantic_status": semantic_status,
        "requirements_status": requirements_status,
        "missing_requirements": semantic_errors,
        "target_link_status": target_link_status,
        "negation_status": negation_status,
        "field_semantics": field_semantics,
        "fact_id": fact_id,
        "submitted_fact_id": str(item.get("fact_id") or ""),
        "fact_type": fact_type,
        "pmid": pmid,
        "pmcid": pmcid,
        "locator": locator,
        "excerpt": excerpt,
        "values": dict(values),
        "field_excerpts": dict(field_excerpts),
        "extractor": dict(extractor),
        "criterion": str(item.get("criterion") or ""),
        "suggested_strength": str(item.get("suggested_strength") or ""),
        "interpretation": str(item.get("interpretation") or ""),
        "confidence": item.get("confidence"),
        "questions": list(item.get("questions") or [])
        if isinstance(item.get("questions"), list)
        else [],
    }


__all__ = [
    "LITERATURE_FACT_CRITERIA",
    "PROPOSAL_REANCHOR_POLICY_VERSION",
    "document_content_hash",
    "document_text_for_locator",
    "retrieved_document_status",
    "stable_document_fact_id",
    "verify_document_fact",
]
