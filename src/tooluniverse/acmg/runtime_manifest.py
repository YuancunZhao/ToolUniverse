"""Stable runtime and ruleset provenance for ACMG evidence results."""

from __future__ import annotations

import hashlib
from importlib import metadata
import json
from typing import Any

from . import (
    compatibility,
    cspec,
    literature_extractor,
    models,
    population,
    pvs1,
    rule_catalog,
    vcep,
)


ACMG_RUNTIME_VERSION = "evidence-automation-3"
COLLECTOR_SCHEMA_VERSION = "2026-08-09-v3"
UPSTREAM_BASE_COMMIT = "089eb8e6308fc64ae5af3de4bfbec32b5cf07b61"
BAYESIAN_PRIOR = 0.1


def _distribution_provenance() -> tuple[str, str]:
    """Return the installed VCS revision when distribution metadata provides it."""
    try:
        distribution = metadata.distribution("tooluniverse")
    except metadata.PackageNotFoundError:
        return "", "source_tree"
    direct_url = distribution.read_text("direct_url.json")
    if not direct_url:
        return "", "installed_distribution"
    try:
        payload = json.loads(direct_url)
    except (TypeError, json.JSONDecodeError):
        return "", "installed_distribution"
    vcs_info = payload.get("vcs_info")
    if isinstance(vcs_info, dict):
        return str(vcs_info.get("commit_id") or ""), "vcs"
    directory_info = payload.get("dir_info")
    if isinstance(directory_info, dict) and directory_info.get("editable") is True:
        return "", "editable"
    return "", "installed_distribution"


def _ruleset_payload() -> dict[str, Any]:
    generic_odds = [
        {
            "direction": direction,
            "strength": strength,
            "odds": odds,
        }
        for (direction, strength), odds in sorted(
            rule_catalog._GENERIC_TAVTIGIAN_ODDS.items()
        )
    ]
    return {
        "criterion_rules": rule_catalog.RULE_CATALOG,
        "criterion_use_matrix": rule_catalog.criterion_use_matrix(),
        "consequence_policies": rule_catalog.CONSEQUENCE_POLICIES,
        "spliceai_rule": rule_catalog.SPLICEAI_RULE,
        "pvs1_rule": {
            "rule_id": pvs1.RULE_ID,
            "version": pvs1.RULE_VERSION,
            "reference": pvs1.RULE_REFERENCE,
        },
        "generic_tavtigian_odds": generic_odds,
        "bayesian_prior": BAYESIAN_PRIOR,
        "evidence_calculation_policy": {
            "automatic_policy_version": models.AUTOMATIC_EVIDENCE_POLICY_VERSION,
            "verified_policy_version": models.VERIFIED_EVIDENCE_POLICY_VERSION,
            "automatic_evidence_statuses": sorted(models.AUTOMATIC_EVIDENCE_STATUSES),
            "verified_evidence_statuses": sorted(models.VERIFIED_EVIDENCE_STATUSES),
            "hard_exclusion_dimensions": {
                key: sorted(values)
                for key, values in sorted(models.HARD_EXCLUSION_DIMENSIONS.items())
            },
            "automatic_requires_known_source_facts": True,
            "verified_requires_strict_source_facts": True,
            "requires_valid_criterion_strength": True,
            "compatibility_policy_version": (
                compatibility.COMPATIBILITY_POLICY_VERSION
            ),
            "pm2_rare_observed_candidate": {
                "policy_id": population.PM2_RARE_OBSERVED_CANDIDATE_POLICY_ID,
                "version": (population.PM2_RARE_OBSERVED_CANDIDATE_POLICY_VERSION),
                "requires_ac_greater_than": 0,
                "global_af_max": population.PM2_RARE_OBSERVED_GLOBAL_AF_MAX,
                "popmax_af_max_or_missing": (
                    population.PM2_RARE_OBSERVED_POPMAX_AF_MAX
                ),
                "requires_missing_disease_specific_mcaf": True,
                "deterministic_svi_threshold": False,
            },
            "literature_extractor": {
                "id": literature_extractor.EXTRACTOR_ID,
                "version": literature_extractor.EXTRACTOR_VERSION,
                "target_link_policy_version": (
                    literature_extractor.TARGET_LINK_POLICY_VERSION
                ),
                "minimum_fact_requirements": (
                    literature_extractor.MINIMUM_FACT_REQUIREMENTS
                ),
            },
            "cspec_rule_parser_version": cspec.CSPEC_RULE_PARSER_VERSION,
            "cspec_scenario_policy_version": (
                rule_catalog.CSPEC_SCENARIO_POLICY_VERSION
            ),
            "user_decision_scenario_policy_version": (
                rule_catalog.USER_DECISION_SCENARIO_POLICY_VERSION
            ),
            "vcep_assertion_parser_version": vcep.VCEP_ASSERTION_PARSER_VERSION,
            "vcep_allele_match_policy": {
                "version": vcep.VCEP_ALLELE_MATCH_POLICY_VERSION,
                "exact_match_tiers": vcep.VCEP_ALLELE_MATCH_TIERS,
                "rsid_alone": "lead_only",
                "protein_hgvs_alone": "lead_only",
            },
            "vcep_moi_policy": {
                "version": vcep.VCEP_MOI_POLICY_VERSION,
                "aliases": {
                    key: sorted(values)
                    for key, values in sorted(vcep.VCEP_MOI_ALIASES.items())
                },
            },
            "vcep_applied_criterion_policy": {
                "structured_applied_criteria_only": True,
                "negative_statuses": sorted(vcep.VCEP_NEGATIVE_APPLIED_STATUSES),
                "free_text_mentions_are_leads_only": True,
            },
        },
    }


def ruleset_hash() -> str:
    canonical = json.dumps(
        _ruleset_payload(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _cspec_index(rule_context: dict[str, Any] | None) -> list[dict[str, str]]:
    context = rule_context if isinstance(rule_context, dict) else {}
    candidates = (
        context.get("applicable_specification"),
        context.get("executable_contract"),
    )
    indexed: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        row = {
            "specification_id": str(
                candidate.get("specification_id")
                or candidate.get("spec_id")
                or candidate.get("id")
                or ""
            ),
            "version": str(candidate.get("version") or ""),
            "content_hash": str(candidate.get("content_hash") or ""),
        }
        identity = (
            row["specification_id"],
            row["version"],
            row["content_hash"],
        )
        if any(identity) and identity not in seen:
            seen.add(identity)
            indexed.append(row)
    return indexed


def build_runtime_manifest(
    rule_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        package_version = metadata.version("tooluniverse")
    except metadata.PackageNotFoundError:
        package_version = "0.0.0+source"
    revision, source_type = _distribution_provenance()
    return {
        "tooluniverse_version": package_version,
        "acmg_runtime_version": ACMG_RUNTIME_VERSION,
        "collector_schema_version": COLLECTOR_SCHEMA_VERSION,
        "upstream_base_commit": UPSTREAM_BASE_COMMIT,
        "ruleset_hash": ruleset_hash(),
        "distribution_vcs_commit": revision,
        "distribution_source_type": source_type,
        "applicable_cspec": _cspec_index(rule_context),
    }


__all__ = [
    "ACMG_RUNTIME_VERSION",
    "BAYESIAN_PRIOR",
    "COLLECTOR_SCHEMA_VERSION",
    "UPSTREAM_BASE_COMMIT",
    "build_runtime_manifest",
    "ruleset_hash",
]
