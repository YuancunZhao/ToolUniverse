#!/usr/bin/env python3
"""CLI wrapper for canonical ToolUniverse ACMG entrypoint bypass checks."""

from __future__ import annotations

from acmg_final_answer_guard import _load_canonical_module


_canonical = _load_canonical_module("check_entrypoint_bypass_fixtures")

PASS = _canonical.PASS
FAIL = _canonical.FAIL
check_text = _canonical.check_text
run_fixture = _canonical.run_fixture
scan_static_gate_violations = _canonical.scan_static_gate_violations
scan_high_risk_tool_definitions = _canonical.scan_high_risk_tool_definitions
scan_gate_priority_implementation = _canonical.scan_gate_priority_implementation
main = _canonical.main


if __name__ == "__main__":
    raise SystemExit(main())
