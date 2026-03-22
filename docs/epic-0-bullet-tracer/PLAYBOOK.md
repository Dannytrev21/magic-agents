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

