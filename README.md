# SPECify Pipeline Contracts

## Data Flow Map

Every arrow below represents a handoff between components. Each handoff has a defined contract (schema + example) that both sides agree to. Team members build against these contracts independently and integrate when ready.

## React Workspace Status

- The React + TypeScript operator workspace now covers epics U1 through U7 of the UI port.
- The right inspector exposes evidence, scan output, per-AC traceability, planner/critique tools, spec diff, and a structured spec contract viewer beside raw YAML.
- The center pane now includes a verification console with backend-confirmed EARS approval, inline spec/test artifact viewers, live SSE pipeline events, and post-run Jira feedback controls.
- The shared workspace shell now ships the graphite/bone visual system, named screen-reader announcements, semantic tabpanels for the active workspace and inspector, and reduced-motion-safe transitions for pane and section changes.
- The inspector consumes the current FastAPI routes directly: `/api/scan`, `/api/scan/status`, `/api/plan`, `/api/evaluate-phase`, `/api/spec-diff`, and `/api/compile`.
- The verification console consumes `/api/ears-approve`, `/api/compile`, `/api/generate-tests`, `/api/pipeline/stream`, and `/api/jira/update`, and the backend now enforces approval before execution endpoints run.
- UI verification currently runs through `npm test` and `npm run build` in [`/Users/dannytrevino/development/magic-agents/ui`](/Users/dannytrevino/development/magic-agents/ui), with Vitest snapshots and axe-backed accessibility assertions covering the shell, negotiation workspace, and verification console.

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
