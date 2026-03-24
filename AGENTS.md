# MCP Client

Reflex web app for connecting to MCP (Model Context Protocol) servers, browsing tools, and interacting with them.

## Features

- Connect to MCP servers (HTTP/SSE and stdio transports)
- Tool Tester: select a tool, fill parameters via form, call it, and view formatted results
- Document View: browse all tools with descriptions and parameter tables

## Dev Environment

- Python >= 3.12 (pinned to 3.13)
- Package manager: uv
- UI framework: Reflex (single-page app with sidebar layout)
- Project layout: `src/` layout (`src/mcp_client/`)
- Key files:
  - `rxconfig.py` — Reflex configuration (adds `src/` to sys.path)
  - `src/mcp_client/mcp_client.py` — App entry point, page layout
  - `src/mcp_client/mcp_transport.py` — MCP protocol transport layer (HTTPTransport, StdioTransport, MCPClient)
  - `src/mcp_client/state/` — State classes (ConnectionState, ViewState, ToolTesterState)
  - `src/mcp_client/components/` — UI components (sidebar, tool_form, tool_document, result_display)
  - `src/mcp_client/utils/formatters.py` — Pure helper functions for result formatting
  - `.mcp.json` — server configuration (gitignored, contains API keys)

## Run

```
uv run reflex run
```
