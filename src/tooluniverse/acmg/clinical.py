"""Atomic clinical-observation evidence for the ACMG v3 automation runtime."""

from __future__ import annotations

from collections import defaultdict
import math
from typing import Any

from .models import EvidenceCard
from .rule_catalog import criterion_use_matrix, is_valid_strength_for_criterion


_DE_NOVO_POINTS = {
    "highly_specific": {"confirmed": 2.0, "assumed": 1.0},
    "consistent": {"confirmed": 1.0, "assumed": 0.5},
    "consistent_high_heterogeneity": {"confirmed": 0.5, "assumed": 0.25},
    "not_consistent": {"confirmed": 0.0, "assumed": 0.0},
}

_OBSERVATION_CRITERIA = {
    "segregation": ("PP1", "BS4"),
    "phenotype_specificity": ("PP4",),
    "healthy_observation": ("BS2",),
    "allelic_phase": ("BP2",),
    "alternative_cause": ("BP5",),
    "functional_assay": ("PS3", "BS3"),
    "case_control": ("PS4",),
    "case_series": ("PS4",),
}

_PP1_PP4_RULE_ID = "clingen-svi-pp1-pp4-bs4"
_PP1_PP4_RULE_VERSION = "2023.1"
_PP1_PP4_REFERENCE = "Biesecker et al. 2024, PMID:38103548"
_DIAGNOSTIC_YIELD_POINTS = (
    (0.999, 12.0),
    (0.998, 11.5),
    (0.997, 11.0),
    (0.996, 10.5),
    (0.994, 10.0),
    (0.992, 9.5),
    (0.988, 9.0),
    (0.983, 8.5),
    (0.975, 8.0),
    (0.965, 7.5),
    (0.950, 7.0),
    (0.930, 6.5),
    (0.902, 6.0),
    (0.864, 5.5),
    (0.816, 5.0),
    (0.754, 4.5),
    (0.680, 4.0),
    (0.596, 3.5),
    (0.506, 3.0),
    (0.415, 2.5),
    (0.330, 2.0),
    (0.254, 1.5),
    (0.191, 1.0),
)


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _diagnostic_yield_points(value: Any) -> float | None:
    diagnostic_yield = _finite(value)
    if diagnostic_yield is None:
        return None
    if diagnostic_yield > 1.0:
        diagnostic_yield /= 100.0
    if diagnostic_yield < 0.0 or diagnostic_yield > 1.0:
        return None
    return next(
        (
            points
            for threshold, points in _DIAGNOSTIC_YIELD_POINTS
            if diagnostic_yield >= threshold
        ),
        0.0,
    )


def _pathogenic_strength_for_points(criterion: str, points: float) -> str:
    if points >= 4.0:
        return f"{criterion}_Strong"
    if points >= 2.0:
        return f"{criterion}_Moderate"
    if points >= 1.0:
        return f"{criterion}_Supporting"
    return ""


def _strength_points(strength: str) -> int:
    if str(strength).endswith("_Strong"):
        return 4
    if str(strength).endswith("_Moderate"):
        return 2
    if str(strength).endswith("_Supporting"):
        return 1
    return 0


def _combined_dimensions(rows: list[dict[str, Any]]) -> dict[str, str]:
    if not rows:
        return {}
    dimensions = [_verification_dimensions(row) for row in rows]
    order = {
        "identity_status": ("matched", "partial", "unknown", "conflict"),
        "source_status": (
            "available",
            "abstract_only",
            "snippet_only",
            "unavailable",
            "failed",
        ),
        "extraction_status": (
            "structured",
            "rule_extracted",
            "llm_extracted",
            "unresolved",
            "contradicted",
        ),
        "version_status": ("versioned", "unversioned", "stale"),
        "disease_match_status": ("matched", "unspecified", "candidate", "mismatch"),
        "independence_status": ("independent", "unknown", "overlapping"),
    }
    return {
        key: max(
            (row.get(key, values[0]) for row in dimensions),
            key=lambda value: values.index(value) if value in values else len(values),
        )
        for key, values in order.items()
    }


def _source_ids(row: dict[str, Any]) -> list[str]:
    value = str(row.get("source_fact_id") or "").strip()
    return [value] if value else []


def _correlation_keys(row: dict[str, Any]) -> dict[str, list[str]]:
    values = row.get("values") if isinstance(row.get("values"), dict) else row
    result: dict[str, list[str]] = {}
    for key in (
        "proband_id",
        "case_id",
        "family_id",
        "cohort_id",
        "assay_instance_id",
        "experiment_id",
        "second_allele_id",
        "individual_id",
    ):
        value = values.get(key)
        if value not in (None, ""):
            result[key] = [str(value)]
    return result


def _verification_dimensions(row: dict[str, Any]) -> dict[str, str]:
    return {
        "identity_status": str(row.get("identity_status") or "matched"),
        "source_status": str(row.get("source_status") or "available"),
        "extraction_status": str(row.get("extraction_status") or "structured"),
        "version_status": str(row.get("version_status") or "unversioned"),
        "disease_match_status": str(row.get("disease_match_status") or "unspecified"),
        "independence_status": str(row.get("independence_status") or "unknown"),
    }


def _hard_error(row: dict[str, Any]) -> str:
    dimensions = _verification_dimensions(row)
    if dimensions["identity_status"] == "conflict":
        return "clinical observation conflicts with the resolved variant identity"
    if dimensions["extraction_status"] == "contradicted":
        return "clinical observation is explicitly contradicted by its source"
    if dimensions["disease_match_status"] == "mismatch":
        return "clinical observation concerns a different disease context"
    if dimensions["independence_status"] == "overlapping":
        return "clinical observation is a confirmed duplicate or overlap"
    return ""


def _independence_limited_rows(
    rows: list[tuple[dict[str, Any], float]],
) -> tuple[list[tuple[dict[str, Any], float]], list[tuple[dict[str, Any], float]]]:
    """Count independent atoms, or one unknown atom when independence is unresolved."""

    def independence_status(row: dict[str, Any]) -> str:
        # Legacy direct calculator inputs use one explicitly identified record
        # per case. Collector-bound literature/caller facts always carry an
        # explicit independence_status, so absence remains safe and compatible.
        if "independence_status" not in row:
            return "independent"
        return _verification_dimensions(row)["independence_status"]

    independent = [row for row in rows if independence_status(row[0]) == "independent"]
    if independent:
        return independent, [row for row in rows if row not in independent]
    unknown = [row for row in rows if independence_status(row[0]) == "unknown"]
    return unknown[:1], unknown[1:]


def _excluded_atom(
    criterion: str,
    row: dict[str, Any],
    reason: str,
    *,
    rule_reference: str,
) -> EvidenceCard:
    return EvidenceCard(
        criterion=criterion,
        strength="not_assessed",
        evidence_status="excluded",
        source_label=str(row.get("source_type") or "clinical observation"),
        observed_facts=dict(row),
        rule_basis=rule_reference,
        source_fact_ids=_source_ids(row),
        source_case_ids=[str(row.get("observation_id") or "")],
        caveats=[reason],
        exclusion_reason=reason,
        correlation_keys=_correlation_keys(row),
        verification_dimensions=_verification_dimensions(row),
    )


def _point_strength(criterion: str, points: float) -> str:
    if criterion == "PS2":
        levels = (
            (4.0, "PS2_VeryStrong"),
            (2.0, "PS2"),
            (1.0, "PS2_Moderate"),
            (0.5, "PS2_Supporting"),
        )
    elif criterion == "PM6":
        levels = (
            (4.0, "PM6_VeryStrong"),
            (2.0, "PM6_Strong"),
            (1.0, "PM6"),
            (0.5, "PM6_Supporting"),
        )
    else:
        levels = (
            (4.0, "PM3_VeryStrong"),
            (2.0, "PM3_Strong"),
            (1.0, "PM3"),
            (0.5, "PM3_Supporting"),
        )
    return next((strength for minimum, strength in levels if points >= minimum), "")


def _case_identifier(record: dict[str, Any]) -> str:
    """Use the atomic observation ID when no narrower case ID is supplied."""
    return str(
        record.get("case_id")
        or record.get("proband_id")
        or record.get("observation_id")
        or ""
    )


def _de_novo_cards(
    probands: list[dict[str, Any]], inheritance_mode: str
) -> list[EvidenceCard]:
    rule = "ClinGen SVI De Novo Recommendation v1.1"
    valid: dict[str, list[tuple[dict[str, Any], float]]] = defaultdict(list)
    cards: list[EvidenceCard] = []
    seen: set[str] = set()
    heterogeneity_points = {"confirmed": 0.0, "assumed": 0.0}
    for index, proband in enumerate(probands):
        if not isinstance(proband, dict):
            cards.append(
                _excluded_atom(
                    "PS2/PM6",
                    {"index": index},
                    "proband record must be an object",
                    rule_reference=rule,
                )
            )
            continue
        if error := _hard_error(proband):
            cards.append(_excluded_atom("PS2/PM6", proband, error, rule_reference=rule))
            continue
        case_id = _case_identifier(proband)
        relationship = str(proband.get("parental_relationships") or "").casefold()
        phenotype = str(proband.get("phenotype_consistency") or "").casefold()
        if not case_id or case_id in seen:
            cards.append(
                _excluded_atom(
                    "PS2/PM6",
                    proband,
                    "unique non-empty case_id, proband_id, or observation_id is required",
                    rule_reference=rule,
                )
            )
            continue
        seen.add(case_id)
        if (
            relationship not in {"confirmed", "assumed"}
            or phenotype not in _DE_NOVO_POINTS
        ):
            cards.append(
                _excluded_atom(
                    "PS2/PM6",
                    proband,
                    "parental relationship or phenotype category is invalid",
                    rule_reference=rule,
                )
            )
            continue
        points = _DE_NOVO_POINTS[phenotype][relationship]
        if phenotype == "consistent_high_heterogeneity":
            points = min(points, max(0.0, 1.0 - heterogeneity_points[relationship]))
            heterogeneity_points[relationship] += points
        valid[relationship].append((proband, points))

    for relationship, rows in valid.items():
        counted_rows, uncounted_rows = _independence_limited_rows(rows)
        total = sum(points for _row, points in counted_rows)
        criterion = "PS2" if relationship == "confirmed" else "PM6"
        strength = _point_strength(criterion, total)
        if "recessive" in inheritance_mode.casefold() and not all(
            row.get("second_variant_pathogenic") is True
            for row, _points in counted_rows
        ):
            downgrade = {
                "PS2_VeryStrong": "PS2",
                "PS2": "PS2_Moderate",
                "PS2_Moderate": "PS2_Supporting",
                "PM6_VeryStrong": "PM6_Strong",
                "PM6_Strong": "PM6",
                "PM6": "PM6_Supporting",
            }
            strength = downgrade.get(strength, strength)
        if not strength:
            strength = "not_met"
        source_fact_ids = sorted(
            {value for row, _points in rows for value in _source_ids(row)}
        )
        case_ids = [
            _case_identifier(row)
            for row, _points in counted_rows
        ]
        uncounted_case_ids = [
            _case_identifier(row)
            for row, _points in uncounted_rows
        ]
        all_counted_independent = bool(counted_rows) and all(
            "independence_status" not in row
            or _verification_dimensions(row)["independence_status"] == "independent"
            for row, _points in counted_rows
        )
        cards.append(
            EvidenceCard(
                criterion=criterion,
                strength=strength,
                evidence_status=(
                    "rule_mapped"
                    if strength != "not_met" and all_counted_independent
                    else "source_backed_candidate"
                    if strength != "not_met"
                    else "not_met"
                ),
                source_label="Atomic de novo observations",
                observed_facts={
                    "total_points": total,
                    "relationship": relationship,
                    "records": [row for row, _points in rows],
                    "counted_case_ids": case_ids,
                    "uncounted_unknown_independence_case_ids": uncounted_case_ids,
                },
                    rule_basis=rule,
                rule_id="clingen-svi-de-novo",
                rule_version="1.1",
                rule_reference=rule,
                rule_source={
                    "type": "versioned_svi",
                    "rule_id": "clingen-svi-de-novo",
                    "version": "1.1",
                },
                strength_source="clingen_svi_point_table",
                source_fact_ids=source_fact_ids,
                source_case_ids=case_ids,
                correlation_keys={"case_id": case_ids},
                verification_dimensions=(
                    _combined_dimensions([row for row, _points in counted_rows])
                ),
                caveats=(
                    [
                        "Additional records with unresolved independence were retained but not added to the de novo point total."
                    ]
                    if uncounted_rows
                    else []
                ),
                provenance_chain=[
                    f"{criterion}: {total:g} independently processed de novo points -> {strength}"
                ],
            )
        )
    return cards


def _pm3_points(observation: dict[str, Any]) -> tuple[float | None, str]:
    if observation.get("other_variant_frequency_eligible") is not True:
        return None, "other allele does not meet the frequency requirement"
    zygosity = str(observation.get("zygosity") or "").casefold()
    phase = str(observation.get("phase") or "").casefold()
    other_class = str(observation.get("other_variant_classification") or "").upper()
    if zygosity == "homozygous":
        return (0.25 if observation.get("consanguineous") is True else 0.5), ""
    if zygosity != "compound_heterozygous" or phase not in {
        "confirmed_in_trans",
        "unknown",
    }:
        return None, "unsupported zygosity or phase"
    if other_class in {"PATHOGENIC", "P"}:
        return (1.0 if phase == "confirmed_in_trans" else 0.5), ""
    if other_class in {"LIKELY_PATHOGENIC", "LP"}:
        return (1.0 if phase == "confirmed_in_trans" else 0.25), ""
    if other_class in {"VUS", "UNCERTAIN_SIGNIFICANCE"}:
        return (0.25 if phase == "confirmed_in_trans" else 0.0), ""
    return None, "unsupported other-allele classification"


def _pm3_cards(
    observations: list[dict[str, Any]],
    *,
    inheritance_mode: str,
    frequency_eligible: bool,
) -> list[EvidenceCard]:
    rule = "ClinGen SVI PM3 Recommendation v1.0"
    cards: list[EvidenceCard] = []
    if "recessive" not in inheritance_mode.casefold() or frequency_eligible is not True:
        return cards
    valid: list[tuple[dict[str, Any], float]] = []
    seen: set[str] = set()
    homozygous_total = 0.0
    capped_total = 0.0
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            cards.append(
                _excluded_atom(
                    "PM3",
                    {"index": index},
                    "observation must be an object",
                    rule_reference=rule,
                )
            )
            continue
        if error := _hard_error(observation):
            cards.append(_excluded_atom("PM3", observation, error, rule_reference=rule))
            continue
        case_id = _case_identifier(observation)
        if not case_id or case_id in seen:
            cards.append(
                _excluded_atom(
                    "PM3",
                    observation,
                    "unique non-empty case_id, proband_id, or observation_id is required",
                    rule_reference=rule,
                )
            )
            continue
        seen.add(case_id)
        points, error = _pm3_points(observation)
        if points is None:
            cards.append(_excluded_atom("PM3", observation, error, rule_reference=rule))
            continue
        if str(observation.get("zygosity") or "").casefold() == "homozygous":
            if observation.get("consanguineous") is True:
                points = min(points, max(0.0, 0.5 - capped_total))
                capped_total += points
            else:
                points = min(points, max(0.0, 1.0 - homozygous_total))
                homozygous_total += points
        elif str(observation.get("other_variant_classification") or "").upper() in {
            "VUS",
            "UNCERTAIN_SIGNIFICANCE",
        }:
            points = min(points, max(0.0, 0.5 - capped_total))
            capped_total += points
        valid.append((observation, points))
    counted, uncounted = _independence_limited_rows(valid)
    total = sum(points for _row, points in counted)
    strength = _point_strength("PM3", total) or "not_met"
    if valid:
        case_ids = [
            _case_identifier(row) for row, _points in counted
        ]
        uncounted_case_ids = [
            _case_identifier(row)
            for row, _points in uncounted
        ]
        all_counted_independent = bool(counted) and all(
            "independence_status" not in row
            or _verification_dimensions(row)["independence_status"] == "independent"
            for row, _points in counted
        )
        cards.append(
            EvidenceCard(
                criterion="PM3",
                strength=strength,
                evidence_status=(
                    "rule_mapped"
                    if strength != "not_met" and all_counted_independent
                    else "source_backed_candidate"
                    if strength != "not_met"
                    else "not_met"
                ),
                source_label="Atomic recessive-case observations",
                observed_facts={
                    "total_points": total,
                    "records": [row for row, _points in valid],
                    "counted_case_ids": case_ids,
                    "uncounted_unknown_independence_case_ids": uncounted_case_ids,
                },
                    rule_basis=rule,
                rule_id="clingen-svi-pm3",
                rule_version="1.0",
                rule_reference=rule,
                rule_source={
                    "type": "versioned_svi",
                    "rule_id": "clingen-svi-pm3",
                    "version": "1.0",
                },
                strength_source="clingen_svi_point_table",
                source_fact_ids=sorted(
                    {value for row, _points in valid for value in _source_ids(row)}
                ),
                source_case_ids=case_ids,
                correlation_keys={"case_id": case_ids},
                verification_dimensions=(
                    _combined_dimensions([row for row, _points in counted])
                ),
                caveats=(
                    [
                        "Additional records with unresolved independence were retained but not added to the PM3 point total."
                    ]
                    if uncounted
                    else []
                ),
                provenance_chain=[
                    f"PM3: {total:g} independently processed points -> {strength}"
                ],
            )
        )
    return cards


def _generic_observation_card(observation: dict[str, Any]) -> EvidenceCard:
    observation_type = str(observation.get("observation_type") or "")
    values = (
        observation.get("values") if isinstance(observation.get("values"), dict) else {}
    )
    allowed = _OBSERVATION_CRITERIA.get(observation_type, ())
    if error := _hard_error(observation):
        return _excluded_atom(
            allowed[0] if allowed else "UNMAPPED",
            observation,
            error,
            rule_reference="ACMG/AMP 2015",
        )
    proposed = str(values.get("criterion") or "")
    if proposed not in allowed:
        if observation_type == "segregation":
            proposed = (
                "BS4"
                if str(values.get("direction") or "").casefold() == "benign"
                else "PP1"
            )
        elif observation_type == "functional_assay":
            proposed = (
                "BS3"
                if str(values.get("direction") or "").casefold() == "benign"
                else "PS3"
            )
        else:
            proposed = allowed[0] if allowed else ""
    matrix = criterion_use_matrix().get(proposed, {})
    strength = str(
        values.get("suggested_strength")
        or matrix.get("default_candidate_strength")
        or proposed
    )
    if not proposed or not is_valid_strength_for_criterion(proposed, strength):
        return _excluded_atom(
            proposed or "UNMAPPED",
            observation,
            "observation type cannot be mapped to a legal criterion/strength",
            rule_reference="ACMG/AMP 2015",
        )
    special_core = bool(matrix.get("special_core_definition_required"))
    core_satisfied = values.get("core_definition_satisfied") is True
    evidence_status = (
        "rule_mapped"
        if values.get("versioned_rule_satisfied") is True
        else "source_backed_candidate"
    )
    if special_core and not core_satisfied:
        evidence_status = "excluded"
    source_fact_ids = _source_ids(observation)
    observation_id = str(observation.get("observation_id") or "")
    return EvidenceCard(
        criterion=proposed,
        strength=strength if evidence_status != "excluded" else "not_assessed",
        evidence_status=evidence_status,
        source_label=str(observation.get("source_type") or "clinical observation"),
        observed_facts=dict(observation),
        rule_basis=str(
            values.get("rule_reference")
            or "ACMG/AMP 2015 source-backed candidate policy"
        ),
        strength_source=(
            "versioned_rule"
            if evidence_status == "rule_mapped"
            else "acmg_2015_default_candidate"
        ),
        rule_source={
            "type": "versioned_svi"
            if evidence_status == "rule_mapped"
            else "generic_acmg_candidate",
            "rule_id": str(
                values.get("rule_id")
                or matrix.get("candidate_policy", {}).get("policy_id")
                or ""
            ),
            "version": str(
                values.get("rule_version")
                or matrix.get("candidate_policy", {}).get("version")
                or ""
            ),
        },
        source_fact_ids=source_fact_ids,
        source_case_ids=[observation_id] if observation_id else [],
        correlation_keys=_correlation_keys(observation),
        verification_dimensions=_verification_dimensions(observation),
        caveats=(
            []
            if evidence_status != "excluded"
            else ["Dedicated core criterion definition was not satisfied."]
        ),
        exclusion_reason=(
            ""
            if evidence_status != "excluded"
            else "special_core_definition_not_satisfied"
        ),
    )


def _ps4_observation_card(observation: dict[str, Any]) -> EvidenceCard:
    """Apply numeric case-control facts and retain case-series facts as candidates."""
    card = _generic_observation_card(observation)
    if card.evidence_status == "excluded":
        return card
    values = (
        observation.get("values") if isinstance(observation.get("values"), dict) else {}
    )
    observation_type = str(observation.get("observation_type") or "")
    card.rule_id = "acmg-v3-ps4-source-backed"
    card.rule_version = "2026-08-08-v3"
    card.rule_reference = "ACMG/AMP 2015 PS4 source-backed automation policy"
    if observation_type == "case_control":
        odds_ratio = _finite(values.get("odds_ratio"))
        ci_lower = _finite(values.get("ci_lower"))
        if odds_ratio is None or ci_lower is None:
            card.caveats.append(
                "A numeric odds ratio and lower confidence bound were not both available; PS4 remains a source-backed candidate."
            )
            return card
        if odds_ratio <= 1.0 or ci_lower <= 1.0:
            card.strength = "not_met"
            card.evidence_status = "not_met"
            card.provenance_chain.append(
                "The case-control estimate does not exclude the null (OR or lower CI bound <= 1)."
            )
            return card
        card.evidence_status = "rule_mapped"
        card.strength_source = "acmg_ps4_case_control_numeric_rule"
        card.rule_source = {
            "type": "generic_acmg_numeric_rule",
            "rule_id": card.rule_id,
            "version": card.rule_version,
        }
        card.provenance_chain.append(
            f"Case-control enrichment: OR={odds_ratio:g}, lower CI={ci_lower:g}."
        )
        return card
    case_count = _finite(values.get("case_count"))
    if case_count is not None:
        card.provenance_chain.append(
            f"Case-series source reports {case_count:g} case(s); no disease-specific threshold was assumed."
        )
    card.caveats.append(
        "Without a uniquely applicable VCEP/CSpec case-series threshold, PS4 uses the ACMG base-strength candidate policy."
    )
    return card


def _segregation_points(
    observation: dict[str, Any], inheritance_mode: str
) -> tuple[float | None, str]:
    values = (
        observation.get("values") if isinstance(observation.get("values"), dict) else {}
    )
    explicit = _finite(values.get("segregation_points"))
    if explicit is not None:
        return max(0.0, explicit), "caller-supplied Bayesian points"
    inheritance = str(
        values.get("inheritance_mode") or inheritance_mode or ""
    ).casefold()
    affected = _finite(
        values.get("affected_cosegregations")
        if values.get("affected_cosegregations") is not None
        else values.get("informative_meioses")
    )
    unaffected = _finite(values.get("unaffected_cosegregations")) or 0.0
    if affected is None:
        return None, "affected co-segregation count is required"
    if affected < 0 or unaffected < 0:
        return None, "co-segregation counts must be non-negative"
    if "recessive" in inheritance and "x-linked" not in inheritance:
        points = affected * 2.0
        if values.get("fully_penetrant") is True:
            points += unaffected * 0.4
    elif "dominant" in inheritance or "x-linked" in inheritance:
        points = affected
        if values.get("fully_penetrant") is True:
            points += unaffected
    else:
        return (
            None,
            "autosomal dominant, autosomal recessive, or X-linked inheritance is required",
        )
    variants_on_allele = _finite(values.get("plausible_variants_on_allele")) or 1.0
    if variants_on_allele < 1:
        return None, "plausible_variants_on_allele must be at least one"
    return points / variants_on_allele, "ClinGen Table 3 co-segregation points"


def _pp1_pp4_card(
    criterion: str,
    strength: str,
    rows: list[dict[str, Any]],
    *,
    raw_points: float,
    allocated_points: int,
    combined_points: float,
    caveats: list[str] | None = None,
) -> EvidenceCard:
    source_ids = sorted({value for row in rows for value in _source_ids(row)})
    semantic_ids = sorted(
        {
            str(value)
            for row in rows
            for value in (
                row.get("observation_id"),
                (row.get("values") or {}).get("family_id")
                if isinstance(row.get("values"), dict)
                else None,
                (row.get("values") or {}).get("case_id")
                if isinstance(row.get("values"), dict)
                else None,
            )
            if value
        }
    )
    evidence_status = "rule_mapped" if strength else "not_met"
    return EvidenceCard(
        criterion=criterion,
        strength=strength or "not_met",
        evidence_status=evidence_status,
        source_label="Atomic phenotype and co-segregation observations",
        observed_facts={
            "records": rows,
            "raw_points": raw_points,
            "allocated_bayesian_points": allocated_points,
            "combined_pp1_pp4_points_capped": combined_points,
        },
        rule_basis=_PP1_PP4_REFERENCE,
        strength_source="clingen_svi_pp1_pp4_point_allocation",
        rule_source={
            "type": "versioned_svi",
            "rule_id": _PP1_PP4_RULE_ID,
            "version": _PP1_PP4_RULE_VERSION,
        },
        rule_id=_PP1_PP4_RULE_ID,
        rule_version=_PP1_PP4_RULE_VERSION,
        rule_reference=_PP1_PP4_REFERENCE,
        source_fact_ids=source_ids,
        source_case_ids=semantic_ids,
        correlation_keys={
            "family_id": [
                str((row.get("values") or {}).get("family_id"))
                for row in rows
                if isinstance(row.get("values"), dict)
                and (row.get("values") or {}).get("family_id")
            ],
            "case_id": [
                str((row.get("values") or {}).get("case_id"))
                for row in rows
                if isinstance(row.get("values"), dict)
                and (row.get("values") or {}).get("case_id")
            ],
        },
        verification_dimensions=_combined_dimensions(rows),
        caveats=list(caveats or []),
        provenance_chain=[
            f"{criterion}: {raw_points:g} raw points, {allocated_points:g} allocated points -> {strength or 'not met'}"
        ],
    )


def _phenotype_segregation_cards(
    observations: list[dict[str, Any]], inheritance_mode: str
) -> tuple[list[EvidenceCard], set[int]]:
    """Apply ClinGen's coupled PP1/PP4 heuristic and retain unresolved atoms."""
    cards: list[EvidenceCard] = []
    handled: set[int] = set()
    phenotype_rows: list[tuple[int, dict[str, Any], float]] = []
    segregation_rows: list[tuple[int, dict[str, Any], float]] = []
    homogeneous_locus = False

    for index, observation in enumerate(observations):
        observation_type = str(observation.get("observation_type") or "")
        if observation_type not in {"segregation", "phenotype_specificity"}:
            continue
        if error := _hard_error(observation):
            criterion = "PP1" if observation_type == "segregation" else "PP4"
            cards.append(
                _excluded_atom(
                    criterion,
                    observation,
                    error,
                    rule_reference=_PP1_PP4_REFERENCE,
                )
            )
            handled.add(index)
            continue
        values = (
            observation.get("values")
            if isinstance(observation.get("values"), dict)
            else {}
        )
        if observation_type == "phenotype_specificity":
            points = _finite(values.get("phenotype_points"))
            if points is None:
                points = _diagnostic_yield_points(values.get("diagnostic_yield"))
            if points is None:
                continue
            phenotype_rows.append((index, observation, max(0.0, points)))
            diagnostic_yield = _finite(values.get("diagnostic_yield"))
            if diagnostic_yield is not None and diagnostic_yield > 1:
                diagnostic_yield /= 100
            homogeneous_locus = homogeneous_locus or bool(
                values.get("locus_homogeneous") is True
                or (diagnostic_yield is not None and diagnostic_yield > 0.9)
            )
            handled.add(index)
            continue
        direction = str(
            values.get("segregation_direction") or values.get("direction") or ""
        ).casefold()
        if direction in {
            "nonsegregation",
            "non-segregation",
            "does not segregate",
            "benign",
        }:
            inheritance = str(
                values.get("inheritance_mode") or inheritance_mode or ""
            ).casefold()
            applicable = bool(
                _finite(values.get("affected_noncarrier_count"))
                and values.get("phenotype_confirmed") is True
                and values.get("penetrance_adequate") is True
                and not (
                    "recessive" in inheritance
                    and values.get("compound_heterozygous_proband") is True
                )
            )
            if applicable:
                card = _pp1_pp4_card(
                    "BS4",
                    "BS4",
                    [observation],
                    raw_points=-4.0,
                    allocated_points=-4,
                    combined_points=-4.0,
                )
            else:
                card = _generic_observation_card(observation)
                card.caveats.append(
                    "BS4 strict use requires an affected non-carrier with a confirmed phenotype, adequate penetrance, and an applicable inheritance configuration."
                )
            cards.append(card)
            handled.add(index)
            continue
        points, _basis = _segregation_points(observation, inheritance_mode)
        if points is None:
            continue
        segregation_rows.append((index, observation, points))
        handled.add(index)

    if not phenotype_rows and not segregation_rows:
        return cards, handled

    # Use the most specific phenotype observation once. Co-segregation points
    # may accumulate across independent families and are divided upstream when
    # multiple plausible variants share one allele.
    phenotype_row = (
        max(phenotype_rows, key=lambda row: row[2]) if phenotype_rows else None
    )
    phenotype_points = min(5.0, phenotype_row[2]) if phenotype_row else 0.0
    countable_segregation, uncounted_segregation = _independence_limited_rows(
        [(row[1], row[2]) for row in segregation_rows]
    )
    segregation_points = sum(row[1] for row in countable_segregation)
    segregation_caveats: list[str] = []
    if uncounted_segregation:
        segregation_caveats.append(
            "Additional families with unresolved independence were retained but not added to the co-segregation total."
        )
    if homogeneous_locus and segregation_points:
        segregation_caveats.append(
            "ClinGen PP1/PP4 guidance uses phenotype specificity alone for a highly homogeneous locus; positive segregation points were not added."
        )
        segregation_points = 0.0
    combined_points = min(5.0, phenotype_points + segregation_points)
    pp4_strength = _pathogenic_strength_for_points("PP4", phenotype_points)
    pp1_strength = _pathogenic_strength_for_points("PP1", segregation_points)

    # Convert the coupled total using Table 4. If discrete code strengths would
    # exceed the +5 point cap, retain the stronger evidence type and reduce the
    # other to Supporting.
    if _strength_points(pp4_strength) + _strength_points(pp1_strength) > 5:
        if phenotype_points >= segregation_points:
            pp1_strength = "PP1_Supporting"
        else:
            pp4_strength = "PP4_Supporting"

    if phenotype_row is not None:
        cards.append(
            _pp1_pp4_card(
                "PP4",
                pp4_strength,
                [phenotype_row[1]],
                raw_points=phenotype_points,
                allocated_points=_strength_points(pp4_strength),
                combined_points=combined_points,
            )
        )
    if segregation_rows:
        cards.append(
            _pp1_pp4_card(
                "PP1",
                pp1_strength,
                [row for row, _points in countable_segregation],
                raw_points=segregation_points,
                allocated_points=_strength_points(pp1_strength),
                combined_points=combined_points,
                caveats=segregation_caveats,
            )
        )
    return cards, handled


def clinical_evidence(
    inheritance_mode: str = "",
    de_novo_probands: list[dict] | None = None,
    pm3_observations: list[dict] | None = None,
    pm3_frequency_eligible: bool = False,
    clinical_observations: list[dict] | None = None,
) -> list[EvidenceCard]:
    """Evaluate each clinical atom independently; one bad record never erases peers."""
    inheritance_mode = str(inheritance_mode or "")
    cards: list[EvidenceCard] = []
    de_novo_items = [row for row in de_novo_probands or []]
    pm3_items = [row for row in pm3_observations or []]
    cards.extend(_de_novo_cards(de_novo_items, inheritance_mode))
    cards.extend(
        _pm3_cards(
            pm3_items,
            inheritance_mode=inheritance_mode,
            frequency_eligible=pm3_frequency_eligible,
        )
    )
    clinical_items = list(clinical_observations or [])
    coupled_cards, handled_indexes = _phenotype_segregation_cards(
        [row for row in clinical_items if isinstance(row, dict)], inheritance_mode
    )
    cards.extend(coupled_cards)
    valid_index = -1
    for observation in clinical_items:
        if not isinstance(observation, dict):
            cards.append(
                _excluded_atom(
                    "UNMAPPED",
                    {},
                    "clinical observation must be an object",
                    rule_reference="ACMG/AMP 2015",
                )
            )
            continue
        valid_index += 1
        if valid_index in handled_indexes:
            continue
        observation_type = str(observation.get("observation_type") or "")
        if observation_type in {"de_novo", "recessive_case"}:
            continue
        cards.append(
            _ps4_observation_card(observation)
            if observation_type in {"case_control", "case_series"}
            else _generic_observation_card(observation)
        )

    return cards


__all__ = ["clinical_evidence"]
