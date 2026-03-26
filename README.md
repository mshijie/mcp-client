# MCP Client

A lightweight web UI for connecting to [MCP](https://modelcontextprotocol.io/) servers, browsing available tools, and calling them interactively.

## Features

- **Connect** to MCP servers via HTTP/SSE or stdio
- **Tool Tester** — select a tool, fill in parameters, call it, and view formatted results (tables, JSON, images)
- **Document View** — browse all tools in one page with descriptions and parameter tables

## Quick Start

### Prerequisites

- Python >= 3.13
- [uv](https://github.com/astral-sh/uv)

### Install & Run

```bash
git clone https://github.com/mshijie/mcp-client.git
cd mcp-client
uv sync
./run.sh
```

### Configuration

Create a `.mcp.json` file in the project root:

```json
{
  "mcpServers": {
    "my-server": {
      "type": "http",
      "url": "https://your-mcp-server-url"
    }
  }
}
```

Stdio transport is also supported:

```json
{
  "mcpServers": {
    "my-server": {
      "type": "stdio",
      "command": "node",
      "args": ["path/to/server.js"]
    }
  }
}
```
