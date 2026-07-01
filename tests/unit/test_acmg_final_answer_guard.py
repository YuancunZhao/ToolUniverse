#!/usr/bin/env python3
"""Compatibility and hardening tests for the ACMG final-answer guard."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.final_answer_guard import guard_acmg_final_answer
from tooluniverse.acmg_gate.final_label_detector import contains_final_acmg_label, manual_acmg_counting_matches


def test_manual_acmg_counting_without_token_is_blocked() -> None:
    result = guard_acmg_final_answer(
        "当前计数证据：PS3 + PM2 + PP3，因此满足 Likely Pathogenic。",
        {
            "state": "DRAFT_ONLY",
            "validator_status": "DRAFT_ONLY",
            "semantic_combiner_status": "NOT_RUN",
            "final_classification_allowed": False,
            "required_next_actions": ["pm2_absence_rarity", "pp3_bp4_splicing_prediction"],
        },
        None,
        "ACMG_FINAL_CLASSIFICATION",
    )
    assert result["status"] == "BLOCK", result
    assert result["has_manual_acmg_counting"] is True
    assert result["manual_acmg_counting_matches"]


def test_chinese_vus_alias_and_false_positive_behavior() -> None:
    assert contains_final_acmg_label("最终分类：意义不明确")
    assert manual_acmg_counting_matches("ACMG组合：PS3 + PM2")
    for text in ("P value", "B cell", "LP score", "致病机制", "良性肿瘤", "pathogenic bacteria"):
        result = guard_acmg_final_answer(text, None, None, None)
        assert result["status"] == "PASS", result
        assert result["detected_final_labels"] == []
        assert result["manual_acmg_counting_matches"] == []


if __name__ == "__main__":
    test_manual_acmg_counting_without_token_is_blocked()
    test_chinese_vus_alias_and_false_positive_behavior()
    print("PASS test_acmg_final_answer_guard")
