"""RED tests for Phase 7 — EARS Formalization & Human Approval.

TDD: Write these tests FIRST (RED), then implement phase7.py (GREEN).

Phase 7 is an interactive LLM phase that synthesizes all outputs into EARS statements
using 5 patterns:
1. UBIQUITOUS: The system SHALL...
2. EVENT-DRIVEN: WHEN {trigger}, the system SHALL...
3. STATE-DRIVEN: WHILE {state}, the system SHALL...
4. UNWANTED: IF {condition}, THEN the system SHALL...
5. OPTIONAL: WHERE {feature}, the system SHALL...
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
        "jira_key": "TEST-007",
        "jira_summary": "Test Phase 7",
        "raw_acceptance_criteria": [
            {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
        ],
        "constitution": {
            "project": {"framework": "spring-boot", "language": "java"},
        },
    }
    defaults.update(kwargs)
    ctx = VerificationContext(**defaults)
    # Populate all prior phase outputs
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
    ctx.verification_routing = {
        "routes": [
            {"req_id": "REQ-001", "skill": "cucumber_java", "refs": ["REQ-001.success"]},
        ]
    }
    return ctx


class TestPhase7Import:
    """Phase 7 module should be importable."""

    def test_import_run_phase7(self):
        from verify.negotiation.phase7 import run_phase7
        assert callable(run_phase7)

    def test_import_system_prompt(self):
        from verify.negotiation.phase7 import SYSTEM_PROMPT
        assert isinstance(SYSTEM_PROMPT, str)
        assert "ears" in SYSTEM_PROMPT.lower()


class TestPhase7Output:
    """Phase 7 should produce structured EARS statements."""

    def test_produces_ears_statements(self):
        from verify.negotiation.phase7 import run_phase7
        ctx = _make_context()
        llm = LLMClient()
        result = run_phase7(ctx, llm)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_ears_statements_are_dicts(self):
        from verify.negotiation.phase7 import run_phase7
        ctx = _make_context()
        llm = LLMClient()
        result = run_phase7(ctx, llm)
        for stmt in result:
            assert isinstance(stmt, dict), f"EARS statement must be dict, got {type(stmt)}"

    def test_ears_have_required_fields(self):
        from verify.negotiation.phase7 import run_phase7
        ctx = _make_context()
        llm = LLMClient()
        result = run_phase7(ctx, llm)
        for stmt in result:
            assert "id" in stmt, f"Missing 'id' in EARS: {stmt}"
            assert "pattern" in stmt, f"Missing 'pattern' in EARS: {stmt}"
            assert "statement" in stmt, f"Missing 'statement' in EARS: {stmt}"
            assert "traces_to" in stmt, f"Missing 'traces_to' in EARS: {stmt}"

    def test_ears_patterns_are_valid(self):
        from verify.negotiation.phase7 import run_phase7, VALID_EARS_PATTERNS
        ctx = _make_context()
        llm = LLMClient()
        result = run_phase7(ctx, llm)
        for stmt in result:
            assert stmt["pattern"] in VALID_EARS_PATTERNS, (
                f"Invalid EARS pattern '{stmt['pattern']}'. Must be one of {VALID_EARS_PATTERNS}"
            )

    def test_ears_stored_on_context(self):
        from verify.negotiation.phase7 import run_phase7
        ctx = _make_context()
        llm = LLMClient()
        run_phase7(ctx, llm)
        assert len(ctx.ears_statements) > 0
        # Ensure they are dicts (not plain strings like old synthesis)
        assert isinstance(ctx.ears_statements[0], dict)


class TestPhase7Feedback:
    """Phase 7 should support multi-turn revision via feedback."""

    def test_revision_with_feedback(self):
        from verify.negotiation.phase7 import run_phase7
        ctx = _make_context()
        llm = LLMClient()

        # First run
        run_phase7(ctx, llm)

        # Second run with feedback
        result = run_phase7(ctx, llm, feedback="Add more specific WHEN conditions")
        assert isinstance(result, list)
        assert len(result) > 0


class TestPhase7Validation:
    """Phase 7 should validate EARS statements."""

    def test_validate_ears_function_exists(self):
        from verify.negotiation.validate import validate_ears_statements
        assert callable(validate_ears_statements)

    def test_validate_ears_rejects_empty(self):
        from verify.negotiation.validate import validate_ears_statements
        is_valid, errors = validate_ears_statements([])
        assert not is_valid

    def test_validate_ears_rejects_bad_pattern(self):
        from verify.negotiation.validate import validate_ears_statements
        bad_ears = [
            {"id": "EARS-001", "pattern": "INVALID", "statement": "test", "traces_to": "REQ-001"},
        ]
        is_valid, errors = validate_ears_statements(bad_ears)
        assert not is_valid

    def test_validate_ears_accepts_good_data(self):
        from verify.negotiation.validate import validate_ears_statements
        good_ears = [
            {"id": "EARS-001", "pattern": "EVENT_DRIVEN", "statement": "WHEN GET /api/v1/users/me is requested THEN system SHALL respond 200", "traces_to": "REQ-001"},
            {"id": "EARS-002", "pattern": "UNWANTED", "statement": "IF no auth token THEN system SHALL respond 401", "traces_to": "REQ-001.FAIL-001"},
        ]
        is_valid, errors = validate_ears_statements(good_ears)
        assert is_valid
