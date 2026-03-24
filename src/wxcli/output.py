import json
import re
from typing import Any
from rich.console import Console
from rich.table import Table

console = Console()

def format_as_json(data: Any) -> str:
    if hasattr(data, "model_dump"):
        return json.dumps(data.model_dump(by_alias=True), indent=2, default=str)
    if isinstance(data, list):
        items = []
        for item in data:
            if hasattr(item, "model_dump"):
                items.append(item.model_dump(by_alias=True))
            elif isinstance(item, dict):
                items.append(item)
            else:
                items.append(str(item))
        return json.dumps(items, indent=2, default=str)
    return json.dumps(data, indent=2, default=str)


def _auto_detect_columns(item: dict) -> list[tuple[str, str]]:
    """Derive table columns from a dict's keys, skipping nested dicts/lists."""
    cols = []
    for key, val in item.items():
        if isinstance(val, (dict, list)):
            continue
        if not key:
            continue
        # Title-case the camelCase key for the header
        header = key[0].upper() + key[1:]
        # Insert space before uppercase letters: "callType" -> "Call Type"
        header = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', header)
        cols.append((header, key))
    return cols if cols else [("Value", "")]


def print_table(data: list, columns: list[tuple[str, str]], limit: int = 50) -> None:
    """Print data as a Rich table.

    columns: list of (header_name, accessor) tuples.
    accessor can use dot notation for nested attrs e.g. "address.city"
    If the configured columns all resolve to empty on the first item,
    auto-detect columns from the item's keys.
    """
    items = data[:limit] if limit > 0 else data

    # Auto-detect columns if defaults produce all-empty values
    if items and isinstance(items[0], dict):
        first_row = [_resolve_accessor(items[0], acc) for _, acc in columns]
        if all(val is None or val == "" for val in first_row):
            columns = _auto_detect_columns(items[0])

    table = Table(show_header=True, header_style="bold")
    for header, _ in columns:
        table.add_column(header)

    for item in items:
        row = []
        for _, accessor in columns:
            val = _resolve_accessor(item, accessor)
            row.append(str(val) if val is not None else "")
        table.add_row(*row)

    if limit > 0 and len(data) > limit:
        table.add_row(*[f"... {len(data) - limit} more" if i == 0 else "" for i in range(len(columns))])

    console.print(table)


def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    print(format_as_json(data))


def _resolve_accessor(obj: Any, accessor: str) -> Any:
    """Resolve a dot-notation accessor on an object or dict.

    Examples:
        _resolve_accessor(loc, "name") -> loc.name
        _resolve_accessor(loc, "address.city") -> loc.address.city
        _resolve_accessor({"name": "x"}, "name") -> "x"
    """
    parts = accessor.split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    # Handle list types (e.g., emails) — return first element
    if isinstance(current, list) and len(current) > 0:
        return current[0]
    return current
