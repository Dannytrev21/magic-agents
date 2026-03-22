---
name: phase4-failure-modes
description: Systematically enumerate failure modes for every precondition using FMEA-inspired analysis. Use after Phase 3 preconditions are defined. This is the most valuable phase — it surfaces edge cases and security-relevant error handling decisions the product owner likely never considered. Each failure mode becomes a test case.
---

# Phase 4: Failure Mode Enumeration

For each precondition, enumerate every way it can be violated. This is FMEA (Failure Mode and Effects Analysis) applied to API contracts.

## Input

- `context.preconditions` — Phase 3 output (each with id, category, formal expression)
- `context.constitution` — especially `api.error_format` and `api.common_status_codes`

## Task

For each precondition, consider subcategories based on its category:

| Category | Subcategories to consider |
|----------|--------------------------|
| authentication | missing token, expired, malformed, wrong issuer, revoked |
| authorization | missing role, insufficient scope, wrong tenant |
| data_existence | never existed, soft-deleted, hard-deleted |
| data_state | inactive, suspended, pending, locked |
| rate_limit | per-user exceeded, global exceeded |
| system_health | dependency down, timeout, connection refused |

Not every subcategory applies to every precondition — use judgment. But err on the side of including too many rather than too few. The developer can trim, but they can't add what they don't know about.

## Security decisions to surface

These are questions where the answer has security implications:
- **404 vs 410**: Should deleted resources return "not found" or "gone"? 410 leaks that the resource once existed.
- **401 vs 403**: Should unauthorized access to a valid resource differ from access to a nonexistent one? Different codes leak resource existence.
- **Error message specificity**: Should "invalid token" distinguish between expired, malformed, and revoked? Specific messages help attackers enumerate token states.

Always surface these as clarifying questions — the developer decides, not the AI.

## Output

```json
{
  "failure_modes": [
    {"id": "FAIL-001", "description": "No auth token provided", "violates": "PRE-001", "status": 401, "body": {"error": "unauthorized", "message": "Bearer token required"}}
  ],
  "questions": ["Should soft-deleted users return 404 or 410? 410 leaks that an account once existed."]
}
```

## Constitutional rules

- Every precondition must have at least one failure mode
- IDs must be sequential: FAIL-001, FAIL-002, etc.
- The `violates` field must reference an existing precondition ID — orphaned failure modes break traceability
- Status must be a numeric HTTP status code
- Error response body should follow the project's standard error format if defined in the constitution
- Always ask about security-relevant status code decisions — don't assume

## Validation

Run `verify.negotiation.validate.validate_failure_modes()` to check IDs, status codes, and precondition references.
