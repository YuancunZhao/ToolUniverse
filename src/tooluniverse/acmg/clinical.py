"""Clinical evidence rules with fail-closed ClinGen point systems.

PS2/PM6 and PM3 consume structured proband observations. PP1 remains
not-assessed until a family-level segregation likelihood model is available.
PP5/BP6 are deprecated and never count.
"""

from __future__ import annotations

from .models import EvidenceCard
from .rule_catalog import rule_for_criterion


_DE_NOVO_POINTS = {
    "highly_specific": {"confirmed": 2.0, "assumed": 1.0},
    "consistent": {"confirmed": 1.0, "assumed": 0.5},
    "consistent_high_heterogeneity": {"confirmed": 0.5, "assumed": 0.25},
    "not_consistent": {"confirmed": 0.0, "assumed": 0.0},
}


def _de_novo_evidence(
    probands: list[dict],
    *,
    inheritance_mode: str,
) -> EvidenceCard:
    if any(not isinstance(proband, dict) for proband in probands):
        return EvidenceCard(
            criterion="PS2/PM6",
            strength="not_assessed",
            input_source="Structured de novo probands",
            input_values={"proband_count": len(probands)},
            clinvar_rule_applied="ClinGen SVI De Novo Recommendation v1.1",
            provenance_chain=["PS2/PM6: every proband record must be an object"],
        )
    if not inheritance_mode:
        return EvidenceCard(
            criterion="PS2/PM6",
            strength="not_assessed",
            input_source="Structured de novo probands",
            input_values={"proband_count": len(probands)},
            clinvar_rule_applied="ClinGen SVI De Novo Recommendation v1.1",
            provenance_chain=["PS2/PM6: inheritance mode is required"],
        )

    total = 0.0
    relationship_states: set[str] = set()
    high_heterogeneity_points = 0.0
    case_ids: list[str] = []
    for proband in probands:
        relationship = str(proband.get("parental_relationships") or "").lower()
        phenotype = str(proband.get("phenotype_consistency") or "").lower()
        case_id = str(proband.get("case_id") or "")
        if (
            relationship not in {"confirmed", "assumed"}
            or phenotype not in _DE_NOVO_POINTS
        ):
            return EvidenceCard(
                criterion="PS2/PM6",
                strength="not_assessed",
                input_source="Structured de novo probands",
                input_values={"invalid_proband": proband},
                clinvar_rule_applied="ClinGen SVI De Novo Recommendation v1.1",
                provenance_chain=[
                    "PS2/PM6: each proband requires parental_relationships "
                    "and a recognized phenotype_consistency category"
                ],
            )
        if not case_id or case_id in case_ids:
            return EvidenceCard(
                criterion="PS2/PM6",
                strength="not_assessed",
                input_source="Structured de novo probands",
                input_values={"case_id": case_id},
                clinvar_rule_applied="ClinGen SVI De Novo Recommendation v1.1",
                provenance_chain=["PS2/PM6: unique non-empty case IDs are required"],
            )
        case_ids.append(case_id)
        relationship_states.add(relationship)
        points = _DE_NOVO_POINTS[phenotype][relationship]
        if phenotype == "consistent_high_heterogeneity":
            allowed = max(0.0, 1.0 - high_heterogeneity_points)
            points = min(points, allowed)
            high_heterogeneity_points += points
        total += points

    if total <= 0 or len(relationship_states) != 1:
        reason = (
            "mixed confirmed and assumed parental relationships require explicit "
            "curator resolution"
            if len(relationship_states) > 1
            else "no de novo points were awarded"
        )
        return EvidenceCard(
            criterion="PS2/PM6",
            strength="not_assessed",
            input_source="Structured de novo probands",
            input_values={"total_points": total},
            clinvar_rule_applied="ClinGen SVI De Novo Recommendation v1.1",
            provenance_chain=[f"PS2/PM6: {reason}"],
            source_case_ids=case_ids,
        )

    levels = [
        (4.0, "VeryStrong"),
        (2.0, "Strong"),
        (1.0, "Moderate"),
        (0.5, "Supporting"),
    ]
    level_index = next(
        index for index, (minimum, _) in enumerate(levels) if total >= minimum
    )
    if "recessive" in inheritance_mode.lower() and not all(
        proband.get("second_variant_pathogenic") is True for proband in probands
    ):
        level_index = min(level_index + 1, len(levels) - 1)
    level = levels[level_index][1]
    confirmed = relationship_states == {"confirmed"}
    criterion = "PS2" if confirmed else "PM6"
    strength_map = {
        ("PS2", "VeryStrong"): "PS2_VeryStrong",
        ("PS2", "Strong"): "PS2",
        ("PS2", "Moderate"): "PS2_Moderate",
        ("PS2", "Supporting"): "PS2_Supporting",
        ("PM6", "VeryStrong"): "PM6_VeryStrong",
        ("PM6", "Strong"): "PM6_Strong",
        ("PM6", "Moderate"): "PM6",
        ("PM6", "Supporting"): "PM6_Supporting",
    }
    return EvidenceCard(
        criterion=criterion,
        strength=strength_map[(criterion, level)],
        input_source="Structured de novo probands",
        input_values={"total_points": total, "proband_count": len(probands)},
        clinvar_rule_applied="ClinGen SVI De Novo Recommendation v1.1, Tables 1-2",
        provenance_chain=[f"{criterion}: {total:g} de novo points -> {level} evidence"],
        source_case_ids=case_ids,
    )


def _pm3_evidence(
    observations: list[dict],
    *,
    inheritance_mode: str,
    frequency_eligible: bool,
) -> EvidenceCard:
    rule = "ClinGen SVI PM3 Recommendation v1.0, Tables 1-2"
    if "recessive" not in inheritance_mode.lower() or frequency_eligible is not True:
        return EvidenceCard(
            criterion="PM3",
            strength="not_assessed",
            input_source="Structured PM3 probands",
            input_values={
                "inheritance_mode": inheritance_mode,
                "frequency_eligible": frequency_eligible,
            },
            clinvar_rule_applied=rule,
            provenance_chain=[
                "PM3: recessive inheritance and PM2-eligible frequencies for "
                "both alleles are required"
            ],
        )

    total = 0.0
    homozygous_total = 0.0
    consanguineous_or_vus_total = 0.0
    case_ids: list[str] = []
    if any(not isinstance(observation, dict) for observation in observations):
        return EvidenceCard(
            criterion="PM3",
            strength="not_assessed",
            input_source="Structured PM3 probands",
            input_values={"proband_count": len(observations)},
            clinvar_rule_applied=rule,
            provenance_chain=["PM3: every proband record must be an object"],
        )
    for observation in observations:
        case_id = str(observation.get("case_id") or "")
        if not case_id or case_id in case_ids:
            return EvidenceCard(
                criterion="PM3",
                strength="not_assessed",
                input_source="Structured PM3 probands",
                input_values={"case_id": case_id},
                clinvar_rule_applied=rule,
                provenance_chain=["PM3: unique non-empty case IDs are required"],
            )
        if observation.get("other_variant_frequency_eligible") is not True:
            return EvidenceCard(
                criterion="PM3",
                strength="not_assessed",
                input_source="Structured PM3 probands",
                input_values={"case_id": case_id},
                clinvar_rule_applied=rule,
                provenance_chain=[
                    "PM3: the variant on the other allele must also meet the "
                    "frequency requirement"
                ],
            )
        case_ids.append(case_id)
        zygosity = str(observation.get("zygosity") or "").lower()
        other_class = str(observation.get("other_variant_classification") or "").upper()
        phase = str(observation.get("phase") or "").lower()
        consanguineous = observation.get("consanguineous") is True

        if zygosity == "homozygous":
            points = 0.25 if consanguineous else 0.5
            if consanguineous:
                allowed = max(0.0, 0.5 - consanguineous_or_vus_total)
                points = min(points, allowed)
                consanguineous_or_vus_total += points
            else:
                allowed = max(0.0, 1.0 - homozygous_total)
                points = min(points, allowed)
                homozygous_total += points
        elif zygosity == "compound_heterozygous":
            if other_class in {"PATHOGENIC", "P"}:
                points = 1.0 if phase == "confirmed_in_trans" else 0.5
            elif other_class in {"LIKELY_PATHOGENIC", "LP"}:
                points = 1.0 if phase == "confirmed_in_trans" else 0.25
            elif other_class in {"VUS", "UNCERTAIN_SIGNIFICANCE"}:
                points = 0.25 if phase == "confirmed_in_trans" else 0.0
                allowed = max(0.0, 0.5 - consanguineous_or_vus_total)
                points = min(points, allowed)
                consanguineous_or_vus_total += points
            else:
                points = -1.0
            if phase not in {"confirmed_in_trans", "unknown"}:
                points = -1.0
        else:
            points = -1.0

        if points < 0:
            return EvidenceCard(
                criterion="PM3",
                strength="not_assessed",
                input_source="Structured PM3 probands",
                input_values={"invalid_observation": observation},
                clinvar_rule_applied=rule,
                provenance_chain=[
                    "PM3: unsupported zygosity, phase, or other-allele classification"
                ],
                source_case_ids=case_ids,
            )
        total += points

    thresholds = rule_for_criterion("PM3")["point_thresholds"]
    if total >= thresholds["very_strong"]:
        strength = "PM3_VeryStrong"
    elif total >= thresholds["strong"]:
        strength = "PM3_Strong"
    elif total >= thresholds["moderate"]:
        strength = "PM3"
    elif total >= thresholds["supporting"]:
        strength = "PM3_Supporting"
    else:
        strength = "not_assessed"
    return EvidenceCard(
        criterion="PM3",
        strength=strength,
        input_source="Structured PM3 probands",
        input_values={"total_points": total, "proband_count": len(observations)},
        clinvar_rule_applied=rule,
        provenance_chain=[f"PM3: {total:g} points -> {strength}"],
        source_case_ids=case_ids,
    )


def clinical_evidence(
    inheritance_mode: str = "",
    de_novo_probands: list[dict] | None = None,
    pm3_observations: list[dict] | None = None,
    pm3_frequency_eligible: bool = False,
) -> list[EvidenceCard]:
    inheritance_mode = str(inheritance_mode or "")
    de_novo_items = de_novo_probands if isinstance(de_novo_probands, list) else []
    pm3_items = pm3_observations if isinstance(pm3_observations, list) else []
    cards: list[EvidenceCard] = []

    # PS2/PM6: only structured, independently identified probands enter preview.
    if de_novo_items:
        cards.append(
            _de_novo_evidence(
                de_novo_items,
                inheritance_mode=inheritance_mode,
            )
        )
    else:
        cards.append(
            EvidenceCard(
                criterion="PS2/PM6",
                strength="not_assessed",
                input_source="Clinical report",
                input_values={},
                clinvar_rule_applied="ClinGen SVI De Novo Recommendation v1.1",
                provenance_chain=[
                    "PS2/PM6: structured de_novo_probands are required"
                ],
            )
        )

    # Segregation and phenotype routes are deliberately not automated here.
    cards.append(
        EvidenceCard(
            criterion="PP1",
            strength="not_assessed",
            input_source="Family study",
            input_values={"inheritance_mode": inheritance_mode},
            clinvar_rule_applied="ClinGen PP1/BS4 segregation guidance",
            provenance_chain=[
                "PP1: family-level affected/unaffected genotypes and a segregation "
                "likelihood model are required"
            ],
        )
    )

    cards.append(
        EvidenceCard(
            criterion="PP4",
            strength="not_assessed",
            input_source="Phenotype and disease context",
            input_values={"inheritance_mode": inheritance_mode},
            clinvar_rule_applied="ACMG/AMP 2015; disease-specific contract required",
            provenance_chain=[
                "PP4: disease-specific phenotype, inheritance, penetrance, and VCEP policy facts are required"
            ],
        )
    )

    # PP5/BP6 are deprecated by ClinGen SVI.
    cards.append(
        EvidenceCard(
            criterion="PP5",
            strength="deprecated",
            input_source="ClinVar",
            input_values={},
            clinvar_rule_applied="ClinGen SVI (PP5/BP6 deprecated)",
            provenance_chain=["PP5: ClinGen SVI deprecates PP5/BP6"],
        )
    )
    cards.append(
        EvidenceCard(
            criterion="BP6",
            strength="deprecated",
            input_source="ClinVar",
            input_values={},
            clinvar_rule_applied="ClinGen SVI (PP5/BP6 deprecated)",
            provenance_chain=["BP6: ClinGen SVI deprecates PP5/BP6 -> deprecated"],
        )
    )

    if pm3_items:
        cards.append(
            _pm3_evidence(
                pm3_items,
                inheritance_mode=inheritance_mode,
                frequency_eligible=pm3_frequency_eligible,
            )
        )
    else:
        cards.append(
            EvidenceCard(
                criterion="PM3",
                strength="not_assessed",
                input_source="Genetic testing",
                input_values={
                    "inheritance_mode": inheritance_mode,
                },
                clinvar_rule_applied="ClinGen SVI PM3 Recommendation v1.0",
                provenance_chain=[
                    "PM3: structured proband observations and point accumulation "
                    "are required"
                ],
            )
        )

    return cards


__all__ = ["clinical_evidence"]
