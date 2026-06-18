---
name: tooluniverse-acmg-overlay-routing-core
description: Shared routing and reporting core for ToolUniverse ACMG/AMP overlay skills. Use before evidence-specific overlays to standardize disease context, mechanism context, phenotype/source/literature intake, double-counting guards, output status values, and evidence-strength labels without changing criterion-specific rules.
disable-model-invocation: true
---

# ACMG Overlay Routing Core

This skill is a lightweight coordination layer for ToolUniverse ACMG/AMP overlay skills. It does not assign ACMG evidence by itself and does not change any criterion threshold, strength adjustment, or VCEP rule.

Use it to decide which context overlays must run before evidence-specific overlays, to keep output labels consistent, and to avoid circular or duplicated evidence use.

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

Final hard-stop audit: every counted evidence item in the final classification must have route outcome `overlay_applied` or `overlay_deferred_to_vcep`. If any counted item lacks one of those outcomes, the report must be labeled `draft classification` and the agent must not present a final ACMG classification until the missing route is corrected or the item is removed from counted evidence.

Separate source assertions from counted evidence. ClinVar, HGMD, LOVD, VCEP, laboratory reports, or a paper's ACMG labels belong in `source assertions` until their primary evidence is retrieved and routed. The final classification may be computed only from `current counted evidence`, not from source labels.

After the hard-stop audit passes, route final evidence combination to `tooluniverse-acmg-bayesian-classification-framework` when posterior probability, Bayesian points, OddsPath, or standardized phase reporting is requested. The Bayesian framework is a final combination layer only. It must not assign evidence strengths, and it must not receive unrouted or source-only evidence.

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

2. **Disease-entity boundary**
   - If the gene has multiple associated disorders, inheritance models, dosage states, phenotype spectra, or mechanisms, use `tooluniverse-acmg-multiple-disorder-context-refinement`.
   - This determines whether evidence can be aggregated or must be split by disease, inheritance, mechanism, or variant class.

3. **Mechanism boundary**
   - If LoF/haploinsufficiency, gain-of-function, dominant-negative, antimorphic, recessive LoF, altered-product, or mixed mechanism could change evidence use, use `tooluniverse-acmg-dominant-negative-mechanism-refinement`.
   - This step routes mechanism-sensitive criteria such as PVS1, PS1/PM5, PS3/BS3, PM1/PP2/BP1/PP3, PM4/BP3, PS4, PP1/BS4, PM3, and PS2/PM6.

4. **Clinical context intake**
   - First classify the needed context as patient-level phenotype, family/proband clinical-genotype context, literature/cohort case definition, or disease-context-only information.
   - Use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` only when a criterion truly needs supplied or extracted phenotype, affected/unaffected status, disease specificity, diagnostic yield, phase, family data, de novo data, alternate diagnosis, or healthy-carrier context.
   - Do not route criteria to phenotype intake merely because they need disease prevalence, inheritance, penetrance, mechanism, or a literature-defined disease entity.
   - Use criterion-specific overlays for scoring after the required clinical fields are collected.

5. **Source and literature intake**
   - Use `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` when a secondary assertion is being considered.
   - Use `tooluniverse-literature-deep-research` and `tooluniverse-literature-figure-evidence-extraction` when primary evidence is embedded in papers, tables, supplements, pedigrees, traces, gels, blots, RT-PCR/minigene panels, or assay figures.

6. **Evidence-specific overlay**
   - Apply the relevant ACMG overlay for the criterion being assessed.
   - VCEP or current disease-specific specifications override generic overlay guidance.

7. **Final Bayesian combination**
   - If all counted evidence has route outcome `overlay_applied` or `overlay_deferred_to_vcep`, use `tooluniverse-acmg-bayesian-classification-framework` to convert counted strengths to Tavtigian 2018 Bayesian points, OddsPath, and posterior probability.
   - If BA1 applies, stop before Bayesian combination and report Benign by BA1 stand-alone.
   - If a VCEP defines a different combining framework, follow the VCEP and report the generic Bayesian result only as optional context if appropriate.

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
| Final counted-evidence combination and posterior probability | Bayesian classification framework after the hard-stop audit passes. |

---

## Limitations

- This routing core does not replace any evidence-specific overlay.
- It does not decide final pathogenicity.
- It should not be used to override current VCEP specifications.
- It is intentionally documentation-only and creates no new ToolUniverse MCP tool.
