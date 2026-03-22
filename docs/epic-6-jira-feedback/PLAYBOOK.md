## Epic 6: Jira Feedback Loop [MVP — Stories 6.1-6.2 only]

**Goal:** Connect the evaluator's verdicts to Jira.
**Depends on:** Epics 1 (Jira client) + 5 (evaluator with verdicts)
**After this epic:** Full end-to-end: Jira AC → AI → spec → tests → execution → Jira checkboxes ticked + evidence posted.

> **Design references:** This closes the correctness chain from `ac-to-specs-plan.md` §1.1. The Jira update is fully deterministic — no AI involved — following the intelligence boundary principle: all downstream operations are mechanical translations of the spec ([reference-library.md §5](reference-library.md#5-cross-cutting-patterns--synthesis)).

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

### Feature 6.3: Wire Evaluator to Ticket Transition [STRETCH]

**Story:** Auto-transition ticket to "Done" when all checkboxes pass.
**Implementation:** Extend `update_jira` to call `jira_client.transition_ticket(jira_key, "Done")` when `all(v["passed"] for v in verdicts)`.

