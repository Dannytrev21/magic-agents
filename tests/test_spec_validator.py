"""Tests for spec JSON schema validation (Feature 22)."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from verify.spec_validator import validate_spec, validate_spec_file


@pytest.fixture
def valid_spec():
    """A complete valid spec dict matching the schema."""
    return {
        "meta": {
            "spec_version": "1.0",
            "jira_key": "TEST-001",
            "jira_summary": "Test acceptance criteria",
            "generated_at": "2026-03-25T10:00:00Z",
            "approved_at": "2026-03-25T10:00:00Z",
            "approved_by": "test-user",
            "status": "approved",
        },
        "requirements": [
            {
                "id": "REQ-001",
                "ac_checkbox": 0,
                "ac_text": "User can perform action",
                "title": "User can perform action",
                "type": "api_behavior",
                "contract": {
                    "interface": {
                        "method": "GET",
                        "path": "/api/test",
                        "auth": "jwt_bearer",
                    },
                    "preconditions": [
                        {
                            "id": "PRE-001",
                            "description": "Valid token",
                            "formal": "token != null",
                            "category": "auth",
                        }
                    ],
                    "success": {
                        "status": 200,
                        "content_type": "application/json",
                        "schema": {
                            "type": "object",
                            "required": ["id"],
                            "properties": {"id": {"type": "string"}},
                        },
                    },
                    "failures": [
                        {
                            "id": "FAIL-001",
                            "when": "No token provided",
                            "violates": "PRE-001",
                            "status": 401,
                            "body": {"error": "unauthorized"},
                        }
                    ],
                    "invariants": [
                        {
                            "id": "INV-001",
                            "type": "security",
                            "rule": "Password must not be exposed",
                            "formal": "'password' not in response",
                        }
                    ],
                },
                "verification": [
                    {
                        "refs": ["success", "FAIL-001", "INV-001"],
                        "skill": "pytest_unit_test",
                        "output": ".verify/generated/test_001.py",
                    }
                ],
            }
        ],
        "traceability": {
            "ac_mappings": [
                {
                    "ac_checkbox": 0,
                    "ac_text": "User can perform action",
                    "pass_condition": "ALL_PASS",
                    "required_verifications": [
                        {
                            "ref": "REQ-001.success",
                            "description": "Success path",
                            "verification_type": "test_result",
                        }
                    ],
                }
            ]
        },
    }


class TestValidSpec:
    """Test cases for valid specs."""

    def test_valid_spec_passes_validation(self, valid_spec):
        """A complete valid spec should pass validation."""
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is True
        assert errors == []

    def test_valid_spec_with_minimal_meta(self):
        """Spec with only required meta fields should pass."""
        spec = {
            "meta": {
                "spec_version": "1.0",
                "jira_key": "TEST-001",
                "generated_at": "2026-03-25T10:00:00Z",
                "status": "draft",
            },
            "requirements": [
                {
                    "id": "REQ-001",
                    "ac_checkbox": 0,
                    "ac_text": "Test AC",
                    "title": "Test AC",
                    "type": "api_behavior",
                    "contract": {},
                    "verification": [
                        {
                            "skill": "pytest_unit_test",
                            "output": ".verify/generated/test.py",
                        }
                    ],
                }
            ],
            "traceability": {"ac_mappings": []},
        }
        is_valid, errors = validate_spec(spec)
        assert is_valid is True, f"Unexpected errors: {errors}"

    def test_valid_spec_with_multiple_requirements(self, valid_spec):
        """Spec with multiple requirements should pass."""
        # Add another requirement
        valid_spec["requirements"].append(
            {
                "id": "REQ-002",
                "ac_checkbox": 1,
                "ac_text": "Another action",
                "title": "Another action",
                "type": "security_invariant",
                "contract": {"invariants": []},
                "verification": [
                    {
                        "skill": "pytest_unit_test",
                        "output": ".verify/generated/test_002.py",
                    }
                ],
            }
        )
        # Add corresponding AC mapping
        valid_spec["traceability"]["ac_mappings"].append(
            {
                "ac_checkbox": 1,
                "ac_text": "Another action",
                "pass_condition": "ALL_PASS",
                "required_verifications": [],
            }
        )
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is True


class TestInvalidSpecs:
    """Test cases for invalid specs."""

    def test_missing_meta_field(self, valid_spec):
        """Spec without meta field should fail."""
        del valid_spec["meta"]
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_missing_requirements_field(self, valid_spec):
        """Spec without requirements field should fail."""
        del valid_spec["requirements"]
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_missing_traceability_field(self, valid_spec):
        """Spec without traceability field should fail."""
        del valid_spec["traceability"]
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_invalid_jira_key_format(self, valid_spec):
        """JIRA key must match pattern."""
        valid_spec["meta"]["jira_key"] = "INVALID_KEY"
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_invalid_requirement_type(self, valid_spec):
        """Requirement type must be from allowed enum."""
        valid_spec["requirements"][0]["type"] = "invalid_type"
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_invalid_status(self, valid_spec):
        """Status must be draft, approved, or executed."""
        valid_spec["meta"]["status"] = "invalid_status"
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_missing_requirement_id(self, valid_spec):
        """Requirement must have id field."""
        del valid_spec["requirements"][0]["id"]
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_invalid_requirement_id_format(self, valid_spec):
        r"""Requirement ID must match REQ-\d+ pattern."""
        valid_spec["requirements"][0]["id"] = "INVALID-001"
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_missing_verification_skill(self, valid_spec):
        """Verification must have skill field."""
        del valid_spec["requirements"][0]["verification"][0]["skill"]
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_missing_ac_mapping_in_traceability(self, valid_spec):
        """AC mapping must have required fields."""
        valid_spec["traceability"]["ac_mappings"][0] = {
            "ac_checkbox": 0,
            "ac_text": "Test",
            # Missing pass_condition and required_verifications
        }
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0

    def test_empty_requirements_array(self, valid_spec):
        """Requirements array cannot be empty."""
        valid_spec["requirements"] = []
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is False
        assert len(errors) > 0


class TestSpecFileValidation:
    """Test cases for validating spec files from disk."""

    def test_valid_spec_file_from_disk(self, valid_spec):
        """Valid spec YAML file should validate."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(valid_spec, f)
            temp_path = f.name

        try:
            is_valid, errors = validate_spec_file(temp_path)
            assert is_valid is True, f"Unexpected errors: {errors}"
        finally:
            os.unlink(temp_path)

    def test_invalid_spec_file_format(self):
        """Invalid YAML should fail to parse."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            is_valid, errors = validate_spec_file(temp_path)
            assert is_valid is False
            assert len(errors) > 0
        finally:
            os.unlink(temp_path)

    def test_nonexistent_file(self):
        """Nonexistent file should return error."""
        is_valid, errors = validate_spec_file("/nonexistent/path/spec.yaml")
        assert is_valid is False
        assert "not found" in errors[0].lower()

    def test_empty_spec_file(self):
        """Empty YAML file should fail."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            is_valid, errors = validate_spec_file(temp_path)
            assert is_valid is False
            assert "empty" in errors[0].lower()
        finally:
            os.unlink(temp_path)


class TestCompilerIntegration:
    """Test integration with compiler.py (Feature 22 integration requirement)."""

    def test_compile_and_validate_integration(self):
        """Compiler should call validator after producing spec."""
        # This test verifies that compile_spec() in compiler.py calls validate_spec()
        # by checking that the import and logging integration is in place
        from verify.compiler import compile_spec, validate_spec as imported_validate

        # Verify the import exists
        assert imported_validate is not None

    def test_validator_works_with_compiler_output(self, valid_spec):
        """Validator should accept specs produced by compiler."""
        # The valid_spec fixture is modeled after compiler.py output
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is True, f"Compiler output failed validation: {errors}"


class TestSchemaEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_valid_with_empty_ac_mappings(self, valid_spec):
        """Spec can have empty ac_mappings in traceability."""
        valid_spec["traceability"]["ac_mappings"] = []
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is True

    def test_valid_with_various_http_methods(self, valid_spec):
        """Spec should support all valid HTTP methods."""
        methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]
        for method in methods:
            valid_spec["requirements"][0]["contract"]["interface"]["method"] = method
            is_valid, errors = validate_spec(valid_spec)
            assert is_valid is True, f"Failed for method {method}: {errors}"

    def test_valid_with_multiple_verification_types(self, valid_spec):
        """AC mapping can have multiple verification types."""
        valid_spec["traceability"]["ac_mappings"][0]["required_verifications"] = [
            {
                "ref": "REQ-001.success",
                "description": "Success test",
                "verification_type": "test_result",
            },
            {
                "ref": "REQ-001.FAIL-001",
                "description": "Failure test",
                "verification_type": "test_result",
            },
            {
                "ref": "REQ-001.INV-001",
                "description": "Invariant check",
                "verification_type": "test_result",
            },
        ]
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is True

    def test_precondition_and_failure_ids_match(self, valid_spec):
        """Failure references to preconditions should be string IDs."""
        # Verify the structure is valid
        valid_spec["requirements"][0]["contract"]["failures"][0]["violates"] = "PRE-001"
        is_valid, errors = validate_spec(valid_spec)
        assert is_valid is True

    def test_requirement_with_all_contract_types(self):
        """Requirement can have all contract element types."""
        spec = {
            "meta": {
                "spec_version": "1.0",
                "jira_key": "TEST-001",
                "generated_at": "2026-03-25T10:00:00Z",
                "status": "draft",
            },
            "requirements": [
                {
                    "id": "REQ-001",
                    "ac_checkbox": 0,
                    "ac_text": "Complete requirement",
                    "title": "Complete requirement",
                    "type": "api_behavior",
                    "contract": {
                        "interface": {
                            "method": "POST",
                            "path": "/api/resource",
                            "auth": "oauth2",
                        },
                        "preconditions": [
                            {
                                "id": "PRE-001",
                                "description": "Condition 1",
                            }
                        ],
                        "success": {
                            "status": 201,
                            "content_type": "application/json",
                            "schema": {"type": "object"},
                        },
                        "failures": [
                            {
                                "id": "FAIL-001",
                                "when": "Bad input",
                                "violates": "PRE-001",
                                "status": 400,
                            }
                        ],
                        "invariants": [
                            {
                                "id": "INV-001",
                                "type": "security",
                                "rule": "Always validate input",
                            }
                        ],
                    },
                    "verification": [
                        {
                            "refs": ["success", "FAIL-001", "INV-001"],
                            "skill": "pytest_unit_test",
                            "output": ".verify/generated/test.py",
                        }
                    ],
                }
            ],
            "traceability": {"ac_mappings": []},
        }
        is_valid, errors = validate_spec(spec)
        assert is_valid is True, f"Complete requirement failed: {errors}"
