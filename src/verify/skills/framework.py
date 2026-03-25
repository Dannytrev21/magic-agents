"""Skill Agent Framework — base class, registry, and dispatcher for verification skills.

Each verification skill is a self-contained module that reads a spec contract
and generates a proof-of-correctness artifact (test file, config, scenario).

This implements Epic 4.1 of the Intent-to-Verification pipeline.
"""

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


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


# ── Base Class ──


class VerificationSkill(ABC):
    """Abstract base class for all verification skills.

    Each skill reads a spec contract and generates verification artifacts.
    Follows the Agent Skills open standard (SKILL.md).
    """

    skill_id: str = ""

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
