"""Unit coverage for the executable ACMG overlay harness runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tooluniverse.acmg_gate_search import add_acmg_gate_to_search_payload
from tooluniverse.acmg_gate import SOURCE_LEAD_NOTICE
from tooluniverse.acmg_harness_runner import ACMGHarnessRunner, ToolCallResult
from tooluniverse.acmg_overlay_gate_tool import ACMGOverlayGateTool

pytestmark = pytest.mark.unit


def _registry_entries() -> list[dict[str, Any]]:
    return [
        {"criterion_group": "pm2_absence_rarity", "overlay_skill": "tooluniverse-acmg-pm2-absence-rarity-refinement"},
        {"criterion_group": "pp3_bp4_missense_prediction", "overlay_skill": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement"},
        {"criterion_group": "ps3_bs3_functional_assay", "overlay_skill": "tooluniverse-acmg-ps3-bs3-functional-assay-refinement"},
        {"criterion_group": "de_novo_ps2_pm6", "overlay_skill": "tooluniverse-acmg-de-novo-evidence-refinement"},
        {"criterion_group": "ps4_case_enrichment", "overlay_skill": "tooluniverse-acmg-ps4-case-enrichment-refinement"},
        {"criterion_group": "reputable_source_review", "overlay_skill": "tooluniverse-acmg-pp5-bp6-reputable-source-refinement"},
        {"criterion_group": "pm4_bp3_protein_length", "overlay_skill": "tooluniverse-acmg-pm4-bp3-protein-length-refinement"},
    ]


def _route_row(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "criterion_group": entry["criterion_group"],
        "overlay_skill": entry.get("overlay_skill"),
        "status": "planned",
    }


def _select_baseline_routes(entries: list[dict[str, Any]], arguments: dict[str, Any]) -> list[dict[str, Any]]:
    return [_route_row({"criterion_group": "baseline_context", "overlay_skill": "tooluniverse-acmg-overlay-routing-core"})]


class FakeRunTool:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool_name, arguments))
        if tool_name == "EnsemblVEP_variant_recoder":
            return {
                "mappings": [
                    {
                        "id": "rs123456",
                        "hgvs": "NC_000004.12:g.1803931C>G",
                        "input": "NM_000142.5:c.1075+95C>G",
                    }
                ]
            }
        if tool_name == "SpliceAI_predict_splice":
            return {"prediction": "SpliceAI DS_DG donor gain 0.95"}
        if tool_name == "ClinVar_get_clinical_significance":
            return {"clinical_significance": "Likely pathogenic", "source": "ClinVar"}
        if tool_name == "MyVariant_get_pathogenicity_scores":
            return {"scores": {"CADD": 30, "AlphaMissense": "pathogenic"}}
        if tool_name in {"EnsemblVar_get_population_frequencies", "gnomad_get_variant", "gnomad_get_variant_populations"}:
            return []
        if tool_name == "GeneBe_classify_variant":
            return {"acmg_classification": "Likely_pathogenic", "acmg_criteria": ["PS3", "PM2"]}
        if tool_name == "InterVar_classify_variant":
            return {"intervar_classification": "Likely pathogenic"}
        if tool_name == "LitVar_search_variants":
            return {
                "articles": [
                    {
                        "pmid": "34162030",
                        "title": "FGFR3 minigene functional splicing assay de novo recurrence family cohort",
                    }
                ]
            }
        if tool_name == "EuropePMC_search_articles":
            return {"articles": [{"pmid": "38397214", "abstractText": "case series with unrelated recurrence"}]}
        if tool_name == "LitVar_get_variant_publications":
            return [{"pmid": "38397214"}]
        if tool_name == "PubMed_get_article":
            return {
                "pmid": str(arguments["pmid"]),
                "abstract": "in vitro RT-PCR minigene assay, de novo observations, cohort recurrence, pedigree family",
            }
        if tool_name == "ClinGen_search_gene_validity":
            return {"gene": "FGFR3", "validity": "Definitive"}
        if tool_name == "MedGen_search_conditions":
            return {"conditions": [{"name": "FGFR3-related skeletal dysplasia"}]}
        raise AssertionError(f"unexpected tool call: {tool_name}")


def _runner(run_tool: Any | None = None) -> ACMGHarnessRunner:
    return ACMGHarnessRunner(
        run_tool=run_tool or FakeRunTool(),
        registry_entries=_registry_entries(),
        route_row=_route_row,
        select_baseline_routes=_select_baseline_routes,
    )


def test_tool_call_result_as_dict_success_and_error():
    assert ToolCallResult("T", {"x": 1}, "literature", "success", result={"ok": True}).as_dict() == {
        "tool_name": "T",
        "arguments": {"x": 1},
        "source_category": "literature",
        "query_status": "success",
        "result": {"ok": True},
    }

    assert ToolCallResult("T", {}, "literature", "failed", error="boom").as_dict()["error"] == "boom"


def test_safe_call_and_query_status_cover_success_no_hit_error_and_exception():
    def fake(tool_name: str, arguments: dict[str, Any]) -> Any:
        return {
            "success": {"value": 1},
            "empty": [],
            "error_dict": {"status": "error", "error": "bad"},
        }[tool_name]

    runner = _runner(fake)
    assert runner._safe_call("success", {}, "x").status == "success"
    assert runner._safe_call("empty", {}, "x").status == "no_hit"
    failed = runner._safe_call("error_dict", {}, "x")
    assert failed.status == "failed"
    assert failed.error == "bad"

    boom_runner = _runner(lambda _name, _args: (_ for _ in ()).throw(RuntimeError("network down")))
    exception_row = boom_runner._safe_call("any", {}, "x")
    assert exception_row.status == "failed"
    assert exception_row.error == "network down"


def test_identifier_parsing_and_pmid_extraction_helpers():
    runner = _runner()
    text = "rs123 NC_000004.12:g.1803931C>G NM_000142.5:c.1075+95C>G PMID 34162030"
    derived = runner._derive_identifiers(text, [])

    assert derived["rsid"] == "rs123"
    assert derived["hgvs_g"] == "NC_000004.12:g.1803931C>G"
    assert derived["hgvs_c"] == "NM_000142.5:c.1075+95C>G"
    assert derived["genomic_parts"] == {"chr": "4", "pos": 1803931, "ref": "C", "alt": "G"}
    assert derived["spliceai_variant"] == "chr4-1803931-C-G"
    assert runner._genomic_parts("chr4:1803931:C:G") == {"chr": "4", "pos": 1803931, "ref": "C", "alt": "G"}
    assert runner._first_match(text, r"rs\d+") == "rs123"
    assert runner._extract_pmids([{"pmid": "34162030"}, "PMID 38397214"]) == ["34162030", "38397214"]


def test_assess_orchestrates_tools_and_never_counts_candidates():
    fake = FakeRunTool()
    result = _runner(fake).assess(
        {
            "variant": "NM_000142.5:c.1075+95C>G",
            "gene": "FGFR3",
            "transcript": "NM_000142.5",
            "source_outputs_or_leads": [{"source": "external lab", "classification": "Pathogenic"}],
        }
    )

    called_names = [name for name, _args in fake.calls]
    assert called_names[:2] == ["EnsemblVEP_variant_recoder", "SpliceAI_predict_splice"]
    assert "GeneBe_classify_variant" in called_names
    assert "InterVar_classify_variant" in called_names
    assert "LitVar_search_variants" in called_names
    assert "EuropePMC_search_articles" in called_names
    assert "PubMed_get_article" in called_names
    assert "ClinGen_search_gene_validity" in called_names
    assert "MedGen_search_conditions" in called_names

    assert result["derived_identifiers"]["rsid"] == "rs123456"
    criteria = {row["criterion"] for row in result["candidate_evidence"]}
    assert {"PM2", "PP3", "PS3", "PS2", "PS4", "PP5"}.issubset(criteria)
    assert all(row["counted"] is False for row in result["route_audit"])
    assert {row["route_outcome"] for row in result["route_audit"]} == {"overlay_not_assessed"}
    assert any(row["status"] == "not_used" and row["criterion"] == "PP5" for row in result["overlay_results"])

    literature = next(row for row in result["coverage_audit"] if row["source_category"] == "literature")
    assert literature["query_status"] == "success"
    assert {
        "ps3_bs3_functional_assay",
        "de_novo_ps2_pm6",
        "ps4_case_enrichment",
        "pp1_bs4_pp4_segregation",
    }.issubset(set(literature["triggered_routes"]))

    source_leads = result["source_assertions_or_leads"]
    assert source_leads
    assert all(lead["countable"] is False for lead in source_leads)
    assert all(lead["reason"] == SOURCE_LEAD_NOTICE for lead in source_leads)

    bundle = result["acmg_assessment_bundle"]
    assert bundle["classification_status"] == "draft classification"
    assert bundle["compatibility_resolution"]["current_counted_evidence_resolved"] == []
    assert result["missing_for_final"]
    assert any("no overlay-applied counted evidence" in item for item in result["missing_for_final"])


def test_coverage_audit_marks_absent_categories_and_summarizes_rows():
    runner = _runner()
    coverage = runner._coverage_audit([], {"rsid": "rs1", "hgvs_g": None, "hgvs_c": "NM_1:c.1A>G"})

    by_category = {row["source_category"]: row for row in coverage}
    assert by_category["literature"]["query_status"] == "unavailable"
    assert by_category["functional_database"]["query_status"] == "not_applicable"
    assert by_category["clinical_context"]["query_status"] == "not_applicable"
    assert by_category["literature"]["not_triggered_routes"]

    summary = runner._coverage_summary(coverage)
    assert summary[0]["source_category"] == "population"
    assert summary[0]["query_status"] == "unavailable"
    assert summary[0]["hit_count"] == 0
    assert summary[0]["triggered_routes"] == []


def test_candidate_evidence_ignores_failed_tool_error_text():
    runner = _runner()
    failed_rows = [
        ToolCallResult(
            "SpliceAI_predict_splice",
            {},
            "computational",
            "failed",
            error="minigene de novo pathogenic donor gain text from exception should not count",
        )
    ]

    assert runner._candidate_evidence(failed_rows, {}) == [
        {
            "criterion": "none",
            "candidate_strength": "no_candidate_trigger",
            "source_category": "harness",
            "reason": "No candidate ACMG evidence triggers were detected from tool outputs.",
        }
    ]


def test_route_plan_deduplicates_baseline_and_maps_candidate_groups():
    runner = _runner()
    route_plan = runner._route_plan(
        {"variant": "x"},
        [
            {"criterion": "PM2"},
            {"criterion": "PP3"},
            {"criterion": "PS3"},
            {"criterion": "PS2"},
            {"criterion": "PS4"},
            {"criterion": "PP5"},
            {"criterion": "PM4"},
            {"criterion": "none"},
        ],
    )

    groups = [row["criterion_group"] for row in route_plan]
    assert groups[0] == "baseline_context"
    assert len(groups) == len(set(groups))
    assert "pm2_absence_rarity" in groups
    assert "pp3_bp4_missense_prediction" in groups
    assert "reputable_source_review" in groups
    assert runner._criterion_to_group("unknown") == ""


def test_overlay_adapters_and_missing_for_final_contract():
    runner = _runner()
    overlay_results, route_audit = runner._overlay_adapters(
        [
            {"criterion": "PS3", "candidate_strength": "functional_candidate", "reason": "functional hit"},
            {"criterion": "PP5", "candidate_strength": "source_lead_only", "reason": "ClinVar label"},
            {"criterion": "none", "candidate_strength": "no_candidate_trigger"},
        ]
    )

    assert [row["criterion"] for row in overlay_results] == ["PS3", "PP5"]
    assert overlay_results[0]["overlay_skill"] == "tooluniverse-acmg-ps3-bs3-functional-assay-refinement"
    assert overlay_results[1]["status"] == "not_used"
    assert all(row["counted"] is False for row in route_audit)
    assert runner._criterion_overlay("unknown") == "tooluniverse-acmg-overlay-routing-core"

    missing = runner._missing_for_final(
        [{"source_category": "literature", "query_status": "failed"}],
        overlay_results,
        route_audit,
    )
    assert "literature coverage is failed" in missing
    assert any("no overlay-applied counted evidence" in item for item in missing)
    assert any("criterion-specific assessment" in item for item in missing)


def test_context_bundle_and_text_helpers():
    runner = _runner()
    bundle = runner._bundle(
        {"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3", "disease_context": "skeletal dysplasia"},
        {"hgvs_c": "NM_000142.5:c.1075+95C>G", "hgvs_g": "NC_000004.12:g.1803931C>G"},
        [{"criterion_group": "baseline_context"}],
        [],
        [],
        [],
        [],
    )

    assert bundle["variant"]["gene"] == "FGFR3"
    assert bundle["variant"]["assessment_context"] == "germline"
    assert bundle["disease_context"]["status"] == "partial"
    assert bundle["penetrance_context"]["criteria_affected"]
    assert bundle["vcep_context"]["scope_match"] == "unknown"
    assert runner._text({"b": 2, "a": 1}) == '{"a": 1, "b": 2}'


def test_remaining_helper_edge_cases():
    runner = _runner()

    assert runner._query_status({"status": "failed"}) == "failed"
    assert runner._query_status({"result": []}) == "no_hit"
    assert runner._genomic_parts("no parseable coordinate") is None
    assert runner._category_status([ToolCallResult("T", {}, "literature", "failed")], "literature") == "failed"

    pm4_candidate = runner._candidate_evidence(
        [ToolCallResult("VEP", {}, "computational", "success", result={"consequence": "in-frame insertion"})],
        {},
    )
    assert any(row["criterion"] == "PM4" for row in pm4_candidate)

    assert runner._text(None) == ""
    assert runner._text("already text") == "already text"
    assert runner._text({"not_json": {1, 2}}).startswith("{'not_json':")


def test_collect_evidence_deduplicates_lookup_ids():
    fake = FakeRunTool()
    calls = _runner(fake)._collect_evidence("rs123456", "FGFR3", "")

    clinvar_ids = [
        row.arguments["variant_id"]
        for row in calls
        if row.tool_name == "ClinVar_get_clinical_significance"
    ]
    assert clinvar_ids.count("rs123456") == 1


def test_gate_tool_assess_mode_uses_harness_and_keeps_draft_without_counted_evidence(monkeypatch):
    tool = ACMGOverlayGateTool({"name": "ACMG_overlay_gate_assess_variant", "type": "ACMGOverlayGateTool"})

    monkeypatch.setattr(tool, "_load_registry_entries", lambda: _registry_entries())
    monkeypatch.setattr(tool, "_run_tool", FakeRunTool())
    monkeypatch.setattr(
        tool,
        "_validate_bundle",
        lambda _bundle: {"validator_status": "PASS", "validator_result": {"status": "PASS"}, "violations": []},
    )

    result = tool.run({"mode": "assess", "variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"})

    assert result["mode"] == "assess"
    assert result["validator_status"] == "PASS"
    assert result["classification_status"] == "draft classification"
    assert result["final_classification_allowed"] is False
    assert result["final_answer_policy"] == "forbidden"
    assert result["counted_evidence"] == []
    assert result["route_triggers"]
    assert "candidate_evidence" not in result


def test_gate_tool_validate_bundle_pass_draft_does_not_allow_final(monkeypatch):
    tool = ACMGOverlayGateTool({"name": "ACMG_overlay_gate_assess_variant", "type": "ACMGOverlayGateTool"})
    monkeypatch.setattr(
        tool,
        "_validate_bundle",
        lambda _bundle: {"validator_status": "PASS", "validator_result": {"status": "PASS"}, "violations": []},
    )

    result = tool.run(
        {
            "mode": "validate_bundle",
            "acmg_assessment_bundle": {
                "variant": {"gene": "FGFR3"},
                "classification_status": "draft classification",
            },
        }
    )

    assert result["validator_status"] == "PASS"
    assert result["classification_status"] == "draft classification"
    assert result["final_classification_allowed"] is False
    assert result["missing_for_final"] == ["bundle classification_status is not final classification"]


def test_workflow_step_operations_and_final_answer_guard(monkeypatch):
    tool = ACMGOverlayGateTool({"name": "ACMG_plan_variant_assessment", "type": "ACMGOverlayGateTool", "fields": {"operation": "plan_variant_assessment"}})
    monkeypatch.setattr(tool, "_load_registry_entries", lambda: _registry_entries())
    plan = tool.run({"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"})
    assert plan["workflow_stage"] == "plan_routes"
    assert plan["final_answer_policy"] == "forbidden"
    assert plan["ordinary_entrypoint"] == "ACMG_overlay_gate_assess_variant"
    assert plan["not_final_entrypoint"] is True

    collect_tool = ACMGOverlayGateTool({"name": "ACMG_collect_variant_evidence", "type": "ACMGOverlayGateTool", "fields": {"operation": "collect_variant_evidence"}})
    monkeypatch.setattr(collect_tool, "_load_registry_entries", lambda: _registry_entries())
    monkeypatch.setattr(collect_tool, "_run_tool", FakeRunTool())
    collected = collect_tool.run({"variant": "NM_000142.5:c.1075+95C>G", "gene": "FGFR3"})
    assert collected["route_triggers"]
    assert collected["literature_status"]["literature_review_status"] == "not_reviewed"
    assert collected["ordinary_entrypoint"] == "ACMG_overlay_gate_assess_variant"
    assert collected["not_final_entrypoint"] is True

    apply_tool = ACMGOverlayGateTool({"name": "ACMG_apply_overlay_routes", "type": "ACMGOverlayGateTool", "fields": {"operation": "apply_overlay_routes"}})
    monkeypatch.setattr(apply_tool, "_load_registry_entries", lambda: _registry_entries())
    applied = apply_tool.run({"route_triggers": collected["route_triggers"]})
    assert applied["overlay_results"]
    assert all(row["counted"] is False for row in applied["route_audit"])
    assert applied["ordinary_entrypoint"] == "ACMG_overlay_gate_assess_variant"
    assert applied["not_final_entrypoint"] is True

    guard_tool = ACMGOverlayGateTool({"name": "ACMG_guard_final_answer", "type": "ACMGOverlayGateTool", "fields": {"operation": "guard_final_answer"}})
    guarded = guard_tool.run(
        {
            "final_answer_text": "Final ACMG classification: Likely Pathogenic. Applied evidence: PM2, PP3.",
            "harness_result": {"validator_status": "DRAFT_ONLY", "final_classification_allowed": False, "route_audit": []},
        }
    )
    assert guarded["status"] == "FAIL"
    assert "final_acmg_label_without_final_classification_allowed_true" in guarded["violations"]


def test_finalize_blocks_unreviewed_literature_even_with_validator_pass(monkeypatch):
    tool = ACMGOverlayGateTool({"name": "ACMG_finalize_assessment", "type": "ACMGOverlayGateTool", "fields": {"operation": "finalize_assessment"}})
    monkeypatch.setattr(
        tool,
        "_validate_bundle",
        lambda _bundle: {"validator_status": "PASS", "validator_result": {"status": "PASS"}, "violations": []},
    )
    bundle = {
        "variant": {"gene": "FGFR3"},
        "classification_status": "final classification",
        "coverage_audit": [
            {"source_category": "literature", "query_status": "success", "hits": [{"pmid": "34162030"}]},
        ],
        "compatibility_resolution": {"current_counted_evidence_resolved": ["PP3"]},
    }

    result = tool.run({"acmg_assessment_bundle": bundle})

    assert result["validator_status"] == "PASS"
    assert result["final_classification_allowed"] is False
    assert result["classification_status"] == "draft classification"
    assert any("literature" in reason for reason in result["blocked_reasons"])


def test_acmg_workflow_tool_metadata_keeps_single_public_entrypoint():
    tool_config = json.loads(
        (Path(__file__).resolve().parents[2] / "src/tooluniverse/data/acmg_overlay_gate_tools.json").read_text()
    )
    by_name = {row["name"]: row for row in tool_config}
    controller = by_name["ACMG_overlay_gate_assess_variant"]

    assert controller["metadata"]["workflow_visibility"] == "public_controller"
    assert controller["metadata"]["ordinary_entrypoint"] == "ACMG_overlay_gate_assess_variant"

    step_names = {
        "ACMG_plan_variant_assessment",
        "ACMG_collect_variant_evidence",
        "ACMG_apply_overlay_routes",
        "ACMG_finalize_assessment",
        "ACMG_guard_final_answer",
    }
    for name in step_names:
        row = by_name[name]
        assert row["metadata"]["workflow_visibility"] == "advanced_internal_step"
        assert row["metadata"]["ordinary_entrypoint"] == "ACMG_overlay_gate_assess_variant"
        assert row["description"].startswith("Advanced/internal ACMG workflow step.")
        assert "ACMG_overlay_gate_assess_variant with mode=assess" in row["description"]


def test_acmg_search_payload_keeps_controller_first_even_when_step_tools_present():
    payload = {
        "tools": [
            {"name": "ACMG_collect_variant_evidence"},
            {"name": "GeneBe_classify_variant"},
            {"name": "ACMG_plan_variant_assessment"},
        ],
        "limit": 4,
    }

    updated = add_acmg_gate_to_search_payload(payload)
    names = [row["name"] for row in updated["tools"]]

    assert names[0] == "ACMG_overlay_gate_assess_variant"
    assert "ACMG_collect_variant_evidence" in names[1:]
    assert "ACMG_plan_variant_assessment" in names[1:]
