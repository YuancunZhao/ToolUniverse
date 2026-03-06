"""
OpenAPI Specification Parser and Validator for NCBI Datasets API.

This module provides utilities to:
1. Parse the NCBI Datasets OpenAPI specification
2. Validate tool implementations against the spec
3. Generate tool configurations from the spec
4. Extract endpoint parameters and schemas
"""

import os
import yaml
from typing import Dict, List, Optional, Any


class OpenAPIValidator:
    """
    Validates and parses OpenAPI specifications for API integrations.
    """

    def __init__(self, spec_path: str):
        """
        Initialize the validator with an OpenAPI spec file.

        Parameters
        ----------
        spec_path : str
            Path to the OpenAPI YAML specification file
        """
        self.spec_path = spec_path
        self.spec = self._load_spec()

    def _load_spec(self) -> Dict[str, Any]:
        """
        Load and parse the OpenAPI YAML specification.

        Returns
        -------
        Dict[str, Any]
            Parsed OpenAPI specification
        """
        if not os.path.exists(self.spec_path):
            raise FileNotFoundError(
                f"OpenAPI spec not found at: {self.spec_path}")

        with open(self.spec_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_endpoint(self, path: str, method: str = "get") -> Optional[Dict]:
        """
        Get endpoint definition from the OpenAPI spec.

        Parameters
        ----------
        path : str
            The API endpoint path (e.g., '/virus/taxon/{taxon}/genome')
        method : str, optional
            HTTP method (default: 'get')

        Returns
        -------
        Optional[Dict]
            Endpoint definition or None if not found
        """
        paths = self.spec.get("paths", {})
        endpoint = paths.get(path, {})
        return endpoint.get(method.lower())

    def get_endpoint_parameters(self, path: str, method: str = "get") -> List[Dict]:
        """
        Extract all parameters for an endpoint.

        Parameters
        ----------
        path : str
            The API endpoint path
        method : str, optional
            HTTP method (default: 'get')

        Returns
        -------
        List[Dict]
            List of parameter definitions
        """
        endpoint = self.get_endpoint(path, method)
        if not endpoint:
            return []

        return endpoint.get("parameters", [])

    def get_parameter_details(self, path: str, method: str = "get") -> Dict[str, Dict]:
        """
        Get detailed parameter information for an endpoint.

        Parameters
        ----------
        path : str
            The API endpoint path
        method : str, optional
            HTTP method (default: 'get')

        Returns
        -------
        Dict[str, Dict]
            Dictionary mapping parameter names to their detailed config
        """
        parameters = self.get_endpoint_parameters(path, method)
        result = {}

        for param in parameters:
            param_name = param.get("name")
            if not param_name:
                continue

            result[param_name] = {
                "name": param_name,
                "description": param.get("description", ""),
                "in": param.get("in", "query"),
                "required": param.get("required", False),
                "schema": param.get("schema", {}),
                "examples": param.get("examples", {}),
            }

        return result

    def validate_tool_parameters(
        self, path: str, tool_params: List[str], method: str = "get"
    ) -> Dict[str, Any]:
        """
        Validate that a tool implementation includes all API parameters.

        Parameters
        ----------
        path : str
            The API endpoint path
        tool_params : List[str]
            List of parameter names implemented in the tool
        method : str, optional
            HTTP method (default: 'get')

        Returns
        -------
        Dict[str, Any]
            Validation results with missing and extra parameters
        """
        spec_params = self.get_parameter_details(path, method)
        spec_param_names = set(spec_params.keys())
        tool_param_names = set(tool_params)

        missing = spec_param_names - tool_param_names
        extra = tool_param_names - spec_param_names

        # Separate required and optional missing parameters
        missing_required = {
            p for p in missing if spec_params[p].get("required", False)}
        missing_optional = missing - missing_required

        return {
            "valid": len(missing_required) == 0,
            "missing_required": list(missing_required),
            "missing_optional": list(missing_optional),
            "extra": list(extra),
            "total_spec_params": len(spec_param_names),
            "total_tool_params": len(tool_param_names),
            "coverage_percent": (
                len(tool_param_names & spec_param_names) /
                len(spec_param_names) * 100
                if spec_param_names
                else 100.0
            ),
        }

    def generate_parameter_schema(
        self, path: str, method: str = "get"
    ) -> Dict[str, Any]:
        """
        Generate a JSON schema for endpoint parameters.

        Parameters
        ----------
        path : str
            The API endpoint path
        method : str, optional
            HTTP method (default: 'get')

        Returns
        -------
        Dict[str, Any]
            JSON schema for the parameters
        """
        param_details = self.get_parameter_details(path, method)
        properties = {}
        required = []

        for param_name, param_info in param_details.items():
            schema = param_info.get("schema", {})
            properties[param_name] = {
                "type": schema.get("type", "string"),
                "description": param_info.get("description", ""),
            }

            # Add additional schema properties
            if "default" in schema:
                properties[param_name]["default"] = schema["default"]
            if "enum" in schema:
                properties[param_name]["enum"] = schema["enum"]
            if "format" in schema:
                properties[param_name]["format"] = schema["format"]
            if "items" in schema:
                properties[param_name]["items"] = schema["items"]

            # Track required parameters
            if param_info.get("required", False):
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def list_all_endpoints(self) -> List[Dict[str, str]]:
        """
        List all endpoints in the OpenAPI spec.

        Returns
        -------
        List[Dict[str, str]]
            List of endpoints with path, method, and summary
        """
        paths = self.spec.get("paths", {})
        endpoints = []

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    endpoints.append(
                        {
                            "path": path,
                            "method": method.upper(),
                            "summary": details.get("summary", ""),
                            "operationId": details.get("operationId", ""),
                        }
                    )

        return endpoints

    def get_endpoint_examples(
        self, path: str, method: str = "get"
    ) -> Dict[str, List[Dict]]:
        """
        Extract examples for endpoint parameters.

        Parameters
        ----------
        path : str
            The API endpoint path
        method : str, optional
            HTTP method (default: 'get')

        Returns
        -------
        Dict[str, List[Dict]]
            Dictionary mapping parameter names to their examples
        """
        parameters = self.get_endpoint_parameters(path, method)
        examples = {}

        for param in parameters:
            param_name = param.get("name")
            param_examples = param.get("examples", {})

            if param_examples:
                examples[param_name] = [
                    {
                        "value": ex.get("value"),
                        "summary": ex.get("summary", ""),
                    }
                    for ex in param_examples.values()
                ]

        return examples


# Convenience function for NCBI Datasets API
def get_ncbi_datasets_validator() -> OpenAPIValidator:
    """
    Get an OpenAPIValidator instance for the NCBI Datasets API.

    Returns
    -------
    OpenAPIValidator
        Configured validator for NCBI Datasets API
    """
    spec_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "specs",
        "ncbi",
        "openapi3.docs.yaml",
    )
    return OpenAPIValidator(spec_path)


__all__ = ["OpenAPIValidator", "get_ncbi_datasets_validator"]
