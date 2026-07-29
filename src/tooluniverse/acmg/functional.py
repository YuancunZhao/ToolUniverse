"""Brnich-calibrated, document-backed PS3/BS3 evidence rules."""

from __future__ import annotations

import math
from typing import Any

from .consequence import consequence_applicability
from .models import EvidenceCard
from .pvs1 import assess_pvs1
from .rule_catalog import rule_for_criterion


_REQUIRED_TEXT = (
    "gene_disease_mechanism",
    "assay_scope",
    "assay_class",
    "assay_instance_id",
    "model_system",
    "readout_name",
    "readout_unit",
    "normal_threshold",
    "abnormal_threshold",
    "variant_result",
    "validation_control_provenance",
)
_REQUIRED_COUNTS = (
    "technical_replicates",
    "biological_replicates",
    "pathogenic_validation_controls",
    "benign_validation_controls",
)


def _not_assessed(reason: str, values: dict[str, Any]) -> EvidenceCard:
    return EvidenceCard(
        criterion="PS3/BS3",
        strength="not_assessed",
        input_source="Document-backed functional assay",
        input_values=values,
        clinvar_rule_applied="Brnich et al. 2019 OddsPath framework",
        provenance_chain=[reason],
        source_case_ids=[str(values.get("assay_instance_id") or "")],
    )


def _finite_positive(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number > 0 else None


def _positive_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _control_present(value: Any) -> bool:
    return (
        _positive_count(value)
        or isinstance(value, (list, tuple, set, dict))
        and bool(value)
    )


def _assay_errors(assay: dict[str, Any]) -> list[str]:
    errors = [
        f"missing:{key}"
        for key in _REQUIRED_TEXT
        if not str(assay.get(key) or "").strip()
    ]
    for key in _REQUIRED_COUNTS:
        if not _positive_count(assay.get(key)):
            errors.append(f"invalid_positive_integer:{key}")
    for key in ("positive_experimental_controls", "negative_experimental_controls"):
        if not _control_present(assay.get(key)):
            errors.append(f"missing:{key}")
    if assay.get("assay_effect_consistent") is not True:
        errors.append("assay_effect_not_mechanistically_consistent")
    if assay.get("disease_relevance") is not True:
        errors.append("model_not_disease_relevant")
    if _finite_positive(assay.get("dynamic_range")) is None:
        errors.append("invalid_dynamic_range")
    if assay.get("calibration_method") != "reported_odds_path":
        errors.append("reported_odds_path_calibration_required")
    if _finite_positive(assay.get("reported_odds_path")) is None:
        errors.append("invalid_reported_odds_path")
    if str(assay.get("direction") or "").strip().lower() not in {"damaging", "normal"}:
        errors.append("invalid_direction")
    if str(assay.get("assay_scope") or "").strip().lower() not in {
        "protein_or_cell_function",
        "direct_rna_splicing",
    }:
        errors.append("invalid_assay_scope")
    return errors


def _assess_assay(assay: dict[str, Any]) -> EvidenceCard:
    if str(assay.get("assay_scope") or "").strip().lower() == "direct_rna_splicing":
        return _not_assessed(
            "PS3/BS3: direct RNA-splicing readouts require the Walker RNA evidence route",
            dict(assay),
        )
    errors = _assay_errors(assay)
    if errors:
        return _not_assessed(
            "PS3/BS3: incomplete Brnich assay contract: " + ", ".join(errors),
            dict(assay),
        )
    odds_path = float(assay["reported_odds_path"])
    direction = str(assay["direction"]).strip().lower()
    thresholds = rule_for_criterion("PS3")["odds_path_thresholds"]
    if direction == "damaging" and odds_path > thresholds["pathogenic"]["strong"]:
        criterion, strength = "PS3", "PS3"
    elif direction == "damaging" and odds_path > thresholds["pathogenic"]["moderate"]:
        criterion, strength = "PS3", "PS3_Moderate"
    elif direction == "damaging" and odds_path > thresholds["pathogenic"]["supporting"]:
        criterion, strength = "PS3", "PS3_Supporting"
    elif direction == "normal" and odds_path < thresholds["benign"]["strong"]:
        criterion, strength = "BS3", "BS3"
    elif direction == "normal" and odds_path < thresholds["benign"]["moderate"]:
        criterion, strength = "BS3", "BS3_Moderate"
    elif direction == "normal" and odds_path < thresholds["benign"]["supporting"]:
        criterion, strength = "BS3", "BS3_Supporting"
    else:
        return EvidenceCard(
            criterion="PS3/BS3",
            strength="not_met",
            input_source="Document-backed functional assay",
            input_values=dict(assay),
            clinvar_rule_applied="Brnich et al. 2019 OddsPath framework",
            provenance_chain=[
                f"PS3/BS3: reported OddsPath={odds_path:g} does not cross a calibrated boundary"
            ],
            source_case_ids=[str(assay["assay_instance_id"])],
        )
    return EvidenceCard(
        criterion=criterion,
        strength=strength,
        input_source="Document-backed functional assay",
        input_values=dict(assay),
        clinvar_rule_applied="Brnich et al. 2019 OddsPath framework",
        provenance_chain=[
            f"PS3/BS3: {direction} assay with reported OddsPath={odds_path:g} -> {strength}"
        ],
        source_case_ids=[str(assay["assay_instance_id"])],
    )


def _pm1_contract(
    rule_override: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    contract = rule_override if isinstance(rule_override, dict) else None
    criteria = contract.get("criteria") if isinstance(contract, dict) else None
    criterion = criteria.get("PM1") if isinstance(criteria, dict) else None
    return contract, criterion if isinstance(criterion, dict) else None


def _in_ranges(position: int, criterion: dict[str, Any]) -> bool:
    residues = {
        int(value)
        for value in criterion.get("residues") or []
        if isinstance(value, int) and not isinstance(value, bool)
    }
    if position in residues:
        return True
    for region in criterion.get("regions") or []:
        if not isinstance(region, dict):
            continue
        start = region.get("start")
        end = region.get("end")
        if (
            isinstance(start, int)
            and not isinstance(start, bool)
            and isinstance(end, int)
            and not isinstance(end, bool)
            and start <= position <= end
        ):
            return True
    return False


def _pm1_card(
    profile: dict[str, Any],
    protein_context: dict[str, Any],
    rule_override: dict[str, Any] | None,
) -> EvidenceCard:
    contract, criterion_contract = _pm1_contract(rule_override)
    applicability = consequence_applicability(
        "PM1", profile, cspec_criterion=criterion_contract
    )
    observed = {
        "consequence_profile": dict(profile),
        "protein_context": dict(protein_context),
    }
    if applicability["status"] != "applicable":
        return EvidenceCard(
            criterion="PM1",
            strength="not_applicable",
            input_source="EBI Proteins / InterPro",
            input_values=observed,
            clinvar_rule_applied="ACMG/AMP 2015 PM1",
            provenance_chain=[applicability["reason"]],
        )
    if protein_context.get("mapping_status") != "resolved":
        return EvidenceCard(
            criterion="PM1",
            strength="not_assessed",
            input_source="EBI Proteins / InterPro",
            input_values=observed,
            clinvar_rule_applied="ACMG/AMP 2015 PM1",
            provenance_chain=[
                "PM1: a unique gene-, allele-, and protein-position-matched UniProt mapping is required"
            ],
        )

    selected = protein_context.get("selected_mapping")
    selected = selected if isinstance(selected, dict) else {}
    position = protein_context.get("protein_position")
    accession = str(selected.get("protein_accession") or "")
    overlapping = list(protein_context.get("overlapping_features") or [])
    if not overlapping and criterion_contract is None:
        return EvidenceCard(
            criterion="PM1",
            strength="not_assessed",
            input_source="EBI Proteins / InterPro",
            input_values=observed,
            clinvar_rule_applied="ACMG/AMP 2015 PM1",
            provenance_chain=[
                "PM1: no position-overlapping UniProt domain/site annotation was returned"
            ],
        )

    contract_complete = bool(
        isinstance(contract, dict)
        and isinstance(criterion_contract, dict)
        and str(contract.get("rule_id") or "")
        and str(contract.get("version") or "")
        and str(contract.get("primary_reference") or "")
        and str(criterion_contract.get("protein_accession") or "") == accession
        and isinstance(position, int)
        and _in_ranges(position, criterion_contract)
        and criterion_contract.get("critical_region_established") is True
        and criterion_contract.get("benign_variation_depleted") is True
        and isinstance(criterion_contract.get("variant_types"), list)
        and bool(criterion_contract.get("variant_types"))
        and isinstance(criterion_contract.get("mutually_exclusive_with"), list)
        and str(criterion_contract.get("strength") or "")
    )
    transcript = (
        str(criterion_contract.get("transcript") or "") if criterion_contract else ""
    )
    if transcript and transcript != str(profile.get("selected_transcript") or ""):
        contract_complete = False
    if contract_complete:
        strength = str(criterion_contract["strength"])
        return EvidenceCard(
            criterion="PM1",
            strength=strength,
            input_source="Verified ClinGen CSpec with EBI protein mapping",
            input_values={
                **observed,
                "cspec_contract_applied": dict(criterion_contract),
            },
            clinvar_rule_applied=str(contract.get("primary_reference") or ""),
            provenance_chain=[
                "PM1: exact verified CSpec protein region contract matched"
            ],
            rule_id=str(contract.get("rule_id") or ""),
            rule_version=str(contract.get("version") or ""),
            rule_reference=str(contract.get("primary_reference") or ""),
        )

    missing = [
        "verified critical-region or hotspot contract",
        "verified depletion of benign variation",
        "exact disease/inheritance/transcript/protein-region match",
    ]
    return EvidenceCard(
        criterion="PM1",
        strength="indeterminate",
        input_source="EBI Proteins / InterPro",
        input_values={**observed, "missing_requirements": missing},
        clinvar_rule_applied="ACMG/AMP 2015 PM1",
        provenance_chain=[
            "PM1: domain/site overlap is reviewable context but is insufficient for automatic PM1"
        ],
    )


def functional_evidence(
    variant_type: str = "",
    functional_assays: list[dict[str, Any]] | None = None,
    consequence_profile: dict[str, Any] | None = None,
    protein_context: dict[str, Any] | None = None,
    pvs1_facts: dict[str, Any] | None = None,
    rule_override: dict[str, Any] | None = None,
) -> list[EvidenceCard]:
    """Return one independent review result per document-verified assay."""
    cards: list[EvidenceCard] = []
    normalized_type = str(variant_type or "").lower().strip()
    profile = dict(consequence_profile or {})
    if not profile:
        normalized_effect = {
            "missense_variant": "missense",
            "inframe_insertion": "inframe",
            "inframe_deletion": "inframe",
            "synonymous_variant": "synonymous",
            "stop_lost": "stop_lost",
        }.get(normalized_type, normalized_type or "unresolved")
        profile = {
            "status": "resolved" if normalized_type else "unavailable",
            "protein_effect": (
                "lof"
                if normalized_type
                in {"frameshift", "frameshift_variant", "stop_gained", "nonsense"}
                else normalized_effect
            ),
            "splice_class": "none",
            "selected_transcript_terms": [normalized_type] if normalized_type else [],
        }
    cards.append(_pm1_card(profile, dict(protein_context or {}), rule_override))
    if consequence_applicability("PVS1", profile)["status"] == "applicable":
        cards.append(
            assess_pvs1(
                consequence_profile=profile,
                pvs1_facts=pvs1_facts,
                rule_override=rule_override,
            )
        )
    assays = [item for item in functional_assays or [] if isinstance(item, dict)]
    if not assays:
        cards.append(
            _not_assessed("PS3/BS3: no document-verified assay was supplied", {})
        )
        return cards
    cards.extend(_assess_assay(assay) for assay in assays)
    return cards


__all__ = ["functional_evidence"]
