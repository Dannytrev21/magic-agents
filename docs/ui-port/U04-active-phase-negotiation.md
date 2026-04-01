# Epic U4: Active Phase Workspace and Negotiation Loop

**Priority:** 4 (High)  
**Implementation Target:** center-pane phase review, revision, approval, and question handling  
**Primary Outcome:** make the negotiation flow readable and efficient for repeated daily use

## Rationale

The current UI dumps structured phase data into generic message blocks. The Operator Workspace needs a summary-first review surface where the operator can understand each phase quickly, inspect details when necessary, and take the next action inline.

## Implementation Status

- Implemented in the React workspace and reflected in `progress.json` on 2026-04-01.
- `U4.1` shipped phase-aware review formatters for all seven negotiation phases with summary-first rendering and raw-payload fallback details.
- `U4.2` shipped inline approve and revise controls wired to `/api/respond` with loading, success, and error feedback kept beside the action row.
- `U4.3` shipped a distinct clarifying-questions region and smooth in-place phase advancement with transition-backed session updates.
- `U4.4` shipped a role-aware transcript with bottom-pin auto-scroll and pause-on-scroll-up behavior.
- `U4.5` shipped a sticky mini-rail with breadcrumb context, completed-phase reopening, and input-aware shortcut suppression.

---

## Story U4.1: Render each phase as a structured review surface

### EARS Requirement

> **When** the backend returns phase results, the system **shall** render them as typed phase-specific sections that summarize the main decision before exposing raw details.

### Design by Contract

**Preconditions:**
- The active session has a current phase and result payload.
- The frontend knows the phase type and expected result shape.

**Postconditions:**
- The operator sees a concise summary of the current phase outcome first.
- Detailed fields remain accessible without overwhelming the primary surface.
- Unknown fields or unexpected payloads degrade gracefully.

**Invariants:**
- Phase titles and counts reflect backend truth.
- Typed renderers avoid dumping raw JSON as the default presentation.
- IDs and refs remain visible in mono styling.

### Acceptance Criteria

- [x] Each of the seven phases has a dedicated renderer or formatter.
- [x] The center pane leads with the primary decision or contract of the phase.
- [x] Dense supporting fields are collapsible or secondary.
- [x] Unknown payload keys still render safely in a fallback details view.

### How to Test

- Add renderer tests for all seven phases using representative mock payloads.
- Add snapshot tests that confirm summary-first hierarchy.
- Manually inspect phases with long lists and nested objects for readability.

---

## Story U4.2: Add inline approve and revise actions

### EARS Requirement

> **When** the operator reviews an active phase, the system **shall** present inline actions to approve or revise that phase without leaving the current work surface.

### Design by Contract

**Preconditions:**
- A phase response is present in the center pane.
- The session is not complete or locked.

**Postconditions:**
- Approve advances the session only after backend confirmation.
- Revise sends operator feedback while preserving the current phase context.
- Loading and error states are visible near the actions they affect.

**Invariants:**
- Approve and revise actions are mutually understandable and never ambiguous.
- The operator can see what message will be sent before submission.
- Disabled states prevent duplicate submissions.

### Acceptance Criteria

- [x] The center pane includes explicit approve and revise actions.
- [x] Revise supports freeform operator feedback without redirecting to a separate chat screen.
- [x] Action states show loading, success, and error feedback inline.
- [x] Duplicate submissions are prevented while a mutation is in flight.

### How to Test

- Add integration tests for approve success, revise success, and mutation failure.
- Verify duplicate clicks do not emit duplicate mutations.
- Confirm keyboard users can trigger both actions without pointer interaction.

---

## Story U4.3: Surface clarifying questions and phase transitions cleanly

### EARS Requirement

> **If** a phase emits clarifying questions, the system **shall** present them beside the current phase result and keep the transition into the next phase smooth and legible.

### Design by Contract

**Preconditions:**
- The phase payload may include zero or more questions.
- Phase transitions may update large result sections.

**Postconditions:**
- Clarifying questions are distinguishable from phase results.
- Transitioning to the next phase preserves operator orientation.
- Non-urgent UI updates do not freeze the feedback input or surrounding layout.

**Invariants:**
- Question text is never mistaken for backend-approved contract text.
- Phase transitions preserve scroll intention where possible.
- Motion is restrained and functional.

### Acceptance Criteria

- [x] Clarifying questions render in a dedicated, visually distinct region.
- [x] The next phase transition does not feel like a new page load.
- [x] `startTransition` is used for non-urgent workspace updates where it improves responsiveness.
- [x] Operators can still reference the previous result summary during or after the transition when appropriate.

### How to Test

- Add tests for phases with and without clarifying questions.
- Simulate long phase payloads and verify input responsiveness during transitions.
- Capture a manual recording to confirm transitions are smooth but restrained.

---

## Story U4.4: Render the conversation transcript for the active phase

### EARS Requirement

> **When** transcript history exists for the active phase, the system **shall** present that conversation as a readable transcript that distinguishes system activity, operator feedback, and model output.

### Design by Contract

**Preconditions:**
- Transcript or session history data exists for the current session.
- The workspace can associate transcript entries with the active phase.

**Postconditions:**
- Transcript entries render in chronological order.
- System, operator, and model entries are visually distinct.
- Auto-scroll behavior keeps up with new entries unless the operator intentionally reads older content.

**Invariants:**
- Transcript rendering is read-only.
- Timestamps and role labels remain secondary to message content.
- Compacted or summarized history states remain understandable if the backend introduces them.

### Acceptance Criteria

- [x] Transcript entries render with distinct system, operator, and model states.
- [x] New transcript entries auto-scroll when the operator is already at the bottom.
- [x] Auto-scroll pauses when the operator intentionally scrolls up.
- [x] Transcript rendering remains readable with long or dense phase history.

### How to Test

- Add component tests for transcript role styling and ordering.
- Add tests for auto-scroll behavior in bottom-pinned and scrolled-up states.
- Manually inspect a revised phase flow with multiple transcript entries.

---

## Story U4.5: Add a sticky phase mini-rail and breadcrumb context

### EARS Requirement

> **While** the operator works in the center pane, the system **shall** keep a compact phase navigation spine and breadcrumb context visible so they can orient themselves and revisit completed work without losing place.

### Design by Contract

**Preconditions:**
- A session is active with current and completed phase metadata.
- The center pane supports sticky sub-navigation.

**Postconditions:**
- The center pane shows a compact seven-phase mini-rail.
- Breadcrumb context identifies the current story and center-pane subview.
- Completed phases can be revisited where the workflow permits.

**Invariants:**
- Navigation never implies phases can be skipped ahead arbitrarily.
- The sticky navigation remains subordinate to the primary phase content.
- Keyboard shortcuts, if added, do not fire while an input or textarea is focused.

### Acceptance Criteria

- [x] The center pane includes a sticky mini-rail for the seven phases.
- [x] Breadcrumb context identifies the active story and current center-pane context.
- [x] Completed phases can be reopened from the mini-rail where appropriate.
- [x] Any quick-jump shortcuts are suppressed while text inputs are focused.

### How to Test

- Add component tests for the mini-rail in pending, active, and completed states.
- Verify breadcrumb context changes with center-pane subviews.
- Run keyboard-only checks for permitted quick-jump behavior and input suppression.
