"""Guard: the CODE_PATTERNS prediction examples must stay raw-score only.

The doc examples in skills/tooluniverse-variant-interpretation/CODE_PATTERNS.md
must not assign ACMG codes or derive them from predictor votes. This test
extracts the computational-prediction code block, syntax-checks it, and runs
it against stubbed tool queries to assert the aggregation returns only the
raw gathered predictions. It is a documentation-contract check, NOT an LLM
behavior acceptance.
"""

import re
from pathlib import Path

SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "tooluniverse-variant-interpretation"
)
DOC = SKILL_DIR / "CODE_PATTERNS.md"


def _prediction_block():
    text = DOC.read_text()
    blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
    merged = [
        block
        for block in blocks
        if any(
            name in block
            for name in (
                "get_cadd_score",
                "get_alphamissense_score",
                "get_eve_score",
                "get_spliceai_prediction",
                "comprehensive_pathogenicity_assessment",
            )
        )
    ]
    assert merged, "prediction example block not found in CODE_PATTERNS.md"
    return "\n\n".join(merged), text


def test_prediction_examples_contain_no_acmg_fields():
    _, text = _prediction_block()
    for banned in ("acmg_support", "acmg_recommendation", "'consensus'"):
        assert banned not in text, (
            f"CODE_PATTERNS.md still generates {banned!r}; prediction "
            "examples must return raw scores and provider labels only"
        )


def test_comprehensive_assessment_returns_raw_predictions_only():
    block, _ = _prediction_block()
    code = compile(block, str(DOC), "exec")
    namespace = {}
    exec(code, namespace)  # noqa: S102 - compiling the documented example

    class _StubTools:
        def __init__(self):
            self.tools = self  # examples call tu.tools.<function>

        def CADD_get_variant_score(self, **_kw):
            return {
                "status": "success",
                "data": {"phred_score": 33.1, "interpretation": "raw"},
            }

        def AlphaMissense_get_variant_score(self, **_kw):
            return {
                "status": "success",
                "data": {"pathogenicity_score": 0.91, "classification": "pathogenic"},
            }

        def EVE_get_variant_score(self, **_kw):
            return {
                "status": "success",
                "data": {"eve_scores": [{"eve_score": 0.82, "classification": "likely pathogenic", "gene_symbol": "TESTGENE"}]},
            }

    result = namespace["comprehensive_pathogenicity_assessment"](
        _StubTools(),
        {"chrom": 1, "pos": 1000, "ref": "C", "alt": "T",
         "uniprot_id": "P00000", "aa_change": "R123H"},
    )
    assert set(result) == {"predictions"}
    for name, prediction in result["predictions"].items():
        assert isinstance(prediction, dict)
        for key in prediction:
            assert "acmg" not in key.lower(), (name, key)
            assert key not in ("consensus", "recommendation"), (name, key)
    # Raw values pass through untouched.
    assert result["predictions"]["cadd"]["score"] == 33.1
    assert result["predictions"]["alphamissense"]["classification"] == "pathogenic"
    assert result["predictions"]["eve"]["score"] == 0.82
