"""MCP Tool Viewer & Tester — Streamlit web app."""

import json
import re

import pandas as pd
import streamlit as st

from mcp_transport import MCPClient, load_config

st.set_page_config(page_title="MCP Tool Tester", layout="wide")

st.markdown(
    """
    <style>
        div[data-testid="stMainBlockContainer"] {
            padding-top: 0.75rem !important;
            padding-bottom: 2rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
            padding-top: 0.75rem !important;
        }

        div[data-testid="stHeader"] {
            height: 0 !important;
            min-height: 0 !important;
            background: transparent !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Session state defaults ---
for key, default in {
    "config": None,
    "clients": {},
    "tools": {},
    "selected_server": None,
    "selected_tool": None,
    "tool_search_query": {},
    "call_result": None,
    "connect_error": None,
    "call_error": None,
    "call_params": None,
    "view_mode": "tool_tester",
}.items():
    st.session_state.setdefault(key, default)

# --- Load config ---
if st.session_state.config is None:
    st.session_state.config = load_config()

config = st.session_state.config
servers = config.get("mcpServers", {})


def render_tool_summary(tool_def, *, heading_level="header"):
    name = tool_def["name"]
    description = tool_def.get("description", "")

    if heading_level == "subheader":
        st.subheader(name)
    else:
        st.header(name)

    if description:
        st.markdown(description)


def render_tool_tabs(tool_def, parsed_label, raw_label, *, heading_level="header", render_parsed_content):
    tab_parsed, tab_raw = st.tabs([parsed_label, raw_label])

    with tab_parsed:
        render_tool_summary(tool_def, heading_level=heading_level)
        render_parsed_content()

    with tab_raw:
        st.json(tool_def)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("MCP Client")

    if not servers:
        st.warning("No servers found in .mcp.json")
        st.stop()

    # --- Server selection ---
    server_names = list(servers.keys())
    selected_server = st.selectbox("Server", server_names, key="server_select")

    # Show server info
    srv_cfg = servers[selected_server]
    st.caption(f"Type: `{srv_cfg.get('type', 'http')}`")
    if "url" in srv_cfg:
        st.caption(f"URL: `{srv_cfg['url'][:60]}...`" if len(srv_cfg.get("url", "")) > 60 else f"URL: `{srv_cfg.get('url', '')}`")

    # --- Connect ---
    if st.button("Connect", width="stretch"):
        st.session_state.connect_error = None
        st.session_state.call_result = None
        st.session_state.selected_tool = None
        try:
            # Close existing client if any
            old = st.session_state.clients.get(selected_server)
            if old:
                old.close()
            client = MCPClient(selected_server, srv_cfg)
            client.initialize()
            tools = client.list_tools()
            st.session_state.clients[selected_server] = client
            st.session_state.tools[selected_server] = tools
            st.session_state.selected_server = selected_server
        except Exception as e:
            st.session_state.connect_error = str(e)

    # Connection status
    if st.session_state.connect_error:
        st.error(st.session_state.connect_error)
    elif selected_server in st.session_state.clients:
        tool_count = len(st.session_state.tools.get(selected_server, []))
        st.success(f"Connected — {tool_count} tools")

        # Document view toggle
        if st.session_state.view_mode == "document":
            if st.button("Back to Tester", width="stretch"):
                st.session_state.view_mode = "tool_tester"
                st.rerun()
        else:
            if st.button("📄 Document", width="stretch"):
                # Backup all param widget values before switching
                st.session_state["_param_backup"] = {
                    k: v for k, v in st.session_state.items() if k.startswith("param_")
                }
                st.session_state.view_mode = "document"
                st.rerun()

    st.divider()

    # --- Tools list in sidebar ---
    tools_list = st.session_state.tools.get(selected_server, [])
    if tools_list:
        st.markdown("### Tools")

        search_query = st.text_input(
            "Search tools",
            value=st.session_state.tool_search_query.get(selected_server, ""),
            key=f"tool_search_{selected_server}",
            placeholder="Search by name or description",
        ).strip()
        st.session_state.tool_search_query[selected_server] = search_query

        if search_query:
            query = search_query.casefold()
            filtered_tools = [
                t for t in tools_list
                if query in t["name"].casefold()
                or query in t.get("description", "").casefold()
            ]
        else:
            filtered_tools = tools_list

        def _tool_link_html(name, is_active, href=None):
            bg = "rgba(100,100,255,0.15)" if is_active else "none"
            weight = "600" if is_active else "normal"
            return (
                f'<a href="{href}" style="display:block;padding:4px 8px;text-decoration:none;'
                f"color:inherit;border-radius:4px;font-weight:{weight};background:{bg};font-size:14px;"
                f'" onmouseover="this.style.background=\'rgba(128,128,128,0.15)\'"'
                f' onmouseout="this.style.background=\'{bg}\'"'
                f">{name}</a>"
            )

        if st.session_state.view_mode == "document":
            links = "".join(_tool_link_html(t["name"], False, href=f'#{t["name"]}') for t in filtered_tools)
            if links:
                st.html(f'<div>{links}</div>')
            else:
                st.caption("No matching tools.")
        else:
            if filtered_tools:
                st.markdown("""<style>
                    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.tool-list-scope) div[data-testid="stButton"] {
                        margin: 0;
                    }
                    section[data-testid="stSidebar"] button[kind="tertiary"],
                    section[data-testid="stSidebar"] button[kind="primary"] {
                        justify-content: flex-start !important;
                        width: 100% !important;
                        margin: 0 !important;
                        padding: 4px 8px !important;
                        border: none !important;
                        border-radius: 4px !important;
                        background: none !important;
                        color: inherit !important;
                        box-shadow: none !important;
                        font-size: 14px !important;
                        font-weight: 400 !important;
                        line-height: 1.5 !important;
                        min-height: auto !important;
                    }
                    section[data-testid="stSidebar"] button[kind="tertiary"]:hover,
                    section[data-testid="stSidebar"] button[kind="primary"]:hover {
                        background: rgba(128,128,128,0.15) !important;
                        color: inherit !important;
                    }
                    section[data-testid="stSidebar"] button[kind="tertiary"] > div,
                    section[data-testid="stSidebar"] button[kind="primary"] > div {
                        justify-content: flex-start !important;
                        width: 100% !important;
                    }
                    section[data-testid="stSidebar"] button[kind="tertiary"] p,
                    section[data-testid="stSidebar"] button[kind="primary"] p {
                        margin: 0 !important;
                        width: 100% !important;
                        text-align: left !important;
                        color: inherit !important;
                    }
                    section[data-testid="stSidebar"] button[kind="primary"] {
                        background: rgba(100,100,255,0.15) !important;
                        color: inherit !important;
                        font-weight: 600 !important;
                    }
                    section[data-testid="stSidebar"] button[kind="primary"] p {
                        font-weight: 600 !important;
                    }
                </style>""", unsafe_allow_html=True)
                with st.container():
                    st.html('<div class="tool-list-scope"></div>')
                    for t in filtered_tools:
                        name = t["name"]
                        is_active = name == st.session_state.selected_tool
                        if st.button(
                            name,
                            key=f"tool_btn_{selected_server}_{name}",
                            width="stretch",
                            type="primary" if is_active else "tertiary",
                        ):
                            st.session_state.selected_tool = name
                            st.session_state.call_result = None
                            st.session_state.call_error = None
                            st.rerun()
            else:
                st.caption("No matching tools.")

# ============================================================
# MAIN PANEL
# ============================================================
selected_tool_name = st.session_state.selected_tool
active_server = st.session_state.selected_server

if not active_server or active_server not in st.session_state.clients:
    st.info("Select a server from the sidebar and click **Connect** to get started.")
    st.stop()

# ============================================================
# DOCUMENT VIEW
# ============================================================
if st.session_state.view_mode == "document":
    all_tools = st.session_state.tools.get(active_server, [])
    if not all_tools:
        st.info("No tools available.")
        st.stop()

    st.html("""<style>
        html { scroll-behavior: smooth; }
        .tool-anchor { scroll-margin-top: 80px; }
    </style>""")

    st.title(f"📄 {active_server} — Tool Documentation")
    st.caption(f"{len(all_tools)} tools available")

    for idx, t in enumerate(all_tools):
        name = t["name"]
        schema = t.get("inputSchema", {})
        props = schema.get("properties", {})
        req_fields = set(schema.get("required", []))

        # Anchor + header
        st.html(f'<div id="{name}" class="tool-anchor"></div>')

        def _render_doc_params(props=props, req_fields=req_fields):
            if props:
                rows = []
                for pname, prop in props.items():
                    rows.append({
                        "Name": pname,
                        "Type": prop.get("type", "string"),
                        "Required": "Yes" if pname in req_fields else "No",
                        "Default": str(prop["default"]) if "default" in prop else "—",
                        "Description": prop.get("description", "—"),
                    })
                df = pd.DataFrame(rows)
                st.dataframe(df, width="stretch", hide_index=True, height=(len(rows) + 1) * 35 + 3)
            else:
                st.caption("This tool takes no parameters.")

        render_tool_tabs(
            t,
            "Tool Info",
            "Raw JSON",
            heading_level="subheader",
            render_parsed_content=_render_doc_params,
        )

        if idx < len(all_tools) - 1:
            st.divider()

    st.stop()

if not selected_tool_name:
    st.info("Select a tool from the sidebar to view details and call it.")
    st.stop()

# Find tool definition
tools_list = st.session_state.tools.get(active_server, [])
tool_def = next((t for t in tools_list if t["name"] == selected_tool_name), None)

if not tool_def:
    st.error(f"Tool '{selected_tool_name}' not found.")
    st.stop()

# --- Parameter schema & form ---
input_schema = tool_def.get("inputSchema", {})
properties = input_schema.get("properties", {})
required_fields = set(input_schema.get("required", []))
tool_form_state = {
    "params": {},
    "missing": [],
    "call_clicked": False,
}

def _render_tool_form():
    _backup = st.session_state.get("_param_backup", {})

    def _bk(key, default):
        """Return backup value if available, otherwise the schema default."""
        return _backup[key] if key in _backup else default

    if properties:
        # Header: Name | Value | Description
        header_cols = st.columns([2, 2, 5])
        header_cols[0].markdown("**Name**")
        header_cols[1].markdown("**Value**")
        header_cols[2].markdown("**Description**")

        params = {}
        for pname, prop in properties.items():
            prop_type = prop.get("type", "string")
            is_req = pname in required_fields
            description = prop.get("description", "")
            enum_values = prop.get("enum")
            default = prop.get("default")
            widget_key = f"param_{selected_tool_name}_{pname}"

            row_cols = st.columns([2, 2, 5])

            # Name — red for required
            if is_req:
                row_cols[0].markdown(f":red[**{pname}** *]")
            else:
                row_cols[0].markdown(f"**{pname}**")

            # Description
            row_cols[2].markdown(description if description else "—")

            # Detect [x,y] pair format in description
            _is_pair = bool(re.search(r"\[.+,.+\]", description))

            # Value input
            with row_cols[1]:
                if _is_pair and not enum_values:
                    # [x,y] pair — render as two side-by-side inputs
                    pair_match = re.search(r"\[([^,\]]+),\s*([^\]]+)\]", description)
                    label_a = pair_match.group(1).strip() if pair_match else "min"
                    label_b = pair_match.group(2).strip() if pair_match else "max"
                    dv_a, dv_b = "", ""
                    if isinstance(default, list) and len(default) == 2:
                        dv_a, dv_b = str(default[0]), str(default[1])
                    dv_a = _bk(f"{widget_key}_a", dv_a)
                    dv_b = _bk(f"{widget_key}_b", dv_b)
                    pair_cols = st.columns([1, 0.2, 1])
                    val_a = pair_cols[0].text_input(label_a, value=dv_a, key=f"{widget_key}_a", placeholder=label_a, label_visibility="collapsed")
                    pair_cols[1].markdown("<div style='text-align:center;padding-top:8px'>-</div>", unsafe_allow_html=True)
                    val_b = pair_cols[2].text_input(label_b, value=dv_b, key=f"{widget_key}_b", placeholder=label_b, label_visibility="collapsed")
                    if val_a.strip() or val_b.strip():
                        if prop_type == "string":
                            params[pname] = f"[{val_a},{val_b}]"
                        else:
                            items = []
                            for v in (val_a, val_b):
                                try:
                                    items.append(json.loads(v) if v.strip() else v)
                                except (json.JSONDecodeError, TypeError):
                                    items.append(v)
                            params[pname] = items
                elif enum_values:
                    if is_req:
                        options = [str(v) for v in enum_values]
                        idx = options.index(str(default)) if default is not None and str(default) in options else 0
                    else:
                        options = [""] + [str(v) for v in enum_values]
                        idx = options.index(str(default)) if default is not None and str(default) in options else 0
                    bk_val = _backup.get(widget_key)
                    if bk_val is not None and bk_val in options:
                        idx = options.index(bk_val)
                    val = st.selectbox(pname, options=options, index=idx, key=widget_key, label_visibility="collapsed")
                    if val:
                        params[pname] = val
                elif prop_type == "boolean":
                    bk_bool = _bk(widget_key, bool(default) if default is not None else False)
                    params[pname] = st.checkbox(pname, value=bk_bool, key=widget_key, label_visibility="collapsed")
                elif prop_type in ("integer", "number"):
                    bk_str = _bk(widget_key, str(default) if default is not None else "")
                    val = st.text_input(pname, value=bk_str, key=widget_key, label_visibility="collapsed")
                    if val.strip():
                        try:
                            params[pname] = int(val) if prop_type == "integer" else float(val)
                        except ValueError:
                            st.warning(f"Invalid {prop_type}")
                elif prop_type in ("object", "array"):
                    ph = '{"key":"value"}' if prop_type == "object" else "[1,2,3]"
                    dv = json.dumps(default, ensure_ascii=False) if default is not None else ""
                    bk_str = _bk(widget_key, dv)
                    val = st.text_area(pname, value=bk_str, placeholder=ph, key=widget_key, height=68, label_visibility="collapsed")
                    if val.strip():
                        try:
                            params[pname] = json.loads(val)
                        except json.JSONDecodeError:
                            st.warning("Invalid JSON")
                else:
                    bk_str = _bk(widget_key, str(default) if default is not None else "")
                    val = st.text_input(pname, value=bk_str, key=widget_key, label_visibility="collapsed")
                    if val:
                        params[pname] = val
    else:
        st.caption("This tool takes no parameters.")
        params = {}

    # Validate required fields
    missing = [f for f in required_fields if f not in params]
    tool_form_state["params"] = params
    tool_form_state["missing"] = missing

    st.divider()

    # --- Call tool ---
    col1, col2 = st.columns([1, 4])
    with col1:
        tool_form_state["call_clicked"] = st.button("Call Tool", type="primary", width="stretch")
    with col2:
        if missing:
            st.warning(f"Missing required: {', '.join(missing)}")


render_tool_tabs(
    tool_def,
    "Tool Info",
    "Raw JSON",
    render_parsed_content=_render_tool_form,
)

if tool_form_state["call_clicked"]:
    if tool_form_state["missing"]:
        st.error(f"Please fill required parameters: {', '.join(tool_form_state['missing'])}")
    else:
        st.session_state.call_error = None
        st.session_state.call_params = tool_form_state["params"]
        try:
            client = st.session_state.clients[active_server]
            with st.spinner("Calling tool..."):
                result = client.call_tool(selected_tool_name, tool_form_state["params"])
            st.session_state.call_result = result
        except Exception as e:
            st.session_state.call_error = str(e)

def _split_text_and_json(text: str) -> tuple[str, object | None, str]:
    """Split text into (prefix, parsed_json, suffix)."""
    stripped = text.strip()
    # Fast path: entire text is JSON
    if stripped.startswith(("[", "{")):
        try:
            return "", json.loads(stripped), ""
        except (json.JSONDecodeError, TypeError):
            pass
    # Try to find the largest valid JSON block (array or object) in text
    # by scanning for [ or { and trying to parse from there
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = stripped.find(start_char)
        if start == -1:
            continue
        # Find the last matching end char
        end = stripped.rfind(end_char)
        if end <= start:
            continue
        candidate = stripped[start : end + 1]
        try:
            parsed = json.loads(candidate)
            prefix = stripped[:start].strip()
            suffix = stripped[end + 1 :].strip()
            return prefix, parsed, suffix
        except (json.JSONDecodeError, TypeError):
            pass
    return text, None, ""


def _is_table_data(data: object) -> bool:
    """Check if data is a list of flat dicts (suitable for a table)."""
    if not (isinstance(data, list) and len(data) > 0 and all(isinstance(row, dict) for row in data)):
        return False
    # Reject if any value is a nested dict or list (not flat)
    for row in data[:5]:
        for v in row.values():
            if isinstance(v, (dict, list)):
                return False
    return True


# --- Display result ---
if st.session_state.call_error:
    st.error(f"Error: {st.session_state.call_error}")

if st.session_state.call_result is not None:
    result = st.session_state.call_result
    st.subheader("Result")

    contents = result.get("content", [])
    tab_content, tab_raw, tab_params = st.tabs(["Content", "Full Response", "Request Params"])

    with tab_params:
        if st.session_state.call_params is not None:
            st.json(st.session_state.call_params)
        else:
            st.info("No params")

    with tab_content:
        if contents:
            for item in contents:
                if item.get("type") == "text":
                    text = item["text"]
                    prefix, parsed, suffix = _split_text_and_json(text)

                    if prefix:
                        st.caption(prefix)

                    if parsed is not None:
                        if _is_table_data(parsed):
                            import pandas as pd
                            df = pd.DataFrame(parsed)
                            # Detect image URL columns and configure them
                            img_cols = {}
                            for col in df.columns:
                                sample = df[col].dropna().astype(str).head(5)
                                if sample.str.match(r"https?://.+\.(jpg|jpeg|png|gif|webp|svg)", case=False).all() and len(sample) > 0:
                                    img_cols[col] = st.column_config.ImageColumn(col, width=65)
                            st.dataframe(df, column_config=img_cols, width="stretch", height=900, row_height=50)
                        else:
                            st.json(parsed)
                        if suffix:
                            st.caption(suffix)
                    elif not prefix:
                        st.text(text)
        else:
            st.info("No content")

    with tab_raw:
        st.json(result)
