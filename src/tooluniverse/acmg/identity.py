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
_CODING_WITH_PROTEIN_SUFFIX_RE = re.compile(
    r"^(?P<coding>.+:c\.[^\s()]+|c\.[^\s()]+)"
    r"\((?P<protein>p\.[^\s()]+)\)$",
    re.IGNORECASE,
)
RSID_RE = re.compile(r"^rs\d+$", re.IGNORECASE)
GENOMIC_HGVS_RE = re.compile(r"^(?:NC_\d+\.\d+|chr[^:\s]+):g\.", re.IGNORECASE)
GENOMIC_VCF_RE = re.compile(
    r"^(?:chr)?[^:\s]+:\d+:[ACGT]+:[ACGT]+$"
    r"|^(?:chr)?[^-\s]+-\d+-[ACGT]+-[ACGT]+$",
    re.IGNORECASE,
)
_VCF_COLON_RE = re.compile(
    r"^(?:chr)?[^:\s]+:(?P<position>\d+):(?P<ref>[ACGT]+):(?P<alt>[ACGT]+)$",
    re.IGNORECASE,
)
_VCF_DASH_RE = re.compile(
    r"^(?:chr)?[^-\s]+-(?P<position>\d+)-(?P<ref>[ACGT]+)-(?P<alt>[ACGT]+)$",
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

_BUILD_ALIASES = {
    "grch37": "GRCh37",
    "hg19": "GRCh37",
    "grch38": "GRCh38",
    "hg38": "GRCh38",
}
_BUILD_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])(GRCh37|hg19|GRCh38|hg38)(?![A-Za-z0-9])", re.IGNORECASE
)
_INTERVAL_RE = re.compile(
    r"^(?:chr)?(?P<chrom>[^:\s]+):(?P<start>\d+)-(?P<end>\d+)"
    r"(?:-(?P<kind>DEL|DUP|INV|CNV|CPX))?$",
    re.IGNORECASE,
)
_HGVS_INTERVAL_RE = re.compile(
    r"(?:^|:)[gcnmr]\.\(?(?P<start>\d+)(?:[+-]\d+)?_"
    r"(?P<end>\d+)(?:[+-]\d+)?\)?(?P<kind>del|dup|inv)",
    re.IGNORECASE,
)
_SYMBOLIC_SV_RE = re.compile(
    r"(?:^|[:\s])<(?:DEL|DUP|INV|CNV|INS|BND|CPX)>(?:$|[:\s])", re.IGNORECASE
)
_BND_RE = re.compile(r"[ACGTN]*[\[\]][^\[\]]+:\d+[\[\]][ACGTN]*", re.IGNORECASE)
_SV_TOKEN_RE = re.compile(
    r"(?:^|[-_:;\s])(DEL|DUP|INV|BND|CPX|CNV)(?:$|[-_:;\s])", re.IGNORECASE
)
_COPY_NUMBER_RE = re.compile(r"(?:\)|\])x(?:0|1|3|4|\d{2,})$", re.IGNORECASE)

# Primary chromosome RefSeq versions uniquely identify the human assembly.
_GRCH37_VERSIONS = (
    10,
    11,
    11,
    11,
    9,
    11,
    13,
    10,
    11,
    10,
    9,
    11,
    10,
    8,
    9,
    9,
    10,
    9,
    9,
    10,
    8,
    10,
    10,
    9,
)
_GRCH38_VERSIONS = tuple(version + 1 for version in _GRCH37_VERSIONS)
_ACCESSION_BUILDS = {
    **{
        f"NC_{serial:06d}.{version}": "GRCh37"
        for serial, version in enumerate(_GRCH37_VERSIONS, start=1)
    },
    **{
        f"NC_{serial:06d}.{version}": "GRCh38"
        for serial, version in enumerate(_GRCH38_VERSIONS, start=1)
    },
}


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


def classify_variant_scope(variant: str, genome_build: str = "") -> dict[str, Any]:
    """Classify build and small-variant scope before any provider call."""
    original = str(variant or "").strip()
    embedded_builds = {
        _BUILD_ALIASES[match.group(1).casefold()]
        for match in _BUILD_TOKEN_RE.finditer(original)
    }
    requested_build = _BUILD_ALIASES.get(str(genome_build or "").strip().casefold())
    invalid_build = bool(genome_build) and requested_build is None
    normalized_variant = _BUILD_TOKEN_RE.sub(" ", original).strip(" ,;:")
    normalized_variant = " ".join(normalized_variant.split())

    accession_build = next(
        (
            build
            for accession, build in _ACCESSION_BUILDS.items()
            if accession.casefold() in normalized_variant.casefold()
        ),
        "",
    )
    build_conflict = (
        len(embedded_builds) > 1
        or bool(
            requested_build
            and embedded_builds
            and requested_build not in embedded_builds
        )
        or bool(
            requested_build and accession_build and requested_build != accession_build
        )
        or bool(
            embedded_builds
            and accession_build
            and accession_build not in embedded_builds
        )
    )
    if requested_build:
        normalized_build = requested_build
        build_source = (
            "explicit_canonical"
            if str(genome_build).casefold().startswith("grch")
            else "explicit_alias"
        )
    elif len(embedded_builds) == 1:
        normalized_build = next(iter(embedded_builds))
        build_source = "embedded_alias"
    elif accession_build:
        normalized_build = accession_build
        build_source = "accession_inferred"
    else:
        normalized_build = ""
        build_source = "missing"

    interval = _INTERVAL_RE.fullmatch(normalized_variant)
    hgvs_interval = _HGVS_INTERVAL_RE.search(normalized_variant)
    vcf_allele = (
        _VCF_COLON_RE.fullmatch(normalized_variant)
        or _VCF_DASH_RE.fullmatch(normalized_variant)
        or COMPACT_GENOMIC_RE.fullmatch(normalized_variant)
    )
    start = end = None
    explicit_sv = bool(
        _SYMBOLIC_SV_RE.search(normalized_variant)
        or _BND_RE.search(normalized_variant)
        or _SV_TOKEN_RE.search(normalized_variant)
        or _COPY_NUMBER_RE.search(normalized_variant)
    )
    if interval:
        start, end = int(interval.group("start")), int(interval.group("end"))
        explicit_sv = explicit_sv or bool(interval.group("kind"))
    elif hgvs_interval:
        start, end = int(hgvs_interval.group("start")), int(hgvs_interval.group("end"))
    span_bp = abs(end - start) + 1 if start is not None and end is not None else None
    if span_bp is None and vcf_allele:
        ref_length = len(vcf_allele.group("ref"))
        alt_length = len(vcf_allele.group("alt"))
        span_bp = (
            ref_length if ref_length == alt_length else abs(ref_length - alt_length)
        )
    is_structural = explicit_sv or (span_bp is not None and span_bp > 50)
    coordinate_input = bool(
        interval
        or GENOMIC_HGVS_RE.match(normalized_variant)
        or GENOMIC_VCF_RE.fullmatch(normalized_variant)
        or COMPACT_GENOMIC_RE.fullmatch(normalized_variant)
        or _SYMBOLIC_SV_RE.search(normalized_variant)
        or _BND_RE.search(normalized_variant)
    )
    if not normalized_build and not coordinate_input:
        normalized_build = "GRCh38"
        build_source = "default_noncoordinate"
    input_error = (
        "genome_build_conflict"
        if build_conflict
        else "unsupported_genome_build"
        if invalid_build
        else "genome_build_required_for_coordinate_input"
        if coordinate_input and not normalized_build
        else ""
    )
    input_kind = "structural_variant" if is_structural else "small_variant"
    supported = input_kind == "small_variant" and not input_error
    return {
        "input_kind": input_kind,
        "span_bp": span_bp,
        "normalized_genome_build": normalized_build or None,
        "build_resolution_source": build_source,
        "collector_supported": supported,
        "recommended_route": (
            "tooluniverse-structural-variant-analysis"
            if is_structural
            else "tooluniverse-acmg-variant-classification"
        ),
        "input_error": input_error,
        "normalized_variant": normalized_variant,
    }


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


def split_coding_protein_suffix(variant: str) -> tuple[str, str]:
    """Separate an optional submitted ``(p.)`` check from a coding HGVS query.

    Providers receive only the coding HGVS.  The protein expression remains a
    caller-supplied assertion until an identity-bound provider resolves it.
    """
    value = variant.strip()
    match = _CODING_WITH_PROTEIN_SUFFIX_RE.fullmatch(value)
    if match is None:
        return value, ""
    return match.group("coding"), match.group("protein")


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
                        "mane_plus_clinical": annotations.get("mane_plus_clinical")
                        is True,
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
                    select_status = (
                        select_status if isinstance(select_status, dict) else {}
                    )
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
        item
        for item in formatted_transcript_candidates(result)
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
    "split_coding_protein_suffix",
    "transcript_accession",
    "transcript_candidates",
]
