"""Population-frequency evidence rules (PM2, BA1 and BS1)."""

from __future__ import annotations

import math
from typing import Any

from .models import EvidenceCard


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
    callability_available = (
        callability_available is True or coverage_adequate is True
    )
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

    def above(value: float | None, threshold: float) -> bool:
        return value is not None and value > threshold

    if (
        gnomad_ac is None
        or gnomad_an is None
        or gnomad_an <= 0
        or not frequency_complete
    ):
        pm2_strength = "not_assessed"
        pm2_values = dict(audit_values)
        pm2_reason = "PM2: complete allele-frequency fields are required -> not_assessed"
    elif above(gnomad_af_popmax, 0.05) or above(gnomad_af_global, 0.05):
        pm2_strength = "not_met"
        pm2_values = dict(audit_values)
        pm2_reason = "PM2: frequency exceeds the BA1 threshold -> not_met"
    elif maximum_credible_af is not None and (
        above(gnomad_af_popmax, maximum_credible_af)
        or above(gnomad_af_global, maximum_credible_af)
    ):
        pm2_strength = "not_met"
        pm2_values = {
            **audit_values,
            "maximum_credible_af": maximum_credible_af,
        }
        pm2_reason = (
            "PM2: frequency exceeds the disease-specific maximum credible AF -> not_met"
        )
    elif gnomad_ac > 0:
        pm2_strength = "indeterminate"
        pm2_values = {
            **audit_values,
            "maximum_credible_af": maximum_credible_af,
        }
        pm2_reason = (
            "PM2: the variant is observed; recessive extremely-low-frequency use "
            "requires a disease-specific maximum credible AF"
        )
    elif gnomad_ac == 0:
        pm2_strength = "PM2_Supporting" if callability_available else "indeterminate"
        pm2_values = {
            **audit_values,
            "coverage_adequate": coverage_adequate,
            "callability_available": callability_available,
        }
        pm2_reason = (
            "PM2: absent from a population dataset with a versioned adequate-coverage "
            "assessment -> PM2_Supporting"
            if coverage_confirmed_adequate
            else "PM2: absence and site callability metrics are available, but no "
            "versioned adequacy threshold was applied -> review PM2_Supporting"
            if callability_available
            else "PM2: absence was observed but site callability was unavailable"
        )
    else:
        pm2_strength = "not_assessed"
        pm2_values = dict(audit_values)
        pm2_reason = "PM2: population observation could not be resolved -> not_assessed"
    cards.append(
        EvidenceCard(
            criterion="PM2",
            strength=pm2_strength,
            input_source=population_source or "gnomAD",
            input_values=pm2_values,
            clinvar_rule_applied="ClinGen SVI PM2 Recommendation v1.0",
            provenance_chain=[pm2_reason],
            proposal_status=(
                "suggested"
                if pm2_strength == "PM2_Supporting" and coverage_confirmed_adequate
                else "requires_user_review"
                if pm2_strength == "PM2_Supporting"
                else ""
            ),
            rule_verification=(
                "versioned_deterministic"
                if coverage_confirmed_adequate
                else "generic_svi"
            ),
            caveats=(
                []
                if coverage_confirmed_adequate or not callability_available
                else [
                    "Coverage metrics were returned, but coverage adequacy was not "
                    "established by a versioned policy."
                ]
            ),
            missing_requirements=(
                []
                if coverage_confirmed_adequate
                else ["versioned site-coverage adequacy assessment"]
                if callability_available
                else []
            ),
        )
    )
    if maximum_credible_af is not None:
        _mark_cspec_contract(cards[-1], rule_override, "PM2")

    high_ba1_frequency = above(gnomad_af_popmax, 0.05) or above(
        gnomad_af_global, 0.05
    )
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

    if maximum_credible_af is None:
        bs1_strength = "not_assessed"
        bs1_reason = "BS1: disease-specific maximum credible AF is missing"
    elif gnomad_an is None or gnomad_an <= 0 or gnomad_af_popmax is None:
        bs1_strength = "not_assessed"
        bs1_reason = "BS1: popmax allele frequency is missing"
    elif gnomad_af_popmax > maximum_credible_af:
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
                "maximum_credible_af": maximum_credible_af,
            },
            clinvar_rule_applied="ACMG/AMP 2015; disease-specific frequency required",
            provenance_chain=[bs1_reason],
        )
    )
    if maximum_credible_af is not None:
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
