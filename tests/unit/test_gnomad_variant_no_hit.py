"""Distinguish gnomAD empty variant results from transport failures."""

from __future__ import annotations

from tooluniverse.gnomad_tool import gnomADGraphQLQueryTool


class _FakeResponse:
    status_code = 200
    url = "https://gnomad.broadinstitute.org/api"
    text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return {"data": {"variant": None}}


def _config(tool_type: str) -> dict:
    return {
        "type": tool_type,
        "name": "gnomad_get_variant",
        "parameter": {"type": "object", "properties": {}},
        "fields": {
            "query_schema": "query { variant { variant_id } }",
            "variable_map": {"variant_id": "variantId"},
        },
    }


def test_generic_variant_query_returns_no_hit_for_null_variant():
    tool = gnomADGraphQLQueryTool(_config("gnomADGraphQLQueryTool"))
    tool.session.post = lambda *args, **kwargs: _FakeResponse()

    result = tool.run({"variant_id": "1-1-A-T", "dataset": "gnomad_r4"})

    assert result["status"] == "no_hit"
    assert result["data"] is None
