from tooluniverse.clingen_tool import ClinGenTool


class _Response:
    def __init__(self, payload, url="https://cspec.example/test"):
        self._payload = payload
        self.url = url

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_cspec_version_falls_back_to_released_title():
    assert ClinGenTool._cspec_version(
        {"title": "VHL AC MG Specifications Version 1.1.0"}
    ) == "1.1.0"


def test_cspec_search_returns_released_gene_specifications(monkeypatch):
    index = {
        "@context": "https://cspec.genome.network/cspec/api/context/svis",
        "data": [
            {
                "@id": "https://cspec.genome.network/cspec/api/SequenceVariantInterpretation/id/GN078",
                "affiliation": {
                    "@id": "https://cspec.genome.network/cspec/api/Organization/id/50099",
                    "@type": "Organization",
                    "label": "VHL Variant Curation Expert Panel",
                },
                "ruleSets": [
                    {
                        "@id": "https://cspec.genome.network/cspec/api/RuleSet/id/1",
                        "genes": [
                            {
                                "@type": "Gene",
                                "label": "VHL",
                                "diseases": [
                                    {
                                        "@id": "http://purl.obolibrary.org/obo/MONDO_0008667",
                                        "label": "MONDO:0008667",
                                        "modeOfInheritance": [
                                            {
                                                "@label": "Autosomal dominant inheritance",
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
                "status": "Released",
                "url": "https://cspec.genome.network/cspec/ui/svi/doc/GN078",
                "version": "1.1.0",
            },
            {
                "@id": "https://cspec.genome.network/cspec/api/SequenceVariantInterpretation/id/GNOLD",
                "status": "Retired",
                "ruleSets": [],
            },
        ],
    }
    detail = {
        "@id": "https://cspec.genome.network/cspec/api/SequenceVariantInterpretation/id/GN078",
        "label": "VHL Expert Panel Specifications Version 1.1.0",
        "version": "1.1.0",
        "ruleSets": [
            {
                "criteriaCodes": [
                    {
                        "@id": "https://cspec.genome.network/cspec/api/CriteriaCode/id/criterion-pm2",
                        "label": "PM2",
                        "description": "Absent from controls.",
                        "evidenceStrengths": [
                            {
                                "label": "Supporting",
                                "applicability": "Applicable",
                                "description": "Use PM2 at supporting strength.",
                            }
                        ],
                    }
                ]
            }
        ],
    }

    requested_urls = []

    def fake_get(url, **_kwargs):
        requested_urls.append(url)
        return _Response(detail if url.endswith("/GN078") else index, url)

    monkeypatch.setattr("tooluniverse.clingen_tool.requests.get", fake_get)
    tool = ClinGenTool(
        {"name": "ClinGen_search_cspec", "fields": {"operation": "search_cspec"}}
    )

    result = tool.run({"gene": "VHL"})

    assert result["status"] == "success"
    assert result["total"] == 1
    assert requested_urls[0].endswith("/cspec/api/svis")
    assert result["data"][0]["specification_id"] == "GN078"
    assert result["data"][0]["vcep"] == "VHL Variant Curation Expert Panel"
    assert result["data"][0]["diseases"][0]["mondo_id"] == "MONDO:0008667"
    assert result["data"][0]["diseases"][0]["inheritance"] == [
        "Autosomal dominant inheritance"
    ]
    assert result["data"][0]["criterion_modifications"][0]["criterion"] == "PM2"
    assert result["data"][0]["criterion_modifications"][0]["strengths"][0]["text"] == (
        "Use PM2 at supporting strength."
    )
