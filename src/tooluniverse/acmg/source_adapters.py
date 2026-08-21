"""Provider-specific identity and readiness checks for ACMG SourceFacts.

This module intentionally contains explicit checks for the small set of
providers used by the collector. It is not a generic adapter framework.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from .spliceai import normalize_spliceai_profile, walker_run_metadata_ready


_GNOMAD_DATASET_BUILDS = {
    "gnomad_r4": "GRCh38",
    "gnomad_r4_non_ukb": "GRCh38",
    "gnomad_r3": "GRCh38",
    "gnomad_r3_controls_and_biobanks": "GRCh38",
    "gnomad_r3_non_cancer": "GRCh38",
    "gnomad_r3_non_neuro": "GRCh38",
    "gnomad_r3_non_topmed": "GRCh38",
    "gnomad_r3_non_v2": "GRCh38",
    "gnomad_r2_1": "GRCh37",
    "gnomad_r2_1_controls": "GRCh37",
    "gnomad_r2_1_non_neuro": "GRCh37",
    "gnomad_r2_1_non_cancer": "GRCh37",
    "gnomad_r2_1_non_topmed": "GRCh37",
    "exac": "GRCh37",
}


def _drop_empty(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in (None, "")}


def provider_version(features: dict[str, Any]) -> str:
    for key in (
        "provider_version",
        "dataset",
        "population_version",
        "version",
        "release",
    ):
        value = features.get(key)
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            continue
        if isinstance(value, float) and not math.isfinite(value):
            continue
        if value not in (None, ""):
            return str(value)
    return ""


def coordinates(values: dict[str, Any]) -> dict[str, Any] | None:
    chrom = values.get("chr") or values.get("chrom") or values.get("chromosome")
    pos = values.get("pos") or values.get("position")
    ref = values.get("ref") or values.get("reference")
    alt = values.get("alt") or values.get("alternate")
    if chrom and pos and ref and alt:
        try:
            return {
                "chr": str(chrom).removeprefix("chr"),
                "pos": int(pos),
                "ref": str(ref),
                "alt": str(alt),
            }
        except (TypeError, ValueError):
            return None
    return None


def _coordinates_from_variant_id(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str):
        return None
    parts = value.removeprefix("chr").split("-")
    if len(parts) == 4:
        return coordinates(
            {"chr": parts[0], "pos": parts[1], "ref": parts[2], "alt": parts[3]}
        )
    match = re.fullmatch(r"(?:chr)?([^:]+):g\.(\d+)([A-Za-z]+)>([A-Za-z]+)", value)
    if not match:
        return None
    return coordinates(
        {
            "chr": match.group(1),
            "pos": match.group(2),
            "ref": match.group(3),
            "alt": match.group(4),
        }
    )


def result_identity(features: dict[str, Any]) -> dict[str, Any]:
    """Extract only identity fields from a provider-normalized feature map."""
    identity: dict[str, Any] = {}
    variant_coordinates = coordinates(features) or _coordinates_from_variant_id(
        features.get("variant_id") or features.get("_id")
    )
    if variant_coordinates:
        identity["coordinates"] = variant_coordinates
    for key in (
        "rsid",
        "hgvs_c",
        "validated_hgvs_c",
        "hgvs_g",
        "hgvs_p",
        "gene",
        "transcript",
        "build",
        "assembly",
        "genome_build",
        "variation_id",
        "clinvar_variation_id",
        "protein_accession",
        "protein_position",
    ):
        value = features.get(key)
        if value not in (None, ""):
            identity[key] = value
    for list_key in ("hgvsc_candidates", "hgvsg_candidates"):
        values = features.get(list_key)
        if isinstance(values, list) and values:
            identity[list_key] = [str(value) for value in values if value]
    if not identity.get("build") and features.get("reference_genome"):
        identity["build"] = features["reference_genome"]
    return identity


def has_variant_identity(identity: dict[str, Any]) -> bool:
    """Return true only for a provider-returned variant-level identifier."""
    return bool(
        identity.get("coordinates")
        or identity.get("rsid")
        or identity.get("hgvs_c")
        or identity.get("validated_hgvs_c")
        or identity.get("hgvs_g")
    )


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _build(value: Any) -> str:
    normalized = _norm(value).replace("grch", "").replace("hg", "")
    return normalized


def explicit_allele_conflict(
    expected: dict[str, Any], observed: dict[str, Any]
) -> bool:
    """Return true only for a directly comparable build or genomic allele clash.

    HGVS strings are deliberately excluded: repeat-normalized descriptions may
    differ while representing the same allele.  Such rows remain visible but
    cannot veto a coordinate-bound identity.
    """
    expected_build = _build(
        expected.get("build")
        or expected.get("assembly")
        or expected.get("genome_build")
    )
    observed_build = _build(
        observed.get("build")
        or observed.get("assembly")
        or observed.get("genome_build")
    )
    if expected_build and observed_build and expected_build != observed_build:
        return True

    expected_coordinates = expected.get("coordinates")
    observed_coordinates = observed.get("coordinates")
    if not isinstance(expected_coordinates, dict) or not isinstance(
        observed_coordinates, dict
    ):
        return False
    comparable = [
        key
        for key in ("chr", "pos", "ref", "alt")
        if expected_coordinates.get(key) not in (None, "")
        and observed_coordinates.get(key) not in (None, "")
    ]
    return bool(
        comparable
        and any(
            _norm(expected_coordinates.get(key))
            != _norm(observed_coordinates.get(key))
            for key in comparable
        )
    )


def identity_matches(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    """Require one positive allele match; annotation labels are not identity.

    Gene and transcript agreement is evaluated by the consequence resolver.  A
    provider may annotate the same genomic allele against another transcript or
    expose a locus label instead of an HGNC symbol; neither is an allele
    conflict.
    """
    if (
        not observed
        or not has_variant_identity(expected)
        or not has_variant_identity(observed)
    ):
        return False

    expected_coordinates = expected.get("coordinates")
    observed_coordinates = observed.get("coordinates")
    if expected_coordinates and observed_coordinates:
        if expected_coordinates == observed_coordinates:
            coordinate_match = True
        else:
            return False
    else:
        coordinate_match = False

    expected_rsid = _norm(expected.get("rsid"))
    observed_rsid = _norm(observed.get("rsid"))
    if expected_rsid and observed_rsid:
        if expected_rsid != observed_rsid:
            return False
        return True

    expected_hgvs = {
        _norm(expected.get(key))
        for key in ("hgvs_c", "validated_hgvs_c", "hgvs_g")
        if expected.get(key)
    }
    observed_hgvs = {
        _norm(observed.get(key))
        for key in ("hgvs_c", "validated_hgvs_c", "hgvs_g")
        if observed.get(key)
    }
    if expected_hgvs and observed_hgvs:
        if not expected_hgvs & observed_hgvs:
            return False
        return True
    return coordinate_match


def build_matches(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    expected_build = expected.get("build") or expected.get("assembly")
    observed_build = (
        observed.get("build")
        or observed.get("assembly")
        or observed.get("genome_build")
    )
    if not expected_build or not observed_build:
        return False
    return _build(expected_build) == _build(observed_build)


def _gnomad_dataset_build(features: dict[str, Any]) -> str:
    dataset = str(features.get("dataset") or "")
    return _GNOMAD_DATASET_BUILDS.get(dataset, "")


def _callability_identity(
    features: dict[str, Any], expected_identity: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Verify a locus-only coverage fact against a normalized allele identity."""
    expected_coordinates = expected_identity.get("coordinates")
    if not isinstance(expected_coordinates, dict):
        return {}, False
    try:
        observed_locus = {
            "chr": str(features.get("chrom") or features.get("chr") or "").removeprefix(
                "chr"
            ),
            "pos": int(features.get("position") or features.get("pos")),
        }
    except (TypeError, ValueError):
        return {}, False
    expected_build = expected_identity.get("build") or expected_identity.get("assembly")
    observed_build = features.get("reference_genome") or _gnomad_dataset_build(features)
    observed_identity = {"locus": observed_locus, "build": observed_build}
    matches = (
        observed_locus["chr"]
        == str(expected_coordinates.get("chr") or "").removeprefix("chr")
        and observed_locus["pos"] == expected_coordinates.get("pos")
        and bool(expected_build)
        and bool(observed_build)
        and _build(expected_build) == _build(observed_build)
    )
    return observed_identity, matches


def _callability_rows_ready(callsets: Any, position: int) -> bool:
    if not isinstance(callsets, dict):
        return False
    coverage_fields = (
        "mean",
        "median",
        "over_1",
        "over_5",
        "over_10",
        "over_15",
        "over_20",
        "over_25",
        "over_30",
        "over_50",
        "over_100",
    )
    for callset_name in ("exome", "genome"):
        row = callsets.get(callset_name)
        if not isinstance(row, dict):
            continue
        try:
            row_position = int(row.get("position") or row.get("pos"))
        except (TypeError, ValueError):
            continue
        if row_position == position and any(
            _number(row, key) is not None for key in coverage_fields
        ):
            return True
    return False


def source_fact_ready(
    tool_name: str,
    features: dict[str, Any],
    expected_identity: dict[str, Any],
) -> tuple[dict[str, Any], bool, bool]:
    """Return (provider identity, identity verified, assessment ready)."""
    if tool_name == "ClinGen_search_cspec":
        observed_identity = {"gene": features.get("gene")}
        expected_gene = str(expected_identity.get("gene") or "").strip().upper()
        observed_gene = str(features.get("gene") or "").strip().upper()
        identity_verified = bool(expected_gene and observed_gene == expected_gene)
        candidates = features.get("data")
        ready = (
            identity_verified
            and isinstance(candidates, list)
            and bool(features.get("provider"))
            and bool(features.get("request_url"))
        )
        return observed_identity, identity_verified, ready

    if tool_name == "EBIProteins_get_variation_by_hgvs":
        expected_hgvs = _norm(expected_identity.get("hgvs_g"))
        observed_hgvs = _norm(features.get("hgvs_g"))
        expected_gene = _norm(expected_identity.get("gene"))
        candidate_genes = {
            _norm(row.get("gene"))
            for row in features.get("protein_candidates") or []
            if isinstance(row, dict) and row.get("gene")
        }
        identity_verified = bool(
            expected_hgvs
            and observed_hgvs == expected_hgvs
            and (
                not expected_gene
                or not candidate_genes
                or expected_gene in candidate_genes
            )
        )
        observed_identity = {"hgvs_g": features.get("hgvs_g")}
        ready = identity_verified and bool(features.get("protein_candidates"))
        return observed_identity, identity_verified, ready

    if tool_name == "EBIProteins_get_variation":
        expected_accession = _norm(expected_identity.get("protein_accession"))
        observed_accession = _norm(features.get("protein_accession"))
        identity_verified = bool(
            expected_accession and observed_accession == expected_accession
        )
        candidates = features.get("same_residue_candidates")
        ready = identity_verified and isinstance(candidates, list)
        return (
            {"protein_accession": features.get("protein_accession")},
            identity_verified,
            ready,
        )

    if tool_name in {
        "EBIProteins_get_features",
        "InterPro_get_entries_for_protein",
    }:
        expected_accession = _norm(expected_identity.get("protein_accession"))
        observed_accession = _norm(features.get("protein_accession"))
        identity_verified = bool(
            expected_accession and observed_accession == expected_accession
        )
        collection_key = (
            "features"
            if tool_name == "EBIProteins_get_features"
            else "interpro_entries"
        )
        ready = identity_verified and isinstance(features.get(collection_key), list)
        return (
            {"protein_accession": features.get("protein_accession")},
            identity_verified,
            ready,
        )

    if tool_name == "gnomad_get_site_callability":
        observed_identity, identity_verified = _callability_identity(
            features, expected_identity
        )
        callsets = features.get("callsets")
        coverage_adequate = features.get("coverage_adequate")
        expected_coordinates = expected_identity.get("coordinates")
        expected_position = (
            expected_coordinates.get("pos")
            if isinstance(expected_coordinates, dict)
            else 0
        )
        ready = (
            identity_verified
            and bool(_gnomad_dataset_build(features))
            and _callability_rows_ready(
                callsets,
                int(expected_position or 0),
            )
            and (coverage_adequate is None or type(coverage_adequate) is bool)
            and bool(provider_version(features))
        )
        return observed_identity, identity_verified, ready

    if tool_name in {"ClinGen_search_gene_validity", "ClinGen_get_gene_validity"}:
        expected_gene = str(expected_identity.get("gene") or "").strip().upper()
        observed_gene = str(features.get("gene") or "").strip().upper()
        identity_verified = bool(expected_gene and observed_gene == expected_gene)
        curations = features.get("validity_curations")
        ready = (
            identity_verified
            and isinstance(curations, list)
            and bool(provider_version(features))
        )
        return {"gene": features.get("gene")}, identity_verified, ready

    if tool_name == "gnomad_get_constraint":
        expected_gene = str(expected_identity.get("gene") or "").strip().upper()
        observed_gene = str(features.get("gene") or "").strip().upper()
        identity_verified = bool(expected_gene and observed_gene == expected_gene)
        ready = (
            identity_verified
            and (
                _number(features, "pli") is not None
                or _number(features, "loeuf") is not None
            )
            and bool(features.get("dataset") or features.get("reference_genome"))
            and bool(provider_version(features))
        )
        return {"gene": features.get("gene")}, identity_verified, ready

    if tool_name in {
        "ClinGen_get_dosage_sensitivity",
        "ClinGen_get_actionability_adult",
        "ClinGen_get_actionability_pediatric",
        "ClinGen_get_variant_classifications",
    }:
        expected_gene = str(expected_identity.get("gene") or "").strip().upper()
        observed_gene = str(features.get("gene") or "").strip().upper()
        identity_verified = bool(expected_gene and observed_gene == expected_gene)
        ready = identity_verified and bool(provider_version(features))
        return {"gene": features.get("gene")}, identity_verified, ready

    if tool_name == "UniProt_get_entry_by_accession":
        expected_accession = _norm(expected_identity.get("protein_accession"))
        observed_accession = _norm(features.get("protein_accession"))
        identity_verified = bool(
            expected_accession and observed_accession == expected_accession
        )
        ready = identity_verified and bool(provider_version(features))
        return (
            {"protein_accession": features.get("protein_accession")},
            identity_verified,
            ready,
        )

    if tool_name.startswith("HPO_"):
        expected_term = _norm(expected_identity.get("hpo_term"))
        observed_term = _norm(features.get("hpo_term"))
        if tool_name == "HPO_search_terms":
            identity_verified = bool(features.get("query"))
        else:
            identity_verified = bool(expected_term and observed_term == expected_term)
        return (
            {"hpo_term": features.get("hpo_term")},
            identity_verified,
            identity_verified and bool(provider_version(features)),
        )

    if tool_name == "ensembl_lookup_gene":
        expected_transcript = str(
            expected_identity.get("ensembl_transcript_id") or ""
        ).strip()
        observed_transcript = str(features.get("transcript_id") or "").strip()
        identity_verified = bool(
            expected_transcript and observed_transcript == expected_transcript
        )
        exons = features.get("exons")
        ready = (
            identity_verified
            and isinstance(exons, list)
            and bool(exons)
            and all(
                isinstance(row, dict)
                and _number(row, "start") is not None
                and _number(row, "end") is not None
                and _number(row, "rank") is not None
                for row in exons
            )
            and bool(provider_version(features))
        )
        return {"transcript": observed_transcript}, identity_verified, ready

    if tool_name == "gnomad_get_region_variants":
        expected_coordinates = expected_identity.get("coordinates")
        expected_chrom = (
            str(expected_coordinates.get("chr") or "").removeprefix("chr")
            if isinstance(expected_coordinates, dict)
            else ""
        )
        observed_chrom = str(features.get("chrom") or "").removeprefix("chr")
        identity_verified = bool(expected_chrom and observed_chrom == expected_chrom)
        ready = (
            identity_verified
            and isinstance(features.get("variants"), list)
            and _number(features, "start") is not None
            and _number(features, "stop") is not None
            and bool(provider_version(features))
        )
        return (
            {"chrom": features.get("chrom")},
            identity_verified,
            ready,
        )

    if tool_name in {"gnomad_get_variant", "gnomad_get_variant_populations"}:
        dataset_build = _gnomad_dataset_build(features)
        if dataset_build and not features.get("build"):
            # The GraphQL variant payload does not repeat the assembly. The
            # requested, versioned gnomAD dataset provides the build binding.
            features["build"] = dataset_build

    observed_identity = result_identity(features)
    identity_verified = identity_matches(expected_identity, observed_identity)
    observed_build = (
        observed_identity.get("build")
        or observed_identity.get("assembly")
        or observed_identity.get("genome_build")
    )
    # Normalization providers may omit the assembly after the collector has
    # already bound the request to its normalized build. A reported mismatch
    # still fails closed; only this narrow identity-only omission is tolerated.
    if observed_build or tool_name not in {
        "VariantValidator_validate_variant",
        "VariantValidator_format_genomic_to_transcripts",
        "EnsemblVEP_variant_recoder",
        "MyVariant_get_pathogenicity_scores",
        "Mutalyzer_normalize_variant",
    }:
        identity_verified = identity_verified and build_matches(
            expected_identity, observed_identity
        )
    if not identity_verified:
        return observed_identity, False, False

    if tool_name in {"gnomad_get_variant", "gnomad_get_variant_populations"}:
        coverage_adequate = features.get("coverage_adequate")
        ready = (
            bool(observed_build)
            and str(features.get("callset") or "") in {"exome", "genome"}
            and _number(features, "AN", "an") is not None
            and _number(features, "AC", "ac") is not None
            and _number(features, "AF", "af", "af_global") is not None
            and (coverage_adequate is None or type(coverage_adequate) is bool)
            and any(
                features.get(key) not in (None, "")
                for key in ("dataset", "population_version", "release")
            )
            and bool(provider_version(features))
        )
    elif tool_name == "MyVariant_get_pathogenicity_scores":
        ready = (
            bool(observed_build)
            and bool(
                expected_identity.get("build") or expected_identity.get("assembly")
            )
            and build_matches(expected_identity, observed_identity)
            and _number(features, "revel_score", "revel") is not None
            and any(
                features.get(key) not in (None, "")
                for key in (
                    "predictor_version",
                    "provider_version",
                    "version",
                    "release",
                )
            )
        )
    elif tool_name == "SpliceAI_predict_splice":
        scores = features.get("scores")
        metadata = features.get("spliceai_run_metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        spliceai_profile = features.get("spliceai_profile")
        spliceai_profile = (
            spliceai_profile if isinstance(spliceai_profile, dict) else {}
        )
        max_delta = _number(spliceai_profile, "max_delta_score")
        ready = (
            bool(observed_build)
            and build_matches(expected_identity, observed_identity)
            and isinstance(scores, list)
            and spliceai_profile.get("status") == "resolved"
            and walker_run_metadata_ready(
                metadata,
                max_delta,
                require_unique_row=True,
            )
            and bool(provider_version(features))
        )
    elif tool_name in {
        "EnsemblVEP_annotate_hgvs",
        "EnsemblVEP_annotate_rsid",
        "ensembl_vep_region",
        "VariantValidator_validate_variant",
        "VariantValidator_format_genomic_to_transcripts",
        "FAVOR_annotate_variant",
        "OpenTargets_get_variant_transcript_consequences",
        "Mutalyzer_normalize_variant",
        "GenomeNexus_annotate_variant",
        "GenomeNexus_annotate_dbsnp",
        "ProtVar_map_variant",
    }:
        candidates = features.get("consequence_candidates")
        if not isinstance(candidates, list):
            candidates = features.get("vep_transcript_candidates")
        ready = (
            bool(provider_version(features))
            and isinstance(candidates, list)
            and bool(candidates)
            and any(
                isinstance(row, dict)
                and bool(row.get("consequence") or row.get("consequence_terms"))
                for row in candidates
            )
        )
    elif tool_name == "EnsemblVEP_variant_recoder":
        ready = bool(provider_version(features))
    else:
        ready = False
    return observed_identity, identity_verified, ready


def _number(values: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = values.get(key)
        if value in (None, ""):
            continue
        # Providers serialize scores as numeric strings (e.g. SpliceAI DS_*).
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            return number
    return None


_CONCLUSION_KEYS = {
    "acmg_classification",
    "classification",
    "clinical_significance",
    "clinicalsignificance",
    "interpretation",
    "pathogenicity",
    "label",
    "verdict",
    "result",
    "suggestion",
    "recommendation",
    "assertion",
    "acmg_criteria",
    "criteria",
    "applied_criteria",
    "pathogenic",
    "benign",
}
_IDENTITY_KEYS = {
    "variant_id",
    "_id",
    "chrom",
    "chr",
    "chromosome",
    "pos",
    "position",
    "ref",
    "reference",
    "alt",
    "alternate",
    "rsid",
    "hgvs_c",
    "validated_hgvs_c",
    "hgvs_g",
    "hgvs_p",
    "gene",
    "transcript",
    "build",
    "assembly",
    "genome_build",
    "variation_id",
    "clinvar_variation_id",
}


def _source_category(tool_name: str) -> str:
    name = tool_name.lower()
    if "genebe" in name or "intervar" in name:
        return "automated_classifier"
    if "clinvar" in name:
        return "source_assertion"
    if "spliceai" in name:
        return "splicing_prediction"
    if any(
        token in name
        for token in (
            "cadd",
            "alphamissense",
            "myvariant",
            "opencravat",
            "vep",
            "favor",
            "genomenexus",
            "mutalyzer",
            "protvar",
            "gprofiler",
        )
    ) or tool_name.startswith("OpenTargets_get_variant"):
        return "computational_prediction"
    if "gnomad" in name or "population" in name:
        return "population"
    if any(token in name for token in ("literature", "pubmed", "pmc")):
        return "literature"
    if "clingen" in name or "g2p" in name:
        return "disease_context"
    if "ebiproteins" in name or "interpro" in name or "uniprot" in name:
        return "protein_context"
    return "source_lead"


def _provider_payload(raw: dict[str, Any]) -> Any:
    raw_output = raw.get("raw_output")
    if isinstance(raw_output, (dict, list)):
        return raw_output
    data = raw.get("data")
    if isinstance(data, dict):
        variant = data.get("variant")
        return variant if isinstance(variant, dict) else data
    return data if isinstance(data, list) else raw


def _copy(raw: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    return {key: raw[key] for key in keys if key in raw}


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def _quarantine(value: Any, path: str, assertions: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            lowered = str(key).casefold()
            if (
                lowered in _CONCLUSION_KEYS
                or lowered.endswith("_classification")
                or lowered.endswith("_significance")
            ):
                assertions[child_path] = child
            else:
                clean[key] = _quarantine(child, child_path, assertions)
        return clean
    if isinstance(value, list):
        return [
            _quarantine(child, f"{path}[{index}]", assertions)
            for index, child in enumerate(value)
        ]
    return value


def _identity_fields(raw: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {**_copy(payload, _IDENTITY_KEYS), **_copy(raw, _IDENTITY_KEYS)}


def _variantvalidator_fields(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data")
    if not isinstance(data, dict):
        return _variantformatter_fields(raw)
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    record = next(
        (
            value
            for key, value in data.items()
            if key not in {"flag", "metadata"}
            and isinstance(value, dict)
            and any(
                field in value
                for field in (
                    "hgvs_transcript_variant",
                    "gene_symbol",
                    "primary_assembly_loci",
                )
            )
        ),
        None,
    )
    if not isinstance(record, dict):
        return _variantformatter_fields(raw)
    hgvs_c = str(record.get("hgvs_transcript_variant") or "")
    protein = record.get("hgvs_predicted_protein_consequence")
    protein = protein if isinstance(protein, dict) else {}
    features: dict[str, Any] = {
        "validated_hgvs_c": hgvs_c,
        "hgvs_c": hgvs_c,
        "gene": record.get("gene_symbol"),
        "hgvs_p": protein.get("tlr") or protein.get("slr"),
        "provider_version": metadata.get("variantvalidator_version")
        or metadata.get("vvdb_version"),
    }
    if ":" in hgvs_c:
        features["transcript"] = hgvs_c.split(":", 1)[0]
    if hgvs_c:
        features["consequence_candidates"] = [
            {
                "gene": record.get("gene_symbol"),
                "transcript": features.get("transcript"),
                "hgvsc": hgvs_c,
                "hgvsp": features.get("hgvs_p"),
                "consequence": _terms_from_hgvs(
                    hgvs_c,
                    str(features.get("hgvs_p") or ""),
                ),
            }
        ]
    loci = record.get("primary_assembly_loci")
    loci = loci if isinstance(loci, dict) else {}
    for build, suffix in (("grch38", ""), ("grch37", "_grch37")):
        locus = loci.get(build) or loci.get(build.upper())
        locus = locus if isinstance(locus, dict) else {}
        hgvs_g = locus.get("hgvs_genomic_description") or locus.get("hgvs_genomic")
        if hgvs_g:
            features[f"hgvs_g{suffix}"] = hgvs_g
        vcf = locus.get("vcf")
        coordinates: dict[str, Any] = {}
        if isinstance(vcf, dict):
            coordinates = {
                "chr": vcf.get("chr") or vcf.get("chrom"),
                "pos": vcf.get("pos") or vcf.get("position"),
                "ref": vcf.get("ref") or vcf.get("reference"),
                "alt": vcf.get("alt") or vcf.get("alternate"),
            }
        elif isinstance(vcf, str):
            parts = vcf.removeprefix("chr").split("-")
            if len(parts) == 4:
                coordinates = dict(zip(("chr", "pos", "ref", "alt"), parts))
        if suffix and coordinates:
            features["coordinates_grch37"] = coordinates
        elif coordinates:
            features.update(coordinates)
    return _drop_empty(features)


def _terms_from_hgvs(hgvs_c: str, hgvs_p: str) -> list[str]:
    """Conservatively derive Sequence Ontology terms from provider HGVS."""
    protein = str(hgvs_p or "").casefold()
    coding = str(hgvs_c or "").casefold()
    if "fs" in protein:
        return ["frameshift_variant"]
    if any(token in protein for token in ("ter", "*")):
        return ["stop_gained"]
    if protein.endswith(("=", "(=)")):
        return ["synonymous_variant"]
    if re.search(r"p\.\(?[a-z]{1,3}\d+[a-z]{1,3}\)?$", protein):
        return ["missense_variant"]
    if re.search(r"c\.\d+[+-][12](?:_|[a-z])", coding):
        return ["splice_donor_variant" if "+" in coding else "splice_acceptor_variant"]
    return []


def _variantformatter_fields(raw: dict[str, Any]) -> dict[str, Any]:
    nested_data = raw.get("data")
    data = nested_data if isinstance(nested_data, dict) else raw
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    pending: list[Any] = [data]
    candidates: list[dict[str, Any]] = []
    formatter_projections: dict[str, dict[str, Any]] = {}
    genomic_hgvs = ""
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if value.get("g_hgvs") and not genomic_hgvs:
                genomic_hgvs = str(value["g_hgvs"])
            projections = value.get("hgvs_t_and_p")
            if isinstance(projections, dict):
                for reference, projection in projections.items():
                    if not isinstance(projection, dict):
                        continue
                    select_status = projection.get("select_status")
                    select_status = (
                        select_status if isinstance(select_status, dict) else {}
                    )
                    gene_info = projection.get("gene_info")
                    gene_info = gene_info if isinstance(gene_info, dict) else {}
                    hgvs_c = str(projection.get("t_hgvs") or "")
                    hgvs_p = str(
                        projection.get("p_hgvs")
                        or projection.get("p_hgvs_tlc")
                        or projection.get("p_hgvs_slc")
                        or ""
                    )
                    candidates.append(
                        {
                            "gene": gene_info.get("symbol"),
                            "transcript": str(reference),
                            "mane_select": (
                                str(reference)
                                if select_status.get("mane_select") is True
                                else ""
                            ),
                            "hgvsc": hgvs_c,
                            "hgvsp": hgvs_p,
                            "consequence": _terms_from_hgvs(hgvs_c, hgvs_p),
                        }
                    )
                    formatter_projections[str(reference)] = {
                        "t_hgvs": hgvs_c,
                        "p_hgvs": hgvs_p,
                        "gene_info": {"symbol": gene_info.get("symbol")},
                        "select_status": {
                            "mane_select": select_status.get("mane_select") is True,
                            "mane_plus_clinical": (
                                select_status.get("mane_plus_clinical") is True
                            ),
                        },
                    }
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    genes = {str(row.get("gene") or "") for row in candidates if row.get("gene")}
    features: dict[str, Any] = {
        "hgvs_g": genomic_hgvs,
        "g_hgvs": genomic_hgvs,
        "hgvs_t_and_p": formatter_projections,
        "consequence_candidates": candidates,
        "provider_version": metadata.get("variantformatter_version")
        or metadata.get("variantvalidator_version")
        or metadata.get("vvdb_version"),
    }
    if len(genes) == 1:
        features["gene"] = next(iter(genes))
    return _drop_empty(features)


def _variant_id_coordinates(value: Any) -> dict[str, Any]:
    parts = re.split(r"[-_:]", str(value or "").removeprefix("chr"))
    if len(parts) != 4:
        return {}
    chrom, position, ref, alt = parts
    try:
        return {"chr": chrom, "pos": int(position), "ref": ref, "alt": alt}
    except (TypeError, ValueError):
        return {}


_FAVOR_COMPOSITE_LABEL_RE = re.compile(
    r"^\s*(?P<label>[^()]+?)\s*\((?P<transcript>ENST\d+(?:\.\d+)?)"
    r"(?::(?P<details>[^)]*))?\)\s*$",
    re.IGNORECASE,
)
_LOCUS_ACCESSION_RE = re.compile(r"^[A-Z]{1,4}\d{5,}(?:\.\d+)?$")


def _favor_consequence_identity(consequence: dict[str, Any]) -> dict[str, Any]:
    """Separate FAVOR's raw locus label from canonical gene/transcript IDs."""
    provider_gene_label = str(consequence.get("gene") or "").strip()
    provider_transcript_label = str(consequence.get("transcript") or "").strip()
    gene_symbol = provider_gene_label
    transcript = provider_transcript_label
    exon = consequence.get("exon")
    inferred_hgvs_c = ""

    match = _FAVOR_COMPOSITE_LABEL_RE.fullmatch(provider_gene_label)
    if match:
        locus_label = str(match.group("label") or "").strip()
        transcript = transcript or str(match.group("transcript") or "").strip()
        details = str(match.group("details") or "")
        detail_parts = [part.strip() for part in details.split(":") if part.strip()]
        exon = exon or next(
            (part for part in detail_parts if part.casefold().startswith("exon")),
            None,
        )
        coding = next(
            (part for part in detail_parts if part.casefold().startswith("c.")),
            "",
        )
        inferred_hgvs_c = f"{transcript}:{coding}" if transcript and coding else ""
        gene_symbol = "" if _LOCUS_ACCESSION_RE.fullmatch(locus_label) else locus_label
    elif _LOCUS_ACCESSION_RE.fullmatch(provider_gene_label):
        gene_symbol = ""

    return {
        "gene": gene_symbol,
        "transcript": transcript,
        "provider_gene_label": provider_gene_label,
        "provider_transcript_label": provider_transcript_label,
        "exon": exon,
        "inferred_hgvs_c": inferred_hgvs_c,
    }


def _favor_fields(payload: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    variant = payload.get("variant")
    variant = variant if isinstance(variant, dict) else {}
    consequence = payload.get("gene_consequence")
    consequence = consequence if isinstance(consequence, dict) else {}
    coordinates_value = _variant_id_coordinates(
        variant.get("variant_vcf") or raw.get("variant")
    )
    consequence_identity = _favor_consequence_identity(consequence)
    hgvs_c = str(
        consequence.get("hgvs_c") or consequence_identity.get("inferred_hgvs_c") or ""
    )
    hgvs_p = str(consequence.get("hgvs_p") or consequence.get("protein_variant") or "")
    so_term = consequence.get("so_term") or consequence.get("exonic_category")
    terms = (
        [str(so_term).casefold().replace(" ", "_")]
        if so_term not in (None, "")
        else _terms_from_hgvs(hgvs_c, hgvs_p)
    )
    candidate = {
        "gene": consequence_identity.get("gene"),
        "transcript": consequence_identity.get("transcript"),
        "provider_gene_label": consequence_identity.get("provider_gene_label"),
        "provider_transcript_label": consequence_identity.get(
            "provider_transcript_label"
        ),
        "mane_select": consequence.get("mane_select"),
        "hgvsc": hgvs_c,
        "hgvsp": hgvs_p,
        "consequence": terms,
        "canonical": consequence.get("is_canonical"),
        "exon": consequence_identity.get("exon"),
    }
    return {
        **coordinates_value,
        "build": "GRCh38",
        "rsid": variant.get("rsid"),
        "hgvs_g": variant.get("hgvs_genomic"),
        "gene": consequence_identity.get("gene"),
        "transcript": consequence_identity.get("transcript"),
        "provider_gene_label": consequence_identity.get("provider_gene_label"),
        "provider_transcript_label": consequence_identity.get(
            "provider_transcript_label"
        ),
        "hgvs_c": hgvs_c,
        "hgvs_p": hgvs_p,
        "most_severe_consequence": next(iter(terms), None),
        "consequence_candidates": [candidate] if any(candidate.values()) else [],
        "provider_version": (
            (raw.get("metadata") or {}).get("source")
            if isinstance(raw.get("metadata"), dict)
            else None
        )
        or "FAVOR GRCh38",
    }


def _open_targets_consequence_fields(payload: dict[str, Any]) -> dict[str, Any]:
    coords = _variant_id_coordinates(payload.get("id"))
    rows = payload.get("transcriptConsequences")
    rows = rows if isinstance(rows, list) else []
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        target = row.get("target")
        target = target if isinstance(target, dict) else {}
        consequence_rows = row.get("variantConsequences")
        consequence_rows = (
            consequence_rows if isinstance(consequence_rows, list) else []
        )
        terms = [
            str(item.get("label") or "").casefold().replace(" ", "_")
            for item in consequence_rows
            if isinstance(item, dict) and item.get("label")
        ]
        candidates.append(
            {
                "gene": target.get("approvedSymbol"),
                "transcript": row.get("transcriptId"),
                "hgvsp": row.get("aminoAcidChange"),
                "consequence": terms,
                "impact": row.get("impact"),
                "canonical": row.get("isEnsemblCanonical"),
            }
        )
    severe = payload.get("mostSevereConsequence")
    severe = severe if isinstance(severe, dict) else {}
    rsids = payload.get("rsIds")
    return {
        **coords,
        "build": "GRCh38",
        "rsid": (
            str(rsids[0]) if isinstance(rsids, list) and len(rsids) == 1 else None
        ),
        "hgvs_g": payload.get("hgvsId"),
        "most_severe_consequence": severe.get("label"),
        "consequence_candidates": candidates,
        "provider_version": "Open Targets Platform GraphQL",
    }


def _genome_nexus_fields(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    for row in payload.get("transcript_consequences") or []:
        if not isinstance(row, dict):
            continue
        candidates.append(
            {
                "gene": row.get("gene_symbol"),
                "transcript": row.get("transcript_id"),
                "hgvsc": row.get("hgvsc"),
                "hgvsp": row.get("hgvsp"),
                "consequence": row.get("consequence_terms") or [],
                "canonical": row.get("canonical"),
                "exon": row.get("exon"),
            }
        )
    return {
        "hgvs_g": payload.get("hgvsg") or payload.get("variant"),
        "build": payload.get("assembly_name") or "GRCh37",
        "most_severe_consequence": payload.get("most_severe_consequence"),
        "consequence_candidates": candidates,
        "provider_version": "Genome Nexus annotation API",
    }


def _mutalyzer_fields(payload: dict[str, Any]) -> dict[str, Any]:
    hgvs_c = str(
        payload.get("normalized_description")
        or payload.get("corrected_description")
        or payload.get("input_description")
        or ""
    )
    protein = payload.get("protein")
    protein = protein if isinstance(protein, dict) else {}
    hgvs_p = str(protein.get("description") or "")
    transcript = hgvs_c.split(":", 1)[0] if ":" in hgvs_c else ""
    return {
        "hgvs_c": hgvs_c,
        "transcript": transcript,
        "hgvs_p": hgvs_p,
        "consequence_candidates": [
            {
                "transcript": transcript,
                "hgvsc": hgvs_c,
                "hgvsp": hgvs_p,
                "consequence": _terms_from_hgvs(hgvs_c, hgvs_p),
            }
        ],
        "provider_version": "Mutalyzer API v3",
    }


def _protvar_fields(payload: dict[str, Any]) -> dict[str, Any]:
    genomic = payload.get("genomic_coordinates")
    genomic = genomic if isinstance(genomic, dict) else {}
    candidates = []
    for row in payload.get("isoform_mappings") or []:
        if not isinstance(row, dict):
            continue
        consequence = row.get("consequence") or []
        candidates.append(
            {
                "gene": row.get("gene"),
                "transcript": row.get("transcript"),
                "hgvsp": row.get("protein_variant"),
                "consequence": (
                    consequence if isinstance(consequence, list) else [consequence]
                ),
                "canonical": row.get("canonical"),
                "protein_position": row.get("position"),
            }
        )
    return {
        **genomic,
        "build": payload.get("assembly") or "GRCh38",
        "consequence_candidates": candidates,
        "provider_version": "EBI ProtVar API",
    }


def _gprofiler_snp_fields(payload: Any) -> dict[str, Any]:
    rows = (
        payload
        if isinstance(payload, list)
        else payload.get("data", [])
        if isinstance(payload, dict)
        else []
    )
    candidates = []
    identity: dict[str, Any] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not identity:
            identity = {
                "rsid": row.get("rs_id"),
                "chr": row.get("chromosome"),
                "pos": row.get("start"),
            }
        for consequence in row.get("variant_consequences") or []:
            if not isinstance(consequence, dict):
                continue
            candidates.append(
                {
                    "gene": next(iter(row.get("gene_names") or []), None),
                    "consequence": [consequence.get("consequence")],
                }
            )
    return {
        **identity,
        "consequence_candidates": candidates,
        "provider_version": "g:Profiler g:SNPense",
    }


def _preferred_refseq_hgvs(candidates: Any) -> Any:
    """Return one unambiguous RefSeq HGVS instead of silently taking the first."""
    values = list(dict.fromkeys(str(value) for value in candidates or [] if value))
    refseq = [
        value for value in values if value.split(":", 1)[0].startswith(("NM_", "NP_"))
    ]
    if len(refseq) == 1:
        return refseq[0]
    return values[0] if len(values) == 1 else None


_REV_COMP = str.maketrans("ACGTUacgtu", "TGCAAtgcaa")


def _reverse_complement(value: str) -> str:
    """Reverse-complement an allele string for minus-strand normalization."""
    return value.translate(_REV_COMP)[::-1]


def _vep_forward_alleles(payload: dict[str, Any]) -> tuple[Any, Any]:
    """Return (ref, alt) on the forward strand from a VEP entry.

    For transcript-oriented HGVS inputs (``c.``/``n.``/``p.``) VEP reports
    ``allele_string`` in transcript orientation, which inverts ref/alt for
    minus-strand genes. Genomic HGVS and rsID inputs are already forward.
    Indel allele strings (``-/X``) use insertion-point rather than padded-VCF
    coordinates, so they must not be treated as comparable coordinates.
    """
    allele = re.split(r"[/|>]", str(payload.get("allele_string") or ""))
    if len(allele) != 2 or "-" in allele:
        return None, None
    ref, alt = allele
    input_text = str(payload.get("input") or "")
    transcript_oriented = any(token in input_text for token in (":c.", ":n.", ":p."))
    if transcript_oriented and str(payload.get("strand") or "") == "-1":
        return _reverse_complement(ref), _reverse_complement(alt)
    return ref, alt


def ncbi_refsnp_alleles(features: dict[str, Any]) -> dict[str, Any]:
    """Parse an NCBIVariation_rsid_lookup sandbox into allele structures.

    Returns per-allele genomic HGVS (SNV-only), gene symbols, MANE Select
    accessions, and a flag for placements this parser cannot represent
    (indels or non-chromosomal accessions), so the caller can fall back to
    the Ensembl recoder instead of guessing HGVS notation.
    """
    record = features.get("data")
    record = record if isinstance(record, dict) else {}
    alleles: list[dict[str, Any]] = []
    unsupported = False
    seen: set[str] = set()
    for row in record.get("grch38_placements") or []:
        if not isinstance(row, dict):
            continue
        seq_id = str(row.get("seq_id") or "")
        deleted = str(row.get("deleted_sequence") or "")
        inserted = str(row.get("inserted_sequence") or "")
        if not seq_id.startswith("NC_"):
            continue
        if deleted == inserted:
            continue  # reference placement, not an alternate allele
        if len(deleted) != 1 or len(inserted) != 1:
            unsupported = True
            continue
        try:
            # dbSNP refsnp placements are 0-based; HGVS positions are 1-based.
            position = int(row.get("position")) + 1
        except (TypeError, ValueError):
            unsupported = True
            continue
        hgvs_g = f"{seq_id}:g.{position}{deleted}>{inserted}"
        if hgvs_g in seen:
            continue
        seen.add(hgvs_g)
        alleles.append({"hgvs_g": hgvs_g})
    genes = list(
        dict.fromkeys(
            str(entry.get("gene") or "")
            for entry in record.get("genes") or []
            if isinstance(entry, dict) and entry.get("gene")
        )
    )
    mane = [
        str(value)
        for value in record.get("mane_select_ids") or []
        if str(value or "").strip()
    ]
    rsid = record.get("refsnp_id")
    return {
        "rsid": f"rs{rsid}" if rsid not in (None, "") else "",
        "alleles": alleles,
        "unsupported_alleles": unsupported,
        "genes": genes,
        "mane_select_ids": mane,
        "provider_version": "NCBI Variation refsnp",
    }


def _vep_fields(raw: dict[str, Any], payload: Any, tool_name: str) -> dict[str, Any]:
    if "variant_recoder" in tool_name and isinstance(payload, list) and payload:
        allele_candidates: list[dict[str, Any]] = []
        for allele in payload:
            if not isinstance(allele, dict):
                continue
            allele_candidates.append(
                {
                    "ids": list(
                        dict.fromkeys(
                            str(value) for value in allele.get("id", []) if value
                        )
                    ),
                    "hgvsg": list(
                        dict.fromkeys(
                            str(value) for value in allele.get("hgvsg", []) if value
                        )
                    ),
                    "hgvsc": list(
                        dict.fromkeys(
                            str(value) for value in allele.get("hgvsc", []) if value
                        )
                    ),
                    "hgvsp": list(
                        dict.fromkeys(
                            str(value) for value in allele.get("hgvsp", []) if value
                        )
                    ),
                }
            )
        rsids = list(
            dict.fromkeys(
                value
                for allele in allele_candidates
                for value in allele["ids"]
                if value.lower().startswith("rs")
            )
        )
        hgvsg_candidates = list(
            dict.fromkeys(
                value for allele in allele_candidates for value in allele["hgvsg"]
            )
        )
        hgvsc_candidates = list(
            dict.fromkeys(
                value for allele in allele_candidates for value in allele["hgvsc"]
            )
        )
        hgvsp_candidates = list(
            dict.fromkeys(
                value for allele in allele_candidates for value in allele["hgvsp"]
            )
        )
        return {
            key: value
            for key, value in {
                "rsid": rsids[0] if len(rsids) == 1 else None,
                "hgvs_g": hgvsg_candidates[0] if len(hgvsg_candidates) == 1 else None,
                "hgvs_c": _preferred_refseq_hgvs(hgvsc_candidates),
                "hgvsc_candidates": hgvsc_candidates or None,
                "hgvsg_candidates": hgvsg_candidates or None,
                "hgvs_p": _preferred_refseq_hgvs(hgvsp_candidates),
                "hgvsp_candidates": hgvsp_candidates or None,
                "allele_candidates": allele_candidates or None,
                "provider_version": "Ensembl Variant Recoder REST",
            }.items()
            if value not in (None, "")
        }
    if not isinstance(payload, dict):
        return {}
    features = _identity_fields(raw, payload)
    consequences = payload.get("transcript_consequences")
    consequences = consequences if isinstance(consequences, list) else []
    candidates = [
        {
            "gene": str(row.get("gene_symbol") or ""),
            "transcript": str(row.get("transcript_id") or ""),
            "consequence": tuple(row.get("consequence_terms") or []),
            "hgvsc": str(row.get("hgvsc") or ""),
            "hgvsp": str(row.get("hgvsp") or ""),
            "exon": row.get("exon"),
            "intron": row.get("intron"),
            "biotype": row.get("biotype"),
            "distance": row.get("distance"),
            "canonical": row.get("canonical"),
            "mane_select": row.get("mane_select"),
            "mane_plus_clinical": row.get("mane_plus_clinical"),
            "amino_acids": row.get("amino_acids"),
            "protein_start": row.get("protein_start"),
            "protein_end": row.get("protein_end"),
            "protein_id": row.get("protein_id"),
            "swissprot": list(row.get("swissprot") or []),
            "uniprot_isoform": list(row.get("uniprot_isoform") or []),
        }
        for row in consequences
        if isinstance(row, dict)
        and (row.get("gene_symbol") or row.get("transcript_id"))
    ]
    if candidates:
        features["vep_transcript_candidates"] = candidates
    genes = {row["gene"] for row in candidates if row["gene"]}
    transcripts = {row["transcript"] for row in candidates if row["transcript"]}
    if len(genes) == 1:
        features["gene"] = next(iter(genes))
    if len(transcripts) == 1:
        features["transcript"] = next(iter(transcripts))
    forward_ref, forward_alt = _vep_forward_alleles(payload)
    features.update(
        {
            key: value
            for key, value in {
                "chr": payload.get("seq_region_name"),
                "pos": payload.get("start"),
                "ref": forward_ref,
                "alt": forward_alt,
                "build": payload.get("assembly_name"),
                "provider_version": "Ensembl VEP REST",
                "most_severe_consequence": payload.get("most_severe_consequence"),
            }.items()
            if value not in (None, "")
        }
    )
    input_text = str(payload.get("input") or "")
    if ":g." in input_text:
        # Genomic HGVS inputs echo back the resolved genomic notation, which
        # lets identity checks link VEP to other providers by HGVS even when
        # the allele representation (e.g. indels) is not VCF-comparable.
        features.setdefault("hgvs_g", input_text)
    return features


def _ebi_protein_variation_fields(
    raw: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        for feature in entry.get("features") or []:
            if not isinstance(feature, dict):
                continue
            candidates.append(
                {
                    "protein_accession": entry.get("accession"),
                    "entry_name": entry.get("entry_name"),
                    "gene": entry.get("gene_name"),
                    "taxid": entry.get("taxid"),
                    "feature_type": feature.get("type"),
                    "protein_position_start": feature.get("begin"),
                    "protein_position_end": feature.get("end"),
                    "wild_type": feature.get("wild_type"),
                    "alternative_sequence": feature.get("alternative_sequence"),
                    "consequence_type": feature.get("consequence_type"),
                    "genomic_location": feature.get("genomic_location"),
                }
            )
    hgvs = str(payload.get("hgvs") or "")
    return {
        "hgvs_g": hgvs,
        "protein_candidates": candidates,
        "provider_version": "EBI Proteins API",
        "request_url": f"https://www.ebi.ac.uk/proteins/api/variation/hgvs/{hgvs}",
    }


def _ebi_protein_feature_fields(payload: dict[str, Any]) -> dict[str, Any]:
    accession = str(payload.get("accession") or "")
    features = [
        {
            "type": row.get("type"),
            "category": row.get("category"),
            "position_start": row.get("position_start"),
            "position_end": row.get("position_end"),
            "description": row.get("description"),
            "evidences": row.get("evidences"),
        }
        for row in payload.get("features") or []
        if isinstance(row, dict)
    ]
    return {
        "protein_accession": accession,
        "entry_name": payload.get("entry_name"),
        "sequence_length": payload.get("sequence_length"),
        "feature_category": payload.get("category_queried"),
        "features": features,
        "provider_version": "EBI Proteins API",
        "request_url": f"https://www.ebi.ac.uk/proteins/api/features/{accession}",
    }


def _ebi_protein_known_variation_fields(payload: dict[str, Any]) -> dict[str, Any]:
    accession = str(payload.get("accession") or "")
    variants = []
    for row in payload.get("variants") or []:
        if not isinstance(row, dict):
            continue
        variants.append(
            {
                "position_start": row.get("position_start"),
                "position_end": row.get("position_end"),
                "wild_type": row.get("wild_type"),
                "alternative": row.get("alternative"),
                "source_type": row.get("source_type"),
                "associations": list(row.get("associations") or []),
                "xrefs": list(row.get("xrefs") or []),
                "clinical_significances": list(row.get("clinical_significances") or []),
            }
        )
    return {
        "protein_accession": accession,
        "entry_name": payload.get("entry_name"),
        "protein_variants": variants,
        "total_variants": payload.get("total_variants")
        or payload.get("total_all_sources")
        or len(variants),
        "provider_version": "EBI Proteins API",
        "request_url": f"https://www.ebi.ac.uk/proteins/api/variation/{accession}",
    }


def _interpro_protein_fields(payload: dict[str, Any]) -> dict[str, Any]:
    accession = str(payload.get("protein_accession") or "")
    entries = [
        dict(row) for row in payload.get("entries") or [] if isinstance(row, dict)
    ]
    return {
        "protein_accession": accession,
        "interpro_entries": entries,
        "provider_version": "InterPro API",
        "request_url": (
            "https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/uniprot/"
            f"{accession}"
        ),
    }


def _myvariant_fields(raw: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    dbnsfp = payload.get("dbnsfp") if isinstance(payload.get("dbnsfp"), dict) else {}
    revel = dbnsfp.get("revel") if isinstance(dbnsfp.get("revel"), dict) else {}
    cadd = dbnsfp.get("cadd") if isinstance(dbnsfp.get("cadd"), dict) else {}
    audit: dict[str, Any] = {}
    for name, values in dbnsfp.items():
        if not isinstance(values, dict):
            value = _first(values)
            if value is not None:
                audit[name] = value
            continue
        for field, label in (
            ("score", "score"),
            ("pred", "prediction"),
            ("phred", "phred"),
            ("rankscore", "rankscore"),
            ("raw", "raw"),
        ):
            value = _first(values.get(field))
            if value is not None:
                audit[f"{name}_{label}"] = value
    features = _identity_fields(raw, payload)
    features.update(
        {
            "revel_score": _first(revel.get("score")),
            "cadd_phred": _first(cadd.get("phred")),
            "predictor_audit": audit,
        }
    )
    predictions = {
        key.removesuffix("_prediction"): value
        for key, value in audit.items()
        if key.endswith("_prediction") and value not in (None, "")
    }
    normalized_predictions = {
        str(value).strip().casefold() for value in predictions.values() if value
    }
    features["predictor_concordance"] = {
        "predictions": predictions,
        "unique_prediction_values": sorted(normalized_predictions),
        "has_disagreement": len(normalized_predictions) > 1,
        "interpretation": (
            "Context only; predictor labels are not combined by majority vote."
        ),
    }
    variant_id = payload.get("_id") or raw.get("_id")
    if isinstance(variant_id, str) and variant_id:
        features.update(
            {"variant_id": variant_id, "_id": variant_id, "build": "GRCh37"}
        )
    version = next(
        (
            _first(source.get(key))
            for source in (raw, payload, dbnsfp)
            for key in (
                "predictor_version",
                "provider_version",
                "dbnsfp_version",
                "version",
                "release",
            )
            if isinstance(source, dict) and source.get(key) not in (None, "")
        ),
        None,
    )
    if isinstance(version, (str, int, float)) and not isinstance(version, bool):
        features["provider_version"] = version
    return features


def _population_fields(payload: dict[str, Any]) -> dict[str, Any]:
    callsets = {
        name: payload[name]
        for name in ("exome", "genome")
        if isinstance(payload.get(name), dict)
    }
    selected_name = next(
        (
            name
            for name in ("exome", "genome")
            if name in callsets
            and all(
                callsets[name].get(key) not in (None, "") for key in ("af", "ac", "an")
            )
        ),
        next(iter(callsets), ""),
    )
    selected = callsets.get(selected_name, {})
    features = _copy(
        payload,
        {
            "variant_id",
            "chrom",
            "pos",
            "ref",
            "alt",
            "rsid",
            "dataset",
            "build",
            "reference_genome",
        },
    )
    features.update(
        _copy(selected, {"af", "ac", "an", "populations", "homozygote_count"})
    )
    features.update(
        {
            "callset": selected_name or None,
            "callsets": callsets,
            "coverage_adequate": None,
        }
    )
    populations = selected.get("populations")
    valid = [
        row
        for row in populations or []
        if isinstance(row, dict) and isinstance(row.get("af"), (int, float))
    ]
    if valid:
        popmax = max(valid, key=lambda row: float(row["af"]))
        features.update(
            {"popmax": popmax.get("af"), "popmax_population": popmax.get("id")}
        )
    return features


def _spliceai_fields(payload: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "DS_AG",
        "DS_AL",
        "DS_DG",
        "DS_DL",
        "DP_AG",
        "DP_AL",
        "DP_DG",
        "DP_DL",
        "transcript",
        "transcript_id",
        "gene",
        "gene_symbol",
        "symbol",
        "genome_build",
        "genome",
        "coordinate",
        "ref",
        "alt",
        "score",
        "scores",
        "max_delta_score",
        "max_delta_transcript",
        "max_delta_event",
        "predicted_splice_event_type",
        "event_type",
        "variant",
        "run_metadata",
    }
    features = _copy(payload, keys)
    variant = payload.get("variant")
    if isinstance(variant, str):
        parts = variant.removeprefix("chr").split("-")
        if len(parts) == 4:
            features.update(dict(zip(("chr", "pos", "ref", "alt"), parts)))
    if payload.get("genome"):
        features["build"] = payload["genome"]
    global_max = features.pop("max_delta_score", None)
    global_transcript = features.pop("max_delta_transcript", None)
    global_event = features.pop("max_delta_event", None)
    scores = payload.get("scores")
    if isinstance(scores, list):
        rows = [row for row in scores if isinstance(row, dict)]
        derived_max: float | None = None
        derived_transcript = ""
        derived_event = ""
        event_names = {
            "DS_AG": "acceptor_gain",
            "DS_AL": "acceptor_loss",
            "DS_DG": "donor_gain",
            "DS_DL": "donor_loss",
        }
        for row in rows:
            for channel, event_name in event_names.items():
                try:
                    value = float(row.get(channel))
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(value) or (
                    derived_max is not None and value <= derived_max
                ):
                    continue
                derived_max = value
                derived_event = event_name
                refseq_ids = row.get("t_refseq_ids")
                first_refseq = (
                    next((str(item) for item in refseq_ids if item), "")
                    if isinstance(refseq_ids, list)
                    else str(refseq_ids or "")
                )
                derived_transcript = str(
                    row.get("transcript")
                    or row.get("transcript_id")
                    or row.get("t_id")
                    or first_refseq
                ).strip()
        parsed_global_max = _number({"value": global_max}, "value")
        if global_max is None and derived_max is not None:
            global_max = derived_max
            parsed_global_max = derived_max
        if (
            derived_max is not None
            and parsed_global_max is not None
            and math.isclose(derived_max, parsed_global_max)
        ):
            global_transcript = global_transcript or derived_transcript
            global_event = global_event or derived_event
        if len(rows) == 1:
            row_features = _copy(rows[0], keys)
            row_features.pop("max_delta_score", None)
            row_features.pop("max_delta_transcript", None)
            row_features.pop("max_delta_event", None)
            features.update(row_features)
    if global_max is not None:
        features["provider_global_max_delta_score"] = global_max
    if global_transcript is not None:
        features["provider_global_max_transcript"] = global_transcript
    if global_event is not None:
        features["provider_global_max_event"] = global_event
    return features


_SPLICEAI_ROW_GENE_KEYS = ("gene", "gene_symbol", "symbol", "g_name")


def spliceai_row_transcripts(row: dict[str, Any]) -> set[str]:
    """Return every transcript identifier a SpliceAI score row claims.

    The live SpliceAI Lookup schema uses ``t_id`` (Ensembl) and
    ``t_refseq_ids`` (RefSeq accessions); synthetic review inputs may use
    ``transcript``/``transcript_id``. All values are casefolded.
    """
    values = {
        str(row.get(key)).strip().casefold()
        for key in ("transcript", "transcript_id", "t_id")
        if row.get(key) not in (None, "")
    }
    refseq_ids = row.get("t_refseq_ids")
    if isinstance(refseq_ids, list):
        values.update(str(value).strip().casefold() for value in refseq_ids if value)
    elif refseq_ids not in (None, ""):
        values.add(str(refseq_ids).strip().casefold())
    return values


def spliceai_row_gene(row: dict[str, Any]) -> str:
    """Return the gene symbol of a SpliceAI score row across known schemas."""
    for key in _SPLICEAI_ROW_GENE_KEYS:
        if row.get(key) not in (None, ""):
            return str(row[key]).strip()
    return ""


def prepare_spliceai_features(
    features: dict[str, Any],
    expected_identity: dict[str, Any],
    request_arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind one SpliceAI row to the identity-selected MANE context."""
    prepared = dict(features)
    rows = [row for row in prepared.get("scores") or [] if isinstance(row, dict)]
    gene = str(expected_identity.get("gene") or "").strip()
    transcript = str(expected_identity.get("transcript") or "").strip()
    normalization = expected_identity.get("normalization")
    normalization = normalization if isinstance(normalization, dict) else {}
    selection = normalization.get("transcript_selection")
    selection = selection if isinstance(selection, dict) else {}
    mane_verified = selection.get("mane_select") is True

    matches: list[dict[str, Any]] = []
    for row in rows:
        row_gene = spliceai_row_gene(row)
        if not gene or row_gene.casefold() != gene.casefold():
            continue
        row_transcripts = spliceai_row_transcripts(row)
        if row_transcripts and transcript.casefold() not in row_transcripts:
            continue
        matched = dict(row)
        # Normalize the matched row onto canonical keys so downstream
        # Walker contract checks work with either provider schema.
        matched.setdefault("gene", row_gene)
        matches.append(matched)

    run_metadata = prepared.get("run_metadata")
    run_metadata = dict(run_metadata) if isinstance(run_metadata, dict) else {}
    arguments = request_arguments if isinstance(request_arguments, dict) else {}
    run_metadata.update(
        {
            "score_mode": run_metadata.get("score_mode"),
            "distance": arguments.get("distance"),
            "mask": arguments.get("mask"),
            "transcript_set": "MANE" if mane_verified else "",
            "selected_transcript": transcript,
            "selected_gene": gene,
            "selected_score_row": matches[0] if len(matches) == 1 else None,
            "row_match_count": len(matches),
        }
    )
    prepared["spliceai_run_metadata"] = run_metadata
    if run_metadata.get("model_version") not in (None, ""):
        prepared["provider_version"] = str(run_metadata["model_version"])
    if len(matches) == 1:
        selected = matches[0]
        prepared["selected_score_row"] = selected
        profile = normalize_spliceai_profile(
            selected,
            selected_transcript_claimed_max_delta_score=selected.get("max_delta_score"),
            distance=int(arguments.get("distance") or 500),
        )
        profile["provider_global_max_delta_score"] = prepared.get(
            "provider_global_max_delta_score"
        )
        profile["provider_global_max_transcript"] = prepared.get(
            "provider_global_max_transcript"
        )
        profile["provider_global_max_event"] = prepared.get("provider_global_max_event")
        prepared["spliceai_profile"] = profile
        if profile.get("status") == "resolved":
            prepared["max_delta_score"] = profile["max_delta_score"]
    return prepared


def _clinvar_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize the canonical ClinVar search or data envelope."""
    merged = dict(payload)
    raw_data = payload.get("raw_data")
    if isinstance(raw_data, dict):
        merged.update(raw_data)
    result_map = merged.get("result")
    if isinstance(result_map, dict):
        records = [
            value
            for key, value in result_map.items()
            if key != "uids" and isinstance(value, dict)
        ]
        if len(records) == 1:
            merged.update(records[0])
    return merged


def _clingen_context_fields(
    tool_name: str, payload: Any, raw: dict[str, Any]
) -> dict[str, Any]:
    request_arguments = raw.get("request_arguments")
    request_arguments = request_arguments if isinstance(request_arguments, dict) else {}
    gene = str(
        raw.get("gene_searched")
        or raw.get("gene")
        or request_arguments.get("gene")
        or ""
    )
    if tool_name in {
        "ClinGen_get_actionability_adult",
        "ClinGen_get_actionability_pediatric",
    }:
        context = (
            "Adult" if tool_name == "ClinGen_get_actionability_adult" else "Pediatric"
        )
        rows = payload if isinstance(payload, list) else []
        if not gene:
            for row in rows:
                if isinstance(row, dict):
                    gene = str(
                        _csv_row_value(
                            row,
                            "GENE SYMBOL",
                            "Gene Symbol",
                            "HGNC Gene Symbol",
                            "Gene(s)",
                        )
                        or ""
                    )
                    if gene:
                        break
        values: dict[str, Any] = {
            "gene": gene,
            "actionability_context": context,
            "actionability": [dict(row) for row in rows if isinstance(row, dict)],
            "total_available": raw.get("total", len(rows)),
            "provider_version": "ClinGen Clinical Actionability",
            "request_url": "https://actionability.clinicalgenome.org/",
        }
    else:
        rows = payload if isinstance(payload, list) else []
        key = (
            "dosage_curations"
            if tool_name == "ClinGen_get_dosage_sensitivity"
            else "variant_classifications"
        )
        if not gene:
            for row in rows:
                if not isinstance(row, dict):
                    continue
                gene = str(
                    _csv_row_value(
                        row,
                        "GENE SYMBOL",
                        "Gene Symbol",
                        "HGNC Gene Symbol",
                    )
                    or ""
                )
                if gene:
                    break
        values = {
            "gene": gene,
            key: [dict(row) for row in rows if isinstance(row, dict)],
            "total_available": raw.get("total", len(rows)),
            "provider_version": (
                "ClinGen Dosage Sensitivity"
                if tool_name == "ClinGen_get_dosage_sensitivity"
                else "ClinGen Evidence Repository"
            ),
            "request_url": (
                "https://search.clinicalgenome.org/kb/gene-dosage"
                if tool_name == "ClinGen_get_dosage_sensitivity"
                else "https://erepo.clinicalgenome.org/"
            ),
        }
    return _drop_empty(values)


def _hpo_fields(tool_name: str, payload: Any, raw: dict[str, Any]) -> dict[str, Any]:
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    arguments = raw.get("request_arguments")
    arguments = arguments if isinstance(arguments, dict) else {}
    term_id = str(metadata.get("term_id") or arguments.get("term_id") or "")
    values = {
        "hpo_term": term_id,
        "query": metadata.get("query") or arguments.get("query"),
        "values": payload,
        "total_available": metadata.get("total_available")
        or metadata.get("total")
        or raw.get("total_available"),
        "provider_version": metadata.get("source") or "HPO (JAX Ontology)",
        "request_url": "https://ontology.jax.org/api/hp/",
        "review_only": True,
    }
    return _drop_empty(values)


def _pubmed_fields(payload: Any, raw: dict[str, Any]) -> dict[str, Any]:
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    articles = payload if isinstance(payload, list) else []
    return {
        "articles": [dict(row) for row in articles if isinstance(row, dict)],
        "query": metadata.get("query"),
        "total_available": metadata.get("total", len(articles)),
        "provider_version": metadata.get("source") or "PubMed E-utilities",
        "request_url": "https://pubmed.ncbi.nlm.nih.gov/",
        "review_only": True,
    }


def _literature_search_fields(
    tool_name: str, payload: Any, raw: dict[str, Any]
) -> dict[str, Any]:
    if isinstance(payload, list):
        articles = payload
    elif isinstance(payload, dict):
        result_list = payload.get("resultList")
        result_list = result_list if isinstance(result_list, dict) else {}
        articles = (
            payload.get("articles")
            or payload.get("results")
            or payload.get("variants")
            or result_list.get("result")
            or []
        )
    else:
        articles = []
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    if tool_name == "LitVar_get_variant_publications":
        pmids = payload.get("pmids") if isinstance(payload, dict) else []
        pmcids = payload.get("pmcids") if isinstance(payload, dict) else []
        articles = [
            {"pmid": str(value)} for value in (pmids if isinstance(pmids, list) else [])
        ]
        for index, value in enumerate(pmcids if isinstance(pmcids, list) else []):
            pmcid = str(value)
            if index < len(articles):
                articles[index]["pmcid"] = pmcid
            else:
                articles.append({"pmcid": pmcid})
    source = (
        "LitVar"
        if tool_name in {"LitVar_search_variants", "LitVar_get_variant_publications"}
        else "PubTator3"
        if tool_name == "PubTator3_LiteratureSearch"
        else "Europe PMC"
    )
    return {
        "articles": [dict(row) for row in articles if isinstance(row, dict)],
        "query": metadata.get("query") or raw.get("query"),
        "total_available": (
            metadata.get("total")
            or raw.get("total")
            or raw.get("hitCount")
            or len(articles)
        ),
        "provider_version": source,
        "request_url": (
            "https://www.ncbi.nlm.nih.gov/research/litvar2/"
            if source == "LitVar"
            else "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/"
            if source == "PubTator3"
            else "https://www.ebi.ac.uk/europepmc/webservices/rest/"
        ),
        "review_only": True,
    }


def _literature_annotation_fields(
    tool_name: str,
    payload: Any,
    raw: dict[str, Any],
) -> dict[str, Any]:
    """Preserve text-mined entities as review context, never as evidence."""
    if tool_name == "PubTator3_get_annotations":
        documents = payload if isinstance(payload, list) else []
        if isinstance(payload, dict):
            documents = (
                payload.get("PubTator3")
                or payload.get("documents")
                or payload.get("results")
                or []
            )
        documents = [dict(row) for row in documents if isinstance(row, dict)]
        return {
            "pmids": [
                str(row.get("pmid") or row.get("_id") or row.get("id") or "")
                for row in documents
                if row.get("pmid") or row.get("_id") or row.get("id")
            ],
            "annotations": documents,
            "provider_version": "PubTator3",
            "request_url": ("https://www.ncbi.nlm.nih.gov/research/pubtator3-api/"),
            "review_only": True,
        }
    payload_map = payload if isinstance(payload, dict) else {}
    return {
        "pmid": raw.get("pmid") or payload_map.get("pmid"),
        "pmcid": payload_map.get("pmcid") or raw.get("pmcid"),
        "article_id": payload_map.get("article_id"),
        "annotations": payload_map.get("annotations") or [],
        "annotation_counts": payload_map.get("annotation_counts") or {},
        "provider_version": "Europe PMC Annotations API",
        "request_url": "https://www.ebi.ac.uk/europepmc/annotations_api/",
        "review_only": True,
    }


def _uniprot_fields(payload: dict[str, Any]) -> dict[str, Any]:
    accession = str(payload.get("primaryAccession") or payload.get("accession") or "")
    description = (
        payload.get("proteinDescription")
        if isinstance(payload.get("proteinDescription"), dict)
        else {}
    )
    recommended = description.get("recommendedName")
    recommended = recommended if isinstance(recommended, dict) else {}
    submission_names = description.get("submissionNames")
    submission_names = submission_names if isinstance(submission_names, list) else []
    name = (
        (recommended.get("fullName") or {}).get("value")
        if isinstance(recommended.get("fullName"), dict)
        else ""
    ) or next(
        (
            (row.get("fullName") or {}).get("value")
            for row in submission_names
            if isinstance(row, dict) and isinstance(row.get("fullName"), dict)
        ),
        "",
    )
    comments = [
        dict(row) for row in payload.get("comments") or [] if isinstance(row, dict)
    ]
    features = [
        dict(row) for row in payload.get("features") or [] if isinstance(row, dict)
    ]
    comments_by_type: dict[str, list[dict[str, Any]]] = {}
    cofactors: list[dict[str, Any]] = []
    for comment in comments:
        comment_type = str(comment.get("commentType") or "")
        if comment_type:
            comments_by_type.setdefault(comment_type, []).append(comment)
        if comment_type == "COFACTOR":
            notes = [
                str(row.get("value"))
                for row in (comment.get("note") or {}).get("texts") or []
                if isinstance(row, dict) and row.get("value")
            ]
            for row in comment.get("cofactors") or []:
                if not isinstance(row, dict) or not row.get("name"):
                    continue
                item = dict(row)
                if notes:
                    item["notes"] = notes
                cofactors.append(item)
    protein_sites = [
        {
            key: row.get(key)
            for key in ("type", "description", "location", "evidences")
            if row.get(key) not in (None, "", [], {})
        }
        for row in features
        if str(row.get("type") or "").casefold()
        in {
            "active site",
            "binding site",
            "domain",
            "region",
            "repeat",
            "modified residue",
            "natural variant",
        }
    ]
    cross_reference_index = [
        {
            key: row.get(key)
            for key in ("database", "id", "properties")
            if row.get(key) not in (None, "", [], {})
        }
        for row in payload.get("uniProtKBCrossReferences") or []
        if isinstance(row, dict)
    ]
    reference_index = [
        {
            key: row.get(key)
            for key in ("citation", "referencePositions", "referenceComments")
            if row.get(key) not in (None, "", [], {})
        }
        for row in payload.get("references") or []
        if isinstance(row, dict)
    ]
    sequence = payload.get("sequence")
    sequence = sequence if isinstance(sequence, dict) else {}
    entry_type = str(payload.get("entryType") or "")
    entry_status = (
        "inactive"
        if entry_type.casefold().startswith("inactive")
        else "reviewed"
        if "reviewed" in entry_type.casefold()
        and "unreviewed" not in entry_type.casefold()
        else "unreviewed"
        if "unreviewed" in entry_type.casefold()
        else "unknown"
    )
    return {
        "protein_accession": accession,
        "entry_type": entry_type,
        "entry_status": entry_status,
        "entry_id": payload.get("uniProtkbId"),
        "protein_name": name,
        "genes": payload.get("genes") or [],
        "organism": payload.get("organism") or {},
        "sequence": sequence,
        "sequence_length": sequence.get("length"),
        "comments": comments,
        "features": features,
        "function_comments": comments_by_type.get("FUNCTION", []),
        "disease_comments": comments_by_type.get("DISEASE", []),
        "catalytic_activity": comments_by_type.get("CATALYTIC ACTIVITY", []),
        "ptm_comments": comments_by_type.get("PTM", []),
        "cofactors": cofactors,
        "protein_sites": protein_sites,
        "ptm_features": [
            row
            for row in protein_sites
            if str(row.get("type") or "").casefold() == "modified residue"
        ],
        "domain_features": [
            row
            for row in protein_sites
            if str(row.get("type") or "").casefold() in {"domain", "region", "repeat"}
        ],
        "keywords": payload.get("keywords") or [],
        "cross_references": payload.get("uniProtKBCrossReferences") or [],
        "references": payload.get("references") or [],
        "cross_reference_index": cross_reference_index,
        "reference_index": reference_index,
        "provider_version": "UniProtKB REST API",
        "request_url": (
            f"https://rest.uniprot.org/uniprotkb/{accession}.json"
            if accession
            else "https://rest.uniprot.org/uniprotkb/"
        ),
        "review_only": True,
    }


def adapt_source_output(tool_name: str, raw_output: Any) -> dict[str, Any]:
    """Extract auditable provider facts while separating provider conclusions."""
    raw = raw_output if isinstance(raw_output, dict) else {"raw_output": raw_output}
    payload = _provider_payload(raw)
    payload_dict = payload if isinstance(payload, dict) else {}
    name = tool_name.lower()
    category = _source_category(tool_name)
    assertions: dict[str, Any] = {}

    if "spliceai" in name:
        features = _spliceai_fields(payload_dict)
    elif tool_name == "EBIProteins_get_variation_by_hgvs":
        features = _ebi_protein_variation_fields(raw, payload_dict)
    elif tool_name == "EBIProteins_get_variation":
        features = _ebi_protein_known_variation_fields(payload_dict)
    elif tool_name == "EBIProteins_get_features":
        features = _ebi_protein_feature_fields(payload_dict)
    elif tool_name == "InterPro_get_entries_for_protein":
        features = _interpro_protein_fields(payload_dict)
    elif tool_name == "UniProt_get_entry_by_accession":
        features = _uniprot_fields(payload_dict)
    elif tool_name == "FAVOR_annotate_variant":
        favor_payload = raw.get("data")
        favor_payload = (
            favor_payload if isinstance(favor_payload, dict) else payload_dict
        )
        features = _favor_fields(favor_payload, raw)
    elif tool_name in {
        "OpenTargets_get_variant_info",
        "OpenTargets_get_variant_transcript_consequences",
    }:
        features = _open_targets_consequence_fields(payload_dict)
    elif tool_name in {
        "GenomeNexus_annotate_variant",
        "GenomeNexus_annotate_dbsnp",
    }:
        features = _genome_nexus_fields(payload_dict)
    elif tool_name == "Mutalyzer_normalize_variant":
        features = _mutalyzer_fields(payload_dict)
    elif tool_name == "ProtVar_map_variant":
        features = _protvar_fields(payload_dict)
    elif tool_name == "gProfiler_annotate_snps":
        features = _gprofiler_snp_fields(payload)
    elif "variantvalidator" in name:
        features = _variantvalidator_fields(raw)
    elif "myvariant" in name:
        features = _myvariant_fields(raw, payload_dict)
    elif "vep" in name:
        features = _vep_fields(raw, payload, tool_name)
    elif tool_name == "gnomad_get_site_callability":
        features = _copy(
            payload_dict,
            {
                "chrom",
                "position",
                "reference_genome",
                "dataset",
                "callsets",
                "request_arguments",
            },
        )
    elif tool_name == "gnomad_get_constraint":
        features = _constraint_fields(payload_dict)
    elif tool_name == "gnomad_get_region_variants":
        features = _gnomad_region_variants_fields(payload_dict)
    elif tool_name == "gnomad_search_variants":
        rows = payload_dict.get("variant_search")
        features = {
            "variant_search": rows if isinstance(rows, list) else [],
            "provider_version": "gnomAD GraphQL variant search",
        }
    elif tool_name == "ensembl_lookup_gene":
        features = _ensembl_lookup_fields(payload_dict)
    elif tool_name in {
        "ClinGen_search_gene_validity",
        "ClinGen_get_gene_validity",
    } and isinstance(payload, list):
        features = _clingen_validity_fields(payload, raw)
    elif tool_name in {
        "ClinGen_get_dosage_sensitivity",
        "ClinGen_get_actionability_adult",
        "ClinGen_get_actionability_pediatric",
        "ClinGen_get_variant_classifications",
    }:
        features = _clingen_context_fields(tool_name, payload, raw)
    elif tool_name.startswith("HPO_"):
        features = _hpo_fields(tool_name, payload, raw)
    elif tool_name == "PubMed_search_articles":
        features = _pubmed_fields(payload, raw)
    elif tool_name in {
        "LitVar_search_variants",
        "LitVar_get_variant_publications",
        "EuropePMC_search_articles",
        "PubTator3_LiteratureSearch",
    }:
        features = _literature_search_fields(tool_name, payload, raw)
    elif tool_name in {
        "PubTator3_get_annotations",
        "EPMC_get_text_mined_annotations",
    }:
        features = _literature_annotation_fields(tool_name, payload, raw)
    elif category == "population":
        features = _population_fields(payload_dict)
    elif "clinvar" in name:
        clinvar_payload = _clinvar_payload(payload_dict)
        result_map = clinvar_payload.get("result")
        if isinstance(result_map, dict):
            uid_records = [
                value
                for key, value in result_map.items()
                if key != "uids" and isinstance(value, dict)
            ]
            if len(uid_records) == 1:
                clinvar_payload = uid_records[0]
        features = _copy(
            clinvar_payload,
            {
                "vcv",
                "vcv_id",
                "rcv",
                "rcv_id",
                "variation_id",
                "review_status",
                "stars",
                "submitters",
                "conditions",
                "date",
                "last_evaluated",
                "assertion_criteria",
                "conflicts",
                "variants",
                "variant_ids",
                "total_count",
                "title",
                "genes",
                "accession",
                "accession_version",
                "uid",
                "obj_type",
                "germline_classification",
                "clinical_significance",
            },
        )
    elif "genebe" in name or "intervar" in name:
        features = _copy(
            raw, {"version", "date", "source", "gene", "transcript", "hgvs_c", "hgvs_p"}
        )
    else:
        features = {
            key: value
            for key, value in raw.items()
            if key.casefold() not in _CONCLUSION_KEYS
        }

    if isinstance(payload_dict, dict):
        features.update(_identity_fields(raw, payload_dict))
    for key, value in raw.items():
        lowered = key.casefold()
        if lowered in _CONCLUSION_KEYS or any(
            token in lowered
            for token in (
                "classification",
                "interpretation",
                "criterion",
                "pathogenic",
                "benign",
            )
        ):
            assertions[key] = value
    features = _quarantine(features, "reviewable_features", assertions)
    raw_json = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str)
    provenance: dict[str, Any] = {
        "raw_result_hash": hashlib.sha256(raw_json.encode()).hexdigest()
    }
    source_url = raw.get("url") or raw.get("source_url")
    if not source_url:
        source_url = features.get("request_url")
    if isinstance(source_url, str) and source_url:
        provenance["source_url"] = source_url
    return {
        "tool_name": tool_name,
        "source_category": category,
        "reviewable_features": features,
        "quarantined_conclusions": assertions,
        "source_provenance": provenance,
        "source_lead_summary": (
            f"{tool_name} preserved as {category} source lead; reviewable facts are "
            "retained and provider conclusions remain source assertions."
        ),
        "source_lead_only": True,
        "final_classification_allowed": False,
        "raw_source_present": raw_output is not None,
    }


def _csv_row_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row[key]
    lowered = {str(existing).casefold(): existing for existing in row}
    for key in keys:
        existing = lowered.get(key.casefold())
        if existing is not None and row.get(existing) not in (None, ""):
            return row[existing]
    return None


def _clingen_validity_fields(payload: Any, raw: dict[str, Any]) -> dict[str, Any]:
    rows = payload if isinstance(payload, list) else []
    curations: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        curations.append(
            {
                "gene": _csv_row_value(row, "GENE SYMBOL", "Gene Symbol"),
                "disease_label": _csv_row_value(row, "DISEASE LABEL", "Disease Label"),
                "disease_id": _csv_row_value(
                    row, "DISEASE ID (MONDO)", "Disease ID (MONDO)"
                ),
                "moi": _csv_row_value(row, "MOI", "Moi"),
                "gene_disease_validity": _csv_row_value(
                    row, "CLASSIFICATION", "Classification"
                ),
                "online_report": _csv_row_value(row, "ONLINE REPORT", "Online Report"),
                "classification_date": _csv_row_value(
                    row, "CLASSIFICATION DATE", "Classification Date"
                ),
                "gcep": _csv_row_value(row, "GCEP", "Gcep"),
            }
        )
    gene = str(raw.get("gene_searched") or "") or next(
        (str(curation["gene"]) for curation in curations if curation.get("gene")),
        "",
    )
    return _drop_empty(
        {
            "gene": gene or None,
            "validity_curations": curations,
            "provider_version": "ClinGen Gene-Disease Validity",
            "request_url": "https://search.clinicalgenome.org/kb/gene-validity/download",
        }
    )


def _constraint_fields(payload: dict[str, Any]) -> dict[str, Any]:
    dataset = payload.get("dataset")
    release = payload.get("release") or payload.get("provider_version")
    provider = release or (
        f"gnomAD constraint {dataset}" if dataset else "gnomAD gene constraint GraphQL"
    )
    return _drop_empty(
        {
            "gene": payload.get("gene_symbol") or payload.get("gene"),
            "gene_id": payload.get("gene_id"),
            "dataset": dataset,
            "reference_genome": payload.get("reference_genome"),
            "pli": payload.get("pLI"),
            "loeuf": payload.get("loeuf"),
            "oe_lof": payload.get("oe_lof"),
            "oe_lof_lower": payload.get("oe_lof_lower"),
            "oe_lof_upper": payload.get("oe_lof_upper"),
            "mis_z": payload.get("mis_z"),
            "syn_z": payload.get("syn_z"),
            "obs_lof": payload.get("obs_lof"),
            "exp_lof": payload.get("exp_lof"),
            "release": release,
            "provider_version": provider,
        }
    )


def _ensembl_lookup_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse an Ensembl lookup payload (transcript or gene) into exon facts."""
    exons: list[dict[str, Any]] = []
    transcript_rows = payload.get("Transcript")
    rows = transcript_rows if isinstance(transcript_rows, list) else [payload]
    for row in rows:
        if not isinstance(row, dict):
            continue
        for exon in row.get("Exon") or []:
            if not isinstance(exon, dict):
                continue
            exons.append(
                {
                    "exon_id": exon.get("id"),
                    "transcript": row.get("id"),
                    "rank": exon.get("rank"),
                    "chrom": exon.get("seq_region_name")
                    or payload.get("seq_region_name"),
                    "start": exon.get("start"),
                    "end": exon.get("end"),
                    "strand": exon.get("strand"),
                }
            )
    return _drop_empty(
        {
            "transcript_id": payload.get("id"),
            "chrom": payload.get("seq_region_name"),
            "exons": exons,
            "provider_version": "Ensembl REST lookup",
        }
    )


def _gnomad_region_variants_fields(payload: dict[str, Any]) -> dict[str, Any]:
    region = payload.get("region")
    region = dict(region) if isinstance(region, dict) else {}
    variants: list[dict[str, Any]] = []
    for row in region.get("variants") or []:
        if not isinstance(row, dict):
            continue
        exome = row.get("exome") if isinstance(row.get("exome"), dict) else {}
        genome = row.get("genome") if isinstance(row.get("genome"), dict) else {}
        variants.append(
            {
                "variant_id": row.get("variant_id"),
                "consequence": row.get("consequence"),
                "filters": row.get("filters"),
                "af_exome": exome.get("af"),
                "af_genome": genome.get("af"),
                "homozygote_count_exome": exome.get("homozygote_count"),
                "homozygote_count_genome": genome.get("homozygote_count"),
            }
        )
    return _drop_empty(
        {
            "chrom": region.get("chrom"),
            "start": region.get("start"),
            "stop": region.get("stop"),
            "variants": variants,
            "provider_version": "gnomAD GraphQL region variants",
        }
    )


__all__ = [
    "adapt_source_output",
    "build_matches",
    "coordinates",
    "explicit_allele_conflict",
    "has_variant_identity",
    "identity_matches",
    "ncbi_refsnp_alleles",
    "prepare_spliceai_features",
    "provider_version",
    "result_identity",
    "source_fact_ready",
]
