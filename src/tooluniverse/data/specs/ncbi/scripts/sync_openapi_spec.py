#!/usr/bin/env python3
"""
Download the latest NCBI Datasets OpenAPI specification.

Run this before committing to ensure the bundled spec is up to date.
The spec is fetched from the official NCBI URL and saved locally.
Runtime code always uses the bundled spec (never fetches at runtime).

Usage:
    python src/tooluniverse/data/specs/ncbi/scripts/sync_openapi_spec.py
    python src/tooluniverse/data/specs/ncbi/scripts/sync_openapi_spec.py --check
"""

import argparse
import hashlib
import sys
from pathlib import Path

import requests

SPEC_URL = (
    "https://www.ncbi.nlm.nih.gov/datasets/docs/v2/openapi3/openapi3.docs.yaml"
)
SPEC_DIR = Path(__file__).resolve().parent.parent
SPEC_PATH = SPEC_DIR / "openapi3.docs.yaml"


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def sync(check_only: bool = False) -> bool:
    """Download the latest spec and compare with the bundled copy.

    Args:
        check_only: If True, only report whether the spec is outdated
                    without overwriting.

    Returns:
        True if the spec was updated (or would be updated in check mode).
    """
    print(f"Fetching spec from {SPEC_URL} ...")
    resp = requests.get(SPEC_URL, timeout=30)
    resp.raise_for_status()
    remote_bytes = resp.content

    local_bytes = SPEC_PATH.read_bytes() if SPEC_PATH.exists() else b""
    remote_hash = _md5(remote_bytes)
    local_hash = _md5(local_bytes)

    if remote_hash == local_hash:
        print(f"Spec is up to date ({remote_hash}).")
        return False

    print(f"Spec changed: local={local_hash}  remote={remote_hash}")
    print(f"  Remote size: {len(remote_bytes):,} bytes")

    if check_only:
        print("Run without --check to update the local copy.")
        return True

    SPEC_PATH.write_bytes(remote_bytes)
    print(f"Updated {SPEC_PATH}")
    print(
        "Next steps:\n"
        "  1. python src/tooluniverse/data/specs/ncbi/maintain_ncbi_tools.py\n"
        "  2. Review changes with `git diff`\n"
        "  3. Run tests: pytest tests/tools/test_ncbi_datasets_tool.py "
        '--override-ini="addopts=" -v'
    )
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Sync NCBI Datasets OpenAPI specification"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check if the spec is outdated (don't overwrite)",
    )
    args = parser.parse_args()

    try:
        changed = sync(check_only=args.check)
    except requests.RequestException as e:
        print(f"Error fetching spec: {e}", file=sys.stderr)
        sys.exit(1)

    if args.check and changed:
        sys.exit(1)  # Non-zero exit for CI: spec is outdated


if __name__ == "__main__":
    main()
