"""Tests for Epic P7: Session Cost Accounting.

P7.1: Persist Token Usage in Checkpoints
P7.2: Session Cost Summary Endpoint
P7.3: Cost Alerts via SSE Events
"""

import json
import time
from pathlib import Path

import pytest

from verify.backpressure import BackPressureController, PhaseCostReport
from verify.context import VerificationContext
from verify.negotiation.checkpoint import (
    load_checkpoint,
    save_checkpoint,
)
from verify.runtime import NegotiationEvent, RuntimeEvent


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------


@pytest.fixture
def temp_sessions_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "verify.negotiation.checkpoint.SESSIONS_DIR",
        tmp_path,
    )
    return tmp_path


@pytest.fixture
def sample_context():
    return VerificationContext(
        jira_key="COST-001",
        jira_summary="Cost Accounting Story",
        raw_acceptance_criteria=[
            {"index": 0, "text": "User can list items", "checked": False},
        ],
        constitution={"project": {"framework": "spring-boot"}},
    )


@pytest.fixture
def controller():
    return BackPressureController(
        max_tokens=500_000,
        warn_tokens=400_000,
        max_api_calls=50,
        warn_api_calls=40,
    )


# ---------------------------------------------------------------
# P7.1 — Persist Token Usage in Checkpoints
# ---------------------------------------------------------------


class TestBackPressureControllerSerialization:
    """BackPressureController should serialize/deserialize its state."""

    def test_to_dict_captures_state(self, controller):
        controller.api_calls = 5
        controller.tokens_used = 10_000
        controller.retries_by_phase = {"phase_1": 1}

        data = controller.to_dict()

        assert data["api_calls"] == 5
        assert data["tokens_used"] == 10_000
        assert data["retries_by_phase"] == {"phase_1": 1}
        assert "wall_clock_seconds" in data
        assert "max_tokens" in data
        assert "max_api_calls" in data

    def test_from_dict_restores_state(self):
        data = {
            "api_calls": 7,
            "tokens_used": 20_000,
            "wall_clock_seconds": 42.5,
            "retries_by_phase": {"phase_2": 2},
            "max_api_calls": 50,
            "max_tokens": 500_000,
            "max_wall_clock_seconds": 600,
            "max_retries_per_phase": 3,
            "warn_api_calls": 40,
            "warn_tokens": 400_000,
        }

        restored = BackPressureController.from_dict(data)

        assert restored.api_calls == 7
        assert restored.tokens_used == 20_000
        assert restored.retries_by_phase == {"phase_2": 2}
        assert restored.max_tokens == 500_000

    def test_from_dict_defaults_missing_fields(self):
        """Old checkpoint data without full controller state should still load."""
        data = {"api_calls": 3, "tokens_used": 5000}
        restored = BackPressureController.from_dict(data)

        assert restored.api_calls == 3
        assert restored.tokens_used == 5000
        assert restored.max_tokens == 500_000  # default
        assert restored.retries_by_phase == {}

    def test_from_dict_empty_returns_defaults(self):
        """An empty dict should produce a zeroed controller."""
        restored = BackPressureController.from_dict({})

        assert restored.api_calls == 0
        assert restored.tokens_used == 0

    def test_round_trip_to_dict_from_dict(self, controller):
        controller.api_calls = 12
        controller.tokens_used = 99_000
        controller.retries_by_phase = {"phase_1": 1, "phase_3": 2}

        data = controller.to_dict()
        restored = BackPressureController.from_dict(data)

        assert restored.api_calls == controller.api_calls
        assert restored.tokens_used == controller.tokens_used
        assert restored.retries_by_phase == controller.retries_by_phase
        assert restored.max_tokens == controller.max_tokens
        assert restored.warn_tokens == controller.warn_tokens


class TestCheckpointUsagePersistence:
    """save/load_checkpoint should persist BackPressureController state."""

    def test_checkpoint_includes_usage_from_controller(
        self, temp_sessions_dir, sample_context, controller
    ):
        controller.api_calls = 5
        controller.tokens_used = 10_000

        save_checkpoint(sample_context, "phase_3", backpressure=controller)

        data = json.loads(
            (temp_sessions_dir / "COST-001" / "checkpoint_phase_3.json").read_text()
        )
        assert data["usage"]["api_calls"] == 5
        assert data["usage"]["tokens_used"] == 10_000

    def test_checkpoint_without_controller_uses_context_usage(
        self, temp_sessions_dir, sample_context
    ):
        """When no controller is passed, context.usage dict is still saved."""
        sample_context.usage = {"api_calls": 3, "tokens_used": 7000}

        save_checkpoint(sample_context, "phase_1")

        data = json.loads(
            (temp_sessions_dir / "COST-001" / "checkpoint_phase_1.json").read_text()
        )
        assert data["usage"]["api_calls"] == 3

    def test_load_checkpoint_returns_controller(
        self, temp_sessions_dir, sample_context, controller
    ):
        controller.api_calls = 8
        controller.tokens_used = 25_000
        controller.retries_by_phase = {"phase_1": 1}

        save_checkpoint(sample_context, "phase_2", backpressure=controller)

        result = load_checkpoint("COST-001")
        assert result is not None
        ctx, phase_idx, restored_controller = result

        assert restored_controller.api_calls == 8
        assert restored_controller.tokens_used == 25_000
        assert restored_controller.retries_by_phase == {"phase_1": 1}

    def test_old_checkpoint_backward_compat(self, temp_sessions_dir):
        """Old checkpoints without usage data should load with zeroed controller."""
        session_dir = temp_sessions_dir / "OLD-001"
        session_dir.mkdir(parents=True)

        (session_dir / "checkpoint_phase_1.json").write_text(
            json.dumps({
                "jira_key": "OLD-001",
                "jira_summary": "Old Story",
                "current_phase": "phase_1",
                "raw_acceptance_criteria": [],
                "constitution": {},
            })
        )

        result = load_checkpoint("OLD-001")
        assert result is not None
        ctx, phase_idx, restored_controller = result

        assert restored_controller.api_calls == 0
        assert restored_controller.tokens_used == 0

    def test_round_trip_save_load_save_identical(
        self, temp_sessions_dir, sample_context, controller
    ):
        controller.api_calls = 10
        controller.tokens_used = 50_000
        controller.retries_by_phase = {"phase_1": 2}

        save_checkpoint(sample_context, "phase_2", backpressure=controller)
        _, _, restored = load_checkpoint("COST-001")

        # Save again with restored controller
        save_checkpoint(sample_context, "phase_2b", backpressure=restored)

        data1 = json.loads(
            (temp_sessions_dir / "COST-001" / "checkpoint_phase_2.json").read_text()
        )
        data2 = json.loads(
            (temp_sessions_dir / "COST-001" / "checkpoint_phase_2b.json").read_text()
        )

        # Usage should be identical (wall_clock_seconds may differ slightly)
        assert data1["usage"]["api_calls"] == data2["usage"]["api_calls"]
        assert data1["usage"]["tokens_used"] == data2["usage"]["tokens_used"]
        assert data1["usage"]["retries_by_phase"] == data2["usage"]["retries_by_phase"]

    def test_controller_usage_overwrites_context_usage(
        self, temp_sessions_dir, sample_context, controller
    ):
        """When a controller is provided, its data takes precedence over context.usage."""
        sample_context.usage = {"api_calls": 99, "tokens_used": 999}
        controller.api_calls = 5
        controller.tokens_used = 10_000

        save_checkpoint(sample_context, "phase_1", backpressure=controller)

        data = json.loads(
            (temp_sessions_dir / "COST-001" / "checkpoint_phase_1.json").read_text()
        )
        assert data["usage"]["api_calls"] == 5  # from controller, not context


# ---------------------------------------------------------------
# P7.2 — Session Cost Summary Endpoint
# ---------------------------------------------------------------


class TestCostSummaryEndpoint:
    """GET /api/session/{session_id}/cost should return cost data."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from verify.negotiation.web import app, SESSION_STORE

        SESSION_STORE.clear()
        return TestClient(app)

    @pytest.fixture
    def session_with_usage(self, client):
        from verify.negotiation.web import SESSION_STORE

        ctx = VerificationContext(
            jira_key="COST-API-001",
            jira_summary="Cost API Test",
            raw_acceptance_criteria=[],
            constitution={},
        )
        state = SESSION_STORE.create(ctx)

        # Wire up a controller with known usage
        controller = BackPressureController(max_tokens=100_000, warn_tokens=80_000)
        controller.api_calls = 10
        controller.tokens_used = 45_000
        state.backpressure = controller

        # Add per-phase cost reports
        state.phase_cost_reports = [
            PhaseCostReport(
                phase_name="phase_1",
                api_calls=3,
                tokens_in=5000,
                tokens_out=2000,
                wall_clock_seconds=12.5,
                retries=0,
                status="success",
            ),
            PhaseCostReport(
                phase_name="phase_2",
                api_calls=7,
                tokens_in=25000,
                tokens_out=13000,
                wall_clock_seconds=30.0,
                retries=1,
                status="success",
            ),
        ]
        return state

    def test_cost_endpoint_returns_200(self, client, session_with_usage):
        resp = client.get(f"/api/session/{session_with_usage.session_id}/cost")
        assert resp.status_code == 200

    def test_cost_endpoint_returns_token_counts(self, client, session_with_usage):
        resp = client.get(f"/api/session/{session_with_usage.session_id}/cost")
        data = resp.json()

        assert "total_input_tokens" in data
        assert "total_output_tokens" in data
        assert "total_api_calls" in data
        assert data["total_api_calls"] == 10

    def test_cost_endpoint_estimated_cost(self, client, session_with_usage):
        resp = client.get(f"/api/session/{session_with_usage.session_id}/cost")
        data = resp.json()

        assert "estimated_cost_usd" in data
        assert isinstance(data["estimated_cost_usd"], float)
        assert data["estimated_cost_usd"] > 0

    def test_cost_endpoint_budget_utilization(self, client, session_with_usage):
        resp = client.get(f"/api/session/{session_with_usage.session_id}/cost")
        data = resp.json()

        assert "budget_utilization_pct" in data
        # 45000 / 100000 * 100 = 45.0%
        assert data["budget_utilization_pct"] == pytest.approx(45.0)

    def test_cost_endpoint_per_phase_breakdown(self, client, session_with_usage):
        resp = client.get(f"/api/session/{session_with_usage.session_id}/cost")
        data = resp.json()

        assert "phases" in data
        assert len(data["phases"]) == 2
        assert data["phases"][0]["phase_name"] == "phase_1"
        assert data["phases"][1]["phase_name"] == "phase_2"

    def test_cost_endpoint_404_unknown_session(self, client):
        resp = client.get("/api/session/nonexistent/cost")
        assert resp.status_code == 404

    def test_cost_endpoint_no_usage_returns_zeros(self, client):
        from verify.negotiation.web import SESSION_STORE

        ctx = VerificationContext(
            jira_key="COST-EMPTY",
            jira_summary="Empty Cost",
            raw_acceptance_criteria=[],
            constitution={},
        )
        state = SESSION_STORE.create(ctx)

        resp = client.get(f"/api/session/{state.session_id}/cost")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_api_calls"] == 0
        assert data["estimated_cost_usd"] == 0.0
        assert data["budget_utilization_pct"] == 0.0


# ---------------------------------------------------------------
# P7.3 — Cost Alerts via SSE Events
# ---------------------------------------------------------------


class TestBudgetEvents:
    """BackPressureController should emit budget_warning and budget_exceeded events."""

    def test_budget_warning_emitted_on_soft_limit(self):
        events = []
        controller = BackPressureController(max_tokens=100, warn_tokens=80)
        controller.tokens_used = 85

        controller.emit_budget_events(events.append)

        assert any(e.type == "budget_warning" for e in events)

    def test_budget_exceeded_emitted_on_hard_limit(self):
        events = []
        controller = BackPressureController(max_tokens=100, warn_tokens=80)
        controller.tokens_used = 105

        controller.emit_budget_events(events.append)

        assert any(e.type == "budget_exceeded" for e in events)

    def test_no_event_when_below_thresholds(self):
        events = []
        controller = BackPressureController(max_tokens=100, warn_tokens=80)
        controller.tokens_used = 50

        controller.emit_budget_events(events.append)

        assert len(events) == 0

    def test_budget_warning_deduplicated(self):
        events = []
        controller = BackPressureController(max_tokens=100, warn_tokens=80)
        controller.tokens_used = 85

        controller.emit_budget_events(events.append)
        controller.emit_budget_events(events.append)

        warnings = [e for e in events if e.type == "budget_warning"]
        assert len(warnings) == 1

    def test_budget_exceeded_deduplicated(self):
        events = []
        controller = BackPressureController(max_tokens=100, warn_tokens=80)
        controller.tokens_used = 105

        controller.emit_budget_events(events.append)
        controller.emit_budget_events(events.append)

        exceeded = [e for e in events if e.type == "budget_exceeded"]
        assert len(exceeded) == 1

    def test_warning_fires_before_exceeded(self):
        events = []
        controller = BackPressureController(max_tokens=100, warn_tokens=80)

        # First cross warning threshold
        controller.tokens_used = 85
        controller.emit_budget_events(events.append)

        # Then cross hard limit
        controller.tokens_used = 105
        controller.emit_budget_events(events.append)

        types = [e.type for e in events]
        assert types.index("budget_warning") < types.index("budget_exceeded")

    def test_event_includes_usage_summary(self):
        events = []
        controller = BackPressureController(max_tokens=100, warn_tokens=80)
        controller.tokens_used = 85

        controller.emit_budget_events(events.append)

        event = next(e for e in events if e.type == "budget_warning")
        assert "tokens_used" in event.data
        assert "budget_limit" in event.data
        assert event.data["tokens_used"] == 85
        assert event.data["budget_limit"] == 100

    def test_api_calls_soft_limit_warning(self):
        events = []
        controller = BackPressureController(
            max_api_calls=50, warn_api_calls=40, max_tokens=500_000, warn_tokens=400_000
        )
        controller.api_calls = 42

        controller.emit_budget_events(events.append)

        assert any(
            e.type == "budget_warning" and e.data.get("limit_type") == "api_calls"
            for e in events
        )

    def test_budget_events_are_valid_runtime_events(self):
        events = []
        controller = BackPressureController(max_tokens=100, warn_tokens=80)
        controller.tokens_used = 85

        controller.emit_budget_events(events.append)

        for event in events:
            assert isinstance(event, RuntimeEvent)
            # Should be serializable as SSE
            sse = event.as_sse()
            assert "event: budget_warning" in sse
