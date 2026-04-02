"""Bootstrap & Initialization Graph (Epic P8).

Provides a structured startup sequence with dependency resolution, stage
timing, and failure propagation.  Replaces ad-hoc init scattered across
entry points.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data model
# ------------------------------------------------------------------


@dataclass
class BootstrapStage:
    """A single startup stage."""

    name: str
    description: str
    dependencies: list[str]
    handler: Callable[[dict[str, Any]], Any]


@dataclass
class StageResult:
    """Outcome of a single bootstrap stage."""

    status: str  # "success", "failed", "skipped"
    duration_ms: float = 0.0
    error: str = ""


@dataclass
class BootstrapReport:
    """Aggregate result of a full bootstrap execution."""

    ready: bool
    total_bootstrap_ms: float
    stages: dict[str, StageResult] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "total_bootstrap_ms": round(self.total_bootstrap_ms, 2),
            "stages": {
                name: {
                    "status": sr.status,
                    "duration_ms": round(sr.duration_ms, 2),
                    **({"error": sr.error} if sr.error else {}),
                }
                for name, sr in self.stages.items()
            },
        }


# ------------------------------------------------------------------
# Graph engine
# ------------------------------------------------------------------


class BootstrapGraph:
    """Directed acyclic graph of startup stages with dependency resolution."""

    def __init__(self) -> None:
        self._stages: dict[str, BootstrapStage] = {}

    def add_stage(self, stage: BootstrapStage) -> None:
        if stage.name in self._stages:
            raise ValueError(f"Duplicate stage name: duplicate '{stage.name}'")
        self._stages[stage.name] = stage

    def execute(self, context: dict[str, Any]) -> BootstrapReport:
        """Run all stages in topological order, skipping dependents of failures."""
        ordered = self._topological_sort()
        results: dict[str, StageResult] = {}
        failed_names: set[str] = set()
        t0 = time.monotonic()

        for stage_name in ordered:
            stage = self._stages[stage_name]

            # If any dependency failed or was skipped, skip this stage.
            if any(dep in failed_names for dep in stage.dependencies):
                results[stage_name] = StageResult(status="skipped")
                failed_names.add(stage_name)
                logger.info("Bootstrap stage '%s' skipped (dependency failed)", stage_name)
                continue

            start = time.monotonic()
            try:
                stage.handler(context)
                elapsed_ms = (time.monotonic() - start) * 1000
                results[stage_name] = StageResult(status="success", duration_ms=elapsed_ms)
                logger.info("Bootstrap stage '%s' succeeded (%.1f ms)", stage_name, elapsed_ms)
            except Exception as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                results[stage_name] = StageResult(
                    status="failed", duration_ms=elapsed_ms, error=str(exc)
                )
                failed_names.add(stage_name)
                logger.error("Bootstrap stage '%s' failed: %s", stage_name, exc)

        total_ms = (time.monotonic() - t0) * 1000
        ready = all(sr.status == "success" for sr in results.values())
        return BootstrapReport(ready=ready, total_bootstrap_ms=total_ms, stages=results)

    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm for topological ordering."""
        # Validate dependencies exist
        for stage in self._stages.values():
            for dep in stage.dependencies:
                if dep not in self._stages:
                    raise ValueError(
                        f"Stage '{stage.name}' depends on unknown stage '{dep}'"
                    )

        in_degree: dict[str, int] = {name: 0 for name in self._stages}
        dependents: dict[str, list[str]] = {name: [] for name in self._stages}

        for name, stage in self._stages.items():
            in_degree[name] = len(stage.dependencies)
            for dep in stage.dependencies:
                dependents[dep].append(name)

        queue = sorted(name for name, deg in in_degree.items() if deg == 0)
        ordered: list[str] = []

        while queue:
            current = queue.pop(0)
            ordered.append(current)
            for child in sorted(dependents[current]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
            queue.sort()  # deterministic ordering

        if len(ordered) != len(self._stages):
            raise ValueError(
                "Dependency cycle detected among bootstrap stages"
            )
        return ordered


# ------------------------------------------------------------------
# Default magic-agents bootstrap graph
# ------------------------------------------------------------------


def _env_validation_handler(ctx: dict[str, Any]) -> None:
    """Validate required environment variables."""
    is_mock = os.environ.get("LLM_MOCK", "").lower() == "true"
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not has_key and not is_mock:
        os.environ["LLM_MOCK"] = "true"
    ctx["llm_mock"] = os.environ.get("LLM_MOCK", "").lower() == "true"


def _constitution_load_handler(ctx: dict[str, Any]) -> None:
    """Load constitution.yaml if present."""
    from pathlib import Path

    constitution_path = Path("constitution.yaml")
    if constitution_path.exists():
        import yaml

        ctx["constitution"] = yaml.safe_load(constitution_path.read_text())
    else:
        ctx["constitution"] = {}


def _llm_client_init_handler(ctx: dict[str, Any]) -> None:
    """Initialize the LLM client."""
    from verify.llm_client import LLMClient

    ctx["llm_client"] = LLMClient()


def _skill_registration_handler(ctx: dict[str, Any]) -> None:
    """Discover and register available skills."""
    from verify.skills.framework import find_skills

    ctx["skills"] = find_skills("*")


def _session_store_init_handler(ctx: dict[str, Any]) -> None:
    """Initialize the session store."""
    from verify.runtime import SessionStore

    ctx["session_store"] = SessionStore()


def build_bootstrap_graph() -> BootstrapGraph:
    """Build the default magic-agents bootstrap graph."""
    graph = BootstrapGraph()

    graph.add_stage(BootstrapStage(
        name="env_validation",
        description="Validate environment variables and set LLM mode",
        dependencies=[],
        handler=_env_validation_handler,
    ))
    graph.add_stage(BootstrapStage(
        name="constitution_load",
        description="Load constitution.yaml configuration",
        dependencies=["env_validation"],
        handler=_constitution_load_handler,
    ))
    graph.add_stage(BootstrapStage(
        name="llm_client_init",
        description="Initialize Claude LLM client",
        dependencies=["env_validation"],
        handler=_llm_client_init_handler,
    ))
    graph.add_stage(BootstrapStage(
        name="skill_registration",
        description="Discover and register available skills",
        dependencies=["env_validation"],
        handler=_skill_registration_handler,
    ))
    graph.add_stage(BootstrapStage(
        name="session_store_init",
        description="Initialize in-memory session store",
        dependencies=["llm_client_init"],
        handler=_session_store_init_handler,
    ))

    return graph
