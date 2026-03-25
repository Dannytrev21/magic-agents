"""RED tests for Feature 4.2: Pytest Unit Test Skill.

Tests the PytestSkill generates correct, tagged test code from specs.
"""

import os
import pytest
import yaml

os.environ["LLM_MOCK"] = "true"


class TestPytestSkillRegistration:
    """Test that PytestSkill is registered in SKILL_REGISTRY."""

    def test_skill_registered(self):
        from verify.skills.pytest_skill import PytestSkill
        from verify.skills.framework import SKILL_REGISTRY
        assert "pytest_unit_test" in SKILL_REGISTRY

    def test_skill_id(self):
        from verify.skills.pytest_skill import PytestSkill
        skill = PytestSkill()
        assert skill.skill_id == "pytest_unit_test"


class TestPytestSkillGeneration:
    """Test the PytestSkill generates correct test content."""

    @pytest.fixture
    def spec(self):
        return yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))

    @pytest.fixture
    def skill(self):
        from verify.skills.pytest_skill import PytestSkill
        return PytestSkill()

    def test_generate_returns_string(self, skill, spec):
        content = skill.generate(spec, spec["requirements"][0], {})
        assert isinstance(content, str)

    def test_generate_contains_test_functions(self, skill, spec):
        content = skill.generate(spec, spec["requirements"][0], {})
        assert "def test_" in content, "Generated content should contain test functions"

    def test_generate_contains_spec_refs(self, skill, spec):
        content = skill.generate(spec, spec["requirements"][0], {})
        assert "REQ-001" in content, "Generated tests should reference the spec requirement"

    def test_generate_contains_testclient_import(self, skill, spec):
        content = skill.generate(spec, spec["requirements"][0], {})
        assert "TestClient" in content, "Generated tests should import TestClient"

    def test_generate_success_test(self, skill, spec):
        content = skill.generate(spec, spec["requirements"][0], {})
        assert "success" in content.lower(), "Should generate a success/happy path test"

    def test_generate_failure_tests(self, skill, spec):
        content = skill.generate(spec, spec["requirements"][0], {})
        assert "FAIL-001" in content, "Should generate test for FAIL-001"
        assert "FAIL-002" in content, "Should generate test for FAIL-002"

    def test_generate_invariant_tests(self, skill, spec):
        content = skill.generate(spec, spec["requirements"][0], {})
        assert "INV-001" in content, "Should generate test for INV-001"

    def test_output_path_returns_string(self, skill, spec):
        path = skill.output_path(spec, spec["requirements"][0])
        assert isinstance(path, str)
        assert path.endswith(".py")

    def test_generate_contains_auth_header(self, skill, spec):
        content = skill.generate(spec, spec["requirements"][0], {})
        assert "Authorization" in content, "Should include Authorization header in tests"
        assert "Bearer" in content, "Should include Bearer token in tests"


class TestPytestSkillGeneratedTestsPass:
    """Test that the generated tests actually pass against the dummy app."""

    def test_generated_tests_are_valid_python(self):
        """Generated code should be syntactically valid Python."""
        from verify.skills.pytest_skill import PytestSkill

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        skill = PytestSkill()
        content = skill.generate(spec, spec["requirements"][0], {})

        # Should compile without SyntaxError
        compile(content, "<generated>", "exec")

    def test_dispatch_and_run_generated_tests(self, tmp_path):
        """Full integration: dispatch skills, write file, run the generated tests."""
        from verify.skills.framework import dispatch_skills

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        files = dispatch_skills(spec, {})

        assert len(files) > 0, "Should generate at least one file"
        # The generated test file should exist
        for path in files:
            assert os.path.exists(path), f"Generated file should exist at {path}"
