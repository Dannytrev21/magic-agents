"""Phase 5 Skill — Interactive Invariant Extraction.

Extracts invariants from:
1. Explicit AC text invariants
2. Constitution's security_invariants
3. Inferences from data model (PII detection, data classification)

Each invariant has: id (INV-NNN), type, rule, source, verification_type
"""

import json

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.validate import validate_invariants

VALID_INVARIANT_TYPES = frozenset({
    "security", "performance", "data_integrity",
    "compliance", "idempotency", "observability",
})

SYSTEM_PROMPT = """\
You are a verification engineer performing invariant extraction.

Given the acceptance criteria, postconditions, preconditions, failure modes, and constitution,
extract ALL invariants that must ALWAYS hold true regardless of input.

Invariants come from 3 sources:
1. **AC text** — explicit "MUST NOT", "NEVER", "ALWAYS" statements in the acceptance criteria
2. **Constitution** — security_invariants, compliance rules, and verification standards
3. **Data model inference** — PII detection (passwords, SSN, tokens should never appear in responses),
   data classification (sensitive vs public fields), cross-tenant isolation

Each invariant MUST have:
- id: sequential, format INV-NNN (e.g., INV-001, INV-002)
- type: one of: security, performance, data_integrity, compliance, idempotency, observability
- rule: the invariant statement (what MUST always be true or MUST NEVER happen)
- source: where this invariant was derived from (e.g., "constitution", "ac_text", "data_model_inference")

You MUST also return a "questions" list with questions about invariants that need human confirmation.

{constitution_context}

RULES:
- IDs MUST be sequential and unique.
- Types MUST be from the allowed set.
- Every forbidden_field from postconditions MUST produce a security invariant.
- Constitution security_invariants MUST all be included.
- Do not include commentary outside the JSON.

Respond with ONLY this JSON structure:
{{
  "invariants": [
    {{"id": "INV-001", "type": "security", "rule": "Response MUST NOT contain password field", "source": "constitution"}}
  ],
  "questions": ["Are there any additional PII fields that should never be exposed?"]
}}"""


def _build_constitution_context(constitution: dict) -> str:
    """Load what Phase 5 needs — security invariants + verification standards."""
    if not constitution:
        return "No project constitution provided."
    parts = []
    security = (
        constitution.get("verification_standards", {})
        .get("security_invariants", [])
    )
    if security:
        parts.append("Security invariants from constitution:\n    - " + "\n    - ".join(security))
    project = constitution.get("project", {})
    if project:
        parts.append(f"Framework: {project.get('framework', 'unknown')}, Language: {project.get('language', 'unknown')}")
    return "Project context:\n  " + "\n  ".join(parts) if parts else "No project constitution provided."


def run_phase5(
    context: VerificationContext,
    llm: LLMClient,
    feedback: str | None = None,
    max_retries: int = 2,
) -> list[dict]:
    """Run Phase 5: extract invariants interactively."""
    system = SYSTEM_PROMPT.format(
        constitution_context=_build_constitution_context(context.constitution)
    )

    # Build user message from context
    user_parts = []
    user_parts.append("Acceptance Criteria:")
    for ac in context.raw_acceptance_criteria:
        user_parts.append(f"  [{ac['index']}] {ac['text']}")

    if context.postconditions:
        user_parts.append("\nPostconditions:")
        for pc in context.postconditions:
            user_parts.append(f"  AC[{pc.get('ac_index')}]: status={pc.get('status')}, forbidden_fields={pc.get('forbidden_fields', [])}")

    if context.preconditions:
        user_parts.append("\nPreconditions:")
        for pre in context.preconditions:
            user_parts.append(f"  {pre['id']}: {pre['description']} [{pre['category']}]")

    if context.failure_modes:
        user_parts.append(f"\nFailure Modes: {len(context.failure_modes)} enumerated")

    user_message = "\n".join(user_parts)

    # Multi-turn revision with feedback
    if feedback and context.invariants:
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": json.dumps({"invariants": context.invariants}, indent=2)},
            {"role": "user", "content": f"Developer feedback: {feedback}\n\nPlease revise your invariants based on this feedback. Respond with the complete updated JSON."},
        ]
        response = llm.chat_multi(system, messages, response_format="json")
        invariants = response.get("invariants", []) if isinstance(response, dict) else []
        context.invariants = invariants
        return invariants

    for attempt in range(max_retries + 1):
        response = llm.chat(system, user_message, response_format="json")
        invariants = response.get("invariants", []) if isinstance(response, dict) else []

        is_valid, errors = validate_invariants(invariants)
        if is_valid:
            context.invariants = invariants
            return invariants

        if attempt < max_retries:
            user_message += (
                f"\n\nValidation errors:\n" + "\n".join(f"- {e}" for e in errors)
                + "\n\nPlease fix and try again."
            )

    context.invariants = invariants
    return invariants
