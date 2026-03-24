"""Result display component — formatted output from tool calls."""

import reflex as rx

from mcp_client.state.tool_tester import ToolTesterState


def _table_cell(value: rx.Var[str], image_columns: rx.Var[list[str]], col_name: rx.Var[str]) -> rx.Component:
    """Render a table cell, with image rendering for detected image columns."""
    return rx.table.cell(
        rx.cond(
            image_columns.contains(col_name),
            rx.image(src=value, width="65px", height="auto"),
            rx.text(value, size="1"),
        ),
    )


def _result_table_header(columns: rx.Var[list[str]]) -> rx.Component:
    return rx.table.header(
        rx.table.row(
            rx.foreach(
                columns,
                lambda col: rx.table.column_header_cell(rx.text(col, size="1")),
            ),
        ),
    )


def _result_table_row(row: rx.Var[dict[str, str]], columns: rx.Var[list[str]], image_columns: rx.Var[list[str]]) -> rx.Component:
    return rx.table.row(
        rx.foreach(
            columns,
            lambda col: _table_cell(row[col], image_columns, col),
        ),
    )


def _content_item(item: rx.Var[dict]) -> rx.Component:
    """Render a single content item with smart formatting."""
    return rx.vstack(
        # Prefix text
        rx.cond(
            item["has_prefix"].to(bool),
            rx.text(item["prefix"].to(str), color="gray", size="2"),
        ),
        # Main content
        rx.cond(
            item["is_table"].to(bool),
            # Table display
            rx.box(
                rx.table.root(
                    _result_table_header(item["table_columns"].to(list[str])),
                    rx.table.body(
                        rx.foreach(
                            item["table_rows"].to(list[dict[str, str]]),
                            lambda row: _result_table_row(
                                row,
                                item["table_columns"].to(list[str]),
                                item["image_columns"].to(list[str]),
                            ),
                        ),
                    ),
                    width="100%",
                    size="1",
                ),
                width="100%",
                overflow_x="auto",
                max_height="600px",
                overflow_y="auto",
            ),
            rx.cond(
                item["is_json"].to(bool),
                rx.code_block(
                    item["json_str"].to(str),
                    language="json",
                    width="100%",
                ),
                # Plain text (only if no prefix was already shown)
                rx.cond(
                    ~item["has_prefix"].to(bool),
                    rx.text(item["text"].to(str), size="2", white_space="pre-wrap"),
                ),
            ),
        ),
        # Suffix text
        rx.cond(
            item["has_suffix"].to(bool),
            rx.text(item["suffix"].to(str), color="gray", size="2"),
        ),
        width="100%",
        spacing="2",
    )


def result_display() -> rx.Component:
    """Display tool call results with Content/Full Response/Params tabs."""
    return rx.cond(
        ToolTesterState.has_result,
        rx.vstack(
            rx.heading("Result", size="4"),
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Content", value="content"),
                    rx.tabs.trigger("Full Response", value="raw"),
                    rx.tabs.trigger("Request Params", value="params"),
                ),
                rx.tabs.content(
                    rx.cond(
                        ToolTesterState.result_contents.length() > 0,
                        rx.vstack(
                            rx.foreach(ToolTesterState.result_contents, _content_item),
                            width="100%",
                            spacing="3",
                        ),
                        rx.text("No content", color="gray"),
                    ),
                    value="content",
                    padding="12px 0",
                ),
                rx.tabs.content(
                    rx.code_block(
                        ToolTesterState.result_json_str,
                        language="json",
                        width="100%",
                    ),
                    value="raw",
                    padding="12px 0",
                ),
                rx.tabs.content(
                    rx.cond(
                        ToolTesterState.call_params_json_str != "",
                        rx.code_block(
                            ToolTesterState.call_params_json_str,
                            language="json",
                            width="100%",
                        ),
                        rx.text("No params", color="gray"),
                    ),
                    value="params",
                    padding="12px 0",
                ),
                default_value="content",
                width="100%",
            ),
            width="100%",
            spacing="3",
        ),
    )
