# ToolUniverse Overlay Difference List

Last updated: 2026-07-01

Baseline: `mims-harvard/ToolUniverse` upstream/main vs `YuancunZhao/ToolUniverse` codex/skills-overlay.

## Summary

- **Added skills:** 22 ACMG overlay + refinement skills
- **Modified upstream skills:** 4 (variant-interpretation, acmg-variant-classification, structural-variant-analysis, protein-sae-variant-interpretation)
- **Canonical runtime:** `src/tooluniverse/acmg_gate/` — single import surface (`__init__.py`) exporting protocol, guard, validator, and semantic-combiner symbols
- **Key modules:** `intent_detector.py`, `pre_router.py`, `session.py`, `source_lead_sandbox.py`, `transaction.py`, `draft_policy.py`, `final_label_detector.py`, `policy.py`, `finalizer.py`, `final_answer_guard.py`, `semantic_combiner.py`, `context_triggers.py`, `registry.py`, `validate_acmg_overlay_bundle.py`, `check_entrypoint_bypass_fixtures.py`
- **Skill-side bridges:** `skills/tooluniverse-acmg-overlay-routing-core/scripts/` → thin wrappers delegating to canonical runtime
- **Mirrors:** `plugin/skills/`, `plugins/tooluniverse/skills/` — drift-checked by `scripts/check_skill_duplicate_drift.py`. `.agents/skills/` is a local-only generated mirror (gitignored).
- **Tests:** 14 ACMG test files (12 unit + 2 integration), 33 validator fixtures, 22 bypass fixtures

## Architecture Rules

- ACMG final classification requires `validator_status=PASS`, `semantic_combiner_status=PASS`, `final_classification_allowed=true`, an ACMG assessment session in `FINALIZED` state, and a verified `acmg-final:v1:` finalization token
- Direct high-risk tools are marked `source_lead_only=true`, `final_classification_allowed=false`
- Source labels and automated criteria (ClinVar, InterVar, GeneBe, etc.) are sandboxed leads only — not counted evidence
- SpliceAI/CADD/AlphaMissense/REVEL/VEP/OpenCRAVAT/MyVariant/gnomAD/literature/user context preserve reviewable facts but quarantine final-like conclusions until overlays validate them
- User clinical context triggers non-counted route candidates only
- `tooluniverse-variant-interpretation` is intake/handoff only

See `docs/acmg_overlay_architecture.md` for full architecture documentation.
See `AGENTS.md` for maintenance rules.

---

*Historical changelog (2026-06-09 through 2026-06-27) has been archived in git history (commits `0cb6f55c` through `c32c324b`).*
