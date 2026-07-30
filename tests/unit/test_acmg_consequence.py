"""Selected-transcript consequence routing tests."""

from tooluniverse.acmg.consequence import (
    build_consequence_profile,
    consequence_applicability,
)
from tooluniverse.acmg.consequence_sources import resolve_consequence_observations
from tooluniverse.acmg.rule_catalog import ACMG_CRITERIA, CONSEQUENCE_POLICIES


IDENTITY = {
    "gene": "FGFR3",
    "transcript": "NM_000142.5",
    "coordinates": {"chr": "4", "pos": 1803931, "ref": "C", "alt": "G"},
}


def test_every_acmg_criterion_has_an_explicit_consequence_policy():
    assert set(CONSEQUENCE_POLICIES) == set(ACMG_CRITERIA)


def _features(*candidates, most_severe="stop_gained"):
    return {
        "most_severe_consequence": most_severe,
        "vep_transcript_candidates": list(candidates),
    }


def _candidate(*terms, **overrides):
    row = {
        "gene": "FGFR3",
        "transcript": "ENST00000440486.7",
        "mane_select": "NM_000142.5",
        "hgvsc": "NM_000142.5:c.1138G>A",
        "hgvsp": "NP_000133.1:p.Gly380Arg",
        "consequence": list(terms),
    }
    row.update(overrides)
    return row


def test_selected_mane_transcript_wins_over_most_severe_other_transcript():
    profile = build_consequence_profile(
        IDENTITY,
        _features(
            _candidate("missense_variant"),
            _candidate(
                "stop_gained",
                transcript="ENST00000699999.1",
                mane_select=None,
                hgvsc="ENST00000699999.1:c.10G>T",
                hgvsp="ENSP00000999999.1:p.Glu4Ter",
            ),
        ),
        source_fact_ids=["vep-fact"],
    )

    assert profile["status"] == "resolved"
    assert profile["protein_effect"] == "missense"
    assert profile["selected_transcript_terms"] == ["missense_variant"]
    assert profile["most_severe_consequence"] == "stop_gained"
    assert profile["source_fact_ids"] == ["vep-fact"]


def test_missense_and_splice_region_terms_preserve_two_routes():
    profile = build_consequence_profile(
        {**IDENTITY, "hgvs_c": "NM_000142.5:c.1075+5G>A"},
        _features(
            _candidate(
                "missense_variant",
                "splice_region_variant",
                hgvsc="NM_000142.5:c.1075+5G>A",
            )
        ),
    )

    assert profile["status"] == "resolved"
    assert profile["protein_effect"] == "missense"
    assert profile["splice_class"] == "noncanonical"
    assert consequence_applicability("PM1", profile)["status"] == "applicable"
    assert consequence_applicability("PP3", profile)["status"] == "applicable"


def test_canonical_splice_routes_to_pvs1_not_computational_pp3():
    profile = build_consequence_profile(
        {**IDENTITY, "hgvs_c": "NM_000142.5:c.1075+1G>A"},
        _features(
            _candidate(
                "splice_donor_variant",
                "intron_variant",
                hgvsc="NM_000142.5:c.1075+1G>A",
                hgvsp="",
            )
        ),
    )

    assert profile["splice_class"] == "canonical"
    assert profile["canonical_site_type"] == "donor"
    assert profile["hgvs_operation"] == "substitution"
    assert profile["canonical_motif_effect"] == "disrupted"
    assert profile["canonical_motif_sequence_status"] == "disrupted"
    assert profile["genomic_position"] == 1803931
    assert profile["genomic_ref"] == "C"
    assert profile["genomic_alt"] == "G"
    assert consequence_applicability("PVS1", profile)["status"] == "applicable"
    assert consequence_applicability("PP3", profile)["status"] == "not_applicable"


def test_canonical_duplication_preserves_both_offsets_and_fails_closed_on_motif():
    profile = build_consequence_profile(
        {**IDENTITY, "hgvs_c": "NM_000142.5:c.1075+1_1075+2dup"},
        _features(
            _candidate(
                "splice_donor_variant",
                "intron_variant",
                hgvsc="NM_000142.5:c.1075+1_1075+2dup",
                hgvsp="",
            )
        ),
    )

    assert profile["splice_positions"] == [1, 2]
    assert profile["splice_position"] == 1
    assert profile["canonical_site_type"] == "donor"
    assert profile["hgvs_operation"] == "duplication"
    assert profile["canonical_motif_effect"] == "potentially_preserved"
    assert profile["canonical_motif_sequence_status"] == "potentially_preserved"


def test_acceptor_range_and_conflicting_site_identity_are_explicit():
    acceptor = build_consequence_profile(
        {**IDENTITY, "hgvs_c": "NM_000142.5:c.1076-2_1076-1dup"},
        _features(
            _candidate(
                "splice_acceptor_variant",
                "intron_variant",
                hgvsc="NM_000142.5:c.1076-2_1076-1dup",
                hgvsp="",
            )
        ),
    )
    conflicting = build_consequence_profile(
        {**IDENTITY, "hgvs_c": "NM_000142.5:c.1076-1G>A"},
        _features(
            _candidate(
                "splice_donor_variant",
                hgvsc="NM_000142.5:c.1076-1G>A",
                hgvsp="",
            )
        ),
    )

    assert acceptor["splice_positions"] == [-2, -1]
    assert acceptor["canonical_site_type"] == "acceptor"
    assert conflicting["canonical_site_type"] == "ambiguous"
    assert conflicting["canonical_motif_effect"] == "unknown"


def test_unknown_so_term_and_conflicting_selected_transcript_fail_closed():
    unknown = build_consequence_profile(
        IDENTITY,
        _features(_candidate("future_consequence_term")),
    )
    conflicting = build_consequence_profile(
        IDENTITY,
        _features(
            _candidate("missense_variant"),
            _candidate("missense_variant", hgvsp="NP_000133.1:p.Gly380Val"),
        ),
    )

    assert unknown["status"] == "ambiguous"
    assert unknown["unrecognized_transcript_terms"] == ["future_consequence_term"]
    assert consequence_applicability("PM1", unknown)["status"] == "requires_context"
    assert conflicting["status"] == "ambiguous"


def test_cspec_can_explicitly_allow_inframe_pm1_route():
    profile = build_consequence_profile(
        IDENTITY,
        _features(_candidate("inframe_deletion", hgvsp="NP_000133.1:p.Gly380del")),
    )

    assert consequence_applicability("PM1", profile)["status"] == "not_applicable"
    assert (
        consequence_applicability(
            "PM1", profile, cspec_criterion={"variant_types": ["inframe"]}
        )["status"]
        == "applicable"
    )


def test_stop_lost_uses_explicit_pm4_term_without_extending_effect_enum():
    profile = build_consequence_profile(
        IDENTITY,
        _features(_candidate("stop_lost", hgvsp="NP_000133.1:p.Ter380ArgextTer5")),
    )

    assert profile["status"] == "resolved"
    assert profile["protein_effect"] == "unresolved"
    assert consequence_applicability("PM4", profile)["status"] == "applicable"


def test_non_consequence_evidence_is_never_screened_out_by_profile():
    profile = {"status": "ambiguous", "protein_effect": "unresolved"}

    for criterion in ("PM2", "PS2", "PS3", "PS4", "PP1"):
        assert consequence_applicability(criterion, profile)["status"] == (
            "not_consequence_gated"
        )


def test_multi_provider_resolver_accepts_overlapping_term_detail():
    observations = [
        {
            "source_fact_id": "vep",
            "provider": "EnsemblVEP_annotate_hgvs",
            "assessment_ready": True,
            "identity_status": "verified",
            "selected_transcript_status": "exact",
            "consequence_terms": ["frameshift_variant", "nmd_transcript_variant"],
            "hgvs_p": "ENSP000001:p.Pro3909ArgfsTer33",
            "_match_rank": 0,
            "_provider_rank": 0,
        },
        {
            "source_fact_id": "vv",
            "provider": "VariantValidator_format_genomic_to_transcripts",
            "assessment_ready": True,
            "identity_status": "verified",
            "selected_transcript_status": "exact",
            "consequence_terms": ["frameshift_variant"],
            "hgvs_p": "NP_001354730.1:p.Pro3909ArgfsTer33",
            "_match_rank": 0,
            "_provider_rank": 1,
        },
    ]

    resolution = resolve_consequence_observations(IDENTITY, observations)

    assert resolution["status"] == "resolved"
    assert resolution["selected_source_fact_ids"] == ["vep", "vv"]


def test_multi_provider_resolver_fails_closed_on_disjoint_effects():
    observations = [
        {
            "source_fact_id": "vv",
            "provider": "VariantValidator_format_genomic_to_transcripts",
            "assessment_ready": True,
            "identity_status": "verified",
            "selected_transcript_status": "exact",
            "consequence_terms": ["frameshift_variant"],
            "_match_rank": 0,
            "_provider_rank": 1,
        },
        {
            "source_fact_id": "other",
            "provider": "FAVOR_annotate_variant",
            "assessment_ready": True,
            "identity_status": "verified",
            "selected_transcript_status": "exact",
            "consequence_terms": ["synonymous_variant"],
            "_match_rank": 0,
            "_provider_rank": 3,
        },
    ]

    resolution = resolve_consequence_observations(IDENTITY, observations)

    assert resolution["status"] == "identity_conflict"
    assert resolution["selected_observation"] is None
