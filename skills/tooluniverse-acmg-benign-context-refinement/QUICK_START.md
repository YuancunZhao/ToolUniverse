# Quick Start: Benign-Context Refinement

Use this overlay for BA1, BS1, BS2, BP2, and BP5 when benign evidence depends on disease frequency, penetrance, healthy observations, phase, or alternate molecular diagnosis.

---

## Example 1: High AF Exceeds Disease Threshold

**Scenario**: A variant exceeds a disease-specific BA1 or BS1 threshold.

**Expected behavior**:

- Before applying BA1, use `tooluniverse-acmg-ba1-exception-list-refinement`.
- Apply BA1 only if the Ghosh 2018 BA1 definition is met and no exception applies.
- Apply BS1/BS1_Strong according to the threshold source when BA1 is not valid but frequency is still too high for the disease.
- Do not apply PM2.
- Report maximum ancestry AF, not global AF alone.

---

## Example 1A: BA1 Exception-List Variant

**Scenario**: A variant has AF >0.05 but matches the ClinGen BA1 exception list, such as GJB2 c.109G>A (p.Val37Ile).

**Expected behavior**:

- Do not apply BA1.
- Report `No BA1 - exception list`.
- Evaluate other ACMG criteria normally without using BA1 or BS1 circularly.

---

## Example 1B: High AF Only in Founder Population

**Scenario**: A variant exceeds 0.05 only in a Finnish, Ashkenazi Jewish, or other bottlenecked/founder population.

**Expected behavior**:

- Do not automatically apply BA1.
- Use `tooluniverse-acmg-ba1-exception-list-refinement` to assess dataset adequacy, observed allele count, and exception-list status.
- If dataset structure is unclear, report `BA1_NotAssessed - population dataset not adequate`.

---

## Example 2: Healthy Adult Observations

**Scenario**: Two well-phenotyped healthy adults carry a variant for a fully penetrant early-onset dominant disorder.

**Expected behavior**:

- Apply BS2 when age, phenotype evaluation, and penetrance make pathogenicity incompatible.
- If age or phenotype evaluation is missing, mark BS2 not assessable.

---

## Example 3: Alternate Diagnosis Explains Phenotype

**Scenario**: The proband has another P/LP variant that explains all key clinical features.

**Expected behavior**:

- Apply BP5 only if the alternate diagnosis explains the phenotype.
- Do not apply BP5 if a blended phenotype remains plausible.

---

## Example 4: Variant in Cis With Pathogenic Variant

**Scenario**: The variant under assessment is in cis with a known pathogenic variant.

**Expected behavior**:

- Consider BP2 if phase is confirmed and the inheritance context supports benign interpretation.
- Do not apply BP2 if phase is unknown.

---

## Minimal Report Block

```markdown
Benign-context refinement:
- Disease context: [disease, inheritance, penetrance]
- Population threshold: [BA1/BS1 source and BA1 exception-list result]
- Healthy observations: [summary]
- Phase/alternate diagnosis: [summary]
- Applied evidence: [BA1 / BS1 / BS2 / BP2 / BP5 / No evidence / Not Assessed]
```
