"""Sidebar component — server selection, connection, tool list."""

import reflex as rx

from mcp_client.state.connection import ConnectionState
from mcp_client.state.tool_tester import ToolTesterState
from mcp_client.state.view import ViewState


def _tool_button(name: rx.Var[str]) -> rx.Component:
    """A single tool button in tester mode."""
    return rx.button(
        name,
        on_click=ToolTesterState.select_tool(name),
        variant=rx.cond(
            ToolTesterState.selected_tool_name == name,
            "solid",
            "ghost",
        ),
        width="100%",
        justify_content="flex-start",
        size="1",
    )


def _tool_link(name: rx.Var[str]) -> rx.Component:
    """A single tool anchor link in document mode."""
    return rx.el.a(
        name,
        href="#" + name,
        style={
            "display": "block",
            "padding": "4px 8px",
            "border_radius": "4px",
            "font_size": "14px",
            "text_decoration": "none",
            "color": "inherit",
            "&:hover": {"background": "rgba(128,128,128,0.15)"},
        },
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

                    # Connect button
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

                    # Connection status
                    rx.cond(
                        ConnectionState.connect_error != "",
                        rx.callout(
                            ConnectionState.connect_error,
                            icon="triangle_alert",
                            color_scheme="red",
                            size="1",
                        ),
                    ),
                    rx.cond(
                        (ConnectionState.connect_error == "") & ConnectionState.is_server_connected,
                        rx.callout(
                            "Connected — " + ConnectionState.connected_tool_count.to(str) + " tools",
                            icon="check",
                            color_scheme="green",
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

            # Tools list
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
                        rx.cond(
                            ViewState.is_document_mode,
                            rx.vstack(
                                rx.foreach(ViewState.filtered_tool_names, _tool_link),
                                width="100%",
                                spacing="0",
                            ),
                            rx.vstack(
                                rx.foreach(ViewState.filtered_tool_names, _tool_button),
                                width="100%",
                                spacing="1",
                            ),
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
        border_right="1px solid var(--gray-a5)",
    )
