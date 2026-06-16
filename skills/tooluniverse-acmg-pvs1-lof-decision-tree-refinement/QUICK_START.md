# Quick Start: PVS1 LoF Decision Tree Refinement

Use this overlay with `tooluniverse-acmg-variant-classification` whenever PVS1 is being considered for a predicted loss-of-function variant.

This is the baseline Abou Tayoun et al. 2018 / ClinGen SVI PVS1 decision tree overlay. Use `tooluniverse-acmg-pvs1-splicing-refinement` only after this step when RNA assay or Walker 2023 splicing-specific evidence is present.

---

## Basic Workflow

1. Normalize the variant and transcript with VariantValidator/VEP.
2. Confirm the Table 1 LoF disease-mechanism gate and any required final-strength downgrade.
3. Determine variant class: nonsense, frameshift, canonical splice, start-loss, exon deletion, whole-gene deletion, duplication, or in-frame event.
4. Determine whether NMD is expected or whether the PTC falls in an NMD-escape branch.
5. Check critical domain/residue loss, alternative initiation, rescue transcripts, and disease-specific exceptions.
6. Assign `PVS1`, `PVS1_Strong`, `PVS1_Moderate`, `PVS1_Supporting`, `PVS1_N/A`, or `applied_evidence: none` with `status: not_assessed` when required inputs are missing.
7. Route RNA evidence to Walker 2023 splicing refinement only when RNA assay or detailed splicing evidence exists.

---

## Example 1: Nonsense or Frameshift With NMD

**Scenario**: Nonsense or frameshift variant in an established LoF disease gene. The downstream PTC is predicted to undergo NMD, and no rescue transcript is identified.

**Expected behavior**:

- Confirm LoF/haploinsufficiency for the exact gene-disease context.
- Confirm the transcript is disease-relevant.
- Apply `PVS1`.

---

## Example 2: Nonsense in a Baseline NMD-Escape Region

**Scenario**: Stop-gain variant is in the 3' most exon or within the 3' most 50 nucleotides of the penultimate exon.

**Expected behavior**:

- Do not assign Very Strong PVS1 automatically.
- Evaluate the NMD-escape truncated-protein branch.
- Use `PVS1_Strong`, `PVS1_Moderate`, `PVS1_Supporting`, or `PVS1_N/A` depending on critical-region loss and retained function.

---

## Example 3: NMD-Escape Region With Unknown Function

**Scenario**: A nonsense variant is not predicted to undergo NMD. The truncated region is not proven critical, LoF variants in the exon are not frequent in population data, and the exon is present in biologically relevant transcripts.

**Expected behavior**:

- Use `PVS1_Strong` if the variant removes more than 10% of the protein.
- Use `PVS1_Moderate` if the variant removes less than 10% of the protein.
- Use `PVS1_N/A` if LoF variants in the exon are frequent in the general population or the exon is absent from biologically relevant transcripts.

---

## Example 4: Canonical Splice Variant With Out-of-Frame NMD Consequence

**Scenario**: A canonical splice donor/acceptor variant is predicted to cause out-of-frame exon skipping with a PTC expected to undergo NMD.

**Expected behavior**:

- Use this baseline PVS1 tree to assign the appropriate PVS1 strength.
- Do not also apply PP3 from in silico splicing prediction for the same canonical splice evidence.
- Check whether a nearby +/-20 nucleotide strong consensus splice sequence may reconstitute in-frame splicing; if so, apply the lowest plausible PVS1 strength unless RNA evidence resolves the event.
- If direct RNA evidence confirms the event, then use `tooluniverse-acmg-pvs1-splicing-refinement` for Walker 2023 RNA-specific naming and double-counting.

---

## Example 5: Canonical Splice Variant With In-Frame Exon Loss

**Scenario**: Canonical splice variant is predicted to cause in-frame exon skipping outside known critical residues or domains.

**Expected behavior**:

- Use `PVS1_Strong` if the skipped in-frame region is critical to protein function.
- If the region role is unknown, use `PVS1_Strong` when more than 10% of the protein is removed and `PVS1_Moderate` when less than 10% is removed, provided LoF variants in the exon are not frequent and the exon is present in biologically relevant transcripts.
- Use `PVS1_N/A` if LoF variants in the exon are frequent or the exon is absent from biologically relevant transcripts.
- Consider `tooluniverse-acmg-pm4-bp3-protein-length-refinement` for PM4/BP3 if the protein-length change is the relevant evidence.

---

## Example 6: Start-Loss Variant

**Scenario**: Initiation codon variant abolishes the annotated start codon.

**Expected behavior**:

- Use `PVS1_N/A` if a different functional transcript uses an alternative start codon.
- If there is no known alternative start codon in other transcripts, use `PVS1_Moderate` when at least one pathogenic variant is reported upstream of the closest potential in-frame start codon.
- Use `PVS1_Supporting` when no pathogenic variants are reported upstream of the closest potential in-frame start codon.
- Do not apply `PVS1` or `PVS1_Strong` to initiation codon variants under the generic 2018 tree unless disease-specific expert guidance justifies it.

---

## Example 7: Single- or Multi-Exon Deletion

**Scenario**: Deletion removes one or more exons.

**Expected behavior**:

- Route event definition through `tooluniverse-structural-variant-analysis`.
- Determine whether the deletion disrupts the reading frame and causes NMD.
- If reading frame is disrupted and NMD is predicted, use `PVS1` when the exon is present in biologically relevant transcripts and `PVS1_N/A` when it is absent.
- If reading frame is disrupted but NMD is not predicted, use the NMD-escape branch.
- If reading frame is preserved, use the in-frame branch.
- Apply the corresponding PVS1 branch only after transcript and exon boundaries are known.

---

## Example 8: Whole-Gene Deletion

**Scenario**: CNV removes the entire gene in a disease where haploinsufficiency is established.

**Expected behavior**:

- Confirm the deletion includes the whole gene and the CNV call is reliable.
- Confirm LoF/haploinsufficiency for the disease.
- Apply PVS1-compatible evidence.
- Avoid double counting the same CNV as both PVS1 and a separate dosage criterion unless the classification framework explicitly permits it.

---

## Example 9: LoF Variant in Dominant-Negative-Only Disease

**Scenario**: The disease is caused by dominant-negative missense or in-frame variants, and haploinsufficiency is not established.

**Expected behavior**:

- Use `tooluniverse-acmg-dominant-negative-mechanism-refinement`.
- Do not apply ordinary PVS1 to a null variant solely because it is null.
- Use `PVS1_N/A` unless a separate LoF disease mechanism is established.

---

## Example 10: Duplication Branch

**Scenario**: A copy-number event duplicates one or more exons and is completely contained within the gene.

**Expected behavior**:

- Use `PVS1` only when the duplication is proven in tandem, disrupts the reading frame, and is predicted to undergo NMD.
- Use `PVS1_Strong` when the duplication is presumed in tandem, the reading frame is presumed disrupted, and NMD is predicted.
- Use `PVS1_N/A` when the duplication is proven not to be in tandem.
- Use `PVS1_N/A` when the duplication has no or unknown impact on reading frame and NMD.
- Use `applied_evidence: none` with `status: not_assessed` when duplication length or breakpoints are too uncertain to predict reading-frame impact.

---

## Example 11: Gene-Level LoF Evidence Downgrade

**Scenario**: A variant reaches a strong Figure 1 branch, but the gene-disease LoF evidence does not meet the full Table 1 gate.

**Expected behavior**:

- Apply the Figure 1 strength directly only when the gene-disease pair has Strong/Definitive validity, at least three Pathogenic LoF variants classified without PVS1, more than 10% phenotype-associated pathogenic variants are LoF, and qualifying LoF variants are distributed across more than one exon unless the gene has one exon.
- Decrease the final strength by one level when clinical validity is at least Moderate, at least two LoF variants are associated with the phenotype across more than one exon, and a null mouse model recapitulates the phenotype.
- Decrease the final strength by two levels when clinical validity is at least Moderate and only one of those supporting conditions is met.
- Use `PVS1_N/A` when there is no evidence that LoF variants cause the disease.

---

## Example 12: RNA Assay Defines the Transcript Consequence

**Scenario**: RNA assay shows the actual transcript product for a splice variant.

**Expected behavior**:

- Interpret the observed transcript product through this 2018 PVS1 tree.
- Then use `tooluniverse-acmg-pvs1-splicing-refinement` for Walker 2023 RNA-specific evidence code naming and double-counting rules.
- Do not also use the same RNA assay as PS3.

---

## Minimal Report Block

```markdown
PVS1 LoF decision tree refinement:
- Variant: [HGVS c./p./g.]
- Transcript: [ID and relevance]
- Variant class: [nonsense/frameshift/splice/start-loss/exon deletion/whole-gene deletion/duplication/in-frame]
- LoF mechanism: [established / not established / mixed / not assessed]
- NMD: [expected / NMD escape / not applicable / unknown]
- Critical-region loss: [yes / plausible / no / unknown]
- Rescue/alternative initiation: [none / plausible / present / not assessed]
- Applied evidence: [PVS1 / PVS1_Strong / PVS1_Moderate / PVS1_Supporting / PVS1_N/A / none]
- Status: [applied / not_applicable / not_assessed]
- Reason: [concise explanation, including missing inputs when status is not_assessed]
```
