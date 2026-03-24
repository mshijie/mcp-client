"""MCP protocol transport layer — supports HTTP and stdio servers."""

import json
import os
import subprocess
import threading
from pathlib import Path

import requests


def load_config(path: str = ".mcp.json") -> dict:
    """Load MCP server configuration from .mcp.json file."""
    config_path = Path(path)
    if not config_path.is_absolute():
        # Resolve relative to project root (where rxconfig.py lives)
        project_root = Path(__file__).resolve().parent.parent.parent
        config_path = project_root / path
    if not config_path.exists():
        return {"mcpServers": {}}
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


class HTTPTransport:
    """JSON-RPC over HTTP with SSE support."""

    DEFAULT_HEADERS = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "User-Agent": "claude-code/2.1.81 (cli)",
        "mcp-protocol-version": "2025-06-18",
        "Connection": "keep-alive",
    }

    def __init__(self, url: str, headers: dict | None = None):
        self.url = url
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        if headers:
            self.session.headers.update(headers)
        self._id_counter = 0

    def send_request(self, method: str, params: dict | None = None) -> dict:
        self._id_counter += 1
        body = {
            "jsonrpc": "2.0",
            "id": self._id_counter,
            "method": method,
        }
        if params is not None:
            body["params"] = params

        resp = self.session.post(
            self.url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            timeout=120,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            return self._parse_sse(resp.text)
        return resp.json()

    @staticmethod
    def _parse_sse(text: str) -> dict:
        """Extract the last JSON-RPC data line from an SSE stream."""
        last_data = None
        for line in text.strip().split("\n"):
            if line.startswith("data:"):
                last_data = line[5:].strip()
        if last_data:
            return json.loads(last_data)
        raise ValueError(f"No data found in SSE response: {text[:500]}")

    def close(self):
        self.session.close()


class StdioTransport:
    """JSON-RPC over subprocess stdin/stdout."""

    def __init__(self, command: str, args: list[str] | None = None, env: dict | None = None):
        merged_env = {**os.environ, **(env or {})}
        self.process = subprocess.Popen(
            [command] + (args or []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=merged_env,
            text=True,
            bufsize=1,
        )
        self._id_counter = 0
        self._lock = threading.Lock()

    def send_request(self, method: str, params: dict | None = None) -> dict:
        with self._lock:
            self._id_counter += 1
            req_id = self._id_counter
            body = {"jsonrpc": "2.0", "id": req_id, "method": method}
            if params is not None:
                body["params"] = params

            line = json.dumps(body, ensure_ascii=False) + "\n"
            self.process.stdin.write(line)
            self.process.stdin.flush()

            # Read lines until we get a response matching our id
            while True:
                response_line = self.process.stdout.readline()
                if not response_line:
                    stderr = self.process.stderr.read()
                    raise ConnectionError(
                        f"Server closed connection. stderr: {stderr}"
                    )
                try:
                    data = json.loads(response_line)
                    if data.get("id") == req_id:
                        return data
                except json.JSONDecodeError:
                    continue  # skip non-JSON lines (notifications, logs)

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class MCPClient:
    """High-level MCP client wrapping a transport."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        server_type = config.get("type", "http")

        if server_type == "http":
            self.transport = HTTPTransport(
                url=config["url"],
                headers=config.get("headers"),
            )
        elif server_type == "stdio":
            self.transport = StdioTransport(
                command=config["command"],
                args=config.get("args", []),
                env=config.get("env"),
            )
        else:
            raise ValueError(f"Unsupported transport type: {server_type}")

        self._initialized = False

    def initialize(self) -> dict:
        """Send MCP initialize handshake."""
        result = self.transport.send_request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "mcp-client", "version": "0.1.0"},
        })
        self._initialized = True
        return result

    def list_tools(self) -> list[dict]:
        """Get available tools from the server."""
        if not self._initialized:
            self.initialize()
        resp = self.transport.send_request("tools/list", {})
        result = resp.get("result", resp)
        return result.get("tools", [])

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool with the given arguments."""
        if not self._initialized:
            self.initialize()
        resp = self.transport.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        return resp.get("result", resp)

    def close(self):
        self.transport.close()
