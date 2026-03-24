"""Parameter table for document view."""

import reflex as rx


def _param_row(prop: rx.Var[dict]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(prop["name"], size="2")),
        rx.table.cell(rx.text(prop["type"], size="2")),
        rx.table.cell(
            rx.cond(
                prop["required"],
                rx.text("Yes", size="2", color="red"),
                rx.text("No", size="2"),
            )
        ),
        rx.table.cell(rx.text(prop["default"], size="2")),
        rx.table.cell(rx.text(prop["description"], size="2")),
    )


def param_table(properties: rx.Var[list[dict]]) -> rx.Component:
    """Render a parameter table for a tool's properties."""
    return rx.cond(
        properties.length() > 0,
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
                rx.foreach(properties, _param_row),
            ),
            width="100%",
            size="2",
        ),
        rx.text("This tool takes no parameters.", color="gray", size="2"),
    )
