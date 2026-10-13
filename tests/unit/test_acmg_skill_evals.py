"""Offline checks for the ACMG skill's acceptance case definitions.

Contract checks only: unique case ids, referenced attachments exist, and
the synthetic case-3 payload still yields the expected result through the
REAL calculator handler. They do not assert that any LLM followed the
skill (that is the separate, recorded host acceptance).
"""

import json
from pathlib import Path

from tooluniverse.clinical_calculators_tool import _acmg_classification

SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "tooluniverse-acmg-variant-classification"
)
EVALS = SKILL_DIR / "evals" / "evals.json"


def _cases():
    return json.loads(EVALS.read_text())["evals"]


def test_case_ids_unique_and_complete():
    ids = [case["id"] for case in _cases()]
    assert ids == [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    ]
    assert len(set(ids)) == 15


def test_attachments_exist():
    for case in _cases():
        for relative in case["files"]:
            assert (SKILL_DIR / "evals" / relative).exists(), (
                case["id"],
                relative,
            )


def test_synthetic_case3_payload_computes_expected_result():
    payload = json.loads(
        (SKILL_DIR / "evals" / "files" / "case3-synthetic-calculator-input.json")
        .read_text()
    )
    # The retired criteria must be recorded as deprecated, never met.
    for record in payload["evidence"]:
        if record["criterion"] in ("PP5", "BP6"):
            assert record["status"] == "deprecated"
    result = _acmg_classification(payload)
    assert result["status"] == "success"
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "Likely Pathogenic"
    assert data["total_score"] == 9
