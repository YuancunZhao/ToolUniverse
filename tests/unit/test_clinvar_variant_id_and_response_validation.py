"""Regression guard for Fix-D-20260918: variant_id normalization and eSearch
response validation.

Confirmed live: ``rs2151556776[uid]`` (an rsID pasted into variant_id)
returned count 0 with an empty translation, while the same rsID as free text
hits VCV 2737810 -- the [uid] index only matches numeric variation IDs, so
any non-numeric payload produced a guaranteed-false empty. And a broken or
truncated eSearch response (``{"status": "success", "data": {}}``) passed
through as the caller's fake success, degrading to "query succeeded, zero
results".

Now:
- variant_id accepts a positive integer, its digit-string form, or a
  suffix-free VCV accession, and is normalized to ``<N>[uid]`` BEFORE any
  request; rsIDs get an explicit error naming the free-text form that works
  (query="rs..."), versioned VCV / zero / blank / bool / other types are
  rejected, and the normalized ID is disclosed in search_params;
- the eSearch payload must carry a parseable count, a list idlist, and a
  querytranslation key -- a structural anomaly is a hard error with the raw
  payload attached, never a success-with-zero;
- warninglist entries (e.g. phrasesnotfound on a real OR query that still
  has hits) are surfaced as query_warnings, never fatal;
- a genuinely-empty valid result (count 0, empty idlist, translation
  present) is still a success.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import (
    ClinVarSearchVariants,
    _esearch_structural_error,
    _normalize_variant_id,
)

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


_ESEARCH_OK = {
    "status": "success",
    "data": {
        "esearchresult": {
            "count": "1",
            "idlist": ["2737810"],
            "querytranslation": "2737810[uid]",
        }
    },
}


def _run(arguments, payload=_ESEARCH_OK):
    with patch.object(
        ClinVarSearchVariants, "_make_request", return_value=payload
    ) as mock_request:
        result = _tool().run(arguments)
    term = next(
        (c[0][1]["term"] for c in mock_request.call_args_list if "term" in c[0][1]),
        None,
    )
    return result, term


# ---------- variant_id normalization ----------


@pytest.mark.parametrize("raw", [2737810, "2737810", "VCV002737810", "vcv002737810"])
def test_valid_variant_id_forms_query_uid(raw):
    result, term = _run({"variant_id": raw})
    assert result["status"] == "success"
    assert term == "2737810[uid]"
    assert result["data"]["search_params"]["variant_id_used"] == 2737810


def test_rsid_in_variant_id_is_error_with_freetext_hint():
    result, term = _run({"variant_id": "rs2151556776"})
    assert result["status"] == "error"
    assert 'query="rs2151556776"' in result["error"]
    assert term is None  # no request dispatched


def test_versioned_vcv_accession_rejected():
    result, _ = _run({"variant_id": "VCV002737810.1"})
    assert result["status"] == "error"
    assert "version suffix" in result["error"]


@pytest.mark.parametrize("raw", ["0", 0, "-5", ""])
def test_zero_blank_negative_rejected_before_request(raw):
    result, term = _run({"variant_id": raw})
    assert result["status"] == "error"
    assert term is None


@pytest.mark.parametrize("raw", [True, False])
def test_boolean_variant_id_rejected(raw):
    result, _ = _run({"variant_id": raw})
    assert result["status"] == "error"
    assert "boolean" in result["error"]


def test_float_and_garbage_variant_id_rejected():
    result, _ = _run({"variant_id": 12.5})
    assert result["status"] == "error"
    result, _ = _run({"variant_id": "VCV00abc"})
    assert result["status"] == "error"
    assert "suffix-free VCV accession" in result["error"]


def test_normalize_helper_direct():
    assert _normalize_variant_id("VCV002737810") == (2737810, None)
    assert _normalize_variant_id("2737810") == (2737810, None)
    uid, err = _normalize_variant_id("rs123")
    assert uid is None and "query=" in err


# ---------- eSearch structural validation ----------


def test_missing_esearchresult_is_structural_error_not_fake_success():
    result, term = _run({"gene": "NF1"}, payload={"status": "success", "data": {}})
    assert result["status"] == "error"
    assert "structurally invalid" in result["error"]
    assert "esearchresult" in result["error"]
    assert result["raw_response"] == {}


@pytest.mark.parametrize(
    "esearch",
    [
        {"count": "1", "querytranslation": "x"},  # idlist missing
        {"count": "1", "idlist": "not-a-list", "querytranslation": "x"},
        {"idlist": [], "querytranslation": "x"},  # count missing
        {"count": "NaN", "idlist": [], "querytranslation": "x"},
        {"count": "1", "idlist": []},  # querytranslation missing
        "not-a-dict",
    ],
)
def test_broken_esearch_payloads_are_structural_errors(esearch):
    assert _esearch_structural_error({"esearchresult": esearch}) is not None


def test_valid_empty_result_is_still_success():
    payload = {
        "status": "success",
        "data": {
            "esearchresult": {
                "count": "0",
                "idlist": [],
                "querytranslation": "ZZZ[gene]",
            }
        },
    }
    result, _ = _run({"gene": "ZZZ"}, payload=payload)
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 0
    assert result["data"]["variant_ids"] == []


def test_request_failure_propagates_as_error():
    result, _ = _run(
        {"gene": "NF1"}, payload={"status": "error", "error": "HTTP 500"}
    )
    assert result["status"] == "error"
    assert "HTTP 500" in result["error"]


def test_phrasesnotfound_with_hits_is_warning_not_failure():
    payload = {
        "status": "success",
        "data": {
            "esearchresult": {
                "count": "3",
                "idlist": ["1", "2", "3"],
                "querytranslation": '(a[Variant name] OR b[Variant name]) AND NF1[gene]',
                "warninglist": {"phrasesnotfound": ["a[Variant name]"]},
            }
        },
    }
    result, _ = _run(
        {"gene": "NF1", "variant_name": ["a", "b"]}, payload=payload
    )
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 3
    assert any(
        "phrasesnotfound" in w for w in result["data"].get("query_warnings", [])
    )


def test_structural_error_includes_raw_response_for_disclosure():
    payload = {"status": "success", "data": {"esearchresult": {"count": "1"}}}
    result, _ = _run({"gene": "NF1"}, payload=payload)
    assert result["status"] == "error"
    assert result["raw_response"] == payload["data"]


def test_hyphen_retry_failure_keeps_original_result_not_fake_empty():
    """A structurally broken fallback must not masquerade as success-zero.

    The hyphen retry only swaps in the fallback when it is a success with
    count > 0; a broken fallback leaves the (valid) original result, and a
    broken ORIGINAL is a structural error -- neither path can produce a
    fake "success, 0 results".
    """
    # Original result valid with 0 hits; fallback (2nd call) broken.
    payloads = [
        {
            "status": "success",
            "data": {
                "esearchresult": {
                    "count": "0",
                    "idlist": [],
                    "querytranslation": "BRCA-2[gene]",
                }
            },
        },
        {"status": "success", "data": {}},  # broken fallback
    ]
    with patch.object(
        ClinVarSearchVariants, "_make_request", side_effect=payloads
    ) as mock_request:
        result = _tool().run({"gene": "BRCA-2"})
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 0
    # at most: esearch + hyphen-retry + gene-resolution attempts, all
    # individually guarded -- and none turned the result into an error
    assert mock_request.call_count >= 1
