# ToolUniverse Overlay Difference List

Last updated: 2026-06-30

Baseline: `mims-harvard/ToolUniverse` upstream/main vs `YuancunZhao/ToolUniverse` codex/skills-overlay.

## Summary

- **Added skills:** 22 ACMG overlay + refinement skills
- **Modified upstream skills:** 4 (variant-interpretation, acmg-variant-classification, structural-variant-analysis, protein-sae-variant-interpretation)
- **Canonical runtime:** `src/tooluniverse/acmg_gate/` — single import surface (`__init__.py`) exporting 37 symbols
- **Key modules:** `intent_detector.py`, `final_label_detector.py`, `policy.py`, `finalizer.py`, `semantic_combiner.py`, `context_triggers.py`, `registry.py`, `validate_acmg_overlay_bundle.py`, `check_entrypoint_bypass_fixtures.py`
- **Skill-side bridges:** `skills/tooluniverse-acmg-overlay-routing-core/scripts/` → thin wrappers delegating to canonical runtime
- **Mirrors:** `plugin/skills/`, `plugins/tooluniverse/skills/` — drift-checked by `scripts/check_skill_duplicate_drift.py`. `.agents/skills/` is a local-only generated mirror (gitignored).
- **Tests:** 9 test files (8 unit + 1 integration), 33 validator fixtures, 21 bypass fixtures

## Architecture Rules

- ACMG final classification requires `validator_status=PASS`, `semantic_combiner_status=PASS`, `final_classification_allowed=true`
- Direct high-risk tools are marked `source_lead_only=true`, `final_classification_allowed=false`
- Source labels (ClinVar, InterVar, GeneBe, etc.) are leads only — not counted evidence
- User clinical context triggers non-counted route candidates only
- `tooluniverse-variant-interpretation` is intake/handoff only

See `docs/acmg_overlay_architecture.md` for full architecture documentation.
See `AGENTS.md` for maintenance rules.

---

*Historical changelog (2026-06-09 through 2026-06-27) has been archived in git history (commits `0cb6f55c` through `c32c324b`).*
