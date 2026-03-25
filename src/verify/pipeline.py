"""End-to-end verification pipeline — single command from spec to verdicts.

Includes Jira feedback loop: checkbox ticking, evidence comments, and ticket transitions.
"""

import logging
import os
import sys
from typing import Optional

import yaml

from verify.evaluator import evaluate_spec
from verify.generator import generate_and_write
from verify.runner import run_and_parse

logger = logging.getLogger(__name__)


def load_constitution(path: str = "constitution.yaml") -> dict:
    """Load a constitution file from disk.

    Searches in order:
    1. Exact path provided
    2. Current working directory
    3. .verify/constitution.yaml
    4. Target repo root
    """
    search_paths = [
        path,
        os.path.join(os.getcwd(), "constitution.yaml"),
        os.path.join(".verify", "constitution.yaml"),
    ]

    for candidate in search_paths:
        if os.path.exists(candidate):
            with open(candidate) as f:
                constitution = yaml.safe_load(f) or {}
            logger.info(f"Loaded constitution from {candidate}")
            return constitution

    logger.warning("No constitution.yaml found; using empty constitution")
    return {}


def run_pipeline(spec_path: str) -> list[dict]:
    """Run the full verification pipeline.

    1. Read spec → 2. Generate tests → 3. Run tests → 4. Parse results → 5. Evaluate
    """
    print(f"{'=' * 60}")
    print(f"  Verification Pipeline")
    print(f"  Spec: {spec_path}")
    print(f"{'=' * 60}")

    # Step 1: Generate tests from spec
    print("\n[1/3] Generating tests from spec...")
    test_path = generate_and_write(spec_path)
    print(f"  → Generated: {test_path}")

    # Step 2: Run tests and parse results
    print("\n[2/3] Running tests...")
    results = run_and_parse(test_path, ".verify/results")
    cases = results["test_cases"]
    passed = sum(1 for c in cases if c["status"] == "passed")
    print(f"  → {passed}/{len(cases)} tests passed")

    # Step 3: Evaluate against spec traceability map
    print("\n[3/3] Evaluating verdicts...")
    verdicts = evaluate_spec(spec_path, results)

    # Print results
    _print_verdicts(verdicts)

    return verdicts


def run_pipeline_with_jira(
    spec_path: str,
    jira_key: Optional[str] = None,
    skip_jira: bool = False,
) -> list[dict]:
    """Run the full pipeline and optionally update Jira with results.

    Extends run_pipeline with Jira feedback loop (Epic 6):
    - Tick AC checkboxes for passing verdicts
    - Post evidence comment
    - Transition ticket to Done if all pass
    """
    verdicts = run_pipeline(spec_path)

    if skip_jira or not jira_key:
        return verdicts

    # Attempt Jira update
    try:
        update_jira(jira_key, verdicts, spec_path)
    except Exception as e:
        logger.warning(f"Jira update failed: {e}")
        print(f"\n  [WARN] Jira update failed: {e}")

    return verdicts


def update_jira(
    jira_key: str,
    verdicts: list[dict],
    spec_path: str = "",
    transition_on_pass: bool = True,
) -> dict:
    """Update Jira ticket with verification results.

    Features 6.1 + 6.2 + 6.3:
    1. Tick AC checkboxes for passing verdicts
    2. Post evidence comment with full breakdown
    3. Transition to Done if all pass (optional)

    Returns a summary dict of what was updated.
    """
    from verify.jira_client import JiraClient

    client = JiraClient()
    result = {
        "checkboxes_ticked": [],
        "comment_posted": False,
        "transitioned": False,
        "all_passed": False,
    }

    # Feature 6.1: Tick AC checkboxes
    passing_indices = [v["ac_checkbox"] for v in verdicts if v["passed"]]
    if passing_indices:
        try:
            client.tick_checkboxes(jira_key, passing_indices)
            result["checkboxes_ticked"] = passing_indices
            logger.info(f"Ticked {len(passing_indices)} checkboxes on {jira_key}")
            print(f"\n  [JIRA] Ticked {len(passing_indices)} AC checkboxes on {jira_key}")
        except Exception as e:
            logger.warning(f"Failed to tick checkboxes on {jira_key}: {e}")
            print(f"\n  [WARN] Failed to tick checkboxes: {e}")

    # Feature 6.2: Post evidence comment
    try:
        comment = JiraClient.format_evidence_comment(verdicts, spec_path)
        client.post_comment(jira_key, comment)
        result["comment_posted"] = True
        logger.info(f"Posted evidence comment on {jira_key}")
        print(f"  [JIRA] Posted evidence comment on {jira_key}")
    except Exception as e:
        logger.warning(f"Failed to post evidence comment on {jira_key}: {e}")
        print(f"  [WARN] Failed to post evidence comment: {e}")

    # Feature 6.3: Transition to Done if all pass
    all_passed = all(v["passed"] for v in verdicts)
    result["all_passed"] = all_passed

    if all_passed and transition_on_pass:
        try:
            transitioned = client.transition_ticket(jira_key, "Done")
            result["transitioned"] = transitioned
            if transitioned:
                logger.info(f"Transitioned {jira_key} to Done")
                print(f"  [JIRA] Transitioned {jira_key} to Done")
            else:
                print(f"  [JIRA] Could not transition {jira_key} (no matching transition)")
        except Exception as e:
            logger.warning(f"Failed to transition {jira_key}: {e}")
            print(f"  [WARN] Failed to transition ticket: {e}")

    return result


def _print_verdicts(verdicts: list[dict]) -> None:
    """Pretty-print verdict results to stdout."""
    print(f"\n{'=' * 60}")
    print("  RESULTS")
    print(f"{'=' * 60}")

    all_passed = True
    for v in verdicts:
        icon = "PASS" if v["passed"] else "FAIL"
        print(f"\n  [{icon}] AC[{v['ac_checkbox']}]: \"{v['ac_text']}\"")
        print(f"         {v['summary']} ({v['pass_condition']})")
        for ev in v["evidence"]:
            ev_icon = "+" if ev["passed"] else "x"
            print(f"         [{ev_icon}] {ev['ref']}: {ev['details']}")
        if not v["passed"]:
            all_passed = False

    print(f"\n{'=' * 60}")
    if all_passed:
        print("  OVERALL: ALL AC CHECKBOXES PASSED")
    else:
        print("  OVERALL: SOME AC CHECKBOXES FAILED")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m verify.pipeline <spec_path>")
        sys.exit(2)

    spec_path = sys.argv[1]
    jira_key = sys.argv[2] if len(sys.argv) > 2 else None

    if jira_key:
        verdicts = run_pipeline_with_jira(spec_path, jira_key)
    else:
        verdicts = run_pipeline(spec_path)

    sys.exit(0 if all(v["passed"] for v in verdicts) else 1)
