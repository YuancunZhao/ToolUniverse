"""Deterministic, source-located literature fact extraction for ACMG v3.

The extractor deliberately emits conservative atomic candidates. It never
uses the search query itself as evidence and never claims to have read content
that is absent from the provider response.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .models import SourceFact


EXTRACTOR_ID = "tooluniverse-acmg-literature-rules"
EXTRACTOR_VERSION = "2026-08-09-v3"
TARGET_LINK_POLICY_VERSION = "2026-08-09-v3"
MINIMUM_FACT_REQUIREMENTS = {
    "de_novo": ("target_variant", "proband_or_family"),
    "case_control": ("target_variant", "odds_ratio", "confidence_interval"),
    "case_series": ("target_variant", "case_series_subject"),
    "recessive_allelic": ("target_variant", "second_allele_identity", "phase"),
    "functional": (
        "target_variant",
        "assay",
        "assay_result",
        "experimental_controls",
    ),
    "segregation": ("target_variant", "family", "segregation_direction"),
    "phenotype_specificity": ("target_variant", "specific_phenotype_context"),
    "healthy_observation": ("target_variant", "observed_individual"),
    "allelic_phase": ("target_variant", "second_allele_identity"),
    "alternative_cause": ("target_variant", "alternative_cause_identity"),
    "prior_variant": ("target_variant", "prior_variant_identity"),
    "rna_splicing": ("target_variant", "rna_assay", "rna_result"),
}


def _strings(value: Any, *, key: str = "") -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() and key not in {"query", "search_query"} else []
    if isinstance(value, dict):
        return [
            text
            for child_key, child in value.items()
            for text in _strings(child, key=str(child_key))
        ]
    if isinstance(value, list):
        return [text for child in value for text in _strings(child, key=key)]
    return []


def _document_strings(features: dict[str, Any]) -> list[str]:
    """Read evidence-bearing document fields without ingesting query metadata."""
    payload = features.get("data")
    payload = payload if isinstance(payload, dict) else features
    texts: list[str] = []
    for key in (
        "title",
        "abstract",
        "sections",
        "text",
        "content",
        "tables",
        "figures",
        "figure_captions",
        "table_captions",
        "supplements",
        "snippet",
    ):
        texts.extend(_strings(payload.get(key), key=key))
    return texts


def _publication_matches(fact: SourceFact, candidate: dict[str, Any]) -> bool:
    arguments = fact.request_arguments
    for key in ("pmid", "pmcid"):
        expected = str(candidate.get(key) or "").casefold()
        observed = str(arguments.get(key) or "").casefold()
        if expected and observed and expected == observed:
            return True
    article_id = str(arguments.get("article_id") or "").casefold()
    return bool(
        article_id and article_id == str(candidate.get("pmid") or "").casefold()
    )


def _candidate_corpus(
    candidate: dict[str, Any], source_facts: dict[str, SourceFact]
) -> tuple[str, str, list[str], str, dict[str, Any]]:
    texts = [
        str(candidate.get("abstract") or ""),
        *_strings(candidate.get("snippets"), key="snippets"),
        *_strings(candidate.get("fulltext_snippets"), key="fulltext_snippets"),
    ]
    source_status = (
        "abstract_only"
        if candidate.get("abstract")
        else "snippet_only"
        if any(text.strip() for text in texts)
        else "unavailable"
    )
    provenance = list(candidate.get("source_fact_ids") or [])
    document_audit: dict[str, Any] = {
        "truncated": False,
        "truncated_sections": [],
        "source": "",
        "format": "",
        "url": "",
        "retrieval_trace": [],
    }
    for fact in source_facts.values():
        if fact.tool_name not in {"EuropePMC_get_full_text", "EuropePMC_get_fulltext"}:
            continue
        if not _publication_matches(fact, candidate):
            continue
        fact_texts = _document_strings(fact.features)
        if fact_texts:
            texts.extend(fact_texts)
            source_status = "available"
            metadata = fact.features.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            document_audit = {
                "truncated": fact.features.get("truncated") is True,
                "truncated_sections": list(
                    fact.features.get("truncated_sections") or []
                ),
                "source": str(
                    fact.features.get("source") or metadata.get("source") or ""
                ),
                "format": str(
                    fact.features.get("format") or metadata.get("format") or ""
                ),
                "url": str(fact.features.get("url") or metadata.get("url") or ""),
                "retrieval_trace": list(
                    fact.features.get("retrieval_trace")
                    or metadata.get("retrieval_trace")
                    or []
                ),
            }
        provenance.append(fact.fact_id)
    corpus = "\n".join(text for text in texts if text.strip())
    digest = hashlib.sha256(corpus.encode()).hexdigest() if corpus else ""
    return corpus, source_status, sorted(set(provenance)), digest, document_audit


def _sentence_units(text: str) -> list[tuple[int, str]]:
    units: list[tuple[int, str]] = []
    start = 0
    for match in re.finditer(r"(?<=[.!?])\s+|\n+", text):
        value = text[start : match.start()].strip()
        if value:
            offset = text.find(value, start, match.start())
            units.append((offset, value))
        start = match.end()
    value = text[start:].strip()
    if value:
        units.append((text.find(value, start), value))
    return units


def _identity_aliases(identity: dict[str, Any]) -> set[str]:
    aliases: set[str] = set()
    for key in ("validated_hgvs_c", "hgvs_c", "hgvs_g", "hgvs_p", "rsid"):
        value = str(identity.get(key) or "").strip()
        if not value:
            continue
        aliases.add(value.casefold())
        if ":" in value:
            aliases.add(value.split(":", 1)[1].casefold())
    normalization = identity.get("normalization")
    if isinstance(normalization, dict):
        for value in normalization.get("verified_hgvs_aliases") or []:
            token = str(value or "").strip()
            if token:
                aliases.add(token.casefold())
                if ":" in token:
                    aliases.add(token.split(":", 1)[1].casefold())
    return {value for value in aliases if len(value) >= 4}


def _direct_target_aliases(sentence: str, aliases: set[str]) -> list[str]:
    lowered = sentence.casefold()
    return sorted(alias for alias in aliases if alias in lowered)


def _target_link(
    sentence: str,
    previous_direct: bool,
    *,
    aliases: set[str],
    gene: str,
    match_class: str,
    fact_type: str,
) -> tuple[str, list[str]]:
    matched_aliases = _direct_target_aliases(sentence, aliases)
    if matched_aliases:
        return "direct_variant", matched_aliases
    if previous_direct and re.search(
        r"\b(?:this|the|that)\s+(?:variant|mutation|allele)|\bit\b",
        sentence,
        re.IGNORECASE,
    ):
        return "adjacent_explicit_referent", []
    gene_linked = bool(gene and re.search(rf"\b{re.escape(gene)}\b", sentence, re.I))
    if fact_type in {"mechanism", "region_hotspot", "protein_length_repeat"}:
        return ("direct_gene", []) if gene_linked else ("unlinked", [])
    if match_class == "same_residue_match" and re.search(
        r"\bp\.[A-Za-z*]{1,3}\d+", sentence, re.I
    ):
        return "same_residue", []
    if match_class == "provider_linked_variant_match" and re.search(
        r"\b(?:variant|mutation|allele)\b", sentence, re.I
    ):
        return "provider_linked", []
    return "unlinked", []


def _negated(fact_type: str, sentence: str, match: re.Match[str]) -> bool:
    if fact_type == "segregation" and re.search(
        r"did not segregate|non-?segregation", sentence, re.I
    ):
        return False
    if fact_type == "functional" and re.search(
        r"no (?:significant )?(?:difference|effect)|normal|wild[ -]?type",
        sentence,
        re.I,
    ):
        return False
    before = sentence[max(0, match.start() - 80) : match.start()]
    return bool(
        re.search(
            r"\b(?:not|never|without|failed to|no evidence (?:of|for)|"
            r"was not|were not|is not|are not)\b",
            before,
            re.IGNORECASE,
        )
    )


def _methodological_false_positive(fact_type: str, sentence: str) -> bool:
    if fact_type == "de_novo" and re.search(
        r"\bde[ -]?novo\s+(?:transcript|genome|sequence|assembly|annotation|prediction)",
        sentence,
        re.IGNORECASE,
    ):
        return True
    return False


def _case_count(excerpt: str) -> int:
    matches = re.findall(
        r"\b(\d{1,4})\s+(?:unrelated\s+)?(?:patients?|probands?|cases?|families)\b",
        excerpt,
        re.IGNORECASE,
    )
    return max((int(value) for value in matches), default=1)


def _pattern_specs() -> list[tuple[str, re.Pattern[str], str, str]]:
    flags = re.IGNORECASE
    return [
        (
            "case_control",
            re.compile(r"\b(?:odds ratio|\bOR\b)\s*[=:]?\s*(\d+(?:\.\d+)?)", flags),
            "PS4",
            "PS4",
        ),
        ("de_novo", re.compile(r"\bde[ -]?novo\b", flags), "PS2", "PS2"),
        (
            "recessive_allelic",
            re.compile(r"\b(?:in trans|compound heterozyg(?:ous|osity))\b", flags),
            "PM3",
            "PM3",
        ),
        (
            "functional",
            re.compile(
                r"\b(?:functional assay|luciferase|western blot|minigene|enzym(?:e|atic) activity|cell-based assay)\b",
                flags,
            ),
            "PS3",
            "PS3",
        ),
        (
            "segregation",
            re.compile(
                r"\b(?:co-?segregat(?:e|ed|es|ion)|did not segregate|non-?segregation)\b",
                flags,
            ),
            "PP1",
            "PP1",
        ),
        (
            "phenotype_specificity",
            re.compile(
                r"\b(?:highly specific phenotype|pathognomonic|phenotype highly specific)\b",
                flags,
            ),
            "PP4",
            "PP4",
        ),
        (
            "healthy_observation",
            re.compile(
                r"\b(?:healthy adult|unaffected adult|healthy control|unaffected individual)\b",
                flags,
            ),
            "BS2",
            "BS2",
        ),
        (
            "allelic_phase",
            re.compile(r"\b(?:in cis|in trans|co-occur(?:red|rence)?)\b", flags),
            "BP2",
            "BP2",
        ),
        (
            "alternative_cause",
            re.compile(
                r"\b(?:alternative (?:molecular )?diagnosis|another pathogenic variant|alternative cause)\b",
                flags,
            ),
            "BP5",
            "BP5",
        ),
        (
            "prior_variant",
            re.compile(
                r"\b(?:same amino acid|same residue|previously reported missense|known pathogenic variant)\b",
                flags,
            ),
            "PM5",
            "PM5",
        ),
        (
            "region_hotspot",
            re.compile(
                r"\b(?:mutational hot ?spot|critical functional domain|critical region)\b",
                flags,
            ),
            "PM1",
            "PM1",
        ),
        (
            "mechanism",
            re.compile(
                r"\b(?:haploinsufficiency|loss[ -]of[ -]function mechanism|missense mechanism|dominant negative)\b",
                flags,
            ),
            "PP2",
            "PP2",
        ),
        (
            "protein_length_repeat",
            re.compile(
                r"\b(?:repeat region|low complexity|protein length|in-frame deletion|in-frame insertion)\b",
                flags,
            ),
            "PM4",
            "PM4",
        ),
        (
            "rna_splicing",
            re.compile(
                r"\b(?:RNA analysis|RT-?PCR|minigene|exon skipping|aberrant splicing)\b",
                flags,
            ),
            "PVS1",
            "PVS1",
        ),
        (
            "case_series",
            re.compile(
                r"\b(?:case series|\d{1,4}\s+(?:unrelated\s+)?(?:patients?|probands?|cases?|families))\b",
                flags,
            ),
            "PS4",
            "PS4_Supporting",
        ),
    ]


def _values(
    fact_type: str,
    match: re.Match[str],
    excerpt: str,
    publication_id: str,
    *,
    inheritance: str,
) -> dict[str, Any]:
    atom_id = f"{publication_id}:{fact_type}:{match.start()}"
    values: dict[str, Any] = {
        "fact_id": atom_id,
        "inheritance_mode": inheritance,
    }
    if fact_type == "case_control":
        values.update(
            {
                "cohort_id": atom_id,
                "odds_ratio": float(match.group(1)),
                "ci_lower": None,
                "cases_independent": None,
            }
        )
        ci = re.search(
            r"(?:95%\s*CI|confidence interval)\s*[:=]?\s*[\[(]?(\d+(?:\.\d+)?)",
            excerpt,
            re.IGNORECASE,
        )
        if ci:
            values["ci_lower"] = float(ci.group(1))
    elif fact_type == "case_series":
        values.update(
            {
                "cohort_id": atom_id,
                "case_count": _case_count(excerpt),
                "cases_independent": None,
            }
        )
    elif fact_type == "de_novo":
        confirmed = bool(
            re.search(
                r"parentage|maternity and paternity|parental relationships? confirmed",
                excerpt,
                re.IGNORECASE,
            )
        )
        values.update(
            {
                "case_id": atom_id,
                "parental_relationships": "confirmed" if confirmed else "assumed",
                "phenotype_consistency": "consistent",
            }
        )
    elif fact_type == "recessive_allelic":
        values.update(
            {
                "case_id": atom_id,
                "zygosity": "compound_heterozygous",
                "phase": "confirmed_in_trans"
                if re.search(r"\bin trans\b", excerpt, re.IGNORECASE)
                else "unknown",
                "other_variant_classification": "VUS",
                "other_variant_frequency_eligible": False,
                "pm3_frequency_eligible": False,
            }
        )
    elif fact_type == "functional":
        benign = bool(
            re.search(
                r"normal|no (?:significant )?(?:difference|effect)|wild[ -]?type",
                excerpt,
                re.IGNORECASE,
            )
        )
        values.update(
            {
                "assay_instance_id": atom_id,
                "direction": "benign" if benign else "pathogenic",
                "core_definition_satisfied": False,
            }
        )
    elif fact_type == "segregation":
        benign = bool(
            re.search(r"did not segregate|non-?segregation", excerpt, re.IGNORECASE)
        )
        values.update(
            {
                "family_id": atom_id,
                "segregation_direction": "nonsegregation" if benign else "cosegregates",
                "direction": "benign" if benign else "pathogenic",
            }
        )
    elif fact_type == "healthy_observation":
        values.update({"individual_id": atom_id})
    elif fact_type in {"allelic_phase", "alternative_cause"}:
        values.update({"case_id": atom_id})
    elif fact_type == "prior_variant":
        values.update({"prior_variant_identity": atom_id})
    return values


def _other_variant(sentence: str, expected_variant: str) -> str:
    matches = re.findall(
        r"(?:(?:NM|NR|NC|NG)_\d+\.\d+:)?[cg]\.[A-Za-z0-9_+\-*>?]+",
        sentence,
        re.IGNORECASE,
    )
    expected = expected_variant.casefold()
    return next((value for value in matches if value.casefold() not in expected), "")


def _requirements(
    fact_type: str,
    sentence: str,
    values: dict[str, Any],
    *,
    target_link_status: str,
    expected_variant: str,
) -> tuple[str, list[str]]:
    missing: list[str] = []
    if target_link_status in {"unlinked", "provider_linked"}:
        missing.append("direct_target_variant_link")
    subject = re.search(
        r"\b(?:patient|proband|case|individual|family|child|offspring)s?\b",
        sentence,
        re.IGNORECASE,
    )
    if fact_type == "de_novo" and not subject:
        missing.append("proband_or_family")
    elif fact_type == "case_control":
        if values.get("odds_ratio") is None:
            missing.append("odds_ratio")
        if values.get("ci_lower") is None:
            missing.append("confidence_interval")
    elif fact_type == "case_series" and not subject:
        missing.append("case_series_subject")
    elif fact_type == "recessive_allelic":
        other = _other_variant(sentence, expected_variant)
        if not other:
            missing.append("second_allele_identity")
        else:
            values["other_variant"] = other
        if not re.search(r"\bin trans\b", sentence, re.I):
            missing.append("phase")
    elif fact_type == "functional":
        if not re.search(
            r"\b(?:reduced|increased|decreased|loss|gain|normal|abnormal|"
            r"no (?:significant )?(?:difference|effect))\b",
            sentence,
            re.I,
        ):
            missing.append("assay_result")
        if not re.search(
            r"\b(?:control|wild[ -]?type|negative|positive)\b", sentence, re.I
        ):
            missing.append("experimental_controls")
    elif fact_type == "segregation":
        if not re.search(r"\bfamil(?:y|ies)|pedigree|kindred\b", sentence, re.I):
            missing.append("family_identifier_or_context")
    elif fact_type == "phenotype_specificity" and not re.search(
        r"\b(?:diagnos|phenotype|syndrome|disease)\w*\b", sentence, re.I
    ):
        missing.append("specific_phenotype_context")
    elif fact_type == "healthy_observation" and not subject:
        missing.append("observed_individual")
    elif fact_type == "allelic_phase":
        other = _other_variant(sentence, expected_variant)
        if not other:
            missing.append("second_allele_identity")
        else:
            values["other_variant"] = other
    elif fact_type == "alternative_cause":
        other = _other_variant(sentence, expected_variant)
        if not other:
            missing.append("alternative_cause_identity")
        else:
            values["alternative_variant"] = other
    elif fact_type == "prior_variant":
        other = _other_variant(sentence, expected_variant)
        if not other:
            missing.append("prior_variant_identity")
        else:
            values["prior_variant_identity"] = other
    elif fact_type == "rna_splicing":
        if not re.search(r"\b(?:RT-?PCR|RNA analysis|minigene)\b", sentence, re.I):
            missing.append("rna_assay")
        if not re.search(
            r"\b(?:exon skipping|aberrant splicing|cryptic splice)\b", sentence, re.I
        ):
            missing.append("rna_result")
    return ("complete" if not missing else "incomplete"), sorted(set(missing))


def extract_literature_facts(
    candidates: list[dict[str, Any]],
    source_facts: dict[str, SourceFact],
    *,
    identity: dict[str, Any],
    disease: str = "",
    inheritance: str = "",
) -> dict[str, SourceFact]:
    """Return one SourceFact per deterministic, source-located evidence atom."""
    extracted: dict[str, SourceFact] = {}
    expected_variant = str(
        identity.get("validated_hgvs_c") or identity.get("hgvs_c") or ""
    )
    expected_gene = str(identity.get("gene") or "")
    for candidate in candidates:
        match_class = str(candidate.get("match_class") or "")
        if match_class not in {
            "exact_variant_match",
            "equivalent_variant_match",
            "provider_linked_variant_match",
            "mechanism_background",
            "same_residue_match",
        }:
            continue
        (
            corpus,
            source_status,
            provenance_ids,
            document_hash,
            document_audit,
        ) = _candidate_corpus(candidate, source_facts)
        if not corpus:
            continue
        publication_id = str(candidate.get("publication_id") or "")
        aliases = _identity_aliases(identity)
        units = _sentence_units(corpus)
        for fact_type, pattern, criterion, strength in _pattern_specs():
            if match_class == "mechanism_background" and fact_type not in {
                "mechanism",
                "region_hotspot",
                "protein_length_repeat",
            }:
                continue
            if match_class == "same_residue_match" and fact_type != "prior_variant":
                continue
            previous_direct = False
            for unit_offset, sentence in units:
                direct_here = bool(_direct_target_aliases(sentence, aliases))
                matches = list(pattern.finditer(sentence))
                for match in matches:
                    target_link_status, matched_aliases = _target_link(
                        sentence,
                        previous_direct,
                        aliases=aliases,
                        gene=expected_gene,
                        match_class=match_class,
                        fact_type=fact_type,
                    )
                    if target_link_status == "unlinked":
                        continue
                    if _methodological_false_positive(fact_type, sentence):
                        continue
                    negated = _negated(fact_type, sentence, match)
                    if negated:
                        continue
                    excerpt = " ".join(sentence.split())
                    absolute_start = unit_offset + match.start()
                    values = _values(
                        fact_type,
                        match,
                        excerpt,
                        publication_id,
                        inheritance=inheritance,
                    )
                    values["fact_id"] = f"{publication_id}:{fact_type}:{absolute_start}"
                    requirements_status, missing_requirements = _requirements(
                        fact_type,
                        sentence,
                        values,
                        target_link_status=target_link_status,
                        expected_variant=expected_variant,
                    )
                    semantic_status = (
                        "verified"
                        if requirements_status == "complete"
                        and target_link_status
                        in {
                            "direct_variant",
                            "adjacent_explicit_referent",
                            "direct_gene",
                            "same_residue",
                        }
                        else "unresolved"
                    )
                    payload = {
                        "publication_id": publication_id,
                        "fact_type": fact_type,
                        "values": values,
                        "excerpt": excerpt,
                        "document_hash": document_hash,
                        "target_link_status": target_link_status,
                        "requirements_status": requirements_status,
                    }
                    fact_hash = hashlib.sha256(
                        json.dumps(
                            payload,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ).encode()
                    ).hexdigest()
                    fact_id = f"acmg-literature-rule:v3:{fact_hash[:20]}"
                    identity_status = (
                        "matched"
                        if target_link_status
                        in {"direct_variant", "adjacent_explicit_referent"}
                        and match_class
                        in {"exact_variant_match", "equivalent_variant_match"}
                        else "partial"
                    )
                    independent = bool(
                        re.search(
                            r"\b(?:independent|unrelated)\s+(?:patients?|probands?|cases?|families)\b",
                            excerpt,
                            re.IGNORECASE,
                        )
                    )
                    reading_status = (
                        "partial"
                        if source_status == "available" and document_audit["truncated"]
                        else "complete"
                        if source_status == "available"
                        else source_status
                    )
                    extracted[fact_id] = SourceFact(
                        fact_id=fact_id,
                        tool_name="EuropePMC_get_full_text",
                        status="success",
                        query_identity={
                            "gene": expected_gene,
                            "hgvs_c": expected_variant,
                        },
                        result_identity={
                            "gene": expected_gene,
                            "hgvs_c": expected_variant,
                        },
                        features={
                            "fact_id": values["fact_id"],
                            "fact_type": fact_type,
                            "values": {
                                **values,
                                "variant_identity": expected_variant,
                                "gene": expected_gene,
                                "disease": disease,
                            },
                            "pmid": candidate.get("pmid"),
                            "pmcid": candidate.get("pmcid"),
                            "criterion": criterion,
                            "suggested_strength": strength,
                            "anchor_status": "verified"
                            if identity_status == "matched"
                            else "provider_linked",
                            "target_link_status": target_link_status,
                            "matched_variant_aliases": matched_aliases,
                            "semantic_status": semantic_status,
                            "requirements_status": requirements_status,
                            "missing_requirements": missing_requirements,
                            "negation_status": "not_negated",
                            "extraction_method": "rule_extracted",
                            "extractor": {
                                "name": EXTRACTOR_ID,
                                "version": EXTRACTOR_VERSION,
                            },
                            "document_hash": document_hash,
                            "document_source": document_audit["source"]
                            or source_status,
                            "document_format": document_audit["format"],
                            "document_url": document_audit["url"],
                            "retrieval_trace": document_audit["retrieval_trace"],
                            "document_truncated": document_audit["truncated"],
                            "truncated_sections": document_audit["truncated_sections"],
                            "reading_manifest": {
                                "status": reading_status,
                                "document_hash": document_hash,
                                "limitations": (
                                    ["provider response was truncated"]
                                    if document_audit["truncated"]
                                    else []
                                ),
                            },
                        },
                        raw_result_hash=document_hash or fact_hash,
                        provider_version=EXTRACTOR_VERSION,
                        request_arguments={"publication_id": publication_id},
                        provenance=tuple([publication_id, *provenance_ids]),
                        excerpt=excerpt,
                        locator=(
                            f"{source_status}:char:{absolute_start}-"
                            f"{absolute_start + len(match.group(0))}"
                        ),
                        verification_level="deterministic_rule_extraction",
                        identity_status=identity_status,
                        source_status=source_status,
                        extraction_status="rule_extracted",
                        version_status="versioned",
                        disease_match_status="candidate" if disease else "unspecified",
                        independence_status="independent" if independent else "unknown",
                    )
                previous_direct = direct_here
    return extracted


__all__ = [
    "EXTRACTOR_ID",
    "EXTRACTOR_VERSION",
    "MINIMUM_FACT_REQUIREMENTS",
    "TARGET_LINK_POLICY_VERSION",
    "extract_literature_facts",
]
