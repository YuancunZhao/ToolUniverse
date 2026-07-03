from __future__ import annotations

from tooluniverse.acmg_overlay_tools.pp3_bp4 import overlay_pp3_bp4
from tooluniverse.acmg_overlay_tools.pm2 import overlay_pm2
from tooluniverse.acmg_overlay_tools.overlays import overlay_functional_assay


def test_vcep_override_is_deferred_not_overlay_applied():
    result = overlay_pp3_bp4(vcep_override="PP3_Strong")

    assert result["strength"] == "PP3_Strong"
    assert result["route_outcome"] == "overlay_deferred_to_vcep"
    assert result["guidance_authority"] == "VCEP-specific"
    assert result["overlay_validated"] is False
    assert result["counted"] is True


def test_vcep_override_requires_validator_scope_before_final():
    result = overlay_pm2(vcep_override="PM2")

    assert result["strength"] == "PM2"
    assert result["route_outcome"] == "overlay_deferred_to_vcep"
    assert result["guidance_authority"] == "VCEP-specific"
    assert "VCEP" in result["reason"]


def test_vcep_override_does_not_mask_wrapper_runtime_errors():
    result = overlay_functional_assay(vcep_override="PS3")

    assert result["criterion"] == "PS3/BS3"
    assert result["route_outcome"] == "overlay_deferred_to_vcep"
    assert result["guidance_authority"] == "VCEP-specific"
