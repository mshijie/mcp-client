"""ToolTesterState — tool selection, parameter form, and call execution."""

import asyncio
import json
import re
from typing import Any

import reflex as rx

from mcp_client.state.connection import ConnectionState
from mcp_client.utils.formatters import detect_image_columns, is_table_data, split_text_and_json


class ToolTesterState(ConnectionState):
    """Manages tool selection, form parameters, and call results. Inherits connection data."""

    selected_tool_name: str = ""
    call_result: dict = {}
    call_error: str = ""
    call_params: dict = {}
    is_calling: bool = False
    sort_column: str = ""
    sort_ascending: bool = True

    @rx.event
    def select_tool(self, name: str):
        self.selected_tool_name = name
        self.call_result = {}
        self.call_error = ""
        self.call_params = {}
        self.sort_column = ""
        self.sort_ascending = True

    @rx.event
    def toggle_sort(self, column: str):
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True

    @rx.event
    def download_table_csv(self):
        """Download the first table in results as CSV."""
        import csv
        import io

        contents = self.result_contents
        for item_data in contents:
            if item_data.get("is_table"):
                output = io.StringIO()
                writer = csv.writer(output)
                columns = item_data["table_columns"]
                writer.writerow(columns)
                for row in item_data["table_rows"]:
                    writer.writerow([row.get(col, "") for col in columns])
                return rx.download(data=output.getvalue(), filename="table_data.csv")

    @rx.var(cache=True)
    def selected_tool_def(self) -> dict:
        tools = self.tools_by_server.get(self.selected_server, [])
        for t in tools:
            if t["name"] == self.selected_tool_name:
                return t
        return {}

    @rx.var(cache=True)
    def tool_description(self) -> str:
        return self.selected_tool_def.get("description", "")

    @rx.var(cache=True)
    def tool_def_json(self) -> str:
        tool = self.selected_tool_def
        if not tool:
            return ""
        return json.dumps(tool, indent=2, ensure_ascii=False)

    @rx.var(cache=True)
    def properties(self) -> list[dict]:
        """Pre-process inputSchema into a flat list for rx.foreach rendering."""
        tool = self.selected_tool_def
        if not tool:
            return []
        schema = tool.get("inputSchema", {})
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        result = []
        for name, prop in props.items():
            prop_type = prop.get("type", "string")
            description = prop.get("description", "")
            enum_values = prop.get("enum")
            default = prop.get("default")
            is_pair = bool(re.search(r"\[.+,.+\]", description))

            pair_labels = ["min", "max"]
            if is_pair:
                m = re.search(r"\[([^,\]]+),\s*([^\]]+)\]", description)
                if m:
                    pair_labels = [m.group(1).strip(), m.group(2).strip()]

            if default is not None and prop_type in ("object", "array"):
                default_str = json.dumps(default, ensure_ascii=False)
            elif default is not None:
                default_str = str(default)
            else:
                default_str = ""

            enum_list: list[str] = []
            if enum_values:
                if name not in required:
                    enum_list = ["(none)"] + [str(v) for v in enum_values]
                else:
                    enum_list = [str(v) for v in enum_values]

            result.append({
                "name": name,
                "type": prop_type,
                "required": name in required,
                "description": description or "",
                "has_enum": bool(enum_values),
                "enum_values": enum_list,
                "default": default_str,
                "default_bool": bool(default) if prop_type == "boolean" else False,
                "is_pair": is_pair,
                "pair_label_a": pair_labels[0],
                "pair_label_b": pair_labels[1] if len(pair_labels) > 1 else "max",
                "placeholder": '{"key":"value"}' if prop_type == "object" else "[1,2,3]" if prop_type == "array" else "",
                "form_key": f"param_{name}",
                "form_key_a": f"param_{name}_a",
                "form_key_b": f"param_{name}_b",
            })
        return result

    @rx.var(cache=True)
    def has_properties(self) -> bool:
        return len(self.properties) > 0

    @rx.var(cache=True)
    def has_result(self) -> bool:
        return bool(self.call_result)

    @rx.var(cache=True)
    def result_contents(self) -> list[dict]:
        """Pre-process call result into display-ready items."""
        if not self.call_result:
            return []
        contents = self.call_result.get("content", [])
        items = []
        for item in contents:
            if item.get("type") == "text":
                prefix, parsed, suffix = split_text_and_json(item["text"])
                display: dict[str, Any] = {
                    "has_prefix": bool(prefix),
                    "prefix": prefix,
                    "has_suffix": bool(suffix),
                    "suffix": suffix,
                    "is_table": False,
                    "is_json": False,
                    "text": item["text"],
                    "json_str": "",
                    "table_columns": [],
                    "table_rows": [],
                    "image_columns": [],
                }
                if parsed is not None:
                    if is_table_data(parsed):
                        display["is_table"] = True
                        display["table_columns"] = list(parsed[0].keys())
                        rows = [
                            {k: str(v) if v is not None else "" for k, v in row.items()}
                            for row in parsed
                        ]
                        # Apply sorting
                        if self.sort_column and self.sort_column in display["table_columns"]:
                            def _sort_key(r: dict) -> tuple:
                                val = r.get(self.sort_column, "")
                                try:
                                    num = float(val.replace("%", "").replace(",", ""))
                                    return (0, num)
                                except (ValueError, AttributeError):
                                    return (1, val.lower() if isinstance(val, str) else str(val))
                            rows.sort(key=_sort_key, reverse=not self.sort_ascending)
                        display["table_rows"] = rows
                        display["image_columns"] = detect_image_columns(parsed)
                    else:
                        display["is_json"] = True
                        display["json_str"] = json.dumps(parsed, indent=2, ensure_ascii=False)
                items.append(display)
        return items

    @rx.var(cache=True)
    def result_json_str(self) -> str:
        if not self.call_result:
            return ""
        return json.dumps(self.call_result, indent=2, ensure_ascii=False)

    @rx.var(cache=True)
    def call_params_json_str(self) -> str:
        if not self.call_params:
            return ""
        return json.dumps(self.call_params, indent=2, ensure_ascii=False)

    @rx.event(background=True)
    async def call_tool(self, form_data: dict):
        async with self:
            props = self.properties
            tool_name = self.selected_tool_name
            self.is_calling = True
            self.call_error = ""

        try:
            params: dict[str, Any] = {}
            for prop in props:
                name = prop["name"]
                prop_type = prop["type"]

                if prop["is_pair"]:
                    val_a = str(form_data.get(prop["form_key_a"], "")).strip()
                    val_b = str(form_data.get(prop["form_key_b"], "")).strip()
                    if val_a or val_b:
                        if prop_type == "string":
                            params[name] = f"[{val_a},{val_b}]"
                        else:
                            items = []
                            for v in (val_a, val_b):
                                try:
                                    items.append(json.loads(v) if v else v)
                                except (json.JSONDecodeError, TypeError):
                                    items.append(v)
                            params[name] = items
                else:
                    val = str(form_data.get(prop["form_key"], "")).strip()
                    if not val or val == "(none)":
                        continue
                    if prop["has_enum"]:
                        params[name] = val
                    elif prop_type == "boolean":
                        params[name] = val.lower() in ("true", "on", "1")
                    elif prop_type == "integer":
                        try:
                            params[name] = int(val)
                        except ValueError:
                            async with self:
                                self.call_error = f"Invalid integer for {name}"
                                self.is_calling = False
                            return
                    elif prop_type == "number":
                        try:
                            params[name] = float(val)
                        except ValueError:
                            async with self:
                                self.call_error = f"Invalid number for {name}"
                                self.is_calling = False
                            return
                    elif prop_type in ("object", "array"):
                        try:
                            params[name] = json.loads(val)
                        except json.JSONDecodeError:
                            async with self:
                                self.call_error = f"Invalid JSON for {name}"
                                self.is_calling = False
                            return
                    else:
                        params[name] = val

            # Validate required
            missing = [p["name"] for p in props if p["required"] and p["name"] not in params]
            if missing:
                async with self:
                    self.call_error = f"Missing required: {', '.join(missing)}"
                    self.is_calling = False
                return

            # Get client and call tool
            async with self:
                client = self._clients.get(self.selected_server)

            if not client:
                async with self:
                    self.call_error = "Not connected to server"
                    self.is_calling = False
                return

            result = await asyncio.to_thread(client.call_tool, tool_name, params)

            async with self:
                self.call_result = result
                self.call_params = params
                self.is_calling = False
        except Exception as e:
            async with self:
                self.call_error = str(e)
                self.is_calling = False
