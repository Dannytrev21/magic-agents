## Epic 10: CI/CD & PR Automation [STRETCH]

> **Design references:** CI integration follows harness engineering's hooks pattern — event-driven scripts executing at lifecycle points (PR creation, test completion, failure detection). The spec drift detection implements the back-pressure mechanism: generated artifacts must stay in sync with the spec. See [reference-library.md §3](reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability) for hooks and verification patterns. The CI skills could be implemented as Agent Skills with SKILL.md files that describe the GitHub Actions workflow and PR formatting conventions ([agent-skills-reference.md §4](agent-skills-reference.md)).

### Feature 10.1: Automated PR Creation

**Story:** Auto-create PRs with generated spec and verification artifacts.
**Implementation:** Use `gh` CLI or GitHub REST API. After `compile_and_write()`, create a branch named `verify/{jira_key}`, commit the spec YAML + generated test files + any config artifacts. Open a PR with: Jira link in title, EARS statements in body, traceability map as a markdown table, and a checklist of verification refs. The PR description follows the spec-as-contract principle — reviewers see exactly what will be verified and how.

### Feature 10.2: GitHub Actions Integration

**Story:** Run evaluation pipeline in CI on PR creation.
**Implementation:** Create `.github/workflows/verify.yml`. Trigger on PR labels or paths matching `.verify/**`. Steps: install deps → run `python -m verify.pipeline .verify/specs/{key}.yaml` → parse verdicts → post PR comment with pass/fail per AC checkbox → if Jira configured, update checkboxes and post evidence. The workflow is the harness's CI hook — it fires on the PR lifecycle event and runs the deterministic pipeline.

### Feature 10.3: Spec Drift Detection

**Story:** Detect when code changes break the spec.
**Implementation:** On test failure in CI, match `[REQ-NNN.FAIL-NNN]` tags from test names to spec refs. Report which business requirements (AC checkboxes) are violated — not just "3 tests failed" but "AC checkbox 0 ('User can view profile') is no longer satisfied because FAIL-002 (user not found) now returns 500 instead of 404." If the spec YAML is modified, verify all downstream artifacts (generated tests, alert configs) are regenerated — stale artifacts break traceability.

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
