"""Tests for EuropePMC_get_full_text (EuropePMCStructuredFullTextTool)."""

import pytest
from tooluniverse import ToolUniverse
from tooluniverse.europe_pmc_tool import EuropePMCStructuredFullTextTool


class _FakeResponse:
    def __init__(self, *, status_code=200, text="", url=""):
        self.status_code = status_code
        self.text = text
        self.url = url or "https://example.test/fullTextXML"
        self.headers = {"Content-Type": "application/xml"}


@pytest.fixture(scope="module")
def tu():
    t = ToolUniverse()
    t.load_tools()
    return t


def _run(tu, **kwargs):
    return tu.run_one_function(
        {"name": "EuropePMC_get_full_text", "arguments": kwargs}
    )


# ------------------------------------------------------------------
# Tool loading
# ------------------------------------------------------------------


def test_tool_registered(tu):
    assert "EuropePMC_get_full_text" in tu.all_tool_dict
    tool = tu.all_tool_dict["EuropePMC_get_full_text"]
    assert tool["type"] == "EuropePMCStructuredFullTextTool"


def test_tool_schema_declares_provenance_and_truncation(tu):
    """The public return contract exposes retrieval provenance and completeness."""
    schema = tu.all_tool_dict["EuropePMC_get_full_text"]["return_schema"]
    success_schema = next(
        branch
        for branch in schema["oneOf"]
        if "status" in branch.get("properties", {})
    )
    properties = success_schema["properties"]
    assert {
        "source",
        "format",
        "url",
        "retrieval_trace",
        "truncated",
        "truncated_sections",
    } <= properties.keys()
    assert {"status", "data"} <= set(success_schema["required"])


# ------------------------------------------------------------------
# Success path: PMC ID
# ------------------------------------------------------------------


@pytest.mark.network
def test_pmcid_success(tu):
    result = _run(tu, pmcid="PMC7096075")
    assert result["status"] == "success"
    data = result["data"]
    assert "Ashwagandha" in data["title"]
    assert data["abstract"] is not None
    assert len(data["abstract"]) > 100


@pytest.mark.network
def test_pmcid_sections(tu):
    result = _run(tu, pmcid="PMC7096075")
    sections = result["data"]["sections"]
    assert "introduction" in sections
    assert "methods" in sections
    assert "results" in sections
    assert "discussion" in sections
    assert "conclusions" in sections


@pytest.mark.network
def test_pmcid_figures(tu):
    result = _run(tu, pmcid="PMC7096075")
    data = result["data"]
    assert data["figure_count"] >= 1
    assert len(data["figures"]) == data["figure_count"]
    fig = data["figures"][0]
    assert "label" in fig
    assert "caption" in fig


@pytest.mark.network
def test_pmcid_tables(tu):
    result = _run(tu, pmcid="PMC7096075")
    data = result["data"]
    assert data["table_count"] >= 1
    assert len(data["tables"]) == data["table_count"]
    tbl = data["tables"][0]
    assert "label" in tbl
    assert "caption" in tbl


@pytest.mark.network
def test_pmcid_references(tu):
    result = _run(tu, pmcid="PMC7096075")
    data = result["data"]
    assert data["reference_count"] >= 1
    assert len(data["references"]) == data["reference_count"]
    ref = data["references"][0]
    assert "id" in ref
    assert "text" in ref
    assert len(ref["text"]) > 10


@pytest.mark.network
def test_metadata(tu):
    result = _run(tu, pmcid="PMC7096075")
    meta = result["metadata"]
    assert meta["pmcid"] == "PMC7096075"
    assert meta["source"] is not None
    assert meta["format"] == "xml"


# ------------------------------------------------------------------
# PMC ID normalisation
# ------------------------------------------------------------------


@pytest.mark.network
def test_pmcid_without_prefix(tu):
    result = _run(tu, pmcid="7096075")
    assert result["status"] == "success"
    assert result["metadata"]["pmcid"] == "PMC7096075"


# ------------------------------------------------------------------
# Success path: PMID (auto-resolved)
# ------------------------------------------------------------------


@pytest.mark.network
def test_pmid_resolution(tu):
    result = _run(tu, pmid="32226684")
    assert result["status"] == "success"
    assert "Ashwagandha" in result["data"]["title"]
    assert result["metadata"]["pmcid"] == "PMC7096075"


# ------------------------------------------------------------------
# Error paths
# ------------------------------------------------------------------


def test_no_params(tu):
    result = _run(tu)
    assert result["status"] == "error"
    assert "pmcid" in result["error"].lower() or "pmid" in result["error"].lower()


@pytest.mark.network
def test_invalid_pmid(tu):
    result = _run(tu, pmid="999999999")
    assert result["status"] == "error"
    assert "resolve" in result["error"].lower() or "not" in result["error"].lower()


def test_invalid_pmcid_format(tu):
    result = _run(tu, pmcid="not_a_number_at_all")
    # Should either error gracefully or attempt and fail
    assert result["status"] in ("error", "success")


# ------------------------------------------------------------------
# max_section_chars truncation
# ------------------------------------------------------------------


@pytest.mark.network
def test_max_section_chars(tu):
    result = _run(tu, pmcid="PMC7096075", max_section_chars=1000)
    assert result["status"] == "success"
    sections = result["data"]["sections"]
    for key, val in sections.items():
        if isinstance(val, str):
            # Sections longer than 1000 chars should be truncated
            assert len(val) <= 1020  # 1000 + " ... [truncated]"


def test_structured_fulltext_reports_provenance_and_truncation(monkeypatch):
    """Structured XML reports its actual source and section truncation."""
    xml_payload = (
        "<article><front><article-meta><title-group><article-title>Fixture</article-title>"
        "</title-group><abstract>Fixture abstract.</abstract></article-meta></front>"
        "<body><sec sec-type='results'><title>Results</title><p>"
        + ("A" * 1500)
        + "</p></sec></body></article>"
    )

    def fake_request_with_retry(
        session, method, url, *, timeout=None, max_attempts=None, **kwargs
    ):
        return _FakeResponse(status_code=200, text=xml_payload, url=url)

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )
    tool = EuropePMCStructuredFullTextTool({"name": "EuropePMC_get_full_text"})
    result = tool.run({"pmcid": "PMC111", "max_section_chars": 1000})

    assert result["status"] == "success"
    assert result["source"] == "Europe PMC fullTextXML"
    assert result["format"] == "xml"
    assert result["url"].endswith("/PMC111/fullTextXML")
    assert result["retrieval_trace"]
    assert result["truncated"] is True
    assert result["truncated_sections"] == ["results"]
    assert result["metadata"]["source"] == result["source"]
