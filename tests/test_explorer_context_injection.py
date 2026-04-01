"""RED tests for P11.5: Inject Codebase Context into Negotiation Phases.

Tests that codebase index data is injected into phase system prompts
and that VerificationContext carries the index.
"""

import pytest
from verify.context import VerificationContext
from verify.explorer.detect import StackProfile
from verify.explorer.index import CodebaseIndex, EndpointInfo, ModelInfo
from verify.explorer.context_injection import (
    build_codebase_context_section,
    inject_codebase_into_constitution,
)


def _sample_index() -> CodebaseIndex:
    return CodebaseIndex(
        project_root="dog-service",
        endpoints=[
            EndpointInfo(method="GET", path="/api/v1/dogs", handler="DogController.list", file_path="DogController.java"),
            EndpointInfo(method="POST", path="/api/v1/dogs", handler="DogController.create", file_path="DogController.java"),
            EndpointInfo(method="GET", path="/api/v1/dogs/{id}", handler="DogController.getById", file_path="DogController.java"),
            EndpointInfo(method="DELETE", path="/api/v1/dogs/{id}", handler="DogController.delete", file_path="DogController.java"),
        ],
        models=[ModelInfo(class_name="Dog", fields=[{"name": "id"}, {"name": "name"}, {"name": "breed"}])],
    )


class TestBuildCodebaseContextSection:
    """build_codebase_context_section should format index for prompt injection."""

    def test_section_header(self):
        section = build_codebase_context_section(_sample_index())
        assert "## Codebase Context" in section

    def test_contains_endpoints(self):
        section = build_codebase_context_section(_sample_index())
        assert "/api/v1/dogs" in section

    def test_contains_models(self):
        section = build_codebase_context_section(_sample_index())
        assert "Dog" in section

    def test_empty_index_returns_empty(self):
        section = build_codebase_context_section(CodebaseIndex())
        assert section == ""

    def test_truncation(self):
        # Create a huge index
        endpoints = [
            EndpointInfo(method="GET", path=f"/api/v{i}/resource", handler=f"Ctrl.method{i}", file_path="C.java")
            for i in range(500)
        ]
        index = CodebaseIndex(project_root="huge", endpoints=endpoints)
        section = build_codebase_context_section(index, max_tokens=2000)
        assert "[truncated" in section
        assert len(section) < 20_000


class TestInjectCodebaseIntoConstitution:
    """inject_codebase_into_constitution merges index into constitution dict."""

    def test_injects_index(self):
        constitution = {"project": {"name": "dog-service"}}
        updated = inject_codebase_into_constitution(constitution, _sample_index())
        assert "_codebase_index" in updated
        assert "/api/v1/dogs" in updated["_codebase_index"]

    def test_original_not_mutated(self):
        constitution = {"project": {"name": "dog-service"}}
        updated = inject_codebase_into_constitution(constitution, _sample_index())
        assert "_codebase_index" not in constitution

    def test_no_index_no_change(self):
        constitution = {"project": {"name": "dog-service"}}
        updated = inject_codebase_into_constitution(constitution, None)
        assert "_codebase_index" not in updated


class TestVerificationContextCodebaseIndex:
    """VerificationContext should optionally carry codebase_index."""

    def test_context_without_index(self):
        ctx = VerificationContext(
            jira_key="TEST-1",
            jira_summary="test",
            raw_acceptance_criteria=[],
            constitution={},
        )
        # Should not fail — codebase_index is optional
        assert not hasattr(ctx, "codebase_index") or ctx.codebase_index is None

    def test_context_with_index(self):
        idx_dict = _sample_index().to_dict()
        ctx = VerificationContext(
            jira_key="TEST-1",
            jira_summary="test",
            raw_acceptance_criteria=[],
            constitution={},
            codebase_index=idx_dict,
        )
        assert ctx.codebase_index is not None
        assert ctx.codebase_index["endpoints"][0]["method"] == "GET"


class TestGracefulDegradation:
    """Phases should work normally when no index is provided."""

    def test_phase1_without_index(self):
        from verify.negotiation.phase1 import _build_constitution_context
        ctx_section = _build_constitution_context({"project": {"language": "java"}})
        assert "## Codebase Context" not in ctx_section

    def test_phase1_with_index(self):
        from verify.negotiation.phase1 import _build_constitution_context
        section = build_codebase_context_section(_sample_index())
        constitution = {"project": {"language": "java"}, "_codebase_index": section}
        ctx_section = _build_constitution_context(constitution)
        assert "/api/v1/dogs" in ctx_section
