"""Resolve identity-bound consequence observations across upstream providers."""

from __future__ import annotations

from typing import Any

from .models import SourceFact, fact_identity_matches, fact_is_available


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


def _term_sets_connected(rows: list[dict[str, Any]]) -> bool:
    """Accept overlapping provider term sets without treating extras as conflict."""
    term_sets = [
        set(row.get("consequence_terms") or [])
        for row in rows
        if row.get("consequence_terms")
    ]
    if len(term_sets) < 2:
        return True
    connected = {0}
    frontier = [0]
    while frontier:
        left_index = frontier.pop()
        for right_index, right in enumerate(term_sets):
            if right_index in connected:
                continue
            if term_sets[left_index] & right:
                connected.add(right_index)
                frontier.append(right_index)
    return len(connected) == len(term_sets)


def _protein_change(value: Any) -> str:
    """Compare protein changes independently of RefSeq/Ensembl accessions."""
    normalized = _text(value).casefold()
    return normalized.rsplit(":", 1)[-1]


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
    if selected_base and any(
        _base(value) == selected_base for value in candidates if value
    ):
        return "version_compatible", 2
    if selected_base and mane and _base(mane) == selected_base:
        return "mane_mapped", 1
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
            observations.append(
                {
                    "source_fact_id": fact.fact_id,
                    "provider": fact.tool_name,
                    "provider_version": fact.provider_version,
                    "annotation_method": CONSEQUENCE_METHODS[fact.tool_name],
                    "query_representation": dict(fact.request_arguments),
                    "identity_status": (fact.identity_status),
                    "selected_transcript_status": "unknown",
                    "source_available": False,
                    "limitation": "no_transcript_consequence_rows",
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
                "transcript": transcript,
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
    identity_conflicts = [
        row for row in observations if row.get("identity_status") == "conflict"
    ]
    if identity_conflicts:
        return {
            "status": "identity_conflict",
            "reason": "consequence_provider_identity_conflict",
            "selected_observation": None,
            "selected_source_fact_ids": [],
            "corroborating_source_fact_ids": [],
            "conflicts": [
                {
                    "type": "provider_identity_conflict",
                    "provider": row.get("provider"),
                    "source_fact_id": row.get("source_fact_id"),
                    "transcript": row.get("transcript"),
                    "consequence_terms": list(row.get("consequence_terms") or []),
                }
                for row in identity_conflicts
            ],
            "failures": [],
        }
    ready = [
        row
        for row in observations
        if row.get("source_available") is True and int(row.get("_match_rank", 99)) <= 2
    ]
    failures = [
        {key: value for key, value in row.items() if not key.startswith("_")}
        for row in observations
        if row.get("source_available") is not True
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
        }

    best_rank = min(int(row["_match_rank"]) for row in ready)
    best = [row for row in ready if int(row["_match_rank"]) == best_rank]
    term_sets = {
        tuple(row.get("consequence_terms") or [])
        for row in best
        if row.get("consequence_terms")
    }
    protein_values = {
        _protein_change(row.get("hgvs_p")) for row in best if _text(row.get("hgvs_p"))
    }
    conflicts: list[dict[str, Any]] = []
    if not _term_sets_connected(best):
        conflicts.append(
            {
                "type": "selected_transcript_consequence_conflict",
                "values": [list(value) for value in sorted(term_sets)],
                "source_fact_ids": sorted({str(row["source_fact_id"]) for row in best}),
            }
        )
    if len(protein_values) > 1:
        conflicts.append(
            {
                "type": "selected_transcript_protein_consequence_conflict",
                "values": sorted(protein_values),
                "source_fact_ids": sorted({str(row["source_fact_id"]) for row in best}),
            }
        )
    if conflicts:
        return {
            "status": "identity_conflict",
            "reason": "identity_bound_consequence_sources_disagree",
            "selected_observation": None,
            "selected_source_fact_ids": [],
            "corroborating_source_fact_ids": [],
            "conflicts": conflicts,
            "failures": failures,
        }

    selected = min(best, key=lambda row: int(row.get("_provider_rank", 99)))
    selected_id = str(selected["source_fact_id"])
    corroborating = sorted(
        {
            str(row["source_fact_id"])
            for row in best
            if str(row["source_fact_id"]) != selected_id
        }
    )
    clean_selected = {
        key: value for key, value in selected.items() if not key.startswith("_")
    }
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
        "transcript_mapping": {
            "requested": identity.get("transcript"),
            "selected": selected.get("transcript"),
            "ensembl_transcript": clean_selected.get("ensembl_transcript"),
            "mane_select": selected.get("mane_select"),
            "status": selected.get("selected_transcript_status"),
        },
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
    "CONSEQUENCE_METHODS",
    "consequence_observations",
    "profile_features_from_resolution",
    "resolve_consequence_observations",
]
