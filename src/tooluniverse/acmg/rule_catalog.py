"""Machine-readable provenance for deterministic ACMG evidence rules."""

from __future__ import annotations

from typing import Any


MONDO_RESOLUTION_POLICY_VERSION = "2026-08-13-v3"
CSPEC_SCENARIO_POLICY_VERSION = "2026-08-13-v3"
USER_DECISION_SCENARIO_POLICY_VERSION = "2026-08-09-v3"
GENE_RESOLUTION_POLICY_VERSION = "2026-08-25-v1"
IDENTITY_VERIFICATION_POLICY = {
    "version": "2026-08-25-v4.2",
    "cross_provider_minimum": 2,
    "single_provider_fallback": "variantvalidator_complete_allele",
    "single_provider_required_fields": [
        "validated_hgvs_c",
        "hgvs_g",
        "gene",
        "transcript",
        "coordinates",
        "provider_version",
    ],
    "fail_closed_on_identity_conflict": True,
    "identity_dimension": "allele_and_build",
    "gene_and_transcript_are_target_binding_dimensions": True,
    "normalization_context_is_non_veto": True,
    "cross_provider_agreement": "matching_authoritative_component",
}
IDENTITY_PROVIDER_ROLES = {
    "VariantValidator_validate_variant": "authoritative",
    "EnsemblVEP_variant_recoder": "authoritative",
    "EnsemblVEP_annotate_hgvs": "authoritative",
    "NCBIVariation_rsid_lookup": "authoritative",
    "Mutalyzer_normalize_variant": "normalization_context",
    "gProfiler_annotate_snps": "normalization_context",
}


ACMG_CRITERIA = (
    "PVS1",
    "PS1",
    "PS2",
    "PS3",
    "PS4",
    "PM1",
    "PM2",
    "PM3",
    "PM4",
    "PM5",
    "PM6",
    "PP1",
    "PP2",
    "PP3",
    "PP4",
    "PP5",
    "BA1",
    "BS1",
    "BS2",
    "BS3",
    "BS4",
    "BP1",
    "BP2",
    "BP3",
    "BP4",
    "BP5",
    "BP6",
    "BP7",
)


_NOT_CONSEQUENCE_GATED = {
    "PS2",
    "PS3",
    "PS4",
    "PM2",
    "PM3",
    "PM6",
    "PP1",
    "PP4",
    "BA1",
    "BS1",
    "BS2",
    "BS3",
    "BS4",
    "BP2",
    "BP5",
}

CONSEQUENCE_POLICIES: dict[str, dict[str, Any]] = {
    criterion: {"mode": "not_consequence_gated"} for criterion in _NOT_CONSEQUENCE_GATED
}
CONSEQUENCE_POLICIES.update(
    {
        "PVS1": {
            "mode": "gated",
            "protein_effects": ["lof"],
            "splice_classes": ["canonical"],
        },
        "PS1": {"mode": "gated", "protein_effects": ["missense"]},
        "PM1": {"mode": "gated", "protein_effects": ["missense"]},
        "PM4": {
            "mode": "gated",
            "protein_effects": ["inframe"],
            "terms": ["stop_lost"],
        },
        "PM5": {"mode": "gated", "protein_effects": ["missense"]},
        "PP2": {"mode": "gated", "protein_effects": ["missense"]},
        "PP3": {
            "mode": "gated",
            "protein_effects": ["missense"],
            "splice_classes": ["noncanonical"],
        },
        "BP1": {"mode": "gated", "protein_effects": ["missense"]},
        "BP3": {"mode": "gated", "protein_effects": ["inframe"]},
        "BP4": {
            "mode": "gated",
            "protein_effects": ["missense"],
            "splice_classes": ["noncanonical"],
        },
        "BP7": {
            "mode": "gated",
            "protein_effects": ["synonymous", "noncoding"],
        },
        "PP5": {"mode": "deprecated"},
        "BP6": {"mode": "deprecated"},
    }
)


def _rule(
    rule_id: str,
    version: str,
    scope: str,
    inputs: list[str],
    reference: str,
    **decision_spec: Any,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "version": version,
        "scope": scope,
        "required_inputs": inputs,
        "primary_reference": reference,
        "countable_strengths": [],
        "bayesian_odds": {},
        **decision_spec,
    }


RULE_CATALOG = {
    "PM2": _rule(
        "clingen-svi-pm2",
        "1.0",
        "population absence",
        ["allele count", "allele number", "explicit coverage assessment"],
        "ClinGen SVI PM2 Recommendation v1.0, approved 2020-09-04",
        absent_strength="Supporting",
        countable_strengths=["PM2_Supporting"],
        bayesian_odds={"PM2_Supporting": 2.08},
    ),
    "BA1": _rule(
        "acmg-ba1-with-clingen-exceptions",
        "1.0",
        "stand-alone population evidence",
        ["global or popmax AF", "BA1 exception status"],
        "Richards et al. 2015, PMID:25741868; ClinGen BA1 exception guidance",
    ),
    "BS1": _rule(
        "acmg-bs1-disease-specific",
        "1.0",
        "disease-specific population evidence",
        ["popmax AF", "maximum credible AF"],
        "Richards et al. 2015, PMID:25741868",
        countable_strengths=["BS1"],
        bayesian_odds={"BS1": 0.053},
    ),
    "PP3": _rule(
        "clingen-svi-pejaver-pp3-bp4",
        "2022",
        "pre-specified calibrated missense computational evidence",
        [
            "missense variant type",
            "predictor name",
            "predictor score",
            "pre-specified policy",
        ],
        "Pejaver et al. 2022 Table 2, PMID:36413997",
        applicable_variant_types=["missense", "missense_variant"],
        thresholds={
            "REVEL": {
                "bp4_very_strong_max": 0.003,
                "bp4_strong_max": 0.016,
                "bp4_moderate_max": 0.183,
                "bp4_supporting_max": 0.290,
                "pp3_supporting_min": 0.644,
                "pp3_moderate_min": 0.773,
                "pp3_strong_min": 0.932,
            },
        },
        countable_strengths=[
            "PP3_Supporting",
            "PP3_Moderate",
            "PP3_Strong",
            "BP4_Supporting",
            "BP4_Moderate",
            "BP4_Strong",
            "BP4_VeryStrong",
        ],
        bayesian_odds={
            "PP3_Supporting": 2.08,
            "PP3_Moderate": 4.3,
            "PP3_Strong": 18.7,
            "BP4_Supporting": 0.48,
            "BP4_Moderate": 0.233,
            "BP4_Strong": 0.053,
            "BP4_VeryStrong": 0.00286,
        },
    ),
    "BP4": _rule(
        "clingen-svi-pejaver-pp3-bp4",
        "2022",
        "pre-specified calibrated missense computational evidence",
        [
            "missense variant type",
            "predictor name",
            "predictor score",
            "pre-specified policy",
        ],
        "Pejaver et al. 2022 Table 2, PMID:36413997",
        shared_decision_spec="PP3",
    ),
    "BP7": _rule(
        "clingen-svi-walker-bp7",
        "2023.1",
        "synonymous or deep-intronic variant with no predicted splice impact",
        [
            "strict Walker BP4 result",
            "selected-transcript consequence",
            "transcript-relative intronic position",
        ],
        "Walker et al. 2023, PMID:37352859",
        donor_region_max=7,
        acceptor_region_min=-21,
        countable_strengths=["BP7_Supporting"],
        bayesian_odds={"BP7_Supporting": 0.48},
    ),
    "PVS1": _rule(
        "clingen-svi-pvs1",
        "1.2",
        "loss-of-function and splicing evidence",
        [
            "gene LoF disease mechanism",
            "selected-transcript consequence",
            "transcript biotype",
            "exon position (exon_number/exon_total)",
            "NMD region",
            "SpliceAI native-site loss DS/DP for canonical splice routes",
        ],
        "Abou Tayoun et al. 2018, PMID:30192042",
        countable_strengths=[
            "PVS1_Supporting",
            "PVS1_Moderate",
            "PVS1_Strong",
            "PVS1",
        ],
        bayesian_odds={
            "PVS1_Supporting": 2.08,
            "PVS1_Moderate": 4.3,
            "PVS1_Strong": 18.7,
            "PVS1": 350.0,
        },
    ),
    "PS2": _rule(
        "clingen-svi-de-novo",
        "1.1",
        "confirmed de novo evidence",
        ["parental relationships", "phenotype specificity", "proband records"],
        "ClinGen SVI de novo recommendation v1.1, updated 2021-05-05",
        countable_strengths=["PS2_Supporting", "PS2_Moderate", "PS2", "PS2_VeryStrong"],
        bayesian_odds={
            "PS2_Supporting": 2.08,
            "PS2_Moderate": 4.3,
            "PS2": 18.7,
            "PS2_VeryStrong": 350.0,
        },
    ),
    "PM6": _rule(
        "clingen-svi-de-novo",
        "1.1",
        "assumed de novo evidence",
        ["parental relationships", "phenotype specificity", "proband records"],
        "ClinGen SVI de novo recommendation v1.1, updated 2021-05-05",
        countable_strengths=["PM6_Supporting", "PM6", "PM6_Strong", "PM6_VeryStrong"],
        bayesian_odds={
            "PM6_Supporting": 2.08,
            "PM6": 4.3,
            "PM6_Strong": 18.7,
            "PM6_VeryStrong": 350.0,
        },
    ),
    "PP1": _rule(
        "clingen-svi-pp1-pp4-bs4",
        "2023.1",
        "coupled phenotype-specificity and family co-segregation evidence",
        [
            "inheritance mode",
            "penetrance and phenocopy context",
            "affected/unaffected co-segregations",
            "phenotype diagnostic yield",
        ],
        "Biesecker et al. 2024, PMID:38103548",
        combined_pathogenic_point_cap=5.0,
        countable_strengths=["PP1_Supporting", "PP1_Moderate", "PP1_Strong"],
        bayesian_odds={
            "PP1_Supporting": 2.08,
            "PP1_Moderate": 4.3,
            "PP1_Strong": 18.7,
        },
    ),
    "PP4": _rule(
        "clingen-svi-pp1-pp4-bs4",
        "2023.1",
        "diagnostic-yield phenotype specificity coupled to co-segregation",
        [
            "gene-phenotype dyad",
            "testing-method diagnostic yield",
            "locus heterogeneity",
            "variants per allele",
        ],
        "Biesecker et al. 2024, PMID:38103548",
        minimum_diagnostic_yield=0.191,
        combined_pathogenic_point_cap=5.0,
        countable_strengths=["PP4_Supporting", "PP4_Moderate", "PP4_Strong"],
        bayesian_odds={
            "PP4_Supporting": 2.08,
            "PP4_Moderate": 4.3,
            "PP4_Strong": 18.7,
        },
    ),
    "PM3": _rule(
        "clingen-svi-pm3",
        "1.0",
        "recessive in-trans evidence",
        ["inheritance mode", "frequency eligibility", "proband records", "phase"],
        "ClinGen SVI PM3 Recommendation v1.0, approved 2019-05-02",
        point_thresholds={
            "supporting": 0.5,
            "moderate": 1.0,
            "strong": 2.0,
            "very_strong": 4.0,
        },
        countable_strengths=[
            "PM3_Supporting",
            "PM3",
            "PM3_Strong",
            "PM3_VeryStrong",
        ],
        bayesian_odds={
            "PM3_Supporting": 2.08,
            "PM3": 4.3,
            "PM3_Strong": 18.7,
            "PM3_VeryStrong": 350.0,
        },
    ),
    "PP5": _rule(
        "clingen-svi-pp5-bp6-deprecation",
        "1.0",
        "deprecated source assertion",
        ["source assertion"],
        "Biesecker and Harrison 2018, PMID:29543229",
    ),
    "BP6": _rule(
        "clingen-svi-pp5-bp6-deprecation",
        "1.0",
        "deprecated source assertion",
        ["source assertion"],
        "Biesecker and Harrison 2018, PMID:29543229",
    ),
    "PM1": _rule(
        "acmg-pm1",
        "2015",
        "critical domain evidence",
        ["variant type", "domain", "pathogenic enrichment"],
        "Richards et al. 2015, PMID:25741868",
    ),
    "BP1": _rule(
        "acmg-bp1",
        "2015",
        "missense mechanism evidence",
        ["variant type", "gene disease mechanism"],
        "Richards et al. 2015, PMID:25741868",
    ),
    "PS3": _rule(
        "clingen-svi-brnich-ps3-bs3",
        "1.0",
        "validated functional assay evidence",
        ["model", "classified controls", "replicates", "readout", "OddsPath"],
        "Brnich et al. 2019, PMID:31892348",
        odds_path_thresholds={
            "pathogenic": {"supporting": 2.1, "moderate": 4.3, "strong": 18.7},
            "benign": {"supporting": 0.48, "moderate": 0.23, "strong": 0.053},
        },
        countable_strengths=["PS3_Supporting", "PS3_Moderate", "PS3"],
        bayesian_odds={"PS3_Supporting": 2.08, "PS3_Moderate": 4.3, "PS3": 18.7},
    ),
    "BS3": _rule(
        "clingen-svi-brnich-ps3-bs3",
        "1.0",
        "validated functional assay evidence",
        ["model", "controls", "replicates", "readout", "validation"],
        "Brnich et al. 2019, PMID:31892348",
        countable_strengths=["BS3_Supporting", "BS3_Moderate", "BS3"],
        bayesian_odds={"BS3_Supporting": 0.48, "BS3_Moderate": 0.23, "BS3": 0.053},
    ),
    "BS4": _rule(
        "clingen-svi-pp1-pp4-bs4",
        "2023.1",
        "lack of segregation in an applicable family configuration",
        [
            "affected non-carrier",
            "confirmed phenotype",
            "penetrance and phenocopy context",
            "inheritance configuration",
        ],
        "Biesecker et al. 2024, PMID:38103548",
        countable_strengths=["BS4"],
        bayesian_odds={"BS4": 0.053},
    ),
    "PM4": _rule(
        "acmg-pm4",
        "2015",
        "protein length change",
        ["variant consequence", "repeat context"],
        "Richards et al. 2015, PMID:25741868",
    ),
    "PS4": _rule(
        "clingen-svi-ps4",
        "1.0",
        "case enrichment and structured case evidence",
        ["independent cases", "phenotype", "case-control statistics or case threshold"],
        "Richards et al. 2015, PMID:25741868; ClinGen SVI PS4 guidance",
    ),
}


SPLICEAI_RULE = _rule(
    "clingen-svi-walker-spliceai-pp3-bp4",
    "2023.1",
    "calibrated non-canonical splicing computational evidence",
    [
        "normalized small-variant identity",
        "transcript consequence and splice position",
        "SpliceAI maximum delta score",
        "SpliceAI model version",
    ],
    "Walker et al. 2023, PMID:37352859",
    applicable_criteria=["PP3", "BP4", "PP3/BP4"],
    excluded_splice_positions=[-2, -1, 1, 2],
    thresholds={"pp3_supporting_min": 0.2, "bp4_supporting_max": 0.1},
    countable_strengths=["PP3_Supporting", "BP4_Supporting"],
    bayesian_odds={"PP3_Supporting": 2.08, "BP4_Supporting": 0.48},
)


# Optional compiled CSpec details. The online ClinGen Registry document is the
# source of truth; these entries can add executable details only when they carry
# a content_hash that exactly matches the freshly fetched document. Natural
# language is never parsed into thresholds here at runtime.
CSPEC_RULE_CATALOG: dict[tuple[str, str], dict[str, Any]] = {
    # ClinGen PTEN Expert Panel Specifications v3.2 (registry id GN003).
    # Reviewed 2026-07-23 against the released JSON-LD document:
    # PM1 is applicable only at Moderate strength, defined as residues in
    # catalytic motifs 90-94, 123-130, 166-168 on NP_000305.3 (PTEN, P60484;
    # MANE Select NM_000314.8). The VCEP's adoption of the 2015 PM1 wording
    # ("critical and well-established functional domain ... without benign
    # variation") for exactly these motifs is the basis for
    # critical_region_established and benign_variation_depleted.
    ("GN003", "3.2"): {
        "specification_id": "GN003",
        "rule_id": "clingen-cspec-gn003-pten-3.2",
        "version": "3.2",
        "gene": "PTEN",
        "mondo": "MONDO:0017623",
        "inheritance": "AD",
        "status": "approved_active",
        "primary_reference": (
            "ClinGen PTEN Expert Panel Specifications to the ACMG/AMP Variant "
            "Interpretation Guidelines for PTEN Version 3.2, "
            "https://cspec.genome.network/cspec/ui/svi/doc/GN003"
        ),
        "criteria": {
            "PM1": {
                "protein_accession": "P60484",
                "transcript": "NM_000314.8",
                "regions": [
                    {"start": 90, "end": 94},
                    {"start": 123, "end": 130},
                    {"start": 166, "end": 168},
                ],
                "variant_types": ["missense"],
                "critical_region_established": True,
                "benign_variation_depleted": True,
                "strength": "PM1_Moderate",
                "mutually_exclusive_with": [],
                "review_basis": (
                    "GN003 v3.2 PM1 Moderate (Applicable): 'Defined to include "
                    "residues in catalytic motifs: 90-94, 123-130, 166-168 "
                    "(NP_000305.3)'; reviewed 2026-07-23"
                ),
            }
        },
        "countable_strengths": ["PM1_Moderate"],
        "bayesian_odds": {"PM1_Moderate": 4.3},
    },
}

_DEFAULT_STRENGTH_LEVELS = {
    "PVS1": "VeryStrong",
    "PS": "Strong",
    "PM": "Moderate",
    "PP": "Supporting",
    "BA": "StandAlone",
    "BS": "Strong",
    "BP": "Supporting",
}

_GENERIC_TAVTIGIAN_ODDS = {
    ("pathogenic", "VeryStrong"): 350.0,
    ("pathogenic", "Strong"): 18.7,
    ("pathogenic", "Moderate"): 4.3,
    ("pathogenic", "Supporting"): 2.08,
    ("benign", "VeryStrong"): 0.00286,
    ("benign", "Strong"): 0.053,
    ("benign", "Moderate"): 0.233,
    ("benign", "Supporting"): 0.48,
}

_DEPRECATED_CRITERIA = {"PP5", "BP6"}
_DETERMINISTIC_GENERAL_CRITERIA = {
    "PVS1",
    "PS2",
    "PS3",
    "PM2",
    "PM3",
    "PM6",
    "PP3",
    "BS1",
    "BS3",
    "BP4",
    "BP7",
}
_DISEASE_SPECIFIC_CRITERIA = {"PS4", "PM1", "PP2", "PP4", "BA1", "BS1", "BS2"}

_PROVIDER_ROUTES: dict[str, tuple[str, ...]] = {
    "PVS1": (
        "consequence",
        "splicing_prediction",
        "protein_context",
        "disease_context",
    ),
    "PS1": ("consequence", "protein_context", "prior_variant_candidates"),
    "PS2": ("literature",),
    "PS3": ("literature",),
    "PS4": ("literature", "disease_context"),
    "PM1": ("protein_context", "dynamic_cspec", "literature"),
    "PM2": ("population", "callability"),
    "PM3": ("literature",),
    "PM4": ("consequence", "protein_context", "literature"),
    "PM5": ("consequence", "protein_context", "prior_variant_candidates"),
    "PM6": ("literature",),
    "PP1": ("literature",),
    "PP2": ("disease_context", "constraint", "literature"),
    "PP3": ("computational", "splicing_prediction"),
    "PP4": ("phenotype_context", "dynamic_cspec", "literature"),
    "PP5": (),
    "BA1": ("population", "dynamic_cspec"),
    "BS1": ("population", "dynamic_cspec"),
    "BS2": ("literature",),
    "BS3": ("literature",),
    "BS4": ("literature",),
    "BP1": ("disease_context", "constraint", "literature"),
    "BP2": ("literature",),
    "BP3": ("consequence", "protein_context", "literature"),
    "BP4": ("computational", "splicing_prediction"),
    "BP5": ("literature",),
    "BP6": (),
    "BP7": ("consequence", "splicing_prediction"),
}

_LITERATURE_FACT_TYPES: dict[str, tuple[str, ...]] = {
    "PVS1": ("mechanism", "rna_splicing"),
    "PS1": ("prior_variant",),
    "PS2": ("de_novo",),
    "PS3": ("functional",),
    "PS4": ("case_control", "case_series"),
    "PM1": ("region_hotspot",),
    "PM3": ("pm3", "recessive_allelic"),
    "PM4": ("protein_length_repeat",),
    "PM5": ("prior_variant",),
    "PM6": ("de_novo",),
    "PP1": ("segregation",),
    "PP2": ("mechanism",),
    "PP4": ("phenotype_specificity",),
    "BS2": ("healthy_observation",),
    "BS3": ("functional",),
    "BS4": ("segregation",),
    "BP1": ("mechanism",),
    "BP2": ("allelic_phase",),
    "BP3": ("protein_length_repeat",),
    "BP5": ("alternative_cause",),
}

_REQUIRED_CONTEXT: dict[str, tuple[str, ...]] = {
    "PVS1": ("gene", "transcript"),
    "PS1": ("gene", "transcript"),
    "PS2": ("gene", "disease", "inheritance"),
    "PS4": ("gene", "disease"),
    "PM1": ("gene", "disease", "transcript"),
    "PM3": ("gene", "inheritance"),
    "PM4": ("gene", "transcript"),
    "PM5": ("gene", "transcript"),
    "PM6": ("gene", "disease", "inheritance"),
    "PP1": ("gene", "disease", "inheritance"),
    "PP2": ("gene", "disease"),
    "PP4": ("gene", "disease", "inheritance"),
    "BA1": ("gene", "disease"),
    "BS1": ("gene", "disease"),
    "BS2": ("gene", "disease", "inheritance"),
    "BS4": ("gene", "disease", "inheritance"),
    "BP1": ("gene", "disease"),
    "BP2": ("gene", "inheritance"),
    "BP3": ("gene", "transcript"),
    "BP5": ("gene", "disease"),
}


CANDIDATE_POLICY_ID = "tooluniverse-acmg-source-backed-candidates"
CANDIDATE_POLICY_VERSION = "2026-08-08-v3"
VERIFIED_POLICY_ID = "tooluniverse-acmg-verified-evidence"
VERIFIED_POLICY_VERSION = "2026-08-08-v3"

_DEFAULT_CANDIDATE_STRENGTHS: dict[str, str] = {
    "PVS1": "PVS1",
    **{criterion: criterion for criterion in ("PS1", "PS2", "PS3", "PS4")},
    **{
        criterion: criterion for criterion in ("PM1", "PM2", "PM3", "PM4", "PM5", "PM6")
    },
    **{criterion: criterion for criterion in ("PP1", "PP2", "PP3", "PP4")},
    "BA1": "BA1",
    **{criterion: criterion for criterion in ("BS1", "BS2", "BS3", "BS4")},
    **{
        criterion: criterion for criterion in ("BP1", "BP2", "BP3", "BP4", "BP5", "BP7")
    },
}

# Criteria with a dedicated core definition cannot be created merely because a
# source mentions the criterion. Their normal calculators must first establish
# the minimum scientific facts. PP5/BP6 remain deprecated.
_SPECIAL_CORE_CRITERIA = frozenset({"PVS1", "PS3", "BS3", "BA1", "PP3", "BP4", "BP7"})

_CORRELATION_KEYS: dict[str, tuple[str, ...]] = {
    "PS1": ("prior_variant_id", "protein_residue"),
    "PM5": ("prior_variant_id", "protein_residue"),
    "PS2": ("proband_id", "family_id"),
    "PM6": ("proband_id", "family_id"),
    "PS3": ("assay_instance_id", "experiment_id"),
    "BS3": ("assay_instance_id", "experiment_id"),
    "PS4": ("case_id", "cohort_id"),
    "PM3": ("proband_id", "family_id", "second_allele_id"),
    "PP1": ("family_id", "meiosis_id"),
    "BS4": ("family_id", "meiosis_id"),
    "PP4": ("case_id", "family_id"),
    "BS2": ("individual_id", "cohort_id"),
    "BP2": ("case_id", "family_id", "cooccurring_variant_id"),
    "BP5": ("case_id", "alternative_cause_id"),
}

_MUTUALLY_EXCLUSIVE_CRITERIA: dict[str, tuple[str, ...]] = {
    "PP3": ("BP4",),
    "BP4": ("PP3",),
    "PS3": ("BS3",),
    "BS3": ("PS3",),
    "PP1": ("BS4",),
    "BS4": ("PP1",),
}

_HARD_EXCLUSIONS = (
    "allele_identity_conflict",
    "gene_identity_conflict",
    "build_identity_conflict",
    "transcript_identity_conflict_when_required",
    "semantic_contradiction",
    "illegal_criterion_strength_direction",
    "missing_traceable_source",
    "confirmed_duplicate_or_hard_conflict",
    "cspec_not_applicable",
    "deprecated_criterion",
)


def _criterion_direction(criterion: str) -> str:
    normalized = str(criterion or "").split("/", 1)[0].upper()
    return "benign" if normalized.startswith("B") else "pathogenic"


def strength_level_for(criterion: str, strength: str) -> str:
    """Return the standard evidence-strength level represented by one code."""
    normalized_criterion = str(criterion or "").split("/", 1)[0].upper()
    normalized_strength = str(strength or "").strip()
    for suffix, level in (
        ("_VeryStrong", "VeryStrong"),
        ("_Strong", "Strong"),
        ("_Moderate", "Moderate"),
        ("_Supporting", "Supporting"),
    ):
        if normalized_strength.endswith(suffix):
            return level
    if normalized_strength == "BA1":
        return "StandAlone"
    if normalized_strength != normalized_criterion:
        return ""
    if normalized_criterion == "PVS1":
        return "VeryStrong"
    for prefix in ("PS", "PM", "PP", "BS", "BP"):
        if normalized_criterion.startswith(prefix):
            return _DEFAULT_STRENGTH_LEVELS[prefix]
    return ""


def generic_bayesian_odds_for(criterion: str, strength: str) -> float | None:
    """Map a user/review proposal onto generic Tavtigian strength odds."""
    level = strength_level_for(criterion, strength)
    if not level or level == "StandAlone":
        return None
    return _GENERIC_TAVTIGIAN_ODDS.get((_criterion_direction(criterion), level))


def is_valid_strength_for_criterion(criterion: str, strength: str) -> bool:
    """Validate direction and standard strength syntax for review decisions."""
    normalized_criterion = str(criterion or "").split("/", 1)[0].upper()
    normalized_strength = str(strength or "").strip()
    if normalized_criterion not in ACMG_CRITERIA or not normalized_strength:
        return False
    strength_criterion = normalized_strength.split("_", 1)[0].upper()
    if strength_criterion != normalized_criterion:
        return False
    return bool(
        strength_level_for(normalized_criterion, normalized_strength)
        and (
            generic_bayesian_odds_for(normalized_criterion, normalized_strength)
            is not None
            or normalized_criterion == "BA1"
        )
    )


def criterion_use_matrix() -> dict[str, dict[str, Any]]:
    """Return the single v3 evidence contract for all 28 criteria."""
    matrix: dict[str, dict[str, Any]] = {}
    directional_conflicts = {
        "PP3": ["BP4"],
        "BP4": ["PP3"],
        "PS3": ["BS3"],
        "BS3": ["PS3"],
    }
    for criterion in ACMG_CRITERIA:
        rule = rule_for_criterion(criterion)
        if criterion in _DEPRECATED_CRITERIA:
            automation_level = "deprecated"
        elif criterion in _DISEASE_SPECIFIC_CRITERIA:
            automation_level = "disease_specific"
        elif criterion in _DETERMINISTIC_GENERAL_CRITERIA:
            automation_level = "versioned_deterministic"
        else:
            automation_level = "review_guided"
        matrix[criterion] = {
            "criterion": criterion,
            "direction": _criterion_direction(criterion),
            "default_strength": strength_level_for(criterion, criterion),
            "automation_level": automation_level,
            "required_facts": list(rule.get("required_inputs") or []),
            "rule_id": str(rule.get("rule_id") or ""),
            "rule_version": str(rule.get("version") or ""),
            "primary_reference": str(rule.get("primary_reference") or ""),
            "consequence_policy": consequence_policy_for(criterion),
            "conflict_relations": directional_conflicts.get(criterion, []),
            "bayesian_direction": _criterion_direction(criterion),
            "final_adoption": "user_decision",
            "provider_routes": list(_PROVIDER_ROUTES.get(criterion, ())),
            "literature_fact_types": list(_LITERATURE_FACT_TYPES.get(criterion, ())),
            "required_context": list(_REQUIRED_CONTEXT.get(criterion, ())),
            "minimum_candidate_facts": list(rule.get("required_inputs") or []),
            "strict_validation_facts": list(rule.get("required_inputs") or []),
            "default_candidate_strength": _DEFAULT_CANDIDATE_STRENGTHS.get(
                criterion, ""
            ),
            "default_candidate_allowed": criterion
            not in _SPECIAL_CORE_CRITERIA | _DEPRECATED_CRITERIA,
            "special_core_definition_required": criterion in _SPECIAL_CORE_CRITERIA,
            "candidate_policy": {
                "policy_id": CANDIDATE_POLICY_ID,
                "version": CANDIDATE_POLICY_VERSION,
                "scope": "source-backed candidate; not a ClinGen deterministic rule",
            },
            "verified_policy": {
                "policy_id": VERIFIED_POLICY_ID,
                "version": VERIFIED_POLICY_VERSION,
            },
            "rule_priority": [
                "exact_released_vcep_assertion",
                "exact_released_cspec",
                "versioned_clingen_svi",
                "generic_acmg_candidate",
            ],
            "hard_exclusions": list(_HARD_EXCLUSIONS),
            "correlation_keys": list(_CORRELATION_KEYS.get(criterion, ())),
            "mutually_exclusive_with": list(
                _MUTUALLY_EXCLUSIVE_CRITERIA.get(criterion, ())
            ),
            "scenario_isolation_required": True,
        }
    return matrix


_COMPOUND = {
    "PP3/BP4": "PP3",
    "BP4": "PP3",
    "PS2/PM6": "PS2",
    "PS3/BS3": "PS3",
}


def rule_for_criterion(criterion: str) -> dict[str, Any]:
    return RULE_CATALOG.get(_COMPOUND.get(criterion, criterion), {})


def consequence_policy_for(criterion: str) -> dict[str, Any]:
    normalized = _COMPOUND.get(str(criterion), str(criterion))
    return CONSEQUENCE_POLICIES.get(normalized, {"mode": "requires_context"})


def rule_for_output(
    criterion: str,
    *,
    rule_id: str = "",
    rule_version: str = "",
) -> dict[str, Any]:
    """Resolve the exact versioned rule that produced one card."""
    candidates: list[tuple[set[str], dict[str, Any]]] = []
    for catalog_criterion, rule in RULE_CATALOG.items():
        shared = str(rule.get("shared_decision_spec") or "")
        candidates.append(({catalog_criterion}, RULE_CATALOG.get(shared, rule)))
    candidates.append(
        (set(SPLICEAI_RULE.get("applicable_criteria") or ()), SPLICEAI_RULE)
    )
    for contract in CSPEC_RULE_CATALOG.values():
        applicable = set(contract.get("applicable_criteria") or ())
        applicable.update(str(value) for value in contract.get("criteria", {}))
        candidates.append((applicable, contract))
    if rule_id or rule_version:
        return next(
            (
                rule
                for applicable, rule in candidates
                if str(rule.get("rule_id") or "") == str(rule_id)
                and str(rule.get("version") or "") == str(rule_version)
                and criterion in applicable
            ),
            {},
        )
    return rule_for_criterion(criterion)


def rule_allows_verified_strength(
    criterion: str,
    strength: str,
    *,
    rule_id: str = "",
    rule_version: str = "",
) -> bool:
    """Return whether a card exactly matches an active versioned rule output."""
    rule = rule_for_output(
        criterion,
        rule_id=rule_id,
        rule_version=rule_version,
    )
    return bool(
        rule
        and rule_id == str(rule["rule_id"])
        and rule_version == str(rule["version"])
        and strength in set(rule.get("countable_strengths", ()))
    )


def bayesian_odds_for_output(
    criterion: str,
    strength: str,
    *,
    rule_id: str,
    rule_version: str,
) -> float | None:
    """Return odds only from the exact executable rule that produced a card."""
    rule = rule_for_output(
        criterion,
        rule_id=rule_id,
        rule_version=rule_version,
    )
    if not rule or strength not in set(rule.get("countable_strengths", ())):
        return None
    value = rule.get("bayesian_odds", {}).get(strength)
    return float(value) if value is not None else None


__all__ = [
    "ACMG_CRITERIA",
    "CANDIDATE_POLICY_ID",
    "CANDIDATE_POLICY_VERSION",
    "CSPEC_RULE_CATALOG",
    "CONSEQUENCE_POLICIES",
    "IDENTITY_PROVIDER_ROLES",
    "IDENTITY_VERIFICATION_POLICY",
    "RULE_CATALOG",
    "SPLICEAI_RULE",
    "bayesian_odds_for_output",
    "criterion_use_matrix",
    "consequence_policy_for",
    "generic_bayesian_odds_for",
    "is_valid_strength_for_criterion",
    "rule_allows_verified_strength",
    "rule_for_criterion",
    "rule_for_output",
    "strength_level_for",
    "VERIFIED_POLICY_ID",
    "VERIFIED_POLICY_VERSION",
]
