# Quick Start: PM3 In-Trans Refinement

Use this overlay with `tooluniverse-acmg-variant-classification` when an affected proband has biallelic evidence in a recessive disease gene.

PM3 is not an automatic database annotation. It requires affected status, recessive disease context, both-variant frequency review, phase review, and independent classification of the other allele.

When PM3 evidence comes from papers, run `tooluniverse-literature-deep-research` or an equivalent ToolUniverse literature-reading skill first. The literature step should extract proband-level genotype, phase wording, parental/read evidence, and source citations; this PM3 overlay then scores the structured evidence.

---

## Example 1: Confirmed In Trans with Pathogenic Variant

**Scenario**: An affected recessive-disease proband has the assessed variant and another independently classified Pathogenic variant. The paper explicitly says the variants are "in trans" or "compound heterozygous"; both variants meet PM2-level rarity.

**Expected behavior**:

- Score 1.0 point for the proband.
- Apply `PM3` if total points = 1.0.
- If another independent 1.0-point proband exists, total = 2.0 and `PM3_Strong` applies.

---

## Example 2: Phase Unknown with Pathogenic Other Allele

**Scenario**: A paper lists allele 1 and allele 2 in an affected proband, but does not state compound heterozygous/in trans and does not provide family or reads-based phase confirmation. The other allele is Pathogenic.

**Expected behavior**:

- Treat phase as unknown.
- Score 0.5 point.
- Apply `PM3_Supporting` if total points = 0.5.

---

## Example 3: Phase Unknown with Likely Pathogenic Other Allele

**Scenario**: The assessed variant is observed with a Likely Pathogenic variant in an affected proband, but phase is unknown.

**Expected behavior**:

- Score 0.25 point.
- Do not apply PM3 until additional eligible proband points reach at least 0.5.

---

## Example 4: One Parent Tested

**Scenario**: Only one parent is available and carries one of the two variants. The affected proband carries both variants.

**Expected behavior**:

- Count as presumed/one-parent-supported in trans under SVI v1.0.
- Score according to the confirmed in-trans column.
- Clearly label the evidence as one-parent-supported trans evidence in the report.

---

## Example 5: Reads-Supported Compound Heterozygosity

**Scenario**: A source provides read-level evidence showing the two variants are on different alleles.

**Expected behavior**:

- Count as confirmed in trans if the read evidence is adequate and source-supported.
- Score according to the confirmed in-trans column.
- Record the reads-based phasing method.

---

## Example 6: Other Allele Is Rare VUS

**Scenario**: The assessed variant is confirmed in trans with a rare VUS in an affected proband.

**Expected behavior**:

- Score 0.25 point, with maximum total 0.5 from rare VUS other-allele observations.
- Do not use the P/LP row.

---

## Example 7: Homozygous Occurrence

**Scenario**: A rare homozygous occurrence is observed in an affected proband.

**Expected behavior**:

- Score 0.5 point.
- Cap all homozygous occurrence points at 1.0 unless a current VCEP rule allows otherwise.

---

## Example 8: Circularity Check Fails

**Scenario**: Variant A is classified LP only because it used variant B as PM3 evidence. You are now evaluating variant B and want to use variant A as the other allele.

**Expected behavior**:

- Do not use variant A as P/LP evidence for variant B.
- Reclassify variant A without PM3 from variant B, or score the observation using the lower applicable row.
- Withhold PM3 if independent classification is not sufficient.

---

## Minimal Report Block

```markdown
PM3 refinement:
- Disease model: [recessive gene-disease context]
- Proband affected: [yes/no/unclear]
- Assessed variant rarity: [PM2 met/not met, source]
- Other allele rarity: [PM2 met/not met, source]
- Other allele classification: [P/LP/VUS], [independent source]
- Phase: [confirmed in trans / presumed in trans / reads-supported / unknown / homozygous]
- Points this proband: [value]
- Total points: [sum]
- Applied evidence: [PM3_Supporting / PM3 / PM3_Strong / PM3_VeryStrong / No PM3]
```
