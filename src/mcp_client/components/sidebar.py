"""Sidebar component — server selection, connection, tool list."""

import reflex as rx

from mcp_client.state.connection import ConnectionState
from mcp_client.state.tool_tester import ToolTesterState
from mcp_client.state.view import ViewState


_TOOL_LINK_STYLE = {
    "display": "block",
    "padding": "4px 8px",
    "border_radius": "var(--radius-2)",
    "font_size": "14px",
    "text_decoration": "none",
    "color": "var(--accent-a11)",
    "cursor": "pointer",
}


def _tool_item(name: rx.Var[str]) -> rx.Component:
    """A single tool item — consistent link style for both modes."""
    return rx.cond(
        ViewState.is_document_mode,
        rx.el.a(
            name,
            href="#" + name,
            style=_TOOL_LINK_STYLE,
        ),
        rx.el.a(
            name,
            on_click=ToolTesterState.select_tool(name),
            style={
                **_TOOL_LINK_STYLE,
                "background": rx.cond(
                    ToolTesterState.selected_tool_name == name,
                    "var(--accent-9)",
                    rx.cond(
                        ToolTesterState.open_tabs.contains(name),
                        "var(--accent-a3)",
                        "none",
                    ),
                ),
                "color": rx.cond(
                    ToolTesterState.selected_tool_name == name,
                    "white",
                    "var(--accent-a11)",
                ),
            },
        ),
    )


def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("MCP Client", size="5"),

            # Server selection
            rx.cond(
                ConnectionState.server_names.length() > 0,
                rx.vstack(
                    rx.select(
                        ConnectionState.server_names,
                        value=ConnectionState.selected_server,
                        on_change=ConnectionState.set_selected_server,
                        width="100%",
                    ),
                    rx.text(
                        "Type: " + ConnectionState.selected_server_type,
                        font_size="12px",
                        color="gray",
                    ),
                    rx.cond(
                        ConnectionState.selected_server_url != "",
                        rx.text(
                            "URL: " + ConnectionState.selected_server_url,
                            font_size="12px",
                            color="gray",
                        ),
                    ),

                    # Connect / Connected button (single button, two states)
                    rx.cond(
                        ConnectionState.is_server_connected & (ConnectionState.connect_error == ""),
                        # Connected state
                        rx.button(
                            rx.hstack(
                                rx.icon("check", size=14),
                                rx.text("Connected — " + ConnectionState.connected_tool_count.to(str) + " tools"),
                                spacing="2",
                                align="center",
                            ),
                            on_click=ConnectionState.connect,
                            variant="soft",
                            color_scheme="green",
                            width="100%",
                        ),
                        # Disconnected / Connecting state
                        rx.button(
                            rx.cond(
                                ConnectionState.is_connecting,
                                rx.hstack(rx.spinner(size="1"), rx.text("Connecting..."), spacing="2"),
                                rx.text("Connect"),
                            ),
                            on_click=ConnectionState.connect,
                            disabled=ConnectionState.is_connecting,
                            width="100%",
                        ),
                    ),

                    # Connection error
                    rx.cond(
                        ConnectionState.connect_error != "",
                        rx.callout(
                            ConnectionState.connect_error,
                            icon="triangle_alert",
                            color_scheme="red",
                            size="1",
                        ),
                    ),

                    # View toggle
                    rx.cond(
                        ConnectionState.is_server_connected,
                        rx.cond(
                            ViewState.is_document_mode,
                            rx.button(
                                "Back to Tester",
                                on_click=ViewState.toggle_to_tester,
                                variant="outline",
                                width="100%",
                                size="2",
                            ),
                            rx.button(
                                "Document",
                                on_click=ViewState.toggle_to_document,
                                variant="outline",
                                width="100%",
                                size="2",
                            ),
                        ),
                    ),
                    width="100%",
                    spacing="2",
                ),
                rx.callout(
                    "No servers found in .mcp.json",
                    icon="info",
                    color_scheme="yellow",
                    size="1",
                ),
            ),

            rx.separator(),

            # Tools list (unified style for both modes)
            rx.cond(
                ConnectionState.is_server_connected,
                rx.vstack(
                    rx.heading("Tools", size="3"),
                    rx.input(
                        placeholder="Search by name or description",
                        value=ViewState.tool_search_query,
                        on_change=ViewState.set_search,
                        width="100%",
                        size="2",
                    ),
                    rx.cond(
                        ViewState.filtered_tool_count > 0,
                        rx.vstack(
                            rx.foreach(ViewState.filtered_tool_names, _tool_item),
                            width="100%",
                            spacing="1",
                        ),
                        rx.text("No matching tools.", font_size="13px", color="gray"),
                    ),
                    width="100%",
                    spacing="2",
                ),
            ),
            width="100%",
            spacing="3",
            padding="16px",
        ),
        width="280px",
        min_width="280px",
        height="100vh",
        overflow_y="auto",
        overscroll_behavior="none",
        border_right="1px solid var(--gray-a5)",
    )
