"""ConnectionState — server connection and tool listing."""

import asyncio
from typing import Any

import reflex as rx

from mcp_client.mcp_transport import MCPClient, load_config


def _init_config() -> tuple[dict[str, dict], list[str], str]:
    """Read .mcp.json at class-definition time so state has data immediately."""
    cfg = load_config()
    servers = cfg.get("mcpServers", {})
    names = list(servers.keys())
    return servers, names, names[0] if names else ""


_INIT_CONFIGS, _INIT_NAMES, _INIT_SELECTED = _init_config()


class ConnectionState(rx.State):
    """Base state: manages MCP server connections and tool discovery."""

    server_configs: dict[str, dict] = _INIT_CONFIGS
    server_names: list[str] = _INIT_NAMES
    selected_server: str = _INIT_SELECTED
    connected_servers: dict[str, bool] = {}
    server_tool_counts: dict[str, int] = {}
    connect_error: str = ""
    is_connecting: bool = False
    tools_by_server: dict[str, list[dict]] = {}

    # Backend-only: MCPClient instances (not serialized to frontend)
    _clients: dict[str, Any] = {}

    @rx.event
    def load_config(self):
        cfg = load_config()
        servers = cfg.get("mcpServers", {})
        self.server_configs = servers
        self.server_names = list(servers.keys())
        if self.server_names and not self.selected_server:
            self.selected_server = self.server_names[0]

    @rx.event
    def set_selected_server(self, value: str):
        self.selected_server = value
        self.connect_error = ""

    @rx.var(cache=True)
    def selected_server_type(self) -> str:
        cfg = self.server_configs.get(self.selected_server, {})
        return cfg.get("type", "http")

    @rx.var(cache=True)
    def selected_server_url(self) -> str:
        cfg = self.server_configs.get(self.selected_server, {})
        url = cfg.get("url", "")
        if len(url) > 60:
            return url[:60] + "..."
        return url

    @rx.var(cache=True)
    def is_server_connected(self) -> bool:
        return self.connected_servers.get(self.selected_server, False)

    @rx.var(cache=True)
    def connected_tool_count(self) -> int:
        return self.server_tool_counts.get(self.selected_server, 0)

    @rx.var(cache=True)
    def current_tools(self) -> list[dict]:
        return self.tools_by_server.get(self.selected_server, [])

    @rx.event(background=True)
    async def connect(self):
        async with self:
            server = self.selected_server
            srv_cfg = self.server_configs.get(server, {})
            if not server or not srv_cfg:
                self.connect_error = "No server selected"
                return
            self.is_connecting = True
            self.connect_error = ""

            # Close existing client
            old = self._clients.get(server)
            if old:
                try:
                    old.close()
                except Exception:
                    pass

        try:
            client = MCPClient(server, srv_cfg)
            await asyncio.to_thread(client.initialize)
            tools = await asyncio.to_thread(client.list_tools)

            async with self:
                self._clients[server] = client
                self.tools_by_server[server] = tools
                self.connected_servers[server] = True
                self.server_tool_counts[server] = len(tools)
                self.is_connecting = False
        except Exception as e:
            async with self:
                self.connect_error = str(e)
                self.is_connecting = False
