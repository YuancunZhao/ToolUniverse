---
name: tooluniverse-acmg-ps3-bs3-functional-assay-refinement
description: Refine ACMG/AMP PS3 and BS3 functional assay evidence using Brnich et al. 2019 ClinGen SVI recommendations. Use with ToolUniverse ACMG variant classification when biochemical, cellular, model-organism, patient-derived, RNA/protein, MAVE/DMS, or other functional assay evidence affects PS3/BS3 strength.
disable-model-invocation: true
---

# ACMG PS3/BS3 Functional Assay Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence area only: PS3 and BS3 functional evidence. It follows the ClinGen Sequence Variant Interpretation recommendations from Brnich et al. 2019 for evaluating functional assay validity and assigning evidence strength.

Use ToolUniverse tools to retrieve variant, gene-disease, assay, and literature evidence. This skill then applies the PS3/BS3 rule refinement inside the ACMG evidence assignment workflow. It does not replace the main ACMG workflow and does not add a new MCP tool.

---

## When to Use This Skill

Use this skill when evidence includes:

- A biochemical, enzymatic, binding, transport, repair, reporter, electrophysiology, localization, abundance, rescue, cellular, model-organism, or other functional assay.
- A multiplexed assay of variant effect, saturation genome editing, deep mutational scanning, or MaveDB-style variant score set.
- Published functional evidence used to argue abnormal function (`PS3`) or preserved/normal function (`BS3`).
- A VCEP-approved or VCEP-discussed functional assay.
- Conflicting functional assays for the same variant.
- A low-throughput historical functional study that may need downgrading.
- A functional assay result that is partial, hypomorphic, intermediate, or outside the calibrated normal/abnormal range.

Do not use this skill for:

- Prediction-only evidence such as REVEL, CADD, AlphaMissense, EVE, SpliceAI, or conservation scores. Use PP3/BP4 pathways instead.
- RNA splicing evidence already assigned through `PVS1_Strength (RNA)` or `BP7_Strong (RNA)` in `tooluniverse-acmg-pvs1-splicing-refinement`.
- Patient phenotype evidence better captured as PP4.
- Population, case-control, segregation, or in-trans evidence unless it is only being used to establish assay controls.

---

## Core Principle

Start from no functional evidence. Increase PS3/BS3 strength only when the assay is biologically applicable to the gene-disease mechanism and the specific assay instance is validated.

Functional evidence should be assigned in four steps:

1. Define the gene-disease mechanism.
2. Evaluate whether the general assay class is applicable to that mechanism.
3. Evaluate the validity of the specific assay instance.
4. Apply PS3 or BS3 to the individual variant result at the justified strength.

The class of assay alone does not determine strength. Strength is determined by validation, controls, reproducibility, calibration, and the variant's result relative to calibrated thresholds.

---

## Evidence Retrieval Workflow

1. **Normalize the variant and consequence**
   - Use `VariantValidator_validate_variant`, `Mutalyzer_normalize_variant`, and `EnsemblVEP_annotate_hgvs`.
   - Record transcript, protein consequence, variant type, and whether the assay context can test that consequence.

2. **Define the gene-disease mechanism**
   - Use `ClinGen_search_gene_validity`, `ClinGen_get_gene_validity`, `GenCC_search_gene`, OMIM/Orphanet-derived evidence, GO/Reactome, UniProt, and disease literature.
   - Record inheritance and mechanism: loss-of-function, gain-of-function, dominant-negative, toxic gain, altered specificity, or unclear.
   - If dominant-negative or antimorphic mechanism may affect which assay readout is relevant, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before assigning PS3/BS3 strength.
   - Do not apply PS3/BS3 if the assay readout is not connected to the disease mechanism.

3. **Retrieve functional evidence**
   - Use `tooluniverse-literature-deep-research` first when evidence comes from papers.
   - When the functional result is shown in a figure, gel, blot, cellular image, assay plot, or supplementary image, use `tooluniverse-literature-figure-evidence-extraction` to extract assay facts, visual observations, labels, controls, and ambiguity notes before assigning PS3/BS3 strength.
   - Use `tooluniverse-image-analysis` when the task requires image-derived measurement statistics, segmentation, fluorescence quantification, cell counts, or analysis of ImageJ/CellProfiler/QuPath outputs.
   - Use `PubMed_search_articles`, `EuropePMC_search_articles`, `EuropePMC_get_full_text`, and `EuropePMC_get_fulltext_snippets` as targeted fallback or supplement.
   - Use `MaveDB_search_score_sets`, `MaveDB_get_score_set`, `MaveDB_get_variant_scores`, and `MaveDB_get_effect_matrix` for multiplexed functional assays.
   - Use UniProt, InterPro, AlphaFold, PDB, and pathway tools when the assay result depends on protein region, domain, or pathway context.

4. **Identify VCEP-specific assay rules**
   - Search current ClinGen/VCEP specifications when available.
   - VCEP rules supersede this generic overlay, especially for approved assays, control counts, thresholds, assay-specific caps, and whether a given readout can support BS3.

5. **Evaluate assay-level validity**
   - Confirm negative or wild-type controls and positive or abnormal/null controls.
   - Confirm technical and/or biological replicates.
   - Count validation controls with independent benign/likely benign and pathogenic/likely pathogenic classifications.
   - Determine whether thresholds for normal, abnormal, and indeterminate readouts are defined.
   - Determine whether the assay has formal statistical calibration, sensitivity/specificity, positive predictive value, or OddsPath.

6. **Apply variant-level evidence**
   - Apply `PS3` if the variant result is functionally abnormal and consistent with the disease mechanism.
   - Apply `BS3` if the variant result is functionally normal and the assay captures the relevant molecular consequence well enough to support a benign inference.
   - Withhold PS3/BS3 for indeterminate, discordant, or mechanistically irrelevant results.

---

## Literature-Assisted Workflow

When PS3/BS3 evidence comes from papers, use `tooluniverse-literature-deep-research` or an equivalent ToolUniverse literature-reading skill first. The literature step should extract assay facts; this PS3/BS3 refinement should assign evidence strength.

Recommended sequence:

1. Search by gene, disease, variant, assay name, and functional keywords.
2. Retrieve full text and supplement when available.
3. Extract the assay-level schema below.
4. Normalize the assessed variant and any control variants.
5. Verify that control variant classifications do not rely on the same assay being calibrated.
6. Apply the four-step SVI framework and the strength rules below.
7. Report the final PS3/BS3 assignment and the reason any same-source evidence was not double-counted.

Minimum assay evidence schema:

| Field | Required content |
|-------|------------------|
| `source` | PMID, DOI, PMCID, MaveDB URN, VCEP document, or report identifier. |
| `assessed_variant` | HGVS/genomic/protein notation and transcript/protein reference. |
| `gene_disease_context` | Gene, disease, inheritance, and disease mechanism. |
| `assay_class` | General class: enzyme activity, reporter, rescue, cellular model, MAVE, splicing assay, etc. |
| `specific_assay_instance` | Laboratory, construct/model, protocol, publication, kit, or score set. |
| `model_system` | Patient-derived material, endogenous genome editing, cDNA overexpression, cell line, organism, in vitro system, etc. |
| `readout` | Quantitative or qualitative readout, units, direction of abnormality, and measured function. |
| `mechanism_match` | Whether the readout models the relevant disease mechanism. |
| `experimental_controls` | Wild-type/normal and abnormal/null controls. |
| `replicates` | Technical and/or biological replicates. |
| `validation_controls` | Number and identity of known benign/LB and pathogenic/LP variant controls. |
| `thresholds` | Normal, abnormal, and indeterminate ranges. |
| `calibration` | Statistical analysis, sensitivity/specificity, OddsPath, VCEP calibration, or no formal analysis. |
| `variant_result` | The assessed variant's readout and category: abnormal, normal, intermediate, indeterminate, or conflicting. |
| `conflicts` | Other assays or evidence that conflict with the result. |
| `double_counting_notes` | Evidence codes that must not also use the same functional data. |

If the literature step cannot fill the required fields, return `PS3/BS3 not assessable` rather than guessing.

---

## Strength Assignment Rules

### No PS3/BS3

Do not apply PS3/BS3 unless an exception is justified by a VCEP or by extremely well-understood dynamic range and thresholds, when:

- The assay lacks both wild-type/normal and abnormal/null controls.
- The assay lacks technical and/or biological replicates.
- The disease mechanism is unclear or the assay does not test it.
- The variant result is indeterminate.
- The assay context cannot test the relevant molecular consequence, such as a cDNA assay used to infer splicing impact.
- A normal result only shows that one limited readout is preserved, while other disease-relevant functions are not tested.

### Supporting

Apply `PS3_Supporting` or `BS3_Supporting` when:

- The assay has experimental controls and replicates, but has 10 or fewer validation controls for distinguishing pathogenic from benign variants.
- Or the assay class is historically accepted, previously validated, or available as a kit with defined performance characteristics, but the specific assay instance does not document controls and replicates.

Historical publications that are rigorous and include appropriate laboratory controls may usually reach supporting evidence, but should not be treated as strong evidence without validation.

### Moderate

Apply `PS3_Moderate` or `BS3_Moderate` when:

- The assay includes at least 11 total validation controls.
- The controls include a mix of benign/LB and pathogenic/LP variants.
- No formal statistical analysis is available, but thresholds for abnormal, normal, and indeterminate results are sufficiently defined.

`BS3_Moderate` is a moderate-equivalent benign strength from the SVI/Bayesian framework. If the local ACMG combiner does not support moderate benign criteria, report it as two supporting-equivalent benign contributions or follow the current VCEP/local combiner policy.

### Calibrated OddsPath

When rigorous statistical analysis enables formal OddsPath calculation, assign strength by OddsPath:

| OddsPath | Evidence strength |
|----------|-------------------|
| `< 0.053` | `BS3` |
| `< 0.23` | `BS3_Moderate` equivalent |
| `< 0.48` | `BS3_Supporting` |
| `0.48-2.1` | Indeterminate |
| `> 2.1` | `PS3_Supporting` |
| `> 4.3` | `PS3_Moderate` |
| `> 18.7` | `PS3` |
| `> 350` | `PS3_VeryStrong`, only if the local framework or VCEP permits very-strong PS3 |

Functional evidence is not stand-alone evidence for a final Pathogenic or Benign classification. Even highly calibrated functional evidence must be combined with other independent evidence.

---

## Variant Result Interpretation

- Functionally abnormal result consistent with the disease mechanism: apply PS3 at the assay-validated strength.
- Functionally normal result in an assay that captures the relevant mechanism: apply BS3 at the assay-validated strength.
- Intermediate or hypomorphic result: compare against calibrated pathogenic, benign, and indeterminate ranges. Do not force PS3 or BS3 if the result falls between validated thresholds.
- Partial loss of function: use the disease mechanism and control distribution. A partial effect may support PS3 at reduced strength, be indeterminate, or support a phenotype-specific mechanism.
- Normal result from a limited assay: reduce BS3 strength or withhold BS3 if the assay does not test the relevant domain, pathway, isoform, splicing consequence, or full protein function.
- Normal variant-only protein function does not exclude a dominant-negative mechanism. For suspected dominant-negative disease, BS3 generally requires WT+variant co-expression, heterozygous/endogenous context, complex assembly, or another assay that can test dominant interference.
- Patient-derived functional data: prefer PP4/phenotype use when it reflects organismal phenotype rather than isolated variant function. If used for PS3/BS3, strength still depends on validation parameters and disease-specific guidance.
- Model-organism evidence: consider organism relevance, genetic background, orthology, phenotype fidelity, and reproducibility. Adjust strength based on rigor and validation.
- cDNA overexpression assays: may reasonably test protein-level effects for missense or in-frame variants, but usually cannot test splicing or NMD-sensitive consequences.

---

## Multiple Assays and Conflicts

- If multiple assays are concordant, apply the strength justified by the most well-validated assay that best measures the disease mechanism.
- If assays conflict, the assay that better reflects the disease mechanism and is better validated can override the weaker assay.
- If conflicting assays have similar relevance and validation, do not apply PS3 or BS3 from the conflicting functional evidence.
- Do not automatically stack two supporting functional assays to create `PS3_Moderate` or `BS3_Moderate`. The SVI group did not reach consensus on stacking different assay classes because independence is difficult to prove and double counting is likely.
- If a VCEP explicitly permits combining independent functional assays, follow that VCEP rule and document why the assays are independent.

---

## Double-Counting Boundaries

- RNA splicing assay evidence used for `PVS1_Strength (RNA)` or `BP7_Strong (RNA)` should not also be counted as PS3/BS3.
- Functional assay evidence should not also be counted as PP3/BP4 prediction evidence.
- MAVE/DMS assay scores used as PS3/BS3 should not also be treated as a computational predictor for PP3/BP4.
- Functional evidence used to calibrate the assay should not also be reused as independent variant evidence for the same assertion.
- Patient phenotype data used as PP4 should not be double-counted as PS3 unless the assay independently measures variant-level function and satisfies PS3/BS3 validation.
- Domain or mechanism evidence used for PM1 can coexist with PS3 only when PM1 is based on independent regional/domain enrichment rather than the same functional assay.

---

## VCEP and Disease-Specific Rules

Current VCEP specifications supersede this generic overlay. Follow VCEP rules when they define:

- Approved functional assays for a gene/disease.
- Assay-specific thresholds and readout ranges.
- Strength caps for model systems, cDNA constructs, mini-gene assays, or patient-derived samples.
- Control variant requirements.
- How to treat MAVE/DMS score sets.
- Whether benign functional evidence can be applied at supporting, moderate-equivalent, or strong levels.
- How to combine or resolve multiple functional assays.

Always cite the VCEP when it changes the default Brnich/SVI assignment.

---

## Output Format

Report PS3/BS3 evidence transparently:

```markdown
PS3/BS3 functional assay refinement:
- Gene-disease mechanism: [LoF / GoF / dominant-negative / other], source [ClinGen/VCEP/literature]
- Assay class and instance: [assay], [source]
- Mechanism match: [yes/no/partial], rationale [short]
- Model system: [patient-derived/endogenous/cDNA/cell/model organism/in vitro/MAVE]
- Controls and replicates: [wild-type/normal], [abnormal/null], [technical/biological replicates]
- Validation controls: [# P/LP], [# B/LB], total [#], classification independence [checked/not checked]
- Thresholds/calibration: [normal/abnormal/indeterminate ranges, OddsPath if available]
- Variant result: [readout], [abnormal/normal/intermediate/indeterminate/conflicting]
- Multiple assay handling: [most validated assay / conflict resolved / no functional code]
- Double counting: [PS3/BS3 replaces same-source PP3/BP4 or PVS1/BP7 RNA use where relevant]
- Applied evidence: [PS3_Supporting / PS3_Moderate / PS3 / PS3_VeryStrong / BS3_Supporting / BS3_Moderate / BS3 / No PS3/BS3]
```

Example evidence table row:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PS3 | Moderate | Variant shows abnormal activity in an assay with wild-type and null controls, replicates, and 11 mixed P/LP and B/LB validation controls; no formal OddsPath calculation was reported. | Brnich et al. 2019 ClinGen SVI; [primary assay source] |
```

---

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `tooluniverse-literature-deep-research` | First-pass extraction of assay facts from functional evidence papers. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Find functional assay publications and VCEP assay specifications. |
| `EuropePMC_get_full_text` / `EuropePMC_get_fulltext_snippets` | Retrieve full text and targeted assay-validation passages. |
| `VariantValidator_validate_variant` / `Mutalyzer_normalize_variant` | Normalize the assessed variant and control variants. |
| `EnsemblVEP_annotate_hgvs` | Confirm consequence, transcript, and whether the assay can test the molecular consequence. |
| `ClinGen_search_gene_validity` / `ClinGen_get_gene_validity` | Gene-disease validity, inheritance, and disease mechanism. |
| `GenCC_search_gene` | Cross-check gene-disease relationship and inheritance. |
| `MaveDB_search_score_sets` / `MaveDB_get_score_set` | Find and inspect MAVE/DMS score sets. |
| `MaveDB_get_variant_scores` / `MaveDB_get_effect_matrix` | Retrieve variant-level functional scores and score matrices. |
| `UniProt_get_entry_by_accession` / InterPro tools | Protein function, domains, isoforms, and functional-region context. |
| `Reactome` / GO tools | Pathway and biological-process context for mechanism matching. |
| `AlphaFold` / PDB tools | Structural context when the assay or domain effect depends on structure. |

---

## Limitations

- This overlay is rule guidance, not an automated assay validator.
- Published functional evidence often lacks enough controls to support strong evidence.
- BS3 requires extra care: a normal result must test the disease-relevant function, not merely one narrow assay readout.
- Control variant classifications must be independent of the assay being calibrated.
- The SVI framework is provisional and VCEP-specific specifications may override it.

---

## Primary Reference

- Brnich SE, Abou Tayoun AN, Couch FJ, Cutting GR, Greenblatt MS, Heinen CD, Kanavy DM, Luo X, McNulty SM, Starita LM, Tavtigian SV, Wright MW, Harrison SM, Biesecker LG, Berg JS. Recommendations for application of the functional evidence PS3/BS3 criterion using the ACMG/AMP sequence variant interpretation framework. Genome Medicine. 2019;12:3. PMID: 31892348. PMCID: PMC6938631. DOI: 10.1186/s13073-019-0690-2.
