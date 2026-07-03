# ACMG Automation Roadmap

## Current Phase: Guarded Overlay Extension

The current branch narrows scope to a ClinGen/SVI guarded overlay extension on top of
upstream ToolUniverse. The system retrieves evidence with existing ToolUniverse tools,
quarantines source labels, applies deterministic overlay rules, validates route audit
rows, and blocks final wording without finalizer and guard approval.

## Next Phase: Evidence-to-Overlay Automation

Increase automation by improving structured evidence extraction:

- Map MyVariant/dbNSFP predictor fields into `ACMG_overlay_pp3_bp4` inputs.
- Map gnomAD coverage and allele frequency fields into `ACMG_overlay_pm2`.
- Map ClinVar same-amino-acid and same-residue comparators into `ACMG_overlay_ps1_pm5`.
- Map MaveDB and literature functional assay fields into `ACMG_overlay_functional_assay`.
- Map family/de novo/segregation fields into dedicated clinical-context overlays.

All mappings remain source lead or route input until deterministic overlay tools pass.

## Later Phase: Intelligent ACMG Rating Assistant

The long-term goal is a reliable and highly automated ACMG intelligent rating tool.
That tool should produce machine-checkable assessment bundles with:

- normalized variant identity,
- disease and transcript context,
- evidence coverage audit,
- overlay results,
- route audit,
- compatibility resolution,
- semantic-combiner result,
- finalization token when allowed.

The assistant may draft final wording only after the final-answer guard passes.

## Non-Goals Before Full Validation

- Do not claim complete clinical-grade ACMG classification.
- Do not trust GeneBe, InterVar, ClinVar, paper labels, or aggregator ACMG labels as counted evidence.
- Do not let LLM-generated criterion assignments bypass deterministic overlays.
- Do not add new predictor or literature tools as counted evidence without source provenance and overlay contracts.
