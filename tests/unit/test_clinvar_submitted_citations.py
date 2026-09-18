"""Regression guard for Fix-E-20260918: submitter citations in VCV records.

Confirmed from the live VCV XML for VCV002737810 (SCV004299284, Labcorp
Genetics): ``ClinicalAssertion/Classification/Citation`` carries PMID
31573083 and ``ClinicalAssertion/AttributeSet/Citation`` carries PMID
28492532 -- two distinct citation locations the submitted-records parser
used to discard entirely.

Contract pinned here:
- every submission gains ``citations`` entries with ``pmid``, ``title``
  and ``source_path``; duplicate (pmid, source_path) pairs inside one
  submission collapse, but the SAME PMID under different source paths
  survives (classification vs methodology provenance), as does the same
  PMID across different submitters;
- titles are backfilled with ONE batch PubMed esummary request; on
  failure the PMID survives with title=None plus a warning;
- ``citations_complete`` is True for a clean fetch and for a confirmed
  no-citation record (empty list), False when backfill or parsing fails;
- citation problems never discard the successfully retrieved variant
  details.

All network access is mocked; no test reaches NCBI.
"""

import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest
import requests as _requests

from tooluniverse.clinvar_submitted_tool import (
    ClinVarSubmittedRecordsTool,
    _citations_from_assertion,
)

pytestmark = pytest.mark.unit


def _vcv_xml(citation_blocks: dict):
    """Build a minimal VCV XML; citation_blocks maps SCV -> list of
    (source_path, pmid) tuples."""
    assertions = []
    for scv, cites in citation_blocks.items():
        cite_xml = ""
        for source_path, pmid in cites:
            if source_path == "Classification/Citation":
                cite_xml += (
                    f"<Classification><Citation>"
                    f'<ID Source="PubMed">{pmid}</ID>'
                    f"</Citation></Classification>"
                )
            else:
                cite_xml += (
                    f"<AttributeSet><Citation>"
                    f'<ID Source="PubMed">{pmid}</ID>'
                    f"</Citation></AttributeSet>"
                )
        assertions.append(
            f"<ClinicalAssertion>"
            f'<ClinVarAccession Accession="{scv}" Version="1" '
            f'SubmitterName="Lab {scv}"/>'
            f"<Classification><GermlineClassification>Pathogenic"
            f"</GermlineClassification></Classification>"
            f"{cite_xml}"
            f"</ClinicalAssertion>"
        )
    return (
        "<ClinVarVariationArchive>"
        '<VariationArchive VariationName="NM_1:c.1A>G" VariationID="2737810" '
        'Accession="VCV002737810" NumberOfSubmissions="{}">'
        "<ClassifiedRecord>"
        "<Classifications><GermlineClassification>"
        "<Description>Pathogenic</Description>"
        "</GermlineClassification></Classifications>"
        "<ClinicalAssertionList>{}</ClinicalAssertionList>"
        "</ClassifiedRecord>"
        "</VariationArchive>"
        "</ClinVarVariationVariationArchive>"
    ).format(len(citation_blocks), "".join(assertions)).replace(
        "ClinVarVariationVariationArchive", "ClinVarVariationArchive"
    )


def _run_with(xml: str, titles_payload=None, titles_error=None):
    """Run the tool with efetch (XML) and esummary (titles) both mocked."""
    tool = ClinVarSubmittedRecordsTool({"name": "ClinVar_get_submitted_records"})

    class _Resp:
        def __init__(self, payload):
            self.payload = payload

        @property
        def status_code(self):
            return 200

        @property
        def content(self):
            return self.payload.encode()

        def json(self):
            return self.payload

    def fake_get(url, params=None, timeout=None, headers=None):
        if "efetch" in url:
            return _Resp(xml)
        assert "esummary" in url and params.get("db") == "pubmed"
        if titles_error is not None:
            raise titles_error
        return _Resp(titles_payload)

    with patch(
        "tooluniverse.clinvar_submitted_tool.requests.get", side_effect=fake_get
    ):
        return tool.run({"variant_id": "VCV002737810"})


def _titles(pmid_to_title):
    return {"result": {pmid: {"title": title} for pmid, title in pmid_to_title.items()}}


def test_both_citation_locations_captured_with_source_path():
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "31573083"),
                              ("AttributeSet/Citation", "28492532")]})
    result = _run_with(xml, titles_payload=_titles({}))
    assert result["status"] == "success"
    subs = result["data"]["submissions"]
    assert len(subs) == 1
    cits = subs[0]["citations"]
    assert {c["pmid"]: c["source_path"] for c in cits} == {
        "31573083": "Classification/Citation",
        "28492532": "AttributeSet/Citation",
    }


def test_titles_backfilled_and_complete():
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "31573083")]})
    result = _run_with(
        xml,
        titles_payload=_titles({"31573083": "A functional study of NF1"}),
    )
    assert result["status"] == "success"
    cit = result["data"]["submissions"][0]["citations"][0]
    assert cit["title"] == "A functional study of NF1"
    assert result["data"]["citations_complete"] is True
    assert "citation_warnings" not in result["data"]


def test_title_backfill_failure_keeps_pmid_null_title_warning():
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "31573083")]})
    result = _run_with(
        xml,
        titles_payload=_titles({}),
        titles_error=_requests.exceptions.ConnectionError("boom"),
    )
    assert result["status"] == "success"  # variant details survive
    cit = result["data"]["submissions"][0]["citations"][0]
    assert cit["pmid"] == "31573083"
    assert cit["title"] is None
    assert result["data"]["citations_complete"] is False
    assert any("backfill" in w for w in result["data"]["citation_warnings"])


def test_missing_pmid_in_esummary_response_is_incomplete():
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "31573083"),
                              ("AttributeSet/Citation", "99999999")]})
    result = _run_with(
        xml,
        titles_payload=_titles({"31573083": "Known title"}),  # 99999999 absent
    )
    assert result["status"] == "success"
    by_pmid = {c["pmid"]: c for c in result["data"]["submissions"][0]["citations"]}
    assert by_pmid["31573083"]["title"] == "Known title"
    assert by_pmid["99999999"]["title"] is None
    assert result["data"]["citations_complete"] is False
    assert any("99999999" in w for w in result["data"]["citation_warnings"])


def test_duplicate_pmid_same_path_collapses_same_pmid_two_paths_survives():
    xml = _vcv_xml(
        {
            "SCV1": [
                ("Classification/Citation", "123"),
                ("Classification/Citation", "123"),  # exact duplicate
                ("AttributeSet/Citation", "123"),  # same PMID, other path
            ]
        }
    )
    result = _run_with(xml, titles_payload=_titles({}))
    cits = result["data"]["submissions"][0]["citations"]
    assert len(cits) == 2
    assert {c["source_path"] for c in cits} == {
        "Classification/Citation",
        "AttributeSet/Citation",
    }


def test_same_pmid_across_submitters_preserved():
    xml = _vcv_xml(
        {
            "SCV1": [("Classification/Citation", "42")],
            "SCV2": [("Classification/Citation", "42")],
        }
    )
    result = _run_with(xml, titles_payload=_titles({"42": "Shared"}))
    subs = result["data"]["submissions"]
    assert [s["citations"][0]["pmid"] for s in subs] == ["42", "42"]
    assert all(s["citations"][0]["title"] == "Shared" for s in subs)


def test_no_citations_empty_list_and_complete_true():
    xml = _vcv_xml({"SCV1": []})
    result = _run_with(xml)
    assert result["status"] == "success"
    assert result["data"]["submissions"][0]["citations"] == []
    assert result["data"]["citations_complete"] is True


def test_non_pubmed_citation_source_warned_not_exposed():
    xml = (
        "<ClinVarVariationArchive>"
        '<VariationArchive Accession="VCV002737810" VariationID="1">'
        "<ClassifiedRecord><ClinicalAssertionList><ClinicalAssertion>"
        '<ClinVarAccession Acc="SCV1" Version="1" SubmitterName="X"/>'
        "<Classification><Citation>"
        '<ID Source="DOI">10.1000/x</ID>'
        "</Citation></Classification>"
        "</ClinicalAssertion></ClinicalAssertionList>"
        "</ClassifiedRecord></VariationArchive></ClinVarVariationArchive>"
    )
    result = _run_with(xml)
    assert result["status"] == "success"
    subs = result["data"]["submissions"]
    assert subs[0]["citations"] == []
    assert any("not PubMed" in w for w in result["data"].get("citation_warnings", []))
    # Fix-R2-20260922: the parse warning must NOT be overridden by the
    # empty-PMID shortcut -- enrichment is not complete here.
    assert result["data"]["citations_complete"] is False


# ---------- Fix-R2-20260922: enrichment failure never discards data ----------


@pytest.mark.parametrize("bad_payload", [[], None, "ok", 123])
def test_non_object_esummary_payload_warns_and_keeps_records(bad_payload):
    """Top-level [], null or a scalar must yield a completion warning, not
    an escaping AttributeError -- the variant record, SCV, PMID and source
    path all survive."""
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "31573083")]})
    result = _run_with(xml, titles_payload=bad_payload)
    assert result["status"] == "success"
    sub = result["data"]["submissions"][0]
    assert sub["scv_accession"] == "SCV1.1"
    assert sub["citations"][0]["pmid"] == "31573083"
    assert sub["citations"][0]["source_path"] == "Classification/Citation"
    assert sub["citations"][0]["title"] is None
    assert result["data"]["citations_complete"] is False
    warnings = result["data"]["citation_warnings"]
    assert any("was not a JSON object" in w for w in warnings)
    assert any("31573083" in w for w in warnings)


def test_corrupted_result_object_warns_and_keeps_records():
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "31573083")]})
    result = _run_with(xml, titles_payload={"result": "corrupted"})
    assert result["status"] == "success"
    assert result["data"]["submissions"][0]["citations"][0]["pmid"] == "31573083"
    assert result["data"]["citations_complete"] is False
    assert any("missing 'result' object" in w for w in result["data"]["citation_warnings"])


@pytest.mark.parametrize("bad_title", ["", "   ", 12.5, None, ["t"]])
def test_blank_or_non_string_title_stays_null_with_pmid_disclosed(bad_title):
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "31573083")]})
    result = _run_with(xml, titles_payload=_titles({"31573083": bad_title}))
    assert result["status"] == "success"
    citation = result["data"]["submissions"][0]["citations"][0]
    assert citation["pmid"] == "31573083"
    assert citation["title"] is None
    assert result["data"]["citations_complete"] is False
    assert any(
        "No PubMed title retrieved for PMID(s): 31573083" in w
        for w in result["data"]["citation_warnings"]
    )


def test_partial_title_success_keeps_the_successful_half():
    xml = _vcv_xml(
        {
            "SCV1": [
                ("Classification/Citation", "111"),
                ("AttributeSet/Citation", "222"),
            ]
        }
    )
    result = _run_with(xml, titles_payload=_titles({"111": "Good title", "222": ""}))
    assert result["status"] == "success"
    citations = result["data"]["submissions"][0]["citations"]
    by_pmid = {c["pmid"]: c for c in citations}
    assert by_pmid["111"]["title"] == "Good title"
    assert by_pmid["222"]["title"] is None
    assert result["data"]["citations_complete"] is False
    assert any("222" in w for w in result["data"]["citation_warnings"])


def test_request_failure_already_warns_without_raising():
    """Pre-existing Fix-E behavior, re-pinned under Fix-R2: a transport
    failure yields warnings + incomplete citations, never an exception."""
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "31573083")]})
    result = _run_with(
        xml, titles_error=_requests.exceptions.ConnectionError("boom")
    )
    assert result["status"] == "success"
    assert result["data"]["submissions"][0]["citations"][0]["pmid"] == "31573083"
    assert result["data"]["citations_complete"] is False
    assert any("request failed" in w for w in result["data"]["citation_warnings"])


def test_existing_submission_fields_unchanged():
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "1")]})
    result = _run_with(xml, titles_payload=_titles({"1": "T"}))
    sub = result["data"]["submissions"][0]
    for key in (
        "scv_accession",
        "classification",
        "classification_type",
        "review_status",
        "submitter",
        "condition",
        "last_evaluated",
    ):
        assert key in sub


def test_helper_direct_on_real_shape():
    assertion = ET.fromstring(
        "<ClinicalAssertion>"
        '<ClinVarAccession Acc="SCV004299284" Version="1"/>'
        "<Classification><Citation>"
        '<ID Source="PubMed">31573083</ID>'
        "</Citation></Classification>"
        "<AttributeSet><Citation>"
        '<ID Source="PubMed">28492532</ID>'
        "</Citation></AttributeSet>"
        "</ClinicalAssertion>"
    )
    warnings = []
    cits = _citations_from_assertion(assertion, warnings)
    assert [(c["pmid"], c["source_path"]) for c in cits] == [
        ("31573083", "Classification/Citation"),
        ("28492532", "AttributeSet/Citation"),
    ]
    assert warnings == []
