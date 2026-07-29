"""ACMG quarantine must remain scoped to the collector executor."""

from __future__ import annotations

from uuid import uuid4

from tooluniverse import ToolUniverse
from tooluniverse.acmg.policy import ACMGScopedExecutor
from tooluniverse.base_tool import BaseTool
from tooluniverse.acmg.source_adapters import adapt_source_output


class _ClinVarFixtureTool(BaseTool):
    calls = 0

    def run(self, arguments):
        type(self).calls += 1
        return {
            "status": "success",
            "classification": "Pathogenic",
            "variation_id": arguments["variant_id"],
        }


def _runtime() -> ToolUniverse:
    runtime = ToolUniverse(tool_files={}, keep_default_tools=False)
    runtime.register_custom_tool(
        _ClinVarFixtureTool,
        tool_config={
            "name": "ClinVar_get_clinical_significance",
            "type": "_ClinVarFixtureTool",
            "description": "fixture",
            "parameter": {
                "type": "object",
                "properties": {"variant_id": {"type": "string"}},
                "required": ["variant_id"],
            },
        },
        instantiate=True,
    )
    return runtime


def test_ordinary_provider_call_remains_raw():
    runtime = _runtime()
    call = {
        "name": "ClinVar_get_clinical_significance",
        "arguments": {"variant_id": "1"},
    }
    raw = runtime.run_one_function(call)
    assert raw["classification"] == "Pathogenic"
    runtime.close()


def test_scoped_executor_quarantines_single_provider_result():
    runtime = _runtime()
    sandboxed = ACMGScopedExecutor(runtime).call(
        "ClinVar_get_clinical_significance",
        {"variant_id": "2"},
    )
    assert sandboxed["source_lead_only"] is True
    assert sandboxed["source_lead_sandbox"]["quarantined_conclusions"] == {
        "classification": "Pathogenic"
    }
    runtime.close()


def test_cache_stores_raw_result_and_scoped_executor_quarantines_after_read():
    _ClinVarFixtureTool.calls = 0
    runtime = _runtime()
    call = {
        "name": "ClinVar_get_clinical_significance",
        "arguments": {"variant_id": f"policy-cache-{uuid4()}"},
    }
    sandboxed = ACMGScopedExecutor(runtime).call(
        call["name"],
        call["arguments"],
        use_cache=True,
    )
    raw = runtime.run_one_function(call, use_cache=True)
    assert sandboxed["source_lead_only"] is True
    assert raw["classification"] == "Pathogenic"
    assert _ClinVarFixtureTool.calls == 1
    runtime.close()


def test_generic_batch_is_raw_and_scoped_batch_is_quarantined():
    runtime = _runtime()
    calls = [
        {
            "name": "ClinVar_get_clinical_significance",
            "arguments": {"variant_id": "batch-1"},
        },
        {
            "name": "ClinVar_get_clinical_significance",
            "arguments": {"variant_id": "batch-2"},
        },
    ]

    raw = runtime.run_many_functions(calls)
    sandboxed = ACMGScopedExecutor(runtime).call_many(calls)

    assert all(row["source_lead_only"] is True for row in sandboxed)
    assert all(row["classification"] == "Pathogenic" for row in raw)
    runtime.close()


def test_nested_provider_payloads_expose_only_rule_input_fields():
    myvariant = adapt_source_output(
        "MyVariant_get_pathogenicity_scores",
        {
            "status": "success",
            "data": {"dbnsfp": {"revel": {"score": [0.81]}, "cadd": {"phred": 29.1}}},
        },
    )
    gnomad = adapt_source_output(
        "gnomad_get_variant",
        {
            "status": "success",
            "data": {"variant": {"variant_id": "1-1-A-G", "exome": {"ac": 0, "an": 1000, "af": 0.0}}},
        },
    )
    recoder = adapt_source_output(
        "EnsemblVEP_variant_recoder",
        {
            "status": "success",
            "data": [{"id": ["rs123"], "hgvsg": ["NC_000001.11:g.1A>G"], "hgvsc": ["NM_000001.1:c.1A>G"]}],
        },
    )
    clinvar_id = adapt_source_output(
        "VariantValidator_validate_variant",
        {
            "status": "success",
            "data": {"variant_id": "1-1-A-G", "variation_id": 12345},
        },
    )
    validated_variant = adapt_source_output(
        "VariantValidator_validate_variant",
        {
            "status": "success",
            "data": {
                "flag": "gene_variant",
                "metadata": {"variantvalidator_version": "fixture-v1"},
                "NM_000059.4:c.5946delT": {
                    "hgvs_transcript_variant": "NM_000059.4:c.5946delT",
                    "gene_symbol": "BRCA2",
                    "hgvs_predicted_protein_consequence": {"tlr": "p.Ser1982ArgfsTer22"},
                    "primary_assembly_loci": {
                        "grch38": {"vcf": "13-32316461-T-A"}
                    },
                },
            },
        },
    )
    protein_variant = adapt_source_output(
        "EnsemblVEP_annotate_hgvs",
        {
            "status": "success",
            "data": {
                "input": "BRCA2:p.Ser1982ArgfsTer22",
                "assembly_name": "GRCh38",
                "seq_region_name": "13",
                "start": 32316461,
                "allele_string": "T/A",
                "transcript_consequences": [
                    {
                        "gene_symbol": "BRCA2",
                        "transcript_id": "ENST00000380152.8",
                        "consequence_terms": ["frameshift_variant"],
                    }
                ],
            },
            "metadata": {"source": "Ensembl VEP", "api_version": "REST"},
        },
    )

    assert myvariant["reviewable_features"]["revel_score"] == 0.81
    assert myvariant["reviewable_features"]["cadd_phred"] == 29.1
    assert "provider_version" not in myvariant["reviewable_features"]
    assert myvariant["reviewable_features"]["predictor_audit"]["revel_score"] == 0.81
    assert gnomad["reviewable_features"]["an"] == 1000
    assert gnomad["reviewable_features"]["coverage_adequate"] is None
    assert recoder["reviewable_features"]["rsid"] == "rs123"
    assert recoder["reviewable_features"]["hgvs_c"] == "NM_000001.1:c.1A>G"
    assert clinvar_id["reviewable_features"]["variation_id"] == 12345
    assert validated_variant["reviewable_features"]["validated_hgvs_c"] == (
        "NM_000059.4:c.5946delT"
    )
    assert validated_variant["reviewable_features"]["gene"] == "BRCA2"
    assert validated_variant["reviewable_features"]["transcript"] == "NM_000059.4"
    assert validated_variant["reviewable_features"]["chr"] == "13"
    assert protein_variant["reviewable_features"]["gene"] == "BRCA2"
    assert protein_variant["reviewable_features"]["chr"] == "13"
    assert protein_variant["reviewable_features"]["pos"] == 32316461
    assert protein_variant["reviewable_features"]["ref"] == "T"
    assert protein_variant["reviewable_features"]["alt"] == "A"
    assert len(myvariant["source_provenance"]["raw_result_hash"]) == 64


def test_nested_classifier_conclusions_are_quarantined():
    result = adapt_source_output(
        "ClinGen_search_gene_validity",
        {
            "status": "success",
            "data": {
                "gene": "BRCA1",
                "classification": "Definitive",
                "clinical_significance": "Pathogenic",
            },
        },
    )
    features = result["reviewable_features"]
    assert features["data"] == {"gene": "BRCA1"}
    assert result["quarantined_conclusions"]["reviewable_features.data.classification"] == "Definitive"
    assert result["quarantined_conclusions"]["reviewable_features.data.clinical_significance"] == "Pathogenic"
