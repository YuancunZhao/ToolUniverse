"""PP3/BP4 Missense Prediction overlay tool.

MCP tool: acmg_overlay_pp3_bp4

Per ClinGen SVI guidance and Pejaver 2022 (PMID:36413997) calibration:
REVEL >= 0.932 → PP3_Strong (specificity > 95%)
REVEL >= 0.7   → PP3 (recommended threshold, specificity 90%)
REVEL in (0.290, 0.644) → No PP3/BP4 evidence
REVEL < 0.15 AND CADD < 15 → BP4
REVEL < 0.016 → BP4_Supporting
Discordant predictors → neither PP3 nor BP4 applies.
"""

from __future__ import annotations

from typing import Any


def overlay_pp3_bp4(
    revel_score: float | None = None,
    cadd_phred: float | None = None,
    spliceai_ds_dg: float | None = None,
    sift_score: float | None = None,
    polyphen_score: float | None = None,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """Determine PP3 or BP4 evidence from computational predictors.

    Args:
        revel_score: REVEL score (0-1). Recommended by ClinGen for missense.
        cadd_phred: CADD Phred-scaled score.
        spliceai_ds_dg: SpliceAI donor gain delta score (for splice impact context)
        sift_score: SIFT score (0-1, <0.05 = damaging)
        polyphen_score: PolyPhen-2 score (0-1, >0.9 = probably damaging)
        vcep_override: VCEP-specific rule name
    """
    from .base import output_template

    if vcep_override:
        return output_template("PP3/BP4", vcep_override, reason=f"VCEP override: {vcep_override}")

    # No predictor data
    if revel_score is None and cadd_phred is None and sift_score is None:
        return output_template(
            "PP3/BP4", "not_assessed",
            status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No computational predictor data available.",
            next_action="Retrieve REVEL/CADD/SIFT/PolyPhen scores from MyVariant or Ensembl VEP.",
        )

    # REVEL is the preferred ClinGen predictor
    if revel_score is not None:
        if revel_score >= 0.7:
            return output_template(
                "PP3", "PP3",
                reason=f"REVEL={revel_score:.2f} (>=0.7). "
                       "Per ClinGen SVI: REVEL >= 0.7 alone is sufficient for PP3.",
                source_of_truth="REVEL",
            )
        if revel_score < 0.15 and (cadd_phred is None or cadd_phred < 15):
            return output_template(
                "BP4", "BP4",
                reason=f"REVEL={revel_score:.2f} (<0.15). "
                       "Per ClinGen SVI: REVEL < 0.15 indicates benign prediction.",
                source_of_truth="REVEL",
            )
        # Intermediate REVEL — check concordance
        if cadd_phred is not None and cadd_phred >= 25:
            return output_template(
                "PP3", "PP3",
                reason=f"REVEL={revel_score:.2f} (moderate), CADD={cadd_phred:.0f} (>=25). "
                       "Concordant damaging predictions. PP3 met per ClinGen guidance.",
                source_of_truth="REVEL, CADD",
            )
        if cadd_phred is not None and cadd_phred < 15 and revel_score < 0.5:
            return output_template(
                "BP4", "BP4",
                reason=f"REVEL={revel_score:.2f} (low), CADD={cadd_phred:.0f} (<15). "
                       "Concordant benign predictions. BP4 met.",
                source_of_truth="REVEL, CADD",
            )
        # Discordant
        return output_template(
            "PP3/BP4", "not_met",
            status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason=f"REVEL={revel_score:.2f} intermediate. "
                   "Predictors discordant or uncertain. Neither PP3 nor BP4 applied.",
            source_of_truth="REVEL, CADD",
        )

    # Fallback: no REVEL, use CADD + SIFT + PolyPhen consensus
    damaging = 0
    benign = 0
    if cadd_phred is not None:
        if cadd_phred >= 25:
            damaging += 1
        elif cadd_phred < 15:
            benign += 1
    if sift_score is not None:
        if sift_score <= 0.05:
            damaging += 1
        elif sift_score > 0.5:
            benign += 1
    if polyphen_score is not None:
        if polyphen_score >= 0.9:
            damaging += 1
        elif polyphen_score < 0.5:
            benign += 1

    if damaging >= 2 and benign == 0:
        return output_template(
            "PP3", "PP3",
            reason=f"Multiple predictors agree damaging: "
                   f"damaging={damaging}, benign={benign}. PP3 met.",
            source_of_truth="CADD, SIFT, PolyPhen-2",
        )
    if benign >= 2 and damaging == 0:
        return output_template(
            "BP4", "BP4",
            reason=f"Multiple predictors agree benign: "
                   f"damaging={damaging}, benign={benign}. BP4 met.",
            source_of_truth="CADD, SIFT, PolyPhen-2",
        )

    return output_template(
        "PP3/BP4", "not_met",
        status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"Predictors discordant or insufficient. "
               f"damaging={damaging}, benign={benign}. Neither PP3 nor BP4 applied.",
        source_of_truth="CADD, SIFT, PolyPhen-2",
        next_action="REVEL score preferred per ClinGen. Use MyVariant to retrieve REVEL.",
    )


__all__ = ["overlay_pp3_bp4"]
