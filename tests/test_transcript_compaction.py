"""Tests for transcript compaction ported from claw-code."""

from pathlib import Path

from verify.context import VerificationContext
from verify.negotiation.checkpoint import load_checkpoint, save_checkpoint
from verify.negotiation.harness import NegotiationHarness
from verify.transcript import TranscriptCompactor


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
    loaded_context, _ = load_checkpoint(context.jira_key)

    assert loaded_context.negotiation_log[0]["kind"] == "compaction_summary"
    assert loaded_context.negotiation_log[-1]["content"] == "message-6"
