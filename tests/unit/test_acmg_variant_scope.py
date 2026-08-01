import pytest

from tooluniverse.acmg.collector import ACMGEvidencePipeline
from tooluniverse.acmg.identity import classify_variant_scope


class _NoProviderCalls:
    def run_one_function(self, *_args, **_kwargs):
        raise AssertionError("SV preflight must not call providers")

    def run_many_functions(self, *_args, **_kwargs):
        raise AssertionError("SV preflight must not call providers")


def test_build_alias_and_structural_variant_scope():
    scope = classify_variant_scope("hg19 chrX:32018026-32222964-DEL")

    assert scope == {
        "input_kind": "structural_variant",
        "span_bp": 204939,
        "normalized_genome_build": "GRCh37",
        "build_resolution_source": "embedded_alias",
        "collector_supported": False,
        "recommended_route": "tooluniverse-structural-variant-analysis",
        "input_error": "",
        "normalized_variant": "chrX:32018026-32222964-DEL",
    }


def test_refseq_accession_infers_build_and_interval_boundary():
    scope = classify_variant_scope("NC_000023.10:g.32018026_32222964del")
    assert scope["normalized_genome_build"] == "GRCh37"
    assert scope["build_resolution_source"] == "accession_inferred"
    assert scope["input_kind"] == "structural_variant"

    assert (
        classify_variant_scope("chr1:100-149", "GRCh38")["input_kind"]
        == "small_variant"
    )
    assert (
        classify_variant_scope("chr1:100-150", "GRCh38")["input_kind"]
        == "structural_variant"
    )


def test_coordinate_input_without_build_fails_closed():
    scope = classify_variant_scope("chr1:100:A:T")
    assert scope["collector_supported"] is False
    assert scope["input_error"] == "genome_build_required_for_coordinate_input"

    genomic_hgvs = classify_variant_scope("NC_000001.11:g.100A>T", "")
    assert genomic_hgvs["normalized_genome_build"] == "GRCh38"
    assert genomic_hgvs["build_resolution_source"] == "accession_inferred"


@pytest.mark.parametrize(
    "variant",
    [
        "chr1:100:A:<DEL>",
        "chr1:100:N:N]chr2:200]",
        "chr1:100-120-DUP",
        "chr1:100-120-INV",
        "chr1:100-120-CNV",
        "chr1:100-120-CPX",
        "arr[hg19] Xp21.2(32018026_32222964)x0",
    ],
)
def test_symbolic_and_copy_number_representations_route_to_sv(variant):
    scope = classify_variant_scope(variant, "GRCh37")
    assert scope["input_kind"] == "structural_variant"
    assert scope["collector_supported"] is False


def test_conflicting_accession_and_requested_build_fails_closed():
    scope = classify_variant_scope("NC_000023.10:g.100A>T", "GRCh38")
    assert scope["input_error"] == "genome_build_conflict"


def test_vcf_allele_length_obeys_50_bp_boundary():
    deletion_50 = classify_variant_scope(
        f"chr1:100:{'A' * 51}:A",
        "GRCh38",
    )
    insertion_51 = classify_variant_scope(
        f"chr1:100:A:{'A' * 52}",
        "GRCh38",
    )

    assert deletion_50["span_bp"] == 50
    assert deletion_50["input_kind"] == "small_variant"
    assert insertion_51["span_bp"] == 51
    assert insertion_51["input_kind"] == "structural_variant"


def test_sv_collector_preflight_returns_route_without_evidence():
    result = ACMGEvidencePipeline(_NoProviderCalls()).run(
        {"variant": "chrX:32018026-32222964-DEL", "genome_build": "hg19"}
    )

    assert result["status"] == "not_applicable"
    assert result["execution_status"] == "not_run"
    assert result["workflow_status"] == "unsupported_variant_class"
    assert result["variant_scope"]["normalized_genome_build"] == "GRCh37"
    assert result["evidence_cards"] == []
    assert result["criterion_reviews"] == []
    assert result["source_facts"] == []
    assert result["recoverable_gaps"] == []
    assert result["review_readiness"]["status"] == "not_applicable"
    assert result["review_readiness"]["system_preview_available"] is False
    assert (
        result["next_actions"][0]["skill_name"]
        == "tooluniverse-structural-variant-analysis"
    )
    assert result["final_classification_allowed"] is False


def test_coordinate_without_build_stops_before_providers():
    result = ACMGEvidencePipeline(_NoProviderCalls()).run(
        {"variant": "chrX:32018026-32222964-DEL"}
    )

    assert result["status"] == "error"
    assert result["workflow_status"] == "input_correction_required"
    assert result["error"] == "genome_build_required_for_coordinate_input"
    assert result["source_facts"] == []
    assert result["evidence_cards"] == []
    assert result["review_readiness"]["status"] == "blocked"
    assert result["review_readiness"]["system_preview_available"] is False
