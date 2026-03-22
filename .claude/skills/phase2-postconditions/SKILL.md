---
name: phase2-postconditions
description: Define happy-path contracts (postconditions) for API behavior requirements. Use after Phase 1 classification, when the user wants to specify exact success responses including status codes, response schemas, field constraints, and forbidden fields. This skill establishes what "correct" means before any tests are written.
---

# Phase 2: Happy Path Contract

For each `api_behavior` classification, define the exact success response — the postcondition that must hold when everything works correctly.

## Input

- `context.classifications` — Phase 1 output (only `api_behavior` types flow here)
- `context.constitution` — project conventions, especially `api.error_format` and `verification_standards.security_invariants`

## Task

For each `api_behavior` AC, propose:
- **status**: numeric HTTP success code (200, 201, etc.)
- **content_type**: response content type
- **schema**: response body fields with types and required flags
- **constraints**: relationships between response fields and request context
- **forbidden_fields**: fields that must never appear in the response

## Why constraints matter

Constraints like "response.id must equal jwt.sub" prevent cross-user data leakage. Without them, a test might verify the response has an `id` field without checking it belongs to the right user. Every constraint becomes a test assertion, so being explicit here directly improves test quality.

## Output

```json
{
  "postconditions": [
    {
      "ac_index": 0,
      "status": 200,
      "content_type": "application/json",
      "schema": {"id": {"type": "string", "required": true}},
      "constraints": ["response.id == jwt.sub"],
      "forbidden_fields": ["password", "password_hash"]
    }
  ],
  "questions": ["Is the avatar field nullable or always present?"]
}
```

## Constitutional rules

- Every `api_behavior` AC must have exactly one postcondition
- Always include `password`, `password_hash`, and `token` as forbidden fields unless the constitution explicitly allows them
- Constraints must link response fields to request context explicitly — "response.id matches user" is too vague; "response.id == jwt.sub" is specific
- Ask about nullable fields and computed fields — these are the most common source of test flakiness

## Validation

Run `verify.negotiation.validate.validate_postconditions()` which checks status codes are valid integers and all `api_behavior` ACs have postconditions.

For the full output schema, see [SCHEMA.md](SCHEMA.md).
