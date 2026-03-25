"""Phase 7 Skill — EARS Formalization & Human Approval.

Synthesizes all outputs into EARS statements using 5 patterns:
1. UBIQUITOUS: The system SHALL... (Invariant test)
2. EVENT_DRIVEN: WHEN {trigger}, the system SHALL... (Happy path)
3. STATE_DRIVEN: WHILE {state}, the system SHALL... (Preconditioned behavior)
4. UNWANTED: IF {condition}, THEN the system SHALL... (Error handling)
5. OPTIONAL: WHERE {feature}, the system SHALL... (Feature-flagged)
"""

import json

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.validate import validate_ears_statements

VALID_EARS_PATTERNS = frozenset({
    "UBIQUITOUS", "EVENT_DRIVEN", "STATE_DRIVEN", "UNWANTED", "OPTIONAL",
})

SYSTEM_PROMPT = """\
You are a verification engineer performing EARS formalization.

EARS (Easy Approach to Requirements Syntax) patterns:
1. **UBIQUITOUS**: The system SHALL <action>. (Always true — invariants)
2. **EVENT_DRIVEN**: WHEN <trigger>, the system SHALL <action>. (Happy path responses)
3. **STATE_DRIVEN**: WHILE <state>, the system SHALL <action>. (Preconditioned behavior)
4. **UNWANTED**: IF <condition>, THEN the system SHALL <action>. (Error handling / failure modes)
5. **OPTIONAL**: WHERE <feature>, the system SHALL <action>. (Feature-flagged behavior)

Given the full negotiation context, produce an EARS statement for every:
- Postcondition → EVENT_DRIVEN
- Failure mode → UNWANTED
- Invariant → UBIQUITOUS
- Precondition → STATE_DRIVEN (if applicable)

Each EARS statement MUST have:
- id: sequential, format EARS-NNN (e.g., EARS-001)
- pattern: one of UBIQUITOUS, EVENT_DRIVEN, STATE_DRIVEN, UNWANTED, OPTIONAL
- statement: the complete EARS sentence using the pattern keywords
- traces_to: the spec ref this traces to (e.g., REQ-001.success, REQ-001.FAIL-001, REQ-001.INV-001)

{constitution_context}

RULES:
- Every postcondition MUST produce an EVENT_DRIVEN statement.
- Every failure mode MUST produce an UNWANTED statement.
- Every invariant MUST produce a UBIQUITOUS statement.
- IDs MUST be sequential.
- Patterns MUST be from the allowed set.
- Statements MUST use the correct EARS keywords (WHEN/SHALL, IF/THEN, WHILE/SHALL).

You MUST also return a "questions" list for any ambiguities in requirements.

Respond with ONLY this JSON structure:
{{
  "ears_statements": [
    {{"id": "EARS-001", "pattern": "EVENT_DRIVEN", "statement": "WHEN GET /api/v1/users/me is requested with valid auth THEN the system SHALL respond with 200", "traces_to": "REQ-001.success"}},
    {{"id": "EARS-002", "pattern": "UNWANTED", "statement": "IF no auth token is provided THEN the system SHALL respond with 401", "traces_to": "REQ-001.FAIL-001"}}
  ],
  "questions": []
}}"""


def _build_constitution_context(constitution: dict) -> str:
    """Load what Phase 7 needs — project context."""
    if not constitution:
        return "No project constitution provided."
    parts = []
    project = constitution.get("project", {})
    if project:
        parts.append(f"Framework: {project.get('framework', 'unknown')}, Language: {project.get('language', 'unknown')}")
    return "Project context:\n  " + "\n  ".join(parts) if parts else "No project constitution provided."


def run_phase7(
    context: VerificationContext,
    llm: LLMClient,
    feedback: str | None = None,
    max_retries: int = 2,
) -> list[dict]:
    """Run Phase 7: EARS formalization."""
    system = SYSTEM_PROMPT.format(
        constitution_context=_build_constitution_context(context.constitution)
    )

    # Build user message from full context
    user_parts = []
    user_parts.append(f"Story: {context.jira_key} — {context.jira_summary}")

    user_parts.append("\nPostconditions:")
    for pc in context.postconditions:
        iface = _find_interface(context, pc.get("ac_index"))
        method = iface.get("method", "?") if iface else "?"
        path = iface.get("path", "?") if iface else "?"
        user_parts.append(f"  AC[{pc.get('ac_index')}]: {method} {path} → status {pc.get('status')}")

    user_parts.append("\nFailure Modes:")
    for fm in context.failure_modes:
        user_parts.append(f"  {fm['id']}: {fm['description']} → status {fm.get('status')}")

    user_parts.append("\nInvariants:")
    for inv in context.invariants:
        user_parts.append(f"  {inv['id']}: {inv.get('rule', inv.get('description', ''))}")

    user_message = "\n".join(user_parts)

    # Multi-turn revision with feedback
    if feedback and context.ears_statements:
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": json.dumps({"ears_statements": context.ears_statements}, indent=2)},
            {"role": "user", "content": f"Developer feedback: {feedback}\n\nPlease revise based on this feedback. Respond with the complete updated JSON."},
        ]
        response = llm.chat_multi(system, messages, response_format="json")
        ears = response.get("ears_statements", []) if isinstance(response, dict) else []
        context.ears_statements = ears
        return ears

    for attempt in range(max_retries + 1):
        response = llm.chat(system, user_message, response_format="json")
        ears = response.get("ears_statements", []) if isinstance(response, dict) else []

        is_valid, errors = validate_ears_statements(ears)
        if is_valid:
            context.ears_statements = ears
            return ears

        if attempt < max_retries:
            user_message += (
                f"\n\nValidation errors:\n" + "\n".join(f"- {e}" for e in errors)
                + "\n\nPlease fix and try again."
            )

    context.ears_statements = ears
    return ears


def _find_interface(context: VerificationContext, ac_index: int) -> dict | None:
    """Find the interface dict for a given AC index from classifications."""
    for c in context.classifications:
        if c.get("ac_index") == ac_index and c.get("interface"):
            return c["interface"]
    return None
