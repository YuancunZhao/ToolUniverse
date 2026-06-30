#!/usr/bin/env python3
"""Validate overlay_registry.yaml coverage: every covered_criteria entry must have a
corresponding overlay skill under skills/ with a valid SKILL.md.

Zero external dependencies — uses only stdlib regex to parse YAML keys.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "skills" / "tooluniverse-acmg-overlay-routing-core" / "overlay_registry.yaml"
SKILLS_ROOT = ROOT / "skills"


def parse_registry_entries(text: str) -> list[dict]:
    """Extract overlay entries that have covered_criteria from YAML text."""
    # Split into overlay blocks (start with '- criterion_group:')
    blocks = re.split(r"\n(?=- )", text)
    entries: list[dict] = []
    for block in blocks:
        # Only process blocks with covered_criteria
        if "covered_criteria:" not in block:
            continue
        entry: dict = {}
        # Extract overlay_skill
        m = re.search(r"overlay_skill:\s*(\S+)", block)
        if m:
            entry["overlay_skill"] = m.group(1)
        # Extract criterion_group
        m = re.search(r"criterion_group:\s*(\S+)", block)
        if m:
            entry["criterion_group"] = m.group(1)
        # Extract covered_criteria (may be list)
        criteria_section = re.search(r"covered_criteria:\s*\n((?:\s+-.+\n?)+)", block)
        criteria: list[str] = []
        if criteria_section:
            for line in criteria_section.group(1).strip().split("\n"):
                m = re.search(r"-\s*(\S+)", line)
                if m:
                    criteria.append(m.group(1))
        entry["covered_criteria"] = criteria
        entries.append(entry)
    return entries


def main() -> int:
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    entries = parse_registry_entries(text)

    if not entries:
        print("ERROR: No overlay entries with covered_criteria found in registry.")
        return 2

    problems: list[str] = []
    checked: int = 0

    for entry in entries:
        skill_name = entry.get("overlay_skill", "")
        criteria = entry.get("covered_criteria", [])
        criterion_group = entry.get("criterion_group", "unknown")

        if not skill_name:
            problems.append(f"No overlay_skill for criterion_group={criterion_group}")
            continue

        checked += 1

        # Check skill directory exists
        skill_dir = SKILLS_ROOT / skill_name
        if not skill_dir.exists():
            problems.append(
                f"Missing skill directory: {skill_name} "
                f"(criterion_group={criterion_group}, criteria={criteria})"
            )
            continue

        # Check SKILL.md exists
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            problems.append(f"Missing SKILL.md for {skill_name}")
            continue

        # Read SKILL.md and check it mentions the criteria
        try:
            md_text = skill_md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            problems.append(f"Cannot read {skill_md}")
            continue

        # Check at least one criterion from covered_criteria appears in SKILL.md
        if criteria:
            found = any(c.upper() in md_text.upper() for c in criteria)
            if not found:
                problems.append(
                    f"SKILL.md for {skill_name} does not mention any of "
                    f"covered_criteria={criteria}"
                )

    print(f"Registry entries with covered_criteria: {checked}")
    if problems:
        print(f"\n{len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"PASS: all {checked} overlay entries have valid skill directories and SKILL.md references.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
