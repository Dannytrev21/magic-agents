"""Checkpoint and resume support for negotiation sessions.

Implements Feature 2.8: Checkpoint & Resume
- Serializes VerificationContext to JSON after each phase advance
- Loads checkpoints to resume negotiations
- Manages session files in .verify/sessions/{jira_key}/
"""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Union

from verify.backpressure import BackPressureController
from verify.context import VerificationContext

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(".verify/sessions")
PHASE_TITLES = {
    1: "Interface & Actor Discovery",
    2: "Happy Path Contract",
    3: "Precondition Formalization",
    4: "Failure Mode Enumeration",
    5: "Invariant Extraction",
    6: "Routing & Completeness Sweep",
    7: "EARS Formalization",
}


def save_checkpoint(
    context: VerificationContext,
    phase: str,
    backpressure: Optional[BackPressureController] = None,
) -> Path:
    """Save a checkpoint of the VerificationContext to disk.

    Args:
        context: The VerificationContext to save
        phase: The phase that was just completed (e.g., "phase_1")
        backpressure: Optional controller whose state is persisted in the
                      checkpoint's ``usage`` field.  When provided, the
                      controller's serialized state takes precedence over
                      ``context.usage``.

    Returns:
        Path to the saved checkpoint file

    Raises:
        OSError: If the checkpoint directory cannot be created or file written
    """
    session_dir = SESSIONS_DIR / context.jira_key
    session_dir.mkdir(parents=True, exist_ok=True)

    # Determine usage: controller state wins when provided
    usage = backpressure.to_dict() if backpressure is not None else context.usage

    # Convert context to dict for JSON serialization
    checkpoint_data = {
        "jira_key": context.jira_key,
        "jira_summary": context.jira_summary,
        "current_phase": context.current_phase,
        "raw_acceptance_criteria": context.raw_acceptance_criteria,
        "constitution": context.constitution,
        "classifications": context.classifications,
        "postconditions": context.postconditions,
        "preconditions": context.preconditions,
        "failure_modes": context.failure_modes,
        "invariants": context.invariants,
        "verification_routing": context.verification_routing,
        "ears_statements": context.ears_statements,
        "traceability_map": context.traceability_map,
        "approved": context.approved,
        "approved_by": context.approved_by,
        "approved_at": context.approved_at,
        "spec_path": context.spec_path,
        "generated_files": context.generated_files,
        "verdicts": context.verdicts,
        "all_passed": context.all_passed,
        "negotiation_log": context.negotiation_log,
        "session_id": context.session_id,
        "usage": usage,
    }

    checkpoint_path = session_dir / f"checkpoint_{phase}.json"
    with open(checkpoint_path, "w") as f:
        json.dump(checkpoint_data, f, indent=2)

    logger.info(f"Saved checkpoint for {context.jira_key} at {checkpoint_path}")
    return checkpoint_path


def load_checkpoint(
    jira_key: str,
) -> Optional[Union[Tuple[VerificationContext, int, BackPressureController], Tuple[VerificationContext, int]]]:
    """Load the most recent checkpoint for a given Jira key.

    Args:
        jira_key: The Jira ticket key to load a checkpoint for

    Returns:
        A tuple of ``(VerificationContext, phase_index, BackPressureController)``
        if a checkpoint exists, ``None`` otherwise.  The controller is restored
        from the checkpoint's ``usage`` field (or defaults to zeros for old
        checkpoints without usage data).

    Raises:
        json.JSONDecodeError: If the checkpoint file is corrupted
        ValueError: If the checkpoint data is invalid
    """
    session_dir = SESSIONS_DIR / jira_key
    if not session_dir.exists():
        logger.debug(f"No session directory found for {jira_key}")
        return None

    # Find the most recent checkpoint
    checkpoint_files = sorted(session_dir.glob("checkpoint_*.json"))
    if not checkpoint_files:
        logger.debug(f"No checkpoint files found for {jira_key}")
        return None

    latest_checkpoint = checkpoint_files[-1]
    logger.info(f"Loading latest checkpoint from {latest_checkpoint}")

    with open(latest_checkpoint, "r") as f:
        checkpoint_data = json.load(f)

    # Reconstruct the VerificationContext
    context = VerificationContext(
        jira_key=checkpoint_data["jira_key"],
        jira_summary=checkpoint_data["jira_summary"],
        raw_acceptance_criteria=checkpoint_data["raw_acceptance_criteria"],
        constitution=checkpoint_data["constitution"],
    )

    # Restore phase-specific data
    context.current_phase = checkpoint_data["current_phase"]
    context.classifications = checkpoint_data.get("classifications", [])
    context.postconditions = checkpoint_data.get("postconditions", [])
    context.preconditions = checkpoint_data.get("preconditions", [])
    context.failure_modes = checkpoint_data.get("failure_modes", [])
    context.invariants = checkpoint_data.get("invariants", [])
    context.verification_routing = checkpoint_data.get("verification_routing", {})
    context.ears_statements = checkpoint_data.get("ears_statements", [])
    context.traceability_map = checkpoint_data.get("traceability_map", {})
    context.approved = checkpoint_data.get("approved", False)
    context.approved_by = checkpoint_data.get("approved_by", "")
    context.approved_at = checkpoint_data.get("approved_at", "")
    context.spec_path = checkpoint_data.get("spec_path", "")
    context.generated_files = checkpoint_data.get("generated_files", {})
    context.verdicts = checkpoint_data.get("verdicts", [])
    context.all_passed = checkpoint_data.get("all_passed", False)
    context.negotiation_log = checkpoint_data.get("negotiation_log", [])
    context.session_id = checkpoint_data.get("session_id", "")
    context.usage = checkpoint_data.get("usage", {})

    # Restore BackPressureController from usage data
    controller = BackPressureController.from_dict(context.usage)

    # Extract phase index from phase name (e.g., "phase_1" -> 0, "phase_2" -> 1)
    phase_name = context.current_phase
    from verify.negotiation.harness import PHASES

    try:
        phase_index = PHASES.index(phase_name)
    except ValueError:
        logger.warning(f"Unknown phase name: {phase_name}, defaulting to index 0")
        phase_index = 0

    logger.info(f"Restored context for {jira_key} at {phase_name} (index {phase_index})")
    return (context, phase_index, controller)


def has_checkpoint(jira_key: str) -> bool:
    """Check if a checkpoint exists for the given Jira key.

    Args:
        jira_key: The Jira ticket key to check

    Returns:
        True if at least one checkpoint file exists, False otherwise
    """
    session_dir = SESSIONS_DIR / jira_key
    if not session_dir.exists():
        return False
    return len(list(session_dir.glob("checkpoint_phase_*.json"))) > 0


def get_session_info(jira_key: str) -> Optional[dict]:
    """Get information about the most recent session for a given Jira key.

    Args:
        jira_key: The Jira ticket key to get info for

    Returns:
        A dict with session metadata (phase, timestamp, etc.) if a checkpoint exists,
        None otherwise
    """
    session_dir = SESSIONS_DIR / jira_key
    if not session_dir.exists():
        return None

    checkpoint_files = sorted(session_dir.glob("checkpoint_phase_*.json"))
    if not checkpoint_files:
        return None

    latest_checkpoint = checkpoint_files[-1]
    with open(latest_checkpoint, "r") as f:
        data = json.load(f)

    return {
        "jira_key": jira_key,
        "jira_summary": data.get("jira_summary", ""),
        "acceptance_criteria_count": len(data.get("raw_acceptance_criteria", [])),
        "current_phase": data.get("current_phase", "unknown"),
        "checkpoint_path": str(latest_checkpoint),
        "log_entries": len(data.get("negotiation_log", [])),
        "approved": data.get("approved", False),
        "phase_number": _resume_phase_number(data.get("current_phase", "unknown")),
        "phase_title": PHASE_TITLES.get(_resume_phase_number(data.get("current_phase", "unknown"))),
        "session_id": data.get("session_id", ""),
        "usage": data.get("usage", {}),
    }


def clear_session(jira_key: str) -> bool:
    """Delete all checkpoints for a given Jira key.

    Args:
        jira_key: The Jira ticket key to clear

    Returns:
        True if the session was cleared, False if no session existed

    Raises:
        OSError: If the session directory cannot be deleted
    """
    session_dir = SESSIONS_DIR / jira_key
    if not session_dir.exists():
        return False

    import shutil

    shutil.rmtree(session_dir)
    logger.info(f"Cleared session for {jira_key}")
    return True


def _resume_phase_number(current_phase: str) -> int:
    if not current_phase.startswith("phase_"):
        return 0

    try:
        return int(current_phase.split("_", 1)[1])
    except ValueError:
        return 0
