# Quick Start: Literature Figure Evidence Extraction

Use this overlay when a paper figure or supplement contains visual evidence needed by an ACMG rule-refinement skill. This skill extracts structured evidence only; it does not assign ACMG codes.

---

## Example 1: PM3 Pedigree with Confirmed In Trans

**Scenario**: A pedigree shows an affected proband with variant A inherited from the mother and variant B inherited from the father.

**Expected behavior**:

- Figure type: `pedigree`.
- Extract parent genotypes and proband affected status.
- Structured interpretation: `confirmed in trans`.
- Relevant overlay: `tooluniverse-acmg-pm3-in-trans-refinement`.
- Do not assign PM3 in this skill.

---

## Example 2: PM3 One-Parent-Supported Phase

**Scenario**: Only the mother is tested and carries one of the two variants. The affected proband carries both variants.

**Expected behavior**:

- Extract `presumed in trans / one-parent-supported` phase.
- Record that the father is untested or unavailable.
- Mark confidence based on clarity of the figure and caption.
- Pass the structured result to PM3 scoring.

---

## Example 3: Phase Unknown

**Scenario**: A figure or table lists allele 1 and allele 2 in an affected proband, but no parental genotype, reads-backed phase, or explicit in-trans wording is shown.

**Expected behavior**:

- Extract `phase unknown`.
- Do not infer compound heterozygosity from allele labels alone.
- Pass to PM3 overlay as phase-unknown evidence only if other PM3 requirements are met.

---

## Example 4: PP1 Segregation Figure

**Scenario**: A pedigree shows affected carriers and unaffected non-carriers across multiple relatives.

**Expected behavior**:

- Figure type: `segregation_family`.
- Extract affected carriers, unaffected carriers, affected non-carriers, unaffected non-carriers, and informative meioses if readable.
- Relevant overlay: `tooluniverse-acmg-pp1-segregation-refinement`.
- Do not assign PP1 or BS4 in this skill.

---

## Example 5: Functional Assay Plot

**Scenario**: A bar plot shows reduced enzyme activity for the variant compared with wild type and includes positive and negative controls.

**Expected behavior**:

- Figure type: `functional_assay`.
- Extract assay class, model system, controls, readout, units, direction of effect, variant result, and visible statistics.
- Use `tooluniverse-image-analysis` if numeric plot extraction or image-derived statistics are required.
- Pass structured facts to `tooluniverse-acmg-ps3-bs3-functional-assay-refinement`.

---

## Example 6: Western Blot or Gel with Unclear Labels

**Scenario**: A gel image contains bands but lane labels are cropped or unreadable.

**Expected behavior**:

- Figure type: `gel_or_western_blot`.
- Record visible bands but mark label interpretation as ambiguous.
- Confidence: low or not_interpretable.
- Do not let the downstream ACMG overlay activate evidence without independent support.

---

## Example 7: RT-PCR or Minigene Figure

**Scenario**: RT-PCR gel and transcript schematic show exon skipping in the variant sample.

**Expected behavior**:

- Figure type: `rna_splicing_assay`.
- Extract assay type, sample labels, normal transcript, aberrant product, exon skipping/intron retention/pseudoexon event, and any abundance or sequence-confirmation note.
- Relevant overlay: `tooluniverse-acmg-pvs1-splicing-refinement`.
- Do not assign `PVS1_Strength (RNA)` here.

---

## Example 8: Sanger Trace for Parental Carrier Status

**Scenario**: Sanger traces show a proband and parent genotypes for a variant.

**Expected behavior**:

- Figure type: `sanger_trace`.
- Extract sample identity, genotype call visible in trace, and whether the trace supports parental origin.
- Relevant overlays: PM3, PP1, PS2/PM6, or BS4 depending on case context.
- Report confidence and any unreadable peak or sample-label issue.

---

## Minimal Report Block

```markdown
Figure evidence extraction:
- Source: [PMID/DOI/file], [figure/supplement/page/panel]
- Figure type: [type]
- Variant(s): [notation]
- Gene/disease context: [context]
- Visual observations: [facts visible in figure]
- Text/caption context: [caption/body/OCR context]
- Structured interpretation: [schema-specific result]
- Relevant ACMG overlays: [overlay names]
- Confidence: [high/medium/low/not_interpretable]
- Ambiguities: [issues]
- ACMG assignment: Not assigned by this figure-extraction skill.
```
