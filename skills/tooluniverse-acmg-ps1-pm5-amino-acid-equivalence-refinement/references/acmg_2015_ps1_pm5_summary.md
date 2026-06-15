# ACMG/AMP 2015 PS1 and PM5 Summary

Primary source:

- Richards S, Aziz N, Bale S, et al. Standards and guidelines for the interpretation of sequence variants: a joint consensus recommendation of ACMG and AMP. Genet Med. 2015;17(5):405-424. PMID: 25741868. DOI: 10.1038/gim.2015.30.

## Scope

This reference summarizes generic PS1 and PM5 use for protein-level missense evidence. It does not replace disease-specific ClinGen VCEP specifications.

## PS1

Generic ACMG/AMP concept:

- Use PS1 when the variant under assessment causes the same amino-acid change as a previously established pathogenic variant, but through a different nucleotide change.

Operational refinement:

- The comparison variant must be independently established as pathogenic or accepted under a current VCEP rule.
- The two variants must encode the same protein substitution on the same clinically relevant transcript.
- The comparison variant's pathogenic mechanism must be the amino-acid change, not a distinct splicing or DNA-level effect.
- The variant under assessment cannot be used as evidence to establish the comparison variant and then receive PS1 from that comparison.

## PM5

Generic ACMG/AMP concept:

- Use PM5 when a novel missense change occurs at an amino-acid residue where a different pathogenic missense change has been observed.

Operational refinement:

- The comparison variant should be an independently established pathogenic missense variant.
- The same residue must be verified on the same clinically relevant transcript/protein.
- The comparison variant's pathogenic mechanism must be relevant to the variant under assessment.
- PM5 is not justified by same codon alone if residue-level amino-acid-mediated pathogenicity is not established.
- PM5 should not be assigned from a comparison variant that is pathogenic because of splicing, LoF, regulatory disruption, or another mechanism not shared by the variant under assessment.

## Splicing and Mechanism Caveat

Protein-level PS1/PM5 should be withheld when the comparison variant's pathogenicity is driven by:

- exon skipping,
- cryptic splice activation,
- intron retention,
- nonsense-mediated decay,
- regulatory sequence disruption,
- DNA-level effects independent of the encoded amino acid,
- or another non-shared molecular mechanism.

When the evidence is same predicted or observed splice event, use the splicing-specific PS1/PVS1 overlays instead.

## VCEP Priority

ClinGen VCEP specifications may modify:

- allowed comparison classification level,
- evidence strength,
- residue/domain requirements,
- known excluded variants,
- or interactions with PS3, PM1, PP3, PS4, and other criteria.

Use current VCEP guidance when available.

## ACGS 2024 Practice Additions

ACGS 2024 is used here as practice guidance for unresolved generic PS1/PM5 edge cases, not as a separate selectable profile.

PS1 additions:

- Full `PS1` is appropriate when the comparison variant is independently Pathogenic.
- `PS1_Moderate` can be considered when the comparison variant is independently Likely Pathogenic rather than Pathogenic.
- Initiation codon PS1-style use requires the same predicted effect on translation initiation and independent comparison evidence.
- Non-coding RNA genes require a disease-specific or VCEP-supported analogous rule; do not automatically transfer protein missense logic.

PM5 additions:

- Full `PM5` is appropriate when the same-residue comparison missense variant is independently Pathogenic.
- `PM5_Supporting` can be considered when the comparison is Likely Pathogenic or supported by limited case evidence.
- Compare the variant under assessment with the comparison variant using REVEL, Grantham distance, BLOSUM62, conservation, and protein/domain context when available.
- PM5 is stronger when the variant under assessment is predicted to be similarly or more disruptive than the comparison variant.
- In-frame deletion or duplication overlapping a residue with a P/LP missense variant can be considered only under gene-specific same-mechanism reasoning; avoid double counting with PM4.

Shared safeguards:

- PS1/PM5 cannot be used for the variant's own pathogenicity assertion.
- Confirm that the comparison variant acts through the amino-acid or local protein effect, not through splicing.
- Do not reuse the same clustering or residue evidence as both PM1 and PM5 unless a VCEP explicitly permits it.
