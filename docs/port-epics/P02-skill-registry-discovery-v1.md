# Feature Spec: Skill Registry & Capability Discovery

**Feature ID:** `P02-v1`
**Source Inspiration:** `claw-code/src/tools.py`, `claw-code/src/execution_registry.py`
**Target Surface:** `magic-agents/src/verify/skills/framework.py`, `magic-agents/src/verify/skills/*.py`, `magic-agents/src/verify/negotiation/web.py`

## Why This Feature

`magic-agents` already routes verification work by `skill` identifier, but the current registry is only a plain `dict[str, VerificationSkill]`. That is enough to dispatch happy-path generation, but it does not let the runtime answer basic contract questions:

- Which skills are installed?
- Which requirement types can each skill handle?
- Is a spec asking for a missing or incompatible skill?
- Can the web UI surface available verification capabilities?

`claw-code` solves the analogous problem with a richer registry and discovery surface. Porting that pattern is useful here because `magic-agents` already has deterministic routing and needs a deterministic capability contract to match it.

## Implementation Slice

This run implements one vertical slice of the feature:

1. Descriptor-backed skill registration
2. Search and filter over registered capabilities
3. Dispatch-time validation for missing or incompatible skills
4. Read-only web introspection via `GET /api/skills`

## EARS Requirements

### R1. Descriptor Registration

> The system **shall** associate every registered `VerificationSkill` with a typed `SkillDescriptor` containing `skill_id`, `name`, `description`, `input_types`, `output_format`, `framework`, and `version`.

### R2. Capability Discovery

> **When** a caller queries the skill registry by free-text search or by requirement type, the system **shall** return only the registered skills whose descriptors match the query.

### R3. Dispatch Validation

> **If** a spec references a skill that is not registered, or references a skill whose descriptor does not accept the requirement type, **then** the system **shall** reject dispatch with a structured `SkillDispatchError`.

### R4. Web Introspection

> The system **shall** expose a `GET /api/skills` endpoint that returns the current set of registered skill descriptors as JSON for UI and operator introspection.

## Design By Contract

### Contract A. Register Skill

**Preconditions**

- A skill instance or `VerificationSkill` subclass is supplied.
- The descriptor's `skill_id` is non-empty.
- The descriptor's `input_types` is non-empty.

**Postconditions**

- The skill is reachable in the registry by `skill_id`.
- The descriptor is stored alongside the registered skill.
- Duplicate `skill_id` registration raises `ValueError`.

**Invariants**

- Each `skill_id` maps to exactly one registered skill.
- Descriptor lookup and skill lookup stay synchronized for add/remove operations.
- Built-in skills remain auto-registered on import.

### Contract B. Discover Skills

**Preconditions**

- At least zero skills may be registered.
- Query text may be empty only for direct listing, not for filtered search.

**Postconditions**

- Free-text search matches `skill_id`, `name`, `description`, and `input_types`.
- Type filtering returns only descriptors whose `input_types` contain the requested requirement type or a wildcard capability.
- Results are returned in deterministic order.

**Invariants**

- Discovery is read-only.
- Search is case-insensitive.
- Search does not mutate registration state.

### Contract C. Validate Dispatch

**Preconditions**

- `spec.requirements[*].verification[*].skill` may reference any string.
- `spec.requirements[*].type` may be absent; if present, compatibility must be checked.

**Postconditions**

- Validation returns an empty error list when every referenced skill exists and is type-compatible.
- Validation returns one error per missing or incompatible binding.
- `dispatch_skills()` raises `SkillDispatchError` before writing any artifacts when validation fails.

**Invariants**

- Validation is exhaustive across the entire spec, not fail-fast on the first error.
- No files are written when validation fails.

### Contract D. List Skills Over HTTP

**Preconditions**

- The FastAPI app is running.

**Postconditions**

- `GET /api/skills` returns `200 OK`.
- Each item includes `skill_id`, `name`, `description`, `input_types`, `output_format`, `framework`, and `version`.
- Response order is stable by `skill_id`.

**Invariants**

- The endpoint is read-only.
- The endpoint reflects the same registry state used by dispatch.

## Red/Green Test Plan

### RED

- Add registry tests for descriptor exposure, duplicate registration rejection, search, type filtering, and dispatch validation.
- Add a web test asserting `/api/skills` returns descriptor objects.

### GREEN

- Introduce `SkillDescriptor`, a synchronized registry wrapper, search/filter helpers, and `SkillDispatchError`.
- Backfill built-in skill metadata for `PytestSkill` and `CucumberJavaSkill`.
- Add the `/api/skills` endpoint and ensure built-in skills are loaded before introspection or dispatch.

### REFACTOR

- Keep the public `SKILL_REGISTRY` dict-like so current tests and call sites continue to work.
- Centralize built-in skill loading so the registry behaves consistently in CLI, tests, and web runtime.
