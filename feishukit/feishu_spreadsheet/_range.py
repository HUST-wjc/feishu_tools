from __future__ import annotations

import re
from typing import Any

_SINGLE_CELL_RE = re.compile(r"^[A-Za-z]+[1-9][0-9]*$")
_CELL_SPAN_RE = re.compile(r"^[A-Za-z]+[1-9][0-9]*:[A-Za-z]+[1-9][0-9]*$")
_CELL_TO_COL_RE = re.compile(r"^[A-Za-z]+[1-9][0-9]*:[A-Za-z]+$")
_COL_SPAN_RE = re.compile(r"^[A-Za-z]+:[A-Za-z]+$")
_ROW_SPAN_RE = re.compile(r"^[1-9][0-9]*:[1-9][0-9]*$")
_CELL_REF_RE = re.compile(r"^([A-Za-z]+)([1-9][0-9]*)$")


def normalize_value_range(value_range: dict[str, Any] | tuple[str, list[list[Any]]]) -> dict[str, Any]:
    if isinstance(value_range, tuple):
        range_value, values = value_range
        return {"range": normalize_write_range(range_value, values), "values": values}
    if "range" in value_range and "values" in value_range:
        value_range = value_range.copy()
        value_range["range"] = normalize_write_range(value_range["range"], value_range["values"])
    return value_range


def normalize_range_separators(value: str) -> str:
    value = value.strip()
    return value.replace("\\！", "!").replace("\\!", "!").replace("！", "!")


def split_sheet_range(value: str) -> tuple[str, str] | None:
    parts = normalize_range_separators(value).split("!", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def looks_like_relative_range(value: str) -> bool:
    value = normalize_range_separators(value)
    return (
        bool(_SINGLE_CELL_RE.fullmatch(value))
        or bool(_CELL_SPAN_RE.fullmatch(value))
        or bool(_CELL_TO_COL_RE.fullmatch(value))
        or bool(_COL_SPAN_RE.fullmatch(value))
        or bool(_ROW_SPAN_RE.fullmatch(value))
    )


def normalize_point_range(value: str) -> str:
    split = split_sheet_range(value)
    if not split:
        return value
    sheet_id, sub_range = split
    if _SINGLE_CELL_RE.fullmatch(sub_range):
        return f"{sheet_id}!{sub_range}:{sub_range}"
    return value


def normalize_write_range(value: str, values: list[list[Any]]) -> str:
    rows, cols = _matrix_dimensions(values)
    split = split_sheet_range(value)
    if not split:
        return _build_rect_range(value, "A1", rows, cols)
    sheet_id, sub_range = split
    if _SINGLE_CELL_RE.fullmatch(sub_range):
        return _build_rect_range(sheet_id, sub_range, rows, cols)
    return value


def _matrix_dimensions(values: list[list[Any]]) -> tuple[int, int]:
    if not values:
        return 1, 1
    rows = len(values)
    cols = max((len(row) for row in values), default=1)
    return rows, max(cols, 1)


def _build_rect_range(sheet_id: str, anchor: str, rows: int, cols: int) -> str:
    end_cell = _offset_cell(anchor, max(rows - 1, 0), max(cols - 1, 0))
    return f"{sheet_id}!{anchor}:{end_cell}"


def _offset_cell(cell: str, row_offset: int, col_offset: int) -> str:
    match = _CELL_REF_RE.fullmatch(cell.strip())
    if not match:
        raise ValueError(f"无效单元格引用: {cell}")
    col_name, row_text = match.groups()
    col_index = _column_name_to_index(col_name)
    row_index = int(row_text)
    return f"{_column_index_to_name(col_index + col_offset)}{row_index + row_offset}"


def _column_name_to_index(name: str) -> int:
    result = 0
    for char in name.upper().strip():
        if char < "A" or char > "Z":
            raise ValueError(f"无效列名: {name}")
        result = result * 26 + ord(char) - ord("A") + 1
    if result < 1:
        raise ValueError(f"无效列名: {name}")
    return result


def _column_index_to_name(index: int) -> str:
    if index < 1:
        raise ValueError(f"无效列序号: {index}")
    chars: list[str] = []
    while index:
        index -= 1
        chars.append(chr(ord("A") + index % 26))
        index //= 26
    return "".join(reversed(chars))
