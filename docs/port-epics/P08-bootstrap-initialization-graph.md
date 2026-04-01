# Epic P8: Bootstrap & Initialization Graph

**Priority:** 8 (Medium-Low)
**Status:** Done
**Ported From:** `claw-code/src/bootstrap_graph.py` (BootstrapGraph with phased stages), `claw-code/src/setup.py` (WorkspaceSetup, prefetch, deferred init)
**Integration Target:** `src/verify/negotiation/web.py`, `src/verify/negotiation/cli.py`

## Rationale

magic-agents initializes its web server and CLI with ad-hoc setup code scattered across entry points — loading constitution, initializing the LLM client, checking environment variables, registering skills, and starting the session store. There is no structured startup sequence, making it hard to diagnose initialization failures or add new startup steps. claw-code's `BootstrapGraph` defines explicit stages that execute in a predictable order with dependency resolution.

---

## Story P8.1: Define BootstrapGraph with Ordered Stages

### EARS Requirement

> The system **shall** define a `BootstrapGraph` with ordered stages: `env_validation`, `constitution_load`, `llm_client_init`, `skill_registration`, `session_store_init`, `jira_client_init`, `web_server_start`, where each stage has a `name`, `description`, `dependencies`, and `handler` callable.

### Design by Contract

**Preconditions:**
- Each stage name is unique.
- Dependencies form a DAG (no cycles).
- Handler callables accept a `BootstrapContext` dict and return a `StageResult`.

**Postconditions:**
- Stages execute in topological order.
- Each stage's result (success/failed/skipped) is recorded in `BootstrapReport`.
- If a stage fails, dependent stages are skipped.
- `BootstrapReport` includes wall clock time per stage.

**Invariants:**
- No stage executes before all its dependencies complete successfully.
- The graph is deterministic: same inputs = same execution order.
- Failed stages do not leave partially initialized state.

### Acceptance Criteria

- [x]`BootstrapStage` dataclass with `name`, `description`, `dependencies`, `handler`.
- [x]`BootstrapGraph` with `add_stage()`, `execute()`, `report()` methods.
- [x]Topological sort respects dependencies.
- [x]Failed stages cause dependent stages to be skipped.

### How to Test

```python
def test_bootstrap_order():
    graph = BootstrapGraph()
    order = []
    graph.add_stage(BootstrapStage(name="a", dependencies=[], handler=lambda ctx: order.append("a")))
    graph.add_stage(BootstrapStage(name="b", dependencies=["a"], handler=lambda ctx: order.append("b")))
    graph.execute({})
    assert order[0] == "a"

def test_failed_stage_skips_dependents():
    graph = BootstrapGraph()
    graph.add_stage(BootstrapStage(name="a", dependencies=[], handler=lambda ctx: 1/0))
    graph.add_stage(BootstrapStage(name="b", dependencies=["a"], handler=lambda ctx: None))
    report = graph.execute({})
    assert report.stages["a"].status == "failed"
    assert report.stages["b"].status == "skipped"

def test_cycle_detection():
    graph = BootstrapGraph()
    graph.add_stage(BootstrapStage(name="a", dependencies=["b"], handler=lambda ctx: None))
    graph.add_stage(BootstrapStage(name="b", dependencies=["a"], handler=lambda ctx: None))
    with pytest.raises(ValueError, match="cycle"):
        graph.execute({})
```

---

## Story P8.2: Replace Ad-Hoc Initialization with Bootstrap Graph

### EARS Requirement

> **When** the web server or CLI starts, the system **shall** execute the `BootstrapGraph` instead of inline initialization code, and **if** any required stage fails, the system **shall** exit with a diagnostic message listing the failed stage and its error.

### Design by Contract

**Preconditions:**
- The `BootstrapGraph` is populated with all required stages.
- Entry points call `graph.execute()` before serving requests.

**Postconditions:**
- All stages execute in dependency order.
- On success, the application is fully initialized.
- On failure, a formatted diagnostic is printed including failed stage name, error, and skipped dependents.
- The process exits with code 1 on bootstrap failure.

**Invariants:**
- No requests served before bootstrap completes.
- Bootstrap report available at `GET /api/health/bootstrap` after startup.

### Acceptance Criteria

- [x]`run_web.py` uses `BootstrapGraph.execute()` for initialization.
- [x]`run_negotiation.py` uses `BootstrapGraph.execute()` for initialization.
- [x]Bootstrap failure produces readable diagnostic on stderr.
- [x]`GET /api/health/bootstrap` returns the report with per-stage timing.

### How to Test

```python
def test_web_bootstrap_success(client):
    resp = client.get("/api/health/bootstrap")
    assert resp.status_code == 200
    report = resp.json()
    assert all(s["status"] == "success" for s in report["stages"].values())

def test_bootstrap_fails_on_missing_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MOCK", "false")
    graph = build_bootstrap_graph()
    report = graph.execute({})
    assert report.stages["llm_client_init"].status == "failed"
```

---

## Story P8.3: Health Check Endpoint with Stage Status

### EARS Requirement

> The system **shall** expose a `GET /api/health` endpoint that returns the status of each bootstrap stage, total bootstrap time, and current readiness state.

### Design by Contract

**Preconditions:**
- The bootstrap graph has been executed.

**Postconditions:**
- Response includes: `ready` (boolean), `total_bootstrap_ms` (integer), `stages` (object mapping stage names to `{status, duration_ms, error?}`).
- `ready` is `True` only if all required stages succeeded.

**Invariants:**
- Always available (even during bootstrap failure) for load balancer health checks.
- Stable JSON schema.

### Acceptance Criteria

- [x]`GET /api/health` returns 200 with readiness and stage status.
- [x]`ready: false` when any required stage failed.
- [x]Each stage includes `duration_ms`.
- [x]Failed stages include an `error` field.

### How to Test

```python
def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "ready" in data
    assert "stages" in data
    assert "total_bootstrap_ms" in data
```
