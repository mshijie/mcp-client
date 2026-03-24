"""Pure helper functions for parsing and formatting MCP tool results."""

import json
import re


def split_text_and_json(text: str) -> tuple[str, object | None, str]:
    """Split text into (prefix, parsed_json, suffix)."""
    stripped = text.strip()
    # Fast path: entire text is JSON
    if stripped.startswith(("[", "{")):
        try:
            return "", json.loads(stripped), ""
        except (json.JSONDecodeError, TypeError):
            pass
    # Try to find the largest valid JSON block (array or object) in text
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = stripped.find(start_char)
        if start == -1:
            continue
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


def is_table_data(data: object) -> bool:
    """Check if data is a list of flat dicts (suitable for a table)."""
    if not (isinstance(data, list) and len(data) > 0 and all(isinstance(row, dict) for row in data)):
        return False
    for row in data[:5]:
        for v in row.values():
            if isinstance(v, (dict, list)):
                return False
    return True


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
