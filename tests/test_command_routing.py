"""Tests for the command routing engine (Epic P4)."""

from __future__ import annotations

import pytest

from verify.commands import (
    CommandDescriptor,
    CommandRegistry,
    CommandResult,
    route_prompt,
)


# ---------------------------------------------------------------
# P4.1 — CommandRegistry with Metadata
# ---------------------------------------------------------------


def _noop_handler(args: dict) -> CommandResult:
    return CommandResult(status="ok", message="done")


def _make_descriptor(
    name: str = "test-cmd",
    description: str = "A test command",
    category: str = "admin",
    aliases: list[str] | None = None,
) -> CommandDescriptor:
    return CommandDescriptor(
        name=name,
        description=description,
        category=category,
        aliases=aliases or [],
    )


class TestCommandRegistry:
    def test_register_and_get(self):
        registry = CommandRegistry()
        desc = _make_descriptor(name="run-phase", description="Run negotiation phase")
        registry.register(desc, handler=_noop_handler)

        result = registry.get("run-phase")
        assert result is not None
        descriptor, handler = result
        assert descriptor.name == "run-phase"
        assert handler is _noop_handler

    def test_get_returns_none_for_unknown(self):
        registry = CommandRegistry()
        assert registry.get("nonexistent") is None

    def test_case_insensitive_lookup(self):
        registry = CommandRegistry()
        registry.register(_make_descriptor(name="Run-Phase"), _noop_handler)

        assert registry.get("run-phase") is not None
        assert registry.get("RUN-PHASE") is not None
        assert registry.get("Run-Phase") is not None

    def test_duplicate_name_raises(self):
        registry = CommandRegistry()
        registry.register(_make_descriptor(name="run-phase"), _noop_handler)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(_make_descriptor(name="run-phase"), _noop_handler)

    def test_duplicate_case_insensitive_raises(self):
        registry = CommandRegistry()
        registry.register(_make_descriptor(name="run-phase"), _noop_handler)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(_make_descriptor(name="RUN-PHASE"), _noop_handler)

    def test_list_all(self):
        registry = CommandRegistry()
        registry.register(_make_descriptor(name="a", category="negotiation"), _noop_handler)
        registry.register(_make_descriptor(name="b", category="pipeline"), _noop_handler)

        all_cmds = registry.list()
        assert len(all_cmds) == 2
        names = {d.name for d in all_cmds}
        assert names == {"a", "b"}

    def test_list_by_category(self):
        registry = CommandRegistry()
        registry.register(_make_descriptor(name="a", category="negotiation"), _noop_handler)
        registry.register(_make_descriptor(name="b", category="pipeline"), _noop_handler)
        registry.register(_make_descriptor(name="c", category="negotiation"), _noop_handler)

        negotiation = registry.list(category="negotiation")
        assert len(negotiation) == 2
        assert all(d.category == "negotiation" for d in negotiation)

    def test_find_by_alias(self):
        registry = CommandRegistry()
        desc = _make_descriptor(name="run-phase", aliases=["rp", "phase"])
        registry.register(desc, _noop_handler)

        result = registry.find("rp")
        assert result is not None
        assert result[0].name == "run-phase"

        result2 = registry.find("phase")
        assert result2 is not None
        assert result2[0].name == "run-phase"

    def test_find_by_name(self):
        registry = CommandRegistry()
        registry.register(_make_descriptor(name="run-phase"), _noop_handler)

        result = registry.find("run-phase")
        assert result is not None
        assert result[0].name == "run-phase"

    def test_find_returns_none_for_unknown(self):
        registry = CommandRegistry()
        assert registry.find("nonexistent") is None


# ---------------------------------------------------------------
# P4.1 — CommandResult dataclass
# ---------------------------------------------------------------


class TestCommandResult:
    def test_default_fields(self):
        result = CommandResult(status="ok", message="done")
        assert result.status == "ok"
        assert result.message == "done"
        assert result.data == {}

    def test_with_data(self):
        result = CommandResult(status="ok", message="done", data={"count": 5})
        assert result.data["count"] == 5


# ---------------------------------------------------------------
# P4.2 — Tokenized Prompt Routing
# ---------------------------------------------------------------


class TestRoutePrompt:
    def _build_registry(self) -> CommandRegistry:
        registry = CommandRegistry()
        registry.register(
            _make_descriptor(
                name="run-phase",
                description="Execute negotiation phase",
                category="negotiation",
            ),
            _noop_handler,
        )
        registry.register(
            _make_descriptor(
                name="dispatch-skills",
                description="Dispatch verification skills",
                category="pipeline",
            ),
            _noop_handler,
        )
        registry.register(
            _make_descriptor(
                name="list-commands",
                description="List all available commands",
                category="admin",
            ),
            _noop_handler,
        )
        return registry

    def test_basic_routing(self):
        registry = self._build_registry()
        results = route_prompt("run the next phase", registry)
        assert len(results) > 0
        assert results[0][0].name == "run-phase"

    def test_no_match_returns_empty(self):
        registry = self._build_registry()
        results = route_prompt("completely unrelated query xyz", registry)
        assert results == []

    def test_deterministic(self):
        registry = self._build_registry()
        r1 = route_prompt("negotiate phase 1", registry)
        r2 = route_prompt("negotiate phase 1", registry)
        assert r1 == r2

    def test_scores_descending(self):
        registry = self._build_registry()
        results = route_prompt("run phase dispatch", registry)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_zero_score_excluded(self):
        registry = self._build_registry()
        results = route_prompt("run phase", registry)
        assert all(score > 0 for _, score in results)

    def test_limit_parameter(self):
        registry = self._build_registry()
        results = route_prompt("run phase dispatch skills list commands", registry, limit=2)
        assert len(results) <= 2

    def test_tokenization_splits_on_slash_and_hyphen(self):
        registry = self._build_registry()
        results = route_prompt("/run-phase", registry)
        assert len(results) > 0
        assert results[0][0].name == "run-phase"

    def test_alias_matching(self):
        registry = CommandRegistry()
        registry.register(
            _make_descriptor(name="run-phase", aliases=["rp", "execute-phase"]),
            _noop_handler,
        )
        results = route_prompt("execute phase", registry)
        assert len(results) > 0
        assert results[0][0].name == "run-phase"

    def test_empty_prompt_returns_empty(self):
        registry = self._build_registry()
        results = route_prompt("", registry)
        assert results == []


# ---------------------------------------------------------------
# P4.3 — Dynamic Command Discovery in Web UI
# ---------------------------------------------------------------

from fastapi.testclient import TestClient


@pytest.fixture
def command_client():
    """Build a FastAPI test client with command endpoints mounted."""
    from verify.commands import CommandRegistry, CommandDescriptor, CommandResult
    from verify.command_routes import create_command_router

    registry = CommandRegistry()
    registry.register(
        CommandDescriptor(
            name="run-phase",
            description="Run negotiation phase",
            category="negotiation",
        ),
        handler=lambda args: CommandResult(
            status="ok",
            message=f"Phase executed",
            data={"phase": args.get("phase", "unknown")},
        ),
    )
    registry.register(
        CommandDescriptor(
            name="dispatch-skills",
            description="Dispatch verification skills",
            category="pipeline",
        ),
        handler=lambda args: CommandResult(status="ok", message="Skills dispatched"),
    )

    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(create_command_router(registry))
    return TestClient(test_app)


class TestCommandWebEndpoints:
    def test_list_commands(self, command_client):
        resp = command_client.get("/api/commands")
        assert resp.status_code == 200
        data = resp.json()
        assert "negotiation" in data
        assert "pipeline" in data
        assert any(c["name"] == "run-phase" for c in data["negotiation"])

    def test_execute_command(self, command_client):
        resp = command_client.post(
            "/api/commands/run-phase",
            json={"phase": "phase_1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["data"]["phase"] == "phase_1"

    def test_command_not_found(self, command_client):
        resp = command_client.post("/api/commands/nonexistent", json={})
        assert resp.status_code == 404

    def test_list_commands_grouped_by_category(self, command_client):
        resp = command_client.get("/api/commands")
        data = resp.json()
        for category, commands in data.items():
            assert isinstance(commands, list)
            for cmd in commands:
                assert "name" in cmd
                assert "description" in cmd
                assert "category" in cmd

    def test_execute_returns_command_result_fields(self, command_client):
        resp = command_client.post(
            "/api/commands/dispatch-skills",
            json={},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "message" in body
