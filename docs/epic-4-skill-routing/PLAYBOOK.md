## Epic 4: Multi-Skill Routing & Test Generation [MVP]

**Goal:** Replace the hardcoded test generator with **Claude Agent Skills** that read spec contracts and generate proof-of-correctness artifacts (tests, configs, scenarios). Each verification skill follows the same SKILL.md standard as the negotiation phase skills — the pipeline uses Agent Skills end-to-end.
**Depends on:** Epic 3 (specs with routing tables exist)
**After this epic:** The spec drives real verification artifact generation via specialized Agent Skills dispatched by the routing table.

> **Design references:** This epic is where the Agent Skills pattern becomes concrete. Each `VerificationSkill` follows the [SKILL.md open standard](https://agentskills.io) (see [agent-skills-reference.md §3](agent-skills-reference.md) for the complete specification). The `SKILL_REGISTRY` + `dispatch_skills` implements the three-stage loading mechanism: **Level 1 (Metadata)** — skill name + description always in context for discovery; **Level 2 (Instructions)** — SKILL.md body loaded when the routing table dispatches to this skill; **Level 3 (Resources)** — templates, reference docs, and scripts loaded during execution ([reference-library.md §2](reference-library.md#2-agent-skills--modular-discoverable-capability-packages)). The tag enforcer is a back-pressure mechanism from harness engineering — agents validate their own work before declaring success ([reference-library.md §3](reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability)).

### Agent Skills Architecture for Verification Skills

Following Block's 3 Principles ([agent-skills-reference.md §6](agent-skills-reference.md)):

**Principle 1 (What agents should NOT decide):** Tag coverage validation, spec schema validation, pass condition evaluation — all handled by deterministic scripts (`tag_enforcer.py`, `validate.py`). The routing table itself is a simple dict lookup in `compiler.py`, not an AI decision.

**Principle 2 (What agents SHOULD decide):** Adapting test templates to specific contract shapes, generating setup fixtures from semi-formal precondition expressions, translating constraint patterns into assertion code.

**Principle 3 (Constitutional rules, not suggestions):** Each skill's SKILL.md includes explicit `MUST`/`FORBIDDEN` sections. The skill description (Level 1 metadata) includes trigger terms for auto-discovery. Instructions explain *why* things are important (not just what to do) — this is more effective than heavy-handed MUSTs for smart models.

### Proof-of-Correctness Skills — Directory Structure

Verification skills live in `.claude/skills/verify-*/` alongside the negotiation phase skills, following the same [Agent Skills open standard](https://agentskills.io). Each skill has a SKILL.md defining its persona, input/output contract, and constitutional rules — just like the phase skills.

```
.claude/skills/
├── phase1-classification/     # Spec generation skill (Epic 2)
│   ├── SKILL.md
│   └── SCHEMA.md
├── phase2-postconditions/     # Spec generation skill (Epic 2)
│   ├── SKILL.md
│   └── SCHEMA.md
├── phase3-preconditions/      # Spec generation skill (Epic 2)
│   └── SKILL.md
├── phase4-failure-modes/      # Spec generation skill (Epic 2)
│   └── SKILL.md
├── verify-pytest/             # Proof-of-correctness skill (this epic)
│   ├── SKILL.md               # Instructions: generate pytest tests from spec contracts
│   ├── TEMPLATES.md           # Test templates for success, failure, invariant patterns
│   └── scripts/
│       └── validate_tags.py   # Ensure all spec refs are tagged
├── verify-newrelic/           # Proof-of-correctness skill (Epic 9 stretch)
│   └── SKILL.md
├── verify-gherkin/            # Proof-of-correctness skill (Epic 9 stretch)
│   └── SKILL.md
└── verify-otel/               # Proof-of-correctness skill (Epic 9 stretch)
    └── SKILL.md
```

The Python runtime dispatches to these skills via `src/verify/skills/framework.py`:
```
src/verify/skills/
├── framework.py           # VerificationSkill base class + SKILL_REGISTRY + dispatch_skills()
├── pytest_skill.py        # Reads .claude/skills/verify-pytest/SKILL.md, generates tests
├── tag_enforcer.py        # Cross-cutting tag coverage validation
└── (future skill runners)
```

Each skill follows the progressive disclosure pattern from [agent-skills-reference.md §2](agent-skills-reference.md):
- **SKILL.md** is the only required file (<500 lines recommended)
- **TEMPLATES.md** and other .md files are loaded as-needed references
- **Scripts** execute via bash — only their *output* enters context, not the code itself
- **The routing table** in `compiler.py` determines which skill handles which requirement type

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

