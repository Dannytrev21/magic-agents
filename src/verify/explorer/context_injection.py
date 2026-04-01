"""Inject Codebase Context into Negotiation Phases (P11.5).

Provides utilities to format CodebaseIndex data into a prompt-ready
context section and merge it into the constitution dictionary.
"""

from __future__ import annotations

from .index import CodebaseIndex


def build_codebase_context_section(
    index: CodebaseIndex,
    max_tokens: int = 2000,
) -> str:
    """Build a ## Codebase Context section for phase system prompts.

    Args:
        index: The CodebaseIndex to format.
        max_tokens: Approximate token budget (chars * 0.25 as heuristic).

    Returns:
        Formatted context string, or empty string if index has no data.
    """
    if not index.endpoints and not index.models and not index.schemas:
        return ""

    max_chars = max_tokens * 4  # ~4 chars per token heuristic
    lines = ["## Codebase Context", ""]

    if index.endpoints:
        lines.append(f"Endpoints ({len(index.endpoints)}):")
        for ep in index.endpoints:
            lines.append(f"  {ep.method:6s} {ep.path} -> {ep.handler}")

    if index.models:
        lines.append(f"\nModels ({len(index.models)}):")
        for m in index.models:
            field_names = [f["name"] for f in m.fields] if m.fields else []
            if field_names:
                lines.append(f"  {m.class_name}: {', '.join(field_names)}")
            else:
                lines.append(f"  {m.class_name}")

    if index.schemas:
        lines.append(f"\nSchemas/DTOs ({len(index.schemas)}):")
        for s in index.schemas:
            field_names = [f["name"] for f in s.fields] if s.fields else []
            if field_names:
                lines.append(f"  {s.class_name}: {', '.join(field_names)}")
            else:
                lines.append(f"  {s.class_name}")

    if index.test_patterns:
        lines.append(f"\nTest patterns ({len(index.test_patterns)}):")
        for t in index.test_patterns:
            lines.append(f"  {t.framework}: {t.file_path}")

    result = "\n".join(lines)

    # Truncate if exceeds budget
    if len(result) > max_chars:
        # Count omitted items
        full_len = len(result)
        result = result[:max_chars]
        # Cut at last newline to avoid partial lines
        last_nl = result.rfind("\n")
        if last_nl > 0:
            result = result[:last_nl]
        omitted = full_len - len(result)
        result += f"\n\n[truncated — ~{omitted} characters omitted]"

    return result


def inject_codebase_into_constitution(
    constitution: dict,
    index: CodebaseIndex | None,
) -> dict:
    """Merge codebase index context into the constitution dict.

    Returns a new dict — does NOT mutate the original.

    Args:
        constitution: Existing constitution dictionary.
        index: CodebaseIndex to inject, or None.

    Returns:
        Updated constitution dict with _codebase_index key if index provided.
    """
    updated = dict(constitution)
    if index is not None:
        section = build_codebase_context_section(index)
        if section:
            updated["_codebase_index"] = section
    return updated
