"""ACMG adapter coverage for OMIM disease context."""

from tooluniverse.acmg.collector import ACMGEvidencePipeline
from tooluniverse.acmg.source_adapters import adapt_source_output


def test_omim_rows_are_normalized_as_disease_context_only():
    result = adapt_source_output(
        "MARRVEL_get_omim_phenotypes",
        {
            "status": "success",
            "data": [
                {
                    "mimNumber": 602421,
                    "phenotype": "Cystic fibrosis",
                    "phenotypeMimNumber": 219700,
                    "phenotypeInheritance": "Autosomal recessive",
                }
            ],
            "url": "http://api.marrvel.org/data/omim/gene/symbol/CFTR",
        },
    )
    assert result["source_category"] == "disease_context"
    features = result["reviewable_features"]
    assert features["omim_associations"][0]["phenotype_mim"] == 219700
    assert features["omim_associations"][0]["inheritance_enum"] == "AR"
    assert result["quarantined_conclusions"] == {}


def test_omim_context_is_auditable_and_not_an_evidence_card():
    context = ACMGEvidencePipeline._omim_context({}, "CFTR")
    assert context["status"] == "not_queried"
    assert context["review_only"] is True
    assert context["associations"] == []
