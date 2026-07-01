"""Route requirement helpers for ACMG final-classification workflows."""

from __future__ import annotations

import json
from typing import Any

BLOCKING_STATUSES = {"pending"}
UNAVAILABLE_STATUS = "unavailable"


def text_blob(*values: Any) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True, default=str).lower()


def blocking_route_requirements(route_requirements: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return route requirements that still block finalization."""

    blockers: list[dict[str, Any]] = []
    for row in route_requirements or []:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "pending")
        if row.get("finalization_blocker") and (status in BLOCKING_STATUSES or status == UNAVAILABLE_STATUS):
            blockers.append(row)
    return blockers


__all__ = [
    "blocking_route_requirements",
    "text_blob",
]
