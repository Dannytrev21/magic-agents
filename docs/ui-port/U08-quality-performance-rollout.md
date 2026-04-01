# Epic U8: Quality, Performance, and Rollout

**Priority:** 8 (Medium-Low)  
**Implementation Target:** test coverage, performance budgets, build integration, and legacy cutover  
**Primary Outcome:** make the new workspace safe to ship and maintain

## Rationale

The new UI should not become a second prototype. Once the workflow is ported, the team needs confidence that the app is performant, tested, and shippable without breaking the backend or losing the ability to compare with the legacy interface during rollout.

## Implementation Status

- `U8.1` is implemented with new left-rail component coverage, page-level integration coverage, and expanded typed API contract tests. `npm run test:ui` and `npm run test:ci` both pass.
- `U8.2` is implemented with Playwright specs for the deterministic manual-entry happy path and a mocked pipeline failure path, plus retained traces/screenshots on failure. The harness is environment-selectable, and the remote-browser path is now first-class: `playwright run-server` can host the browser outside Codex while `npm run test:e2e` or `npm run test:e2e:remote` connects to it. Direct browser launch inside Codex-hosted macOS can still fail, but remote-browser execution is now validated.
- `U8.3` is implemented with a lazy-loaded verification console chunk, manifest-backed bundle budgets, and a reversible FastAPI frontend switch via `MAGIC_AGENTS_FRONTEND_MODE` or the `frontend` query parameter. The 2026-04-01 verification pass restored the shell CSS budget to green by simplifying decorative chrome instead of raising thresholds, and the targeted backend rollout tests pass.

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

- [x] Component tests exist for shell, rails, phase surfaces, inspector tabs, and artifact viewers.
- [x] Integration tests cover story selection, phase approval, revision, and pipeline launch.
- [x] API contract tests validate the typed frontend adapters against representative backend payloads.
- [x] CI can run frontend tests independently of browser e2e tests.

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

- [x] Browser tests cover manual entry, Jira intake fallback, negotiation progress, approval, and pipeline execution.
- [x] Browser tests cover at least one failure mode such as stream error or mutation failure.
- [x] Tests run in deterministic mock mode.
- [x] Screenshots or traces are retained for failed runs.

### How to Test

- Run the browser suite locally against mock mode.
- Intentionally inject one failing API response and confirm the failure path is asserted.
- Review captured traces or screenshots from a failed test run.
- Use `npm run test:e2e` for the default Chromium path in this repo, or `npm run test:e2e:chromium`, `npm run test:e2e:firefox`, and `npm run test:e2e:webkit` when isolating host-specific browser failures.
- For Codex-hosted runs, start `npm run test:e2e:server` outside Codex and then run `npm run test:e2e:remote` or `PW_TEST_CONNECT_WS_ENDPOINT=ws://127.0.0.1:3000/ npm run test:e2e` from Codex.
- If the app under test is already running elsewhere, set `PW_SKIP_WEBSERVER=1` and point Playwright at it with `PW_BASE_URL=http://host:port`.

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

- [x] Bundle-size budgets are defined for the shell and major lazy-loaded surfaces.
- [x] Heavy surfaces such as artifact viewers and analyst tools are code-split.
- [x] A feature flag, route split, or reversible deployment path exists for rollout.
- [x] The legacy UI remains available until the new workspace is accepted.

### How to Test

- Run bundle analysis on production builds and compare against budgets.
- Verify lazy-loaded surfaces are not present in the initial shell chunk.
- Perform a manual cutover test between legacy and new UI entrypoints.
- Verify `/?frontend=legacy` still serves [`/Users/dannytrevino/development/magic-agents/static/index.html`](/Users/dannytrevino/development/magic-agents/static/index.html) while the default root continues to prefer the built React bundle when present.
- Re-run `npm run test:ci` and confirm the budget report keeps the workspace shell under 33.5 kB raw / 7 kB gzip without editing `ui/config/bundle-budgets.json`.
