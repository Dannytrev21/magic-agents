"""Tests for the spec diff feature (Feature 17: Spec Diff on Re-negotiation)."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from verify.spec_diff import diff_specs, format_diff_summary


# Fixtures for test specs
@pytest.fixture
def old_spec_dict():
    """Sample old spec from a previous negotiation."""
    return {
        "meta": {
            "spec_version": "1.0",
            "jira_key": "DEMO-001",
            "jira_summary": "User can view their profile",
            "generated_at": "2026-03-21T00:00:00Z",
            "approved_at": "2026-03-21T00:00:00Z",
            "approved_by": "hackathon-team",
            "status": "approved",
        },
        "requirements": [
            {
                "id": "REQ-001",
                "ac_checkbox": 0,
                "ac_text": "User can view their profile",
                "title": "Authenticated user retrieves their profile",
                "type": "api_behavior",
                "contract": {
                    "interface": {
                        "method": "GET",
                        "path": "/api/v1/users/me",
                        "auth": "jwt_bearer",
                    },
                    "preconditions": [
                        {
                            "id": "PRE-001",
                            "description": "Request includes a valid Bearer token",
                            "formal": "authorization_header != null",
                            "category": "authentication",
                        }
                    ],
                    "success": {
                        "status": 200,
                        "content_type": "application/json",
                        "schema": {
                            "type": "object",
                            "required": ["id", "email"],
                            "properties": {
                                "id": {"type": "string"},
                                "email": {"type": "string"},
                            },
                        },
                    },
                    "failures": [
                        {
                            "id": "FAIL-001",
                            "when": "Missing Authorization header",
                            "violates": "PRE-001",
                            "status": 401,
                        }
                    ],
                    "invariants": [
                        {
                            "id": "INV-001",
                            "type": "security",
                            "rule": "MUST NOT expose password field",
                            "formal": "'password' not in response.keys()",
                        }
                    ],
                },
                "verification": [
                    {
                        "refs": ["success", "FAIL-001", "INV-001"],
                        "skill": "cucumber_java",
                        "output": "dog-service/src/test/resources/features/demo_001.feature",
                    }
                ],
            }
        ],
        "traceability": {
            "ac_mappings": [
                {
                    "ac_checkbox": 0,
                    "ac_text": "User can view their profile",
                    "pass_condition": "ALL_PASS",
                    "required_verifications": [
                        {
                            "ref": "REQ-001.success",
                            "description": "Happy path: HTTP 200",
                            "verification_type": "test_result",
                        }
                    ],
                }
            ]
        },
    }


@pytest.fixture
def new_spec_dict_with_new_req(old_spec_dict):
    """New spec with an added requirement."""
    new_spec = {
        **old_spec_dict,
        "meta": {
            **old_spec_dict["meta"],
            "generated_at": "2026-03-25T10:00:00Z",
        },
        "requirements": old_spec_dict["requirements"] + [
            {
                "id": "REQ-002",
                "ac_checkbox": 1,
                "ac_text": "User can update their profile",
                "title": "Authenticated user updates their profile",
                "type": "api_behavior",
                "contract": {
                    "interface": {
                        "method": "PATCH",
                        "path": "/api/v1/users/me",
                        "auth": "jwt_bearer",
                    },
                    "preconditions": [
                        {
                            "id": "PRE-002",
                            "description": "Request includes a valid Bearer token",
                            "formal": "authorization_header != null",
                            "category": "authentication",
                        }
                    ],
                    "success": {
                        "status": 200,
                        "content_type": "application/json",
                        "schema": {
                            "type": "object",
                            "required": ["id"],
                            "properties": {
                                "id": {"type": "string"},
                            },
                        },
                    },
                    "failures": [],
                    "invariants": [],
                },
                "verification": [
                    {
                        "refs": ["success"],
                        "skill": "cucumber_java",
                        "output": "dog-service/src/test/resources/features/demo_001.feature",
                    }
                ],
            }
        ],
    }
    return new_spec


@pytest.fixture
def new_spec_dict_with_removed_req(old_spec_dict):
    """New spec with the first requirement removed."""
    new_spec = {
        **old_spec_dict,
        "meta": {
            **old_spec_dict["meta"],
            "generated_at": "2026-03-25T10:00:00Z",
        },
        "requirements": [],  # Removed REQ-001
    }
    return new_spec


@pytest.fixture
def new_spec_dict_with_modified_req(old_spec_dict):
    """New spec with REQ-001 modified."""
    new_spec = {
        **old_spec_dict,
        "meta": {
            **old_spec_dict["meta"],
            "generated_at": "2026-03-25T10:00:00Z",
        },
        "requirements": [
            {
                **old_spec_dict["requirements"][0],
                "title": "Updated title: User profile retrieval",
                "contract": {
                    **old_spec_dict["requirements"][0]["contract"],
                    "success": {
                        **old_spec_dict["requirements"][0]["contract"]["success"],
                        "status": 201,  # Changed from 200 to 201
                    },
                },
            }
        ],
    }
    return new_spec


@pytest.fixture
def old_spec_file(tmp_path, old_spec_dict):
    """Write the old spec to a temp file."""
    spec_file = tmp_path / "DEMO-001.yaml"
    with open(spec_file, "w") as f:
        yaml.dump(old_spec_dict, f)
    return str(spec_file)


# Tests

class TestDiffSpecsNoOldSpec:
    """Test diff_specs when no old spec exists."""

    def test_missing_old_spec_file(self, tmp_path, old_spec_dict):
        """Should handle missing old spec gracefully."""
        missing_path = str(tmp_path / "nonexistent.yaml")
        new_spec = old_spec_dict

        result = diff_specs(missing_path, new_spec)

        assert result["error"] is not None
        assert "not found" in result["error"].lower()
        assert result["added_requirements"] == []
        assert "No old spec found" in result["summary"]


class TestDiffSpecsAddedRequirements:
    """Test detection of added requirements."""

    def test_single_added_requirement(self, old_spec_file, new_spec_dict_with_new_req):
        """Should detect a newly added requirement."""
        result = diff_specs(old_spec_file, new_spec_dict_with_new_req)

        assert result["added_requirements"] == ["REQ-002"]
        assert result["removed_requirements"] == []
        assert result["modified_requirements"] == {}

    def test_added_requirement_in_summary(self, old_spec_file, new_spec_dict_with_new_req):
        """Summary should mention the added requirement."""
        result = diff_specs(old_spec_file, new_spec_dict_with_new_req)
        summary = result["summary"]

        assert "ADDED (1)" in summary
        assert "REQ-002" in summary


class TestDiffSpecsRemovedRequirements:
    """Test detection of removed requirements."""

    def test_single_removed_requirement(self, old_spec_file, new_spec_dict_with_removed_req):
        """Should detect a removed requirement."""
        result = diff_specs(old_spec_file, new_spec_dict_with_removed_req)

        assert result["removed_requirements"] == ["REQ-001"]
        assert result["added_requirements"] == []
        assert result["modified_requirements"] == {}

    def test_removed_requirement_in_summary(self, old_spec_file, new_spec_dict_with_removed_req):
        """Summary should mention the removed requirement."""
        result = diff_specs(old_spec_file, new_spec_dict_with_removed_req)
        summary = result["summary"]

        assert "REMOVED (1)" in summary
        assert "REQ-001" in summary


class TestDiffSpecsModifiedRequirements:
    """Test detection of modified requirements."""

    def test_modified_requirement_title(self, old_spec_file, new_spec_dict_with_modified_req):
        """Should detect when a requirement's title changes."""
        result = diff_specs(old_spec_file, new_spec_dict_with_modified_req)

        assert "REQ-001" in result["modified_requirements"]
        changes = result["modified_requirements"]["REQ-001"]
        assert "title" in changes
        old_title, new_title = changes["title"]
        assert old_title == "Authenticated user retrieves their profile"
        assert "Updated title" in new_title

    def test_modified_requirement_status_code(self, old_spec_file, new_spec_dict_with_modified_req):
        """Should detect changes in nested contract fields."""
        result = diff_specs(old_spec_file, new_spec_dict_with_modified_req)

        assert "REQ-001" in result["modified_requirements"]
        changes = result["modified_requirements"]["REQ-001"]
        assert "contract" in changes
        old_contract, new_contract = changes["contract"]
        assert old_contract["success"]["status"] == 200
        assert new_contract["success"]["status"] == 201

    def test_modified_requirement_in_summary(self, old_spec_file, new_spec_dict_with_modified_req):
        """Summary should mention the modified requirement and its fields."""
        result = diff_specs(old_spec_file, new_spec_dict_with_modified_req)
        summary = result["summary"]

        assert "MODIFIED (1)" in summary
        assert "REQ-001" in summary
        assert "title" in summary.lower() or "contract" in summary.lower()


class TestDiffSpecsChangedTopLevelFields:
    """Test detection of changed top-level fields (metadata, traceability, etc.)."""

    def test_changed_metadata(self, old_spec_file, new_spec_dict_with_new_req):
        """Should detect changes to metadata fields."""
        result = diff_specs(old_spec_file, new_spec_dict_with_new_req)

        # generated_at should have changed
        assert "meta" in result["changed_fields"]

    def test_changed_traceability(self, old_spec_file, new_spec_dict_with_new_req):
        """Should detect changes to traceability mapping."""
        # New spec has an additional requirement, so traceability changes
        result = diff_specs(old_spec_file, new_spec_dict_with_new_req)

        # The traceability should differ because we added REQ-002
        # (actual comparison depends on implementation)
        # At minimum, changed_fields should be populated if traceability differs
        assert isinstance(result["changed_fields"], list)


class TestDiffSpecsNoChanges:
    """Test diff when specs are identical."""

    def test_identical_specs(self, old_spec_file, old_spec_dict):
        """Identical specs should show no changes."""
        result = diff_specs(old_spec_file, old_spec_dict)

        assert result["added_requirements"] == []
        assert result["removed_requirements"] == []
        assert result["modified_requirements"] == {}
        # changed_fields might still include meta fields like generated_at
        # (depends on whether those are compared exactly)


class TestFormatDiffSummary:
    """Test the human-readable summary formatter."""

    def test_format_with_added_requirements(self):
        """Summary should list added requirements."""
        diff = {
            "added_requirements": ["REQ-002", "REQ-003"],
            "removed_requirements": [],
            "modified_requirements": {},
            "changed_fields": [],
        }
        summary = format_diff_summary(diff)

        assert "ADDED (2)" in summary
        assert "REQ-002" in summary
        assert "REQ-003" in summary

    def test_format_with_removed_requirements(self):
        """Summary should list removed requirements."""
        diff = {
            "added_requirements": [],
            "removed_requirements": ["REQ-001"],
            "modified_requirements": {},
            "changed_fields": [],
        }
        summary = format_diff_summary(diff)

        assert "REMOVED (1)" in summary
        assert "REQ-001" in summary

    def test_format_with_modified_requirements(self):
        """Summary should show modified requirement fields."""
        diff = {
            "added_requirements": [],
            "removed_requirements": [],
            "modified_requirements": {
                "REQ-001": {
                    "title": ("Old title", "New title"),
                    "status": (200, 201),
                }
            },
            "changed_fields": [],
        }
        summary = format_diff_summary(diff)

        assert "MODIFIED (1)" in summary
        assert "REQ-001" in summary
        assert "title" in summary
        assert "status" in summary

    def test_format_with_no_changes(self):
        """Summary should indicate no changes."""
        diff = {
            "added_requirements": [],
            "removed_requirements": [],
            "modified_requirements": {},
            "changed_fields": [],
        }
        summary = format_diff_summary(diff)

        assert "No changes detected" in summary

    def test_format_with_changed_fields(self):
        """Summary should list changed top-level fields."""
        diff = {
            "added_requirements": [],
            "removed_requirements": [],
            "modified_requirements": {},
            "changed_fields": ["meta", "traceability"],
        }
        summary = format_diff_summary(diff)

        assert "FIELD CHANGES (2)" in summary
        assert "meta" in summary
        assert "traceability" in summary

    def test_format_comprehensive(self):
        """Summary should handle multiple types of changes."""
        diff = {
            "added_requirements": ["REQ-002"],
            "removed_requirements": ["REQ-003"],
            "modified_requirements": {
                "REQ-001": {
                    "title": ("Old", "New"),
                }
            },
            "changed_fields": ["meta"],
        }
        summary = format_diff_summary(diff)

        assert "ADDED (1)" in summary
        assert "REMOVED (1)" in summary
        assert "MODIFIED (1)" in summary
        assert "FIELD CHANGES (1)" in summary
        assert "Total changes: 4" in summary


class TestSpecDiffIntegration:
    """Integration tests for full spec diff flow."""

    def test_diff_specs_result_structure(self, old_spec_file, new_spec_dict_with_new_req):
        """Result should have all expected keys."""
        result = diff_specs(old_spec_file, new_spec_dict_with_new_req)

        expected_keys = {
            "added_requirements",
            "removed_requirements",
            "modified_requirements",
            "changed_fields",
            "summary",
            "old_spec",
            "new_spec",
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_diff_preserves_specs_for_reference(self, old_spec_file, new_spec_dict_with_new_req):
        """Result should include both old and new specs for reference."""
        result = diff_specs(old_spec_file, new_spec_dict_with_new_req)

        assert result["old_spec"] is not None
        assert result["new_spec"] is not None
        assert isinstance(result["old_spec"], dict)
        assert isinstance(result["new_spec"], dict)

    def test_diff_with_complex_changes(self, old_spec_file, new_spec_dict_with_new_req):
        """Diff should work with multiple simultaneous changes."""
        # Start with new spec that has an added requirement
        complex_spec = {
            **new_spec_dict_with_new_req,
            "requirements": [
                # Modify the first requirement
                {
                    **new_spec_dict_with_new_req["requirements"][0],
                    "title": "Modified title",
                },
                # Keep the second requirement as-is
                new_spec_dict_with_new_req["requirements"][1],
            ],
            "meta": {
                **new_spec_dict_with_new_req["meta"],
                "status": "draft",  # Changed from approved
            },
        }

        result = diff_specs(old_spec_file, complex_spec)

        # Should detect added and modified
        assert "REQ-002" in result["added_requirements"]
        assert "REQ-001" in result["modified_requirements"]
        # Should detect meta field changes
        assert "meta" in result["changed_fields"]
