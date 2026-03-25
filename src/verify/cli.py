"""CLI interface for the magic-agents verification pipeline.

Feature 23: `specify` command-line tool.

Commands:
  specify negotiate <JIRA_KEY>   - Run 4-phase negotiation for a ticket
  specify compile <JIRA_KEY>     - Compile the negotiated context into a YAML spec
  specify execute <spec_path>    - Run the full pipeline (generate → run → evaluate)
  specify check <JIRA_KEY>       - Check if a spec exists for a ticket
  specify status                 - Show the status of the current session
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from verify.compiler import compile_and_write
from verify.context import VerificationContext
from verify.jira_client import JiraClient, JiraAuthError, JiraNotFoundError
from verify.llm_client import LLMClient
from verify.negotiation.cli import run_negotiation_auto, run_negotiation_cli
from verify.pipeline import load_constitution, run_pipeline, run_pipeline_with_jira

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────────────────────────────────────


def cmd_negotiate(args):
    """Run 4-phase negotiation for a Jira ticket."""
    jira_key = args.jira_key
    interactive = not args.auto

    # Fetch ticket from Jira
    print(f"Fetching {jira_key} from Jira...")
    try:
        client = JiraClient()
        issue = client.fetch_ticket(jira_key)
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")

        # Extract acceptance criteria
        ac_list = client.extract_acceptance_criteria(issue)
        if not ac_list:
            print(f"  [ERROR] No acceptance criteria found in {jira_key}")
            sys.exit(1)

        print(f"  ✓ Found {len(ac_list)} acceptance criteria")
    except JiraAuthError as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)
    except JiraNotFoundError as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Failed to fetch ticket: {e}")
        sys.exit(1)

    # Load constitution
    constitution = load_constitution()

    # Create context
    context = VerificationContext(
        jira_key=jira_key,
        jira_summary=summary,
        raw_acceptance_criteria=ac_list,
        constitution=constitution,
    )

    # Create LLM client
    llm = LLMClient()

    # Run negotiation
    if interactive:
        print(f"\nStarting interactive negotiation for {jira_key}...")
        run_negotiation_cli(context, llm)
    else:
        print(f"\nRunning auto negotiation for {jira_key}...")
        run_negotiation_auto(context, llm)

    # Mark as approved
    context.approved = True
    context.approved_by = "cli"

    print(f"\n{'=' * 60}")
    print("  Negotiation Complete")
    print(f"{'=' * 60}")
    print(f"  Jira Key:     {context.jira_key}")
    print(f"  Summary:      {context.jira_summary}")
    print(f"  ACs:          {len(context.raw_acceptance_criteria)}")
    print(f"  Classes:      {len(context.classifications)}")
    print(f"  Postcond:     {len(context.postconditions)}")
    print(f"  Precond:      {len(context.preconditions)}")
    print(f"  Fail modes:   {len(context.failure_modes)}")
    print(f"  Invariants:   {len(context.invariants)}")
    print(f"  EARS:         {len(context.ears_statements)}")

    # Optionally compile immediately
    if args.compile:
        print(f"\nCompiling spec...")
        spec_path = compile_and_write(context)
        print(f"  ✓ Spec written to {spec_path}")


def cmd_compile(args):
    """Compile negotiated context into a YAML spec."""
    jira_key = args.jira_key
    spec_dir = args.output_dir or ".verify/specs"

    # Fetch ticket from Jira
    print(f"Fetching {jira_key} from Jira...")
    try:
        client = JiraClient()
        issue = client.fetch_ticket(jira_key)
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        ac_list = client.extract_acceptance_criteria(issue)

        if not ac_list:
            print(f"  [ERROR] No acceptance criteria found in {jira_key}")
            sys.exit(1)

        print(f"  ✓ Found {len(ac_list)} acceptance criteria")
    except JiraAuthError as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)
    except JiraNotFoundError as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Failed to fetch ticket: {e}")
        sys.exit(1)

    # Load constitution
    constitution = load_constitution()

    # Create context and run negotiation
    context = VerificationContext(
        jira_key=jira_key,
        jira_summary=summary,
        raw_acceptance_criteria=ac_list,
        constitution=constitution,
    )

    llm = LLMClient()
    print(f"\nRunning negotiation phases...")
    run_negotiation_auto(context, llm)
    context.approved = True
    context.approved_by = "cli"

    # Compile spec
    print(f"\nCompiling spec...")
    spec_path = compile_and_write(context, spec_dir)

    print(f"\n{'=' * 60}")
    print("  Spec Compiled")
    print(f"{'=' * 60}")
    print(f"  Output:       {spec_path}")
    print(f"  Requirements: {len(context.classifications)}")
    print(f"  Invariants:   {len(context.invariants)}")


def cmd_execute(args):
    """Run the full verification pipeline."""
    spec_path = args.spec_path
    jira_key = args.jira_key

    if not os.path.exists(spec_path):
        print(f"[ERROR] Spec not found: {spec_path}")
        sys.exit(1)

    print(f"Running pipeline for {spec_path}...")

    if jira_key:
        verdicts = run_pipeline_with_jira(spec_path, jira_key, skip_jira=args.no_jira)
    else:
        verdicts = run_pipeline(spec_path)

    # Exit with failure if any verdict failed
    all_passed = all(v["passed"] for v in verdicts)
    sys.exit(0 if all_passed else 1)


def cmd_check(args):
    """Check if a spec exists for a ticket."""
    jira_key = args.jira_key
    spec_dir = args.spec_dir or ".verify/specs"
    spec_path = os.path.join(spec_dir, f"{jira_key}.yaml")

    print(f"Checking spec for {jira_key}...")

    if os.path.exists(spec_path):
        # Read spec metadata
        import yaml
        try:
            with open(spec_path) as f:
                spec = yaml.safe_load(f)
            meta = spec.get("meta", {})

            print(f"\n{'=' * 60}")
            print("  Spec Found")
            print(f"{'=' * 60}")
            print(f"  Jira Key:     {meta.get('jira_key', '?')}")
            print(f"  Summary:      {meta.get('jira_summary', '?')}")
            print(f"  Status:       {meta.get('status', 'unknown')}")
            print(f"  Generated:    {meta.get('generated_at', '?')}")
            print(f"  Approved By:  {meta.get('approved_by', '?')}")
            print(f"  Path:         {spec_path}")
            print(f"  Requirements: {len(spec.get('requirements', []))}")
        except Exception as e:
            print(f"  [ERROR] Failed to read spec: {e}")
            sys.exit(1)
    else:
        print(f"\n{'=' * 60}")
        print("  Spec Not Found")
        print(f"{'=' * 60}")
        print(f"  Path: {spec_path}")
        print(f"  Run 'specify compile {jira_key}' to generate it.")
        sys.exit(1)


def cmd_status(args):
    """Show the status of the current session/environment."""
    print(f"\n{'=' * 60}")
    print("  Session Status")
    print(f"{'=' * 60}")

    # Check environment
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    llm_mock = os.environ.get("LLM_MOCK", "false").lower() == "true"
    jira_url = os.environ.get("JIRA_BASE_URL", "")
    jira_email = os.environ.get("JIRA_EMAIL", "")

    print(f"\n  LLM Configuration:")
    print(f"    Mock Mode:        {llm_mock}")
    print(f"    API Key:          {'✓ configured' if api_key else '✗ not configured'}")

    print(f"\n  Jira Configuration:")
    print(f"    Base URL:         {jira_url or '(not set)'}")
    print(f"    Email:            {jira_email or '(not set)'}")
    print(f"    Auth:             {'✓ configured' if (jira_url and jira_email) else '✗ incomplete'}")

    # Check directories
    spec_dir = ".verify/specs"
    gen_dir = ".verify/generated"
    results_dir = ".verify/results"

    print(f"\n  Spec Storage:")
    spec_files = []
    if os.path.isdir(spec_dir):
        spec_files = [f for f in os.listdir(spec_dir) if f.endswith(".yaml")]
    print(f"    Directory:        {spec_dir}")
    print(f"    Specs:            {len(spec_files)}")
    if spec_files:
        for f in spec_files[:5]:
            print(f"      - {f}")
        if len(spec_files) > 5:
            print(f"      ... and {len(spec_files) - 5} more")

    print(f"\n  Generated Artifacts:")
    gen_files = []
    if os.path.isdir(gen_dir):
        gen_files = os.listdir(gen_dir)
    print(f"    Directory:        {gen_dir}")
    print(f"    Files:            {len(gen_files)}")

    print(f"\n  Test Results:")
    result_files = []
    if os.path.isdir(results_dir):
        result_files = os.listdir(results_dir)
    print(f"    Directory:        {results_dir}")
    print(f"    Files:            {len(result_files)}")


# ──────────────────────────────────────────────────────────────────────────────
# CLI setup
# ──────────────────────────────────────────────────────────────────────────────


def main():
    """Main CLI entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Root parser
    parser = argparse.ArgumentParser(
        prog="specify",
        description="Magic Agents CLI — Intent-to-Verification Spec Engine",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # ------------------------------------------------------------------
    # `specify negotiate <JIRA_KEY>`
    # ------------------------------------------------------------------
    negotiate_parser = subparsers.add_parser(
        "negotiate",
        help="Run 4-phase negotiation for a ticket",
    )
    negotiate_parser.add_argument(
        "jira_key",
        help="Jira ticket key (e.g., PROJ-1234)",
    )
    negotiate_parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in non-interactive mode (auto-approve all phases)",
    )
    negotiate_parser.add_argument(
        "--compile",
        action="store_true",
        help="Automatically compile spec after negotiation",
    )
    negotiate_parser.set_defaults(func=cmd_negotiate)

    # ------------------------------------------------------------------
    # `specify compile <JIRA_KEY>`
    # ------------------------------------------------------------------
    compile_parser = subparsers.add_parser(
        "compile",
        help="Compile negotiated context into a YAML spec",
    )
    compile_parser.add_argument(
        "jira_key",
        help="Jira ticket key (e.g., PROJ-1234)",
    )
    compile_parser.add_argument(
        "--output-dir",
        "-o",
        help="Output directory for specs (default: .verify/specs)",
    )
    compile_parser.set_defaults(func=cmd_compile)

    # ------------------------------------------------------------------
    # `specify execute <spec_path>`
    # ------------------------------------------------------------------
    execute_parser = subparsers.add_parser(
        "execute",
        help="Run the full pipeline (generate → run → evaluate)",
    )
    execute_parser.add_argument(
        "spec_path",
        help="Path to the spec YAML file",
    )
    execute_parser.add_argument(
        "--jira-key",
        "-j",
        help="Jira ticket key (optional; enables Jira updates)",
    )
    execute_parser.add_argument(
        "--no-jira",
        action="store_true",
        help="Skip Jira updates even if key is provided",
    )
    execute_parser.set_defaults(func=cmd_execute)

    # ------------------------------------------------------------------
    # `specify check <JIRA_KEY>`
    # ------------------------------------------------------------------
    check_parser = subparsers.add_parser(
        "check",
        help="Check if a spec exists for a ticket and its status",
    )
    check_parser.add_argument(
        "jira_key",
        help="Jira ticket key (e.g., PROJ-1234)",
    )
    check_parser.add_argument(
        "--spec-dir",
        help="Spec directory (default: .verify/specs)",
    )
    check_parser.set_defaults(func=cmd_check)

    # ------------------------------------------------------------------
    # `specify status`
    # ------------------------------------------------------------------
    status_parser = subparsers.add_parser(
        "status",
        help="Show the status of the current session/environment",
    )
    status_parser.set_defaults(func=cmd_status)

    # Parse and run
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Run the selected command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n[Interrupted by user]")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Command failed: {e}")
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
