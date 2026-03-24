"""MCP Client — Reflex web app for browsing and testing MCP tools."""

import reflex as rx

from mcp_client.components.sidebar import sidebar
from mcp_client.components.tab_bar import tab_bar
from mcp_client.components.tool_form import tool_form
from mcp_client.components.tool_document import document_view
from mcp_client.components.result_display import result_display
from mcp_client.state.connection import ConnectionState
from mcp_client.state.tool_tester import ToolTesterState
from mcp_client.state.view import ViewState


def main_content() -> rx.Component:
    """Main content area — switches between tester and document views."""
    return rx.cond(
        ~ConnectionState.is_server_connected,
        # Not connected
        rx.callout(
            "Select a server from the sidebar and click Connect to get started.",
            icon="info",
            size="2",
        ),
        # Connected
        rx.cond(
            ViewState.is_document_mode,
            document_view(),
            # Tester mode: tab bar fixed, content scrolls
            rx.cond(
                ToolTesterState.active_tab == "",
                rx.callout(
                    "Select a tool from the sidebar to view details and call it.",
                    icon="info",
                    size="2",
                ),
                rx.cond(
                    ToolTesterState.tab_loading,
                    rx.center(
                        rx.vstack(
                            rx.spinner(size="3"),
                            rx.text("Loading...", size="2", color="gray"),
                            align="center",
                            spacing="2",
                        ),
                        width="100%",
                        min_height="200px",
                    ),
                    rx.vstack(
                        tool_form(),
                        result_display(),
                        width="100%",
                        spacing="4",
                        key=ToolTesterState.selected_tool_name,
                    ),
                ),
            ),
        ),
    )


@rx.page(route="/")
def index() -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.vstack(
            rx.cond(ViewState.is_tester_mode, tab_bar()),
            rx.box(
                main_content(),
                flex="1",
                padding="24px",
                overflow_y="auto",
                overscroll_behavior="none",
                width="100%",
            ),
            flex="1",
            height="100vh",
            spacing="0",
        ),
        width="100%",
        height="100vh",
        spacing="0",
    )


app = rx.App()
