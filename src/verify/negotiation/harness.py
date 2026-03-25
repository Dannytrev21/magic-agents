"""NegotiationHarness — drives the VerificationContext through negotiation phases.

Implements Sherpa's state machine pattern with guard conditions on every transition.
"""

from datetime import datetime, timezone

from verify.context import VerificationContext
from verify.negotiation.checkpoint import save_checkpoint
from verify.observability import HarnessLogger

PHASES = [
    "phase_0",  # Intake & classification
    "phase_1",  # Postcondition extraction
    "phase_2",  # Precondition & failure-mode analysis
    "phase_3",  # Invariant identification
    "phase_4",  # Verification routing
    "phase_5",  # EARS statement generation
    "phase_6",  # Traceability mapping
    "phase_7",  # Approval gate
]


class NegotiationHarness:
    """Orchestrates phase-by-phase negotiation over a VerificationContext."""

    def __init__(self, ctx: VerificationContext) -> None:
        self.ctx = ctx
        self.logger = HarnessLogger(ctx.jira_key)

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

    # ------------------------------------------------------------------
    # Phase advancement
    # ------------------------------------------------------------------

    def advance_phase(self) -> str:
        """Move to the next phase if exit conditions for the current phase are met.

        Returns the new phase name, or the current phase if conditions are not met
        or we are already at the final phase.

        Saves a checkpoint after advancing to the new phase.
        """
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
        """Guard: preconditions exist and every failure mode references a valid precondition."""
        if not self.ctx.preconditions or not self.ctx.failure_modes:
            return False
        pre_ids = {p.get("id") for p in self.ctx.preconditions}
        fail_refs = {f.get("violates") for f in self.ctx.failure_modes}
        return fail_refs.issubset(pre_ids)

    def _phase_3_ok(self) -> bool:
        """Guard: invariants populated (can be from constitution or synthesis)."""
        return len(self.ctx.invariants) > 0

    def _phase_4_ok(self) -> bool:
        return len(self.ctx.verification_routing) > 0

    def _phase_5_ok(self) -> bool:
        return len(self.ctx.ears_statements) > 0

    def _phase_6_ok(self) -> bool:
        return len(self.ctx.traceability_map) > 0

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
