# Epic U8: Quality, Performance, and Rollout

**Priority:** 8 (Medium-Low)  
**Implementation Target:** test coverage, performance budgets, build integration, and legacy cutover  
**Primary Outcome:** make the new workspace safe to ship and maintain

## Rationale

The new UI should not become a second prototype. Once the workflow is ported, the team needs confidence that the app is performant, tested, and shippable without breaking the backend or losing the ability to compare with the legacy interface during rollout.

---

## Story U8.1: Add component, integration, and contract tests for the new UI

### EARS Requirement

> **When** a frontend change modifies Operator Workspace behavior, the system **shall** have automated tests that catch regressions in layout logic, typed API integration, and the main operator workflows.

### Design by Contract

**Preconditions:**
- The React workspace and typed API layer exist.
- The project has a frontend test runner configured.

**Postconditions:**
- Key components have unit coverage.
- Query and mutation flows have integration coverage.
- Backend contract assumptions used by the UI are pinned in tests.

**Invariants:**
- Tests favor behavior over implementation details.
- Contract tests are updated deliberately when the backend changes.
- Critical flows have more than one layer of verification.

### Acceptance Criteria

- [ ] Component tests exist for shell, rails, phase surfaces, inspector tabs, and artifact viewers.
- [ ] Integration tests cover story selection, phase approval, revision, and pipeline launch.
- [ ] API contract tests validate the typed frontend adapters against representative backend payloads.
- [ ] CI can run frontend tests independently of browser e2e tests.

### How to Test

- Run the frontend unit and integration suite locally and in CI.
- Intentionally break a contract shape in a mock response and confirm tests fail.
- Re-run backend web tests to ensure the shared workflow still works end to end.

---

## Story U8.2: Cover the operator journey with browser-level end-to-end tests

### EARS Requirement

> **When** the application is built for review or release, the system **shall** have browser-level tests for the core operator journey from intake through verification.

### Design by Contract

**Preconditions:**
- The app can run against mock mode or deterministic test fixtures.
- A browser automation framework is configured.

**Postconditions:**
- The main operator flow is replayable in CI.
- Critical regressions in focus, layout, and streaming behavior are detectable.
- Mock mode keeps the tests deterministic.

**Invariants:**
- E2E tests target user-visible behavior, not internal implementation details.
- The happy path and one failure path are both covered.
- Streaming assertions tolerate expected timing variance without becoming flaky.

### Acceptance Criteria

- [ ] Browser tests cover manual entry, Jira intake fallback, negotiation progress, approval, and pipeline execution.
- [ ] Browser tests cover at least one failure mode such as stream error or mutation failure.
- [ ] Tests run in deterministic mock mode.
- [ ] Screenshots or traces are retained for failed runs.

### How to Test

- Run the browser suite locally against mock mode.
- Intentionally inject one failing API response and confirm the failure path is asserted.
- Review captured traces or screenshots from a failed test run.

---

## Story U8.3: Ship performance budgets and a safe rollout path

### EARS Requirement

> **When** the new workspace is prepared for release, the system **shall** meet explicit bundle and interaction budgets and support a reversible cutover from the legacy HTML frontend.

### Design by Contract

**Preconditions:**
- The workspace is feature-complete enough for evaluation.
- Build tooling can report bundle composition and asset sizes.

**Postconditions:**
- Initial bundle and route-chunk targets are defined and measured.
- Heavy inspector and artifact surfaces are code-split.
- The team can switch between legacy and new UI during rollout if needed.

**Invariants:**
- Bundle growth is tracked intentionally.
- Heavy features load on demand where appropriate.
- The backend API surface remains the same across the cutover.

### Acceptance Criteria

- [ ] Bundle-size budgets are defined for the shell and major lazy-loaded surfaces.
- [ ] Heavy surfaces such as artifact viewers and analyst tools are code-split.
- [ ] A feature flag, route split, or reversible deployment path exists for rollout.
- [ ] The legacy UI remains available until the new workspace is accepted.

### How to Test

- Run bundle analysis on production builds and compare against budgets.
- Verify lazy-loaded surfaces are not present in the initial shell chunk.
- Perform a manual cutover test between legacy and new UI entrypoints.
