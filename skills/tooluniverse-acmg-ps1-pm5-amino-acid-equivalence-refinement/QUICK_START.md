# Quick Start: PS1/PM5 Amino-Acid Equivalence Refinement

Use this overlay with `tooluniverse-acmg-variant-classification` when a missense variant may match an independently established pathogenic variant by the same amino-acid substitution, same residue, or same codon.

This overlay is for protein-level PS1/PM5. Use `tooluniverse-acmg-ps1-splicing-similarity-refinement` when the evidence is same predicted splicing event.

---

## Example 1: Same Amino-Acid Change, Different Nucleotide Change

**Scenario**: The variant under assessment and a known pathogenic comparison variant encode the same amino-acid substitution, but the cDNA/genomic nucleotide change is different.

**Expected behavior**:

- Confirm both variants are on the same clinically relevant transcript/protein residue.
- Confirm the comparison variant is independently pathogenic without using the variant under assessment.
- Confirm the comparison variant acts through the amino-acid change rather than splicing or another DNA/RNA-level mechanism.
- Apply `PS1` if all checks pass.

---

## Example 2: Same Residue, Different Amino-Acid Change

**Scenario**: The variant under assessment changes the same amino-acid residue as a different pathogenic missense variant, but the alternate amino acid is different.

**Expected behavior**:

- Confirm the comparison variant is an independently established pathogenic missense variant.
- Confirm same residue on the same disease-relevant transcript.
- Confirm the disease mechanism supports amino-acid-mediated pathogenicity at that residue or region.
- Apply `PM5` if all checks pass.

---

## Example 3: Same Codon but Different Mechanism

**Scenario**: A reported pathogenic variant affects the same codon, but literature shows its pathogenicity is due to exon skipping or splice disruption.

**Expected behavior**:

- Do not use that comparison variant for protein-level PS1 or PM5.
- Route same-splicing-event evidence to `tooluniverse-acmg-ps1-splicing-similarity-refinement` if applicable.
- Route direct RNA evidence to `tooluniverse-acmg-pvs1-splicing-refinement` if it affects PVS1/BP7.

---

## Example 4: PM5 Circularity

**Scenario**: Variant A is called likely pathogenic only because Variant B affects the same residue, and Variant B is now being interpreted using Variant A.

**Expected behavior**:

- Do not use Variant A as PM5 evidence for Variant B.
- Report the comparison as non-independent.
- Assign `No PM5` or `PM5 not assessable`.

---

## Example 5: Same Amino-Acid Change but Splicing Confounder

**Scenario**: Two variants encode the same amino-acid substitution, but one nucleotide change is predicted or shown to alter splicing.

**Expected behavior**:

- Check SpliceAI, VEP splice-region consequence, and available RNA/literature evidence.
- If the comparison variant's pathogenicity is splicing-mediated, do not apply protein-level PS1.
- If both variants independently share a splicing event, evaluate splicing PS1 separately.

---

## Example 6: Dominant-Negative or Mixed Mechanism Gene

**Scenario**: A same-residue comparison variant is pathogenic in a dominant-negative disease mechanism.

**Expected behavior**:

- Use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before PS1/PM5.
- Apply PS1/PM5 only if the variant under assessment plausibly shares the same disease-relevant mechanism.
- Do not transfer evidence from a haploinsufficiency, splicing LoF, or unrelated gain-of-function variant to a dominant-negative missense variant without same-mechanism support.

---

## Example 7: Same Codon Only

**Scenario**: The variant under assessment affects the same codon as a known pathogenic variant, but it does not produce the same amino-acid substitution and the residue-level mechanism is uncertain.

**Expected behavior**:

- Same codon alone is not enough for PS1.
- Consider PM5 only if the alternate amino acid is different at the same residue and the comparison variant is an independently pathogenic missense variant.
- Withhold PS1/PM5 when the mechanism or comparison classification is not reliable.

---

## Minimal Report Block

```markdown
PS1/PM5 amino-acid equivalence refinement:
- Variant under assessment: [HGVS c.], [HGVS p.], transcript [ID]
- Comparison variant: [HGVS c.], [HGVS p.], source [ClinVar/ClinGen/VCEP/literature]
- Relationship: [same amino-acid substitution / same residue different substitution / same codon only]
- Comparison classification and review status: [summary]
- Independence: [confirmed / circularity concern / not assessable]
- Mechanism: [amino-acid mediated / splicing-mediated / mixed / uncertain]
- Splicing confounding: [none / present / not assessable]
- Applied evidence: [PS1 / PM5 / No PS1/PM5 / not assessable]
```
