#!/usr/bin/env python3
"""
Auto-discovery and generation system for NCBI Datasets API endpoints.

This script:
1. Discovers all GET endpoints in the OpenAPI specification
2. Identifies which are already implemented (reads from JSON "endpoint" field)
3. Generates complete scaffolding for missing endpoints:
   - Tool classes (with generation markers)
   - JSON configurations (with endpoint field)
   - Wrapper functions
   - Test definitions (integrated with existing structure)
   - __init__.py updates (avoiding duplicates)

Usage:
    python discover_and_generate.py [--dry-run] [--filter CATEGORY] [--limit N]
"""

import os
import sys
import json
import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add scripts to path for openapi_validator
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "scripts"))
from openapi_validator import OpenAPIValidator  # noqa: E402


def resolve_schema_ref(ref: str, spec: dict):
    """Resolve a $ref to its schema definition in the OpenAPI spec.

    Args:
        ref: Reference string like '#/components/schemas/SchemaName'
        spec: Full OpenAPI specification dict

    Returns:
        Resolved schema dict or None if not found
    """
    if not ref or not ref.startswith("#/"):
        return None

    # Parse ref path (e.g., "#/components/schemas/SchemaName")
    parts = ref.lstrip("#/").split("/")

    # Navigate to the schema
    current = spec
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


class EndpointDiscovery:
    """Discovers and categorizes NCBI Datasets API endpoints."""

    def __init__(self, spec_path: str, json_config_path: str):
        self.spec_path = spec_path
        self.json_config_path = json_config_path
        with open(spec_path, 'r') as f:
            self.spec = yaml.safe_load(f)
        self.validator = OpenAPIValidator(spec_path)

    def discover_all_endpoints(self) -> List[Dict]:
        """Discover all GET endpoints from OpenAPI spec.

        Filters out endpoints that don't return application/json (e.g., images,
        ZIP downloads) as they don't fit the current JSON-based architecture.
        """
        endpoints = []

        for path, methods in self.spec['paths'].items():
            if 'get' not in methods:
                continue

            method_spec = methods['get']

            # Skip non-JSON endpoints (images, downloads, etc.)
            responses = method_spec.get('responses', {}).get('200', {})
            content_types = responses.get('content', {}).keys()
            if content_types and 'application/json' not in content_types:
                print(f"  ⊘ Skipping non-JSON endpoint: {path}")
                continue

            # Extract path parameters
            path_params = []
            if '{' in path:
                path_params = re.findall(r'\{([^}]+)\}', path)

            # Get all parameters
            param_details = self.validator.get_parameter_details(path)

            endpoint_info = {
                'path': path,
                'operation_id': method_spec.get('operationId', ''),
                'summary': method_spec.get('summary', ''),
                'description': method_spec.get('description', ''),
                'path_params': path_params,
                'all_params': list(param_details.keys()),
                'resource_type': path.split('/')[1] if path.startswith('/') else '',
            }

            endpoints.append(endpoint_info)

        return endpoints

    def load_implemented_endpoints(self) -> Set[str]:
        """Load list of currently implemented endpoints from JSON config."""
        if not os.path.exists(self.json_config_path):
            print(f"Warning: JSON config not found at {self.json_config_path}")
            return set()

        with open(self.json_config_path, 'r') as f:
            tools = json.load(f)

        # Extract endpoint paths from JSON "endpoint" field
        implemented = set()
        for tool in tools:
            endpoint = tool.get('endpoint')
            if endpoint:
                implemented.add(endpoint)
                print(f"  ✓ Already implemented: {endpoint}")

        return implemented

    def filter_unimplemented(self, endpoints: List[Dict]) -> List[Dict]:
        """Filter to only unimplemented endpoints."""
        implemented = self.load_implemented_endpoints()
        return [ep for ep in endpoints if ep['path'] not in implemented]

    def prioritize_endpoints(self, endpoints: List[Dict]) -> List[Dict]:
        """Prioritize endpoints by usefulness and simplicity."""
        def priority_score(ep):
            score = 0

            # Resource type priority
            resource_priority = {
                'gene': 10,
                'genome': 10,
                'virus': 10,
                'taxonomy': 10,
                'protein': 5,
                'organelle': 5,
                'biosample': 3,
            }
            score += resource_priority.get(ep['resource_type'], 0)

            # Penalize complex paths
            score -= len(ep['path_params']) * 2

            # Penalize many parameters
            score -= len(ep['all_params']) // 5

            # Prefer dataset_report endpoints
            if 'dataset_report' in ep['path']:
                score += 5

            # Avoid download endpoints (binary data)
            if 'download' in ep['path']:
                score -= 20

            return score

        return sorted(endpoints, key=priority_score, reverse=True)


class ToolGenerator:
    """Generates tool scaffolding from endpoint specifications."""

    # Path parameters that accept both single values and arrays
    FLEXIBLE_PARAMS = {
        "gene_ids": {
            "single_type": "integer",
            "description_example": "59067 for IL21, or [59067, 50615] for multiple genes"
        },
        "symbols": {
            "single_type": "string",
            "description_example": "'BRCA1', or ['BRCA1', 'BRCA2']"
        },
        "accessions": {
            "single_type": "string",
            "description_example": "'NM_021803.4' or ['NM_021803.4', 'NM_000546.6']"
        },
        "taxons": {
            "single_type": "string",
            "description_example": "'9606' for human, or ['9606', '10090'] for human and mouse"
        },
        "locus_tags": {
            "single_type": "string",
            "description_example": "'b0001' or ['b0001', 'b0002']"
        },
        "assembly_names": {
            "single_type": "string",
            "description_example": "'GRCh38' or ['GRCh38', 'GRCh37']"
        },
        "bioprojects": {
            "single_type": "string",
            "description_example": "'PRJNA489243' or ['PRJNA489243', 'PRJNA248792']"
        },
        "biosample_ids": {
            "single_type": "string",
            "description_example": "'SAMN02953835' or ['SAMN02953835', 'SAMN02953836']"
        },
        "proteins": {
            "single_type": "string",
            "description_example": "'NP_001234.1' or ['NP_001234.1', 'NP_001235.1']"
        },
        "tax_ids": {
            "single_type": "string",
            "description_example": "'9606' or ['9606', '10090']"
        },
        "wgs_accessions": {
            "single_type": "string",
            "description_example": "'AAAA01' or ['AAAA01', 'AAAB01']"
        },
    }

    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.validator = OpenAPIValidator(spec_path)
        # Load spec for $ref resolution
        with open(spec_path, 'r') as f:
            self.spec = yaml.safe_load(f)

    def generate_tool_name(self, endpoint: Dict) -> Dict[str, str]:
        """Generate tool class name and function name from endpoint."""
        parts = endpoint['path'].strip('/').split('/')

        # Remove path parameter placeholders
        clean_parts = []
        for part in parts:
            if '{' not in part:
                words = part.replace('_', ' ').replace('-', ' ').split()
                clean_parts.extend([w.capitalize() for w in words])

        # Build names
        class_name = "NCBIDatasets" + "".join(clean_parts) + "Tool"
        function_name = "ncbi_datasets_" + "_".join(
            p.lower().replace('-', '_') for p in clean_parts
        )

        return {
            'class_name': class_name,
            'function_name': function_name,
        }

    def generate_tool_class(self, endpoint: Dict) -> str:
        """Generate a tool class with generation marker in docstring."""
        names = self.generate_tool_name(endpoint)
        param_details = self.validator.get_parameter_details(endpoint['path'])

        # Separate path and query parameters
        path_params = endpoint['path_params']
        query_params = [p for p, details in param_details.items()
                        if details.get('in') == 'query']

        # Build parameter extraction code
        param_extractions = []
        for param in endpoint['all_params']:
            python_name = param.replace('.', '_').replace('-', '_')
            param_extractions.append(
                f'        {python_name} = arguments.get("{param}")'
            )

        # Build method parameters
        method_params = ['self'] + [f'{p}: str' for p in path_params]
        for param in query_params:
            python_name = param.replace('.', '_').replace('-', '_')
            method_params.append(f'{python_name}: Optional[str] = None')

        # Generate class code with marker
        class_code = f'''@register_tool("{names['class_name']}")
class {names['class_name']}(BaseTool):
    """
    {endpoint['summary']}
    
    Auto-generated by discover_and_generate.py
    Endpoint: {endpoint['path']}
    """

    def __init__(self, tool_config, base_url=NCBI_DATASETS_BASE_URL):
        super().__init__(tool_config)
        self.base_url = base_url
        self.api_key = os.getenv("NCBI_API_KEY") or tool_config.get("api_key")

    def run(self, arguments):
        """Execute the tool with given arguments."""
{chr(10).join(param_extractions)}
        
        try:
            result = self._fetch_data({", ".join(endpoint['path_params'] + [p.replace('.', '_').replace('-', '_') for p in query_params])})
            response = {{"success": True, "data": result}}
            # Add path parameters to response
            {''.join(chr(10) + '            response["' + p + '"] = ' + p for p in endpoint['path_params'])}
            return response
        except Exception as e:
            return {{"success": False, "error": str(e)}}
    
    def _fetch_data(
        self,
{",".join(chr(10) + "        " + p for p in method_params[1:])}
    ):
        """Fetch data from NCBI Datasets API."""
        # Convert flexible path parameters to comma-separated strings{''.join(chr(10) + '        if isinstance(' + p + ', (str, int)):' + chr(10) + '            ' + p + ' = [str(' + p + ')]' + chr(10) + '        else:' + chr(10) + '            ' + p + ' = [str(x) for x in ' + p + ']' + chr(10) + '        ' + p + ' = ",".join(' + p + ')' for p in path_params if p in self.FLEXIBLE_PARAMS)}
        
        # Build URL
        url = self.base_url + {'"' + endpoint['path'] + '"' + '.format(' + ', '.join([f'{p}={p}' for p in path_params]) + ')' if path_params else '"' + endpoint['path'] + '"'}
        
        # Build parameters
        params = {{}}
        if self.api_key:
            params["api_key"] = self.api_key
        {''.join(chr(10) + '        if ' + p.replace(".", "_").replace("-", "_") + ' is not None:' + chr(10) + '            params["' + p + '"] = ' + p.replace(".", "_").replace("-", "_") for p in query_params)}
        
        # Make request
        headers = {{"Accept": NCBI_DATASETS_ACCEPT_JSON}}
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
'''

        return class_code

    def generate_wrapper_function(self, endpoint: Dict) -> str:
        """Generate wrapper function."""
        names = self.generate_tool_name(endpoint)
        param_details = self.validator.get_parameter_details(endpoint['path'])

        # Build function parameters
        func_params = []
        for param in endpoint['all_params']:
            python_name = param.replace('.', '_').replace('-', '_')
            details = param_details.get(param, {})
            param_type = details.get('schema', {}).get('type', 'str')

            type_mapping = {
                'integer': 'int',
                'boolean': 'bool',
                'string': 'str',
                'array': 'List[str]',
            }
            py_type = type_mapping.get(param_type, 'str')

            if details.get('required'):
                func_params.append(f'{python_name}: {py_type}')
            else:
                func_params.append(
                    f'{python_name}: Optional[{py_type}] = None')

        docs_url = f"https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/#get-{endpoint['path'].replace('/', '-')}"

        wrapper_code = f'''"""
{names['function_name']}

{endpoint['description'][:200] if endpoint['description'] else endpoint['summary']}

Auto-generated by discover_and_generate.py
"""

from typing import Any, Optional, Callable, List
from ._shared_client import get_shared_client


def {names['function_name']}(
    {("," + chr(10) + "    ").join(func_params)},
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    {endpoint['summary']}

    For complete parameter documentation, see:
    {docs_url}

    Returns
    -------
    dict[str, Any]
        Response with success status, data, and metadata
    """
    return get_shared_client().run_one_function(
        {{
            "name": "{names['function_name']}",
            "arguments": {{
                {("," + chr(10) + "                ").join(f'"{p}": {p.replace(".", "_").replace("-", "_")}' for p in endpoint['all_params'])}
            }},
        }},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["{names['function_name']}"]
'''

        return wrapper_code

    def generate_json_config(self, endpoint: Dict) -> Dict:
        """Generate JSON configuration with endpoint field and $ref resolution."""
        names = self.generate_tool_name(endpoint)
        param_details = self.validator.get_parameter_details(endpoint['path'])

        # Build parameter properties
        properties = {}
        required_params = []

        for param, details in param_details.items():
            schema = details.get('schema', {})
            python_name = param.replace('.', '_').replace('-', '_')
            description = details.get('description', f'Parameter: {param}')

            # Resolve $ref at schema level if present
            if "$ref" in schema:
                ref = schema["$ref"]
                resolved = resolve_schema_ref(ref, self.spec)
                if resolved:
                    schema = resolved.copy()

            param_def = {}

            # Handle flexible path parameters (single value or array)
            if param in self.FLEXIBLE_PARAMS and param in endpoint['path_params']:
                flex_config = self.FLEXIBLE_PARAMS[param]
                # Extract first word of description, or use param name as fallback
                desc_word = description.split()[0].lower(
                ) if description and description.split() else param.replace('_', ' ')
                param_def = {
                    "description": f"One or more {desc_word} (e.g., {flex_config['description_example']})",
                    "anyOf": [
                        {"type": flex_config["single_type"]},
                        {
                            "type": "array",
                            "items": {"type": flex_config["single_type"]}
                        }
                    ]
                }
            else:
                # Standard parameter handling
                param_def = {"description": description}

                # Add type information
                if 'type' in schema:
                    param_def['type'] = schema['type']
                if 'items' in schema:
                    param_def['type'] = 'array'
                    # Resolve $ref in items if present
                    items = schema['items']
                    if "$ref" in items:
                        ref = items["$ref"]
                        resolved = resolve_schema_ref(ref, self.spec)
                        if resolved:
                            param_def['items'] = resolved.copy()
                        else:
                            param_def['items'] = items
                    else:
                        param_def['items'] = items
                if 'default' in schema:
                    param_def['default'] = schema['default']
                if 'enum' in schema:
                    param_def['enum'] = schema['enum']

            properties[python_name] = param_def

            if details.get('required'):
                required_params.append(python_name)

        return {
            'type': names['class_name'],
            'name': names['function_name'],
            # CRITICAL: Store endpoint for detection
            'endpoint': endpoint['path'],
            'description': endpoint['summary'] or (endpoint['description'][:200] if endpoint['description'] else ''),
            'parameter': {
                'type': 'object',
                'properties': properties,
                'required': sorted(required_params)
            },
            'return_schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'description': 'Whether the request was successful'},
                    'data': {'type': 'object', 'description': 'Data from NCBI Datasets API'},
                    'error': {'type': 'string', 'description': 'Error message if request failed'}
                }
            }
        }


def update_init_file(tool_classes: List[Dict], init_file: Path) -> bool:
    """Update __init__.py with proper import integration (avoiding duplicates).

    This function modifies existing import blocks rather than inserting new lines.
    It handles multi-line import statements properly.
    """
    if not init_file.exists():
        print(f"❌ __init__.py not found at {init_file}")
        return False

    with open(init_file, 'r') as f:
        lines = f.readlines()

    # Collect tool names to add (skip if already present)
    tools_to_add = []
    file_content = ''.join(lines)

    for tc in tool_classes:
        class_name = tc['name']
        # Check if already present anywhere in file
        if class_name not in file_content:
            tools_to_add.append(class_name)
            print(f"  → Will add: {class_name}")
        else:
            print(f"  ✓ Already present: {class_name}")

    if not tools_to_add:
        print("  ℹ️  No new tools to add")
        return True

    # 1. Update type annotation section (# Only import tool classes...)
    type_section_start = -1
    last_ncbi_type = -1
    for i, line in enumerate(lines):
        if "# Only import tool classes if lazy loading is disabled" in line:
            type_section_start = i
        if type_section_start >= 0 and "NCBIDatasetsVirusGenomeSummaryTool: Any" in line:
            last_ncbi_type = i
            break

    if last_ncbi_type >= 0:
        insert_idx = last_ncbi_type + 1
        for tool in tools_to_add:
            lines.insert(insert_idx, f'{tool}: Any\n')
            insert_idx += 1
        print(f"  ✅ Updated type annotations after line {last_ncbi_type}")
    else:
        print("  ⚠️  Could not find type annotation section")

    # 2. Update multi-line import block: from .ncbi_datasets_tool import (...)
    import_start = -1
    import_end = -1
    for i, line in enumerate(lines):
        if "from .ncbi_datasets_tool import (" in line:
            import_start = i
        if import_start >= 0 and import_end < 0 and ")" in line:
            import_end = i
            break

    if import_start >= 0 and import_end >= 0:
        # Find last non-closing-paren line in block
        insert_idx = import_end
        for i in range(import_end - 1, import_start, -1):
            if lines[i].strip() and lines[i].strip() != ")":
                insert_idx = i + 1
                break

        # Add new imports
        for tool in tools_to_add:
            lines.insert(insert_idx, f"    {tool},\n")
            insert_idx += 1
        print(f"  ✅ Updated import block at lines {import_start}-{import_end}")
    else:
        print("  ⚠️  Could not find import block")

    # 3. Update lazy imports section (handle multi-line statements)
    lazy_section_start = -1
    last_ncbi_lazy_end = -1
    in_ncbi_lazy = False

    for i, line in enumerate(lines):
        if "# Lazy imports" in line or "_LazyImportProxy" in line:
            if lazy_section_start < 0:
                lazy_section_start = i

        # Detect start of NCBI lazy import
        if "NCBIDatasets" in line and "=" in line and "_LazyImportProxy" in line:
            in_ncbi_lazy = True
            last_ncbi_lazy_end = i
        # Continue tracking if we're in a multi-line NCBI lazy import
        elif in_ncbi_lazy and line.strip() and not line.strip().startswith("#"):
            # Still in the same statement if line starts with whitespace
            # and doesn't start a new assignment
            if line.strip().startswith(")") or (line.startswith("        ") and "=" not in line):
                last_ncbi_lazy_end = i
            else:
                in_ncbi_lazy = False

    if last_ncbi_lazy_end >= 0:
        # Insert after the complete multi-line statement
        insert_idx = last_ncbi_lazy_end + 1
        for tool in tools_to_add:
            # Add proper indentation (4 spaces to match other lazy imports)
            lines.insert(
                insert_idx, f'    {tool} = _LazyImportProxy("ncbi_datasets_tool", "{tool}")\n')
            insert_idx += 1
        print(f"  ✅ Updated lazy imports after line {last_ncbi_lazy_end}")
    else:
        print("  ⚠️  Could not find lazy import section")

    # 4. Update __all__ export list
    all_start = -1
    last_ncbi_export = -1
    for i, line in enumerate(lines):
        if "__all__ = [" in line:
            all_start = i
        if all_start >= 0 and '"NCBIDatasets' in line:
            last_ncbi_export = i

    if last_ncbi_export >= 0:
        insert_idx = last_ncbi_export + 1
        for tool in tools_to_add:
            lines.insert(insert_idx, f'    "{tool}",\n')
            insert_idx += 1
        print(f"  ✅ Updated __all__ at line {last_ncbi_export}")
    else:
        print("  ⚠️  Could not find __all__ section")

    # Write back
    with open(init_file, 'w') as f:
        f.writelines(lines)

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-discover and generate NCBI tools")
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be generated')
    parser.add_argument(
        '--filter', help='Filter by resource type (gene, genome, etc.)')
    parser.add_argument('--limit', type=int,
                        help='Limit number of tools to generate')

    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent
    spec_path = script_dir.parent / "openapi3.docs.yaml"
    json_path = script_dir.parent.parent.parent.parent / \
        "data" / "ncbi_datasets_tools.json"

    print("=" * 80)
    print("NCBI Datasets API - Auto-Discovery and Generation (v2.0)")
    print("=" * 80)

    # Discover endpoints
    discovery = EndpointDiscovery(str(spec_path), str(json_path))
    all_endpoints = discovery.discover_all_endpoints()
    unimplemented = discovery.filter_unimplemented(all_endpoints)
    prioritized = discovery.prioritize_endpoints(unimplemented)

    # Filter by resource type if specified
    if args.filter:
        prioritized = [
            ep for ep in prioritized if ep['resource_type'] == args.filter]

    # Limit if specified
    if args.limit:
        prioritized = prioritized[:args.limit]

    print(f"\nTotal endpoints: {len(all_endpoints)}")
    print(f"Already implemented: {len(all_endpoints) - len(unimplemented)}")
    print(f"Remaining: {len(unimplemented)}")
    print(f"To generate: {len(prioritized)}")

    if args.dry_run:
        print("\nDRY RUN - Showing what would be generated:\n")
        generator = ToolGenerator(str(spec_path))

        for i, ep in enumerate(prioritized[:10], 1):
            names = generator.generate_tool_name(ep)
            print(f"{i}. {ep['path']}")
            print(f"   Class: {names['class_name']}")
            print(f"   Function: {names['function_name']}")
            print(f"   Parameters: {len(ep['all_params'])}")
            print()

        if len(prioritized) > 10:
            print(f"... and {len(prioritized) - 10} more")
    else:
        if len(prioritized) == 0:
            print("\n✅ All endpoints already implemented!")
            return

        print("\nGenerating tool scaffolding...")
        generator = ToolGenerator(str(spec_path))

        # Collect all generated content
        tool_classes = []
        wrapper_files = []
        json_configs = []

        for ep in prioritized:
            names = generator.generate_tool_name(ep)

            tool_classes.append({
                'name': names['class_name'],
                'code': generator.generate_tool_class(ep),
                'endpoint': ep['path']
            })

            wrapper_files.append({
                'filename': f"{names['function_name']}.py",
                'code': generator.generate_wrapper_function(ep)
            })

            json_configs.append(generator.generate_json_config(ep))

        # Summary
        print(f"\n{'='*80}")
        print("GENERATION SUMMARY")
        print('='*80)
        print(f"\nGenerated {len(prioritized)} new tools:")
        print(f"  - {len(tool_classes)} tool classes (with generation markers)")
        print(f"  - {len(wrapper_files)} wrapper functions")
        print(
            f"  - {len(json_configs)} JSON configurations (with endpoint field)")

        # Write files
        print(f"\n{'='*80}")
        print("WRITING FILES")
        print('='*80)

        # 1. Append tool classes
        tool_file = script_dir.parent.parent.parent.parent / "ncbi_datasets_tool.py"
        if tool_file.exists():
            with open(tool_file, 'a') as f:
                f.write("\n\n# " + "="*76 + "\n")
                f.write(
                    "# AUTO-GENERATED TOOLS - Generated by discover_and_generate.py\n")
                f.write("# " + "="*76 + "\n\n")
                for tc in tool_classes:
                    f.write(tc['code'])
                    f.write("\n\n")
            print(
                f"✅ Appended {len(tool_classes)} tool classes to ncbi_datasets_tool.py")

        # 2. Create wrapper files
        tools_dir = script_dir.parent.parent.parent.parent / "tools"
        for wf in wrapper_files:
            file_path = tools_dir / wf['filename']
            with open(file_path, 'w') as f:
                f.write(wf['code'])
            print(f"✅ Created {wf['filename']}")

        # 3. Append to JSON config
        if json_path.exists():
            with open(json_path, 'r') as f:
                existing_json = json.load(f)

            existing_json.extend(json_configs)

            with open(json_path, 'w') as f:
                json.dump(existing_json, f, indent=2)
            print(
                f"✅ Added {len(json_configs)} configurations to ncbi_datasets_tools.json")

        # 4. Update __init__.py
        init_file = script_dir.parent.parent.parent.parent / "__init__.py"
        if update_init_file(tool_classes, init_file):
            print(f"✅ Updated __init__.py with {len(tool_classes)} imports")

        # 5. Test file auto-generates from OpenAPI spec - no update needed!
        print(f"✅ Tests will auto-generate from OpenAPI spec examples")

        print(f"\n{'='*80}")
        print("✅ Generation complete!")
        print('='*80)
        print(f"\nGenerated tools are FULLY INTEGRATED:")
        print(f"  ✅ Tool classes with generation markers")
        print(f"  ✅ Wrapper functions created")
        print(f"  ✅ JSON configurations with endpoint field")
        print(f"  ✅ __init__.py imports (no duplicates)")
        print(f"  ✅ Tests auto-generate from OpenAPI spec")
        print(f"\nNext steps:")
        print(f"1. Run: pytest tests/tools/test_ncbi_datasets_tool.py -v")
        print(f"2. Tests will use examples from OpenAPI spec automatically!")
        print('='*80)


if __name__ == "__main__":
    main()
