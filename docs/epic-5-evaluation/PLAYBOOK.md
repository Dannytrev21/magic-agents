## Epic 5: Evaluation Engine (Full) [MVP]

**Goal:** Extend the evaluator to handle multiple verification types and format strategies.
**Depends on:** Epic 0 (basic evaluator), Epic 4 (generated tests with tags)
**After this epic:** The evaluator handles test results, deployment checks, and config validations.

> **Design references:** The multi-format parser and evaluation strategies implement harness engineering's back-pressure pattern — make verification context-efficient by auto-detecting formats and merging results. The pass condition logic (ALL_PASS / ANY_PASS / PERCENTAGE) maps directly to Sherpa's guard conditions on state transitions ([reference-library.md §1](reference-library.md#1-sherpa--model-driven-agent-orchestration-via-state-machines), [reference-library.md §3](reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability)).

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

