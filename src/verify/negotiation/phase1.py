"""Phase 1 Skill — Interface & Actor Discovery.

Classifies each AC by type, actor, and interface using the LLM.
Block Principle 3: constitutional rules, not suggestions.
"""

import json

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.validate import validate_classifications

SYSTEM_PROMPT = """\
You are a verification engineer. Your job is to classify acceptance criteria.

Given acceptance criteria from a Jira ticket, you MUST classify every single AC.

For EACH AC, return:
- ac_index: the index of the AC in the list
- type: MUST be one of: api_behavior, performance_sla, security_invariant, observability, compliance, data_constraint
- actor: MUST be one of: authenticated_user, admin, system, anonymous_user, api_client
- interface: for api_behavior types, MUST include HTTP method and endpoint path using the project's base path

You MUST also return a "questions" list — at least one clarifying question for any ambiguous classification. Return an empty list only if every classification is unambiguous.

{constitution_context}

RULES:
- Classify ALL ACs. Never skip one.
- Use ONLY the types and actors listed above. Do not invent new categories.
- For api_behavior, propose endpoints using the base path from project context.
- Do not include commentary or explanation outside the JSON.

Respond with ONLY this JSON structure:
{{
  "classifications": [
    {{"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user", "interface": {{"method": "GET", "path": "/api/v1/..."}}}}
  ],
  "questions": ["Does this endpoint require specific roles beyond basic authentication?"]
}}"""


def _build_constitution_context(constitution: dict) -> str:
    """Build phase-specific constitution context — only load what Phase 1 needs."""
    if not constitution:
        return "No project constitution provided."
    parts = []
    project = constitution.get("project", {})
    if project:
        parts.append(f"Framework: {project.get('framework', 'unknown')}")
        parts.append(f"Language: {project.get('language', 'unknown')}")
    api = constitution.get("api", {})
    if api:
        parts.append(f"API base path: {api.get('base_path', '/api/v1')}")
        auth = api.get("auth", {})
        if auth:
            parts.append(f"Auth mechanism: {auth.get('mechanism', 'unknown')}")
            claims = auth.get("claims", [])
            if claims:
                parts.append(f"Required JWT claims: {', '.join(claims)}")
    testing = constitution.get("testing", {})
    if testing:
        parts.append(f"Test framework: {testing.get('unit_framework', 'unknown')}")
    # Include codebase scan results if available
    codebase = constitution.get("_codebase_index", "")
    if codebase:
        parts.append(f"\nCodebase scan results:\n{codebase}")
    return "Project context:\n  " + "\n  ".join(parts) if parts else "No project constitution provided."


def run_phase1(
    context: VerificationContext,
    llm: LLMClient,
    feedback: str | None = None,
    max_retries: int = 2,
) -> list[dict]:
    """Run Phase 1: classify each AC by type, actor, and interface.

    If feedback is provided, sends the previous output + developer feedback
    as a multi-turn conversation so the LLM can revise its output.
    """
    system = SYSTEM_PROMPT.format(
        constitution_context=_build_constitution_context(context.constitution)
    )
    ac_text = "\n".join(
        f"[{ac['index']}] {ac['text']}" for ac in context.raw_acceptance_criteria
    )
    user_message = f"Jira: {context.jira_key} — {context.jira_summary}\n\nAcceptance Criteria:\n{ac_text}"
    total_acs = len(context.raw_acceptance_criteria)

    # Multi-turn revision: send previous output + feedback
    if feedback and context.classifications:
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": json.dumps({"classifications": context.classifications}, indent=2)},
            {"role": "user", "content": f"Developer feedback: {feedback}\n\nPlease revise your classifications based on this feedback. Respond with the complete updated JSON."},
        ]
        response = llm.chat_multi(system, messages, response_format="json")
        classifications = response.get("classifications", []) if isinstance(response, dict) else []
        context.classifications = classifications
        return classifications

    # First run with validation retries
    for attempt in range(max_retries + 1):
        response = llm.chat(system, user_message, response_format="json")
        classifications = response.get("classifications", []) if isinstance(response, dict) else []

        is_valid, errors = validate_classifications(classifications, total_acs)
        if is_valid:
            context.classifications = classifications
            return classifications

        if attempt < max_retries:
            user_message += (
                f"\n\nYour previous output had validation errors:\n"
                + "\n".join(f"- {e}" for e in errors)
                + "\n\nPlease fix and try again."
            )

    context.classifications = classifications
    return classifications
