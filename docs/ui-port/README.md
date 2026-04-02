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

- As of 2026-04-01, `progress.json` reports all 36 UI-port stories complete and the U1 through U8 epic markdown acceptance checklists are synchronized to that shipped state.
- A recurring verification run on 2026-04-02 re-checked `progress.json` plus the epic markdown files, found no unfinished UI-port stories, and reconfirmed `npm run lint`, `npm run test:ci`, and `npm run test:e2e:chromium` on the current branch.
- A follow-up verification run on 2026-04-02 again found no unfinished UI-port stories, but it did catch suite-level Vitest instability under concurrent worker contention. The fix was to serialize Vitest in [`/Users/dannytrevino/development/magic-agents/ui/vitest.config.ts`](/Users/dannytrevino/development/magic-agents/ui/vitest.config.ts) with `maxWorkers: 1`, which restored a deterministic `npm run test:ci` pass without changing shipped UI behavior.
- This verification pass re-ran `npm test`, `npm run build`, and `npm run test:ci` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui). The non-browser frontend gate is green again under the updated 36 kB raw / 7 kB gzip shell CSS budget, which keeps the compressed ceiling fixed while accommodating the shipped live stream-status/progress chrome.
- A follow-up browser rerun on 2026-04-02 confirmed `npm run test:e2e:chromium` still passes for the mocked operator journey after the Vitest harness stabilization, so the detected gap was in the non-browser test runner rather than the shipped workspace flow.
- A later 2026-04-02 browser-harness fix kept U8.2 green by making Playwright trace capture opt-in through `PW_TRACE=1`; failed runs still retain screenshots by default, and the normal `npm run test:e2e:chromium` path no longer depends on local trace-archive support.
- U8.2 browser coverage remains implemented; when Codex-hosted macOS cannot launch Playwright locally, the supported path is `npm run test:e2e:server` outside Codex plus `npm run test:e2e:remote` or `PW_TEST_CONNECT_WS_ENDPOINT=... npm run test:e2e` inside Codex.
- The shell, rails, workspace, and verification console now consume a typed graphite/bone/signal design system mirrored into CSS tokens.
- The shell now mounts the shared SSE event store through the app provider stack, surfaces connection state in the top bar, and keeps the phase progress strip integrated into the workspace chrome without regressing the existing CSS budget.
- The evidence inspector now keeps its idle state to a single compact prompt until a story/session exists, which preserves a calmer right rail without hiding the tab structure.
- Workspace announcements, pane focus handoff, busy states, and the pipeline log now support keyboard and screen-reader operation without pointer-only assumptions.
- Reduced-motion fallbacks and shared timing tokens now govern pane transitions, live console behavior, and responsive shell refinements.
- The frontend now ships explicit quality gates: `npm run test:ci` for Vitest + build + bundle budgets, `npm run test:e2e` for deterministic mock-mode browser journeys, and a FastAPI rollout switch that can force either React or legacy HTML at request or process scope.
- ESLint now uses a dedicated typed project file for tracked source plus Playwright config/spec files and ignores generated browser caches, which keeps the completed UI-port epic focused on product-code regressions instead of local tool output.

## Success Criteria

- An operator can load a story, negotiate through all phases, inspect supporting evidence, run verification, and understand verdicts without navigating across disconnected screens.
- The first viewport makes the product feel like a serious operations tool rather than a prototype.
- The React app is modular, typed, testable, and cheap to extend as the backend grows.
