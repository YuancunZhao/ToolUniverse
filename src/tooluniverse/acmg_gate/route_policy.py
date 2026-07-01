"""Canonical route requirement policy for ACMG final-classification workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any

ROUTE_VARIANT_NORMALIZATION = "variant_normalization"
ROUTE_POPULATION_FREQUENCY = "population_frequency"
ROUTE_CONSEQUENCE_ASSESSMENT = "consequence_assessment"
ROUTE_COMPUTATIONAL_PREDICTION = "computational_prediction"
ROUTE_SOURCE_DATABASE_DISCOVERY = "source_database_discovery"
ROUTE_LITERATURE_DISCOVERY = "literature_discovery"
ROUTE_LITERATURE_DEEP_REVIEW = "literature_deep_review"
ROUTE_FUNCTIONAL_ASSAY_REVIEW = "functional_assay_review"
ROUTE_SEGREGATION_DE_NOVO_REVIEW = "segregation_de_novo_review"
ROUTE_PHENOTYPE_SPECIFICITY_REVIEW = "phenotype_specificity_review"
ROUTE_PHASE_PM3_REVIEW = "phase_pm3_review"

BLOCKING_STATUSES = {"pending"}
COMPLETION_STATUSES = {"completed", "no_actionable_evidence", "waived", "not_applicable"}
UNAVAILABLE_STATUS = "unavailable"

_PMID_RE = re.compile(r"\b\d{7,9}\b")


@dataclass
class RouteRequirement:
    route: str
    requirement: str
    status: str = "pending"
    trigger_reason: str = ""
    finalization_blocker: bool = True
    required_action: str | None = None
    source_leads: list[dict[str, Any]] = field(default_factory=list)
    route_candidates: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if payload["required_action"] is None:
            payload["required_action"] = self.route
        return payload


def _as_dict_list(values: Any) -> list[dict[str, Any]]:
    if not values:
        return []
    if isinstance(values, dict):
        return [values]
    if isinstance(values, list):
        return [value for value in values if isinstance(value, dict)]
    return []


def _text_blob(*values: Any) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True, default=str).lower()


def _variant_effect_type(variant_context: dict[str, Any]) -> str:
    explicit = str(variant_context.get("effect_type") or variant_context.get("consequence") or "").lower()
    if explicit:
        return explicit
    variant = str(variant_context.get("variant") or "")
    if re.search(r"c\.\d+[+-]\d+", variant, re.IGNORECASE):
        return "intronic"
    return "unknown"


def _has_actionable_literature(source_leads: list[dict[str, Any]], user_context: dict[str, Any]) -> bool:
    blob = _text_blob(source_leads, user_context)
    return bool(_PMID_RE.search(blob)) or any(
        term in blob
        for term in (
            "functional assay",
            "minigene",
            "rna assay",
            "segregation",
            "de novo",
            "ps3",
            "bs3",
            "ps2",
            "pm6",
            "pp1",
            "pp4",
            "查文献",
            "文献",
        )
    )


def _route_status_from_session(route: str, session: dict[str, Any]) -> str:
    for row in _as_dict_list(session.get("route_requirements")):
        if row.get("route") == route and row.get("status"):
            return str(row["status"])
    completed = {str(item.get("route") or item.get("action") or item) for item in session.get("completed_actions", [])}
    return "completed" if route in completed else "pending"


def determine_required_routes(
    session: dict[str, Any] | Any,
    source_leads: list[dict[str, Any]] | None = None,
    user_context: dict[str, Any] | None = None,
    variant_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return route requirements that must be resolved before ACMG finalization."""

    session_payload = session if isinstance(session, dict) else {}
    source_leads = source_leads or _as_dict_list(session_payload.get("source_lead_sandbox"))
    user_context = user_context or {}
    variant_context = variant_context or {}
    effect_type = _variant_effect_type(variant_context)
    blob = _text_blob(source_leads, user_context, variant_context)
    actionable_literature = _has_actionable_literature(source_leads, user_context)
    phenotype_present = bool(user_context.get("phenotype") or user_context.get("hpo_terms") or user_context.get("HPO"))
    family_present = any(term in blob for term in ("mother", "grandmother", "family", "segregation", "de novo", "母亲", "外婆", "家系", "遗传"))
    recessive_phase = any(term in blob for term in ("compound heterozygous", "in trans", "recessive", "pm3", "复合杂合", "反式"))
    splicing_applicable = effect_type in {"intronic", "splice_region", "canonical_splice", "synonymous"} or any(
        term in blob for term in ("spliceai", "ds_dg", "splice", "剪切", "内含子")
    )

    routes = [
        RouteRequirement(
            ROUTE_VARIANT_NORMALIZATION,
            "required",
            trigger_reason="final ACMG classification requires normalized variant/gene/transcript identity",
        ),
        RouteRequirement(
            ROUTE_POPULATION_FREQUENCY,
            "required",
            trigger_reason="population frequency is required for BA1/BS1/PM2 decisions",
            diagnostics={
                "coverage_adequacy_required": effect_type == "intronic",
                "population_absence_status": "absent_but_intronic_coverage_uncertain" if effect_type == "intronic" else None,
            },
        ),
        RouteRequirement(
            ROUTE_CONSEQUENCE_ASSESSMENT,
            "required",
            trigger_reason="consequence class determines applicable overlays",
            diagnostics={"effect_type": effect_type},
        ),
        RouteRequirement(
            ROUTE_COMPUTATIONAL_PREDICTION,
            "required_if_applicable",
            trigger_reason="consequence-appropriate prediction route is applicable",
            diagnostics={"prediction_class": "splicing" if splicing_applicable else "sequence_or_missense"},
        ),
        RouteRequirement(
            ROUTE_SOURCE_DATABASE_DISCOVERY,
            "required",
            trigger_reason="source databases provide source leads and conflicts only",
        ),
        RouteRequirement(
            ROUTE_LITERATURE_DISCOVERY,
            "required",
            status="pending" if actionable_literature else "no_actionable_evidence",
            trigger_reason="lightweight literature discovery is required; no-hit does not block deep review",
            finalization_blocker=actionable_literature,
            diagnostics={"actionable_literature_found": actionable_literature},
        ),
    ]
    if actionable_literature:
        routes.append(
            RouteRequirement(
                ROUTE_LITERATURE_DEEP_REVIEW,
                "conditionally_required",
                trigger_reason="actionable literature or source-lead evidence claim requires deep review",
            )
        )
        if any(term in blob for term in ("functional", "minigene", "rna assay", "ps3", "bs3", "34162030", "38397214")):
            routes.append(
                RouteRequirement(
                    ROUTE_FUNCTIONAL_ASSAY_REVIEW,
                    "conditionally_required",
                    trigger_reason="functional assay claim or PMID requires overlay review",
                )
            )
    if family_present:
        routes.append(
            RouteRequirement(
                ROUTE_SEGREGATION_DE_NOVO_REVIEW,
                "conditionally_required",
                trigger_reason="family/de novo/segregation context provided",
                route_candidates=[
                    {
                        "suggested_criterion": "PP1",
                        "counted": False,
                        "required_action": "test_relatives_for_variant",
                        "reason": "phenotype-only family history requires genotype-supported segregation review",
                    }
                ],
                diagnostics={"confirmed_relative_genotypes": bool(user_context.get("confirmed_relative_genotypes"))},
            )
        )
    if phenotype_present:
        routes.append(
            RouteRequirement(
                ROUTE_PHENOTYPE_SPECIFICITY_REVIEW,
                "conditionally_required",
                trigger_reason="phenotype/HPO context provided",
                route_candidates=[{"suggested_criterion": "PP4", "counted": False, "requires_overlay_validation": True}],
            )
        )
    if recessive_phase:
        routes.append(
            RouteRequirement(
                ROUTE_PHASE_PM3_REVIEW,
                "conditionally_required",
                trigger_reason="recessive phase/second-variant context provided",
            )
        )

    results: list[dict[str, Any]] = []
    for route in routes:
        row = route.to_dict()
        if row["status"] == "pending":
            row["status"] = _route_status_from_session(row["route"], session_payload)
        if row["status"] in COMPLETION_STATUSES:
            row["finalization_blocker"] = False
        results.append(row)
    return results


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
    "RouteRequirement",
    "determine_required_routes",
    "blocking_route_requirements",
]
