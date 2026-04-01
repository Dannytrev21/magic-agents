from pathlib import Path
from unittest.mock import Mock

from verify.context import VerificationContext
from verify.negotiation.checkpoint import save_checkpoint
from verify.runtime import SessionStore


def test_restore_reuses_persisted_session_identity(monkeypatch, tmp_path):
    monkeypatch.setattr("verify.negotiation.checkpoint.SESSIONS_DIR", Path(tmp_path))

    context = VerificationContext(
        jira_key="RUNTIME-001",
        jira_summary="Runtime restore",
        raw_acceptance_criteria=[
            {"index": 0, "text": "Operator can resume the saved session", "checked": False},
        ],
        constitution={},
    )
    context.current_phase = "phase_2"
    context.session_id = "session-runtime-001"

    save_checkpoint(context, "phase_2")

    store = SessionStore()
    first_restore = store.restore("RUNTIME-001", llm=Mock())
    second_restore = store.restore("RUNTIME-001", llm=Mock())

    assert first_restore is not None
    assert first_restore.session_id == "session-runtime-001"
    assert first_restore.context.session_id == "session-runtime-001"
    assert second_restore is first_restore
