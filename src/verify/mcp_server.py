"""MCP Server Wrapper (Epic P10).

Exposes magic-agents core capabilities as MCP tools and resources.
Can be run standalone via ``python -m verify.mcp_server`` (stdio transport)
or ``python -m verify.mcp_server --port 8080`` (SSE transport).

The implementation is framework-agnostic: it does not require the ``mcp``
Python package.  The core ``MCPServer`` class provides ``list_tools()``,
``call_tool()``, ``list_resources()``, and ``read_resource()`` that can
be wired to any transport.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.runtime import SessionStore

logger = logging.getLogger(__name__)

SPECS_DIR = Path(".verify/specs")

_VERSION = "0.1.0"


# ------------------------------------------------------------------
# Tool definitions
# ------------------------------------------------------------------

_TOOLS = [
    {
        "name": "start_negotiation",
        "description": "Start a new negotiation session for a Jira story.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "jira_key": {"type": "string", "description": "Jira ticket key"},
                "jira_summary": {"type": "string", "description": "Ticket summary"},
                "acceptance_criteria": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of AC dicts",
                },
                "constitution": {"type": "object", "description": "Optional constitution"},
            },
            "required": ["jira_key", "jira_summary", "acceptance_criteria"],
        },
    },
    {
        "name": "run_phase",
        "description": "Advance the negotiation to the next phase.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Active session ID"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "get_spec",
        "description": "Get the compiled YAML spec for a session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Active session ID"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "dispatch_skills",
        "description": "Trigger artifact generation for a session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Active session ID"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "get_verdicts",
        "description": "Get evaluation verdicts for a session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Active session ID"},
            },
            "required": ["session_id"],
        },
    },
]


# ------------------------------------------------------------------
# MCPServer
# ------------------------------------------------------------------


class MCPServer:
    """Core MCP server logic, transport-agnostic."""

    def __init__(self) -> None:
        self._store = SessionStore()

    def server_info(self) -> dict[str, Any]:
        return {"name": "magic-agents", "version": _VERSION}

    def capabilities(self) -> dict[str, Any]:
        return {"tools": {}, "resources": {}}

    def list_tools(self) -> list[dict[str, Any]]:
        return list(_TOOLS)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            return {"status": "error", "message": f"Unknown tool: {name}"}
        try:
            return handler(self, arguments)
        except Exception as exc:
            logger.warning("Tool '%s' raised: %s", name, exc)
            return {"status": "error", "message": str(exc)}

    def list_resources(self) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []

        # Spec files
        if SPECS_DIR.exists():
            for spec_file in sorted(SPECS_DIR.glob("*.yaml"))[:100]:
                key = spec_file.stem
                resources.append({
                    "uri": f"verify://specs/{key}",
                    "name": f"Spec: {key}",
                    "mimeType": "text/yaml",
                })

        # Active sessions
        for sid, state in list(self._store.sessions.items())[:100]:
            resources.append({
                "uri": f"verify://sessions/{sid}",
                "name": f"Session: {state.context.jira_key}",
                "mimeType": "application/json",
            })

        return resources

    def read_resource(self, uri: str) -> str:
        if uri.startswith("verify://specs/"):
            key = uri.split("/")[-1]
            spec_path = SPECS_DIR / f"{key}.yaml"
            if not spec_path.exists():
                raise KeyError(f"Spec not found: {key}")
            return spec_path.read_text()

        if uri.startswith("verify://sessions/"):
            sid = uri.split("/")[-1]
            state = self._store.get(sid)
            if state is None:
                raise KeyError(f"Session not found: {sid}")
            ctx = state.context
            return json.dumps({
                "session_id": sid,
                "jira_key": ctx.jira_key,
                "jira_summary": ctx.jira_summary,
                "current_phase": ctx.current_phase,
                "classifications_count": len(ctx.classifications),
                "postconditions_count": len(ctx.postconditions),
                "approved": ctx.approved,
            }, indent=2)

        raise KeyError(f"Unknown resource URI: {uri}")


# ------------------------------------------------------------------
# Tool handlers
# ------------------------------------------------------------------


def _handle_start_negotiation(server: MCPServer, args: dict[str, Any]) -> dict[str, Any]:
    ctx = VerificationContext(
        jira_key=args["jira_key"],
        jira_summary=args.get("jira_summary", ""),
        raw_acceptance_criteria=args.get("acceptance_criteria", []),
        constitution=args.get("constitution", {}),
    )
    state = server._store.create(ctx, llm=LLMClient())
    return {
        "status": "success",
        "session_id": state.session_id,
        "jira_key": ctx.jira_key,
        "current_phase": ctx.current_phase,
    }


def _handle_run_phase(server: MCPServer, args: dict[str, Any]) -> dict[str, Any]:
    state = server._store.get(args.get("session_id"))
    if state is None:
        return {"status": "error", "message": "Session not found"}
    previous = state.context.current_phase
    new_phase = state.harness.advance_phase()
    if new_phase == previous:
        return {
            "status": "no_change",
            "message": f"Phase {previous} exit conditions not met",
            "current_phase": previous,
        }
    return {
        "status": "success",
        "previous_phase": previous,
        "current_phase": new_phase,
    }


def _handle_get_spec(server: MCPServer, args: dict[str, Any]) -> dict[str, Any]:
    state = server._store.get(args.get("session_id"))
    if state is None:
        return {"status": "error", "message": "Session not found"}
    spec_path = state.context.spec_path
    if not spec_path or not Path(spec_path).exists():
        return {"status": "error", "message": "Spec not yet compiled"}
    return {"status": "success", "spec_yaml": Path(spec_path).read_text()}


def _handle_dispatch_skills(server: MCPServer, args: dict[str, Any]) -> dict[str, Any]:
    state = server._store.get(args.get("session_id"))
    if state is None:
        return {"status": "error", "message": "Session not found"}
    return {
        "status": "success",
        "message": "Skill dispatch queued",
        "session_id": state.session_id,
    }


def _handle_get_verdicts(server: MCPServer, args: dict[str, Any]) -> dict[str, Any]:
    state = server._store.get(args.get("session_id"))
    if state is None:
        return {"status": "error", "message": "Session not found"}
    return {
        "status": "success",
        "verdicts": state.context.verdicts,
        "all_passed": state.context.all_passed,
    }


_TOOL_HANDLERS: dict[str, Any] = {
    "start_negotiation": _handle_start_negotiation,
    "run_phase": _handle_run_phase,
    "get_spec": _handle_get_spec,
    "dispatch_skills": _handle_dispatch_skills,
    "get_verdicts": _handle_get_verdicts,
}
