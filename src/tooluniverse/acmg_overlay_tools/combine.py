"""ACMG evidence strength summary tool — DRAFT ONLY.

MCP tool: acmg_combine_criteria

Counts and summarizes ACMG criterion strengths from overlay tool outputs.
Does NOT produce a five-tier ACMG classification — that requires the full
validator → semantic_combiner → finalizer → token → guard path.

Output is always draft/preliminary.
"""

from __future__ import annotations

from typing import Any


def combine_criteria(
    criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize ACMG criterion strengths from overlay tool outputs.

    Returns computed_strengths, strength_summary, and next_steps.
    Does NOT return Pathogenic/LP/VUS/LB/Benign — this is a draft-only utility.
    """
    counted = [
        c for c in criteria
        if isinstance(c, dict)
        and c.get("counted") is True
        and c.get("overlay_validated") is True
    ]

    if not counted:
        return {
            "status": "draft",
            "counted_criteria": [],
            "not_counted": len(criteria) - len(counted),
            "strength_summary": "No overlay-validated counted evidence.",
            "next_steps": [
                "Collect population frequency data (gnomAD → ACMG_overlay_pm2)",
                "Retrieve computational predictions (MyVariant → ACMG_overlay_pp3_bp4)",
                "Search PubMed full text for variant-specific functional/segregation evidence",
            ],
        }

    very_strong = 0
    strong = 0
    moderate = 0
    supporting = 0
    benign_standalone = 0
    benign_strong = 0
    benign_supporting = 0

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

    computed_strengths = {
        "pathogenic": {"very_strong": very_strong, "strong": strong, "moderate": moderate, "supporting": supporting},
        "benign": {"standalone": benign_standalone, "strong": benign_strong, "supporting": benign_supporting},
    }

    # Describe the combination per ACMG/AMP 2015 rules without giving a final label
    descriptions = []
    if benign_standalone >= 1:
        descriptions.append("BA1 stand-alone benign criterion met")
    if benign_strong >= 2:
        descriptions.append("≥2 benign strong criteria (BS) — benign path")
    if benign_strong >= 1 and benign_supporting >= 1:
        descriptions.append("1 benign strong + ≥1 benign supporting — likely benign path")
    if benign_supporting >= 2:
        descriptions.append("≥2 benign supporting criteria — likely benign path")

    # PVS1 + PM2_Supporting = LP (ClinGen SVI)
    describing = bool(descriptions)
    pvs1_met = very_strong >= 1 or any(
        c.get("criterion") == "PVS1" and "Strong" in str(c.get("strength", ""))
        for c in counted
    )
    has_pm2_supporting = any(
        c.get("criterion") == "PM2" and "Supporting" in str(c.get("strength", ""))
        for c in counted
    )

    if very_strong >= 1:
        if strong >= 1:
            descriptions.append("PVS1 + strong evidence → meets pathogenic threshold")
        elif moderate >= 2:
            descriptions.append("PVS1 + 2 moderate → meets pathogenic threshold")
        elif moderate >= 1 and supporting >= 1:
            descriptions.append("PVS1 + 1 moderate + ≥1 supporting → meets pathogenic threshold")
        elif supporting >= 2:
            descriptions.append("PVS1 + ≥2 supporting → meets pathogenic threshold")
        elif moderate >= 1:
            descriptions.append("PVS1 + 1 moderate → likely pathogenic (ClinGen SVI)")
        elif pvs1_met and has_pm2_supporting:
            descriptions.append("PVS1 + PM2_Supporting → likely pathogenic (ClinGen SVI PVS1 decision tree)")
        elif not describing:
            descriptions.append("PVS1 alone without additional evidence")

    if strong >= 2:
        descriptions.append("≥2 strong → meets pathogenic threshold")
    if strong >= 1 and moderate >= 1:
        descriptions.append("1 strong + 1 moderate → likely pathogenic")
    if strong >= 1 and supporting >= 2:
        descriptions.append("1 strong + ≥2 supporting → likely pathogenic")
    if moderate >= 3:
        descriptions.append("≥3 moderate → likely pathogenic")
    if moderate >= 2 and supporting >= 2:
        descriptions.append("2 moderate + ≥2 supporting → likely pathogenic")

    if not describing and (very_strong + strong + moderate + supporting) == 0:
        descriptions.append("No pathogenic evidence criteria met")
    elif not describing:
        strengths_text = f"VS={very_strong}, S={strong}, M={moderate}, P={supporting}"
        if (very_strong + strong + moderate + supporting) >= 1:
            descriptions.append(f"Some evidence present ({strengths_text}) but insufficient for any classification")
        else:
            descriptions.append("Insufficient evidence")

    next_steps = []
    if very_strong == 0 and strong == 0:
        next_steps.append("Functional assay (PS3) could upgrade")
    if moderate == 0:
        next_steps.append("Segregation analysis (PP1) could provide additional evidence")
    if supporting <= 1:
        next_steps.append("Additional evidence needed beyond VUS threshold")

    return {
        "status": "draft",
        "computed_strengths": computed_strengths,
        "strength_summary": ", ".join(descriptions),
        "counted_criteria": [
            f"{c['criterion']}({c.get('strength','?')})"
            for c in counted
        ],
        "counted_criteria_detail": [
            {"criterion": c["criterion"], "strength": c.get("strength", "")}
            for c in counted
        ],
        "next_steps": next_steps,
        "final_classification_requires": "validator PASS + semantic_combiner PASS + finalization token + guard",
    }


__all__ = ["combine_criteria"]
