# ADR 0006: Client-Side SSE Event Store (U07)

## Status

Accepted

## Context

The backend emits structured SSE events via `GET /api/events/{session_id}` (ADR 0005), but the React frontend had no persistent connection or event management layer. Components fetched data via React Query mutations, which is appropriate for request-response but not for real-time streaming. The pipeline streaming in `client.ts` used a one-shot `fetch` with `ReadableStream`, which does not support auto-reconnection or shared event dispatch.

claw-code's terminal UI processes events inline within the turn loop. For a web UI, we need a persistent connection with reconnection logic and a shared store that routes events to the correct components without prop drilling.

## Decision

### U07.1: SSE Client (`useSSE` hook)

1. **`EventSource`-based hook**: `useSSE(sessionId)` opens a single `EventSource` to `/api/events/{sessionId}`. Only one connection exists per session regardless of re-renders.

2. **Exponential backoff**: On connection drop, reconnects with delays of `1s, 2s, 4s, 8s, ...` capped at 30s. Backoff resets after a successful reconnection.

3. **Connection status**: Exposed as `'connecting' | 'connected' | 'reconnecting' | 'disconnected'`. `usePhaseWorkspaceModel()` maps this into stable top-bar copy so the shell can surface live-stream health without duplicating SSE wiring.

4. **Workspace bridge hook**: `usePhaseWorkspaceModel(sessionId)` is the page-level integration point. It owns the live `EventSource` subscription for the active session, clears stale event-store state when the session changes, and dispatches each parsed SSE payload into the shared client-side event store so the shell stream-status pill and `PhaseProgressBar` stay in sync.

5. **Max retries**: Configurable (default 8). After exhaustion, status transitions to `'disconnected'` and reconnection stops.

6. **Cleanup**: `EventSource.close()` and timer cleanup run on unmount and session ID change.

### U07.2: Event Store (`createEventStore` + context hooks)

1. **Framework-agnostic core**: `createEventStore()` returns a plain object with `dispatch`, `getEvents`, `subscribe`, `clearForSession`, and `clear`. No React dependency in the core.

2. **React integration via `useSyncExternalStore`**: Hooks subscribe to the store using React 18's `useSyncExternalStore` for tear-free reads.

3. **Typed selectors**: `usePhaseEvents()`, `useBudgetEvents()`, `useValidationEvents()`, `useLatestEvent(type)` filter events by type. `useMemo` ensures referential stability.

4. **FIFO overflow**: The store retains at most 100 events. Oldest events are evicted on overflow.

5. **Session scoping**: `clearForSession(id)` clears events when the session ID changes. `usePhaseWorkspaceModel()` owns that handoff so stale phase activity never bleeds across sessions.

### U07.3: Phase Progress Bar

1. **Event-driven rendering**: `PhaseProgressBar` subscribes to phase events via `usePhaseEvents()`. It appears on `phase_start`, updates step description on `phase_progress`, lingers in a terminal complete state on `phase_complete`, and turns red on `phase_error`. The workspace renders it in both the sticky mini-rail and the center header.

2. **Elapsed timer**: A 1-second interval counts up from the `phase_start` timestamp. Resets when a new phase starts.

3. **Indeterminate animation**: A sliding gradient bar in `--color-signal` since phase duration is unknown. Respects `prefers-reduced-motion`.

## Consequences

- Components can subscribe to specific event slices without re-rendering on unrelated events.
- The SSE connection is resilient to network drops with bounded retry.
- No polling overhead. The backend pushes events; the UI reacts.
- The event store is testable in isolation (no React required for the core).
- The page-level workspace keeps one session-scoped event history inside the shared store while still letting shell chrome and workspace surfaces react independently.
- The PhaseProgressBar provides real-time feedback during negotiation without additional API calls.
- Routing store writes through `useSSE(..., { onEvent })` preserves ordered `phase_start` + `phase_progress` pairs that can otherwise collapse if React batches incoming events into one render.
- The React provider stack mounts `EventStoreProvider` in `ui/src/app/AppProviders.tsx`, while `usePhaseWorkspaceModel()` bridges `useSSE()` into the store and feeds the top-bar stream indicator plus the mini-rail and workspace-header progress bars.
