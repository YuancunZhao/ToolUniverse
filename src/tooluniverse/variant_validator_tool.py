"""Dedicated VariantValidator REST wrapper tools."""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import quote

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("VariantValidatorTool")
class VariantValidatorTool(BaseTool):
    """Small typed wrapper for VariantValidator path-based endpoints."""

    BASE_URL = "https://rest.variantvalidator.org"
    TIMEOUT = 30

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.api_name = tool_config.get("name", "VariantValidator")

    def _normalize_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        args = dict(arguments or {})
        if "gene_symbol" not in args:
            if "gene" in args:
                args["gene_symbol"] = args["gene"]
            elif "gene_name" in args:
                args["gene_symbol"] = args["gene_name"]

        properties = self.tool_config.get("parameter", {}).get("properties", {})
        for name, spec in properties.items():
            if name not in args and "default" in spec:
                args[name] = spec["default"]
        return args

    def _segment(self, value: Any) -> str:
        return quote(str(value), safe="")

    def _url_for(self, args: Dict[str, Any]) -> str:
        name = self.tool_config.get("name")
        if name == "VariantValidator_validate_variant":
            return (
                f"{self.BASE_URL}/VariantValidator/variantvalidator/"
                f"{self._segment(args['genome_build'])}/"
                f"{self._segment(args['variant_description'])}/"
                f"{self._segment(args['select_transcripts'])}"
            )
        if name == "VariantValidator_gene2transcripts":
            return (
                f"{self.BASE_URL}/VariantValidator/tools/gene2transcripts_v2/"
                f"{self._segment(args['gene_symbol'])}/"
                f"{self._segment(args.get('transcript_set', 'mane'))}/all/"
                f"{self._segment(args.get('genome_build', 'GRCh38'))}"
            )
        if name == "VariantValidator_format_genomic_to_transcripts":
            return (
                f"{self.BASE_URL}/VariantFormatter/variantformatter/"
                f"{self._segment(args.get('genome_build', 'GRCh38'))}/"
                f"{self._segment(args['variant_description'])}/refseq/all/False"
            )
        raise ValueError(f"Unsupported VariantValidator tool: {name}")

    def _error_result(
        self,
        message: str,
        *,
        url: str | None = None,
        status_code: int | None = None,
        detail: Any = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {"status": "error", "error": message}
        if url:
            result["url"] = url
        if status_code is not None:
            result["status_code"] = status_code
        if detail is not None:
            result["detail"] = detail
        return result

    def _diagnostic_hint(self, status_code: int, detail: str) -> str | None:
        if (
            self.tool_config.get("name") == "VariantValidator_validate_variant"
            and status_code == 404
            and "VariantFormatter" in detail
        ):
            return (
                "For genomic variants projected to all transcripts, use "
                "VariantValidator_format_genomic_to_transcripts."
            )
        return None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        args = self._normalize_arguments(arguments)
        url = None
        try:
            url = self._url_for(args)
            response = request_with_retry(
                self.session,
                "GET",
                url,
                headers={"Accept": "application/json"},
                timeout=self.TIMEOUT,
                max_attempts=3,
            )
        except KeyError as exc:
            return self._error_result(
                f"{self.api_name}: missing required argument {exc.args[0]!r}"
            )
        except Exception as exc:
            return self._error_result(f"{self.api_name} request failed: {exc}", url=url)

        detail_text = (response.text or "")[:500]
        if not (200 <= response.status_code < 300):
            result = self._error_result(
                f"{self.api_name} API error",
                url=response.url or url,
                status_code=response.status_code,
                detail=detail_text,
            )
            hint = self._diagnostic_hint(response.status_code, detail_text)
            if hint:
                result["hint"] = hint
            return result

        try:
            data = response.json()
        except Exception:
            return self._error_result(
                f"{self.api_name}: server returned a non-JSON response",
                url=response.url or url,
                status_code=response.status_code,
                detail=detail_text,
            )

        result: Dict[str, Any] = {
            "status": "success",
            "data": data,
            "url": response.url or url,
        }
        if isinstance(data, list):
            result["count"] = len(data)
        return result
