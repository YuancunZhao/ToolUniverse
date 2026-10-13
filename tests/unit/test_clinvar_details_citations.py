"""Fix-R3-20260922: submitter citations in ClinVar_get_variant_details.

The details tool reuses ClinVarSubmittedRecordsTool's efetch+parse+PubMed
path once and flattens the per-submission citations into
``data.citations`` with PER-SUBMITTER attribution (no global PMID dedup).
An esummary (details) failure keeps its original error; a citation-fetch
failure keeps the details with empty citations, ``citations_complete``
false and an explicit warning.
"""

import json
from unittest.mock import patch

import pytest

from tooluniverse.clinvar_submitted_tool import ClinVarSubmittedRecordsTool
from tooluniverse.clinvar_tool import ClinVarGetVariantDetails

pytestmark = pytest.mark.unit

_DETAILS_ID = "2737810"


def _tool():
    return ClinVarGetVariantDetails({"name": "ClinVar_get_variant_details"})


def _fetch_ok(**extra):
    variant_data = {
        "accession": "VCV002737810",
        "obj_type": "single nucleotide variant",
        "chr_sort": "13",
        "variation_set": [
            {
                "variation_name": "NM_1:c.1A>G",
                "variation_loc": [{"band": "13q33.1"}],
            }
        ],
        "title": "NM_1(BRCA2):c.1A>G",
        "gene_set": [{"symbol": "BRCA2"}],
        "germline_classification": {"description": "Pathogenic"},
        "review_status": "reviewed by expert panel",
        **extra,
    }
    return {
        "variant_data": variant_data,
        "result": {"status": "success", "data": {}},
    }


def _vcv_xml(citation_blocks):
    """Realistic VCV XML: ClinVarAccession carries the REAL Accession /
    Version / SubmitterName attributes the parser reads."""
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
            f'<ClinVarAccession Accession="{scv}" Version="2" '
            f'SubmitterName="Lab {scv}"/>'
            f"<Classification><GermlineClassification>Pathogenic"
            f"</GermlineClassification></Classification>"
            f"{cite_xml}"
            f"</ClinicalAssertion>"
        )
    return (
        "<ClinVarVariationArchive>"
        '<VariationArchive VariationName="NM_1:c.1A>G" VariationID="2737810" '
        'Accession="VCV002737810">'
        "<ClassifiedRecord><Classifications><GermlineClassification>"
        "<Description>Pathogenic</Description>"
        "</GermlineClassification></Classifications>"
        f"<ClinicalAssertionList>{''.join(assertions)}</ClinicalAssertionList>"
        "</ClassifiedRecord></VariationArchive></ClinVarVariationArchive>"
    )


class _Resp:
    def __init__(self, payload):
        self.payload = payload
        self.status_code = 200

    @property
    def content(self):
        return self.payload.encode()

    def json(self):
        return self.payload


def _run_details(xml, titles_payload=None, titles_error=None):
    """Run the details tool with its esummary fetch mocked OK and the
    submitted-records path exercised for real (only HTTP mocked)."""

    def fake_get(url, params=None, timeout=None, headers=None):
        if "efetch" in url:
            return _Resp(xml)
        assert "esummary" in url and params.get("db") == "pubmed"
        if titles_error is not None:
            raise titles_error
        return _Resp(titles_payload)

    with patch.object(
        ClinVarGetVariantDetails, "_fetch_variant", return_value=_fetch_ok()
    ), patch(
        "tooluniverse.clinvar_submitted_tool.requests.get", side_effect=fake_get
    ):
        return _tool().run({"variant_id": _DETAILS_ID})


def test_normal_citations_with_attribution_and_complete():
    xml = _vcv_xml(
        {
            "SCV1": [("Classification/Citation", "31573083")],
            "SCV2": [("AttributeSet/Citation", "28492532")],
        }
    )
    result = _run_details(
        xml,
        titles_payload={
            "result": {
                "31573083": {"title": "Panel-based NGS study"},
                "28492532": {"title": "Sherloc"},
            }
        },
    )
    assert result["status"] == "success"
    data = result["data"]
    assert data["clinical_significance"] == "Pathogenic"  # details intact
    assert data["citations_complete"] is True
    assert "citation_warnings" not in data
    by_scv = {}
    for c in data["citations"]:
        by_scv[c["scv_accession"]] = c
    assert by_scv["SCV1.2"]["pmid"] == "31573083"
    assert by_scv["SCV1.2"]["title"] == "Panel-based NGS study"
    assert by_scv["SCV1.2"]["source_path"] == "Classification/Citation"
    assert by_scv["SCV1.2"]["submitter"] == "Lab SCV1"
    assert by_scv["SCV2.2"]["pmid"] == "28492532"
    assert by_scv["SCV2.2"]["source_path"] == "AttributeSet/Citation"


def test_same_pmid_two_scvs_kept_as_two_entries():
    """No global PMID dedup: two submitters citing the same PMID keep their
    own attribution in the flattened list."""
    xml = _vcv_xml(
        {
            "SCV1": [("Classification/Citation", "111")],
            "SCV2": [("Classification/Citation", "111")],
        }
    )
    result = _run_details(xml, titles_payload={"result": {"111": {"title": "T"}}})
    citations = result["data"]["citations"]
    assert len(citations) == 2
    assert {c["scv_accession"] for c in citations} == {"SCV1.2", "SCV2.2"}
    assert {c["submitter"] for c in citations} == {"Lab SCV1", "Lab SCV2"}
    assert all(c["pmid"] == "111" for c in citations)


def test_no_citations_complete_true():
    result = _run_details(_vcv_xml({"SCV1": []}))
    assert result["status"] == "success"
    assert result["data"]["citations"] == []
    assert result["data"]["citations_complete"] is True
    assert "citation_warnings" not in result["data"]


def test_vcv_fetch_failure_keeps_details_with_warning():
    """VCV efetch returns an HTTP error: the details survive, citations are
    empty, complete=false, and an explicit warning names the failure."""
    tool = _tool()
    submitted_error = {
        "status": "error",
        "error": "NCBI efetch returned HTTP 503 for VCV002737810.",
    }
    with patch.object(
        ClinVarGetVariantDetails, "_fetch_variant", return_value=_fetch_ok()
    ), patch.object(
        ClinVarSubmittedRecordsTool, "run", return_value=submitted_error
    ):
        result = tool.run({"variant_id": _DETAILS_ID})
    assert result["status"] == "success"
    data = result["data"]
    assert data["variation_name"] == "NM_1:c.1A>G"
    assert data["citations"] == []
    assert data["citations_complete"] is False
    assert any(
        "Submitter citation fetch failed" in w and "HTTP 503" in w
        for w in data["citation_warnings"]
    )


def test_partial_title_failure_incomplete_with_null_title():
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "111")]})
    result = _run_details(
        xml, titles_payload={"result": {"111": {"title": "   "}}}
    )
    data = result["data"]
    assert data["citations"][0]["pmid"] == "111"
    assert data["citations"][0]["title"] is None
    assert data["citations_complete"] is False
    assert any("111" in w for w in data["citation_warnings"])


def test_output_matches_declared_schema():
    """Every data key the tool emits is declared in the return schema, and
    every citation item key matches the schema's item properties."""
    xml = _vcv_xml({"SCV1": [("Classification/Citation", "111")]})
    result = _run_details(xml, titles_payload={"result": {"111": {"title": "T"}}})
    data = result["data"]
    registry = json.load(open("src/tooluniverse/data/clinvar_tools.json"))
    entry = next(t for t in registry if t["name"] == "ClinVar_get_variant_details")
    schema_props = entry["return_schema"]["properties"]["data"]["properties"]
    for key in data:
        assert key in schema_props, f"undeclared output key {key!r}"
    citation_item_props = schema_props["citations"]["items"]["properties"]
    for citation in data["citations"]:
        for key in citation:
            assert key in citation_item_props, f"undeclared citation key {key!r}"
    assert schema_props["citations_complete"]["type"] == "boolean"


# ---------- Fix-F01-20261013: observed/direct citations via details entry ----------


def test_observed_and_direct_citations_match_submitted_records_entry():
    """F01 consistency: the same VCV XML must yield the SAME citation set
    (pmid, source_path, attribution) whether read through
    ClinVar_get_submitted_records or ClinVar_get_variant_details."""
    xml = (
        "<ClinVarVariationArchive>"
        '<VariationArchive VariationName="NM_1:c.1A>G" VariationID="2737810" '
        'Accession="VCV002737810">'
        "<ClassifiedRecord><Classifications><GermlineClassification>"
        "<Description>Pathogenic</Description>"
        "</GermlineClassification></Classifications>"
        "<ClinicalAssertionList>"
        "<ClinicalAssertion>"
        '<ClinVarAccession Accession="SCV000035247" Version="13" '
        'SubmitterName="Labcorp"/>'
        "<Classification><GermlineClassification>Pathogenic"
        "</GermlineClassification></Classification>"
        "<ObservedInList><ObservedIn><ObservedData>"
        '<Citation><ID Source="PubMed">12068308</ID></Citation>'
        "</ObservedData></ObservedIn></ObservedInList>"
        "<Citation><ID Source=\"PubMed\">31573083</ID></Citation>"
        "</ClinicalAssertion>"
        "</ClinicalAssertionList>"
        "</ClassifiedRecord></VariationArchive></ClinVarVariationArchive>"
    )
    titles = {
        "result": {
            "12068308": {"title": "Observed"},
            "31573083": {"title": "Direct"},
        }
    }

    class _Resp:
        def __init__(self, payload):
            self.payload = payload
            self.status_code = 200

        @property
        def content(self):
            return self.payload.encode()

        def json(self):
            return self.payload

    def fake_get(url, params=None, timeout=None, headers=None):
        if "efetch" in url:
            return _Resp(xml)
        assert "esummary" in url and params.get("db") == "pubmed"
        return _Resp(titles)

    submitted = ClinVarSubmittedRecordsTool(
        {"name": "ClinVar_get_submitted_records"}
    )
    with patch(
        "tooluniverse.clinvar_submitted_tool.requests.get", side_effect=fake_get
    ):
        sub_result = submitted.run({"variant_id": "VCV000013961"})

    tool = _tool()
    with patch.object(
        ClinVarGetVariantDetails, "_fetch_variant", return_value=_fetch_ok()
    ), patch(
        "tooluniverse.clinvar_submitted_tool.requests.get", side_effect=fake_get
    ):
        details_result = tool.run({"variant_id": _DETAILS_ID})

    sub_cits = [
        (c["pmid"], c["source_path"])
        for s in sub_result["data"]["submissions"]
        for c in s["citations"]
    ]
    detail_cits = [(c["pmid"], c["source_path"]) for c in details_result["data"]["citations"]]
    assert sub_cits == detail_cits == [
        ("12068308", "ObservedInList/ObservedIn/ObservedData/Citation"),
        ("31573083", "Citation"),
    ]
    assert details_result["data"]["citations_complete"] is True
    assert sub_result["data"]["citations_complete"] is True
