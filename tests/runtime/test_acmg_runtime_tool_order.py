#!/usr/bin/env python3
"""Runtime ACMG tool-order and source-sandbox tests."""

from tooluniverse.acmg_gate.runtime_integration import (
    after_tool_call,
    before_tool_call,
    route_user_message_before_agent,
)


def test_genebe_before_front_door_is_rerouted() -> None:
    state = route_user_message_before_agent("根据ACMG规则评估FGFR3 c.1075+95C>G 是否致病")["runtime_state"]

    decision = before_tool_call("GeneBe_classify_variant", {"variant": "FGFR3 c.1075+95C>G"}, state)

    assert decision["action"] == "reroute"
    assert decision["allow"] is False
    assert decision["reroute_to"] == "ACMG_overlay_gate_assess_variant"


def test_source_tool_inside_session_is_sandboxed() -> None:
    state = route_user_message_before_agent("根据ACMG规则评估FGFR3 c.1075+95C>G 是否致病")["runtime_state"]
    state = after_tool_call("ACMG_overlay_gate_assess_variant", {"acmg_session": state["acmg_session"]}, state)["runtime_state"]

    decision = before_tool_call("GeneBe_classify_variant", {"variant": "FGFR3 c.1075+95C>G"}, state)
    assert decision["action"] == "allow"
    assert decision["sandbox_required"] is True

    result = after_tool_call(
        "GeneBe_classify_variant",
        {"acmg_classification": "Likely Pathogenic", "acmg_criteria": ["PM2", "PP3"]},
        state,
    )
    output = result["output"]
    session = result["runtime_state"]["acmg_session"]

    assert output["source_lead_only"] is True
    assert output["acmg_countable_evidence"] is False
    assert output["final_classification_allowed"] is False
    assert session["source_lead_sandbox"][0]["counted"] is False
    assert session["counted_evidence"] == []


if __name__ == "__main__":
    test_genebe_before_front_door_is_rerouted()
    test_source_tool_inside_session_is_sandboxed()
    print("PASS test_acmg_runtime_tool_order")
