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


def test_tool_reference_has_no_alternative_acmg_evaluator():
    # Documentation contract only: TOOLS_REFERENCE.md must not carry its own
    # classifier or vote-based PP3/BP4 generator. This does NOT assert that
    # any LLM follows the unified flow.
    text = (SKILL_DIR / "TOOLS_REFERENCE.md").read_text()
    forbidden = (
        "def calculate_acmg_classification(",
        "def get_multi_predictor_evidence(",
        "'acmg_pp3'",
        "'acmg_bp4'",
    )
    for marker in forbidden:
        assert marker not in text, marker


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


def test_old_entry_shortcuts_are_gone():
    # Documentation contract only: the confirmed old shortcut markers must
    # not reappear in the three old-entry files. This does NOT assert that
    # any LLM follows the unified flow.
    forbidden_by_file = {
        "TOOLS_REFERENCE.md": (
            "COSMIC Evidence for ACMG",
            "DisGeNET Score for ACMG",
            "Mapping SAE categories → ACMG support",
            "(PS3_supporting / PP3)",
        ),
        "EXAMPLES.md": (
            "PM1 applies (moderate)",
            "Supports PM2 (absent from controls)",
            "**PS3**: Not directly applicable",
            "**PS1**: Not applicable",
        ),
        "SKILL.md": (
            "Epidemiological data generally trumps",
            "epidemiological evidence is weighted more heavily",
            "lean toward REVEL",
            "the mechanistic evidence ACMG PS3/PP3 actually needs",
        ),
    }
    violations = []
    for name, markers in forbidden_by_file.items():
        content = (SKILL_DIR / name).read_text()
        for marker in markers:
            if marker in content:
                violations.append(f"{name}: {marker!r}")
    assert not violations, "old evaluation shortcuts remain: " + "; ".join(
        violations
    )


_SYNCED_SKILLS = (
    "tooluniverse-acmg-variant-classification",
    "tooluniverse-variant-interpretation",
)


def test_published_copies_match_sources():
    # Content-consistency check for both ACMG-related skills across the
    # Claude (plugin/skills) and Codex (plugins/tooluniverse/skills)
    # distributions: plain Markdown files must match the canonical source
    # byte-for-byte; for Codex SKILL.md only the body after the frontmatter
    # is compared (frontmatter legality is covered by test_codex_plugin).
    repo = Path(__file__).resolve().parents[2]
    problems = []
    for skill in _SYNCED_SKILLS:
        source_dir = repo / "skills" / skill
        for source in sorted(source_dir.rglob("*.md")):
            relative = source.relative_to(source_dir)
            for destination in ("plugin/skills", "plugins/tooluniverse/skills"):
                target = repo / destination / skill / relative
                if not target.exists():
                    problems.append(f"missing: {target}")
                    continue
                expected = source.read_text()
                actual = target.read_text()
                if destination.startswith("plugins/") and source.name == "SKILL.md":
                    expected = expected.split("---", 2)[2]
                    actual = actual.split("---", 2)[2]
                if actual != expected:
                    problems.append(f"differs: {target}")
    assert not problems, "; ".join(problems)
