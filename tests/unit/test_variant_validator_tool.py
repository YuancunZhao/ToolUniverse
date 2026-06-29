"""VariantValidatorTool behavior tests."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.variant_validator_tool import VariantValidatorTool

pytestmark = pytest.mark.unit


def _config(name):
    path = Path(__file__).parents[2] / "src" / "tooluniverse" / "data" / "variant_validator_tools.json"
    configs = json.loads(path.read_text())
    return next(entry for entry in configs if entry["name"] == name)


def _response(status_code=200, payload=None, text="{}", url="https://example.test"):
    response = MagicMock()
    response.status_code = status_code
    response.url = url
    response.text = text
    if payload is None:
        response.json.side_effect = ValueError("not json")
    else:
        response.json.return_value = payload
    return response


def test_variantvalidator_configs_use_dedicated_tool_type():
    path = Path(__file__).parents[2] / "src" / "tooluniverse" / "data" / "variant_validator_tools.json"
    configs = json.loads(path.read_text())

    assert {entry["type"] for entry in configs} == {"VariantValidatorTool"}
    gene2transcripts = next(
        entry for entry in configs if entry["name"] == "VariantValidator_gene2transcripts"
    )
    assert gene2transcripts["parameter"]["anyOf"] == [
        {"required": ["gene_symbol"]},
        {"required": ["gene"]},
        {"required": ["gene_name"]},
    ]


def test_variantvalidator_tool_is_in_static_lazy_registry():
    from tooluniverse._lazy_registry_static import STATIC_LAZY_REGISTRY

    assert STATIC_LAZY_REGISTRY["VariantValidatorTool"] == "variant_validator_tool"


def test_validate_variant_url_encodes_hgvs_path_segments():
    tool = VariantValidatorTool(_config("VariantValidator_validate_variant"))
    response = _response(payload={"flag": "gene_variant"}, url="https://vv.test/result")

    with patch("tooluniverse.variant_validator_tool.request_with_retry", return_value=response) as mocked:
        result = tool.run(
            {
                "genome_build": "GRCh38",
                "variant_description": "NM_000059.4:c.5946delT",
                "select_transcripts": "NM_000059.4",
            }
        )

    assert result["status"] == "success"
    requested_url = mocked.call_args.args[2]
    assert "NM_000059.4%3Ac.5946delT" in requested_url


def test_gene2transcripts_aliases_and_defaults():
    tool = VariantValidatorTool(_config("VariantValidator_gene2transcripts"))
    response = _response(payload=[{"requested_symbol": "LDLR"}])

    with patch("tooluniverse.variant_validator_tool.request_with_retry", return_value=response) as mocked:
        result = tool.run({"gene": "LDLR"})

    assert result["status"] == "success"
    assert result["count"] == 1
    requested_url = mocked.call_args.args[2]
    assert requested_url.endswith("/LDLR/mane/all/GRCh38")


def test_variantformatter_defaults_and_url_encoding():
    tool = VariantValidatorTool(_config("VariantValidator_format_genomic_to_transcripts"))
    response = _response(payload={"metadata": {}})

    with patch("tooluniverse.variant_validator_tool.request_with_retry", return_value=response) as mocked:
        result = tool.run({"variant_description": "NC_000017.11:g.50198002C>A"})

    assert result["status"] == "success"
    requested_url = mocked.call_args.args[2]
    assert "/GRCh38/" in requested_url
    assert "NC_000017.11%3Ag.50198002C%3EA" in requested_url


def test_http_error_is_normalized_with_variantformatter_hint():
    tool = VariantValidatorTool(_config("VariantValidator_validate_variant"))
    response = _response(
        status_code=404,
        text="Please use VariantFormatter for this request",
        url="https://vv.test/error",
    )

    with patch("tooluniverse.variant_validator_tool.request_with_retry", return_value=response):
        result = tool.run(
            {
                "genome_build": "GRCh38",
                "variant_description": "NC_000017.11:g.50198002C>A",
                "select_transcripts": "all",
            }
        )

    assert result["status"] == "error"
    assert result["status_code"] == 404
    assert "VariantValidator_format_genomic_to_transcripts" in result["hint"]


def test_non_json_response_is_normalized():
    tool = VariantValidatorTool(_config("VariantValidator_gene2transcripts"))
    response = _response(text="<html>maintenance</html>", url="https://vv.test/html")

    with patch("tooluniverse.variant_validator_tool.request_with_retry", return_value=response):
        result = tool.run({"gene_symbol": "TP53"})

    assert result == {
        "status": "error",
        "error": "VariantValidator_gene2transcripts: server returned a non-JSON response",
        "url": "https://vv.test/html",
        "status_code": 200,
        "detail": "<html>maintenance</html>",
    }
