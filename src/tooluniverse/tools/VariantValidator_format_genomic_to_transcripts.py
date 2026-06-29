"""
VariantValidator_format_genomic_to_transcripts

Project a genomic variant onto every overlapping RefSeq transcript using
VariantValidator VariantFormatter.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VariantValidator_format_genomic_to_transcripts(
    variant_description: str,
    genome_build: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Project a genomic variant onto RefSeq transcripts using VariantFormatter.

    Parameters
    ----------
    variant_description : str
        Genomic HGVS or pseudo-VCF variant description.
    genome_build : str
        Reference genome assembly: 'GRCh37' or 'GRCh38'. Defaults to GRCh38.
    stream_callback : Callable, optional
        Callback for streaming output.
    use_cache : bool, default False
        Enable caching.
    validate : bool, default True
        Validate parameters.
    """
    _args = {
        k: v
        for k, v in {
            "genome_build": genome_build,
            "variant_description": variant_description,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VariantValidator_format_genomic_to_transcripts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VariantValidator_format_genomic_to_transcripts"]
