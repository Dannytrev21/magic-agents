# Epic P6: Structured Streaming Events

**Priority:** 6 (Medium)
**Status:** Not Started
**Ported From:** `claw-code/src/query_engine.py` (`stream_submit_message` — typed SSE yields with `message_start`, `command_match`, `tool_match`, `permission_denial`, `message_delta`, `message_stop`)
**Integration Target:** `src/verify/runtime.py` (RuntimeEvent), `src/verify/negotiation/web.py` (SSE endpoints)

## Rationale

magic-agents has SSE streaming in `web.py` and a `RuntimeEvent` dataclass, but the event types and payloads are ad-hoc — each endpoint constructs its own event format. claw-code's `stream_submit_message` demonstrates a structured approach where every event has a typed `type` field and predictable payload shape, enabling the web UI to render progress indicators, token counts, and error states consistently.

---

## Story P6.1: Define Typed Event Schema

### EARS Requirement

> The system **shall** define a closed set of SSE event types — `phase_start`, `phase_progress`, `phase_complete`, `phase_error`, `validation_result`, `budget_warning`, `budget_exceeded`, `skill_dispatch`, `skill_complete`, `session_checkpoint` — each with a documented JSON payload schema.

### Design by Contract

**Preconditions:**
- Each event type has a corresponding payload structure with required fields.

**Postconditions:**
- `NegotiationEvent` is an enum of all valid event types.
- `RuntimeEvent.payload()` returns a dict matching the documented schema for its type.
- Unknown event types cannot be constructed.

**Invariants:**
- Every SSE message has a valid `type` field from the enum.
- Payload schemas are backward-compatible (new optional fields OK, no removals).

### Acceptance Criteria

- [x] `NegotiationEvent` enum is defined with all listed types.
- [x] Each type has a documented payload schema.
- [x] `RuntimeEvent` validates type against the enum.
- [x] `EVENT_SCHEMAS` constant maps each type to expected fields.

### How to Test

```python
def test_valid_event_types():
    for event_type in NegotiationEvent:
        event = RuntimeEvent(type=event_type.value, session_id="test")
        assert event.type == event_type.value

def test_invalid_event_type():
    with pytest.raises(ValueError):
        RuntimeEvent(type="invalid_type", session_id="test")
```

---

## Story P6.2: Emit Structured Events from NegotiationHarness

### EARS Requirement

> **When** the `NegotiationHarness` transitions between phases, validates output, or encounters an error, the system **shall** emit the corresponding typed SSE event through an `EventEmitter` callback.

### Design by Contract

**Preconditions:**
- The `NegotiationHarness` has an optional `event_emitter: Callable[[RuntimeEvent], None]` callback.

**Postconditions:**
- `phase_start` emitted before LLM call.
- `phase_progress` emitted during multi-turn feedback.
- `phase_complete` emitted when exit condition passes.
- `phase_error` emitted on validation failure or exception.
- `validation_result` emitted after `validate.py` runs.
- `session_checkpoint` emitted after checkpoint save.

**Invariants:**
- Event emission never blocks the harness — callback errors are logged and swallowed.
- Events are in causal order (start → progress → complete/error).
- Every `phase_start` has a corresponding `phase_complete` or `phase_error`.

### Acceptance Criteria

- [x] `NegotiationHarness.__init__` accepts optional `event_emitter`.
- [x] All six event types emitted at correct lifecycle points.
- [x] Callback exceptions caught and logged.
- [x] No-op default when no emitter registered.

### How to Test

```python
def test_event_order():
    events = []
    harness = NegotiationHarness(context, event_emitter=events.append)
    harness.run_current_phase(llm)
    types = [e.type for e in events]
    assert types[0] == "phase_start"
    assert types[-1] in ("phase_complete", "phase_error")

def test_callback_error_graceful():
    def bad_emitter(event): raise RuntimeError("fail")
    harness = NegotiationHarness(context, event_emitter=bad_emitter)
    harness.run_current_phase(llm)  # Should not raise
```

---

## Story P6.3: SSE Endpoint with Event Filtering

### EARS Requirement

> **When** a client connects to `GET /api/events/{session_id}`, the system **shall** stream all events as SSE, and **where** the client provides a `types` query parameter, the system **shall** filter to only those event types.

### Design by Contract

**Preconditions:**
- A valid `session_id` exists in the `SessionStore`.
- SSE connection established with `text/event-stream` content type.

**Postconditions:**
- Events streamed in real-time as emitted by harness.
- Each SSE message has `event: {type}` and `data: {json_payload}` fields.
- `?types=phase_start,phase_complete` filters to those types only.
- Stream closes when session ends or client disconnects.

**Invariants:**
- Filtering never drops events from the harness — only from the SSE stream.
- Multiple concurrent clients per session are supported.

### Acceptance Criteria

- [x] `GET /api/events/{session_id}` returns `text/event-stream`.
- [x] Events include both `event:` and `data:` SSE fields.
- [x] `?types=` query parameter filters event types.
- [x] Disconnected clients cleaned up without blocking harness.

### How to Test

```python
async def test_sse_stream(async_client):
    async with async_client.stream("GET", f"/api/events/{session_id}") as resp:
        assert resp.headers["content-type"].startswith("text/event-stream")

async def test_sse_filtering(async_client):
    url = f"/api/events/{session_id}?types=phase_complete"
    async with async_client.stream("GET", url) as resp:
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                assert "phase_complete" in line
```
