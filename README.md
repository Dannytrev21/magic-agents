# SPECify Pipeline Contracts

## Data Flow Map

Every arrow below represents a handoff between components. Each handoff has a defined contract (schema + example) that both sides agree to. Team members build against these contracts independently and integrate when ready.

## React Workspace Status

- The React + TypeScript operator workspace now covers epics U1 through U8 of the UI port.
- As of 2026-04-01, [`/Users/dannytrevino/development/magic-agents/docs/ui-port/progress.json`](/Users/dannytrevino/development/magic-agents/docs/ui-port/progress.json) reports 36 of 36 UI stories complete and the U1 through U8 epic markdown EARS checklists are synchronized to that state.
- A recurring verification run on 2026-04-02 re-checked `progress.json` and the UI-port epic markdown files, found no unfinished U1 through U8 stories, and revalidated `npm run lint`, `npm run test:ci`, and `npm run test:e2e:chromium` on the current branch.
- A follow-up verification run on 2026-04-02 again found no unfinished UI-port stories, then stabilized the non-browser harness by keeping the shared browser-runtime fallbacks in [`/Users/dannytrevino/development/magic-agents/ui/src/test/setup.ts`](/Users/dannytrevino/development/magic-agents/ui/src/test/setup.ts), serializing Vitest in [`/Users/dannytrevino/development/magic-agents/ui/vitest.config.ts`](/Users/dannytrevino/development/magic-agents/ui/vitest.config.ts) with `maxWorkers: 1`, and pinning Playwright to a single non-fully-parallel worker in [`/Users/dannytrevino/development/magic-agents/ui/playwright.config.ts`](/Users/dannytrevino/development/magic-agents/ui/playwright.config.ts), so `npm run test:ci` and `npm run test:e2e:chromium` are green on `feat/u07-realtime-streaming-events`.
- The latest 2026-04-02 gap pass also tightened the typed lint boundary with [`/Users/dannytrevino/development/magic-agents/ui/tsconfig.eslint.json`](/Users/dannytrevino/development/magic-agents/ui/tsconfig.eslint.json), so tracked source and Playwright files stay linted while generated browser caches and build output remain ignored.
- The right inspector exposes evidence, scan output, per-AC traceability, planner/critique tools, spec diff, and a structured spec contract viewer beside raw YAML.
- When no session is active, the evidence inspector now stays visually quiet with a single compact prompt instead of stacked empty session/spec sections, while the tab strip remains keyboard reachable.
- The center pane now includes a verification console with backend-confirmed EARS approval, inline spec/test artifact viewers, live SSE pipeline events, and post-run Jira feedback controls.
- The shared UI design system now ships from a typed token source mirrored into CSS variables, keeping graphite/bone surfaces, mono artifact treatment, and restrained glass chrome aligned across the shell, rails, and verification surfaces.
- Workspace navigation and execution surfaces now announce session, phase, and pipeline changes through live regions while focus follows the active workspace flow after session start, phase advancement, and pipeline completion.
- The verification workspace is now lazy-loaded behind the center-pane boundary, the analyst tool surface remains lazy-loaded in the inspector, and production builds emit a manifest-backed bundle budget report.
- Frontend rollout is now reversible from FastAPI through `MAGIC_AGENTS_FRONTEND_MODE=auto|react|legacy`, with `/?frontend=react` and `/?frontend=legacy` available as per-request overrides while the legacy HTML entrypoint remains on disk.
- The inspector consumes the current FastAPI routes directly: `/api/scan`, `/api/scan/status`, `/api/plan`, `/api/evaluate-phase`, `/api/spec-diff`, and `/api/compile`.
- The verification console consumes `/api/ears-approve`, `/api/compile`, `/api/generate-tests`, `/api/pipeline/stream`, and `/api/jira/update`, and the backend now enforces approval before execution endpoints run.
- Structured streaming events (P06) provide a closed set of typed SSE event types (`NegotiationEvent` enum) with documented payload schemas. The `NegotiationHarness` emits `phase_start`, `phase_complete`, `phase_error`, `validation_result`, `budget_exceeded`, and `session_checkpoint` events through an optional `event_emitter` callback. The `GET /api/events/{session_id}?types=` endpoint streams filtered SSE events per session.
- Real-time updates & streaming (U07) delivers a client-side SSE architecture: `useSSE` hook maintains a persistent EventSource with exponential-backoff reconnection (1s-30s); `createEventStore` provides a FIFO-bounded (100 events) store with typed selector hooks (`usePhaseEvents`, `useBudgetEvents`, `useValidationEvents`, `useLatestEvent`); `PhaseProgressBar` renders an indeterminate progress indicator with elapsed timer between `phase_start` and `phase_complete` events (see ADR 0006).
- The shell-level bridge in [`/Users/dannytrevino/development/magic-agents/ui/src/features/workspace/phaseWorkspaceModel.ts`](/Users/dannytrevino/development/magic-agents/ui/src/features/workspace/phaseWorkspaceModel.ts) now dispatches every negotiation SSE through `useSSE(..., { onEvent })` instead of deriving store writes from one `lastEvent` snapshot, which preserves `phase_start` and immediate `phase_progress` pairs when React batches them into the same render.
- Session cost accounting (P07) persists `BackPressureController` state in checkpoints via `to_dict()`/`from_dict()` serialization, exposes `GET /api/session/{session_id}/cost` for cumulative token usage with per-phase breakdowns and estimated USD cost, and emits deduplicated `budget_warning`/`budget_exceeded` SSE events when soft/hard token limits are crossed.
- Bootstrap & initialization graph (P08) replaces ad-hoc startup with a DAG-based `BootstrapGraph` that executes stages (`env_validation`, `constitution_load`, `llm_client_init`, `skill_registration`, `session_store_init`) in topological order with dependency resolution, failure propagation, and per-stage timing. `GET /api/health` exposes readiness and stage status.
- Hook & event system (P09) provides a `HookRegistry` with lifecycle points (`pre_phase`, `post_phase`, `checkpoint_saved`, etc.) that fire registered callbacks in order with isolated failure handling. Hooks integrate into `NegotiationHarness` at phase boundaries and can be configured via `constitution.yaml` shell commands with environment variable context.
- MCP server wrapper (P10) exposes core pipeline capabilities as MCP tools (`start_negotiation`, `run_phase`, `get_spec`, `dispatch_skills`, `get_verdicts`) with JSON Schema definitions, plus resources at `verify://specs/{key}` and `verify://sessions/{id}` for spec YAML and session state.
- UI verification now runs through `npm run test:ci` for Vitest + build + bundle budgets, with browser coverage authored under `npm run test:e2e` after `npm run test:e2e:install` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui). The Playwright harness supports `PLAYWRIGHT_BROWSER=chromium|firefox|webkit`, a dedicated remote browser server via `npm run test:e2e:server`, and Codex-friendly remote execution through `npm run test:e2e:remote` or `PW_TEST_CONNECT_WS_ENDPOINT=... npm run test:e2e`.
- Browser failures now retain screenshots by default. Set `PW_TRACE=1` when you also want Playwright trace archives and the local host can persist them reliably.
- On 2026-04-02, the default Vitest worker fan-out was capped at `1` in [`/Users/dannytrevino/development/magic-agents/ui/vitest.config.ts`](/Users/dannytrevino/development/magic-agents/ui/vitest.config.ts) after a rerun showed the full jsdom-heavy UI suite could pass file-by-file but timed out under concurrent worker contention.
- On 2026-04-02, the shared Vitest setup added durable `MutationObserver`, `ResizeObserver`, `IntersectionObserver`, `matchMedia`, and `scrollIntoView` fallbacks so component and integration failures track UI behavior instead of host DOM gaps.
- On 2026-04-01, a local Chromium rerun of the mocked operator journey (`npm run test:e2e:chromium`) revalidated intake fallback, in-place phase approval, and pipeline execution after browser coverage caught stale UI-contract drift in the Jira fallback and approval path.
- The current non-browser shell CSS budget remains 33.5 kB raw and 7 kB gzip. A 2026-04-02 verification run measured the shipped shell at 30.94 kB raw and 5.78 kB gzip after trimming shell chrome and inlining the live phase-progress styling instead of raising thresholds.
- A follow-up 2026-04-01 workspace verification reran `npm run test:ui`, `npm run build`, and `npm run test:budgets` after tightening the inspector tab chrome and idle evidence state; all three gates remained green.

```
┌──────────┐     jira_ticket.yaml      ┌───────────────┐
│  Jira    │ ──────────────────────────▶│  Phase 0:     │
│  Cloud   │                            │  AC Ingestion │
│  API     │◀────────────────────────── │               │
│          │  jira_update.yaml          └───────┬───────┘
│          │  jira_comment.yaml                 │
│          │  jira_transition.yaml              │ ac_input.yaml
└──────────┘                                    ▼
                                        ┌───────────────┐
              constitution.yaml ───────▶│  Negotiation  │
              codebase_index.yaml ─────▶│  Harness      │
                                        │  (Phases 1-7) │
                                        └───────┬───────┘
                                                │
            ┌───────────────────────────────────┘
            │ Each phase produces structured JSON:
            │  phase1_classifications.json
            │  phase2_postconditions.json
            │  phase3_preconditions.json
            │  phase4_failure_modes.json
            │  phase5_invariants.json
            │  phase6_routing.json
            │  phase7_ears.json
            ▼
    ┌───────────────┐
    │  Spec         │    spec.yaml (THE canonical contract)
    │  Compiler     │───────────────────────┐
    └───────────────┘                       │
                                            ▼
                              ┌──────────────────────────┐
                              │  Skill Router            │
                              │  (reads spec.verification)│
                              └─────┬──────────┬─────────┘
                                    │          │
                    ┌───────────────┘          └──────────────┐
                    ▼                                         ▼
            ┌───────────────┐                        ┌───────────────┐
            │  Test Skill   │                        │  Config Skill │
            │  (JUnit/Jest) │                        │  (NRQL/OTel)  │
            └───────┬───────┘                        └───────┬───────┘
                    │                                         │
                    │ Generated test file                     │ Generated config
                    │ (with @Tag annotations)                 │ (JSON/YAML)
                    ▼                                         ▼
            ┌───────────────┐                        ┌───────────────┐
            │  Test Runner  │                        │  File         │
            │  (gradle/npm) │                        │  Validator    │
            └───────┬───────┘                        └───────┬───────┘
                    │                                         │
                    │ test_results.json                       │ validation_results.json
                    │ (unified format)                        │
                    └──────────────┬──────────────────────────┘
                                   ▼
                           ┌───────────────┐
                           │  Evaluator    │
                           │  (reads spec  │     verdicts.json
                           │  traceability)│────────────────────┐
                           └───────────────┘                    │
                                                                ▼
                                                        ┌───────────────┐
                                                        │  Jira Updater │
                                                        │  (checkboxes, │
                                                        │   comments,   │
                                                        │   transitions)│
                                                        └───────────────┘
```

## File Index

| Contract File | Producer | Consumer | Purpose |
|---|---|---|---|
| `schemas/constitution.schema.json` | init scanner | all phases | Repo context validation |
| `schemas/spec.schema.json` | spec compiler | skills, evaluator, Jira updater | The canonical spec validation |
| `schemas/codebase-index.schema.json` | codebase scanner | negotiation phases | Codebase metadata validation |
| `schemas/phase-outputs.schema.json` | negotiation phases | spec compiler | Per-phase output validation |
| `schemas/test-results.schema.json` | test runner parsers | evaluator | Unified test results validation |
| `schemas/verdicts.schema.json` | evaluator | Jira updater, web UI | AC checkbox verdicts validation |
| `examples/constitution.yaml` | reference | all team members | Example constitution |
| `examples/spec.yaml` | reference | all team members | Complete example spec |
| `examples/ac-input.yaml` | Jira client | negotiation harness | Example Jira AC extraction |
| `examples/phase1-output.json` | Phase 1 skill | harness / spec compiler | Example classification output |
| `examples/phase2-output.json` | Phase 2 skill | harness / spec compiler | Example postcondition output |
| `examples/phase3-output.json` | Phase 3 skill | harness / spec compiler | Example precondition output |
| `examples/phase4-output.json` | Phase 4 skill | harness / spec compiler | Example failure mode output |
| `examples/phase5-output.json` | Phase 5 skill | harness / spec compiler | Example invariant output |
| `examples/phase6-output.json` | Phase 6 skill | harness / spec compiler | Example routing output |
| `examples/test-results.json` | test runner | evaluator | Example unified test results |
| `examples/verdicts.json` | evaluator | Jira updater | Example AC verdicts |
| `examples/jira-update.json` | Jira updater | Jira Cloud API | Example Jira API payloads |
| `examples/jira-comment.md` | Jira updater | Jira Cloud API | Example evidence comment |
| `interfaces/api-endpoints.yaml` | backend | frontend (web UI) | REST API contract |
| `interfaces/sse-events.yaml` | backend | frontend (web UI) | Server-Sent Events contract |
| `interfaces/skill-interface.yaml` | skill framework | skill authors | What a skill receives/returns |
