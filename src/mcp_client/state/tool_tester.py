"""ToolTesterState — multi-tab tool testing with per-tab state."""

import asyncio
import json
import re
from typing import Any

import reflex as rx

from mcp_client.state.connection import ConnectionState
from mcp_client.utils.formatters import (
    _make_display_item,
    _make_table_item,
    explode_dict,
    has_complex_values,
    is_flat_dict,
    is_table_data,
    split_text_segments,
)


class ToolTesterState(ConnectionState):
    """Manages multi-tab tool testing. Each open tool has independent state."""

    # Tab management
    open_tabs: list[str] = []
    active_tab: str = ""

    # Per-tab state (keyed by tool name)
    tab_results: dict[str, dict] = {}
    tab_errors: dict[str, str] = {}
    tab_params: dict[str, dict] = {}
    tab_calling: dict[str, bool] = {}
    tab_form_data: dict[str, dict[str, str]] = {}  # form field values per tab

    # Table sorting (shared, resets on tab switch)
    sort_column: str = ""
    sort_ascending: bool = True

    # Loading state for tab switch animation
    tab_loading: bool = False

    # --- Computed var compatibility layer ---
    # These expose the active tab's data with the same names as the old
    # single-tool state vars, so tool_form.py and result_display.py need
    # zero changes to their state references.

    @rx.var(cache=True)
    def selected_tool_name(self) -> str:
        return self.active_tab

    @rx.var(cache=True)
    def call_result(self) -> dict:
        return self.tab_results.get(self.active_tab, {})

    @rx.var(cache=True)
    def call_error(self) -> str:
        return self.tab_errors.get(self.active_tab, "")

    @rx.var(cache=True)
    def call_params(self) -> dict:
        return self.tab_params.get(self.active_tab, {})

    @rx.var(cache=True)
    def is_calling(self) -> bool:
        return self.tab_calling.get(self.active_tab, False)

    @rx.var(cache=True)
    def has_open_tabs(self) -> bool:
        return len(self.open_tabs) > 0

    # --- Event handlers ---

    @rx.event
    def set_field_value(self, field_key: str, value: str):
        """Save a form field value for the active tab."""
        if not self.active_tab:
            return
        if self.active_tab not in self.tab_form_data:
            self.tab_form_data[self.active_tab] = {}
        self.tab_form_data[self.active_tab][field_key] = value

    @rx.event
    def set_field_bool(self, field_key: str, value: bool):
        """Save a boolean form field value for the active tab."""
        if not self.active_tab:
            return
        if self.active_tab not in self.tab_form_data:
            self.tab_form_data[self.active_tab] = {}
        self.tab_form_data[self.active_tab][field_key] = "true" if value else "false"

    def _init_form_data(self, tool_name: str):
        """Pre-populate form data with defaults for a new tab."""
        tools = self.tools_by_server.get(self.selected_server, [])
        tool = None
        for t in tools:
            if t["name"] == tool_name:
                tool = t
                break
        if not tool:
            self.tab_form_data[tool_name] = {}
            return
        schema = tool.get("inputSchema", {})
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        data: dict[str, str] = {}
        for pname, prop in props.items():
            prop_type = prop.get("type", "string")
            enum_values = prop.get("enum")
            default = prop.get("default")
            if default is None and enum_values and pname in required:
                default = enum_values[0]
            if default is not None:
                if prop_type in ("object", "array"):
                    data[f"param_{pname}"] = json.dumps(default, ensure_ascii=False)
                else:
                    data[f"param_{pname}"] = str(default)
        self.tab_form_data[tool_name] = data

    @rx.event
    def select_tool(self, name: str):
        """Open a tool tab (or switch to it if already open).

        Two-phase yield: tab bar updates instantly, then content renders.
        """
        if name == self.active_tab:
            return
        if name not in self.open_tabs:
            self.open_tabs = self.open_tabs + [name]
            self._init_form_data(name)
        self.active_tab = name
        self.sort_column = ""
        self.sort_ascending = True
        self.tab_loading = True
        yield
        self.tab_loading = False

    @rx.event
    def close_tab(self, name: str):
        """Close a tab and clean up its state."""
        if name not in self.open_tabs:
            return
        idx = self.open_tabs.index(name)
        self.open_tabs = [t for t in self.open_tabs if t != name]
        self.tab_results.pop(name, None)
        self.tab_errors.pop(name, None)
        self.tab_params.pop(name, None)
        self.tab_calling.pop(name, None)
        self.tab_form_data.pop(name, None)
        # Switch to nearest neighbor if closing the active tab
        if self.active_tab == name:
            if self.open_tabs:
                self.active_tab = self.open_tabs[min(idx, len(self.open_tabs) - 1)]
                self.sort_column = ""
                self.sort_ascending = True
                self.tab_loading = True
                yield
                self.tab_loading = False
            else:
                self.active_tab = ""
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

    # --- Existing computed vars (unchanged, derive from compatibility layer) ---

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
        form_data = self.tab_form_data.get(self.active_tab, {})
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

            # Auto-select first enum value for required enum fields
            if default is None and enum_values and name in required:
                default = enum_values[0]

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
                # Saved form values (falls back to defaults)
                "value": form_data.get(f"param_{name}", default_str),
                "value_a": form_data.get(f"param_{name}_a", ""),
                "value_b": form_data.get(f"param_{name}_b", ""),
                "value_bool": form_data.get(f"param_{name}", "false").lower() in ("true", "on", "1") if prop_type == "boolean" else (bool(default) if prop_type == "boolean" else False),
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
        items: list[dict[str, Any]] = []
        for item in contents:
            if item.get("type") == "text":
                segments = split_text_segments(item["text"])
                for seg_type, seg_data in segments:
                    if seg_type == "text":
                        items.append(_make_display_item(is_text=True, text=seg_data))
                    elif seg_type == "json":
                        items.extend(self._classify_json(seg_data))
        # Apply sorting to all table items
        self._apply_sorting(items)
        return items

    def _classify_json(self, parsed: object) -> list[dict[str, Any]]:
        """Classify a parsed JSON value into one or more display items."""
        if is_table_data(parsed):
            return [_make_table_item(parsed)]
        if isinstance(parsed, dict) and has_complex_values(parsed):
            return explode_dict(parsed)
        if is_flat_dict(parsed):
            kv_rows = [{"Key": str(k), "Value": str(v) if v is not None else ""} for k, v in parsed.items()]
            return [_make_table_item(kv_rows, override_columns=["Key", "Value"])]
        return [_make_display_item(
            is_json=True,
            json_str=json.dumps(parsed, indent=2, ensure_ascii=False),
        )]

    def _apply_sorting(self, items: list[dict[str, Any]]) -> None:
        """Apply current sort_column/sort_ascending to all table items in-place."""
        if not self.sort_column:
            return
        for display in items:
            if not display.get("is_table"):
                continue
            columns = display.get("table_columns", [])
            if self.sort_column not in columns:
                continue
            rows = display.get("table_rows", [])
            sort_col = self.sort_column

            def _sort_key(r: dict) -> tuple:
                val = r.get(sort_col, "")
                try:
                    num = float(val.replace("%", "").replace(",", ""))
                    return (0, num)
                except (ValueError, AttributeError):
                    return (1, val.lower() if isinstance(val, str) else str(val))

            rows.sort(key=_sort_key, reverse=not self.sort_ascending)

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
            tool_name = self.active_tab  # capture at start for tab safety
            self.tab_calling[tool_name] = True
            self.tab_errors[tool_name] = ""

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
                                self.tab_errors[tool_name] = f"Invalid integer for {name}"
                                self.tab_calling[tool_name] = False
                            return
                    elif prop_type == "number":
                        try:
                            params[name] = float(val)
                        except ValueError:
                            async with self:
                                self.tab_errors[tool_name] = f"Invalid number for {name}"
                                self.tab_calling[tool_name] = False
                            return
                    elif prop_type in ("object", "array"):
                        try:
                            params[name] = json.loads(val)
                        except json.JSONDecodeError:
                            async with self:
                                self.tab_errors[tool_name] = f"Invalid JSON for {name}"
                                self.tab_calling[tool_name] = False
                            return
                    else:
                        params[name] = val

            # Validate required
            missing = [p["name"] for p in props if p["required"] and p["name"] not in params]
            if missing:
                async with self:
                    self.tab_errors[tool_name] = f"Missing required: {', '.join(missing)}"
                    self.tab_calling[tool_name] = False
                return

            # Get client and call tool
            async with self:
                client = self._clients.get(self.selected_server)

            if not client:
                async with self:
                    self.tab_errors[tool_name] = "Not connected to server"
                    self.tab_calling[tool_name] = False
                return

            result = await asyncio.to_thread(client.call_tool, tool_name, params)

            async with self:
                if tool_name in self.open_tabs:
                    self.tab_results[tool_name] = result
                    self.tab_params[tool_name] = params
                self.tab_calling[tool_name] = False
        except Exception as e:
            async with self:
                if tool_name in self.open_tabs:
                    self.tab_errors[tool_name] = str(e)
                self.tab_calling[tool_name] = False
