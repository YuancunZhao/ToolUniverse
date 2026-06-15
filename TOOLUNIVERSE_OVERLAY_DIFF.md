# ToolUniverse Overlay Difference List

Last updated: 2026-06-15

Baseline comparison:

- Upstream: `mims-harvard/ToolUniverse`, `upstream/main` at `574a7027`
- Overlay branch: `YuancunZhao/ToolUniverse`, `codex/skills-overlay` at `073b2199`
- Diff command: `git diff --name-status upstream/main...codex/skills-overlay -- skills`

Summary:

- Added skills: 18
- Modified upstream skills: 4
- Deleted upstream skills: 0
- Changed files under `skills/`: 52
- Net intended overlay diff: 6498 insertions, 57 deletions

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
| `tooluniverse-acmg-pm4-bp3-protein-length-refinement` | Refine PM4/BP3 for in-frame insertions/deletions, single amino-acid indels, repeat regions, stop-loss variants, and last-exon altered-product contexts using ACGS 2024 practice guidance. | `SKILL.md`, `QUICK_START.md`, `references/acgs_2024_pm4_bp3_summary.md` |
| `tooluniverse-acmg-pp1-segregation-refinement` | Refine PP1/BS4 segregation evidence using informative meioses, LOD-like reasoning, phenocopy/reduced-penetrance checks, and qualified-variant boundaries. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` | Replace uncalibrated predictor majority voting with calibrated missense prediction evidence strengths for PP3/BP4. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` | Refine PP5/BP6 reputable-source assertions using ClinGen SVI guidance recommending discontinuation of PP5/BP6; treats secondary classifications as leads to primary evidence rather than counted criteria. | `SKILL.md`, `QUICK_START.md`, `references/biesecker_2018_pp5_bp6_summary.md` |
| `tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement` | Refine protein-level PS1/PM5 for same amino-acid substitution, same-residue missense comparison variants, same-codon edge cases, mechanism matching, splicing confounding, and circularity. | `SKILL.md`, `QUICK_START.md`, `references/acmg_2015_ps1_pm5_summary.md` |
| `tooluniverse-acmg-ps1-splicing-similarity-refinement` | Apply PS1 logic for same predicted RNA-splicing events relative to known P/LP comparison variants, with RNA-evidence precedence and duplicate-evidence guards. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-ps3-bs3-functional-assay-refinement` | Refine PS3/BS3 strength for functional assays using assay validity, disease-mechanism fit, controls, OddsPath/calibration, and duplicate-counting checks. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-ps4-case-enrichment-refinement` | Refine PS4 for case-control evidence, odds ratio/confidence interval, unrelated affected case counts, ancestry matching, gnomAD control caveats, and rare-disease ACGS-style case counting. | `SKILL.md`, `QUICK_START.md`, `references/acgs_2024_ps4_summary.md` |
| `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` | Refine baseline PVS1 strength using Abou Tayoun et al. 2018 / ClinGen SVI PVS1 LoF decision tree, including LoF mechanism gate, NMD, start-loss, exon deletion/duplication, whole-gene deletion, rescue transcript, and in-frame branch handling. | `SKILL.md`, `QUICK_START.md`, `references/abou_tayoun_2018_pvs1_summary.md` |
| `tooluniverse-acmg-pvs1-splicing-refinement` | Refine PVS1/BP7 for RNA-splicing evidence, aberrant transcripts, exon skipping, rescue transcripts, and Walker/ClinGen SVI splicing-style logic. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-benign-context-refinement` | Refine BA1/BS1/BS2/BP2/BP5 while keeping PM2 on the ClinGen SVI PM2 overlay; requests disease threshold, phenotype, unaffected-status, phase, and alternate-diagnosis context when missing. | `SKILL.md`, `QUICK_START.md`, `references/acgs_2024_benign_context_summary.md` |

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
- Routes PM2, PP3/BP4, PP5/BP6, protein-level PS1/PM5, PS1-splicing, PM1, baseline PVS1 LoF decision-tree, PVS1-splicing, PS3/BS3, PP1, PM3, phenotype-dependent criteria, PS2/PM6 de novo evidence, PM4/BP3, and visual-literature evidence to the new overlay skills.
- Routes PS4 case enrichment, PM4/BP3 protein-length evidence, and BA1/BS1/BS2/BP2/BP5 benign-context evidence to dedicated overlays.
- Specifies that PS2/PM6 uses ClinGen SVI De Novo Criteria v1.1 point scoring and routes literature-derived de novo evidence through literature deep research and figure evidence extraction before scoring.
- Adds explicit behavior for missing phenotype or de novo information: mark affected criteria as not assessed and ask the user for targeted missing fields.
- Adds GeneReviews/MedGen as mechanism and inheritance background support, while stating that GeneReviews is not a VCEP specification or primary variant-level evidence by itself.
- Replaces uncalibrated predictor-majority language with calibrated missense-prediction logic.
- Adds safeguards against transferring evidence across recessive LoF, haploinsufficiency, dominant-negative, gain-of-function, and splicing mechanisms without a same-mechanism rationale.
- Preserves locked rule priorities: PM2 remains ClinGen SVI `PM2_Supporting` by default, and PP3/BP4 remains Pejaver 2022 calibrated missense prediction evidence rather than ACGS generic predictor voting.

### `tooluniverse-variant-interpretation`

Modified files:

- `skills/tooluniverse-variant-interpretation/SKILL.md`
- `skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md`
- `skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md`

Main behavior changes:

- Adds GeneReviews/MedGen to the clinical database phase for disease spectrum, inheritance, and mechanism context.
- Adds explicit guidance to query GeneReviews/NCBI Bookshelf when mechanism affects ACMG routing.
- Tightens truncating-variant handling: PVS1 requires confirmed LoF/haploinsufficiency for the exact gene-disease context.
- Routes ambiguous dominant/recessive, structural/complex, mixed-mechanism, or unclear HI/LoF contexts through `tooluniverse-acmg-dominant-negative-mechanism-refinement` before assigning PVS1.
- Routes baseline PVS1 strength to `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` before Walker 2023 RNA/splicing refinement.
- Clarifies that gene expression and gene-disease association scores do not substitute for patient-level PP4 or other phenotype-dependent evidence, and routes missing phenotype/de novo context to the new overlays.
- Routes PS4, PM4/BP3, and benign-context criteria to the new overlays.
- Routes PP5/BP6 reputable-source assertions to the new overlay and documents that they are not counted by default.
- Removes old uncalibrated predictor-majority PP3/BP4 language and points missense prediction evidence to the Pejaver 2022 overlay.
- Updates the ACMG quick reference so PM2 is no longer documented as Moderate and points final evidence strength to the overlay workflow.

### `tooluniverse-rare-disease-diagnosis`

Modified file:

- `skills/tooluniverse-rare-disease-diagnosis/SKILL.md`

Main behavior changes:

- Routes Phase 4 ACMG variant interpretation to `tooluniverse-acmg-variant-classification` and overlay skills.
- Clarifies that PM2 defaults to `PM2_Supporting` under the ClinGen SVI PM2 overlay.
- Replaces old "2+ concordant predictors strengthen PP3" language with the Pejaver 2022 PP3/BP4 overlay.

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
A skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/SKILL.md
A skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/references/acgs_2024_pm4_bp3_summary.md
A skills/tooluniverse-acmg-pp1-segregation-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pp1-segregation-refinement/SKILL.md
A skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/SKILL.md
A skills/tooluniverse-acmg-pp5-bp6-reputable-source-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pp5-bp6-reputable-source-refinement/SKILL.md
A skills/tooluniverse-acmg-pp5-bp6-reputable-source-refinement/references/biesecker_2018_pp5_bp6_summary.md
A skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/SKILL.md
A skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/references/acmg_2015_ps1_pm5_summary.md
A skills/tooluniverse-acmg-ps1-splicing-similarity-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ps1-splicing-similarity-refinement/SKILL.md
A skills/tooluniverse-acmg-ps3-bs3-functional-assay-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ps3-bs3-functional-assay-refinement/SKILL.md
A skills/tooluniverse-acmg-ps4-case-enrichment-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ps4-case-enrichment-refinement/SKILL.md
A skills/tooluniverse-acmg-ps4-case-enrichment-refinement/references/acgs_2024_ps4_summary.md
A skills/tooluniverse-acmg-pvs1-lof-decision-tree-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pvs1-lof-decision-tree-refinement/SKILL.md
A skills/tooluniverse-acmg-pvs1-lof-decision-tree-refinement/references/abou_tayoun_2018_pvs1_summary.md
A skills/tooluniverse-acmg-pvs1-splicing-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pvs1-splicing-refinement/SKILL.md
A skills/tooluniverse-acmg-benign-context-refinement/QUICK_START.md
A skills/tooluniverse-acmg-benign-context-refinement/SKILL.md
A skills/tooluniverse-acmg-benign-context-refinement/references/acgs_2024_benign_context_summary.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-literature-deep-research/SKILL.md
A skills/tooluniverse-literature-figure-evidence-extraction/QUICK_START.md
A skills/tooluniverse-literature-figure-evidence-extraction/SKILL.md
A skills/tooluniverse-literature-figure-evidence-extraction/references/figure_evidence_schema.md
M skills/tooluniverse-rare-disease-diagnosis/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/EXAMPLES.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
```

## Local ToolUniverse Update: 2026-06-15

Changed files:

```text
M skills/tooluniverse-acmg-pvs1-splicing-refinement/SKILL.md
M skills/tooluniverse-acmg-pvs1-splicing-refinement/QUICK_START.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
```

Behavior added:

- Removes the experimental DECIPHER sequence-variant scraper/tool and keeps the overlay skill-only.
- PVS1 skills route protein-truncating variants through transcript-structure review before assigning PVS1 Very Strong.
- This older local NMD-escape wording was superseded by the PMID 30192042 decision-tree update below: the Abou Tayoun et al. 2018 baseline tree uses the 3' most exon and 3' most 50 nucleotides of the penultimate exon rule; additional transcript-specific escape rules require a separate VCEP or current-source basis.
- LoFTEE is documented as auxiliary annotation and not a substitute for direct transcript-structure review.

## PMID 30192042 PVS1 Decision Tree Update: 2026-06-15

Changed files:

```text
A skills/tooluniverse-acmg-pvs1-lof-decision-tree-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pvs1-lof-decision-tree-refinement/SKILL.md
A skills/tooluniverse-acmg-pvs1-lof-decision-tree-refinement/references/abou_tayoun_2018_pvs1_summary.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-acmg-pvs1-splicing-refinement/QUICK_START.md
M skills/tooluniverse-acmg-pvs1-splicing-refinement/SKILL.md
M skills/tooluniverse-acmg-dominant-negative-mechanism-refinement/SKILL.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
```

Behavior added:

- Adds a dedicated Abou Tayoun et al. 2018 / ClinGen SVI PVS1 LoF decision-tree overlay for baseline PVS1 assignment.
- Aligns the baseline overlay with the user-provided full-text PDF (`nihms-986839.pdf`) and editable decision-tree PPTX (`clingen_svi_pvs1_decisiontree_editable.pptx`), including Table 1 gene-level LoF mechanism gating and Figure 1 branch wording.
- Covers LoF/HI applicability, nonsense/frameshift PTC with NMD, NMD escape, canonical splice predicted transcript consequence, start-loss, exon deletion/duplication, whole-gene deletion, rescue transcript, and in-frame LoF branches.
- Uses the Abou Tayoun et al. 2018 baseline NMD rule: NMD is generally not predicted when the PTC is in the 3' most exon or within the 3' most 50 nucleotides of the penultimate exon.
- Preserves exact Figure 1 branches for initiation codon variants, tandem/presumed-tandem duplications, >10% versus <10% protein removal, canonical splice +/-20 nucleotide caveat, and PM4/PVS1 non-overlap.
- Defines standard outputs: `PVS1`, `PVS1_Strong`, `PVS1_Moderate`, `PVS1_Supporting`, `PVS1_N/A`, and `PVS1_NotAssessed`.
- Separates responsibilities: baseline PVS1 strength is assigned by the 2018 LoF decision-tree overlay; Walker 2023 RNA/splicing evidence is handled afterward by `tooluniverse-acmg-pvs1-splicing-refinement`.
- Routes CNV/SV event definition to `tooluniverse-structural-variant-analysis` before PVS1 strength assignment when exon-level or whole-gene copy-number events are involved.

## PP5/BP6 Reputable Source Update: 2026-06-15

Changed files:

```text
A skills/tooluniverse-acmg-pp5-bp6-reputable-source-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pp5-bp6-reputable-source-refinement/SKILL.md
A skills/tooluniverse-acmg-pp5-bp6-reputable-source-refinement/references/biesecker_2018_pp5_bp6_summary.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/EXAMPLES.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
```

Behavior added:

- Adds a dedicated PP5/BP6 reputable-source overlay based on Biesecker and Harrison 2018 / ClinGen SVI, PMID:29543229.
- Makes `PP5` and `BP6` not counted by default; reputable-source assertions are treated as leads to retrieve primary evidence.
- Routes primary evidence to the appropriate evidence-specific overlays instead of counting source labels.
- Removes old examples that counted ClinVar or expert-source labels as PP5/BP6 supporting evidence.
- Adds double-counting guards so the same functional, population, case, segregation, de novo, PM3, PVS1, or computational evidence is not counted once directly and again through PP5/BP6.

## ACGS 2024 Overlay Update: 2026-06-15

Changed files:

```text
A skills/tooluniverse-acmg-ps4-case-enrichment-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ps4-case-enrichment-refinement/SKILL.md
A skills/tooluniverse-acmg-ps4-case-enrichment-refinement/references/acgs_2024_ps4_summary.md
A skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/QUICK_START.md
A skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/SKILL.md
A skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/references/acgs_2024_pm4_bp3_summary.md
A skills/tooluniverse-acmg-benign-context-refinement/QUICK_START.md
A skills/tooluniverse-acmg-benign-context-refinement/SKILL.md
A skills/tooluniverse-acmg-benign-context-refinement/references/acgs_2024_benign_context_summary.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/QUICK_START.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/SKILL.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/references/phenotype_dependent_criteria_summary.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/QUICK_START.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/SKILL.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/references/acmg_2015_ps1_pm5_summary.md
M skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/QUICK_START.md
M skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/SKILL.md
M skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/references/pmid38645134_regional_missense_constraint_summary.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
M skills/tooluniverse-rare-disease-diagnosis/SKILL.md
```

Behavior added:

- Adds PS4 case-enrichment overlay for formal case-control evidence and ACGS-style rare-disease affected-case counting; recessive biallelic affected-proband evidence routes to PM3 instead of PS4.
- Adds PM4/BP3 overlay for protein length changes, single amino-acid in-frame indels, repeat-region BP3, stop-loss, and last-exon altered-product contexts; PM4 is not co-used with PVS1 for the same length-changing effect.
- Adds benign-context overlay for BA1/BS1/BS2/BP2/BP5, while keeping PM2 under the ClinGen SVI PM2 overlay.
- Enhances phenotype-dependent PP4 with ACGS Appendix B-style specificity stratification and double-counting safeguards with PS2/PM6 and PS4.
- Enhances PS1/PM5 with ACGS practice guidance for `PS1_Moderate`, `PM5_Supporting`, initiation codon and non-coding RNA caveats, predicted-impact comparison, in-frame indel overlap, and PM1/PM5 double-counting.
- Enhances PM1/PP2/BP1 with ACGS regional resources such as DECIPHER regional constraint, CCR, MetaDome, paralogous residue evidence, critical-residue `PM1_Strong` examples, and BP1 conflict handling.
- Preserves locked priorities: PM2 remains ClinGen SVI `PM2_Supporting`, and PP3/BP4 remains Pejaver 2022 calibrated missense prediction evidence.

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
