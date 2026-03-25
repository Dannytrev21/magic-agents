"""TDD tests for Epic 4: Verification Skill Framework, Pytest Skill, and Tag Enforcer.

RED phase — these tests define the contracts for:
  - Feature 4.1: Skill Agent Framework (VerificationSkill base class, SKILL_REGISTRY, dispatch_skills)
  - Feature 4.2: Pytest Unit Test Skill (PytestSkill generates tagged test code)
  - Feature 4.3: Tag Contract Enforcement (validate_tags checks coverage)
"""

import os
import yaml
import pytest


# ── Feature 4.1: Skill Agent Framework ──

class TestSkillFramework:
    """Feature 4.1: VerificationSkill base class, SKILL_REGISTRY, dispatch_skills."""

    def test_framework_imports(self):
        """SKILL_REGISTRY and dispatch_skills are importable."""
        from verify.skills.framework import VerificationSkill, SKILL_REGISTRY, dispatch_skills
        assert isinstance(SKILL_REGISTRY, dict)

    def test_verification_skill_is_abstract(self):
        """VerificationSkill enforces generate() and output_path() implementation."""
        from verify.skills.framework import VerificationSkill

        class IncompleteSkill(VerificationSkill):
            skill_id = "incomplete"

        with pytest.raises(TypeError):
            IncompleteSkill()

    def test_register_skill_adds_to_registry(self):
        """register_skill() puts a skill into SKILL_REGISTRY by its skill_id."""
        from verify.skills.framework import VerificationSkill, SKILL_REGISTRY, register_skill

        class DummySkill(VerificationSkill):
            skill_id = "test_dummy"

            def generate(self, spec, requirement, constitution):
                return "# dummy"

            def output_path(self, spec, requirement):
                return "/tmp/dummy.py"

        register_skill(DummySkill())
        assert "test_dummy" in SKILL_REGISTRY

        # Clean up
        del SKILL_REGISTRY["test_dummy"]

    def test_dispatch_skills_returns_dict_of_generated_files(self):
        """dispatch_skills() routes spec requirements to skills and returns {path: content}."""
        from verify.skills.framework import dispatch_skills
        import verify.skills.pytest_skill  # noqa: F401 — ensure skill is registered

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        result = dispatch_skills(spec, {})

        assert isinstance(result, dict)
        assert len(result) > 0
        for path, content in result.items():
            assert path.endswith(".py")
            assert "def test_" in content

    def test_dispatch_skills_writes_files(self, tmp_path):
        """dispatch_skills() actually writes generated files to disk."""
        from verify.skills.framework import dispatch_skills
        import verify.skills.pytest_skill  # noqa: F401 — ensure skill is registered

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        result = dispatch_skills(spec, {})

        for path in result:
            assert os.path.exists(path), f"Expected file to be written: {path}"


# ── Feature 4.2: Pytest Unit Test Skill ──

class TestPytestSkill:
    """Feature 4.2: PytestSkill generates tagged pytest test code from spec contracts."""

    def test_pytest_skill_registered(self):
        """PytestSkill is auto-registered as 'pytest_unit_test'."""
        from verify.skills.pytest_skill import PytestSkill
        from verify.skills.framework import SKILL_REGISTRY

        assert "pytest_unit_test" in SKILL_REGISTRY
        assert isinstance(SKILL_REGISTRY["pytest_unit_test"], PytestSkill)

    def test_generate_contains_spec_refs(self):
        """Generated test code contains spec refs like REQ-001."""
        from verify.skills.framework import SKILL_REGISTRY

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        skill = SKILL_REGISTRY["pytest_unit_test"]
        content = skill.generate(spec, spec["requirements"][0], {})

        assert "REQ-001" in content, "Missing spec refs in generated tests"

    def test_generate_contains_test_functions(self):
        """Generated code contains actual test function definitions."""
        from verify.skills.framework import SKILL_REGISTRY

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        skill = SKILL_REGISTRY["pytest_unit_test"]
        content = skill.generate(spec, spec["requirements"][0], {})

        assert "def test_" in content, "No test functions generated"

    def test_generate_uses_testclient(self):
        """Generated tests use FastAPI's TestClient for API testing."""
        from verify.skills.framework import SKILL_REGISTRY

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        skill = SKILL_REGISTRY["pytest_unit_test"]
        content = skill.generate(spec, spec["requirements"][0], {})

        assert "TestClient" in content, "Missing TestClient import"

    def test_generate_covers_success_and_failures(self):
        """Generated tests cover the happy path, all failure modes, and invariants."""
        from verify.skills.framework import SKILL_REGISTRY

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        skill = SKILL_REGISTRY["pytest_unit_test"]
        content = skill.generate(spec, spec["requirements"][0], {})

        assert "success" in content.lower(), "No success test"
        assert "FAIL-001" in content or "FAIL_001" in content, "No FAIL-001 test"
        assert "FAIL-002" in content or "FAIL_002" in content, "No FAIL-002 test"
        assert "INV-001" in content or "INV_001" in content, "No INV-001 test"

    def test_output_path_matches_spec(self):
        """output_path() returns the path specified in the spec verification block."""
        from verify.skills.framework import SKILL_REGISTRY

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        skill = SKILL_REGISTRY["pytest_unit_test"]
        path = skill.output_path(spec, spec["requirements"][0])

        assert path == ".verify/generated/test_demo_001.py"

    def test_generated_tests_actually_pass(self):
        """Generated tests pass when run against the dummy app."""
        from verify.skills.framework import dispatch_skills

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        files = dispatch_skills(spec, {})

        # Run the generated tests
        import subprocess
        import sys

        for path in files:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src"},
            )
            assert result.returncode == 0, (
                f"Generated tests failed:\n{result.stdout}\n{result.stderr}"
            )


# ── Feature 4.3: Tag Contract Enforcement ──

class TestTagEnforcer:
    """Feature 4.3: validate_tags checks that generated tests cover all spec refs."""

    def test_validate_tags_importable(self):
        """validate_tags is importable from tag_enforcer module."""
        from verify.skills.tag_enforcer import validate_tags

    def test_validate_tags_finds_covered_refs(self):
        """validate_tags correctly identifies refs present in the test content."""
        from verify.skills.tag_enforcer import validate_tags

        test_content = '''
        def test_success_REQ_001():
            """[REQ-001.success] Happy path"""
            pass

        def test_fail_001():
            """[REQ-001.FAIL-001] No auth"""
            pass
        '''

        result = validate_tags(
            test_content,
            ["REQ-001.success", "REQ-001.FAIL-001", "REQ-001.FAIL-002"],
        )

        assert "REQ-001.success" in result["covered"]
        assert "REQ-001.FAIL-001" in result["covered"]

    def test_validate_tags_finds_missing_refs(self):
        """validate_tags correctly identifies refs NOT present in the test content."""
        from verify.skills.tag_enforcer import validate_tags

        test_content = '[REQ-001.success]'

        result = validate_tags(
            test_content,
            ["REQ-001.success", "REQ-001.FAIL-001"],
        )

        assert "REQ-001.FAIL-001" in result["missing"]

    def test_validate_tags_finds_extra_refs(self):
        """validate_tags identifies refs in tests that aren't in the expected list."""
        from verify.skills.tag_enforcer import validate_tags

        test_content = '[REQ-001.success] [REQ-001.FAIL-001] [REQ-001.EXTRA-001]'

        result = validate_tags(
            test_content,
            ["REQ-001.success"],
        )

        assert len(result["extra"]) > 0

    def test_validate_tags_returns_correct_structure(self):
        """validate_tags returns dict with 'covered', 'missing', and 'extra' keys."""
        from verify.skills.tag_enforcer import validate_tags

        result = validate_tags("", [])
        assert "covered" in result
        assert "missing" in result
        assert "extra" in result

    def test_full_coverage_on_generated_tests(self):
        """Generated tests from PytestSkill have 100% tag coverage for DEMO-001."""
        from verify.skills.framework import SKILL_REGISTRY
        from verify.skills.tag_enforcer import validate_tags

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        skill = SKILL_REGISTRY["pytest_unit_test"]
        content = skill.generate(spec, spec["requirements"][0], {})

        req = spec["requirements"][0]
        expected_refs = [
            f"{req['id']}.{ref}" for ref in req["verification"][0]["refs"]
        ]

        result = validate_tags(content, expected_refs)
        assert len(result["missing"]) == 0, (
            f"Missing refs in generated tests: {result['missing']}"
        )
