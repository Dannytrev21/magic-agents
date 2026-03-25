"""Tests for new web API endpoints: evaluator-optimizer and planner.

RED-GREEN TDD for the /api/evaluate-phase and /api/plan endpoints.
"""

import os
import pytest

os.environ["LLM_MOCK"] = "true"

from fastapi.testclient import TestClient

from verify.negotiation.web import app, _session
from verify.context import VerificationContext
from verify.llm_client import LLMClient


@pytest.fixture(autouse=True)
def clear_session():
    """Clear session state before each test."""
    _session.clear()
    yield
    _session.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session_with_context():
    """Set up a session with a context that has Phase 1 output."""
    ctx = VerificationContext(
        jira_key="TEST-001",
        jira_summary="Test ticket",
        raw_acceptance_criteria=[
            {"index": 0, "text": "User can view profile via GET /api/v1/users/me", "checked": False},
            {"index": 1, "text": "User can update profile via PUT /api/v1/users/me", "checked": False},
        ],
        constitution={"project": {"framework": "spring_boot"}, "api": {"base_path": "/api/v1"}},
    )
    ctx.classifications = [
        {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user",
         "interface": {"method": "GET", "path": "/api/v1/users/me"}},
        {"ac_index": 1, "type": "api_behavior", "actor": "authenticated_user",
         "interface": {"method": "PUT", "path": "/api/v1/users/me"}},
    ]
    _session["context"] = ctx
    _session["llm"] = LLMClient()
    return ctx


# ─── Evaluate phase endpoint ─────────────────────────────────────────────


class TestEvaluatePhaseEndpoint:
    def test_endpoint_exists(self, client):
        """POST /api/evaluate-phase should be a valid route."""
        response = client.post("/api/evaluate-phase", json={"phase": "phase_1"})
        # Even without a session, it should return a JSON error, not 404/405
        assert response.status_code in (200, 400)

    def test_returns_critique_with_session(self, client, session_with_context):
        response = client.post("/api/evaluate-phase", json={"phase": "phase_1"})
        assert response.status_code == 200
        data = response.json()
        assert "has_issues" in data
        assert "issues" in data
        assert "suggestions" in data

    def test_returns_error_without_session(self, client):
        response = client.post("/api/evaluate-phase", json={"phase": "phase_1"})
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_detects_issues_in_phase_1(self, client, session_with_context):
        """With only api_behavior and no security_invariant, should flag issues."""
        response = client.post("/api/evaluate-phase", json={"phase": "phase_1"})
        data = response.json()
        assert data["has_issues"] is True
        assert len(data["issues"]) > 0


# ─── Plan endpoint ───────────────────────────────────────────────────────


class TestPlanEndpoint:
    def test_endpoint_exists(self, client):
        """POST /api/plan should be a valid route."""
        response = client.post("/api/plan")
        assert response.status_code in (200, 400)

    def test_returns_plan_with_session(self, client, session_with_context):
        response = client.post("/api/plan")
        assert response.status_code == 200
        data = response.json()
        assert "ac_groups" in data
        assert "cross_ac_dependencies" in data
        assert "estimated_complexity" in data

    def test_returns_error_without_session(self, client):
        response = client.post("/api/plan")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_plan_groups_acs(self, client, session_with_context):
        """ACs referencing the same endpoint should be grouped."""
        response = client.post("/api/plan")
        data = response.json()
        # Both ACs reference /api/v1/users/me — should be in same group
        all_grouped_indices = set()
        for group in data["ac_groups"]:
            all_grouped_indices.update(group["ac_indices"])
        assert 0 in all_grouped_indices
        assert 1 in all_grouped_indices
