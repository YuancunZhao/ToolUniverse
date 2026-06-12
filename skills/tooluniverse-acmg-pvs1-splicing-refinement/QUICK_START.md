# Quick Start: ACMG PVS1 Splicing Refinement

Use this skill together with `tooluniverse-acmg-variant-classification` when RNA-splicing evidence changes PVS1 or BP7 assignment.

## Basic Workflow

1. Run the usual ACMG variant classification evidence retrieval.
2. If RNA assay or detailed splicing evidence is present, invoke this skill for the PVS1/splicing branch.
3. Decide whether the evidence should be captured as `PVS1_Strength (RNA)`, `BP7_Strong (RNA)`, prediction-only PP3/BP4 evidence, explanatory text, or no code.
4. Remove duplicate splicing-use of PS3/BS3 or PP3/BP4 when RNA evidence already supplies the PVS1/BP7 splicing code.

## Example 1: Out-of-frame exon skipping with NMD

**Input evidence**

- Canonical splice variant in a gene where LoF is the established disease mechanism.
- RNA assay shows complete or near-complete exon skipping.
- Skipping causes a frameshift and premature termination codon predicted to undergo NMD.
- No plausible rescue transcript preserves the critical protein region.

**Expected behavior**

- Apply `PVS1_Strength (RNA)` at the strength supported by the PVS1 decision tree, often very strong when the transcript consequence is equivalent to a null allele.
- Do not also apply PS3 for the same RNA-splicing assay.
- Do not apply PP3 for the same splice mechanism if RNA evidence is being used for PVS1.

**Report wording**

`PVS1_Strength (RNA): RNA assay demonstrates out-of-frame exon skipping with predicted NMD in an LoF disease gene; no plausible rescue transcript was identified. Evidence interpreted under Walker et al. 2023 ClinGen SVI Splicing Subgroup guidance.`

## Example 2: In-frame exon skipping removes critical residues

**Input evidence**

- RNA assay shows in-frame exon skipping.
- The skipped exon contains undisputed clinically relevant residues or a critical functional domain.
- Protein/domain evidence supports that loss of this region disrupts function.

**Expected behavior**

- Apply `PVS1_Strength (RNA)` using the PVS1 decision tree.
- Very strong evidence may be appropriate for in-frame RNA skipping that removes undisputed clinically relevant residues, but reduce strength if size, location, structural context, or retained domain function weakens the LoF inference.
- Cite protein/domain evidence used to support the critical-region call.

## Example 3: In-frame exon skipping outside critical regions

**Input evidence**

- RNA assay shows in-frame exon skipping.
- The skipped region is outside known critical domains and does not remove known clinically relevant residues.
- Available protein evidence does not establish loss of function.

**Expected behavior**

- Reduce PVS1 strength or do not apply PVS1.
- Record the RNA event and explain why LoF is not established.
- Continue classification using other applicable ACMG evidence.

## Example 4: Plausible rescue transcript

**Input evidence**

- Variant disrupts an exon present in the canonical transcript.
- A physiological alternative transcript naturally excludes the affected exon.
- The alternative transcript preserves reading frame and critical domains.
- Expression is sufficient or unknown but plausible under the conservative rescue transcript model.

**Expected behavior**

- Reduce PVS1 strength or withhold PVS1 (`PVS1_N/A`) depending on how strongly the rescue transcript preserves clinically relevant function.
- Document the alternative transcript, retained domains, and expression evidence or uncertainty.

## Example 5: SpliceAI high score without RNA assay

**Input evidence**

- SpliceAI max delta score is high.
- No RNA assay or published RNA-splicing result is available.

**Expected behavior**

- Do not apply `PVS1_Strength (RNA)`.
- Treat the result as prediction-only evidence, generally in the PP3/BP4 splicing-prediction pathway.
- If later RNA evidence becomes available and supports PVS1, remove duplicate PP3/BP4 use for the same splicing mechanism.

## Example 6: No splicing impact for synonymous or intronic variant

**Input evidence**

- Variant is synonymous, intronic, or non-coding.
- RNA assay shows no detectable splicing impact.
- No separate coding protein consequence requires classification.

**Expected behavior**

- Apply `BP7_Strong (RNA)`.
- Do not also apply BS3 for the same RNA assay.

## Example 7: Missense variant with no splicing impact

**Input evidence**

- Variant has a missense or in-frame coding consequence.
- RNA assay shows no splicing impact.
- Protein-level impact has not been excluded.

**Expected behavior**

- Record the RNA result as explanatory text.
- Do not apply `BP7_Strong (RNA)` unless protein impact is also excluded or gene-specific rules make protein impact irrelevant.
- Classify the coding consequence separately.

## Example 8: RNA evidence already used for PVS1

**Input evidence**

- RNA assay demonstrates a LoF transcript and is used for `PVS1_Strength (RNA)`.
- SpliceAI also predicts a splice effect.
- The same publication describes the RNA assay as a functional result.

**Expected behavior**

- Apply `PVS1_Strength (RNA)`.
- Do not apply PS3 for the same RNA assay.
- Do not apply PP3 for the same splice mechanism.
- State that prediction/functional splicing codes were not counted separately to avoid double counting.
