"""Regression guards for the 2026-10-14 follow-up: per-record malformed
esummary isolation.

Before this fix, ``_parse_variant_summary`` read ``genes`` and
``germline_classification`` with bare attribute access and ``.get``
chains, so a single structurally damaged record inside an esummary
response crashed the WHOLE call with a raw TypeError/AttributeError (or,
for an empty object, produced an all-blank "valid" detail). Contract
pinned here (plan Batch B):

- a shared STRICT parser validates one esummary record and raises
  ``ValueError`` naming the offending field; an empty object is not a
  valid record; ``genes``/``germline_classification`` are optional but,
  when present, must be a list of objects / an object; omitting them or
  omitting the clinical classification adds NO biological applicability
  condition -- the record stays valid with blank fields;
- the SEARCH tool isolates the damaged record: counts, IDs and the other
  healthy details are kept, the failed UID lands in
  ``missing_variant_ids``, the reason goes to ``warnings`` and
  ``details_complete`` is false;
- ``ClinVar_get_variant_details`` returns an explicit error for a
  malformed record BEFORE any citation fetch;
- the same contract holds when the tool is invoked through a REAL SMCP
  registration (fastmcp in-memory client) with all HTTP mocked.

All network access is mocked; no test reaches NCBI.
"""

import json
from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import (
    ClinVarGetVariantDetails,
    ClinVarSearchVariants,
)

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _esearch_result(count, ids):
    return {
        "status": "success",
        "data": {
            "esearchresult": {
                "idlist": ids,
                "count": str(count),
                "querytranslation": "qt[All Fields]",
            }
        },
    }


def _esummary_result(records):
    return {"status": "success", "data": {"result": records}}


def _healthy_record(uid, title="NM_1:c.1A>G"):
    """A record shaped like a real esummary variant payload."""
    return {
        "uid": uid,
        "title": title,
        "genes": [{"symbol": "NF1"}],
        "germline_classification": {
            "description": "Pathogenic",
            "review_status": "criteria provided, single submitter",
        },
    }


def _run_search_with_records(records):
    """Search returning ids 1..N; the esummary response maps as given."""
    ids = list(records)
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[_esearch_result(len(ids), ids), _esummary_result(records)],
    ):
        return tool.run({"gene": "NF1"})


# --------------------------------------------------------------------------- #
# Strict shared parser: malformed shapes are isolated, not crashed on
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "record",
    [
        pytest.param({}, id="empty-object"),
        pytest.param({"uid": "1", "genes": None}, id="genes-null"),
        pytest.param({"uid": "1", "genes": {}}, id="genes-dict"),
        pytest.param({"uid": "1", "genes": ["NF1"]}, id="genes-string-entry"),
        pytest.param({"uid": "1", "genes": [123]}, id="genes-int-entry"),
        pytest.param(
            {"uid": "1", "germline_classification": None},
            id="germline-classification-null",
        ),
        pytest.param(
            {"uid": "1", "germline_classification": "Pathogenic"},
            id="germline-classification-string",
        ),
    ],
)
def test_malformed_record_is_isolated_and_named(record):
    result = _run_search_with_records({"1": record, "2": _healthy_record("2")})

    assert result["status"] == "success"
    data = result["data"]
    assert data["total_count"] == 2
    assert data["variant_ids"] == ["1", "2"]
    assert [v["variant_id"] for v in data["variants"]] == ["2"]
    assert data["missing_variant_ids"] == ["1"]
    assert data["details_complete"] is False
    malformed_warnings = [w for w in data["warnings"] if "1" in w]
    assert malformed_warnings, data["warnings"]
    assert any(
        "malformed" in w.lower() for w in malformed_warnings
    ), malformed_warnings


def test_healthy_record_content_survives_alongside_malformed():
    result = _run_search_with_records(
        {"1": {"uid": "1", "genes": None}, "2": _healthy_record("2")}
    )

    data = result["data"]
    (kept,) = data["variants"]
    # Content assertions, not just IDs and completeness: the healthy
    # record must carry its actual title, gene symbol and classification.
    assert kept["title"] == "NM_1:c.1A>G"
    assert kept["genes"] == ["NF1"]
    assert kept["clinical_significance"] == "Pathogenic"
    assert kept["review_status"] == "criteria provided, single submitter"


def test_optional_fields_omitted_remain_valid():
    record = {
        "uid": "1",
        "title": "NM_1:c.1A>G",
        # no `genes` key, no `germline_classification` key: a record
        # without a clinical classification is still a valid detail.
    }
    result = _run_search_with_records({"1": record})

    data = result["data"]
    assert data["details_complete"] is True
    assert data["missing_variant_ids"] == []
    (kept,) = data["variants"]
    assert kept["title"] == "NM_1:c.1A>G"
    assert kept["genes"] == []
    assert kept["clinical_significance"] == ""


# --------------------------------------------------------------------------- #
# Details entry point: explicit error, no citation fetch afterwards
# --------------------------------------------------------------------------- #
def test_details_tool_errors_before_citation_fetch():
    tool = ClinVarGetVariantDetails({"name": "ClinVar_get_variant_details"})
    with (
        patch.object(
            ClinVarGetVariantDetails,
            "_make_request",
            return_value=_esummary_result({"13961": {"uid": "13961", "genes": None}}),
        ),
        patch.object(
            ClinVarGetVariantDetails,
            "_submitter_citations",
            side_effect=AssertionError("citations must not be fetched"),
        ) as citations,
    ):
        result = tool.run({"variant_id": "13961"})

    assert result["status"] == "error"
    assert "malformed" in result["error"].lower()
    assert "genes" in result["error"].lower()
    citations.assert_not_called()


# --------------------------------------------------------------------------- #
# Same contract through a REAL SMCP registration (fastmcp in-memory
# client); every HTTP request is mocked.
# --------------------------------------------------------------------------- #
def test_smcp_registered_search_discloses_partial_details():
    import asyncio

    from fastmcp import Client

    from tooluniverse.smcp import SMCP

    def fake_request(_self, path, params):
        if "esearch" in path:
            return _esearch_result(2, ["1", "2"])
        return _esummary_result(
            {"1": {"uid": "1", "genes": None}, "2": _healthy_record("2")}
        )

    async def drive():
        server = SMCP(name="malformed-record-test")
        with patch.object(ClinVarSearchVariants, "_make_request", new=fake_request):
            async with Client(server) as client:
                call = await client.call_tool(
                    "ClinVar_search_variants", {"gene": "NF1"}
                )
        return json.loads(call.content[0].text)

    payload = asyncio.run(drive())
    assert payload["status"] == "success"
    data = payload["data"]
    assert data["total_count"] == 2
    assert [v["variant_id"] for v in data["variants"]] == ["2"]
    assert data["missing_variant_ids"] == ["1"]
    assert data["details_complete"] is False
    assert any("malformed" in w.lower() for w in data["warnings"])
    (kept,) = data["variants"]
    assert kept["genes"] == ["NF1"]
    assert kept["clinical_significance"] == "Pathogenic"
