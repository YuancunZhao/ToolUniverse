"""Ensure NCBI Datasets tools avoid endpoints deprecated by the current spec."""

import pytest

from tooluniverse.ncbi_datasets_tool import NCBIDatasetsTool

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, payload, *, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.closed = False

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload

    def close(self):
        self.closed = True


@pytest.mark.parametrize(
    ("endpoint_type", "arguments", "expected_suffix", "payload"),
    [
        (
            "gene_by_id",
            {"gene_id": "7157"},
            "/gene/id/7157/dataset_report",
            {
                "reports": [
                    {
                        "gene": {
                            "gene_id": "7157",
                            "symbol": "TP53",
                            "annotations": [],
                        }
                    }
                ]
            },
        ),
        (
            "gene_by_symbol",
            {"symbol": "TP53", "taxon": "human"},
            "/gene/symbol/TP53/taxon/human/dataset_report",
            {
                "reports": [
                    {
                        "gene": {
                            "gene_id": "7157",
                            "symbol": "TP53",
                        }
                    }
                ]
            },
        ),
    ],
)
def test_gene_tools_use_active_dataset_report_endpoints(
    monkeypatch, endpoint_type, arguments, expected_suffix, payload
):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _FakeResponse(payload)

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)
    tool = NCBIDatasetsTool(
        {
            "name": f"test_{endpoint_type}",
            "fields": {"endpoint_type": endpoint_type},
        }
    )

    result = tool.run(arguments)

    assert result["status"] == "success"
    symbols = (
        [result["data"]["symbol"]]
        if endpoint_type == "gene_by_id"
        else [item["symbol"] for item in result["data"]]
    )
    assert symbols == ["TP53"]
    assert calls[0][0].endswith(expected_suffix)


def test_transient_throttle_retries_and_honors_retry_after(monkeypatch):
    throttled = _FakeResponse(
        {"error": "rate limited"},
        status_code=429,
        headers={"Retry-After": "0"},
    )
    success = _FakeResponse(
        {
            "reports": [
                {
                    "gene": {
                        "gene_id": "7157",
                        "symbol": "TP53",
                        "annotations": [],
                    }
                }
            ]
        }
    )
    responses = iter([throttled, success])
    sleeps = []

    monkeypatch.setattr(
        "tooluniverse.ncbi_datasets_tool.requests.get",
        lambda url, **kwargs: next(responses),
    )
    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.time.sleep", sleeps.append)
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene",
            "fields": {"endpoint_type": "gene_by_id"},
        }
    )

    result = tool.run({"gene_id": "7157"})

    assert result["status"] == "success"
    assert result["data"]["symbol"] == "TP53"
    assert throttled.closed is True
    assert sleeps == [0.0]
