"""
ACMG_overlay_gate_assess_variant

Thin backward-compatible alias for ACMG_evidence_collector. Parameters and return structure are i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACMG_overlay_gate_assess_variant(
    variant: str,
    gene: Optional[str] = None,
    transcript: Optional[str] = None,
    disease: Optional[str] = None,
    inheritance: Optional[str] = None,
    genome_build: Optional[str] = None,
    source_outputs_or_leads: Optional[list[Any]] = None,
    literature_proposals: Optional[list[Any]] = None,
    cspec_proposals: Optional[list[Any]] = None,
    evidence_decisions: Optional[list[Any]] = None,
    protein_accession: Optional[str] = None,
    clinical_context: Optional[dict[str, Any]] = None,
    clinical_observations: Optional[list[Any]] = None,
    response_detail: Optional[str] = 'summary',
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Thin backward-compatible alias for ACMG_evidence_collector. Parameters and return structure are i...

    Parameters
    ----------
    variant : str
        Transcript HGVS, gene;transcript:c. HGVS, genomic HGVS/VCF-like variant, rsID...
    gene : str
        Gene symbol, if known.
    transcript : str
        Transcript accession or transcript context, if known.
    disease : str
        Disease name or MONDO identifier used to match an applicable ClinGen CSpec.
    inheritance : str
        Inheritance mode used to match an applicable ClinGen CSpec.
    genome_build : str
        Genome assembly. hg19/hg38 normalize to GRCh37/GRCh38; coordinate inputs with...
    source_outputs_or_leads : list[Any]
        Existing outputs from GeneBe, InterVar, ClinVar, ClinGen, SpliceAI, MyVariant...
    literature_proposals : list[Any]
        Optional supplemental literature facts or reproducibility input. The collecto...
    cspec_proposals : list[Any]
        Optional supplemental interpretations of unresolved natural-language rules fr...
    evidence_decisions : list[Any]
        User decisions applied only to stable card IDs regenerated in this call. Acce...
    protein_accession : str
        
    clinical_context : dict[str, Any]
        Review-only clinical context. Explicit HPO terms trigger term/gene/disease lo...
    clinical_observations : list[Any]
        Structured caller-supplied case, family, phase, phenotype, assay, case-contro...
    response_detail : str
        Output detail level. 'summary' (default) returns compact source-fact/evidence...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "variant": variant,
                "gene": gene,
                "transcript": transcript,
                "disease": disease,
                "inheritance": inheritance,
                "genome_build": genome_build,
                "source_outputs_or_leads": source_outputs_or_leads,
                "literature_proposals": literature_proposals,
                "cspec_proposals": cspec_proposals,
                "evidence_decisions": evidence_decisions,
                "protein_accession": protein_accession,
                "clinical_context": clinical_context,
                "clinical_observations": clinical_observations,
                "response_detail": response_detail
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ACMG_overlay_gate_assess_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ACMG_overlay_gate_assess_variant"]
