"""Unit test: ClinVar_search_by_region reports how complete its scan was.

Regression: the envelope's only count, `n_candidates`, was `len(idlist)` from an
esearch pinned at `retmax=500`, so for any busy window it was the constant 500
-- a retmax masquerading as a match count. The chr11:47332696 window at the
default 2 Mb margin matched 15,327 records; 500 were inspected (3.3%) with no
flag saying so, and the `note` advised raising `margin`, which made recall
strictly worse (1 kb -> 2 variants, 100 kb -> 1, 2 Mb -> 1) because a wider
window pushed the spanning CNV out of the still-capped candidate set.

Pins:
  * `total_available` carries esearch's own `count`, whatever retmax is;
  * `n_candidates` counts records actually inspected, and `truncated` is true
    with a `truncation_note` exactly when the two differ;
  * the upstream window excludes single-base records with `NOT 1:1[VLEN]` and
    never with a positive VLEN range -- ClinVar's flagship spanning CNV
    (Variation 1703527) carries no VLEN at all and a positive range drops it;
  * the region's own window carries no length filter, so a record starting
    inside it is never excluded for being short.
"""

import re
from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import _CANDIDATE_CAP, ClinVarSearchByRegion

pytestmark = pytest.mark.unit

REGION = {"region": "chr11:47332696-47332696", "assembly": "GRCh38"}


class _Resp:
    """Follow-up 2026-10-23: healthy responses now also carry a working
    raise_for_status(), which the production scan asserts."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class _FakeEntrez:
    """Stands in for the tool's requests.Session: no network, and it honours
    retmax the way esearch does -- reporting the full `count` while returning
    only a page of ids."""

    def __init__(self, count, ids=None, overlapping=0):
        self.count = count
        # Only a page of ids is ever served, so only a page needs building.
        self.ids = (
            ids
            if ids is not None
            else [str(1000 + i) for i in range(min(count, _CANDIDATE_CAP))]
        )
        self.overlapping_ids = set(self.ids[:overlapping])
        self.terms = []

    def get(self, url, params=None, timeout=None):
        params = params or {}
        if "esearch" in url:
            self.terms.append(params["term"])
            return _Resp(
                {
                    "esearchresult": {
                        "count": str(self.count),
                        "idlist": self.ids[: params.get("retmax", 20)],
                        # Follow-up 2026-10-23: a real esearch always returns
                        # one; the scan now validates the payload.
                        "querytranslation": "17[chr] AND window[chrpos38]",
                    }
                }
            )
        result = {}
        for vid in params["id"].split(","):
            # The first `overlapping` ids straddle the locus; the rest sit clear
            # of it, so the overlap filter has something to reject.
            start, stop = (
                (47332000, 47333000)
                if vid in self.overlapping_ids
                else (46000000, 46000100)
            )
            result[vid] = {
                "title": f"variant {vid}",
                "obj_type": "copy number loss",
                "germline_classification": {"description": "Pathogenic"},
                "variation_set": [
                    {
                        "variation_loc": [
                            {
                                "assembly_name": "GRCh38",
                                "chr": "11",
                                "start": str(start),
                                "stop": str(stop),
                            }
                        ]
                    }
                ],
            }
        return _Resp({"result": result})


def _run(session, **overrides):
    tool = ClinVarSearchByRegion({"name": "ClinVar_search_by_region"})
    tool.session = session
    result = tool.run({**REGION, **overrides})
    assert result["status"] == "success", result
    return result["data"]


# --- 1. a partial scan is counted honestly and flagged --------------------


@pytest.fixture(scope="module")
def partial_scan():
    """The regression scenario: 15,327 matching records, 500 inspected."""
    return _run(_FakeEntrez(count=15327, overlapping=1))


def test_true_entrez_count_is_reported_not_the_page_size(partial_scan):
    assert partial_scan["total_available"] == 15327
    # ...and the number of inspected records is reported separately, honestly.
    assert partial_scan["n_candidates"] == _CANDIDATE_CAP


def test_truncation_is_flagged_with_the_numbers_that_justify_it(partial_scan):
    assert partial_scan["truncated"] is True
    note = partial_scan["truncation_note"]
    assert "15327" in note and str(_CANDIDATE_CAP) in note
    # The shortfall is stated as a fraction too, so a caller reading prose
    # rather than branching on the flag still learns the scan was partial.
    assert "3.3%" in note


def test_a_truncated_scan_never_advises_widening_the_window(partial_scan):
    # The pre-fix note said "Raise `margin` to catch larger spanning variants"
    # with no caveat, which reduced recall.
    advice = partial_scan["note"] + partial_scan["truncation_note"]
    assert "worse" in advice
    assert "Raise `margin` to catch larger spanning variants" not in advice


# --- 2. and the flag stays off when the scan really was complete ----------


def test_count_is_reported_even_when_nothing_was_inspected():
    data = _run(_FakeEntrez(count=0, ids=[]))

    assert data["total_available"] == 0
    assert data["n_candidates"] == 0
    assert data["variants"] == []
    assert data["truncated"] is False


def test_no_truncation_flag_when_the_whole_match_set_was_inspected():
    data = _run(_FakeEntrez(count=245, overlapping=3))

    assert data["truncated"] is False
    assert "truncation_note" not in data
    assert data["n_candidates"] == data["total_available"] == 245
    assert data["n_overlapping"] == 3


# --- 3. n_overlapping keeps max_results from hiding a partial list ---------


def test_overlap_total_is_reported_separately_from_the_capped_list():
    session = _FakeEntrez(count=50, overlapping=9)

    data = _run(session, max_results=4)

    assert data["n_overlapping"] == 9
    assert len(data["variants"]) == 4


# --- 4. the query shape that makes the candidate set small -----------------


def _term(margin=2_000_000):
    session = _FakeEntrez(count=0, ids=[])
    _run(session, margin=margin)
    return session.terms[0]


def test_upstream_window_excludes_single_base_records():
    term = _term()

    # 47332696 - 2,000,000 upstream, stopping just short of the region's own
    # window, filtered to records that occupy more than one base.
    assert "45332696:47332685[chrpos38] NOT 1:1[VLEN]" in term


def test_single_base_exclusion_is_a_negation_never_a_positive_length_range():
    """A positive `2:...[VLEN]` range would drop records with no VLEN indexed --
    among them Variation 1703527, the 1.5 Mb copy-number loss this tool's own
    documentation is built around (`1703527[VID] AND 0:1000000000[VLEN]`
    returns 0 hits). The negation keeps them."""
    term = _term()

    assert "NOT 1:1[VLEN]" in term
    assert not re.search(r"AND\s+\d+:\d+\[VLEN\]", term)


def test_region_window_itself_carries_no_length_filter():
    term = _term()

    region_clause = term.split(" OR ")[0]
    assert "47332686:47332696[chrpos38]" in region_clause
    assert "VLEN" not in region_clause


def test_widening_the_margin_only_extends_the_window_upstream():
    narrow, wide = _term(margin=1_000), _term(margin=10_000_000)

    # The region's own clause is identical either way -- widening can only add
    # upstream candidates, never displace the ones already found.
    assert narrow.split(" OR ")[0] == wide.split(" OR ")[0]
    assert "47331696:47332685[chrpos38] NOT 1:1[VLEN]" in narrow
    assert "37332696:47332685[chrpos38] NOT 1:1[VLEN]" in wide


def test_significance_filter_applies_to_the_whole_or_group():
    session = _FakeEntrez(count=0, ids=[])
    _run(session, clinical_significance="pathogenic")

    term = session.terms[0]
    # Without the grouping parentheses the AND would bind to the last OR branch
    # only, silently leaving the region's own window unfiltered.
    window, _, clinsig = term.partition(" AND (")
    assert " OR " in window and window.endswith(")")
    assert window.count("(") == window.count(")")
    assert clinsig.startswith('"clinsig pathogenic"[Filter]')


# --------------------------------------------------------------------------- #
# Follow-up 2026-10-23 (Batch A): an incomplete scan is an ERROR, never a
# healthy-looking negative. HTTP failures, API errors, malformed eSearch
# payloads, count/idlist contradictions, missing or damaged esummary
# records, unusable current-assembly coordinates and unparseable or
# inverted intervals all raise, and ClinVarSearchByRegion.run converts
# that into status:"error" -- no "success / n_overlapping=0" envelope
# may survive an incomplete request chain.
# --------------------------------------------------------------------------- #
class _HttpError(Exception):
    pass


class _Resp23:
    """Realistic response object: json() plus raise_for_status()."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def raise_for_status(self):
        if isinstance(self._payload, _HttpError):
            raise self._payload


class _ScriptedEntrez:
    """Serves a fixed esearch payload and a per-chunk esummary result."""

    def __init__(self, esearch_payload, summary_by_chunk=None):
        self.esearch_payload = esearch_payload
        self.summary_by_chunk = summary_by_chunk or []
        self._summary_calls = 0
        self.terms = []

    def get(self, url, params=None, timeout=None):
        params = params or {}
        if "esearch" in url:
            self.terms.append(params["term"])
            return _Resp23(self.esearch_payload)
        chunk_index = self._summary_calls
        self._summary_calls += 1
        return _Resp23(self.summary_by_chunk[chunk_index])


def _healthy_esearch(count, ids):
    return {
        "esearchresult": {
            "count": str(count),
            "idlist": list(ids),
            "querytranslation": "17[chr] AND window[chrpos38]",
        }
    }


def _loc_record(vid, start, stop, assembly="GRCh38"):
    return {
        vid: {
            "title": f"variant {vid}",
            "obj_type": "copy number loss",
            "germline_classification": {"description": "Pathogenic"},
            "variation_set": [
                {
                    "variation_loc": [
                        {
                            "assembly_name": assembly,
                            "chr": "11",
                            "start": str(start),
                            "stop": str(stop),
                        }
                    ]
                }
            ],
        }
    }


def _run_expect_error(session, **overrides):
    tool = ClinVarSearchByRegion({"name": "ClinVar_search_by_region"})
    tool.session = session
    result = tool.run({**REGION, **overrides})
    assert result["status"] == "error", result
    return result["error"]


@pytest.mark.parametrize(
    "esearch_payload",
    [
        pytest.param(_HttpError("HTTP 503"), id="esearch-http-error"),
        pytest.param({"error": "service unavailable"}, id="esearch-api-error"),
        pytest.param({"unexpected": True}, id="esearch-missing-envelope"),
        pytest.param(
            {
                "esearchresult": {
                    "count": "3",
                    "idlist": [],
                    "querytranslation": "17[chr]",
                }
            },
            id="positive-count-empty-idlist",
        ),
        pytest.param(
            {
                "esearchresult": {
                    "count": "1",
                    "idlist": ["1", "2"],
                    "querytranslation": "17[chr]",
                }
            },
            id="count-below-idlist-length",
        ),
        pytest.param(
            {"esearchresult": {"count": "2", "idlist": ["1"]}},
            id="missing-querytranslation",
        ),
    ],
)
def test_broken_esearch_is_whole_call_error(esearch_payload):
    error = _run_expect_error(_ScriptedEntrez(esearch_payload))
    assert "region search failed" in error.lower() or "esearch" in error.lower()


def test_healthy_zero_result_never_requests_details():
    session = _ScriptedEntrez(_healthy_esearch(0, []))
    data = _run(session)
    assert data["n_candidates"] == 0
    assert data["n_overlapping"] == 0
    assert data["truncated"] is False
    assert session._summary_calls == 0


@pytest.mark.parametrize(
    "summaries",
    [
        pytest.param([_HttpError("HTTP 503")], id="esummary-http-error"),
        pytest.param(
            [{"result": {"1": {"error": "cannot find uid"}}}],
            id="record-api-error",
        ),
        pytest.param([{"result": {}}], id="missing-uid-record"),
        pytest.param([{"result": {"1": {}}}], id="empty-record"),
        pytest.param([{"unrelated": True}], id="broken-container"),
        pytest.param(
            [
                {"result": _loc_record("1", 46000000, 46000100)},
                _HttpError("HTTP 503 on second chunk"),
            ],
            id="later-chunk-failure",
        ),
        pytest.param(
            [
                {
                    "result": {
                        "1": {
                            "title": "variant 1",
                            "variation_set": [
                                {
                                    "variation_loc": [
                                        {
                                            "assembly_name": "GRCh37",
                                            "chr": "11",
                                            "start": "46000000",
                                            "stop": "46000100",
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                }
            ],
            id="no-current-assembly-coordinates",
        ),
        pytest.param(
            [
                {
                    "result": {
                        "1": {
                            "title": "variant 1",
                            "variation_set": [
                                {
                                    "variation_loc": [
                                        {
                                            "assembly_name": "GRCh38",
                                            "chr": "11",
                                            "start": True,
                                            "stop": "46000100",
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                }
            ],
            id="boolean-start-coordinate",
        ),
        pytest.param(
            [
                {
                    "result": {
                        "1": {
                            "title": "variant 1",
                            "variation_set": [
                                {
                                    "variation_loc": [
                                        {
                                            "assembly_name": "GRCh38",
                                            "chr": "11",
                                            "start": "not-a-number",
                                            "stop": "46000100",
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                }
            ],
            id="unparseable-start-coordinate",
        ),
        pytest.param(
            [
                {
                    "result": {
                        "1": {
                            "title": "variant 1",
                            "variation_set": [
                                {
                                    "variation_loc": [
                                        {
                                            "assembly_name": "GRCh38",
                                            "chr": "11",
                                            "start": "46000100",
                                            "stop": "46000000",
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                }
            ],
            id="inverted-interval",
        ),
    ],
)
def test_broken_esummary_is_whole_call_error(summaries):
    session = _ScriptedEntrez(_healthy_esearch(2, ["1", "2"]), summaries)
    error = _run_expect_error(session)
    lowered = error.lower()
    assert "region search failed" in lowered
    # The message names the stage and (where applicable) the UID or field.
    assert any(
        marker in lowered
        for marker in ("esummary", "uid 1", "coordinates", "interval", "http")
    )


def test_other_assembly_position_does_not_require_usable_coordinates():
    # A loc clearly on another assembly is skipped WITHOUT its coordinates
    # ever being parsed; a sibling current-assembly loc decides overlap.
    record = {
        "1": {
            "title": "variant 1",
            "variation_set": [
                {
                    "variation_loc": [
                        {
                            "assembly_name": "GRCh37",
                            "chr": "11",
                            "start": "not-even-a-number",
                            "stop": "???",
                        },
                        {
                            "assembly_name": "GRCh38",
                            "chr": "11",
                            "start": "47332000",
                            "stop": "47333000",
                        },
                    ]
                }
            ],
        }
    }
    session = _ScriptedEntrez(
        _healthy_esearch(1, ["1"]), [{"result": record}]
    )
    data = _run(session)
    assert data["n_overlapping"] == 1
    assert data["variants"][0]["variation_id"] == "1"


def test_candidate_cap_truncation_disclosure_unchanged():
    # Healthy oversized match set: the existing truncation contract stays.
    ids = [str(1000 + i) for i in range(_CANDIDATE_CAP)]
    all_records = {
        vid: _loc_record(vid, 46000000, 46000100)[vid] for vid in ids
    }
    session = _ScriptedEntrez(
        _healthy_esearch(15327, ids),
        # The scan fetches details in 200-id chunks; serve every chunk.
        [{"result": all_records}] * 5,
    )
    data = _run(session)
    assert data["truncated"] is True
    assert data["n_candidates"] == _CANDIDATE_CAP
    assert data["total_available"] == 15327


# --------------------------------------------------------------------------- #
# The same whole-call error must survive a REAL SMCP registration (the
# HTTP-layer contract reaches the MCP caller). All HTTP is mocked.
# --------------------------------------------------------------------------- #
class _FakeSession:
    """Minimal requests.Session stand-in: only .get is used by the scan."""

    def __init__(self, get_impl):
        self._get = get_impl

    def get(self, url, params=None, timeout=None):
        return self._get(url, params=params, timeout=timeout)


def test_smcp_registered_region_error_reaches_caller():
    import asyncio
    import json as _json

    from fastmcp import Client

    from tooluniverse.clinvar_tool import clinvar_variants_overlapping
    from tooluniverse.smcp import SMCP

    def fake_get(url, params=None, timeout=None):
        if "esearch" in url:
            return _Resp23(_healthy_esearch(1, ["13961"]))
        return _Resp23(
            {"result": {"13961": {"error": "service unavailable"}}}
        )

    async def drive():
        from tooluniverse.clinvar_tool import ClinVarRESTTool

        server = SMCP(name="region-error-test")
        # The region tool builds its own requests.Session in __init__; swap
        # the constructor so every instance the SMCP dispatch creates gets
        # the fake (HTTP fully mocked, the REAL handler logic runs).
        original_init = ClinVarRESTTool.__init__

        def patched_init(self, tool_config):
            original_init(self, tool_config)
            self.session = _FakeSession(fake_get)

        with patch.object(ClinVarRESTTool, "__init__", patched_init):
            async with Client(server) as client:
                call = await client.call_tool(
                    "ClinVar_search_by_region",
                    {"region": "chr11:47332696-47332696", "assembly": "GRCh38"},
                )
        return _json.loads(call.content[0].text)

    payload = asyncio.run(drive())
    assert payload["status"] == "error"
    lowered = payload["error"].lower()
    assert "region search failed" in lowered
    assert "13961" in lowered or "service unavailable" in lowered
