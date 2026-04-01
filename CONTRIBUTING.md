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
- Real-time event handling should use the `EventStoreProvider` + typed selector hooks (`usePhaseEvents`, `useBudgetEvents`, etc.) from `eventStore.ts` rather than ad-hoc component state. The SSE connection is managed by `useSSE` and should not be duplicated.
- Any new pane swap, status strip, or execution control should preserve keyboard reachability, visible focus, and a screen-reader announcement path for major status changes.
- Reduced-motion behavior is required for new UI motion; rely on the shared motion tokens and the global `prefers-reduced-motion` fallback instead of inventing per-component timing constants.

## Verification

- Run `npm run test:ui` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui) for component, integration, and typed client contract coverage.
- Run `npm run build` and `npm run test:budgets` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui) before pushing UI changes that affect shipped assets or lazy-loaded surfaces.
- Use `npm run test:ci` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui) when you want the full non-browser frontend gate in one command.
- Treat `npm run test:ci` as the default pre-push gate for UI-only changes; use browser e2e coverage as an additional release or regression check when a local or remote Playwright runtime is available.
- Install the local Playwright browsers once with `npm run test:e2e:install` and run `npm run test:e2e` for deterministic mock-mode browser coverage. Use `npm run test:e2e:chromium`, `npm run test:e2e:firefox`, or `npm run test:e2e:webkit` when you need to isolate host-specific browser failures.
- When Codex Desktop cannot launch browsers locally, start `npm run test:e2e:server` in a normal terminal and run `npm run test:e2e:remote` from Codex. For non-default endpoints, pass `PW_TEST_CONNECT_WS_ENDPOINT=ws://host:port/` directly to `npm run test:e2e`.
- Set `PW_SKIP_WEBSERVER=1` when the app under test is already running, or override the target app URL with `PW_BASE_URL=http://host:port`. Failed runs retain traces/screenshots under the ignored Playwright output folders in the UI workspace.
- When backend endpoint contracts change to support the UI, prefer additive response fields and run `uv run pytest tests/test_web_integration.py tests/test_sse_pipeline.py tests/test_structured_streaming_events.py` from [`/Users/dannytrevino/development/magic-agents`](/Users/dannytrevino/development/magic-agents) before pushing.
- Execution endpoints that compile specs, generate tests, or stream the pipeline must enforce the EARS approval gate on the server, not only through disabled frontend controls.
- When comparing React and legacy entrypoints during rollout, prefer `MAGIC_AGENTS_FRONTEND_MODE=legacy` for a process-wide fallback and `/?frontend=react` or `/?frontend=legacy` for per-request cutover checks without editing the backend.

## Port Epics (Backend)

- Track backend port epic progress in [`/Users/dannytrevino/development/magic-agents/docs/port-epics/progress.json`](/Users/dannytrevino/development/magic-agents/docs/port-epics/progress.json).
- When adding checkpoint-serializable state, implement `to_dict()`/`from_dict()` on the dataclass and wire it through `save_checkpoint()`/`load_checkpoint()` in `checkpoint.py`.
- New web endpoints should follow the existing FastAPI pattern in `web.py` and include test coverage in `tests/test_session_cost_accounting.py` or an appropriate test module.
- Budget events (`budget_warning`, `budget_exceeded`) use the `RuntimeEvent` type and must be registered in the `NegotiationEvent` enum and `EVENT_SCHEMAS` dict.

## Documentation

- Update [`/Users/dannytrevino/development/magic-agents/docs/ui-port/progress.json`](/Users/dannytrevino/development/magic-agents/docs/ui-port/progress.json) when a UI story changes status.
- Keep the relevant epic file in [`/Users/dannytrevino/development/magic-agents/docs/ui-port`](/Users/dannytrevino/development/magic-agents/docs/ui-port) synchronized with the implemented acceptance criteria.
- When a UI story moves to `complete`, flip the corresponding Acceptance Criteria checkboxes in the epic file to `[x]` in the same change so the EARS-style docs stay consistent with `progress.json`.
- Record durable UI architecture decisions in [`/Users/dannytrevino/development/magic-agents/docs/adr/0001-workspace-inspector.md`](/Users/dannytrevino/development/magic-agents/docs/adr/0001-workspace-inspector.md) or later ADRs when the decision scope expands.
