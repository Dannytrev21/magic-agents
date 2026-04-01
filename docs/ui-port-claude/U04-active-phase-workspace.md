# Epic U04: Active Phase Workspace (Center Panel)

**Priority:** 4 (High — the core interaction surface)
**Depends On:** U01 (primitives), U02 (center panel), U03 (phase navigation)

## Interaction Thesis

Smooth panel swaps instead of screen jumps. When the user advances from Phase 1 to Phase 2, the center workspace cross-fades (150ms) to the new phase content. Inline approve/revise actions — no modal dialogs for the primary workflow. The workspace is where the negotiation conversation happens.

---

## Story U04.1: Phase Content Container with Transitions

### EARS Requirement

> **When** the active phase changes, the system **shall** cross-fade the center workspace content from the previous phase to the next with a 150ms opacity + translateY transition, preserving scroll position when returning to a previously visited phase.

### Design by Contract

**Preconditions:**
- A session is active and a phase transition is triggered (by the harness or user navigation).

**Postconditions:**
- Outgoing phase content fades out (opacity 1→0, translateY 0→-8px) over 150ms.
- Incoming phase content fades in (opacity 0→1, translateY 8px→0) over 150ms, starting after outgoing completes.
- If the user navigates back to a completed phase, scroll position is restored from a cache.
- During transition, the workspace shows neither double content nor an empty flash.

**Invariants:**
- Transitions are interruptible — if a second phase change occurs during animation, the first is cancelled.
- Phase content components are lazily mounted (not rendered until visited).
- Completed phase content is kept in memory (not unmounted) to preserve state.

### Acceptance Criteria

- [ ] Phase transitions produce a smooth cross-fade.
- [ ] Scroll position is restored when revisiting a phase.
- [ ] No content flash or double-render during transitions.
- [ ] Rapid phase switching doesn't break the UI.

### How to Test

```typescript
test("phase transition renders new content", async () => {
  const { rerender } = render(<PhaseWorkspace phase={1} />);
  expect(screen.getByText("Classification")).toBeInTheDocument();
  rerender(<PhaseWorkspace phase={2} />);
  await waitFor(() => expect(screen.getByText("Postconditions")).toBeInTheDocument());
});
```

---

## Story U04.2: Phase Output Display

### EARS Requirement

> **When** a phase produces output (classifications, postconditions, preconditions, etc.), the system **shall** render the output as structured cards — one card per AC item — with the item's index, type badge, and the phase-specific data fields displayed in a scannable layout.

### Design by Contract

**Preconditions:**
- The active phase has completed at least one LLM call and produced structured output.
- The output is a JSON array of objects with phase-specific fields.

**Postconditions:**
- Each output item renders as a `Card` with:
  - Header: AC index (`Mono`), classification type (`Badge`), and actor name.
  - Body: phase-specific fields rendered as labeled key-value pairs.
  - For Phase 2 (postconditions): status code, response schema, forbidden fields.
  - For Phase 3 (preconditions): precondition text, enforcement point.
  - For Phase 4 (failure modes): trigger condition, expected error, severity.
- Cards are stacked vertically with `--space-3` gap.
- Each card has a subtle hover state (1px border becomes `--color-signal`).

**Invariants:**
- Cards maintain the same order as the AC items in the left rail.
- Empty/null fields render as `—` (em dash) in muted text.
- Cards are read-only during the output display state.

### Acceptance Criteria

- [ ] Each AC's output renders as a structured card.
- [ ] Phase-specific fields display correctly for phases 1-7.
- [ ] Hover state applies signal-color border.
- [ ] Empty fields show em dash.

### How to Test

```typescript
test("phase output renders classification cards", () => {
  render(<PhaseOutput phase="phase_1" data={mockClassifications} />);
  const cards = screen.getAllByRole("article");
  expect(cards).toHaveLength(mockClassifications.length);
  expect(screen.getByText("api_behavior")).toBeInTheDocument();
});
```

---

## Story U04.3: Inline Approve & Revise Actions

### EARS Requirement

> **When** a phase output is displayed, the system **shall** render an action bar at the bottom of the workspace with "Approve & Continue" (primary button) and "Revise" (secondary button), and **when** the user clicks "Revise", the system **shall** expand an inline text area for feedback without navigating away from the current view.

### Design by Contract

**Preconditions:**
- Phase output has been rendered and is awaiting developer decision.

**Postconditions:**
- "Approve & Continue" sends `POST /api/session/{id}/approve` and advances to the next phase.
- "Revise" expands a textarea (animated, 200ms slide-down) below the action bar.
- The textarea has placeholder text: "Describe what should change...".
- Submitting feedback sends `POST /api/session/{id}/feedback` with the text.
- During LLM revision, the action bar shows a progress indicator and disables buttons.
- After revision, the updated output replaces the current cards (with a subtle flash to indicate change).

**Invariants:**
- The action bar is sticky at the bottom of the center workspace.
- "Approve & Continue" is disabled if validation has not passed for the current phase.
- Revision feedback is appended to the session transcript.

### Acceptance Criteria

- [ ] "Approve & Continue" advances to the next phase.
- [ ] "Revise" expands inline textarea without navigation.
- [ ] Feedback submission triggers LLM revision and shows loading state.
- [ ] Updated output replaces previous with visual indicator.
- [ ] "Approve" is disabled when validation fails.

### How to Test

```typescript
test("approve advances phase", async () => {
  render(<PhaseActions sessionId="abc" phase={1} validationPassed={true} />);
  await userEvent.click(screen.getByRole("button", { name: /approve/i }));
  await waitFor(() => expect(mockApproveHandler).toHaveBeenCalled());
});

test("revise expands textarea", async () => {
  render(<PhaseActions sessionId="abc" phase={1} validationPassed={true} />);
  await userEvent.click(screen.getByRole("button", { name: /revise/i }));
  expect(screen.getByRole("textbox")).toBeInTheDocument();
});
```

---

## Story U04.4: Conversation Transcript View

### EARS Requirement

> **When** the user scrolls above the current phase output, the system **shall** display the conversation transcript for the current phase — showing alternating AI and developer messages with timestamps, role labels, and a visual distinction between system prompts, AI output, and developer feedback.

### Design by Contract

**Preconditions:**
- The session transcript contains entries for the active phase.

**Postconditions:**
- AI messages render with a `--color-graphite-50` background, left-aligned.
- Developer messages render with a `--color-bone` background, right-aligned.
- System messages (validation results, phase transitions) render centered with muted text.
- Each message shows: role icon, timestamp (`Mono`, `--text-xs`), and content.
- The transcript auto-scrolls to the bottom when new messages arrive.
- Old messages that were compacted (P3) show a "N earlier messages summarized" banner.

**Invariants:**
- Transcript is read-only.
- Auto-scroll is disabled when the user has manually scrolled up (re-enabled when they scroll to bottom).
- Messages render in chronological order.

### Acceptance Criteria

- [ ] AI and developer messages are visually distinct.
- [ ] Timestamps display correctly.
- [ ] Auto-scroll works but pauses when user scrolls up.
- [ ] Compacted messages show summary banner.

### How to Test

```typescript
test("transcript renders messages", () => {
  render(<Transcript entries={mockTranscript} />);
  const aiMessages = screen.getAllByTestId("message-ai");
  const devMessages = screen.getAllByTestId("message-developer");
  expect(aiMessages.length).toBeGreaterThan(0);
  expect(devMessages.length).toBeGreaterThan(0);
});
```
