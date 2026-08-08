"""Single-path ACMG evidence collection runtime.

The collector gathers raw ToolUniverse source data, normalizes reviewable
features, applies the five deterministic evidence groups, and returns evidence
for review. It never produces a five-tier ACMG classification.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from collections.abc import Callable
from typing import Any

from .clinical import clinical_evidence
from .compatibility import resolve_evidence_compatibility
from .computational import computational_evidence
from .consequence import build_consequence_profile, consequence_applicability
from .consequence_sources import (
    CONSEQUENCE_METHODS,
    consequence_observations,
    profile_features_from_resolution,
    resolve_consequence_observations,
)
from .cspec import build_dynamic_cspec_contract
from .document_facts import (
    LITERATURE_FACT_CRITERIA,
    document_content_hash,
    verify_document_fact,
)
from .models import (
    EvidenceCard,
    SourceFact,
    evidence_cards_to_result,
    is_source_backed_candidate,
)
from .functional import functional_evidence
from .guard import GUARD_CONTEXT_SCHEMA_VERSION, guard_context_hash
from .identity import (
    COMPACT_GENOMIC_RE as _COMPACT_GENOMIC_RE,
    GENOMIC_HGVS_RE as _GENOMIC_HGVS_RE,
    GENOMIC_VCF_RE as _GENOMIC_VCF_RE,
    RSID_RE as _RSID_RE,
    formatted_transcript_candidates as _formatted_transcript_candidates,
    myvariant_id_from_hgvs_g as _myvariant_id_from_hgvs_g,
    select_formatted_transcript as _select_formatted_transcript,
    select_mane_transcript as _select_mane_transcript,
    split_gene_coding_input as _split_gene_coding_input,
    split_gene_protein_input as _split_gene_protein_input,
    split_gene_transcript_input as _split_gene_transcript_input,
    transcript_accession as _transcript_accession,
    transcript_candidates as _transcript_candidates,
    classify_variant_scope,
)
from .literature import literature_evidence
from .population import population_evidence
from .policy import ACMGScopedExecutor
from .pvs1 import infer_mechanism_from_population_facts
from .rule_catalog import (
    ACMG_CRITERIA,
    CSPEC_RULE_CATALOG,
    criterion_use_matrix,
    is_valid_strength_for_criterion,
    rule_for_criterion,
)
from .runtime_manifest import BAYESIAN_PRIOR, build_runtime_manifest
from .source_adapters import (
    build_matches,
    coordinates,
    has_variant_identity,
    ncbi_refsnp_alleles,
    prepare_spliceai_features,
    provider_version,
    result_identity,
    source_fact_ready,
)
from .spliceai import bind_spliceai_site
from .summary import compute_bayesian_score, detect_conflicts

_CLINVAR_TITLE_C_RE = re.compile(r"c\.[^\s();:]+", re.IGNORECASE)
_CLINVAR_TITLE_GENE_RE = re.compile(r"\(([A-Za-z][A-Za-z0-9-]*)\)")
_DUP_TRAILING_BASE_RE = re.compile(r"^(c\.\d+(?:[+-]\d+)?dup)[acgt]$", re.IGNORECASE)
_PROTEIN_CHANGE_RE = re.compile(
    r"p\.\(?(?P<ref>[A-Za-z]{1,3})(?P<position>\d+)(?P<alt>[A-Za-z*]{1,3})"
)
_AA3_TO_1 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
    "TER": "*",
}


def _normalize_clinvar_c_token(token: str) -> str:
    """Tolerate 3'-rule dup normalization differences (c.5266dupC == c.5266dup)."""
    normalized = token.casefold().rstrip(".")
    match = _DUP_TRAILING_BASE_RE.fullmatch(normalized)
    return match.group(1) if match else normalized


def _clinvar_variation_id_from_search(
    result: Any, expected_hgvs_c: str, gene: str
) -> str | None:
    """Resolve a unique ClinVar variation ID by c.-token title matching.

    Returns the variation ID only when exactly one searched variant row shares
    the normalized coding HGVS token (and gene, when the title names one);
    zero or ambiguous matches resolve to ``None`` (fail closed).
    """
    features = _reviewable_features(result)
    variants = features.get("variants")
    if not isinstance(variants, list):
        return None
    expected_tokens = {
        _normalize_clinvar_c_token(token)
        for token in _CLINVAR_TITLE_C_RE.findall(expected_hgvs_c)
    }
    if not expected_tokens:
        return None
    expected_gene = _normalize_text(gene)
    matches: set[str] = set()
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        title = str(variant.get("title") or "")
        title_genes = [str(item) for item in variant.get("genes") or []]
        if not title_genes:
            title_genes = _CLINVAR_TITLE_GENE_RE.findall(title)
        if (
            expected_gene
            and title_genes
            and not any(_normalize_text(item) == expected_gene for item in title_genes)
        ):
            continue
        title_tokens = {
            _normalize_clinvar_c_token(token)
            for token in _CLINVAR_TITLE_C_RE.findall(title)
        }
        if expected_tokens & title_tokens:
            variation_id = str(variant.get("variant_id") or "")
            if variation_id.isdecimal():
                matches.add(variation_id)
    return matches.pop() if len(matches) == 1 else None


@dataclass
class SourceCall:
    tool_name: str
    category: str
    status: str
    result: Any = None
    error: str = ""
    arguments: dict[str, Any] | None = None


_CLINICAL_CONTEXT_FIELDS = (
    "zygosity",
    "parental_origin",
    "phase",
    "phenotype",
    "hpo_terms",
    "second_allele_status",
)

_CLINICAL_CONTEXT_NOTICE = (
    "Clinical context is displayed for human review only; it never generates "
    "PS2, PM3, PP4, or any classification."
)


def _protvar_variant(identity: dict[str, Any]) -> str:
    accession = str(identity.get("protein_accession") or "").strip()
    ref, position, alt = _protein_change(identity.get("hgvs_p"))
    if accession and ref and position is not None and alt:
        return f"{accession} {ref}{position}{alt}"
    return ""


def _normalize_clinical_context(raw: Any) -> dict[str, Any] | None:
    """Pass clinical context through as review-only display, never as evidence."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return {
            "review_only": True,
            "not_evidence": True,
            "status": "invalid",
            "error": "clinical_context must be an object",
            "notice": _CLINICAL_CONTEXT_NOTICE,
        }
    values: dict[str, Any] = {}
    ignored: list[str] = []
    for key, value in raw.items():
        if key in _CLINICAL_CONTEXT_FIELDS and isinstance(
            value, (str, int, float, bool, list)
        ):
            values[key] = value
        else:
            ignored.append(str(key))
    return {
        "review_only": True,
        "not_evidence": True,
        "status": "accepted",
        "notice": _CLINICAL_CONTEXT_NOTICE,
        "values": values,
        "ignored_fields": ignored,
    }


def _normalize_evidence_decisions(
    raw: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], ["evidence_decisions must be an array"]
    decisions: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"evidence_decisions[{index}] must be an object")
            continue
        card_id = str(item.get("card_id") or "").strip()
        decision = str(item.get("decision") or "").strip().casefold()
        strength_override = str(item.get("strength_override") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if not card_id:
            errors.append(f"evidence_decisions[{index}].card_id is required")
            continue
        if card_id in seen:
            errors.append(f"duplicate evidence decision for card_id {card_id}")
            continue
        seen.add(card_id)
        if decision not in {"accept", "reject"}:
            errors.append(
                f"evidence_decisions[{index}].decision must be accept or reject"
            )
            continue
        if strength_override and decision != "accept":
            errors.append(
                f"evidence_decisions[{index}] may override strength only when accepted"
            )
            continue
        if strength_override and not reason:
            errors.append(
                f"evidence_decisions[{index}].reason is required for strength_override"
            )
            continue
        decisions.append(
            {
                "card_id": card_id,
                "decision": decision,
                "strength_override": strength_override,
                "reason": reason,
                "reviewer": str(item.get("reviewer") or "").strip(),
                "decided_at": str(item.get("decided_at") or "").strip(),
            }
        )
    return decisions, errors


def _literature_input(arguments: dict[str, Any]) -> tuple[Any, str]:
    proposals = arguments.get("literature_proposals")
    return proposals, ""


def _hpo_query_specs(
    arguments: dict[str, Any],
) -> list[tuple[str, dict[str, Any], str]]:
    """Return conditionally relevant HPO calls without choosing ambiguous terms."""
    context = arguments.get("clinical_context")
    if not isinstance(context, dict):
        return []
    raw_values: list[Any] = []
    hpo_terms = context.get("hpo_terms")
    raw_values.extend(hpo_terms if isinstance(hpo_terms, list) else [])
    phenotype = context.get("phenotype")
    raw_values.extend(phenotype if isinstance(phenotype, list) else [phenotype])

    normalized_ids: list[str] = []
    free_text: list[str] = []
    for raw in raw_values:
        value = str(raw or "").strip()
        if not value:
            continue
        match = re.fullmatch(r"(?i)(?:HP[:_])?(\d{1,7})", value)
        if match:
            term_id = f"HP:{match.group(1).zfill(7)}"
            if term_id not in normalized_ids:
                normalized_ids.append(term_id)
        elif value not in free_text:
            free_text.append(value)

    specs: list[tuple[str, dict[str, Any], str]] = []
    for term_id in normalized_ids:
        specs.extend(
            [
                ("HPO_get_term", {"term_id": term_id}, "phenotype_context"),
                (
                    "HPO_get_genes_by_phenotype",
                    {"term_id": term_id, "limit": 500},
                    "phenotype_context",
                ),
                (
                    "HPO_get_diseases_by_phenotype",
                    {"term_id": term_id, "limit": 500},
                    "phenotype_context",
                ),
            ]
        )
    specs.extend(
        (
            "HPO_search_terms",
            {"query": value, "max_results": 50},
            "phenotype_context",
        )
        for value in free_text
    )
    return specs


def _variant_literature_aliases(
    identity: dict[str, Any] | None,
    arguments: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    identity = identity if isinstance(identity, dict) else {}
    arguments = arguments if isinstance(arguments, dict) else {}
    exact: list[str] = []
    equivalent: list[str] = []

    def add(target: list[str], value: Any) -> None:
        text = str(value or "").strip()
        if text and text not in target:
            target.append(text)
        if ":" in text:
            shorthand = text.split(":", 1)[1]
            if shorthand and shorthand not in target:
                target.append(shorthand)

    for value in (
        arguments.get("variant"),
        identity.get("validated_hgvs_c"),
        identity.get("hgvs_c"),
        identity.get("hgvs_g"),
        identity.get("hgvs_p"),
        identity.get("rsid"),
    ):
        add(exact, value)
    for value in (
        identity.get("hgvs_g_grch37"),
        (identity.get("normalization") or {}).get("vep_hgvs_c")
        if isinstance(identity.get("normalization"), dict)
        else None,
    ):
        add(equivalent, value)
    normalization = identity.get("normalization")
    normalization = normalization if isinstance(normalization, dict) else {}
    for candidate in normalization.get("recoder_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        for key in ("hgvsc", "hgvsg", "hgvsp", "ids"):
            for value in candidate.get(key) or []:
                add(equivalent, value)
    for coords in (
        identity.get("coordinates"),
        identity.get("coordinates_grch37"),
    ):
        if not isinstance(coords, dict) or not all(
            coords.get(key) not in (None, "") for key in ("chr", "pos", "ref", "alt")
        ):
            continue
        chrom = str(coords["chr"]).removeprefix("chr")
        for value in (
            f"{chrom}-{coords['pos']}-{coords['ref']}-{coords['alt']}",
            f"{chrom}_{coords['pos']}_{coords['ref']}_{coords['alt']}",
            f"chr{chrom}:{coords['pos']}:{coords['ref']}:{coords['alt']}",
        ):
            add(equivalent, value)
        coding = str(identity.get("validated_hgvs_c") or identity.get("hgvs_c") or "")
        ref = str(coords["ref"]).upper()
        alt = str(coords["alt"]).upper()
        if (
            coding.casefold().endswith("del")
            and ref.startswith(alt)
            and len(ref) > len(alt)
        ):
            deleted = ref[len(alt) :]
            add(equivalent, f"{coding}{deleted}")

    protein = str(identity.get("hgvs_p") or "")
    protein_change = protein.split(":", 1)[-1]
    match = re.fullmatch(
        r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})fs(?:Ter|\*)(\d+)",
        protein_change,
    )
    if match:
        add(
            equivalent,
            (
                f"p.{_AA3_TO_1[match.group(1).upper()]}{match.group(2)}"
                f"{_AA3_TO_1[match.group(3).upper()]}fs*{match.group(4)}"
            ),
        )
    equivalent = [value for value in equivalent if value not in exact]
    return {"exact": exact, "equivalent": equivalent}


def _literature_alias_in_text(alias: str, searchable: str) -> bool:
    """Match a normalized alias as a complete token, not an HGVS prefix."""
    if not alias:
        return False
    return (
        re.search(
            rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",
            searchable,
        )
        is not None
    )


def _literature_candidate_index(
    source_facts: dict[str, SourceFact],
    identity: dict[str, Any] | None = None,
    arguments: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Merge publications through an identifier graph and classify relevance."""
    aliases = _variant_literature_aliases(identity, arguments)
    normalized_exact = {_normalize_text(value): value for value in aliases["exact"]}
    normalized_equivalent = {
        _normalize_text(value): value for value in aliases["equivalent"]
    }
    gene = _normalize_text(
        (arguments or {}).get("gene") or (identity or {}).get("gene")
    )
    residue_tokens = {
        f"{match.group(1).casefold()}{match.group(2)}"
        for value in (
            (identity or {}).get("hgvs_p"),
            (arguments or {}).get("variant"),
        )
        for match in [re.search(r"p\.\(?([A-Z][a-z]{2})(\d+)", str(value or ""))]
        if match
    }
    entries: list[dict[str, Any]] = []
    literature_tools = {
        "LitVar_search_variants",
        "LitVar_get_variant_publications",
        "EuropePMC_search_articles",
        "PubMed_search_articles",
        "PubTator3_LiteratureSearch",
    }
    for fact in source_facts.values():
        if fact.tool_name not in literature_tools:
            continue
        articles = fact.features.get("articles")
        if not isinstance(articles, list):
            continue
        query = str(
            fact.features.get("query")
            or fact.request_arguments.get("query")
            or fact.request_arguments.get("rsid")
            or ""
        )
        for article in articles:
            if not isinstance(article, dict):
                continue
            pmid = str(article.get("pmid") or article.get("PMID") or "").strip()
            pmcid = str(article.get("pmcid") or article.get("PMCID") or "").strip()
            doi = str(article.get("doi") or article.get("DOI") or "").strip()
            title = str(article.get("title") or article.get("Title") or "").strip()
            if not (pmid or pmcid or doi or title):
                continue
            entries.append(
                {
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "doi": doi,
                    "title": title,
                    "authors": article.get("authors")
                    or article.get("authorList")
                    or [],
                    "journal": article.get("journal") or article.get("journalTitle"),
                    "publication_date": article.get("pub_date")
                    or article.get("pubYear")
                    or article.get("firstPublicationDate"),
                    "url": article.get("url"),
                    "abstract": article.get("abstract") or article.get("abstractText"),
                    "snippet": article.get("snippet")
                    or article.get("highlight")
                    or " ".join(
                        str(value)
                        for value in article.get("fulltext_snippets") or []
                        if value
                    ),
                    "has_full_text": article.get("hasFullText")
                    if "hasFullText" in article
                    else article.get("has_full_text"),
                    "full_text_availability_reported": (
                        "hasFullText" in article or "has_full_text" in article
                    ),
                    "full_text": article.get("full_text"),
                    "full_text_url": article.get("fullTextUrl")
                    or article.get("full_text_url"),
                    "source": fact.tool_name,
                    "source_fact_id": fact.fact_id,
                    "query": query,
                    "provider_linked_variant": (
                        fact.tool_name == "LitVar_get_variant_publications"
                    ),
                    "review_fact_types": list(
                        fact.request_arguments.get("_acmg_fact_types") or []
                    ),
                    "prior_variant_candidates": list(
                        fact.request_arguments.get("_acmg_prior_variant_candidates")
                        or []
                    ),
                }
            )

    parent = list(range(len(entries)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    identifier_conflicts: dict[int, list[dict[str, Any]]] = {}
    for left in range(len(entries)):
        for right in range(left + 1, len(entries)):
            left_ids = {
                f"{key}:{str(entries[left][key]).casefold()}"
                for key in ("pmid", "pmcid", "doi")
                if entries[left].get(key)
            }
            right_ids = {
                f"{key}:{str(entries[right][key]).casefold()}"
                for key in ("pmid", "pmcid", "doi")
                if entries[right].get(key)
            }
            if not left_ids.intersection(right_ids):
                continue
            conflicts = [
                {
                    "identifier_type": key,
                    "left": entries[left].get(key),
                    "right": entries[right].get(key),
                }
                for key in ("pmid", "pmcid", "doi")
                if entries[left].get(key)
                and entries[right].get(key)
                and _normalize_text(entries[left][key])
                != _normalize_text(entries[right][key])
            ]
            if conflicts:
                identifier_conflicts.setdefault(left, []).extend(conflicts)
                identifier_conflicts.setdefault(right, []).extend(conflicts)
                continue
            union(left, right)

    groups: dict[int, list[int]] = {}
    for index in range(len(entries)):
        groups.setdefault(find(index), []).append(index)
    candidates: list[dict[str, Any]] = []
    for member_indexes in groups.values():
        members = [entries[index] for index in member_indexes]

        def first(key: str) -> Any:
            return next((row.get(key) for row in members if row.get(key)), "")

        pmid, pmcid, doi = first("pmid"), first("pmcid"), first("doi")
        title, abstract = first("title"), first("abstract")
        group_identifier_conflicts = [
            conflict
            for index in member_indexes
            for conflict in identifier_conflicts.get(index, [])
        ]
        publication_id = next(
            (
                value
                for value in (
                    f"pmid:{pmid}" if pmid else "",
                    f"pmcid:{str(pmcid).casefold()}" if pmcid else "",
                    f"doi:{str(doi).casefold()}" if doi else "",
                    f"title:{_normalize_text(title)}" if title else "",
                )
                if value
            ),
            "",
        )
        if group_identifier_conflicts:
            conflict_identity = [
                {
                    "pmid": row.get("pmid"),
                    "pmcid": row.get("pmcid"),
                    "doi": row.get("doi"),
                }
                for row in members
            ]
            publication_id += (
                ":conflict:"
                + hashlib.sha256(
                    json.dumps(
                        conflict_identity, sort_keys=True, separators=(",", ":")
                    ).encode()
                ).hexdigest()[:10]
            )
        searchable = _normalize_text(
            " ".join(
                str(value or "")
                for row in members
                for value in (
                    row.get("title"),
                    row.get("abstract"),
                    row.get("snippet"),
                    row.get("full_text"),
                )
            )
        )
        exact_matches = [
            original
            for normalized, original in normalized_exact.items()
            if _literature_alias_in_text(normalized, searchable)
        ]
        equivalent_matches = [
            original
            for normalized, original in normalized_equivalent.items()
            if _literature_alias_in_text(normalized, searchable)
        ]
        if exact_matches:
            match_class = "exact_variant_match"
        elif equivalent_matches:
            match_class = "equivalent_variant_match"
        elif any(row.get("provider_linked_variant") for row in members):
            match_class = "provider_linked_variant_match"
        elif any(row.get("prior_variant_candidates") for row in members):
            match_class = "same_residue_match"
        elif any(token in searchable for token in residue_tokens):
            match_class = "same_residue_match"
        elif (
            gene
            and gene in searchable
            and any(
                token in searchable
                for token in (
                    "loss of function",
                    "loss-of-function",
                    "haploinsufficiency",
                    "truncating",
                    "nonsense mediated decay",
                    "splice",
                )
            )
        ):
            match_class = "mechanism_background"
        elif gene and gene in searchable:
            match_class = "gene_disease_background"
        else:
            match_class = "unverified_candidate"
        verified_full_text = any(
            isinstance(row.get("full_text"), str)
            and bool(str(row.get("full_text") or "").strip())
            for row in members
        )
        reported_full_text = any(
            row.get("has_full_text") is True or row.get("full_text_url")
            for row in members
        )
        explicitly_unavailable = any(
            row.get("full_text_availability_reported") is True
            and row.get("has_full_text") is False
            for row in members
        )
        if verified_full_text:
            full_text_status = "full_text_verified_available"
        elif abstract:
            full_text_status = "abstract_only"
        elif explicitly_unavailable:
            full_text_status = "full_text_unavailable"
        elif reported_full_text:
            full_text_status = "full_text_reported_available"
        else:
            full_text_status = "availability_unknown"
        candidates.append(
            {
                "publication_id": publication_id,
                "pmid": pmid,
                "pmcid": pmcid,
                "doi": doi,
                "title": title,
                "authors": first("authors") or [],
                "journal": first("journal"),
                "publication_date": first("publication_date"),
                "url": first("url"),
                "abstract": abstract,
                "full_text_available": verified_full_text,
                "full_text_reported_available": reported_full_text,
                "full_text_status": full_text_status,
                "record_content_status": (
                    "abstract_only" if abstract else "index_record_only"
                ),
                "match_class": match_class,
                "matched_variant_aliases": sorted(
                    set(exact_matches + equivalent_matches)
                ),
                "sources": sorted({str(row["source"]) for row in members}),
                "source_fact_ids": sorted(
                    {str(row["source_fact_id"]) for row in members}
                ),
                "search_queries": sorted(
                    {str(row["query"]) for row in members if row.get("query")}
                ),
                "review_fact_types": sorted(
                    {
                        str(value)
                        for row in members
                        for value in row.get("review_fact_types") or []
                        if value
                    }
                ),
                "prior_variant_candidates": [
                    row
                    for key, row in {
                        str(candidate.get("prior_variant_identity") or ""): candidate
                        for member in members
                        for candidate in member.get("prior_variant_candidates") or []
                        if isinstance(candidate, dict)
                        and candidate.get("prior_variant_identity")
                    }.items()
                    if key
                ],
                "identifier_conflicts": group_identifier_conflicts,
            }
        )
    return sorted(candidates, key=lambda row: str(row["publication_id"]))


def _document_provenance(result: Any) -> dict[str, Any]:
    """Normalize full-text provenance across structured and fallback envelopes."""
    payload = result if isinstance(result, dict) else {}
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    return {
        "source": str(payload.get("source") or metadata.get("source") or ""),
        "format": str(payload.get("format") or metadata.get("format") or ""),
        "url": str(payload.get("url") or metadata.get("url") or ""),
        "retrieval_trace": list(
            payload.get("retrieval_trace") or metadata.get("retrieval_trace") or []
        ),
        "truncated": payload.get("truncated") is True,
        "truncated_sections": [
            str(value)
            for value in payload.get("truncated_sections") or []
            if value
        ],
    }


def _literature_review_state(
    candidates: list[dict[str, Any]],
    source_facts: dict[str, SourceFact],
    *,
    identity: dict[str, Any],
    arguments: dict[str, Any],
    consequence_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build executable host-LLM review requests without embedding a model."""
    proposal_facts = [
        fact
        for fact in source_facts.values()
        if fact.tool_name == "EuropePMC_get_full_text"
        and fact.features.get("fact_type")
    ]
    manifests = [
        dict(fact.features.get("reading_manifest") or {})
        for fact in proposal_facts
        if isinstance(fact.features.get("reading_manifest"), dict)
    ]
    processed_ids = {
        value
        for fact in proposal_facts
        for value in (
            str(fact.features.get("pmid") or ""),
            str(fact.features.get("pmcid") or ""),
        )
        if value and fact.assessment_ready
    }
    submitted_ids = {
        value
        for fact in proposal_facts
        for value in (
            str(fact.features.get("pmid") or ""),
            str(fact.features.get("pmcid") or ""),
        )
        if value
    }
    blocked_submitted_ids = {
        value
        for fact in proposal_facts
        if str((fact.features.get("reading_manifest") or {}).get("status") or "")
        in {"abstract_only", "unavailable"}
        for value in (
            str(fact.features.get("pmid") or ""),
            str(fact.features.get("pmcid") or ""),
        )
        if value
    }
    consequence_terms = set(
        (consequence_profile or {}).get("selected_transcript_terms") or []
    )
    mechanism_review_needed = bool(
        consequence_terms.intersection(
            {
                "frameshift_variant",
                "stop_gained",
                "splice_donor_variant",
                "splice_acceptor_variant",
                "missense_variant",
            }
        )
        and not any(
            fact.assessment_ready
            and fact.features.get("fact_type") in {"disease_mechanism", "mechanism"}
            for fact in source_facts.values()
        )
    )
    search_queries: dict[str, dict[str, Any]] = {}
    for fact in source_facts.values():
        query = str(
            fact.request_arguments.get("query") or fact.features.get("query") or ""
        ).strip()
        if not query:
            continue
        query_id = (
            "acmg-lit-query:v1:" + hashlib.sha256(query.encode()).hexdigest()[:16]
        )
        entry = search_queries.setdefault(
            query_id,
            {"query_id": query_id, "query": query, "providers": [], "pages": []},
        )
        if fact.tool_name not in entry["providers"]:
            entry["providers"].append(fact.tool_name)
        page = fact.request_arguments.get("page")
        if isinstance(page, int) and page not in entry["pages"]:
            entry["pages"].append(page)
    requests: list[dict[str, Any]] = []
    for candidate in candidates:
        match_class = candidate.get("match_class")
        if match_class not in {
            "exact_variant_match",
            "equivalent_variant_match",
            "provider_linked_variant_match",
        } and not (match_class == "mechanism_background" and mechanism_review_needed):
            continue
        pmid = str(candidate.get("pmid") or "")
        pmcid = str(candidate.get("pmcid") or "")
        request_payload = {"pmcid": pmcid} if pmcid else {"pmid": pmid}
        if not request_payload.get("pmcid") and not request_payload.get("pmid"):
            continue
        stable_payload = {
            "publication_id": candidate.get("publication_id"),
            "matched_variant_aliases": candidate.get("matched_variant_aliases"),
            "document": request_payload,
        }
        request_id = (
            "acmg-literature-review:v1:"
            + hashlib.sha256(
                json.dumps(
                    stable_payload, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()[:20]
        )
        identifiers = {value for value in (pmid, pmcid) if value}
        if identifiers.intersection(processed_ids):
            state = "completed"
        elif identifiers.intersection(blocked_submitted_ids):
            state = "blocked_full_text_unavailable"
        elif identifiers.intersection(submitted_ids):
            state = "proposal_validation_failed"
        elif candidate.get("full_text_status") != "full_text_unavailable":
            state = "pending"
        else:
            state = "blocked_full_text_unavailable"
        fallback_arguments = (
            {"pmcid": pmcid, "output_format": "text", "max_chars": 2000000}
            if pmcid
            else {
                "source_db": "MED",
                "article_id": pmid,
                "output_format": "text",
                "max_chars": 2000000,
            }
        )
        requests.append(
            {
                "request_id": request_id,
                "publication_id": candidate.get("publication_id"),
                "pmid": pmid,
                "pmcid": pmcid,
                "match_class": match_class,
                "matched_variant_aliases": list(
                    candidate.get("matched_variant_aliases") or []
                ),
                "tool_name": "EuropePMC_get_full_text",
                "arguments": request_payload,
                "tool_attempts": [
                    {
                        "tool_name": "EuropePMC_get_full_text",
                        "arguments": request_payload,
                        "max_attempts": 1,
                    },
                    {
                        "tool_name": "EuropePMC_get_fulltext",
                        "arguments": fallback_arguments,
                        "max_attempts": 1,
                    },
                ],
                "expected_identity": {
                    "variant": identity.get("validated_hgvs_c")
                    or identity.get("hgvs_c"),
                    "gene": arguments.get("gene") or identity.get("gene"),
                    "disease": arguments.get("disease"),
                    "inheritance": arguments.get("inheritance")
                    or arguments.get("inheritance_mode"),
                },
                "allowed_fact_types": sorted(
                    candidate.get("review_fact_types") or LITERATURE_FACT_CRITERIA
                ),
                "prior_variant_candidates": list(
                    candidate.get("prior_variant_candidates") or []
                ),
                "state": state,
                "completion_condition": (
                    "submit excerpt-backed literature_proposals and receive "
                    "identity-bound document SourceFacts"
                ),
                "blocking_reason": (
                    "full_text_not_verified_available"
                    if state == "blocked_full_text_unavailable"
                    else ""
                ),
            }
        )
    pending = [row for row in requests if row["state"] == "pending"]
    blocked = [
        row for row in requests if row["state"] == "blocked_full_text_unavailable"
    ]
    failed = [row for row in requests if row["state"] == "proposal_validation_failed"]
    status = (
        "literature_review_required"
        if pending
        else "proposal_validation_required"
        if failed
        else "blocked_external_full_text"
        if blocked
        else "evidence_ready"
    )
    return {
        "candidates": candidates,
        "review_requests": requests,
        "reading_manifests": manifests,
        "processed_publication_ids": sorted(processed_ids),
        "unprocessed_request_ids": [
            row["request_id"] for row in requests if row["state"] != "completed"
        ],
        "proposal_validation_status": (
            "not_submitted"
            if not proposal_facts
            else "verified"
            if processed_ids
            else "failed"
        ),
        "search_queries": sorted(
            search_queries.values(), key=lambda row: str(row["query_id"])
        ),
        "workflow_status": status,
    }


def _recoverable_gaps(
    consequence_profile: dict[str, Any],
    literature_review: dict[str, Any],
    *,
    protein_mapping: dict[str, Any] | None = None,
    source_facts: dict[str, SourceFact] | None = None,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    attempts = consequence_profile.get("attempted_representations") or []
    primary_failed = any(
        row.get("tool_name") == "EnsemblVEP_annotate_hgvs"
        and row.get("representation") == "selected_transcript_hgvs"
        and row.get("query_status") not in {"success", "no_hit"}
        for row in attempts
        if isinstance(row, dict)
    )
    if primary_failed:
        gaps.append(
            {
                "code": "consequence_primary_provider_failed_but_alternatives_available",
                "status": (
                    "recovered"
                    if consequence_profile.get("annotation_status") == "resolved"
                    else "unresolved"
                ),
                "handled_internally": True,
                "recovery_status": (
                    "complete"
                    if consequence_profile.get("annotation_status") == "resolved"
                    else "exhausted"
                ),
            }
        )
    if consequence_profile.get("annotation_status") != "resolved":
        gaps.append(
            {
                "code": "selected_transcript_missing",
                "status": "unresolved",
                "handled_internally": True,
                "recovery_status": "exhausted",
            }
        )
    terms = set(consequence_profile.get("selected_transcript_terms") or [])
    exon_structure_ready = any(
        fact.tool_name == "ensembl_lookup_gene" and fact.assessment_ready
        for fact in (source_facts or {}).values()
    )
    if (
        terms.intersection(
            {
                "frameshift_variant",
                "stop_gained",
                "splice_donor_variant",
                "splice_acceptor_variant",
            }
        )
        and not exon_structure_ready
    ):
        gaps.append(
            {
                "code": "exon_structure_missing",
                "status": "unresolved",
                "handled_internally": True,
                "recovery_status": "exhausted",
            }
        )
        gaps.append(
            {
                "code": "nmd_facts_missing",
                "status": "unresolved",
                "handled_internally": True,
                "recovery_status": "exhausted",
            }
        )
    if consequence_profile.get("hgvs_p") and not (
        isinstance(protein_mapping, dict)
        and protein_mapping.get("status") == "resolved"
    ):
        gaps.append(
            {
                "code": "protein_context_missing",
                "status": "unresolved",
                "handled_internally": True,
                "recovery_status": "exhausted",
            }
        )
    if any(
        row.get("state") == "pending"
        for row in literature_review.get("review_requests") or []
        if isinstance(row, dict)
    ):
        gaps.append(
            {
                "code": "variant_literature_full_text_review_pending",
                "status": "host_llm_required",
                "handled_internally": False,
                "recovery_status": "pending",
            }
        )
    return gaps


def _workflow_next_actions(
    literature_review: dict[str, Any],
    rule_context: dict[str, Any],
) -> list[dict[str, Any]]:
    actions = [
        {
            "action": "host_llm_full_text_review",
            "executor": "host_llm",
            "request_id": row.get("request_id"),
            "tool_name": row.get("tool_name"),
            "arguments": dict(row.get("arguments") or {}),
            "tool_attempts": list(row.get("tool_attempts") or []),
            "expected_input": "complete section/table/figure-aware article content",
            "completion_condition": row.get("completion_condition"),
            "blocking_reason": row.get("blocking_reason"),
            "repeat_collector_with": ["literature_proposals"],
        }
        for row in literature_review.get("review_requests") or []
        if isinstance(row, dict) and row.get("state") == "pending"
    ]
    for row in rule_context.get("cspec_review_requests") or []:
        if not isinstance(row, dict):
            continue
        actions.append(
            {
                "action": "host_llm_cspec_review",
                "executor": "host_llm",
                "request_id": "acmg-cspec-review:v1:"
                + hashlib.sha256(
                    json.dumps(row, sort_keys=True, default=str).encode()
                ).hexdigest()[:20],
                "tool_name": "ClinGen_search_cspec",
                "arguments": {
                    "gene": (
                        (rule_context.get("applicable_specification") or {}).get("gene")
                        if isinstance(
                            rule_context.get("applicable_specification"), dict
                        )
                        else ""
                    )
                },
                "expected_input": "source-located CSpec interpretation",
                "completion_condition": (
                    "submit hash-bound cspec_proposals and receive a verified contract"
                ),
                "blocking_reason": "",
                "repeat_collector_with": ["cspec_proposals"],
            }
        )
    return actions


def _review_readiness(
    *,
    variant_scope: dict[str, Any],
    identity: dict[str, Any],
    arguments: dict[str, Any],
    workflow_status: str,
    criterion_reviews: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    conflict_report: dict[str, Any],
    literature_review: dict[str, Any],
    recoverable_gaps: list[dict[str, Any]],
    system_preview_bayesian: dict[str, Any],
    validated_subset_bayesian: dict[str, Any],
    user_selected_bayesian: dict[str, Any],
) -> dict[str, Any]:
    """Report whether automatic evidence collection is ready for human review."""
    if workflow_status == "input_correction_required":
        status = "blocked"
    elif variant_scope.get("collector_supported") is False:
        status = "not_applicable"
    elif identity.get("identity_verified") is not True:
        status = "blocked"
    elif workflow_status != "evidence_ready":
        status = "incomplete"
    else:
        status = "ready_for_evidence_review"

    route_counts: dict[str, int] = {}
    assessment_counts: dict[str, int] = {}
    for row in criterion_reviews:
        route = str(row.get("route_status") or "insufficient_information")
        assessment = str(row.get("assessment_status") or "not_assessed")
        route_counts[route] = route_counts.get(route, 0) + 1
        assessment_counts[assessment] = assessment_counts.get(assessment, 0) + 1
    pending_request_ids = sorted(
        {
            str(row.get("request_id") or "")
            for row in literature_review.get("review_requests") or []
            if isinstance(row, dict) and row.get("state") != "completed"
        }
    )
    pending_card_ids = sorted(
        {
            str(row.get("card_id") or "")
            for row in evidence_rows
            if row.get("proposal_status") == "requires_user_review"
            and row.get("user_decision", "pending") == "pending"
            and row.get("card_id")
        }
    )
    conflicts = [
        row for row in conflict_report.get("conflicts") or [] if isinstance(row, dict)
    ]
    condition_values = {
        "disease": str(arguments.get("disease") or ""),
        "inheritance": str(
            arguments.get("inheritance") or arguments.get("inheritance_mode") or ""
        ),
    }
    return {
        "status": status,
        "identity_status": (
            "verified" if identity.get("identity_verified") is True else "unresolved"
        ),
        "disease_status": "provided" if condition_values["disease"] else "not_provided",
        "inheritance_status": (
            "provided" if condition_values["inheritance"] else "not_provided"
        ),
        "criterion_counts": {
            "total": len(criterion_reviews),
            "by_route_status": route_counts,
            "by_assessment_status": assessment_counts,
        },
        "unresolved_conflict_count": len(conflicts),
        "unresolved_conflicts": conflicts,
        "pending_request_ids": [value for value in pending_request_ids if value],
        "candidate_card_ids": pending_card_ids,
        "system_preview_available": status
        not in {"blocked", "not_applicable"}
        and system_preview_bayesian.get("status") == "computed",
        "validated_subset_available": status
        not in {"blocked", "not_applicable"}
        and validated_subset_bayesian.get("status") == "computed",
        "user_decision_status": str(
            user_selected_bayesian.get("status") or "not_requested"
        ),
        "blocking_requirements": [
            str(row.get("code") or "")
            for row in recoverable_gaps
            if isinstance(row, dict)
            and row.get("status") == "unresolved"
            and row.get("code")
        ],
        "workflow_status": workflow_status,
        "notice": (
            "Readiness means automatic evidence gathering is complete enough for "
            "EvidenceCard review; it is not a five-tier classification."
        ),
    }


def _apply_evidence_decisions(
    rows: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    *,
    known_source_fact_ids: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not decisions:
        for row in rows:
            row["user_decision"] = "pending"
            row["user_selected_included"] = False
            row["effective_strength"] = str(
                row.get("effective_strength") or row.get("strength") or ""
            )
        return (
            {
                "status": "not_requested",
                "estimate_type": "user_selected",
                "prior_probability": BAYESIAN_PRIOR,
                "not_a_final_classification": True,
            },
            {
                "status": "not_requested",
                "matched_decisions": [],
                "unmatched_decisions": [],
                "decision_errors": [],
                "compatibility_exclusions": [],
            },
        )

    by_card_id = {str(row.get("card_id") or ""): row for row in rows}
    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    decision_errors: list[dict[str, Any]] = []
    for decision in decisions:
        card_id = decision["card_id"]
        row = by_card_id.get(card_id)
        if row is None:
            unmatched.append(dict(decision))
            continue
        matched.append(dict(decision))
        row["decision_reason"] = decision.get("reason") or ""
        if decision["decision"] == "reject":
            row["user_decision"] = "rejected"
            row["user_selected_included"] = False
            continue
        effective_strength = (
            decision.get("strength_override")
            or row.get("effective_strength")
            or row.get("strength")
            or ""
        )
        criterion = str(
            row.get("suggested_criterion") or row.get("criterion") or ""
        )
        if not is_valid_strength_for_criterion(criterion, str(effective_strength)):
            row["user_decision"] = "pending"
            row["user_selected_included"] = False
            decision_errors.append(
                {
                    "card_id": card_id,
                    "reason": "invalid_strength_for_criterion",
                    "criterion": criterion,
                    "strength": effective_strength,
                }
            )
            continue
        candidate_row = {
            **row,
            "effective_strength": str(effective_strength),
            "system_preview_included": True,
        }
        if not is_source_backed_candidate(
            candidate_row,
            known_source_fact_ids=known_source_fact_ids,
        ):
            row["user_decision"] = "pending"
            row["user_selected_included"] = False
            decision_errors.append(
                {
                    "card_id": card_id,
                    "reason": "proposal_not_eligible_for_source_backed_selection",
                }
            )
            continue
        row["user_decision"] = (
            "modified" if decision.get("strength_override") else "accepted"
        )
        row["effective_strength"] = str(effective_strength)
        row["user_selected_included"] = True

    selection_rows = [
        {
            **row,
            "system_preview_included": True,
        }
        for row in rows
        if row.get("user_selected_included") is True
    ]
    compatibility = resolve_evidence_compatibility(
        selection_rows,
        known_source_fact_ids=known_source_fact_ids,
        eligibility="source_backed",
        selection_field="user_selected_included",
    )
    compatible_ids = {
        str(row.get("card_id") or "") for row in compatibility["compatible_evidence"]
    }
    for row in rows:
        if (
            row.get("user_selected_included") is True
            and str(row.get("card_id") or "") not in compatible_ids
        ):
            row["user_selected_included"] = False
    selected_score = compute_bayesian_score(
        rows,
        known_source_fact_ids=known_source_fact_ids,
        estimate_type="user_selected",
        selection_field="user_selected_included",
        eligibility="source_backed",
    )
    selected_score["excluded_card_ids"] = [
        str(row.get("card_id") or "")
        for row in compatibility["excluded_evidence"]
        if row.get("card_id")
    ]
    return (
        selected_score,
        {
            "status": "completed",
            "matched_decisions": matched,
            "unmatched_decisions": unmatched,
            "decision_errors": decision_errors,
            "compatibility_exclusions": [
                {
                    "card_id": row.get("card_id"),
                    "criterion": row.get("criterion"),
                    "reason": row.get("reason") or row.get("exclusion_reason"),
                }
                for row in compatibility["excluded_evidence"]
            ],
        },
    )


_SUMMARY_OMITTED_FEATURE_KEYS = {
    "raw_data",
    "raw_output",
    "full_text",
    "fulltext",
    "xml",
    "specification",
}


def _compact_normalized_value(value: Any, *, key: str = "") -> Any:
    """Keep complete normalized indexes while omitting bulky source bodies."""
    if key in _SUMMARY_OMITTED_FEATURE_KEYS:
        return None
    if key == "abstract":
        return bool(str(value or "").strip())
    if isinstance(value, dict):
        return {
            child_key: compacted
            for child_key, child_value in value.items()
            if (compacted := _compact_normalized_value(child_value, key=str(child_key)))
            not in (None, "", [], {})
        }
    if isinstance(value, list):
        return [
            compacted
            for child in value
            if (compacted := _compact_normalized_value(child)) not in (None, "", [], {})
        ]
    return value


def _compact_source_fact(fact: dict[str, Any]) -> dict[str, Any]:
    entry = {
        key: fact.get(key)
        for key in (
            "fact_id",
            "tool_name",
            "status",
            "identity_verified",
            "assessment_ready",
            "provider_version",
            "request_arguments",
            "provenance",
        )
        if fact.get(key) not in (None, "", [], {})
    }
    status = str(fact.get("status") or "")
    tool_name = str(fact.get("tool_name") or "")
    if status not in {"success", "no_hit"} and tool_name != ("EuropePMC_get_full_text"):
        entry = {
            key: entry[key]
            for key in ("fact_id", "tool_name", "status")
            if key in entry
        }
    if tool_name in CONSEQUENCE_METHODS and status != "success":
        entry.pop("request_arguments", None)
    source_links = (
        [
            str(value)
            for value in fact.get("provenance") or []
            if str(value).startswith(("http://", "https://"))
        ]
        if status in {"success", "no_hit"}
        or tool_name == "EuropePMC_get_full_text"
        else []
    )
    if source_links:
        entry["provenance"] = source_links
    else:
        entry.pop("provenance", None)
    if fact.get("tool_name") in {
        "LitVar_search_variants",
        "PubMed_search_articles",
        "EuropePMC_search_articles",
        "PubTator3_LiteratureSearch",
    }:
        if status == "success":
            request_arguments = dict(fact.get("request_arguments") or {})
            query = str(request_arguments.pop("query", "") or "")
            request_arguments.pop("extract_terms_from_fulltext", None)
            if query:
                request_arguments["query_id"] = (
                    "acmg-lit-query:v1:"
                    + hashlib.sha256(query.encode()).hexdigest()[:16]
                )
            entry["request_arguments"] = request_arguments
        else:
            entry.pop("request_arguments", None)
    if (
        tool_name
        in {
            "PubTator3_get_annotations",
            "EPMC_get_text_mined_annotations",
        }
        and status != "success"
    ):
        entry.pop("request_arguments", None)
    if fact.get("status") == "success" and fact.get("assessment_ready") is False:
        entry["limitation"] = "not_assessment_ready"
    features = fact.get("features")
    if fact.get("status") == "success" and isinstance(features, dict):
        summary_features = dict(features)
        tool_name = str(fact.get("tool_name") or "")
        mirrored_tools = {
            "VariantValidator_validate_variant",
            "EnsemblVEP_variant_recoder",
            "VariantValidator_gene2transcripts",
            "SpliceAI_predict_splice",
            "MyVariant_get_pathogenicity_scores",
            "MyVariant_get_metadata",
            *CONSEQUENCE_METHODS,
        }
        if tool_name in mirrored_tools:
            request_arguments = entry.pop("request_arguments", None)
            if isinstance(request_arguments, dict) and request_arguments:
                entry["request_id"] = hashlib.sha256(
                    json.dumps(
                        request_arguments,
                        sort_keys=True,
                        separators=(",", ":"),
                        default=str,
                    ).encode()
                ).hexdigest()[:16]
        if tool_name == "UniProt_get_entry_by_accession":
            for bulky_key in ("comments", "features", "cross_references", "references"):
                summary_features.pop(bulky_key, None)
        if tool_name in {
            "VariantValidator_validate_variant",
            "EnsemblVEP_variant_recoder",
            "VariantValidator_gene2transcripts",
        }:
            summary_features = {}
        elif tool_name == "SpliceAI_predict_splice":
            summary_features = {}
        elif tool_name in {
            "MyVariant_get_pathogenicity_scores",
            "MyVariant_get_metadata",
        }:
            summary_features = {}
        elif tool_name in CONSEQUENCE_METHODS:
            summary_features = {}
        elif tool_name in {
            "LitVar_search_variants",
            "LitVar_get_variant_publications",
            "PubMed_search_articles",
            "EuropePMC_search_articles",
            "PubTator3_LiteratureSearch",
        }:
            summary_features = {}
        elif tool_name in {"EuropePMC_get_full_text", "EuropePMC_get_fulltext"}:
            entry.pop("request_arguments", None)
            entry.pop("provider_version", None)
            compact_values = dict(summary_features.get("values") or {})
            for duplicated_key in (
                "variant_identity",
                "gene",
                "disease",
                "inheritance",
            ):
                compact_values.pop(duplicated_key, None)
            summary_features = {
                key: summary_features.get(key)
                for key in (
                    "submitted_fact_id",
                    "fact_type",
                    "document_hash",
                    "document_source_tool",
                    "document_source",
                    "document_format",
                )
                if summary_features.get(key) not in (None, "", [], {})
            }
            if compact_values:
                summary_features["values"] = compact_values
        clinically_relevant = _compact_normalized_value(summary_features)
        if clinically_relevant:
            entry["observed_values"] = clinically_relevant
    if fact.get("excerpt"):
        entry["excerpt"] = fact["excerpt"]
    if fact.get("locator"):
        entry["locator"] = fact["locator"]
    return entry


def _compact_evidence_card(card: dict[str, Any]) -> dict[str, Any]:
    source = str(card.get("input_source") or "")
    route = {
        "REVEL": "missense_revel",
        "SpliceAI": "spliceai_splice",
    }.get(source, source)
    entry = {
        "card_id": card.get("card_id"),
        "criterion": card.get("criterion"),
        "strength": card.get("strength"),
        "suggested_criterion": card.get("suggested_criterion"),
        "suggested_strength": card.get("suggested_strength"),
        "assessment_status": card.get("assessment_status"),
        "source": source,
        "route": route,
        "proposal_status": card.get("proposal_status"),
        "rule_basis": card.get("rule_basis"),
        "verification_status": card.get("verification_status"),
        "preview_inclusion_basis": card.get("preview_inclusion_basis"),
        "preview_exclusion_reason": card.get("preview_exclusion_reason"),
        "caveats": list(card.get("caveats") or []),
        "missing_requirements": list(card.get("missing_requirements") or []),
        "system_preview_included": card.get("system_preview_included") is True,
        "validated_subset_included": card.get("validated_subset_included") is True,
        "user_decision": card.get("user_decision"),
        "effective_strength": card.get("effective_strength"),
        "user_selected_included": card.get("user_selected_included") is True,
        "decision_reason": card.get("decision_reason"),
        "decision_basis": next(iter(card.get("provenance_chain") or []), ""),
        "source_fact_ids": list(card.get("source_fact_ids") or []),
        "source_pmid": card.get("source_pmid"),
        "source_pmids": list(card.get("source_pmids") or []),
        "source_case_ids": list(card.get("source_case_ids") or []),
    }
    if entry.get("user_decision") == "pending":
        entry.pop("user_decision", None)
    if entry.get("user_selected_included") is False:
        entry.pop("user_selected_included", None)
    if entry.get("effective_strength") == entry.get("strength"):
        entry.pop("effective_strength", None)
    if entry.get("assessment_status") not in {"met", "suggested"}:
        entry["decision_basis"] = (
            next(iter(entry.get("missing_requirements") or []), "")
            or str(entry.get("proposal_status") or "")
            or str(entry.get("assessment_status") or "")
        )
    else:
        entry["decision_basis"] = (
            str(entry.get("preview_inclusion_basis") or "")
            or str(entry.get("proposal_status") or "")
        )
    return {
        key: value for key, value in entry.items() if value not in (None, "", [], {})
    }


def _build_guard_context(
    evidence_rows: list[dict[str, Any]],
    source_facts: dict[str, SourceFact],
    *,
    variant_identity: dict[str, Any],
    runtime_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Build the compact, self-contained contract consumed by the Guard."""
    cards = []
    for row in evidence_rows:
        source_ids = list(row.get("source_fact_ids") or [])
        if not source_ids:
            continue
        cards.append(
            {
                "card_id": row.get("card_id"),
                "criterion": row.get("suggested_criterion")
                or row.get("criterion"),
                "proposal_status": row.get("proposal_status"),
                "role": (
                    "validated"
                    if row.get("validated_subset_included") is True
                    else "candidate"
                    if row.get("system_preview_included") is True
                    else "excluded"
                ),
                "source_fact_ids": source_ids,
            }
        )
    referenced_source_ids = {
        str(value)
        for row in cards
        for value in row.get("source_fact_ids") or []
        if value
    }
    known_ids = sorted(referenced_source_ids.intersection(source_facts))
    trusted_ids = sorted(
        fact_id
        for fact_id, fact in source_facts.items()
        if fact_id in referenced_source_ids and fact.assessment_ready
    )
    variant_identity_hash = hashlib.sha256(
        json.dumps(
            variant_identity,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode()
    ).hexdigest()
    context = {
        "schema_version": GUARD_CONTEXT_SCHEMA_VERSION,
        "variant_identity_hash": variant_identity_hash,
        "ruleset_hash": str(runtime_manifest.get("ruleset_hash") or ""),
        "cards": cards,
        "known_source_fact_ids": known_ids,
        "trusted_source_fact_ids": trusted_ids,
    }
    context["context_hash"] = guard_context_hash(context)
    return context


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return the summary-level view: compact indexes, no bulky payloads."""

    def pick(row: dict[str, Any], *keys: str) -> dict[str, Any]:
        return {
            key: row.get(key) for key in keys if row.get(key) not in (None, "", [], {})
        }

    compact = dict(result)
    variant_identity = result.get("variant_identity")
    if isinstance(variant_identity, dict):
        compact["variant_identity"] = pick(
            variant_identity,
            "input_variant",
            "hgvs_c",
            "gene",
            "transcript",
            "normalization_error",
            "candidates",
            "excluded_candidates",
        )
        compact["variant_identity"]["candidates"] = list(
            variant_identity.get("candidates") or []
        )
        compact["variant_identity"]["excluded_candidates"] = list(
            variant_identity.get("excluded_candidates") or []
        )
        compact["variant_identity"]["normalization_details_in"] = "variant"
        compact_variant = dict(compact["variant_identity"])
        full_variant = result.get("variant")
        full_variant = full_variant if isinstance(full_variant, dict) else {}
        normalization = full_variant.get("normalization")
        normalization = normalization if isinstance(normalization, dict) else {}
        compact_normalization = pick(
            normalization,
            "input_kind",
            "transcript_source",
            "transcript_selection",
            "canonical_hgvs",
            "selected_candidate",
            "formatter_candidates",
            "rsid_resolver",
            "selected_genomic_allele",
            "allele_alternatives",
            "error",
            "excluded_candidates",
        )
        if compact_normalization:
            compact_variant["normalization"] = compact_normalization
        compact["variant"] = compact_variant
    compact["source_facts"] = [
        _compact_source_fact(fact)
        for fact in result.get("source_facts") or []
        if isinstance(fact, dict)
    ]
    compact["evidence_cards"] = [
        _compact_evidence_card(card)
        for card in result.get("evidence_cards") or []
        if isinstance(card, dict)
    ]
    compact["source_assertions"] = list(result.get("source_assertions") or [])
    compact["predictor_scores"] = dict(result.get("predictor_scores") or {})
    compact["coverage_summary"] = [
        pick(
            row,
            "source_category",
            "required",
            "query_status",
            "query_completed",
            "hit_count",
            "assessment_ready",
            "source_fact_count",
            "limitation_code",
        )
        for row in result.get("coverage_summary") or []
        if isinstance(row, dict)
    ]
    compact["literature_candidates"] = [
        pick(
            row,
            "publication_id",
            "pmid",
            "pmcid",
            "doi",
            "match_class",
            "full_text_status",
        )
        for row in result.get("literature_candidates") or []
        if isinstance(row, dict)
    ]
    consequence_profile = result.get("consequence_profile")
    if isinstance(consequence_profile, dict):
        compact_profile = dict(consequence_profile)
        compact_profile["observations"] = [
            pick(
                row,
                "source_fact_id",
                "provider",
                "annotation_method",
                "transcript",
                "hgvs_c",
                "hgvs_p",
                "consequence_terms",
                "biotype",
                "exon",
                "identity_status",
                "selected_transcript_status",
                "assessment_ready",
            )
            for row in consequence_profile.get("observations") or []
            if isinstance(row, dict)
            and (
                row.get("assessment_ready") is True
                or row.get("identity_status") == "conflict"
            )
        ]
        compact_profile["attempted_representations"] = [
            pick(row, "representation", "query_status", "outcome")
            for row in consequence_profile.get("attempted_representations") or []
            if isinstance(row, dict)
        ]
        compact_profile["provider_failure_source_fact_ids"] = [
            str(row.get("source_fact_id") or "")
            for row in consequence_profile.get("provider_failures") or []
            if isinstance(row, dict) and row.get("source_fact_id")
        ]
        compact_profile.pop("provider_failures", None)
        compact_profile["provider_failure_details_in"] = "full response"
        selected_observation = consequence_profile.get("selected_observation")
        if isinstance(selected_observation, dict):
            compact_profile["selected_observation"] = {
                "source_fact_id": selected_observation.get("source_fact_id"),
                "provider": selected_observation.get("provider"),
                "complete_observation_in": "consequence_profile.observations",
            }
        compact["consequence_profile"] = compact_profile
    literature_review = result.get("literature_review")
    if isinstance(literature_review, dict):
        compact_review = dict(literature_review)
        search_queries = list(literature_review.get("search_queries") or [])
        compact_review["search_query_ids"] = [
            "acmg-lit-query:v1:"
            + hashlib.sha256(str(query).encode()).hexdigest()[:16]
            for query in search_queries
            if str(query)
        ]
        compact_review.pop("search_queries", None)
        compact_review["candidates"] = [
            pick(
                row,
                "publication_id",
                "pmid",
                "pmcid",
                "doi",
                "match_class",
                "matched_variant_aliases",
                "review_fact_types",
                "prior_variant_candidates",
                "full_text_status",
                "source_fact_ids",
            )
            for row in literature_review.get("candidates") or []
            if isinstance(row, dict)
        ]
        compact_review["reading_manifests"] = [
            pick(
                row,
                "pmid",
                "pmcid",
                "doi",
                "document_hash",
                "status",
                "sections_read",
                "tables_read",
                "figures_read",
                "supplements_read",
                "limitations",
            )
            for row in literature_review.get("reading_manifests") or []
            if isinstance(row, dict)
        ]
        compact_review["review_requests"] = [
            {
                **pick(
                    row,
                    "request_id",
                    "publication_id",
                    "pmid",
                    "pmcid",
                    "match_class",
                    "state",
                    "blocking_reason",
                ),
                **(
                    {
                        "allowed_fact_types": list(row.get("allowed_fact_types") or []),
                        "prior_variant_candidates": list(
                            row.get("prior_variant_candidates") or []
                        ),
                    }
                    if row.get("state") not in {"completed", "processed"}
                    else {}
                ),
                "execution_details_in": "next_actions",
            }
            for row in literature_review.get("review_requests") or []
            if isinstance(row, dict)
        ]
        compact["literature_review"] = compact_review
    compatibility = result.get("compatibility_report")
    if isinstance(compatibility, dict):
        compact["compatibility_report"] = {
            "compatible_card_ids": [
                str(row.get("card_id") or "")
                for row in compatibility.get("compatible_evidence") or []
                if isinstance(row, dict) and row.get("card_id")
            ],
            "excluded_evidence": [
                {
                    "card_id": row.get("card_id"),
                    "criterion": row.get("criterion"),
                    "reason": row.get("reason") or row.get("exclusion_reason"),
                }
                for row in compatibility.get("excluded_evidence") or []
                if isinstance(row, dict)
            ],
        }
    conflict_report = result.get("conflict_report")
    if isinstance(conflict_report, dict):
        compact_conflicts = dict(conflict_report)
        compact_conflicts["compatibility_exclusions"] = [
            str(row.get("criterion") or "")
            for row in conflict_report.get("compatibility_exclusions") or []
            if isinstance(row, dict) and row.get("criterion")
        ]
        compact_conflicts["compatibility_exclusion_details_in"] = (
            "compatibility_report.excluded_evidence"
        )
        compact["conflict_report"] = compact_conflicts
    for key in (
        "system_preview_bayesian",
        "validated_subset_bayesian",
        "user_selected_bayesian",
    ):
        bayesian = result.get(key)
        if isinstance(bayesian, dict):
            compact_bayesian = dict(bayesian)
            compact_bayesian.pop("compatibility_exclusions", None)
            compact_bayesian.pop("excluded_card_ids", None)
            compact[key] = compact_bayesian
    compact["criterion_reviews"] = []
    for review in result.get("criterion_reviews") or []:
        if not isinstance(review, dict):
            continue
        compact_review = pick(
            review,
            "criterion",
            "route_status",
            "pending_request_ids",
            "missing_requirements",
        )
        if review.get("assessment_status") not in {
            "not_assessed",
            "not_applicable",
            "deprecated",
        }:
            card_ids = list(review.get("evidence_card_ids") or [])
            if card_ids:
                compact_review["evidence_card_ids"] = card_ids
        if not compact_review.get("evidence_card_ids"):
            candidate_ids = list(review.get("candidate_source_fact_ids") or [])
            if candidate_ids:
                compact_review["candidate_source_fact_ids"] = candidate_ids
        if review.get("assessment_status") in {
            "met",
            "not_met",
            "not_applicable",
            "deprecated",
        }:
            compact_review.pop("missing_requirements", None)
        compact["criterion_reviews"].append(compact_review)
    rule_context = result.get("rule_context")
    if isinstance(rule_context, dict):
        trimmed_context = dict(rule_context)
        matched = [
            str(row.get("specification_id") or "")
            for row in trimmed_context.get("matched_specifications") or []
            if isinstance(row, dict) and row.get("specification_id")
        ]
        trimmed_context.pop("matched_specifications", None)
        trimmed_context["matched_specification_ids"] = matched
        matrix = trimmed_context.get("criterion_use_matrix")
        if isinstance(matrix, dict):
            trimmed_context.pop("criterion_use_matrix", None)
            trimmed_context["criterion_use_matrix_summary"] = {
                "criteria": len(matrix),
                "ruleset_hash_in": "runtime_manifest.ruleset_hash",
                "complete_matrix_in": "full response rule_context.criterion_use_matrix",
            }
        specification = trimmed_context.get("applicable_specification")
        if isinstance(specification, dict) and "specification" in specification:
            specification = dict(specification)
            specification.pop("specification", None)
            specification["specification_detail"] = "omitted in summary mode"
            trimmed_context["applicable_specification"] = specification
        candidates = trimmed_context.get("vcep_candidates")
        if isinstance(candidates, list):
            trimmed_candidates = []
            for candidate in candidates:
                if isinstance(candidate, dict):
                    candidate = pick(
                        candidate, "specification_id", "gene", "version", "status"
                    )
                trimmed_candidates.append(candidate)
            trimmed_context["vcep_candidates"] = trimmed_candidates
        contract = trimmed_context.get("executable_contract")
        if isinstance(contract, dict):
            compact_contract = {
                key: contract.get(key)
                for key in (
                    "specification_id",
                    "rule_id",
                    "version",
                    "status",
                    "primary_reference",
                    "content_hash",
                    "rule_source",
                    "compiled_contract_status",
                )
            }
            criteria = contract.get("criteria")
            if isinstance(criteria, dict):
                compact_contract["criteria"] = {
                    criterion: {
                        key: row.get(key)
                        for key in (
                            "applicability",
                            "strength",
                            "allowed_strengths",
                            "verification",
                            "mutually_exclusive_with",
                        )
                    }
                    for criterion, row in criteria.items()
                    if isinstance(row, dict)
                }
            trimmed_context["executable_contract"] = compact_contract
        requests = trimmed_context.get("cspec_review_requests")
        if isinstance(requests, list):
            trimmed_context["cspec_review_requests"] = [
                {
                    key: row.get(key)
                    for key in (
                        "specification_id",
                        "version",
                        "content_hash",
                        "criterion",
                        "locator",
                        "reason",
                    )
                }
                for row in requests
                if isinstance(row, dict)
            ]
        compact["rule_context"] = trimmed_context
    compact["response_detail"] = "summary"
    return compact


def _status(result: Any) -> str:
    if result in (None, "", [], {}):
        return "no_hit"
    if isinstance(result, dict):
        status = str(result.get("status") or "").lower()
        if status in {"unavailable", "error", "failed", "no_hit"}:
            return "failed" if status in {"error", "failed"} else status
    return "success"


def _reviewable_features(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    sandbox = result.get("source_lead_sandbox")
    if isinstance(sandbox, dict):
        features = sandbox.get("reviewable_features")
        return features if isinstance(features, dict) else {}
    features = result.get("reviewable_features")
    if isinstance(features, dict):
        return features
    nested = result.get("result")
    if isinstance(nested, dict):
        return _reviewable_features(nested) or nested
    return result


def _features_for_call(call: SourceCall) -> dict[str, Any]:
    """Consume only the sandbox's reviewed, provider-specific feature surface."""
    features = _reviewable_features(call.result)
    return dict(features) if isinstance(features, dict) else {}


def _provider_payload(result: Any) -> Any:
    """Unwrap the small number of upstream provider envelope shapes."""
    if not isinstance(result, dict):
        return result
    for key in ("result", "data"):
        value = result.get(key)
        if isinstance(value, (dict, list)):
            return value
    return result


def _quarantined_conclusions(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    sandbox = result.get("source_lead_sandbox")
    if isinstance(sandbox, dict):
        value = sandbox.get("quarantined_conclusions")
        return value if isinstance(value, dict) else {}
    return {}


def _number(values: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = values.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _integer(values: dict[str, Any], *keys: str) -> int | None:
    value = _number(values, *keys)
    return int(value) if value is not None else None


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _normalize_inheritance(value: Any) -> str:
    normalized = _normalize_text(value).replace("-", " ")
    aliases = {
        "ad": "autosomal dominant",
        "autosomal dominant inheritance": "autosomal dominant",
        "ar": "autosomal recessive",
        "autosomal recessive inheritance": "autosomal recessive",
        "x linked": "x linked",
        "x linked inheritance": "x linked",
        "xl": "x linked",
    }
    return aliases.get(normalized, normalized)


def _identity_hgvs_values(observed: dict[str, Any]) -> set[str]:
    """All HGVS spellings an observed identity carries, incl. candidate lists."""
    values = {
        _normalize_text(observed.get(key))
        for key in ("hgvs_c", "validated_hgvs_c", "hgvs_g")
        if observed.get(key)
    }
    for list_key in ("hgvsc_candidates", "hgvsg_candidates"):
        candidates = observed.get(list_key)
        if isinstance(candidates, list):
            values.update(_normalize_text(value) for value in candidates)
    values.discard("")
    return values


def _identity_hgvs_values_for(
    observed: dict[str, Any],
    *,
    keys: tuple[str, ...],
    list_key: str,
) -> set[str]:
    values = {_normalize_text(observed.get(key)) for key in keys if observed.get(key)}
    candidates = observed.get(list_key)
    if isinstance(candidates, list):
        values.update(_normalize_text(value) for value in candidates)
    values.discard("")
    return values


def _identity_conflicts(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Detect contradictory provider identity fields without cross-mapping HGVS."""
    left_coordinates = left.get("coordinates")
    right_coordinates = right.get("coordinates")
    if left_coordinates and right_coordinates and left_coordinates != right_coordinates:
        return True

    left_rsid = _normalize_text(left.get("rsid"))
    right_rsid = _normalize_text(right.get("rsid"))
    if left_rsid and right_rsid and left_rsid != right_rsid:
        return True

    for keys, list_key in (
        (("hgvs_c", "validated_hgvs_c"), "hgvsc_candidates"),
        (("hgvs_g",), "hgvsg_candidates"),
    ):
        left_hgvs = _identity_hgvs_values_for(left, keys=keys, list_key=list_key)
        right_hgvs = _identity_hgvs_values_for(right, keys=keys, list_key=list_key)
        if left_hgvs and right_hgvs and not left_hgvs & right_hgvs:
            return True

    left_gene = _normalize_text(left.get("gene"))
    right_gene = _normalize_text(right.get("gene"))
    if left_gene and right_gene and left_gene != right_gene:
        return True

    return bool(
        left.get("build") and right.get("build") and not build_matches(left, right)
    )


def _identities_share_variant(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("coordinates") and right.get("coordinates"):
        return left["coordinates"] == right["coordinates"]
    if left.get("rsid") and right.get("rsid"):
        return _normalize_text(left["rsid"]) == _normalize_text(right["rsid"])
    return any(
        bool(
            _identity_hgvs_values_for(left, keys=keys, list_key=list_key)
            & _identity_hgvs_values_for(right, keys=keys, list_key=list_key)
        )
        for keys, list_key in (
            (("hgvs_c", "validated_hgvs_c"), "hgvsc_candidates"),
            (("hgvs_g",), "hgvsg_candidates"),
        )
    )


def _literature_values(
    source_facts: dict[str, SourceFact], fact_type: str
) -> list[dict[str, Any]]:
    return [
        dict(fact.features.get("values") or {})
        for fact in source_facts.values()
        if fact.assessment_ready and fact.features.get("fact_type") == fact_type
    ]


def _literature_fact_ids(
    source_facts: dict[str, SourceFact], *fact_types: str
) -> list[str]:
    allowed = set(fact_types)
    return [
        fact.fact_id
        for fact in source_facts.values()
        if fact.assessment_ready and fact.features.get("fact_type") in allowed
    ]


_SPECIALIZED_LITERATURE_FACTS = {
    "case_control",
    "case_series",
    "de_novo",
    "pm3",
    "recessive_allelic",
    "functional",
}


def _mapped_literature_criterion(
    fact_type: str,
    values: dict[str, Any],
    suggested: str,
) -> tuple[str, str]:
    """Return (criterion, mapping_status) without trusting free-form LLM codes."""
    allowed = set(LITERATURE_FACT_CRITERIA.get(fact_type, ()))
    normalized_suggestion = str(suggested or "").upper()
    if normalized_suggestion in allowed:
        if fact_type == "mechanism" and normalized_suggestion == "PVS1":
            return "", "unmapped"
        return normalized_suggestion, "llm_review_required"
    if fact_type == "segregation":
        direction = _normalize_text(values.get("segregation_direction"))
        if direction in {"segregates", "co-segregates", "cosegregates"}:
            return "PP1", "llm_review_required"
        if direction in {"does not segregate", "nonsegregation", "non-segregation"}:
            return "BS4", "llm_review_required"
    if fact_type == "prior_variant":
        relation = _normalize_text(values.get("amino_acid_relation"))
        if relation == "same amino acid change":
            return "PS1", "llm_review_required"
        if relation == "same residue different change":
            return "PM5", "llm_review_required"
    if fact_type == "mechanism":
        mechanism = _normalize_text(values.get("gene_disease_mechanism"))
        if mechanism in {"missense", "missense constrained"}:
            return "PP2", "llm_review_required"
        if mechanism in {"loss of function", "lof", "truncating"}:
            return "BP1", "llm_review_required"
    if fact_type == "protein_length_repeat":
        effect = _normalize_text(values.get("effect_type"))
        if effect == "length change outside repeat":
            return "PM4", "llm_review_required"
        if effect == "inframe change in repeat":
            return "BP3", "llm_review_required"
    if len(allowed) == 1:
        return next(iter(allowed)), "llm_review_required"
    return "", "unmapped"


def _literature_mapping_requirements_met(
    fact_type: str, values: dict[str, Any], criterion: str
) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if (
        fact_type == "prior_variant"
        and values.get("independent_pathogenic_evidence") is not True
    ):
        missing.append("independent pathogenic evidence for the prior variant")
    if fact_type == "segregation":
        try:
            informative = int(values.get("informative_meioses") or 0)
        except (TypeError, ValueError):
            informative = 0
        if informative <= 0:
            missing.append("positive informative meiosis count")
    if fact_type == "healthy_observation" and values.get("age_appropriate") is not True:
        missing.append("age-appropriate unaffected observation")
    if (
        fact_type == "alternative_cause"
        and values.get("alternative_cause_established") is not True
    ):
        missing.append("established alternative molecular cause")
    if fact_type == "region_hotspot":
        if values.get("pathogenic_enrichment") is not True:
            missing.append("pathogenic enrichment in the region")
        if values.get("benign_variation_depleted") is not True:
            missing.append("depletion of benign variation")
    if fact_type == "rna_splicing":
        missing.append("versioned RNA-splicing evidence rule; PVS1 cannot be bypassed")
    if not criterion:
        missing.append("an allowed fact-type to criterion mapping")
    return not missing, missing


def _shared_string(values: list[dict[str, Any]], key: str) -> str:
    items = {str(value.get(key) or "") for value in values if value.get(key)}
    return items.pop() if len(items) == 1 else ""


def _shared_bool(values: list[dict[str, Any]], key: str) -> bool:
    return bool(values) and all(value.get(key) is True for value in values)


def _stable_source_fact_id(
    tool_name: str, query_identity: dict[str, Any], result: Any
) -> tuple[str, str]:
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)
    raw_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    query = json.dumps(
        query_identity, sort_keys=True, separators=(",", ":"), default=str
    )
    digest = hashlib.sha256(
        f"{tool_name}:{query}:{raw_hash}".encode("utf-8")
    ).hexdigest()[:20]
    return f"acmg-source:v1:{digest}", raw_hash


def _stable_payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _amino_acid(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    return _AA3_TO_1.get(normalized, normalized if len(normalized) == 1 else "")


def _protein_change(hgvs_p: Any) -> tuple[str, int | None, str]:
    match = _PROTEIN_CHANGE_RE.search(str(hgvs_p or ""))
    if not match:
        return "", None, ""
    return (
        _amino_acid(match.group("ref")),
        int(match.group("position")),
        _amino_acid(match.group("alt")),
    )


def _prior_variant_identity(
    accession: str,
    row: dict[str, Any],
    *,
    position: int,
    wild_type: str,
    alternative: str,
) -> str:
    """Choose a stable external identity for a same-residue lead."""
    for xref in row.get("xrefs") or []:
        if isinstance(xref, dict):
            value = xref.get("id") or xref.get("accession") or xref.get("name")
        else:
            value = xref
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    suffix = (
        f"p.{wild_type}{position}{alternative}"
        if alternative
        else f"p.{wild_type}{position}"
    )
    return f"{accession}:{suffix}"


def _same_residue_candidates(
    features: dict[str, Any], hgvs_p: Any
) -> list[dict[str, Any]]:
    """Reduce a protein-wide variation response to review-only residue leads."""
    target_ref, target_position, target_alt = _protein_change(hgvs_p)
    accession = str(features.get("protein_accession") or "")
    if target_position is None or not accession:
        return []
    candidates: dict[str, dict[str, Any]] = {}
    for row in features.get("protein_variants") or []:
        if not isinstance(row, dict):
            continue
        start = _position(row.get("position_start"))
        end = _position(row.get("position_end")) or start
        if start != target_position or end != target_position:
            continue
        wild_type = _amino_acid(row.get("wild_type")) or target_ref
        alternative = _amino_acid(row.get("alternative"))
        source_type = str(row.get("source_type") or "")
        source_text = " ".join(
            str(value or "")
            for value in (
                source_type,
                *(row.get("associations") or []),
                *(row.get("xrefs") or []),
            )
        ).casefold()
        somatic_only = bool(
            "cosmic" in source_text or "somatic" in source_text
        ) and not any(
            token in source_text for token in ("clinvar", "germline", "uniprot")
        )
        identity = _prior_variant_identity(
            accession,
            row,
            position=target_position,
            wild_type=wild_type,
            alternative=alternative,
        )
        candidate = {
            "prior_variant_identity": identity,
            "protein_accession": accession,
            "position": target_position,
            "wild_type": wild_type,
            "alternative": alternative,
            "amino_acid_relation": (
                "same_amino_acid_change"
                if target_alt and alternative == target_alt
                else "same_residue_different_change"
            ),
            "source_type": source_type,
            "associations": list(row.get("associations") or []),
            "xrefs": list(row.get("xrefs") or []),
            "germline_compatible": not somatic_only,
            "review_only": True,
            "independent_pathogenic_evidence_required": True,
        }
        candidates[identity] = candidate
    return sorted(
        candidates.values(), key=lambda row: str(row["prior_variant_identity"])
    )


def _position(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fact_matches_route(fact: SourceFact, route: str) -> bool:
    tool = fact.tool_name
    features = fact.features
    if route == "prior_variant_candidates":
        return tool == "EBIProteins_get_variation" and bool(
            features.get("same_residue_candidates")
        )
    if route == "protein_context":
        return (
            tool.startswith("EBIProteins_")
            or tool.startswith("InterPro_")
            or tool.startswith("UniProt_")
        )
    if route == "constraint":
        return tool == "gnomad_get_constraint"
    if route == "phenotype_context":
        return tool.startswith("HPO_")
    if route == "dynamic_cspec":
        return tool == "ClinGen_search_cspec"
    if route == "disease_context":
        return tool.startswith("ClinGen_") or tool.startswith("HPO_")
    if route == "population":
        return tool in {"gnomad_get_variant", "gnomad_get_variant_populations"}
    if route == "callability":
        return tool == "gnomad_get_site_callability"
    if route == "computational":
        return tool == "MyVariant_get_pathogenicity_scores"
    if route == "splicing_prediction":
        return tool == "SpliceAI_predict_splice"
    if route == "consequence":
        return (
            bool(features.get("consequence_candidates")) or tool in CONSEQUENCE_METHODS
        )
    if route == "literature":
        return tool in {
            "LitVar_search_variants",
            "LitVar_get_variant_publications",
            "EuropePMC_search_articles",
            "PubMed_search_articles",
            "PubTator3_LiteratureSearch",
            "EuropePMC_get_full_text",
        }
    return False


class ACMGEvidencePipeline:
    """Run the evidence-only ACMG workflow with an injected ToolUniverse."""

    def __init__(
        self,
        tooluniverse: Any | None,
        *,
        review_assertion_verifier: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        self.tooluniverse = tooluniverse
        self.provider_executor = ACMGScopedExecutor(tooluniverse)
        self.review_assertion_verifier = review_assertion_verifier or getattr(
            tooluniverse, "acmg_review_assertion_verifier", None
        )

    def _call(
        self, tool_name: str, arguments: dict[str, Any], category: str
    ) -> SourceCall:
        if self.tooluniverse is None:
            return SourceCall(
                tool_name,
                category,
                "unavailable",
                result={"status": "unavailable", "reason": "no ToolUniverse executor"},
                arguments=arguments,
            )
        try:
            result = self.provider_executor.call(tool_name, arguments)
        except Exception as exc:
            return SourceCall(
                tool_name, category, "failed", error=str(exc), arguments=arguments
            )
        return SourceCall(
            tool_name,
            category,
            _status(result),
            result=result,
            arguments=arguments,
        )

    def _rsid_features_from_refsnp(
        self, parsed: dict[str, Any], calls: list[SourceCall]
    ) -> dict[str, Any] | None:
        """Build recoder-shaped rsID features from NCBI refsnp alleles.

        Each SNV allele is projected to coding HGVS through
        VariantValidator_format_genomic_to_transcripts. Returns ``None`` when
        any allele cannot be represented (indels, failed projection) so the
        caller can fall back to the Ensembl recoder instead of guessing.
        """
        alleles = parsed.get("alleles") or []
        if parsed.get("unsupported_alleles") or not alleles:
            return None
        allele_candidates: list[dict[str, Any]] = []
        for allele in alleles:
            formatter_call = self._call(
                "VariantValidator_format_genomic_to_transcripts",
                {"variant_description": allele["hgvs_g"], "genome_build": "GRCh38"},
                "identity",
            )
            calls.append(formatter_call)
            hgvsc = list(
                dict.fromkeys(
                    str(candidate.get("t_hgvs") or "")
                    for candidate in _formatted_transcript_candidates(
                        formatter_call.result
                    )
                    if str(candidate.get("t_hgvs") or "")
                )
            )
            if not hgvsc:
                return None
            allele_candidates.append(
                {
                    "ids": [parsed["rsid"]] if parsed.get("rsid") else [],
                    "hgvsg": [allele["hgvs_g"]],
                    "hgvsc": hgvsc,
                    "hgvsp": [],
                }
            )
        hgvsc_candidates = list(
            dict.fromkeys(
                value for allele in allele_candidates for value in allele["hgvsc"]
            )
        )
        hgvs_c = next(
            (
                value
                for value in hgvsc_candidates
                if value.split(":", 1)[0].startswith("NM_")
            ),
            hgvsc_candidates[0] if hgvsc_candidates else "",
        )
        return {
            "rsid": parsed.get("rsid"),
            "hgvs_g": allele_candidates[0]["hgvsg"][0],
            "hgvs_c": hgvs_c,
            "hgvsc_candidates": hgvsc_candidates,
            "allele_candidates": allele_candidates,
            "provider_version": str(
                parsed.get("provider_version") or "NCBI Variation refsnp"
            ),
        }

    @staticmethod
    def _merge_identity_features(call: SourceCall, features: dict[str, Any]) -> None:
        """Merge resolved identity fields into a resolver call's sandbox.

        The identity stage counts provider-observed identities from each
        call's sandbox; without this merge the NCBI resolver record carries
        the raw refsnp payload but no variant-level identity fields.
        """
        if not isinstance(call.result, dict):
            return
        sandbox = call.result.setdefault("source_lead_sandbox", {})
        reviewable = sandbox.setdefault("reviewable_features", {})
        for key in (
            "rsid",
            "hgvs_c",
            "hgvs_g",
            "hgvsc_candidates",
            "allele_candidates",
            "provider_version",
        ):
            if features.get(key) not in (None, "", []):
                reviewable[key] = features[key]

    def _resolve_rsid_features(
        self, rsid: str, genome_build: str, calls: list[SourceCall]
    ) -> tuple[dict[str, Any], str]:
        """Resolve an rsID to recoder-shaped features without a recoder dependency.

        Primary path: NCBIVariation_rsid_lookup alleles plus per-allele
        VariantValidator projection (works when the Ensembl recoder is down).
        Fallback: EnsemblVEP_variant_recoder when NCBI resolution is unusable.
        """
        if genome_build == "GRCh38":
            ncbi_call = self._call(
                "NCBIVariation_rsid_lookup", {"rsid": rsid}, "identity"
            )
            calls.append(ncbi_call)
            if ncbi_call.status == "success":
                parsed = ncbi_refsnp_alleles(_features_for_call(ncbi_call))
                features = self._rsid_features_from_refsnp(parsed, calls)
                if features is not None:
                    self._merge_identity_features(ncbi_call, features)
                    return features, "NCBIVariation_rsid_lookup"
        recoder_call = self._call(
            "EnsemblVEP_variant_recoder",
            {"variant_id": rsid},
            "identity",
        )
        calls.append(recoder_call)
        return _features_for_call(recoder_call), "EnsemblVEP_variant_recoder"

    def _identity(
        self,
        variant: str,
        gene: str = "",
        transcript: str = "",
        genome_build: str = "GRCh38",
    ) -> tuple[list[SourceCall], dict[str, Any]]:
        genome_build = "GRCh37" if genome_build == "GRCh37" else "GRCh38"
        requested_variant = variant.strip()
        qualified_gene, qualified_variant, qualified_input = (
            _split_gene_transcript_input(requested_variant, gene)
        )
        protein_gene, protein_variant, protein_input = _split_gene_protein_input(
            requested_variant, gene
        )
        requested_gene, shorthand, shorthand_input = _split_gene_coding_input(
            requested_variant, gene
        )
        if qualified_input:
            requested_gene = qualified_gene
        elif protein_input:
            requested_gene = protein_gene
        calls: list[SourceCall] = []
        canonical_variant = requested_variant
        selected_transcript = transcript.strip()
        normalization: dict[str, Any] = {
            "input_variant": requested_variant,
            "input_gene": gene.strip(),
            "genome_build": genome_build,
        }

        def record_excluded_candidates(reason: str) -> None:
            excluded: list[dict[str, Any]] = []
            for kind, values in (
                ("allele", normalization.get("recoder_candidates")),
                ("transcript", normalization.get("transcript_candidates")),
                ("projection", normalization.get("formatter_candidates")),
            ):
                for candidate in values if isinstance(values, list) else []:
                    excluded.append(
                        {
                            "candidate_type": kind,
                            "candidate": candidate,
                            "reason": reason,
                        }
                    )
            normalization["excluded_candidates"] = excluded

        def failed_identity(reason: str) -> tuple[list[SourceCall], dict[str, Any]]:
            normalization["error"] = reason
            record_excluded_candidates(reason)
            return calls, {
                "hgvs_c": requested_variant,
                "build": genome_build,
                "gene": requested_gene or gene.strip(),
                "transcript": selected_transcript,
                "input_variant": requested_variant,
                "normalization": normalization,
                "identity_verified": False,
                "identity_error": reason,
            }

        if qualified_input:
            if not qualified_gene:
                return failed_identity("gene_identity_mismatch")
            canonical_variant = qualified_variant
            input_transcript = _transcript_accession(canonical_variant)
            if transcript and _normalize_text(transcript) != _normalize_text(
                input_transcript
            ):
                return failed_identity("transcript_identity_mismatch")
            selected_transcript = input_transcript
            normalization.update(
                {
                    "input_kind": "gene_transcript_hgvs",
                    "transcript_source": "input",
                    "canonical_hgvs": canonical_variant,
                }
            )
        elif protein_input:
            if not protein_gene:
                return failed_identity("gene_identity_mismatch")
            protein_notation = f"{protein_gene}:{protein_variant}"
            # Resolve protein HGVS through the recoder: it returns the
            # forward-strand genomic HGVS. VEP allele_string follows transcript
            # orientation, which inverts ref/alt for minus-strand genes.
            recoder_call = self._call(
                "EnsemblVEP_variant_recoder",
                {"variant_id": protein_notation},
                "identity",
            )
            calls.append(recoder_call)
            recoder_features = _features_for_call(recoder_call)
            normalization["recoder_candidates"] = list(
                recoder_features.get("allele_candidates") or []
            )
            formatter_variant = str(recoder_features.get("hgvs_g") or "")
            protein_resolver = "EnsemblVEP_variant_recoder"
            if not formatter_variant:
                # Recoder outage fallback: VEP annotates the protein notation
                # directly; the adapter already normalizes its
                # transcript-oriented alleles onto the forward strand.
                protein_call = self._call(
                    "EnsemblVEP_annotate_hgvs",
                    {"hgvs_notation": protein_notation},
                    "identity",
                )
                calls.append(protein_call)
                protein_features = _features_for_call(protein_call)
                observed_gene = str(protein_features.get("gene") or "")
                protein_coordinates = coordinates(protein_features)
                if (
                    protein_call.status != "success"
                    or not protein_coordinates
                    or _normalize_text(observed_gene) != _normalize_text(protein_gene)
                ):
                    return failed_identity("protein_identity_unverified")
                formatter_variant = (
                    f"{protein_coordinates['chr']}-{protein_coordinates['pos']}"
                    f"-{protein_coordinates['ref']}-{protein_coordinates['alt']}"
                )
                protein_resolver = "EnsemblVEP_annotate_hgvs"
            formatter_call = self._call(
                "VariantValidator_format_genomic_to_transcripts",
                {
                    "variant_description": formatter_variant,
                    "genome_build": genome_build,
                },
                "identity",
            )
            calls.append(formatter_call)
            normalization["formatter_candidates"] = _formatted_transcript_candidates(
                formatter_call.result
            )
            selected = _select_formatted_transcript(formatter_call.result)
            if selected is None or (
                selected["gene"]
                and _normalize_text(selected["gene"]) != _normalize_text(protein_gene)
            ):
                return failed_identity("mane_transcript_unverified")
            selected_transcript = selected["reference"]
            if transcript and _normalize_text(transcript) != _normalize_text(
                selected_transcript
            ):
                return failed_identity("transcript_identity_mismatch")
            canonical_variant = selected["t_hgvs"]
            normalization.update(
                {
                    "input_kind": "gene_protein_hgvs",
                    "protein_resolver": protein_resolver,
                    "protein_hgvs": protein_notation,
                    "formatter_input": formatter_variant,
                    "transcript_source": "VariantValidator_format_genomic_to_transcripts",
                    "transcript_selection": {
                        "reference": selected_transcript,
                        "mane_select": True,
                    },
                    "canonical_hgvs": canonical_variant,
                }
            )
        elif shorthand_input:
            if not shorthand:
                calls.append(
                    SourceCall(
                        "VariantValidator_gene2transcripts",
                        "identity",
                        "failed",
                        error="gene is required for coding HGVS shorthand",
                        arguments={"gene_symbol": requested_gene},
                    )
                )
                return failed_identity("gene_required_for_coding_shorthand")
            if selected_transcript:
                normalization["transcript_source"] = "caller"
            else:
                resolver_args = {
                    "gene_symbol": requested_gene,
                    "transcript_set": "mane",
                    "genome_build": genome_build,
                }
                resolver_call = self._call(
                    "VariantValidator_gene2transcripts",
                    resolver_args,
                    "identity",
                )
                calls.append(resolver_call)
                normalization["transcript_candidates"] = _transcript_candidates(
                    resolver_call.result, requested_gene
                )
                selected = _select_mane_transcript(resolver_call.result, requested_gene)
                if selected is None:
                    return failed_identity("mane_transcript_unverified")
                selected_transcript = selected["reference"]
                normalization["transcript_source"] = "VariantValidator_gene2transcripts"
                normalization["transcript_selection"] = {
                    "reference": selected_transcript,
                    "mane_select": selected["mane_select"],
                    "mane_plus_clinical": selected["mane_plus_clinical"],
                }
            canonical_variant = f"{selected_transcript}:{shorthand}"
            normalization["canonical_hgvs"] = canonical_variant
        elif (
            _GENOMIC_HGVS_RE.match(requested_variant)
            or _GENOMIC_VCF_RE.fullmatch(requested_variant)
            or _COMPACT_GENOMIC_RE.fullmatch(requested_variant)
        ):
            compact_match = _COMPACT_GENOMIC_RE.fullmatch(requested_variant)
            formatter_variant = requested_variant
            if compact_match:
                formatter_variant = "{chrom}-{position}-{ref}-{alt}".format(
                    chrom=compact_match.group("chrom").removeprefix("chr"),
                    position=compact_match.group("position"),
                    ref=compact_match.group("ref"),
                    alt=compact_match.group("alt"),
                )
            formatter_args = {
                "variant_description": formatter_variant,
                "genome_build": genome_build,
            }
            formatter_call = self._call(
                "VariantValidator_format_genomic_to_transcripts",
                formatter_args,
                "identity",
            )
            calls.append(formatter_call)
            normalization["formatter_candidates"] = _formatted_transcript_candidates(
                formatter_call.result
            )
            selected = _select_formatted_transcript(formatter_call.result)
            if selected is None:
                return failed_identity("mane_transcript_unverified")
            selected_transcript = selected["reference"]
            canonical_variant = selected["t_hgvs"]
            if (
                requested_gene
                and selected["gene"]
                and _normalize_text(requested_gene) != _normalize_text(selected["gene"])
            ):
                return failed_identity("gene_identity_mismatch")
            normalization.update(
                {
                    "transcript_source": "VariantValidator_format_genomic_to_transcripts",
                    "transcript_selection": {
                        "reference": selected_transcript,
                        "mane_select": True,
                    },
                    "formatter_input": formatter_variant,
                    "canonical_hgvs": canonical_variant,
                }
            )
        elif _RSID_RE.fullmatch(requested_variant):
            recoder_features, rsid_resolver = self._resolve_rsid_features(
                requested_variant, genome_build, calls
            )
            normalization["rsid_resolver"] = rsid_resolver
            normalization["recoder_candidates"] = list(
                recoder_features.get("allele_candidates") or []
            )
            hgvsc_candidates = [
                str(value)
                for value in recoder_features.get("hgvsc_candidates") or []
                if ":c." in str(value)
            ]
            if selected_transcript:
                # Honor a caller-supplied transcript by selecting its HGVS
                # from the recoder candidates rather than the default pick.
                transcript_matches = list(
                    dict.fromkeys(
                        value
                        for value in hgvsc_candidates
                        if _normalize_text(_transcript_accession(value))
                        == _normalize_text(selected_transcript)
                    )
                )
                if not transcript_matches:
                    return failed_identity("transcript_identity_mismatch")
                if len(transcript_matches) > 1:
                    # The transcript alone does not disambiguate a
                    # multi-allelic rsID; the caller must supply the full HGVS.
                    normalization["allele_alternatives"] = transcript_matches
                    normalization["resolution_reason"] = (
                        "rsid_maps_to_multiple_alleles_on_the_selected_transcript"
                    )
                    return failed_identity("ambiguous_rsid_allele")
                canonical_variant = transcript_matches[0]
            else:
                # VariantValidator validates RefSeq transcripts only; the
                # recoder's first pick may be an Ensembl transcript. Prefer the
                # gene's MANE transcript when one can be resolved.
                mane_reference = ""
                if requested_gene:
                    resolver_call = self._call(
                        "VariantValidator_gene2transcripts",
                        {
                            "gene_symbol": requested_gene,
                            "transcript_set": "mane",
                            "genome_build": genome_build,
                        },
                        "identity",
                    )
                    calls.append(resolver_call)
                    normalization["transcript_candidates"] = _transcript_candidates(
                        resolver_call.result, requested_gene
                    )
                    selected = _select_mane_transcript(
                        resolver_call.result, requested_gene
                    )
                    if selected is not None:
                        mane_reference = str(selected["reference"])
                        normalization["transcript_selection"] = {
                            "reference": mane_reference,
                            "mane_select": selected["mane_select"],
                            "mane_plus_clinical": selected["mane_plus_clinical"],
                        }
                if mane_reference:
                    # One rsID may carry several alleles on the SAME transcript
                    # (e.g. rs104894531: NM_000303.3:c.669C>T and c.669C>G).
                    # Never collapse them silently; fail closed with the
                    # alternatives preserved for the caller to disambiguate.
                    mane_matches = list(
                        dict.fromkeys(
                            value
                            for value in hgvsc_candidates
                            if _normalize_text(_transcript_accession(value))
                            == _normalize_text(mane_reference)
                        )
                    )
                    if len(mane_matches) > 1:
                        normalization["allele_alternatives"] = mane_matches
                        normalization["resolution_reason"] = (
                            "rsid_maps_to_multiple_alleles_on_the_selected_transcript"
                        )
                        return failed_identity("ambiguous_rsid_allele")
                    canonical_variant = mane_matches[0] if mane_matches else ""
                else:
                    refseq_candidates = [
                        value
                        for value in hgvsc_candidates
                        if _transcript_accession(value).startswith("NM_")
                    ]
                    canonical_variant = (
                        refseq_candidates[0] if len(refseq_candidates) == 1 else ""
                    )
            if not canonical_variant:
                return failed_identity("variant_recoder_unverified")
            matching_alleles = [
                allele
                for allele in recoder_features.get("allele_candidates") or []
                if isinstance(allele, dict)
                and canonical_variant in set(allele.get("hgvsc") or [])
                and len(allele.get("hgvsg") or []) == 1
            ]
            if len(matching_alleles) != 1:
                return failed_identity("ambiguous_genomic_allele")
            normalization["selected_genomic_allele"] = matching_alleles[0]["hgvsg"][0]
            selected_transcript = _transcript_accession(canonical_variant)
            normalization.update(
                {
                    "transcript_source": "EnsemblVEP_variant_recoder",
                    "canonical_hgvs": canonical_variant,
                }
            )

        canonical_transcript = _transcript_accession(canonical_variant)
        if (
            selected_transcript
            and canonical_transcript
            and _normalize_text(selected_transcript)
            != _normalize_text(canonical_transcript)
        ):
            return failed_identity("transcript_identity_mismatch")
        if not selected_transcript:
            selected_transcript = canonical_transcript
        validator_args = {
            "variant_description": canonical_variant,
            "genome_build": genome_build,
            "select_transcripts": selected_transcript
            or _transcript_accession(canonical_variant)
            or "all",
        }
        validator_call = self._call(
            "VariantValidator_validate_variant",
            validator_args,
            "identity",
        )
        calls.append(validator_call)

        if not _RSID_RE.fullmatch(requested_variant):
            recoder_call = self._call(
                "EnsemblVEP_variant_recoder",
                {"variant_id": canonical_variant},
                "identity",
            )
            calls.append(recoder_call)
            recoder_observed = result_identity(_features_for_call(recoder_call))
            if recoder_call.status != "success" or not has_variant_identity(
                recoder_observed
            ):
                # The Ensembl recoder is a single point of failure; VEP
                # annotation provides an independent second identity source.
                # Prefer the VariantValidator-confirmed genomic HGVS so the
                # fallback observes the exact same genomic allele.
                validator_features = next(
                    (
                        _features_for_call(call)
                        for call in calls
                        if call.tool_name == "VariantValidator_validate_variant"
                        and call.status == "success"
                    ),
                    {},
                )
                calls.append(
                    self._call(
                        "EnsemblVEP_annotate_hgvs",
                        {
                            "hgvs_notation": str(
                                validator_features.get("hgvs_g") or canonical_variant
                            )
                        },
                        "identity",
                    )
                )

        identity: dict[str, Any] = {
            "hgvs_c": canonical_variant if ":c." in canonical_variant else "",
            "hgvs_g": canonical_variant if ":g." in canonical_variant else "",
            "build": genome_build,
            "gene": requested_gene or gene.strip(),
            "transcript": selected_transcript,
            "input_variant": requested_variant,
            "normalization": normalization,
        }
        observed_identities: list[dict[str, Any]] = []
        observed_calls: list[tuple[SourceCall, dict[str, Any]]] = []
        for call in calls:
            if call.status != "success":
                continue
            features = _features_for_call(call)
            if genome_build == "GRCh37" and features.get("hgvs_g_grch37"):
                features["hgvs_g"] = features["hgvs_g_grch37"]
                coordinates_grch37 = features.get("coordinates_grch37")
                if isinstance(coordinates_grch37, dict):
                    features.update(coordinates_grch37)
                features["build"] = "GRCh37"
            observed = result_identity(features)
            if observed:
                observed_identities.append(observed)
                observed_calls.append((call, observed))
            for key in (
                "validated_hgvs_c",
                "hgvs_c",
                "hgvs_g",
                "hgvs_p",
                "rsid",
                "gene",
                "transcript",
                "consequence",
                "build",
                "assembly",
                "variation_id",
                "clinvar_variation_id",
                "hgvs_g_grch37",
                "coordinates_grch37",
            ):
                if features.get(key) and key not in {
                    "build",
                    "assembly",
                    "genome_build",
                }:
                    identity[key] = (
                        coordinates(features[key])
                        if key == "coordinates_grch37"
                        and isinstance(features[key], dict)
                        else features[key]
                    )
            coords = coordinates(features)
            if coords:
                identity["coordinates"] = coords
        if "rsid" not in identity:
            match = re.search(r"\brs\d+\b", variant, re.IGNORECASE)
            if match:
                identity["rsid"] = match.group(0)
        conflicts = any(
            _identity_conflicts(left, right)
            for index, left in enumerate(observed_identities)
            for right in observed_identities[index + 1 :]
        ) or any(
            (
                observed.get("build")
                or observed.get("assembly")
                or observed.get("genome_build")
            )
            and not build_matches(identity, observed)
            for observed in observed_identities
        )
        positive_identities = [
            observed
            for observed in observed_identities
            if has_variant_identity(observed)
        ]
        if len(positive_identities) > 1:
            connected = {0}
            frontier = [0]
            while frontier:
                left_index = frontier.pop()
                for right_index, right in enumerate(positive_identities):
                    if right_index in connected:
                        continue
                    if _identities_share_variant(
                        positive_identities[left_index], right
                    ):
                        connected.add(right_index)
                        frontier.append(right_index)
            if len(connected) != len(positive_identities):
                conflicts = True
        requested_gene_key = _normalize_text(requested_gene)
        if requested_gene_key and any(
            observed.get("gene")
            and _normalize_text(observed["gene"]) != requested_gene_key
            for observed in observed_identities
        ):
            conflicts = True
        selected_transcript_key = _normalize_text(selected_transcript)
        if selected_transcript_key and any(
            observed.get("transcript")
            and _normalize_text(observed["transcript"]) != selected_transcript_key
            for observed in observed_identities
        ):
            conflicts = True
        transcript_selection = normalization.get("transcript_selection")
        transcript_selection = (
            transcript_selection if isinstance(transcript_selection, dict) else {}
        )
        if (
            len(positive_identities) >= 2
            and not conflicts
            and requested_gene
            and selected_transcript
            and transcript_selection.get("mane_select") is not True
        ):
            mane_call = self._call(
                "VariantValidator_gene2transcripts",
                {
                    "gene_symbol": requested_gene,
                    "transcript_set": "mane",
                    "genome_build": genome_build,
                },
                "identity",
            )
            calls.append(mane_call)
            normalization["transcript_candidates"] = _transcript_candidates(
                mane_call.result,
                requested_gene,
            )
            selected_mane = _select_mane_transcript(mane_call.result, requested_gene)
            mane_matches = bool(
                selected_mane
                and selected_mane.get("mane_select") is True
                and _normalize_text(selected_mane.get("reference"))
                == _normalize_text(selected_transcript)
            )
            normalization["transcript_selection"] = {
                "reference": selected_transcript,
                "mane_select": mane_matches,
                "mane_plus_clinical": bool(
                    selected_mane
                    and selected_mane.get("mane_plus_clinical") is True
                    and _normalize_text(selected_mane.get("reference"))
                    == _normalize_text(selected_transcript)
                ),
                "verification_source": "VariantValidator_gene2transcripts",
            }
        normalization["identity_calls"] = [
            {
                "tool": call.tool_name,
                "status": call.status,
                "arguments": dict(call.arguments or {}),
                "raw_result_hash": _stable_payload_hash(
                    call.result if call.result is not None else {"error": call.error}
                ),
                "provider_version": provider_version(_features_for_call(call)),
            }
            for call in calls
        ]
        normalization["validated_hgvs_c"] = identity.get("validated_hgvs_c")
        if identity.get("hgvs_g_grch37"):
            normalization["grch37_projection"] = {
                "hgvs_g": identity.get("hgvs_g_grch37"),
                "coordinates": identity.get("coordinates_grch37"),
                "build": "GRCh37",
                "source": "VariantValidator_validate_variant",
            }
        normalization["vep_hgvs_c"] = next(
            (
                observed.get("hgvs_c") or observed.get("validated_hgvs_c")
                for call, observed in observed_calls
                if call.tool_name == "EnsemblVEP_variant_recoder"
            ),
            None,
        )
        selected_candidate = {
            "hgvs_c": identity.get("validated_hgvs_c") or identity.get("hgvs_c"),
            "hgvs_g": identity.get("hgvs_g"),
            "transcript": selected_transcript,
            "reason": "unique_cross_provider_identity",
        }
        normalization["selected_candidate"] = selected_candidate
        excluded: list[dict[str, Any]] = []
        selected_hgvsc = {
            str(identity.get("validated_hgvs_c") or ""),
            str(identity.get("hgvs_c") or ""),
        }
        selected_hgvsc.discard("")
        for candidate in normalization.get("recoder_candidates") or []:
            if not isinstance(candidate, dict) or not selected_hgvsc.intersection(
                {str(value) for value in candidate.get("hgvsc") or []}
            ):
                excluded.append(
                    {
                        "candidate_type": "allele",
                        "candidate": candidate,
                        "reason": "not_selected_by_unique_transcript_and_allele_match",
                    }
                )
        for kind, key in (
            ("transcript", "transcript_candidates"),
            ("projection", "formatter_candidates"),
        ):
            for candidate in normalization.get(key) or []:
                reference = (
                    str(candidate.get("reference") or "")
                    if isinstance(candidate, dict)
                    else ""
                )
                if _normalize_text(reference) != _normalize_text(selected_transcript):
                    excluded.append(
                        {
                            "candidate_type": kind,
                            "candidate": candidate,
                            "reason": "not_selected_by_mane_and_cross_provider_match",
                        }
                    )
        normalization["excluded_candidates"] = excluded
        identity["identity_verified"] = len(positive_identities) >= 2 and not conflicts
        identity["transcript"] = selected_transcript
        identity["normalization"] = normalization
        if conflicts:
            normalization["error"] = "provider_identity_conflict"
            identity["identity_error"] = "provider_identity_conflict"
            identity["identity_conflict"] = True
        return calls, identity

    def _source_specs(
        self,
        arguments: dict[str, Any],
        identity: dict[str, Any],
    ) -> list[tuple[str, dict[str, Any], str]]:
        myvariant_id = _myvariant_id_from_hgvs_g(
            str(identity.get("hgvs_g_grch37") or "")
        )
        gene = str(arguments.get("gene") or identity.get("gene") or "")
        build = str(identity.get("build") or "GRCh38")
        gnomad_dataset = "gnomad_r2_1" if build == "GRCh37" else "gnomad_r4"
        splice_genome = "37" if build == "GRCh37" else "38"
        specs: list[tuple[str, dict[str, Any], str]] = []
        if myvariant_id:
            specs.extend(
                [
                    ("MyVariant_get_metadata", {"source": "dbnsfp"}, "computational"),
                    (
                        "MyVariant_get_pathogenicity_scores",
                        {"variant_id": myvariant_id},
                        "computational",
                    ),
                ]
            )
        clinvar_variation_id = str(
            identity.get("clinvar_variation_id") or identity.get("variation_id") or ""
        )
        if clinvar_variation_id.isdecimal():
            specs.insert(
                0,
                (
                    "ClinVar_get_clinical_significance",
                    {"variant_id": clinvar_variation_id},
                    "source_assertion",
                ),
            )
        coords = identity.get("coordinates")
        if isinstance(coords, dict):
            variant_id = (
                f"{coords['chr']}-{coords['pos']}-{coords['ref']}-{coords['alt']}"
            )
            specs.extend(
                [
                    (
                        "gnomad_get_variant",
                        {"variant_id": variant_id, "dataset": gnomad_dataset},
                        "population",
                    ),
                    (
                        "gnomad_get_variant_populations",
                        {"variant_id": variant_id, "dataset": gnomad_dataset},
                        "population",
                    ),
                    (
                        "gnomad_get_site_callability",
                        {
                            "chrom": str(coords["chr"]),
                            "position": int(coords["pos"]),
                            "reference_genome": str(identity.get("build") or "GRCh38"),
                            "dataset": gnomad_dataset,
                        },
                        "population",
                    ),
                ]
            )
        if isinstance(coords, dict) and all(
            str(coords.get(key) or "") for key in ("chr", "pos", "ref", "alt")
        ):
            splice_variant = (
                f"{coords['chr']}-{coords['pos']}-{coords['ref']}-{coords['alt']}"
            )
            specs.append(
                (
                    "SpliceAI_predict_splice",
                    {
                        "variant": splice_variant,
                        "genome": splice_genome,
                        "distance": 500,
                        "mask": False,
                    },
                    "computational",
                )
            )
        if gene:
            canonical_variant = str(
                identity.get("validated_hgvs_c")
                or identity.get("hgvs_c")
                or arguments["variant"]
            )
            specs.extend(
                [
                    ("ClinGen_search_gene_validity", {"gene": gene}, "disease_context"),
                    (
                        "ClinGen_get_dosage_sensitivity",
                        {"gene": gene, "include_regions": False},
                        "disease_context",
                    ),
                    (
                        "ClinGen_get_actionability_adult",
                        {"gene": gene},
                        "disease_context",
                    ),
                    (
                        "ClinGen_get_actionability_pediatric",
                        {"gene": gene},
                        "disease_context",
                    ),
                    (
                        "ClinGen_get_variant_classifications",
                        {"gene": gene, "variant": canonical_variant},
                        "source_assertion",
                    ),
                    (
                        "gnomad_get_constraint",
                        {"gene_symbol": gene, "dataset": gnomad_dataset},
                        "functional",
                    ),
                ]
            )
            aliases = _variant_literature_aliases(identity, arguments)
            search_aliases = list(
                dict.fromkeys([*aliases["exact"], *aliases["equivalent"]])
            )
            if search_aliases:
                alias_expression = " OR ".join(f'"{alias}"' for alias in search_aliases)
                query = f"{gene} AND ({alias_expression})"
                specs.extend(
                    [
                        (
                            "LitVar_search_variants",
                            {"query": query},
                            "literature",
                        ),
                        (
                            "PubMed_search_articles",
                            {
                                "query": query,
                                "include_abstract": True,
                                "max_results": 50,
                            },
                            "literature",
                        ),
                        (
                            "EuropePMC_search_articles",
                            {
                                "query": query,
                                "require_has_ft": False,
                                "enrich_missing_abstract": True,
                                "extract_terms_from_fulltext": [
                                    *search_aliases,
                                    gene,
                                    "functional assay",
                                    "de novo",
                                    "segregation",
                                ],
                                "limit": 100,
                            },
                            "literature",
                        ),
                    ]
                )
                specs.extend(
                    (
                        "PubTator3_LiteratureSearch",
                        {
                            "query": query,
                            "page": page,
                            "page_size": 10,
                            "limit": 10,
                        },
                        "literature",
                    )
                    for page in range(5)
                )
            rsid = str(identity.get("rsid") or "")
            if rsid:
                specs.append(
                    (
                        "LitVar_get_variant_publications",
                        {"rsid": rsid, "max": 50},
                        "literature",
                    )
                )
        specs.extend(_hpo_query_specs(arguments))
        unique_specs: list[tuple[str, dict[str, Any], str]] = []
        seen_specs: set[str] = set()
        for name, params, category in specs:
            fingerprint = json.dumps(
                [name, params, category], sort_keys=True, separators=(",", ":")
            )
            if fingerprint in seen_specs:
                continue
            seen_specs.add(fingerprint)
            unique_specs.append((name, params, category))
        return unique_specs

    @staticmethod
    def _rsid_consequence_fallback_allowed(identity: dict[str, Any]) -> bool:
        normalization = identity.get("normalization")
        normalization = normalization if isinstance(normalization, dict) else {}
        return bool(
            identity.get("identity_verified") is True
            and not identity.get("identity_conflict")
            and identity.get("rsid")
            and normalization.get("selected_genomic_allele")
            and not normalization.get("allele_alternatives")
        )

    def _consequence_calls(
        self, identity: dict[str, Any]
    ) -> tuple[list[SourceCall], dict[str, Any]]:
        """Collect every applicable identity-bound consequence source."""
        transcript_hgvs = str(
            identity.get("validated_hgvs_c") or identity.get("hgvs_c") or ""
        )
        transcript = str(identity.get("transcript") or "")
        if transcript_hgvs.startswith("c.") and transcript:
            transcript_hgvs = f"{transcript}:{transcript_hgvs}"

        specs: list[tuple[str, str, dict[str, Any]]] = []
        if transcript_hgvs:
            specs.append(
                (
                    "selected_transcript_hgvs",
                    "EnsemblVEP_annotate_hgvs",
                    {"hgvs_notation": transcript_hgvs},
                )
            )
        genomic_hgvs = str(identity.get("hgvs_g") or "")
        if genomic_hgvs and genomic_hgvs != transcript_hgvs:
            specs.append(
                (
                    "genomic_hgvs",
                    "EnsemblVEP_annotate_hgvs",
                    {"hgvs_notation": genomic_hgvs},
                )
            )
        if self._rsid_consequence_fallback_allowed(identity):
            specs.append(
                (
                    "rsid_single_allele",
                    "EnsemblVEP_annotate_rsid",
                    {"variant_id": str(identity["rsid"])},
                )
            )

        coords = identity.get("coordinates")
        coords = coords if isinstance(coords, dict) else {}
        if all(
            coords.get(key) not in (None, "") for key in ("chr", "pos", "ref", "alt")
        ):
            chrom = str(coords["chr"]).removeprefix("chr")
            position = int(coords["pos"])
            ref = str(coords["ref"])
            alt = str(coords["alt"])
            end = position + max(len(ref), 1) - 1
            variant_dash = f"{chrom}-{position}-{ref}-{alt}"
            variant_underscore = f"{chrom}_{position}_{ref}_{alt}"
            specs.extend(
                [
                    (
                        "vep_region",
                        "ensembl_vep_region",
                        {
                            "species": "human",
                            "region": f"{chrom}:{position}-{end}",
                            "allele": alt,
                        },
                    ),
                    (
                        "variantvalidator_all_transcripts",
                        "VariantValidator_format_genomic_to_transcripts",
                        {
                            "variant_description": str(
                                identity.get("hgvs_g") or variant_dash
                            ),
                            "genome_build": str(identity.get("build") or "GRCh38"),
                        },
                    ),
                    (
                        "opentargets_variant",
                        "OpenTargets_get_variant_info",
                        {"variantId": variant_underscore},
                    ),
                    (
                        "opentargets_transcripts",
                        "OpenTargets_get_variant_transcript_consequences",
                        {"variantId": variant_underscore},
                    ),
                ]
            )
            if str(identity.get("build") or "GRCh38") == "GRCh38":
                specs.append(
                    (
                        "favor_grch38",
                        "FAVOR_annotate_variant",
                        {"variant": variant_dash},
                    )
                )
        protvar_variant = _protvar_variant(identity)
        if protvar_variant:
            specs.append(
                (
                    "protvar_protein",
                    "ProtVar_map_variant",
                    {"variant": protvar_variant},
                )
            )
        if transcript_hgvs:
            specs.append(
                (
                    "mutalyzer_transcript_hgvs",
                    "Mutalyzer_normalize_variant",
                    {"variant": transcript_hgvs},
                )
            )
        hgvs_g_grch37 = str(identity.get("hgvs_g_grch37") or "")
        if hgvs_g_grch37:
            specs.append(
                (
                    "genomenexus_grch37",
                    "GenomeNexus_annotate_variant",
                    {"hgvsg": hgvs_g_grch37},
                )
            )
        rsid = str(identity.get("rsid") or "")
        if self._rsid_consequence_fallback_allowed(identity) and rsid:
            specs.extend(
                [
                    (
                        "genomenexus_rsid",
                        "GenomeNexus_annotate_dbsnp",
                        {"rsid": rsid},
                    ),
                    (
                        "gprofiler_rsid",
                        "gProfiler_annotate_snps",
                        {"snp_list": rsid, "organism": "hsapiens"},
                    ),
                ]
            )

        unique_specs: list[tuple[str, str, dict[str, Any]]] = []
        seen_specs: set[str] = set()
        for representation, tool_name, arguments in specs:
            fingerprint = json.dumps(
                [tool_name, arguments], sort_keys=True, separators=(",", ":")
            )
            if fingerprint in seen_specs:
                continue
            seen_specs.add(fingerprint)
            unique_specs.append((representation, tool_name, arguments))

        calls: list[SourceCall] = []
        if self.tooluniverse is None:
            calls = [
                self._call(tool_name, arguments, "consequence")
                for _, tool_name, arguments in unique_specs
            ]
        else:
            try:
                results = self.provider_executor.call_many(
                    [
                        {"name": tool_name, "arguments": arguments}
                        for _, tool_name, arguments in unique_specs
                    ],
                    max_workers=min(max(len(unique_specs), 1), 8),
                )
            except Exception as exc:
                calls = [
                    SourceCall(
                        tool_name,
                        "consequence",
                        "failed",
                        error=str(exc),
                        arguments=arguments,
                    )
                    for _, tool_name, arguments in unique_specs
                ]
            else:
                calls = [
                    SourceCall(
                        tool_name,
                        "consequence",
                        _status(result),
                        result=result,
                        arguments=arguments,
                    )
                    for (_, tool_name, arguments), result in zip(
                        unique_specs, results, strict=True
                    )
                ]
        facts = self._source_facts(calls, identity)
        observations = consequence_observations(identity, facts)
        resolution = resolve_consequence_observations(identity, observations)
        attempted = [
            {
                "representation": representation,
                "tool_name": tool_name,
                "arguments": dict(arguments),
                "query_status": call.status,
                "outcome": (
                    "provider_unavailable"
                    if call.status not in {"success", "no_hit"}
                    else "queried"
                ),
            }
            for (representation, tool_name, arguments), call in zip(
                unique_specs, calls, strict=True
            )
        ]
        status = str(resolution.get("status") or "unavailable")
        diagnostics: dict[str, Any] = {
            "annotation_status": status,
            "attempted_representations": attempted,
            "annotation_reason": str(
                resolution.get("reason") or "consequence_annotation_empty"
            ),
            "selected_source_fact_id": next(
                iter(resolution.get("selected_source_fact_ids") or []), ""
            ),
            "resolution": resolution,
        }
        return calls, diagnostics

    @staticmethod
    def _profile_from_facts(
        identity: dict[str, Any],
        source_facts: dict[str, SourceFact],
        diagnostics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        annotation = dict(diagnostics or {})
        observations = consequence_observations(identity, source_facts)
        resolution = resolve_consequence_observations(identity, observations)
        profile_features = profile_features_from_resolution(resolution)
        profile = build_consequence_profile(
            identity,
            profile_features,
            source_fact_ids=list(resolution.get("selected_source_fact_ids") or []),
        )
        clean_observations = [
            {key: value for key, value in row.items() if not key.startswith("_")}
            for row in observations
        ]
        profile.update(
            {
                "annotation_status": resolution.get(
                    "status", annotation.get("annotation_status", "unavailable")
                ),
                "attempted_representations": list(
                    annotation.get("attempted_representations") or []
                ),
                "annotation_reason": resolution.get(
                    "reason",
                    annotation.get("annotation_reason", "consequence_annotation_empty"),
                ),
                "observations": clean_observations,
                "selected_provider": (
                    (resolution.get("selected_observation") or {}).get("provider")
                    if isinstance(resolution.get("selected_observation"), dict)
                    else None
                ),
                "selected_source_fact_ids": list(
                    resolution.get("selected_source_fact_ids") or []
                ),
                "corroborating_source_fact_ids": list(
                    resolution.get("corroborating_source_fact_ids") or []
                ),
                "provider_failures": list(resolution.get("failures") or []),
                "provider_conflicts": list(resolution.get("conflicts") or []),
                "resolution_reason": resolution.get("reason"),
                "transcript_mapping": dict(resolution.get("transcript_mapping") or {}),
                "selected_observation": resolution.get("selected_observation"),
                "missing_requirements": (
                    []
                    if resolution.get("status") == "resolved"
                    else ["identity-bound selected-transcript consequence"]
                ),
            }
        )
        return profile

    @staticmethod
    def _pm1_cspec_contract(rule_context: dict[str, Any]) -> dict[str, Any] | None:
        contract = rule_context.get("executable_contract")
        criteria = contract.get("criteria") if isinstance(contract, dict) else None
        pm1 = criteria.get("PM1") if isinstance(criteria, dict) else None
        return pm1 if isinstance(pm1, dict) else None

    @staticmethod
    def _select_protein_mapping(
        features: dict[str, Any],
        *,
        gene: str,
        profile: dict[str, Any],
        protein_accession_hint: str,
    ) -> dict[str, Any]:
        expected_ref, expected_position, expected_alt = _protein_change(
            profile.get("hgvs_p")
        )
        expected_position = expected_position or _position(
            profile.get("protein_position")
        )
        protein_effect = str(profile.get("protein_effect") or "")
        missing_identity = not gene or expected_position is None
        missing_missense_change = protein_effect == "missense" and not (
            expected_ref and expected_alt
        )
        if missing_identity or missing_missense_change:
            return {
                "status": "unavailable",
                "selected": None,
                "candidates": [],
                "protein_accession_hint": protein_accession_hint,
                "reason": "verified_gene_and_protein_position_required",
            }
        candidates: list[dict[str, Any]] = []
        for candidate in features.get("protein_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            if _normalize_text(candidate.get("gene")) != _normalize_text(gene):
                continue
            if candidate.get("taxid") not in (None, "", 9606, "9606"):
                continue
            start = _position(candidate.get("protein_position_start"))
            end = _position(candidate.get("protein_position_end")) or start
            if expected_position is not None and not (
                start is not None
                and end is not None
                and start <= expected_position <= end
            ):
                continue
            observed_ref = _amino_acid(candidate.get("wild_type"))
            observed_alt = _amino_acid(candidate.get("alternative_sequence"))
            if expected_ref and observed_ref != expected_ref:
                continue
            if expected_alt and observed_alt != expected_alt:
                continue
            if protein_accession_hint and _normalize_text(
                candidate.get("protein_accession")
            ) != _normalize_text(protein_accession_hint):
                continue
            candidates.append(dict(candidate))
        unique = {
            (
                str(row.get("protein_accession") or ""),
                _position(row.get("protein_position_start")),
                _position(row.get("protein_position_end")),
            ): row
            for row in candidates
            if row.get("protein_accession")
        }
        # EBI Proteins returns isoform/TrEMBL entries alongside the reviewed
        # canonical UniProt protein. Residue numbering contracts are written
        # against the canonical accession, so prefer the bare reviewed entry
        # (no A0A TrEMBL prefix, no -N isoform suffix) when exactly one exists.
        canonical = [
            row
            for row in unique.values()
            if not str(row.get("protein_accession") or "").startswith("A0A")
            and "-" not in str(row.get("protein_accession") or "")
        ]
        selected = (
            canonical[0]
            if len(canonical) == 1
            else next(iter(unique.values()))
            if len(unique) == 1
            else None
        )
        return {
            "status": "resolved"
            if selected is not None
            else "ambiguous"
            if unique
            else "unavailable",
            "selected": selected,
            "candidates": list(unique.values()),
            "protein_accession_hint": protein_accession_hint,
        }

    def _protein_context_calls(
        self,
        arguments: dict[str, Any],
        identity: dict[str, Any],
        profile: dict[str, Any],
        rule_context: dict[str, Any],
    ) -> tuple[list[SourceCall], dict[str, Any]]:
        pm1_contract = self._pm1_cspec_contract(rule_context)
        applicability = consequence_applicability(
            "PM1", profile, cspec_criterion=pm1_contract
        )
        pvs1_applicable = (
            consequence_applicability("PVS1", profile)["status"] == "applicable"
        )
        protein_relevant = bool(
            profile.get("hgvs_p")
            or profile.get("protein_position")
            or profile.get("protein_effect")
            in {"missense", "lof", "inframe", "stop_lost"}
        )
        if (
            applicability["status"] != "applicable"
            and not pvs1_applicable
            and not protein_relevant
            or not identity.get("hgvs_g")
        ):
            return [], {
                "status": "not_applicable",
                "candidates": [],
                "selected": None,
            }
        mapping_call = self._call(
            "EBIProteins_get_variation_by_hgvs",
            {"hgvs": str(identity["hgvs_g"])},
            "protein_context",
        )
        mapping = self._select_protein_mapping(
            _features_for_call(mapping_call),
            gene=str(arguments.get("gene") or identity.get("gene") or ""),
            profile=profile,
            protein_accession_hint=str(arguments.get("protein_accession") or ""),
        )
        calls = [mapping_call]
        selected = mapping.get("selected")
        if not isinstance(selected, dict):
            return calls, mapping
        accession = str(selected.get("protein_accession") or "")
        calls.extend(
            [
                self._call(
                    "EBIProteins_get_features",
                    {"accession": accession, "category": "DOMAINS_AND_SITES"},
                    "protein_context",
                ),
                self._call(
                    "InterPro_get_entries_for_protein",
                    {"accession": accession},
                    "protein_context",
                ),
                self._call(
                    "UniProt_get_entry_by_accession",
                    {"accession": accession, "compact": False},
                    "protein_context",
                ),
            ]
        )
        if profile.get("protein_effect") == "missense" and profile.get("hgvs_p"):
            provider_arguments = {"accession": accession, "disease_only": False}
            variation_call = self._call(
                "EBIProteins_get_variation",
                provider_arguments,
                "prior_variant_candidates",
            )
            variation_call.arguments = {
                **provider_arguments,
                "_acmg_target_hgvs_p": profile.get("hgvs_p"),
            }
            calls.append(variation_call)
        return calls, mapping

    @staticmethod
    def _prior_variant_candidates(
        source_facts: dict[str, SourceFact],
    ) -> list[dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        for fact in source_facts.values():
            if (
                fact.tool_name != "EBIProteins_get_variation"
                or not fact.identity_verified
            ):
                continue
            for row in fact.features.get("same_residue_candidates") or []:
                if (
                    not isinstance(row, dict)
                    or row.get("germline_compatible") is not True
                ):
                    continue
                candidate = dict(row)
                candidate["source_fact_id"] = fact.fact_id
                key = str(candidate.get("prior_variant_identity") or "")
                if key:
                    candidates[key] = candidate
        return sorted(
            candidates.values(), key=lambda row: str(row["prior_variant_identity"])
        )

    def _prior_variant_literature_calls(
        self,
        candidates: list[dict[str, Any]],
        *,
        gene: str,
    ) -> list[SourceCall]:
        """Search literature for same-residue leads without treating labels as evidence."""
        calls: list[SourceCall] = []
        for candidate in candidates:
            identity = str(candidate.get("prior_variant_identity") or "")
            if not identity:
                continue
            query = f'{gene} AND "{identity}"' if gene else f'"{identity}"'
            specs = (
                (
                    "PubMed_search_articles",
                    {"query": query, "include_abstract": True, "max_results": 50},
                ),
                (
                    "EuropePMC_search_articles",
                    {
                        "query": query,
                        "require_has_ft": False,
                        "enrich_missing_abstract": True,
                        "extract_terms_from_fulltext": [identity, gene],
                        "limit": 100,
                    },
                ),
            )
            for tool_name, provider_arguments in specs:
                call = self._call(tool_name, provider_arguments, "literature")
                call.arguments = {
                    **provider_arguments,
                    "_acmg_fact_types": ["prior_variant"],
                    "_acmg_prior_variant_candidates": [candidate],
                }
                calls.append(call)
        return calls

    @staticmethod
    def _harvest_rsid_from_calls(
        calls: list[SourceCall], identity: dict[str, Any]
    ) -> str:
        """Harvest an rsID from identity-consistent provider calls in this run."""
        expected = identity.get("coordinates")
        for call in calls:
            if (
                call.tool_name
                not in {
                    "gnomad_get_variant",
                    "gnomad_get_variant_populations",
                    "EnsemblVEP_annotate_rsid",
                    "EnsemblVEP_annotate_hgvs",
                }
                or call.status != "success"
            ):
                continue
            features = _features_for_call(call)
            rsid = str(features.get("rsid") or "")
            if not rsid:
                continue
            if not isinstance(expected, dict):
                return rsid
            observed = coordinates(features)
            if observed and observed == expected:
                return rsid
        return ""

    def _resolve_clinvar_calls(
        self,
        arguments: dict[str, Any],
        identity: dict[str, Any],
        harvested_rsid: str = "",
    ) -> tuple[list[SourceCall], str | None]:
        """Resolve ClinVar through ordered, identity-bound representations."""
        gene = str(arguments.get("gene") or identity.get("gene") or "")
        rsid = str(identity.get("rsid") or "") or harvested_rsid
        expected_c = str(
            identity.get("validated_hgvs_c")
            or identity.get("hgvs_c")
            or arguments.get("variant")
            or ""
        )
        expected_p = str(identity.get("hgvs_p") or "")

        searches: list[dict[str, Any]] = []
        if rsid:
            searches.append({"rsid": rsid, "max_results": 50})
        variant_names = [value for value in (expected_c, expected_p) if value]
        if variant_names:
            targeted: dict[str, Any] = {
                "variant_name": variant_names,
                "max_results": 50,
            }
            if gene:
                targeted["gene"] = gene
            searches.append(targeted)
        if gene:
            fallback: dict[str, Any] = {"gene": gene, "max_results": 100}
            disease = str(arguments.get("disease") or "")
            if disease and not re.fullmatch(r"[A-Za-z]+:\d+", disease.strip()):
                fallback["condition"] = disease
            searches.append(fallback)
        if not searches:
            return [], None

        calls: list[SourceCall] = []
        seen: set[str] = set()
        for search_args in searches:
            fingerprint = json.dumps(search_args, sort_keys=True, default=str)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            search_call = self._call(
                "ClinVar_search_variants", search_args, "source_assertion"
            )
            calls.append(search_call)
            if search_call.status != "success":
                return calls, None
            variation_id = _clinvar_variation_id_from_search(
                search_call.result, expected_c, gene
            )
            if variation_id:
                calls.append(
                    self._call(
                        "ClinVar_get_clinical_significance",
                        {"variant_id": variation_id},
                        "source_assertion",
                    )
                )
                return calls, variation_id

            features = _reviewable_features(search_call.result)
            variants = features.get("variants")
            total_count = _integer(features, "total_count")
            if isinstance(variants, list) and variants:
                # A non-empty representation that does not uniquely match the
                # selected allele is an identity mismatch or ambiguity. Do not
                # search a broader representation to bypass it.
                return calls, None
            if total_count not in (None, 0):
                # The provider reported hits but supplied no rows that can be
                # identity checked.
                return calls, None
        return calls, None

    def _collect_sources(
        self,
        arguments: dict[str, Any],
        identity: dict[str, Any],
    ) -> list[SourceCall]:
        specs = self._source_specs(arguments, identity)
        calls: list[SourceCall] = []
        clinvar_resolved = any(
            name == "ClinVar_get_clinical_significance" for name, _, _ in specs
        )
        if self.tooluniverse is None:
            calls.extend(
                self._call(name, args, category) for name, args, category in specs
            )
        else:
            try:
                raw_results = self.provider_executor.call_many(
                    [{"name": name, "arguments": args} for name, args, _ in specs],
                    max_workers=min(max(len(specs), 1), 8),
                )
            except Exception as exc:
                calls.extend(
                    SourceCall(name, category, "failed", error=str(exc), arguments=args)
                    for name, args, category in specs
                )
            else:
                calls.extend(
                    SourceCall(
                        name,
                        category,
                        _status(result),
                        result=result,
                        arguments=args,
                    )
                    for (name, args, category), result in zip(
                        specs, raw_results, strict=True
                    )
                )
        if not clinvar_resolved:
            resolution_calls, resolved_id = self._resolve_clinvar_calls(
                arguments,
                identity,
                harvested_rsid=self._harvest_rsid_from_calls(calls, identity),
            )
            calls.extend(resolution_calls)
            clinvar_resolved = resolved_id is not None
        if not clinvar_resolved:
            calls.append(
                SourceCall(
                    "ClinVar_get_clinical_significance",
                    "source_assertion",
                    "no_hit",
                    error="ClinVar Variation ID could not be resolved from normalized identity",
                )
            )
        return calls

    @staticmethod
    def _source_facts(
        calls: list[SourceCall], identity: dict[str, Any]
    ) -> dict[str, SourceFact]:
        facts: dict[str, SourceFact] = {}
        myvariant_metadata = next(
            (
                _features_for_call(call)
                for call in calls
                if call.tool_name == "MyVariant_get_metadata"
                and call.status == "success"
            ),
            {},
        )
        query_identity = {
            key: identity.get(key)
            for key in (
                "input_variant",
                "hgvs_c",
                "validated_hgvs_c",
                "hgvs_g",
                "rsid",
                "gene",
                "transcript",
                "build",
                "coordinates",
                "variation_id",
                "clinvar_variation_id",
                "normalization",
            )
            if identity.get(key)
        }
        for call in calls:
            features = _features_for_call(call)
            call_arguments = call.arguments or {}
            if call.tool_name in {
                "ClinGen_get_dosage_sensitivity",
                "ClinGen_get_actionability_adult",
                "ClinGen_get_actionability_pediatric",
                "ClinGen_get_variant_classifications",
            }:
                features.setdefault("gene", call_arguments.get("gene"))
            elif call.tool_name.startswith("HPO_"):
                features.setdefault("hpo_term", call_arguments.get("term_id"))
                features.setdefault("query", call_arguments.get("query"))
            elif call.tool_name in {
                "LitVar_search_variants",
                "LitVar_get_variant_publications",
                "EuropePMC_search_articles",
                "PubMed_search_articles",
                "PubTator3_LiteratureSearch",
            }:
                features.setdefault(
                    "query",
                    call_arguments.get("query") or call_arguments.get("rsid"),
                )
            expected_identity = identity
            if call.tool_name == "MyVariant_get_pathogenicity_scores":
                if myvariant_metadata.get("version"):
                    features["provider_version"] = str(myvariant_metadata["version"])
                    features["dbnsfp_version"] = str(myvariant_metadata["version"])
                expected_identity = {
                    "hgvs_g": identity.get("hgvs_g_grch37"),
                    "coordinates": identity.get("coordinates_grch37"),
                    "gene": identity.get("gene"),
                    "build": "GRCh37",
                }
            elif call.tool_name in {
                "GenomeNexus_annotate_variant",
                "GenomeNexus_annotate_dbsnp",
            }:
                expected_identity = {
                    "hgvs_g": identity.get("hgvs_g_grch37"),
                    "coordinates": identity.get("coordinates_grch37"),
                    "rsid": identity.get("rsid"),
                    "gene": identity.get("gene"),
                    "build": "GRCh37",
                }
            elif call.tool_name == "SpliceAI_predict_splice":
                features = prepare_spliceai_features(
                    features,
                    identity,
                    call.arguments,
                )
            elif call.tool_name == "EBIProteins_get_variation_by_hgvs":
                expected_identity = {
                    "hgvs_g": identity.get("hgvs_g"),
                    "gene": identity.get("gene"),
                }
            elif call.tool_name in {
                "EBIProteins_get_features",
                "EBIProteins_get_variation",
                "InterPro_get_entries_for_protein",
                "UniProt_get_entry_by_accession",
            }:
                expected_identity = {
                    "protein_accession": (call.arguments or {}).get("accession")
                }
                if call.tool_name == "EBIProteins_get_variation":
                    features["same_residue_candidates"] = _same_residue_candidates(
                        features,
                        call_arguments.get("_acmg_target_hgvs_p")
                        or identity.get("hgvs_p"),
                    )
                    features.pop("protein_variants", None)
            elif call.tool_name.startswith("HPO_"):
                expected_identity = {"hpo_term": (call.arguments or {}).get("term_id")}
            elif call.tool_name == "ensembl_lookup_gene":
                expected_identity = {
                    "ensembl_transcript_id": (call.arguments or {}).get("gene_id")
                }
            elif call.tool_name == "gnomad_get_region_variants":
                expected_identity = {"coordinates": identity.get("coordinates")}
            if call.tool_name in {
                "gnomad_get_variant",
                "gnomad_get_variant_populations",
                "gnomad_get_site_callability",
            } and isinstance(call.arguments, dict):
                features.setdefault("dataset", call.arguments.get("dataset"))
            observed_identity, identity_verified, ready = source_fact_ready(
                call.tool_name,
                features,
                expected_identity,
            )
            if not identity_verified and _identity_conflicts(
                expected_identity, observed_identity
            ):
                features["identity_conflict"] = True
            fact_id, sandbox_hash = _stable_source_fact_id(
                call.tool_name,
                {**query_identity, "arguments": call.arguments or {}},
                call.result if call.result is not None else {"error": call.error},
            )
            sandbox = (
                call.result.get("source_lead_sandbox")
                if isinstance(call.result, dict)
                else None
            )
            source_provenance = (
                sandbox.get("source_provenance") if isinstance(sandbox, dict) else None
            )
            source_provenance = (
                source_provenance if isinstance(source_provenance, dict) else {}
            )
            raw_hash = str(source_provenance.get("raw_result_hash") or sandbox_hash)
            provenance = [
                str(value)
                for value in (
                    source_provenance.get("source_url"),
                    source_provenance.get("raw_result_hash"),
                )
                if isinstance(value, str) and value
            ]
            if call.error:
                provenance.append(call.error)
            facts[fact_id] = SourceFact(
                fact_id=fact_id,
                tool_name=call.tool_name,
                status=call.status,
                query_identity=(
                    {key: value for key, value in expected_identity.items() if value}
                    if call.tool_name
                    in {
                        "MyVariant_get_pathogenicity_scores",
                        "EBIProteins_get_variation_by_hgvs",
                        "EBIProteins_get_features",
                        "EBIProteins_get_variation",
                        "InterPro_get_entries_for_protein",
                        "UniProt_get_entry_by_accession",
                    }
                    else query_identity
                ),
                result_identity=observed_identity,
                identity_verified=identity_verified,
                features=features,
                raw_result_hash=raw_hash,
                provider_version=provider_version(features),
                request_arguments=dict(call.arguments or {}),
                provenance=tuple(provenance),
                assessment_ready=call.status == "success"
                and identity_verified
                and ready,
            )
        return facts

    def _literature_annotation_calls(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[SourceCall]:
        """Prefill entities for exact/equivalent papers without interpreting them."""
        specs: list[tuple[str, dict[str, Any], str]] = []
        for candidate in candidates:
            if candidate.get("match_class") not in {
                "exact_variant_match",
                "equivalent_variant_match",
                "provider_linked_variant_match",
            }:
                continue
            pmid = str(candidate.get("pmid") or "").strip()
            pmcid = str(candidate.get("pmcid") or "").strip()
            if pmid:
                specs.append(
                    (
                        "PubTator3_get_annotations",
                        {
                            "pmids": pmid,
                            "concepts": "gene,disease,mutation",
                        },
                        "literature",
                    )
                )
            if pmid or pmcid:
                specs.append(
                    (
                        "EPMC_get_text_mined_annotations",
                        {"pmcid": pmcid} if pmcid else {"pmid": pmid},
                        "literature",
                    )
                )
        deduplicated: list[tuple[str, dict[str, Any], str]] = []
        seen: set[str] = set()
        for tool_name, arguments, category in specs:
            key = json.dumps(
                [tool_name, arguments], sort_keys=True, separators=(",", ":")
            )
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append((tool_name, arguments, category))
        if not deduplicated:
            return []
        try:
            results = self.provider_executor.call_many(
                [
                    {"name": tool_name, "arguments": arguments}
                    for tool_name, arguments, _category in deduplicated
                ],
                max_workers=min(len(deduplicated), 8),
            )
        except Exception as exc:
            return [
                SourceCall(
                    tool_name,
                    category,
                    "failed",
                    error=str(exc),
                    arguments=arguments,
                )
                for tool_name, arguments, category in deduplicated
            ]
        return [
            SourceCall(
                tool_name,
                category,
                _status(result),
                result=result,
                arguments=arguments,
            )
            for (tool_name, arguments, category), result in zip(
                deduplicated, results, strict=True
            )
        ]

    def _document_backed_literature_proposals(
        self, arguments: dict[str, Any], identity: dict[str, Any]
    ) -> tuple[dict[str, SourceFact], list[SourceCall]]:
        """Verify LLM-extracted facts against ToolUniverse full-text responses."""
        submitted, input_error = _literature_input(arguments)
        if input_error:
            return {}, []
        if not isinstance(submitted, list):
            return {}, []
        facts: dict[str, SourceFact] = {}
        calls: list[SourceCall] = []
        expected_variant = str(
            identity.get("validated_hgvs_c")
            or identity.get("hgvs_c")
            or arguments.get("variant")
            or ""
        )
        expected_gene = str(arguments.get("gene") or identity.get("gene") or "")
        documents: dict[tuple[str, str], SourceCall] = {}
        for item in submitted:
            if not isinstance(item, dict):
                continue
            pmcid = str(item.get("pmcid") or "").strip()
            pmid = str(item.get("pmid") or "").strip()
            key = (pmcid, pmid)
            if not (pmcid or pmid):
                continue
            if key not in documents:
                primary_call = self._call(
                    "EuropePMC_get_full_text",
                    (
                        {"pmcid": pmcid, "max_section_chars": 500000}
                        if pmcid
                        else {"pmid": pmid, "max_section_chars": 500000}
                    ),
                    "literature",
                )
                calls.append(primary_call)
                document_call = primary_call
                if primary_call.status != "success":
                    fallback_arguments = (
                        {
                            "pmcid": pmcid,
                            "output_format": "text",
                            "max_chars": 2000000,
                        }
                        if pmcid
                        else {
                            "source_db": "MED",
                            "article_id": pmid,
                            "output_format": "text",
                            "max_chars": 2000000,
                        }
                    )
                    fallback_call = self._call(
                        "EuropePMC_get_fulltext",
                        fallback_arguments,
                        "literature",
                    )
                    calls.append(fallback_call)
                    if fallback_call.status == "success":
                        document_call = fallback_call
                documents[key] = document_call

        for item in submitted:
            if not isinstance(item, dict):
                continue
            pmcid = str(item.get("pmcid") or "").strip()
            pmid = str(item.get("pmid") or "").strip()
            document_call = documents.get((pmcid, pmid))
            document_result = (
                dict(document_call.result)
                if document_call and isinstance(document_call.result, dict)
                else document_call.result
                if document_call
                else None
            )
            if isinstance(document_result, dict):
                metadata = document_result.get("metadata")
                metadata = dict(metadata) if isinstance(metadata, dict) else {}
                if pmid:
                    metadata.setdefault("pmid", pmid)
                if pmcid:
                    metadata.setdefault("pmcid", pmcid)
                document_result["metadata"] = metadata
            document_provenance = _document_provenance(document_result)
            verification = verify_document_fact(
                item,
                document_result,
                expected_variant=expected_variant,
                expected_gene=expected_gene,
                expected_disease=str(arguments.get("disease") or ""),
                expected_inheritance=str(
                    arguments.get("inheritance")
                    or arguments.get("inheritance_mode")
                    or ""
                ),
            )
            submitted_manifest = item.get("reading_manifest")
            submitted_manifest = (
                dict(submitted_manifest) if isinstance(submitted_manifest, dict) else {}
            )
            submitted_reading_status = str(
                submitted_manifest.get("status")
                or submitted_manifest.get("reading_status")
                or "unspecified"
            )
            provider_raw_hash = _stable_payload_hash(
                document_call.result
                if document_call and document_call.result is not None
                else item
            )
            document_hash = document_content_hash(document_result) or provider_raw_hash
            fact_id = (
                "acmg-document-fact:v2:"
                + hashlib.sha256(
                    (
                        f"{verification['fact_id']}:{document_hash}:"
                        f"{item.get('review_request_id') or ''}"
                    ).encode()
                ).hexdigest()[:24]
            )
            submitted_document_hash = str(item.get("document_hash") or "")
            document_hash_matches = (
                not submitted_document_hash
                or submitted_document_hash == document_hash
            )
            if not document_hash_matches:
                verification["validation_errors"].append(
                    "submitted document_hash does not match re-fetched document"
                )
                verification["anchor_status"] = "mismatch"
            if submitted_reading_status in {"abstract_only", "unavailable"}:
                verification["validation_errors"].append(
                    "full-text reading status is not eligible for evidence mapping"
                )
            if document_provenance["truncated"]:
                verification["validation_errors"].append(
                    "retrieved full text was truncated; strict validation is unavailable"
                )
            is_bound = (
                verification["verified"] is True
                and document_hash_matches
                and submitted_reading_status not in {"abstract_only", "unavailable"}
                and not document_provenance["truncated"]
            )
            host_verified = False
            if is_bound and callable(self.review_assertion_verifier):
                assertion = {
                    "fact_id": fact_id,
                    "submitted_fact_id": verification["submitted_fact_id"],
                    "fact_payload_hash": _stable_payload_hash(verification),
                    "document_raw_hash": provider_raw_hash,
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "locator": verification["locator"],
                }
                try:
                    host_verified = bool(self.review_assertion_verifier(assertion))
                except Exception:
                    host_verified = False
            verification_level = (
                "host_verified"
                if host_verified
                else str(verification["verification_level"])
            )
            reading_manifest = {
                "pmid": pmid,
                "pmcid": pmcid,
                "doi": str(item.get("doi") or ""),
                "document_hash": document_hash,
                "status": submitted_reading_status,
                "sections_read": list(submitted_manifest.get("sections_read") or []),
                "tables_read": list(
                    submitted_manifest.get("tables_read")
                    or submitted_manifest.get("tables_reviewed")
                    or []
                ),
                "figures_read": list(
                    submitted_manifest.get("figures_read")
                    or submitted_manifest.get("figures_reviewed")
                    or []
                ),
                "supplements_read": list(
                    submitted_manifest.get("supplements_read")
                    or submitted_manifest.get("supplements_reviewed")
                    or []
                ),
                "variant_match_locations": list(
                    submitted_manifest.get("variant_match_locations") or []
                ),
                "limitations": list(
                    submitted_manifest.get("limitations")
                    or submitted_manifest.get("missing_sections")
                    or []
                ),
            }
            if document_provenance["truncated"]:
                if reading_manifest["status"] == "complete":
                    reading_manifest["status"] = "partial"
                reading_manifest["limitations"].append(
                    "Provider response was truncated for sections: "
                    + ", ".join(document_provenance["truncated_sections"] or ["unknown"])
                )
            if reading_manifest["status"] == "unspecified":
                reading_manifest["limitations"].append(
                    "host LLM did not submit a reading manifest"
                )
            facts[fact_id] = SourceFact(
                fact_id=fact_id,
                tool_name="EuropePMC_get_full_text",
                status="success" if is_bound else "unverified",
                query_identity={"variant": expected_variant, "gene": expected_gene},
                result_identity={
                    "hgvs_c": expected_variant,
                    "gene": expected_gene,
                },
                identity_verified=bool(is_bound),
                features={
                    "fact_id": fact_id,
                    "submitted_fact_id": verification["submitted_fact_id"],
                    "fact_type": verification["fact_type"],
                    "values": verification["values"],
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "extractor": verification["extractor"],
                    "field_excerpts": verification["field_excerpts"],
                    "verification_level": verification_level,
                    "validation_errors": verification["validation_errors"],
                    "anchor_status": verification["anchor_status"],
                    "semantic_status": verification["semantic_status"],
                    "field_semantics": verification["field_semantics"],
                    "criterion": verification["criterion"],
                    "suggested_strength": verification["suggested_strength"],
                    "interpretation": verification["interpretation"],
                    "confidence": verification["confidence"],
                    "questions": verification["questions"],
                    "document_hash": document_hash,
                    "provider_raw_result_hash": provider_raw_hash,
                    "submitted_document_hash": submitted_document_hash,
                    "document_source_tool": (
                        document_call.tool_name if document_call else ""
                    ),
                    "document_source": document_provenance["source"],
                    "document_format": document_provenance["format"],
                    "document_url": document_provenance["url"],
                    "retrieval_trace": document_provenance["retrieval_trace"],
                    "document_truncated": document_provenance["truncated"],
                    "truncated_sections": document_provenance[
                        "truncated_sections"
                    ],
                    "review_request_id": str(item.get("review_request_id") or ""),
                    "proposal_hash": _stable_payload_hash(item),
                    "reading_manifest": reading_manifest,
                },
                raw_result_hash=provider_raw_hash,
                provider_version=document_provenance["source"]
                or "full-text source unavailable",
                request_arguments=dict(document_call.arguments or {})
                if document_call
                else {},
                provenance=(
                    pmid or pmcid,
                    str(verification["locator"]),
                    document_provenance["url"],
                    f"{verification['extractor'].get('name', '')}:{verification['extractor'].get('version', '')}",
                ),
                excerpt=str(verification["excerpt"]),
                locator=str(verification["locator"]),
                assessment_ready=bool(is_bound),
                verification_level=verification_level,
            )
        return facts, calls

    @staticmethod
    def _facts_for_tool(
        source_facts: dict[str, SourceFact], *tool_names: str
    ) -> list[SourceFact]:
        return [
            fact
            for fact in source_facts.values()
            if fact.tool_name in tool_names and fact.assessment_ready
        ]

    @staticmethod
    def _literature_proposal_cards(
        source_facts: dict[str, SourceFact],
        consequence_profile: dict[str, Any],
    ) -> list[EvidenceCard]:
        cards: list[EvidenceCard] = []
        for fact in source_facts.values():
            if fact.tool_name != "EuropePMC_get_full_text":
                continue
            fact_type = str(fact.features.get("fact_type") or "")
            if fact_type not in LITERATURE_FACT_CRITERIA:
                continue
            if fact_type in _SPECIALIZED_LITERATURE_FACTS:
                # These facts are consumed by their criterion-specific engines;
                # adding a second free-form LLM card would double count them.
                continue
            values = fact.features.get("values")
            values = dict(values) if isinstance(values, dict) else {}
            criterion, mapping_status = _mapped_literature_criterion(
                fact_type,
                values,
                str(fact.features.get("criterion") or ""),
            )
            suggested_strength = str(fact.features.get("suggested_strength") or "")
            strength = (
                suggested_strength
                if criterion
                and is_valid_strength_for_criterion(criterion, suggested_strength)
                else criterion
                if criterion and is_valid_strength_for_criterion(criterion, criterion)
                else ""
            )
            anchor_status = str(fact.features.get("anchor_status") or "unavailable")
            semantic_status = str(fact.features.get("semantic_status") or "unresolved")
            criterion_valid = criterion in ACMG_CRITERIA
            consequence = (
                consequence_applicability(criterion, consequence_profile)
                if criterion_valid
                else {"status": "requires_context", "reason": "criterion unmapped"}
            )
            strength_valid = criterion_valid and is_valid_strength_for_criterion(
                criterion, strength
            )
            requirements_met, mapping_missing = _literature_mapping_requirements_met(
                fact_type, values, criterion
            )
            hard_error = (
                anchor_status == "mismatch"
                or semantic_status == "contradicted"
                or not strength_valid
                or mapping_status == "unmapped"
                or consequence.get("status")
                in {"not_applicable", "deprecated", "ambiguous"}
            )
            source_backed_candidate = (
                not hard_error
                and criterion_valid
                and bool(fact.fact_id)
            )
            proposal_usable = (
                fact.assessment_ready
                and anchor_status == "verified"
                and semantic_status != "contradicted"
                and strength_valid
                and mapping_status != "unmapped"
                and requirements_met
                and consequence.get("status")
                not in {"not_applicable", "deprecated", "unavailable", "ambiguous"}
            )
            caveats: list[str] = []
            if anchor_status != "verified":
                caveats.append(
                    f"Literature source anchoring is {anchor_status}; proposal is a lead only."
                )
            if semantic_status == "unresolved":
                caveats.append(
                    "Some structured values could not be deterministically recovered "
                    "from the cited excerpts."
                )
            elif semantic_status == "contradicted":
                caveats.append(
                    "One or more submitted values contradict the cited excerpts."
                )
            document_truncated = fact.features.get("document_truncated") is True
            if document_truncated:
                caveats.append(
                    "The retrieved document was truncated; this proposal is excluded "
                    "from the validated subset."
                )
            if not criterion_valid:
                caveats.append(
                    "The fact could not be mapped to an allowed ACMG criterion."
                )
            elif not strength_valid:
                caveats.append(
                    "The proposed strength is not valid for the proposed criterion."
                )
            if consequence.get("status") not in {"applicable", "not_consequence_gated"}:
                caveats.append(str(consequence.get("reason") or ""))
            semantic_ids = [
                str(values.get(key) or "")
                for key in (
                    "case_id",
                    "family_id",
                    "cohort_id",
                    "assay_instance_id",
                    "prior_variant_identity",
                )
                if values.get(key)
            ]
            if not semantic_ids and fact.features.get("fact_id"):
                semantic_ids.append(str(fact.features["fact_id"]))
            llm_suggestion = {
                "criterion": fact.features.get("criterion"),
                "suggested_strength": fact.features.get("suggested_strength"),
                "interpretation": fact.features.get("interpretation"),
                "confidence": fact.features.get("confidence"),
                "questions": list(fact.features.get("questions") or []),
                "extractor": dict(fact.features.get("extractor") or {}),
            }
            cards.append(
                EvidenceCard(
                    criterion=criterion or "UNMAPPED",
                    strength=strength or "not_assessed",
                    assessment_status=(
                        "met"
                        if proposal_usable
                        else "indeterminate"
                        if source_backed_candidate
                        else "not_assessed"
                    ),
                    input_source="Host LLM literature proposal",
                    input_values={
                        **values,
                        "anchor_status": anchor_status,
                        "semantic_status": semantic_status,
                        "field_semantics": dict(
                            fact.features.get("field_semantics") or {}
                        ),
                        "interpretation": fact.features.get("interpretation"),
                        "confidence": fact.features.get("confidence"),
                        "questions": list(fact.features.get("questions") or []),
                        "extractor": dict(fact.features.get("extractor") or {}),
                        "fact_type": fact_type,
                        "locator": fact.locator,
                        "excerpt": fact.excerpt,
                    },
                    clinvar_rule_applied=(
                        "Host LLM interpretation mapped to ClinGen SVI for user review"
                    ),
                    overlay_validated=proposal_usable,
                    provenance_chain=[
                        "LLM proposal anchored to the named full-text locator; final "
                        "criterion adoption remains a user decision."
                    ],
                    source_pmid=str(fact.features.get("pmid") or "") or None,
                    source_pmids=[
                        str(value)
                        for value in (
                            fact.features.get("pmid"),
                            fact.features.get("pmcid"),
                        )
                        if value
                    ],
                    source_case_ids=semantic_ids,
                    source_fact_ids=[fact.fact_id],
                    suggested_criterion=criterion if source_backed_candidate else "",
                    suggested_strength=strength if source_backed_candidate else "",
                    proposal_origin="llm_literature",
                    proposal_status=(
                        "requires_user_review"
                        if source_backed_candidate
                        else "insufficient_information"
                    ),
                    rule_verification="generic_svi",
                    rule_mapping_status=mapping_status,
                    llm_suggestion=llm_suggestion,
                    caveats=caveats,
                    missing_requirements=(
                        []
                        if proposal_usable
                        else sorted(
                            {
                                *mapping_missing,
                                *(
                                    ["identity-bound full-text anchor"]
                                    if anchor_status != "verified"
                                    else []
                                ),
                                *(
                                    ["semantically verified extracted values"]
                                    if semantic_status == "unresolved"
                                    else []
                                ),
                                *(
                                    ["complete untruncated full-text retrieval"]
                                    if document_truncated
                                    else []
                                ),
                            }
                        )
                    ),
                    verification_status=(
                        "contradicted"
                        if semantic_status == "contradicted"
                        else "identity_mismatch"
                        if anchor_status == "mismatch"
                        else "source_unavailable"
                        if anchor_status == "unavailable"
                        else "verified"
                        if proposal_usable
                        else "unresolved"
                    ),
                )
            )
        return cards

    @staticmethod
    def _attach_literature_suggestions(
        cards: list[EvidenceCard],
        source_facts: dict[str, SourceFact],
    ) -> None:
        """Keep each LLM interpretation on its criterion-specific card."""
        for card in cards:
            suggestions: list[dict[str, Any]] = []
            for fact_id in card.source_fact_ids:
                fact = source_facts.get(fact_id)
                if (
                    fact is None
                    or fact.tool_name != "EuropePMC_get_full_text"
                    or not fact.features.get("interpretation")
                ):
                    continue
                suggestions.append(
                    {
                        "fact_type": fact.features.get("fact_type"),
                        "criterion": fact.features.get("criterion"),
                        "suggested_strength": fact.features.get("suggested_strength"),
                        "interpretation": fact.features.get("interpretation"),
                        "confidence": fact.features.get("confidence"),
                        "questions": list(fact.features.get("questions") or []),
                        "extractor": dict(fact.features.get("extractor") or {}),
                    }
                )
            if suggestions:
                card.llm_suggestion = {"items": suggestions}

    @staticmethod
    def _promote_cards(
        cards: list[EvidenceCard],
        source_fact_ids: list[str],
        allowed_criteria: set[str],
    ) -> list[EvidenceCard]:
        """Promote cards only when their source facts are verified."""
        for card in cards:
            if source_fact_ids:
                card.source_fact_ids = list(source_fact_ids)
            if card.criterion not in allowed_criteria:
                continue
            if source_fact_ids:
                card.overlay_validated = True
        return cards

    @staticmethod
    def _population_inputs(
        source_facts: dict[str, SourceFact],
        rule_context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], list[str]]:
        observation: dict[str, Any] = {}
        source = ""
        source_fact: SourceFact | None = None
        preferred_sources = (
            "gnomad_get_variant_populations",
            "gnomad_get_variant",
        )
        for tool_name in preferred_sources:
            for fact in source_facts.values():
                if fact.tool_name != tool_name or not fact.assessment_ready:
                    continue
                features = fact.features
                if _number(features, "AN", "an") is not None:
                    observation = features
                    source = tool_name
                    source_fact = fact
                    break
            if observation:
                break
        source_fact_ids = [source_fact.fact_id] if source_fact else []
        callability_metrics: dict[str, Any] = {}
        if source_fact:
            frequency_coordinates = source_fact.result_identity.get("coordinates")
            frequency_dataset = str(source_fact.features.get("dataset") or "")
            callset = str(source_fact.features.get("callset") or "")
            for fact in source_facts.values():
                if (
                    fact.tool_name != "gnomad_get_site_callability"
                    or not fact.assessment_ready
                    or str(fact.features.get("dataset") or "") != frequency_dataset
                    or not isinstance(frequency_coordinates, dict)
                ):
                    continue
                locus = fact.result_identity.get("locus")
                callsets = fact.features.get("callsets")
                if (
                    isinstance(locus, dict)
                    and locus.get("chr") == frequency_coordinates.get("chr")
                    and locus.get("pos") == frequency_coordinates.get("pos")
                    and isinstance(callsets, dict)
                    and isinstance(callsets.get(callset), dict)
                ):
                    source_fact_ids.append(fact.fact_id)
                    callability_metrics = dict(callsets[callset])
                    break
        executable_contract = (
            (rule_context or {}).get("executable_contract")
            if isinstance(rule_context, dict)
            else None
        )
        criteria_contracts = (
            executable_contract.get("criteria")
            if isinstance(executable_contract, dict)
            and isinstance(executable_contract.get("criteria"), dict)
            else {}
        )
        pm2_contract = criteria_contracts.get("PM2") or {}
        bs1_contract = criteria_contracts.get("BS1") or {}
        ba1_contract = criteria_contracts.get("BA1") or {}
        maximum_credible_af = _number(
            bs1_contract if isinstance(bs1_contract, dict) else {},
            "maximum_credible_af",
        ) or _number(
            pm2_contract if isinstance(pm2_contract, dict) else {},
            "maximum_credible_af",
        )
        return (
            {
                "gnomad_af_global": _number(observation, "AF", "af", "af_global"),
                "gnomad_af_popmax": _number(observation, "popmax", "af_popmax"),
                "gnomad_ac": _integer(observation, "AC", "ac"),
                "gnomad_an": _integer(observation, "AN", "an"),
                "coverage_adequate": None,
                "callability_available": len(source_fact_ids) > 1,
                "maximum_credible_af": maximum_credible_af,
                "ba1_exception": (
                    ba1_contract.get("exception") is True
                    if isinstance(ba1_contract, dict)
                    else False
                ),
                "ba1_exception_verified": bool(ba1_contract),
                "population_source": source,
                "population_details": {
                    key: observation.get(key)
                    for key in (
                        "dataset",
                        "release",
                        "population_version",
                        "callset",
                        "homozygote_count",
                        "homozygote_count_global",
                        "populations",
                        "ancestry_frequencies",
                    )
                    if observation.get(key) is not None
                },
                "callability_metrics": callability_metrics,
                "rule_override": executable_contract,
            },
            source_fact_ids,
        )

    @staticmethod
    def _computational_inputs(
        source_facts: dict[str, SourceFact],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        predictor_features: dict[str, Any] = {}
        predictor_audit_features: dict[str, Any] = {}
        splice_features: dict[str, Any] = {}
        splice_audit_features: dict[str, Any] = {}
        for fact in source_facts.values():
            if fact.tool_name == "MyVariant_get_pathogenicity_scores":
                predictor_audit_features = fact.features
                if fact.assessment_ready:
                    predictor_features = fact.features
            elif fact.tool_name == "SpliceAI_predict_splice":
                splice_audit_features = fact.features
                if fact.assessment_ready:
                    splice_features = fact.features
        predictor_scores = dict(predictor_audit_features.get("predictor_audit") or {})
        for key in ("revel_score", "cadd_phred"):
            if predictor_audit_features.get(key) is not None:
                predictor_scores[key] = predictor_audit_features[key]
        if isinstance(predictor_audit_features.get("predictor_concordance"), dict):
            predictor_scores["predictor_concordance"] = dict(
                predictor_audit_features["predictor_concordance"]
            )
        splice_run_metadata = splice_audit_features.get("spliceai_run_metadata")
        splice_run_metadata = (
            dict(splice_run_metadata) if isinstance(splice_run_metadata, dict) else {}
        )
        splice_scores = splice_run_metadata.get("selected_score_row")
        splice_scores = dict(splice_scores) if isinstance(splice_scores, dict) else {}
        audit_spliceai_profile = bind_spliceai_site(
            splice_audit_features.get("spliceai_profile"),
            profile.get("canonical_site_type"),
            hgvs_c=profile.get("hgvs_c"),
            variant_position=profile.get("genomic_position"),
        )
        spliceai_profile = bind_spliceai_site(
            splice_features.get("spliceai_profile"),
            profile.get("canonical_site_type"),
            hgvs_c=profile.get("hgvs_c"),
            variant_position=profile.get("genomic_position"),
        )
        max_delta = (
            _number(spliceai_profile, "max_delta_score")
            if spliceai_profile.get("status") == "resolved"
            else None
        )
        splice_applicable = (
            bool(splice_features) and profile.get("status") == "resolved"
        )
        splice_context = {
            "applicable": splice_applicable,
            "derived_from": (
                "VariantValidator and EnsemblVEP consequence"
                if profile.get("source_fact_ids")
                else ""
            ),
            "splice_position": profile.get("splice_position"),
            "splice_positions": list(profile.get("splice_positions") or []),
            "splice_class": profile.get("splice_class"),
            "canonical_site_type": profile.get("canonical_site_type"),
            "canonical_motif_effect": profile.get("canonical_motif_effect"),
            "canonical_motif_sequence_status": profile.get(
                "canonical_motif_sequence_status"
            ),
            "hgvs_operation": profile.get("hgvs_operation"),
            "hgvs_c": profile.get("hgvs_c"),
            "genomic_position": profile.get("genomic_position"),
            "consequence_terms": list(profile.get("selected_transcript_terms") or []),
            "transcript": profile.get("selected_transcript"),
            "protein_effect": profile.get("protein_effect"),
        }
        if splice_audit_features:
            predictor_scores["spliceai"] = {
                "scores": splice_audit_features.get("scores"),
                "profile": audit_spliceai_profile,
                "max_delta_score": audit_spliceai_profile.get("max_delta_score"),
                "provider_version": splice_audit_features.get("provider_version"),
                "run_metadata": splice_run_metadata,
            }
        return {
            "revel_score": _number(predictor_features, "revel_score", "revel"),
            "cadd_phred": _number(predictor_features, "cadd_phred", "cadd"),
            "spliceai_max_delta": max_delta,
            "spliceai_profile": spliceai_profile,
            "spliceai_scores": splice_scores if isinstance(splice_scores, dict) else {},
            "spliceai_run_metadata": (
                dict(splice_features.get("spliceai_run_metadata") or {})
                if isinstance(splice_features.get("spliceai_run_metadata"), dict)
                else {}
            ),
            "predictor_scores": predictor_scores,
            "splice_context": splice_context,
            "consequence_profile": dict(profile),
            "variant_type": str(profile.get("protein_effect") or ""),
        }

    @staticmethod
    def _clinical_inputs(source_facts: dict[str, SourceFact]) -> dict[str, Any]:
        de_novo = _literature_values(source_facts, "de_novo")
        pm3 = [
            *_literature_values(source_facts, "pm3"),
            *_literature_values(source_facts, "recessive_allelic"),
        ]
        return {
            "inheritance_mode": _shared_string(de_novo or pm3, "inheritance_mode"),
            "de_novo_probands": de_novo or None,
            "pm3_observations": pm3 or None,
            "pm3_frequency_eligible": _shared_bool(pm3, "pm3_frequency_eligible"),
        }

    @staticmethod
    def _selected_transcript_row(
        source_facts: dict[str, SourceFact], profile: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """Return the resolver-selected transcript row and its source fact id."""
        observation = profile.get("selected_observation")
        if isinstance(observation, dict):
            fact_id = str(observation.get("source_fact_id") or "")
            return (
                {
                    "gene": observation.get("gene"),
                    "transcript": observation.get("ensembl_transcript")
                    or observation.get("transcript"),
                    "mane_select": observation.get("mane_select")
                    or profile.get("selected_transcript"),
                    "hgvsc": observation.get("hgvs_c"),
                    "hgvsp": observation.get("hgvs_p"),
                    "consequence": list(observation.get("consequence_terms") or []),
                    "impact": observation.get("impact"),
                    "biotype": observation.get("biotype"),
                    "exon": observation.get("exon"),
                    "protein_start": observation.get("protein_position"),
                    "canonical": observation.get("canonical"),
                },
                fact_id,
            )
        selected_base = (
            str(profile.get("selected_transcript") or "").split(".", 1)[0].casefold()
        )
        for fact in ACMGEvidencePipeline._facts_for_tool(
            source_facts, "EnsemblVEP_annotate_hgvs", "EnsemblVEP_annotate_rsid"
        ):
            for row in fact.features.get("vep_transcript_candidates") or []:
                if not isinstance(row, dict):
                    continue
                candidates = {
                    str(row.get("transcript") or "").split(".", 1)[0].casefold(),
                    str(row.get("mane_select") or "").split(".", 1)[0].casefold(),
                }
                if selected_base and selected_base in candidates:
                    return dict(row), fact.fact_id
        return None, ""

    def _pvs1_context_calls(
        self,
        identity: dict[str, Any],
        profile: dict[str, Any],
        seed_facts: dict[str, SourceFact],
    ) -> list[SourceCall]:
        """Ensembl exon-structure call for the PVS1 exon-position facts."""
        if consequence_applicability("PVS1", profile)["status"] != "applicable":
            return []
        row, _fact_id = ACMGEvidencePipeline._selected_transcript_row(
            seed_facts, profile
        )
        if not row:
            return []
        enst = str(row.get("transcript") or "")
        exon = str(row.get("exon") or "")
        if not enst.upper().startswith("ENS") or "/" not in exon:
            return []
        return [
            self._call(
                "ensembl_lookup_gene",
                {"gene_id": enst, "expand": "1"},
                "functional",
            )
        ]

    def _pvs1_exon_lof_calls(
        self,
        identity: dict[str, Any],
        profile: dict[str, Any],
        source_facts: dict[str, SourceFact],
    ) -> list[SourceCall]:
        """gnomAD per-exon LoF-frequency call for the PVS1 frequent-LoF gate."""
        if consequence_applicability("PVS1", profile)["status"] != "applicable":
            return []
        build = str(identity.get("build") or "GRCh38")
        if build != "GRCh38":
            # Ensembl lookup coordinates are GRCh38; mixing builds would
            # misplace the exon window, so other builds skip this gate.
            return []
        row, _fact_id = self._selected_transcript_row(source_facts, profile)
        if not row:
            return []
        exon_text = str(row.get("exon") or "")
        exon_number, _, _total = exon_text.partition("/")
        try:
            rank = int(exon_number)
        except (TypeError, ValueError):
            return []
        lookup_facts = self._facts_for_tool(source_facts, "ensembl_lookup_gene")
        if not lookup_facts:
            return []
        exons = [
            exon
            for exon in lookup_facts[0].features.get("exons") or []
            if isinstance(exon, dict) and exon.get("rank") == rank
        ]
        if len(exons) != 1:
            return []
        exon = exons[0]
        chrom = str(exon.get("chrom") or identity.get("chr") or "").removeprefix("chr")
        coordinates = identity.get("coordinates")
        if not chrom and isinstance(coordinates, dict):
            chrom = str(coordinates.get("chr") or "").removeprefix("chr")
        try:
            start, stop = int(exon["start"]), int(exon["end"])
        except (KeyError, TypeError, ValueError):
            return []
        if not chrom or start > stop:
            return []
        return [
            self._call(
                "gnomad_get_region_variants",
                {
                    "chrom": chrom,
                    "start": start,
                    "stop": stop,
                    "dataset": "gnomad_r4",
                    "reference_genome": build,
                },
                "population",
            )
        ]

    @staticmethod
    def _pvs1_facts(
        profile: dict[str, Any],
        source_facts: dict[str, SourceFact],
    ) -> tuple[dict[str, Any], list[str]]:
        """Build machine-verifiable PVS1 facts from provider-verified facts."""
        facts: dict[str, Any] = {}
        fact_ids: list[str] = []
        matched, vep_fact_id = ACMGEvidencePipeline._selected_transcript_row(
            source_facts, profile
        )
        if matched is not None:
            facts["transcript"] = {
                "biotype": matched.get("biotype"),
                "exon": matched.get("exon"),
                "intron": matched.get("intron"),
                "mane_select": matched.get("mane_select"),
            }
            fact_ids.append(vep_fact_id)
        canonical_site_position = None
        exon_text = str((facts.get("transcript") or {}).get("exon") or "")
        exon_number_text, _, _exon_total = exon_text.partition("/")
        try:
            selected_exon_number = int(exon_number_text)
        except (TypeError, ValueError):
            selected_exon_number = None
        if selected_exon_number is not None:
            for lookup_fact in ACMGEvidencePipeline._facts_for_tool(
                source_facts, "ensembl_lookup_gene"
            ):
                exons = [
                    dict(exon)
                    for exon in lookup_fact.features.get("exons") or []
                    if isinstance(exon, dict)
                    and _position(exon.get("rank")) == selected_exon_number
                ]
                if len(exons) != 1:
                    continue
                exon = exons[0]
                try:
                    start = int(exon["start"])
                    end = int(exon["end"])
                    strand = int(exon["strand"])
                except (KeyError, TypeError, ValueError):
                    continue
                site_type = str(profile.get("canonical_site_type") or "")
                if site_type == "donor":
                    canonical_site_position = end if strand == 1 else start
                elif site_type == "acceptor":
                    canonical_site_position = start if strand == 1 else end
                if canonical_site_position is not None:
                    facts["transcript"].update(
                        {
                            "strand": strand,
                            "canonical_site_position": canonical_site_position,
                        }
                    )
                    fact_ids.append(lookup_fact.fact_id)
                break
        protein_length = None
        protein_length_fact_id = ""
        position = _position(profile.get("protein_position"))
        for fact in ACMGEvidencePipeline._facts_for_tool(
            source_facts, "EBIProteins_get_features"
        ):
            length = fact.features.get("sequence_length")
            if isinstance(length, (int, float)) and not isinstance(length, bool):
                protein_length = int(length)
                protein_length_fact_id = fact.fact_id
            if position is not None:
                overlaps = [
                    dict(feature)
                    for feature in fact.features.get("features") or []
                    if isinstance(feature, dict)
                    and _position(feature.get("position_end")) is not None
                    and _position(feature.get("position_end")) >= position
                ]
                if overlaps:
                    facts["critical_region"] = {
                        "overlapping_features": overlaps,
                        "source": "uniprot_features",
                    }
                    if fact.fact_id not in fact_ids:
                        fact_ids.append(fact.fact_id)
            break
        facts["protein"] = {
            "position": profile.get("protein_position"),
            "length": protein_length,
        }
        if protein_length_fact_id:
            fact_ids.append(protein_length_fact_id)
        for fact in ACMGEvidencePipeline._facts_for_tool(
            source_facts, "gnomad_get_region_variants"
        ):
            variants = [
                dict(variant)
                for variant in fact.features.get("variants") or []
                if isinstance(variant, dict)
            ][:50]
            facts["exon_context"] = {
                "lof_variants": variants,
                "source": "gnomad_region_variants",
            }
            fact_ids.append(fact.fact_id)
            break
        mechanism_facts = [
            fact
            for fact in source_facts.values()
            if fact.assessment_ready
            and fact.features.get("fact_type") in {"functional", "mechanism"}
            and fact.features.get("semantic_status") == "verified"
            and str(
                (fact.features.get("values") or {}).get("gene_disease_mechanism") or ""
            ).strip()
        ]
        if mechanism_facts:
            value = str(
                (mechanism_facts[0].features.get("values") or {}).get(
                    "gene_disease_mechanism"
                )
                or ""
            ).strip()
            facts["lof_mechanism"] = {"value": value, "source": "document_fact"}
            fact_ids.append(mechanism_facts[0].fact_id)
        else:
            validity_facts = ACMGEvidencePipeline._facts_for_tool(
                source_facts, "ClinGen_search_gene_validity"
            )
            constraint_facts = ACMGEvidencePipeline._facts_for_tool(
                source_facts,
                "gnomad_get_constraint",
            )
            if validity_facts or constraint_facts:
                curations = (
                    list(validity_facts[0].features.get("validity_curations") or [])
                    if validity_facts
                    else []
                )
                constraint = (
                    dict(constraint_facts[0].features) if constraint_facts else {}
                )
                facts["lof_mechanism"] = infer_mechanism_from_population_facts(
                    curations, constraint
                )
                fact_ids.extend(fact.fact_id for fact in validity_facts[:1])
                fact_ids.extend(fact.fact_id for fact in constraint_facts[:1])
        splice_facts = ACMGEvidencePipeline._facts_for_tool(
            source_facts, "SpliceAI_predict_splice"
        )
        if splice_facts:
            spliceai_profile = bind_spliceai_site(
                splice_facts[0].features.get("spliceai_profile"),
                profile.get("canonical_site_type"),
                hgvs_c=profile.get("hgvs_c"),
                variant_position=profile.get("genomic_position"),
                canonical_site_position=canonical_site_position,
            )
            if spliceai_profile.get("status") == "resolved":
                facts["spliceai_profile"] = spliceai_profile
                fact_ids.append(splice_facts[0].fact_id)
        return facts, fact_ids

    @staticmethod
    def _functional_inputs(
        profile: dict[str, Any],
        source_facts: dict[str, SourceFact],
        protein_mapping: dict[str, Any],
        rule_context: dict[str, Any],
        pvs1_facts: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        observations = _literature_values(source_facts, "functional")
        return {
            "variant_type": str(profile.get("protein_effect") or ""),
            "consequence_profile": dict(profile),
            "protein_context": ACMGEvidencePipeline._protein_context_inputs(
                source_facts, protein_mapping
            ),
            "pvs1_facts": dict(pvs1_facts) if isinstance(pvs1_facts, dict) else None,
            "rule_override": rule_context.get("executable_contract"),
            "functional_assays": observations or None,
        }

    @staticmethod
    def _protein_context_inputs(
        source_facts: dict[str, SourceFact], protein_mapping: dict[str, Any]
    ) -> dict[str, Any]:
        selected = protein_mapping.get("selected")
        selected = dict(selected) if isinstance(selected, dict) else None
        position = (
            _position(selected.get("protein_position_start"))
            if selected is not None
            else None
        )
        feature_fact = next(
            (
                fact
                for fact in source_facts.values()
                if fact.tool_name == "EBIProteins_get_features"
                and fact.assessment_ready
            ),
            None,
        )
        interpro_fact = next(
            (
                fact
                for fact in source_facts.values()
                if fact.tool_name == "InterPro_get_entries_for_protein"
                and fact.assessment_ready
            ),
            None,
        )
        features = (
            list(feature_fact.features.get("features") or [])
            if feature_fact is not None
            else []
        )
        overlaps = []
        for feature in features:
            if not isinstance(feature, dict) or position is None:
                continue
            start = _position(feature.get("position_start"))
            end = _position(feature.get("position_end")) or start
            if start is not None and end is not None and start <= position <= end:
                overlaps.append(dict(feature))
        return {
            "mapping_status": protein_mapping.get("status"),
            "selected_mapping": selected,
            "mapping_candidates": list(protein_mapping.get("candidates") or []),
            "protein_accession_hint": protein_mapping.get("protein_accession_hint"),
            "protein_position": position,
            "features": features,
            "overlapping_features": overlaps,
            "interpro_entries": (
                list(interpro_fact.features.get("interpro_entries") or [])
                if interpro_fact is not None
                else []
            ),
            "source_fact_ids": [
                fact.fact_id
                for fact in source_facts.values()
                if fact.tool_name
                in {
                    "EBIProteins_get_variation_by_hgvs",
                    "EBIProteins_get_features",
                    "InterPro_get_entries_for_protein",
                }
                and fact.assessment_ready
            ],
        }

    @staticmethod
    def _protein_length_repeat_cards(
        profile: dict[str, Any],
        source_facts: dict[str, SourceFact],
        protein_context: dict[str, Any],
    ) -> list[EvidenceCard]:
        """Create review-required PM4/BP3 proposals from identity-bound facts."""
        if protein_context.get("mapping_status") != "resolved":
            return []
        if profile.get("protein_effect") != "inframe" and "stop_lost" not in set(
            profile.get("selected_transcript_terms") or []
        ):
            return []
        feature_facts = [
            fact
            for fact in source_facts.values()
            if fact.tool_name == "EBIProteins_get_features" and fact.assessment_ready
        ]
        selected_fact_ids = [
            str(value) for value in profile.get("source_fact_ids") or [] if value
        ]
        if len(feature_facts) != 1 or not selected_fact_ids:
            return []
        overlaps = [
            dict(row)
            for row in protein_context.get("overlapping_features") or []
            if isinstance(row, dict)
        ]
        repeat_tokens = ("repeat", "low complexity", "low_complexity")
        functional_tokens = (
            "domain",
            "active site",
            "binding",
            "motif",
            "metal",
            "site",
            "catalytic",
        )

        def text(row: dict[str, Any]) -> str:
            return " ".join(
                str(row.get(key) or "") for key in ("type", "category", "description")
            ).casefold()

        repeat_overlaps = [
            row
            for row in overlaps
            if any(token in text(row) for token in repeat_tokens)
        ]
        functional_overlaps = [
            row
            for row in overlaps
            if any(token in text(row) for token in functional_tokens)
        ]
        source_fact_ids = list(
            dict.fromkeys([*selected_fact_ids, feature_facts[0].fact_id])
        )
        common = {
            "consequence_profile": {
                "protein_effect": profile.get("protein_effect"),
                "selected_transcript_terms": list(
                    profile.get("selected_transcript_terms") or []
                ),
                "hgvs_p": profile.get("hgvs_p"),
            },
            "selected_mapping": dict(protein_context.get("selected_mapping") or {}),
            "protein_position": protein_context.get("protein_position"),
            "repeat_overlaps": repeat_overlaps,
            "functional_overlaps": functional_overlaps,
        }
        if repeat_overlaps and not functional_overlaps:
            criterion = "BP3"
            rule_text = "ACMG/AMP 2015 BP3: in-frame change in a repetitive region without known function"
        elif not repeat_overlaps:
            criterion = "PM4"
            rule_text = (
                "ACMG/AMP 2015 PM4: protein length change outside a repeat region"
            )
        else:
            return []
        return [
            EvidenceCard(
                criterion=criterion,
                strength=criterion,
                assessment_status="met",
                input_source="Consequence resolver + EBI Proteins",
                input_values=common,
                clinvar_rule_applied=rule_text,
                overlay_validated=True,
                source_fact_ids=source_fact_ids,
                observed_facts={
                    **common,
                    "review_required": True,
                    "database_labels_used_as_evidence": False,
                },
                proposal_origin="external_lead",
                proposal_status="requires_user_review",
                rule_verification="generic_svi",
                rule_mapping_status="provider_review_required",
                caveats=[
                    "This is a provider-derived evidence proposal, not a final criterion adoption."
                ],
            )
        ]

    @staticmethod
    def _literature_inputs(
        arguments: dict[str, Any],
        identity: dict[str, Any],
        source_facts: dict[str, SourceFact],
    ) -> dict[str, Any]:
        values = {
            "case_control_facts": [
                {
                    **dict(fact.features.get("values") or {}),
                    "fact_id": fact.features.get("fact_id"),
                    "fact_type": fact.features.get("fact_type"),
                    "source_fact_id": fact.fact_id,
                    "assessment_ready": fact.assessment_ready,
                    "anchor_status": fact.features.get("anchor_status"),
                    "semantic_status": fact.features.get("semantic_status"),
                    "document_truncated": fact.features.get("document_truncated")
                    is True,
                    "truncated_sections": list(
                        fact.features.get("truncated_sections") or []
                    ),
                    "reading_manifest": dict(
                        fact.features.get("reading_manifest") or {}
                    ),
                    "pmid": fact.features.get("pmid"),
                    "pmcid": fact.features.get("pmcid"),
                    "locator": fact.locator,
                    "variant_identity": (fact.features.get("values") or {}).get(
                        "variant_identity"
                    ),
                    "gene": (fact.features.get("values") or {}).get("gene"),
                    "suggested_strength": fact.features.get("suggested_strength"),
                    "llm_suggestion": {
                        "criterion": fact.features.get("criterion"),
                        "suggested_strength": fact.features.get("suggested_strength"),
                        "interpretation": fact.features.get("interpretation"),
                        "confidence": fact.features.get("confidence"),
                        "questions": list(fact.features.get("questions") or []),
                        "extractor": dict(fact.features.get("extractor") or {}),
                    },
                }
                for fact in source_facts.values()
                if fact.tool_name == "EuropePMC_get_full_text"
                and fact.features.get("fact_type") in {"case_control", "case_series"}
            ]
        }
        values["expected_variant"] = str(
            identity.get("validated_hgvs_c") or identity.get("hgvs_c") or ""
        )
        values["expected_gene"] = str(
            arguments.get("gene") or identity.get("gene") or ""
        )
        return values

    @staticmethod
    def _coverage(
        calls: list[SourceCall],
        source_facts: dict[str, SourceFact],
        identity: dict[str, Any] | None = None,
        arguments: dict[str, Any] | None = None,
        consequence_profile: dict[str, Any] | None = None,
        rule_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        identity = identity or {}
        arguments = arguments or {}
        consequence_profile = consequence_profile or {}
        rule_context = rule_context or {}
        rows = []
        ready_by_category: dict[str, int] = {}
        for fact in source_facts.values():
            category = next(
                (call.category for call in calls if call.tool_name == fact.tool_name),
                "source_assertion",
            )
            if fact.assessment_ready:
                ready_by_category[category] = ready_by_category.get(category, 0) + 1
        has_coordinates = isinstance(identity.get("coordinates"), dict)
        has_gene = bool(arguments.get("gene") or identity.get("gene"))
        is_missense = consequence_profile.get("protein_effect") == "missense"
        pm1_applicable = (
            consequence_applicability(
                "PM1",
                consequence_profile,
                cspec_criterion=ACMGEvidencePipeline._pm1_cspec_contract(rule_context),
            )["status"]
            == "applicable"
        )
        required_tools: dict[str, list[set[str]]] = {
            "identity": [
                {"VariantValidator_validate_variant"},
                {
                    "EnsemblVEP_variant_recoder",
                    "EnsemblVEP_annotate_hgvs",
                    "EnsemblVEP_annotate_rsid",
                    "NCBIVariation_rsid_lookup",
                },
            ],
            "population": (
                [
                    {"gnomad_get_variant", "gnomad_get_variant_populations"},
                    {"gnomad_get_site_callability"},
                ]
                if has_coordinates
                else []
            ),
            "computational": (
                ([{"MyVariant_get_pathogenicity_scores"}] if is_missense else [])
                + ([{"SpliceAI_predict_splice"}] if has_coordinates else [])
            ),
            "consequence": [{"EnsemblVEP_annotate_hgvs", "EnsemblVEP_annotate_rsid"}],
            "protein_context": (
                [
                    {"EBIProteins_get_variation_by_hgvs"},
                    {"EBIProteins_get_features"},
                    {"InterPro_get_entries_for_protein"},
                    {"UniProt_get_entry_by_accession"},
                ]
                if pm1_applicable or bool(consequence_profile.get("hgvs_p"))
                else []
            ),
            "rule_context": ([{"ClinGen_search_cspec"}] if has_gene else []),
            "disease_context": (
                [
                    {"ClinGen_search_gene_validity"},
                    {"ClinGen_get_dosage_sensitivity"},
                    {"ClinGen_get_actionability_adult"},
                    {"ClinGen_get_actionability_pediatric"},
                ]
                if has_gene
                else []
            ),
            "functional": ([{"gnomad_get_constraint"}] if has_gene else []),
            "literature": (
                [
                    {"LitVar_search_variants"},
                    {"PubMed_search_articles"},
                    {"EuropePMC_search_articles"},
                ]
                if has_gene
                else []
            ),
            "phenotype_context": [
                {tool_name} for tool_name, _, _ in _hpo_query_specs(arguments)
            ],
        }
        for category in (
            "identity",
            "consequence",
            "population",
            "computational",
            "source_assertion",
            "literature",
            "disease_context",
            "rule_context",
            "functional",
            "protein_context",
            "phenotype_context",
        ):
            selected = [call for call in calls if call.category == category]
            groups = required_tools.get(category, [])
            required = bool(groups) or category == "identity"
            calls_by_name = {call.tool_name: call for call in selected}
            query_completed = (
                all(
                    any(
                        name in calls_by_name
                        and calls_by_name[name].status in {"success", "no_hit"}
                        for name in alternatives
                    )
                    for alternatives in groups
                )
                if groups
                else bool(selected) or not required
            )
            assessment_ready = (
                all(
                    any(
                        fact.tool_name in alternatives and fact.assessment_ready
                        for fact in source_facts.values()
                    )
                    for alternatives in groups
                )
                if groups
                else ready_by_category.get(category, 0) > 0
            )
            statuses = {call.status for call in selected}
            successful_required_result = any(
                any(
                    name in calls_by_name and calls_by_name[name].status == "success"
                    for name in alternatives
                )
                for alternatives in groups
            )
            if "success" in statuses:
                status = "success"
            elif "failed" in statuses:
                status = "failed"
            elif "unavailable" in statuses:
                status = "unavailable"
            elif selected:
                status = "no_hit"
            else:
                status = "not_applicable"
            rows.append(
                {
                    "source_category": category,
                    "required": required,
                    "query_status": status,
                    "query_completed": query_completed,
                    "queried_sources": [call.tool_name for call in selected],
                    "hit_count": sum(call.status == "success" for call in selected),
                    "assessment_ready": assessment_ready,
                    "source_fact_count": ready_by_category.get(category, 0),
                    "limitation_code": (
                        "required_provider_incomplete"
                        if required and not query_completed
                        else "provider_contract_malformed"
                        if required
                        and query_completed
                        and successful_required_result
                        and not assessment_ready
                        else ""
                    ),
                    "reason": (
                        "Literature search/full-text snippets are leads only; no structured "
                        "case, family, assay, or case-control facts were validated."
                        if status == "success" and category == "literature"
                        else f"{category} evidence sources returned reviewable data."
                        if status == "success"
                        else f"{category} evidence sources did not return reviewable data."
                    ),
                }
            )
        return rows

    @staticmethod
    def _source_assertions(
        calls: list[SourceCall], supplied: Any
    ) -> list[dict[str, Any]]:
        leads = []
        for call in calls:
            if call.category != "source_assertion" or call.status != "success":
                continue
            leads.append(
                {
                    "source_type": call.tool_name,
                    "reviewable_features": _features_for_call(call),
                    "quarantined_conclusions": _quarantined_conclusions(call.result),
                    "system_preview_eligible": False,
                    "notice": "Source assertion only; not automatically adopted as ACMG evidence.",
                }
            )
        if supplied:
            values = supplied if isinstance(supplied, list) else [supplied]
            for value in values:
                leads.append(
                    {
                        "source_type": "supplied_source_output",
                        "raw_source": value,
                        "system_preview_eligible": False,
                        "notice": "Supplied source assertion only; not automatically adopted.",
                    }
                )
        return leads

    def _normalize_disease_context(
        self, disease: str
    ) -> tuple[dict[str, Any], SourceCall | None]:
        value = str(disease or "").strip()
        if not value:
            return {"input": "", "status": "not_provided", "mondo_id": ""}, None
        if re.fullmatch(r"MONDO:\d+", value, re.IGNORECASE):
            return {
                "input": value,
                "status": "resolved",
                "mondo_id": value.upper(),
                "resolver": "input",
                "candidates": [value.upper()],
            }, None
        call = self._call(
            "ols_search_terms",
            {
                "query": value,
                "ontology": "mondo",
                "exact_match": True,
                "rows": 10,
            },
            "disease_context",
        )
        payload = _provider_payload(call.result)
        response = payload.get("response") if isinstance(payload, dict) else None
        docs = response.get("docs") if isinstance(response, dict) else None
        mondo_ids: list[str] = []
        for row in docs if isinstance(docs, list) else []:
            if not isinstance(row, dict):
                continue
            ontology = _normalize_text(
                row.get("ontology_name")
                or row.get("ontology_prefix")
                or row.get("ontology")
            )
            if ontology and ontology != "mondo":
                continue
            candidate = (
                str(
                    row.get("obo_id")
                    or row.get("short_form")
                    or row.get("ontology_id")
                    or ""
                )
                .upper()
                .replace("MONDO_", "MONDO:")
            )
            if re.fullmatch(r"MONDO:\d+", candidate) and candidate not in mondo_ids:
                mondo_ids.append(candidate)
        return {
            "input": value,
            "status": "resolved"
            if len(mondo_ids) == 1
            else "ambiguous"
            if mondo_ids
            else "unresolved",
            "mondo_id": mondo_ids[0] if len(mondo_ids) == 1 else "",
            "resolver": "ols_search_terms",
            "candidates": mondo_ids,
        }, call

    @staticmethod
    def _rule_context(
        cspec_call: SourceCall | None,
        *,
        gene: str,
        disease_context: dict[str, Any],
        inheritance: str,
        cspec_proposals: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload = _provider_payload(cspec_call.result) if cspec_call else None
        candidates = payload if isinstance(payload, list) else []
        normalized_gene = _normalize_text(gene)
        normalized_disease = _normalize_text(disease_context.get("mondo_id"))
        normalized_inheritance = _normalize_inheritance(inheritance)
        applicable: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            reasons: list[str] = []
            if _normalize_text(candidate.get("gene")) != normalized_gene:
                reasons.append("gene_mismatch")
            if _normalize_text(candidate.get("status")) != "released":
                reasons.append("specification_not_active")
            if not str(candidate.get("version") or "").strip():
                reasons.append("specification_version_missing")
            disease_rows = candidate.get("diseases")
            disease_rows = disease_rows if isinstance(disease_rows, list) else []
            if normalized_disease:
                if not any(
                    normalized_disease == _normalize_text(row.get("mondo_id"))
                    for row in disease_rows
                    if isinstance(row, dict)
                ):
                    reasons.append("disease_mismatch")
            else:
                reasons.append("disease_not_provided")
            if normalized_inheritance:
                if not any(
                    normalized_inheritance == _normalize_inheritance(mode)
                    for row in disease_rows
                    if isinstance(row, dict)
                    for mode in row.get("inheritance") or []
                ):
                    reasons.append("inheritance_mismatch")
            else:
                reasons.append("inheritance_not_provided")
            if reasons:
                unmatched.append(
                    {
                        "specification_id": candidate.get("specification_id"),
                        "reasons": reasons,
                    }
                )
            else:
                applicable.append(candidate)
        matched = applicable[0] if len(applicable) == 1 else None
        compiled_contract = None
        if matched is not None:
            compiled_contract = CSPEC_RULE_CATALOG.get(
                (
                    str(matched.get("specification_id") or ""),
                    str(matched.get("version") or ""),
                )
            )
        contract = (
            build_dynamic_cspec_contract(
                matched,
                proposals=cspec_proposals,
                compiled_contract=compiled_contract,
            )
            if matched is not None
            else None
        )
        provider_unavailable = bool(
            cspec_call is not None and cspec_call.status not in {"success", "no_hit"}
        )
        cspec_status = (
            "cspec_unavailable"
            if provider_unavailable
            else "not_found"
            if not candidates
            else "ambiguous"
            if len(applicable) > 1
            else "dynamic_structured_applied"
            if contract is not None
            else "discovered_context_incomplete"
        )
        return {
            "vcep_discovered": bool(candidates),
            "vcep_candidates": candidates,
            "cspec_status": cspec_status,
            "matched_specifications": applicable,
            "applicable_specification": matched,
            "applied_contract_id": (
                str(contract.get("rule_id") or "") if contract is not None else ""
            ),
            "applied_contract_version": (
                str(contract.get("version") or "") if contract is not None else ""
            ),
            "executable_contract": contract,
            "cspec_content_hash": (
                str(contract.get("content_hash") or "") if contract else ""
            ),
            "cspec_review_requests": (
                list(contract.get("review_requests") or []) if contract else []
            ),
            "cspec_proposal_report": (
                list(contract.get("proposal_reports") or []) if contract else []
            ),
            "compiled_contract_status": (
                str(contract.get("compiled_contract_status") or "") if contract else ""
            ),
            "disease_context": disease_context,
            "unmatched_reasons": unmatched,
            "fallback_policy": (
                "applicable_clingen_cspec"
                if contract is not None
                else "general_clingen_svi"
            ),
            "multiple_applicable_specifications": len(applicable) > 1,
        }

    @staticmethod
    def _criterion_reviews(
        rows: list[dict[str, Any]],
        consequence_profile: dict[str, Any],
        rule_context: dict[str, Any],
        source_facts: dict[str, SourceFact] | None = None,
        literature_review: dict[str, Any] | None = None,
        input_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        source_facts = source_facts or {}
        literature_review = literature_review or {}
        input_context = input_context or {}
        use_matrix = criterion_use_matrix()
        by_criterion: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            criterion = str(row.get("criterion") or "")
            targets = ("PP3", "BP4") if criterion == "PP3/BP4" else (criterion,)
            for target in targets:
                by_criterion.setdefault(target, []).append(row)
        executable = rule_context.get("executable_contract")
        criteria = executable.get("criteria") if isinstance(executable, dict) else {}
        reviews = []
        for criterion in ACMG_CRITERIA:
            criterion_rows = by_criterion.get(criterion, [])
            cspec_criterion = (
                criteria.get(criterion) if isinstance(criteria, dict) else None
            )
            applicability = consequence_applicability(
                criterion,
                consequence_profile,
                cspec_criterion=(
                    cspec_criterion if isinstance(cspec_criterion, dict) else None
                ),
            )
            statuses = {
                str(row.get("assessment_status") or "not_assessed")
                for row in criterion_rows
            }
            if applicability["status"] == "deprecated":
                aggregate = "deprecated"
            elif "met" in statuses:
                aggregate = "met"
            elif applicability["status"] == "not_applicable":
                aggregate = "not_applicable"
            elif "indeterminate" in statuses:
                aggregate = "indeterminate"
            elif "not_met" in statuses:
                aggregate = "not_met"
            else:
                aggregate = "not_assessed"
            rule = rule_for_criterion(criterion)
            use_contract = use_matrix[criterion]
            candidate_routes = list(use_contract.get("provider_routes") or [])
            if criterion in {"PS1", "PM5"}:
                candidate_routes = ["prior_variant_candidates"]
            pending_request_ids = []
            for request in literature_review.get("review_requests") or []:
                if not isinstance(request, dict) or request.get("state") not in {
                    "pending",
                    "proposal_validation_failed",
                }:
                    continue
                allowed_fact_types = request.get("allowed_fact_types") or []
                if any(
                    criterion in LITERATURE_FACT_CRITERIA.get(str(fact_type), ())
                    for fact_type in allowed_fact_types
                ):
                    pending_request_ids.append(str(request.get("request_id") or ""))
            candidate_source_fact_ids = sorted(
                {
                    fact.fact_id
                    for fact in source_facts.values()
                    if fact.status == "success"
                    and fact.identity_verified
                    and any(
                        route != "literature" and _fact_matches_route(fact, route)
                        for route in candidate_routes
                    )
                }
            )
            required = list(rule.get("required_inputs") or [])
            context_values = {
                "gene": input_context.get("gene") or consequence_profile.get("gene"),
                "transcript": input_context.get("transcript")
                or consequence_profile.get("selected_transcript"),
                "disease": input_context.get("disease"),
                "inheritance": input_context.get("inheritance")
                or input_context.get("inheritance_mode"),
            }
            missing_context = [
                name
                for name in use_contract.get("required_context") or []
                if not context_values.get(name)
            ]
            missing = {
                str(value)
                for row in criterion_rows
                for value in (
                    row.get("observed_facts", {}).get("missing_requirements", [])
                    if isinstance(row.get("observed_facts"), dict)
                    else []
                )
                if value
            }
            if aggregate not in {"met", "not_applicable", "deprecated"} and not missing:
                missing.update(
                    required
                    or ["No deterministic structured fact contract was satisfied."]
                )
            missing.update(f"context:{name}" for name in missing_context)
            row_proposal_statuses = {
                str(row.get("proposal_status") or "")
                for row in criterion_rows
                if row.get("proposal_status")
            }
            if aggregate == "deprecated":
                proposal_status = "deprecated"
            elif aggregate == "not_applicable":
                proposal_status = "not_applicable"
            elif "suggested" in row_proposal_statuses:
                proposal_status = "suggested"
            elif "requires_user_review" in row_proposal_statuses:
                proposal_status = "requires_user_review"
            elif use_contract["automation_level"] in {
                "disease_specific",
                "review_guided",
            }:
                proposal_status = "requires_user_review"
            else:
                proposal_status = "insufficient_information"
            validated_proposals = [
                row
                for row in criterion_rows
                if row.get("assessment_status") == "met"
                and row.get("proposal_origin") in {"llm_literature", "llm_cspec"}
            ]
            assessed_rows = [
                row
                for row in criterion_rows
                if row.get("assessment_status") in {"met", "not_met", "indeterminate"}
                and row.get("proposal_origin") not in {"llm_literature", "llm_cspec"}
            ]
            if aggregate == "deprecated":
                route_status = "deprecated"
            elif aggregate == "not_applicable":
                route_status = "not_applicable"
            elif validated_proposals:
                route_status = "proposal_validated"
            elif assessed_rows:
                route_status = "assessed"
            elif pending_request_ids:
                route_status = "review_pending"
            elif candidate_source_fact_ids:
                route_status = "candidate_available"
            else:
                route_status = "insufficient_information"
            reviews.append(
                {
                    "criterion": criterion,
                    "direction": use_contract["direction"],
                    "default_strength": use_contract["default_strength"],
                    "automation_level": use_contract["automation_level"],
                    "consequence_applicability": applicability["status"],
                    "consequence_reason": applicability["reason"],
                    "assessment_status": aggregate,
                    "proposal_status": proposal_status,
                    "route_status": route_status,
                    "evidence_card_ids": [row.get("card_id") for row in criterion_rows],
                    "candidate_source_fact_ids": candidate_source_fact_ids,
                    "pending_request_ids": sorted(
                        value for value in set(pending_request_ids) if value
                    ),
                    "proposal_statuses": sorted(row_proposal_statuses),
                    "observed_facts": [
                        row.get("observed_facts") for row in criterion_rows
                    ],
                    "required_facts": required,
                    "required_context": list(
                        use_contract.get("required_context") or []
                    ),
                    "missing_requirements": sorted(missing),
                }
            )
        return reviews

    @staticmethod
    def _annotate_cspec(
        cards: list[EvidenceCard], rule_context: dict[str, Any]
    ) -> None:
        """Attach a uniquely matched online CSpec to already-supported cards."""
        specification = rule_context.get("applicable_specification")
        contract = rule_context.get("executable_contract")
        if not isinstance(specification, dict) or not isinstance(contract, dict):
            return
        by_criterion = contract.get("criteria")
        if not isinstance(by_criterion, dict):
            return
        spec_id = str(specification.get("specification_id") or "")
        for card in cards:
            strength_criterion = str(card.strength or "").split("_", 1)[0]
            criterion = (
                strength_criterion
                if strength_criterion in by_criterion
                else str(card.criterion or "").split("/", 1)[0].split("_", 1)[0]
            )
            matched = by_criterion.get(criterion)
            if not isinstance(matched, dict):
                continue
            if matched.get("rule_applicable") is False:
                card.assessment_status = "not_applicable"
                card.strength = "not_applicable"
                card.proposal_status = "not_applicable"
                card.overlay_validated = False
                card.caveats.append(
                    "The uniquely matched online CSpec marks this criterion "
                    "not applicable."
                )
            assessment = card.assessment_status or ""
            card_has_rule_result = (
                assessment == "met"
                or is_valid_strength_for_criterion(criterion, str(card.strength or ""))
            )
            if not card_has_rule_result and matched.get("rule_applicable") is not False:
                continue
            mapped_strength = str(matched.get("strength") or "")
            if mapped_strength and is_valid_strength_for_criterion(
                criterion, mapped_strength
            ):
                card.strength = mapped_strength
            card.input_values = {
                **card.input_values,
                "applicable_cspec": {
                    "specification_id": spec_id,
                    "version": specification.get("version"),
                    "vcep": specification.get("vcep"),
                    "content_hash": contract.get("content_hash"),
                    "criterion_contract": matched,
                },
                "cspec_contract_applied": {
                    "specification_id": spec_id,
                    "version": specification.get("version"),
                    "content_hash": contract.get("content_hash"),
                    "rule_id": contract.get("rule_id"),
                    "bayesian_odds": (
                        contract.get("bayesian_odds", {}).get(card.strength)
                        if isinstance(contract.get("bayesian_odds"), dict)
                        else None
                    ),
                    "mutually_exclusive_with": list(
                        matched.get("mutually_exclusive_with") or []
                    ),
                },
            }
            card.rule_id = str(contract.get("rule_id") or card.rule_id)
            card.rule_version = str(contract.get("version") or card.rule_version)
            card.rule_reference = str(
                contract.get("primary_reference") or card.rule_reference
            )
            verification = str(matched.get("verification") or "")
            card.rule_verification = (
                "dynamic_cspec_llm"
                if verification == "dynamic_cspec_llm"
                else "compiled_hash_verified"
                if verification == "compiled_hash_verified"
                else "dynamic_cspec_structured"
            )
            card.rule_mapping_status = (
                "llm_review_required"
                if verification == "dynamic_cspec_llm"
                else "dynamic_cspec_structured"
            )
            if verification == "dynamic_cspec_llm":
                card.proposal_origin = "llm_cspec"
                card.llm_suggestion = {
                    **card.llm_suggestion,
                    "cspec": {
                        "criterion": criterion,
                        "suggested_strength": matched.get("strength"),
                        "interpretation": matched.get("llm_interpretation"),
                        "confidence": matched.get("confidence"),
                        "extractor": dict(matched.get("extractor") or {}),
                        "locator": matched.get("cspec_locator"),
                        "excerpt": matched.get("cspec_excerpt"),
                    },
                }
            card.proposal_status = (
                "requires_user_review"
                if verification == "dynamic_cspec_llm"
                else card.proposal_status
            )
            card.rule_basis = (
                f"Online ClinGen CSpec {spec_id} v{specification.get('version')}"
            )

    def _error_result(
        self,
        variant: str,
        calls: list[SourceCall],
        source_facts: dict[str, SourceFact],
        limitation_code: str,
        identity: dict[str, Any] | None = None,
        clinical_context: dict[str, Any] | None = None,
        variant_scope: dict[str, Any] | None = None,
        workflow_status: str = "consequence_recovery_required",
    ) -> dict[str, Any]:
        """Return the stable collector shape without evaluating unbound evidence."""
        consequence_profile = build_consequence_profile(identity or {}, {})
        not_applicable = workflow_status == "unsupported_variant_class"
        preflight_stop = (
            not_applicable or workflow_status == "input_correction_required"
        )
        if preflight_stop:
            consequence_profile.update(
                {
                    "annotation_status": "unavailable",
                    "annotation_reason": limitation_code,
                    "missing_requirements": [],
                }
            )
        coverage = self._coverage(
            calls,
            source_facts,
            identity,
            {"variant": variant},
            consequence_profile,
            {},
        )
        limitations = [limitation_code]
        variant_identity = {
            "input_variant": variant,
            "hgvs_c": (identity or {}).get("hgvs_c") or variant,
            "gene": (identity or {}).get("gene"),
            "transcript": (identity or {}).get("transcript"),
            "normalization": (identity or {}).get("normalization", {}),
            "normalization_error": (identity or {}).get("identity_error"),
            "candidates": list(
                (identity or {}).get("normalization", {}).get("recoder_candidates")
                or []
            ),
            "excluded_candidates": list(
                (identity or {}).get("normalization", {}).get("excluded_candidates")
                or []
            ),
        }
        rule_context = {
            "vcep_discovered": False,
            "vcep_candidates": [],
            "cspec_status": "not_found",
            "applicable_specification": None,
            "applied_contract_id": "",
            "applied_contract_version": "",
            "unmatched_reasons": [],
            "fallback_policy": "general_clingen_svi",
            "criterion_use_matrix": criterion_use_matrix(),
        }
        literature_candidates = _literature_candidate_index(
            source_facts,
            identity=identity or {},
            arguments={"variant": variant},
        )
        literature_review = _literature_review_state(
            literature_candidates,
            source_facts,
            identity=identity or {},
            arguments={"variant": variant},
        )
        recoverable_gaps = _recoverable_gaps(
            consequence_profile,
            literature_review,
        )
        if preflight_stop:
            coverage = []
            recoverable_gaps = []
            literature_candidates = []
            literature_review = {
                "candidates": [],
                "review_requests": [],
                "reading_manifests": [],
                "processed_publication_ids": [],
                "unprocessed_request_ids": [],
                "proposal_validation_status": "not_applicable",
                "search_queries": [],
                "workflow_status": workflow_status,
            }
        next_actions = (
            [
                {
                    "action": "route_structural_variant",
                    "executor": "host_llm",
                    "skill_name": "tooluniverse-structural-variant-analysis",
                    "expected_input": "original structural-variant coordinates and build",
                    "completion_condition": "structural-variant workflow loaded",
                    "blocking_reason": "small-variant ACMG collector is not applicable",
                }
            ]
            if not_applicable
            else []
        )
        criterion_reviews = (
            []
            if not_applicable
            else self._criterion_reviews(
                [], consequence_profile, {}, source_facts, literature_review
            )
        )
        conflict_report = detect_conflicts([])
        system_preview_bayesian = compute_bayesian_score(
            [],
            estimate_type="system_preview",
            known_source_fact_ids=set(),
            eligibility="source_backed",
        )
        validated_subset_bayesian = compute_bayesian_score(
            [],
            estimate_type="validated_subset",
            selection_field="validated_subset_included",
        )
        user_selected_bayesian = {
            "status": "not_requested",
            "estimate_type": "user_selected",
            "prior_probability": BAYESIAN_PRIOR,
            "not_a_final_classification": True,
        }
        review_readiness = _review_readiness(
            variant_scope=dict(variant_scope or {}),
            identity=identity or {},
            arguments={"variant": variant},
            workflow_status=workflow_status,
            criterion_reviews=criterion_reviews,
            evidence_rows=[],
            conflict_report=conflict_report,
            literature_review=literature_review,
            recoverable_gaps=recoverable_gaps,
            system_preview_bayesian=system_preview_bayesian,
            validated_subset_bayesian=validated_subset_bayesian,
            user_selected_bayesian=user_selected_bayesian,
        )
        runtime_manifest = build_runtime_manifest(rule_context)
        guard_context = _build_guard_context(
            [],
            source_facts,
            variant_identity=variant_identity,
            runtime_manifest=runtime_manifest,
        )
        return {
            "status": "not_applicable" if not_applicable else "error",
            "execution_status": "not_run" if not_applicable else "error",
            "coverage_status": "not_applicable" if not_applicable else "insufficient",
            "error": limitation_code,
            "variant": variant_identity,
            "variant_identity": variant_identity,
            "variant_scope": dict(variant_scope or {}),
            "clinical_context": clinical_context,
            "response_detail": "full",
            "consequence_profile": consequence_profile,
            "coverage_summary": coverage,
            "source_facts": [fact.to_dict() for fact in source_facts.values()],
            "source_assertions": self._source_assertions(calls, None),
            "prior_variant_candidates": [],
            "literature_candidates": literature_candidates,
            "literature_review": literature_review,
            "recoverable_gaps": recoverable_gaps,
            "workflow_status": workflow_status,
            "review_readiness": review_readiness,
            "next_actions": next_actions,
            "rule_context": rule_context,
            "runtime_manifest": runtime_manifest,
            "guard_context": guard_context,
            "predictor_scores": {},
            "criterion_reviews": criterion_reviews,
            "evidence_cards": [],
            "compatibility_report": {
                "compatible_evidence": [],
                "excluded_evidence": [],
            },
            "conflict_report": conflict_report,
            "system_preview_bayesian": system_preview_bayesian,
            "validated_subset_bayesian": validated_subset_bayesian,
            "user_selected_bayesian": user_selected_bayesian,
            "decision_report": {
                "status": "not_requested",
                "matched_decisions": [],
                "unmatched_decisions": [],
                "decision_errors": [],
                "compatibility_exclusions": [],
            },
            "limitations": limitations,
            "final_classification_allowed": False,
        }

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        variant = str(arguments.get("variant") or "")
        if not variant:
            return self._error_result(
                "",
                [],
                {},
                "variant_required",
                variant_scope={
                    "input_kind": "unknown",
                    "span_bp": None,
                    "normalized_genome_build": None,
                    "build_resolution_source": "missing",
                    "collector_supported": False,
                    "recommended_route": "input_correction_required",
                    "input_error": "variant_required",
                    "normalized_variant": "",
                },
                workflow_status="input_correction_required",
            )
        variant_scope = classify_variant_scope(
            variant, str(arguments.get("genome_build") or "")
        )
        if variant_scope.get("input_error"):
            return self._error_result(
                variant,
                [],
                {},
                str(variant_scope["input_error"]),
                variant_scope=variant_scope,
                workflow_status="input_correction_required",
            )
        if variant_scope.get("input_kind") == "structural_variant":
            return self._error_result(
                variant,
                [],
                {},
                "unsupported_variant_class_structural_variant",
                variant_scope=variant_scope,
                workflow_status="unsupported_variant_class",
            )
        evidence_decisions, decision_input_errors = _normalize_evidence_decisions(
            arguments.get("evidence_decisions")
        )
        _literature_items, literature_input_error = _literature_input(arguments)
        input_errors = [
            *decision_input_errors,
            *([literature_input_error] if literature_input_error else []),
        ]
        if input_errors:
            result = self._error_result(
                variant,
                [],
                {},
                "invalid_acmg_review_input",
                variant_scope=variant_scope,
                workflow_status="input_correction_required",
            )
            result["input_errors"] = input_errors
            return result
        clinical_context = _normalize_clinical_context(
            arguments.get("clinical_context")
        )

        identity_calls, identity = self._identity(
            str(variant_scope.get("normalized_variant") or variant),
            str(arguments.get("gene") or ""),
            str(arguments.get("transcript") or ""),
            str(variant_scope.get("normalized_genome_build") or "GRCh38"),
        )
        identity["input_variant"] = variant
        identity.setdefault("normalization", {})["normalized_input_variant"] = str(
            variant_scope.get("normalized_variant") or variant
        )
        identity_valid = bool(identity.get("identity_verified")) and not bool(
            identity.get("identity_conflict")
        )
        if not identity_valid:
            identity_source_facts = self._source_facts(identity_calls, identity)
            return self._error_result(
                variant,
                identity_calls,
                identity_source_facts,
                "variant_identity_unverified",
                identity,
                clinical_context=clinical_context,
                variant_scope=variant_scope,
            )

        consequence_calls, consequence_diagnostics = self._consequence_calls(identity)
        consequence_seed_facts = self._source_facts(
            [*identity_calls, *consequence_calls], identity
        )
        consequence_profile = self._profile_from_facts(
            identity,
            consequence_seed_facts,
            consequence_diagnostics,
        )

        resolved_gene = str(arguments.get("gene") or identity.get("gene") or "")
        cspec_call = (
            self._call("ClinGen_search_cspec", {"gene": resolved_gene}, "rule_context")
            if resolved_gene
            else None
        )
        disease_context, disease_call = self._normalize_disease_context(
            str(arguments.get("disease") or "")
        )
        rule_context = self._rule_context(
            cspec_call,
            gene=resolved_gene,
            disease_context=disease_context,
            inheritance=str(
                arguments.get("inheritance") or arguments.get("inheritance_mode") or ""
            ),
            cspec_proposals=(
                arguments.get("cspec_proposals")
                if isinstance(arguments.get("cspec_proposals"), list)
                else []
            ),
        )
        source_calls = self._collect_sources(arguments, identity)
        if cspec_call is not None:
            source_calls.insert(0, cspec_call)
        if disease_call is not None:
            source_calls.insert(1 if cspec_call is not None else 0, disease_call)
        protein_calls, protein_mapping = self._protein_context_calls(
            arguments,
            identity,
            consequence_profile,
            rule_context,
        )
        source_calls.extend(protein_calls)
        source_calls.extend(
            self._pvs1_context_calls(
                identity, consequence_profile, consequence_seed_facts
            )
        )
        literature_seed_facts = self._source_facts(
            [*identity_calls, *consequence_calls, *source_calls],
            identity,
        )
        prior_variant_candidates = self._prior_variant_candidates(literature_seed_facts)
        prior_variant_calls = self._prior_variant_literature_calls(
            prior_variant_candidates,
            gene=resolved_gene,
        )
        if prior_variant_calls:
            source_calls.extend(prior_variant_calls)
            literature_seed_facts = self._source_facts(
                [*identity_calls, *consequence_calls, *source_calls],
                identity,
            )
        literature_seed_candidates = _literature_candidate_index(
            literature_seed_facts,
            identity=identity,
            arguments=arguments,
        )
        source_calls.extend(
            self._literature_annotation_calls(literature_seed_candidates)
        )
        literature_source_facts, fulltext_calls = (
            self._document_backed_literature_proposals(arguments, identity)
        )
        calls = [
            *identity_calls,
            *consequence_calls,
            *source_calls,
            *fulltext_calls,
        ]
        source_facts = self._source_facts(calls, identity)
        source_facts.update(literature_source_facts)
        exon_lof_calls = self._pvs1_exon_lof_calls(
            identity, consequence_profile, source_facts
        )
        if exon_lof_calls:
            calls.extend(exon_lof_calls)
            source_facts.update(self._source_facts(exon_lof_calls, identity))
        consequence_profile = self._profile_from_facts(
            identity,
            source_facts,
            consequence_diagnostics,
        )
        consequence_profile["protein_mapping"] = protein_mapping
        cspec_facts = self._facts_for_tool(source_facts, "ClinGen_search_cspec")
        rule_context["source_fact_ids"] = [fact.fact_id for fact in cspec_facts]
        rule_context["applicability_matching"] = (
            "exact_gene_disease_or_mondo_inheritance"
        )
        rule_context["criterion_use_matrix"] = criterion_use_matrix()

        cards: list[EvidenceCard] = []
        population_inputs, population_fact_ids = self._population_inputs(
            source_facts, rule_context
        )
        population_cards = population_evidence(**population_inputs)
        cards.extend(
            self._promote_cards(
                population_cards,
                population_fact_ids,
                {"PM2", "BS1"},
            )
        )

        computational_inputs = self._computational_inputs(
            source_facts, consequence_profile
        )
        computational_inputs["rule_override"] = rule_context.get("executable_contract")
        computational_cards = computational_evidence(**computational_inputs)
        predictor_facts = self._facts_for_tool(
            source_facts, "MyVariant_get_pathogenicity_scores"
        )
        splice_facts = self._facts_for_tool(source_facts, "SpliceAI_predict_splice")
        for card in computational_cards:
            if card.input_source == "SpliceAI":
                fact_ids = [fact.fact_id for fact in splice_facts[:1]]
            elif card.input_source == "REVEL":
                fact_ids = [fact.fact_id for fact in predictor_facts[:1]]
            else:
                fact_ids = []
            cards.extend(
                self._promote_cards(
                    [card],
                    fact_ids,
                    {"PP3", "BP4", "PP3/BP4", "BP7"},
                )
            )

        clinical_cards = clinical_evidence(**self._clinical_inputs(source_facts))
        de_novo_fact_ids = _literature_fact_ids(source_facts, "de_novo")
        for card in clinical_cards:
            if card.criterion in {"PS2", "PM6"}:
                self._promote_cards([card], de_novo_fact_ids, {"PS2", "PM6"})
            elif card.criterion == "PM3":
                self._promote_cards(
                    [card],
                    _literature_fact_ids(source_facts, "pm3", "recessive_allelic"),
                    {"PM3"},
                )
        cards.extend(clinical_cards)
        pvs1_facts, pvs1_fact_ids = self._pvs1_facts(consequence_profile, source_facts)
        functional_inputs = self._functional_inputs(
            consequence_profile,
            source_facts,
            protein_mapping,
            rule_context,
            pvs1_facts,
        )
        functional_cards = functional_evidence(**functional_inputs)
        pm1_source_fact_ids = list(
            functional_inputs.get("protein_context", {}).get("source_fact_ids") or []
        )
        pm1_source_fact_ids.extend(
            str(value)
            for value in consequence_profile.get("source_fact_ids") or []
            if value not in pm1_source_fact_ids
        )
        functional_facts = {
            str(fact.features.get("values", {}).get("assay_instance_id") or ""): fact
            for fact in source_facts.values()
            if fact.assessment_ready and fact.features.get("fact_type") == "functional"
        }
        for card in functional_cards:
            if card.criterion == "PM1":
                self._promote_cards([card], pm1_source_fact_ids, {"PM1"})
                continue
            if card.criterion == "PVS1":
                self._promote_cards([card], pvs1_fact_ids, {"PVS1"})
                continue
            assay_id = next((value for value in card.source_case_ids if value), "")
            supporting_fact = functional_facts.get(assay_id)
            if supporting_fact is not None:
                pmid = str(supporting_fact.features.get("pmid") or "")
                pmcid = str(supporting_fact.features.get("pmcid") or "")
                card.source_pmid = pmid or None
                card.source_pmids = [value for value in (pmid, pmcid) if value]
            self._promote_cards(
                [card],
                [supporting_fact.fact_id] if supporting_fact is not None else [],
                {"PS3", "BS3"},
            )
        cards.extend(functional_cards)
        cards.extend(
            self._protein_length_repeat_cards(
                consequence_profile,
                source_facts,
                functional_inputs.get("protein_context", {}),
            )
        )

        literature_cards = literature_evidence(
            **self._literature_inputs(arguments, identity, source_facts),
            rule_override=rule_context.get("executable_contract"),
        )
        case_series_facts = [
            fact
            for fact in source_facts.values()
            if fact.assessment_ready
            and fact.features.get("fact_type") in {"case_control", "case_series"}
        ]
        facts_by_case_id = {
            str(fact.features.get("fact_id")): fact.fact_id
            for fact in case_series_facts
            if fact.features.get("fact_id")
        }
        for card in literature_cards:
            fact_ids = [
                facts_by_case_id[case_id]
                for case_id in card.source_case_ids
                if case_id in facts_by_case_id
            ]
            self._promote_cards([card], fact_ids, {"PS4"})
        cards.extend(literature_cards)
        cards.extend(self._literature_proposal_cards(source_facts, consequence_profile))
        self._attach_literature_suggestions(cards, source_facts)

        variant_identity = {
            "input_variant": identity.get("input_variant") or variant,
            "gene": arguments.get("gene") or identity.get("gene"),
            "transcript": arguments.get("transcript") or identity.get("transcript"),
            "hgvs_c": identity.get("validated_hgvs_c")
            or identity.get("hgvs_c")
            or variant,
            "hgvs_g": identity.get("hgvs_g"),
            "hgvs_p": identity.get("hgvs_p"),
            "rsid": identity.get("rsid"),
            "consequence": arguments.get("consequence") or identity.get("consequence"),
            "coordinates": identity.get("coordinates"),
            "normalization": identity.get("normalization", {}),
            "candidates": list(
                identity.get("normalization", {}).get("recoder_candidates") or []
            ),
            "excluded_candidates": list(
                identity.get("normalization", {}).get("excluded_candidates") or []
            ),
        }
        self._annotate_cspec(cards, rule_context)
        trusted_source_fact_ids = {
            fact_id for fact_id, fact in source_facts.items() if fact.assessment_ready
        }
        known_source_fact_ids = set(source_facts)
        serialized = evidence_cards_to_result(
            cards,
            variant_identity=variant_identity,
            trusted_source_fact_ids=trusted_source_fact_ids,
            known_source_fact_ids=known_source_fact_ids,
        )
        evidence_rows = list(
            {row["card_id"]: row for row in serialized["evidence_cards"]}.values()
        )
        variant_identity["consequence"] = list(
            consequence_profile.get("selected_transcript_terms") or []
        )
        coverage = self._coverage(
            calls,
            source_facts,
            identity,
            arguments,
            consequence_profile,
            rule_context,
        )
        limitations = [
            f"{row['source_category']} coverage is {row['query_status']}"
            for row in coverage
            if row["query_status"] in {"failed", "unavailable"}
        ]
        limitations.extend(
            f"{row['source_category']}: {row['limitation_code']}"
            for row in coverage
            if row.get("limitation_code")
        )
        if consequence_profile.get("annotation_status") != "resolved":
            limitations.append(
                str(
                    consequence_profile.get("annotation_reason")
                    or "consequence_annotation_empty"
                )
            )
        literature_items, _literature_error = _literature_input(arguments)
        if (
            any(
                row["source_category"] == "literature"
                and row["query_status"] == "success"
                and row["assessment_ready"] is False
                for row in coverage
            )
            and not literature_items
        ):
            limitations.append(
                "literature search returned leads, but no validated structured "
                "literature facts were available for criterion assessment"
            )
        splice_call_succeeded = any(
            call.tool_name == "SpliceAI_predict_splice" and call.status == "success"
            for call in calls
        )
        splice_fact_ready = any(
            fact.tool_name == "SpliceAI_predict_splice" and fact.assessment_ready
            for fact in source_facts.values()
        )
        if splice_call_succeeded and not splice_fact_ready:
            limitations.append(
                "spliceai_walker_contract_incomplete: SpliceAI PP3/BP4 held "
                "not_assessed; the provider model/annotation version or an "
                "identity-bound score row could not be proven for the "
                "Walker 2023 calibration contract"
            )
        coverage_partial = any(row.get("limitation_code") for row in coverage)
        evidence_ready = any(
            row.get("assessment_ready")
            for row in coverage
            if row.get("source_category")
            in {"population", "computational", "literature", "functional"}
        )
        coverage_status = (
            "partial"
            if coverage_partial
            else "complete"
            if evidence_ready
            else "insufficient"
        )
        status = (
            "degraded" if self.tooluniverse is None or coverage_partial else "success"
        )
        compatibility = resolve_evidence_compatibility(
            evidence_rows,
            known_source_fact_ids=known_source_fact_ids,
            eligibility="source_backed",
            selection_field="system_preview_included",
        )
        compatible_ids = {
            str(row.get("card_id") or "")
            for row in compatibility["compatible_evidence"]
        }
        excluded_reasons = {
            str(row.get("card_id") or ""): str(row.get("reason") or "")
            for row in compatibility["excluded_evidence"]
            if row.get("card_id")
        }
        for row in evidence_rows:
            card_id = str(row.get("card_id") or "")
            if (
                row.get("system_preview_included") is True
                and card_id not in compatible_ids
            ):
                row["system_preview_included"] = False
                row["exclusion_reason"] = excluded_reasons.get(
                    card_id, "excluded_by_compatibility_resolver"
                )
                row["preview_inclusion_basis"] = "excluded"
                row["preview_exclusion_reason"] = row["exclusion_reason"]
        system_preview_bayesian = compute_bayesian_score(
            compatibility["compatible_evidence"],
            known_source_fact_ids=known_source_fact_ids,
            estimate_type="system_preview",
            eligibility="source_backed",
        )
        system_preview_bayesian["compatibility_exclusions"] = compatibility[
            "excluded_evidence"
        ]
        system_preview_bayesian["excluded_card_ids"] = [
            str(row.get("card_id") or "")
            for row in compatibility["excluded_evidence"]
            if row.get("card_id")
        ]
        validated_compatibility = resolve_evidence_compatibility(
            evidence_rows,
            trusted_source_fact_ids=trusted_source_fact_ids,
            eligibility="validated",
            selection_field="validated_subset_included",
        )
        validated_ids = {
            str(row.get("card_id") or "")
            for row in validated_compatibility["compatible_evidence"]
        }
        for row in evidence_rows:
            if (
                row.get("validated_subset_included") is True
                and str(row.get("card_id") or "") not in validated_ids
            ):
                row["validated_subset_included"] = False
        validated_subset_bayesian = compute_bayesian_score(
            validated_compatibility["compatible_evidence"],
            trusted_source_fact_ids=trusted_source_fact_ids,
            estimate_type="validated_subset",
            selection_field="validated_subset_included",
            eligibility="validated",
        )
        validated_subset_bayesian["excluded_card_ids"] = [
            str(row.get("card_id") or "")
            for row in validated_compatibility["excluded_evidence"]
            if row.get("card_id")
        ]
        user_selected_bayesian, decision_report = _apply_evidence_decisions(
            evidence_rows,
            evidence_decisions,
            known_source_fact_ids=known_source_fact_ids,
        )
        conflict_report = detect_conflicts(
            evidence_rows,
            known_source_fact_ids=known_source_fact_ids,
            eligibility="source_backed",
        )
        conflict_report["compatibility_exclusions"] = [
            {
                "card_id": row.get("card_id"),
                "criterion": row.get("criterion"),
                "reason": row.get("reason") or row.get("exclusion_reason"),
                "source_fact_ids": row.get("source_fact_ids", []),
            }
            for row in compatibility["excluded_evidence"]
        ]
        correlated_reasons = {
            "shared_source_fact",
            "duplicate_assay_instance",
            "duplicate_family",
            "overlapping_cohort",
            "duplicate_prior_variant",
            "overlapping_cases",
            "overlapping_clinical_case",
            "same_source_same_criterion",
            "correlated_computational_evidence",
            "duplicate_criterion",
        }
        conflict_report["correlated_source_exclusions"] = [
            {
                "card_id": row.get("card_id"),
                "criterion": row.get("criterion"),
                "reason": row.get("reason") or row.get("exclusion_reason"),
                "source_fact_ids": row.get("source_fact_ids", []),
            }
            for row in compatibility["excluded_evidence"]
            if (row.get("reason") or row.get("exclusion_reason")) in correlated_reasons
        ]
        directional_conflicts = [
            row
            for row in compatibility["excluded_evidence"]
            if row.get("reason") == "unresolved_directional_conflict"
        ]
        if directional_conflicts:
            conflict_report["has_conflicts"] = True
            conflict_report["conflicts"].append(
                {
                    "type": "unresolved_directional_conflict",
                    "card_ids": [row.get("card_id") for row in directional_conflicts],
                    "criteria": [row.get("criterion") for row in directional_conflicts],
                    "source_fact_ids": sorted(
                        {
                            str(fact_id)
                            for row in directional_conflicts
                            for fact_id in row.get("source_fact_ids", [])
                            if fact_id
                        }
                    ),
                    "description": (
                        "Opposing candidate evidence remains visible, but all "
                        "members were excluded from the Bayesian estimate."
                    ),
                }
            )

        literature_candidates = _literature_candidate_index(
            source_facts,
            identity=identity,
            arguments=arguments,
        )
        literature_review = _literature_review_state(
            literature_candidates,
            source_facts,
            identity=identity,
            arguments=arguments,
            consequence_profile=consequence_profile,
        )
        recoverable_gaps = _recoverable_gaps(
            consequence_profile,
            literature_review,
            protein_mapping=protein_mapping,
            source_facts=source_facts,
        )
        next_actions = _workflow_next_actions(literature_review, rule_context)
        literature_status = str(
            literature_review.get("workflow_status") or "evidence_ready"
        )
        unresolved_consequence = consequence_profile.get(
            "annotation_status"
        ) != "resolved" or any(
            row.get("status") == "unresolved"
            and row.get("recovery_status") != "exhausted"
            and row.get("code")
            in {
                "selected_transcript_missing",
                "exon_structure_missing",
                "nmd_facts_missing",
                "protein_context_missing",
            }
            for row in recoverable_gaps
            if isinstance(row, dict)
        )
        if unresolved_consequence:
            workflow_status = "consequence_recovery_required"
        elif literature_status in {
            "literature_review_required",
            "proposal_validation_required",
        }:
            workflow_status = literature_status
        elif next_actions:
            workflow_status = "proposal_validation_required"
        elif literature_status == "blocked_external_full_text":
            workflow_status = literature_status
        else:
            workflow_status = "evidence_ready"
        literature_review["workflow_status"] = workflow_status
        criterion_reviews = self._criterion_reviews(
            evidence_rows,
            consequence_profile,
            rule_context,
            source_facts,
            literature_review,
            arguments,
        )
        prior_variant_candidates = self._prior_variant_candidates(source_facts)
        review_readiness = _review_readiness(
            variant_scope=variant_scope,
            identity=identity,
            arguments=arguments,
            workflow_status=workflow_status,
            criterion_reviews=criterion_reviews,
            evidence_rows=evidence_rows,
            conflict_report=conflict_report,
            literature_review=literature_review,
            recoverable_gaps=recoverable_gaps,
            system_preview_bayesian=system_preview_bayesian,
            validated_subset_bayesian=validated_subset_bayesian,
            user_selected_bayesian=user_selected_bayesian,
        )
        runtime_manifest = build_runtime_manifest(rule_context)
        guard_context = _build_guard_context(
            evidence_rows,
            source_facts,
            variant_identity=variant_identity,
            runtime_manifest=runtime_manifest,
        )

        result = {
            "status": status,
            "execution_status": "success",
            "coverage_status": coverage_status,
            "variant": variant_identity,
            "variant_identity": variant_identity,
            "variant_scope": variant_scope,
            "clinical_context": clinical_context,
            "response_detail": "full",
            "consequence_profile": consequence_profile,
            "rule_context": rule_context,
            "runtime_manifest": runtime_manifest,
            "guard_context": guard_context,
            "coverage_summary": coverage,
            "source_facts": [fact.to_dict() for fact in source_facts.values()],
            "source_assertions": self._source_assertions(
                source_calls, arguments.get("source_outputs_or_leads")
            ),
            "prior_variant_candidates": prior_variant_candidates,
            "literature_candidates": literature_candidates,
            "literature_review": literature_review,
            "recoverable_gaps": recoverable_gaps,
            "workflow_status": workflow_status,
            "review_readiness": review_readiness,
            "next_actions": next_actions,
            "predictor_scores": self._computational_inputs(
                source_facts, consequence_profile
            ).get("predictor_scores", {}),
            "evidence_cards": evidence_rows,
            "criterion_reviews": criterion_reviews,
            "compatibility_report": compatibility,
            "conflict_report": conflict_report,
            "system_preview_bayesian": system_preview_bayesian,
            "validated_subset_bayesian": validated_subset_bayesian,
            "user_selected_bayesian": user_selected_bayesian,
            "decision_report": decision_report,
            "limitations": limitations,
            "final_classification_allowed": False,
        }
        if str(arguments.get("response_detail") or "summary").casefold() != "full":
            return _compact_result(result)
        return result


__all__ = ["ACMGEvidencePipeline", "SourceCall"]
