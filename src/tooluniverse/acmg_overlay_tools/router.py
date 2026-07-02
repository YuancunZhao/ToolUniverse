"""Router: determines which ACMG overlays apply to a given variant.

MCP tool: acmg_route_overlays

LLM calls this FIRST to get the list of applicable overlay tools,
then collects evidence for each one, then calls each overlay tool.
"""

from __future__ import annotations

import re
from typing import Any


def _infer_variant_type(hgvs_c: str) -> str:
    """Infer variant type from HGVS coding notation.

    Returns one of: missense, null (nonsense/frameshift), splice, synonymous,
    intronic, indel_inframe, unknown.
    """
    if not hgvs_c:
        return "unknown"

    notation = hgvs_c.strip()

    # p. notation → look for common missense/null patterns
    if notation.startswith("p."):
        if any(kw in notation.lower() for kw in ("ter", "*", "fs", "frameshift", "x")):
            return "null"
        if re.search(r"[A-Z][a-z]{2}\d+[A-Z][a-z]{2}", notation):
            return "missense"
        return "unknown"

    # c. notation
    # c. notation - deletions (frameshift unless multiple of 3)
    if "del" in notation and "ins" not in notation and "delins" not in notation:
        # Single base deletion like c.1620delC or multi-base like c.68_69delAG
        letters = re.findall(r"del([ACGT]+)", notation)
        if letters:
            size = len(letters[0])
        else:
            size_match = re.search(r"del(\d+)", notation)
            size = int(size_match.group(1)) if size_match else 1  # default 1 = frameshift
        if size % 3 != 0:
            return "null"
        return "indel_inframe"
    if "ins" in notation:
        size_match = re.search(r"ins[ACGT]+", notation)
        lentext = notation.split("ins")[-1]
        letters = re.findall(r"[ACGT]+", lentext)
        if letters and len(letters[0]) % 3 != 0:
            return "null"
        return "indel_inframe"
    if "dup" in notation:
        return "indel_inframe"
    if "delins" in notation:
        return "indel_inframe"

    # Substitution: c.742C>T
    sub_match = re.search(r"c\.(\d+)([ACGT])>([ACGT])", notation)
    if sub_match:
        pos = int(sub_match.group(1))
        if pos < 0:
            return "unknown"
        # Check if near splice site (±2)
        if "±" in notation or any(k in notation for k in ("+", "-")):
            if "splice" in notation.lower():
                return "splice"
        return "missense"  # default for coding substitution

    if ">" in notation or "→" in notation:
        return "missense"

    if any(kw in notation.lower() for kw in ("nonsense", "frameshift", "stop", "ter")):
        return "null"

    if any(kw in notation.lower() for kw in ("splice", "ivs", "intron", "intronic")):
        return "splice"

    if any(kw in notation.lower() for kw in ("synonymous", "silent")):
        return "synonymous"

    return "unknown"


def route_overlays(
    variant: str = "",
    gene: str = "",
    hgvs_c: str = "",
    variant_type: str = "",
) -> dict[str, Any]:
    """Determine which ACMG overlay tools apply to a variant.

    Args:
        variant: HGVS notation or variant description (e.g. "NM_000142.4:c.742C>T")
        gene: Gene symbol (e.g. "FGFR3")
        hgvs_c: Explicit HGVS coding notation, if variant is not HGVS
        variant_type: Pre-determined variant type, overrides inference

    Returns:
        Dict with baseline_overlays, literature_overlays, evidence_sources,
        variant_type, and recommended workflow steps.
    """
    from .base import literature_dependent_overlays, variant_type_overlays

    # Determine variant type
    input_hgvs = hgvs_c or variant or ""
    inferred_type = variant_type or _infer_variant_type(input_hgvs)

    # Get applicable overlays from registry
    baseline = variant_type_overlays(inferred_type)
    literature = literature_dependent_overlays()

    # Always include these baseline overlays
    always_baseline = {"pm2_absence_rarity", "ba1_exception_list", "benign_context"}
    for g in always_baseline:
        if g not in baseline:
            baseline.append(g)

    # Remove duplicates while preserving order
    baseline = list(dict.fromkeys(baseline))
    literature = [g for g in literature if g not in baseline]

    # Evidence sources per category
    evidence_sources: dict[str, list[str]] = {
        "population": ["gnomAD", "Ensembl variation", "1000 Genomes"],
        "computational": ["REVEL", "CADD", "SpliceAI", "SIFT", "PolyPhen-2"],
        "source_assertion": ["ClinVar", "ClinVarSubmitted", "HGMD", "LOVD"],
        "functional_database": ["MaveDB", "ClinGen", "G2P"],
        "literature": ["PubMed", "EuropePMC"],
    }

    # Filter sources based on variant type
    if inferred_type == "missense":
        evidence_sources["computational"] = ["REVEL", "CADD", "SpliceAI", "SIFT", "PolyPhen-2"]
    elif inferred_type in ("splice", "intronic"):
        evidence_sources["computational"] = ["SpliceAI", "MaxEntScan", "dbscSNV"]
    elif inferred_type in ("synonymous",):
        evidence_sources["computational"] = ["SpliceAI", "dbscSNV"]

    workflow_steps = [
        f"1. Collect population frequency data: {', '.join(evidence_sources['population'])}",
        f"2. Collect computational predictions: {', '.join(evidence_sources['computational'])}",
        f"3. Collect source assertions: {', '.join(evidence_sources['source_assertion'])}",
        "4. Search PubMed for functional assay, case enrichment, segregation, de novo evidence",
        "5. Call each baseline overlay tool with collected evidence",
        "6. Call each literature overlay tool with extracted literature evidence",
        "7. Call acmg_combine_criteria with all overlay results",
    ]

    return {
        "variant": input_hgvs,
        "gene": gene,
        "variant_type": inferred_type,
        "baseline_overlays": baseline,
        "literature_overlays": literature,
        "total_overlays": len(baseline) + len(literature),
        "evidence_sources": evidence_sources,
        "workflow_steps": workflow_steps,
    }


__all__ = ["route_overlays"]
