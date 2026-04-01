"""Permission & Access Control — ported from claw-code.

Provides fine-grained control over which verification skills and tools
can be dispatched during a session.

Epic P05: Permission & Access Control.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PermissionDenial:
    """Record of a tool/skill that was blocked by the permission context."""

    tool_name: str
    reason: str


@dataclass(frozen=True)
class ToolPermissionContext:
    """Immutable permission rules that control which tools/skills are allowed.

    Supports two levels of blocking:
    - Exact name matching (deny_names)
    - Prefix-based matching (deny_prefixes)

    All comparisons are case-insensitive.
    """

    deny_names: frozenset[str]
    deny_prefixes: tuple[str, ...]

    @classmethod
    def from_iterables(
        cls,
        deny_names: list[str] | tuple[str, ...] | frozenset[str] | None = None,
        deny_prefixes: list[str] | tuple[str, ...] | None = None,
    ) -> ToolPermissionContext:
        """Construct from mutable iterables."""
        return cls(
            deny_names=frozenset(deny_names or []),
            deny_prefixes=tuple(deny_prefixes or []),
        )

    @classmethod
    def from_constitution(cls, constitution: dict) -> ToolPermissionContext:
        """Build permission context from constitution YAML permissions section."""
        perms = constitution.get("permissions", {})
        if not perms:
            return cls(deny_names=frozenset(), deny_prefixes=())
        return cls.from_iterables(
            deny_names=perms.get("deny_skills", []),
            deny_prefixes=perms.get("deny_prefixes", []),
        )

    def blocks(self, tool_name: str) -> bool:
        """Check if a tool/skill name is blocked. Case-insensitive."""
        name_lower = tool_name.lower()

        if name_lower in {n.lower() for n in self.deny_names}:
            return True

        for prefix in self.deny_prefixes:
            if name_lower.startswith(prefix.lower()):
                return True

        return False


def filter_skills_by_permission(
    skills: dict[str, object],
    permission_context: ToolPermissionContext | None = None,
) -> dict[str, object]:
    """Filter a skill registry dict by permission context.

    Args:
        skills: Dict mapping skill_id -> VerificationSkill.
        permission_context: Rules for blocking. None means allow all.

    Returns:
        Filtered dict with blocked skills removed.
    """
    if permission_context is None:
        return skills
    return {
        skill_id: skill
        for skill_id, skill in skills.items()
        if not permission_context.blocks(skill_id)
    }


def dispatch_skills_with_permissions(
    spec: dict,
    constitution: dict,
    permission_context: ToolPermissionContext | None = None,
) -> tuple[dict[str, str], list[PermissionDenial]]:
    """Dispatch skills with permission enforcement.

    Like framework.dispatch_skills but checks permissions first and
    collects denials instead of raising.

    Returns:
        Tuple of (generated_files dict, list of PermissionDenial).
    """
    import os
    from verify.skills.framework import SKILL_REGISTRY, _ensure_builtin_skills_loaded

    _ensure_builtin_skills_loaded()

    generated_files: dict[str, str] = {}
    denials: list[PermissionDenial] = []

    for requirement in spec.get("requirements", []):
        for ver_entry in requirement.get("verification", []):
            skill_id = ver_entry.get("skill", "")
            output = ver_entry.get("output", "")

            # Check permission first
            if permission_context and permission_context.blocks(skill_id):
                denials.append(PermissionDenial(
                    tool_name=skill_id,
                    reason=f"Skill '{skill_id}' blocked by permission policy",
                ))
                continue

            skill = SKILL_REGISTRY.get(skill_id)
            if skill is None:
                denials.append(PermissionDenial(
                    tool_name=skill_id,
                    reason=f"Skill '{skill_id}' not found in registry",
                ))
                continue

            try:
                content = skill.generate(spec, requirement, constitution)
                if output:
                    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
                    with open(output, "w") as f:
                        f.write(content)
                generated_files[output] = content
            except Exception as e:
                logger.error(f"Skill '{skill_id}' failed: {e}")

    return generated_files, denials
