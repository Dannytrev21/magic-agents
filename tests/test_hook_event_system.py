"""Tests for Epic P9: Hook & Event System.

P9.1: Hook Registry with Lifecycle Points
P9.2: Integrate Hooks into NegotiationHarness
P9.3: Configurable Hooks via Constitution
"""

import logging
import time

import pytest


# ---------------------------------------------------------------
# P9.1 — Hook Registry with Lifecycle Points
# ---------------------------------------------------------------


class TestHookEvent:
    """HookEvent should carry lifecycle event data."""

    def test_hook_event_fields(self):
        from verify.hooks import HookEvent

        event = HookEvent(
            lifecycle_point="post_phase",
            session_id="s1",
            phase_name="phase_1",
            data={"result_count": 5},
        )
        assert event.lifecycle_point == "post_phase"
        assert event.session_id == "s1"
        assert event.phase_name == "phase_1"
        assert event.data["result_count"] == 5

    def test_hook_event_has_timestamp(self):
        from verify.hooks import HookEvent

        event = HookEvent(
            lifecycle_point="pre_phase",
            session_id="s1",
            phase_name="phase_1",
        )
        assert event.timestamp  # auto-populated


class TestHookRegistryBasics:
    """HookRegistry should register and fire hooks."""

    def test_register_and_fire(self):
        from verify.hooks import HookEvent, HookRegistry

        registry = HookRegistry()
        events = []
        registry.register("post_phase", lambda e: events.append(e))
        registry.fire(
            "post_phase",
            HookEvent(
                lifecycle_point="post_phase",
                session_id="s1",
                phase_name="phase_1",
            ),
        )
        assert len(events) == 1

    def test_multiple_hooks_order(self):
        from verify.hooks import HookEvent, HookRegistry

        registry = HookRegistry()
        order = []
        registry.register("post_phase", lambda e: order.append("a"))
        registry.register("post_phase", lambda e: order.append("b"))
        registry.fire(
            "post_phase",
            HookEvent(lifecycle_point="post_phase", session_id="s1", phase_name="p1"),
        )
        assert order == ["a", "b"]

    def test_hook_failure_isolated(self, caplog):
        from verify.hooks import HookEvent, HookRegistry

        registry = HookRegistry()
        results = []
        registry.register("post_phase", lambda e: 1 / 0)
        registry.register("post_phase", lambda e: results.append("ok"))
        with caplog.at_level(logging.WARNING):
            registry.fire(
                "post_phase",
                HookEvent(
                    lifecycle_point="post_phase",
                    session_id="s1",
                    phase_name="p1",
                ),
            )
        assert results == ["ok"]

    def test_invalid_lifecycle_point_raises(self):
        from verify.hooks import HookRegistry

        registry = HookRegistry()
        with pytest.raises(ValueError, match="Invalid lifecycle point"):
            registry.register("nonexistent_point", lambda e: None)

    def test_no_hooks_fire_silently(self):
        from verify.hooks import HookEvent, HookRegistry

        registry = HookRegistry()
        # Should not raise
        registry.fire(
            "pre_phase",
            HookEvent(lifecycle_point="pre_phase", session_id="s1", phase_name="p1"),
        )

    def test_all_lifecycle_points_valid(self):
        from verify.hooks import LIFECYCLE_POINTS, HookRegistry

        registry = HookRegistry()
        for point in LIFECYCLE_POINTS:
            registry.register(point, lambda e: None)  # no error

    def test_fire_returns_none_on_success(self):
        from verify.hooks import HookEvent, HookRegistry

        registry = HookRegistry()
        registry.register("pre_phase", lambda e: None)
        result = registry.fire(
            "pre_phase",
            HookEvent(lifecycle_point="pre_phase", session_id="s1", phase_name="p1"),
        )
        assert result is None


# ---------------------------------------------------------------
# P9.2 — Integrate Hooks into NegotiationHarness
# ---------------------------------------------------------------


class TestHarnessHookIntegration:
    """NegotiationHarness should accept and fire hooks at phase boundaries."""

    def test_harness_accepts_hook_registry(self):
        from verify.context import VerificationContext
        from verify.hooks import HookRegistry
        from verify.negotiation.harness import NegotiationHarness

        ctx = VerificationContext(
            jira_key="HOOK-001",
            jira_summary="Hook Test",
            raw_acceptance_criteria=[{"index": 0, "text": "AC1", "checked": False}],
            constitution={},
        )
        registry = HookRegistry()
        harness = NegotiationHarness(ctx, hooks=registry)
        assert harness.hooks is registry

    def test_harness_without_hooks_still_works(self):
        from verify.context import VerificationContext
        from verify.negotiation.harness import NegotiationHarness

        ctx = VerificationContext(
            jira_key="HOOK-002",
            jira_summary="No Hooks Test",
            raw_acceptance_criteria=[{"index": 0, "text": "AC1", "checked": False}],
            constitution={},
        )
        harness = NegotiationHarness(ctx)
        assert harness.hooks is None

    def test_advance_phase_fires_hooks(self, monkeypatch, tmp_path):
        from verify.context import VerificationContext
        from verify.hooks import HookRegistry
        from verify.negotiation.harness import NegotiationHarness

        monkeypatch.setattr(
            "verify.negotiation.checkpoint.SESSIONS_DIR",
            tmp_path,
        )

        ctx = VerificationContext(
            jira_key="HOOK-003",
            jira_summary="Advance Hook Test",
            raw_acceptance_criteria=[
                {"index": 0, "text": "AC1", "checked": False},
            ],
            constitution={},
        )
        ctx.classifications = [{"ac_index": 0, "type": "api_behavior"}]

        events = []
        registry = HookRegistry()
        registry.register("post_phase", lambda e: events.append(e.data.get("phase_name")))

        harness = NegotiationHarness(ctx, hooks=registry)
        harness.advance_phase()
        assert "phase_1" in events


# ---------------------------------------------------------------
# P9.3 — Configurable Hooks via Constitution
# ---------------------------------------------------------------


class TestConstitutionHooks:
    """HookRegistry.from_constitution should register shell hooks."""

    def test_from_constitution_creates_registry(self):
        from verify.hooks import HookRegistry

        constitution = {"hooks": {"post_phase": "echo 'phase done'"}}
        registry = HookRegistry.from_constitution(constitution)
        assert len(registry._hooks.get("post_phase", [])) == 1

    def test_shell_hook_executes(self, tmp_path):
        from verify.hooks import HookEvent, HookRegistry

        marker = tmp_path / "hook_fired.txt"
        constitution = {"hooks": {"post_phase": f"touch {marker}"}}
        registry = HookRegistry.from_constitution(constitution)
        registry.fire(
            "post_phase",
            HookEvent(lifecycle_point="post_phase", session_id="s1", phase_name="p1"),
        )
        assert marker.exists()

    def test_shell_hook_receives_env_vars(self, tmp_path):
        from verify.hooks import HookEvent, HookRegistry

        output_file = tmp_path / "env_output.txt"
        cmd = f'echo "$HOOK_EVENT:$HOOK_SESSION_ID:$HOOK_PHASE" > {output_file}'
        constitution = {"hooks": {"post_phase": cmd}}
        registry = HookRegistry.from_constitution(constitution)
        registry.fire(
            "post_phase",
            HookEvent(
                lifecycle_point="post_phase",
                session_id="test-sess",
                phase_name="phase_2",
            ),
        )
        content = output_file.read_text().strip()
        assert "post_phase" in content
        assert "test-sess" in content
        assert "phase_2" in content

    def test_shell_hook_timeout_handled(self, caplog):
        from verify.hooks import HookEvent, HookRegistry

        constitution = {"hooks": {"post_phase": "sleep 60"}}
        registry = HookRegistry.from_constitution(constitution, timeout=1)
        with caplog.at_level(logging.WARNING):
            registry.fire(
                "post_phase",
                HookEvent(
                    lifecycle_point="post_phase",
                    session_id="s1",
                    phase_name="p1",
                ),
            )
        assert "timeout" in caplog.text.lower() or "timed out" in caplog.text.lower()

    def test_empty_constitution_hooks(self):
        from verify.hooks import HookRegistry

        registry = HookRegistry.from_constitution({})
        assert len(registry._hooks) == 0

    def test_constitution_with_multiple_hooks(self, tmp_path):
        from verify.hooks import HookEvent, HookRegistry

        marker1 = tmp_path / "pre.txt"
        marker2 = tmp_path / "post.txt"
        constitution = {
            "hooks": {
                "pre_phase": f"touch {marker1}",
                "post_phase": f"touch {marker2}",
            }
        }
        registry = HookRegistry.from_constitution(constitution)
        registry.fire(
            "pre_phase",
            HookEvent(lifecycle_point="pre_phase", session_id="s1", phase_name="p1"),
        )
        registry.fire(
            "post_phase",
            HookEvent(lifecycle_point="post_phase", session_id="s1", phase_name="p1"),
        )
        assert marker1.exists()
        assert marker2.exists()
