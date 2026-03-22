"""Interactive CLI for the negotiation loop + non-interactive auto mode."""

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.harness import NegotiationHarness
from verify.negotiation.phase1 import run_phase1
from verify.negotiation.phase2 import run_phase2
from verify.negotiation.phase3 import run_phase3
from verify.negotiation.phase4 import run_phase4
from verify.negotiation.synthesis import run_synthesis

_PHASE_SKILLS = [
    ("Phase 1 of 4: Interface & Actor Discovery", run_phase1),
    ("Phase 2 of 4: Happy Path Contract", run_phase2),
    ("Phase 3 of 4: Precondition Formalization", run_phase3),
    ("Phase 4 of 4: Failure Mode Enumeration", run_phase4),
]


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _display_results(label: str, items: list[dict]) -> None:
    """Pretty-print a list of result dicts."""
    if not items:
        print(f"  (no {label} produced)")
        return
    for item in items:
        parts = []
        for key, val in item.items():
            if key in ("schema", "body", "interface"):
                continue  # skip nested dicts for brevity
            parts.append(f"{key}={val}")
        print(f"  - {', '.join(parts)}")


# ------------------------------------------------------------------
# Interactive CLI
# ------------------------------------------------------------------


def run_negotiation_cli(context: VerificationContext, llm: LLMClient) -> None:
    """Run the negotiation interactively — displays proposals and waits for input."""
    harness = NegotiationHarness(context)

    _print_section(f"Negotiation: {context.jira_key} — {context.jira_summary}")
    print("\n  Acceptance Criteria:")
    for ac in context.raw_acceptance_criteria:
        check = "x" if ac.get("checked") else " "
        print(f"  [{check}] {ac['index']}: {ac['text']}")

    for title, skill_fn in _PHASE_SKILLS:
        _print_section(title)
        results = skill_fn(context, llm)
        _display_results(title.split(":")[-1].strip().lower(), results)

        harness.add_to_log(
            harness.current_phase, "ai",
            f"{title}: produced {len(results)} items",
        )

        while True:
            user_input = input("\n  [approve / skip / or type feedback] > ").strip()
            if user_input.lower() in ("approve", "skip", ""):
                harness.add_to_log(harness.current_phase, "human", user_input or "approve")
                break
            else:
                # Feedback loop — re-run with developer's input
                harness.add_to_log(harness.current_phase, "human", user_input)
                print("\n  Revising based on your feedback...")
                results = skill_fn(context, llm, feedback=user_input)
                _print_section(f"{title} (revised)")
                _display_results(title.split(":")[-1].strip().lower(), results)
                harness.add_to_log(
                    harness.current_phase, "ai",
                    f"{title} (revised): produced {len(results)} items",
                )

        harness.advance_phase()

    # Post-negotiation synthesis: invariants, EARS, traceability
    _print_section("Synthesis")
    run_synthesis(context)
    print(f"  Invariants:    {len(context.invariants)}")
    print(f"  EARS:          {len(context.ears_statements)}")
    print(f"  Traceability:  {len(context.traceability_map.get('ac_mappings', []))} AC mappings")

    _print_section("Negotiation Complete")
    print(f"  Classifications: {len(context.classifications)}")
    print(f"  Postconditions:  {len(context.postconditions)}")
    print(f"  Preconditions:   {len(context.preconditions)}")
    print(f"  Failure modes:   {len(context.failure_modes)}")
    print(f"  Invariants:      {len(context.invariants)}")
    print(f"  EARS statements: {len(context.ears_statements)}")
    print(f"  Log entries:     {len(context.negotiation_log)}")


# ------------------------------------------------------------------
# Non-interactive (auto) mode
# ------------------------------------------------------------------


def run_negotiation_auto(
    context: VerificationContext,
    llm: LLMClient,
    answers: list[str] | None = None,
) -> None:
    """Run all negotiation phases without prompting — for CI/testing.

    Args:
        context: The VerificationContext to populate.
        llm: LLM client (typically in mock mode).
        answers: Optional list of answers per phase. Defaults to "approve" for all.
    """
    harness = NegotiationHarness(context)
    answers = answers or ["approve"] * len(_PHASE_SKILLS)

    for i, (title, skill_fn) in enumerate(_PHASE_SKILLS):
        results = skill_fn(context, llm)
        answer = answers[i] if i < len(answers) else "approve"

        harness.add_to_log(
            harness.current_phase, "ai",
            f"{title}: produced {len(results)} items",
        )
        harness.add_to_log(harness.current_phase, "human", answer)
        harness.advance_phase()

    # Post-negotiation synthesis
    run_synthesis(context)
