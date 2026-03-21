# Intent-to-Verification Spec Engine: AC → Formal Specification Design Plan

## Executive Summary

This document defines the design for a system that transforms fuzzy, human-written Jira Acceptance Criteria into formal, machine-verifiable specifications. The specification becomes the single source of truth for correctness — code is correct if and only if it satisfies the spec, and the spec is a faithful formalization of the business intent.

The system uses an AI-driven negotiation loop to systematically eliminate ambiguity across six dimensions, then emits a structured YAML specification that can be mechanically translated into verification artifacts (tests, alert configs, contract checks, observability probes) by downstream skill agents.

**Key Principle:** AI handles the fuzzy-to-formal translation (negotiation + spec generation). Everything downstream of the spec — routing, test generation, execution, Jira updates — is deterministic. The spec is the boundary between intelligence and automation.

---

## 1. Conceptual Architecture

### 1.1 The Correctness Chain

```
Jira AC (human intent, fuzzy)
    ↓  [AI Negotiation — structured disambiguation]
Formal Spec (YAML, machine-precise)
    ↓  [Deterministic Routing — lookup table, zero AI]
Verification Artifacts (tests, alerts, contracts, probes)
    ↓  [Deterministic Execution — local or CI]
Pass/Fail Results
    ↓  [Deterministic Mapping — spec refs → AC checkboxes]
Jira Status Update
```

The correctness argument: If a test passes, the spec is satisfied (because the test was mechanically generated from the spec). If the spec is satisfied, the AC is met (because the spec was negotiated from the AC with human approval). Therefore: passing tests = business intent verified.

### 1.2 Design Influences

This design borrows concepts from multiple disciplines:

| Concept | Source | How It's Used Here |
|---------|--------|--------------------|
| State machine orchestration | Sherpa (Aggregate Intellect / McGill) | The negotiation loop is a hierarchical state machine with composite states for each phase. Transitions are either rule-based (phase completion checks) or LLM-driven (clarification questions). |
| Agent Skills / progressive disclosure | Agent Skills standard (Block, Anthropic) | Each negotiation phase and each downstream generator is a self-contained skill with a SKILL.md defining its prompt template, input/output contract, and trigger conditions. Skills are loaded on demand, not all at once. |
| Harness engineering | Anthropic, HumanLayer (12-factor agents) | The orchestrator is a harness, not an agent. It manages context windows, enforces phase transitions, and provides the belief/context object that flows through the pipeline. The AI operates within the harness, not above it. |
| Spec-driven development | GitHub Spec Kit, AWS Kiro | Specifications are the source of truth. Code serves the spec, not the other way around. The spec is a living artifact committed to the repo. |
| EARS notation | Alistair Mavin (Rolls-Royce) | Requirements are formalized using WHEN/SHALL/IF-THEN/WHILE sentence patterns to eliminate natural language ambiguity. Each EARS statement maps to exactly one verifiable assertion. |
| Design by Contract | Bertrand Meyer (Eiffel) | Every behavior is defined by preconditions (what must be true before), postconditions (what must be true after), and invariants (what must always be true). |
| ATDD (Acceptance Test-Driven Development) | Agile Alliance | The spec is written before the code. Tests are derived from the spec. Code is written to pass the tests. |
| BMAD Agent-as-Code | BMad Method | Each negotiation phase agent and each generator skill is defined as a markdown file with a persona, responsibilities, and output contract — portable, versionable, and diffable. |
| Constitution / Steering | GitHub Spec Kit, AWS Kiro | A repo-level constitution file captures organizational conventions, tech stack, and testing patterns. All spec generation and negotiation is steered by this context. |
| Conformance suites | Simon Willison | Specs are language-independent contracts (YAML) that any implementation must satisfy. The test framework is a translation detail, not a spec detail. |

### 1.3 The Six Dimensions of Ambiguity

Every acceptance criterion contains ambiguity across these dimensions. The negotiation loop must systematically probe each one:

1. **Actors** — Who exactly is performing the action? Authenticated user, admin, API client, system timer, another microservice?
2. **Boundaries** — What data or behavior constitutes the capability? Which fields, from which sources, in what format, with what limits?
3. **Preconditions** — What must be true before the behavior can succeed? Authentication, authorization, account state, data existence, rate limits?
4. **Failure Modes** — For every precondition, what happens when it's violated? What are ALL the ways this can fail, and what is the exact error behavior for each?
5. **Invariants** — What must NEVER happen regardless of input? Data leakage, sensitive field exposure, unauthorized state transitions, cross-tenant access?
6. **Non-Functional Constraints** — What are the performance, observability, compliance, and operational requirements? Latency SLAs, alerting thresholds, audit logging, data classification?

These six dimensions are the backbone of the negotiation protocol. Each phase of the negotiation targets one or more dimensions.

---

## 2. The Repository Constitution (Init Phase)

### 2.1 Purpose

Before any Jira ticket is processed, the system needs to understand the repository it's working with. The constitution is a one-time (or periodically refreshed) snapshot of:

- Language, framework, and build tooling
- Existing test patterns (imports, annotations, assertion styles, directory structure)
- API conventions (auth mechanism, error format, base paths)
- Observability stack (APM provider, alert format, logging framework)
- Organizational conventions (branch naming, commit format, PR templates)
- Verification standards (required coverage types, quality gates, compliance requirements)

### 2.2 Constitution Schema

```yaml
# .verify/constitution.yaml
# Generated by: verify init
# Last updated: 2026-03-21

project:
  name: "user-service"
  language: java
  version: 17
  framework: spring-boot
  framework_version: "3.2"
  build_tool: gradle

source_structure:
  main: "src/main/java"
  test: "src/test/java"
  resources: "src/main/resources"
  package_root: "com.example.userservice"

testing:
  unit_framework: junit5
  assertion_library: assertj
  mocking_library: mockito
  test_runner: "gradle test"
  naming_convention: "{ClassName}Test.java"
  method_naming: "should_{expected_behavior}_when_{condition}"
  
  # Discovered by scanning existing tests in the repo
  patterns:
    - id: controller_test
      description: "REST controller tests using MockMvc"
      example_file: "src/test/java/com/example/controller/UserControllerTest.java"
      annotations: ["@WebMvcTest", "@MockBean"]
      imports:
        - "org.springframework.test.web.servlet.MockMvc"
        - "org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest"
      assertion_style: "mockMvc.perform().andExpect()"
      
    - id: service_test
      description: "Service layer unit tests with Mockito"
      example_file: "src/test/java/com/example/service/UserServiceTest.java"
      annotations: ["@ExtendWith(MockitoExtension.class)", "@Mock", "@InjectMocks"]
      imports:
        - "org.mockito.junit.jupiter.MockitoExtension"
      assertion_style: "assertThat().isEqualTo()"

    - id: integration_test
      description: "Full Spring context integration tests"
      example_file: "src/test/java/com/example/integration/UserApiIntegrationTest.java"
      annotations: ["@SpringBootTest", "@AutoConfigureMockMvc", "@Testcontainers"]
      imports:
        - "org.springframework.boot.test.context.SpringBootTest"

api:
  style: rest
  base_path: "/api/v1"
  auth:
    mechanism: jwt_bearer
    token_header: "Authorization"
    token_prefix: "Bearer "
    claims: [sub, exp, iat, roles]
  error_format:
    schema:
      type: object
      properties:
        error: { type: string }
        message: { type: string }
        timestamp: { type: string, format: iso8601 }
        path: { type: string }
    example: '{"error": "not_found", "message": "User not found", "timestamp": "...", "path": "/api/v1/users/me"}'
  common_status_codes: [200, 201, 204, 400, 401, 403, 404, 409, 422, 429, 500]

observability:
  apm_provider: new_relic
  alert_format: nrql
  default_latency_sla_ms: 500
  logging_framework: slf4j
  log_format: structured_json
  tracing: opentelemetry
  metrics_endpoint: "/actuator/prometheus"

infrastructure:
  ci_cd: github_actions
  deployment_target: aws_ecs
  environments: [dev, staging, prod]
  feature_flags: launchdarkly

conventions:
  branch_naming: "feat/{jira_key}-{short-description}"
  commit_format: "[{jira_key}] {message}"
  pr_template: ".github/pull_request_template.md"
  pr_description_must_include: [jira_link, spec_ref, test_results]

verification_standards:
  # Organizational requirements for what "verified" means
  required_verification_types:
    - unit_test        # Always required
    - schema_contract  # Required for API endpoints
  optional_verification_types:
    - integration_test
    - performance_test
    - alert_config
    - compliance_check
  coverage_minimum: 80
  security_invariants:
    - "Never expose password, SSN, or internal IDs in API responses"
    - "Never allow cross-tenant data access"
    - "All PII fields must be classified and logged when accessed"
```

### 2.3 Init Phase Process

The init phase can be automated (repo scanning) or manual (developer fills in a template). For the hackathon, pre-write the constitution for the dummy app. In production, the init skill would:

1. **Detect stack**: Parse `build.gradle` / `pom.xml` / `package.json` / `requirements.txt` for language, framework, and dependencies
2. **Sample existing tests**: Find 3-5 test files, extract annotations, imports, assertion patterns, and directory conventions
3. **Read config files**: Parse `.github/`, CI configs, `newrelic.yml`, `application.yml`, `Dockerfile`
4. **Identify API patterns**: Scan controller/route files for endpoint conventions, auth annotations, error handling patterns
5. **Present for approval**: Show the discovered constitution to the developer for confirmation and amendment

---

## 3. The Negotiation Protocol

### 3.1 Overview

The negotiation is a multi-phase, human-in-the-loop conversation between the AI and the developer. Each phase targets specific dimensions of ambiguity using established requirements engineering techniques.

```
┌─────────────────────────────────────────────────┐
│              NEGOTIATION STATE MACHINE            │
│                                                   │
│  ┌──────────┐   ┌──────────────┐   ┌──────────┐ │
│  │  Phase 0  │──▶│   Phase 1    │──▶│ Phase 2  │ │
│  │  Ingest   │   │  Interface   │   │  Happy   │ │
│  │  & Parse  │   │  Discovery   │   │  Path    │ │
│  └──────────┘   └──────────────┘   └──────────┘ │
│                                         │        │
│  ┌──────────┐   ┌──────────────┐        ▼        │
│  │  Phase 5  │◀──│   Phase 4    │◀──┌──────────┐ │
│  │ Complete- │   │  Invariant   │   │ Phase 3  │ │
│  │  ness     │   │  Extraction  │   │ Failure  │ │
│  └──────────┘   └──────────────┘   │  Modes   │ │
│       │                             └──────────┘ │
│       ▼                                          │
│  ┌──────────┐   ┌──────────────┐                 │
│  │  Phase 6  │──▶│   Phase 7    │                 │
│  │ Formal-   │   │   Human      │                 │
│  │ ization   │   │   Approval   │                 │
│  └──────────┘   └──────────────┘                 │
│                        │                          │
│                        ▼                          │
│                  [Emit Spec YAML]                 │
└─────────────────────────────────────────────────┘
```

### 3.2 Phase 0: AC Ingestion & Parse (Deterministic)

**Dimension targeted:** None — this is pure data retrieval.

**Input:** Jira ticket key (e.g., PROJ-1234)
**Output:** Structured AC list, ticket metadata

**Process:**
1. Call Jira REST API to fetch ticket
2. Extract: summary, description, acceptance criteria checkboxes, story points, labels, components
3. Parse AC into individual items, preserving checkbox index (for later Jira update mapping)
4. Load the repo constitution from `.verify/constitution.yaml`
5. Initialize the VerificationContext (the belief object that flows through all phases)

**Implementation note:** This phase is 100% deterministic — no AI involved. It's a Python/Node script making REST API calls.

```python
# Pseudocode for Phase 0
context = VerificationContext(
    jira_key="PROJ-1234",
    raw_ac=[
        { "index": 0, "text": "User can view their profile", "checked": False },
        { "index": 1, "text": "Profile endpoint responds within 500ms p99", "checked": False },
        { "index": 2, "text": "Profile data is never exposed to other users", "checked": False }
    ],
    constitution=load_yaml(".verify/constitution.yaml"),
    negotiation_log=[],
    requirements=[]
)
```

### 3.3 Phase 1: Interface & Actor Discovery

**Dimensions targeted:** Actors, Boundaries (partial)
**Technique:** EARS-based classification + Constitution-guided questioning

**What the AI does:**
For each AC, the AI determines what *type* of requirement it is (API behavior, data constraint, performance SLA, security invariant, infrastructure concern) and who the actor is. The constitution steers this — if the repo is a Spring Boot REST API, the AI knows to ask about endpoints, HTTP methods, and auth.

**Prompt strategy:**
```
SYSTEM: You are a requirements analyst. You are formalizing acceptance 
criteria for the {constitution.project.name} project, a 
{constitution.language} {constitution.framework} application.

The API uses {constitution.api.auth.mechanism} authentication with 
base path {constitution.api.base_path}.

For each acceptance criterion, determine:
1. What TYPE of requirement is this? (api_behavior, data_constraint, 
   performance_sla, security_invariant, observability, compliance)
2. Who is the ACTOR? (authenticated_user, admin, api_client, system, 
   anonymous_user)
3. What is the INTERFACE? (endpoint path, method, or N/A for non-API)

For API behaviors, propose the endpoint. For non-API requirements, 
identify the verification domain.

Ask the developer to confirm or correct each classification.
```

**Example interaction:**
```
AI: I've classified your 3 acceptance criteria:

  AC[0] "User can view their profile"
    → Type: api_behavior
    → Actor: authenticated_user
    → Interface: GET /api/v1/users/me
    → Auth: jwt_bearer (from constitution)
    
  AC[1] "Profile endpoint responds within 500ms p99"
    → Type: performance_sla
    → Applies to: GET /api/v1/users/me (same endpoint as AC[0])
    → Metric: response_time_p99 < 500ms
    
  AC[2] "Profile data is never exposed to other users"
    → Type: security_invariant
    → Scope: ALL endpoints returning user data
    → This is a universal constraint, not tied to one endpoint

Questions:
1. For AC[0], is "their profile" specifically GET /api/v1/users/me, 
   or could it also include GET /api/v1/users/{id}?
2. For AC[2], should this invariant apply only to the profile 
   endpoint, or to every endpoint that returns user data?
3. Is there an admin actor who CAN view other users' profiles, 
   or is that strictly forbidden?

Dev: 1. Just /users/me for now. 2. Every endpoint with user data. 
     3. Admins can view via GET /api/v1/admin/users/{id} but that's 
        a separate story.
```

**Phase exit condition (rule-based):** Every AC has a classified type, actor, and interface. The developer has confirmed the classifications.

### 3.4 Phase 2: Happy Path Contract (Postconditions)

**Dimensions targeted:** Boundaries (full), Actors (refinement)
**Technique:** Example-driven boundary discovery + Design by Contract postconditions

**What the AI does:**
For each API behavior requirement, the AI proposes a concrete success response and asks the developer to confirm the exact shape. The constitution's `api.error_format` and existing patterns guide the proposal.

**Prompt strategy:**
```
SYSTEM: For the endpoint GET /api/v1/users/me, define the exact 
success response. You must specify:

1. HTTP status code
2. Content-Type
3. Response body schema with:
   - Every field name, type, and format
   - Which fields are required vs optional/nullable
   - Any constraints linking response fields to request context
     (e.g., "response.id MUST equal the authenticated user's id")
   - Any fields that must NEVER appear (from constitution.verification_standards.security_invariants)

Generate a concrete example response, then ask the developer if it's 
correct and complete.
```

**Example interaction:**
```
AI: Here's what I think a successful GET /api/v1/users/me looks like:

  Status: 200
  Content-Type: application/json
  
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",  ← must equal jwt.sub
    "email": "danny@example.com",
    "displayName": "Danny Trevino",
    "createdAt": "2024-01-15T08:30:00Z",
    "avatar": null
  }

  Required fields: id, email, displayName, createdAt
  Optional/nullable: avatar
  
  Forbidden fields (from your security standards): 
    password, ssn, internalId, passwordHash
  
  Constraint: response.id MUST equal the authenticated user's JWT sub claim.
  This prevents data leakage by construction.

Questions:
1. Are there other profile fields I'm missing? 
   (phone? address? subscription tier? role?)
2. Is displayName always present, or can it be null for new accounts?
3. Should createdAt be the account creation date or last login?

Dev: 1. Add 'role' (string, required) and 'lastLogin' (iso8601, nullable).
     2. displayName is always present, set during registration.
     3. createdAt is account creation.
```

**Phase exit condition (rule-based):** Every API behavior requirement has a complete success response schema with all fields typed, constrained, and confirmed.

### 3.5 Phase 3: Precondition Formalization

**Dimensions targeted:** Preconditions
**Technique:** Design by Contract preconditions + EARS WHEN/WHILE patterns

**What the AI does:**
For each behavior, the AI identifies every condition that must be true for the happy path to execute. Each precondition is expressed as both a human-readable description AND a semi-formal expression.

**Prompt strategy:**
```
SYSTEM: For the endpoint GET /api/v1/users/me, identify every 
precondition that must hold for the success response to be valid.

For each precondition:
1. Give it an ID (PRE-001, PRE-002, etc.)
2. Write a human-readable description
3. Write a semi-formal expression using the pattern:
   {entity}.{field} {operator} {value}
4. Classify it as: authentication, authorization, data_existence, 
   data_state, rate_limit, or system_health

The authentication mechanism is {constitution.api.auth.mechanism} 
with required claims: {constitution.api.auth.claims}.
```

**Example interaction:**
```
AI: I've identified 3 preconditions for GET /api/v1/users/me:

  PRE-001 (authentication):
    "Request includes a valid, non-expired JWT Bearer token"
    formal: jwt != null AND jwt.exp > now() AND jwt.sub != null
    
  PRE-002 (data_existence):
    "A user record exists for the authenticated subject"
    formal: users.findById(jwt.sub) != null
    
  PRE-003 (data_state):
    "The user account is in active status"
    formal: users.findById(jwt.sub).status == 'ACTIVE'

Questions:
1. Should I add a rate limiting precondition? Your constitution 
   doesn't mention rate limits for this endpoint.
2. Does the JWT need specific roles/scopes, or is any valid 
   JWT sufficient?
3. Is there a difference between "account not found" (never existed)
   and "account deleted" (existed, then removed)?

Dev: 1. No rate limit for MVP. 2. Any valid JWT is fine. 
     3. Yes — not found is 404, soft-deleted is 410 Gone.
```

**Phase exit condition (rule-based):** Every behavior has at least one precondition. Every precondition has an ID, description, formal expression, and classification.

### 3.6 Phase 4: Failure Mode Enumeration

**Dimensions targeted:** Failure Modes
**Technique:** FMEA-inspired systematic failure analysis + EARS IF-THEN patterns

**What the AI does:**
For each precondition identified in Phase 3, the AI systematically enumerates every way it can be violated and asks for the exact error response. This is the most valuable phase — it surfaces edge cases the PO never considered.

**Prompt strategy:**
```
SYSTEM: For each precondition, enumerate every distinct failure mode. 
A failure mode is a specific way a precondition can be violated that 
produces a different system response.

For each failure mode:
1. Give it an ID (FAIL-001, etc.)
2. Describe the specific condition
3. Reference which precondition it violates
4. Define the exact response: status code, error body 
   (using the project's standard error format from the constitution)

The project's error format is:
{constitution.api.error_format.example}

IMPORTANT: Consider these common failure subcategories:
- For authentication: missing token, malformed token, expired token, 
  token for wrong service, revoked token
- For data existence: never existed, soft-deleted, hard-deleted
- For data state: each possible invalid state (inactive, suspended, 
  pending_verification, locked)

Ask the developer about any distinctions that are ambiguous.
```

**Example interaction:**
```
AI: Here are the failure modes for GET /api/v1/users/me:

  FAIL-001 (violates PRE-001):
    When: "No Authorization header present"
    Status: 401
    Body: { "error": "unauthorized", "message": "Authentication required" }

  FAIL-002 (violates PRE-001):
    When: "JWT is expired"
    Status: 401
    Body: { "error": "token_expired", "message": "Token has expired", 
            "retryable": true }

  FAIL-003 (violates PRE-001):
    When: "JWT is malformed or signature is invalid"
    Status: 401
    Body: { "error": "invalid_token", "message": "Token is invalid" }

  FAIL-004 (violates PRE-002):
    When: "JWT sub references a user that never existed"
    Status: 404
    Body: { "error": "user_not_found", "message": "User not found" }

  FAIL-005 (violates PRE-002):
    When: "JWT sub references a soft-deleted user"
    Status: 410
    Body: { "error": "user_deleted", "message": "Account has been removed" }

  FAIL-006 (violates PRE-003):
    When: "User account exists but status is SUSPENDED"
    Status: 403
    Body: { "error": "account_suspended", "message": "Account is suspended" }

  FAIL-007 (violates PRE-003):
    When: "User account exists but status is PENDING_VERIFICATION"
    Status: 403
    Body: { "error": "account_pending", "message": "Account pending verification" }

Questions:
1. Should FAIL-002 (expired) and FAIL-003 (malformed) return the same 
   status and error, or different ones? Some APIs distinguish these for 
   client retry logic.
2. I split FAIL-006 and FAIL-007 because SUSPENDED and PENDING are 
   different states. Should they have different error codes, or both 
   return 403 with the same error body?
3. Security question: For FAIL-004 and FAIL-005, should the API reveal 
   whether the user ever existed? Returning 404 vs 410 leaks information.
   Should both return 404 for security?

Dev: 1. Keep them different — expired is retryable, malformed isn't.
     2. Same 403 is fine, but different error strings.
     3. Good catch — both should return 404. Don't leak deletion status.
```

Note that question 3 is the kind of security insight that makes this system valuable — it catches information disclosure vulnerabilities that the PO would never think to specify.

**Phase exit condition (rule-based):** Every precondition has at least one failure mode. Every failure mode has an exact status code and response body.

### 3.7 Phase 5: Invariant Extraction

**Dimensions targeted:** Invariants, Non-Functional Constraints
**Technique:** EARS ubiquitous patterns + Constitution security standards + Completeness checklist

**What the AI does:**
The AI extracts universal properties that must hold regardless of the specific request. Some come from the AC itself, some from the constitution's security standards, and some are inferred from the data model.

**Prompt strategy:**
```
SYSTEM: Extract invariants — properties that must ALWAYS be true for 
this endpoint, regardless of the specific request or scenario.

Sources for invariants:
1. The acceptance criteria themselves (AC[2] is explicitly an invariant)
2. The constitution's security_invariants
3. Inferred from the data model (e.g., if response contains user data, 
   it must be the authenticated user's data)
4. Non-functional requirements from the AC or constitution

For each invariant:
1. Give it an ID (INV-001, etc.)
2. Classify: security, performance, data_integrity, compliance, 
   idempotency, observability
3. Write the rule as a universal statement
4. Identify the verification type: unit_test, property_test, 
   alert_config, compliance_check, schema_validation
5. If verification type is NOT unit_test, specify the target system 
   (e.g., new_relic, opentelemetry, datadog)
```

**Example interaction:**
```
AI: I've extracted these invariants:

  INV-001 (security, from AC[2]):
    "Response body MUST only contain data belonging to the 
     authenticated user (response.id == jwt.sub)"
    Verification: unit_test
    
  INV-002 (security, from constitution):
    "Response body MUST NEVER contain fields: password, ssn, 
     internalId, passwordHash"
    Verification: unit_test
    
  INV-003 (security, inferred):
    "No response — success or error — may include stack traces, 
     internal exception details, or database query information"
    Verification: unit_test
    
  INV-004 (performance, from AC[1]):
    "p99 response time MUST be below 500ms"
    Verification: alert_config → new_relic
    
  INV-005 (data_integrity, inferred):
    "GET requests MUST be safe — no side effects on user data"
    Verification: unit_test (call twice, assert same response 
    and no state change)
    
  INV-006 (observability, from constitution):
    "All profile access MUST be logged with user ID, timestamp, 
     and requesting IP for audit trail"
    Verification: unit_test (assert log output contains required fields)

  INV-007 (compliance, inferred from PII in response):
    "Response contains PII (email). Data classification label 
     MUST be present in response headers or metadata."
    Verification: unit_test (check for X-Data-Classification header)

Questions:
1. INV-007 is inferred because email is PII. Does your org require 
   data classification headers on PII responses?
2. Should I add an invariant for CORS? (e.g., "Endpoint must only 
   accept requests from allowed origins")
3. For INV-006 (audit logging), what's the required log format? 
   Structured JSON via SLF4J per your constitution?

Dev: 1. Yes, add it — X-Data-Classification: PII-STANDARD.
     2. Not for this story, CORS is handled at the gateway level.
     3. Yes, structured JSON. Include user_id, action, timestamp, 
        source_ip, and response_status.
```

**Phase exit condition (rule-based):** At least the constitution's security invariants are represented. All AC items that are invariants (not behaviors) have been captured. Developer has confirmed all invariants.

### 3.8 Phase 6: Completeness Sweep & Verification Routing

**Dimensions targeted:** All (gap check)
**Technique:** Dimension checklist sweep + Verification type routing

**What the AI does:**
Two tasks in one phase:
1. Run through a standard checklist of dimensions and flag anything the AC + negotiation didn't cover
2. For every requirement, precondition, failure mode, and invariant, assign a verification type and target skill

**Completeness checklist (customizable per org):**
```
□ Authentication — who can access? [COVERED]
□ Authorization / RBAC — role/scope restrictions? [COVERED: any valid JWT]
□ Input validation — request params/body constraints? [N/A for GET /me]
□ Output schema — response shape fully defined? [COVERED]
□ Error responses — all failure modes enumerated? [COVERED]
□ Rate limiting — request throttling? [EXPLICITLY DEFERRED]
□ Pagination — needed for collection endpoints? [N/A]
□ Caching — response cacheable? TTL? [NOT ADDRESSED]
□ Versioning — API version strategy? [NOT ADDRESSED]
□ Idempotency — safe and idempotent? [COVERED: INV-005]
□ Observability — latency SLA? logging? alerting? [COVERED]
□ Security — data leakage? field exposure? [COVERED]
□ Data classification — PII handling? [COVERED: INV-007]
□ Deprecation — replacing older endpoint? [NOT ADDRESSED]
□ Documentation — OpenAPI spec impact? [NOT ADDRESSED]
```

Items marked [NOT ADDRESSED] are surfaced to the developer: "The AC and our negotiation didn't cover caching, versioning, or deprecation. Should I add spec entries for any of these, or are they out of scope for this story?"

**Verification routing:**
For each spec element, the AI assigns the skill that will generate the verification artifact. This assignment is deterministic — it's based on the verification type, not AI judgment at runtime.

```yaml
# Routing table generated in Phase 6
verification_routing:
  - refs: [success, FAIL-001 through FAIL-007, INV-001, INV-002, INV-003, INV-005]
    skill: junit5_controller_test
    pattern: controller_test  # from constitution
    output: "src/test/java/.../UserProfileVerificationTest.java"
    
  - refs: [success.schema]
    skill: schema_contract_test
    pattern: integration_test  # from constitution
    output: "src/test/java/.../UserProfileContractTest.java"
    
  - refs: [INV-004]
    skill: newrelic_alert_config
    output: "infra/alerts/user-profile-latency.json"
    
  - refs: [INV-006]
    skill: audit_log_test
    pattern: service_test  # from constitution
    output: "src/test/java/.../UserProfileAuditTest.java"
    
  - refs: [INV-007]
    skill: compliance_header_test
    pattern: controller_test  # from constitution
    output: "src/test/java/.../UserProfileComplianceTest.java"
```

**Phase exit condition (rule-based):** All spec elements have a verification routing entry. All checklist items are either covered or explicitly deferred with developer acknowledgment.

### 3.9 Phase 7: EARS Formalization & Human Approval

**Dimensions targeted:** All (final review)
**Technique:** EARS notation synthesis + Full spec preview

**What the AI does:**
Synthesize everything from Phases 1-6 into EARS statements — one human-readable sentence per verifiable assertion. Present the complete spec to the developer for final approval.

The EARS statements serve as the human-reviewable layer. The developer reads these and can validate them without understanding YAML schemas. Each EARS statement maps to a specific contract element, which maps to a specific test.

**Example EARS output:**
```
REQUIREMENT: REQ-001 (AC checkbox 0: "User can view their profile")

WHEN an authenticated user with a valid JWT requests GET /api/v1/users/me,
  the system SHALL return 200 with a JSON body containing id, email, 
  displayName, role, createdAt, lastLogin, and avatar.

WHEN an authenticated user requests GET /api/v1/users/me,
  the system SHALL return a response where id equals the JWT sub claim.

IF the request has no Authorization header,
  THEN the system SHALL return 401 with error "unauthorized".

IF the JWT is expired,
  THEN the system SHALL return 401 with error "token_expired" and 
  retryable=true.

IF the JWT is malformed or has an invalid signature,
  THEN the system SHALL return 401 with error "invalid_token".

IF the JWT sub references a non-existent or deleted user,
  THEN the system SHALL return 404 with error "user_not_found".

IF the user account is suspended or pending verification,
  THEN the system SHALL return 403 with the appropriate error string.

The system SHALL never include password, ssn, internalId, or 
  passwordHash in any profile response. [UBIQUITOUS]

The system SHALL never include stack traces or internal exception 
  details in any error response. [UBIQUITOUS]

The system SHALL respond within 500ms at the 99th percentile. [UBIQUITOUS]

The system SHALL log every profile access with user_id, action, 
  timestamp, source_ip, and response_status. [UBIQUITOUS]

REQUIREMENT: REQ-002 (AC checkbox 1: "Profile endpoint responds within 500ms p99")
  [Covered by INV-004 above]

REQUIREMENT: REQ-003 (AC checkbox 2: "Profile data is never exposed to other users")
  [Covered by INV-001 above]
```

The developer reviews these statements. If they approve, the full YAML spec is emitted. If they want changes, they specify which statement to modify and the negotiation re-enters the relevant phase.

**Phase exit condition (human approval):** Developer explicitly approves the EARS summary and the spec is frozen.

---

## 4. The Spec Format (Output Schema)

### 4.1 Format Choice: YAML

Rationale:
- LLMs generate valid YAML more reliably than JSON (no trailing comma / bracket matching issues)
- YAML supports comments, enabling inline traceability annotations
- Human-readable for demo presentations and code review
- Validated against a JSON Schema for structural correctness

### 4.2 Complete Spec Schema

```yaml
# .verify/specs/{jira_key}.yaml
# Generated by: negotiation engine
# Approved by: {developer} at {timestamp}
# Validated against: .verify/schema/spec-schema.json

meta:
  spec_version: "1.0"
  jira_key: string        # e.g., "PROJ-1234"
  jira_summary: string    # Ticket title for reference
  generated_at: iso8601
  approved_at: iso8601
  approved_by: string     # Developer who approved
  constitution_ref: string # Path to constitution used
  negotiation_log: string  # Path to full negotiation transcript
  status: enum [draft, in_review, approved, superseded]

# Repo context snapshot at spec generation time
context:
  relevant_source_files: list[string]  # Files the spec touches
  relevant_test_files: list[string]    # Existing tests in this area
  related_specs: list[string]          # Other specs this depends on

# Each AC checkbox becomes one or more requirement blocks
requirements:
  - id: string            # REQ-001, REQ-002, etc.
    ac_checkbox: integer   # Index of the Jira AC checkbox this satisfies
    ac_text: string        # Original AC text verbatim (for traceability)
    title: string          # Human-readable requirement name
    type: enum [api_behavior, data_constraint, performance_sla, 
                security_invariant, observability, compliance]

    # EARS formalization — human-readable AND machine-parseable
    ears: list
      - type: enum [ubiquitous, event_driven, state_driven, unwanted, optional]
        when: string       # For event_driven / state_driven
        if: string         # For unwanted
        shall: string      # The requirement itself
        then: string       # For unwanted (the error behavior)
        where: string      # For optional (the feature condition)

    # The formal contract — precise enough for mechanical test generation
    contract:
      interface:           # Only for api_behavior type
        method: enum [GET, POST, PUT, PATCH, DELETE]
        path: string
        auth: string       # Reference to constitution auth config
        request_params: object   # Query params schema (if any)
        request_body: object     # Request body schema (if any)

      preconditions: list
        - id: string       # PRE-001, etc.
          description: string
          formal: string   # Semi-formal expression
          category: enum [authentication, authorization, data_existence, 
                         data_state, rate_limit, system_health]

      success:             # Only for api_behavior type
        status: integer
        content_type: string
        schema:
          type: string
          required: list[string]
          properties: object  # JSON Schema-like field definitions
          forbidden_fields: list[string]
        body_constraints: list[string]  # e.g., "response.id == jwt.sub"

      failures: list
        - id: string       # FAIL-001, etc.
          when: string     # Human-readable condition
          violates: string # Reference to precondition ID
          status: integer
          body: object     # Exact error response body

      invariants: list
        - id: string       # INV-001, etc.
          type: enum [security, performance, data_integrity, 
                     compliance, idempotency, observability]
          rule: string     # The invariant as a universal statement
          formal: string   # Semi-formal expression (optional)

      constraints: list    # For non-API requirements
        - id: string
          metric: string
          operator: enum [lt, lte, gt, gte, eq, ne]
          value: number
          unit: string
          percentile: number  # e.g., 99 for p99

    # Verification routing — deterministic dispatch to skills
    verification: list
      - refs: list[string]       # IDs of contract elements this covers
        skill: string            # Skill agent ID
        pattern: string          # Constitution test pattern to follow
        output: string           # Output file path
        framework: string        # e.g., junit5, jest, pytest

# =============================================================
# TOP-LEVEL TRACEABILITY MAP
# This is the ONLY section the Jira updater reads.
# It defines the many-to-many mapping between AC checkboxes and
# verification results, with explicit pass/fail evaluation logic.
# =============================================================
traceability:
  ac_mappings: list
    - ac_checkbox: integer       # Jira AC checkbox index (0-based)
      ac_text: string            # Original AC text verbatim
      pass_condition: enum [ALL_PASS, ANY_PASS, PERCENTAGE]
      threshold: number          # Only for PERCENTAGE (e.g., 80 = 80%)
      required_verifications: list
        - ref: string            # Spec element ID (e.g., "REQ-001.FAIL-002")
          description: string    # Human-readable what this proves
          verification_type: enum [
            test_result,         # Pass/fail from test runner output
            deployment_check,    # File exists + structurally valid
            config_validation,   # Config matches a schema
            api_health_check,    # HTTP call returns expected result
            log_assertion,       # Log output contains required entries
            metric_query,        # APM metric meets threshold
            manual_gate          # Human must confirm (stretch goal)
          ]
          # For test_result: matched by @Tag or test name in JUnit XML / Jest JSON
          # For deployment_check: matched by verification[].output file path
          # For config_validation: matched by output file + schema
          # For api_health_check: endpoint + expected status
          # For log_assertion: log pattern + required fields
          # For metric_query: NRQL query + threshold
          # For manual_gate: human approval recorded in context
```

### 4.3 Verification Types Beyond Traditional Testing

One of the key innovations is that "proof of correctness" extends beyond unit tests. The spec's verification entries can target any of these skill types:

| Skill Type | What It Proves | Output Format | Execution Method | Evaluation Method |
|-----------|---------------|---------------|-----------------|-------------------|
| `junit5_controller_test` | API behavior matches contract | Java test file | `gradle test` | Parse JUnit XML, match `@Tag` |
| `jest_unit_test` | Business logic matches contract | JS/TS test file | `npm test` | Parse Jest JSON, match describe/it names |
| `pytest_unit_test` | Python logic matches contract | Python test file | `pytest --junitxml` | Parse JUnit XML, match markers |
| `schema_contract_test` | Response shape matches schema | Contract test file | Test runner | Parse test results, match tags |
| `property_based_test` | Invariants hold for all inputs | Property test file | Test runner + fuzzer | Parse test results |
| `gherkin_scenario` | Human-readable behavior doc | .feature file | Cucumber/Behave | Parse Cucumber JSON report |
| `newrelic_alert_config` | Performance SLA is monitored | NRQL JSON config | File validation | Check file exists + valid NRQL schema |
| `otel_instrumentation` | Observability is in place | OTel config/code | File validation | Check config matches OTel schema |
| `audit_log_assertion` | Compliance logging exists | Test that asserts log output | Test runner | Parse test results |
| `data_classification_check` | PII is properly labeled | Header/metadata test | Test runner | Parse test results |
| `openapi_diff` | API spec matches implementation | OpenAPI comparison | `openapi-diff` CLI | Exit code 0 = pass |
| `security_scan_config` | Known vulnerabilities checked | Scanner config | SAST/DAST tool | Parse scanner report |
| `db_migration_check` | Schema change is backwards-compatible | Migration validation | `flyway validate` or similar | Exit code 0 = pass |
| `load_test_config` | Performance under load is acceptable | k6/Gatling script | Load test runner | Parse results against threshold |
| `accessibility_check` | UI meets WCAG standards | axe/pa11y config | Accessibility scanner | Parse violation count |
| `api_health_probe` | Deployed endpoint responds correctly | HTTP check script | `curl` or HTTP client | Status code + body match |

These verification types fall into three execution categories:

**Category 1: Test-Based Verification** — Produces a test file that runs in a test framework and emits structured results (JUnit XML, Jest JSON, Cucumber JSON). The evaluator parses the results and matches tagged test methods to spec refs. This covers: unit tests, integration tests, contract tests, property-based tests, audit log assertions, data classification checks, Gherkin scenarios.

**Category 2: Artifact-Based Verification** — Produces a configuration file or infrastructure artifact. The evaluator checks that the file exists AND validates it against a schema. The artifact itself is the proof — it proves the developer (or pipeline) has the correct monitoring/alerting/instrumentation configured. This covers: New Relic alert configs, OTel instrumentation, security scan configs, load test configs, accessibility configs.

**Category 3: Runtime Verification** — Requires executing a check against a live or deployed system. The evaluator runs the check and evaluates the result. This covers: API health probes, OpenAPI diff checks, database migration validation, deployed alert verification.

The key insight: **each category needs a different evaluation strategy**, but they all feed into the same traceability map. A passing unit test and a valid New Relic config file both check the same kind of box — "this spec element is verified."

### 4.4 The Tag Contract: How Tests Link Back to Spec Refs

The glue between generated tests and the traceability map is a **tagging convention**. Every generated test method is tagged with the spec ref it verifies. The evaluator uses these tags to match test results to spec elements.

**JUnit 5 (Java):**
```java
// Generated by: junit5_controller_test skill
// Spec: PROJ-1234.REQ-001

@Tag("PROJ-1234")
@Tag("REQ-001")
class UserProfileVerificationTest {

    @Test
    @Tag("REQ-001.success")
    @DisplayName("[REQ-001.success] Returns 200 with profile for authenticated user")
    void should_return_profile_when_authenticated() { ... }

    @Test
    @Tag("REQ-001.FAIL-001")
    @DisplayName("[REQ-001.FAIL-001] Returns 401 when no auth header")
    void should_return_401_when_no_auth_header() { ... }

    @Test
    @Tag("REQ-001.INV-001")
    @DisplayName("[REQ-001.INV-001] Response only contains authenticated user data")
    void should_never_return_other_users_data() { ... }
}
```

**Jest (TypeScript/JavaScript):**
```typescript
// Generated by: jest_unit_test skill
// Spec: PROJ-1234.REQ-001

describe('[REQ-001] User Profile Retrieval', () => {
  it('[REQ-001.success] returns 200 with profile for authenticated user', async () => { ... });
  it('[REQ-001.FAIL-001] returns 401 when no auth header', async () => { ... });
  it('[REQ-001.INV-001] response only contains authenticated user data', async () => { ... });
});
```

**Pytest (Python):**
```python
# Generated by: pytest_unit_test skill
# Spec: PROJ-1234.REQ-001

import pytest

@pytest.mark.spec("REQ-001.success")
def test_returns_profile_when_authenticated(): ...

@pytest.mark.spec("REQ-001.FAIL-001")
def test_returns_401_when_no_auth_header(): ...

@pytest.mark.spec("REQ-001.INV-001")
def test_never_returns_other_users_data(): ...
```

**Cucumber/Gherkin (.feature):**
```gherkin
# Generated by: gherkin_scenario skill
# Spec: PROJ-1234.REQ-001

@REQ-001 @REQ-001.success
Scenario: Authenticated user retrieves their profile
  Given a user "danny" exists with email "danny@example.com"
  And the user is authenticated with a valid JWT
  When the user requests GET /api/v1/users/me
  Then the response status should be 200
  And the response body should contain "email": "danny@example.com"

@REQ-001 @REQ-001.FAIL-001
Scenario: Unauthenticated request is rejected
  Given no authentication token is provided
  When a request is made to GET /api/v1/users/me
  Then the response status should be 401
```

The tag format is consistent across all frameworks: `{REQ-ID}.{element-ID}`. This is what the evaluator matches on. The skill agents generate these tags mechanically from the spec's `verification[].refs` field.

### 4.5 Traceability Map: Worked Example

Here is a complete traceability map for a ticket with 3 AC checkboxes, showing how multiple verification types feed into the same evaluation:

```yaml
traceability:
  ac_mappings:
    # ─────────────────────────────────────────────────────────
    # AC[0]: Functional correctness — requires ALL tests to pass
    # ─────────────────────────────────────────────────────────
    - ac_checkbox: 0
      ac_text: "User can view their profile"
      pass_condition: ALL_PASS
      required_verifications:
        # Happy path (from contract.success)
        - ref: "REQ-001.success"
          description: "Happy path returns correct profile data"
          verification_type: test_result

        # Error handling (from contract.failures)
        - ref: "REQ-001.FAIL-001"
          description: "Missing auth returns 401"
          verification_type: test_result
        - ref: "REQ-001.FAIL-002"
          description: "Expired JWT returns 401"
          verification_type: test_result
        - ref: "REQ-001.FAIL-003"
          description: "Malformed JWT returns 401"
          verification_type: test_result
        - ref: "REQ-001.FAIL-004"
          description: "Non-existent user returns 404"
          verification_type: test_result
        - ref: "REQ-001.FAIL-005"
          description: "Soft-deleted user returns 404"
          verification_type: test_result
        - ref: "REQ-001.FAIL-006"
          description: "Suspended account returns 403"
          verification_type: test_result
        - ref: "REQ-001.FAIL-007"
          description: "Pending verification returns 403"
          verification_type: test_result

        # Security invariants (from contract.invariants)
        - ref: "REQ-001.INV-001"
          description: "Response only contains authenticated user's data"
          verification_type: test_result
        - ref: "REQ-001.INV-002"
          description: "Forbidden fields never appear in response"
          verification_type: test_result
        - ref: "REQ-001.INV-005"
          description: "GET is idempotent — no side effects"
          verification_type: test_result

        # Schema contract (from contract.success.schema)
        - ref: "REQ-001.schema"
          description: "Response shape matches defined JSON schema"
          verification_type: test_result

    # ─────────────────────────────────────────────────────────
    # AC[1]: Performance SLA — mix of deployment + runtime checks
    # ─────────────────────────────────────────────────────────
    - ac_checkbox: 1
      ac_text: "Profile endpoint responds within 500ms p99"
      pass_condition: ALL_PASS
      required_verifications:
        # Alert configuration exists and is valid
        - ref: "REQ-001.INV-004.config"
          description: "New Relic NRQL alert config is present and valid"
          verification_type: deployment_check
          check_details:
            file: "infra/alerts/user-profile-latency.json"
            schema: "nrql_alert_schema"

        # OTel instrumentation is in place
        - ref: "REQ-001.INV-004.instrumentation"
          description: "OpenTelemetry span configured for endpoint"
          verification_type: config_validation
          check_details:
            file: "src/main/resources/otel-config.yaml"
            required_spans: ["GET /api/v1/users/me"]

        # (Stretch) Actual latency check against deployed endpoint
        # - ref: "REQ-001.INV-004.live"
        #   description: "Live p99 latency is below 500ms"
        #   verification_type: metric_query
        #   check_details:
        #     query: "SELECT percentile(duration, 99) FROM Transaction WHERE name = 'GET /api/v1/users/me'"
        #     threshold_ms: 500
        #     provider: new_relic

    # ─────────────────────────────────────────────────────────
    # AC[2]: Security invariant — shares tests with AC[0]
    # ─────────────────────────────────────────────────────────
    - ac_checkbox: 2
      ac_text: "Profile data is never exposed to other users"
      pass_condition: ALL_PASS
      required_verifications:
        # These refs appear in BOTH ac_checkbox 0 AND 2
        # The same test result satisfies both mappings
        - ref: "REQ-001.INV-001"
          description: "Response only contains authenticated user's data"
          verification_type: test_result
        - ref: "REQ-001.INV-002"
          description: "Forbidden fields never appear in response"
          verification_type: test_result
        - ref: "REQ-001.INV-003"
          description: "No stack traces or internal details in error responses"
          verification_type: test_result
        - ref: "REQ-001.INV-006"
          description: "All profile access is audit-logged"
          verification_type: test_result
        - ref: "REQ-001.INV-007"
          description: "PII data classification header present"
          verification_type: test_result
```

Notice the key patterns:
- **AC[0]** is pure `test_result` — all verifications come from test runner output
- **AC[1]** mixes `deployment_check` and `config_validation` — "correctness" here means the monitoring infrastructure exists, not that code passes a test
- **AC[2]** shares refs with AC[0] — the same INV-001 test result satisfies both checkboxes
- The commented-out `metric_query` on AC[1] shows how you'd extend to live runtime verification in production

---

## 5. The Evaluation Engine

### 5.1 Purpose

The evaluation engine is a 100% deterministic script (zero AI) that reads three inputs and produces one output:

```
Inputs:
  1. The spec YAML (specifically traceability.ac_mappings)
  2. Test execution results (JUnit XML, Jest JSON, Cucumber JSON, pytest XML)
  3. Non-test verification checks (file existence, schema validation, runtime probes)

Output:
  A list of verdicts: { ac_checkbox, passed, evidence[] }
```

### 5.2 Evaluation Logic

```python
# evaluator.py — 100% deterministic, zero AI

import xml.etree.ElementTree as ET
import yaml, json, os

def evaluate_spec(spec_path: str, test_results_paths: list[str]) -> list[dict]:
    """
    Master evaluation function.
    Reads the spec's traceability map and all verification results.
    Returns a verdict for each AC checkbox.
    """
    spec = yaml.safe_load(open(spec_path))
    test_results = merge_test_results(test_results_paths)
    
    verdicts = []
    
    for mapping in spec["traceability"]["ac_mappings"]:
        checkbox_results = []
        
        for req_ver in mapping["required_verifications"]:
            ref = req_ver["ref"]
            ver_type = req_ver["verification_type"]
            
            # Route to the correct evaluation strategy
            result = EVALUATION_STRATEGIES[ver_type](
                ref=ref,
                spec=spec,
                test_results=test_results,
                check_details=req_ver.get("check_details", {})
            )
            
            checkbox_results.append({
                "ref": ref,
                "description": req_ver["description"],
                "verification_type": ver_type,
                "passed": result["passed"],
                "details": result.get("details", "")
            })
        
        # Evaluate pass condition
        verdict = evaluate_pass_condition(
            condition=mapping["pass_condition"],
            results=checkbox_results,
            threshold=mapping.get("threshold")
        )
        
        verdicts.append({
            "ac_checkbox": mapping["ac_checkbox"],
            "ac_text": mapping["ac_text"],
            "passed": verdict,
            "pass_condition": mapping["pass_condition"],
            "evidence": checkbox_results,
            "summary": (
                f"{sum(1 for r in checkbox_results if r['passed'])}"
                f"/{len(checkbox_results)} verifications passed"
            )
        })
    
    return verdicts


# ── Evaluation strategies per verification type ──

EVALUATION_STRATEGIES = {}

def strategy(ver_type):
    """Decorator to register evaluation strategies."""
    def decorator(fn):
        EVALUATION_STRATEGIES[ver_type] = fn
        return fn
    return decorator

@strategy("test_result")
def eval_test_result(ref, spec, test_results, check_details):
    """
    Match a spec ref to a tagged test in JUnit XML / Jest JSON / pytest XML.
    The ref (e.g., "REQ-001.FAIL-002") must appear in the test's tags, 
    name, or @DisplayName.
    """
    for test_case in test_results.get("test_cases", []):
        tags = test_case.get("tags", [])
        name = test_case.get("name", "")
        display_name = test_case.get("display_name", "")
        
        if ref in tags or ref in name or ref in display_name:
            passed = test_case["status"] == "passed"
            return {
                "passed": passed,
                "details": (
                    f"Test '{test_case['name']}' {test_case['status']}"
                    + (f": {test_case.get('failure_message', '')}" if not passed else "")
                )
            }
    
    # No matching test found — this is a failure
    return {
        "passed": False,
        "details": f"No test found with tag or name matching '{ref}'"
    }

@strategy("deployment_check")
def eval_deployment_check(ref, spec, test_results, check_details):
    """
    Verify that a generated artifact file exists and is structurally valid.
    Used for: New Relic alerts, OTel configs, security scanner configs.
    """
    file_path = check_details.get("file", "")
    schema_name = check_details.get("schema")
    
    if not os.path.exists(file_path):
        return {
            "passed": False,
            "details": f"Expected file not found: {file_path}"
        }
    
    # Validate file is parseable
    try:
        with open(file_path) as f:
            if file_path.endswith(".json"):
                content = json.load(f)
            elif file_path.endswith((".yaml", ".yml")):
                content = yaml.safe_load(f)
            else:
                content = f.read()
    except Exception as e:
        return {
            "passed": False,
            "details": f"File exists but is not parseable: {e}"
        }
    
    # Optional schema validation
    if schema_name:
        schema_valid = validate_against_schema(content, schema_name)
        if not schema_valid["passed"]:
            return schema_valid
    
    return {
        "passed": True,
        "details": f"File exists and is valid: {file_path}"
    }

@strategy("config_validation")
def eval_config_validation(ref, spec, test_results, check_details):
    """
    Validate that a configuration file contains required entries.
    Used for: OTel span configs, feature flag configs, logging configs.
    """
    file_path = check_details.get("file", "")
    required_entries = check_details.get("required_spans", 
                       check_details.get("required_entries", []))
    
    if not os.path.exists(file_path):
        return {
            "passed": False,
            "details": f"Config file not found: {file_path}"
        }
    
    try:
        with open(file_path) as f:
            content = yaml.safe_load(f) if file_path.endswith((".yaml", ".yml")) else json.load(f)
    except Exception as e:
        return {"passed": False, "details": f"Config not parseable: {e}"}
    
    # Check for required entries in the config
    content_str = json.dumps(content)
    missing = [entry for entry in required_entries if entry not in content_str]
    
    if missing:
        return {
            "passed": False,
            "details": f"Config missing required entries: {missing}"
        }
    
    return {
        "passed": True,
        "details": f"Config valid with all {len(required_entries)} required entries"
    }

@strategy("api_health_check")
def eval_api_health_check(ref, spec, test_results, check_details):
    """
    Make an HTTP request to a deployed endpoint and verify the response.
    Used for: post-deployment smoke tests, live endpoint verification.
    """
    import requests
    
    url = check_details.get("url", "")
    expected_status = check_details.get("expected_status", 200)
    timeout_ms = check_details.get("timeout_ms", 5000)
    
    try:
        response = requests.get(url, timeout=timeout_ms / 1000)
        passed = response.status_code == expected_status
        return {
            "passed": passed,
            "details": f"GET {url} returned {response.status_code} (expected {expected_status})"
        }
    except Exception as e:
        return {"passed": False, "details": f"Health check failed: {e}"}

@strategy("log_assertion")
def eval_log_assertion(ref, spec, test_results, check_details):
    """
    Check that application logs contain required structured entries.
    Used for: audit trail verification, compliance logging.
    """
    log_file = check_details.get("log_file", "")
    required_fields = check_details.get("required_fields", [])
    
    if not os.path.exists(log_file):
        return {"passed": False, "details": f"Log file not found: {log_file}"}
    
    with open(log_file) as f:
        log_content = f.read()
    
    missing = [field for field in required_fields if field not in log_content]
    
    return {
        "passed": len(missing) == 0,
        "details": f"Missing log fields: {missing}" if missing 
                   else f"All {len(required_fields)} required fields present in logs"
    }

@strategy("metric_query")
def eval_metric_query(ref, spec, test_results, check_details):
    """
    Query an APM provider for a metric and compare against threshold.
    Used for: live performance SLA verification, error rate checks.
    """
    provider = check_details.get("provider", "new_relic")
    query = check_details.get("query", "")
    threshold = check_details.get("threshold_ms") or check_details.get("threshold")
    
    # In production, this would call the New Relic / Datadog / Prometheus API
    # For hackathon, mock this
    return {
        "passed": False,
        "details": f"Metric query evaluation not implemented for {provider} (stretch goal)"
    }

@strategy("manual_gate")
def eval_manual_gate(ref, spec, test_results, check_details):
    """
    Check if a human has approved this verification in the context.
    Used for: UX review, accessibility review, security sign-off.
    """
    approvals = check_details.get("approvals", {})
    return {
        "passed": ref in approvals and approvals[ref] == "approved",
        "details": f"Manual gate {'approved' if ref in approvals else 'pending'}"
    }


# ── Pass condition evaluators ──

def evaluate_pass_condition(condition, results, threshold=None):
    """Evaluate whether the AC checkbox should be ticked."""
    if condition == "ALL_PASS":
        return all(r["passed"] for r in results)
    elif condition == "ANY_PASS":
        return any(r["passed"] for r in results)
    elif condition == "PERCENTAGE":
        if not results:
            return False
        pass_rate = sum(1 for r in results if r["passed"]) / len(results) * 100
        return pass_rate >= (threshold or 100)
    return False


# ── Test result parsers ──

def merge_test_results(paths: list[str]) -> dict:
    """
    Parse and merge test results from multiple formats into a unified structure.
    Supports: JUnit XML, Jest JSON, Cucumber JSON, pytest XML.
    """
    all_cases = []
    
    for path in paths:
        if path.endswith(".xml"):
            all_cases.extend(parse_junit_xml(path))
        elif path.endswith(".json"):
            content = json.load(open(path))
            if "testResults" in content:
                all_cases.extend(parse_jest_json(content))
            elif isinstance(content, list) and content and "elements" in content[0]:
                all_cases.extend(parse_cucumber_json(content))
    
    return {"test_cases": all_cases}

def parse_junit_xml(path: str) -> list[dict]:
    """
    Parse JUnit XML (used by JUnit 5, pytest, Gradle).
    Extracts test name, status, tags from @Tag annotations.
    
    JUnit XML stores @Tag values in <properties> or in the test name.
    """
    tree = ET.parse(path)
    cases = []
    
    for testcase in tree.iter("testcase"):
        name = testcase.get("name", "")
        classname = testcase.get("classname", "")
        
        # Extract tags from properties (JUnit 5 with tag reporting enabled)
        tags = []
        for prop in testcase.iter("property"):
            if prop.get("name") == "tag":
                tags.append(prop.get("value", ""))
        
        # Also extract ref from @DisplayName pattern: [REQ-001.FAIL-002]
        import re
        display_match = re.search(r'\[([A-Z]+-\d+\.\S+)\]', name)
        if display_match:
            tags.append(display_match.group(1))
        
        # Determine status
        failure = testcase.find("failure")
        error = testcase.find("error")
        skipped = testcase.find("skipped")
        
        if failure is not None:
            status = "failed"
            failure_msg = failure.get("message", "")
        elif error is not None:
            status = "errored"
            failure_msg = error.get("message", "")
        elif skipped is not None:
            status = "skipped"
            failure_msg = ""
        else:
            status = "passed"
            failure_msg = ""
        
        cases.append({
            "name": name,
            "classname": classname,
            "display_name": name,
            "tags": tags,
            "status": status,
            "failure_message": failure_msg
        })
    
    return cases

def parse_jest_json(content: dict) -> list[dict]:
    """
    Parse Jest JSON output (--json flag).
    Extracts test names which contain refs in brackets.
    """
    cases = []
    import re
    
    for suite in content.get("testResults", []):
        for test in suite.get("assertionResults", []):
            name = test.get("fullName", "") or test.get("title", "")
            
            # Extract ref from name pattern: [REQ-001.FAIL-002]
            tags = []
            for match in re.finditer(r'\[([A-Z]+-\d+\.\S+)\]', name):
                tags.append(match.group(1))
            
            # Also check ancestorTitles for describe-level refs
            for ancestor in test.get("ancestorTitles", []):
                for match in re.finditer(r'\[([A-Z]+-\d+(?:\.\S+)?)\]', ancestor):
                    tags.append(match.group(1))
            
            cases.append({
                "name": name,
                "display_name": name,
                "tags": tags,
                "status": test.get("status", "failed"),
                "failure_message": "\n".join(test.get("failureMessages", []))
            })
    
    return cases

def parse_cucumber_json(content: list) -> list[dict]:
    """
    Parse Cucumber JSON report.
    Extracts tags from @REQ-001.FAIL-002 scenario tags.
    """
    cases = []
    
    for feature in content:
        for element in feature.get("elements", []):
            if element.get("type") != "scenario":
                continue
            
            name = element.get("name", "")
            tags = [t.get("name", "").lstrip("@") for t in element.get("tags", [])]
            
            # A scenario passes only if ALL steps pass
            steps = element.get("steps", [])
            all_passed = all(
                s.get("result", {}).get("status") == "passed" 
                for s in steps
            )
            
            cases.append({
                "name": name,
                "display_name": name,
                "tags": tags,
                "status": "passed" if all_passed else "failed",
                "failure_message": ""
            })
    
    return cases
```

### 5.3 The Complete Traceability Chain

This diagram shows every ID linkage from Jira AC to checkbox update, across all verification types:

```
Jira Ticket: PROJ-1234
│
├── AC Checkbox [0]: "User can view their profile"
│   │
│   └── traceability.ac_mappings[0]
│       │   pass_condition: ALL_PASS
│       │   required_verifications: 12 entries (all test_result type)
│       │
│       ├── Requirement REQ-001, verification[0]
│       │   skill: junit5_controller_test
│       │   output: UserProfileVerificationTest.java
│       │   │
│       │   └── Generated tests:
│       │       ├── @Tag("REQ-001.success")      → test_happy_path
│       │       ├── @Tag("REQ-001.FAIL-001")     → test_no_auth
│       │       ├── @Tag("REQ-001.FAIL-002")     → test_expired_jwt
│       │       ├── @Tag("REQ-001.INV-001")      → test_no_data_leakage
│       │       └── @Tag("REQ-001.INV-002")      → test_no_sensitive_fields
│       │
│       └── Requirement REQ-001, verification[1]
│           skill: schema_contract_test
│           output: UserProfileContractTest.java
│           │
│           └── Generated tests:
│               └── @Tag("REQ-001.schema")       → test_response_schema
│
│       Execution: gradle test → JUnit XML
│       Evaluator: parse XML, match @Tag to each ref
│       Result: 12/12 passed
│       ▸ Jira API: tick checkbox [0] ✅
│
├── AC Checkbox [1]: "Profile endpoint responds within 500ms p99"
│   │
│   └── traceability.ac_mappings[1]
│       │   pass_condition: ALL_PASS
│       │   required_verifications: 2 entries (mixed types)
│       │
│       ├── ref: "REQ-001.INV-004.config"
│       │   verification_type: deployment_check
│       │   │
│       │   └── Evaluator: 
│       │       Does infra/alerts/user-profile-latency.json exist?
│       │       Is it valid JSON matching NRQL alert schema?
│       │       → YES ✅
│       │
│       └── ref: "REQ-001.INV-004.instrumentation"
│           verification_type: config_validation
│           │
│           └── Evaluator:
│               Does otel-config.yaml exist?
│               Does it contain span for "GET /api/v1/users/me"?
│               → YES ✅
│
│       Result: 2/2 passed
│       ▸ Jira API: tick checkbox [1] ✅
│
├── AC Checkbox [2]: "Profile data is never exposed to other users"
│   │
│   └── traceability.ac_mappings[2]
│       │   pass_condition: ALL_PASS
│       │   required_verifications: 5 entries (all test_result type)
│       │
│       └── refs: INV-001, INV-002, INV-003, INV-006, INV-007
│           These are the SAME test results already evaluated for AC[0]
│           Evaluator reuses the parsed JUnit XML — no re-execution
│           │
│           Result: 5/5 passed
│           ▸ Jira API: tick checkbox [2] ✅
│
└── ALL checkboxes passed
    ▸ Jira API: transition ticket to "Done"
    ▸ Jira API: add evidence comment with full breakdown
```

---

## 6. The Jira Updater

### 6.1 Purpose

The Jira updater is a 100% deterministic script that takes the evaluator's verdicts and translates them into Jira API calls. Zero AI involvement.

### 6.2 Implementation

```python
# jira_updater.py — 100% deterministic, zero AI

import requests

JIRA_BASE = "https://your-org.atlassian.net"
JIRA_AUTH = ("api-user", "api-token")

def update_jira_from_verdicts(jira_key: str, verdicts: list[dict], spec_path: str):
    """
    For each AC checkbox verdict, update the Jira ticket:
    1. Tick the checkbox if passed
    2. Add an evidence comment
    3. Transition the ticket if all checkboxes pass
    """
    
    # Step 1: Update individual AC checkboxes
    for verdict in verdicts:
        if verdict["passed"]:
            tick_ac_checkbox(jira_key, verdict["ac_checkbox"])
    
    # Step 2: Add evidence comment (always, even on failure)
    comment = format_evidence_comment(jira_key, verdicts, spec_path)
    add_jira_comment(jira_key, comment)
    
    # Step 3: Transition ticket if ALL checkboxes pass
    if all(v["passed"] for v in verdicts):
        transition_ticket(jira_key, target_status="Done")
    else:
        # Move to "In Review" or "Blocked" if partial pass
        failed_count = sum(1 for v in verdicts if not v["passed"])
        if failed_count < len(verdicts):
            transition_ticket(jira_key, target_status="In Review")


def format_evidence_comment(jira_key: str, verdicts: list[dict], spec_path: str) -> str:
    """
    Generate a structured Jira comment that serves as the audit trail.
    Uses Jira wiki markup for formatting.
    """
    lines = [
        "h3. Verification Pipeline Results",
        f"Spec: {{code}}{spec_path}{{code}}",
        ""
    ]
    
    all_passed = all(v["passed"] for v in verdicts)
    lines.append(f"*Overall: {'(/) ALL PASSED' if all_passed else '(x) FAILURES DETECTED'}*")
    lines.append("")
    
    for verdict in verdicts:
        icon = "(/)" if verdict["passed"] else "(x)"
        lines.append(f"h4. {icon} AC: \"{verdict['ac_text']}\"")
        lines.append(f"Condition: {verdict['pass_condition']} | Result: {verdict['summary']}")
        lines.append("")
        lines.append("||Ref||Description||Type||Result||")
        
        for ev in verdict["evidence"]:
            status = "(/)" if ev["passed"] else "(x)"
            lines.append(
                f"|{ev['ref']}|{ev['description']}"
                f"|{ev['verification_type']}|{status}|"
            )
        
        lines.append("")
    
    lines.extend([
        "----",
        f"_Generated by Intent-to-Verification Pipeline_",
        f"_Traceability: Every result maps to a spec ref, "
        f"every spec ref maps to an AC checkbox, "
        f"every AC checkbox maps to business intent._"
    ])
    
    return "\n".join(lines)


def tick_ac_checkbox(jira_key: str, checkbox_index: int):
    """
    Update a specific AC checkbox on the Jira ticket.
    
    NOTE: Jira's AC checkbox implementation varies:
    - Jira Cloud with checklist plugin: use checklist API
    - Jira Cloud native: update description field with checked markdown
    - Jira Server: depends on custom fields
    
    This implementation assumes the AC is in the description as 
    markdown checkboxes: [ ] unchecked, [x] checked
    """
    # Fetch current description
    response = requests.get(
        f"{JIRA_BASE}/rest/api/3/issue/{jira_key}",
        auth=JIRA_AUTH
    )
    issue = response.json()
    description = issue["fields"]["description"]
    
    # Parse and update the specific checkbox
    # Jira Cloud uses Atlassian Document Format (ADF), not markdown
    # For hackathon: simplify by using description text with regex
    updated_description = check_nth_checkbox(description, checkbox_index)
    
    # Push update
    requests.put(
        f"{JIRA_BASE}/rest/api/3/issue/{jira_key}",
        auth=JIRA_AUTH,
        json={"fields": {"description": updated_description}}
    )
```

### 6.3 The Evidence Comment in Jira

When the pipeline completes, this is what appears on the Jira ticket:

```
╔══════════════════════════════════════════════════════╗
║  Verification Pipeline Results                        ║
║  Spec: .verify/specs/PROJ-1234.yaml                  ║
║                                                       ║
║  Overall: ✅ ALL PASSED                               ║
╠══════════════════════════════════════════════════════╣
║                                                       ║
║  ✅ AC: "User can view their profile"                ║
║  Condition: ALL_PASS | Result: 12/12 passed          ║
║                                                       ║
║  Ref              │ Description              │ Type   ║
║  REQ-001.success  │ Happy path returns 200   │ test ✅║
║  REQ-001.FAIL-001 │ No auth returns 401      │ test ✅║
║  REQ-001.FAIL-002 │ Expired JWT returns 401  │ test ✅║
║  REQ-001.FAIL-003 │ Malformed JWT returns 401│ test ✅║
║  REQ-001.FAIL-004 │ No user returns 404      │ test ✅║
║  REQ-001.FAIL-005 │ Deleted user returns 404 │ test ✅║
║  REQ-001.FAIL-006 │ Suspended returns 403    │ test ✅║
║  REQ-001.FAIL-007 │ Pending returns 403      │ test ✅║
║  REQ-001.INV-001  │ No data leakage          │ test ✅║
║  REQ-001.INV-002  │ No sensitive fields       │ test ✅║
║  REQ-001.INV-005  │ GET is idempotent        │ test ✅║
║  REQ-001.schema   │ Response matches schema  │ test ✅║
║                                                       ║
║  ✅ AC: "Profile endpoint responds within 500ms p99" ║
║  Condition: ALL_PASS | Result: 2/2 passed            ║
║                                                       ║
║  Ref                        │ Description      │ Type ║
║  REQ-001.INV-004.config     │ NR alert valid   │ file✅║
║  REQ-001.INV-004.instrument │ OTel span exists │ cfg ✅║
║                                                       ║
║  ✅ AC: "Profile data never exposed to other users"  ║
║  Condition: ALL_PASS | Result: 5/5 passed            ║
║                                                       ║
║  Ref             │ Description              │ Type    ║
║  REQ-001.INV-001 │ No cross-user leakage    │ test ✅ ║
║  REQ-001.INV-002 │ No sensitive fields       │ test ✅ ║
║  REQ-001.INV-003 │ No stack traces           │ test ✅ ║
║  REQ-001.INV-006 │ Audit logging present    │ test ✅ ║
║  REQ-001.INV-007 │ PII classification header│ test ✅ ║
║                                                       ║
║  ─────────────────────────────────────────────────    ║
║  Generated by Intent-to-Verification Pipeline         ║
║  Traceability: result → spec ref → AC → business intent║
╚══════════════════════════════════════════════════════╝
```

This comment IS the audit trail. When someone asks "how do we know this ticket was properly verified?", the answer is on the ticket itself, with every link in the chain visible.

---

## 7. The Belief Object (Pipeline Context)

### 7.1 Purpose

The VerificationContext is the single object that flows through the entire pipeline, accumulating state. It's the "belief" in Sherpa terminology — the agent's understanding of what's happened so far. It's also the traceability artifact — at the end, it contains the complete provenance chain from AC to test results.

### 7.2 Schema

```python
@dataclass
class VerificationContext:
    """The belief object that flows through the entire pipeline."""
    
    # Identifiers
    jira_key: str
    jira_summary: str
    
    # Inputs
    raw_acceptance_criteria: list[dict]  # From Jira, with checkbox indices
    constitution: dict                    # From .verify/constitution.yaml
    
    # Negotiation state
    current_phase: str                    # Which negotiation phase we're in
    negotiation_log: list[dict]           # Full conversation history
    # Each entry: { phase, role (ai/human), content, timestamp }
    
    # Accumulated spec (built incrementally across phases)
    classifications: list[dict]           # Phase 1 output
    postconditions: list[dict]            # Phase 2 output
    preconditions: list[dict]             # Phase 3 output
    failure_modes: list[dict]             # Phase 4 output
    invariants: list[dict]               # Phase 5 output
    completeness_gaps: list[dict]         # Phase 6 output
    verification_routing: list[dict]      # Phase 6 output
    ears_statements: list[str]            # Phase 7 output
    traceability_map: dict               # Phase 7 output — the ac_mappings
    
    # Approval
    approved: bool
    approved_by: str
    approved_at: str
    
    # Post-spec (filled by downstream pipeline)
    spec_path: str                        # Where the YAML was written
    generated_files: dict[str, str]       # filepath → content (or hash)
    
    # Evaluation results (filled by evaluator)
    test_result_paths: list[str]          # Paths to JUnit XML / Jest JSON / etc.
    verdicts: list[dict]                  # Evaluator output per AC checkbox
    all_passed: bool                      # Overall pass/fail
    
    # Jira update results (filled by jira_updater)
    jira_updates_applied: list[dict]      # What was updated and when
    jira_comment_id: str                  # ID of the evidence comment
    jira_transition_applied: str          # Final ticket status
    
    def emit_spec_yaml(self) -> str:
        """Compile all accumulated state into the final YAML spec."""
        ...
    
    def traceability_report(self) -> dict:
        """Generate the complete provenance chain for audit."""
        return {
            "pipeline_run": {
                "jira_key": self.jira_key,
                "timestamp": self.approved_at,
                "approved_by": self.approved_by,
            },
            "input": {
                "ac_count": len(self.raw_acceptance_criteria),
                "ac_items": [ac["text"] for ac in self.raw_acceptance_criteria],
            },
            "negotiation": {
                "phases_completed": len(set(e["phase"] for e in self.negotiation_log)),
                "total_exchanges": len(self.negotiation_log),
                "log_path": f".verify/logs/{self.jira_key}-negotiation.md",
            },
            "spec": {
                "path": self.spec_path,
                "requirements_count": len(self.postconditions),
                "failure_modes_count": len(self.failure_modes),
                "invariants_count": len(self.invariants),
            },
            "verification": {
                "files_generated": list(self.generated_files.keys()),
                "verification_types": list(set(
                    v["verification_type"] 
                    for m in self.traceability_map.get("ac_mappings", [])
                    for v in m.get("required_verifications", [])
                )),
            },
            "results": {
                "verdicts": self.verdicts,
                "all_passed": self.all_passed,
                "checkboxes_ticked": [
                    v["ac_checkbox"] for v in self.verdicts if v["passed"]
                ],
            },
            "jira": {
                "updates_applied": self.jira_updates_applied,
                "comment_id": self.jira_comment_id,
                "final_status": self.jira_transition_applied,
            }
        }
```

---

## 8. Hackathon Scoping

### 8.1 What to Build for the Demo

| Component | Priority | Notes |
|-----------|----------|-------|
| **Init & Constitution** | | |
| Constitution (hardcoded) | MVP | Pre-write for dummy app, don't build the scanner |
| **Negotiation Phases** | | |
| Phase 0 (Jira ingestion) | MVP | Real Jira API calls — this is the "Plumber" role |
| Phase 1 (Interface discovery) | MVP | Single prompt, show classification |
| Phase 2 (Happy path) | MVP | Single prompt, show schema proposal |
| Phase 3 (Preconditions) | MVP | Can combine with Phase 4 for demo |
| Phase 4 (Failure modes) | MVP | This is the "wow" moment — show edge case discovery |
| Phase 5 (Invariants) | STRETCH | Hardcode 2-3 invariants from constitution |
| Phase 6 (Completeness) | STRETCH | Show the checklist sweep if time permits |
| Phase 7 (EARS + approval) | MVP | Show the final EARS summary, get approval |
| **Spec Emission** | | |
| Spec YAML emission | MVP | Emit the file, show it in the repo |
| Traceability map in spec | MVP | The ac_mappings block linking refs to checkboxes |
| Verification routing in spec | MVP | Show the routing table, dispatch to skills |
| **Verification Skills** | | |
| JUnit skill (test generation) | MVP | Generate one test file with @Tag annotations |
| New Relic alert skill | STRETCH | Generate one alert config JSON from INV-004 |
| Gherkin skill | STRETCH | Generate .feature file from EARS statements |
| OTel config skill | STRETCH | Generate span config for latency monitoring |
| **Evaluation & Jira** | | |
| JUnit XML parser | MVP | Parse test results, match @Tag to spec refs |
| Deployment check evaluator | STRETCH | Validate generated config files exist/are valid |
| Pass condition evaluator | MVP | ALL_PASS logic for each AC checkbox |
| Jira checkbox updater | MVP | Tick checkboxes via Jira REST API |
| Jira evidence comment | MVP | Post the full evidence breakdown to the ticket |
| Jira ticket transition | MVP | Move to "Done" when all checkboxes pass |

### 8.2 The 5-Minute Demo Flow

1. **(30s)** Show the Jira ticket with 3 AC checkboxes. Show the gap — "developers hate this manual process."
2. **(60s)** Run the tool. Show the AI reading the AC, classifying requirements, asking smart questions about edge cases (Phase 1-4 highlights).
3. **(30s)** Show the AI surface a security insight the PO missed (FAIL-004/FAIL-005 distinction — information disclosure via 404 vs 410).
4. **(30s)** Show the EARS summary. Developer approves.
5. **(30s)** Show the emitted spec YAML in the repo. Point out the traceability map: "Every line traces back to an AC checkbox."
6. **(30s)** Show the routing: "The spec says this needs a JUnit test AND a New Relic alert. The router dispatches to two different skills." Emphasize that this is deterministic — zero AI in routing.
7. **(30s)** Show the generated test file. Point out the @Tag annotations: "Every test method is tagged with a spec ref. This is how we trace from test results back to AC checkboxes."
8. **(30s)** Run the tests. They pass. Show the evaluator output: "12/12 test verifications passed for AC[0], 2/2 deployment checks passed for AC[1], 5/5 invariant tests passed for AC[2]."
9. **(30s)** Tab to Jira. Refresh. Checkboxes are ticked. Show the evidence comment with the full breakdown. Mic drop: "Mathematically provable traceability from business intent to verified code, across multiple verification domains."

### 8.3 Key Talking Points for Judges

- "We didn't just generate tests — we generated a *formal specification* that defines correctness. The tests are a mechanical translation of the spec."
- "The AI found a security vulnerability — information disclosure via HTTP status codes — that the PO never wrote in the acceptance criteria."
- "Everything downstream of the spec is deterministic. Zero AI hallucination in the workflow layer."
- "This isn't just for unit tests. The same spec generated a New Relic alert config AND a unit test suite. Correctness isn't limited to code — it's any verifiable business assertion."
- "The traceability map is a many-to-many relationship. One test can satisfy multiple AC checkboxes. One AC checkbox can require multiple verification types. The evaluator handles both."
- "Every commit traces to a test, every test traces to a spec ref, every spec ref traces to an AC checkbox. The evidence is posted directly to Jira. That's the 2026 AOP mandate — done."
- "The Jira ticket now has a complete audit trail: which tests ran, what they covered, which spec elements they verify, and which AC checkboxes they satisfy. This is what 'trust AI agents' looks like."
