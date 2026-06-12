# Quick Start: PS3/BS3 Functional Assay Refinement

Use this overlay with `tooluniverse-acmg-variant-classification` when a variant has functional assay evidence.

PS3/BS3 should not be assigned simply because a paper reports a functional experiment. Start from no evidence, then increase strength only when the assay is applicable to the disease mechanism and the specific assay instance is validated.

When evidence comes from papers, run `tooluniverse-literature-deep-research` or an equivalent ToolUniverse literature-reading skill first. The literature step should extract assay design, controls, replicates, validation controls, thresholds, and variant readout; this overlay then assigns PS3/BS3 strength.

---

## Example 1: Calibrated Abnormal Function

**Scenario**: A missense variant in a loss-of-function disease gene shows severely reduced enzyme activity. The assay has wild-type and null controls, biological replicates, calibrated abnormal/normal thresholds, and formal OddsPath > 18.7.

**Expected behavior**:

- Confirm that reduced activity is the disease mechanism.
- Apply `PS3`.
- Do not also count the same assay as PP3.

---

## Example 2: Moderate Functional Evidence Without Formal OddsPath

**Scenario**: A cellular assay includes wild-type and null controls, replicates, and 11 total validation controls with a mix of P/LP and B/LB variants. The assessed variant falls in the calibrated abnormal range, but the paper does not report formal statistical calibration.

**Expected behavior**:

- Apply `PS3_Moderate`.
- Cite the 11-control threshold and the assay source.

---

## Example 3: Supporting Historical Assay

**Scenario**: A historical biochemical assay reports abnormal activity with appropriate wild-type and abnormal controls plus replicates, but only a few validation controls.

**Expected behavior**:

- Apply `PS3_Supporting` at most.
- Do not treat the study as strong evidence without assay validation.

---

## Example 4: Normal Function in a Well-Calibrated Assay

**Scenario**: A variant result is indistinguishable from benign controls in a well-calibrated assay that tests the full disease-relevant function. OddsPath is < 0.053.

**Expected behavior**:

- Apply `BS3`.
- Confirm that the normal result tests the relevant molecular consequence.

---

## Example 5: Normal Result in a Narrow Assay

**Scenario**: A variant has normal ATP hydrolysis in an assay, but disease pathogenesis also depends on binding and substrate processing that the assay does not test.

**Expected behavior**:

- Reduce BS3 strength or withhold BS3.
- Record that the assay is mechanistically incomplete.

---

## Example 6: Indeterminate or Hypomorphic Result

**Scenario**: A variant has intermediate activity between calibrated benign and pathogenic ranges.

**Expected behavior**:

- Do not force PS3 or BS3.
- Apply no functional code unless VCEP thresholds define the intermediate range as pathogenic, benign, or strength-reduced evidence.

---

## Example 7: Prediction-Only Evidence

**Scenario**: REVEL, AlphaMissense, EVE, or SpliceAI predicts deleteriousness, but no assay was performed.

**Expected behavior**:

- Do not apply PS3/BS3.
- Use PP3/BP4 or the splicing prediction pathway as appropriate.

---

## Example 8: RNA Splicing Assay Already Used for PVS1/BP7 RNA

**Scenario**: RNA assay evidence shows out-of-frame exon skipping with predicted NMD and is used as `PVS1_Strength (RNA)`.

**Expected behavior**:

- Do not also apply PS3 from the same splicing assay.
- Let `tooluniverse-acmg-pvs1-splicing-refinement` handle RNA-based PVS1/BP7 logic.

---

## Example 9: Conflicting Functional Assays

**Scenario**: One assay reports abnormal function and another reports normal function.

**Expected behavior**:

- If one assay better matches the disease mechanism and is better validated, use that assay at its justified strength.
- If both assays have similar relevance and validation, apply no PS3/BS3 from the conflicting evidence.

---

## Example 10: MAVE/DMS Score Set

**Scenario**: A deep mutational scanning score set contains the variant. The score set has many known P/LP and B/LB controls, calibrated thresholds, and the variant falls in the abnormal range.

**Expected behavior**:

- Retrieve the score set with MaveDB tools.
- Confirm control independence, score direction, threshold calibration, and mechanism match.
- Apply PS3/BS3 at the calibrated strength.
- Do not also use the same score as PP3/BP4.

---

## Minimal Report Block

```markdown
PS3/BS3 functional assay refinement:
- Mechanism: [gene-disease mechanism]
- Assay: [class and specific instance]
- Controls/replicates: [present/absent]
- Validation controls: [P/LP count], [B/LB count], total [count]
- Calibration: [thresholds / OddsPath / VCEP rule / none]
- Variant result: [readout and category]
- Conflict handling: [none/resolved/unresolved]
- Double counting: [same functional evidence not reused as PP3/BP4/PVS1/BP7]
- Applied evidence: [PS3_Supporting / PS3_Moderate / PS3 / BS3_Supporting / BS3_Moderate / BS3 / No PS3/BS3]
```
