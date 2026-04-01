# Epic P10: MCP Server Wrapper

**Priority:** 10 (Lower)
**Status:** Done
**Ported From:** `claw-code` MCP integration patterns (server discovery, tool exposure, resource serving)
**Integration Target:** New module: `src/verify/mcp_server.py`

## Rationale

The Model Context Protocol (MCP) allows AI assistants like Claude Code to discover and invoke tools exposed by external servers. magic-agents currently operates as a standalone web app and CLI. By wrapping its core capabilities as an MCP server, users could invoke negotiation phases, compile specs, dispatch skills, and query verdicts directly from Claude Code without switching to the magic-agents UI. This is the lowest priority epic because it requires the registry (P2) and streaming (P6) epics to be in place first.

---

## Story P10.1: Expose Core Pipeline as MCP Tools

### EARS Requirement

> The system **shall** expose the following capabilities as MCP tools: `start_negotiation`, `run_phase`, `get_spec`, `dispatch_skills`, and `get_verdicts`.

### Design by Contract

**Preconditions:**
- The MCP server is running and discoverable by the client.
- Each tool has a JSON Schema for input parameters and return type.
- For `run_phase` and `get_spec`, an active session must exist.

**Postconditions:**
- Each MCP tool maps to a corresponding internal function.
- Tool responses are JSON-serializable with a `status` field.
- Errors return structured error responses (not stack traces).
- Sessions created via MCP tools use the same checkpoint system.

**Invariants:**
- MCP tools are stateless at the protocol level — sessions managed server-side.
- Tool schemas match actual parameter requirements.
- MCP tool calls subject to same permission model as web/CLI (P5).

### Acceptance Criteria

- [x]MCP server exposes 5 tools with JSON Schema definitions.
- [x]`start_negotiation` creates a session and returns session ID.
- [x]`run_phase` advances negotiation and returns phase output.
- [x]`get_spec` returns compiled YAML spec as string.
- [x]`dispatch_skills` triggers artifact generation.
- [x]`get_verdicts` returns evaluation results.

### How to Test

```python
def test_mcp_tool_schemas():
    server = MCPServer()
    tools = server.list_tools()
    assert len(tools) == 5
    for tool in tools:
        assert "inputSchema" in tool

def test_mcp_start_negotiation():
    server = MCPServer()
    result = server.call_tool("start_negotiation", {"jira_key": "TEST-1"})
    assert result["status"] == "success"
    assert "session_id" in result
```

---

## Story P10.2: Expose Specs and Sessions as MCP Resources

### EARS Requirement

> The system **shall** expose compiled specs as MCP resources at `verify://specs/{jira_key}` and active sessions at `verify://sessions/{session_id}`.

### Design by Contract

**Preconditions:**
- MCP server supports `resources/list` and `resources/read` methods.
- Compiled specs exist in `.verify/specs/`.
- Active sessions exist in `SessionStore`.

**Postconditions:**
- `resources/list` returns entries for all specs and sessions.
- `resources/read` for spec URI returns YAML content.
- `resources/read` for session URI returns JSON state summary.
- Non-existent resources return structured error.

**Invariants:**
- Resources are read-only.
- URIs use `verify://` scheme.
- Listing bounded to max 100 entries.

### Acceptance Criteria

- [x]`resources/list` returns spec and session resources.
- [x]`resources/read` for specs returns YAML.
- [x]`resources/read` for sessions returns JSON summary.
- [x]Missing resources return clear error.

### How to Test

```python
def test_mcp_list_resources():
    server = MCPServer()
    resources = server.list_resources()
    spec_resources = [r for r in resources if r["uri"].startswith("verify://specs/")]
    assert isinstance(spec_resources, list)

def test_mcp_read_missing():
    server = MCPServer()
    with pytest.raises(ResourceNotFoundError):
        server.read_resource("verify://specs/NONEXISTENT-999")
```

---

## Story P10.3: MCP Server Configuration and Launch

### EARS Requirement

> **When** the user runs `python -m verify.mcp_server`, the system **shall** start an MCP server on stdio transport, and **where** the `--port` flag is provided, start on SSE transport at that port.

### Design by Contract

**Preconditions:**
- The `mcp` Python package is installed.
- Either stdio or SSE transport selected via CLI flags.

**Postconditions:**
- Server starts and responds to `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`.
- `.claude/mcp.json` template documented for Claude Code discovery.
- Server loads constitution and skill registry before accepting connections.

**Invariants:**
- Server runs until explicitly terminated.
- Each tool call independent (no implicit session state between calls unless session ID provided).
- Respects same environment variables as web app.

### Acceptance Criteria

- [x]`python -m verify.mcp_server` starts on stdio.
- [x]`python -m verify.mcp_server --port 8080` starts on SSE.
- [x]Server responds to MCP initialization handshake.
- [x]Documentation includes `.claude/mcp.json` snippet.

### How to Test

```python
def test_mcp_server_starts():
    proc = subprocess.Popen(
        ["python", "-m", "verify.mcp_server"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    init_msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"capabilities": {}}})
    proc.stdin.write((init_msg + "\n").encode())
    proc.stdin.flush()
    response = proc.stdout.readline()
    data = json.loads(response)
    assert data["result"]["serverInfo"]["name"] == "magic-agents"
    proc.terminate()
```
