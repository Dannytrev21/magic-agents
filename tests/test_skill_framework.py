"""RED tests for Epic 4.1: Skill Agent Framework.

Tests the VerificationSkill base class, SKILL_REGISTRY, and dispatch_skills.
"""

import os
import yaml
import pytest


class TestVerificationSkillBase:
    """Test the VerificationSkill abstract base class."""

    def test_base_class_importable(self):
        from verify.skills.framework import VerificationSkill
        assert VerificationSkill is not None

    def test_base_class_has_skill_id(self):
        from verify.skills.framework import VerificationSkill
        # Subclass must define skill_id
        class TestSkill(VerificationSkill):
            skill_id = "test_skill"
            def generate(self, spec, requirement, constitution):
                return "test"
            def output_path(self, spec, requirement):
                return "/tmp/test.py"
        skill = TestSkill()
        assert skill.skill_id == "test_skill"

    def test_base_class_requires_generate(self):
        from verify.skills.framework import VerificationSkill
        # Cannot instantiate without implementing generate
        with pytest.raises(TypeError):
            VerificationSkill()

    def test_base_class_requires_output_path(self):
        from verify.skills.framework import VerificationSkill
        class Incomplete(VerificationSkill):
            skill_id = "incomplete"
            def generate(self, spec, requirement, constitution):
                return "test"
        with pytest.raises(TypeError):
            Incomplete()


class TestSkillRegistry:
    """Test the SKILL_REGISTRY dict and register_skill function."""

    def test_registry_exists(self):
        from verify.skills.framework import SKILL_REGISTRY
        assert isinstance(SKILL_REGISTRY, dict)

    def test_register_skill(self):
        from verify.skills.framework import VerificationSkill, SKILL_REGISTRY, register_skill
        class DummySkill(VerificationSkill):
            skill_id = "dummy_test_skill"
            def generate(self, spec, requirement, constitution):
                return "dummy"
            def output_path(self, spec, requirement):
                return "/tmp/dummy.py"
        register_skill(DummySkill())
        assert "dummy_test_skill" in SKILL_REGISTRY
        # Cleanup
        del SKILL_REGISTRY["dummy_test_skill"]

    def test_register_skill_rejects_duplicate(self):
        from verify.skills.framework import VerificationSkill, SKILL_REGISTRY, register_skill
        class Dup(VerificationSkill):
            skill_id = "dup_skill"
            def generate(self, spec, requirement, constitution):
                return ""
            def output_path(self, spec, requirement):
                return ""
        register_skill(Dup())
        with pytest.raises(ValueError):
            register_skill(Dup())
        # Cleanup
        del SKILL_REGISTRY["dup_skill"]


class TestDispatchSkills:
    """Test the dispatch_skills function."""

    def test_dispatch_skills_exists(self):
        from verify.skills.framework import dispatch_skills
        assert callable(dispatch_skills)

    def test_dispatch_skills_returns_dict(self):
        from verify.skills.framework import dispatch_skills
        # With empty spec requirements, should return empty dict
        spec = {"meta": {}, "requirements": [], "traceability": {"ac_mappings": []}}
        result = dispatch_skills(spec, {})
        assert isinstance(result, dict)

    def test_dispatch_skills_calls_registered_skill(self, tmp_path):
        from verify.skills.framework import (
            VerificationSkill, SKILL_REGISTRY, register_skill, dispatch_skills
        )

        output_file = str(tmp_path / "test_output.py")

        class MockSkill(VerificationSkill):
            skill_id = "mock_dispatch_skill"
            def generate(self, spec, requirement, constitution):
                return "# mock generated content"
            def output_path(self, spec, requirement):
                return output_file

        register_skill(MockSkill())

        spec = {
            "meta": {"jira_key": "TEST-001"},
            "requirements": [{
                "id": "REQ-001",
                "verification": [{
                    "skill": "mock_dispatch_skill",
                    "output": output_file,
                    "refs": ["success"],
                }],
                "contract": {},
            }],
            "traceability": {"ac_mappings": []},
        }

        result = dispatch_skills(spec, {})
        assert output_file in result
        assert "mock generated content" in result[output_file]
        assert os.path.exists(output_file)

        # Cleanup
        del SKILL_REGISTRY["mock_dispatch_skill"]

    def test_dispatch_skills_warns_on_missing_skill(self, tmp_path):
        from verify.skills.framework import dispatch_skills
        spec = {
            "meta": {"jira_key": "TEST-001"},
            "requirements": [{
                "id": "REQ-001",
                "verification": [{
                    "skill": "nonexistent_skill",
                    "output": str(tmp_path / "out.py"),
                    "refs": ["success"],
                }],
                "contract": {},
            }],
            "traceability": {"ac_mappings": []},
        }
        # Should not raise but should skip the missing skill
        result = dispatch_skills(spec, {})
        assert str(tmp_path / "out.py") not in result
