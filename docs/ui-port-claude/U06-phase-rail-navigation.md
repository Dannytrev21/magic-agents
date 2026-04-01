# Epic U06: Phase Rail & Navigation

**Priority:** 6 (Medium — enhances workflow continuity)
**Depends On:** U02 (layout), U03 (phase timeline), U04 (phase workspace)

## Interaction Thesis

The phase rail is the spine of the negotiation workflow. It stays visible as the user works, provides at-a-glance progress, and enables non-linear navigation to revisit completed phases without losing context.

---

## Story U06.1: Sticky Phase Mini-Rail in Center Workspace

### EARS Requirement

> The system **shall** render a compact horizontal phase rail at the top of the center workspace — below the top bar — showing phase numbers 1–7 as clickable circles connected by a progress line, with completed phases filled, the active phase pulsing, and pending phases hollow.

### Design by Contract

**Preconditions:**
- A session is active with a known current phase.
- The center workspace is visible.

**Postconditions:**
- The mini-rail renders as a horizontal row of 7 circles (24px diameter) connected by 2px lines.
- Completed phases: filled `--color-graphite-600` circle with white checkmark.
- Active phase: filled `--color-signal` circle with a CSS pulse keyframe (scale 1→1.15→1, 2s loop).
- Pending phases: 2px `--color-graphite-300` outline circle, no fill.
- The connecting line between phases is solid up to the active phase, dashed after.
- Hovering a phase circle shows a tooltip with the phase name.
- Clicking a completed phase circle triggers a smooth workspace transition to that phase's output.

**Invariants:**
- The mini-rail is `position: sticky; top: 48px` (below the top bar).
- The mini-rail height is exactly 48px.
- The active phase circle is always centered within the available width.

### Acceptance Criteria

- [ ] Seven circles render with correct states (completed/active/pending).
- [ ] Active phase pulses with animation.
- [ ] Tooltips show phase names on hover.
- [ ] Clicking a completed phase navigates to its content.
- [ ] Mini-rail stays sticky during scroll.

### How to Test

```typescript
test("mini-rail renders phase states", () => {
  render(<PhaseMiniRail currentPhase={3} completedPhases={[1, 2]} />);
  const circles = screen.getAllByRole("button");
  expect(circles).toHaveLength(7);
  expect(circles[0]).toHaveAttribute("data-state", "completed");
  expect(circles[2]).toHaveAttribute("data-state", "active");
  expect(circles[3]).toHaveAttribute("data-state", "pending");
});
```

---

## Story U06.2: Breadcrumb Trail with Phase Context

### EARS Requirement

> The system **shall** render a breadcrumb trail below the mini-rail showing the navigation path: `{Jira Key} > Phase {N}: {Name} > {Sub-context}`, where sub-context is the current view within the phase (e.g., "Output", "Transcript", "Revising").

### Design by Contract

**Preconditions:**
- A session is active with a Jira key and current phase.

**Postconditions:**
- Breadcrumb segments are separated by `>` in `--color-graphite-400`.
- The Jira key segment is clickable and navigates to the AC overview.
- The phase segment shows the phase number and name.
- The sub-context segment reflects the current view state.
- Breadcrumbs use `--text-xs` with `--font-sans`.

**Invariants:**
- Breadcrumbs never wrap to a second line — they truncate the Jira key with ellipsis if needed.
- The last breadcrumb segment is not clickable (current location).

### Acceptance Criteria

- [ ] Breadcrumb renders with correct segments.
- [ ] Jira key is clickable.
- [ ] Sub-context updates when view changes.
- [ ] No line wrapping.

### How to Test

```typescript
test("breadcrumb renders path", () => {
  render(<Breadcrumb jiraKey="DEMO-001" phase={2} phaseName="Postconditions" subContext="Output" />);
  expect(screen.getByText("DEMO-001")).toBeInTheDocument();
  expect(screen.getByText("Phase 2: Postconditions")).toBeInTheDocument();
  expect(screen.getByText("Output")).toBeInTheDocument();
});
```

---

## Story U06.3: Phase Quick-Jump Keyboard Shortcuts

### EARS Requirement

> **When** the user presses `Ctrl+{1-7}` (or `Cmd+{1-7}` on macOS), the system **shall** navigate to the corresponding phase number if it is completed or active, and display a brief toast notification showing the phase name.

### Design by Contract

**Preconditions:**
- A session is active.
- The target phase is completed or active (not pending).

**Postconditions:**
- The center workspace transitions to the target phase.
- A toast notification appears at the bottom-center for 2 seconds: "Phase {N}: {Name}".
- If the target phase is pending, the shortcut is ignored and no toast appears.

**Invariants:**
- Shortcuts do not fire when an input/textarea is focused.
- Shortcuts work regardless of which panel is focused.

### Acceptance Criteria

- [ ] `Ctrl+1` navigates to Phase 1 (if completed/active).
- [ ] Pending phases are ignored.
- [ ] Toast notification appears and auto-dismisses.
- [ ] Shortcuts are suppressed during text input.

### How to Test

```typescript
test("keyboard shortcut navigates to phase", async () => {
  render(<App session={mockSessionAtPhase3} />);
  await userEvent.keyboard("{Control>}2{/Control}");
  await waitFor(() => expect(screen.getByText("Postconditions")).toBeInTheDocument());
  expect(screen.getByRole("status")).toHaveTextContent("Phase 2");
});
```
