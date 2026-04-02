"""Tests for transcript compaction ported from claw-code."""

from pathlib import Path

import pytest

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.checkpoint import load_checkpoint, save_checkpoint
from verify.negotiation.harness import NegotiationHarness
from verify.transcript import TranscriptCompactor


@pytest.fixture(autouse=True)
def ensure_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


def _entry(index: int, phase: str) -> dict:
    return {
        "phase": phase,
        "role": "ai",
        "content": f"message-{index}",
        "timestamp": f"2026-04-01T00:00:{index:02d}+00:00",
    }


def _context() -> VerificationContext:
    return VerificationContext(
        jira_key="TC-001",
        jira_summary="Transcript compaction",
        raw_acceptance_criteria=[
            {"index": 0, "text": "User can view profile", "checked": False},
        ],
        constitution={"project": {"framework": "fastapi"}, "api": {"base_path": "/api/v1"}},
    )


def test_compactor_reduces_old_entries_to_summary():
    entries = [_entry(index, f"phase_{index % 3}") for index in range(8)]

    compacted = TranscriptCompactor(compaction_threshold=5, keep_recent=2).compact(entries)

    assert len(compacted) == 3
    assert compacted[0]["kind"] == "compaction_summary"
    assert compacted[0]["data"]["compacted_count"] == 6
    assert compacted[0]["data"]["phases"] == ["phase_0", "phase_1", "phase_2"]
    assert [entry["content"] for entry in compacted[1:]] == ["message-6", "message-7"]


def test_compactor_is_idempotent_without_new_entries():
    entries = [_entry(index, "phase_0") for index in range(8)]
    compactor = TranscriptCompactor(compaction_threshold=5, keep_recent=2)

    first = compactor.compact(entries)
    second = compactor.compact(first)

    assert second == first


def test_compactor_reuses_existing_summary_instead_of_stacking():
    compactor = TranscriptCompactor(compaction_threshold=5, keep_recent=2)
    first = compactor.compact([_entry(index, "phase_0") for index in range(8)])
    expanded = first + [_entry(8, "phase_1"), _entry(9, "phase_1"), _entry(10, "phase_2")]

    compacted = compactor.compact(expanded)

    assert len([entry for entry in compacted if entry.get("kind") == "compaction_summary"]) == 1
    assert compacted[0]["data"]["compacted_count"] == 9
    assert [entry["content"] for entry in compacted[1:]] == ["message-9", "message-10"]


def test_harness_auto_compacts_negotiation_log():
    context = _context()
    harness = NegotiationHarness(
        context,
        transcript_compactor=TranscriptCompactor(compaction_threshold=4, keep_recent=2),
    )

    for index in range(7):
        harness.add_to_log("phase_0", "ai", f"message-{index}")

    assert context.negotiation_log[0]["kind"] == "compaction_summary"
    assert context.negotiation_log[-1]["content"] == "message-6"
    assert len(context.negotiation_log) <= 4


def test_checkpoint_round_trip_preserves_compaction_summary(monkeypatch, tmp_path):
    monkeypatch.setattr("verify.negotiation.checkpoint.SESSIONS_DIR", Path(tmp_path))
    context = _context()
    harness = NegotiationHarness(
        context,
        transcript_compactor=TranscriptCompactor(compaction_threshold=4, keep_recent=2),
    )

    for index in range(7):
        harness.add_to_log("phase_0", "ai", f"message-{index}")

    save_checkpoint(context, "phase_0")
    loaded_context, _, _controller = load_checkpoint(context.jira_key)

    assert loaded_context.negotiation_log[0]["kind"] == "compaction_summary"
    assert loaded_context.negotiation_log[-1]["content"] == "message-6"


# ---------------------------------------------------------------
# P3.3 — History log compaction with event deduplication
# ---------------------------------------------------------------

def _history_entry(timestamp: str, title: str, detail: str) -> dict:
    return {"timestamp": timestamp, "title": title, "detail": detail}


def test_history_dedup_consecutive_same_title():
    """Consecutive history entries with the same title are merged."""
    entries = [
        _history_entry("t1", "phase_output", "phase_1 produced 5 items"),
        _history_entry("t2", "phase_output", "phase_1 produced 5 items (revised)"),
        _history_entry("t3", "checkpoint_saved", "saved phase_1"),
    ]
    compactor = TranscriptCompactor(compaction_threshold=30, keep_recent=15)
    compacted = compactor.compact_history(entries, threshold=2, keep_recent=1)

    assert len(compacted) < len(entries)
    merged = [e for e in compacted if e.get("count", 0) >= 2]
    assert len(merged) == 1
    assert merged[0]["first_timestamp"] == "t1"
    assert merged[0]["last_timestamp"] == "t2"


def test_history_non_consecutive_preserved():
    """Non-consecutive entries with the same title remain separate."""
    entries = [
        _history_entry("t1", "A", "first A"),
        _history_entry("t2", "B", "a B"),
        _history_entry("t3", "A", "second A"),
    ]
    compactor = TranscriptCompactor(compaction_threshold=30, keep_recent=15)
    compacted = compactor.compact_history(entries, threshold=2, keep_recent=0)

    a_entries = [e for e in compacted if e["title"] == "A"]
    assert len(a_entries) == 2  # Not merged because non-consecutive


def test_history_merged_entry_has_count_and_timestamps():
    """Merged entries have count >= 2, first_timestamp, last_timestamp."""
    entries = [
        _history_entry("t1", "X", "detail1"),
        _history_entry("t2", "X", "detail2"),
        _history_entry("t3", "X", "detail3"),
    ]
    compactor = TranscriptCompactor(compaction_threshold=30, keep_recent=15)
    compacted = compactor.compact_history(entries, threshold=2, keep_recent=0)

    assert len(compacted) == 1
    assert compacted[0]["count"] == 3
    assert compacted[0]["first_timestamp"] == "t1"
    assert compacted[0]["last_timestamp"] == "t3"
    assert compacted[0]["title"] == "X"


def test_history_keep_recent_preserved_verbatim():
    """The most recent keep_recent entries are preserved without merging."""
    entries = [
        _history_entry("t1", "Y", "old1"),
        _history_entry("t2", "Y", "old2"),
        _history_entry("t3", "Z", "old3"),
        _history_entry("t4", "W", "recent1"),
        _history_entry("t5", "W", "recent2"),
    ]
    compactor = TranscriptCompactor(compaction_threshold=30, keep_recent=15)
    compacted = compactor.compact_history(entries, threshold=3, keep_recent=2)

    # The last 2 entries should be verbatim
    assert compacted[-1] == entries[-1]
    assert compacted[-2] == entries[-2]


def test_session_record_history_triggers_compaction():
    """record_history triggers compaction when history_compaction_threshold is exceeded."""
    from verify.runtime import SessionState

    ctx = _context()
    state = SessionState(
        session_id="hist-1",
        context=ctx,
        llm=LLMClient(),
        harness=NegotiationHarness(ctx),
        history_compaction_threshold=10,
        keep_recent_history=5,
    )

    # Add many history entries with consecutive duplicates
    for i in range(15):
        state.record_history("repeated_event", f"detail {i}")

    # Should have been compacted — merged entries exist
    assert len(state.history) < 15
    merged = [e for e in state.history if e.get("count", 0) >= 2]
    assert len(merged) >= 1
