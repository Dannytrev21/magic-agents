"""Hook & Event System (Epic P9).

Provides lifecycle hooks for phase boundaries, checkpoint saves, and
session events.  External systems can register callbacks or shell commands
via constitution.yaml.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

LIFECYCLE_POINTS = frozenset({
    "pre_phase",
    "post_phase",
    "pre_dispatch",
    "post_dispatch",
    "pre_evaluation",
    "post_evaluation",
    "checkpoint_saved",
    "session_ended",
})


@dataclass
class HookEvent:
    """Data payload delivered to hook callables."""

    lifecycle_point: str
    session_id: str
    phase_name: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class HookRegistry:
    """Append-only registry of lifecycle hooks."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable[[HookEvent], None]]] = {}

    def register(self, lifecycle_point: str, hook_fn: Callable[[HookEvent], None]) -> None:
        if lifecycle_point not in LIFECYCLE_POINTS:
            raise ValueError(
                f"Invalid lifecycle point '{lifecycle_point}'. "
                f"Must be one of: {sorted(LIFECYCLE_POINTS)}"
            )
        self._hooks.setdefault(lifecycle_point, []).append(hook_fn)

    def fire(self, lifecycle_point: str, event: HookEvent) -> None:
        for hook_fn in self._hooks.get(lifecycle_point, []):
            try:
                hook_fn(event)
            except Exception:
                logger.warning(
                    "Hook failed for '%s': %s",
                    lifecycle_point,
                    hook_fn,
                    exc_info=True,
                )

    @classmethod
    def from_constitution(
        cls,
        constitution: dict[str, Any],
        timeout: int = 30,
    ) -> HookRegistry:
        """Build a registry from constitution.yaml hooks section.

        Each entry maps a lifecycle point to a shell command string.
        """
        registry = cls()
        hooks_section = constitution.get("hooks") or {}

        for point, command in hooks_section.items():
            if point not in LIFECYCLE_POINTS:
                logger.warning("Ignoring unknown hook lifecycle point: %s", point)
                continue

            def _make_shell_hook(cmd: str, tmo: int) -> Callable[[HookEvent], None]:
                def shell_hook(event: HookEvent) -> None:
                    env = {
                        "HOOK_EVENT": event.lifecycle_point,
                        "HOOK_SESSION_ID": event.session_id,
                        "HOOK_PHASE": event.phase_name,
                        "HOOK_STATUS": event.data.get("status", ""),
                    }
                    import os

                    full_env = {**os.environ, **env}
                    try:
                        subprocess.run(
                            cmd,
                            shell=True,
                            timeout=tmo,
                            capture_output=True,
                            text=True,
                            env=full_env,
                        )
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            "Shell hook timed out after %ds for '%s': %s",
                            tmo,
                            event.lifecycle_point,
                            cmd,
                        )
                    except Exception:
                        logger.warning(
                            "Shell hook failed for '%s': %s",
                            event.lifecycle_point,
                            cmd,
                            exc_info=True,
                        )

                return shell_hook

            registry.register(point, _make_shell_hook(command, timeout))

        return registry
