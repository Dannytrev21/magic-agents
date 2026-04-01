"""RED tests for P11.3: Auto-Generate Draft Constitution from Index.

Tests the constitution generator that produces a draft constitution.yaml
from a StackProfile and CodebaseIndex.
"""

import yaml
import pytest
from verify.explorer.detect import StackProfile
from verify.explorer.index import (
    CodebaseIndex, EndpointInfo, ModelInfo, SchemaInfo, TestPatternInfo,
)
from verify.explorer.constitution import ConstitutionDraft, generate_constitution


def _java_profile() -> StackProfile:
    return StackProfile(
        language="java", framework="spring-boot",
        build_tool="gradle", runtime_version="17", confidence=0.95,
    )


def _java_index() -> CodebaseIndex:
    return CodebaseIndex(
        project_root="dog-service",
        endpoints=[
            EndpointInfo(method="GET", path="/api/v1/dogs", handler="DogController.list", file_path="DogController.java"),
            EndpointInfo(method="POST", path="/api/v1/dogs", handler="DogController.create", file_path="DogController.java"),
        ],
        models=[ModelInfo(class_name="Dog", fields=[{"name": "id"}, {"name": "name"}], file_path="Dog.java")],
        schemas=[SchemaInfo(class_name="DogDto", fields=[{"name": "name"}], file_path="DogDto.java")],
        test_patterns=[TestPatternInfo(file_path="DogControllerTest.java", framework="webmvc-test")],
        config_files=["application.yaml"],
        directory_tree=["src", "build.gradle"],
    )


def _minimal_profile() -> StackProfile:
    return StackProfile(
        language="python", framework="unknown",
        build_tool="pip", runtime_version="", confidence=0.3,
    )


def _minimal_index() -> CodebaseIndex:
    return CodebaseIndex(project_root="/tmp/minimal")


class TestConstitutionDraft:
    """ConstitutionDraft should carry generated YAML and metadata."""

    def test_draft_fields(self):
        draft = ConstitutionDraft(
            yaml_content="project:\n  name: test",
            todo_count=3,
            sections_populated=["project"],
        )
        assert "project" in draft.yaml_content
        assert draft.todo_count == 3
        assert "project" in draft.sections_populated


class TestGeneratesValidYAML:
    """Generated constitution must be valid YAML matching the schema."""

    def test_generates_valid_yaml(self):
        draft = generate_constitution(_java_profile(), _java_index())
        parsed = yaml.safe_load(draft.yaml_content)
        assert isinstance(parsed, dict)
        assert "project" in parsed

    def test_project_section(self):
        draft = generate_constitution(_java_profile(), _java_index())
        parsed = yaml.safe_load(draft.yaml_content)
        assert parsed["project"]["language"] == "java"
        assert parsed["project"]["framework"] == "spring-boot"
        assert parsed["project"]["build_tool"] == "gradle"
        assert parsed["project"]["name"] == "dog-service"

    def test_source_structure_section(self):
        draft = generate_constitution(_java_profile(), _java_index())
        parsed = yaml.safe_load(draft.yaml_content)
        assert "source_structure" in parsed

    def test_testing_section(self):
        draft = generate_constitution(_java_profile(), _java_index())
        parsed = yaml.safe_load(draft.yaml_content)
        assert "testing" in parsed
        assert parsed["testing"]["unit_framework"] is not None

    def test_api_section(self):
        draft = generate_constitution(_java_profile(), _java_index())
        parsed = yaml.safe_load(draft.yaml_content)
        assert "api" in parsed
        assert parsed["api"]["style"] == "rest"

    def test_verification_standards_section(self):
        draft = generate_constitution(_java_profile(), _java_index())
        parsed = yaml.safe_load(draft.yaml_content)
        assert "verification_standards" in parsed


class TestTodoMarkers:
    """Unknown fields should get TODO markers."""

    def test_todo_markers_for_minimal(self):
        draft = generate_constitution(_minimal_profile(), _minimal_index())
        assert draft.todo_count > 0
        assert "# TODO: verify" in draft.yaml_content

    def test_sections_populated_list(self):
        draft = generate_constitution(_java_profile(), _java_index())
        assert "project" in draft.sections_populated
        assert "testing" in draft.sections_populated
        assert "api" in draft.sections_populated


class TestNoOverwrite:
    """Existing constitution files should never be silently overwritten."""

    def test_no_overwrite_existing(self, tmp_path):
        existing = tmp_path / "constitution.yaml"
        existing.write_text("project:\n  name: existing")
        draft = generate_constitution(
            _java_profile(), _java_index(), output_path=str(existing),
        )
        # Should NOT have overwritten
        assert existing.read_text().startswith("project:\n  name: existing")
        # But should still return the draft
        assert "dog-service" in draft.yaml_content

    def test_writes_to_new_path(self, tmp_path):
        output = tmp_path / "new_constitution.yaml"
        draft = generate_constitution(
            _java_profile(), _java_index(), output_path=str(output),
        )
        assert output.exists()
        parsed = yaml.safe_load(output.read_text())
        assert parsed["project"]["language"] == "java"


class TestDeterministic:
    """Same inputs should produce same output."""

    def test_deterministic(self):
        d1 = generate_constitution(_java_profile(), _java_index())
        d2 = generate_constitution(_java_profile(), _java_index())
        assert d1.yaml_content == d2.yaml_content
        assert d1.todo_count == d2.todo_count


class TestRoundtripDogService:
    """Integration test with real repo detection."""

    def test_roundtrip_dog_service(self):
        from verify.explorer.detect import detect_stack
        from verify.explorer.index import build_codebase_index

        profile = detect_stack("dog-service")
        index = build_codebase_index(profile, "dog-service")
        draft = generate_constitution(profile, index)
        parsed = yaml.safe_load(draft.yaml_content)
        assert parsed["project"]["name"] == "dog-service"
        assert parsed["project"]["language"] == "java"
        assert parsed["project"]["framework"] == "spring-boot"
