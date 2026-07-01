"""Source-lead sandbox for pre-overlay ACMG evidence inputs."""

from __future__ import annotations

import json
from typing import Any

from .intent_detector import ACMGIntent

FINAL_OR_INTERPRETIVE_KEYS = {
    "acmg_classification",
    "classification",
    "clinical_significance",
    "clinicalSignificance",
    "interpretation",
    "pathogenicity",
    "label",
    "verdict",
    "result",
    "suggestion",
    "recommendation",
    "acmg_criteria",
    "criteria",
    "applied_criteria",
}

SPLICEAI_FEATURE_KEYS = {
    "DS_AG",
    "DS_AL",
    "DS_DG",
    "DS_DL",
    "DP_AG",
    "DP_AL",
    "DP_DG",
    "DP_DL",
    "transcript",
    "genome_build",
    "genome",
    "coordinate",
    "ref",
    "alt",
    "score",
    "predicted_splice_event_type",
    "event_type",
}

PREDICTOR_FEATURE_KEY_PARTS = (
    "score",
    "rank",
    "version",
    "transcript",
    "protein",
    "consequence",
    "phred",
    "raw",
    "model",
    "threshold",
)

CLINVAR_FEATURE_KEYS = {
    "vcv",
    "vcv_id",
    "rcv",
    "rcv_id",
    "variation_id",
    "review_status",
    "stars",
    "submitters",
    "conditions",
    "date",
    "last_evaluated",
    "assertion_criteria",
    "conflicts",
}

GNOMAD_FEATURE_KEYS = {
    "AF",
    "af",
    "AC",
    "ac",
    "AN",
    "an",
    "homozygote_count",
    "hemizygote_count",
    "popmax",
    "faf95",
    "coverage",
    "quality_flags",
    "dataset",
    "population_version",
}

LITERATURE_FEATURE_KEYS = {
    "pmid",
    "PMID",
    "title",
    "abstract",
    "methods",
    "variant_mention",
    "phenotype",
    "functional_assay_details",
    "segregation",
    "de_novo",
    "study_quality",
    "hit_count",
    "literature_status",
}

USER_CONTEXT_FEATURE_KEYS = {
    "phenotype",
    "hpo_terms",
    "HPO",
    "de_novo",
    "segregation",
    "unaffected_adult",
    "alternate_diagnosis",
    "family_structure",
    "family_context",
    "phenotype_context",
}


def _lower_name(tool_name: str) -> str:
    return (tool_name or "").lower()


def source_category_for_tool(tool_name: str) -> str:
    name = _lower_name(tool_name)
    if "genebe" in name or "intervar" in name:
        return "automated_classifier"
    if "clinvar" in name:
        return "source_assertion"
    if "spliceai" in name:
        return "splicing_prediction"
    if any(token in name for token in ("cadd", "revel", "alphamissense", "myvariant", "opencravat", "vep")):
        return "computational_prediction"
    if "gnomad" in name or "population" in name:
        return "population"
    if "literature" in name or "pubmed" in name or "pmc" in name:
        return "literature"
    if "user" in name or "context" in name:
        return "user_context"
    if "clingen" in name or "g2p" in name:
        return "disease_context"
    return "source_lead"


def _candidate_from_criterion(criterion: str) -> dict[str, Any]:
    text = criterion.strip()
    route = {
        "PS3": "ps3_bs3_functional_assay_review",
        "BS3": "ps3_bs3_functional_assay_review",
        "PM2": "pm2_absence_rarity",
        "PP3": "computational_evidence_overlay",
        "BP4": "computational_evidence_overlay",
        "PP5": "reputable_source_review",
        "BP6": "reputable_source_review",
        "BA1": "ba1_bs1_frequency",
        "BS1": "ba1_bs1_frequency",
        "PVS1": "pvs1_splicing_refinement",
        "PS2": "ps2_pm6_de_novo_review",
        "PM6": "ps2_pm6_de_novo_review",
        "PP1": "pp1_segregation_review",
        "PP4": "pp4_phenotype_specificity_review",
        "BS2": "benign_context_review",
        "BP5": "benign_context_review",
    }.get(text.split("_", 1)[0], "overlay_review")
    return {
        "route": route,
        "suggested_criterion": text,
        "counted": False,
        "requires_overlay_validation": True,
    }


def _criteria_candidates(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [part.strip() for part in value.replace(";", ",").split(",")]
    elif isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = [str(value).strip()]
    return [_candidate_from_criterion(item) for item in items if item]


def _copy_keys(raw: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    return {key: raw[key] for key in keys if key in raw}


def _predictor_features(raw: dict[str, Any]) -> dict[str, Any]:
    features: dict[str, Any] = {}
    for key, value in raw.items():
        lowered = key.lower()
        if any(part in lowered for part in PREDICTOR_FEATURE_KEY_PARTS):
            features[key] = value
    return features


def _base_sandbox(tool_name: str, raw_output: Any) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "source_category": source_category_for_tool(tool_name),
        "reviewable_features": {},
        "candidate_routes": [],
        "quarantined_conclusions": {},
        "source_lead_summary": "",
        "counted": False,
        "source_lead_only": True,
        "acmg_countable_evidence": False,
        "final_classification_allowed": False,
        "may_emit_final_label": False,
        "requires_overlay_validation": True,
        "raw_source_present": raw_output is not None,
    }


def sandbox_source_output(
    *,
    tool_name: str,
    raw_output: Any,
    intent: str | ACMGIntent | None = None,
) -> dict[str, Any]:
    """Preserve source output as reviewable context while preventing direct counting."""

    intent_value = intent.value if isinstance(intent, ACMGIntent) else str(intent or ACMGIntent.ACMG_FINAL_CLASSIFICATION.value)
    sandbox = _base_sandbox(tool_name, raw_output)
    if intent_value == ACMGIntent.NONE.value:
        sandbox["requires_overlay_validation"] = False

    raw = raw_output if isinstance(raw_output, dict) else {"raw_output": raw_output}
    name = _lower_name(tool_name)
    category = sandbox["source_category"]

    if "spliceai" in name:
        sandbox["reviewable_features"].update(_copy_keys(raw, SPLICEAI_FEATURE_KEYS))
        sandbox["candidate_routes"].extend(
            [
                {"route": "pp3_bp4_splicing_prediction", "counted": False, "requires_overlay_validation": True},
                {"route": "pvs1_splicing_refinement", "counted": False, "requires_overlay_validation": True},
            ]
        )
    elif category == "computational_prediction":
        sandbox["reviewable_features"].update(_predictor_features(raw))
        if "vep" in name:
            for key in ("consequence", "most_severe_consequence", "transcript", "gene", "hgvs"):
                if key in raw:
                    sandbox["reviewable_features"][key] = raw[key]
        sandbox["candidate_routes"].extend(
            [
                {"route": "computational_evidence_overlay", "counted": False, "requires_overlay_validation": True},
                {"route": "pp3_bp4_prediction_refinement", "counted": False, "requires_overlay_validation": True},
            ]
        )
    elif "clinvar" in name:
        sandbox["reviewable_features"].update(_copy_keys(raw, CLINVAR_FEATURE_KEYS))
        sandbox["candidate_routes"].extend(
            [
                {"route": "reputable_source_review", "counted": False, "requires_overlay_validation": True},
                {"route": "conflict_resolution", "counted": False, "requires_overlay_validation": True},
            ]
        )
    elif "genebe" in name or "intervar" in name:
        for key in ("version", "date", "source", "gene", "transcript", "hgvs_c", "hgvs_p"):
            if key in raw:
                sandbox["reviewable_features"][key] = raw[key]
    elif category == "population":
        sandbox["reviewable_features"].update(_copy_keys(raw, GNOMAD_FEATURE_KEYS))
        sandbox["candidate_routes"].extend(
            [
                {"route": "pm2_absence_rarity", "counted": False, "requires_overlay_validation": True},
                {"route": "ba1_bs1_frequency", "counted": False, "requires_overlay_validation": True},
            ]
        )
    elif category == "literature":
        sandbox["reviewable_features"].update(_copy_keys(raw, LITERATURE_FEATURE_KEYS))
        sandbox["candidate_routes"].extend(
            [
                {"route": "literature_review", "counted": False, "requires_overlay_validation": True},
                {"route": "ps3_bs3_functional_assay_review", "counted": False, "requires_overlay_validation": True},
                {"route": "ps2_pm6_de_novo_review", "counted": False, "requires_overlay_validation": True},
                {"route": "pp1_segregation_review", "counted": False, "requires_overlay_validation": True},
                {"route": "pp4_phenotype_specificity_review", "counted": False, "requires_overlay_validation": True},
            ]
        )
    elif category == "user_context":
        sandbox["reviewable_features"].update(_copy_keys(raw, USER_CONTEXT_FEATURE_KEYS))
        for route in (
            "ps2_pm6_de_novo_review",
            "pp1_segregation_review",
            "pp4_phenotype_specificity_review",
            "benign_context_review",
        ):
            sandbox["candidate_routes"].append({"route": route, "counted": False, "requires_overlay_validation": True})
    else:
        sandbox["reviewable_features"].update(
            {key: value for key, value in raw.items() if key not in FINAL_OR_INTERPRETIVE_KEYS}
        )

    for key, value in raw.items():
        lowered = key.lower()
        if key in FINAL_OR_INTERPRETIVE_KEYS or any(term in lowered for term in ("classification", "interpretation", "criterion", "criteria", "pathogenic", "benign")):
            sandbox["quarantined_conclusions"][key] = value

    for key in ("acmg_criteria", "criteria", "applied_criteria"):
        sandbox["candidate_routes"].extend(_criteria_candidates(raw.get(key)))

    if raw.get("de_novo") or "de novo" in json.dumps(raw, ensure_ascii=False).lower():
        sandbox["candidate_routes"].append(
            {"route": "ps2_pm6_de_novo_review", "counted": False, "requires_overlay_validation": True}
        )
    if raw.get("segregation"):
        sandbox["candidate_routes"].append(
            {"route": "pp1_segregation_review", "counted": False, "requires_overlay_validation": True}
        )

    sandbox["source_lead_summary"] = (
        f"{tool_name} preserved as {sandbox['source_category']} source lead; "
        "reviewable features may feed overlays, quarantined conclusions cannot count."
    )
    return sandbox


__all__ = ["sandbox_source_output", "source_category_for_tool"]
