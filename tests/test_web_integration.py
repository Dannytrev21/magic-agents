"""RED tests for web endpoint integration: SSE streaming, EARS approval, pipeline flow.

TDD: Write these tests FIRST (RED), then implement if any fail (GREEN).
"""

import json
import os

import pytest


@pytest.fixture(autouse=True)
def ensure_mock_mode(monkeypatch):
    """Ensure LLM_MOCK is set for all tests in this module."""
    monkeypatch.setenv("LLM_MOCK", "true")


from fastapi.testclient import TestClient
from verify.negotiation.web import app, _session, SCAN_STATE


@pytest.fixture
def client(monkeypatch):
    """Create a test client and clear session state."""
    monkeypatch.setenv("LLM_MOCK", "true")
    _session.clear()
    SCAN_STATE["project_root"] = ""
    SCAN_STATE["scanned"] = False
    SCAN_STATE["summary"] = ""
    return TestClient(app)


@pytest.fixture
def negotiated_session(client, monkeypatch):
    """Run a full negotiation to populate session state."""
    monkeypatch.setenv("LLM_MOCK", "true")
    # Start negotiation
    response = client.post("/api/start", json={
        "jira_key": "TEST-WEB",
        "jira_summary": "Web Integration Test",
        "acceptance_criteria": [
            {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
        ],
    })
    assert response.status_code == 200

    # Approve all 7 phases
    for i in range(7):
        data = response.json()
        if data.get("done"):
            break
        response = client.post("/api/respond", json={"input": "approve"})
        assert response.status_code == 200

    return response.json()


class TestStartNegotiation:
    """Tests for /api/start endpoint."""

    def test_start_returns_first_phase(self, client):
        response = client.post("/api/start", json={
            "jira_key": "START-001",
            "jira_summary": "Test",
            "acceptance_criteria": [
                {"index": 0, "text": "Test AC", "checked": False},
            ],
        })
        data = response.json()
        assert response.status_code == 200
        assert data["done"] is False
        assert data["phase_number"] == 1
        assert data["total_phases"] == 7

    def test_start_returns_structured_phase_payload_for_workspace(self, client):
        response = client.post("/api/start", json={
            "jira_key": "SURFACE-001",
            "jira_summary": "Workspace review surface",
            "acceptance_criteria": [
                {"index": 0, "text": "Operator can review typed phase output", "checked": False},
            ],
        })
        data = response.json()

        assert response.status_code == 200
        assert data["classifications"] == data["results"]
        assert isinstance(data["questions"], list)
        assert data["postconditions"] == []
        assert data["preconditions"] == []
        assert data["failure_modes"] == []
        assert data["invariants"] == []
        assert data["verification_routing"] == {}
        assert data["ears_statements"] == []
        assert data["traceability_map"] == {}
        assert len(data["negotiation_log"]) >= 1
        assert data["negotiation_log"][-1]["role"] == "ai"
        assert len(data["session_events"]) >= 1
        assert data["session_events"][0]["title"] == "session_created"
        assert "timestamp" in data["session_events"][0]

    def test_start_with_constitution(self, client):
        response = client.post("/api/start", json={
            "jira_key": "CONST-001",
            "jira_summary": "Constitution Test",
            "acceptance_criteria": [
                {"index": 0, "text": "AC", "checked": False},
            ],
            "constitution": {
                "project": {"framework": "fastapi", "language": "python"},
                "api": {"base_path": "/api/v2"},
            },
        })
        assert response.status_code == 200


class TestNegotiationFlow:
    """Tests for the approve/feedback negotiation flow."""

    def test_approve_advances_phase(self, client):
        client.post("/api/start", json={
            "jira_key": "ADV-001",
            "jira_summary": "Advance Test",
            "acceptance_criteria": [
                {"index": 0, "text": "Test AC", "checked": False},
            ],
        })

        response = client.post("/api/respond", json={"input": "approve"})
        data = response.json()
        assert response.status_code == 200
        # Should be phase 2 or done
        assert data.get("phase_number", 0) >= 2 or data.get("done")

    def test_feedback_reruns_phase(self, client):
        client.post("/api/start", json={
            "jira_key": "FB-001",
            "jira_summary": "Feedback Test",
            "acceptance_criteria": [
                {"index": 0, "text": "Test AC", "checked": False},
            ],
        })

        response = client.post("/api/respond", json={
            "input": "The classification should be security_invariant",
        })
        data = response.json()
        assert response.status_code == 200
        assert data.get("revised") is True
        assert data["phase_number"] == 1  # Still on phase 1

    def test_approve_keeps_transcript_and_phase_context_in_place(self, client):
        client.post("/api/start", json={
            "jira_key": "ADV-CTX-001",
            "jira_summary": "Advance with transcript",
            "acceptance_criteria": [
                {"index": 0, "text": "Operator can approve the active phase", "checked": False},
            ],
        })

        response = client.post("/api/respond", json={"input": "approve"})
        data = response.json()

        assert response.status_code == 200
        assert data["phase_number"] == 2
        assert len(data["postconditions"]) >= 1
        assert any(entry["role"] == "human" for entry in data["negotiation_log"])
        assert any(entry["role"] == "ai" for entry in data["negotiation_log"])

    def test_full_negotiation_produces_summary(self, negotiated_session):
        data = negotiated_session
        assert data["done"] is True
        assert "summary" in data
        assert data["summary"]["jira_key"] == "TEST-WEB"
        assert data["summary"]["counts"]["classifications"] >= 1
        assert len(data["summary"]["ears_statements"]) >= 1


class TestEARSApprovalGate:
    """Tests for Feature 7: EARS Statement Summary + Approval Gate."""

    def test_ears_approve_endpoint(self, client):
        """EARS approval should set context.approved with metadata."""
        # Need a session first
        client.post("/api/start", json={
            "jira_key": "EARS-001",
            "jira_summary": "EARS Test",
            "acceptance_criteria": [
                {"index": 0, "text": "Test AC", "checked": False},
            ],
        })
        # Run through all phases
        for _ in range(4):
            client.post("/api/respond", json={"input": "approve"})

        # Now approve EARS
        response = client.post("/api/ears-approve", json={
            "approved_by": "test_developer",
        })
        data = response.json()
        assert response.status_code == 200
        assert data["approved"] is True
        assert data["approved_by"] == "test_developer"
        assert "approved_at" in data

    def test_ears_approve_no_session(self, client):
        """EARS approval without a session should return 400."""
        response = client.post("/api/ears-approve", json={})
        assert response.status_code == 400


class TestCompileEndpoint:
    """Tests for /api/compile endpoint."""

    def test_compile_after_negotiation(self, client, negotiated_session):
        """Compile should produce a spec file after negotiation."""
        # Approve EARS first
        client.post("/api/ears-approve", json={"approved_by": "tester"})

        response = client.post("/api/compile")
        data = response.json()
        assert response.status_code == 200
        assert "spec_path" in data
        assert "spec_content" in data
        assert "TEST-WEB" in data["spec_content"]

    def test_compile_requires_ears_approval(self, client, negotiated_session):
        response = client.post("/api/compile")

        assert response.status_code == 400
        assert "Approve EARS" in response.json()["error"]

    def test_compile_no_session(self, client):
        response = client.post("/api/compile")
        assert response.status_code == 400


class TestSpecDiffEndpoint:
    """Tests for Feature 17: Spec Diff."""

    def test_spec_diff_no_old_spec(self, client, negotiated_session):
        """Spec diff with no prior spec should indicate 'new spec'."""
        response = client.post("/api/spec-diff")
        data = response.json()
        assert response.status_code == 200
        # Either has_old_spec is False or we get an error about spec path
        if "has_old_spec" in data:
            assert data["jira_key"] == "TEST-WEB"


class TestSSEStreamingPipeline:
    """Tests for Feature 11: SSE Streaming for Pipeline Execution."""

    def test_stream_pipeline_endpoint_exists(self, client):
        """The streaming pipeline endpoint should exist."""
        routes = [r.path for r in app.routes]
        assert "/api/pipeline/stream" in routes

    def test_stream_pipeline_no_session(self, client):
        """Streaming without a session should return error."""
        response = client.post("/api/pipeline/stream")
        assert response.status_code == 400

    def test_stream_pipeline_requires_ears_approval(self, client, negotiated_session):
        response = client.post("/api/pipeline/stream")

        assert response.status_code == 400
        assert "Approve EARS" in response.json()["error"]

    def test_stream_pipeline_emits_step_events_after_approval(
        self, client, negotiated_session, monkeypatch, tmp_path
    ):
        client.post("/api/ears-approve", json={"approved_by": "test_developer"})

        spec_path = tmp_path / "TEST-WEB.yaml"
        spec_path.write_text(
            "requirements:\n"
            "  - id: REQ-001\n"
            "    verification:\n"
            "      - output: tests/test_generated.py\n"
            "traceability:\n"
            "  ac_mappings:\n"
            "    - ac_checkbox: 0\n"
            "      ac_text: User can view their profile via GET /api/v1/users/me\n"
            "      pass_condition: ALL_PASS\n"
            "      required_verifications:\n"
            "        - ref: REQ-001.success\n"
            "          verification_type: test_result\n"
        )
        test_path = tmp_path / "test_generated.py"
        test_path.write_text("def test_generated():\n    assert True\n")

        monkeypatch.setattr(
            "verify.compiler.compile_and_write",
            lambda ctx, output_dir="specs": str(spec_path),
        )
        monkeypatch.setattr(
            "verify.generator.generate_and_write",
            lambda compiled_spec_path: str(test_path),
        )
        monkeypatch.setattr(
            "verify.runner.run_and_parse",
            lambda generated_test_path, results_dir: {
                "test_cases": [
                    {
                        "name": "test_generated",
                        "status": "passed",
                        "tags": ["REQ-001.success"],
                    }
                ]
            },
        )
        monkeypatch.setattr(
            "verify.evaluator.evaluate_spec",
            lambda compiled_spec_path, results: [
                {
                    "ac_checkbox": 0,
                    "ac_text": "User can view their profile via GET /api/v1/users/me",
                    "passed": True,
                    "summary": "1/1 verifications passed",
                    "evidence": [
                        {
                            "ref": "REQ-001.success",
                            "verification_type": "test_result",
                            "passed": True,
                            "details": "Test 'test_generated' passed",
                        }
                    ],
                }
            ],
        )

        response = client.post("/api/pipeline/stream")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = [
            json.loads(line[6:])
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]

        assert any(
            event.get("type") == "step"
            and event.get("step") == "compile"
            and event.get("status") in {"done", "skipped"}
            for event in events
        )
        assert any(
            event.get("type") == "step"
            and event.get("step") == "generate"
            and event.get("status") == "done"
            for event in events
        )
        assert events[-1]["type"] == "done"
        assert events[-1]["all_passed"] is True


class TestScanEndpoint:
    """Tests for Feature 8: Codebase Pre-Scanner."""

    def test_scan_endpoint_exists(self, client):
        routes = [r.path for r in app.routes]
        assert "/api/scan" in routes

    def test_scan_status_default(self, client):
        response = client.get("/api/scan/status")
        data = response.json()
        assert data["scanned"] is False


class TestConstitutionEndpoints:
    """Tests for Feature 6: Constitution File Loading."""

    def test_get_constitution(self, client):
        response = client.get("/api/constitution")
        data = response.json()
        assert response.status_code == 200
        assert "constitution" in data

    def test_set_constitution(self, client):
        # Start a session first
        client.post("/api/start", json={
            "jira_key": "CONST-001",
            "jira_summary": "Test",
            "acceptance_criteria": [{"index": 0, "text": "AC", "checked": False}],
        })

        response = client.post("/api/constitution", json={
            "constitution": {"project": {"framework": "django"}},
        })
        assert response.status_code == 200


class TestSessionEndpoints:
    """Tests for Feature 2.8: Checkpoint & Resume web endpoints."""

    def test_session_check_no_checkpoint(self, client):
        response = client.get("/api/session/NONEXISTENT-999")
        data = response.json()
        assert data["has_checkpoint"] is False
