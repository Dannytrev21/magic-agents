# SPECify: Production Specification
## Intent-to-Verification Pipeline — Full System Design

**Version:** 1.0
**Status:** Design Complete
**Last Updated:** 2026-03-23

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Architecture](#3-architecture)
4. [The Harness](#4-the-harness)
5. [Multi-Agent Architecture](#5-multi-agent-architecture)
6. [Repository Constitution & Codebase Intelligence](#6-repository-constitution--codebase-intelligence)
7. [The Negotiation Protocol](#7-the-negotiation-protocol)
8. [The Spec Format](#8-the-spec-format)
9. [Verification Engine](#9-verification-engine)
10. [Evaluation Engine](#10-evaluation-engine)
11. [Jira Integration](#11-jira-integration)
12. [Spec Drift Detection](#12-spec-drift-detection)
13. [Web UI & API Contract](#13-web-ui--api-contract)
14. [CLI Interface](#14-cli-interface)
15. [Data Contracts](#15-data-contracts)
16. [Development & Deployment](#16-development--deployment)

---

## 1. Executive Summary

SPECify is an intent-to-verification pipeline that transforms fuzzy, human-written Jira Acceptance Criteria into formal, machine-verifiable specifications. The specification becomes the single source of truth for correctness — code is correct if and only if it satisfies the spec, and the spec is a faithful formalization of the business intent.

**The Correctness Argument:**
```
If tests pass → spec is satisfied (tests are mechanical translations of the spec)
If spec is satisfied → AC is met (spec was negotiated from AC with human approval)
If AC is met → business intent is verified
Therefore: passing tests = proven business intent
```

**Key Principle:** AI handles the fuzzy-to-formal translation (negotiation + spec generation). Everything downstream of the approved spec — routing, test generation, execution, evaluation, Jira updates — is deterministic. The spec is the boundary between intelligence and automation.

### Design Influences

| Concept | Source | Application |
|---------|--------|-------------|
| Hierarchical state machines | Sherpa (Aggregate Intellect / McGill) | Negotiation harness is a state machine. Transitions are rule-based or LLM-driven. Composite states for multi-turn phases. |
| Agent Skills / progressive disclosure | Agent Skills standard (Block, Anthropic) | Each negotiation phase and generator is a SKILL.md loaded on-demand. Skills inject domain expertise without bloating the system prompt. |
| Harness engineering | Anthropic (12-factor agents), HumanLayer | The orchestrator is a harness, not an agent. It controls phase sequencing, context curation, validation, back-pressure, observability, checkpointing, and the deterministic boundary. |
| Spec-driven development | GitHub Spec Kit, AWS Kiro | Specifications are the source of truth. Code serves the spec. The spec is a living artifact committed to the repo. |
| EARS notation | Alistair Mavin (Rolls-Royce) | Requirements formalized using WHEN/SHALL/IF-THEN/WHILE patterns. Each EARS statement maps to exactly one verifiable assertion. |
| Design by Contract | Bertrand Meyer (Eiffel) | Every behavior defined by preconditions, postconditions, and invariants. |
| FMEA | Failure Mode and Effects Analysis | Phase 4 systematically enumerates every way each precondition can be violated. |
| ATDD | Agile Alliance | Spec written before code. Tests derived from spec. Code written to pass tests. |
| BMAD Agent-as-Code | BMad Method | Each agent/skill defined as a versioned markdown file — portable, diffable, reviewable in PRs. |
| Constitution / Steering | GitHub Spec Kit, AWS Kiro | Repo-level constitution captures org conventions, tech stack, testing patterns. All generation is steered by this context. |
| Conformance suites | Simon Willison | Specs are language-independent YAML contracts. The test framework is a translation detail. |
| CiRA | Fischbach et al. (NLP research) | Conditional extraction from natural language requirements. Systematically finding every if/when/unless in AC text. |

---

## 2. System Overview

### 2.1 The Pipeline

```
Jira AC (human intent, fuzzy)
    ↓  [Phase 0: Deterministic Jira API pull]
Raw AC + Ticket Metadata
    ↓  [Codebase Pre-Scan: Deterministic static analysis]
Codebase Index (endpoints, entities, DTOs, error handlers, tests)
    ↓  [Phases 1-7: AI Negotiation with human-in-the-loop]
Formal Spec YAML (the canonical contract)
    ↓  [Deterministic Routing: spec.verification[].skill lookup]
Skill Agents (parallel: JUnit, NRQL, Gherkin, OTel, CLI checks)
    ↓  [Deterministic Execution: test runners, file validators, CLI tools]
Verification Results (JUnit XML, file existence, exit codes)
    ↓  [Deterministic Evaluation: spec.traceability.ac_mappings → verdicts]
Verdicts per AC Checkbox
    ↓  [Deterministic Jira Update: checkboxes, evidence comment, transition]
Jira Ticket → Done
```

### 2.2 The Six Dimensions of Ambiguity

Every acceptance criterion contains ambiguity across these dimensions. The negotiation protocol systematically probes each one:

1. **Actors** — Who exactly is performing the action? Authenticated user, admin, API client, system timer, another microservice?
2. **Boundaries** — What data or behavior constitutes the capability? Which fields, from which sources, in what format, with what limits?
3. **Preconditions** — What must be true before the behavior can succeed? Authentication, authorization, account state, data existence, rate limits?
4. **Failure Modes** — For every precondition, what happens when it's violated? What are ALL the ways this can fail, and what is the exact error behavior for each?
5. **Invariants** — What must NEVER happen regardless of input? Data leakage, sensitive field exposure, unauthorized state transitions, cross-tenant access?
6. **Non-Functional Constraints** — What are the performance, observability, compliance, and operational requirements? Latency SLAs, alerting thresholds, audit logging, data classification?

### 2.3 The User Workflow

```
PO writes fuzzy AC in Jira (their job, unchanged)
    ↓
Developer opens SPECify UI: localhost:8000
    ↓
Developer enters Jira ticket key
    ↓
SPECify scans the codebase (pre-scan + optional deep reads)
    ↓
AI negotiation helps the DEVELOPER formalize the AC into a spec
(The AI asks questions informed by actual code — entities, 
 endpoints, DTOs, security config, existing tests)
    ↓
Developer approves the spec (EARS summary review)
    ↓
Everything downstream is automated:
  skills generate artifacts → executed → evaluated → Jira updated
    ↓
Developer writes code to satisfy the spec (TDD)
    ↓
CI re-runs evaluation → checkboxes ticked → ticket Done
```

---

## 3. Architecture

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Browser: localhost:8000                                     │
│                                                              │
│  Single-page app (Alpine.js + Prism.js)                      │
│  ├── View 1: Negotiation (split-pane: chat + spec preview)   │
│  ├── View 2: Execution (pipeline log + streaming verdicts)   │
│  └── View 3: Results (evidence breakdown + Jira link)        │
│                                                              │
│  Communicates via 5 REST endpoints + SSE stream              │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP (localhost)
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  Python Backend (FastAPI)                                     │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  NEGOTIATION HARNESS (Sections 4 + 5)                 │    │
│  │  ├── State Machine (phase sequencing)                 │    │
│  │  ├── Context Curator (per-phase context engineering)   │    │
│  │  ├── Output Validator (structural validation)          │    │
│  │  ├── Back-Pressure Controller (circuit breakers)       │    │
│  │  ├── Observer (structured logging)                     │    │
│  │  ├── Checkpointer (resume from failure)                │    │
│  │  └── Deterministic Boundary (no AI below the spec)     │    │
│  │                                                        │    │
│  │  AI Integration:                                       │    │
│  │  ├── Raw Anthropic API (negotiation phases)            │    │
│  │  ├── Claude Agent SDK (test generation subagents)      │    │
│  │  └── Skills (.claude/skills/*.SKILL.md)                │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  DETERMINISTIC PIPELINE (Section 9-11)                │    │
│  │  ├── Skill Router (spec.verification[] → dispatch)     │    │
│  │  ├── Test Runner (subprocess: gradle/npm/pytest)       │    │
│  │  ├── Result Parsers (JUnit XML, Jest JSON, Cucumber)   │    │
│  │  ├── Evaluator (traceability map → verdicts)           │    │
│  │  └── Jira Client (read/write/comment/transition)       │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  CODEBASE INTELLIGENCE (Section 6)                    │    │
│  │  ├── Pre-Scanner (structural index, no AI)             │    │
│  │  ├── Deep Reader (targeted file reads, AI-requested)   │    │
│  │  └── Language-specific scanners (Java, Node, Python)   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  DRIFT DETECTION (Section 12)                         │    │
│  │  ├── Layer 1: Spec-tagged test failure analysis        │    │
│  │  ├── Layer 2: Spec fingerprinting                      │    │
│  │  ├── Layer 3: Source-spec cross-reference (Git hooks)  │    │
│  │  └── Layer 4: AI-assisted amendment (specify amend)    │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────┬──────────────────────────────┬───────────────────┘
            │                              │
            ▼                              ▼
┌─────────────────────┐    ┌──────────────────────────────────┐
│  EXTERNAL: AI        │    │  EXTERNAL: Jira Cloud             │
│                      │    │                                   │
│  Anthropic API       │    │  REST API v3                      │
│  (Claude Sonnet 4)   │    │  ├── Read ticket + AC             │
│                      │    │  ├── Write checkbox updates        │
│  Called during:       │    │  ├── Post evidence comments        │
│  - Negotiation       │    │  └── Transition ticket status      │
│  - Skill generation  │    │                                   │
│  - Spec amendment    │    │  Free plan (10 users, full API)   │
│                      │    │                                   │
│  NEVER called during: │    │  Called during:                   │
│  - Evaluation        │    │  - AC ingestion (Phase 0)         │
│  - Jira updates      │    │  - Checkbox updates (post-eval)   │
│  - Routing           │    │  - Evidence comment posting        │
│  - Drift detection   │    │  - Ticket transition               │
│    (layers 1-3)      │    │                                   │
└──────────────────────┘    └──────────────────────────────────┘
```

### 3.2 The File System as State Store

All state lives on the filesystem. No database. Everything is committable, auditable, and resumable.

```
.verify/
├── constitution.yaml                    # Repo context (init phase, once per repo)
├── schemas/
│   └── spec.schema.json                 # JSON Schema for spec validation
├── specs/
│   └── PROJ-1234.yaml                   # The canonical spec (negotiation output)
├── checkpoints/
│   └── PROJ-1234.yaml                   # Harness state for resume-from-failure
├── logs/
│   ├── PROJ-1234-negotiation.md         # Full conversation transcript
│   ├── PROJ-1234-harness.jsonl          # Structured harness event log
│   └── PROJ-1234-codebase-index.yaml    # Pre-scan results snapshot
├── generated/
│   ├── UserProfileVerificationTest.java # Generated by junit5_controller_test skill
│   ├── user-profile-latency.json        # Generated by newrelic_alert_config skill
│   └── UserProfile.feature              # Generated by gherkin_scenario skill
├── results/
│   ├── PROJ-1234-test-results.json      # Unified test results (parsed from JUnit XML)
│   └── PROJ-1234-verdicts.json          # Evaluator output (per-AC-checkbox verdicts)
└── fingerprints/
    └── PROJ-1234.sha256                 # Spec contract hash for drift detection

.claude/
└── skills/
    ├── codebase-explorer/
    │   └── SKILL.md                     # Codebase exploration skill
    ├── negotiate-phase-1/
    │   └── SKILL.md                     # Interface & actor discovery
    ├── negotiate-phase-4/
    │   ├── SKILL.md                     # FMEA failure mode enumeration
    │   └── references/
    │       └── fmea-patterns.md         # Common failure subcategories
    ├── negotiate-phase-5/
    │   └── SKILL.md                     # Invariant extraction
    ├── generate-junit/
    │   ├── SKILL.md                     # JUnit test generation
    │   ├── references/
    │   │   └── tag-contract.md          # Tagging conventions
    │   └── scripts/
    │       └── validate_tags.py         # Tag coverage validation
    ├── generate-nrql/
    │   ├── SKILL.md                     # New Relic alert generation
    │   └── references/
    │       └── nrql-schema.json         # Valid NRQL structure
    ├── generate-gherkin/
    │   └── SKILL.md                     # Gherkin scenario generation
    └── generate-otel/
        └── SKILL.md                     # OpenTelemetry config generation
```

---

## 4. The Harness

The harness is the central control plane. It is NOT an AI agent — it is the infrastructure that AI operates within. The harness controls what the agent sees, what it can do, when it runs, and how its output is validated.

### 4.1 Principle 1: Phase Sequencing (State Machine)

The harness owns the state machine. Claude is called within states. Claude never decides which phase comes next.

```python
class NegotiationHarness:
    """
    Sherpa-inspired state machine. Each phase is a state.
    Transitions are rule-based (exit conditions), not LLM-decided.
    """
    
    PHASES = [
        Phase("ac_ingestion",        required=["raw_ac"],              max_retries=1, uses_ai=False),
        Phase("codebase_prescan",    required=["codebase_index"],      max_retries=1, uses_ai=False),
        Phase("interface_discovery", required=["classifications"],     max_retries=2, uses_ai=True),
        Phase("happy_path",          required=["postconditions"],      max_retries=2, uses_ai=True),
        Phase("preconditions",       required=["preconditions"],       max_retries=2, uses_ai=True),
        Phase("failure_modes",       required=["failure_modes"],       max_retries=3, uses_ai=True),
        Phase("invariants",          required=["invariants"],          max_retries=2, uses_ai=True),
        Phase("completeness",        required=["completeness_check"],  max_retries=1, uses_ai=True),
        Phase("formalization",       required=["ears_statements"],     max_retries=1, uses_ai=True),
    ]

    async def run(self, context, user_callback):
        while self.current_phase_index < len(self.PHASES):
            phase = self.PHASES[self.current_phase_index]
            
            # Guard: entry condition (rule-based)
            if not self._entry_condition_met(phase):
                raise HarnessError(f"Prerequisites missing for {phase.name}")
            
            # Execute: call Claude (if AI phase) or run script (if deterministic)
            result = await self._execute_phase(phase)
            
            # Validate: structural check (rule-based, not AI)
            validation = self._validate_output(phase, result)
            if not validation.valid:
                if self.phase_attempts[phase.name] >= phase.max_retries:
                    raise HarnessError(f"{phase.name} failed after {phase.max_retries} attempts")
                continue  # Retry the same phase
            
            # Store: put validated output in context
            self._store_output(phase, result)
            
            # Checkpoint: persist to disk for resumability
            Checkpoint.save(context.jira_key, context)
            
            # Human gate: developer must approve before advancing
            if phase.uses_ai:
                approval = await user_callback(phase.name, result)
                if approval.action == "reject":
                    continue  # Re-run with corrections
            
            # Advance: move to next phase (harness decision)
            self.current_phase_index += 1
            self.observer.phase_completed(phase.name, self.phase_attempts[phase.name])
```

**Entry conditions (what each phase requires from previous phases):**

| Phase | Entry Condition |
|-------|----------------|
| ac_ingestion | Jira key provided |
| codebase_prescan | raw_ac loaded |
| interface_discovery | raw_ac + codebase_index |
| happy_path | classifications confirmed |
| preconditions | postconditions confirmed |
| failure_modes | preconditions confirmed |
| invariants | failure_modes confirmed |
| completeness | invariants confirmed |
| formalization | all prior phases confirmed |

### 4.2 Principle 2: Context Engineering

Each phase sees ONLY the context it needs. Claude never sees the full accumulated state. This prevents context rot and produces better output.

```python
class ContextCurator:
    """
    Builds curated context views for each phase.
    Phase 4 sees preconditions + error format.
    It does NOT see Phase 1 classifications, Phase 2 schemas, 
    or raw AC. This is deliberate.
    """
    
    @staticmethod
    def for_phase(phase: str, context: VerificationContext, 
                   codebase: CodebaseIndex) -> str:
        
        PHASE_VIEWS = {
            "interface_discovery": lambda ctx, cb: {
                "acceptance_criteria": ctx.ac,
                "existing_endpoints": cb.endpoints,
                "project_config": ctx.constitution["project"],
                "api_base_path": ctx.constitution.get("api", {}).get("base_path"),
            },
            "happy_path": lambda ctx, cb: {
                "api_requirements": [c for c in ctx.classifications if c["type"] == "api_behavior"],
                "relevant_entity": find_relevant_entity(ctx.classifications, cb.entities),
                "relevant_dto": find_relevant_dto(ctx.classifications, cb.dtos),
                "sensitive_fields": [f["name"] for e in cb.entities for f in e["fields"] if f.get("sensitive")],
                "auth_config": ctx.constitution.get("api", {}).get("auth", {}),
                "security_invariants": ctx.constitution.get("verification_standards", {}).get("security_invariants", []),
            },
            "preconditions": lambda ctx, cb: {
                "success_contracts": ctx.postconditions,
                "security_config": cb.security_config,
                "auth_mechanism": ctx.constitution.get("api", {}).get("auth", {}),
                "entity_constraints": extract_validation_annotations(cb.entities, ctx.classifications),
            },
            "failure_modes": lambda ctx, cb: {
                "preconditions": ctx.preconditions,
                "error_handlers": cb.error_handlers,
                "error_format": ctx.constitution.get("api", {}).get("error_format", {}),
                "common_status_codes": ctx.constitution.get("api", {}).get("common_status_codes", []),
            },
            "invariants": lambda ctx, cb: {
                "response_fields": ctx.postconditions,
                "existing_test_coverage": cb.existing_tests,
                "infra_configs": cb.infra_configs,
                "sensitive_fields": [{"entity": e["class_name"], "field": f["name"]} 
                                     for e in cb.entities for f in e["fields"] if f.get("sensitive")],
                "security_invariants": ctx.constitution.get("verification_standards", {}).get("security_invariants", []),
                "observability_config": ctx.constitution.get("observability", {}),
            },
        }
        
        view_fn = PHASE_VIEWS.get(phase)
        if not view_fn:
            raise ValueError(f"No context view defined for phase: {phase}")
        return json.dumps(view_fn(context, codebase), indent=2)
```

### 4.3 Principle 3: Output Validation

Every phase output is structurally validated before it's stored. If validation fails, the harness retries with the error message.

```python
class OutputValidator:
    """
    Deterministic structural validation. Zero AI.
    Catches: missing fields, wrong types, empty arrays,
    orphaned references, invalid IDs, schema violations.
    """
    
    VALIDATORS = {
        "classifications": validate_classifications,
        "postconditions": validate_postconditions,
        "preconditions": validate_preconditions,
        "failure_modes": validate_failure_modes,
        "invariants": validate_invariants,
    }
    
    @staticmethod
    def validate(phase: str, output: dict) -> ValidationResult:
        validator = OutputValidator.VALIDATORS.get(phase)
        if not validator:
            return ValidationResult(valid=True, errors=[])
        return validator(output)
    
    @staticmethod
    def validate_cross_references(context: VerificationContext) -> ValidationResult:
        """Run before emitting the final spec. Checks that all 
        references between phases actually resolve."""
        errors = []
        
        # Every failure mode must reference an existing precondition
        pre_ids = {p["id"] for p in (context.preconditions or [])}
        for fm in (context.failure_modes or []):
            if fm["violates"] not in pre_ids:
                errors.append(f"FAIL {fm['id']} references non-existent precondition '{fm['violates']}'")
        
        # Every AC index must map to an actual AC
        ac_indices = {ac["index"] for ac in context.ac}
        for c in (context.classifications or []):
            if c["ac_index"] not in ac_indices:
                errors.append(f"Classification references non-existent ac_index {c['ac_index']}")
        
        # Traceability map must cover every AC checkbox
        mapped = {m["ac_checkbox"] for m in context.traceability_map.get("ac_mappings", [])}
        for ac in context.ac:
            if ac["index"] not in mapped:
                errors.append(f"AC[{ac['index']}] has no traceability mapping")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
```

### 4.4 Principle 4: Back-Pressure

Hard limits that prevent runaway agents. The harness enforces these regardless of what Claude wants to do.

```python
class BackPressure:
    # Hard limits (kill the session)
    MAX_API_CALLS = 50            # Total LLM calls across all phases
    MAX_TOKENS = 500_000          # Total token budget
    MAX_RUNTIME = 600             # 10 minutes wall clock
    MAX_PHASE_RETRIES = 3         # Per individual phase
    MAX_CONSECUTIVE_FAILURES = 5  # Validation failures in a row
    MAX_DEEP_READS = 10           # Codebase files the AI can read
    
    # Soft limits (warn and adjust)
    WARN_API_CALLS = 30
    WARN_TOKENS = 300_000
    
    def check(self) -> tuple[str, str]:
        """Returns (action, reason). Action: 'continue', 'warn', 'kill'."""
        ...
```

### 4.5 Principle 5: Observability

Every harness event is logged as structured JSON. This is the audit trail for debugging and for the Jira evidence comment.

```python
class HarnessObserver:
    """Structured JSONL logging for every harness event."""
    
    def __init__(self, jira_key: str):
        self.log_path = f".verify/logs/{jira_key}-harness.jsonl"
    
    # Events logged:
    # phase_started, llm_called, validation_result, developer_interaction,
    # phase_completed, tool_call, back_pressure_triggered, skill_loaded,
    # pipeline_completed, checkpoint_saved, checkpoint_resumed,
    # codebase_deep_read, spec_fingerprint_computed, drift_detected
```

### 4.6 Principle 6: Checkpointing

After each completed phase, the context is persisted to disk. On startup, check if a checkpoint exists and offer to resume.

```python
class Checkpoint:
    CHECKPOINT_DIR = ".verify/checkpoints"
    
    @staticmethod
    def save(jira_key: str, context: VerificationContext):
        """Serialize context after each phase completion."""
        ...
    
    @staticmethod
    def load(jira_key: str) -> VerificationContext | None:
        """Load checkpoint if it exists. Returns None if no checkpoint."""
        ...
    
    @staticmethod
    def resume_phase(context: VerificationContext) -> int:
        """Determine which phase index to resume from based on populated fields."""
        ...
```

### 4.7 Principle 7: The Deterministic Boundary

The most important harness principle. Everything below the approved spec is deterministic. No AI calls during evaluation, Jira updates, or routing.

```python
class DeterministicBoundary:
    _ai_allowed = True
    
    @classmethod
    def enter_deterministic_zone(cls):
        """Called after spec approval. No more AI calls."""
        cls._ai_allowed = False
    
    @classmethod
    def check(cls, operation: str):
        """Called before any LLM API call. Raises if in deterministic zone."""
        if not cls._ai_allowed:
            raise HarnessViolation(
                f"AI call attempted in deterministic zone during '{operation}'."
            )
```

**Exception:** Skill agents that use the Agent SDK for test generation ARE allowed to call the LLM — but they operate in isolated subagent contexts that don't affect the pipeline state. The harness validates their output deterministically after they complete.

---

## 5. Multi-Agent Architecture

### 5.1 Hybrid Approach: Raw API for Negotiation, Agent SDK for Generation

The negotiation phases use the **raw Anthropic Messages API** (your code orchestrates). The test/artifact generation phase uses the **Claude Agent SDK** with skills and subagents (Claude orchestrates within constrained boundaries).

```
NEGOTIATION (Phases 0-7):
  ┌─────────────────────────────────────────────┐
  │  Your Python code is the orchestrator        │
  │  ├── Each phase = one Claude API call        │
  │  ├── Curated context per phase               │
  │  ├── Human-in-the-loop at each phase         │
  │  └── VerificationContext is shared state      │
  │                                               │
  │  WHY: Deterministic sequencing, curated       │
  │  context, maximum control, lowest cost        │
  └─────────────────────────────────────────────┘
          ↓ [Spec YAML approved and saved]
          
GENERATION (Post-approval):
  ┌─────────────────────────────────────────────┐
  │  Claude Agent SDK orchestrates subagents     │
  │  ├── Orchestrator reads spec routing table   │
  │  ├── Spawns parallel subagents per skill     │
  │  ├── Each subagent has isolated context      │
  │  ├── Skills loaded on-demand via SKILL.md    │
  │  └── Subagents return only generated files   │
  │                                               │
  │  WHY: Parallel generation, autonomous tool   │
  │  use (Read/Write/Bash), skill-driven quality │
  └─────────────────────────────────────────────┘
          ↓ [Generated files on disk]
          
EVALUATION + JIRA (Pipeline):
  ┌─────────────────────────────────────────────┐
  │  Pure Python, zero AI                        │
  │  ├── Run tests (subprocess)                  │
  │  ├── Parse results (JUnit XML / Jest JSON)   │
  │  ├── Evaluate (traceability map → verdicts)  │
  │  └── Update Jira (REST API)                  │
  │                                               │
  │  WHY: Deterministic boundary. Zero hallucination.│
  └─────────────────────────────────────────────┘
```

### 5.2 Negotiation: Raw API with Phase Skills

Each negotiation phase is a function that calls the Anthropic Messages API with a curated system prompt and curated context. The LLM sees one prompt per phase, not a growing conversation.

```python
# Each phase skill defines its own system prompt

PHASE_SKILLS = {
    "interface_discovery": {
        "system": "You are a requirements analyst...",
        "output_schema": {"classifications": [...]},
        "max_tokens": 2048,
        "model": "claude-sonnet-4-20250514",
    },
    "happy_path": {
        "system": "You are an API contract designer...",
        "output_schema": {"postconditions": [...]},
        "max_tokens": 4096,
        "model": "claude-sonnet-4-20250514",
    },
    "failure_modes": {
        "system": "You are a failure mode analyst specializing in FMEA...",
        "output_schema": {"failure_modes": [...], "security_questions": [...]},
        "max_tokens": 4096,
        "model": "claude-sonnet-4-20250514",  # Needs strong reasoning
    },
}

async def execute_phase(phase_name: str, context: VerificationContext, 
                         codebase: CodebaseIndex) -> dict:
    """One Claude API call per phase. Curated context. Structured output."""
    skill = PHASE_SKILLS[phase_name]
    curated = ContextCurator.for_phase(phase_name, context, codebase)
    
    response = client.messages.create(
        model=skill["model"],
        max_tokens=skill["max_tokens"],
        system=skill["system"],
        messages=[{"role": "user", "content": curated}]
    )
    
    return json.loads(response.content[0].text)
```

**Multi-turn refinement within a phase:**

When the developer provides corrections, the harness sends the full phase conversation:

```python
async def refine_with_corrections(phase_name, original_prompt, 
                                    ai_output, corrections):
    messages = [
        {"role": "user", "content": original_prompt},
        {"role": "assistant", "content": json.dumps(ai_output)},
        {"role": "user", "content": f"Corrections: {json.dumps(corrections)}. Update accordingly."},
    ]
    response = client.messages.create(
        model=PHASE_SKILLS[phase_name]["model"],
        max_tokens=PHASE_SKILLS[phase_name]["max_tokens"],
        system=PHASE_SKILLS[phase_name]["system"],
        messages=messages,
    )
    return json.loads(response.content[0].text)
```

### 5.3 Generation: Agent SDK with Skills and Subagents

After the spec is approved, the generation phase uses the Claude Agent SDK. The orchestrator agent reads the spec's routing table and spawns specialized subagents for each skill type.

```python
from claude_agent_sdk import (
    ClaudeAgentOptions, ClaudeSDKClient, query,
    tool, create_sdk_mcp_server, HookMatcher
)

# Custom tools for the generation phase
@tool("read_spec", "Read the approved SPECify spec YAML", {"jira_key": str})
async def read_spec(args):
    spec = yaml.safe_load(open(f".verify/specs/{args['jira_key']}.yaml"))
    return {"content": [{"type": "text", "text": yaml.dump(spec)}]}

@tool("read_constitution", "Read the repo constitution", {})
async def read_constitution(args):
    const = yaml.safe_load(open(".verify/constitution.yaml"))
    return {"content": [{"type": "text", "text": yaml.dump(const)}]}

# MCP server with custom tools
generation_tools = create_sdk_mcp_server(
    name="specify-generation",
    version="1.0.0",
    tools=[read_spec, read_constitution]
)

# Subagent definitions — each is a specialist
GENERATION_SUBAGENTS = {
    "junit-generator": {
        "description": "Generates JUnit 5 test files with @Tag annotations from spec contracts",
        "prompt": "You are a JUnit 5 test generator. Read the spec and constitution, then generate a test file following the tag contract exactly.",
        "allowed_tools": ["Read", "Write", "Bash", "Skill"],
        "model": "sonnet"
    },
    "nrql-generator": {
        "description": "Generates New Relic NRQL alert configurations from performance invariants",
        "prompt": "You are a New Relic alert config generator. Read the spec's performance invariants and generate a valid NRQL alert condition JSON.",
        "allowed_tools": ["Read", "Write", "Skill"],
        "model": "haiku"  # Simpler task, cheaper model
    },
    "gherkin-generator": {
        "description": "Generates Gherkin .feature files from EARS statements",
        "prompt": "You are a Gherkin scenario generator. Read the spec's EARS statements and generate Given/When/Then scenarios with @TAG annotations.",
        "allowed_tools": ["Read", "Write", "Skill"],
        "model": "haiku"
    },
}

ORCHESTRATOR_PROMPT = """You are the SPECify generation orchestrator.
Read the spec's verification routing table and spawn the appropriate 
subagent for each verification entry. Subagents run in parallel.
After all subagents complete, validate that every spec ref has a 
corresponding tagged artifact."""

async def run_generation(jira_key: str):
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-20250514",
        system_prompt=ORCHESTRATOR_PROMPT,
        cwd=os.getcwd(),
        setting_sources=["project"],          # Loads skills from .claude/skills/
        allowed_tools=[
            "Read", "Write", "Bash", "Glob", "Grep",
            "Skill", "Task",                   # Task = spawn subagents
            "mcp__specify-generation__read_spec",
            "mcp__specify-generation__read_constitution",
        ],
        agents=GENERATION_SUBAGENTS,
        mcp_servers=[generation_tools],
        permission_mode="acceptEdits",
    )
    
    async for message in query(
        prompt=f"Generate all verification artifacts for spec .verify/specs/{jira_key}.yaml",
        options=options
    ):
        yield message
```

### 5.4 Agent SDK Hooks — Harness Enforcement

Hooks intercept every tool call. The harness uses them to enforce rules the agent can't override.

```python
async def pre_tool_hook(input_data, tool_use_id, context):
    """Called BEFORE every tool execution in the Agent SDK."""
    tool_name = input_data["tool_name"]
    tool_input = input_data["tool_input"]
    
    # Circuit breaker
    harness_state.total_api_calls += 1
    can_continue, reason = harness_state.can_continue()
    if not can_continue:
        return deny(reason)
    
    # Block dangerous bash commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        allowed = ["cat ", "grep ", "find ", "ls ", "head ", 
                    "python scripts/", "gradle test", "npm test", "pytest"]
        if not any(command.strip().startswith(p) for p in allowed):
            return deny(f"Bash command not in allowlist: {command[:50]}")
    
    # Block reads of sensitive files
    if tool_name == "Read":
        path = tool_input.get("file_path", "")
        blocked = [".env", "secrets", "credentials", ".git/", "node_modules/"]
        if any(p in path for p in blocked):
            return deny(f"Access denied: {path}")
    
    # Block writes outside of allowed directories
    if tool_name == "Write":
        path = tool_input.get("file_path", "")
        allowed_dirs = ["src/test/", ".verify/generated/", "infra/alerts/"]
        if not any(path.startswith(d) for d in allowed_dirs):
            return deny(f"Write blocked: {path} not in allowed directories")
    
    return {}  # Allow

async def post_tool_hook(input_data, output_data, tool_use_id, context):
    """Called AFTER every tool execution."""
    # Log for observability
    harness_observer.tool_call(input_data["tool_name"], "executed")
    
    # Track token usage from the output
    if "usage" in output_data:
        harness_state.record_tokens(output_data["usage"])
    
    return {}
```

### 5.5 Skills in the Agent SDK

Skills are SKILL.md files that Claude loads on-demand. They inject domain expertise into the agent's context without bloating the system prompt.

**File location:** `.claude/skills/{skill-name}/SKILL.md`

**Discovery:** The Agent SDK scans `.claude/skills/` at startup when `setting_sources=["project"]` is set. Claude sees skill names and descriptions. When a task matches a skill's description, Claude reads the SKILL.md file, bringing its full instructions into context.

**Example: JUnit Test Generation Skill**

```markdown
# .claude/skills/generate-junit/SKILL.md
---
name: junit5-test-generator
description: >
  Use this skill when generating JUnit 5 test files from a SPECify spec.
  Triggers: "generate tests", "create JUnit", "spec to tests".
---

# JUnit 5 Test Generation from SPECify Spec

## Tag Contract (MUST follow exactly)
Every test method MUST have:
1. @Tag("{REQ-ID}") — requirement-level tag
2. @Tag("{REQ-ID}.{element-ID}") — element-level tag  
3. @DisplayName("[{REQ-ID}.{element-ID}] {description}")

## Mapping Rules
| Spec Element | Test Content |
|---|---|
| contract.success | Happy path: valid auth → assert status + body schema |
| contract.failures[N] | Negative: setup failure condition → assert status + error body |
| contract.invariants (security) | Assert forbidden fields absent, no cross-user data |
| contract.invariants (idempotency) | Call twice, assert identical responses |

## After Generation
Run `scripts/validate_tags.py` to verify every ref has a tagged test.
```

**Progressive disclosure:** The skill's description is loaded at startup (~50 tokens). The full SKILL.md content (~500-1000 tokens) is only loaded when the skill is triggered. Reference files (fmea-patterns.md, tag-contract.md) are loaded only if the SKILL.md mentions them and Claude decides to read them.

---

## 6. Repository Constitution & Codebase Intelligence

### 6.1 Constitution

The constitution is a one-time (or periodically refreshed) YAML file that captures the repo's tech stack, testing patterns, API conventions, and organizational standards. Every negotiation phase and every skill reads it.

**Location:** `.verify/constitution.yaml`
**Created by:** `specify init` command (automated scanner or manual template)
**Updated:** When the stack changes (framework upgrade, new test framework, etc.)

**Schema:** See `contracts/examples/constitution.yaml` for the complete example. Key sections:

- `project` — language, framework, build tool
- `source_structure` — where source and test files live
- `testing` — framework, assertion library, naming conventions, discovered patterns with example files
- `api` — style, base path, auth mechanism, error format, common status codes
- `observability` — APM provider, alert format, logging framework, tracing
- `conventions` — branch naming, commit format, PR template
- `verification_standards` — required verification types, security invariants, coverage minimum

### 6.2 Codebase Intelligence: Hybrid Pre-Scan + Deep Reads

**Phase 1: Pre-Scan (deterministic, no AI)**

A language-specific scanner runs at negotiation start and builds a lightweight structural index. This index tells the AI what exists in the codebase without reading every file.

```python
class CodebaseScanner:
    """Language-specific scanners. Each returns a CodebaseIndex."""
    
    def scan(self) -> CodebaseIndex:
        return CodebaseIndex(
            endpoints=self._scan_endpoints(),      # Controller methods + paths
            entities=self._scan_entities(),         # JPA/Mongoose entities + fields + sensitive flags
            dtos=self._scan_dtos(),                 # Response/Request objects
            error_handlers=self._scan_error_handlers(),  # Exception handlers + status codes
            security_config=self._scan_security_config(), # Auth mechanism + protected paths
            existing_tests=self._scan_existing_tests(),   # Test files + count + what they test
            infra_configs=self._scan_infra_configs(),      # NR, OTel, Docker, K8s, CI configs
        )

# Language-specific implementations:
class JavaSpringScanner(CodebaseScanner): ...    # @GetMapping, @Entity, @ControllerAdvice
class NodeExpressScanner(CodebaseScanner): ...   # router.get(), mongoose.Schema, errorMiddleware
class PythonFastAPIScanner(CodebaseScanner): ... # @app.get(), SQLAlchemy models, exception_handlers
```

**Scanners detect:**

| Element | Java/Spring | Node/Express | Python/FastAPI |
|---------|-------------|--------------|----------------|
| Endpoints | `@GetMapping`, `@PostMapping` | `router.get()`, `app.get()` | `@app.get()`, `@router.get()` |
| Entities | `@Entity`, `@Document` | `mongoose.Schema`, Prisma models | SQLAlchemy `Base`, Pydantic models |
| DTOs | `*Response.java`, `*Dto.java` | `*Response.ts`, interfaces | Pydantic `*Schema`, `*Response` |
| Error handlers | `@ControllerAdvice` | `app.use((err, ...))` | `@app.exception_handler` |
| Security | `SecurityFilterChain` | `passport.authenticate` | `Depends(get_current_user)` |
| Sensitive fields | `password`, `ssn`, `hash`, `salt`, `token`, `secret` in field names |

**Phase 2: Deep Reads (AI-requested, constrained)**

During negotiation, the AI can request full reads of specific files identified in the index. The harness constrains this:

- Maximum 10 deep reads per session (back-pressure)
- Only files with allowed extensions (.java, .ts, .py, .yaml, .json, .xml, .properties)
- Maximum 100 lines per file (truncated with notice)
- No .env, secrets, credentials, .git/, node_modules/, build/
- Cached — reading the same file twice doesn't count against the limit

**Two-pass phase execution:**

```
Pass 1: AI sees the index summary + curated phase context
    → Proposes output, may request deep reads
    
Pass 2 (if deep reads requested): AI gets file contents
    → Produces refined output with actual code knowledge
```

---

## 7. The Negotiation Protocol

### 7.1 Phase 0: AC Ingestion (Deterministic)

**Input:** Jira ticket key
**Output:** `VerificationContext.raw_ac`
**AI involved:** No

Calls Jira REST API to fetch the ticket. Parses Atlassian Document Format (ADF) to extract `taskList` / `taskItem` nodes as AC checkboxes. Each checkbox gets an `index`, `text`, `checked` status, and `adf_local_id` (for later updates).

### 7.2 Phase 0.5: Codebase Pre-Scan (Deterministic)

**Input:** Repository root path
**Output:** `CodebaseIndex`
**AI involved:** No

Runs the language-specific scanner. Produces structural index of endpoints, entities, DTOs, error handlers, security config, existing tests, and infrastructure configs.

### 7.3 Phase 1: Interface & Actor Discovery

**Dimensions targeted:** Actors, Boundaries (partial)
**Technique:** EARS-based classification + Constitution-guided + Codebase-informed

The AI classifies each AC by type (api_behavior, performance_sla, security_invariant, observability, compliance, data_constraint), identifies the actor, and proposes the interface. The codebase index informs accurate proposals: "I found your existing endpoint `GET /api/v1/users/me` in `UserController.java`."

**Output:** `classifications[]` — one per AC, with type, actor, interface, codebase evidence, and clarifying questions.

### 7.4 Phase 2: Happy Path Contract

**Dimensions targeted:** Boundaries (full)
**Technique:** Example-driven boundary discovery + Design by Contract postconditions + Codebase-informed schemas

The AI proposes the exact success response, informed by the actual entity fields and existing DTO: "Your `UserEntity` has 9 fields. Your `UserProfileResponse` DTO exposes 6 of them. `passwordHash`, `ssn`, and `internalId` are excluded. Should the spec match the existing DTO?"

**Output:** `postconditions[]` — success status, content type, response schema (fields, types, constraints, forbidden fields), source DTO reference.

### 7.5 Phase 3: Precondition Formalization

**Dimensions targeted:** Preconditions
**Technique:** Design by Contract + Codebase security config analysis

The AI identifies every precondition, informed by the actual security config: "Your `SecurityConfig.java` requires JWT for all `/api/**` paths. I'm formalizing this as PRE-001."

**Output:** `preconditions[]` — each with ID, description, formal expression, category, codebase evidence.

### 7.6 Phase 4: Failure Mode Enumeration

**Dimensions targeted:** Failure Modes
**Technique:** FMEA (Failure Mode and Effects Analysis) + Codebase error handler analysis

The most valuable phase. The AI systematically enumerates every failure mode, informed by existing error handlers: "Your `GlobalExceptionHandler` maps `UserNotFoundException` to 404. I'm using that for FAIL-004."

**Security analysis:** For every pair of failure modes that could return different status codes, the AI asks whether the difference leaks information.

**Output:** `failure_modes[]` — each with ID, condition, violated precondition, exact status, exact error body, security notes. Plus `security_questions_surfaced[]`.

### 7.7 Phase 5: Invariant Extraction

**Dimensions targeted:** Invariants, Non-Functional Constraints
**Technique:** EARS ubiquitous patterns + Constitution standards + Codebase inference

The AI extracts universal properties from three sources:
1. The AC text (explicit invariants like "data never exposed")
2. The constitution's `security_invariants` list
3. Inferences from the data model (email in response → PII → data classification required)

**Output:** `invariants[]` — each with ID, type (security/performance/data_integrity/compliance/idempotency/observability), rule, source, verification type.

### 7.8 Phase 6: Completeness Sweep & Verification Routing

**Dimensions targeted:** All (gap check)
**Technique:** Dimension checklist sweep + Verification routing assignment

Two tasks:
1. Run a standardized checklist (auth, authz, input validation, output schema, errors, rate limiting, pagination, caching, versioning, idempotency, observability, security, data classification, deprecation, documentation) and flag anything not covered.
2. For every requirement, assign a verification type and skill.

**Output:** `completeness_checklist` (per-dimension status), `verification_routing[]` (refs → skill → pattern → output path).

### 7.9 Phase 7: EARS Formalization & Human Approval

**Dimensions targeted:** All (final review)
**Technique:** EARS notation synthesis

Synthesizes all outputs into EARS statements — one human-readable sentence per verifiable assertion. Each EARS statement uses one of five patterns:

| Pattern | Syntax | Maps To |
|---------|--------|---------|
| UBIQUITOUS | The system SHALL... | Invariant test |
| EVENT-DRIVEN | WHEN {trigger}, the system SHALL... | Happy path test |
| STATE-DRIVEN | WHILE {state}, the system SHALL... | Preconditioned behavior test |
| UNWANTED | IF {condition}, THEN the system SHALL... | Error handling test |
| OPTIONAL | WHERE {feature}, the system SHALL... | Feature-flagged test |

The developer reviews the EARS summary and approves. On approval, the spec YAML is emitted.

---

## 8. The Spec Format

### 8.1 Format: YAML

- LLMs generate valid YAML more reliably than JSON
- YAML supports comments for inline traceability annotations
- Human-readable for demo presentations and code review
- Validated against a JSON Schema

### 8.2 Schema

```yaml
meta:
  spec_version: "1.0"
  jira_key: string
  jira_summary: string
  jira_url: string
  generated_at: iso8601
  approved_at: iso8601
  approved_by: string
  constitution_ref: string
  negotiation_log: string
  codebase_index_ref: string
  status: enum [draft, in_review, approved, superseded]

context:
  relevant_source_files: list[string]
  relevant_test_files: list[string]
  related_specs: list[string]

requirements:
  - id: string              # REQ-001
    ac_checkbox: integer     # Jira AC checkbox index
    ac_text: string          # Original AC text verbatim
    title: string
    type: enum [api_behavior, data_constraint, performance_sla, 
                security_invariant, observability, compliance]

    ears: list
      - type: enum [ubiquitous, event_driven, state_driven, unwanted, optional]
        when/if/while/where: string
        shall/then: string

    contract:
      interface:
        method: enum [GET, POST, PUT, PATCH, DELETE]
        path: string
        auth: string
        discovered_from: string  # Source file reference
        
      preconditions: list
        - id: string           # PRE-001
          description: string
          formal: string       # Semi-formal expression
          category: enum [authentication, authorization, data_existence, 
                         data_state, rate_limit, system_health]

      success:
        status: integer
        content_type: string
        schema:
          type: string
          required: list[string]
          properties: object
          forbidden_fields: list[string]
          source_dto: string   # DTO class this matches

      failures: list
        - id: string           # FAIL-001
          when: string
          violates: string     # PRE-xxx reference
          status: integer
          body: object

      invariants: list
        - id: string           # INV-001
          type: enum [security, performance, data_integrity, 
                     compliance, idempotency, observability]
          rule: string

    verification: list
      - refs: list[string]
        skill: string
        pattern: string        # Constitution test pattern reference
        output: string         # File path for generated artifact
        framework: string

traceability:
  ac_mappings: list
    - ac_checkbox: integer
      ac_text: string
      adf_local_id: string   # For Jira checkbox update
      pass_condition: enum [ALL_PASS, ANY_PASS, PERCENTAGE]
      threshold: number       # For PERCENTAGE
      required_verifications: list
        - ref: string         # e.g., "REQ-001.FAIL-002"
          description: string
          verification_type: enum [
            test_result, deployment_check, config_validation,
            api_health_check, log_assertion, metric_query,
            cli_exit_code, manual_gate
          ]
          confidence: enum [strongest, strong, medium, weaker, weakest]
          check_details: object  # Type-specific parameters
```

### 8.3 The Tag Contract

Every generated test method is tagged with its spec ref. The evaluator matches tags to traceability map refs.

| Framework | Tag Format |
|-----------|-----------|
| JUnit 5 | `@Tag("REQ-001.FAIL-002")` + `@DisplayName("[REQ-001.FAIL-002] description")` |
| Jest | `it('[REQ-001.FAIL-002] description', ...)` inside `describe('[REQ-001]', ...)` |
| Pytest | `@pytest.mark.spec("REQ-001.FAIL-002")` |
| Cucumber | `@REQ-001.FAIL-002` scenario tag |

---

## 9. Verification Engine

### 9.1 Verification Types

**Category 1: Test-Based** — Produces a test file with tagged methods. Evaluator parses test runner output.

| Skill | What It Proves | Output | Execution |
|-------|---------------|--------|-----------|
| junit5_controller_test | API behavior matches contract | Java test file | `gradle test` |
| jest_unit_test | Business logic matches contract | JS/TS test file | `npm test` |
| pytest_unit_test | Python logic matches contract | Python test file | `pytest --junitxml` |
| schema_contract_test | Response shape matches schema | Contract test | Test runner |
| property_based_test | Invariants hold for random inputs | Property test | Test runner + fuzzer |
| gherkin_scenario | Human-readable behavior doc | .feature file | Cucumber/Behave |
| audit_log_assertion | Compliance logging exists | Log assertion test | Test runner |
| data_classification_check | PII properly labeled | Header check test | Test runner |

**Category 2: Artifact-Based** — Produces a config file. Evaluator checks existence + schema validity.

| Skill | What It Proves | Output |
|-------|---------------|--------|
| newrelic_alert_config | Performance SLA monitored | NRQL JSON config |
| otel_instrumentation | Observability in place | OTel config YAML |
| security_scan_config | Vulnerability scanning configured | Scanner config |
| load_test_config | Performance test defined | k6/Gatling script |

**Category 3: CLI-Based** — Runs a tool, checks exit code. Binary pass/fail.

| Skill | What It Proves | Command |
|-------|---------------|---------|
| dependency_audit | No critical CVEs | `npm audit --audit-level=critical` |
| secret_scan | No secrets in code | `gitleaks detect --source .` |
| openapi_diff | API spec matches implementation | `openapi-diff spec.yaml live` |
| db_migration | Schema change backwards-compatible | `flyway validate` |
| accessibility_check | UI meets WCAG standards | `pa11y --standard WCAG2AA` |

**Category 4: Runtime** — Checks against a live/deployed system.

| Skill | What It Proves | Method |
|-------|---------------|--------|
| api_health_probe | Endpoint responds correctly | HTTP GET, check status |
| metric_query | Live metric meets threshold | NRQL query against New Relic API |

### 9.2 Hierarchy of Provability

| Strength | Type | What It Actually Proves | Limitation |
|----------|------|------------------------|------------|
| **Strongest** | test_result (unit/integration) | Code behaves correctly for specific inputs | Only proves tested scenarios |
| **Strong** | test_result (property-based) | Invariant holds for random inputs | Probabilistic, not exhaustive |
| **Strong** | cli_exit_code (SAST/CVE scan) | No known vulnerabilities at scan time | New CVEs discovered tomorrow |
| **Medium** | deployment_check (config file) | Config artifact exists and is valid | Doesn't prove it's deployed/active |
| **Medium** | config_validation (entry check) | Config contains required entries | Doesn't prove values are correct |
| **Medium** | api_health_check (live probe) | Endpoint responds correctly now | Doesn't prove it will in 5 minutes |
| **Weaker** | cli_exit_code (a11y scanner) | No violations found by scanner | Scanners don't catch everything |
| **Weakest** | deployment_check (doc exists) | Documentation exists at path | Doesn't prove it's accurate |

### 9.3 The Universe of "Usually Untested" Things

The negotiation engine (Phases 5-6) proactively surfaces these even when the PO didn't write them:

- **Configuration & Infrastructure**: Alerting rules, dashboard panels, feature flags, rate limiting, CORS, container security, resource limits
- **Observability & Ops**: Structured logging, distributed tracing, health endpoints, readiness probes, runbooks, graceful degradation
- **Security Posture**: Dependency CVEs, SAST, security headers, secrets in code, auth enforcement, audit trails
- **Data Governance**: Data classification, retention policies, GDPR erasure, accessibility, localization, consent management
- **Documentation**: API docs (OpenAPI), changelogs, ADRs, migration guides
- **Deployment**: DB migrations, backwards compatibility, smoke tests, feature toggle defaults
- **Cross-System**: Event schemas, downstream SLAs, API version contracts, message ordering

---

## 10. Evaluation Engine

### 10.1 Purpose

100% deterministic. Zero AI. Reads the spec's traceability map and verification results. Produces a verdict per AC checkbox.

### 10.2 Evaluation Strategies

Each `verification_type` in the traceability map has a corresponding evaluation strategy:

| Type | Strategy | How It Checks |
|------|----------|---------------|
| `test_result` | Parse JUnit XML / Jest JSON / Cucumber JSON, match @Tag to spec ref | Tag match → check test status |
| `deployment_check` | Check file exists + parseable + optional schema validation | File present + valid |
| `config_validation` | Check file contains required entries (span names, metric names) | String presence in config |
| `cli_exit_code` | Run CLI command, check exit code == expected | Exit code match |
| `api_health_check` | HTTP GET, check status code + optional body match | Status code match |
| `log_assertion` | Check log file contains required structured fields | Field presence |
| `metric_query` | Query APM API, compare metric against threshold | Metric vs. threshold |
| `manual_gate` | Check if human approval recorded in context | Approval record |

### 10.3 Pass Condition Logic

| Condition | Logic |
|-----------|-------|
| `ALL_PASS` | Checkbox passes only if every required verification passes |
| `ANY_PASS` | Checkbox passes if at least one verification passes |
| `PERCENTAGE` | Checkbox passes if pass rate ≥ threshold |

### 10.4 Test Result Parsers

The evaluator supports three test output formats, all parsed into a unified structure:

```json
{
  "test_cases": [
    {
      "name": "should_return_401_when_jwt_expired",
      "classname": "com.example.UserProfileVerificationTest",
      "display_name": "[REQ-001.FAIL-002] Returns 401 when JWT expired",
      "tags": ["PROJ-1234", "REQ-001", "REQ-001.FAIL-002"],
      "status": "passed",
      "duration_ms": 92,
      "failure_message": null
    }
  ]
}
```

**Tag extraction methods:**
- JUnit XML: `<property name="tag" value="REQ-001.FAIL-002">` or regex on `@DisplayName`
- Jest JSON: regex `\[([A-Z]+-\d+\.\S+)\]` on `fullName` and `ancestorTitles`
- Cucumber JSON: `@TAG` annotations on scenario elements

---

## 11. Jira Integration

### 11.1 AC Ingestion (Read)

- `GET /rest/api/3/issue/{key}` with fields=description,summary,status,labels,components
- Parse ADF `taskList` / `taskItem` nodes for AC checkboxes
- Extract `localId` for each taskItem (needed for checkbox updates)
- Store in `VerificationContext.raw_ac`

### 11.2 Checkbox Update (Write)

- `GET` current description ADF
- Walk ADF content tree, find `taskItem` by `localId`
- Change `state: "TODO"` to `state: "DONE"` for passed checkboxes
- `PUT` the entire updated description back (Jira doesn't support partial ADF updates)

### 11.3 Evidence Comment (Write)

- `POST /rest/api/3/issue/{key}/comment` (use v2 API with wiki markup for simplicity)
- Comment includes: overall pass/fail, per-AC-checkbox breakdown, per-ref evidence table with verification type, spec file path, traceability statement
- Posted regardless of pass/fail (failures are documented too)

### 11.4 Ticket Transition (Write)

- `GET /rest/api/3/issue/{key}/transitions` to discover available transition IDs
- Match by transition name (IDs vary per project workflow)
- `POST /rest/api/3/issue/{key}/transitions` with matched ID
- All pass → "Done"; partial pass → "In Review" or unchanged

---

## 12. Spec Drift Detection

Four layers, ordered from simplest to most sophisticated:

### Layer 1: CI Test Failure with Spec Context (Free)

When a spec-tagged test fails, the CI report includes the spec ref. "Test `@Tag(REQ-001.FAIL-002)` failed — spec says status 401, actual 403." No extra work needed — the tagged tests are the drift detection.

**Catches:** Code changed and broke existing behavior.
**Misses:** Additive changes (new field added, tests still pass but spec is incomplete), spec updated but tests not regenerated.

### Layer 2: Spec Fingerprinting (30 lines of code)

After test generation, hash the spec's contract sections. Embed the hash in the generated test file header. In CI, recompute and compare.

```python
def compute_spec_fingerprint(spec_path: str) -> str:
    spec = yaml.safe_load(open(spec_path))
    contract_str = json.dumps(spec.get("requirements", []), sort_keys=True)
    return hashlib.sha256(contract_str.encode()).hexdigest()[:16]
```

Generated test file header:
```java
// SPECify fingerprint: sha256:a3f2b8c1e4f56789
// Generated from: .verify/specs/PROJ-1234.yaml
// Spec version: 2026-03-22T14:35:00Z
```

**Catches:** Spec updated but tests not regenerated.
**Misses:** Code changed but spec not updated.

### Layer 3: Source-Spec Cross-Reference (CI config)

A CI check reads the spec's `context.relevant_source_files` and flags if any are modified in the PR.

```yaml
# GitHub Actions step
- name: Check spec relevance
  run: |
    CHANGED=$(git diff --name-only origin/main)
    for spec in .verify/specs/*.yaml; do
      SOURCE_FILES=$(python -c "import yaml; s=yaml.safe_load(open('$spec')); [print(f) for f in s.get('context',{}).get('relevant_source_files',[])]")
      for src in $SOURCE_FILES; do
        echo "$CHANGED" | grep -q "$src" && echo "⚠️ $src modified, referenced by $spec"
      done
    done
```

**Catches:** Source code changed for a spec'd component.
**Misses:** Doesn't identify WHAT changed — just that something did.

### Layer 4: AI-Assisted Amendment (Production feature)

When Layer 3 flags a source-spec mismatch AND tests fail, trigger an automated amendment flow:

```bash
specify amend PROJ-1234 --diff PR#456
```

The amend command:
1. Reads the current spec
2. Reads the git diff for relevant files
3. Sends both to the AI: "Here's the spec and here's what changed. What needs updating?"
4. AI proposes targeted amendments (not full re-negotiation)
5. Developer reviews and approves in the PR
6. Tests regenerated from amended spec
7. Updated spec + tests committed to the same PR

**The full drift detection stack:**
```
Layer 1: Tagged test fails → developer knows which spec element broke
Layer 2: Fingerprint mismatch → "spec changed, tests stale"
Layer 3: Source file changed → "code changed, spec might be stale"
Layer 4: AI amendment → "here's what needs updating in the spec"
```

---

## 13. Web UI & API Contract

### 13.1 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python) |
| Frontend | HTML + Alpine.js (8kb, zero build) + Prism.js (YAML highlighting) |
| Streaming | Server-Sent Events (SSE) |
| State | File system (no database) |

### 13.2 REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/start | Fetch Jira ticket, start session |
| POST | /api/message | Send developer response, get AI output |
| POST | /api/approve | Approve spec, trigger generation |
| POST | /api/execute | Run pipeline (streamed via SSE) |
| GET | /api/spec/{id} | Get current spec YAML |

### 13.3 SSE Event Types

| Stage | Payload |
|-------|---------|
| generating | skill, output, status |
| running_tests | runner, progress, status |
| evaluating | ac_checkbox, passed, summary |
| updating_jira | action (checkbox_ticked, comment_posted, transitioned) |
| complete | all_passed, verdicts_path, jira_comment_url, duration_ms |
| error | error, phase, details |

### 13.4 UI Views

**View 1: Negotiation** — Split-pane: chat conversation (left) + live YAML spec preview (right). Phase progress bar top. Input box bottom with Send and Approve buttons.

**View 2: Execution** — Pipeline log streaming (left) + spec with verification entries lighting up green (right). SSE events update in real-time.

**View 3: Results** — Evidence breakdown by AC checkbox. Each ref shows verification type, pass/fail, details. Link to Jira ticket.

---

## 14. CLI Interface

```bash
# Primary: web UI
specify start                          # Launch at localhost:8000

# Full pipeline
specify PROJ-1234                      # negotiate + execute (web UI)

# Step-by-step
specify init                           # Scan repo, generate constitution
specify negotiate PROJ-1234            # Negotiation (web UI)
specify generate PROJ-1234             # Spec → verification artifacts
specify run PROJ-1234                  # Execute tests
specify evaluate PROJ-1234             # Results → verdicts
specify update-jira PROJ-1234          # Verdicts → Jira

# Shortcuts
specify execute PROJ-1234              # generate + run + evaluate + update-jira

# Drift detection
specify check PROJ-1234                # Run Layer 1-3 drift checks
specify amend PROJ-1234 --diff HEAD~1  # AI-assisted spec amendment

# Utilities
specify status PROJ-1234               # Pipeline state for this ticket
specify show-spec PROJ-1234            # Pretty-print spec YAML
specify show-verdicts PROJ-1234        # Evaluation results
specify show-evidence PROJ-1234        # What would be posted to Jira
specify resume PROJ-1234               # Resume from checkpoint
```

---

## 15. Data Contracts

Every data handoff in the pipeline has a defined contract. See the `contracts/` directory for complete schemas and examples:

### 15.1 Contract Flow

```
ac-input.yaml        → (Jira → Harness)
constitution.yaml     → (Init → Everything)
codebase-index.yaml   → (Scanner → Negotiation Phases)
phase-outputs.json    → (Each Phase → Harness → Spec Compiler)
spec.yaml             → (Compiler → Skills, Evaluator, Jira Updater)
test-results.json     → (Test Runner Parsers → Evaluator)
verdicts.json         → (Evaluator → Jira Updater, Web UI)
jira-api-payloads.yaml → (Jira Updater → Jira Cloud API)
api-endpoints.yaml    → (Backend → Frontend)
skill-interface.yaml  → (Skill Framework → Skill Authors)
harness-state.yaml    → (Harness → Checkpoint File)
```

### 15.2 Key Contract: The Spec YAML

The spec YAML is the canonical contract. Everything upstream produces it. Everything downstream consumes it. It is the boundary between intelligence and automation.

Three layers within the spec:
1. **EARS statements** — Human-readable, what the developer reviews and approves
2. **Contract** — Machine-precise, what the skill agents translate into test code
3. **Traceability map** — The evaluation map, what the evaluator reads to produce verdicts

### 15.3 Key Contract: Verdicts JSON

The evaluator's output. One verdict per AC checkbox with `passed`, `pass_condition`, and evidence array. Also includes `jira_actions` — the deterministic list of Jira API calls to make.

---

## 16. Development & Deployment

### 16.1 Jira Cloud Setup

Jira Cloud free plan: free forever, up to 10 users, full REST API access. Setup in 5 minutes:
1. Create site at `atlassian.com/software/jira/free`
2. Create project, create ticket with AC checkboxes
3. Generate API token at `id.atlassian.com/manage-profile/security/api-tokens`

### 16.2 Python Environment

```bash
pip install fastapi uvicorn pyyaml requests anthropic
# Optional: claude-agent-sdk (for generation phase)
pip install claude-agent-sdk
```

### 16.3 Environment Variables

```bash
JIRA_BASE_URL=https://yoursite.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
ANTHROPIC_API_KEY=your-key
```

### 16.4 Running

```bash
# Development
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```
