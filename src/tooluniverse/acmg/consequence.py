"""Normalize selected-transcript consequences and route ACMG review criteria."""

from __future__ import annotations

import re
from typing import Any

from .rule_catalog import consequence_policy_for


_LOF_TERMS = {
    "frameshift_variant",
    "stop_gained",
    "start_lost",
    "transcript_ablation",
}
_INFRAME_TERMS = {"inframe_insertion", "inframe_deletion"}
_MISSENSE_TERMS = {"missense_variant"}
_SYNONYMOUS_TERMS = {"synonymous_variant", "stop_retained_variant"}
_NONCODING_TERMS = {
    "intron_variant",
    "5_prime_utr_variant",
    "3_prime_utr_variant",
    "non_coding_transcript_exon_variant",
    "non_coding_transcript_variant",
    "regulatory_region_variant",
    "upstream_gene_variant",
    "downstream_gene_variant",
}
_CANONICAL_SPLICE_TERMS = {"splice_acceptor_variant", "splice_donor_variant"}
_NONCANONICAL_SPLICE_TERMS = {"splice_region_variant"}
_KNOWN_TERMS = (
    _LOF_TERMS
    | _INFRAME_TERMS
    | _MISSENSE_TERMS
    | _SYNONYMOUS_TERMS
    | _NONCODING_TERMS
    | _CANONICAL_SPLICE_TERMS
    | _NONCANONICAL_SPLICE_TERMS
    | {"stop_lost"}
)
_PROTEIN_POSITION_RE = re.compile(r"p\.\(?[A-Za-z*]{1,3}(\d+)")
_ALL_SPLICE_OFFSETS_RE = re.compile(r"\d+(?P<offset>[+-]\d+)", re.IGNORECASE)


def _normalized(value: Any) -> str:
    return str(value or "").strip().casefold()


def _accession(value: Any) -> str:
    return str(value or "").strip().split(":", 1)[0]


def _candidate_matches_transcript(candidate: dict[str, Any], transcript: str) -> bool:
    expected = _normalized(transcript)
    if not expected:
        return False
    values = {
        _normalized(candidate.get("transcript")),
        _normalized(candidate.get("mane_select")),
        _normalized(candidate.get("mane_plus_clinical")),
        _normalized(_accession(candidate.get("hgvsc"))),
    }
    return expected in values


def _protein_position(*values: Any) -> int | None:
    for value in values:
        match = _PROTEIN_POSITION_RE.search(str(value or ""))
        if match:
            return int(match.group(1))
    return None


def _splice_offsets(hgvs_c: str) -> list[int]:
    offsets: list[int] = []
    for match in _ALL_SPLICE_OFFSETS_RE.finditer(str(hgvs_c or "")):
        offset = int(match.group("offset"))
        if offset not in offsets:
            offsets.append(offset)
    return offsets


def _hgvs_operation(hgvs_c: str) -> str:
    expression = str(hgvs_c or "").split(":", 1)[-1].casefold()
    if "delins" in expression:
        return "delins"
    if "dup" in expression:
        return "duplication"
    if "ins" in expression:
        return "insertion"
    if "inv" in expression:
        return "inversion"
    if "del" in expression:
        return "deletion"
    if ">" in expression:
        return "substitution"
    if expression.endswith("="):
        return "no_change"
    return "unknown"


def _canonical_site_type(terms: set[str], offsets: list[int]) -> str:
    donor = "splice_donor_variant" in terms
    acceptor = "splice_acceptor_variant" in terms
    if donor and acceptor:
        return "ambiguous"
    offset_types = {
        "donor" if offset > 0 else "acceptor"
        for offset in offsets
        if offset in {-2, -1, 1, 2}
    }
    if donor:
        return "ambiguous" if offset_types - {"donor"} else "donor"
    if acceptor:
        return "ambiguous" if offset_types - {"acceptor"} else "acceptor"
    if len(offset_types) == 1:
        return next(iter(offset_types))
    return "ambiguous" if offset_types else "none"


def _canonical_motif_effect(
    splice_class: str,
    operation: str,
    site_type: str,
) -> tuple[str, str]:
    if splice_class != "canonical":
        return "not_applicable", "variant is not in the canonical splice route"
    if site_type == "ambiguous":
        return "unknown", "donor/acceptor identity is ambiguous"
    if operation in {"substitution", "deletion", "delins"}:
        return "disrupted", f"canonical motif is altered by HGVS {operation}"
    if operation in {"duplication", "insertion"}:
        return (
            "potentially_preserved",
            f"HGVS {operation} may leave or recreate a native splice motif",
        )
    return "unknown", f"HGVS {operation} does not prove canonical motif disruption"


def build_consequence_profile(
    identity: dict[str, Any],
    vep_features: dict[str, Any] | None,
    *,
    source_fact_ids: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build one consequence profile from the identity-selected transcript."""
    features = dict(vep_features or {})
    transcript = str(identity.get("transcript") or "")
    gene = _normalized(identity.get("gene"))
    candidates = [
        dict(row)
        for row in features.get("vep_transcript_candidates") or []
        if isinstance(row, dict)
    ]
    gene_candidates = [
        row
        for row in candidates
        if not gene or not row.get("gene") or _normalized(row.get("gene")) == gene
    ]
    selected = [
        row for row in gene_candidates if _candidate_matches_transcript(row, transcript)
    ]
    ignored = [row for row in candidates if row not in selected]
    selected_terms = sorted(
        {
            _normalized(term)
            for row in selected
            for term in row.get("consequence") or ()
            if _normalized(term)
        }
    )
    hgvsc_values = {str(row.get("hgvsc") or "") for row in selected if row.get("hgvsc")}
    hgvsp_values = {str(row.get("hgvsp") or "") for row in selected if row.get("hgvsp")}
    hgvs_c = next(iter(hgvsc_values), "") or str(
        identity.get("validated_hgvs_c") or identity.get("hgvs_c") or ""
    )
    hgvs_p = next(iter(hgvsp_values), "") or str(identity.get("hgvs_p") or "")

    protein_categories = set()
    terms = set(selected_terms)
    if terms & _LOF_TERMS:
        protein_categories.add("lof")
    if terms & _INFRAME_TERMS:
        protein_categories.add("inframe")
    if terms & _MISSENSE_TERMS:
        protein_categories.add("missense")
    if terms & _SYNONYMOUS_TERMS:
        protein_categories.add("synonymous")
    if terms & _NONCODING_TERMS:
        protein_categories.add("noncoding")
    offsets = _splice_offsets(hgvs_c)
    offset = next(iter(offsets), None)
    if terms & _CANONICAL_SPLICE_TERMS or offset in {-2, -1, 1, 2}:
        splice_class = "canonical"
    elif terms & _NONCANONICAL_SPLICE_TERMS or (
        offset is not None and offset not in {-2, -1, 1, 2}
    ):
        splice_class = "noncanonical"
    elif selected_terms:
        splice_class = "none"
    else:
        splice_class = "unresolved"
    operation = _hgvs_operation(hgvs_c)
    site_type = _canonical_site_type(terms, offsets)
    motif_effect, motif_reason = _canonical_motif_effect(
        splice_class,
        operation,
        site_type,
    )

    coordinates = identity.get("coordinates")
    ref = str(coordinates.get("ref") or "") if isinstance(coordinates, dict) else ""
    alt = str(coordinates.get("alt") or "") if isinstance(coordinates, dict) else ""
    is_small_variant = bool(ref and alt and max(len(ref), len(alt)) <= 50)

    unknown_terms = terms - _KNOWN_TERMS
    conflict = (
        len(hgvsc_values) > 1
        or len(hgvsp_values) > 1
        or len(protein_categories) > 1
        or bool(unknown_terms)
    )
    if conflict or (transcript and not selected and candidates):
        status = "ambiguous"
    elif selected and selected_terms:
        status = "resolved"
    else:
        status = "unavailable"
    protein_effect = (
        next(iter(protein_categories)) if len(protein_categories) == 1 else "unresolved"
    )
    return {
        "status": status,
        "selected_transcript": transcript,
        "selected_transcript_terms": selected_terms,
        "unrecognized_transcript_terms": sorted(unknown_terms),
        "ignored_transcript_terms": [
            {
                "transcript": row.get("transcript"),
                "mane_select": row.get("mane_select"),
                "consequence_terms": list(row.get("consequence") or ()),
                "reason": "not_selected_identity_transcript",
            }
            for row in ignored
        ],
        "most_severe_consequence": features.get("most_severe_consequence"),
        "protein_effect": protein_effect,
        "splice_class": splice_class,
        "splice_position": offset,
        "splice_positions": offsets,
        "canonical_site_type": site_type,
        "canonical_motif_effect": motif_effect,
        "canonical_motif_effect_reason": motif_reason,
        # Compatibility keeps canonical_motif_effect, but this field makes
        # explicit that HGVS/REF/ALT describes sequence structure. Functional
        # native-site loss is assessed separately from SpliceAI DS/DP.
        "canonical_motif_sequence_status": motif_effect,
        "canonical_motif_sequence_reason": motif_reason,
        "hgvs_operation": operation,
        "is_small_variant": is_small_variant,
        "genomic_position": (
            coordinates.get("pos") if isinstance(coordinates, dict) else None
        ),
        "genomic_ref": ref,
        "genomic_alt": alt,
        "hgvs_c": hgvs_c,
        "hgvs_p": hgvs_p,
        "protein_position": _protein_position(hgvs_p, identity.get("hgvs_p")),
        "source_fact_ids": [str(value) for value in source_fact_ids if value],
    }


def consequence_applicability(
    criterion: str,
    profile: dict[str, Any] | None,
    *,
    cspec_criterion: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return consequence-only applicability without assessing evidence strength."""
    policy = consequence_policy_for(criterion)
    mode = str(policy.get("mode") or "requires_context")
    if mode == "deprecated":
        return {"status": "deprecated", "reason": "criterion_deprecated"}
    if mode == "not_consequence_gated":
        return {
            "status": "not_consequence_gated",
            "reason": "criterion_uses_non_consequence_evidence",
        }
    profile = dict(profile or {})
    if profile.get("status") != "resolved":
        return {
            "status": "requires_context",
            "reason": f"consequence_profile_{profile.get('status') or 'unavailable'}",
        }

    effect = str(profile.get("protein_effect") or "unresolved")
    splice_class = str(profile.get("splice_class") or "unresolved")
    terms = {
        str(value).casefold()
        for value in profile.get("selected_transcript_terms") or []
    }

    if criterion == "PM1" and isinstance(cspec_criterion, dict):
        allowed = {
            str(value).casefold()
            for value in cspec_criterion.get("variant_types") or ()
        }
        if allowed and (effect in allowed or bool(terms & allowed)):
            return {
                "status": "applicable",
                "reason": "exact_cspec_consequence_override",
            }

    allowed_effects = set(policy.get("protein_effects") or ())
    allowed_splice = set(policy.get("splice_classes") or ())
    allowed_terms = set(policy.get("terms") or ())
    applies = bool(
        (allowed_effects and effect in allowed_effects)
        or (allowed_splice and splice_class in allowed_splice)
        or (allowed_terms and terms & allowed_terms)
    )
    return {
        "status": "applicable" if applies else "not_applicable",
        "reason": (
            f"matched_{criterion.lower()}_consequence_policy"
            if applies
            else f"consequence_not_supported_for_{criterion.lower()}"
        ),
    }


__all__ = ["build_consequence_profile", "consequence_applicability"]
