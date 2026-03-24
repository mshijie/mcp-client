# MCP Client

Streamlit web app for connecting to MCP (Model Context Protocol) servers, browsing tools, and interacting with them.

## Features

- Connect to MCP servers (HTTP/SSE and stdio transports)
- Tool Tester: select a tool, fill parameters via form, call it, and view formatted results
- Document View: browse all tools with descriptions and parameter tables

## Dev Environment

- Python >= 3.13
- Package manager: uv
- UI framework: Streamlit (wide layout, single-page app)
- Key files:
  - `app.py` — Streamlit UI (sidebar navigation, tool tester, document view)
  - `mcp_transport.py` — MCP protocol transport layer (HTTPTransport, StdioTransport, MCPClient)
  - `.mcp.json` — server configuration (gitignored, contains API keys)

## Run

```
uv run streamlit run app.py
```
