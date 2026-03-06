# NCBI Datasets API Integration

Specification-driven maintenance directory for NCBI Datasets API tools in
ToolUniverse. All configurations, tests, and documentation are automatically
generated from the official OpenAPI specification.

## Directory Structure

```bash
ncbi/
├── maintain_ncbi_tools.py              # Master maintenance orchestrator
├── README.md                            # This documentation
├── KNOWN_TEST_FAILURES.md              # Tracked upstream API failures
├── openapi3.docs.yaml                  # Official NCBI OpenAPI spec v2
└── scripts/
    ├── update_ncbi_json_from_openapi.py
    ├── discover_and_generate.py
    └── sync_openapi_spec.py
```

## Quick Start

### Run All Maintenance Tasks

```bash
python src/tooluniverse/data/specs/ncbi/maintain_ncbi_tools.py
```

Executes:

1. JSON configuration update from OpenAPI specification
2. Validation test suite

### Selective Execution

```bash
# Update configurations only
python src/tooluniverse/data/specs/ncbi/maintain_ncbi_tools.py --json

# Run validation tests only
python src/tooluniverse/data/specs/ncbi/maintain_ncbi_tools.py --validate
```

## Architecture

### Design Principles

1. **Single Source of Truth**: OpenAPI specification drives all
   configurations
2. **Zero Hardcoding**: Parameters extracted dynamically from specification
3. **Automated Validation**: 100% parameter coverage enforced by tests
4. **Minimal Maintenance**: Specification updates propagate automatically

### Data Flow

```bash
OpenAPI Specification (openapi3.docs.yaml)
    ↓
Scripts (parse, extract, generate)
    ↓
Outputs:
    ├── JSON configurations (ncbi_datasets_tools.json)
    ├── Test definitions (TOOL_DEFINITIONS)
    └── Wrapper templates (with docstrings)
```

## Workflows

### 1. OpenAPI Specification Update

The bundled spec (`openapi3.docs.yaml`) is the single source of truth at
runtime. It is **never fetched automatically** — updates are a deliberate
developer action so that spec changes don't break things silently.

```bash
# Check if the spec is outdated (safe, read-only)
python src/tooluniverse/data/specs/ncbi/scripts/sync_openapi_spec.py --check

# Download the latest spec from NCBI
python src/tooluniverse/data/specs/ncbi/scripts/sync_openapi_spec.py

# Regenerate configurations and validate
python src/tooluniverse/data/specs/ncbi/maintain_ncbi_tools.py

# Review changes, run tests, then commit
git diff
pytest tests/tools/test_ncbi_datasets_tool.py --override-ini="addopts=" -v
```

The `--check` flag can be used in CI to alert when the upstream spec has
changed without failing the build.

If tests pass after the update, the integration is ready to commit.

### 2. Adding New Endpoints

To integrate a new NCBI Datasets endpoint:

1. **Configure endpoint** in
   `scripts/discover_and_generate.py`:

   ```python
   {
       "type": "NCBIDatasetsNewTool",
       "name": "ncbi_datasets_new_tool",
       "endpoint": "/api/v2/new_endpoint/{param}",
       "description": "Detailed endpoint description",
       "flexible_params": ["param"],  # Parameters accepting single/array
   }
   ```

   Add URL mapping to `ENDPOINT_DOCS_MAPPING`:

   ```python
   "/api/v2/new_endpoint/{param}": "https://www.ncbi.nlm.nih.gov/...",
   ```

2. **Generate scaffolding**:

   ```bash
   python src/tooluniverse/data/specs/ncbi/scripts/discover_and_generate.py
   ```

   Output includes:
   - Updated JSON configuration
   - Test definitions (`TOOL_DEFINITIONS`)
   - Wrapper function template with minimal docstring

3. **Implement components**:
   - Copy `TOOL_DEFINITIONS` to `tests/tools/test_ncbi_datasets_tool.py`
   - Create tool class in `src/tooluniverse/ncbi_datasets_tool.py`
   - Save wrapper template to `src/tooluniverse/tools/`

4. **Validate**:

   ```bash
   python src/tooluniverse/data/specs/ncbi/maintain_ncbi_tools.py
   ```

## Scripts Reference

### maintain_ncbi_tools.py

Master orchestration script for all maintenance tasks.

**Purpose**: Single entry point for specification-driven updates

**Usage**:

```bash
python maintain_ncbi_tools.py [--all|--json|--validate]
```

**Options**:

- `--all`: Run all tasks (default)
- `--json`: Update JSON configurations only
- `--validate`: Run validation tests only

### scripts/update_ncbi_json_from_openapi.py

Updates JSON tool configurations from OpenAPI specification.

**Functionality**:

- Parses `openapi3.docs.yaml`
- Extracts endpoint parameters with types, descriptions, defaults
- Generates complete JSON configurations
- Handles flexible parameters (single value or array via `anyOf`)

**Output**: `src/tooluniverse/data/ncbi_datasets_tools.json`

**When to run**: After specification updates or parameter changes

### scripts/discover_and_generate.py

Comprehensive generator for new tool scaffolding.

**Functionality**:

- All functionality of `update_ncbi_json_from_openapi.py`
- Generates test definitions (`TOOL_DEFINITIONS`)
- Creates wrapper function templates with minimal docstrings

**Output**:

- Updated JSON configuration
- Formatted test definitions (stdout)
- Complete wrapper templates with docstrings (stdout)

**When to run**: When adding new endpoints

## Documentation Standards

### Docstring Methodology

**Problem**: Traditional docstrings duplicate parameter documentation,
creating maintenance burden and synchronization issues.

**Solution**: Minimal docstrings with external documentation links.

All generated wrapper functions use 6-line docstrings:

```python
def ncbi_datasets_example_tool(...) -> dict[str, Any]:
    """
    Brief one-line description of tool functionality.

    For complete parameter documentation, see:
    https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/#endpoint

    Returns
    -------
    dict[str, Any]
        Response with success status, data, and metadata
    """
```

**Benefits**:

- No parameter duplication across codebase
- Always current (links to official documentation)
- Minimal maintenance overhead
- Professional appearance

### Tool URL Mapping

| Tool | Official Documentation |
|------|------------------------|
| gene_by_id | https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/#get-/gene/id/-gene_ids- |
| gene_by_symbol | https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/#get-/gene/symbol/-symbols-/taxon/-taxon- |
| gene_by_accession | https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/#get-/gene/accession/-accessions- |
| genome_report | https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/#get-/genome/accession/-accessions-/dataset_report |
| taxonomy_metadata | https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/#get-/taxonomy/taxon/-taxons- |
| virus_genome_summary | https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/#get-/virus/taxon/-taxon-/genome |

## Implementation Details

### Flexible Parameter Handling

Path parameters that accept single values or arrays use `anyOf` schemas:

```json
"gene_ids": {
  "anyOf": [
    {"type": "integer"},
    {"type": "array", "items": {"type": "integer"}}
  ],
  "description": "One or more NCBI Gene IDs (e.g., 59067 or [59067, 50615])"
}
```

Supported by custom validation in `src/tooluniverse/utils.py`.

### Parameter Coverage Enforcement

All tools must achieve 100% OpenAPI parameter coverage, verified by:

```python
TOOL_DEFINITIONS = [
    {
        "name": "NCBIDatasetsGeneByIdTool",
        "endpoint": "/gene/id/{gene_ids}",
        "implemented_params": ["gene_ids", "page_size", "page_token"],
        "min_coverage": 100.0,
    },
    # ...
]
```

Tests in `tests/tools/test_ncbi_datasets_tool.py` validate against OpenAPI
specification using `OpenAPIValidator`.

## Testing

**100% Spec-Driven Test Suite** in `tests/tools/test_ncbi_datasets_tool.py`:

All test data is dynamically generated from the OpenAPI specification:

- Test cases extracted from spec examples
- Missing parameter tests generated from required params
- No hardcoded test values - pure spec-driven architecture

**Test Categories**:

- Tool registration and existence
- Single and multiple ID execution (from spec examples)
- Missing parameter handling (auto-generated from spec)
- Performance benchmarks
- Concurrent execution
- OpenAPI parameter coverage validation (100% of spec params implemented)

**Run tests**:

```bash
# All NCBI tests (30 tests total)
pytest tests/tools/test_ncbi_datasets_tool.py -v

# OpenAPI validation only
pytest tests/tools/test_ncbi_datasets_tool.py -k openapi -v
```

**Test Results**: 30 passed, 100% spec-driven

## Related Documentation

- **User Documentation**: `docs/tools/ncbi_datasets_tools.rst` - End-user
  tool documentation

## External Resources

- **NCBI Datasets API**: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/
- **OpenAPI Specification**: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/openapi3/openapi3.docs.yaml
- **API Keys**: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/api-keys/
- **Rate Limits**: 5 requests/second (default), 10 requests/second (with API
  key)

## Best Practices

1. **Always validate after updates**: Run full maintenance script after
   specification changes
2. **Review generated configurations**: Inspect diffs before applying updates
3. **Keep specification current**: Regularly check for NCBI API updates
4. **Maintain URL mappings**: Update `ENDPOINT_DOCS_MAPPING` when adding
   endpoints
5. **Preserve naming conventions**: Follow established PascalCase/snake_case
   patterns
6. **Link to official documentation**: Never duplicate parameter
   documentation

## Troubleshooting

### Tests Fail After Specification Update

1. Check specification syntax: `yamllint openapi3.docs.yaml`
2. Verify endpoint URLs are correct in tool configurations
3. Review parameter type changes in specification
4. Check flexible parameter configurations

### New Tool Not Generating Correctly

1. Verify endpoint exists in `openapi3.docs.yaml`
2. Confirm tool configuration in `discover_and_generate.py`
3. Check `ENDPOINT_DOCS_MAPPING` includes new endpoint
4. Ensure flexible parameters are correctly identified

### Parameter Coverage Below 100%

1. Compare implemented parameters with specification
2. Check for renamed parameters (e.g., `sort.field` → `sort_field`)
3. Verify `TOOL_DEFINITIONS` matches tool class implementation
4. Run `discover_and_generate.py` to see complete parameter list
