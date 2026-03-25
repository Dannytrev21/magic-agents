"""Spec Diff Engine — compares old and new specs to show what changed.

When re-running negotiation on a ticket that already has a spec, this module
provides structured and human-readable diffs to show what changed in:
- Requirements (added, removed, modified)
- Fields within requirements
- Traceability mappings
- Metadata (timestamps, approval status, etc.)

Output: A structured diff dict with:
- added_requirements: New REQ-* ids
- removed_requirements: Deleted REQ-* ids
- modified_requirements: {id: {field: (old_value, new_value)}}
- changed_fields: Summary of which top-level fields changed
- summary: Human-readable text summary
"""

import os
from typing import Any
import yaml


def diff_specs(old_spec_path: str, new_spec: dict) -> dict:
    """Compare an old spec file against a new spec dict.

    Args:
        old_spec_path: Path to the old YAML spec file
        new_spec: The new compiled spec dict

    Returns:
        A structured diff dict with keys:
        - added_requirements: list of new requirement IDs
        - removed_requirements: list of deleted requirement IDs
        - modified_requirements: dict mapping req_id to field changes
        - changed_fields: list of changed top-level fields (meta, traceability, etc.)
        - summary: Human-readable text summary string
        - old_spec: The loaded old spec (for reference)
        - new_spec: The new spec (for reference)
    """
    # Load old spec
    if not os.path.exists(old_spec_path):
        return {
            "error": f"Old spec not found at {old_spec_path}",
            "added_requirements": [],
            "removed_requirements": [],
            "modified_requirements": {},
            "changed_fields": [],
            "summary": f"No old spec found; all requirements are new.",
            "old_spec": None,
            "new_spec": new_spec,
        }

    with open(old_spec_path, "r") as f:
        old_spec = yaml.safe_load(f) or {}

    # Extract requirement lists
    old_reqs = {r["id"]: r for r in old_spec.get("requirements", [])}
    new_reqs = {r["id"]: r for r in new_spec.get("requirements", [])}

    # Find added, removed, modified
    added = [rid for rid in new_reqs if rid not in old_reqs]
    removed = [rid for rid in old_reqs if rid not in new_reqs]
    modified_map = {}

    for rid in set(new_reqs.keys()) & set(old_reqs.keys()):
        changes = _diff_requirement(old_reqs[rid], new_reqs[rid])
        if changes:
            modified_map[rid] = changes

    # Find changed top-level fields
    changed_fields = _diff_top_level_fields(old_spec, new_spec)

    # Build summary
    summary = format_diff_summary({
        "added_requirements": added,
        "removed_requirements": removed,
        "modified_requirements": modified_map,
        "changed_fields": changed_fields,
    })

    return {
        "added_requirements": added,
        "removed_requirements": removed,
        "modified_requirements": modified_map,
        "changed_fields": changed_fields,
        "summary": summary,
        "old_spec": old_spec,
        "new_spec": new_spec,
    }


def _diff_requirement(old_req: dict, new_req: dict) -> dict:
    """Compare two requirement dicts and return field-level changes.

    Returns:
        Dict mapping field name to (old_value, new_value) tuple.
        Empty dict if no changes.
    """
    changes = {}
    all_keys = set(old_req.keys()) | set(new_req.keys())

    for key in all_keys:
        old_val = old_req.get(key)
        new_val = new_req.get(key)

        # For nested structures (contract, verification), do shallow comparison
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            if old_val != new_val:
                changes[key] = (old_val, new_val)
        elif isinstance(old_val, list) and isinstance(new_val, list):
            if old_val != new_val:
                changes[key] = (old_val, new_val)
        elif old_val != new_val:
            changes[key] = (old_val, new_val)

    return changes


def _diff_top_level_fields(old_spec: dict, new_spec: dict) -> list[str]:
    """Identify which top-level fields changed (meta, traceability, etc.).

    Returns:
        List of field names that differ.
    """
    changed = []
    all_keys = set(old_spec.keys()) | set(new_spec.keys())

    for key in all_keys:
        if key == "requirements":
            # requirements is handled separately in diff_specs
            continue
        old_val = old_spec.get(key)
        new_val = new_spec.get(key)
        if old_val != new_val:
            changed.append(key)

    return changed


def format_diff_summary(diff: dict) -> str:
    """Format a diff dict into a human-readable summary string.

    Args:
        diff: The structured diff dict from diff_specs()

    Returns:
        A formatted text summary (multi-line string).
    """
    lines = []
    lines.append("=== Spec Diff Summary ===\n")

    added = diff.get("added_requirements", [])
    removed = diff.get("removed_requirements", [])
    modified = diff.get("modified_requirements", {})
    changed_fields = diff.get("changed_fields", [])

    # Summary line
    total_changes = len(added) + len(removed) + len(modified) + len(changed_fields)
    if total_changes == 0:
        lines.append("No changes detected.")
        return "\n".join(lines)

    lines.append(f"Total changes: {total_changes}")
    lines.append("")

    # Added requirements
    if added:
        lines.append(f"ADDED ({len(added)}):")
        for rid in sorted(added):
            lines.append(f"  + {rid}")
        lines.append("")

    # Removed requirements
    if removed:
        lines.append(f"REMOVED ({len(removed)}):")
        for rid in sorted(removed):
            lines.append(f"  - {rid}")
        lines.append("")

    # Modified requirements
    if modified:
        lines.append(f"MODIFIED ({len(modified)}):")
        for rid in sorted(modified.keys()):
            lines.append(f"  ~ {rid}")
            changes = modified[rid]
            for field, (old_val, new_val) in sorted(changes.items()):
                old_str = _short_repr(old_val)
                new_str = _short_repr(new_val)
                lines.append(f"      {field}: {old_str} → {new_str}")
        lines.append("")

    # Changed top-level fields
    if changed_fields:
        lines.append(f"FIELD CHANGES ({len(changed_fields)}):")
        for field in sorted(changed_fields):
            lines.append(f"  * {field}")
        lines.append("")

    return "\n".join(lines)


def _short_repr(value: Any, max_len: int = 50) -> str:
    """Return a shortened string representation of a value for diffs.

    Args:
        value: Any object to represent
        max_len: Max length before truncation

    Returns:
        A string, truncated if needed.
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        s = repr(value)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s
    if isinstance(value, dict):
        return "{...}" if value else "{}"
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return type(value).__name__
