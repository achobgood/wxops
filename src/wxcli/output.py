import json
import os
import re
import sys
from typing import Any
from rich import box as _box
from rich.cells import cell_len
from rich.console import Console
from rich.table import Table


def plain_mode() -> bool:
    """True when output is being captured rather than read by a human.

    Auto-detection is the point: an agent must not have to discover a flag
    before it stops paying for box-drawing characters. WXCLI_PLAIN overrides
    in both directions for testing and for forcing plain output in a terminal.
    """
    override = os.environ.get("WXCLI_PLAIN")
    if override is not None:
        return override.strip().lower() not in ("", "0", "false", "no")
    return not sys.stdout.isatty()


def _make_console() -> Console:
    return Console()


console = _make_console()

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


def auto_columns(item: dict) -> list[tuple[str, str]]:
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
            columns = auto_columns(items[0])

    plain = plain_mode()
    table = Table(show_header=True, header_style="bold",
                  box=None if plain else _box.HEAVY_HEAD)
    for header, _ in columns:
        table.add_column(header)

    rows: list[list[str]] = []
    for item in items:
        row = []
        for _, accessor in columns:
            val = _resolve_accessor(item, accessor)
            row.append(str(val) if val is not None else "")
        table.add_row(*row)
        rows.append(row)

    if limit > 0 and len(data) > limit:
        more_row = [f"... {len(data) - limit} more" if i == 0 else "" for i in range(len(columns))]
        table.add_row(*more_row)
        rows.append(more_row)

    if plain:
        # No human ever reads this — the output is parsed by an agent that
        # treats a value as complete once it sees it. Rich defaults to an
        # 80-column layout when stdout isn't a terminal and silently
        # ellipsis-truncates any cell that doesn't fit (e.g. an ID), which
        # looks like a whole value and 404s on the next call with no error.
        # Size the console to exactly fit the widest value in each column
        # (plus a safety margin) so nothing is ever truncated or wrapped —
        # every record still renders on exactly one line. cell_len (not
        # len()) accounts for wide/unicode characters.
        headers = [header for header, _ in columns]
        col_widths = [max([cell_len(h)] + [cell_len(r[i]) for r in rows]) for i, h in enumerate(headers)]
        render_width = sum(w + 4 for w in col_widths) + 4
        render_console = Console(width=render_width)
    else:
        render_console = console

    render_console.print(table)


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


def _text_cell(val: Any) -> str:
    """Render one --output text cell: compact JSON for nested values, empty for None."""
    if isinstance(val, (dict, list)):
        return json.dumps(val, separators=(",", ":"), default=str)
    if val is None:
        return ""
    return str(val)


def _text_row(item: Any, keys: list[str] | None = None) -> str:
    """One --output text row: tab-separated scalars, nested values as compact JSON.

    keys, when given, fixes the column order (padding a record's missing key
    with an empty cell) so a record that omits an optional field doesn't
    shift every later column out of alignment with the rest of the table.
    """
    if isinstance(item, dict):
        if keys is None:
            keys = list(item.keys())
        return "\t".join(_text_cell(item.get(k)) for k in keys)
    return "" if item is None else str(item)


def print_text(data: Any) -> None:
    """AWS-style --output text: one record per line, tab-separated fields.

    This is what makes --fields composable in a shell pipeline:
        wxcli call-queue list --fields '[].name' -o text | while read name; do ...

    Webex routinely omits absent optional fields per record (e.g. `extension`
    only appears for calling-licensed users). Without a shared column order, a
    record missing a field shifts every later column, so `cut -f4` silently
    returns the wrong value for that row. When the data is a list of dicts,
    derive one stable order — the union of keys across every record, in
    first-seen order — and pad a missing key with an empty cell instead of
    skipping it.
    """
    if isinstance(data, list):
        if data and all(isinstance(item, dict) for item in data):
            keys: list[str] = []
            seen: set[str] = set()
            for item in data:
                for k in item:
                    if k not in seen:
                        seen.add(k)
                        keys.append(k)
            for item in data:
                print(_text_row(item, keys))
        else:
            for item in data:
                print(_text_row(item))
    else:
        print(_text_row(data))
