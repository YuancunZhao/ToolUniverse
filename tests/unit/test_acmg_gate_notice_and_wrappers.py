"""Regression tests for ACMG gate notice sharing and wrapper forwarding."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _load_wrapper_module(module_stem, monkeypatch):
    """Load one generated wrapper without importing tooluniverse.tools.__init__."""
    import importlib.util
    import sys
    import types
    from pathlib import Path

    package = types.ModuleType("tooluniverse.tools")
    package.__path__ = [str(Path(__file__).parents[2] / "src" / "tooluniverse" / "tools")]
    monkeypatch.setitem(sys.modules, "tooluniverse.tools", package)

    shared = types.ModuleType("tooluniverse.tools._shared_client")
    shared.get_shared_client = MagicMock()
    monkeypatch.setitem(sys.modules, "tooluniverse.tools._shared_client", shared)

    path = Path(__file__).parents[2] / "src" / "tooluniverse" / "tools" / f"{module_stem}.py"
    spec = importlib.util.spec_from_file_location(f"tooluniverse.tools.{module_stem}", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module, shared


def test_genebe_uses_shared_acmg_gate_notice():
    from tooluniverse.acmg_gate_policy import ACMG_GATE_NOTICE
    from tooluniverse.genebe_tool import GeneBeTool

    tool = GeneBeTool({"name": "GeneBe_classify_variant", "type": "GeneBeTool", "fields": {}})
    response = MagicMock()
    response.status_code = 200
    response.text = ""
    response.json.return_value = {
        "variants": [
            {
                "gene_symbol": "BRAF",
                "acmg_classification": "Pathogenic",
                "hgvs_c": "NM_004333.6:c.1799T>A",
            }
        ]
    }
    with patch("tooluniverse.genebe_tool.requests.get", return_value=response):
        result = tool.run({"chr": "7", "pos": 140753336, "ref": "A", "alt": "T"})

    assert result["metadata"]["acmg_gate_notice"] == ACMG_GATE_NOTICE


def test_overlay_gate_source_leads_use_shared_notice():
    from tooluniverse.acmg_gate_policy import SOURCE_LEAD_NOTICE
    from tooluniverse.acmg_overlay_gate_tool import ACMGOverlayGateTool

    tool = ACMGOverlayGateTool({"name": "ACMG_overlay_gate_assess_variant", "type": "ACMGOverlayGateTool"})
    leads = tool._normalize_source_leads([{"source": "ClinVar", "classification": "Pathogenic"}])

    assert leads[0]["countable"] is False
    assert leads[0]["reason"] == SOURCE_LEAD_NOTICE


def test_tool_json_acmg_gate_notices_are_canonical():
    import json
    from pathlib import Path

    from tooluniverse.acmg_gate_policy import ACMG_GATE_NOTICE

    data_dir = Path(__file__).parents[2] / "src" / "tooluniverse" / "data"
    seen = []
    for path in data_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        entries = payload if isinstance(payload, list) else [payload]
        for entry in entries:
            if isinstance(entry, dict) and "acmg_gate_notice" in entry:
                seen.append((path.name, entry.get("name")))
                assert entry["acmg_gate_notice"] == ACMG_GATE_NOTICE

    assert seen


def test_tools_package_imports_common_variant_wrappers():
    from tooluniverse.tools import (
        ClinVar_get_clinical_significance,
        ClinVar_get_variant_details,
        UniProt_get_entry_by_accession,
        dbsnp_get_variant_by_rsid,
    )

    assert callable(ClinVar_get_clinical_significance)
    assert callable(ClinVar_get_variant_details)
    assert callable(UniProt_get_entry_by_accession)
    assert callable(dbsnp_get_variant_by_rsid)


def test_variantvalidator_wrapper_forwards_arguments(monkeypatch):
    module, shared = _load_wrapper_module("VariantValidator_validate_variant", monkeypatch)

    client = MagicMock()
    client.run_one_function.return_value = {"status": "ok"}
    shared.get_shared_client.return_value = client
    with patch.object(module, "get_shared_client", shared.get_shared_client):
        result = module.VariantValidator_validate_variant(
            genome_build="GRCh38",
            variant_description="NM_000059.4:c.5946delT",
            select_transcripts="mane_select",
            use_cache=True,
            validate=False,
        )

    assert result == {"status": "ok"}
    client.run_one_function.assert_called_once()
    payload = client.run_one_function.call_args.args[0]
    assert payload == {
        "name": "VariantValidator_validate_variant",
        "arguments": {
            "genome_build": "GRCh38",
            "variant_description": "NM_000059.4:c.5946delT",
            "select_transcripts": "mane_select",
        },
    }
    assert client.run_one_function.call_args.kwargs["use_cache"] is True
    assert client.run_one_function.call_args.kwargs["validate"] is False


def test_variantvalidator_formatter_wrapper_forwards_arguments(monkeypatch):
    module, shared = _load_wrapper_module(
        "VariantValidator_format_genomic_to_transcripts", monkeypatch
    )

    client = MagicMock()
    client.run_one_function.return_value = {"status": "ok"}
    shared.get_shared_client.return_value = client
    with patch.object(module, "get_shared_client", shared.get_shared_client):
        result = module.VariantValidator_format_genomic_to_transcripts(
            variant_description="NC_000017.11:g.50198002C>A",
            genome_build="GRCh38",
            use_cache=True,
            validate=False,
        )

    assert result == {"status": "ok"}
    payload = client.run_one_function.call_args.args[0]
    assert payload == {
        "name": "VariantValidator_format_genomic_to_transcripts",
        "arguments": {
            "genome_build": "GRCh38",
            "variant_description": "NC_000017.11:g.50198002C>A",
        },
    }
    assert client.run_one_function.call_args.kwargs["use_cache"] is True
    assert client.run_one_function.call_args.kwargs["validate"] is False


@pytest.mark.parametrize(
    ("module_name", "function_name", "kwargs", "expected_name", "expected_arguments"),
    [
        (
            "tooluniverse.tools.CADD_get_variant_score",
            "CADD_get_variant_score",
            {"chrom": "7", "pos": 140753336, "ref": "A", "alt": "T"},
            "CADD_get_variant_score",
            {
                "chrom": "7",
                "pos": 140753336,
                "ref": "A",
                "alt": "T",
                "version": "GRCh38-v1.7",
                "include_annotations": False,
            },
        ),
        (
            "tooluniverse.tools.SpliceAI_predict_splice",
            "SpliceAI_predict_splice",
            {"variant": "chr7-140753336-A-T", "genome": "38", "distance": 50, "mask": False},
            "SpliceAI_predict_splice",
            {"variant": "chr7-140753336-A-T", "genome": "38", "distance": 50, "mask": False},
        ),
    ],
)
def test_prediction_wrappers_forward_as_context_only(
    monkeypatch, module_name, function_name, kwargs, expected_name, expected_arguments
):
    module, shared = _load_wrapper_module(module_name.rsplit(".", 1)[-1], monkeypatch)
    client = MagicMock()
    client.run_one_function.return_value = {"status": "ok"}
    shared.get_shared_client.return_value = client
    with patch.object(module, "get_shared_client", shared.get_shared_client):
        getattr(module, function_name)(**kwargs)

    payload = client.run_one_function.call_args.args[0]
    assert payload["name"] == expected_name
    assert payload["arguments"] == expected_arguments
