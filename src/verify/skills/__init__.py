"""Verification Skills — pluggable agent skill framework for proof-of-correctness generation."""

from verify.skills.framework import (
    SKILL_REGISTRY,
    VerificationSkill,
    dispatch_skills,
    register_skill,
)

# Import skills to trigger registration
from verify.skills import pytest_skill  # noqa: F401, E402
from verify.skills import cucumber_java_skill  # noqa: F401, E402

__all__ = [
    "SKILL_REGISTRY",
    "VerificationSkill",
    "dispatch_skills",
    "register_skill",
]
