---
name: tooluniverse-acmg-dominant-negative-mechanism-refinement
description: Mechanism-layer overlay for ACMG/AMP variant classification when dominant-negative or antimorphic disease mechanisms may affect evidence assignment across PVS1, PS3/BS3, PS1/PM5, PM1/PP2/PP3, PP1, PS2/PM6, PM4/BP3, BP1, PS4, PM3, and BS4.
disable-model-invocation: true
---

# ToolUniverse ACMG Dominant-Negative Mechanism Refinement

Use this overlay when a gene-disease relationship, variant class, functional assay, or literature source suggests a dominant-negative mechanism. This is a mechanism-routing layer for ACMG/AMP interpretation. It does not create a new ACMG evidence code and does not replace evidence-specific overlays.

Use `tooluniverse-acmg-overlay-routing-core` for shared routing order and output-status conventions. This overlay is the mechanism-context step in that shared routing order.

If the main question is whether evidence from one gene-associated disorder can be used for another disorder, invoke `tooluniverse-acmg-multiple-disorder-context-refinement` first. Then use this dominant-negative overlay only for mechanism-specific routing within the selected disease entity, inheritance model, and variant class.

Dominant-negative is used here in the broad clinical genetics sense: a variant allele produces an altered product that interferes with the wild-type allele product, a multimeric complex, a protein interaction network, or a pathway output. Antimorphic is treated as the closest formal synonym when used in literature.

## When to Invoke

Invoke this overlay when any of the following are present:

- The disease is autosomal dominant and reported mechanism includes dominant-negative, antimorphic, altered multimerization, poison subunit, interference with wild-type protein, altered complex assembly, or dominant interference.
- Pathogenic variants are predominantly missense or in-frame variants while truncating variants have absent, milder, different, or uncertain phenotypes.
- The gene encodes a multimeric structural protein, transcription factor, receptor/channel subunit, enzyme complex member, collagen-like protein, cytoskeletal protein, or protein with obligate oligomerization.
- A functional assay uses WT+variant co-expression, heterozygous cellular models, patient-derived cells, multimer assembly, complex stability, channel/receptor output, or pathway readout.
- PVS1 is being considered in a gene where LoF/haploinsufficiency is not clearly established for the exact gene-disease context, inheritance pattern, transcript/isoform, and variant class.
- PVS1 is being considered in a gene with both dominant and recessive disease associations, different phenotypes by inheritance, or suspected mixed mechanisms.
- PVS1 is being considered for an autosomal dominant disease and ClinGen dosage sensitivity, G2P, GenCC, VCEP, or equivalent sources do not clearly establish haploinsufficiency/LoF as the disease mechanism.
- PVS1 plus PM2_Supporting, PM3, PP1, PS4, or another evidence combination would drive the classification and mechanism uncertainty could change whether PVS1 is valid.
- PS1/PM5, PM1, PP2, PP3, PP1, PS2/PM6, PM4/BP3, BP1, PS4, PM3, or BS4 depends on whether the variant class fits a dominant-negative disease model.
- Any criterion would rely on transferring evidence from one variant class or disease mechanism to another, including missense/in-frame hotspot evidence, functional assays, de novo observations, segregation, case enrichment, in-trans observations, or benign non-segregation.

Do not invoke this overlay for routine haploinsufficiency/LoF genes only when the target disease context already has clear curated LoF/HI support and there is no dominant, antimorphic, gain-of-function, or mixed-mechanism disease association that could affect the evidence code under consideration. If skipping the overlay while applying a mechanism-sensitive criterion, explicitly cite the curated mechanism source that makes the criterion safe to use.

## Core Principle

Dominant-negative is a gene-disease and variant-class mechanism, not a standalone ACMG evidence criterion. First decide whether the disease mechanism plausibly requires dominant interference. Then use that mechanism decision to route or constrain the usual ACMG evidence criteria.

Do not treat dominant-negative as equivalent to:

- Simple haploinsufficiency.
- Generic loss of protein function.
- Generic gain of function.
- A high missense pathogenicity score.
- A functional assay showing reduced activity only in the variant protein alone.

## Evidence Retrieval Workflow

Use ToolUniverse tools first; do not infer a dominant-negative mechanism from inheritance alone.

1. **Define gene-disease context**
   - Use `ClinGen_search_gene_validity` and `ClinGen_get_gene_validity` for gene-disease validity and inheritance.
   - Use `G2P_search` and `G2P_get_record` for curated genotype, variant consequence, and molecular mechanism.
   - Use `GenCC_search_gene` or `GenCC_search_disease` for cross-curator gene-disease validity.
   - Use `ClinGen_search_dosage_sensitivity` to check whether haploinsufficiency or triplosensitivity has curated support.
   - Use GeneReviews/NCBI Bookshelf disease chapters, discovered through `MedGen_search_conditions`, PubMed/EuropePMC, or direct NCBI Bookshelf lookup, to capture expert-reviewed inheritance, disease spectrum, and mechanism statements.
   - Treat GeneReviews as expert review/background support, not as a VCEP rule or primary variant-level evidence. If GeneReviews gives a mechanism statement that affects routing, record the chapter title, update date, table/section, and whether primary references need follow-up.

2. **Retrieve mechanism-specific literature**
   - Use `tooluniverse-literature-deep-research` when the mechanism depends on published studies.
   - Use `PubMed_search_articles`, `EuropePMC_search_articles`, `EuropePMC_get_full_text`, and `EuropePMC_get_fulltext_snippets` with terms such as "dominant-negative", "dominant negative", "antimorphic", "poison subunit", "multimerization", "oligomerization", "co-expression", "wild-type", "heterozygous", and the gene/disease name.
   - Use `tooluniverse-literature-figure-evidence-extraction` when mechanism evidence is in pedigrees, functional assay figures, protein-complex diagrams, blots, gels, cellular images, or assay plots.

3. **Compare variant classes**
   - Use ClinVar, ClinGen ERepo, G2P, UniProt/EBI Proteins, disease literature, and VCEP specifications to compare pathogenic missense/in-frame variants versus truncating/LoF variants.
   - Record whether different variant classes produce the same disease, different phenotypes, different severities, or no established disease.

4. **Assess protein and pathway biology**
   - Use `UniProt_get_function_by_accession`, `EBIProteins_get_mutagenesis`, `EBIProteins_get_variation`, InterPro, AlphaFold/PDB, Reactome, GO, STRING, and protein-interaction tools when relevant.
   - Look for obligate oligomerization, subunit assembly, DNA/protein binding, receptor/channel complexes, collagen triple helices, cytoskeletal networks, or other mechanisms where mutant protein can interfere with wild-type function.

5. **Evaluate variant-level compatibility**
   - Confirm the variant can plausibly produce a stable or expressed altered product. Missense and in-frame changes are often more compatible with dominant-negative mechanisms than early null alleles, but this is gene-specific.
   - Truncating or splice variants can still be dominant-negative if they escape NMD, produce a stable truncated product, disrupt a critical interaction domain, or have literature/assay evidence for interference.
   - If the variant is predicted to undergo complete NMD and no altered product is produced, dominant-negative evidence is usually weak unless a disease-specific source says otherwise.

## Mechanism Confidence

Assign a mechanism confidence label before routing ACMG evidence:

| Confidence | When to use |
|---|---|
| `DN established` | Curated source, VCEP, or multiple robust studies explicitly support dominant-negative/antimorphic mechanism for the same gene-disease context and relevant variant class. |
| `DN plausible` | Literature, protein biology, variant spectrum, or assay data support dominant interference, but curation is incomplete or variant-class specificity is not fully resolved. |
| `DN uncertain` | Some features suggest dominant-negative, but evidence is indirect, conflicting, or not disease-specific. |
| `DN not supported` | Disease mechanism is haploinsufficiency/LoF/GoF only, or dominant interference is contradicted by curated evidence. |
| `Mixed mechanism` | Multiple mechanisms are established for the same gene, or different diseases/phenotypes use different mechanisms. Keep disease context separate. |

Use conservative evidence assignment when confidence is `DN plausible` or `DN uncertain`. Do not upgrade ACMG strength solely because dominant-negative is biologically plausible.

## ACMG Evidence Routing

### PVS1

Use PVS1 only for a gene-disease context where LoF/haploinsufficiency is established.

- If the disease mechanism is established dominant-negative and haploinsufficiency is not established, do not apply PVS1 to a null variant solely because it is a null variant.
- If a truncating/splicing variant produces a stable altered product that interferes with wild-type protein, route the evidence through mechanism-specific functional evidence, clinical comparison, or disease-specific VCEP guidance rather than ordinary PVS1.
- If both haploinsufficiency and dominant-negative mechanisms are established, separate the evidence by disease, phenotype, transcript, and variant class.
- If a gene has a recessive LoF disease and a separate dominant missense/in-frame or complex-mediated disease, PVS1 may be allowed only for the recessive LoF context unless curated evidence also supports LoF for the dominant context.

Use `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` for baseline PVS1 strength after mechanism is resolved. Use `tooluniverse-acmg-pvs1-splicing-refinement` only for RNA/splicing details after the baseline branch is identified.

### PS3/BS3

Dominant-negative claims usually require functional assays that test interference with wild-type function.

PS3 may be supported when the assay shows disease-relevant dominant interference, such as:

- WT+variant co-expression reduces function more than expected from 50% dosage.
- Heterozygous/endogenous or patient-derived models show abnormal complex/pathway output.
- Variant protein incorporates into a multimer or complex and poisons function.
- Variant alters assembly, trafficking, DNA/protein binding, channel gating, receptor signaling, or structural network behavior in a way consistent with disease.

Be cautious with BS3:

- A normal result for variant-only protein function does not exclude dominant-negative effect.
- BS3 should require an assay that can exclude the dominant-negative mechanism, such as WT+variant co-expression or an endogenous heterozygous model that measures the disease-relevant readout.

Use `tooluniverse-acmg-ps3-bs3-functional-assay-refinement` for assay validation and strength assignment.

### PS1 and PM5

PS1/PM5 require same-mechanism reasoning when dominant-negative disease is possible.

- Same amino acid change can support PS1 only when the comparison variant's pathogenic mechanism is relevant to the current gene-disease context and not based on a different mechanism.
- Same residue but different amino acid substitution supports PM5 only if the residue/region is known to mediate the dominant-negative mechanism or the comparison variants support the same disease mechanism.
- Do not apply PS1/PM5 by residue proximity when one variant is dominant-negative and another is haploinsufficiency, splicing LoF, or an unrelated GoF mechanism.

### PM1, PP2, PP3, and BP1

- PM1 can be appropriate for a dominant-negative missense hotspot, oligomerization interface, DNA-binding domain, collagen repeat, channel pore, receptor interface, or other mechanism-specific critical region.
- PP2 can support missense-mediated disease only when the gene-disease context has low benign missense variation and pathogenic missense variants are an established mechanism; dominant-negative is one possible missense mechanism.
- PP3/BP4 calibrated missense predictors do not prove or exclude dominant-negative mechanism. They can support generic missense deleteriousness, while this overlay supplies the mechanism plausibility check.
- Do not apply BP1 simply because truncating variants are a known disease mechanism if the same gene-disease context also has established pathogenic dominant-negative missense variants.

Use `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` and `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` for the criterion-specific rules.

### PP1, PS2, PM6, and BS4

Genetic evidence requires variant-class plausibility.

- PP1 segregation evidence is stronger when the segregating variant class fits the dominant-negative disease model.
- PS2/PM6 de novo evidence should be interpreted with the gene-disease mechanism and variant class; a de novo missense/in-frame variant may fit a DN disease better than a de novo null allele in a DN-only disease.
- BS4 non-segregation should consider phenotypic heterogeneity, reduced penetrance, and whether the family's actual disease mechanism matches the asserted dominant-negative mechanism.

Use `tooluniverse-acmg-pp1-segregation-refinement` for PP1 strength, and document the DN mechanism check in the qualifying-variant rationale.

### PM4 and BP3

In-frame insertions/deletions require mechanism-specific interpretation.

- PM4 may be appropriate when an in-frame change plausibly disrupts or alters a dominant-negative critical region, especially oligomerization, interface, repeat, or structural assembly regions.
- BP3 should not be applied mechanically to an in-frame change in a repeat or low-complexity region if that region is disease-relevant for dominant interference.
- Protein length changes that preserve mutant protein expression may be more DN-compatible than complete NMD alleles, but this requires evidence.

### PS4

Case enrichment and case-control evidence should be mechanism-stratified.

- Do not combine truncating, missense, in-frame, and splice variants into one burden category if the gene has different disease mechanisms by variant class.
- For DN diseases, enrichment of relevant missense/in-frame variants is more informative than mixed all-variant burden unless a VCEP or study justifies grouping.

### PM3

PM3 is usually recessive in-trans evidence and is not a dominant-negative criterion.

- If a gene has both recessive LoF and dominant-negative disease mechanisms, keep disease entities and inheritance patterns separate.
- Do not use a dominant-negative variant as the "other allele" for PM3 in a recessive LoF disease unless the literature shows that allele functions as a qualifying pathogenic allele for that recessive disease.

Use `tooluniverse-acmg-pm3-in-trans-refinement` for PM3 scoring.

## Output Format

Report a mechanism-routing block before evidence-specific ACMG assignments:

```markdown
Dominant-negative mechanism refinement:
- Gene-disease context: [gene], [disease], [inheritance]
- Mechanism status: [DN established / DN plausible / DN uncertain / DN not supported / Mixed mechanism]
- Sources: [ClinGen/G2P/VCEP/PMID/UniProt/functional assay]
- Variant class fit: [fits / partial / does not fit / unclear], rationale [short]
- Product-expression assumption: [missense/in-frame expressed product / NMD predicted / NMD escape / unknown]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Routed to: [evidence-specific overlay]
- Evidence routing:
  - PVS1: [allowed / withhold / separate HI mechanism / not assessed]
  - PS3/BS3: [DN-capable assay required / current assay sufficient / current assay insufficient]
  - PS1/PM5: [same-mechanism comparison required / comparison acceptable / comparison withheld]
  - PM1/PP2/PP3/BP1: [missense-mediated mechanism supported / generic predictor only / BP1 unsafe]
  - PP1/PS2/PM6/BS4: [variant class plausible / not plausible / unclear]
  - PM4/BP3: [in-frame DN region check required]
  - PS4/PM3: [mechanism-stratify / not applicable]
```

## Evidence Sufficiency Rules

Strong enough to affect ACMG routing:

- Current VCEP/gene-specific specification states dominant-negative or antimorphic mechanism for the disease and variant class.
- Curated G2P/ClinGen/GenCC source plus supporting literature indicates dominant-negative mechanism.
- Well-controlled functional assay directly tests WT+variant or heterozygous interference and is consistent with disease.
- Variant spectrum shows disease-causing missense/in-frame variants clustered in a biologically coherent dominant-negative region, while null alleles cause no disease or a different phenotype.

Not enough by itself:

- Autosomal dominant inheritance alone.
- A high REVEL/CADD/AlphaMissense score.
- General gene constraint or missense intolerance.
- Variant-only reduced activity without WT co-expression or heterozygous context.
- Broad domain membership without mechanism-specific evidence.
- A single paper using "dominant" inheritance language but not showing dominant-negative molecular mechanism.

## Tool Parameter Reference

| Tool | Use |
|------|-----|
| `ClinGen_search_gene_validity` / `ClinGen_get_gene_validity` | Gene-disease validity and inheritance. |
| `ClinGen_search_dosage_sensitivity` | Haploinsufficiency/triplosensitivity context; helps avoid confusing DN with HI. |
| `G2P_search` / `G2P_get_record` | Curated genotype, consequence, and molecular mechanism. |
| `GenCC_search_gene` / `GenCC_search_disease` | Cross-curator gene-disease validity. |
| `ClinGen_get_variant_classifications` | Expert variant classifications and evidence context. |
| `MedGen_search_conditions` | Discover MedGen conditions and linked GeneReviews/NCBI Bookshelf disease chapters for inheritance, disease spectrum, and expert-reviewed mechanism background. |
| `ClinVar_search_variants` / `ClinVar_get_variant_details` | Variant spectrum and clinical assertions. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Mechanism literature retrieval. |
| `EuropePMC_get_full_text` / `EuropePMC_get_fulltext_snippets` | Full-text mechanism and assay passages. |
| `tooluniverse-literature-deep-research` | Deep extraction from mechanism papers. |
| `tooluniverse-literature-figure-evidence-extraction` | Extract figure-based assay, pedigree, or mechanism evidence. |
| `UniProt_get_function_by_accession` | Protein function, isoforms, domains, and curated comments. |
| `EBIProteins_get_mutagenesis` | Curated mutagenesis effects, including gain/loss/binding/functional changes. |
| `EBIProteins_get_variation` | Protein variant spectrum from ClinVar, COSMIC, gnomAD/ExAC, and UniProt. |
| InterPro, AlphaFold, PDB, STRING, Reactome, GO tools | Domain, structure, interaction, and pathway context. |

## Limitations

- This overlay does not assign final ACMG evidence strength by itself.
- Many databases record loss/gain of function but not dominant-negative explicitly; literature review is often required.
- DN mechanisms are gene-, disease-, transcript-, and variant-class specific. Avoid transferring mechanism between different diseases caused by the same gene unless evidence supports it.
- Functional assays must be interpreted through PS3/BS3 validation rules; a DN-compatible assay is not automatically strong evidence.
- Disease-specific VCEP specifications supersede this generic mechanism overlay.

## References

- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants. Genetics in Medicine. 2015;17:405-424. PMID: 25741868.
- Brnich SE, Abou Tayoun AN, Couch FJ, et al. Recommendations for application of the functional evidence PS3/BS3 criterion using the ACMG/AMP sequence variant interpretation framework. Genome Medicine. 2019;12:3. PMID: 31892348.
- Strande NT, Riggs ER, Buchanan AH, et al. Evaluating the clinical validity of gene-disease associations: an evidence-based framework developed by the Clinical Genome Resource. American Journal of Human Genetics. 2017;100:895-906. PMID: 28552198.
- Use current VCEP specifications, ClinGen/GenCC/G2P curations, and primary mechanism literature whenever available.
