"""Distinguish gnomAD empty variant results from transport failures."""

from __future__ import annotations

from unittest.mock import patch

import requests

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


class _SequenceResponse:
    url = "https://gnomad.broadinstitute.org/api"
    text = ""

    def __init__(self, status_code: int, payload: dict, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


class _SequenceSession:
    def __init__(self, responses):
        self.responses = list(responses)

    def post(self, *_args, **_kwargs):
        return self.responses.pop(0)


def _retry_tool(*responses):
    tool = gnomADGraphQLQueryTool(_config("gnomADGraphQLQueryTool"))
    tool.session = _SequenceSession(responses)
    return tool


def test_variant_query_retries_429_then_succeeds():
    tool = _retry_tool(
        _SequenceResponse(429, {}, {"Retry-After": "0"}),
        _SequenceResponse(
            200,
            {"data": {"variant": {"variant_id": "1-1-A-T"}}},
        ),
    )

    with (
        patch("tooluniverse.http_utils.time.sleep"),
        patch("tooluniverse.http_utils.random.uniform", return_value=0.0),
    ):
        result = tool.run({"variant_id": "1-1-A-T", "dataset": "gnomad_r4"})

    assert result["status"] == "success"
    assert result["retry_attempts"] == 1
    assert [row["status_code"] for row in result["retry_trace"]] == [429, 200]


def test_variant_query_retries_graphql_overload_then_succeeds():
    tool = _retry_tool(
        _SequenceResponse(200, {"errors": [{"message": "Service overloaded"}]}),
        _SequenceResponse(
            200,
            {"data": {"variant": {"variant_id": "1-1-A-T"}}},
        ),
    )

    with patch("tooluniverse.http_utils._jittered_sleep"):
        result = tool.run({"variant_id": "1-1-A-T", "dataset": "gnomad_r4"})

    assert result["status"] == "success"
    assert result["retry_attempts"] == 1


def test_variant_query_reports_exhausted_transient_retries():
    tool = _retry_tool(
        *[_SequenceResponse(503, {}) for _ in range(3)],
    )

    with patch("tooluniverse.http_utils._jittered_sleep"):
        result = tool.run({"variant_id": "1-1-A-T", "dataset": "gnomad_r4"})

    assert result["status"] == "error"
    assert result["status_code"] == 503
    assert result["retry_attempts"] == 2
    assert len(result["retry_trace"]) == 3
