#!/usr/bin/env python3
"""Verify complete published Skill mirrors and the consolidated ACMG surface."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = ROOT / "skills"
MIRROR_PROFILES = (
    (
        ROOT / "plugin" / "skills",
        {"tooluniverse-codex-plugin", "tooluniverse-cs-setup"},
    ),
    (
        ROOT / "plugins" / "tooluniverse" / "skills",
        {"tooluniverse-claude-code-plugin", "tooluniverse-cs-setup"},
    ),
)
REQUIRED_ACMG_SKILLS = {
    "tooluniverse-acmg-variant-classification",
    "tooluniverse-variant-interpretation",
}
RETIRED_ACMG_SKILL = "tooluniverse-acmg-overlay-routing-core"
EXCLUDED_PARTS = {
    "evals",
    "__pycache__",
    ".pytest_cache",
    "htmlcov",
    ".mypy_cache",
    ".ruff_cache",
}


def _body(text: str) -> str:
    """Ignore supported host-specific YAML frontmatter differences."""
    if not text.startswith("---\n"):
        return text
    parts = text.split("---", 2)
    return parts[2].lstrip("\n") if len(parts) == 3 else text


def _published_skill_names() -> set[str]:
    names = {"tooluniverse", "setup-tooluniverse"}
    names.update(
        path.name
        for path in CANONICAL_ROOT.glob("tooluniverse-*")
        if (path / "SKILL.md").is_file()
    )
    return {name for name in names if (CANONICAL_ROOT / name / "SKILL.md").is_file()}


def _is_published_file(path: Path, skill_root: Path) -> bool:
    relative = path.relative_to(skill_root)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    name = path.name
    return not (
        fnmatch(name, "test_*.py")
        or fnmatch(name, "*_test.py")
        or fnmatch(name, "*.pyc")
        or name == ".DS_Store"
        or name == "coverage.xml"
        or name == ".coverage"
        or name.startswith(".coverage.")
    )


def _file_set(skill_root: Path) -> set[Path]:
    return {
        path.relative_to(skill_root)
        for path in skill_root.rglob("*")
        if path.is_file() and _is_published_file(path, skill_root)
    }


def main() -> int:
    errors: list[str] = []
    canonical_names = _published_skill_names()
    if not REQUIRED_ACMG_SKILLS <= canonical_names:
        errors.append("required consolidated ACMG Skills are missing")
    if RETIRED_ACMG_SKILL in canonical_names:
        errors.append("retired ACMG routing-core remains canonical")

    for mirror_root, profile_exclusions in MIRROR_PROFILES:
        expected_names = canonical_names - profile_exclusions
        actual_names = {
            path.name
            for path in mirror_root.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        }
        if expected_names != actual_names:
            missing = sorted(expected_names - actual_names)
            extra = sorted(actual_names - expected_names)
            errors.append(
                f"Skill set differs: {mirror_root}; missing={missing}; extra={extra}"
            )
            continue

        for skill in sorted(expected_names):
            source_dir = CANONICAL_ROOT / skill
            mirror_dir = mirror_root / skill
            source_files = _file_set(source_dir)
            mirror_files = _file_set(mirror_dir)
            if source_files != mirror_files:
                errors.append(f"file set differs: {mirror_dir}")
                continue
            for relative in sorted(source_files):
                source = (source_dir / relative).read_text(encoding="utf-8")
                mirror = (mirror_dir / relative).read_text(encoding="utf-8")
                if relative.name == "SKILL.md":
                    source, mirror = _body(source), _body(mirror)
                if source != mirror:
                    errors.append(f"content differs: {mirror_dir / relative}")

    if errors:
        raise SystemExit("\n".join(errors))
    print(
        "Complete ToolUniverse Skill mirrors match canonical content; "
        "ACMG routing is consolidated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
