"""Skill Agent Framework — base class, registry, and dispatch for verification skills.

Each verification skill follows the Agent Skills open standard (SKILL.md).
The SKILL_REGISTRY maps skill IDs to concrete VerificationSkill implementations.
dispatch_skills() reads routing tables from compiled specs and dispatches to skills.

This module is the bridge between the deterministic routing table in compiler.py
and the AI-powered (or template-based) skill implementations.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional

import yaml


class VerificationSkill(ABC):
    """Base class for all verification skills.

    Each skill knows how to generate a specific type of verification artifact
    (tests, configs, scenarios) from a spec contract.

    Follows Block's 3 Principles:
    - Principle 1: Tag coverage validation is deterministic (tag_enforcer.py)
    - Principle 2: Adapting templates to contracts is the AI's job
    - Principle 3: Constitutional rules in SKILL.md, not suggestions
    """

    skill_id: str = ""
    description: str = ""

    @abstractmethod
    def generate(
        self,
        spec: dict,
        requirement: dict,
        constitution: dict,
    ) -> str:
        """Generate verification artifact content from a spec requirement.

        Args:
            spec: The full compiled spec dict.
            requirement: A single requirement dict from spec['requirements'].
            constitution: The project constitution dict.

        Returns:
            The generated file content as a string.
        """

    def output_path(self, spec: dict, requirement: dict) -> str:
        """Return the output file path for this requirement.

        Default implementation reads from the requirement's verification block.
        """
        verification = requirement.get("verification", [{}])
        if verification:
            return verification[0].get("output", "")
        return ""

    def expected_refs(self, requirement: dict) -> list[str]:
        """Return the list of spec refs this skill should cover.

        Used by tag_enforcer to validate coverage.
        """
        req_id = requirement.get("id", "REQ-001")
        verification = requirement.get("verification", [{}])
        refs = []
        if verification:
            raw_refs = verification[0].get("refs", [])
            for ref in raw_refs:
                if ref.startswith("REQ-"):
                    refs.append(ref)
                else:
                    refs.append(f"{req_id}.{ref}")
        return refs


# ── Skill Registry ──

SKILL_REGISTRY: dict[str, VerificationSkill] = {}


def register_skill(skill_cls):
    """Decorator to register a skill class in the global registry.

    Usage:
        @register_skill
        class PytestSkill(VerificationSkill):
            skill_id = "pytest_unit_test"
            ...
    """
    instance = skill_cls()
    SKILL_REGISTRY[instance.skill_id] = instance
    return skill_cls


# ── Skill Dispatch ──


def dispatch_skills(
    spec: dict,
    constitution: dict,
    output_base: str = ".",
) -> dict[str, str]:
    """Dispatch verification skills based on the spec's routing table.

    For each requirement in the spec, looks up the skill in SKILL_REGISTRY
    and calls skill.generate(). Writes output files and returns a mapping
    of {output_path: content}.

    Args:
        spec: The compiled spec dict (from compile_spec or loaded YAML).
        constitution: The project constitution dict.
        output_base: Base directory for output paths (default: current dir).

    Returns:
        Dict mapping output file paths to their generated content.
    """
    generated_files: dict[str, str] = {}

    for requirement in spec.get("requirements", []):
        for verification in requirement.get("verification", []):
            skill_id = verification.get("skill", "")
            output_path = verification.get("output", "")

            if not skill_id or not output_path:
                continue

            # Look up skill in registry
            skill = SKILL_REGISTRY.get(skill_id)
            if skill is None:
                print(f"  [WARN] No registered skill for '{skill_id}', skipping {output_path}")
                continue

            # Resolve output path
            full_path = os.path.join(output_base, output_path) if output_base != "." else output_path

            # Generate the content
            try:
                content = skill.generate(spec, requirement, constitution)
            except Exception as e:
                print(f"  [ERROR] Skill '{skill_id}' failed for {requirement.get('id', '?')}: {e}")
                continue

            if not content or not content.strip():
                print(f"  [WARN] Skill '{skill_id}' produced empty output for {requirement.get('id', '?')}")
                continue

            # Write to disk
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

            generated_files[full_path] = content
            print(f"  [OK] {skill_id} → {full_path}")

    return generated_files


def dispatch_skills_for_spec_path(
    spec_path: str,
    constitution_path: str = "constitution.yaml",
) -> dict[str, str]:
    """Convenience: dispatch skills from file paths instead of dicts."""
    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    constitution = {}
    if os.path.exists(constitution_path):
        with open(constitution_path) as f:
            constitution = yaml.safe_load(f) or {}

    return dispatch_skills(spec, constitution)
