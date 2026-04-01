"""Explore Agent — orchestrates detection, indexing, and constitution generation (P11.4).

Provides the core `explore()` function, CLI entrypoint, and data structures
for the web endpoint.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .constitution import ConstitutionDraft, generate_constitution
from .detect import StackProfile, detect_stack
from .index import CodebaseIndex, build_codebase_index


@dataclass
class ExploreResult:
    """Full exploration result."""

    stack_profile: StackProfile
    codebase_index: CodebaseIndex
    constitution_draft: ConstitutionDraft
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "stack_profile": {
                "language": self.stack_profile.language,
                "framework": self.stack_profile.framework,
                "build_tool": self.stack_profile.build_tool,
                "runtime_version": self.stack_profile.runtime_version,
                "confidence": self.stack_profile.confidence,
                "secondary_languages": self.stack_profile.secondary_languages,
            },
            "codebase_index": self.codebase_index.to_dict(),
            "constitution_draft": self.constitution_draft.yaml_content,
            "todo_count": self.constitution_draft.todo_count,
            "sections_populated": self.constitution_draft.sections_populated,
            "duration_seconds": round(self.duration_seconds, 3),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def format_report(self) -> str:
        """Human-readable report for CLI output."""
        lines = [
            "=== Codebase Exploration Report ===",
            "",
            f"Language:    {self.stack_profile.language}",
            f"Framework:   {self.stack_profile.framework}",
            f"Build Tool:  {self.stack_profile.build_tool}",
            f"Runtime:     {self.stack_profile.runtime_version or 'N/A'}",
            f"Confidence:  {self.stack_profile.confidence:.0%}",
        ]
        if self.stack_profile.secondary_languages:
            lines.append(f"Secondary:   {', '.join(self.stack_profile.secondary_languages)}")
        lines.append("")

        # Index summary
        idx = self.codebase_index
        lines.append(f"Endpoints:   {len(idx.endpoints)}")
        for ep in idx.endpoints[:10]:
            lines.append(f"  {ep.method:6s} {ep.path} -> {ep.handler}")
        if len(idx.endpoints) > 10:
            lines.append(f"  ... and {len(idx.endpoints) - 10} more")

        lines.append(f"Models:      {len(idx.models)}")
        for m in idx.models:
            lines.append(f"  {m.class_name}")

        lines.append(f"Schemas:     {len(idx.schemas)}")
        for s in idx.schemas:
            lines.append(f"  {s.class_name}")

        lines.append(f"Test files:  {len(idx.test_patterns)}")
        lines.append(f"Config:      {len(idx.config_files)}")
        lines.append("")

        # Coverage
        report = idx.coverage_report
        lines.append(
            f"Coverage: {report['parsed_files']}/{report['total_files']} files parsed"
            f" ({report['failed_files']} failed)"
        )
        lines.append("")

        # Constitution
        lines.append("--- Draft Constitution ---")
        lines.append(self.constitution_draft.yaml_content)
        lines.append(f"TODO markers: {self.constitution_draft.todo_count}")
        lines.append(f"Duration: {self.duration_seconds:.2f}s")
        return "\n".join(lines)


def explore(path: str) -> ExploreResult:
    """Run the full exploration pipeline: detect → index → constitution.

    Args:
        path: Directory path to explore.

    Returns:
        ExploreResult with all detection results.
    """
    start = time.monotonic()
    profile = detect_stack(path)
    index = build_codebase_index(profile, path)
    draft = generate_constitution(profile, index)
    duration = time.monotonic() - start

    return ExploreResult(
        stack_profile=profile,
        codebase_index=index,
        constitution_draft=draft,
        duration_seconds=round(duration, 3),
    )
