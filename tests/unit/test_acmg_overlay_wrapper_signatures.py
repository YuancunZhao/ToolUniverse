"""Regression tests for ACMG overlay wrapper signatures."""

import inspect
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.acmg_overlay_tools.overlays import (
    overlay_case_enrichment,
    overlay_de_novo,
    overlay_functional_assay,
    overlay_pvs1_splicing,
    overlay_segregation,
)
from tooluniverse.acmg_overlay_tools.pp3_bp4 import overlay_pp3_bp4
from tooluniverse.tools.ACMG_overlay_case_enrichment import ACMG_overlay_case_enrichment
from tooluniverse.tools.ACMG_overlay_de_novo import ACMG_overlay_de_novo
from tooluniverse.tools.ACMG_overlay_functional_assay import ACMG_overlay_functional_assay
from tooluniverse.tools.ACMG_overlay_pp3_bp4 import ACMG_overlay_pp3_bp4
from tooluniverse.tools.ACMG_overlay_pvs1_splicing import ACMG_overlay_pvs1_splicing
from tooluniverse.tools.ACMG_overlay_segregation import ACMG_overlay_segregation

pytestmark = pytest.mark.unit

WRAPPER_ONLY_PARAMETERS = {"stream_callback", "use_cache", "validate"}

OVERLAY_TOOL_MAPPINGS = [
    ("ACMG_overlay_pp3_bp4", ACMG_overlay_pp3_bp4, overlay_pp3_bp4),
    ("ACMG_overlay_functional_assay", ACMG_overlay_functional_assay, overlay_functional_assay),
    ("ACMG_overlay_segregation", ACMG_overlay_segregation, overlay_segregation),
    ("ACMG_overlay_pvs1_splicing", ACMG_overlay_pvs1_splicing, overlay_pvs1_splicing),
    ("ACMG_overlay_case_enrichment", ACMG_overlay_case_enrichment, overlay_case_enrichment),
    ("ACMG_overlay_de_novo", ACMG_overlay_de_novo, overlay_de_novo),
]


def _positional_or_keyword_parameter_names(function):
    return [
        name
        for name, parameter in inspect.signature(function).parameters.items()
        if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    ]


@pytest.fixture(scope="module")
def acmg_overlay_gate_tool_metadata():
    metadata_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "acmg_overlay_gate_tools.json"
    )
    return {tool["name"]: tool for tool in json.loads(metadata_path.read_text())}


@pytest.mark.parametrize(("tool_name", "wrapper", "overlay"), OVERLAY_TOOL_MAPPINGS)
def test_wrapper_public_parameters_match_underlying_overlay(tool_name, wrapper, overlay):
    assert _positional_or_keyword_parameter_names(wrapper) == _positional_or_keyword_parameter_names(overlay)


@pytest.mark.parametrize(("tool_name", "wrapper", "overlay"), OVERLAY_TOOL_MAPPINGS)
def test_json_parameters_match_wrapper_public_parameters(
    acmg_overlay_gate_tool_metadata,
    tool_name,
    wrapper,
    overlay,
):
    wrapper_parameters = set(_positional_or_keyword_parameter_names(wrapper))
    json_parameters = set(
        acmg_overlay_gate_tool_metadata[tool_name]["parameter"]["properties"].keys()
    )

    assert json_parameters == wrapper_parameters
    assert json_parameters.isdisjoint(WRAPPER_ONLY_PARAMETERS)


def test_functional_assay_wrapper_accepts_overlay_inputs():
    result = ACMG_overlay_functional_assay(
        functional_evidence="variant-specific assay",
        assay_type="enzyme activity",
        variant_specific=True,
        replicated=True,
        has_controls=True,
        statistically_significant=True,
        effect_direction="loss of function",
    )

    assert result["criterion"] == "PS3"
    assert result["counted"] is True


def test_segregation_wrapper_accepts_overlay_inputs():
    result = ACMG_overlay_segregation(
        segregation_present=True,
        affected_meioses=3,
        total_meioses=3,
    )

    assert result["criterion"] == "PP1"
    assert result["strength"] == "PP1"


def test_pvs1_splicing_wrapper_accepts_overlay_inputs():
    result = ACMG_overlay_pvs1_splicing(
        spliceai_dl=0.7,
        is_canonical_gt_ag=True,
        rna_evidence=False,
        nmd_predicted=True,
    )

    assert result["criterion"] == "PVS1"
    assert result["strength"] == "PVS1_Moderate"


def test_case_enrichment_wrapper_accepts_overlay_inputs():
    result = ACMG_overlay_case_enrichment(
        case_count=10,
        control_count=1000,
        odds_ratio=3.0,
        confidence_interval_lower=1.2,
        phenotype_consistent=True,
    )

    assert result["criterion"] == "PS4"
    assert result["counted"] is True


def test_de_novo_wrapper_accepts_overlay_inputs():
    result = ACMG_overlay_de_novo(
        de_novo_confirmed=True,
        paternity_confirmed=True,
        phenotype_consistent=True,
    )

    assert result["criterion"] == "PS2"
    assert result["strength"] == "PS2_Moderate"
