# Epic P1: Token Budget Enforcement & Cost Tracking

**Priority:** 1 (Critical)
**Status:** Done
**Ported From:** `claw-code/src/cost_tracker.py`, `claw-code/src/query_engine.py` (`QueryEngineConfig.max_budget_tokens`)
**Integration Target:** `src/verify/backpressure.py`, `src/verify/llm_client.py`, `src/verify/negotiation/harness.py`

## Rationale

magic-agents runs a 7-phase AI negotiation pipeline where each phase can involve multiple LLM turns (initial generation + developer feedback revisions). Without enforced token budgets, a single negotiation session can silently consume unbounded tokens and cost. The `BackPressureController` already exists in `backpressure.py` with hard/soft limits for API calls, tokens, wall clock time, and per-phase retries, but it was **not wired into the harness or LLM client**. claw-code's `QueryEngineConfig` demonstrates how budget enforcement integrates with a query engine — checking token projections before each turn and halting with a `max_budget_reached` stop reason. This epic wires the existing controller into the live pipeline and adds per-phase cost reporting.

---

## Story P1.1: Wire BackPressureController into LLMClient

### EARS Requirement

> **When** the `LLMClient` completes an API call, the system **shall** record the input and output token counts on the session's `BackPressureController` via `record_api_call(tokens_in, tokens_out)`.

### Design by Contract

**Preconditions:**
- A `BackPressureController` instance is associated with the current session (injected into `LLMClient` at construction or via setter).
- The Anthropic SDK response object contains `usage.input_tokens` and `usage.output_tokens` fields.

**Postconditions:**
- `controller.api_calls` is incremented by 1.
- `controller.tokens_used` is incremented by `tokens_in + tokens_out`.
- If a hard limit is exceeded, `BackPressureLimitExceeded` is raised before the response is returned to the caller.

**Invariants:**
- `controller.tokens_used` is always equal to the sum of all `tokens_in + tokens_out` values passed to `record_api_call` since the controller was created.
- `controller.api_calls` is always equal to the number of successful API calls made through this client.
- Mock mode (`LLM_MOCK=true`) still records calls with zero tokens (does not skip tracking).

### Acceptance Criteria

- [x] `LLMClient.__init__` accepts an optional `BackPressureController` parameter.
- [x] Every `chat()` and `chat_multi()` call invokes `record_api_call` after receiving the response.
- [x] When `BackPressureLimitExceeded` is raised, the exception propagates to the caller without returning partial results.
- [x] In mock mode, `record_api_call(0, 0)` is called for each mock response.

### How to Test

```python
def test_llm_client_records_tokens():
    controller = BackPressureController(max_tokens=1000)
    client = LLMClient(backpressure=controller)
    client.chat("system prompt", "user message")
    assert controller.api_calls == 1
    assert controller.tokens_used > 0

def test_llm_client_raises_on_budget_exceeded():
    controller = BackPressureController(max_api_calls=1)
    client = LLMClient(backpressure=controller)
    client.chat("system", "msg1")
    with pytest.raises(BackPressureLimitExceeded):
        client.chat("system", "msg2")
```

---

## Story P1.2: Enforce Budget Checks Before Each Negotiation Turn

### EARS Requirement

> **While** a negotiation phase is executing, the system **shall** call `controller.can_proceed()` before each LLM invocation and halt the phase with a `budget_exceeded` status if the check returns `False`.

### Design by Contract

**Preconditions:**
- The `NegotiationHarness` has a reference to the session's `BackPressureController`.
- The phase skill function (`run_phase_N`) is about to invoke `llm.chat()` or `llm.chat_multi()`.

**Postconditions:**
- If `can_proceed()` returns `False`, the phase exits immediately with a structured error containing the usage summary from `controller.get_usage_summary()`.
- The harness does NOT advance to the next phase.
- The checkpoint is saved with the current partial state so the session can be resumed after budget adjustment.

**Invariants:**
- No LLM call is ever made when `can_proceed()` returns `False`.
- Budget check overhead is O(1) per turn (no database or network calls).

### Acceptance Criteria

- [x] `NegotiationHarness` constructor accepts an optional `BackPressureController`.
- [x] Before each `llm.chat()` / `llm.chat_multi()` call within a phase, `can_proceed()` is checked.
- [x] When budget is exceeded, the harness returns a structured response with `status: "budget_exceeded"` and the usage summary.
- [x] A checkpoint is saved so the session can be resumed.

### How to Test

```python
def test_phase_halts_on_budget():
    controller = BackPressureController(max_api_calls=2)
    controller.api_calls = 2
    harness = NegotiationHarness(context, backpressure=controller)
    result = harness.run_current_phase(llm)
    assert result["status"] == "budget_exceeded"
    assert "api_calls" in result["usage_summary"]
```

---

## Story P1.3: Per-Phase Cost Reporting in Usage Summary

### EARS Requirement

> **When** a negotiation phase completes (success or failure), the system **shall** emit a cost report containing the phase name, API call count, token count (input + output), wall clock duration, and retry count for that phase.

### Design by Contract

**Preconditions:**
- The `BackPressureController` has been recording calls throughout the phase.
- The phase has a well-defined start and end point (tracked by the harness).

**Postconditions:**
- A `PhaseCostReport` dataclass is appended to the session's cost history.
- The report contains: `phase_name`, `api_calls`, `tokens_in`, `tokens_out`, `wall_clock_seconds`, `retries`, `status` (success/failed/budget_exceeded).
- The cumulative session cost report is updated.

**Invariants:**
- The sum of all `PhaseCostReport.tokens_in + tokens_out` across phases equals `controller.tokens_used`.
- The sum of all `PhaseCostReport.api_calls` across phases equals `controller.api_calls`.

### Acceptance Criteria

- [x] A `PhaseCostReport` dataclass is defined with the fields listed above.
- [x] After each phase completes, a report is generated and stored on the session state.
- [x] `PhaseCostReport.aggregate()` returns a summary across all phases.
- [x] The web UI `/api/status` endpoint includes the cost summary.

### How to Test

```python
def test_phase_cost_report():
    controller = BackPressureController()
    harness = NegotiationHarness(context, backpressure=controller)
    harness.run_current_phase(llm)
    reports = harness.cost_reports
    assert len(reports) == 1
    assert reports[0].phase_name == "phase_1"
    assert reports[0].api_calls >= 1
    assert reports[0].status == "success"
```

---

## Story P1.4: Configurable Budget Limits via Constitution

### EARS Requirement

> **Where** a `constitution.yaml` file defines a `budget` section, the system **shall** initialize the `BackPressureController` with the limits specified in that section instead of the defaults.

### Design by Contract

**Preconditions:**
- `constitution.yaml` is loaded and parsed before the negotiation session starts.
- The `budget` section, if present, contains valid integer values for any subset of: `max_api_calls`, `max_tokens`, `max_wall_clock_seconds`, `max_retries_per_phase`, `warn_api_calls`, `warn_tokens`.

**Postconditions:**
- The `BackPressureController` is initialized with overridden values for any keys present in the `budget` section.
- Keys not present in the `budget` section use the dataclass defaults.
- If the `budget` section is absent, all defaults are used.

**Invariants:**
- All limit values are positive integers.
- `warn_*` thresholds are always less than or equal to their corresponding `max_*` limits.

### Acceptance Criteria

- [x] `constitution.yaml` schema supports an optional `budget` section.
- [x] `BackPressureController.from_constitution(constitution)` class method is implemented.
- [x] Invalid values (negative, non-integer, warn > max) raise `ValueError` at startup.
- [x] When no `budget` section exists, defaults are used unchanged.

### How to Test

```python
def test_controller_from_constitution():
    constitution = {"budget": {"max_api_calls": 100, "max_tokens": 1_000_000}}
    controller = BackPressureController.from_constitution(constitution)
    assert controller.max_api_calls == 100
    assert controller.max_tokens == 1_000_000
    assert controller.max_wall_clock_seconds == 600  # default

def test_controller_rejects_negative():
    constitution = {"budget": {"max_api_calls": -1}}
    with pytest.raises(ValueError):
        BackPressureController.from_constitution(constitution)
```
