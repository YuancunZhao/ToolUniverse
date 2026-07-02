# ToolUniverse

For any scientific research question involving drugs, genes, proteins, diseases, literature, clinical trials, variants, or other biomedical/scientific databases, use the ToolUniverse MCP server and the relevant `tooluniverse-*` skill when applicable. ToolUniverse provides access to 2,000+ scientific database tools through natural-language routing and direct tool execution.

When changing `skills/` (the canonical Skill source), update `TOOLUNIVERSE_OVERLAY_DIFF.md` in the same change set. Keep the file aligned with the diff between `upstream/main` and `codex/skills-overlay` in `/Users/zhaoyuancun/Documents/ToolUniverse-fork`, especially for added overlay skills and modifications to upstream skills such as variant interpretation and ACMG classification.

ACMG overlay maintenance rules:

- ACMG final classification must never be emitted outside the overlay routing core, validator, semantic combiner, and final-answer guard path.
- `tooluniverse-variant-interpretation` is intake/handoff only. It may collect context and route candidates, but it must not assign final five-tier ACMG labels.
- Source labels from ClinVar, InterVar, GeneBe, HGMD, LOVD, VCEP/lab assertions, papers, or other automated classifiers are source leads only until primary evidence is routed.
- Evidence can only be counted if criterion-specific overlay or VCEP validator passes; the route outcome must be `overlay_applied` or `overlay_deferred_to_vcep`.
- Final classification requires validator_status PASS, semantic_combiner_status PASS, and final_classification_allowed true.
- Final labels additionally require an ACMG assessment session in `FINALIZED` state and a valid `acmg-final:v1:` finalization token issued by `src/tooluniverse/acmg_gate/finalizer.py`.
- Direct tool outputs must enter `source_lead_sandbox`: preserve factual features and quarantine automated labels/criteria; never convert GeneBe, InterVar, ClinVar, SpliceAI, CADD, AlphaMissense, REVEL, OpenCRAVAT, VEP, gnomAD, literature, or user context directly into counted evidence.
- When gates fail, output is draft-only. Allowed sections are variant normalization, source leads, counted=false route candidates, missing overlays/literature/coverage, block reasons, and next ToolUniverse actions. Draft/provisional final labels are still forbidden without a token.
- P/LP/VUS/LB/B abbreviations are final labels and must be guarded by the final-answer guard.
- User clinical context (de novo, segregation, compound heterozygous, HPO, unaffected carrier, alternate diagnosis) can only trigger non-counted route candidates. It must never directly become counted evidence.
- Do not reintroduce duplicate Skill drift. Run `python3 scripts/check_skill_duplicate_drift.py` after any Skill change. The canonical source is `skills/`; committed mirrors live under `plugin/skills/` and `plugins/tooluniverse/skills/`. `.agents/skills/` is a local-only generated mirror (gitignored).
- Keep shared ACMG runtime policy in `src/tooluniverse/acmg_gate/`. Skill scripts should be thin wrappers around canonical modules unless a file is purely schema, registry, fixture, or documentation.
- Run `python3 scripts/check_skill_duplicate_drift.py` after any Skill change. The canonical source is `skills/`; committed mirrors live under `plugin/skills/` and `plugins/tooluniverse/skills/`. `.agents/skills/` is a local-only generated mirror (gitignored).
**Global final-answer guard limitation:** ToolUniverse cannot enforce final-answer guard at the LLM runtime level — the LLM owns the final user-visible message. The `ACMG_guard_final_answer` tool must be called explicitly by the agent before emitting any text containing ACMG final labels. All ACMG-related skills must reference `ACMG_guard_final_answer` or `ACMG_overlay_gate_assess_variant` as the required path before final labels. Direct high-risk tools (GeneBe, InterVar, ClinVar, SpliceAI, etc.) are marked `final_classification_allowed=false` and `source_lead_only=true` in search results and tool outputs, but the agent may still bypass these markings — regression fixtures in `evals/entrypoint_bypass_fixtures/` test for such bypasses.

**ACMG Overlay MCP Tools mitigation (branch `acmg-overlay-mcp-tools`):** Each ACMG criterion is exposed as an independent deterministic MCP tool (e.g., `ACMG_overlay_pm2`, `ACMG_combine_criteria`). The LLM collects evidence from external data sources (gnomAD, ClinVar, SpliceAI), then passes structured data to overlay tools that apply ClinGen/SVI rules deterministically. This means even if the LLM bypasses the Gate, individual overlay tools still produce correct, reproducible judgments. The Router (`ACMG_route_overlays`) determines which overlays apply to a variant type, removing the need for LLM to memorize criterion applicability rules.

Recommended deployment hook:

- Pre-answer policy: if the user message matches `ACMG_FINAL_CLASSIFICATION` intent from `src/tooluniverse/acmg_gate/intent_detector.py`, the runtime must call ToolUniverse `ACMG_overlay_gate_assess_variant` before answering.
- Post-answer policy: if the draft final answer contains ACMG final labels in English, shorthand, or Chinese according to `src/tooluniverse/acmg_gate/final_label_detector.py`, the runtime must call `ACMG_guard_final_answer` and block or downgrade unless all gates and the finalization token verify.
- If no upper-level runtime hook exists, do not claim full global enforcement. ToolUniverse enforcement begins once the agent enters ToolUniverse tool discovery or execution.
