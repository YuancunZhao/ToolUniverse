"""Provider contract tests for normalized ACMG SourceFacts."""

from __future__ import annotations

from tooluniverse.acmg.source_adapters import (
    adapt_source_output,
    prepare_spliceai_features,
    result_identity,
    source_fact_ready,
)


EXPECTED = {
    "coordinates": {"chr": "1", "pos": 10, "ref": "A", "alt": "G"},
    "build": "GRCh38",
}


def _gnomad(**overrides):
    features = {
        "variant_id": "1-10-A-G",
        "build": "GRCh38",
        "dataset": "gnomad_r4",
        "AC": 0,
        "AN": 1000,
        "AF": 0.0,
        "callset": "exome",
        "coverage_adequate": True,
    }
    features.update(overrides)
    return features


def test_gnomad_requires_complete_frequency_contract():
    assert source_fact_ready("gnomad_get_variant", _gnomad(), EXPECTED)[2] is True
    assert (
        source_fact_ready("gnomad_get_variant", _gnomad(callset=None), EXPECTED)[2]
        is False
    )
    assert (
        source_fact_ready("gnomad_get_variant", _gnomad(AF=None), EXPECTED)[2] is False
    )
    assert (
        source_fact_ready("gnomad_get_variant", _gnomad(dataset=None), EXPECTED)[2]
        is False
    )
    assert (
        source_fact_ready(
            "gnomad_get_variant", _gnomad(coverage_adequate="true"), EXPECTED
        )[2]
        is False
    )


def test_gnomad_build_mismatch_is_not_ready():
    observed, identity_verified, ready = source_fact_ready(
        "gnomad_get_variant", _gnomad(build="GRCh37"), EXPECTED
    )
    assert observed["build"] == "GRCh37"
    assert identity_verified is False
    assert ready is False


def test_myvariant_requires_revel_and_provider_version():
    complete = {
        "variant_id": "1-10-A-G",
        "build": "GRCh38",
        "revel_score": 0.8,
        "provider_version": "dbNSFP-4.5",
    }
    assert (
        source_fact_ready("MyVariant_get_pathogenicity_scores", complete, EXPECTED)[2]
        is True
    )
    assert (
        source_fact_ready(
            "MyVariant_get_pathogenicity_scores",
            {key: value for key, value in complete.items() if key != "build"},
            EXPECTED,
        )[2]
        is False
    )
    assert (
        source_fact_ready(
            "MyVariant_get_pathogenicity_scores",
            {**complete, "provider_version": None},
            EXPECTED,
        )[2]
        is False
    )


def test_myvariant_raw_identifier_binds_to_normalized_coordinates():
    complete = {
        "_id": "chr1:g.10A>G",
        "revel_score": 0.8,
        "provider_version": "MyVariant dbNSFP",
    }
    observed, identity_verified, ready = source_fact_ready(
        "MyVariant_get_pathogenicity_scores", complete, EXPECTED
    )
    assert observed["coordinates"] == EXPECTED["coordinates"]
    assert identity_verified is True
    assert ready is False


def test_callability_requires_matching_locus_build_dataset_and_row():
    complete = {
        "chrom": "1",
        "position": 10,
        "reference_genome": "GRCh38",
        "dataset": "gnomad_r4",
        "callsets": {"exome": {"position": 10, "median": 30}},
    }
    observed, identity_verified, ready = source_fact_ready(
        "gnomad_get_site_callability", complete, EXPECTED
    )
    assert observed["locus"] == {"chr": "1", "pos": 10}
    assert identity_verified is True
    assert ready is True
    assert (
        source_fact_ready(
            "gnomad_get_site_callability", {**complete, "position": 11}, EXPECTED
        )[2]
        is False
    )
    assert (
        source_fact_ready(
            "gnomad_get_site_callability",
            {**complete, "callsets": {"other": {"position": 10, "median": 30}}},
            EXPECTED,
        )[2]
        is False
    )
    assert (
        source_fact_ready(
            "MyVariant_get_pathogenicity_scores",
            {**complete, "provider_version": None, "dataset": "dbNSFP"},
            EXPECTED,
        )[2]
        is False
    )


def test_result_identity_preserves_numeric_clinvar_variation_id():
    identity = result_identity(
        {
            "variant_id": "1-10-A-G",
            "build": "GRCh38",
            "variation_id": 12345,
            "clinvar_variation_id": "12345",
        }
    )
    assert identity["variation_id"] == 12345
    assert identity["clinvar_variation_id"] == "12345"


def test_spliceai_real_score_shape_satisfies_verified_run_contract():
    row = {
        "gene": "GENE1",
        "transcript": "NM_000001.1",
        "DS_AG": 0.31,
        "DS_AL": 0.0,
        "DS_DG": 0.0,
        "DS_DL": 0.0,
        "DP_AG": 2,
        "DP_AL": 0,
        "DP_DG": 0,
        "DP_DL": 0,
    }
    features = {
        "variant_id": "1-10-A-G",
        "chr": "1",
        "pos": 10,
        "ref": "A",
        "alt": "G",
        "build": "GRCh38",
        "scores": [row],
        "run_metadata": {
            "model_version": "1.3.1",
            "annotation_version": "MANE fixture release",
            "score_mode": "raw",
        },
    }
    expected = {
        **EXPECTED,
        "gene": "GENE1",
        "transcript": "NM_000001.1",
        "normalization": {
            "transcript_selection": {"reference": "NM_000001.1", "mane_select": True}
        },
    }
    features = prepare_spliceai_features(
        features,
        expected,
        {"distance": 500, "mask": False},
    )

    observed, verified, ready = source_fact_ready(
        "SpliceAI_predict_splice", features, expected
    )

    assert observed["coordinates"] == EXPECTED["coordinates"]
    assert verified is True
    assert ready is True
    assert features["spliceai_profile"]["max_delta_channels"] == ["DS_AG"]
    assert features["spliceai_profile"]["max_delta_events"] == ["acceptor_gain"]

    required_metadata = (
        "model_version",
        "annotation_version",
        "score_mode",
        "distance",
        "mask",
        "transcript_set",
        "selected_transcript",
        "selected_gene",
        "selected_score_row",
    )
    for key in required_metadata:
        incomplete = dict(features)
        incomplete_metadata = dict(features["spliceai_run_metadata"])
        incomplete_metadata.pop(key)
        incomplete["spliceai_run_metadata"] = incomplete_metadata
        assert (
            source_fact_ready("SpliceAI_predict_splice", incomplete, expected)[2]
            is False
        )


def test_spliceai_live_lookup_row_schema_matches_via_g_name_and_refseq_ids():
    """Real SpliceAI Lookup rows use g_name/t_id/t_refseq_ids, not gene/transcript."""
    live_row = {
        "DS_AG": "0.00",
        "DS_AL": "0.00",
        "DS_DG": "0.00",
        "DS_DL": "0.05",
        "DP_AG": 99,
        "DP_AL": -86,
        "DP_DG": -160,
        "DP_DL": 40,
        "g_id": "ENSG00000141510.20",
        "g_name": "TP53",
        "t_id": "ENST00000269305.9",
        "t_priority": "MS",
        "t_refseq_ids": ["NM_000546.6"],
        "t_strand": "-",
        "t_type": "protein_coding",
    }
    features = {
        "variant_id": "17-7676154-G-C",
        "chr": "17",
        "pos": 7676154,
        "ref": "G",
        "alt": "C",
        "build": "GRCh38",
        "scores": [live_row],
        "run_metadata": {
            "model_version": "1.3.1",
            "annotation_version": "MANE fixture release",
            "score_mode": "raw",
        },
    }
    expected = {
        "coordinates": {"chr": "17", "pos": 7676154, "ref": "G", "alt": "C"},
        "build": "GRCh38",
        "gene": "TP53",
        "transcript": "NM_000546.6",
        "normalization": {
            "transcript_selection": {"reference": "NM_000546.6", "mane_select": True}
        },
    }
    prepared = prepare_spliceai_features(
        features,
        expected,
        {"distance": 500, "mask": False},
    )

    metadata = prepared["spliceai_run_metadata"]
    assert metadata["row_match_count"] == 1
    assert metadata["selected_score_row"]["g_name"] == "TP53"
    assert prepared["max_delta_score"] == 0.05
    assert prepared["spliceai_profile"]["delta_scores"]["DS_DL"] == 0.05

    observed, verified, ready = source_fact_ready(
        "SpliceAI_predict_splice", prepared, expected
    )
    assert observed["coordinates"] == expected["coordinates"]
    assert verified is True
    assert ready is True

    # The same row must also match when the identity transcript is Ensembl.
    expected_enst = {**expected, "transcript": "ENST00000269305.9"}
    prepared_enst = prepare_spliceai_features(
        features,
        expected_enst,
        {"distance": 500, "mask": False},
    )
    assert prepared_enst["spliceai_run_metadata"]["row_match_count"] == 1

    # A row for another gene must not match.
    other_gene = {
        "coordinates": {"chr": "17", "pos": 7676154, "ref": "G", "alt": "C"},
        "build": "GRCh38",
        "gene": "BRCA1",
        "transcript": "NM_007294.4",
        "normalization": {"transcript_selection": {"mane_select": True}},
    }
    prepared_other = prepare_spliceai_features(
        features,
        other_gene,
        {"distance": 500, "mask": False},
    )
    assert prepared_other["spliceai_run_metadata"]["row_match_count"] == 0
    assert prepared_other["spliceai_run_metadata"]["selected_score_row"] is None


def test_spliceai_provider_max_mismatch_and_missing_channel_fail_closed():
    row = {
        "gene": "GENE1",
        "transcript": "NM_000001.1",
        "DS_AG": 0.22,
        "DS_AL": 0.22,
        "DS_DG": 0.20,
        "DS_DL": 0.02,
        "DP_AG": 1,
        "DP_AL": -1,
        "DP_DG": 2,
        "DP_DL": -2,
    }
    expected = {
        **EXPECTED,
        "gene": "GENE1",
        "transcript": "NM_000001.1",
        "normalization": {"transcript_selection": {"mane_select": True}},
    }
    base = {
        "variant_id": "1-10-A-G",
        "build": "GRCh38",
        "scores": [row],
        "provider_max_delta_score": 0.9,
        "run_metadata": {
            "model_version": "1.3.1",
            "annotation_version": "MANE fixture release",
            "score_mode": "raw",
        },
    }
    conflicting = prepare_spliceai_features(
        base,
        expected,
        {"distance": 500, "mask": False},
    )
    incomplete = prepare_spliceai_features(
        {
            **base,
            "provider_max_delta_score": None,
            "scores": [{k: v for k, v in row.items() if k != "DS_DL"}],
        },
        expected,
        {"distance": 500, "mask": False},
    )

    profile = conflicting["spliceai_profile"]
    assert profile["status"] == "conflicting"
    assert profile["max_delta_channels"] == ["DS_AG", "DS_AL"]
    assert (
        source_fact_ready("SpliceAI_predict_splice", conflicting, expected)[2] is False
    )
    assert incomplete["spliceai_profile"]["status"] == "incomplete"
    assert (
        source_fact_ready("SpliceAI_predict_splice", incomplete, expected)[2] is False
    )


def test_spliceai_zero_or_ambiguous_selected_gene_rows_fail_closed():
    def row(gene, score):
        return {
            "gene": gene,
            "DS_AG": score,
            "DS_AL": 0.0,
            "DS_DG": 0.0,
            "DS_DL": 0.0,
            "DP_AG": 1,
            "DP_AL": 0,
            "DP_DG": 0,
            "DP_DL": 0,
        }

    expected = {
        **EXPECTED,
        "gene": "GENE1",
        "transcript": "NM_000001.1",
        "normalization": {"transcript_selection": {"mane_select": True}},
    }
    base = {
        "variant_id": "1-10-A-G",
        "build": "GRCh38",
        "run_metadata": {
            "model_version": "1.3.1",
            "annotation_version": "MANE fixture release",
            "score_mode": "raw",
        },
    }
    for rows, expected_count in (
        ([row("OTHER", 0.9)], 0),
        ([row("GENE1", 0.1), row("GENE1", 0.2)], 2),
    ):
        prepared = prepare_spliceai_features(
            {**base, "scores": rows},
            expected,
            {"distance": 500, "mask": False},
        )
        assert prepared["spliceai_run_metadata"]["row_match_count"] == expected_count
        assert (
            source_fact_ready("SpliceAI_predict_splice", prepared, expected)[2] is False
        )


def test_cspec_source_fact_is_bound_to_the_identity_verified_gene():
    observed, identity_verified, ready = source_fact_ready(
        "ClinGen_search_cspec",
        {
            "gene": "FGFR3",
            "provider": "ClinGen CSpec Registry",
            "request_url": "https://cspec.example/id",
            "data": [{"specification_id": "GN078"}],
        },
        {"gene": "FGFR3", "build": "GRCh38"},
    )

    assert observed == {"gene": "FGFR3"}
    assert identity_verified is True
    assert ready is True


def test_vep_recoder_preserves_multiple_alleles_without_first_result_selection():
    adapted = adapt_source_output(
        "EnsemblVEP_variant_recoder",
        [
            {
                "id": ["rs1"],
                "hgvsg": ["NC_000001.11:g.10A>G"],
                "hgvsc": ["NM_000001.1:c.1A>G"],
            },
            {
                "id": ["rs1"],
                "hgvsg": ["NC_000001.11:g.10A>T"],
                "hgvsc": ["NM_000001.1:c.1A>T"],
            },
        ],
    )
    features = adapted["reviewable_features"]

    assert "hgvs_g" not in features
    assert "hgvs_c" not in features
    assert len(features["allele_candidates"]) == 2
    assert features["hgvsg_candidates"] == [
        "NC_000001.11:g.10A>G",
        "NC_000001.11:g.10A>T",
    ]


def test_spliceai_adapter_preserves_rows_without_using_cross_gene_maximum():
    adapted = adapt_source_output(
        "SpliceAI_predict_splice",
        {
            "variant": "1-10-A-G",
            "genome": "38",
            "scores": [
                {
                    "gene": "GENE1",
                    "DS_AG": 0.1,
                    "DS_AL": 0.0,
                    "DS_DG": 0.0,
                    "DS_DL": 0.0,
                    "DP_AG": 2,
                },
                {
                    "gene": "OTHER",
                    "DS_AG": 0.0,
                    "DS_AL": 0.0,
                    "DS_DG": 0.7,
                    "DS_DL": 0.0,
                    "DP_DG": -3,
                },
            ],
        },
    )
    features = adapted["reviewable_features"]

    assert "max_delta_score" not in features
    assert features["scores"][1]["DP_DG"] == -3


def test_spliceai_row_binding_ignores_higher_unrelated_gene_score():
    def row(gene, score):
        return {
            "gene": gene,
            "DS_AG": score,
            "DS_AL": 0.0,
            "DS_DG": 0.0,
            "DS_DL": 0.0,
            "DP_AG": 1,
            "DP_AL": 0,
            "DP_DG": 0,
            "DP_DL": 0,
        }

    features = prepare_spliceai_features(
        {
            "scores": [row("GENE1", 0.1), row("OTHER", 0.9)],
            "run_metadata": {
                "model_version": "1.3.1",
                "annotation_version": "MANE fixture release",
                "score_mode": "raw",
            },
        },
        {
            "gene": "GENE1",
            "transcript": "NM_000001.1",
            "normalization": {"transcript_selection": {"mane_select": True}},
        },
        {"distance": 500, "mask": False},
    )

    assert features["max_delta_score"] == 0.1
    assert features["spliceai_run_metadata"]["row_match_count"] == 1


def test_ebi_protein_variation_adapter_preserves_mapping_identity():
    adapted = adapt_source_output(
        "EBIProteins_get_variation_by_hgvs",
        {
            "status": "success",
            "data": {
                "hgvs": "NC_000004.12:g.1804392G>A",
                "entries": [
                    {
                        "accession": "P22607",
                        "entry_name": "FGFR3_HUMAN",
                        "gene_name": "FGFR3",
                        "taxid": 9606,
                        "features": [
                            {
                                "type": "VARIANT",
                                "begin": 380,
                                "end": 380,
                                "wild_type": "G",
                                "alternative_sequence": "R",
                                "genomic_location": "4:1804392:G:A",
                            }
                        ],
                    }
                ],
            },
        },
    )
    features = adapted["reviewable_features"]
    observed, verified, ready = source_fact_ready(
        "EBIProteins_get_variation_by_hgvs",
        features,
        {"hgvs_g": "NC_000004.12:g.1804392G>A", "gene": "FGFR3"},
    )

    assert observed == {"hgvs_g": "NC_000004.12:g.1804392G>A"}
    assert verified is True
    assert ready is True
    assert features["protein_candidates"][0]["protein_accession"] == "P22607"
    assert features["protein_candidates"][0]["protein_position_start"] == 380


def test_protein_feature_and_interpro_adapters_do_not_invent_coordinates():
    feature_values = adapt_source_output(
        "EBIProteins_get_features",
        {
            "status": "success",
            "data": {
                "accession": "P22607",
                "features": [
                    {
                        "type": "DOMAIN",
                        "position_start": 350,
                        "position_end": 400,
                        "description": "protein kinase domain",
                    }
                ],
            },
        },
    )["reviewable_features"]
    interpro_values = adapt_source_output(
        "InterPro_get_entries_for_protein",
        {
            "status": "success",
            "data": {
                "protein_accession": "P22607",
                "entries": [
                    {"accession": "IPR000719", "name": "Protein kinase domain"}
                ],
            },
        },
    )["reviewable_features"]

    assert (
        source_fact_ready(
            "EBIProteins_get_features",
            feature_values,
            {"protein_accession": "P22607"},
        )[2]
        is True
    )
    assert (
        source_fact_ready(
            "InterPro_get_entries_for_protein",
            interpro_values,
            {"protein_accession": "P22607"},
        )[2]
        is True
    )
    assert interpro_values["interpro_entries"] == [
        {"accession": "IPR000719", "name": "Protein kinase domain"}
    ]
    assert all(
        "position_start" not in row for row in interpro_values["interpro_entries"]
    )


def test_ebi_known_variation_adapter_requires_residue_filter_before_readiness():
    features = adapt_source_output(
        "EBIProteins_get_variation",
        {
            "status": "success",
            "data": {
                "accession": "P22607",
                "variants": [
                    {
                        "position_start": 380,
                        "position_end": 380,
                        "wild_type": "G",
                        "alternative": "A",
                        "source_type": "mixed",
                        "xrefs": [{"id": "VCV000000123"}],
                    }
                ],
            },
        },
    )["reviewable_features"]

    assert features["protein_variants"][0]["alternative"] == "A"
    assert (
        source_fact_ready(
            "EBIProteins_get_variation",
            features,
            {"protein_accession": "P22607"},
        )[2]
        is False
    )
    features["same_residue_candidates"] = []
    assert (
        source_fact_ready(
            "EBIProteins_get_variation",
            features,
            {"protein_accession": "P22607"},
        )[2]
        is True
    )


def test_ensembl_lookup_gene_exon_contract():
    features = {
        "transcript_id": "ENST00000357654",
        "exons": [
            {
                "exon_id": "ENSE1",
                "transcript": "ENST00000357654",
                "rank": 3,
                "chrom": "4",
                "start": 100,
                "end": 200,
                "strand": 1,
            }
        ],
        "provider_version": "Ensembl REST lookup",
    }
    expected = {"ensembl_transcript_id": "ENST00000357654"}
    assert source_fact_ready("ensembl_lookup_gene", features, expected)[2] is True
    assert (
        source_fact_ready(
            "ensembl_lookup_gene",
            {**features, "transcript_id": "ENST00000000000"},
            expected,
        )[2]
        is False
    )
    assert (
        source_fact_ready("ensembl_lookup_gene", {**features, "exons": []}, expected)[2]
        is False
    )


def test_gnomad_region_variants_contract():
    features = {
        "chrom": "4",
        "start": 1803900,
        "stop": 1804200,
        "variants": [
            {
                "variant_id": "4-1804000-A-T",
                "consequence": "stop_gained",
                "af_exome": 0.003,
                "homozygote_count_exome": 0,
            }
        ],
        "provider_version": "gnomAD GraphQL region variants",
    }
    expected = {"coordinates": {"chr": "4", "pos": 1803931, "ref": "C", "alt": "A"}}
    assert (
        source_fact_ready("gnomad_get_region_variants", features, expected)[2] is True
    )
    assert (
        source_fact_ready(
            "gnomad_get_region_variants", {**features, "chrom": "5"}, expected
        )[2]
        is False
    )
    assert (
        source_fact_ready(
            "gnomad_get_region_variants",
            {**features, "provider_version": ""},
            expected,
        )[2]
        is False
    )


def test_ensembl_lookup_and_region_variants_adapters_parse_payloads():
    lookup = adapt_source_output(
        "ensembl_lookup_gene",
        {
            "status": "success",
            "data": {
                "id": "ENST00000357654",
                "seq_region_name": "4",
                "Exon": [
                    {
                        "id": "ENSE1",
                        "start": 100,
                        "end": 200,
                        "rank": 3,
                        "strand": 1,
                    }
                ],
            },
        },
    )
    lookup_features = lookup["reviewable_features"]
    assert lookup_features["transcript_id"] == "ENST00000357654"
    assert lookup_features["exons"][0]["rank"] == 3
    assert lookup_features["exons"][0]["start"] == 100

    region = adapt_source_output(
        "gnomad_get_region_variants",
        {
            "status": "success",
            "data": {
                "region": {
                    "chrom": "4",
                    "start": 1803900,
                    "stop": 1804200,
                    "variants": [
                        {
                            "variant_id": "4-1804000-A-T",
                            "consequence": "stop_gained",
                            "filters": [],
                            "exome": {
                                "ac": 5,
                                "an": 1000,
                                "af": 0.005,
                                "homozygote_count": 1,
                            },
                            "genome": None,
                        }
                    ],
                }
            },
        },
    )
    region_features = region["reviewable_features"]
    assert region_features["variants"][0]["consequence"] == "stop_gained"
    assert region_features["variants"][0]["af_exome"] == 0.005
    assert region_features["variants"][0]["homozygote_count_exome"] == 1


def test_myvariant_preserves_full_predictor_audit_surface():
    adapted = adapt_source_output(
        "MyVariant_get_pathogenicity_scores",
        {
            "status": "success",
            "version": "4.7a",
            "data": {
                "_id": "chr1:g.10A>G",
                "dbnsfp": {
                    "revel": {"score": [0.91]},
                    "cadd": {"phred": 28.4},
                    "alphamissense": {"score": 0.88, "pred": "P"},
                    "sift": {"score": 0.01, "pred": "D"},
                    "polyphen2_hdiv": {"score": 0.99, "pred": "D"},
                    "metarnn": {"score": 0.95, "pred": "D"},
                    "gerp_rs": 5.7,
                    "phylop100way_vertebrate": {"rankscore": 0.97},
                    "phastcons100way_vertebrate": {"rankscore": 0.96},
                    "vest4": {"score": 0.82},
                    "mutationtaster": {"pred": "D"},
                },
            },
        },
    )
    features = adapted["reviewable_features"]
    audit = features["predictor_audit"]
    assert features["revel_score"] == 0.91
    assert features["cadd_phred"] == 28.4
    assert audit["alphamissense_score"] == 0.88
    assert audit["sift_prediction"] == "D"
    assert audit["polyphen2_hdiv_score"] == 0.99
    assert audit["metarnn_score"] == 0.95
    assert audit["gerp_rs"] == 5.7
    assert audit["phylop100way_vertebrate_rankscore"] == 0.97
    assert audit["phastcons100way_vertebrate_rankscore"] == 0.96
    assert audit["vest4_score"] == 0.82
    assert audit["mutationtaster_prediction"] == "D"


def test_new_gnomad_constraint_contract_is_complete_and_identity_bound():
    adapted = adapt_source_output(
        "gnomad_get_constraint",
        {
            "status": "success",
            "data": {
                "gene_symbol": "FGFR3",
                "gene_id": "ENSG00000068078",
                "dataset": "gnomad_r4",
                "reference_genome": "GRCh38",
                "pLI": 0.98,
                "oe_lof": 0.12,
                "oe_lof_lower": 0.08,
                "oe_lof_upper": 0.21,
                "loeuf": 0.21,
                "mis_z": 3.2,
                "syn_z": 0.1,
                "obs_lof": 2,
                "exp_lof": 20,
            },
        },
    )
    features = adapted["reviewable_features"]
    assert features["oe_lof_upper"] == 0.21
    assert features["mis_z"] == 3.2
    assert features["syn_z"] == 0.1
    observed, identity_verified, ready = source_fact_ready(
        "gnomad_get_constraint", features, {"gene": "FGFR3"}
    )
    assert observed == {"gene": "FGFR3"}
    assert identity_verified is True
    assert ready is True
    assert (
        source_fact_ready("gnomad_get_constraint", features, {"gene": "NOTCH1"})[2]
        is False
    )


def test_clinvar_adapter_accepts_raw_search_and_new_data_payload_shapes():
    payloads = [
        {
            "status": "success",
            "data": {
                "result": {
                    "uids": ["1"],
                    "1": {
                        "uid": "1",
                        "title": "NM_000518.5(HBB):c.20A>T",
                        "germline_classification": {"description": "Pathogenic"},
                    },
                }
            },
        },
        {
            "status": "success",
            "data": {
                "variant_id": "2",
                "raw_data": {
                    "uid": "2",
                    "title": "NM_000518.5(HBB):c.20A>T",
                    "germline_classification": {"description": "Pathogenic"},
                },
            },
        },
    ]
    for payload in payloads:
        adapted = adapt_source_output("ClinVar_get_clinical_significance", payload)
        assert adapted["reviewable_features"]["title"].endswith("c.20A>T")
        assert "germline_classification" not in adapted["reviewable_features"]
        assert any(
            "germline_classification" in key
            for key in adapted["quarantined_conclusions"]
        )


def test_clingen_context_adapters_preserve_direct_actionability_and_classifications():
    adult = adapt_source_output(
        "ClinGen_get_actionability_adult",
        {
            "status": "success",
            "gene": "BRCA1",
            "data": [
                {
                    "Gene(s)": "BRCA1",
                    "condition": "Hereditary breast cancer",
                    "intervention": "Screening",
                }
            ],
            "total": 1,
        },
    )["reviewable_features"]
    classification = adapt_source_output(
        "ClinGen_get_variant_classifications",
        {
            "status": "success",
            "gene_searched": "BRCA1",
            "data": [
                {
                    "HGNC Gene Symbol": "BRCA1",
                    "Variation ID": "123",
                    "Classification": "Pathogenic",
                }
            ],
            "total": 1,
        },
    )

    assert adult["gene"] == "BRCA1"
    assert adult["actionability_context"] == "Adult"
    assert adult["actionability"][0]["intervention"] == "Screening"
    assert classification["reviewable_features"]["variant_classifications"]
    assert any(
        "Classification" in key for key in classification["quarantined_conclusions"]
    )


def test_hpo_adapters_preserve_full_association_counts_as_review_context():
    adapted = adapt_source_output(
        "HPO_get_genes_by_phenotype",
        {
            "status": "success",
            "data": {"genes": [{"id": "NCBIGene:672", "name": "BRCA1"}]},
            "metadata": {
                "term_id": "HP:0001250",
                "total": 1400,
                "returned": 500,
                "source": "JAX HPO",
            },
        },
    )["reviewable_features"]

    assert adapted["hpo_term"] == "HP:0001250"
    assert adapted["total_available"] == 1400
    assert adapted["values"]["genes"][0]["name"] == "BRCA1"
    assert adapted["review_only"] is True


def test_uniprot_adapter_preserves_complete_normalized_entry_context():
    adapted = adapt_source_output(
        "UniProt_get_entry_by_accession",
        {
            "status": "success",
            "data": {
                "primaryAccession": "P38398",
                "entryType": "UniProtKB reviewed (Swiss-Prot)",
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "BRCA1 protein"}}
                },
                "genes": [{"geneName": {"value": "BRCA1"}}],
                "sequence": {"length": 1863},
                "comments": [
                    {
                        "commentType": "FUNCTION",
                        "texts": [{"value": "DNA repair."}],
                    },
                    {
                        "commentType": "COFACTOR",
                        "cofactors": [{"name": "Zn(2+)"}],
                    },
                ],
                "features": [
                    {
                        "type": "Modified residue",
                        "description": "Phosphoserine",
                    }
                ],
                "uniProtKBCrossReferences": [{"database": "PDB", "id": "1JM7"}],
                "references": [{"citation": {"title": "BRCA1 study"}}],
            },
        },
    )["reviewable_features"]

    assert adapted["protein_accession"] == "P38398"
    assert adapted["protein_name"] == "BRCA1 protein"
    assert adapted["sequence_length"] == 1863
    assert adapted["function_comments"]
    assert adapted["cofactors"][0]["name"] == "Zn(2+)"
    assert adapted["ptm_features"]
    assert adapted["cross_references"][0]["database"] == "PDB"
    assert adapted["references"][0]["citation"]["title"] == "BRCA1 study"


def test_variantformatter_adapter_exposes_mane_consequence_projection():
    adapted = adapt_source_output(
        "VariantValidator_format_genomic_to_transcripts",
        {
            "metadata": {"variantformatter_version": "2.2.0"},
            "submitted": {
                "normalized": {
                    "g_hgvs": "NC_000003.12:g.52396983_52396984del",
                    "hgvs_t_and_p": {
                        "NM_015512.5": {
                            "t_hgvs": "NM_015512.5:c.11726_11727del",
                            "p_hgvs": "NP_056327.4:p.Pro3909ArgfsTer33",
                            "gene_info": {"symbol": "DNAH1"},
                            "select_status": {"mane_select": True},
                        }
                    },
                }
            },
        },
    )
    features = adapted["reviewable_features"]
    candidate = features["consequence_candidates"][0]

    assert features["provider_version"] == "2.2.0"
    assert candidate["transcript"] == "NM_015512.5"
    assert candidate["mane_select"] == "NM_015512.5"
    assert candidate["consequence"] == ["frameshift_variant"]
    observed, identity_verified, ready = source_fact_ready(
        "VariantValidator_format_genomic_to_transcripts",
        features,
        {
            "gene": "DNAH1",
            "transcript": "NM_015512.5",
            "hgvs_c": "NM_015512.5:c.11726_11727del",
            "hgvs_g": "NC_000003.12:g.52396983_52396984del",
        },
    )
    assert observed["gene"] == "DNAH1"
    assert identity_verified is True
    assert ready is True


def test_favor_and_opentargets_adapters_preserve_transcript_consequences():
    favor = adapt_source_output(
        "FAVOR_annotate_variant",
        {
            "status": "success",
            "variant": "3-52396982-CCT-C",
            "metadata": {"source": "FAVOR fixture"},
            "data": {
                "variant": {"variant_vcf": "3-52396982-CCT-C"},
                "gene_consequence": {
                    "gene": "DNAH1",
                    "transcript": "NM_015512.5",
                    "hgvs_c": "NM_015512.5:c.11726_11727del",
                    "hgvs_p": "NP_056327.4:p.Pro3909ArgfsTer33",
                    "so_term": "frameshift_variant",
                    "exon": "73",
                },
            },
        },
    )["reviewable_features"]
    open_targets = adapt_source_output(
        "OpenTargets_get_variant_transcript_consequences",
        {
            "status": "success",
            "data": {
                "id": "3_52396982_CCT_C",
                "transcriptConsequences": [
                    {
                        "target": {"approvedSymbol": "DNAH1"},
                        "transcriptId": "ENST00000420323.6",
                        "aminoAcidChange": "P3909RfsTer33",
                        "variantConsequences": [{"label": "frameshift_variant"}],
                        "impact": "HIGH",
                        "isEnsemblCanonical": True,
                    }
                ],
            },
        },
    )["reviewable_features"]

    assert favor["consequence_candidates"][0]["exon"] == "73"
    assert favor["consequence_candidates"][0]["consequence"] == ["frameshift_variant"]
    assert open_targets["consequence_candidates"][0]["transcript"] == (
        "ENST00000420323.6"
    )
    assert open_targets["consequence_candidates"][0]["consequence"] == [
        "frameshift_variant"
    ]
