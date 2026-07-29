"""Backward-compatible alias contracts for the evidence-only runtime."""

from __future__ import annotations

from tooluniverse.acmg_runtime_tools import ACMGOverlayGateTool


class _FakeToolUniverse:
    def run_one_function(self, call, **kwargs):
        return {"status": "error", "error": "offline fixture"}


def _alias() -> ACMGOverlayGateTool:
    return ACMGOverlayGateTool(
        {"name": "ACMG_overlay_gate_assess_variant", "fields": {}},
        tooluniverse=_FakeToolUniverse(),
    )


def test_alias_default_shape_matches_collector_runtime():
    result = _alias().run({"variant": "NM_000059.4:c.1A>G"})
    assert result["execution_status"] == "error"
    assert "consequence_profile" in result
    assert "evidence_cards" in result
    assert result["final_classification_allowed"] is False
