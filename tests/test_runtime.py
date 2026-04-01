"""Unit tests for session/runtime helpers — includes P3.2 compaction integration."""

from pathlib import Path
from unittest.mock import Mock

import logging
import pytest

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.checkpoint import save_checkpoint
from verify.negotiation.harness import NegotiationHarness
from verify.runtime import SessionState, SessionStore
from verify.transcript import TranscriptCompactor


@pytest.fixture(autouse=True)
def ensure_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.fixture
def sample_context():
    return VerificationContext(
        jira_key="RUNTIME-001",
        jira_summary="Runtime helpers",
        raw_acceptance_criteria=[
            {"index": 0, "text": "User can view profile via GET /api/v1/users/me", "checked": False},
        ],
        constitution={"project": {"framework": "fastapi"}, "api": {"base_path": "/api/v1"}},
    )


# ---------------------------------------------------------------
# Existing SessionStore tests
# ---------------------------------------------------------------

def test_session_store_creates_distinct_sessions(sample_context):
    store = SessionStore()
    first = store.create(sample_context, llm=LLMClient())
    second_context = VerificationContext(
        jira_key="RUNTIME-002",
        jira_summary="Second runtime session",
        raw_acceptance_criteria=[
            {"index": 0, "text": "Admin can ban user via POST /api/v1/admin/ban", "checked": False},
        ],
        constitution={"project": {"framework": "fastapi"}, "api": {"base_path": "/api/v1"}},
    )
    second = store.create(second_context, llm=LLMClient())

    assert first.session_id != second.session_id
    assert store.resolve(first.session_id) is first
    assert store.resolve(second.session_id) is second
    # resolve(None) returns the active session (last created)
    assert store.resolve(None) is second


def test_run_phase_captures_structured_questions(sample_context):
    state = SessionState(
        session_id="session-2",
        context=sample_context,
        llm=LLMClient(),
        harness=NegotiationHarness(sample_context),
    )

    def skill(context, llm):
        return llm.chat(
            "You are a verification engineer. Classify acceptance criteria.",
            "[0] User can view profile via GET /api/v1/users/me",
            response_format="json",
        )

    results, questions = state.run_phase(
        title="Phase 1",
        phase_name="phase_0",
        skill_fn=skill,
    )

    assert results["classifications"][0]["ac_index"] == 0
    assert questions[0]["id"] == "phase_0-question-1"
    assert "specific role" in questions[0]["text"]
    assert state.latest_questions == questions
    assert any(entry["kind"] == "questions" for entry in state.transcript)


def test_restore_uses_checkpoint_phase_index(sample_context, monkeypatch, tmp_path):
    monkeypatch.setattr("verify.negotiation.checkpoint.SESSIONS_DIR", Path(tmp_path))
    sample_context.current_phase = "phase_2"
    sample_context.classifications = [
        {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user"}
    ]
    sample_context.postconditions = [{"ac_index": 0, "status": 200}]
    save_checkpoint(sample_context, "phase_2")

    store = SessionStore()
    restored = store.restore(sample_context.jira_key, llm=LLMClient())

    assert restored is not None
    assert restored.context.current_phase == "phase_2"
    assert restored.phase_idx == 2


# ---------------------------------------------------------------
# Session identity persistence (from main)
# ---------------------------------------------------------------

def test_restore_reuses_persisted_session_identity(monkeypatch, tmp_path):
    monkeypatch.setattr("verify.negotiation.checkpoint.SESSIONS_DIR", Path(tmp_path))

    context = VerificationContext(
        jira_key="RUNTIME-001",
        jira_summary="Runtime restore",
        raw_acceptance_criteria=[
            {"index": 0, "text": "Operator can resume the saved session", "checked": False},
        ],
        constitution={},
    )
    context.current_phase = "phase_2"
    context.session_id = "session-runtime-001"

    save_checkpoint(context, "phase_2")

    store = SessionStore()
    first_restore = store.restore("RUNTIME-001", llm=LLMClient())
    second_restore = store.restore("RUNTIME-001", llm=LLMClient())

    assert first_restore is not None
    assert first_restore.session_id == "session-runtime-001"
    assert first_restore.context.session_id == "session-runtime-001"
    assert second_restore is first_restore


# ---------------------------------------------------------------
# P3.2 — SessionState compaction integration
# ---------------------------------------------------------------

def test_session_state_accepts_compaction_params(sample_context):
    """SessionState.__init__ accepts compaction_threshold and keep_recent."""
    state = SessionState(
        session_id="cmp-1",
        context=sample_context,
        llm=LLMClient(),
        harness=NegotiationHarness(sample_context),
        compaction_threshold=10,
        keep_recent=5,
    )
    assert state.compaction_threshold == 10
    assert state.keep_recent == 5


def test_session_auto_compacts_transcript(sample_context):
    """record_transcript triggers compaction when threshold exceeded."""
    state = SessionState(
        session_id="cmp-2",
        context=sample_context,
        llm=LLMClient(),
        harness=NegotiationHarness(sample_context),
        compaction_threshold=10,
        keep_recent=5,
    )
    for i in range(15):
        state.record_transcript("user", f"phase_{i % 3}", f"message {i}")

    # Compaction should have fired at least once — summary entry present
    assert state.transcript[0]["kind"] == "compaction_summary"
    # Transcript should never exceed threshold + 1 (the entry that triggers compaction)
    assert len(state.transcript) <= state.compaction_threshold + 1
    # Last entry should be the most recent message
    assert state.transcript[-1]["content"] == "message 14"


def test_session_compaction_replaces_naive_slice(sample_context):
    """The old naive slice behaviour is replaced by TranscriptCompactor."""
    state = SessionState(
        session_id="cmp-3",
        context=sample_context,
        llm=LLMClient(),
        harness=NegotiationHarness(sample_context),
        compaction_threshold=8,
        keep_recent=3,
    )
    for i in range(12):
        state.record_transcript("user", "phase_1", f"msg-{i}")

    # First entry must be a compaction summary, not a regular message
    assert state.transcript[0]["kind"] == "compaction_summary"
    # Recent entries preserved verbatim
    assert state.transcript[-1]["content"] == "msg-11"
    # Summary contains original phase data
    assert "phase_1" in state.transcript[0]["content"]
    # Never exceeds threshold + 1
    assert len(state.transcript) <= state.compaction_threshold + 1


def test_compaction_failure_does_not_break_recording(sample_context, caplog):
    """If compaction raises, the entry is still recorded and the error logged."""
    state = SessionState(
        session_id="cmp-4",
        context=sample_context,
        llm=LLMClient(),
        harness=NegotiationHarness(sample_context),
        compaction_threshold=5,
        keep_recent=2,
    )

    class BrokenCompactor:
        def compact(self, entries):
            raise RuntimeError("compaction boom")

    state.compactor = BrokenCompactor()

    with caplog.at_level(logging.WARNING):
        entry = state.record_transcript("user", "phase_1", "test-msg")

    assert entry["content"] == "test-msg"
    assert "compaction" in caplog.text.lower()
