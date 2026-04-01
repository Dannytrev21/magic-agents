# Contributing

## UI Workspace

- The primary frontend lives in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui).
- Keep the React workspace aligned to the FastAPI backend instead of inventing frontend-only contracts.
- Prefer TanStack Query reads and mutations for server state; do not introduce a parallel global state store for inspector/session data unless multiple surfaces are blocked by the same cross-cutting concern.
- Inspector actions must not reset the center-pane negotiation draft or route the operator away from the active workspace.
- Shared acceptance-criterion selection should remain the source of truth for left-rail, center-pane, and inspector cross-highlighting.

## Verification

- Run `npm test` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui) for component and query-layer coverage.
- Run `npm run build` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui) before pushing UI changes.
- When backend endpoint contracts change to support the UI, prefer additive response fields and note unverified backend changes if the Python test environment is unavailable.

## Documentation

- Update [`/Users/dannytrevino/development/magic-agents/docs/ui-port/progress.json`](/Users/dannytrevino/development/magic-agents/docs/ui-port/progress.json) when a UI story changes status.
- Keep the relevant epic file in [`/Users/dannytrevino/development/magic-agents/docs/ui-port`](/Users/dannytrevino/development/magic-agents/docs/ui-port) synchronized with the implemented acceptance criteria.
- Record durable UI architecture decisions in [`/Users/dannytrevino/development/magic-agents/docs/adr/0001-workspace-inspector.md`](/Users/dannytrevino/development/magic-agents/docs/adr/0001-workspace-inspector.md) or later ADRs when the decision scope expands.
