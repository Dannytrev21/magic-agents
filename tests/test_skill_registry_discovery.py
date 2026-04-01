"""TDD coverage for ported skill registry discovery from claw-code."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from verify.negotiation.web import app


class TestSkillRegistryDiscovery:
    """Skill descriptors, search, and dispatch validation."""

    def test_builtin_skills_expose_descriptors(self):
        from verify.skills.framework import (
            SkillDescriptor,
            get_skill_descriptor,
        )

        descriptor = get_skill_descriptor("pytest_unit_test")

        assert isinstance(descriptor, SkillDescriptor)
        assert descriptor.skill_id == "pytest_unit_test"
        assert "api_behavior" in descriptor.input_types
        assert descriptor.framework == "pytest"
        assert descriptor.output_format == ".py"

    def test_duplicate_registration_raises(self):
        from verify.skills.framework import (
            SKILL_REGISTRY,
            VerificationSkill,
            register_skill,
        )

        class DuplicateSkill(VerificationSkill):
            skill_id = "duplicate_probe"
            name = "Duplicate Probe"
            description = "Used to verify duplicate skill detection."
            input_types = frozenset({"api_behavior"})
            output_format = ".txt"
            framework = "custom"
            version = "1.0.0"

            def generate(self, spec, requirement, constitution):
                return "probe"

            def output_path(self, spec, requirement):
                return ".verify/generated/duplicate_probe.txt"

        try:
            register_skill(DuplicateSkill())
            with pytest.raises(ValueError, match="duplicate"):
                register_skill(DuplicateSkill())
        finally:
            SKILL_REGISTRY.pop("duplicate_probe", None)

    def test_find_skills_matches_query_and_type(self):
        from verify.skills.framework import find_skills, find_skills_by_type

        query_results = find_skills("pytest")
        query_ids = [descriptor.skill_id for descriptor, _ in query_results]
        assert "pytest_unit_test" in query_ids

        type_results = find_skills_by_type("api_behavior")
        type_ids = [descriptor.skill_id for descriptor, _ in type_results]
        assert "pytest_unit_test" in type_ids
        assert "cucumber_java" in type_ids

    def test_validate_dispatch_reports_missing_and_incompatible_skills(self):
        from verify.skills.framework import validate_dispatch

        spec = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "type": "observability",
                    "verification": [{"skill": "pytest_unit_test"}],
                },
                {
                    "id": "REQ-002",
                    "type": "api_behavior",
                    "verification": [{"skill": "missing_skill"}],
                },
            ],
        }

        errors = validate_dispatch(spec)

        assert len(errors) == 2
        assert any("REQ-001" in error and "pytest_unit_test" in error for error in errors)
        assert any("REQ-002" in error and "missing_skill" in error for error in errors)

    def test_dispatch_skills_raises_on_invalid_bindings(self):
        from verify.skills.framework import SkillDispatchError, dispatch_skills

        spec = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "type": "observability",
                    "verification": [{"skill": "pytest_unit_test"}],
                },
            ],
        }

        with pytest.raises(SkillDispatchError, match="REQ-001"):
            dispatch_skills(spec, {})


class TestSkillRegistryEndpoint:
    """Read-only skill discovery for the web runtime."""

    def test_skills_endpoint_lists_registered_descriptors(self):
        client = TestClient(app)

        response = client.get("/api/skills")

        assert response.status_code == 200
        skills = response.json()
        assert isinstance(skills, list)
        assert any(skill["skill_id"] == "pytest_unit_test" for skill in skills)
        assert all("input_types" in skill for skill in skills)
        assert all("framework" in skill for skill in skills)
