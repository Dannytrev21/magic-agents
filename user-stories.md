# Intent-to-Verification Spec Engine: User Stories

## How This Document Is Organized

Stories are grouped into **Epics** that represent progressive layers of capability. Epic 0 is the **Bullet Tracer** — the thinnest possible end-to-end thread that proves the concept works from Jira AC to Jira checkbox ticked. Each subsequent epic adds depth to a specific layer without breaking what came before.

The principle: **always be demo-able**. After every epic, you have a working end-to-end pipeline that does more than it did before.

```
Epic 0: Bullet Tracer (hardcoded everything, one AC, one test, one checkbox)
Epic 1: Real Jira Integration (live API replaces hardcoded Jira data)
Epic 2: AI Negotiation — Core Loop (Phases 1-4, the "intelligence" layer)
Epic 3: Formal Spec Emission (YAML spec with traceability map)
Epic 4: Multi-Skill Routing & Generation (multiple verification types)
Epic 5: Evaluation Engine (parse results, map to AC checkboxes)
Epic 6: Jira Feedback Loop (tick checkboxes, post evidence, transition ticket)
Epic 7: Constitution & Repo Awareness (init phase, pattern detection)
Epic 8: Advanced Negotiation (Phases 5-7, invariants, completeness, EARS)
Epic 9: Beyond-Code Verification (alert configs, OTel, compliance checks)
Epic 10: CI/CD & PR Automation (GitHub Actions, automated PRs)
```

### Story Format

Each story follows this template:
- **As a** [role] **I want** [capability] **so that** [value]
- **Acceptance Criteria** — checkboxes defining "done"
- **Tech Notes** — implementation guidance referencing the plan
- **Dependencies** — which stories must be complete first
- **Demo Impact** — what this adds to the 5-minute presentation

---

## Epic 0: Bullet Tracer

**Goal:** Prove the end-to-end concept works with a single thread. Everything is hardcoded or mocked except the connection between components. This is the skeleton that all future epics flesh out.

**After this epic:** You can run a script that reads a hardcoded AC, emits a hardcoded spec YAML, generates a single test file, runs it, and prints "AC checkbox 0: PASSED."

---

### Story 0.1: Dummy Application

**As a** hackathon developer
**I want** a simple, pre-written application with one testable endpoint
**so that** I have a target for the generated verification tests to run against.

**Acceptance Criteria:**
- [ ] A minimal application exists with a single GET endpoint (e.g., `GET /api/v1/users/me`)
- [ ] The endpoint returns a hardcoded JSON response with known fields (id, email, displayName)
- [ ] The endpoint returns 401 when no auth header is present
- [ ] The application can be started locally with a single command
- [ ] The application's test framework is configured and `gradle test` / `npm test` / `pytest` runs successfully with zero tests

**Tech Notes:** Use whatever language the team is fastest in. Spring Boot with a single `@RestController` is fine. Express.js with one route is also fine. The app only needs to satisfy the tests that will be generated — keep it trivially simple.

**Dependencies:** None — this is the foundation.

**Demo Impact:** Not shown directly, but everything breaks without it.

---

### Story 0.2: Hardcoded Spec YAML

**As a** hackathon developer
**I want** a manually-written spec YAML file for the dummy app's endpoint
**so that** downstream stories have a concrete spec to consume without waiting for the AI negotiation to be built.

**Acceptance Criteria:**
- [ ] A file exists at `.verify/specs/DEMO-001.yaml` following the spec schema from the plan
- [ ] The spec contains one requirement block (REQ-001) with: one success postcondition, two failure modes (no auth → 401, user not found → 404), and one invariant (no sensitive field exposure)
- [ ] The spec contains a `verification` block routing to a single skill (e.g., `junit5_controller_test` or `jest_unit_test`)
- [ ] The spec contains a `traceability.ac_mappings` block mapping all refs to `ac_checkbox: 0` with `pass_condition: ALL_PASS`
- [ ] The YAML is valid and parseable by Python's `yaml.safe_load` or equivalent

**Tech Notes:** Write this by hand. Copy the schema from Plan Section 4.2 and fill in concrete values for the dummy app. This file IS the contract that proves the format works.

**Dependencies:** Story 0.1 (need to know the endpoint shape to write the spec)

**Demo Impact:** This is what you show when you say "here's the formal specification." Even if the AI negotiation isn't built yet, the spec format is the innovation.

---

### Story 0.3: Single Test Generator Skill (Hardcoded)

**As a** hackathon developer
**I want** a script that reads the spec YAML and generates a single test file with tagged test methods
**so that** I can prove that specs can be mechanically translated into executable tests.

**Acceptance Criteria:**
- [ ] A script reads `.verify/specs/DEMO-001.yaml`
- [ ] The script generates a test file at the path specified in the spec's `verification[].output`
- [ ] Each generated test method is tagged with its spec ref (e.g., `@Tag("REQ-001.success")` for JUnit, or `[REQ-001.success]` in the test name for Jest)
- [ ] The generated test file has at least: one happy path test, one 401 test, one 404 test, one invariant test (forbidden fields)
- [ ] The generated tests actually pass when run against the dummy app from Story 0.1

**Tech Notes:** For the bullet tracer, this can be a template-based script — read the spec YAML, fill in a test file template with the values. No AI needed for this step. The point is proving that the spec format contains enough information for mechanical translation.

**Dependencies:** Story 0.1, Story 0.2

**Demo Impact:** "The spec generated this test file. Every test method is tagged with a spec ref. The code exists solely to make these tests pass."

---

### Story 0.4: Test Runner + Result Parser

**As a** hackathon developer
**I want** a script that executes the generated tests and parses the results into a structured format
**so that** I can programmatically determine which spec refs passed and which failed.

**Acceptance Criteria:**
- [ ] A script runs the test suite (e.g., `gradle test`, `npm test`, `pytest --junitxml=results.xml`)
- [ ] The script parses the test output (JUnit XML or Jest JSON) into a unified structure: `[{ name, tags, status, failure_message }]`
- [ ] Tags/refs are correctly extracted from the test results (matching the `@Tag` or `[REQ-001.xxx]` naming)
- [ ] The script outputs a JSON file with the parsed results

**Tech Notes:** JUnit XML is the universal format — even Jest and pytest can emit it. Start with one parser. The unified structure must include the `tags` field so the evaluator can match refs.

**Dependencies:** Story 0.3 (need generated tests to run)

**Demo Impact:** Not shown directly, but this is the bridge between "tests passed" and "Jira checkboxes ticked."

---

### Story 0.5: Evaluator — Spec Refs to AC Checkbox Verdicts

**As a** hackathon developer
**I want** a script that reads the spec's traceability map and the parsed test results, and produces a verdict for each AC checkbox
**so that** I can deterministically answer "is this AC satisfied?" based on test results.

**Acceptance Criteria:**
- [ ] The evaluator reads `traceability.ac_mappings` from the spec YAML
- [ ] For each `ac_checkbox`, it looks up every `required_verification.ref` in the parsed test results
- [ ] A ref is "passed" if a test with a matching tag has status "passed"
- [ ] A ref is "failed" if no matching test exists OR the matching test failed
- [ ] The `pass_condition` (ALL_PASS) is evaluated: checkbox passes only if every required ref passed
- [ ] The evaluator outputs a JSON verdict: `[{ ac_checkbox, ac_text, passed, evidence: [{ ref, passed, details }] }]`

**Tech Notes:** This is the core of the deterministic evaluation engine from Plan Section 5.2. For the bullet tracer, only implement the `test_result` verification type and `ALL_PASS` condition. Other verification types come in Epic 9.

**Dependencies:** Story 0.2 (spec with traceability map), Story 0.4 (parsed test results)

**Demo Impact:** "12 out of 12 verifications passed for AC checkbox 0. This evaluation is 100% deterministic — zero AI."

---

### Story 0.6: Console Output — End-to-End Proof

**As a** hackathon developer
**I want** a single command that runs the entire bullet tracer pipeline and prints the results
**so that** I can demonstrate end-to-end flow in one terminal session.

**Acceptance Criteria:**
- [ ] Running `python run_pipeline.py DEMO-001` (or equivalent) executes: read spec → generate tests → run tests → parse results → evaluate → print verdicts
- [ ] Console output clearly shows: which spec was used, which tests were generated, which passed/failed, and the final verdict per AC checkbox
- [ ] Exit code is 0 if all checkboxes pass, non-zero otherwise

**Tech Notes:** This is just a shell script or Python script that calls Stories 0.3 → 0.4 → 0.5 in sequence. No Jira integration yet (that's Epic 1 and 6). No AI (that's Epic 2). Just the deterministic pipeline.

**Dependencies:** Stories 0.3, 0.4, 0.5

**Demo Impact:** This IS the bullet tracer. "Watch: one command, spec in, verdicts out." Everything after this makes it smarter and more connected.

---

## Epic 1: Real Jira Integration

**Goal:** Replace hardcoded Jira data with live API calls. The pipeline now reads real AC from a real ticket and (later in Epic 6) writes real updates back.

**After this epic:** The pipeline reads AC from a live Jira Cloud ticket and uses the AC text as input to the spec (still hardcoded spec for now, but the Jira connection is real).

---

### Story 1.1: Jira API Client — Read Ticket

**As a** developer using the tool
**I want** the pipeline to pull acceptance criteria from a real Jira Cloud ticket
**so that** the spec is driven by actual business requirements, not hardcoded test data.

**Acceptance Criteria:**
- [ ] Given a Jira ticket key (e.g., `PROJ-1234`), the tool fetches the ticket via Jira REST API
- [ ] The tool extracts: ticket summary, description, and acceptance criteria (as a list with checkbox index and text)
- [ ] AC checkboxes are parsed correctly regardless of whether they use Jira's native checklist, ADF checkboxes, or markdown-style `[ ]` / `[x]` in the description
- [ ] The extracted AC is stored in the VerificationContext as `raw_acceptance_criteria`
- [ ] Auth uses API token (not OAuth) for simplicity

**Tech Notes:** Jira Cloud REST API v3. The AC format varies wildly — Jira's Atlassian Document Format (ADF) represents checkboxes as `taskList` nodes. For hackathon, support ADF checkboxes and fall back to regex parsing of markdown checkboxes in the description.

**Dependencies:** None (can be built in parallel with Epic 0)

**Demo Impact:** "We're reading directly from your Jira ticket. This is a live connection."

---

### Story 1.2: Jira API Client — Write Checkbox Update

**As a** developer using the tool
**I want** the pipeline to tick specific AC checkboxes on the Jira ticket
**so that** the ticket reflects which acceptance criteria have been verified.

**Acceptance Criteria:**
- [ ] Given a Jira ticket key and a checkbox index, the tool marks that checkbox as complete
- [ ] The update preserves all other content on the ticket (description, other checkboxes, comments)
- [ ] Ticking a checkbox that's already checked is a no-op (idempotent)
- [ ] The tool can tick multiple checkboxes in a single API call or sequential calls

**Tech Notes:** Updating ADF checkboxes requires fetching the current description ADF, modifying the specific `taskItem` node's `state` attribute, and PUT-ing the updated description back. This is fiddly but deterministic.

**Dependencies:** Story 1.1 (need the Jira client infrastructure)

**Demo Impact:** This is the "mic drop" — tab to Jira, refresh, checkboxes are ticked.

---

### Story 1.3: Jira API Client — Post Evidence Comment

**As a** developer using the tool
**I want** the pipeline to post a structured evidence comment on the Jira ticket showing which verifications passed
**so that** there is a permanent audit trail on the ticket itself.

**Acceptance Criteria:**
- [ ] After evaluation, the tool posts a comment to the Jira ticket using Jira REST API
- [ ] The comment includes: overall pass/fail, per-AC-checkbox breakdown, per-ref evidence table, spec file path
- [ ] The comment uses Jira wiki markup or ADF for formatting (tables, checkmarks, headers)
- [ ] The comment is posted regardless of whether all checkboxes pass or not (failures are documented too)

**Tech Notes:** Use the Jira comment API (`POST /rest/api/3/issue/{key}/comment`). Format using the evidence comment template from Plan Section 6.3.

**Dependencies:** Story 0.5 (evaluator produces the verdicts), Story 1.1 (Jira client)

**Demo Impact:** "Here's the audit trail — posted directly to Jira. When an auditor asks 'how was this verified?', the answer is right on the ticket."

---

### Story 1.4: Jira API Client — Transition Ticket

**As a** developer using the tool
**I want** the pipeline to automatically transition the Jira ticket to "Done" when all AC checkboxes pass
**so that** the ticket status reflects verified completion without manual developer action.

**Acceptance Criteria:**
- [ ] When all AC checkboxes are verified, the tool transitions the ticket to "Done" (or a configurable target status)
- [ ] When some but not all checkboxes pass, the tool transitions to "In Review" (or leaves status unchanged)
- [ ] The tool handles Jira workflow transition IDs correctly (fetches available transitions first)
- [ ] Transition failures (e.g., missing required fields, workflow restrictions) are reported clearly

**Tech Notes:** Jira transitions require looking up the transition ID first (`GET /rest/api/3/issue/{key}/transitions`) then executing it (`POST /rest/api/3/issue/{key}/transitions`). The transition name-to-ID mapping varies per Jira project workflow.

**Dependencies:** Story 1.2 (checkbox updates happen before transition)

**Demo Impact:** "The ticket moved to Done. No developer touched Jira."

---

## Epic 2: AI Negotiation — Core Loop

**Goal:** Build the AI-powered negotiation that transforms fuzzy AC into structured spec elements. This is the "intelligence" layer — Phases 1-4 of the negotiation protocol.

**After this epic:** A developer can paste an AC (or have it pulled from Jira), have an interactive conversation with the AI, and get structured spec elements as output.

---

### Story 2.1: Negotiation Harness & Context Object

**As a** developer building the tool
**I want** a harness that manages the negotiation conversation state, tracks which phase we're in, and accumulates spec elements
**so that** the AI operates within a controlled pipeline rather than freewheeling.

**Acceptance Criteria:**
- [ ] A VerificationContext dataclass (or equivalent) exists with all fields from Plan Section 7.2
- [ ] The harness tracks the current negotiation phase (0 through 7)
- [ ] Each phase has an explicit entry condition (previous phase completed) and exit condition (required fields populated)
- [ ] The negotiation log captures every AI message and developer response with timestamps
- [ ] Phase transitions are deterministic — the harness decides when to advance, not the AI

**Tech Notes:** This is the Sherpa-inspired state machine concept, implemented as a simple Python class with phase enum and transition rules. The harness calls the AI, receives structured output, validates it, updates the context, and decides the next phase. The AI never decides which phase comes next.

**Dependencies:** None (can start in parallel)

**Demo Impact:** Not directly visible, but this is what makes the negotiation reproducible and debuggable.

---

### Story 2.2: AI Integration — LLM Client

**As a** developer building the tool
**I want** a client that sends prompts to the internal AI endpoint and receives structured responses
**so that** the negotiation phases can call the LLM with templated prompts and parse the output.

**Acceptance Criteria:**
- [ ] A client connects to the internal AI endpoint (Claude/Sherpa)
- [ ] The client accepts a system prompt and user message, returns the AI's response
- [ ] The client supports structured output (JSON mode or XML parsing) so responses can be programmatically processed
- [ ] The client handles rate limits, timeouts, and retries gracefully
- [ ] API key / auth is configured via environment variable, not hardcoded

**Tech Notes:** If using the internal Sherpa endpoint, follow the internal SDK docs. If using Claude directly, use the Anthropic SDK. The key requirement is structured output — every negotiation phase needs to parse the AI's response into specific fields, not just display free text.

**Dependencies:** None

**Demo Impact:** Not directly visible — this is infrastructure.

---

### Story 2.3: Phase 1 Skill — Interface & Actor Discovery

**As a** developer using the tool
**I want** the AI to read my acceptance criteria and classify each one by type, actor, and interface
**so that** I know what kind of verification each AC requires before we go deeper.

**Acceptance Criteria:**
- [ ] Given raw AC text, the AI classifies each AC as: `api_behavior`, `performance_sla`, `security_invariant`, `observability`, `compliance`, or `data_constraint`
- [ ] For `api_behavior` types, the AI proposes: HTTP method, endpoint path, and auth mechanism (informed by the constitution)
- [ ] For each AC, the AI identifies the actor (authenticated_user, admin, system, etc.)
- [ ] The AI asks 1-3 clarifying questions about any ambiguous classifications
- [ ] The developer confirms or corrects, and the classifications are stored in the context

**Tech Notes:** This is a single LLM call with the constitution injected into the system prompt. The prompt template should reference `constitution.api.base_path`, `constitution.api.auth.mechanism`, etc. Output should be structured (JSON array of classifications). See Plan Section 3.3 for the full prompt strategy.

**Dependencies:** Story 2.1 (harness), Story 2.2 (LLM client)

**Demo Impact:** "The AI read the AC and classified it: 'This is an API behavior for authenticated users at GET /api/v1/users/me. This one is a performance SLA. This one is a security invariant.'"

---

### Story 2.4: Phase 2 Skill — Happy Path Contract

**As a** developer using the tool
**I want** the AI to propose the exact success response for my endpoint, including field names, types, and constraints
**so that** the "correct" behavior is precisely defined before any tests are written.

**Acceptance Criteria:**
- [ ] For each `api_behavior` requirement, the AI proposes: success status code, content type, response body schema (field names, types, formats, required vs. optional)
- [ ] The AI proposes constraints linking response fields to request context (e.g., "response.id must equal jwt.sub")
- [ ] The AI identifies forbidden fields from `constitution.verification_standards.security_invariants`
- [ ] The AI asks clarifying questions about missing fields, nullable fields, and computed fields
- [ ] The developer confirms and the postconditions are stored in the context

**Tech Notes:** The prompt should include the constitution's API conventions and security invariants. Use the example-driven boundary discovery technique from the plan — propose a concrete example response and let the developer confirm/edit. See Plan Section 3.4.

**Dependencies:** Story 2.3 (need classifications to know which ACs are api_behavior)

**Demo Impact:** "The AI proposed the exact response shape. It even caught that 'avatar' should be nullable."

---

### Story 2.5: Phase 3 Skill — Precondition Formalization

**As a** developer using the tool
**I want** the AI to identify every precondition that must hold for the happy path to succeed
**so that** we know exactly what can go wrong and can define failure modes for each.

**Acceptance Criteria:**
- [ ] For each behavior, the AI identifies preconditions categorized as: authentication, authorization, data_existence, data_state, rate_limit, or system_health
- [ ] Each precondition has: an ID (PRE-001), human-readable description, semi-formal expression, and category
- [ ] The AI asks whether any implicit preconditions are missing (e.g., "Does the JWT need specific roles?")
- [ ] The developer confirms and preconditions are stored in the context

**Tech Notes:** Use Design by Contract technique. The formal expressions use a simple syntax: `entity.field operator value`. These aren't executable — they're precise enough that a human can unambiguously verify them and a test generator can translate them into setup fixtures. See Plan Section 3.5.

**Dependencies:** Story 2.4 (need the happy path contract to identify what must be true for it to work)

**Demo Impact:** "The AI found 3 preconditions: valid JWT, user exists, account is active."

---

### Story 2.6: Phase 4 Skill — Failure Mode Enumeration

**As a** developer using the tool
**I want** the AI to systematically enumerate every failure mode for every precondition, with exact error responses
**so that** the spec covers all error scenarios, not just the happy path.

**Acceptance Criteria:**
- [ ] For each precondition, the AI generates at least one failure mode (and usually multiple: e.g., "token missing" vs. "token expired" vs. "token malformed")
- [ ] Each failure mode has: an ID (FAIL-001), a description, a reference to the violated precondition, an exact status code, and an exact error response body using the constitution's error format
- [ ] The AI surfaces security-relevant questions (e.g., "Should 'user not found' and 'user deleted' return different status codes? Returning different codes leaks information.")
- [ ] The developer confirms and failure modes are stored in the context

**Tech Notes:** This is the FMEA-inspired technique from Plan Section 3.6. This phase produces the most valuable output — edge cases the PO never considered. The prompt should enumerate common failure subcategories for each precondition type (auth failures: missing, expired, malformed, wrong issuer, revoked; data state: inactive, suspended, pending, locked, deleted).

**Dependencies:** Story 2.5 (need preconditions to enumerate failures for)

**Demo Impact:** This is the "wow" moment. "The AI found a security issue: returning 404 vs. 410 for deleted users leaks information about account existence. Both should return 404."

---

### Story 2.7: Interactive CLI/Chat Interface

**As a** developer using the tool
**I want** an interactive interface where I can see the AI's proposals, answer clarifying questions, and approve each phase
**so that** the negotiation feels like a conversation, not a form.

**Acceptance Criteria:**
- [ ] A CLI or chat UI presents the AI's output for each phase and waits for developer input
- [ ] The developer can: confirm/approve, provide corrections, ask the AI to elaborate, or skip to the next phase
- [ ] The current negotiation phase is clearly indicated (e.g., "Phase 2 of 7: Happy Path Contract")
- [ ] The developer can type "approve" to advance to the next phase, or "edit" to modify a specific section
- [ ] The full negotiation log is saved for traceability

**Tech Notes:** For the hackathon, a simple terminal-based CLI with `input()` prompts is sufficient. A rich terminal UI (with `rich` or `inquirer.js`) is a stretch goal. The key is that the interface calls the harness, which calls the AI, which returns structured output that the interface renders.

**Dependencies:** Stories 2.3-2.6 (the phase skills to orchestrate)

**Demo Impact:** "Watch the developer interact with the AI. It asks smart questions. The developer approves. The spec builds incrementally."

---

## Epic 3: Formal Spec Emission

**Goal:** The negotiation output is compiled into a complete, validated YAML spec file with traceability map.

**After this epic:** The negotiation produces a real `.verify/specs/{jira_key}.yaml` file that downstream skills can consume.

---

### Story 3.1: Spec Compiler — Context to YAML

**As a** developer using the tool
**I want** the negotiation results to be automatically compiled into a valid spec YAML file
**so that** the spec is a concrete artifact committed to the repo, not just conversation history.

**Acceptance Criteria:**
- [ ] After the developer approves the negotiation, the tool compiles the VerificationContext into a YAML file
- [ ] The YAML follows the schema defined in the plan (meta, context, requirements, traceability)
- [ ] The file is written to `.verify/specs/{jira_key}.yaml`
- [ ] The meta section includes: jira_key, generated_at, approved_by, negotiation_log path
- [ ] The YAML is validated against the spec JSON Schema (or at minimum, is valid YAML parseable by the downstream tools)

**Tech Notes:** This is a straightforward serialization of the VerificationContext fields into the YAML schema. Use Python's `yaml.dump` with custom representers for clean output. Add comments for readability (YAML supports inline comments).

**Dependencies:** Epic 2 (negotiation produces the context to serialize)

**Demo Impact:** "Here's the spec file. It was generated from our conversation. Every line traces to an AC checkbox."

---

### Story 3.2: Verification Routing Table Generation

**As a** developer using the tool
**I want** the spec to include a routing table that maps each contract element to a specific verification skill
**so that** downstream test generation is a deterministic lookup, not an AI decision.

**Acceptance Criteria:**
- [ ] The spec includes a `verification` block under each requirement
- [ ] Each verification entry specifies: refs (which contract elements it covers), skill (which generator to use), pattern (which constitution test pattern to follow), and output (file path for the generated artifact)
- [ ] The routing decision is made during negotiation (Phase 6) based on the requirement type and constitution's testing patterns
- [ ] For the MVP, routing can use simple rules: `api_behavior` → `junit5_controller_test` (or equivalent for the repo's language), `performance_sla` → `newrelic_alert_config`, `security_invariant` → same as the behavior test

**Tech Notes:** For the hackathon, the routing logic can be a simple switch statement on `requirement.type` + `invariant.type`. In production, this becomes a more sophisticated classifier.

**Dependencies:** Story 3.1 (part of the spec compilation)

**Demo Impact:** "The spec says: route these 10 refs to JUnit, route this 1 ref to New Relic. The router reads the spec, not the AI."

---

### Story 3.3: Traceability Map Generation

**As a** developer using the tool
**I want** the spec to include an explicit traceability map linking every verification ref to specific AC checkboxes
**so that** the evaluator can deterministically answer "which checkboxes are satisfied?" from test results.

**Acceptance Criteria:**
- [ ] The spec includes a top-level `traceability.ac_mappings` block
- [ ] Each AC checkbox has: index, original text, pass_condition, and a list of required verification refs
- [ ] Refs that satisfy multiple AC checkboxes appear in multiple mappings (many-to-many)
- [ ] Each verification ref has a `verification_type` (test_result, deployment_check, config_validation, etc.)
- [ ] The traceability map is generated from the negotiation results — the AI assigns refs to checkboxes during the negotiation based on which AC each requirement/invariant was derived from

**Tech Notes:** The `ac_checkbox` index comes from Phase 0 (Jira ingestion). The mapping is built incrementally: Phase 1 assigns each AC to a requirement, Phases 2-5 add contract elements to requirements, and Phase 6 routes elements to verification types. The compiler walks this chain to build the final map.

**Dependencies:** Story 3.1 (part of the spec compilation)

**Demo Impact:** "This traceability map is how one test can satisfy two AC checkboxes. The security invariant test satisfies both 'user can view profile' AND 'data never exposed to other users.'"

---

## Epic 4: Multi-Skill Routing & Test Generation

**Goal:** Replace the hardcoded test generator from Epic 0 with AI-powered skill agents that read the spec and generate framework-appropriate verification artifacts.

**After this epic:** The spec drives real test generation via specialized skills, producing tagged test files that match the repo's existing patterns.

---

### Story 4.1: Skill Agent Framework

**As a** developer building the tool
**I want** a plugin architecture where each verification skill is a self-contained module with a prompt template and output contract
**so that** adding new verification types (JUnit, Jest, New Relic, Gherkin) is just adding a new skill file.

**Acceptance Criteria:**
- [ ] A skill is defined by: a prompt template (or SKILL.md), input contract (which spec fields it reads), and output contract (what file it produces and in what format)
- [ ] The orchestrator reads the spec's `verification[].skill` field and dispatches to the matching skill
- [ ] Each skill receives: the relevant spec contract elements, the constitution (for test patterns), and the output file path
- [ ] Skills are loaded on demand (progressive disclosure) — only the needed skills are invoked

**Tech Notes:** For the hackathon, skills can be Python functions registered in a dict: `SKILLS = { "junit5_controller_test": generate_junit, "newrelic_alert_config": generate_nrql }`. In production, these become proper Agent Skills with SKILL.md files.

**Dependencies:** Story 3.2 (need the routing table to dispatch)

**Demo Impact:** "The router dispatched to the JUnit skill AND the New Relic skill. Each is a specialist."

---

### Story 4.2: Unit Test Skill — Primary Language

**As a** developer using the tool
**I want** a skill that reads the spec's contract and generates a complete test file with tagged test methods in my repo's language and framework
**so that** I get tests that match my codebase's existing patterns, not generic boilerplate.

**Acceptance Criteria:**
- [ ] The skill reads: `contract.success`, `contract.failures`, `contract.invariants`, and `constitution.testing.patterns`
- [ ] For each contract element, the skill generates a test method with the correct `@Tag` / test name containing the spec ref
- [ ] The test file uses the same annotations, imports, and assertion style as existing tests in the repo (from the constitution's patterns)
- [ ] The generated test file compiles/parses without errors
- [ ] The generated tests pass against the dummy app (or target app)

**Tech Notes:** This is the skill that uses AI — it takes structured spec data and a test pattern example, and generates a complete test file. The prompt should include: the spec contract as YAML, one example test file from the constitution, and the instruction to follow the same style. The AI's job is translation (spec → test code), not invention.

**Dependencies:** Story 4.1 (skill framework), Story 0.2 or 3.1 (spec to read)

**Demo Impact:** "Look at the generated test — it uses @WebMvcTest and MockMvc, just like our existing tests. It didn't invent a new style."

---

### Story 4.3: Tag Contract Enforcement

**As a** developer using the tool
**I want** every generated test method to be tagged with its spec ref in a consistent format
**so that** the evaluator can match test results back to spec elements.

**Acceptance Criteria:**
- [ ] Every generated test method includes a tag/marker matching the format `{REQ-ID}.{element-ID}` (e.g., `REQ-001.FAIL-002`)
- [ ] For JUnit 5: uses `@Tag("REQ-001.FAIL-002")` annotation
- [ ] For Jest: includes `[REQ-001.FAIL-002]` in the `it()` description string
- [ ] For pytest: uses `@pytest.mark.spec("REQ-001.FAIL-002")` marker
- [ ] The skill validates that every ref in `verification[].refs` has a corresponding tagged test method (no orphaned refs)

**Tech Notes:** This is a validation step in the skill, not a separate component. After generating the test file, the skill scans it for tag patterns and verifies coverage against the spec's `verification[].refs`. If a ref is missing a test, the skill flags it.

**Dependencies:** Story 4.2 (generates the tagged tests)

**Demo Impact:** "Every test method has a tag. That tag links to a spec ref. That spec ref links to an AC checkbox. That's the chain."

---

## Epic 5: Evaluation Engine (Full)

**Goal:** Replace the minimal evaluator from Epic 0 with the full multi-strategy evaluation engine that handles different verification types.

**After this epic:** The evaluator can handle test results, deployment checks, config validations, and produce detailed verdicts per AC checkbox.

---

### Story 5.1: Multi-Format Test Result Parser

**As a** developer using the tool
**I want** the evaluator to parse test results from JUnit XML, Jest JSON, and Cucumber JSON into a unified format
**so that** the evaluation works regardless of which test framework the repo uses.

**Acceptance Criteria:**
- [ ] JUnit XML parser extracts: test name, classname, tags (from `<property>` elements or `@DisplayName` patterns), status, failure message
- [ ] Jest JSON parser extracts: full test name (including `describe` ancestors), tags (from bracket patterns in test names), status, failure messages
- [ ] Cucumber JSON parser extracts: scenario name, tags (from `@TAG` annotations), status (all steps must pass for scenario to pass)
- [ ] All parsers emit the same unified structure: `{ name, display_name, tags, status, failure_message }`
- [ ] The merge function combines results from multiple files/formats

**Tech Notes:** See Plan Section 5.2 for the parser implementations. JUnit XML is the priority (most universal). Jest JSON and Cucumber JSON are stretch goals. The key is the `tags` field — this is what the evaluator matches on.

**Dependencies:** Story 0.4 (extends the basic parser)

**Demo Impact:** Not directly visible, but enables the evaluator to work with any test framework.

---

### Story 5.2: Deployment Check Evaluation Strategy

**As a** developer using the tool
**I want** the evaluator to verify that generated configuration files (New Relic alerts, OTel configs) exist and are structurally valid
**so that** non-test verification artifacts can satisfy AC checkboxes.

**Acceptance Criteria:**
- [ ] For `verification_type: deployment_check`, the evaluator checks: file exists at the specified path, file is parseable (valid JSON/YAML), file passes optional schema validation
- [ ] For `verification_type: config_validation`, the evaluator checks: file exists, file contains required entries (e.g., specific span names, metric names)
- [ ] A missing or invalid file is a FAIL with a clear error message
- [ ] A valid file is a PASS with details about what was validated

**Tech Notes:** This is the `eval_deployment_check` and `eval_config_validation` strategies from Plan Section 5.2. For the hackathon, schema validation can be simple (file is valid JSON and contains expected top-level keys). Full JSON Schema validation is a stretch goal.

**Dependencies:** Story 0.5 (extends the basic evaluator)

**Demo Impact:** "AC checkbox 1 — 'responds within 500ms' — was satisfied by verifying that a New Relic alert config was generated. No unit test needed. The config IS the proof."

---

### Story 5.3: Verdict Aggregation with Pass Conditions

**As a** developer using the tool
**I want** the evaluator to support multiple pass conditions (ALL_PASS, ANY_PASS, PERCENTAGE) for different AC checkboxes
**so that** different types of acceptance criteria can have appropriate evaluation logic.

**Acceptance Criteria:**
- [ ] `ALL_PASS`: checkbox passes only if every required verification passes
- [ ] `ANY_PASS`: checkbox passes if at least one required verification passes
- [ ] `PERCENTAGE`: checkbox passes if the pass rate meets the specified threshold
- [ ] The verdict for each checkbox includes: the pass condition used, the total/passed/failed counts, and per-ref evidence

**Tech Notes:** For the hackathon MVP, only `ALL_PASS` is needed. `ANY_PASS` and `PERCENTAGE` are quick to implement but unlikely to be needed for the demo.

**Dependencies:** Story 5.1 or 5.2 (need verification results to aggregate)

**Demo Impact:** Mentioned in passing: "The evaluator supports different pass conditions per checkbox — ALL_PASS, ANY_PASS, or percentage thresholds."

---

## Epic 6: Jira Feedback Loop (Full)

**Goal:** Connect the evaluator's verdicts to Jira: tick checkboxes, post evidence, transition the ticket.

**After this epic:** The full end-to-end pipeline works: Jira AC → AI negotiation → spec → tests → execution → evaluation → Jira checkboxes ticked + evidence posted + ticket transitioned.

---

### Story 6.1: Wire Evaluator to Jira Checkbox Updates

**As a** developer using the tool
**I want** the evaluator's verdicts to automatically tick the corresponding AC checkboxes on the Jira ticket
**so that** the Jira ticket reflects which acceptance criteria are verified without me touching Jira.

**Acceptance Criteria:**
- [ ] For each verdict where `passed == true`, the corresponding AC checkbox is ticked via Stories 1.2
- [ ] For verdicts where `passed == false`, the checkbox is left unchecked
- [ ] The mapping from `ac_checkbox` index to Jira checkbox is correct (0-indexed)
- [ ] The update is idempotent — running the pipeline twice doesn't break anything

**Dependencies:** Story 1.2 (Jira write), Story 5.3 (verdicts)

**Demo Impact:** The Jira refresh moment. "All three checkboxes just ticked themselves."

---

### Story 6.2: Wire Evaluator to Evidence Comment

**As a** developer using the tool
**I want** the full evidence breakdown posted as a comment on the Jira ticket
**so that** there's a permanent audit trail documenting exactly what was verified and how.

**Acceptance Criteria:**
- [ ] The evidence comment shows: overall result, per-checkbox breakdown with pass/fail icon, per-ref evidence table with verification type
- [ ] The comment includes the spec file path for traceability
- [ ] Both passing and failing verifications are shown (failures explain what went wrong)
- [ ] The comment is formatted using Jira wiki markup or ADF for readability

**Dependencies:** Story 1.3 (Jira comment), Story 5.3 (verdicts)

**Demo Impact:** "Here's the audit trail on the ticket. Every verification, every result, every link in the chain."

---

### Story 6.3: Wire Evaluator to Ticket Transition

**As a** developer using the tool
**I want** the ticket to automatically move to "Done" when all AC checkboxes pass
**so that** the ticket lifecycle is fully automated.

**Acceptance Criteria:**
- [ ] All checkboxes pass → transition to "Done"
- [ ] Some checkboxes fail → leave status unchanged (or move to "In Review" if configured)
- [ ] Transition errors are handled gracefully (logged, not pipeline-breaking)

**Dependencies:** Story 1.4 (Jira transition), Story 6.1 (checkboxes updated first)

**Demo Impact:** "Ticket status: Done. Zero manual steps."

---

## Epic 7: Constitution & Repo Awareness

**Goal:** Build the init phase that scans the repo and generates the constitution, so the pipeline adapts to different codebases.

**After this epic:** Running `verify init` on a new repo generates a constitution YAML that steers all subsequent spec generation and test output.

---

### Story 7.1: Repo Scanner — Stack Detection

**As a** developer using the tool
**I want** the init command to detect my repo's language, framework, build tool, and test framework
**so that** the constitution is auto-generated from my actual codebase, not manually written.

**Acceptance Criteria:**
- [ ] Detects language from: `build.gradle`/`pom.xml` (Java), `package.json` (Node), `requirements.txt`/`pyproject.toml` (Python)
- [ ] Detects framework from: dependency analysis (Spring Boot, Express, FastAPI, etc.)
- [ ] Detects test framework from: test dependencies (JUnit 5, Jest, pytest, etc.)
- [ ] Populates `constitution.project` and `constitution.testing` sections
- [ ] Presents findings for developer confirmation before writing the file

**Dependencies:** None (can be built in parallel)

**Demo Impact:** "We ran `verify init` and it detected Spring Boot 3.2 with JUnit 5 and Mockito."

---

### Story 7.2: Test Pattern Discovery

**As a** developer using the tool
**I want** the init command to sample existing test files and extract the testing patterns used in my repo
**so that** generated tests match my codebase's existing style.

**Acceptance Criteria:**
- [ ] The scanner finds 3-5 existing test files by searching the test directory
- [ ] For each test file, it extracts: annotations used, import statements, assertion library, naming conventions
- [ ] The patterns are stored in `constitution.testing.patterns` with example file paths
- [ ] The AI (or pattern matcher) classifies patterns by type: controller_test, service_test, integration_test

**Tech Notes:** This can be AI-assisted — send a test file to the LLM and ask it to extract the pattern. Or it can be regex-based for common patterns (@WebMvcTest, @ExtendWith, etc.).

**Dependencies:** Story 7.1 (need the base stack detection first)

**Demo Impact:** "It found our existing test patterns — @WebMvcTest for controllers, @ExtendWith(MockitoExtension.class) for services."

---

### Story 7.3: API Convention Discovery

**As a** developer using the tool
**I want** the init command to detect my API conventions (base path, auth mechanism, error format)
**so that** the negotiation AI proposes endpoints and error responses that match my actual API style.

**Acceptance Criteria:**
- [ ] Scans controller/route files for common base paths (e.g., `/api/v1/`)
- [ ] Detects auth mechanism from annotations (`@PreAuthorize`, passport middleware, etc.) or security config
- [ ] Detects error response format from existing error handlers or sample error responses
- [ ] Populates `constitution.api` section

**Dependencies:** Story 7.1

**Demo Impact:** "It detected our API uses /api/v1/ base path with JWT Bearer auth and returns errors in our standard format."

---

## Epic 8: Advanced Negotiation

**Goal:** Add Phases 5-7 to the negotiation: invariant extraction, completeness sweep, and EARS formalization with human approval.

**After this epic:** The negotiation produces specs with invariants, has been checked for completeness gaps, and presents a final EARS summary for approval.

---

### Story 8.1: Phase 5 Skill — Invariant Extraction

**As a** developer using the tool
**I want** the AI to extract universal properties (security, performance, compliance invariants) from the AC, constitution, and data model
**so that** the spec captures what must ALWAYS be true, not just scenario-specific behavior.

**Acceptance Criteria:**
- [ ] The AI extracts invariants from three sources: the AC text (explicit invariants), the constitution's `verification_standards.security_invariants`, and inferences from the data model (e.g., PII in response → data classification required)
- [ ] Each invariant has: ID, type (security/performance/data_integrity/compliance/idempotency/observability), rule, and verification type
- [ ] Invariants with `verification_type` other than `unit_test` are flagged for routing to specialized skills (e.g., New Relic, OTel)
- [ ] The developer confirms all invariants

**Dependencies:** Story 2.6 (builds on the core negotiation loop)

**Demo Impact:** "The AI inferred that because the response contains email (PII), a data classification header is required. The PO never wrote that."

---

### Story 8.2: Phase 6 Skill — Completeness Sweep

**As a** developer using the tool
**I want** the AI to run a checklist of dimensions and flag anything the AC and negotiation didn't cover
**so that** I know exactly what's specified and what's explicitly deferred.

**Acceptance Criteria:**
- [ ] The AI runs through a standardized checklist (auth, authz, input validation, output schema, errors, rate limiting, pagination, caching, versioning, idempotency, observability, security, data classification, deprecation, documentation)
- [ ] Each checklist item is marked: COVERED (with ref), EXPLICITLY DEFERRED, or NOT ADDRESSED
- [ ] NOT ADDRESSED items are surfaced to the developer with the question "Should I add a spec entry?"
- [ ] The developer can add entries or confirm they're out of scope
- [ ] The checklist is customizable per organization (via constitution)

**Dependencies:** Stories 2.3-2.6 and 8.1 (need all prior phases complete)

**Demo Impact:** "The AI flagged that caching and rate limiting weren't addressed. The developer confirmed they're out of scope for this story."

---

### Story 8.3: Phase 7 Skill — EARS Formalization & Approval

**As a** developer using the tool
**I want** the AI to synthesize all negotiation results into a set of EARS statements and present them for my final approval
**so that** I can review the entire spec in human-readable form before it's frozen.

**Acceptance Criteria:**
- [ ] Every contract element (success, failure, invariant) is expressed as an EARS statement (WHEN/SHALL, IF/THEN, WHILE/SHALL, or ubiquitous)
- [ ] The EARS statements are presented as a numbered list, grouped by requirement
- [ ] The developer can: approve all, reject specific statements (returning to the relevant phase), or edit statements directly
- [ ] On approval, the spec status changes to "approved" and the YAML is emitted
- [ ] On rejection, the harness re-enters the relevant negotiation phase

**Dependencies:** Story 8.2 (completeness sweep is the last check before formalization)

**Demo Impact:** "Here are 15 EARS statements. Each one maps to exactly one test. The developer reads them, approves, and the spec is frozen."

---

## Epic 9: Beyond-Code Verification Skills

**Goal:** Add specialized skills that generate non-test verification artifacts: New Relic alerts, OpenTelemetry configs, Gherkin scenarios.

**After this epic:** The pipeline can prove "correctness" through alert configurations, observability instrumentation, and human-readable behavior documentation — not just unit tests.

---

### Story 9.1: New Relic Alert Config Skill

**As a** developer using the tool
**I want** the pipeline to generate a New Relic NRQL alert configuration from a performance invariant in the spec
**so that** my latency SLA is monitored, and the alert config itself is the "proof" that monitoring is in place.

**Acceptance Criteria:**
- [ ] The skill reads invariants with `type: performance` from the spec
- [ ] It generates a valid NRQL alert condition JSON (query, threshold, duration, notification channel)
- [ ] The generated config is written to the path specified in `verification[].output`
- [ ] The evaluator verifies the file exists and is valid (deployment_check strategy)
- [ ] The generated NRQL query references the correct endpoint/transaction name

**Dependencies:** Story 4.1 (skill framework), Story 5.2 (deployment check evaluator)

**Demo Impact:** "This isn't a test. It's a New Relic alert config. The spec said 'p99 < 500ms', and the skill generated the monitoring. That's correctness beyond code."

---

### Story 9.2: Gherkin Scenario Skill

**As a** developer using the tool
**I want** the pipeline to generate Gherkin (.feature) files from the spec's contract
**so that** there's a human-readable behavior document derived from the same spec as the tests.

**Acceptance Criteria:**
- [ ] The skill reads the success, failures, and invariants from the spec's contract
- [ ] It generates Given/When/Then scenarios with `@TAG` annotations matching spec refs
- [ ] The generated .feature file is syntactically valid Gherkin
- [ ] Each scenario is tagged with the spec ref (e.g., `@REQ-001.FAIL-002`)

**Dependencies:** Story 4.1 (skill framework)

**Demo Impact:** "The same spec generated JUnit tests, a New Relic alert, AND Gherkin scenarios. Three different proofs of correctness from one specification."

---

### Story 9.3: OpenTelemetry Instrumentation Skill

**As a** developer using the tool
**I want** the pipeline to generate OpenTelemetry span configurations for monitored endpoints
**so that** observability instrumentation is treated as a verifiable artifact, not an afterthought.

**Acceptance Criteria:**
- [ ] The skill reads invariants with `type: observability` from the spec
- [ ] It generates an OTel config snippet or instrumentation code for the target endpoint
- [ ] The evaluator verifies the config file contains required span definitions (config_validation strategy)

**Dependencies:** Story 4.1 (skill framework), Story 5.2 (config validation evaluator)

**Demo Impact:** "OTel instrumentation was generated from the spec. The evaluator confirmed the span exists for our endpoint."

---

## Epic 10: CI/CD & PR Automation

**Goal:** Move from local execution to CI/CD integration: automated PRs, GitHub Actions, pipeline-triggered Jira updates.

**After this epic:** The full pipeline runs in CI: PR is created with verification artifacts, tests run in GitHub Actions, results flow back to Jira.

---

### Story 10.1: Automated PR Creation

**As a** developer using the tool
**I want** the pipeline to automatically create a PR with the generated spec and verification artifacts
**so that** the traceability chain extends to the Git history.

**Acceptance Criteria:**
- [ ] The tool creates a branch named per the constitution's `conventions.branch_naming` pattern
- [ ] Generated files (spec, tests, configs) are committed with a message per `conventions.commit_format`
- [ ] A PR is opened with: Jira ticket link, spec summary, list of generated files, EARS statements in the description
- [ ] The PR description template includes the traceability map summary

**Dependencies:** Epics 3-4 (need generated artifacts to commit)

**Demo Impact:** "The PR was auto-created. The description links to the Jira ticket and lists every spec ref."

---

### Story 10.2: GitHub Actions Integration

**As a** developer using the tool
**I want** a GitHub Action that runs the evaluation pipeline on PR, parsing test results and updating Jira
**so that** the verification-to-Jira-update loop runs automatically in CI, not just locally.

**Acceptance Criteria:**
- [ ] A GitHub Action workflow triggers on PR creation/update
- [ ] The action runs tests, parses results, evaluates against the spec, and updates Jira
- [ ] The action posts a PR comment with the evaluation summary
- [ ] Jira checkbox updates and evidence comments are posted from CI

**Dependencies:** Story 10.1, Epics 5-6

**Demo Impact:** "This runs in CI now. Every PR automatically verifies against the spec and updates Jira."

---

### Story 10.3: Spec Drift Detection

**As a** developer using the tool
**I want** the CI pipeline to detect when code changes break the spec (tests fail) or when the spec is modified without updating tests
**so that** the spec remains the source of truth and drift is caught early.

**Acceptance Criteria:**
- [ ] If tests tagged with spec refs fail, the CI flags which spec elements are violated
- [ ] If the spec YAML is modified, the CI checks that all verification artifacts are regenerated
- [ ] Drift is reported as a PR check failure with specific details about which refs are out of sync

**Dependencies:** Story 10.2

**Demo Impact:** "If someone changes the code and breaks a spec-linked test, CI catches it and tells you exactly which business requirement was violated."

---

## Summary: Progressive Demo Capability

| After Epic | Demo Capability |
|-----------|----------------|
| Epic 0 | "One command: hardcoded spec → generated tests → pass/fail verdict in the terminal" |
| Epic 1 | "We read from a real Jira ticket and write checkboxes back" |
| Epic 2 | "An AI negotiation turns fuzzy AC into precise spec elements, finding edge cases the PO missed" |
| Epic 3 | "The negotiation produces a formal YAML spec with a traceability map" |
| Epic 4 | "Specialized skills generate framework-appropriate tests with tagged spec refs" |
| Epic 5 | "The evaluator handles multiple verification types, not just test pass/fail" |
| Epic 6 | "Full loop: Jira → AI → spec → tests → pass → checkboxes ticked + evidence posted + ticket Done" |
| Epic 7 | "The tool adapts to any repo by scanning the codebase and generating a constitution" |
| Epic 8 | "The negotiation extracts invariants, runs completeness checks, and presents EARS for approval" |
| Epic 9 | "Correctness beyond code: New Relic alerts, OTel configs, Gherkin scenarios from the same spec" |
| Epic 10 | "Full CI/CD: auto-PRs, GitHub Actions evaluation, spec drift detection" |

**For the hackathon: target Epics 0-4 + Stories 6.1-6.2.** That gives you the full chain from AI negotiation → spec → tests → Jira checkboxes with evidence, which is the complete "mic drop" demo.
