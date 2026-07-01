#!/usr/bin/env python3
"""Route requirement policy tests for ACMG final-classification workflows."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_gate.route_policy import blocking_route_requirements, determine_required_routes


def test_fgfr3_required_baseline_routes() -> None:
    routes = determine_required_routes(
        session={},
        source_leads=[],
        user_context={"phenotype": ["short stature", "prenatal long bone shortening"]},
        variant_context={"gene": "FGFR3", "variant": "NM_000142.5:c.1075+95C>G", "effect_type": "intronic"},
    )
    names = {row["route"] for row in routes}
    assert "variant_normalization" in names
    assert "population_frequency" in names
    assert "consequence_assessment" in names
    assert "computational_prediction" in names
    assert "source_database_discovery" in names
    assert "literature_discovery" in names
    computational = next(row for row in routes if row["route"] == "computational_prediction")
    assert computational["diagnostics"]["prediction_class"] == "splicing"


def test_fgfr3_literature_discovery_triggers_deep_review() -> None:
    routes = determine_required_routes(
        session={},
        source_leads=[{"PMID": "34162030", "functional_assay_details": "minigene assay"}],
        variant_context={"effect_type": "intronic"},
    )
    names = {row["route"] for row in routes}
    assert "literature_deep_review" in names
    assert "functional_assay_review" in names
    assert blocking_route_requirements(routes)


def test_fgfr3_literature_no_hit_does_not_infinite_block() -> None:
    routes = determine_required_routes(
        session={},
        source_leads=[],
        user_context={},
        variant_context={"effect_type": "intronic"},
    )
    literature = next(row for row in routes if row["route"] == "literature_discovery")
    assert literature["status"] == "no_actionable_evidence"
    assert literature["finalization_blocker"] is False
    assert "literature_deep_review" not in {row["route"] for row in routes}


if __name__ == "__main__":
    test_fgfr3_required_baseline_routes()
    test_fgfr3_literature_discovery_triggers_deep_review()
    test_fgfr3_literature_no_hit_does_not_infinite_block()
    print("PASS test_acmg_route_policy")
