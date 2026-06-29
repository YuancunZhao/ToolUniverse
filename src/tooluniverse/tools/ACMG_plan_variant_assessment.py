"""ACMG_plan_variant_assessment"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ._shared_client import get_shared_client


def ACMG_plan_variant_assessment(
    variant: Optional[str] = None,
    gene: Optional[str] = None,
    transcript: Optional[str] = None,
    consequence: Optional[str] = None,
    variant_type: Optional[str] = None,
    disease_context: Optional[Any] = None,
    phenotype_context: Optional[Any] = None,
    family_context: Optional[Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    args = {
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
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {"name": "ACMG_plan_variant_assessment", "arguments": args},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ACMG_plan_variant_assessment"]
