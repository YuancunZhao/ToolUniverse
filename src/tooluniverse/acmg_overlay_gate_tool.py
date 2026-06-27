"""ACMG overlay gate front-door tool for ToolUniverse.

This tool is intentionally a compliance gate and preflight planner, not a new
ACMG classifier. It routes germline pathogenicity tasks toward the overlay
bundle/validator workflow and treats automated classifier outputs as source
leads.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

from .base_tool import BaseTool
from .tool_registry import register_tool

CLASSIFICATION_DRAFT = "draft classification"
CLASSIFICATION_FINAL = "final classification"
VALIDATOR_NOT_RUN = "NOT_RUN"
VALIDATOR_DRAFT_ONLY = "DRAFT_ONLY"
SOURCE_LEAD_NOTICE = (
    "Automated classifier, database label, predictor score, or annotation output "
    "is a source lead or route trigger only. It is not ACMG counted evidence "
    "until routed through an overlay or in-scope VCEP and validated in an "
    "acmg_assessment_bundle."
)

SOURCE_LEAD_KEYWORDS = (
    "genebe",
    "intervar",
    "clinvar",
    "clingen",
    "hgmd",
    "lovd",
    "lab assertion",
    "paper label",
)

BASE_RECOMMENDED_TOOL_CALLS = [
    {
        "tool_name": "EnsemblVEP_annotate_hgvs",
        "purpose": "Normalize consequence, transcript, protein effect, and colocated variant context.",
        "route_input_for": ["PVS1", "PM4/BP3", "PS1/PM5", "PP3/BP4"],
    },
    {
        "tool_name": "ClinVar_get_clinical_significance",
        "purpose": "Retrieve ClinVar assertion as source lead only; do not count the label directly.",
        "route_input_for": ["PP5/BP6 source review", "source_assertions_or_leads"],
    },
    {
        "tool_name": "MyVariant_get_pathogenicity_scores",
        "purpose": "Retrieve predictor and dbNSFP context as PP3/BP4 route input only.",
        "route_input_for": ["PP3/BP4"],
    },
    {
        "tool_name": "SpliceAI_predict_splice",
        "purpose": "Retrieve splice prediction as splicing/prediction route input only.",
        "route_input_for": ["splice bundle", "PP3-style prediction", "PVS1-splicing boundary"],
    },
    {
        "tool_name": "GeneBe_classify_variant",
        "purpose": "Retrieve automated ACMG-style label as source lead only.",
        "route_input_for": ["source_assertions_or_leads"],
    },
    {
        "tool_name": "InterVar_classify_variant",
        "purpose": "Retrieve automated ACMG-style label as source lead/comparator only.",
        "route_input_for": ["source_assertions_or_leads"],
    },
]

ONLINE_LITERATURE_TOOL_CALLS = [
    {
        "tool_name": "tooluniverse-literature-deep-research",
        "source_category": "literature",
        "purpose": "Run online literature discovery before final ACMG classification; record no-hit results as coverage, not as evidence.",
        "route_input_for": ["PP1/BS4/PP4", "PS4", "PS2/PM6", "PM3", "PS3/BS3"],
    },
    {
        "tool_name": "NCBI/PubMed literature search",
        "source_category": "literature",
        "purpose": "Search PubMed for variant, rsID, gene-disease, family, cohort, and functional/RNA evidence.",
        "route_input_for": ["literature coverage audit"],
    },
    {
        "tool_name": "PMC/EuropePMC full-text search",
        "source_category": "literature",
        "purpose": "Search full text, tables, supplements, and figures when abstracts or source assertions mention primary evidence.",
        "route_input_for": ["literature provenance", "full-text/supplement coverage"],
    },
    {
        "tool_name": "tooluniverse-literature-figure-evidence-extraction",
        "source_category": "literature",
        "purpose": "Extract primary evidence from figures, pedigrees, RT-PCR/minigene panels, tables, or supplements when literature hits require it.",
        "route_input_for": ["PS3/BS3", "PP1/BS4/PP4", "PS4"],
    },
]

DISCOVERY_NO_HIT_ROUTES = [
    "pp1_bs4_pp4_segregation",
    "ps4_case_enrichment",
    "de_novo_ps2_pm6",
    "pm3_in_trans",
    "ps3_bs3_functional_assay",
]


@register_tool("ACMGOverlayGateTool")
class ACMGOverlayGateTool(BaseTool):
    """Plan and validate ACMG overlay-gated assessments."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.operation = self.tool_config.get("fields", {}).get("operation", "assess_variant")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.operation != "assess_variant":
            return {"status": "error", "error": f"Unknown operation: {self.operation}"}
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "arguments must be an object"}

        output_mode = str(arguments.get("output_mode") or "compact").lower()
        if output_mode not in {"compact", "full"}:
            return {"status": "error", "error": "output_mode must be 'compact' or 'full'"}

        registry_entries = self._load_registry_entries()
        baseline_routes = self._select_baseline_routes(registry_entries, arguments)
        discovery_routes = self._select_discovery_routes(registry_entries, arguments)
        source_leads = self._normalize_source_leads(arguments.get("source_outputs_or_leads"))
        bundle = self._extract_bundle(arguments)
        validation = self._validate_bundle(bundle) if bundle else self._missing_bundle_result()

        validator_status = validation["validator_status"]
        final_allowed = validator_status == "PASS"
        classification_status = CLASSIFICATION_FINAL if final_allowed else CLASSIFICATION_DRAFT

        response = {
            "status": "success",
            "tool_role": "ACMG overlay compliance gate and preflight planner; not an ACMG classifier",
            "output_mode": output_mode,
            "classification_status": classification_status,
            "validator_status": validator_status,
            "final_classification_allowed": final_allowed,
            "variant": self._variant_summary(arguments),
            "required_baseline_routes": baseline_routes,
            "triggered_discovery_routes": discovery_routes,
            "recommended_tool_calls": self._recommended_tool_calls(arguments),
            "online_literature_query_templates": self._literature_query_templates(arguments, source_leads),
            "required_coverage_tasks": self._required_coverage_tasks(arguments, source_leads),
            "source_assertions_or_leads": source_leads,
            "acmg_assessment_bundle": bundle or self._bundle_skeleton(arguments, baseline_routes, discovery_routes, source_leads),
            "validator_result": validation.get("validator_result"),
            "violations": validation.get("violations", []),
            "next_actions": self._next_actions(validation, baseline_routes, discovery_routes),
            "acmg_gate_notice": (
                "Final germline ACMG/pathogenicity wording requires a machine-checkable "
                "acmg_assessment_bundle and validator_status: PASS. Without PASS, report "
                "draft classification only."
            ),
        }
        if output_mode == "full":
            return response
        return self._compact_response(response, bundle is not None)

    def _repo_root_candidates(self) -> Iterable[Path]:
        here = Path(__file__).resolve()
        for parent in here.parents:
            yield parent
        yield Path.cwd()

    def _find_skills_root(self) -> Path | None:
        for root in self._repo_root_candidates():
            direct = root / "skills" / "tooluniverse-acmg-overlay-routing-core"
            if direct.exists():
                return direct
            agents = root / ".agents" / "skills" / "tooluniverse-acmg-overlay-routing-core"
            if agents.exists():
                return agents
        packaged = Path(__file__).resolve().parent / "data" / "acmg_overlay_gate"
        if packaged.exists():
            return packaged
        return None

    def _load_registry_entries(self) -> List[Dict[str, Any]]:
        skills_root = self._find_skills_root()
        if not skills_root:
            return []
        registry_path = skills_root / "overlay_registry.yaml"
        try:
            payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return []
        if isinstance(payload, dict):
            entries = payload.get("overlays") or payload.get("routes") or payload.get("registry") or payload.get("criteria")
            if entries is None:
                entries = [item for item in payload.get("entries", []) if isinstance(item, dict)]
        else:
            entries = []
        if not entries and isinstance(payload, dict):
            entries = [value for value in payload.values() if isinstance(value, dict) and "criterion_group" in value]
        return [entry for entry in entries or [] if isinstance(entry, dict)]

    def _route_row(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "criterion_group": entry.get("criterion_group"),
            "covered_criteria": entry.get("covered_criteria", []),
            "overlay_skill": entry.get("overlay_skill"),
            "trigger_policy": entry.get("trigger_policy"),
            "enforcement_level": entry.get("enforcement_level"),
            "route_kind": entry.get("route_kind"),
            "applies_when": entry.get("applies_when", []),
            "baseline_data_sources": entry.get("baseline_data_sources", []),
        }

    def _compact_route_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "criterion_group": row.get("criterion_group"),
            "covered_criteria": row.get("covered_criteria", []),
            "overlay_skill": row.get("overlay_skill"),
            "trigger_policy": row.get("trigger_policy"),
            "enforcement_level": row.get("enforcement_level"),
            "route_kind": row.get("route_kind"),
        }

    def _compact_response(self, response: Dict[str, Any], bundle_present: bool) -> Dict[str, Any]:
        return {
            "status": response["status"],
            "tool_role": response["tool_role"],
            "output_mode": "compact",
            "classification_status": response["classification_status"],
            "validator_status": response["validator_status"],
            "final_classification_allowed": response["final_classification_allowed"],
            "variant": response["variant"],
            "required_baseline_route_groups": [
                self._compact_route_row(row) for row in response["required_baseline_routes"]
            ],
            "triggered_discovery_route_groups": [
                self._compact_route_row(row) for row in response["triggered_discovery_routes"]
            ],
            "recommended_tool_calls": response["recommended_tool_calls"],
            "online_literature_query_templates": response["online_literature_query_templates"],
            "required_coverage_tasks": response["required_coverage_tasks"],
            "source_assertions_or_leads": response["source_assertions_or_leads"],
            "validated_bundle_present": bundle_present,
            "acmg_assessment_bundle_status": (
                "validated_input_bundle_not_echoed" if bundle_present else "skeleton_available_with_output_mode_full"
            ),
            "bundle_required_fields": [
                "variant",
                "classification_status",
                "route_plan",
                "coverage_audit",
                "overlay_results",
                "route_audit",
                "compatibility_resolution",
            ],
            "validator_result": response["validator_result"],
            "violations": response["violations"],
            "next_actions": response["next_actions"],
            "acmg_gate_notice": response["acmg_gate_notice"],
        }

    def _select_baseline_routes(self, entries: List[Dict[str, Any]], arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        consequence_text = " ".join(str(arguments.get(key, "")) for key in ("variant", "transcript", "consequence", "variant_type")).lower()
        selected: List[Dict[str, Any]] = []
        for entry in entries:
            policy = entry.get("trigger_policy")
            if policy == "universal_baseline":
                selected.append(self._route_row(entry))
            elif policy == "variant_type_baseline" and self._variant_type_matches(entry, consequence_text):
                selected.append(self._route_row(entry))
        if selected:
            return selected
        return [
            {"criterion_group": "population_frequency_bundle", "trigger_policy": "universal_baseline", "enforcement_level": "must_query"},
            {"criterion_group": "source_assertion_review", "trigger_policy": "universal_baseline", "enforcement_level": "must_query"},
            {"criterion_group": "pvs1_applicability_gate", "trigger_policy": "universal_baseline", "enforcement_level": "must_plan"},
            {"criterion_group": "evidence_compatibility_resolution", "trigger_policy": "universal_baseline", "enforcement_level": "must_audit_if_counted"},
        ]

    def _variant_type_matches(self, entry: Dict[str, Any], consequence_text: str) -> bool:
        applies = " ".join(str(item).lower() for item in entry.get("applies_when", []))
        group = str(entry.get("criterion_group", "")).lower()
        if "missense" in applies or "missense" in group:
            return "missense" in consequence_text or "p." in consequence_text
        if "splice" in applies or "splice" in group:
            return "splice" in consequence_text or "+" in consequence_text or "-" in consequence_text
        if "lof" in applies or "lof" in group:
            return any(term in consequence_text for term in ("stop", "frameshift", "nonsense", "splice_acceptor", "splice_donor"))
        if "protein_length" in applies or "pm4" in group:
            return any(term in consequence_text for term in ("in-frame", "inframe", "del", "ins", "dup"))
        return False

    def _select_discovery_routes(self, entries: List[Dict[str, Any]], arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        haystack = json.dumps(arguments, ensure_ascii=False).lower()
        trigger_terms = {
            "pp1": ("segregation", "family", "pedigree", "affected", "mother", "father", "grandmother", "cascade", "家系", "共分离", "母亲", "父亲", "外婆", "外祖母", "患病亲属"),
            "ps4": ("case-control", "cohort", "odds ratio", "recurrence", "case series", "病例对照", "队列", "复现", "病例系列"),
            "ps3": ("functional", "assay", "rt-pcr", "rna", "minigene", "mavedb", "mave", "功能实验", "剪接实验", "转录", "迷你基因"),
            "ps2": ("de novo", "trio", "parental", "新发", "三联体", "父母验证"),
            "pm3": ("in trans", "biallelic", "phase", "compound heterozyg", "反式", "双等位", "相位", "复合杂合"),
        }
        selected: List[Dict[str, Any]] = []
        for entry in entries:
            if entry.get("trigger_policy") != "evidence_discovery":
                continue
            text = json.dumps(entry, ensure_ascii=False).lower()
            if any(any(term in haystack for term in terms) and key in text for key, terms in trigger_terms.items()):
                selected.append(self._route_row(entry))
        return selected

    def _recommended_tool_calls(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        calls = list(ONLINE_LITERATURE_TOOL_CALLS) + list(BASE_RECOMMENDED_TOOL_CALLS)
        variant_text = str(arguments.get("variant", ""))
        if variant_text and ("+" in variant_text or "-" in variant_text or "splice" in variant_text.lower()):
            calls.insert(0, {
                "tool_name": "EnsemblVEP_variant_recoder",
                "purpose": "Map transcript HGVS to genomic coordinates before SpliceAI/GeneBe/InterVar calls.",
                "route_input_for": ["normalization", "splice bundle"],
            })
        return calls

    def _literature_query_templates(self, arguments: Dict[str, Any], source_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        gene = str(arguments.get("gene") or "").strip()
        variant = str(arguments.get("variant") or "").strip()
        transcript = str(arguments.get("transcript") or "").strip()
        phenotype = str(arguments.get("phenotype_context") or arguments.get("disease_context") or "").strip()
        family = str(arguments.get("family_context") or "").strip()
        source_text = json.dumps([lead.get("raw_source") for lead in source_leads], ensure_ascii=False).lower()
        rsids = sorted(set(token for token in source_text.replace(",", " ").split() if token.startswith("rs") and token[2:].isdigit()))

        base_terms = [term for term in (gene, transcript, variant) if term]
        queries: List[Dict[str, Any]] = []
        if base_terms:
            queries.append({
                "purpose": "variant_specific_literature",
                "query": " ".join(base_terms),
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        for rsid in rsids:
            queries.append({
                "purpose": "rsid_literature",
                "query": f"{gene} {rsid}".strip(),
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        if gene and phenotype:
            queries.append({
                "purpose": "gene_phenotype_literature",
                "query": f"{gene} {phenotype}",
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        if gene and (family or phenotype):
            queries.append({
                "purpose": "segregation_family_literature",
                "query": f"{gene} segregation family pedigree affected relatives",
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        if gene:
            queries.append({
                "purpose": "functional_splicing_literature",
                "query": f"{gene} {variant} RT-PCR RNA minigene cryptic splice intron retention".strip(),
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
            queries.append({
                "purpose": "case_enrichment_literature",
                "query": f"{gene} {variant} cohort case series recurrence".strip(),
                "sources": ["PubMed", "PMC", "EuropePMC"],
            })
        return queries

    def _required_coverage_tasks(self, arguments: Dict[str, Any], source_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "source_category": "literature",
                "required_before_final": True,
                "must_be_online": True,
                "acceptable_query_status": ["success", "no_hit", "failed", "unavailable"],
                "required_fields": ["queried_sources", "query_terms", "query_tool_or_time", "query_status", "reason", "not_triggered_routes"],
                "not_triggered_routes_if_no_hit": DISCOVERY_NO_HIT_ROUTES,
                "reason": "Final classification requires actual online literature discovery; no-hit is acceptable, no-search is not.",
            },
            {
                "source_category": "population",
                "required_before_final": True,
                "reason": "Population frequency outputs are coverage inputs; BA1/BS1/PM2 require overlay routing.",
            },
            {
                "source_category": "computational",
                "required_before_final": True,
                "reason": "VEP/SpliceAI/MyVariant/CADD/SIFT/PolyPhen outputs are route inputs, not counted evidence.",
            },
            {
                "source_category": "source_assertion",
                "required_before_final": bool(source_leads),
                "reason": "GeneBe/InterVar/ClinVar/lab/paper assertions are source leads and must not be counted directly.",
            },
            {
                "source_category": "functional_database",
                "required_before_final": True,
                "reason": "MaveDB/DMS hits trigger PS3/BS3 overlay; no-hit is documented coverage.",
            },
            {
                "source_category": "disease_context",
                "required_before_final": True,
                "reason": "ClinGen/G2P/GeneReviews resolve disease/mechanism context but do not count as ACMG evidence.",
            },
            {
                "source_category": "clinical_context",
                "required_before_final": bool(arguments.get("family_context") or arguments.get("phenotype_context")),
                "reason": "User-supplied family/phenotype context triggers PP1/PP4 intake but does not assign strength directly.",
            },
        ]

    def _normalize_source_leads(self, value: Any) -> List[Dict[str, Any]]:
        if value in (None, ""):
            return []
        raw_items = value if isinstance(value, list) else [value]
        leads: List[Dict[str, Any]] = []
        for item in raw_items:
            text = json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item)
            lowered = text.lower()
            source_type = "source_output"
            for keyword in SOURCE_LEAD_KEYWORDS:
                if keyword in lowered:
                    source_type = keyword.replace(" ", "_")
                    break
            leads.append({
                "source_type": source_type,
                "raw_source": item,
                "countable": False,
                "reason": SOURCE_LEAD_NOTICE,
            })
        return leads

    def _extract_bundle(self, arguments: Dict[str, Any]) -> Dict[str, Any] | None:
        bundle = arguments.get("acmg_assessment_bundle") or arguments.get("assessment_bundle") or arguments.get("bundle")
        if isinstance(bundle, dict):
            return bundle
        return None

    def _validate_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        skills_root = self._find_skills_root()
        if not skills_root:
            return {
                "validator_status": VALIDATOR_DRAFT_ONLY,
                "violations": [{"code": "validator_unavailable", "message": "ACMG overlay validator script was not found."}],
                "validator_result": None,
            }
        script = skills_root / "scripts" / "validate_acmg_overlay_bundle.py"
        if not script.exists():
            return {
                "validator_status": VALIDATOR_DRAFT_ONLY,
                "violations": [{"code": "validator_unavailable", "message": str(script)}],
                "validator_result": None,
            }
        payload = {"acmg_assessment_bundle": bundle}
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False)
            tmp_path = Path(handle.name)
        try:
            proc = subprocess.run(
                [sys.executable, str(script), str(tmp_path)],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            result = json.loads(proc.stdout) if proc.stdout.strip() else {"status": VALIDATOR_DRAFT_ONLY, "violations": []}
        except Exception as exc:
            result = {"status": VALIDATOR_DRAFT_ONLY, "violations": [{"code": "validator_error", "message": str(exc)}]}
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return {
            "validator_status": result.get("status", VALIDATOR_DRAFT_ONLY),
            "violations": result.get("violations", []),
            "validator_result": result,
        }

    def _missing_bundle_result(self) -> Dict[str, Any]:
        return {
            "validator_status": VALIDATOR_DRAFT_ONLY,
            "violations": [{"code": "missing_acmg_assessment_bundle", "message": "No machine-checkable ACMG assessment bundle was provided."}],
            "validator_result": {"status": VALIDATOR_NOT_RUN, "reason": "No bundle provided."},
        }

    def _bundle_skeleton(self, arguments: Dict[str, Any], baseline_routes: List[Dict[str, Any]], discovery_routes: List[Dict[str, Any]], source_leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "variant": self._variant_summary(arguments),
            "classification_status": CLASSIFICATION_DRAFT,
            "route_plan": baseline_routes + discovery_routes,
            "coverage_audit": [],
            "coverage_audit_note": "Populate coverage_audit only after actual queries. Literature coverage must come from online PubMed/PMC/EuropePMC or ToolUniverse literature search; no-hit is acceptable, no-search is not.",
            "overlay_results": [],
            "route_audit": [],
            "compatibility_resolution": {"current_counted_evidence_resolved": [], "unresolved_conflicts": []},
            "source_assertions_or_leads": source_leads,
        }

    def _variant_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "variant": arguments.get("variant"),
            "gene": arguments.get("gene"),
            "transcript": arguments.get("transcript"),
            "disease_context": arguments.get("disease_context"),
            "phenotype_context": arguments.get("phenotype_context"),
            "family_context": arguments.get("family_context"),
        }

    def _next_actions(self, validation: Dict[str, Any], baseline_routes: List[Dict[str, Any]], discovery_routes: List[Dict[str, Any]]) -> List[str]:
        actions = []
        if validation.get("validator_status") != "PASS":
            actions.append("Keep classification_status as draft classification until validator_status is PASS.")
            actions.append("Populate route_plan, coverage_audit, overlay_results, route_audit, and compatibility_resolution in acmg_assessment_bundle.")
            actions.append("Run online literature discovery before final classification; record no-hit literature searches with queried sources, query terms, tool/time, reason, and not_triggered_routes.")
        if baseline_routes:
            actions.append("Run or document all applicable baseline routes before evidence assignment.")
        if discovery_routes:
            actions.append("Run triggered discovery overlays before counting family, functional, cohort, de novo, or phase evidence.")
        actions.append("Treat SpliceAI/VEP/MyVariant/gnomAD/MaveDB/ClinGen/G2P and user family or phenotype input as coverage hits or route triggers until overlay audit passes.")
        actions.append("Keep GeneBe, InterVar, ClinVar, lab, and paper labels in source_assertions_or_leads unless primary evidence is routed.")
        return actions
