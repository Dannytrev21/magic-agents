# Magic Agents — System Design

## Intent-to-Verification Spec Engine

Transforms fuzzy Jira acceptance criteria into formal, machine-verifiable specifications through AI-driven negotiation, then dispatches to **Claude Agent Skills** that generate verification artifacts (tests, alert configs, compliance scenarios), runs them, and feeds verdicts back to Jira — closing the loop from business intent to verified software.

Both sides of the pipeline — **spec generation** (negotiation phases) and **proof-of-correctness generation** (verification skills) — are implemented as [Agent Skills](https://agentskills.io) following the SKILL.md open standard with progressive disclosure.

**Stack:** Python 3.11+ / FastAPI / pytest / Claude API
**References:** [reference-library.md](../reference-library.md) | [agent-skills-reference.md](../agent-skills-reference.md) | [ac-to-specs-plan.md](../ac-to-specs-plan.md)

---

## 1. End-to-End Pipeline

```mermaid
flowchart LR
    Jira["Jira Ticket\n(AC checkboxes)"] --> Ingest["AC Ingestion"]
    Ingest --> Negotiate["AI Negotiation\nPhases 1-4"]
    Negotiate --> Synthesis["Synthesis\n(invariants, EARS,\ntraceability)"]
    Synthesis --> Compile["Spec Compiler"]
    Compile --> Spec[".verify/specs/*.yaml"]
    Spec --> Route["Routing Table\n(deterministic)"]
    Route --> Generate["Agent Skills\n(proof-of-correctness\ngenerators)"]
    Generate --> Tests[".verify/generated/*\n(tests, configs,\nscenarios)"]
    Tests --> Run["Test Runner\n(pytest + JUnit XML)"]
    Run --> Evaluate["Evaluator\n(zero AI)"]
    Evaluate --> Verdicts["Verdicts\n(per AC checkbox)"]
    Verdicts --> Jira
```

---

## 2. Two-Zone Architecture

The spec YAML is the intelligence boundary. Both zones use **Claude Agent Skills** — but for fundamentally different purposes.

```mermaid
flowchart TB
    subgraph ai["AI ZONE — Spec Generation Agent Skills"]
        direction LR
        P1["Phase 1 Skill\nClassify ACs"] --> P2["Phase 2 Skill\nPostconditions"]
        P2 --> P3["Phase 3 Skill\nPreconditions"]
        P3 --> P4["Phase 4 Skill\nFailure Modes"]
        P4 --> SYN["Synthesis\n(deterministic)"]
    end

    SYN --> SPEC["SPEC YAML\n(.verify/specs/*.yaml)"]

    subgraph poc["PROOF-OF-CORRECTNESS — Verification Agent Skills"]
        direction LR
        RT["Routing\nTable"] --> SK1["pytest Skill"]
        RT --> SK2["NewRelic Skill"]
        RT --> SK3["Gherkin Skill"]
        RT --> SK4["OTel Skill"]
    end

    SPEC --> RT

    subgraph det["DETERMINISTIC ZONE — Execution & Evaluation"]
        direction LR
        RUN["Test\nRunner"] --> EVAL["Evaluator"]
        EVAL --> JIRA["Jira\nUpdates"]
    end

    SK1 & SK2 & SK3 & SK4 --> RUN
```

**Spec Generation Skills** (`.claude/skills/phase*-*/SKILL.md`) — AI interprets fuzzy AC into structured contracts through negotiation with the developer. Each phase is a Claude Agent Skill with constitutional rules.

**Proof-of-Correctness Skills** (`.claude/skills/verify-*/SKILL.md`) — Agent Skills that read the spec contract and generate verification artifacts: pytest tests, New Relic alert configs, Gherkin scenarios, OTel configs. Each skill follows the same SKILL.md standard — metadata for discovery, instructions for generation, templates as resources.

**Execution & Evaluation** — Fully deterministic. Run the generated artifacts, parse results, map back to AC checkboxes via the traceability map.

---

## 3. Epic Dependency Graph

```mermaid
flowchart TD
    E0["Epic 0\nBullet Tracer\n6 features"]:::done --> E1["Epic 1\nJira Integration\n4 features"]:::done
    E0 --> E2["Epic 2\nAI Negotiation\n7 features"]:::done
    E1 --> E2
    E2 --> E3["Epic 3\nFormal Spec\n3 features"]:::done
    E3 --> E4["Epic 4\nSkill Routing\n3 features"]:::mvp
    E0 --> E5["Epic 5\nEvaluation\n3 features"]:::mvp
    E4 --> E5
    E1 --> E6["Epic 6\nJira Feedback\n3 features"]:::mvp
    E5 --> E6
    E2 --> E7["Epic 7\nConstitution\n3 features"]:::stretch
    E2 --> E8["Epic 8\nAdv. Negotiation\n3 features"]:::stretch
    E4 --> E9["Epic 9\nBeyond-Code Skills\n3 features"]:::stretch
    E6 --> E10["Epic 10\nCI/CD\n3 features"]:::stretch

    classDef done fill:#00b894,color:#fff,stroke:#00b894
    classDef mvp fill:#6c5ce7,color:#fff,stroke:#6c5ce7
    classDef stretch fill:#636e72,color:#fff,stroke:#636e72
```

**Legend:** Green = complete | Purple = MVP (next) | Gray = stretch

---

## 4. Negotiation State Machine

The `NegotiationHarness` drives the `VerificationContext` through phases with guard conditions on each transition. Each phase includes validation, optional evaluator-optimizer critique, and checkpointing.

```mermaid
stateDiagram-v2
    [*] --> Plan: read all ACs
    Plan --> Phase0: plan confirmed
    Phase0 --> Phase1: all ACs classified
    Phase1 --> Phase2: all api_behaviors\nhave postconditions
    Phase2 --> Phase3: preconditions populated
    Phase3 --> Phase4: failure modes reference\nvalid preconditions
    Phase4 --> Synthesis: all failure modes valid
    Synthesis --> Compile: invariants + EARS +\ntraceability built
    Compile --> [*]: .verify/specs/{key}.yaml

    state Phase0 {
        [*] --> Generate: LLM call
        Generate --> Validate: raw output
        Validate --> Retry: schema errors
        Retry --> Generate
        Validate --> Evaluate: structurally valid
        Evaluate --> Improve: gaps found
        Improve --> Generate
        Evaluate --> Present: complete
        Present --> Revise: developer feedback
        Revise --> Generate
        Present --> Checkpoint: approved
        Checkpoint --> [*]: saved
    }

    Plan: Plan-then-Execute (negotiation plan)
    Phase0: Phase 0 — Interface & Actor Discovery
    Phase1: Phase 1 — Happy Path Contract
    Phase2: Phase 2 — Precondition Formalization
    Phase3: Phase 3 — Failure Mode Enumeration
    Phase4: Phase 4 — Final Review
    Synthesis: Synthesis (zero AI)
    Compile: Spec Compilation (zero AI)
```

**Inner phase flow:** Generate → Validate (deterministic) → Evaluate (LLM critique) → Present (developer) → Checkpoint (persist). The evaluator-optimizer and checkpoint patterns apply to every phase.

---

## 5. VerificationContext Lifecycle

The single data object that threads through every phase, accumulating structured knowledge.

```mermaid
sequenceDiagram
    participant J as Jira
    participant H as Harness
    participant P1 as Phase 1
    participant P2 as Phase 2
    participant P3 as Phase 3
    participant P4 as Phase 4
    participant S as Synthesis
    participant C as Compiler
    participant G as Generator
    participant E as Evaluator

    J->>H: jira_key, summary, raw_ac[]
    H->>P1: context
    P1-->>H: + classifications[]
    Note over P1: Developer feedback loop
    H->>P2: context
    P2-->>H: + postconditions[]
    H->>P3: context
    P3-->>H: + preconditions[]
    H->>P4: context
    P4-->>H: + failure_modes[]
    H->>S: context (all phases done)
    S-->>H: + invariants[], ears[], traceability_map
    H->>C: context (full)
    C-->>C: .verify/specs/{key}.yaml
    C->>G: spec YAML
    G-->>G: .verify/generated/test_{key}.py
    G->>E: test results
    E-->>J: verdicts → tick checkboxes
```

---

## 6. Agent Skills Architecture

**Both spec generation and proof-of-correctness generation are Claude Agent Skills.** They follow the same [SKILL.md open standard](https://agentskills.io) with the same progressive disclosure pattern — the only difference is what they produce.

```mermaid
flowchart TB
    subgraph spec_skills["SPEC GENERATION SKILLS\n(.claude/skills/phase*-*/SKILL.md)"]
        direction LR
        PS1["phase1-classification\nSKILL.md + SCHEMA.md"]
        PS2["phase2-postconditions\nSKILL.md + SCHEMA.md"]
        PS3["phase3-preconditions\nSKILL.md"]
        PS4["phase4-failure-modes\nSKILL.md"]
    end

    PS4 --> SPEC["SPEC YAML"]
    SPEC --> RT["ROUTING_TABLE\n(deterministic dispatch)"]

    subgraph poc_skills["PROOF-OF-CORRECTNESS SKILLS\n(.claude/skills/verify-*/SKILL.md)"]
        direction LR
        VS1["verify-pytest\nSKILL.md + TEMPLATES.md"]
        VS2["verify-newrelic\nSKILL.md"]
        VS3["verify-gherkin\nSKILL.md"]
        VS4["verify-otel\nSKILL.md"]
    end

    RT --> VS1 & VS2 & VS3 & VS4

    subgraph loading["Progressive Disclosure — Same for Both Skill Types"]
        L1["Level 1: Metadata\nname + description\n~100 tokens, always loaded"]
        L2["Level 2: Instructions\nSKILL.md body\nloaded when skill triggers"]
        L3["Level 3: Resources\nSCHEMA.md, TEMPLATES.md, scripts\nloaded on demand"]
    end
```

### How the Two Skill Types Compare

| | Spec Generation Skills | Proof-of-Correctness Skills |
|---|---|---|
| **Location** | `.claude/skills/phase*-*/` | `.claude/skills/verify-*/` |
| **Input** | Raw AC + constitution | Spec contract + constitution |
| **Output** | Structured data on VerificationContext | Verification artifacts (tests, configs, scenarios) |
| **AI role** | Interpret, classify, propose, negotiate | Generate code/configs from structured spec |
| **Validation** | `validate.py` (enum checks) | `tag_enforcer.py` (spec ref coverage) |
| **Developer interaction** | Feedback loop (approve/revise) | None (deterministic dispatch) |
| **Standard** | SKILL.md + SCHEMA.md | SKILL.md + TEMPLATES.md |

### Block's 3 Principles Applied (Both Skill Types)

| Principle | Spec Skills | Verification Skills |
|-----------|-------------|---------------------|
| **1. NOT decide** | `validate.py` enums, guard conditions | `tag_enforcer.py`, routing table |
| **2. SHOULD decide** | Interpreting AC, clarifying questions | Adapting templates to contract shapes |
| **3. Constitutional rules** | `MUST`/`FORBIDDEN` in prompts | `MUST tag every ref`, `MUST use TestClient` |

---

## 7. Routing Table

Deterministic mapping from requirement type to verification skill (zero AI):

| Requirement Type | Skill | Framework | Output Pattern |
|-----------------|-------|-----------|----------------|
| `api_behavior` | `pytest_unit_test` | pytest | `.verify/generated/test_{key}.py` |
| `performance_sla` | `newrelic_alert_config` | newrelic | `.verify/generated/{key}_alerts.json` |
| `security_invariant` | `pytest_unit_test` | pytest | `.verify/generated/test_{key}_security.py` |
| `observability` | `otel_config` | opentelemetry | `.verify/generated/{key}_otel.yaml` |
| `compliance` | `gherkin_scenario` | behave | `.verify/generated/{key}_compliance.feature` |
| `data_constraint` | `pytest_unit_test` | pytest | `.verify/generated/test_{key}_data.py` |

---

## 8. Epic Summary

| Epic | Name | Features | Agentic Patterns | Status | Playbook |
|------|------|----------|-----------------|--------|----------|
| 0 | Bullet Tracer | 6 | — | Foundation | [epic-0](epic-0-bullet-tracer/PLAYBOOK.md) |
| 1 | Jira Integration | 4 | — | Foundation | [epic-1](epic-1-jira-integration/PLAYBOOK.md) |
| 2 | AI Negotiation | 7 | State machine, belief system, feedback loop, constitutional AI, **checkpoint & resume, evaluator-optimizer, plan-then-execute** | Complete (patterns pending) | [epic-2](epic-2-ai-negotiation/PLAYBOOK.md) |
| 3 | Formal Spec Emission | 3 | Two-zone architecture, deterministic validation | Complete | [epic-3](epic-3-formal-spec/PLAYBOOK.md) |
| 4 | Verification Agent Skills | 3 | Progressive disclosure, Block's 3 Principles | MVP Next | [epic-4](epic-4-skill-routing/PLAYBOOK.md) |
| 5 | Evaluation Engine | 3 | Back-pressure (tag enforcement) | MVP Next | [epic-5](epic-5-evaluation/PLAYBOOK.md) |
| 6 | Jira Feedback | 3 | — | MVP Next | [epic-6](epic-6-jira-feedback/PLAYBOOK.md) |
| 7 | Constitution & RAG | 3 | **Code-grounded negotiation (RAG)** | Stretch | [epic-7](epic-7-constitution/PLAYBOOK.md) |
| 8 | Advanced Negotiation | 3 | **Multi-agent debate**, evaluator-optimizer | Stretch | [epic-8](epic-8-advanced-negotiation/PLAYBOOK.md) |
| 9 | Beyond-Code Skills | 3 | Progressive disclosure | Stretch | [epic-9](epic-9-verification-skills/PLAYBOOK.md) |
| 10 | CI/CD | 3 | **Spec drift detection** | Stretch | [epic-10](epic-10-cicd/PLAYBOOK.md) |

---

## 9. Agentic Patterns

Patterns that shape how AI agents operate within the pipeline. Each maps to a specific epic.

### Implemented

```mermaid
flowchart LR
    subgraph implemented["Currently Implemented"]
        SM["State Machine\nOrchestration"] --- BS["Belief System\n(VerificationContext)"]
        BS --- PD["Progressive\nDisclosure"]
        PD --- CA["Constitutional AI\n(Block P3)"]
        CA --- DV["Deterministic\nValidation (Block P1)"]
        DV --- TZ["Two-Zone\nArchitecture"]
        TZ --- FL["Feedback Loop\n(multi-turn)"]
    end
```

### Planned

```mermaid
flowchart TB
    subgraph high["HIGH PRIORITY"]
        CP["Checkpoint & Resume\nSerialize context after each phase\nResume from last checkpoint"]
        EO["Evaluator-Optimizer\nSecond LLM critiques output\nbefore showing developer"]
    end

    subgraph medium["MEDIUM PRIORITY"]
        PE["Plan-then-Execute\nAI proposes negotiation plan\nbefore diving into phases"]
        RAG["Code-Grounded Negotiation\nLLM reads actual source code\nto ground proposals in reality"]
    end

    subgraph low["STRETCH"]
        OW["Orchestrator-Worker\nParallel sub-agents per AC\nMerge + resolve conflicts"]
        MAD["Multi-Agent Debate\nTwo personas argue\nsecurity tradeoffs"]
        SD["Spec Drift Detection\nCI detects when code\nbreaks the spec contract"]
    end

    CP --> PE
    EO --> RAG
    PE --> OW
    RAG --> MAD
```

### Pattern Details

#### Checkpoint & Resume (Epic 2 enhancement)

**Problem:** Negotiation takes 10+ minutes. If the browser closes, all state is lost.
**Pattern:** Serialize `VerificationContext` to `.verify/sessions/{jira_key}/` after each phase advance. On startup, check for existing sessions and offer to resume.

```
.verify/sessions/{jira_key}/
├── checkpoint_phase0.json    # After classification
├── checkpoint_phase1.json    # After postconditions
├── checkpoint_phase2.json    # After preconditions
├── checkpoint_phase3.json    # After failure modes
├── checkpoint_synthesis.json # After synthesis
└── negotiation_log.jsonl     # Full conversation history
```

**Implementation:** The harness calls `save_checkpoint()` after each `advance_phase()`. The web UI checks for sessions on load and shows a "Resume" option. Maps to Sherpa's "agent persistence across sessions" capability ([reference-library.md §1](../reference-library.md#1-sherpa--model-driven-agent-orchestration-via-state-machines)).

#### Evaluator-Optimizer (Epic 2 enhancement)

**Problem:** LLM output can have subtle gaps (missing precondition categories, inconsistent status codes) that pass validation but aren't caught until the developer reviews.
**Pattern:** After each phase produces output, a second LLM call with an adversarial evaluator persona critiques it before presenting to the developer.

```mermaid
sequenceDiagram
    participant P as Phase Skill
    participant V as Validate.py
    participant E as Evaluator Skill
    participant D as Developer

    P->>V: Raw LLM output
    V->>V: Enum/schema check
    V->>E: Structurally valid output
    E->>E: "Missing rate_limit precondition"
    E->>P: Critique + retry
    P->>V: Improved output
    V->>E: Re-evaluate
    E->>D: "Looks complete"
```

**Implementation:** A new Agent Skill at `.claude/skills/evaluator-optimizer/SKILL.md` with constitutional rules like "check every precondition category is addressed" and "verify failure modes cover both happy and unhappy subcategories." The harness calls it between validation and developer presentation. Maps to harness engineering's back-pressure pattern ([reference-library.md §3](../reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability)).

#### Plan-then-Execute (Epic 2 enhancement)

**Problem:** With multiple ACs, the AI dives into Phase 1 without considering the full picture. It might classify AC[0] as `api_behavior` and AC[3] as `security_invariant` but miss that they're related.
**Pattern:** Before Phase 1, the AI reads all ACs and proposes a negotiation plan — which ACs are related, which phases each needs, expected complexity. The developer confirms before execution.

```mermaid
sequenceDiagram
    participant AI as Planner Skill
    participant D as Developer
    participant H as Harness

    AI->>D: 5 ACs found - 3 API, 1 perf, 1 security. AC0 and AC4 related.
    D->>AI: AC3 is actually a data constraint, not perf SLA
    AI->>H: Revised plan configures state machine
    H->>H: Execute plan - phases 1-4 per AC group
```

**Implementation:** A new Agent Skill at `.claude/skills/negotiation-planner/SKILL.md`. The harness runs it as "Phase -1" before classification. The plan output configures which phases each AC flows through. Maps to Sherpa's "treat state machines as configurable data" principle ([reference-library.md §1](../reference-library.md#1-sherpa--model-driven-agent-orchestration-via-state-machines)).

#### Code-Grounded Negotiation / RAG (Epic 7 integration)

**Problem:** The AI proposes schemas and error codes based on convention, but the actual codebase may already implement things differently. The developer has to manually correct every mismatch.
**Pattern:** During phases 2-4, the LLM can call a `read_source(path, lines)` tool to inspect actual endpoint code, error handlers, and model definitions. Proposals are grounded in what's already implemented.

```mermaid
flowchart LR
    AC["AC text"] --> LLM["Phase 2 Skill"]
    CODE["Actual source code\n(endpoint, models, errors)"] --> LLM
    CONST["Constitution\n(conventions)"] --> LLM
    LLM --> POST["Postconditions\n(grounded in reality)"]
```

**Implementation:** Extend `LLMClient` with tool-use support. Add a `CodeSearchTool` that the LLM calls during negotiation. The constitution (Epic 7) provides file paths; the tool reads the actual code. Results are injected into the conversation as tool results, not the system prompt (respecting instruction budget). Maps to harness engineering's "tools & dispatch" pattern ([reference-library.md §3](../reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability)).

---

## 10. Design Influences

| Influence | What It Provides | Reference |
|-----------|-----------------|-----------|
| **Sherpa** | Hierarchical state machines, belief system, guard conditions | [reference-library.md §1](../reference-library.md#1-sherpa--model-driven-agent-orchestration-via-state-machines) |
| **Agent Skills** | Progressive disclosure, SKILL.md standard, Block's 3 Principles | [reference-library.md §2](../reference-library.md#2-agent-skills--modular-discoverable-capability-packages), [agent-skills-reference.md](../agent-skills-reference.md) |
| **Harness Engineering** | Context management, back-pressure, instruction budget | [reference-library.md §3](../reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability) |
| **BMAD** | Agent-as-code, documentation-first, versionable markdown agents | [reference-library.md §4](../reference-library.md#4-bmad--agent-as-code-agile-development-framework) |

---

## 10. Key Files

| Area | File | Purpose |
|------|------|---------|
| **Context** | `src/verify/context.py` | VerificationContext dataclass (Sherpa belief system) |
| **Negotiation** | `src/verify/negotiation/harness.py` | Phase state machine with guard conditions |
| | `src/verify/negotiation/phase1-4.py` | LLM-powered negotiation skills |
| | `src/verify/negotiation/validate.py` | Deterministic output validation |
| | `src/verify/negotiation/synthesis.py` | Post-negotiation: invariants, EARS, traceability |
| **Compiler** | `src/verify/compiler.py` | Context → YAML spec + routing table + traceability |
| **Pipeline** | `src/verify/generator.py` | Spec → pytest test file (to be replaced by verify-pytest skill) |
| | `src/verify/runner.py` | Run tests + parse JUnit XML |
| | `src/verify/evaluator.py` | Spec + results → verdicts |
| | `src/verify/pipeline.py` | End-to-end orchestrator |
| **Jira** | `src/verify/jira_client.py` | Read/write/search Jira Cloud REST API |
| **LLM** | `src/verify/llm_client.py` | Claude SDK + mock mode + multi-turn |
| **UI** | `static/index.html` | Web UI (Jira picker, negotiation, traceability) |
| **Spec Skills** | `.claude/skills/phase*-*/SKILL.md` | Negotiation phase skill definitions |
| **Verification Skills** | `.claude/skills/verify-*/SKILL.md` | Proof-of-correctness generator skills (Epic 4) |

---

## 11. Detailed Implementation Flow

Three connected flowcharts showing every step, interface, and data shape in the pipeline — color-coded by actor/system.

### Color Legend

| Color | Actor/System | Description |
|-------|-------------|-------------|
| **Blue** | Jira Cloud API | External ticket system — fetch stories, extract ACs, write back verdicts |
| **Teal** | Web UI | Frontend screens — story picker, AC overview, negotiation chat, traceability |
| **Purple** | AC→Spec (Negotiation) | LLM-powered phases 1-4 with constitutional prompts |
| **Indigo** | Spec→Test (Verification Skills) | Agent Skills that generate tests, configs, and scenarios |
| **Orange** | Orchestrator | Harness (state machine + guards), Pipeline, deterministic synthesis/compilation |
| **Dark Gray** | GitHub | PR creation, CI/CD workflows, Actions |
| **Green** | User | Human developer decisions — approve, feedback, review, fix |
| **Red** | Tests | Test runner, pytest execution, JUnit parsing |
| **Gold** | Artifacts | Files produced at each stage (.verify/specs, generated, results) |
| **Pink** | Evaluator | Maps test results to AC verdicts via traceability |

### Diagram A: Entry + AI Negotiation

```mermaid
flowchart TD
    classDef jira fill:#0984e3,color:#fff,stroke:#0984e3
    classDef ui fill:#00cec9,color:#000,stroke:#00cec9
    classDef acspec fill:#6c5ce7,color:#fff,stroke:#6c5ce7
    classDef orch fill:#e17055,color:#fff,stroke:#e17055
    classDef user fill:#00b894,color:#fff,stroke:#00b894
    classDef artifact fill:#fdcb6e,color:#000,stroke:#fdcb6e

    subgraph entry["JIRA INGESTION"]
        J1["Jira Cloud REST API v3"]:::jira
        J2["JiraClient.fetch_ticket(key)<br/>+ extract_acceptance_criteria()"]:::jira
        J3["JiraClient.get_in_progress_stories()<br/>JQL: status = In Progress"]:::jira
        J1 -->|"GET /rest/api/3/issue/{key}"| J2
        J1 -->|"GET /rest/api/3/search/jql"| J3
    end

    subgraph webui["WEB UI"]
        UI1["Story Picker<br/>GET /api/jira/stories"]:::ui
        U1["User selects story<br/>or enters manual ACs"]:::user
        UI2["AC Overview Screen<br/>display acceptance criteria"]:::ui
        UI3["Begin Negotiation<br/>button click"]:::user
    end

    J3 -->|"stories[]"| UI1
    UI1 --> U1
    U1 -->|"GET /api/jira/ticket/{key}"| J2
    J2 -->|"{key, summary, acceptance_criteria[]}"| UI2
    UI2 --> UI3

    subgraph init["ORCHESTRATOR INIT"]
        START["POST /api/start<br/>Create VerificationContext<br/>+ NegotiationHarness<br/>+ LLMClient"]:::orch
    end

    UI3 -->|"{jira_key, summary,<br/>acceptance_criteria[], constitution}"| START

    subgraph phase1["PHASE 1: INTERFACE & ACTOR DISCOVERY"]
        P1_LLM["run_phase1(ctx, llm)<br/>Constitutional system prompt<br/>+ raw ACs → Claude API"]:::acspec
        P1_VAL{"validate_classifications()<br/>type ∈ VALID_TYPES?<br/>actor ∈ VALID_ACTORS?<br/>all ACs covered?"}:::orch
        P1_CTX["ctx.classifications =<br/>{ac_index, type, actor, interface}"]:::artifact
        P1_UI["Present results +<br/>clarifying questions"]:::ui
        P1_DEC{"Developer<br/>decision"}:::user
        P1_FB["chat_multi() revision<br/>prev output + feedback<br/>→ revised classifications"]:::acspec
        P1_GUARD{"Guard: _phase_0_ok()<br/>every AC classified?"}:::orch

        P1_LLM --> P1_VAL
        P1_VAL -->|"invalid → retry up to 2x<br/>with errors appended"| P1_LLM
        P1_VAL -->|"valid"| P1_CTX
        P1_CTX --> P1_UI
        P1_UI --> P1_DEC
        P1_DEC -->|"feedback text"| P1_FB
        P1_FB --> P1_VAL
        P1_DEC -->|"approve"| P1_GUARD
    end

    START -->|"harness.phase = phase_0"| P1_LLM

    subgraph phase2["PHASE 2: HAPPY PATH CONTRACT"]
        P2_LLM["run_phase2(ctx, llm)<br/>api_behavior classifications<br/>+ constitution → Claude API"]:::acspec
        P2_VAL{"validate_postconditions()<br/>every api_behavior AC<br/>has postcondition?<br/>status is valid HTTP?"}:::orch
        P2_CTX["ctx.postconditions =<br/>{ac_index, status, schema,<br/>constraints, forbidden_fields}"]:::artifact
        P2_UI["Present postconditions +<br/>clarifying questions"]:::ui
        P2_DEC{"Developer<br/>decision"}:::user
        P2_FB["chat_multi() revision"]:::acspec
        P2_GUARD{"Guard: _phase_1_ok()<br/>api_behavior ACs<br/>⊆ postcond indices?"}:::orch

        P2_LLM --> P2_VAL
        P2_VAL -->|"invalid → retry"| P2_LLM
        P2_VAL -->|"valid"| P2_CTX
        P2_CTX --> P2_UI
        P2_UI --> P2_DEC
        P2_DEC -->|"feedback"| P2_FB
        P2_FB --> P2_VAL
        P2_DEC -->|"approve"| P2_GUARD
    end

    P1_GUARD -->|"advance_phase()"| P2_LLM

    subgraph phase3["PHASE 3: PRECONDITION FORMALIZATION"]
        P3_LLM["run_phase3(ctx, llm)<br/>postconditions + auth context<br/>Design by Contract → Claude API"]:::acspec
        P3_VAL{"validate_preconditions()<br/>IDs = PRE-NNN?<br/>category ∈ VALID?<br/>formal non-empty?"}:::orch
        P3_CTX["ctx.preconditions =<br/>{id: PRE-NNN, description,<br/>formal, category}"]:::artifact
        P3_UI["Present preconditions +<br/>clarifying questions"]:::ui
        P3_DEC{"Developer<br/>decision"}:::user
        P3_FB["chat_multi() revision"]:::acspec
        P3_GUARD{"Guard: _phase_2_ok()<br/>preconditions exist?"}:::orch

        P3_LLM --> P3_VAL
        P3_VAL -->|"invalid → retry"| P3_LLM
        P3_VAL -->|"valid"| P3_CTX
        P3_CTX --> P3_UI
        P3_UI --> P3_DEC
        P3_DEC -->|"feedback"| P3_FB
        P3_FB --> P3_VAL
        P3_DEC -->|"approve"| P3_GUARD
    end

    P2_GUARD -->|"advance_phase()"| P3_LLM

    subgraph phase4["PHASE 4: FAILURE MODE ENUMERATION"]
        P4_LLM["run_phase4(ctx, llm)<br/>preconditions + error format<br/>FMEA-inspired → Claude API"]:::acspec
        P4_VAL{"validate_failure_modes()<br/>IDs = FAIL-NNN?<br/>violates ∈ precond IDs?<br/>every PRE has ≥1 FAIL?"}:::orch
        P4_CTX["ctx.failure_modes =<br/>{id: FAIL-NNN, violates: PRE-NNN,<br/>description, status, body}"]:::artifact
        P4_UI["Present failure modes +<br/>security questions"]:::ui
        P4_DEC{"Developer<br/>decision"}:::user
        P4_FB["chat_multi() revision"]:::acspec
        P4_GUARD{"Guard: _phase_3_ok()<br/>all failure modes<br/>ref valid preconditions?"}:::orch

        P4_LLM --> P4_VAL
        P4_VAL -->|"invalid → retry"| P4_LLM
        P4_VAL -->|"valid"| P4_CTX
        P4_CTX --> P4_UI
        P4_UI --> P4_DEC
        P4_DEC -->|"feedback"| P4_FB
        P4_FB --> P4_VAL
        P4_DEC -->|"approve"| P4_GUARD
    end

    P3_GUARD -->|"advance_phase()"| P4_LLM
    P4_GUARD -->|"run_synthesis(ctx)"| CONN_A["▼ Continue to Diagram B:<br/>Synthesis & Compilation"]:::orch
```

### Diagram B: Synthesis + Spec Compilation + Skill Dispatch + PR

```mermaid
flowchart TD
    classDef jira fill:#0984e3,color:#fff,stroke:#0984e3
    classDef ui fill:#00cec9,color:#000,stroke:#00cec9
    classDef acspec fill:#6c5ce7,color:#fff,stroke:#6c5ce7
    classDef spectest fill:#4834d4,color:#fff,stroke:#4834d4
    classDef orch fill:#e17055,color:#fff,stroke:#e17055
    classDef gh fill:#636e72,color:#fff,stroke:#636e72
    classDef user fill:#00b894,color:#fff,stroke:#00b894
    classDef artifact fill:#fdcb6e,color:#000,stroke:#fdcb6e

    CONN_IN["▲ From Diagram A:<br/>Phase 4 approved"]:::orch

    subgraph synthesis["DETERMINISTIC SYNTHESIS (Zero AI)"]
        SYN1["extract_invariants()<br/>constitution.security_invariants<br/>+ postcondition.forbidden_fields"]:::orch
        SYN2["generate_ears_statements()<br/>WHEN/IF/WHILE patterns<br/>from all contract elements"]:::orch
        SYN3["build_traceability_map()<br/>AC checkbox → required<br/>verification refs"]:::orch

        SYN1_OUT["ctx.invariants =<br/>{id: INV-NNN, description, category}"]:::artifact
        SYN2_OUT["ctx.ears_statements =<br/>WHEN event THEN system SHALL action<br/>IF condition THEN response<br/>WHILE state system SHALL property"]:::artifact
        SYN3_OUT["ctx.traceability_map =<br/>{ac_mappings: [{ac_checkbox,<br/>pass_condition,<br/>required_verifications[]}]}"]:::artifact

        SYN1 --> SYN1_OUT
        SYN1_OUT --> SYN2
        SYN2 --> SYN2_OUT
        SYN2_OUT --> SYN3
        SYN3 --> SYN3_OUT
    end

    CONN_IN -->|"run_synthesis(ctx)"| SYN1

    subgraph compile["SPEC COMPILATION (Deterministic)"]
        CC1["compile_spec(context)<br/>_build_meta()<br/>_build_requirements()<br/>_build_traceability()"]:::orch
        CC2["ROUTING_TABLE lookup<br/>requirement type → skill"]:::orch
        CC3["write_spec(spec, output_dir)<br/>YAML serialization"]:::orch
        CC4[".verify/specs/{KEY}.yaml<br/>meta + requirements<br/>+ verification routing<br/>+ traceability"]:::artifact
    end

    SYN3_OUT -->|"compile_and_write(ctx)"| CC1
    CC1 -->|"for each requirement:<br/>route = ROUTING_TABLE[type]"| CC2
    CC2 --> CC3
    CC3 --> CC4

    subgraph routing["ROUTING TABLE (Zero AI)"]
        R1["api_behavior → pytest_unit_test"]:::orch
        R2["performance_sla → newrelic_alert_config"]:::orch
        R3["security_invariant → pytest_unit_test"]:::orch
        R4["observability → otel_config"]:::orch
        R5["compliance → gherkin_scenario"]:::orch
        R6["data_constraint → pytest_unit_test"]:::orch
    end

    CC2 -.->|"deterministic mapping"| routing

    subgraph dispatch["VERIFICATION SKILL DISPATCH"]
        SR["Skill Router<br/>reads spec.verification[].skill"]:::orch

        SK1["verify-pytest<br/>SKILL.md + TEMPLATES.md<br/>Agent Skill"]:::spectest
        SK2["verify-newrelic<br/>SKILL.md<br/>Agent Skill"]:::spectest
        SK3["verify-otel<br/>SKILL.md<br/>Agent Skill"]:::spectest
        SK4["verify-gherkin<br/>SKILL.md<br/>Agent Skill"]:::spectest

        ART1[".verify/generated/test_{key}.py<br/>tagged [REQ-NNN.success]<br/>tagged [REQ-NNN.FAIL-NNN]<br/>tagged [REQ-NNN.INV-NNN]"]:::artifact
        ART2[".verify/generated/<br/>{key}_alerts.json"]:::artifact
        ART3[".verify/generated/<br/>{key}_otel.yaml"]:::artifact
        ART4[".verify/generated/<br/>{key}.feature"]:::artifact

        SR -->|"api_behavior /<br/>security / data"| SK1
        SR -->|"performance_sla"| SK2
        SR -->|"observability"| SK3
        SR -->|"compliance"| SK4

        SK1 --> ART1
        SK2 --> ART2
        SK3 --> ART3
        SK4 --> ART4
    end

    CC4 -->|"spec YAML path"| SR

    subgraph github["GITHUB PR CREATION"]
        GH1["Create branch<br/>verify/{jira_key}"]:::gh
        GH2["Commit spec YAML +<br/>all generated artifacts"]:::gh
        GH3["gh pr create<br/>EARS statements +<br/>traceability table in body"]:::gh
        GH4["Developer reviews PR"]:::user
    end

    ART1 & ART2 & ART3 & ART4 -->|"generated artifacts"| GH1
    CC4 -->|"spec file"| GH2
    GH1 --> GH2 --> GH3 --> GH4
    GH4 -->|"PR triggers CI"| CONN_B["▼ Continue to Diagram C:<br/>CI + Evaluation"]:::gh
```

### Diagram C: CI Execution + Evaluation + Feedback Loop

```mermaid
flowchart TD
    classDef jira fill:#0984e3,color:#fff,stroke:#0984e3
    classDef orch fill:#e17055,color:#fff,stroke:#e17055
    classDef gh fill:#636e72,color:#fff,stroke:#636e72
    classDef user fill:#00b894,color:#fff,stroke:#00b894
    classDef tests fill:#d63031,color:#fff,stroke:#d63031
    classDef artifact fill:#fdcb6e,color:#000,stroke:#fdcb6e
    classDef eval fill:#e84393,color:#fff,stroke:#e84393

    CONN_IN["▲ From Diagram B:<br/>PR triggers CI"]:::gh

    subgraph ci["GITHUB ACTIONS CI"]
        CI1[".github/workflows/verify.yml<br/>on: pull_request<br/>paths: .verify/**"]:::gh
        CI2["Pipeline Orchestrator<br/>python -m verify.pipeline<br/>.verify/specs/{KEY}.yaml"]:::orch
    end

    CONN_IN --> CI1
    CI1 -->|"run pipeline"| CI2

    subgraph testexec["TEST EXECUTION"]
        TR1["run_tests(test_path, results_dir)<br/>pytest --junitxml -v"]:::tests
        TR_TARGET["Execute against<br/>target application<br/>(dummy_app / real service)"]:::tests
        TR2[".verify/results/results.xml<br/>JUnit XML output"]:::artifact
        TR3["parse_junit_xml(xml_path)<br/>extract [REQ-NNN.*] tags<br/>from test names/docstrings"]:::tests
        TR4[".verify/results/<br/>parsed_results.json<br/>{test_cases: [{name, tags,<br/>status, failure_message}]}"]:::artifact

        TR1 --> TR_TARGET
        TR_TARGET --> TR2
        TR2 --> TR3
        TR3 --> TR4
    end

    CI2 -->|"generate_and_write(spec)"| TR1

    subgraph evaluation["EVALUATION"]
        EV1["evaluate_spec(spec_path, results)<br/>read spec.traceability.ac_mappings"]:::eval
        EV2["For each AC mapping:<br/>match verification refs<br/>to test case tags"]:::eval
        EV3{"evaluate_pass_condition()<br/>ALL_PASS: all refs pass<br/>ANY_PASS: ≥1 ref passes<br/>PERCENTAGE: ≥N% pass"}:::eval
        EV4["verdicts[] =<br/>{ac_checkbox, ac_text, passed,<br/>pass_condition, summary,<br/>evidence[{ref, passed, details}]}"]:::artifact

        EV1 --> EV2
        EV2 --> EV3
        EV3 --> EV4
    end

    TR4 -->|"test results"| EV1

    DEC{"All ACs<br/>passed?"}:::eval
    EV4 --> DEC

    subgraph pass_path["ALL PASS"]
        JT1["JiraClient.tick_checkbox()<br/>for each passed AC index"]:::jira
        JT2["JiraClient.post_comment()<br/>format_evidence_comment(verdicts)"]:::jira
        JT3["JiraClient.transition_ticket()<br/>→ Done"]:::jira
        GHP1["Post verdict summary<br/>as PR comment"]:::gh
        GHP2["Merge PR"]:::gh
        DONE["Jira Ticket Verified<br/>✓ AC checkboxes ticked<br/>✓ Evidence comment posted<br/>✓ Status: Done<br/>✓ PR merged"]:::jira
    end

    DEC -->|"yes"| JT1
    JT1 --> JT2 --> JT3 --> DONE
    DEC -->|"yes"| GHP1
    GHP1 --> GHP2 --> DONE

    subgraph fail_path["FAILURES DETECTED"]
        JF1["JiraClient.tick_checkbox()<br/>only for passed ACs"]:::jira
        JF2["JiraClient.post_comment()<br/>failure evidence + which ACs violated"]:::jira
        GHF1["Post failure summary<br/>as PR comment<br/>which REQ-NNN refs failed"]:::gh
        GHF2{"Developer<br/>decides"}:::user
        FIX["Fix code<br/>push to PR branch"]:::user
        RENEG["Re-enter negotiation<br/>spec needs revision<br/>→ Diagram A"]:::orch
    end

    DEC -->|"no"| JF1
    JF1 --> JF2
    DEC -->|"no"| GHF1
    GHF1 --> GHF2
    GHF2 -->|"code fix needed"| FIX
    GHF2 -->|"spec drift /<br/>requirements changed"| RENEG
    FIX -->|"re-triggers CI"| CI1
```

---

## 12. Production Vision: AC-to-Spec Detailed Flow

Four connected flowcharts showing the full production negotiation protocol from [`specify-production-spec.md`](../specify-production-spec.md) — all 9 phases, the harness inner loop, codebase intelligence, multi-agent generation, and spec formation. Reuses the [color legend from Section 11](#color-legend).

### Diagram D: Ingestion + Codebase Intelligence (Phases 0-0.5)

```mermaid
flowchart TD
    classDef jira fill:#0984e3,color:#fff,stroke:#0984e3
    classDef ui fill:#00cec9,color:#000,stroke:#00cec9
    classDef acspec fill:#6c5ce7,color:#fff,stroke:#6c5ce7
    classDef orch fill:#e17055,color:#fff,stroke:#e17055
    classDef user fill:#00b894,color:#fff,stroke:#00b894
    classDef artifact fill:#fdcb6e,color:#000,stroke:#fdcb6e

    DEV["Developer opens SPECify UI<br/>enters Jira ticket key"]:::user

    subgraph phase0["PHASE 0: AC INGESTION (Deterministic, No AI)"]
        J1["Jira REST API v3<br/>GET /rest/api/3/issue/KEY<br/>fields=description,summary,status"]:::jira
        J2["Parse Atlassian Document Format<br/>Walk ADF content tree<br/>Find taskList + taskItem nodes"]:::orch
        J3["Extract AC checkboxes<br/>index, text, checked, adf_local_id"]:::orch
        AC_OUT["VerificationContext.raw_ac =<br/>index, text, checked, adf_local_id"]:::artifact

        J1 -->|"ADF document"| J2
        J2 -->|"taskItem nodes"| J3
        J3 --> AC_OUT
    end

    DEV -->|"jira_key"| J1

    subgraph phase05["PHASE 0.5: CODEBASE PRE-SCAN (Deterministic, No AI)"]
        DETECT["Detect language + framework<br/>from project files"]:::orch
        SCAN_SEL{"Select scanner"}:::orch

        JAVA["JavaSpringScanner<br/>@GetMapping, @Entity,<br/>@ControllerAdvice,<br/>SecurityFilterChain"]:::orch
        NODE["NodeExpressScanner<br/>router.get, mongoose.Schema,<br/>errorMiddleware,<br/>passport.authenticate"]:::orch
        PY["PythonFastAPIScanner<br/>@app.get, SQLAlchemy Base,<br/>@app.exception_handler,<br/>Depends get_current_user"]:::orch

        EP["endpoints<br/>method + path + file + auth"]:::artifact
        ENT["entities<br/>class + fields + sensitive flags"]:::artifact
        DTO["dtos<br/>response/request objects"]:::artifact
        ERR["error_handlers<br/>exception to status code map"]:::artifact
        SEC["security_config<br/>auth mechanism + protected paths"]:::artifact
        TST["existing_tests<br/>test files + count + coverage"]:::artifact
        INF["infra_configs<br/>NR, OTel, Docker, K8s, CI"]:::artifact

        IDX["CodebaseIndex<br/>structural index, no file contents<br/>saved to .verify/logs/KEY-codebase-index.yaml"]:::artifact

        DETECT --> SCAN_SEL
        SCAN_SEL -->|"Java/Spring"| JAVA
        SCAN_SEL -->|"Node/Express"| NODE
        SCAN_SEL -->|"Python/FastAPI"| PY
        JAVA & NODE & PY --> EP & ENT & DTO & ERR & SEC & TST & INF
        EP & ENT & DTO & ERR & SEC & TST & INF --> IDX
    end

    AC_OUT -->|"raw_ac loaded"| DETECT

    subgraph deep_reads["DEEP READS (AI-Requested, Constrained)"]
        DR_RULES["Constraints:<br/>Max 10 files per session<br/>Allowed extensions only<br/>Max 100 lines per file<br/>No .env / secrets / .git<br/>Cached: re-reads free"]:::orch
        DR_FLOW["Pass 1: AI sees index summary<br/>may request specific files<br/>Pass 2: AI gets file contents<br/>produces refined output"]:::acspec
    end

    IDX -->|"Available during<br/>Phases 1-7"| DR_FLOW
    DR_RULES -.->|"enforced by<br/>BackPressure"| DR_FLOW

    IDX --> CONN_D["Continue to Diagram E:<br/>AI Negotiation Protocol"]:::orch
```

### Diagram E: AI Negotiation Protocol (Phases 1-5)

```mermaid
flowchart TD
    classDef jira fill:#0984e3,color:#fff,stroke:#0984e3
    classDef ui fill:#00cec9,color:#000,stroke:#00cec9
    classDef acspec fill:#6c5ce7,color:#fff,stroke:#6c5ce7
    classDef orch fill:#e17055,color:#fff,stroke:#e17055
    classDef user fill:#00b894,color:#fff,stroke:#00b894
    classDef artifact fill:#fdcb6e,color:#000,stroke:#fdcb6e

    CONN_IN["From Diagram D:<br/>raw_ac + CodebaseIndex ready"]:::orch

    subgraph bp["HARNESS INFRASTRUCTURE (applies to every phase)"]
        BP1["BackPressure Controller<br/>MAX_API_CALLS=50<br/>MAX_TOKENS=500K<br/>MAX_RUNTIME=600s<br/>MAX_RETRIES=3/phase<br/>MAX_DEEP_READS=10"]:::orch
        OBS["HarnessObserver<br/>Structured JSONL logging<br/>phase_started, llm_called,<br/>validation_result,<br/>developer_interaction,<br/>checkpoint_saved"]:::orch
        DET["DeterministicBoundary<br/>AI allowed = True<br/>enforced: no AI below spec"]:::orch
    end

    subgraph harness_loop["HARNESS INNER LOOP (repeated per phase)"]
        direction TB
        H1["1. Entry Condition<br/>Guard: prerequisites met?"]:::orch
        H2["2. Context Curation<br/>ContextCurator builds<br/>phase-specific view"]:::orch
        H3["3. Execute<br/>Raw Anthropic API call<br/>system prompt + curated context"]:::acspec
        H4["4. Validate<br/>OutputValidator checks<br/>structural validity"]:::orch
        H5{"5. Valid?"}:::orch
        H5R["Retry: append errors<br/>up to max_retries"]:::acspec
        H6["6. Human Gate<br/>Developer reviews<br/>approves or corrects"]:::user
        H6R["Multi-turn revision<br/>messages = prompt + output<br/>+ corrections"]:::acspec
        H7["7. Checkpoint<br/>Save to .verify/checkpoints/"]:::orch
        H8["8. Advance<br/>harness decision, not AI"]:::orch

        H1 --> H2 --> H3 --> H4 --> H5
        H5 -->|"invalid"| H5R --> H3
        H5 -->|"valid"| H6
        H6 -->|"corrections"| H6R --> H4
        H6 -->|"approve"| H7 --> H8
    end

    CONN_IN --> P1

    subgraph phase1["PHASE 1: INTERFACE + ACTOR DISCOVERY"]
        P1["Entry: raw_ac + codebase_index"]:::orch
        P1C["ContextCurator:<br/>raw_ac + endpoints<br/>+ project config<br/>+ api_base_path"]:::orch
        P1A["AI classifies each AC:<br/>type, actor, interface<br/>+ codebase evidence"]:::acspec
        P1O["classifications =<br/>ac_index, type, actor,<br/>interface, evidence"]:::artifact
        P1D["Dimensions:<br/>Actors, Boundaries partial"]:::acspec

        P1 --> P1C --> P1A --> P1O
        P1D -.-> P1A
    end

    subgraph phase2["PHASE 2: HAPPY PATH CONTRACT"]
        P2["Entry: classifications confirmed"]:::orch
        P2C["ContextCurator:<br/>api_requirements<br/>+ relevant_entity + relevant_dto<br/>+ sensitive_fields + auth_config<br/>+ security_invariants"]:::orch
        P2A["AI proposes success response<br/>informed by actual entity<br/>fields and existing DTOs"]:::acspec
        P2O["postconditions =<br/>status, schema, constraints,<br/>forbidden_fields, source_dto"]:::artifact
        P2D["Dimensions:<br/>Boundaries full"]:::acspec

        P2 --> P2C --> P2A --> P2O
        P2D -.-> P2A
    end

    subgraph phase3["PHASE 3: PRECONDITION FORMALIZATION"]
        P3["Entry: postconditions confirmed"]:::orch
        P3C["ContextCurator:<br/>success_contracts<br/>+ security_config<br/>+ auth_mechanism<br/>+ entity_constraints"]:::orch
        P3A["Design by Contract +<br/>codebase security analysis"]:::acspec
        P3O["preconditions =<br/>PRE-NNN, formal, category,<br/>codebase_evidence"]:::artifact
        P3D["Dimensions:<br/>Preconditions"]:::acspec

        P3 --> P3C --> P3A --> P3O
        P3D -.-> P3A
    end

    subgraph phase4["PHASE 4: FAILURE MODE ENUMERATION"]
        P4["Entry: preconditions confirmed"]:::orch
        P4C["ContextCurator:<br/>preconditions + error_handlers<br/>+ error_format<br/>+ common_status_codes"]:::orch
        P4A["FMEA + error handler analysis<br/>+ security analysis:<br/>status code info leakage"]:::acspec
        P4O["failure_modes =<br/>FAIL-NNN, violates PRE-NNN,<br/>status, body +<br/>security_questions"]:::artifact
        P4D["Dimensions:<br/>Failure Modes"]:::acspec

        P4 --> P4C --> P4A --> P4O
        P4D -.-> P4A
    end

    subgraph phase5["PHASE 5: INVARIANT EXTRACTION"]
        P5["Entry: failure_modes confirmed"]:::orch
        P5C["ContextCurator:<br/>response_fields +<br/>existing_test_coverage<br/>+ infra_configs<br/>+ sensitive_fields<br/>+ security_invariants<br/>+ observability_config"]:::orch
        P5A["Three sources:<br/>1. AC text explicit invariants<br/>2. Constitution standards<br/>3. Data model inference"]:::acspec
        P5O["invariants =<br/>INV-NNN, type, rule,<br/>source, verification_type"]:::artifact
        P5D["Dimensions: Invariants,<br/>Non-Functional Constraints"]:::acspec

        P5 --> P5C --> P5A --> P5O
        P5D -.-> P5A
    end

    P1O -->|"advance_phase"| P2
    P2O -->|"advance_phase"| P3
    P3O -->|"advance_phase"| P4
    P4O -->|"advance_phase"| P5

    CB["CodebaseIndex<br/>from Phase 0.5"]:::artifact
    CB -.->|"endpoints"| P1C
    CB -.->|"entities + DTOs<br/>+ sensitive fields"| P2C
    CB -.->|"security_config"| P3C
    CB -.->|"error_handlers"| P4C
    CB -.->|"tests + infra"| P5C

    P5O --> CONN_E["Continue to Diagram F:<br/>Completeness + Formalization"]:::orch
```

### Diagram F: Completeness + Formalization + Spec Compilation (Phases 6-7)

```mermaid
flowchart TD
    classDef jira fill:#0984e3,color:#fff,stroke:#0984e3
    classDef ui fill:#00cec9,color:#000,stroke:#00cec9
    classDef acspec fill:#6c5ce7,color:#fff,stroke:#6c5ce7
    classDef orch fill:#e17055,color:#fff,stroke:#e17055
    classDef user fill:#00b894,color:#fff,stroke:#00b894
    classDef artifact fill:#fdcb6e,color:#000,stroke:#fdcb6e

    CONN_IN["From Diagram E:<br/>Phases 1-5 outputs confirmed"]:::orch

    subgraph phase6["PHASE 6: COMPLETENESS SWEEP + VERIFICATION ROUTING (AI)"]
        P6S["Entry: invariants confirmed<br/>+ all prior phases complete"]:::orch
        P6A["15-dimension checklist scan<br/>For each: COVERED /<br/>DEFERRED / NOT_ADDRESSED"]:::acspec

        CK["auth, authz, input validation,<br/>output schema, errors,<br/>rate limiting, pagination,<br/>caching, versioning, idempotency,<br/>observability, security,<br/>data classification,<br/>deprecation, documentation"]:::orch

        P6R["Assign verification type + skill<br/>per requirement"]:::orch
        P6O["completeness_checklist +<br/>verification_routing =<br/>refs, skill, pattern, output, framework"]:::artifact

        P6S --> P6A --> CK --> P6R --> P6O
    end

    CONN_IN --> P6S

    subgraph phase7["PHASE 7: EARS FORMALIZATION + HUMAN APPROVAL (AI)"]
        P7S["Entry: all prior phases confirmed<br/>+ completeness sweep done"]:::orch
        P7A["Synthesize all outputs<br/>into EARS statements"]:::acspec

        EP1["UBIQUITOUS<br/>The system SHALL..."]:::acspec
        EP2["EVENT_DRIVEN<br/>WHEN trigger, system SHALL..."]:::acspec
        EP3["STATE_DRIVEN<br/>WHILE state, system SHALL..."]:::acspec
        EP4["UNWANTED<br/>IF condition, THEN system SHALL..."]:::acspec
        EP5["OPTIONAL<br/>WHERE feature, system SHALL..."]:::acspec

        P7SUM["EARS Summary<br/>every verifiable assertion<br/>as one human-readable sentence"]:::ui
        P7REV{"Developer reviews<br/>full EARS summary"}:::user
        P7COR["Developer provides<br/>corrections"]:::user
        P7APP["Developer approves"]:::user
        P7O["ears_statements +<br/>approved = True"]:::artifact

        P7S --> P7A
        P7A --> EP1 & EP2 & EP3 & EP4 & EP5
        EP1 & EP2 & EP3 & EP4 & EP5 --> P7SUM
        P7SUM --> P7REV
        P7REV -->|"corrections"| P7COR
        P7COR -->|"multi-turn revision"| P7A
        P7REV -->|"approve"| P7APP --> P7O
    end

    P6O -->|"advance_phase"| P7S

    subgraph compile["SPEC COMPILATION (Deterministic, Zero AI)"]
        CC_CROSS["Cross-reference validation<br/>Every FAIL refs valid PRE<br/>Every AC index has mapping<br/>Every classification refs valid AC"]:::orch
        CC_BUILD["compile_spec context<br/>build_meta + build_requirements<br/>+ build_traceability"]:::orch

        S_META["meta:<br/>jira_key, approval_info,<br/>constitution_ref,<br/>codebase_index_ref,<br/>status: approved"]:::artifact
        S_CTX["context:<br/>relevant_source_files,<br/>relevant_test_files,<br/>related_specs"]:::artifact
        S_REQ["requirements:<br/>id, ac_checkbox, title, type<br/>+ ears pattern + when/shall<br/>+ contract: interface,<br/>preconditions, success,<br/>failures, invariants<br/>+ verification: refs, skill,<br/>pattern, output, framework"]:::artifact
        S_TRACE["traceability:<br/>ac_mappings: ac_checkbox,<br/>adf_local_id, pass_condition,<br/>threshold, required_verifications<br/>ref, description,<br/>verification_type, confidence"]:::artifact

        CC_WRITE["write_spec<br/>.verify/specs/KEY.yaml<br/>+ fingerprint to<br/>.verify/fingerprints/"]:::orch

        CC_CROSS --> CC_BUILD
        CC_BUILD --> S_META & S_CTX & S_REQ & S_TRACE
        S_META & S_CTX & S_REQ & S_TRACE --> CC_WRITE
    end

    P7O -->|"triggers spec compilation"| CC_CROSS

    DET["DETERMINISTIC BOUNDARY<br/>AI allowed = False from here<br/>No more LLM calls in pipeline"]:::orch

    CC_WRITE --> DET
    DET --> CONN_F["Continue to Diagram G:<br/>Multi-Agent Generation"]:::orch
```

### Diagram G: Multi-Agent Generation (Post-Approval)

```mermaid
flowchart TD
    classDef jira fill:#0984e3,color:#fff,stroke:#0984e3
    classDef spectest fill:#4834d4,color:#fff,stroke:#4834d4
    classDef orch fill:#e17055,color:#fff,stroke:#e17055
    classDef user fill:#00b894,color:#fff,stroke:#00b894
    classDef tests fill:#d63031,color:#fff,stroke:#d63031
    classDef artifact fill:#fdcb6e,color:#000,stroke:#fdcb6e
    classDef eval fill:#e84393,color:#fff,stroke:#e84393

    CONN_IN["From Diagram F:<br/>Spec YAML approved + saved"]:::orch

    subgraph gen["GENERATION ZONE (Claude Agent SDK)"]
        ORCH["Orchestrator Agent<br/>Reads spec.verification.skill<br/>for each requirement<br/>Determines subagents to spawn"]:::spectest

        RT1["api_behavior to junit"]:::orch
        RT2["performance_sla to nrql"]:::orch
        RT3["security_invariant to junit"]:::orch
        RT4["observability to otel"]:::orch
        RT5["compliance to gherkin"]:::orch
        RT6["data_constraint to junit"]:::orch

        ORCH --> RT1 & RT2 & RT3 & RT4 & RT5 & RT6

        SA1["junit-generator<br/>Model: Sonnet<br/>SKILL.md loaded on-demand<br/>Tools: Read, Write, Bash, Skill"]:::spectest
        SA2["nrql-generator<br/>Model: Haiku<br/>SKILL.md loaded on-demand<br/>Tools: Read, Write, Skill"]:::spectest
        SA3["gherkin-generator<br/>Model: Haiku<br/>SKILL.md loaded on-demand<br/>Tools: Read, Write, Skill"]:::spectest
        SA4["otel-generator<br/>Model: Haiku<br/>SKILL.md loaded on-demand<br/>Tools: Read, Write, Skill"]:::spectest

        RT1 & RT3 & RT6 -->|"spawn parallel"| SA1
        RT2 -->|"spawn"| SA2
        RT5 -->|"spawn"| SA3
        RT4 -->|"spawn"| SA4

        PRE["pre_tool_hook:<br/>Block dangerous bash<br/>Block sensitive reads<br/>Write only to allowed dirs<br/>Enforce back-pressure"]:::orch
        POST["post_tool_hook:<br/>Log every tool call<br/>Track token usage<br/>Update harness state"]:::orch

        PRE & POST -.->|"intercept every<br/>tool call"| SA1 & SA2 & SA3 & SA4

        SK1["generate-junit/SKILL.md<br/>Tag contract + mapping rules<br/>+ references/tag-contract.md"]:::spectest
        SK2["generate-nrql/SKILL.md<br/>NRQL schema + alert format<br/>+ references/nrql-schema.json"]:::spectest
        SK3["generate-gherkin/SKILL.md<br/>Given/When/Then patterns<br/>+ @TAG annotations"]:::spectest
        SK4["generate-otel/SKILL.md<br/>OTel config schema<br/>+ instrumentation rules"]:::spectest

        SA1 -.->|"loads on demand"| SK1
        SA2 -.->|"loads on demand"| SK2
        SA3 -.->|"loads on demand"| SK3
        SA4 -.->|"loads on demand"| SK4

        A1[".verify/generated/test_KEY.py<br/>@Tag per spec ref<br/>@DisplayName per element"]:::artifact
        A2[".verify/generated/KEY_alerts.json<br/>NRQL alert configs"]:::artifact
        A3[".verify/generated/KEY.feature<br/>@TAG Gherkin scenarios"]:::artifact
        A4[".verify/generated/KEY_otel.yaml<br/>OTel instrumentation"]:::artifact

        SA1 --> A1
        SA2 --> A2
        SA3 --> A3
        SA4 --> A4
    end

    CONN_IN --> ORCH

    subgraph tag_enforce["TAG ENFORCEMENT (Deterministic)"]
        TE1["tag_enforcer.py<br/>For every spec ref:<br/>find matching @Tag in artifacts"]:::orch
        TE_CHK{"Coverage<br/>gaps?"}:::orch
        TE_RERUN["Re-run missing subagent<br/>for uncovered refs"]:::spectest
        TE_PASS["All spec refs covered<br/>by tagged artifacts"]:::orch

        TE1 --> TE_CHK
        TE_CHK -->|"gaps found"| TE_RERUN
        TE_RERUN -->|"re-validate"| TE1
        TE_CHK -->|"100% coverage"| TE_PASS
    end

    A1 & A2 & A3 & A4 --> TE1

    subgraph det_pipe["DETERMINISTIC PIPELINE (Zero AI)"]
        RUN["Test Runner<br/>subprocess: gradle test /<br/>npm test / pytest --junitxml"]:::tests
        PARSE["Result Parsers<br/>JUnit XML / Jest JSON /<br/>Cucumber JSON to unified format"]:::tests
        EVAL_ENG["Evaluator<br/>traceability map to verdicts<br/>ALL_PASS / ANY_PASS / PERCENTAGE"]:::eval
        VERD["Verdicts per AC checkbox<br/>ac_checkbox, passed, summary,<br/>evidence: ref, passed, details"]:::artifact
    end

    TE_PASS --> RUN --> PARSE --> EVAL_ENG --> VERD

    subgraph jira_up["JIRA FEEDBACK (Deterministic)"]
        JU1["Tick checkboxes<br/>ADF taskItem state: DONE<br/>matched by adf_local_id"]:::jira
        JU2["Post evidence comment<br/>per-AC breakdown + per-ref<br/>evidence + spec path"]:::jira
        JU3{"All ACs<br/>passed?"}:::jira
        JU4["Transition to Done"]:::jira
        JU5["Transition to In Review<br/>or unchanged"]:::jira
    end

    VERD --> JU1 --> JU2 --> JU3
    JU3 -->|"yes"| JU4
    JU3 -->|"no"| JU5

    JU4 --> DONE["Pipeline Complete<br/>Jira ticket verified"]:::jira
    JU5 --> PARTIAL["Partial pass<br/>Developer fixes code<br/>or re-enters negotiation"]:::user
```
