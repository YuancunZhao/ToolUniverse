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


def test_alias_uses_the_same_structural_variant_preflight():
    result = _alias().run(
        {"variant": "chrX:32018026-32222964-DEL", "genome_build": "hg19"}
    )

    assert result["status"] == "not_applicable"
    assert result["workflow_status"] == "unsupported_variant_class"
    assert result["variant_scope"]["normalized_genome_build"] == "GRCh37"
    assert result["evidence_cards"] == []
