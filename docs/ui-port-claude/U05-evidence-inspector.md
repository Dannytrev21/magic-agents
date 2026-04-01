# Epic U05: Evidence Inspector (Right Panel)

**Priority:** 5 (Medium-High — critical for traceability and trust)
**Depends On:** U01 (primitives), U02 (right inspector panel), U04 (phase output context)

## Content Plan

The right inspector shows the "proof" side of the pipeline. When a user selects an AC item or requirement, the inspector shows the evidence chain: scan results from the codebase explorer, the compiled spec contract, generated test code, and test verdicts. It is the traceability window.

---

## Story U05.1: Inspector Tab System

### EARS Requirement

> The system **shall** render the right inspector with a sticky tab bar containing four tabs — "Scan", "Spec", "Tests", "Trace" — where clicking a tab swaps the inspector content with a 120ms crossfade and the active tab is underlined with `--color-signal`.

### Design by Contract

**Preconditions:**
- The right inspector panel is visible (not collapsed).
- At least one tab has content to display.

**Postconditions:**
- Tabs render horizontally in the sticky header of the right panel.
- Active tab has a 2px bottom border in `--color-signal` and bold text.
- Inactive tabs have `--color-graphite-500` text.
- Switching tabs cross-fades content (opacity transition, 120ms).
- Tab state persists within the session (survives panel collapse/expand).

**Invariants:**
- Tabs are keyboard-navigable (arrow keys to switch, Enter to select).
- Tab content is lazily rendered (only the active tab's content is in the DOM).
- The tab bar never scrolls — it is fixed at the top of the inspector.

### Acceptance Criteria

- [ ] Four tabs render with correct labels.
- [ ] Active tab has signal-color underline.
- [ ] Tab switching produces smooth crossfade.
- [ ] Keyboard navigation works.

### How to Test

```typescript
test("inspector tabs switch content", async () => {
  render(<Inspector ... />);
  expect(screen.getByText("Scan")).toBeInTheDocument();
  await userEvent.click(screen.getByText("Spec"));
  await waitFor(() => expect(screen.getByTestId("spec-panel")).toBeInTheDocument());
});
```

---

## Story U05.2: Codebase Scan Results View

### EARS Requirement

> **When** the "Scan" tab is active and a codebase exploration has been performed (P11), the system **shall** display the `StackProfile` (language, framework, build tool, confidence) and `CodebaseIndex` summary (endpoint count, model count, test pattern count) as a structured readout, with expandable sections for endpoint details and model fields.

### Design by Contract

**Preconditions:**
- The explorer has been run and results are available on the session.

**Postconditions:**
- Stack profile renders as a compact header: "Java 17 / Spring Boot 3.2 / Gradle" with a confidence badge.
- Summary stats render as a row of metric cards: endpoints, models, DTOs, test files.
- Expandable "Endpoints" section lists each endpoint as `{METHOD} {path} → {handler}` in `Mono` font.
- Expandable "Models" section lists each entity with its field names.
- If no scan has been performed, a CTA ("Scan Codebase") is shown instead.

**Invariants:**
- Expandable sections default to collapsed.
- The scan view is read-only.
- Long lists (>20 items) show "and N more..." with a "Show all" toggle.

### Acceptance Criteria

- [ ] Stack profile renders with correct metadata.
- [ ] Summary stats display endpoint/model/test counts.
- [ ] Expandable sections work.
- [ ] "Scan Codebase" CTA appears when no scan exists.

### How to Test

```typescript
test("scan results display stack profile", () => {
  render(<ScanResults profile={mockProfile} index={mockIndex} />);
  expect(screen.getByText(/spring-boot/i)).toBeInTheDocument();
  expect(screen.getByText(/endpoints/i)).toBeInTheDocument();
});
```

---

## Story U05.3: Spec Contract Viewer

### EARS Requirement

> **When** the "Spec" tab is active and a compiled spec exists for the current story, the system **shall** render the spec requirements as a list of requirement cards, each showing `REQ-NNN` ID, type badge, contract summary (preconditions, postconditions, failure modes), and verification routing.

### Design by Contract

**Preconditions:**
- A compiled spec YAML exists in `.verify/specs/{jira_key}.yaml`.
- The spec has been loaded into the session.

**Postconditions:**
- Each requirement renders as a card with:
  - Header: `Mono` ID (e.g., `REQ-001`), type `Badge`, linked AC index.
  - Contract section: preconditions as a bullet list, postcondition status code and schema, failure modes count.
  - Routing section: skill name, framework, output path in `Mono`.
- Clicking a requirement card highlights the corresponding AC in the left rail.
- If no spec exists, a message "Spec not yet compiled" is shown.

**Invariants:**
- Requirements maintain spec ordering.
- Contract details are read-only.

### Acceptance Criteria

- [ ] Requirement cards render with all contract elements.
- [ ] Clicking a requirement highlights the corresponding AC.
- [ ] No-spec state shows appropriate message.

### How to Test

```typescript
test("spec viewer renders requirements", () => {
  render(<SpecViewer spec={mockSpec} />);
  expect(screen.getByText("REQ-001")).toBeInTheDocument();
  expect(screen.getByText("api_behavior")).toBeInTheDocument();
});
```

---

## Story U05.4: Traceability Matrix

### EARS Requirement

> **When** the "Trace" tab is active, the system **shall** render an end-to-end traceability matrix showing the chain from AC checkbox → classification → requirement → EARS statement → test tag → verdict, with each link clickable to navigate to the corresponding artifact.

### Design by Contract

**Preconditions:**
- The spec has a `traceability_map` section populated.
- At least some verdicts are available.

**Postconditions:**
- The matrix renders as a table with columns: AC, Classification, Requirement, EARS, Test Tag, Verdict.
- Each cell is a clickable link that navigates to the corresponding view (AC in left rail, requirement in Spec tab, etc.).
- Verdict cells display pass/fail/pending with color-coded badges.
- Rows with failed verdicts are highlighted with a subtle `--color-error` left border.
- If traceability is incomplete, missing cells show a warning icon.

**Invariants:**
- The matrix updates in real-time as test results arrive.
- Sorting by verdict (fail first) is the default.
- The table is horizontally scrollable if columns overflow.

### Acceptance Criteria

- [ ] Traceability matrix renders all columns.
- [ ] Clickable links navigate to correct views.
- [ ] Failed rows are highlighted.
- [ ] Missing cells show warning icons.

### How to Test

```typescript
test("traceability matrix renders chain", () => {
  render(<TraceabilityMatrix traceMap={mockTraceMap} verdicts={mockVerdicts} />);
  expect(screen.getByText("AC[1]")).toBeInTheDocument();
  expect(screen.getByText("REQ-001")).toBeInTheDocument();
  expect(screen.getByText("PASS")).toBeInTheDocument();
});
```
