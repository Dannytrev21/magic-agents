"""Tests for Feature 2.9: Evaluator-Optimizer pattern.

RED phase — these tests define the expected behavior for the evaluator-optimizer,
which provides adversarial critique of phase outputs before presenting to the developer.
"""

import os
import pytest

os.environ["LLM_MOCK"] = "true"

from verify.context import VerificationContext
from verify.llm_client import LLMClient


def _make_context(**overrides):
    defaults = dict(
        jira_key="TEST-001",
        jira_summary="Test ticket",
        raw_acceptance_criteria=[
            {"index": 0, "text": "User can view their profile", "checked": False}
        ],
        constitution={"project": {"framework": "spring_boot"}, "api": {"base_path": "/api/v1"}},
    )
    defaults.update(overrides)
    return VerificationContext(**defaults)


# ─── Module import ───────────────────────────────────────────────────────


class TestEvaluatorOptimizerImport:
    def test_module_importable(self):
        from verify.negotiation.evaluator_optimizer import evaluate_phase_output
        assert callable(evaluate_phase_output)

    def test_critique_class_importable(self):
        from verify.negotiation.evaluator_optimizer import PhaseCritique
        assert PhaseCritique is not None


# ─── Phase 1 critique (classifications) ─────────────────────────────────


class TestPhase1Critique:
    def test_returns_critique_dict(self):
        from verify.negotiation.evaluator_optimizer import evaluate_phase_output

        ctx = _make_context()
        ctx.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user",
             "interface": {"method": "GET", "path": "/api/v1/users/me"}}
        ]
        llm = LLMClient()
        result = evaluate_phase_output(ctx, "phase_1", llm)

        assert isinstance(result, dict)
        assert "has_issues" in result
        assert "issues" in result
        assert "suggestions" in result
        assert isinstance(result["issues"], list)
        assert isinstance(result["suggestions"], list)

    def test_detects_missing_security_consideration(self):
        """If an API behavior has no corresponding security_invariant, flag it."""
        from verify.negotiation.evaluator_optimizer import evaluate_phase_output

        ctx = _make_context(
            raw_acceptance_criteria=[
                {"index": 0, "text": "User can view profile", "checked": False},
                {"index": 1, "text": "User can update profile", "checked": False},
            ]
        )
        # All classified as api_behavior, no security_invariant
        ctx.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user",
             "interface": {"method": "GET", "path": "/api/v1/users/me"}},
            {"ac_index": 1, "type": "api_behavior", "actor": "authenticated_user",
             "interface": {"method": "PUT", "path": "/api/v1/users/me"}},
        ]
        llm = LLMClient()
        result = evaluate_phase_output(ctx, "phase_1", llm)

        # Should flag that there are no security-related classifications
        assert result["has_issues"] is True
        assert any("security" in issue.lower() for issue in result["issues"])


# ─── Phase 3 critique (preconditions) ───────────────────────────────────


class TestPhase3Critique:
    def test_detects_missing_precondition_categories(self):
        """Every API endpoint should have at least auth + data_existence preconditions."""
        from verify.negotiation.evaluator_optimizer import evaluate_phase_output

        ctx = _make_context()
        ctx.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user",
             "interface": {"method": "GET", "path": "/api/v1/users/me"}}
        ]
        ctx.postconditions = [{"ac_index": 0, "status": 200}]
        # Only authentication — missing data_existence
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid auth", "category": "authentication",
             "formal": "jwt != null"},
        ]
        llm = LLMClient()
        result = evaluate_phase_output(ctx, "phase_3", llm)

        assert result["has_issues"] is True
        assert any("data_existence" in issue.lower() for issue in result["issues"])

    def test_no_issues_when_categories_covered(self):
        """When all essential categories are present, no issues."""
        from verify.negotiation.evaluator_optimizer import evaluate_phase_output

        ctx = _make_context()
        ctx.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user",
             "interface": {"method": "GET", "path": "/api/v1/users/me"}}
        ]
        ctx.postconditions = [{"ac_index": 0, "status": 200}]
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid auth", "category": "authentication",
             "formal": "jwt != null"},
            {"id": "PRE-002", "description": "User exists", "category": "data_existence",
             "formal": "db.user.exists(jwt.sub)"},
        ]
        llm = LLMClient()
        result = evaluate_phase_output(ctx, "phase_3", llm)

        # Essential categories are covered — no deterministic issues
        assert result["has_issues"] is False or len(result["issues"]) == 0


# ─── Phase 4 critique (failure modes) ───────────────────────────────────


class TestPhase4Critique:
    def test_detects_uncovered_precondition(self):
        """Every precondition should have at least one failure mode."""
        from verify.negotiation.evaluator_optimizer import evaluate_phase_output

        ctx = _make_context()
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid auth", "category": "authentication",
             "formal": "jwt != null"},
            {"id": "PRE-002", "description": "User exists", "category": "data_existence",
             "formal": "db.user.exists(jwt.sub)"},
            {"id": "PRE-003", "description": "User active", "category": "data_state",
             "formal": "user.status == 'active'"},
        ]
        # Only failure modes for PRE-001 and PRE-002, not PRE-003
        ctx.failure_modes = [
            {"id": "FAIL-001", "violates": "PRE-001", "status": 401,
             "description": "No token", "body": {"error": "unauthorized"}},
            {"id": "FAIL-002", "violates": "PRE-002", "status": 404,
             "description": "Not found", "body": {"error": "not_found"}},
        ]
        llm = LLMClient()
        result = evaluate_phase_output(ctx, "phase_4", llm)

        assert result["has_issues"] is True
        assert any("PRE-003" in issue for issue in result["issues"])

    def test_detects_few_auth_failure_modes(self):
        """Auth preconditions should have multiple failure modes (missing, expired, malformed)."""
        from verify.negotiation.evaluator_optimizer import evaluate_phase_output

        ctx = _make_context()
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid auth", "category": "authentication",
             "formal": "jwt != null AND jwt.exp > now()"},
        ]
        # Only one failure mode for auth — should flag as insufficient
        ctx.failure_modes = [
            {"id": "FAIL-001", "violates": "PRE-001", "status": 401,
             "description": "No token", "body": {"error": "unauthorized"}},
        ]
        llm = LLMClient()
        result = evaluate_phase_output(ctx, "phase_4", llm)

        assert result["has_issues"] is True
        assert any("authentication" in issue.lower() or "auth" in issue.lower()
                    for issue in result["issues"])


# ─── PhaseCritique dataclass ─────────────────────────────────────────────


class TestPhaseCritique:
    def test_critique_fields(self):
        from verify.negotiation.evaluator_optimizer import PhaseCritique

        critique = PhaseCritique(
            phase="phase_1",
            has_issues=True,
            issues=["Missing security classification"],
            suggestions=["Consider adding security_invariant for sensitive endpoints"],
        )
        assert critique.phase == "phase_1"
        assert critique.has_issues is True
        assert len(critique.issues) == 1
        assert len(critique.suggestions) == 1

    def test_critique_to_dict(self):
        from verify.negotiation.evaluator_optimizer import PhaseCritique

        critique = PhaseCritique(
            phase="phase_3",
            has_issues=False,
            issues=[],
            suggestions=[],
        )
        d = critique.to_dict()
        assert isinstance(d, dict)
        assert d["phase"] == "phase_3"
        assert d["has_issues"] is False


# ─── Integration with harness ────────────────────────────────────────────


class TestHarnessIntegration:
    def test_evaluate_returns_serializable(self):
        """Result should be JSON-serializable for the web UI."""
        import json
        from verify.negotiation.evaluator_optimizer import evaluate_phase_output

        ctx = _make_context()
        ctx.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user",
             "interface": {"method": "GET", "path": "/api/v1/users/me"}}
        ]
        llm = LLMClient()
        result = evaluate_phase_output(ctx, "phase_1", llm)

        # Must be JSON-serializable
        serialized = json.dumps(result)
        assert isinstance(serialized, str)
