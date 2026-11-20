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


def _gn015_record(version="1.0", rule_set_ids=("135641398",)):
    """Live GN015 index shape (frozen 2026-11-20): Released, Mitochondrial
    Diseases VCEP, and every rule set carries NO `genes` key at all."""
    return {
        "@id": (
            "https://cspec.genome.network/cspec/api/"
            "SequenceVariantInterpretation/id/GN015"
        ),
        "affiliation": {
            "@id": (
                "https://cspec.genome.network/cspec/api/Organization/id/50027"
            ),
            "@type": "Organization",
            "label": "Mitochondrial Diseases Variant Curation Expert Panel",
            "url": "http://clinicalgenome.org/affiliation/50027",
        },
        "ruleSets": [
            {
                "@id": (
                    "https://cspec.genome.network/cspec/api/"
                    f"RuleSet/id/{rule_set_id}"
                ),
                "@type": "RuleSet",
            }
            for rule_set_id in rule_set_ids
        ],
        "status": "Released",
        "url": "https://cspec.genome.network/cspec/ui/svi/doc/GN015",
        "version": version,
    }


def _patch(monkeypatch, index_payload, detail_payloads=None, fail_detail_ids=()):
    """Route fake requests.get: index payload for /svis, per-spec detail after.

    Scope applicability is decided locally (no registry dependency), so ANY
    request outside the CSpec index/detail endpoints raises: a spurious
    lookup must fail the test loudly, not pass silently.
    """
    detail_payloads = detail_payloads if detail_payloads is not None else {}
    requested = []

    def fake_get(url, **_kwargs):
        requested.append(url)
        if "rest.genenames.org" in url:
            raise AssertionError(f"search-time registry query forbidden: {url}")
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


# --------------------------------------------------------------------------- #
# Index structural damage must stay an error, never a valid empty result
# --------------------------------------------------------------------------- #
def test_malformed_index_is_not_a_valid_empty_result(monkeypatch):
    _patch(monkeypatch, {"data": [None]})

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "data[0]" in result["error"]
    # Never readable as "no specification exists"; not a JSON-decode claim.
    assert "no specification exists" in result["error"]
    assert "not valid JSON" not in result["error"]


def test_missing_or_non_string_status_is_error(monkeypatch):
    record = _index_record()
    del record["status"]
    _patch(monkeypatch, _index(record))

    assert _tool().run({"gene": "MYOC"})["status"] == "error"

    _patch(monkeypatch, _index(_index_record(status=123)))
    assert _tool().run({"gene": "MYOC"})["status"] == "error"


def test_released_record_without_usable_id_is_error(monkeypatch):
    record = _index_record()
    del record["@id"]
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "no specification exists" in result["error"]


def test_released_record_with_broken_rulesets_is_error(monkeypatch):
    record = _index_record()
    record["ruleSets"] = "broken"
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "ruleSets" in result["error"]


def test_released_record_with_non_list_genes_is_error(monkeypatch):
    record = _index_record()
    record["ruleSets"][0]["genes"] = "MYOC"
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "genes is not a list" in result["error"]


def test_unlisted_gene_scope_returns_unresolved_candidate(monkeypatch):
    # Real-world shape (live GN015): a Released rule set whose index entry
    # carries no `genes`. The API not listing genes says NOTHING about
    # applicability (GN015's official page provides mitochondrial gene
    # rules) -- the spec must be kept as an unresolved-scope candidate,
    # never reported as determinately inapplicable and never silently
    # dropped.
    unlisted = _index_record(spec_id="GN015", gene="MYOC")
    del unlisted["ruleSets"][0]["genes"]
    _patch(monkeypatch, _index(unlisted))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["total"] == 0
    assert len(result["unresolved_scope_specs"]) == 1
    candidate = result["unresolved_scope_specs"][0]
    assert candidate["specification_id"] == "GN015"
    assert candidate["scope_reason"] == "gene_binding_unavailable"
    assert candidate["rule_set_ids"] == ["635003681"]
    assert candidate["api_url"].endswith("/SequenceVariantInterpretation/id/GN015")
    # The response must not claim a completed "no specification" judgment,
    # and must not direct the caller to generic classification.
    assert "unresolved" in result["note"]
    assert "classify under" not in result["note"]
    assert "do not default to generic rules" in result["note"]


@pytest.mark.parametrize("genes_value", [None, []])
def test_null_or_empty_genes_returns_candidate(monkeypatch, genes_value):
    record = _index_record()
    record["ruleSets"][0]["genes"] = genes_value
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert [c["specification_id"] for c in result["unresolved_scope_specs"]] == [
        "GN019"
    ]


def test_match_and_unresolved_candidate_coexist(monkeypatch):
    unlisted = _index_record(spec_id="GN015", gene="MYOC", rule_set_id="999")
    del unlisted["ruleSets"][0]["genes"]
    _patch(monkeypatch, _index(_index_record(), unlisted))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert [e["specification_id"] for e in result["data"]] == ["GN019"]
    assert result["total"] == 1  # candidates are not counted
    assert [c["specification_id"] for c in result["unresolved_scope_specs"]] == [
        "GN015"
    ]


def test_one_spec_with_matching_and_unresolved_rule_sets(monkeypatch):
    record = _index_record()
    record["ruleSets"].append(
        {"@id": "https://cspec.genome.network/cspec/api/RuleSet/id/888"}
    )  # second rule set without genes: unresolved, kept separate
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    entry = result["data"][0]
    assert [rs["rule_set_id"] for rs in entry["rule_sets"]] == ["635003681"]
    candidates = result["unresolved_scope_specs"]
    assert len(candidates) == 1
    assert candidates[0]["specification_id"] == "GN019"
    assert candidates[0]["rule_set_ids"] == ["888"]


def test_released_empty_rulesets_returns_candidate(monkeypatch):
    record = _index_record()
    record["ruleSets"] = []
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["data"] == []
    candidate = result["unresolved_scope_specs"][0]
    assert candidate["specification_id"] == "GN019"
    assert candidate["rule_set_ids"] == []


def test_candidate_missing_version_and_vcep_stay_missing(monkeypatch):
    record = _index_record()
    record.pop("version", None)
    record["affiliation"] = {}
    del record["ruleSets"][0]["genes"]
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    candidate = result["unresolved_scope_specs"][0]
    assert candidate["version"] is None
    assert candidate["vcep"] is None


def test_unresolved_rule_set_with_bad_id_is_error(monkeypatch):
    record = _index_record()
    del record["ruleSets"][0]["genes"]
    del record["ruleSets"][0]["@id"]
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "no usable" in result["error"]


def test_valid_empty_result_has_empty_candidates(monkeypatch):
    _patch(monkeypatch, _index(_index_record(spec_id="GNBRCA", gene="BRCA1")))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["unresolved_scope_specs"] == []
    # Full "no specification" judgment is allowed only in this state.
    assert "No Released" in result["note"]
    assert "generic" in result["note"]


def test_match_response_carries_empty_candidates_field(monkeypatch):
    _patch(monkeypatch, _index(_index_record()))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["total"] == 1
    assert result["unresolved_scope_specs"] == []


def test_released_record_with_non_string_gene_label_is_error(monkeypatch):
    record = _index_record()
    record["ruleSets"][0]["genes"][0]["label"] = 42
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "label" in result["error"]


def test_mixed_normal_and_corrupt_records_is_error(monkeypatch):
    # One broken record poisons the applicability decision even when a
    # perfectly valid Released record for the gene is also present.
    _patch(monkeypatch, _index(_index_record(), None))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"


def test_matched_rule_set_without_usable_id_is_error(monkeypatch):
    record = _index_record()
    del record["ruleSets"][0]["@id"]
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "no usable" in result["error"]


def test_non_released_records_do_not_require_released_detail(monkeypatch):
    # Draft/retired records are filtered by status alone; their structure
    # must not be held to Released standards, or every draft would error.
    draft = _index_record(spec_id="GNDRAFT", gene="MYOC", status="Draft")
    del draft["ruleSets"]
    del draft["@id"]
    _patch(monkeypatch, _index(_index_record(), draft))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["total"] == 1
    assert result["data"][0]["specification_id"] == "GN019"


def test_detail_non_object_is_partial_structure_failure(monkeypatch):
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": ["not", "an", "object"]},
    )

    result = _tool().run({"gene": "MYOC"})

    # The candidate specification is kept; the structural damage is
    # disclosed as a partial failure, distinct from missing optional
    # material, and never reported as a fully-read specification.
    assert result["status"] == "success"
    entry = result["data"][0]
    assert entry["detail_structure_failed"] is True
    assert "GN019" in result["partial_failures"]
    assert any(
        "detail structure damaged" in m for m in entry["missing_materials"]
    )
    assert entry["criterion_modifications"] == []


# --------------------------------------------------------------------------- #
# ID validation: non-string / blank IDs must never normalize into valid ones
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw_id", [123, {"bad": "id"}, " \t "])
@pytest.mark.parametrize("unresolved", [False, True])
def test_invalid_rule_set_id_is_error(monkeypatch, raw_id, unresolved):
    record = _index_record()
    record["ruleSets"][0]["@id"] = raw_id
    if unresolved:
        del record["ruleSets"][0]["genes"]
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "no usable" in result["error"]


def test_slash_only_spec_id_is_error(monkeypatch):
    # A string @id that normalizes to empty (pure slashes) must not
    # silently produce results with a blank specification_id.
    record = _index_record()
    record["@id"] = "///"
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "normalizes to an empty identifier" in result["error"]
    assert "not a statement that no specification exists" in result["error"]


def test_numeric_string_id_still_accepted(monkeypatch):
    # String-typed IDs remain valid input regardless of their content.
    record = _index_record()
    record["ruleSets"][0]["@id"] = (
        "https://cspec.genome.network/cspec/api/RuleSet/id/635003681"
    )
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["data"][0]["rule_sets"][0]["rule_set_id"] == "635003681"


def test_detail_rule_set_with_invalid_id_disclosed_not_filtered(monkeypatch):
    # A non-string @id inside the detail cannot be attributed to any rule
    # set: it must surface as structural damage -- never fall through to
    # the "clearly unrelated rule set" filter that would hide it.
    detail = _detail_payload()
    detail["ruleSets"].append(
        {"@id": 123, "criteriaCodes": [{"label": "PM2"}]}
    )
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    entry = result["data"][0]
    # Valid criteria from the selected rule set survive...
    assert [c["criterion"] for c in entry["criterion_modifications"]] == ["PM2"]
    # ...and the unattributable damage is disclosed on all three channels.
    assert entry["detail_structure_failed"] is True
    assert any(
        "ruleSets[1].@id" in m for m in entry["missing_materials"]
    ), entry["missing_materials"]
    assert "GN019" in result["partial_failures"]
    assert "ruleSets[1].@id" in result["partial_failures"]["GN019"]
# --------------------------------------------------------------------------- #
# Detail-internal damage: valid parts kept, damage disclosed with paths
# --------------------------------------------------------------------------- #
def _detail_with_criteria(criteria):
    return _detail_payload(criteria=criteria)


def test_detail_criteria_with_null_element_keeps_valid_and_flags(monkeypatch):
    valid_pm2 = _detail_payload()["ruleSets"][0]["criteriaCodes"][0]
    damaged = _detail_with_criteria([valid_pm2, None])
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": damaged},
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    entry = result["data"][0]
    # The valid criterion survives alongside the damage marker.
    assert [c["criterion"] for c in entry["criterion_modifications"]] == ["PM2"]
    assert entry["detail_structure_failed"] is True
    assert any(
        "criteriaCodes[1]" in m for m in entry["missing_materials"]
    ), entry["missing_materials"]
    assert "GN019" in result["partial_failures"]
    assert "criteriaCodes[1]" in result["partial_failures"]["GN019"]


def test_detail_strength_with_illegal_element_flags_path(monkeypatch):
    criteria = _detail_payload()["ruleSets"][0]["criteriaCodes"]
    criteria[0]["evidenceStrengths"] = [
        criteria[0]["evidenceStrengths"][0],
        42,
    ]
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": _detail_with_criteria(criteria)},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    strengths = entry["criterion_modifications"][0]["strengths"]
    assert [s["strength"] for s in strengths] == ["Supporting"]
    assert entry["detail_structure_failed"] is True
    assert any(
        "evidenceStrengths[1]" in m for m in entry["missing_materials"]
    ), entry["missing_materials"]


def test_detail_criterion_with_unusable_label_flagged(monkeypatch):
    criteria = _detail_payload()["ruleSets"][0]["criteriaCodes"]
    criteria[0]["label"] = 7
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": _detail_with_criteria(criteria)},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry["detail_structure_failed"] is True
    assert any(
        "label is not a usable string" in m for m in entry["missing_materials"]
    )


def test_detail_missing_optional_text_is_not_damage(monkeypatch):
    criteria = _detail_payload()["ruleSets"][0]["criteriaCodes"]
    for strength in criteria[0]["evidenceStrengths"]:
        strength.pop("description", None)  # optional prose absent: legal
    criteria[0].pop("description", None)
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": _detail_with_criteria(criteria)},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry.get("detail_structure_failed") is not True
    assert "GN019" not in result.get("partial_failures", {})
    assert entry["criterion_modifications"][0]["criterion"] == "PM2"


def test_detail_criteria_absent_is_material_gap_not_structure(monkeypatch):
    detail = _detail_payload()
    del detail["ruleSets"][0]["criteriaCodes"]
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry.get("detail_structure_failed") is not True
    assert "criterion_specifications" in entry["missing_materials"]


def test_detail_unattributable_rule_set_element_flagged(monkeypatch):
    detail = _detail_payload()
    detail["ruleSets"].append(42)  # cannot be attributed to any rule set
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry["detail_structure_failed"] is True
    assert any(
        "ruleSets[1] is not an object" in m for m in entry["missing_materials"]
    )


def test_detail_unrelated_damaged_rule_set_not_mixed(monkeypatch):
    detail = _detail_payload()
    detail["ruleSets"].append(
        {
            "@id": "https://cspec.genome.network/cspec/api/RuleSet/id/777",
            "criteriaCodes": [None],  # damaged, but clearly not selected
        }
    )
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    # Selected criteria unaffected; the unrelated damage is not smuggled in.
    assert [c["criterion"] for c in entry["criterion_modifications"]] == ["PM2"]
    assert all(
        c["rule_set_id"] == "635003681" for c in entry["criterion_modifications"]
    )


def test_one_damaged_detail_does_not_sink_other_spec(monkeypatch):
    damaged_detail = _detail_with_criteria([None])
    healthy_gn020 = _detail_payload(spec_id="GN020", rule_set_id="777")
    healthy_gn020["version"] = "3.0"  # match its index record
    _patch(
        monkeypatch,
        _index(
            _index_record(),
            _index_record(spec_id="GN020", version="3.0", rule_set_id="777"),
        ),
        detail_payloads={"GN019": damaged_detail, "GN020": healthy_gn020},
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    by_id = {e["specification_id"]: e for e in result["data"]}
    assert by_id["GN020"]["criterion_modifications"][0]["criterion"] == "PM2"
    assert by_id["GN019"]["detail_structure_failed"] is True
    assert set(result["partial_failures"]) == {"GN019"}


# --------------------------------------------------------------------------- #
# Per-rule-set material coverage (issue 7)
# --------------------------------------------------------------------------- #
def _two_rule_set_index():
    record = _index_record()
    record["ruleSets"].append(
        {
            "@id": "https://cspec.genome.network/cspec/api/RuleSet/id/777",
            "genes": [
                {
                    "@type": "Gene",
                    "label": "MYOC",
                    "diseases": [
                        {
                            "label": "MONDO:0009999",
                            "modeOfInheritance": [
                                {"@label": "Autosomal recessive inheritance"}
                            ],
                        }
                    ],
                }
            ],
        }
    )
    return record


def test_second_rule_set_missing_from_detail_is_disclosed(monkeypatch):
    # Index matches two rule sets; the detail carries criteria only for the
    # first -- the second rule set's materials are missing, and the gap
    # must name the rule set id instead of passing silently because the
    # overall criteria list is non-empty.
    _patch(monkeypatch, _index(_two_rule_set_index()))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    entry = result["data"][0]
    assert [c["rule_set_id"] for c in entry["criterion_modifications"]] == [
        "635003681"
    ]
    assert (
        "criterion_specifications (rule_set_id=777)" in entry["missing_materials"]
    ), entry["missing_materials"]
    # A legitimate absence is a material gap, not structural damage.
    assert entry.get("detail_structure_failed") is not True
    assert "GN019" not in result.get("partial_failures", {})


@pytest.mark.parametrize("codes", [None, []])
def test_second_rule_set_with_empty_criteria_is_disclosed(monkeypatch, codes):
    detail = _detail_payload()
    detail["ruleSets"].append(
        {
            "@id": "https://cspec.genome.network/cspec/api/RuleSet/id/777",
            "genes": [{"label": "MYOC"}],
            "criteriaCodes": codes,
        }
    )
    _patch(
        monkeypatch,
        _index(_two_rule_set_index()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    entry = result["data"][0]
    assert [c["rule_set_id"] for c in entry["criterion_modifications"]] == [
        "635003681"
    ]
    assert (
        "criterion_specifications (rule_set_id=777)" in entry["missing_materials"]
    )
    assert entry.get("detail_structure_failed") is not True


def test_complete_response_not_flagged_for_rule_set_gaps(monkeypatch):
    detail = _detail_payload()
    detail["ruleSets"].append(
        {
            "@id": "https://cspec.genome.network/cspec/api/RuleSet/id/777",
            "genes": [{"label": "MYOC"}],
            "criteriaCodes": _detail_payload()["ruleSets"][0]["criteriaCodes"],
        }
    )
    _patch(
        monkeypatch,
        _index(_two_rule_set_index()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert not any(
        "rule_set_id=" in m for m in entry["missing_materials"]
    ), entry["missing_materials"]


# --------------------------------------------------------------------------- #
# Disease / inheritance binding validation (issue 8)
# --------------------------------------------------------------------------- #
def test_diseases_with_null_element_is_error(monkeypatch):
    record = _index_record()
    record["ruleSets"][0]["genes"][0]["diseases"].append(None)
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "diseases[1]" in result["error"]


@pytest.mark.parametrize("bad", [42, "MONDO:1", {"label": "MONDO:1"}])
def test_diseases_wrong_container_is_error(monkeypatch, bad):
    record = _index_record()
    record["ruleSets"][0]["genes"][0]["diseases"] = bad
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "error"
    assert "diseases is not a list" in result["error"]


def test_inheritance_bad_element_and_label_are_errors(monkeypatch):
    record = _index_record()
    record["ruleSets"][0]["genes"][0]["diseases"][0]["modeOfInheritance"] = [42]
    _patch(monkeypatch, _index(record))
    assert _tool().run({"gene": "MYOC"})["status"] == "error"

    record = _index_record()
    record["ruleSets"][0]["genes"][0]["diseases"][0]["modeOfInheritance"] = [
        {"no_label": True}
    ]
    _patch(monkeypatch, _index(record))
    result = _tool().run({"gene": "MYOC"})
    assert result["status"] == "error"
    assert "@label" in result["error"]


def test_binding_defaults_stay_legal(monkeypatch):
    record = _index_record()
    gene = record["ruleSets"][0]["genes"][0]
    gene["diseases"] = []  # empty list is a legal default
    _patch(monkeypatch, _index(record))
    assert _tool().run({"gene": "MYOC"})["status"] == "success"

    record = _index_record()
    del record["ruleSets"][0]["genes"][0]["diseases"]
    _patch(monkeypatch, _index(record))
    assert _tool().run({"gene": "MYOC"})["status"] == "success"

    record = _index_record()
    record["ruleSets"][0]["genes"][0]["diseases"][0]["modeOfInheritance"] = None
    _patch(monkeypatch, _index(record))
    assert _tool().run({"gene": "MYOC"})["status"] == "success"


def test_binding_validation_limited_to_requested_gene(monkeypatch):
    # Malformed bindings on a DIFFERENT gene's entry must not fail this
    # gene's lookup; that record simply does not match.
    record = _index_record(spec_id="GNBRCA", gene="BRCA1", rule_set_id="222")
    record["ruleSets"][0]["genes"][0]["diseases"] = 42
    _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["data"] == []


# --------------------------------------------------------------------------- #
# Index/detail identity, version and status contradictions (F03, 2026-10-13):
# the merged entry must not present detail material under index identity when
# the detail's own @id, version or cspecStatus contradicts the index.
# --------------------------------------------------------------------------- #
def test_detail_id_mismatch_is_disclosed(monkeypatch):
    # Index says GN019; the detail fetched at GN019's URL identifies itself
    # as GN020 -- the rules inside may belong to another specification.
    detail = _detail_payload(spec_id="GN020")
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    entry = result["data"][0]
    assert entry["specification_id"] == "GN019"
    assert entry["detail_structure_failed"] is True
    assert any(
        "@id" in m and "GN019" in m and "GN020" in m
        for m in entry["missing_materials"]
    ), entry["missing_materials"]
    assert "GN019" in result["partial_failures"]
    assert "GN020" in result["partial_failures"]["GN019"]


def test_detail_version_mismatch_is_disclosed(monkeypatch):
    detail = _detail_payload()
    detail["version"] = "2.2"  # index says 2.1
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry["detail_structure_failed"] is True
    assert any(
        "version" in m and "2.1" in m and "2.2" in m
        for m in entry["missing_materials"]
    ), entry["missing_materials"]
    assert "version" in result["partial_failures"]["GN019"]
    # Index identity is kept for the entry; the contradiction is
    # disclosed, not silently resolved to the detail's version.
    assert entry["version"] == "2.1"


def test_detail_retired_status_is_disclosed(monkeypatch):
    detail = _detail_payload()
    detail["cspecStatus"] = "Retired"  # index says Released
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry["detail_structure_failed"] is True
    assert any(
        "cspecStatus" in m and "Retired" in m and "Released" in m
        for m in entry["missing_materials"]
    ), entry["missing_materials"]
    assert "cspecStatus" in result["partial_failures"]["GN019"]


def test_detail_identity_metadata_absent_stays_compatible(monkeypatch):
    # @id / version / cspecStatus are optional on the detail: their absence
    # must not add new failure conditions.
    detail = _detail_payload()
    del detail["@id"]
    del detail["version"]
    del detail["cspecStatus"]
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry.get("detail_structure_failed") is not True
    assert "GN019" not in result.get("partial_failures", {})
    assert entry["criterion_modifications"][0]["criterion"] == "PM2"
    # Index version still wins when the detail carries none.
    assert entry["version"] == "2.1"


def test_detail_status_case_insensitive_match_is_consistent(monkeypatch):
    detail = _detail_payload()
    detail["cspecStatus"] = "released"  # case differs, value matches
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry.get("detail_structure_failed") is not True
    assert entry["missing_materials"] == []


# --------------------------------------------------------------------------- #
# Follow-up 2026-10-14 (Batch C): distinguish metadata ABSENT (optional,
# compatible) from metadata DAMAGED (wrong type / unnormalizable) on the
# detail's @id / version / cspecStatus. Damage must surface through the
# existing three channels naming the field and actual value; absence,
# null and blank stay compatible.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad_id", [123, {}, [], "///"])
def test_detail_non_string_or_unnormalizable_id_is_damage(monkeypatch, bad_id):
    detail = _detail_payload()
    detail["@id"] = bad_id
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry["detail_structure_failed"] is True
    assert any(
        "@id" in m and ("123" in m or "{}" in m or "[]" in m or "///" in m)
        for m in entry["missing_materials"]
    ), entry["missing_materials"]
    assert "@id" in result["partial_failures"]["GN019"]


@pytest.mark.parametrize("bad_status", [123, {}, []])
def test_detail_non_string_cspec_status_is_damage(monkeypatch, bad_status):
    detail = _detail_payload()
    detail["cspecStatus"] = bad_status
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry["detail_structure_failed"] is True
    assert any(
        "cspecStatus" in m for m in entry["missing_materials"]
    ), entry["missing_materials"]
    assert "cspecStatus" in result["partial_failures"]["GN019"]


@pytest.mark.parametrize("bad_version", [123, 2.1, ["2.1"], {"v": "2.1"}])
def test_detail_non_string_version_is_damage_not_hidden(monkeypatch, bad_version):
    # The float 2.1 is the sharpest case: stringifying it yields "2.1",
    # which EQUALS the index version, so the old coercion reported a
    # consistent specification and hid the damage entirely.
    detail = _detail_payload()
    detail["version"] = bad_version
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry["detail_structure_failed"] is True
    assert any(
        "version" in m and "malformed" in m.lower()
        for m in entry["missing_materials"]
    ), entry["missing_materials"]
    assert "version" in result["partial_failures"]["GN019"]


@pytest.mark.parametrize("shape", ["null", "blank"])
def test_detail_metadata_null_or_blank_stays_compatible(monkeypatch, shape):
    detail = _detail_payload()
    detail["@id"] = None if shape == "null" else "   "
    detail["version"] = None if shape == "null" else ""
    detail["cspecStatus"] = None if shape == "null" else "  "
    _patch(
        monkeypatch,
        _index(_index_record()),
        detail_payloads={"GN019": detail},
    )

    result = _tool().run({"gene": "MYOC"})

    entry = result["data"][0]
    assert entry.get("detail_structure_failed") is not True
    assert "GN019" not in result.get("partial_failures", {})
    assert entry["criterion_modifications"][0]["criterion"] == "PM2"


def test_damaged_metadata_does_not_sink_other_specification(monkeypatch):
    damaged = _detail_payload(spec_id="GN019")
    damaged["version"] = 123
    healthy = _detail_payload(spec_id="GN020", rule_set_id="777")
    healthy["version"] = "3.0"
    healthy["label"] = healthy["label"].replace("Version 2.1", "Version 3.0")
    index = _index(
        _index_record(spec_id="GN019"),
        _index_record(spec_id="GN020", rule_set_id="777", version="3.0"),
    )
    _patch(
        monkeypatch,
        index,
        detail_payloads={"GN019": damaged, "GN020": healthy},
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    by_id = {e["specification_id"]: e for e in result["data"]}
    assert by_id["GN019"]["detail_structure_failed"] is True
    assert by_id["GN020"].get("detail_structure_failed") is not True
    assert "GN019" in result["partial_failures"]
    assert "GN020" not in result["partial_failures"]


# --------------------------------------------------------------------------- #
# 2026-11-09 (Batch B): the gene-centric mainline, generalized beyond the
# MYOC/GN015 fixtures. ClinGen_search_cspec serves ANY given HGNC symbol;
# applicability is adjudicated per gene + disease + inheritance mode from
# the official materials (SKILL step 2). The fixtures below are SYNTHETIC
# (spec ids GNTST0xx are test-only and do not exist in the real CSpec
# registry; diseases/inheritance are the canonical associations, used here
# only to exercise binding preservation); a synthetic TSC2 hit asserts
# interface behavior, never that a real TSC2 specification exists.
# --------------------------------------------------------------------------- #
_SYNTHETIC_GENE_CASES = [
    # (gene, disease_mondo, disease_label, inheritance, spec_id)
    ("MYOC", "MONDO:0005338", "MONDO:0005338",
     "Autosomal dominant inheritance", "GNTST001"),
    ("LDLR", "MONDO:0007750", "MONDO:0007750",
     "Autosomal dominant and autosomal recessive inheritance", "GNTST002"),
    ("BRCA1", "MONDO:0006573", "MONDO:0006573",
     "Autosomal dominant inheritance", "GNTST003"),
    ("MYH7", "MONDO:0004959", "MONDO:0004959",
     "Autosomal dominant inheritance", "GNTST004"),
    ("TSC2", "MONDO:0001734", "MONDO:0001734",
     "Autosomal dominant inheritance", "GNTST005"),
]


@pytest.mark.parametrize(
    "gene, disease_mondo, disease_label, inheritance, spec_id",
    _SYNTHETIC_GENE_CASES,
    ids=[case[0] for case in _SYNTHETIC_GENE_CASES],
)
def test_cspec_gene_centric_mainline_exact_match_and_binding(
    monkeypatch, gene, disease_mondo, disease_label, inheritance, spec_id
):
    # Any given HGNC symbol: case-insensitive exact match, and the
    # gene-disease-inheritance binding survives into the receipt so the
    # workflow can adjudicate applicability against the queried disease.
    # The detail payload is constructed to MATCH the index record (same
    # spec id, rule-set id, gene, version, Released status, VCEP label)
    # so the success path is genuinely complete: criteria parsed, no
    # material gaps, no fetch/structure failure flags. All bindings here
    # are synthetic -- the test verifies they are preserved verbatim, it
    # does not assert that any synthetic gene-disease-inheritance
    # combination is a clinical fact.
    rule_set_id = "9" + spec_id[-2:]
    record = _index_record(
        spec_id=spec_id,
        gene=gene,
        disease_label=disease_label,
        inheritance=inheritance,
        rule_set_id=rule_set_id,
    )
    detail = _detail_payload(spec_id=spec_id, rule_set_id=rule_set_id)
    detail["label"] = f"Synthetic {gene} specification Version 2.1"
    detail["ruleSets"][0]["genes"] = [{"@type": "Gene", "label": gene}]
    detail["affiliation"]["label"] = "Synthetic VCEP"
    record["affiliation"]["label"] = "Synthetic VCEP"
    requested = _patch(
        monkeypatch, _index(record), detail_payloads={spec_id: detail}
    )

    result = _tool().run({"gene": gene.lower()})

    assert result["status"] == "success"
    assert result["gene"] == gene
    assert result["total"] == 1
    entry = result["data"][0]
    assert entry["specification_id"] == spec_id
    assert entry["gene"] == gene
    assert entry["status"] == "Released"
    assert entry["version"] == "2.1"
    assert entry["vcep"] == "Synthetic VCEP"
    binding = entry["rule_sets"][0]["genes"][0]["diseases"][0]
    assert entry["rule_sets"][0]["genes"][0]["symbol"] == gene
    assert binding["mondo_id"] == disease_mondo
    assert binding["inheritance"] == [inheritance]
    # A matched success case must carry fully parsed detail material:
    # non-empty criteria, no gaps, no failure flags, no partial failures,
    # and the assertion-method URL present. (Not a fixed count: the
    # helper's valid criteria set is enough -- no 28-entry hard constraint.)
    assert entry["criterion_modifications"], "criteria must not be empty"
    assert entry["missing_materials"] == []
    assert entry.get("detail_fetch_failed") is not True
    assert entry.get("detail_structure_failed") is not True
    assert not result.get("partial_failures")
    assert entry["assertion_method_url"]
    # No candidates: a clean match plus no unbound specs must not invent
    # unresolved-scope entries.
    assert result["unresolved_scope_specs"] == []
    # Request discipline: the index plus exactly the matched detail URL --
    # synthetic bindings go out, nothing else is fetched.
    assert requested == [
        "https://cspec.genome.network/cspec/api/svis",
        f"https://cspec.genome.network/cspec/api/"
        f"SequenceVariantInterpretation/id/{spec_id}",
    ]


@pytest.mark.parametrize(
    "gene, disease_mondo, disease_label, inheritance, spec_id",
    _SYNTHETIC_GENE_CASES,
    ids=[case[0] for case in _SYNTHETIC_GENE_CASES],
)
def test_cspec_gene_centric_mainline_no_match_is_generic_guidance(
    monkeypatch, gene, disease_mondo, disease_label, inheritance, spec_id
):
    # Query a gene the synthetic index does not carry: a valid empty match
    # is success with generic-rules guidance -- never an error, and never
    # reported as "no specification" when scope candidates exist.
    record = _index_record(
        spec_id=spec_id,
        gene=gene,
        disease_label=disease_label,
        inheritance=inheritance,
    )
    requested = _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": gene + "X"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["total"] == 0
    assert result["unresolved_scope_specs"] == []
    assert "No Released" in result["note"]
    assert "generic" in result["note"]
    # No match -> no detail request: only the index URL was fetched.
    assert requested == [
        "https://cspec.genome.network/cspec/api/svis",
    ]


def test_cspec_gene_unbound_synthetic_spec_coexists_with_exact_match(
    monkeypatch,
):
    # General (non-mitochondrial) form of the unbound-index-entry case: a
    # synthetic TSC2 spec whose index record lists no genes is an
    # unresolved-scope candidate -- kept alongside the explicit match,
    # neither dropped as a duplicate nor counted as a match. The API not
    # listing genes says nothing about applicability. The BOUND spec gets
    # a matching detail (GNTST005 / rule-set 992 / TSC2) so its entry is
    # a complete success; the candidate must NOT have its detail pulled.
    unbound = _index_record(
        spec_id="GNTST099",
        gene="TSC2",
        rule_set_id="991",
    )
    del unbound["ruleSets"][0]["genes"]
    bound = _index_record(
        spec_id="GNTST005",
        gene="TSC2",
        disease_label="MONDO:0001734",
        rule_set_id="992",
    )
    bound_detail = _detail_payload(spec_id="GNTST005", rule_set_id="992")
    bound_detail["label"] = "Synthetic TSC2 specification Version 2.1"
    bound_detail["ruleSets"][0]["genes"] = [
        {"@type": "Gene", "label": "TSC2"}
    ]
    requested = _patch(
        monkeypatch,
        _index(bound, unbound),
        detail_payloads={"GNTST005": bound_detail},
    )

    result = _tool().run({"gene": "TSC2"})

    assert result["status"] == "success"
    assert [e["specification_id"] for e in result["data"]] == ["GNTST005"]
    assert result["total"] == 1  # candidates never count as matches
    # The explicit match is complete: criteria parsed, no gaps, no flags.
    entry = result["data"][0]
    assert entry["criterion_modifications"], "criteria must not be empty"
    assert entry["missing_materials"] == []
    assert entry.get("detail_fetch_failed") is not True
    assert entry.get("detail_structure_failed") is not True
    assert not result.get("partial_failures")
    assert entry["assertion_method_url"]
    candidates = result["unresolved_scope_specs"]
    assert [c["specification_id"] for c in candidates] == ["GNTST099"]
    assert candidates[0]["scope_reason"] == "gene_binding_unavailable"
    assert candidates[0]["rule_set_ids"] == ["991"]
    # Request discipline: index + the BOUND spec's detail only -- the
    # candidate's detail URL is never fetched.
    assert requested == [
        "https://cspec.genome.network/cspec/api/svis",
        "https://cspec.genome.network/cspec/api/"
        "SequenceVariantInterpretation/id/GNTST005",
    ]
    # The note must keep the response honest: unresolved, no premature
    # "classify under generic" directive.
    assert "unresolved" in result["note"]
    assert "classify under" not in result["note"]


# --------------------------------------------------------------------------- #
# 2026-11-21: scope-based pre-filtering of the one index-verified mtDNA-only
# unbound candidate. Live facts frozen above: GN015 version 1.0's only rule
# set 135641398 carries no gene binding in the index, and the official page
# limits the specification to mitochondrial DNA genes. Applicability is now
# decided BEFORE candidates are generated, by exact local membership in the
# 37 HGNC standard symbols of the genes encoded by the human mitochondrial
# reference genome (rCRS, NC_012920.1): 13 protein-coding + 22 tRNA + 2
# rRNA genes (verified live against HGNC 2026-11-20: 56 Approved MT-
# prefixed symbols carry location "mitochondria", exactly 37 of which have
# a gene locus_type -- the other 19 are regulatory regions / lncRNA). A
# gene on that list still discovers GN015 as a candidate (its specific
# applicability is still adjudicated from the official materials); a gene
# outside it -- including nuclear-encoded mitochondrial-disease genes such
# as POLG -- never sees GN015 in results, candidates or notes. No registry
# lookup happens at search time: the previous per-query HGNC verification,
# its numFound discipline and the scope_exclusions output are gone. New
# versions and other unverified rule sets in the same document keep the
# candidate-verification flow untouched.
# --------------------------------------------------------------------------- #
_FROZEN_NUCLEAR_RECEIPTS = [
    # (gene, spec_id, version, rule_set_id, disease) — spec ids, versions,
    # rule-set ids and disease bindings are live registry facts
    # (fetched 2026-11-20). None of these genes may see GN015.
    ("MYOC", "GN019", "2.1", "635003681", "MONDO:0005338"),
    ("LDLR", "GN013", "1.2", "135640393", "MONDO:0007750"),
    ("BRCA1", "GN092", "1.2", "1530970800", "MONDO:0700268"),
    ("POLG", "GN014", "1.0", "135641175", "MONDO:0044970"),
]


@pytest.mark.parametrize(
    "gene,spec_id,version,rule_set_id,disease",
    _FROZEN_NUCLEAR_RECEIPTS,
    ids=[case[0] for case in _FROZEN_NUCLEAR_RECEIPTS],
)
def test_mtdna_scope_prefiltered_for_nuclear_gene(
    monkeypatch, gene, spec_id, version, rule_set_id, disease
):
    # A nuclear gene (including POLG, which causes mitochondrial disease
    # but is nuclear-encoded at 15q26.1) keeps its explicitly matched
    # specification and never sees GN015 -- not as a match, not as an
    # unresolved candidate, not in the note -- with zero registry lookups.
    match = _index_record(
        spec_id=spec_id,
        gene=gene,
        disease_label=disease,
        inheritance="Autosomal dominant inheritance",
        rule_set_id=rule_set_id,
        version=version,
    )
    detail = _detail_payload(spec_id=spec_id, rule_set_id=rule_set_id)
    detail["version"] = version
    requested = _patch(
        monkeypatch,
        _index(match, _gn015_record()),
        detail_payloads={spec_id: detail},
    )

    result = _tool().run({"gene": gene})

    assert result["status"] == "success"
    assert [entry["specification_id"] for entry in result["data"]] == [spec_id]
    assert result["data"][0]["gene"] == gene
    assert result["data"][0]["rule_sets"][0]["genes"][0]["symbol"] == gene
    assert result["unresolved_scope_specs"] == []
    assert "scope_exclusions" not in result
    assert "GN015" not in result["note"]
    assert "mtDNA" not in result["note"]
    # Request discipline: the index plus exactly the matched detail -- no
    # HGNC (or any other) registry request happens at search time.
    assert requested == [
        "https://cspec.genome.network/cspec/api/svis",
        f"https://cspec.genome.network/cspec/api/"
        f"SequenceVariantInterpretation/id/{spec_id}",
    ]


def test_nuclear_gene_with_no_spec_reaches_generic_rules_branch(monkeypatch):
    # TSC2 has no Released specification in the live registry (verified
    # 2026-11-20: no record binds TSC2). With GN015 scope-filtered out and
    # no match, the valid-empty note -- the generic-rules branch -- is the
    # honest outcome of a successful index lookup.
    requested = _patch(monkeypatch, _index(_gn015_record()))

    result = _tool().run({"gene": "TSC2"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["total"] == 0
    assert result["unresolved_scope_specs"] == []
    assert "scope_exclusions" not in result
    assert "No Released" in result["note"]
    assert "generic" in result["note"]
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]


@pytest.mark.parametrize(
    "gene,gene_class",
    [
        ("MT-ND1", "protein-coding"),
        ("MT-TL1", "trna"),
        ("MT-RNR1", "rrna"),
    ],
    ids=["MT-ND1", "MT-TL1", "MT-RNR1"],
)
def test_mt_encoded_gene_discovers_gn015(monkeypatch, gene, gene_class):
    # All three classes of mitochondrially encoded genes (protein-coding,
    # tRNA, rRNA) are inside the rCRS scope, so GN015 remains discoverable
    # as an unresolved candidate with its rule set intact -- still requiring
    # official-material adjudication, never auto-applied.
    del gene_class
    requested = _patch(monkeypatch, _index(_gn015_record()))

    result = _tool().run({"gene": gene})

    assert result["status"] == "success"
    assert result["data"] == []
    candidates = result["unresolved_scope_specs"]
    assert [c["specification_id"] for c in candidates] == ["GN015"]
    assert candidates[0]["rule_set_ids"] == ["135641398"]
    assert candidates[0]["scope_reason"] == "gene_binding_unavailable"
    assert "scope_exclusions" not in result
    assert "unresolved" in result["note"]
    assert "classify under" not in result["note"]
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]


def test_mtdna_scope_gate_is_exact_symbol_match(monkeypatch):
    # The gate is an exact match against the 37 rCRS symbols (the tool
    # uppercases the query): "mt-nd1" discovers GN015; "MTND1" -- a real
    # nuclear gene symbol shape but NOT one of the 37 -- does not.
    requested = _patch(
        monkeypatch, _index(_gn015_record(), _gn015_record())
    )

    result = _tool().run({"gene": "mt-nd1"})
    assert [c["specification_id"] for c in result["unresolved_scope_specs"]] == [
        "GN015", "GN015"
    ]

    result = _tool().run({"gene": "MTND1"})
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["unresolved_scope_specs"] == []
    assert "scope_exclusions" not in result
    assert requested == [
        "https://cspec.genome.network/cspec/api/svis",
        "https://cspec.genome.network/cspec/api/svis",
    ]


def _gn015_detail():
    """GN015 detail fixture consistent with the pinned index record: id,
    version "1.0" and rule set 135641398 all match the frozen shape."""
    detail = _detail_payload(spec_id="GN015", rule_set_id="135641398")
    detail["version"] = "1.0"
    return detail


def _conflicting_gn015_record():
    """Synthetic index damage: MYOC -- nuclear, outside the verified 37-symbol
    rCRS scope -- explicitly bound inside GN015 v1.0's rule set 135641398,
    contradicting the specification's official applicability."""
    record = _gn015_record()
    record["ruleSets"][0]["genes"] = _index_record(gene="MYOC")["ruleSets"][0][
        "genes"
    ]
    return record


@pytest.mark.parametrize(
    "conflict_position",
    [None, 0, 1],
    ids=["conflict-only", "valid-gn019-first", "valid-gn019-last"],
)
def test_cspec_pinned_scope_conflict_is_index_error(
    monkeypatch, conflict_position
):
    # An index that explicitly binds the queried gene to the verified
    # mtDNA-only rule set contradicts the specification's official scope:
    # that is index damage, decided BEFORE any detail request -- even when
    # a legitimate GN019 match sits in the same index -- and reported as
    # the bare error envelope, never as a valid hit or a valid empty.
    conflict = _conflicting_gn015_record()
    if conflict_position is None:
        records = [conflict]
    elif conflict_position == 1:
        records = [_index_record(), conflict]
    else:
        records = [conflict, _index_record()]
    requested = _patch(
        monkeypatch,
        _index(*records),
        detail_payloads={"GN015": _gn015_detail(), "GN019": _detail_payload()},
    )

    result = _tool().run({"gene": " myoc "})

    expected_position = 0 if conflict_position in (None, 0) else 1
    where = (
        f"index data[{expected_position}].ruleSets[0].genes[0]"
    )
    assert result["status"] == "error"
    assert set(result.keys()) == {"status", "error"}
    assert where in result["error"]
    for token in ("MYOC", "GN015", "1.0", "135641398", "mtDNA"):
        assert token in result["error"]
    # Fails before ANY detail fetch despite the legitimate GN019 match.
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]


def test_scope_conflict_is_scoped_to_the_queried_gene(monkeypatch):
    # The same index carrying the MYOC<->GN015 contradiction does not
    # affect a query for another gene: LDLR still returns GN013 normally.
    gn013 = _index_record(
        spec_id="GN013",
        gene="LDLR",
        disease_label="MONDO:0007750",
        rule_set_id="135640393",
        version="1.2",
    )
    gn013_detail = _detail_payload(spec_id="GN013", rule_set_id="135640393")
    gn013_detail["version"] = "1.2"
    requested = _patch(
        monkeypatch,
        _index(_conflicting_gn015_record(), gn013),
        detail_payloads={"GN013": gn013_detail},
    )

    result = _tool().run({"gene": "LDLR"})

    assert result["status"] == "success"
    assert [entry["specification_id"] for entry in result["data"]] == ["GN013"]
    assert requested == [
        "https://cspec.genome.network/cspec/api/svis",
        "https://cspec.genome.network/cspec/api/"
        "SequenceVariantInterpretation/id/GN013",
    ]


def test_scope_conflict_ignores_foreign_binding_for_mt_gene(monkeypatch):
    # A wrong MYOC binding inside the verified rule set does not poison it
    # for an in-scope gene: querying MT-ND1 keeps GN015's 135641398 as an
    # explicit match, and the returned rule set binds only MT-ND1.
    record = _gn015_record()
    record["ruleSets"][0]["genes"] = [
        _index_record(gene="MYOC")["ruleSets"][0]["genes"][0],
        _index_record(gene="MT-ND1")["ruleSets"][0]["genes"][0],
    ]
    requested = _patch(
        monkeypatch,
        _index(record),
        detail_payloads={"GN015": _gn015_detail()},
    )

    result = _tool().run({"gene": "MT-ND1"})

    assert result["status"] == "success"
    assert [entry["specification_id"] for entry in result["data"]] == ["GN015"]
    rule_set = result["data"][0]["rule_sets"][0]
    assert rule_set["rule_set_id"] == "135641398"
    assert [bound["symbol"] for bound in rule_set["genes"]] == ["MT-ND1"]
    assert requested == [
        "https://cspec.genome.network/cspec/api/svis",
        "https://cspec.genome.network/cspec/api/"
        "SequenceVariantInterpretation/id/GN015",
    ]


def test_mtdna_reference_set_is_the_37_rcrs_gene_symbols():
    # Frozen live receipt (HGNC, verified 2026-11-20): the genes encoded by
    # the human mitochondrial reference genome carry exactly these 37 HGNC
    # Approved symbols (13 protein-coding, 22 tRNA, 2 rRNA). The other 19
    # Approved mitochondrially-located MT- symbols are regulatory regions
    # or lncRNA, not reference-genome genes, and are deliberately absent.
    from tooluniverse.clingen_tool import _MTDNA_REFERENCE_GENOME_GENES

    expected = {
        # 13 protein-coding
        "MT-ATP6", "MT-ATP8", "MT-CO1", "MT-CO2", "MT-CO3", "MT-CYB",
        "MT-ND1", "MT-ND2", "MT-ND3", "MT-ND4", "MT-ND4L", "MT-ND5",
        "MT-ND6",
        # 2 rRNA
        "MT-RNR1", "MT-RNR2",
        # 22 tRNA
        "MT-TA", "MT-TC", "MT-TD", "MT-TE", "MT-TF", "MT-TG", "MT-TH",
        "MT-TI", "MT-TK", "MT-TL1", "MT-TL2", "MT-TM", "MT-TN", "MT-TP",
        "MT-TQ", "MT-TR", "MT-TS1", "MT-TS2", "MT-TT", "MT-TV", "MT-TW",
        "MT-TY",
    }
    assert _MTDNA_REFERENCE_GENOME_GENES == expected
    assert len(_MTDNA_REFERENCE_GENOME_GENES) == 37


def test_new_gn015_version_stays_candidate_without_registry_query(monkeypatch):
    # The mtDNA-only verification is pinned to index version 1.0; a new
    # version is unverified and must go through candidate verification --
    # with no registry lookup spent on it.
    requested = _patch(monkeypatch, _index(_gn015_record(version="2.0")))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert [c["specification_id"] for c in result["unresolved_scope_specs"]] == [
        "GN015"
    ]
    assert "scope_exclusions" not in result
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]


def test_unverified_rule_set_stays_candidate_without_registry_query(monkeypatch):
    requested = _patch(
        monkeypatch, _index(_gn015_record(rule_set_ids=("999999",)))
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert [c["specification_id"] for c in result["unresolved_scope_specs"]] == [
        "GN015"
    ]
    assert "scope_exclusions" not in result
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]


def test_scope_gate_removes_only_the_pinned_rule_set(monkeypatch):
    # If other unresolved rule sets shared the record, only 135641398 is
    # scoped out for a non-rCRS gene; the candidate survives carrying the
    # remaining ids for the original candidate verification.
    requested = _patch(
        monkeypatch, _index(_gn015_record(rule_set_ids=("135641398", "777")))
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    candidates = result["unresolved_scope_specs"]
    assert [c["specification_id"] for c in candidates] == ["GN015"]
    assert candidates[0]["rule_set_ids"] == ["777"]
    assert "scope_exclusions" not in result
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]


def test_duplicate_gn015_records_absent_for_nuclear_gene(monkeypatch):
    # A (hypothetically) duplicated index record must not leak GN015 into
    # a nuclear gene's output; each copy is scoped out independently.
    requested = _patch(
        monkeypatch, _index(_gn015_record(), _gn015_record())
    )

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert result["unresolved_scope_specs"] == []
    assert "scope_exclusions" not in result
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]


def test_label_derived_version_does_not_gate_scope(monkeypatch):
    # The pin is the index's explicit `version` field ("1.0"), not a
    # version inferred from prose in `label` -- inference from prose is
    # thinner evidence than the verified index fact.
    record = _gn015_record()
    del record["version"]
    record["label"] = "Mitochondrial specification Version 1.0"
    requested = _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert [c["specification_id"] for c in result["unresolved_scope_specs"]] == [
        "GN015"
    ]
    assert "scope_exclusions" not in result
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]


def test_gn015_empty_rulesets_keeps_candidate(monkeypatch):
    # An empty ruleSets record carries no rule set id, so the pinned
    # (GN015, "1.0", 135641398) fact cannot apply: the record keeps the
    # generic candidate flow for any gene.
    record = _gn015_record()
    record["ruleSets"] = []
    requested = _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    candidates = result["unresolved_scope_specs"]
    assert [c["specification_id"] for c in candidates] == ["GN015"]
    assert candidates[0]["rule_set_ids"] == []
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]


def test_numeric_index_version_stays_candidate(monkeypatch):
    # A JSON number 1.0 is not the string "1.0" the pin was verified
    # against; coercion through str() would smuggle it in.
    record = _gn015_record()
    record["version"] = 1.0  # float, not string
    requested = _patch(monkeypatch, _index(record))

    result = _tool().run({"gene": "MYOC"})

    assert result["status"] == "success"
    assert [c["specification_id"] for c in result["unresolved_scope_specs"]] == [
        "GN015"
    ]
    assert "scope_exclusions" not in result
    assert requested == ["https://cspec.genome.network/cspec/api/svis"]
