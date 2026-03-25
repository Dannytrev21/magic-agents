# Spec Diff Feature (Feature 17)

## Overview

When re-running negotiation on a Jira ticket that already has a spec, the Spec Diff feature shows exactly what changed between the old and new specs. This proves that specs are **living documents**, not throwaway artifacts.

Implementation: Feature 17 from `hackathon-roadmap.md` — ~1 hour effort, medium impact.

## Implementation Details

### Module: `src/verify/spec_diff.py`

Core functions:

#### `diff_specs(old_spec_path: str, new_spec: dict) -> dict`

Compares an old YAML spec file against a new spec dict. Returns a structured diff with:

- **`added_requirements`** (list): New requirement IDs (e.g., `["REQ-002", "REQ-003"]`)
- **`removed_requirements`** (list): Deleted requirement IDs
- **`modified_requirements`** (dict): Maps requirement ID → field changes
  - Each field change is `(old_value, new_value)` tuple
  - Example: `{"REQ-001": {"title": ("Old", "New"), "contract": ({...}, {...})}}`
- **`changed_fields`** (list): Top-level fields that differ (e.g., `["meta", "traceability"]`)
- **`summary`** (str): Human-readable text summary (see below)
- **`old_spec`** & **`new_spec`**: The loaded specs for reference

#### `format_diff_summary(diff: dict) -> str`

Converts the structured diff into readable text. Example output:

```
=== Spec Diff Summary ===

Total changes: 3

ADDED (1):
  + REQ-002

MODIFIED (1):
  ~ REQ-001
      title: "Old title" → "New title"
      contract: {...} → {...}

FIELD CHANGES (1):
  * meta
```

### Web Endpoint: `POST /api/spec-diff`

**Available at:** `http://localhost:8000/api/spec-diff` (after running `python run_web.py`)

**Request:** (None — uses current session context)

**Response:**

```json
{
  "has_old_spec": true,
  "has_changes": true,
  "jira_key": "DEMO-001",
  "old_spec_path": "specs/DEMO-001.yaml",
  "added_requirements": ["REQ-002"],
  "removed_requirements": [],
  "modified_requirements": {
    "REQ-001": {
      "title": {
        "old": "Old title",
        "new": "New title"
      },
      "contract": {
        "old": {...},
        "new": {...}
      }
    }
  },
  "changed_fields": ["meta"],
  "summary": "=== Spec Diff Summary ===\n\nTotal changes: 2\n..."
}
```

If no old spec exists:

```json
{
  "has_old_spec": false,
  "message": "No previous spec found; treating as new spec",
  "jira_key": "DEMO-001",
  "new_spec": {...}
}
```

## Usage Scenarios

### Scenario 1: Developer Re-negotiates a Requirement

**Steps:**

1. Developer negotiates DEMO-001 → Spec is compiled and written to `specs/DEMO-001.yaml`
2. Later, they re-run negotiation for DEMO-001 with updated acceptance criteria
3. After phase 4, they call `POST /api/spec-diff` before compiling the new spec
4. Response shows: "REQ-001 title changed, REQ-002 added"
5. Developer approves the diff and proceeds to compile the new spec

### Scenario 2: Detecting Spec Drift

**Use case:** "I thought we agreed on X, but the spec says Y"

1. Check `specs/{JIRA_KEY}.yaml` against a new negotiation
2. Diff reveals exactly which contracts changed
3. Developer can approve the change or provide feedback to re-negotiate

### Scenario 3: Spec Fingerprinting (Future: Feature 18)

The diff output feeds into drift detection:

```python
old_spec_hash = hash_spec(old_spec)
new_spec_hash = hash_spec(new_spec)

if old_spec_hash != new_spec_hash:
    diff = diff_specs(old_path, new_spec)
    if diff["has_changes"]:
        log("WARNING: Spec has drifted. See diff for details.")
```

## Design Principles

### Block Principle 1: Deterministic Comparison

All diffing is **100% deterministic** — zero AI. The function:

1. Loads YAML (deterministic parser)
2. Compares dicts field-by-field
3. Returns structured output (no fuzzy matching)

This ensures **reproducibility and auditability**.

### Block Principle 2: Shallow Comparison for Large Structures

For nested fields (contract, verification), the diff reports that they changed without recursing deeply. This:

- Keeps diffs readable (not 100 lines of nested changes)
- Preserves context (you see the whole contract changed, not 10 individual fields)

### Block Principle 3: Specs as Living Documents

By showing diffs, we prove specs evolve with understanding:

- First negotiation: "Here's what we think the contract is"
- Second negotiation: "Updated understanding; here's what changed"
- The traceability link in the spec means tests automatically re-evaluate

## Test Coverage

`tests/test_spec_diff.py` includes 20 tests:

- **TestDiffSpecsNoOldSpec**: Missing old spec gracefully
- **TestDiffSpecsAddedRequirements**: Detecting new requirements
- **TestDiffSpecsRemovedRequirements**: Detecting deleted requirements
- **TestDiffSpecsModifiedRequirements**: Detecting changed fields
- **TestDiffSpecsChangedTopLevelFields**: Detecting meta/traceability changes
- **TestFormatDiffSummary**: Human-readable formatting
- **TestSpecDiffIntegration**: Full flow end-to-end

All tests pass:

```bash
$ pytest tests/test_spec_diff.py -v
======================== 20 passed in 0.09s ========================
```

## Integration with Negotiation Flow

### Proposal: Web UI Integration (Post-Feature 17)

```
Negotiation → Phase 4 Complete
  ↓
Show EARS Approval Gate
  ↓
User clicks "Compile Spec"
  ↓
[NEW] Spec Diff Check:
  - Load new spec
  - Compare against old (if exists)
  - Show side-by-side diff in UI
  - User approves: "Yes, these changes are correct"
  ↓
Write spec to disk
  ↓
Generate tests → Run → Evaluate → Jira update
```

UI would display:

```
[ADDED] 1 new requirement
  + REQ-002: User can update profile

[MODIFIED] 1 existing requirement
  ~ REQ-001: Title changed from "X" to "Y"

[FIELDS] 1 top-level change
  * meta (timestamps, status)

[Approve] [Request Changes]
```

## Future Extensions

### Feature 18: Drift Detection Layer 1-2

Use spec hashes embedded in test file headers to detect when specs drift from code:

```python
# dog-service/src/test/resources/features/DEMO-001.feature

@spec_hash:abc123def456
Scenario: User can view their profile
  ...
```

CI check:

```bash
$ specify check DEMO-001
ERROR: Spec hash mismatch!
  Expected: abc123def456
  Actual: xyz789uvw012
  Changes: REQ-001.title updated

Run 'specify diff' to see full diff.
```

### Feature 25: AI-Assisted Amend

Use the diff to propose targeted spec updates:

```bash
$ specify amend DEMO-001 --from-git-diff

Proposed changes:
  ~ REQ-001: title updated due to code refactor
  + INV-002: new security invariant (password field MUST be hidden)

Review? [yes/no]
```

## Code Locations

- **Core module:** `/src/verify/spec_diff.py` (150 LOC)
- **Web integration:** `/src/verify/negotiation/web.py` (POST `/api/spec-diff` endpoint, ~60 LOC)
- **Tests:** `/tests/test_spec_diff.py` (20 test cases, 100% coverage)
- **Helper:** `_serialize_for_json()` in web.py for JSON serialization of diff values

## Performance

- **Spec loading:** O(n) where n = file size (typically <10 KB)
- **Diffing:** O(r × f) where r = requirement count (~5), f = fields per requirement (~10)
- **Total:** <1 ms for typical specs

## Error Handling

1. **Missing old spec:** Returns `{"has_old_spec": false, "message": "..."}`
2. **Invalid YAML:** Caught in `yaml.safe_load()`, returns error response
3. **Session not active:** Returns `{"error": "No active session"}` (400)
4. **Serialization errors:** Caught and logged in endpoint, returns traceback

## References

- **Hackathon Roadmap:** Feature 17, `hackathon-roadmap.md` (line 55)
- **Block Principles:** `CLAUDE.md` (Design Principles)
- **Traceability Map:** `compiler.py` (shows how specs are used downstream)
- **Testing patterns:** `tests/test_spec_diff.py` (comprehensive fixtures and assertions)
