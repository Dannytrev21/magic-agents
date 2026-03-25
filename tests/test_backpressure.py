"""Tests for Back-Pressure Controller (Feature 20)."""

import time
import pytest
import os
from verify.backpressure import BackPressureController, BackPressureLimitExceeded
from verify.llm_client import LLMClient


class TestBackPressureControllerDefaults:
    """Test BackPressureController initialization and default limits."""

    def test_default_limits(self):
        """Controller should initialize with correct default hard limits."""
        controller = BackPressureController()

        assert controller.max_api_calls == 50
        assert controller.max_tokens == 500_000
        assert controller.max_wall_clock_seconds == 600  # 10 minutes
        assert controller.max_retries_per_phase == 3

    def test_default_soft_limits(self):
        """Controller should initialize with correct default soft limits."""
        controller = BackPressureController()

        assert controller.warn_api_calls == 40
        assert controller.warn_tokens == 400_000

    def test_initial_state(self):
        """Controller should start with zero usage."""
        controller = BackPressureController()

        assert controller.api_calls == 0
        assert controller.tokens_used == 0
        assert controller.retries_by_phase == {}

    def test_custom_limits(self):
        """Controller should allow custom limits."""
        controller = BackPressureController(
            max_api_calls=100,
            max_tokens=1_000_000,
            warn_api_calls=80,
            warn_tokens=800_000,
        )

        assert controller.max_api_calls == 100
        assert controller.max_tokens == 1_000_000
        assert controller.warn_api_calls == 80
        assert controller.warn_tokens == 800_000


class TestAPICallTracking:
    """Test API call and token tracking."""

    def test_record_single_api_call(self):
        """Should track a single API call."""
        controller = BackPressureController()

        controller.record_api_call(tokens_in=100, tokens_out=200)

        assert controller.api_calls == 1
        assert controller.tokens_used == 300

    def test_record_multiple_api_calls(self):
        """Should accumulate multiple API calls."""
        controller = BackPressureController()

        controller.record_api_call(tokens_in=100, tokens_out=200)
        controller.record_api_call(tokens_in=150, tokens_out=250)
        controller.record_api_call(tokens_in=200, tokens_out=300)

        assert controller.api_calls == 3
        assert controller.tokens_used == 1200  # 100+200+150+250+200+300

    def test_can_proceed_when_below_limits(self):
        """Should return True when below all limits."""
        controller = BackPressureController()

        controller.record_api_call(tokens_in=100, tokens_out=200)

        assert controller.can_proceed() is True

    def test_can_proceed_when_at_soft_limit(self):
        """Should return True even when at soft limits (hard limit is different)."""
        controller = BackPressureController(
            warn_api_calls=1,
            warn_tokens=300,
        )

        controller.record_api_call(tokens_in=100, tokens_out=200)

        assert controller.can_proceed() is True


class TestHardLimitEnforcement:
    """Test enforcement of hard limits."""

    def test_api_call_hard_limit(self):
        """Should raise exception when exceeding API call hard limit."""
        controller = BackPressureController(max_api_calls=5)

        for i in range(5):
            controller.record_api_call(tokens_in=10, tokens_out=10)

        # 6th call should exceed limit
        with pytest.raises(BackPressureLimitExceeded) as exc_info:
            controller.record_api_call(tokens_in=10, tokens_out=10)

        assert "API calls" in str(exc_info.value)
        assert controller.api_calls == 6

    def test_token_hard_limit(self):
        """Should raise exception when exceeding token hard limit."""
        controller = BackPressureController(max_tokens=1000)

        # Record exactly at limit - 1
        controller.record_api_call(tokens_in=500, tokens_out=499)

        # Next call should exceed
        with pytest.raises(BackPressureLimitExceeded) as exc_info:
            controller.record_api_call(tokens_in=1, tokens_out=1)

        assert "tokens" in str(exc_info.value)

    def test_wall_clock_hard_limit(self):
        """Should raise exception when exceeding wall clock time limit."""
        controller = BackPressureController(max_wall_clock_seconds=1)

        # Wait for more than 1 second
        time.sleep(1.1)

        with pytest.raises(BackPressureLimitExceeded) as exc_info:
            controller.record_api_call(tokens_in=1, tokens_out=1)

        assert "wall clock" in str(exc_info.value)

    def test_can_proceed_when_at_hard_limit(self):
        """Should return False when at hard API call limit."""
        controller = BackPressureController(max_api_calls=2)

        controller.record_api_call(tokens_in=10, tokens_out=10)
        controller.record_api_call(tokens_in=10, tokens_out=10)

        assert controller.can_proceed() is False


class TestWallClockTracking:
    """Test wall clock time tracking."""

    def test_wall_clock_tracking(self):
        """Should track elapsed wall clock time."""
        controller = BackPressureController()

        time.sleep(0.1)

        summary = controller.get_usage_summary()
        assert summary["wall_clock_seconds"] >= 0.1

    def test_wall_clock_in_minutes(self):
        """Should convert wall clock seconds to minutes."""
        controller = BackPressureController()

        time.sleep(0.06)

        summary = controller.get_usage_summary()
        assert summary["wall_clock_minutes"] >= 0.001

    def test_wall_clock_remaining(self):
        """Should calculate remaining wall clock time."""
        controller = BackPressureController(max_wall_clock_seconds=100)

        time.sleep(0.05)

        summary = controller.get_usage_summary()
        remaining = summary["wall_clock_remaining_seconds"]
        assert remaining < 100
        assert remaining > 99.9


class TestRetryTracking:
    """Test per-phase retry tracking."""

    def test_record_first_retry(self):
        """Should record first retry for a phase."""
        controller = BackPressureController()

        controller.record_retry("phase_1")

        assert controller.retries_by_phase["phase_1"] == 1

    def test_accumulate_retries(self):
        """Should accumulate retries for the same phase."""
        controller = BackPressureController(max_retries_per_phase=5)

        controller.record_retry("phase_1")
        controller.record_retry("phase_1")
        controller.record_retry("phase_1")

        assert controller.retries_by_phase["phase_1"] == 3

    def test_track_retries_per_phase(self):
        """Should track retries separately per phase."""
        controller = BackPressureController(max_retries_per_phase=10)

        controller.record_retry("phase_1")
        controller.record_retry("phase_1")
        controller.record_retry("phase_2")

        assert controller.retries_by_phase["phase_1"] == 2
        assert controller.retries_by_phase["phase_2"] == 1

    def test_exceed_retry_limit(self):
        """Should raise exception when exceeding retry limit for a phase."""
        controller = BackPressureController(max_retries_per_phase=2)

        controller.record_retry("phase_1")
        controller.record_retry("phase_1")

        with pytest.raises(BackPressureLimitExceeded) as exc_info:
            controller.record_retry("phase_1")

        assert "Max retries" in str(exc_info.value)
        assert "phase_1" in str(exc_info.value)


class TestCheckLimits:
    """Test the check_limits() method for warnings and errors."""

    def test_all_clear(self):
        """Should return (True, []) when all is clear."""
        controller = BackPressureController()

        ok, messages = controller.check_limits()

        assert ok is True
        assert messages == []

    def test_soft_limit_warning_api_calls(self):
        """Should warn when approaching API call soft limit."""
        controller = BackPressureController(
            max_api_calls=100,
            warn_api_calls=50,
        )

        for i in range(51):
            controller.record_api_call(tokens_in=10, tokens_out=10)

        ok, messages = controller.check_limits()

        assert ok is True
        assert len(messages) > 0
        assert any("approaching" in msg.lower() for msg in messages)

    def test_soft_limit_warning_tokens(self):
        """Should warn when approaching token soft limit."""
        controller = BackPressureController(
            max_tokens=1_000_000,
            warn_tokens=500_000,
        )

        # Record 501K tokens
        controller.record_api_call(tokens_in=250_500, tokens_out=250_500)

        ok, messages = controller.check_limits()

        assert ok is True
        assert len(messages) > 0
        assert any("tokens" in msg.lower() and "approaching" in msg.lower() for msg in messages)

    def test_hard_limit_error_api_calls(self):
        """Should return (False, [errors]) when hard API call limit exceeded."""
        controller = BackPressureController(max_api_calls=3)

        for i in range(3):
            controller.record_api_call(tokens_in=10, tokens_out=10)

        # At this point we're at limit, next call would exceed
        try:
            controller.record_api_call(tokens_in=10, tokens_out=10)
        except BackPressureLimitExceeded:
            pass

        ok, messages = controller.check_limits()

        assert ok is False
        assert len(messages) > 0
        assert any("API calls" in msg for msg in messages)

    def test_hard_limit_error_tokens(self):
        """Should return (False, [errors]) when hard token limit exceeded."""
        controller = BackPressureController(max_tokens=100)

        try:
            controller.record_api_call(tokens_in=51, tokens_out=51)
        except BackPressureLimitExceeded:
            pass

        ok, messages = controller.check_limits()

        assert ok is False
        assert len(messages) > 0


class TestUsageSummary:
    """Test the get_usage_summary() method."""

    def test_usage_summary_structure(self):
        """Summary should contain all expected fields."""
        controller = BackPressureController()

        controller.record_api_call(tokens_in=100, tokens_out=200)

        summary = controller.get_usage_summary()

        expected_keys = {
            "api_calls",
            "tokens_used",
            "wall_clock_seconds",
            "wall_clock_minutes",
            "retries_by_phase",
            "api_calls_remaining",
            "tokens_remaining",
            "wall_clock_remaining_seconds",
            "status",
        }
        assert set(summary.keys()) == expected_keys

    def test_usage_summary_initial_state(self):
        """Summary should reflect initial state correctly."""
        controller = BackPressureController(max_api_calls=50, max_tokens=500_000)

        summary = controller.get_usage_summary()

        assert summary["api_calls"] == 0
        assert summary["tokens_used"] == 0
        assert summary["api_calls_remaining"] == 50
        assert summary["tokens_remaining"] == 500_000
        assert summary["status"] == "ok"

    def test_usage_summary_after_calls(self):
        """Summary should reflect usage after API calls."""
        controller = BackPressureController(max_api_calls=100, max_tokens=1_000_000)

        controller.record_api_call(tokens_in=200, tokens_out=300)
        controller.record_api_call(tokens_in=150, tokens_out=250)

        summary = controller.get_usage_summary()

        assert summary["api_calls"] == 2
        assert summary["tokens_used"] == 900
        assert summary["api_calls_remaining"] == 98
        assert summary["tokens_remaining"] == 999_100

    def test_usage_summary_status_warning(self):
        """Summary status should be 'warning' when soft limits approached."""
        controller = BackPressureController(
            max_api_calls=100,
            warn_api_calls=50,
        )

        for i in range(51):
            controller.record_api_call(tokens_in=10, tokens_out=10)

        summary = controller.get_usage_summary()

        assert summary["status"] == "warning"

    def test_usage_summary_retries_included(self):
        """Summary should include retry counts per phase."""
        controller = BackPressureController(max_retries_per_phase=10)

        controller.record_retry("phase_1")
        controller.record_retry("phase_1")
        controller.record_retry("phase_2")

        summary = controller.get_usage_summary()

        assert summary["retries_by_phase"]["phase_1"] == 2
        assert summary["retries_by_phase"]["phase_2"] == 1


class TestLLMClientIntegration:
    """Test BackPressureController integration with LLMClient."""

    def test_llm_client_accepts_backpressure(self):
        """LLMClient should accept optional backpressure parameter."""
        controller = BackPressureController()
        client = LLMClient(backpressure=controller)

        assert client.backpressure is controller

    def test_llm_client_works_without_backpressure(self):
        """LLMClient should work without backpressure (optional)."""
        client = LLMClient()

        assert client.backpressure is None

    def test_llm_client_checks_backpressure_before_call(self):
        """LLMClient should check backpressure limits before making calls."""
        controller = BackPressureController(max_api_calls=1)

        # Manually set api_calls to hit the limit (simulating prior calls)
        controller.api_calls = 1

        # Create client with this controller
        os.environ["LLM_MOCK"] = "true"
        client = LLMClient(backpressure=controller)

        # Next call should fail backpressure check
        with pytest.raises(RuntimeError) as exc_info:
            client.chat(
                system_prompt="test",
                user_message="test",
            )

        assert "Backpressure limits exceeded" in str(exc_info.value)

        # Cleanup
        del os.environ["LLM_MOCK"]

    def test_llm_client_mock_calls_dont_track(self):
        """Mock calls should not record usage (since they don't use real tokens)."""
        controller = BackPressureController()

        os.environ["LLM_MOCK"] = "true"
        client = LLMClient(backpressure=controller)

        # Make a mock call
        result = client.chat(
            system_prompt="classify acceptance criteria",
            user_message="test",
        )

        # Token count should still be 0 (mock doesn't record)
        assert controller.tokens_used == 0
        assert controller.api_calls == 0

        # Cleanup
        del os.environ["LLM_MOCK"]

    def test_backpressure_raises_sensible_error(self):
        """Error message should be clear when backpressure blocks a call."""
        controller = BackPressureController(max_api_calls=1)

        for _ in range(1):
            controller.api_calls += 1

        os.environ["LLM_MOCK"] = "true"
        client = LLMClient(backpressure=controller)

        with pytest.raises(RuntimeError) as exc_info:
            client.chat(system_prompt="test", user_message="test")

        error_msg = str(exc_info.value)
        assert "Backpressure" in error_msg
        assert "exceeded" in error_msg

        del os.environ["LLM_MOCK"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_usage_remaining(self):
        """Should handle remaining = 0 correctly."""
        controller = BackPressureController(max_api_calls=1)

        controller.record_api_call(tokens_in=10, tokens_out=10)

        summary = controller.get_usage_summary()

        assert summary["api_calls_remaining"] == 0

    def test_large_token_counts(self):
        """Should handle large token counts."""
        controller = BackPressureController(max_tokens=10_000_000)

        controller.record_api_call(tokens_in=5_000_000, tokens_out=4_000_000)

        assert controller.tokens_used == 9_000_000

    def test_many_retries_different_phases(self):
        """Should track many retries across different phases."""
        controller = BackPressureController(max_retries_per_phase=100)

        for phase_num in range(5):
            phase = f"phase_{phase_num}"
            for _ in range(10):
                controller.record_retry(phase)

        assert len(controller.retries_by_phase) == 5
        for phase_num in range(5):
            phase = f"phase_{phase_num}"
            assert controller.retries_by_phase[phase] == 10

    def test_zero_api_calls_limit(self):
        """Should handle edge case of zero max API calls."""
        controller = BackPressureController(max_api_calls=0)

        with pytest.raises(BackPressureLimitExceeded):
            controller.record_api_call(tokens_in=1, tokens_out=1)

    def test_multiple_simultaneous_limits_exceeded(self):
        """Error should be raised on first exceeded limit."""
        controller = BackPressureController(
            max_api_calls=1,
            max_tokens=100,
        )

        controller.api_calls = 1

        with pytest.raises(BackPressureLimitExceeded):
            controller.record_api_call(tokens_in=60, tokens_out=60)
