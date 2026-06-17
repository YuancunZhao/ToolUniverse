# Quick Start: PM1 Regional Missense Constraint Refinement

Use this overlay with `tooluniverse-acmg-variant-classification` when a missense variant may qualify for PM1 because it lies in a constrained protein region, hotspot, critical functional subregion, or missense-depleted region.

This overlay requires a region-level source. A broad domain label or a high computational score alone is not enough.

---

## Example 1: Variant in Validated MDR

**Scenario**: A missense variant maps to the same transcript/protein coordinate system as an author-provided MDR. The region meets the calibrated observed/expected missense threshold, has low benign variation, and the disease is known to involve pathogenic missense variants.

**Expected behavior**:

- Apply `PM1`.
- Report MDR boundaries, dataset version, and observed/expected missense threshold.
- Do not count the same MDR feature again as PP3.

---

## Example 2: Variant in Broad Domain Only

**Scenario**: A missense variant lies inside a large InterPro/Pfam domain, but there is no hotspot, critical residue, MDR membership, or pathogenic clustering.

**Expected behavior**:

- Do not apply PM1.
- Record broad domain membership as context only.
- Continue evaluating PP3, PM2, PS3, PM5, or other criteria as appropriate.

---

## Example 3: Hotspot with Low Benign Variation

**Scenario**: Multiple disease-relevant pathogenic missense variants cluster in a small protein subregion, the region lacks benign population missense variation, and the current variant lies in that subregion.

**Expected behavior**:

- Apply `PM1` if the hotspot is well established for the same disease mechanism.
- Cite ClinVar/curated literature/domain evidence.
- Avoid using the same ClinVar assertions as separate PS1/PM5 evidence unless independence is clear.

---

## Example 3b: Critical Residue Rule

**Scenario**: A missense variant alters a residue type with an established disease-specific critical-residue rule, such as a collagen triple-helix glycine, an EGF-repeat cysteine imbalance, or a Cys/His zinc-finger coordination residue.

**Expected behavior**:

- Confirm the residue rule is established for the gene-disease context or a current VCEP.
- Consider `PM1_Strong` only when VCEP-specific or accepted practice/local guideline evidence supports that residue class, and label the guidance authority explicitly.
- Do not use generic conservation alone to upgrade PM1 to Strong.

---

## Example 3c: Regional Constraint Source

**Scenario**: DECIPHER regional constraint, CCR, MetaDome, or paralogous-residue evidence suggests the variant lies in an intolerant local region.

**Expected behavior**:

- Map coordinates carefully to the disease-relevant transcript/protein.
- Record the source, version, region boundaries, and whether benign variation is absent or low.
- Use as PM1 context only when it is regional/local evidence, not merely whole-gene missense intolerance.

---

## Example 4: High MPC or AlphaMissense Only

**Scenario**: A missense variant has a high MPC or AlphaMissense score, but no validated MDR membership, hotspot, critical domain, or benign-depleted region evidence is available.

**Expected behavior**:

- Do not apply PM1.
- Consider PP3 if the prediction evidence is calibrated and independent.
- State that PM1 requires regional/domain evidence, not only prediction score evidence.

---

## Example 5: Missense Variant in LoF-Only Disease Gene

**Scenario**: The variant lies in a constrained region, but the disease mechanism is established only for loss-of-function variants and pathogenic missense variants are not established.

**Expected behavior**:

- Do not apply regional PM1.
- Evaluate the variant through the appropriate missense evidence framework.
- Record that gene-disease mechanism does not support PM1 from missense constraint.

---

## Example 6: Benign Variation in the Region

**Scenario**: The queried protein interval contains multiple benign or high-frequency missense variants in ClinVar/gnomAD.

**Expected behavior**:

- Withhold PM1 or reduce confidence unless a smaller critical subregion excludes the benign variation.
- Report the benign variation conflict.

---

## Example 7: PM1 and PP2 Both Met

**Scenario**: A missense variant lies in a validated MDR/hotspot that supports moderate `PM1`. The gene also satisfies `PP2` because missense is a known disease mechanism and benign missense variation is low.

**Expected behavior**:

- Retain `PM1`.
- Do not also apply `PP2`, unless a current disease-specific VCEP rule permits both.
- State that PM1 was retained because the local/regional evidence is more specific than gene-wide PP2.

---

## Example 8: PM1_Supporting and PP2 Both Met

**Scenario**: A missense variant has weak regional/domain evidence that would support only `PM1_Supporting`. The same gene clearly satisfies `PP2`.

**Expected behavior**:

- Retain `PP2`.
- Do not also apply `PM1_Supporting`, unless a current disease-specific VCEP rule permits both.
- Record the weak regional evidence as context.

---

## Example 8b: BP1 Conflict

**Scenario**: A missense variant is in a gene where LoF is the usual disease mechanism, but the local region also has reported pathogenic missense variants for a different dominant-negative disease context.

**Expected behavior**:

- Do not automatically apply BP1 from the LoF-only context.
- Resolve the exact disease mechanism and inheritance context first.
- Apply PM1/PP2/BP1 only in the disease context where the variant class is qualified.

---

## Example 9: PM1 and PP3 Both Retained

**Scenario**: A missense variant lies in a validated MDR supporting `PM1` and also has independent calibrated damaging predictors supporting `PP3`.

**Expected behavior**:

- Retain both only if PP3 is independent of the regional PM1 evidence.
- Cap the combined regional/predictor evidence contribution at Strong.
- Do not treat PM1 plus PP3 as an effective Very Strong evidence block.

---

## Minimal Report Block

```markdown
PM1 refinement:
- Variant: [HGVS/protein], [transcript], [UniProt coordinate]
- Disease mechanism: [missense mechanism supported / not supported]
- Region evidence: [MDR/hotspot/domain], [boundaries], [dataset/version]
- Benign variation check: [ClinVar/gnomAD/ProtVar summary]
- PM1/PP2 selection: [PM1 retained / PP2 retained / VCEP override]
- PM1/PP3 cap: [not applicable / capped at Strong]
- Double-counting check: [MDR not reused as PP3; population rarity not reused as PM1]
- Applied evidence: [PM1 / PP2 / PM1_Supporting / No PM1]
- Guidance authority: [ACMG/AMP baseline / VCEP-specific / practice/local refinement]
```
