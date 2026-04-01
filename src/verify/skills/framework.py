"""Skill Agent Framework — base class, registry, and dispatcher for verification skills.

Each verification skill is a self-contained module that reads a spec contract
and generates a proof-of-correctness artifact (test file, config, scenario).

This implements Epic 4.1 of the Intent-to-Verification pipeline.
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Skill Descriptor ──


@dataclass(frozen=True)
class SkillDescriptor:
    """Read-only metadata for a registered verification skill."""

    skill_id: str
    name: str
    description: str
    input_types: frozenset
    output_format: str
    framework: str
    version: str


# ── Exceptions ──


class SkillDispatchError(Exception):
    """Raised when skill dispatch encounters incompatible bindings."""


# ── Skill Registry ──

SKILL_REGISTRY: dict[str, "VerificationSkill"] = {}


def register_skill(skill: "VerificationSkill") -> None:
    """Register a verification skill in the global registry.

    Raises ValueError if a skill with the same ID is already registered.
    """
    if skill.skill_id in SKILL_REGISTRY:
        raise ValueError(
            f"Skill '{skill.skill_id}' is already registered. "
            f"Cannot register duplicate skill IDs."
        )
    SKILL_REGISTRY[skill.skill_id] = skill
    logger.info(f"Registered verification skill: {skill.skill_id}")


def _ensure_builtin_skills_loaded() -> None:
    """Import builtin skill modules to trigger their auto-registration."""
    if SKILL_REGISTRY:
        return
    try:
        import verify.skills.pytest_skill  # noqa: F401
    except Exception:
        pass
    try:
        import verify.skills.cucumber_java_skill  # noqa: F401
    except Exception:
        pass


# ── Descriptor Access ──


def get_skill_descriptor(skill_id: str) -> SkillDescriptor | None:
    """Get descriptor for a registered skill by ID."""
    _ensure_builtin_skills_loaded()
    skill = SKILL_REGISTRY.get(skill_id)
    if skill is None:
        return None
    return _build_descriptor(skill)


def _build_descriptor(skill: "VerificationSkill") -> SkillDescriptor:
    """Build a SkillDescriptor from a VerificationSkill instance."""
    return SkillDescriptor(
        skill_id=skill.skill_id,
        name=getattr(skill, "name", skill.skill_id),
        description=getattr(skill, "description", ""),
        input_types=frozenset(getattr(skill, "input_types", frozenset())),
        output_format=getattr(skill, "output_format", ""),
        framework=getattr(skill, "framework", ""),
        version=getattr(skill, "version", "1.0.0"),
    )


def get_all_descriptors() -> list[SkillDescriptor]:
    """Return descriptors for all registered skills."""
    _ensure_builtin_skills_loaded()
    return [_build_descriptor(skill) for skill in SKILL_REGISTRY.values()]


# ── Search & Discovery ──


def find_skills(query: str) -> list[tuple[SkillDescriptor, "VerificationSkill"]]:
    """Find skills matching a text query against ID, name, description, and framework."""
    _ensure_builtin_skills_loaded()
    query_lower = query.lower()
    results = []
    for skill in SKILL_REGISTRY.values():
        searchable = " ".join([
            skill.skill_id,
            getattr(skill, "name", ""),
            getattr(skill, "description", ""),
            getattr(skill, "framework", ""),
        ]).lower()
        if query_lower in searchable:
            results.append((_build_descriptor(skill), skill))
    return results


def find_skills_by_type(req_type: str) -> list[tuple[SkillDescriptor, "VerificationSkill"]]:
    """Find skills that accept a given requirement type."""
    _ensure_builtin_skills_loaded()
    results = []
    for skill in SKILL_REGISTRY.values():
        input_types = getattr(skill, "input_types", frozenset())
        if req_type in input_types:
            results.append((_build_descriptor(skill), skill))
    return results


# ── Dispatch Validation ──


def validate_dispatch(spec: dict) -> list[str]:
    """Validate skill/requirement bindings in a spec.

    Returns a list of human-readable error strings for:
    - Skills that don't exist in the registry
    - Skills that don't accept the requirement's type
    """
    _ensure_builtin_skills_loaded()
    errors = []
    for requirement in spec.get("requirements", []):
        req_id = requirement.get("id", "?")
        req_type = requirement.get("type", "")
        for ver_entry in requirement.get("verification", []):
            skill_id = ver_entry.get("skill", "")
            skill = SKILL_REGISTRY.get(skill_id)
            if skill is None:
                errors.append(
                    f"{req_id}: skill '{skill_id}' not found in registry"
                )
            else:
                input_types = getattr(skill, "input_types", frozenset())
                if input_types and req_type not in input_types:
                    errors.append(
                        f"{req_id}: skill '{skill_id}' does not accept "
                        f"type '{req_type}' (accepts: {sorted(input_types)})"
                    )
    return errors


# ── Base Class ──


class VerificationSkill(ABC):
    """Abstract base class for all verification skills.

    Each skill reads a spec contract and generates verification artifacts.
    Follows the Agent Skills open standard (SKILL.md).

    Subclasses should set these class attributes for descriptor metadata:
        skill_id: str
        name: str
        description: str
        input_types: frozenset
        output_format: str
        framework: str
        version: str
    """

    skill_id: str = ""
    name: str = ""
    description: str = ""
    input_types: frozenset = frozenset()
    output_format: str = ""
    framework: str = ""
    version: str = "1.0.0"

    @abstractmethod
    def generate(self, spec: dict, requirement: dict, constitution: dict) -> str:
        """Generate verification artifact content from a spec requirement."""
        ...

    @abstractmethod
    def output_path(self, spec: dict, requirement: dict) -> str:
        """Return the file path where the generated artifact should be written."""
        ...


# ── Dispatcher ──


def dispatch_skills(spec: dict, constitution: dict) -> dict[str, str]:
    """Dispatch verification skills based on the spec's routing table.

    Raises SkillDispatchError if any requirement has an incompatible skill binding.
    """
    _ensure_builtin_skills_loaded()

    # Validate first — raise on incompatible bindings
    errors = validate_dispatch(spec)
    if errors:
        raise SkillDispatchError(
            f"Skill dispatch validation failed: {'; '.join(errors)}"
        )

    generated_files: dict[str, str] = {}

    for requirement in spec.get("requirements", []):
        for ver_entry in requirement.get("verification", []):
            skill_id = ver_entry.get("skill", "")
            output = ver_entry.get("output", "")

            skill = SKILL_REGISTRY.get(skill_id)
            if skill is None:
                logger.warning(
                    f"Skill '{skill_id}' not found in registry for "
                    f"requirement {requirement.get('id', '?')}. Skipping."
                )
                continue

            try:
                content = skill.generate(spec, requirement, constitution)
                # Write to disk
                os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
                with open(output, "w") as f:
                    f.write(content)
                generated_files[output] = content
                logger.info(f"Generated {output} via skill '{skill_id}'")
            except Exception as e:
                logger.error(
                    f"Skill '{skill_id}' failed for requirement "
                    f"{requirement.get('id', '?')}: {e}"
                )

    return generated_files
