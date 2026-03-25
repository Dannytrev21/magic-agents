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
- **`dog-service/`** — Spring Boot demo target (Dog CRUD API at `/api/v1/dogs` with Bearer auth, Lombok, Cucumber tests).

### Web UI

- **`src/verify/negotiation/web.py`** — FastAPI backend with endpoints for Jira integration (`/api/jira/*`) and negotiation (`/api/start`, `/api/respond`). In-memory single-user session.
- **`static/index.html`** — Single-page app: story picker → AC overview → negotiation chat → traceability view.

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
