# ToolUniverse Overlay Difference List

Last updated: 2026-06-15

Baseline comparison:

- Upstream: `mims-harvard/ToolUniverse`, `upstream/main` at `574a7027`
- Overlay branch: `YuancunZhao/ToolUniverse`, `codex/skills-overlay` at `073b2199`
- Diff command: `git diff --name-status upstream/main...codex/skills-overlay -- skills`

Summary:

- Added skills: 13
- Modified upstream skills: 3
- Deleted upstream skills: 0
- Changed files under `skills/`: 34
- Net diff: 4615 insertions, 23 deletions

## Added Skills

### ACMG Evidence Refinement Overlays

These are additive overlays intended to refine ACMG/AMP evidence assignment without replacing the base ToolUniverse variant skills.

| Skill | Purpose | Files |
| --- | --- | --- |
| `tooluniverse-acmg-dominant-negative-mechanism-refinement` | Resolve whether a gene-disease context supports LoF/haploinsufficiency, dominant-negative, antimorphic, gain-of-function, recessive LoF, or mixed mechanism before applying mechanism-sensitive ACMG criteria. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-de-novo-evidence-refinement` | Refine PS2/PM6 de novo evidence using ClinGen SVI De Novo Criteria v1.1 point scoring, parental relationship confirmation, phenotype specificity, recurrent observations, inheritance adjustments, literature extraction, and missing-information prompts. | `SKILL.md`, `QUICK_START.md`, `references/de_novo_ps2_pm6_summary.md` |
| `tooluniverse-acmg-phenotype-dependent-evidence-refinement` | Route phenotype-dependent evidence such as PP4, PS4, PP1/BS4, PM3, BP5, BS2, and PS2/PM6 phenotype consistency, and request missing phenotype fields when not supplied. | `SKILL.md`, `QUICK_START.md`, `references/phenotype_dependent_criteria_summary.md` |
| `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` | Refine PM1 for regional missense intolerance, hotspots, constrained subdomains, and low benign variation while avoiding PP3/PM1 double counting. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pm2-absence-rarity-refinement` | Apply SVI-style PM2 absence/rarity logic, coverage checks, BA1/BS1/BS2 precedence, and PM2 supporting-strength boundaries. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pm3-in-trans-refinement` | Score PM3 for recessive disorders using in-trans, phase-unknown, one-parent-supported, VUS-other-allele, and homozygous evidence while checking rarity and circularity. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pp1-segregation-refinement` | Refine PP1/BS4 segregation evidence using informative meioses, LOD-like reasoning, phenocopy/reduced-penetrance checks, and qualified-variant boundaries. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` | Replace uncalibrated predictor majority voting with calibrated missense prediction evidence strengths for PP3/BP4. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement` | Refine protein-level PS1/PM5 for same amino-acid substitution, same-residue missense comparison variants, same-codon edge cases, mechanism matching, splicing confounding, and circularity. | `SKILL.md`, `QUICK_START.md`, `references/acmg_2015_ps1_pm5_summary.md` |
| `tooluniverse-acmg-ps1-splicing-similarity-refinement` | Apply PS1 logic for same predicted RNA-splicing events relative to known P/LP comparison variants, with RNA-evidence precedence and duplicate-evidence guards. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-ps3-bs3-functional-assay-refinement` | Refine PS3/BS3 strength for functional assays using assay validity, disease-mechanism fit, controls, OddsPath/calibration, and duplicate-counting checks. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pvs1-splicing-refinement` | Refine PVS1/BP7 for RNA-splicing evidence, aberrant transcripts, exon skipping, rescue transcripts, and Walker/ClinGen SVI splicing-style logic. | `SKILL.md`, `QUICK_START.md` |

### Literature Evidence Overlay

| Skill | Purpose | Files |
| --- | --- | --- |
| `tooluniverse-literature-figure-evidence-extraction` | Extract structured evidence from paper figures, supplements, pedigrees, gels, blots, Sanger traces, RT-PCR/minigene panels, and functional assay plots before downstream ACMG/domain interpretation. | `SKILL.md`, `QUICK_START.md`, `references/figure_evidence_schema.md` |

## Modified Upstream Skills

### `tooluniverse-acmg-variant-classification`

Modified file:

- `skills/tooluniverse-acmg-variant-classification/SKILL.md`

Main behavior changes:

- Adds a Phase 0b gene-disease mechanism check before mechanism-sensitive ACMG criteria.
- Adds explicit gates for PVS1 when LoF/haploinsufficiency is uncertain or disease mechanism may be dominant-negative, antimorphic, gain-of-function, or mixed.
- Routes PM2, PP3/BP4, protein-level PS1/PM5, PS1-splicing, PM1, PVS1-splicing, PS3/BS3, PP1, PM3, phenotype-dependent criteria, PS2/PM6 de novo evidence, PM4/BP3, and visual-literature evidence to the new overlay skills.
- Specifies that PS2/PM6 uses ClinGen SVI De Novo Criteria v1.1 point scoring and routes literature-derived de novo evidence through literature deep research and figure evidence extraction before scoring.
- Adds explicit behavior for missing phenotype or de novo information: mark affected criteria as not assessed and ask the user for targeted missing fields.
- Adds GeneReviews/MedGen as mechanism and inheritance background support, while stating that GeneReviews is not a VCEP specification or primary variant-level evidence by itself.
- Replaces uncalibrated predictor-majority language with calibrated missense-prediction logic.
- Adds safeguards against transferring evidence across recessive LoF, haploinsufficiency, dominant-negative, gain-of-function, and splicing mechanisms without a same-mechanism rationale.

### `tooluniverse-variant-interpretation`

Modified files:

- `skills/tooluniverse-variant-interpretation/SKILL.md`
- `skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md`

Main behavior changes:

- Adds GeneReviews/MedGen to the clinical database phase for disease spectrum, inheritance, and mechanism context.
- Adds explicit guidance to query GeneReviews/NCBI Bookshelf when mechanism affects ACMG routing.
- Tightens truncating-variant handling: PVS1 requires confirmed LoF/haploinsufficiency for the exact gene-disease context.
- Routes ambiguous dominant/recessive, structural/complex, mixed-mechanism, or unclear HI/LoF contexts through `tooluniverse-acmg-dominant-negative-mechanism-refinement` before assigning PVS1.
- Clarifies that gene expression and gene-disease association scores do not substitute for patient-level PP4 or other phenotype-dependent evidence, and routes missing phenotype/de novo context to the new overlays.

### `tooluniverse-literature-deep-research`

Modified file:

- `skills/tooluniverse-literature-deep-research/SKILL.md`

Main behavior changes:

- Adds a figure-level evidence section.
- Routes claims depending on visual literature evidence to `tooluniverse-literature-figure-evidence-extraction`.
- Defines visual evidence scope: paper figures, supplements, pedigrees, gels, blots, Sanger traces, RT-PCR/minigene panels, functional assay plots, and related images.

## Changed File Inventory

```text
A skills/tooluniverse-acmg-dominant-negative-mechanism-refinement/QUICK_START.md
A skills/tooluniverse-acmg-dominant-negative-mechanism-refinement/SKILL.md
A skills/tooluniverse-acmg-de-novo-evidence-refinement/QUICK_START.md
A skills/tooluniverse-acmg-de-novo-evidence-refinement/SKILL.md
A skills/tooluniverse-acmg-de-novo-evidence-refinement/references/de_novo_ps2_pm6_summary.md
A skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/QUICK_START.md
A skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/SKILL.md
A skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/references/phenotype_dependent_criteria_summary.md
A skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/SKILL.md
A skills/tooluniverse-acmg-pm2-absence-rarity-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pm2-absence-rarity-refinement/SKILL.md
A skills/tooluniverse-acmg-pm3-in-trans-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pm3-in-trans-refinement/SKILL.md
A skills/tooluniverse-acmg-pp1-segregation-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pp1-segregation-refinement/SKILL.md
A skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/SKILL.md
A skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/SKILL.md
A skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/references/acmg_2015_ps1_pm5_summary.md
A skills/tooluniverse-acmg-ps1-splicing-similarity-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ps1-splicing-similarity-refinement/SKILL.md
A skills/tooluniverse-acmg-ps3-bs3-functional-assay-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ps3-bs3-functional-assay-refinement/SKILL.md
A skills/tooluniverse-acmg-pvs1-splicing-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pvs1-splicing-refinement/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-literature-deep-research/SKILL.md
A skills/tooluniverse-literature-figure-evidence-extraction/QUICK_START.md
A skills/tooluniverse-literature-figure-evidence-extraction/SKILL.md
A skills/tooluniverse-literature-figure-evidence-extraction/references/figure_evidence_schema.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/SKILL.md
```

## Local ToolUniverse Update: 2026-06-15

Changed files:

```text
A src/tooluniverse/decipher_tool.py
A src/tooluniverse/data/decipher_tools.json
A tests/unit/test_decipher_tool.py
M src/tooluniverse/default_config.py
M skills/tooluniverse-acmg-pvs1-splicing-refinement/SKILL.md
M skills/tooluniverse-acmg-pvs1-splicing-refinement/QUICK_START.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
```

Behavior added:

- Adds DECIPHER sequence-variant NMD escape tool `DECIPHER_get_sequence_variant_nmd`, backed by the public `/sequence-variant/{chr-pos-ref-alt}` page.
- The tool returns page URL, GRCh38 variant coordinates, basic gene/transcript context, first-100bp predicted NMD escape region, overlap status, and provenance.
- PVS1 skills now route protein-truncating variants through DECIPHER/equivalent NMD escape checks before assigning PVS1 Very Strong.
- LoFTEE `50_BP_RULE:PASS` is explicitly documented as auxiliary and not sufficient to exclude DECIPHER 5' first-100bp NMD escape.

## Update Procedure

Whenever `.agents/skills` changes in RulesEnhancement:

1. Test the changed skills in Codex.
2. Sync tested changes into the fork:

   ```bash
   rsync -a /Users/zhaoyuancun/Documents/RulesEnhancement/.agents/skills/ ~/Documents/ToolUniverse-fork/skills/
   ```

3. Refresh upstream comparison in the fork:

   ```bash
   cd ~/Documents/ToolUniverse-fork
   git fetch upstream
   git checkout codex/skills-overlay
   git merge upstream/main
   git diff --name-status upstream/main...codex/skills-overlay -- skills
   git diff --stat upstream/main...codex/skills-overlay -- skills
   ```

4. Update this file with the new added/modified/deleted skill list and behavior summary.
5. Commit both skill changes and this difference list.

Avoid `rsync --delete` during routine overlay publishing unless the goal is to make the fork `skills/` directory exactly match RulesEnhancement's `.agents/skills/` directory.
