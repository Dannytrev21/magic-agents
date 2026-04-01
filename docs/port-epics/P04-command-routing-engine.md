# Epic P4: Command Routing Engine

**Priority:** 4 (Medium-High)
**Status:** Done
**Ported From:** `claw-code/src/runtime.py` (PortRuntime.route_prompt, tokenized matching, scoring), `claw-code/src/commands.py` (command registry, search, filtering)
**Integration Target:** `src/verify/negotiation/cli.py`, `src/verify/negotiation/web.py`

## Rationale

magic-agents dispatched phases and commands through hardcoded `if/elif` chains in `web.py` and `cli.py`. Adding a new phase, skill, or CLI command required modifying these files directly. claw-code's `PortRuntime.route_prompt()` demonstrates a tokenized matching system where user prompts are scored against a registry of commands/tools, enabling dynamic dispatch without code changes. This epic adds a command registry and tokenized prompt routing so new phases, skills, and CLI commands can be discovered and dispatched dynamically.

---

## Story P4.1: Command Registry with Metadata

### EARS Requirement

> The system **shall** maintain a `CommandRegistry` that maps command names to `CommandDescriptor` objects containing `name`, `description`, `aliases`, `category` (negotiation/verification/pipeline/admin), and a `handler` callable.

### Design by Contract

**Preconditions:**
- Each command has a unique `name` (lowercase, hyphenated).
- The `handler` callable accepts `(args: dict) -> CommandResult`.

**Postconditions:**
- `CommandRegistry.register(descriptor, handler)` adds the command.
- `CommandRegistry.get(name)` returns the `(CommandDescriptor, handler)` tuple or `None`.
- `CommandRegistry.list(category=None)` returns all descriptors, optionally filtered.
- Duplicate `name` registration raises `ValueError`.

**Invariants:**
- Command names are case-insensitive for lookup.
- The registry is append-only during normal operation.

### Acceptance Criteria

- [x] `CommandDescriptor` and `CommandResult` dataclasses are defined.
- [x] `CommandRegistry` supports `register`, `get`, `list`, and `find` methods.
- [x] Existing CLI commands are registered at import time.
- [x] Duplicate names raise `ValueError`.

### How to Test

```python
def test_register_and_get():
    registry = CommandRegistry()
    desc = CommandDescriptor(name="run-phase", description="Run negotiation phase", ...)
    registry.register(desc, handler=mock_handler)
    assert registry.get("run-phase") is not None

def test_case_insensitive():
    registry = CommandRegistry()
    registry.register(CommandDescriptor(name="Run-Phase", ...), mock_handler)
    assert registry.get("run-phase") is not None
    assert registry.get("RUN-PHASE") is not None

def test_list_by_category():
    registry = CommandRegistry()
    registry.register(CommandDescriptor(name="a", category="negotiation", ...), mock_handler)
    registry.register(CommandDescriptor(name="b", category="pipeline", ...), mock_handler)
    assert len(registry.list(category="negotiation")) == 1
```

---

## Story P4.2: Tokenized Prompt Routing

### EARS Requirement

> **When** a user submits a free-text prompt, the system **shall** tokenize the prompt, score it against all registered commands using token overlap with `name`, `description`, and `aliases`, and return the top-N matches sorted by descending score.

### Design by Contract

**Preconditions:**
- At least one command is registered.
- The prompt is a non-empty string.

**Postconditions:**
- Prompt is split into lowercase tokens (splitting on whitespace, `/`, `-`).
- Each command scored by token overlap with its descriptor fields.
- Results returned as `list[tuple[CommandDescriptor, int]]`, sorted descending.
- Zero-score commands excluded.

**Invariants:**
- Routing is deterministic: same prompt + registry = same results.
- Routing is read-only: never executes commands or mutates state.

### Acceptance Criteria

- [x] `route_prompt(prompt, limit=5)` is implemented.
- [x] Tokenization splits on whitespace, `/`, and `-`.
- [x] Zero-score commands excluded from results.
- [x] Results sorted by descending score, then alphabetically.

### How to Test

```python
def test_route_prompt():
    registry = CommandRegistry()
    registry.register(CommandDescriptor(name="run-phase", description="Execute negotiation phase"), ...)
    results = route_prompt("run the next phase", registry)
    assert results[0][0].name == "run-phase"

def test_route_no_match():
    results = route_prompt("completely unrelated", registry)
    assert results == []
```

---

## Story P4.3: Dynamic Command Discovery in Web UI

### EARS Requirement

> The system **shall** expose a `GET /api/commands` endpoint returning all registered commands grouped by category, and a `POST /api/commands/{name}` endpoint that executes the named command.

### Design by Contract

**Preconditions:**
- The FastAPI app is running.
- At least one command is registered.

**Postconditions:**
- `GET /api/commands` returns JSON with category keys and command descriptor arrays.
- `POST /api/commands/{name}` executes the handler and returns `CommandResult`.
- Unknown commands return 404.

**Invariants:**
- `GET` is read-only.
- `POST` only executes registered commands — no eval.

### Acceptance Criteria

- [x] `GET /api/commands` returns 200 with grouped commands.
- [x] `POST /api/commands/run-phase` executes the handler.
- [x] `POST /api/commands/nonexistent` returns 404.
- [x] Results include `status`, `message`, and optional `data`.

### How to Test

```python
def test_list_commands(client):
    resp = client.get("/api/commands")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)

def test_execute_command(client):
    resp = client.post("/api/commands/run-phase", json={"phase": "phase_1"})
    assert resp.status_code == 200
    assert "status" in resp.json()

def test_command_not_found(client):
    resp = client.post("/api/commands/nonexistent", json={})
    assert resp.status_code == 404
```
