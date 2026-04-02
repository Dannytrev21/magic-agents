# Epic U07: Real-time Updates & Streaming

**Priority:** 7 (Medium — connects backend events to UI reactivity)
**Depends On:** U01-U04 (all visual components), P6 (structured streaming events)

## Technical Thesis

The UI subscribes to the backend SSE stream and dispatches typed events to a lightweight client-side store. Components subscribe to store slices and re-render only when their slice changes. No polling. No WebSocket complexity. Pure SSE with automatic reconnection.

---

## Story U07.1: SSE Client with Auto-Reconnection

### EARS Requirement

> The system **shall** maintain a persistent SSE connection to `GET /api/events/{session_id}` that automatically reconnects with exponential backoff (1s, 2s, 4s, max 30s) when the connection drops, and emit a `connection_status` update to the UI store on every state change.

### Design by Contract

**Preconditions:**
- A session ID is available from the session start response.
- The browser supports the `EventSource` API.

**Postconditions:**
- An `EventSource` is opened to the backend SSE endpoint.
- Incoming events are parsed and dispatched to the `useEventStore` hook.
- On connection close, reconnection starts with exponential backoff.
- `connection_status` updates: `"connected"` on open, `"reconnecting"` on close with retry, `"disconnected"` after max retries exhausted.
- The top bar status indicator (U02.4) reflects the connection status.

**Invariants:**
- Only one SSE connection exists per session (no duplicates on re-render).
- Reconnection backoff resets after a successful reconnection.
- The SSE client is cleaned up on component unmount (no memory leaks).
- Events received during reconnection gap are not replayed (eventual consistency).

### Acceptance Criteria

- [x] SSE connection establishes on session start.
- [x] Connection status is reflected in the top bar indicator.
- [x] Auto-reconnection uses exponential backoff.
- [x] Cleanup occurs on unmount.

### Implementation Notes

- `usePhaseWorkspaceModel()` now owns the session-scoped `useSSE()` lifecycle and maps connection state into quiet top-bar copy.
- The shipped shell exposes a dedicated connection-status pill so stream health is visible without overriding the existing session-status language.
- Browser tests use a lightweight `EventSource` stub in Vitest while `useSSE.test.ts` keeps the full reconnect behavior under direct hook coverage.

### How to Test

```typescript
test("SSE client connects and receives events", async () => {
  const { result } = renderHook(() => useSSE("test-session"));
  await waitFor(() => expect(result.current.status).toBe("connected"));
});

test("SSE client reconnects on drop", async () => {
  const mockES = new MockEventSource();
  const { result } = renderHook(() => useSSE("test-session"));
  mockES.simulateClose();
  await waitFor(() => expect(result.current.status).toBe("reconnecting"));
});
```

---

## Story U07.2: Client-Side Event Store

### EARS Requirement

> The system **shall** implement a `useEventStore` React hook backed by a lightweight store that categorizes incoming SSE events by type and provides selector hooks for components to subscribe to specific event types without re-rendering on unrelated events.

### Design by Contract

**Preconditions:**
- SSE events are arriving via the SSE client (U07.1).
- Events conform to the typed schema from P6.

**Postconditions:**
- `usePhaseEvents()` returns only `phase_start`, `phase_progress`, `phase_complete`, `phase_error` events.
- `useBudgetEvents()` returns only `budget_warning`, `budget_exceeded` events.
- `useValidationEvents()` returns only `validation_result` events.
- `useLatestEvent(type)` returns the most recent event of a given type.
- Selectors use referential equality to prevent unnecessary re-renders.

**Invariants:**
- The store retains the last 100 events (FIFO overflow).
- Store updates are batched within a single React render cycle.
- The store is scoped to the active session — a new session clears the store.

### Acceptance Criteria

- [x] Selector hooks return correctly filtered events.
- [x] Components only re-render when their subscribed event type arrives.
- [x] Store clears on session change.
- [x] FIFO overflow at 100 events.

### Implementation Notes

- `EventStoreProvider` is mounted in the shared app provider stack so all live workspace surfaces subscribe to one store.
- `usePhaseWorkspaceModel()` clears the store whenever the confirmed session changes, preventing stale phase events from leaking into the next story.
- FIFO retention and selector behavior remain covered in `eventStore.test.ts`, while `phaseWorkspaceModel.test.tsx` verifies the session handoff wiring and connection-label mapping.

### How to Test

```typescript
test("usePhaseEvents filters correctly", () => {
  const store = createEventStore();
  store.dispatch({ type: "phase_start", session_id: "s1", step: "phase_1" });
  store.dispatch({ type: "budget_warning", session_id: "s1" });
  const { result } = renderHook(() => usePhaseEvents(), { wrapper: StoreProvider(store) });
  expect(result.current).toHaveLength(1);
  expect(result.current[0].type).toBe("phase_start");
});
```

---

## Story U07.3: Live Phase Progress Indicator

### EARS Requirement

> **While** a phase is executing (between `phase_start` and `phase_complete` events), the system **shall** display a progress indicator in both the phase mini-rail and the center workspace header — showing an animated bar, elapsed time, and the current step description from `phase_progress` events.

### Design by Contract

**Preconditions:**
- A `phase_start` event has been received.
- The phase has not yet completed.

**Postconditions:**
- A thin (3px) animated progress bar renders at the top of the center workspace in `--color-signal`.
- The progress bar uses an indeterminate animation (sliding gradient) since phase duration is unknown.
- Elapsed time displays as `Mono` text: "12s", "1m 03s".
- Step description (from `phase_progress` events) displays below the progress bar.
- On `phase_complete`, the bar fills to 100% and fades out over 300ms.
- On `phase_error`, the bar turns `--color-error` and stays visible.

**Invariants:**
- Only one progress indicator is visible at a time.
- The progress bar does not block interaction with the workspace content below it.

### Acceptance Criteria

- [x] Progress bar appears on `phase_start`.
- [x] Elapsed time counts up in real-time.
- [x] Step description updates from `phase_progress` events.
- [x] Bar fills and fades on `phase_complete`.
- [x] Bar turns red on `phase_error`.

### Implementation Notes

- `PhaseProgressBar` now ships in two quiet surfaces: a compact rail variant and a fuller workspace-header variant.
- Completion switches the bar into a terminal success state before it leaves the screen, while error events keep the indicator visible in the error tone.
- `WorkspaceCenterPane.test.tsx` covers the dual-surface rendering and `PhaseProgressBar.test.tsx` covers the timer, message, completion, and error states.

### How to Test

```typescript
test("progress bar appears during phase execution", async () => {
  const store = createEventStore();
  store.dispatch({ type: "phase_start", session_id: "s1", step: "phase_1" });
  render(<PhaseProgressBar />, { wrapper: StoreProvider(store) });
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
});
```
