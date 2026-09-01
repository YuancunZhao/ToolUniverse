"""Stable runtime and ruleset provenance for ACMG evidence results."""

from __future__ import annotations

import hashlib
from importlib import metadata
import json
from typing import Any
from pathlib import Path

from . import (
    compatibility,
    computational,
    consequence_sources,
    cspec,
    literature_extractor,
    models,
    population,
    pvs1,
    rule_catalog,
    spliceai,
    vcep,
)


ACMG_RUNTIME_VERSION = "evidence-automation-4.3"
COLLECTOR_SCHEMA_VERSION = "2026-08-31-v4.3"
OMIM_CONTEXT_POLICY_VERSION = "2026-08-21-v1"
UPSTREAM_BASE_COMMIT = "1aaaf00d1a9a91c21ae09d014fe19bf46fa82917"
BAYESIAN_PRIOR = 0.1


def _distribution_provenance() -> tuple[str, str, str]:
    """Return the installed VCS revision when distribution metadata provides it."""
    try:
        distribution = metadata.distribution("tooluniverse")
    except metadata.PackageNotFoundError:
        return "", "source_tree", ""
    package_path = str(Path(distribution.locate_file("tooluniverse")).resolve())
    direct_url = distribution.read_text("direct_url.json")
    if not direct_url:
        return "", "installed_distribution", package_path
    try:
        payload = json.loads(direct_url)
    except (TypeError, json.JSONDecodeError):
        return "", "installed_distribution", package_path
    vcs_info = payload.get("vcs_info")
    if isinstance(vcs_info, dict):
        return str(vcs_info.get("commit_id") or ""), "vcs", package_path
    directory_info = payload.get("dir_info")
    if isinstance(directory_info, dict) and directory_info.get("editable") is True:
        return "", "editable", package_path
    return "", "installed_distribution", package_path


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
            "computational_scope": computational.COMPUTATIONAL_SCOPE_POLICY_VERSION,
            "protein_mapping": rule_catalog.PROTEIN_MAPPING_POLICY_VERSION,
            "identity_verification": rule_catalog.IDENTITY_VERIFICATION_POLICY,
            "identity_provider_roles": rule_catalog.IDENTITY_PROVIDER_ROLES,
            "clinical_observation_case_identifier_priority": [
                "case_id",
                "proband_id",
                "observation_id",
            ],
            "automatic_policy_version": models.AUTOMATIC_EVIDENCE_POLICY_VERSION,
            "verified_policy_version": models.VERIFIED_EVIDENCE_POLICY_VERSION,
            "automatic_evidence_statuses": sorted(models.AUTOMATIC_EVIDENCE_STATUSES),
            "verified_evidence_statuses": sorted(models.VERIFIED_EVIDENCE_STATUSES),
            "non_evidence_strengths": sorted(models.NON_EVIDENCE_STRENGTHS),
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
            "evidence_aggregation_policy_version": (
                compatibility.EVIDENCE_AGGREGATION_POLICY_VERSION
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
            "pm2_decision_policy": {
                "version": population.PM2_DECISION_POLICY_VERSION,
                "order": [
                    "require_complete_af_ac_an",
                    "apply_unique_cspec_frequency_condition",
                    "apply_generic_or_fork_candidate_policy",
                    "assess_callability_only_when_ac_is_zero",
                ],
                "provider_failure_is_absence": False,
            },
            "gnomad_no_hit_policy": {
                "version": population.GNOMAD_NO_HIT_POLICY_VERSION,
                "transport_retry_version": (
                    population.GNOMAD_TRANSPORT_RETRY_POLICY_VERSION
                ),
                "requires_valid_variant_representation": True,
                "requires_same_site_callability": True,
                "no_hit_is_not_provider_failure": True,
                "representation_retry_only_after_no_hit": True,
                "frequency_query_count": 1,
                "effective_af_for_rule": 0.0,
            },
            "gene_resolution_policy": {
                "version": rule_catalog.GENE_RESOLUTION_POLICY_VERSION,
                "approved_symbol": "matched",
                "unique_previous_or_alias_symbol": "resolved_alias",
                "unique_transcript_gene_fallback": "corrected_from_transcript",
                "explicit_gene_transcript_conflict": "fail_closed",
            },
            "omim_context_policy": {
                "version": OMIM_CONTEXT_POLICY_VERSION,
                "source": "MARRVEL_get_omim_phenotypes",
                "review_only": True,
                "does_not_select_cspec": True,
            },
            "mondo_resolution_policy": {
                "version": rule_catalog.MONDO_RESOLUTION_POLICY_VERSION,
                "envelope": "terms",
                "exclude_obsolete": True,
                "exact_label_first": True,
                "unique_remaining_candidate": True,
            },
            "consequence_conflict_policy": {
                "version": consequence_sources.CONSEQUENCE_CONFLICT_POLICY_VERSION,
                "hard_conflicts": [
                    "build",
                    "allele",
                    "authoritative_selected_transcript_consequence",
                    "authoritative_selected_transcript_protein_change",
                ],
                "provider_roles": consequence_sources.CONSEQUENCE_PROVIDER_ROLES,
                "alternate_transcript_difference": "context_only",
                "empty_or_failed_provider": "nonblocking_visible_limitation",
                "authoritative_aggregation_disagreement": ("automatic_only_disputed"),
                "single_authoritative_selected_transcript": "verified_usable",
                "single_aggregation_selected_transcript": "automatic_only",
                "selection": "exact_refseq_then_mane_then_version_compatible",
                "majority_vote": False,
                "input_fallback_version": (
                    consequence_sources.INPUT_CONSEQUENCE_FALLBACK_POLICY_VERSION
                ),
                "deep_intronic_input": "automatic_only",
            },
            "spliceai_scope_policy": {
                "version": spliceai.SPLICEAI_SCOPE_POLICY_VERSION,
                "calculation_scope": "identity_selected_transcript_row",
                "provider_global_max": "context_only",
                "selected_row_claimed_max": "validated_against_four_delta_channels",
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
    revision, source_type, distribution_package = _distribution_provenance()
    package_location = str(Path(__file__).resolve().parents[1])
    return {
        "tooluniverse_version": package_version,
        "acmg_runtime_version": ACMG_RUNTIME_VERSION,
        "collector_schema_version": COLLECTOR_SCHEMA_VERSION,
        "upstream_base_commit": UPSTREAM_BASE_COMMIT,
        "ruleset_hash": ruleset_hash(),
        "distribution_vcs_commit": revision,
        "distribution_source_type": source_type,
        "package_location": package_location,
        "distribution_package_location": distribution_package,
        "package_matches_distribution": package_location == distribution_package,
        "applicable_cspec": _cspec_index(rule_context),
    }


__all__ = [
    "ACMG_RUNTIME_VERSION",
    "BAYESIAN_PRIOR",
    "COLLECTOR_SCHEMA_VERSION",
    "OMIM_CONTEXT_POLICY_VERSION",
    "UPSTREAM_BASE_COMMIT",
    "build_runtime_manifest",
    "ruleset_hash",
]
