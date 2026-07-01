#!/usr/bin/env python3
"""Integration tests for the ACMG overlay pipeline — focus on guard, semantic, and context."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "tooluniverse-acmg-overlay-routing-core" / "scripts"


def _run_stdin(script_name: str, payload: dict) -> dict:
    """Run a script that accepts JSON via stdin."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script_name)],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.stdout.strip():
        return json.loads(proc.stdout)
    return {"error": proc.stderr, "exit": proc.returncode}


def _run_file_input(script_name: str, payload: dict) -> dict:
    """Run a script that accepts a JSON file as positional argument."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False)
        tmp_path = handle.name
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / script_name), tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"error": proc.stderr, "exit": proc.returncode}
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass


# ── Tests ────────────────────────────────────────────────────────────

def test_guard_blocks_final_label_without_pass():
    """Final answer guard blocks text with final labels when gates fail."""
    text = "Final classification: Pathogenic. This variant is pathogenic."
    result = _run_stdin(
        "acmg_final_answer_guard.py",
        {
            "answer": text,
            "validation": {
                "validator_status": "DRAFT_ONLY",
                "semantic_combiner_status": "FAIL",
                "final_classification_allowed": False,
            },
        },
    )
    status = result.get("status") or result.get("guard_status")
    assert status in ("BLOCK", "BLOCKED"), f"Guard should block: {result}"
    print("  PASS: guard blocks final label without gates")


def test_guard_allows_safe_text():
    """Safe text without final labels passes through."""
    text = "LP score is 0.8. Population frequency is 0.001 in gnomAD."
    result = _run_stdin(
        "acmg_final_answer_guard.py",
        {
            "answer": text,
            "validation": {
                "validator_status": "PASS",
                "semantic_combiner_status": "PASS",
                "final_classification_allowed": True,
            },
        },
    )
    status = result.get("status") or result.get("guard_status")
    assert status == "PASS", f"Guard should allow: {result}"
    print("  PASS: guard allows safe text")


def test_guard_blocks_chinese_final_label():
    """Guard must block Chinese final labels without gates."""
    text = "最终分类：致病。该变异为可能致病。"
    result = _run_stdin(
        "acmg_final_answer_guard.py",
        {
            "answer": text,
            "validation": {
                "validator_status": "DRAFT_ONLY",
                "semantic_combiner_status": "FAIL",
                "final_classification_allowed": False,
            },
        },
    )
    status = result.get("status") or result.get("guard_status")
    assert status in ("BLOCK", "BLOCKED"), f"Guard should block Chinese: {result}"
    print("  PASS: guard blocks Chinese final labels")


def test_semantic_combiner_rejects_unsupported():
    """Semantic combiner rejects Pathogenic with only PM2_Supporting."""
    result = _run_file_input(
        "acmg_semantic_combiner.py",
        {
            "acmg_assessment_bundle": {
                "classification": "Pathogenic",
                "classification_status": "final classification",
                "final_classification_allowed": True,
                "compatibility_resolution": {
                    "current_counted_evidence_resolved": [
                        {"criterion": "PM2", "strength": "supporting"},
                    ],
                },
            },
        },
    )
    assert result.get("semantic_combiner_status") == "FAIL", f"Semantic: {result}"
    assert result.get("computed_classification") == "VUS", f"Semantic: {result}"
    print("  PASS: semantic combiner rejects PM2-only Pathogenic")


def test_semantic_combiner_accepts_ba1_benign():
    """Semantic combiner accepts Benign with BA1 standalone."""
    result = _run_file_input(
        "acmg_semantic_combiner.py",
        {
            "acmg_assessment_bundle": {
                "classification": "Benign",
                "classification_status": "final classification",
                "final_classification_allowed": True,
                "compatibility_resolution": {
                    "current_counted_evidence_resolved": [
                        {"criterion": "BA1", "strength": "standalone"},
                    ],
                },
            },
        },
    )
    assert result.get("semantic_combiner_status") == "PASS", f"Semantic: {result}"
    assert result.get("computed_classification") == "Benign", f"Semantic: {result}"
    print("  PASS: semantic combiner accepts BA1 Benign")


def test_context_triggers_non_counted():
    """Context triggers create non-counted routes from user context."""
    result = _run_stdin(
        "acmg_context_triggers.py",
        {
            "family_context": "trio with de novo variant, parents negative",
            "phenotype_context": "HPO:0001250 seizure, developmental delay",
            "disease_context": "early infantile epileptic encephalopathy",
            "inheritance_context": "autosomal dominant",
        },
    )
    routes = result.get("route_candidates", [])
    assert len(routes) > 0, f"No routes: {result}"
    for route in routes:
        assert route.get("counted") is False, f"Route should be non-counted: {route}"
        assert route.get("source_type") == "user_context", f"Source: {route}"
    print(f"  PASS: {len(routes)} context routes, all counted=False")


def test_validator_fixtures_integration():
    """Validator processes all fixtures correctly (smoke test)."""
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "validate_acmg_overlay_bundle.py"),
            "--fixtures",
            str(SCRIPTS.parent / "evals" / "validator_fixtures"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    result = json.loads(proc.stdout)
    assert result["status"] == "PASS", f"Validator fixtures: {result['status']}"
    assert result["fixture_count"] >= 30, f"Fixture count: {result['fixture_count']}"
    failures = sum(1 for r in result["results"] if not r["ok"])
    assert failures == 0, f"{failures} fixture failures"
    print(f"  PASS: validator {result['fixture_count']} fixtures, 0 failures")


def test_bypass_fixtures_integration():
    """Entrypoint bypass checker processes all fixtures correctly (smoke test)."""
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "check_entrypoint_bypass_fixtures.py"),
            "--fixtures",
            str(SCRIPTS.parent / "evals" / "entrypoint_bypass_fixtures"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    result = json.loads(proc.stdout)
    assert result["status"] == "PASS", f"Bypass fixtures: {result['status']}"
    assert result["fixture_count"] >= 20, f"Fixture count: {result['fixture_count']}"
    failures = sum(1 for r in result["results"] if not r["ok"])
    assert failures == 0, f"{failures} bypass fixture failures"
    print(f"  PASS: bypass {result['fixture_count']} fixtures, 0 failures")


if __name__ == "__main__":
    test_guard_blocks_final_label_without_pass()
    test_guard_allows_safe_text()
    test_guard_blocks_chinese_final_label()
    test_semantic_combiner_rejects_unsupported()
    test_semantic_combiner_accepts_ba1_benign()
    test_context_triggers_non_counted()
    test_validator_fixtures_integration()
    test_bypass_fixtures_integration()
    print("PASS test_acmg_pipeline")
