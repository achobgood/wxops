"""Shared output pipeline for every wxcli command.

Generated commands import emit() so that --fields and --output behave
identically across all ~1,900 commands.
"""
import json as _json
import sys
from pathlib import Path
from typing import Any

import typer

from wxcli.output import auto_columns, print_json, print_table, print_text

FIELDS_HELP = (
    "JMESPath expression selecting/filtering response fields, "
    "e.g. \"[].{name:name,id:id}\" or \"[?type=='AGENT'].name\""
)


def apply_fields(data: Any, expr: str | None) -> Any:
    """Apply a JMESPath expression. Returns data unchanged when expr is falsy."""
    if not expr:
        return data
    import jmespath
    from jmespath.exceptions import JMESPathError

    try:
        return jmespath.search(expr, data)
    except JMESPathError as e:
        typer.echo(f"Error: invalid --fields expression: {e}", err=True)
        raise typer.Exit(2)


def _record_count(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return 1 if data else 0
    return 0 if data is None else 1


def _is_empty(data: Any) -> bool:
    return data is None or (isinstance(data, (list, dict, str)) and len(data) == 0)


def _warn_if_projection_emptied(before: Any, after: Any, fields: str | None) -> None:
    """Stop a wrong --fields expression from looking exactly like a true zero.

    CLAUDE.md's Discovery-First rule: only accept a negative once the query
    could have returned a positive. Goes to stderr so stdout stays pipeable.
    """
    if not fields or not _is_empty(after):
        return
    n = _record_count(before)
    if n == 0:
        return
    typer.echo(
        f"Note: --fields matched nothing; the unfiltered response held {n} record(s). "
        f"Re-run without --fields before concluding the result is empty.",
        err=True,
    )


def emit(
    data: Any,
    output: str = "json",
    fields: str | None = None,
    columns: list[tuple[str, str]] | None = None,
    limit: int = 0,
) -> None:
    """Apply --fields, then render in the requested format.

    A --fields projection determines the table headers: `[].{Name:name}` prints
    a Name column, not the endpoint's configured ID/Name pair. Table output
    takes a list of dicts; a single dict renders as a one-row table; a scalar
    or bare-list result falls back to JSON so a legitimate projection never
    crashes the command.
    """
    raw = data
    data = apply_fields(data, fields)
    _warn_if_projection_emptied(raw, data, fields)

    if output == "id":
        if isinstance(data, dict):
            typer.echo(data.get("id", ""))
        else:
            print_json(data)
    elif output == "text":
        print_text(data)
    elif output == "table":
        if isinstance(data, list) and (not data or isinstance(data[0], dict)):
            cols = auto_columns(data[0]) if (fields and data) else (
                columns or [("ID", "id"), ("Name", "name")])
            print_table(data, columns=cols, limit=limit)
        elif isinstance(data, dict):
            # A single object in table mode renders as a one-row auto-column
            # table — the behaviour every generated `show -o table` already
            # has today: locations.py:126-134 passes decoy ("Key","")/
            # ("Value","") columns that resolve empty and always trigger
            # print_table's auto-detect fallback. JSON-printing dicts here
            # would change show's table mode on every generated command.
            print_table([data], columns=auto_columns(data), limit=0)
        else:
            print_json(data)
    else:
        print_json(data)


def load_json_body(value: str) -> dict:
    """Read a request body from an inline string, file://path, path, or stdin.

    Pairs with --generate-json-body: a skeleton you cannot feed back in is
    half a feature, and non-trivial bodies do not survive shell quoting.
    """
    if value == "-":
        text, source = sys.stdin.read(), "stdin"
    elif value.startswith("file://"):
        path = Path(value[len("file://"):])
        if not path.is_file():
            typer.echo(f"Error: --json-body file not found: {path}", err=True)
            raise typer.Exit(2)
        text, source = path.read_text(encoding="utf-8"), str(path)
    elif not value.lstrip().startswith(("{", "[")) and Path(value).is_file():
        text, source = Path(value).read_text(encoding="utf-8"), value
    else:
        text, source = value, "--json-body"

    try:
        return _json.loads(text)
    except _json.JSONDecodeError as e:
        typer.echo(f"Error: {source} is not valid JSON: {e}", err=True)
        raise typer.Exit(2)
