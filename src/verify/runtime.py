"""Runtime session helpers for the negotiation web UI.

This module keeps web-session concerns out of the negotiation and pipeline
modules themselves:
- session IDs and lookup
- transcript/history capture with compaction
- normalized runtime/SSE event payloads
- checkpoint-backed session restore
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.checkpoint import load_checkpoint
from verify.negotiation.harness import NegotiationHarness
from verify.transcript import TranscriptCompactor

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RuntimeEvent:
    """Normalized event payload used by runtime history and SSE streaming."""

    type: str
    session_id: str
    step: str = ""
    status: str = ""
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type,
            "session_id": self.session_id,
        }
        if self.step:
            payload["step"] = self.step
        if self.status:
            payload["status"] = self.status
        if self.message:
            payload["message"] = self.message
        payload.update(self.data)
        return payload

    def as_sse(self) -> str:
        return f"data: {json.dumps(self.payload())}\n\n"


@dataclass
class SessionState:
    """In-memory runtime state for a single web session."""

    session_id: str
    context: VerificationContext
    llm: LLMClient
    harness: NegotiationHarness
    phase_idx: int = 0
    transcript: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    latest_questions: list[dict[str, str]] = field(default_factory=list)
    latest_pipeline: dict[str, Any] = field(default_factory=dict)
    compaction_threshold: int = 30
    keep_recent: int = 15
    history_compaction_threshold: int = 60
    keep_recent_history: int = 20

    def __post_init__(self) -> None:
        self.compactor: TranscriptCompactor | Any = TranscriptCompactor(
            compaction_threshold=self.compaction_threshold,
            keep_recent=self.keep_recent,
        )

    def record_transcript(
        self,
        role: str,
        phase: str,
        content: str,
        kind: str = "message",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": _now_iso(),
            "role": role,
            "phase": phase,
            "kind": kind,
            "content": content,
        }
        if data:
            entry["data"] = data
        self.transcript.append(entry)

        try:
            self.transcript = self.compactor.compact(self.transcript)
        except Exception:
            logger.warning("Transcript compaction failed; retaining raw transcript.")

        return entry

    def record_history(
        self,
        title: str,
        detail: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": _now_iso(),
            "title": title,
            "detail": detail,
        }
        if data:
            entry["data"] = data
        self.history.append(entry)
        try:
            self.history = self.compactor.compact_history(
                self.history,
                threshold=self.history_compaction_threshold,
                keep_recent=self.keep_recent_history,
            )
        except Exception:
            logger.warning("History compaction failed; retaining raw history.")
        return entry

    def set_questions(self, phase: str, questions: list[str]) -> list[dict[str, str]]:
        structured = [
            {"id": f"{phase}-question-{idx}", "text": question}
            for idx, question in enumerate(questions, start=1)
        ]
        self.latest_questions = structured
        if structured:
            joined = "\n".join(question["text"] for question in structured)
            self.record_transcript(
                role="ai",
                phase=phase,
                content=joined,
                kind="questions",
                data={"questions": structured},
            )
        return structured

    def run_phase(
        self,
        title: str,
        phase_name: str,
        skill_fn: Callable[..., Any],
        feedback: str | None = None,
    ) -> tuple[Any, list[dict[str, str]]]:
        """Execute a negotiation phase while capturing structured questions."""

        captured_questions: list[str] = []
        original_chat = self.llm.chat
        original_chat_multi = self.llm.chat_multi

        def _capture(result: Any) -> Any:
            if isinstance(result, dict):
                raw_questions = result.get("questions", [])
                captured_questions[:] = [
                    question for question in raw_questions if isinstance(question, str)
                ]
            return result

        def _wrapped_chat(*args: Any, **kwargs: Any) -> Any:
            return _capture(original_chat(*args, **kwargs))

        def _wrapped_chat_multi(*args: Any, **kwargs: Any) -> Any:
            return _capture(original_chat_multi(*args, **kwargs))

        self.llm.chat = _wrapped_chat
        self.llm.chat_multi = _wrapped_chat_multi
        try:
            if feedback is None:
                results = skill_fn(self.context, self.llm)
            else:
                results = skill_fn(self.context, self.llm, feedback=feedback)
        finally:
            self.llm.chat = original_chat
            self.llm.chat_multi = original_chat_multi

        count = _result_count(results)
        self.harness.add_to_log(phase_name, "ai", f"{title}: produced {count} items")
        self.record_transcript(
            role="ai",
            phase=phase_name,
            content=f"{title}: produced {count} items",
            kind="phase-output",
            data={"title": title, "count": count},
        )
        self.record_history(
            "phase_output",
            f"{phase_name} produced {count} item(s)",
            data={"title": title},
        )

        return results, self.set_questions(phase_name, captured_questions)


class SessionStore:
    """Creates, stores, and restores runtime session state."""

    def __init__(self) -> None:
        self.sessions: dict[str, SessionState] = {}

    def create(
        self,
        context: VerificationContext,
        llm: LLMClient | None = None,
        phase_idx: int = 0,
    ) -> SessionState:
        session_id = uuid4().hex
        state = SessionState(
            session_id=session_id,
            context=context,
            llm=llm or LLMClient(),
            harness=NegotiationHarness(context),
            phase_idx=phase_idx,
        )
        state.record_history("session_created", context.jira_key)
        self.sessions[session_id] = state
        return state

    def get(self, session_id: str | None) -> SessionState | None:
        if not session_id:
            return None
        return self.sessions.get(session_id)

    def resolve(self, session_id: str | None) -> SessionState | None:
        if session_id:
            return self.sessions.get(session_id)
        if len(self.sessions) == 1:
            return next(iter(self.sessions.values()))
        return None

    def delete(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            return False
        del self.sessions[session_id]
        return True

    def clear(self) -> None:
        self.sessions.clear()

    def restore(self, jira_key: str, llm: LLMClient | None = None) -> SessionState | None:
        loaded = load_checkpoint(jira_key)
        if loaded is None:
            return None

        context, _ = loaded
        state = self.create(
            context=context,
            llm=llm,
            phase_idx=_next_phase_index_from_context(context.current_phase),
        )
        state.record_history(
            "session_restored",
            f"Restored from checkpoint for {jira_key}",
            data={"current_phase": context.current_phase},
        )
        return state


def _result_count(results: Any) -> int:
    if isinstance(results, list):
        return len(results)
    if isinstance(results, dict):
        for key in ("classifications", "postconditions", "preconditions", "failure_modes", "invariants", "routing", "ears_statements", "checklist"):
            value = results.get(key)
            if isinstance(value, list):
                return len(value)
        return len(results)
    return 0


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
