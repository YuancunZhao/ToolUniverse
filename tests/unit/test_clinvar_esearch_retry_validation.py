"""Regression battery for unified ClinVar eSearch validation (Fix-R1-20260922).

Every eSearch request -- the first query, the three replacement retries
(hyphen-stripped gene, alias-resolved gene, condition free-text) and the
count-only zero-attribution lookups -- now goes through the same
``_validate_esearch_payload`` entry point, with two failure disciplines:

* a broken payload or an explicit API error on the first query or a
  REPLACEMENT retry is an explicit error -- it must never degrade into
  "success, zero results" (the zero would be attributed to biology when
  the pipeline is broken);
* a failure of an AUXILIARY lookup (the gene-alias resolver, the
  count-only attribution checks) keeps the valid original result and adds
  a warning, because those lookups only explain an already-valid zero.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants, _validate_esearch_payload

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _esearch(count, ids=None, translation="qt[All Fields]", esearch_extra=None):
    esearch = {
        "count": str(count),
        "idlist": ids if ids is not None else [],
        "querytranslation": translation,
    }
    if esearch_extra:
        esearch.update(esearch_extra)
    return {"status": "success", "data": {"esearchresult": esearch}}


def _run(arguments, side_effects):
    with patch.object(
        ClinVarSearchVariants, "_make_request", side_effect=side_effects
    ) as mock_request:
        result = _tool().run(arguments)
    return result, mock_request


# ---------- validator unit cases ----------


@pytest.mark.parametrize(
    "esearch",
    [
        {"count": "1", "idlist": [], "querytranslation": "x"},  # ok: retmax=0 style
        {"count": 7, "idlist": ["16870"], "querytranslation": "x"},
    ],
)
def test_validator_accepts_wellformed_payloads(esearch):
    error, warnings = _validate_esearch_payload({"esearchresult": esearch})
    assert error is None
    assert warnings == []


def test_validator_accepts_positive_count_with_empty_idlist():
    """A count-only query (retmax=0) legitimately pairs count > 0 with an
    empty idlist; count is never checked against the idlist length."""
    error, _ = _validate_esearch_payload(
        {"esearchresult": {"count": "99", "idlist": [], "querytranslation": "x"}}
    )
    assert error is None


@pytest.mark.parametrize(
    "translation", [None, "", "   ", 123, ["x"]],
)
def test_blank_or_null_translation_rejected(translation):
    error, _ = _validate_esearch_payload(
        {"esearchresult": {"count": "1", "idlist": [], "querytranslation": translation}}
    )
    assert error is not None
    assert "querytranslation" in error


@pytest.mark.parametrize("count", [-1, "-1", "--1", "1.5", 1.5, "abc", True, None])
def test_negative_or_malformed_count_rejected(count):
    error, _ = _validate_esearch_payload(
        {"esearchresult": {"count": count, "idlist": [], "querytranslation": "x"}}
    )
    assert error is not None
    assert "count" in error


@pytest.mark.parametrize("idlist", ["16870", {"0": "16870"}, 16870])
def test_non_list_idlist_rejected(idlist):
    error, _ = _validate_esearch_payload(
        {"esearchresult": {"count": "1", "idlist": idlist, "querytranslation": "x"}}
    )
    assert error is not None
    assert "idlist" in error


@pytest.mark.parametrize("uid", [123, "12a", "16 870", True])
def test_non_uid_idlist_entries_rejected(uid):
    error, _ = _validate_esearch_payload(
        {"esearchresult": {"count": "1", "idlist": [uid], "querytranslation": "x"}}
    )
    assert error is not None
    assert "idlist" in error


def test_top_level_api_error_rejected():
    error, _ = _validate_esearch_payload(
        {"error": "Invalid db name", "esearchresult": {}}
    )
    assert error is not None
    assert "API error" in error


def test_inner_api_error_rejected():
    error, _ = _validate_esearch_payload(
        {
            "esearchresult": {
                "count": "0",
                "idlist": [],
                "querytranslation": "x",
                "error": "Invalid term",
            }
        }
    )
    assert error is not None
    assert "API error" in error


def test_phrasesnotfound_in_real_errorlist_position_is_retained_warning():
    """errorlist is phrasesnotfound's REAL position in eSearch responses,
    and a real OR query can report it while still returning valid hits."""
    error, warnings = _validate_esearch_payload(
        {
            "esearchresult": {
                "count": "3",
                "idlist": ["1", "2", "3"],
                "querytranslation": "a OR b",
                "errorlist": {"phrasesnotfound": ["zzz[Variant name]"]},
                "warninglist": {"outputmessages": ["ok"]},
            }
        }
    )
    assert error is None
    assert any("phrasesnotfound" in w for w in warnings)
    assert any("outputmessages" in w for w in warnings)


# ---------- first query ----------


def test_first_query_api_error_is_error_not_fake_success():
    result, _ = _run(
        {"gene": "NF1"},
        [{"status": "success", "data": {"error": "Invalid db name"}}],
    )
    assert result["status"] == "error"
    assert "API error" in result["error"]


def test_first_query_negative_count_is_error():
    result, _ = _run(
        {"gene": "NF1"},
        [_esearch(0, translation="x[All Fields]", esearch_extra={"count": "-1"})],
    )
    assert result["status"] == "error"
    assert "count" in result["error"]


def test_legitimate_zero_stays_success_without_warnings():
    result, mock_request = _run(
        {"gene": "ZZZ"},
        [
            _esearch(0, translation="ZZZ[gene]"),
            # gene-alias resolver (auxiliary): healthy empty lookup
            {
                "status": "success",
                "data": {"esearchresult": {"count": "0", "idlist": []}},
            },
        ],
    )
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 0
    assert "query_warnings" not in result["data"]


# ---------- replacement retries: broken retry is an explicit error ----------


def test_hyphen_retry_request_failure_is_explicit_error():
    result, mock_request = _run(
        {"gene": "BRCA-2"},
        [
            _esearch(0, translation="BRCA-2[gene]"),
            {"status": "error", "error": "HTTP 502"},
        ],
    )
    assert result["status"] == "error"
    assert "hyphen-stripped gene retry failed" in result["error"]
    assert "HTTP 502" in result["error"]
    assert mock_request.call_count == 2


def test_alias_retry_broken_payload_is_explicit_error():
    result, mock_request = _run(
        {"gene": "GBA"},
        [
            _esearch(0, translation="GBA[gene]"),
            # gene-db esearch: healthy, finds gene id 2629
            {
                "status": "success",
                "data": {
                    "esearchresult": {"count": "1", "idlist": ["2629"]}
                },
            },
            # gene-db esummary: resolves the rename
            {"status": "success", "data": {"result": {"2629": {"name": "GBA1"}}}},
            # ClinVar alias retry: structurally broken
            {"status": "success", "data": {}},
        ],
    )
    assert result["status"] == "error"
    assert "alias-resolved gene GBA1 retry" in result["error"]
    assert "invalid" in result["error"]
    assert mock_request.call_count == 4


def test_freetext_retry_broken_payload_is_explicit_error():
    result, mock_request = _run(
        {"gene": "RPE65", "condition": "Lebers congenital amaurosis"},
        [
            _esearch(0, translation='RPE65[gene] AND "lca"[dis]'),
            # gene-alias resolver: healthy empty lookup (no rename)
            {
                "status": "success",
                "data": {"esearchresult": {"count": "0", "idlist": []}},
            },
            # condition free-text retry: broken payload
            {"status": "success", "data": {"esearchresult": "truncated"}},
        ],
    )
    assert result["status"] == "error"
    assert "condition free-text retry" in result["error"]
    assert mock_request.call_count == 3


# ---------- auxiliary lookups: failure keeps the result, adds a warning ----------


def test_gene_alias_lookup_failure_keeps_zero_with_warning():
    result, mock_request = _run(
        {"gene": "ZZZ"},
        [
            _esearch(0, translation="ZZZ[gene]"),
            # gene-db esearch (auxiliary) fails at the request level
            {"status": "error", "error": "HTTP 500"},
        ],
    )
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 0
    warnings = result["data"]["query_warnings"]
    assert any(
        "gene-alias lookup failed" in w and "do not read total_count 0" in w
        for w in warnings
    )


def test_count_only_attribution_failure_keeps_zero_with_warning():
    result, mock_request = _run(
        {"gene": "ZZZ", "condition": "cancer"},
        [
            _esearch(0, translation='ZZZ[gene] AND "cancer"[dis]'),
            # gene-alias resolver: healthy empty lookup
            {
                "status": "success",
                "data": {"esearchresult": {"count": "0", "idlist": []}},
            },
            # condition free-text retry: valid zero (not adopted)
            _esearch(0, translation="ZZZ[gene] AND cancer"),
            # gene-only attribution check: structurally broken
            {"status": "success", "data": {}},
            # condition-only attribution check: healthy 0
            _esearch(0, translation='"cancer"[dis]'),
        ],
    )
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 0
    assert "gene_only_match_count" not in result["data"]
    assert result["data"]["condition_only_match_count"] == 0
    warnings = result["data"]["query_warnings"]
    assert len([w for w in warnings if "zero-result attribution check" in w]) == 1
    assert "do not read it as" in warnings[0]


def test_phrasesnotfound_errorlist_with_hits_flows_to_query_warnings():
    payload = _esearch(
        3,
        ids=["1", "2", "3"],
        translation="a OR b",
        esearch_extra={"errorlist": {"phrasesnotfound": ["zzz[Variant name]"]}},
    )
    result, _ = _run(
        {"gene": "NF1", "variant_name": ["a", "zzz"]},
        [payload, {"status": "success", "data": {"result": {}}}],
    )
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 3
    assert any(
        "phrasesnotfound" in w for w in result["data"].get("query_warnings", [])
    )
