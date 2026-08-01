"""Machine-readable scientific rule metadata contracts."""

from tooluniverse.acmg.rule_catalog import (
    ACMG_CRITERIA,
    RULE_CATALOG,
    criterion_use_matrix,
    generic_bayesian_odds_for,
    rule_for_criterion,
)


def test_rule_catalog_entries_have_required_metadata():
    assert {
        "PM2",
        "BA1",
        "BS1",
        "PP3",
        "BP4",
        "PS2",
        "PP1",
        "PS3",
        "PS4",
    } <= RULE_CATALOG.keys()
    for rule in RULE_CATALOG.values():
        assert rule["rule_id"]
        assert rule["version"]
        assert rule["scope"]
        assert rule["required_inputs"]
        assert rule["primary_reference"]


def test_compound_criterion_uses_shared_rule_metadata():
    assert rule_for_criterion("PP3/BP4")["rule_id"] == "clingen-svi-pejaver-pp3-bp4"


def test_criterion_use_matrix_covers_all_28_codes():
    matrix = criterion_use_matrix()
    assert set(matrix) == set(ACMG_CRITERIA)
    assert all(
        {
            "direction",
            "default_strength",
            "automation_level",
            "required_facts",
            "provider_routes",
            "literature_fact_types",
            "required_context",
            "conflict_relations",
            "bayesian_direction",
        }
        <= set(row)
        for row in matrix.values()
    )
    assert matrix["PP5"]["automation_level"] == "deprecated"
    assert matrix["BP6"]["automation_level"] == "deprecated"
    assert matrix["PS1"]["provider_routes"] == [
        "consequence",
        "protein_context",
        "prior_variant_candidates",
    ]
    assert matrix["PP1"]["literature_fact_types"] == ["segregation"]


def test_generic_tavtigian_odds_preserve_direction():
    assert generic_bayesian_odds_for("PM3", "PM3_Moderate") == 4.3
    assert generic_bayesian_odds_for("BS3", "BS3_Strong") == 0.053
    assert generic_bayesian_odds_for("PP3", "arbitrary_strength") is None
