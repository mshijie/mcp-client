"""Tab bar component — horizontal tabs for open tools."""

import reflex as rx

from mcp_client.state.tool_tester import ToolTesterState


def _tab_item(name: rx.Var[str]) -> rx.Component:
    """A single tab with tool name and close button."""
    is_active = ToolTesterState.selected_tool_name == name
    return rx.hstack(
        rx.text(
            name,
            size="2",
            weight=rx.cond(is_active, "bold", "regular"),
            color=rx.cond(is_active, "var(--accent-11)", "var(--gray-11)"),
            cursor="pointer",
            on_click=ToolTesterState.select_tool(name),
            white_space="nowrap",
        ),
        rx.icon(
            "x",
            size=14,
            cursor="pointer",
            color="var(--gray-9)",
            on_click=ToolTesterState.close_tab(name),
            _hover={"color": "var(--gray-12)"},
        ),
        padding="8px 12px",
        border_bottom=rx.cond(
            is_active,
            "2px solid var(--accent-9)",
            "2px solid transparent",
        ),
        background=rx.cond(is_active, "var(--accent-a3)", "none"),
        align="center",
        spacing="2",
        _hover={"background": rx.cond(is_active, "var(--accent-a3)", "var(--gray-a3)")},
    )


def tab_bar() -> rx.Component:
    """Horizontal tab bar showing all open tools."""
    return rx.cond(
        ToolTesterState.has_open_tabs,
        rx.box(
            rx.hstack(
                rx.foreach(ToolTesterState.open_tabs, _tab_item),
                spacing="0",
                overflow_x="auto",
            ),
            border_bottom="1px solid var(--gray-a5)",
            width="100%",
        ),
    )
