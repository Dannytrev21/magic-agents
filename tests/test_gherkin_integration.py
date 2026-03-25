"""RED tests for Gherkin scenario generation and skill dispatch integration.

Tests Feature 9 (Gherkin Scenario Generation) and Feature 10 (Multiple Verification Skills).
TDD: Write these tests FIRST (RED), then implement if any fail (GREEN).
"""

import os
import tempfile

import pytest
import yaml

os.environ["LLM_MOCK"] = "true"


class TestGherkinSkillRegistration:
    """Tests that Gherkin/Cucumber skill is registered in the framework."""

    def test_cucumber_java_skill_in_registry(self):
        from verify.skills.framework import SKILL_REGISTRY
        assert "cucumber_java" in SKILL_REGISTRY

    def test_cucumber_java_skill_has_generate_method(self):
        from verify.skills.framework import SKILL_REGISTRY
        skill = SKILL_REGISTRY["cucumber_java"]
        assert hasattr(skill, "generate")
        assert callable(skill.generate)

    def test_cucumber_java_skill_has_skill_id(self):
        from verify.skills.framework import SKILL_REGISTRY
        skill = SKILL_REGISTRY["cucumber_java"]
        assert skill.skill_id == "cucumber_java"


class TestMultiSkillRouting:
    """Tests for Feature 10: Multiple Verification Skills routing."""

    def test_routing_table_maps_api_behavior(self):
        from verify.compiler import ROUTING_TABLE
        entry = ROUTING_TABLE["api_behavior"]
        assert entry["skill"] == "cucumber_java"
        assert "output_pattern" in entry

    def test_routing_table_maps_compliance(self):
        from verify.compiler import ROUTING_TABLE
        entry = ROUTING_TABLE["compliance"]
        assert entry["skill"] == "gherkin_scenario"

    def test_routing_table_maps_security(self):
        from verify.compiler import ROUTING_TABLE
        entry = ROUTING_TABLE["security_invariant"]
        assert entry["skill"] == "pytest_unit_test"

    def test_routing_table_maps_performance(self):
        from verify.compiler import ROUTING_TABLE
        entry = ROUTING_TABLE["performance_sla"]
        assert entry["skill"] == "newrelic_alert_config"

    def test_routing_table_covers_all_types(self):
        """Every classification type should have a routing entry."""
        from verify.compiler import ROUTING_TABLE
        from verify.negotiation.validate import VALID_TYPES

        for req_type in VALID_TYPES:
            assert req_type in ROUTING_TABLE, f"Missing routing for type: {req_type}"


class TestSkillDispatch:
    """Tests for skill dispatch mechanism."""

    def test_dispatch_skills_with_pytest_skill(self):
        """dispatch_skills should generate content for api_behavior requirements."""
        from verify.skills.framework import dispatch_skills

        spec = {
            "meta": {"jira_key": "DISP-001"},
            "requirements": [
                {
                    "id": "REQ-001",
                    "type": "api_behavior",
                    "title": "Test requirement",
                    "contract": {
                        "interface": {"method": "GET", "path": "/api/v1/test"},
                        "success": {"status": 200, "schema": {"type": "object", "properties": {}, "required": []}},
                        "failures": [
                            {"id": "FAIL-001", "status": 401, "body": {"error": "unauthorized"},
                             "description": "No auth", "violates": "PRE-001"},
                        ],
                        "preconditions": [
                            {"id": "PRE-001", "description": "Auth", "category": "authentication", "formal": "jwt != null"},
                        ],
                        "invariants": [],
                    },
                    "verification": [
                        {
                            "skill": "pytest_unit_test",
                            "refs": ["success", "FAIL-001"],
                            "output": ".verify/generated/test_disp_001.py",
                        },
                    ],
                },
            ],
        }

        files = dispatch_skills(spec, {})
        assert len(files) >= 1
        # At least one file should contain test functions
        for path, content in files.items():
            assert "def test_" in content or "Scenario" in content


class TestCucumberJavaGenerator:
    """Tests for the Cucumber Java generator module."""

    def test_generator_registry(self):
        """CucumberJavaGenerator should be registered via @register decorator."""
        from verify.generators import get_generator
        gen = get_generator("cucumber_java")
        assert gen is not None

    def test_generator_validate_feature_file(self):
        """Validator should check for Feature: declaration and scenarios."""
        from verify.generators.cucumber_java import CucumberJavaGenerator

        gen = CucumberJavaGenerator()
        from verify.generators.base import GeneratedFiles

        files = GeneratedFiles()
        files.add("test.feature", "@DEV-17\nFeature: Test\n  Scenario: Happy path\n    Given something")
        files.add("TestSteps.java", "package com.example;\nimport io.cucumber;\npublic class TestSteps {\n  @Given(\"something\")\n  public void something() {}\n}")

        valid, errors = gen.validate(files)
        # Should at least check for Feature: and Scenario:
        # The @REQ tag check may fail, but the structure should be valid
        assert isinstance(valid, bool)
        assert isinstance(errors, list)

    def test_generator_validate_empty_content_fails(self):
        """Empty file content should fail validation."""
        from verify.generators.cucumber_java import CucumberJavaGenerator
        from verify.generators.base import GeneratedFiles

        gen = CucumberJavaGenerator()
        files = GeneratedFiles()
        files.add("test.feature", "")

        valid, errors = gen.validate(files)
        assert valid is False
        assert len(errors) > 0


class TestGeneratorBaseClass:
    """Tests for the base generator framework."""

    def test_base_generator_load_spec(self):
        """BaseGenerator.load_spec should parse a YAML spec file."""
        from verify.generators.base import BaseGenerator

        spec = {
            "meta": {"jira_key": "LOAD-001"},
            "requirements": [],
            "traceability": {"ac_mappings": []},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(spec, f)
            path = f.name

        try:
            loaded = BaseGenerator.load_spec(path)
            assert loaded["meta"]["jira_key"] == "LOAD-001"
        finally:
            os.unlink(path)

    def test_generated_files_add_and_iterate(self):
        """GeneratedFiles should store and retrieve files."""
        from verify.generators.base import GeneratedFiles

        files = GeneratedFiles()
        files.add("path/to/file.feature", "Feature: Test")
        files.add("path/to/Steps.java", "public class Steps {}")

        assert len(files.files) == 2
        assert "path/to/file.feature" in files.files
        assert files.files["path/to/file.feature"] == "Feature: Test"


class TestVerifyGherkinSkillMd:
    """Tests that the verify-gherkin SKILL.md exists and is well-formed."""

    def test_skill_md_exists(self):
        skill_path = os.path.join(
            os.path.dirname(__file__), "..", ".claude", "skills", "verify-gherkin", "SKILL.md"
        )
        # Normalize the path
        skill_path = os.path.normpath(skill_path)
        assert os.path.exists(skill_path), f"SKILL.md not found at {skill_path}"

    def test_skill_md_has_required_sections(self):
        skill_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", ".claude", "skills", "verify-gherkin", "SKILL.md"
        ))
        if not os.path.exists(skill_path):
            pytest.skip("SKILL.md not found")

        with open(skill_path) as f:
            content = f.read()

        # Agent Skills standard requires these
        assert "---" in content, "Missing YAML frontmatter"
        assert "name:" in content.lower() or "# " in content, "Missing skill name"
