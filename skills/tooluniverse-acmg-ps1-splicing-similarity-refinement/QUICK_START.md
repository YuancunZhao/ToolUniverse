# Quick Start: PS1 Splicing Similarity Refinement

Use this overlay with `tooluniverse-acmg-variant-classification` when PS1 may apply because the variant under assessment has the same predicted RNA-splicing event as a known pathogenic or likely pathogenic comparison variant.

This overlay is separate from `tooluniverse-acmg-pvs1-splicing-refinement`. PVS1 evaluates loss-of-function consequence and strength. This overlay evaluates PS1 similarity evidence.

---

## Minimal Workflow

1. Normalize the VUA and comparison variant on the same transcript.
2. Determine whether the VUA is outside donor/acceptor +/-1,2 or at donor/acceptor +/-1,2.
3. Assign the VUA's baseline splicing code first: PP3 or PVS1/PVS1_Strength.
4. Confirm the comparison variant is P or LP with clinical or literature support.
5. Confirm the VUA and comparison variant have the same predicted splicing event.
6. Confirm the VUA prediction is similar to or stronger than the comparison variant.
7. Apply the Walker Table 2 PS1-splicing strength.

---

## Example 1: Same Nucleotide Outside +/-1,2

**Scenario**: The VUA is outside donor/acceptor +/-1,2 and has PP3 splicing prediction evidence. A different alternate allele at the same nucleotide is Pathogenic and predicts the same exon-skipping event.

**Expected behavior**:

- Apply `PS1` if the comparison variant is Pathogenic.
- Apply `PS1_Moderate` if the comparison variant is Likely Pathogenic.

---

## Example 2: Same Motif Outside +/-1,2

**Scenario**: The VUA is outside donor/acceptor +/-1,2 and has PP3. A P/LP comparison variant lies at another position in the same donor or acceptor motif. Both variants predict the same cryptic splice-site use.

**Expected behavior**:

- Apply `PS1_Moderate` if the comparison variant is Pathogenic.
- Apply `PS1_Supporting` if the comparison variant is Likely Pathogenic.

---

## Example 3: Full PVS1 Canonical Splice Variant

**Scenario**: The VUA is at donor/acceptor +/-1,2 and receives full PVS1. A Pathogenic comparison variant lies within the same donor/acceptor +/-1,2 dinucleotide and predicts the same event.

**Expected behavior**:

- Apply `PS1_Supporting`.
- Do not apply PS1 if the comparison variant is only Likely Pathogenic for this row.

---

## Example 4: Downgraded PVS1 Canonical Splice Variant

**Scenario**: The VUA is at donor/acceptor +/-1,2, but PVS1 is downgraded to `PVS1_Moderate` because of transcript context. A Pathogenic comparison variant lies in the same donor/acceptor +/-1,2 dinucleotide and predicts the same event.

**Expected behavior**:

- Apply `PS1`.
- If the comparison variant is Likely Pathogenic, apply no PS1 for this row.

---

## Example 5: Canonical Splice VUA Compared with Motif Variant Outside +/-1,2

**Scenario**: The VUA is at donor/acceptor +/-1,2 and has `PVS1_Strong`, `PVS1_Moderate`, or `PVS1_Supporting`. A comparison variant lies in the same donor/acceptor motif but outside +/-1,2. The predicted event is the same.

**Expected behavior**:

- Apply `PS1_Moderate` if the comparison variant is Pathogenic.
- Apply `PS1_Supporting` if the comparison variant is Likely Pathogenic.

---

## Example 6: Event Does Not Precisely Match

**Scenario**: Both variants have high SpliceAI scores, but the VUA predicts donor loss while the comparison variant predicts cryptic acceptor gain.

**Expected behavior**:

- Apply no PS1-splicing evidence.
- Record that the predicted splice events do not precisely match.

---

## Example 7: Exonic Variant with Protein Effect

**Scenario**: The VUA and comparison variant are exonic. Both are predicted to alter splicing, but retained mRNA would encode different missense substitutions.

**Expected behavior**:

- Review protein consequences before applying PS1-splicing.
- Withhold PS1-splicing if the pathogenic mechanisms may differ.
- Evaluate ordinary protein-level PS1/PM5 separately if applicable.

---

## Minimal Report Block

```markdown
PS1 splicing similarity refinement:
- VUA: [HGVS], transcript [reference], location [outside +/-1,2 / at +/-1,2]
- Baseline splicing evidence: [PP3 / PVS1 / PVS1_Strong / PVS1_Moderate / PVS1_Supporting]
- VUA predicted event: [event and prediction strength]
- Comparison variant: [HGVS], [P/LP], [source]
- Comparison event: [predicted or observed event]
- Relative position: [same nucleotide / same +/-1,2 dinucleotide / same motif]
- Same-event prerequisite: [met/not met]
- Protein consequence check: [not applicable / reviewed / issue]
- Applied evidence: [PS1 / PS1_Moderate / PS1_Supporting / No PS1]
```
