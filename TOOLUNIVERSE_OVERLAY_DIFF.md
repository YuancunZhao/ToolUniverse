# ToolUniverse Overlay Difference List

Last updated: 2026-06-18

Baseline comparison:

- Upstream: `mims-harvard/ToolUniverse`, `upstream/main` at `574a7027`
- Overlay branch: `YuancunZhao/ToolUniverse`, `codex/skills-overlay` at `073b2199`
- Diff command: `git diff --name-status upstream/main...codex/skills-overlay -- skills`

Summary:

- Added skills: 22
- Modified upstream skills: 4
- Deleted upstream skills: 0
- Changed files under `skills/`: 75
- Net intended overlay diff: approximately 10400 insertions, 190 deletions

## Added Skills

### ACMG Evidence Refinement Overlays

These are additive overlays intended to refine ACMG/AMP evidence assignment without replacing the base ToolUniverse variant skills.

| Skill | Purpose | Files |
| --- | --- | --- |
| `tooluniverse-acmg-ba1-exception-list-refinement` | Refine BA1 stand-alone benign evidence using Ghosh et al. 2018 ClinGen SVI BA1 definition, 2,000 observed-allele requirement, general continental population dataset checks, founder-population caveats, gene/variant-specific BA1 modifications, and the BA1 exception list. | `SKILL.md`, `QUICK_START.md`, `references/ghosh_2018_ba1_exception_guidance.md` |
| `tooluniverse-acmg-bayesian-classification-framework` | Convert already-routed ACMG/AMP evidence strengths into Tavtigian et al. 2018 Bayesian points, OddsPath, posterior probability, and standardized phase output after the final overlay route audit. | `SKILL.md`, `QUICK_START.md`, `references/tavtigian_2018_bayesian_framework.md` |
| `tooluniverse-acmg-dominant-negative-mechanism-refinement` | Resolve whether a gene-disease context supports LoF/haploinsufficiency, dominant-negative, antimorphic, gain-of-function, recessive LoF, or mixed mechanism before applying mechanism-sensitive ACMG criteria. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-de-novo-evidence-refinement` | Refine PS2/PM6 de novo evidence using ClinGen SVI De Novo Criteria v1.1 point scoring, parental relationship confirmation, phenotype specificity, recurrent observations, inheritance adjustments, literature extraction, and missing-information prompts. | `SKILL.md`, `QUICK_START.md`, `references/de_novo_ps2_pm6_summary.md` |
| `tooluniverse-acmg-multiple-disorder-context-refinement` | Refine disease-entity selection and evidence aggregation when one gene has multiple associated disorders, inheritance models, dosage states, phenotype spectra, or mechanisms, using ClinGen multiple-disorder guidance and gene-disease validity/dosage context. | `SKILL.md`, `QUICK_START.md`, `references/clingen_multiple_disorder_guidance.md` |
| `tooluniverse-acmg-overlay-routing-core` | Shared routing and reporting core for ACMG overlays; standardizes context-overlay order, output status fields, evidence consumption, boundary rules, and a portable registry/schema/eval compliance layer without changing criterion-specific evidence thresholds. | `SKILL.md`, `QUICK_START.md`, `overlay_registry.yaml`, `overlay_route_contract.md`, `schemas/*.schema.json`, `evals/evals.json`, `references/routing_core_conventions.md` |
| `tooluniverse-acmg-phenotype-dependent-evidence-refinement` | Route phenotype-dependent evidence such as PP4, PS4, PP1/BS4, PM3, BP5, BS2, and PS2/PM6 phenotype consistency, and request missing phenotype fields when not supplied. | `SKILL.md`, `QUICK_START.md`, `references/phenotype_dependent_criteria_summary.md` |
| `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` | Refine PM1 for regional missense intolerance, hotspots, constrained subdomains, and low benign variation while avoiding PP3/PM1 double counting. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pm2-absence-rarity-refinement` | Apply SVI-style PM2 absence/rarity logic, coverage checks, BA1/BS1/BS2 precedence, and PM2 supporting-strength boundaries. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pm3-in-trans-refinement` | Score PM3 for recessive disorders using in-trans, phase-unknown, one-parent-supported, VUS-other-allele, and homozygous evidence while checking rarity and circularity. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pm4-bp3-protein-length-refinement` | Refine PM4/BP3 for in-frame insertions/deletions, single amino-acid indels, repeat regions, stop-loss variants, and last-exon altered-product contexts using ACMG/AMP baseline wording plus explicitly labeled ACGS practice/local refinement. | `SKILL.md`, `QUICK_START.md`, `references/acgs_2024_pm4_bp3_summary.md` |
| `tooluniverse-acmg-pp1-segregation-refinement` | Refine PP1/BS4 segregation evidence using ClinGen 2024 combined PP1/BS4/PP4 points, diagnostic-yield PP4 interaction, locus-evidence cap, allele/locus apportionment, informative meioses, LOD-like reasoning, phenocopy/reduced-penetrance checks, and qualified-variant boundaries. | `SKILL.md`, `QUICK_START.md`, `references/biesecker_2024_pp1_bs4_pp4_combined_guidance.md` |
| `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` | Replace uncalibrated predictor majority voting with calibrated missense prediction evidence strengths for PP3/BP4. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` | Refine PP5/BP6 reputable-source assertions using ClinGen SVI guidance recommending discontinuation of PP5/BP6; treats secondary classifications as leads to primary evidence rather than counted criteria. | `SKILL.md`, `QUICK_START.md`, `references/biesecker_2018_pp5_bp6_summary.md` |
| `tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement` | Refine protein-level PS1/PM5 for same amino-acid substitution, same-residue missense comparison variants, same-codon edge cases, mechanism matching, splicing confounding, and circularity. | `SKILL.md`, `QUICK_START.md`, `references/acmg_2015_ps1_pm5_summary.md` |
| `tooluniverse-acmg-ps1-splicing-similarity-refinement` | Apply PS1 logic for same predicted RNA-splicing events relative to known P/LP comparison variants, with RNA-evidence precedence and duplicate-evidence guards. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-ps3-bs3-functional-assay-refinement` | Refine PS3/BS3 strength for functional assays using assay validity, disease-mechanism fit, controls, OddsPath/calibration, and duplicate-counting checks. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-ps4-case-enrichment-refinement` | Refine PS4 for formal case-control/cohort evidence, odds ratio/confidence interval, unrelated affected case counts, ancestry matching, gnomAD control caveats, and rare-disease ACGS-style case counting labeled as practice/local refinement. | `SKILL.md`, `QUICK_START.md`, `references/acgs_2024_ps4_summary.md` |
| `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` | Refine baseline PVS1 strength using Abou Tayoun et al. 2018 / ClinGen SVI PVS1 LoF decision tree, including LoF mechanism gate, NMD, start-loss, exon deletion/duplication, whole-gene deletion, rescue transcript, and in-frame branch handling. | `SKILL.md`, `QUICK_START.md`, `references/abou_tayoun_2018_pvs1_summary.md` |
| `tooluniverse-acmg-pvs1-splicing-refinement` | Refine PVS1/BP7 for RNA-splicing evidence, aberrant transcripts, exon skipping, rescue transcripts, and Walker/ClinGen SVI splicing-style logic. | `SKILL.md`, `QUICK_START.md` |
| `tooluniverse-acmg-benign-context-refinement` | Refine BA1/BS1/BS2/BP2/BP5 while keeping PM2 on the ClinGen SVI PM2 overlay; requests disease threshold, phenotype, unaffected-status, phase, and alternate-diagnosis context when missing. | `SKILL.md`, `QUICK_START.md`, `references/acgs_2024_benign_context_summary.md` |

## ACMG Overlay Trigger Policy Contract: 2026-06-18

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-overlay-routing-core/overlay_registry.yaml
M skills/tooluniverse-acmg-overlay-routing-core/overlay_route_contract.md
M skills/tooluniverse-acmg-overlay-routing-core/schemas/route_plan.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/schemas/route_audit.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/evals/evals.json
```

Behavior clarified:

- Adds registry-level `trigger_policy` values: `universal_baseline`, `variant_type_baseline`, and `evidence_discovery`.
- Adds registry-level `applies_when` and `baseline_data_sources` so agents can distinguish routes that must appear before literature review from routes that are appended after evidence discovery.
- Defines baseline route requirements for germline assessments, including population frequency gates, disease/mechanism context, source assertion review when assertions exist, and PVS1 applicability.
- Defines missense baseline routes for PP3/BP4, PS1/PM5, PM1/PP2/BP1, and structured functional-discovery search such as MaveDB when available.
- Clarifies that PS3/BS3 literature functional assays remain discovery-triggered, while structured functional database lookup is a variant-type baseline discovery source for missense variants.
- Clarifies that missing an applicable baseline route forces `draft classification`; missing a discovery route is acceptable only when no triggering evidence was found and source/literature coverage is stated.
- Adds LDLR-like missense, literature cascade-screening, MaveDB functional-score, and missing-baseline-route regression evals.
- This is a routing compliance contract update only. It does not change ACMG evidence thresholds, strength mappings, VCEP precedence, PM2/PP3 locked rules, or final classification combining.

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
- Adds a Phase 0a overlay routing core before disease-specific evidence aggregation and mechanism-sensitive evidence assignment.
- Adds explicit gates for PVS1 when LoF/haploinsufficiency is uncertain or disease mechanism may be dominant-negative, antimorphic, gain-of-function, or mixed.
- Routes PM2, BA1, PP3/BP4, PP5/BP6, protein-level PS1/PM5, PS1-splicing, PM1, baseline PVS1 LoF decision-tree, PVS1-splicing, PS3/BS3, PP1/BS4 with PP4 combined guidance, PM3, phenotype-dependent criteria, PS2/PM6 de novo evidence, PM4/BP3, and visual-literature evidence to the overlay skills through the shared routing core.
- Routes PS4 case enrichment, PM4/BP3 protein-length evidence, BA1 exception-list evidence, and BA1/BS1/BS2/BP2/BP5 benign-context evidence to dedicated overlays.
- Adds a final Tavtigian 2018 Bayesian evidence-combination phase after the overlay hard-stop audit, reporting points, OddsPath, posterior probability, and a standardized phase report without changing evidence-specific overlay thresholds.
- Specifies that PS2/PM6 uses ClinGen SVI De Novo Criteria v1.1 point scoring and routes literature-derived de novo evidence through literature deep research and figure evidence extraction before scoring.
- Adds explicit behavior for missing phenotype or de novo information: use routing-core status `not_assessed` and ask the user for targeted missing fields.
- Adds explicit behavior for missing target disease/phenotype in multi-disorder genes: mark disease-context routing as not assessed and ask before transferring disease-specific evidence.
- Routes PP4 that interacts with PP1/BS4 to ClinGen 2024 combined PP1/BS4/PP4 points, preserving the +5.0 cap and avoiding PP1/PP4/PS4 double counting.
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
- Routes context-sensitive ACMG assessment through `tooluniverse-acmg-overlay-routing-core`, which then dispatches multiple-disorder, mechanism, phenotype, source, literature, and evidence-specific overlays in order.
- Adds explicit guidance to query GeneReviews/NCBI Bookshelf when mechanism affects ACMG routing.
- Tightens truncating-variant handling: PVS1 requires confirmed LoF/haploinsufficiency for the exact gene-disease context.
- Routes ambiguous dominant/recessive, structural/complex, mixed-mechanism, or unclear HI/LoF contexts through `tooluniverse-acmg-dominant-negative-mechanism-refinement` before assigning PVS1.
- Clarifies that ClinGen gene-disease validity and dosage sensitivity are distinct, and that evidence transfer across disorders requires the multiple-disorder overlay.
- Routes baseline PVS1 strength to `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` before Walker 2023 RNA/splicing refinement.
- Clarifies that gene expression and gene-disease association scores do not substitute for patient-level PP4 or other phenotype-dependent evidence, and routes missing phenotype/de novo context to the new overlays.
- Clarifies that PP4 phenotype specificity cannot be counted independently from PP1/BS4 when both derive from the same locus, family, or diagnostic-yield evidence.
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
A skills/tooluniverse-acmg-ba1-exception-list-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ba1-exception-list-refinement/SKILL.md
A skills/tooluniverse-acmg-ba1-exception-list-refinement/references/ghosh_2018_ba1_exception_guidance.md
A skills/tooluniverse-acmg-bayesian-classification-framework/QUICK_START.md
A skills/tooluniverse-acmg-bayesian-classification-framework/SKILL.md
A skills/tooluniverse-acmg-bayesian-classification-framework/references/tavtigian_2018_bayesian_framework.md
A skills/tooluniverse-acmg-de-novo-evidence-refinement/QUICK_START.md
A skills/tooluniverse-acmg-de-novo-evidence-refinement/SKILL.md
A skills/tooluniverse-acmg-de-novo-evidence-refinement/references/de_novo_ps2_pm6_summary.md
A skills/tooluniverse-acmg-multiple-disorder-context-refinement/QUICK_START.md
A skills/tooluniverse-acmg-multiple-disorder-context-refinement/SKILL.md
A skills/tooluniverse-acmg-multiple-disorder-context-refinement/references/clingen_multiple_disorder_guidance.md
A skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
A skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
A skills/tooluniverse-acmg-overlay-routing-core/overlay_registry.yaml
A skills/tooluniverse-acmg-overlay-routing-core/overlay_route_contract.md
A skills/tooluniverse-acmg-overlay-routing-core/schemas/route_plan.schema.json
A skills/tooluniverse-acmg-overlay-routing-core/schemas/overlay_result.schema.json
A skills/tooluniverse-acmg-overlay-routing-core/schemas/route_audit.schema.json
A skills/tooluniverse-acmg-overlay-routing-core/evals/evals.json
A skills/tooluniverse-acmg-overlay-routing-core/references/routing_core_conventions.md
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
A skills/tooluniverse-acmg-pp1-segregation-refinement/references/biesecker_2024_pp1_bs4_pp4_combined_guidance.md
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
M skills/tooluniverse-acmg-pm2-absence-rarity-refinement/SKILL.md
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
- Defines standard outputs: `PVS1`, `PVS1_Strong`, `PVS1_Moderate`, `PVS1_Supporting`, `PVS1_N/A`, and `applied_evidence: none` with `status: not_assessed` when required inputs are missing.
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

## BA1 Exception List Update: 2026-06-15

Changed files:

```text
A skills/tooluniverse-acmg-ba1-exception-list-refinement/QUICK_START.md
A skills/tooluniverse-acmg-ba1-exception-list-refinement/SKILL.md
A skills/tooluniverse-acmg-ba1-exception-list-refinement/references/ghosh_2018_ba1_exception_guidance.md
M skills/tooluniverse-acmg-benign-context-refinement/QUICK_START.md
M skills/tooluniverse-acmg-benign-context-refinement/SKILL.md
M skills/tooluniverse-acmg-pm2-absence-rarity-refinement/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
```

Behavior added:

- Adds a dedicated BA1 exception-list overlay based on Ghosh et al. 2018 / ClinGen SVI, PMID:30311383, and the user-provided July 30, 2018 BA1 exception list PDF.
- Requires BA1 stand-alone benign evidence to pass the updated Ghosh 2018 definition: AF >0.05 in a general continental population dataset with at least 2,000 observed alleles and no gene- or variant-specific BA1 modification.
- Adds the nine BA1 exception-list variants as a structured reference table with gene, HGVS, ClinVar ID, ClinGen Allele Registry ID, ExAC population, MAF, and disease.
- Adds founder/bottlenecked population caveats and routes high-frequency but non-BA1 cases to BS1 review through benign-context refinement.
- Updates PM2 and variant-interpretation routing so PM2 is not applied when BA1 is valid, and BA1 is not applied before exception-list review.

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

- Adds PS4 case-enrichment overlay for formal case-control evidence and ACGS-style rare-disease affected-case counting as practice/local refinement; recessive biallelic affected-proband evidence routes to PM3 instead of PS4.
- Adds PM4/BP3 overlay for protein length changes, single amino-acid in-frame indels, repeat-region BP3, stop-loss, and last-exon altered-product contexts; PM4 is not co-used with PVS1 for the same length-changing effect.
- Adds benign-context overlay for BA1/BS1/BS2/BP2/BP5, while keeping PM2 under the ClinGen SVI PM2 overlay.
- Enhances phenotype-dependent PP4 with ACGS Appendix B-style specificity stratification as practice/local refinement and double-counting safeguards with PS2/PM6 and PS4.
- Enhances PS1/PM5 with ACGS practice/local refinement for `PS1_Moderate`, `PM5_Supporting`, initiation codon and non-coding RNA caveats, predicted-impact comparison, in-frame indel overlap, and PM1/PM5 double-counting.
- Enhances PM1/PP2/BP1 with ACGS regional resources as practice/local refinement, including DECIPHER regional constraint, CCR, MetaDome, paralogous residue evidence, critical-residue `PM1_Strong` examples, and BP1 conflict handling.
- Preserves locked priorities: PM2 remains ClinGen SVI `PM2_Supporting`, and PP3/BP4 remains Pejaver 2022 calibrated missense prediction evidence.

## ClinGen 2024 PP1/BS4/PP4 Combined Guidance Update: 2026-06-16

Changed files:

```text
M skills/tooluniverse-acmg-pp1-segregation-refinement/QUICK_START.md
M skills/tooluniverse-acmg-pp1-segregation-refinement/SKILL.md
A skills/tooluniverse-acmg-pp1-segregation-refinement/references/biesecker_2024_pp1_bs4_pp4_combined_guidance.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/QUICK_START.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/SKILL.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/references/phenotype_dependent_criteria_summary.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
```

Behavior added:

- Incorporates Biesecker et al. 2024 / ClinGen SVI guidance for PP1/BS4 co-segregation and PP4 phenotype specificity, PMID:38103548, PMCID:PMC10806742.
- Keeps the existing PP1 and phenotype-dependent overlays, but adds a combined PP1/BS4/PP4 rule layer when phenotype specificity and segregation/non-segregation use the same locus, family, or diagnostic-yield evidence.
- Adds diagnostic-yield-to-points logic for PP4, co-segregation point tables for autosomal-recessive, autosomal-dominant, and X-linked recessive scenarios, and the combined +5.0 PP1/PP4 locus-evidence cap.
- Clarifies that high-yield locus-homogeneous phenotypes should generally use PP4 locus evidence rather than adding expected perfect PP1 segregation.
- Adds BS4 caveats for autosomal-recessive compound heterozygous families, where non-segregation may not identify which allele is benign.
- Adds evidence-apportionment logic for multiple plausible candidate variants on the same allele or linked loci using the Supplemental Table S1 concept.
- Strengthens double-counting guards: the same affected individual cannot count as both PP4 and PS4, and PP1/PP4 combined evidence cannot be stacked beyond the ClinGen 2024 cap.

## ClinGen Multiple-Disorder Guidance Update: 2026-06-16

Changed files:

```text
A skills/tooluniverse-acmg-multiple-disorder-context-refinement/QUICK_START.md
A skills/tooluniverse-acmg-multiple-disorder-context-refinement/SKILL.md
A skills/tooluniverse-acmg-multiple-disorder-context-refinement/references/clingen_multiple_disorder_guidance.md
M skills/tooluniverse-acmg-dominant-negative-mechanism-refinement/SKILL.md
M skills/tooluniverse-acmg-pvs1-lof-decision-tree-refinement/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
```

Behavior added:

- Adds a dedicated multiple-disorder context overlay based on ClinGen January 2024 Guidance Classifying Variants in Genes Associated with Multiple Disorders and Thaxton et al. 2022, PMID:34694049.
- Adds a Phase 0a gate before ACMG evidence-code assignment to define target disease/entity, inheritance, mechanism, dosage state, and whether evidence can be aggregated or must be split.
- Implements the seven ClinGen categories: semidominant single condition, distinct conditions with same mechanism, spectrum/pleiotropy, mutually exclusive mechanisms, non-mutually exclusive conditions, unclear disease boundary, and multi-gene CNV.
- Clarifies that gene-disease validity and dosage sensitivity are distinct; definitive gene-disease validity does not automatically establish HI/TS, and non-sufficient dosage does not refute non-dosage mechanisms.
- Prevents transferring PVS1, PS1/PM5, PS3/BS3, PS4, PP1/BS4, PP4, PM3, BA1/BS1/PM2, or de novo evidence across split disease mechanisms without same-disease/same-mechanism support.
- Routes multi-gene CNVs to structural-variant analysis and asks for target disease/phenotype when disease-context routing cannot be completed from the supplied information.

## ACMG Overlay Routing Core and Consistency Update: 2026-06-16

Changed files:

```text
A skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
A skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
A skills/tooluniverse-acmg-overlay-routing-core/references/routing_core_conventions.md
M skills/tooluniverse-acmg-ba1-exception-list-refinement/SKILL.md
M skills/tooluniverse-acmg-benign-context-refinement/SKILL.md
M skills/tooluniverse-acmg-de-novo-evidence-refinement/SKILL.md
M skills/tooluniverse-acmg-dominant-negative-mechanism-refinement/SKILL.md
M skills/tooluniverse-acmg-multiple-disorder-context-refinement/SKILL.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/SKILL.md
M skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/SKILL.md
M skills/tooluniverse-acmg-pm2-absence-rarity-refinement/SKILL.md
M skills/tooluniverse-acmg-pm3-in-trans-refinement/SKILL.md
M skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/SKILL.md
M skills/tooluniverse-acmg-pp1-segregation-refinement/SKILL.md
M skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/SKILL.md
M skills/tooluniverse-acmg-pp5-bp6-reputable-source-refinement/SKILL.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/SKILL.md
M skills/tooluniverse-acmg-ps1-splicing-similarity-refinement/SKILL.md
M skills/tooluniverse-acmg-ps3-bs3-functional-assay-refinement/SKILL.md
M skills/tooluniverse-acmg-ps4-case-enrichment-refinement/SKILL.md
M skills/tooluniverse-acmg-pvs1-lof-decision-tree-refinement/SKILL.md
M skills/tooluniverse-acmg-pvs1-splicing-refinement/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
```

Behavior added:

- Adds `tooluniverse-acmg-overlay-routing-core` as a lightweight shared routing layer for ACMG overlays.
- Standardizes the intended context-overlay order: multiple-disorder context, mechanism context, phenotype/source/literature intake, then evidence-specific overlay.
- Standardizes structured output fields: `applied_evidence`, `status`, `reason`, `consumed_evidence`, and `routed_to`.
- Standardizes structured status values: `applied`, `no_evidence`, `not_assessed`, `not_applicable`, and `not_used`.
- Standardizes strength names as `Supporting`, `Moderate`, `Strong`, and `VeryStrong`, while preserving existing evidence labels such as `PM2_Supporting`, `PS2_VeryStrong`, and `PVS1_N/A` for display compatibility.
- Clarifies non-circular routing boundaries: BA1 exception list is the BA1 stand-alone gate; benign-context handles BS1/BS2/BP2/BP5 and BA1 follow-up context; phenotype-dependent handles intake; PP1 handles PP1/BS4/PP4 combined scoring; PVS1 LoF tree remains the baseline; Walker/RNA splicing remains a refinement; PS1-splicing remains comparison-variant evidence; PP5/BP6 is a source-review utility and not ordinary counted evidence.
- Reduces repeated precondition text in evidence-specific overlays by pointing to the routing core, without changing criterion-specific thresholds, evidence strengths, double-counting rules, or VCEP precedence.
- Preserves locked rules: PM2 remains ClinGen SVI `PM2_Supporting` by default, and PP3/BP4 remains Pejaver 2022 calibrated missense prediction evidence.

## Variant Interpretation Simplification Update: 2026-06-16

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/CHECKLIST.md
M skills/tooluniverse-variant-interpretation/CODE_PATTERNS.md
M skills/tooluniverse-variant-interpretation/EXAMPLES.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
```

Behavior added:

- Makes `tooluniverse-variant-interpretation` an intake, retrieval, and reporting skill rather than an independent ACMG classifier.
- Removes local ACMG classification helper logic and points final evidence strength assignment to `tooluniverse-acmg-variant-classification`.
- Converts predictor examples and threshold tables into retrieval/orientation guidance only; PP3/BP4 strength remains assigned by the Pejaver 2022 overlay or current VCEP rules.
- Converts SpliceAI helper examples into prediction-context output only; RNA/splicing evidence routes to PVS1/RNA, PS1-splicing, or prediction-specific overlays as appropriate.
- Treats COSMIC somatic recurrence as cancer-context or literature/domain lead, not direct germline ACMG PS3.
- Aligns checklist and examples with the same routing model: predictor evidence, PM2, BA1/BS1, SpliceAI, PVS1/RNA, PP1/BS4/PP4, and final classification are routed to overlays instead of being locally assigned by examples.
- Adds ClinGen AI note-taking policy-inspired governance safeguards to the routing core and variant-interpretation checklist: de-identify patient-level inputs, separate public from restricted evidence, disclose AI-assisted drafting when used for notes/curation drafts, require human review, and avoid automatic publication or finalization.
- Does not change any ACMG overlay threshold, PM2 default strength, PP3/BP4 locked rule, PP5/BP6 non-counting behavior, or VCEP precedence.

## PS4 Clinical-Context Clarification: 2026-06-16

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/SKILL.md
M skills/tooluniverse-acmg-ps4-case-enrichment-refinement/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
```

Behavior clarified:

- Clarifies that PS4 is mixed evidence, not uniformly user-clinical-data-dependent.
- Formal case-control, cohort, or meta-analysis PS4 can be assessed from literature or cohort data when the source defines cases, disease context, controls, ancestry handling, and enrichment statistics sufficiently.
- Rare-disease affected-case counting still requires affected-case phenotype specificity, unrelatedness, duplicate-report checks, and population-control context from the paper, database, or user.
- Updates phenotype-dependent routing so PS4 only enters patient-phenotype intake when disease/case ascertainment is missing or when rare-disease case-count evidence needs case-level context.
- Does not change PS4 thresholds, ACGS rare-disease case-count handling now labeled as practice/local refinement, PM3 routing for recessive biallelic probands, or VCEP precedence.

## Clinical Phenotype Dependency Audit: 2026-06-16

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/SKILL.md
M skills/tooluniverse-acmg-benign-context-refinement/SKILL.md
M skills/tooluniverse-acmg-multiple-disorder-context-refinement/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
```

Behavior clarified:

- Adds a shared clinical-context dependency matrix separating `user_patient_phenotype_required`, `literature_case_context_required`, `literature_or_cohort_case_definition_required`, and `disease_context_only` inputs.
- Confirms that patient-level phenotype is required or may be required for PP4, PP1/BS4, PS2/PM6, PM3, BS2, BP2, BP5, and rare-disease PS4 case counting when those facts are not already present in a source.
- Confirms that formal PS4 case-control/cohort/meta-analysis evidence requires study case definition and statistics, not user-supplied patient phenotype when the publication is adequate.
- Clarifies that BA1/BS1/PM2, PVS1, PM1/PP2/BP1, PP3/BP4, PM4/BP3, and PS1/PM5 usually need disease, mechanism, transcript, threshold, protein-region, prediction, or comparison-variant context rather than patient phenotype.
- Does not change any evidence thresholds, strength mappings, VCEP precedence, or double-counting rules.

## External-Agent Overlay Compliance Guardrails: 2026-06-16

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-acmg-ps3-bs3-functional-assay-refinement/SKILL.md
M skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/SKILL.md
M skills/tooluniverse-acmg-pp5-bp6-reputable-source-refinement/SKILL.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/SKILL.md
M skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/SKILL.md
M skills/tooluniverse-variant-interpretation/CHECKLIST.md
```

Behavior clarified:

- Adds explicit external-agent compliance outcomes for each considered criterion: `overlay_applied`, `overlay_not_applicable`, `overlay_not_assessed`, and `overlay_deferred_to_vcep`.
- Requires imported agents to record overlay routing before final classification rather than using the base ACMG workflow as a manual checklist.
- Strengthens PS3/BS3 guardrails: segregation, case recurrence, de novo evidence, PM3-compatible biallelic evidence, HGMD/ClinVar labels, and another paper's ACMG code cannot be counted as PS3 unless the actual functional assay is retrieved and evaluated.
- Strengthens PP3/BP4 guardrails against local predictor-majority reasoning across CADD, SIFT, PolyPhen, or similar tools; counted evidence must come from Pejaver 2022 calibrated thresholds or a current VCEP rule.
- Strengthens PP5/BP6 and PS1/PM5 guardrails so reputable-source labels are source leads only and cannot be directly promoted into PM5, PM1, PS3, PP3, or other counted evidence without primary evidence review.
- Strengthens PM1 guardrails against broad domain membership or another source's PM1 label without reviewable hotspot, constrained-region, critical-residue, or low-benign-variation evidence.
- Does not change any evidence threshold, strength mapping, locked PM2/PP3 rules, VCEP precedence, or final ACMG combining rule.

## External-Agent Compliance and Literature-Provenance Guardrail Cleanup: 2026-06-16

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-literature-deep-research/SKILL.md
M skills/tooluniverse-literature-deep-research/FULLTEXT_STRATEGY.md
M skills/tooluniverse-literature-figure-evidence-extraction/SKILL.md
M skills/tooluniverse-literature-figure-evidence-extraction/references/figure_evidence_schema.md
M skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/SKILL.md
M skills/tooluniverse-acmg-ps3-bs3-functional-assay-refinement/SKILL.md
M skills/tooluniverse-acmg-ps4-case-enrichment-refinement/SKILL.md
M skills/tooluniverse-acmg-pp1-segregation-refinement/SKILL.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/SKILL.md
M skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/SKILL.md
```

Behavior clarified:

- Adds final hard-stop audit language: every counted evidence item must have `overlay_applied` or `overlay_deferred_to_vcep`; otherwise the report remains `draft classification`.
- Separates source assertions from current counted evidence so ClinVar/HGMD/VCEP/paper labels cannot drive the final ACMG tier by themselves.
- Adds literature provenance fields and the required sequence for inaccessible papers: search full text and supplements first, ask the user for PDF/source material if needed, then list as `missing evidence` only if still unavailable.
- Clarifies that abstract-only, unavailable full-text, unread supplement, and low-confidence figure/OCR evidence are leads only unless a current VCEP explicitly permits use.
- Reinforces PP3/BP4 Pejaver 2022 handling: no fallback PP3 from developer-default CADD/SIFT/PolyPhen-style labels or predictor-majority reasoning when calibrated scores are missing.
- Reinforces PS3/BS3 handling: do not upgrade by counting multiple historical functional publications; use the best validated assay unless VCEP, OddsPath, or a validated combination rule permits combining.
- Adds PS4 caveats for founder haplotypes, shared ancestry, mutation-positive cohorts, gnomAD-as-control comparisons, and case-series recurrence.
- Adds PP1 guardrails for proband counting, co-segregating individual versus informative meiosis units, Biesecker/fallback non-mixing, figure provenance, and PP1/PP4/PS4 double counting.
- Adds PS1/PM5 comparison-variant provenance and PM1 broad-domain checks.
- Does not change any evidence threshold, strength mapping, VCEP precedence, PM2 default `PM2_Supporting`, PP3/BP4 Pejaver 2022 rule, or final ACMG combining rule.

## ACMG Overlay Consistency and Compliance Cleanup: 2026-06-16

Changed files:

```text
M skills/tooluniverse-acmg-ba1-exception-list-refinement/SKILL.md
M skills/tooluniverse-acmg-benign-context-refinement/SKILL.md
M skills/tooluniverse-acmg-de-novo-evidence-refinement/SKILL.md
M skills/tooluniverse-acmg-dominant-negative-mechanism-refinement/SKILL.md
M skills/tooluniverse-acmg-multiple-disorder-context-refinement/SKILL.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/SKILL.md
M skills/tooluniverse-acmg-pm2-absence-rarity-refinement/SKILL.md
M skills/tooluniverse-acmg-pm3-in-trans-refinement/SKILL.md
M skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/SKILL.md
M skills/tooluniverse-acmg-pp3-bp4-missense-prediction-refinement/SKILL.md
M skills/tooluniverse-acmg-pp5-bp6-reputable-source-refinement/SKILL.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/SKILL.md
M skills/tooluniverse-acmg-ps3-bs3-functional-assay-refinement/SKILL.md
M skills/tooluniverse-acmg-ps4-case-enrichment-refinement/SKILL.md
M skills/tooluniverse-acmg-pvs1-lof-decision-tree-refinement/SKILL.md
M skills/tooluniverse-acmg-pvs1-splicing-refinement/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-variant-interpretation/SKILL.md
```

Behavior clarified:

- Removes the residual misleading main-workflow example that implied a ClinVar expert-panel source label could directly count as PS1.
- Removes the old variant-interpretation fallback suggesting CADD/SIFT/PolyPhen consensus could substitute for missing REVEL; missing calibrated prediction now routes to PP3/BP4 overlay or `status: not_assessed`.
- Normalizes structured missing-information output to `status: not_assessed` with the explanatory text placed in `reason`, rather than using uncontrolled free-text values inside evidence fields.
- Converts legacy source-review and PVS1 missing-input display labels to `applied_evidence: none` plus `status: not_assessed` in structured output guidance.
- Tightens common examples so ClinVar/CIViC/HGMD-style assertions are source leads, PP3/BP4 is assigned by calibrated overlay/VCEP, PM1 requires overlay-confirmed eligible regional evidence, and PS3 requires actual functional assay evidence.
- Does not change evidence thresholds, strength mappings, VCEP precedence, PM2 default `PM2_Supporting`, PP3/BP4 Pejaver 2022 handling, or the final ACMG combining rule.

## ClinGen Guidance Authority Alignment Cleanup: 2026-06-17

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-acmg-ps4-case-enrichment-refinement/SKILL.md
M skills/tooluniverse-acmg-ps4-case-enrichment-refinement/QUICK_START.md
M skills/tooluniverse-acmg-ps4-case-enrichment-refinement/references/acgs_2024_ps4_summary.md
M skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/SKILL.md
M skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/QUICK_START.md
M skills/tooluniverse-acmg-pm4-bp3-protein-length-refinement/references/acgs_2024_pm4_bp3_summary.md
M skills/tooluniverse-acmg-benign-context-refinement/SKILL.md
M skills/tooluniverse-acmg-benign-context-refinement/QUICK_START.md
M skills/tooluniverse-acmg-benign-context-refinement/references/acgs_2024_benign_context_summary.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/SKILL.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/QUICK_START.md
M skills/tooluniverse-acmg-phenotype-dependent-evidence-refinement/references/phenotype_dependent_criteria_summary.md
M skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/SKILL.md
M skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/QUICK_START.md
M skills/tooluniverse-acmg-pm1-regional-missense-constraint-refinement/references/pmid38645134_regional_missense_constraint_summary.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/SKILL.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/QUICK_START.md
M skills/tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement/references/acmg_2015_ps1_pm5_summary.md
```

Behavior clarified:

- Adds a required `guidance_authority` field for counted evidence, with controlled labels `ClinGen/SVI primary`, `ACMG/AMP baseline`, `VCEP-specific`, `practice/local refinement`, and `source lead only`.
- Clarifies that formal ClinGen/SVI recommendations, ACMG/AMP 2015 baseline criteria, and VCEP-specific rules must be distinguished from ACGS 2024, non-ClinGen literature, and local operational guardrails.
- Re-labels PS4 rare-disease affected-case counting from ACGS 2024 as `practice/local refinement`; formal case-control/cohort enrichment and VCEP rules remain the primary PS4 paths.
- Re-labels PM4/BP3 single-amino-acid indel, stop-loss, and last-exon altered-product details from ACGS 2024 as `practice/local refinement`; ACMG/AMP 2015 remains the baseline authority.
- Keeps BA1/Ghosh 2018 as `ClinGen/SVI primary` while labeling ACGS details for BS1/BS2/BP2/BP5 as `practice/local refinement` unless adopted by VCEP.
- Clarifies that Biesecker et al. 2024 is `ClinGen/SVI primary` for combined PP1/BS4/PP4 guidance, while standalone ACGS-style PP4 stratification is `practice/local refinement`.
- Clarifies that PMID:38645134 regional missense constraint is a non-ClinGen regional evidence refinement for PM1 unless a VCEP or local policy adopts the threshold.
- Clarifies that protein-level PS1/PM5 is `ACMG/AMP baseline`, Walker 2023 is `ClinGen/SVI primary` only for splicing-specific PS1/PVS1 interactions, and ACGS PS1/PM5 downgrades or edge-case extensions are `practice/local refinement`.
- Does not change any evidence threshold, strength mapping, VCEP precedence, PM2 default `PM2_Supporting`, PP3/BP4 Pejaver 2022 handling, or final ACMG combining rule.

## ACMG Overlay Skill-Gate Compliance Contract: 2026-06-18

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
A skills/tooluniverse-acmg-overlay-routing-core/overlay_registry.yaml
A skills/tooluniverse-acmg-overlay-routing-core/overlay_route_contract.md
A skills/tooluniverse-acmg-overlay-routing-core/schemas/route_plan.schema.json
A skills/tooluniverse-acmg-overlay-routing-core/schemas/overlay_result.schema.json
A skills/tooluniverse-acmg-overlay-routing-core/schemas/route_audit.schema.json
A skills/tooluniverse-acmg-overlay-routing-core/evals/evals.json
```

Behavior clarified:

- Adds a portable compliance layer for external agents that import ToolUniverse ACMG overlays: registry, route contract, JSON Schemas, and regression evals.
- Defines three machine-checkable routing phases: `candidate_detection`, `mandatory_overlay_route`, and `counted_evidence_audit`.
- Adds `overlay_registry.yaml` to map candidate ACMG evidence signals to mandatory overlay skills, including PP1/BS4/PP4, PS3/BS3, PS4, PP3/BP4, PP5/BP6, PVS1, PM2, BA1/BS1/BS2/BP2/BP5, PS1/PM5, PM1/PP2/BP1, PM3, PS2/PM6, and mechanism/disease-context overlays.
- Adds JSON Schemas for route plans, overlay results, and route audits so later validators or harnesses can check whether counted evidence has an overlay or VCEP trace.
- Adds regression eval cases for common overlay-bypass failures: direct PP1 strength assignment from family evidence, PS3 from source labels, PS4 from case recurrence without study fields, PP3 from predictor-majority reasoning, PP5/BP6 from source assertions, PVS1 from consequence alone, PM2_Moderate from absence alone, broad-domain PM1, source-label PM5, and missing final route audits.
- Keeps the first version as a GitHub-shareable compliance contract rather than a full enforcement runtime or MCP tool.
- Does not change any evidence threshold, strength mapping, VCEP precedence, PM2 default `PM2_Supporting`, PP3/BP4 Pejaver 2022 handling, or final ACMG combining rule.

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
