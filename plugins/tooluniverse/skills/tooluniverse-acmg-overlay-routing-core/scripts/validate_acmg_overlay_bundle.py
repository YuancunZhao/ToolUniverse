#!/usr/bin/env python3
"""CLI wrapper for canonical ToolUniverse ACMG overlay bundle validator."""

from __future__ import annotations

from acmg_final_answer_guard import _load_canonical_module


_canonical = _load_canonical_module("validate_acmg_overlay_bundle")

PASS = _canonical.PASS
DRAFT_ONLY = _canonical.DRAFT_ONLY
FAIL = _canonical.FAIL
validate = _canonical.validate
validate_minimal = _canonical.validate_minimal
run_fixture_dir = _canonical.run_fixture_dir
main = _canonical.main


if __name__ == "__main__":
    raise SystemExit(main())
