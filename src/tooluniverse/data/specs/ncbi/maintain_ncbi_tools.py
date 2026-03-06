#!/usr/bin/env python3
"""
Master maintenance script for NCBI Datasets tools.

This script orchestrates all maintenance tasks for NCBI tools:
1. Update JSON configs from OpenAPI spec
2. Run validation tests

Usage:
    python maintain_ncbi_tools.py [--all|--json|--validate]

Options:
    --all          Run all maintenance tasks (default)
    --json         Update JSON configs only
    --validate     Run validation tests only
"""

import sys
import subprocess
from pathlib import Path


def run_script(script_name: str, description: str) -> bool:
    """Run a maintenance script and report results."""
    script_path = Path(__file__).parent / "scripts" / script_name

    if not script_path.exists():
        print(f"❌ Script not found: {script_name}")
        return False

    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"Script: scripts/{script_name}")
    print('='*80)

    result = subprocess.run([sys.executable, str(
        script_path)], cwd=Path(__file__).parent)

    if result.returncode == 0:
        print(f"✅ {description} completed successfully")
        return True
    else:
        print(f"❌ {description} failed with code {result.returncode}")
        return False


def run_tests(test_file: str) -> bool:
    """Run pytest on NCBI tools."""
    print(f"\n{'='*80}")
    print("Running: Validation Tests")
    print('='*80)

    # Find repo root
    # This script is in: src/tooluniverse/data/specs/ncbi/maintain_ncbi_tools.py
    # Path hierarchy: ncbi/ <- specs/ <- data/ <- tooluniverse/ <- src/ <- root/
    # Repo root is 5 levels up
    repo_root = Path(__file__).resolve().parents[5]
    test_path = repo_root / "tests" / "tools" / test_file

    if not test_path.exists():
        print(f"❌ Test file not found: {test_path}")
        return False

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
        cwd=repo_root
    )

    if result.returncode == 0:
        print("✅ All tests passed")
        return True
    else:
        print(f"❌ Tests failed with code {result.returncode}")
        return False


def main():
    """Run maintenance tasks based on command line arguments."""
    args = sys.argv[1:]

    # Default to --all if no args
    if not args:
        args = ["--all"]

    tasks = {
        "--json": ("update_ncbi_json_from_openapi.py", "Update JSON Configs"),
    }

    results = {}

    print("\n" + "="*80)
    print("NCBI Datasets Tools - Maintenance Script")
    print("="*80)

    if "--all" in args:
        # Run all tasks in order
        for flag, (script, desc) in tasks.items():
            results[desc] = run_script(script, desc)

        # Run tests last
        results["Tests"] = run_tests("test_ncbi_datasets_tool.py")

    else:
        # Run specific tasks
        for flag, (script, desc) in tasks.items():
            if flag in args:
                results[desc] = run_script(script, desc)

        if "--validate" in args:
            results["Tests"] = run_tests("test_ncbi_datasets_tool.py")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for task, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}  {task}")

    all_passed = all(results.values())
    print("\n" + "="*80)

    if all_passed:
        print("✅ All maintenance tasks completed successfully!")
        return 0
    else:
        print("❌ Some maintenance tasks failed. Check output above.")
        return 1


if __name__ == "__main__":
    exit(main())
