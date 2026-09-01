"""Display-only compaction preserves clinical indexes and does not rescore facts."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from tooluniverse.acmg.collector import _compact_result


@pytest.fixture
def replay():
    path = (
        Path(__file__).resolve().parents[1] / "fixtures/acmg/duox2_summary_replay.json"
    )
    return json.loads(path.read_text())["full_result"]


def test_historical_duox2_replay_is_complete_and_nonmutating(
    replay, check_acmg_summary
):
    """The frozen old response tests serialization, not today's evidence decisions."""
    original = deepcopy(replay)
    summary = _compact_result(replay)
    assert (
        check_acmg_summary(summary) > 40_000
    )  # Deliberately exercise the soft target.
    assert replay == original
    assert _compact_result(replay) == summary
    assert summary["guard_context"] == original["guard_context"]
    assert summary["decision_report"] == original["decision_report"]
    assert summary["population_observations"] == original["population_observations"]
    assert summary["runtime_manifest"] == original["runtime_manifest"]
    for key in ("status", "execution_status", "coverage_status", "next_actions"):
        assert summary[key] == original[key]
    for key in ("automatic_bayesian", "verified_bayesian", "user_selected_bayesian"):
        assert summary[key] == original[key]
    for before, after in zip(original["evidence_cards"], summary["evidence_cards"]):
        for key in (
            "card_id",
            "criterion",
            "strength",
            "calculation_roles",
            "source_fact_ids",
        ):
            assert before.get(key) == after.get(key)
    assert len(summary["source_facts"]) < len(replay["source_facts"])
    assert len(summary["literature_candidates"]) == 64
    assert [
        (r.get("pmid") or None, r.get("pmcid") or None, r.get("doi") or None)
        for r in summary["literature_candidates"]
    ] == [
        (r.get("pmid") or None, r.get("pmcid") or None, r.get("doi") or None)
        for r in original["literature_candidates"]
    ]
    profile = summary["consequence_profile"]
    restored = [
        {
            **profile["observation_defaults"],
            **group["shared"],
            **dict(zip(group["columns"], row)),
        }
        for group in profile["observation_groups"]
        for row in group["rows"]
    ]
    assert len(restored) == len(original["consequence_profile"]["observations"]) == 90
    fields = (
        "provider",
        "source_fact_id",
        "transcript",
        "hgvs_c",
        "hgvs_p",
        "consequence_terms",
        "observation_role",
        "allele_match_status",
        "gene_match_status",
        "transcript_match_status",
        "target_binding_status",
    )

    def signatures(rows):
        return sorted(
            json.dumps([r.get(k) or None for k in fields], sort_keys=True) for r in rows
        )

    assert signatures(restored) == signatures(
        original["consequence_profile"]["observations"]
    )
    ps4_before = next(
        r for r in original["criterion_reviews"] if r["criterion"] == "PS4"
    )
    ps4_after = next(r for r in summary["criterion_reviews"] if r["criterion"] == "PS4")
    atomic_ids = [
        r["card_id"]
        for c in ps4_before["aggregated_cards"]
        for r in c["aggregation"]["other_results"]
    ]
    assert len(atomic_ids) == 8
    assert len(ps4_after["other_card_results"]) == 1
    assert ps4_after["other_card_results"][0]["card_ids"] == atomic_ids


def test_summary_groups_only_identical_results_within_representative_and_scenario():
    """Equal wording does not merge distinct scenarios, representatives or strengths."""

    def card(card_id, scenario, strength="PS4"):
        return {
            "card_id": card_id,
            "scenario_id": scenario,
            "aggregation": {
                "other_results": [
                    {
                        "card_id": card_id + "-a",
                        "strength": strength,
                        "evidence_status": "excluded",
                        "reason": "same explanation",
                    },
                    {
                        "card_id": card_id + "-b",
                        "strength": strength,
                        "evidence_status": "excluded",
                        "reason": "same explanation",
                    },
                ]
            },
        }

    cards = [
        card("rep-1", "one"),
        card("rep-1", "two"),
        card("rep-2", "one"),
        card("rep-1", "one", "PS4_Moderate"),
        card("rep-3", None),
    ]
    full = {
        "criterion_reviews": [{"criterion": "PS4", "aggregated_cards": cards}],
        "evidence_cards": [{"card_id": "rep-3", "scenario_id": "three"}],
    }
    groups = _compact_result(full)["criterion_reviews"][0]["other_card_results"]
    assert len(groups) == 5
    assert groups[-1]["scenario_id"] == "three"
    assert all(len(g["card_ids"]) == 2 for g in groups)
    assert all("card_id" not in g for g in groups)


def test_source_references_from_all_summary_sections_and_missing_source_diagnostics():
    """Only referenced sources are indexed; failed-source provenance remains visible."""
    source_ids = [
        "review",
        "population",
        "vcep",
        "omim",
        "prior",
        "rule",
        "selected",
        "alternate",
        "failure",
    ]
    facts = [
        {
            "fact_id": key,
            "status": "success",
            "tool_name": "fixture",
            "provider_version": "1",
        }
        for key in source_ids
    ]
    facts[-1].update(
        status="failed",
        provenance=["https://example.org/provider"],
        failure_details={"failure_code": "provider_failed", "retry_attempts": 2},
    )
    full = {
        "final_classification_allowed": False,
        "source_facts": [
            *facts,
            deepcopy(facts[0]),
            {"fact_id": "unused", "status": "success"},
        ],
        "criterion_reviews": [
            {"criterion": "PP1", "candidate_source_fact_ids": ["review", "review"]}
        ],
        "population_observations": [{"fact_id": "population"}],
        "vcep_assertions": [{"source_fact_id": "vcep"}],
        "omim_context": {"source_fact_ids": ["omim"]},
        "prior_variant_candidates": [{"source_fact_ids": ["prior"]}],
        "rule_context": {"source_fact_ids": ["rule"]},
        "consequence_profile": {
            "observations": [
                {
                    "provider": "fixture",
                    "source_fact_id": "selected",
                    "transcript": "NM_1",
                    "observation_role": "selected",
                },
                {
                    "provider": "fixture",
                    "source_fact_id": "alternate",
                    "transcript": "NM_2",
                    "observation_role": "alternate_transcript",
                },
            ]
        },
        "limitations": ["same", "same", "different"],
        "conflict_report": {
            "conflicts": [
                {"reason": "x", "case_id": "one"},
                {"reason": "x", "case_id": "one"},
                {"reason": "x", "case_id": "two"},
            ]
        },
    }
    original = deepcopy(full)
    summary = _compact_result(full)
    assert [r["fact_id"] for r in summary["source_facts"]] == source_ids
    failed = {**summary["source_fact_defaults"], **summary["source_facts"][-1]}
    assert failed["provider_version"] == "1"
    assert failed["provenance"] == ["https://example.org/provider"]
    assert summary["limitations"] == ["same", "different"]
    assert len(summary["conflict_report"]["conflicts"]) == 2
    assert full == original
    full["criterion_reviews"][0]["candidate_source_fact_ids"].extend(
        ["missing", "missing"]
    )
    summary = _compact_result(full)
    assert summary["limitations"].count("source_reference_unresolved: missing") == 1
    assert "missing" not in {r["fact_id"] for r in summary["source_facts"]}


def test_more_literature_keeps_all_identifiers_without_new_actions(
    replay, check_acmg_summary
):
    """Large clinical indexes remain visible; size does not change workflow or scores."""
    small = _compact_result(replay)
    replay["literature_candidates"].extend(
        [
            {
                "pmid": str(80000000 + i),
                "doi": f"10.0000/serializer-fixture-{i}",
                "match_class": "gene_disease_background",
                "full_text_status": "abstract_only",
                "sources": ["PubMed_search_articles"],
            }
            for i in range(400)
        ]
    )
    large = _compact_result(replay)
    assert check_acmg_summary(large) > 40_000
    assert len(large["literature_candidates"]) == 464
    assert large["literature_candidates"][-1]["pmid"] == "80000399"
    for key in (
        "next_actions",
        "status",
        "guard_context",
        "automatic_bayesian",
        "verified_bayesian",
        "user_selected_bayesian",
    ):
        assert small[key] == large[key]
