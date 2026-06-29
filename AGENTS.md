# ToolUniverse

For any scientific research question involving drugs, genes, proteins, diseases, literature, clinical trials, variants, or other biomedical/scientific databases, use the ToolUniverse MCP server and the relevant `tooluniverse-*` skill when applicable. ToolUniverse provides access to 2,000+ scientific database tools through natural-language routing and direct tool execution.

When changing `skills/` (the canonical Skill source), update `TOOLUNIVERSE_OVERLAY_DIFF.md` in the same change set. Keep the file aligned with the diff between `upstream/main` and `codex/skills-overlay` in `/Users/zhaoyuancun/Documents/ToolUniverse-fork`, especially for added overlay skills and modifications to upstream skills such as variant interpretation and ACMG classification.

ACMG overlay maintenance rules:

- ACMG final classification must never be emitted outside the overlay routing core, validator, semantic combiner, and final-answer guard path.
- `tooluniverse-variant-interpretation` is intake/handoff only. It may collect context and route candidates, but it must not assign final five-tier ACMG labels.
- Source labels from ClinVar, InterVar, GeneBe, HGMD, LOVD, VCEP/lab assertions, papers, or other automated classifiers are source leads only until primary evidence is routed.
- Evidence can only be counted if criterion-specific overlay or VCEP validator passes; the route outcome must be `overlay_applied` or `overlay_deferred_to_vcep`.
- Final classification requires validator_status PASS, semantic_combiner_status PASS, and final_classification_allowed true.
- P/LP/VUS/LB/B abbreviations are final labels and must be guarded by the final-answer guard.
- User clinical context (de novo, segregation, compound heterozygous, HPO, unaffected carrier, alternate diagnosis) can only trigger non-counted route candidates. It must never directly become counted evidence.
- Do not reintroduce duplicate Skill drift. Run `python3 scripts/check_skill_duplicate_drift.py` after any Skill change. The canonical source is `skills/`; mirrors live under `.agents/skills/`, `plugin/skills/`, and `plugins/tooluniverse/skills/`.
