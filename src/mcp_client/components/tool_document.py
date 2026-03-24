"""Document view — browse all tools with descriptions and parameter tables."""

import reflex as rx

from mcp_client.state.connection import ConnectionState
from mcp_client.state.view import ViewState


def _doc_param_row(param: rx.Var[dict]) -> rx.Component:
    """Render a parameter row in the document table."""
    return rx.table.row(
        rx.table.cell(rx.text(param["name"], size="2")),
        rx.table.cell(rx.text(param["type"], size="2")),
        rx.table.cell(
            rx.cond(
                param["required"] == "Yes",
                rx.text("Yes", size="2", color="red"),
                rx.text("No", size="2"),
            ),
        ),
        rx.table.cell(rx.text(param["default"], size="2")),
        rx.table.cell(rx.text(param["description"], size="2")),
    )


def _tool_card(tool: rx.Var[dict]) -> rx.Component:
    """Render a single tool in document view."""
    return rx.vstack(
        rx.el.div(id=tool["name"]),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Tool Info", value="info"),
                rx.tabs.trigger("Raw JSON", value="raw"),
            ),
            rx.tabs.content(
                rx.vstack(
                    rx.heading(tool["name"], size="4"),
                    rx.cond(
                        tool["description"] != "",
                        rx.text(tool["description"]),
                    ),
                    rx.cond(
                        tool["has_params"],
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Name"),
                                    rx.table.column_header_cell("Type"),
                                    rx.table.column_header_cell("Required"),
                                    rx.table.column_header_cell("Default"),
                                    rx.table.column_header_cell("Description"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(tool["params"].to(list[dict[str, str]]), _doc_param_row),
                            ),
                            width="100%",
                            size="2",
                        ),
                        rx.text("This tool takes no parameters.", color="gray", size="2"),
                    ),
                    width="100%",
                    spacing="3",
                    padding="12px 0",
                ),
                value="info",
            ),
            rx.tabs.content(
                rx.code_block(
                    tool["raw_json"],
                    language="json",
                    width="100%",
                ),
                value="raw",
                padding="12px 0",
            ),
            default_value="info",
            width="100%",
        ),
        rx.separator(),
        width="100%",
        spacing="2",
    )


def document_view() -> rx.Component:
    """Full document view showing all tools."""
    return rx.vstack(
        rx.heading(
            ConnectionState.selected_server + " — Tool Documentation",
            size="5",
        ),
        rx.text(
            ViewState.filtered_tool_count.to(str) + " tools available",
            color="gray",
            size="2",
        ),
        rx.foreach(ViewState.document_tools, _tool_card),
        width="100%",
        spacing="4",
    )
