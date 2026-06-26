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

        registry_entries = self._load_registry_entries()
        baseline_routes = self._select_baseline_routes(registry_entries, arguments)
        discovery_routes = self._select_discovery_routes(registry_entries, arguments)
        source_leads = self._normalize_source_leads(arguments.get("source_outputs_or_leads"))
        bundle = self._extract_bundle(arguments)
        validation = self._validate_bundle(bundle) if bundle else self._missing_bundle_result()

        validator_status = validation["validator_status"]
        final_allowed = validator_status == "PASS"
        classification_status = CLASSIFICATION_FINAL if final_allowed else CLASSIFICATION_DRAFT

        return {
            "status": "success",
            "tool_role": "ACMG overlay compliance gate and preflight planner; not an ACMG classifier",
            "classification_status": classification_status,
            "validator_status": validator_status,
            "final_classification_allowed": final_allowed,
            "variant": self._variant_summary(arguments),
            "required_baseline_routes": baseline_routes,
            "triggered_discovery_routes": discovery_routes,
            "recommended_tool_calls": self._recommended_tool_calls(arguments),
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
            "pp1": ("segregation", "family", "pedigree", "affected", "mother", "father", "grandmother", "cascade"),
            "ps4": ("case-control", "cohort", "odds ratio", "recurrence", "case series"),
            "ps3": ("functional", "assay", "rt-pcr", "rna", "minigene", "mavedb", "mave"),
            "ps2": ("de novo", "trio", "parental"),
            "pm3": ("in trans", "biallelic", "phase", "compound heterozyg"),
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
        calls = list(BASE_RECOMMENDED_TOOL_CALLS)
        variant_text = str(arguments.get("variant", ""))
        if variant_text and ("+" in variant_text or "-" in variant_text or "splice" in variant_text.lower()):
            calls.insert(0, {
                "tool_name": "EnsemblVEP_variant_recoder",
                "purpose": "Map transcript HGVS to genomic coordinates before SpliceAI/GeneBe/InterVar calls.",
                "route_input_for": ["normalization", "splice bundle"],
            })
        return calls

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
        if baseline_routes:
            actions.append("Run or document all applicable baseline routes before evidence assignment.")
        if discovery_routes:
            actions.append("Run triggered discovery overlays before counting family, functional, cohort, de novo, or phase evidence.")
        actions.append("Keep GeneBe, InterVar, ClinVar, lab, and paper labels in source_assertions_or_leads unless primary evidence is routed.")
        return actions
