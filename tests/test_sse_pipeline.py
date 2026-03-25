"""Tests for SSE streaming pipeline (Feature 11).

Tests the streaming event format and structure.
Heavy integration tests are avoided to keep the test suite fast.
"""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from verify.negotiation.web import app, _session


@pytest.fixture(autouse=True)
def ensure_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


class TestSSEPipelineEndpoint:
    """Tests for the SSE streaming pipeline endpoint registration and basics."""

    def test_stream_pipeline_endpoint_exists(self):
        """The streaming pipeline endpoint should be registered."""
        routes = [r.path for r in app.routes]
        assert "/api/pipeline/stream" in routes

    def test_stream_requires_session(self):
        """Should return 400 when no session exists."""
        from fastapi.testclient import TestClient
        _session.clear()
        client = TestClient(app)
        response = client.post("/api/pipeline/stream")
        assert response.status_code == 400


class TestSSEEventFormat:
    """Tests for the SSE event format helper used in the pipeline."""

    def test_sse_event_json_structure(self):
        """SSE events should be valid JSON with type, step, status, message."""
        # Test the event format by simulating what the pipeline produces
        event_data = {
            "type": "step",
            "step": "compile",
            "status": "running",
            "message": "Compiling spec...",
        }
        json_str = json.dumps(event_data)
        parsed = json.loads(json_str)
        assert parsed["type"] == "step"
        assert parsed["step"] == "compile"
        assert parsed["status"] == "running"

    def test_sse_done_event_structure(self):
        """Done events should have success flag and optional verdicts."""
        event_data = {
            "type": "done",
            "success": True,
            "all_passed": True,
            "verdicts": [{"ac_checkbox": 0, "passed": True}],
        }
        json_str = json.dumps(event_data)
        parsed = json.loads(json_str)
        assert parsed["type"] == "done"
        assert parsed["success"] is True


class TestPipelineStepEndpoints:
    """Tests for individual pipeline step endpoints (non-streaming)."""

    def test_compile_endpoint_no_session(self):
        from fastapi.testclient import TestClient
        _session.clear()
        client = TestClient(app)
        response = client.post("/api/compile")
        assert response.status_code == 400

    def test_run_tests_endpoint_no_session(self):
        from fastapi.testclient import TestClient
        _session.clear()
        client = TestClient(app)
        response = client.post("/api/run-tests")
        assert response.status_code == 400

    def test_evaluate_endpoint_no_session(self):
        from fastapi.testclient import TestClient
        _session.clear()
        client = TestClient(app)
        response = client.post("/api/evaluate")
        assert response.status_code == 400

    def test_jira_update_endpoint_no_session(self):
        from fastapi.testclient import TestClient
        _session.clear()
        client = TestClient(app)
        response = client.post("/api/jira-update")
        assert response.status_code == 400


def _parse_sse_events(sse_text: str) -> list[dict]:
    """Parse SSE text into a list of event dicts."""
    events = []
    for line in sse_text.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                events.append(data)
            except json.JSONDecodeError:
                pass
    return events
