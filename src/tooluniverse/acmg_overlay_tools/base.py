"""Base infrastructure for ACMG overlay MCP tools.

Loads overlay_registry.yaml at module init. Falls back to hardcoded tables
when PyYAML is not available — the hardcoded copy MUST be kept in sync
with the YAML file when making overlay rule changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ── YAML loading ────────────────────────────────────────────────────

_REGISTRY: dict[str, Any] | None = None


def _registry_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        for candidate in (
            parent / "skills" / "tooluniverse-acmg-overlay-routing-core" / "overlay_registry.yaml",
            parent / "src" / "tooluniverse" / "data" / "acmg_overlay_gate" / "overlay_registry.yaml",
        ):
            if candidate.exists():
                return candidate
    return Path("overlay_registry.yaml")


def _load_yaml() -> dict[str, Any] | None:
    try:
        import yaml

        return yaml.safe_load(_registry_path().read_text(encoding="utf-8")) or {}
    except Exception:
        return None


# ── Hardcoded fallback (synced from overlay_registry.yaml 2026-07-02) ─

_FALLBACK_CRITERION_OWNERSHIP: dict[str, list[str]] = {
    "PVS1": ["pvs1_lof_decision_tree", "pvs1_splicing"],
    "PS1": ["ps1_pm5_amino_acid_equivalence", "ps1_splicing_similarity"],
    "PS2": ["de_novo_ps2_pm6"],
    "PS3": ["ps3_bs3_functional_assay"],
    "PS4": ["ps4_case_enrichment"],
    "PM1": ["pm1_regional_missense_constraint"],
    "PM2": ["pm2_absence_rarity"],
    "PM3": ["pm3_in_trans"],
    "PM4": ["pm4_bp3_protein_length"],
    "PM5": ["ps1_pm5_amino_acid_equivalence"],
    "PM6": ["de_novo_ps2_pm6"],
    "PP1": ["pp1_bs4_pp4_segregation"],
    "PP2": ["pm1_regional_missense_constraint"],
    "PP3": ["pp3_bp4_missense_prediction"],
    "PP4": ["pp1_bs4_pp4_segregation"],
    "PP5": ["reputable_source_review"],
    "BA1": ["ba1_exception_list", "benign_context"],
    "BS1": ["benign_context"],
    "BS2": ["benign_context"],
    "BS3": ["ps3_bs3_functional_assay"],
    "BS4": ["pp1_bs4_pp4_segregation"],
    "BP1": ["pm1_regional_missense_constraint"],
    "BP2": ["benign_context"],
    "BP3": ["pm4_bp3_protein_length"],
    "BP4": ["pp3_bp4_missense_prediction"],
    "BP5": ["benign_context"],
    "BP6": ["reputable_source_review"],
    "BP7": ["pvs1_splicing"],
}

_FALLBACK_OVERLAY_GROUPS: list[dict[str, Any]] = [
    {"group": "ba1_exception_list", "policy": "universal_baseline"},
    {"group": "benign_context", "policy": "universal_baseline"},
    {"group": "pm2_absence_rarity", "policy": "universal_baseline"},
    {"group": "pp3_bp4_missense_prediction", "policy": "variant_type_baseline", "applies": ["missense"]},
    {"group": "ps1_pm5_amino_acid_equivalence", "policy": "variant_type_baseline", "applies": ["missense"]},
    {"group": "ps1_splicing_similarity", "policy": "variant_type_baseline", "applies": ["splice", "intronic"]},
    {"group": "pm1_regional_missense_constraint", "policy": "variant_type_baseline", "applies": ["missense"]},
    {"group": "pvs1_lof_decision_tree", "policy": "variant_type_baseline", "applies": ["null", "frameshift", "nonsense"]},
    {"group": "pvs1_splicing", "policy": "variant_type_baseline", "applies": ["splice", "intronic"]},
    {"group": "pm4_bp3_protein_length", "policy": "variant_type_baseline", "applies": ["indel_inframe", "null"]},
    {"group": "dominant_negative_mechanism", "policy": "variant_type_baseline", "applies": ["missense"]},
    {"group": "multiple_disorder_context", "policy": "universal_baseline"},
    {"group": "phenotype_dependent_intake", "policy": "evidence_discovery"},
    {"group": "reputable_source_review", "policy": "evidence_discovery"},
    {"group": "ps3_bs3_functional_assay", "policy": "evidence_discovery"},
    {"group": "ps4_case_enrichment", "policy": "evidence_discovery"},
    {"group": "pp1_bs4_pp4_segregation", "policy": "evidence_discovery"},
    {"group": "pm3_in_trans", "policy": "evidence_discovery"},
    {"group": "de_novo_ps2_pm6", "policy": "evidence_discovery"},
    {"group": "evidence_compatibility_resolution", "policy": "evidence_discovery"},
]

# ── Public API ────────────────────────────────────────────────────────


def _registry() -> dict[str, Any]:
    """Return registry dict, preferring YAML over hardcoded fallback."""
    global _REGISTRY
    if _REGISTRY is None:
        loaded = _load_yaml()
        if loaded:
            _REGISTRY = loaded
        else:
            # Fallback: build a minimal dict from hardcoded tables
            _REGISTRY = {
                "criterion_ownership": _FALLBACK_CRITERION_OWNERSHIP,
                "overlays": _FALLBACK_OVERLAY_GROUPS,
            }
    return _REGISTRY


def criterion_ownership() -> dict[str, list[str]]:
    reg = _registry()
    raw = reg.get("criterion_ownership", {})
    if raw:
        return raw
    return _FALLBACK_CRITERION_OWNERSHIP


def overlays_for_criterion(criterion: str) -> list[str]:
    return criterion_ownership().get(criterion.upper(), [])


def _overlay_entries() -> list[dict[str, Any]]:
    """Return overlay entries from YAML or fallback."""
    reg = _registry()
    entries = reg.get("overlays")
    if entries:
        return [e for e in entries if isinstance(e, dict)]
    return _FALLBACK_OVERLAY_GROUPS


def variant_type_overlays(variant_type: str) -> list[str]:
    vt = variant_type.lower().strip()
    groups: list[str] = []
    for entry in _overlay_entries():
        group = entry.get("criterion_group") or entry.get("group", "")
        policy = entry.get("trigger_policy") or entry.get("policy", "")
        if policy == "universal_baseline":
            groups.append(str(group))
        elif policy == "variant_type_baseline":
            applies = entry.get("applies_when") or entry.get("applies", [])
            if isinstance(applies, str):
                applies = [applies]
            applies_text = " ".join(str(a).lower() for a in applies)
            if not applies or vt in applies_text:
                groups.append(str(group))
    return list(dict.fromkeys(groups))


def literature_dependent_overlays() -> list[str]:
    groups: list[str] = []
    for entry in _overlay_entries():
        policy = entry.get("trigger_policy") or entry.get("policy", "")
        if policy == "evidence_discovery":
            group = entry.get("criterion_group") or entry.get("group", "")
            groups.append(str(group))
    return groups


def output_template(
    criterion: str,
    strength: str,
    status: str = "applied",
    route_outcome: str = "overlay_applied",
    guidance_authority: str = "ClinGen/SVI primary",
    reason: str = "",
    source_of_truth: str = "",
    next_action: str = "",
) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "strength": strength,
        "status": status,
        "route_outcome": route_outcome,
        "guidance_authority": guidance_authority,
        "source_of_truth": source_of_truth,
        "reason": reason,
        "next_action": next_action,
        "counted": route_outcome in {"overlay_applied", "overlay_deferred_to_vcep"},
        "overlay_validated": route_outcome == "overlay_applied",
    }


def vcep_deferred_template(
    criterion: str,
    strength: str,
    *,
    reason: str = "",
    source_of_truth: str = "VCEP specification",
    next_action: str = "Validate VCEP disease, gene, transcript, variant type, and scope in acmg_assessment_bundle.vcep_context.",
) -> dict[str, Any]:
    return output_template(
        criterion,
        strength,
        status="applied",
        route_outcome="overlay_deferred_to_vcep",
        guidance_authority="VCEP-specific",
        reason=reason or f"VCEP-specific rule proposed {strength}; validator must confirm scope before final classification.",
        source_of_truth=source_of_truth,
        next_action=next_action,
    )


__all__ = [
    "criterion_ownership",
    "literature_dependent_overlays",
    "output_template",
    "overlays_for_criterion",
    "vcep_deferred_template",
    "variant_type_overlays",
]
