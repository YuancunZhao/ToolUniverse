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


# --------------------------------------------------------------------------- #
# 2026-10-23 review (Batch C): the single-detail path crashed before and
# after the shared parser. Top-level envelope damage (``data`` a list,
# ``result`` null, the UID record a non-empty list) hit raw
# AttributeError inside ``_fetch_variant``; the detail assemblies then
# indexed ``variation_set``/``variation_loc`` with ``[0]`` (IndexError on
# empty/null) and ``.get()`` on possibly-null
# ``clinical_impact_classification``/``oncogenicity_classification``/
# ``trait_set``. New contract:
#
# - ``_fetch_variant`` type-checks the envelope BEFORE any nested .get();
# - absent/null/empty optional containers mean "not provided" and keep
#   the existing empty output fields (first-record selection unchanged);
# - present-but-corrupt containers (wrong container type, non-object
#   elements, non-null non-object classification scalars) are explicit
#   errors naming the field -- raised before any citation fetch;
# - all new counter-examples run the REAL ``_fetch_variant`` with only
#   ``_make_request`` mocked.
# --------------------------------------------------------------------------- #
def _healthy_detail_record(uid="13961"):
    return {
        "uid": uid,
        "title": "NM_007294.4(BRCA1):c.5266dupC",
        "accession": "VCV000013961",
        "obj_type": "simple variant",
        "chr_sort": "17",
        "genes": [{"symbol": "BRCA1"}],
        "germline_classification": {
            "description": "Pathogenic",
            "review_status": "reviewed by expert panel",
            "trait_set": [{"trait_name": "Hereditary breast and ovarian cancer syndrome"}],
        },
        "variation_set": [
            {
                "variation_name": "NM_007294.4(BRCA1):c.5266dupC",
                "variation_loc": [
                    {
                        "assembly_name": "GRCh38",
                        "chr": "17",
                        "start": 43045711,
                        "stop": 43045711,
                        "band": "17q21.31",
                    },
                    {
                        "assembly_name": "GRCh37",
                        "chr": "17",
                        "start": 41245466,
                        "stop": 41245466,
                        "band": "17q21.31(p37)",
                    },
                ],
            }
        ],
        "clinical_impact_classification": None,
        "oncogenicity_classification": None,
    }


def _fetch_with_result(result):
    """Run the REAL _fetch_variant with only the HTTP call mocked."""
    tool = ClinVarGetVariantDetails({"name": "ClinVar_get_variant_details"})
    with patch.object(
        ClinVarGetVariantDetails, "_make_request", return_value=result
    ):
        return tool._fetch_variant("13961")


def _run_details(record, citations=None):
    """Run the REAL details handler (real _fetch_variant); citations are
    stubbed only where the record is expected to be healthy."""
    tool = ClinVarGetVariantDetails({"name": "ClinVar_get_variant_details"})
    if citations is None:
        citations = patch.object(
            ClinVarGetVariantDetails,
            "_submitter_citations",
            side_effect=AssertionError("citations must not be fetched"),
        )
    with patch.object(
        ClinVarGetVariantDetails,
        "_make_request",
        return_value=_esummary_result({"13961": record}),
    ), citations:
        return tool.run({"variant_id": "13961"})


def _empty_citations_stub():
    return patch.object(
        ClinVarGetVariantDetails,
        "_submitter_citations",
        return_value={
            "citations": [],
            "citations_complete": False,
            "citation_warnings": ["stubbed"],
        },
    )


@pytest.mark.parametrize(
    "result",
    [
        pytest.param({"status": "success", "data": []}, id="data-list"),
        pytest.param(
            {"status": "success", "data": {"result": None}}, id="result-null"
        ),
        pytest.param(
            {"status": "success", "data": {"result": [1, 2]}}, id="result-list"
        ),
        pytest.param(
            {"status": "success", "data": {"result": "uids"}},
            id="result-string",
        ),
    ],
)
def test_fetch_variant_rejects_malformed_envelope(result):
    fetch = _fetch_with_result(result)
    assert "error_result" in fetch, fetch
    error = fetch["error_result"]["error"]
    assert "malformed" in error.lower(), error
    assert "must be" in error, error


def test_fetch_variant_rejects_list_valued_uid_record():
    fetch = _fetch_with_result(_esummary_result({"13961": [1, 2, 3]}))
    assert "error_result" in fetch, fetch
    error = fetch["error_result"]["error"]
    assert "13961" in error, error
    assert "must be a json object" in error.lower(), error


def test_fetch_variant_keeps_not_found_path_for_absent_keys():
    # A missing data/result/uid is "no record found" (existing contract),
    # not a malformed-envelope error.
    fetch = _fetch_with_result({"status": "success", "data": {}})
    assert "error_result" in fetch, fetch
    error = fetch["error_result"]["error"]
    assert "no clinvar record found" in error.lower(), error


@pytest.mark.parametrize(
    "record, expect_location, expect_variation_name",
    [
        pytest.param(
            {**_healthy_detail_record(), "variation_set": None},
            "",
            "",
            id="variation-set-null",
        ),
        pytest.param(
            {**_healthy_detail_record(), "variation_set": []},
            "",
            "",
            id="variation-set-empty",
        ),
        # loc absent: the FIRST variation_set entry still supplies
        # variation_name; only the band is empty.
        pytest.param(
            {
                **_healthy_detail_record(),
                "variation_set": [
                    {"variation_name": "NM_007294.4:c.5266dupC", "variation_loc": None}
                ],
            },
            "",
            "NM_007294.4:c.5266dupC",
            id="variation-loc-null",
        ),
        pytest.param(
            {
                **_healthy_detail_record(),
                "variation_set": [
                    {"variation_name": "NM_007294.4:c.5266dupC", "variation_loc": []}
                ],
            },
            "",
            "NM_007294.4:c.5266dupC",
            id="variation-loc-empty",
        ),
        # Nulling only the classification scalars leaves the healthy
        # location fields in place -- empty output applies to the nulled
        # field, not the whole detail.
        pytest.param(
            {**_healthy_detail_record(), "clinical_impact_classification": None},
            "17q21.31",
            "NM_007294.4(BRCA1):c.5266dupC",
            id="clinical-impact-null",
        ),
        pytest.param(
            {**_healthy_detail_record(), "oncogenicity_classification": None},
            "17q21.31",
            "NM_007294.4(BRCA1):c.5266dupC",
            id="oncogenicity-null",
        ),
    ],
)
def test_details_optional_containers_absent_mean_empty_fields(
    record, expect_location, expect_variation_name
):
    result = _run_details(record, citations=_empty_citations_stub())
    assert result["status"] == "success", result
    data = result["data"]
    assert data["location"] == expect_location
    assert data["variation_name"] == expect_variation_name
    assert data["citations_complete"] is False


def test_clinical_significance_trait_set_absent_means_empty_traits():
    from tooluniverse.clinvar_tool import ClinVarGetClinicalSignificance

    record = _healthy_detail_record()
    record["germline_classification"] = {
        "description": "Pathogenic",
        "review_status": "reviewed by expert panel",
        "trait_set": None,
    }
    tool = ClinVarGetClinicalSignificance(
        {"name": "ClinVar_get_clinical_significance"}
    )
    with patch.object(
        ClinVarGetClinicalSignificance,
        "_make_request",
        return_value=_esummary_result({"13961": record}),
    ):
        result = tool.run({"variant_id": "13961"})
    assert result["status"] == "success", result
    assert result["data"]["germline_classification"]["traits"] == []
    assert result["data"]["clinical_impact"]["description"] == ""
    assert result["data"]["oncogenicity"]["description"] == ""


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(
            {**_healthy_detail_record(), "variation_set": {"0": {}}},
            id="variation-set-dict",
        ),
        pytest.param(
            {**_healthy_detail_record(), "variation_set": ["entry"]},
            id="variation-set-string-entry",
        ),
        pytest.param(
            {
                **_healthy_detail_record(),
                "variation_set": [
                    {"variation_name": "x", "variation_loc": {"band": "17"}}
                ],
            },
            id="variation-loc-dict",
        ),
        pytest.param(
            {
                **_healthy_detail_record(),
                "variation_set": [
                    {"variation_name": "x", "variation_loc": [17]}
                ],
            },
            id="variation-loc-int-entry",
        ),
        pytest.param(
            {**_healthy_detail_record(), "clinical_impact_classification": "impact"},
            id="clinical-impact-string",
        ),
        pytest.param(
            {**_healthy_detail_record(), "oncogenicity_classification": 3},
            id="oncogenicity-int",
        ),
        pytest.param(
            {
                **_healthy_detail_record(),
                "germline_classification": {
                    "description": "Pathogenic",
                    "trait_set": {"trait_name": "x"},
                },
            },
            id="trait-set-dict",
        ),
        pytest.param(
            {
                **_healthy_detail_record(),
                "germline_classification": {
                    "description": "Pathogenic",
                    "trait_set": ["Hereditary cancer"],
                },
            },
            id="trait-set-string-entry",
        ),
    ],
)
def test_details_corrupt_optional_containers_error_before_citations(record):
    result = _run_details(record)
    assert result["status"] == "error", result
    error = result["error"].lower()
    assert "malformed" in error, error
    assert "must be" in error, error


def test_details_first_record_selection_semantics_unchanged():
    # Two variation_set entries with two loc entries each: the FIRST
    # variation_set entry and its FIRST loc entry supply the fields --
    # exactly the pre-existing selection, no assembly inference added.
    record = _healthy_detail_record()
    record["variation_set"] = [
        {
            "variation_name": "FIRST_NAME",
            "variation_loc": [
                {"assembly_name": "GRCh38", "band": "FIRST_BAND"},
                {"assembly_name": "GRCh37", "band": "SECOND_BAND"},
            ],
        },
        {
            "variation_name": "SECOND_NAME",
            "variation_loc": [{"assembly_name": "GRCh38", "band": "THIRD_BAND"}],
        },
    ]
    result = _run_details(record, citations=_empty_citations_stub())
    assert result["status"] == "success", result
    data = result["data"]
    assert data["variation_name"] == "FIRST_NAME"
    assert data["location"] == "FIRST_BAND"


def test_details_healthy_full_record_keeps_public_fields():
    result = _run_details(_healthy_detail_record(), citations=_empty_citations_stub())
    assert result["status"] == "success", result
    data = result["data"]
    assert data["accession"] == "VCV000013961"
    assert data["location"] == "17q21.31"
    assert data["variation_name"] == "NM_007294.4(BRCA1):c.5266dupC"
    assert data["genes"] == ["BRCA1"]
    assert data["clinical_significance"] == "Pathogenic"
    # single raw copy, and the citation receipt fields keep their shape
    assert list(data.keys()).count("raw_data") == 1
    assert data["citations"] == []
    assert data["citations_complete"] is False


# --------------------------------------------------------------------------- #
# Same contracts through REAL SMCP registrations (fastmcp in-memory
# client); every HTTP request is mocked.
# --------------------------------------------------------------------------- #
def test_smcp_registered_details_reports_corrupt_optional_container():
    import asyncio

    from fastmcp import Client

    from tooluniverse.smcp import SMCP

    record = _healthy_detail_record()
    record["variation_set"] = {"0": {}}

    def fake_request(_self, path, params):
        assert "esummary" in path, path
        return _esummary_result({"13961": record})

    async def drive():
        server = SMCP(name="detail-corrupt-container-test")
        with patch.object(
            ClinVarGetVariantDetails, "_make_request", new=fake_request
        ), patch.object(
            ClinVarGetVariantDetails,
            "_submitter_citations",
            new=lambda self, vid: {
                "citations": [],
                "citations_complete": False,
                "citation_warnings": [],
            },
        ):
            async with Client(server) as client:
                call = await client.call_tool(
                    "ClinVar_get_variant_details", {"variant_id": "13961"}
                )
        return json.loads(call.content[0].text)

    payload = asyncio.run(drive())
    assert payload["status"] == "error", payload
    error = payload["error"].lower()
    assert "variation_set" in error, error
    assert "must be" in error, error


def test_smcp_registered_clinical_significance_null_containers_ok():
    import asyncio

    from fastmcp import Client

    from tooluniverse.clinvar_tool import ClinVarGetClinicalSignificance
    from tooluniverse.smcp import SMCP

    record = _healthy_detail_record()
    record["germline_classification"]["trait_set"] = []
    # clinical_impact/oncogenicity already None in the healthy record

    def fake_request(_self, path, params):
        assert "esummary" in path, path
        return _esummary_result({"13961": record})

    async def drive():
        server = SMCP(name="clin-sig-null-containers-test")
        with patch.object(
            ClinVarGetClinicalSignificance, "_make_request", new=fake_request
        ):
            async with Client(server) as client:
                call = await client.call_tool(
                    "ClinVar_get_clinical_significance",
                    {"variant_id": "13961"},
                )
        return json.loads(call.content[0].text)

    payload = asyncio.run(drive())
    assert payload["status"] == "success", payload
    germline = payload["data"]["germline_classification"]
    assert germline["traits"] == []
    assert germline["description"] == "Pathogenic"
    assert payload["data"]["clinical_impact"]["description"] == ""
    assert payload["data"]["oncogenicity"]["description"] == ""
