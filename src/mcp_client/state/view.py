"""ViewState — view mode toggle and tool search filtering."""

import json

import reflex as rx

from mcp_client.state.connection import ConnectionState


class ViewState(ConnectionState):
    """Controls view mode and tool search/filter. Inherits connection data."""

    view_mode: str = "tool_tester"
    tool_search_query: str = ""

    @rx.var(cache=True)
    def is_document_mode(self) -> bool:
        return self.view_mode == "document"

    @rx.var(cache=True)
    def is_tester_mode(self) -> bool:
        return self.view_mode == "tool_tester"

    @rx.var(cache=True)
    def filtered_tools(self) -> list[dict]:
        tools = self.tools_by_server.get(self.selected_server, [])
        query = self.tool_search_query.strip().casefold()
        if not query:
            return tools
        return [
            t for t in tools
            if query in t["name"].casefold()
            or query in t.get("description", "").casefold()
        ]

    @rx.var(cache=True)
    def filtered_tool_names(self) -> list[str]:
        return [t["name"] for t in self.filtered_tools]

    @rx.var(cache=True)
    def filtered_tool_count(self) -> int:
        return len(self.filtered_tools)

    @rx.var(cache=True)
    def document_tools(self) -> list[dict]:
        """Pre-process tools for document view rendering."""
        result = []
        for tool in self.filtered_tools:
            schema = tool.get("inputSchema", {})
            props = schema.get("properties", {})
            required = set(schema.get("required", []))
            params = []
            for pname, prop in props.items():
                params.append({
                    "name": pname,
                    "type": prop.get("type", "string"),
                    "required": "Yes" if pname in required else "No",
                    "default": str(prop["default"]) if "default" in prop else "",
                    "description": prop.get("description", ""),
                })
            result.append({
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "params": params,
                "has_params": len(params) > 0,
                "raw_json": json.dumps(tool, indent=2, ensure_ascii=False),
            })
        return result

    @rx.event
    def toggle_to_document(self):
        self.view_mode = "document"

    @rx.event
    def toggle_to_tester(self):
        self.view_mode = "tool_tester"

    @rx.event
    def set_search(self, value: str):
        self.tool_search_query = value
