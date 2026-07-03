"""PP3/BP4 missense-prediction overlay tool.

MCP tool: ACMG_overlay_pp3_bp4

Implements the Pejaver et al. 2022 ClinGen SVI calibrated score intervals
(PMID:36413997). This is not a predictor-voting tool: callers must provide an
explicit selection_policy. Pre-specified predictors use ClinGen/SVI interval
authority, VCEP-specific selections remain VCEP-specific, and the built-in
hierarchy is available only as practice/local refinement.
"""

from __future__ import annotations

from typing import Any


def _interval(
    criterion: str,
    strength: str,
    lower: float | None = None,
    upper: float | None = None,
    *,
    lower_inclusive: bool = False,
    upper_inclusive: bool = False,
) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "strength": strength,
        "lower": lower,
        "upper": upper,
        "lower_inclusive": lower_inclusive,
        "upper_inclusive": upper_inclusive,
    }


CALIBRATED_INTERVALS: dict[str, list[dict[str, Any]]] = {
    "bayesdel_noaf": [
        _interval("BP4", "BP4_Moderate", upper=-0.36, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=-0.36, upper=-0.18, upper_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=0.13, upper=0.27, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=0.27, upper=0.50, lower_inclusive=True),
        _interval("PP3", "PP3_Strong", lower=0.50, lower_inclusive=True),
    ],
    "cadd": [
        _interval("BP4", "BP4_Strong", upper=0.15, upper_inclusive=True),
        _interval("BP4", "BP4_Moderate", lower=0.15, upper=17.3, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=17.3, upper=22.7, upper_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=25.3, upper=28.1, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=28.1, lower_inclusive=True),
    ],
    "evolutionary_action": [
        _interval("BP4", "BP4_Moderate", upper=0.069, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=0.069, upper=0.262, upper_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=0.685, upper=0.821, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=0.821, lower_inclusive=True),
    ],
    "fathmm": [
        _interval("BP4", "BP4_Moderate", lower=4.69, lower_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=3.32, upper=4.69, lower_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=-5.04, upper=-4.14, lower_inclusive=False, upper_inclusive=True),
        _interval("PP3", "PP3_Moderate", upper=-5.04, upper_inclusive=True),
    ],
    "gerp": [
        _interval("BP4", "BP4_Moderate", upper=-4.54, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=-4.54, upper=2.70, upper_inclusive=True),
    ],
    "mpc": [
        _interval("PP3", "PP3_Supporting", lower=1.360, upper=1.828, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=1.828, lower_inclusive=True),
    ],
    "mutpred2": [
        _interval("BP4", "BP4_Strong", upper=0.010, upper_inclusive=True),
        _interval("BP4", "BP4_Moderate", lower=0.010, upper=0.197, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=0.197, upper=0.391, upper_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=0.737, upper=0.829, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=0.829, upper=0.932, lower_inclusive=True),
        _interval("PP3", "PP3_Strong", lower=0.932, lower_inclusive=True),
    ],
    "phylop": [
        _interval("BP4", "BP4_Moderate", upper=0.021, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=0.021, upper=1.879, upper_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=7.367, upper=9.741, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=9.741, lower_inclusive=True),
    ],
    "polyphen2_humvar": [
        _interval("BP4", "BP4_Moderate", upper=0.009, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=0.009, upper=0.113, upper_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=0.978, upper=0.999, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=0.999, lower_inclusive=True),
    ],
    "primateai": [
        _interval("BP4", "BP4_Moderate", upper=0.362, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=0.362, upper=0.483, upper_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=0.790, upper=0.867, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=0.867, lower_inclusive=True),
    ],
    "revel": [
        _interval("BP4", "BP4_VeryStrong", upper=0.003, upper_inclusive=True),
        _interval("BP4", "BP4_Strong", lower=0.003, upper=0.016, upper_inclusive=True),
        _interval("BP4", "BP4_Moderate", lower=0.016, upper=0.183, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=0.183, upper=0.290, upper_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=0.644, upper=0.773, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=0.773, upper=0.932, lower_inclusive=True),
        _interval("PP3", "PP3_Strong", lower=0.932, lower_inclusive=True),
    ],
    "sift": [
        _interval("BP4", "BP4_Moderate", lower=0.327, lower_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=0.080, upper=0.327, lower_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=0.0, upper=0.001, upper_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=0.0, upper=0.0, lower_inclusive=True, upper_inclusive=True),
    ],
    "vest4": [
        _interval("BP4", "BP4_Moderate", upper=0.302, upper_inclusive=True),
        _interval("BP4", "BP4_Supporting", lower=0.302, upper=0.449, upper_inclusive=True),
        _interval("PP3", "PP3_Supporting", lower=0.764, upper=0.861, lower_inclusive=True),
        _interval("PP3", "PP3_Moderate", lower=0.861, upper=0.965, lower_inclusive=True),
        _interval("PP3", "PP3_Strong", lower=0.965, lower_inclusive=True),
    ],
}

TOOL_ALIASES = {
    "bayesdel": "bayesdel_noaf",
    "bayesdel_noaf": "bayesdel_noaf",
    "bayesdel noaf": "bayesdel_noaf",
    "cadd": "cadd",
    "evolutionary_action": "evolutionary_action",
    "evolutionary action": "evolutionary_action",
    "fathmm": "fathmm",
    "gerp": "gerp",
    "gerp++": "gerp",
    "mpc": "mpc",
    "mutpred2": "mutpred2",
    "phylop": "phylop",
    "polyphen": "polyphen2_humvar",
    "polyphen2": "polyphen2_humvar",
    "polyphen2_humvar": "polyphen2_humvar",
    "polyphen-2 humvar": "polyphen2_humvar",
    "primateai": "primateai",
    "revel": "revel",
    "sift": "sift",
    "vest4": "vest4",
}

DEFAULT_TOOL_HIERARCHY = [
    "revel",
    "bayesdel_noaf",
    "mutpred2",
    "vest4",
    "cadd",
    "evolutionary_action",
    "fathmm",
    "gerp",
    "mpc",
    "phylop",
    "polyphen2_humvar",
    "primateai",
    "sift",
]

EXPLICIT_SELECTION_POLICIES = {"pre_specified", "vcep_specific"}
LOCAL_SELECTION_POLICIES = {"local_default_hierarchy"}


def _canonical_tool_name(value: str | None) -> str | None:
    if not value:
        return None
    return TOOL_ALIASES.get(value.strip().lower().replace("-", "_").replace(" ", "_")) or TOOL_ALIASES.get(value.strip().lower())


def _score_by_tool(
    *,
    revel_score: float | None,
    cadd_phred: float | None,
    sift_score: float | None,
    polyphen_score: float | None,
    bayesdel_noaf_score: float | None,
    mutpred2_score: float | None,
    vest4_score: float | None,
    evolutionary_action_score: float | None,
    fathmm_score: float | None,
    gerp_score: float | None,
    mpc_score: float | None,
    phylop_score: float | None,
    primateai_score: float | None,
) -> dict[str, float]:
    raw = {
        "revel": revel_score,
        "cadd": cadd_phred,
        "sift": sift_score,
        "polyphen2_humvar": polyphen_score,
        "bayesdel_noaf": bayesdel_noaf_score,
        "mutpred2": mutpred2_score,
        "vest4": vest4_score,
        "evolutionary_action": evolutionary_action_score,
        "fathmm": fathmm_score,
        "gerp": gerp_score,
        "mpc": mpc_score,
        "phylop": phylop_score,
        "primateai": primateai_score,
    }
    return {tool: float(score) for tool, score in raw.items() if score is not None}


def _in_interval(score: float, interval: dict[str, Any]) -> bool:
    lower = interval["lower"]
    upper = interval["upper"]
    if lower is not None:
        if interval["lower_inclusive"]:
            if score < lower:
                return False
        elif score <= lower:
            return False
    if upper is not None:
        if interval["upper_inclusive"]:
            if score > upper:
                return False
        elif score >= upper:
            return False
    return True


def _format_interval(interval: dict[str, Any]) -> str:
    lower = interval["lower"]
    upper = interval["upper"]
    if lower is None:
        return f"<= {upper}"
    if upper is None:
        return f">= {lower}"
    left = "[" if interval["lower_inclusive"] else "("
    right = "]" if interval["upper_inclusive"] else ")"
    return f"{left}{lower}, {upper}{right}"


def overlay_pp3_bp4(
    revel_score: float | None = None,
    cadd_phred: float | None = None,
    spliceai_ds_dg: float | None = None,
    sift_score: float | None = None,
    polyphen_score: float | None = None,
    bayesdel_noaf_score: float | None = None,
    mutpred2_score: float | None = None,
    vest4_score: float | None = None,
    evolutionary_action_score: float | None = None,
    fathmm_score: float | None = None,
    gerp_score: float | None = None,
    mpc_score: float | None = None,
    phylop_score: float | None = None,
    primateai_score: float | None = None,
    selected_tool: str | None = None,
    selection_policy: str | None = None,
    vcep_override: str | None = None,
) -> dict[str, Any]:
    """Determine PP3 or BP4 evidence from computational predictors.

    Args:
        selected_tool: Calibrated tool chosen by a pre-score selection policy.
        selection_policy: How the selected predictor was chosen. Use
            "pre_specified" or "vcep_specific" with selected_tool, or explicitly
            request "local_default_hierarchy" for this tool's documented local
            fallback hierarchy.
        *_score: Raw score for the selected calibrated predictor.
        spliceai_ds_dg: Accepted for backward compatibility but not used for
            missense PP3/BP4; route splicing prediction to splicing overlays.
        vcep_override: VCEP-specific rule name
    """
    from .base import output_template, vcep_deferred_template

    if vcep_override:
        return vcep_deferred_template(
            "PP3/BP4",
            vcep_override,
            reason=f"VCEP-specific override requested: {vcep_override}. Scope must be validated before final counting.",
        )

    scores = _score_by_tool(
        revel_score=revel_score,
        cadd_phred=cadd_phred,
        sift_score=sift_score,
        polyphen_score=polyphen_score,
        bayesdel_noaf_score=bayesdel_noaf_score,
        mutpred2_score=mutpred2_score,
        vest4_score=vest4_score,
        evolutionary_action_score=evolutionary_action_score,
        fathmm_score=fathmm_score,
        gerp_score=gerp_score,
        mpc_score=mpc_score,
        phylop_score=phylop_score,
        primateai_score=primateai_score,
    )

    if not scores:
        next_action = "Retrieve a Pejaver-calibrated missense predictor score, preferably REVEL, BayesDel noAF, MutPred2, or VEST4."
        if spliceai_ds_dg is not None:
            next_action += " SpliceAI is not used for missense PP3/BP4; route splicing effects to the splicing overlays."
        return output_template(
            "PP3/BP4", "not_assessed",
            status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No Pejaver 2022 calibrated missense predictor score was provided.",
            source_of_truth="Pejaver 2022 ClinGen SVI calibration",
            next_action=next_action,
        )

    policy = str(selection_policy or "").strip().lower()
    selected = _canonical_tool_name(selected_tool)
    if selected_tool and not selected:
        return output_template(
            "PP3/BP4", "not_assessed",
            status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason=f"Selected predictor `{selected_tool}` is not in the Pejaver 2022 calibrated tool table.",
            source_of_truth="Pejaver 2022 ClinGen SVI calibration",
            next_action=f"Use one of: {', '.join(DEFAULT_TOOL_HIERARCHY)}.",
        )

    if selected:
        if policy not in EXPLICIT_SELECTION_POLICIES:
            return output_template(
                "PP3/BP4", "not_assessed",
                status="not_assessed",
                route_outcome="overlay_not_assessed",
                reason="A selected predictor was provided, but selection_policy was not pre_specified or vcep_specific.",
                source_of_truth="Pejaver 2022 ClinGen SVI calibration",
                next_action="Provide selected_tool with selection_policy='pre_specified' or selection_policy='vcep_specific'.",
            )
        if selected not in scores:
            return output_template(
                "PP3/BP4", "not_assessed",
                status="not_assessed",
                route_outcome="overlay_not_assessed",
                reason=f"Selected predictor `{selected}` was specified, but no raw score for that predictor was provided.",
                source_of_truth="Pejaver 2022 ClinGen SVI calibration",
                next_action=f"Provide `{selected}` score or choose another pre-specified calibrated predictor.",
            )
        chosen = selected
        guidance_authority = "VCEP-specific" if policy == "vcep_specific" else "ClinGen/SVI primary"
    else:
        if policy != "local_default_hierarchy":
            return output_template(
                "PP3/BP4", "not_assessed",
                status="not_assessed",
                route_outcome="overlay_not_assessed",
                reason="Predictor scores were provided without an explicit selected_tool or local_default_hierarchy policy.",
                source_of_truth="Pejaver 2022 ClinGen SVI calibration",
                next_action="Provide selected_tool with selection_policy='pre_specified' or explicitly use selection_policy='local_default_hierarchy'.",
            )
        chosen = next((tool for tool in DEFAULT_TOOL_HIERARCHY if tool in scores), None)
        guidance_authority = "practice/local refinement"

    if not chosen:
        return output_template(
            "PP3/BP4", "not_assessed",
            status="not_assessed",
            route_outcome="overlay_not_assessed",
            reason="No supported Pejaver 2022 calibrated predictor score was provided.",
            source_of_truth="Pejaver 2022 ClinGen SVI calibration",
            next_action=f"Provide one of: {', '.join(DEFAULT_TOOL_HIERARCHY)}.",
        )

    score = scores[chosen]
    for interval in CALIBRATED_INTERVALS[chosen]:
        if _in_interval(score, interval):
            interval_text = _format_interval(interval)
            return output_template(
                interval["criterion"],
                interval["strength"],
                guidance_authority=guidance_authority,
                reason=f"{chosen} score={score:g} falls in Pejaver 2022 calibrated interval {interval_text}; "
                       f"applies {interval['strength']}. Other predictors, if present, were not counted by majority vote.",
                source_of_truth=f"{chosen}; Pejaver 2022 ClinGen SVI calibrated thresholds",
            )

    return output_template(
        "PP3/BP4", "not_assessed",
        status="not_assessed",
        route_outcome="overlay_not_assessed",
        reason=f"{chosen} score={score:g} does not fall in a Pejaver 2022 PP3/BP4 evidence interval. "
               "No computational evidence is counted.",
        source_of_truth=f"{chosen}; Pejaver 2022 ClinGen SVI calibrated thresholds",
        next_action="Do not substitute predictor voting. Use VCEP-specific rules if available.",
    )


__all__ = ["overlay_pp3_bp4"]
