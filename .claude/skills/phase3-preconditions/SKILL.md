---
name: phase3-preconditions
description: Identify and formalize preconditions for API endpoints using Design by Contract. Use after Phase 2 postconditions are defined, when determining what must be true for the happy path to succeed. Each precondition becomes a failure mode in Phase 4, so thoroughness here directly determines test coverage.
---

# Phase 3: Precondition Formalization

For each postcondition, identify every precondition that must hold for the happy path to succeed. Uses the Design by Contract technique.

## Input

- `context.postconditions` — Phase 2 output (happy-path contracts)
- `context.constitution` — especially `api.auth.mechanism` and `api.auth.claims`

## Task

For each postcondition, identify preconditions across these categories:
- **authentication**: token present, valid, not expired
- **authorization**: correct role, scope, or ownership
- **data_existence**: referenced records exist
- **data_state**: records are in the expected state (active, not deleted)
- **rate_limit**: within rate limits
- **system_health**: dependencies available

Each precondition gets a semi-formal expression that's precise enough for a human to verify and a test generator to translate into a setup fixture.

## Formal expression patterns

```
jwt != null AND jwt.exp > now()
db.users.exists(jwt.sub) == true
db.users.find(jwt.sub).status == 'active'
request.headers['Authorization'].startsWith('Bearer ')
rate_limiter.check(user_id, 'endpoint') == allowed
```

These aren't executable code — they're precise enough to be unambiguous while remaining language-agnostic.

## Output

```json
{
  "preconditions": [
    {"id": "PRE-001", "description": "Valid JWT bearer token is present", "formal": "jwt != null AND jwt.exp > now()", "category": "authentication"}
  ],
  "questions": ["Does the JWT need specific roles or scopes beyond basic authentication?"]
}
```

## Constitutional rules

- Every postcondition must have at least one precondition (if something can succeed, something can also fail)
- IDs must be sequential: PRE-001, PRE-002, etc.
- Categories must be from the prescribed set — this determines how Phase 4 enumerates failure subcategories
- The formal expression must be non-empty and use the `entity.field operator value` pattern
- Ask about implicit preconditions the developer may have overlooked (rate limits, soft-delete states, multi-tenancy)

## Validation

Run `verify.negotiation.validate.validate_preconditions()` to check IDs, categories, and formal expressions.
