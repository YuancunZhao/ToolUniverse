"""Offline contracts for the gnomAD per-locus callability tool."""

from __future__ import annotations

import pytest

from tooluniverse.gnomad_tool import gnomADGetSiteCallability
from tooluniverse.tool_registry import lazy_import_tool

pytestmark = pytest.mark.unit


TOOL_CONFIG = {
    "type": "gnomADGetSiteCallability",
    "name": "gnomad_get_site_callability",
    "parameter": {"type": "object", "properties": {}},
}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.url = "https://gnomad.broadinstitute.org/api"
        self.text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _tool(payload):
    tool = gnomADGetSiteCallability(TOOL_CONFIG)
    tool.session.post = lambda *args, **kwargs: _FakeResponse(payload)
    return tool


def _payload(*, exome=None, genome=None, build="GRCh38", chrom="1"):
    return {
        "data": {
            "region": {
                "reference_genome": build,
                "chrom": chrom,
                "start": 10,
                "stop": 10,
                "coverage": {"exome": exome or [], "genome": genome or []},
            }
        }
    }


def test_selects_only_the_exact_requested_position_and_preserves_provenance():
    result = _tool(
        _payload(
            exome=[
                {"pos": 9, "median": 2, "over_20": 0.1},
                {"pos": 10, "mean": 31.2, "median": 30, "over_20": 0.91},
            ],
            genome=[{"pos": 10, "mean": 35.0, "median": 34, "over_20": 0.98}],
        )
    ).run({"chrom": "chr1", "position": 10, "dataset": "gnomad_r4"})

    assert result["status"] == "success"
    assert result["data"]["chrom"] == "1"
    assert result["data"]["callsets"]["exome"] == {
        "position": 10,
        "mean": 31.2,
        "median": 30,
        "over_1": None,
        "over_5": None,
        "over_10": None,
        "over_15": None,
        "over_20": 0.91,
        "over_25": None,
        "over_30": None,
        "over_50": None,
        "over_100": None,
    }
    assert result["data"]["callsets"]["genome"]["over_20"] == 0.98
    assert result["data"]["request_arguments"]["position"] == 10
    assert result["data"]["raw_region"]["coverage"]["exome"][0]["pos"] == 9


def test_rejects_known_dataset_build_mismatch_without_requesting_api():
    tool = _tool(_payload())
    result = tool.run(
        {
            "chrom": "1",
            "position": 10,
            "reference_genome": "GRCh37",
            "dataset": "gnomad_r4",
        }
    )
    assert result["status"] == "error"
    assert "GRCh38" in result["error"]


def test_missing_exact_coverage_row_is_no_hit():
    result = _tool(_payload(exome=[{"pos": 9, "median": 20}])).run(
        {"chrom": "1", "position": 10, "dataset": "gnomad_r4"}
    )
    assert result["status"] == "no_hit"
    assert result["data"] is None


def test_position_row_without_coverage_metrics_is_no_hit():
    result = _tool(_payload(exome=[{"pos": 10}])).run(
        {"chrom": "1", "position": 10, "dataset": "gnomad_r4"}
    )
    assert result["status"] == "no_hit"



def test_returned_region_identity_must_match_request():
    result = _tool(_payload(chrom="2")).run(
        {"chrom": "1", "position": 10, "dataset": "gnomad_r4"}
    )
    assert result["status"] == "error"
    assert "identity" in result["error"]


def test_returned_region_coordinates_must_match_request():
    payload = _payload(exome=[{"pos": 10, "median": 30}])
    payload["data"]["region"]["start"] = 9
    result = _tool(payload).run(
        {"chrom": "1", "position": 10, "dataset": "gnomad_r4"}
    )
    assert result["status"] == "error"
    assert "identity" in result["error"]


def test_tool_is_available_through_lazy_registry():
    from tooluniverse._lazy_registry_static import STATIC_LAZY_REGISTRY

    assert STATIC_LAZY_REGISTRY["gnomADGetSiteCallability"] == "gnomad_tool"
    assert lazy_import_tool("gnomADGetSiteCallability") is gnomADGetSiteCallability


def test_tool_config_is_discoverable_through_tooluniverse():
    from tooluniverse import ToolUniverse

    runtime = ToolUniverse(
        tool_files={"gnomad": "src/tooluniverse/data/gnomad_tools.json"},
        keep_default_tools=False,
    )
    runtime.load_tools()

    assert "gnomad_get_site_callability" in runtime.all_tool_dict
