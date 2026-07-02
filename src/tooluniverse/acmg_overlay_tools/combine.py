"""ACMG evidence combination tool.

MCP tool: acmg_combine_criteria

Wraps semantic_combiner.py to aggregate overlay results into a five-tier
ACMG classification (Pathogenic / Likely Pathogenic / VUS /
Likely Benign / Benign).
"""

from __future__ import annotations

from typing import Any


def combine_criteria(
    criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    """Combine overlay results into a five-tier ACMG classification.

    Args:
        criteria: List of overlay tool outputs, each with 'criterion', 'strength',
                  'status', 'counted', 'overlay_validated' fields.

    Returns:
        Dict with computed_classification, semantic_combiner_status,
        counted_criteria, explanation, next_steps.
    """
    # Count only overlay-validated evidence
    counted = [
        c for c in criteria
        if isinstance(c, dict)
        and c.get("counted") is True
        and c.get("overlay_validated") is True
    ]

    if not counted:
        return {
            "computed_classification": "VUS",
            "semantic_combiner_status": "NOT_APPLICABLE",
            "counted_criteria": [],
            "not_counted": len(criteria) - len(counted),
            "explanation": "No overlay-validated counted evidence. Classification cannot be determined.",
            "next_steps": [
                "Collect population frequency data for PM2 assessment",
                "Retrieve computational predictions for PP3/BP4",
                "Search literature for functional and segregation evidence",
            ],
        }

    # Count strengths
    very_strong = 0  # PVS1
    strong = 0       # PS1-PS4
    moderate = 0     # PM1-PM6
    supporting = 0   # PP1-PP5
    benign_standalone = 0  # BA1
    benign_strong = 0      # BS1-BS4
    benign_supporting = 0  # BP1-BP7

    for c in counted:
        strength = str(c.get("strength", ""))
        if strength in ("PVS1", "very_strong"):
            very_strong += 1
        elif strength == "PVS1_Strong":
            strong += 1
        elif strength in ("PS1", "PS2", "PS3", "PS4"):
            strong += 1
        elif strength in ("PS1_Supporting", "PS2_Supporting", "PS3_Supporting", "PS4_Supporting"):
            supporting += 1
        elif strength.startswith("PM"):
            if "Supporting" in strength:
                supporting += 1
            else:
                moderate += 1
        elif strength.startswith("PP"):
            supporting += 1
        elif strength == "BA1":
            benign_standalone += 1
        elif strength.startswith("BS"):
            benign_strong += 1
        elif strength.startswith("BP"):
            benign_supporting += 1

    # Classification rules per ACMG/AMP 2015

    # Benign path
    if benign_standalone >= 1:
        return _result("Benign", "PASS", counted,
            f"BA1 stand-alone benign. {benign_standalone} BA1 criteria met. "
            "No further analysis needed.",
            [])

    if benign_strong >= 2:
        return _result("Benign", "PASS", counted,
            f"2 benign strong criteria ({benign_strong} BS). Benign classification.",
            [])

    if benign_strong >= 1 and benign_supporting >= 1:
        return _result("Likely Benign", "PASS", counted,
            f"1 strong benign ({benign_strong} BS) + {benign_supporting} "
            "benign supporting. Likely Benign.",
            [])

    if benign_supporting >= 2:
        return _result("Likely Benign", "PASS", counted,
            f"{benign_supporting} benign supporting criteria. Likely Benign.",
            [])

    # Pathogenic path
    if very_strong >= 1 and (strong >= 1 or moderate >= 2 or
                             (moderate >= 1 and supporting >= 1) or
                             supporting >= 2):
        return _result("Pathogenic", "PASS", counted,
            f"PVS1 + sufficient additional evidence: S={strong}, M={moderate}, "
            f"P={supporting}. Pathogenic.",
            [])

    if strong >= 2:
        return _result("Pathogenic", "PASS", counted,
            f"2 strong pathogenic criteria. Pathogenic.",
            [])

    if strong >= 1 and moderate >= 1:
        return _result("Likely Pathogenic", "PASS", counted,
            f"1 strong + 1 moderate. Likely Pathogenic.",
            [])

    if strong >= 1 and supporting >= 2:
        return _result("Likely Pathogenic", "PASS", counted,
            f"1 strong + 2 supporting. Likely Pathogenic.",
            [])

    if moderate >= 3:
        return _result("Likely Pathogenic", "PASS", counted,
            f"3 moderate criteria. Likely Pathogenic.",
            [])

    if moderate >= 2 and supporting >= 2:
        return _result("Likely Pathogenic", "PASS", counted,
            f"2 moderate + 2 supporting. Likely Pathogenic.",
            [])

    if very_strong >= 1 and moderate >= 1:
        return _result("Likely Pathogenic", "PASS", counted,
            f"PVS1 + 1 moderate. Likely Pathogenic.",
            [])

    # PVS1 (any strength) + PM2_Supporting = Likely Pathogenic (ClinGen SVI)
    pvs1_met = very_strong >= 1 or any(
        c.get("criterion") == "PVS1" and "Strong" in str(c.get("strength", ""))
        for c in counted
    )
    if pvs1_met and any(
        c.get("criterion") == "PM2" and "Supporting" in str(c.get("strength", ""))
        for c in counted
    ):
        return _result("Likely Pathogenic", "PASS", counted,
            "PVS1 + PM2_Supporting. Per ClinGen SVI PVS1 decision tree: "
            "PVS1 at any strength + PM2_Supporting = Likely Pathogenic.",
            [])

    # VUS — insufficient or conflicting evidence
    next_steps = []
    if very_strong == 0 and strong == 0:
        next_steps.append("Functional assay (PS3) could upgrade classification")
    if moderate == 0:
        next_steps.append("Segregation analysis (PP1) could provide additional evidence")
    if supporting <= 1:
        next_steps.append("Additional evidence needed for classification beyond VUS")

    strengths = f"VS={very_strong}, S={strong}, M={moderate}, P={supporting}"
    return _result("VUS", "PASS", counted,
        f"Insufficient evidence for classification beyond VUS. {strengths}.",
        next_steps)


def _result(
    classification: str,
    status: str,
    counted: list[dict],
    explanation: str,
    next_steps: list[str],
) -> dict[str, Any]:
    return {
        "computed_classification": classification,
        "semantic_combiner_status": status,
        "counted_criteria": [
            f"{c['criterion']}({c.get('strength','?')})"
            for c in counted
        ],
        "counted_criteria_detail": [
            {"criterion": c["criterion"], "strength": c.get("strength", "")}
            for c in counted
        ],
        "explanation": explanation,
        "next_steps": next_steps,
    }


__all__ = ["combine_criteria"]
