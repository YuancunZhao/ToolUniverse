"""Regression guard for review fix F07 (2026-10-13 report): the generated
SDK wrapper for ClinVar_search_variants inserted ``variant_name`` BEFORE
``max_results``, shifting every subsequent positional parameter and
breaking old callers -- ``ClinVar_search_variants("BRCA1", None, None, 10)``
submitted ``variant_name=10, max_results=20`` and was rejected by the
schema.

Contract pinned here: the OLD nine positional parameters keep their order
``gene, condition, variant_id, max_results, limit, clinical_significance,
gene_symbol, significance, query`` with ``variant_name`` appended after
them; keyword calls (``variant_name=`` string or list) work unchanged.
New code should still prefer keyword arguments.

The shared client is mocked in memory; no test reaches NCBI, and the REAL
generated wrapper file is imported (not a re-implementation).
"""

import inspect
from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants
from tooluniverse.tools import ClinVar_search_variants

pytestmark = pytest.mark.unit


class _CapturingClient:
    """Stand-in for the shared client; records the submitted payload."""

    def __init__(self):
        self.captured = None

    def run_one_function(self, payload, **_kwargs):
        self.captured = payload
        return {"status": "success", "data": {}}


def test_old_nine_positional_parameters_keep_their_order():
    parameters = list(
        inspect.signature(ClinVar_search_variants).parameters
    )
    # keyword-only injected params come after *
    assert parameters[:9] == [
        "gene",
        "condition",
        "variant_id",
        "max_results",
        "limit",
        "clinical_significance",
        "gene_symbol",
        "significance",
        "query",
    ]
    # variant_name exists, but only AFTER the old nine.
    assert "variant_name" in parameters
    assert parameters.index("variant_name") >= 9


def test_old_fourth_positional_still_means_max_results():
    client = _CapturingClient()
    with patch(
        "tooluniverse.tools.ClinVar_search_variants.get_shared_client",
        return_value=client,
    ):
        ClinVar_search_variants("BRCA1", None, None, 10)

    arguments = client.captured["arguments"]
    assert arguments["gene"] == "BRCA1"
    assert arguments["max_results"] == 10
    assert "variant_name" not in arguments


def test_variant_name_keyword_string_passes_through():
    client = _CapturingClient()
    with patch(
        "tooluniverse.tools.ClinVar_search_variants.get_shared_client",
        return_value=client,
    ):
        ClinVar_search_variants(gene="CYP2C19", variant_name="c.681G>A")

    arguments = client.captured["arguments"]
    assert arguments["gene"] == "CYP2C19"
    assert arguments["variant_name"] == "c.681G>A"


def test_variant_name_keyword_list_passes_through():
    client = _CapturingClient()
    with patch(
        "tooluniverse.tools.ClinVar_search_variants.get_shared_client",
        return_value=client,
    ):
        ClinVar_search_variants(
            variant_name=["rs4244285", "rs4986893"]
        )

    arguments = client.captured["arguments"]
    assert arguments["variant_name"] == ["rs4244285", "rs4986893"]


# --------------------------------------------------------------------------- #
# Default MCP registration path: the registered config must accept an array
# variant_name through validate_parameters and its return schema must expose
# the F06 completeness fields. This checks the PUBLIC registered entry, not
# a direct handler call.
# --------------------------------------------------------------------------- #
def _registered_config():
    from pathlib import Path

    from tooluniverse.utils import read_json_list

    for tool_config in read_json_list(
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "clinvar_tools.json"
    ):
        if tool_config.get("name") == "ClinVar_search_variants":
            return tool_config
    raise AssertionError(
        "ClinVar_search_variants not found in clinvar_tools.json"
    )


def test_registered_schema_accepts_array_variant_name():
    tool = ClinVarSearchVariants(_registered_config())
    error = tool.validate_parameters(
        {"gene": "CYP2C19", "variant_name": ["rs4244285", "c.681G>A"]}
    )
    assert error is None, error


def test_registered_return_schema_exposes_completeness_fields():
    schema = _registered_config()["return_schema"]
    data_properties = schema["properties"]["data"]["properties"]
    assert "details_complete" in data_properties
    assert "missing_variant_ids" in data_properties
    assert "warnings" in data_properties
