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
    """Yield ``(tool_name, keywords, lineno)`` for documented tool calls.

    Follow-up 2026-10-14 (Batch D): also provide
    ``_static_tool_arguments`` which evaluates CONSTANT keyword values
    (string/number/boolean/dict/list literals) so guards can check them
    against the registered parameter types and enums.
    """
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


class _DynamicContainer:
    """A dict/list literal with dynamic members; only its JSON type is
    known statically (content checks belong to the executed-example
    stubs)."""

    def __init__(self, json_type):
        self.json_type = json_type


_JSON_TYPE_OF_LITERAL = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
    dict: "object",
    list: "array",
}


def _static_tool_arguments(markdown_text):
    """Yield ``(tool_name, {keyword: literal_value}, lineno)`` for documented
    tool calls whose keyword values are constant literals (f-strings and
    names are skipped -- they are covered by the executed-example stub
    tests)."""
    import ast

    for block in re.findall(r"```python\n(.*?)```", markdown_text, re.DOTALL):
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "tools"
            ):
                continue
            arguments = {}
            for kw in node.keywords:
                if kw.arg is None:
                    continue
                value_node = kw.value
                if isinstance(value_node, ast.Constant):
                    value = value_node.value
                    if isinstance(value, (type(None), tuple, bytes)):
                        continue
                elif isinstance(value_node, ast.Dict):
                    try:
                        value = ast.literal_eval(value_node)
                    except ValueError:
                        # Dynamic members (e.g. {"gene_name": gene_symbol}):
                        # the CONTAINER's JSON type is still a static fact.
                        value = _DynamicContainer("object")
                elif isinstance(value_node, ast.List):
                    try:
                        value = ast.literal_eval(value_node)
                    except ValueError:
                        value = _DynamicContainer("array")
                else:
                    continue
                arguments[kw.arg] = value
            if arguments:
                yield func.attr, arguments, node.lineno


def _registered_tool_specs():
    """{tool_name: {param: property_dict}} from the registered configs."""
    from pathlib import Path

    from tooluniverse.default_config import default_tool_files
    from tooluniverse.utils import read_json_list

    specs = {}
    for path in default_tool_files.values():
        for config in read_json_list(Path(path)):
            name = config.get("name")
            if name:
                specs[name] = config.get("parameter", {}).get(
                    "properties", {}
                )
    return specs


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


# --------------------------------------------------------------------------- #
# Follow-up 2026-10-14 (Batch D): documented example VALUES must match the
# registered parameter types and enums, not just the parameter names.
# The executed-example stubs then validate the DYNAMIC values (f-string
# filters) against the same real schemas, and the structure-collection
# example must preserve the raw SIFTS receipt across all three real
# return shapes without auto-invoking a prediction tool.
# --------------------------------------------------------------------------- #
def test_documented_example_arguments_match_registered_types_and_enums():
    specs = _registered_tool_specs()
    problems = []
    for doc_name in ("TOOLS_REFERENCE.md", "CODE_PATTERNS.md"):
        text = (SKILL_DIR / doc_name).read_text()
        for tool_name, arguments, lineno in _static_tool_arguments(text):
            properties = specs.get(tool_name)
            if not properties:
                continue
            for keyword, value in arguments.items():
                prop = properties.get(keyword)
                if not isinstance(prop, dict):
                    continue
                enum = prop.get("enum")
                if enum and not isinstance(value, _DynamicContainer):
                    if value not in enum:
                        problems.append(
                            f"{doc_name}:{lineno}: {tool_name} parameter "
                            f"{keyword}={value!r} is not in the registered "
                            f"enum {enum}"
                        )
                declared = prop.get("type")
                if isinstance(declared, list):
                    declared_types = set(declared)
                elif declared:
                    declared_types = {declared}
                else:
                    declared_types = set()
                if isinstance(value, _DynamicContainer):
                    actual = value.json_type
                else:
                    actual = _JSON_TYPE_OF_LITERAL.get(type(value))
                if declared_types and actual and actual not in declared_types:
                    problems.append(
                        f"{doc_name}:{lineno}: {tool_name} parameter "
                        f"{keyword} is declared {sorted(declared_types)} "
                        f"but the example passes a {actual}"
                    )
    assert not problems, "\n".join(problems)


class _SchemaValidatingStub:
    """Executes documented examples: every ``tu.tools.<name>(**)`` call is
    validated against the tool's REAL registered schema (required keys,
    declared JSON types, enums) and recorded. Non-tool code runs as-is."""

    def __init__(self):
        import types

        self._specs = _registered_tool_specs()
        self.calls = []
        self._tools = types.SimpleNamespace()
        for name in self._specs:
            setattr(self._tools, name, self._make_validator(name))
        self.tools = self._tools

    def _make_validator(self, tool_name):
        def validate(**kwargs):
            properties = self._specs[tool_name]
            for keyword, value in kwargs.items():
                if keyword not in properties:
                    raise AssertionError(
                        f"{tool_name} has no registered parameter "
                        f"{keyword!r}"
                    )
                prop = properties[keyword]
                enum = prop.get("enum")
                if enum and value not in enum:
                    raise AssertionError(
                        f"{tool_name}.{keyword}={value!r} not in enum "
                        f"{enum}"
                    )
                declared = prop.get("type")
                if isinstance(declared, list):
                    declared_types = set(declared)
                elif declared:
                    declared_types = {declared}
                else:
                    declared_types = set()
                actual = _JSON_TYPE_OF_LITERAL.get(type(value))
                if declared_types and actual and actual not in declared_types:
                    raise AssertionError(
                        f"{tool_name}.{keyword} declared "
                        f"{sorted(declared_types)} but got {actual}"
                    )
            self.calls.append((tool_name, kwargs))
            return {"status": "success", "data": {}}

        return validate

    def tool_names_called(self):
        return [name for name, _ in self.calls]


def _exec_python_block(markdown_text, heading):
    """Extract the ```python block that follows ``heading`` and exec it in
    a fresh namespace; returns the namespace."""
    pattern = re.compile(
        re.escape(heading) + r".*?```python\n(.*?)```", re.DOTALL
    )
    match = pattern.search(markdown_text)
    assert match, f"python block after {heading!r} not found"
    namespace = {}
    exec(compile(match.group(1), "<doc>", "exec"), namespace)  # noqa: S102
    return namespace


def test_cellxgene_dynamic_filter_example_validates_in_stub():
    text = (SKILL_DIR / "CODE_PATTERNS.md").read_text()
    namespace = _exec_python_block(text, "## Phase 4.5")
    stub = _SchemaValidatingStub()
    result = namespace["validate_expression_context"](
        stub, "FBN1", ["Heart - Left Ventricle"]
    )
    calls = {name: kwargs for name, kwargs in stub.calls}
    assert "CELLxGENE_get_expression_data" in calls
    cellxgene = calls["CELLxGENE_get_expression_data"]
    # The dynamic filter value is validated against the registered STRING
    # type and must address the feature-name column.
    filter_value = cellxgene["var_value_filter"]
    assert isinstance(filter_value, str), filter_value
    assert filter_value == "feature_name == 'FBN1'"
    # No operation/organism overrides: the example uses tool defaults.
    assert "operation" not in cellxgene
    assert "organism" not in cellxgene
    assert result["single_cell"] == {"status": "success", "data": {}}


def test_sifts_example_preserves_raw_receipt_across_return_shapes():
    text = (SKILL_DIR / "CODE_PATTERNS.md").read_text()
    namespace = _exec_python_block(text, "## Phase 4")
    assert "collect_structural_context" in namespace, (
        "the structure block must define collect_structural_context(tu, "
        "uniprot_id)"
    )

    has_structures = {
        "status": "success",
        "data": [
            {"pdb_id": "1HYZ", "chain": "A", "resolution": 1.8},
        ],
    }
    healthy_empty = {"status": "success", "data": []}
    request_error = {
        "status": "error",
        "error": "PDBe request failed: HTTP 503",
    }
    for shape in (has_structures, healthy_empty, request_error):
        stub = _SchemaValidatingStub()

        def sifts(**kwargs):
            # Validate against the real schema, then return the concrete
            # shape under test (recorded like every other call).
            stub._make_validator("PDBeSIFTS_get_best_structures")(**kwargs)
            return shape

        stub.tools.PDBeSIFTS_get_best_structures = sifts
        result = namespace["collect_structural_context"](stub, "P35555")
        # Raw status AND content are preserved verbatim -- a request error
        # is never reinterpreted as "no experimental structures", and an
        # empty hit list is not turned into a success-with-hits.
        assert result["experimental_structures"] == shape
        assert result["experimental_structures"]["status"] == shape["status"]
        # Collection stops at SIFTS: no auto-prediction or sequence fetch.
        assert stub.tool_names_called() == ["PDBeSIFTS_get_best_structures"]
