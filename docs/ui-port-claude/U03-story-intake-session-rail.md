# Epic U03: Story Intake & Session Rail (Left Panel)

**Priority:** 3 (High — entry point for all user workflows)
**Depends On:** U01 (primitives), U02 (left rail panel)

## Content Plan

The left rail is the user's command center: pick a Jira story, see its acceptance criteria, view the phase progress timeline, and monitor session health (budget, cost, duration). It should feel like a calm mission control sidebar.

---

## Story U03.1: Jira Story Picker

### EARS Requirement

> The system **shall** render a story picker at the top of the left rail with a text input for entering a Jira key (e.g., `DEMO-001`) and a "Load" button that fetches the story from the backend via `POST /api/session/start`, and **when** the story loads successfully, the system **shall** display the story title and transition to the AC overview.

### Design by Contract

**Preconditions:**
- The FastAPI backend is running and reachable.
- The left rail panel is visible.

**Postconditions:**
- The input accepts alphanumeric Jira keys with a hyphen (e.g., `PROJ-123`).
- Pressing Enter or clicking "Load" calls `POST /api/session/start` with the key.
- On success: the input collapses into a compact header showing the key and title; the AC overview renders below.
- On error: an inline error message appears below the input in `--color-error`.
- Loading state: the button shows a spinner and is disabled during the request.

**Invariants:**
- The input validates format client-side before sending (regex: `^[A-Z]+-\d+$`).
- Only one session can be active at a time; starting a new one replaces the current.

### Acceptance Criteria

- [ ] Input accepts valid Jira keys and rejects invalid formats.
- [ ] Loading state shows spinner and disables input.
- [ ] Success transitions to AC overview with story title.
- [ ] Error shows inline message without clearing the input.

### How to Test

```typescript
test("story picker loads story", async () => {
  server.use(rest.post("/api/session/start", (req, res, ctx) =>
    res(ctx.json({ session_id: "abc", title: "Add dog endpoint" }))
  ));
  render(<StoryPicker />);
  await userEvent.type(screen.getByRole("textbox"), "DEMO-001");
  await userEvent.click(screen.getByRole("button", { name: /load/i }));
  await waitFor(() => expect(screen.getByText("Add dog endpoint")).toBeInTheDocument());
});
```

---

## Story U03.2: Acceptance Criteria Checklist

### EARS Requirement

> **When** a story is loaded, the system **shall** render its acceptance criteria as a vertical checklist where each AC item shows its index, text, classification badge (if classified), and a verdict indicator (pending/pass/fail), and the list **shall** scroll independently within the rail.

### Design by Contract

**Preconditions:**
- A session is active with `raw_acceptance_criteria` populated.

**Postconditions:**
- Each AC renders with: index number in `Mono`, AC text in `Text`, an optional classification `Badge` (e.g., "api_behavior", "security_invariant"), and a verdict dot (gray=pending, green=pass, red=fail).
- Clicking an AC item selects it and highlights it with a 2px left border in `--color-signal`.
- The selected AC scrolls to its context in the center workspace.
- The list is scrollable with a max-height of `calc(100vh - 300px)`.

**Invariants:**
- AC items maintain their Jira-original ordering.
- Verdict indicators update in real-time as test results arrive.
- Long AC text wraps but is truncated to 3 lines with "..." and a tooltip for the full text.

### Acceptance Criteria

- [ ] AC items render with index, text, badge, and verdict.
- [ ] Clicking an AC highlights it and scrolls center workspace.
- [ ] Verdicts update when test results arrive.
- [ ] Long text truncates with tooltip.

### How to Test

```typescript
test("AC checklist renders items", () => {
  render(<ACChecklist items={mockACs} classifications={mockClassifications} />);
  expect(screen.getAllByRole("listitem")).toHaveLength(mockACs.length);
  expect(screen.getByText("AC[1]")).toBeInTheDocument();
});
```

---

## Story U03.3: Phase Progress Timeline

### EARS Requirement

> The system **shall** render a vertical timeline below the AC checklist showing all 7 negotiation phases, where each phase displays its name, status (pending/active/complete/error), and duration, with the active phase visually emphasized using the signal color.

### Design by Contract

**Preconditions:**
- A session is active and the harness has a known current phase.

**Postconditions:**
- The timeline renders 7 phase nodes connected by vertical lines.
- Completed phases: solid `--color-graphite-400` line and checkmark icon.
- Active phase: `--color-signal` circle with a subtle pulse animation, bold label.
- Pending phases: dashed `--color-graphite-200` line and hollow circle.
- Error phases: `--color-error` circle with an X icon.
- Each phase node shows: phase name, status badge, and duration (e.g., "2m 14s").
- Clicking a completed phase scrolls the center workspace to that phase's output.

**Invariants:**
- Only one phase can be "active" at a time.
- The timeline is read-only — users cannot skip or reorder phases.
- The active phase auto-scrolls into view within the rail.

### Acceptance Criteria

- [ ] All 7 phases render in order with correct status indicators.
- [ ] Active phase has signal color and pulse animation.
- [ ] Completed phases show duration.
- [ ] Clicking a completed phase navigates to its output.

### How to Test

```typescript
test("timeline shows active phase", () => {
  render(<PhaseTimeline currentPhase={2} phases={mockPhases} />);
  const activeNode = screen.getByText("Postconditions").closest("[data-status]");
  expect(activeNode).toHaveAttribute("data-status", "active");
});
```

---

## Story U03.4: Session Health Indicators

### EARS Requirement

> The system **shall** render a compact health bar at the bottom of the left rail showing: token budget utilization (progress bar with percentage), API call count, wall clock time, and estimated cost in USD — all updated in real-time from SSE events.

### Design by Contract

**Preconditions:**
- A session is active with a `BackPressureController` tracking usage (P1).
- SSE events include `budget_warning` and usage updates.

**Postconditions:**
- Token utilization renders as a horizontal progress bar: green (0-70%), amber (70-90%), red (90%+).
- API call count renders as `Mono` text: "12 / 50 calls".
- Wall clock time renders as `Mono` text: "4m 32s".
- Estimated cost renders as `Mono` text: "$0.42".
- When a `budget_warning` event arrives, the health bar flashes amber for 2 seconds.

**Invariants:**
- Health indicators update every time an SSE usage event arrives (no polling).
- The health bar is always visible at the bottom of the rail (sticky footer).
- Values gracefully show "—" when no session is active.

### Acceptance Criteria

- [ ] Progress bar reflects token utilization with correct color thresholds.
- [ ] API calls, time, and cost display correctly.
- [ ] Budget warning causes a visual flash.
- [ ] Displays "—" when no session is active.

### How to Test

```typescript
test("health bar shows budget utilization", () => {
  render(<SessionHealth usage={{ tokens_used: 350000, max_tokens: 500000, api_calls: 12, ... }} />);
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "70");
  expect(screen.getByText("12 / 50 calls")).toBeInTheDocument();
});
```
