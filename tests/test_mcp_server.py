"""Tests for Epic P10: MCP Server Wrapper.

P10.1: Expose Core Pipeline as MCP Tools
P10.2: Expose Specs and Sessions as MCP Resources
P10.3: MCP Server Configuration and Launch
"""

import json
from pathlib import Path

import pytest

from verify.context import VerificationContext


# ---------------------------------------------------------------
# P10.1 — MCP Tool Definitions
# ---------------------------------------------------------------


class TestMCPToolSchemas:
    """MCPServer should expose tools with JSON Schema definitions."""

    def test_list_tools_returns_five(self):
        from verify.mcp_server import MCPServer

        server = MCPServer()
        tools = server.list_tools()
        assert len(tools) == 5

    def test_each_tool_has_input_schema(self):
        from verify.mcp_server import MCPServer

        server = MCPServer()
        tools = server.list_tools()
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_tool_names(self):
        from verify.mcp_server import MCPServer

        server = MCPServer()
        tools = server.list_tools()
        names = {t["name"] for t in tools}
        assert names == {
            "start_negotiation",
            "run_phase",
            "get_spec",
            "dispatch_skills",
            "get_verdicts",
        }


class TestMCPToolCalls:
    """MCPServer tool calls should dispatch to internal functions."""

    @pytest.fixture
    def server(self, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        from verify.mcp_server import MCPServer

        return MCPServer()

    def test_start_negotiation(self, server):
        result = server.call_tool(
            "start_negotiation",
            {
                "jira_key": "MCP-001",
                "jira_summary": "MCP Test",
                "acceptance_criteria": [
                    {"index": 0, "text": "AC1", "checked": False}
                ],
            },
        )
        assert result["status"] == "success"
        assert "session_id" in result

    def test_run_phase_without_session_errors(self, server):
        result = server.call_tool("run_phase", {"session_id": "nonexistent"})
        assert result["status"] == "error"

    def test_run_phase_after_start(self, server):
        start = server.call_tool(
            "start_negotiation",
            {
                "jira_key": "MCP-002",
                "jira_summary": "Phase Test",
                "acceptance_criteria": [
                    {"index": 0, "text": "AC1", "checked": False}
                ],
            },
        )
        session_id = start["session_id"]
        result = server.call_tool("run_phase", {"session_id": session_id})
        assert result["status"] in ("success", "no_change")

    def test_get_spec_without_session_errors(self, server):
        result = server.call_tool("get_spec", {"session_id": "nonexistent"})
        assert result["status"] == "error"

    def test_get_verdicts_without_session_errors(self, server):
        result = server.call_tool("get_verdicts", {"session_id": "nonexistent"})
        assert result["status"] == "error"

    def test_dispatch_skills_without_session_errors(self, server):
        result = server.call_tool("dispatch_skills", {"session_id": "nonexistent"})
        assert result["status"] == "error"

    def test_unknown_tool_errors(self, server):
        result = server.call_tool("nonexistent_tool", {})
        assert result["status"] == "error"

    def test_tool_results_are_json_serializable(self, server):
        result = server.call_tool(
            "start_negotiation",
            {
                "jira_key": "MCP-JSON",
                "jira_summary": "JSON Test",
                "acceptance_criteria": [
                    {"index": 0, "text": "AC1", "checked": False}
                ],
            },
        )
        # Should not raise
        json.dumps(result)


# ---------------------------------------------------------------
# P10.2 — MCP Resources
# ---------------------------------------------------------------


class TestMCPResources:
    """MCPServer should expose specs and sessions as resources."""

    @pytest.fixture
    def server(self, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        from verify.mcp_server import MCPServer

        return MCPServer()

    def test_list_resources_returns_list(self, server):
        resources = server.list_resources()
        assert isinstance(resources, list)

    def test_list_resources_after_session_creation(self, server):
        server.call_tool(
            "start_negotiation",
            {
                "jira_key": "RES-001",
                "jira_summary": "Resource Test",
                "acceptance_criteria": [],
            },
        )
        resources = server.list_resources()
        session_uris = [r["uri"] for r in resources if "sessions" in r["uri"]]
        assert len(session_uris) >= 1

    def test_read_session_resource(self, server):
        start = server.call_tool(
            "start_negotiation",
            {
                "jira_key": "RES-002",
                "jira_summary": "Read Session",
                "acceptance_criteria": [],
            },
        )
        session_id = start["session_id"]
        content = server.read_resource(f"verify://sessions/{session_id}")
        assert "jira_key" in content

    def test_read_missing_resource_errors(self, server):
        with pytest.raises(KeyError):
            server.read_resource("verify://specs/NONEXISTENT-999")

    def test_read_spec_resource(self, server, tmp_path, monkeypatch):
        specs_dir = tmp_path / ".verify" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "SPEC-001.yaml").write_text("key: SPEC-001\n")
        monkeypatch.setattr("verify.mcp_server.SPECS_DIR", specs_dir)

        resources = server.list_resources()
        spec_uris = [r["uri"] for r in resources if "specs" in r["uri"]]
        assert any("SPEC-001" in uri for uri in spec_uris)

        content = server.read_resource("verify://specs/SPEC-001")
        assert "key: SPEC-001" in content


# ---------------------------------------------------------------
# P10.3 — Server Info
# ---------------------------------------------------------------


class TestMCPServerInfo:
    """MCPServer should provide server metadata."""

    def test_server_info(self):
        from verify.mcp_server import MCPServer

        server = MCPServer()
        info = server.server_info()
        assert info["name"] == "magic-agents"
        assert "version" in info

    def test_server_capabilities(self):
        from verify.mcp_server import MCPServer

        server = MCPServer()
        caps = server.capabilities()
        assert "tools" in caps
        assert "resources" in caps
