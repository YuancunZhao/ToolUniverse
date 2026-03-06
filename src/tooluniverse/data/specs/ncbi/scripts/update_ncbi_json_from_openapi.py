#!/usr/bin/env python3
"""
Update NCBI Datasets JSON configurations from OpenAPI spec.

This script reads existing tool configurations and updates them with the latest
parameters from the OpenAPI specification. Uses the "endpoint" field from JSON
to determine which spec endpoint to use (NO HARDCODING).

When the OpenAPI spec is updated:
1. Download the new openapi3.docs.yaml from NCBI
2. Replace src/tooluniverse/data/specs/ncbi/openapi3.docs.yaml
3. Run this script to update existing tools with new parameters
4. Review changes and commit

Usage:
    python scripts/update_ncbi_json_from_openapi.py [--dry-run]
"""

import sys
import os
import json
import argparse
import yaml
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser(
        description="Update NCBI tool JSON configs from OpenAPI spec")
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be updated without writing')
    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent
    spec_path = script_dir.parent / "openapi3.docs.yaml"
    json_path = script_dir.parent.parent.parent.parent / \
        "data" / "ncbi_datasets_tools.json"

    if not spec_path.exists():
        print(f"❌ OpenAPI spec not found: {spec_path}")
        sys.exit(1)

    if not json_path.exists():
        print(f"❌ JSON config not found: {json_path}")
        sys.exit(1)

    # Load validator, spec, and JSON config
    validator = OpenAPIValidator(str(spec_path))

    with open(spec_path, "r") as f:
        openapi_spec = yaml.safe_load(f)

    with open(json_path, "r") as f:
        config = json.load(f)

    print("=" * 80)
    print("NCBI Datasets - Update JSON from OpenAPI Spec")
    print("=" * 80)
    print(f"\nOpenAPI spec: {spec_path}")
    print(f"JSON config: {json_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE UPDATE'}")

    # Path parameter names that should accept both single values and arrays
    flexible_params = {
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

    updates_made = 0
    tools_processed = 0

    # Update each tool configuration
    for tool in config:
        tool_type = tool.get("type")
        _tool_name = tool.get("name")
        endpoint = tool.get("endpoint")  # ← Read from JSON (no hardcoding!)

        if not endpoint:
            print(f"\n⚠️  Skipping {tool_type}: No 'endpoint' field in JSON")
            continue

        tools_processed += 1

        print(f"\n{'='*80}")
        print(f"Processing: {tool_type}")
        print(f"Endpoint: {endpoint}")

        # Get all parameters from OpenAPI spec
        try:
            param_details = validator.get_parameter_details(endpoint)
        except Exception as e:
            print(f"  ❌ Error getting parameters: {e}")
            continue

        # Current configuration
        current_props = tool["parameter"]["properties"]
        required_params = tool["parameter"].get("required", [])
        new_props = {}

        # Add all parameters from spec
        params_added = 0
        params_updated = 0

        for param_name, param_info in param_details.items():
            schema = param_info["schema"]
            description = param_info["description"] or f"Parameter: {param_name}"

            # Resolve $ref at schema level if present
            if "$ref" in schema:
                ref = schema["$ref"]
                resolved = resolve_schema_ref(ref, openapi_spec)
                if resolved:
                    schema = resolved.copy()

            # Handle parameter name mapping (e.g., sort.field -> sort_field)
            json_param_name = param_name.replace(".", "_").replace("-", "_")

            # Check if this is a flexible parameter (path parameter in URL)
            if param_name in flexible_params and param_info.get("in") == "path":
                flex_config = flexible_params[param_name]
                # Extract first word of description, or use param name as fallback
                desc_word = description.split()[0].lower(
                ) if description and description.split() else param_name.replace('_', ' ')
                # Create anyOf schema for flexible single/array input
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
                # Build standard parameter definition
                param_def = {"description": description}

                # Add type information
                if "type" in schema:
                    param_def["type"] = schema["type"]
                if "items" in schema:
                    param_def["type"] = "array"
                    # Resolve $ref in items if present
                    items = schema["items"]
                    if "$ref" in items:
                        ref = items["$ref"]
                        resolved = resolve_schema_ref(ref, openapi_spec)
                        if resolved:
                            # Use resolved schema (without $ref)
                            param_def["items"] = resolved.copy()
                        else:
                            # Fallback to original if resolution fails
                            param_def["items"] = items
                    else:
                        param_def["items"] = items
                if "default" in schema:
                    param_def["default"] = schema["default"]
                if "enum" in schema:
                    param_def["enum"] = schema["enum"]

            # Track if this is new or updated
            if json_param_name not in current_props:
                params_added += 1
                print(f"  + Adding parameter: {json_param_name}")
            elif current_props[json_param_name] != param_def:
                params_updated += 1
                print(f"  ↻ Updating parameter: {json_param_name}")

            new_props[json_param_name] = param_def

            # Track required params
            if param_info["required"] and json_param_name not in required_params:
                required_params.append(json_param_name)

        # Update tool configuration
        if params_added > 0 or params_updated > 0:
            tool["parameter"]["properties"] = new_props
            tool["parameter"]["required"] = sorted(required_params)
            updates_made += 1

            print(f"  ✅ Total: {len(new_props)} parameters "
                  f"({params_added} added, {params_updated} updated, "
                  f"{len(required_params)} required)")
        else:
            print(
                f"  ✓ No changes needed ({len(current_props)} parameters up to date)")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print('='*80)
    print(f"Tools processed: {tools_processed}")
    print(f"Tools updated: {updates_made}")
    print(f"Tools unchanged: {tools_processed - updates_made}")

    # Write updated configuration (unless dry-run)
    if args.dry_run:
        print(f"\n{'='*80}")
        print("DRY RUN - No files were modified")
        print('='*80)
    else:
        with open(json_path, "w") as f:
            json.dump(config, f, indent=2)

        print(f"\n{'='*80}")
        print(f"✅ Updated configuration written to: {json_path}")
        print('='*80)
        print("\nNext steps:")
        print("1. Review changes with: git diff")
        print("2. Run tests: pytest tests/tools/test_ncbi_datasets_tool.py -v")
        print("3. Commit if all looks good")


if __name__ == "__main__":
    main()
