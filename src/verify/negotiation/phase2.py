"""Phase 2 Skill — Happy Path Contract.

Proposes the exact success response for each api_behavior classification.
Block Principle 3: constitutional rules, not suggestions.
"""

import json

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.validate import validate_postconditions

SYSTEM_PROMPT = """\
You are a verification engineer defining postconditions (happy-path contracts).

For each API behavior classification, you MUST propose:
- ac_index: which AC this postcondition covers
- status: numeric HTTP success status code (e.g., 200, 201)
- content_type: response content type (e.g., "application/json")
- schema: response body schema — field names with type and required flag
- constraints: list of cross-field relationships (e.g., "response.id == jwt.sub")
- forbidden_fields: fields that MUST NEVER appear in the response

You MUST also return a "questions" list — ask about nullable fields, computed fields, or missing field constraints. Return empty list only if schema is unambiguous.

{constitution_context}

RULES:
- Every api_behavior AC MUST have exactly one postcondition.
- Status MUST be a numeric HTTP status code.
- Constraints MUST link response fields to request context explicitly.
  Example: "response.id MUST equal the JWT sub claim (prevents cross-user data leakage)"
- Forbidden fields: always include password, tokens, internal IDs unless the constitution says otherwise.
- Do not include commentary outside the JSON.

Respond with ONLY this JSON structure:
{{
  "postconditions": [
    {{
      "ac_index": 0,
      "status": 200,
      "content_type": "application/json",
      "schema": {{"id": {{"type": "string", "required": true}}}},
      "constraints": ["response.id == jwt.sub"],
      "forbidden_fields": ["password", "password_hash"]
    }}
  ],
  "questions": ["Is the avatar field nullable or always present?"]
}}"""


def _build_constitution_context(constitution: dict) -> str:
    """Load only what Phase 2 needs — API conventions + security invariants."""
    if not constitution:
        return "No project constitution provided."
    parts = []
    api = constitution.get("api", {})
    if api:
        parts.append(f"API base path: {api.get('base_path', '/api/v1')}")
        error_fmt = api.get("error_format", {})
        if error_fmt:
            parts.append(f"Error format: {error_fmt}")
    security = (
        constitution.get("verification_standards", {})
        .get("security_invariants", [])
    )
    if security:
        parts.append("Security invariants (NEVER expose):\n    - " + "\n    - ".join(security))
    return "Project context:\n  " + "\n  ".join(parts) if parts else "No project constitution provided."


def run_phase2(
    context: VerificationContext,
    llm: LLMClient,
    feedback: str | None = None,
    max_retries: int = 2,
) -> list[dict]:
    """Run Phase 2: define happy-path postconditions for each api_behavior AC."""
    api_behaviors = [c for c in context.classifications if c.get("type") == "api_behavior"]
    if not api_behaviors:
        context.postconditions = []
        return []

    api_indices = {c["ac_index"] for c in api_behaviors}

    system = SYSTEM_PROMPT.format(
        constitution_context=_build_constitution_context(context.constitution)
    )
    user_message = "API behavior classifications:\n"
    for c in api_behaviors:
        iface = c.get("interface", {})
        user_message += (
            f"- AC[{c['ac_index']}]: {iface.get('method', '?')} {iface.get('path', '?')} "
            f"(actor: {c.get('actor', '?')})\n"
        )

    # Multi-turn revision
    if feedback and context.postconditions:
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": json.dumps({"postconditions": context.postconditions}, indent=2)},
            {"role": "user", "content": f"Developer feedback: {feedback}\n\nPlease revise your postconditions based on this feedback. Respond with the complete updated JSON."},
        ]
        response = llm.chat_multi(system, messages, response_format="json")
        postconditions = response.get("postconditions", []) if isinstance(response, dict) else []
        context.postconditions = postconditions
        return postconditions

    for attempt in range(max_retries + 1):
        response = llm.chat(system, user_message, response_format="json")
        postconditions = response.get("postconditions", []) if isinstance(response, dict) else []

        is_valid, errors = validate_postconditions(postconditions, api_indices)
        if is_valid:
            context.postconditions = postconditions
            return postconditions

        if attempt < max_retries:
            user_message += (
                f"\n\nValidation errors:\n" + "\n".join(f"- {e}" for e in errors)
                + "\n\nPlease fix and try again."
            )

    context.postconditions = postconditions
    return postconditions
