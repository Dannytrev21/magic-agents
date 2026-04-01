# Epic U02: Three-Panel Layout Shell

**Priority:** 2 (High — structural skeleton for all content)
**Depends On:** U01 (tokens, primitives)

## Content Plan

Left rail (280px default) for story intake and session state. Center workspace (fluid) for the active phase. Right inspector (320px default) for evidence, scan results, and traceability. All three panels are independently scrollable with sticky headers.

---

## Story U02.1: AppShell with Three-Panel Grid

### EARS Requirement

> The system **shall** render an `AppShell` layout using CSS Grid with three columns — a collapsible left rail (280px), a fluid center workspace (`1fr`), and a collapsible right inspector (320px) — with a fixed 48px top bar spanning the full width.

### Design by Contract

**Preconditions:**
- Design tokens are loaded (U01.2).
- The viewport is at least 1024px wide.

**Postconditions:**
- The layout uses `display: grid` with `grid-template-columns: var(--rail-width) 1fr var(--inspector-width)`.
- The top bar is `position: sticky; top: 0` with `z-index: 10` and `--color-graphite-900` background.
- Each panel has `overflow-y: auto` and independent scroll position.
- Panels render their `children` prop.
- A 1px `--color-graphite-200` border separates each panel.

**Invariants:**
- The top bar never scrolls out of view.
- Panel borders are purely visual separators — no interactive resize handles (resize is via collapse toggle).
- Minimum center workspace width is 480px regardless of panel state.

### Acceptance Criteria

- [ ] Three-column grid renders with correct widths.
- [ ] Top bar stays fixed during scroll.
- [ ] Panels scroll independently.
- [ ] Center workspace never shrinks below 480px.

### How to Test

```typescript
test("AppShell renders three panels", () => {
  render(
    <AppShell
      topBar={<div>Top</div>}
      leftRail={<div>Left</div>}
      center={<div>Center</div>}
      rightInspector={<div>Right</div>}
    />
  );
  expect(screen.getByText("Left")).toBeInTheDocument();
  expect(screen.getByText("Center")).toBeInTheDocument();
  expect(screen.getByText("Right")).toBeInTheDocument();
});
```

---

## Story U02.2: Panel Collapse & Expand

### EARS Requirement

> **When** the user clicks a panel toggle button in the top bar, the system **shall** collapse the corresponding panel (left rail or right inspector) to 0px width with a 200ms ease-out transition, and expand it back to its default width on a second click.

### Design by Contract

**Preconditions:**
- The `AppShell` is rendered with all three panels.
- Toggle buttons exist in the top bar for left and right panels.

**Postconditions:**
- Collapsing animates `grid-template-columns` from the panel's width to `0px` over 200ms.
- The collapsed panel's content is hidden with `overflow: hidden`.
- The center workspace grows to fill the freed space.
- Panel state (collapsed/expanded) persists in `localStorage` across page reloads.
- Toggle icons rotate 180° when panel state changes (chevron direction indicator).

**Invariants:**
- Both panels can be collapsed simultaneously, leaving only the center workspace.
- Collapse animation never causes layout jank (no reflow during transition).
- Keyboard shortcut `Cmd+[` toggles left rail, `Cmd+]` toggles right inspector.

### Acceptance Criteria

- [ ] Clicking left toggle collapses/expands the left rail with smooth animation.
- [ ] Clicking right toggle collapses/expands the right inspector.
- [ ] Panel state persists in `localStorage`.
- [ ] Keyboard shortcuts work.
- [ ] Both panels can be collapsed at once.

### How to Test

```typescript
test("left panel collapse toggle", async () => {
  render(<AppShell ... />);
  const toggle = screen.getByLabelText("Toggle left panel");
  await userEvent.click(toggle);
  // Panel should be collapsed
  expect(localStorage.getItem("panel-left")).toBe("collapsed");
});
```

---

## Story U02.3: Responsive Breakpoint Behavior

### EARS Requirement

> **While** the viewport width is below 1024px, the system **shall** auto-collapse the right inspector, and **while** below 768px, the system **shall** auto-collapse both side panels and show a bottom tab bar for panel switching.

### Design by Contract

**Preconditions:**
- The `AppShell` is rendered.

**Postconditions:**
- At < 1024px: right inspector auto-collapses; left rail remains open; a toggle appears to restore the inspector as an overlay.
- At < 768px: both panels collapse; a bottom tab bar with 3 tabs (Story, Workspace, Evidence) appears; tapping a tab shows that panel as the full-width content.
- At ≥ 1024px: three-column layout is restored from persisted state.

**Invariants:**
- Breakpoint transitions do not lose panel scroll position.
- The bottom tab bar is 56px tall with `--color-graphite-900` background.
- Active tab has a 2px `--color-signal` top border.

### Acceptance Criteria

- [ ] Right inspector auto-collapses below 1024px.
- [ ] Both panels collapse and bottom tabs appear below 768px.
- [ ] Tab switching shows the correct panel full-width.
- [ ] Restoring to ≥ 1024px returns to three-column layout.

### How to Test

```typescript
test("responsive collapse at 768px", () => {
  // Set viewport to 768px
  window.innerWidth = 768;
  fireEvent(window, new Event("resize"));
  render(<AppShell ... />);
  expect(screen.getByRole("tablist")).toBeInTheDocument();
});
```

---

## Story U02.4: Top Bar with Session Context

### EARS Requirement

> The system **shall** render a top bar containing: the app logo/name ("SPECify"), the current Jira key as a `Mono` badge, the current phase name, panel toggle buttons, and a session status indicator (connected/disconnected).

### Design by Contract

**Preconditions:**
- A session is active with a Jira key and current phase.

**Postconditions:**
- Logo renders left-aligned with `--font-sans` at `--text-lg`, weight 600.
- Jira key renders as a `Mono` badge with `--color-graphite-700` background.
- Phase name renders center-aligned with `--text-sm`.
- Panel toggles render right-aligned with icon buttons.
- Status indicator is a 8px circle: green for connected, amber for reconnecting, red for disconnected.

**Invariants:**
- Top bar height is exactly 48px.
- All elements are vertically centered.
- Top bar content does not wrap — it truncates with ellipsis if space is constrained.

### Acceptance Criteria

- [ ] All five elements render in the correct positions.
- [ ] Jira key uses monospace font.
- [ ] Status indicator reflects connection state.
- [ ] Top bar is 48px tall.

### How to Test

```typescript
test("top bar renders session context", () => {
  render(<TopBar jiraKey="DEMO-001" phase="Phase 2: Postconditions" connected={true} />);
  expect(screen.getByText("DEMO-001")).toBeInTheDocument();
  expect(screen.getByText("Phase 2: Postconditions")).toBeInTheDocument();
});
```
