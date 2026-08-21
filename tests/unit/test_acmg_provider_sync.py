"""Offline regressions for the ACMG-relevant upstream provider fixes."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from tooluniverse.clingen_tool import ClinGenTool
from tooluniverse.clinvar_tool import (
    ClinVarGetClinicalSignificance,
    ClinVarGetVariantDetails,
    ClinVarSearchVariants,
)
from tooluniverse.ebi_proteins_interactions_tool import (
    EBIProteinsInteractionsTool,
)
from tooluniverse.hpo_tool import HPOTool
from tooluniverse.mygene_tool import MyVariantTool
from tooluniverse.uniprot_tool import UniProtRESTTool

pytestmark = pytest.mark.unit


def _response(payload, *, text: str = "", url: str = "https://example.test"):
    response = Mock()
    response.status_code = 200
    response.json.return_value = payload
    response.text = text
    response.url = url
    response.raise_for_status.return_value = None
    return response


def test_myvariant_uses_per_tool_declared_fields_and_explicit_override():
    declared = "dbnsfp.revel.score,dbnsfp.alphamissense.score"
    tool = MyVariantTool(
        {
            "fields": {"operation": "get_variant"},
            "parameter": {
                "properties": {"fields": {"default": declared}},
            },
        }
    )
    with patch(
        "tooluniverse.mygene_tool.requests.get",
        return_value=_response({"_id": "chr1:g.1A>G"}),
    ) as request:
        tool.run({"variant_id": "chr1:g.1A>G"})
        assert request.call_args.kwargs["params"]["fields"] == declared
        tool.run({"variant_id": "chr1:g.1A>G", "fields": "dbsnp"})
        assert request.call_args.kwargs["params"]["fields"] == "dbsnp"


def _clinvar_tool() -> ClinVarSearchVariants:
    return ClinVarSearchVariants({"fields": {"endpoint": "/esearch.fcgi"}})


def test_clinvar_variant_name_preserves_exact_transcript_hgvs():
    tool = _clinvar_tool()
    with patch.object(
        tool,
        "_make_request",
        return_value={
            "status": "success",
            "data": {"esearchresult": {"count": "0", "idlist": []}},
        },
    ) as request:
        tool.run(
            {
                "gene": "HBB",
                "variant_name": [
                    "NM_000518.5:c.20A>T",
                    "NP_000509.1:p.Glu7Val",
                ],
            }
        )
    term = request.call_args_list[0].args[1]["term"]
    assert "HBB[gene]" in term
    assert '"NM_000518.5:c.20A>T"[Variant name]' in term
    assert '"NP_000509.1:p.Glu7Val"[Variant name]' in term


def test_clingen_flattens_current_erepo_evidence_codes():
    row = {
        "caid": "CAR:CA114360",
        "variationId": "586",
        "hgvs": ["NM_000277.2:c.1A>G"],
        "gene": {"label": "PAH"},
        "condition": {"label": "PKU", "@id": "MONDO:0009861"},
        "guidelines": [
            {
                "outcome": {"label": "Pathogenic"},
                "agents": [
                    {
                        "affiliation": "PAH VCEP",
                        "evidenceCodes": [
                            {"label": "PM2", "status": "Met", "@id": "pm2"},
                            {
                                "label": "PP4_Moderate",
                                "status": "Met",
                                "@id": "pp4",
                            },
                            {"label": "PVS1", "status": "Not Met", "@id": "pvs1"},
                        ],
                    }
                ],
            }
        ],
    }

    flattened = ClinGenTool._flatten_classification(row)
    assert flattened["Applied Criteria"] == [
        {
            "criterion": "PM2",
            "strength": "",
            "status": "Met",
            "evidenceSummary": None,
            "pmids": [],
            "source_id": "pm2",
            "source_label": "PM2",
        },
        {
            "criterion": "PP4",
            "strength": "Moderate",
            "status": "Met",
            "evidenceSummary": None,
            "pmids": [],
            "source_id": "pp4",
            "source_label": "PP4_Moderate",
        },
        {
            "criterion": "PVS1",
            "strength": "",
            "status": "Not Met",
            "evidenceSummary": None,
            "pmids": [],
            "source_id": "pvs1",
            "source_label": "PVS1",
        },
    ]


def test_clinvar_preserves_official_hyphen_and_falls_back_only_on_zero_hits():
    tool = _clinvar_tool()
    with patch.object(
        tool,
        "_make_request",
        return_value={
            "status": "success",
            "data": {"esearchresult": {"count": "1", "idlist": []}},
        },
    ) as request:
        tool.run({"gene": "HLA-B"})
    assert request.call_count == 1
    assert request.call_args.args[1]["term"] == "HLA-B[gene]"

    responses = [
        {
            "status": "success",
            "data": {"esearchresult": {"count": "0", "idlist": []}},
        },
        {
            "status": "success",
            "data": {"esearchresult": {"count": "1", "idlist": []}},
        },
    ]
    with patch.object(tool, "_make_request", side_effect=responses) as request:
        tool.run({"gene": "BRCA-2"})
    assert request.call_args_list[0].args[1]["term"] == "BRCA-2[gene]"
    assert request.call_args_list[1].args[1]["term"] == "BRCA2[gene]"


def test_clinvar_deprecated_symbol_and_clinsig_queries():
    tool = _clinvar_tool()
    responses = [
        {
            "status": "success",
            "data": {"esearchresult": {"count": "0", "idlist": []}},
        },
        {
            "status": "success",
            "data": {"esearchresult": {"count": "1", "idlist": []}},
        },
    ]
    with (
        patch.object(tool, "_make_request", side_effect=responses) as request,
        patch.object(tool, "_resolve_deprecated_gene_symbol", return_value="GBA1"),
    ):
        tool.run({"gene": "GBA"})
    assert request.call_args_list[1].args[1]["term"] == "GBA1[gene]"

    with patch.object(
        tool,
        "_make_request",
        return_value={
            "status": "success",
            "data": {"esearchresult": {"count": "0", "idlist": []}},
        },
    ) as request:
        tool.run({"clinical_significance": "Uncertain significance"})
    assert "clinsig_vus[prop]" in request.call_args.args[1]["term"]

    with patch.object(
        tool,
        "_make_request",
        return_value={
            "status": "success",
            "data": {"esearchresult": {"count": "0", "idlist": []}},
        },
    ) as request:
        result = tool.run(
            {"clinical_significance": "Pathogenic/Likely pathogenic"}
        )
    assert " OR " in request.call_args.args[1]["term"]
    assert "clinical_significance_note" in result["data"]


def test_clinvar_details_and_significance_use_only_canonical_data_envelope():
    variant_data = {
        "accession": "VCV000000001",
        "obj_type": "single nucleotide variant",
        "chr_sort": "1",
        "genes": [{"symbol": "GENE1"}],
        "variation_set": [
            {
                "variation_name": "NM_000001.1:c.1A>G",
                "variation_loc": [{"band": "1p36"}],
            }
        ],
        "germline_classification": {
            "description": "Uncertain significance",
            "review_status": "criteria provided",
            "trait_set": [{"trait_name": "Example disorder"}],
        },
    }
    def fetch():
        return {
            "variant_data": variant_data,
            "result": {"status": "success", "url": "https://example.test"},
        }

    details = ClinVarGetVariantDetails({})
    significance = ClinVarGetClinicalSignificance({})
    with patch.object(
        details,
        "_fetch_variant",
        side_effect=lambda _: fetch(),
    ):
        details_result = details.run({"variant_id": "1"})
    with patch.object(
        significance,
        "_fetch_variant",
        side_effect=lambda _: fetch(),
    ):
        significance_result = significance.run({"variant_id": "1"})

    for result in (details_result, significance_result):
        assert "formatted_data" not in result
        assert result["data"]["raw_data"] == variant_data
    assert details_result["data"]["genes"] == ["GENE1"]
    assert (
        significance_result["data"]["germline_classification"]["description"]
        == "Uncertain significance"
    )


def test_clingen_gene_validity_uses_exact_symbol_match():
    csv_text = (
        "GENE SYMBOL,DISEASE LABEL,CLASSIFICATION\n"
        "OTC,ornithine transcarbamylase deficiency,Definitive\n"
        "NOTCH1,NOTCH1 disorder,Definitive\n"
        "NOTCH2,NOTCH2 disorder,Definitive\n"
    )
    tool = ClinGenTool({"fields": {"operation": "search_gene_validity"}})
    with patch(
        "tooluniverse.clingen_tool.requests.get",
        return_value=_response({}, text=csv_text),
    ):
        result = tool.run({"gene": "OTC"})
    assert [row["GENE SYMBOL"] for row in result["data"]] == ["OTC"]

    dosage = ClinGenTool(
        {"fields": {"operation": "search_dosage_sensitivity"}}
    )
    with patch(
        "tooluniverse.clingen_tool.requests.get",
        return_value=_response({}, text=csv_text),
    ):
        result = dosage.run({"gene": "OTC"})
    assert [row["GENE SYMBOL"] for row in result["data"]] == ["OTC"]


def test_clingen_actionability_parses_columnar_rows():
    tool = ClinGenTool({"fields": {"operation": "get_actionability_adult"}})
    payload = {
        "columns": ["geneOrVariant", "condition"],
        "rows": [["BRCA1,BRCA2", "Hereditary cancer"], ["LDLR", "FH"]],
    }
    with patch(
        "tooluniverse.clingen_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"gene": "BRCA1"})
    assert result["total"] == 1
    assert result["data"][0]["condition"] == "Hereditary cancer"


def test_clingen_variant_classification_is_server_filtered():
    tool = ClinGenTool({"fields": {"operation": "get_variant_classifications"}})
    payload = {
        "variantInterpretations": [
            {
                "caid": "CA123",
                "variationId": 123,
                "hgvs": ["NM_000277.2:c.1A>G"],
                "gene": {"label": "PAH"},
                "condition": {"label": "PKU", "@id": "MONDO:0009861"},
                "guidelines": [
                    {
                        "outcome": {"label": "Pathogenic"},
                        "agents": [{"affiliation": "PAH VCEP"}],
                    }
                ],
            }
        ]
    }
    with patch(
        "tooluniverse.clingen_tool.requests.get",
        return_value=_response(payload),
    ) as request:
        result = tool.run({"gene": "PAH"})
    assert request.call_args.args[0].endswith("/classifications")
    assert request.call_args.kwargs["params"] == {
        "gene": "PAH",
        "matchLimit": 5000,
    }
    assert result["data"][0]["HGNC Gene Symbol"] == "PAH"
    assert tool.run({})["status"] == "error"


@pytest.mark.parametrize("term_id", ["HP:0001250", "HP_0001250", "0001250"])
def test_hpo_normalizes_supported_identifier_forms(term_id):
    tool = HPOTool({"fields": {"endpoint": "get_term"}})
    with patch(
        "tooluniverse.hpo_tool.requests.get",
        return_value=_response({"id": "HP:0001250", "name": "Seizure"}),
    ) as request:
        result = tool.run({"term_id": term_id})
    assert request.call_args.args[0].endswith("/HP:0001250")
    assert result["metadata"]["term_id"] == "HP:0001250"


def test_hpo_search_uses_limit_and_reports_total_available():
    tool = HPOTool({"fields": {"endpoint": "search_terms"}})
    payload = {
        "terms": [{"id": f"HP:{index:07d}", "name": str(index)} for index in range(20)],
        "totalCount": 123,
    }
    with patch(
        "tooluniverse.hpo_tool.requests.get",
        return_value=_response(payload),
    ) as request:
        result = tool.run({"query": "seizure", "max_results": 12})
    assert request.call_args.kwargs["params"] == {"q": "seizure", "limit": 12}
    assert len(result["data"]) == 12
    assert result["metadata"]["total_available"] == 123


def test_uniprot_trembl_name_cofactor_and_inactive_reason():
    compact = UniProtRESTTool(
        {
            "parameter": {"properties": {"compact": {"default": True}}},
            "fields": {"endpoint": "https://example.test/{accession}"},
        }
    )
    payload = {
        "entryType": "UniProtKB unreviewed (TrEMBL)",
        "proteinDescription": {
            "submissionNames": [{"fullName": {"value": "Submitted protein"}}]
        },
        "comments": [
            {
                "commentType": "COFACTOR",
                "cofactors": [{"name": "Fe(2+)"}],
                "note": {"texts": [{"value": "Binds iron."}]},
            }
        ],
    }
    with patch(
        "tooluniverse.uniprot_tool.requests.get",
        return_value=_response(payload),
    ):
        result = compact.run({"accession": "Q53707"})
    assert result["data"]["protein_name"] == "Submitted protein"
    assert result["data"]["comments"][0]["texts"] == ["Fe(2+)", "Binds iron."]

    extracted = UniProtRESTTool(
        {
            "fields": {
                "endpoint": "https://example.test/{accession}",
                "extract_path": "sequence.value",
            }
        }
    )
    inactive = {
        "entryType": "Inactive",
        "inactiveReason": {"deletedReason": "DEMERGED"},
    }
    with patch(
        "tooluniverse.uniprot_tool.requests.get",
        return_value=_response(inactive),
    ):
        result = extracted.run({"accession": "Q9ZZZ9"})
    assert result["status"] == "error"
    assert "inactive" in result["error"].lower()
    assert result["inactive_reason"]["deletedReason"] == "DEMERGED"

    full = UniProtRESTTool(
        {"fields": {"endpoint": "https://example.test/{accession}"}}
    )
    with patch(
        "tooluniverse.uniprot_tool.requests.get",
        return_value=_response(inactive),
    ):
        result = full.run({"accession": "Q9ZZZ9", "compact": False})
    assert result["status"] == "error"
    assert result["inactive_reason"]["deletedReason"] == "DEMERGED"


def test_ebi_interactions_runtime_default_matches_schema():
    tool = EBIProteinsInteractionsTool(
        {"fields": {"endpoint": "interactions"}}
    )
    payload = [
        {
            "accession": "P04637",
            "interactions": [
                {
                    "accession1": "P04637",
                    "accession2": f"Q{index:05d}",
                    "experiments": index,
                }
                for index in range(60)
            ],
        }
    ]
    with patch(
        "tooluniverse.ebi_proteins_interactions_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"accession": "P04637"})
    assert len(result["data"]["interactions"]) == 50
