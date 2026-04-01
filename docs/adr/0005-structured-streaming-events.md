# ADR 0005: Structured Streaming Events (P06)

## Status

Accepted

## Context

magic-agents had SSE streaming via `RuntimeEvent.as_sse()` for the verification pipeline, but event types were ad-hoc strings (`step`, `done`, `error`). The `NegotiationHarness` emitted no runtime events, making it impossible for the web UI to render real-time phase progress, validation feedback, or budget status during negotiation.

claw-code's `stream_submit_message` demonstrated a pattern where every SSE event has a typed `type` field and predictable payload shape, enabling consistent UI rendering.

## Decision

1. **Closed event enum**: `NegotiationEvent` enum defines exactly 10 typed event types (`phase_start`, `phase_progress`, `phase_complete`, `phase_error`, `validation_result`, `budget_warning`, `budget_exceeded`, `skill_dispatch`, `skill_complete`, `session_checkpoint`).

2. **Validated RuntimeEvent**: `RuntimeEvent.__post_init__` rejects unknown types at construction time. Legacy types (`step`, `done`, `error`) remain accepted for backward compatibility.

3. **Typed SSE format**: New event types emit `event: {type}\ndata: {json}\n\n` (standard SSE with event field). Legacy types emit `data: {json}\n\n` only.

4. **Event emitter callback**: `NegotiationHarness.__init__` accepts an optional `event_emitter: Callable` that is invoked at lifecycle points. Callback exceptions are logged and swallowed (never block the harness).

5. **SSE endpoint**: `GET /api/events/{session_id}?types=` streams events from `SessionState.event_buffer` with optional type filtering.

6. **Schema contract**: `EVENT_SCHEMAS` maps each event type to its required payload fields, enabling UI and test assertions.

## Consequences

- Web UI can subscribe to typed SSE events for real-time negotiation progress.
- Invalid event types are caught at construction, not at rendering time.
- The `event_emitter` pattern is opt-in and does not change existing harness behavior.
- Legacy pipeline streaming continues to work unchanged.
