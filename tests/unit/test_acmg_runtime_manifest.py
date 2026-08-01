"""Stable provenance contract for ACMG collector results."""

from __future__ import annotations

from tooluniverse.acmg.runtime_manifest import build_runtime_manifest, ruleset_hash


def test_ruleset_hash_is_stable_sha256():
    first = ruleset_hash()
    second = ruleset_hash()
    assert first == second
    assert len(first) == 64
    assert set(first) <= set("0123456789abcdef")


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

    assert manifest["acmg_runtime_version"] == "evidence-only-1"
    assert manifest["collector_schema_version"] == "2026-08-01"
    assert manifest["tooluniverse_version"]
    assert manifest["applicable_cspec"] == [
        {
            "specification_id": "GN097",
            "version": "1.0.0",
            "content_hash": "sha256:fixture",
        }
    ]
