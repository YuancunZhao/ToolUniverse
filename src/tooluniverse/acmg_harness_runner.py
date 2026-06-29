"""Executable ACMG overlay harness for ToolUniverse variant assessments.

The harness orchestrates existing ToolUniverse tools and produces a structured
assessment bundle. It intentionally does not replace criterion-specific medical
rules or the final combiner.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from .acmg_gate_policy import SOURCE_LEAD_NOTICE


CLASSIFICATION_DRAFT = "draft classification"


@dataclass
class ToolCallResult:
    tool_name: str
    arguments: Dict[str, Any]
    source_category: str
    status: str
    result: Any = None
    error: str | None = None

    def as_dict(self) -> Dict[str, Any]:
        payload = {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "source_category": self.source_category,
            "query_status": self.status,
        }
        if self.error:
            payload["error"] = self.error
        else:
            payload["result"] = self.result
        return payload


class ACMGHarnessRunner:
    """Run evidence intake, lightweight overlay adapters, and bundle assembly."""

    def __init__(
        self,
        run_tool: Callable[[str, Dict[str, Any]], Any],
        registry_entries: List[Dict[str, Any]],
        route_row: Callable[[Dict[str, Any]], Dict[str, Any]],
        select_baseline_routes: Callable[[List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]],
    ) -> None:
        self.run_tool = run_tool
        self.registry_entries = registry_entries
        self.route_row = route_row
        self.select_baseline_routes = select_baseline_routes

    def assess(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        variant = str(arguments.get("variant") or "")
        gene = str(arguments.get("gene") or "")
        transcript = str(arguments.get("transcript") or "")

        tool_calls = self._collect_evidence(variant, gene, transcript)
        source_leads = self._source_leads(tool_calls, arguments.get("source_outputs_or_leads"))
        derived = self._derive_identifiers(variant, tool_calls)
        coverage_audit = self._coverage_audit(tool_calls, derived)
        candidate_evidence = self._candidate_evidence(tool_calls, derived)
        route_plan = self._route_plan(arguments, candidate_evidence)
        overlay_results, route_audit = self._overlay_adapters(candidate_evidence)
        bundle = self._bundle(arguments, derived, route_plan, coverage_audit, overlay_results, route_audit, source_leads)

        return {
            "tool_calls": [row.as_dict() for row in tool_calls],
            "derived_identifiers": derived,
            "coverage_audit": coverage_audit,
            "coverage_audit_summary": self._coverage_summary(coverage_audit),
            "candidate_evidence": candidate_evidence,
            "overlay_results": overlay_results,
            "route_audit": route_audit,
            "source_assertions_or_leads": source_leads,
            "acmg_assessment_bundle": bundle,
            "missing_for_final": self._missing_for_final(coverage_audit, overlay_results, route_audit),
        }

    def _safe_call(self, tool_name: str, arguments: Dict[str, Any], source_category: str) -> ToolCallResult:
        try:
            result = self.run_tool(tool_name, arguments)
        except Exception as exc:
            return ToolCallResult(tool_name, arguments, source_category, "failed", error=str(exc))
        if isinstance(result, dict) and result.get("status") == "error":
            return ToolCallResult(tool_name, arguments, source_category, "failed", result=result, error=str(result.get("error") or result))
        return ToolCallResult(tool_name, arguments, source_category, self._query_status(result), result=result)

    def _collect_evidence(self, variant: str, gene: str, transcript: str) -> List[ToolCallResult]:
        calls: List[ToolCallResult] = []
        if variant:
            calls.append(self._safe_call("EnsemblVEP_variant_recoder", {"variant_id": variant}, "computational"))

        derived = self._derive_identifiers(variant, calls)
        splice_variant = derived.get("spliceai_variant") or variant
        if splice_variant:
            calls.append(self._safe_call("SpliceAI_predict_splice", {"variant": splice_variant, "genome": "38"}, "computational"))

        lookup_ids = [value for value in (derived.get("rsid"), derived.get("hgvs_g"), variant) if value]
        seen_ids = set()
        for lookup_id in lookup_ids:
            if lookup_id in seen_ids:
                continue
            seen_ids.add(lookup_id)
            calls.append(self._safe_call("ClinVar_get_clinical_significance", {"variant_id": lookup_id}, "source_assertion"))
            calls.append(self._safe_call("MyVariant_get_pathogenicity_scores", {"variant_id": lookup_id}, "computational"))
            calls.append(self._safe_call("EnsemblVar_get_population_frequencies", {"variant_id": lookup_id}, "population"))

        genomic = derived.get("genomic_parts") or {}
        if genomic:
            calls.append(self._safe_call("GeneBe_classify_variant", {**genomic, "genome": "hg38"}, "source_assertion"))
            calls.append(self._safe_call("InterVar_classify_variant", {
                "chrom": genomic["chr"],
                "pos": genomic["pos"],
                "ref": genomic["ref"],
                "alt": genomic["alt"],
                "build": "hg38",
            }, "source_assertion"))
            gnomad_id = f"{genomic['chr']}-{genomic['pos']}-{genomic['ref']}-{genomic['alt']}"
            calls.append(self._safe_call("gnomad_get_variant", {"variant_id": gnomad_id, "dataset": "gnomad_r4"}, "population"))
            calls.append(self._safe_call("gnomad_get_variant_populations", {"variant_id": gnomad_id, "dataset": "gnomad_r4"}, "population"))

        lit_queries = [query for query in (f"{gene} {variant}".strip(), derived.get("rsid"), f"{gene} {derived.get('hgvs_c', '')}".strip()) if query]
        seen_queries = set()
        for query in lit_queries:
            if query in seen_queries:
                continue
            seen_queries.add(query)
            calls.append(self._safe_call("LitVar_search_variants", {"query": query}, "literature"))
            calls.append(self._safe_call("EuropePMC_search_articles", {"query": query, "limit": 5}, "literature"))
        if derived.get("rsid"):
            calls.append(self._safe_call("LitVar_get_variant_publications", {"rsid": derived["rsid"], "max": 10}, "literature"))

        pmids = self._extract_pmids([row.result for row in calls])
        for pmid in pmids[:5]:
            calls.append(self._safe_call("PubMed_get_article", {"pmid": pmid}, "literature"))

        if gene:
            calls.append(self._safe_call("ClinGen_search_gene_validity", {"gene": gene}, "disease_context"))
            calls.append(self._safe_call("MedGen_search_conditions", {"term": gene, "max_results": 10}, "disease_context"))

        return calls

    def _query_status(self, result: Any) -> str:
        if result in (None, "", [], {}):
            return "no_hit"
        if isinstance(result, dict):
            if result.get("status") in {"error", "failed"}:
                return "failed"
            if not result.get("result", result) and len(result) <= 2:
                return "no_hit"
        return "success"

    def _derive_identifiers(self, variant: str, calls: List[ToolCallResult]) -> Dict[str, Any]:
        text = " ".join([variant, *[self._text(row.result) for row in calls]])
        rsid = self._first_match(text, r"\brs\d+\b")
        hgvs_g = self._first_match(text, r"NC_0+\d+\.\d+:g\.\d+[ACGT]>[ACGT]")
        hgvs_c = self._first_match(text, r"N[MR]_\d+(?:\.\d+)?:c\.[A-Za-z0-9_+\->]+")
        genomic_parts = self._genomic_parts(text)
        spliceai_variant = None
        if genomic_parts:
            spliceai_variant = f"chr{genomic_parts['chr']}-{genomic_parts['pos']}-{genomic_parts['ref']}-{genomic_parts['alt']}"
        return {
            "rsid": rsid,
            "hgvs_g": hgvs_g,
            "hgvs_c": hgvs_c,
            "genomic_parts": genomic_parts,
            "spliceai_variant": spliceai_variant,
        }

    def _genomic_parts(self, text: str) -> Dict[str, Any] | None:
        match = re.search(r"NC_0*(\d+)\.\d+:g\.(\d+)([ACGT])>([ACGT])", text)
        if not match:
            match = re.search(r"\bchr?([0-9XYM]+)[:\-](\d+)[:\-]([ACGT])[:\-]([ACGT])\b", text, re.IGNORECASE)
        if not match:
            return None
        chrom = match.group(1).lstrip("0") or match.group(1)
        return {"chr": chrom, "pos": int(match.group(2)), "ref": match.group(3), "alt": match.group(4)}

    def _first_match(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else None

    def _extract_pmids(self, values: List[Any]) -> List[str]:
        pmids = sorted(set(re.findall(r"\b\d{7,9}\b", self._text(values))))
        return pmids

    def _source_leads(self, tool_calls: List[ToolCallResult], supplied: Any) -> List[Dict[str, Any]]:
        leads = []
        for row in tool_calls:
            if row.source_category != "source_assertion":
                continue
            leads.append({
                "source_type": row.tool_name,
                "raw_source": row.result if row.status == "success" else row.as_dict(),
                "countable": False,
                "reason": SOURCE_LEAD_NOTICE,
            })
        if supplied:
            raw_items = supplied if isinstance(supplied, list) else [supplied]
            for item in raw_items:
                leads.append({"source_type": "supplied_source_output", "raw_source": item, "countable": False, "reason": SOURCE_LEAD_NOTICE})
        return leads

    def _coverage_audit(self, tool_calls: List[ToolCallResult], derived: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = []
        for category in ("population", "computational", "source_assertion", "literature", "disease_context", "functional_database", "clinical_context"):
            category_calls = [row for row in tool_calls if row.source_category == category]
            status = self._category_status(category_calls, category)
            hits = [row.as_dict() for row in category_calls if row.status == "success"][:8]
            triggered = self._triggered_routes(category, hits)
            not_triggered = [route for route in ("pp1_bs4_pp4_segregation", "ps4_case_enrichment", "de_novo_ps2_pm6", "pm3_in_trans", "ps3_bs3_functional_assay") if route not in triggered]
            rows.append({
                "source_category": category,
                "queried_sources": [row.tool_name for row in category_calls] or [category],
                "query_terms": [str(value) for value in (derived.get("rsid"), derived.get("hgvs_g"), derived.get("hgvs_c")) if value],
                "query_tool": "ToolUniverse ACMG harness",
                "query_status": status,
                "hits": hits,
                "triggered_routes": triggered,
                "not_triggered_routes": not_triggered if category == "literature" else [],
                "reason": f"{category} coverage collected by ACMG harness." if category_calls else f"{category} coverage not available to harness.",
            })
        return rows

    def _category_status(self, calls: List[ToolCallResult], category: str) -> str:
        if category in {"functional_database", "clinical_context"} and not calls:
            return "not_applicable"
        if not calls:
            return "unavailable"
        if any(row.status == "success" for row in calls):
            return "success"
        if any(row.status == "failed" for row in calls):
            return "failed"
        return "no_hit"

    def _triggered_routes(self, category: str, hits: List[Dict[str, Any]]) -> List[str]:
        text = self._text(hits).lower()
        routes = []
        if category == "literature":
            if any(term in text for term in ("minigene", "functional", "in vitro", "rt-pcr", "splicing assay")):
                routes.append("ps3_bs3_functional_assay")
            if any(term in text for term in ("de novo", "denovo", "trio", "parental")):
                routes.append("de_novo_ps2_pm6")
            if any(term in text for term in ("case series", "recurrence", "cohort", "unrelated", "additional patient")):
                routes.append("ps4_case_enrichment")
            if any(term in text for term in ("segregation", "pedigree", "family", "cascade")):
                routes.append("pp1_bs4_pp4_segregation")
        if category == "computational" and any(term in text for term in ("spliceai", "donor gain", "acceptor gain", "ds_dg", "ds_ag")):
            routes.append("pp3_bp4_missense_prediction")
        return sorted(set(routes))

    def _candidate_evidence(self, tool_calls: List[ToolCallResult], derived: Dict[str, Any]) -> List[Dict[str, Any]]:
        evidence = []
        successful_results = [row.result for row in tool_calls if row.status == "success"]
        all_text = self._text(successful_results)
        lower = all_text.lower()
        if self._has_population_absence(tool_calls):
            evidence.append({"criterion": "PM2", "candidate_strength": "supporting_candidate", "source_category": "population", "reason": "Population tools did not return a usable frequency hit; requires PM2 overlay adjudication."})
        if any(term in lower for term in ("spliceai", "donor gain", "acceptor gain", "ds_dg", "ds_ag")):
            evidence.append({"criterion": "PP3", "candidate_strength": "prediction_candidate", "source_category": "computational", "reason": "Computational/splicing prediction signal detected; requires PP3/BP4 or splicing overlay."})
        if any(term in lower for term in ("minigene", "functional", "in vitro", "rt-pcr", "aberrant splicing", "exonization")):
            evidence.append({"criterion": "PS3", "candidate_strength": "functional_candidate", "source_category": "literature", "reason": "Functional or RNA/splicing assay language detected in literature/source hits."})
        if any(term in lower for term in ("de novo", "denovo")):
            evidence.append({"criterion": "PS2", "candidate_strength": "de_novo_candidate", "source_category": "literature", "reason": "De novo language detected; requires PS2/PM6 overlay."})
        if any(term in lower for term in ("case series", "recurrence", "cohort", "unrelated", "additional patient")):
            evidence.append({"criterion": "PS4", "candidate_strength": "case_enrichment_candidate", "source_category": "literature", "reason": "Case recurrence/enrichment language detected; requires PS4 overlay."})
        if any(term in lower for term in ("clinvar", "genebe", "intervar", "pathogenic", "likely_pathogenic", "likely pathogenic")):
            evidence.append({"criterion": "PP5", "candidate_strength": "source_lead_only", "source_category": "source_assertion", "reason": "Automated/database assertion detected; source lead only, not counted."})
        if any(term in lower for term in ("in-frame", "inframe", "in frame", "insertion", "retention")):
            evidence.append({"criterion": "PM4", "candidate_strength": "protein_length_candidate", "source_category": "computational", "reason": "Protein length or in-frame consequence language detected; requires PM4/BP3 overlay."})
        if not evidence:
            evidence.append({"criterion": "none", "candidate_strength": "no_candidate_trigger", "source_category": "harness", "reason": "No candidate ACMG evidence triggers were detected from tool outputs."})
        return evidence

    def _has_population_absence(self, tool_calls: List[ToolCallResult]) -> bool:
        population_calls = [row for row in tool_calls if row.source_category == "population"]
        return bool(population_calls) and not any(row.status == "success" for row in population_calls)

    def _route_plan(self, arguments: Dict[str, Any], candidate_evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        route_plan = self.select_baseline_routes(self.registry_entries, arguments)
        wanted = {self._criterion_to_group(row.get("criterion")) for row in candidate_evidence}
        existing = {row.get("criterion_group") for row in route_plan if isinstance(row, dict)}
        for entry in self.registry_entries:
            group = entry.get("criterion_group")
            if group in wanted and group not in existing:
                route_plan.append(self.route_row(entry))
                existing.add(group)
        return route_plan

    def _criterion_to_group(self, criterion: Any) -> str:
        return {
            "PM2": "pm2_absence_rarity",
            "PP3": "pp3_bp4_missense_prediction",
            "PS3": "ps3_bs3_functional_assay",
            "PS2": "de_novo_ps2_pm6",
            "PS4": "ps4_case_enrichment",
            "PP1": "pp1_bs4_pp4_segregation",
            "PP5": "reputable_source_review",
            "PM4": "pm4_bp3_protein_length",
        }.get(str(criterion), "")

    def _overlay_adapters(self, candidate_evidence: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        overlay_results = []
        route_audit = []
        for candidate in candidate_evidence:
            criterion = str(candidate.get("criterion"))
            if criterion == "none":
                continue
            overlay = self._criterion_overlay(criterion)
            status = "not_used" if criterion in {"PP5"} else "not_assessed"
            applied = None
            reason = candidate.get("reason", "")
            overlay_results.append({
                "overlay_skill": overlay,
                "criterion": criterion,
                "applied_evidence": applied,
                "status": status,
                "guidance_authority": "source lead only" if criterion == "PP5" else "ACMG/AMP baseline",
                "reason": f"Harness detected candidate evidence. {reason} Overlay-specific strength assignment still required before counting.",
                "consumed_evidence": [candidate],
            })
            route_audit.append({
                "criterion": criterion,
                "proposed_evidence": candidate.get("candidate_strength"),
                "route_outcome": "overlay_not_assessed",
                "overlay_or_vcep_source": overlay,
                "counted": False,
                "guidance_authority": "source lead only" if criterion == "PP5" else "ACMG/AMP baseline",
                "reason": "Harness generated a route candidate only; evidence is not counted until the overlay applies or VCEP defers it.",
            })
        return overlay_results, route_audit

    def _criterion_overlay(self, criterion: str) -> str:
        return {
            "PM2": "tooluniverse-acmg-pm2-absence-rarity-refinement",
            "PP3": "tooluniverse-acmg-pp3-bp4-missense-prediction-refinement",
            "PS3": "tooluniverse-acmg-ps3-bs3-functional-assay-refinement",
            "PS2": "tooluniverse-acmg-de-novo-evidence-refinement",
            "PS4": "tooluniverse-acmg-ps4-case-enrichment-refinement",
            "PP1": "tooluniverse-acmg-pp1-segregation-refinement",
            "PP5": "tooluniverse-acmg-pp5-bp6-reputable-source-refinement",
            "PM4": "tooluniverse-acmg-pm4-bp3-protein-length-refinement",
        }.get(criterion, "tooluniverse-acmg-overlay-routing-core")

    def _bundle(
        self,
        arguments: Dict[str, Any],
        derived: Dict[str, Any],
        route_plan: List[Dict[str, Any]],
        coverage_audit: List[Dict[str, Any]],
        overlay_results: List[Dict[str, Any]],
        route_audit: List[Dict[str, Any]],
        source_leads: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        variant = {
            "gene": arguments.get("gene"),
            "transcript": arguments.get("transcript"),
            "hgvs_c": derived.get("hgvs_c") or arguments.get("variant"),
            "hgvs_g": derived.get("hgvs_g"),
            "consequence": arguments.get("consequence") or arguments.get("variant_type"),
            "assessment_context": "germline",
        }
        return {
            "variant": variant,
            "classification_status": CLASSIFICATION_DRAFT,
            "disease_context": self._context(arguments, "disease_context"),
            "penetrance_context": self._penetrance_context(),
            "vcep_context": self._vcep_context(),
            "route_plan": route_plan,
            "coverage_audit": coverage_audit,
            "overlay_results": overlay_results,
            "route_audit": route_audit,
            "compatibility_resolution": {
                "current_counted_evidence_resolved": [],
                "unresolved_conflicts": [],
                "not_used_due_to_overlap": [],
                "caps_applied": [],
                "context_splits": [],
            },
            "source_assertions_or_leads": source_leads,
        }

    def _context(self, arguments: Dict[str, Any], key: str) -> Dict[str, Any]:
        supplied = arguments.get(key)
        return {
            "disease_entity": supplied or arguments.get("phenotype_context") or "unknown",
            "inheritance": "unknown",
            "mechanism": "unknown",
            "source": "ToolUniverse ACMG harness intake",
            "status": "partial" if supplied else "unknown",
        }

    def _penetrance_context(self) -> Dict[str, Any]:
        return {
            "penetrance_type": "unknown",
            "unaffected_carrier_interpretability": "unknown",
            "source": "ToolUniverse ACMG harness intake",
            "criteria_affected": ["BS1", "BS2", "BS4", "PP1", "PP4", "PM2", "PS4"],
            "status": "unknown",
        }

    def _vcep_context(self) -> Dict[str, Any]:
        return {
            "vcep_available": False,
            "scope_match": "unknown",
            "source": "ToolUniverse ACMG harness intake",
            "criteria_overridden": [],
            "generic_overlay_responsibilities": ["all triggered generic overlays"],
            "reason": "Harness does not assume VCEP scope without an explicit VCEP lookup/result.",
        }

    def _coverage_summary(self, coverage: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "source_category": row.get("source_category"),
                "query_status": row.get("query_status"),
                "hit_count": len(row.get("hits") or []),
                "triggered_routes": row.get("triggered_routes", []),
            }
            for row in coverage
        ]

    def _missing_for_final(self, coverage: List[Dict[str, Any]], overlay_results: List[Dict[str, Any]], route_audit: List[Dict[str, Any]]) -> List[str]:
        missing = []
        for row in coverage:
            if row.get("source_category") in {"literature", "population", "computational", "disease_context"} and row.get("query_status") in {"failed", "unavailable"}:
                missing.append(f"{row.get('source_category')} coverage is {row.get('query_status')}")
        if not any(row.get("counted") is True for row in route_audit):
            missing.append("no overlay-applied counted evidence; final classification remains draft")
        if any(row.get("status") == "not_assessed" for row in overlay_results):
            missing.append("one or more triggered overlay adapters require criterion-specific assessment before counting")
        return missing

    def _text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            return str(value)
