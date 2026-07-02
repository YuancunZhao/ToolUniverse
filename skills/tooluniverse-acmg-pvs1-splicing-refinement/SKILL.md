---
name: tooluniverse-acmg-pvs1-splicing-refinement
description: Refine ACMG/AMP PVS1/BP7 assignment for RNA splicing evidence using Walker et al. 2023 ClinGen SVI Splicing Subgroup guidance. Use after the baseline Abou Tayoun et al. 2018 PVS1 LoF decision-tree overlay when RNA assay, published RNA-splicing evidence, rescue transcript model, in-frame exon skipping, partial splicing, complex aberrant transcript profiles, or detailed splice-impact evidence affects PVS1/BP7 assignment.
disable-model-invocation: true
---

> ⚠️ **DEPRECATED for direct LLM use.** This SKILL.md is reference documentation only.
> **ALWAYS call the corresponding MCP tool instead** — it is deterministic (same input = same output).
> Do NOT manually interpret ACMG decision trees from this document.
> If you cannot find the MCP tool, call  first to get the list.


# ACMG PVS1 Splicing Refinement

This skill extends `tooluniverse-acmg-variant-classification` for PVS1/BP7 assignment when RNA-splicing evidence is relevant. It uses the Walker et al. 2023 ClinGen SVI Splicing Subgroup recommendations to interpret RNA-splicing assay evidence, rescue transcript models, in-frame transcript effects, and double-counting boundaries with PS3/BS3 and PP3/BP4.

This skill does not replace the baseline PVS1 loss-of-function decision tree. Use `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` first for Abou Tayoun et al. 2018 PVS1 branches such as nonsense, frameshift, canonical splice prediction, start-loss, exon deletion/duplication, whole-gene deletion, NMD escape, alternative initiation, and LoF mechanism applicability. Then use this Walker 2023 RNA/splicing overlay when direct RNA evidence or detailed splicing interpretation changes the branch, evidence label, or double-counting behavior.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this RNA/splicing-specific logic.

---

## When to Use This Skill

Use this skill when any of the following are present:

- RNA assay evidence for altered or normal splicing.
- Published RNA-splicing evidence in PubMed, Europe PMC, or ClinVar/ClinGen curation.
- Canonical splice donor/acceptor variants needing refined PVS1 strength.
- Predicted or observed exon skipping, pseudoexon inclusion, intron retention, partial splicing, or complex aberrant transcript profiles.
- In-frame exon skipping where critical residue/domain retention changes PVS1 strength.
- Possible rescue transcripts or alternative transcripts that may preserve functional protein.
- Nonsense, frameshift, or splice-derived premature termination variants only when RNA evidence or detailed splicing evidence changes the transcript consequence already assessed by the baseline PVS1 LoF decision tree.
- User-supplied, DECIPHER-derived, or transcript-model-derived predicted NMD escape evidence only when connected to RNA/splicing interpretation; otherwise use the baseline PVS1 LoF decision tree overlay.
- Need to decide whether RNA-splicing evidence should be captured as `PVS1_Strength (RNA)`, `BP7_Strong (RNA)`, or explanatory text.

Do not use this skill to refine unrelated ACMG evidence criteria. PS3/BS3, PP3/BP4, BA1/BS1/PM2, PM1, PS1, and PM5 should only be refined here when required to avoid double counting splicing evidence.

---

## Core Principle

RNA-splicing assay data that directly demonstrate a loss-of-function transcript should be captured through `PVS1_Strength (RNA)`, not through PS3. RNA-splicing assay data demonstrating no splicing impact should be captured through `BP7_Strong (RNA)` when appropriate, not through BS3. Prediction-only evidence remains separate and should not be treated as RNA assay evidence.

---

## Evidence Retrieval Workflow

Use English queries and database-verified evidence.

1. **Normalize the variant and transcript**
   - Use `VariantValidator_gene2transcripts` to identify MANE Select and relevant clinical transcripts.
   - Use `VariantValidator_validate_variant` to confirm HGVS c./p./g. notation and transcript consequence.
   - Record exon/intron position, canonical splice status, coding consequence, and affected transcript.

2. **Annotate splicing consequence**
   - Use `EnsemblVEP_annotate_hgvs` for consequence terms and transcript context.
   - Use `ensembl_vep_region` with `LoF=1` when available to retrieve LoFTEE fields, but treat LoFTEE as auxiliary annotation rather than a substitute for the baseline PVS1 LoF decision tree.
   - Use `SpliceAI_predict_splice` or `SpliceAI_get_max_delta` for prediction-only evidence.
   - Treat SpliceAI as prediction evidence, not as RNA assay evidence.

3. **Confirm LoF disease mechanism**
   - Use `ClinGen_search_gene_validity`, OMIM/GenCC/Orphanet-derived evidence when available, and disease-specific literature.
   - Apply PVS1 only when LoF is an established or well-supported disease mechanism for the gene-disease context.
   - If the disease mechanism may be dominant-negative, antimorphic, or mixed by variant class, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before applying PVS1. Do not treat a dominant-negative disease mechanism as ordinary haploinsufficiency.

4. **Import the baseline PVS1 branch**
   - Use `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` to determine whether the baseline branch is `PVS1`, `PVS1_Strong`, `PVS1_Moderate`, `PVS1_Supporting`, `PVS1_N/A`, or `status: not_assessed`.
   - If the RNA assay shows a transcript product that differs from the predicted DNA consequence, re-enter the baseline LoF decision tree using the observed transcript product.
   - Apply NMD escape rules through the baseline overlay unless RNA evidence specifically changes the transcript consequence.
   - Use existing ToolUniverse tools rather than a dedicated DECIPHER scraper: `VariantValidator_validate_variant` for normalized c./p./g. consequence and PTC position; `EnsemblVEP_annotate_hgvs` or `ensembl_vep_region` for transcript consequence, exon/intron fields, and LoFTEE context; Ensembl transcript lookup/overlap tools for exon/CDS structure when VEP output does not provide enough detail.

5. **Retrieve RNA-splicing evidence**
   - Use `PubMed_search_articles` and `EuropePMC_search_articles` with queries combining gene, variant notation, "RNA", "splicing", "RT-PCR", "minigene", "transcript", "exon skipping", or "pseudoexon".
   - If RNA evidence is from a paper, capture assay type, sample/source, observed transcript products, estimated abundance if reported, and whether normal controls or known controls were used.
   - When RNA evidence is shown in a figure, gel, Sanger trace, minigene panel, RT-PCR panel, or transcript schematic, use `tooluniverse-literature-figure-evidence-extraction` to extract the visual transcript evidence before applying `PVS1_Strength (RNA)` or `BP7_Strong (RNA)`.

6. **Assess protein consequences of observed RNA products**
   - Determine whether the RNA product is out-of-frame, introduces a premature termination codon, is predicted to undergo NMD, removes initiation codon, disrupts a canonical transcript, or produces an in-frame protein alteration.
   - For in-frame products, use UniProt, InterPro, Pfam-equivalent annotations, AlphaFold/PDB structural context, and known clinically important residues/domains to judge whether critical protein function is lost or retained.

7. **Assess rescue transcript model**
   - Identify physiologic alternative transcripts that naturally exclude the affected exon or otherwise avoid the variant effect.
   - A plausible rescue transcript must preserve reading frame and critical protein domains. Tissue expression is helpful; Walker et al. propose 10% of overall gene expression as a conservative operational threshold when gene-specific data are unavailable.
   - If a plausible rescue model exists, reduce PVS1 strength or withhold PVS1 as described below.

---

## PVS1 Strength Refinement Rules

### Apply PVS1_Strength (RNA)

Apply `PVS1_Strength (RNA)` when RNA assay evidence shows aberrant transcript(s) that can be evaluated through a PVS1 decision tree and the gene-disease mechanism supports LoF.

Use the observed RNA product, not only the DNA consequence, to choose strength:

- **Out-of-frame exon skipping, frameshifted transcript, intron retention, or pseudoexon inclusion with premature termination and expected NMD**: apply the PVS1 strength that would apply to an equivalent LoF transcript in that gene and transcript context.
- **Complete or near-complete aberrant splicing**: use the RNA result as the primary splicing evidence. Strength depends on PVS1 decision-tree context, gene mechanism, NMD/rescue transcript status, and critical region retention.
- **Partial aberrant splicing**: reduce strength unless a disease/gene-specific threshold justifies the full weight. If multiple transcript products are observed, use the most conservative applicable PVS1 strength supported by the assay.
- **In-frame exon skipping or in-frame deletion/insertion from splicing**: evaluate whether the resulting protein loses undisputed clinically relevant residues, known critical domains, or established functional regions.
- **In-frame event removing undisputed clinically relevant residues**: PVS1 may reach very strong evidence, but reduce strength when structural features, alteration size/location, or retained domain function weaken the LoF inference.
- **In-frame event outside known critical regions or retaining key functional domains**: reduce PVS1 substantially or do not apply PVS1 if LoF is not demonstrated.

### Withhold or Reduce PVS1

Do not automatically apply high PVS1 strength when any of the following apply:

- LoF is not an established disease mechanism for the gene-disease context.
- The relevant disease is established as dominant-negative and haploinsufficiency/LoF is not established for the same disease context.
- RNA impact is limited, mixed, or not clearly disease-relevant.
- The baseline LoF decision tree or another transcript-specific source predicts NMD escape and the truncated protein consequences have not been shown to cause LoF at full PVS1 strength.
- The RNA assay is not interpretable for the relevant tissue/transcript or does not resolve the clinically relevant isoform.
- The variant affects a non-constitutive exon and a plausible rescue transcript preserves reading frame and critical domains.
- The observed in-frame transcript is compatible with retained protein function.
- The assay shows complex aberrant profiles and the proportion of LoF transcript is unclear.

When a plausible rescue transcript model is present, use reduced PVS1 strength or `PVS1_N/A` rather than full PVS1. Record the transcript evidence and why the rescue model changes the strength.

When a predicted NMD escape region is present, report the baseline LoF decision-tree result explicitly and separate three questions: (1) whether NMD is expected, (2) whether any translated truncated product would lose critical protein function, and (3) whether the gene-disease mechanism supports LoF for the evaluated inheritance model. Do not collapse these into a single "nonsense = PVS1 Very Strong" statement.

---

## BP7_Strong (RNA) Rules

Apply `BP7_Strong (RNA)` when experimental RNA-splicing data demonstrate no splicing impact and the variant type/context is appropriate.

Use `BP7_Strong (RNA)` for:

- Synonymous variants with RNA assay evidence showing no splicing impact, when no other coding mechanism needs classification.
- Intronic/non-coding variants with RNA assay evidence showing no splicing impact.
- Coding variants only when other possible protein-level consequences have also been excluded or are not clinically relevant.

Do not apply `BP7_Strong (RNA)` for missense or in-frame coding variants solely because splicing is normal. In those cases, record the RNA result as explanatory text and classify the protein consequence separately. If protein functional impact is also excluded, `BP7_Strong (RNA)` may be used to track the RNA evidence.

---

## Prediction-Only Evidence Boundary

SpliceAI and other splice predictors are not RNA assay evidence.

- Use prediction-only evidence for PP3/BP4-style splicing support when RNA assay data are absent.
- Do not convert a high SpliceAI score alone into `PVS1_Strength (RNA)`.
- Do not apply PP3 together with PVS1 for the same splicing mechanism when RNA data already justify PVS1.
- Walker et al. used SpliceAI max delta score >= 0.2 as an example threshold supporting spliceogenicity and <= 0.1 as an example threshold supporting non-spliceogenicity for variants outside donor/acceptor +/-1,2 dinucleotides. Treat these as splicing-prediction guidance and refine with disease/gene-specific VCEP rules when available.

---

## Double-Counting Rules

- RNA-splicing assay evidence used for `PVS1_Strength (RNA)` replaces splicing-use of PS3.
- RNA-splicing assay evidence showing no splicing impact and used for `BP7_Strong (RNA)` replaces splicing-use of BS3.
- If RNA evidence is used to designate a variant as LoF through PVS1, remove PP3/BP4 codes based on the same splicing mechanism.
- If the variant has both a splicing mechanism and an independent protein mechanism, evaluate those mechanisms separately and use the most deleterious supported classification path.
- Do not count the same RNA assay result twice under both a splicing code and a protein functional code.

---

## Interaction with PS1-Splicing Similarity

Evaluate direct RNA evidence for the variant under assessment before applying PS1 based on similarity to a known spliceogenic variant:

- If the VUA RNA assay shows LoF transcript(s), assign `PVS1_Strength (RNA)` first.
- If the VUA RNA assay shows no splicing impact and BP7 conditions are met, assign `BP7_Strong (RNA)` and do not apply PS1-splicing for a predicted splice event contradicted by RNA.
- If the VUA RNA result differs from the predicted event used for PS1-splicing, or differs from the comparison variant's event, the observed RNA result supersedes the prediction and PS1-splicing should be withheld.
- If RNA shows partial, tissue-limited, or complex transcript profiles, do not assume same-event PS1. Require explicit matching of the clinically relevant observed transcript effect and consider abundance, NMD, rescue, and domain context.
- Do not use PP3 when RNA evidence already supplies `PVS1_Strength (RNA)` for the same splicing mechanism.
- PS1-splicing may coexist with `PVS1_Strength (RNA)` only when the comparison variant's pathogenic or likely pathogenic classification is independent of the VUA RNA assay, the same case, the same family, the same experimental observation, and any circular inference chain.
- If the comparison variant's classification depends on the VUA, the same unpublished RNA observation, or reciprocal use of the current variant, withhold PS1-splicing unless a current VCEP rule explicitly permits a different handling.
- Report the evidence split explicitly: direct RNA evidence supports PVS1/BP7; independent comparison-variant same-event evidence supports PS1.

Use `tooluniverse-acmg-ps1-splicing-similarity-refinement` after this RNA-first step when same-event comparison evidence remains eligible.

---

## Output Format

Report the refined evidence as part of the ACMG evidence table:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PVS1_Strength (RNA) | [Very Strong/Strong/Moderate/Supporting] | RNA assay shows [observed transcript effect]; interpreted through PVS1 decision tree with [NMD/rescue/domain context]. | Walker et al. 2023; PMID:37352859; [primary RNA source] |
```

For no-splicing-impact RNA evidence:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| BP7_Strong (RNA) | Strong | RNA assay shows no splicing impact for [synonymous/intronic/non-coding] variant; no separate coding consequence requires classification. | Walker et al. 2023; PMID:37352859; [primary RNA source] |
```

Always state which prediction codes were not applied to avoid double counting. If PS1-splicing similarity was considered, also state whether it was not assessed, withheld because direct RNA contradicted the predicted event, or applied using independent comparison-variant evidence.

Also include a routing-core summary:

```markdown
PVS1 splicing refinement:
- Applied evidence: [PVS1_Strength (RNA) / BP7_Strong (RNA) / PVS1_N/A / no splicing evidence]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [RNA assay / published RNA evidence / prediction only / none]
- Routed to: [PS1-splicing / PS3-BS3 / none]
```

---

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `VariantValidator_gene2transcripts` | Identify MANE Select and clinically relevant transcripts. |
| `VariantValidator_validate_variant` | Validate HGVS and transcript/protein/genomic consequences. |
| `EnsemblVEP_annotate_hgvs` | Retrieve consequence and transcript context. |
| `ensembl_vep_region` with `LoF=1` | Retrieve transcript consequence, exon/intron fields, and LoFTEE context; LoFTEE does not replace the baseline PVS1 LoF decision tree. |
| `SpliceAI_predict_splice` / `SpliceAI_get_max_delta` | Prediction-only splice evidence; not RNA assay evidence. |
| `MyVariant_query_variants` | Aggregated variant annotation, ClinVar, gnomAD, CADD/dbNSFP fields. |
| `ClinGen_search_gene_validity` | Gene-disease validity and disease mechanism context. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | RNA assay and splicing literature retrieval. |
| `UniProt_get_function_by_accession` | Protein function, sites, and domain context. |
| `InterPro_get_entries_for_protein` | Domain architecture relevant to in-frame transcript effects. |
| `alphafold_get_prediction` | Structural confidence/context when domain retention is unclear. |

---

## Limitations

- This skill is a rule-refinement layer, not a new deterministic MCP tool.
- Gene-specific VCEP specifications should supersede generic guidance when available and current.
- This skill intentionally avoids adding a DECIPHER-specific scraper. Apply baseline NMD escape rules through `tooluniverse-acmg-pvs1-lof-decision-tree-refinement`; DECIPHER page or screenshot evidence is optional supporting provenance, not the primary automation layer.
- PVS1 strength for partial splicing, complex transcript profiles, and in-frame events may require gene-specific domain maps or assay calibration.
- RNA source, assay design, transcript expression, and control validation can change evidence weight.
- This skill intentionally does not refine unrelated ACMG criteria beyond avoiding splicing-evidence double counting.

---

## Primary References

- Abou Tayoun AN, Pesaran T, DiStefano MT, Oza A, Rehm HL, Biesecker LG, Harrison SM. Recommendations for interpreting the loss of function PVS1 ACMG/AMP variant criterion. Human Mutation. 2018;39(11):1517-1524. PMID:30192042. DOI:10.1002/humu.23626. Use through `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` as the baseline PVS1 decision tree.
- Walker LC, de la Hoya M, Wiggins GAR, et al. Using the ACMG/AMP framework to capture evidence related to predicted and observed impact on splicing: Recommendations from the ClinGen SVI Splicing Subgroup. Am J Hum Genet. 2023;110(7):1046-1067. PMID: 37352859. DOI: 10.1016/j.ajhg.2023.06.002.
- Supplemental information: Document S1 (Figures S1-S5 and Box S1), Data S1 (Tables S1-S13), and Document S2 (article plus supplement), linked from PMC10357475.
