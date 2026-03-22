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
