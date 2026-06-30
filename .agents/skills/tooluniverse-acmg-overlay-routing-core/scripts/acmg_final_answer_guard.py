#!/usr/bin/env python3
"""CLI wrapper for canonical ToolUniverse ACMG final-answer guard."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def _load_canonical_module(module_name: str):
    for parent in Path(__file__).resolve().parents:
        package_dir = parent / "src" / "tooluniverse" / "acmg_gate"
        module_path = package_dir / f"{module_name}.py"
        if not module_path.exists():
            continue
        tooluniverse_pkg = types.ModuleType("tooluniverse")
        tooluniverse_pkg.__path__ = [str(parent / "src" / "tooluniverse")]
        acmg_pkg = types.ModuleType("tooluniverse.acmg_gate")
        acmg_pkg.__path__ = [str(package_dir)]
        sys.modules.setdefault("tooluniverse", tooluniverse_pkg)
        sys.modules.setdefault("tooluniverse.acmg_gate", acmg_pkg)
        spec = importlib.util.spec_from_file_location(f"tooluniverse.acmg_gate.{module_name}", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    raise RuntimeError("Could not locate src/tooluniverse/acmg_gate")


_canonical = _load_canonical_module("final_answer_guard")
contains_final_acmg_label = _canonical.contains_final_acmg_label
has_final_acmg_label = _canonical.has_final_acmg_label
guard_final_answer = _canonical.guard_final_answer
main = _canonical.main


if __name__ == "__main__":
    raise SystemExit(main())
