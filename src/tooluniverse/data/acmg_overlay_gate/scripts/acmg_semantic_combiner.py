#!/usr/bin/env python3
"""CLI wrapper for canonical ToolUniverse ACMG semantic combiner."""

from __future__ import annotations

from acmg_final_answer_guard import _load_canonical_module


_canonical = _load_canonical_module("semantic_combiner")

PASS = _canonical.PASS
FAIL = _canonical.FAIL
NOT_APPLICABLE = _canonical.NOT_APPLICABLE
normalize_label = _canonical.normalize_label
parse_evidence = _canonical.parse_evidence
compute_classification = _canonical.compute_classification
validate_bundle_semantics = _canonical.validate_bundle_semantics
main = _canonical.main


if __name__ == "__main__":
    raise SystemExit(main())
