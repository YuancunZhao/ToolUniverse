---
name: tooluniverse-acmg-pvs1-lof-decision-tree-refinement
description: Refine ACMG/AMP PVS1 strength assignment using the ClinGen SVI loss-of-function PVS1 decision tree from Abou Tayoun et al. 2018, PMID 30192042. Use with ToolUniverse ACMG classification before Walker 2023 RNA/splicing refinements when nonsense, frameshift, canonical splice, initiation codon, exon-level deletion/duplication, whole-gene deletion, NMD escape, rescue transcript, or LoF mechanism context affects PVS1 strength.
disable-model-invocation: true
---

# ACMG PVS1 LoF Decision Tree Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence rule: PVS1 strength assignment under the ClinGen SVI loss-of-function decision tree described by Abou Tayoun et al. 2018, PMID:30192042.

Use this as the baseline PVS1 decision tree for predicted loss-of-function variants. Apply Walker et al. 2023 RNA/splicing refinements only after this baseline tree has identified the relevant PVS1 branch or when direct RNA evidence changes the transcript consequence.

This skill is an overlay only. It does not create a new MCP tool and does not replace disease-specific VCEP specifications.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this baseline PVS1 decision tree.

---

## When to Use This Skill

Use this skill when PVS1 is being considered for:

- nonsense or frameshift variants that create a premature termination codon;
- canonical splice donor/acceptor variants, especially +/-1 or +/-2 positions;
- initiation codon or start-loss variants;
- single-exon or multi-exon deletions;
- whole-gene deletions;
- duplications or other copy-number events predicted to disrupt the reading frame or remove critical coding sequence;
- predicted NMD escape, alternative initiation, or rescue transcript scenarios;
- variants in genes with uncertain, mixed, dominant-negative, gain-of-function, or inheritance-specific disease mechanisms.

Do not use this skill as an RNA assay interpretation overlay. If RNA assay evidence is present, first use this skill to define the baseline PVS1 branch for the observed transcript consequence, then use `tooluniverse-acmg-pvs1-splicing-refinement` for Walker 2023 RNA-specific evidence naming, partial splicing, BP7_RNA, and double-counting rules.

---

## Core Principle

PVS1 is valid only when the variant is predicted to cause loss of function and loss of function is an established disease mechanism for the exact gene-disease context.

If the gene has multiple associated disorders, inheritance models, phenotype spectra, dosage states, or molecular mechanisms, first use `tooluniverse-acmg-multiple-disorder-context-refinement` to define the disease entity and evidence-aggregation boundary. Then apply this PVS1 decision tree only to the LoF-compatible target disease context.

Do not apply PVS1 solely because a variant is annotated as stop-gained, frameshift, splice-site, start-loss, or deletion. First confirm:

- the relevant transcript and variant consequence;
- whether the gene-disease mechanism supports LoF/haploinsufficiency for the evaluated inheritance model;
- whether NMD is expected or the transcript is in an NMD-escape branch;
- whether a truncated or altered protein would remove critical functional regions;
- whether alternative initiation or biologically relevant rescue transcripts preserve function;
- whether a VCEP or disease-specific rule supersedes the generic tree.

Output one of: `PVS1`, `PVS1_Strong`, `PVS1_Moderate`, `PVS1_Supporting`, `PVS1_N/A`, or `PVS1_NotAssessed`.

---

## Evidence Retrieval Workflow

Use ToolUniverse tools before assigning PVS1 strength.

1. **Normalize variant and transcript**
   - Use `VariantValidator_validate_variant` and `VariantValidator_gene2transcripts`.
   - Use `EnsemblVEP_annotate_hgvs` and, when available, `ensembl_vep_region` with LoF annotations.
   - Record MANE Select or disease-relevant transcript, HGVS c./p./g., variant class, exon number, CDS coordinate, protein coordinate, predicted PTC, and affected isoform.

2. **Confirm LoF applicability**
   - Use `ClinGen_search_gene_validity`, `ClinGen_search_dosage_sensitivity`, `ClinGen_dosage_by_gene`, `GenCC_search_gene`, `G2P_search`, MedGen/GeneReviews, ClinVar, ClinGen ERepo, PubMed, and Europe PMC.
   - Apply PVS1 only for the exact gene-disease-inheritance context where LoF or haploinsufficiency is established.
   - If mechanism is dominant-negative, antimorphic, gain-of-function, mixed, or unclear, invoke `tooluniverse-acmg-dominant-negative-mechanism-refinement` before assigning PVS1.

3. **Assess NMD and transcript structure**
   - Determine whether the PTC is expected to undergo NMD.
   - Apply the Abou Tayoun et al. 2018 NMD rule: NMD is not predicted when the PTC occurs in the 3' most exon or within the 3' most 50 nucleotides of the penultimate exon.
   - For frameshift variants, use the downstream PTC coordinate, not only the indel start.
   - Treat LoFTEE as supporting annotation, not as a substitute for direct transcript-structure review.

4. **Assess altered protein consequence**
   - Use UniProt, InterPro, EBI Proteins, ProtVar, AlphaFold/PDB, and disease literature to determine whether the truncated or altered protein loses critical residues, domains, active sites, binding regions, or clinically established functional regions.
   - If the altered protein preserves critical function or the affected region is non-critical, downgrade or withhold PVS1.

5. **Assess rescue and alternative transcripts**
   - Identify biologically relevant alternative transcripts, naturally skipped exons, alternative start codons, or tissue-specific isoforms that may preserve critical function.
   - If a rescue transcript preserves the reading frame and critical domains in disease-relevant tissue, reduce strength or use `PVS1_N/A`.

6. **Route CNV/SV evidence**
   - For single-exon, multi-exon, whole-gene, or complex copy-number variants, use `tooluniverse-structural-variant-analysis` for CNV/SV evidence extraction and coordinate review.
   - Use this PVS1 overlay only to assign the LoF evidence strength after the structural event and affected transcript region are known.

7. **Route RNA evidence**
   - If RNA assay evidence, minigene evidence, RT-PCR, transcript diagrams, gels, or Sanger traces define the actual transcript product, use `tooluniverse-literature-deep-research` and `tooluniverse-literature-figure-evidence-extraction` when literature or figures are involved.
   - Then use `tooluniverse-acmg-pvs1-splicing-refinement` for Walker 2023 RNA-specific evidence naming and double-counting rules.

---

## Baseline Decision Tree

### Applicability Gate

Use `PVS1_NotAssessed` when required inputs are missing:

- no disease context;
- no transcript/protein consequence;
- no information about LoF disease mechanism;
- insufficient transcript structure to determine NMD or exon effect.

Use `PVS1_N/A` when:

- LoF is not an established disease mechanism for the evaluated disease;
- the disease mechanism is dominant-negative or gain-of-function only and haploinsufficiency is not established;
- the variant is not predicted to cause LoF after transcript and protein review;
- a rescue transcript or alternative initiation model preserves critical function.

### Gene-Disease LoF Mechanism Strength Gate

Apply the Figure 1 decision-tree strength directly only when the gene-disease pair meets the full LoF mechanism gate from Table 1:

- clinical validity is Strong or Definitive; and
- three or more LoF variants are classified Pathogenic without using PVS1; and
- more than 10% of phenotype-associated pathogenic variants are LoF; and
- qualifying LoF variants are distributed across more than one exon, except for single-exon genes.

Decrease the final Figure 1 strength by one level when:

- clinical validity is at least Moderate; and
- two or more LoF variants have been associated with the phenotype across more than one exon, except for single-exon genes; and
- a null mouse model recapitulates the disease phenotype.

Decrease the final Figure 1 strength by two levels when:

- clinical validity is at least Moderate; and
- either two or more LoF variants have been associated with the phenotype across more than one exon, or a null mouse model recapitulates the disease phenotype.

Use `PVS1_N/A` when there is no evidence that LoF variants cause the disease.

For autosomal dominant disease, do not assume haploinsufficiency from inheritance alone. Use ClinGen HI, constraint, disease literature, and mechanism-specific evidence, then apply `tooluniverse-acmg-dominant-negative-mechanism-refinement` when dominant-negative, gain-of-function, or mixed mechanism is possible.

### Nonsense and Frameshift Variants

Apply `PVS1` when:

- the gene-disease context supports LoF;
- the variant creates a PTC;
- the PTC is predicted to undergo NMD;
- the exon/transcript is biologically relevant;
- no rescue transcript or disease-specific exception weakens the LoF inference.

For variants not predicted to undergo NMD:

- Use `PVS1_Strong` when the truncated or altered region is critical to protein function. A critical region is supported by experimental evidence for the domain/region or by non-truncating pathogenic variants in that region.
- If the region's role is unknown, use `PVS1_N/A` when LoF variants in the exon are frequent in the general population or the exon is absent from biologically relevant transcript(s).
- If the region's role is unknown, LoF variants in the exon are not frequent in the general population, and the exon is present in biologically relevant transcript(s), use `PVS1_Strong` when the variant removes more than 10% of the protein.
- In the same unknown-region branch, use `PVS1_Moderate` when the variant removes less than 10% of the protein.

### Canonical Splice Donor/Acceptor Variants

For canonical +/-1 or +/-2 splice variants:

- Predict the transcript consequence rather than assigning full PVS1 automatically.
- Do not apply PP3 splicing prediction for the same canonical +/-1 or +/-2 splice evidence used for PVS1.
- Confirm there is no detectable nearby +/-20 nucleotide strong consensus splice sequence that may reconstitute in-frame splicing.
- If exon skipping or cryptic splice-site use disrupts the reading frame and is predicted to undergo NMD, use `PVS1` when the exon is present in biologically relevant transcript(s), and `PVS1_N/A` when the exon is absent from biologically relevant transcript(s).
- If exon skipping or cryptic splice-site use disrupts the reading frame and is not predicted to undergo NMD, use the same not-predicted-NMD branch as nonsense/frameshift.
- If exon skipping or cryptic splice-site use preserves the reading frame, use the in-frame branch below.
- If multiple plausible transcript consequences exist, apply the lowest PVS1 strength among plausible scenarios unless RNA evidence resolves the consequence.

Use Walker 2023 RNA/splicing refinement when direct RNA evidence, complex transcript profiles, partial splicing, or BP7_RNA is present.

### Initiation Codon / Start-Loss Variants

For initiation codon variants:

- Use `PVS1_N/A` when a different functional transcript uses an alternative start codon.
- If there is no known alternative start codon in other transcripts, use `PVS1_Moderate` when one or more pathogenic variants are reported upstream of the closest potential in-frame start codon.
- If there is no known alternative start codon in other transcripts, use `PVS1_Supporting` when no pathogenic variants are reported upstream of the closest potential in-frame start codon.
- Do not apply `PVS1` or `PVS1_Strong` to initiation codon variants under the generic 2018 decision tree unless a disease-specific VCEP or expert rule justifies a higher strength.
- Use disease-specific or VCEP rules when available.

### Single-Exon and Multi-Exon Deletions

For exon-level deletions:

- Confirm exact exon boundaries, transcript affected, reading-frame effect, and whether the deleted exon is biologically relevant.
- For single- to multi-exon deletion that disrupts the reading frame and is predicted to undergo NMD, use `PVS1` when the exon is present in biologically relevant transcript(s), and `PVS1_N/A` when the exon is absent from biologically relevant transcript(s).
- For single- to multi-exon deletion that disrupts the reading frame and is not predicted to undergo NMD, use the not-predicted-NMD branch.
- For single- to multi-exon deletion that preserves the reading frame, use the in-frame branch.
- If deletion removes the first exon or promoter/translation start region, assess whether transcript/protein expression is abolished and whether alternative promoters or start codons exist.
- Use structural-variant tools for event definition and this overlay for PVS1 strength.

### Whole-Gene Deletions

Apply PVS1-compatible evidence when:

- the deletion includes the whole gene or a clearly LoF-equivalent event;
- haploinsufficiency/LoF is established for the disease context;
- the CNV call and gene boundaries are reliable.

Do not double count the same whole-gene deletion under both PVS1 and a separate CNV dosage criterion unless the downstream classification framework explicitly supports that evidence split.

### Duplications and Complex Rearrangements

For duplications:

- Do not assume LoF from duplication alone.
- Evaluate duplications only when the event is at least one exon in size and completely contained within the gene.
- Use `PVS1` when the duplication is proven in tandem, the reading frame is disrupted, and NMD is predicted to occur.
- Use `PVS1_Strong` when the duplication is presumed in tandem, the reading frame is presumed disrupted, and NMD is predicted to occur.
- Use `PVS1_N/A` when the duplication is proven not to be in tandem.
- Use `PVS1_N/A` when there is no or unknown impact on reading frame and NMD.
- If duplication length or breakpoints are too uncertain to predict reading-frame impact and NMD, use `PVS1_NotAssessed`.

### In-Frame Deletion/Duplication or Exon Skipping

Use PVS1 only when the in-frame event is predicted or shown to cause loss of function:

- Use `PVS1_Strong` when the event removes an undisputed critical functional domain, active site, required motif, or clinically established critical region.
- If the region's role is unknown, use `PVS1_N/A` when LoF variants in the exon are frequent in the general population or the exon is absent from biologically relevant transcript(s).
- If the region's role is unknown, LoF variants in the exon are not frequent in the general population, and the exon is present in biologically relevant transcript(s), use `PVS1_Strong` when the in-frame event removes more than 10% of the protein.
- In the same unknown-region branch, use `PVS1_Moderate` when the in-frame event removes less than 10% of the protein.
- Use `PVS1_N/A` when critical domains are retained, the event is in a repetitive/non-critical region, or LoF is not established.
- Route ordinary protein-length changes to `tooluniverse-acmg-pm4-bp3-protein-length-refinement` when PVS1 is not justified.

---

## Double-Counting and Routing

- Do not apply PVS1 and PM4 for the same protein-length change unless a VCEP explicitly permits a defined split. Prefer PVS1 only when LoF is established; otherwise route to PM4/BP3.
- Do not use the same RNA assay as both PVS1 and PS3. Use Walker 2023 RNA/splicing refinement for RNA-specific double-counting rules.
- Do not apply ordinary PVS1 in a dominant-negative-only disease mechanism. Use the dominant-negative mechanism overlay first.
- Do not treat PM2 rarity as a reason to upgrade PVS1. PM2 remains separate and defaults to `PM2_Supporting`.
- Do not treat prediction-only splice evidence as RNA assay evidence.

---

## Output Format

```markdown
PVS1 LoF decision tree refinement:
- Variant: [HGVS c./p./g.]
- Transcript: [MANE/disease-relevant transcript]
- Variant class: [nonsense/frameshift/canonical splice/start-loss/exon deletion/whole-gene deletion/duplication/other]
- Gene-disease mechanism: [LoF/HI established / not established / mixed / not assessed]
- PTC/NMD assessment: [NMD expected / NMD escape / not applicable / not assessable]
- Altered protein assessment: [critical region lost / substantial region lost / non-critical region / preserved function / unknown]
- Rescue/alternative transcript assessment: [none found / plausible / established / not assessed]
- CNV/SV routing: [not applicable / structural-variant-analysis used / needed]
- RNA routing: [not applicable / Walker 2023 overlay used / needed]
- Applied evidence: [PVS1 / PVS1_Strong / PVS1_Moderate / PVS1_Supporting / PVS1_N/A / PVS1_NotAssessed]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [LoF decision tree / CNV definition / transcript evidence / none]
- Rationale: [brief explanation with sources]
```

Evidence table row:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PVS1 | Very Strong | Predicted null variant in an established LoF disease gene; PTC is expected to undergo NMD; no rescue transcript or mechanism conflict identified. | Abou Tayoun et al. 2018; PMID:30192042; [tool/database sources] |
```

---

## Tool Parameter Reference

| Tool | Use |
| --- | --- |
| `VariantValidator_validate_variant` | Normalize HGVS and retrieve cDNA/protein consequence. |
| `VariantValidator_gene2transcripts` | Identify MANE Select and clinically relevant transcripts. |
| `EnsemblVEP_annotate_hgvs` | Consequence terms, transcript effects, exon/protein context. |
| `ensembl_vep_region` with LoF annotations when available | LoFTEE and transcript consequence context; not a replacement for the decision tree. |
| `ClinGen_search_gene_validity`, `ClinGen_get_gene_validity` | Gene-disease validity and inheritance. |
| `ClinGen_search_dosage_sensitivity`, `ClinGen_dosage_by_gene` | Haploinsufficiency/dosage evidence for LoF applicability. |
| `GenCC_search_gene`, `G2P_search` | Cross-check disease mechanism and inheritance. |
| `MedGen_search_conditions` | GeneReviews/disease context discovery. |
| `ClinVar_search_variants`, `ClinVar_get_variant`, `ClinGen_get_variant_classifications` | Variant-level curated context and known disease mechanism. |
| `PubMed_search_articles`, `EuropePMC_search_articles` | Literature for mechanism, transcript consequence, functional regions, and VCEP-like rules. |
| `UniProt_get_function_by_accession`, `InterPro_get_entries_for_protein`, `ProtVar_get_function`, `EBIProteins_get_mutagenesis` | Critical domain/residue and altered protein consequence. |
| `alphafold_get_prediction`, PDB/structure tools | Structural context when critical-region loss is uncertain. |
| `tooluniverse-structural-variant-analysis` | CNV/SV event definition before PVS1 strength assignment. |
| `tooluniverse-literature-deep-research`, `tooluniverse-literature-figure-evidence-extraction` | Literature tables/figures, transcript diagrams, exon maps, and visual evidence. |

---

## Limitations

- This overlay summarizes the ClinGen SVI PVS1 decision tree and should be superseded by current disease-specific VCEP specifications.
- This implementation was aligned against PubMed metadata plus the user-provided full-text PDF (`nihms-986839.pdf`) and editable decision-tree PPTX (`clingen_svi_pvs1_decisiontree_editable.pptx`).
- Start-loss, CNV/SV, NMD escape, and in-frame consequences often require transcript-specific or disease-specific evidence.
- This overlay intentionally keeps Walker 2023 RNA/splicing recommendations separate.

---

## Primary Reference

- Abou Tayoun AN, Pesaran T, DiStefano MT, Oza A, Rehm HL, Biesecker LG, Harrison SM. Recommendations for interpreting the loss of function PVS1 ACMG/AMP variant criterion. Human Mutation. 2018;39(11):1517-1524. PMID:30192042. DOI:10.1002/humu.23626.
