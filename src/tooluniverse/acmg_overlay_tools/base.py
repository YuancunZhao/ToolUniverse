"""Base infrastructure for ACMG overlay MCP tools.

Provides shared lookup functions and output formatting. Does NOT require
PyYAML at runtime — overlay routing rules are hardcoded from overlay_registry.yaml.
"""

from __future__ import annotations

from typing import Any


# Hardcoded from overlay_registry.yaml criterion_ownership section.
# Updated: 2026-07-01
CRITERION_OWNERSHIP: dict[str, list[str]] = {
    "PVS1": ["pvs1_lof_decision_tree", "pvs1_splicing"],
    "PS1":  ["ps1_pm5_amino_acid_equivalence", "ps1_splicing_similarity"],
    "PS2":  ["de_novo_ps2_pm6"],
    "PS3":  ["ps3_bs3_functional_assay"],
    "PS4":  ["ps4_case_enrichment"],
    "PM1":  ["pm1_regional_missense_constraint"],
    "PM2":  ["pm2_absence_rarity"],
    "PM3":  ["pm3_in_trans"],
    "PM4":  ["pm4_bp3_protein_length"],
    "PM5":  ["ps1_pm5_amino_acid_equivalence"],
    "PM6":  ["de_novo_ps2_pm6"],
    "PP1":  ["pp1_bs4_pp4_segregation"],
    "PP2":  ["pm1_regional_missense_constraint"],
    "PP3":  ["pp3_bp4_missense_prediction"],
    "PP4":  ["pp1_bs4_pp4_segregation"],
    "PP5":  ["reputable_source_review"],
    "BA1":  ["ba1_exception_list", "benign_context"],
    "BS1":  ["benign_context"],
    "BS2":  ["benign_context"],
    "BS3":  ["ps3_bs3_functional_assay"],
    "BS4":  ["pp1_bs4_pp4_segregation"],
    "BP1":  ["pm1_regional_missense_constraint"],
    "BP2":  ["benign_context"],
    "BP3":  ["pm4_bp3_protein_length"],
    "BP4":  ["pp3_bp4_missense_prediction"],
    "BP5":  ["benign_context"],
    "BP6":  ["reputable_source_review"],
    "BP7":  ["pvs1_splicing"],
}

# Overlay groups and their trigger policies, hardcoded from overlay_registry.yaml
OVERLAY_GROUPS: list[dict[str, Any]] = [
    {"group": "ba1_exception_list",       "policy": "universal_baseline"},
    {"group": "benign_context",            "policy": "universal_baseline"},
    {"group": "pm2_absence_rarity",        "policy": "universal_baseline"},
    {"group": "pp3_bp4_missense_prediction","policy": "variant_type_baseline", "applies": ["missense"]},
    {"group": "ps1_pm5_amino_acid_equivalence","policy":"variant_type_baseline", "applies": ["missense"]},
    {"group": "ps1_splicing_similarity",   "policy": "variant_type_baseline", "applies": ["splice","intronic"]},
    {"group": "pm1_regional_missense_constraint","policy":"variant_type_baseline","applies": ["missense"]},
    {"group": "pvs1_lof_decision_tree",    "policy": "variant_type_baseline", "applies": ["null","frameshift","nonsense"]},
    {"group": "pvs1_splicing",             "policy": "variant_type_baseline", "applies": ["splice","intronic"]},
    {"group": "pm4_bp3_protein_length",    "policy": "variant_type_baseline", "applies": ["indel_inframe","null"]},
    {"group": "dominant_negative_mechanism","policy":"variant_type_baseline","applies": ["missense"]},
    {"group": "multiple_disorder_context", "policy": "universal_baseline"},
    {"group": "phenotype_dependent_intake","policy": "evidence_discovery"},
    {"group": "reputable_source_review",   "policy": "evidence_discovery"},
    {"group": "ps3_bs3_functional_assay",  "policy": "evidence_discovery"},
    {"group": "ps4_case_enrichment",       "policy": "evidence_discovery"},
    {"group": "pp1_bs4_pp4_segregation",   "policy": "evidence_discovery"},
    {"group": "pm3_in_trans",              "policy": "evidence_discovery"},
    {"group": "de_novo_ps2_pm6",           "policy": "evidence_discovery"},
    {"group": "evidence_compatibility_resolution","policy":"evidence_discovery"},
]

LITERATURE_DEPENDENT = [
    "ps3_bs3_functional_assay",
    "ps4_case_enrichment",
    "pp1_bs4_pp4_segregation",
    "de_novo_ps2_pm6",
    "pm3_in_trans",
    "reputable_source_review",
]


def criterion_ownership() -> dict[str, list[str]]:
    return CRITERION_OWNERSHIP


def overlays_for_criterion(criterion: str) -> list[str]:
    return CRITERION_OWNERSHIP.get(criterion.upper(), [])


def variant_type_overlays(variant_type: str) -> list[str]:
    vt = variant_type.lower().strip()
    groups: list[str] = []
    for entry in OVERLAY_GROUPS:
        policy = entry["policy"]
        if policy == "universal_baseline":
            groups.append(entry["group"])
        elif policy == "variant_type_baseline":
            applies = entry.get("applies", [])
            if not applies or vt in applies:
                groups.append(entry["group"])
    return list(dict.fromkeys(groups))


def literature_dependent_overlays() -> list[str]:
    return LITERATURE_DEPENDENT


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


__all__ = [
    "criterion_ownership",
    "literature_dependent_overlays",
    "output_template",
    "overlays_for_criterion",
    "variant_type_overlays",
]
