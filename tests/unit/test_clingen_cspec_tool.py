"""Unit tests for the ClinGen_search_cspec operation (ClinGenTool).

All fixtures are frozen snapshots of the CSpec API shape (index
``/cspec/api/svis`` and detail ``/cspec/api/SequenceVariantInterpretation/id/…``
as confirmed live on 2026-09-09); no test here touches the network.
"""

import pytest
import requests

from tooluniverse.clingen_tool import ClinGenTool


class _Response:
    def __init__(self, payload, url="https://cspec.example/test"):
        self._payload = payload
        self.url = url

    def raise_for_status(self):
        return None

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _index_record(
    spec_id="GN019",
    gene="MYOC",
    disease_label="MONDO:0005338",
    inheritance="Autosomal dominant inheritance",
    status="Released",
    version="2.1",
    rule_set_id="635003681",
):
    return {
        "@id": (
            "https://cspec.genome.network/cspec/api/"
            f"SequenceVariantInterpretation/id/{spec_id}"
        ),
        "affiliation": {
            "@id": "https://cspec.genome.network/cspec/api/Organization/id/50053",
            "@type": "Organization",
            "label": "Glaucoma Variant Curation Expert Panel",
        },
        "ruleSets": [
            {
                "@id": (
                    "https://cspec.genome.network/cspec/api/"
                    f"RuleSet/id/{rule_set_id}"
                ),
                "@type": "RuleSet",
                "genes": [
                    {
                        "@id": f"https://www.genenames.org/tools/search/#!/?query={gene}",
                        "@type": "Gene",
                        "label": gene,
                        "diseases": [
                            {
                                "@id": "http://purl.obolibrary.org/obo/MONDO_0005338",
                                "@type": "Disease",
                                "label": disease_label,
                                "modeOfInheritance": [
                                    {
                                        "@id": "https://hpo.jax.org/app/browse/term/HP:0000006",
                                        "@label": inheritance,
                                        "@type": "Mode of inheritance",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
        "status": status,
        "url": f"https://cspec.genome.network/cspec/ui/svi/doc/{spec_id}",
        "version": version,
    }


def _detail_payload(
    spec_id="GN019",
    rule_set_id="635003681",
    criteria=None,
    assertion_method=True,
):
    if criteria is None:
        criteria = [
            {
                "@id": (
                    "https://cspec.genome.network/cspec/api/"
                    "CriteriaCode/id/635003689"
                ),
                "@type": "CriteriaCode",
                "label": "PM2",
                "description": "Absent from controls.",
                "evidenceStrengths": [
                    {
                        "@id": (
                            "https://cspec.genome.network/cspec/api/"
                            "CriteriaCode/id/635003689/str/Supporting"
                        ),
                        "@type": "EvidenceStrength",
                        "label": "Supporting",
                        "applicability": "Applicable",
                        "description": "Allele frequency <= 0.0001.",
                    },
                    {
                        "@id": (
                            "https://cspec.genome.network/cspec/api/"
                            "CriteriaCode/id/635003689/str/Moderate"
                        ),
                        "@type": "EvidenceStrength",
                        "label": "Moderate",
                        "applicability": "Not Applicable",
                    },
                ],
            }
        ]
    payload = {
        "@id": (
            "https://cspec.genome.network/cspec/api/"
            f"SequenceVariantInterpretation/id/{spec_id}"
        ),
        "@type": "SequenceVariantInterpretation",
        "affiliation": {
            "@id": "https://cspec.genome.network/cspec/api/Organization/id/50053",
            "label": "Glaucoma Variant Curation Expert Panel",
        },
        "label": (
            "ClinGen Glaucoma Expert Panel Specifications to the ACMG/AMP "
            f"Variant Interpretation Guidelines for MYOC Version 2.1"
        ),
        "version": "2.1",
        "lastUpdated": "2025-06-13",
        "cspecStatus": "Released",
        "ruleSets": [
            {
                "@id": (
                    "https://cspec.genome.network/cspec/api/"
                    f"RuleSet/id/{rule_set_id}"
                ),
                "@type": "RuleSet",
                "criteriaCodes": criteria,
                "genes": [{"@type": "Gene", "label": "MYOC"}],
            }
        ],
    }
    if assertion_method:
        payload["assertionMethod"] = {
            "@id": "_:am1",
            "@type": "AssertionMethod",
            "url": (
                "https://cspec.genome.network/cspec/"
                "SequenceVariantInterpretation/id/635003679"
            ),
        }
    return payload


def _tool():
    return ClinGenTool(
        {"name": "ClinGen_search_cspec", "fields": {"operation": "search_cspec"}}
    )


def _patch(monkeypatch, index_payload, detail_payloads=None, fail_detail_ids=()):
    """Route fake requests.get: index payload for /svis, per-spec detail after."""
    detail_payloads = detail_payloads if detail_payloads is not None else {}
    requested = []

    def fake_get(url, **_kwargs):
        requested.append(url)
        if url.endswith("/cspec/api/svis"):
            if isinstance(index_payload, Exception):
                raise index_payload
            return _Response(index_payload, url)
        spec_id = url.rstrip("/").rsplit("/", 1)[-1]
        if spec_id in fail_detail_ids:
            raise requests.exceptions.HTTPError(f"500 for {spec_id}")
        return _Response(detail_payloads.get(spec_id, _detail_payload()), url)

    monkeypatch.setattr("tooluniverse.clingen_tool.requests.get", fake_get)
    return requested


def _index(*records):
    return {
        "@context": "https://cspec.genome.network/cspec/api/context/svis",
        "data": list(records),
    }


def test_cspec_missing_gene_is_error():
    assert _tool().run({})["status"] == "error"


def test_cspec_released_filter_and_exact_gene_match(monkeypatch):
    index = _index(
        _index_record(),
        _index_record(
            spec_id="GNOLD",
            gene="MYOC",
            status="Retired",
            version="1.0",
            rule_set_id="111",
        ),
        _index_record(spec_id="GNBRCA", gene="BRCA1", rule_set_id="222"),
    )
    _patch(monkeypatch, index)

    result = _tool().run({"gene": "myoc"})

    assert result["status"] == "success"
    assert result["gene"] == "MYOC"
    assert result["total"] == 1
    entry = result["data"][0]
    assert entry["specification_id"] == "GN019"
    assert entry["vcep"] == "Glaucoma Variant Curation Expert Panel"
    assert entry["status"] == "Released"


def test_cspec_exact_match_not_substring(monkeypatch):
    index = _index(_index_record())
    _patch(monkeypatch, index)

    result = _tool().run({"gene": "MYO"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["total"] == 0


def test_cspec_empty_result_is_success_with_guidance_note(monkeypatch):
    _patch(monkeypatch, _index(_index_record(spec_id="GNBRCA", gene="BRCA1")))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["data"] == []
    note = result["note"]
    # A valid empty result must read as "no Released specification", and say
    # what to do next -- generic ACMG/SVI rules apply.
    assert "no Released" in note or "No Released" in note
    assert "generic" in note


def test_cspec_success_note_names_the_official_page_reading_step(monkeypatch):
    _patch(monkeypatch, _index(_index_record()))

    result = _tool().run({"gene": "MYOC"})

    # The API JSON is not the full specification: the note must direct the
    # caller to read the official page before classifying.
    assert "get_webpage_text_from_url" in result["note"]
    assert "url" in result["data"][0]


def test_cspec_preserves_rule_set_gene_disease_binding(monkeypatch):
    record = _index_record()
    second_rule_set = {
        "@id": "https://cspec.genome.network/cspec/api/RuleSet/id/999",
        "@type": "RuleSet",
        "genes": [
            {
                "@type": "Gene",
                "label": "MYOC",
                "diseases": [
                    {
                        "@id": "http://purl.obolibrary.org/obo/MONDO_0009999",
                        "label": "MONDO:0009999",
                        "modeOfInheritance": [
                            {"@label": "Autosomal recessive inheritance"}
                        ],
                    }
                ],
            }
        ],
    }
    record["ruleSets"].append(second_rule_set)
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["total"] == 1
    entry = result["data"][0]
    assert len(entry["rule_sets"]) == 2
    rule_set_ids = {rs["rule_set_id"] for rs in entry["rule_sets"]}
    assert rule_set_ids == {"635003681", "999"}
    # Each rule set keeps its own gene-disease-inheritance binding; they are
    # not merged into one undifferentiated disease list.
    by_id = {rs["rule_set_id"]: rs for rs in entry["rule_sets"]}
    assert by_id["635003681"]["genes"][0]["diseases"][0]["mondo_id"] == (
        "MONDO:0005338"
    )
    assert by_id["999"]["genes"][0]["diseases"][0]["mondo_id"] == "MONDO:0009999"
    assert by_id["635003681"]["genes"][0]["diseases"][0]["inheritance"] == [
        "Autosomal dominant inheritance"
    ]
    assert by_id["999"]["genes"][0]["diseases"][0]["inheritance"] == [
        "Autosomal recessive inheritance"
    ]


def test_cspec_two_specifications_stay_separate(monkeypatch):
    index = _index(
        _index_record(version="2.1"),
        _index_record(spec_id="GN020", version="3.0", rule_set_id="777"),
    )
    _patch(monkeypatch, index)

    result = _tool().run({"gene": "MYOC"})

    assert result["total"] == 2
    versions = {e["version"] for e in result["data"]}
    assert versions == {"2.1", "3.0"}
    assert {e["specification_id"] for e in result["data"]} == {"GN019", "GN020"}


def test_cspec_version_falls_back_to_title(monkeypatch):
    record = _index_record()
    record.pop("version")
    record["url"] = None
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    # `version` absent on the index record: parsed from the label ("Version
    # 2.1"), and the official page URL derived from the specification id.
    assert entry["version"] == "2.1"
    assert entry["url"] == "https://cspec.genome.network/cspec/ui/svi/doc/GN019"


def test_cspec_criteria_bound_to_rule_set_with_strength_details(monkeypatch):
    _patch(monkeypatch, _index(_index_record()))

    result = _tool().run({"gene": "MYOC"})

    mods = result["data"][0]["criterion_modifications"]
    assert mods, "criterion modifications must be present"
    pm2 = next(m for m in mods if m["criterion"] == "PM2")
    assert pm2["rule_set_id"] == "635003681"
    supporting = next(s for s in pm2["strengths"] if s["strength"] == "Supporting")
    assert supporting["applicability"] == "Applicable"
    assert supporting["text"] == "Allele frequency <= 0.0001."
    moderate = next(s for s in pm2["strengths"] if s["strength"] == "Moderate")
    assert moderate["applicability"] == "Not Applicable"


def test_cspec_assertion_method_and_raw_specification_kept(monkeypatch):
    _patch(monkeypatch, _index(_index_record()))

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry["assertion_method_url"] == (
        "https://cspec.genome.network/cspec/SequenceVariantInterpretation/"
        "id/635003679"
    )
    assert entry["missing_materials"] == []
    # The raw specification JSON travels with the entry for auditability.
    assert entry["specification"]["version"] == "2.1"
    assert entry["api_url"].endswith("/SequenceVariantInterpretation/id/GN019")


def test_cspec_missing_assertion_method_is_flagged(monkeypatch):
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": _detail_payload(assertion_method=False)},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry["assertion_method_url"] is None
    assert "assertion_method" in entry["missing_materials"]


def test_cspec_detail_partial_failure_is_disclosed_not_swallowed(monkeypatch):
    _patch(
        monkeypatch,
        _index(
            _index_record(),
            _index_record(spec_id="GN020", version="3.0", rule_set_id="777"),
        ),
        fail_detail_ids=("GN020",),
    )

    result = _tool().run({"gene": "MYOC"})

    # One detail fetch failing must not fail the whole search, and must not
    # be presented as a complete answer either.
    assert result["status"] == "success"
    assert result["total"] == 2
    assert "GN020" in result["partial_failures"]
    failed = next(e for e in result["data"] if e["specification_id"] == "GN020")
    assert failed["detail_fetch_failed"] is True
    assert any("specification" in m for m in failed["missing_materials"])


def test_cspec_malformed_index_json_is_error_not_no_cspec(monkeypatch):
    _patch(monkeypatch, ValueError("Expecting value: line 1 column 1 (char 0)"))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    # An error must never be readable as "the gene has no CSpec".
    assert "no Released" not in result["error"]
    assert "data" not in result


def test_cspec_timeout_is_error(monkeypatch):
    _patch(
        monkeypatch,
        requests.exceptions.Timeout("timed out"),
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "Timeout" in result["error"]


def test_cspec_index_http_error_is_error(monkeypatch):
    def fake_get(url, **_kwargs):
        raise requests.exceptions.HTTPError("503 Service Unavailable")

    monkeypatch.setattr("tooluniverse.clingen_tool.requests.get", fake_get)

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"


def test_cspec_index_unexpected_shape_is_error(monkeypatch):
    _patch(monkeypatch, ["not", "a", "dict"])

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
