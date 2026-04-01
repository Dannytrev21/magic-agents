"""VerificationContext — single data object threaded through every negotiation phase."""

from dataclasses import dataclass, field


@dataclass
class VerificationContext:
    # Required init fields
    jira_key: str
    jira_summary: str
    raw_acceptance_criteria: list[dict]
    constitution: dict

    # Current negotiation phase
    current_phase: str = "phase_0"

    # Phase outputs — populated as negotiation progresses
    classifications: list[dict] = field(default_factory=list)
    postconditions: list[dict] = field(default_factory=list)
    preconditions: list[dict] = field(default_factory=list)
    failure_modes: list[dict] = field(default_factory=list)
    invariants: list[dict] = field(default_factory=list)
    verification_routing: dict = field(default_factory=dict)
    ears_statements: list[dict] = field(default_factory=list)
    traceability_map: dict = field(default_factory=dict)

    # Approval gate
    approved: bool = False
    approved_by: str = ""
    approved_at: str = ""

    # Post-spec generation
    spec_path: str = ""
    generated_files: dict = field(default_factory=dict)

    # Evaluation
    verdicts: list[dict] = field(default_factory=list)
    all_passed: bool = False

    # Codebase index — optional, from explore agent (P11)
    codebase_index: dict | None = None

    # Negotiation log — timestamped entries from add_to_log
    negotiation_log: list[dict] = field(default_factory=list)

    # Runtime session metadata
    session_id: str = ""
    usage: dict = field(default_factory=dict)
