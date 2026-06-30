#!/usr/bin/env python3
"""Direct python tests for the canonical ACMG finalizer."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[2] / "src/tooluniverse/acmg_gate/finalizer.py"
    spec = importlib.util.spec_from_file_location("acmg_finalizer_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_finalizer() -> None:
    finalizer = _load()
    base = {
        "validator_status": "PASS",
        "semantic_combiner_status": "PASS",
        "final_classification_allowed": True,
        "bundle_final_requested": True,
        "counted_evidence": [{"criterion": "PM2"}],
        "literature_ready": True,
    }
    assert finalizer.compute_finalization_gate(**base)["final_allowed"] is True
    for key, value in (
        ("validator_status", "FAIL"),
        ("semantic_combiner_status", "FAIL"),
        ("final_classification_allowed", False),
        ("bundle_final_requested", False),
        ("counted_evidence", []),
        ("literature_ready", False),
    ):
        args = dict(base)
        args[key] = value
        assert finalizer.compute_finalization_gate(**args)["final_allowed"] is False, key


if __name__ == "__main__":
    test_finalizer()
    print("PASS test_acmg_finalizer")
