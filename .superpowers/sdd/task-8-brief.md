# Task 8: Rewrite Project Positioning Docs

Files to modify: `README.md`, `docs/acmg_overlay_architecture.md`, `TOOLUNIVERSE_OVERLAY_DIFF.md`

## Step 1: Update README positioning

In `README.md`, find the existing fork-positioning banner (currently around the top, starting with "⚠️ **This is the ACMG Enhanced fork**") and replace it with:

```markdown
> This fork is a ClinGen/SVI guarded overlay extension for upstream ToolUniverse.
> Upstream ToolUniverse remains the evidence retrieval and tool-execution platform.
> This extension adds deterministic ACMG/ClinGen overlay tools, source-lead sandboxing,
> route-audit validation, and final-answer guards so agents cannot directly convert
> GeneBe, InterVar, ClinVar, SpliceAI, MyVariant, VEP, gnomAD, literature, or user
> context into counted ACMG evidence.
```

Also add this paragraph after the banner:

```markdown
This fork is not a standalone clinical classifier. Its near-term purpose is to make
ACMG-related agent workflows harder to bypass and easier to audit. The long-term
direction is a higher-automation ACMG intelligent rating tool, built incrementally
from validated overlay routes and evidence provenance.
```

## Step 2: Update architecture doc

In `docs/acmg_overlay_architecture.md`, add a new top-level section after the first heading:

```markdown
## Project Scope

The project is temporarily scoped as an upstream ToolUniverse-compatible ClinGen/SVI
guarded overlay extension. The extension does three things:

1. Converts direct ToolUniverse variant evidence outputs into source leads or route inputs.
2. Applies ClinGen/SVI criterion-specific recommendations through deterministic overlay tools.
3. Blocks final ACMG wording unless bundle validation, semantic combination, finalization token,
   and final-answer guard all pass.

The extension intentionally does not replace upstream ToolUniverse evidence retrieval,
does not trust automated source labels as counted evidence, and does not claim complete
clinical-grade ACMG automation until every criterion path has validated route contracts.
```

## Step 3: Update overlay diff

In `TOOLUNIVERSE_OVERLAY_DIFF.md`, add a new top-level section at the beginning:

```markdown
## Current Scope: Guarded Overlay Extension

This branch narrows the ACMG work to a ToolUniverse-compatible guarded overlay layer.
Canonical ToolUniverse tools continue to retrieve evidence. ACMG additions provide
deterministic overlay judgment, source-lead quarantine, route audit validation, and
final-answer gating.
```

## Step 4: Verify no stale claims

Run: `grep -Rn "standalone clinical classifier\|complete clinical\|ACMG Enhanced fork\|5-tier classification" README.md docs TOOLUNIVERSE_OVERLAY_DIFF.md`

Expected: no wording that claims this fork is a complete clinical classifier.

## Step 5: Commit

`git add README.md docs/acmg_overlay_architecture.md TOOLUNIVERSE_OVERLAY_DIFF.md`
`git commit -m "docs: reframe fork as ClinGen SVI guarded overlay extension"`

## Important

- Do NOT change the one-line install prompt (`Read https://raw.githubusercontent.com/...`) — keep that working
- Preserve all existing ACMG architecture documentation content, only add the new scope section
- Do NOT change any technical content in README or architecture docs
