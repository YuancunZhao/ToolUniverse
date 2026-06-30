#!/usr/bin/env python3
"""Check protected Skill mirrors for drift from canonical skills/."""

from __future__ import annotations

import filecmp
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = ROOT / "skills"
DUPLICATE_ROOTS = [
    ROOT / "plugin" / "skills",
    ROOT / "plugins" / "tooluniverse" / "skills",
]
PROTECTED_SKILLS = [
    "tooluniverse",
    "tooluniverse-variant-interpretation",
    "tooluniverse-acmg-variant-classification",
    "tooluniverse-acmg-overlay-routing-core",
    "tooluniverse-rare-disease-diagnosis",
    "tooluniverse-rare-disease-genomics",
    "tooluniverse-variant-functional-annotation",
    "tooluniverse-regulatory-variant-analysis",
    "tooluniverse-variant-to-mechanism",
    "tooluniverse-structural-variant-analysis",
    "tooluniverse-protein-sae-variant-interpretation",
]
ACMG_WRAPPER_SCRIPT_ROOT = CANONICAL_ROOT / "tooluniverse-acmg-overlay-routing-core" / "scripts"
PACKAGED_ACMG_WRAPPER_SCRIPT_ROOT = ROOT / "src" / "tooluniverse" / "data" / "acmg_overlay_gate" / "scripts"
REQUIRED_ACMG_WRAPPER_SCRIPTS = [
    "acmg_final_answer_guard.py",
    "acmg_semantic_combiner.py",
    "acmg_context_triggers.py",
    "acmg_registry.py",
    "validate_acmg_overlay_bundle.py",
    "check_entrypoint_bypass_fixtures.py",
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
    "reason about pathogenicity yourself",
]

NON_OVERLAY_SKILLS = {
    "tooluniverse",
    "tooluniverse-variant-interpretation",
    "tooluniverse-rare-disease-diagnosis",
    "tooluniverse-rare-disease-genomics",
    "tooluniverse-variant-functional-annotation",
    "tooluniverse-regulatory-variant-analysis",
    "tooluniverse-variant-to-mechanism",
    "tooluniverse-structural-variant-analysis",
    "tooluniverse-protein-sae-variant-interpretation",
}

FINAL_ROUTE_TO_VARIANT_INTERPRETATION_RE = re.compile(
    r"(ACMG\s+(?:clinical\s+)?classification|ACMG\s+pathogenicity\s+classification|"
    r"pathogenicity\s+classification|full\s+clinical\s+variant\s+classification|"
    r"complete\s+ACMG|final\s+ACMG|final\s+germline\s+pathogenicity|"
    r"is\s+.*variant\s+pathogenic|clinical\s+significance).*tooluniverse-variant-interpretation|"
    r"tooluniverse-variant-interpretation.*(ACMG\s+(?:clinical\s+)?classification|"
    r"pathogenicity\s+classification|complete\s+ACMG|final\s+ACMG|"
    r"final\s+germline\s+pathogenicity)",
    re.IGNORECASE,
)
DIRECT_COUNT_OR_FINAL_RE = re.compile(
    r"\b(assign|emit|produce|calculate|report)\b.*\b("
    r"final\s+(?:germline\s+)?ACMG|five-tier|5-tier|P/LP|LP/P|LB/B|B/LB|"
    r"counted\s+ACMG\s+evidence|count\s+ACMG\s+evidence"
    r")\b",
    re.IGNORECASE,
)


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


def compare_packaged_acmg_wrappers() -> list[str]:
    problems: list[str] = []
    if not ACMG_WRAPPER_SCRIPT_ROOT.exists():
        return [f"canonical ACMG wrapper directory missing: {ACMG_WRAPPER_SCRIPT_ROOT}"]
    if not PACKAGED_ACMG_WRAPPER_SCRIPT_ROOT.exists():
        return [f"packaged ACMG wrapper directory missing: {PACKAGED_ACMG_WRAPPER_SCRIPT_ROOT}"]
    for filename in REQUIRED_ACMG_WRAPPER_SCRIPTS:
        canonical = ACMG_WRAPPER_SCRIPT_ROOT / filename
        packaged = PACKAGED_ACMG_WRAPPER_SCRIPT_ROOT / filename
        if not canonical.exists():
            problems.append(f"canonical ACMG wrapper script missing: {canonical}")
            continue
        if not packaged.exists():
            problems.append(f"packaged ACMG wrapper script missing: {packaged}")
            continue
        if not filecmp.cmp(canonical, packaged, shallow=False):
            problems.append(f"drifted packaged ACMG wrapper script: {packaged}")
    return problems


def scan_unsafe_phrases(path: Path) -> list[str]:
    """Scan a directory tree for unsafe direct-classification phrases."""
    hits: list[str] = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        if _is_ignored(item.relative_to(path)) or "entrypoint_bypass_fixtures" in item.parts:
            continue
        try:
            text = item.read_text(errors="replace")
        except Exception:
            continue
        for phrase in UNSAFE_PHRASES:
            if phrase.lower() in text.lower():
                hits.append(f"unsafe phrase '{phrase}' in {item}")
        for line in text.splitlines():
            lowered = line.lower()
            if "do not stop at `tooluniverse-variant-interpretation`" in lowered:
                continue
            if "intake only" in lowered and "tooluniverse-acmg-variant-classification" in lowered:
                continue
            if "only for evidence intake" in lowered and "tooluniverse-acmg-variant-classification" in lowered:
                continue
            if FINAL_ROUTE_TO_VARIANT_INTERPRETATION_RE.search(line):
                hits.append(f"final ACMG/pathogenicity route points to variant-interpretation in {item}")
                break
    return hits


def scan_protected_skill_policy(skill: str, path: Path) -> list[str]:
    hits: list[str] = []
    if not path.exists():
        return hits
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in {".md", ".txt", ".py", ".json", ".yaml", ".yml"}:
            continue
        if _is_ignored(item.relative_to(path)) or "entrypoint_bypass_fixtures" in item.parts:
            continue
        text = item.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            lowered = line.lower()
            if "do not stop at `tooluniverse-variant-interpretation`" in lowered:
                continue
            if "intake only" in lowered and "tooluniverse-acmg-variant-classification" in lowered:
                continue
            if "only for evidence intake" in lowered and "tooluniverse-acmg-variant-classification" in lowered:
                continue
            if FINAL_ROUTE_TO_VARIANT_INTERPRETATION_RE.search(line):
                hits.append(f"forbidden final ACMG/pathogenicity route to variant-interpretation in {item}")
                break
        if skill in NON_OVERLAY_SKILLS and DIRECT_COUNT_OR_FINAL_RE.search(text):
            if "tooluniverse-acmg-variant-classification" not in text and "ACMG_overlay_gate_assess_variant" not in text:
                hits.append(f"non-overlay skill may claim direct counted/final ACMG output in {item}")
    if skill == "tooluniverse":
        skill_md = path / "SKILL.md"
        text = skill_md.read_text(encoding="utf-8", errors="replace") if skill_md.exists() else ""
        if "tooluniverse-acmg-variant-classification" not in text:
            hits.append(f"tooluniverse router missing ACMG classification route in {skill_md}")
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
                problems.extend(scan_protected_skill_policy(skill, skill_dir))

    problems.extend(compare_packaged_acmg_wrappers())

    if problems:
        print("Skill duplicate drift detected:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("PASS: protected Skill mirrors and packaged ACMG wrapper scripts match canonical sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
