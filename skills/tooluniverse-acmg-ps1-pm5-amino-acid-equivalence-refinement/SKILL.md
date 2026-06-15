---
name: tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement
description: Refine ACMG/AMP PS1 and PM5 evidence for missense variants at the same codon, same amino-acid substitution, or same amino-acid residue as an independently established pathogenic comparison variant. Use with ToolUniverse ACMG classification when amino-acid equivalence, same-residue missense evidence, splicing confounding, or circularity affects PS1/PM5 assignment.
disable-model-invocation: true
---

# ACMG PS1/PM5 Amino-Acid Equivalence Refinement

This skill extends `tooluniverse-acmg-variant-classification` for two closely related evidence rules:

- `PS1`: same amino-acid change as an established pathogenic variant, but caused by a different nucleotide change.
- `PM5`: different missense change at the same amino-acid residue where another pathogenic missense variant has been established.

This overlay is for protein-level missense evidence. It is separate from `tooluniverse-acmg-ps1-splicing-similarity-refinement`, which handles PS1 based on same predicted RNA-splicing events.

Use ToolUniverse tools to normalize the variant, identify comparison variants, verify transcript/protein equivalence, review clinical assertions, and check whether the pathogenic mechanism is amino-acid mediated rather than DNA-level or splicing-mediated. Then assign PS1, PM5, or no evidence in the ACMG evidence table.

---

## When to Use This Skill

Use this skill when:

- The variant under assessment is a missense variant.
- A reported pathogenic or likely pathogenic comparison variant affects the same codon, same amino-acid substitution, or same amino-acid residue.
- The main ACMG workflow is considering PS1 or PM5 from ClinVar, ClinGen, a VCEP specification, a publication, or a curated database.
- There is a need to distinguish ordinary protein-level PS1/PM5 from splicing-based PS1.
- The codon-level nucleotide change could alter splicing, transcript processing, or another DNA/RNA-level mechanism.
- The comparison variant's pathogenicity may depend on dominant-negative, gain-of-function, haploinsufficiency, splice disruption, or another mechanism that may not match the variant under assessment.

Do not use this skill for:

- Variants whose primary evidence is the same predicted splice event; use `tooluniverse-acmg-ps1-splicing-similarity-refinement`.
- Purely synonymous, intronic, UTR, promoter, copy-number, or structural variants unless a current VCEP explicitly adapts PS1/PM5 for that context.
- Applying PS1 or PM5 from the variant's own classification evidence.

---

## Core Principle

PS1 and PM5 require an independently established comparison variant and a shared disease-relevant protein-level mechanism.

Do not assign PS1 or PM5 merely because two variants affect the same codon or residue. First confirm that:

- The comparison variant is already classified as pathogenic or likely pathogenic without relying on the variant under assessment or reciprocal PS1/PM5 logic.
- The comparison variant's pathogenicity is attributable to the amino-acid effect, not primarily to splicing, DNA sequence change, regulatory effect, or another non-shared mechanism.
- The variant under assessment and the comparison variant are evaluated on the same clinically relevant transcript/protein residue.
- Splicing consequences and other coding consequences have been reviewed and do not contradict a protein-level PS1/PM5 interpretation.
- Current VCEP specifications, if available, do not override the generic PS1/PM5 rule.

---

## Evidence Retrieval Workflow

1. **Normalize the variant**
   - Use `VariantValidator_validate_variant`, `Mutalyzer_normalize_variant`, or `ClinGenAR_lookup_allele`.
   - Record HGVS cDNA, genomic allele, transcript, protein HGVS, codon, amino-acid residue, reference amino acid, and alternate amino acid.
   - Confirm the variant is a missense variant on the disease-relevant transcript.

2. **Annotate protein and transcript consequence**
   - Use `EnsemblVEP_annotate_hgvs`, `MyVariant_query_variants`, and transcript-aware annotations.
   - Check whether the variant has additional consequences such as splice-region impact, multiple transcript effects, in-frame indel, stop-gain, or complex allele representation.
   - Use `SpliceAI_predict_splice` or `SpliceAI_get_max_delta` when the variant is near exon-intron boundaries or when a synonymous/codon-level change could affect splicing.

3. **Identify comparison variants**
   - Search by gene, protein residue, codon, amino-acid change, HGVS protein expression, ClinVar Variation ID, rsID, or ClinGen Allele Registry ID.
   - Use `ClinVar_search_variants`, `ClinVar_get_variant`, `MyVariant_query_variants`, `ClinGenAR_lookup_allele`, `PubMed_search_articles`, and `EuropePMC_search_articles`.
   - Prefer comparison variants classified by expert panel, VCEP, ClinGen-approved curation, or multiple independent high-quality submitters.

4. **Verify comparison variant independence**
   - The comparison variant must be pathogenic or likely pathogenic without using the variant under assessment as evidence.
   - Do not use the variant under assessment to establish the comparison variant's pathogenicity, and then use the comparison variant back as PS1/PM5 evidence.
   - Exclude comparison variants whose P/LP status depends only on the same patient, same family, same unpublished case, reciprocal PM5/PS1 inference, or an unsupported database assertion.

5. **Confirm mechanism match**
   - Confirm that the comparison variant's evidence supports an amino-acid-mediated missense mechanism.
   - If the comparison variant is pathogenic because of splicing, exon skipping, nonsense-mediated decay, regulatory effect, or another DNA/RNA-level mechanism, do not transfer that evidence as protein-level PS1/PM5.
   - If the gene-disease context may involve dominant-negative, antimorphic, gain-of-function, or mixed mechanisms, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before assigning PS1/PM5.

6. **Apply PS1 or PM5**
   - Use PS1 when the variant under assessment produces the same amino-acid substitution as an independently established pathogenic comparison variant but from a different nucleotide change.
   - Use PM5 when the variant under assessment produces a different missense substitution at the same amino-acid residue as an independently established pathogenic missense comparison variant.
   - If the comparison variant is only likely pathogenic, follow current VCEP guidance when available; otherwise consider whether downgraded or no evidence is more appropriate and document the uncertainty.
   - Do not apply both PS1 and PM5 from the same comparison relationship.

---

## PS1 Rules

Apply `PS1` when all of the following are true:

- The variant under assessment and the comparison variant encode the same amino-acid substitution.
- The nucleotide changes are different.
- The comparison variant is independently established as pathogenic for the same disease context, or a current VCEP allows likely pathogenic comparison variants.
- The comparison variant's pathogenicity is mediated by the amino-acid substitution rather than a different splicing, DNA-level, or transcript-level effect.
- Transcript/protein residue equivalence is confirmed.
- The comparison evidence is not circular.

Withhold PS1 when:

- The same amino-acid change is caused by the same nucleotide variant; that is not PS1 and should be evaluated as the same variant.
- The comparison variant's P/LP classification depends on the variant under assessment.
- Either variant has a different clinically relevant transcript consequence.
- Splicing evidence contradicts the assumed protein-level equivalence.
- The comparison variant is pathogenic through a different mechanism, such as splice disruption or haploinsufficiency, while the variant under assessment is only a missense change.

---

## PM5 Rules

Apply `PM5` when all of the following are true:

- The variant under assessment is a missense variant.
- A different missense comparison variant affects the same amino-acid residue.
- The comparison variant is independently established as pathogenic for the same disease context, or a current VCEP allows likely pathogenic comparison variants.
- The disease mechanism supports pathogenicity through amino-acid change at that residue or region.
- The comparison variant is not pathogenic primarily because of splicing, DNA-level effect, or a mechanism not shared with the variant under assessment.
- Transcript/protein residue equivalence is confirmed.
- The comparison evidence is not circular.

Withhold or downgrade PM5 when:

- The comparison variant is not independently pathogenic.
- The comparison variant is pathogenic only because it alters splicing or causes a non-missense mechanism.
- The residue is not conserved or not in a disease-relevant functional region and the only support is an uncurated database assertion.
- Multiple variants at the residue show conflicting benign and pathogenic interpretations without a VCEP rule.
- The gene has mechanism-specific residue effects and the variant under assessment does not plausibly share the pathogenic mechanism.

---

## Circularity Guard

PS1 and PM5 cannot be used to establish the pathogenicity of the same comparison evidence that is then used back for the variant under assessment.

Do not use PS1/PM5 when:

- Variant A is classified as pathogenic only because of Variant B.
- Variant B is then used as PS1 or PM5 evidence for Variant A.
- Both variants are from the same family or case series and neither has independent pathogenic evidence.
- The comparison variant's classification is an unreviewed database assertion with no accessible evidence and no independent support.

If independence cannot be confirmed, report `PS1/PM5 not assessable` or `No PS1/PM5` rather than forcing the criterion.

---

## Splicing and DNA-Level Confounding

Before assigning protein-level PS1 or PM5, check whether either variant may act through splicing or another DNA/RNA-level mechanism.

Use splicing review when:

- The variant is exonic but near a splice junction.
- The nucleotide change creates, disrupts, or strengthens a splice motif.
- SpliceAI, VEP, literature, or RNA assay evidence suggests altered splicing.
- The comparison variant is reported as pathogenic because of exon skipping, cryptic splice activation, intron retention, or NMD.

Routing:

- If the evidence is same predicted splice event, use `tooluniverse-acmg-ps1-splicing-similarity-refinement`.
- If direct RNA evidence affects PVS1 or BP7, use `tooluniverse-acmg-pvs1-splicing-refinement`.
- If the protein-level amino-acid effect remains independent and disease-relevant, evaluate protein-level PS1/PM5 separately and avoid double counting the same comparison evidence.

---

## VCEP Priority

Current VCEP specifications supersede this generic overlay. Follow VCEP rules when they define:

- Whether likely pathogenic comparison variants can be used.
- Whether PS1 or PM5 may be downgraded to Moderate or Supporting.
- Gene-specific residue, domain, mechanism, or assay requirements.
- How to handle multiple pathogenic variants at the same residue.
- How PS1/PM5 interact with PM1, PM5, PP3, PS3, PS4, or other criteria.
- Whether specific known variants are excluded because their pathogenicity is splicing-mediated or otherwise not protein-level.

Always cite the VCEP when it changes the default PS1/PM5 assignment.

---

## Output Format

Report PS1/PM5 refinement transparently:

```markdown
PS1/PM5 amino-acid equivalence refinement:
- Variant under assessment: [HGVS c.], [HGVS p.], transcript [ID], residue [position]
- Comparison variant: [HGVS c.], [HGVS p.], source [ClinVar/ClinGen/VCEP/literature]
- Relationship: [same amino-acid substitution / same residue different substitution / same codon only]
- Comparison classification: [P/LP/VUS/etc.], review status: [expert panel/multiple submitters/etc.]
- Independence check: [independent / circularity concern / not assessable]
- Mechanism check: [amino-acid mediated / splicing-mediated / mixed / uncertain]
- Splicing/DNA-level confounding: [none found / present / not assessable]
- VCEP rule: [none found / applied rule]
- Applied evidence: [PS1 / PM5 / No PS1/PM5 / not assessable]
```

Example evidence table row:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PS1 | Strong | The variant encodes the same amino-acid substitution as an independently established pathogenic comparison variant caused by a different nucleotide change; both support the same amino-acid-mediated disease mechanism and no splicing confounder was found. | ACMG/AMP 2015; ClinVar/ClinGen/VCEP/literature source |
```

---

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `VariantValidator_validate_variant` | Normalize HGVS and confirm transcript/protein consequence. |
| `Mutalyzer_normalize_variant` | Alternative HGVS normalization and allele representation. |
| `ClinGenAR_lookup_allele` | Resolve ClinGen Allele Registry ID and cross-references. |
| `EnsemblVEP_annotate_hgvs` | Annotate consequence, transcript effects, protein HGVS, and splice-region flags. |
| `MyVariant_query_variants` | Retrieve aggregated ClinVar, dbNSFP, transcript, and consequence annotations. |
| `ClinVar_search_variants` / `ClinVar_get_variant` | Identify comparison variants and review status. |
| `ClinGen_get_variant_classifications` / ClinGen ERepo tools | Prefer expert-curated variant classifications when available. |
| `SpliceAI_predict_splice` / `SpliceAI_get_max_delta` | Check splicing confounding for exonic or splice-proximal missense variants. |
| `ClinGen_search_gene_validity` / `GenCC_search_gene` | Confirm gene-disease context and inheritance. |
| `PubMed_search_articles` / `EuropePMC_search_articles` / `EuropePMC_get_full_text` | Retrieve literature supporting comparison variant pathogenicity and mechanism. |
| `UniProt_get_protein_info`, InterPro tools, AlphaFold or structure tools | Support residue/domain mechanism when PM5 depends on a critical region. |

---

## Limitations

- This overlay does not create a universal expert-panel PS1/PM5 rule beyond ACMG/AMP 2015 and current VCEP specifications.
- PS1/PM5 strength may be gene-specific; use VCEP guidance when available.
- Database classifications without accessible evidence should not be treated as independently established pathogenic comparison variants.
- Same codon does not automatically mean same mechanism.
- Splicing and protein effects can coexist; avoid counting the same observation twice.

---

## Primary References

- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants: a joint consensus recommendation of ACMG and AMP. Genet Med. 2015;17(5):405-424. PMID: 25741868. DOI: 10.1038/gim.2015.30.
- Walker LC, Hoya M, Wiggins GAR, et al. Using the ACMG/AMP framework to capture evidence related to predicted and observed impact on splicing. ClinGen SVI Splicing Subgroup. 2023. PMID: 37352859; PMCID: PMC10357475. Use only for splicing-specific PS1/PVS1 interactions, not ordinary protein-level PS1/PM5.
- Current ClinGen VCEP specifications and ClinGen Evidence Repository records for gene/disease-specific PS1 and PM5 modifications.
