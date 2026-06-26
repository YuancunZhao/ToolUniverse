"""
ACMG_overlay_gate_assess_variant

Front-door ACMG overlay compliance gate for germline variant pathogenicity assessment.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACMG_overlay_gate_assess_variant(
    variant: str,
    gene: Optional[str] = None,
    transcript: Optional[str] = None,
    consequence: Optional[str] = None,
    variant_type: Optional[str] = None,
    disease_context: Optional[Any] = None,
    phenotype_context: Optional[Any] = None,
    family_context: Optional[Any] = None,
    source_outputs_or_leads: Optional[list[Any]] = None,
    acmg_assessment_bundle: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """Run the ACMG overlay gate preflight/validator front door."""
    _args = {
        k: v
        for k, v in {
            "variant": variant,
            "gene": gene,
            "transcript": transcript,
            "consequence": consequence,
            "variant_type": variant_type,
            "disease_context": disease_context,
            "phenotype_context": phenotype_context,
            "family_context": family_context,
            "source_outputs_or_leads": source_outputs_or_leads,
            "acmg_assessment_bundle": acmg_assessment_bundle,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {"name": "ACMG_overlay_gate_assess_variant", "arguments": _args},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ACMG_overlay_gate_assess_variant"]
