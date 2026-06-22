---
name: tooluniverse-acmg-overlay-routing-core
description: Shared routing and reporting core for ToolUniverse ACMG/AMP overlay skills. Use before evidence-specific overlays to standardize disease context, mechanism context, phenotype/source/literature intake, double-counting guards, output status values, and evidence-strength labels without changing criterion-specific rules.
disable-model-invocation: true
---

# ACMG Overlay Routing Core

This skill is a lightweight coordination layer for ToolUniverse ACMG/AMP overlay skills. It does not assign ACMG evidence by itself and does not change any criterion threshold, strength adjustment, or VCEP rule.

Use it to decide which context overlays must run before evidence-specific overlays, to keep output labels consistent, and to avoid circular or duplicated evidence use.

For portable use by external agents, this skill also includes a lightweight compliance contract:

- `overlay_registry.yaml`: machine-readable mapping from ACMG criterion groups to mandatory overlay skills, trigger policies, applies-when conditions, and baseline data-source categories.
- `overlay_route_contract.md`: human- and agent-readable rules for baseline route planning, discovery route expansion, mandatory overlay routing, and counted-evidence audit.
- `schemas/bundle_route_plan.schema.json`: JSON Schema for compact bundle-level execution planning before detailed route expansion.
- `schemas/route_plan.schema.json`: JSON Schema for pre-assignment route plans.
- `schemas/overlay_result.schema.json`: JSON Schema for overlay-like results.
- `schemas/route_audit.schema.json`: JSON Schema for final counted-evidence audits.
- `schemas/coverage_audit.schema.json`: JSON Schema for data-source coverage, query hits, and discovery routes not triggered because coverage found no signal.
- `schemas/evidence_compatibility.schema.json`: JSON Schema for final-combine evidence compatibility resolution.
- `evals/evals.json`: regression cases for detecting direct evidence assignment that bypasses overlays.

These files are a portable compliance layer, not a full runtime. They do not invoke tools, query databases, compute final ACMG classifications, or modify evidence thresholds. A future validator or harness may consume the same registry and schemas.

Apply the compliance layer in two route-planning passes followed by coverage, audit, and compatibility resolution:

1. `bundle_route_plan`: optionally emit compact bundle rows with `schemas/bundle_route_plan.schema.json` to decide which route groups need expansion.
2. `baseline_route_plan`: before evidence assignment, add every applicable `universal_baseline` route and every `variant_type_baseline` route whose `applies_when` condition matches the variant or context.
3. `coverage_audit`: query or explicitly mark unavailable the required baseline/discovery data-source categories, and record hits, no-hits, triggered routes, and routes not triggered.
4. `discovery_route_expansion`: after source, database, literature, clinical, or user-provided evidence is reviewed, append `evidence_discovery` routes for newly found candidate signals.
5. `counted_evidence_audit`: count only evidence with route outcome `overlay_applied` or `overlay_deferred_to_vcep`.
6. `evidence_compatibility_resolution`: before final ACMG qualitative or Bayesian combination, resolve incompatible, duplicated, capped, or context-split evidence.

Agents may plan these routes through the **Route Bundle Quick Planner** below. Bundle planning is an operational shortcut for efficiency and readability; it does not replace `overlay_registry.yaml`, route audit, coverage audit, evidence compatibility resolution, or evidence-specific overlay rules.

Missing an applicable baseline route is a compliance failure and requires `draft classification`. Missing a discovery route is acceptable only when no triggering evidence was found and the report includes coverage audit rows supporting that absence.

If a covered criterion is assigned strength without a valid overlay or VCEP trace, mark the report `draft classification` and move the item out of current counted evidence.

Every counted evidence item should report its guidance authority. Use one of these authority labels:

- `ClinGen/SVI primary`: a formal ClinGen SVI recommendation or ClinGen guidance document directly governs the evidence assignment.
- `ACMG/AMP baseline`: the assignment follows Richards et al. 2015 ACMG/AMP baseline language without a later generic ClinGen/SVI recommendation.
- `VCEP-specific`: a current disease- or gene-specific VCEP specification supersedes generic guidance.
- `practice/local refinement`: ACGS 2024, non-ClinGen literature, or local guardrail guidance is being used to operationalize an under-specified criterion.
- `source lead only`: a database, paper label, expert assertion, abstract-only source, or inaccessible source is used only to retrieve primary evidence and is not counted.

Practice/local refinements must be explicitly labeled in the output and must not be described as ClinGen/SVI primary guidance. VCEP-specific rules supersede generic overlays and practice/local refinements.

---

## External-Agent Compliance Rules

When this skill set is imported into another agent, do not treat the base ACMG workflow as a free-form checklist. The base workflow retrieves and organizes evidence; criterion-specific overlays assign refined evidence strengths.

For every ACMG criterion that could affect the final classification, the agent must record one of these routing outcomes:

- `overlay_applied`: the relevant overlay was used and assigned or withheld evidence.
- `overlay_not_applicable`: the overlay was not relevant to the variant class, disease mechanism, or evidence type.
- `overlay_not_assessed`: required evidence was unavailable and the missing fields are listed.
- `overlay_deferred_to_vcep`: a current VCEP or disease-specific specification superseded the generic overlay.

Do not assign refined evidence strength directly in the base workflow for criteria covered by overlays, including PM2, PP3/BP4, PS1/PM5, PM1/PP2/BP1, PS3/BS3, PS4, PP1/BS4/PP4, PM3, PS2/PM6, PM4/BP3, PVS1, BA1/BS1/BS2/BP2/BP5, PP5/BP6, and dominant-negative mechanism-sensitive criteria.

Final hard-stop audit: every counted evidence item in the final classification must have route outcome `overlay_applied` or `overlay_deferred_to_vcep`, and every applicable baseline route must appear in the route plan. If a counted item lacks one of those outcomes, or if an applicable baseline route is missing, the report must be labeled `draft classification` and the agent must not present a final ACMG classification until the missing route is corrected or the item is removed from counted evidence.

Separate source assertions from counted evidence. ClinVar, HGMD, LOVD, VCEP, laboratory reports, or a paper's ACMG labels belong in `source assertions` until their primary evidence is retrieved and routed. The final classification may be computed only from `current counted evidence`, not from source labels.

Source-label fan-out is controlled. A ClinVar, HGMD, LOVD, VCEP, laboratory, or paper classification label by itself routes to `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` only. Fan-out to PS3/BS3, PM1, PM2, PM5, PP3/BP4, PP1/BS4/PP4, PS4, PM3, or PS2/PM6 requires explicit ACMG criterion codes in the source, primary-evidence keywords, or retrievable primary evidence. Without those, keep the assertion as `source lead only`.

After the hard-stop audit passes, run Evidence Compatibility Resolution before any final combination. The compatibility gate outputs `current_counted_evidence_resolved`, `not_used_due_to_overlap`, `caps_applied`, `context_splits`, and `unresolved_conflicts`. Only `current_counted_evidence_resolved` may enter ACMG/AMP qualitative combination or `tooluniverse-acmg-bayesian-classification-framework`. If `unresolved_conflicts` is not empty, the report remains `draft classification` and no final posterior probability should be reported.

Route final evidence combination to `tooluniverse-acmg-bayesian-classification-framework` only after compatibility resolution passes. The Bayesian framework is a final combination layer only. It must not assign evidence strengths, and it must not receive unrouted, source-only, or unresolved-conflict evidence.

Treat these as routing failures unless corrected before final classification:

- Applying `PS3` or `BS3` from literature reports, HGMD/ClinVar labels, segregation, de novo observations, case enrichment, or another author's ACMG classification without reviewing the actual functional assay.
- Applying `PP3/BP4` from local predictor-majority reasoning across CADD, SIFT, PolyPhen, or similar tools, rather than the calibrated PP3/BP4 overlay or a current VCEP rule.
- Applying `PM5`, `PS1`, `PM1`, `PM2`, or `PS3` directly from a ClinVar, HGMD, LOVD, expert-panel, or paper classification label without extracting and routing the underlying primary evidence.
- Using manual summaries to replace failed ToolUniverse calls when the missing tool result is essential to a counted criterion.
- Counting abstract-only, unavailable full-text, unread supplementary material, or low-confidence figure/OCR evidence as a criterion when the criterion depends on details that are not actually accessible.

If an external agent cannot invoke a named overlay, it should still follow that overlay's SKILL.md instructions and explicitly state that the overlay logic was applied manually. If neither is possible, mark the criterion `not_assessed` instead of assigning strength.

---

## Routing Order

Apply this order before assigning final evidence codes:

1. **Variant normalization**
   - Normalize HGVS, transcript, consequence, genome build, and zygosity.
   - Use the base `tooluniverse-acmg-variant-classification` workflow and ToolUniverse variant annotation tools.

2. **Baseline route plan**
   - Use `overlay_registry.yaml` to add `universal_baseline` routes for germline assessment, including population frequency gates, disease/mechanism boundary, PVS1 applicability, and source assertion review when source assertions are available.
   - Add `variant_type_baseline` routes when `applies_when` matches the consequence. For missense variants, this normally includes PP3/BP4, PS1/PM5, PM1/PP2/BP1, and structured functional-discovery lookup such as MaveDB when available.
   - Run the PVS1 applicability gate for germline assessment even when the expected result for a non-LoF missense variant is `not_applicable`.
   - Include `enforcement_level`, `route_kind`, and `expected_default_status` in route-plan rows when structured output is available.
   - Do not wait for literature discovery before planning population, computational, comparison-variant, regional/mechanism, structured functional-discovery, or PVS1 applicability routes.

3. **Disease-entity boundary**
   - If the gene has multiple associated disorders, inheritance models, dosage states, phenotype spectra, or mechanisms, use `tooluniverse-acmg-multiple-disorder-context-refinement`.
   - This determines whether evidence can be aggregated or must be split by disease, inheritance, mechanism, or variant class.

4. **Mechanism boundary**
   - If LoF/haploinsufficiency, gain-of-function, dominant-negative, antimorphic, recessive LoF, altered-product, or mixed mechanism could change evidence use, use `tooluniverse-acmg-dominant-negative-mechanism-refinement`.
   - This step routes mechanism-sensitive criteria such as PVS1, PS1/PM5, PS3/BS3, PM1/PP2/BP1/PP3, PM4/BP3, PS4, PP1/BS4, PM3, and PS2/PM6.

5. **Clinical context intake**
   - First classify the needed context as patient-level phenotype, family/proband clinical-genotype context, literature/cohort case definition, or disease-context-only information.
   - Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` only when a criterion truly needs supplied or extracted phenotype, affected/unaffected status, disease specificity, diagnostic yield, phase, family data, de novo data, alternate diagnosis, or healthy-carrier context.
   - Do not route criteria to phenotype intake merely because they need disease prevalence, inheritance, penetrance, mechanism, or a literature-defined disease entity.
   - Use criterion-specific overlays for scoring after the required clinical fields are collected.

6. **Source, database, and literature coverage**
   - Use `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` when a secondary assertion is being considered.
   - For missense variants, check structured functional-discovery sources such as MaveDB when available. A hit routes to `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`; no hit is recorded in coverage audit and should not force a PS3/BS3 overlay result. Do not interpret the functional score directly as PS3/BS3.
   - Use `tooluniverse-literature-deep-research` and `tooluniverse-literature-figure-evidence-extraction` when primary evidence is embedded in papers, tables, supplements, pedigrees, traces, gels, blots, RT-PCR/minigene panels, or assay figures.
   - Append discovery routes only after evidence appears. Examples include PP1/BS4/PP4 after pedigree or cascade-screening evidence, PS4 after cohort or enrichment evidence, PS2/PM6 after de novo/trio evidence, and PM3 after biallelic or in-trans evidence.
   - Emit coverage audit rows compatible with `schemas/coverage_audit.schema.json` for population, computational, source assertion, literature, functional database, disease context, mechanism context, and clinical context coverage when those categories determine whether routes are mandatory.

7. **Evidence-specific overlay**
   - Apply the relevant ACMG overlay for the criterion being assessed.
   - VCEP or current disease-specific specifications override generic overlay guidance.

8. **Evidence compatibility resolution**
   - Use this routing core as the final-combine compatibility gate after the route audit passes.
   - Resolve hard incompatibilities, same-primary-evidence conflicts, mechanism mismatches, context splits, and caps before final combination.
   - Output `current_counted_evidence_resolved`, `not_used_due_to_overlap`, `caps_applied`, `context_splits`, and `unresolved_conflicts` using `schemas/evidence_compatibility.schema.json`.
   - If unresolved conflicts remain, label the report `draft classification` and do not run final qualitative or Bayesian combination.

9. **Final Bayesian combination**
   - If all counted evidence has route outcome `overlay_applied` or `overlay_deferred_to_vcep`, and compatibility resolution has produced `current_counted_evidence_resolved` with no unresolved conflicts, use `tooluniverse-acmg-bayesian-classification-framework` to convert resolved counted strengths to Tavtigian 2018 Bayesian points, OddsPath, and posterior probability.
   - If BA1 applies, stop before Bayesian combination and report Benign by BA1 stand-alone.
   - If a VCEP defines a different combining framework, follow the VCEP and report the generic Bayesian result only as optional context if appropriate.

---

## Route Bundle Quick Planner

Use route bundles to keep variant interpretation efficient. A bundle is a compact plan row that expands to the required overlays and coverage checks. It is acceptable to report bundle-level planning first, then expand only triggered bundles into detailed route-plan rows.

| Bundle | Trigger | Required overlays / checks | Evidence consumed | Output artifact | Stop condition |
| --- | --- | --- | --- | --- | --- |
| `baseline_context_bundle` | Any germline ACMG assessment | `tooluniverse-acmg-multiple-disorder-context-refinement`; `tooluniverse-acmg-dominant-negative-mechanism-refinement` when mechanism-sensitive evidence is possible | Disease, inheritance, mechanism, transcript, gene-disease validity, dosage context | Disease/mechanism context and context splits | Target disease or mechanism cannot be resolved; report `not_assessed` for mechanism-sensitive criteria |
| `population_frequency_bundle` | Any germline ACMG assessment | `tooluniverse-acmg-ba1-exception-list-refinement`; `tooluniverse-acmg-pm2-absence-rarity-refinement`; `tooluniverse-acmg-benign-context-refinement` when BA1/BS1/BS2/BP2/BP5 may apply | gnomAD/ClinVar frequency, ancestry, disease prevalence/penetrance, coverage adequacy | BA1/BS1/BS2/PM2/BP2/BP5 route outcomes | Valid BA1 short-circuits PM2/BS1 for the same context |
| `consequence_lof_bundle` | Nonsense, frameshift, canonical splice, start-loss, exon-level CNV, whole-gene deletion, or other LoF-like consequence | `tooluniverse-acmg-pvs1-lof-decision-tree-refinement`; route CNV/SV evidence through `tooluniverse-structural-variant-analysis` as intake only | Consequence, transcript structure, NMD branch, rescue transcript, LoF/HI mechanism | Baseline PVS1 applicability and strength outcome | LoF/HI mechanism unsupported, rescue transcript preserves relevant function, or consequence is not LoF-like |
| `splice_bundle` | Canonical splice, near-splice, deep intronic splice prediction, RNA assay, published RNA/splicing evidence | `tooluniverse-acmg-pvs1-splicing-refinement` only for RNA assay or observed transcript consequence; `tooluniverse-acmg-ps1-splicing-similarity-refinement` for independent same-event comparison evidence | SpliceAI and similar predictions, RNA assay, transcript event, comparison variant | Splicing prediction context, PVS1/RNA or BP7/RNA result, PS1-splicing result | SpliceAI-only evidence does not enter RNA-assay PVS1; route prediction-only evidence separately |
| `missense_bundle` | Missense or amino-acid substitution consequence | `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement`; `tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement`; `tooluniverse-acmg-pm1-regional-missense-constraint-refinement`; structured functional discovery such as MaveDB | Calibrated predictor, same residue/amino acid comparison, regional constraint, hotspot/domain, structured functional hit | PP3/BP4, PS1/PM5, PM1/PP2/BP1, PS3/BS3 discovery routes | No calibrated predictor/VCEP threshold, source-only comparison, broad domain only, or no structured functional hit |
| `protein_length_bundle` | In-frame insertion/deletion, stop-loss, altered product, repeat-region indel | `tooluniverse-acmg-pm4-bp3-protein-length-refinement`; mechanism overlay when altered-product or dominant-negative context matters | Protein length, repeat/low-complexity region, critical domain/residue, stop-loss/nonstop decay context | PM4/BP3 route outcome or PVS1/PM4 routing decision | Same consequence already consumed by PVS1, nonfunctional repeat supports BP3, or altered-product mechanism unsupported |
| `clinical_observation_bundle` | De novo, segregation, affected/unaffected relatives, biallelic phase, healthy carriers, alternate diagnosis, phenotype specificity | `tooluniverse-acmg-de-novo-evidence-refinement`; `tooluniverse-acmg-pp1-segregation-refinement`; `tooluniverse-acmg-pm3-in-trans-refinement`; phenotype-dependent intake as needed | Trio/parentage, pedigree, probands, phase, affected status, phenotype, alternate diagnosis | PS2/PM6, PP1/BS4/PP4, PM3, BS2/BP2/BP5 route outcomes | Missing clinical fields; same individual would be reused across incompatible criteria |
| `literature_functional_bundle` | Functional assay, case-control/cohort/meta-analysis, case series, figure/table/supplement evidence, paper ACMG labels | `tooluniverse-literature-deep-research`; `tooluniverse-literature-figure-evidence-extraction`; `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`; `tooluniverse-acmg-ps4-case-enrichment-refinement`; `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` for source labels | Full text, supplements, figures, assay design, controls, cases/controls, OR/CI, source assertions | Literature provenance, PS3/BS3 or PS4 route outcomes, source leads | Full text/supplement unavailable after retrieval attempt, abstract-only details, low-confidence figure evidence, or source labels without primary evidence |
| `cnv_sv_bundle` | Deletion, duplication, inversion, translocation, complex rearrangement, exon-level event, whole-gene CNV | `tooluniverse-structural-variant-analysis` for SV/CNV intake; final ACMG evidence through PVS1, PM4/BP3, PM2/BA1/BS1, PS2/PM6, PS4, PP1/BS4/PP4, and compatibility resolution as applicable | Coordinates, SV type, reciprocal overlap, gene content, dosage, breakpoint, inheritance, population SVs | SV evidence summary and ACMG route candidates | Do not produce standalone germline ACMG final classification from this bundle alone |
| `final_combine_bundle` | After overlay route audit passes | Evidence Compatibility Resolution; `tooluniverse-acmg-bayesian-classification-framework` after resolved evidence set | Routed counted evidence and source leads | `current_counted_evidence_resolved`, qualitative ACMG result, Bayesian points/posterior | Missing route audit, missing compatibility artifact, unresolved conflicts, valid BA1 stand-alone gate |

Minimum bundle-plan output:

```markdown
Bundle route plan:
| Bundle | Trigger found? | Required overlays/checks | Coverage required | Status | Reason |
| --- | --- | --- | --- | --- | --- |
```

Use detailed route-plan rows compatible with `schemas/route_plan.schema.json` for every bundle that is triggered, counted, or needed to justify `not_assessed` / `not_applicable`.

Structured bundle-plan output should be compatible with `schemas/bundle_route_plan.schema.json`. Bundle rows may list non-ACMG intake steps in `required_checks`, such as `tooluniverse-structural-variant-analysis` for `cnv_sv_bundle`. Counted evidence must still come from expanded ACMG overlay route rows or VCEP-specific route outcomes, never from the bundle row itself.

---

## Canonical Status Values

Use these status values in reports and structured summaries:

| Status | Meaning |
| --- | --- |
| `applied` | A criterion or strength was assigned. |
| `no_evidence` | The criterion was considered but available evidence does not support applying it. |
| `not_assessed` | Required information is missing or unavailable. Ask for targeted fields when user-provided clinical data are needed. |
| `not_applicable` | The criterion does not apply to the variant class, disease mechanism, or disease context. |
| `not_used` | Evidence is recorded as a lead or context but is intentionally not counted. |

Do not use free-text missing-data phrases as the only status in structured output. Put the explanation in `reason` and use the controlled `status` values.

---

## Canonical Output Fields

Each overlay should be able to report this minimal block:

```markdown
ACMG overlay result:
- overlay: [skill name]
- criterion: [ACMG code or context gate]
- applied_evidence: [evidence label or none]
- status: [applied / no_evidence / not_assessed / not_applicable / not_used]
- guidance_authority: [ClinGen/SVI primary / ACMG/AMP baseline / VCEP-specific / practice/local refinement / source lead only]
- reason: [short evidence-specific rationale]
- consumed_evidence: [data sources or evidence already used]
- routed_to: [next overlay if applicable]
```

Evidence-specific overlays may add fields needed for their criterion, such as points, OddsPath, phase status, assay validity, transcript consequence, or case-count details.

For final ACMG reports, include an audit table with these fields for each potentially counted item:

```markdown
ACMG route audit:
| Criterion | Proposed evidence | Route outcome | Guidance authority | Overlay or VCEP source | Counted? | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| [code] | [candidate label] | [overlay_applied / overlay_deferred_to_vcep / overlay_not_assessed / overlay_not_applicable] | [ClinGen/SVI primary / ACMG/AMP baseline / VCEP-specific / practice/local refinement / source lead only] | [skill or VCEP] | [yes/no] | [one-line rationale] |
```

Allowed route outcomes are `overlay_applied`, `overlay_not_applicable`, `overlay_not_assessed`, and `overlay_deferred_to_vcep`. Only `overlay_applied` and `overlay_deferred_to_vcep` may be counted.

For final-combine compatibility, include this block before qualitative or Bayesian classification:

```markdown
Evidence compatibility resolution:
- current_counted_evidence_resolved: [criteria retained for final combination]
- not_used_due_to_overlap: [criteria removed because another criterion consumed the evidence]
- caps_applied: [PM1+PP3, PP1+PP4, PM3 homozygous, PS2/PM6 heterogeneity, or VCEP caps]
- context_splits: [disease / inheritance / mechanism / transcript splits]
- unresolved_conflicts: [conflicts that block final classification]

| Conflict group | Evidence items | Conflict type | Resolution | Kept evidence | Removed/capped evidence | Status | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
```

Use `schemas/evidence_compatibility.schema.json` for machine-checkable output. If a conflict cannot be resolved, set `resolution: unresolved_draft_only`, leave the affected item out of `current_counted_evidence_resolved`, and keep `classification_status: draft classification`.

---

## Strength Labels

Use these strength terms in evidence labels:

- `Supporting`
- `Moderate`
- `Strong`
- `VeryStrong`

Examples:

- `PM2_Supporting`
- `PS2_VeryStrong`
- `PM3_Strong`
- `BP4_Moderate`

Do not introduce underscore-separated variants of very-strong strength names. For backward-compatible display text, keep established labels such as `PVS1_N/A` in narrative output, but represent them structurally as `status: not_applicable` when possible.

---

## Boundary Rules

- **BA1 and benign context**: BA1 exception-list review is the BA1 stand-alone gate. If BA1 is valid, do not use PM2 or BS1 for the same disease context. If BA1 is blocked but frequency remains too high, route to benign-context BS1 review.
- **Phenotype and PP1/BS4/PP4**: phenotype-dependent refinement collects clinical context. PP1 segregation refinement performs PP1/BS4/PP4 combined scoring, diagnostic-yield conversion, evidence apportionment, and the +5.0 cap.
- **PVS1 and splicing**: baseline PVS1 uses `tooluniverse-acmg-pvs1-lof-decision-tree-refinement`. RNA/Walker evidence uses `tooluniverse-acmg-pvs1-splicing-refinement` after the baseline branch is identified.
- **PS1-splicing**: `tooluniverse-acmg-ps1-splicing-similarity-refinement` is comparison-variant evidence, not direct PVS1 evidence.
- **PP5/BP6**: reputable-source assertions are source leads by default. Do not count PP5/BP6 unless a current VCEP or explicitly approved local legacy policy requires it.
- **Double counting**: if the same primary evidence supports multiple possible criteria, choose the criterion-specific path and record the other criteria as `not_used` or `no_evidence` with a reason.
- **Literature provenance**: evidence from papers must state whether the relevant full text, supplement, and figure/table content were read. Abstract-only or inaccessible papers are source leads, not counted evidence, unless a VCEP explicitly allows abstract-level use.
- **Figure confidence**: low-confidence or `not_interpretable` visual extraction cannot by itself upgrade evidence strength. Route it as a lead and request the source image/PDF or corroborating text.
- **Bayesian combination**: Tavtigian-style points are assigned only after overlays have assigned evidence strengths. Do not use points to promote candidate evidence into counted evidence.

### Final-Combine Compatibility Matrix

Apply these generic choices unless a current VCEP explicitly permits a different handling:

- **Frequency**: valid BA1 excludes PM2 and BS1 for the same disease context. BS1 or BS2 excludes PM2 for the same frequency or healthy-carrier rationale.
- **Disease/mechanism context**: do not combine evidence across mutually exclusive disorders, inheritance models, mechanisms, or transcript contexts. Use `split_by_context` when multiple-disorder refinement requires separate classifications.
- **PVS1 and splicing**: canonical splice PVS1 excludes same-mechanism PP3. `PVS1_Strength (RNA)` excludes PS3 and same-mechanism PP3/BP4. `BP7_Strong (RNA)` excludes BS3 and contradicted PS1-splicing. Direct RNA evidence supersedes predicted same-event PS1-splicing unless independent comparison evidence remains.
- **PVS1, PM4, and CNV/SV**: PVS1 and PM4 cannot use the same protein-length or LoF consequence. Whole-gene deletion should not be counted both as PVS1 and separate CNV dosage evidence unless the downstream framework explicitly permits the split. PVS1 is not countable when only dominant-negative or gain-of-function mechanism is established.
- **Functional and computational evidence**: PS3/BS3 excludes the same assay, DMS, or MAVE source as PP3/BP4. Multiple functional assays are not stacked unless VCEP, formal OddsPath, or a validated combination rule permits it. Comparable conflicting assays yield no PS3/BS3.
- **Missense regional and prediction evidence**: PP2 and BP1 are mutually exclusive. PM1 versus PP2 follows the PM1 overlay priority. PM1 plus PP3 is capped at Strong contribution. PM1, PM5, and PM4 cannot reuse the same residue/domain rationale unless evidence sources are independent.
- **Protein comparison**: PS1 and PM5 are mutually exclusive for the same comparison relationship. Protein-level PS1/PM5 cannot use comparison variants whose pathogenicity is actually splicing, DNA-level, RNA-level, or another non-amino-acid mechanism.
- **Clinical observations**: the same proband or individual cannot support PS4 plus PM3, PS2/PM6, PP1, or PP4. Recessive biallelic probands route to PM3; de novo observations route to PS2/PM6; family segregation routes to PP1/BS4.
- **Phenotype and segregation**: PP1/PP4 combined evidence is capped at +5.0. Do not combine Biesecker 2024 points with informative-meioses fallback for the same pedigree. Phenotype specificity consumed by PS2/PM6 or a VCEP PS4 rule cannot also become PP4 unless explicitly allowed.
- **PM3 and de novo caps**: block PM3 circularity; de-duplicate repeated or related probands; apply the default PM3 homozygous cap of 1.0 unless VCEP says otherwise; apply the PS2/PM6 high-genetic-heterogeneity cap of 1 point.
- **Source and provenance**: PP5/BP6 source labels are not counted when underlying primary evidence is counted. Abstract-only evidence, inaccessible full text, unread supplements, and low-confidence figure/OCR evidence cannot enter `current_counted_evidence_resolved`.

---

## Clinical Context Dependency Classes

Use these classes before asking the user for phenotype. Patient-level phenotype is requested only when the criterion cannot be scored from public literature, cohort metadata, or disease-context resources.

| Class | Meaning | Typical criteria |
| --- | --- | --- |
| `user_patient_phenotype_required` | The current patient's or family's phenotype, affected/unaffected status, age, alternate diagnosis, or clinical evaluation is needed and is not available from a cited source. Ask the user for targeted fields. | PP4 for the current case, BP5, BS2, BP2 when alternate diagnosis or phenotype explanation is needed, PS2/PM6 for a user-reported de novo event, PP1/BS4 for a user-supplied family, PM3 for a user-supplied affected proband. |
| `literature_case_context_required` | Case phenotype, affected status, family data, phase, or disease ascertainment may be extracted from papers, tables, supplements, pedigrees, or databases. Ask the user only if extraction fails or the source is unavailable. | Published PS2/PM6, PM3, PP1/BS4, PP4, rare-disease PS4 affected-case counting, pedigree-based evidence. |
| `literature_or_cohort_case_definition_required` | Formal study-level case definition, disease ascertainment, controls, ancestry handling, and statistics are needed. Patient-level phenotype from the user is not required when the study definition is sufficient. | Formal PS4 case-control, cohort, or meta-analysis evidence. |
| `disease_context_only` | Disease entity, inheritance, prevalence, penetrance, mechanism, transcript, or threshold context is needed, but not a patient phenotype. Retrieve from ClinGen, GenCC, MONDO/MedGen, GeneReviews, VCEP guidance, population data, or literature. | BA1/BS1/PM2 frequency thresholds, PVS1 LoF mechanism gate, PM1/PP2/BP1 regional or mechanism context, PP3/BP4 prediction context, PM4/BP3 protein-region context, PS1/PM5 comparison-variant context. |

If a criterion falls into more than one class, use the narrowest missing-information request. For example, formal PS4 should ask for the case-control study details, not the current patient's phenotype; rare-disease PS4 case counting should ask for affected-case phenotype and unrelatedness only when those facts are missing from the publication or database.

---

## Confidentiality, Transparency, and Human Review

Use these safeguards whenever patient-level data, unpublished deliberations, draft specifications, or meeting-derived evidence are involved. These safeguards are based on ClinGen's AI note-taking policy v1.0 and are governance requirements, not ACMG evidence rules.

- **De-identify inputs**: do not send names, dates of birth, medical record numbers, direct contact information, or other patient-identifiable data to unsecured tools. Use de-identified phenotype, genotype, phase, and family-relationship descriptors whenever possible.
- **Separate public from restricted evidence**: published PMIDs, public ClinGen guidance, ClinVar/gnomAD/UniProt/OMIM records, and public supplements can be cited directly. Unpublished VCEP drafts, private meeting notes, internal deliberations, and confidential patient-level material should be summarized only when the user has permission and should not be redistributed as public guidance.
- **Disclose AI assistance**: if the output is used as meeting notes, a curation draft, or a clinical interpretation draft, include an AI-assistance statement such as: "AI tools were used to assist evidence retrieval and drafting; the final interpretation requires review and approval by the designated human curator or qualified professional."
- **Require human oversight**: do not present ToolUniverse overlay output as a final ClinGen/VCEP decision, clinical laboratory classification, or medical recommendation without qualified human review.
- **Avoid unattended automation**: do not use this workflow to automatically publish, distribute, or finalize notes, evidence tables, or variant classifications without human review.

---

## Common Routing Map

| Situation | Route |
| --- | --- |
| Multiple gene-associated disorders or mechanisms | Multiple-disorder context, then mechanism overlay if needed. |
| Possible dominant-negative or altered-product mechanism | Mechanism overlay before evidence-specific criteria. |
| Missing patient phenotype, family, de novo, phase, healthy-carrier, or alternate-diagnosis context | Phenotype-dependent intake before criterion scoring. |
| Formal PS4 case-control, cohort, or meta-analysis evidence | PS4 overlay; phenotype-dependent intake only if the study case definition or disease ascertainment is missing or ambiguous. |
| Disease prevalence, penetrance, inheritance, mechanism, transcript, or threshold context only | Disease-context retrieval and the evidence-specific overlay; do not request patient phenotype solely for these inputs. |
| Secondary source assertion only | PP5/BP6 source refinement, then retrieve primary evidence. |
| Literature evidence in figures or supplements | Literature deep research plus figure evidence extraction. |
| Baseline LoF PVS1 | PVS1 LoF decision-tree overlay. |
| RNA/splicing PVS1 or BP7 | PVS1 splicing overlay after baseline context. |
| Same predicted splicing event as known P/LP variant | PS1-splicing overlay, keeping evidence independent from direct RNA evidence. |
| Final counted-evidence compatibility | Evidence compatibility resolution in this routing core after the route audit passes. |
| Final counted-evidence combination and posterior probability | Bayesian classification framework after compatibility resolution passes. |

---

## Limitations

- This routing core does not replace any evidence-specific overlay.
- It does not decide final pathogenicity.
- It should not be used to override current VCEP specifications.
- It is intentionally documentation-only and creates no new ToolUniverse MCP tool.
