"""Registration and import contracts for the ACMG evidence collector."""

from __future__ import annotations

import json
import inspect
import re
from pathlib import Path

from tooluniverse.tool_registry import lazy_import_tool
from tooluniverse.tools.ACMG_evidence_collector import ACMG_evidence_collector
from tooluniverse.tools.ACMG_overlay_gate_assess_variant import (
    ACMG_overlay_gate_assess_variant,
)


def test_acmg_summary_imports_without_legacy_overlay_package():
    from tooluniverse.acmg import summary

    assert hasattr(summary, "compute_bayesian_score")
    assert hasattr(summary, "detect_conflicts")


def test_tools_package_does_not_export_retired_acmg_wrappers():
    source = Path("src/tooluniverse/tools/__init__.py").read_text(encoding="utf-8")

    for retired_name in (
        "ACMG_apply_overlay_routes",
        "ACMG_collect_variant_evidence",
        "ACMG_combine_criteria",
        "ACMG_finalize_assessment",
        "ACMG_plan_variant_assessment",
        "ACMG_route_overlays",
    ):
        assert retired_name not in source


def test_tools_init_imports_match_tracked_module_filename_case():
    tools_dir = Path("src/tooluniverse/tools")
    source = (tools_dir / "__init__.py").read_text(encoding="utf-8")
    imported_modules = set(
        re.findall(r"^from \.([A-Za-z0-9_]+) import ", source, re.MULTILINE)
    )
    on_disk_modules = {path.stem for path in tools_dir.glob("*.py")}

    assert imported_modules <= on_disk_modules, sorted(
        imported_modules - on_disk_modules
    )


def test_current_acmg_skill_mirrors_do_not_contain_retired_workflow():
    skill_files = (
        "tooluniverse-acmg-variant-classification/SKILL.md",
        "tooluniverse-acmg-variant-classification/QUICK_START.md",
        "tooluniverse-variant-interpretation/SKILL.md",
    )
    roots = (
        Path("skills"),
        Path("plugin/skills"),
        Path("plugins/tooluniverse/skills"),
    )
    retired_tokens = (
        "ACMG_route_overlays",
        "ACMG_combine_criteria",
        "FINALIZED",
        "semantic_combiner",
        "validator_status",
    )

    for root in roots:
        for relative_path in skill_files:
            text = (root / relative_path).read_text(encoding="utf-8")
            assert not any(token in text for token in retired_tokens), (
                f"retired ACMG workflow token found in {root / relative_path}"
            )


def test_canonical_acmg_docs_do_not_claim_pvs1_is_unimplemented():
    forbidden = (
        "PVS1 remains `not_assessed` in the current runtime",
        "current runtime does not complete the PVS1 decision tree",
        "PVS1/splicing remains `not_assessed` until the complete ClinGen",
    )
    for path in (
        Path("skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md"),
        Path("skills/tooluniverse-acmg-variant-classification/SKILL.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path


def test_acmg_routing_contract_is_consolidated_into_one_visible_skill():
    roots = (
        Path("skills"),
        Path("plugin/skills"),
        Path("plugins/tooluniverse/skills"),
    )
    required_tokens = (
        "ACMG_evidence_collector",
        "cspec_proposals",
        "literature_proposals",
        "recoverable_gaps",
        "workflow_status",
        "next_actions",
        "Do not ask the user whether",
        "End automated collection only when",
        "DS_AG",
        "DS_DL",
        "system_preview_bayesian",
        "validated_subset_bayesian",
        "guard_context",
        "user_selected_bayesian",
        "ACMG_guard_final_answer",
        "`reviewer` and `decided_at` are optional",
    )
    forbidden_tokens = (
        "abstract-only or unavailable material remains a source lead",
        "Abstract-only or unavailable papers remain source leads",
    )

    for root in roots:
        retired = root / "tooluniverse-acmg-overlay-routing-core"
        assert not (retired / "SKILL.md").exists()
        text = (
            root / "tooluniverse-acmg-variant-classification" / "SKILL.md"
        ).read_text(encoding="utf-8")
        assert all(token in text for token in required_tokens)
        assert not any(token in text for token in forbidden_tokens)


def test_active_skills_do_not_depend_on_retired_acmg_routing_core():
    retired_name = "tooluniverse-acmg-overlay-routing-core"
    for path in Path("skills").rglob("*.md"):
        if path == Path("skills/tooluniverse-install-skills/SKILL.md"):
            continue
        assert retired_name not in path.read_text(encoding="utf-8"), path


def test_structural_variant_skill_excludes_small_variant_collector():
    paths = (
        Path("skills/tooluniverse-structural-variant-analysis/SKILL.md"),
        Path("skills/tooluniverse-structural-variant-analysis/CLASSIFICATION_GUIDE.md"),
    )
    for path in paths:
        text = " ".join(path.read_text(encoding="utf-8").split())
        assert "supports germline small variants" in text
        assert "do not submit" in text or "never submit" in text
    skill = paths[0].read_text(encoding="utf-8")
    assert "disable-model-invocation" not in skill
    assert "EnsemblMap_convert_coordinates" in skill
    assert "gnomad_get_sv_by_region" in skill
    assert "approximate coordinate offset" in skill


def test_general_router_preserves_biology_routes_and_enhanced_acmg_route():
    text = Path("skills/tooluniverse/SKILL.md").read_text(encoding="utf-8")

    for skill_name in (
        "tooluniverse-disease-research",
        "tooluniverse-drug-research",
        "tooluniverse-literature-deep-research",
        "tooluniverse-target-research",
        "tooluniverse-protein-structure-retrieval",
        "tooluniverse-acmg-variant-classification",
    ):
        assert f'Skill(skill="{skill_name}")' in text
    assert text.count(
        'Skill(skill="tooluniverse-acmg-variant-classification")'
    ) < text.count("Skill(skill=")
    structural = 'Skill(skill="tooluniverse-structural-variant-analysis")'
    assert structural in text
    assert text.index(structural) < text.index(
        'Skill(skill="tooluniverse-acmg-variant-classification")'
    )
    assert all(token in text for token in ("结构变异", "缺失", "BND", "chr:start-end"))


def test_variant_interpretation_routes_sv_before_small_variant_collector():
    text = Path("skills/tooluniverse-variant-interpretation/SKILL.md").read_text(
        encoding="utf-8"
    )
    structural = "tooluniverse-structural-variant-analysis"
    collector = "ACMG_evidence_collector"
    assert text.index(structural) < text.index(collector)
    assert "intervals over 50 bp" in " ".join(text.split())
    assert "Normalize hg19 to GRCh37" in text


def test_acmg_evidence_collector_lazy_imports():
    cls = lazy_import_tool("ACMG_evidence_collector")

    assert cls is not None
    assert cls.__name__ == "ACMGEvidenceCollector"


def test_public_acmg_runtime_tool_types_lazy_import():
    assert lazy_import_tool("ACMGEvidenceGroupTool").__name__ == "ACMGEvidenceGroupTool"
    assert (
        lazy_import_tool("ACMGGuardFinalAnswerTool").__name__
        == "ACMGGuardFinalAnswerTool"
    )


def test_collector_is_the_primary_runtime_discovery_front_door():
    from tooluniverse.acmg import policy
    from tooluniverse import tools

    assert policy.ACMG_FRONT_DOOR_TOOL_NAME == "ACMG_evidence_collector"
    assert "ACMG_evidence_collector" in tools.__all__

    sandboxed = policy.sanitize_high_risk_acmg_result(
        "GeneBe_classify_variant",
        {"classification": "Pathogenic"},
        policy_context={"acmg_evidence_collection": True},
    )
    assert sandboxed["recommended_front_door_tool"] == "ACMG_evidence_collector"


def test_acmg_evidence_collector_has_public_tool_config():
    path = Path("src/tooluniverse/data/acmg_overlay_gate_tools.json")
    configs = json.loads(path.read_text())
    matching = [c for c in configs if c.get("name") == "ACMG_evidence_collector"]

    assert len(matching) == 1
    assert matching[0]["type"] == "ACMG_evidence_collector"
    assert "collects and displays evidence" in matching[0]["description"]


def test_all_evidence_runtime_tools_have_public_configs():
    path = Path("src/tooluniverse/data/acmg_overlay_gate_tools.json")
    configs = json.loads(path.read_text())
    by_name = {row.get("name"): row for row in configs}
    group_names = {
        "ACMG_population_evidence",
        "ACMG_computational_evidence",
        "ACMG_clinical_evidence",
        "ACMG_functional_evidence",
        "ACMG_literature_evidence",
    }

    assert group_names <= by_name.keys()
    assert {by_name[name]["type"] for name in group_names} == {"ACMGEvidenceGroupTool"}
    assert by_name["ACMG_guard_final_answer"]["type"] == "ACMGGuardFinalAnswerTool"


def test_public_runtime_tools_dispatch_through_tooluniverse():
    from tooluniverse import ToolUniverse

    path = "src/tooluniverse/data/acmg_overlay_gate_tools.json"
    runtime = ToolUniverse(tool_files={"acmg": path}, keep_default_tools=False)
    runtime.load_tools()

    population = runtime.run_one_function(
        {
            "name": "ACMG_population_evidence",
            "arguments": {
                "gnomad_ac": 0,
                "gnomad_an": 1000,
                "coverage_adequate": True,
            },
        }
    )
    guard = runtime.run_one_function(
        {
            "name": "ACMG_guard_final_answer",
            "arguments": {"final_answer_text": "PP3", "evidence_cards": []},
        }
    )
    collector = runtime.run_one_function(
        {
            "name": "ACMG_evidence_collector",
            "arguments": {"variant": "NM_000000.0:c.1A>G"},
        }
    )
    legacy = runtime.run_one_function(
        {
            "name": "ACMG_overlay_gate_assess_variant",
            "arguments": {"variant": "NM_000000.0:c.1A>G"},
        }
    )

    assert population["evidence_cards"][0]["system_preview_included"] is False
    assert population["evidence_cards"][0]["overlay_validated"] is False
    assert guard["status"] == "BLOCK"
    assert collector["execution_status"] == "error"
    assert legacy["execution_status"] == "error"


def test_group_tool_schemas_cover_python_wrapper_parameters():
    from tooluniverse import tools

    configs = json.loads(
        Path("src/tooluniverse/data/acmg_overlay_gate_tools.json").read_text()
    )
    by_name = {row["name"]: row for row in configs}
    ignored = {"stream_callback", "use_cache", "validate"}
    for name in (
        "ACMG_population_evidence",
        "ACMG_computational_evidence",
        "ACMG_clinical_evidence",
        "ACMG_functional_evidence",
        "ACMG_literature_evidence",
    ):
        wrapper = getattr(tools, name)
        parameters = set(inspect.signature(wrapper).parameters) - ignored
        schema_parameters = set(by_name[name]["parameter"]["properties"])
        assert parameters <= schema_parameters, (
            f"{name}: {parameters - schema_parameters}"
        )


def test_computational_schema_exposes_normalized_spliceai_migration_fields():
    configs = json.loads(
        Path("src/tooluniverse/data/acmg_overlay_gate_tools.json").read_text()
    )
    by_name = {row["name"]: row for row in configs}
    properties = by_name["ACMG_computational_evidence"]["parameter"]["properties"]

    assert {"spliceai_profile", "spliceai_scores", "spliceai_max_delta"} <= set(
        properties
    )
    assert "spliceai_dl" not in properties


def test_spliceai_provider_schema_defines_delta_channels_and_maximum():
    configs = json.loads(Path("src/tooluniverse/data/spliceai_tools.json").read_text())
    by_name = {row["name"]: row for row in configs}
    data = by_name["SpliceAI_predict_splice"]["return_schema"]["properties"]["data"]
    score_properties = data["properties"]["scores"]["items"]["properties"]

    assert {"DS_AG", "DS_AL", "DS_DG", "DS_DL"} <= set(score_properties)
    assert {"DP_AG", "DP_AL", "DP_DG", "DP_DL"} <= set(score_properties)
    assert "do not invert" in score_properties["DP_DL"]["description"]
    assert "Maximum of DS_AG" in data["properties"]["max_delta_score"]["description"]
    assert "not donor loss" in by_name["SpliceAI_get_max_delta"]["description"]


def test_collector_wrapper_parameters_match_public_schemas():
    from tooluniverse import tools

    configs = json.loads(
        Path("src/tooluniverse/data/acmg_overlay_gate_tools.json").read_text()
    )
    by_name = {row["name"]: row for row in configs}
    ignored = {"stream_callback", "use_cache", "validate"}
    for name in ("ACMG_evidence_collector", "ACMG_overlay_gate_assess_variant"):
        wrapper = getattr(tools, name)
        parameters = set(inspect.signature(wrapper).parameters) - ignored
        assert parameters == set(by_name[name]["parameter"]["properties"])


def test_public_config_is_converged_to_eight_runtime_tools():
    path = Path("src/tooluniverse/data/acmg_overlay_gate_tools.json")
    configs = json.loads(path.read_text())
    assert len(configs) == 8


def test_collector_and_alias_require_the_same_runtime_result_fields():
    configs = json.loads(
        Path("src/tooluniverse/data/acmg_overlay_gate_tools.json").read_text()
    )
    by_name = {row["name"]: row for row in configs}

    collector_required = set(
        by_name["ACMG_evidence_collector"]["return_schema"]["required"]
    )
    alias_required = set(
        by_name["ACMG_overlay_gate_assess_variant"]["return_schema"]["required"]
    )
    assert collector_required == alias_required
    assert (
        by_name["ACMG_evidence_collector"]["parameter"]
        == by_name["ACMG_overlay_gate_assess_variant"]["parameter"]
    )
    assert (
        by_name["ACMG_evidence_collector"]["return_schema"]
        == by_name["ACMG_overlay_gate_assess_variant"]["return_schema"]
    )
    assert "consequence_profile" in collector_required
    assert {
        "variant_scope",
        "system_preview_bayesian",
        "validated_subset_bayesian",
        "guard_context",
        "user_selected_bayesian",
        "decision_report",
        "recoverable_gaps",
        "workflow_status",
        "next_actions",
        "literature_review",
    } <= collector_required

    build_schema = by_name["ACMG_evidence_collector"]["parameter"]["properties"][
        "genome_build"
    ]
    assert set(build_schema["enum"]) == {"GRCh37", "GRCh38", "hg19", "hg38"}
    assert "default" not in build_schema
    collector_signature = inspect.signature(ACMG_evidence_collector)
    alias_signature = inspect.signature(ACMG_overlay_gate_assess_variant)
    assert collector_signature.parameters["genome_build"].default is None
    assert alias_signature.parameters["genome_build"].default is None
    workflow_statuses = by_name["ACMG_evidence_collector"]["return_schema"][
        "properties"
    ]["workflow_status"]["enum"]
    assert {"input_correction_required", "unsupported_variant_class"} <= set(
        workflow_statuses
    )


def test_collector_and_alias_expose_literature_and_decision_workbench_inputs():
    configs = json.loads(
        Path("src/tooluniverse/data/acmg_overlay_gate_tools.json").read_text()
    )
    by_name = {row["name"]: row for row in configs}
    for name in ("ACMG_evidence_collector", "ACMG_overlay_gate_assess_variant"):
        parameter = by_name[name]["parameter"]
        assert {
            "literature_proposals",
            "cspec_proposals",
            "evidence_decisions",
        } <= set(parameter["properties"])
        assert "literature_facts" not in parameter["properties"]
        proposal_items = parameter["properties"]["literature_proposals"]["items"]
        assert "criterion" not in proposal_items["required"]
        assert "suggested_strength" not in proposal_items["required"]
        assert {
            "review_request_id",
            "document_hash",
            "reading_manifest",
        } <= set(proposal_items["properties"])
        reading_status = proposal_items["properties"]["reading_manifest"]["properties"][
            "status"
        ]
        assert set(reading_status["enum"]) == {
            "complete",
            "partial",
            "abstract_only",
            "unavailable",
        }
        assert {
            "segregation",
            "phenotype_specificity",
            "healthy_observation",
            "allelic_phase",
            "alternative_cause",
            "prior_variant",
            "region_hotspot",
            "protein_length_repeat",
            "rna_splicing",
        } <= set(proposal_items["properties"]["fact_type"]["enum"])
        assert "allOf" not in parameter
