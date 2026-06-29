#!/usr/bin/env python3
"""Small registry adapter for ACMG overlay routing metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "overlay_registry.yaml"


def load_overlay_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = Path(path) if path else REGISTRY_PATH
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _entries(registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = registry or load_overlay_registry()
    entries = payload.get("overlays") or payload.get("routes") or payload.get("entries") or []
    return [entry for entry in entries if isinstance(entry, dict)]


def _criteria(entry: dict[str, Any]) -> set[str]:
    keys = ("covered_criteria", "gated_criteria", "intake_criteria", "source_review_criteria", "compatibility_criteria")
    values: set[str] = set()
    for key in keys:
        raw = entry.get(key) or []
        if isinstance(raw, str):
            raw = [raw]
        values.update(str(item).upper() for item in raw)
    return values


def criterion_to_overlay(criterion: str) -> str | None:
    target = criterion.upper()
    for entry in _entries():
        if target in _criteria(entry):
            overlay = entry.get("overlay_skill")
            return str(overlay) if overlay else None
    return None


def criterion_to_group(criterion: str) -> str | None:
    target = criterion.upper()
    for entry in _entries():
        if target in _criteria(entry):
            group = entry.get("criterion_group")
            return str(group) if group else None
    return None


def required_coverage_for_criterion(criterion: str) -> list[str]:
    group = criterion_to_group(criterion)
    for entry in _entries():
        if group and entry.get("criterion_group") == group:
            sources = entry.get("baseline_data_sources") or entry.get("required_coverage") or []
            if isinstance(sources, str):
                sources = [sources]
            return sorted({str(source) for source in sources})
    return []


def discovery_routes() -> list[dict[str, Any]]:
    return [entry for entry in _entries() if entry.get("trigger_policy") == "evidence_discovery"]


def baseline_routes_for_variant_type(variant_type: str) -> list[dict[str, Any]]:
    text = str(variant_type or "").lower()
    selected = []
    for entry in _entries():
        policy = entry.get("trigger_policy")
        applies = " ".join(str(item).lower() for item in entry.get("applies_when", []))
        if policy == "universal_baseline":
            selected.append(entry)
        elif policy == "variant_type_baseline" and (not applies or any(token in text for token in applies.replace(",", " ").split())):
            selected.append(entry)
    return selected


def source_lead_routes() -> list[dict[str, Any]]:
    return [entry for entry in _entries() if entry.get("trigger_policy") in {"source_assertion", "source_review", "source_lead"} or entry.get("source_review_criteria")]
