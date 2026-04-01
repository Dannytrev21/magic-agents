"""Back-Pressure Controller for API usage limits and resource enforcement."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


class BackPressureLimitExceeded(Exception):
    """Raised when a hard limit is exceeded."""

    pass


@dataclass
class PhaseCostReport:
    """Cost report for a single negotiation phase."""

    phase_name: str
    api_calls: int
    tokens_in: int
    tokens_out: int
    wall_clock_seconds: float
    retries: int
    status: str  # "success", "failed", "budget_exceeded"

    @staticmethod
    def aggregate(reports: list[PhaseCostReport]) -> dict[str, Any]:
        """Aggregate cost reports across phases into a summary dict."""
        total_in = sum(r.tokens_in for r in reports)
        total_out = sum(r.tokens_out for r in reports)
        return {
            "total_api_calls": sum(r.api_calls for r in reports),
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "total_tokens": total_in + total_out,
            "total_wall_clock_seconds": sum(r.wall_clock_seconds for r in reports),
            "total_retries": sum(r.retries for r in reports),
            "phases": len(reports),
        }


@dataclass
class BackPressureController:
    """Tracks API calls, tokens, wall clock time, and retries with hard/soft limits.

    Hard limits cause exceptions when exceeded:
    - max_api_calls: Maximum number of API calls allowed
    - max_tokens: Maximum tokens allowed
    - max_wall_clock_seconds: Maximum wall clock time allowed (in seconds)
    - max_retries_per_phase: Maximum retries allowed per phase

    Soft limits generate warnings but don't prevent execution:
    - warn_api_calls: Warning threshold for API calls
    - warn_tokens: Warning threshold for tokens
    """

    # Hard limits
    max_api_calls: int = 50
    max_tokens: int = 500_000
    max_wall_clock_seconds: int = 600  # 10 minutes
    max_retries_per_phase: int = 3

    # Soft limits
    warn_api_calls: int = 40
    warn_tokens: int = 400_000

    # Current state
    api_calls: int = field(default=0)
    tokens_used: int = field(default=0)
    start_time: float = field(default_factory=time.time)
    retries_by_phase: dict[str, int] = field(default_factory=dict)

    # Known budget fields that can be overridden via constitution
    _BUDGET_FIELDS = {
        "max_api_calls",
        "max_tokens",
        "max_wall_clock_seconds",
        "max_retries_per_phase",
        "warn_api_calls",
        "warn_tokens",
    }

    _WARN_TO_MAX = {
        "warn_api_calls": "max_api_calls",
        "warn_tokens": "max_tokens",
    }

    @classmethod
    def from_constitution(cls, constitution: dict) -> BackPressureController:
        """Create a controller from a constitution dict's optional budget section."""
        budget = constitution.get("budget") or {}
        kwargs: dict[str, Any] = {}
        for key, value in budget.items():
            if key not in cls._BUDGET_FIELDS:
                continue
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"budget.{key} must be a positive integer, got {value!r}"
                )
            kwargs[key] = value

        controller = cls(**kwargs)

        # Validate warn <= max constraints
        for warn_key, max_key in cls._WARN_TO_MAX.items():
            warn_val = getattr(controller, warn_key)
            max_val = getattr(controller, max_key)
            if warn_val > max_val:
                raise ValueError(
                    f"budget.{warn_key} ({warn_val}) must not exceed "
                    f"budget.{max_key} ({max_val}): warn must be <= max"
                )

        return controller

    def record_api_call(self, tokens_in: int, tokens_out: int) -> None:
        """Record an API call with input and output tokens.

        Args:
            tokens_in: Number of input tokens used.
            tokens_out: Number of output tokens used.

        Raises:
            BackPressureLimitExceeded: If hard limits are exceeded.
        """
        self.api_calls += 1
        self.tokens_used += tokens_in + tokens_out

        # Check hard limits immediately after recording
        self._check_hard_limits()

    def check_limits(self) -> tuple[bool, list[str]]:
        """Check all limits and return status with warnings/errors.

        Returns:
            A tuple of (ok: bool, messages: list[str]).
            - ok=True and messages=[] means all clear
            - ok=True and messages=[warnings] means warnings (soft limits)
            - ok=False and messages=[errors] means hard limits exceeded
        """
        messages = []

        # Check hard limits (>= means we've hit or exceeded the limit)
        if self.api_calls >= self.max_api_calls:
            messages.append(
                f"Hard limit exceeded: {self.api_calls} API calls >= {self.max_api_calls}"
            )
        if self.tokens_used >= self.max_tokens:
            messages.append(
                f"Hard limit exceeded: {self.tokens_used} tokens >= {self.max_tokens}"
            )

        elapsed = time.time() - self.start_time
        if elapsed >= self.max_wall_clock_seconds:
            messages.append(
                f"Hard limit exceeded: {elapsed:.1f}s wall clock >= {self.max_wall_clock_seconds}s"
            )

        if messages:
            return (False, messages)

        # Check soft limits
        if self.api_calls > self.warn_api_calls:
            messages.append(
                f"Warning: {self.api_calls} API calls approaching limit ({self.warn_api_calls})"
            )
        if self.tokens_used > self.warn_tokens:
            messages.append(
                f"Warning: {self.tokens_used} tokens approaching limit ({self.warn_tokens})"
            )

        return (True, messages)

    def can_proceed(self) -> bool:
        """Quick check if we can make another API call.

        Returns:
            True if we haven't hit hard limits, False otherwise.
        """
        ok, _ = self.check_limits()
        return ok

    def record_retry(self, phase: str) -> None:
        """Record a retry for a specific phase.

        Args:
            phase: The phase name (e.g., 'phase_1', 'phase_2').

        Raises:
            BackPressureLimitExceeded: If max retries for this phase exceeded.
        """
        self.retries_by_phase[phase] = self.retries_by_phase.get(phase, 0) + 1

        if self.retries_by_phase[phase] > self.max_retries_per_phase:
            raise BackPressureLimitExceeded(
                f"Max retries ({self.max_retries_per_phase}) exceeded for {phase}"
            )

    def get_usage_summary(self) -> dict:
        """Return current usage statistics.

        Returns:
            A dict with keys:
            - api_calls: Current number of API calls
            - tokens_used: Current token count
            - wall_clock_seconds: Elapsed time in seconds
            - wall_clock_minutes: Elapsed time in minutes
            - retries_by_phase: Dict mapping phase names to retry counts
            - api_calls_remaining: Hard limit - current
            - tokens_remaining: Hard limit - current
            - wall_clock_remaining_seconds: Hard limit - elapsed
            - status: "ok", "warning", or "exceeded"
        """
        elapsed = time.time() - self.start_time

        ok, messages = self.check_limits()
        if not ok:
            status = "exceeded"
        elif messages:
            status = "warning"
        else:
            status = "ok"

        return {
            "api_calls": self.api_calls,
            "tokens_used": self.tokens_used,
            "wall_clock_seconds": elapsed,
            "wall_clock_minutes": elapsed / 60.0,
            "retries_by_phase": dict(self.retries_by_phase),
            "api_calls_remaining": self.max_api_calls - self.api_calls,
            "tokens_remaining": self.max_tokens - self.tokens_used,
            "wall_clock_remaining_seconds": self.max_wall_clock_seconds - elapsed,
            "status": status,
        }

    def _check_hard_limits(self) -> None:
        """Internal: Check hard limits and raise if exceeded."""
        if self.api_calls > self.max_api_calls:
            raise BackPressureLimitExceeded(
                f"Hard limit exceeded: {self.api_calls} API calls > {self.max_api_calls}"
            )
        if self.tokens_used > self.max_tokens:
            raise BackPressureLimitExceeded(
                f"Hard limit exceeded: {self.tokens_used} tokens > {self.max_tokens}"
            )

        elapsed = time.time() - self.start_time
        if elapsed > self.max_wall_clock_seconds:
            raise BackPressureLimitExceeded(
                f"Hard limit exceeded: {elapsed:.1f}s wall clock > {self.max_wall_clock_seconds}s"
            )
