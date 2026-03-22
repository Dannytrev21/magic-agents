"""LLM Client — wraps Anthropic SDK with mock mode for testing."""

import json
import os

import anthropic


# Default mock responses keyed by a unique phrase from the system prompt.
# Order matters — first match wins, so use distinctive phrases.
_MOCK_RESPONSES: dict[str, dict] = {
    "failure mode enumeration": {
        "failure_modes": [
            {
                "id": "FAIL-001",
                "description": "No auth token provided",
                "violates": "PRE-001",
                "status": 401,
                "body": {"error": "unauthorized", "message": "Bearer token required"},
            },
            {
                "id": "FAIL-002",
                "description": "Auth token expired",
                "violates": "PRE-001",
                "status": 401,
                "body": {"error": "unauthorized", "message": "Token expired"},
            },
            {
                "id": "FAIL-003",
                "description": "User not found",
                "violates": "PRE-002",
                "status": 404,
                "body": {"error": "not_found", "message": "User not found"},
            },
        ],
        "questions": [
            "Should deleted users return 404 or 410? Returning different codes leaks account existence."
        ],
    },
    "design by contract": {
        "preconditions": [
            {
                "id": "PRE-001",
                "description": "Valid JWT bearer token is present",
                "formal": "jwt != null AND jwt.exp > now()",
                "category": "authentication",
            },
            {
                "id": "PRE-002",
                "description": "User referenced by JWT exists",
                "formal": "db.users.exists(jwt.sub) == true",
                "category": "data_existence",
            },
            {
                "id": "PRE-003",
                "description": "User account is active",
                "formal": "db.users.find(jwt.sub).status == 'active'",
                "category": "data_state",
            },
        ],
        "questions": ["Does the JWT need specific roles or scopes?"],
    },
    "defining postconditions": {
        "postconditions": [
            {
                "ac_index": 0,
                "status": 200,
                "content_type": "application/json",
                "schema": {
                    "id": {"type": "string", "required": True},
                    "email": {"type": "string", "required": True},
                    "displayName": {"type": "string", "required": True},
                },
                "constraints": ["response.id == jwt.sub"],
                "forbidden_fields": ["password", "ssn"],
            }
        ],
        "questions": ["Are there any nullable fields in the response?"],
    },
    "classify acceptance criteria": {
        "classifications": [
            {
                "ac_index": 0,
                "type": "api_behavior",
                "actor": "authenticated_user",
                "interface": {"method": "GET", "path": "/api/v1/users/me"},
            }
        ],
        "questions": ["Does this endpoint require any specific role beyond authentication?"],
    },
}

# Fallback when no hint matches
_MOCK_DEFAULT = {"result": "mock response", "status": "ok"}


class LLMClient:
    """Client for Claude API with mock mode for testing."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self.model = model
        self._mock = os.environ.get("LLM_MOCK", "").lower() == "true"
        if not self._mock:
            self._client = anthropic.Anthropic(
                api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
            )

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        response_format: str = "json",
    ) -> dict | str:
        """Send a single-turn message to Claude and return the response.

        Args:
            system_prompt: System-level instructions.
            user_message: The user's message / prompt content.
            response_format: "json" attempts JSON parsing of the response.

        Returns:
            Parsed dict when response_format="json", raw string otherwise.
        """
        if self._mock:
            return self._mock_response(system_prompt)

        message = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        text = message.content[0].text

        if response_format == "json":
            return self._parse_json(text)
        return text

    def chat_multi(
        self,
        system_prompt: str,
        messages: list[dict],
        response_format: str = "json",
    ) -> dict | str:
        """Send a multi-turn conversation to Claude.

        Args:
            system_prompt: System-level instructions.
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts.
            response_format: "json" attempts JSON parsing of the response.

        Returns:
            Parsed dict when response_format="json", raw string otherwise.
        """
        if self._mock:
            return self._mock_response(system_prompt)

        message = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )

        text = message.content[0].text

        if response_format == "json":
            return self._parse_json(text)
        return text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_response(system_prompt: str) -> dict:
        """Return a predefined mock response based on keyword hints in the prompt."""
        prompt_lower = system_prompt.lower()
        for hint, response in _MOCK_RESPONSES.items():
            if hint in prompt_lower:
                return response
        return dict(_MOCK_DEFAULT)

    @staticmethod
    def _parse_json(text: str) -> dict | str:
        """Extract and parse JSON from the response text."""
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from ```json ... ``` fences
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

        # Try extracting from { ... } or [ ... ]
        for open_char, close_char in [("{", "}"), ("[", "]")]:
            if open_char in text:
                start = text.index(open_char)
                end = text.rindex(close_char) + 1
                try:
                    return json.loads(text[start:end])
                except (json.JSONDecodeError, ValueError):
                    pass

        # Give up — return raw text
        return text
