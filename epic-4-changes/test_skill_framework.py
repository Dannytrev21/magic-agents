"""RED tests for Feature 4.1: Skill Agent Framework.

Tests the VerificationSkill base class, SKILL_REGISTRY, and dispatch_skills().
"""

import os
import pytest
import yaml

# Ensure mock mode
os.environ["LLM_MOCK"] = "true"


class TestVerificationSkillBase:
    """Test the VerificationSkill abstract base class."""

    def test_skill_base_class_exists(self):
        from verify.skills.framework import VerificationSkill
        assert VerificationSkill is not None

    def test_skill_has_required_attributes(self):
        from verify.skills.framework import VerificationSkill

        # A concrete subclass should define skill_id and implement generate/output_path
        class DummySkill(VerificationSkill):
            skill_id = "dummy_test"

            def generate(self, spec, requirement, constitution):
                return "# dummy test"

            def output_path(self, spec, requirement):
                return ".verify/generated/test_dummy.py"

        skill = DummySkill()
        assert skill.skill_id == "dummy_test"
        assert callable(skill.generate)
        assert callable(skill.output_path)

    def test_generate_returns_string(self):
        from verify.skills.framework import VerificationSkill

        class DummySkill(VerificationSkill):
            skill_id = "dummy_test"

            def generate(self, spec, requirement, constitution):
                return "# generated test content"

            def output_path(self, spec, requirement):
                return ".verify/generated/test_dummy.py"

        skill = DummySkill()
        result = skill.generate({}, {}, {})
        assert isinstance(result, str)


class TestSkillRegistry:
    """Test the SKILL_REGISTRY and register_skill function."""

    def test_registry_exists(self):
        from verify.skills.framework import SKILL_REGISTRY
        assert isinstance(SKILL_REGISTRY, dict)

    def test_register_skill(self):
        from verify.skills.framework import VerificationSkill, SKILL_REGISTRY, register_skill

        class TestSkill(VerificationSkill):
            skill_id = "test_register"

            def generate(self, spec, requirement, constitution):
                return ""

            def output_path(self, spec, requirement):
                return ""

        skill = TestSkill()
        register_skill(skill)
        assert "test_register" in SKILL_REGISTRY
        assert SKILL_REGISTRY["test_register"] is skill

    def test_register_duplicate_overwrites(self):
        from verify.skills.framework import VerificationSkill, SKILL_REGISTRY, register_skill

        class SkillV1(VerificationSkill):
            skill_id = "test_dup"

            def generate(self, spec, requirement, constitution):
                return "v1"

            def output_path(self, spec, requirement):
                return ""

        class SkillV2(VerificationSkill):
            skill_id = "test_dup"

            def generate(self, spec, requirement, constitution):
                return "v2"

            def output_path(self, spec, requirement):
                return ""

        register_skill(SkillV1())
        register_skill(SkillV2())
        assert SKILL_REGISTRY["test_dup"].generate({}, {}, {}) == "v2"


class TestDispatchSkills:
    """Test the dispatch_skills function."""

    def test_dispatch_skills_exists(self):
        from verify.skills.framework import dispatch_skills
        assert callable(dispatch_skills)

    def test_dispatch_returns_dict(self):
        from verify.skills.framework import dispatch_skills

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        result = dispatch_skills(spec, {})
        assert isinstance(result, dict)

    def test_dispatch_generates_files(self):
        from verify.skills.framework import dispatch_skills

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        result = dispatch_skills(spec, {})
        # Should have at least one generated file
        assert len(result) > 0
        # Each value should be a string (generated content)
        for path, content in result.items():
            assert isinstance(path, str)
            assert isinstance(content, str)
            assert len(content) > 0

    def test_dispatch_writes_files_to_disk(self, tmp_path):
        from verify.skills.framework import dispatch_skills

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        # Modify output path to use tmp_path
        for req in spec["requirements"]:
            for v in req.get("verification", []):
                v["output"] = str(tmp_path / "test_output.py")

        result = dispatch_skills(spec, {})
        for path in result:
            assert os.path.exists(path), f"Expected file {path} to be written to disk"
