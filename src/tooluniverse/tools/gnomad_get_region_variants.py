"""
gnomad_get_region_variants

Get per-variant consequence and frequency facts for a small genomic interval from gnomAD. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_region_variants(
    chrom: str,
    start: int,
    stop: int,
    reference_genome: Optional[str] = 'GRCh38',
    dataset: Optional[str] = 'gnomad_r4',
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get per-variant consequence and frequency facts for a small genomic interval from gnomAD. Returns...

    Parameters
    ----------
    chrom : str
        Chromosome (e.g., '19').
    start : int
        1-based start position.
    stop : int
        1-based stop position.
    reference_genome : str
        Reference genome.
    dataset : str
        gnomAD dataset ID used for `variants(dataset: ...)`. Allowed values: gnomad_r...
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
                "start": start,
                "stop": stop,
                "reference_genome": reference_genome,
                "dataset": dataset
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "gnomad_get_region_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["gnomad_get_region_variants"]
