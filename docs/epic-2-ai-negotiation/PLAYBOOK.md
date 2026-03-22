## Epic 2: AI Negotiation — Core Loop [MVP] ✅ COMPLETE

**Goal:** Build the AI-powered negotiation that transforms fuzzy AC into structured spec elements (Phases 1-4).
**Depends on:** Epic 0 (pipeline exists), Epic 1 (can read from Jira)
**After this epic:** A developer can interactively negotiate with the AI, turning AC into classifications, postconditions, preconditions, and failure modes.

> **Design references:** This epic implements the core Sherpa state machine pattern ([reference-library.md §1](reference-library.md#1-sherpa--model-driven-agent-orchestration-via-state-machines)). The `NegotiationHarness` follows harness engineering principles — it manages context, enforces transitions, and provides the belief object, while the AI operates *within* the harness, not above it ([reference-library.md §3](reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability)). Each phase skill follows the agent-as-code pattern: a self-contained module with a persona, input/output contract, and trigger conditions ([reference-library.md §4](reference-library.md#4-bmad--agent-as-code-agile-development-framework)).

### Implementation Notes (Learned During Development)

**Feedback loop:** The negotiation supports multi-turn revision. When the developer provides feedback instead of approving, the LLM receives a 3-turn conversation (original prompt → AI's previous output → developer feedback) via `LLMClient.chat_multi()`. This lets the AI revise its output based on specific corrections. The loop continues until the developer types "approve" or "skip".

**Deterministic validation (Block Principle 1):** Every phase output is validated by `negotiation/validate.py` against strict enums and schema rules. Invalid types, actors, or orphaned references trigger automatic retry — the LLM gets the validation errors appended to its prompt and tries again (up to 2 retries). This catches LLM inconsistencies (e.g., `api behavior` instead of `api_behavior`) without human intervention.

**Constitutional prompts (Block Principle 3):** Phase prompts use `MUST`/`RULES`/`FORBIDDEN` sections. Each prompt loads only the constitution fields relevant to that phase (not the full constitution), respecting the instruction budget from harness engineering.

**Guard conditions (Sherpa):** Phase transitions check structural integrity, not just "list non-empty": Phase 0 verifies every AC is classified, Phase 1 verifies every `api_behavior` has a postcondition, Phase 2 verifies every failure mode references a valid precondition.

**Post-negotiation synthesis:** After Phase 4, `synthesis.py` runs deterministically (zero AI) to extract invariants from the constitution, generate EARS statements (WHEN/SHALL, IF/THEN, WHILE/SHALL), and build the traceability map.

**Mock mode:** `LLM_MOCK=true` provides canned responses keyed by unique phrases in each phase's system prompt. Mock hint matching is order-sensitive — distinctive phrases like `"failure mode enumeration"` must appear before generic ones like `"classify"`.

**Web UI:** A FastAPI app at `localhost:8000` with 4 screens: Home (Jira story picker + manual entry), AC Overview, Negotiation (chat with clarifying questions), and Traceability (per-AC drill-down with stats).

**Agent Skills:** Each negotiation phase has a corresponding SKILL.md in `.claude/skills/` following the [Agent Skills open standard](https://agentskills.io). Skills use progressive disclosure: metadata (Level 1, ~100 tokens always loaded) → instructions with constitutional rules (Level 2, loaded when triggered) → SCHEMA.md reference (Level 3, loaded during execution). See [agent-skills-reference.md §6](agent-skills-reference.md) for how these map to our project.

---

### Feature 2.1: Negotiation Harness & VerificationContext [MVP]

**Story:** A harness that manages negotiation state, tracks phases, and accumulates spec elements.
**Depends on:** None
> **Deep dive:** The `VerificationContext` is Sherpa's "belief system" — agent-specific state tracking execution history, action logs, and task data. The harness is the outer layer of the three-layer stack (prompt → context → harness engineering). See [reference-library.md §1](reference-library.md#1-sherpa--model-driven-agent-orchestration-via-state-machines) for the belief system architecture and [reference-library.md §3](reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability) for the harness pattern (especially "The Agent Loop" and "Context Management Principles").

#### Prerequisites

```sh
python3 -c "import dataclasses; print('OK: dataclasses available')"
```

#### Implementation Steps

- [ ] **Step 1: Create the VerificationContext dataclass at `src/verify/context.py`**

  Implement a `VerificationContext` dataclass with all fields from `ac-to-specs-plan.md` Section 7.2:
  - `jira_key: str`, `jira_summary: str`
  - `raw_acceptance_criteria: list[dict]`
  - `constitution: dict`
  - `current_phase: str`
  - `negotiation_log: list[dict]` (each entry: `{phase, role, content, timestamp}`)
  - `classifications: list[dict]` (Phase 1 output)
  - `postconditions: list[dict]` (Phase 2 output)
  - `preconditions: list[dict]` (Phase 3 output)
  - `failure_modes: list[dict]` (Phase 4 output)
  - `invariants: list[dict]` (Phase 5 output)
  - `verification_routing: list[dict]` (Phase 6 output)
  - `ears_statements: list[str]` (Phase 7 output)
  - `traceability_map: dict`
  - `approved: bool`, `approved_by: str`, `approved_at: str`
  - `spec_path: str`, `generated_files: dict`
  - `verdicts: list[dict]`, `all_passed: bool`

  Use `field(default_factory=list)` for list fields and `field(default_factory=dict)` for dict fields.

  **Verify:**
  ```sh
  python3 -c "
  from verify.context import VerificationContext

  ctx = VerificationContext(
      jira_key='TEST-001',
      jira_summary='Test ticket',
      raw_acceptance_criteria=[{'index': 0, 'text': 'Test AC', 'checked': False}],
      constitution={}
  )
  assert ctx.jira_key == 'TEST-001'
  assert ctx.current_phase == 'phase_0'  # or similar default
  assert ctx.negotiation_log == []
  assert ctx.classifications == []
  print('OK: VerificationContext constructable with defaults')
  "
  ```
  Expected: `OK: VerificationContext constructable with defaults`

- [ ] **Step 2: Create the negotiation harness at `src/verify/negotiation/harness.py`**

  Implement a `NegotiationHarness` class that:
  - Holds a `VerificationContext`
  - Has an enum or list of phases: `[phase_0, phase_1, phase_2, phase_3, phase_4, phase_5, phase_6, phase_7]`
  - Tracks the current phase
  - Has `advance_phase()` that moves to the next phase (only if exit conditions met)
  - Has `add_to_log(phase, role, content)` that appends to `context.negotiation_log`
  - Has phase exit condition checks: e.g., Phase 1 requires `classifications` to be populated

  **Verify:**
  ```sh
  python3 -c "
  from verify.context import VerificationContext
  from verify.negotiation.harness import NegotiationHarness

  ctx = VerificationContext(jira_key='TEST-001', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}],
      constitution={})
  harness = NegotiationHarness(ctx)
  assert harness.current_phase == 'phase_1' or harness.current_phase == 'phase_0'
  harness.add_to_log('phase_1', 'ai', 'Test message')
  assert len(ctx.negotiation_log) == 1
  print('OK: NegotiationHarness works')
  "
  ```
  Expected: `OK: NegotiationHarness works`

#### Definition of Done

```sh
echo "=== Feature 2.1: Harness & Context ==="
python3 -c "
from verify.context import VerificationContext
from verify.negotiation.harness import NegotiationHarness

ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
    raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}],
    constitution={})
h = NegotiationHarness(ctx)
h.add_to_log('phase_1', 'ai', 'classified')
assert len(ctx.negotiation_log) == 1
print('PASS: harness and context work')
" && echo "=== Feature 2.1 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

### Feature 2.2: LLM Client — Claude/Anthropic SDK [MVP]

**Story:** A client that sends prompts to Claude and receives structured responses.
**Depends on:** None

#### Prerequisites

```sh
pip install anthropic 2>/dev/null; python3 -c "import anthropic; print('OK: anthropic SDK available')"
```

#### Implementation Steps

- [ ] **Step 1: Create LLM client at `src/verify/llm_client.py`**

  Implement `LLMClient` class with:
  - `__init__(api_key=None, model="claude-sonnet-4-20250514")` — reads `ANTHROPIC_API_KEY` from env if not provided
  - `chat(system_prompt: str, user_message: str, response_format: str = "json") -> dict | str` — sends a message and returns the response. If `response_format="json"`, attempts to parse the response as JSON.
  - Error handling for rate limits, timeouts, and auth failures with clear messages
  - A `mock` mode (set via env var `LLM_MOCK=true`) that returns predefined responses for testing without API calls

  **Verify:**
  ```sh
  python3 -c "
  import os
  os.environ['LLM_MOCK'] = 'true'
  from verify.llm_client import LLMClient

  client = LLMClient()
  response = client.chat(
      system_prompt='You are a test assistant.',
      user_message='Hello'
  )
  assert response is not None
  print(f'OK: LLMClient works in mock mode, response type: {type(response).__name__}')
  "
  ```
  Expected: `OK: LLMClient works in mock mode, response type: ...`

- [ ] **Step 2: Add structured output support**

  Ensure the `chat` method can request JSON output from Claude and parse it. Use Claude's system prompt to instruct JSON output, then parse the response.

  **Verify:**
  ```sh
  python3 -c "
  import os
  os.environ['LLM_MOCK'] = 'true'
  from verify.llm_client import LLMClient

  client = LLMClient()
  assert hasattr(client, 'chat')
  # In mock mode, should return a parseable response
  response = client.chat('system', 'test', response_format='json')
  print(f'OK: structured output supported, response: {type(response).__name__}')
  "
  ```
  Expected: `OK: structured output supported`

#### Definition of Done

```sh
echo "=== Feature 2.2: LLM Client ==="
LLM_MOCK=true python3 -c "
from verify.llm_client import LLMClient
client = LLMClient()
r = client.chat('system', 'hello')
assert r is not None
print('PASS: LLM client works in mock mode')
" && echo "=== Feature 2.2 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

### Feature 2.3: Phase 1 Skill — Interface & Actor Discovery [MVP]

**Story:** The AI reads AC and classifies each one by type, actor, and interface.
**Depends on:** Features 2.1, 2.2
> **Deep dive:** Each phase skill follows Block's 3 Principles: (1) identify what agents should NOT decide — use deterministic checks for type classification validation, (2) identify what agents SHOULD decide — interpretation and context-dependent reasoning, (3) write constitutional rules, not suggestions — explicit constraints in the prompt prevent skipping steps. See [reference-library.md §2](reference-library.md#2-agent-skills--modular-discoverable-capability-packages).

#### Prerequisites

```sh
python3 -c "
from verify.negotiation.harness import NegotiationHarness
from verify.llm_client import LLMClient
print('OK: harness and LLM client importable')
"
```

#### Implementation Steps

- [ ] **Step 1: Create Phase 1 skill at `src/verify/negotiation/phase1.py`**

  Implement `run_phase1(context: VerificationContext, llm: LLMClient) -> list[dict]` that:
  1. Builds a system prompt using the constitution (language, framework, API conventions) — see `ac-to-specs-plan.md` Section 3.3 for the prompt template
  2. Sends each AC to the LLM for classification
  3. Asks the LLM to determine for each AC:
     - `type`: one of `api_behavior`, `performance_sla`, `security_invariant`, `observability`, `compliance`, `data_constraint`
     - `actor`: `authenticated_user`, `admin`, `system`, `anonymous_user`, `api_client`
     - `interface`: for API behaviors, propose HTTP method + endpoint path
  4. Returns a list of classification dicts
  5. Stores results in `context.classifications`

  **Verify:**
  ```sh
  LLM_MOCK=true python3 -c "
  from verify.context import VerificationContext
  from verify.llm_client import LLMClient
  from verify.negotiation.phase1 import run_phase1

  ctx = VerificationContext(
      jira_key='TEST-001', jira_summary='User Profile',
      raw_acceptance_criteria=[
          {'index': 0, 'text': 'User can view their profile', 'checked': False}
      ],
      constitution={'project': {'framework': 'fastapi'}, 'api': {'base_path': '/api/v1'}}
  )
  llm = LLMClient()
  classifications = run_phase1(ctx, llm)
  assert len(classifications) >= 1, 'No classifications produced'
  assert 'type' in classifications[0]
  assert 'actor' in classifications[0]
  print(f'OK: Phase 1 produced {len(classifications)} classifications')
  "
  ```
  Expected: `OK: Phase 1 produced 1 classifications`

- [ ] **Step 2: Add clarifying questions support**

  The Phase 1 output should include a `questions` field — a list of clarifying questions the AI wants to ask the developer. These will be presented by the CLI (Feature 2.7).

  **Verify:**
  ```sh
  LLM_MOCK=true python3 -c "
  from verify.negotiation.phase1 import run_phase1
  from verify.context import VerificationContext
  from verify.llm_client import LLMClient

  ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'User can view their profile', 'checked': False}],
      constitution={})
  result = run_phase1(ctx, LLMClient())
  # Should have classifications and optionally questions
  assert isinstance(result, list)
  print('OK: Phase 1 returns structured output')
  "
  ```

#### Definition of Done

```sh
echo "=== Feature 2.3: Phase 1 ==="
LLM_MOCK=true python3 -c "
from verify.negotiation.phase1 import run_phase1
from verify.context import VerificationContext
from verify.llm_client import LLMClient

ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
    raw_acceptance_criteria=[{'index': 0, 'text': 'AC text', 'checked': False}],
    constitution={})
result = run_phase1(ctx, LLMClient())
assert len(result) >= 1
print('PASS: Phase 1 works')
" && echo "=== Feature 2.3 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

### Feature 2.4: Phase 2 Skill — Happy Path Contract [MVP]

**Story:** The AI proposes the exact success response for each endpoint.
**Depends on:** Feature 2.3 (need classifications)

#### Prerequisites

```sh
LLM_MOCK=true python3 -c "from verify.negotiation.phase1 import run_phase1; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Create Phase 2 skill at `src/verify/negotiation/phase2.py`**

  Implement `run_phase2(context: VerificationContext, llm: LLMClient) -> list[dict]` that:
  1. For each classification with `type == "api_behavior"`, builds a prompt asking the LLM to propose:
     - Success HTTP status code
     - Response body schema (field names, types, required vs optional)
     - Constraints linking response to request context (e.g., `response.id == jwt.sub`)
     - Forbidden fields from constitution's security invariants
  2. Returns postcondition dicts and stores in `context.postconditions`
  3. Includes clarifying questions about missing/nullable fields

  **Verify:**
  ```sh
  LLM_MOCK=true python3 -c "
  from verify.negotiation.phase2 import run_phase2
  from verify.context import VerificationContext
  from verify.llm_client import LLMClient

  ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'User can view their profile', 'checked': False}],
      constitution={})
  ctx.classifications = [{'ac_index': 0, 'type': 'api_behavior', 'actor': 'authenticated_user',
      'interface': {'method': 'GET', 'path': '/api/v1/users/me'}}]

  postconditions = run_phase2(ctx, LLMClient())
  assert len(postconditions) >= 1
  print(f'OK: Phase 2 produced {len(postconditions)} postconditions')
  "
  ```
  Expected: `OK: Phase 2 produced 1 postconditions`

#### Definition of Done

```sh
echo "=== Feature 2.4: Phase 2 ==="
LLM_MOCK=true python3 -c "
from verify.negotiation.phase2 import run_phase2
from verify.context import VerificationContext
from verify.llm_client import LLMClient
ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
    raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}], constitution={})
ctx.classifications = [{'ac_index': 0, 'type': 'api_behavior', 'actor': 'authenticated_user',
    'interface': {'method': 'GET', 'path': '/api/v1/users/me'}}]
result = run_phase2(ctx, LLMClient())
assert len(result) >= 1
print('PASS: Phase 2 works')
" && echo "=== Feature 2.4 COMPLETE ==="
```
- [ ] Step 1 checked off
- [ ] Definition of Done passes

---

### Feature 2.5: Phase 3 Skill — Precondition Formalization [MVP]

**Story:** The AI identifies every precondition that must hold for the happy path to succeed.
**Depends on:** Feature 2.4

#### Prerequisites

```sh
LLM_MOCK=true python3 -c "from verify.negotiation.phase2 import run_phase2; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Create Phase 3 skill at `src/verify/negotiation/phase3.py`**

  Implement `run_phase3(context: VerificationContext, llm: LLMClient) -> list[dict]` that:
  1. For each postcondition, asks the LLM to identify preconditions
  2. Each precondition has: `id` (PRE-001), `description`, `formal` (semi-formal expression like `jwt != null AND jwt.exp > now()`), `category` (authentication, authorization, data_existence, data_state, rate_limit, system_health)
  3. Returns precondition dicts and stores in `context.preconditions`
  4. Includes clarifying questions (e.g., "Does the JWT need specific roles?")

  **Verify:**
  ```sh
  LLM_MOCK=true python3 -c "
  from verify.negotiation.phase3 import run_phase3
  from verify.context import VerificationContext
  from verify.llm_client import LLMClient

  ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}], constitution={})
  ctx.postconditions = [{'ac_index': 0, 'status': 200, 'schema': {'id': 'string'}}]

  preconditions = run_phase3(ctx, LLMClient())
  assert len(preconditions) >= 1
  assert 'id' in preconditions[0]
  assert 'category' in preconditions[0]
  print(f'OK: Phase 3 produced {len(preconditions)} preconditions')
  "
  ```
  Expected: `OK: Phase 3 produced N preconditions`

#### Definition of Done

```sh
echo "=== Feature 2.5: Phase 3 ==="
LLM_MOCK=true python3 -c "
from verify.negotiation.phase3 import run_phase3
from verify.context import VerificationContext
from verify.llm_client import LLMClient
ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
    raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}], constitution={})
ctx.postconditions = [{'ac_index': 0, 'status': 200}]
result = run_phase3(ctx, LLMClient())
assert len(result) >= 1
print('PASS: Phase 3 works')
" && echo "=== Feature 2.5 COMPLETE ==="
```
- [ ] Step 1 checked off
- [ ] Definition of Done passes

---

### Feature 2.6: Phase 4 Skill — Failure Mode Enumeration [MVP]

**Story:** The AI systematically enumerates every failure mode for every precondition with exact error responses.
**Depends on:** Feature 2.5

#### Prerequisites

```sh
LLM_MOCK=true python3 -c "from verify.negotiation.phase3 import run_phase3; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Create Phase 4 skill at `src/verify/negotiation/phase4.py`**

  Implement `run_phase4(context: VerificationContext, llm: LLMClient) -> list[dict]` that:
  1. For each precondition, asks the LLM to enumerate failure modes
  2. Each failure mode has: `id` (FAIL-001), `description`, `violates` (precondition ID), `status` (HTTP status code), `body` (exact error response using the constitution's error format)
  3. The LLM should consider subcategories per precondition type:
     - Authentication: missing token, expired, malformed, wrong issuer, revoked
     - Data existence: never existed, soft-deleted, hard-deleted
     - Data state: each invalid state (inactive, suspended, pending, locked)
  4. Includes security-relevant questions (e.g., "Should 404 vs 410 leak deletion status?")
  5. Stores results in `context.failure_modes`

  **Verify:**
  ```sh
  LLM_MOCK=true python3 -c "
  from verify.negotiation.phase4 import run_phase4
  from verify.context import VerificationContext
  from verify.llm_client import LLMClient

  ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}], constitution={})
  ctx.preconditions = [
      {'id': 'PRE-001', 'description': 'Valid auth', 'category': 'authentication'},
      {'id': 'PRE-002', 'description': 'User exists', 'category': 'data_existence'}
  ]

  failures = run_phase4(ctx, LLMClient())
  assert len(failures) >= 2, f'Expected 2+ failure modes, got {len(failures)}'
  assert all('id' in f for f in failures)
  assert all('violates' in f for f in failures)
  assert all('status' in f for f in failures)
  print(f'OK: Phase 4 produced {len(failures)} failure modes')
  "
  ```
  Expected: `OK: Phase 4 produced N failure modes`

#### Definition of Done

```sh
echo "=== Feature 2.6: Phase 4 ==="
LLM_MOCK=true python3 -c "
from verify.negotiation.phase4 import run_phase4
from verify.context import VerificationContext
from verify.llm_client import LLMClient
ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
    raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}], constitution={})
ctx.preconditions = [{'id': 'PRE-001', 'description': 'Auth', 'category': 'authentication'}]
result = run_phase4(ctx, LLMClient())
assert len(result) >= 1
print('PASS: Phase 4 works')
" && echo "=== Feature 2.6 COMPLETE ==="
```
- [ ] Step 1 checked off
- [ ] Definition of Done passes

---

### Feature 2.7: Interactive CLI Interface [MVP]

**Story:** An interactive interface where the developer sees AI proposals, answers questions, and approves each phase.
**Depends on:** Features 2.3-2.6

#### Prerequisites

```sh
python3 -c "
from verify.negotiation.phase1 import run_phase1
from verify.negotiation.phase2 import run_phase2
from verify.negotiation.phase3 import run_phase3
from verify.negotiation.phase4 import run_phase4
print('OK: all phase skills importable')
"
```

#### Implementation Steps

- [ ] **Step 1: Create CLI module at `src/verify/negotiation/cli.py`**

  Implement `run_negotiation_cli(context: VerificationContext, llm: LLMClient)` that:
  1. Shows a welcome message with the Jira key and AC list
  2. For each phase (1-4), runs the phase skill, displays the AI's output, and asks for developer input
  3. The developer can: type `approve` to advance, provide corrections/answers to questions, or type `skip` to use defaults
  4. Displays a phase indicator: `"=== Phase 2 of 4: Happy Path Contract ==="`
  5. After all phases, displays a summary and asks for final approval
  6. Saves the full negotiation log to `context.negotiation_log`

  **Verify:**
  ```sh
  python3 -c "
  from verify.negotiation.cli import run_negotiation_cli
  print('OK: cli module importable')
  # Full interactive test requires terminal input — manual test only
  "
  ```
  Expected: `OK: cli module importable`

- [ ] **Step 2: Add non-interactive mode for testing**

  Add a `run_negotiation_auto(context, llm, answers=None)` function that runs all phases without prompting, using provided answers or defaults. This is essential for CI/testing.

  **Verify:**
  ```sh
  LLM_MOCK=true python3 -c "
  from verify.negotiation.cli import run_negotiation_auto
  from verify.context import VerificationContext
  from verify.llm_client import LLMClient

  ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'User can view their profile', 'checked': False}],
      constitution={'project': {'framework': 'fastapi'}, 'api': {'base_path': '/api/v1'}})
  llm = LLMClient()

  run_negotiation_auto(ctx, llm)
  assert len(ctx.classifications) >= 1, 'No classifications after auto-negotiation'
  assert len(ctx.negotiation_log) >= 1, 'No log entries'
  print(f'OK: auto-negotiation completed {len(ctx.negotiation_log)} exchanges')
  "
  ```
  Expected: `OK: auto-negotiation completed N exchanges`

#### Definition of Done

```sh
echo "=== Feature 2.7: CLI Interface ==="
LLM_MOCK=true python3 -c "
from verify.negotiation.cli import run_negotiation_auto
from verify.context import VerificationContext
from verify.llm_client import LLMClient
ctx = VerificationContext(jira_key='T-1', jira_summary='Test',
    raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}],
    constitution={})
run_negotiation_auto(ctx, LLMClient())
assert len(ctx.negotiation_log) >= 1
print('PASS: auto-negotiation works')
" && echo "=== Feature 2.7 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

