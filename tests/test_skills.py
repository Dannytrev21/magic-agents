"""Tests for the verification skill framework, pytest skill, and tag enforcer."""

import os
import tempfile

import pytest
import yaml


# ── Feature 4.1: Skill Framework Tests ──


class TestSkillFramework:
    """Tests for the skill framework: registry, dispatch, base class."""

    def test_skill_registry_exists(self):
        from verify.skills.framework import SKILL_REGISTRY
        assert isinstance(SKILL_REGISTRY, dict)

    def test_pytest_skill_registered(self):
        from verify.skills.framework import SKILL_REGISTRY
        assert "pytest_unit_test" in SKILL_REGISTRY, (
            f"pytest_unit_test not in registry. Available: {list(SKILL_REGISTRY.keys())}"
        )

    def test_cucumber_java_skill_registered(self):
        from verify.skills.framework import SKILL_REGISTRY
        assert "cucumber_java" in SKILL_REGISTRY, (
            f"cucumber_java not in registry. Available: {list(SKILL_REGISTRY.keys())}"
        )

    def test_dispatch_skills_importable(self):
        from verify.skills.framework import dispatch_skills
        assert callable(dispatch_skills)

    def test_verification_skill_base_class(self):
        from verify.skills.framework import VerificationSkill
        assert hasattr(VerificationSkill, "generate")
        assert hasattr(VerificationSkill, "output_path")
        assert hasattr(VerificationSkill, "expected_refs")

    def test_dispatch_skills_with_mock_spec(self):
        """dispatch_skills generates files from a spec with pytest routing."""
        from verify.skills.framework import dispatch_skills

        with tempfile.TemporaryDirectory() as tmpdir:
            spec = {
                "meta": {"jira_key": "TEST-001", "spec_version": "1.0"},
                "requirements": [
                    {
                        "id": "REQ-001",
                        "type": "api_behavior",
                        "ac_checkbox": 0,
                        "title": "Test AC",
                        "contract": {
                            "interface": {"method": "GET", "path": "/api/v1/test", "auth": "jwt_bearer"},
                            "preconditions": [
                                {"id": "PRE-001", "description": "Valid auth", "category": "authentication", "formal": "jwt != null"}
                            ],
                            "success": {
                                "status": 200,
                                "content_type": "application/json",
                                "schema": {
                                    "type": "object",
                                    "required": ["id", "name"],
                                    "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                                    "forbidden_fields": ["password"],
                                },
                            },
                            "failures": [
                                {"id": "FAIL-001", "when": "No auth token", "violates": "PRE-001", "status": 401, "body": {"error": "unauthorized"}},
                            ],
                            "invariants": [
                                {"id": "INV-001", "type": "security", "rule": "No password in response", "formal": "'password' not in response.keys()"},
                            ],
                        },
                        "verification": [
                            {
                                "refs": ["success", "FAIL-001", "INV-001"],
                                "skill": "pytest_unit_test",
                                "output": os.path.join(tmpdir, "test_generated.py"),
                            }
                        ],
                    }
                ],
                "traceability": {"ac_mappings": []},
            }

            files = dispatch_skills(spec, {})
            assert len(files) >= 1, "No files generated"

            output_path = os.path.join(tmpdir, "test_generated.py")
            assert os.path.exists(output_path), f"Output not created at {output_path}"

            content = files[output_path]
            assert "def test_" in content, "No test functions in output"
            assert "REQ-001" in content, "Missing spec refs"

    def test_dispatch_skips_unknown_skills(self, capsys):
        """dispatch_skills warns about unknown skills."""
        from verify.skills.framework import dispatch_skills

        spec = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "verification": [{"skill": "nonexistent_skill", "output": "/tmp/out.py"}],
                }
            ]
        }
        files = dispatch_skills(spec, {})
        assert len(files) == 0

        captured = capsys.readouterr()
        assert "WARN" in captured.out


# ── Feature 4.2: Pytest Skill Tests ──


class TestPytestSkill:
    """Tests for the pytest unit test skill."""

    def _make_spec_requirement(self):
        return {
            "id": "REQ-001",
            "type": "api_behavior",
            "contract": {
                "interface": {"method": "GET", "path": "/api/v1/dogs/1", "auth": "jwt_bearer"},
                "preconditions": [
                    {"id": "PRE-001", "description": "Valid JWT", "category": "authentication", "formal": "jwt != null"},
                    {"id": "PRE-002", "description": "Dog exists", "category": "data_existence", "formal": "dog.id exists"},
                ],
                "success": {
                    "status": 200,
                    "content_type": "application/json",
                    "schema": {
                        "type": "object",
                        "required": ["id", "name", "breed"],
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "breed": {"type": "string"},
                        },
                        "forbidden_fields": ["password", "internal_id"],
                    },
                },
                "failures": [
                    {"id": "FAIL-001", "when": "No auth token", "violates": "PRE-001", "status": 401, "body": {"error": "unauthorized"}},
                    {"id": "FAIL-002", "when": "Dog not found", "violates": "PRE-002", "status": 404, "body": {"error": "not_found"}},
                ],
                "invariants": [
                    {"id": "INV-001", "type": "security", "rule": "Response MUST NOT contain password", "formal": "'password' not in response"},
                ],
            },
            "verification": [{"refs": ["success", "FAIL-001", "FAIL-002", "INV-001"], "skill": "pytest_unit_test", "output": "test.py"}],
        }

    def test_generate_api_behavior(self):
        """PytestSkill generates tests for api_behavior requirements."""
        from verify.skills.pytest_skill import PytestSkill

        skill = PytestSkill()
        spec = {"meta": {"jira_key": "TEST-001"}, "requirements": [self._make_spec_requirement()]}
        constitution = {
            "api": {
                "base_path": "/api/v1",
                "auth": {"mechanism": "jwt_bearer", "token_header": "Authorization", "token_prefix": "Bearer "},
            }
        }

        content = skill.generate(spec, spec["requirements"][0], constitution)

        # Check test functions exist
        assert "def test_REQ_001_success" in content, "Missing success test"
        assert "def test_REQ_001_FAIL_001" in content, "Missing FAIL-001 test"
        assert "def test_REQ_001_FAIL_002" in content, "Missing FAIL-002 test"
        assert "def test_REQ_001_INV_001" in content, "Missing INV-001 test"

    def test_generate_includes_spec_refs_in_docstrings(self):
        """Generated tests have [REQ-xxx.yyy] in docstrings."""
        from verify.skills.pytest_skill import PytestSkill

        skill = PytestSkill()
        spec = {"meta": {"jira_key": "TEST-001"}, "requirements": [self._make_spec_requirement()]}
        content = skill.generate(spec, spec["requirements"][0], {})

        assert "[REQ-001.success]" in content
        assert "[REQ-001.FAIL-001]" in content
        assert "[REQ-001.FAIL-002]" in content
        assert "[REQ-001.INV-001]" in content

    def test_generate_uses_requests_library(self):
        """Generated tests use the requests library for HTTP calls."""
        from verify.skills.pytest_skill import PytestSkill

        skill = PytestSkill()
        spec = {"meta": {"jira_key": "TEST-001"}, "requirements": [self._make_spec_requirement()]}
        content = skill.generate(spec, spec["requirements"][0], {})

        assert "import requests" in content
        assert "requests.get" in content

    def test_generate_checks_forbidden_fields(self):
        """Generated invariant tests check forbidden fields."""
        from verify.skills.pytest_skill import PytestSkill

        skill = PytestSkill()
        spec = {"meta": {"jira_key": "TEST-001"}, "requirements": [self._make_spec_requirement()]}
        content = skill.generate(spec, spec["requirements"][0], {})

        assert '"password" not in body' in content
        assert '"internal_id" not in body' in content

    def test_auth_failure_has_no_auth_header(self):
        """Authentication failure tests don't send auth headers."""
        from verify.skills.pytest_skill import PytestSkill

        skill = PytestSkill()
        spec = {"meta": {"jira_key": "TEST-001"}, "requirements": [self._make_spec_requirement()]}
        content = skill.generate(spec, spec["requirements"][0], {})

        # Find the FAIL-001 test (auth failure) and check it doesn't use _auth_headers
        lines = content.split("\n")
        in_fail_001 = False
        fail_001_lines = []
        for line in lines:
            if "def test_REQ_001_FAIL_001" in line:
                in_fail_001 = True
            elif in_fail_001 and line.strip().startswith("def "):
                break
            elif in_fail_001:
                fail_001_lines.append(line)

        fail_001_body = "\n".join(fail_001_lines)
        assert "No auth header" in fail_001_body or "_auth_headers" not in fail_001_body


# ── Feature 4.3: Tag Enforcer Tests ──


class TestTagEnforcer:
    """Tests for the tag contract enforcement module."""

    def test_validate_tags_full_coverage(self):
        from verify.skills.tag_enforcer import validate_tags

        content = '''
        def test_REQ_001_success():
            """[REQ-001.success] Happy path"""
            pass

        def test_REQ_001_FAIL_001():
            """[REQ-001.FAIL-001] No auth"""
            pass
        '''
        expected = ["REQ-001.success", "REQ-001.FAIL-001"]
        result = validate_tags(content, expected)

        assert len(result["covered"]) == 2
        assert len(result["missing"]) == 0
        assert result["coverage_pct"] == 100.0

    def test_validate_tags_partial_coverage(self):
        from verify.skills.tag_enforcer import validate_tags

        content = '''
        def test_REQ_001_success():
            """[REQ-001.success] Happy path"""
            pass
        '''
        expected = ["REQ-001.success", "REQ-001.FAIL-001", "REQ-001.FAIL-002"]
        result = validate_tags(content, expected)

        assert "REQ-001.success" in result["covered"]
        assert "REQ-001.FAIL-001" in result["missing"]
        assert "REQ-001.FAIL-002" in result["missing"]
        assert len(result["missing"]) == 2

    def test_validate_tags_extra_refs(self):
        from verify.skills.tag_enforcer import validate_tags

        content = """[REQ-001.success] [REQ-001.FAIL-001] [REQ-001.FAIL-002]"""
        expected = ["REQ-001.success"]
        result = validate_tags(content, expected)

        assert "REQ-001.success" in result["covered"]
        assert "REQ-001.FAIL-001" in result["extra"]
        assert "REQ-001.FAIL-002" in result["extra"]

    def test_extract_refs_bracket_pattern(self):
        from verify.skills.tag_enforcer import extract_refs

        content = '[REQ-001.success] and [REQ-001.FAIL-001]'
        refs = extract_refs(content)

        assert "REQ-001.success" in refs
        assert "REQ-001.FAIL-001" in refs

    def test_extract_refs_underscore_pattern(self):
        from verify.skills.tag_enforcer import extract_refs

        content = "def test_REQ_001_success(): pass\ndef test_REQ_001_FAIL_001(): pass"
        refs = extract_refs(content)

        assert "REQ-001.success" in refs
        assert "REQ-001.FAIL-001" in refs

    def test_extract_refs_marker_pattern(self):
        from verify.skills.tag_enforcer import extract_refs

        content = '@pytest.mark.spec("REQ-001.success")'
        refs = extract_refs(content)

        assert "REQ-001.success" in refs

    def test_enforce_coverage_passes(self):
        from verify.skills.tag_enforcer import enforce_coverage

        content = "[REQ-001.success] [REQ-001.FAIL-001]"
        expected = ["REQ-001.success", "REQ-001.FAIL-001"]
        passed, result = enforce_coverage(content, expected)

        assert passed is True
        assert result["coverage_pct"] == 100.0

    def test_enforce_coverage_fails(self):
        from verify.skills.tag_enforcer import enforce_coverage

        content = "[REQ-001.success]"
        expected = ["REQ-001.success", "REQ-001.FAIL-001"]
        passed, result = enforce_coverage(content, expected)

        assert passed is False
        assert result["coverage_pct"] == 50.0


# ── Integration: Skill + Tag Enforcer ──


class TestSkillTagIntegration:
    """Integration test: skill generates content, tag enforcer validates it."""

    def test_pytest_skill_passes_tag_enforcement(self):
        """Generated pytest tests have 100% tag coverage."""
        from verify.skills.pytest_skill import PytestSkill
        from verify.skills.tag_enforcer import enforce_coverage

        skill = PytestSkill()
        requirement = {
            "id": "REQ-001",
            "type": "api_behavior",
            "contract": {
                "interface": {"method": "GET", "path": "/api/v1/dogs/1", "auth": "jwt_bearer"},
                "preconditions": [
                    {"id": "PRE-001", "description": "Auth", "category": "authentication", "formal": "x"},
                ],
                "success": {
                    "status": 200,
                    "schema": {"required": ["id"], "properties": {"id": {"type": "int"}}, "forbidden_fields": ["password"]},
                },
                "failures": [
                    {"id": "FAIL-001", "when": "No auth", "violates": "PRE-001", "status": 401, "body": {"error": "unauthorized"}},
                ],
                "invariants": [
                    {"id": "INV-001", "type": "security", "rule": "No password", "formal": "x"},
                ],
            },
            "verification": [{"refs": ["success", "FAIL-001", "INV-001"], "skill": "pytest_unit_test", "output": "test.py"}],
        }

        spec = {"meta": {"jira_key": "TEST-001"}, "requirements": [requirement]}
        content = skill.generate(spec, requirement, {})

        expected_refs = ["REQ-001.success", "REQ-001.FAIL-001", "REQ-001.INV-001"]
        passed, result = enforce_coverage(content, expected_refs)

        assert passed, f"Tag coverage failed! Missing: {result['missing']}, Coverage: {result['coverage_pct']}%"
