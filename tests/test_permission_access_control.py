"""TDD tests for P05: Permission & Access Control.

Ported from claw-code's permission system. Tests cover:
- P5.1: ToolPermissionContext & PermissionDenial data models
- P5.2: Skill filtering by permission context
- P5.3: Permission-aware web endpoints
- P5.4: Constitution-driven permission defaults
"""

import os
import pytest

os.environ["LLM_MOCK"] = "true"

from verify.negotiation.web import SESSION_STORE, SCAN_STATE


@pytest.fixture(autouse=True)
def clean_web_state():
    """Reset shared web state before and after each test."""
    SESSION_STORE.clear()
    SCAN_STATE["project_root"] = ""
    SCAN_STATE["scanned"] = False
    SCAN_STATE["summary"] = ""
    yield
    SESSION_STORE.clear()


# ── P5.1: Data Models ──────────────────────────────────────────────────


class TestToolPermissionContext:
    """ToolPermissionContext: frozen dataclass with deny_names, deny_prefixes."""

    def test_importable(self):
        from verify.permissions import ToolPermissionContext
        assert ToolPermissionContext is not None

    def test_frozen_dataclass(self):
        from verify.permissions import ToolPermissionContext
        ctx = ToolPermissionContext(
            deny_names=frozenset({"pytest_unit_test"}),
            deny_prefixes=("mcp_",),
        )
        with pytest.raises(AttributeError):
            ctx.deny_names = frozenset()

    def test_from_iterables(self):
        from verify.permissions import ToolPermissionContext
        ctx = ToolPermissionContext.from_iterables(
            deny_names=["pytest_unit_test", "cucumber_java"],
            deny_prefixes=["mcp_", "debug_"],
        )
        assert isinstance(ctx.deny_names, frozenset)
        assert isinstance(ctx.deny_prefixes, tuple)
        assert "pytest_unit_test" in ctx.deny_names
        assert "mcp_" in ctx.deny_prefixes

    def test_blocks_exact_name(self):
        from verify.permissions import ToolPermissionContext
        ctx = ToolPermissionContext(
            deny_names=frozenset({"blocked_skill"}),
            deny_prefixes=(),
        )
        assert ctx.blocks("blocked_skill") is True
        assert ctx.blocks("allowed_skill") is False

    def test_blocks_case_insensitive(self):
        from verify.permissions import ToolPermissionContext
        ctx = ToolPermissionContext(
            deny_names=frozenset({"blocked_skill"}),
            deny_prefixes=(),
        )
        assert ctx.blocks("BLOCKED_SKILL") is True
        assert ctx.blocks("Blocked_Skill") is True

    def test_blocks_by_prefix(self):
        from verify.permissions import ToolPermissionContext
        ctx = ToolPermissionContext(
            deny_names=frozenset(),
            deny_prefixes=("mcp_", "debug_"),
        )
        assert ctx.blocks("mcp_server_tool") is True
        assert ctx.blocks("debug_profiler") is True
        assert ctx.blocks("pytest_unit_test") is False

    def test_blocks_prefix_case_insensitive(self):
        from verify.permissions import ToolPermissionContext
        ctx = ToolPermissionContext(
            deny_names=frozenset(),
            deny_prefixes=("mcp_",),
        )
        assert ctx.blocks("MCP_tool") is True

    def test_empty_context_blocks_nothing(self):
        from verify.permissions import ToolPermissionContext
        ctx = ToolPermissionContext(
            deny_names=frozenset(),
            deny_prefixes=(),
        )
        assert ctx.blocks("any_tool") is False


class TestPermissionDenial:
    """PermissionDenial: frozen dataclass for denial events."""

    def test_importable(self):
        from verify.permissions import PermissionDenial
        assert PermissionDenial is not None

    def test_frozen_dataclass(self):
        from verify.permissions import PermissionDenial
        denial = PermissionDenial(
            tool_name="pytest_unit_test",
            reason="Blocked by operator policy",
        )
        assert denial.tool_name == "pytest_unit_test"
        assert denial.reason == "Blocked by operator policy"
        with pytest.raises(AttributeError):
            denial.tool_name = "other"


# ── P5.2: Skill Filtering ──────────────────────────────────────────────


class TestSkillFiltering:
    """filter_skills_by_permission and dispatch integration."""

    def test_filter_skills_by_permission_exists(self):
        from verify.permissions import filter_skills_by_permission
        assert callable(filter_skills_by_permission)

    def test_filter_removes_blocked_skills(self):
        from verify.permissions import ToolPermissionContext, filter_skills_by_permission
        from verify.skills.framework import SKILL_REGISTRY

        ctx = ToolPermissionContext(
            deny_names=frozenset({"pytest_unit_test"}),
            deny_prefixes=(),
        )
        filtered = filter_skills_by_permission(SKILL_REGISTRY, ctx)
        assert "pytest_unit_test" not in filtered
        assert "cucumber_java" in filtered

    def test_filter_removes_by_prefix(self):
        from verify.permissions import ToolPermissionContext, filter_skills_by_permission
        from verify.skills.framework import SKILL_REGISTRY

        ctx = ToolPermissionContext(
            deny_names=frozenset(),
            deny_prefixes=("cucumber_",),
        )
        filtered = filter_skills_by_permission(SKILL_REGISTRY, ctx)
        assert "cucumber_java" not in filtered
        assert "pytest_unit_test" in filtered

    def test_filter_with_none_returns_all(self):
        from verify.permissions import filter_skills_by_permission
        from verify.skills.framework import SKILL_REGISTRY

        filtered = filter_skills_by_permission(SKILL_REGISTRY, None)
        assert filtered == SKILL_REGISTRY

    def test_dispatch_with_permission_context_skips_blocked(self):
        from verify.permissions import ToolPermissionContext, PermissionDenial
        from verify.permissions import dispatch_skills_with_permissions

        ctx = ToolPermissionContext(
            deny_names=frozenset({"pytest_unit_test"}),
            deny_prefixes=(),
        )
        spec = {
            "meta": {"jira_key": "PERM-001"},
            "requirements": [
                {
                    "id": "REQ-001",
                    "type": "api_behavior",
                    "verification": [{"skill": "pytest_unit_test", "output": "/tmp/test_perm.py"}],
                    "contract": {},
                },
            ],
        }

        files, denials = dispatch_skills_with_permissions(spec, {}, ctx)
        assert len(files) == 0
        assert len(denials) == 1
        assert denials[0].tool_name == "pytest_unit_test"


# ── P5.3: Web Endpoints ────────────────────────────────────────────────


class TestPermissionWebEndpoints:
    """Permission-aware web API endpoints."""

    def test_get_permissions_endpoint_exists(self):
        from verify.negotiation.web import app
        routes = [r.path for r in app.routes]
        assert "/api/permissions" in routes

    def _start_session_and_get_client(self):
        from fastapi.testclient import TestClient
        from verify.negotiation.web import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/start", json={
            "jira_key": "PERM-TEST",
            "jira_summary": "Permission test",
            "acceptance_criteria": [{"index": 0, "text": "AC", "checked": False}],
        })
        if resp.status_code != 200:
            pytest.skip(f"Could not start session: {resp.status_code}")
        return client

    def test_get_permissions_returns_defaults(self):
        client = self._start_session_and_get_client()
        response = client.get("/api/permissions")
        assert response.status_code == 200
        data = response.json()
        assert "deny_names" in data
        assert "deny_prefixes" in data

    def test_set_permissions(self):
        client = self._start_session_and_get_client()
        response = client.post("/api/permissions", json={
            "deny_names": ["pytest_unit_test"],
            "deny_prefixes": ["debug_"],
        })
        assert response.status_code == 200

        # Verify it persists
        response = client.get("/api/permissions")
        data = response.json()
        assert "pytest_unit_test" in data["deny_names"]

    def test_get_denials_empty_initially(self):
        client = self._start_session_and_get_client()
        response = client.get("/api/permissions/denials")
        assert response.status_code == 200
        data = response.json()
        assert data["denials"] == []


# ── P5.4: Constitution Defaults ─────────────────────────────────────────


class TestConstitutionPermissionDefaults:
    """Constitution-driven permission defaults."""

    def test_permission_context_from_constitution(self):
        from verify.permissions import ToolPermissionContext

        constitution = {
            "permissions": {
                "deny_skills": ["debug_inspector"],
                "deny_prefixes": ["experimental_"],
            },
        }
        ctx = ToolPermissionContext.from_constitution(constitution)
        assert ctx.blocks("debug_inspector") is True
        assert ctx.blocks("experimental_probe") is True
        assert ctx.blocks("pytest_unit_test") is False

    def test_empty_constitution_returns_empty_context(self):
        from verify.permissions import ToolPermissionContext

        ctx = ToolPermissionContext.from_constitution({})
        assert ctx.blocks("anything") is False

    def test_missing_permissions_section_returns_empty(self):
        from verify.permissions import ToolPermissionContext

        ctx = ToolPermissionContext.from_constitution({"project": {"name": "test"}})
        assert ctx.blocks("anything") is False
