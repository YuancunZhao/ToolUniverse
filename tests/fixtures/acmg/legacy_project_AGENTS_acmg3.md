# ACMG Guard — DO NOT REMOVE

You are operating with ToolUniverse ACMG gate enforcement (v3 evidence-only runtime, commit 07973c6, version 1.4.0+acmg.3).

## ACMG TOOLS (use only these 8)

- ACMG_evidence_collector — the single full-pipeline entry point
- ACMG_population_evidence, ACMG_computational_evidence,
  ACMG_clinical_evidence, ACMG_functional_evidence, ACMG_literature_evidence
- ACMG_overlay_gate_assess_variant — thin compatibility alias of the
  collector (same parameters and return structure, no separate logic)
- ACMG_guard_final_answer — fail-closed guard for final wording

All tools run through execute_tool in compact MCP mode.

## HARD RULES

1. For ANY variant pathogenicity / ACMG classification question:
   → FIRST call ACMG_evidence_collector with the variant and gene
     (variant, gene, transcript, genome_build, disease, inheritance,
     optional clinical_context / clinical_observations)
   → It returns evidence_cards with calculation_roles (automatic /
     verified / user_selected), criterion_reviews, automatic_bayesian /
     verified_bayesian / scenario_estimates (review estimates, NOT
     clinical classifications), vcep_context, and guard_context.

2. NEVER call these tools directly: GeneBe, InterVar, ClinVar, SpliceAI,
   VEP, gnomAD, MyVariant, CADD, AlphaMissense, REVEL.
   They are SOURCE LEADS ONLY — the collector calls them automatically.
   Direct calls produce quarantined outputs.

3. NEVER output Pathogenic / Likely Pathogenic / VUS / Likely Benign /
   Benign / 可能致病 / 可能良性 / 致病 / 良性 as final ACMG
   classification. final_classification_allowed is ALWAYS false in this
   evidence-only runtime; no five-tier label is ever permitted.

4. If the collector returns degraded/partial: state "evidence collection
   incomplete", list the failed/no-result sources from source_facts /
   coverage_summary / limitations (e.g. required_provider_incomplete,
   provider_contract_malformed), and recommend next actions. Provider
   failures must remain visible — never silently replace them with
   unverified manual evidence. Do not upgrade review estimates to final.

5. Before final answer, run ACMG_guard_final_answer with
   final_answer_text and the collector result / guard_context. The
   response has top-level fields status (BLOCK/PASS), cards_used,
   card_roles, unsupported_codes, blocking_reasons.
   - If status is BLOCK, fix the answer and re-run: any ACMG criterion you
     cite MUST have a corresponding EvidenceCard (see cards_used /
     card_roles); five-tier labels are always blocked.
   - guard_context is self-checking (context_hash covers schema version,
     variant identity, ruleset, cards, source-fact IDs). A modified or
     truncated context fails closed — do not bypass or strip it.
   - Source labels (GeneBe, ClinVar, InterVar) may be cited but must be
     labeled as "source lead only — not independently verified."

6. NEVER read SKILL.md files for ACMG criterion judgment. SKILL.md files
   are HUMAN REFERENCE ONLY.
   → INSTEAD: Call ACMG_evidence_collector (the single full-pipeline entry
     point) and review its evidence_cards and Bayesian estimates.
   → Review cards, then re-call the collector with evidence_decisions
     (accept / reject card_id; strength_override must preserve criterion
     direction and include a reason) for user-selected estimates.
   → ACMG_overlay_gate_assess_variant is only a thin compatibility alias —
     never call it as a separate route or expect different behavior.

7. NEVER invoke read_skill, slash commands (/tooluniverse-acmg-*), or
   run_skill for ACMG criterion evaluation. Use the MCP tools instead.
   The only valid ACMG workflow is: ACMG_evidence_collector → review
   EvidenceCards & Bayesian estimates → evidence_decisions (optional) →
   ACMG_guard_final_answer before final answer. The runtime is
   evidence-only; it does not issue five-tier classifications.

8. Fail-closed specifics:
   - PM3 requires unique phase and second-allele identity. If variant
     identity or phase is ambiguous, no positive PM3 card is emitted and
     no downstream call proceeds — do not fabricate in-trans evidence.
   - SpliceAI must be read as four separate delta channels DS_AG / DS_AL /
     DS_DG / DS_DL; spliceai_max_delta is their maximum and is NOT
     synonymous with donor loss. Report all four channels.
   - PVS1 requires the deterministic ClinGen/SVI decision tree with
     versioned splice thresholds; missing splice facts stay visible as
     missing requirements — caller booleans cannot complete the tree.
   - PP5/BP6 remain deprecated; database classifications, actionability,
     constraint metrics, and uncalibrated predictor outputs are source
     assertions only, never criteria by themselves.
