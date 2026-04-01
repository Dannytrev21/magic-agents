# Epic U7: Design System, Accessibility, and Motion

**Priority:** 7 (Medium-Low)  
**Implementation Target:** visual language, semantic tokens, keyboard support, and restrained motion  
**Primary Outcome:** make the Operator Workspace feel deliberate and trustworthy instead of generic

## Rationale

The new workspace should look and feel premium, but polish only matters after the structural workflow is in place. This epic codifies the visual thesis and interaction quality so the UI stays coherent as more surfaces are ported.

---

## Story U7.1: Establish the visual system and typography rules

### EARS Requirement

> **When** any Operator Workspace surface renders, the system **shall** use one consistent visual language based on graphite, bone, one accent signal, and disciplined type usage.

### Design by Contract

**Preconditions:**
- The application shell and layout primitives exist.
- Theme tokens can be consumed by all workspace surfaces.

**Postconditions:**
- Color, spacing, typography, and divider rules are tokenized.
- Product copy uses the primary sans-serif family.
- IDs, refs, and code-like artifacts use a mono family.

**Invariants:**
- Accent color is reserved for action, state, or emphasis.
- Decorative gradients do not dominate routine operator UI.
- Typography scale remains readable across dense surfaces.

### Acceptance Criteria

- [x] CSS variables or tokens define color, spacing, radius, and type scales.
- [x] Sans-serif is the default product copy face.
- [x] Mono is limited to IDs, refs, paths, and artifact text.
- [x] Visual treatment favors dividers and whitespace over boxed cards.

### How to Test

- Add visual regression coverage for the shell, rails, and artifact surfaces.
- Verify token usage through component stories or design-system snapshots.
- Manually inspect representative screens for typography misuse or accent overuse.

### Implementation Notes

- Rebased the operator workspace onto a light graphite/bone visual system in `ui/src/styles/tokens.css`, `ui/src/styles/global.css`, and the shared primitive/layout CSS modules.
- Tightened shell, rail, and verification-console composition to rely on dividers, surface layering, and spacing before boxed treatment, while preserving mono typography only for refs, file paths, and session IDs.
- Added Vitest snapshot coverage for the app shell, negotiation workspace, and verification surface so future visual regressions in the shared layout can be reviewed intentionally.

---

## Story U7.2: Make the workspace accessible for keyboard and screen-reader users

### EARS Requirement

> **When** an operator uses the workspace without a pointer, the system **shall** keep all primary actions, pane navigation, and execution feedback accessible by keyboard and assistive technology.

### Design by Contract

**Preconditions:**
- Interactive controls use semantic HTML or accessible primitives.
- Focus management can be controlled across pane transitions.

**Postconditions:**
- Primary actions are keyboard reachable.
- Focus order matches the logical operating flow.
- Live status changes are announced where needed.

**Invariants:**
- Focus is never lost on pane swaps or dialog opens.
- Color is never the only status signal.
- Inspector tabs and execution controls expose accessible names.

### Acceptance Criteria

- [x] Keyboard users can move through the rails, workspace, and inspector predictably.
- [x] Focus is managed after major transitions such as story selection, phase approval, and pipeline completion.
- [x] Live regions announce important status changes such as running, failed, and complete.
- [x] Contrast and visible focus styling meet accessible operator-use standards.

### How to Test

- Add accessibility tests with axe or equivalent tooling.
- Run keyboard-only manual checks for the main negotiation and execution flows.
- Verify screen-reader-friendly labels on tabs, buttons, and execution output.

### Implementation Notes

- Added named `role="status"` regions for persistent workspace state and transient announcements in the app shell plus a dedicated pipeline-status live region in the verification console.
- Promoted center-pane and inspector surfaces to named tabpanels with explicit `aria-controls`/`aria-labelledby` wiring so the active workspace and inspector views are screen-reader addressable.
- Added focus handoff on session start, successful phase actions, and pipeline completion; axe-backed tests now cover shell, negotiation, and verification surfaces.

---

## Story U7.3: Add restrained motion and responsive refinement

### EARS Requirement

> **When** workspace sections change state, the system **shall** use restrained motion and responsive adaptations that improve orientation without making the interface feel ornamental.

### Design by Contract

**Preconditions:**
- Layout and pane state transitions are already modeled in React.
- Motion preferences can be detected.

**Postconditions:**
- Pane swaps, inspector reveals, and status changes have deliberate transition behavior.
- Reduced-motion preferences are respected.
- Tablet and mobile layouts remain usable when all three panes cannot remain expanded.

**Invariants:**
- Motion clarifies hierarchy rather than decorating it.
- Responsive changes preserve core tasks first.
- Animation timing stays fast and consistent.

### Acceptance Criteria

- [x] Pane and section transitions use a shared motion vocabulary.
- [x] Reduced-motion users receive a no-frills equivalent.
- [x] Tablet and mobile layouts collapse gracefully without losing key actions.
- [x] Motion does not introduce jank during data-heavy updates.

### How to Test

- Add visual interaction tests for key transitions.
- Verify reduced-motion handling in browser devtools or OS settings.
- Run manual responsive checks across desktop, tablet, and mobile widths.

### Implementation Notes

- Standardized pane, overlay, and section entrance timing around the shared motion tokens and limited motion to orientation cues instead of ornamental movement.
- Added a global `prefers-reduced-motion` escape hatch that disables animations and smooth scrolling for motion-sensitive operators.
- Kept existing tablet overlay and mobile pane switching behavior, then refined the shell and pane surfaces so the responsive fallbacks stay readable without sacrificing primary actions.
