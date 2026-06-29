#!/usr/bin/env python3
"""Check protected Skill mirrors for drift from canonical skills/."""

from __future__ import annotations

import filecmp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = ROOT / "skills"
DUPLICATE_ROOTS = [
    ROOT / ".agents" / "skills",
    ROOT / "plugin" / "skills",
    ROOT / "plugins" / "tooluniverse" / "skills",
]
PROTECTED_SKILLS = [
    "tooluniverse-variant-interpretation",
    "tooluniverse-acmg-variant-classification",
    "tooluniverse-acmg-overlay-routing-core",
]

# Cache/build noise to ignore
IGNORE_PATTERNS = (
    "__pycache__",
    ".pyc",
    ".DS_Store",
    ".git",
    ".pytest_cache",
    "node_modules",
)

# Unsafe direct-classification phrases that must not appear in protected Skill mirrors
UNSAFE_PHRASES = [
    "Produces 5-tier verdict",
    "clinical-grade variant reports",
    "ACMG-classified",
    "Phase 6: ACMG CLASSIFICATION",
    "2+ concordant damaging = strong PP3",
    "Expression supports PP4",
]


def _is_ignored(rel: Path) -> bool:
    """Check whether a relative path or any of its parts is noise."""
    for part in rel.parts:
        if part in IGNORE_PATTERNS or part.endswith(".pyc"):
            return True
    return False


def files_under(path: Path) -> set[Path]:
    return {
        item.relative_to(path)
        for item in path.rglob("*")
        if item.is_file() and not _is_ignored(item.relative_to(path))
    }


def compare_dirs(canonical: Path, duplicate: Path) -> list[str]:
    problems: list[str] = []
    canonical_files = files_under(canonical)
    duplicate_files = files_under(duplicate)
    for rel in sorted(canonical_files - duplicate_files):
        problems.append(f"missing duplicate file: {duplicate / rel}")
    for rel in sorted(duplicate_files - canonical_files):
        problems.append(f"extra duplicate file: {duplicate / rel}")
    for rel in sorted(canonical_files & duplicate_files):
        if not filecmp.cmp(canonical / rel, duplicate / rel, shallow=False):
            problems.append(f"drifted duplicate file: {duplicate / rel}")
    return problems


def scan_unsafe_phrases(path: Path) -> list[str]:
    """Scan a directory tree for unsafe direct-classification phrases."""
    hits: list[str] = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        if _is_ignored(item.relative_to(path)):
            continue
        try:
            text = item.read_text(errors="replace")
        except Exception:
            continue
        for phrase in UNSAFE_PHRASES:
            if phrase.lower() in text.lower():
                hits.append(f"unsafe phrase '{phrase}' in {item}")
    return hits


def main() -> int:
    problems: list[str] = []
    for skill in PROTECTED_SKILLS:
        canonical = CANONICAL_ROOT / skill
        if not canonical.exists():
            problems.append(f"canonical skill missing: {canonical}")
            continue
        for root in DUPLICATE_ROOTS:
            duplicate = root / skill
            if not duplicate.exists():
                problems.append(f"duplicate mirror missing: {duplicate}")
                continue
            problems.extend(compare_dirs(canonical, duplicate))

    # Also scan all protected mirrors for unsafe phrases
    all_roots = [CANONICAL_ROOT] + DUPLICATE_ROOTS
    for root in all_roots:
        for skill in PROTECTED_SKILLS:
            skill_dir = root / skill
            if skill_dir.exists():
                problems.extend(scan_unsafe_phrases(skill_dir))

    if problems:
        print("Skill duplicate drift detected:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("PASS: all protected Skill mirrors match canonical skills/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
