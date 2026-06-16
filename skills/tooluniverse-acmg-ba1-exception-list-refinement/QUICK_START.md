# Quick Start: BA1 Exception List Refinement

Use this overlay before applying BA1 stand-alone benign evidence from high population allele frequency.

Default behavior: `AF >0.05` is not enough by itself. Confirm dataset adequacy, observed allele count, general continental population status, exception-list status, and gene/variant-specific BA1 modifications first.

---

## Example 1: Ordinary High-Frequency Variant

**Scenario**: A variant has AF 0.08 in a qualifying general continental population, AN is greater than 2,000, and it is not on the BA1 exception list.

**Expected behavior**:

- Apply `BA1`.
- Do not evaluate PM2.
- Do not also apply BS1 for the same disease context.
- Report the population, AF, AC/AN, and exception-list check.

---

## Example 2: BA1 Exception-List Variant

**Scenario**: GJB2 NM_004004.5:c.109G>A (p.Val37Ile) has AF >0.05 in East Asian population data.

**Expected behavior**:

- Do not apply BA1.
- Report `No BA1 - exception list`.
- Evaluate all other criteria normally, without using BA1 or BS1 circularly.

---

## Example 3: High Frequency Only in a Founder Population

**Scenario**: A variant exceeds 0.05 only in a Finnish or other bottlenecked/founder population.

**Expected behavior**:

- Do not automatically apply BA1.
- Check whether the population dataset is suitable for stand-alone benign filtering and whether the variant is on the exception list.
- If dataset structure or effective population size is unclear, report `BA1_NotAssessed - population dataset not adequate`.
- Consider BS1 only through disease-specific frequency review.

---

## Example 4: Gene-Specific BA1 Threshold

**Scenario**: A VCEP or gene-disease expert panel defines a BA1 threshold lower than 0.05 based on prevalence, penetrance, and heterogeneity.

**Expected behavior**:

- Follow the VCEP/gene-specific threshold instead of the generic 0.05 threshold.
- Record `No BA1 - gene/variant-specific threshold` if the generic threshold would misclassify the variant.
- Route residual high-frequency evidence to `tooluniverse-acmg-benign-context-refinement` if BS1 is more appropriate.

---

## Example 5: Source Assertion Conflicts With BA1

**Scenario**: A variant exceeds 0.05 but also has a ClinVar Pathogenic assertion.

**Expected behavior**:

- Do not let the assertion alone block BA1.
- Use `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` to treat the assertion as a lead to primary evidence.
- If the variant is not on the exception list and no primary evidence or VCEP rule blocks BA1, BA1 may still apply.

---

## Minimal Report Block

```markdown
BA1 exception-list refinement:
- Variant: [HGVS / CA ID / ClinVar ID]
- Population AF: [population, AF, AC/AN]
- Dataset adequacy: [general continental / founder / unclear]
- Exception-list status: [matched / not matched]
- Gene-specific BA1 rule: [none / threshold / not assessed]
- Applied evidence: [BA1 / No BA1 - exception list / No BA1 - gene-specific rule / No BA1 - use BS1 review / BA1_NotAssessed]
```
