"""Feature 2.9: Evaluator-Optimizer — adversarial critique of phase outputs.

After each phase produces output and passes deterministic validation (validate.py),
this module provides a second-pass critique that catches semantic gaps the enum
checks can't — missing precondition categories, insufficient failure mode coverage,
security oversights, etc.

Design: Deterministic checks first (zero AI), then optionally LLM-powered deeper
analysis. This follows the harness engineering back-pressure pattern — agents
validate their own work before declaring success.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

from verify.context import VerificationContext
from verify.llm_client import LLMClient


# ── Minimum expected precondition categories for API behavior ──

ESSENTIAL_PRECONDITION_CATEGORIES = {"authentication", "data_existence"}

# Auth preconditions should have at least this many failure modes
MIN_AUTH_FAILURE_MODES = 2


@dataclass
class PhaseCritique:
    """Structured critique result from the evaluator-optimizer."""

    phase: str
    has_issues: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_phase_output(
    ctx: VerificationContext,
    phase: str,
    llm: Optional[LLMClient] = None,
) -> dict:
    """Evaluate a phase's output for completeness and quality.

    Runs deterministic checks first, then optionally LLM-powered deeper analysis.

    Args:
        ctx: The current VerificationContext with phase output populated.
        phase: Which phase to evaluate ("phase_1", "phase_3", "phase_4").
        llm: Optional LLM client for deeper analysis (not used in deterministic checks).

    Returns:
        Dict with keys: has_issues, issues, suggestions, phase.
    """
    checker = _PHASE_CHECKERS.get(phase)
    if checker is None:
        return PhaseCritique(
            phase=phase,
            has_issues=False,
            issues=[],
            suggestions=[f"No evaluator-optimizer defined for {phase}"],
        ).to_dict()

    critique = checker(ctx)
    return critique.to_dict()


# ── Phase 1: Classification critique ──────────────────────────────────────


def _critique_phase_1(ctx: VerificationContext) -> PhaseCritique:
    """Critique Phase 1 classifications.

    Checks:
    - If there are API behaviors but no security_invariant classifications,
      flag that security considerations may be missing.
    """
    issues: list[str] = []
    suggestions: list[str] = []

    classifications = ctx.classifications or []
    types_present = {c.get("type") for c in classifications}

    has_api_behavior = "api_behavior" in types_present
    has_security = "security_invariant" in types_present

    if has_api_behavior and not has_security:
        issues.append(
            "No security_invariant classifications found. API endpoints typically "
            "need security considerations (e.g., forbidden fields, auth requirements)."
        )
        suggestions.append(
            "Consider adding security_invariant for sensitive endpoints, or confirm "
            "that security is handled at the infrastructure level."
        )

    # Check for PUT/POST/DELETE without authorization considerations
    mutating_methods = {"PUT", "POST", "DELETE", "PATCH"}
    for clf in classifications:
        iface = clf.get("interface", {})
        method = iface.get("method", "").upper()
        if method in mutating_methods and clf.get("actor") != "admin":
            if not has_security:
                issues.append(
                    f"AC[{clf.get('ac_index')}] uses {method} but no security_invariant "
                    f"classification exists to enforce authorization rules."
                )

    return PhaseCritique(
        phase="phase_1",
        has_issues=len(issues) > 0,
        issues=issues,
        suggestions=suggestions,
    )


# ── Phase 3: Precondition critique ───────────────────────────────────────


def _critique_phase_3(ctx: VerificationContext) -> PhaseCritique:
    """Critique Phase 3 preconditions.

    Checks:
    - Essential categories (authentication, data_existence) should be present
      for API behavior requirements.
    """
    issues: list[str] = []
    suggestions: list[str] = []

    preconditions = ctx.preconditions or []
    categories_present = {p.get("category") for p in preconditions}

    # Check if we have API behavior classifications that need preconditions
    has_api = any(
        c.get("type") == "api_behavior" for c in (ctx.classifications or [])
    )

    if has_api:
        missing_categories = ESSENTIAL_PRECONDITION_CATEGORIES - categories_present
        for cat in sorted(missing_categories):
            issues.append(
                f"Missing precondition category: {cat}. API endpoints typically "
                f"require {cat} preconditions."
            )
            suggestions.append(
                f"Add a {cat} precondition to cover the common {cat} failure path."
            )

    return PhaseCritique(
        phase="phase_3",
        has_issues=len(issues) > 0,
        issues=issues,
        suggestions=suggestions,
    )


# ── Phase 4: Failure mode critique ──────────────────────────────────────


def _critique_phase_4(ctx: VerificationContext) -> PhaseCritique:
    """Critique Phase 4 failure modes.

    Checks:
    - Every precondition should have at least one failure mode.
    - Authentication preconditions should have multiple failure modes
      (missing token, expired token, malformed token, etc.).
    """
    issues: list[str] = []
    suggestions: list[str] = []

    preconditions = ctx.preconditions or []
    failure_modes = ctx.failure_modes or []

    # Build mapping: precondition_id → list of failure modes
    pre_to_failures: dict[str, list[dict]] = {}
    for pre in preconditions:
        pre_to_failures[pre["id"]] = []

    for fm in failure_modes:
        violates = fm.get("violates", "")
        if violates in pre_to_failures:
            pre_to_failures[violates].append(fm)

    # Check 1: Every precondition should have at least one failure mode
    for pre in preconditions:
        pid = pre["id"]
        if not pre_to_failures.get(pid):
            issues.append(
                f"Precondition {pid} ({pre.get('description', '')}) has no failure modes. "
                f"Every precondition should have at least one failure path."
            )
            suggestions.append(
                f"Add failure mode(s) for {pid} covering what happens when "
                f"{pre.get('description', 'this precondition')} is violated."
            )

    # Check 2: Auth preconditions should have multiple failure modes
    for pre in preconditions:
        pid = pre["id"]
        category = pre.get("category", "")
        failures_for_pre = pre_to_failures.get(pid, [])

        if category == "authentication" and len(failures_for_pre) < MIN_AUTH_FAILURE_MODES:
            issues.append(
                f"Authentication precondition {pid} has only {len(failures_for_pre)} "
                f"failure mode(s). Authentication typically has multiple failure paths: "
                f"missing token, expired token, malformed token, wrong issuer, revoked token."
            )
            suggestions.append(
                f"Consider adding more authentication failure modes for {pid}: "
                f"expired token, malformed token, revoked token."
            )

    return PhaseCritique(
        phase="phase_4",
        has_issues=len(issues) > 0,
        issues=issues,
        suggestions=suggestions,
    )


# ── Registry ─────────────────────────────────────────────────────────────

_PHASE_CHECKERS = {
    "phase_1": _critique_phase_1,
    "phase_3": _critique_phase_3,
    "phase_4": _critique_phase_4,
}
