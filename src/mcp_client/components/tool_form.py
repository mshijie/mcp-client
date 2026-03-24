"""Dynamic tool parameter form component."""

import reflex as rx

from mcp_client.state.tool_tester import ToolTesterState


def _pair_input(prop: rx.Var[dict]) -> rx.Component:
    """Two side-by-side inputs for [x,y] pair parameters."""
    return rx.hstack(
        rx.input(
            name=prop["form_key_a"].to(str),
            placeholder=prop["pair_label_a"].to(str),
            default_value=prop["default"].to(str),
            size="2",
            width="45%",
        ),
        rx.text("-", color="gray"),
        rx.input(
            name=prop["form_key_b"].to(str),
            placeholder=prop["pair_label_b"].to(str),
            size="2",
            width="45%",
        ),
        width="100%",
        align="center",
    )


def _enum_input(prop: rx.Var[dict]) -> rx.Component:
    return rx.select(
        prop["enum_values"].to(list[str]),
        name=prop["form_key"].to(str),
        default_value=prop["default"].to(str),
        width="100%",
        size="2",
    )


def _boolean_input(prop: rx.Var[dict]) -> rx.Component:
    return rx.checkbox(
        name=prop["form_key"].to(str),
        default_checked=prop["default_bool"].to(bool),
    )


def _textarea_input(prop: rx.Var[dict]) -> rx.Component:
    return rx.el.textarea(
        name=prop["form_key"].to(str),
        placeholder=prop["placeholder"].to(str),
        default_value=prop["default"].to(str),
        rows=3,
        style={
            "width": "100%",
            "padding": "6px 8px",
            "border": "1px solid var(--gray-a7)",
            "border_radius": "var(--radius-2)",
            "font_size": "14px",
            "font_family": "inherit",
            "resize": "vertical",
        },
    )


def _text_input(prop: rx.Var[dict]) -> rx.Component:
    return rx.input(
        name=prop["form_key"].to(str),
        default_value=prop["default"].to(str),
        width="100%",
        size="2",
    )


def _value_widget(prop: rx.Var[dict]) -> rx.Component:
    """Select the right widget based on property type."""
    return rx.cond(
        prop["is_pair"].to(bool),
        _pair_input(prop),
        rx.cond(
            prop["has_enum"].to(bool),
            _enum_input(prop),
            rx.cond(
                prop["type"].to(str) == "boolean",
                _boolean_input(prop),
                rx.cond(
                    (prop["type"].to(str) == "object") | (prop["type"].to(str) == "array"),
                    _textarea_input(prop),
                    _text_input(prop),
                ),
            ),
        ),
    )


def _param_row(prop: rx.Var[dict]) -> rx.Component:
    """One row: Name | Value | Description."""
    return rx.hstack(
        # Name column
        rx.box(
            rx.cond(
                prop["required"].to(bool),
                rx.text(prop["name"].to(str), " *", color="red", weight="bold", size="2"),
                rx.text(prop["name"].to(str), weight="bold", size="2"),
            ),
            width="20%",
            min_width="120px",
        ),
        # Value column
        rx.box(
            _value_widget(prop),
            width="25%",
            min_width="160px",
        ),
        # Description column
        rx.box(
            rx.text(prop["description"].to(str), size="2", color="gray"),
            width="55%",
        ),
        width="100%",
        align="start",
        spacing="3",
    )


def _call_button_row() -> rx.Component:
    """Call Tool button and error callout."""
    return rx.hstack(
        rx.button(
            rx.cond(
                ToolTesterState.is_calling,
                rx.hstack(rx.spinner(size="1"), rx.text("Calling..."), spacing="2"),
                rx.text("Call Tool"),
            ),
            type="submit",
            disabled=ToolTesterState.is_calling,
        ),
        rx.cond(
            ToolTesterState.call_error != "",
            rx.callout(
                ToolTesterState.call_error,
                icon="triangle_alert",
                color_scheme="red",
                size="1",
            ),
        ),
        align="center",
        spacing="3",
    )


def tool_form() -> rx.Component:
    """The tool parameter form with Call Tool button."""
    return rx.vstack(
        rx.cond(
            ToolTesterState.tool_description != "",
            rx.text(ToolTesterState.tool_description),
        ),
        rx.cond(
            ToolTesterState.has_properties,
            rx.form(
                rx.vstack(
                    # Header
                    rx.hstack(
                        rx.box(rx.text("Name", weight="bold", size="2"), width="20%", min_width="120px"),
                        rx.box(rx.text("Value", weight="bold", size="2"), width="25%", min_width="160px"),
                        rx.box(rx.text("Description", weight="bold", size="2"), width="55%"),
                        width="100%",
                        spacing="3",
                    ),
                    rx.separator(),
                    # Parameter rows
                    rx.foreach(ToolTesterState.properties, _param_row),
                    rx.separator(),
                    _call_button_row(),
                    width="100%",
                    spacing="3",
                ),
                on_submit=ToolTesterState.call_tool,
                width="100%",
            ),
            rx.form(
                rx.vstack(
                    rx.text("This tool takes no parameters.", color="gray", size="2"),
                    rx.separator(),
                    _call_button_row(),
                    width="100%",
                    spacing="3",
                ),
                on_submit=ToolTesterState.call_tool,
                width="100%",
            ),
        ),
        width="100%",
        spacing="3",
    )
