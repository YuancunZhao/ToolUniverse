"""Population-frequency evidence rules (PM2, BA1 and BS1)."""

from __future__ import annotations

import math
import operator
from typing import Any

from .models import EvidenceCard


PM2_RARE_OBSERVED_CANDIDATE_POLICY_ID = "tooluniverse-pm2-rare-observed-candidate"
PM2_RARE_OBSERVED_CANDIDATE_POLICY_VERSION = "2026-08-08-v3"
PM2_RARE_OBSERVED_GLOBAL_AF_MAX = 0.0001
PM2_RARE_OBSERVED_POPMAX_AF_MAX = 0.001
PM2_DECISION_POLICY_VERSION = "2026-08-13-v3"
_FREQUENCY_OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def population_evidence(
    gnomad_af_global: float | None = None,
    gnomad_af_popmax: float | None = None,
    gnomad_ac: int | None = None,
    gnomad_an: int | None = None,
    coverage_adequate: bool | None = None,
    callability_available: bool | None = None,
    maximum_credible_af: float | None = None,
    ba1_exception: bool = False,
    ba1_exception_verified: bool = False,
    population_source: str = "gnomAD",
    population_details: dict[str, Any] | None = None,
    callability_metrics: dict[str, Any] | None = None,
    rule_override: dict[str, Any] | None = None,
) -> list[EvidenceCard]:
    """Evaluate population evidence without combining fields across providers."""
    gnomad_af_global = _finite_number(gnomad_af_global)
    gnomad_af_popmax = _finite_number(gnomad_af_popmax)
    gnomad_ac = _finite_number(gnomad_ac)
    gnomad_an = _finite_number(gnomad_an)
    maximum_credible_af = _finite_number(maximum_credible_af)
    ba1_exception = ba1_exception is True
    ba1_exception_verified = ba1_exception_verified is True
    coverage_confirmed_adequate = coverage_adequate is True
    callability_available = callability_available is True or coverage_adequate is True
    cards: list[EvidenceCard] = []
    frequency_complete = gnomad_af_global is not None
    audit_values = {
        "ac": gnomad_ac,
        "an": gnomad_an,
        "af_global": gnomad_af_global,
        "af_popmax": gnomad_af_popmax,
        "population_details": dict(population_details or {}),
        "callability_metrics": dict(callability_metrics or {}),
    }
    rare_observed_candidate = bool(
        gnomad_ac is not None
        and gnomad_ac > 0
        and gnomad_af_global is not None
        and gnomad_af_global <= PM2_RARE_OBSERVED_GLOBAL_AF_MAX
        and (
            gnomad_af_popmax is None
            or gnomad_af_popmax <= PM2_RARE_OBSERVED_POPMAX_AF_MAX
        )
        and maximum_credible_af is None
    )

    def above(value: float | None, threshold: float) -> bool:
        return value is not None and value > threshold

    complete = bool(
        gnomad_ac is not None
        and gnomad_an is not None
        and gnomad_an > 0
        and frequency_complete
    )
    observed_frequency = (
        max(
            value for value in (gnomad_af_global, gnomad_af_popmax) if value is not None
        )
        if frequency_complete
        else None
    )
    cspec_pm2 = (
        (rule_override.get("criteria") or {}).get("PM2")
        if isinstance(rule_override, dict)
        and isinstance(rule_override.get("criteria"), dict)
        else None
    )
    cspec_bs1 = (
        (rule_override.get("criteria") or {}).get("BS1")
        if isinstance(rule_override, dict)
        and isinstance(rule_override.get("criteria"), dict)
        else None
    )
    bs1_maximum_credible_af = (
        _finite_number(cspec_bs1.get("maximum_credible_af"))
        if isinstance(cspec_bs1, dict)
        else None
    )
    if bs1_maximum_credible_af is None:
        bs1_maximum_credible_af = maximum_credible_af
    cspec_frequency_threshold = (
        _finite_number(cspec_pm2.get("population_frequency_threshold"))
        if isinstance(cspec_pm2, dict)
        else None
    )
    if cspec_frequency_threshold is None and isinstance(cspec_pm2, dict):
        cspec_frequency_threshold = _finite_number(cspec_pm2.get("maximum_credible_af"))
    cspec_frequency_operator = (
        str(cspec_pm2.get("operator") or "<=") if isinstance(cspec_pm2, dict) else "<="
    )
    has_cspec_threshold = bool(
        isinstance(cspec_pm2, dict)
        and cspec_frequency_threshold is not None
        and cspec_frequency_operator in _FREQUENCY_OPERATORS
    )
    cspec_strength = (
        str(cspec_pm2.get("strength") or "") if isinstance(cspec_pm2, dict) else ""
    )
    if not cspec_strength and isinstance(cspec_pm2, dict):
        allowed = [
            str(value)
            for value in cspec_pm2.get("allowed_strengths") or []
            if str(value).startswith("PM2")
        ]
        cspec_strength = allowed[0] if len(allowed) == 1 else ""
    cspec_strength = cspec_strength or "PM2_Supporting"
    pm2_values = {
        **audit_values,
        "maximum_credible_af": maximum_credible_af,
        "coverage_adequate": coverage_adequate,
        "callability_available": callability_available,
    }
    caveats: list[str] = []
    missing_requirements: list[str] = []
    if not complete:
        pm2_strength = "not_assessed"
        pm2_status = "excluded"
        condition = "unresolved"
        pm2_reason = "PM2: complete AF, AC, and positive AN are required"
        missing_requirements = ["complete AF, AC, and AN"]
    elif has_cspec_threshold and gnomad_ac > 0:
        comparison = _FREQUENCY_OPERATORS[cspec_frequency_operator]
        if observed_frequency is not None and comparison(
            observed_frequency, cspec_frequency_threshold
        ):
            pm2_strength = cspec_strength
            pm2_status = "rule_mapped"
            condition = "condition_met"
            pm2_reason = (
                "PM2: observed frequency satisfies the applicable CSpec maximum "
                "credible allele-frequency condition"
            )
        else:
            pm2_strength = "not_met"
            pm2_status = "not_met"
            condition = "condition_not_met"
            pm2_reason = (
                "PM2: observed frequency exceeds the applicable CSpec maximum "
                "credible allele-frequency condition"
            )
    elif gnomad_ac > 0:
        condition = "unresolved"
        missing_requirements = ["disease-specific maximum credible allele frequency"]
        if rare_observed_candidate:
            pm2_strength = "PM2_Supporting"
            pm2_status = "source_backed_candidate"
            pm2_reason = (
                "PM2: observed frequency passes the fork review-only rare-variant "
                "candidate filter; no disease-specific threshold was available"
            )
            caveats.append(
                "The fork AF filters route a review candidate because a "
                "disease-specific maximum credible allele frequency is missing; "
                "they are not a deterministic ClinGen SVI PM2 threshold."
            )
        else:
            pm2_strength = "indeterminate"
            pm2_status = "excluded"
            pm2_reason = (
                "PM2: the variant is observed and no disease-specific maximum "
                "credible allele frequency was available"
            )
    elif gnomad_ac == 0:
        condition = "condition_met" if coverage_confirmed_adequate else "unresolved"
        pm2_strength = "PM2_Supporting" if callability_available else "indeterminate"
        pm2_status = (
            "rule_mapped"
            if coverage_confirmed_adequate
            else "source_backed_candidate"
            if callability_available
            else "excluded"
        )
        pm2_reason = (
            "PM2: absence is supported by a versioned adequate-coverage assessment"
            if coverage_confirmed_adequate
            else "PM2: absence and raw callability metrics are available, but no "
            "versioned adequacy policy was applied"
            if callability_available
            else "PM2: absence was reported but site callability was unavailable"
        )
        if callability_available and not coverage_confirmed_adequate:
            caveats.append(
                "Raw coverage/callability values are shown without inventing an "
                "adequacy threshold."
            )
            missing_requirements = ["versioned site-coverage adequacy assessment"]
        elif not callability_available:
            missing_requirements = ["site callability metrics"]
    else:
        pm2_strength = "not_assessed"
        pm2_status = "excluded"
        condition = "unresolved"
        pm2_reason = "PM2: population observation could not be resolved"
        missing_requirements = ["resolved population observation"]

    if has_cspec_threshold and gnomad_ac > 0:
        strength_source = "dynamic_cspec"
        rule_source = {
            "type": "dynamic_cspec_structured",
            "rule_id": str(rule_override.get("rule_id") or ""),
            "version": str(rule_override.get("version") or ""),
            "specification_id": str(rule_override.get("specification_id") or ""),
        }
    elif coverage_confirmed_adequate:
        strength_source = "clingen_svi_pm2_v1"
        rule_source = {
            "type": "versioned_svi",
            "rule_id": "clingen-svi-pm2",
            "version": "1.0",
        }
    else:
        strength_source = PM2_RARE_OBSERVED_CANDIDATE_POLICY_ID
        rule_source = {
            "type": "fork_candidate_policy",
            "rule_id": PM2_RARE_OBSERVED_CANDIDATE_POLICY_ID,
            "version": PM2_RARE_OBSERVED_CANDIDATE_POLICY_VERSION,
        }
    applied_rule_label = (
        "ClinGen CSpec population-frequency condition"
        if has_cspec_threshold and gnomad_ac > 0
        else "ClinGen SVI PM2 Recommendation v1.0"
    )
    cards.append(
        EvidenceCard(
            criterion="PM2",
            strength=pm2_strength,
            input_source=population_source or "gnomAD",
            input_values=pm2_values,
            clinvar_rule_applied=applied_rule_label,
            rule_basis=(
                "Applicable released CSpec population-frequency condition."
                if has_cspec_threshold and gnomad_ac > 0
                else "Fork review-only rare-observed PM2 candidate policy "
                f"{PM2_RARE_OBSERVED_CANDIDATE_POLICY_VERSION}; its AF filters "
                "are not a deterministic ClinGen SVI PM2 threshold."
                if rare_observed_candidate
                else ""
            ),
            provenance_chain=[pm2_reason],
            evidence_status=pm2_status,
            strength_source=strength_source,
            rule_source=rule_source,
            caveats=caveats,
            missing_requirements=missing_requirements,
            rule_evaluation={
                "observed": {
                    "af_global": gnomad_af_global,
                    "af_popmax": gnomad_af_popmax,
                    "ac": gnomad_ac,
                    "an": gnomad_an,
                },
                "rule_source": rule_source,
                "threshold": cspec_frequency_threshold,
                "comparison": (
                    cspec_frequency_operator
                    if has_cspec_threshold and gnomad_ac > 0
                    else ""
                ),
                "threshold_type": (
                    "cspec_population_frequency"
                    if has_cspec_threshold and gnomad_ac > 0
                    else "fork_candidate_filter"
                    if rare_observed_candidate
                    else ""
                ),
                "status": condition,
                "primary_reason": pm2_reason,
                "caveats": list(caveats),
            },
            verification_dimensions={
                "extraction_status": (
                    "structured"
                    if coverage_confirmed_adequate
                    or (has_cspec_threshold and gnomad_ac > 0)
                    else "unresolved"
                ),
                "version_status": (
                    "versioned"
                    if coverage_confirmed_adequate
                    or (has_cspec_threshold and gnomad_ac > 0)
                    else "unversioned"
                ),
            },
        )
    )
    if has_cspec_threshold:
        _mark_cspec_contract(cards[-1], rule_override, "PM2")

    high_ba1_frequency = above(gnomad_af_popmax, 0.05) or above(gnomad_af_global, 0.05)
    if high_ba1_frequency and not ba1_exception_verified:
        ba1_strength = "not_assessed"
        ba1_reason = (
            "BA1: frequency exceeds 5%, but exception status was not verified "
            "against a versioned reviewed catalog"
        )
    elif ba1_exception and ba1_exception_verified:
        ba1_strength = "not_applicable"
        ba1_reason = "BA1: verified exception -> not_applicable"
    elif not frequency_complete:
        ba1_strength = "not_assessed"
        ba1_reason = "BA1: allele-frequency fields are incomplete"
    elif high_ba1_frequency:
        ba1_strength = "BA1"
        ba1_reason = "BA1: global or popmax AF exceeds 5%"
    else:
        ba1_strength = "not_met"
        ba1_reason = "BA1: frequency is below 5%"
    cards.append(
        EvidenceCard(
            criterion="BA1",
            strength=ba1_strength,
            input_source=f"{population_source or 'gnomAD'} / ClinGen BA1 exception catalog",
            input_values={
                **audit_values,
                "af_global": gnomad_af_global,
                "af_popmax": gnomad_af_popmax,
                "ba1_exception": ba1_exception,
                "ba1_exception_verified": ba1_exception_verified,
            },
            clinvar_rule_applied="ACMG/AMP 2015; ClinGen BA1 exception guidance",
            provenance_chain=[ba1_reason],
        )
    )
    if ba1_exception_verified:
        _mark_cspec_contract(cards[-1], rule_override, "BA1")

    if bs1_maximum_credible_af is None:
        bs1_strength = "not_assessed"
        bs1_reason = "BS1: disease-specific maximum credible AF is missing"
    elif gnomad_an is None or gnomad_an <= 0 or gnomad_af_popmax is None:
        bs1_strength = "not_assessed"
        bs1_reason = "BS1: popmax allele frequency is missing"
    elif gnomad_af_popmax > bs1_maximum_credible_af:
        bs1_strength = "BS1"
        bs1_reason = "BS1: popmax AF exceeds the disease-specific maximum credible AF"
    else:
        bs1_strength = "not_met"
        bs1_reason = "BS1: popmax AF does not exceed the disease-specific threshold"
    cards.append(
        EvidenceCard(
            criterion="BS1",
            strength=bs1_strength,
            input_source=f"{population_source or 'gnomAD'} and disease-specific frequency model",
            input_values={
                **audit_values,
                "af_popmax": gnomad_af_popmax,
                "an": gnomad_an,
                "maximum_credible_af": bs1_maximum_credible_af,
            },
            clinvar_rule_applied="ACMG/AMP 2015; disease-specific frequency required",
            provenance_chain=[bs1_reason],
        )
    )
    if bs1_maximum_credible_af is not None:
        _mark_cspec_contract(cards[-1], rule_override, "BS1")
    return cards


def _mark_cspec_contract(
    card: EvidenceCard,
    rule_override: dict[str, Any] | None,
    criterion: str,
) -> None:
    if not isinstance(rule_override, dict):
        return
    criteria = rule_override.get("criteria")
    if not isinstance(criteria, dict) or not isinstance(criteria.get(criterion), dict):
        return
    card.input_values["cspec_contract_applied"] = {
        "specification_id": rule_override.get("specification_id"),
        "version": rule_override.get("version"),
    }


__all__ = ["population_evidence"]
