# Quick Start: Dominant-Negative Mechanism Refinement

Use this overlay before assigning ACMG evidence when dominant-negative or antimorphic mechanism may change how a criterion should be used.

## Minimal Workflow

1. Define the exact gene-disease context and inheritance.
2. Search curated mechanism sources: ClinGen, G2P, GenCC, ClinGen dosage sensitivity, and VCEP specifications.
3. Search literature for "dominant-negative", "antimorphic", "poison subunit", "wild-type co-expression", "oligomerization", "multimerization", and gene/disease terms.
4. Compare pathogenic variant classes: missense/in-frame versus truncating/splice/null.
5. Decide mechanism confidence: `DN established`, `DN plausible`, `DN uncertain`, `DN not supported`, or `Mixed mechanism`.
6. Route ACMG evidence criteria according to the mechanism decision.

## Example Tool Sequence

```text
ClinGen_search_gene_validity(gene="...")
ClinGen_search_dosage_sensitivity(gene="...")
G2P_search(query="...")
PubMed_search_articles(query="GENE disease dominant-negative")
EuropePMC_search_articles(query="GENE disease antimorphic OR dominant-negative")
EBIProteins_get_mutagenesis(accession="...")
EBIProteins_get_variation(accession="...")
UniProt_get_function_by_accession(accession="...")
```

## Expected Behaviors

### DN-only missense disease and a truncating variant

Input evidence: autosomal dominant disease caused by dominant-negative missense variants; haploinsufficiency is not established; the variant under assessment is an early nonsense predicted to undergo NMD.

Expected: do not apply PVS1 solely because the variant is null. Report `DN established` or `DN plausible` for the missense disease mechanism and mark the truncating variant as not fitting the established DN variant class unless a separate HI/LoF disease mechanism is supported.

### DN assay with WT+variant co-expression

Input evidence: a missense variant is tested in a WT+variant co-expression assay and reduces pathway output below the expected 50% dosage effect; controls and replicates are present.

Expected: route to `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`. The assay is DN-capable because it tests interference with wild-type function. PS3 strength still depends on assay validation, controls, thresholds, and OddsPath or control counts.

### Variant-only functional assay

Input evidence: assay tests variant protein alone and shows normal activity; disease mechanism is suspected dominant-negative.

Expected: do not apply BS3 from this assay alone. A normal variant-only assay does not exclude dominant interference. Require WT+variant co-expression, heterozygous/endogenous model, complex assembly, or disease-relevant pathway assay before using BS3.

### PS1 or PM5 same-residue comparison

Input evidence: a known pathogenic variant at the same residue is dominant-negative; the VUA changes the residue differently.

Expected: PM5 may be considered only if the residue/region is linked to the same DN mechanism. If the known variant's pathogenicity is from DN but the VUA likely causes NMD, splicing LoF, or unrelated GoF, withhold PM5 or downgrade according to disease-specific guidance.

### PM1 hotspot in a DN region

Input evidence: variant lies in an oligomerization interface where multiple pathogenic DN missense variants cluster and benign variation is low.

Expected: PM1 can be appropriate if the region is disease-relevant and low benign variation is documented. Use `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` for PM1 strength and double-counting checks.

### PP3 high score in a DN gene

Input evidence: REVEL is high for a missense variant in a DN disease gene.

Expected: PP3 can support generic missense deleteriousness through `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement`, but the high score does not prove DN mechanism. Keep the mechanism statement separate.

### BP1 in a mixed-mechanism gene

Input evidence: truncating variants cause one disease by haploinsufficiency, while missense variants cause another autosomal dominant disease by DN.

Expected: do not apply BP1 to a missense variant until the disease context is separated. BP1 may be reasonable only for a disease context where missense pathogenicity is unsupported.

### PP1 segregation

Input evidence: a missense variant segregates in a family with an autosomal dominant phenotype and the gene's established disease mechanism is DN missense.

Expected: use the DN mechanism check as the qualifying-variant rationale, then apply `tooluniverse-acmg-pp1-segregation-refinement` for meioses, LOD, penetrance, and phenocopy handling.

### PM3 in a gene with recessive and dominant DN diseases

Input evidence: the same gene has recessive LoF disease and dominant DN disease.

Expected: keep disease entities separate. Do not use a dominant DN variant as the other allele for PM3 in a recessive disease unless it is established as a qualifying pathogenic allele for that recessive context.

## Reporting Template

```text
Dominant-negative mechanism refinement:
- Gene-disease context: [gene], [disease], [inheritance]
- Mechanism status: [DN established / DN plausible / DN uncertain / DN not supported / Mixed mechanism]
- Sources: [curated databases and literature]
- Variant class fit: [fits / partial / does not fit / unclear]
- Product-expression assumption: [expressed altered product / NMD / NMD escape / unknown]
- Evidence routing:
  - PVS1: [allowed / withhold / separate LoF disease context]
  - PS3/BS3: [DN-capable assay required or available]
  - PS1/PM5: [same-mechanism comparison required]
  - PM1/PP2/PP3/BP1: [missense-mediated mechanism notes]
  - PP1/PS2/PM6/BS4: [variant class plausibility notes]
  - PM4/BP3: [in-frame DN region check]
  - PS4/PM3: [mechanism stratification notes]
```
