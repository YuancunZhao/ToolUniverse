"""Release-smoke CLI contract tests without performing an installation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "verify_acmg_install_smoke.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("acmg_install_smoke", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_online_provider_flag_is_opt_in(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--source", "local"])
    assert module._parse_args().online_providers is False

    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--source", "local", "--online-providers"],
    )
    assert module._parse_args().online_providers is True


def test_git_ref_requires_a_full_commit_sha(monkeypatch):
    module = _load_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--source", "git-ref", "--git-ref", "deadbeef"],
    )
    with pytest.raises(SystemExit, match="2"):
        module._parse_args()


def test_embedded_online_gate_is_syntax_valid_and_covers_required_sources():
    module = _load_module()
    compile(module.ONLINE_CHECKS_PROGRAM, "<online-provider-smoke>", "exec")
    for name in (
        "ClinGen_search_cspec",
        "ClinGen_get_variant_classifications",
        "ClinVar_search_variants",
        "gnomad_get_variant",
        "MyVariant_get_pathogenicity_scores",
        "EuropePMC_get_full_text",
        "ACMG_evidence_collector",
    ):
        assert name in module.ONLINE_CHECKS_PROGRAM
    assert 'result.get("status") in {"success", "degraded"}' in (
        module.ONLINE_CHECKS_PROGRAM
    )
