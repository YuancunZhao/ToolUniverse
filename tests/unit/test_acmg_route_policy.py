#!/usr/bin/env python3
"""Route requirement policy tests for ACMG final-classification workflows."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.route_policy import blocking_route_requirements


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


if __name__ == "__main__":
    test_blocking_route_requirements_empty()
    test_blocking_route_requirements_filters_blockers()
    print("PASS test_acmg_route_policy")
