# Abou Tayoun et al. 2018 PVS1 Summary

Primary reference:

- Abou Tayoun AN, Pesaran T, DiStefano MT, Oza A, Rehm HL, Biesecker LG, Harrison SM. Recommendations for interpreting the loss of function PVS1 ACMG/AMP variant criterion. Human Mutation. 2018;39(11):1517-1524. PMID:30192042. DOI:10.1002/humu.23626.

## Source Status

ToolUniverse `PubMed_get_article` retrieved the PubMed metadata and abstract for PMID:30192042. The user also provided the full-text PDF (`nihms-986839.pdf`) and the editable ClinGen SVI PVS1 decision tree (`clingen_svi_pvs1_decisiontree_editable.pptx`). This overlay summary was aligned against those full-text and decision-tree files.

## Rule Scope

This source refines the original ACMG/AMP 2015 PVS1 criterion for predicted loss-of-function variants.

It is the baseline PVS1 decision tree for:

- nonsense and frameshift variants;
- canonical splice donor/acceptor variants;
- initiation codon/start-loss variants;
- single-exon or multi-exon deletions;
- whole-gene deletions;
- duplications and complex rearrangements when they cause LoF;
- NMD escape and truncated-protein consequence assessment.

Walker et al. 2023 RNA/splicing guidance is later evidence-specific refinement and should be applied separately after the baseline PVS1 branch is identified.

## Operational Principles

1. PVS1 requires an established LoF disease mechanism for the exact gene-disease context.
2. Variant type alone is not sufficient; transcript consequence and location matter.
3. PTCs predicted to undergo NMD generally support stronger PVS1 than NMD-escape variants.
4. NMD-escape variants require truncated-protein review.
5. In-frame exon loss or in-frame protein-length change supports PVS1 only when critical functional sequence is lost.
6. Start-loss variants require assessment of alternative start codons and N-terminal critical function.
7. CNV/SV events require reliable event definition before PVS1 strength assignment.
8. Rescue transcripts or biologically relevant alternative transcripts can reduce or eliminate PVS1.
9. Disease-specific VCEP specifications supersede the generic decision tree.

## Gene-Disease LoF Mechanism Gate

Apply the Figure 1 decision-tree strength directly only when the gene-disease pair meets the Table 1 LoF mechanism gate:

- clinical validity is Strong or Definitive;
- three or more LoF variants are classified Pathogenic without using PVS1;
- more than 10% of phenotype-associated pathogenic variants are LoF;
- qualifying LoF variants are distributed across more than one exon, except for single-exon genes.

Decrease the final Figure 1 strength by one level when clinical validity is at least Moderate, two or more LoF variants have been associated with the phenotype across more than one exon, and a null mouse model recapitulates the disease phenotype.

Decrease the final Figure 1 strength by two levels when clinical validity is at least Moderate and only one of those two supporting conditions is met.

Do not apply PVS1 at any strength when there is no evidence that LoF variants cause the disease.

## NMD Rule Used by the 2018 Decision Tree

The baseline rule in Abou Tayoun et al. 2018 states that NMD is generally not predicted when the premature termination codon occurs in either:

- the 3' most exon; or
- the 3' most 50 nucleotides of the penultimate exon.

For frameshift variants, assess the downstream PTC coordinate, not only the indel start coordinate. Do not add separate transcript-specific NMD-escape rules to this 2018 baseline unless a disease-specific VCEP or separate current source explicitly instructs that modification.

## Figure 1 Branch Summary

### Nonsense and Frameshift

Use `PVS1` when the PTC is predicted to undergo NMD and the affected exon is present in biologically relevant transcript(s).

When the PTC is not predicted to undergo NMD:

- use `PVS1_Strong` if the truncated or altered region is critical to protein function;
- use `PVS1_N/A` if the region's role is unknown and LoF variants are frequent in the general population or the exon is absent from biologically relevant transcript(s);
- use `PVS1_Strong` if the region's role is unknown, LoF variants are not frequent, the exon is biologically relevant, and more than 10% of the protein is removed;
- use `PVS1_Moderate` in the same unknown-region branch when less than 10% of the protein is removed.

### Canonical Splice Donor/Acceptor

For GT-AG +/-1 or +/-2 splice variants, predict the transcript consequence first.

- If exon skipping or cryptic splice use disrupts the reading frame and NMD is predicted, use `PVS1` when the exon is present in biologically relevant transcript(s), otherwise `PVS1_N/A`.
- If the reading frame is disrupted but NMD is not predicted, use the same not-predicted-NMD branch as nonsense/frameshift variants.
- If the reading frame is preserved, use the in-frame branch.
- Do not combine this canonical splice PVS1 use with PP3 for the same splice prediction evidence.
- The original figure footnote requires no detectable nearby +/-20 nucleotide strong consensus splice sequence that could reconstitute in-frame splicing.

### Initiation Codon

Use `PVS1_N/A` when a different functional transcript uses an alternative start codon.

When there is no known alternative start codon in other transcripts:

- use `PVS1_Moderate` if one or more pathogenic variants are reported upstream of the closest potential in-frame start codon;
- use `PVS1_Supporting` if no pathogenic variants are reported upstream of the closest potential in-frame start codon.

The generic 2018 decision tree does not recommend `PVS1` or `PVS1_Strong` for initiation codon variants without disease-specific expert guidance.

### Exon-Level and Whole-Gene Deletions

Use `PVS1` for a single- or multi-exon deletion when the deletion disrupts the reading frame, NMD is predicted, and the exon is present in biologically relevant transcript(s). Use `PVS1_N/A` if that exon is absent from biologically relevant transcript(s).

For exon-level deletions that disrupt the reading frame but are not predicted to undergo NMD, use the not-predicted-NMD branch. For exon-level deletions that preserve the reading frame, use the in-frame branch.

For whole-gene deletion of a known haploinsufficient gene, the original footnote states that Pathogenic classification is warranted in the absence of conflicting data, even though `PVS1` alone does not reach Pathogenic under the generic combining rules.

### Duplications

Evaluate duplications only when they are at least one exon in size and completely contained within the gene.

- Use `PVS1` when the duplication is proven in tandem, disrupts the reading frame, and NMD is predicted.
- Use `PVS1_Strong` when the duplication is presumed in tandem, the reading frame is presumed disrupted, and NMD is predicted.
- Use `PVS1_N/A` when the duplication is proven not to be in tandem.
- Use `PVS1_N/A` when there is no or unknown impact on the reading frame and NMD.
- If duplication length or breakpoints are too uncertain to predict the reading-frame effect, do not assign PVS1.

### In-Frame Exon Loss or In-Frame Protein Change

Use `PVS1_Strong` when an in-frame event removes a region critical to protein function.

If the region's role is unknown:

- use `PVS1_N/A` when LoF variants are frequent in the general population or the exon is absent from biologically relevant transcript(s);
- use `PVS1_Strong` when LoF variants are not frequent, the exon is biologically relevant, and more than 10% of the protein is removed;
- use `PVS1_Moderate` in the same branch when less than 10% of the protein is removed.

## Footnote-Level Rules to Preserve

- Critical regions should be supported by experimental evidence for the domain/region or by non-truncating pathogenic variants in that region.
- PM4 should not be applied for any variant where PVS1 is applied at any strength.
- For autosomal dominant disease, assess whether the mechanism is haploinsufficiency, dominant-negative, gain-of-function, or mixed before using PVS1.
- ClinGen haploinsufficiency/dosage evidence and population LoF constraint can support mechanism review, but they do not replace variant-level decision-tree assessment.

## Strength Outputs

Use these evidence labels in ToolUniverse ACMG output:

- `PVS1`
- `PVS1_Strong`
- `PVS1_Moderate`
- `PVS1_Supporting`
- `PVS1_N/A`
- `applied_evidence: none` with `status: not_assessed` when required inputs are missing

## ToolUniverse Routing

Use this source through `tooluniverse-acmg-pvs1-lof-decision-tree-refinement`.

Related overlays:

- `tooluniverse-acmg-dominant-negative-mechanism-refinement` for mechanism conflicts before PVS1.
- `tooluniverse-acmg-pvs1-splicing-refinement` for Walker 2023 RNA/splicing evidence after the baseline branch is identified.
- `tooluniverse-acmg-pm4-bp3-protein-length-refinement` when the event is a protein-length change but LoF is not established.
- `tooluniverse-structural-variant-analysis` for CNV/SV event definition.
