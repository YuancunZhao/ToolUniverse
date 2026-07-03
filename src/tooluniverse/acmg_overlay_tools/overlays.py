"""Overlay tool stubs: functional_assay, case_enrichment, segregation,
   de_novo, pm3_in_trans, protein_length, source_review, pvs1_lof,
   pvs1_splicing, ps1_splicing, pm1_bp1.
Each stub returns not_assessed with a recommendation to collect evidence.
"""

from __future__ import annotations
from typing import Any
from .base import output_template, vcep_deferred_template


def overlay_functional_assay(
    functional_evidence: str = "",
    assay_type: str = "",
    assay_category: str = "",
    assay_applicable_to_disease_mechanism: bool = False,
    variant_specific: bool = False,
    replicated: bool = False,
    has_controls: bool = False,
    statistically_significant: bool = False,
    effect_direction: str = "",
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PS3/BS3 per ClinGen SVI functional assay classification (Brnich 2019, PMID:31892348).

    ClinGen defines 5 levels of functional assay validation:
        Level 1: Validated - gene/variant-specific, replicated, controlled, statistically significant
        Level 2: Well-established - gene-specific, replicated, controlled
        Level 3: Emerging - gene-specific, has controls, may not be replicated
        Level 4: Supportive - variant-specific but not gene-level validated
        Level 5: Non-validated - not meeting above criteria

    LLM input: from full text of published functional studies (Methods/Results sections).
    """
    if vcep_override:
        return vcep_deferred_template(
            "PS3/BS3",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if not functional_evidence:
        return output_template("PS3/BS3", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No functional assay evidence provided.",
            next_action="Search PubMed (full text) for functional studies of this variant using "
                         "the variant HGVS, rsID, or protein change as query terms.")
    if not variant_specific:
        return output_template("PS3/BS3", "not_applicable",
            status="not_assessed", route_outcome="overlay_not_assessed",
            reason="Functional evidence is gene-level, not variant-specific. PS3/BS3 requires "
                   "variant-specific functional data.",
            next_action="Search for functional studies specifically testing this variant "
                         "(not general gene function).")

    # Determine assay level per Brnich 2019 Table 1
    if replicated and has_controls and statistically_significant:
        level = 1  # Validated
    elif has_controls and statistically_significant:
        level = 2  # Well-established (controls + stats, may not be independently replicated)
    elif has_controls:
        level = 3  # Emerging (has controls, no statistical validation or not replicated)
    elif variant_specific:
        level = 4  # Supportive (variant-specific but minimal validation)
    else:
        level = 5  # Non-validated

    # Determine strength based on level and effect direction
    is_lof = "loss" in effect_direction.lower() or "lof" in effect_direction.lower()
    is_gof = "gain" in effect_direction.lower() or "gof" in effect_direction.lower()
    is_no_effect = "no" in effect_direction.lower() or "normal" in effect_direction.lower() or "wt" in effect_direction.lower()

    if level == 1:
        if is_no_effect:
            return output_template("BS3", "BS3",
                reason=f"Level 1 validated assay ({assay_type}) shows no functional effect. BS3 applies.",
                source_of_truth="PubMed functional study")
        return output_template("PS3", "PS3",
            reason=f"Level 1 validated assay ({assay_type}) shows {effect_direction}. PS3 applies.",
            source_of_truth="PubMed functional study")
    elif level == 2:
        if is_no_effect:
            return output_template("BS3", "BS3_Supporting",
                reason=f"Level 2 well-established assay ({assay_type}) shows no effect. BS3_Supporting.",
                source_of_truth="PubMed functional study")
        return output_template("PS3", "PS3_Moderate",
            reason=f"Level 2 well-established assay ({assay_type}) shows {effect_direction}. PS3_Moderate.",
            source_of_truth="PubMed functional study")
    elif level == 3:
        return output_template("PS3", "PS3_Supporting",
            reason=f"Level 3 emerging assay ({assay_type}) shows {effect_direction}. PS3_Supporting.",
            source_of_truth="PubMed functional study")
    elif level == 4:
        return output_template("PS3", "PS3_Supporting",
            reason=f"Level 4 supportive assay ({assay_type}) shows {effect_direction}. "
                   "PS3_Supporting. Not replicated — consider independent verification.",
            source_of_truth="PubMed functional study")
    else:
        return output_template("PS3/BS3", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason=f"Level 5 non-validated assay ({assay_type}). Cannot assign PS3/BS3. "
                   "Needs: replication, controls, or statistical validation.",
            source_of_truth="PubMed functional study")


def overlay_case_enrichment(
    case_count: int = 0,
    control_count: int = 0,
    case_af: float = 0.0,
    control_af: float = 0.0,
    odds_ratio: float | None = None,
    confidence_interval_lower: float | None = None,
    phenotype_consistent: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PS4 per ClinGen SVI case enrichment recommendation.

    LLM input: from full text of case-control/cohort studies (Results/Tables).
    OR > 5 + CI excluding 1.0 → PS4_Strong, OR > 2 → PS4, OR > 1.5 → PS4_Supporting.
    """
    if vcep_override:
        return vcep_deferred_template(
            "PS4",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if case_count == 0:
        return output_template("PS4", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No case enrichment data provided.",
            next_action="Search PubMed full text for case-control studies.")
    if not phenotype_consistent:
        return output_template("PS4", "not_met", status="not_applicable",
            route_outcome="overlay_not_applicable",
            reason="Reported case phenotypes not consistent with patient.")
    if odds_ratio is not None and control_count > 0:
        ci_excludes_1 = confidence_interval_lower is not None and confidence_interval_lower > 1.0
        if odds_ratio >= 5.0 and ci_excludes_1:
            return output_template("PS4", "PS4_Strong",
                reason=f"OR={odds_ratio:.1f} (CI>{confidence_interval_lower:.1f}), {case_count}c/{control_count}ctrl. PS4_Strong.",
                source_of_truth="PubMed case-control")
        if odds_ratio >= 2.0 and ci_excludes_1:
            return output_template("PS4", "PS4",
                reason=f"OR={odds_ratio:.1f} (CI>{confidence_interval_lower:.1f}), {case_count}c/{control_count}ctrl. PS4.",
                source_of_truth="PubMed case-control")
        if odds_ratio >= 1.5:
            return output_template("PS4", "PS4_Supporting",
                reason=f"OR={odds_ratio:.1f}, {case_count}c/{control_count}ctrl. PS4_Supporting.",
                source_of_truth="PubMed case-control")
    if case_count >= 5:
        return output_template("PS4", "PS4_Supporting",
            reason=f"{case_count} unrelated cases without controls. PS4_Supporting (≥5 per ClinGen).",
            source_of_truth="PubMed case series")
    return output_template("PS4", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"Only {case_count} case(s), insufficient for PS4.")


def overlay_segregation(
    segregation_present: bool = False,
    affected_meioses: int = 0,
    total_meioses: int = 0,
    phenotype_highly_specific: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PP1/BS4/PP4 per ClinGen SVI segregation recommendation (Jarvik 2015, PMID:25631863).

    Scoring is based on meioses (meiotic events), not raw affected count:
        PP1_Strong: ≥7 meioses observed + phenotype specific
        PP1_Moderate: 5-6 meioses
        PP1: 3-4 meioses
        PP1_Supporting: 1-2 meioses

    LLM input: from full text of family/segregation studies (pedigree/methods).
    """
    if vcep_override:
        return vcep_deferred_template(
            "PP1/BS4",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if not segregation_present:
        return output_template("PP1/BS4", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No segregation data provided.",
            next_action="Obtain family segregation data (meioses count from pedigree).")
    if affected_meioses >= 7 and phenotype_highly_specific:
        return output_template("PP1", "PP1_Strong",
            reason=f"{affected_meioses} meioses observed + highly specific phenotype. PP1_Strong.",
            source_of_truth="Family study")
    if affected_meioses >= 5:
        return output_template("PP1", "PP1_Moderate",
            reason=f"{affected_meioses} meioses observed. PP1_Moderate.",
            source_of_truth="Family study")
    if affected_meioses >= 3:
        return output_template("PP1", "PP1",
            reason=f"{affected_meioses} meioses observed. PP1.",
            source_of_truth="Family study")
    if affected_meioses >= 1:
        return output_template("PP1", "PP1_Supporting",
            reason=f"{affected_meioses} meioses observed. PP1_Supporting.",
            source_of_truth="Family study")
    return output_template("PP1/BS4", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"{affected_meioses} meioses insufficient for PP1.")


def overlay_de_novo(
    de_novo_confirmed: bool = False,
    paternity_confirmed: bool = False,
    phenotype_highly_specific: bool = False,
    phenotype_consistent: bool = False,
    genetic_heterogeneity_low: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PS2/PM6 per SVI De Novo Criteria v1.1 (PMID:38103545).
    LLM input: from clinical report / published case literature.
    2pt=PS2, 1pt=PS2_Moderate, 0pt=PM6, not de novo=not_assessed.
    """
    if vcep_override:
        return vcep_deferred_template(
            "PS2/PM6",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if not de_novo_confirmed:
        return output_template("PS2/PM6", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No de novo evidence or variant is inherited.",
            next_action="Trio testing required.")
    if not paternity_confirmed:
        return output_template("PM6", "PM6",
            reason="De novo observed without confirmed parentage → PM6.",
            source_of_truth="Trio testing")
    pts = 2 if phenotype_highly_specific else (1 if phenotype_consistent else 0)
    if genetic_heterogeneity_low and pts > 0:
        pts = min(pts + 1, 2)
    if pts >= 2:
        return output_template("PS2", "PS2",
            reason=f"De novo + parentage confirmed, phenotype score {pts}/2 → PS2.",
            source_of_truth="Trio testing")
    if pts == 1:
        return output_template("PS2", "PS2_Moderate",
            reason=f"De novo + parentage confirmed, phenotype score {pts}/2 → PS2_Moderate.",
            source_of_truth="Trio testing")
    return output_template("PM6", "PM6",
        reason="De novo + parentage confirmed but phenotype insufficient → PM6.",
        source_of_truth="Trio testing")
def overlay_pm3_in_trans(
    second_variant_pathogenic: bool = False,
    phase_confirmed: bool = False,

    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return vcep_deferred_template(
            "PM3",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if not second_variant_pathogenic:
        return output_template("PM3", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No second pathogenic variant in trans identified.",
            next_action="Test for second variant in recessive gene.")
    if phase_confirmed:
        return output_template("PM3", "PM3",
            reason="Second pathogenic variant confirmed in trans.",
            source_of_truth="Genetic testing")
    return output_template("PM3", "PM3_Supporting",
        reason="Second pathogenic variant identified. Phase not confirmed.",
        source_of_truth="Genetic testing")


def overlay_protein_length(
    variant_type: str = "",
    in_repeat_region: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return vcep_deferred_template(
            "PM4/BP3",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if variant_type in ("indel_inframe", "null"):
        return output_template("PM4", "PM4",
            reason=f"Protein length change due to {variant_type}.",
            source_of_truth="Variant annotation")
    return output_template("PM4/BP3", "not_met", status="not_applicable",
        route_outcome="overlay_not_applicable",
        reason="Variant does not change protein length.")


def overlay_source_review(
    clinvar_review_stars: int = 0,
    clinvar_pathogenic_submitters: int = 0,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return vcep_deferred_template(
            "PP5/BP6",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    # ClinGen SVI: PP5/BP6 are deprecated — use as leads to primary evidence
    return output_template("PP5/BP6", "not_counted",
        status="not_applicable",
        route_outcome="overlay_not_applicable",
        reason="ClinGen SVI recommends discontinuing PP5/BP6. "
               "Use ClinVar assertions as leads to retrieve primary evidence.",
        guidance_authority="ClinGen/SVI primary",
        next_action="Retrieve primary evidence supporting ClinVar classification.")


def overlay_pvs1_lof(
    variant_type: str = "",
    gene_lof_mechanism: bool = False,
    lof_intolerant: bool = False,
    nmd_predicted: bool | None = None,
    exon_position: str = "",
    truncated_region_percent: float = 100.0,
    region_criticality: str = "unknown",
    rescue_transcript: bool = False,
    spliceai_dl: float | None = None,
    ar_disease: bool = False,
    second_allele_found: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PVS1 strength per ClinGen SVI decision tree (Abou Tayoun 2018, PMID:30192042).

    Args:
        variant_type: null/frameshift/nonsense/splice/canonical_splice
        gene_lof_mechanism: LOF established as disease mechanism
        lof_intolerant: gnomAD pLI >= 0.9 or LOEUF < 0.35
        nmd_predicted: NMD predicted (None = unknown, use defaults)
        exon_position: last/penultimate/middle/first (for NMD prediction)
        truncated_region_percent: % of protein removed by truncation
        region_criticality: critical/important/unknown (for biologically relevant regions)
        rescue_transcript: rescue transcript or alternative initiation exists
        spliceai_dl: SpliceAI donor loss delta score (for splice variants)
        ar_disease: autosomal recessive disease
        second_allele_found: second pathogenic allele confirmed (for AR)
        vcep_override: VCEP-specific rule name
    """
    if vcep_override:
        return vcep_deferred_template(
            "PVS1",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )

    vt = variant_type.lower().strip()

    # === Table 1: Applicability Gate ===
    if vt not in ("null", "frameshift", "nonsense", "splice", "canonical_splice"):
        return output_template("PVS1", "not_met", status="not_applicable",
            route_outcome="overlay_not_applicable",
            reason=f"PVS1 requires null variant (nonsense/frameshift/canonical splice). Got: {vt}.")

    if not gene_lof_mechanism:
        return output_template("PVS1", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="Gene LOF mechanism not confirmed.",
            next_action="Check ClinGen gene-disease validity.")

    # === AR disease: single heterozygous null variant ===
    if ar_disease and not second_allele_found:
        return output_template("PVS1", "not_applicable_ar_heterozygous",
            status="not_assessed", route_outcome="overlay_not_assessed",
            reason="Autosomal recessive disease with single heterozygous null variant. "
                   "PVS1 requires biallelic status. Search for second pathogenic allele.",
            next_action="Sequence full gene for second allele; check CNV for deletion/duplication.")

    # === Splice variants: check SpliceAI before proceeding ===
    if vt in ("splice", "canonical_splice"):
        if spliceai_dl is not None and spliceai_dl < 0.2:
            return output_template("PVS1", "not_met", status="not_applicable",
                route_outcome="overlay_not_applicable",
                reason=f"SpliceAI donor loss={spliceai_dl:.2f} (<0.2). "
                       "Computational prediction does not support splice disruption. "
                       "RNA evidence recommended.",
                next_action="Perform RT-PCR/minigene assay to confirm splicing impact.")
        if nmd_predicted is False:
            return output_template("PVS1", "PVS1_Supporting",
                reason="Canonical splice variant but NMD not predicted. "
                       "Protein may retain partial function. "
                       "Per PVS1 decision tree: PTC not predicted to undergo NMD → downgrade.",
                source_of_truth="SpliceAI, VEP")
        if nmd_predicted is True:
            return output_template("PVS1", "PVS1",
                reason="Canonical splice variant predicted to cause NMD. "
                       "Full PVS1 strength applies.",
                source_of_truth="SpliceAI, VEP, NMD prediction")
        # NMD unknown — require explicit prediction, do not default to PVS1
        return output_template("PVS1", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="Canonical splice variant but NMD prediction unavailable. "
                   "PVS1 strength assignment requires NMD prediction. "
                   "Do NOT default to full PVS1 for canonical ±1,2 positions "
                   "without NMD confirmation.",
            source_of_truth="VEP, SpliceAI",
            next_action="Provide NMD prediction or RNA evidence before PVS1 assessment.")

    # === NMD Decision Branch ===
    if nmd_predicted is True:
        # NMD predicted → check exon location
        if exon_position == "last" or truncated_region_percent < 10:
            return output_template("PVS1", "PVS1_Moderate",
                reason=f"NMD predicted but PTC in last exon or truncation <10% ({truncated_region_percent:.1f}%). "
                       "Per PVS1 decision tree: downgrade to PVS1_Moderate.",
                source_of_truth="VEP, NMD prediction")

        if region_criticality == "critical" and truncated_region_percent >= 10:
            return output_template("PVS1", "PVS1",
                reason=f"NMD predicted. Truncation removes {truncated_region_percent:.0f}% "
                       "including a critical functional domain. PVS1 at full strength.",
                source_of_truth="VEP, InterPro")

        if rescue_transcript:
            return output_template("PVS1", "PVS1_Supporting",
                reason="NMD predicted but rescue transcript or alternative "
                       "initiation exists. Downgrade to PVS1_Supporting.",
                source_of_truth="literature, VEP")

        # NMD predicted, standard case
        return output_template("PVS1", "PVS1",
            reason="NMD predicted for null variant in LOF-mechanism gene. PVS1 applies.",
            source_of_truth="VEP, NMD prediction, ClinGen")

    elif nmd_predicted is False:
        # NMD not predicted → truncated/altered region assessment
        if truncated_region_percent >= 10:
            if region_criticality == "critical":
                return output_template("PVS1", "PVS1_Strong",
                    reason=f"NMD not predicted but truncation removes {truncated_region_percent:.0f}% "
                           "including critical domain. PVS1_Strong per decision tree.",
                    source_of_truth="VEP, InterPro")
            else:
                return output_template("PVS1", "PVS1_Moderate",
                    reason=f"NMD not predicted. Truncation removes {truncated_region_percent:.0f}% "
                           "but region criticality unknown. PVS1_Moderate per decision tree.",
                    source_of_truth="VEP")
        else:
            return output_template("PVS1", "PVS1_Supporting",
                reason=f"NMD not predicted and truncation <10% ({truncated_region_percent:.1f}%). "
                       "PVS1_Supporting per decision tree.",
                source_of_truth="VEP")

    # NMD unknown — require explicit prediction
    return output_template("PVS1", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"Null variant ({vt}) in LOF-mechanism gene but NMD prediction unavailable. "
               "PVS1 strength assignment requires NMD prediction. "
               "Do NOT default to PVS1 without confirming NMD.",
        source_of_truth="ClinGen, gnomAD constraint",
        next_action="Provide NMD prediction (from VEP or manual assessment) before PVS1 assessment.")

    return output_template("PVS1", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"Insufficient data to complete PVS1 decision tree for {vt}.",
        next_action="Provide NMD prediction, exon position, and region information.")


def overlay_pvs1_splicing(
    spliceai_dl: float | None = None,
    spliceai_da: float | None = None,
    is_canonical_gt_ag: bool = False,
    rna_evidence: bool = False,
    nmd_predicted: bool | None = None,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PVS1 Splicing per Walker 2023 RNA/splicing refinement (PMID:36652601).

    Canonical ±1/2 splice sites with SpliceAI support can activate PVS1.
    Requires orthogonal validation (RNA evidence preferred).
    """
    if vcep_override:
        return vcep_deferred_template(
            "PVS1/BP7",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if not is_canonical_gt_ag:
        return output_template("PVS1/BP7", "not_met", status="not_applicable",
            route_outcome="overlay_not_applicable",
            reason="Not a canonical GT-AG splice site (±1/2). PVS1 splicing not applicable.")
    if spliceai_dl is not None and spliceai_dl >= 0.5:
        if rna_evidence:
            return output_template("PVS1", "PVS1",
                reason=f"Canonical splice, SpliceAI DL={spliceai_dl:.2f}(≥0.5) + RNA evidence. PVS1.",
                source_of_truth="SpliceAI, RNA study")
        return output_template("PVS1", "PVS1_Moderate",
            reason=f"Canonical splice, SpliceAI DL={spliceai_dl:.2f}(≥0.5). PVS1_Moderate (RNA evidence recommended).",
            source_of_truth="SpliceAI",
            next_action="Perform RT-PCR/minigene for RNA confirmation.")
    if spliceai_dl is not None and spliceai_dl < 0.2:
        return output_template("PVS1/BP7", "not_met", status="not_applicable",
            route_outcome="overlay_not_applicable",
            reason=f"SpliceAI DL={spliceai_dl:.2f} (<0.2). No splicing impact predicted.")
    if not spliceai_dl and not rna_evidence:
        return output_template("PVS1/BP7", "not_assessed", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No SpliceAI or RNA evidence for splice assessment.")
    return output_template("BP7", "BP7",
        reason=f"Splice prediction available. May support BP7 for synonymous variants.",
        source_of_truth="SpliceAI")


def overlay_ps1_splicing(
    same_splice_event_pathogenic: bool = False,
    same_donor_acceptor: bool = False,
    predicted_skipped_exon: bool = False,
    in_frame: bool | None = None,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """PS1 splicing similarity. Assesses whether predicted splicing event matches known pathogenic.

    Key elements: same donor/acceptor, same predicted skipped exon, reading frame concordance.
    """
    if vcep_override:
        return vcep_deferred_template(
            "PS1_splice",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if same_splice_event_pathogenic and same_donor_acceptor:
        return output_template("PS1", "PS1",
            reason="Same predicted splicing event + same donor/acceptor as known pathogenic. PS1.",
            source_of_truth="SpliceAI, literature")
    if same_splice_event_pathogenic:
        return output_template("PS1", "PS1_Supporting",
            reason="Same predicted splicing event as known pathogenic but donor/acceptor differs. PS1_Supporting.",
            source_of_truth="SpliceAI, literature")
    if not same_splice_event_pathogenic:
        return output_template("PS1_splice", "not_met", status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No evidence of same predicted splicing event as known pathogenic.",
            next_action="Compare SpliceAI predictions with known pathogenic splice variants in this gene.")
    return output_template("PS1_splice", "not_assessed", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason="Insufficient splicing comparison data.")


def overlay_pm1_bp1(
    in_functional_domain: bool = False,
    domain_has_pathogenic_enrichment: bool = False,
    gene_missense_mechanism: bool = False,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    if vcep_override:
        return vcep_deferred_template(
            "PM1/BP1",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )
    if in_functional_domain and domain_has_pathogenic_enrichment:
        return output_template("PM1", "PM1_Moderate",
            reason="Variant in functional domain with pathogenic missense enrichment.",
            source_of_truth="InterPro, ClinVar")
    # BP1: missense in LOF-only gene
    if not gene_missense_mechanism:
        return output_template("BP1", "BP1_Supporting",
            reason="Missense in gene where only LOF causes disease. BP1 applicable.",
            source_of_truth="ClinGen, gnomAD constraint")
    return output_template("PM1/BP1", "not_met", status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason="No domain or constraint evidence for PM1/BP1.")


__all__ = [
    "overlay_case_enrichment",
    "overlay_de_novo",
    "overlay_functional_assay",
    "overlay_pm1_bp1",
    "overlay_pm3_in_trans",
    "overlay_protein_length",
    "overlay_ps1_splicing",
    "overlay_pvs1_lof",
    "overlay_pvs1_splicing",
    "overlay_segregation",
    "overlay_source_review",
]
