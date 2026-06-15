---
name: tooluniverse-acmg-pp5-bp6-reputable-source-refinement
description: Refine ACMG/AMP PP5 and BP6 reputable-source evidence using the ClinGen SVI recommendation by Biesecker and Harrison 2018, PMID 29543229. Use when a database, report, expert source, ClinVar assertion, or other secondary classification is being considered as evidence without directly reviewable primary data.
disable-model-invocation: true
---

# ACMG PP5/BP6 Reputable-Source Refinement

This skill extends `tooluniverse-acmg-variant-classification` for one evidence pair: `PP5` and `BP6`, the original ACMG/AMP reputable-source criteria.

The ClinGen SVI recommendation by Biesecker and Harrison 2018, PMID:29543229, recommends that laboratories discontinue use of PP5 and BP6 as soon as practically achievable. In this ToolUniverse overlay, PP5 and BP6 are not counted as ACMG evidence by default. Reputable-source assertions should instead be used as leads to retrieve primary evidence and then assign the appropriate underlying criteria.

This skill is an overlay only. It does not create a new MCP tool and does not replace disease-specific VCEP specifications.

---

## When to Use This Skill

Use this skill whenever a classification workflow is tempted to apply PP5 or BP6 from:

- ClinVar assertions without directly reviewed supporting evidence;
- laboratory reports or test reports that state Pathogenic, Likely Pathogenic, Benign, or Likely Benign but do not provide primary data;
- locus-specific databases, expert panels, clinical databases, or internal knowledgebases that summarize a variant classification;
- published statements that cite another source's classification without showing the underlying case, segregation, functional, population, computational, or mechanistic evidence;
- automated or aggregate database labels such as "consensus pathogenic" or "benign consensus."

Do not use this skill to evaluate the underlying evidence itself. Once primary evidence is retrieved, route it to the relevant evidence-specific overlay.

---

## Core Principle

Do not count PP5 or BP6 when the only evidence is a secondary assertion.

Reputable-source classifications can be useful for evidence discovery, but they should not be used as independent ACMG evidence when the primary data can be retrieved or requested. This avoids double counting the same evidence that may already support PS3/BS3, PS4, PM2/BA1/BS1, PP1/BS4, PM3, PVS1, PP3/BP4, PS1/PM5, or other criteria.

Default outputs:

- `No PP5`
- `No BP6`
- `PP5_NotUsed`
- `BP6_NotUsed`
- `PP5_NotAssessed - primary evidence required`
- `BP6_NotAssessed - primary evidence required`

Do not output `PP5` or `BP6` as counted evidence unless a current disease-specific VCEP or explicitly approved local policy requires legacy ACMG 2015 usage.

---

## Evidence Retrieval Workflow

Use ToolUniverse tools to turn reputable-source assertions into primary-evidence retrieval tasks.

1. **Normalize the variant**
   - Use `VariantValidator_validate_variant`, `ClinGenAR_lookup_allele`, `EnsemblVEP_annotate_hgvs`, or `MyVariant_query_variants`.
   - Record HGVS c./p./g., transcript, rsID, ClinGen allele registry ID, ClinVar Variation ID, and disease context.

2. **Retrieve secondary assertions**
   - Use `ClinVar_search_variants`, `ClinVar_get_variant`, `ClinGen_get_variant_classifications`, and ClinGen ERepo tools when available.
   - Record classification, submitter or expert panel, review status, assertion criteria provided, condition, date, and conflict status.
   - Treat these as leads unless the underlying evidence is directly available and reviewed.

3. **Extract or request primary evidence**
   - If the assertion has criteria, evidence summaries, citations, submitter comments, or links, retrieve the original evidence.
   - Use `PubMed_search_articles`, `EuropePMC_search_articles`, `tooluniverse-literature-deep-research`, and `tooluniverse-literature-figure-evidence-extraction` for paper-derived cases, figures, tables, functional assays, segregation, or de novo evidence.
   - If primary evidence is unavailable, record `PP5_NotAssessed - primary evidence required` or `BP6_NotAssessed - primary evidence required`.

4. **Route to underlying criteria**
   - Functional data: `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`.
   - Population frequency: `tooluniverse-acmg-pm2-absence-rarity-refinement` or `tooluniverse-acmg-benign-context-refinement`.
   - Segregation or non-segregation: `tooluniverse-acmg-pp1-segregation-refinement`.
   - De novo data: `tooluniverse-acmg-de-novo-evidence-refinement`.
   - In-trans recessive data: `tooluniverse-acmg-pm3-in-trans-refinement`.
   - Case enrichment: `tooluniverse-acmg-ps4-case-enrichment-refinement`.
   - LoF/splicing: `tooluniverse-acmg-pvs1-lof-decision-tree-refinement`, then `tooluniverse-acmg-pvs1-splicing-refinement` when RNA/splicing evidence is present.
   - Computational evidence: `tooluniverse-acmg-pp3-bp4-missense-prediction-refinement` or splicing-specific overlays.
   - Protein comparison evidence: `tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement` or `tooluniverse-acmg-ps1-splicing-similarity-refinement`.

---

## Assignment Rules

### PP5

Do not apply `PP5` when a source reports a variant as Pathogenic or Likely Pathogenic but the primary evidence is unavailable or has not been independently evaluated.

Instead:

- record the source and classification as a non-counted lead;
- retrieve the primary data supporting that classification;
- apply the underlying ACMG criteria directly if evidence is sufficient;
- if no primary evidence can be evaluated, report `PP5_NotAssessed - primary evidence required` or `PP5_NotUsed`.

### BP6

Do not apply `BP6` when a source reports a variant as Benign or Likely Benign but the primary evidence is unavailable or has not been independently evaluated.

Instead:

- record the source and classification as a non-counted lead;
- retrieve the primary data supporting that classification;
- apply the underlying benign criteria directly if evidence is sufficient;
- if no primary evidence can be evaluated, report `BP6_NotAssessed - primary evidence required` or `BP6_NotUsed`.

### ClinVar and Expert Sources

ClinVar, ClinGen expert panels, VCEP classifications, and other reputable sources are valuable for evidence discovery and conflict review. They should not be counted through PP5/BP6 by default.

Use curated classifications to:

- identify relevant disease context and transcript;
- identify submitter-provided criteria and citations;
- detect conflicting interpretations;
- decide whether disease-specific VCEP rules exist;
- prioritize primary evidence extraction.

If a ClinGen/VCEP classification supplies explicit criteria and evidence, evaluate those underlying criteria rather than adding PP5/BP6.

---

## Double-Counting Guardrails

Do not count the same information twice:

- Do not apply PP5 on top of PS3, PS4, PM3, PP1, PVS1, PS1/PM5, or PP3 when the reputable-source classification is based on those same evidence types.
- Do not apply BP6 on top of BA1, BS1, BS2, BS3, BS4, BP2, BP4, BP5, or BP7 when the reputable-source classification is based on those same evidence types.
- Do not use an aggregate ClinVar label as evidence when the underlying submissions already contributed primary evidence elsewhere.
- Do not use PP5/BP6 to resolve conflicting interpretations. Instead, review the primary evidence and conflict source.

---

## Missing-Information Behavior

If a classification source is cited but primary evidence is unavailable, do not infer the underlying ACMG criteria.

Use this prompt:

```text
PP5/BP6 reputable-source evidence cannot be counted without primary evidence. Please provide the source report, submitter criteria, evidence summary, citations, case details, population data, functional assay, segregation/de novo data, or other primary evidence supporting the reported classification.
```

---

## Output Format

```markdown
PP5/BP6 reputable-source refinement:
- Variant: [HGVS / ClinVar Variation ID / CA ID]
- Disease context: [condition and inheritance]
- Source assertion: [source, classification, review status, date]
- Primary evidence available: [yes / partial / no]
- Conflict status: [none / conflicting classifications / not assessed]
- Routed underlying criteria: [PS3/BS3, PS4, PM3, PP1/BS4, PVS1, PM2/BA1/BS1, etc.]
- Applied PP5/BP6 evidence: [No PP5 / No BP6 / PP5_NotUsed / BP6_NotUsed / Not Assessed - primary evidence required]
- Rationale: [brief explanation]
```

Evidence table row:

```markdown
| Criterion | Strength | Evidence | Source |
|-----------|----------|----------|--------|
| PP5/BP6 | Not used | Secondary classification was treated as a lead; primary evidence was required and routed to underlying ACMG criteria. | Biesecker & Harrison 2018; PMID:29543229 |
```

---

## Tool Parameter Reference

| Tool or skill | Use |
| --- | --- |
| `VariantValidator_validate_variant` | Normalize HGVS and transcript consequence. |
| `ClinGenAR_lookup_allele` | Resolve canonical allele and external IDs. |
| `ClinVar_search_variants`, `ClinVar_get_variant` | Retrieve classifications, review status, submitter criteria, citations, and conflicts. |
| `ClinGen_get_variant_classifications`, ClinGen ERepo tools | Retrieve expert-panel or VCEP assertions when available. |
| `PubMed_search_articles`, `EuropePMC_search_articles` | Retrieve cited primary literature. |
| `tooluniverse-literature-deep-research` | Extract primary evidence from articles, tables, and supplements. |
| `tooluniverse-literature-figure-evidence-extraction` | Extract evidence from pedigrees, assay figures, gels, plots, and other visual data. |
| Evidence-specific ACMG overlay skills | Assign the underlying evidence criteria after primary evidence retrieval. |

---

## Primary Reference

- Biesecker LG, Harrison SM; ClinGen Sequence Variant Interpretation Working Group. The ACMG/AMP reputable source criteria for the interpretation of sequence variants. Genetics in Medicine. 2018;20(12):1687-1688. PMID:29543229. PMCID:PMC6709533. DOI:10.1038/gim.2018.42.
