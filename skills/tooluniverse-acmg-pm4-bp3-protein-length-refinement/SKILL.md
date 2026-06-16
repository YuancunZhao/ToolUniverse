---
name: tooluniverse-acmg-pm4-bp3-protein-length-refinement
description: Refine ACMG/AMP PM4 and BP3 evidence for protein length changes, in-frame insertions/deletions, stop-loss variants, last-exon gain-of-function truncating variants, and in-frame changes in repetitive regions using ACGS 2024 practice guidance.
disable-model-invocation: true
---

# ACMG PM4/BP3 Protein-Length Refinement

This skill extends `tooluniverse-acmg-variant-classification` for protein length changes and in-frame indels:

- `PM4`: protein length changes as a result of in-frame deletions/insertions in a non-repeat region or stop-loss variants.
- `BP3`: in-frame deletions/insertions in a repetitive region without known function.

It uses ACGS 2024 practice guidance to avoid mechanical PM4/BP3 assignment and to route truncating, stop-loss, and gain-of-function cases away from inappropriate PVS1/PM4 double counting.

Use `tooluniverse-acmg-overlay-routing-core` for shared disease-context, mechanism, clinical-context, source-review, double-counting, and output-status conventions before applying this PM4/BP3-specific logic.

---

## When to Use This Skill

Use this skill when:

- The variant is an in-frame deletion, insertion, duplication, or delins.
- A single amino-acid insertion/deletion may otherwise be over-weighted.
- The variant affects a repeat, low-complexity region, linker, domain, motif, or known functional region.
- A stop-loss variant extends the protein or may trigger nonstop-mediated decay.
- A last-exon truncating or frameshift variant may cause gain-of-function rather than LoF.
- PM4 and PVS1, or PM4 and BP3, could conflict.

Do not use this skill for canonical LoF assignment; use PVS1 and `tooluniverse-acmg-pvs1-splicing-refinement` when the predicted consequence is LoF/NMD/NSD.

---

## Evidence Retrieval Workflow

1. **Normalize and annotate consequence**
   - Use `VariantValidator_validate_variant`, `EnsemblVEP_annotate_hgvs`, `MyVariant_query_variants`, and `ClinGenAR_lookup_allele`.
   - Record HGVS cDNA/protein, transcript, affected amino acids, in-frame status, stop-loss status, repeat context, and whether a PTC/extension is created.

2. **Assess region function**
   - Use `UniProt_get_function_by_accession`, `InterPro_get_entries_for_protein`, AlphaFold/structure tools, protein interaction/domain tools, and literature.
   - Record whether the region is a known domain, active site, binding site, repeat with function, disordered linker, or nonfunctional repetitive region.

3. **Assess conservation and population context**
   - Use gnomAD and Ensembl/MyVariant population frequency tools.
   - Use conservation and indel-impact predictors when available, such as VEP, MutPred-Indel, VEST-indel, BayesDel, or other validated gene/VCEP-supported resources.
   - Treat predictor evidence as auxiliary; it should not override clear functional-region or population evidence.

4. **Resolve mechanism**
   - Use `tooluniverse-acmg-dominant-negative-mechanism-refinement` when an altered in-frame product may interfere with wild-type function or a protein complex.
   - Use `tooluniverse-acmg-pvs1-splicing-refinement` when the variant is better interpreted as LoF, NMD escape, rescue transcript, or RNA-splicing evidence.

---

## PM4 Rules

Apply PM4 when:

- The variant causes an in-frame protein length change in a non-repeat region.
- The affected region is conserved, functionally relevant, structurally relevant, or otherwise disease-relevant.
- Population frequency does not argue against pathogenicity.
- The same evidence is not already used as PVS1.

Strength guidance:

| Situation | Default evidence |
| --- | --- |
| Multi-residue in-frame deletion/insertion in conserved non-repeat functional region | `PM4` |
| Single amino-acid in-frame deletion/insertion | `PM4_Supporting` by default |
| Single amino-acid in-frame deletion/insertion with strong gene-specific/VCEP/functional-domain evidence | `PM4` may be considered |
| In-frame change outside conserved or functional region | No PM4 or PM4 not assessable |
| Exon-scale deletion/duplication causing LoF | Route to PVS1, not PM4 |

PM4 may also be appropriate for last-exon truncating variants in genes where disease is caused by gain-of-function or altered protein products, rather than haploinsufficiency. In those cases, document why PVS1 is not the correct mechanism.

---

## Stop-Loss and Last-Exon Routing

For stop-loss variants:

- If no in-frame termination codon is present in the 3' UTR and nonstop-mediated decay is likely, route to PVS1.
- If an in-frame termination codon is present in the 3' UTR and the predicted result is a protein extension, consider PM4.
- If the extension affects a known functional domain or creates a disease-relevant altered product, document the mechanism and supporting evidence.

For last-exon truncating/frameshift variants:

- If LoF/haploinsufficiency is the mechanism and the variant escapes NMD, use the PVS1 decision-tree downgrade logic rather than PM4.
- If the disease mechanism is gain-of-function, dominant-negative, or altered-product effect, consider PM4 after mechanism review.

---

## BP3 Rules

Apply BP3 when:

- The variant is an in-frame deletion/insertion in a repetitive or low-complexity region.
- The region has no known function.
- The region is not a disease-relevant repeat, interaction interface, motif, active site, or structural element.
- Population frequency and clinical context do not support pathogenicity.

Do not apply BP3 when:

- The repeat or low-complexity region is disease-relevant.
- The in-frame product may have dominant-negative, gain-of-function, or altered complex effect.
- The variant overlaps a known critical residue, domain, or motif.
- The evidence supports PM4 or another pathogenic code.

---

## Double Counting

- Do not use PM4 if PVS1 is applied for the same variant consequence.
- Do not use BP3 and PM4 simultaneously.
- Do not reuse the same functional-domain evidence as both PM4 and PM1 unless the criteria are supported by distinct evidence.
- Do not reuse the same in silico indel score as both PM4 and PP3 unless a VCEP explicitly permits it.
- If an in-frame indel overlaps a residue with known pathogenic missense variation, evaluate PS1/PM5-style evidence separately using `tooluniverse-acmg-ps1-pm5-amino-acid-equivalence-refinement`.

---

## Missing-Information Behavior

If region function, repeat status, conservation, or mechanism is unclear, report `PM4/BP3 not assessable` and ask for targeted data.

```text
PM4/BP3 requires protein-region context. Please provide the transcript/protein change, whether the affected segment is repetitive, known domain or motif annotations, conservation or indel predictor evidence, population frequency, and any disease-specific mechanism or VCEP rule.
```

---

## Output Format

```markdown
PM4/BP3 protein-length refinement:
- Variant: [HGVS c.], [HGVS p.], transcript [ID]
- Consequence: [in-frame deletion/insertion/delins/stop-loss/last-exon truncating]
- Affected residues: [range], size: [aa count]
- Region context: [functional domain / repeat no known function / conserved / unclear]
- Mechanism review: [LoF / GOF / dominant-negative / altered product / unclear]
- PVS1 conflict: [none / route to PVS1 / PM4 retained because altered product mechanism]
- Population/conservation evidence: [summary]
- Applied evidence: [PM4 / PM4_Supporting / BP3 / No PM4/BP3 / not assessable]
- Status: [applied / no_evidence / not_assessed / not_applicable]
- Consumed evidence: [protein length/domain/repeat evidence / none]
```

---

## Primary References

- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants. Genet Med. 2015;17(5):405-424. PMID: 25741868.
- ACGS Best Practice Guidelines for Variant Classification in Rare Disease 2024, v1.2, PM4 and BP3 sections.
- Current ClinGen VCEP specifications for gene-specific in-frame indel and protein-length rules.
