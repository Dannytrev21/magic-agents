"""Tests for structured observability logging (Feature 21).

Tests the HarnessLogger class and its integration with NegotiationHarness.
"""

import json
import tempfile
from pathlib import Path

import pytest

from verify.context import VerificationContext
from verify.observability import HarnessLogger, LOGS_DIR
from verify.negotiation.harness import NegotiationHarness


@pytest.fixture
def temp_logs_dir(monkeypatch):
    """Fixture that creates a temporary logs directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(
            "verify.observability.LOGS_DIR",
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
        },
    )


class TestHarnessLoggerBasics:
    """Test basic HarnessLogger functionality."""

    def test_logger_creation(self, temp_logs_dir):
        """Test that a logger can be created."""
        logger = HarnessLogger("TEST-001")
        assert logger.jira_key == "TEST-001"
        # Log file is created on first write, not on initialization
        logger.log_event("test", phase="phase_1")
        assert logger.log_path.exists()

    def test_log_event_basic(self, temp_logs_dir):
        """Test that a basic event can be logged."""
        logger = HarnessLogger("TEST-001")
        logger.log_event("phase_started", phase="phase_1", data={"ac_index": 0})

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "phase_started"
        assert events[0]["phase"] == "phase_1"
        assert events[0]["data"]["ac_index"] == 0
        assert "timestamp" in events[0]

    def test_multiple_events(self, temp_logs_dir):
        """Test that multiple events are logged in order."""
        logger = HarnessLogger("TEST-001")
        logger.log_event("phase_started", phase="phase_1")
        logger.log_event("llm_called", phase="phase_1")
        logger.log_event("llm_responded", phase="phase_1")

        events = logger.read_events()
        assert len(events) == 3
        assert events[0]["event_type"] == "phase_started"
        assert events[1]["event_type"] == "llm_called"
        assert events[2]["event_type"] == "llm_responded"

    def test_read_nonexistent_log(self, temp_logs_dir):
        """Test that reading a nonexistent log returns empty list."""
        logger = HarnessLogger("NONEXISTENT")
        events = logger.read_events()
        assert events == []

    def test_clear_log(self, temp_logs_dir):
        """Test that a log file can be cleared."""
        logger = HarnessLogger("TEST-001")
        logger.log_event("phase_started", phase="phase_1")
        assert len(logger.read_events()) == 1

        logger.clear()
        assert len(logger.read_events()) == 0
        assert not logger.log_path.exists()


class TestHarnessLoggerEventTypes:
    """Test different event types."""

    def test_phase_started(self, temp_logs_dir):
        """Test phase_started event logging."""
        logger = HarnessLogger("TEST-001")
        logger.log_phase_started("phase_1", data={"ac_index": 0})

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "phase_started"
        assert events[0]["phase"] == "phase_1"

    def test_phase_completed(self, temp_logs_dir):
        """Test phase_completed event logging."""
        logger = HarnessLogger("TEST-001")
        logger.log_phase_completed("phase_1", duration_ms=1234, data={"result_count": 5})

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "phase_completed"
        assert events[0]["duration_ms"] == 1234
        assert events[0]["data"]["result_count"] == 5

    def test_llm_called(self, temp_logs_dir):
        """Test llm_called event logging."""
        logger = HarnessLogger("TEST-001")
        logger.log_llm_called("phase_1", prompt_length=500, data={"model": "claude-3"})

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "llm_called"
        assert events[0]["data"]["prompt_length"] == 500
        assert events[0]["data"]["model"] == "claude-3"

    def test_llm_responded(self, temp_logs_dir):
        """Test llm_responded event logging."""
        logger = HarnessLogger("TEST-001")
        logger.log_llm_responded(
            "phase_1", response_length=1000, duration_ms=2500,
            data={"tokens_used": 150}
        )

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "llm_responded"
        assert events[0]["duration_ms"] == 2500
        assert events[0]["data"]["response_length"] == 1000
        assert events[0]["data"]["tokens_used"] == 150

    def test_validation_result_passed(self, temp_logs_dir):
        """Test validation_result event when validation passes."""
        logger = HarnessLogger("TEST-001")
        logger.log_validation_result("phase_1", valid=True)

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "validation_result"
        assert events[0]["data"]["valid"] is True

    def test_validation_result_failed(self, temp_logs_dir):
        """Test validation_result event when validation fails with errors."""
        logger = HarnessLogger("TEST-001")
        errors = ["AC index 0 not classified", "AC index 1 not classified"]
        logger.log_validation_result("phase_1", valid=False, errors=errors)

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["data"]["valid"] is False
        assert events[0]["data"]["errors"] == errors

    def test_developer_interaction(self, temp_logs_dir):
        """Test developer_interaction event logging."""
        logger = HarnessLogger("TEST-001")
        logger.log_developer_interaction(
            "phase_1", "feedback",
            data={"feedback_text": "Please clarify"}
        )

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "developer_interaction"
        assert events[0]["data"]["interaction_type"] == "feedback"
        assert events[0]["data"]["feedback_text"] == "Please clarify"

    def test_checkpoint_saved(self, temp_logs_dir):
        """Test checkpoint_saved event logging."""
        logger = HarnessLogger("TEST-001")
        logger.log_checkpoint_saved("phase_1", "/path/to/checkpoint.json")

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "checkpoint_saved"
        assert events[0]["data"]["checkpoint_path"] == "/path/to/checkpoint.json"

    def test_error(self, temp_logs_dir):
        """Test error event logging."""
        logger = HarnessLogger("TEST-001")
        logger.log_error(
            "phase_1", "LLM call failed",
            error_type="LLMError",
            data={"status_code": 500}
        )

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "error"
        assert events[0]["data"]["error_msg"] == "LLM call failed"
        assert events[0]["data"]["error_type"] == "LLMError"
        assert events[0]["data"]["status_code"] == 500


class TestHarnessLoggerContextManagers:
    """Test context manager functionality for timing."""

    def test_time_phase_context_manager(self, temp_logs_dir):
        """Test the time_phase context manager."""
        logger = HarnessLogger("TEST-001")

        with logger.time_phase("phase_1", data={"ac_count": 3}):
            # Simulate some work
            pass

        events = logger.read_events()
        assert len(events) == 2
        assert events[0]["event_type"] == "phase_started"
        assert events[1]["event_type"] == "phase_completed"
        assert events[1]["duration_ms"] >= 0

    def test_time_llm_call_context_manager(self, temp_logs_dir):
        """Test the time_llm_call context manager."""
        logger = HarnessLogger("TEST-001")

        with logger.time_llm_call("phase_1", prompt_length=500):
            # Simulate an LLM call
            pass

        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "llm_called"
        assert events[0]["data"]["prompt_length"] == 500

    def test_phase_timing_captures_duration(self, temp_logs_dir):
        """Test that phase timing captures duration correctly."""
        import time
        logger = HarnessLogger("TEST-001")

        with logger.time_phase("phase_1"):
            time.sleep(0.1)  # Sleep for ~100ms

        events = logger.read_events()
        completed = [e for e in events if e["event_type"] == "phase_completed"][0]
        # Duration should be at least 100ms (allowing some tolerance)
        assert completed["duration_ms"] >= 90


class TestHarnessLoggerSummary:
    """Test the summary function."""

    def test_summary_empty_log(self, temp_logs_dir):
        """Test summary for an empty log."""
        logger = HarnessLogger("TEST-001")
        summary = logger.get_summary()

        assert summary["total_events"] == 0
        assert summary["event_counts"] == {}
        assert summary["phases"] == []
        assert summary["duration_ms"] is None

    def test_summary_with_events(self, temp_logs_dir):
        """Test summary with multiple events."""
        import time
        logger = HarnessLogger("TEST-001")
        logger.log_phase_started("phase_1")
        time.sleep(0.01)  # Sleep to ensure timestamps differ
        logger.log_llm_called("phase_1", prompt_length=500)
        logger.log_llm_responded("phase_1", response_length=1000, duration_ms=2000)
        logger.log_phase_completed("phase_1", duration_ms=2500)

        summary = logger.get_summary()

        assert summary["total_events"] == 4
        assert summary["event_counts"]["phase_started"] == 1
        assert summary["event_counts"]["llm_called"] == 1
        assert summary["event_counts"]["llm_responded"] == 1
        assert summary["event_counts"]["phase_completed"] == 1
        assert "phase_1" in summary["phases"]
        assert summary["duration_ms"] >= 0  # Can be 0 if events are very close

    def test_summary_multiple_phases(self, temp_logs_dir):
        """Test summary with multiple phases."""
        logger = HarnessLogger("TEST-001")
        logger.log_phase_started("phase_1")
        logger.log_phase_completed("phase_1", duration_ms=1000)
        logger.log_phase_started("phase_2")
        logger.log_phase_completed("phase_2", duration_ms=1500)

        summary = logger.get_summary()

        assert summary["total_events"] == 4
        assert len(summary["phases"]) == 2
        assert "phase_1" in summary["phases"]
        assert "phase_2" in summary["phases"]


class TestHarnessIntegration:
    """Test integration with NegotiationHarness."""

    def test_harness_creates_logger(self, temp_logs_dir, sample_context):
        """Test that NegotiationHarness creates a logger."""
        harness = NegotiationHarness(sample_context)
        assert harness.logger is not None
        assert harness.logger.jira_key == "TEST-001"

    def test_harness_logs_phase_advancement(self, temp_logs_dir, sample_context):
        """Test that harness logs phase advancement."""
        # Manually set classifications to pass phase 0 exit condition
        sample_context.classifications = [
            {"ac_index": 0, "type": "api_behavior"}
        ]

        harness = NegotiationHarness(sample_context)
        harness.advance_phase()

        events = harness.logger.read_events()
        # Should have phase_started and checkpoint_saved events
        event_types = [e["event_type"] for e in events]
        assert "phase_started" in event_types
        assert "checkpoint_saved" in event_types

    def test_harness_logs_multiple_phases(self, temp_logs_dir):
        """Test that harness logs transitions through multiple phases."""
        ctx = VerificationContext(
            jira_key="TEST-002",
            jira_summary="Multi-phase test",
            raw_acceptance_criteria=[
                {"index": 0, "text": "Test AC", "checked": False},
            ],
            constitution={},
        )

        harness = NegotiationHarness(ctx)

        # Advance through phases
        # Phase 0 -> Phase 1
        ctx.classifications = [{"ac_index": 0, "type": "api_behavior"}]
        harness.advance_phase()

        # Phase 1 -> Phase 2
        ctx.postconditions = [{"ac_index": 0}]
        harness.advance_phase()

        events = harness.logger.read_events()
        # Should have at least 4 events: 2 phase_started + 2 checkpoint_saved
        assert len(events) >= 4


class TestEventJsonValidity:
    """Test that events are valid JSON."""

    def test_events_are_valid_json(self, temp_logs_dir):
        """Test that all events can be serialized to and from JSON."""
        logger = HarnessLogger("TEST-001")

        # Log various event types
        logger.log_phase_started("phase_1", data={"nested": {"key": "value"}})
        logger.log_llm_called("phase_1", prompt_length=500)
        logger.log_error("phase_1", "Error occurred", error_type="ValueError")

        # Read back and verify JSON validity
        events = logger.read_events()
        for event in events:
            # If we got here, the event was successfully parsed from JSON
            assert isinstance(event, dict)
            assert "timestamp" in event
            assert "event_type" in event

    def test_event_roundtrip(self, temp_logs_dir):
        """Test that events survive JSON serialization roundtrip."""
        logger = HarnessLogger("TEST-001")

        original_data = {
            "phase": "phase_1",
            "result_count": 42,
            "nested": {"key": "value", "list": [1, 2, 3]}
        }
        logger.log_event("test_event", phase="phase_1", data=original_data)

        events = logger.read_events()
        assert events[0]["data"] == original_data


class TestFlushBehavior:
    """Test that logs are flushed properly."""

    def test_flush_method_exists(self, temp_logs_dir):
        """Test that flush() method can be called."""
        logger = HarnessLogger("TEST-001")
        logger.log_event("phase_started", phase="phase_1")
        logger.flush()  # Should not raise

        events = logger.read_events()
        assert len(events) == 1

    def test_events_persisted_immediately(self, temp_logs_dir):
        """Test that events are available immediately after logging."""
        logger = HarnessLogger("TEST-001")
        logger.log_event("phase_started", phase="phase_1")

        # Read immediately without explicit flush
        events = logger.read_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "phase_started"
