"""Skill Agent Framework — base class, registry, and dispatcher for verification skills.

Each verification skill is a self-contained module that reads a spec contract
and generates a proof-of-correctness artifact (test file, config, scenario).

This implements Epic 4.1 of the Intent-to-Verification pipeline.
"""

from __future__ import annotations

import importlib
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)

BUILTIN_SKILL_MODULES = (
    "verify.skills.pytest_skill",
    "verify.skills.cucumber_java_skill",
)


@dataclass(frozen=True)
class SkillDescriptor:
    """Normalized metadata for capability discovery and dispatch validation."""

    skill_id: str
    name: str
    description: str
    input_types: frozenset[str]
    output_format: str
    framework: str
    version: str

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["input_types"] = sorted(self.input_types)
        return payload


class SkillDispatchError(RuntimeError):
    """Raised when a spec references missing or incompatible skills."""


# ── Skill Registry ──

class VerificationSkill(ABC):
    """Abstract base class for all verification skills.

    Each skill reads a spec contract and generates verification artifacts.
    Follows the Agent Skills open standard (SKILL.md).
    """

    skill_id: str = ""
    name: str = ""
    description: str = ""
    input_types: frozenset[str] = frozenset({"*"})
    output_format: str = ""
    framework: str = "custom"
    version: str = "1.0.0"

    @abstractmethod
    def generate(self, spec: dict, requirement: dict, constitution: dict) -> str:
        """Generate verification artifact content from a spec requirement.

        Args:
            spec: The full spec dict
            requirement: A single requirement from spec["requirements"]
            constitution: The project constitution dict

        Returns:
            The generated artifact content as a string
        """
        ...

    @abstractmethod
    def output_path(self, spec: dict, requirement: dict) -> str:
        """Return the file path where the generated artifact should be written.

        Args:
            spec: The full spec dict
            requirement: A single requirement from spec["requirements"]

        Returns:
            Absolute or relative path for the output file
        """
        ...

    def descriptor(self) -> SkillDescriptor:
        """Build a descriptor from the class-level metadata."""
        descriptor = getattr(self, "DESCRIPTOR", None)
        if isinstance(descriptor, SkillDescriptor):
            return descriptor

        description = self.description or (type(self).__doc__ or "").strip()
        if not description:
            description = f"{type(self).__name__} verification skill"

        return SkillDescriptor(
            skill_id=self.skill_id,
            name=self.name or type(self).__name__,
            description=description,
            input_types=frozenset(self.input_types or {"*"}),
            output_format=self.output_format,
            framework=self.framework or "custom",
            version=self.version or "1.0.0",
        )


class SkillRegistry(dict[str, VerificationSkill]):
    """Dict-like registry that keeps descriptors synchronized with skill entries."""

    def __init__(self) -> None:
        super().__init__()
        self._descriptors: dict[str, SkillDescriptor] = {}

    def register(self, descriptor: SkillDescriptor, skill: VerificationSkill) -> None:
        if descriptor.skill_id in self:
            raise ValueError(f"duplicate skill registration: {descriptor.skill_id}")
        super().__setitem__(descriptor.skill_id, skill)
        self._descriptors[descriptor.skill_id] = descriptor

    def descriptor_for(self, skill_id: str) -> SkillDescriptor | None:
        return self._descriptors.get(skill_id)

    def descriptors(self) -> list[SkillDescriptor]:
        return [self._descriptors[skill_id] for skill_id in sorted(self)]

    def entries(self) -> list[tuple[SkillDescriptor, VerificationSkill]]:
        return [
            (self._descriptors[skill_id], self[skill_id])
            for skill_id in sorted(self)
        ]

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        self._descriptors.pop(key, None)

    def clear(self) -> None:
        super().clear()
        self._descriptors.clear()

    def pop(
        self,
        key: str,
        default: VerificationSkill | None = None,
    ) -> VerificationSkill | None:
        self._descriptors.pop(key, None)
        if default is None:
            return super().pop(key)  # type: ignore[return-value]
        return super().pop(key, default)


SKILL_REGISTRY: SkillRegistry = SkillRegistry()


def _validate_descriptor(descriptor: SkillDescriptor) -> SkillDescriptor:
    if not descriptor.skill_id:
        raise ValueError("skill descriptor requires a non-empty skill_id")
    if not descriptor.name:
        raise ValueError(f"{descriptor.skill_id} requires a non-empty name")
    if not descriptor.description:
        raise ValueError(f"{descriptor.skill_id} requires a non-empty description")
    if not descriptor.input_types:
        raise ValueError(f"{descriptor.skill_id} requires at least one input type")
    return descriptor


def ensure_builtin_skills_registered() -> None:
    """Import built-in skill modules so their registration side effects run."""
    for module_name in BUILTIN_SKILL_MODULES:
        importlib.import_module(module_name)


def register_skill(
    skill: VerificationSkill | type[VerificationSkill],
) -> VerificationSkill | type[VerificationSkill]:
    """Register a verification skill class or instance in the global registry."""
    if isinstance(skill, type):
        if not issubclass(skill, VerificationSkill):
            raise TypeError("register_skill expects a VerificationSkill or subclass")
        instance = skill()
        descriptor = _validate_descriptor(instance.descriptor())
        SKILL_REGISTRY.register(descriptor, instance)
        logger.info("Registered verification skill: %s", descriptor.skill_id)
        return skill

    if not isinstance(skill, VerificationSkill):
        raise TypeError("register_skill expects a VerificationSkill or subclass")

    descriptor = _validate_descriptor(skill.descriptor())
    SKILL_REGISTRY.register(descriptor, skill)
    logger.info("Registered verification skill: %s", descriptor.skill_id)
    return skill


def get_skill_descriptor(skill_id: str) -> SkillDescriptor | None:
    """Return the descriptor for a skill_id if it is registered."""
    ensure_builtin_skills_registered()
    return SKILL_REGISTRY.descriptor_for(skill_id)


def list_skill_descriptors() -> list[SkillDescriptor]:
    """Return all registered skill descriptors in stable order."""
    ensure_builtin_skills_registered()
    return SKILL_REGISTRY.descriptors()


def list_registered_skills() -> list[tuple[SkillDescriptor, VerificationSkill]]:
    """Return all registered skills paired with their descriptors."""
    ensure_builtin_skills_registered()
    return SKILL_REGISTRY.entries()


def find_skills(
    query: str,
    limit: int = 20,
) -> list[tuple[SkillDescriptor, VerificationSkill]]:
    """Find registered skills by skill id, name, description, or input type."""
    query = query.strip().lower()
    if not query:
        return list_registered_skills()[:limit]

    matches: list[tuple[int, SkillDescriptor, VerificationSkill]] = []
    for descriptor, skill in list_registered_skills():
        haystacks = [
            descriptor.skill_id.lower(),
            descriptor.name.lower(),
            descriptor.description.lower(),
            " ".join(sorted(descriptor.input_types)).lower(),
        ]
        if not any(query in haystack for haystack in haystacks):
            continue

        if descriptor.skill_id.lower() == query:
            rank = 0
        elif descriptor.name.lower() == query:
            rank = 1
        elif query in descriptor.skill_id.lower() or query in descriptor.name.lower():
            rank = 2
        elif query in descriptor.description.lower():
            rank = 3
        else:
            rank = 4
        matches.append((rank, descriptor, skill))

    matches.sort(key=lambda item: (item[0], item[1].skill_id))
    return [(descriptor, skill) for _, descriptor, skill in matches[:limit]]


def find_skills_by_type(
    requirement_type: str,
) -> list[tuple[SkillDescriptor, VerificationSkill]]:
    """Find skills that can handle the supplied requirement type."""
    requirement_type = requirement_type.strip()
    if not requirement_type:
        return []

    return [
        (descriptor, skill)
        for descriptor, skill in list_registered_skills()
        if "*" in descriptor.input_types or requirement_type in descriptor.input_types
    ]


def validate_dispatch(spec: dict) -> list[str]:
    """Return a list of missing or incompatible skill bindings for a spec."""
    ensure_builtin_skills_registered()
    errors: list[str] = []

    for requirement in spec.get("requirements", []):
        req_id = requirement.get("id", "?")
        req_type = requirement.get("type", "")
        for ver_entry in requirement.get("verification", []):
            skill_id = ver_entry.get("skill", "")
            if not skill_id:
                errors.append(f"{req_id}: missing verification skill")
                continue

            descriptor = SKILL_REGISTRY.descriptor_for(skill_id)
            skill = SKILL_REGISTRY.get(skill_id)
            if descriptor is None or skill is None:
                errors.append(f"{req_id}: missing registered skill '{skill_id}'")
                continue

            if req_type and "*" not in descriptor.input_types and req_type not in descriptor.input_types:
                errors.append(
                    f"{req_id}: skill '{skill_id}' does not support requirement type '{req_type}'"
                )

    return errors


# ── Dispatcher ──


def dispatch_skills(spec: dict, constitution: dict) -> dict[str, str]:
    """Dispatch verification skills based on the spec's routing table.

    Reads each requirement's verification block, looks up the skill in
    SKILL_REGISTRY, calls generate(), and writes the output to disk.

    Args:
        spec: The complete spec dict with requirements and verification blocks
        constitution: The project constitution dict

    Returns:
        Dict mapping output_path -> generated content for all dispatched skills
    """
    errors = validate_dispatch(spec)
    if errors:
        raise SkillDispatchError("; ".join(errors))

    generated_files: dict[str, str] = {}

    for requirement in spec.get("requirements", []):
        for ver_entry in requirement.get("verification", []):
            skill_id = ver_entry.get("skill", "")
            output = ver_entry.get("output", "")
            skill = SKILL_REGISTRY[skill_id]

            try:
                content = skill.generate(spec, requirement, constitution)
                # Write to disk
                destination = output or skill.output_path(spec, requirement)
                os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
                with open(destination, "w", encoding="utf-8") as f:
                    f.write(content)
                generated_files[destination] = content
                logger.info(f"Generated {destination} via skill '{skill_id}'")
            except Exception as e:
                logger.error(
                    f"Skill '{skill_id}' failed for requirement "
                    f"{requirement.get('id', '?')}: {e}"
                )

    return generated_files


ensure_builtin_skills_registered()
