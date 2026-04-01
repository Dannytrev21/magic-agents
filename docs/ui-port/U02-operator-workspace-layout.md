# Epic U2: Operator Workspace Layout

**Priority:** 2 (High)  
**Implementation Target:** three-pane app composition with sticky navigation and responsive behavior  
**Primary Outcome:** eliminate the current "screen hopping" model in favor of one continuous workspace

## Rationale

The most visible improvement is structural, not ornamental. The app needs to feel like an operating surface: intake on the left, active work in the center, evidence on the right. This epic defines the workspace composition that the rest of the port relies on.

---

## Story U2.1: Implement the three-pane workspace layout

### EARS Requirement

> **When** the Operator Workspace loads on desktop, the system **shall** display a persistent left rail, center work surface, and right inspector in a single continuous view.

### Design by Contract

**Preconditions:**
- The application shell is available.
- Workspace state identifies the currently selected story or session.

**Postconditions:**
- The left rail holds intake and session controls.
- The center pane holds the active phase or execution surface.
- The right pane holds evidence, scan output, and traceability context.

**Invariants:**
- The center pane remains visually dominant.
- Side panes can scroll independently without breaking the shell.
- Layout hierarchy remains readable without decorative cards.

### Acceptance Criteria

- [ ] Desktop layouts render all three panes at once.
- [ ] Pane widths follow a clear hierarchy, with the center pane widest.
- [ ] Independent scroll regions do not cause header jitter or layout collapse.
- [ ] The visual treatment uses sections and dividers rather than a grid of cards.

### How to Test

- Add layout snapshot tests for common desktop widths.
- Verify independent scrolling in a browser with long story lists and long traceability output.
- Record a manual smoke test showing the full workspace within one stable composition.

---

## Story U2.2: Add the sticky phase rail and session status strip

### EARS Requirement

> **While** a negotiation session is active, the system **shall** keep the current phase and session status visible without requiring the operator to scroll back to the top.

### Design by Contract

**Preconditions:**
- A session is active or resumable.
- Phase metadata is available from the current session state.

**Postconditions:**
- The operator can always identify the active phase.
- Completed and pending phases are distinguishable at a glance.
- Session state such as running, waiting, approved, or complete remains visible.

**Invariants:**
- The phase rail reflects the true backend phase count.
- Sticky behavior does not reduce the center pane below usable height.
- Status colors are semantic and consistent across the app.

### Acceptance Criteria

- [ ] The phase rail shows all seven negotiation phases, not an abbreviated count.
- [ ] The active phase is visually distinct from complete and pending phases.
- [ ] Session status is visible while the operator scrolls the center workspace.
- [ ] Phase navigation does not imply fake client-side completion states.

### How to Test

- Add component tests for the seven-phase rail in idle, active, complete, and resumed states.
- Verify sticky behavior in desktop and tablet widths.
- Confirm that the rail updates correctly when the backend advances phases.

---

## Story U2.3: Replace screen jumps with panel state transitions

### EARS Requirement

> **When** the operator changes workflow focus, the system **shall** transition panes and sections in place instead of navigating through disconnected full-screen views.

### Design by Contract

**Preconditions:**
- The workspace has a selected story or session.
- The shell supports swapping center content and inspector content independently.

**Postconditions:**
- Story selection, negotiation, traceability review, and execution occur inside one route context.
- Focus is moved intentionally to the newly active region.
- Non-urgent view changes do not block typing or selection.

**Invariants:**
- Workspace state is serializable from React state and URL state.
- Transitions preserve context instead of clearing all pane content.
- Animations remain fast and restrained.

### Acceptance Criteria

- [ ] The new UI avoids the current separate "Home / AC Overview / Negotiate / Traceability" screen model.
- [ ] Center and inspector surfaces can swap independently.
- [ ] Phase transitions use in-place updates, not full re-renders of the whole workspace.
- [ ] Focus lands in the primary active region after each transition.

### How to Test

- Add integration tests that select a story, begin negotiation, and open traceability without route thrash.
- Verify focus movement with keyboard-only navigation.
- Measure interaction responsiveness during transitions with large payloads.

---

## Story U2.4: Add a top bar with session context and workspace controls

### EARS Requirement

> **While** the Operator Workspace is active, the system **shall** render a top bar that keeps the product identity, current story, current phase context, and workspace controls visible.

### Design by Contract

**Preconditions:**
- The shell layout exists.
- Story and session metadata can be derived from workspace state.

**Postconditions:**
- The top bar displays product identity, Jira key or manual story key, current phase or view context, and panel controls.
- Connection or session state can be surfaced without crowding the main workspace.
- The top bar remains visually stable during pane scrolling.

**Invariants:**
- The top bar height and visual weight stay restrained.
- Story identifiers remain readable in mono styling.
- Workspace controls do not compete with the center pane for attention.

### Acceptance Criteria

- [ ] The top bar shows product identity and current story context.
- [ ] The top bar shows phase or workspace context for the active session.
- [ ] Panel controls are reachable from the top bar.
- [ ] The bar remains stable during independent pane scrolling.

### How to Test

- Add component tests for top bar states with and without an active session.
- Verify the story ID and phase context update from session state.
- Manually confirm the top bar does not jitter during independent pane scrolling.

---

## Story U2.5: Support panel collapse, persistence, and responsive fallbacks

### EARS Requirement

> **When** the operator changes available workspace space or the viewport shrinks, the system **shall** preserve a usable center workspace by collapsing or overlaying side panes without losing context.

### Design by Contract

**Preconditions:**
- The three-pane shell is rendered.
- Left and right pane visibility can be controlled from React state.

**Postconditions:**
- Desktop users can collapse and restore side panes.
- Panel visibility preferences persist across reloads when appropriate.
- Tablet and mobile layouts fall back to overlays or panel switching instead of a broken three-column squeeze.

**Invariants:**
- The center workspace keeps priority for available width.
- Responsive transitions do not lose pane-local state such as scroll or selected tabs when that state can be preserved.
- Collapsing both side panes remains a supported state.

### Acceptance Criteria

- [ ] Left and right panes can be collapsed and restored from workspace controls.
- [ ] Panel visibility preferences persist across reloads.
- [ ] Narrower breakpoints use overlays or single-panel switching instead of unusable compressed columns.
- [ ] Returning to wider breakpoints restores the multi-pane layout predictably.

### How to Test

- Add tests for persisted panel visibility state.
- Run responsive browser checks across desktop, tablet, and mobile widths.
- Verify pane-local state survives collapse and restore where designed.
