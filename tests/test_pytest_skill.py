"""RED tests for Epic 4.2: Pytest Unit Test Skill.

Tests the PytestSkill that generates pytest test files from spec contracts.
"""

import os
import yaml
import pytest


@pytest.fixture
def sample_spec():
    """A minimal valid spec for testing skill generation."""
    return {
        "meta": {
            "spec_version": "1.0",
            "jira_key": "TEST-001",
            "generated_at": "2026-03-25T00:00:00Z",
            "approved_by": "developer",
            "status": "approved",
        },
        "requirements": [{
            "id": "REQ-001",
            "ac_index": 0,
            "type": "api_behavior",
            "actor": "authenticated_user",
            "contract": {
                "interface": {
                    "method": "GET",
                    "path": "/api/v1/users/me",
                },
                "success": {
                    "status": 200,
                    "schema": {
                        "type": "object",
                        "required": ["id", "email", "displayName"],
                        "properties": {
                            "id": {"type": "string"},
                            "email": {"type": "string"},
                            "displayName": {"type": "string"},
                        },
                        "forbidden_fields": ["password", "password_hash"],
                    },
                },
                "preconditions": [
                    {"id": "PRE-001", "description": "Valid JWT", "category": "authentication",
                     "formal": "jwt != null AND jwt.exp > now()"},
                    {"id": "PRE-002", "description": "User exists", "category": "data_existence",
                     "formal": "db.users.findById(jwt.sub) != null"},
                ],
                "failures": [
                    {"id": "FAIL-001", "when": "No auth token", "violates": "PRE-001",
                     "status": 401, "body": {"error": "unauthorized"}},
                    {"id": "FAIL-002", "when": "User not found", "violates": "PRE-002",
                     "status": 404, "body": {"error": "user_not_found"}},
                ],
                "invariants": [
                    {"id": "INV-001", "type": "security", "rule": "No password in response"},
                ],
            },
            "verification": [{
                "skill": "pytest_unit_test",
                "output": ".verify/generated/test_TEST_001.py",
                "refs": ["success", "FAIL-001", "FAIL-002", "INV-001"],
            }],
        }],
        "traceability": {
            "ac_mappings": [{
                "ac_checkbox": 0,
                "ac_text": "User can view their profile",
                "pass_condition": "ALL_PASS",
                "required_verifications": [
                    {"ref": "REQ-001.success", "description": "Happy path", "verification_type": "test_result"},
                    {"ref": "REQ-001.FAIL-001", "description": "No auth", "verification_type": "test_result"},
                    {"ref": "REQ-001.FAIL-002", "description": "Not found", "verification_type": "test_result"},
                    {"ref": "REQ-001.INV-001", "description": "No password", "verification_type": "test_result"},
                ],
            }],
        },
    }


class TestPytestSkillRegistration:
    """Test that PytestSkill is properly registered."""

    def test_skill_importable(self):
        from verify.skills.pytest_skill import PytestSkill
        assert PytestSkill is not None

    def test_skill_registered_in_registry(self):
        from verify.skills.pytest_skill import PytestSkill  # noqa: F401 - triggers registration
        from verify.skills.framework import SKILL_REGISTRY
        assert "pytest_unit_test" in SKILL_REGISTRY

    def test_skill_has_correct_id(self):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        assert skill.skill_id == "pytest_unit_test"


class TestPytestSkillGeneration:
    """Test that PytestSkill generates valid test files."""

    def test_generate_returns_string(self, sample_spec):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        content = skill.generate(sample_spec, sample_spec["requirements"][0], {})
        assert isinstance(content, str)
        assert len(content) > 0

    def test_generated_content_has_test_functions(self, sample_spec):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        content = skill.generate(sample_spec, sample_spec["requirements"][0], {})
        assert "def test_" in content

    def test_generated_content_has_spec_refs(self, sample_spec):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        content = skill.generate(sample_spec, sample_spec["requirements"][0], {})
        assert "REQ-001" in content
        assert "success" in content
        assert "FAIL-001" in content
        assert "FAIL-002" in content
        assert "INV-001" in content

    def test_generated_content_has_test_client(self, sample_spec):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        content = skill.generate(sample_spec, sample_spec["requirements"][0], {})
        assert "TestClient" in content

    def test_generated_success_test_checks_status(self, sample_spec):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        content = skill.generate(sample_spec, sample_spec["requirements"][0], {})
        assert "200" in content

    def test_generated_failure_tests_check_error_status(self, sample_spec):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        content = skill.generate(sample_spec, sample_spec["requirements"][0], {})
        assert "401" in content
        assert "404" in content

    def test_generated_invariant_test_checks_forbidden_fields(self, sample_spec):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        content = skill.generate(sample_spec, sample_spec["requirements"][0], {})
        assert "password" in content

    def test_output_path_returns_correct_path(self, sample_spec):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        path = skill.output_path(sample_spec, sample_spec["requirements"][0])
        assert "test_" in path
        assert path.endswith(".py")


class TestPytestSkillRunsAgainstDummyApp:
    """Test that generated tests actually pass against the dummy app."""

    def test_generated_tests_are_valid_python(self, sample_spec, tmp_path):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        content = skill.generate(sample_spec, sample_spec["requirements"][0], {})
        test_file = tmp_path / "test_generated.py"
        test_file.write_text(content)
        # Should compile without syntax errors
        compile(content, str(test_file), "exec")
