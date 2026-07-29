# Clinical Variant Interpreter Checklist

Pre-delivery verification checklist for variant interpretation reports.

## Report Quality Checklist

### Structure & Format
- [ ] Report file created: `{GENE}_{VARIANT}_interpretation_report.md`
- [ ] All 9 main sections present
- [ ] Executive summary completed (not `[Interpreting...]`)
- [ ] Data sources section populated

### Confidentiality, Transparency, and Human Review
- [ ] Patient-level data are de-identified; no names, dates of birth, medical record numbers, direct contact details, or other identifiers included
- [ ] Public evidence is separated from unpublished drafts, meeting notes, internal deliberations, or restricted case-level evidence
- [ ] AI-assisted drafting/evidence-retrieval statement included when the output is used for notes, curation drafts, or clinical interpretation drafts
- [ ] Final report states that clinical or ClinGen/VCEP use requires qualified human review
- [ ] No automatic publication, distribution, or final classification without human review

### Phase 1: Variant Identity
- [ ] Gene symbol identified
- [ ] HGVS c. notation provided
- [ ] HGVS p. notation (if applicable)
- [ ] Transcript ID (MANE Select preferred)
- [ ] Consequence type identified
- [ ] Exon/intron location stated
- [ ] Amino acid change (for missense)

### Phase 2: Population Data
- [ ] gnomAD queried
- [ ] Overall allele frequency reported
- [ ] ≥3 ancestry-specific frequencies
- [ ] Homozygote count reported
- [ ] Hemizygote count (X-linked genes)
- [ ] Frequency interpreted vs. disease prevalence

### Phase 3: Clinical Database Evidence
- [ ] ClinVar searched
- [ ] ClinVar submitted classification reported as a source assertion (or "Not in ClinVar")
- [ ] Review status noted (gold stars)
- [ ] Number of submissions documented
- [ ] Conflicting interpretations noted (if any)
- [ ] OMIM gene-disease associations checked
- [ ] ClinGen gene validity (if available)

### Phase 4: Computational Predictions
- [ ] Relevant predictor scores reported when available
- [ ] Selected predictor source and coverage documented
- [ ] Discordance recorded without local vote-based evidence assignment
- [ ] PP3/BP4 evidence routed to `ACMG_computational_evidence` or current VCEP
- [ ] SpliceAI scores and positions retained; overlap with RNA/PVS1 handled by compatibility review
- [ ] Walker candidate use is Supporting-only and has verified 1.3.1/MANE/raw/unmasked/distance-500 provenance plus one identity-bound row
- [ ] BP7_Supporting appears only after strict BP4 and eligible synonymous or outside-+7/-21 intronic context
- [ ] Functional assay declares `assay_scope`; direct RNA-splicing readouts are excluded from PS3/BS3

### Phase 5: Structural Analysis (for missense)
- [ ] Protein structure source identified (PDB/AlphaFold)
- [ ] pLDDT at variant position (if AlphaFold)
- [ ] Residue location (buried/surface)
- [ ] Secondary structure context
- [ ] Domain/functional site proximity
- [ ] UniProt accession and residue mapping verified against genomic HGVS
- [ ] Exact EBI feature overlap separated from coordinate-free InterPro inventory
- [ ] Generic domain overlap kept `indeterminate`; PM1 candidate requires an exact reviewed CSpec region contract

### Phase 6: Literature Evidence
- [ ] PubMed searched with ≥2 strategies
- [ ] Functional studies documented (or "None found")
- [ ] Case reports documented
- [ ] PS3 consideration documented
- [ ] PP1 (segregation) documented if available

### Phase 7: ACMG Evidence Review
- [ ] All criteria have a review row, including missing requirements
- [ ] Observed facts are separated from suggested criterion and strength
- [ ] Each suggestion includes rule ID, version, basis, and SourceFact IDs
- [ ] CSpec candidates, applicability decision, and general-SVI fallback are shown
- [ ] Five-tier classification is explicitly withheld by the evidence-only runtime
- [ ] Compatibility exclusions, conflicts, and system-preview Bayesian estimate are reported

### Phase 8: Human Review Boundary
- [ ] Candidate evidence is not described as clinically approved evidence
- [ ] No management recommendation is inferred from a withheld classification
- [ ] Unresolved conflicts and missing data are assigned to human review

### Phase 9: Limitations
- [ ] Missing data acknowledged
- [ ] Conflicting evidence noted
- [ ] Uncertainty quantified

---

## Citation Requirements

### Every Evidence Statement Must Include
- [ ] Source database/tool in backticks
- [ ] Specific identifier (ClinVar ID, PMID)
- [ ] Date of access (for changing databases)

### Format Examples
```markdown
*Source: ClinVar VCV000012345, reviewed 4-star, accessed 2026-02-04*
*Source: gnomAD v4.0, overall AF=0.00001, accessed 2026-02-04*
*Source: PMID 12345678 - functional study showed loss of activity*
*Source: AlphaFold DB via `alphafold_get_prediction`, pLDDT=92 at position*
```

---

## ACMG Code Verification

### For Each Suggested Code
- [ ] Code abbreviation correct (PVS1, PM2, PP3, etc.)
- [ ] Strength appropriate (VeryStrong/Strong/Moderate/Supporting)
- [ ] Evidence clearly supports application
- [ ] Not double-counted

### Common Errors to Avoid
- [ ] PM2 without the versioned population rule reviewing frequency and callability facts
- [ ] PP3/BP4 from uncalibrated predictor voting rather than the versioned rule or applicable CSpec
- [ ] PVS1 presented as assessed before the complete LoF decision-tree facts exist
- [ ] PS3/BS3 without functional-assay refinement
- [ ] PS3/BS3 from segregation, case recurrence, HGMD/ClinVar labels, or another author's ACMG code rather than actual functional assay data
- [ ] PM1, PM5, PS3, or PP3 assigned directly from a reputable-source label without primary evidence extraction
- [ ] PM1 assigned from generic domain overlap without critical-region, benign-depletion, disease/inheritance, transcript, and contract-version checks
- [ ] Applying the same evidence to multiple codes

---

## Evidence Routing Verification

### Verify Routing
| Step | Requirement |
|------|-------------|
| Context routing | `ACMG_evidence_collector` used for evidence-only intake; unsupported context remains review-only |
| Evidence assignment | Shared deterministic group rules used for candidate suggestions |
| Final classification | Not produced in the current evidence-only runtime |

### External-Agent Evidence Audit
- [ ] Every Bayesian-included candidate has `assessment_status=met`, `overlay_validated=true`, and trusted SourceFact IDs
- [ ] Source assertions from ClinVar, HGMD, LOVD, expert panels, lab reports, or published ACMG classifications remain source leads and are not converted to criteria
- [ ] Failed tool calls are retried or marked as missing; manual summaries are not used to replace required verified evidence
- [ ] Literature-derived facts are routed to the correct group rule: functional assay -> PS3/BS3, segregation -> PP1/BS4, case enrichment -> PS4, biallelic recessive proband -> PM3, de novo -> PS2/PM6

### Candidate Review Cross-Check
- [ ] Candidate criteria align with their deterministic rule outputs
- [ ] No conflicting codes ignored
- [ ] Applicable CSpec or explicit general-SVI fallback is recorded

---

## Quantified Minimums

| Section | Minimum Requirement |
|---------|---------------------|
| Population frequencies | gnomAD + ≥3 ancestry groups |
| Computational predictors | Relevant predictor outputs and PP3/BP4 overlay route |
| Literature searches | ≥2 search strategies |
| ACMG codes | All applicable documented |
| Candidate evidence | All available facts, suggestions, exclusions, and gaps shown |

---

## Structural Analysis Quality (for Missense)

### Must Include
- [ ] Structure source (PDB ID or "AlphaFold predicted")
- [ ] pLDDT at position (if AlphaFold)
- [ ] Residue depth/accessibility
- [ ] Structural consequence prediction

### Quality Thresholds
| Metric | Confident | Uncertain |
|--------|-----------|-----------|
| pLDDT | >70 | <70 |
| PDB Resolution | <3.0 Å | >3.0 Å |

---

## Special Scenario Checks

### Truncating Variants
- [ ] NMD prediction assessed
- [ ] LOF mechanism confirmed for gene
- [ ] PVS1 remains a documented route with all missing decision-tree facts
- [ ] Last exon exception considered

### Splice Variants
- [ ] Canonical splice site distance
- [ ] SpliceAI scores (if available)
- [ ] In-frame skip assessment
- [ ] PVS1/SpliceAI/RNA overlap recorded for compatibility review

### X-linked Genes
- [ ] Sex of individual considered
- [ ] Hemizygote frequency used appropriately
- [ ] Penetrance in females addressed

---

## Output Files

### Required
- [ ] `{GENE}_{VARIANT}_interpretation_report.md` - Main report

### Optional Data Export
- [ ] `{GENE}_{VARIANT}_evidence_table.csv` - Structured evidence
- [ ] `{GENE}_{VARIANT}_evidence_cards.csv` - Candidate and excluded EvidenceCards

---

## Final Review

### Before Delivery
- [ ] No `[Interpreting...]` placeholders remaining
- [ ] All tables properly formatted
- [ ] Executive summary synthesizes findings
- [ ] Evidence-only boundary stated prominently
- [ ] No patient-management recommendation inferred from the review estimate
- [ ] Limitations clearly stated

### Common Issues to Avoid
- [ ] Missing gnomAD frequencies
- [ ] Source classification presented as if it were a derived EvidenceCard
- [ ] Management recommendations inferred from a withheld classification
- [ ] Missing literature search
- [ ] Structure analysis skipped for VUS missense
- [ ] ACMG codes without justification

---

## ClinVar-Specific Checks

### When Variant in ClinVar
- [ ] VCV ID documented
- [ ] Review status (stars) noted
- [ ] Number of submitters
- [ ] Date of last evaluation
- [ ] Concordance with our assessment

### When Variant NOT in ClinVar
- [ ] Explicitly state "Not in ClinVar as of {date}"
- [ ] Consider novel variant workflow
- [ ] Emphasize structural analysis

---

## Tool Verification Checklist

### Before Report Generation
- [ ] `ClinVar_search_variants` returns results or "not found"
- [ ] `gnomad_search_variants` frequency values valid
- [ ] `MyVariant_query_variants` predictions populated
- [ ] Structure available (PDB or AlphaFold)

### NVIDIA NIM Availability
- [ ] Check if structural analysis needed
- [ ] Confirm NVIDIA_API_KEY if using NvidiaNIM_alphafold2
- [ ] Document if fallback used

---

## Report Completeness Score

Calculate before delivery:

| Section | Points |
|---------|--------|
| Variant identity complete | 10 |
| gnomAD with ancestry | 10 |
| ClinVar documented | 10 |
| Predictor context and overlay route | 10 |
| Structural analysis | 15 |
| Literature search | 10 |
| Candidate evidence with rule rationale | 20 |
| Compatibility and conflicts | 10 |
| Limitations stated | 5 |

**Minimum passing score**: 85/100
