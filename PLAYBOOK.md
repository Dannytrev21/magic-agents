# Claude Code Implementation Playbook
## Project: Intent-to-Verification Spec Engine ("Magic Agents")

**Stack:** Python 3.11+ / FastAPI / pytest
**MVP Scope:** Epics 0-4 + Stories 6.1-6.2
**Source docs:** `ac-to-specs-plan.md`, `user-stories.md`

### How to Use This Playbook

Work through features **sequentially within each epic**. Each feature has:
1. **Prerequisites** — run these checks before starting; if any fail, the dependency isn't ready
2. **Implementation Steps** — each with an inline `Verify` block containing an executable command
3. **Definition of Done** — a smoke-test script that re-verifies everything for the feature

Check off `- [ ]` boxes as you complete each step. Do not skip verification steps.

### Project Structure (Target)

```
magic-agents/
├── pyproject.toml
├── src/
│   ├── dummy_app/          # The target app tests run against
│   │   ├── __init__.py
│   │   └── main.py
│   └── verify/             # The verification pipeline
│       ├── __init__.py
│       ├── context.py      # VerificationContext dataclass
│       ├── generator.py    # Template-based test generator
│       ├── runner.py        # Test runner + JUnit XML parser
│       ├── evaluator.py     # Spec-to-verdict evaluation
│       ├── pipeline.py      # End-to-end orchestrator
│       ├── jira_client.py   # Jira REST API client
│       ├── llm_client.py    # Claude/Anthropic LLM client
│       ├── negotiation/     # AI negotiation phases
│       │   ├── __init__.py
│       │   ├── harness.py
│       │   ├── phase1.py
│       │   ├── phase2.py
│       │   ├── phase3.py
│       │   ├── phase4.py
│       │   └── cli.py
│       ├── compiler.py      # VerificationContext → spec YAML
│       └── skills/          # Verification artifact generators
│           ├── __init__.py
│           ├── framework.py
│           ├── pytest_skill.py
│           └── tag_enforcer.py
├── tests/
│   ├── conftest.py
│   └── test_*.py
├── .verify/
│   ├── specs/
│   ├── generated/
│   └── results/
├── PLAYBOOK.md
├── ac-to-specs-plan.md
└── user-stories.md
```

---

## Epic 0: Bullet Tracer [MVP]

**Goal:** Prove the end-to-end concept with a single hardcoded thread: spec in → tests generated → tests executed → verdicts printed.
**Depends on:** Nothing — this is the foundation.
**After this epic:** One command runs the full pipeline with hardcoded data and prints pass/fail verdicts.

---

### Feature 0.1: Dummy FastAPI Application [MVP]

**Story:** A simple pre-written application with one testable endpoint so generated tests have a target to run against.
**Depends on:** None

#### Prerequisites

```sh
# Verify Python 3.11+ is available
python3 --version
# Expected: Python 3.11.x or higher
```

#### Implementation Steps

- [ ] **Step 1: Create project skeleton with pyproject.toml**

  Create `pyproject.toml` with project metadata and dependencies:
  - Runtime: `fastapi`, `uvicorn`
  - Dev/test: `pytest`, `pytest-cov`, `httpx` (FastAPI test client), `pyyaml`

  Use `src` layout with two packages: `dummy_app` and `verify`.

  **Verify:**
  ```sh
  test -f pyproject.toml && python3 -c "
  import tomllib
  with open('pyproject.toml', 'rb') as f:
      config = tomllib.load(f)
  deps = config['project']['dependencies']
  assert 'fastapi' in str(deps), 'Missing fastapi'
  print('OK: pyproject.toml valid with dependencies')
  "
  ```
  Expected: `OK: pyproject.toml valid with dependencies`

- [ ] **Step 2: Create source package directories**

  Create:
  - `src/dummy_app/__init__.py` (empty)
  - `src/dummy_app/main.py` (FastAPI app placeholder)
  - `src/verify/__init__.py` (empty)
  - `tests/__init__.py` (empty)
  - `tests/conftest.py` (empty for now)

  **Verify:**
  ```sh
  test -f src/dummy_app/__init__.py && \
  test -f src/dummy_app/main.py && \
  test -f src/verify/__init__.py && \
  test -d tests && \
  echo "OK: package structure exists"
  ```
  Expected: `OK: package structure exists`

- [ ] **Step 3: Install project in editable mode**

  **Verify:**
  ```sh
  pip install -e ".[dev]" && python3 -c "import dummy_app; print('OK: dummy_app importable')"
  ```
  Expected: `OK: dummy_app importable`

- [ ] **Step 4: Implement GET /api/v1/users/me with hardcoded response**

  In `src/dummy_app/main.py`, create a FastAPI app with:
  - A simple auth dependency that checks for `Authorization: Bearer <token>` header. If missing/empty → return 401 with `{"error": "unauthorized", "message": "Missing or invalid authorization header"}`.
  - `GET /api/v1/users/me` returns 200 with `{"id": "user-001", "email": "demo@example.com", "displayName": "Demo User"}` when auth header is present.
  - If the token value is `"not-found-user"`, return 404 with `{"error": "user_not_found", "message": "User not found"}` (to support failure mode testing in Feature 0.3).

  **Verify:**
  ```sh
  python3 -c "
  from fastapi.testclient import TestClient
  from dummy_app.main import app

  client = TestClient(app)

  # Test 401 without auth
  r = client.get('/api/v1/users/me')
  assert r.status_code == 401, f'Expected 401, got {r.status_code}'
  assert r.json()['error'] == 'unauthorized'

  # Test 200 with auth
  r = client.get('/api/v1/users/me', headers={'Authorization': 'Bearer valid-token'})
  assert r.status_code == 200, f'Expected 200, got {r.status_code}'
  body = r.json()
  assert body['id'] == 'user-001'
  assert body['email'] == 'demo@example.com'
  assert body['displayName'] == 'Demo User'

  # Test 404 with not-found token
  r = client.get('/api/v1/users/me', headers={'Authorization': 'Bearer not-found-user'})
  assert r.status_code == 404, f'Expected 404, got {r.status_code}'
  assert r.json()['error'] == 'user_not_found'

  print('OK: all endpoint behaviors correct')
  "
  ```
  Expected: `OK: all endpoint behaviors correct`

- [ ] **Step 5: Configure pytest and create a placeholder test**

  Add pytest config to `pyproject.toml` (testpaths, pythonpath). Create `tests/test_dummy_app.py` with one test that hits the endpoint via `TestClient` to confirm pytest works.

  **Verify:**
  ```sh
  python3 -m pytest tests/test_dummy_app.py -v 2>&1 | tail -5
  ```
  Expected: `1 passed` and exit code 0.

- [ ] **Step 6: Create .verify/ directory structure**

  Create directories: `.verify/`, `.verify/specs/`, `.verify/generated/`, `.verify/results/`. Add `.gitkeep` files so git tracks empty dirs.

  **Verify:**
  ```sh
  test -d .verify/specs && test -d .verify/generated && test -d .verify/results && \
  echo "OK: .verify directory structure"
  ```
  Expected: `OK: .verify directory structure`

#### Definition of Done

```sh
echo "=== Feature 0.1: Dummy Application ==="
python3 -c "
from fastapi.testclient import TestClient
from dummy_app.main import app
c = TestClient(app)
assert c.get('/api/v1/users/me').status_code == 401, 'FAIL: 401'
assert c.get('/api/v1/users/me', headers={'Authorization': 'Bearer t'}).status_code == 200, 'FAIL: 200'
assert c.get('/api/v1/users/me', headers={'Authorization': 'Bearer not-found-user'}).status_code == 404, 'FAIL: 404'
print('PASS: endpoint behaviors')
" && \
python3 -m pytest tests/test_dummy_app.py -q && \
test -d .verify/specs && \
echo "=== Feature 0.1 COMPLETE ==="
```
- [ ] All 6 steps checked off
- [ ] Definition of Done script passes

---

### Feature 0.2: Hardcoded Spec YAML [MVP]

**Story:** A manually-written spec YAML file for the dummy app's endpoint so downstream features have a concrete spec to consume.
**Depends on:** Feature 0.1 (need to know the endpoint shape)

#### Prerequisites

```sh
python3 -c "
from fastapi.testclient import TestClient
from dummy_app.main import app
c = TestClient(app)
assert c.get('/api/v1/users/me', headers={'Authorization': 'Bearer t'}).status_code == 200
print('OK: dummy app endpoint exists')
"
```

#### Implementation Steps

- [ ] **Step 1: Create the spec YAML file at `.verify/specs/DEMO-001.yaml`**

  Write a hand-crafted spec following the schema from `ac-to-specs-plan.md` Section 4.2. The spec must contain:

  **meta:** spec_version, jira_key (`DEMO-001`), generated_at, status (`approved`)

  **requirements:** One requirement block `REQ-001` with:
  - `ac_checkbox: 0`, `ac_text: "User can view their profile"`
  - `type: api_behavior`
  - **contract.interface:** `GET /api/v1/users/me`, auth `jwt_bearer`
  - **contract.success:** status 200, schema with `id`, `email`, `displayName` (all required strings), `forbidden_fields: [password, ssn]`
  - **contract.preconditions:**
    - `PRE-001`: valid auth header present (category: authentication)
    - `PRE-002`: user exists for token (category: data_existence)
  - **contract.failures:**
    - `FAIL-001`: no auth header → 401 `{"error": "unauthorized", "message": "Missing or invalid authorization header"}`
    - `FAIL-002`: user not found → 404 `{"error": "user_not_found", "message": "User not found"}`
  - **contract.invariants:**
    - `INV-001`: response must never contain `password` or `ssn` fields (type: security)
  - **verification:** `[{refs: [success, FAIL-001, FAIL-002, INV-001], skill: pytest_unit_test, output: ".verify/generated/test_demo_001.py"}]`

  **traceability.ac_mappings:** One mapping:
  - `ac_checkbox: 0`, `pass_condition: ALL_PASS`
  - `required_verifications:` refs for `REQ-001.success`, `REQ-001.FAIL-001`, `REQ-001.FAIL-002`, `REQ-001.INV-001`, all with `verification_type: test_result`

  **Verify:**
  ```sh
  python3 -c "
  import yaml
  with open('.verify/specs/DEMO-001.yaml') as f:
      spec = yaml.safe_load(f)

  # Check structure
  assert spec['meta']['jira_key'] == 'DEMO-001', 'Bad jira_key'
  assert len(spec['requirements']) >= 1, 'No requirements'

  req = spec['requirements'][0]
  assert req['id'] == 'REQ-001', 'Bad requirement id'
  assert req['contract']['interface']['method'] == 'GET', 'Bad method'
  assert req['contract']['interface']['path'] == '/api/v1/users/me', 'Bad path'
  assert req['contract']['success']['status'] == 200, 'Bad success status'
  assert len(req['contract']['failures']) >= 2, 'Need at least 2 failure modes'
  assert len(req['contract']['invariants']) >= 1, 'Need at least 1 invariant'
  assert len(req['verification']) >= 1, 'No verification routing'

  # Check traceability
  assert 'traceability' in spec, 'Missing traceability'
  ac_map = spec['traceability']['ac_mappings']
  assert len(ac_map) >= 1, 'No ac_mappings'
  assert ac_map[0]['pass_condition'] == 'ALL_PASS', 'Bad pass_condition'
  assert len(ac_map[0]['required_verifications']) >= 4, 'Need 4+ verification refs'

  print('OK: spec YAML is valid and complete')
  "
  ```
  Expected: `OK: spec YAML is valid and complete`

#### Definition of Done

```sh
echo "=== Feature 0.2: Hardcoded Spec ==="
python3 -c "
import yaml
spec = yaml.safe_load(open('.verify/specs/DEMO-001.yaml'))
assert spec['meta']['jira_key'] == 'DEMO-001'
req = spec['requirements'][0]
assert req['contract']['interface']['path'] == '/api/v1/users/me'
assert len(req['contract']['failures']) >= 2
assert len(spec['traceability']['ac_mappings'][0]['required_verifications']) >= 4
print('PASS: spec structure valid')
" && echo "=== Feature 0.2 COMPLETE ==="
```
- [ ] Step 1 checked off
- [ ] Definition of Done script passes

---

### Feature 0.3: Template-Based Test Generator [MVP]

**Story:** A script that reads the spec YAML and generates a pytest test file with tagged test methods.
**Depends on:** Features 0.1 (app to test against), 0.2 (spec to read)

#### Prerequisites

```sh
python3 -c "
import yaml
spec = yaml.safe_load(open('.verify/specs/DEMO-001.yaml'))
print(f'OK: spec has {len(spec[\"requirements\"])} requirements')
" && python3 -c "
from dummy_app.main import app
print('OK: dummy app importable')
"
```

#### Implementation Steps

- [ ] **Step 1: Create the generator module at `src/verify/generator.py`**

  Implement a function `generate_tests(spec_path: str) -> str` that:
  1. Reads the spec YAML
  2. Extracts the requirement's contract (success, failures, invariants)
  3. For each contract element, generates a pytest test function
  4. Each test function name contains the spec ref in brackets: `test_REQ_001_success`, `test_REQ_001_FAIL_001`, etc.
  5. Each test function has a `@pytest.mark.spec("REQ-001.success")` marker (or equivalent tagging via the test name including `[REQ-001.success]`)
  6. Returns the generated test file content as a string

  For the bullet tracer, use **string templates** — no AI. The generator reads the spec and fills in a template. Each test uses `FastAPI.TestClient` to hit the endpoint and assert status codes and response bodies.

  The generated test file should:
  - Import `TestClient` from `fastapi.testclient` and `app` from `dummy_app.main`
  - For `success`: send GET with auth header, assert 200, assert all required fields present in response
  - For `FAIL-001`: send GET without auth header, assert 401, assert error body matches
  - For `FAIL-002`: send GET with `Bearer not-found-user`, assert 404, assert error body matches
  - For `INV-001`: send GET with auth, assert `password` and `ssn` NOT in response keys

  **Verify:**
  ```sh
  python3 -c "
  from verify.generator import generate_tests
  content = generate_tests('.verify/specs/DEMO-001.yaml')
  assert 'REQ-001.success' in content or 'REQ_001_success' in content, 'Missing success test'
  assert 'FAIL-001' in content or 'FAIL_001' in content, 'Missing FAIL-001 test'
  assert 'FAIL-002' in content or 'FAIL_002' in content, 'Missing FAIL-002 test'
  assert 'INV-001' in content or 'INV_001' in content, 'Missing INV-001 test'
  print('OK: generator produces tests for all spec refs')
  "
  ```
  Expected: `OK: generator produces tests for all spec refs`

- [ ] **Step 2: Add file-writing capability**

  Implement `generate_and_write(spec_path: str) -> str` that calls `generate_tests`, writes the output to the path specified in the spec's `verification[].output` field, and returns the output path.

  **Verify:**
  ```sh
  python3 -c "
  from verify.generator import generate_and_write
  output_path = generate_and_write('.verify/specs/DEMO-001.yaml')
  import os
  assert os.path.exists(output_path), f'File not created at {output_path}'
  print(f'OK: test file written to {output_path}')
  "
  ```
  Expected: `OK: test file written to .verify/generated/test_demo_001.py`

- [ ] **Step 3: Verify generated tests actually pass against the dummy app**

  **Verify:**
  ```sh
  python3 -c "from verify.generator import generate_and_write; generate_and_write('.verify/specs/DEMO-001.yaml')"
  python3 -m pytest .verify/generated/test_demo_001.py -v 2>&1 | tail -10
  ```
  Expected: All 4 tests pass (success, FAIL-001, FAIL-002, INV-001).

#### Definition of Done

```sh
echo "=== Feature 0.3: Test Generator ==="
python3 -c "
from verify.generator import generate_and_write
path = generate_and_write('.verify/specs/DEMO-001.yaml')
print(f'PASS: generated {path}')
" && \
python3 -m pytest .verify/generated/test_demo_001.py -v --tb=short 2>&1 | tail -10 && \
echo "=== Feature 0.3 COMPLETE ==="
```
- [ ] All 3 steps checked off
- [ ] Generated tests pass against the dummy app

---

### Feature 0.4: Test Runner + JUnit XML Parser [MVP]

**Story:** A script that executes generated tests and parses results into a structured format with tags extracted.
**Depends on:** Feature 0.3 (need generated tests to run)

#### Prerequisites

```sh
test -f .verify/generated/test_demo_001.py && echo "OK: generated test file exists" || \
  python3 -c "from verify.generator import generate_and_write; generate_and_write('.verify/specs/DEMO-001.yaml'); print('OK: regenerated')"
```

#### Implementation Steps

- [ ] **Step 1: Create the runner module at `src/verify/runner.py`**

  Implement `run_tests(test_path: str, results_dir: str) -> str` that:
  1. Runs pytest on the given test file with `--junitxml={results_dir}/results.xml` flag
  2. Uses `subprocess.run` to execute pytest
  3. Returns the path to the JUnit XML results file
  4. Captures and logs stdout/stderr

  **Verify:**
  ```sh
  python3 -c "
  from verify.runner import run_tests
  xml_path = run_tests('.verify/generated/test_demo_001.py', '.verify/results')
  import os
  assert os.path.exists(xml_path), f'No results file at {xml_path}'
  print(f'OK: test results at {xml_path}')
  "
  ```
  Expected: `OK: test results at .verify/results/results.xml`

- [ ] **Step 2: Implement JUnit XML parser**

  Implement `parse_junit_xml(xml_path: str) -> list[dict]` that:
  1. Parses JUnit XML using `xml.etree.ElementTree`
  2. For each `<testcase>`, extracts: `name`, `classname`, `status` (passed/failed/errored/skipped), `failure_message`
  3. Extracts spec ref tags from the test name. Look for patterns like `REQ_001_success` and convert to `REQ-001.success`, or extract from `[REQ-001.success]` brackets if present.
  4. Returns a list of dicts: `[{"name": str, "tags": [str], "status": str, "failure_message": str}]`

  **Verify:**
  ```sh
  python3 -c "
  from verify.runner import run_tests, parse_junit_xml
  xml_path = run_tests('.verify/generated/test_demo_001.py', '.verify/results')
  results = parse_junit_xml(xml_path)
  assert len(results) >= 4, f'Expected 4+ test cases, got {len(results)}'
  tagged = [r for r in results if len(r['tags']) > 0]
  assert len(tagged) >= 4, f'Expected 4+ tagged tests, got {len(tagged)}'
  for r in results:
      assert r['status'] == 'passed', f'Test {r[\"name\"]} {r[\"status\"]}: {r.get(\"failure_message\", \"\")}'
  print(f'OK: parsed {len(results)} test cases, all passed, all tagged')
  "
  ```
  Expected: `OK: parsed 4 test cases, all passed, all tagged`

- [ ] **Step 3: Add unified output function**

  Implement `run_and_parse(test_path: str, results_dir: str) -> dict` that runs tests and parses results in one call, returning `{"test_cases": [...]}`.

  Optionally, write the parsed results to a JSON file at `{results_dir}/parsed_results.json`.

  **Verify:**
  ```sh
  python3 -c "
  from verify.runner import run_and_parse
  results = run_and_parse('.verify/generated/test_demo_001.py', '.verify/results')
  assert 'test_cases' in results
  assert len(results['test_cases']) >= 4
  tags = [t for tc in results['test_cases'] for t in tc['tags']]
  assert 'REQ-001.success' in tags, f'Missing REQ-001.success in tags: {tags}'
  assert 'REQ-001.FAIL-001' in tags, f'Missing REQ-001.FAIL-001 in tags: {tags}'
  print(f'OK: run_and_parse returned {len(results[\"test_cases\"])} cases with correct tags')
  "
  ```
  Expected: `OK: run_and_parse returned 4 cases with correct tags`

#### Definition of Done

```sh
echo "=== Feature 0.4: Test Runner + Parser ==="
python3 -c "
from verify.runner import run_and_parse
results = run_and_parse('.verify/generated/test_demo_001.py', '.verify/results')
cases = results['test_cases']
assert len(cases) >= 4, f'FAIL: only {len(cases)} cases'
assert all(c['status'] == 'passed' for c in cases), 'FAIL: not all passed'
tags = {t for c in cases for t in c['tags']}
for ref in ['REQ-001.success', 'REQ-001.FAIL-001', 'REQ-001.FAIL-002', 'REQ-001.INV-001']:
    assert ref in tags, f'FAIL: missing tag {ref}'
print('PASS: all test cases parsed with correct tags')
" && echo "=== Feature 0.4 COMPLETE ==="
```
- [ ] All 3 steps checked off
- [ ] Definition of Done script passes

---

### Feature 0.5: Evaluator — Spec Refs to AC Checkbox Verdicts [MVP]

**Story:** A script that reads the spec's traceability map and parsed test results, producing a verdict for each AC checkbox.
**Depends on:** Features 0.2 (spec with traceability map), 0.4 (parsed test results)

#### Prerequisites

```sh
python3 -c "
import yaml
spec = yaml.safe_load(open('.verify/specs/DEMO-001.yaml'))
assert 'traceability' in spec
print(f'OK: spec has {len(spec[\"traceability\"][\"ac_mappings\"])} AC mappings')
"
```

#### Implementation Steps

- [ ] **Step 1: Create the evaluator module at `src/verify/evaluator.py`**

  Implement `evaluate_spec(spec_path: str, test_results: dict) -> list[dict]` that:
  1. Loads the spec YAML and reads `traceability.ac_mappings`
  2. For each `ac_mapping`, iterates through `required_verifications`
  3. For each verification with `verification_type: test_result`, looks up the `ref` in the test results by matching against the `tags` list
  4. A ref is **passed** if a test with a matching tag has `status == "passed"`
  5. A ref is **failed** if no matching test exists OR the matching test failed
  6. Evaluates `pass_condition`:
     - `ALL_PASS`: checkbox passes only if ALL required refs passed
     - `ANY_PASS`: passes if at least one ref passed
     - `PERCENTAGE`: passes if pass rate >= threshold
  7. Returns a list of verdict dicts:
     ```python
     [{
       "ac_checkbox": int,
       "ac_text": str,
       "passed": bool,
       "pass_condition": str,
       "summary": "4/4 verifications passed",
       "evidence": [{"ref": str, "passed": bool, "details": str}]
     }]
     ```

  **Verify:**
  ```sh
  python3 -c "
  from verify.evaluator import evaluate_spec
  from verify.runner import run_and_parse

  test_results = run_and_parse('.verify/generated/test_demo_001.py', '.verify/results')
  verdicts = evaluate_spec('.verify/specs/DEMO-001.yaml', test_results)

  assert len(verdicts) >= 1, 'No verdicts produced'
  v = verdicts[0]
  assert v['ac_checkbox'] == 0
  assert v['passed'] == True, f'Expected pass, got evidence: {v[\"evidence\"]}'
  assert '4/4' in v['summary'] or 'passed' in v['summary']
  print(f'OK: AC checkbox 0 verdict: {v[\"summary\"]}')
  "
  ```
  Expected: `OK: AC checkbox 0 verdict: 4/4 verifications passed`

- [ ] **Step 2: Handle missing/failed tests gracefully**

  Ensure the evaluator produces clear failure messages when:
  - A required ref has no matching test (message: `"No test found with tag matching 'REQ-001.XXX'"`)
  - A matching test failed (message includes the test failure details)

  **Verify:**
  ```sh
  python3 -c "
  from verify.evaluator import evaluate_spec

  # Test with empty results — all refs should fail
  empty_results = {'test_cases': []}
  verdicts = evaluate_spec('.verify/specs/DEMO-001.yaml', empty_results)
  v = verdicts[0]
  assert v['passed'] == False, 'Should fail with no test results'
  assert all(not e['passed'] for e in v['evidence']), 'All evidence should be failed'
  print(f'OK: correctly fails with empty results: {v[\"summary\"]}')
  "
  ```
  Expected: `OK: correctly fails with empty results: 0/4 verifications passed`

#### Definition of Done

```sh
echo "=== Feature 0.5: Evaluator ==="
python3 -c "
from verify.evaluator import evaluate_spec
from verify.runner import run_and_parse

# Run with real tests
results = run_and_parse('.verify/generated/test_demo_001.py', '.verify/results')
verdicts = evaluate_spec('.verify/specs/DEMO-001.yaml', results)
assert verdicts[0]['passed'], f'FAIL: {verdicts[0][\"evidence\"]}'
print(f'PASS: {verdicts[0][\"summary\"]}')

# Run with no tests — should fail
empty = {'test_cases': []}
verdicts_empty = evaluate_spec('.verify/specs/DEMO-001.yaml', empty)
assert not verdicts_empty[0]['passed'], 'FAIL: should fail with no tests'
print('PASS: correctly handles missing tests')
" && echo "=== Feature 0.5 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done script passes

---

### Feature 0.6: Pipeline Runner — End-to-End Proof [MVP]

**Story:** A single command that runs the entire bullet tracer pipeline and prints results.
**Depends on:** Features 0.3, 0.4, 0.5

#### Prerequisites

```sh
python3 -c "
from verify.generator import generate_and_write
from verify.runner import run_and_parse
from verify.evaluator import evaluate_spec
print('OK: all pipeline modules importable')
"
```

#### Implementation Steps

- [ ] **Step 1: Create the pipeline module at `src/verify/pipeline.py`**

  Implement `run_pipeline(spec_path: str) -> list[dict]` that:
  1. Reads the spec at `spec_path`
  2. Calls `generate_and_write(spec_path)` → gets generated test file path
  3. Calls `run_and_parse(test_path, results_dir)` → gets parsed test results
  4. Calls `evaluate_spec(spec_path, test_results)` → gets verdicts
  5. Prints a formatted summary to stdout showing: spec used, tests generated, results per AC checkbox
  6. Returns the verdicts list

  **Verify:**
  ```sh
  python3 -c "
  from verify.pipeline import run_pipeline
  verdicts = run_pipeline('.verify/specs/DEMO-001.yaml')
  assert len(verdicts) >= 1
  assert verdicts[0]['passed']
  print('OK: pipeline runs end-to-end')
  "
  ```
  Expected: Console shows the pipeline steps, then `OK: pipeline runs end-to-end`

- [ ] **Step 2: Add CLI entry point**

  Add a `__main__.py` or a script entry so the pipeline can be run as:
  ```
  python -m verify.pipeline .verify/specs/DEMO-001.yaml
  ```

  The script should:
  - Accept a spec path as a CLI argument
  - Run the pipeline
  - Print formatted results
  - Exit with code 0 if all verdicts pass, 1 otherwise

  **Verify:**
  ```sh
  python3 -m verify.pipeline .verify/specs/DEMO-001.yaml
  echo "Exit code: $?"
  ```
  Expected: Pipeline output followed by `Exit code: 0`

#### Definition of Done

```sh
echo "=== Feature 0.6: Pipeline Runner ==="
python3 -m verify.pipeline .verify/specs/DEMO-001.yaml && \
echo "=== Feature 0.6 COMPLETE ===" || \
echo "=== Feature 0.6 FAILED ==="
```
- [ ] Both steps checked off
- [ ] Pipeline runs end-to-end with exit code 0

---

## Epic 1: Real Jira Integration [MVP]

**Goal:** Replace hardcoded Jira data with live API calls. Read real AC from real tickets, write checkboxes back.
**Depends on:** Epic 0 (pipeline skeleton exists)
**After this epic:** Pipeline reads from live Jira and can write checkbox updates + evidence comments back.

---

### Feature 1.1: Jira API Client — Read Ticket [MVP]

**Story:** Pull acceptance criteria from a real Jira Cloud ticket via REST API.
**Depends on:** None (can be built in parallel with Epic 0)

#### Prerequisites

```sh
# Verify required env vars are set (or can be set)
echo "Jira credentials needed: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN"
echo "These will be read from environment variables at runtime"
```

#### Implementation Steps

- [ ] **Step 1: Create Jira client module at `src/verify/jira_client.py`**

  Implement a `JiraClient` class with:
  - `__init__(base_url, email, api_token)` — reads from env vars if not provided: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
  - Uses `requests` library with basic auth (email:api_token)
  - Base URL like `https://your-org.atlassian.net`

  **Verify:**
  ```sh
  python3 -c "
  from verify.jira_client import JiraClient
  # Should be constructable (won't connect without real creds)
  client = JiraClient(base_url='https://test.atlassian.net', email='test', api_token='test')
  print('OK: JiraClient constructable')
  "
  ```
  Expected: `OK: JiraClient constructable`

- [ ] **Step 2: Implement `fetch_ticket(jira_key: str) -> dict`**

  Makes `GET /rest/api/3/issue/{jira_key}` call. Returns raw issue JSON. Handles errors (404, auth failures) with clear messages.

  **Verify:**
  ```sh
  python3 -c "
  from verify.jira_client import JiraClient
  client = JiraClient(base_url='https://test.atlassian.net', email='test', api_token='test')
  assert hasattr(client, 'fetch_ticket')
  print('OK: fetch_ticket method exists')
  "
  ```
  Expected: `OK: fetch_ticket method exists`

- [ ] **Step 3: Implement `extract_acceptance_criteria(issue: dict) -> list[dict]`**

  Parses the ticket description to extract AC checkboxes. Must handle:
  - **ADF format** (Jira Cloud): Look for `taskList` → `taskItem` nodes, extract `state` (DONE/TODO) and text content
  - **Markdown fallback**: Parse `- [ ] text` and `- [x] text` patterns from description text

  Returns: `[{"index": 0, "text": "User can view their profile", "checked": False}, ...]`

  **Verify:**
  ```sh
  python3 -c "
  from verify.jira_client import JiraClient

  # Test markdown parsing with mock data
  mock_description_text = '''Some intro text
  - [ ] User can view their profile
  - [x] Already done item
  - [ ] Profile data is never exposed'''

  result = JiraClient.parse_markdown_checkboxes(mock_description_text)
  assert len(result) == 3, f'Expected 3 checkboxes, got {len(result)}'
  assert result[0]['text'] == 'User can view their profile'
  assert result[0]['checked'] == False
  assert result[1]['checked'] == True
  assert result[0]['index'] == 0
  print(f'OK: parsed {len(result)} checkboxes from markdown')
  "
  ```
  Expected: `OK: parsed 3 checkboxes from markdown`

- [ ] **Step 4: Implement `get_acceptance_criteria(jira_key: str) -> list[dict]`**

  Convenience method that calls `fetch_ticket` then `extract_acceptance_criteria`. This is what the pipeline will call.

  **Verify (with real Jira — requires credentials):**
  ```sh
  # Skip this verification if no Jira credentials available
  # When credentials are set, test with a real ticket:
  # python3 -c "
  # from verify.jira_client import JiraClient
  # client = JiraClient()  # reads from env vars
  # ac = client.get_acceptance_criteria('YOUR-TICKET-KEY')
  # print(f'OK: fetched {len(ac)} acceptance criteria')
  # for item in ac:
  #     print(f'  [{\"x\" if item[\"checked\"] else \" \"}] {item[\"text\"]}')
  # "
  echo "OK: get_acceptance_criteria implemented (test with real creds when available)"
  ```

#### Definition of Done

```sh
echo "=== Feature 1.1: Jira Read ==="
python3 -c "
from verify.jira_client import JiraClient

# Test construction
client = JiraClient(base_url='https://test.atlassian.net', email='t', api_token='t')
assert hasattr(client, 'fetch_ticket')
assert hasattr(client, 'get_acceptance_criteria')

# Test markdown parsing
result = JiraClient.parse_markdown_checkboxes('- [ ] AC one\n- [x] AC two\n- [ ] AC three')
assert len(result) == 3
assert result[1]['checked'] == True
print('PASS: Jira client with markdown parsing')
" && echo "=== Feature 1.1 COMPLETE ==="
```
- [ ] All 4 steps checked off
- [ ] Definition of Done passes

---

### Feature 1.2: Jira API Client — Write Checkbox Update [MVP]

**Story:** Tick specific AC checkboxes on the Jira ticket.
**Depends on:** Feature 1.1

#### Prerequisites

```sh
python3 -c "from verify.jira_client import JiraClient; print('OK: JiraClient importable')"
```

#### Implementation Steps

- [ ] **Step 1: Implement `tick_checkbox(jira_key: str, checkbox_index: int)`**

  1. Fetch the current ticket description via `fetch_ticket`
  2. Parse the description to find the nth checkbox
  3. For ADF: modify the `taskItem` node's `state` attribute from `TODO` to `DONE`
  4. For markdown: replace `- [ ]` with `- [x]` for the specific checkbox
  5. PUT the updated description back to `PUT /rest/api/3/issue/{jira_key}`
  6. Must be idempotent — ticking an already-checked box is a no-op

  **Verify:**
  ```sh
  python3 -c "
  from verify.jira_client import JiraClient

  # Test markdown checkbox ticking logic (unit test, no API call)
  desc = '- [ ] First\n- [ ] Second\n- [ ] Third'
  updated = JiraClient.tick_markdown_checkbox(desc, 1)
  assert '- [x] Second' in updated, f'Checkbox 1 not ticked: {updated}'
  assert '- [ ] First' in updated, 'Checkbox 0 should remain unchecked'
  assert '- [ ] Third' in updated, 'Checkbox 2 should remain unchecked'

  # Test idempotency
  updated2 = JiraClient.tick_markdown_checkbox(updated, 1)
  assert updated2 == updated, 'Should be idempotent'
  print('OK: checkbox ticking logic correct and idempotent')
  "
  ```
  Expected: `OK: checkbox ticking logic correct and idempotent`

- [ ] **Step 2: Implement `tick_checkboxes(jira_key: str, indices: list[int])`**

  Batch version that ticks multiple checkboxes in a single description update (one API call, not N calls).

  **Verify:**
  ```sh
  python3 -c "
  from verify.jira_client import JiraClient
  desc = '- [ ] A\n- [ ] B\n- [ ] C'
  updated = JiraClient.tick_markdown_checkbox(desc, 0)
  updated = JiraClient.tick_markdown_checkbox(updated, 2)
  assert '- [x] A' in updated
  assert '- [ ] B' in updated
  assert '- [x] C' in updated
  print('OK: multiple checkboxes ticked correctly')
  "
  ```
  Expected: `OK: multiple checkboxes ticked correctly`

#### Definition of Done

```sh
echo "=== Feature 1.2: Jira Write ==="
python3 -c "
from verify.jira_client import JiraClient
desc = '- [ ] A\n- [ ] B\n- [x] C\n- [ ] D'
updated = JiraClient.tick_markdown_checkbox(desc, 0)
updated = JiraClient.tick_markdown_checkbox(updated, 1)
assert '- [x] A' in updated
assert '- [x] B' in updated
assert '- [x] C' in updated  # already checked, preserved
assert '- [ ] D' in updated
print('PASS: checkbox manipulation correct')
" && echo "=== Feature 1.2 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

### Feature 1.3: Jira API Client — Post Evidence Comment [MVP]

**Story:** Post a structured evidence comment on the Jira ticket showing verification results.
**Depends on:** Feature 1.1

#### Prerequisites

```sh
python3 -c "from verify.jira_client import JiraClient; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Implement `format_evidence_comment(verdicts: list[dict], spec_path: str) -> str`**

  Takes the evaluator's verdicts and formats them as a Jira wiki markup comment (see `ac-to-specs-plan.md` Section 6.3 for the template). Include:
  - Overall pass/fail header
  - Per-AC-checkbox section with pass/fail icon
  - Per-ref evidence table with columns: Ref, Description, Type, Result
  - Spec file path for traceability
  - Footer noting this was generated by the pipeline

  **Verify:**
  ```sh
  python3 -c "
  from verify.jira_client import JiraClient

  mock_verdicts = [{
      'ac_checkbox': 0,
      'ac_text': 'User can view their profile',
      'passed': True,
      'pass_condition': 'ALL_PASS',
      'summary': '4/4 verifications passed',
      'evidence': [
          {'ref': 'REQ-001.success', 'passed': True, 'details': 'Test passed', 'verification_type': 'test_result'},
          {'ref': 'REQ-001.FAIL-001', 'passed': True, 'details': 'Test passed', 'verification_type': 'test_result'},
      ]
  }]

  comment = JiraClient.format_evidence_comment(mock_verdicts, '.verify/specs/DEMO-001.yaml')
  assert 'Verification Pipeline Results' in comment
  assert 'REQ-001.success' in comment
  assert 'ALL PASSED' in comment or 'all passed' in comment.lower()
  assert len(comment) > 100  # Should be substantial
  print(f'OK: evidence comment generated ({len(comment)} chars)')
  "
  ```
  Expected: `OK: evidence comment generated (XXX chars)`

- [ ] **Step 2: Implement `post_comment(jira_key: str, comment: str)`**

  Posts the comment via `POST /rest/api/3/issue/{jira_key}/comment`. The body should use Jira's ADF format or wiki markup depending on the API version.

  **Verify:**
  ```sh
  python3 -c "
  from verify.jira_client import JiraClient
  client = JiraClient(base_url='https://test.atlassian.net', email='t', api_token='t')
  assert hasattr(client, 'post_comment')
  print('OK: post_comment method exists')
  "
  ```
  Expected: `OK: post_comment method exists`

#### Definition of Done

```sh
echo "=== Feature 1.3: Evidence Comment ==="
python3 -c "
from verify.jira_client import JiraClient
mock_verdicts = [{'ac_checkbox': 0, 'ac_text': 'Test AC', 'passed': True,
  'pass_condition': 'ALL_PASS', 'summary': '2/2 passed',
  'evidence': [{'ref': 'REQ-001.success', 'passed': True, 'details': 'ok', 'verification_type': 'test_result'}]}]
comment = JiraClient.format_evidence_comment(mock_verdicts, 'spec.yaml')
assert 'REQ-001.success' in comment
print('PASS: evidence comment formatting works')
" && echo "=== Feature 1.3 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

### Feature 1.4: Jira API Client — Transition Ticket [MVP]

**Story:** Automatically transition the ticket to "Done" when all AC checkboxes pass.
**Depends on:** Feature 1.1

#### Prerequisites

```sh
python3 -c "from verify.jira_client import JiraClient; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Implement `get_transitions(jira_key: str) -> list[dict]`**

  Calls `GET /rest/api/3/issue/{jira_key}/transitions` to get available transitions. Returns `[{"id": "31", "name": "Done"}, ...]`.

  **Verify:**
  ```sh
  python3 -c "
  from verify.jira_client import JiraClient
  client = JiraClient(base_url='https://test.atlassian.net', email='t', api_token='t')
  assert hasattr(client, 'get_transitions')
  print('OK: get_transitions method exists')
  "
  ```

- [ ] **Step 2: Implement `transition_ticket(jira_key: str, target_status: str)`**

  1. Calls `get_transitions` to find the transition ID for `target_status`
  2. Executes `POST /rest/api/3/issue/{jira_key}/transitions` with the transition ID
  3. If no matching transition found, logs a warning (doesn't crash)

  **Verify:**
  ```sh
  python3 -c "
  from verify.jira_client import JiraClient
  client = JiraClient(base_url='https://test.atlassian.net', email='t', api_token='t')
  assert hasattr(client, 'transition_ticket')
  print('OK: transition_ticket method exists')
  "
  ```

#### Definition of Done

```sh
echo "=== Feature 1.4: Ticket Transition ==="
python3 -c "
from verify.jira_client import JiraClient
client = JiraClient(base_url='https://test.atlassian.net', email='t', api_token='t')
for method in ['fetch_ticket', 'get_acceptance_criteria', 'tick_checkbox', 'post_comment', 'get_transitions', 'transition_ticket']:
    assert hasattr(client, method), f'Missing method: {method}'
print('PASS: JiraClient has all required methods')
" && echo "=== Feature 1.4 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

## Epic 2: AI Negotiation — Core Loop [MVP]

**Goal:** Build the AI-powered negotiation that transforms fuzzy AC into structured spec elements (Phases 1-4).
**Depends on:** Epic 0 (pipeline exists), Epic 1 (can read from Jira)
**After this epic:** A developer can interactively negotiate with the AI, turning AC into classifications, postconditions, preconditions, and failure modes.

---

### Feature 2.1: Negotiation Harness & VerificationContext [MVP]

**Story:** A harness that manages negotiation state, tracks phases, and accumulates spec elements.
**Depends on:** None

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

## Epic 3: Formal Spec Emission [MVP]

**Goal:** Compile negotiation output into a complete, validated YAML spec with traceability map.
**Depends on:** Epic 2 (negotiation produces the context to serialize)
**After this epic:** The negotiation produces a real `.verify/specs/{jira_key}.yaml` file.

---

### Feature 3.1: Spec Compiler — Context to YAML [MVP]

**Story:** Automatically compile the VerificationContext into a valid spec YAML file.
**Depends on:** Epic 2

#### Prerequisites

```sh
python3 -c "from verify.context import VerificationContext; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Create compiler module at `src/verify/compiler.py`**

  Implement `compile_spec(context: VerificationContext) -> dict` that:
  1. Builds the spec dict following the schema from `ac-to-specs-plan.md` Section 4.2
  2. Populates `meta` section: spec_version, jira_key, generated_at, approved_by, status
  3. Populates `requirements` section: one requirement per classified AC, with contract (interface, preconditions, success, failures, invariants)
  4. Returns the complete spec dict (not yet written to disk)

  **Verify:**
  ```sh
  python3 -c "
  from verify.compiler import compile_spec
  from verify.context import VerificationContext

  ctx = VerificationContext(jira_key='TEST-001', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'User can view profile', 'checked': False}],
      constitution={})
  ctx.classifications = [{'ac_index': 0, 'type': 'api_behavior', 'actor': 'authenticated_user',
      'interface': {'method': 'GET', 'path': '/api/v1/users/me'}}]
  ctx.postconditions = [{'ac_index': 0, 'status': 200, 'schema': {'properties': {'id': {'type': 'string'}}}}]
  ctx.preconditions = [{'id': 'PRE-001', 'description': 'Valid auth', 'category': 'authentication', 'formal': 'jwt != null'}]
  ctx.failure_modes = [{'id': 'FAIL-001', 'description': 'No auth', 'violates': 'PRE-001', 'status': 401,
      'body': {'error': 'unauthorized'}}]
  ctx.approved = True
  ctx.approved_by = 'developer'

  spec = compile_spec(ctx)
  assert spec['meta']['jira_key'] == 'TEST-001'
  assert len(spec['requirements']) >= 1
  assert spec['requirements'][0]['contract']['interface']['method'] == 'GET'
  print('OK: spec compiled from context')
  "
  ```
  Expected: `OK: spec compiled from context`

- [ ] **Step 2: Add YAML serialization and file writing**

  Implement `write_spec(context: VerificationContext) -> str` that:
  1. Calls `compile_spec(context)`
  2. Serializes to YAML with `yaml.dump` (using clean formatting, no anchors)
  3. Writes to `.verify/specs/{jira_key}.yaml`
  4. Returns the file path

  **Verify:**
  ```sh
  python3 -c "
  import os, yaml
  from verify.compiler import write_spec
  from verify.context import VerificationContext

  ctx = VerificationContext(jira_key='TEST-COMPILE', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}],
      constitution={})
  ctx.classifications = [{'ac_index': 0, 'type': 'api_behavior', 'actor': 'authenticated_user',
      'interface': {'method': 'GET', 'path': '/test'}}]
  ctx.postconditions = [{'ac_index': 0, 'status': 200}]
  ctx.preconditions = [{'id': 'PRE-001', 'description': 'Auth', 'category': 'authentication', 'formal': 'jwt != null'}]
  ctx.failure_modes = [{'id': 'FAIL-001', 'violates': 'PRE-001', 'status': 401, 'body': {}, 'description': 'no auth'}]
  ctx.approved = True
  ctx.approved_by = 'test'

  path = write_spec(ctx)
  assert os.path.exists(path), f'File not created: {path}'
  spec = yaml.safe_load(open(path))
  assert spec['meta']['jira_key'] == 'TEST-COMPILE'
  os.remove(path)  # cleanup
  print(f'OK: spec written to {path}')
  "
  ```
  Expected: `OK: spec written to .verify/specs/TEST-COMPILE.yaml`

#### Definition of Done

```sh
echo "=== Feature 3.1: Spec Compiler ==="
python3 -c "
from verify.compiler import compile_spec, write_spec
from verify.context import VerificationContext
ctx = VerificationContext(jira_key='DOD-TEST', jira_summary='T',
    raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}], constitution={})
ctx.classifications = [{'ac_index': 0, 'type': 'api_behavior', 'actor': 'user', 'interface': {'method': 'GET', 'path': '/t'}}]
ctx.postconditions = [{'ac_index': 0, 'status': 200}]
ctx.preconditions = [{'id': 'PRE-001', 'description': 'A', 'category': 'authentication', 'formal': 'x'}]
ctx.failure_modes = [{'id': 'FAIL-001', 'violates': 'PRE-001', 'status': 401, 'body': {}, 'description': 'd'}]
ctx.approved = True; ctx.approved_by = 'test'
spec = compile_spec(ctx)
assert 'meta' in spec and 'requirements' in spec
import os; path = write_spec(ctx); assert os.path.exists(path); os.remove(path)
print('PASS: compiler works')
" && echo "=== Feature 3.1 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

### Feature 3.2: Verification Routing Table Generation [MVP]

**Story:** The spec includes a routing table mapping each contract element to a verification skill.
**Depends on:** Feature 3.1

#### Prerequisites

```sh
python3 -c "from verify.compiler import compile_spec; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Add routing logic to the compiler**

  Extend `compile_spec` to generate a `verification` block under each requirement:
  - For `api_behavior` requirements: route to `pytest_unit_test` skill
  - For `performance_sla`: route to `newrelic_alert_config` skill
  - For `security_invariant`: route to same test file as the parent behavior
  - Each entry specifies: `refs` (contract elements covered), `skill` (generator ID), `output` (file path)

  The routing is a simple mapping — no AI:
  ```python
  ROUTING_TABLE = {
      "api_behavior": "pytest_unit_test",
      "performance_sla": "newrelic_alert_config",
      "security_invariant": "pytest_unit_test",
      "observability": "otel_config",
  }
  ```

  **Verify:**
  ```sh
  python3 -c "
  from verify.compiler import compile_spec
  from verify.context import VerificationContext

  ctx = VerificationContext(jira_key='RT-001', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}], constitution={})
  ctx.classifications = [{'ac_index': 0, 'type': 'api_behavior', 'actor': 'user',
      'interface': {'method': 'GET', 'path': '/test'}}]
  ctx.postconditions = [{'ac_index': 0, 'status': 200}]
  ctx.preconditions = [{'id': 'PRE-001', 'description': 'A', 'category': 'authentication', 'formal': 'x'}]
  ctx.failure_modes = [{'id': 'FAIL-001', 'violates': 'PRE-001', 'status': 401, 'body': {}, 'description': 'd'}]
  ctx.approved = True; ctx.approved_by = 'test'

  spec = compile_spec(ctx)
  req = spec['requirements'][0]
  assert 'verification' in req, 'No verification block'
  assert len(req['verification']) >= 1
  assert req['verification'][0]['skill'] == 'pytest_unit_test'
  assert 'output' in req['verification'][0]
  print(f'OK: routing table has {len(req[\"verification\"])} entries')
  "
  ```
  Expected: `OK: routing table has N entries`

#### Definition of Done

```sh
echo "=== Feature 3.2: Routing Table ==="
python3 -c "
from verify.compiler import compile_spec
from verify.context import VerificationContext
ctx = VerificationContext(jira_key='RT', jira_summary='T',
    raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}], constitution={})
ctx.classifications = [{'ac_index': 0, 'type': 'api_behavior', 'actor': 'u', 'interface': {'method': 'GET', 'path': '/t'}}]
ctx.postconditions = [{'ac_index': 0, 'status': 200}]
ctx.preconditions = [{'id': 'P1', 'description': 'a', 'category': 'authentication', 'formal': 'x'}]
ctx.failure_modes = [{'id': 'F1', 'violates': 'P1', 'status': 401, 'body': {}, 'description': 'd'}]
ctx.approved = True; ctx.approved_by = 'x'
spec = compile_spec(ctx)
assert 'verification' in spec['requirements'][0]
print('PASS: routing table generated')
" && echo "=== Feature 3.2 COMPLETE ==="
```
- [ ] Step 1 checked off
- [ ] Definition of Done passes

---

### Feature 3.3: Traceability Map Generation [MVP]

**Story:** The spec includes an explicit traceability map linking every verification ref to AC checkboxes.
**Depends on:** Feature 3.1

#### Prerequisites

```sh
python3 -c "from verify.compiler import compile_spec; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Add traceability map generation to the compiler**

  Extend `compile_spec` to generate the `traceability.ac_mappings` block:
  1. For each AC checkbox, collect all spec refs that trace to it (success, failures, invariants)
  2. Each mapping has: `ac_checkbox` (index), `ac_text`, `pass_condition` (default `ALL_PASS`), `required_verifications` (list of `{ref, description, verification_type}`)
  3. Refs that satisfy multiple AC checkboxes appear in multiple mappings (many-to-many)

  **Verify:**
  ```sh
  python3 -c "
  from verify.compiler import compile_spec
  from verify.context import VerificationContext

  ctx = VerificationContext(jira_key='TM-001', jira_summary='Test',
      raw_acceptance_criteria=[{'index': 0, 'text': 'User can view profile', 'checked': False}],
      constitution={})
  ctx.classifications = [{'ac_index': 0, 'type': 'api_behavior', 'actor': 'user',
      'interface': {'method': 'GET', 'path': '/test'}}]
  ctx.postconditions = [{'ac_index': 0, 'status': 200}]
  ctx.preconditions = [{'id': 'PRE-001', 'description': 'Auth', 'category': 'authentication', 'formal': 'x'}]
  ctx.failure_modes = [{'id': 'FAIL-001', 'violates': 'PRE-001', 'status': 401, 'body': {}, 'description': 'no auth'}]
  ctx.invariants = [{'id': 'INV-001', 'type': 'security', 'rule': 'No password in response'}]
  ctx.approved = True; ctx.approved_by = 'test'

  spec = compile_spec(ctx)
  assert 'traceability' in spec, 'Missing traceability'
  mappings = spec['traceability']['ac_mappings']
  assert len(mappings) >= 1
  assert mappings[0]['ac_checkbox'] == 0
  assert mappings[0]['pass_condition'] == 'ALL_PASS'
  refs = [v['ref'] for v in mappings[0]['required_verifications']]
  assert any('success' in r for r in refs), f'Missing success ref in {refs}'
  assert any('FAIL' in r for r in refs), f'Missing failure ref in {refs}'
  print(f'OK: traceability map with {len(refs)} refs for AC[0]')
  "
  ```
  Expected: `OK: traceability map with N refs for AC[0]`

#### Definition of Done

```sh
echo "=== Feature 3.3: Traceability Map ==="
python3 -c "
from verify.compiler import compile_spec
from verify.context import VerificationContext
ctx = VerificationContext(jira_key='TM', jira_summary='T',
    raw_acceptance_criteria=[{'index': 0, 'text': 'AC', 'checked': False}], constitution={})
ctx.classifications = [{'ac_index': 0, 'type': 'api_behavior', 'actor': 'u', 'interface': {'method': 'GET', 'path': '/t'}}]
ctx.postconditions = [{'ac_index': 0, 'status': 200}]
ctx.preconditions = [{'id': 'P1', 'description': 'a', 'category': 'authentication', 'formal': 'x'}]
ctx.failure_modes = [{'id': 'F1', 'violates': 'P1', 'status': 401, 'body': {}, 'description': 'd'}]
ctx.approved = True; ctx.approved_by = 'x'
spec = compile_spec(ctx)
assert 'traceability' in spec
assert len(spec['traceability']['ac_mappings']) >= 1
print('PASS: traceability map generated')
" && echo "=== Feature 3.3 COMPLETE ==="
```
- [ ] Step 1 checked off
- [ ] Definition of Done passes

---

## Epic 4: Multi-Skill Routing & Test Generation [MVP]

**Goal:** Replace the hardcoded test generator with AI-powered skill agents that read specs and generate framework-appropriate tests.
**Depends on:** Epic 3 (specs with routing tables exist)
**After this epic:** The spec drives real test generation via specialized skills.

---

### Feature 4.1: Skill Agent Framework [MVP]

**Story:** A plugin architecture where each verification skill is a self-contained module.
**Depends on:** Feature 3.2

#### Prerequisites

```sh
python3 -c "from verify.compiler import compile_spec; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Create skill framework at `src/verify/skills/framework.py`**

  Define a base class `VerificationSkill` with:
  - `skill_id: str` — unique identifier (e.g., `pytest_unit_test`)
  - `generate(spec: dict, requirement: dict, constitution: dict) -> str` — generates the verification artifact content
  - `output_path(spec: dict, requirement: dict) -> str` — returns where the artifact should be written

  Create a registry `SKILL_REGISTRY: dict[str, VerificationSkill]` and a `register_skill(skill)` function.

  **Verify:**
  ```sh
  python3 -c "
  from verify.skills.framework import VerificationSkill, SKILL_REGISTRY
  assert isinstance(SKILL_REGISTRY, dict)
  print(f'OK: skill framework exists with {len(SKILL_REGISTRY)} registered skills')
  "
  ```

- [ ] **Step 2: Create skill dispatcher**

  Implement `dispatch_skills(spec: dict, constitution: dict) -> dict[str, str]` that:
  1. Reads `verification` blocks from each requirement in the spec
  2. Looks up each `skill` ID in `SKILL_REGISTRY`
  3. Calls `skill.generate()` for each routing entry
  4. Writes the output to the specified path
  5. Returns a dict of `{output_path: content}` for all generated files

  **Verify:**
  ```sh
  python3 -c "
  from verify.skills.framework import dispatch_skills
  # Will work once at least one skill is registered (Feature 4.2)
  print('OK: dispatch_skills exists')
  "
  ```

#### Definition of Done

```sh
echo "=== Feature 4.1: Skill Framework ==="
python3 -c "
from verify.skills.framework import VerificationSkill, SKILL_REGISTRY, dispatch_skills
print('PASS: skill framework importable')
" && echo "=== Feature 4.1 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

### Feature 4.2: Pytest Unit Test Skill [MVP]

**Story:** A skill that reads the spec contract and generates a complete pytest test file with tagged methods.
**Depends on:** Feature 4.1

#### Prerequisites

```sh
python3 -c "from verify.skills.framework import SKILL_REGISTRY; print('OK')"
```

#### Implementation Steps

- [ ] **Step 1: Create pytest skill at `src/verify/skills/pytest_skill.py`**

  Implement `PytestSkill(VerificationSkill)` with `skill_id = "pytest_unit_test"` that:
  1. Reads `contract.success`, `contract.failures`, `contract.invariants` from the spec requirement
  2. Uses the LLM (or templates) to generate a complete pytest test file
  3. Each test function includes the spec ref in its name: `test_REQ_001_success[REQ-001.success]`
  4. Uses `pytest.mark.spec("REQ-001.success")` markers OR includes `[REQ-001.success]` in the parametrize ID
  5. Tests use `fastapi.testclient.TestClient` to hit the endpoint
  6. The skill follows the constitution's test patterns (imports, assertion style)
  7. Registers itself in `SKILL_REGISTRY`

  **Verify:**
  ```sh
  python3 -c "
  from verify.skills.pytest_skill import PytestSkill
  from verify.skills.framework import SKILL_REGISTRY
  import yaml

  assert 'pytest_unit_test' in SKILL_REGISTRY, 'Skill not registered'

  spec = yaml.safe_load(open('.verify/specs/DEMO-001.yaml'))
  skill = SKILL_REGISTRY['pytest_unit_test']
  content = skill.generate(spec, spec['requirements'][0], {})

  assert 'REQ-001' in content, 'Missing spec refs in generated tests'
  assert 'def test_' in content, 'No test functions generated'
  assert 'TestClient' in content, 'Missing TestClient import'
  print(f'OK: pytest skill generated {content.count(\"def test_\")} test functions')
  "
  ```
  Expected: `OK: pytest skill generated N test functions`

- [ ] **Step 2: Verify generated tests pass against the dummy app**

  **Verify:**
  ```sh
  python3 -c "
  from verify.skills.framework import dispatch_skills
  import yaml
  spec = yaml.safe_load(open('.verify/specs/DEMO-001.yaml'))
  files = dispatch_skills(spec, {})
  print(f'Generated {len(files)} files')
  " && python3 -m pytest .verify/generated/test_demo_001.py -v 2>&1 | tail -10
  ```
  Expected: All tests pass.

#### Definition of Done

```sh
echo "=== Feature 4.2: Pytest Skill ==="
python3 -c "
from verify.skills.framework import SKILL_REGISTRY
assert 'pytest_unit_test' in SKILL_REGISTRY
print('PASS: skill registered')
" && \
python3 -c "
from verify.skills.framework import dispatch_skills
import yaml
spec = yaml.safe_load(open('.verify/specs/DEMO-001.yaml'))
dispatch_skills(spec, {})
" && \
python3 -m pytest .verify/generated/test_demo_001.py -v --tb=short 2>&1 | tail -5 && \
echo "=== Feature 4.2 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Generated tests pass

---

### Feature 4.3: Tag Contract Enforcement [MVP]

**Story:** Every generated test method is tagged with its spec ref in a consistent format, and coverage is validated.
**Depends on:** Feature 4.2

#### Prerequisites

```sh
test -f .verify/generated/test_demo_001.py && echo "OK: generated test file exists"
```

#### Implementation Steps

- [ ] **Step 1: Add tag validation to the skill framework**

  Implement `validate_tags(generated_content: str, expected_refs: list[str]) -> dict` in `src/verify/skills/tag_enforcer.py` that:
  1. Scans the generated test file content for spec ref patterns
  2. Extracts all refs found (from markers, test names, or brackets)
  3. Compares against `expected_refs` from the spec's `verification[].refs`
  4. Returns `{"covered": [...], "missing": [...], "extra": [...]}`

  **Verify:**
  ```sh
  python3 -c "
  from verify.skills.tag_enforcer import validate_tags

  test_content = '''
  def test_success_REQ_001():
      \"\"\"[REQ-001.success] Happy path\"\"\"
      pass

  def test_fail_001():
      \"\"\"[REQ-001.FAIL-001] No auth\"\"\"
      pass
  '''

  result = validate_tags(test_content, ['REQ-001.success', 'REQ-001.FAIL-001', 'REQ-001.FAIL-002'])
  assert 'REQ-001.success' in result['covered']
  assert 'REQ-001.FAIL-001' in result['covered']
  assert 'REQ-001.FAIL-002' in result['missing']
  print(f'OK: {len(result[\"covered\"])} covered, {len(result[\"missing\"])} missing')
  "
  ```
  Expected: `OK: 2 covered, 1 missing`

- [ ] **Step 2: Integrate tag validation into skill dispatch**

  After generating a test file, automatically validate tags. If any required refs are missing, log a warning.

  **Verify:**
  ```sh
  python3 -c "
  from verify.skills.tag_enforcer import validate_tags
  import yaml

  spec = yaml.safe_load(open('.verify/specs/DEMO-001.yaml'))
  expected_refs = []
  for req in spec['requirements']:
      for v in req.get('verification', []):
          for ref in v.get('refs', []):
              expected_refs.append(f'REQ-001.{ref}' if not ref.startswith('REQ') else ref)

  with open('.verify/generated/test_demo_001.py') as f:
      content = f.read()

  result = validate_tags(content, expected_refs)
  print(f'Coverage: {len(result[\"covered\"])}/{len(expected_refs)} refs covered')
  if result['missing']:
      print(f'Missing: {result[\"missing\"]}')
  else:
      print('OK: 100% ref coverage')
  "
  ```

#### Definition of Done

```sh
echo "=== Feature 4.3: Tag Enforcement ==="
python3 -c "
from verify.skills.tag_enforcer import validate_tags
result = validate_tags('[REQ-001.success] [REQ-001.FAIL-001]', ['REQ-001.success', 'REQ-001.FAIL-001'])
assert len(result['missing']) == 0
print('PASS: tag enforcement works')
" && echo "=== Feature 4.3 COMPLETE ==="
```
- [ ] Both steps checked off
- [ ] Definition of Done passes

---

## Epic 5: Evaluation Engine (Full) [MVP]

**Goal:** Extend the evaluator to handle multiple verification types and format strategies.
**Depends on:** Epic 0 (basic evaluator), Epic 4 (generated tests with tags)
**After this epic:** The evaluator handles test results, deployment checks, and config validations.

---

### Feature 5.1: Multi-Format Test Result Parser [MVP]

**Story:** Parse test results from JUnit XML, Jest JSON, and Cucumber JSON into a unified format.
**Depends on:** Feature 0.4 (extends the basic parser)

#### Implementation Steps

- [ ] **Step 1: Extend `src/verify/runner.py` to handle multiple result formats**

  Add parsers for:
  - JUnit XML (already exists from Feature 0.4) — `parse_junit_xml`
  - Jest JSON (`parse_jest_json`) — extract from `testResults[].assertionResults[]`, tags from `[REF]` patterns in test names
  - A `merge_results(paths: list[str]) -> dict` function that auto-detects format (`.xml` → JUnit, `.json` → Jest) and combines

  **Verify:**
  ```sh
  python3 -c "
  from verify.runner import parse_junit_xml, merge_results
  print('OK: multi-format parsers exist')
  "
  ```

#### Definition of Done

```sh
echo "=== Feature 5.1 ==="
python3 -c "from verify.runner import parse_junit_xml, merge_results; print('PASS')"
echo "=== Feature 5.1 COMPLETE ==="
```
- [ ] Step checked off

---

### Feature 5.2: Deployment Check Evaluation Strategy [MVP]

**Story:** Verify that generated config files exist and are structurally valid.
**Depends on:** Feature 0.5 (extends the evaluator)

#### Implementation Steps

- [ ] **Step 1: Add `deployment_check` and `config_validation` strategies to `src/verify/evaluator.py`**

  Implement evaluation strategies (from `ac-to-specs-plan.md` Section 5.2):
  - `deployment_check`: file exists at specified path AND is parseable (valid JSON/YAML)
  - `config_validation`: file exists AND contains required entries

  Register them in an `EVALUATION_STRATEGIES` dict alongside the existing `test_result` strategy.

  **Verify:**
  ```sh
  python3 -c "
  from verify.evaluator import EVALUATION_STRATEGIES
  assert 'test_result' in EVALUATION_STRATEGIES
  assert 'deployment_check' in EVALUATION_STRATEGIES
  assert 'config_validation' in EVALUATION_STRATEGIES
  print(f'OK: {len(EVALUATION_STRATEGIES)} evaluation strategies registered')
  "
  ```

#### Definition of Done

```sh
echo "=== Feature 5.2 ==="
python3 -c "
from verify.evaluator import EVALUATION_STRATEGIES
assert len(EVALUATION_STRATEGIES) >= 3
print('PASS: evaluation strategies registered')
" && echo "=== Feature 5.2 COMPLETE ==="
```
- [ ] Step checked off

---

### Feature 5.3: Verdict Aggregation with Pass Conditions [MVP]

**Story:** Support ALL_PASS, ANY_PASS, and PERCENTAGE pass conditions.
**Depends on:** Feature 0.5

#### Implementation Steps

- [ ] **Step 1: Ensure `evaluate_pass_condition` handles all three modes**

  In `src/verify/evaluator.py`, verify or implement:
  - `ALL_PASS`: `all(r["passed"] for r in results)`
  - `ANY_PASS`: `any(r["passed"] for r in results)`
  - `PERCENTAGE`: `(passed_count / total_count * 100) >= threshold`

  **Verify:**
  ```sh
  python3 -c "
  from verify.evaluator import evaluate_pass_condition

  results = [{'passed': True}, {'passed': True}, {'passed': False}]
  assert evaluate_pass_condition('ALL_PASS', results) == False
  assert evaluate_pass_condition('ANY_PASS', results) == True
  assert evaluate_pass_condition('PERCENTAGE', results, threshold=60) == True
  assert evaluate_pass_condition('PERCENTAGE', results, threshold=80) == False
  print('OK: all pass conditions work correctly')
  "
  ```
  Expected: `OK: all pass conditions work correctly`

#### Definition of Done

```sh
echo "=== Feature 5.3 ==="
python3 -c "
from verify.evaluator import evaluate_pass_condition
assert evaluate_pass_condition('ALL_PASS', [{'passed': True}, {'passed': True}]) == True
assert evaluate_pass_condition('ALL_PASS', [{'passed': True}, {'passed': False}]) == False
assert evaluate_pass_condition('ANY_PASS', [{'passed': False}, {'passed': True}]) == True
print('PASS: pass conditions work')
" && echo "=== Feature 5.3 COMPLETE ==="
```
- [ ] Step checked off

---

## Epic 6: Jira Feedback Loop [MVP — Stories 6.1-6.2 only]

**Goal:** Connect the evaluator's verdicts to Jira.
**Depends on:** Epics 1 (Jira client) + 5 (evaluator with verdicts)
**After this epic:** Full end-to-end: Jira AC → AI → spec → tests → execution → Jira checkboxes ticked + evidence posted.

---

### Feature 6.1: Wire Evaluator to Jira Checkbox Updates [MVP]

**Story:** Evaluator verdicts automatically tick corresponding AC checkboxes on the Jira ticket.
**Depends on:** Features 1.2, 5.3

#### Implementation Steps

- [ ] **Step 1: Create Jira update integration in the pipeline**

  Extend `src/verify/pipeline.py` with `update_jira(jira_key: str, verdicts: list[dict], jira_client: JiraClient)` that:
  1. For each verdict where `passed == True`, calls `jira_client.tick_checkbox(jira_key, verdict["ac_checkbox"])`
  2. Skips false verdicts (leaves checkbox unchecked)
  3. Logs which checkboxes were updated

  **Verify:**
  ```sh
  python3 -c "
  from verify.pipeline import update_jira
  print('OK: update_jira function exists')
  "
  ```

#### Definition of Done

```sh
echo "=== Feature 6.1 ==="
python3 -c "from verify.pipeline import update_jira; print('PASS: wired')"
echo "=== Feature 6.1 COMPLETE ==="
```
- [ ] Step checked off

---

### Feature 6.2: Wire Evaluator to Evidence Comment [MVP]

**Story:** Full evidence breakdown posted as a comment on the Jira ticket.
**Depends on:** Features 1.3, 5.3

#### Implementation Steps

- [ ] **Step 1: Add evidence posting to the pipeline**

  Extend `update_jira` in `src/verify/pipeline.py` to:
  1. Call `JiraClient.format_evidence_comment(verdicts, spec_path)`
  2. Call `jira_client.post_comment(jira_key, comment)`
  3. Log the comment posting

  **Verify:**
  ```sh
  python3 -c "
  from verify.pipeline import update_jira
  from verify.jira_client import JiraClient
  # The function should accept verdicts and post evidence
  print('OK: evidence posting wired into pipeline')
  "
  ```

#### Definition of Done

```sh
echo "=== Feature 6.2 ==="
python3 -c "
from verify.pipeline import update_jira
from verify.jira_client import JiraClient
print('PASS: Jira feedback wired')
" && echo "=== Feature 6.2 COMPLETE ==="
```
- [ ] Step checked off

---

## Stretch Epics (Summarized)

The following epics are stretch goals. Each is listed with its stories and key implementation notes, but without the granular verification steps of the MVP features.

---

## Epic 6.3: Ticket Transition [STRETCH]

### Feature 6.3: Wire Evaluator to Ticket Transition

**Story:** Auto-transition ticket to "Done" when all checkboxes pass.
**Implementation:** Extend `update_jira` to call `jira_client.transition_ticket(jira_key, "Done")` when `all(v["passed"] for v in verdicts)`.

---

## Epic 7: Constitution & Repo Awareness [STRETCH]

### Feature 7.1: Repo Scanner — Stack Detection

**Story:** Auto-detect language, framework, build tool from repo files.
**Implementation:** Parse `pyproject.toml`/`package.json`/`pom.xml`/`build.gradle` to detect stack. Populate `constitution.project` section. Present for developer confirmation.

### Feature 7.2: Test Pattern Discovery

**Story:** Sample existing test files and extract patterns.
**Implementation:** Find test files via glob, extract imports/annotations/assertion styles. Classify as controller_test, service_test, integration_test. Store in `constitution.testing.patterns`.

### Feature 7.3: API Convention Discovery

**Story:** Detect base paths, auth mechanism, error format.
**Implementation:** Scan route/controller files for patterns. Detect auth from decorators/middleware. Parse error handlers for response format. Populate `constitution.api`.

---

## Epic 8: Advanced Negotiation [STRETCH]

### Feature 8.1: Phase 5 — Invariant Extraction

**Story:** Extract universal properties from AC, constitution, and data model.
**Implementation:** Create `src/verify/negotiation/phase5.py`. Extract invariants from three sources: AC text, constitution security standards, inferred from data model. Each has ID, type, rule, verification type.

### Feature 8.2: Phase 6 — Completeness Sweep

**Story:** Run a checklist of dimensions and flag gaps.
**Implementation:** Create `src/verify/negotiation/phase6.py`. Standard checklist (auth, authz, validation, schema, errors, rate limiting, pagination, caching, observability, security, data classification). Mark each: COVERED, DEFERRED, NOT ADDRESSED.

### Feature 8.3: Phase 7 — EARS Formalization & Approval

**Story:** Synthesize everything into EARS statements for final approval.
**Implementation:** Create `src/verify/negotiation/phase7.py`. Generate WHEN/SHALL, IF/THEN, WHILE/SHALL statements from all contract elements. Present for approval. On approve → freeze spec. On reject → re-enter relevant phase.

---

## Epic 9: Beyond-Code Verification Skills [STRETCH]

### Feature 9.1: New Relic Alert Config Skill

**Story:** Generate NRQL alert configurations from performance invariants.
**Implementation:** Create `src/verify/skills/newrelic_skill.py`. Read `type: performance` invariants. Generate NRQL JSON with query, threshold, duration. Register as `newrelic_alert_config` in SKILL_REGISTRY.

### Feature 9.2: Gherkin Scenario Skill

**Story:** Generate .feature files from spec contracts.
**Implementation:** Create `src/verify/skills/gherkin_skill.py`. Generate Given/When/Then scenarios with `@TAG` annotations. Register as `gherkin_scenario`.

### Feature 9.3: OpenTelemetry Instrumentation Skill

**Story:** Generate OTel span configs for monitored endpoints.
**Implementation:** Create `src/verify/skills/otel_skill.py`. Generate OTel config snippets for each observed endpoint. Register as `otel_config`.

---

## Epic 10: CI/CD & PR Automation [STRETCH]

### Feature 10.1: Automated PR Creation

**Story:** Auto-create PRs with generated spec and verification artifacts.
**Implementation:** Use GitHub REST API. Create branch per constitution naming. Commit generated files. Open PR with Jira link, spec summary, EARS statements.

### Feature 10.2: GitHub Actions Integration

**Story:** Run evaluation pipeline in CI on PR creation.
**Implementation:** Create `.github/workflows/verify.yml`. Trigger on PR. Run tests, evaluate, update Jira. Post PR comment with results.

### Feature 10.3: Spec Drift Detection

**Story:** Detect when code changes break the spec.
**Implementation:** On test failure, match `@Tag` to spec refs. Report which business requirements are violated. If spec modified, verify all artifacts regenerated.

---

## Full Pipeline Smoke Test

After completing all MVP features (Epics 0-4 + 6.1-6.2), run this end-to-end check:

```sh
echo "=== FULL MVP PIPELINE SMOKE TEST ==="

# 1. Dummy app works
python3 -c "
from fastapi.testclient import TestClient
from dummy_app.main import app
c = TestClient(app)
assert c.get('/api/v1/users/me', headers={'Authorization': 'Bearer t'}).status_code == 200
print('1. PASS: Dummy app')
"

# 2. Spec exists and is valid
python3 -c "
import yaml
spec = yaml.safe_load(open('.verify/specs/DEMO-001.yaml'))
assert spec['meta']['jira_key'] == 'DEMO-001'
print('2. PASS: Spec YAML valid')
"

# 3. Full pipeline runs end-to-end
python3 -m verify.pipeline .verify/specs/DEMO-001.yaml
echo "3. Pipeline exit code: $?"

# 4. All core modules importable
python3 -c "
from verify.generator import generate_and_write
from verify.runner import run_and_parse
from verify.evaluator import evaluate_spec
from verify.pipeline import run_pipeline
from verify.jira_client import JiraClient
from verify.llm_client import LLMClient
from verify.compiler import compile_spec
from verify.context import VerificationContext
from verify.negotiation.harness import NegotiationHarness
from verify.skills.framework import SKILL_REGISTRY
print('4. PASS: All modules importable')
"

echo "=== MVP SMOKE TEST COMPLETE ==="
```
