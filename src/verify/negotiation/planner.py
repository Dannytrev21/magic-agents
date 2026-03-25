"""Feature 2.10: Plan-then-Execute — pre-negotiation planner.

Before Phase 1, the planner reads all ACs and proposes a negotiation plan:
which ACs are related (same endpoint), which are cross-cutting (security),
expected complexity, and AC groupings.

This runs as "Phase -1" conceptually — it configures the state machine before
classification begins. The developer can confirm or adjust the plan.

Design: Deterministic heuristics for grouping (endpoint extraction, keyword
matching), with optional LLM enrichment for ambiguous cases.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from verify.context import VerificationContext
from verify.llm_client import LLMClient


# ── Keywords that indicate cross-cutting concerns ──

SECURITY_KEYWORDS = frozenset({
    "401", "403", "unauthorized", "unauthenticated", "forbidden",
    "auth", "token", "jwt", "security", "password", "internal",
    "expose", "never", "sensitive", "secret", "credential",
})

PERFORMANCE_KEYWORDS = frozenset({
    "latency", "performance", "sla", "timeout", "response time",
    "throughput", "rate limit", "throttle",
})


@dataclass
class NegotiationPlan:
    """Structured plan for a negotiation session."""

    ac_groups: list[dict] = field(default_factory=list)
    cross_ac_dependencies: list[dict] = field(default_factory=list)
    estimated_complexity: str = "low"

    def to_dict(self) -> dict:
        return asdict(self)


def create_negotiation_plan(
    ctx: VerificationContext,
    llm: Optional[LLMClient] = None,
) -> dict:
    """Create a negotiation plan by analyzing all ACs before Phase 1.

    Steps:
    1. Extract endpoint references from AC text.
    2. Group ACs that reference the same endpoint.
    3. Identify cross-cutting ACs (security, performance).
    4. Estimate complexity.

    Returns:
        Dict with keys: ac_groups, cross_ac_dependencies, estimated_complexity.
    """
    acs = ctx.raw_acceptance_criteria or []

    # Step 1: Analyze each AC
    ac_analysis = [_analyze_ac(ac) for ac in acs]

    # Step 2: Group by endpoint
    groups = _group_by_endpoint(ac_analysis)

    # Step 3: Identify cross-cutting dependencies
    cross_cutting = _find_cross_cutting(ac_analysis)

    # Step 4: Estimate complexity
    complexity = _estimate_complexity(acs, groups, cross_cutting)

    plan = NegotiationPlan(
        ac_groups=groups,
        cross_ac_dependencies=cross_cutting,
        estimated_complexity=complexity,
    )
    return plan.to_dict()


# ── AC analysis helpers ──────────────────────────────────────────────────


def _analyze_ac(ac: dict) -> dict:
    """Analyze a single AC for endpoint references, keywords, and type hints."""
    text = ac.get("text", "").lower()
    index = ac["index"]

    # Extract endpoint references
    endpoint = _extract_endpoint(text)

    # Detect type hints
    predicted_type = _predict_type(text)

    # Check for cross-cutting keywords
    is_security = any(kw in text for kw in SECURITY_KEYWORDS)
    is_performance = any(kw in text for kw in PERFORMANCE_KEYWORDS)

    return {
        "index": index,
        "text": ac.get("text", ""),
        "endpoint": endpoint,
        "predicted_type": predicted_type,
        "is_security": is_security,
        "is_performance": is_performance,
    }


def _extract_endpoint(text: str) -> Optional[str]:
    """Extract an API endpoint path from AC text."""
    # Match patterns like /api/v1/users/me, GET /api/v1/dogs
    patterns = [
        r"((?:GET|POST|PUT|DELETE|PATCH)\s+)?(/api/[^\s,]+|/\w+/v\d+/[^\s,]+)",
        r"(/[a-z][a-z0-9_/{}]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Return just the path, not the method
            path = match.group(2) if match.group(2) else match.group(1)
            return path.rstrip(".,;:)")
    return None


def _predict_type(text: str) -> str:
    """Predict the requirement type from AC text."""
    text_lower = text.lower()

    if any(kw in text_lower for kw in SECURITY_KEYWORDS):
        return "security_invariant"
    if any(kw in text_lower for kw in PERFORMANCE_KEYWORDS):
        return "performance_sla"
    if any(kw in text_lower for kw in ("compliance", "gdpr", "regulation")):
        return "compliance"
    if any(kw in text_lower for kw in ("metric", "log", "trace", "monitor")):
        return "observability"

    return "api_behavior"


def _group_by_endpoint(analyses: list[dict]) -> list[dict]:
    """Group ACs that reference the same endpoint.

    ACs without endpoints get their own group.
    """
    endpoint_groups: dict[str, list[int]] = {}
    ungrouped: list[int] = []

    for analysis in analyses:
        endpoint = analysis.get("endpoint")
        if endpoint:
            # Normalize: strip trailing path params for grouping
            normalized = re.sub(r"/\{[^}]+\}$", "", endpoint)
            normalized = re.sub(r"/\d+$", "", normalized)
            if normalized not in endpoint_groups:
                endpoint_groups[normalized] = []
            endpoint_groups[normalized].append(analysis["index"])
        else:
            ungrouped.append(analysis["index"])

    groups = []

    for endpoint, indices in endpoint_groups.items():
        # Find the predicted type for this group (use the first non-security one)
        predicted_type = "api_behavior"
        for analysis in analyses:
            if analysis["index"] in indices and not analysis["is_security"]:
                predicted_type = analysis["predicted_type"]
                break

        groups.append({
            "ac_indices": indices,
            "predicted_type": predicted_type,
            "endpoint": endpoint,
            "reason": f"Same endpoint: {endpoint}" if len(indices) > 1
                      else f"Endpoint: {endpoint}",
        })

    # Add ungrouped ACs as individual groups
    for idx in ungrouped:
        analysis = next(a for a in analyses if a["index"] == idx)
        groups.append({
            "ac_indices": [idx],
            "predicted_type": analysis["predicted_type"],
            "endpoint": None,
            "reason": f"Standalone AC: {analysis['predicted_type']}",
        })

    return groups


def _find_cross_cutting(analyses: list[dict]) -> list[dict]:
    """Identify ACs that are cross-cutting concerns (security, performance)."""
    cross_cutting = []

    security_indices = [a["index"] for a in analyses if a["is_security"]]
    if security_indices:
        cross_cutting.append({
            "ac_indices": security_indices,
            "type": "security",
            "description": "Security-related ACs that cross-cut all API endpoints",
        })

    performance_indices = [a["index"] for a in analyses if a["is_performance"]]
    if performance_indices:
        cross_cutting.append({
            "ac_indices": performance_indices,
            "type": "performance",
            "description": "Performance SLA ACs that apply across endpoints",
        })

    return cross_cutting


def _estimate_complexity(
    acs: list[dict],
    groups: list[dict],
    cross_cutting: list[dict],
) -> str:
    """Estimate negotiation complexity based on AC count and structure."""
    ac_count = len(acs)
    group_count = len(groups)
    cross_cutting_count = len(cross_cutting)

    if ac_count <= 2 and cross_cutting_count == 0:
        return "low"
    elif ac_count <= 5 and cross_cutting_count <= 1:
        return "medium"
    else:
        return "high"
