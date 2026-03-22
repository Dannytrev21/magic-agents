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

The `NegotiationHarness` drives the `VerificationContext` through phases with guard conditions on each transition.

```mermaid
stateDiagram-v2
    [*] --> Phase0
    Phase0 --> Phase1: all ACs classified
    Phase1 --> Phase2: all api_behaviors\nhave postconditions
    Phase2 --> Phase3: preconditions populated
    Phase3 --> Phase4: failure modes reference\nvalid preconditions
    Phase4 --> Synthesis: all failure modes valid
    Synthesis --> Compile: invariants + EARS +\ntraceability built
    Compile --> [*]: .verify/specs/{key}.yaml

    state Phase0 {
        [*] --> Classify
        Classify --> Validate: LLM output
        Validate --> Retry: validation errors
        Retry --> Classify: append errors to prompt
        Validate --> [*]: valid
    }

    Phase0: Phase 0 — Interface & Actor Discovery
    Phase1: Phase 1 — Happy Path Contract
    Phase2: Phase 2 — Precondition Formalization
    Phase3: Phase 3 — Failure Mode Enumeration
    Phase4: Phase 4 — Developer Feedback Loop
    Synthesis: Synthesis (zero AI)
    Compile: Spec Compilation (zero AI)
```

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

| Epic | Name | Features | Status | Playbook |
|------|------|----------|--------|----------|
| 0 | Bullet Tracer | 6 | Foundation | [docs/epic-0-bullet-tracer/](epic-0-bullet-tracer/PLAYBOOK.md) |
| 1 | Jira Integration | 4 | Foundation | [docs/epic-1-jira-integration/](epic-1-jira-integration/PLAYBOOK.md) |
| 2 | AI Negotiation | 7 | Complete | [docs/epic-2-ai-negotiation/](epic-2-ai-negotiation/PLAYBOOK.md) |
| 3 | Formal Spec Emission | 3 | Complete | [docs/epic-3-formal-spec/](epic-3-formal-spec/PLAYBOOK.md) |
| 4 | Skill Routing | 3 | MVP Next | [docs/epic-4-skill-routing/](epic-4-skill-routing/PLAYBOOK.md) |
| 5 | Evaluation Engine | 3 | MVP Next | [docs/epic-5-evaluation/](epic-5-evaluation/PLAYBOOK.md) |
| 6 | Jira Feedback | 3 | MVP Next | [docs/epic-6-jira-feedback/](epic-6-jira-feedback/PLAYBOOK.md) |
| 7 | Constitution | 3 | Stretch | [docs/epic-7-constitution/](epic-7-constitution/PLAYBOOK.md) |
| 8 | Advanced Negotiation | 3 | Stretch | [docs/epic-8-advanced-negotiation/](epic-8-advanced-negotiation/PLAYBOOK.md) |
| 9 | Beyond-Code Skills | 3 | Stretch | [docs/epic-9-verification-skills/](epic-9-verification-skills/PLAYBOOK.md) |
| 10 | CI/CD | 3 | Stretch | [docs/epic-10-cicd/](epic-10-cicd/PLAYBOOK.md) |

---

## 9. Design Influences

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
