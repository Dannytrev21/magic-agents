"""Tests for checkpoint and resume support (Feature 2.8).

Tests the save/load checkpoint functionality, session management,
and integration with the harness.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from verify.context import VerificationContext
from verify.negotiation.checkpoint import (
    save_checkpoint,
    load_checkpoint,
    has_checkpoint,
    get_session_info,
    clear_session,
    SESSIONS_DIR,
)
from verify.negotiation.harness import NegotiationHarness, PHASES


@pytest.fixture
def temp_sessions_dir(monkeypatch):
    """Fixture that creates a temporary sessions directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(
            "verify.negotiation.checkpoint.SESSIONS_DIR",
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
            {"index": 1, "text": "User can logout", "checked": False},
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
            "interface": {"method": "POST", "path": "/api/v1/auth/login"},
        }
    ]
    ctx.postconditions = [
        {
            "ac_index": 0,
            "status": 200,
            "schema": {"token": "string", "expires_in": "integer"},
        }
    ]
    ctx.negotiation_log = [
        {
            "phase": "phase_0",
            "role": "ai",
            "content": "Classified all ACs",
            "timestamp": "2026-03-25T10:00:00+00:00",
        }
    ]
    return ctx


class TestSaveCheckpoint:
    """Tests for save_checkpoint function."""

    def test_save_checkpoint_creates_directory(self, temp_sessions_dir, sample_context):
        """Checkpoint save should create the session directory if it doesn't exist."""
        assert not (temp_sessions_dir / sample_context.jira_key).exists()

        save_checkpoint(sample_context, "phase_0")

        assert (temp_sessions_dir / sample_context.jira_key).exists()
        assert (
            temp_sessions_dir / sample_context.jira_key / "checkpoint_phase_0.json"
        ).exists()

    def test_save_checkpoint_writes_json(self, temp_sessions_dir, populated_context):
        """Checkpoint should contain all context data as JSON."""
        save_checkpoint(populated_context, "phase_1")

        checkpoint_path = (
            temp_sessions_dir
            / populated_context.jira_key
            / "checkpoint_phase_1.json"
        )
        with open(checkpoint_path) as f:
            data = json.load(f)

        assert data["jira_key"] == "TEST-001"
        assert data["jira_summary"] == "Test Story"
        assert data["current_phase"] == "phase_1"
        assert len(data["classifications"]) == 1
        assert len(data["postconditions"]) == 1
        assert len(data["negotiation_log"]) == 1

    def test_save_checkpoint_includes_all_fields(
        self, temp_sessions_dir, populated_context
    ):
        """Checkpoint should serialize all VerificationContext fields."""
        populated_context.approved = True
        populated_context.approved_by = "developer"
        populated_context.approved_at = "2026-03-25T10:00:00Z"
        populated_context.spec_path = "/path/to/spec.yaml"
        populated_context.verdicts = [{"ac_index": 0, "passed": True}]
        populated_context.all_passed = True

        save_checkpoint(populated_context, "phase_2")

        checkpoint_path = (
            temp_sessions_dir
            / populated_context.jira_key
            / "checkpoint_phase_2.json"
        )
        with open(checkpoint_path) as f:
            data = json.load(f)

        assert data["approved"] is True
        assert data["approved_by"] == "developer"
        assert data["spec_path"] == "/path/to/spec.yaml"
        assert len(data["verdicts"]) == 1
        assert data["all_passed"] is True

    def test_save_checkpoint_overwrites_existing(
        self, temp_sessions_dir, sample_context
    ):
        """Saving a checkpoint with the same phase should overwrite."""
        sample_context.classifications = [{"ac_index": 0, "type": "api_behavior"}]
        save_checkpoint(sample_context, "phase_1")

        sample_context.classifications = [
            {"ac_index": 0, "type": "api_behavior"},
            {"ac_index": 1, "type": "api_behavior"},
        ]
        save_checkpoint(sample_context, "phase_1")

        checkpoint_path = (
            temp_sessions_dir / sample_context.jira_key / "checkpoint_phase_1.json"
        )
        with open(checkpoint_path) as f:
            data = json.load(f)

        assert len(data["classifications"]) == 2

    def test_save_checkpoint_returns_path(self, temp_sessions_dir, sample_context):
        """save_checkpoint should return the path to the saved checkpoint."""
        path = save_checkpoint(sample_context, "phase_0")

        assert isinstance(path, Path)
        assert path.exists()
        assert path.name == "checkpoint_phase_0.json"


class TestLoadCheckpoint:
    """Tests for load_checkpoint function."""

    def test_load_checkpoint_returns_none_when_not_exists(
        self, temp_sessions_dir, sample_context
    ):
        """Loading a checkpoint that doesn't exist should return None."""
        result = load_checkpoint(sample_context.jira_key)
        assert result is None

    def test_load_checkpoint_restores_context(
        self, temp_sessions_dir, populated_context
    ):
        """Loading a checkpoint should restore the VerificationContext."""
        save_checkpoint(populated_context, "phase_1")

        result = load_checkpoint(populated_context.jira_key)
        assert result is not None

        ctx, phase_idx = result
        assert ctx.jira_key == "TEST-001"
        assert ctx.jira_summary == "Test Story"
        assert ctx.current_phase == "phase_1"
        assert len(ctx.classifications) == 1
        assert len(ctx.postconditions) == 1

    def test_load_checkpoint_returns_phase_index(
        self, temp_sessions_dir, populated_context
    ):
        """Loading a checkpoint should return the correct phase index."""
        for phase_name, phase_idx in [("phase_1", 0), ("phase_2", 1), ("phase_3", 2)]:
            populated_context.current_phase = phase_name
            save_checkpoint(populated_context, phase_name)

            result = load_checkpoint(populated_context.jira_key)
            ctx, idx = result
            assert ctx.current_phase == phase_name
            # Phase index is the index in PHASES list
            assert idx == PHASES.index(phase_name)

    def test_load_checkpoint_gets_most_recent(
        self, temp_sessions_dir, populated_context
    ):
        """Loading should get the most recent checkpoint, not the first."""
        # Save multiple checkpoints
        populated_context.current_phase = "phase_1"
        save_checkpoint(populated_context, "phase_1")

        populated_context.current_phase = "phase_2"
        populated_context.postconditions.append({"ac_index": 1, "status": 201})
        save_checkpoint(populated_context, "phase_2")

        # Load should get phase_2 (most recent)
        ctx, phase_idx = load_checkpoint(populated_context.jira_key)
        assert ctx.current_phase == "phase_2"
        assert len(ctx.postconditions) == 2

    def test_load_checkpoint_preserves_log(
        self, temp_sessions_dir, populated_context
    ):
        """Loaded checkpoint should preserve the full negotiation log."""
        populated_context.negotiation_log = [
            {
                "phase": "phase_0",
                "role": "ai",
                "content": "Step 1",
                "timestamp": "2026-03-25T10:00:00Z",
            },
            {
                "phase": "phase_0",
                "role": "human",
                "content": "Answer to Q1",
                "timestamp": "2026-03-25T10:05:00Z",
            },
            {
                "phase": "phase_1",
                "role": "ai",
                "content": "Classified all ACs",
                "timestamp": "2026-03-25T10:10:00Z",
            },
        ]

        save_checkpoint(populated_context, "phase_1")
        ctx, _ = load_checkpoint(populated_context.jira_key)

        assert len(ctx.negotiation_log) == 3
        assert ctx.negotiation_log[0]["content"] == "Step 1"
        assert ctx.negotiation_log[1]["content"] == "Answer to Q1"

    def test_load_checkpoint_handles_missing_optional_fields(
        self, temp_sessions_dir, sample_context
    ):
        """Loading should handle missing optional fields gracefully."""
        # Manually create a minimal checkpoint
        session_dir = temp_sessions_dir / sample_context.jira_key
        session_dir.mkdir(parents=True, exist_ok=True)

        minimal_data = {
            "jira_key": "TEST-001",
            "jira_summary": "Test Story",
            "current_phase": "phase_0",
            "raw_acceptance_criteria": [],
            "constitution": {},
            # Missing most optional fields
        }

        with open(session_dir / "checkpoint_phase_0.json", "w") as f:
            json.dump(minimal_data, f)

        ctx, phase_idx = load_checkpoint(sample_context.jira_key)
        assert ctx.jira_key == "TEST-001"
        assert ctx.classifications == []
        assert ctx.postconditions == []
        assert ctx.negotiation_log == []
        assert ctx.approved is False


class TestHasCheckpoint:
    """Tests for has_checkpoint function."""

    def test_has_checkpoint_returns_false_when_no_session(
        self, temp_sessions_dir, sample_context
    ):
        """has_checkpoint should return False if no session directory exists."""
        assert not has_checkpoint(sample_context.jira_key)

    def test_has_checkpoint_returns_false_when_no_checkpoints(
        self, temp_sessions_dir, sample_context
    ):
        """has_checkpoint should return False if session exists but has no checkpoints."""
        session_dir = temp_sessions_dir / sample_context.jira_key
        session_dir.mkdir(parents=True, exist_ok=True)
        # Directory exists but no checkpoint files

        assert not has_checkpoint(sample_context.jira_key)

    def test_has_checkpoint_returns_true_when_checkpoint_exists(
        self, temp_sessions_dir, populated_context
    ):
        """has_checkpoint should return True if a checkpoint exists."""
        save_checkpoint(populated_context, "phase_1")

        assert has_checkpoint(populated_context.jira_key)

    def test_has_checkpoint_returns_true_for_multiple_checkpoints(
        self, temp_sessions_dir, populated_context
    ):
        """has_checkpoint should return True if multiple checkpoints exist."""
        save_checkpoint(populated_context, "phase_1")
        save_checkpoint(populated_context, "phase_2")
        save_checkpoint(populated_context, "phase_3")

        assert has_checkpoint(populated_context.jira_key)


class TestGetSessionInfo:
    """Tests for get_session_info function."""

    def test_get_session_info_returns_none_when_not_exists(
        self, temp_sessions_dir, sample_context
    ):
        """get_session_info should return None if no session exists."""
        result = get_session_info(sample_context.jira_key)
        assert result is None

    def test_get_session_info_returns_metadata(
        self, temp_sessions_dir, populated_context
    ):
        """get_session_info should return session metadata."""
        save_checkpoint(populated_context, "phase_1")

        info = get_session_info(populated_context.jira_key)
        assert info is not None
        assert info["jira_key"] == "TEST-001"
        assert info["current_phase"] == "phase_1"
        assert info["checkpoint_path"].endswith("checkpoint_phase_1.json")
        assert info["log_entries"] == 1
        assert info["approved"] is False

    def test_get_session_info_reflects_approved_status(
        self, temp_sessions_dir, populated_context
    ):
        """get_session_info should reflect approval status."""
        populated_context.approved = True
        populated_context.approved_by = "developer"
        save_checkpoint(populated_context, "phase_7")

        info = get_session_info(populated_context.jira_key)
        assert info["approved"] is True

    def test_get_session_info_uses_latest_checkpoint(
        self, temp_sessions_dir, populated_context
    ):
        """get_session_info should return info from the latest checkpoint."""
        populated_context.current_phase = "phase_1"
        save_checkpoint(populated_context, "phase_1")

        populated_context.current_phase = "phase_2"
        populated_context.negotiation_log.append(
            {
                "phase": "phase_1",
                "role": "ai",
                "content": "New phase output",
                "timestamp": "2026-03-25T10:15:00Z",
            }
        )
        save_checkpoint(populated_context, "phase_2")

        info = get_session_info(populated_context.jira_key)
        assert info["current_phase"] == "phase_2"
        assert info["log_entries"] == 2  # Original + new one


class TestClearSession:
    """Tests for clear_session function."""

    def test_clear_session_removes_directory(self, temp_sessions_dir, populated_context):
        """clear_session should remove the entire session directory."""
        save_checkpoint(populated_context, "phase_1")
        session_dir = temp_sessions_dir / populated_context.jira_key
        assert session_dir.exists()

        result = clear_session(populated_context.jira_key)

        assert result is True
        assert not session_dir.exists()

    def test_clear_session_returns_false_if_not_exists(
        self, temp_sessions_dir, sample_context
    ):
        """clear_session should return False if session doesn't exist."""
        result = clear_session(sample_context.jira_key)
        assert result is False

    def test_clear_session_cannot_be_loaded_after(
        self, temp_sessions_dir, populated_context
    ):
        """After clear_session, load_checkpoint should return None."""
        save_checkpoint(populated_context, "phase_1")
        clear_session(populated_context.jira_key)

        result = load_checkpoint(populated_context.jira_key)
        assert result is None


class TestHarnessIntegration:
    """Tests for integration with NegotiationHarness."""

    def test_harness_advance_phase_saves_checkpoint(
        self, temp_sessions_dir, sample_context
    ):
        """NegotiationHarness.advance_phase should save a checkpoint."""
        harness = NegotiationHarness(sample_context)

        # Manually set phase data to satisfy exit conditions
        sample_context.classifications = [
            {"ac_index": 0, "type": "api_behavior"},
            {"ac_index": 1, "type": "api_behavior"},
        ]

        # Advance from phase_0 to phase_1
        new_phase = harness.advance_phase()
        assert new_phase == "phase_1"

        # Check that checkpoint was saved
        assert has_checkpoint(sample_context.jira_key)
        ctx, phase_idx = load_checkpoint(sample_context.jira_key)
        assert ctx.current_phase == "phase_1"
        assert phase_idx == 1  # phase_1 is index 1 in PHASES

    def test_harness_checkpoints_accumulate(
        self, temp_sessions_dir, sample_context
    ):
        """Multiple advance_phase calls should create multiple checkpoints."""
        harness = NegotiationHarness(sample_context)

        # Phase 0 -> Phase 1
        sample_context.classifications = [
            {"ac_index": 0, "type": "api_behavior"},
            {"ac_index": 1, "type": "api_behavior"},
        ]
        harness.advance_phase()

        # Phase 1 -> Phase 2
        sample_context.postconditions = [
            {"ac_index": 0, "status": 200},
            {"ac_index": 1, "status": 200},
        ]
        harness.advance_phase()

        # Check that we have multiple checkpoint files
        session_dir = temp_sessions_dir / sample_context.jira_key
        checkpoints = list(session_dir.glob("checkpoint_*.json"))
        assert len(checkpoints) == 2

        # Load the latest (should be phase_2)
        ctx, phase_idx = load_checkpoint(sample_context.jira_key)
        assert ctx.current_phase == "phase_2"


class TestRoundTrip:
    """End-to-end tests for saving and loading a context."""

    def test_roundtrip_preserves_all_data(self, temp_sessions_dir, populated_context):
        """Saving and loading should preserve all context data."""
        # Add some extra data
        populated_context.preconditions = [
            {"id": "PRE-001", "description": "User exists", "category": "data_existence"}
        ]
        populated_context.failure_modes = [
            {"id": "FAIL-001", "description": "User not found", "status": 404}
        ]
        populated_context.invariants = [
            {"name": "security", "rule": "All API calls require JWT"}
        ]
        populated_context.approved = True
        populated_context.approved_by = "qa-lead"
        populated_context.approved_at = "2026-03-25T12:00:00Z"

        # Save
        save_checkpoint(populated_context, "phase_3")

        # Load
        ctx, phase_idx = load_checkpoint(populated_context.jira_key)

        # Verify all data matches
        assert ctx.jira_key == populated_context.jira_key
        assert ctx.jira_summary == populated_context.jira_summary
        assert ctx.current_phase == populated_context.current_phase
        assert len(ctx.classifications) == len(populated_context.classifications)
        assert len(ctx.postconditions) == len(populated_context.postconditions)
        assert len(ctx.preconditions) == len(populated_context.preconditions)
        assert len(ctx.failure_modes) == len(populated_context.failure_modes)
        assert len(ctx.invariants) == len(populated_context.invariants)
        assert ctx.approved == populated_context.approved
        assert ctx.approved_by == populated_context.approved_by
        assert ctx.approved_at == populated_context.approved_at

    def test_roundtrip_preserves_constitution(self, temp_sessions_dir, sample_context):
        """Constitution should be preserved exactly."""
        constitution = {
            "project": {"framework": "spring-boot", "language": "java"},
            "api": {"base_path": "/api/v1", "auth": "jwt"},
            "database": {"type": "postgresql", "migrations": "true"},
        }
        sample_context.constitution = constitution

        save_checkpoint(sample_context, "phase_0")
        ctx, _ = load_checkpoint(sample_context.jira_key)

        assert ctx.constitution == constitution

    def test_roundtrip_preserves_complex_structures(
        self, temp_sessions_dir, sample_context
    ):
        """Complex nested structures should be preserved."""
        sample_context.traceability_map = {
            "ac_mappings": [
                {
                    "ac_checkbox": 0,
                    "specification_refs": ["GET /api/v1/users/me"],
                    "verification_refs": ["test_user_can_get_profile"],
                }
            ]
        }
        sample_context.verification_routing = {
            "GET /api/v1/users/me": {
                "skill": "python_unit_test",
                "template": "rest_api_contract_testing",
            }
        }

        save_checkpoint(sample_context, "phase_4")
        ctx, _ = load_checkpoint(sample_context.jira_key)

        assert ctx.traceability_map == sample_context.traceability_map
        assert ctx.verification_routing == sample_context.verification_routing
