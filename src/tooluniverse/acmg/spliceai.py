"""Normalize SpliceAI delta scores without conflating event channels."""

from __future__ import annotations

import math
import re
from typing import Any


DELTA_CHANNELS = ("DS_AG", "DS_AL", "DS_DG", "DS_DL")
POSITION_CHANNELS = ("DP_AG", "DP_AL", "DP_DG", "DP_DL")
EVENT_NAMES = {
    "DS_AG": "acceptor_gain",
    "DS_AL": "acceptor_loss",
    "DS_DG": "donor_gain",
    "DS_DL": "donor_loss",
}
NATIVE_LOSS_CHANNELS = {"acceptor": "DS_AL", "donor": "DS_DL"}
GAIN_CHANNELS = ("DS_AG", "DS_DG")
DEFAULT_INTERPRETATION_THRESHOLD = 0.5
PLUS_2_T_TO_C_THRESHOLD = 0.8
CANONICAL_GAIN_WINDOW = 20
_MAX_TOLERANCE = 1e-12
_PLUS_2_T_TO_C_RE = re.compile(r"\+2T>C(?:$|[;)])", re.IGNORECASE)


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _position(value: Any, distance: int) -> int | None:
    number = _finite_float(value)
    if number is None or not number.is_integer():
        return None
    position = int(number)
    return position if abs(position) <= distance else None


def normalize_spliceai_profile(
    score_row: dict[str, Any] | None,
    *,
    provider_max_delta_score: Any = None,
    distance: int = 500,
) -> dict[str, Any]:
    """Return one validated profile from the identity-selected score row."""
    row = dict(score_row or {})
    deltas: dict[str, float] = {}
    positions: dict[str, int] = {}
    issues: list[str] = []

    for channel in DELTA_CHANNELS:
        value = _finite_float(row.get(channel))
        if value is None:
            issues.append(f"missing_or_invalid_{channel}")
        elif not 0.0 <= value <= 1.0:
            issues.append(f"out_of_range_{channel}")
        else:
            deltas[channel] = value
    for channel in POSITION_CHANNELS:
        value = _position(row.get(channel), distance)
        if value is None:
            issues.append(f"missing_or_invalid_{channel}")
        else:
            positions[channel] = value

    if not row:
        status = "unavailable"
    elif len(deltas) != len(DELTA_CHANNELS) or len(positions) != len(POSITION_CHANNELS):
        status = "incomplete"
    else:
        status = "resolved"

    max_delta: float | None = None
    max_channels: list[str] = []
    if len(deltas) == len(DELTA_CHANNELS):
        max_delta = max(deltas.values())
        max_channels = [
            channel
            for channel in DELTA_CHANNELS
            if math.isclose(
                deltas[channel],
                max_delta,
                rel_tol=0.0,
                abs_tol=_MAX_TOLERANCE,
            )
        ]

    provider_max = _finite_float(provider_max_delta_score)
    if provider_max_delta_score not in (None, "") and provider_max is None:
        issues.append("invalid_provider_max_delta_score")
        status = "conflicting"
    elif provider_max is not None and (
        max_delta is None
        or not math.isclose(
            provider_max,
            max_delta,
            rel_tol=0.0,
            abs_tol=_MAX_TOLERANCE,
        )
    ):
        issues.append("provider_max_delta_score_mismatch")
        status = "conflicting"

    return {
        "status": status,
        "delta_scores": deltas,
        "delta_positions": positions,
        "max_delta_score": max_delta,
        "max_delta_channels": max_channels,
        "max_delta_events": [EVENT_NAMES[channel] for channel in max_channels],
        "provider_max_delta_score": provider_max,
        "canonical_site_type": "none",
        "native_loss_channel": None,
        "native_loss_score": None,
        "native_loss_position_channel": None,
        "native_loss_position": None,
        "native_loss_event_coordinate": None,
        "native_loss_threshold": None,
        "native_loss_threshold_reason": None,
        "native_loss_position_status": "unavailable",
        "native_loss_supported": None,
        "gain_interpretation_window_bp": CANONICAL_GAIN_WINDOW,
        "supported_gain_events": [],
        "out_of_window_gain_events": [],
        "selected_gene": next(
            (
                str(row[key]).strip()
                for key in ("gene", "gene_symbol", "symbol", "g_name")
                if row.get(key) not in (None, "")
            ),
            "",
        ),
        "selected_transcript": next(
            (
                str(row[key]).strip()
                for key in ("transcript", "transcript_id", "t_id")
                if row.get(key) not in (None, "")
            ),
            "",
        ),
        "transcript_strand": str(row.get("t_strand") or row.get("strand") or ""),
        "issues": issues,
    }


def bind_spliceai_site(
    profile: dict[str, Any] | None,
    canonical_site_type: Any,
    *,
    hgvs_c: Any = None,
    variant_position: Any = None,
    canonical_site_position: Any = None,
) -> dict[str, Any]:
    """Bind selected-transcript splice context to DS/DP interpretation.

    DP signs follow genomic coordinates and are not inverted for transcript
    strand. Loss is interpreted from the site-specific channel; gain events
    are usable only in the canonical +/-20 bp review window.
    """
    bound = dict(profile or {})
    site_type = str(canonical_site_type or "none").strip().casefold()
    if site_type not in {"donor", "acceptor", "ambiguous", "none"}:
        site_type = "ambiguous"
    bound["canonical_site_type"] = site_type
    channel = NATIVE_LOSS_CHANNELS.get(site_type)
    deltas = bound.get("delta_scores")
    deltas = deltas if isinstance(deltas, dict) else {}
    positions = bound.get("delta_positions")
    positions = positions if isinstance(positions, dict) else {}
    bound["native_loss_channel"] = channel
    bound["native_loss_score"] = deltas.get(channel) if channel else None
    position_channel = channel.replace("DS_", "DP_") if channel else None
    native_position = positions.get(position_channel) if position_channel else None
    bound["native_loss_position_channel"] = position_channel
    bound["native_loss_position"] = native_position

    genomic_position = _position(variant_position, 1_000_000_000)
    canonical_position = _position(canonical_site_position, 1_000_000_000)
    bound["variant_genomic_position"] = genomic_position
    bound["canonical_site_genomic_position"] = canonical_position
    bound["native_loss_event_coordinate"] = (
        genomic_position + native_position
        if genomic_position is not None and native_position is not None
        else None
    )
    bound["expected_native_loss_position"] = (
        canonical_position - genomic_position
        if canonical_position is not None and genomic_position is not None
        else None
    )

    special_plus_2 = bool(_PLUS_2_T_TO_C_RE.search(str(hgvs_c or "")))
    threshold = (
        PLUS_2_T_TO_C_THRESHOLD if special_plus_2 else DEFAULT_INTERPRETATION_THRESHOLD
    )
    bound["native_loss_threshold"] = threshold
    bound["native_loss_threshold_reason"] = (
        "canonical_plus_2_T_to_C"
        if special_plus_2
        else "general_spliceai_interpretation"
    )
    if native_position is None:
        position_status = "unavailable"
    elif (
        canonical_position is not None
        and bound["native_loss_event_coordinate"] == canonical_position
    ):
        position_status = "exact_selected_transcript_site"
    elif canonical_position is not None:
        position_status = "selected_transcript_site_mismatch"
    elif abs(native_position) <= CANONICAL_GAIN_WINDOW:
        position_status = "within_canonical_20bp_window"
    else:
        position_status = "outside_canonical_20bp_window"
    bound["native_loss_position_status"] = position_status
    native_score = bound["native_loss_score"]
    if (
        bound.get("status") != "resolved"
        or channel is None
        or native_score is None
        or native_position is None
    ):
        bound["native_loss_supported"] = None
    elif position_status not in {
        "exact_selected_transcript_site",
        "within_canonical_20bp_window",
    }:
        bound["native_loss_supported"] = None
    else:
        bound["native_loss_supported"] = native_score >= threshold

    supported_gains: list[dict[str, Any]] = []
    out_of_window_gains: list[dict[str, Any]] = []
    for gain_channel in GAIN_CHANNELS:
        gain_score = deltas.get(gain_channel)
        gain_position_channel = gain_channel.replace("DS_", "DP_")
        gain_position = positions.get(gain_position_channel)
        if gain_score is None or gain_position is None:
            continue
        event = {
            "event": EVENT_NAMES[gain_channel],
            "score_channel": gain_channel,
            "score": gain_score,
            "position_channel": gain_position_channel,
            "position": gain_position,
            "event_coordinate": (
                genomic_position + gain_position
                if genomic_position is not None
                else None
            ),
            "distance_from_canonical_site": (
                genomic_position + gain_position - canonical_position
                if genomic_position is not None and canonical_position is not None
                else gain_position
            ),
            "threshold": DEFAULT_INTERPRETATION_THRESHOLD,
        }
        if gain_score < DEFAULT_INTERPRETATION_THRESHOLD:
            continue
        if abs(event["distance_from_canonical_site"]) <= CANONICAL_GAIN_WINDOW:
            supported_gains.append(event)
        else:
            out_of_window_gains.append(event)
    bound["gain_interpretation_window_bp"] = CANONICAL_GAIN_WINDOW
    bound["supported_gain_events"] = supported_gains
    bound["out_of_window_gain_events"] = out_of_window_gains
    return bound


def normalize_spliceai_inputs(
    *,
    spliceai_profile: dict[str, Any] | None = None,
    spliceai_scores: dict[str, Any] | None = None,
    spliceai_max_delta: Any = None,
    canonical_site_type: Any = None,
    hgvs_c: Any = None,
    variant_position: Any = None,
    canonical_site_position: Any = None,
    distance: int = 500,
) -> dict[str, Any]:
    """Normalize public computational-tool inputs and validate an explicit maximum."""
    supplied_profile = dict(spliceai_profile or {})
    if supplied_profile:
        row = {
            **dict(supplied_profile.get("delta_scores") or {}),
            **dict(supplied_profile.get("delta_positions") or {}),
        }
        claimed_profile_max = supplied_profile.get("max_delta_score")
        provider_max = supplied_profile.get("provider_max_delta_score")
    else:
        row = dict(spliceai_scores or {})
        claimed_profile_max = None
        provider_max = None
    profile = normalize_spliceai_profile(
        row,
        provider_max_delta_score=provider_max,
        distance=distance,
    )
    if supplied_profile:
        for key in ("selected_gene", "selected_transcript", "transcript_strand"):
            if supplied_profile.get(key) not in (None, ""):
                profile[key] = supplied_profile[key]
    profile = bind_spliceai_site(
        profile,
        canonical_site_type,
        hgvs_c=hgvs_c,
        variant_position=variant_position,
        canonical_site_position=canonical_site_position,
    )

    expected = profile.get("max_delta_score")
    explicit_max = _finite_float(spliceai_max_delta)
    issues = list(profile.get("issues") or [])
    claimed_max = _finite_float(claimed_profile_max)
    if supplied_profile and (
        claimed_max is None
        or expected is None
        or not math.isclose(
            claimed_max,
            expected,
            rel_tol=0.0,
            abs_tol=_MAX_TOLERANCE,
        )
    ):
        issues.append("spliceai_profile_max_delta_conflict")
    if spliceai_max_delta not in (None, ""):
        if explicit_max is None:
            issues.append("invalid_spliceai_max_delta")
        elif expected is not None and not math.isclose(
            explicit_max,
            expected,
            rel_tol=0.0,
            abs_tol=_MAX_TOLERANCE,
        ):
            issues.append("spliceai_max_delta_conflict")
    if any(
        "conflict" in issue or issue.startswith("invalid_spliceai") for issue in issues
    ):
        profile["status"] = "conflicting"
    profile["issues"] = list(dict.fromkeys(issues))
    profile["explicit_max_delta_score"] = explicit_max
    return profile


__all__ = [
    "DELTA_CHANNELS",
    "DEFAULT_INTERPRETATION_THRESHOLD",
    "GAIN_CHANNELS",
    "POSITION_CHANNELS",
    "PLUS_2_T_TO_C_THRESHOLD",
    "bind_spliceai_site",
    "normalize_spliceai_inputs",
    "normalize_spliceai_profile",
]
