"""RED tests for Phase 5 — Interactive Invariant Extraction.

TDD: Write these tests FIRST (RED), then implement phase5.py (GREEN).

Phase 5 is an interactive LLM phase that extracts invariants from:
1. Explicit AC text invariants
2. Constitution's security_invariants
3. Inferences from data model (PII detection, data classification)

Each invariant has: id (INV-NNN), type, rule, source, verification_type
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
        "jira_key": "TEST-005",
        "jira_summary": "Test Phase 5",
        "raw_acceptance_criteria": [
            {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
        ],
        "constitution": {
            "project": {"framework": "spring-boot", "language": "java"},
            "verification_standards": {
                "security_invariants": [
                    "Response MUST NOT contain password field",
                    "Response MUST NOT contain SSN field",
                ]
            },
        },
    }
    defaults.update(kwargs)
    return VerificationContext(**defaults)


class TestPhase5Import:
    """Phase 5 module should be importable."""

    def test_import_run_phase5(self):
        from verify.negotiation.phase5 import run_phase5
        assert callable(run_phase5)

    def test_import_system_prompt(self):
        from verify.negotiation.phase5 import SYSTEM_PROMPT
        assert isinstance(SYSTEM_PROMPT, str)
        assert "invariant" in SYSTEM_PROMPT.lower()


class TestPhase5Output:
    """Phase 5 should produce properly structured invariants."""

    def test_produces_invariants(self):
        from verify.negotiation.phase5 import run_phase5
        ctx = _make_context()
        # Provide postconditions with forbidden_fields (populated by earlier phases)
        ctx.postconditions = [
            {"ac_index": 0, "status": 200, "forbidden_fields": ["password", "ssn"]},
        ]
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid JWT", "formal": "jwt != null", "category": "authentication"},
        ]
        llm = LLMClient()
        result = run_phase5(ctx, llm)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_invariants_have_required_fields(self):
        from verify.negotiation.phase5 import run_phase5
        ctx = _make_context()
        ctx.postconditions = [
            {"ac_index": 0, "status": 200, "forbidden_fields": ["password"]},
        ]
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid JWT", "formal": "jwt != null", "category": "authentication"},
        ]
        llm = LLMClient()
        result = run_phase5(ctx, llm)

        for inv in result:
            assert "id" in inv, f"Missing 'id' in invariant: {inv}"
            assert inv["id"].startswith("INV-"), f"ID must start with INV-: {inv['id']}"
            assert "type" in inv, f"Missing 'type' in invariant: {inv}"
            assert "rule" in inv, f"Missing 'rule' in invariant: {inv}"
            assert "source" in inv, f"Missing 'source' in invariant: {inv}"

    def test_invariants_stored_on_context(self):
        from verify.negotiation.phase5 import run_phase5
        ctx = _make_context()
        ctx.postconditions = [
            {"ac_index": 0, "status": 200, "forbidden_fields": ["password"]},
        ]
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid JWT", "formal": "jwt != null", "category": "authentication"},
        ]
        llm = LLMClient()
        run_phase5(ctx, llm)
        assert len(ctx.invariants) > 0

    def test_invariant_types_are_valid(self):
        from verify.negotiation.phase5 import run_phase5, VALID_INVARIANT_TYPES
        ctx = _make_context()
        ctx.postconditions = [
            {"ac_index": 0, "status": 200, "forbidden_fields": ["password"]},
        ]
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid JWT", "formal": "jwt != null", "category": "authentication"},
        ]
        llm = LLMClient()
        result = run_phase5(ctx, llm)

        for inv in result:
            assert inv["type"] in VALID_INVARIANT_TYPES, (
                f"Invalid invariant type '{inv['type']}'. Must be one of {VALID_INVARIANT_TYPES}"
            )


class TestPhase5Feedback:
    """Phase 5 should support multi-turn revision via feedback."""

    def test_revision_with_feedback(self):
        from verify.negotiation.phase5 import run_phase5
        ctx = _make_context()
        ctx.postconditions = [
            {"ac_index": 0, "status": 200, "forbidden_fields": ["password"]},
        ]
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid JWT", "formal": "jwt != null", "category": "authentication"},
        ]
        llm = LLMClient()

        # First run
        run_phase5(ctx, llm)
        initial_count = len(ctx.invariants)

        # Second run with feedback
        result = run_phase5(ctx, llm, feedback="Also add idempotency invariants")
        assert isinstance(result, list)
        assert len(result) > 0


class TestPhase5Validation:
    """Phase 5 should use deterministic validation (Block Principle 1)."""

    def test_validate_invariants_function_exists(self):
        from verify.negotiation.validate import validate_invariants
        assert callable(validate_invariants)

    def test_validate_invariants_rejects_bad_ids(self):
        from verify.negotiation.validate import validate_invariants
        bad_invariants = [
            {"id": "BAD-001", "type": "security", "rule": "test", "source": "constitution"},
        ]
        is_valid, errors = validate_invariants(bad_invariants)
        assert not is_valid
        assert any("INV-" in e for e in errors)

    def test_validate_invariants_rejects_bad_types(self):
        from verify.negotiation.validate import validate_invariants
        bad_invariants = [
            {"id": "INV-001", "type": "invalid_type", "rule": "test", "source": "constitution"},
        ]
        is_valid, errors = validate_invariants(bad_invariants)
        assert not is_valid

    def test_validate_invariants_accepts_good_data(self):
        from verify.negotiation.validate import validate_invariants
        good_invariants = [
            {"id": "INV-001", "type": "security", "rule": "No password in response", "source": "constitution"},
            {"id": "INV-002", "type": "data_integrity", "rule": "IDs are immutable", "source": "ac_text"},
        ]
        is_valid, errors = validate_invariants(good_invariants)
        assert is_valid
        assert len(errors) == 0
