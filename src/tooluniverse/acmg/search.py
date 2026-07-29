"""Minimal ACMG evidence-collector integration for ToolUniverse search."""

from __future__ import annotations

import json
import re
from typing import Any

from .policy import (
    ACMG_FRONT_DOOR_TOOL_NAME,
    HIGH_RISK_ACMG_TOOLS,
    acmg_source_lead_metadata,
)


ACMG_GROUP_TOOLS = {
    "ACMG_clinical_evidence",
    "ACMG_computational_evidence",
    "ACMG_functional_evidence",
    "ACMG_literature_evidence",
    "ACMG_population_evidence",
}

_EXPLICIT_TERMS = (
    "acmg",
    "variant classification",
    "variant interpretation",
    "variant pathogenicity",
    "pathogenicity classification",
    "变异分类",
    "变异评级",
    "变异判读",
    "位点评级",
    "位点致病性",
    "突变致病性",
    "致病性评级",
)
_INTERPRETATION_TERMS = (
    "pathogenic",
    "benign",
    "pathogenicity",
    "clinical significance",
    "classification",
    "interpretation",
    "致病",
    "良性",
    "临床意义",
    "分类",
    "评级",
    "判读",
)
_VARIANT_PATTERNS = (
    re.compile(r"\bN[MR]_[0-9]+(?:\.[0-9]+)?:[cgmnpr]\.", re.IGNORECASE),
    re.compile(r"\b[A-Z][A-Z0-9]{1,12}[ ;]+(?:N[MR]_[0-9]+(?:\.[0-9]+)?:)?[cgmnpr]\.", re.IGNORECASE),
    re.compile(r"\bchr(?:[0-9]{1,2}|x|y|m):[0-9]+", re.IGNORECASE),
    re.compile(r"\b(?:chr)?(?:[0-9]{1,2}|X|Y|M)[-:][0-9]+[-:][ACGT]+[-:][ACGT]+\b", re.IGNORECASE),
    re.compile(r"\brs[0-9]+\b", re.IGNORECASE),
)


def is_acmg_query(query: str) -> bool:
    """Return whether a search query requests germline variant interpretation."""
    text = " ".join(str(query or "").lower().split())
    if not text:
        return False
    if any(term in text for term in _EXPLICIT_TERMS):
        return True
    has_variant = any(pattern.search(query or "") for pattern in _VARIANT_PATTERNS)
    if not has_variant:
        return False
    return "clingen" in text or any(term in text for term in _INTERPRETATION_TERMS)


def _item_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or item.get("tool_name") or "")
    return str(item or "")


def prioritize_acmg_tools(
    tools: list[Any], *, promote_collector: bool = True
) -> list[Any]:
    """Rank registry rows without fabricating a tool that search did not return."""
    if not promote_collector:
        preserved: list[Any] = []
        seen: set[str] = set()
        for item in tools:
            name = _item_name(item)
            if name and name in seen:
                continue
            if name:
                seen.add(name)
            if name in HIGH_RISK_ACMG_TOOLS and isinstance(item, dict):
                item = {**item, **acmg_source_lead_metadata()}
            preserved.append(item)
        return preserved
    collector: Any = None
    groups: list[Any] = []
    high_risk: list[Any] = []
    other: list[Any] = []
    seen: set[str] = set()

    for item in tools:
        name = _item_name(item)
        if name and name in seen:
            continue
        if name:
            seen.add(name)
        if name == ACMG_FRONT_DOOR_TOOL_NAME:
            collector = item
        elif name in ACMG_GROUP_TOOLS:
            groups.append(item)
        elif name in HIGH_RISK_ACMG_TOOLS:
            if isinstance(item, dict):
                item = {**item, **acmg_source_lead_metadata()}
            high_risk.append(item)
        else:
            other.append(item)

    if collector is not None:
        return [collector, *groups, *high_risk, *other]
    return [*groups, *high_risk, *other]


def decorate_search_payload(payload: Any) -> Any:
    """Reorder existing registry rows without changing the payload contract."""
    if isinstance(payload, list):
        return prioritize_acmg_tools(payload)
    if not isinstance(payload, dict):
        return payload

    result = dict(payload)
    limit = result.get("limit")
    limit = limit if isinstance(limit, int) and not isinstance(limit, bool) and limit > 0 else None
    offset = result.get("offset")
    offset = offset if isinstance(offset, int) and not isinstance(offset, bool) else 0
    categories = result.get("categories")
    category_allows_acmg = not categories or any(
        "acmg" in str(value).casefold()
        for value in (categories if isinstance(categories, list) else [categories])
    )
    for key in ("tools", "results", "data"):
        if isinstance(result.get(key), list):
            rows = prioritize_acmg_tools(
                result[key],
                promote_collector=offset == 0 and category_allows_acmg,
            )
            result[key] = rows[:limit] if limit else rows
            break
    return result


def decorate_serialized_search(serialized: str, query: str) -> str:
    """Decorate an MCP search response only when the query is ACMG-related."""
    if not is_acmg_query(query):
        return serialized
    try:
        payload = json.loads(serialized)
    except (json.JSONDecodeError, ValueError):
        payload = serialized
    return json.dumps(decorate_search_payload(payload), ensure_ascii=False, default=str)


__all__ = [
    "ACMG_GROUP_TOOLS",
    "decorate_search_payload",
    "decorate_serialized_search",
    "is_acmg_query",
    "prioritize_acmg_tools",
]
