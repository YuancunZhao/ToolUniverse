"""Stable provenance contract for ACMG collector results."""

from __future__ import annotations

from tooluniverse.acmg import (
    compatibility,
    consequence_sources,
    literature_extractor,
    models,
    population,
    rule_catalog,
    vcep,
)
from tooluniverse.acmg.runtime_manifest import build_runtime_manifest, ruleset_hash


def test_ruleset_hash_is_stable_sha256():
    first = ruleset_hash()
    second = ruleset_hash()
    assert first == second
    assert len(first) == 64
    assert set(first) <= set("0123456789abcdef")


def test_ruleset_hash_tracks_candidate_preview_policy(monkeypatch):
    baseline = ruleset_hash()
    monkeypatch.setattr(
        models,
        "AUTOMATIC_EVIDENCE_STATUSES",
        frozenset({*models.AUTOMATIC_EVIDENCE_STATUSES, "fixture"}),
    )
    assert ruleset_hash() != baseline


def test_ruleset_hash_tracks_pm2_candidate_threshold(monkeypatch):
    baseline = ruleset_hash()
    monkeypatch.setattr(population, "PM2_RARE_OBSERVED_GLOBAL_AF_MAX", 0.0002)
    assert ruleset_hash() != baseline


def test_ruleset_hash_tracks_compatibility_policy_version(monkeypatch):
    baseline = ruleset_hash()
    monkeypatch.setattr(compatibility, "COMPATIBILITY_POLICY_VERSION", "fixture")
    assert ruleset_hash() != baseline


def test_ruleset_hash_tracks_identity_verification_policy(monkeypatch):
    baseline = ruleset_hash()
    monkeypatch.setitem(
        rule_catalog.IDENTITY_VERIFICATION_POLICY,
        "version",
        "fixture",
    )
    assert ruleset_hash() != baseline


def test_ruleset_hash_tracks_vcep_identity_and_moi_policies(monkeypatch):
    baseline = ruleset_hash()
    monkeypatch.setattr(vcep, "VCEP_ALLELE_MATCH_POLICY_VERSION", "fixture")
    assert ruleset_hash() != baseline

    baseline = ruleset_hash()
    monkeypatch.setattr(vcep, "VCEP_MOI_POLICY_VERSION", "fixture")
    assert ruleset_hash() != baseline


def test_ruleset_hash_tracks_scenario_and_literature_contracts(monkeypatch):
    baseline = ruleset_hash()
    monkeypatch.setattr(rule_catalog, "CSPEC_SCENARIO_POLICY_VERSION", "fixture")
    assert ruleset_hash() != baseline

    baseline = ruleset_hash()
    monkeypatch.setattr(
        rule_catalog, "USER_DECISION_SCENARIO_POLICY_VERSION", "fixture"
    )
    assert ruleset_hash() != baseline

    baseline = ruleset_hash()
    monkeypatch.setattr(
        literature_extractor,
        "TARGET_LINK_POLICY_VERSION",
        "fixture",
    )
    assert ruleset_hash() != baseline


def test_ruleset_hash_tracks_gp1ba_exposed_policies(monkeypatch):
    baseline = ruleset_hash()
    monkeypatch.setattr(population, "PM2_DECISION_POLICY_VERSION", "fixture")
    assert ruleset_hash() != baseline

    baseline = ruleset_hash()
    monkeypatch.setattr(
        consequence_sources,
        "CONSEQUENCE_CONFLICT_POLICY_VERSION",
        "fixture",
    )
    assert ruleset_hash() != baseline

    baseline = ruleset_hash()
    monkeypatch.setattr(rule_catalog, "MONDO_RESOLUTION_POLICY_VERSION", "fixture")
    assert ruleset_hash() != baseline


def test_runtime_manifest_indexes_applicable_dynamic_cspec():
    manifest = build_runtime_manifest(
        {
            "executable_contract": {
                "specification_id": "GN097",
                "version": "1.0.0",
                "content_hash": "sha256:fixture",
            }
        }
    )

    assert manifest["acmg_runtime_version"] == "evidence-automation-3.1"
    assert manifest["collector_schema_version"] == "2026-08-13-v3"
    assert manifest["tooluniverse_version"]
    assert manifest["applicable_cspec"] == [
        {
            "specification_id": "GN097",
            "version": "1.0.0",
            "content_hash": "sha256:fixture",
        }
    ]
