# Quick Start: PP1 Segregation Refinement

Use this overlay with `tooluniverse-acmg-variant-classification` when family segregation evidence affects PP1 strength, BS4, or the combined PP1/PP4 evidence cap.

The examples below assume that variant identity, gene-disease validity, inheritance, and phenotype fit have already been checked with ToolUniverse tools.

---

## Example 1: Locus Homogeneity With High Diagnostic Yield

**Scenario**: A proband has a highly specific phenotype for a single-gene disorder with diagnostic yield above 90%, and one plausible qualifying variant is found on the implicated allele.

**Expected behavior**:

- Use diagnostic-yield PP4 points, round down, and cap combined PP1/PP4 locus evidence at +5.0.
- Do not add PP1 from expected perfect co-segregation in the same locus-homogeneous context.
- Report the selected code split, for example `PP4_Strong` plus `PP1` only if the evidence source justifies both and the combined cap is respected.

---

## Example 2: Locus Heterogeneity With Affected Sibling

**Scenario**: A recessive disease has two known genes. The phenotype and testing method give 70% diagnostic yield for the gene under assessment. Two affected siblings share the same homozygous or in-trans genotype.

**Expected behavior**:

- Assign PP4 diagnostic-yield points from 70% by rounding down to `+4.0`.
- Add co-segregation points from the affected sibling using the ClinGen 2024 table.
- Cap the combined PP1/PP4 total at `+5.0` per variant.
- Do not count either affected child again as PS4 if the same observation is used for PP4/PP1.

---

## Example 3: Multiple Candidate Variants on One Allele

**Scenario**: The implicated allele has two plausible variants in cis and the phenotype/test-yield evidence implicates the allele.

**Expected behavior**:

- Do not give the full PP1/PP4 points to both variants by default.
- Apportion posterior probability across the plausible variants using non-PP1/PP4/BS4 evidence and the Table S1 logic.
- Redistribute evidence only when independent evidence makes one variant substantially more plausible than the other.

---

## Example 4: Fallback Strong Co-Segregation

**Scenario**: Diagnostic-yield and PP4 inputs are not available, but a heterozygous variant in an autosomal dominant disease gene is present in eight affected relatives across a large pedigree. There are at least seven informative meioses, no affected non-carriers, and no unexplained informative unaffected carriers.

**Expected behavior**:

- Use the older informative-meioses/LOD fallback only because combined-guidance inputs are unavailable.
- Apply `PP1_Strong` if the segregation is credible and variant-specific.
- Report why the combined PP1/PP4 approach could not be applied.

---

## Example 5: Published LOD Score

**Scenario**: A paper reports a variant-specific LOD score of 3.2 in a disease-consistent pedigree.

**Expected behavior**:

- Apply `PP1_Strong` if the LOD score is credible and variant-specific.
- Record whether the LOD is variant-specific, locus-level, gene-level, or allele-level.
- If the LOD is only locus-level and multiple candidate variants remain, apportion evidence, reduce strength, or withhold PP1 for the individual variant.

---

## Example 6: Apparent Non-Segregation

**Scenario**: One affected relative does not carry the variant, but the phenotype is common and the reported diagnosis is not specific.

**Expected behavior**:

- Do not automatically apply BS4.
- Withhold or downgrade PP1 until phenocopy and phenotype-certainty issues are resolved.
- Explain why the affected non-carrier is not definitive non-segregation.

---

## Example 7: Robust Non-Segregation

**Scenario**: Multiple definitely affected relatives do not carry the variant, paternity/sample identity and genotype quality are confirmed, and phenocopy is unlikely.

**Expected behavior**:

- Apply `BS4`.
- Do not apply PP1.
- State why reduced penetrance or phenocopy does not explain the observation.

---

## Example 8: Compound Heterozygous Recessive Non-Segregation

**Scenario**: In a recessive disorder, the affected proband is compound heterozygous. A relative shows non-segregation at the locus, but the data do not identify which allele is benign.

**Expected behavior**:

- Do not automatically apply BS4 to either variant.
- State that a single family may show one allele is not causative without distinguishing which variant is benign.
- Use PM3, phase, phenotype, and independent variant-level evidence instead.

---

## Example 9: Adult-Onset or Reduced-Penetrance Disease

**Scenario**: Several unaffected variant carriers are young relatives in an adult-onset cancer predisposition syndrome.

**Expected behavior**:

- Do not treat the young unaffected carriers as strong contradiction.
- Use affected-only segregation counting or formal linkage analysis with liability classes.
- Prefer case-control or other evidence if the phenotype has high phenocopy risk.

---

## Example 10: Case-Control, PP4, and Segregation in One Paper

**Scenario**: A paper includes a family pedigree and a case-control cohort, and some family members are also counted in the cohort.

**Expected behavior**:

- Do not double count the same individuals.
- Use the most informative evidence path for each individual.
- A previously observed affected individual can count as PP4 or PS4, but not both.
- Family members of that individual can still contribute PP1 if independently informative.

---

## Minimal Report Block

```markdown
PP1 refinement:
- Gene-disease context: [gene], [disease], [inheritance], [ClinGen/GenCC status]
- Variant: [HGVS], qualifying because [mechanism/consequence/frequency]
- PP4/diagnostic yield: [yield, testing method comparability, PP4 points, if used]
- Segregation: [Biesecker 2024 points / LOD / informative meioses fallback], [affected carriers], [contradictions]
- Combined cap: [PP1/PP4 total, +5.0 cap, code split]
- Apportionment: [single variant / multiple variants on allele / linked loci]
- Modifiers: [penetrance/phenocopy/age/phenotype certainty]
- Double-counting check: [what was excluded or not reused]
- Applied evidence: [PP1 / PP1_Moderate / PP1_Strong / BS4 / No PP1]
```
