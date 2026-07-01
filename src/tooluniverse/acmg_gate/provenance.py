"""Tool-call receipts and evidence provenance helpers for ACMG routes.

This module records and matches evidence/receipt provenance. ``complete_step``
may mark a route completed when a matching receipt exists, but it does not
decide evidence countability or finalization eligibility.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

try:
    from .session import mark_completed_action, session_from_dict, session_to_dict
except ImportError:  # pragma: no cover - direct file execution in tests.
    from tooluniverse.acmg_gate.session import mark_completed_action, session_from_dict, session_to_dict


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class ToolCallReceipt:
    call_id: str
    outer_tool: str
    inner_tool: str | None
    route: str
    status: str
    input_hash: str
    output_hash: str
    summary: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance_type: str = "tool"
    receipt_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["receipt_id"] = self.receipt_id or f"receipt:{self.call_id}:{stable_hash(payload)[:12]}"
        return payload


@dataclass
class EvidenceProvenance:
    evidence_id: str
    source_type: str
    source_name: str
    route: str
    access_level: str
    review_status: str
    supports_criteria: list[str] = field(default_factory=list)
    counted: bool = False
    countability_reason: str = "source provenance is not overlay-validated counted evidence"
    pmid: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_tool_call_receipt(
    *,
    call_id: str,
    outer_tool: str,
    inner_tool: str | None,
    route: str,
    status: str,
    inputs: Any = None,
    output: Any = None,
    summary: str = "",
    provenance_type: str = "tool",
) -> dict[str, Any]:
    return ToolCallReceipt(
        call_id=call_id,
        outer_tool=outer_tool,
        inner_tool=inner_tool,
        route=route,
        status=status,
        input_hash=stable_hash(inputs),
        output_hash=stable_hash(output),
        summary=summary,
        provenance_type=provenance_type,
    ).to_dict()


def make_evidence_provenance(
    *,
    evidence_id: str,
    source_type: str,
    source_name: str,
    route: str,
    access_level: str,
    review_status: str,
    supports_criteria: list[str] | None = None,
    counted: bool = False,
    countability_reason: str | None = None,
    pmid: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    reason = countability_reason or (
        "overlay-validated counted evidence" if counted else "source provenance is not overlay-validated counted evidence"
    )
    return EvidenceProvenance(
        evidence_id=evidence_id,
        source_type=source_type,
        source_name=source_name,
        route=route,
        access_level=access_level,
        review_status=review_status,
        supports_criteria=supports_criteria or [],
        counted=counted,
        countability_reason=reason,
        pmid=pmid,
        url=url,
    ).to_dict()


def _receipt_matches_route(receipt: dict[str, Any], route: str, *, inner_tool: str | None = None, receipt_id: str | None = None, call_id: str | None = None) -> bool:
    if receipt_id and receipt.get("receipt_id") == receipt_id:
        return True
    if call_id and receipt.get("call_id") == call_id:
        return True
    if inner_tool and receipt.get("inner_tool") == inner_tool:
        return True
    return receipt.get("route") == route


def complete_step(
    session: dict[str, Any] | Any,
    *,
    route: str,
    receipt: dict[str, Any] | None = None,
    receipt_id: str | None = None,
    call_id: str | None = None,
    inner_tool: str | None = None,
    status: str = "completed",
) -> dict[str, Any]:
    """Complete a route using a route name, receipt id, call id, or inner tool identity."""

    obj = session_from_dict(session)
    receipts = list(obj.tool_call_receipts)
    if receipt:
        receipts.append(dict(receipt))
    matched = any(_receipt_matches_route(row, route, inner_tool=inner_tool, receipt_id=receipt_id, call_id=call_id) for row in receipts)
    if not matched and not (receipt_id or call_id or inner_tool):
        matched = True
    if not matched:
        return {
            "status": "BLOCK",
            "route_completed": False,
            "reason": "no receipt matched route, receipt_id, call_id, or inner_tool",
            "route": route,
        }
    obj.tool_call_receipts = receipts
    for row in obj.route_requirements:
        if isinstance(row, dict) and row.get("route") == route:
            row["status"] = status
            row["finalization_blocker"] = status not in {"completed", "no_actionable_evidence", "waived", "not_applicable"}
    obj = mark_completed_action(obj, route)
    return {
        "status": "PASS",
        "route_completed": True,
        "route": route,
        "acmg_session": session_to_dict(obj),
    }


__all__ = [
    "EvidenceProvenance",
    "ToolCallReceipt",
    "complete_step",
    "make_evidence_provenance",
    "make_tool_call_receipt",
    "stable_hash",
]
