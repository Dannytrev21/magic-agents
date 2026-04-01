# Epic U3: Story Intake and Session Lifecycle

**Priority:** 3 (High)  
**Implementation Target:** left-rail intake flows, resumable sessions, and session-aware workspace state  
**Primary Outcome:** make the app usable as a daily intake and review tool

## Rationale

The workspace only works if operators can reliably enter it. Jira story selection, manual entry, checkpoint resume, and stateful session feedback are the top-of-funnel actions that determine whether the UI feels operational or merely decorative.

---

## Story U3.1: Unify Jira intake and manual entry in the left rail

### EARS Requirement

> **When** the operator opens the workspace without an active session, the system **shall** present Jira intake and manual acceptance-criteria entry as two modes of the same left-rail workflow.

### Design by Contract

**Preconditions:**
- The workspace has loaded.
- Jira configuration status can be queried from the backend.

**Postconditions:**
- The operator can select a Jira story or create a manual story payload without leaving the left rail.
- Both modes emit the same normalized story shape into the center workspace.
- Empty, loading, and configuration-error states are understandable.

**Invariants:**
- Manual entry remains available even when Jira is unavailable.
- Story list filtering does not block typing.
- Story summaries and IDs remain scannable in compact rows.

### Acceptance Criteria

- [ ] Jira story intake and manual entry share one left-rail surface.
- [ ] Jira loading, empty, and misconfiguration states are explicitly designed.
- [ ] Story filtering uses a responsive input experience for larger lists.
- [ ] Manual entry produces the same normalized state shape as Jira intake.

### How to Test

- Add component tests for configured, unconfigured, empty, and populated Jira states.
- Add a test for manual entry normalization into the shared story model.
- Verify local list filtering stays responsive while typing.

---

## Story U3.2: Start, resume, and recover sessions from checkpoints

### EARS Requirement

> **When** a story has an active or checkpointed negotiation session, the system **shall** let the operator resume that session from the left rail without rebuilding state from scratch.

### Design by Contract

**Preconditions:**
- Session lookup endpoints return checkpoint metadata for a story.
- The workspace can distinguish new sessions from resumed sessions.

**Postconditions:**
- The operator sees whether a story is new, in progress, resumable, or complete.
- Resume actions hydrate the center pane and inspector with the saved session context.
- Failed resume attempts return controlled error feedback.

**Invariants:**
- Resume never fabricates phase progress.
- Session identity remains stable across tabs and mutations.
- New-session and resume actions are visually distinct.

### Acceptance Criteria

- [ ] The left rail shows resume affordances when checkpoint data exists.
- [ ] Resume loads phase number, summary metadata, and current session context.
- [ ] Failed resume actions do not leave the workspace in a broken intermediate state.
- [ ] Operators can intentionally start a fresh session when a checkpoint exists.

### How to Test

- Add integration tests for no checkpoint, resumable checkpoint, and failed resume scenarios.
- Mock resume payloads and verify the workspace updates without a full reload.
- Perform a manual browser test across refreshes with a checkpointed session.

---

## Story U3.3: Model session state in React without UI drift

### EARS Requirement

> **While** the operator is working in a session, the system **shall** keep session state synchronized between React view state and backend responses so the UI never implies progress the backend has not confirmed.

### Design by Contract

**Preconditions:**
- The typed API client and query layer are in place.
- Session mutations return canonical backend state.

**Postconditions:**
- The UI can distinguish optimistic local intent from confirmed session state.
- Local draft input survives non-destructive workspace updates.
- Query invalidation rules are explicit for negotiation, compile, and pipeline mutations.

**Invariants:**
- Backend-confirmed state wins over stale local snapshots.
- Draft feedback text is not lost on unrelated query refreshes.
- Session status badges only reflect confirmed backend state.

### Acceptance Criteria

- [ ] Session identity, phase number, and status are derived from backend-confirmed state.
- [ ] Draft user feedback survives inspector switches and non-destructive refreshes.
- [ ] Mutations invalidate or refresh only the required queries.
- [ ] The UI does not show a completed phase before the backend confirms it.

### How to Test

- Add integration tests for mutation success, failure, and race-condition-like refreshes.
- Simulate rapid session updates and confirm draft text is preserved.
- Verify query invalidation does not refetch unrelated panes.

---

## Story U3.4: Render a phase-aware acceptance criteria checklist

### EARS Requirement

> **When** a story is selected, the system **shall** render its acceptance criteria in the left rail as a scannable checklist with selection state, optional classification state, and eventual verdict state.

### Design by Contract

**Preconditions:**
- A normalized story model exists in workspace state.
- Classification and verdict data may or may not exist yet.

**Postconditions:**
- Each AC row displays its index, text, and any known status metadata.
- Selecting an AC updates the center workspace or inspector context where relevant.
- Long AC text remains readable in compact form without collapsing the rail.

**Invariants:**
- AC ordering matches the source story ordering.
- Missing classification or verdict data does not break the list.
- The rail remains readable with many AC items.

### Acceptance Criteria

- [ ] AC rows show index and text for the selected story.
- [ ] Classification badges and verdict indicators appear when data exists.
- [ ] Selecting an AC updates related workspace context.
- [ ] Long AC text is truncated responsibly with access to full text.

### How to Test

- Add component tests for checklist rows with and without classification or verdict data.
- Verify selection state updates the rest of the workspace correctly.
- Manually inspect long AC lists to confirm compact readability.

---

## Story U3.5: Display a left-rail phase progress timeline

### EARS Requirement

> **While** a session is active, the system **shall** render a phase progress timeline in the left rail so the operator can understand session progress without leaving the current view.

### Design by Contract

**Preconditions:**
- The current session has phase metadata.
- The workspace can distinguish pending, active, complete, and failed states.

**Postconditions:**
- All negotiation phases are rendered in order.
- The active phase is visually emphasized.
- Completed phases can be revisited where the workflow allows.

**Invariants:**
- Only one phase is active at a time.
- The timeline reflects backend-confirmed progress.
- The timeline remains subordinate to the selected story and AC context.

### Acceptance Criteria

- [ ] The timeline renders all seven phases in order.
- [ ] Active, complete, pending, and failed states are distinct.
- [ ] Completed phases can be revisited from the timeline where supported.
- [ ] The active phase remains easy to locate in long left-rail sessions.

### How to Test

- Add component tests for each phase status state.
- Verify timeline updates after approve and revise flows.
- Run a manual flow through multiple phases and confirm the timeline stays synchronized.

---

## Story U3.6: Surface session health and usage telemetry

### EARS Requirement

> **If** the backend exposes session usage or budget telemetry, the system **shall** render a compact health section in the left rail showing the current utilization and warning state without interrupting primary work.

### Design by Contract

**Preconditions:**
- Session usage, budget, or cost data is available from backend endpoints or streaming events.
- The left rail has a dedicated region for status telemetry.

**Postconditions:**
- The rail can show budget utilization, duration, API calls, or cost where supported.
- Warning states are visible but secondary to the main workflow.
- Missing telemetry results in a clear empty or unavailable state.

**Invariants:**
- The health section never invents values the backend has not provided.
- Warning states do not block the operator unless the backend has already blocked the session.
- The UI degrades gracefully when telemetry is absent.

### Acceptance Criteria

- [ ] Available telemetry is rendered in a compact health section.
- [ ] Warning states are visible and understandable.
- [ ] Unsupported or unavailable telemetry renders a clear fallback state.
- [ ] Health data updates without forcing a full workspace reload.

### How to Test

- Add tests for available, warning, and unavailable telemetry states.
- Mock usage updates and verify only the health region refreshes.
- Manually verify the health section remains readable during active work.
