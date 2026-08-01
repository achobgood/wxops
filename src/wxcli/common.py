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
    if isinstance(data, str):
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
        f"Note: --fields matched 0 of {n} record(s). If you expected matches, "
        f"re-check the expression; if not, this is a genuine empty result.",
        err=True,
    )


# Query params that ADD FIELDS to each record. Omit one and the field is absent
# from every record — the command still exits 0 and still returns every record,
# so a --fields expression naming that field yields null/[] and reads as a
# truthful zero. `wxcli people list --fields '[].extension'` answers "no user
# has an extension" on an org where every user does.
#
# Proven pairs only, and deliberately narrow. Two limits worth stating:
#
#   1. This catches FIELD expansion, not RECORD expansion. `--has-cx-essentials`
#      is the same class of trap (CLAUDE.md known issue #7: standard
#      `call-queue list` omits CX queues entirely without it) but is invisible
#      here — nothing in a --fields expression says "I also wanted CX queues",
#      so there is no signal to check. Do not add record-expanding flags to
#      this table; they need a different mechanism.
#   2. A field named here may also exist independently on some endpoints. The
#      warning says the answer is not trustworthy, never that it is wrong.
FIELD_UNLOCKS: dict[str, frozenset[str]] = {
    "callingData": frozenset({"extension", "locationId"}),
}


def warn_missing_expansion(
    params: dict | None, fields: str | None, expansions: tuple[str, ...] = ()
) -> None:
    """Say so when --fields asks for a field the request did not unlock.

    The single highest-value interlock in the CLI, because this failure is
    otherwise invisible: exit 0, every record returned, and a confident wrong
    number. Everything else in this module warns about a result that LOOKS
    wrong; this warns about one that looks perfectly right.

    `expansions` is the set of unlocking params THIS endpoint actually accepts,
    passed by the generator. It is not optional rigour — without it the check
    fires on any endpoint whose records legitimately carry `extension` natively
    (virtual lines do), telling the caller to pass a flag that does not exist
    there. A warning that cannot be acted on is worse than none.
    """
    if not fields:
        return
    for param in expansions:
        unlocked = FIELD_UNLOCKS.get(param)
        if not unlocked:
            continue
        if params and params.get(param) is not None:
            continue
        named = sorted(f for f in unlocked if f in fields)
        if not named:
            continue
        typer.echo(
            f"Note: --fields references {', '.join(named)}, which this endpoint "
            f"omits unless --{_flag_of(param)} is passed. Without it the field is "
            f"absent from every record, so an empty or zero result here is not "
            f"evidence of anything. Re-run with --{_flag_of(param)} true.",
            err=True,
        )


def _flag_of(param: str) -> str:
    """camelCase query param -> the --kebab-case option that sets it."""
    out = []
    for ch in param:
        if ch.isupper():
            out.append("-")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)


def verify_write(api, url: str, params: dict | None, sent: Any) -> None:
    """Re-read after a write and report any field that did not take.

    A 2xx proves the request was WELL-FORMED, not that the configuration is
    right. `docs/reference/devices-core.md` carries the worked case:
    device-members does no port validation, so PRIMARY on two ports returns 200
    and both persist. Nothing about the response says the config is wrong.

    Three deliberate limits:

      1. **Only the fields you sent are compared.** A full-response diff drowns
         the signal in server-computed fields (`lastModified`, expanded objects)
         that differ on every call by design.
      2. **Warn-only; the exit code is untouched.** Servers legitimately
         normalise — case, E.164 rewriting, defaults filled in — so a hard
         failure would break correct callers. This reports the difference and
         lets the caller judge it.
      3. **A read-back failure is reported, never swallowed.** "Could not
         verify" and "verified clean" must never look alike, which is the whole
         point of the flag.
    """
    if not isinstance(sent, dict) or not sent:
        typer.echo("Note: --verify had no request body to compare against.", err=True)
        return
    try:
        got = api.session.rest_get(url, params=params)
    except Exception as e:  # noqa: BLE001 - any failure must stay visible
        typer.echo(f"Note: --verify could not re-read {url}: {e}", err=True)
        return
    if not isinstance(got, dict):
        typer.echo("Note: --verify read back a non-object response; cannot compare.", err=True)
        return

    drift = []
    for key, want in sent.items():
        if key not in got:
            drift.append((key, want, "<not present in read-back>"))
        elif got[key] != want:
            drift.append((key, want, got[key]))

    if not drift:
        typer.echo(f"Verified: re-read {url} and all {len(sent)} sent field(s) match.", err=True)
        return
    typer.echo(
        f"Note: --verify re-read {url} and {len(drift)} of {len(sent)} sent "
        f"field(s) differ. A 2xx means the request was accepted, not that it "
        f"took effect — check whether the server normalised these or ignored them:",
        err=True,
    )
    for key, want, actual in drift:
        typer.echo(f"  {key}: sent {want!r}, now {actual!r}", err=True)


def emit(
    data: Any,
    output: str = "json",
    fields: str | None = None,
    columns: list[tuple[str, str]] | None = None,
    limit: int = 0,
    params: dict | None = None,
    expansions: tuple[str, ...] = (),
) -> None:
    """Apply --fields, then render in the requested format.

    A --fields projection determines the table headers: `[].{Name:name}` prints
    a Name column, not the endpoint's configured ID/Name pair. Table output
    takes a list of dicts; a single dict renders as a one-row table; a scalar
    or bare-list result falls back to JSON so a legitimate projection never
    crashes the command.
    """
    # Before the projection warning, because this is the root cause the other
    # one is a symptom of: an unlocked-field miss can render as "matched 0 of N".
    warn_missing_expansion(params, fields, expansions)

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
