#!/usr/bin/env python3
"""Direct python architecture checks for duplicated ACMG policy logic."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _iter_policy_files():
    for root_name in ("src/tooluniverse", "skills", "plugin/skills", "plugins/tooluniverse/skills", ".agents/skills", "scripts"):
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


if __name__ == "__main__":
    test_no_duplicate_policy_regex()
    test_no_wrong_skill_final_route()
    print("PASS test_acmg_no_duplicate_policy")
