"""Tests for Epic P06: Structured Streaming Events.

Covers all three stories:
- P6.1: Typed event schema (NegotiationEvent enum, RuntimeEvent validation, EVENT_SCHEMAS)
- P6.2: Event emission from NegotiationHarness via event_emitter callback
- P6.3: SSE endpoint with event filtering
"""

import asyncio
import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.harness import NegotiationHarness
from verify.runtime import (
    EVENT_SCHEMAS,
    NegotiationEvent,
    RuntimeEvent,
    SessionState,
    SessionStore,
)


@pytest.fixture(autouse=True)
def ensure_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.fixture
def sample_context():
    return VerificationContext(
        jira_key="P06-001",
        jira_summary="Structured streaming events",
        raw_acceptance_criteria=[
            {"index": 0, "text": "User can view profile via GET /api/v1/users/me", "checked": False},
        ],
        constitution={"project": {"framework": "fastapi"}, "api": {"base_path": "/api/v1"}},
    )


# ===================================================================
# P6.1: Typed Event Schema
# ===================================================================


class TestNegotiationEventEnum:
    """NegotiationEvent enum defines the closed set of SSE event types."""

    def test_all_event_types_defined(self):
        expected = {
            "phase_start",
            "phase_progress",
            "phase_complete",
            "phase_error",
            "validation_result",
            "budget_warning",
            "budget_exceeded",
            "skill_dispatch",
            "skill_complete",
            "session_checkpoint",
        }
        actual = {e.value for e in NegotiationEvent}
        assert actual == expected

    def test_enum_members_are_strings(self):
        for event in NegotiationEvent:
            assert isinstance(event.value, str)

    def test_enum_lookup_by_value(self):
        assert NegotiationEvent("phase_start") == NegotiationEvent.PHASE_START
        assert NegotiationEvent("phase_error") == NegotiationEvent.PHASE_ERROR

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            NegotiationEvent("invalid_type")


class TestRuntimeEventValidation:
    """RuntimeEvent validates its type against NegotiationEvent."""

    def test_valid_event_types(self):
        for event_type in NegotiationEvent:
            event = RuntimeEvent(type=event_type.value, session_id="test")
            assert event.type == event_type.value

    def test_invalid_event_type_raises(self):
        with pytest.raises(ValueError, match="invalid_type"):
            RuntimeEvent(type="invalid_type", session_id="test")

    def test_legacy_event_types_still_work(self):
        """Legacy types like 'step', 'done', 'error' must still be accepted."""
        for legacy_type in ("step", "done", "error"):
            event = RuntimeEvent(type=legacy_type, session_id="test")
            assert event.type == legacy_type

    def test_payload_structure(self):
        event = RuntimeEvent(
            type="phase_start",
            session_id="sess-1",
            step="phase_0",
            status="running",
            message="Starting classification",
            data={"phase_index": 0},
        )
        payload = event.payload()
        assert payload["type"] == "phase_start"
        assert payload["session_id"] == "sess-1"
        assert payload["step"] == "phase_0"
        assert payload["status"] == "running"
        assert payload["message"] == "Starting classification"
        assert payload["phase_index"] == 0

    def test_as_sse_format(self):
        event = RuntimeEvent(type="phase_start", session_id="test")
        sse = event.as_sse()
        assert sse.startswith("event: phase_start\ndata: ")
        assert sse.endswith("\n\n")
        # Extract data line and parse JSON
        data_line = sse.split("\n")[1]
        data_json = json.loads(data_line[len("data: "):])
        assert data_json["type"] == "phase_start"

    def test_legacy_as_sse_format(self):
        """Legacy events use old format without event: prefix."""
        event = RuntimeEvent(type="step", session_id="test")
        sse = event.as_sse()
        assert sse.startswith("data: ")
        assert "event:" not in sse


class TestEventSchemas:
    """EVENT_SCHEMAS maps each NegotiationEvent to its expected payload fields."""

    def test_every_event_type_has_schema(self):
        for event_type in NegotiationEvent:
            assert event_type.value in EVENT_SCHEMAS, (
                f"Missing schema for {event_type.value}"
            )

    def test_schema_fields_are_sets(self):
        for event_type, fields in EVENT_SCHEMAS.items():
            assert isinstance(fields, set), (
                f"Schema for {event_type} should be a set of field names"
            )

    def test_phase_start_schema(self):
        schema = EVENT_SCHEMAS["phase_start"]
        assert "phase" in schema
        assert "phase_index" in schema

    def test_phase_complete_schema(self):
        schema = EVENT_SCHEMAS["phase_complete"]
        assert "phase" in schema
        assert "result_count" in schema

    def test_phase_error_schema(self):
        schema = EVENT_SCHEMAS["phase_error"]
        assert "phase" in schema
        assert "error" in schema

    def test_budget_exceeded_schema(self):
        schema = EVENT_SCHEMAS["budget_exceeded"]
        assert "phase" in schema
        assert "usage_summary" in schema


# ===================================================================
# P6.2: Event Emission from NegotiationHarness
# ===================================================================


class TestHarnessEventEmitter:
    """NegotiationHarness emits structured events through event_emitter callback."""

    def test_harness_accepts_event_emitter(self, sample_context):
        events = []
        harness = NegotiationHarness(
            sample_context, event_emitter=events.append
        )
        assert harness.event_emitter is not None

    def test_harness_default_no_emitter(self, sample_context):
        harness = NegotiationHarness(sample_context)
        assert harness.event_emitter is None

    def test_run_current_phase_emits_phase_start_and_complete(self, sample_context):
        events = []
        harness = NegotiationHarness(
            sample_context, event_emitter=events.append
        )
        llm = LLMClient()
        harness.run_current_phase(llm)

        types = [e.type for e in events]
        assert types[0] == "phase_start"
        assert types[-1] in ("phase_complete", "phase_error")

    def test_phase_start_event_has_correct_payload(self, sample_context):
        events = []
        harness = NegotiationHarness(
            sample_context, event_emitter=events.append
        )
        llm = LLMClient()
        harness.run_current_phase(llm)

        start_event = events[0]
        assert start_event.type == "phase_start"
        payload = start_event.payload()
        assert "phase" in payload.get("data", payload)  or payload.get("step") == "phase_0"

    def test_phase_complete_includes_result_count(self, sample_context):
        events = []
        harness = NegotiationHarness(
            sample_context, event_emitter=events.append
        )
        llm = LLMClient()
        harness.run_current_phase(llm)

        complete_events = [e for e in events if e.type == "phase_complete"]
        assert len(complete_events) == 1
        payload = complete_events[0].payload()
        assert "result_count" in payload or "result_count" in payload.get("data", {})

    def test_validation_result_emitted(self, sample_context):
        events = []
        harness = NegotiationHarness(
            sample_context, event_emitter=events.append
        )
        llm = LLMClient()
        harness.run_current_phase(llm)

        validation_events = [e for e in events if e.type == "validation_result"]
        assert len(validation_events) >= 1

    def test_phase_error_on_exception(self, sample_context):
        events = []
        harness = NegotiationHarness(
            sample_context, event_emitter=events.append
        )

        broken_llm = MagicMock(spec=LLMClient)
        broken_llm.chat.side_effect = RuntimeError("LLM failure")

        with pytest.raises(RuntimeError):
            harness.run_current_phase(broken_llm)

        error_events = [e for e in events if e.type == "phase_error"]
        assert len(error_events) == 1
        payload = error_events[0].payload()
        assert "LLM failure" in str(payload)

    def test_callback_error_graceful(self, sample_context, caplog):
        """Emitter exceptions are caught and logged, never block the harness."""

        def bad_emitter(event):
            raise RuntimeError("emitter boom")

        harness = NegotiationHarness(
            sample_context, event_emitter=bad_emitter
        )
        llm = LLMClient()

        with caplog.at_level(logging.WARNING):
            result = harness.run_current_phase(llm)

        assert result["status"] in ("completed", "no_runner")
        assert "emitter" in caplog.text.lower() or "event" in caplog.text.lower()

    def test_budget_exceeded_emits_event(self, sample_context):
        events = []
        bp = MagicMock()
        bp.can_proceed.return_value = False
        bp.get_usage_summary.return_value = {"tokens": 5000}

        harness = NegotiationHarness(
            sample_context,
            backpressure=bp,
            event_emitter=events.append,
        )
        llm = LLMClient()
        harness.run_current_phase(llm)

        budget_events = [e for e in events if e.type == "budget_exceeded"]
        assert len(budget_events) == 1

    def test_advance_phase_emits_checkpoint(self, sample_context):
        events = []
        sample_context.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "user"}
        ]
        harness = NegotiationHarness(
            sample_context, event_emitter=events.append
        )
        harness.advance_phase()

        checkpoint_events = [e for e in events if e.type == "session_checkpoint"]
        assert len(checkpoint_events) == 1

    def test_events_in_causal_order(self, sample_context):
        events = []
        harness = NegotiationHarness(
            sample_context, event_emitter=events.append
        )
        llm = LLMClient()
        harness.run_current_phase(llm)

        types = [e.type for e in events]
        if "phase_start" in types and "phase_complete" in types:
            start_idx = types.index("phase_start")
            complete_idx = types.index("phase_complete")
            assert start_idx < complete_idx


# ===================================================================
# P6.3: SSE Endpoint with Event Filtering
# ===================================================================


class TestSSEEventsEndpoint:
    """GET /api/events/{session_id} streams typed SSE events."""

    def test_events_endpoint_exists(self):
        from verify.negotiation.web import app
        routes = [r.path for r in app.routes]
        assert "/api/events/{session_id}" in routes

    def test_events_endpoint_returns_event_stream(self):
        from fastapi.testclient import TestClient
        from verify.negotiation.web import app, SESSION_STORE

        SESSION_STORE.clear()
        ctx = VerificationContext(
            jira_key="SSE-001",
            jira_summary="SSE test",
            raw_acceptance_criteria=[
                {"index": 0, "text": "Test AC", "checked": False}
            ],
            constitution={},
        )
        state = SESSION_STORE.create(ctx, llm=LLMClient())
        sid = state.session_id

        client = TestClient(app)
        response = client.get(f"/api/events/{sid}")
        assert response.headers["content-type"].startswith("text/event-stream")

    def test_events_endpoint_invalid_session(self):
        from fastapi.testclient import TestClient
        from verify.negotiation.web import app, SESSION_STORE

        SESSION_STORE.clear()
        client = TestClient(app)
        response = client.get("/api/events/nonexistent")
        assert response.status_code == 404

    def test_events_endpoint_filtering(self):
        from fastapi.testclient import TestClient
        from verify.negotiation.web import app, SESSION_STORE

        SESSION_STORE.clear()
        ctx = VerificationContext(
            jira_key="SSE-002",
            jira_summary="SSE filter test",
            raw_acceptance_criteria=[
                {"index": 0, "text": "Test AC", "checked": False}
            ],
            constitution={},
        )
        state = SESSION_STORE.create(ctx, llm=LLMClient())
        sid = state.session_id

        # Enqueue some events into the session's event buffer
        state.event_buffer.append(
            RuntimeEvent(type="phase_start", session_id=sid, step="phase_0")
        )
        state.event_buffer.append(
            RuntimeEvent(type="phase_complete", session_id=sid, step="phase_0")
        )
        state.event_buffer.append(
            RuntimeEvent(type="validation_result", session_id=sid, step="phase_0")
        )

        client = TestClient(app)
        response = client.get(
            f"/api/events/{sid}?types=phase_complete"
        )

        events = _parse_sse_events(response.text)
        for event in events:
            if event.get("type") in {e.value for e in NegotiationEvent}:
                assert event["type"] == "phase_complete"

    def test_events_sse_field_format(self):
        from fastapi.testclient import TestClient
        from verify.negotiation.web import app, SESSION_STORE

        SESSION_STORE.clear()
        ctx = VerificationContext(
            jira_key="SSE-003",
            jira_summary="SSE format test",
            raw_acceptance_criteria=[
                {"index": 0, "text": "Test AC", "checked": False}
            ],
            constitution={},
        )
        state = SESSION_STORE.create(ctx, llm=LLMClient())
        sid = state.session_id

        state.event_buffer.append(
            RuntimeEvent(type="phase_start", session_id=sid, step="phase_0")
        )

        client = TestClient(app)
        response = client.get(f"/api/events/{sid}")

        # SSE messages should have event: and data: fields
        lines = response.text.strip().split("\n")
        has_event_field = any(line.startswith("event:") for line in lines)
        has_data_field = any(line.startswith("data:") for line in lines)
        assert has_event_field, "SSE should include 'event:' field"
        assert has_data_field, "SSE should include 'data:' field"


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
