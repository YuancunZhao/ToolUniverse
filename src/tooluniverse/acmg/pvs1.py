"""Deterministic ClinGen SVI PVS1 decision tree.

Implements the Abou Tayoun et al. 2018 (PMID:30192042) PVS1 flowchart with
selected-transcript SpliceAI Loss/Gain and delta-position interpretation for
the canonical splice-site route. The tree is fail-closed: it only consumes structured,
machine-verifiable facts and never caller booleans; facts that cannot be
verified (last-50nt NMD boundary, exon-frame outcome, alternative start
codons) trigger conservative downgrades or ``not_assessed`` instead of
assumed strength. Deletion and duplication branches remain review-only until
curated exon-level fact contracts exist.
"""

from __future__ import annotations

from typing import Any

from .consequence import consequence_applicability
from .models import EvidenceCard

RULE_ID = "clingen-svi-pvs1"
RULE_VERSION = "1.2"
RULE_REFERENCE = "Abou Tayoun et al. 2018, PMID:30192042"
RULE_BASIS = "ClinGen SVI PVS1 decision tree"

_STRENGTH_LADDER = ("PVS1_Supporting", "PVS1_Moderate", "PVS1_Strong", "PVS1")

_TRUNCATING_TERMS = {"stop_gained", "frameshift_variant"}
_START_LOST_TERMS = {"start_lost"}

# gnomAD constraint thresholds for LoF intolerance (Karczewski et al. 2020).
_PLI_INTOLERANT = 0.9
_LOEUF_INTOLERANT = 0.35
_VALIDITY_ESTABLISHED = {"definitive", "strong", "moderate"}

_LOF_MECHANISM_TERMS = {
    "lof",
    "loss of function",
    "loss-of-function",
    "loss_of_function",
    "haploinsufficiency",
    "nonsense mediated decay",
    "nonsense-mediated decay",
}
_NON_LOF_MECHANISM_TERMS = {
    "gof",
    "gain of function",
    "gain-of-function",
    "gain_of_function",
    "dominant negative",
    "dominant-negative",
    "dominant_negative",
}
_NMD_ESCAPE_FRACTION = 0.10

# Exon-level "LoF frequent in the general population" gate (gnomAD facts).
_EXON_LOF_FREQUENT_AF = 0.001
_EXON_LOF_CONSEQUENCES = {
    "stop_gained",
    "frameshift_variant",
    "splice_donor_variant",
    "splice_acceptor_variant",
}

# UniProt curated feature types that count as machine-verifiable critical
# regions; broader DOMAIN/MOTIF/REGION overlap stays review context only.
_CRITICAL_FEATURE_TYPES = {"act_site", "binding", "metal", "site"}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _weaken(strength: str) -> str:
    index = _STRENGTH_LADDER.index(strength)
    return _STRENGTH_LADDER[max(0, index - 1)]


def _cap(strength: str, ceiling: Any) -> str:
    ceiling = str(ceiling or "")
    if ceiling not in _STRENGTH_LADDER:
        return strength
    if _STRENGTH_LADDER.index(strength) > _STRENGTH_LADDER.index(ceiling):
        return ceiling
    return strength


def _exon_pair(value: Any) -> tuple[int | None, int | None]:
    """Parse a VEP exon/intron locator such as ``"3/10"`` or ``["3/10"]``."""
    if isinstance(value, (list, tuple)):
        value = next(iter(value), None)
    text = str(value or "").strip()
    if "/" not in text:
        return None, None
    number, _, total = text.partition("/")
    return _int(number), _int(total)


def _pvs1_contract(rule_override: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(rule_override, dict):
        return None
    criteria = rule_override.get("criteria")
    if not isinstance(criteria, dict):
        return None
    contract = criteria.get("PVS1")
    return dict(contract) if isinstance(contract, dict) else None


def _mechanism_from_facts(
    facts: dict[str, Any], contract: dict[str, Any] | None, steps: list[str]
) -> bool | None:
    """Resolve the LoF-disease-mechanism gate (decision-tree step 1)."""
    if contract is not None and contract.get("lof_mechanism_established") is True:
        steps.append("LoF mechanism established by verified CSpec contract")
        return True
    mechanism = facts.get("lof_mechanism")
    mechanism = dict(mechanism) if isinstance(mechanism, dict) else {}
    value = _norm(mechanism.get("value"))
    if value:
        if value in _LOF_MECHANISM_TERMS:
            steps.append(
                f"LoF mechanism established by {mechanism.get('source') or 'fact'} "
                f"(gene_disease_mechanism={value})"
            )
            return True
        if value in _NON_LOF_MECHANISM_TERMS:
            steps.append(
                f"LoF is not the documented disease mechanism "
                f"(gene_disease_mechanism={value})"
            )
            return False
    established = mechanism.get("established")
    if established is True:
        steps.append(
            f"LoF mechanism established by {mechanism.get('source') or 'fact'}"
        )
        return True
    if established is False:
        steps.append(
            f"LoF is not the disease mechanism per {mechanism.get('source') or 'fact'}"
        )
        return False
    steps.append(
        "LoF disease mechanism not established: requires a CSpec contract, a "
        "document-verified gene_disease_mechanism fact, or another explicitly "
        "validated disease-specific mechanism source. ClinGen validity, pLI, "
        "and LOEUF are context only."
    )
    return None


def infer_mechanism_from_population_facts(
    validity_curations: Any, constraint: dict[str, Any] | None
) -> dict[str, Any]:
    """Return review context without treating constraint as disease mechanism.

    ClinGen validity establishes a gene-disease association and pLI/LOEUF
    describe gene-level population constraint. Neither proves that LoF is the
    mechanism for the specific disease. These observations therefore remain
    visible context, while the PVS1 mechanism gate stays unresolved.
    """
    curations = [row for row in validity_curations or [] if isinstance(row, dict)]
    best = ""
    for row in curations:
        validity = _norm(row.get("gene_disease_validity"))
        if validity in _VALIDITY_ESTABLISHED:
            best = validity
            break
    constraint = dict(constraint or {})
    pli = _float(constraint.get("pli"))
    loeuf = _float(constraint.get("loeuf"))
    intolerant = (pli is not None and pli >= _PLI_INTOLERANT) or (
        loeuf is not None and loeuf <= _LOEUF_INTOLERANT
    )
    return {
        "established": None,
        "source": "clingen_gnomad_review_context",
        "gene_disease_validity": best or None,
        "pli": pli,
        "loeuf": loeuf,
        "lof_intolerant": bool(intolerant),
        "inference": (
            "Gene-disease validity plus LoF intolerance is review context only; "
            "a CSpec or document-backed gene-disease mechanism is required."
        ),
    }


def _transcript_gate(
    facts: dict[str, Any], steps: list[str]
) -> tuple[dict[str, Any], str | None]:
    """Return (transcript facts, fail-closed reason or None)."""
    transcript = facts.get("transcript")
    transcript = dict(transcript) if isinstance(transcript, dict) else {}
    biotype = _norm(transcript.get("biotype"))
    if not biotype:
        return transcript, "transcript biotype is required to assess NMD"
    if biotype != "protein_coding":
        return transcript, (
            f"PVS1 not predictable on biotype {biotype}: NMD and truncation "
            "assessments require a protein-coding transcript"
        )
    steps.append("selected transcript is protein-coding")
    return transcript, None


def _nmd_region(
    transcript: dict[str, Any], steps: list[str]
) -> tuple[str | None, int | None]:
    """Classify the PTC region; the 50nt boundary is not machine-verifiable."""
    exon_number, exon_total = _exon_pair(transcript.get("exon"))
    if transcript.get("exon_number") is not None:
        exon_number = _int(transcript.get("exon_number"))
        exon_total = _int(transcript.get("exon_total"))
    if exon_number is None or exon_total is None:
        steps.append(
            "exon position unavailable: PVS1 requires exon_number/exon_total "
            "from the selected transcript"
        )
        return None, exon_number
    if exon_total >= 3 and exon_number <= exon_total - 2:
        steps.append(
            f"PTC in exon {exon_number}/{exon_total}: NMD predicted "
            "(rescue-transcript status not machine-verified)"
        )
        return "nmd_predicted", exon_number
    if exon_number == exon_total - 1:
        steps.append(
            f"PTC in penultimate exon {exon_number}/{exon_total}: the final-50nt "
            "NMD-escape boundary is not machine-verifiable; conservative "
            "one-level downgrade"
        )
        return "nmd_uncertain", exon_number
    steps.append(
        f"PTC in terminal exon {exon_number}/{exon_total}: NMD escape; assess "
        "truncated fraction and critical regions"
    )
    return "nmd_escape", exon_number


def _critical_exons(contract: dict[str, Any] | None) -> set[int]:
    return {
        value
        for value in (
            _int(item) for item in (contract or {}).get("critical_exons") or []
        )
        if value is not None
    }


def _critical_feature_overlap(facts: dict[str, Any], steps: list[str]) -> bool:
    """UniProt curated functional features overlapping the truncated region."""
    context = facts.get("critical_region")
    context = dict(context) if isinstance(context, dict) else {}
    overlaps = [
        row
        for row in context.get("overlapping_features") or []
        if isinstance(row, dict) and _norm(row.get("type")) in _CRITICAL_FEATURE_TYPES
    ]
    for row in overlaps:
        steps.append(
            "truncated/altered region overlaps curated UniProt feature "
            f"{row.get('type')} {row.get('description') or ''}".strip()
        )
    return bool(overlaps)


def _exon_lof_frequent(
    facts: dict[str, Any], contract: dict[str, Any] | None, steps: list[str]
) -> bool:
    """gnomAD exon facts: frequent LoF variation argues against PVS1."""
    if (contract or {}).get("exon_lof_frequent_in_population") is True:
        steps.append(
            "LoF variants in this exon are frequent in the general population "
            "per CSpec contract; PVS1 does not apply"
        )
        return True
    threshold = _float((contract or {}).get("exon_lof_frequent_af_threshold"))
    threshold = threshold if threshold is not None else _EXON_LOF_FREQUENT_AF
    context = facts.get("exon_context")
    context = dict(context) if isinstance(context, dict) else {}
    for row in context.get("lof_variants") or []:
        if not isinstance(row, dict):
            continue
        if _norm(row.get("consequence")) not in _EXON_LOF_CONSEQUENCES:
            continue
        af = max(
            (
                value
                for value in (
                    _float(row.get("af_exome")),
                    _float(row.get("af_genome")),
                )
                if value is not None
            ),
            default=None,
        )
        hom = max(
            (
                value
                for value in (
                    _int(row.get("homozygote_count_exome")),
                    _int(row.get("homozygote_count_genome")),
                )
                if value is not None
            ),
            default=0,
        )
        if (af is not None and af >= threshold) or hom >= 1:
            steps.append(
                f"LoF variant {row.get('variant_id')} in this exon is frequent "
                f"in gnomAD (AF={af}, homozygotes={hom}; threshold "
                f"AF>={threshold}); PVS1 does not apply"
            )
            return True
    return False


def _escape_role_and_fraction(
    profile: dict[str, Any],
    facts: dict[str, Any],
    contract: dict[str, Any] | None,
    steps: list[str],
    exon_number: int | None,
) -> str:
    """NMD-escape / in-frame path of the SVI flowchart.

    Abou Tayoun 2018: a critical truncated/altered region is PVS1_Strong; an
    exon whose LoF variants are frequent in the general population (or that is
    absent from biologically relevant transcripts) is N/A; otherwise the
    removed protein fraction decides PVS1_Strong (>10%) vs PVS1_Moderate
    (<10%).
    """
    if (
        exon_number in _critical_exons(contract)
        or (contract or {}).get("critical_region_confirmed") is True
        or _critical_feature_overlap(facts, steps)
    ):
        steps.append("truncated/altered region is critical to protein function")
        return "PVS1_Strong"
    if _exon_lof_frequent(facts, contract, steps):
        return "not_applicable"
    steps.append("role of region in protein function treated as unknown")
    protein = facts.get("protein")
    protein = dict(protein) if isinstance(protein, dict) else {}
    position = _int(protein.get("position")) or _int(profile.get("protein_position"))
    length = _int(protein.get("length"))
    if position is not None and length is not None and length > 0:
        removed = max(0.0, (length - position) / length)
        if removed > _NMD_ESCAPE_FRACTION:
            steps.append(f"variant removes {removed:.1%} of the protein (>10%)")
            return "PVS1_Strong"
        steps.append(f"variant removes {removed:.1%} of the protein (<=10%)")
        return "PVS1_Moderate"
    steps.append(
        "protein length unavailable for the truncated fraction; "
        "conservative PVS1_Moderate"
    )
    return "PVS1_Moderate"


def _truncating_branch(
    profile: dict[str, Any],
    facts: dict[str, Any],
    contract: dict[str, Any] | None,
    steps: list[str],
) -> str:
    transcript, failure = _transcript_gate(facts, steps)
    if failure:
        steps.append(failure)
        return "not_assessed"
    region, exon_number = _nmd_region(transcript, steps)
    if region is None:
        return "not_assessed"
    if region == "nmd_predicted":
        strength = "PVS1"
    elif region == "nmd_uncertain":
        strength = "PVS1_Strong"
    else:
        strength = _escape_role_and_fraction(
            profile, facts, contract, steps, exon_number
        )
    return _contract_adjust(strength, contract, steps)


def _contract_covers_canonical_operation(
    contract: dict[str, Any] | None,
    operation: str,
) -> bool:
    if not isinstance(contract, dict) or not operation:
        return False
    frame = _norm(contract.get("predicted_frame_outcome"))
    if frame not in {
        "disrupts",
        "disrupts_reading_frame",
        "out_of_frame",
        "preserves",
        "preserves_reading_frame",
        "in_frame",
    }:
        return False
    aliases = {
        "duplication": {"duplication", "dup", "small_duplication"},
        "insertion": {"insertion", "ins", "small_insertion"},
    }.get(operation, {operation})
    allowed = {_norm(value) for value in contract.get("variant_types") or () if value}
    return bool(aliases & allowed)


def _canonical_splice_branch(
    profile: dict[str, Any],
    facts: dict[str, Any],
    contract: dict[str, Any] | None,
    steps: list[str],
) -> str:
    transcript, failure = _transcript_gate(facts, steps)
    if failure:
        steps.append(failure)
        return "not_assessed"
    rna = facts.get("rna_evidence")
    rna = dict(rna) if isinstance(rna, dict) else {}
    rna_outcome = _norm(rna.get("outcome"))
    if rna_outcome in {"no_lof", "in_frame_rescue", "normal_splicing"}:
        steps.append(
            "document-verified RNA evidence shows no LoF outcome; PVS1 does not apply"
        )
        return "not_applicable"
    motif_effect = _norm(profile.get("canonical_motif_effect"))
    operation = _norm(profile.get("hgvs_operation"))
    rna_confirms_lof = rna_outcome in {"lof_confirmed", "nmd_confirmed"}
    spliceai_profile = facts.get("spliceai_profile")
    spliceai_profile = (
        dict(spliceai_profile) if isinstance(spliceai_profile, dict) else {}
    )
    site_type = _norm(profile.get("canonical_site_type"))
    expected_channel = (
        "DS_DL" if site_type == "donor" else "DS_AL" if site_type == "acceptor" else ""
    )
    channel = str(spliceai_profile.get("native_loss_channel") or "")
    delta = _float(spliceai_profile.get("native_loss_score"))
    native_position = _int(spliceai_profile.get("native_loss_position"))
    threshold = _float(spliceai_profile.get("native_loss_threshold"))
    loss_supported = spliceai_profile.get("native_loss_supported")
    position_status = str(
        spliceai_profile.get("native_loss_position_status") or "unavailable"
    )
    spliceai_ready = (
        spliceai_profile.get("status") == "resolved"
        and site_type in {"donor", "acceptor"}
        and _norm(spliceai_profile.get("canonical_site_type")) == site_type
        and channel == expected_channel
        and delta is not None
        and native_position is not None
        and threshold is not None
        and position_status == "exact_selected_transcript_site"
        and type(loss_supported) is bool
    )
    contract_covers_operation = _contract_covers_canonical_operation(
        contract, operation
    )
    if motif_effect in {"potentially_preserved", "unknown"} and not (
        rna_confirms_lof or contract_covers_operation
    ):
        if not spliceai_ready:
            steps.append(
                "canonical_native_site_loss_unresolved: HGVS "
                f"{operation or 'operation'} does not by itself establish functional "
                "GT/AG loss, and SpliceAI Loss DP does not bind exactly to the "
                "selected-transcript exon boundary"
            )
            return "not_assessed"
        if loss_supported is not True:
            steps.append(
                f"canonical_native_site_loss_not_predicted: {expected_channel}="
                f"{delta} at DP={native_position} is below the {threshold} "
                "interpretation threshold; duplication/insertion remains review-only"
            )
            return "not_assessed"
        steps.append(
            f"selected-transcript SpliceAI predicts canonical {site_type} loss: "
            f"{expected_channel}={delta} at DP={native_position}, threshold={threshold}"
        )
    frame = _norm((contract or {}).get("predicted_frame_outcome"))
    if frame in {"disrupts", "disrupts_reading_frame", "out_of_frame"}:
        frame = "disrupts"
    elif frame in {"preserves", "preserves_reading_frame", "in_frame"}:
        frame = "preserves"
    elif rna_outcome in {"lof_confirmed", "nmd_confirmed"}:
        steps.append(
            "document-verified RNA evidence confirms an LoF (reading-frame "
            "disrupting) outcome"
        )
        frame = "disrupts"
    else:
        frame = ""
    region, exon_number = _nmd_region(transcript, steps)
    if frame == "disrupts":
        steps.append("exon skipping disrupts the reading frame")
        if region == "nmd_predicted":
            strength = "PVS1"
        elif region == "nmd_uncertain":
            strength = "PVS1_Strong"
        elif region is None:
            return "not_assessed"
        else:
            strength = _escape_role_and_fraction(
                profile, facts, contract, steps, exon_number
            )
    elif frame == "preserves":
        steps.append("exon skipping preserves the reading frame")
        strength = _escape_role_and_fraction(
            profile, facts, contract, steps, exon_number
        )
    else:
        # Exon-frame effects of exon skipping are not machine-verifiable; the
        # conservative default for a canonical +/-1/2 site is PVS1_Strong.
        strength = "PVS1_Strong"
        steps.append(
            "canonical +/-1/2 splice site; exon-frame outcome not "
            "machine-verified; conservative default PVS1_Strong"
        )
        if region == "nmd_uncertain":
            strength = _weaken(strength)
        elif region == "nmd_escape":
            strength = _weaken(strength)
        if site_type not in {"donor", "acceptor"}:
            steps.append(
                "canonical donor/acceptor identity is not uniquely resolved; "
                "native-site loss score cannot be selected"
            )
            return "not_assessed"
        if spliceai_profile.get("status") != "resolved":
            steps.append(
                "complete, internally consistent SpliceAI delta profile is "
                "required for the canonical native-site loss check"
            )
            return "not_assessed"
        if _norm(spliceai_profile.get("canonical_site_type")) != site_type:
            steps.append(
                "SpliceAI profile site type conflicts with the selected-transcript "
                "consequence"
            )
            return "not_assessed"
        if channel != expected_channel or delta is None or native_position is None:
            steps.append(
                f"{expected_channel} native-site loss score/position is unavailable; "
                "the four-channel maximum cannot substitute for selected-transcript "
                "DS/DP binding"
            )
            return "not_assessed"
        if position_status not in {
            "exact_selected_transcript_site",
            "within_canonical_20bp_window",
        }:
            steps.append(
                f"{expected_channel} loss event DP={native_position} does not bind "
                "to the selected-transcript canonical site"
            )
            return "not_assessed"
        steps.append(
            f"canonical {site_type} route uses {expected_channel}={delta} at "
            f"DP={native_position}; DP signs are genomic-coordinate relative and "
            "are not inverted by transcript strand"
        )
        gain_events = [
            row
            for row in spliceai_profile.get("supported_gain_events") or []
            if isinstance(row, dict)
        ]
        if gain_events:
            steps.append(
                "SpliceAI predicts canonical-window alternative site gain(s): "
                + ", ".join(
                    f"{row.get('score_channel')}={row.get('score')} "
                    f"at {row.get('position_channel')}={row.get('position')}"
                    for row in gain_events
                )
                + "; exact transcript/frame outcome requires review"
            )
        if loss_supported is False:
            steps.append(
                f"SpliceAI {expected_channel}={delta} is below the "
                f"{threshold} interpretation threshold; downgrade"
            )
            strength = _weaken(strength)
        else:
            steps.append(
                f"SpliceAI {expected_channel}={delta} supports native-site loss at "
                f"the applicable threshold (>={threshold})"
            )
    return _contract_adjust(strength, contract, steps)


def _start_lost_branch(
    profile: dict[str, Any],
    facts: dict[str, Any],
    contract: dict[str, Any] | None,
    steps: list[str],
) -> str:
    """Initiation-codon path of the SVI flowchart (Abou Tayoun 2018)."""
    alternative = (contract or {}).get("alternative_in_frame_start")
    if alternative is True:
        steps.append(
            "a different functional transcript uses an alternative start "
            "codon per CSpec contract; PVS1 does not apply"
        )
        return "not_applicable"
    if alternative is not False:
        steps.append(
            "alternative start codon status not machine-verified; PVS1 "
            "requires a CSpec contract documenting alternative_in_frame_start"
        )
        return "not_assessed"
    steps.append("CSpec contract documents no known alternative start codon")
    upstream = (contract or {}).get("pathogenic_upstream_of_alternative_start")
    if upstream is True:
        steps.append(
            ">=1 pathogenic variant(s) upstream of the closest potential "
            "in-frame start codon"
        )
        strength = "PVS1_Moderate"
    elif upstream is False:
        steps.append(
            "no pathogenic variant(s) upstream of the closest potential "
            "in-frame start codon"
        )
        strength = "PVS1_Supporting"
    else:
        steps.append(
            "upstream pathogenic-variant status not machine-verified; "
            "conservative weakest branch PVS1_Supporting"
        )
        strength = "PVS1_Supporting"
    return _contract_adjust(strength, contract, steps)


def _contract_adjust(
    strength: str, contract: dict[str, Any] | None, steps: list[str]
) -> str:
    if strength not in _STRENGTH_LADDER:
        return strength
    if contract is None:
        return strength
    if (
        contract.get("rescue_transcript_known") is True
        or contract.get("exon_absent_from_relevant_transcripts") is True
    ):
        steps.append(
            "exon is absent from biologically relevant transcript(s) per "
            "CSpec contract; PVS1 does not apply"
        )
        return "not_applicable"
    ceiling = contract.get("strength_ceiling")
    capped = _cap(strength, ceiling)
    if capped != strength:
        steps.append(f"CSpec strength ceiling applied: {ceiling}")
    return capped


def assess_pvs1(
    *,
    consequence_profile: dict[str, Any] | None,
    pvs1_facts: dict[str, Any] | None = None,
    rule_override: dict[str, Any] | None = None,
) -> EvidenceCard:
    """Assess PVS1 with the deterministic ClinGen SVI decision tree."""
    profile = dict(consequence_profile or {})
    facts = dict(pvs1_facts or {})
    contract = _pvs1_contract(rule_override)
    applicability = consequence_applicability("PVS1", profile)
    steps: list[str] = []
    if applicability["status"] != "applicable":
        return _card(
            "not_applicable", profile, facts, contract, [applicability["reason"]]
        )

    mechanism = _mechanism_from_facts(facts, contract, steps)
    if mechanism is False:
        return _card("not_applicable", profile, facts, contract, steps)
    if mechanism is not True:
        return _card("not_assessed", profile, facts, contract, steps)

    terms = {_norm(term) for term in profile.get("selected_transcript_terms") or ()}
    if profile.get("protein_effect") == "lof" and terms & _TRUNCATING_TERMS:
        steps.append("nonsense/frameshift route")
        strength = _truncating_branch(profile, facts, contract, steps)
    elif terms & _START_LOST_TERMS:
        steps.append("initiation-codon route")
        strength = _start_lost_branch(profile, facts, contract, steps)
    elif str(profile.get("splice_class") or "") == "canonical":
        steps.append("canonical splice-site route")
        strength = _canonical_splice_branch(profile, facts, contract, steps)
    else:
        steps.append(
            "PVS1 route unresolved: exon deletions, transcript ablation and "
            "other LoF classes require curated exon-level facts"
        )
        strength = "not_assessed"
    return _card(strength, profile, facts, contract, steps)


def _card(
    strength: str,
    profile: dict[str, Any],
    facts: dict[str, Any],
    contract: dict[str, Any] | None,
    steps: list[str],
) -> EvidenceCard:
    observed_facts: dict[str, Any] = {
        **facts,
        "consequence_profile": profile,
    }
    card = EvidenceCard(
        criterion="PVS1",
        strength=strength,
        source_label="PVS1 decision tree facts",
        observed_facts=observed_facts,
        rule_basis=RULE_BASIS,
        rule_id=RULE_ID,
        rule_version=RULE_VERSION,
        rule_reference=RULE_REFERENCE,
        provenance_chain=[str(step) for step in steps if step],
    )
    if contract is not None:
        observed_facts["cspec_contract_applied"] = dict(contract)
    return card


__all__ = ["assess_pvs1", "infer_mechanism_from_population_facts"]
