# Bullet Tracer — Initial Design

> One hardcoded Jira story, one AC, zero human negotiation.
> Straight-line pipeline: Jira -> Spec -> Java Tests -> Jira checkbox ticked.

---

## 1. End-to-End Logic Flow

The happy-path execution from start to finish. No branching, no human-in-the-loop.

```mermaid
flowchart TD
    A[Start: Python Orchestrator] --> B[Load Hardcoded Jira Story]
    B --> C[Build Context String]
    C --> D[Display Story + AC in Web UI]
    D --> E[Call Claude API: Negotiation]
    E --> F{Valid Spec JSON?}
    F -- No --> G[Retry with Validation Errors]
    G --> E
    F -- Yes --> H[Compile to YAML Spec]
    H --> I[Display Spec in Web UI]
    I --> J[Call Claude API: Generate Java Tests]
    J --> K{Valid Java Source?}
    K -- No --> L[Retry with Compilation Errors]
    L --> J
    K -- Yes --> M[Write Test File to Repo]
    M --> N[Run Tests via Gradle]
    N --> O[Parse JUnit XML Results]
    O --> P{All Tests Pass?}
    P -- Yes --> Q[Update Jira: Tick AC Checkbox]
    Q --> R[Post Evidence Comment to Jira]
    R --> S[Display Final Verdict in UI]
    S --> T[End: Pipeline Complete]
    P -- No --> U[Display Failures in UI]
    U --> T

    style A fill:#6c5ce7,color:#fff
    style T fill:#00b894,color:#fff
    style E fill:#fdcb6e,color:#333
    style J fill:#fdcb6e,color:#333
    style Q fill:#00b894,color:#fff
    style U fill:#e17055,color:#fff
```

---

## 2. Component View

Every box is a Python module or external system. Arrows show call direction.

```mermaid
flowchart LR
    subgraph Orchestrator["orchestrator.py"]
        ORCH[Pipeline Controller]
    end

    subgraph Context["Built In-Memory"]
        STORY[Hardcoded Story + AC]
        CONST[Constitution Template]
        CTX[Context String Builder]
    end

    subgraph AI["Claude API Calls"]
        NEG[Negotiation Call<br/>system + user prompt<br/>returns spec JSON]
        GEN[Test Generation Call<br/>spec + skill context<br/>returns Java source]
    end

    subgraph Deterministic["Deterministic Zone"]
        COMPILER[Spec Compiler<br/>JSON to YAML]
        VALIDATOR[Spec Validator<br/>enum + referential checks]
        RUNNER[Test Runner<br/>Gradle + JUnit XML parser]
        EVAL[Evaluator<br/>map results to AC verdicts]
    end

    subgraph External["External Systems"]
        JIRA[Jira Cloud API]
        CLAUDE[Claude API<br/>claude-sonnet-4]
    end

    subgraph UI["Web UI"]
        WEB[FastAPI + Static HTML<br/>display-only for bullet tracer]
    end

    ORCH --> STORY
    ORCH --> CONST
    STORY --> CTX
    CONST --> CTX
    CTX --> NEG
    NEG --> CLAUDE
    CLAUDE --> NEG
    NEG --> VALIDATOR
    VALIDATOR --> COMPILER
    COMPILER --> GEN
    GEN --> CLAUDE
    CLAUDE --> GEN
    GEN --> RUNNER
    RUNNER --> EVAL
    EVAL --> JIRA
    ORCH --> WEB
    NEG -.->|display spec| WEB
    EVAL -.->|display verdict| WEB
```

---

## 3. Sequence Diagram

Who calls whom, in what order, with what data.

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant UI as Web UI
    participant C as Claude API
    participant V as Validator
    participant Comp as Compiler
    participant R as Runner
    participant E as Evaluator
    participant J as Jira

    Note over O: Pipeline starts with hardcoded story

    O->>O: Build context string<br/>(story + AC + constitution + repo structure)
    O->>UI: Display story + AC

    rect rgba(108, 92, 231, 0.1)
        Note over O,C: Phase 1 — Spec Generation (single Claude call)
        O->>C: POST /messages
        Note right of C: system: negotiation prompt
        Note right of C: user: full context string
        C-->>O: JSON (classifications, postconditions, preconditions, failure_modes)
        O->>V: Validate spec JSON
        V-->>O: valid / errors
        O->>Comp: Compile JSON to YAML
        Comp-->>O: spec.yaml path
        O->>UI: Display compiled spec
    end

    rect rgba(0, 184, 148, 0.1)
        Note over O,C: Phase 2 — Proof-of-Correctness Generation
        O->>C: POST /messages
        Note right of C: system: test gen skill prompt
        Note right of C: user: spec YAML + constitution
        C-->>O: Java test source code
        O->>O: Write .java file to repo
        O->>R: Run Gradle test
        R-->>O: JUnit XML results
        O->>E: Evaluate results vs spec traceability
        E-->>O: AC verdicts
        O->>UI: Display test results + verdict
    end

    rect rgba(253, 203, 110, 0.1)
        Note over O,J: Phase 3 — Jira Feedback
        O->>J: PUT /issue/{key} (tick AC checkbox)
        O->>J: POST /issue/{key}/comment (evidence)
        J-->>O: 200 OK
        O->>UI: Display complete
    end
```

---

## 4. Data Transformation Pipeline

Shows how data changes shape at each stage.

```mermaid
flowchart TD
    subgraph Input["INPUT: Hardcoded"]
        I1["Jira Story<br/><code>key: DEMO-001</code><br/><code>summary: User Profile Endpoint</code>"]
        I2["AC Checkbox<br/><code>[0] User can view their profile<br/>via GET /api/v1/users/me</code>"]
        I3["Constitution<br/><code>framework: spring-boot</code><br/><code>auth: jwt_bearer</code><br/><code>test: junit5 + mockito</code>"]
    end

    subgraph ContextStr["CONTEXT STRING (built in Python)"]
        CS["Single string containing:<br/>- Story key + summary<br/>- All AC text<br/>- Constitution (framework, auth, API)<br/>- Repo structure hints<br/>- Output format instructions"]
    end

    subgraph SpecJSON["CLAUDE OUTPUT: Spec JSON"]
        SJ["classifications: [{ac_index, type, actor, interface}]<br/>postconditions: [{status, schema, forbidden_fields}]<br/>preconditions: [{id, description, formal, category}]<br/>failure_modes: [{id, violates, status, body}]"]
    end

    subgraph SpecYAML["COMPILED: spec.yaml"]
        SY["meta: {jira_key, status: approved}<br/>requirements: [{contract, verification}]<br/>traceability: {ac_mappings}"]
    end

    subgraph JavaTests["CLAUDE OUTPUT: Java Tests"]
        JT["@WebMvcTest controller test<br/>- test_success_200<br/>- test_no_auth_401<br/>- test_user_not_found_404<br/>- test_forbidden_fields"]
    end

    subgraph Results["TEST RESULTS"]
        TR["JUnit XML → parsed verdicts<br/>AC[0]: PASS/FAIL + evidence"]
    end

    subgraph JiraUpdate["JIRA UPDATE"]
        JU["- [x] AC checkbox ticked<br/>Evidence comment posted"]
    end

    I1 --> CS
    I2 --> CS
    I3 --> CS
    CS -->|Claude API call 1| SJ
    SJ -->|validate + compile| SY
    SY -->|Claude API call 2| JT
    JT -->|gradle test| TR
    TR -->|Jira REST API| JU

    style CS fill:#6c5ce7,color:#fff
    style SJ fill:#fdcb6e,color:#333
    style SY fill:#74b9ff,color:#333
    style JT fill:#fdcb6e,color:#333
    style TR fill:#00b894,color:#fff
    style JU fill:#00b894,color:#fff
```

---

## 5. Context String Assembly

What gets packed into the single Claude API call for spec generation.

```mermaid
flowchart LR
    subgraph Sources["Data Sources"]
        S1[Hardcoded Story]
        S2[Constitution YAML]
        S3[Repo Conventions]
        S4[Output Schema]
    end

    subgraph Builder["Context String Builder<br/>(in orchestrator.py)"]
        B1["STORY BLOCK<br/>key, summary, AC list"]
        B2["CONSTITUTION BLOCK<br/>framework, language, API base path,<br/>auth mechanism, error format,<br/>security invariants"]
        B3["REPO BLOCK<br/>test patterns, naming conventions,<br/>source structure"]
        B4["INSTRUCTIONS BLOCK<br/>required output JSON schema,<br/>constitutional MUST/FORBIDDEN rules,<br/>validation constraints"]
    end

    subgraph Prompt["Final Claude Prompt"]
        SYS["system: You are a verification engineer...<br/>+ constitution + rules + output format"]
        USR["user: Here is the Jira story...<br/>+ AC text + repo context"]
    end

    S1 --> B1
    S2 --> B2
    S2 --> B3
    S4 --> B4
    B1 --> USR
    B2 --> SYS
    B3 --> USR
    B4 --> SYS

    style SYS fill:#6c5ce7,color:#fff
    style USR fill:#74b9ff,color:#333
```

---

## 6. Module Dependency Graph

Build order and import relationships for the bullet tracer.

```mermaid
flowchart BT
    subgraph Core["Core (no dependencies)"]
        CTX[context.py<br/>VerificationContext dataclass]
        VAL[validate.py<br/>deterministic checks]
    end

    subgraph AI["AI Layer"]
        LLM[llm_client.py<br/>Claude SDK wrapper]
    end

    subgraph Negotiation["Spec Generation"]
        SPEC_GEN[spec_generator.py<br/>single-call negotiation<br/>builds context string<br/>calls Claude once<br/>validates + returns JSON]
    end

    subgraph Compilation["Spec Compilation"]
        COMP[compiler.py<br/>JSON to YAML spec]
    end

    subgraph TestGen["Test Generation"]
        TEST_GEN[test_generator.py<br/>builds skill prompt<br/>calls Claude with spec + constitution<br/>returns Java source]
    end

    subgraph Execution["Test Execution"]
        RUN[runner.py<br/>Gradle + JUnit XML]
        EVAL[evaluator.py<br/>results to verdicts]
    end

    subgraph Integration["External Integration"]
        JIRA[jira_client.py<br/>tick checkbox + comment]
    end

    subgraph Orchestration["Orchestrator"]
        ORCH[orchestrator.py<br/>wires everything together]
        WEB[web.py<br/>display layer]
    end

    CTX --> SPEC_GEN
    VAL --> SPEC_GEN
    LLM --> SPEC_GEN
    CTX --> COMP
    SPEC_GEN --> ORCH
    COMP --> ORCH
    LLM --> TEST_GEN
    TEST_GEN --> ORCH
    RUN --> ORCH
    EVAL --> ORCH
    JIRA --> ORCH
    ORCH --> WEB
```

---

## 7. State Machine

The orchestrator's internal state progression.

```mermaid
stateDiagram-v2
    [*] --> Initializing: orchestrator starts

    Initializing --> ContextReady: load story + constitution + build context string
    ContextReady --> GeneratingSpec: call Claude API (negotiation prompt)
    GeneratingSpec --> ValidatingSpec: parse JSON response
    ValidatingSpec --> GeneratingSpec: validation failed (retry)
    ValidatingSpec --> CompilingSpec: validation passed
    CompilingSpec --> SpecReady: write YAML file

    SpecReady --> GeneratingTests: call Claude API (test gen prompt)
    GeneratingTests --> WritingTests: parse Java source
    WritingTests --> RunningTests: gradle test
    RunningTests --> Evaluating: parse JUnit XML

    Evaluating --> AllPassed: every AC verdict = PASS
    Evaluating --> SomeFailed: any verdict = FAIL

    AllPassed --> UpdatingJira: tick checkbox + post comment
    UpdatingJira --> Done
    SomeFailed --> Done: display failures

    Done --> [*]

    note right of GeneratingSpec
        Single Claude call replaces
        the 4-phase negotiation loop.
        All context in one prompt.
    end note

    note right of GeneratingTests
        Second Claude call.
        Prompt contains spec YAML +
        constitution + skill template.
    end note
```

---

## 8. Hardcoded Story Definition

What the bullet tracer locks in. No Jira fetch needed for the tracer run.

```yaml
# Hardcoded in orchestrator.py
story:
  key: "DEMO-001"
  summary: "User can view their profile"
  acceptance_criteria:
    - index: 0
      text: "Authenticated user can retrieve their profile via GET /api/v1/users/me"
      checked: false

constitution:
  project:
    framework: spring-boot
    language: java
    version: 17
  api:
    base_path: "/api/v1"
    auth:
      mechanism: jwt_bearer
      claims: [sub, exp, iat]
    error_format:
      example: '{"error":"...","message":"...","timestamp":"...","path":"..."}'
  testing:
    unit_framework: junit5
    assertion_library: assertj
    mocking_library: mockito
    patterns: [controller_test, service_test]
  verification_standards:
    security_invariants:
      - "Never expose password, passwordHash, ssn, or internalId"
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Single Claude call for spec** | Bullet tracer proves the pipe works. No negotiation loop, no human approval. One prompt with all context packed in. |
| **Context string built in Python** | The orchestrator file is the single source of truth for what Claude sees. No file-loading at runtime — everything is a string literal or assembled from hardcoded dicts. |
| **Java test generation (not Python)** | The constitution targets Spring Boot / JUnit5. This proves the system generates tests in the *project's* language, not the pipeline's language. |
| **Deterministic validation between calls** | Claude output is validated before compilation (spec JSON) and before execution (Java syntax). Retries are automatic with error feedback. |
| **Jira update is the final proof** | A ticked checkbox on a real Jira ticket is the end-to-end proof that the pipeline works from intent to verified outcome. |
| **Web UI is display-only** | For the bullet tracer, the UI shows progress and results. No interactive negotiation. The orchestrator drives everything. |
