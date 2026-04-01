"""Command routing engine for dynamic command dispatch.

Provides a registry of command descriptors with tokenized prompt routing,
ported from claw-code's PortRuntime.route_prompt pattern.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class CommandDescriptor:
    """Metadata for a registered command."""

    name: str
    description: str
    category: str
    aliases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CommandResult:
    """Result of a command execution."""

    status: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


_TOKENIZE_RE = re.compile(r"[\s/\-]+")


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens on whitespace, ``/``, and ``-``."""
    return [t for t in _TOKENIZE_RE.split(text.lower()) if t]


class CommandRegistry:
    """Registry mapping command names to descriptors and handlers."""

    def __init__(self) -> None:
        self._commands: dict[str, tuple[CommandDescriptor, Callable[..., CommandResult]]] = {}

    def register(
        self,
        descriptor: CommandDescriptor,
        handler: Callable[..., CommandResult],
    ) -> None:
        key = descriptor.name.lower()
        if key in self._commands:
            raise ValueError(
                f"Command '{descriptor.name}' is already registered"
            )
        self._commands[key] = (descriptor, handler)

    def get(self, name: str) -> tuple[CommandDescriptor, Callable[..., CommandResult]] | None:
        return self._commands.get(name.lower())

    def find(self, name: str) -> tuple[CommandDescriptor, Callable[..., CommandResult]] | None:
        """Look up a command by name or alias (case-insensitive)."""
        result = self.get(name)
        if result is not None:
            return result

        query = name.lower()
        for _, (descriptor, handler) in self._commands.items():
            if query in [a.lower() for a in descriptor.aliases]:
                return (descriptor, handler)
        return None

    def list(self, category: str | None = None) -> list[CommandDescriptor]:
        descriptors = [desc for desc, _ in self._commands.values()]
        if category is not None:
            descriptors = [d for d in descriptors if d.category == category]
        return descriptors


def route_prompt(
    prompt: str,
    registry: CommandRegistry,
    limit: int = 5,
) -> list[tuple[CommandDescriptor, int]]:
    """Score registered commands against a free-text prompt using token overlap.

    Returns a list of ``(descriptor, score)`` tuples sorted by descending
    score.  Commands with zero score are excluded.
    """
    if not prompt or not prompt.strip():
        return []

    prompt_tokens = set(_tokenize(prompt))
    if not prompt_tokens:
        return []

    scored: list[tuple[CommandDescriptor, int]] = []
    for descriptor in registry.list():
        command_tokens = set(_tokenize(descriptor.name))
        command_tokens.update(_tokenize(descriptor.description))
        for alias in descriptor.aliases:
            command_tokens.update(_tokenize(alias))

        overlap = len(prompt_tokens & command_tokens)
        if overlap > 0:
            scored.append((descriptor, overlap))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]
