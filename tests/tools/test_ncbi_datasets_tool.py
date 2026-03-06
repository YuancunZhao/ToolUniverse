"""
Test suite for NCBI Datasets tools integration.

Refactored for conciseness with parametrized tests to reduce tech debt.
Includes comprehensive coverage of functionality, error handling, performance,
and OpenAPI specification compliance.
"""

import pytest
import time
import concurrent.futures
import sys
import os
import yaml
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, Mock
import requests
from dotenv import load_dotenv
from tooluniverse import ToolUniverse

# Load environment variables from .env file (for NCBI_API_KEY)
# Find .env file from project root (up from tests/tools/)
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add scripts to path for openapi_validator imports
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "scripts"
    ),
)

try:
    from openapi_validator import get_ncbi_datasets_validator  # noqa: E402

    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False


# Load OpenAPI spec for examples
SPEC_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "tooluniverse"
    / "data"
    / "specs"
    / "ncbi"
    / "openapi3.docs.yaml"
)
OPENAPI_SPEC = None
if SPEC_PATH.exists():
    with open(SPEC_PATH, "r") as f:
        OPENAPI_SPEC = yaml.safe_load(f)


def resolve_schema_ref(ref: str):
    """Resolve a $ref to its schema definition in the OpenAPI spec.

    Args:
        ref: Reference string like '#/components/schemas/SchemaName'

    Returns:
        Resolved schema dict or None if not found
    """
    if not OPENAPI_SPEC or not ref or not ref.startswith("#/"):
        return None

    # Parse ref path (e.g., "#/components/schemas/SchemaName")
    parts = ref.lstrip("#/").split("/")

    # Navigate to the schema
    current = OPENAPI_SPEC
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


def extract_example_from_spec(endpoint: str, param_name: str):
    """
    Extract first example value for a parameter from OpenAPI spec.

    Handles type conversion when spec examples don't match schema types.
    """
    if not OPENAPI_SPEC:
        return None

    endpoint_spec = (
        OPENAPI_SPEC.get("paths", {}).get(endpoint, {}).get("get", {})
    )
    parameters = endpoint_spec.get("parameters", [])

    for param in parameters:
        if param.get("name") == param_name:
            schema = param.get("schema", {})
            examples = param.get("examples", {})
            if examples:
                # Get first example value
                for example_data in examples.values():
                    value = example_data.get("value")
                    if value is not None:
                        # Convert to match schema type if needed
                        if schema.get("type") == "array":
                            items_type = schema.get("items", {}).get("type")
                            if items_type == "string":
                                # Convert int to string, wrap in array
                                if isinstance(value, int):
                                    value = [str(value)]
                                elif isinstance(value, str):
                                    value = [value]
                        return value
    return None


@pytest.fixture(scope="session")
def tooluni():
    """Create a ToolUniverse instance for all tests."""
    tu = ToolUniverse()
    tu.load_tools()
    return tu


@pytest.fixture(autouse=True)
def rate_limit():
    """
    Rate limiting fixture to respect NCBI API limits.

    NCBI allows 10 requests/second with API key, 5 without.
    Adding 0.25s delay = ~4 rps to stay well under limit and avoid
    overwhelming NCBI servers (prevents 504 Gateway Timeout errors).

    This rate is conservative and safe for both scenarios:
    - With API key: 4 req/s << 10 req/s limit (safe)
    - Without API key: 4 req/s << 5 req/s limit (safe)
    """
    yield
    time.sleep(0.25)


@pytest.fixture(scope="session")
def validator():
    """Create an OpenAPI validator instance."""
    if not VALIDATOR_AVAILABLE:
        pytest.skip("OpenAPI validator not available")
    return get_ncbi_datasets_validator()


# ============================================================================
# Test Data - Generated from OpenAPI Spec
# ============================================================================


def generate_test_cases_from_spec():
    """Generate test cases dynamically from OpenAPI spec examples.

    Generates both basic test cases (path params only) and optional
    parameter test cases (path params + query params with examples).
    """
    # Read tool-endpoint mapping from JSON config
    json_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "tooluniverse"
        / "data"
        / "ncbi_datasets_tools.json"
    )
    tool_endpoint_map = {}
    tool_supports_page_size = {}
    tool_json_params = {}  # Store JSON config params for validation

    if json_path.exists():
        import json

        with open(json_path, "r") as f:
            tools_config = json.load(f)

        for tool in tools_config:
            tool_name = tool.get("name")
            endpoint = tool.get("endpoint")
            if tool_name and endpoint:
                tool_endpoint_map[tool_name] = endpoint
                # Check if tool supports page_size parameter
                params = tool.get("parameter", {})
                if isinstance(params, dict):
                    props = params.get("properties", {})
                    tool_supports_page_size[tool_name] = "page_size" in props
                    tool_json_params[tool_name] = props
                else:
                    tool_supports_page_size[tool_name] = False
                    tool_json_params[tool_name] = {}

    test_cases = []

    for tool_name, endpoint in tool_endpoint_map.items():
        endpoint_spec = (
            OPENAPI_SPEC.get("paths", {}).get(endpoint, {}).get("get", {})
        )
        parameters = endpoint_spec.get("parameters", [])

        # Collect path and query parameter examples
        single_args = {}
        multi_args = {}
        path_params = []
        query_param_examples = {}

        for param in parameters:
            param_name = param.get("name")
            examples = param.get("examples", {})
            is_path = param.get("in") == "path"
            is_query = param.get("in") == "query"

            if is_path:
                path_params.append(param_name)

                # Extract examples for PATH parameters (required)
                if examples:
                    example_values = list(examples.values())

                    # First example (usually single value)
                    if example_values:
                        value = example_values[0].get("value")
                        if value is not None:
                            single_args[param_name] = value

                    # Second example (usually multi-value if exists)
                    if len(example_values) > 1:
                        value = example_values[1].get("value")
                        if value is not None and isinstance(value, list):
                            multi_args[param_name] = value

            elif is_query:
                # Collect query param examples/defaults for optional tests
                param_schema = param.get("schema", {})

                # Resolve $ref if present
                if "$ref" in param_schema:
                    ref = param_schema.get("$ref")
                    resolved = resolve_schema_ref(ref)
                    if resolved:
                        param_schema = resolved
                    else:
                        # Skip if can't resolve
                        continue

                # Resolve $ref in array items if present
                items = param_schema.get("items", {})
                if items and "$ref" in items:
                    ref = items.get("$ref")
                    resolved = resolve_schema_ref(ref)
                    if resolved:
                        param_schema["items"] = resolved
                    else:
                        # Skip if can't resolve
                        continue

                # Try to get test value from examples or schema
                value = None

                # 1. Try examples first
                if examples:
                    example_values = list(examples.values())
                    if example_values:
                        value = example_values[0].get("value")
                        # Convert value to match schema type if needed
                        if value is not None and param_schema.get("type") == "array":
                            items_type = param_schema.get(
                                "items", {}).get("type")
                            if items_type == "string":
                                # Convert int/other to string for array[string]
                                if isinstance(value, int):
                                    value = [str(value)]
                                elif isinstance(value, str):
                                    value = [value]
                                elif not isinstance(value, list):
                                    value = [str(value)]

                # 2. If no example, use default value (skip UNSPECIFIED)
                if value is None and "default" in param_schema:
                    default_val = param_schema["default"]
                    if "UNSPECIFIED" not in str(default_val):
                        value = default_val

                # 3. If no default, try enum (skip UNSPECIFIED values)
                if value is None and "enum" in param_schema:
                    enum_values = param_schema["enum"]
                    if enum_values:
                        # Skip UNSPECIFIED sentinel values
                        for enum_val in enum_values:
                            if "UNSPECIFIED" not in str(enum_val):
                                value = enum_val
                                break
                        # If all are UNSPECIFIED, skip this param
                        if value is None:
                            continue

                # 4. For arrays, check items for enum/default
                if value is None and param_schema.get("type") == "array":
                    items_schema = param_schema.get("items", {})
                    if "enum" in items_schema:
                        # Use first non-UNSPECIFIED enum value
                        for enum_val in items_schema["enum"]:
                            if "UNSPECIFIED" not in str(enum_val):
                                value = [enum_val]
                                break
                    elif "default" in items_schema:
                        default_val = items_schema["default"]
                        # Skip UNSPECIFIED defaults
                        if "UNSPECIFIED" not in str(default_val):
                            value = [default_val]
                    elif items_schema.get("type") == "string":
                        # For string arrays without enum/default,
                        # use generic test value
                        value = ["test"]

                # 5. For booleans without default, use False
                if value is None and param_schema.get("type") == "boolean":
                    value = False

                # 6. For plain strings without values (like sort.field)
                # use a generic test value
                if value is None and param_schema.get("type") == "string":
                    # Use parameter name as hint for test value
                    if "field" in param_name.lower():
                        # Use hyphen format per OpenAPI examples
                        value = "gene-id"
                    else:
                        value = "test"

                if value is not None:
                    param_type = param_schema.get("type")

                    # Convert datetime to ISO string
                    if isinstance(value, datetime):
                        value = value.date().isoformat()

                    # Convert string to array if needed
                    if param_type == "array" and not isinstance(value, list):
                        value = [value]

                    query_param_examples[param_name] = value

        # Create basic single-value test case
        if single_args:
            # Only add page_size if tool supports it
            if tool_supports_page_size.get(tool_name, False):
                args = (
                    {**single_args, "page_size": 1}
                    if "page_size" not in single_args
                    else single_args
                )
            else:
                args = single_args

            test_cases.append(
                {
                    "name": tool_name,
                    "args": args,
                    "expected_keys": ["success", "data"] + path_params,
                }
            )

        # Create multi-value test case if available
        if multi_args:
            # Only add page_size if tool supports it
            if tool_supports_page_size.get(tool_name, False):
                args = (
                    {**multi_args, "page_size": 5}
                    if "page_size" not in multi_args
                    else multi_args
                )
            else:
                args = multi_args

            test_cases.append(
                {
                    "name": tool_name,
                    "args": args,
                    "expected_keys": ["success", "data"] + path_params,
                    "expected_count": (
                        len(multi_args[path_params[0]])
                        if path_params and path_params[0] in multi_args
                        else None
                    ),
                }
            )

        # Create individual test case for EACH optional parameter
        # This ensures all parameters are tested without conflicts
        if single_args and query_param_examples:
            # Define parameters that should be skipped from testing
            # These require specific state/context not available in unit tests
            skip_params = {
                "page_token",  # Requires token from previous paginated request
                "sort_direction",  # API rejects even with sort_field
                "sort_field",  # API rejects sorting on these endpoints
            }

            # Define dependent parameter pairs (kept for future use)
            # These must be tested together, not individually
            dependent_pairs = {}

            # Track which params are part of dependent pairs
            dependent_params = set(dependent_pairs.keys()) | set(
                dependent_pairs.values()
            )

            for param_name, value in query_param_examples.items():
                # Skip page_size (handled in base test)
                if param_name == "page_size":
                    continue

                # Convert dot notation to underscore notation
                param_name_converted = param_name.replace(".", "_")

                # Skip params that require special state/context
                if param_name_converted in skip_params:
                    continue

                # Skip dependent params (will be tested as pairs below)
                if param_name_converted in dependent_params:
                    continue

                # Skip only if we couldn't generate a value
                if value is None:
                    continue

                # Create test with base args + this one optional param
                optional_args = {**single_args}
                optional_args[param_name_converted] = value

                # Add page_size if supported
                if tool_supports_page_size.get(tool_name, False):
                    optional_args["page_size"] = 1

                test_cases.append(
                    {
                        "name": tool_name,
                        "args": optional_args,
                        "expected_keys": ["success", "data"] + path_params,
                        "optional_params": True,
                        "param_name": param_name_converted,  # For test ID
                    }
                )

            # Create combined tests for dependent parameter pairs
            for primary_param, required_param in dependent_pairs.items():
                # Check if both params have values
                primary_value = query_param_examples.get(
                    primary_param.replace("_", ".")
                )
                required_value = query_param_examples.get(
                    required_param.replace("_", ".")
                )

                if primary_value is not None and required_value is not None:
                    # Create test with both params
                    optional_args = {**single_args}
                    optional_args[primary_param] = primary_value
                    optional_args[required_param] = required_value

                    # Add page_size if supported
                    if tool_supports_page_size.get(tool_name, False):
                        optional_args["page_size"] = 1

                    test_cases.append(
                        {
                            "name": tool_name,
                            "args": optional_args,
                            "expected_keys": ["success", "data"] + path_params,
                            "optional_params": True,
                            "param_name": f"{primary_param}+{required_param}",
                        }
                    )

    return test_cases


def generate_missing_param_test_cases():
    """Generate missing parameter test cases from OpenAPI spec."""
    if not OPENAPI_SPEC:
        return []

    import json

    json_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "tooluniverse"
        / "data"
        / "ncbi_datasets_tools.json"
    )

    if not json_path.exists():
        return []

    with open(json_path, "r") as f:
        tools_config = json.load(f)

    test_cases = []
    for tool in tools_config:
        tool_name = tool.get("name")
        endpoint = tool.get("endpoint")

        if not (tool_name and endpoint):
            continue

        # Get required parameters from OpenAPI spec
        endpoint_spec = (
            OPENAPI_SPEC.get("paths", {}).get(endpoint, {}).get("get", {})
        )
        parameters = endpoint_spec.get("parameters", [])

        required_params = [
            p.get("name")
            for p in parameters
            if p.get("required") or p.get("in") == "path"
        ]

        # Generate test case for each required parameter
        for req_param in required_params:
            # Args with all required params except the one we're testing
            args = {}
            for other_param in required_params:
                if other_param != req_param:
                    # Get example value from spec
                    param_info = next(
                        (
                            p
                            for p in parameters
                            if p.get("name") == other_param
                        ),
                        None,
                    )
                    if param_info and param_info.get("examples"):
                        examples = param_info.get("examples", {})
                        first_example = (
                            list(examples.values())[0] if examples else None
                        )
                        if first_example:
                            args[other_param] = first_example.get("value")

            if (
                args or len(required_params) == 1
            ):  # Only add if we have args or single required param
                test_cases.append(
                    {
                        "name": tool_name,
                        "args": args,
                        "missing": req_param,
                    }
                )

    return test_cases


def generate_openapi_tool_definitions():
    """Generate OpenAPI tool definitions from JSON config and spec."""
    if not OPENAPI_SPEC:
        return []

    import json

    json_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "tooluniverse"
        / "data"
        / "ncbi_datasets_tools.json"
    )

    if not json_path.exists():
        return []

    with open(json_path, "r") as f:
        tools_config = json.load(f)

    tool_definitions = []
    for tool in tools_config:
        tool_type = tool.get("type")
        endpoint = tool.get("endpoint")

        if not (tool_type and endpoint):
            continue

        # Get all parameters from JSON config
        params = tool.get("parameter", {})
        if isinstance(params, dict):
            props = params.get("properties", {})
            # Convert parameter names back to OpenAPI format
            # (dots instead of underscores for nested params)
            implemented_params = []
            for param_name in props.keys():
                # Convert sort_direction -> sort.direction,
                # filters_assembly_level -> filters.assembly_level,
                # filter_refseq_only -> filter.refseq_only
                if param_name.startswith("sort_"):
                    implemented_params.append(
                        param_name.replace("sort_", "sort.", 1)
                    )
                elif param_name.startswith("filters_"):
                    implemented_params.append(
                        param_name.replace("filters_", "filters.", 1)
                    )
                elif param_name.startswith("filter_"):
                    implemented_params.append(
                        param_name.replace("filter_", "filter.", 1)
                    )
                else:
                    implemented_params.append(param_name)
        else:
            implemented_params = []

        tool_definitions.append(
            {
                "name": tool_type,
                "endpoint": endpoint,
                "implemented_params": implemented_params,
                "min_coverage": 100.0,
            }
        )

    return tool_definitions


# Generate all test data from spec
TOOL_TEST_CASES = generate_test_cases_from_spec()
MISSING_PARAM_TEST_CASES = generate_missing_param_test_cases()
OPENAPI_TOOL_DEFINITIONS = generate_openapi_tool_definitions()


def _get_test_id(tc):
    """Generate test ID matching the parametrize ids lambda."""
    base = (
        f"{tc['name']}_"
        f"{'multi' if tc.get('expected_count') else 'single'}"
    )
    if tc.get("optional_params"):
        base += f"_{tc.get('param_name', 'optional')}"
    return base


# ============================================================================
# Core Functionality Tests
# ============================================================================


def test_ncbi_datasets_tools_exist(tooluni):
    """Verify all NCBI Datasets tools are registered."""
    expected_tools = [tc["name"] for tc in TOOL_TEST_CASES]
    tool_names = [
        tool.get("name")
        for tool in tooluni.all_tools
        if isinstance(tool, dict)
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, f"Tool {tool_name} not found"


@pytest.mark.parametrize(
    "test_case",
    TOOL_TEST_CASES,
    ids=lambda tc: _get_test_id(tc),
)
def test_tool_execution(tooluni, test_case):
    """Test successful execution of each tool with single and multiple IDs."""
    result = tooluni.run(
        {"name": test_case["name"], "arguments": test_case["args"]}
    )

    assert result is not None, "Result should not be None"
    assert isinstance(result, dict), "Result should be a dictionary"
    assert not result.get("error"), f"Unexpected error: {result.get('error')}"
    assert result.get("success") is True, "Request should be successful"

    for key in test_case["expected_keys"]:
        assert key in result, f"Result should contain '{key}'"

    # Verify count for multiple ID tests
    if "expected_count" in test_case:
        id_keys = [
            "gene_ids",
            "symbols",
            "accessions",
            "taxons",
        ]
        for id_key in id_keys:
            if id_key in result:
                expected = test_case["expected_count"]
                actual = len(result[id_key])
                assert (
                    actual == expected
                ), f"Expected {expected} {id_key}, got {actual}"
                break


@pytest.mark.parametrize(
    "test_case",
    MISSING_PARAM_TEST_CASES,
    ids=lambda tc: f"{tc['name']}_missing_{tc['missing']}",
)
def test_missing_parameters(tooluni, test_case):
    """Test error handling for missing required parameters."""
    result = tooluni.run(
        {"name": test_case["name"], "arguments": test_case["args"]}
    )
    assert (
        "error" in result
    ), f"Should return error for missing {test_case['missing']}"


def test_virus_filters(tooluni):
    """Test virus genome summary with multiple filters."""
    result = tooluni.run(
        {
            "name": "ncbi_datasets_virus_genome_summary",
            "arguments": {
                "taxon": "2697049",  # SARS-CoV-2
                "refseq_only": True,
                "annotated_only": True,
            },
        }
    )

    assert result is not None
    if result.get("success"):
        assert "data" in result


# ============================================================================
# Performance & Reliability Tests
# ============================================================================


def test_performance(tooluni):
    """Test that tools respond within acceptable time limits."""
    start_time = time.time()
    result = tooluni.run(
        {
            "name": "ncbi_datasets_gene_by_id",
            "arguments": {"gene_ids": 59067, "page_size": 1},
        }
    )
    elapsed_time = time.time() - start_time

    assert result is not None
    assert (
        elapsed_time < 30
    ), f"Request took {elapsed_time:.2f}s, should be < 30s"


def test_concurrent_execution(tooluni):
    """Test concurrent request handling."""

    def make_call(call_id):
        result = tooluni.run(
            {
                "name": "ncbi_datasets_gene_by_id",
                "arguments": {"gene_ids": 59067, "page_size": 1},
            }
        )
        return call_id, result

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(make_call, i) for i in range(5)]
        results = [
            f.result() for f in concurrent.futures.as_completed(futures)
        ]

    assert len(results) == 5
    for call_id, result in results:
        assert result is not None
        if "success" in result:
            assert result["success"] is True


# ============================================================================
# OpenAPI Specification Compliance Tests
# ============================================================================


@pytest.mark.skipif(
    not VALIDATOR_AVAILABLE, reason="OpenAPI validator not available"
)
@pytest.mark.parametrize(
    "tool_def", OPENAPI_TOOL_DEFINITIONS, ids=lambda t: t["name"]
)
def test_openapi_parameter_coverage(validator, tool_def):
    """Test each tool implements all required parameters from OpenAPI spec."""
    result = validator.validate_tool_parameters(
        tool_def["endpoint"], tool_def["implemented_params"]
    )

    assert result[
        "valid"
    ], f"{tool_def['name']} missing required: {result['missing_required']}"

    assert result["coverage_percent"] >= tool_def["min_coverage"], (
        f"{tool_def['name']} coverage {result['coverage_percent']:.1f}% "
        f"below minimum {tool_def['min_coverage']:.1f}%"
    )


@pytest.mark.skipif(
    not VALIDATOR_AVAILABLE, reason="OpenAPI validator not available"
)
def test_openapi_overall_coverage(validator):
    """Test overall parameter coverage across all tools."""
    total_coverage = sum(
        validator.validate_tool_parameters(
            t["endpoint"], t["implemented_params"]
        )["coverage_percent"]
        for t in OPENAPI_TOOL_DEFINITIONS
    )

    avg_coverage = total_coverage / len(OPENAPI_TOOL_DEFINITIONS)
    assert (
        avg_coverage == 100.0
    ), f"Average coverage {avg_coverage:.1f}% below 100%"


@pytest.mark.skipif(
    not VALIDATOR_AVAILABLE, reason="OpenAPI validator not available"
)
def test_openapi_endpoint_validity(validator):
    """Test all tool endpoints exist in the OpenAPI spec."""
    all_endpoints = validator.list_all_endpoints()
    all_paths = {ep["path"] for ep in all_endpoints}

    for tool_def in OPENAPI_TOOL_DEFINITIONS:
        assert (
            tool_def["endpoint"] in all_paths
        ), f"{tool_def['name']} endpoint '{tool_def['endpoint']}' not found"


@pytest.mark.skipif(
    not VALIDATOR_AVAILABLE, reason="OpenAPI validator not available"
)
def test_openapi_validation_report(validator):
    """Generate comprehensive validation report (always passes)."""
    print("\n" + "=" * 79)
    print("NCBI Datasets Tools - OpenAPI Validation Report")
    print("=" * 79)

    all_valid = True
    for tool_def in OPENAPI_TOOL_DEFINITIONS:
        result = validator.validate_tool_parameters(
            tool_def["endpoint"], tool_def["implemented_params"]
        )

        status = "✅ VALID" if result["valid"] else "❌ INVALID"
        coverage = result["coverage_percent"]
        print(f"\n{tool_def['name']}: {status} ({coverage:.1f}%)")

        if result["missing_required"]:
            missing = ", ".join(result["missing_required"])
            print(f"  ⚠️  Missing required: {missing}")
            all_valid = False

    avg_coverage = sum(
        validator.validate_tool_parameters(
            t["endpoint"], t["implemented_params"]
        )["coverage_percent"]
        for t in OPENAPI_TOOL_DEFINITIONS
    ) / len(OPENAPI_TOOL_DEFINITIONS)

    print("\n" + "=" * 79)
    print(
        f"Summary: {len(OPENAPI_TOOL_DEFINITIONS)} tools, "
        f"{avg_coverage:.1f}% avg coverage, "
        f"{'✅ All valid' if all_valid else '❌ Has issues'}"
    )
    print("=" * 79)


# ============================================================================
# Direct Tool Error Handling Tests
# ============================================================================


def generate_direct_tool_test_cases():
    """Generate direct tool test cases from JSON config."""
    import json

    json_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "tooluniverse"
        / "data"
        / "ncbi_datasets_tools.json"
    )

    if not json_path.exists():
        return []

    with open(json_path, "r") as f:
        tools_config = json.load(f)

    test_cases = []
    for tool in tools_config:
        tool_type = tool.get("type")
        tool_name = tool.get("name")
        endpoint = tool.get("endpoint")

        if not (tool_type and tool_name and endpoint):
            continue

        # Get required parameters from OpenAPI spec
        if OPENAPI_SPEC:
            endpoint_spec = (
                OPENAPI_SPEC.get("paths", {}).get(endpoint, {}).get("get", {})
            )
            parameters = endpoint_spec.get("parameters", [])

            # Find first required path parameter
            for param in parameters:
                if param.get("required") or param.get("in") == "path":
                    param_name = param.get("name")
                    test_cases.append(
                        {
                            "tool_class": tool_type,
                            "tool_name": tool_name,
                            "param_name": param_name,
                        }
                    )
                    break  # Only need one required param per tool

    return test_cases


DIRECT_TOOL_TEST_CASES = generate_direct_tool_test_cases()


@pytest.mark.parametrize(
    "test_case",
    DIRECT_TOOL_TEST_CASES,
    ids=lambda tc: f"{tc['tool_name']}_missing_{tc['param_name']}",
)
def test_direct_tool_missing_required_param(test_case):
    """Test tool error handling for missing required parameters directly."""
    # Import the tool class
    from tooluniverse import ncbi_datasets_tool

    tool_cls = getattr(ncbi_datasets_tool, test_case["tool_class"])
    tool_instance = tool_cls({})

    # Call run with empty arguments
    result = tool_instance.run({})

    # Should return error dict
    assert isinstance(result, dict), "Result should be a dict"
    assert (
        "error" in result
    ), f"Should have error for missing {test_case['param_name']}"
    assert (
        test_case["param_name"] in result["error"].lower()
    ), f"Error should mention {test_case['param_name']}"


# ============================================================================
# Exception Handling Tests
# ============================================================================


def generate_exception_test_cases():
    """Generate exception test cases from TOOL_TEST_CASES.

    Reuses the base single-ID test cases for each tool.
    """
    # Extract single-ID test cases (non-multi, non-optional)
    exception_cases = []
    for tc in TOOL_TEST_CASES:
        if not tc.get("expected_count") and not tc.get("optional_params"):
            exception_cases.append(
                {"tool_name": tc["name"], "args": tc["args"]}
            )

    return exception_cases


EXCEPTION_TEST_CASES = generate_exception_test_cases()


@pytest.mark.parametrize(
    "test_case",
    EXCEPTION_TEST_CASES,
    ids=lambda tc: f"{tc['tool_name']}_http_error",
)
@patch("requests.get")
def test_http_error_handling(mock_get, tooluni, test_case):
    """Test handling of HTTP errors."""
    # Mock HTTP error
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError(
        "500 Server Error"
    )
    mock_get.return_value = mock_response

    result = tooluni.run(
        {"name": test_case["tool_name"], "arguments": test_case["args"]}
    )

    assert isinstance(result, dict), "Result should be a dict"
    assert "error" in result, "Should return error dict for HTTP error"


@pytest.mark.parametrize(
    "test_case",
    EXCEPTION_TEST_CASES,
    ids=lambda tc: f"{tc['tool_name']}_generic_exception",
)
@patch("requests.get")
def test_generic_exception_handling(mock_get, tooluni, test_case):
    """Test handling of generic exceptions."""
    # Mock generic exception
    mock_get.side_effect = Exception("Connection failed")

    result = tooluni.run(
        {"name": test_case["tool_name"], "arguments": test_case["args"]}
    )

    assert isinstance(result, dict), "Result should be a dict"
    assert "error" in result, "Should return error dict for exception"
