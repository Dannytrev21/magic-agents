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

