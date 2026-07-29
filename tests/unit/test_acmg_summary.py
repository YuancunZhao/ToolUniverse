"""Evidence-only summary contracts."""

from tooluniverse.acmg.summary import summarize_strengths
from tooluniverse.acmg.rule_catalog import rule_for_criterion


def test_summary_requires_explicit_met_preview_and_validated_flags():
    rows = [
        {
            "criterion": "PP3",
            "strength": "PP3_Supporting",
            "assessment_status": "met",
            "system_preview_included": True,
            "overlay_validated": True,
            "source_fact_ids": ["fixture-pp3"],
            "rule_id": rule_for_criterion("PP3")["rule_id"],
            "rule_version": rule_for_criterion("PP3")["version"],
        },
        {
            "criterion": "PM2",
            "strength": "PM2_Supporting",
            "assessment_status": "met",
            "system_preview_included": "true",
            "overlay_validated": True,
            "source_fact_ids": ["fixture-pm2"],
        },
    ]

    result = summarize_strengths(
        rows, trusted_source_fact_ids={"fixture-pp3", "fixture-pm2"}
    )

    assert result["system_preview_criteria"] == ["PP3"]
    assert result["strength_counts"] == {"PP3_Supporting": 1}


def test_summary_does_not_emit_a_final_classification():
    result = summarize_strengths([])

    assert result["system_preview_criteria"] == []
    assert "classification" not in result
