#!/usr/bin/env python3
"""Runtime ACMG pre-router integration tests."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.runtime_integration import route_user_message_before_agent


def test_acmg_final_classification_pre_router_requires_front_door() -> None:
    decision = route_user_message_before_agent("根据ACMG规则评估FGFR3 c.1075+95C>G 是否致病")

    assert decision["intent"] == "ACMG_FINAL_CLASSIFICATION"
    assert decision["allow_direct_answer"] is False
    assert decision["require_tool"] == "ACMG_overlay_gate_assess_variant"
    assert decision["require_post_guard"] is True
    assert decision["runtime_state"]["allow_direct_answer"] is False
    assert decision["runtime_state"]["front_door_completed"] is False


if __name__ == "__main__":
    test_acmg_final_classification_pre_router_requires_front_door()
    print("PASS test_acmg_runtime_pre_router")
