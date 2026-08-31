"""Resolve identity-bound consequence observations across upstream providers."""

from __future__ import annotations

import re
from typing import Any

from .models import SourceFact, fact_identity_matches, fact_is_available
from .source_adapters import explicit_allele_conflict


CONSEQUENCE_CONFLICT_POLICY_VERSION = "2026-08-15-v5"
INPUT_CONSEQUENCE_FALLBACK_POLICY_VERSION = "2026-08-25-v1"
_INTRONIC_HGVS_RE = re.compile(r"c\.[*+-]?\d+(?P<offset>[+-]\d+)", re.IGNORECASE)


CONSEQUENCE_METHODS = {
    "EnsemblVEP_annotate_hgvs": "vep_derived",
    "EnsemblVEP_annotate_rsid": "vep_derived",
    "ensembl_vep_region": "vep_derived",
    "VariantValidator_validate_variant": "independent",
    "VariantValidator_format_genomic_to_transcripts": "independent",
    "FAVOR_annotate_variant": "aggregation",
    "OpenTargets_get_variant_info": "vep_derived",
    "OpenTargets_get_variant_transcript_consequences": "vep_derived",
    "Mutalyzer_normalize_variant": "independent",
    "GenomeNexus_annotate_variant": "vep_derived",
    "GenomeNexus_annotate_dbsnp": "vep_derived",
    "ProtVar_map_variant": "aggregation",
    "gProfiler_annotate_snps": "aggregation",
}

CONSEQUENCE_PROVIDER_ROLES = {
    "EnsemblVEP_annotate_hgvs": "authoritative",
    "EnsemblVEP_annotate_rsid": "authoritative",
    "ensembl_vep_region": "authoritative",
    "VariantValidator_validate_variant": "authoritative",
    "VariantValidator_format_genomic_to_transcripts": "authoritative",
    "FAVOR_annotate_variant": "aggregation",
    "OpenTargets_get_variant_info": "aggregation",
    "OpenTargets_get_variant_transcript_consequences": "aggregation",
    "GenomeNexus_annotate_variant": "aggregation",
    "GenomeNexus_annotate_dbsnp": "aggregation",
    "ProtVar_map_variant": "aggregation",
    "Mutalyzer_normalize_variant": "normalization_context",
    "gProfiler_annotate_snps": "normalization_context",
}

_PROVIDER_PRIORITY = {
    "EnsemblVEP_annotate_hgvs": 0,
    "VariantValidator_format_genomic_to_transcripts": 1,
    "VariantValidator_validate_variant": 2,
    "FAVOR_annotate_variant": 3,
    "OpenTargets_get_variant_transcript_consequences": 4,
    "Mutalyzer_normalize_variant": 5,
    "GenomeNexus_annotate_variant": 6,
    "EnsemblVEP_annotate_rsid": 7,
    "ensembl_vep_region": 8,
    "OpenTargets_get_variant_info": 9,
    "ProtVar_map_variant": 10,
    "gProfiler_annotate_snps": 11,
}


def _provider_role(row: dict[str, Any]) -> str:
    return str(
        row.get("provider_role")
        or CONSEQUENCE_PROVIDER_ROLES.get(
            str(row.get("provider") or ""), "normalization_context"
        )
    )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _base(value: Any) -> str:
    return _text(value).split(":", 1)[0].split(".", 1)[0].casefold()


def _versioned(value: Any) -> str:
    return _text(value).split(":", 1)[0].casefold()


def _terms(row: dict[str, Any]) -> list[str]:
    values = row.get("consequence") or row.get("consequence_terms") or []
    if isinstance(values, str):
        values = [values]
    return sorted(
        {_text(value).casefold().replace(" ", "_") for value in values if _text(value)}
    )


def _protein_change(value: Any) -> str:
    """Compare protein changes independently of RefSeq/Ensembl accessions."""
    normalized = _text(value).casefold()
    return normalized.rsplit(":", 1)[-1]


def _explicit_identity_mismatch(
    identity: dict[str, Any], observation: dict[str, Any]
) -> bool:
    """Detect only explicit allele/build disagreement.

    A different transcript is an expected annotation of the same genomic
    allele and is deliberately not part of this check.
    """
    return explicit_allele_conflict(
        identity,
        {
            "build": observation.get("build"),
            "coordinates": observation.get("allele") or {},
        },
    )


def _conflict_class(identity: dict[str, Any], observation: dict[str, Any]) -> str:
    match_rank = int(observation.get("_match_rank", 99))
    if _explicit_identity_mismatch(identity, observation):
        return (
            "hard_identity_conflict"
            if _provider_role(observation) == "authoritative"
            else "nonblocking_allele_disagreement"
        )
    if match_rank >= 3:
        if (
            _text(observation.get("transcript"))
            or _text(observation.get("hgvs_c")).split(":", 1)[0]
        ):
            return "alternate_transcript_observation"
        return ""
    return ""


def _equivalent_or_alternate_representations(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep provider HGVS labels without treating string differences as vetoes."""
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for observation in observations:
        for representation_type in ("hgvs_c", "hgvs_g"):
            value = _text(observation.get(representation_type))
            if not value:
                continue
            key = (str(observation.get("provider") or ""), representation_type, value)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "provider": observation.get("provider"),
                    "source_fact_id": observation.get("source_fact_id"),
                    "provider_role": _provider_role(observation),
                    "representation_type": representation_type,
                    "value": value,
                    "transcript_match_status": observation.get(
                        "transcript_match_status"
                    ),
                }
            )
    return rows


def _gene_match_status(identity: dict[str, Any], observation: dict[str, Any]) -> str:
    expected = _text(identity.get("gene")).casefold()
    observed = _text(observation.get("gene")).casefold()
    if not observed:
        return "unknown"
    if not expected:
        return "unresolved"
    return "matched" if observed == expected else "alternate_annotation"


def _target_binding_status(gene_match_status: str, transcript_match_status: str) -> str:
    if transcript_match_status in {"exact", "mane_mapped", "version_compatible"}:
        return "matched" if gene_match_status != "alternate_annotation" else "partial"
    if transcript_match_status in {"other", "other_canonical"}:
        return "alternate_transcript"
    return "unknown"


def _transcript_match(row: dict[str, Any], selected_transcript: str) -> tuple[str, int]:
    selected_versioned = _versioned(selected_transcript)
    selected_base = _base(selected_transcript)
    transcript = _text(
        row.get("transcript") or row.get("reference") or row.get("transcript_id")
    )
    mane = _text(row.get("mane_select") or row.get("mane_transcript"))
    hgvsc_transcript = _text(row.get("hgvsc") or row.get("hgvs_c")).split(":", 1)[0]
    candidates = [transcript, mane, hgvsc_transcript]
    if selected_versioned and any(
        _versioned(value) == selected_versioned for value in candidates if value
    ):
        return "exact", 0
    if selected_base and mane and _base(mane) == selected_base:
        return "mane_mapped", 1
    if selected_base and any(
        _base(value) == selected_base
        for value in (transcript, hgvsc_transcript)
        if value
    ):
        return "version_compatible", 2
    if row.get("canonical") is True or row.get("is_canonical") is True:
        return "other_canonical", 3
    return "other", 4


def consequence_observations(
    identity: dict[str, Any],
    source_facts: dict[str, SourceFact],
) -> list[dict[str, Any]]:
    """Return normalized, fully auditable observations from consequence facts."""
    selected_transcript = _text(identity.get("transcript"))
    observations: list[dict[str, Any]] = []
    for fact in source_facts.values():
        if fact.tool_name not in CONSEQUENCE_METHODS:
            continue
        features = fact.features if isinstance(fact.features, dict) else {}
        rows = features.get("consequence_candidates")
        if not isinstance(rows, list):
            rows = features.get("vep_transcript_candidates")
        rows = [row for row in rows or [] if isinstance(row, dict)]
        if not rows and features.get("most_severe_consequence"):
            rows = [
                {
                    "gene": features.get("gene"),
                    "transcript": features.get("transcript"),
                    "hgvsc": features.get("hgvs_c"),
                    "hgvsp": features.get("hgvs_p"),
                    "consequence": [features["most_severe_consequence"]],
                    "canonical": features.get("canonical"),
                }
            ]
        if not rows:
            hard_conflict = bool(
                fact.identity_status == "conflict"
                and _explicit_identity_mismatch(
                    identity,
                    {
                        "build": fact.result_identity.get("build"),
                        "allele": fact.result_identity.get("coordinates") or {},
                    },
                )
            )
            observations.append(
                {
                    "source_fact_id": fact.fact_id,
                    "provider": fact.tool_name,
                    "provider_version": fact.provider_version,
                    "annotation_method": CONSEQUENCE_METHODS[fact.tool_name],
                    "provider_role": CONSEQUENCE_PROVIDER_ROLES[fact.tool_name],
                    "query_representation": dict(fact.request_arguments),
                    "identity_status": (fact.identity_status),
                    "allele_match_status": fact.identity_status,
                    "gene_match_status": "unknown",
                    "transcript_match_status": "unknown",
                    "target_binding_status": "unknown",
                    "selected_transcript_status": "unknown",
                    "source_available": False,
                    "limitation": "no_transcript_consequence_rows",
                    "observation_role": (
                        "hard_conflict" if hard_conflict else "unavailable"
                    ),
                    "conflict_class": (
                        "hard_identity_conflict" if hard_conflict else ""
                    ),
                    "_match_rank": 0 if hard_conflict else 99,
                    "_provider_rank": _PROVIDER_PRIORITY.get(fact.tool_name, 99),
                }
            )
            continue
        for row in rows:
            match_status, match_rank = _transcript_match(row, selected_transcript)
            transcript = _text(
                row.get("transcript")
                or row.get("reference")
                or row.get("transcript_id")
            )
            terms = _terms(row)
            observation = {
                "source_fact_id": fact.fact_id,
                "provider": fact.tool_name,
                "provider_version": fact.provider_version,
                "annotation_method": CONSEQUENCE_METHODS[fact.tool_name],
                "provider_role": CONSEQUENCE_PROVIDER_ROLES[fact.tool_name],
                "query_representation": dict(fact.request_arguments),
                "build": (
                    fact.result_identity.get("build")
                    or fact.result_identity.get("assembly")
                    or features.get("build")
                    or features.get("assembly")
                ),
                "allele": fact.result_identity.get("coordinates")
                or features.get("coordinates")
                or {},
                "gene": _text(row.get("gene") or features.get("gene")),
                "provider_gene_label": _text(
                    row.get("provider_gene_label")
                    or features.get("provider_gene_label")
                ),
                "transcript": transcript,
                "provider_transcript_label": _text(
                    row.get("provider_transcript_label")
                    or features.get("provider_transcript_label")
                ),
                "mane_select": row.get("mane_select"),
                "hgvs_c": _text(row.get("hgvsc") or row.get("hgvs_c")),
                "hgvs_p": _text(row.get("hgvsp") or row.get("hgvs_p")),
                "consequence_terms": terms,
                "impact": row.get("impact"),
                "biotype": row.get("biotype"),
                "exon": row.get("exon"),
                "protein_position": row.get("protein_start")
                or row.get("protein_position"),
                "canonical": row.get("canonical") or row.get("is_canonical"),
                "identity_status": (fact.identity_status),
                "allele_match_status": fact.identity_status,
                "selected_transcript_status": match_status,
                "source_available": bool(
                    fact_is_available(fact)
                    and fact_identity_matches(fact)
                    and match_rank <= 2
                    and terms
                ),
                "_match_rank": match_rank,
                "_provider_rank": _PROVIDER_PRIORITY.get(fact.tool_name, 99),
            }
            observation["gene_match_status"] = _gene_match_status(identity, observation)
            observation["transcript_match_status"] = match_status
            observation["target_binding_status"] = _target_binding_status(
                observation["gene_match_status"], match_status
            )
            observation["conflict_class"] = _conflict_class(identity, observation)
            observation["observation_role"] = (
                "hard_conflict"
                if observation["conflict_class"] == "hard_identity_conflict"
                else "alternate_transcript"
                if observation["conflict_class"] == "alternate_transcript_observation"
                else "context_only"
            )
            observations.append(observation)
    return sorted(
        observations,
        key=lambda row: (
            int(row.get("_match_rank", 99)),
            int(row.get("_provider_rank", 99)),
            str(row.get("provider") or ""),
            str(row.get("transcript") or ""),
        ),
    )


def resolve_consequence_observations(
    identity: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select one transcript-bound consequence without majority voting."""

    def clean(row: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in row.items() if not key.startswith("_")}

    def observations_compatible(left: dict[str, Any], right: dict[str, Any]) -> bool:
        left_terms = set(left.get("consequence_terms") or [])
        right_terms = set(right.get("consequence_terms") or [])
        if left_terms and right_terms and not left_terms.intersection(right_terms):
            return False
        left_protein = _protein_change(left.get("hgvs_p"))
        right_protein = _protein_change(right.get("hgvs_p"))
        return not (left_protein and right_protein and left_protein != right_protein)

    identity_conflicts = [
        row
        for row in observations
        if row.get("conflict_class") == "hard_identity_conflict"
    ]
    alternate_transcripts = [
        clean(row)
        for row in observations
        if row.get("conflict_class") == "alternate_transcript_observation"
    ]
    representations = _equivalent_or_alternate_representations(observations)
    if identity_conflicts:
        return {
            "status": "identity_conflict",
            "reason": "consequence_provider_identity_conflict",
            "selected_observation": None,
            "selected_source_fact_ids": [],
            "corroborating_source_fact_ids": [],
            "conflicts": [
                {
                    "type": "hard_identity_conflict",
                    "provider": row.get("provider"),
                    "source_fact_id": row.get("source_fact_id"),
                    "transcript": row.get("transcript"),
                    "consequence_terms": list(row.get("consequence_terms") or []),
                }
                for row in identity_conflicts
            ],
            "failures": [],
            "hard_identity_conflicts": [clean(row) for row in identity_conflicts],
            "selected_transcript_conflicts": [],
            "alternate_transcript_observations": alternate_transcripts,
            "nonblocking_disagreements": [],
            "equivalent_or_alternate_representations": representations,
            "resolution_confidence": "unresolved",
            "automatic_usable": False,
            "verified_usable": False,
        }
    ready = [
        row
        for row in observations
        if row.get("source_available") is True
        and int(row.get("_match_rank", 99)) <= 2
        and _provider_role(row) in {"authoritative", "aggregation"}
    ]
    failures = [
        clean(row)
        for row in observations
        if row.get("source_available") is not True
        and row.get("conflict_class") != "alternate_transcript_observation"
    ]
    if not ready:
        return {
            "status": "unavailable",
            "reason": "no_identity_bound_selected_transcript_consequence",
            "selected_observation": None,
            "selected_source_fact_ids": [],
            "corroborating_source_fact_ids": [],
            "conflicts": [],
            "failures": failures,
            "hard_identity_conflicts": [],
            "selected_transcript_conflicts": [],
            "alternate_transcript_observations": alternate_transcripts,
            "nonblocking_disagreements": [],
            "equivalent_or_alternate_representations": representations,
            "resolution_confidence": "unresolved",
            "automatic_usable": False,
            "verified_usable": False,
        }

    best_rank = min(int(row["_match_rank"]) for row in ready)
    best = [row for row in ready if int(row["_match_rank"]) == best_rank]
    authoritative = [row for row in best if _provider_role(row) == "authoritative"]
    selection_pool = (
        authoritative
        or [row for row in best if _provider_role(row) == "aggregation"]
        or best
    )
    selected = min(selection_pool, key=lambda row: int(row.get("_provider_rank", 99)))
    blocking_conflicts: list[dict[str, Any]] = []
    nonblocking_disagreements: list[dict[str, Any]] = []
    corroborating_rows: list[dict[str, Any]] = []
    for row in best:
        if row is selected:
            continue
        if observations_compatible(selected, row):
            corroborating_rows.append(row)
            continue
        disagreement = {
            "type": "selected_transcript_provider_disagreement",
            "selected_source_fact_id": selected.get("source_fact_id"),
            "other_source_fact_id": row.get("source_fact_id"),
            "selected_provider": selected.get("provider"),
            "other_provider": row.get("provider"),
            "selected_consequence_terms": list(selected.get("consequence_terms") or []),
            "other_consequence_terms": list(row.get("consequence_terms") or []),
            "selected_hgvs_p": selected.get("hgvs_p"),
            "other_hgvs_p": row.get("hgvs_p"),
        }
        if (
            _provider_role(selected) == "authoritative"
            and _provider_role(row) == "authoritative"
        ):
            disagreement["type"] = "selected_transcript_conflict"
            blocking_conflicts.append(disagreement)
            row["observation_role"] = "hard_conflict"
        else:
            nonblocking_disagreements.append(disagreement)
            row["observation_role"] = "disputed"
    if blocking_conflicts:
        return {
            "status": "identity_conflict",
            "reason": "identity_bound_consequence_sources_disagree",
            "selected_observation": None,
            "selected_source_fact_ids": [],
            "corroborating_source_fact_ids": [],
            "conflicts": blocking_conflicts,
            "failures": failures,
            "hard_identity_conflicts": [],
            "selected_transcript_conflicts": blocking_conflicts,
            "alternate_transcript_observations": alternate_transcripts,
            "nonblocking_disagreements": nonblocking_disagreements,
            "equivalent_or_alternate_representations": representations,
            "resolution_confidence": "unresolved",
            "automatic_usable": False,
            "verified_usable": False,
        }

    selected["observation_role"] = "selected"
    for row in corroborating_rows:
        row["observation_role"] = "corroborating"
    selected_id = str(selected["source_fact_id"])
    corroborating = sorted(
        {
            str(row["source_fact_id"])
            for row in corroborating_rows
            if str(row["source_fact_id"]) != selected_id
        }
    )
    selected_is_authoritative = _provider_role(selected) == "authoritative"
    target_binding_partial = selected.get("target_binding_status") == "partial"
    if target_binding_partial:
        nonblocking_disagreements.append(
            {
                "type": "selected_provider_target_binding_partial",
                "source_fact_id": selected_id,
                "provider": selected.get("provider"),
                "gene_match_status": selected.get("gene_match_status"),
                "transcript_match_status": selected.get("transcript_match_status"),
            }
        )
    authoritative_corroboration = any(
        _provider_role(row) == "authoritative" for row in corroborating_rows
    )
    if selected_is_authoritative and nonblocking_disagreements:
        confidence = "disputed"
    elif selected_is_authoritative and authoritative_corroboration:
        confidence = "authoritative_corroborated"
    elif selected_is_authoritative:
        confidence = "authoritative_single_source"
    else:
        confidence = "source_backed_only"
    clean_selected = clean(selected)
    ensembl_transcripts = {
        _text(row.get("transcript"))
        for row in best
        if _text(row.get("transcript")).upper().startswith("ENST")
    }
    if len(ensembl_transcripts) == 1:
        clean_selected["ensembl_transcript"] = next(iter(ensembl_transcripts))
    return {
        "status": "resolved",
        "reason": f"selected_{selected['selected_transcript_status']}_transcript_consequence",
        "selected_observation": clean_selected,
        "selected_source_fact_ids": [selected_id, *corroborating],
        "corroborating_source_fact_ids": corroborating,
        "conflicts": [],
        "failures": failures,
        "hard_identity_conflicts": [],
        "selected_transcript_conflicts": [],
        "alternate_transcript_observations": alternate_transcripts,
        "nonblocking_disagreements": nonblocking_disagreements,
        "equivalent_or_alternate_representations": representations,
        "resolution_confidence": confidence,
        "automatic_usable": True,
        "verified_usable": bool(
            selected_is_authoritative and not nonblocking_disagreements
        ),
        "transcript_mapping": {
            "requested": identity.get("transcript"),
            "selected": selected.get("transcript"),
            "ensembl_transcript": clean_selected.get("ensembl_transcript"),
            "mane_select": selected.get("mane_select"),
            "status": selected.get("selected_transcript_status"),
        },
    }


def apply_input_intronic_fallback(
    identity: dict[str, Any],
    observations: list[dict[str, Any]],
    resolution: dict[str, Any],
) -> dict[str, Any]:
    """Expose an identity-bound HGVS intron observation when providers are empty."""
    if resolution.get("status") in {"resolved", "identity_conflict"}:
        return resolution
    hgvs_c = _text(identity.get("validated_hgvs_c") or identity.get("hgvs_c"))
    transcript = _text(identity.get("transcript"))
    offsets = [
        int(match.group("offset")) for match in _INTRONIC_HGVS_RE.finditer(hgvs_c)
    ]
    if not transcript or not any(abs(offset) > 2 for offset in offsets):
        return resolution
    selected = {
        "provider": "submitted_hgvs_syntax",
        "provider_role": "input_context",
        "annotation_method": "input_syntax",
        "observation_role": "selected",
        "gene": identity.get("gene"),
        "transcript": transcript,
        "hgvs_c": hgvs_c,
        "consequence_terms": ["intron_variant"],
        "allele_match_status": "matched",
        "gene_match_status": "matched" if identity.get("gene") else "unknown",
        "transcript_match_status": "exact",
        "target_binding_status": "matched",
        "limitation": "provider_consequence_unavailable_input_syntax_only",
        "policy_version": INPUT_CONSEQUENCE_FALLBACK_POLICY_VERSION,
    }
    return {
        **resolution,
        "status": "resolved",
        "reason": "selected_transcript_intronic_hgvs_input_observation",
        "selected_observation": selected,
        "selected_source_fact_ids": [],
        "corroborating_source_fact_ids": [],
        "conflicts": [],
        "nonblocking_disagreements": [
            {
                "type": "provider_consequence_unavailable_input_syntax_used",
                "hgvs_c": hgvs_c,
            }
        ],
        "resolution_confidence": "source_backed_only",
        "automatic_usable": True,
        "verified_usable": False,
        "transcript_mapping": {
            "requested": transcript,
            "selected": transcript,
            "status": "exact",
        },
        "input_observation": selected,
        "observations": [
            *[
                {key: value for key, value in row.items() if not key.startswith("_")}
                for row in observations
            ],
            selected,
        ],
    }


def profile_features_from_resolution(resolution: dict[str, Any]) -> dict[str, Any]:
    """Adapt a selected observation to the established profile builder."""
    selected = resolution.get("selected_observation")
    if not isinstance(selected, dict):
        return {}
    row = {
        "gene": selected.get("gene"),
        "transcript": selected.get("transcript"),
        "mane_select": selected.get("mane_select"),
        "hgvsc": selected.get("hgvs_c"),
        "hgvsp": selected.get("hgvs_p"),
        "consequence": list(selected.get("consequence_terms") or []),
        "impact": selected.get("impact"),
        "biotype": selected.get("biotype"),
        "exon": selected.get("exon"),
        "protein_start": selected.get("protein_position"),
        "canonical": selected.get("canonical"),
    }
    return {
        "vep_transcript_candidates": [row],
        "most_severe_consequence": next(
            iter(selected.get("consequence_terms") or []), None
        ),
    }


__all__ = [
    "CONSEQUENCE_CONFLICT_POLICY_VERSION",
    "INPUT_CONSEQUENCE_FALLBACK_POLICY_VERSION",
    "CONSEQUENCE_METHODS",
    "CONSEQUENCE_PROVIDER_ROLES",
    "apply_input_intronic_fallback",
    "consequence_observations",
    "profile_features_from_resolution",
    "resolve_consequence_observations",
]
