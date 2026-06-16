---
name: tooluniverse-acmg-ps1-splicing-similarity-refinement
description: Refine ACMG/AMP PS1 evidence for variants with the same predicted RNA-splicing impact as a known pathogenic or likely pathogenic variant, based on Walker et al. 2023 ClinGen SVI Splicing Subgroup Table 2. Use with ToolUniverse ACMG variant classification when splicing prediction similarity, donor/acceptor motif position, or splice-event matching affects PS1 strength.
disable-model-invocation: true
---

# ACMG PS1 Splicing Similarity Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence rule only: PS1 when the evidence is similarity of predicted RNA-splicing impact to a known pathogenic or likely pathogenic variant. It follows Walker et al. 2023 ClinGen SVI Splicing Subgroup guidance, especially the PS1 splicing adaptation in Table 2.

This is a PS1 overlay, not a PVS1 overlay. It can interact with PVS1 because canonical splice donor/acceptor variants often have a PVS1 baseline, but the PS1 evidence here is the comparison to another classified variant with the same predicted splicing event.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this PS1-splicing comparison logic.

---

## When to Use This Skill

Use this skill when all are relevant:

- The variant under assessment (VUA) has predicted splice impact.
- A known pathogenic or likely pathogenic comparison variant exists in the same splice donor or acceptor context.
- The VUA and comparison variant are predicted to produce the same RNA-splicing event.
- The VUA has an applicable baseline splicing prediction code, usually PP3 or PVS1/PVS1_Strength.
- You need to decide whether PS1, PS1_Moderate, PS1_Supporting, or no PS1 applies.

Use this for:

- Intronic or exonic variants outside donor/acceptor +/-1,2 dinucleotides with PP3-level splicing prediction evidence.
- Canonical donor/acceptor +/-1,2 variants with PVS1 or downgraded PVS1 strength.
- Different nucleotide substitutions at the same splice-relevant nucleotide.
- Different nucleotide positions within the same donor or acceptor motif, when the predicted event precisely matches.

Do not use this skill for:

- Ordinary missense PS1 based on the same amino-acid substitution. Use standard PS1 logic for that.
- PM5-style residue or splice-site similarity without a precise predicted RNA-event match.
- Variants without an established P/LP comparison variant.
- Variants where the VUA prediction is weaker than the comparison variant's prediction.
- Non-splice donor/acceptor region variants where abnormal splicing is only a speculative mechanism.

---

## Core Principle

Walker et al. adapt PS1 from "same amino acid change as a previously established pathogenic variant" to "same predicted splicing impact as a previously classified pathogenic or likely pathogenic variant."

The logic is mechanism matching: if the VUA and a known P/LP comparison variant are predicted to cause the same splice event with similar or stronger predicted impact, the clinical evidence supporting the comparison variant can support the VUA through PS1 at a calibrated strength.

PM5 should not be used for splicing prediction similarity in this framework. Use PS1 only when the predicted event precisely matches.

---

## Required Preconditions

All preconditions must be satisfied before assigning PS1-splicing evidence:

1. **Same predicted splicing event**
   - The VUA and comparison variant must be predicted to produce the same RNA event.
   - Examples: both cause the same exon skipping event; both enhance the same cryptic donor/acceptor motif; both disrupt the same native donor/acceptor motif with comparable predicted consequence.

2. **Prediction strength is similar or stronger for the VUA**
   - The VUA's predicted splice impact must be similar to or stronger than the comparison variant's prediction.
   - Use the same prediction framework where possible, preferably calibrated SpliceAI/Pangolin or VCEP-specified tools.

3. **Comparison variant is clinically supported**
   - The comparison variant must be Pathogenic or Likely Pathogenic with clinical or literature support.
   - Prefer ClinGen Expert Panel or VCEP-curated classifications.
   - ClinVar-only evidence should be reviewed for stars, submitter conflict, and whether evidence criteria are available.

4. **Same transcript and same splice context**
   - Compare variants on the same reference transcript used for curation.
   - For GT-AG introns, Walker et al. define the donor motif as the last 3 exonic bases and the first 6 intronic bases, and the acceptor motif as the first exonic base and the 20 intronic bases upstream of the exon boundary.
   - For non-GT-AG introns, use motif ranges appropriate to that intron or VCEP guidance.

5. **Protein effect check for exonic variants**
   - For exonic VUAs or comparison variants, review the predicted or proven protein effect of any encoded missense or in-frame change before applying PS1-splicing.
   - If two substitutions both alter splicing but retain different nucleotide sequence in mRNA, codon/protein consequences may differ. Confirm that the pathogenic mechanism is truly the same.
   - If the gene-disease context may involve dominant-negative, antimorphic, or mixed protein mechanisms, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before transferring PS1/PM5-style evidence between comparison variants.

6. **VUA has baseline splicing evidence**
   - The VUA should already have PP3 or PVS1/PVS1_Strength evidence relevant to splicing.
   - Do not use PS1-splicing as the first and only indication that the VUA affects splicing.

---

## Evidence Retrieval Workflow

1. **Normalize and anchor the VUA**
   - Use `VariantValidator_validate_variant` or `Mutalyzer_normalize_variant`.
   - Use `VariantValidator_gene2transcripts` and `EnsemblVEP_annotate_hgvs` to confirm transcript, exon/intron boundary, coding consequence, and whether the VUA lies inside donor/acceptor +/-1,2 or outside it.

2. **Predict splice effect for the VUA**
   - Use `SpliceAI_predict_splice`, `SpliceAI_get_max_delta`, and optionally `SpliceAI_predict_pangolin`.
   - Record delta score type, affected donor/acceptor, predicted exon skipping, cryptic motif use, donor/acceptor loss/gain, and prediction strength.
   - Assign the VUA baseline code first: PP3 for prediction evidence outside +/-1,2, or PVS1/PVS1_Strength for donor/acceptor +/-1,2 variants where LoF is an applicable disease mechanism.

3. **Find comparison variants**
   - Search ClinGen, ClinVar, PubMed, Europe PMC, LOVD/gene-specific sources where available, and VCEP specifications for P/LP variants in the same splice donor or acceptor motif.
   - Use `ClinGen_get_variant_classifications`, `ClinVar_get_variant_details`, `ClinVar_get_clinical_significance`, `PubMed_search_articles`, and `EuropePMC_search_articles`.

4. **Predict or verify comparison variant splice effect**
   - Run the same splice prediction tools for the comparison variant when possible.
   - If RNA assay evidence exists for the comparison variant, record the observed event, but still ensure the VUA is predicted to match that event.
   - When the comparison event or VUA RNA event is shown in an RNA figure, transcript schematic, gel, Sanger trace, or supplementary image, use `tooluniverse-literature-figure-evidence-extraction` to extract the visual event before deciding whether same-event matching is defensible.
   - If the comparison variant lies outside +/-1,2 and has RNA assay evidence, that assay may support updating a PVS1 decision tree for a +/-1,2 VUA, but PS1 strength still follows the table below.

5. **Check event identity**
   - Confirm same affected transcript and same donor or acceptor motif.
   - Confirm same predicted event, not just "both high SpliceAI."
   - Confirm VUA prediction is similar or stronger than the comparison variant.
   - For exonic variants, confirm protein/codon consequences do not introduce a different dominant pathogenic mechanism.

6. **Assign PS1 strength**
   - Use the Walker Table 2 adaptation below.
   - Apply current VCEP rules if they differ.
   - Report both the baseline splicing code and the PS1-splicing evidence, unless RNA assay evidence replaces prediction codes as described under double counting.

---

## PS1-Splicing Strength Table

Use the highest row that matches the VUA and comparison variant.

| VUA location and baseline code | Comparison variant position relative to VUA | Comparison variant P | Comparison variant LP |
|--------------------------------|---------------------------------------------|----------------------|-----------------------|
| VUA outside donor/acceptor +/-1,2; baseline `PP3` | Same nucleotide | `PS1` | `PS1_Moderate` |
| VUA outside donor/acceptor +/-1,2; baseline `PP3` | Same donor/acceptor motif, including +/-1,2 | `PS1_Moderate` | `PS1_Supporting` |
| VUA at donor/acceptor +/-1,2; baseline full `PVS1` | Same donor/acceptor +/-1,2 dinucleotide | `PS1_Supporting` | No PS1 |
| VUA at donor/acceptor +/-1,2; baseline full `PVS1` | Same donor/acceptor region or motif but outside +/-1,2 | `PS1_Supporting` | `PS1_Supporting` |
| VUA at donor/acceptor +/-1,2; baseline `PVS1_Strong`, `PVS1_Moderate`, or `PVS1_Supporting` | Same donor/acceptor +/-1,2 dinucleotide | `PS1` | No PS1 |
| VUA at donor/acceptor +/-1,2; baseline `PVS1_Strong`, `PVS1_Moderate`, or `PVS1_Supporting` | Same donor/acceptor motif but outside +/-1,2 | `PS1_Moderate` | `PS1_Supporting` |

Interpretation notes:

- "Same nucleotide" means the same genomic or transcript nucleotide position relative to the splice motif, but a different alternate allele may be present.
- "Same donor/acceptor motif" means the same local splice motif, not merely the same gene or exon.
- "Same donor/acceptor region but outside +/-1,2" should be interpreted conservatively and aligned to VCEP motif boundaries where available.
- The predicted event must precisely match in all rows.

---

## Same Event Requirements

Do not apply PS1-splicing if the comparison is only superficially similar.

Count as potentially same event:

- Both variants are predicted to abolish the same donor site and cause the same exon skipping.
- Both variants are predicted to abolish the same acceptor site and cause the same exon skipping.
- Both variants strengthen or create the same cryptic donor or acceptor motif.
- Both variants cause the same predicted pseudoexon inclusion or intron-retention mechanism, if supported by the prediction method and transcript context.

Do not count as same event:

- Both variants have high SpliceAI scores but affect different donor/acceptor motifs.
- One variant predicts donor loss and the other predicts donor gain.
- One variant predicts exon skipping and the other predicts cryptic splice-site use unless the final transcript event is clearly the same.
- Exonic variants where retained mRNA encodes different missense/in-frame products that may change the pathogenic mechanism.
- A non-donor/non-acceptor region variant where abnormal splicing is plausible but not the most likely mechanism.

---

## Double-Counting and Code Interaction

- PS1-splicing does not replace PVS1; it is additional similarity evidence when Table 2 conditions are met.
- If RNA assay evidence for the VUA is already used as `PVS1_Strength (RNA)`, do not also use PP3 for the same splicing mechanism. PS1-splicing may still be considered only if the comparison evidence remains independent and a VCEP or curator determines that the same-event comparison adds non-duplicative evidence.
- Do not use the same comparison variant both as PS1-splicing and as generic PP5 without documenting independence.
- Do not use PM5 for splicing prediction similarity under Walker et al. 2023 unless a current VCEP specifically requires a different rule.
- For variants with both splicing and protein mechanisms, evaluate protein-level PS1/PM5 separately from PS1-splicing, then avoid counting the same comparison evidence twice.
- If a comparison variant's pathogenicity is due to dominant-negative protein mechanism rather than the same splice event, do not use it as PS1-splicing evidence unless the same splice event is independently established and relevant.

---

## Interaction with Direct RNA Evidence

Direct RNA evidence for the VUA takes priority over prediction-based same-event inference:

- If the VUA RNA assay demonstrates LoF transcript(s), first assign `PVS1_Strength (RNA)` using `tooluniverse-acmg-pvs1-splicing-refinement`.
- If the observed VUA RNA event matches the comparison variant event and the comparison variant's clinical classification is independent, PS1-splicing may coexist at the Table 2 strength.
- If the observed VUA RNA event is different from the event predicted for PS1-splicing, do not apply PS1-splicing from the prediction.
- If the VUA RNA assay shows no splicing impact, use `BP7_Strong (RNA)` where appropriate and withhold PS1-splicing for the contradicted predicted splice event.
- If the VUA RNA assay shows partial, tissue-limited, or complex aberrant transcripts, require explicit same-event matching for the clinically relevant transcript effect. Do not infer sameness from SpliceAI score similarity alone.
- Do not use the VUA RNA assay as both direct PVS1/BP7 evidence and as the comparison evidence that establishes PS1.
- If the comparison variant's P/LP status depends on the VUA, the same case, the same family, the same unpublished RNA experiment, or reciprocal inference, treat the comparison as non-independent and withhold PS1-splicing unless a current VCEP rule specifies otherwise.

---

## VCEP and Disease-Specific Rules

Current VCEP specifications supersede this generic Walker overlay. Follow VCEP rules when they define:

- Splice motif boundaries.
- Which prediction tool and thresholds to use.
- Whether LP comparison variants are allowed.
- Whether canonical donor/acceptor variants can receive additional PS1 evidence.
- How to combine PVS1, PP3, PS1, and RNA assay evidence.
- Gene-specific rescue transcripts or alternative transcript models that change PVS1 baseline.

Always cite the VCEP if it changes the default Table 2 assignment.

---

## Output Format

Report PS1-splicing evidence transparently:

```markdown
PS1 splicing similarity refinement:
- VUA: [HGVS], transcript [reference], location [outside +/-1,2 / at +/-1,2]
- VUA baseline splicing code: [PP3 / PVS1 / PVS1_Strong / PVS1_Moderate / PVS1_Supporting]
- Direct VUA RNA evidence: [none / PVS1_Strength (RNA) / BP7_Strong (RNA) / conflicting or complex result]
- VUA predicted event: [donor loss / acceptor loss / cryptic gain / exon skipping / intron retention / pseudoexon], score [tool/result]
- Comparison variant: [HGVS], classification [P/LP], source [ClinGen/ClinVar/PMID/VCEP], independence [checked]
- Comparison predicted or observed event: [event], score or RNA result [source]
- Relative position: [same nucleotide / same +/-1,2 dinucleotide / same motif outside +/-1,2]
- Same-event check: [met/not met], rationale [short]
- Exonic protein check: [not applicable / reviewed / conflicting mechanism]
- Applied evidence: [PS1 / PS1_Moderate / PS1_Supporting / No PS1]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [comparison variant / splice prediction / RNA evidence / none]
```

Example evidence table row:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PS1 | Moderate | VUA and a pathogenic comparison variant are in the same donor motif and are predicted to cause the same exon-skipping event with similar or stronger predicted splice impact for the VUA. | Walker et al. 2023 Table 2; [comparison source] |
```

---

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `VariantValidator_validate_variant` | Normalize VUA and comparison variant, align transcript coordinates. |
| `VariantValidator_gene2transcripts` | Identify MANE Select and clinically relevant transcripts. |
| `Mutalyzer_normalize_variant` | HGVS normalization and protein/RNA consequence support. |
| `EnsemblVEP_annotate_hgvs` | Consequence, transcript, and exon/intron context. |
| `SpliceAI_predict_splice` / `SpliceAI_get_max_delta` | Predict splice effect and compare score strength. |
| `SpliceAI_predict_pangolin` | Optional second splicing predictor for borderline or VCEP-specified use. |
| `ClinGen_get_variant_classifications` | Expert-curated comparison variant classifications. |
| `ClinVar_get_variant_details` / `ClinVar_get_clinical_significance` | Comparison variant classification, review status, and conflicts. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Literature support for comparison variant pathogenicity and RNA effects. |
| `EuropePMC_get_fulltext_snippets` | Targeted extraction of RNA assay or variant comparison passages. |

---

## Limitations

- This skill is a rule-refinement layer, not a deterministic splice-event matcher.
- "Same predicted event" may require manual curation when tools report only score categories rather than transcript products.
- SpliceAI alone may not fully specify transcript-level event identity; use RNA evidence or VCEP specifications when available.
- Comparison variant classification must be clinically supported and not circularly dependent on the VUA.
- The Walker Table 2 framework is generic; current VCEP specifications should be preferred when available.

---

## Primary Reference

- Walker LC, de la Hoya M, Wiggins GAR, et al. Using the ACMG/AMP framework to capture evidence related to predicted and observed impact on splicing: Recommendations from the ClinGen SVI Splicing Subgroup. Am J Hum Genet. 2023;110(7):1046-1067. PMID: 37352859. PMCID: PMC10357475. DOI: 10.1016/j.ajhg.2023.06.002.
