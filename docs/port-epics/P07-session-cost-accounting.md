# Epic P7: Session Cost Accounting

**Priority:** 7 (Medium)
**Status:** Not Started
**Ported From:** `claw-code/src/session_store.py` (StoredSession with input/output token tracking), `claw-code/src/query_engine.py` (UsageSummary, total_usage tracking)
**Integration Target:** `src/verify/negotiation/checkpoint.py`, `src/verify/runtime.py`

## Rationale

magic-agents persists sessions via checkpoints but does not track token usage or cost across checkpoint saves and restores. When a negotiation session is resumed after a break, there is no way to know how many tokens were spent in prior phases. claw-code's `StoredSession` includes `input_tokens` and `output_tokens` fields that are persisted and restored. This epic extends checkpoints to include cost data.

---

## Story P7.1: Persist Token Usage in Checkpoints

### EARS Requirement

> **When** a checkpoint is saved, the system **shall** include the cumulative `input_tokens`, `output_tokens`, `api_calls`, and `wall_clock_seconds` from the `BackPressureController` in the checkpoint JSON.

### Design by Contract

**Preconditions:**
- The `BackPressureController` is associated with the session (from Epic P1).
- `save_checkpoint()` is called after a phase completes.

**Postconditions:**
- Checkpoint JSON includes a `usage` object with token and call counts.
- Existing checkpoint fields unchanged (backward compatible).
- Restoring a checkpoint restores the `BackPressureController` state.

**Invariants:**
- Token counts are monotonically increasing across successive saves.
- Old checkpoints without `usage` load without error (defaults to zeros).

### Acceptance Criteria

- [ ] `save_checkpoint()` serializes usage data from `BackPressureController`.
- [ ] `load_checkpoint()` restores usage data back to a controller.
- [ ] Old checkpoints backward-compatible.
- [ ] Round-trip: save → load → save produces identical usage data.

### How to Test

```python
def test_checkpoint_includes_usage(tmp_path):
    controller = BackPressureController()
    controller.api_calls = 5
    controller.tokens_used = 10000
    save_checkpoint(context, phase=3, backpressure=controller, directory=tmp_path)
    data = json.loads((tmp_path / "checkpoint_phase_3.json").read_text())
    assert data["usage"]["api_calls"] == 5

def test_old_checkpoint_backward_compat(tmp_path):
    (tmp_path / "checkpoint_phase_1.json").write_text('{"jira_key": "TEST-1"}')
    _, controller = load_checkpoint("TEST-1", directory=tmp_path)
    assert controller.api_calls == 0
```

---

## Story P7.2: Session Cost Summary Endpoint

### EARS Requirement

> The system **shall** expose a `GET /api/session/{session_id}/cost` endpoint returning cumulative token usage, per-phase breakdowns, estimated cost in USD, and budget utilization percentage.

### Design by Contract

**Preconditions:**
- A session exists with the given `session_id`.
- The session has a `BackPressureController` with recorded usage.

**Postconditions:**
- Response includes: `total_input_tokens`, `total_output_tokens`, `total_api_calls`, `estimated_cost_usd`, `budget_utilization_pct`, and `phases` array.
- `estimated_cost_usd` uses configurable per-token rates (default: $3/M input, $15/M output).
- `budget_utilization_pct` is `tokens_used / max_tokens * 100`.

**Invariants:**
- Cost estimation uses session-configured rates, not live API pricing.
- Endpoint is read-only and idempotent.

### Acceptance Criteria

- [ ] `GET /api/session/{id}/cost` returns 200 with cost summary.
- [ ] Per-phase breakdowns match `PhaseCostReport` entries from P1.
- [ ] `estimated_cost_usd` calculated correctly.
- [ ] `budget_utilization_pct` between 0 and 100+ (if over budget).

### How to Test

```python
def test_cost_endpoint(client):
    resp = client.get(f"/api/session/{session_id}/cost")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_input_tokens" in data
    assert "estimated_cost_usd" in data
    assert data["budget_utilization_pct"] >= 0
```

---

## Story P7.3: Cost Alerts via SSE Events

### EARS Requirement

> **When** token usage crosses a soft limit threshold, the system **shall** emit a `budget_warning` SSE event, and **when** usage crosses a hard limit, the system **shall** emit a `budget_exceeded` event, both with the current usage summary.

### Design by Contract

**Preconditions:**
- The `BackPressureController` has recorded a new API call.
- The session has an `EventEmitter` registered (from Epic P6).

**Postconditions:**
- `budget_warning` emitted when soft limits crossed.
- `budget_exceeded` emitted when hard limits crossed.
- Events emitted at most once per threshold crossing (deduplicated).

**Invariants:**
- `budget_warning` fires before `budget_exceeded`.
- Each threshold emits exactly one event per crossing.

### Acceptance Criteria

- [ ] `budget_warning` emitted when soft limits crossed.
- [ ] `budget_exceeded` emitted when hard limits crossed.
- [ ] Events include usage summary and specific limit crossed.
- [ ] Deduplication prevents repeated events for same threshold.

### How to Test

```python
def test_budget_warning_event():
    events = []
    controller = BackPressureController(max_tokens=100, warn_tokens=80)
    controller.tokens_used = 85
    controller._emit_budget_events(events.append)
    assert any(e.type == "budget_warning" for e in events)

def test_budget_warning_deduplicated():
    events = []
    controller = BackPressureController(max_tokens=100, warn_tokens=80)
    controller.tokens_used = 85
    controller._emit_budget_events(events.append)
    controller._emit_budget_events(events.append)
    warnings = [e for e in events if e.type == "budget_warning"]
    assert len(warnings) == 1
```
