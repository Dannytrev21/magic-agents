# Contributing

## UI Workspace

- The primary frontend lives in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui).
- Keep the React workspace aligned to the FastAPI backend instead of inventing frontend-only contracts.
- Prefer TanStack Query reads and mutations for server state; do not introduce a parallel global state store for inspector/session data unless multiple surfaces are blocked by the same cross-cutting concern.
- Keep shared UI tokens in [`/Users/dannytrevino/development/magic-agents/ui/src/styles/system.ts`](/Users/dannytrevino/development/magic-agents/ui/src/styles/system.ts) and mirror any new cross-cutting values into [`/Users/dannytrevino/development/magic-agents/ui/src/styles/tokens.css`](/Users/dannytrevino/development/magic-agents/ui/src/styles/tokens.css) before consuming them in component CSS.
- Treat sans copy, mono refs, and the single signal accent as invariants; dense operator surfaces should prefer whitespace, dividers, and layered panels over mosaics of heavy cards.
- Inspector actions must not reset the center-pane negotiation draft or route the operator away from the active workspace.
- Shared acceptance-criterion selection should remain the source of truth for left-rail, center-pane, and inspector cross-highlighting.
- Verification console state must remain session-scoped inside the center pane so approval, artifacts, live pipeline events, and Jira feedback survive tab changes without forcing a second route model.
- Any new pane swap, status strip, or execution control should preserve keyboard reachability, visible focus, and a screen-reader announcement path for major status changes.
- Reduced-motion behavior is required for new UI motion; rely on the shared motion tokens and the global `prefers-reduced-motion` fallback instead of inventing per-component timing constants.

## Verification

- Run `npm test` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui) for component and query-layer coverage.
- Run `npm run build` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui) before pushing UI changes.
- When backend endpoint contracts change to support the UI, prefer additive response fields and run `uv run pytest tests/test_web_integration.py tests/test_sse_pipeline.py` from [`/Users/dannytrevino/development/magic-agents`](/Users/dannytrevino/development/magic-agents) before pushing.
- Execution endpoints that compile specs, generate tests, or stream the pipeline must enforce the EARS approval gate on the server, not only through disabled frontend controls.

## Documentation

- Update [`/Users/dannytrevino/development/magic-agents/docs/ui-port/progress.json`](/Users/dannytrevino/development/magic-agents/docs/ui-port/progress.json) when a UI story changes status.
- Keep the relevant epic file in [`/Users/dannytrevino/development/magic-agents/docs/ui-port`](/Users/dannytrevino/development/magic-agents/docs/ui-port) synchronized with the implemented acceptance criteria.
- Record durable UI architecture decisions in [`/Users/dannytrevino/development/magic-agents/docs/adr/0001-workspace-inspector.md`](/Users/dannytrevino/development/magic-agents/docs/adr/0001-workspace-inspector.md) or later ADRs when the decision scope expands.
