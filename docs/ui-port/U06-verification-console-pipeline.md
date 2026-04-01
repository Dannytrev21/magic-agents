# Epic U6: Verification Console and Pipeline Execution

**Priority:** 6 (Medium)  
**Implementation Target:** EARS approval, artifact generation, pipeline execution, verdict review, and Jira feedback  
**Primary Outcome:** bring post-negotiation execution into the same operator surface

## Rationale

The Operator Workspace should not stop at negotiation. Once the operator approves EARS, the app needs to feel like a verification console: generate artifacts, watch execution, inspect verdicts, and push evidence back to Jira from the same surface.

---

## Story U6.1: Integrate the EARS approval gate and execution controls

### EARS Requirement

> **When** the session reaches post-negotiation review, the system **shall** require explicit EARS approval before enabling spec compilation and downstream execution controls.

### Design by Contract

**Preconditions:**
- The negotiation session is complete.
- EARS statements are present or the backend marks approval as available.

**Postconditions:**
- The approval action records backend approval metadata.
- Compile and execution controls remain unavailable until approval succeeds.
- Approval state is visible in the workspace after success.

**Invariants:**
- Approval status comes from backend confirmation.
- Disabled execution controls cannot be bypassed by local UI state.
- Approval UI remains close to the EARS review surface.

### Acceptance Criteria

- [ ] The EARS approval gate is rendered in the workspace after negotiation completes.
- [ ] Compile, generate-tests, and pipeline actions stay disabled until approval succeeds.
- [ ] Approval status shows approver and timestamp from the backend.
- [ ] Failed approvals leave execution controls disabled and display inline errors.

### How to Test

- Add integration tests for approval success and failure states.
- Verify execution actions stay disabled before approval.
- Manually confirm approval metadata remains visible after switching panes.

---

## Story U6.2: Add artifact viewers for specs and generated tests

### EARS Requirement

> **When** the operator compiles a spec or generates tests, the system **shall** display those artifacts in a readable viewer without leaving the verification console.

### Design by Contract

**Preconditions:**
- Compile or generate-tests mutations have succeeded.
- Artifact content is returned by the backend.

**Postconditions:**
- The operator can inspect spec YAML and generated tests inline.
- Artifacts can be revisited after other workspace actions.
- Heavy artifact panels can be loaded only when needed.

**Invariants:**
- Artifact content is read-only unless an explicit editor is introduced later.
- File paths and refs remain visually distinct in mono styling.
- The artifact viewer does not displace the primary workspace context unnecessarily.

### Acceptance Criteria

- [ ] Spec YAML is displayed in an inline artifact viewer after compile succeeds.
- [ ] Generated test output is displayed after test generation succeeds.
- [ ] Artifact viewers support long content without breaking layout.
- [ ] Artifact surfaces can be revisited from the workspace after the initial action.

### How to Test

- Add component tests for spec and test artifact viewers with long content.
- Add integration tests for compile and generate-tests success flows.
- Manually verify large artifact payloads remain readable in desktop and tablet widths.

---

## Story U6.3: Stream pipeline execution as a live console

### EARS Requirement

> **While** the verification pipeline is executing, the system **shall** stream step-level progress into the workspace so the operator can monitor execution without polling or leaving the page.

### Design by Contract

**Preconditions:**
- The pipeline streaming endpoint is available.
- A valid session is selected.

**Postconditions:**
- The workspace shows step-level events in order.
- Success and failure states are obvious.
- Final execution status is persisted after the stream ends.

**Invariants:**
- Events render in the order received from the backend stream.
- Stream failures degrade to a controlled error state.
- The operator can continue reading prior output while new events append.

### Acceptance Criteria

- [ ] The pipeline console connects to the SSE endpoint and renders step events live.
- [ ] Running, done, skipped, and failed states are visually distinct.
- [ ] Final pipeline status remains visible after completion.
- [ ] Stream errors are surfaced without crashing the workspace.

### How to Test

- Add integration tests that mock SSE event sequences for success and failure.
- Manually run the pipeline and verify the console appends new events correctly.
- Confirm the rest of the workspace remains responsive during streaming.

---

## Story U6.4: Present verdicts and Jira feedback in one post-run surface

### EARS Requirement

> **When** execution results are available, the system **shall** let the operator inspect per-AC verdicts and trigger Jira feedback from the same post-run surface.

### Design by Contract

**Preconditions:**
- Verdict data exists from evaluation or full-pipeline execution.
- Jira feedback endpoints are reachable when Jira is configured.

**Postconditions:**
- The post-run surface summarizes overall results before the per-AC details.
- The operator can inspect pass/fail outcomes per AC with evidence.
- Jira feedback can be triggered without leaving the workspace.
- Feedback results are explicit about what changed in Jira.
- Empty and failed execution states remain actionable in the same surface.

**Invariants:**
- Verdict summaries do not hide per-evidence detail.
- Jira update state is session-scoped and idempotent from the UI perspective.
- Missing Jira configuration is surfaced as a clear limitation rather than a silent no-op.
- Post-run states remain in the workspace rather than redirecting to separate routes.

### Acceptance Criteria

- [ ] The post-run surface includes a concise overall results summary before the detailed verdict list.
- [ ] The post-run surface shows pass/fail verdicts grouped by AC.
- [ ] Evidence refs and details are visible for each verdict.
- [ ] Failed or incomplete results are surfaced ahead of passed results where helpful for operator review.
- [ ] Jira feedback can be triggered from the verification console.
- [ ] The UI reports whether checkboxes were ticked and evidence was posted.
- [ ] Empty-result and pipeline-error states provide clear next actions in the same surface.

### How to Test

- Add integration tests for verdict rendering and Jira feedback success/failure responses.
- Verify non-configured Jira states disable or explain the feedback action.
- Add tests for empty-result and pipeline-error post-run states.
- Manually run a mock-mode session through verdict review and Jira feedback.
