# Task 8 Report: Rewrite Project Positioning Docs

## Status: DONE

## Commits Created

- `f733554e` — `docs: reframe fork as ClinGen SVI guarded overlay extension`

## Summary

All three files now correctly position the fork as a ClinGen/SVI guarded overlay extension:

1. **README.md** — Fork banner reframed from "ACMG Enhanced fork" to "ClinGen/SVI guarded overlay extension" with the "not a standalone clinical classifier" disclaimer. Removed a leftover fragment (`only has the 7-layer gate enforcement system.`) that remained from the old banner. One-line install prompt preserved.

2. **docs/acmg_overlay_architecture.md** — `## Project Scope` section added after the first heading, describing the three responsibilities of the overlay extension and what it intentionally does not do.

3. **TOOLUNIVERSE_OVERLAY_DIFF.md** — `## Current Scope: Guarded Overlay Extension` section added at the top, narrowing the ACMG work to a guarded overlay layer.

## Verification

```
grep -Rn "standalone clinical classifier\|complete clinical\|ACMG Enhanced fork\|5-tier classification" README.md docs TOOLUNIVERSE_OVERLAY_DIFF.md
```

- `README.md:23`: "This fork is **not** a standalone clinical classifier" — negation, not a positive claim. ✓
- `docs/acmg_automation_roadmap.md:40`: "Do **not** claim complete clinical-grade" — prohibition, not a claim. ✓
- No wording claims this fork IS a complete clinical classifier. ✓

## Concerns

None. The two other docs (`docs/acmg_overlay_architecture.md` and `TOOLUNIVERSE_OVERLAY_DIFF.md`) already had the required sections in place before this task run; only the README fragment cleanup was needed.
