"""Phase 6 Skill — Completeness Sweep & Verification Routing.

Runs a standardized completeness checklist and assigns verification skills via routing.
"""

import json

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.validate import validate_routing

COMPLETENESS_CATEGORIES = [
    "authentication", "authorization", "input_validation",
    "output_schema", "error_handling", "rate_limiting",
    "pagination", "caching", "versioning", "idempotency",
    "observability", "security", "data_classification",
]

SYSTEM_PROMPT = """\
You are a verification engineer performing a completeness sweep and verification routing.

Given the full negotiation context (classifications, postconditions, preconditions,
failure modes, invariants), you must:

1. Run a **completeness checklist** across these categories:
   authentication, authorization, input_validation, output_schema, error_handling,
   rate_limiting, pagination, caching, versioning, idempotency, observability,
   security, data_classification

   For each category, mark it as "covered" (with detail on what covers it) or "gap"
   (with detail on what's missing).

2. Assign **verification routing** — for each requirement, determine which skill
   should generate the proof-of-correctness artifacts and what refs to test.

{constitution_context}

RULES:
- Every checklist category MUST be assessed.
- Routing entries MUST have req_id, skill, and refs.
- skill MUST be one of: cucumber_java, pytest_unit_test, gherkin_scenario, newrelic_alert_config, otel_config
- refs MUST reference actual spec elements (REQ-NNN.success, REQ-NNN.FAIL-NNN, etc.)

You MUST also return a "questions" list for any gaps found.

Respond with ONLY this JSON structure:
{{
  "checklist": [
    {{"category": "authentication", "status": "covered", "detail": "PRE-001 covers JWT validation"}},
    {{"category": "rate_limiting", "status": "gap", "detail": "No rate limiting preconditions defined"}}
  ],
  "routing": [
    {{"req_id": "REQ-001", "skill": "cucumber_java", "refs": ["REQ-001.success", "REQ-001.FAIL-001"]}}
  ],
  "questions": ["Should we add rate limiting for this endpoint?"]
}}"""


def _build_constitution_context(constitution: dict) -> str:
    """Load what Phase 6 needs — project context + verification standards."""
    if not constitution:
        return "No project constitution provided."
    parts = []
    project = constitution.get("project", {})
    if project:
        parts.append(f"Framework: {project.get('framework', 'unknown')}, Language: {project.get('language', 'unknown')}")
    api = constitution.get("api", {})
    if api:
        parts.append(f"API base path: {api.get('base_path', '/api/v1')}")
    return "Project context:\n  " + "\n  ".join(parts) if parts else "No project constitution provided."


def run_phase6(
    context: VerificationContext,
    llm: LLMClient,
    feedback: str | None = None,
    max_retries: int = 2,
) -> dict:
    """Run Phase 6: completeness sweep and verification routing."""
    system = SYSTEM_PROMPT.format(
        constitution_context=_build_constitution_context(context.constitution)
    )

    # Build user message from full context
    user_parts = []
    user_parts.append(f"Story: {context.jira_key} — {context.jira_summary}")

    user_parts.append("\nClassifications:")
    for clf in context.classifications:
        user_parts.append(f"  AC[{clf.get('ac_index')}]: {clf.get('type')} ({clf.get('actor')})")

    user_parts.append(f"\nPostconditions: {len(context.postconditions)}")
    user_parts.append(f"Preconditions: {len(context.preconditions)}")
    user_parts.append(f"Failure Modes: {len(context.failure_modes)}")
    user_parts.append(f"Invariants: {len(context.invariants)}")

    # List requirement IDs + elements for routing
    user_parts.append("\nRequirements to route:")
    for ac in context.raw_acceptance_criteria:
        req_id = f"REQ-{ac['index'] + 1:03d}"
        refs = [f"{req_id}.success"]
        for fm in context.failure_modes:
            refs.append(f"{req_id}.{fm['id']}")
        for inv in context.invariants:
            refs.append(f"{req_id}.{inv['id']}")
        user_parts.append(f"  {req_id}: {ac['text']} → refs: {refs}")

    user_message = "\n".join(user_parts)

    # Multi-turn revision with feedback
    if feedback and context.verification_routing:
        prev_result = context.verification_routing
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": json.dumps(prev_result, indent=2)},
            {"role": "user", "content": f"Developer feedback: {feedback}\n\nPlease revise based on this feedback. Respond with the complete updated JSON."},
        ]
        response = llm.chat_multi(system, messages, response_format="json")
        if isinstance(response, dict):
            context.verification_routing = response
            return response
        return {"checklist": [], "routing": [], "questions": []}

    for attempt in range(max_retries + 1):
        response = llm.chat(system, user_message, response_format="json")
        if not isinstance(response, dict):
            continue

        routing = response.get("routing", [])
        is_valid, errors = validate_routing(routing)
        if is_valid:
            context.verification_routing = response
            return response

        if attempt < max_retries:
            user_message += (
                f"\n\nValidation errors:\n" + "\n".join(f"- {e}" for e in errors)
                + "\n\nPlease fix and try again."
            )

    context.verification_routing = response if isinstance(response, dict) else {"checklist": [], "routing": [], "questions": []}
    return context.verification_routing
