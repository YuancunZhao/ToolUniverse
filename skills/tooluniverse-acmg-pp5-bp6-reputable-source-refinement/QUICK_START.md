# Quick Start: PP5/BP6 Reputable-Source Refinement

Use this overlay when a variant classification workflow is considering PP5 or BP6 from a secondary classification source.

Default behavior: do not count PP5 or BP6. Use the source assertion as a lead to retrieve primary evidence, then route the primary evidence to the relevant ACMG criteria.

---

## Example 1: ClinVar Pathogenic Assertion Without Primary Review

**Scenario**: ClinVar includes a Pathogenic or Likely Pathogenic assertion, but the current workflow has not reviewed the underlying evidence.

**Expected behavior**:

- Do not apply `PP5`.
- Record the ClinVar assertion, review status, submitter, date, and condition.
- Retrieve submitter criteria, cited publications, or evidence summaries if available.
- Route the underlying evidence to criteria such as PVS1, PS3, PS4, PM3, PP1, PS1/PM5, or PP3/BP4.
- If no primary evidence is available, report `PP5_NotAssessed - primary evidence required`.

---

## Example 2: Expert Panel or VCEP Classification

**Scenario**: A ClinGen expert panel or VCEP classifies the variant as Pathogenic.

**Expected behavior**:

- Do not add PP5 by default.
- Use the expert assertion to locate disease-specific rules, curated evidence, and criteria already applied.
- Apply the underlying evidence directly only if it is available and appropriate for the current disease context.
- Do not double count the expert-panel label and the underlying criteria.

---

## Example 3: Laboratory Report Without Underlying Evidence

**Scenario**: A clinical report says the variant is Pathogenic, but the report does not provide case data, segregation, functional assay, population data, criteria, or citations.

**Expected behavior**:

- Do not apply `PP5`.
- Treat the report as a non-counted lead.
- Ask for the supporting evidence or original report details.
- Use `PP5_NotAssessed - primary evidence required`.

---

## Example 4: Benign Assertion Without Primary Evidence

**Scenario**: A reputable source reports Benign or Likely Benign, but the current workflow cannot inspect the population frequency, healthy-observation, functional, or other benign evidence.

**Expected behavior**:

- Do not apply `BP6`.
- Retrieve underlying evidence and route it to BA1, BS1, BS2, BS3, BS4, BP2, BP4, BP5, BP7, or another appropriate benign criterion.
- If primary evidence is unavailable, report `BP6_NotAssessed - primary evidence required`.

---

## Example 5: Source Assertion Based on Functional Evidence Already Counted

**Scenario**: A database states Pathogenic, and its cited evidence is the same functional assay being evaluated as PS3.

**Expected behavior**:

- Apply PS3/BS3 only through `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`.
- Do not also apply PP5/BP6 from the database label.
- State that the reputable-source classification was not counted separately to avoid double counting.

---

## Minimal Report Block

```markdown
PP5/BP6 reputable-source refinement:
- Variant: [HGVS / ClinVar Variation ID / CA ID]
- Source assertion: [source, classification, review status, date]
- Primary evidence available: [yes / partial / no]
- Routed underlying criteria: [criteria or none]
- Applied PP5/BP6 evidence: [No PP5 / No BP6 / PP5_NotUsed / BP6_NotUsed / Not Assessed - primary evidence required]
- Rationale: [why PP5/BP6 was not counted]
```
