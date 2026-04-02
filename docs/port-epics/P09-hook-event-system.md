# Epic P9: Hook & Event System

**Priority:** 9 (Medium-Low)
**Status:** Done
**Ported From:** `claw-code` hook system (pre/post-command hooks, file access monitoring hooks, background task hooks)
**Integration Target:** `src/verify/observability.py`, `src/verify/negotiation/harness.py`

## Rationale

magic-agents has `observability.py` for timestamped event logging, but no mechanism for external systems to register callbacks at lifecycle points. claw-code supports pre/post-command hooks that trigger custom actions. This epic adds hook registration at phase boundaries — e.g., send a Slack notification when a phase completes, trigger a CI pipeline when specs are compiled, or log to an external monitoring system when budget thresholds are crossed.

---

## Story P9.1: Hook Registry with Lifecycle Points

### EARS Requirement

> The system **shall** maintain a `HookRegistry` where hooks can be registered for lifecycle points: `pre_phase`, `post_phase`, `pre_dispatch`, `post_dispatch`, `pre_evaluation`, `post_evaluation`, `checkpoint_saved`, and `session_ended`.

### Design by Contract

**Preconditions:**
- Each hook is a callable with signature `(event: HookEvent) -> None`.
- Lifecycle point names are from a closed enum.

**Postconditions:**
- `HookRegistry.register(lifecycle_point, hook_fn)` adds the hook.
- Multiple hooks per lifecycle point are executed in registration order.
- `HookRegistry.fire(lifecycle_point, event)` invokes all registered hooks.
- Hook exceptions are caught and logged; remaining hooks still execute.

**Invariants:**
- Hook execution never blocks the main pipeline.
- The registry is append-only.
- `HookEvent` contains: `lifecycle_point`, `timestamp`, `session_id`, `phase_name`, `data`.

### Acceptance Criteria

- [x]`HookRegistry` with `register()` and `fire()` methods.
- [x]`HookEvent` dataclass with all listed fields.
- [x]Multiple hooks per point executed in order.
- [x]Hook exceptions caught and logged without pipeline interruption.

### How to Test

```python
def test_register_and_fire():
    registry = HookRegistry()
    events = []
    registry.register("post_phase", lambda e: events.append(e))
    registry.fire("post_phase", HookEvent(lifecycle_point="post_phase", session_id="s1", phase_name="phase_1"))
    assert len(events) == 1

def test_multiple_hooks_order():
    registry = HookRegistry()
    order = []
    registry.register("post_phase", lambda e: order.append("a"))
    registry.register("post_phase", lambda e: order.append("b"))
    registry.fire("post_phase", HookEvent(...))
    assert order == ["a", "b"]

def test_hook_failure_isolated(caplog):
    registry = HookRegistry()
    results = []
    registry.register("post_phase", lambda e: 1/0)
    registry.register("post_phase", lambda e: results.append("ok"))
    registry.fire("post_phase", HookEvent(...))
    assert results == ["ok"]
```

---

## Story P9.2: Integrate Hooks into NegotiationHarness

### EARS Requirement

> **When** the `NegotiationHarness` enters or exits a phase, the system **shall** fire `pre_phase` and `post_phase` hooks, and **when** the harness saves a checkpoint, the system **shall** fire the `checkpoint_saved` hook.

### Design by Contract

**Preconditions:**
- The `NegotiationHarness` has a reference to the session's `HookRegistry`.

**Postconditions:**
- `pre_phase` fires before `run_phase_N()` with `phase_name` and `phase_index`.
- `post_phase` fires after phase completes with `phase_name`, `status`, and `duration_seconds`.
- `checkpoint_saved` fires after `save_checkpoint()` with the checkpoint path.

**Invariants:**
- Every `pre_phase` has a corresponding `post_phase` (even on failure).
- Hook execution overhead is < 100ms per lifecycle point.

### Acceptance Criteria

- [x]`NegotiationHarness.__init__` accepts an optional `HookRegistry`.
- [x]`pre_phase` and `post_phase` fire at correct times.
- [x]`checkpoint_saved` fires after each checkpoint save.
- [x]Hook data includes phase name, status, and timing.

### How to Test

```python
def test_hooks_fire_during_negotiation():
    events = []
    registry = HookRegistry()
    registry.register("pre_phase", lambda e: events.append(("pre", e.data["phase_name"])))
    registry.register("post_phase", lambda e: events.append(("post", e.data["phase_name"])))
    harness = NegotiationHarness(context, hooks=registry)
    harness.run_current_phase(llm)
    assert ("pre", "phase_1") in events
    assert ("post", "phase_1") in events
```

---

## Story P9.3: Configurable Hooks via Constitution

### EARS Requirement

> **Where** a `constitution.yaml` defines a `hooks` section mapping lifecycle points to shell commands, the system **shall** register shell-execution hooks that run those commands when the corresponding lifecycle point fires.

### Design by Contract

**Preconditions:**
- `constitution.yaml` has an optional `hooks` section.
- Shell commands receive context via environment variables: `HOOK_EVENT`, `HOOK_SESSION_ID`, `HOOK_PHASE`, `HOOK_STATUS`.

**Postconditions:**
- Each constitution hook is registered as a shell-execution hook.
- Commands run via `subprocess.run()` with configurable timeout (default: 30s).
- stdout/stderr captured and logged.
- Timeout/failure logged at WARNING level.

**Invariants:**
- Shell hooks run in the magic-agents process working directory.
- Shell hook failures never abort the pipeline.
- Hooks registered during bootstrap before negotiation starts.

### Acceptance Criteria

- [x]Constitution schema supports `hooks` section.
- [x]Shell commands executed with environment variables.
- [x]Timeout and failure handled gracefully.
- [x]Hooks registered during bootstrap.

### How to Test

```python
def test_shell_hook_executes(tmp_path):
    marker = tmp_path / "hook_fired.txt"
    constitution = {"hooks": {"post_phase": f"touch {marker}"}}
    registry = HookRegistry.from_constitution(constitution)
    registry.fire("post_phase", HookEvent(...))
    assert marker.exists()

def test_shell_hook_timeout(caplog):
    constitution = {"hooks": {"post_phase": "sleep 60"}}
    registry = HookRegistry.from_constitution(constitution, timeout=1)
    registry.fire("post_phase", HookEvent(...))
    assert "timeout" in caplog.text.lower()
```
