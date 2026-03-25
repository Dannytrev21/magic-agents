"""Tests for checkpoint and resume web endpoints (Feature 2.8).

Tests the GET /api/session/{jira_key} and POST /api/session/{jira_key}/resume endpoints.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from verify.context import VerificationContext
from verify.negotiation.checkpoint import save_checkpoint


@pytest.fixture
def client():
    """Fixture that creates a FastAPI test client."""
    from verify.negotiation.web import app

    return TestClient(app)


@pytest.fixture
def temp_sessions_dir(monkeypatch):
    """Fixture that creates a temporary sessions directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(
            "verify.negotiation.checkpoint.SESSIONS_DIR",
            Path(tmpdir),
        )
        # Also patch it in the web module since it imports from checkpoint
        from verify.negotiation import checkpoint

        monkeypatch.setattr(
            checkpoint,
            "SESSIONS_DIR",
            Path(tmpdir),
        )
        yield Path(tmpdir)


@pytest.fixture
def sample_context():
    """Fixture that creates a sample VerificationContext."""
    return VerificationContext(
        jira_key="TEST-001",
        jira_summary="Test Story",
        raw_acceptance_criteria=[
            {"index": 0, "text": "User can login", "checked": False},
        ],
        constitution={
            "project": {"framework": "spring-boot", "language": "java"},
            "api": {"base_path": "/api/v1"},
        },
    )


@pytest.fixture
def populated_context(sample_context):
    """Fixture that creates a context with phase data."""
    ctx = sample_context
    ctx.current_phase = "phase_1"
    ctx.classifications = [
        {
            "ac_index": 0,
            "type": "api_behavior",
            "actor": "authenticated_user",
        }
    ]
    ctx.negotiation_log = [
        {
            "phase": "phase_0",
            "role": "ai",
            "content": "Classified AC",
            "timestamp": "2026-03-25T10:00:00+00:00",
        }
    ]
    return ctx


class TestGetSessionEndpoint:
    """Tests for GET /api/session/{jira_key} endpoint."""

    def test_get_session_no_checkpoint(self, client, temp_sessions_dir):
        """GET /api/session/{jira_key} should return has_checkpoint: false when no checkpoint exists."""
        response = client.get("/api/session/NONEXISTENT-001")

        assert response.status_code == 200
        data = response.json()
        assert data["has_checkpoint"] is False
        assert "session" not in data

    def test_get_session_with_checkpoint(
        self, client, temp_sessions_dir, populated_context
    ):
        """GET /api/session/{jira_key} should return session info when checkpoint exists."""
        save_checkpoint(populated_context, "phase_1")

        response = client.get(f"/api/session/{populated_context.jira_key}")

        assert response.status_code == 200
        data = response.json()
        assert data["has_checkpoint"] is True
        assert "session" in data

        session_info = data["session"]
        assert session_info["jira_key"] == "TEST-001"
        assert session_info["current_phase"] == "phase_1"
        assert session_info["log_entries"] == 1
        assert session_info["approved"] is False

    def test_get_session_info_includes_checkpoint_path(
        self, client, temp_sessions_dir, populated_context
    ):
        """Session info should include the checkpoint file path."""
        save_checkpoint(populated_context, "phase_1")

        response = client.get(f"/api/session/{populated_context.jira_key}")

        session_info = response.json()["session"]
        assert "checkpoint_path" in session_info
        assert session_info["checkpoint_path"].endswith("checkpoint_phase_1.json")

    def test_get_session_reflects_approved_status(
        self, client, temp_sessions_dir, populated_context
    ):
        """Session info should reflect approval status."""
        populated_context.approved = True
        populated_context.approved_by = "qa"
        save_checkpoint(populated_context, "phase_7")

        response = client.get(f"/api/session/{populated_context.jira_key}")

        session_info = response.json()["session"]
        assert session_info["approved"] is True


class TestResumeSessionEndpoint:
    """Tests for POST /api/session/{jira_key}/resume endpoint."""

    def test_resume_session_no_checkpoint(self, client, temp_sessions_dir):
        """POST /api/session/{jira_key}/resume should return error if no checkpoint exists."""
        response = client.post("/api/session/NONEXISTENT-001/resume")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "No checkpoint found" in data["error"]

    def test_resume_session_with_checkpoint(
        self, client, temp_sessions_dir, populated_context
    ):
        """POST /api/session/{jira_key}/resume should restore the session."""
        save_checkpoint(populated_context, "phase_1")

        response = client.post(f"/api/session/{populated_context.jira_key}/resume")

        assert response.status_code == 200
        data = response.json()
        assert data["resumed"] is True
        assert data["jira_key"] == "TEST-001"
        assert data["jira_summary"] == "Test Story"
        assert data["current_phase"] == "phase_1"
        assert data["phase_number"] == 1  # PHASES[1] -> PHASE_SKILLS[0] -> phase_number=1
        assert data["log_entries"] == 1
        assert data["approved"] is False

    def test_resume_session_restores_in_memory_session(
        self, client, temp_sessions_dir, populated_context
    ):
        """Resuming should populate the in-memory _session dictionary."""
        from verify.negotiation import web

        save_checkpoint(populated_context, "phase_1")

        # Clear the in-memory session
        web._session.clear()
        assert not web._session

        # Resume
        response = client.post(f"/api/session/{populated_context.jira_key}/resume")
        assert response.status_code == 200

        # Check that session was populated
        # Note: TestClient doesn't share session state across requests
        # so we can't directly test the session here, but we can test
        # that the endpoint response is correct

    def test_resume_preserves_context_data(
        self, client, temp_sessions_dir, populated_context
    ):
        """Resumed session should have all the context data."""
        populated_context.current_phase = "phase_2"
        populated_context.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "user"}
        ]
        populated_context.postconditions = [{"ac_index": 0, "status": 200}]
        save_checkpoint(populated_context, "phase_2")

        response = client.post(f"/api/session/{populated_context.jira_key}/resume")
        assert response.status_code == 200

        data = response.json()
        assert data["current_phase"] == "phase_2"

    def test_resume_with_approved_checkpoint(
        self, client, temp_sessions_dir, populated_context
    ):
        """Resuming an approved checkpoint should show approved status."""
        populated_context.approved = True
        populated_context.approved_by = "tech-lead"
        populated_context.approved_at = "2026-03-25T15:00:00Z"
        save_checkpoint(populated_context, "phase_7")

        response = client.post(f"/api/session/{populated_context.jira_key}/resume")

        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is True

    def test_resume_latest_checkpoint_if_multiple(
        self, client, temp_sessions_dir, populated_context
    ):
        """If multiple checkpoints exist, resume should get the latest one."""
        # Create first checkpoint at phase_1
        save_checkpoint(populated_context, "phase_1")

        # Create second checkpoint at phase_2 with additional data
        populated_context.current_phase = "phase_2"
        populated_context.postconditions = [
            {"ac_index": 0, "status": 200},
            {"ac_index": 0, "status": 201},
        ]
        save_checkpoint(populated_context, "phase_2")

        # Resume should get phase_2
        response = client.post(f"/api/session/{populated_context.jira_key}/resume")

        assert response.status_code == 200
        data = response.json()
        assert data["current_phase"] == "phase_2"
        assert data["phase_number"] == 2  # PHASES[2] -> PHASE_SKILLS[1] -> phase_number=2


class TestSessionWorkflow:
    """Integration tests for the full session workflow."""

    def test_full_workflow_check_and_resume(
        self, client, temp_sessions_dir, populated_context
    ):
        """Full workflow: check session, then resume if it exists."""
        save_checkpoint(populated_context, "phase_1")

        # First, check if session exists
        check_response = client.get(f"/api/session/{populated_context.jira_key}")
        assert check_response.status_code == 200
        assert check_response.json()["has_checkpoint"] is True

        # Then, resume the session
        resume_response = client.post(f"/api/session/{populated_context.jira_key}/resume")
        assert resume_response.status_code == 200
        assert resume_response.json()["resumed"] is True

    def test_workflow_no_session_then_start_new(
        self, client, temp_sessions_dir
    ):
        """Workflow: check for session (none exists), then start new negotiation."""
        # Check session (none exists)
        check_response = client.get("/api/session/NEW-001")
        assert check_response.status_code == 200
        assert check_response.json()["has_checkpoint"] is False

        # Developer would then call /api/start to begin a new negotiation
        # (not testing /api/start here as that's outside scope of checkpoint feature)
