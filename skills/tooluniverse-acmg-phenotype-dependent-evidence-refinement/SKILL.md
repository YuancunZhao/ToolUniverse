---
name: tooluniverse-acmg-phenotype-dependent-evidence-refinement
description: Refine ACMG/AMP evidence criteria that require patient phenotype, disease specificity, affected status, or phenotype-match context. Use with ToolUniverse ACMG classification when PP4, PS4, PP1/BS4, PM3, BP5, BS2, PS2/PM6 phenotype consistency, or other clinical-context-dependent criteria cannot be assessed without phenotype information. Route PP4 that interacts with segregation/non-segregation through the ClinGen 2024 combined PP1/BS4/PP4 guidance in the PP1 overlay.
disable-model-invocation: true
---

# ACMG Phenotype-Dependent Evidence Refinement

This skill extends `tooluniverse-acmg-variant-classification` by defining a lightweight intake and routing layer for ACMG evidence criteria that require phenotype, affected status, or disease-match context.

It does not create new evidence codes and does not replace evidence-specific overlays. It prevents ToolUniverse from guessing phenotype-dependent evidence when the user has not provided enough clinical context.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, source-review, double-counting, and output-status conventions. This overlay is the clinical-context intake step; criterion-specific scoring remains in the relevant evidence overlay.

When PP4 phenotype specificity is considered together with family segregation or non-segregation, this skill performs phenotype intake only. Use `tooluniverse-acmg-pp1-segregation-refinement` for Biesecker et al. 2024 ClinGen combined PP1/BS4/PP4 points, diagnostic-yield conversion, locus-evidence cap, and evidence apportionment.

---

## When to Use This Skill

Use this skill when an ACMG classification may depend on:

- `PP4`: phenotype or family history highly specific for a disease with a single genetic etiology.
- `PS4`: significantly increased prevalence of the variant in affected individuals compared with controls.
- `PP1` or `BS4`: segregation or non-segregation in affected and unaffected relatives.
- `PM3`: affected proband observations for recessive in-trans or phase-unknown variants.
- `BP5`: an alternate molecular basis for the patient's disease.
- `BS2`: observation in healthy adult individuals where disease penetrance and phenotype status matter.
- `PS2` or `PM6`: de novo evidence where phenotype consistency affects whether the observation is relevant.
- Any VCEP rule requiring phenotype specificity, HPO terms, disease onset, penetrance, severity, or affected/unaffected status.
- Any case where PP4 may be linked to PP1/BS4 because the same phenotype/locus evidence is being used for segregation.

Do not infer these criteria from variant annotation alone.

---

## Required Phenotype Intake

Before applying phenotype-dependent evidence, collect the minimum clinical context needed for the criterion under consideration.

Ask the user for missing information when it is not present in the prompt, literature excerpt, case table, or supplied report.

Minimum useful phenotype fields:

- Proband phenotype summary.
- HPO terms, if available.
- Suspected disease or disease spectrum.
- Age at onset and current age.
- Disease severity and key positive/negative features.
- Inheritance model being evaluated.
- Family history and affected/unaffected relative status, if relevant.
- Whether the phenotype is highly specific for the gene/disease or broadly nonspecific.
- Any known alternate molecular diagnosis.

If these fields are missing, report the affected criteria as `Not Assessed - phenotype required` and ask targeted follow-up questions.

---

## ToolUniverse Evidence Retrieval

Use ToolUniverse tools to contextualize the supplied phenotype; do not use them to invent a patient phenotype.

Recommended tools:

| Tool | Use |
|------|-----|
| `ClinGen_search_gene_validity` | Confirm gene-disease validity and disease scope. |
| `GenCC_search_gene` | Cross-check gene-disease validity, inheritance, and mechanism. |
| `MedGen_search_conditions`, `MedGen_get_condition`, `MedGen_get_clinical_features` | Disease synonyms, OMIM cross-references, inheritance, and HPO clinical features. |
| `Mondo_get_disease`, `Mondo_get_disease_phenotypes` | Normalize disease names and retrieve disease-associated HPO phenotypes. |
| `HPO_get_diseases_by_phenotype`, `HPO_get_genes_by_phenotype` | Map supplied HPO terms to diseases and candidate genes. |
| `MyDisease_get_disease` | Retrieve disease annotations, HPO links, DisGeNET context, and cross-references. |
| `MonarchV3_get_entity`, `MonarchV3_get_associations` | Cross-check gene-disease and disease-phenotype associations. |
| `PubMed_search_articles` / `EuropePMC_search_articles` | Case-series phenotype, disease specificity, and variant prevalence evidence. |
| `ClinVar_search_variants` / `ClinVar_get_variant` | Variant-level clinical assertions; not sufficient by itself for patient phenotype. |

Use the retrieved disease description only to assess match to user-supplied phenotype.

---

## Criterion Routing

### PP4

Apply PP4 only when the supplied phenotype is highly specific for a disease with a single or narrow genetic etiology, or when a current VCEP explicitly defines phenotype specificity rules.

If PP4 is being considered together with PP1 co-segregation or BS4 non-segregation, route to `tooluniverse-acmg-pp1-segregation-refinement` after collecting phenotype, diagnostic yield, inheritance, and family data. Under Biesecker et al. 2024, PP4 and PP1 are coupled forms of locus evidence and are capped together at +5.0 points; they should not be counted as fully independent criteria.

ACGS 2024 practice guidance broadens the operational framing: PP4 can also be considered when the phenotype is a rare, highly characteristic combination of features with only a limited set of known genetic etiologies and the relevant genes have been appropriately assessed. The phenotype does not have to be absolutely pathognomonic for one gene, but it must be specific enough that a genotype-phenotype match is meaningful.

Use this practical strength ladder unless a VCEP defines different disease-specific rules:

| Phenotype evidence | Default PP4 handling |
| --- | --- |
| Broad, common, or nonspecific features such as isolated developmental delay, seizures, hearing loss, cardiomyopathy, or cancer predisposition without distinctive pattern | No PP4 |
| Phenotype is compatible with the gene-disease association but many unrelated etiologies remain plausible | Usually no PP4, or `PP4_Supporting` only under a current VCEP rule |
| Rare and recognizable phenotype or rare combination of features with a narrow genetic differential and appropriate testing strategy | `PP4_Supporting` |
| Highly specific clinical, biochemical, imaging, methylation, electrophysiology, histopathology, or treatment-response pattern with strong gene-disease fit | Consider `PP4_Moderate` |
| Near-pathognomonic disease-defining phenotype or validated disease-specific biomarker profile with very limited etiologies, after appropriate differential testing | Consider `PP4_Strong` only with VCEP, MDT, or guideline-level support |

Evidence types that can support stronger PP4 include pathognomonic biochemical tests, disease-specific MRI patterns, methylation episignatures, muscle biopsy findings, functional clinical biomarkers, or clinical treatment response where those findings are recognized as disease-defining. Record the testing method and whether the differential diagnosis was adequately excluded.

For diagnostic-yield PP4 under the ClinGen 2024 combined guidance:

- use a robust diagnostic yield for the exact gene-phenotype dyad and comparable testing method;
- round down to the nearest supported diagnostic-yield point value;
- avoid PP4 when diagnostic yield is below about 20% unless a VCEP permits it;
- do not use high PP4 strength from incomplete phenotyping, young age before hallmark features emerge, or broad endophenotypes such as isolated thoracic aortic aneurysm, arrhythmia, intellectual disability, seizures, nonsyndromic hearing loss, or cancer predisposition without a distinctive pattern;
- when the same affected case could support PP4 or PS4, choose one evidence path and document the choice.

Do not double count phenotype specificity. If PS2/PM6 de novo evidence has already been upgraded because the proband phenotype is highly specific for the gene-disease association, do not also apply PP4 from the same phenotype unless a current VCEP explicitly permits both. If a VCEP folds phenotype specificity into PS4 case counting, do not add PP4 separately from the same affected-case ascertainment.

If PP1 is also used, do not stack PP4 and PP1 beyond the ClinGen 2024 combined cap. The PP1 overlay should report the combined points and the chosen code split, such as `PP1_Strong + PP4_Supporting` or `PP4_Strong + PP1`.

Do not apply PP4 when:

- No phenotype is supplied.
- The phenotype is broad, common, or compatible with many unrelated genes.
- The gene-disease association is weak or disputed.
- The phenotype matches a different disease mechanism than the variant being interpreted.
- The only support is that the gene is known for a phenotype, but the patient's actual features were not supplied.
- The same phenotype specificity has already been used to upgrade PS2/PM6, PS4, or another VCEP-specific criterion.

If phenotype is missing, ask:

```text
PP4 requires phenotype specificity. Please provide the proband's key clinical features or HPO terms, suspected disease, age at onset, and any known alternate diagnosis.
```

### PS4

Apply PS4 only when affected-case enrichment is supported by case-control, cohort, or well-curated case-count evidence and the affected individuals have a phenotype matching the gene-disease context.

Do not apply PS4 from isolated case reports without appropriate enrichment or VCEP-approved counting rules.

If affected phenotype details are missing, ask:

```text
PS4 requires affected-case context. Please provide the disease/phenotype used for case ascertainment, number of affected carriers, ancestry or cohort details, and the control comparison or VCEP case-count rule.
```

### PP1 and BS4

Use `tooluniverse-acmg-pp1-segregation-refinement` for segregation scoring, but use this phenotype overlay first when affected/unaffected status or phenotype specificity is unclear.

Collect these PP1/BS4/PP4 combined-guidance fields before routing:

- exact disease or phenotype constellation used for diagnostic yield;
- HPO terms and key positive/negative findings;
- gene-disease dyad and inheritance model;
- whether the phenotype suggests locus homogeneity or locus heterogeneity;
- diagnostic yield and testing method used to derive it;
- genes/loci tested and whether alternative loci were excluded;
- affected and unaffected relatives, genotype status, age, sex when relevant, and phenotype certainty;
- phase and whether more than one plausible candidate variant is present on an implicated allele.

If family phenotype is missing, ask:

```text
PP1/BS4 requires family phenotype status. Please provide which relatives are affected or unaffected, their genotype status, age at evaluation, phenotype details, penetrance assumptions, and whether phenocopy is plausible.
```

### PM3

Use `tooluniverse-acmg-pm3-in-trans-refinement` for PM3 scoring. This phenotype overlay checks whether the proband is affected with the recessive disease being evaluated.

If proband phenotype is missing, ask:

```text
PM3 requires an affected proband in the relevant recessive disease context. Please provide the proband phenotype, suspected diagnosis, zygosity/phase of both variants, and whether the phenotype matches the gene-disease association.
```

### BP5

Apply BP5 only when an alternate molecular basis plausibly explains the patient's phenotype better than the variant under assessment.

Do not apply BP5 when:

- No phenotype is supplied.
- The alternate finding is unrelated to the patient's phenotype.
- The alternate diagnosis does not fully explain the relevant disease features.

If alternate diagnosis context is missing, ask:

```text
BP5 requires phenotype and alternate-diagnosis context. Please provide the patient's phenotype and the alternate pathogenic/likely pathogenic variant or molecular diagnosis proposed to explain it.
```

### BS2

Apply BS2 only when the variant is observed in an individual who is truly unaffected for a disease where age, penetrance, sex, and ascertainment make that observation incompatible with pathogenicity.

If unaffected status is unclear, ask:

```text
BS2 requires reliable unaffected status. Please provide the individual's age, sex if relevant, clinical evaluation, family history, penetrance/onset expectations, and whether the individual was specifically assessed for the disease.
```

### PS2 and PM6 Phenotype Consistency

Use `tooluniverse-acmg-de-novo-evidence-refinement` for de novo strength. This phenotype overlay only ensures that the proband phenotype matches the gene-disease context before de novo evidence is counted.

When de novo evidence strength is increased because the phenotype is highly specific, treat that phenotype specificity as consumed for PS2/PM6 and do not apply a separate PP4 unless a VCEP explicitly allows separate use.

---

## Missing-Information Behavior

If the user has not provided required phenotype information:

1. Do not apply the phenotype-dependent criterion.
2. Mark the criterion as `Not Assessed - phenotype required`.
3. Ask only for the fields needed for the criterion being considered.
4. Continue assessing criteria that do not require phenotype.

Example:

```markdown
Not assessed:
- PP4: phenotype specificity cannot be evaluated without proband clinical features or HPO terms.
- PS2/PM6 phenotype consistency: de novo status may be relevant, but proband phenotype was not provided.

Please provide the proband phenotype or HPO terms, suspected disease, age at onset, and any known alternate diagnosis.
```

---

## Output Format

```markdown
Phenotype-dependent evidence refinement:
- Supplied phenotype: [summary / not provided]
- Normalized phenotype terms: [HPO/MONDO/MedGen if available]
- Gene-disease context: [disease, inheritance, validity]
- Phenotype match: [highly specific / compatible / nonspecific / mismatched / not assessable]
- Criteria affected: [PP4, PS4, PP1, BS4, PM3, BP5, BS2, PS2/PM6, other]
- Missing information: [fields]
- Applied evidence: [criterion and strength / Not Assessed - phenotype required]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Routed to: [criterion-specific overlay if needed]
- Follow-up question to user: [targeted question if needed]
```

---

## Limitations

- This skill does not diagnose the patient and does not infer unprovided phenotype.
- Literature and databases provide disease background, not patient-specific evidence.
- PP4 and phenotype-dependent VCEP rules are disease-specific and should not be generalized across genes.
- Reduced penetrance, variable expressivity, age-dependent onset, phenocopy, and alternate diagnoses can change evidence strength.

---

## Primary References

- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants. Genet Med. 2015;17(5):405-424. PMID: 25741868. DOI: 10.1038/gim.2015.30.
- Strande NT, Riggs ER, Buchanan AH, et al. Evaluating the Clinical Validity of Gene-Disease Associations: An Evidence-Based Framework Developed by the Clinical Genome Resource. Am J Hum Genet. 2017;100(6):895-906. PMID: 28552198. PMCID: PMC5473734.
- Ellard S, Baple EL, Berry I, et al. ACGS Best Practice Guidelines for Variant Classification 2024. Use as practice guidance for phenotype-specific PP4 stratification and phenotype double-counting safeguards.
- Current ClinGen VCEP specifications for disease-specific PP4, PS4, segregation, de novo, and phenotype-match rules.
