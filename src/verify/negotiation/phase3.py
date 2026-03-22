"""Phase 3 Skill — Precondition Formalization.

Identifies every precondition that must hold for the happy path to succeed.
Uses Design by Contract technique (Plan Section 3.5).
"""

import json

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.validate import validate_preconditions

SYSTEM_PROMPT = """\
You are a verification engineer identifying preconditions using Design by Contract.

Given postconditions (happy-path contracts), identify EVERY precondition that must hold
for each to succeed.

Each precondition MUST have:
- id: sequential, format PRE-NNN (e.g., PRE-001, PRE-002)
- description: human-readable statement of what must be true
- formal: semi-formal expression using the pattern entity.field operator value
- category: MUST be one of: authentication, authorization, data_existence, data_state, rate_limit, system_health

You MUST also return a "questions" list — ask about implicit preconditions the developer may not have considered. Return empty list only if preconditions are comprehensive.

{constitution_context}

FORMAL EXPRESSION PATTERNS:
  - jwt != null AND jwt.exp > now()
  - db.users.exists(jwt.sub) == true
  - db.users.find(jwt.sub).status == 'active'
  - request.headers['Authorization'].startsWith('Bearer ')
  - rate_limiter.check(user_id, 'endpoint') == allowed

CATEGORY GUIDANCE:
  - authentication: JWT/token validation (present, not expired, well-formed)
  - authorization: role, scope, or ownership checks
  - data_existence: the referenced record exists (vs. never existed, deleted)
  - data_state: state-dependent checks (active vs. suspended, pending, locked)
  - rate_limit: per-user or global rate limiting
  - system_health: dependency availability (database, cache, external service)

RULES:
- Every postcondition MUST have at least one precondition.
- IDs MUST be sequential and unique.
- Category MUST be from the list above.
- Formal expression MUST be non-empty.
- Do not include commentary outside the JSON.

Respond with ONLY this JSON structure:
{{
  "preconditions": [
    {{"id": "PRE-001", "description": "Valid JWT bearer token is present", "formal": "jwt != null AND jwt.exp > now()", "category": "authentication"}}
  ],
  "questions": ["Does the JWT need specific roles or scopes?"]
}}"""


def _build_constitution_context(constitution: dict) -> str:
    """Load only what Phase 3 needs — auth mechanism and claims."""
    if not constitution:
        return "No project constitution provided."
    parts = []
    api = constitution.get("api", {})
    auth = api.get("auth", {})
    if auth:
        parts.append(f"Auth mechanism: {auth.get('mechanism', 'unknown')}")
        claims = auth.get("claims", [])
        if claims:
            parts.append(f"Required JWT claims: {', '.join(claims)}")
    return "Project context:\n  " + "\n  ".join(parts) if parts else "No project constitution provided."


def run_phase3(
    context: VerificationContext,
    llm: LLMClient,
    feedback: str | None = None,
    max_retries: int = 2,
) -> list[dict]:
    """Run Phase 3: identify preconditions for each postcondition."""
    if not context.postconditions:
        context.preconditions = []
        return []

    system = SYSTEM_PROMPT.format(
        constitution_context=_build_constitution_context(context.constitution)
    )
    user_message = "Postconditions (happy-path contracts):\n"
    for p in context.postconditions:
        user_message += (
            f"- AC[{p.get('ac_index', '?')}]: HTTP {p.get('status', '?')}, "
            f"schema: {p.get('schema', {})}, constraints: {p.get('constraints', [])}\n"
        )

    # Multi-turn revision
    if feedback and context.preconditions:
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": json.dumps({"preconditions": context.preconditions}, indent=2)},
            {"role": "user", "content": f"Developer feedback: {feedback}\n\nPlease revise your preconditions based on this feedback. Respond with the complete updated JSON."},
        ]
        response = llm.chat_multi(system, messages, response_format="json")
        preconditions = response.get("preconditions", []) if isinstance(response, dict) else []
        context.preconditions = preconditions
        return preconditions

    for attempt in range(max_retries + 1):
        response = llm.chat(system, user_message, response_format="json")
        preconditions = response.get("preconditions", []) if isinstance(response, dict) else []

        is_valid, errors = validate_preconditions(preconditions)
        if is_valid:
            context.preconditions = preconditions
            return preconditions

        if attempt < max_retries:
            user_message += (
                f"\n\nValidation errors:\n" + "\n".join(f"- {e}" for e in errors)
                + "\n\nPlease fix and try again."
            )

    context.preconditions = preconditions
    return preconditions
