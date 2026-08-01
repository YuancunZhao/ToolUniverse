"""Computational ACMG evidence with a fixed, auditable REVEL policy."""

from __future__ import annotations

import math
from typing import Any

from .consequence import consequence_applicability
from .models import EvidenceCard
from .rule_catalog import SPLICEAI_RULE, rule_for_criterion
from .spliceai import normalize_spliceai_inputs, walker_run_metadata_ready


def _finite_number(value: object) -> float | None:
    # Providers serialize scores as numeric strings (e.g. SpliceAI DS_*).
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def computational_evidence(
    revel_score: float | None = None,
    cadd_phred: float | None = None,
    spliceai_max_delta: float | None = None,
    spliceai_profile: dict[str, Any] | None = None,
    spliceai_scores: dict[str, Any] | None = None,
    spliceai_run_metadata: dict[str, Any] | None = None,
    predictor_scores: dict[str, Any] | None = None,
    splice_context: dict[str, Any] | None = None,
    consequence_profile: dict[str, Any] | None = None,
    consequence_terms: list[str] | None = None,
    hgvs_c: str = "",
    hgvs_p: str = "",
    rule_override: dict[str, Any] | None = None,
    variant_type: str = "",
) -> list[EvidenceCard]:
    """Assess PP3/BP4 with REVEL only; retain other scores as audit context."""
    revel_score = _finite_number(revel_score)
    rule = rule_for_criterion("PP3")
    variant_type = str(variant_type or "").strip().lower()
    profile = dict(consequence_profile or {})
    if not profile:
        normalized_type = {
            "missense_variant": "missense",
            "frameshift_variant": "lof",
            "inframe_insertion": "inframe",
            "inframe_deletion": "inframe",
            "synonymous_variant": "synonymous",
        }.get(variant_type, variant_type or "unresolved")
        terms = [str(value).casefold() for value in consequence_terms or [] if value]
        splice_class = (
            "canonical"
            if {"splice_donor_variant", "splice_acceptor_variant"} & set(terms)
            else "noncanonical"
            if "splice_region_variant" in terms
            else "none"
        )
        profile = {
            "status": "resolved" if variant_type or terms else "unavailable",
            "protein_effect": normalized_type,
            "splice_class": splice_class,
            "selected_transcript_terms": terms,
            "hgvs_c": hgvs_c,
            "hgvs_p": hgvs_p,
            "is_small_variant": True,
        }
    variant_type = str(profile.get("protein_effect") or variant_type).strip().lower()
    context = dict(splice_context or {})
    if not context:
        context = {
            "applicable": profile.get("status") == "resolved",
            "derived_from": "direct review input"
            if profile.get("status") == "resolved"
            else "",
            "splice_position": profile.get("splice_position"),
            "splice_class": profile.get("splice_class"),
            "consequence_terms": list(profile.get("selected_transcript_terms") or []),
            "protein_effect": profile.get("protein_effect"),
        }
    context.setdefault("protein_effect", profile.get("protein_effect"))
    splice_position = _splice_position(context.get("splice_position"))
    consequence_terms = {
        str(value).strip().lower()
        for value in context.get("consequence_terms") or []
        if value
    }
    is_canonical_splice = (
        context.get("splice_class") == "canonical"
        or splice_position in {-2, -1, 1, 2}
        or bool(consequence_terms & {"splice_donor_variant", "splice_acceptor_variant"})
    )
    splice_prediction_applicable = bool(
        context.get("derived_from")
        and context.get("applicable") is True
        and profile.get("is_small_variant") is True
        and not is_canonical_splice
    )
    site_type = str(
        profile.get("canonical_site_type")
        or context.get("canonical_site_type")
        or _site_type_from_context(consequence_terms, splice_position)
    )
    metadata_row = (
        spliceai_run_metadata.get("selected_score_row")
        if isinstance(spliceai_run_metadata, dict)
        and isinstance(spliceai_run_metadata.get("selected_score_row"), dict)
        else {}
    )
    supplied_scores = dict(spliceai_scores or {})
    required_channels = {
        "DS_AG",
        "DS_AL",
        "DS_DG",
        "DS_DL",
        "DP_AG",
        "DP_AL",
        "DP_DG",
        "DP_DL",
    }
    score_row = (
        supplied_scores
        if required_channels <= supplied_scores.keys()
        else dict(metadata_row)
        if required_channels <= metadata_row.keys()
        else supplied_scores
    )
    normalized_spliceai = normalize_spliceai_inputs(
        spliceai_profile=spliceai_profile,
        spliceai_scores=score_row,
        spliceai_max_delta=spliceai_max_delta,
        canonical_site_type=site_type,
        hgvs_c=profile.get("hgvs_c") or context.get("hgvs_c"),
        variant_position=profile.get("genomic_position")
        or context.get("genomic_position"),
    )
    audit_scores = {
        key: value
        for key, value in {
            "revel_score": revel_score,
            "cadd_phred": cadd_phred,
            "spliceai_max_delta": spliceai_max_delta,
        }.items()
        if value is not None
    }
    audit_scores.update(dict(predictor_scores or {}))
    if spliceai_scores:
        audit_scores["spliceai_scores"] = dict(spliceai_scores)
    audit_scores["spliceai_profile"] = normalized_spliceai
    if spliceai_run_metadata:
        audit_scores["spliceai_run_metadata"] = dict(spliceai_run_metadata)

    missense_applicable = (
        profile.get("protein_effect") == "missense"
        and consequence_applicability("PP3", profile)["status"] == "applicable"
    )
    if not missense_applicable:
        cards = [
            EvidenceCard(
                criterion="PP3/BP4",
                strength="not_assessed" if not variant_type else "not_applicable",
                input_source="REVEL",
                input_values={"variant_type": variant_type, **audit_scores},
                clinvar_rule_applied="Pejaver 2022 (PMID:36413997)",
                provenance_chain=[
                    "PP3/BP4: the fixed REVEL calibration applies only to explicit missense variants"
                ],
            ),
        ]
        cards.extend(
            _splice_prediction_cards(
                normalized_spliceai,
                splice_prediction_applicable=splice_prediction_applicable,
                splice_context=context,
                audit_scores=audit_scores,
                spliceai_run_metadata=spliceai_run_metadata,
                rule_override=rule_override,
            )
        )
        cards.extend(_pvs1_splice_route(is_canonical_splice, normalized_spliceai))
        return cards

    if revel_score is None:
        card = EvidenceCard(
            criterion="PP3/BP4",
            strength="not_assessed",
            input_source="REVEL",
            input_values=audit_scores,
            clinvar_rule_applied="Pejaver 2022 (PMID:36413997)",
            provenance_chain=["PP3/BP4: no REVEL score was returned by the provider"],
        )
        return [
            card,
            *_splice_prediction_cards(
                normalized_spliceai,
                splice_prediction_applicable=splice_prediction_applicable,
                splice_context=context,
                audit_scores=audit_scores,
                spliceai_run_metadata=spliceai_run_metadata,
                rule_override=rule_override,
            ),
            *_pvs1_splice_route(is_canonical_splice, normalized_spliceai),
        ]

    cspec_decision = _cspec_predictor_decision(
        revel_score,
        predictor="REVEL",
        variant_type=variant_type,
        rule_override=rule_override,
    )
    thresholds = rule["thresholds"]["REVEL"]
    if cspec_decision is not None:
        criterion, strength = cspec_decision
    elif revel_score >= thresholds["pp3_strong_min"]:
        criterion, strength = "PP3", "PP3_Strong"
    elif revel_score >= thresholds["pp3_moderate_min"]:
        criterion, strength = "PP3", "PP3_Moderate"
    elif revel_score >= thresholds["pp3_supporting_min"]:
        criterion, strength = "PP3", "PP3_Supporting"
    elif revel_score <= thresholds["bp4_very_strong_max"]:
        criterion, strength = "BP4", "BP4_VeryStrong"
    elif revel_score <= thresholds["bp4_strong_max"]:
        criterion, strength = "BP4", "BP4_Strong"
    elif revel_score <= thresholds["bp4_moderate_max"]:
        criterion, strength = "BP4", "BP4_Moderate"
    elif revel_score <= thresholds["bp4_supporting_max"]:
        criterion, strength = "BP4", "BP4_Supporting"
    else:
        criterion, strength = "PP3/BP4", "not_met"

    card = EvidenceCard(
        criterion=criterion,
        strength=strength,
        input_source="REVEL",
        input_values=audit_scores,
        clinvar_rule_applied="Pejaver 2022 Table 2 (PMID:36413997)",
        provenance_chain=[
            f"PP3/BP4: fixed REVEL={revel_score:.3f} -> {strength}; other predictors are audit-only"
        ],
    )
    _apply_cspec_provenance(card, rule_override, cspec_decision is not None)
    return [
        card,
        *_splice_prediction_cards(
            normalized_spliceai,
            splice_prediction_applicable=splice_prediction_applicable,
            splice_context=context,
            audit_scores=audit_scores,
            spliceai_run_metadata=spliceai_run_metadata,
            rule_override=rule_override,
        ),
        *_pvs1_splice_route(is_canonical_splice, normalized_spliceai),
    ]


def _splice_prediction_cards(
    spliceai_profile: dict[str, Any],
    *,
    splice_prediction_applicable: bool,
    splice_context: dict[str, Any],
    audit_scores: dict[str, Any],
    spliceai_run_metadata: dict[str, Any] | None,
    rule_override: dict[str, Any] | None = None,
) -> list[EvidenceCard]:
    score = _finite_number(spliceai_profile.get("max_delta_score"))
    if score is None and not splice_context:
        return []
    cspec_decision = None
    if not splice_prediction_applicable:
        strength = "not_assessed"
        reason = (
            "PP3/BP4 splicing: transcript-relative splice position was not "
            "derived from normalized consequence data"
        )
    elif spliceai_profile.get("status") != "resolved":
        strength = "not_assessed"
        reason = (
            "PP3/BP4 splicing: complete, internally consistent DS_AG/DS_AL/"
            "DS_DG/DS_DL and DP_* values were not available"
        )
    elif score is None:
        strength = "not_assessed"
        reason = "PP3/BP4 splicing: no SpliceAI maximum delta score was returned"
    elif not walker_run_metadata_ready(spliceai_run_metadata, score):
        strength = "not_assessed"
        reason = (
            "PP3/BP4 splicing: SpliceAI run metadata does not prove the "
            "Walker 2023 calibration conditions"
        )
    else:
        cspec_decision = _cspec_predictor_decision(
            score,
            predictor="SpliceAI",
            variant_type="splicing",
            rule_override=rule_override,
        )
    if not splice_prediction_applicable:
        pass
    elif spliceai_profile.get("status") != "resolved":
        pass
    elif score is None:
        pass
    elif not walker_run_metadata_ready(spliceai_run_metadata, score):
        pass
    elif cspec_decision is not None:
        strength = cspec_decision[1]
        reason = (
            f"{cspec_decision[0]} splicing: verified CSpec contract "
            f"applied to SpliceAI={score:.3f}"
        )
    elif score >= SPLICEAI_RULE["thresholds"]["pp3_supporting_min"]:
        strength = "PP3_Supporting"
        reason = (
            f"PP3 splicing: SpliceAI maximum unmasked delta score={score:.3f} >= 0.2"
        )
    elif score <= SPLICEAI_RULE["thresholds"]["bp4_supporting_max"]:
        strength = "BP4_Supporting"
        reason = (
            f"BP4 splicing: SpliceAI maximum unmasked delta score={score:.3f} <= 0.1"
        )
    else:
        strength = "not_met"
        reason = f"PP3/BP4 splicing: SpliceAI max delta={score:.3f} is indeterminate"
    criterion = (
        "PP3"
        if strength.startswith("PP3")
        else "BP4"
        if strength.startswith("BP4")
        else "PP3/BP4"
    )
    card = EvidenceCard(
        criterion=criterion,
        strength=strength,
        input_source="SpliceAI",
        input_values={**audit_scores, "splice_context": dict(splice_context)},
        clinvar_rule_applied="ClinGen SVI splicing recommendations (Walker et al. 2023)",
        provenance_chain=[reason],
        rule_id=str(SPLICEAI_RULE["rule_id"]),
        rule_version=str(SPLICEAI_RULE["version"]),
        rule_reference=str(SPLICEAI_RULE["primary_reference"]),
    )
    _apply_cspec_provenance(card, rule_override, cspec_decision is not None)
    cards = [card]
    if strength == "BP4_Supporting":
        bp7 = _bp7_after_walker_bp4(splice_context, audit_scores)
        if bp7 is not None:
            cards.append(bp7)
    return cards


def _bp7_after_walker_bp4(
    splice_context: dict[str, Any],
    audit_scores: dict[str, Any],
) -> EvidenceCard | None:
    """Apply BP7 only after the strict Walker BP4 prediction result."""
    terms = {
        str(value).strip().casefold()
        for value in splice_context.get("consequence_terms") or []
        if value
    }
    effect = str(splice_context.get("protein_effect") or "").strip().casefold()
    position = _splice_position(splice_context.get("splice_position"))
    synonymous = effect == "synonymous" or "synonymous_variant" in terms
    deep_intronic = bool(
        "intron_variant" in terms
        and position is not None
        and (position > 7 or position < -21)
    )
    if not (synonymous or deep_intronic):
        return None
    rule = rule_for_criterion("BP7")
    reason = (
        "BP7: strict Walker BP4 plus synonymous consequence"
        if synonymous
        else "BP7: strict Walker BP4 plus intronic position outside +7/-21"
    )
    return EvidenceCard(
        criterion="BP7",
        strength="BP7_Supporting",
        input_source="SpliceAI",
        input_values={**audit_scores, "splice_context": dict(splice_context)},
        clinvar_rule_applied="ClinGen SVI splicing recommendations (Walker et al. 2023)",
        provenance_chain=[reason],
        rule_id=str(rule.get("rule_id") or ""),
        rule_version=str(rule.get("version") or ""),
        rule_reference=str(rule.get("primary_reference") or ""),
    )


def _cspec_predictor_decision(
    score: float | None,
    *,
    predictor: str,
    variant_type: str,
    rule_override: dict[str, Any] | None,
) -> tuple[str, str] | None:
    """Apply only an explicit, source-verified CSpec numeric predictor contract."""
    if score is None or not isinstance(rule_override, dict):
        return None
    criteria = rule_override.get("criteria")
    if not isinstance(criteria, dict):
        return None
    decisions: list[tuple[str, str]] = []
    for criterion in ("PP3", "BP4"):
        contract = criteria.get(criterion)
        if not isinstance(contract, dict):
            continue
        if str(contract.get("predictor") or "").casefold() != predictor.casefold():
            continue
        allowed_types = {
            str(value).casefold() for value in contract.get("variant_types") or ()
        }
        normalized_type = variant_type.casefold()
        equivalent_types = {
            normalized_type,
            {
                "missense": "missense_variant",
                "inframe": "inframe_variant",
                "synonymous": "synonymous_variant",
                "noncoding": "noncoding_variant",
            }.get(normalized_type, normalized_type),
        }
        if allowed_types and not (equivalent_types & allowed_types):
            continue
        threshold = _finite_number(contract.get("threshold"))
        operator = str(contract.get("operator") or "")
        strength = str(contract.get("strength") or "")
        if threshold is None or not strength:
            continue
        matched = (operator in {">=", "gte"} and score >= threshold) or (
            operator in {"<=", "lte"} and score <= threshold
        )
        if matched:
            decisions.append((criterion, strength))
    return decisions[0] if len(decisions) == 1 else None


def _apply_cspec_provenance(
    card: EvidenceCard,
    rule_override: dict[str, Any] | None,
    applied: bool,
) -> None:
    if not applied or not isinstance(rule_override, dict):
        return
    card.input_values["cspec_contract_applied"] = {
        "specification_id": rule_override.get("specification_id"),
        "version": rule_override.get("version"),
    }
    card.rule_id = str(rule_override.get("rule_id") or "")
    card.rule_version = str(rule_override.get("version") or "")
    card.rule_reference = str(rule_override.get("primary_reference") or "")
    card.rule_basis = (
        f"Verified ClinGen CSpec contract "
        f"{rule_override.get('specification_id') or rule_override.get('rule_id')}"
    )


def _splice_position(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _site_type_from_context(
    consequence_terms: set[str],
    splice_position: int | None,
) -> str:
    donor = "splice_donor_variant" in consequence_terms
    acceptor = "splice_acceptor_variant" in consequence_terms
    if donor and acceptor:
        return "ambiguous"
    if donor:
        return "donor"
    if acceptor:
        return "acceptor"
    if splice_position in {1, 2}:
        return "donor"
    if splice_position in {-2, -1}:
        return "acceptor"
    return "none"


def _pvs1_splice_route(
    is_canonical_splice: bool,
    spliceai_profile: dict[str, Any],
) -> list[EvidenceCard]:
    if not is_canonical_splice:
        return []
    return [
        EvidenceCard(
            criterion="PVS1",
            strength="not_assessed",
            input_source="SpliceAI route context",
            input_values={"spliceai_profile": dict(spliceai_profile)},
            clinvar_rule_applied="ClinGen SVI PVS1 decision tree",
            provenance_chain=[
                "PVS1: transcript, observed RNA outcome, NMD, rescue, and LoF mechanism facts are required"
            ],
        )
    ]


__all__ = ["computational_evidence"]
