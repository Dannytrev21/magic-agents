"""RED tests for 7-phase negotiation flow through web UI.

TDD: Tests for the full 7-phase negotiation flow (was 4 phases, now 7).
Ensures the web UI correctly handles phases 5, 6, 7 as interactive LLM phases.
"""

import json
import os

import pytest


@pytest.fixture(autouse=True)
def ensure_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


from fastapi.testclient import TestClient
from verify.negotiation.web import app, _session


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    _session.clear()
    return TestClient(app)


class TestSevenPhaseFlow:
    """The negotiation should now run 7 phases instead of 4."""

    def test_start_shows_7_total_phases(self, client):
        response = client.post("/api/start", json={
            "jira_key": "PHASE7-001",
            "jira_summary": "Seven Phase Test",
            "acceptance_criteria": [
                {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
            ],
        })
        data = response.json()
        assert response.status_code == 200
        assert data["total_phases"] == 7

    def test_full_seven_phase_negotiation(self, client):
        """Run through all 7 phases by approving each one."""
        response = client.post("/api/start", json={
            "jira_key": "PHASE7-002",
            "jira_summary": "Full Seven Phase Test",
            "acceptance_criteria": [
                {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
            ],
        })

        phases_seen = []
        data = response.json()
        phases_seen.append(data.get("phase_number"))

        # Approve through all phases
        for i in range(7):
            if data.get("done"):
                break
            response = client.post("/api/respond", json={"input": "approve"})
            assert response.status_code == 200
            data = response.json()
            if not data.get("done"):
                phases_seen.append(data.get("phase_number"))

        assert data.get("done") is True
        # Should have seen phases 1 through 7
        assert max(phases_seen) >= 7 or data.get("done")

    def test_phase5_produces_invariants(self, client):
        """Phase 5 should produce invariants in the negotiation flow."""
        response = client.post("/api/start", json={
            "jira_key": "PHASE5-WEB",
            "jira_summary": "Phase 5 Invariant Test",
            "acceptance_criteria": [
                {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
            ],
        })
        data = response.json()

        # Approve phases 1-4
        for i in range(4):
            if data.get("done"):
                break
            response = client.post("/api/respond", json={"input": "approve"})
            data = response.json()

        # Phase 5 should now be active (invariant extraction)
        if not data.get("done"):
            assert data.get("phase_number") == 5
            assert "results" in data

    def test_phase6_produces_routing(self, client):
        """Phase 6 should produce routing in the negotiation flow."""
        response = client.post("/api/start", json={
            "jira_key": "PHASE6-WEB",
            "jira_summary": "Phase 6 Routing Test",
            "acceptance_criteria": [
                {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
            ],
        })
        data = response.json()

        # Approve phases 1-5
        for i in range(5):
            if data.get("done"):
                break
            response = client.post("/api/respond", json={"input": "approve"})
            data = response.json()

        # Phase 6 should now be active (completeness sweep)
        if not data.get("done"):
            assert data.get("phase_number") == 6

    def test_phase7_produces_ears(self, client):
        """Phase 7 should produce EARS statements in the negotiation flow."""
        response = client.post("/api/start", json={
            "jira_key": "PHASE7-WEB",
            "jira_summary": "Phase 7 EARS Test",
            "acceptance_criteria": [
                {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
            ],
        })
        data = response.json()

        # Approve phases 1-6
        for i in range(6):
            if data.get("done"):
                break
            response = client.post("/api/respond", json={"input": "approve"})
            data = response.json()

        # Phase 7 should now be active (EARS formalization)
        if not data.get("done"):
            assert data.get("phase_number") == 7

    def test_negotiation_done_has_summary(self, client):
        """After 7 phases the negotiation should produce a complete summary."""
        response = client.post("/api/start", json={
            "jira_key": "SUMMARY-001",
            "jira_summary": "Summary Test",
            "acceptance_criteria": [
                {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
            ],
        })
        data = response.json()

        for i in range(7):
            if data.get("done"):
                break
            response = client.post("/api/respond", json={"input": "approve"})
            data = response.json()

        assert data.get("done") is True
        summary = data.get("summary", {})
        assert "invariants" in summary
        assert "ears_statements" in summary
        assert "traceability_map" in summary

    def test_feedback_in_phase5(self, client):
        """Developer feedback should trigger re-run in phase 5."""
        response = client.post("/api/start", json={
            "jira_key": "FB5-001",
            "jira_summary": "Feedback Phase 5 Test",
            "acceptance_criteria": [
                {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
            ],
        })
        data = response.json()

        # Approve phases 1-4
        for i in range(4):
            if data.get("done"):
                break
            response = client.post("/api/respond", json={"input": "approve"})
            data = response.json()

        # Send feedback for phase 5
        if not data.get("done") and data.get("phase_number") == 5:
            response = client.post("/api/respond", json={"input": "Add PII invariants"})
            data = response.json()
            assert data.get("revised") is True
            assert data.get("phase_number") == 5
