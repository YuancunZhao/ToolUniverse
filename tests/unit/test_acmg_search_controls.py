"""Retrieval budgets are explicit engineering controls, not evidence rules."""

from copy import deepcopy

import pytest

from tooluniverse.acmg.collector import (
    ACMGEvidencePipeline,
    SourceCall,
    _literature_control_errors,
    _fulltext_selected,
    _literature_search_summary,
)
from tooluniverse.acmg.models import SourceFact
from tooluniverse.acmg.source_adapters import adapt_source_output

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", [True, 0, -1, 1001, 1.5, "50", None])
def test_invalid_search_budget_is_rejected_before_provider_calls(value):
    """Only bounded integers are legal, with no silent coercion."""
    assert _literature_control_errors({"literature_search_limits": {"pubmed": value}})


def test_search_controls_and_fulltext_selection():
    """An empty fulltext scope does not change evidence matching semantics."""
    assert not _literature_control_errors(
        {"literature_search_limits": {"pubmed": 1000}}
    )
    assert _literature_control_errors({"literature_search_limits": {"unknown": 1}})
    assert _literature_control_errors({"fulltext_match_classes": ["invented"]})
    candidate = {"match_class": "gene_disease_background"}
    original = deepcopy(candidate)
    assert not _fulltext_selected(candidate, {})
    assert _fulltext_selected(
        candidate, {"fulltext_match_classes": ["gene_disease_background"]}
    )
    assert not _fulltext_selected(
        {"match_class": "exact_variant_match"}, {"fulltext_match_classes": []}
    )
    assert candidate == original


@pytest.mark.parametrize(
    "budget,mode,expected_pages,stop",
    [
        (10, "normal", [0], "budget_exhausted"),
        (30, "normal", [0, 1, 2], "budget_exhausted"),
        (30, "filtered", [0, 1, 2], "budget_exhausted"),
        (30, "repeated", [0, 1], "repeated_page"),
        (30, "maintenance", [0], "maintenance"),
        (30, "failure", [0], "technical_failure"),
    ],
)
def test_pubtator_pages_follow_raw_budget(
    monkeypatch, budget, mode, expected_pages, stop
):
    """Low-score filtering does not consume less budget or retry maintenance pages."""
    pipeline = ACMGEvidencePipeline(object())

    def call(name, params, category):
        page = params.get("page", 0)
        rows = (
            []
            if mode == "filtered"
            else [{"pmid": str(page * 10 + i)} for i in range(10)]
        )
        failed = mode in {"maintenance", "failure"}
        return SourceCall(
            name,
            category,
            "failed" if failed else "success",
            result={
                "results": rows,
                "status_code": 400 if mode == "maintenance" else 503 if failed else 200,
                "search_counts": {
                    "provider_returned_count": 10,
                    "filtered_count": 10 if mode == "filtered" else 0,
                    "page_hash": "same" if mode == "repeated" else str(page),
                },
            },
            arguments=params,
        )

    monkeypatch.setattr(
        pipeline,
        "_source_specs",
        lambda *_: [
            ("ClinVar_get_clinical_significance", {}, "source_assertion"),
            (
                "PubTator3_LiteratureSearch",
                {"query": "TEST", "page": 0, "limit": 10},
                "literature",
            ),
        ],
    )
    monkeypatch.setattr(
        pipeline, "_call_batch", lambda specs: [call(*spec) for spec in specs]
    )
    monkeypatch.setattr(pipeline, "_call", call)
    calls = pipeline._collect_sources(
        {"literature_search_limits": {"pubtator": budget}}, {}
    )
    pages = [item for item in calls if item.tool_name == "PubTator3_LiteratureSearch"]
    assert [item.arguments["page"] for item in pages] == expected_pages
    assert pages[-1].result["search_counts"]["stop_reason"] == stop


@pytest.mark.parametrize(
    "raw,total",
    [
        ({"data": {"articles": [{"pmid": "1"}]}}, None),
        ({"data": {"articles": []}, "metadata": {"total_results": 0}}, 0),
        (
            {"data": {"articles": [{"pmid": "1"}]}, "metadata": {"total_results": 23}},
            23,
        ),
    ],
)
def test_search_total_is_not_inferred_from_page_length(raw, total):
    """Unknown totals stay null in summary; an explicit zero stays zero."""
    features = adapt_source_output("EuropePMC_search_articles", raw)[
        "reviewable_features"
    ]
    fact = SourceFact(
        fact_id="search-1",
        tool_name="EuropePMC_search_articles",
        status="success",
        query_identity={},
        result_identity={},
        raw_result_hash="fixture",
        features=features,
        request_arguments={"query": "TEST", "limit": 100},
    )
    row = _literature_search_summary({fact.fact_id: fact}, {})[0]
    assert row["total_available"] == total
    assert row["source_fact_id"] == "search-1"


def test_pubmed_unknown_total_and_explicit_zero():
    """The independent PubMed adapter uses the same unknown-total policy."""
    for total in (None, 0, 123):
        raw = {"data": [{"pmid": "1"}]}
        if total is not None:
            raw["metadata"] = {"total": total}
        features = adapt_source_output("PubMed_search_articles", raw)[
            "reviewable_features"
        ]
        assert features["total_available"] == total


def test_empty_fulltext_scope_does_not_affect_explicit_reanchoring(monkeypatch):
    """Normal candidate selection and proposal retrieval are separate callers."""
    pipeline = ACMGEvidencePipeline(object())
    fetched = []

    def fetch(candidates, existing_calls=()):
        fetched.extend(candidates)
        return {}, []

    monkeypatch.setattr(pipeline, "_fetch_literature_documents", fetch)
    candidate = {"pmid": "1", "match_class": "exact_variant_match"}
    assert (
        pipeline._automatic_fulltext_calls([candidate], {"fulltext_match_classes": []})
        == []
    )
    assert not fetched
    pipeline._fetch_literature_documents([candidate])
    assert fetched == [candidate]
