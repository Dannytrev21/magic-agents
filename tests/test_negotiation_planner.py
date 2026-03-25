"""Tests for Feature 2.10: Plan-then-Execute — pre-negotiation planner.

RED phase — before Phase 1, a planner reads all ACs and proposes a negotiation
plan: which ACs are related, which phases each needs, expected complexity, and
cross-AC dependencies.
"""

import os
import pytest

os.environ["LLM_MOCK"] = "true"

from verify.context import VerificationContext
from verify.llm_client import LLMClient


def _make_context(**overrides):
    defaults = dict(
        jira_key="PLAN-001",
        jira_summary="User Profile CRUD",
        raw_acceptance_criteria=[
            {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
            {"index": 1, "text": "User can update their profile via PUT /api/v1/users/me", "checked": False},
            {"index": 2, "text": "API returns 401 for unauthenticated requests", "checked": False},
            {"index": 3, "text": "Internal user IDs are never exposed in API responses", "checked": False},
        ],
        constitution={"project": {"framework": "spring_boot"}, "api": {"base_path": "/api/v1"}},
    )
    defaults.update(overrides)
    return VerificationContext(**defaults)


# ─── Module import ───────────────────────────────────────────────────────


class TestPlannerImport:
    def test_module_importable(self):
        from verify.negotiation.planner import create_negotiation_plan
        assert callable(create_negotiation_plan)

    def test_plan_class_importable(self):
        from verify.negotiation.planner import NegotiationPlan
        assert NegotiationPlan is not None


# ─── Plan creation ───────────────────────────────────────────────────────


class TestPlanCreation:
    def test_returns_plan_dict(self):
        from verify.negotiation.planner import create_negotiation_plan

        ctx = _make_context()
        llm = LLMClient()
        plan = create_negotiation_plan(ctx, llm)

        assert isinstance(plan, dict)
        assert "ac_groups" in plan
        assert "cross_ac_dependencies" in plan
        assert "estimated_complexity" in plan

    def test_all_acs_represented(self):
        """Every AC should appear in at least one group."""
        from verify.negotiation.planner import create_negotiation_plan

        ctx = _make_context()
        llm = LLMClient()
        plan = create_negotiation_plan(ctx, llm)

        all_indices = set()
        for group in plan["ac_groups"]:
            all_indices.update(group["ac_indices"])

        expected = {ac["index"] for ac in ctx.raw_acceptance_criteria}
        assert expected == all_indices, f"Expected {expected}, got {all_indices}"

    def test_groups_have_required_fields(self):
        from verify.negotiation.planner import create_negotiation_plan

        ctx = _make_context()
        llm = LLMClient()
        plan = create_negotiation_plan(ctx, llm)

        for group in plan["ac_groups"]:
            assert "ac_indices" in group
            assert "predicted_type" in group
            assert "reason" in group
            assert isinstance(group["ac_indices"], list)
            assert len(group["ac_indices"]) >= 1


# ─── AC grouping logic ──────────────────────────────────────────────────


class TestACGrouping:
    def test_detects_related_endpoints(self):
        """ACs referencing the same endpoint should be grouped together."""
        from verify.negotiation.planner import create_negotiation_plan

        ctx = _make_context(
            raw_acceptance_criteria=[
                {"index": 0, "text": "GET /api/v1/users/me returns profile", "checked": False},
                {"index": 1, "text": "GET /api/v1/users/me includes email field", "checked": False},
                {"index": 2, "text": "POST /api/v1/orders creates a new order", "checked": False},
            ]
        )
        llm = LLMClient()
        plan = create_negotiation_plan(ctx, llm)

        # ACs 0 and 1 reference the same endpoint — should be in the same group
        for group in plan["ac_groups"]:
            indices = set(group["ac_indices"])
            if 0 in indices:
                assert 1 in indices, "ACs referencing same endpoint should be grouped"
                break

    def test_identifies_security_crosscutting(self):
        """Security-related ACs should be flagged as cross-cutting."""
        from verify.negotiation.planner import create_negotiation_plan

        ctx = _make_context()  # AC[2] is about 401, AC[3] is about field exposure
        llm = LLMClient()
        plan = create_negotiation_plan(ctx, llm)

        # Cross-cutting dependencies should mention security ACs
        dep_indices = set()
        for dep in plan.get("cross_ac_dependencies", []):
            dep_indices.update(dep.get("ac_indices", []))

        # AC[2] (401 auth) and AC[3] (field exposure) are cross-cutting
        assert 2 in dep_indices or 3 in dep_indices, \
            "Security ACs should be identified as cross-cutting"


# ─── Complexity estimation ───────────────────────────────────────────────


class TestComplexityEstimation:
    def test_single_ac_is_low(self):
        from verify.negotiation.planner import create_negotiation_plan

        ctx = _make_context(
            raw_acceptance_criteria=[
                {"index": 0, "text": "User can view profile", "checked": False},
            ]
        )
        llm = LLMClient()
        plan = create_negotiation_plan(ctx, llm)

        assert plan["estimated_complexity"] in ("low", "medium")

    def test_many_acs_is_higher(self):
        from verify.negotiation.planner import create_negotiation_plan

        ctx = _make_context(
            raw_acceptance_criteria=[
                {"index": i, "text": f"AC {i} description", "checked": False}
                for i in range(8)
            ]
        )
        llm = LLMClient()
        plan = create_negotiation_plan(ctx, llm)

        assert plan["estimated_complexity"] in ("medium", "high")


# ─── NegotiationPlan dataclass ───────────────────────────────────────────


class TestNegotiationPlan:
    def test_plan_fields(self):
        from verify.negotiation.planner import NegotiationPlan

        plan = NegotiationPlan(
            ac_groups=[
                {"ac_indices": [0, 1], "predicted_type": "api_behavior", "reason": "Same endpoint"}
            ],
            cross_ac_dependencies=[
                {"ac_indices": [2], "type": "security", "description": "Cross-cutting auth"}
            ],
            estimated_complexity="medium",
        )
        assert len(plan.ac_groups) == 1
        assert plan.estimated_complexity == "medium"

    def test_plan_to_dict(self):
        from verify.negotiation.planner import NegotiationPlan

        plan = NegotiationPlan(
            ac_groups=[],
            cross_ac_dependencies=[],
            estimated_complexity="low",
        )
        d = plan.to_dict()
        assert isinstance(d, dict)
        assert d["estimated_complexity"] == "low"

    def test_plan_serializable(self):
        import json
        from verify.negotiation.planner import NegotiationPlan

        plan = NegotiationPlan(
            ac_groups=[{"ac_indices": [0], "predicted_type": "api_behavior", "reason": "test"}],
            cross_ac_dependencies=[],
            estimated_complexity="low",
        )
        serialized = json.dumps(plan.to_dict())
        assert isinstance(serialized, str)
