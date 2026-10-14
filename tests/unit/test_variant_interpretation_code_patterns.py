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
        "pm1_applicable",
        "assess_pm1",
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
            if "evals" in source.relative_to(source_dir).parts:
                # evals/ is excluded from both distribution sync flows by
                # upstream design -- dev-side acceptance material only.
                continue
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


def test_acmg_reference_has_no_known_overrestrictive_shortcuts():
    # 2026-09-24 review: these exact sentences were confirmed wrong
    # (eligibility confused with evidence guardrails). The check only
    # prevents the known erroneous wording from reappearing; it does NOT
    # prove scientific correctness or that any LLM follows the rules.
    root = SKILL_DIR.parent / "tooluniverse-acmg-variant-classification"
    forbidden = {
        "SVI_REFERENCE.md": (
            "PM1: specification-defined regions only",
            "Without either, PM1 is not_met",
            "discordant calibrated predictors → neither",
            "gnomAD missense z-score > 3.09 is the common convention",
            'specifications define "healthy" thresholds (age, exam) — otherwise record needs_review',
            "epidemiological contradictions take precedence",
            "tools outside the calibrated panel are not usable for scoring",
            "significantly depleted benign missense rate",
        ),
        "SKILL.md": (
            "discordant calibrated predictors → neither",
            "Ambiguous evidence → not_met or needs_review",
            "and under-validated assays leave the criterion at needs_review",
            "no scoring with tools outside the calibrated panel",
        ),
    }
    failures = []
    for name, markers in forbidden.items():
        text = (root / name).read_text().replace("**", "").replace("`", "")
        normalized = " ".join(text.split()).casefold()
        for marker in markers:
            if marker.casefold() in normalized:
                failures.append(f"{name}: {marker}")
    assert not failures, "\n".join(failures)


def test_acmg_reference_has_no_2026_10_13_confirmed_wrong_wording():
    # 2026-10-13 review F02/F08/F09: these exact sentences were confirmed
    # wrong -- the blanket PVS1 exclusion for nearby in-frame splice
    # reconstitution, the unqualified BayesDel calibration row/combination
    # claim (Pejaver 2022 calibrated the no-AF model), the PS1/PM5 protein
    # comparisons lacking a splice-mechanism check, the sweeping "no SVI
    # recommendation for PS1/PM5" source claim (Walker 2023 does give
    # splicing guidance there), and a PS1 identity phrasing readable as a
    # functional-assay precondition. The check only prevents the known
    # erroneous wording from reappearing; it does NOT prove scientific
    # correctness or that any LLM follows the rules.
    root = SKILL_DIR.parent / "tooluniverse-acmg-variant-classification"
    forbidden = {
        "SVI_REFERENCE.md": (
            "strong consensus splice sequence may reconstitute in-frame splicing",
            "bayesdel | 0.13",
            "component (revel, bayesdel) may combine",
            "no svi criteria-specific recommendation exists for ps1/pm5",
            "no svi criteria-specific recommendation exists for pm5",
            "(not merely predicted) identity",
        ),
    }
    failures = []
    for name, markers in forbidden.items():
        text = (root / name).read_text().replace("**", "").replace("`", "")
        normalized = " ".join(text.split()).casefold()
        for marker in markers:
            if marker.casefold() in normalized:
                failures.append(f"{name}: {marker}")
    assert not failures, "\n".join(failures)


# --------------------------------------------------------------------------- #
# F10/F11 (2026-10-13 review): the old entry kept a second, superseded
# classification-combination table, and its collection/structure examples
# called tools by names/parameters the registered configs reject. The
# guards below parse documented python blocks and check every static
# ``tu.tools.<name>(...)`` call against the registered tool configs.
# They catch interface drift in the documentation only; they cannot
# prove that any LLM follows the examples.
# --------------------------------------------------------------------------- #
def _registered_tool_index():
    from pathlib import Path

    from tooluniverse.default_config import default_tool_files
    from tooluniverse.utils import read_json_list

    index = {}
    for path in default_tool_files.values():
        for config in read_json_list(Path(path)):
            name = config.get("name")
            if name:
                parameter = config.get("parameter", {})
                index[name] = (
                    set(parameter.get("properties", {})),
                    set(parameter.get("required", []) or []),
                )
    return index


def _static_tool_calls(markdown_text):
    import ast

    for block in re.findall(r"```python\n(.*?)```", markdown_text, re.DOTALL):
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue  # non-executable prose snippets are not the subject
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # tu.tools.<name>(...) or self.tools.<name>(...)
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "tools"
            ):
                keywords = [kw.arg for kw in node.keywords if kw.arg]
                yield func.attr, keywords, node.lineno


def test_documented_tool_calls_match_registered_configs():
    import sys

    index = _registered_tool_index()
    problems = []
    for doc_name in ("TOOLS_REFERENCE.md", "CODE_PATTERNS.md"):
        text = (SKILL_DIR / doc_name).read_text()
        for tool_name, keywords, lineno in _static_tool_calls(text):
            if tool_name not in index:
                problems.append(f"{doc_name}:{lineno}: unknown tool {tool_name}")
                continue
            legal, required = index[tool_name]
            for keyword in keywords:
                if keyword not in legal:
                    problems.append(
                        f"{doc_name}:{lineno}: {tool_name} has no parameter "
                        f"{keyword!r} (legal: {sorted(legal)})"
                    )
            missing = required - set(keywords)
            if missing:
                problems.append(
                    f"{doc_name}:{lineno}: {tool_name} missing required "
                    f"{sorted(missing)}"
                )
    assert not problems, "\n".join(problems)


def test_checklist_has_no_second_classification_table():
    # The calculator's Tavtigian point system is the ONLY combining rule;
    # the old "Minimum Evidence" rows contradicted it (e.g. Likely Benign
    # ">=1 Strong + >=1 Supporting" vs the calculator's score thresholds).
    text = (SKILL_DIR / "CHECKLIST.md").read_text()
    for marker in (
        "| Classification | Minimum Evidence |",
        "| Likely Pathogenic | ≥1 Strong + ≥2 Moderate |",
        "| Likely Benign | ≥1 Strong + ≥1 Supporting (benign) |",
        "| Benign | ≥1 StandAlone OR ≥2 Strong (benign) |",
    ):
        assert marker not in text, marker


def test_acmg_reference_has_no_2026_10_14_confirmed_wrong_wording():
    # 2026-10-14 follow-up: the review confirmed two PVS1 wording defects
    # that survived the 2026-10-13 round. (1) The blanket rescue
    # confirmation gate -- "only when established evidence such as RNA
    # studies confirms splicing and protein function are preserved" --
    # demanded variant-specific RNA/protein experiments for EVERY rescue
    # N/A, contradicting Walker 2023/Abou Tayoun 2018, under which a
    # sourced, framework-supported prediction of a functional rescue
    # splice site (e.g. a GC donor) can enter the N/A path. (2) The
    # generic-tree phrase offering "Moderate/Supporting" for a
    # non-critical small in-frame loss -- in the generic decision tree a
    # <=10% non-critical in-frame loss is Moderate, and Supporting needs
    # its own applicable rule basis. The check only prevents the known
    # erroneous wording from reappearing; it does NOT prove scientific
    # correctness or that any LLM follows the rules.
    root = SKILL_DIR.parent / "tooluniverse-acmg-variant-classification"
    forbidden = {
        "SVI_REFERENCE.md": (
            "rna studies confirms splicing and protein function are preserved",
            "moderate/supporting per the tree",
        ),
    }
    failures = []
    for name, markers in forbidden.items():
        text = (root / name).read_text().replace("**", "").replace("`", "")
        normalized = " ".join(text.split()).casefold()
        for marker in markers:
            if marker.casefold() in normalized:
                failures.append(f"{name}: {marker}")
    assert not failures, "\n".join(failures)
