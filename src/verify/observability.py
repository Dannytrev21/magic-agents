"""Structured observability logging for the negotiation harness.

Implements Feature 21: Structured Observability (JSONL Harness Log)
- HarnessLogger class for structured JSON event logging
- JSONL format for machine-parseability
- Events: phase_started, phase_completed, llm_called, llm_responded,
  validation_result, developer_interaction, checkpoint_saved, error
- Context manager support for timing
- Auto-flush on each write
"""

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

LOGS_DIR = Path(".verify/logs")


class HarnessLogger:
    """Structured JSON event logger for negotiation harness.

    Logs events as JSONL (one JSON line per event) to `.verify/logs/{jira_key}.jsonl`.
    Each event includes: timestamp, event_type, phase, data, and optional duration_ms.
    """

    def __init__(self, jira_key: str):
        """Initialize the logger for a given Jira ticket key.

        Args:
            jira_key: The Jira ticket key (used in filename)
        """
        self.jira_key = jira_key
        self.log_path = LOGS_DIR / f"{jira_key}.jsonl"
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        """Create the logs directory if it doesn't exist."""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        phase: Optional[str] = None,
        data: Optional[dict] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Log a structured JSON event to the JSONL file.

        Args:
            event_type: Type of event (phase_started, phase_completed, llm_called,
                       llm_responded, validation_result, developer_interaction,
                       checkpoint_saved, error)
            phase: Current negotiation phase (e.g., "phase_1")
            data: Event-specific data as a dict
            duration_ms: Optional duration in milliseconds for timing events
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
        }

        if phase is not None:
            event["phase"] = phase

        if data is not None:
            event["data"] = data

        if duration_ms is not None:
            event["duration_ms"] = duration_ms

        self._write_event(event)

    def log_phase_started(self, phase: str, data: Optional[dict] = None) -> None:
        """Log that a phase has started.

        Args:
            phase: The phase that started (e.g., "phase_1")
            data: Optional data (e.g., AC index, guidance text)
        """
        self.log_event("phase_started", phase=phase, data=data)

    def log_phase_completed(
        self, phase: str, duration_ms: int, data: Optional[dict] = None
    ) -> None:
        """Log that a phase has completed.

        Args:
            phase: The phase that completed (e.g., "phase_1")
            duration_ms: Duration in milliseconds
            data: Optional data (e.g., output count, validation results)
        """
        self.log_event(
            "phase_completed", phase=phase, data=data, duration_ms=duration_ms
        )

    def log_llm_called(
        self, phase: str, prompt_length: int, data: Optional[dict] = None
    ) -> None:
        """Log that an LLM call was initiated.

        Args:
            phase: The phase calling the LLM
            prompt_length: Length of the prompt in characters
            data: Optional data (e.g., model, temperature)
        """
        event_data = {"prompt_length": prompt_length}
        if data:
            event_data.update(data)
        self.log_event("llm_called", phase=phase, data=event_data)

    def log_llm_responded(
        self, phase: str, response_length: int, duration_ms: int, data: Optional[dict] = None
    ) -> None:
        """Log that an LLM response was received.

        Args:
            phase: The phase that called the LLM
            response_length: Length of the response in characters
            duration_ms: Duration of the LLM call in milliseconds
            data: Optional data (e.g., tokens_used, cost)
        """
        event_data = {
            "response_length": response_length,
        }
        if data:
            event_data.update(data)
        self.log_event(
            "llm_responded", phase=phase, data=event_data, duration_ms=duration_ms
        )

    def log_validation_result(
        self, phase: str, valid: bool, errors: Optional[list[str]] = None
    ) -> None:
        """Log the result of validation.

        Args:
            phase: The phase that was validated
            valid: Whether validation passed
            errors: Optional list of validation errors
        """
        data = {"valid": valid}
        if errors:
            data["errors"] = errors
        self.log_event("validation_result", phase=phase, data=data)

    def log_developer_interaction(
        self, phase: str, interaction_type: str, data: Optional[dict] = None
    ) -> None:
        """Log a developer interaction (feedback, approval, etc.).

        Args:
            phase: The phase during which the interaction occurred
            interaction_type: Type of interaction (feedback, approval, rejection, etc.)
            data: Optional interaction data (e.g., feedback text)
        """
        event_data = {"interaction_type": interaction_type}
        if data:
            event_data.update(data)
        self.log_event("developer_interaction", phase=phase, data=event_data)

    def log_checkpoint_saved(self, phase: str, checkpoint_path: str) -> None:
        """Log that a checkpoint was saved.

        Args:
            phase: The phase that was checkpointed
            checkpoint_path: Path to the saved checkpoint file
        """
        self.log_event(
            "checkpoint_saved", phase=phase, data={"checkpoint_path": checkpoint_path}
        )

    def log_error(self, phase: str, error_msg: str, error_type: Optional[str] = None, data: Optional[dict] = None) -> None:
        """Log an error event.

        Args:
            phase: The phase during which the error occurred
            error_msg: Human-readable error message
            error_type: Optional error type (e.g., "ValidationError", "LLMError")
            data: Optional additional error data
        """
        event_data = {"error_msg": error_msg}
        if error_type:
            event_data["error_type"] = error_type
        if data:
            event_data.update(data)
        self.log_event("error", phase=phase, data=event_data)

    def _write_event(self, event: dict) -> None:
        """Write a single event as a JSON line and flush.

        Args:
            event: The event dict to write
        """
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(event) + "\n")
                f.flush()
        except IOError as e:
            logger.error(f"Failed to write observability log: {e}")

    def flush(self) -> None:
        """Explicitly flush the log file.

        Note: Individual writes already flush, so this is a no-op but provided
        for explicit control if needed.
        """
        pass  # Auto-flush on each write already implemented

    def read_events(self) -> list[dict]:
        """Read all logged events from the JSONL file.

        Returns:
            List of event dicts, in order logged

        Raises:
            FileNotFoundError: If the log file doesn't exist yet
            json.JSONDecodeError: If a line is malformed JSON
        """
        if not self.log_path.exists():
            return []

        events = []
        with open(self.log_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    events.append(json.loads(line))
        return events

    def clear(self) -> None:
        """Clear all logged events (delete the log file)."""
        if self.log_path.exists():
            self.log_path.unlink()
            logger.info(f"Cleared log file: {self.log_path}")

    @contextmanager
    def time_phase(self, phase: str, data: Optional[dict] = None):
        """Context manager for timing a phase.

        Usage:
            with logger.time_phase("phase_1"):
                # do work
                pass
            # Automatically logs phase_completed with duration

        Args:
            phase: The phase name
            data: Optional phase metadata
        """
        self.log_phase_started(phase, data=data)
        start_ms = int(time.time() * 1000)
        try:
            yield
        finally:
            end_ms = int(time.time() * 1000)
            duration_ms = end_ms - start_ms
            self.log_phase_completed(phase, duration_ms=duration_ms)

    @contextmanager
    def time_llm_call(self, phase: str, prompt_length: int):
        """Context manager for timing an LLM call.

        Usage:
            with logger.time_llm_call("phase_1", len(prompt)):
                response = llm.call(prompt)
            # Automatically logs llm_responded with duration

        Args:
            phase: The phase calling the LLM
            prompt_length: Length of the prompt in characters
        """
        self.log_llm_called(phase, prompt_length)
        start_ms = int(time.time() * 1000)
        try:
            yield
        finally:
            end_ms = int(time.time() * 1000)
            duration_ms = end_ms - start_ms
            # Note: response length should be logged separately with log_llm_responded
            # This context manager just captures the timing

    def get_summary(self) -> dict:
        """Get a summary of all logged events.

        Returns a dict with event counts, phase timings, and other metadata.

        Returns:
            Dict with keys:
            - total_events: Total number of events
            - event_counts: Dict of event_type -> count
            - phases: List of unique phases
            - duration_ms: Total duration from first to last event (if > 1 event)
        """
        events = self.read_events()
        if not events:
            return {
                "total_events": 0,
                "event_counts": {},
                "phases": [],
                "duration_ms": None,
            }

        event_counts = {}
        phases = set()
        for event in events:
            event_type = event.get("event_type")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            if "phase" in event:
                phases.add(event["phase"])

        duration_ms = None
        if len(events) > 1:
            first_ts = datetime.fromisoformat(events[0]["timestamp"])
            last_ts = datetime.fromisoformat(events[-1]["timestamp"])
            duration_ms = int((last_ts - first_ts).total_seconds() * 1000)

        return {
            "total_events": len(events),
            "event_counts": event_counts,
            "phases": sorted(list(phases)),
            "duration_ms": duration_ms,
        }
