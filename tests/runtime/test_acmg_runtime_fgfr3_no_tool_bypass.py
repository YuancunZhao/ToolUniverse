#!/usr/bin/env python3
"""Runtime regression for FGFR3 no-tool and GeneBe-first bypass attempts."""

from tooluniverse.acmg_gate.runtime_integration import (
    after_tool_call,
    before_final_answer,
    before_tool_call,
    route_user_message_before_agent,
)


def test_fgfr3_no_tool_and_genebe_first_bypass_are_blocked() -> None:
    state = route_user_message_before_agent("根据ACMG规则评估FGFR3 c.1075+95C>G 是否致病")["runtime_state"]

    direct = before_final_answer("ACMG分类：Likely Pathogenic", state)
    assert direct["action"] == "block"

    genebe_first = before_tool_call("GeneBe_classify_variant", {"variant": "FGFR3 c.1075+95C>G"}, state)
    assert genebe_first["action"] == "reroute"
    assert genebe_first["reroute_to"] == "ACMG_overlay_gate_assess_variant"

    state = after_tool_call("ACMG_overlay_gate_assess_variant", {"acmg_session": state["acmg_session"]}, state)["runtime_state"]
    state = after_tool_call(
        "GeneBe_classify_variant",
        {"acmg_classification": "Likely Pathogenic", "acmg_criteria": ["PM2", "PP3"]},
        state,
    )["runtime_state"]

    draft_like = before_final_answer("草稿分类：Likely Pathogenic", state)
    assert draft_like["action"] == "block"
    safe = draft_like["answer_text"]
    assert safe["status"] == "DRAFT_ONLY"
    assert safe["final_classification_allowed"] is False
    assert safe["source_lead_sandbox"][0]["source_lead_only"] is True
    assert "Likely Pathogenic" not in str(safe)


if __name__ == "__main__":
    test_fgfr3_no_tool_and_genebe_first_bypass_are_blocked()
    print("PASS test_acmg_runtime_fgfr3_no_tool_bypass")
