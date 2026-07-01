"""ACMG overlay registry ownership semantics."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit


ALL_ACMG_CRITERIA = {
    "PVS1",
    "PS1",
    "PS2",
    "PS3",
    "PS4",
    "PM1",
    "PM2",
    "PM3",
    "PM4",
    "PM5",
    "PM6",
    "PP1",
    "PP2",
    "PP3",
    "PP4",
    "PP5",
    "BA1",
    "BS1",
    "BS2",
    "BS3",
    "BS4",
    "BP1",
    "BP2",
    "BP3",
    "BP4",
    "BP5",
    "BP6",
    "BP7",
}


def _repo_root() -> Path:
    return Path(__file__).parents[2]


def _load_registry(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_skill_and_runtime_overlay_registries_are_identical():
    root = _repo_root()
    skill_registry = root / "skills" / "tooluniverse-acmg-overlay-routing-core" / "overlay_registry.yaml"
    runtime_registry = root / "src" / "tooluniverse" / "data" / "acmg_overlay_gate" / "overlay_registry.yaml"

    assert skill_registry.read_text(encoding="utf-8") == runtime_registry.read_text(encoding="utf-8")


def test_criterion_ownership_covers_all_acmg_criteria():
    registry = _load_registry(
        _repo_root() / "skills" / "tooluniverse-acmg-overlay-routing-core" / "overlay_registry.yaml"
    )
    ownership = registry["criterion_ownership"]

    assert set(ownership) == ALL_ACMG_CRITERIA
    assert ownership["PS1"] == [
        "ps1_pm5_amino_acid_equivalence",
        "ps1_splicing_similarity",
    ]
    assert ownership["PVS1"] == [
        "pvs1_lof_decision_tree",
        "pvs1_splicing",
    ]
    assert ownership["BP1"] == ["pm1_regional_missense_constraint"]


def test_covered_criteria_are_reserved_for_evidence_scoring_routes():
    registry = _load_registry(
        _repo_root() / "skills" / "tooluniverse-acmg-overlay-routing-core" / "overlay_registry.yaml"
    )

    for row in registry["overlays"]:
        if "covered_criteria" in row:
            assert row["route_kind"] == "evidence_scoring", row["criterion_group"]


def test_non_scoring_routes_use_scope_specific_fields():
    overlays = {
        row["criterion_group"]: row
        for row in _load_registry(
            _repo_root() / "skills" / "tooluniverse-acmg-overlay-routing-core" / "overlay_registry.yaml"
        )["overlays"]
    }

    assert "gated_criteria" in overlays["dominant_negative_mechanism"]
    assert "gated_criteria" in overlays["multiple_disorder_context"]
    assert "intake_criteria" in overlays["phenotype_dependent_intake"]
    assert overlays["phenotype_dependent_intake"]["route_kind"] == "evidence_intake"
    assert "source_review_criteria" in overlays["reputable_source_review"]
    assert "compatibility_criteria" in overlays["evidence_compatibility_resolution"]
    assert "covered_criteria" not in overlays["evidence_compatibility_resolution"]


def test_benign_context_cross_routes_bp1_without_owning_it():
    overlays = {
        row["criterion_group"]: row
        for row in _load_registry(
            _repo_root() / "skills" / "tooluniverse-acmg-overlay-routing-core" / "overlay_registry.yaml"
        )["overlays"]
    }
    benign_context = overlays["benign_context"]

    assert "BP1" not in benign_context["covered_criteria"]
    assert any(
        route.get("criterion") == "BP1"
        and route.get("route_to") == "pm1_regional_missense_constraint"
        for route in benign_context.get("cross_routes", [])
    )
