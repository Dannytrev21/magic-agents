## Epic 3: Formal Spec Emission [MVP] ✅ COMPLETE

**Goal:** Compile negotiation output into a complete, validated YAML spec with traceability map.
**Depends on:** Epic 2 (negotiation produces the context to serialize)
**After this epic:** The negotiation produces a real `.verify/specs/{jira_key}.yaml` file.

> **Design references:** The spec is the intelligence boundary — AI handles the fuzzy-to-formal translation (Epics 2-3), everything downstream is deterministic (Epics 4-6). This follows BMAD's documentation-first principle: "specs become the contract, not your latest chat message" ([reference-library.md §4](reference-library.md#4-bmad--agent-as-code-agile-development-framework)). The verification routing table is a simple lookup — zero AI — following the harness engineering principle that deterministic operations belong in scripts, not agents ([reference-library.md §3](reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability)).

### Implementation Notes (Learned During Development)

**Compiler location:** `src/verify/compiler.py` — three public functions: `compile_spec()` (pure dict assembly), `write_spec()` (YAML serialization), `compile_and_write()` (convenience wrapper that sets `context.spec_path`).

**Schema restructuring:** The critical transform is Phase 2's postcondition schema `{field: {type, required: true}}` → generator's expected format `{type: "object", required: [...], properties: {...}, forbidden_fields: [...]}`. The compiler iterates the schema dict, extracts required field names into a list, and strips the `required` key from each property.

**Routing table:** `ROUTING_TABLE` in `compiler.py` maps 6 requirement types to verification skills: `api_behavior` → `pytest_unit_test`, `performance_sla` → `newrelic_alert_config`, `security_invariant` → `pytest_unit_test`, `observability` → `otel_config`, `compliance` → `gherkin_scenario`, `data_constraint` → `pytest_unit_test`. This is a deterministic lookup — zero AI.

**Traceability:** The compiler builds `traceability.ac_mappings` from compiled requirements (not from synthesis). Each AC gets refs from its requirement's contract elements with routing-aware `verification_type` (`test_result`, `config_validation`, `deployment_check`). Invariants are cross-cutting — they appear in every AC mapping (many-to-many).

**Generator compatibility verified E2E:** Compiled specs are consumed by `generator.py` to produce valid pytest code, which runs against the dummy app and feeds into `evaluator.py` for verdicts. The full chain: `VerificationContext` → `compile_and_write()` → `.yaml` → `generate_tests()` → `run_and_parse()` → `evaluate_spec()` → verdicts.

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

