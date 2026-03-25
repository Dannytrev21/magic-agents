"""Post-negotiation synthesis — builds traceability map, EARS statements, and invariants.

Runs after Phase 4 to populate remaining context fields deterministically (no LLM).
"""

from verify.context import VerificationContext


def extract_invariants(context: VerificationContext) -> list[dict]:
    """Extract security invariants from the constitution.

    These are deterministic — no AI involved.
    """
    invariants: list[dict] = []
    security_inv = (
        context.constitution
        .get("verification_standards", {})
        .get("security_invariants", [])
    )
    for i, text in enumerate(security_inv):
        invariants.append({
            "id": f"INV-{i + 1:03d}",
            "description": text,
            "category": "security",
        })

    # Also derive invariants from postcondition forbidden_fields
    forbidden: set[str] = set()
    for p in context.postconditions:
        for f in p.get("forbidden_fields", []):
            forbidden.add(f)
    if forbidden:
        invariants.append({
            "id": f"INV-{len(invariants) + 1:03d}",
            "description": f"Response MUST NOT contain fields: {', '.join(sorted(forbidden))}",
            "category": "security",
        })

    context.invariants = invariants
    return invariants


def generate_ears_statements(context: VerificationContext) -> list[str]:
    """Generate EARS statements from postconditions + failure modes.

    EARS patterns:
      WHEN {condition} THEN {system} SHALL {action}
      IF {condition} THEN {response}
      WHILE {invariant} {behavior} SHALL {property}
    """
    ears: list[str] = []

    # Happy path EARS from postconditions
    for pc in context.postconditions:
        iface = _find_interface_for_ac(context, pc.get("ac_index"))
        method = iface.get("method", "?") if iface else "?"
        path = iface.get("path", "?") if iface else "?"
        ears.append(
            f"WHEN {method} {path} is requested with valid authentication "
            f"THEN the system SHALL respond with status {pc.get('status', '?')}"
        )

    # Failure mode EARS
    for fm in context.failure_modes:
        ears.append(
            f"IF {fm['description'].lower()} "
            f"THEN the system SHALL respond with status {fm.get('status', '?')}"
        )

    # Invariant EARS
    for inv in context.invariants:
        inv_desc = inv.get('description', inv.get('rule', ''))
        ears.append(
            f"WHILE the system is operational, "
            f"responses SHALL satisfy: {inv_desc}"
        )

    context.ears_statements = ears
    return ears


def build_traceability_map(context: VerificationContext) -> dict:
    """Build ac_mappings linking each AC to downstream verification refs."""
    ac_mappings: list[dict] = []

    for ac in context.raw_acceptance_criteria:
        ac_idx = ac["index"]
        req_prefix = f"REQ-{ac_idx + 1:03d}"
        verifications: list[dict] = []

        # Happy path from postconditions
        postconds = [p for p in context.postconditions if p.get("ac_index") == ac_idx]
        for pc in postconds:
            verifications.append({
                "ref": f"{req_prefix}.success",
                "verification_type": "test_result",
                "description": f"Happy path: HTTP {pc.get('status')}",
            })
            if pc.get("schema"):
                verifications.append({
                    "ref": f"{req_prefix}.schema",
                    "verification_type": "test_result",
                    "description": "Response schema matches spec",
                })

        # Failure modes
        for fm in context.failure_modes:
            verifications.append({
                "ref": f"{req_prefix}.{fm['id']}",
                "verification_type": "test_result",
                "description": f"Failure: {fm['description']}",
            })

        # Invariants
        for inv in context.invariants:
            inv_desc = inv.get('description', inv.get('rule', ''))
            verifications.append({
                "ref": f"{req_prefix}.{inv['id']}",
                "verification_type": "test_result",
                "description": f"Invariant: {inv_desc}",
            })

        ac_mappings.append({
            "ac_text": ac["text"],
            "ac_checkbox": ac_idx,
            "pass_condition": "ALL_PASS",
            "required_verifications": verifications,
        })

    traceability = {"ac_mappings": ac_mappings}
    context.traceability_map = traceability
    return traceability


def run_synthesis(context: VerificationContext) -> None:
    """Run all post-negotiation synthesis steps."""
    extract_invariants(context)
    generate_ears_statements(context)
    build_traceability_map(context)


def _find_interface_for_ac(context: VerificationContext, ac_index: int) -> dict | None:
    """Find the interface dict for a given AC index from classifications."""
    for c in context.classifications:
        if c.get("ac_index") == ac_index and c.get("interface"):
            return c["interface"]
    return None
