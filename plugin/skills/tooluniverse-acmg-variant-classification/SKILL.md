---
name: tooluniverse-acmg-variant-classification
description: ACMG/AMP germline variant interpretation intake and overlay-gated classification workflow. Use only through the ACMG overlay routing core and validator-gated assessment bundle. Does not itself produce a final five-tier verdict unless validator_status is PASS, semantic_combiner_status is PASS, final_classification_allowed is true, and final combiner validation succeeds.
disable-model-invocation: true
---

# ACMG/AMP Variant Classification

## ACMG Reasoning

Each criterion (PS, PM, PP for pathogenic; BS, BP for benign) contributes a weighted piece of evidence for or against pathogenicity. The classification is the COMBINATION of all activated criteria, not any single criterion. Do not overweight a single finding.

The hierarchy is: PVS1 (very strong) > PS (strong) > PM (moderate) > PP (supporting). On the benign side: BA1 (stand-alone) > BS (strong) > BP (supporting). A source label such as a ClinVar expert-panel, HGMD, LOVD, or published ACMG classification is not itself a counted criterion; use it as a lead to retrieve primary evidence and route that evidence to the appropriate overlay before combining criteria. A single PP criterion alone is not enough. The combination rule is what matters.

Two common errors to avoid: (1) seeing a "Pathogenic" or "Benign" ClinVar entry and counting PP5/BP6 — ClinGen SVI recommends discontinuing PP5/BP6, so secondary assertions should be used as leads to retrieve primary evidence; (2) treating arbitrary predictor disagreement as benign — PP3/BP4 should follow calibrated predictor rules or a VCEP specification, and non-applied prediction evidence is neutral rather than benign.

Always apply criteria conservatively. When evidence is ambiguous, leave the criterion unmet. Cite the source for every criterion you activate so clinicians can audit the reasoning.

When this skill is imported into another agent, the agent must not use this base workflow to bypass overlay rules. For every criterion covered by an overlay, record whether the overlay was `overlay_applied`, `overlay_not_applicable`, `overlay_not_assessed`, or `overlay_deferred_to_vcep`. Do not hand-assign refined strengths in the main workflow just because evidence appears obvious.

**KEY PRINCIPLES**:
1. **Criteria-driven** — cite which criteria were activated and why
2. **Conservative** — do not upgrade a criterion when evidence is ambiguous
3. **Gene-aware** — adjust thresholds based on gene mechanism (LOF, gain-of-function, dominant-negative, mixed mechanism)
4. **Population-calibrated** — use ancestry-specific gnomAD frequencies, not just global AF
5. **Transparent** — show evidence for each criterion
6. **Source-referenced** — every criterion activation must cite the database/tool source
7. **English-first queries** — always use English terms in tool calls; respond in user's language

---

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## When to Use

- "Classify BRCA2 c.5946delT using ACMG criteria"
- "Is this VUS pathogenic? NM_000059.4:c.7397T>C"
- "Apply ACMG guidelines to rs28897743"
- "What is the pathogenicity of CFTR p.Arg117His?"
- "ACMG classification for TP53 R248W"

---

## Tool Parameter Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `VariantValidator_validate_variant` | `variant_description`, `genome_build`, `select_transcripts` | genome_build="GRCh38" |
| `VariantValidator_gene2transcripts` | `gene_symbol` | Returns MANE Select transcript |
| `MyVariant_query_variants` | `query` | HGVS or rsID. Returns ClinVar, gnomAD, CADD, REVEL, SIFT, PolyPhen |
| `EnsemblVEP_annotate_hgvs` | `hgvs_notation` | Consequence, colocated variants, ancestry gnomAD |
| `gnomad_search_variants` | `query` | rsID to gnomAD variant ID |
| `gnomad_get_variant` | `variant_id` | Per-ancestry population frequencies |
| `gnomad_get_gene_constraints` | `gene_symbol` | pLI, LOEUF, mis_z |
| `ClinVar_search_variants` | `query` | Variable response format: list OR `{status, data}` |
| `ClinVar_get_variant_details` | `variant_id` | ClinVar numeric ID |
| `civic_get_variants_by_gene` | `gene_id` | CIViC numeric gene ID (NOT symbol). Known: BRAF=5, BRCA2=19 |
| `MedGen_search_conditions` | `query` | MedGen aggregates OMIM, Orphanet, ClinVar, HPO, GTR, and GeneReviews; use to discover GeneReviews disease chapters when mechanism or inheritance is unclear |
| `UniProt_get_function_by_accession` | `accession` | Returns list of strings |
| `InterPro_get_entries_for_protein` | `accession` | Domain architecture by UniProt accession |
| `alphafold_get_prediction` | `qualifier` | UniProt accession; pLDDT confidence |
| `PubMed_search_articles` | `query`, `limit` | Returns list of dicts |
| `MyGene_query_genes` | `query` | Filter by `symbol` match (first hit may not match) |

---

## Phase 0: Variant Validation and Normalization

Wrong HGVS or wrong transcript cascades errors through every downstream criterion. Validate first.

1. **Get MANE Select transcript**: `VariantValidator_gene2transcripts(gene_symbol="BRCA2")`
2. **Validate variant**: `VariantValidator_validate_variant(variant_description="NM_000059.4:c.5946delT", genome_build="GRCh38", select_transcripts="mane_select")`
3. **Resolve gene IDs**: `MyGene_query_genes(query="BRCA2")` — extract Ensembl ID and UniProt accession. Filter results by `symbol == 'BRCA2'` (first hit may not match).
4. **Record**: HGVS coding, HGVS protein, genomic coordinates, variant type (frameshift/missense/nonsense/splice/synonymous/in-frame indel).

Accepted inputs: HGVS coding (NM_000059.4:c.5946delT), HGVS protein (BRCA2 p.Val600Glu), rsID (rs28897743), gene+change (BRCA1 c.68_69del), genomic coordinates.

---

## Phase 0a: Overlay Routing Core

Use `tooluniverse-acmg-overlay-routing-core` before evidence-specific overlays. This skill is the dispatcher/reporting workflow: normalize the variant, establish disease/mechanism context, select route bundles, expand triggered bundles into overlay route rows, run overlays, resolve compatibility, and only then combine evidence.

The routing core is the source of truth for anti-bypass rules, canonical status values, guidance-authority labels, bundle details, coverage audit, source-lead handling, and Evidence Compatibility Resolution. Do not duplicate or override those rules here.

Hard gate for external agents: before presenting any final ACMG classification, emit an `acmg_assessment_bundle` compatible with `tooluniverse-acmg-overlay-routing-core/schemas/acmg_assessment_bundle.schema.json` and validate it with `tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py`. If the validator returns `DRAFT_ONLY` or `FAIL`, keep `classification_status: draft classification`; do not compute or present the final ACMG tier from unrouted evidence.

Any final five-tier ACMG answer must include a validator summary block equivalent to:

```json
{"validator_status":"PASS","semantic_combiner_status":"PASS","violations":[]}
```

If the validator summary is absent, malformed, not `PASS`, or has `semantic_combiner_status` other than `PASS`, use `classification_status: draft classification` and do not present `Pathogenic`, `Likely Pathogenic`, `VUS`, `Likely Benign`, or `Benign` as a final classification. Automated classifier outputs such as GeneBe, ClinVar-derived summaries, commercial/lab labels, or paper ACMG labels are `source_assertions_or_leads`; they are not overlay results and must not be inserted into counted evidence without the responsible overlay or VCEP route.

Create a structured `Bundle Route Plan` using the routing core's Route Bundle Quick Planner, then expand triggered bundles into `route_plan.schema.json` rows before any evidence is counted. A bundle row is never counted evidence. Criterion ownership, including the PS1 split and BP1 route, is defined only in the routing core Criterion Ownership Index.

---

## Phase 0b: Gene-Disease Mechanism Check

Use the routing core before mechanism-sensitive criteria. In short, run multiple-disorder context first if evidence may cross disease boundaries, then run dominant-negative/mechanism refinement if variant class, product expression, LoF/HI, GoF, DN, or mixed mechanism could change criterion use.

PVS1 must have a direct LoF/haploinsufficiency source for the exact gene-disease context, or a mechanism-refinement result showing PVS1 is allowed for that context. Do not transfer evidence between recessive LoF, haploinsufficiency, dominant-negative, gain-of-function, splicing LoF, and other mechanisms without a same-mechanism rationale.

Do not infer dominant-negative mechanism from autosomal dominant inheritance alone. Use curated mechanism sources, VCEP guidance, G2P/ClinGen/GenCC, dosage sensitivity, GeneReviews/NCBI Bookshelf disease chapters, functional assay literature, and protein biology.

GeneReviews should be queried when inheritance, disease spectrum, or mechanism routing is unclear, especially for genes with both dominant and recessive disease associations or for structural/complex proteins. Treat GeneReviews as expert review/background support for gene-disease mechanism, inheritance, phenotype spectrum, and management. Do not treat GeneReviews as a VCEP criteria specification or as primary variant-level evidence for PS3, PS4, PP1, PM3, or BS4 unless it cites and you separately evaluate the underlying primary evidence.

```python
ClinGen_search_gene_validity(gene="...")
ClinGen_search_dosage_sensitivity(gene="...")
G2P_search(query="...")
MedGen_search_conditions(query="GENE disease GeneReviews")
PubMed_search_articles(query="GENE disease dominant-negative")
```

---

## Phase 1: Population Frequency (BA1, BS1, BS2, PM2)

Use the `population_frequency_bundle` and route to the owning overlays instead of assigning frequency evidence in this dispatcher:

- `tooluniverse-acmg-ba1-exception-list-refinement` for BA1 stand-alone review.
- `tooluniverse-acmg-pm2-absence-rarity-refinement` for PM2 absence/rarity, coverage adequacy, and PM2 strength.
- `tooluniverse-acmg-benign-context-refinement` for BS1, BS2, BP2, BP5, and benign-context requirements such as disease prevalence, penetrance, ancestry, unaffected-carrier interpretability, phase, and alternate diagnosis.

Population data retrieval is context only until the appropriate overlay returns a routed result. If disease threshold, penetrance, phenotype, unaffected status, phase, or alternate-diagnosis context is missing, report the relevant criterion as `not_assessed` and request the missing fields.

```python
gnomad_search_variants(query="rs28897743")          # get gnomAD variant ID
gnomad_get_variant(variant_id="...")                 # per-ancestry frequencies
gnomad_get_gene_constraints(gene_symbol="BRCA2")     # pLI, LOEUF, mis_z
MyVariant_query_variants(query="rs28897743")          # fallback: gnomad_genome.af
```

If gnomAD data is unavailable, note the gap and continue — absence of data is not the same as evidence of absence.

---

## Phase 2: Computational Predictions (PP3, BP4)

Use `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` for missense prediction evidence. Predictor tools return prediction context only; PP3/BP4 strength must come from the PP3/BP4 overlay or an in-scope VCEP rule. Do not use SIFT/PolyPhen/CADD voting or developer-default thresholds as counted ACMG evidence.

```python
MyVariant_get_pathogenicity_scores(variant_id="...") # REVEL, CADD, SIFT, PolyPhen-2, GERP, PhyloP, VEST4
OpenCRAVAT_annotate_variant(...)              # optional predictor-source fallback
EnsemblVEP_annotate_hgvs(hgvs_notation="...") # consequence, transcript, SIFT/PolyPhen, colocated variants
```

For non-missense variants, skip missense PP3/BP4 and focus on the relevant mechanism-specific evidence. Splice prediction/RNA evidence belongs in Phase 5 and the splicing overlays, not this missense-prediction pathway.

If the gene-disease context may involve dominant-negative, antimorphic, gain-of-function, or mixed mechanisms, run `tooluniverse-acmg-dominant-negative-mechanism-refinement` before using predictor evidence in a missense-mediated disease model. Protein mechanism tools can explain biological plausibility, but they do not change PP3/BP4 strength unless the owning overlay or VCEP says so.

---

## Phase 3: Source Assertions and Comparison Evidence (PS1, PM5, PP5, BP6)

ClinVar, HGMD, VCEP, lab reports, GeneBe/InterVar labels, and paper ACMG codes are source leads until primary evidence is routed. Use:

- `tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement` for protein-level PS1/PM5 comparison evidence.
- `tooluniverse-acmg-ps1-splicing-similarity-refinement` for same predicted splicing-event PS1 comparison evidence.
- `tooluniverse-acmg-pp5-bp6-reputable-source-refinement` for PP5/BP6 source review; by default PP5/BP6 should not be counted and should lead to primary-evidence retrieval.

Do not count comparison evidence unless the owning overlay confirms independence, same disease/mechanism context, non-circularity, and absence of splicing/DNA/RNA confounding.

```python
ClinVar_search_variants(query="BRCA2 c.5946delT")
ClinVar_get_variant_details(variant_id="...")
civic_get_variants_by_gene(gene_id=19)   # BRCA2 CIViC ID is 19
```

---

## Phase 4: Functional Region and Protein-Length Evidence (PM1, PP2, BP1, PM4, BP3)

Use the owning overlays instead of assigning these criteria in the dispatcher:

- `tooluniverse-acmg-pm1-regional-missense-constraint-refinement` for PM1, PP2, BP1, regional missense constraint, hotspot, critical residue, and PM1/PP2/BP1 priority.
- `tooluniverse-acmg-pm4-bp3-protein-length-refinement` for PM4/BP3 protein-length, in-frame indel, repeat-region, stop-loss, and altered-product contexts.

Broad domain membership, mechanism hypotheses, and source labels are leads only. Run dominant-negative/mechanism refinement before PM1/PP2/BP1 when DN/GoF/mixed mechanism could affect criterion use.

```python
UniProt_get_function_by_accession(accession="P51587")        # active sites, binding sites
InterPro_get_entries_for_protein(accession="P51587")          # domain architecture
alphafold_get_prediction(qualifier="P51587")                   # pLDDT > 90 = structured region
gnomad_get_gene_constraints(gene_symbol="BRCA2")              # mis_z for PP2/BP1
```

---

## Phase 5: LoF and Splicing Evidence (PVS1, BP7, PS1-Splicing)

Use `tooluniverse-acmg-pvs1-lof-decision-tree-refinement` for the baseline Abou Tayoun et al. 2018 PVS1 decision tree and `tooluniverse-acmg-pvs1-splicing-refinement` only when RNA assay, observed transcript consequence, published RNA-splicing evidence, or no-splicing-impact RNA evidence affects PVS1/BP7. SpliceAI-only evidence is prediction context and must not trigger RNA-assay PVS1 by itself.

Use dominant-negative/mechanism refinement before PVS1 when LoF/HI applicability is uncertain or the gene-disease context has DN, GoF, recessive LoF, or mixed mechanisms. Use PS1-splicing only for independent comparison-variant evidence and let Evidence Compatibility Resolution remove duplicate PP3/PS3/BS3/RNA uses.

```python
EnsemblVEP_annotate_hgvs(hgvs_notation="...")   # splice_donor_variant, splice_acceptor_variant
MyVariant_query_variants(query="...")             # SpliceAI deltas
gnomad_get_gene_constraints(gene_symbol="...")    # pLI >= 0.9 or LOEUF < 0.35 = LOF intolerant
```

---

## Phase 6: Literature and Clinical/Functional Evidence (PS3, BS3, PS4, PP1, PP4)

Well-designed functional assays showing LOF (PS3) or normal function (BS3) can shift a classification decisively. PS3/BS3 can be downgraded (e.g., PS3_Supporting) for less rigorous assays. Not all functional assays qualify — ClinGen gene-specific guidance defines valid assays. When biochemical, cellular, model-organism, patient-derived, MAVE/DMS, or other functional assay evidence affects PS3/BS3 strength, use `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`. That overlay adapts Brnich et al. 2019 ClinGen SVI functional-evidence guidance: start from no functional evidence, require disease-mechanism fit and assay-instance validation, use control-count or OddsPath calibration for strength, and avoid double-counting the same assay as PP3/BP4 or RNA-specific PVS1/BP7 evidence. Do not apply PS3 from case reports, segregation, HGMD/ClinVar labels, or another paper's ACMG classification unless the underlying functional assay is retrieved and evaluated by the PS3/BS3 overlay.

Multiple historical functional assays are not automatically cumulative. Count PS3/BS3 once at the strength justified by the most disease-relevant and best-validated assay, unless a current VCEP, OddsPath analysis, or explicit validated combination rule permits combining independent assays.

When the asserted or possible functional mechanism is dominant-negative, antimorphic, or mixed, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` first to decide whether the assay must test WT+variant interference, heterozygous/endogenous context, complex assembly, or pathway output. Then use the PS3/BS3 overlay for strength.

PP1/BS4 should be routed through `tooluniverse-acmg-pp1-segregation-refinement` when published family segregation, LOD/likelihood evidence, informative meioses, diagnostic yield, locus homogeneity/heterogeneity, reduced penetrance, phenocopy, or non-segregation affects evidence strength. That overlay owns PP1/BS4/PP4 combined scoring, the +5.0 cap, and evidence apportionment when segregation and phenotype specificity interact.

When a criterion requires patient phenotype, affected/unaffected status, disease specificity, diagnostic yield, tested/excluded loci, or alternate-diagnosis context, use `tooluniverse-acmg-phenotype-dependent-evidence-refinement` for intake. If the criterion only needs disease-context inputs such as prevalence, penetrance, inheritance, mechanism, transcript, or frequency threshold, retrieve those through ToolUniverse disease/population resources and route directly to the evidence-specific overlay. If PP4 may combine with PP1/BS4, route scoring to the PP1 overlay.

For PS4 affected-case enrichment, use `tooluniverse-acmg-ps4-case-enrichment-refinement`. Prefer formal case-control evidence with odds ratio, confidence interval, ancestry-matched cases and controls, and disease-specific frequency context. When formal case-control data are unavailable, ACGS-style rare-disease counting may support `PS4_Supporting` for one unrelated affected individual with a rare/specific matching phenotype and absent population-control evidence, and `PS4_Moderate` for two or more unrelated affected individuals after duplicate-reporting, phenotype, ancestry, and control checks only as `practice/local refinement` unless a VCEP adopts those case-count rules. Recessive rare biallelic affected-proband evidence belongs in PM3, not PS4.

Founder haplotypes, shared ancestry, mutation-positive cohorts, or repeated reports in a case series are not ordinary case-control enrichment. Before using them for PS4, document the disease-case denominator, whether cases are unrelated, founder/duplicate status, ancestry-matched controls, and whether gnomAD is suitable as a control. Do not convert a mutation-positive proband denominator into a full disease-cohort enrichment statistic.

When ACMG evidence depends on visual material in a paper or supplement, such as pedigrees, segregation diagrams, Sanger traces, RT-PCR/minigene figures, gels, blots, or functional assay plots, use `tooluniverse-literature-figure-evidence-extraction` first to produce structured figure evidence. Then pass those extracted facts to the relevant evidence-specific overlay. Use `tooluniverse-image-analysis` only when the task requires quantitative image-derived measurements or statistics.

Low-confidence OCR, cropped figures, unreadable labels, or `not_interpretable` figure extraction can be used only as a lead. Do not upgrade PP1, PS4, PS3/BS3, PM3, or PS2/PM6 from figure evidence unless the figure extraction provides source/panel, sample ID, genotype, phenotype or assay readout, confidence, and ambiguity notes.

```python
PubMed_search_articles(query="BRCA2 c.5946delT functional assay", limit=10)
PubMed_search_articles(query="BRCA2 c.5946delT segregation family", limit=5)
```

Criteria requiring user-supplied patient or family clinical data (PS2, PM3, PM6, BS4, BP2, BP5, BS2, PP4, and some VCEP-specific rules) cannot be assessed automatically. Use routing-core status `not_assessed` and request targeted missing fields rather than inferring clinical data from variant annotation. PS4 is mixed: formal case-control, cohort, or meta-analysis evidence can be assessed from literature or cohort data when the publication defines cases, disease context, controls, ancestry handling, and statistics sufficiently; rare-disease affected-case counting still requires affected-case phenotype, unrelatedness, duplicate-report, and control context from the paper, database, or user. Use `tooluniverse-acmg-de-novo-evidence-refinement` for PS2/PM6 whenever de novo status, parental testing, parentage confirmation, parental mosaicism, or phenotype consistency is relevant.

Use standard user-input request blocks when fields are missing:

- `clinical_phenotype_needed`: HPO terms, clinical diagnosis, age, sex when relevant, age of onset, severity, tested/excluded diagnoses, and phenotype specificity.
- `pedigree_or_phase_needed`: affected/unaffected relatives, genotype status, relationship, age at evaluation, phenotype details, phasing method, and whether phenocopy or reduced penetrance is plausible.
- `de_novo_needed`: proband genotype, mother/father genotypes, biological relationship confirmation, parental mosaicism assessment, and phenotype consistency.
- `literature_source_needed`: PMID/DOI/source name, requested PDF/supplement/figure/table, why abstract-only evidence is insufficient, and affected criteria.
- `disease_context_needed`: disease entity, inheritance, mechanism, penetrance, prevalence, age of onset, and VCEP/gene-specific rule scope.

When affected-proband biallelic evidence is available for a recessive disorder, use `tooluniverse-acmg-pm3-in-trans-refinement` to score PM3 using ClinGen SVI PM3 v1.0 points while checking PM2-level rarity, phase, other-allele classification, and circularity. Recessive biallelic probands with genotype/phase evidence should route to PM3 rather than PS4 unless a VCEP specifies otherwise.

PM4 (protein length change in non-repeat region) and BP3 (in-frame indel in repeat) are routed through `tooluniverse-acmg-pm4-bp3-protein-length-refinement` in Phase 4. If an in-frame protein length change may preserve an altered product in a dominant-negative or complex-mediated disease context, use `tooluniverse-acmg-dominant-negative-mechanism-refinement` before assigning PM4 or BP3. BP7 for synonymous or intronic variants requires the appropriate no-splicing-impact context and route audit; SpliceAI low score alone is prediction context, not a direct BP7 assignment. RNA-specific BP7 is handled through the PVS1/RNA splicing overlay when direct RNA evidence exists.

Before combining evidence, run an overlay compliance audit:

| Evidence source observed | Required route before counting |
| --- | --- |
| ClinVar, HGMD, LOVD, expert panel, paper classification, or lab report says P/LP/B/LB | PP5/BP6 source review, then primary evidence overlays; do not count the label itself. |
| Functional assay, MAVE/DMS, patient-derived cellular assay, animal model, protein/RNA assay | PS3/BS3 functional-assay overlay, unless RNA evidence is routed to PVS1/BP7 splicing. |
| Segregation, non-segregation, family pedigree, LOD, informative meioses | PP1/BS4/PP4 overlay, not PS3. |
| Case-control, cohort, meta-analysis, unrelated affected case counts | PS4 overlay, or PM3 if recessive biallelic probands with phase/genotype evidence. |
| Missense prediction scores | PP3/BP4 calibrated prediction overlay or VCEP; do not use local predictor voting. |
| Same codon/residue comparison variant | PS1/PM5 overlay; verify independent P/LP status and amino-acid-mediated mechanism. |
| Protein domain, hotspot, regional constraint, broad domain membership | PM1 overlay; broad domain membership alone is not enough. |

Hard-stop rule: if any evidence row in the final counted table lacks a valid route outcome, stop and label the report `draft classification`. The classification algorithm below is applied only after the audit table contains no un-routed counted criteria and evidence compatibility resolution has produced `current_counted_evidence_resolved` with no unresolved conflicts.

---

## Phase 7: Evidence Compatibility Resolution

After the hard-stop audit passes, run Evidence Compatibility Resolution through `tooluniverse-acmg-overlay-routing-core` before any final combination.

This gate does not assign evidence strength. It resolves already-routed evidence before combine by keeping, dropping, capping, splitting, deferring to VCEP, or blocking incompatible evidence. The complete compatibility matrix lives in `tooluniverse-acmg-overlay-routing-core`; do not duplicate or locally reinterpret it here.

Required outputs:

- `current_counted_evidence_resolved`: only these evidence items may enter final combine.
- `not_used_due_to_overlap`: evidence removed because the same primary evidence, proband, assay, source, mechanism, or region was consumed elsewhere.
- `caps_applied`: PM1+PP3, PP1+PP4, PM3 homozygous, PS2/PM6 high-heterogeneity, or VCEP caps.
- `context_splits`: separate disease, inheritance, mechanism, or transcript contexts that require separate classifications.
- `unresolved_conflicts`: unresolved conflicts that block final classification.

If `unresolved_conflicts` is not empty, report `draft classification` and do not run ACMG qualitative or Bayesian final combine.

---

## Phase 8: Bayesian Evidence Combination

After compatibility resolution passes, use `tooluniverse-acmg-bayesian-classification-framework` to convert `current_counted_evidence_resolved` into Tavtigian et al. 2018 Bayesian points, OddsPath, posterior probability, and a structured final report.

This final combination layer is not an evidence-assignment overlay. It must not retrieve evidence, decide whether criteria are met, or change the strength assigned by evidence-specific overlays or VCEP rules.

Use these boundaries:

- If BA1 is valid, short-circuit before Bayesian calculation and report Benign by BA1 stand-alone.
- If any counted evidence lacks route outcome `overlay_applied` or `overlay_deferred_to_vcep`, output `draft classification` and do not compute final posterior probability.
- If evidence compatibility resolution has not produced `current_counted_evidence_resolved`, output `draft classification` and do not compute final posterior probability.
- If evidence compatibility resolution contains unresolved conflicts, output `draft classification` and do not compute final posterior probability.
- If a VCEP defines a disease-specific combining framework, follow the VCEP and report Tavtigian-style posterior only as optional context when appropriate.
- Do not use Bayesian points to convert source assertions, unrouted candidate evidence, abstract-only evidence, unread supplements, or low-confidence figure extraction into counted criteria.

The Bayesian framework reports both readable points and probability:

| Evidence strength | Points |
| --- | ---: |
| Pathogenic VeryStrong | `+8` |
| Pathogenic Strong | `+4` |
| Pathogenic Moderate | `+2` |
| Pathogenic Supporting | `+1` |
| Benign Strong | `-4` |
| Benign Supporting | `-1` |

Default formula from Tavtigian et al. 2018 and Supplemental Table S1:

```text
OddsPath = 350^(total_points / 8)
Post_P = OddsPath * 0.10 / ((OddsPath - 1) * 0.10 + 1)
```

Later benign strengths not present in Tavtigian et al. 2018, such as `BP4_Moderate`, `BP4_VeryStrong`, or `BS3_Moderate`, require explicit VCEP, ClinGen/SVI extension, or local-policy conversion before entering the Bayesian calculator.

---

## Classification Algorithm

Combine criteria at their resolved applied strength after overlay route audit and evidence compatibility resolution:

**Pathogenic**: (1) PVS1 + ≥1 Strong; (2) PVS1 + ≥2 Moderate; (3) PVS1 + 1 Moderate + 1 Supporting; (4) PVS1 + ≥2 Supporting; (5) ≥2 Strong; (6) 1 Strong + ≥3 Moderate; (7) 1 Strong + 2 Moderate + ≥2 Supporting; (8) 1 Strong + 1 Moderate + ≥4 Supporting

**Likely Pathogenic**: (1) PVS1 + 1 Moderate; (2) 1 Strong + 1-2 Moderate; (3) 1 Strong + ≥2 Supporting; (4) ≥3 Moderate; (5) 2 Moderate + ≥2 Supporting; (6) 1 Moderate + ≥4 Supporting

**Benign**: (1) BA1 stand-alone; (2) ≥2 Strong benign

**Likely Benign**: (1) 1 Strong benign + 1 Supporting benign; (2) ≥2 Supporting benign

**VUS**: Criteria do not meet any threshold above, OR pathogenic and benign evidence conflict.

---

## Output Format

```markdown
# ACMG Variant Classification Report

## Variant Normalization
- Variant:
- Gene:
- Transcript:
- Genome build:
- Consequence:

## Disease / Mechanism Context
- Disease context:
- Inheritance:
- Mechanism:
- Multiple-disorder boundary:
- Penetrance context:
- VCEP context:

## Evidence Retrieval Coverage
- Population:
- Computational:
- Clinical databases and source assertions:
- Literature and supplements:
- Functional / segregation / case evidence:

## Bundle Route Plan
| Bundle | Trigger found? | Required overlays/checks | Coverage required | Status | Reason |
| --- | --- | --- | --- | --- | --- |

## Overlay Results
| Overlay / VCEP | Criterion | Status | Applied evidence | Guidance authority | Consumed evidence | Reason |
| --- | --- | --- | --- | --- | --- | --- |

## Overlay Route Audit
| Criterion | Route bundle | Proposed evidence | Route outcome | Guidance authority | Overlay or VCEP source | Counted? | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Evidence Compatibility Resolution
- current_counted_evidence_resolved:
- not_used_due_to_overlap:
- caps_applied:
- context_splits:
- unresolved_conflicts:

| Conflict group | Evidence items | Conflict type | Resolution | Kept evidence | Removed/capped evidence | Status | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Current Counted Evidence Resolved
| Criterion | Direction | Strength | Points | Evidence | Overlay route outcome | Source |
| --- | --- | --- | ---: | --- | --- | --- |

## Bayesian Calculation
- Model: Tavtigian et al. 2018 Bayesian ACMG/AMP framework
- Prior probability:
- Very Strong OddsPath:
- Exponential progression:
- Total points:
- OddsPath:
- Posterior probability:
- Formula source:

## Final Classification
- Classification status: [final classification / draft classification]
- Classification: [PATHOGENIC / LIKELY PATHOGENIC / VUS / LIKELY BENIGN / BENIGN / not computed because route audit failed]
- ACMG/AMP qualitative table comparison:
- VCEP override, if any:

## Source Assertions / Leads
machine key: `source_assertions_or_leads`

| Source | Assertion | Why not counted directly | Routed primary evidence |
| --- | --- | --- | --- |

## Missing Evidence / Not Assessed
machine key: `missing_not_assessed`

| Criterion | Missing field or unavailable source | Impact |
| --- | --- | --- |

## User-Needed Inputs
machine key: `user_needed_inputs`

| Missing input type | Requested details | Why needed | Affected criteria |
| --- | --- | --- | --- |
```

---

## Common Patterns

**Pattern 1: Known pathogenic frameshift** — "Classify BRCA2 c.5946delT"
Phase 0 (validate) → Phase 1 (gnomAD absent/rare population context routed to the PM2 overlay) → Phase 3 (ClinVar Pathogenic assertion used as lead only; no PP5) → Phase 4 (DNA repair domain routed to PM1 only if the PM1 overlay confirms an eligible critical region) → Phase 5 (frameshift + LOF gene routed to the PVS1 decision-tree overlay) → Phase 6 (functional assay evidence routed to PS3/BS3 if present)
Final result can be reported only after route audit, Evidence Compatibility Resolution, and validator PASS; PP5 is not counted from the ClinVar source label.

**Pattern 2: Missense VUS** — "Is BRCA1 p.Arg1699Gln pathogenic?"
Phase 0 → Phase 1 (rare population context routed to the PM2 overlay) → Phase 2 (REVEL score routed to the calibrated PP3/BP4 missense-prediction overlay) → Phase 3 (ClinVar VUS source lead) → Phase 4 (BRCT domain routed to PM1/PP2/BP1; PM1+PP3 cap handled by compatibility resolution) → Phase 6 (reduced activity routed to PS3/BS3 functional-assay overlay)
Final result can be reported only after route audit, Evidence Compatibility Resolution, validator PASS, and documentation of the PM1+PP3 cap.

**Pattern 3: Common benign variant** — "ACMG for rs1800497"
Phase 1 (gnomAD AF=0.21, BA1 exception-list overlay confirms no exception and adequate general population data) → BA1 stand-alone gate. Final Benign output still requires route audit and validator PASS documenting the BA1 route.

**Pattern 4: Deep-intronic variant** — "Classify NM_000059.4:c.7977+100A>G"
Phase 1 (check AF) → splice prediction context such as a low SpliceAI score → route audit. Do not assign BP7 or Likely Benign from SpliceAI alone. If no calibrated benign frequency evidence, RNA no-impact evidence, VCEP rule, or other routed benign evidence is present, keep the result as VUS or `draft classification` depending on route completeness.
