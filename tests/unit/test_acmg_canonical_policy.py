"""Focused tests for canonical ACMG intent and final-label policy."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import importlib.util
from pathlib import Path
import warnings


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, Path(path).resolve())
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_canonical_acmg_intent_detector():
    module = _load_module("src/tooluniverse/acmg_gate/intent_detector.py", "intent_detector_test")
    cases = [
        # Original
        ("这个变异可能致病吗", "ACMG_FINAL_CLASSIFICATION"),
        ("这个位点严重吗", "ACMG_FINAL_CLASSIFICATION"),
        ("这个变异能否解释表型", "ACMG_FINAL_CLASSIFICATION"),
        ("能不能报阳性", "ACMG_FINAL_CLASSIFICATION"),
        ("BRCA1 c.68_69del 是否致病", "ACMG_FINAL_CLASSIFICATION"),
        ("rs123456 是不是致病", "ACMG_FINAL_CLASSIFICATION"),
        ("Is this variant likely pathogenic?", "ACMG_FINAL_CLASSIFICATION"),
        ("variant pathogenicity", "ACMG_FINAL_CLASSIFICATION"),
        # New — English clinical contexts
        ("germline testing for BRCA2 variant", "ACMG_FINAL_CLASSIFICATION"),
        ("variant of unknown significance interpretation", "ACMG_FINAL_CLASSIFICATION"),
        # "hereditary cancer panel" alone → ACMG_RELATED (no variant context)
        ("hereditary cancer panel classification", "ACMG_RELATED"),
        # New — Chinese clinical contexts
        ("遗传性肿瘤基因检测结果", "ACMG_FINAL_CLASSIFICATION"),
        ("携带者筛查发现变异", "ACMG_FINAL_CLASSIFICATION"),
        ("产前诊断变异解读", "ACMG_FINAL_CLASSIFICATION"),
        ("基因panel 测序结果", "ACMG_FINAL_CLASSIFICATION"),
        ("这个无义变异致病性分析", "ACMG_FINAL_CLASSIFICATION"),
        ("移码变异评级", "ACMG_FINAL_CLASSIFICATION"),
        ("剪切位点变异判读", "ACMG_FINAL_CLASSIFICATION"),
        ("有危害吗这个位点", "ACMG_FINAL_CLASSIFICATION"),
        ("良性还是致病", "ACMG_FINAL_CLASSIFICATION"),
        ("需不需要报阳性", "ACMG_FINAL_CLASSIFICATION"),
        ("基因报告解读变异", "ACMG_FINAL_CLASSIFICATION"),
        # New — Chinese judgment phrases
        ("判定为可能致病", "ACMG_FINAL_CLASSIFICATION"),
        ("评级为临床意义不明", "ACMG_FINAL_CLASSIFICATION"),
        # New — ACMG_RELATED but not final
        ("常染色体显性遗传病", "ACMG_RELATED"),
        ("新生突变分析", "ACMG_RELATED"),
        ("x连锁遗传变异", "ACMG_RELATED"),
        # False positives
        ("pathogenic bacteria", "NONE"),
        ("P value", "NONE"),
        ("B cell phenotype", "NONE"),
        ("良性肿瘤", "NONE"),
        ("致病机制", "NONE"),
    ]
    for query, expected in cases:
        assert module.detect_acmg_intent(query).value == expected, f"{query!r} -> {expected}"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert module.classify_acmg_intent("variant pathogenicity").value == "ACMG_FINAL_CLASSIFICATION"
    assert any(item.category is DeprecationWarning for item in caught)


def test_final_label_detector_blocks_guarded_labels():
    module = _load_module("src/tooluniverse/acmg_gate/final_label_detector.py", "final_label_detector_test")
    cases = [
        # English
        "Final classification: Pathogenic",
        "ACMG classification: LP",
        "classification = B",
        # Chinese original
        "最终分类：致病",
        "最终判断：可能致病",
        "该变异为临床意义不明",
        "ACMG分类：可能良性",
        "结论：良性",
        "这个变异为致病",
        "这个位点为可能致病",
        # Chinese new edge cases
        "评级为可能致病",
        "判定为良性",
        "分级为临床意义不明",
        "该突变为致病",
        "这个突变为可能良性",
    ]
    for text in cases:
        assert module.contains_final_acmg_label(text) is True, text


def test_final_label_detector_allows_false_positives():
    module = _load_module("src/tooluniverse/acmg_gate/final_label_detector.py", "final_label_detector_fp_test")
    cases = [
        "致病机制仍需研究",
        "良性肿瘤",
        "B细胞良性增殖",
        "可能致病机制",
        "该基因与疾病机制有关",
        "病原体具有致病性",
        "这个肿瘤是良性的",
        "P value is significant",
        "LP score is not a classification",
        "B cell phenotype",
    ]
    for text in cases:
        assert module.contains_final_acmg_label(text) is False, text


def test_final_classification_search_fails_closed():
    module = _load_module("src/tooluniverse/acmg_gate_search.py", "acmg_gate_search_policy_test")
    payload = {
        "tools": [
            {"name": "GeneBe_classify_variant"},
            {"name": "ClinVar_get_clinical_significance"},
            {"name": "SomeGenericVariantTool"},
        ],
        "limit": 10,
    }

    updated = module.add_acmg_gate_to_search_payload(
        payload,
        intent="ACMG_FINAL_CLASSIFICATION",
    )

    names = [row["name"] for row in updated["tools"]]
    assert names == [
        "ACMG_overlay_gate_assess_variant",
        "GeneBe_classify_variant",
        "ClinVar_get_clinical_significance",
    ]
    for row in updated["tools"][1:]:
        assert row["source_lead_only"] is True
        assert row["acmg_countable_evidence"] is False
        assert row["final_classification_allowed"] is False
        assert row["allowed_use"] == "source_lead_or_route_input"
        assert row["must_route_through"] == "ACMG_overlay_gate_assess_variant"


def test_acmg_related_search_preserves_non_high_risk_results():
    module = _load_module("src/tooluniverse/acmg_gate_search.py", "acmg_gate_search_related_test")
    payload = {"tools": [{"name": "SomeGenericVariantTool"}]}

    updated = module.add_acmg_gate_to_search_payload(payload, intent="ACMG_RELATED")

    assert [row["name"] for row in updated["tools"]] == [
        "ACMG_overlay_gate_assess_variant",
        "SomeGenericVariantTool",
    ]


if __name__ == "__main__":
    test_canonical_acmg_intent_detector()
    test_final_label_detector_blocks_guarded_labels()
    test_final_label_detector_allows_false_positives()
    test_final_classification_search_fails_closed()
    test_acmg_related_search_preserves_non_high_risk_results()
    print("PASS test_acmg_canonical_policy")
