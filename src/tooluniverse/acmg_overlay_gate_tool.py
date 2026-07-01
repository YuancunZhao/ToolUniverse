"""ACMG overlay gate front-door tool for ToolUniverse.

This tool is intentionally a compliance gate and preflight planner, not a new
ACMG classifier. It routes germline pathogenicity tasks toward the overlay
bundle/validator workflow and treats automated classifier outputs as source
leads.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - minimal direct-python test env.
    yaml = None

from .acmg_gate import (
    ACMG_GATE_NOTICE,
    DISCOVERY_NO_HIT_ROUTES,
    RECOMMENDED_ACMG_INTAKE_TOOLS,
    REQUIRED_ACMG_COVERAGE_CATEGORIES,
    SOURCE_LEAD_NOTICE,
    add_required_actions_from_plan,
    build_draft_only_response,
    compute_finalization_gate,
    contains_final_acmg_label,
    create_acmg_session,
    discover_user_context_routes,
    issue_finalization_token,
    sandbox_source_output,
    session_from_dict,
    session_to_dict,
    session_to_policy_envelope,
)
from .acmg_harness_runner import ACMGHarnessRunner
from .base_tool import BaseTool
from .tool_registry import register_tool

CLASSIFICATION_DRAFT = "draft classification"
CLASSIFICATION_FINAL = "final classification"
VALIDATOR_NOT_RUN = "NOT_RUN"
VALIDATOR_DRAFT_ONLY = "DRAFT_ONLY"
ACMG_ORDINARY_ENTRYPOINT = "ACMG_overlay_gate_assess_variant"

SOURCE_LEAD_KEYWORDS = (
    "genebe",
    "intervar",
    "clinvar",
    "clingen",
    "hgmd",
    "lovd",
    "lab assertion",
    "paper label",
)


@register_tool("ACMGOverlayGateTool")
class ACMGOverlayGateTool(BaseTool):
    """Plan and validate ACMG overlay-gated assessments."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.operation = self.tool_config.get("fields", {}).get("operation", "assess_variant")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "arguments must be an object"}

        if self.operation == "plan_variant_assessment":
            return self._run_plan_variant_assessment(arguments)
        if self.operation == "collect_variant_evidence":
            return self._run_collect_variant_evidence(arguments)
        if self.operation == "apply_overlay_routes":
            return self._run_apply_overlay_routes(arguments)
        if self.operation == "finalize_assessment":
            return self._run_finalize_assessment(arguments)
        if self.operation == "guard_final_answer":
            return self._run_guard_final_answer(arguments)
        if self.operation != "assess_variant":
            return {"status": "error", "error": f"Unknown operation: {self.operation}"}

        mode = str(arguments.get("mode") or "assess").lower()
        if mode not in {"assess", "plan_only", "validate_bundle"}:
            return {"status": "error", "error": "mode must be 'assess', 'plan_only', or 'validate_bundle'"}
        output_mode = str(arguments.get("output_mode") or "compact").lower()
        if output_mode not in {"compact", "full"}:
            return {"status": "error", "error": "output_mode must be 'compact' or 'full'"}

        if mode == "assess":
            return self._run_harness(arguments, output_mode)
        if mode == "validate_bundle":
            return self._run_validate_bundle(arguments, output_mode)

        return self._run_plan_only(arguments, output_mode)

    def _runner(self) -> ACMGHarnessRunner:
        registry_entries = self._load_registry_entries()
        return ACMGHarnessRunner(
            run_tool=self._run_tool,
            registry_entries=registry_entries,
            route_row=self._route_row,
            select_baseline_routes=self._select_baseline_routes,
        )

    def _run_plan_variant_assessment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        planned = self._runner().plan_routes(arguments)
        session = self._protocol_session(arguments)
        session = session_from_dict(add_required_actions_from_plan(session, planned))
        return {
            "status": "success",
            "tool_role": "ACMG workflow planner; not an ACMG classifier",
            "ordinary_entrypoint": ACMG_ORDINARY_ENTRYPOINT,
            "not_final_entrypoint": True,
            "classification_status": CLASSIFICATION_DRAFT,
            "final_classification_allowed": False,
            "final_answer_policy": "forbidden",
            "variant": self._variant_summary(arguments),
            **planned,
            "acmg_session": session_to_dict(session),
            "protocol_envelope": session_to_policy_envelope(session),
            "required_next_actions": ["collect_evidence", "review_literature", "apply_overlay_routes", "finalize_assessment"],
            "acmg_gate_notice": ACMG_GATE_NOTICE,
        }

    def _run_collect_variant_evidence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        collected = self._runner().collect_evidence(arguments)
        session = self._protocol_session(arguments)
        for lead in collected.get("source_assertions_or_leads", []):
            session.source_lead_sandbox.append(
                sandbox_source_output(tool_name=str(lead.get("source_type") or "source_output"), raw_output=lead)
            )
        session = session_from_dict(add_required_actions_from_plan(session, collected))
        return {
            "status": "success",
            "tool_role": "ACMG evidence collector; not an ACMG classifier",
            "ordinary_entrypoint": ACMG_ORDINARY_ENTRYPOINT,
            "not_final_entrypoint": True,
            "classification_status": CLASSIFICATION_DRAFT,
            "final_classification_allowed": False,
            "final_answer_policy": "forbidden",
            "variant": self._variant_summary(arguments),
            "route_triggers": collected["route_triggers"],
            "coverage_audit_summary": collected["coverage_audit_summary"],
            "literature_status": collected["literature_status"],
            "source_assertions_or_leads": collected["source_assertions_or_leads"],
            "coverage_audit": collected["coverage_audit"],
            "tool_calls": collected["tool_calls"],
            "source_lead_sandbox": session.source_lead_sandbox,
            "acmg_session": session_to_dict(session),
            "protocol_envelope": session_to_policy_envelope(session),
            "required_next_actions": ["review_literature", "apply_overlay_routes", "finalize_assessment"],
            "acmg_gate_notice": ACMG_GATE_NOTICE,
        }

    def _run_apply_overlay_routes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        candidate_evidence = arguments.get("candidate_evidence")
        if not isinstance(candidate_evidence, list):
            candidate_evidence = self._candidate_evidence_from_route_triggers(arguments.get("route_triggers"))
        applied = self._runner().apply_overlay_routes(candidate_evidence)
        session = self._protocol_session(arguments)
        session = session_from_dict(add_required_actions_from_plan(session, {"required_next_actions": ["assemble_bundle", "validate_bundle", "finalize_assessment"]}))
        return {
            "status": "success",
            "tool_role": "ACMG overlay route dispatcher; not an ACMG classifier",
            "ordinary_entrypoint": ACMG_ORDINARY_ENTRYPOINT,
            "not_final_entrypoint": True,
            "classification_status": CLASSIFICATION_DRAFT,
            "final_classification_allowed": False,
            "final_answer_policy": "forbidden",
            **applied,
            "acmg_session": session_to_dict(session),
            "protocol_envelope": session_to_policy_envelope(session),
            "required_next_actions": ["assemble_bundle", "validate_bundle", "finalize_assessment"],
            "acmg_gate_notice": ACMG_GATE_NOTICE,
        }

    def _run_finalize_assessment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Compute final-classification gate status.

        final_allowed requires ALL of:
          - validator_status == "PASS" (policy/trace + semantic combiner integrated)
          - semantic_combiner_status == "PASS" (explicit re-check for readability)
          - final_classification_allowed is True
          - bundle requests final classification
          - compatibility-resolved counted evidence is non-empty
          - literature is reviewed / not needed
        """
        bundle = self._extract_bundle(arguments)
        validation = self._validate_bundle(bundle) if bundle else self._missing_bundle_result()
        validator_status = validation["validator_status"]
        validator_result = validation.get("validator_result") or {}
        semantic_status = validator_result.get("semantic_combiner_status") if isinstance(validator_result, dict) else None

        bundle_final_requested = self._bundle_requests_final_classification(bundle)
        counted = self._bundle_counted_evidence(bundle)
        literature_ready = self._bundle_literature_final_ready(bundle)

        gate = compute_finalization_gate(
            validator_status=validator_status,
            semantic_combiner_status=semantic_status,
            final_classification_allowed=True,
            bundle_final_requested=bundle_final_requested,
            counted_evidence=counted,
            literature_ready=literature_ready,
        )
        final_allowed = bool(gate["final_allowed"])

        blocked = self._missing_for_final_from_validation(validation, bundle_final_requested)
        blocked.extend(reason for reason in gate["blocking_reasons"] if reason not in blocked)
        session = self._session_from_finalization_inputs(
            arguments,
            bundle=bundle,
            validator_status=validator_status,
            semantic_status=semantic_status,
            final_allowed=final_allowed,
            counted=counted,
            literature_ready=literature_ready,
            blocked=blocked,
        )
        token_result = issue_finalization_token(session, classification=self._bundle_payload(bundle).get("classification")) if final_allowed else {
            "status": "BLOCK",
            "finalization_token_issued": False,
            "blocking_reasons": blocked,
        }
        if token_result.get("finalization_token_issued"):
            session = session_from_dict(token_result["acmg_session"])
        draft_policy = None if token_result.get("finalization_token_issued") else build_draft_only_response(session)

        return {
            "status": "success",
            "tool_role": "ACMG finalization gate; not an ACMG classifier",
            "ordinary_entrypoint": ACMG_ORDINARY_ENTRYPOINT,
            "not_final_entrypoint": True,
            "classification_status": CLASSIFICATION_FINAL if final_allowed else CLASSIFICATION_DRAFT,
            "validator_status": validator_status,
            "semantic_combiner_status": semantic_status,
            "final_classification_allowed": final_allowed,
            "final_answer_policy": "allowed" if final_allowed else "forbidden",
            "allowed_response": "final classification" if final_allowed else "draft classification only",
            "counted_evidence": counted,
            "blocked_reasons": blocked,
            "acmg_session": session_to_dict(session),
            "finalization_token": token_result.get("acmg_finalization_token"),
            "finalization_token_result": token_result,
            "draft_only_policy": draft_policy,
            "finalization_gate": gate,
            "validator_result": validator_result,
            "violations": validation.get("violations", []),
            "acmg_gate_notice": ACMG_GATE_NOTICE,
        }

    def _run_guard_final_answer(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        from .acmg_gate import guard_acmg_final_answer

        text = str(arguments.get("final_answer_text") or arguments.get("answer") or "")
        harness_result = arguments.get("harness_result") or arguments.get("workflow_result") or {}
        guarded = guard_acmg_final_answer(
            answer_text=text,
            session=harness_result if isinstance(harness_result, dict) else None,
            finalization_token=arguments.get("finalization_token") or (harness_result.get("finalization_token") if isinstance(harness_result, dict) else None),
            intent=arguments.get("intent") or (harness_result.get("intent") if isinstance(harness_result, dict) else None),
        )
        has_final_label = contains_final_acmg_label(text)
        evidence_without_overlay = self._contains_counted_evidence_without_overlay(text, harness_result)
        violations = []
        if guarded.get("status") == "BLOCK":
            violations.append("final_acmg_label_without_verified_finalization_token")
        if evidence_without_overlay:
            violations.append("counted_evidence_without_overlay_applied_or_vcep")
        status = "FAIL" if violations else "PASS"
        return {
            "status": status,
            "ordinary_entrypoint": ACMG_ORDINARY_ENTRYPOINT,
            "not_final_entrypoint": True,
            "has_final_acmg_label": has_final_label,
            "final_classification_allowed": guarded.get("final_answer_allowed") is True,
            "validator_status": harness_result.get("validator_status") if isinstance(harness_result, dict) else None,
            "violations": violations,
            "allowed_response": "final classification" if status == "PASS" and guarded.get("final_answer_allowed") else "draft classification only",
            "final_answer_guard": guarded,
            "acmg_gate_notice": ACMG_GATE_NOTICE,
        }

    def _run_plan_only(self, arguments: Dict[str, Any], output_mode: str) -> Dict[str, Any]:
        registry_entries = self._load_registry_entries()
        baseline_routes = self._select_baseline_routes(registry_entries, arguments)
        discovery_routes = self._select_discovery_routes(registry_entries, arguments)
        source_leads = self._normalize_source_leads(arguments.get("source_outputs_or_leads"))
        session = self._protocol_session(arguments)
        for lead in source_leads:
            if isinstance(lead.get("sandbox"), dict):
                session.source_lead_sandbox.append(lead["sandbox"])
        bundle = self._extract_bundle(arguments)
        validation = self._validate_bundle(bundle) if bundle else self._missing_bundle_result()

        validator_status = validation["validator_status"]
        validator_result = validation.get("validator_result") if isinstance(validation.get("validator_result"), dict) else {}
        gate = self._finalization_gate_from_bundle(
            bundle,
            validator_status=validator_status,
            semantic_status=validator_result.get("semantic_combiner_status"),
            policy_allows_final=bundle is not None,
        )
        final_allowed = bool(gate["final_allowed"])
        classification_status = CLASSIFICATION_FINAL if final_allowed else CLASSIFICATION_DRAFT
        session.validator_status = validator_status
        session.semantic_combiner_status = validator_result.get("semantic_combiner_status") or "NOT_RUN"
        session.final_classification_allowed = final_allowed
        session.counted_evidence = self._bundle_counted_evidence(bundle)
        session.literature_status = "reviewed" if self._bundle_literature_final_ready(bundle) else "not_reviewed"
        session = session_from_dict(add_required_actions_from_plan(session, {"required_baseline_routes": baseline_routes, "triggered_discovery_routes": discovery_routes}))

        response = {
            "status": "success",
            "tool_role": "ACMG overlay compliance gate and preflight planner; not an ACMG classifier",
            "mode": "plan_only",
            "output_mode": output_mode,
            "classification_status": classification_status,
            "validator_status": validator_status,
            "final_classification_allowed": final_allowed,
            "variant": self._variant_summary(arguments),
            "required_baseline_routes": baseline_routes,
            "triggered_discovery_routes": discovery_routes,
            "recommended_tool_calls": self._recommended_tool_calls(arguments),
            "online_literature_query_templates": self._literature_query_templates(arguments, source_leads),
            "required_coverage_categories": self._required_coverage_categories(arguments, source_leads),
            "required_coverage_tasks": self._required_coverage_tasks(arguments, source_leads),
            "source_assertions_or_leads": source_leads,
            "source_lead_sandbox": session.source_lead_sandbox,
            "acmg_session": session_to_dict(session),
            "protocol_envelope": session_to_policy_envelope(session),
            "draft_only_policy": None if final_allowed else build_draft_only_response(session),
            "acmg_assessment_bundle": bundle or self._bundle_skeleton(arguments, baseline_routes, discovery_routes, source_leads),
            "validator_result": validation.get("validator_result"),
            "semantic_combiner_status": validator_result.get("semantic_combiner_status"),
            "finalization_gate": gate,
            "violations": validation.get("violations", []),
            "next_actions": self._next_actions(validation, baseline_routes, discovery_routes),
            "acmg_gate_notice": ACMG_GATE_NOTICE,
        }
        if output_mode == "full":
            return response
        return self._compact_response(response, bundle is not None)

    def _run_validate_bundle(self, arguments: Dict[str, Any], output_mode: str) -> Dict[str, Any]:
        bundle = self._extract_bundle(arguments)
        validation = self._validate_bundle(bundle) if bundle else self._missing_bundle_result()
        validator_status = validation["validator_status"]
        validator_result = validation.get("validator_result") if isinstance(validation.get("validator_result"), dict) else {}
        bundle_final_requested = self._bundle_requests_final_classification(bundle)
        gate = self._finalization_gate_from_bundle(
            bundle,
            validator_status=validator_status,
            semantic_status=validator_result.get("semantic_combiner_status"),
            policy_allows_final=True,
        )
        final_allowed = bool(gate["final_allowed"])
        response = {
            "status": "success",
            "tool_role": "ACMG overlay compliance gate validator wrapper; not an ACMG classifier",
            "mode": "validate_bundle",
            "output_mode": output_mode,
            "classification_status": CLASSIFICATION_FINAL if final_allowed else CLASSIFICATION_DRAFT,
            "validator_status": validator_status,
            "semantic_combiner_status": validator_result.get("semantic_combiner_status"),
            "final_classification_allowed": final_allowed,
            "variant": self._variant_summary(arguments),
            "source_assertions_or_leads": self._normalize_source_leads(arguments.get("source_outputs_or_leads")),
            "validated_bundle_present": bundle is not None,
            "acmg_assessment_bundle_status": "validated_input_bundle_not_echoed" if bundle else "missing",
            "validator_result": validation.get("validator_result"),
            "violations": validation.get("violations", []),
            "candidate_evidence": [],
            "counted_evidence": [],
            "not_counted_source_leads": [],
            "coverage_audit_summary": [],
            "missing_for_final": self._missing_for_final_from_validation(validation, bundle_final_requested),
            "finalization_gate": gate,
            "acmg_gate_notice": ACMG_GATE_NOTICE,
        }
        response["acmg_session"] = session_to_dict(
            self._session_from_finalization_inputs(
                arguments,
                bundle=bundle,
                validator_status=validator_status,
                semantic_status=validator_result.get("semantic_combiner_status"),
                final_allowed=final_allowed,
                counted=self._bundle_counted_evidence(bundle),
                literature_ready=self._bundle_literature_final_ready(bundle),
                blocked=response["missing_for_final"],
            )
        )
        response["draft_only_policy"] = None if final_allowed else build_draft_only_response(response["acmg_session"])
        if output_mode == "full":
            response["acmg_assessment_bundle"] = bundle
        return response

    def _run_harness(self, arguments: Dict[str, Any], output_mode: str) -> Dict[str, Any]:
        runner = self._runner()
        harness = runner.assess(arguments)
        validation = self._validate_bundle(harness["acmg_assessment_bundle"])
        validator_status = validation["validator_status"]
        validator_result = validation.get("validator_result") if isinstance(validation.get("validator_result"), dict) else {}
        counted = [
            row
            for row in harness.get("route_audit", [])
            if isinstance(row, dict) and row.get("counted") is True
        ]
        validation_missing = self._missing_for_final_from_validation(validation)
        missing_for_final = harness.get("missing_for_final", []) + validation_missing
        gate = self._finalization_gate_from_bundle(
            harness.get("acmg_assessment_bundle"),
            validator_status=validator_status,
            semantic_status=validator_result.get("semantic_combiner_status"),
            policy_allows_final=not missing_for_final,
        )
        final_allowed = bool(gate["final_allowed"])
        session = self._session_from_finalization_inputs(
            arguments,
            bundle=harness.get("acmg_assessment_bundle"),
            validator_status=validator_status,
            semantic_status=validator_result.get("semantic_combiner_status"),
            final_allowed=final_allowed,
            counted=counted,
            literature_ready=self._bundle_literature_final_ready(harness.get("acmg_assessment_bundle")),
            blocked=missing_for_final,
        )
        response = {
            "status": "success",
            "tool_role": "ACMG executable overlay harness; not an independent ACMG classifier",
            "mode": "assess",
            "output_mode": output_mode,
            "classification_status": CLASSIFICATION_FINAL if final_allowed else CLASSIFICATION_DRAFT,
            "validator_status": validator_status,
            "semantic_combiner_status": validator_result.get("semantic_combiner_status"),
            "final_classification_allowed": final_allowed,
            "final_answer_policy": "allowed" if final_allowed else "forbidden",
            "allowed_response": "final classification" if final_allowed else "draft classification only",
            "variant": self._variant_summary(arguments),
            "route_triggers": harness.get("route_triggers", []),
            "counted_evidence": counted,
            "not_counted_source_leads": harness.get("source_assertions_or_leads", []),
            "coverage_audit_summary": harness.get("coverage_audit_summary", []),
            "literature_status": harness.get("literature_status", {}),
            "missing_for_final": missing_for_final,
            "finalization_gate": gate,
            "required_next_actions": self._required_next_actions_from_missing(missing_for_final),
            "validator_result": validation.get("validator_result"),
            "violations": validation.get("violations", []),
            "source_assertions_or_leads": harness.get("source_assertions_or_leads", []),
            "source_lead_sandbox": session.source_lead_sandbox,
            "acmg_session": session_to_dict(session),
            "protocol_envelope": session_to_policy_envelope(session),
            "draft_only_policy": None if final_allowed else build_draft_only_response(session),
            "acmg_gate_notice": ACMG_GATE_NOTICE,
        }
        if output_mode == "full":
            response.update({
                "tool_calls": harness.get("tool_calls", []),
                "derived_identifiers": harness.get("derived_identifiers", {}),
                "coverage_audit": harness.get("coverage_audit", []),
                "candidate_evidence": harness.get("candidate_evidence", []),
                "overlay_results": harness.get("overlay_results", []),
                "route_audit": harness.get("route_audit", []),
                "acmg_assessment_bundle": harness.get("acmg_assessment_bundle"),
            })
        return response

    def _protocol_session(self, arguments: Dict[str, Any]):
        existing = arguments.get("acmg_session") or arguments.get("session")
        if isinstance(existing, dict):
            return session_from_dict(existing)
        return create_acmg_session(
            variant=arguments.get("variant"),
            gene=arguments.get("gene"),
            transcript=arguments.get("transcript"),
        )

    def _session_from_finalization_inputs(
        self,
        arguments: Dict[str, Any],
        *,
        bundle: Dict[str, Any] | None,
        validator_status: str | None,
        semantic_status: str | None,
        final_allowed: bool,
        counted: List[Any],
        literature_ready: bool,
        blocked: List[str],
    ):
        session = self._protocol_session(arguments)
        payload = self._bundle_payload(bundle)
        session.variant = payload.get("variant", session.variant)
        if isinstance(session.variant, dict):
            variant_payload = session.variant
            session.variant = variant_payload.get("variant")
            session.gene = variant_payload.get("gene", session.gene)
            session.transcript = variant_payload.get("transcript", session.transcript)
        session.validator_status = validator_status or "NOT_RUN"
        session.semantic_combiner_status = semantic_status or "NOT_RUN"
        session.final_classification_allowed = bool(final_allowed)
        session.counted_evidence = [row for row in counted if isinstance(row, dict)]
        session.overlay_validated_evidence = [dict(row, overlay_validated=True) for row in session.counted_evidence]
        session.literature_status = "reviewed" if literature_ready else "not_reviewed"
        session.classification = payload.get("classification")
        for lead in self._normalize_source_leads(payload.get("source_assertions_or_leads")):
            if isinstance(lead.get("sandbox"), dict):
                session.source_lead_sandbox.append(lead["sandbox"])
        session = session_from_dict(add_required_actions_from_plan(session, payload))
        if blocked:
            session.policy_warnings.extend(str(item) for item in blocked)
        if final_allowed:
            session.state = "READY_FOR_FINALIZER"
        elif session.required_next_actions:
            session.state = "OVERLAYS_REQUIRED"
        else:
            session.state = "DRAFT_ONLY"
        return session

    def _run_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        from .tools._shared_client import get_shared_client

        return get_shared_client().run_one_function(
            {"name": tool_name, "arguments": arguments},
            use_cache=False,
            validate=True,
        )

    def _bundle_requests_final_classification(self, bundle: Dict[str, Any] | None) -> bool:
        if not isinstance(bundle, dict):
            return False
        payload = bundle.get("acmg_assessment_bundle") if "acmg_assessment_bundle" in bundle else bundle
        return isinstance(payload, dict) and payload.get("classification_status") == CLASSIFICATION_FINAL

    def _missing_for_final_from_validation(self, validation: Dict[str, Any], bundle_final_requested: bool = True) -> List[str]:
        if validation.get("validator_status") == "PASS":
            if bundle_final_requested:
                return []
            return ["bundle classification_status is not final classification"]
        missing = []
        for row in validation.get("violations", []):
            if isinstance(row, dict):
                code = row.get("code")
                message = row.get("message")
                missing.append(f"{code}: {message}" if code and message else str(row))
        return missing

    def _candidate_evidence_from_route_triggers(self, route_triggers: Any) -> List[Dict[str, Any]]:
        if not isinstance(route_triggers, list):
            return []
        group_to_criterion = {
            "pm2_absence_rarity": "PM2",
            "ba1_exception_list": "BA1",
            "pp3_bp4_missense_prediction": "PP3",
            "pm4_bp3_protein_length": "PM4",
            "ps3_bs3_functional_assay": "PS3",
            "de_novo_ps2_pm6": "PS2",
            "ps4_case_enrichment": "PS4",
            "pp1_bs4_pp4_segregation": "PP1",
            "reputable_source_review": "PP5",
            "pvs1_lof_decision_tree": "PVS1",
        }
        candidates = []
        for trigger in route_triggers:
            if not isinstance(trigger, dict):
                continue
            criterion = group_to_criterion.get(str(trigger.get("route_family") or ""))
            if not criterion:
                continue
            candidates.append({
                "criterion": criterion,
                "candidate_strength": "route_trigger_only",
                "source_category": trigger.get("source_category"),
                "reason": trigger.get("reason", "Route trigger supplied to overlay dispatcher."),
            })
        return candidates

    def _bundle_payload(self, bundle: Dict[str, Any] | None) -> Dict[str, Any]:
        if not isinstance(bundle, dict):
            return {}
        payload = bundle.get("acmg_assessment_bundle") if "acmg_assessment_bundle" in bundle else bundle
        return payload if isinstance(payload, dict) else {}

    def _bundle_counted_evidence(self, bundle: Dict[str, Any] | None) -> List[Any]:
        payload = self._bundle_payload(bundle)
        compatibility = payload.get("compatibility_resolution")
        if not isinstance(compatibility, dict):
            return []
        counted = compatibility.get("current_counted_evidence_resolved")
        return counted if isinstance(counted, list) else []

    def _bundle_literature_final_ready(self, bundle: Dict[str, Any] | None) -> bool:
        payload = self._bundle_payload(bundle)
        coverage = payload.get("coverage_audit")
        if not isinstance(coverage, list):
            return False
        literature_rows = [row for row in coverage if isinstance(row, dict) and row.get("source_category") == "literature"]
        if not literature_rows:
            return False
        for row in literature_rows:
            status = row.get("query_status")
            hits = row.get("hits") if isinstance(row.get("hits"), list) else []
            review_status = row.get("literature_review_status")
            if status == "no_hit":
                return True
            if status == "success" and not hits:
                return True
            if status == "success" and hits and review_status in {"reviewed_full", "reviewed_not_needed"}:
                return True
        return False

    def _finalization_gate_from_bundle(
        self,
        bundle: Dict[str, Any] | None,
        *,
        validator_status: str,
        semantic_status: str | None,
        policy_allows_final: bool,
    ) -> Dict[str, Any]:
        return compute_finalization_gate(
            validator_status=validator_status,
            semantic_combiner_status=semantic_status,
            final_classification_allowed=policy_allows_final,
            bundle_final_requested=self._bundle_requests_final_classification(bundle),
            counted_evidence=self._bundle_counted_evidence(bundle),
            literature_ready=self._bundle_literature_final_ready(bundle),
        )

    def _contains_counted_evidence_without_overlay(self, text: str, harness_result: Any) -> bool:
        if not re.search(r"\b(PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7])(?:_[A-Za-z]+)?\b", text):
            return False
        if not isinstance(harness_result, dict):
            return True
        route_audit = harness_result.get("route_audit") or []
        if not isinstance(route_audit, list):
            return True
        return not any(
            isinstance(row, dict)
            and row.get("counted") is True
            and row.get("route_outcome") in {"overlay_applied", "overlay_deferred_to_vcep"}
            for row in route_audit
        )

    def _required_next_actions_from_missing(self, missing: List[str]) -> List[str]:
        actions = []
        text = " ".join(missing).lower()
        if "literature" in text:
            actions.append("review_literature_hits_or_document_no_hit")
        if "counted evidence" in text or "overlay" in text:
            actions.append("apply_overlay_routes_before_counting")
        if "coverage" in text:
            actions.append("complete_required_coverage")
        actions.append("rerun_acmg_finalize_assessment")
        return list(dict.fromkeys(actions))

    def _repo_root_candidates(self) -> Iterable[Path]:
        here = Path(__file__).resolve()
        for parent in here.parents:
            yield parent
        yield Path.cwd()

    def _find_skills_root(self) -> Path | None:
        for root in self._repo_root_candidates():
            direct = root / "skills" / "tooluniverse-acmg-overlay-routing-core"
            if direct.exists():
                return direct
            agents = root / ".agents" / "skills" / "tooluniverse-acmg-overlay-routing-core"
            if agents.exists():
                return agents
        packaged = Path(__file__).resolve().parent / "data" / "acmg_overlay_gate"
        if packaged.exists():
            return packaged
        return None

    def _load_registry_entries(self) -> List[Dict[str, Any]]:
        skills_root = self._find_skills_root()
        if not skills_root:
            return []
        registry_path = skills_root / "overlay_registry.yaml"
        if yaml is None:
            return []
        try:
            payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return []
        if isinstance(payload, dict):
            entries = payload.get("overlays") or payload.get("routes") or payload.get("registry") or payload.get("criteria")
            if entries is None:
                entries = [item for item in payload.get("entries", []) if isinstance(item, dict)]
        else:
            entries = []
        if not entries and isinstance(payload, dict):
            entries = [value for value in payload.values() if isinstance(value, dict) and "criterion_group" in value]
        return [entry for entry in entries or [] if isinstance(entry, dict)]

    def _route_row(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "criterion_group": entry.get("criterion_group"),
            "covered_criteria": entry.get("covered_criteria", []),
            "gated_criteria": entry.get("gated_criteria", []),
            "intake_criteria": entry.get("intake_criteria", []),
            "source_review_criteria": entry.get("source_review_criteria", []),
            "compatibility_criteria": entry.get("compatibility_criteria", []),
            "overlay_skill": entry.get("overlay_skill"),
            "trigger_policy": entry.get("trigger_policy"),
            "enforcement_level": entry.get("enforcement_level"),
            "route_kind": entry.get("route_kind"),
            "applies_when": entry.get("applies_when", []),
            "baseline_data_sources": entry.get("baseline_data_sources", []),
        }

    def _compact_response(self, response: Dict[str, Any], bundle_present: bool) -> Dict[str, Any]:
        return {
            "status": response["status"],
            "tool_role": response["tool_role"],
            "mode": response.get("mode", "plan_only"),
            "output_mode": "compact",
            "classification_status": response["classification_status"],
            "validator_status": response["validator_status"],
            "final_classification_allowed": response["final_classification_allowed"],
            "variant": response["variant"],
            "recommended_tool_calls": response["recommended_tool_calls"],
            "required_coverage_categories": response["required_coverage_categories"],
            "source_assertions_or_leads": response["source_assertions_or_leads"],
            "source_lead_sandbox": response.get("source_lead_sandbox", []),
            "acmg_session": response.get("acmg_session"),
            "protocol_envelope": response.get("protocol_envelope"),
            "draft_only_policy": response.get("draft_only_policy"),
            "validated_bundle_present": bundle_present,
            "acmg_assessment_bundle_status": (
                "validated_input_bundle_not_echoed" if bundle_present else "skeleton_available_with_output_mode_full"
            ),
            "bundle_required_fields": [
                "variant",
                "classification_status",
                "route_plan",
                "coverage_audit",
                "overlay_results",
                "route_audit",
                "compatibility_resolution",
            ],
            "validator_result": response["validator_result"],
            "violations": response["violations"],
            "next_actions": response["next_actions"],
            "acmg_gate_notice": response["acmg_gate_notice"],
        }

    def _select_baseline_routes(self, entries: List[Dict[str, Any]], arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        consequence_text = " ".join(str(arguments.get(key, "")) for key in ("variant", "transcript", "consequence", "variant_type")).lower()
        selected: List[Dict[str, Any]] = []
        for entry in entries:
            policy = entry.get("trigger_policy")
            if policy == "universal_baseline":
                selected.append(self._route_row(entry))
            elif policy == "variant_type_baseline" and self._variant_type_matches(entry, consequence_text):
                selected.append(self._route_row(entry))
        if selected:
            return selected
        return [
            {"criterion_group": "population_frequency_bundle", "trigger_policy": "universal_baseline", "enforcement_level": "must_query"},
            {"criterion_group": "source_assertion_review", "trigger_policy": "universal_baseline", "enforcement_level": "must_query"},
            {"criterion_group": "pvs1_applicability_gate", "trigger_policy": "universal_baseline", "enforcement_level": "must_plan"},
            {"criterion_group": "evidence_compatibility_resolution", "trigger_policy": "universal_baseline", "enforcement_level": "must_audit_if_counted"},
        ]

    def _variant_type_matches(self, entry: Dict[str, Any], consequence_text: str) -> bool:
        applies = " ".join(str(item).lower() for item in entry.get("applies_when", []))
        group = str(entry.get("criterion_group", "")).lower()
        if "missense" in applies or "missense" in group:
            return "missense" in consequence_text or "p." in consequence_text
        if "splice" in applies or "splice" in group:
            return "splice" in consequence_text or "+" in consequence_text or "-" in consequence_text
        if "lof" in applies or "lof" in group:
            return any(term in consequence_text for term in ("stop", "frameshift", "nonsense", "splice_acceptor", "splice_donor"))
        if "protein_length" in applies or "pm4" in group:
            return any(term in consequence_text for term in ("in-frame", "inframe", "del", "ins", "dup"))
        return False

    def _select_discovery_routes(self, entries: List[Dict[str, Any]], arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        context_routes = discover_user_context_routes(arguments)
        if not context_routes:
            return []
        by_group = {str(entry.get("criterion_group")): entry for entry in entries}
        selected = []
        for route in context_routes:
            group = str(route.get("criterion_group"))
            entry = by_group.get(group)
            row = self._route_row(entry) if entry else {"criterion_group": group}
            row.update({
                "source_type": "user_context",
                "route_outcome": route.get("route_outcome", "overlay_required"),
                "counted": False,
                "trigger_text": route.get("trigger_text"),
                "reason": route.get("reason"),
            })
            selected.append(row)
        return selected

    def _recommended_tool_calls(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        calls = [dict(row) for row in RECOMMENDED_ACMG_INTAKE_TOOLS]
        variant_text = str(arguments.get("variant", ""))
        if variant_text and ("+" in variant_text or "-" in variant_text or "splice" in variant_text.lower()):
            calls.insert(0, {
                "tool_name": "EnsemblVEP_variant_recoder",
                "purpose": "Map transcript HGVS to genomic coordinates before SpliceAI/GeneBe/InterVar calls.",
                "route_input_for": ["normalization", "splice bundle"],
            })
        return calls

    def _literature_query_templates(self, arguments: Dict[str, Any], source_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        gene = str(arguments.get("gene") or "").strip()
        variant = str(arguments.get("variant") or "").strip()
        transcript = str(arguments.get("transcript") or "").strip()
        phenotype = str(arguments.get("phenotype_context") or arguments.get("disease_context") or "").strip()
        family = str(arguments.get("family_context") or "").strip()
        source_text = json.dumps([lead.get("raw_source") for lead in source_leads], ensure_ascii=False).lower()
        rsids = sorted(set(token for token in source_text.replace(",", " ").split() if token.startswith("rs") and token[2:].isdigit()))

        base_terms = [term for term in (gene, transcript, variant) if term]
        queries: List[Dict[str, Any]] = []
        if base_terms:
            queries.append({
                "purpose": "variant_specific_literature",
                "query": " ".join(base_terms),
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        for rsid in rsids:
            queries.append({
                "purpose": "rsid_literature",
                "query": f"{gene} {rsid}".strip(),
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        if gene and phenotype:
            queries.append({
                "purpose": "gene_phenotype_literature",
                "query": f"{gene} {phenotype}",
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        if gene and (family or phenotype):
            queries.append({
                "purpose": "segregation_family_literature",
                "query": f"{gene} segregation family pedigree affected relatives",
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        if gene:
            queries.append({
                "purpose": "functional_splicing_literature",
                "query": f"{gene} {variant} RT-PCR RNA minigene cryptic splice intron retention".strip(),
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
            queries.append({
                "purpose": "case_enrichment_literature",
                "query": f"{gene} {variant} cohort case series recurrence".strip(),
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        return queries

    def _required_coverage_categories(self, arguments: Dict[str, Any], source_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        categories = [dict(row) for row in REQUIRED_ACMG_COVERAGE_CATEGORIES]
        categories.append({
            "source_category": "source_assertion",
            "required_before_final": bool(source_leads),
            "reason": "GeneBe/InterVar/ClinVar/lab/paper assertions are source leads and must not be counted directly.",
        })
        categories.append({
            "source_category": "clinical_context",
            "required_before_final": bool(arguments.get("family_context") or arguments.get("phenotype_context")),
            "reason": "User-supplied family/phenotype context triggers intake but does not assign strength directly.",
        })
        return categories

    def _required_coverage_tasks(self, arguments: Dict[str, Any], source_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tasks = self._required_coverage_categories(arguments, source_leads)
        for row in tasks:
            if row.get("source_category") == "literature":
                row["required_fields"] = ["queried_sources", "query_terms", "query_tool_or_time", "query_status", "reason", "not_triggered_routes"]
                row["not_triggered_routes_if_no_hit"] = DISCOVERY_NO_HIT_ROUTES
        return tasks

    def _normalize_source_leads(self, value: Any) -> List[Dict[str, Any]]:
        if value in (None, ""):
            return []
        raw_items = value if isinstance(value, list) else [value]
        leads: List[Dict[str, Any]] = []
        for item in raw_items:
            text = json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item)
            lowered = text.lower()
            source_type = "source_output"
            for keyword in SOURCE_LEAD_KEYWORDS:
                if keyword in lowered:
                    source_type = keyword.replace(" ", "_")
                    break
            tool_name = source_type
            if isinstance(item, dict):
                tool_name = str(item.get("tool_name") or item.get("name") or item.get("source") or source_type)
            sandbox = sandbox_source_output(tool_name=tool_name, raw_output=item)
            leads.append({
                "source_type": source_type,
                "raw_source": item,
                "countable": False,
                "counted": False,
                "source_lead_only": True,
                "acmg_countable_evidence": False,
                "final_classification_allowed": False,
                "sandbox": sandbox,
                "route_candidates": sandbox.get("candidate_routes", []),
                "reason": SOURCE_LEAD_NOTICE,
            })
        return leads

    def _extract_bundle(self, arguments: Dict[str, Any]) -> Dict[str, Any] | None:
        bundle = arguments.get("acmg_assessment_bundle") or arguments.get("assessment_bundle") or arguments.get("bundle")
        if isinstance(bundle, dict):
            return bundle
        return None

    def _validate_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        skills_root = self._find_skills_root()
        if not skills_root:
            return {
                "validator_status": VALIDATOR_DRAFT_ONLY,
                "violations": [{"code": "validator_unavailable", "message": "ACMG overlay validator script was not found."}],
                "validator_result": None,
            }
        script = skills_root / "scripts" / "validate_acmg_overlay_bundle.py"
        if not script.exists():
            return {
                "validator_status": VALIDATOR_DRAFT_ONLY,
                "violations": [{"code": "validator_unavailable", "message": str(script)}],
                "validator_result": None,
            }
        payload = {"acmg_assessment_bundle": bundle}
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False)
            tmp_path = Path(handle.name)
        try:
            proc = subprocess.run(
                [sys.executable, str(script), str(tmp_path)],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            result = json.loads(proc.stdout) if proc.stdout.strip() else {"status": VALIDATOR_DRAFT_ONLY, "violations": []}
        except Exception as exc:
            result = {"status": VALIDATOR_DRAFT_ONLY, "violations": [{"code": "validator_error", "message": str(exc)}]}
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return {
            "validator_status": result.get("status", VALIDATOR_DRAFT_ONLY),
            "violations": result.get("violations", []),
            "validator_result": result,
        }

    def _missing_bundle_result(self) -> Dict[str, Any]:
        return {
            "validator_status": VALIDATOR_DRAFT_ONLY,
            "violations": [{"code": "missing_acmg_assessment_bundle", "message": "No machine-checkable ACMG assessment bundle was provided."}],
            "validator_result": {"status": VALIDATOR_NOT_RUN, "reason": "No bundle provided."},
        }

    def _bundle_skeleton(self, arguments: Dict[str, Any], baseline_routes: List[Dict[str, Any]], discovery_routes: List[Dict[str, Any]], source_leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "variant": self._variant_summary(arguments),
            "classification_status": CLASSIFICATION_DRAFT,
            "route_plan": baseline_routes + discovery_routes,
            "coverage_audit": [],
            "coverage_audit_note": "Populate coverage_audit only after actual queries. Literature coverage must come from online PubMed/PMC/EuropePMC or ToolUniverse literature search; no-hit is acceptable, no-search is not.",
            "overlay_results": [],
            "route_audit": [],
            "compatibility_resolution": {"current_counted_evidence_resolved": [], "unresolved_conflicts": []},
            "source_assertions_or_leads": source_leads,
        }

    def _variant_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "variant": arguments.get("variant"),
            "gene": arguments.get("gene"),
            "transcript": arguments.get("transcript"),
            "disease_context": arguments.get("disease_context"),
            "phenotype_context": arguments.get("phenotype_context"),
            "family_context": arguments.get("family_context"),
        }

    def _next_actions(self, validation: Dict[str, Any], baseline_routes: List[Dict[str, Any]], discovery_routes: List[Dict[str, Any]]) -> List[str]:
        actions = []
        if validation.get("validator_status") != "PASS":
            actions.append("Keep classification_status as draft classification until validator_status is PASS.")
            actions.append("Populate route_plan, coverage_audit, overlay_results, route_audit, and compatibility_resolution in acmg_assessment_bundle.")
            actions.append("Run online literature discovery before final classification; record no-hit literature searches with queried sources, query terms, tool/time, reason, and not_triggered_routes.")
        if baseline_routes:
            actions.append("Run or document all applicable baseline routes before evidence assignment.")
        if discovery_routes:
            actions.append("Run triggered discovery overlays before counting family, functional, cohort, de novo, or phase evidence.")
        actions.append("Treat SpliceAI/VEP/MyVariant/gnomAD/MaveDB/ClinGen/G2P and user family or phenotype input as coverage hits or route triggers until overlay audit passes.")
        actions.append("Keep GeneBe, InterVar, ClinVar, lab, and paper labels in source_assertions_or_leads unless primary evidence is routed.")
        return actions
