"""Agent-runtime integration guard for ACMG final-classification workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .draft_policy import build_draft_only_response
from .final_answer_guard import guard_acmg_final_answer
from .intent_detector import ACMGIntent
from .policy import ACMG_FRONT_DOOR_TOOL_NAME, is_high_risk_acmg_tool
from .pre_router import route_acmg_intent
from .session import (
    ACMGAssessmentSession,
    add_source_lead,
    create_acmg_session,
    missing_required_actions,
    session_from_dict,
    session_to_dict,
)
from .source_lead_sandbox import sandbox_source_output, source_category_for_tool

PLAN_TOOL_NAME = "ACMG_plan_variant_assessment"
FINALIZER_TOOL_NAME = "ACMG_finalize_assessment"

_SOURCE_LEAD_CATEGORIES = {
    "automated_classifier",
    "source_assertion",
    "splicing_prediction",
    "computational_prediction",
    "population",
    "literature",
    "disease_context",
}


@dataclass
class ACMGRuntimeState:
    """Mutable ACMG guard state owned by the agent runtime loop."""

    intent: str = ACMGIntent.NONE.value
    acmg_session: dict[str, Any] | None = None
    allow_direct_answer: bool = True
    require_tool: str | None = None
    require_post_guard: bool = False
    front_door_completed: bool = False
    finalization_token: str | None = None
    tool_outputs_must_be_sandboxed: bool = False
    blocked_events: list[dict[str, Any]] = field(default_factory=list)


def _state(runtime_state: dict[str, Any] | ACMGRuntimeState | None) -> ACMGRuntimeState:
    if isinstance(runtime_state, ACMGRuntimeState):
        return runtime_state
    if isinstance(runtime_state, dict):
        allowed = set(ACMGRuntimeState.__dataclass_fields__)
        return ACMGRuntimeState(**{key: value for key, value in runtime_state.items() if key in allowed})
    return ACMGRuntimeState()


def _state_payload(state: ACMGRuntimeState) -> dict[str, Any]:
    return asdict(state)


def _session_dict(session: dict[str, Any] | ACMGAssessmentSession | None) -> dict[str, Any] | None:
    if session is None:
        return None
    return session_to_dict(session_from_dict(session))


def _extract_session(raw_output: Any) -> dict[str, Any] | None:
    if not isinstance(raw_output, dict):
        return None
    for key in ("acmg_session", "session"):
        if isinstance(raw_output.get(key), dict):
            return _session_dict(raw_output[key])
    bundle = raw_output.get("acmg_assessment_bundle")
    if isinstance(bundle, dict) and isinstance(bundle.get("acmg_session"), dict):
        return _session_dict(bundle["acmg_session"])
    return None


def _is_acmg_final_intent(state: ACMGRuntimeState) -> bool:
    return state.intent == ACMGIntent.ACMG_FINAL_CLASSIFICATION.value


def _is_source_lead_tool(tool_name: str) -> bool:
    return is_high_risk_acmg_tool(tool_name) or source_category_for_tool(tool_name) in _SOURCE_LEAD_CATEGORIES


def _decision(
    action: str,
    *,
    state: ACMGRuntimeState,
    reason: str,
    tool_name: str | None = None,
    reroute_to: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "action": action,
        "allow": action == "allow",
        "block": action == "block",
        "reroute": action == "reroute",
        "tool_name": tool_name,
        "reroute_to": reroute_to,
        "reason": reason,
        "runtime_state": _state_payload(state),
    }
    if payload:
        decision.update(payload)
    if action in {"block", "reroute"}:
        state.blocked_events.append(
            {
                "action": action,
                "tool_name": tool_name,
                "reroute_to": reroute_to,
                "reason": reason,
            }
        )
        decision["runtime_state"] = _state_payload(state)
    return decision


def route_user_message_before_agent(user_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pre-route an incoming message before the model can answer directly."""

    routed = route_acmg_intent(user_message, context)
    if routed.get("intent") != ACMGIntent.ACMG_FINAL_CLASSIFICATION.value:
        state = ACMGRuntimeState(intent=str(routed.get("intent") or ACMGIntent.NONE.value))
        return {
            **routed,
            "require_tool": None,
            "require_post_guard": False,
            "runtime_state": _state_payload(state),
            "handling": "normal",
        }

    existing_session = context.get("acmg_session") if isinstance(context, dict) else None
    session = _session_dict(existing_session) or session_to_dict(create_acmg_session())
    state = ACMGRuntimeState(
        intent=ACMGIntent.ACMG_FINAL_CLASSIFICATION.value,
        acmg_session=session,
        allow_direct_answer=False,
        require_tool=ACMG_FRONT_DOOR_TOOL_NAME,
        require_post_guard=True,
        front_door_completed=False,
        tool_outputs_must_be_sandboxed=True,
    )
    return {
        **routed,
        "allow_direct_answer": False,
        "require_tool": ACMG_FRONT_DOOR_TOOL_NAME,
        "require_post_guard": True,
        "runtime_state": _state_payload(state),
        "handling": "acmg_guarded",
    }


def before_tool_call(tool_name: str, arguments: dict[str, Any] | None, runtime_state: dict[str, Any] | ACMGRuntimeState) -> dict[str, Any]:
    """Authorize, block, or reroute a tool call before execution."""

    state = _state(runtime_state)
    if not _is_acmg_final_intent(state):
        return _decision("allow", state=state, tool_name=tool_name, reason="non-ACMG-final workflow")

    if tool_name == ACMG_FRONT_DOOR_TOOL_NAME:
        return _decision("allow", state=state, tool_name=tool_name, reason="ACMG front-door routing required")

    if tool_name == PLAN_TOOL_NAME and not state.front_door_completed:
        return _decision("allow", state=state, tool_name=tool_name, reason="planning tool may create ACMG session")

    if not state.front_door_completed and _is_source_lead_tool(tool_name):
        return _decision(
            "reroute",
            state=state,
            tool_name=tool_name,
            reroute_to=ACMG_FRONT_DOOR_TOOL_NAME,
            reason="ACMG final-classification intent requires front-door overlay gate before source tools",
        )

    if not state.acmg_session and tool_name not in {ACMG_FRONT_DOOR_TOOL_NAME, PLAN_TOOL_NAME}:
        return _decision(
            "reroute",
            state=state,
            tool_name=tool_name,
            reroute_to=ACMG_FRONT_DOOR_TOOL_NAME,
            reason="ACMG session is required before tool execution",
        )

    if tool_name == FINALIZER_TOOL_NAME:
        session = session_from_dict(state.acmg_session or {})
        missing = missing_required_actions(session)
        if missing:
            return _decision(
                "block",
                state=state,
                tool_name=tool_name,
                reason="required overlay actions are incomplete",
                payload={"missing_required_actions": missing},
            )

    if _is_source_lead_tool(tool_name):
        return _decision(
            "allow",
            state=state,
            tool_name=tool_name,
            reason="source tool allowed only as sandboxed source lead",
            payload={
                "sandbox_required": True,
                "source_lead_only": True,
                "acmg_countable_evidence": False,
                "final_classification_allowed": False,
            },
        )

    return _decision("allow", state=state, tool_name=tool_name, reason="tool allowed in ACMG session")


def after_tool_call(tool_name: str, raw_output: Any, runtime_state: dict[str, Any] | ACMGRuntimeState) -> dict[str, Any]:
    """Normalize tool output after execution and update ACMG runtime state."""

    state = _state(runtime_state)
    if not _is_acmg_final_intent(state):
        return {"output": raw_output, "runtime_state": _state_payload(state)}

    output = raw_output
    if tool_name in {ACMG_FRONT_DOOR_TOOL_NAME, PLAN_TOOL_NAME}:
        state.front_door_completed = True
        extracted = _extract_session(raw_output)
        if extracted is not None:
            state.acmg_session = extracted
        elif state.acmg_session is None:
            state.acmg_session = session_to_dict(create_acmg_session())

    if _is_source_lead_tool(tool_name):
        sandboxed = sandbox_source_output(
            tool_name=tool_name,
            raw_output=raw_output,
            intent=ACMGIntent.ACMG_FINAL_CLASSIFICATION.value,
        )
        session = session_from_dict(state.acmg_session or create_acmg_session())
        session = add_source_lead(session, sandboxed)
        state.acmg_session = session_to_dict(session)
        output = {
            "source_lead_sandbox": sandboxed,
            "source_lead_only": True,
            "acmg_countable_evidence": False,
            "final_classification_allowed": False,
            "raw_output_sandboxed": True,
        }

    if tool_name == FINALIZER_TOOL_NAME and isinstance(raw_output, dict):
        token = raw_output.get("acmg_finalization_token") or raw_output.get("finalization_token")
        if token:
            state.finalization_token = str(token)
        extracted = _extract_session(raw_output)
        if extracted is not None:
            state.acmg_session = extracted

    return {
        "output": output,
        "runtime_state": _state_payload(state),
    }


def _safe_draft_only_response(session: dict[str, Any] | ACMGAssessmentSession | None) -> dict[str, Any]:
    draft = build_draft_only_response(session or create_acmg_session())
    source_summaries: list[dict[str, Any]] = []
    for lead in draft.get("source_lead_sandbox", []):
        if not isinstance(lead, dict):
            continue
        source_summaries.append(
            {
                "tool_name": lead.get("tool_name"),
                "source_category": lead.get("source_category"),
                "source_lead_summary": lead.get("source_lead_summary"),
                "candidate_routes": lead.get("candidate_routes", []),
                "counted": False,
                "source_lead_only": True,
                "acmg_countable_evidence": False,
                "final_classification_allowed": False,
            }
        )
    draft["source_lead_sandbox"] = source_summaries
    if isinstance(draft.get("acmg_session"), dict):
        draft["acmg_session"] = {
            **draft["acmg_session"],
            "source_lead_sandbox": source_summaries,
            "classification": None,
            "finalization_token": None,
            "final_classification_allowed": False,
            "counted_evidence": [],
            "overlay_validated_evidence": [],
        }
    return draft


def before_final_answer(answer_text: str, runtime_state: dict[str, Any] | ACMGRuntimeState) -> dict[str, Any]:
    """Guard ACMG final answers immediately before user-visible output."""

    state = _state(runtime_state)
    if not _is_acmg_final_intent(state):
        return {
            "action": "allow",
            "allow": True,
            "answer_text": answer_text,
            "runtime_state": _state_payload(state),
        }

    session = state.acmg_session
    token = state.finalization_token or (session or {}).get("finalization_token")
    guarded = guard_acmg_final_answer(
        answer_text=answer_text,
        session=session,
        finalization_token=token,
        intent=state.intent,
    )
    if guarded.get("status") == "PASS":
        return {
            "action": "allow",
            "allow": True,
            "guard_result": guarded,
            "answer_text": answer_text,
            "runtime_state": _state_payload(state),
        }

    safe = _safe_draft_only_response(session)
    return {
        "action": "block",
        "allow": False,
        "guard_result": guarded,
        "answer_text": safe,
        "runtime_state": _state_payload(state),
    }


def run_agent_with_acmg_runtime_guard(
    user_message: str,
    agent_callable: Callable[..., Any],
    tool_executor: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Demonstration wrapper: pre-route, run an agent, then post-guard its answer.

    The callable may accept either ``(user_message, runtime_state, tool_executor)``
    or just ``(user_message)``. Real runtimes should call ``before_tool_call`` and
    ``after_tool_call`` around each tool execution inside their own tool loop.
    """

    preroute = route_user_message_before_agent(user_message)
    state = preroute["runtime_state"]
    try:
        agent_result = agent_callable(user_message, state, tool_executor)
    except TypeError:
        agent_result = agent_callable(user_message)
    if isinstance(agent_result, dict):
        answer = str(agent_result.get("answer_text") or agent_result.get("answer") or "")
        if isinstance(agent_result.get("runtime_state"), dict):
            state = agent_result["runtime_state"]
    else:
        answer = str(agent_result)
    final = before_final_answer(answer, state)
    return {
        "pre_route": preroute,
        "agent_result": agent_result,
        "final_decision": final,
    }


__all__ = [
    "ACMGRuntimeState",
    "after_tool_call",
    "before_final_answer",
    "before_tool_call",
    "route_user_message_before_agent",
    "run_agent_with_acmg_runtime_guard",
]
