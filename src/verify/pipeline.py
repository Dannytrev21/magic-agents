"""End-to-end verification pipeline — single command from spec to verdicts."""

import logging
import sys

from verify.evaluator import evaluate_spec
from verify.generator import generate_and_write
from verify.runner import run_and_parse

logger = logging.getLogger(__name__)


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

    return verdicts


def update_jira(
    jira_key: str,
    verdicts: list[dict],
    jira_client,
    spec_path: str = "",
) -> None:
    """Wire evaluator verdicts to Jira checkbox updates and evidence comments.

    Feature 6.1: Tick AC checkboxes for passed verdicts.
    Feature 6.2: Post evidence comment with full breakdown.

    Args:
        jira_key: The Jira ticket key (e.g., "DEV-17")
        verdicts: List of verdict dicts from evaluate_spec
        jira_client: A JiraClient instance
        spec_path: Path to the spec file for evidence formatting
    """
    if not verdicts:
        logger.info(f"No verdicts to update for {jira_key}")
        return

    # Feature 6.1: Tick checkboxes for passed verdicts
    passed_indices = [v["ac_checkbox"] for v in verdicts if v["passed"]]
    if passed_indices:
        logger.info(f"Ticking checkboxes {passed_indices} on {jira_key}")
        jira_client.tick_checkboxes(jira_key, passed_indices)

    # Feature 6.2: Post evidence comment
    if spec_path:
        comment = jira_client.format_evidence_comment(verdicts, spec_path)
        logger.info(f"Posting evidence comment to {jira_key}")
        jira_client.post_comment(jira_key, comment)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m verify.pipeline <spec_path>")
        sys.exit(2)

    spec_path = sys.argv[1]
    verdicts = run_pipeline(spec_path)
    sys.exit(0 if all(v["passed"] for v in verdicts) else 1)
