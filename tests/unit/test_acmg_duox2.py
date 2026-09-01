"""DUOX2 regression: reported scores with explicitly synthetic offline metadata."""

import json

import pytest

from tooluniverse.acmg.collector import (
    ACMGEvidencePipeline,
    SourceCall,
    _compact_result,
    _compact_spliceai,
)
from tooluniverse.acmg_runtime_tools import ACMGGuardFinalAnswerTool


class DUOX2Fixture:
    """Scores/alleles reproduce the report; transcript metadata is a test fixture."""

    def __init__(self, second=False):
        self.calls = []
        self.transcript = "NM_001363711.2"
        self.c = self.transcript + (":c.4027C>T" if second else ":c.3632G>A")
        self.p = "NP_001350640.1:p." + ("Leu1343Phe" if second else "Arg1211His")
        self.position = 45095881 if second else 45097675
        self.fixture_grch37_position = 45195881 if second else 45197675
        self.ref, self.alt = ("G", "A") if second else ("C", "T")
        self.g = f"NC_000015.10:g.{self.position}{self.ref}>{self.alt}"
        self.revel, self.splice = (0.575, 0.017) if second else (0.967, 0.008)
        self.residue = 1343 if second else 1211
        self.aa_ref, self.aa_alt = ("L", "F") if second else ("R", "H")

    def run_many_functions(self, calls, **kwargs):
        return [self.run_one_function(call, **kwargs) for call in calls]

    def run_one_function(self, call, **kwargs):
        self.calls.append(call)
        name, args = call["name"], call["arguments"]
        allele = {
            "chr": "15",
            "pos": self.position,
            "ref": self.ref,
            "alt": self.alt,
            "build": "GRCh38",
        }
        features = None
        if name == "VariantValidator_gene2transcripts":
            features = {
                "transcripts": [
                    {"reference": self.transcript, "gene": "DUOX2", "mane_select": True}
                ]
            }
        elif name in {
            "VariantValidator_validate_variant",
            "EnsemblVEP_variant_recoder",
        }:
            features = {
                **allele,
                "coordinates": allele,
                "gene": "DUOX2",
                "transcript": self.transcript,
                "validated_hgvs_c": self.c,
                "hgvs_c": self.c,
                "hgvs_g": self.g,
                "hgvs_p": self.p,
                "consequence": "missense_variant",
            }
            features.update(
                {
                    "hgvs_g_grch37": f"chr15:g.{self.fixture_grch37_position}{self.ref}>{self.alt}",
                    "coordinates_grch37": {
                        **allele,
                        "pos": self.fixture_grch37_position,
                    },
                }
            )
        elif name.startswith("EnsemblVEP_annotate"):
            features = {
                **allele,
                "gene": "DUOX2",
                "most_severe_consequence": "missense_variant",
                "vep_transcript_candidates": [
                    {
                        "gene": "DUOX2",
                        "transcript": self.transcript,
                        "mane_select": self.transcript,
                        "hgvsc": self.c,
                        "hgvsp": self.p,
                        "consequence": ["missense_variant"],
                    }
                ],
            }
        elif name == "OpenTargets_get_variant_transcript_consequences":
            features = {
                **allele,
                "consequence_candidates": [
                    {
                        "gene": "DUOX2",
                        "transcript": f"ENST{index:011d}",
                        "consequence": ["missense_variant"],
                    }
                    for index in range(1, 91)
                ],
            }
        elif name == "MyVariant_get_metadata":
            return {"status": "success", "source": "dbnsfp", "version": "4.8a"}
        elif name == "MyVariant_get_pathogenicity_scores":
            features = {
                **allele,
                "revel_score": self.revel,
                "alphamissense_score": 0.92,
                "sift_score": 0.01,
                "metarnn_score": 0.9,
                "vest4_score": 0.8,
                "mutationtaster_prediction": "D",
            }
            features.update({"build": "GRCh37", "pos": self.fixture_grch37_position})
        elif name == "SpliceAI_predict_splice":
            features = {
                **allele,
                "scores": [
                    {
                        "gene": "DUOX2",
                        "transcript": self.transcript,
                        "DS_AG": 0,
                        "DS_AL": self.splice,
                        "DS_DG": 0,
                        "DS_DL": 0,
                        "DP_AG": 0,
                        "DP_AL": -3,
                        "DP_DG": 0,
                        "DP_DL": 0,
                        "EXON_STARTS": list(range(100)),
                        "EXON_ENDS": list(range(100)),
                    }
                ],
                "run_metadata": {
                    "model_version": "1.3.1",
                    "annotation_version": "MANE fixture",
                    "score_mode": "raw",
                },
            }
        elif name == "gnomad_get_variant":
            features = {
                **allele,
                "variant_id": f"15-{self.position}-{self.ref}-{self.alt}",
                "dataset": "gnomad_r4",
                "callset": "exome",
                "AF": 165 / 1461888,
                "AC": 165,
                "AN": 1461888,
                "popmax": 8 / 20712,
                "popmax_population": "eas_XX",
                "populations": [
                    {"id": "eas_XX", "ac": 8, "an": 20712, "af": 8 / 20712}
                ],
            }
        elif name == "EBIProteins_get_variation_by_hgvs":
            features = {
                "hgvs_g": self.g,
                "protein_candidates": [
                    {
                        "protein_accession": accession,
                        "gene": "DUOX2",
                        "taxid": 9606,
                        "protein_position_start": self.residue,
                        "protein_position_end": self.residue,
                        "wild_type": self.aa_ref,
                        "alternative_sequence": self.aa_alt,
                    }
                    for accession in ("Q9NRD8", "X6RAN8")
                ],
            }
        elif name == "UniProt_get_entry_by_accession":
            accession = args["accession"]
            features = {
                "protein_accession": accession,
                "entry_status": "reviewed" if accession == "Q9NRD8" else "unreviewed",
                "cross_reference_index": [
                    {
                        "database": "RefSeq",
                        "id": self.p.split(":")[0],
                        "properties": [
                            {"key": "NucleotideSequenceId", "value": self.transcript}
                        ],
                    }
                ]
                if accession == "Q9NRD8"
                else [],
                "sequence_length": 1548,
            }
        elif name == "EBIProteins_get_features":
            features = {
                "protein_accession": args["accession"],
                "features": [],
                "sequence_length": 1548,
            }
        elif name == "InterPro_get_entries_for_protein":
            features = {"protein_accession": args["accession"], "interpro_entries": []}
        elif name == "PubMed_search_articles":
            features = {
                "articles": [
                    {"pmid": str(90000000 + i), "title": "DUOX2 background"}
                    for i in range(64)
                ]
            }
        if features is not None:
            return {
                "status": "success",
                "source_lead_sandbox": {
                    "reviewable_features": {
                        "provider_version": "offline fixture 1",
                        **features,
                    }
                },
            }
        return {"status": "unavailable", "reason": "No offline fixture"}


@pytest.mark.parametrize("second", [False, True])
def test_duox2_one_collection_preserves_scores_frequency_and_resolves_protein(
    second, check_acmg_summary
):
    provider = DUOX2Fixture(second)
    full = ACMGEvidencePipeline(provider).run(
        {
            "variant": provider.c + "(" + provider.p.split(":")[1] + ")",
            "gene": "DUOX2",
            "transcript": provider.transcript,
            "response_detail": "full",
        }
    )
    result = _compact_result(full)
    assert full["consequence_profile"]["annotation_status"] == "resolved"
    mapping = full["consequence_profile"]["protein_mapping"]
    assert mapping["selected"]["protein_accession"] == "Q9NRD8"
    assert mapping["selected"]["mapping_basis"] == "exact_refseq"
    cards = result["evidence_cards"]
    automatic = {
        row["criterion"]: row for row in cards if row["calculation_roles"]["automatic"]
    }
    assert "BP4" not in automatic
    assert ("PP3" in automatic) is not second
    if not second:
        assert automatic["PP3"]["strength"] == "PP3_Strong"
    assert set(result["verified_bayesian"].get("included_card_ids", [])) <= set(
        result["automatic_bayesian"].get("included_card_ids", [])
    )
    pop = next(
        row
        for row in result["population_observations"]
        if row["tool_name"] == "gnomad_get_variant"
    )
    assert pop["observations"]["AC"] == 165
    assert pop["observations"]["AN"] == 1461888
    assert pop["observations"]["popmax_population"] == "eas_XX"
    pm2 = next(row for row in result["criterion_reviews"] if row["criterion"] == "PM2")
    assert (
        pm2["rule_evaluations"][0]["candidate_filter"]["status"] == "condition_not_met"
    )
    assert "PM2" not in automatic
    assert len(result["literature_candidates"]) == 64
    groups = result["consequence_profile"]["observation_groups"]
    assert sum(len(group["rows"]) for group in groups) == len(
        full["consequence_profile"]["observations"]
    )
    restored = [
        {
            **result["consequence_profile"].get("observation_defaults", {}),
            **group["shared"],
            **dict(zip(group["columns"], row)),
        }
        for group in groups
        for row in group["rows"]
    ]
    fields = ("provider", "transcript", "hgvs_c", "hgvs_p", "consequence_terms")

    def signatures(rows):
        return sorted(
            json.dumps([row.get(key) or None for key in fields], sort_keys=True)
            for row in rows
        )

    assert signatures(restored) == signatures(
        full["consequence_profile"]["observations"]
    )

    def size(value):
        return len(
            json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
        )

    check_acmg_summary(result)
    assert size(result["guard_context"]) < 5000
    assert "EXON_STARTS" not in json.dumps(result["predictor_scores"])
    text = (
        "REVEL="
        + str(provider.revel)
        + "; SpliceAI="
        + str(provider.splice)
        + ". PM2 lacks a disease-specific frequency threshold."
    )
    assert (
        ACMGGuardFinalAnswerTool({}).run(
            {"final_answer_text": text, "guard_context": result["guard_context"]}
        )["status"]
        == "PASS"
    )
    calls = [row["name"] for row in provider.calls]
    assert calls.count("gnomad_get_variant") == 1
    assert calls.count("UniProt_get_entry_by_accession") == 2
    assert all(
        row["arguments"]["accession"] == "Q9NRD8"
        for row in provider.calls
        if row["name"]
        in {"InterPro_get_entries_for_protein", "EBIProteins_get_features"}
    )


def test_protein_reviewed_tiebreak_never_overrides_exact_target():
    features = {
        "protein_candidates": [
            {
                "protein_accession": accession,
                "gene": "DUOX2",
                "protein_position_start": 1211,
                "wild_type": "R",
                "alternative_sequence": "H",
            }
            for accession in ("Q9NRD8", "A0A-2")
        ]
    }
    profile = {
        "protein_effect": "missense",
        "hgvs_p": "NP_001350640.1:p.Arg1211His",
        "selected_transcript": "NM_001363711.2",
    }
    args = dict(gene="DUOX2", profile=profile, protein_accession_hint="")
    assert (
        ACMGEvidencePipeline._select_protein_mapping(features, **args)["selected"]
        is None
    )
    entries = {
        "Q9NRD8": {
            "entry_status": "reviewed",
            "cross_reference_index": [{"id": "NM_014080.5"}],
        },
        "A0A-2": {
            "entry_status": "unreviewed",
            "cross_reference_index": [{"id": "NM_001363711.2"}],
        },
    }
    result = ACMGEvidencePipeline._select_protein_mapping(
        features, uniprot_entries=entries, **args
    )
    assert result["selected"]["protein_accession"] == "A0A-2"
    entries["Q9NRD8"]["cross_reference_index"] = entries["A0A-2"][
        "cross_reference_index"
    ]
    assert (
        ACMGEvidencePipeline._select_protein_mapping(
            features, uniprot_entries=entries, **args
        )["selected"]["protein_accession"]
        == "Q9NRD8"
    )
    # A cross-reference to a non-displayed isoform is not a canonical match.
    entries["Q9NRD8"]["cross_reference_index"] = [
        {"id": "NM_001363711.2", "isoformId": "Q9NRD8-2"}
    ]
    selected = ACMGEvidencePipeline._select_protein_mapping(
        features, uniprot_entries=entries, **args
    )["selected"]
    assert selected["protein_accession"] == "A0A-2"
    entries["A0A-2"]["protein_accession"] = "WRONG_ENTRY"
    result = ACMGEvidencePipeline._select_protein_mapping(
        features, uniprot_entries=entries, **args
    )
    assert (
        next(
            row for row in result["candidates"] if row["protein_accession"] == "A0A-2"
        )["mapping_basis"]
        == "entry_accession_conflict"
    )


def test_splice_summary_keeps_all_distinct_delta_values_without_raw_duplicates():
    scores = {"DS_AG": 0.008, "DS_AL": 0.002, "DS_DG": 0.004, "DS_DL": 0.001}
    positions = {"DP_AG": 117, "DP_AL": -301, "DP_DG": -118, "DP_DL": -61}
    selected = {**scores, **positions, "t_id": "ENST1", "g_name": "DUOX2"}
    raw = {
        "scores": [
            {**selected, "EXON_STARTS": [1, 2], "DS_AG_REF": 0.102},
            {**selected, "t_id": "ENST2", "DS_AG": 0.02},
        ],
        "profile": {
            "status": "resolved",
            "selected_transcript": "ENST1",
            "selected_gene": "DUOX2",
            "delta_scores": scores,
            "delta_positions": positions,
        },
    }
    compact = _compact_spliceai(raw)
    assert compact["profile"]["delta_scores"] == scores
    assert compact["profile"]["delta_positions"] == positions
    assert len(compact["alternate_transcript_scores"]) == 1
    assert compact["alternate_transcript_scores"][0]["DS_AG"] == 0.02
    assert "scores" not in compact
    assert raw["scores"][0]["EXON_STARTS"] == [1, 2]


@pytest.mark.parametrize(
    "primary",
    ["complete", "failed", "empty", "empty_sections", "captions_only", "partial"],
)
def test_document_fallback_only_when_needed_and_reused_for_proposals(
    monkeypatch, primary
):
    pipeline = ACMGEvidencePipeline(None)
    requested = []

    def batch(specs):
        results = []
        for name, arguments, category in specs:
            requested.append(name)
            fallback = name == "EuropePMC_get_fulltext"
            body = (
                {"text": "DUOX2 article body"} if fallback or primary != "empty" else {}
            )
            if primary == "empty_sections" and not fallback:
                body = {"sections": {"results": [{"title": "Results", "text": " "}]}}
            if primary == "captions_only" and not fallback:
                body = {"figures": [{"caption": "DUOX2 figure without body text"}]}
            payload = {
                "status": "success",
                "data": body,
                "source": "PMC HTML" if fallback else "Europe PMC XML",
                "format": "html" if fallback else "xml",
                "url": "https://example.org/article",
                "truncated": primary == "partial" and not fallback,
            }
            results.append(
                SourceCall(
                    name,
                    category,
                    "failed" if primary == "failed" and not fallback else "success",
                    payload,
                    arguments=arguments,
                )
            )
        return results

    monkeypatch.setattr(pipeline, "_call_batch", batch)
    candidates = [{"pmid": "123"}, {"pmid": "123", "pmcid": "PMC123"}, {"pmid": "123"}]
    docs, calls = pipeline._fetch_literature_documents(candidates)
    assert len(requested) == (1 if primary == "complete" else 2)
    assert docs["123"] is docs["PMC123"]
    _, extra = pipeline._fetch_literature_documents(candidates, calls)
    assert extra == []
    assert len(requested) == (1 if primary == "complete" else 2)
