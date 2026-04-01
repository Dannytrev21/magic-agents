"""Auto-Generate Draft Constitution from Index (P11.3).

Generates a draft constitution.yaml from a StackProfile and CodebaseIndex,
formatted to match the existing hand-written constitution schema.

Deterministic: same inputs always produce the same output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .detect import StackProfile
from .index import CodebaseIndex


@dataclass
class ConstitutionDraft:
    """Result of constitution generation."""

    yaml_content: str
    todo_count: int
    sections_populated: list[str] = field(default_factory=list)


# Framework → testing defaults mapping
_TEST_DEFAULTS: dict[str, dict] = {
    "spring-boot": {
        "unit_framework": "junit5",
        "assertion_library": "assertj",
        "mocking_library": "mockito",
        "naming_convention": "{ClassName}Test.java",
    },
    "fastapi": {
        "unit_framework": "pytest",
        "assertion_library": "pytest",
        "mocking_library": "unittest.mock",
        "naming_convention": "test_{module}.py",
    },
    "django": {
        "unit_framework": "pytest",
        "assertion_library": "pytest",
        "mocking_library": "unittest.mock",
        "naming_convention": "test_{module}.py",
    },
    "express": {
        "unit_framework": "jest",
        "assertion_library": "jest",
        "mocking_library": "jest",
        "naming_convention": "{module}.test.ts",
    },
    "nextjs": {
        "unit_framework": "jest",
        "assertion_library": "jest",
        "mocking_library": "jest",
        "naming_convention": "{module}.test.tsx",
    },
}

# Framework → source structure defaults
_SOURCE_DEFAULTS: dict[str, dict] = {
    "spring-boot": {
        "main": "src/main/java",
        "test": "src/test/java",
        "resources": "src/main/resources",
    },
    "fastapi": {"main": "src", "test": "tests"},
    "django": {"main": ".", "test": "tests"},
    "express": {"main": "src", "test": "__tests__"},
    "nextjs": {"main": "src", "test": "__tests__"},
}

# Build tool → test runner mapping
_TEST_RUNNERS: dict[str, str] = {
    "gradle": "./gradlew test",
    "maven": "mvn test",
    "npm": "npm test",
    "yarn": "yarn test",
    "pnpm": "pnpm test",
    "pip": "pytest tests/",
    "poetry": "poetry run pytest tests/",
    "cargo": "cargo test",
    "go": "go test ./...",
}


def generate_constitution(
    profile: StackProfile,
    index: CodebaseIndex,
    output_path: str | None = None,
) -> ConstitutionDraft:
    """Generate a draft constitution.yaml from detection results.

    Args:
        profile: Detected StackProfile.
        index: Built CodebaseIndex.
        output_path: Optional path to write the constitution. Will NOT
            overwrite an existing file.

    Returns:
        A ConstitutionDraft with the YAML content and metadata.
    """
    todo_count = 0
    sections_populated: list[str] = []

    # --- Project section ---
    project_name = Path(index.project_root).name if index.project_root else "unknown"
    project = {
        "name": project_name,
        "language": profile.language,
        "framework": profile.framework,
        "build_tool": profile.build_tool,
    }
    if profile.runtime_version:
        project["version"] = profile.runtime_version
    else:
        project["version"] = "# TODO: verify"
        todo_count += 1
    sections_populated.append("project")

    # --- Source structure section ---
    source_defaults = _SOURCE_DEFAULTS.get(profile.framework, {})
    source_structure: dict = {}
    if source_defaults:
        prefix = f"{project_name}/" if project_name != "unknown" else ""
        source_structure = {
            k: f"{prefix}{v}" for k, v in source_defaults.items()
        }
    else:
        source_structure = {
            "main": "# TODO: verify",
            "test": "# TODO: verify",
        }
        todo_count += 2
    sections_populated.append("source_structure")

    # --- Testing section ---
    test_defaults = _TEST_DEFAULTS.get(profile.framework, {})
    testing: dict = {}
    if test_defaults:
        testing = dict(test_defaults)
    else:
        testing = {
            "unit_framework": "# TODO: verify",
            "assertion_library": "# TODO: verify",
        }
        todo_count += 2

    # Add test runner from build tool
    test_runner = _TEST_RUNNERS.get(profile.build_tool, "# TODO: verify")
    if test_runner == "# TODO: verify":
        todo_count += 1
    if project_name != "unknown" and profile.build_tool in ("gradle", "maven"):
        test_runner = f"cd {project_name} && {test_runner}"
    testing["test_runner"] = test_runner

    # Include discovered test patterns
    if index.test_patterns:
        patterns = []
        for tp in index.test_patterns:
            patterns.append({
                "framework": tp.framework,
                "file": tp.file_path,
            })
        testing["discovered_patterns"] = patterns
    sections_populated.append("testing")

    # --- API section ---
    api: dict = {}
    if index.endpoints:
        api["style"] = "rest"
        # Detect common base path
        paths = [e.path for e in index.endpoints]
        base_path = _detect_base_path(paths)
        if base_path:
            api["base_path"] = base_path
        api["endpoints_discovered"] = len(index.endpoints)
    else:
        api["style"] = "# TODO: verify"
        todo_count += 1
    sections_populated.append("api")

    # --- Observability section (mostly TODOs unless we can detect) ---
    observability: dict = {
        "apm_provider": "# TODO: verify",
        "logging_framework": "# TODO: verify",
    }
    if profile.language == "java":
        observability["logging_framework"] = "slf4j"
    elif profile.language == "python":
        observability["logging_framework"] = "logging"
    else:
        todo_count += 1
    todo_count += 1  # apm_provider is always a TODO
    sections_populated.append("observability")

    # --- Conventions section ---
    conventions: dict = {
        "branch_naming": "feat/{jira_key}-{short-description}",
        "commit_format": "[{jira_key}] {message}",
    }
    sections_populated.append("conventions")

    # --- Verification standards ---
    verification_standards: dict = {
        "required_verification_types": ["unit_test", "schema_contract"],
        "security_invariants": [
            "Never expose password, passwordHash, ssn, or internalId in API responses",
            "Never allow cross-tenant data access",
        ],
    }
    sections_populated.append("verification_standards")

    # --- Compose the full constitution ---
    constitution = {
        "project": project,
        "source_structure": source_structure,
        "testing": testing,
        "api": api,
        "observability": observability,
        "conventions": conventions,
        "verification_standards": verification_standards,
    }

    yaml_content = yaml.dump(
        constitution,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    draft = ConstitutionDraft(
        yaml_content=yaml_content,
        todo_count=todo_count,
        sections_populated=sections_populated,
    )

    # Write to disk if output_path provided and file doesn't exist
    if output_path:
        output = Path(output_path)
        if not output.exists():
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(yaml_content)

    return draft


def _detect_base_path(paths: list[str]) -> str:
    """Detect the common API base path from a list of endpoint paths."""
    if not paths:
        return ""
    parts_list = [p.strip("/").split("/") for p in paths]
    min_len = min(len(parts) for parts in parts_list)
    common: list[str] = []
    for i in range(min_len):
        segment = parts_list[0][i]
        if all(parts[i] == segment for parts in parts_list):
            common.append(segment)
        else:
            break
    return "/" + "/".join(common) if common else ""
