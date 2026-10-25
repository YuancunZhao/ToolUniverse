"""Regression guards for review fixes F04/F05/F06 (2026-10-13 report).

F04: candidate rsID/HGVS names inside ``variant_name`` used to be appended
as SEPARATE ``AND`` terms instead of one OR candidate group, so two rsIDs
returned the intersection (a needless false empty) and rsID+HGVS searched
``rsID AND names`` instead of any-of.

F05: the gene alias/hyphen retries rebuilt the query as
``[new gene term] + query_parts[1:]`` -- assuming the gene term is always
part index 0 -- but ``raw_term`` (an Entrez expression passed via
``query``) is appended FIRST. With both present the retry dropped the
caller's expression and kept the OLD gene term:
``{"gene":"GBA","query":"1[chr]"}`` retried as
``GBA1[gene] AND GBA[gene]`` instead of ``1[chr] AND GBA1[gene]``.

F06: after a successful eSearch, a failing/partially-broken esummary fetch
was silently swallowed -- counts and IDs came back with ``variants: []``
and no field said the details were missing.

Contract pinned here (plan section 1):
- ``details_complete`` is true iff every returned ``variant_ids`` entry has
  parseable details; a healthy empty query is complete.
- ``missing_variant_ids`` keeps the returned-ID order, deduplicated.
- detail-failure reasons go to ``warnings`` (never ``query_warnings``).
- completeness is measured against the returned IDs only -- a total_count
  larger than the page does NOT make the response incomplete.
- eSearch itself failing still returns an error (covered elsewhere).

All network access is mocked; no test reaches NCBI.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _esearch_result(count, ids=None, query_translation="qt[All Fields]"):
    return {
        "status": "success",
        "data": {
            "esearchresult": {
                "idlist": ids or [],
                "count": str(count),
                "querytranslation": query_translation,
            }
        },
    }


def _gene_db_result(uids):
    # Fix-A-20260922 shape: a real gene-db eSearch response carries count
    # and a querytranslation alongside the idlist; the alias resolver
    # validates the payload, so a fixture without them would read as broken.
    return {
        "status": "success",
        "data": {
            "esearchresult": {
                "idlist": uids,
                "count": str(len(uids)),
                "querytranslation": "sym[All Fields] AND human[orgn]",
            }
        },
    }


def _gene_summary_result(uid, name):
    return {
        "status": "success",
        "data": {"result": {uid: {"name": name}}},
    }


def _esummary_result(records):
    return {"status": "success", "data": {"result": records}}


def _variant_record(uid, name="NM_1:c.1A>G"):
    """Follow-up 2026-10-14: shaped like a REAL esummary record. The old
    fixture used ``name``/``clinical_significance`` keys the parser never
    reads, so "healthy" records parsed to all-blank fields."""
    return {
        "uid": uid,
        "title": name,
        "genes": [{"symbol": "NF1"}],
        "germline_classification": {
            "description": "Pathogenic",
            "review_status": "criteria provided, single submitter",
        },
    }


def _terms_of(mock_request):
    return [
        c[0][1]["term"]
        for c in mock_request.call_args_list
        if "term" in c[0][1]
    ]


# --------------------------------------------------------------------------- #
# F04: variant_name candidates form ONE OR group
# --------------------------------------------------------------------------- #
def test_two_rsid_candidates_join_in_one_or_group():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value=_esearch_result(0),
    ) as mock_request:
        tool.run({"variant_name": ["rs4244285", "rs4986893"]})

    term = _terms_of(mock_request)[0]
    assert term == "(rs4244285 OR rs4986893)"


def test_single_rsid_candidate_stays_bare_term():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value=_esearch_result(0),
    ) as mock_request:
        tool.run({"variant_name": "rs4244285"})

    term = _terms_of(mock_request)[0]
    assert term == "rs4244285"


def test_rsid_and_hgvs_candidates_share_one_or_group():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value=_esearch_result(0),
    ) as mock_request:
        tool.run({"variant_name": ["rs4244285", "c.681G>A"]})

    term = _terms_of(mock_request)[0]
    # All candidates -- bare rsID and both HGVS spellings -- in ONE OR
    # clause, joined to other filters with AND, never intersected.
    assert term == (
        '(rs4244285 OR "c.681G>A"[Variant name] '
        'OR "681G>A"[Variant name])'
    )


def test_candidate_or_group_ands_with_gene_filter():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value=_esearch_result(0),
    ) as mock_request:
        tool.run({"gene": "CYP2C19", "variant_name": ["rs4244285", "rs4986893"]})

    term = _terms_of(mock_request)[0]
    assert term == "CYP2C19[gene] AND (rs4244285 OR rs4986893)"


def test_two_plain_name_candidates_keep_variant_name_or_group():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value=_esearch_result(0),
    ) as mock_request:
        tool.run({"variant_name": ["Glu6Val", "V600E"]})

    term = _terms_of(mock_request)[0]
    assert term == (
        '("Glu6Val"[Variant name] OR "V600E"[Variant name])'
    )


# --------------------------------------------------------------------------- #
# F05: gene retries replace the gene element, never the raw_term
# --------------------------------------------------------------------------- #
def test_alias_retry_with_raw_term_keeps_caller_expression():
    """{"gene":"GBA","query":"1[chr]"} -- the query is an Entrez expression
    (has field tags) so it rides as raw_term BEFORE the gene term. The
    alias-resolved retry must become ``1[chr] AND GBA1[gene]``, not
    ``GBA1[gene] AND GBA[gene]``."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(0),  # 1[chr] AND GBA[gene]
            _gene_db_result(["2629"]),
            _gene_summary_result("2629", "GBA1"),
            _esearch_result(12),  # retry
        ],
    ) as mock_request:
        result = tool.run({"gene": "GBA", "query": "1[chr]"})

    terms = _terms_of(mock_request)
    assert terms[0] == "1[chr] AND GBA[gene]"
    # The gene-database lookup (GBA[sym] AND human[orgn]) rides the same
    # mocked _make_request between the two variant searches; the retry is
    # the LAST term.
    assert terms[-1] == "1[chr] AND GBA1[gene]"
    assert result["data"]["total_count"] == 12


def test_hyphen_retry_with_raw_term_keeps_caller_expression():
    """{"gene":"BRCA-2","query":"13[chr]"} -- the hyphen-stripped retry must
    keep the chromosome condition and replace only the gene element."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(0),  # 13[chr] AND BRCA-2[gene]
            _esearch_result(21879),  # retry
        ],
    ) as mock_request:
        result = tool.run({"gene": "BRCA-2", "query": "13[chr]"})

    terms = _terms_of(mock_request)
    assert terms[0] == "13[chr] AND BRCA-2[gene]"
    assert terms[1] == "13[chr] AND BRCA2[gene]"
    assert result["data"]["total_count"] == 21879


def test_gene_retry_with_condition_keeps_condition_filter():
    """The condition path already records its index; the gene-retry fix must
    not disturb it (gene + condition, no raw_term)."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(0),
            _esearch_result(203),
        ],
    ) as mock_request:
        tool.run({"gene": "BRCA-2", "condition": "breast cancer"})

    terms = _terms_of(mock_request)
    assert terms[1] == 'BRCA2[gene] AND "breast cancer"[dis]'


def test_alias_retry_gene_only_unchanged_behavior():
    """gene-only retry (the original Fix-R62A-1 case) must keep working."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(0),
            _gene_db_result(["2629"]),
            _gene_summary_result("2629", "GBA1"),
            _esearch_result(786),
        ],
    ) as mock_request:
        result = tool.run({"gene": "GBA"})

    terms = _terms_of(mock_request)
    assert terms[0] == "GBA[gene]"
    assert terms[-1] == "GBA1[gene]"
    assert result["data"]["total_count"] == 786


# --------------------------------------------------------------------------- #
# F06: details completeness disclosure
# --------------------------------------------------------------------------- #
def _hit(ids):
    """One successful eSearch round with the given id list; the caller
    supplies the esummary response as the next side_effect entry."""
    return _esearch_result(len(ids), ids=ids)


def test_whole_esummary_failure_keeps_counts_and_discloses():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _hit(["2737810"]),
            {"status": "error", "error": "HTTP 503"},
        ],
    ):
        result = tool.run({"gene": "NF1"})

    assert result["status"] == "success"
    data = result["data"]
    assert data["total_count"] == 1
    assert data["variant_ids"] == ["2737810"]
    assert data["variants"] == []
    assert data["details_complete"] is False
    assert data["missing_variant_ids"] == ["2737810"]
    assert any(
        "esummary" in w.lower() or "details" in w.lower()
        for w in data["warnings"]
    ), data.get("warnings")


def test_broken_esummary_container_discloses_all_ids():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _hit(["1", "2"]),
            {"status": "success", "data": {"unrelated": True}},
        ],
    ):
        result = tool.run({"gene": "NF1"})

    data = result["data"]
    assert data["details_complete"] is False
    assert data["missing_variant_ids"] == ["1", "2"]
    assert data["warnings"]


def test_missing_uid_named_others_kept():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _hit(["1", "2", "3"]),
            _esummary_result({"1": _variant_record("1"), "3": _variant_record("3")}),
        ],
    ):
        result = tool.run({"gene": "NF1"})

    data = result["data"]
    assert [v["variant_id"] for v in data["variants"]] == ["1", "3"]
    assert data["details_complete"] is False
    assert data["missing_variant_ids"] == ["2"]
    assert any("2" in w for w in data["warnings"])
    # Follow-up 2026-10-14: the kept healthy records carry real content.
    for kept in data["variants"]:
        assert kept["title"] == "NM_1:c.1A>G"
        assert kept["genes"] == ["NF1"]
        assert kept["clinical_significance"] == "Pathogenic"


def test_inline_record_error_named_uid_disclosed():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _hit(["1", "2"]),
            _esummary_result(
                {
                    "1": _variant_record("1"),
                    "2": {"uid": "2", "error": "cannot find uid"},
                }
            ),
        ],
    ):
        result = tool.run({"gene": "NF1"})

    data = result["data"]
    assert [v["variant_id"] for v in data["variants"]] == ["1"]
    assert data["details_complete"] is False
    assert data["missing_variant_ids"] == ["2"]
    assert any(
        "cannot find uid" in w for w in data["warnings"]
    ), data["warnings"]


def test_healthy_hit_is_complete():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _hit(["1", "2"]),
            _esummary_result(
                {"1": _variant_record("1"), "2": _variant_record("2")}
            ),
        ],
    ):
        result = tool.run({"gene": "NF1"})

    data = result["data"]
    assert data["details_complete"] is True
    assert data["missing_variant_ids"] == []
    assert "warnings" not in data or data["warnings"] == []
    # Follow-up 2026-10-14: healthy details must carry real CONTENT, not
    # just IDs and a completeness flag.
    assert [v["variant_id"] for v in data["variants"]] == ["1", "2"]
    for kept in data["variants"]:
        assert kept["title"] == "NM_1:c.1A>G"
        assert kept["genes"] == ["NF1"]
        assert kept["clinical_significance"] == "Pathogenic"
        assert kept["review_status"] == "criteria provided, single submitter"


def test_healthy_empty_query_is_complete():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value=_esearch_result(0, ids=[]),
    ):
        result = tool.run({"gene": "NF1"})

    data = result["data"]
    assert data["total_count"] == 0
    assert data["variant_ids"] == []
    assert data["details_complete"] is True
    assert data["missing_variant_ids"] == []


def test_pagination_overrun_does_not_flag_incomplete():
    """total_count 500 but only the 20 returned IDs matter for details
    completeness -- the unreturned remainder is pagination, not missing
    details."""
    tool = _tool()
    returned = [str(i) for i in range(1, 21)]
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _esearch_result(500, ids=returned),
            _esummary_result(
                {uid: _variant_record(uid) for uid in returned}
            ),
        ],
    ):
        result = tool.run({"gene": "NF1"})

    data = result["data"]
    assert data["total_count"] == 500
    assert data["details_complete"] is True
    assert data["missing_variant_ids"] == []


def test_detail_warnings_do_not_leak_into_query_warnings():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            _hit(["1"]),
            {"status": "error", "error": "HTTP 503"},
        ],
    ):
        result = tool.run({"gene": "NF1"})

    data = result["data"]
    assert data["warnings"]
    assert not data.get("query_warnings")


# --------------------------------------------------------------------------- #
# 2026-10-23 review (Batch D): raw_term -- the internal name `query` is
# rewritten to when it carries Entrez field tags -- actually JOINS the
# query, yet it was missing from the recognized-parameter set, so a
# caller using {"query": "17[chr]"} got ``ignored_parameters:
# ["raw_term"]`` accusing the one input that WAS applied. Truly unknown
# parameters (typos) must stay disclosed.
# --------------------------------------------------------------------------- #
def test_query_expression_is_applied_and_not_reported_ignored():
    """{"query": "17[chr]"} -- the expression rides as raw_term into the
    actual term and must NOT appear in ignored_parameters."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[_esearch_result(7)],
    ) as mock_request:
        result = tool.run({"query": "17[chr]"})

    terms = _terms_of(mock_request)
    assert terms == ["17[chr]"]
    assert result["status"] == "success", result
    assert result["data"]["total_count"] == 7
    assert "ignored_parameters" not in result["data"]


def test_unknown_parameter_still_disclosed_alongside_raw_term():
    """A real typo next to a raw_term expression stays disclosed -- fixing
    the internal-name leak must not silently accept misspelled params."""
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[_esearch_result(7)],
    ):
        result = tool.run({"query": "17[chr]", "genee": "BRCA2"})

    assert result["status"] == "success", result
    assert result["data"]["ignored_parameters"] == ["genee"]
