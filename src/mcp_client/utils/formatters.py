"""Pure helper functions for parsing and formatting MCP tool results."""

import json
import re
from typing import Any


def split_text_segments(text: str) -> list[tuple[str, Any]]:
    """Split text into alternating ("text", str) and ("json", parsed) segments.

    Finds all valid, non-trivial JSON fragments in *text* and returns them
    interleaved with the surrounding plain-text spans.

    Rules:
    - Only extracts JSON that is non-trivial (dict with >=1 key, or list with >=1 element).
    - Empty ``{}`` and ``[]`` are left as plain text.
    - Uses brace-depth counting to locate matching closing delimiters.
    """
    stripped = text.strip()
    if not stripped:
        return []

    # Fast path: entire text is valid JSON
    if stripped[0] in ("{", "["):
        try:
            parsed = json.loads(stripped)
            if _is_nontrivial(parsed):
                return [("json", parsed)]
        except (json.JSONDecodeError, TypeError):
            pass

    segments: list[tuple[str, Any]] = []
    pos = 0
    length = len(stripped)

    while pos < length:
        # Find next potential JSON start
        next_start = -1
        for i in range(pos, length):
            if stripped[i] in ("{", "["):
                next_start = i
                break

        if next_start == -1:
            # No more braces — rest is text
            remaining = stripped[pos:].strip()
            if remaining:
                segments.append(("text", remaining))
            break

        # Use brace-depth counting to find matching close
        open_char = stripped[next_start]
        close_char = "}" if open_char == "{" else "]"
        depth = 0
        in_string = False
        escape_next = False
        match_end = -1

        for i in range(next_start, length):
            ch = stripped[i]
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                if in_string:
                    escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    match_end = i
                    break

        if match_end == -1:
            # Unmatched brace — skip past it as text
            pos = next_start + 1
            continue

        candidate = stripped[next_start : match_end + 1]
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            parsed = None

        if parsed is not None and _is_nontrivial(parsed):
            # Emit text before the JSON
            before = stripped[pos:next_start].strip()
            if before:
                segments.append(("text", before))
            segments.append(("json", parsed))
            pos = match_end + 1
        else:
            # Not valid or trivial JSON — skip past the entire matched region
            # so that closing braces (e.g. from {}) don't leak into text
            pos = match_end + 1

    # If nothing was extracted, return whole text
    if not segments:
        return [("text", stripped)]

    return segments


def _is_nontrivial(data: object) -> bool:
    """Return True if *data* is a non-empty dict or non-empty list."""
    if isinstance(data, dict) and len(data) > 0:
        return True
    if isinstance(data, list) and len(data) > 0:
        return True
    return False


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def is_table_data(data: object) -> bool:
    """Check if data is a list of flat dicts (suitable for a table)."""
    if not (isinstance(data, list) and len(data) > 0 and all(isinstance(row, dict) for row in data)):
        return False
    for row in data[:5]:
        for v in row.values():
            if isinstance(v, (dict, list)):
                return False
    return True


def is_flat_dict(data: object) -> bool:
    """Check if data is a non-empty dict with all scalar values."""
    if not isinstance(data, dict) or len(data) == 0:
        return False
    for v in data.values():
        if isinstance(v, (dict, list)):
            return False
    return True


def has_complex_values(data: dict) -> bool:
    """Return True if any value in *data* is a dict or list."""
    return any(isinstance(v, (dict, list)) for v in data.values())


def detect_image_columns(rows: list[dict]) -> list[str]:
    """Return column names whose values are image URLs."""
    if not rows:
        return []
    pattern = re.compile(r"https?://.+\.(jpg|jpeg|png|gif|webp|svg)", re.IGNORECASE)
    image_cols = []
    columns = list(rows[0].keys())
    for col in columns:
        samples = [str(row.get(col, "")) for row in rows[:5] if row.get(col)]
        if samples and all(pattern.match(s) for s in samples):
            image_cols.append(col)
    return image_cols


# ---------------------------------------------------------------------------
# Dict explosion — recursive
# ---------------------------------------------------------------------------

def _make_display_item(
    *,
    is_text: bool = False,
    is_table: bool = False,
    is_json: bool = False,
    text: str = "",
    json_str: str = "",
    table_columns: list[str] | None = None,
    table_rows: list[dict[str, str]] | None = None,
    image_columns: list[str] | None = None,
    section_title: str = "",
) -> dict[str, Any]:
    """Create a uniform display-item dict."""
    return {
        "is_text": is_text,
        "is_table": is_table,
        "is_json": is_json,
        "text": text,
        "json_str": json_str,
        "table_columns": table_columns or [],
        "table_rows": table_rows or [],
        "image_columns": image_columns or [],
        "section_title": section_title,
        "has_section_title": bool(section_title),
    }


def _make_table_item(
    rows: list[dict],
    *,
    section_title: str = "",
    override_columns: list[str] | None = None,
) -> dict[str, Any]:
    """Create a table display-item from a list of dicts."""
    columns = override_columns or list(rows[0].keys())
    str_rows = [
        {k: str(v) if v is not None else "" for k, v in row.items()}
        for row in rows
    ]
    return _make_display_item(
        is_table=True,
        table_columns=columns,
        table_rows=str_rows,
        image_columns=detect_image_columns(rows) if not override_columns else [],
        section_title=section_title,
    )


def explode_dict(data: dict, title_prefix: str = "", max_depth: int = 3) -> list[dict[str, Any]]:
    """Recursively explode a dict into display-ready items.

    Groups consecutive scalar key-values into one kv_table section.
    Each complex value gets its own titled section.
    """
    items: list[dict[str, Any]] = []
    scalar_buffer: list[tuple[str, Any]] = []

    def _flush_scalars(title: str) -> None:
        if not scalar_buffer:
            return
        kv_rows = [{"Key": str(k), "Value": str(v) if v is not None else ""} for k, v in scalar_buffer]
        items.append(_make_table_item(
            kv_rows,
            section_title=title,
            override_columns=["Key", "Value"],
        ))
        scalar_buffer.clear()

    for key, value in data.items():
        child_title = f"{title_prefix} > {key}" if title_prefix else key

        if not isinstance(value, (dict, list)):
            # Scalar — buffer it
            scalar_buffer.append((key, value))
            continue

        # Flush any buffered scalars before a complex value
        _flush_scalars(title_prefix)

        if is_table_data(value):
            items.append(_make_table_item(value, section_title=child_title))
        elif isinstance(value, dict) and has_complex_values(value) and max_depth > 1:
            items.extend(explode_dict(value, title_prefix=child_title, max_depth=max_depth - 1))
        elif is_flat_dict(value):
            kv_rows = [{"Key": str(k), "Value": str(v) if v is not None else ""} for k, v in value.items()]
            items.append(_make_table_item(
                kv_rows,
                section_title=child_title,
                override_columns=["Key", "Value"],
            ))
        else:
            items.append(_make_display_item(
                is_json=True,
                json_str=json.dumps(value, indent=2, ensure_ascii=False),
                section_title=child_title,
            ))

    # Flush remaining scalars
    _flush_scalars(title_prefix)

    return items
