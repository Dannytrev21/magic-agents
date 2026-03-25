"""Spec JSON Schema Validation (Feature 22: Spec JSON Schema Validation).

This module validates compiled verification specs against a JSON schema to ensure
they conform to the expected structure before being written and consumed downstream.
"""

import json
import os
from pathlib import Path

import jsonschema
import yaml


def _load_schema() -> dict:
    """Load the spec JSON schema from spec_schema.json."""
    schema_path = Path(__file__).parent / "spec_schema.json"
    with open(schema_path, "r") as f:
        return json.load(f)


def validate_spec(spec: dict) -> tuple[bool, list[str]]:
    """Validate a spec dict against the JSON schema.

    Args:
        spec: The spec dictionary to validate

    Returns:
        tuple[bool, list[str]]: (is_valid, list of error messages)
            - is_valid: True if spec passes validation
            - errors: List of validation error messages (empty if valid)
    """
    schema = _load_schema()
    errors = []

    try:
        jsonschema.validate(instance=spec, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        # Build detailed error message showing path to the problem
        path_str = " → ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        error_msg = f"At {path_str}: {e.message}"
        errors.append(error_msg)
        return False, errors
    except jsonschema.SchemaError as e:
        errors.append(f"Schema error: {e.message}")
        return False, errors


def validate_spec_file(path: str) -> tuple[bool, list[str]]:
    """Load a YAML spec file and validate it against the schema.

    Args:
        path: Path to the YAML spec file

    Returns:
        tuple[bool, list[str]]: (is_valid, list of error messages)
    """
    try:
        with open(path, "r") as f:
            spec = yaml.safe_load(f)
    except FileNotFoundError:
        return False, [f"File not found: {path}"]
    except yaml.YAMLError as e:
        return False, [f"YAML parse error: {str(e)}"]

    if spec is None:
        return False, ["Spec file is empty"]

    return validate_spec(spec)
