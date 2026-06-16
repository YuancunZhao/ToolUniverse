# Quick Start: Multiple-Disorder Context Refinement

Use this overlay before ACMG evidence assignment when one gene has multiple disease associations, inheritance patterns, dosage states, phenotypic spectra, or mechanisms.

## Minimal Workflow

1. Normalize the variant and consequence.
2. Identify the target disease/entity and inheritance.
3. Retrieve all relevant gene-disease validity and dosage sensitivity curations.
4. Determine whether the gene-disease entities should be aggregated or split.
5. Route mechanism-sensitive evidence to the appropriate ACMG overlay.
6. Report disease-specific classification boundaries.

---

## Example 1: Semidominant Single Condition

**Scenario**: `LDLR` variant observed in familial hypercholesterolemia, where monoallelic and biallelic pathogenic variants cause the same disease with different severity.

**Expected behavior**:

- Use a single FH disease entity.
- Aggregate evidence across monoallelic and biallelic observations.
- Record zygosity/severity in the evidence summary.

---

## Example 2: Different Inheritance, Same Mechanism

**Scenario**: `ATM` variant with evidence from dominant breast cancer and recessive ataxia-telangiectasia contexts.

**Expected behavior**:

- If the mechanism is consistent across conditions, aggregate evidence.
- Prefer separate stored classifications for each condition using the same evidence summary.
- If only one classification can be submitted, use the best-established condition and note the other relationship.

---

## Example 3: Spectrum Disorder

**Scenario**: `FBN1` variant observed in full Marfan syndrome and in isolated aortic dissection cases.

**Expected behavior**:

- Aggregate evidence across the valid spectrum.
- Count phenotype-specific observations differently: full specific phenotype supports stronger case evidence than isolated common features.
- Route PP4/PS4/PP1 questions through the phenotype and segregation overlays.

---

## Example 4: Mutually Exclusive Mechanisms

**Scenario**: `RET` variant evidence exists for MEN2 gain-of-function disease, while Hirschsprung disease is usually LoF-mediated.

**Expected behavior**:

- Do not aggregate evidence between MEN2 and Hirschsprung disease.
- Classify the variant for the condition and mechanism supported by evidence.
- Do not apply PVS1, PS1/PM5, PS3/BS3, PS4, or PM3 across the mechanism boundary.

---

## Example 5: Non-Mutually Exclusive Conditions

**Scenario**: `RYR1` variant may be relevant to malignant hyperthermia and also to dominant or recessive myopathy.

**Expected behavior**:

- Make separate classifications per condition.
- If pathogenic for more than one condition, each classification needs its own evidence summary.
- If pathogenic for one condition but uncertain for another, note the lack of evidence rather than creating a misleading conflict.

---

## Example 6: Unclear Disease Boundary

**Scenario**: A gene has reported related phenotypes, but current sources do not clearly establish whether they are one spectrum or distinct disorders.

**Expected behavior**:

- Aggregate evidence only if phenotypes are close and mechanism appears similar.
- Otherwise split evidence and mark disease-context aggregation as uncertain.
- Ask for target phenotype/disease if the user has not supplied one.

---

## Example 7: Multi-Gene CNV

**Scenario**: A deletion includes multiple genes with distinct disease associations.

**Expected behavior**:

- Route to `tooluniverse-structural-variant-analysis`.
- List diseases associated with genes in the interval.
- Note additional genes with unknown disease association.
- Do not convert the CNV disease list into a sequence-variant claim for one gene.

---

## Minimal Report Block

```markdown
Multiple-disorder context refinement:
- Gene: [symbol]
- Target disease/entity: [disease, inheritance]
- Other associated disorders: [list]
- Validity/dosage: [ClinGen/GenCC/G2P/HI/TS]
- Category: [1-7]
- Evidence aggregation: [aggregate / split / condition-specific]
- ACMG routing changes: [criteria affected]
- Missing information: [if any]
```
