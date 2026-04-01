# Magic Agents UI Port Plan

## Operator Workspace

**Objective:** replace the current single-file HTML frontend with a React + TypeScript + Vite operator workspace that fits the product's real job: intake a story, negotiate a spec, inspect evidence, run verification, and publish outcomes.

## Frontend Direction

**Visual thesis:** calm, high-trust product UI; graphite, bone, and one sharp signal color; sans-serif for product copy, mono only for refs and IDs.

**Content plan:** left rail for story intake and session state, center workspace for the active phase, right inspector for evidence, scan results, and traceability.

**Interaction thesis:** sticky phase rail, inline approve/revise actions, smooth panel swaps instead of screen jumps.

## Decision Record

- Comparison and hybrid rationale: [DECISION.md](DECISION.md)

## Target Stack

- React 19 + TypeScript
- Vite
- TanStack Query for server state
- Radix primitives for accessibility-sensitive controls
- Motion for restrained transitions
- CSS variables + CSS Modules for the visual system

## Architecture Guardrails

- Keep FastAPI as the backend and source of truth for negotiation, session, and pipeline state.
- Serve the built React app from FastAPI; do not introduce SSR or Next.js.
- Use direct imports; avoid barrel files in the UI app.
- Use TanStack Query for API reads and mutations; avoid a global client-state store unless a clear cross-cutting need appears.
- Start independent requests in parallel and await late.
- Use `startTransition` for non-urgent workspace updates.
- Use `useDeferredValue` for local search and heavy filtered lists.
- Keep mono typography limited to IDs, refs, paths, and code-like artifacts.
- Default to layout, sections, dividers, and inspectors; do not rebuild the product as a stack of generic cards.

## Epic Order

| Priority | Epic | Focus | File |
|----------|------|-------|------|
| 1 | U1 | Frontend foundation and app shell | [U01-frontend-foundation.md](U01-frontend-foundation.md) |
| 2 | U2 | Three-pane operator workspace layout | [U02-operator-workspace-layout.md](U02-operator-workspace-layout.md) |
| 3 | U3 | Story intake and session lifecycle | [U03-story-intake-session-lifecycle.md](U03-story-intake-session-lifecycle.md) |
| 4 | U4 | Active phase workspace and negotiation loop | [U04-active-phase-negotiation.md](U04-active-phase-negotiation.md) |
| 5 | U5 | Inspector, evidence, and traceability | [U05-inspector-evidence-traceability.md](U05-inspector-evidence-traceability.md) |
| 6 | U6 | Verification console and pipeline execution | [U06-verification-console-pipeline.md](U06-verification-console-pipeline.md) |
| 7 | U7 | Design system, accessibility, and motion | [U07-design-system-accessibility-motion.md](U07-design-system-accessibility-motion.md) |
| 8 | U8 | Quality, performance, and rollout | [U08-quality-performance-rollout.md](U08-quality-performance-rollout.md) |

## Hybrid Outcome

- Keep the current `ui-port` plan as the base because it is stronger on backend alignment, React/Vite architecture, and rollout safety.
- Pull concrete interaction details from `ui-port-claude`: tokenized visual system, panel collapse behavior, top bar context, AC checklist, phase timeline, transcript view, sticky phase mini-rail, spec viewer, and richer results states.
- Reject or rewrite Claude-plan details that drift from the real backend today, especially incorrect route assumptions, React 18 defaults, and overly card-heavy presentation.

## Planned Delivery Shape

- Build the new app beside the current static UI first.
- Land the shell and workspace before polishing secondary surfaces.
- Move the negotiation and evidence workflow into the new app before removing the legacy screen model.
- Keep API compatibility with the existing FastAPI endpoints during the port.

## Current Status

- U1 through U6 are now complete in the React workspace.
- The right inspector now owns the evidence, scan, traceability, planning/critique, and structured spec-contract surfaces.
- The center pane now carries a session-scoped verification console with backend-confirmed EARS approval, inline artifact viewers, live pipeline streaming, verdict summaries, and Jira feedback.
- Inspector actions and verification actions stay session-scoped and keep the center-pane workflow stable while scan, critique, planning, compile, and pipeline requests run.
- The next delivery slice is Epic U7: design system, accessibility, and motion.

## Success Criteria

- An operator can load a story, negotiate through all phases, inspect supporting evidence, run verification, and understand verdicts without navigating across disconnected screens.
- The first viewport makes the product feel like a serious operations tool rather than a prototype.
- The React app is modular, typed, testable, and cheap to extend as the backend grows.
