# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Magic Agents is an Intent-to-Verification Spec Engine: it transforms Jira acceptance criteria into formal, machine-verifiable specifications through AI negotiation, then generates tests/configs via Claude Agent Skills and feeds verdicts back to Jira.

## Commands

```bash
# Setup
source .venv/bin/activate
pip install -e ".[dev]"

# Run web UI (Jira story picker + negotiation + traceability)
python run_web.py                         # requires ANTHROPIC_API_KEY in .env
LLM_MOCK=true python run_web.py           # mock mode, no API key needed

# Run CLI negotiation
python run_negotiation.py
LLM_MOCK=true python run_negotiation.py

# Run full pipeline (generate → run → evaluate)
python -m verify.pipeline .verify/specs/DEMO-001.yaml

# Tests
pytest tests/                             # all tests
cd dog-service && ./gradlew test          # run dog-service tests (Cucumber + JUnit)
pytest --cov=src tests/                   # with coverage
```

## Architecture

**Two-Zone design** — AI zone produces specs, deterministic zone consumes them:

1. **AI Zone (Negotiation):** Jira ticket → 4-phase AI negotiation → VerificationContext
2. **Spec Boundary:** VerificationContext → YAML spec via deterministic compiler
3. **Deterministic Zone:** Spec → routing table → test generation → runner → evaluator → Jira

### Key modules (`src/verify/`)

- **`context.py`** — `VerificationContext` dataclass, the single belief object threaded through all phases. Accumulates classifications, postconditions, preconditions, failure_modes, invariants, EARS statements, traceability.
- **`negotiation/harness.py`** — Sherpa-pattern state machine with guard conditions on phase transitions (e.g., phase 0→1 requires every AC classified).
- **`negotiation/phase{1,2,3,4}.py`** — Each phase: builds a constitutional system prompt, calls LLM, validates output deterministically. All accept `feedback` param for multi-turn revision via `chat_multi()`.
- **`negotiation/validate.py`** — Block Principle 1: deterministic validation of phase outputs (enum checks, ID format, referential integrity). No AI.
- **`negotiation/synthesis.py`** — Post-negotiation: extracts invariants, generates EARS statements, builds traceability map. Zero AI.
- **`compiler.py`** — Transforms VerificationContext → `.verify/specs/{key}.yaml`. Contains `ROUTING_TABLE` mapping requirement types to verification skills.
- **`llm_client.py`** — Claude SDK wrapper. `chat()` for single-turn, `chat_multi()` for feedback loops. `LLM_MOCK=true` activates canned responses keyed by system prompt phrases.
- **`generator.py`** — Template-based pytest generation from spec YAML. Tags tests with spec refs for traceability.
- **`runner.py`** — Runs pytest with `--junitxml`, parses results.
- **`evaluator.py`** — Maps test results back to AC verdicts via spec traceability.
- **`jira_client.py`** — Jira Cloud REST API v3 (search, fetch, extract AC, update).
- **`permissions.py`** — Permission & access control: `ToolPermissionContext` (frozen dataclass with deny rules), `PermissionDenial` (denial event), skill filtering, and constitution-driven defaults. Ported from claw-code P05.
- **`runtime.py`** — `NegotiationEvent` enum (closed set of SSE event types), `EVENT_SCHEMAS` (payload field contracts per type), `RuntimeEvent` (validates type against enum + legacy types, emits typed SSE with `event:` prefix). `SessionState` includes `event_buffer` for SSE streaming, `backpressure` (`BackPressureController`), and `phase_cost_reports` (`list[PhaseCostReport]`) for P7 cost accounting.
- **`bootstrap.py`** — `BootstrapGraph` with `BootstrapStage`, topological sort, failure propagation, and `BootstrapReport`. `build_bootstrap_graph()` returns the default magic-agents startup graph. Ported from claw-code P08.
- **`hooks.py`** — `HookRegistry` with `HookEvent`, lifecycle point validation, ordered multi-hook execution with isolated failure, and `from_constitution()` for shell-command hooks with env vars. Ported from claw-code P09.
- **`mcp_server.py`** — `MCPServer` exposing 5 MCP tools and spec/session resources. Transport-agnostic core; can be wired to stdio or SSE. Ported from claw-code P10.
- **`skills/framework.py`** — Skill agent framework with `SkillDescriptor`, `SkillDispatchError`, `find_skills()`, `find_skills_by_type()`, `validate_dispatch()`, and registry discovery.
- **`dog-service/`** — Spring Boot demo target (Dog CRUD API at `/api/v1/dogs` with Bearer auth, Lombok, Cucumber tests).

### Web UI

- **`src/verify/negotiation/web.py`** — FastAPI backend with endpoints for Jira integration (`/api/jira/*`), negotiation (`/api/start`, `/api/respond`), session cost (`GET /api/session/{id}/cost`), and SSE events (`GET /api/events/{session_id}`). In-memory single-user session.
- **`static/index.html`** — Legacy single-page app (superseded by React UI).
- **`ui/`** — React 19 + TypeScript + Vite frontend. Key modules:
  - **`ui/src/lib/api/client.ts`** — API client for all FastAPI endpoints.
  - **`ui/src/lib/api/useSSE.ts`** — SSE client hook with auto-reconnection (exponential backoff, max 30s). One connection per session.
  - **`ui/src/lib/api/eventStore.ts`** — Client-side event store with typed selectors (`usePhaseEvents`, `useBudgetEvents`, `useValidationEvents`, `useLatestEvent`). FIFO overflow at 100 events.
  - **`ui/src/components/layout/AppShell.tsx`** — Three-panel responsive layout (desktop/tablet/mobile).
  - **`ui/src/components/primitives/`** — Design system primitives (Button, Badge, Text, Mono, Panel, Divider, Skeleton).
  - **`ui/src/features/workspace/PhaseProgressBar.tsx`** — Live progress indicator driven by SSE phase events.
  - **`ui/src/styles/tokens.css`** — CSS custom property design tokens (colors, spacing, typography, motion).

### Agent Skills (`.claude/skills/phase*-*/`)

Follow the [SKILL.md open standard](agent-skills-reference.md). Each skill directory has `SKILL.md` (metadata + constitutional rules) and optionally `SCHEMA.md`. These are the prompt templates consumed by `phase{1..4}.py` via `LLMClient`.

## Design Principles

- **Block Principle 1:** Deterministic validation for things agents shouldn't decide (enum membership, ID formats, referential integrity).
- **Block Principle 2:** LLM only for context-dependent reasoning (classifying ACs, proposing contracts).
- **Block Principle 3:** Constitutional rules are MUST/FORBIDDEN, not suggestions. Embedded in system prompts.
- **Sherpa pattern:** Guard conditions on every phase transition — harness won't advance until exit conditions are met.
- **Traceability is end-to-end:** AC checkbox → classification → contract elements → verification refs → test tags → verdicts.

## Environment Variables

Set in `.env` (loaded by `python-dotenv`):

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | No (falls back to mock) | Claude API access |
| `JIRA_BASE_URL` | For Jira features | e.g. `https://yourorg.atlassian.net` |
| `JIRA_EMAIL` | For Jira features | API user email |
| `JIRA_API_TOKEN` | For Jira features | Jira API token |
| `LLM_MOCK` | No | Set `true` to use canned responses |

## Mock Mode

When `LLM_MOCK=true` or no `ANTHROPIC_API_KEY` is set, `LLMClient` returns canned responses keyed by distinctive phrases in system prompts. Mock key matching is order-dependent (first match wins). When adding mock responses, use unique phrases that won't collide with other phases.

## Generated Artifacts

- `.verify/specs/*.yaml` — Compiled specs (the canonical contract)
- `.verify/generated/test_*.py` — Generated test files
- `.verify/results/` — JUnit XML + parsed JSON results

## Documentation

- `docs/DESIGN.md` — Architecture diagrams (Mermaid), epic dependencies, agentic patterns
- `docs/epic-{0..10}-*/PLAYBOOK.md` — Per-epic implementation playbooks
- `PLAYBOOK.md` — Index linking to all epic playbooks
- `reference-library.md` — Sherpa, Agent Skills, Harness Engineering, BMAD references
- `ac-to-specs-plan.md` — Detailed design with spec schema
