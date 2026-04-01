# Epic U08: Verification & Results Dashboard

**Priority:** 8 (Medium — the payoff screen after negotiation completes)
**Depends On:** U01-U05 (all prior UI), P1 (cost), P5 (permissions)

## Content Plan

After all 7 phases complete and verification artifacts are generated, the center workspace transitions to a results dashboard showing test execution results, verdicts per AC, coverage metrics, and the final spec. This is the "proof" view — the deliverable that goes back to Jira.

---

## Story U08.1: Results Summary Header

### EARS Requirement

> **When** the evaluation phase completes and verdicts are available, the system **shall** render a results summary header at the top of the center workspace showing: overall pass/fail status (large badge), AC pass rate (e.g., "4/5 AC verified"), total test count, and a "Push to Jira" action button.

### Design by Contract

**Preconditions:**
- All negotiation phases are complete.
- The evaluator has produced verdicts for at least one AC.

**Postconditions:**
- Overall status: large `Badge` — green "ALL PASS" if all ACs pass, red "FAILURES" if any fail, amber "PARTIAL" if some are untested.
- Pass rate: `Text` with fraction and percentage (e.g., "4/5 (80%)").
- Test count: total tests run, passed, failed, skipped.
- "Push to Jira" button (`Button` primary variant) calls `POST /api/session/{id}/push-verdicts`.
- If already pushed, the button shows "Pushed ✓" in disabled state.

**Invariants:**
- The summary header is visible without scrolling (above the fold).
- "Push to Jira" requires explicit user click (never auto-pushed).

### Acceptance Criteria

- [ ] Overall status badge displays correct state.
- [ ] Pass rate fraction and percentage are accurate.
- [ ] Test count summary is accurate.
- [ ] "Push to Jira" triggers the correct API call.
- [ ] Button disables after successful push.

### How to Test

```typescript
test("results header shows pass rate", () => {
  render(<ResultsHeader verdicts={mockVerdicts} totalTests={12} passed={10} failed={2} />);
  expect(screen.getByText("FAILURES")).toBeInTheDocument();
  expect(screen.getByText("4/5 (80%)")).toBeInTheDocument();
});

test("push to jira calls API", async () => {
  render(<ResultsHeader ... />);
  await userEvent.click(screen.getByRole("button", { name: /push to jira/i }));
  expect(mockPushHandler).toHaveBeenCalled();
});
```

---

## Story U08.2: Verdict Cards per AC

### EARS Requirement

> The system **shall** render a verdict card for each acceptance criterion showing: AC text, verdict (pass/fail/untested), evidence summary (test tags executed, config validations run), and a link to the generated test file, with failed verdicts sorted to the top.

### Design by Contract

**Preconditions:**
- Verdicts are available from the evaluator.
- Generated test files exist on disk.

**Postconditions:**
- Each verdict card renders as a `Card` with:
  - Left border: green for pass, red for fail, gray for untested.
  - Header: AC index and text.
  - Evidence: list of test tags executed with pass/fail badges.
  - Link: file path to generated test (clickable to open in the "Tests" inspector tab).
- Failed verdicts render before passed verdicts.
- Untested ACs render at the bottom with a warning icon.

**Invariants:**
- Verdict cards maintain a 1:1 mapping with acceptance criteria.
- Cards are read-only.

### Acceptance Criteria

- [ ] Each AC has a verdict card.
- [ ] Failed verdicts appear first.
- [ ] Evidence shows test tag results.
- [ ] File link navigates to the Tests inspector tab.

### How to Test

```typescript
test("verdict cards render in fail-first order", () => {
  render(<VerdictCards verdicts={[passVerdict, failVerdict]} />);
  const cards = screen.getAllByRole("article");
  expect(cards[0]).toHaveAttribute("data-verdict", "fail");
  expect(cards[1]).toHaveAttribute("data-verdict", "pass");
});
```

---

## Story U08.3: Cost Summary & Session Report

### EARS Requirement

> The system **shall** render a collapsible "Session Report" section below the verdict cards showing: total negotiation cost (USD), per-phase cost breakdown (table), total duration, token usage, and a "Download Report" button that exports the full session data as a JSON file.

### Design by Contract

**Preconditions:**
- Cost data is available from the `BackPressureController` (P1/P7).
- The session has completed all phases.

**Postconditions:**
- Cost summary renders as a compact row: "$1.24 total | 7 phases | 4m 32s | 142K tokens".
- Per-phase breakdown renders as a table: Phase | API Calls | Tokens | Duration | Cost.
- "Download Report" exports a JSON file containing: session ID, Jira key, all phase cost reports, verdicts, spec YAML, and timestamp.
- The section defaults to collapsed (expandable with a chevron toggle).

**Invariants:**
- Cost is calculated using the rates from the session (not live API pricing).
- The downloaded JSON is self-contained (all data needed to reproduce the session).
- File name follows pattern: `specify-report-{JIRA_KEY}-{date}.json`.

### Acceptance Criteria

- [ ] Cost summary renders with correct totals.
- [ ] Per-phase table shows breakdown.
- [ ] Download button produces a valid JSON file.
- [ ] Section is collapsible.

### How to Test

```typescript
test("cost summary displays total", () => {
  render(<SessionReport costSummary={mockCostSummary} />);
  expect(screen.getByText(/\$1\.24/)).toBeInTheDocument();
  expect(screen.getByText("142K tokens")).toBeInTheDocument();
});

test("download report produces JSON", async () => {
  render(<SessionReport ... />);
  const downloadSpy = jest.spyOn(document, "createElement");
  await userEvent.click(screen.getByRole("button", { name: /download/i }));
  expect(downloadSpy).toHaveBeenCalledWith("a");
});
```

---

## Story U08.4: Empty & Error States

### EARS Requirement

> **If** no verdicts are available (pipeline not yet run), the system **shall** display an empty state with an illustration, explanatory text, and a "Run Pipeline" CTA, and **if** the pipeline failed mid-execution, the system **shall** display the error message with a "Retry" button.

### Design by Contract

**Preconditions:**
- The results dashboard is rendered but no verdicts exist, or the pipeline encountered an error.

**Postconditions:**
- Empty state: centered layout with a muted illustration (spec document icon), headline "No results yet", body text explaining the next step, and a "Run Pipeline" primary button.
- Error state: centered layout with error icon in `--color-error`, the error message, and a "Retry" secondary button.
- Both states render within the center workspace (no separate route).

**Invariants:**
- The empty state CTA triggers `POST /api/session/{id}/run-pipeline`.
- The error state shows the actual error message (not a generic fallback).
- Both states are visually consistent with the design token system.

### Acceptance Criteria

- [ ] Empty state renders with illustration and CTA.
- [ ] Error state renders with actual error message.
- [ ] "Run Pipeline" triggers the correct API call.
- [ ] "Retry" re-runs the pipeline.

### How to Test

```typescript
test("empty state renders CTA", () => {
  render(<ResultsDashboard verdicts={[]} error={null} />);
  expect(screen.getByText("No results yet")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /run pipeline/i })).toBeInTheDocument();
});

test("error state renders message", () => {
  render(<ResultsDashboard verdicts={[]} error="Connection timeout to Jira" />);
  expect(screen.getByText("Connection timeout to Jira")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
});
```
