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
            _gene_esearch([], count="0"),
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
                    "esearchresult": {"count": "1", "idlist": ["2629"], "querytranslation": "GBA[sym] AND human[orgn]"}
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
            _gene_esearch([], count="0"),
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
            _gene_esearch([], count="0"),
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


# ---------- Fix-A-20260922: gene-alias lookup payload validation ----------


def _gene_esearch(
    ids, count=None, translation="GBA[sym] AND human[orgn]", esearch_extra=None
):
    """A gene-db esearch payload with overridable structure fields."""
    esearch = {
        "idlist": ids,
        "querytranslation": translation,
    }
    if count is None:
        esearch["count"] = str(len(ids))
    else:
        esearch["count"] = count
    if esearch_extra:
        esearch.update(esearch_extra)
    return {"status": "success", "data": {"esearchresult": esearch}}


def _gene_summary(name):
    return {"status": "success", "data": {"result": {"2629": {"name": name}}}}


@pytest.mark.parametrize(
    "gene_esearch_payload",
    [
        # API error carried in the payload
        {"status": "success", "data": {"error": "Invalid db name"}},
        # esearchresult present but translation blank
        _gene_esearch([], count="0", translation="   "),
        # illegal count
        _gene_esearch(["2629"], count="-1"),
        # non-UID idlist entry (int, not a digit string)
        _gene_esearch([2629]),
    ],
)
def test_broken_gene_alias_esearch_warns_not_silent(gene_esearch_payload):
    """A structurally broken gene-db eSearch response must surface as an
    alias-lookup warning, never as a healthy 'no alias found'."""
    result, mock_request = _run(
        {"gene": "GBA"},
        [
            _esearch(0, translation="GBA[gene]"),
            gene_esearch_payload,
        ],
    )
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 0
    warnings = result["data"]["query_warnings"]
    assert any(
        "gene-alias lookup failed" in w and "do not read total_count 0" in w
        for w in warnings
    ), f"expected alias warning, got {warnings}"


def test_gene_alias_esearch_query_warnings_kept_with_source():
    """Non-fatal reminders from the gene-db eSearch (errorlist/warninglist)
    are retained, labelled with the alias-lookup provenance."""
    payload = _gene_esearch(
        [], count="0", esearch_extra=None
    )
    payload["data"]["esearchresult"]["errorlist"] = {
        "phrasesnotfound": ["GBA[sym]"]
    }
    result, _ = _run(
        {"gene": "GBA"},
        [_esearch(0, translation="GBA[gene]"), payload],
    )
    assert result["status"] == "success"
    warnings = result["data"]["query_warnings"]
    assert any("gene-alias" in w and "phrasesnotfound" in w for w in warnings)


@pytest.mark.parametrize("bad_name", ["", "   ", 123, 4.5])
def test_gene_summary_bad_name_warns_not_silent(bad_name):
    """A hit record whose name is missing/blank/wrong-typed must warn, not
    silently report 'no alias' -- and a numeric name must never reach the
    caller's .upper()."""
    result, mock_request = _run(
        {"gene": "GBA"},
        [
            _esearch(0, translation="GBA[gene]"),
            _gene_esearch(["2629"]),
            _gene_summary(bad_name),
        ],
    )
    assert result["status"] == "success"
    warnings = result["data"]["query_warnings"]
    assert any("gene-alias lookup failed" in w for w in warnings), (
        f"expected alias warning for name={bad_name!r}, got {warnings}"
    )


def test_gene_summary_corrupted_entry_warns_not_silent():
    result, _ = _run(
        {"gene": "GBA"},
        [
            _esearch(0, translation="GBA[gene]"),
            _gene_esearch(["2629"]),
            {"status": "success", "data": {"result": "corrupted"}},
        ],
    )
    assert result["status"] == "success"
    assert any(
        "gene-alias lookup failed" in w for w in result["data"]["query_warnings"]
    )


def test_gene_alias_healthy_zero_still_no_warning():
    result, mock_request = _run(
        {"gene": "GBA"},
        [
            _esearch(0, translation="GBA[gene]"),
            _gene_esearch([], count="0"),
        ],
    )
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 0
    assert "query_warnings" not in result["data"]


def test_gene_alias_valid_rename_still_triggers_replacement():
    payloads = [
        _esearch(0, translation="GBA[gene]"),
        _gene_esearch(["2629"]),
        _gene_summary("GBA1"),
        _esearch(786, translation="GBA1[gene]"),
    ]
    result, mock_request = _run({"gene": "GBA"}, payloads)
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 786
    assert mock_request.call_args_list[3][0][1]["term"] == "GBA1[gene]"


def test_gene_alias_replacement_broken_is_explicit_error():
    payloads = [
        _esearch(0, translation="GBA[gene]"),
        _gene_esearch(["2629"]),
        _gene_summary("GBA1"),
        {"status": "success", "data": {}},  # broken replacement
    ]
    result, _ = _run({"gene": "GBA"}, payloads)
    assert result["status"] == "error"
    assert "alias-resolved gene GBA1 retry" in result["error"]


# ---------- Fix-B-20260922: failed condition attribution stays inconclusive ----------


def _condition_variant_name_payloads(condition_check_payload):
    """Main query zero + free-text retry zero + a (bad) condition-only
    count check -- the `condition + variant_name` input shape."""
    return [
        _esearch(0, translation='"Lebers congenital amaurosis"[dis] AND "x"[Variant name]'),
        _esearch(0, translation="Lebers congenital amaurosis AND x"),
        condition_check_payload,
    ]


@pytest.mark.parametrize(
    "condition_check_payload",
    [
        # structural damage: querytranslation null
        {"status": "success", "data": {"esearchresult": {"count": "0", "idlist": [], "querytranslation": None}}},
        # request-level failure
        {"status": "error", "error": "HTTP 503"},
    ],
)
def test_failed_condition_check_not_declared_valid(condition_check_payload):
    """When the condition-only count query fails, the hint must NOT claim
    the condition is a recognized disease term, must not print 'None
    record(s)', and must not definitively attribute the zero to the other
    filter (variant_name)."""
    result, _ = _run(
        {"condition": "Lebers congenital amaurosis", "variant_name": "x"},
        _condition_variant_name_payloads(condition_check_payload),
    )
    assert result["status"] == "success"
    assert result["data"]["total_count"] == 0
    hint = result["data"].get("zero_result_hint", "")
    assert "None record(s)" not in hint, hint
    assert "recognized ClinVar disease term" not in hint, hint
    assert "comes from the other filter" not in hint, hint
    assert "condition_only_match_count" not in result["data"]
    assert any(
        "zero-result attribution check" in w for w in result["data"]["query_warnings"]
    )
    assert "unknown" in hint or "could not" in hint or "failed" in hint, hint


def test_failed_condition_check_with_gene_keeps_gene_evidence():
    """With gene+condition+variant_name and only the CONDITION check
    failing: the already-established gene-only count stays, the gene is
    not blamed, and the condition stays inconclusive."""
    payloads = [
        _esearch(0, translation='TP53[gene] AND "lcaxx"[dis] AND "x"[Variant name]'),
        # gene-alias resolver: healthy empty lookup
        _gene_esearch([], count="0"),
        # free-text retry: valid zero (not adopted)
        _esearch(0, translation="TP53[gene] AND lcaxx AND x"),
        # gene-only count check: succeeds
        _esearch(434, translation="TP53[gene]"),
        # condition-only count check: structurally broken
        {"status": "success", "data": {"esearchresult": {"count": "0", "idlist": [], "querytranslation": None}}},
    ]
    result, _ = _run(
        {"gene": "TP53", "condition": "lcaxx", "variant_name": "x"}, payloads
    )
    assert result["status"] == "success"
    data = result["data"]
    assert data["gene_only_match_count"] == 434
    assert "condition_only_match_count" not in data
    hint = data.get("zero_result_hint", "")
    assert "None record(s)" not in hint
    assert "recognized ClinVar disease term" not in hint
    assert "unknown" in hint or "could not" in hint or "failed" in hint, hint
