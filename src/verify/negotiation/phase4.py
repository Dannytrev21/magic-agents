"""Phase 4 Skill — Failure Mode Enumeration.

Systematically enumerates every failure mode for every precondition (FMEA-inspired).
Plan Section 3.6.
"""

import json

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.validate import validate_failure_modes

SYSTEM_PROMPT = """\
You are a verification engineer performing failure mode enumeration (FMEA-inspired).

Given preconditions, enumerate EVERY failure mode for EACH one. You MUST consider these subcategories:
- Authentication: missing token, expired token, malformed token, wrong issuer, revoked token
- Authorization: missing role, insufficient scope, wrong tenant
- Data existence: never existed, soft-deleted, hard-deleted
- Data state: each invalid state (inactive, suspended, pending, locked)
- Rate limit: per-user exceeded, global exceeded
- System health: dependency down, timeout, connection refused

Each failure mode MUST have:
- id: sequential, format FAIL-NNN (e.g., FAIL-001, FAIL-002)
- description: what went wrong
- violates: the precondition ID this failure violates (MUST reference an existing PRE-NNN)
- status: numeric HTTP status code
- body: exact error response body as a JSON object

You MUST also return a "questions" list with security-relevant questions. Return empty list only if all failure modes are straightforward.

{constitution_context}

SECURITY DECISIONS (ask the developer about these):
- If a user was deleted: should the API return 404 (not found) or 410 (gone)?
  Returning 410 leaks that an account once existed.
- If authorization fails vs authentication fails: should status codes differ?
  Different codes may leak whether an account exists.

RULES:
- Every precondition MUST have at least one failure mode.
- IDs MUST be sequential and unique.
- The "violates" field MUST reference an existing precondition ID.
- Status MUST be a numeric HTTP status code.
- Body MUST use the project's standard error format if one is defined.
- Do not include commentary outside the JSON.

Respond with ONLY this JSON structure:
{{
  "failure_modes": [
    {{"id": "FAIL-001", "description": "No auth token provided", "violates": "PRE-001", "status": 401, "body": {{"error": "unauthorized", "message": "Bearer token required"}}}}
  ],
  "questions": ["Should soft-deleted users return 404 or 410?"]
}}"""


def _build_constitution_context(constitution: dict) -> str:
    """Load what Phase 4 needs — error format + security invariants."""
    if not constitution:
        return "No project constitution provided."
    parts = []
    api = constitution.get("api", {})
    if api:
        error_fmt = api.get("error_format", {})
        if error_fmt:
            example = error_fmt.get("example", error_fmt)
            parts.append(f"Standard error format: {example}")
        codes = api.get("common_status_codes", [])
        if codes:
            parts.append(f"Common status codes: {codes}")
    security = (
        constitution.get("verification_standards", {})
        .get("security_invariants", [])
    )
    if security:
        parts.append("Security invariants:\n    - " + "\n    - ".join(security))
    return "Project context:\n  " + "\n  ".join(parts) if parts else "No project constitution provided."


def run_phase4(
    context: VerificationContext,
    llm: LLMClient,
    feedback: str | None = None,
    max_retries: int = 2,
) -> list[dict]:
    """Run Phase 4: enumerate failure modes for each precondition."""
    if not context.preconditions:
        context.failure_modes = []
        return []

    pre_ids = {p["id"] for p in context.preconditions}

    system = SYSTEM_PROMPT.format(
        constitution_context=_build_constitution_context(context.constitution)
    )
    user_message = "Preconditions:\n"
    for p in context.preconditions:
        user_message += f"- {p['id']}: {p['description']} [{p['category']}] — {p.get('formal', '')}\n"

    # Multi-turn revision
    if feedback and context.failure_modes:
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": json.dumps({"failure_modes": context.failure_modes}, indent=2)},
            {"role": "user", "content": f"Developer feedback: {feedback}\n\nPlease revise your failure modes based on this feedback. Respond with the complete updated JSON."},
        ]
        response = llm.chat_multi(system, messages, response_format="json")
        failure_modes = response.get("failure_modes", []) if isinstance(response, dict) else []
        context.failure_modes = failure_modes
        return failure_modes

    for attempt in range(max_retries + 1):
        response = llm.chat(system, user_message, response_format="json")
        failure_modes = response.get("failure_modes", []) if isinstance(response, dict) else []

        is_valid, errors = validate_failure_modes(failure_modes, pre_ids)
        if is_valid:
            context.failure_modes = failure_modes
            return failure_modes

        if attempt < max_retries:
            user_message += (
                f"\n\nValidation errors:\n" + "\n".join(f"- {e}" for e in errors)
                + "\n\nPlease fix and try again."
            )

    context.failure_modes = failure_modes
    return failure_modes
