"""Reusable ACMG runtime hooks for LLM agent frameworks.

These hooks must be wired into the host LLM runtime agent loop. They do not
self-install — see SETUP.md for deployment guides.

Usage in a typical agent loop:

    from tooluniverse.acmg_gate.runtime_hooks import pre_answer_hook, post_answer_hook

    def agent_loop(user_message, tool_executor):
        # Before LLM answers: check if gate is required
        pre = pre_answer_hook(user_message)
        context = {}
        if pre["action"] == "require_tool":
            context = tool_executor(pre["tool_name"], pre.get("args", {}))

        # LLM generates answer
        answer = llm.generate(user_message, context=context)

        # Before user sees answer: guard against unvalidated ACMG labels
        post = post_answer_hook(answer, context)
        return post["answer"]
"""

from __future__ import annotations

from typing import Any


def pre_answer_hook(user_message: str) -> dict[str, Any]:
    """Check if user message requires ACMG gate before LLM answers.

    Returns dict with:
        action: "allow" | "require_tool"
        tool_name: name of required tool (if action == "require_tool")
        args: default arguments for the tool
        intent: detected ACMG intent level
    """
    from .intent_detector import ACMGIntent, detect_acmg_intent

    text = user_message or ""
    intent = detect_acmg_intent(text)

    if intent == ACMGIntent.ACMG_FINAL_CLASSIFICATION:
        return {
            "action": "require_tool",
            "tool_name": "ACMG_overlay_gate_assess_variant",
            "args": {"mode": "assess", "variant": ""},
            "intent": intent.value,
            "reason": (
                "ACMG final pathogenicity classification detected. "
                "Gate assessment required before answering."
            ),
        }

    return {"action": "allow", "intent": intent.value}


def post_answer_hook(
    answer_text: str,
    gate_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check LLM answer for unvalidated ACMG labels before user sees it.

    Args:
        answer_text: The LLM's generated answer text.
        gate_context: Optional dict with acmg_session, finalization_token, intent
                      from a previous ACMG_overlay_gate_assess_variant call.

    Returns dict with:
        action: "allow" | "block"
        answer: the (possibly replaced) answer text
        reason: why it was blocked (if blocked)
        has_final_label: whether ACMG labels were detected
    """
    from .final_label_detector import contains_final_acmg_label
    from .final_answer_guard import guard_acmg_final_answer

    text = answer_text or ""
    if not contains_final_acmg_label(text):
        return {"action": "allow", "answer": text, "has_final_label": False}

    ctx = gate_context or {}
    result = guard_acmg_final_answer(
        answer_text=text,
        session=ctx.get("acmg_session"),
        finalization_token=ctx.get("finalization_token"),
        intent=ctx.get("intent"),
    )

    if result["status"] == "BLOCK":
        return {
            "action": "block",
            "answer": result.get("safe_answer", result.get("reason", "")),
            "reason": result.get("message", ""),
            "has_final_label": True,
            "matched_labels": result.get("matched_labels", []),
        }

    return {
        "action": "allow",
        "answer": text,
        "has_final_label": True,
        "matched_labels": result.get("matched_labels", []),
    }


__all__ = ["pre_answer_hook", "post_answer_hook"]
