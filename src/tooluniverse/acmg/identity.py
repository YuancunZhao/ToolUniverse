"""Small, upstream-tool-oriented helpers for variant identity resolution."""

from __future__ import annotations

import re
from typing import Any


CODING_HGVS_RE = re.compile(r"^c\.[^\s]+$", re.IGNORECASE)
GENE_CODING_RE = re.compile(
    r"^(?P<gene>[A-Za-z][A-Za-z0-9-]*)\s*[: ]\s*(?P<hgvs>c\.[^\s]+)$",
    re.IGNORECASE,
)
GENE_PROTEIN_RE = re.compile(
    r"^(?P<gene>[A-Za-z][A-Za-z0-9-]*)\s*[:; ]\s*(?P<hgvs>p\.[^\s]+)$",
    re.IGNORECASE,
)
GENE_TRANSCRIPT_RE = re.compile(
    r"^(?P<gene>[A-Za-z][A-Za-z0-9-]*)\s*;\s*"
    r"(?P<hgvs>(?P<transcript>[A-Za-z][A-Za-z0-9_]*\.\d+):c\.[^\s]+)$",
    re.IGNORECASE,
)
RSID_RE = re.compile(r"^rs\d+$", re.IGNORECASE)
GENOMIC_HGVS_RE = re.compile(r"^(?:NC_\d+\.\d+|chr[^:\s]+):g\.", re.IGNORECASE)
GENOMIC_VCF_RE = re.compile(
    r"^(?:chr)?[^:\s]+:\d+:[ACGT]+:[ACGT]+$"
    r"|^(?:chr)?[^-\s]+-\d+-[ACGT]+-[ACGT]+$",
    re.IGNORECASE,
)
COMPACT_GENOMIC_RE = re.compile(
    r"^(?:chr)?(?P<chrom>[^:\s]+):(?P<position>\d+)"
    r"(?P<ref>[ACGT]+)>(?P<alt>[ACGT]+)$",
    re.IGNORECASE,
)
_NC_GENOMIC_RE = re.compile(r"^NC_(?P<accession>\d+)\.\d+:g\.(?P<body>.+)$")
_NC_SERIAL_CHROM = {str(number): str(number) for number in range(1, 23)}
_NC_SERIAL_CHROM.update({"23": "X", "24": "Y", "12920": "MT"})


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _payload(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    sandbox = result.get("source_lead_sandbox")
    if isinstance(sandbox, dict):
        features = sandbox.get("reviewable_features")
        if isinstance(features, (dict, list)):
            return features
    features = result.get("reviewable_features")
    if isinstance(features, (dict, list)):
        return features
    for key in ("result", "data"):
        value = result.get(key)
        if isinstance(value, (dict, list)):
            return value
    return result


def myvariant_id_from_hgvs_g(hgvs_g: str) -> str:
    """Convert a verified GRCh37 RefSeq genomic HGVS to a MyVariant key."""
    match = _NC_GENOMIC_RE.match(str(hgvs_g or "").strip())
    if not match:
        return str(hgvs_g or "")
    chrom = _NC_SERIAL_CHROM.get(str(int(match.group("accession"))))
    return f"chr{chrom}:g.{match.group('body')}" if chrom else str(hgvs_g or "")


def split_gene_coding_input(variant: str, gene: str) -> tuple[str, str, bool]:
    value = variant.strip()
    if CODING_HGVS_RE.fullmatch(value):
        return gene.strip(), value, True
    match = GENE_CODING_RE.fullmatch(value)
    if not match:
        return gene.strip(), "", False
    embedded_gene = match.group("gene").strip()
    if gene and _norm(gene) != _norm(embedded_gene):
        return "", "", True
    return gene.strip() or embedded_gene, match.group("hgvs"), True


def split_gene_protein_input(variant: str, gene: str) -> tuple[str, str, bool]:
    match = GENE_PROTEIN_RE.fullmatch(variant.strip())
    if not match:
        return gene.strip(), "", False
    embedded_gene = match.group("gene").strip()
    if gene and _norm(gene) != _norm(embedded_gene):
        return "", "", True
    return gene.strip() or embedded_gene, match.group("hgvs"), True


def split_gene_transcript_input(variant: str, gene: str) -> tuple[str, str, bool]:
    match = GENE_TRANSCRIPT_RE.fullmatch(variant.strip())
    if not match:
        return gene.strip(), "", False
    embedded_gene = match.group("gene").strip()
    if gene and _norm(gene) != _norm(embedded_gene):
        return "", "", True
    return gene.strip() or embedded_gene, match.group("hgvs"), True


def transcript_accession(hgvs: str) -> str:
    return hgvs.split(":", 1)[0] if ":" in hgvs else ""


def transcript_candidates(result: Any, expected_gene: str) -> list[dict[str, Any]]:
    payload = _payload(result)
    if isinstance(payload, dict) and isinstance(payload.get("transcripts"), list):
        records = [payload]
    elif isinstance(payload, list):
        records = [item for item in payload if isinstance(item, dict)]
    else:
        records = []
    candidates: list[dict[str, Any]] = []
    for record in records:
        record_gene = str(
            record.get("current_symbol")
            or record.get("current_name")
            or record.get("requested_symbol")
            or ""
        )
        if record_gene and expected_gene and _norm(record_gene) != _norm(expected_gene):
            continue
        for transcript in record.get("transcripts") or []:
            if not isinstance(transcript, dict):
                continue
            annotations = transcript.get("annotations")
            annotations = annotations if isinstance(annotations, dict) else {}
            reference = str(transcript.get("reference") or "").strip()
            if reference:
                candidates.append(
                    {
                        "reference": reference,
                        "mane_select": annotations.get("mane_select") is True,
                        "mane_plus_clinical": annotations.get("mane_plus_clinical") is True,
                        "gene": record_gene or expected_gene,
                    }
                )
    return candidates


def select_mane_transcript(result: Any, expected_gene: str) -> dict[str, Any] | None:
    candidates = transcript_candidates(result, expected_gene)
    for pool in (
        [item for item in candidates if item["mane_select"]],
        [item for item in candidates if item["mane_plus_clinical"]],
    ):
        if not pool:
            continue
        refseq = [item for item in pool if str(item["reference"]).startswith("NM_")]
        if len(refseq) == 1:
            return refseq[0]
        if len(pool) == 1:
            return pool[0]
        return None
    return None


def formatted_transcript_candidates(result: Any) -> list[dict[str, Any]]:
    pending = [_payload(result)]
    candidates: list[dict[str, Any]] = []
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            projections = value.get("hgvs_t_and_p")
            if isinstance(projections, dict):
                for reference, projection in projections.items():
                    if not isinstance(projection, dict):
                        continue
                    select_status = projection.get("select_status")
                    select_status = select_status if isinstance(select_status, dict) else {}
                    gene_info = projection.get("gene_info")
                    gene_info = gene_info if isinstance(gene_info, dict) else {}
                    candidates.append(
                        {
                            "reference": str(reference),
                            "t_hgvs": str(projection.get("t_hgvs") or ""),
                            "g_hgvs": str(value.get("g_hgvs") or ""),
                            "mane_select": select_status.get("mane_select") is True,
                            "gene": str(gene_info.get("symbol") or ""),
                        }
                    )
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return candidates


def select_formatted_transcript(result: Any) -> dict[str, Any] | None:
    candidates = [
        item for item in formatted_transcript_candidates(result)
        if item["mane_select"] and item["t_hgvs"]
    ]
    refseq = [item for item in candidates if str(item["reference"]).startswith("NM_")]
    if len(refseq) == 1:
        return refseq[0]
    return candidates[0] if len(candidates) == 1 else None


__all__ = [
    "COMPACT_GENOMIC_RE",
    "GENOMIC_HGVS_RE",
    "GENOMIC_VCF_RE",
    "RSID_RE",
    "formatted_transcript_candidates",
    "myvariant_id_from_hgvs_g",
    "select_formatted_transcript",
    "select_mane_transcript",
    "split_gene_coding_input",
    "split_gene_protein_input",
    "split_gene_transcript_input",
    "transcript_accession",
    "transcript_candidates",
]
