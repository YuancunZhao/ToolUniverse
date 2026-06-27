# ToolUniverse Overlay Difference List

Last updated: 2026-06-25

Baseline comparison:

- Upstream: `mims-harvard/ToolUniverse`, `upstream/main` at `574a7027`
- Overlay branch: `YuancunZhao/ToolUniverse`, `codex/skills-overlay` at `073b2199`
- Diff command: `git diff --name-status upstream/main...codex/skills-overlay -- skills`

Summary:

- Added skills: 22
- Modified upstream skills: 4
- Deleted upstream skills: 0
- Changed files under `skills/`: 76
- Net intended overlay diff: approximately 11700 insertions, 230 deletions

## ACMG Gate Complexity Consolidation: 2026-06-27

This change keeps the MCP front-door gate strict while reducing duplicate downstream planning surfaces.

- Adds a shared ACMG gate policy module so high-risk tool lists, gate notices, recommended intake tools, coverage categories, and literature no-hit route families are maintained in one place.
- Keeps `find_tools`, direct `Tool_Finder_Keyword`, and direct `execute_tool` gate behavior, but stops synthesizing extra direct-tool search entries when those tools were not returned by the normal search.
- Narrows the default `ACMG_overlay_gate_assess_variant` compact output to preflight status, recommended intake calls, required coverage categories, source leads, validator result, violations, and next actions.
- Leaves full route rows and empty bundle skeleton output available only through `output_mode: "full"` for debugging and fixture construction.
- Adds `--mode minimal` to the validator for lightweight integrations while keeping strict validation as the default ToolUniverse ACMG gate behavior.
- Updates routing-core documentation to describe a three-step MCP workflow: call the gate tool, run recommended evidence/literature intake, then validate the assessment bundle before any final classification.

This is complexity consolidation only. It does not change ACMG evidence thresholds, strength mappings, VCEP precedence, database query logic, online literature requirements, or final combiner behavior.

## ACMG Gate Direct-MCP Hardening: 2026-06-26

This change closes a remaining bypass path where an agent can skip ACMG skills and call ToolUniverse MCP tools such as GeneBe, ClinVar, SpliceAI, MyVariant, or Ensembl VEP directly, then turn those outputs into final ACMG evidence.

- Adds `ACMG_overlay_gate_assess_variant` as a lightweight ToolUniverse MCP front-door gate for germline ACMG/pathogenicity tasks. The tool returns compact CLI/agent output by default, exposes full route rows and bundle skeletons via `output_mode: "full"`, normalizes automated classifiers as source leads, and validates supplied `acmg_assessment_bundle` payloads; it is not a new ACMG classifier.
- Updates ToolUniverse MCP search handling so ACMG/pathogenicity/five-tier variant-classification queries surface `ACMG_overlay_gate_assess_variant` as the recommended front-door tool before direct tools such as GeneBe, InterVar, ClinVar, SpliceAI, MyVariant, or VEP.
- Adds direct-MCP regression coverage for an FGFR3-like transcript where GeneBe, SpliceAI, VEP, and MyVariant outputs are manually combined into a final `Likely Pathogenic` call without an `acmg_assessment_bundle` or validator `PASS`.
- Extends the entrypoint bypass checker to flag direct ToolUniverse MCP variant-tool usage plus final ACMG wording when validator `PASS` is absent.
- Adds optional static checks for high-risk ToolUniverse tool definitions so GeneBe, InterVar, ClinVar clinical significance, SpliceAI, MyVariant pathogenicity scores, and Ensembl VEP definitions must carry source-lead / not-counted-evidence / validator-PASS gate wording.
- Updates `tooluniverse-acmg-overlay-routing-core/QUICK_START.md` to state that direct ToolUniverse MCP outputs remain source leads or route triggers until routed through the bundle and validator.
- Updates ToolUniverse runtime metadata in the fork so high-risk direct MCP tool results, parameter-validation errors, and ACMG/pathogenicity tool-search responses carry an `acmg_gate_notice`.
- Hardens gate priority for Chinese and real-HGVS queries such as `根据ACMG规则评估 ... 杂合变异致病性`, so `ACMG_overlay_gate_assess_variant` is surfaced before direct evidence tools.
- Reuses the same front-door gate search helper from both the MCP `find_tools` wrapper and direct `Tool_Finder_Keyword` execution, closing a bypass where agents could call the tool finder through `execute_tool`.
- Packages a runtime fallback copy of the overlay registry, assessment-bundle schema, and validator under `tooluniverse.data` so installed ToolUniverse builds can run the gate tool even when repository-level `skills/` files are not present.
- Adds Chinese direct-MCP regression coverage and gate-priority implementation checks to the entrypoint bypass checker.
- Requires actual online literature coverage before final ACMG/pathogenicity output. A no-hit PubMed/PMC/EuropePMC or ToolUniverse literature search is acceptable, but an empty placeholder or skipped search is not.
- Extends the gate tool output with online literature query templates and required coverage tasks for literature, population, computational, source assertion, functional database, disease/mechanism, and clinical context sources.
- Tightens validator/checker behavior so direct MCP outputs from GeneBe/InterVar, ClinVar, SpliceAI/VEP/MyVariant, gnomAD, MaveDB/DMS, ClinGen/G2P/GeneReviews, or user family/phenotype input cannot become counted ACMG evidence without coverage audit, overlay routing, and validator `PASS`.

This is direct-MCP/tool-output gate hardening only. It does not add a full harness, query databases in the validator, assign evidence strength, change VCEP precedence, change ACMG thresholds, or modify the final combiner.

## ACMG Overlay Gate Convergence: 2026-06-24

This change converges the overlay compliance layer around `registry + assessment bundle + validator`.

- Added `tooluniverse-acmg-overlay-routing-core/schemas/acmg_assessment_bundle.schema.json` as the required final-report bundle shape.
- Added `tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py`, a dependency-free validator returning `PASS`, `DRAFT_ONLY`, or `FAIL`.
- Added `tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures/` regression fixtures for DHX30-like direct bypass, source-label counting, missing missense baseline routes, PP1 no-hit coverage, MaveDB no-hit, MaveDB raw-score counting, and missing compatibility resolution.
- Updated `tooluniverse-acmg-overlay-routing-core/SKILL.md`, `QUICK_START.md`, and `overlay_route_contract.md` to state the hard gate: no validator-passing ACMG assessment bundle, no final ACMG classification.
- Updated `tooluniverse-acmg-variant-classification/SKILL.md` to make the assessment bundle and validator the final-classification gate for external agents.

This is a routing-compliance enforcement change only. It does not change ACMG evidence thresholds, strength mapping, VCEP precedence, final combiner behavior, database query logic, or ToolUniverse MCP tools.

## ACMG Overlay Gate Hardening: 2026-06-24

This change closes validator gaps found during review.

- Requires final classifications to have non-empty `current_counted_evidence_resolved` and at least one matching counted route-audit row with `overlay_applied` or `overlay_deferred_to_vcep`.
- Requires final classifications to include literature/discovery coverage, or an explicit literature `unavailable` / `not_applicable` row.
- Requires literature trigger hits such as pedigree, functional assay, cohort, de novo, or in-trans evidence to route to the corresponding discovery overlay.
- Aligns validator structural checks with the assessment-bundle schema for key controlled values and requires `route_audit.counted` to be boolean.
- Adds validator fixtures for empty final evidence, route-audit/resolved-evidence mismatch, missing literature coverage, literature pedigree trigger without PP1 route, and invalid string `counted` values.
- Demotes old section schemas to internal/reference artifacts in the routing-core skill entrypoint; external agents should use `overlay_registry.yaml`, `acmg_assessment_bundle.schema.json`, and `validate_acmg_overlay_bundle.py`.

This remains a lightweight compliance validator. It does not query databases, execute overlays, assign evidence strength, or change the final ACMG combiner.

## ACMG Gate Entrypoint Hardening: 2026-06-25

This change moves the validator gate to the main variant pathogenicity entrypoints so external agents cannot bypass the bundle by staying in a general router or evidence-intake skill.

- Updates `tooluniverse/SKILL.md` so ACMG classification, pathogenicity, variant clinical significance, VUS, and "is this variant pathogenic" requests route to `tooluniverse-acmg-variant-classification` for final classification rather than stopping at `tooluniverse-variant-interpretation`.
- Updates `tooluniverse-variant-interpretation/SKILL.md` to define Phase 6 as intake-only and require handoff to `tooluniverse-acmg-variant-classification` for final ACMG answers.
- Updates `tooluniverse-acmg-variant-classification/SKILL.md` so final five-tier output requires a validator summary block with `validator_status: PASS`; otherwise the classification status remains draft-only.
- Adds entrypoint bypass fixtures and a lightweight text checker for VWF-like GeneBe direct classification, natural-language route-table substitution, variant-interpretation direct final answers, and the accepted validator-PASS pattern.

This is an entrypoint compliance change only. It does not add a ToolUniverse MCP tool, query databases, assign evidence strength, change VCEP precedence, or modify the final ACMG combiner.

## ACMG Gate Full Entrypoint Closure: 2026-06-25

This change closes remaining entrypoint and final-output bypass paths found after the first entrypoint hardening pass.

- Reframes `tooluniverse-variant-interpretation` as evidence intake and draft reporting only; its frontmatter no longer advertises final ACMG/pathogenicity classification.
- Repoints final ACMG/pathogenicity cross-skill references from `tooluniverse-variant-interpretation` to `tooluniverse-acmg-variant-classification`.
- Adds the same `acmg_assessment_bundle` and `validator_status: PASS` requirement to the Bayesian final-combination skill before any final five-tier tier is presented.
- Rewords rare-disease diagnosis variant sections so ClinVar/predictor/structure signals remain diagnosis context or ACMG route leads unless the ACMG gate validates.
- Extends entrypoint bypass regression checks to scan static skill text and adds fixtures for Bayesian final output without validator PASS, rare-disease VUS promotion, and cross-skill final-routing bypass.

This is still a skill-routing and output-gate change only. It does not change ACMG thresholds, evidence strength mapping, VCEP precedence, database query logic, or Tavtigian/Bayesian formulas.

## Added Skills

### ACMG Evidence Refinement Overlays

These are additive overlays intended to refine ACMG/AMP evidence assignment without replacing the base ToolUniverse variant skills.

| Skill | Purpose | Files |
| --- | --- | --- |
| `tooluniverse-acmg-ba1-exception-list-refinement` | Refine BA1 stand-alone benign evidence using Ghosh et al. 2018 ClinGen SVI BA1 definition, 2,000 observed-allele requirement, general continental population dataset checks, founder-population caveats, gene/variant-specific BA1 modifications, and the BA1 exception list. | `SKILL.md`, `QUICK_START.md`, `references/ghosh_2018_ba1_exception_guidance.md` |
| `tooluniverse-acmg-bayesian-classification-framework` | Convert already-routed and compatibility-resolved ACMG/AMP evidence strengths into Tavtigian et al. 2018 Bayesian points, OddsPath, posterior probability, and standardized phase output after the final overlay route audit and evidence compatibility gate. | `SKILL.md`, `QUICK_START.md`, `references/tavtigian_2018_bayesian_framework.md` |
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
M skills/tooluniverse-acmg-overlay-routing-core/schemas/evidence_compatibility.schema.json
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

## ACMG Overlay Query-Aware Enforcement Contract: 2026-06-22

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-overlay-routing-core/overlay_registry.yaml
M skills/tooluniverse-acmg-overlay-routing-core/overlay_route_contract.md
M skills/tooluniverse-acmg-overlay-routing-core/schemas/route_plan.schema.json
A skills/tooluniverse-acmg-overlay-routing-core/schemas/coverage_audit.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/evals/evals.json
```

Behavior clarified:

- Adds registry-level `enforcement_level` values: `must_plan`, `must_query`, `must_route_if_hit`, and `must_audit_if_counted`.
- Adds registry-level `route_kind` values: `applicability_gate`, `evidence_scoring`, `source_review`, `functional_discovery`, and `compatibility_gate`.
- Adds `expected_default_status` so applicability gates such as missense PVS1 can be planned with an expected `not_applicable` result.
- Adds `schemas/coverage_audit.schema.json` for queried sources, query status, hits, triggered routes, not-triggered routes, and rationale.
- Clarifies that MaveDB or equivalent structured functional databases are `must_query` for missense functional discovery; a hit triggers PS3/BS3 routing, while no hit is a coverage audit result rather than a forced overlay.
- Clarifies source-label fan-out: ClinVar, HGMD, LOVD, VCEP, lab, or paper labels route to PP5/BP6 source review by default; evidence-specific fan-out requires explicit criterion codes, primary-evidence keywords, or retrievable primary evidence.
- Adds regression evals for LDLR p.His583Tyr coverage audit, MaveDB hit/no-hit behavior, ClinVar label-only fan-out blocking, paper criterion-code fan-out, PP1 absence after literature no-hit, and abstract-only family evidence.
- This remains a portable compliance contract. It does not add a CLI, MCP tool, runtime database query layer, ACMG threshold change, VCEP precedence change, or final combiner change.

## Variant Pathogenicity Route-Bundle Optimization and SV Bypass Cleanup: 2026-06-22

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-overlay-routing-core/overlay_route_contract.md
A skills/tooluniverse-acmg-overlay-routing-core/schemas/bundle_route_plan.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/schemas/route_plan.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/evals/evals.json
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-structural-variant-analysis/SKILL.md
M skills/tooluniverse-structural-variant-analysis/CLASSIFICATION_GUIDE.md
M skills/tooluniverse-structural-variant-analysis/ANALYSIS_PROCEDURES.md
M skills/tooluniverse-structural-variant-analysis/REPORT_TEMPLATE.md
M skills/tooluniverse-structural-variant-analysis/EXAMPLES.md
M skills/tooluniverse-variant-analysis/SKILL.md
M skills/tooluniverse-variant-analysis/references/sv_cnv_analysis.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
M skills/tooluniverse-variant-interpretation/EXAMPLES.md
M skills/tooluniverse-rare-disease-diagnosis/EXAMPLES.md
```

Behavior clarified:

- Adds a `Route Bundle Quick Planner` to the routing core so external agents can plan compact bundles before expanding triggered bundles into registry-backed overlay routes.
- Adds `schemas/bundle_route_plan.schema.json` as the first-class compact bundle planning artifact, allowing non-ACMG intake steps in `required_checks` while keeping counted evidence tied to expanded ACMG overlay route rows.
- Adds optional `route_bundle` to `schemas/route_plan.schema.json` and regression evals for route-bundle planning, SV/CNV standalone-classification blocking, Bayesian refusal without compatibility artifacts, and bundle-row-not-counted safeguards.
- Simplifies the main ACMG workflow into a dispatcher: normalize variant, establish context, emit bundle route plan, run triggered overlays, resolve compatibility, then combine.
- Converts `tooluniverse-structural-variant-analysis` into SV/CNV evidence intake. It now outputs evidence summaries and route candidates rather than standalone final germline ACMG classification, 0-10 pathogenicity score, or directly counted ACMG criteria.
- Updates `tooluniverse-variant-analysis` SV/CNV reference to route structural variant evidence through SV intake and ACMG overlays.
- Replaces direct final-classification examples in `tooluniverse-variant-interpretation` with retrieval and route-planning examples.
- Removes residual de novo shortcut language from a rare-disease example; de novo observations now route to the PS2/PM6 overlay.
- This is a workflow efficiency and bypass-prevention cleanup only. It does not change evidence-specific thresholds, ClinGen/VCEP authority, PM2 default strength, PP3/BP4 Pejaver handling, evidence compatibility rules, or Bayesian formulas.

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
- Adds a final compatibility-resolution gate after the overlay hard-stop audit, then a Tavtigian 2018 Bayesian evidence-combination phase that consumes only `current_counted_evidence_resolved`, reporting points, OddsPath, posterior probability, and a standardized phase report without changing evidence-specific overlay thresholds.
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
A skills/tooluniverse-acmg-overlay-routing-core/schemas/evidence_compatibility.schema.json
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
A skills/tooluniverse-acmg-overlay-routing-core/schemas/evidence_compatibility.schema.json
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

## Final Combine Evidence Compatibility Resolution: 2026-06-18

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
M skills/tooluniverse-acmg-overlay-routing-core/overlay_registry.yaml
M skills/tooluniverse-acmg-overlay-routing-core/overlay_route_contract.md
A skills/tooluniverse-acmg-overlay-routing-core/schemas/evidence_compatibility.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/evals/evals.json
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-acmg-bayesian-classification-framework/SKILL.md
```

Behavior added:

- Adds a universal final-combine `Evidence Compatibility Resolution` gate after route audit and before qualitative ACMG or Tavtigian Bayesian combine.
- Adds required compatibility artifacts: `current_counted_evidence_resolved`, `not_used_due_to_overlap`, `caps_applied`, `context_splits`, and `unresolved_conflicts`.
- Adds `schemas/evidence_compatibility.schema.json` with controlled resolution values: `keep_more_specific`, `keep_primary_evidence`, `keep_mechanism_appropriate`, `drop_as_not_used`, `cap_combined_strength`, `split_by_context`, `defer_to_vcep`, and `unresolved_draft_only`.
- Extends `overlay_registry.yaml` with `criterion_group: evidence_compatibility_resolution`, `trigger_policy: universal_baseline`, and `applies_when: final_counted_evidence_before_combination`.
- Updates `tooluniverse-acmg-variant-classification` so Phase 7 resolves compatibility and Phase 8 Bayesian calculation consumes only `current_counted_evidence_resolved`.
- Updates `tooluniverse-acmg-bayesian-classification-framework` so unresolved conflicts block final OddsPath/posterior calculation and return `draft classification`.
- Documents v1 incompatibility/cap/split rules for frequency evidence, disease/mechanism context, PVS1/RNA/splicing, PVS1/PM4/CNV, functional/computational reuse, PM1/PP2/PP3, PS1/PM5, clinical-observation reuse, PP1/PP4 caps, PM3/de novo caps, and source/provenance leads.
- Adds regression evals for BA1/PM2/BS1, PP2/BP1, PVS1/PP3, PVS1_RNA/PS3/PP3, BP7_RNA/BS3/PS1-splicing, PM4/PVS1/BP3, whole-gene deletion dosage reuse, multiple/conflicting assays, DMS reuse, PM1/PP2/PP3 cap, PS1/PM5, PM5/PM1/PM4 overlap, same-proband clinical evidence reuse, PP1/PP4 cap, PS2/PM6 phenotype double counting, PM3 circularity/duplicates/homozygous cap, multiple-disorder context split, missing compatibility artifact, and unresolved Bayesian hard stop.
- Does not assign new evidence, alter evidence-specific thresholds, change strength mappings, change VCEP precedence, or modify locked PM2 and PP3/BP4 rules.

## Shared-Agent Bypass Cleanup and Final-Combine Consistency Pass: 2026-06-18

Changed files:

```text
M skills/tooluniverse-rare-disease-diagnosis/DIAGNOSTIC_WORKFLOW.md
M skills/tooluniverse-rare-disease-diagnosis/REPORT_TEMPLATE.md
M skills/tooluniverse-rare-disease-diagnosis/EXAMPLES.md
M skills/tooluniverse-rare-disease-diagnosis/TOOLS_REFERENCE.md
M skills/tooluniverse-variant-interpretation/ACMG_CLASSIFICATION.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
M skills/tooluniverse-acmg-bayesian-classification-framework/QUICK_START.md
M skills/tooluniverse-acmg-overlay-routing-core/overlay_registry.yaml
M skills/tooluniverse-acmg-overlay-routing-core/schemas/route_audit.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/schemas/evidence_compatibility.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/evals/evals.json
```

Behavior clarified:

- Removes residual direct ACMG strength shortcuts from rare-disease diagnosis templates and examples, including PM2 Moderate from absence, PP3 from predictor consensus, SpliceAI-only PP3/BP7, and affected-family-member PS4 shortcuts.
- Converts rare-disease Phase 4 variant output into candidate route, prediction context, required overlay, route status, and missing-input reporting.
- Converts variant-interpretation quick references and predictor helper output into route-index and prediction-context language rather than local evidence-strength assignment.
- Aligns Bayesian Quick Start with the final-combine compatibility gate by requiring `current_counted_evidence_resolved` and empty `unresolved_conflicts` before OddsPath or posterior calculation.
- Clarifies in the routing registry that SpliceAI-only evidence is prediction/comparison context and does not trigger PVS1_RNA without RNA assay, published RNA evidence, or observed transcript consequence.
- Adds schema comments that JSON Schema validates field shape only; hard-stop invariants are enforced by the routing contract and evals.
- Adds regression evals for rare-disease template bypass, variant-interpretation predictor voting, raw-counted-evidence Bayesian use, and SpliceAI-only PVS1_RNA misrouting.
- Does not add evidence criteria, change overlay thresholds, change VCEP precedence, or modify locked PM2 and PP3/BP4 rules.

## Literature Provenance Hard-Stop Upgrade: 2026-06-24

Changed files:

```text
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
M skills/tooluniverse-acmg-overlay-routing-core/overlay_route_contract.md
M skills/tooluniverse-acmg-overlay-routing-core/schemas/acmg_assessment_bundle.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/schemas/route_audit.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/schemas/overlay_result.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/schemas/evidence_compatibility.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py
M skills/tooluniverse-acmg-overlay-routing-core/evals/evals.json
A skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures/abstract_only_literature_counted.json
M skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures/README.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
```

Behavior clarified:

- Adds structured `literature_provenance` fields for literature-backed evidence: `full_text_status`, `supplement_status`, `figure_status`, `counted_evidence_allowed`, and `reason`.
- Extends the validator so counted literature-backed evidence with `abstract_only`, `source_unavailable`, unavailable required supplements, or uninterpretable required figures blocks final classification unless a current VCEP explicitly allows abstract-level use.
- Keeps abstract-only literature as a source lead rather than discarding it. The lead should trigger full-text/supplement retrieval or a user PDF/source request, and only unresolved counted use is blocked.
- Adds regression coverage for abstract-only literature incorrectly counted as PS3.
- Does not change any evidence threshold, strength mapping, VCEP precedence, or final-combine rule.

## Peripheral Bypass Cleanup and Context Artifact Hardening: 2026-06-24

Changed files:

```text
M skills/tooluniverse-variant-functional-annotation/SKILL.md
M skills/tooluniverse-rare-disease-genomics/SKILL.md
M skills/tooluniverse-protein-lof-mechanism/SKILL.md
M skills/tooluniverse-protein-sae-variant-interpretation/SKILL.md
M skills/tooluniverse-variant-interpretation/SKILL.md
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
M skills/tooluniverse-acmg-overlay-routing-core/overlay_route_contract.md
M skills/tooluniverse-acmg-overlay-routing-core/schemas/acmg_assessment_bundle.schema.json
M skills/tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py
M skills/tooluniverse-acmg-overlay-routing-core/evals/evals.json
A skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures/outer_skill_cadd_pp3_counted.json
A skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures/reduced_penetrance_bs2_missing_context.json
A skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures/vcep_scope_mismatch_counted.json
M skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures/no_pp1_literature_no_hit_pass.json
M skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures/README.md
```

Behavior clarified:

- Converts `tooluniverse-variant-functional-annotation` into retrieval/orientation output only, removing CADD-to-PP3/BP4 shortcuts, ClinVar-label override language, and variant-level evidence grading.
- Marks rare-disease genomics tiers as gene-disease prioritization only; ClinVar/HGMD/LOVD/lab/paper labels remain source leads until primary evidence is routed.
- Limits protein SAE/LoF mechanism outputs to mechanism or prediction context; they cannot directly assign PVS1, PS3, PP3, PM1, or final ACMG classification.
- Adds shared `disease_context`, `penetrance_context`, and `vcep_context` artifacts to the final ACMG assessment bundle and validator.
- Requires penetrance context before final classification when penetrance-sensitive evidence such as BS1, BS2, BS4, PP1, PP4, PM2, or PS4 is counted.
- Requires VCEP-deferred counted evidence to have exact or partial VCEP scope match; out-of-scope VCEP labels fall back to generic overlays.
- Rejects non-ACMG outer skills as `overlay_applied` counted evidence sources.
- Keeps SNV/small-indel overlay thresholds unchanged and leaves SV/CNV as intake/routing only.

## Shortcut Cleanup and Documentation Deduplication: 2026-06-27

Changed files:

```text
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-rare-disease-diagnosis/TOOLS_REFERENCE.md
M skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
```

Behavior clarified:

- Removes residual wording that could be read as assigning BP7 or a benign classification directly from a low SpliceAI score. SpliceAI-only low-score evidence is prediction context unless a VCEP, RNA no-impact evidence, or another routed benign criterion supports counting.
- Converts ACMG common-pattern examples from direct final classifications into route-gated examples requiring route audit, Evidence Compatibility Resolution, and validator PASS before final output.
- Downgrades CADD and SAE/ESM mechanism examples in rare-disease diagnosis to prediction/mechanism context only; PP3/BP4 must still route through the calibrated overlay or VCEP.
- Rephrases the DisGeNET table in variant interpretation as gene-disease background and PP4 route context, not variant-level ACMG evidence.
- Does not change any evidence threshold, strength mapping, VCEP precedence, or final-combine rule.

## MCP Execute-Tool Gate Hardening: 2026-06-27

Changed files:

```text
M src/tooluniverse/acmg_gate_search.py
M src/tooluniverse/execute_function.py
M src/tooluniverse/tool_discovery_tools.py
M skills/tooluniverse-acmg-overlay-routing-core/QUICK_START.md
M skills/tooluniverse-acmg-overlay-routing-core/scripts/check_entrypoint_bypass_fixtures.py
```

Behavior clarified:

- Reuses the shared ACMG gate helper for direct tool execution results, so high-risk outputs include `acmg_gate_notice` and `recommended_front_door_tool`.
- Extends direct-output guard coverage to gnomAD, MaveDB/DMS, ClinGen/G2P, GeneReviews/MedGen-style disease-context tools, in addition to GeneBe, InterVar, ClinVar, SpliceAI, MyVariant, and VEP.
- Applies the same notice path to sync execution, async execution, cache hits, and the native `execute_tool` wrapper.
- Keeps these tools available for evidence retrieval; their outputs remain source leads, coverage hits, route triggers, or annotation inputs until an ACMG assessment bundle validates with `PASS`.
- Does not change any evidence threshold, strength mapping, VCEP precedence, database query logic, or final-combine rule.

## Structural Deduplication and Gate Notice Consolidation: 2026-06-27

Changed files:

```text
M skills/tooluniverse-acmg-variant-classification/SKILL.md
M skills/tooluniverse-acmg-overlay-routing-core/SKILL.md
M src/tooluniverse/acmg_gate_policy.py
M src/tooluniverse/genebe_tool.py
M src/tooluniverse/acmg_overlay_gate_tool.py
M src/tooluniverse/execute_function.py
M src/tooluniverse/tools/__init__.py
M src/tooluniverse/data/*_tools.json files carrying acmg_gate_notice
A tests/unit/test_acmg_gate_notice_and_wrappers.py
```

Behavior clarified:

- Keeps `tooluniverse-acmg-overlay-routing-core` as the portable routing/compliance contract and reduces duplicated hard-gate and compatibility-matrix prose in the main ACMG classification skill.
- Adds a Criterion Ownership Index for PS1 protein comparison, PS1 splicing comparison, BP1, BP2/BP5, and BP7/RNA no-impact routing.
- Consolidates ACMG gate and source-lead notices in `acmg_gate_policy.py`; GeneBe, ACMG overlay gate, and tool JSON configs now use the same canonical gate notice semantics.
- Fixes SDK typed-wrapper import drift for ClinVar/dbSNP generated modules and adds a regression import check for common variant wrappers.
- Makes the default persistent cache path fall back to a writable temporary directory when the default home cache directory is not writable and no explicit cache path or cache directory was configured.
- Adds focused unit tests for shared notices and wrapper argument forwarding for VariantValidator, CADD, SpliceAI, and common variant wrappers.
- Does not change evidence thresholds, strength mapping, VCEP precedence, validator hard-stop semantics, or final-combine rules.

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
