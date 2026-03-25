"""Deterministic validation for phase outputs — Block Principle 1.

Agents should NOT decide what's valid. These are binary pass/fail checks.
"""

VALID_TYPES = frozenset({
    "api_behavior", "performance_sla", "security_invariant",
    "observability", "compliance", "data_constraint",
})

VALID_ACTORS = frozenset({
    "authenticated_user", "admin", "system", "anonymous_user", "api_client",
})

VALID_CATEGORIES = frozenset({
    "authentication", "authorization", "data_existence",
    "data_state", "rate_limit", "system_health",
})

VALID_INVARIANT_TYPES = frozenset({
    "security", "performance", "data_integrity",
    "compliance", "idempotency", "observability",
})

VALID_EARS_PATTERNS = frozenset({
    "UBIQUITOUS", "EVENT_DRIVEN", "STATE_DRIVEN", "UNWANTED", "OPTIONAL",
})


def validate_classifications(
    classifications: list[dict], total_acs: int,
) -> tuple[bool, list[str]]:
    """Validate Phase 1 output."""
    errors: list[str] = []
    if not classifications:
        errors.append("No classifications produced")
        return False, errors

    classified_indices = set()
    for c in classifications:
        idx = c.get("ac_index")
        classified_indices.add(idx)

        ac_type = c.get("type")
        if ac_type not in VALID_TYPES:
            errors.append(f"AC[{idx}]: invalid type '{ac_type}'")

        actor = c.get("actor")
        if actor not in VALID_ACTORS:
            errors.append(f"AC[{idx}]: invalid actor '{actor}'")

        if ac_type == "api_behavior" and not c.get("interface"):
            errors.append(f"AC[{idx}]: api_behavior requires interface")

    expected = set(range(total_acs))
    missing = expected - classified_indices
    if missing:
        errors.append(f"Missing classifications for AC indices: {missing}")

    return len(errors) == 0, errors


def validate_postconditions(
    postconditions: list[dict], api_behavior_indices: set[int],
) -> tuple[bool, list[str]]:
    """Validate Phase 2 output."""
    errors: list[str] = []
    if not api_behavior_indices:
        return True, []  # nothing to validate

    if not postconditions:
        errors.append("No postconditions for api_behavior classifications")
        return False, errors

    postcond_indices = {p.get("ac_index") for p in postconditions}
    missing = api_behavior_indices - postcond_indices
    if missing:
        errors.append(f"Missing postconditions for AC indices: {missing}")

    for p in postconditions:
        status = p.get("status")
        if not isinstance(status, int) or status < 100 or status > 599:
            errors.append(f"AC[{p.get('ac_index')}]: invalid status '{status}'")

    return len(errors) == 0, errors


def validate_preconditions(preconditions: list[dict]) -> tuple[bool, list[str]]:
    """Validate Phase 3 output."""
    errors: list[str] = []
    if not preconditions:
        errors.append("No preconditions produced")
        return False, errors

    ids_seen: set[str] = set()
    for p in preconditions:
        pid = p.get("id", "")
        if not pid.startswith("PRE-"):
            errors.append(f"Precondition id '{pid}' must start with PRE-")
        if pid in ids_seen:
            errors.append(f"Duplicate precondition id: {pid}")
        ids_seen.add(pid)

        category = p.get("category")
        if category not in VALID_CATEGORIES:
            errors.append(f"{pid}: invalid category '{category}'")

        if not p.get("formal"):
            errors.append(f"{pid}: missing formal expression")

    return len(errors) == 0, errors


def validate_failure_modes(
    failure_modes: list[dict], precondition_ids: set[str],
) -> tuple[bool, list[str]]:
    """Validate Phase 4 output."""
    errors: list[str] = []
    if not failure_modes:
        errors.append("No failure modes produced")
        return False, errors

    ids_seen: set[str] = set()
    for f in failure_modes:
        fid = f.get("id", "")
        if not fid.startswith("FAIL-"):
            errors.append(f"Failure mode id '{fid}' must start with FAIL-")
        if fid in ids_seen:
            errors.append(f"Duplicate failure mode id: {fid}")
        ids_seen.add(fid)

        violates = f.get("violates", "")
        if violates not in precondition_ids:
            errors.append(f"{fid}: violates unknown precondition '{violates}'")

        status = f.get("status")
        if not isinstance(status, int) or status < 100 or status > 599:
            errors.append(f"{fid}: invalid status '{status}'")

    return len(errors) == 0, errors


def validate_invariants(invariants: list[dict]) -> tuple[bool, list[str]]:
    """Validate Phase 5 output — invariant extraction."""
    errors: list[str] = []
    if not invariants:
        errors.append("No invariants produced")
        return False, errors

    ids_seen: set[str] = set()
    for inv in invariants:
        iid = inv.get("id", "")
        if not iid.startswith("INV-"):
            errors.append(f"Invariant id '{iid}' must start with INV-")
        if iid in ids_seen:
            errors.append(f"Duplicate invariant id: {iid}")
        ids_seen.add(iid)

        inv_type = inv.get("type")
        if inv_type not in VALID_INVARIANT_TYPES:
            errors.append(f"{iid}: invalid type '{inv_type}'. Must be one of {VALID_INVARIANT_TYPES}")

        if not inv.get("rule"):
            errors.append(f"{iid}: missing rule")

        if not inv.get("source"):
            errors.append(f"{iid}: missing source")

    return len(errors) == 0, errors


def validate_routing(routing: list[dict]) -> tuple[bool, list[str]]:
    """Validate Phase 6 output — verification routing entries."""
    errors: list[str] = []
    if not routing:
        errors.append("No routing entries produced")
        return False, errors

    for entry in routing:
        req_id = entry.get("req_id", "")
        if not req_id.startswith("REQ-"):
            errors.append(f"Routing entry req_id '{req_id}' must start with REQ-")

        skill = entry.get("skill", "")
        if not skill:
            errors.append(f"{req_id}: missing skill")

        refs = entry.get("refs", [])
        if not refs:
            errors.append(f"{req_id}: missing refs")

    return len(errors) == 0, errors


def validate_ears_statements(ears: list[dict]) -> tuple[bool, list[str]]:
    """Validate Phase 7 output — EARS statements."""
    errors: list[str] = []
    if not ears:
        errors.append("No EARS statements produced")
        return False, errors

    ids_seen: set[str] = set()
    for stmt in ears:
        eid = stmt.get("id", "")
        if not eid.startswith("EARS-"):
            errors.append(f"EARS id '{eid}' must start with EARS-")
        if eid in ids_seen:
            errors.append(f"Duplicate EARS id: {eid}")
        ids_seen.add(eid)

        pattern = stmt.get("pattern")
        if pattern not in VALID_EARS_PATTERNS:
            errors.append(f"{eid}: invalid pattern '{pattern}'. Must be one of {VALID_EARS_PATTERNS}")

        if not stmt.get("statement"):
            errors.append(f"{eid}: missing statement")

        if not stmt.get("traces_to"):
            errors.append(f"{eid}: missing traces_to")

    return len(errors) == 0, errors
