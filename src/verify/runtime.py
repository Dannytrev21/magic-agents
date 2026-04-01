"""Runtime session helpers for the negotiation web UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from verify.context import VerificationContext
from verify.negotiation.checkpoint import load_checkpoint
from verify.negotiation.harness import NegotiationHarness


@dataclass
class SessionState:
    """In-memory runtime state for a single web session."""

    session_id: str
    context: VerificationContext
    llm: Any
    harness: NegotiationHarness
    phase_idx: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)

    def record_history(
        self,
        title: str,
        detail: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {"title": title, "detail": detail}
        if data:
            entry["data"] = data
        self.history.append(entry)
        return entry


class SessionStore:
    """Creates, stores, and restores runtime session state."""

    def __init__(self) -> None:
        self.sessions: dict[str, SessionState] = {}
        self.active_session_id: str | None = None

    def create(
        self,
        context: VerificationContext,
        llm: Any | None = None,
        phase_idx: int = 0,
        session_id: str | None = None,
    ) -> SessionState:
        resolved_session_id = session_id or context.session_id or uuid4().hex
        context.session_id = resolved_session_id

        state = SessionState(
            session_id=resolved_session_id,
            context=context,
            llm=llm,
            harness=NegotiationHarness(context),
            phase_idx=phase_idx,
        )
        state.record_history("session_created", context.jira_key)
        self.sessions[resolved_session_id] = state
        self.active_session_id = resolved_session_id
        return state

    def get(self, session_id: str | None) -> SessionState | None:
        if not session_id:
            return None
        return self.sessions.get(session_id)

    def resolve(self, session_id: str | None) -> SessionState | None:
        if session_id:
            return self.sessions.get(session_id)
        if self.active_session_id:
            active_session = self.sessions.get(self.active_session_id)
            if active_session is not None:
                return active_session
        if len(self.sessions) == 1:
            return next(iter(self.sessions.values()))
        return None

    def clear(self) -> None:
        self.sessions.clear()
        self.active_session_id = None

    def restore(self, jira_key: str, llm: Any | None = None) -> SessionState | None:
        loaded = load_checkpoint(jira_key)
        if loaded is None:
            return None

        context, _ = loaded
        session_id = context.session_id or None

        if session_id and session_id in self.sessions:
            self.active_session_id = session_id
            return self.sessions[session_id]

        state = self.create(
            context=context,
            llm=llm,
            phase_idx=_next_phase_index_from_context(context.current_phase),
            session_id=session_id,
        )
        state.record_history(
            "session_restored",
            f"Restored from checkpoint for {jira_key}",
            data={"current_phase": context.current_phase},
        )
        return state


def _next_phase_index_from_context(current_phase: str) -> int:
    if current_phase == "phase_0":
        return 0
    if not current_phase.startswith("phase_"):
        return 0
    try:
        phase_number = int(current_phase.split("_", 1)[1])
    except ValueError:
        return 0
    return max(0, min(phase_number, 7))
