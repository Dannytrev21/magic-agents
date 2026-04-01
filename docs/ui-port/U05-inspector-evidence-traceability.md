# Epic U5: Inspector, Evidence, and Traceability

**Priority:** 5 (Medium-High)  
**Implementation Target:** right-side inspector for scan data, traceability, critique, and planning surfaces  
**Primary Outcome:** make the product's differentiator - evidence-backed traceability - visible during work, not only after the fact

## Rationale

Magic Agents is not only a phase-by-phase chat tool. Its value is that each acceptance criterion can be traced into contracts, verification refs, and final verdicts. The right inspector should make that evidence tangible while the operator is working, not bury it at the end of the flow.

---

## Story U5.1: Build a tabbed inspector for evidence surfaces

### EARS Requirement

> **While** the operator works in the center pane, the system **shall** provide a persistent right inspector with dedicated surfaces for evidence and supporting context.

### Design by Contract

**Preconditions:**
- The workspace shell supports a persistent inspector region.
- Inspector content can vary independently from the center pane.

**Postconditions:**
- The inspector can show scan results, traceability, planner output, critique, and artifact context.
- Changing inspector tabs does not reset the active center-pane workflow.
- Heavy inspector views can load on demand.

**Invariants:**
- Inspector state is subordinate to the selected story or session.
- The inspector never becomes the primary visual weight over the center pane.
- Hidden inspector tabs do not eagerly mount expensive content unless needed.

### Acceptance Criteria

- [x] The right rail supports at least scan, traceability, and planning/critique tabs.
- [x] Switching inspector tabs does not reset draft input in the center pane.
- [x] Inspector tabs can be lazy-loaded when they contain heavier artifact viewers.
- [x] The selected inspector tab is visually clear and keyboard reachable.

### How to Test

- Add component tests for tab switching and state preservation.
- Add a lazy-loading test for heavier inspector surfaces.
- Manually verify the center pane remains stable while switching tabs.

---

## Story U5.2: Integrate codebase scan output into the inspector

### EARS Requirement

> **When** the operator runs a codebase scan, the system **shall** display scan status, summary output, and scan-derived context in the inspector without displacing the active phase review.

### Design by Contract

**Preconditions:**
- The scan endpoints are available.
- The workspace knows which project root is being scanned.

**Postconditions:**
- Scan execution status is visible in the workspace.
- Scan summary content is persisted in the inspector for later reference.
- Scan failures remain actionable and non-destructive.

**Invariants:**
- Scan output is associated with the current story or session context where applicable.
- Failed scans do not blank existing inspector data.
- The operator can continue reviewing the active phase while a scan completes.

### Acceptance Criteria

- [x] The scan action can be launched from the workspace without moving to a separate page.
- [x] The inspector shows scan progress, success, and failure states.
- [x] Successful scans expose the textual summary in a readable format.
- [x] Existing scan status can be rehydrated from the backend status endpoint.

### How to Test

- Add integration tests for successful scan, failed scan, and preexisting scan status.
- Verify that scan output remains visible after changing center-pane focus.
- Run a manual scan against `dog-service` and confirm the inspector updates correctly.

---

## Story U5.3: Render per-AC traceability as linked evidence

### EARS Requirement

> **When** traceability data exists for a session, the system **shall** let the operator inspect each acceptance criterion as a linked chain of classification, contracts, failure modes, and verification refs.

### Design by Contract

**Preconditions:**
- Negotiation summary data includes per-AC details and traceability references.
- The workspace has a selected AC or an active summary view.

**Postconditions:**
- The operator can expand an AC and inspect its full evidence chain.
- Cross-highlighting can connect selected ACs to related details in the center pane or artifacts.
- The inspector can switch between a per-AC browser and a denser matrix-style traceability view when that improves scanning.
- Large traceability payloads remain navigable.

**Invariants:**
- Traceability refs remain immutable identifiers from backend output.
- Expanded state is local UI state and does not mutate the source summary.
- The evidence chain is ordered from AC to verification refs.

### Acceptance Criteria

- [x] The inspector supports a per-AC traceability browser.
- [x] Selecting an AC reveals classification, postconditions, preconditions, failure modes, and verification refs.
- [x] A denser traceability matrix or table view exists for cross-AC scanning.
- [x] Ref IDs are easy to scan and copy.
- [x] Large traceability trees remain usable without collapsing the entire inspector.

### How to Test

- Add component tests with multi-AC summaries and long evidence chains.
- Verify selected AC state survives tab changes where appropriate.
- Manually inspect a completed negotiation session and confirm traceability remains readable.

---

## Story U5.4: Expose planner, critique, and spec diff as analyst tools

### EARS Requirement

> **Where** the backend provides planning, critique, or spec-diff analysis, the system **shall** surface those outputs in the inspector as optional analyst views instead of hiding them behind raw endpoints.

### Design by Contract

**Preconditions:**
- The current session exists.
- Planner, critique, and spec-diff endpoints are available.

**Postconditions:**
- The operator can request phase critique and planning without leaving the workspace.
- Spec diff results are visible when historical specs exist.
- Secondary analysis does not interrupt the primary negotiation flow.

**Invariants:**
- Analyst tools are clearly secondary to the main workflow.
- Analysis requests are session-scoped.
- Empty or unavailable analysis states are explicit.

### Acceptance Criteria

- [x] The inspector includes access to planner output for the current session.
- [x] The inspector includes access to phase critique for the active phase.
- [x] The inspector includes spec-diff output when an old spec exists.
- [x] Missing historical data produces a clear "nothing to compare" state.

### How to Test

- Add integration tests for planner and critique request flows.
- Add a spec-diff test for both "no old spec" and "old spec exists" responses.
- Verify that analyst-tool requests do not reset the active phase composer.

---

## Story U5.5: Add a spec contract viewer in the inspector

### EARS Requirement

> **When** a compiled spec exists for the current story, the system **shall** let the operator inspect that contract in the right inspector as structured requirements rather than only as raw artifact text.

### Design by Contract

**Preconditions:**
- A compiled spec exists for the current session or story.
- The inspector has access to parsed or renderable spec data.

**Postconditions:**
- Requirement IDs, types, and routing details are visible in a scannable contract view.
- The operator can connect a spec requirement back to the originating AC or traceability chain.
- The spec viewer coexists with the raw artifact viewer rather than replacing it.

**Invariants:**
- Requirement ordering follows the compiled spec.
- Requirement IDs remain immutable backend-generated references.
- The spec view is read-only.

### Acceptance Criteria

- [x] The inspector exposes a structured spec contract view when a spec exists.
- [x] Requirement IDs, types, and verification routing are visible.
- [x] The operator can navigate between a requirement and its originating AC or traceability context.
- [x] A clear "spec not yet compiled" state exists when no spec is available.

### How to Test

- Add component tests for populated and empty spec viewer states.
- Verify requirement-to-AC navigation behavior in integration tests.
- Manually inspect a compiled session and confirm the spec view complements the raw YAML artifact.

---

## Implementation Notes

- The scan surface now launches `/api/scan` directly from the inspector, keeps the latest `/api/scan/status` payload mounted, and preserves the prior summary when reruns fail.
- Traceability uses shared AC selection state so the inspector can cross-highlight the same acceptance criterion already selected in the left rail and center pane.
- Planner, critique, and spec-diff results are session-scoped inspector actions rather than route-level screens, keeping the active phase composer intact.
- The compile endpoint now returns parsed requirement and traceability payloads so the UI can render a structured contract view beside the raw YAML artifact without client-side YAML parsing.
