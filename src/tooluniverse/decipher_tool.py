"""DECIPHER sequence-variant page tool.

This module extracts public, non-login DECIPHER exact-variant page evidence
needed for ACMG PVS1 NMD-escape assessment. DECIPHER does not currently expose
this NMD escape annotation through a stable public API in ToolUniverse, so this
wrapper uses the server-rendered sequence-variant page as a structured source
and keeps provenance explicit in the output.
"""

from __future__ import annotations

from datetime import datetime, timezone
import html
import math
import re
from typing import Any, Dict, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("DECIPHERSequenceVariantNMDTool")
class DECIPHERSequenceVariantNMDTool(BaseTool):
    """Fetch DECIPHER exact variant page evidence for NMD escape checks."""

    BASE_URL = "https://www.deciphergenomics.org"
    VARIANT_RE = re.compile(
        r"^(?:chr)?(?P<chrom>[1-9]|1[0-9]|2[0-2]|X|Y|MT|M)-"
        r"(?P<pos>[1-9][0-9]*)-(?P<ref>[ACGT]+)-(?P<alt>[ACGT]+)$",
        re.IGNORECASE,
    )
    CODING_POS_RE = re.compile(r"(?:^|:)c\.(?P<pos>\d+)")

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 30
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0 Safari/537.36 ToolUniverse/1.0"
                ),
            }
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}
        variant_id = str(arguments.get("variant_id") or "").strip()
        parsed = self._parse_variant_id(variant_id)
        if not parsed:
            return {
                "status": "error",
                "error": (
                    "variant_id must be GRCh38 chr-pos-ref-alt, e.g. "
                    "15-56464157-T-A"
                ),
                "data": None,
            }

        normalized_variant_id = self._format_variant_id(parsed)
        url = f"{self.BASE_URL}/sequence-variant/{normalized_variant_id}"

        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "DECIPHER request timed out after 30s",
                "url": url,
                "data": None,
            }
        except requests.exceptions.RequestException as exc:
            return {
                "status": "error",
                "error": f"DECIPHER request failed: {exc}",
                "url": url,
                "data": None,
            }

        if response.status_code == 404:
            return {
                "status": "error",
                "error": "DECIPHER sequence variant page returned HTTP 404",
                "url": url,
                "status_code": response.status_code,
                "data": None,
            }

        if response.status_code >= 400:
            return {
                "status": "error",
                "error": (
                    "DECIPHER sequence variant page returned HTTP "
                    f"{response.status_code}"
                ),
                "url": url,
                "status_code": response.status_code,
                "detail": response.text[:500],
                "data": None,
            }

        page_text = response.text or ""
        if not self._looks_like_sequence_variant_page(page_text, normalized_variant_id):
            return {
                "status": "error",
                "error": "DECIPHER page did not contain expected sequence-variant data",
                "url": url,
                "status_code": response.status_code,
                "detail": page_text[:500],
                "data": None,
            }

        coding_position = self._parse_coding_position(arguments.get("coding_hgvs"))
        protein_position = self._parse_positive_int(arguments.get("protein_position"))
        if protein_position is None and coding_position is not None:
            protein_position = int(math.ceil(coding_position / 3.0))

        basic = self._extract_basic_page_data(page_text)
        nmd_result = self._assess_first_100bp_escape(
            coding_position=coding_position,
            protein_position=protein_position,
        )

        data = {
            "variant_id": normalized_variant_id,
            "page_url": url,
            "genome_build": "GRCh38",
            "genomic_position": {
                "chrom": parsed["chrom"],
                "pos": int(parsed["pos"]),
                "ref": parsed["ref"],
                "alt": parsed["alt"],
            },
            "query_context": {
                "transcript_id": arguments.get("transcript_id"),
                "coding_hgvs": arguments.get("coding_hgvs"),
                "coding_position": coding_position,
                "protein_position": protein_position,
            },
            "basic_variant_context": basic,
            "nmd_escape": nmd_result,
            "provenance": {
                "source": "DECIPHER sequence-variant public page",
                "source_url": url,
                "evidence_source": nmd_result["evidence_source"],
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "method": "public_page_fetch_and_first_100bp_escape_assessment",
                "note": (
                    "DECIPHER exact variant page was reachable. v1 assesses the "
                    "DECIPHER-style first-100bp predicted NMD escape region using "
                    "caller-provided protein_position or coding_hgvs; "
                    "HGVS-to-coordinate "
                    "normalization remains upstream."
                ),
            },
        }

        return {
            "status": "success",
            "data": data,
            "url": url,
            "status_code": response.status_code,
        }

    def _parse_variant_id(self, variant_id: str) -> Optional[Dict[str, str]]:
        match = self.VARIANT_RE.match(variant_id)
        if not match:
            return None
        parts = match.groupdict()
        chrom = parts["chrom"].upper()
        if chrom == "M":
            chrom = "MT"
        return {
            "chrom": chrom,
            "pos": parts["pos"],
            "ref": parts["ref"].upper(),
            "alt": parts["alt"].upper(),
        }

    def _format_variant_id(self, parsed: Dict[str, str]) -> str:
        return f"{parsed['chrom']}-{parsed['pos']}-{parsed['ref']}-{parsed['alt']}"

    def _looks_like_sequence_variant_page(self, text: str, variant_id: str) -> bool:
        if "sequence-variant" not in text:
            return False
        if "genomicPosition" in text or "Exact variant searches" in text:
            return True
        return variant_id in text

    def _parse_coding_position(self, coding_hgvs: Any) -> Optional[int]:
        if not coding_hgvs:
            return None
        match = self.CODING_POS_RE.search(str(coding_hgvs))
        if not match:
            return None
        return int(match.group("pos"))

    def _parse_positive_int(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            return None
        return ivalue if ivalue > 0 else None

    def _assess_first_100bp_escape(
        self,
        *,
        coding_position: Optional[int],
        protein_position: Optional[int],
    ) -> Dict[str, Any]:
        region = {
            "type": "first_100bp_predicted_nmd_escape",
            "coding_start": 1,
            "coding_end": 100,
            "protein_start": 1,
            "protein_end": 34,
            "description": "First 100bp predicted to escape NMD",
            "display_position": "1-34aa",
        }

        if coding_position is None and protein_position is None:
            return {
                "interpretation_status": "insufficient_position",
                "overlaps_nmd_escape": None,
                "nmd_escape_regions": [region],
                "matched_region": None,
                "evidence_source": "decipher_page_derived",
                "matched_by": None,
                "message": (
                    "DECIPHER page was fetched, but coding_hgvs or protein_position "
                    "is required to determine overlap with the first-100bp "
                    "NMD escape region."
                ),
            }

        coding_overlap = coding_position is not None and 1 <= coding_position <= 100
        protein_overlap = protein_position is not None and 1 <= protein_position <= 34
        overlaps = bool(coding_overlap or protein_overlap)
        matched_by = []
        if coding_overlap:
            matched_by.append("coding_hgvs")
        if protein_overlap:
            matched_by.append("protein_position")

        return {
            "interpretation_status": "overlap" if overlaps else "not_detected",
            "overlaps_nmd_escape": overlaps,
            "nmd_escape_regions": [region],
            "matched_region": region if overlaps else None,
            "evidence_source": "decipher_page_derived",
            "matched_by": matched_by or None,
            "message": (
                "Variant falls in DECIPHER-style first-100bp predicted "
                "NMD escape region."
                if overlaps
                else (
                    "Variant position does not fall in the first-100bp "
                    "predicted NMD escape region assessed by this v1 tool."
                )
            ),
        }

    def _extract_basic_page_data(self, text: str) -> Dict[str, Any]:
        unescaped = html.unescape(text)
        return {
            "gene_symbol": self._extract_gene_symbol(unescaped),
            "hgnc_description": self._first_regex(
                unescaped, r'hgnc_description:"([^"]+)"'
            ),
            "refseq_transcripts": sorted(
                set(
                    re.findall(
                        r'refseq_accs:\["(NM_[0-9]+(?:\.[0-9]+)?)"\]',
                        unescaped,
                    )
                )
            ),
            "ensembl_transcript_names": sorted(
                set(re.findall(r'ensembl_transcript_name:"([^"]+)"', unescaped))
            ),
            "omim_morbid_diseases": sorted(
                set(re.findall(r'disease_name:"([^"]+)"', unescaped))
            ),
        }

    def _extract_gene_symbol(self, text: str) -> Optional[str]:
        # DECIPHER's Nuxt payload is minified and often aliases symbols through
        # function arguments. This pattern extracts the common argument sequence
        # around coding_start/coding_end/biotype without executing JavaScript.
        match = re.search(r',"([A-Z][A-Z0-9-]{1,15})",\d+,\d+,"protein_coding"', text)
        if match:
            return match.group(1)
        # Fallback for pages whose payload happens to inline a symbol field.
        return self._first_regex(text, r'current_hgnc_symbol:"([A-Z0-9-]+)"')

    def _first_regex(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text)
        if not match:
            return None
        return match.group(1)
