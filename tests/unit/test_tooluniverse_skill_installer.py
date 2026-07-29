"""Contracts for the complete user-facing ToolUniverse Skill installer."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "scripts" / "install_tooluniverse_skills.sh"


def _skill_names(root: Path) -> set[str]:
    return {
        path.name
        for path in root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }


def _generic_names() -> set[str]:
    skills_root = ROOT / "skills"
    candidates = (
        skills_root / "tooluniverse",
        *skills_root.glob("tooluniverse-*"),
        skills_root / "setup-tooluniverse",
    )
    return {path.name for path in candidates if (path / "SKILL.md").is_file()}


@pytest.mark.parametrize(
    ("profile", "expected_names"),
    (
        ("codex", _skill_names(ROOT / "plugins" / "tooluniverse" / "skills")),
        ("claude", _skill_names(ROOT / "plugin" / "skills")),
        ("generic", _generic_names()),
    ),
)
def test_installer_copies_complete_profile_and_preserves_unrelated_skill(
    tmp_path: Path,
    profile: str,
    expected_names: set[str],
):
    destination = tmp_path / profile / "skills"
    unrelated = destination / "user-private-workflow"
    unrelated.mkdir(parents=True)
    (unrelated / "SKILL.md").write_text("private\n", encoding="utf-8")
    (destination / "tooluniverse-acmg-overlay-routing-core").mkdir()
    (destination / "tooluniverse-acmg-pm2-refinement").mkdir()

    run = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--client",
            profile,
            "--dest",
            str(destination),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert run.returncode == 0, run.stderr
    installed_names = _skill_names(destination) - {"user-private-workflow"}
    assert installed_names == expected_names
    assert (unrelated / "SKILL.md").read_text(encoding="utf-8") == "private\n"
    assert not (destination / "tooluniverse-acmg-overlay-routing-core").exists()
    assert not (destination / "tooluniverse-acmg-pm2-refinement").exists()
    assert not list(destination.rglob("test_*.py"))
    assert not list(destination.rglob("*_test.py"))
    if profile in {"codex", "claude"}:
        assert not (destination / "tooluniverse-cs-setup").exists()
    else:
        assert (destination / "tooluniverse-cs-setup" / "SKILL.md").is_file()
    for representative in (
        "tooluniverse",
        "tooluniverse-drug-research",
        "tooluniverse-protein-structure-retrieval",
        "tooluniverse-literature-deep-research",
        "tooluniverse-acmg-variant-classification",
    ):
        assert (destination / representative / "SKILL.md").is_file()


def test_installer_rejects_missing_or_invalid_profile(tmp_path: Path):
    missing = subprocess.run(
        ["bash", str(INSTALLER), "--dest", str(tmp_path / "skills")],
        check=False,
        capture_output=True,
        text=True,
    )
    invalid = subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--client",
            "unknown",
            "--dest",
            str(tmp_path / "skills"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    unsafe = subprocess.run(
        ["bash", str(INSTALLER), "--client", "generic", "--dest", "/"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert missing.returncode == 2
    assert invalid.returncode == 2
    assert unsafe.returncode == 2


def test_plugin_marketplace_and_mcp_manifests_follow_upstream_layout():
    marketplace = json.loads(
        (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
    )
    assert marketplace["plugins"][0]["source"] == {
        "source": "local",
        "path": "./plugins/tooluniverse",
    }

    setup_text = (ROOT / "SETUP.md").read_text(encoding="utf-8")
    match = re.search(r"Commit:\s+([0-9a-f]{40})", setup_text)
    assert match is not None
    validated_sha = match.group(1)

    for relative in ("plugin/.mcp.json", "plugins/tooluniverse/.mcp.json"):
        manifest = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        args = manifest["mcpServers"]["tooluniverse"]["args"]
        assert args == [
            "--refresh",
            "--from",
            (
                "git+https://github.com/YuancunZhao/ToolUniverse.git@"
                f"{validated_sha}"
            ),
            "tooluniverse",
        ]
