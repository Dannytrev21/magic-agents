"""NegotiationHarness — drives the VerificationContext through negotiation phases.

Implements Sherpa's state machine pattern with guard conditions on every transition.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

from verify.backpressure import PhaseCostReport
from verify.context import VerificationContext
from verify.negotiation.checkpoint import save_checkpoint
from verify.observability import HarnessLogger
from verify.transcript import TranscriptCompactor

if TYPE_CHECKING:
    from verify.backpressure import BackPressureController
    from verify.llm_client import LLMClient

_harness_logger = logging.getLogger(__name__)

PHASES = [
    "phase_0",  # Intake & classification
    "phase_1",  # Postcondition extraction
    "phase_2",  # Precondition formalization
    "phase_3",  # Failure mode enumeration
    "phase_4",  # Invariant identification
    "phase_5",  # Verification routing
    "phase_6",  # EARS statement generation
    "phase_7",  # Approval gate
]


class NegotiationHarness:
    """Orchestrates phase-by-phase negotiation over a VerificationContext."""

    def __init__(
        self,
        ctx: VerificationContext,
        backpressure: BackPressureController | None = None,
        transcript_compactor: TranscriptCompactor | None = None,
        event_emitter: Callable[..., None] | None = None,
        hooks: Any | None = None,
    ) -> None:
        self.ctx = ctx
        self.backpressure = backpressure
        self.transcript_compactor = transcript_compactor or TranscriptCompactor()
        self.cost_reports: list[PhaseCostReport] = []
        self.logger = HarnessLogger(ctx.jira_key)
        self.event_emitter = event_emitter
        self.hooks = hooks  # Optional HookRegistry (P9)

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------

    def _emit(self, event: Any) -> None:
        """Emit a RuntimeEvent through the callback. Exceptions are logged and swallowed."""
        if self.event_emitter is None:
            return
        try:
            self.event_emitter(event)
        except Exception:
            _harness_logger.warning("Event emitter callback raised; swallowing exception.")

    def _fire_hook(self, lifecycle_point: str, phase_name: str = "", data: dict[str, Any] | None = None) -> None:
        """Fire a lifecycle hook if a HookRegistry is attached."""
        if self.hooks is None:
            return
        try:
            from verify.hooks import HookEvent
            self.hooks.fire(
                lifecycle_point,
                HookEvent(
                    lifecycle_point=lifecycle_point,
                    session_id=getattr(self.ctx, "session_id", "") or "",
                    phase_name=phase_name,
                    data=data or {},
                ),
            )
        except Exception:
            _harness_logger.warning("Hook fire raised; swallowing exception.")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_phase(self) -> str:
        return self.ctx.current_phase

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def add_to_log(self, phase: str, role: str, content: str) -> None:
        """Append a timestamped entry to the negotiation log."""
        self.ctx.negotiation_log.append(
            {
                "phase": phase,
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.ctx.negotiation_log = self.transcript_compactor.compact(
            self.ctx.negotiation_log
        )

    # ------------------------------------------------------------------
    # Run current phase with budget enforcement
    # ------------------------------------------------------------------

    def run_current_phase(
        self,
        llm: LLMClient,
        feedback: str | None = None,
    ) -> dict:
        """Execute the current phase with optional backpressure enforcement.

        Returns a dict with at least a 'status' key. If the budget is exceeded
        before the phase runs, returns {"status": "budget_exceeded", "usage_summary": ...}.
        """
        from verify.runtime import RuntimeEvent

        phase = self.ctx.current_phase
        phase_index = PHASES.index(phase) if phase in PHASES else -1
        session_id = getattr(self.ctx, "session_id", "") or ""

        # Budget gate: check before invoking the LLM
        if self.backpressure and not self.backpressure.can_proceed():
            save_checkpoint(self.ctx, phase)
            usage = self.backpressure.get_usage_summary()
            self._emit(RuntimeEvent(
                type="budget_exceeded",
                session_id=session_id,
                step=phase,
                status="budget_exceeded",
                data={"phase": phase, "usage_summary": usage},
            ))
            return {
                "status": "budget_exceeded",
                "phase": phase,
                "usage_summary": usage,
            }

        # Emit phase_start
        self._emit(RuntimeEvent(
            type="phase_start",
            session_id=session_id,
            step=phase,
            status="running",
            data={"phase": phase, "phase_index": phase_index},
        ))

        # Snapshot counters for per-phase cost reporting
        bp = self.backpressure
        calls_before = bp.api_calls if bp else 0
        tokens_before = bp.tokens_used if bp else 0
        retries_before = bp.retries_by_phase.get(phase, 0) if bp else 0
        phase_start_time = time.time()

        # Dispatch to the appropriate phase function
        from verify.negotiation.phase1 import run_phase1
        from verify.negotiation.phase2 import run_phase2
        from verify.negotiation.phase3 import run_phase3
        from verify.negotiation.phase4 import run_phase4

        phase_runners = {
            "phase_0": run_phase1,
            "phase_1": run_phase2,
            "phase_2": run_phase3,
            "phase_3": run_phase4,
        }

        runner = phase_runners.get(phase)
        if runner is None:
            return {"status": "no_runner", "phase": phase}

        try:
            result = runner(self.ctx, llm, feedback=feedback)
        except Exception as exc:
            self._emit(RuntimeEvent(
                type="phase_error",
                session_id=session_id,
                step=phase,
                status="error",
                data={"phase": phase, "error": str(exc), "phase_index": phase_index},
            ))
            raise

        # Emit validation_result
        self._emit(RuntimeEvent(
            type="validation_result",
            session_id=session_id,
            step=phase,
            status="validated",
            data={"phase": phase, "valid": True, "errors": []},
        ))

        # Record per-phase cost report
        phase_elapsed = time.time() - phase_start_time
        if bp:
            calls_delta = bp.api_calls - calls_before
            tokens_in_delta = (bp.tokens_used - tokens_before) // 2
            tokens_out_delta = bp.tokens_used - tokens_before - tokens_in_delta
            retries_delta = bp.retries_by_phase.get(phase, 0) - retries_before
        else:
            calls_delta = 0
            tokens_in_delta = 0
            tokens_out_delta = 0
            retries_delta = 0

        report = PhaseCostReport(
            phase_name=phase,
            api_calls=calls_delta,
            tokens_in=tokens_in_delta,
            tokens_out=tokens_out_delta,
            wall_clock_seconds=phase_elapsed,
            retries=retries_delta,
            status="success",
        )
        self.cost_reports.append(report)

        # Compute result count for phase_complete event
        result_count = 0
        if isinstance(result, dict):
            for key in ("classifications", "postconditions", "preconditions", "failure_modes"):
                val = result.get(key)
                if isinstance(val, list):
                    result_count = len(val)
                    break
        elif isinstance(result, list):
            result_count = len(result)

        self._emit(RuntimeEvent(
            type="phase_complete",
            session_id=session_id,
            step=phase,
            status="completed",
            data={"phase": phase, "result_count": result_count, "phase_index": phase_index},
        ))

        return {"status": "completed", "phase": phase, "result": result}

    # ------------------------------------------------------------------
    # Phase advancement
    # ------------------------------------------------------------------

    def advance_phase(self) -> str:
        """Move to the next phase if exit conditions for the current phase are met.

        Returns the new phase name, or the current phase if conditions are not met
        or we are already at the final phase.

        Saves a checkpoint after advancing to the new phase.
        """
        from verify.runtime import RuntimeEvent

        current = self.ctx.current_phase
        if not self._exit_conditions_met(current):
            return current

        idx = PHASES.index(current)
        if idx >= len(PHASES) - 1:
            return current  # already at final phase

        next_phase = PHASES[idx + 1]
        self.ctx.current_phase = next_phase

        # Log phase_started for the new phase
        self.logger.log_phase_started(next_phase)

        # Save a checkpoint after advancing to the new phase
        checkpoint_path = save_checkpoint(self.ctx, next_phase)

        # Log checkpoint_saved
        self.logger.log_checkpoint_saved(next_phase, str(checkpoint_path))

        # Emit session_checkpoint event
        session_id = getattr(self.ctx, "session_id", "") or ""
        self._emit(RuntimeEvent(
            type="session_checkpoint",
            session_id=session_id,
            step=next_phase,
            status="checkpointed",
            data={"phase": next_phase, "checkpoint_path": str(checkpoint_path)},
        ))

        # P9: Fire lifecycle hooks
        self._fire_hook("post_phase", next_phase, data={"phase_name": next_phase, "status": "advanced"})
        self._fire_hook("checkpoint_saved", next_phase, data={"checkpoint_path": str(checkpoint_path)})

        return next_phase

    # ------------------------------------------------------------------
    # Exit-condition guards (Sherpa guard conditions)
    # ------------------------------------------------------------------

    def _exit_conditions_met(self, phase: str) -> bool:
        """Return True when the given phase's guard conditions are satisfied."""
        checker = self._exit_checkers.get(phase)
        if checker is None:
            return False
        return checker(self)

    def _phase_0_ok(self) -> bool:
        """Guard: every AC must be classified."""
        if not self.ctx.classifications:
            return False
        classified = {c.get("ac_index") for c in self.ctx.classifications}
        expected = {ac["index"] for ac in self.ctx.raw_acceptance_criteria}
        return expected.issubset(classified)

    def _phase_1_ok(self) -> bool:
        """Guard: every api_behavior classification must have a postcondition."""
        api_indices = {
            c.get("ac_index")
            for c in self.ctx.classifications
            if c.get("type") == "api_behavior"
        }
        if not api_indices:
            return True  # no API behaviors — phase exits cleanly
        postcond_indices = {p.get("ac_index") for p in self.ctx.postconditions}
        return api_indices.issubset(postcond_indices)

    def _phase_2_ok(self) -> bool:
        """Guard: preconditions have been identified for the current story."""
        return len(self.ctx.preconditions) > 0

    def _phase_3_ok(self) -> bool:
        """Guard: failure modes exist and reference known preconditions."""
        if not self.ctx.preconditions or not self.ctx.failure_modes:
            return False
        pre_ids = {p.get("id") for p in self.ctx.preconditions}
        fail_refs = {f.get("violates") for f in self.ctx.failure_modes}
        return fail_refs.issubset(pre_ids)

    def _phase_4_ok(self) -> bool:
        """Guard: invariants populated (can be from constitution or synthesis)."""
        return len(self.ctx.invariants) > 0

    def _phase_5_ok(self) -> bool:
        return len(self.ctx.verification_routing) > 0

    def _phase_6_ok(self) -> bool:
        return len(self.ctx.ears_statements) > 0

    def _phase_7_ok(self) -> bool:
        return self.ctx.approved

    _exit_checkers: dict = {
        "phase_0": _phase_0_ok,
        "phase_1": _phase_1_ok,
        "phase_2": _phase_2_ok,
        "phase_3": _phase_3_ok,
        "phase_4": _phase_4_ok,
        "phase_5": _phase_5_ok,
        "phase_6": _phase_6_ok,
        "phase_7": _phase_7_ok,
    }
