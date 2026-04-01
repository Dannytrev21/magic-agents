# P05 — Permission & Access Control

## Goal
Port the permission and access control system from claw-code into magic-agents. This gives operators fine-grained control over which verification skills and tools can be dispatched.

## Source Reference
- `claw-code/src/permissions.py` — `ToolPermissionContext` frozen dataclass
- `claw-code/src/models.py` — `PermissionDenial` frozen dataclass
- `claw-code/src/tools.py` — `filter_tools_by_permission_context()`
- `claw-code/src/runtime.py` — `_infer_permission_denials()`
- `claw-code/src/query_engine.py` — denial tracking in `TurnResult`

## Stories

### P5.1 — ToolPermissionContext & PermissionDenial Data Models
Create immutable data models for permission rules and denial events.

**AC:**
- `ToolPermissionContext` is a frozen dataclass with `deny_names: frozenset[str]` and `deny_prefixes: tuple[str, ...]`
- Factory method `from_iterables(deny_names, deny_prefixes)` constructs instances
- `blocks(tool_name)` performs case-insensitive matching against names and prefixes
- `PermissionDenial` is a frozen dataclass with `tool_name: str` and `reason: str`

### P5.2 — Skill Filtering by Permission Context
Apply permission context to the skill dispatch pipeline.

**AC:**
- `filter_skills_by_permission(skills, permission_context)` returns only allowed skills
- `dispatch_skills()` accepts optional `permission_context` and skips blocked skills
- Blocked skills produce `PermissionDenial` entries with explanatory reasons

### P5.3 — Permission-Aware Web Endpoints
Expose permission controls via the web API.

**AC:**
- `POST /api/permissions` sets the active permission context for the session
- `GET /api/permissions` returns the current permission context
- `GET /api/permissions/denials` returns all denial events for the session
- Blocked dispatches are tracked in session state

### P5.4 — Constitution-Driven Permission Defaults
Allow the constitution YAML to specify default permission rules.

**AC:**
- `constitution.yaml` supports `permissions.deny_skills` and `permissions.deny_prefixes` fields
- Default permission context is loaded from constitution when a session starts
- Operator-set permissions override constitution defaults
