# Quick Start: Phenotype-Dependent Evidence Refinement

Use this overlay when ACMG evidence cannot be assessed without patient phenotype, affected status, unaffected status, disease specificity, or alternate-diagnosis context.

---

## Example 1: PP4 Without Phenotype

**Scenario**: A variant is in a gene associated with a highly recognizable syndrome, but the user provides only the variant and gene.

**Expected behavior**:

- Do not apply PP4.
- Mark `PP4: Not Assessed - phenotype required`.
- Ask for proband phenotype, HPO terms, suspected disease, age at onset, and alternate diagnoses.

---

## Example 2: PP4 With Specific Phenotype

**Scenario**: The user provides HPO terms and a suspected disease that is highly specific for the gene-disease relationship.

**Expected behavior**:

- Normalize disease and phenotype terms where possible.
- Confirm gene-disease validity and phenotype specificity.
- Apply PP4 only if the phenotype is sufficiently specific or VCEP rules are met.

---

## Example 3: Segregation Without Affected Status

**Scenario**: A family table lists genotypes but does not say who is affected or their clinical features.

**Expected behavior**:

- Do not score PP1 or BS4.
- Ask for affected/unaffected status, ages, phenotype details, penetrance assumptions, and possible phenocopy.
- Then route to `tooluniverse-acmg-pp1-segregation-refinement`.

---

## Example 4: PM3 Without Proband Phenotype

**Scenario**: Two variants are reported in trans, but the patient's phenotype is not supplied.

**Expected behavior**:

- Do not score PM3 until the proband is confirmed affected with the relevant recessive disease context.
- Ask for proband phenotype, suspected diagnosis, phase, and both variant details.
- Then route to `tooluniverse-acmg-pm3-in-trans-refinement`.

---

## Example 5: BP5 With Alternate Diagnosis

**Scenario**: The user reports a pathogenic variant in another gene.

**Expected behavior**:

- Do not apply BP5 unless the alternate molecular diagnosis explains the patient's phenotype.
- Ask for patient phenotype and the alternate diagnosis if not supplied.

---

## Minimal Missing-Information Prompt

```markdown
The following ACMG criteria require phenotype or affected-status information and cannot be assessed from variant annotation alone:
- [criterion]: [reason]

Please provide: proband phenotype or HPO terms, suspected disease, age at onset/current age, family affected/unaffected status if relevant, and any known alternate molecular diagnosis.
```

---

## Minimal Report Block

```markdown
Phenotype-dependent evidence refinement:
- Supplied phenotype: [summary / not provided]
- Gene-disease context: [summary]
- Phenotype match: [highly specific / compatible / nonspecific / mismatched / not assessable]
- Criteria affected: [PP4/PS4/PP1/BS4/PM3/BP5/BS2/PS2/PM6]
- Applied evidence: [criterion / Not Assessed - phenotype required]
- Follow-up request: [targeted missing fields]
```
