# Quick Start: PM2 Absence/Rarity Refinement

Use this overlay with `tooluniverse-acmg-variant-classification` when absence or rarity in population databases affects PM2, BA1, BS1, BS2, PM3 eligibility, or the `PVS1 + PM2_Supporting` combination.

PM2 is not a moderate pathogenic criterion under the generic ClinGen SVI recommendation. The default evidence code is `PM2_Supporting`.

---

## Example 1: Absent from Adequately Covered gnomAD

**Scenario**: A rare disease variant is absent from gnomAD after correct normalization. The locus is represented and no ancestry-specific conflict is found.

**Expected behavior**:

- Apply `PM2_Supporting`.
- Do not apply PM2 at Moderate strength.
- Report population sources and coverage/representation status.

---

## Example 2: Very Low Frequency Compatible with Disease Model

**Scenario**: The variant is present at a very low allele count and the maximum ancestry AF remains below the disease- or VCEP-specific PM2 threshold.

**Expected behavior**:

- Apply `PM2_Supporting`.
- Report global AF, maximum ancestry AF, AC/AN, and homozygote or hemizygote count.
- Do not infer pathogenicity from rarity alone.

---

## Example 3: No gnomAD Record but Coverage Is Unclear

**Scenario**: The variant is not returned by gnomAD, but the region is hard to map, poorly covered, structurally complex, or the allele cannot be confidently matched across builds.

**Expected behavior**:

- Do not apply PM2.
- Report `PM2 not assessable`.
- Use fallback sources only to clarify representation, not to force PM2.

---

## Example 4: Frequency Too High

**Scenario**: The variant has a maximum ancestry AF above the disease-specific BS1 threshold or above BA1.

**Expected behavior**:

- Do not apply PM2.
- Apply BA1 or BS1 if the relevant threshold and disease context are met.
- Let benign frequency evidence take priority over rarity evidence.

---

## Example 5: Healthy Homozygotes or Hemizygotes

**Scenario**: The variant is rare but observed in healthy homozygotes for a severe fully penetrant recessive disease, or hemizygotes for an X-linked condition where this is incompatible with disease.

**Expected behavior**:

- Do not apply PM2 if BS2 is supported.
- Consider BS2 with appropriate disease penetrance and clinical context.
- Document why rarity is overridden by incompatible healthy observations.

---

## Example 6: PVS1 Plus PM2_Supporting

**Scenario**: A novel frameshift variant validly meets PVS1 at Very Strong strength in a gene where LoF is an established disease mechanism. It is absent from adequately covered population data.

**Expected behavior**:

- Before applying `PVS1`, document the curated LoF/HI mechanism source. If the gene has dominant/recessive disease associations, mixed mechanisms, structural/complex biology, or unclear LoF support for the exact disease context, run `tooluniverse-acmg-dominant-negative-mechanism-refinement` first.
- Apply `PVS1`.
- Apply `PM2_Supporting`.
- Classify as Likely Pathogenic under the ClinGen SVI PM2 combination rule, assuming no conflicting benign evidence or VCEP exception.

---

## Example 7: Downgraded PVS1

**Scenario**: A predicted LoF variant is rare, but PVS1 is downgraded to `PVS1_Moderate` because NMD is not expected or a rescue transcript is plausible.

**Expected behavior**:

- Apply `PM2_Supporting` if population evidence is adequate.
- Do not use the special `PVS1 + PM2_Supporting` Likely Pathogenic combination because PVS1 is not Very Strong.
- Use standard ACMG or VCEP-specific combining rules.

---

## Example 8: PM3 Eligibility Check

**Scenario**: In a recessive disorder, the assessed variant is observed with another allele in an affected proband.

**Expected behavior**:

- Check PM2-level rarity for both variants.
- Pass the structured result into `tooluniverse-acmg-pm3-in-trans-refinement`.
- Do not treat the other allele's rarity as standalone PM2 evidence for the assessed variant.

---

## Minimal Report Block

```markdown
PM2 absence/rarity refinement:
- Variant: [HGVS/genomic allele], normalized ID [rsID/CA ID/gnomAD ID]
- Population sources checked: [sources]
- Global AF: [value], max ancestry AF: [value and ancestry]
- AC/AN: [value], homozygotes/hemizygotes: [value]
- Coverage/representation: [adequate/uncertain/poor]
- Disease model and threshold: [summary]
- Benign frequency conflict: [none/BA1/BS1/BS2]
- Applied evidence: [PM2_Supporting / No PM2 / PM2 not assessable]
- Combination: [none / PVS1 + PM2_Supporting => Likely Pathogenic]
```
