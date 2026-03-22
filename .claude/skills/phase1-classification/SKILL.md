---
name: phase1-classification
description: Classify Jira acceptance criteria by requirement type, actor, and API interface. Use when starting negotiation on a ticket's AC items, when the user mentions classifying requirements, or when beginning the verification spec process for a new story. This skill probes the Actors and Boundaries dimensions of ambiguity.
---

# Phase 1: Interface & Actor Discovery

Classify each acceptance criterion from a Jira ticket to determine what kind of verification it needs.

## Input

- `context.raw_acceptance_criteria` — list of AC items from Jira (each has `index`, `text`, `checked`)
- `context.constitution` — project conventions (framework, API patterns, auth mechanism)

## Task

For each AC item, determine:
- **type**: `api_behavior` | `performance_sla` | `security_invariant` | `observability` | `compliance` | `data_constraint`
- **actor**: `authenticated_user` | `admin` | `system` | `anonymous_user` | `api_client`
- **interface**: For `api_behavior` types only — propose HTTP method + endpoint path using the constitution's `api.base_path`

## Why these categories matter

The type determines the downstream verification strategy. An `api_behavior` flows through postconditions and failure modes into generated tests. A `security_invariant` becomes a cross-cutting invariant check. Getting this wrong means generating the wrong kind of spec — so when in doubt, ask a clarifying question rather than guessing.

## Output

```json
{
  "classifications": [
    {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user", "interface": {"method": "GET", "path": "/api/v1/users/me"}}
  ],
  "questions": ["Does this endpoint require admin-level access or just basic authentication?"]
}
```

## Constitutional rules

- Classify ALL ACs — never skip one, even if ambiguous
- Use ONLY the prescribed type and actor values — inventing new categories breaks downstream validation
- For `api_behavior`, always propose endpoints using the constitution's base path
- When the actor is unclear from the AC text, default to `authenticated_user` and add a clarifying question
- Include at least one question per ambiguous classification — the developer's confirmation is what makes the classification reliable

## Validation

After classification, run `verify.negotiation.validate.validate_classifications()` which checks:
- Every AC index is covered
- Types and actors are from the allowed set
- `api_behavior` items have an interface

For details on the output schema, see [SCHEMA.md](SCHEMA.md).
