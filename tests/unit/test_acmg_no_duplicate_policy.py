#!/usr/bin/env python3
"""Direct python architecture checks for duplicated ACMG policy logic."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _iter_policy_files():
    for root_name in ("src/tooluniverse", "skills", "plugin/skills", "plugins/tooluniverse/skills", "scripts"):
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".json", ".yaml"}:
                if "__pycache__" not in path.parts and "entrypoint_bypass_fixtures" not in path.parts:
                    yield path


def test_no_duplicate_policy_regex() -> None:
    allowed_regex_files = {
        ROOT / "src/tooluniverse/acmg_gate/final_label_detector.py",
        ROOT / "src/tooluniverse/acmg_gate/intent_detector.py",
        ROOT / "scripts/check_skill_duplicate_drift.py",
        ROOT / "src/tooluniverse/acmg_gate/check_entrypoint_bypass_fixtures.py",
    }
    forbidden_tokens = (
        "FULL" + "_FINAL_LABEL_RE",
        "CHINESE" + "_FINAL_LABEL_RE",
        "PAIRED" + "_ABBREVIATION_RE",
        "STANDALONE" + "_ABBREVIATION_RE",
        "_ACMG" + "_INTENT_TERMS",
        "_HGVS" + "_PATTERNS",
    )
    offenders = []
    for path in _iter_policy_files():
        if path in allowed_regex_files:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(token in text for token in forbidden_tokens):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, offenders


def test_no_wrong_skill_final_route() -> None:
    pattern = re.compile(
        r"(ACMG\s+(?:clinical\s+)?classification|pathogenicity\s+classification|final\s+ACMG)"
        r".*tooluniverse-variant-interpretation",
        re.I,
    )
    offenders = []
    for path in _iter_policy_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            lowered = line.lower()
            if "only for evidence intake" in lowered or "intake only" in lowered:
                continue
            if pattern.search(line):
                offenders.append(str(path.relative_to(ROOT)))
                break
    assert not offenders, offenders


def test_no_context_trigger_regex_in_gate_tool() -> None:
    """acmg_overlay_gate_tool.py must not define local context trigger regex."""
    gate_tool_path = ROOT / "src/tooluniverse/acmg_overlay_gate_tool.py"
    assert gate_tool_path.exists(), f"Missing: {gate_tool_path}"
    text = gate_tool_path.read_text(encoding="utf-8", errors="replace")
    # These trigger names may appear only in the group_to_criterion dict (for route
    # dispatching), not as regex patterns.  Check that no re.compile() wraps them.
    trigger_names = (
        "de_novo_ps2_pm6",
        "pp1_bs4_pp4_segregation",
        "pm3_in_trans",
        "phenotype_dependent_pp4",
        "benign_context_bs2",
        "benign_context_bp5",
    )
    # Find each trigger name and verify the surrounding line is a dict entry
    for name in trigger_names:
        idx = text.find(name)
        if idx == -1:
            continue
        # Extract the line containing the trigger name
        line_start = text.rfind("\n", 0, idx) + 1
        line_end = text.find("\n", idx)
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end]
        # Must be a dict key-value entry, not a re.compile()
        assert "re.compile" not in line, f"context trigger regex found in gate tool: {line.strip()!r}"
        assert '":' in line or '": ' in line or "' :" in line, f"unexpected trigger usage: {line.strip()!r}"


def test_no_criterion_helpers_in_harness_runner() -> None:
    """acmg_harness_runner.py must not define _criterion_to_group or _criterion_overlay."""
    runner_path = ROOT / "src/tooluniverse/acmg_harness_runner.py"
    assert runner_path.exists(), f"Missing: {runner_path}"
    text = runner_path.read_text(encoding="utf-8", errors="replace")
    assert "_criterion_to_group" not in text, "harness_runner defines _criterion_to_group"
    assert "_criterion_overlay" not in text, "harness_runner defines _criterion_overlay"


def test_packaged_acmg_wrapper_scripts_are_in_package_data() -> None:
    """pyproject.toml must package ACMG wrapper scripts used at runtime."""
    pyproject_path = ROOT / "pyproject.toml"
    assert pyproject_path.exists(), f"Missing: {pyproject_path}"
    text = pyproject_path.read_text(encoding="utf-8", errors="replace")
    assert '"data/acmg_overlay_gate/scripts/*"' in text


if __name__ == "__main__":
    test_no_duplicate_policy_regex()
    test_no_wrong_skill_final_route()
    test_no_context_trigger_regex_in_gate_tool()
    test_no_criterion_helpers_in_harness_runner()
    test_packaged_acmg_wrapper_scripts_are_in_package_data()
    print("PASS test_acmg_no_duplicate_policy")
