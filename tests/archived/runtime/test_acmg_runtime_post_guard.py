#!/usr/bin/env python3
"""Runtime ACMG final-answer post-guard tests."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.runtime_integration import before_final_answer, route_user_message_before_agent


def test_final_label_without_token_is_blocked() -> None:
    state = route_user_message_before_agent("根据ACMG规则评估FGFR3 c.1075+95C>G 是否致病")["runtime_state"]

    decision = before_final_answer("ACMG分类：Likely Pathogenic", state)

    assert decision["action"] == "block"
    assert decision["allow"] is False
    assert decision["answer_text"]["status"] == "DRAFT_ONLY"


def test_draft_final_label_without_token_is_blocked() -> None:
    state = route_user_message_before_agent("根据ACMG规则评估FGFR3 c.1075+95C>G 是否致病")["runtime_state"]

    decision = before_final_answer("草稿分类：Likely Pathogenic", state)

    assert decision["action"] == "block"
    assert decision["allow"] is False
    assert decision["guard_result"]["status"] == "BLOCK"


if __name__ == "__main__":
    test_final_label_without_token_is_blocked()
    test_draft_final_label_without_token_is_blocked()
    print("PASS test_acmg_runtime_post_guard")
