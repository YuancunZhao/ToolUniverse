"""Shared fixture helpers for ACMG validator and bypass runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - fixture categories are optional.
    yaml = None


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def expected_status(payload: dict[str, Any], key: str) -> str:
    return str(payload.get(key, "")).strip().upper()


def load_fixture_manifest(fixtures_dir: Path) -> dict[str, str]:
    """Return fixture-name to category mapping from an optional manifest."""

    for candidate in (
        fixtures_dir / "fixture_manifest.yaml",
        fixtures_dir.parent / "fixture_manifest.yaml",
    ):
        if not candidate.exists():
            continue
        text = candidate.read_text(encoding="utf-8")
        payload = yaml.safe_load(text) if yaml is not None else _parse_simple_manifest(text)
        payload = payload or {}
        if not isinstance(payload, dict):
            return {}
        categories: dict[str, str] = {}
        for section, rows in payload.items():
            if not isinstance(rows, dict):
                continue
            for category, names in rows.items():
                if isinstance(names, list):
                    for name in names:
                        categories[str(name)] = f"{section}.{category}"
        return categories
    return {}


def _parse_simple_manifest(text: str) -> dict[str, dict[str, list[str]]]:
    """Parse the simple two-level fixture manifest without requiring PyYAML."""

    manifest: dict[str, dict[str, list[str]]] = {}
    current_section: str | None = None
    current_category: str | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if indent == 0 and line.endswith(":"):
            current_section = line[:-1]
            manifest.setdefault(current_section, {})
            current_category = None
        elif indent == 2 and line.endswith(":") and current_section:
            current_category = line[:-1]
            manifest[current_section].setdefault(current_category, [])
        elif indent >= 4 and line.startswith("- ") and current_section and current_category:
            manifest[current_section][current_category].append(line[2:].strip())
    return manifest


def summarize_by_category(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for row in results:
        category = str(row.get("category") or "uncategorized")
        bucket = summary.setdefault(category, {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if row.get("ok") is True:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    return summary
