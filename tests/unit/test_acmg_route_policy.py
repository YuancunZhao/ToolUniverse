#!/usr/bin/env python3
"""Route requirement policy tests for ACMG final-classification workflows."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.route_policy import blocking_route_requirements
from tooluniverse.acmg_overlay_tools.router import route_overlays


def test_blocking_route_requirements_empty() -> None:
    assert blocking_route_requirements(None) == []
    assert blocking_route_requirements([]) == []


def test_blocking_route_requirements_filters_blockers() -> None:
    routes = [
        {"route": "test", "status": "pending", "finalization_blocker": True},
        {"route": "done", "status": "completed", "finalization_blocker": True},
        {"route": "no", "status": "pending", "finalization_blocker": False},
    ]
    blockers = blocking_route_requirements(routes)
    assert len(blockers) == 1
    assert blockers[0]["route"] == "test"


def test_bare_coding_substitution_without_consequence_is_unknown() -> None:
    result = route_overlays(variant="NM_000000.0:c.742C>T", gene="GENE")

    assert result["variant_type"] == "unknown"
    assert "pp3_bp4_missense_prediction" not in result["baseline_overlays"]
    assert any("Resolve molecular consequence" in step for step in result["workflow_steps"])


def test_explicit_missense_consequence_routes_missense_overlays() -> None:
    result = route_overlays(
        variant="NM_000000.0:c.742C>T",
        gene="GENE",
        consequence="missense_variant",
    )

    assert result["variant_type"] == "missense"
    assert "pp3_bp4_missense_prediction" in result["baseline_overlays"]


if __name__ == "__main__":
    test_blocking_route_requirements_empty()
    test_blocking_route_requirements_filters_blockers()
    test_bare_coding_substitution_without_consequence_is_unknown()
    test_explicit_missense_consequence_routes_missense_overlays()
    print("PASS test_acmg_route_policy")
