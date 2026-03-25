"""LLM Client — wraps Anthropic SDK with mock mode for testing."""

from __future__ import annotations

import json
import os
import re
from typing import Union

import anthropic


# ------------------------------------------------------------------
# Dynamic mock helpers — produce context-aware responses
# ------------------------------------------------------------------


def _dynamic_classify(system_prompt: str, user_message: str = "") -> dict:
    """Produce multi-AC classifications from the user message context."""
    # Count ACs from the user message (lines like [0], [1], [2])
    ac_matches = re.findall(r"\[(\d+)\]", user_message)
    ac_indices = [int(m) for m in ac_matches] if ac_matches else [0]

    type_hints = {
        "401": "security_invariant",
        "auth": "security_invariant",
        "security": "security_invariant",
        "internal": "security_invariant",
        "expose": "security_invariant",
        "never": "security_invariant",
        "performance": "performance_sla",
        "latency": "performance_sla",
    }

    classifications = []
    for idx in ac_indices:
        # Find the text for this AC in the user message
        pattern = rf"\[{idx}\]\s+(.+?)(?:\n|$)"
        match = re.search(pattern, user_message)
        ac_text = match.group(1).strip().lower() if match else ""

        # Determine type from AC text
        req_type = "api_behavior"
        for hint, hint_type in type_hints.items():
            if hint in ac_text:
                req_type = hint_type
                break

        # Determine interface for api_behavior
        interface = {}
        if req_type == "api_behavior":
            method_match = re.search(r"(GET|POST|PUT|DELETE|PATCH)", ac_text, re.IGNORECASE)
            path_match = re.search(r"(/api/[^\s,]+|/\w+/v\d+/[^\s,]+)", ac_text)
            interface = {
                "method": method_match.group(1).upper() if method_match else "GET",
                "path": path_match.group(1) if path_match else "/api/v1/resource",
            }

        clf = {
            "ac_index": idx,
            "type": req_type,
            "actor": "authenticated_user",
        }
        if interface:
            clf["interface"] = interface

        classifications.append(clf)

    return {
        "classifications": classifications,
        "questions": ["Does this endpoint require any specific role beyond authentication?"],
    }


def _dynamic_postconditions(system_prompt: str, user_message: str = "") -> dict:
    """Produce postconditions for each api_behavior AC."""
    # We don't have direct access to the context here, so provide a reasonable default
    return {
        "postconditions": [
            {
                "ac_index": 0,
                "status": 200,
                "content_type": "application/json",
                "schema": {
                    "id": {"type": "integer", "required": True},
                    "name": {"type": "string", "required": True},
                    "breed": {"type": "string", "required": True},
                    "age": {"type": "integer", "required": False},
                },
                "constraints": ["response.id == path.id"],
                "forbidden_fields": ["password", "internalId", "ssn"],
            }
        ],
        "questions": ["Are there any nullable fields in the response?"],
    }


# Default mock responses keyed by a unique phrase from the system prompt.
# Order matters — first match wins, so use distinctive phrases.
# Values can be dicts (static) or callables (dynamic).
_MOCK_RESPONSES: dict = {
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
                "description": "Resource not found",
                "violates": "PRE-002",
                "status": 404,
                "body": {"error": "not_found", "message": "Resource not found"},
            },
        ],
        "questions": [
            "Should deleted resources return 404 or 410? Returning different codes leaks existence."
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
                "description": "Resource referenced by path exists",
                "formal": "db.resource.exists(path.id) == true",
                "category": "data_existence",
            },
            {
                "id": "PRE-003",
                "description": "User has access to the resource",
                "formal": "resource.owner == jwt.sub OR jwt.role == 'admin'",
                "category": "authorization",
            },
        ],
        "questions": ["Does the JWT need specific roles or scopes?"],
    },
    "defining postconditions": _dynamic_postconditions,
    "classify acceptance criteria": _dynamic_classify,
    "cucumber": {
        "feature_content": """@DEV-17 @REQ-001
Feature: Dog CRUD API verification

  @REQ-001.success
  Scenario: Successfully retrieve a dog by ID
    Given the API is running
    And a valid JWT token is available
    And a dog exists with ID 1
    When I send a GET request to "/api/v1/dogs/1" with auth
    Then the response status should be 200
    And the response should contain "name"
    And the response should contain "breed"
    And the response should not contain "password"
    And the response should not contain "internalId"

  @REQ-001.FAIL-001
  Scenario: Reject request without auth token
    Given the API is running
    When I send a GET request to "/api/v1/dogs/1" without auth
    Then the response status should be 401
    And the response should contain "unauthorized"

  @REQ-001.FAIL-002
  Scenario: Reject request with expired token
    Given the API is running
    And an expired JWT token is available
    When I send a GET request to "/api/v1/dogs/1" with auth
    Then the response status should be 401

  @REQ-001.FAIL-003
  Scenario: Return 404 for non-existent dog
    Given the API is running
    And a valid JWT token is available
    When I send a GET request to "/api/v1/dogs/99999" with auth
    Then the response status should be 404

  @REQ-001.INV-001
  Scenario: Response never exposes forbidden fields
    Given the API is running
    And a valid JWT token is available
    And a dog exists with ID 1
    When I send a GET request to "/api/v1/dogs/1" with auth
    Then the response status should be 200
    And the response should not contain "password"
    And the response should not contain "internalId"
    And the response should not contain "ssn"
""",
        "step_definition_content": """package com.example.dogservice.steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import io.cucumber.spring.CucumberContextConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.*;
import static org.assertj.core.api.Assertions.assertThat;

@CucumberContextConfiguration
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class DEV17Steps {

    @LocalServerPort
    private int port;

    private final TestRestTemplate restTemplate = new TestRestTemplate();
    private ResponseEntity<String> response;
    private String authToken = null;
    private String baseUrl;

    @Given("the API is running")
    public void theApiIsRunning() {
        baseUrl = "http://localhost:" + port;
    }

    @Given("a valid JWT token is available")
    public void aValidJwtTokenIsAvailable() {
        authToken = "test-valid-token";
    }

    @Given("an expired JWT token is available")
    public void anExpiredJwtTokenIsAvailable() {
        authToken = "test-expired-token";
    }

    @Given("a dog exists with ID {int}")
    public void aDogExistsWithId(int id) {
        // Seed data or assume test data exists
    }

    @When("I send a GET request to {string} with auth")
    public void iSendGetRequestWithAuth(String path) {
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + authToken);
        HttpEntity<String> entity = new HttpEntity<>(headers);
        response = restTemplate.exchange(baseUrl + path, HttpMethod.GET, entity, String.class);
    }

    @When("I send a GET request to {string} without auth")
    public void iSendGetRequestWithoutAuth(String path) {
        response = restTemplate.getForEntity(baseUrl + path, String.class);
    }

    @Then("the response status should be {int}")
    public void theResponseStatusShouldBe(int status) {
        assertThat(response.getStatusCode().value()).isEqualTo(status);
    }

    @Then("the response should contain {string}")
    public void theResponseShouldContain(String field) {
        assertThat(response.getBody()).contains(field);
    }

    @Then("the response should not contain {string}")
    public void theResponseShouldNotContain(String field) {
        assertThat(response.getBody()).doesNotContain(field);
    }
}
""",
        "step_class_name": "DEV17Steps",
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
                api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
                timeout=120.0,
            )

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        response_format: str = "json",
        max_tokens: int = 4096,
    ) -> dict | str:
        """Send a single-turn message to Claude and return the response.

        Args:
            system_prompt: System-level instructions.
            user_message: The user's message / prompt content.
            response_format: "json" attempts JSON parsing of the response.
            max_tokens: Maximum tokens in the response.

        Returns:
            Parsed dict when response_format="json", raw string otherwise.
        """
        if self._mock:
            return self._mock_response(system_prompt, user_message)

        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
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
    def _mock_response(system_prompt: str, user_message: str = "") -> dict:
        """Return a predefined mock response based on keyword hints in the prompt.

        Supports both static dict responses and dynamic callables that receive
        the system prompt and user message for context-aware mock generation.
        """
        prompt_lower = system_prompt.lower()
        for hint, response in _MOCK_RESPONSES.items():
            if hint in prompt_lower:
                if callable(response):
                    return response(system_prompt, user_message)
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
