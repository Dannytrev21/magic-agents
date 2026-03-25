"""Base class for all test generators — pluggable architecture."""

from abc import ABC, abstractmethod

import yaml

from verify.llm_client import LLMClient


class GeneratedFiles:
    """Container for files produced by a generator."""

    def __init__(self):
        self.files: dict[str, str] = {}  # path -> content

    def add(self, path: str, content: str) -> None:
        self.files[path] = content

    def paths(self) -> list[str]:
        return list(self.files.keys())


class BaseGenerator(ABC):
    """Abstract base for test generators.

    Each generator knows how to:
    1. generate() — call Claude API with spec + constitution context
    2. validate() — check structural validity of generated output
    3. write() — write files to the paths specified by the constitution
    """

    @abstractmethod
    def generate(
        self,
        spec_path: str,
        constitution: dict,
        llm: LLMClient,
    ) -> GeneratedFiles:
        """Generate test files from a spec YAML using the LLM.

        Args:
            spec_path: Path to the compiled spec YAML.
            constitution: Parsed constitution dict.
            llm: LLM client for Claude API calls.

        Returns:
            GeneratedFiles containing all generated file paths and contents.
        """

    @abstractmethod
    def validate(self, generated: GeneratedFiles) -> tuple[bool, list[str]]:
        """Validate the generated files structurally.

        Returns:
            (is_valid, list_of_errors)
        """

    def write(self, generated: GeneratedFiles) -> list[str]:
        """Write all generated files to disk. Returns list of written paths."""
        import os

        written = []
        for path, content in generated.files.items():
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            written.append(path)
        return written

    @staticmethod
    def load_spec(spec_path: str) -> dict:
        with open(spec_path) as f:
            return yaml.safe_load(f)

    @staticmethod
    def load_constitution(path: str = "constitution.yaml") -> dict:
        with open(path) as f:
            return yaml.safe_load(f)
