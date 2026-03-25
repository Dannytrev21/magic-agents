"""RED tests for Phase 6 — Completeness Sweep & Verification Routing.

TDD: Write these tests FIRST (RED), then implement phase6.py (GREEN).

Phase 6 is an interactive LLM phase that:
1. Runs a standardized completeness checklist (auth, input validation, errors, etc.)
2. Flags gaps and asks clarifying questions
3. Assigns verification types and skills via routing table
"""

import json
import os

import pytest


@pytest.fixture(autouse=True)
def ensure_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


from verify.context import VerificationContext
from verify.llm_client import LLMClient


def _make_context(**kwargs):
    defaults = {
        "jira_key": "TEST-006",
        "jira_summary": "Test Phase 6",
        "raw_acceptance_criteria": [
            {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
        ],
        "constitution": {
            "project": {"framework": "spring-boot", "language": "java"},
        },
    }
    defaults.update(kwargs)
    ctx = VerificationContext(**defaults)
    # Populate prior phase outputs
    ctx.classifications = [
        {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user",
         "interface": {"method": "GET", "path": "/api/v1/users/me"}},
    ]
    ctx.postconditions = [
        {"ac_index": 0, "status": 200, "content_type": "application/json",
         "schema": {"id": {"type": "integer"}}, "forbidden_fields": ["password"]},
    ]
    ctx.preconditions = [
        {"id": "PRE-001", "description": "Valid JWT", "formal": "jwt != null", "category": "authentication"},
    ]
    ctx.failure_modes = [
        {"id": "FAIL-001", "description": "No auth token", "violates": "PRE-001", "status": 401,
         "body": {"error": "unauthorized"}},
    ]
    ctx.invariants = [
        {"id": "INV-001", "type": "security", "rule": "No password in response", "source": "constitution"},
    ]
    return ctx


class TestPhase6Import:
    """Phase 6 module should be importable."""

    def test_import_run_phase6(self):
        from verify.negotiation.phase6 import run_phase6
        assert callable(run_phase6)

    def test_import_system_prompt(self):
        from verify.negotiation.phase6 import SYSTEM_PROMPT
        assert isinstance(SYSTEM_PROMPT, str)
        assert "completeness" in SYSTEM_PROMPT.lower()


class TestPhase6Output:
    """Phase 6 should produce completeness results and routing."""

    def test_produces_routing(self):
        from verify.negotiation.phase6 import run_phase6
        ctx = _make_context()
        llm = LLMClient()
        result = run_phase6(ctx, llm)
        assert isinstance(result, dict)
        assert "checklist" in result
        assert "routing" in result

    def test_checklist_has_items(self):
        from verify.negotiation.phase6 import run_phase6
        ctx = _make_context()
        llm = LLMClient()
        result = run_phase6(ctx, llm)
        checklist = result["checklist"]
        assert isinstance(checklist, list)
        assert len(checklist) > 0

    def test_checklist_item_structure(self):
        from verify.negotiation.phase6 import run_phase6
        ctx = _make_context()
        llm = LLMClient()
        result = run_phase6(ctx, llm)
        for item in result["checklist"]:
            assert "category" in item
            assert "status" in item  # "covered" or "gap"
            assert "detail" in item

    def test_routing_has_entries(self):
        from verify.negotiation.phase6 import run_phase6
        ctx = _make_context()
        llm = LLMClient()
        result = run_phase6(ctx, llm)
        routing = result["routing"]
        assert isinstance(routing, list)
        assert len(routing) > 0

    def test_routing_entry_structure(self):
        from verify.negotiation.phase6 import run_phase6
        ctx = _make_context()
        llm = LLMClient()
        result = run_phase6(ctx, llm)
        for entry in result["routing"]:
            assert "req_id" in entry
            assert "skill" in entry
            assert "refs" in entry

    def test_routing_stored_on_context(self):
        from verify.negotiation.phase6 import run_phase6
        ctx = _make_context()
        llm = LLMClient()
        run_phase6(ctx, llm)
        assert len(ctx.verification_routing) > 0


class TestPhase6Feedback:
    """Phase 6 should support multi-turn revision via feedback."""

    def test_revision_with_feedback(self):
        from verify.negotiation.phase6 import run_phase6
        ctx = _make_context()
        llm = LLMClient()

        # First run
        run_phase6(ctx, llm)

        # Second run with feedback
        result = run_phase6(ctx, llm, feedback="Also add rate limiting checks")
        assert isinstance(result, dict)
        assert "checklist" in result


class TestPhase6Validation:
    """Phase 6 should validate routing entries."""

    def test_validate_routing_function_exists(self):
        from verify.negotiation.validate import validate_routing
        assert callable(validate_routing)

    def test_validate_routing_rejects_empty(self):
        from verify.negotiation.validate import validate_routing
        is_valid, errors = validate_routing([])
        assert not is_valid

    def test_validate_routing_accepts_good_data(self):
        from verify.negotiation.validate import validate_routing
        good_routing = [
            {"req_id": "REQ-001", "skill": "cucumber_java", "refs": ["REQ-001.success", "REQ-001.FAIL-001"]},
        ]
        is_valid, errors = validate_routing(good_routing)
        assert is_valid
