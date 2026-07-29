"""
gnomad_get_site_callability

Retrieve gnomAD per-locus exome and genome coverage for a normalized genomic position. This retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_site_callability(
    chrom: str,
    position: int,
    reference_genome: Optional[str] = 'GRCh38',
    dataset: Optional[str] = 'gnomad_r4',
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve gnomAD per-locus exome and genome coverage for a normalized genomic position. This retur...

    Parameters
    ----------
    chrom : str
        Chromosome without or with the chr prefix, e.g. '1'.
    position : int
        One-based genomic position.
    reference_genome : str
        Reference genome for the normalized position.
    dataset : str
        gnomAD dataset. The tool rejects known dataset/build mismatches.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "chrom": chrom,
                "position": position,
                "reference_genome": reference_genome,
                "dataset": dataset
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "gnomad_get_site_callability",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["gnomad_get_site_callability"]
