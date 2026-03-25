"""Skill Agent Framework — base class, registry, and dispatcher.

Implements Feature 4.1: A plugin architecture where each verification skill
is a self-contained module that reads spec contracts and generates proof-of-correctness
artifacts (tests, configs, scenarios).

Following Block's 3 Principles:
- Principle 1: Tag coverage validation and spec schema validation are deterministic
- Principle 2: Adapting test templates to specific contract shapes is the agent's job
- Principle 3: Constitutional rules in SKILL.md are MUST/FORBIDDEN, not suggestions
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class VerificationSkill(ABC):
    """Base class for all verification skills.

    Each skill reads a spec contract and generates a verification artifact
    (test file, config, scenario, etc.).
    """

    skill_id: str = ""

    @abstractmethod
    def generate(self, spec: dict, requirement: dict, constitution: dict) -> str:
        """Generate the verification artifact content.

        Args:
            spec: The full spec dict (meta + requirements + traceability).
            requirement: The specific requirement dict this skill is generating for.
            constitution: The repository constitution (coding conventions, patterns).

        Returns:
            The generated artifact content as a string.
        """
        ...

    @abstractmethod
    def output_path(self, spec: dict, requirement: dict) -> str:
        """Return the file path where the artifact should be written.

        Args:
            spec: The full spec dict.
            requirement: The specific requirement dict.

        Returns:
            The output file path as a string.
        """
        ...


# ------------------------------------------------------------------
# Skill Registry — maps skill_id → VerificationSkill instance
# ------------------------------------------------------------------

SKILL_REGISTRY: dict[str, VerificationSkill] = {}


def register_skill(skill: VerificationSkill) -> None:
    """Register a skill instance in the global registry."""
    SKILL_REGISTRY[skill.skill_id] = skill
    logger.info(f"Registered skill: {skill.skill_id}")


# ------------------------------------------------------------------
# Skill Dispatcher — routes spec requirements to skills
# ------------------------------------------------------------------


def dispatch_skills(spec: dict, constitution: dict) -> dict[str, str]:
    """Dispatch verification skills for each requirement in the spec.

    Reads the `verification` blocks from each requirement, looks up
    the skill in SKILL_REGISTRY, calls generate(), and writes output.

    Args:
        spec: The full spec dict with requirements and verification routing.
        constitution: The repository constitution.

    Returns:
        Dict mapping {output_path: generated_content} for all generated files.
    """
    # Ensure skills are loaded (importing pytest_skill registers it)
    _ensure_skills_loaded()

    generated: dict[str, str] = {}

    for requirement in spec.get("requirements", []):
        for verification in requirement.get("verification", []):
            skill_id = verification.get("skill")
            output = verification.get("output", "")

            if skill_id not in SKILL_REGISTRY:
                logger.warning(
                    f"Skill '{skill_id}' not found in registry for "
                    f"requirement {requirement.get('id', '?')}"
                )
                continue

            skill = SKILL_REGISTRY[skill_id]
            content = skill.generate(spec, requirement, constitution)

            # Write to disk
            if output:
                os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
                with open(output, "w") as f:
                    f.write(content)
                logger.info(f"Generated: {output} ({len(content)} chars)")

            generated[output] = content

    return generated


def _ensure_skills_loaded() -> None:
    """Lazily import skill modules so they self-register."""
    if "pytest_unit_test" not in SKILL_REGISTRY:
        try:
            import verify.skills.pytest_skill  # noqa: F401
        except ImportError:
            logger.debug("pytest_skill not yet available")
