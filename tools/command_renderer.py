"""Render Endpoint objects into complete wxcli Typer command .py files."""
import base64
import re
from pathlib import Path

from tools.postman_parser import (
    DESTRUCTIVE_SEMANTICS,
    Endpoint,
    EndpointField,
    camel_to_snake,
    camel_to_kebab,
    summary_leading_verb,
)


BASE_URL = "https://webexapis.com/v1"
BASE_URL_NO_V1 = "https://webexapis.com"
BASE_URL_ANALYTICS = "https://analytics-calling.webexapis.com/v1"
BASE_URL_CC = "{cc_base_url}"  # Resolved at runtime from config
BASE_URL_FS = "{fs_base_url}"  # Resolved at runtime from config

# Path prefixes that use the base URL without /v1
NO_V1_PREFIXES = ("identity/", "Schemas/")

# Paths that use analytics.webexapis.com instead of webexapis.com
ANALYTICS_PREFIXES = ("cdr_feed", "cdr_stream")

# Module-level override set by render_command_file for spec-specific base URLs (e.g., CC)
_active_base_url_override: str | None = None

# The CLI group currently being rendered ("locations", "call-queue"). Argument
# help and the runnable example both need to name the command as an operator
# types it, and the six render paths are dispatched through a fixed
# (ep, folder_overrides) signature — same reason _active_base_url_override is
# a module global rather than a parameter.
_active_cli_name: str = ""

# Existing v2 command modules — generate with _generated suffix to avoid collision
V2_MODULES = {
    "auto_attendants", "call_park", "call_pickup", "call_queues",
    "hunt_groups", "operating_modes", "paging", "schedules",
    "voicemail_groups", "locations", "users", "numbers", "licenses",
    "configure",
}

# Spec-declared paging param names that are suppressed on list commands in
# favor of the generator's unified --limit/--offset flags. The renderer maps
# --limit to whichever of {limit, max} the endpoint uses (preferring spec-
# declared "limit" when present) and --offset to {offset, start}.
_SUPPRESS_SPEC_PAGING_NAMES = {"max", "start", "offset", "limit"}

# CLI option names the renderer injects unconditionally, via
# _render_output_options(), on every generated command (list, show, create,
# update, delete, settings-get, settings-update, action). Unlike the paging
# names above, there is no renderer flag with equivalent semantics that a
# colliding spec parameter could be folded into: --fields is a client-side
# JMESPath post-filter over an already-fetched response, not the same
# operation as a spec's own server-side field-selection query parameter
# (e.g. CC Functions' `fields=id,name,status`, evaluated by the API). Nor
# does PYTHON_KEYWORDS-style suffixing help here — that renames the local
# variable but leaves the CLI flag text ("--fields") unchanged, so a spec
# "fields" param would still emit a second --fields option bound to a
# different variable: two Click options sharing one flag string, which
# Typer accepts silently and just shadows (see tools/CLAUDE.md's --filter
# discussion of the same failure mode). So a collision here fails the
# generator build loudly (ReservedParamCollisionError) instead of being
# silently dropped or silently shadowed.
# `all` joined these when --all shipped. Not hypothetical: webex-flow-store.json
# already declares a query parameter literally named `all` on
# GET /{orgId}/project/{projectId}/flows/{flowId}/tags. It is inert only because
# that spec is dev-only and gitignored. Unguarded, a tracked spec adding one
# would emit two options spelling "--all" and Typer would silently shadow one —
# the same silent failure the --filter analysis in tools/CLAUDE.md rejected.
_RESERVED_OUTPUT_PARAM_NAMES = {"output", "fields", "all"}


class ReservedParamCollisionError(Exception):
    """A spec-derived parameter's CLI name collides with an option the
    renderer injects unconditionally on every command (see
    _RESERVED_OUTPUT_PARAM_NAMES). Left unguarded, the generated function
    would declare two parameters with the same name — a SyntaxError at
    import time, discovered only when someone tries to load the generated
    module. Raising here turns that into a clear failure at generation
    time, naming the endpoint and the colliding parameter.
    """


class ParamNameOverrideError(Exception):
    """A param_name_overrides entry does not match a real parameter on a real
    command, or renames one to a name that still collides.

    Checked at generation time so the override cannot rot: if upstream renames
    or drops the parameter the entry targets, the build fails naming the stale
    entry instead of silently leaving it inert (the same anti-rot contract
    verb_semantics_ack has).
    """


class UnboundUrlPlaceholderError(Exception):
    """A rendered URL f-string references a `{name}` that no path variable,
    base-URL injection, or other renderer local actually binds.

    Found live: webex-meetings.json's PUT
    /admin/meeting/config/trackingCodes/{trackingCodeId} declares an empty
    `parameters` array, so `ep.path_vars` was `[]` while the URL template
    still carried `{trackingCodeId}` — every call to
    `meeting-tracking-codes update` raised a bare `NameError:
    name 'trackingCodeId' is not defined`, not a SyntaxError, so `compile()`
    never caught it. `_infer_missing_path_vars` (see `render_command_file`)
    heals this specific shape by borrowing the var from a sibling operation
    on the identical path (the GET/DELETE on that same path both declare
    `trackingCodeId`). This guard is the backstop for cases inference can't
    heal — no sibling declares the var either — so a future spec defect
    fails the build loudly instead of shipping a runtime crash.
    """


_URL_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def folder_name_to_module(folder_name: str) -> tuple[str, str]:
    cleaned = re.sub(r"^Features:\s*", "", folder_name).strip()
    cleaned = re.sub(r"\s*\(\d+/\d+\)", "", cleaned).strip()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned).strip("_").lower()
    cli_name = slug.replace("_", "-")
    return slug, cli_name


def _path_var_to_param(var: str) -> str:
    return camel_to_snake(var)


def _apply_param_name_overrides(endpoints: list, folder_overrides: dict) -> None:
    """Rename a spec parameter's CLI flag without changing its wire name.

    A spec parameter whose CLI name collides with an option the renderer
    injects on every command (_RESERVED_OUTPUT_PARAM_NAMES) cannot be rendered
    as-is: the flag text is built from python_name, so both would emit the
    same "--fields" string and Typer would silently shadow one. Renaming
    python_name changes only the CLI spelling — request assembly keys the
    params dict off qp.name, so the spec's own name still goes on the wire.

    This is the mechanism ReservedParamCollisionError's message points at. It
    exists because the two flags are genuinely different operations: a spec
    "fields" param is server-side field selection, while --fields is a
    client-side JMESPath post-filter. Dropping either would lose a capability
    the other cannot provide, so the fix is to spell them differently.

    Shape, per tag block:
        param_name_overrides:
          <command-name>:
            <spec-param-name>: <new-kebab-cli-name>
    """
    overrides = (folder_overrides or {}).get("param_name_overrides") or {}
    if not overrides:
        return
    by_command: dict[str, list] = {}
    for ep in endpoints:
        by_command.setdefault(ep.command_name, []).append(ep)

    for command_name, renames in overrides.items():
        eps = by_command.get(command_name)
        if not eps:
            raise ParamNameOverrideError(
                f"param_name_overrides names command {command_name!r}, which "
                f"this tag does not render. Known commands: "
                f"{sorted(by_command)}. Remove the stale entry or correct the "
                f"command name."
            )
        for spec_name, new_name in (renames or {}).items():
            if _safe_param_name(new_name) in _RESERVED_OUTPUT_PARAM_NAMES:
                raise ParamNameOverrideError(
                    f"param_name_overrides renames {spec_name!r} on "
                    f"{command_name!r} to {new_name!r}, which still collides "
                    f"with the --{new_name} option the renderer injects on "
                    f"every command. Choose a name outside "
                    f"{sorted(_RESERVED_OUTPUT_PARAM_NAMES)}."
                )
            matched = False
            for ep in eps:
                for qp in ep.query_params:
                    if qp.name == spec_name:
                        qp.python_name = new_name
                        matched = True
            if not matched:
                raise ParamNameOverrideError(
                    f"param_name_overrides targets query parameter "
                    f"{spec_name!r} on command {command_name!r}, which no "
                    f"longer declares it. Upstream may have renamed or "
                    f"dropped it — remove the stale entry."
                )


def _render_output_options(default_output: str = "json") -> list[str]:
    """The --output/--fields pair, identical on every generated command.

    --fields is deliberately not --query or --filter: those names are already
    taken by 2 and 65 spec-derived parameters respectively. --fields is free on
    every command, so this needs no per-command suppression. See the plan's
    "Why --fields and not --query".
    """
    choices = "id|table|json|text" if default_output == "id" else "table|json|text"
    return [
        f'    output: str = typer.Option("{default_output}", "--output", "-o", '
        f'help="Output format: {choices}"),',
        '    fields: str = typer.Option(None, "--fields", '
        'help="JMESPath expression selecting/filtering response fields, '
        'e.g. \\"[].{name:name,id:id}\\""),',
    ]


def _render_imports(include_org_id: bool = False, include_org_id_path: bool = False,
                    include_cc_url: bool = False, include_cc_org_id: bool = False,
                    include_fs_url: bool = False, include_fs_project_id: bool = False) -> str:
    lines = '''import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
'''
    config_imports = []
    if include_org_id:
        config_imports.append('get_org_id')
    if include_org_id_path:
        config_imports.append('resolve_org_id')
    if include_cc_url:
        config_imports.append('get_cc_base_url')
    if include_cc_org_id:
        config_imports.append('get_cc_org_id')
    if include_fs_url:
        config_imports.append('get_fs_base_url')
    if include_fs_project_id:
        config_imports.append('get_fs_project_id')
    if config_imports:
        lines += f'from wxcli.config import {", ".join(config_imports)}\n'
    return lines


def _render_url_expr(url_path: str, path_vars: list[str], method: str | None = None) -> str:
    # Module-level override takes precedence (set by render_command_file for CC spec)
    if _active_base_url_override:
        base = _active_base_url_override
    elif any(url_path.startswith(p) for p in ANALYTICS_PREFIXES):
        base = BASE_URL_ANALYTICS
    elif any(url_path.startswith(p) for p in NO_V1_PREFIXES):
        base = BASE_URL_NO_V1
    else:
        base = BASE_URL
    expr = f"{base}/{url_path}"
    bound = set()
    for var in path_vars:
        param = _path_var_to_param(var)
        expr = expr.replace("{" + var + "}", "{" + param + "}")
        bound.add(param)
    # The CC/FS base URL constants are themselves unresolved placeholders
    # ("{cc_base_url}"/"{fs_base_url}") — _render_path_inject assigns a
    # matching local before the URL line runs, so these are bound too.
    if _active_base_url_override == BASE_URL_CC:
        bound.add("cc_base_url")
    elif _active_base_url_override == BASE_URL_FS:
        bound.add("fs_base_url")
    unresolved = [name for name in _URL_PLACEHOLDER_RE.findall(expr) if name not in bound]
    if unresolved:
        raise UnboundUrlPlaceholderError(
            f"{method or '<unknown method>'} {url_path} renders a URL "
            f"f-string with unbound placeholder(s) {unresolved!r} — no path "
            f"variable, query param, body field, or renderer-injected local "
            f"binds {'that name' if len(unresolved) == 1 else 'those names'}. "
            f"This would raise NameError at call time, not compile time. "
            f"The spec's declared parameters for this operation are missing "
            f"the path parameter — add it (or borrow it from a sibling "
            f"operation on the same path) before regenerating."
        )
    return expr


def _render_error_handler(indent: str = "    ") -> str:
    # WebexError is not currently a subclass of httpx.HTTPError (verified:
    # issubclass(WebexError, httpx.HTTPError) is False), so these two except
    # clauses are disjoint and this order isn't load-bearing today — either
    # clause could run first with identical results. It's kept in this order
    # as a defensive convention: WebexError before the broader httpx.HTTPError
    # clause, so that if WebexError ever gains an httpx exception as a base
    # class, the more specific handler still wins instead of being shadowed.
    # Do not reorder or merge these clauses on the assumption that the order
    # is arbitrary.
    return f'''{indent}except WebexError as e:
{indent}    handle_rest_error(e)
{indent}except httpx.HTTPError as e:
{indent}    handle_network_error(e)'''


def _render_auto_inject_params(ep: Endpoint) -> list[str]:
    """Return lines to inject auto-inject params from config."""
    lines = []
    if "orgId" in getattr(ep, "auto_inject_params", []):
        lines.append("    org_id = get_org_id()")
        lines.append("    if org_id is not None:")
        lines.append('        params["orgId"] = org_id')
    return lines


def _render_path_inject(ep: Endpoint) -> list[str]:
    """Return lines to inject auto-inject PATH params from config (before URL line)."""
    lines = []
    if _active_base_url_override == BASE_URL_CC:
        lines.append("    cc_base_url = get_cc_base_url()")
    elif _active_base_url_override == BASE_URL_FS:
        lines.append("    fs_base_url = get_fs_base_url()")
    for var in getattr(ep, "auto_inject_path_params", []):
        param = _path_var_to_param(var)
        if var.lower() == "orgid":
            if _active_base_url_override == BASE_URL_CC:
                lines.append(f"    {param} = get_cc_org_id(api.session)")
            elif _active_base_url_override == BASE_URL_FS:
                lines.append(f"    {param} = get_cc_org_id(api.session)")
            else:
                lines.append(f"    {param} = resolve_org_id(api.session)")
        elif var.lower() == "projectid":
            if _active_base_url_override == BASE_URL_FS:
                lines.append(f"    {param} = get_fs_project_id()")
    return lines



def _skip_injected_path_var(var: str, ep: Endpoint) -> bool:
    """Return True if this path var is auto-injected and should not be a CLI argument."""
    return var in getattr(ep, "auto_inject_path_params", [])


PYTHON_KEYWORDS = {
    "list", "type", "id", "format", "input", "print", "open", "set", "map", "filter",
    "from", "import", "class", "def", "return", "yield", "for", "while", "if", "else",
    "elif", "try", "except", "finally", "with", "as", "pass", "break", "continue",
    "and", "or", "not", "in", "is", "lambda", "global", "nonlocal", "del", "raise",
    "assert", "True", "False", "None", "async", "await",
}

def _safe_func_name(command_name: str) -> str:
    import re
    name = command_name.replace("-", "_")
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if name in PYTHON_KEYWORDS:
        return f"cmd_{name}"
    return name

def _safe_param_name(name: str) -> str:
    snake = name.replace("-", "_")
    if snake in PYTHON_KEYWORDS:
        return f"{snake}_param"
    return snake

def _escape_help(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _success_message(ep, default: str) -> str:
    """Success message for an operation, following semantics rather than verb.

    Known issue #20: command_type comes from the HTTP method, so a PUT that only
    deletes would report "Updated." Where the parser identified real destructive
    semantics, that wins.
    """
    semantics = getattr(ep, "real_semantics", None)
    return DESTRUCTIVE_SEMANTICS[semantics] if semantics else default


# Finding 9: --output defaults to json on update/delete, but Webex PUT/DELETE
# mostly return 204 with no body — the common case — so the no-body branch
# used to always print the issue #20 prose line even when -o json (or -o
# text, or --fields) was requested, and piping to jq failed. table/id keep
# the exact prose message (see _success_message); json/text/--fields now get
# a small structured result instead, routed through emit() so --fields still
# applies. Its status word must follow the SAME semantics as the prose line
# (a delete-shaped PUT reports "deleted", not "updated") — hence reusing
# _success_message rather than hardcoding the verb per renderer.
def _status_word(message: str) -> str:
    """'Updated.' -> 'updated', 'Purged.' -> 'purged', etc."""
    return message.rstrip(".").lower()


def _no_body_result_expr(ep: Endpoint, default_message: str) -> str:
    """Python source for the {"status": ..., "id": ...} object emitted on
    update/delete when the API returned no body and the requested --output
    is a machine format (json/text) or --fields was given. `id` is included
    only when the endpoint has a path variable to report.
    """
    status = _status_word(_success_message(ep, default_message))
    if ep.path_vars:
        id_var = _path_var_to_param(ep.path_vars[-1])
        return f'{{"status": "{status}", "id": {id_var}}}'
    return f'{{"status": "{status}"}}'


def _render_docstring(ep) -> str:
    """Render docstring with a destructive-semantics note, a runnable example,
    and the --json-body skeleton.

    The trailing "." is now attached to the summary rather than to whatever
    ended up last. It used to be appended after the --json-body skeleton, so
    every skeleton ended `..."}'.` and every DESTRUCTIVE note ended `modify..`
    — harmless while the docstring's last line was prose, actively wrong now
    that it can end with a command an operator is meant to copy.

    Both example blocks open with Click's `\\b` no-rewrap marker, which only
    takes effect when it is the FIRST line of its paragraph (verified against
    click 8.3.2 in plain mode; measured: without it Click reflowed
    `Example:\\n  wxcli ...` onto one run-together line, and it had been
    breaking the --json-body skeleton mid-token — `"callBo\\nunceMaxRings"` —
    so the one piece of example text the CLI already had could not actually be
    pasted). Rich mode ignores `\\b` and still wraps; every agent invocation is
    non-TTY and therefore plain.
    """
    doc = " ".join((ep.name or "").split())
    if doc and not doc.endswith("."):
        doc += "."
    semantics = getattr(ep, "real_semantics", None)
    if semantics and summary_leading_verb(ep.name) not in DESTRUCTIVE_SEMANTICS:
        # The summary itself is misleading — "Modify Access Codes for a Person"
        # on a PUT that accepts only deleteCodes. Someone reading --help gets no
        # other hint that this is destructive, so say it before the example.
        doc += (
            f"\\n\\nDESTRUCTIVE: this {ep.method} only {semantics}s despite the "
            f"summary above. It cannot add or modify."
        )
    note = getattr(ep, "help_note", None)
    if note:
        doc += f"\\n\\nNOTE: {note}"
    example = _render_example(ep)
    if example:
        doc += f"\\n\\n\\b\\nExample: {example}"
    # Suppressed only when the example above already carries this exact blob —
    # printing the same JSON twice costs tokens on every read of the screen and
    # tells the reader nothing new. When the example carries the pruned body
    # the full one still earns its place: it is the only listing of the
    # optional fields.
    if ep.json_body_example and _example_json_body(ep) != ep.json_body_example:
        doc += f"\\n\\n\\b\\nExample --json-body: '{ep.json_body_example}'"
    for note in getattr(ep, "json_body_truncations", ()) or ():
        doc += f"\\n\\n\\b\\nNOTE: skeleton incomplete — {_escape_help(note)}"
    return f'    """{doc}"""'


def _command_decorator(ep) -> str:
    """The `@app.command(...)` line(s) for an endpoint — short_help, plus any alias.

    TWO separate defects live here.

    1. GROUP-SCREEN TRUNCATION. Click derives a command's group-screen summary
       with `make_default_short_help(help, max_length=45)` — a 45-CHARACTER cap,
       and it is Click's, not ours. `_clean_desc`'s 300-char cap never touches a
       command docstring (measured: 0 of 1,863 generated docstrings are
       truncated in the source; 220 *option* help strings are, which is a
       genuinely separate issue). So "Read the List of Call Queues with Customer
       Assist." — 49 chars — reached the group screen as "Read the List of Call
       Queues...". 579 of 1,666 summaries were cut this way, on the screen an
       agent reads to discover the CLI. Passing short_help explicitly bypasses
       Click's truncation entirely; it does not truncate what it is given.

    2. RENAMES NEED THEIR OLD NAME TO KEEP WORKING. When
       `command_name_overrides` renames a command, the original spec-derived
       name is emitted as a HIDDEN alias. Stacked decorators register one
       function under both names (verified on typer 0.24.1 / click 8.3.2): the
       new name shows in --help, the old one runs and stays invisible. Nothing
       anyone scripted against the old name breaks.
    """
    summary = " ".join((ep.name or "").split())
    if summary and not summary.endswith("."):
        summary += "."
    lines = []
    original = getattr(ep, "original_command_name", None)
    if original and original != ep.command_name:
        # Emitted FIRST so it is the outer decorator; Typer registers both and
        # the visible name is the one carrying short_help.
        lines.append(f'@app.command("{original}", hidden=True)')
    head = f'@app.command("{ep.command_name}"'
    if summary:
        head += f', short_help="{_escape_help(summary)}"'
    lines.append(head + ")")
    return "\n".join(lines)


def _dedup_enum_values(values: list[str]) -> list[str]:
    """Deduplicate case-insensitive enum values, preferring title-case."""
    seen: dict[str, str] = {}
    for v in values:
        key = v.lower()
        if key not in seen or (v[0].isupper() and not v.isupper()):
            seen[key] = v
    return list(seen.values())


def _clean_desc(text: str, max_desc: int = 300) -> str:
    """Collapse whitespace and truncate on a word boundary, never mid-word.

    Replaces the old blind `description[:60]` slice, which cut mid-word and
    routinely dropped the trailing "Default: X" clause — the single most useful
    fact in most field descriptions. The cap is generous enough to keep those
    trailing defaults; only genuinely long prose is trimmed, and then only at a
    word boundary with an ellipsis so nothing is chopped mid-token.
    """
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= max_desc:
        return collapsed
    return collapsed[:max_desc].rsplit(" ", 1)[0] + "..."


def _enum_help(field: EndpointField, max_desc: int = 300) -> str:
    """Build help text for a field, showing enum choices if available."""
    if field.enum_values:
        deduped = _dedup_enum_values(field.enum_values)
        if len(deduped) <= 12:
            return _escape_help(f"Choices: {', '.join(deduped)}")
        return _escape_help(f"{_clean_desc(field.description, max_desc)} (use --help for choices)")
    return _escape_help(_clean_desc(field.description, max_desc))


# ── Positional argument help ────────────────────────────────────────────────
#
# An argument used to render as `LOCATION_ID  locationId  [required]` — the
# argument's own name echoed back, on 1,499 of 1,508 arguments. Two facts the
# screen never carried are what an agent actually needs, and both are derivable
# from the spec:
#
#   1. WHAT THE VALUE LOOKS LIKE. 1,961 of 2,120 path params declare an
#      `example`. The Webex ones are real base64 Spark IDs that decode to
#      `ciscospark://us/<KIND>/<uuid>`, and <KIND> is the fact that matters —
#      it is what distinguishes a LOCATION id from a PEOPLE id, which is the
#      error an agent actually makes. Printing the base64 blob itself would
#      cost ~25 tokens to say the same thing less clearly.
#   2. WHICH COMMAND PRODUCES IT. See _producer_for below.

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                      r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_HEX24_RE = re.compile(r"^[0-9a-f]{24}$")
# A word-ish literal (`businessHours`) is worth echoing; an opaque hex/uuid
# sample is not — it teaches nothing the shape name does not already say.
_WORDISH_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{2,19}$")


def _spark_id_kind(example: str) -> str | None:
    """`Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OL2E4...` -> `LOCATION`.

    Spec examples are frequently truncated mid-uuid, so the tail may not be
    valid utf-8 or valid base64 padding — decode leniently and only trust the
    `ciscospark://` prefix and the kind segment, both of which land well
    before any truncation point.
    """
    if len(example) < 24 or not example.startswith("Y2lzY29zcGFyazovL"):
        return None
    try:
        decoded = base64.b64decode(example + "===", validate=False).decode(
            "utf-8", errors="ignore")
    except Exception:
        return None
    if not decoded.startswith("ciscospark://"):
        return None
    # "ciscospark://us/LOCATION/<uuid>" -> ['ciscospark:', '', 'us', 'LOCATION', ...]
    parts = decoded.split("/")
    kind = parts[3] if len(parts) > 3 else ""
    return kind if kind and kind.replace("_", "").isalnum() else None


def _value_shape(meta: dict) -> tuple[str | None, str | None]:
    """Describe a path argument's value: (human shape, literal example or None).

    The literal is returned separately because the runnable example line can
    only paste a value that is genuinely usable — an enum member or a word-ish
    constant is, an opaque id is not.
    """
    meta = meta or {}
    enum = meta.get("enum")
    if enum:
        values = _dedup_enum_values([str(v) for v in enum])
        if len(values) <= 6:
            return "one of: " + "|".join(values), values[0]
        return f"one of {len(values)} values (see the API docs)", values[0]
    example = meta.get("example")
    example = "" if example is None else str(example).strip()
    if example:
        kind = _spark_id_kind(example)
        if kind:
            return f"Webex {kind} id", None
        if _UUID_RE.match(example):
            return "UUID", None
        if _HEX24_RE.match(example):
            return "24-char hex id", None
        if _WORDISH_RE.match(example):
            return f"e.g. {example}", example
    if meta.get("format") == "date-time":
        return "ISO-8601 timestamp", None
    return None, None


# ── Which command produces this id ──────────────────────────────────────────
#
# Built once per process from every tracked spec, because the producing command
# is routinely in a DIFFERENT group than the command that consumes the id
# (`cq-playlists list` needs a playlist id from `announcement-playlists list`).
# Two resolution rules, in strict order — a wrong pointer is worse than none,
# so the exact rule always wins and the heuristic only fills gaps:
#
#   1. EXACT PARENT COLLECTION. For `{locationId}` in
#      `/telephony/config/locations/{locationId}/dectNetworks`, the parent
#      collection is `/telephony/config/locations`; whatever list command sits
#      at that exact URL is the producer BY CONSTRUCTION. 821 of 1,503.
#   2. SAME RESOURCE, SHALLOWER PATH. `/telephony/config/people` has no list
#      command of its own, but `/people` does, and `people` is a contiguous
#      tail of `telephony/config/people` — same resource, fewer scoping
#      segments. 258 of 1,503, dominated by people (115) and workspaces (86).
#
# Rule 2 needs a guard, and it was measured, not assumed: without one it also
# matched `.../schedules/{type}/{scheduleId}/events` -> `wxcli events list`
# (schedule events are not admin events) and
# `partner/tags/organizations/{orgId}/subscriptions` -> `cc-subscriptions
# list`. Both drop a segment that SCOPES some other resource somewhere in the
# API (`locations/{...}`, `organizations/{...}`), which is the tell: a dropped
# namespace (`telephony/config`, `hds`) is never a scoping segment. Requiring
# the candidate to be named `list*` drops a third bad class
# (`cc-flow export`). The remaining 312 arguments resolve to nothing and
# deliberately say nothing.
_TRACKED_SPECS = Path(__file__).resolve().parent.parent / "specs"

_producer_index: dict | None = None


def _path_literals(url_path: str) -> list[str]:
    return [s for s in url_path.split("/") if s and not s.startswith("{")]


def build_producer_index(specs_dir: Path | None = None) -> dict:
    """{url_path -> "group command"} for every list command, plus the lookup
    tables rule 2 needs. Imports generate_commands lazily: that module imports
    this one, and the override resolvers it owns (skip_tags, tag_merge,
    cli_name_overrides, tag_op_excludes) must not be duplicated here or the
    index would name groups the CLI does not actually ship.
    """
    from tools import generate_commands as gc
    from tools.openapi_parser import load_spec, get_tags, parse_tag
    from tools.postman_parser import load_overrides, apply_endpoint_overrides

    from tools.spec_sync import PREFERRED_ORDER

    specs_dir = specs_dir or _TRACKED_SPECS
    overrides = load_overrides(Path(__file__).resolve().parent / "field_overrides.yaml")
    by_path: dict[str, str] = {}
    by_tail: dict[str, list[tuple[list[str], str, str]]] = {}
    scoping: set[str] = set()

    # Same order spec_sync generates in, so that where two specs declare one
    # path the index names the same group the CLI actually ships it under.
    found = [p for p in specs_dir.glob("webex-*.json")
             if not p.name.endswith(".overlay.json")]
    ordered = [p for n in PREFERRED_ORDER for p in found if p.name == n]
    ordered += sorted(p for p in found if p.name not in PREFERRED_ORDER)

    for spec_path in ordered:
        name = spec_path.name
        spec = load_spec(spec_path)
        for path in spec.get("paths", {}):
            segs = path.strip("/").split("/")
            for i, seg in enumerate(segs[:-1]):
                if not seg.startswith("{") and segs[i + 1].startswith("{"):
                    scoping.add(seg)
        merge = gc.resolve_tag_merge(overrides.get("tag_merge"), name)
        if merge:
            gc.merge_tags(spec, merge)
        cli_ovr = gc.resolve_cli_name_overrides(overrides.get("cli_name_overrides"), name)
        excludes = gc.resolve_tag_op_excludes(overrides.get("tag_op_excludes"), name)
        skip = gc.resolve_skip_patterns(overrides.get("skip_tags"), name)
        for tag in get_tags(spec):
            if gc.should_skip_tag(tag, skip):
                continue
            endpoints, _ = parse_tag(
                tag, spec,
                omit_query_params=list(overrides.get("omit_query_params", [])),
                auto_inject_params=set(overrides.get("auto_inject_from_config", ["orgId"])),
                seen_operation_ids=set(), exclude_paths=excludes.get(tag),
            )
            # `_tag_ovr:*` keys are synthesized by generate_commands.main() at
            # runtime and are absent from the raw YAML this function loads, so
            # relying on them alone silently skipped every entry under
            # `tag_overrides:` — including all 26 command renames. The index
            # then pointed argument help at PRE-rename names (212 arguments
            # cited `location-settings list-1`, a name that no longer exists as
            # a visible command). Resolve the per-spec block the same way
            # main() does, and keep the other two forms as fallbacks.
            raw_tag_ovr = overrides.get("tag_overrides") or {}
            merged_tag_ovr = dict((raw_tag_ovr.get("_global") or {}).get(tag, {}))
            merged_tag_ovr.update((raw_tag_ovr.get(name) or {}).get(tag, {}))
            tag_ovr = (merged_tag_ovr
                       or overrides.get(f"_tag_ovr:{tag}")
                       or overrides.get(tag) or {})
            group = cli_ovr.get(tag) or folder_name_to_module(tag)[1]
            for ep in endpoints:
                apply_endpoint_overrides(ep, tag_ovr)
                if ep.command_type != "list":
                    continue
                by_path.setdefault(ep.url_path, f"{group} {ep.command_name}")
                literals = _path_literals(ep.url_path)
                if literals and ep.command_name.startswith("list"):
                    by_tail.setdefault(literals[-1], []).append(
                        (literals, ep.url_path, f"{group} {ep.command_name}"))
    for entries in by_tail.values():
        entries.sort(key=lambda e: (len(e[0]), len(e[1]), e[1]))
    return {"by_path": by_path, "by_tail": by_tail, "scoping": scoping}


def _subsequence_remainder(candidate: list[str], target: list[str]) -> list[str] | None:
    """Segments of `target` skipped over when matching `candidate` as an
    ordered subsequence ending on target's last segment, or None if it is not
    one. `[telephony, config, huntGroups]` inside
    `[telephony, config, locations, huntGroups]` skips `[locations]` — the
    same resource, one scoping level up. The skipped list is what the caller
    inspects to decide whether the skip was a namespace or a real resource.
    """
    if not candidate or not target or candidate[-1] != target[-1]:
        return None
    skipped: list[str] = []
    i = 0
    for seg in target:
        if i < len(candidate) and seg == candidate[i]:
            i += 1
        else:
            skipped.append(seg)
    return skipped if i == len(candidate) else None


def _producer_for(url_path: str, var: str, group: str) -> str | None:
    """`wxcli <group> <command>` that yields a value for `{var}`, or None."""
    global _producer_index
    if _producer_index is None:
        _producer_index = build_producer_index()
    segs = url_path.split("/")
    token = "{" + var + "}"
    if token not in segs:
        return None
    prefix = "/".join(segs[:segs.index(token)])
    if not prefix:
        return None
    hit = _producer_index["by_path"].get(prefix)
    if hit:
        return f"wxcli {hit}"
    literals = _path_literals(prefix)
    if not literals:
        return None
    for cand_literals, cand_path, cand in _producer_index["by_tail"].get(literals[-1], ()):
        if cand_path == prefix or len(cand_literals) > len(literals):
            continue
        dropped = _subsequence_remainder(cand_literals, literals)
        if dropped is None:
            continue
        if cand.split(" ", 1)[0] != group and any(
                d in _producer_index["scoping"] for d in dropped):
            continue
        return f"wxcli {cand}"
    return None


def _argument_help(ep: Endpoint, var: str, group: str | None = None) -> str:
    """Help text for one positional argument."""
    group = group if group is not None else _active_cli_name
    shape, _ = _value_shape((ep.path_var_meta or {}).get(var))
    producer = _producer_for(ep.url_path, var, group)
    parts = [p for p in (shape, f"from: {producer}" if producer else None) if p]
    # Nothing derivable: keep the spec's own name rather than an empty column.
    return _escape_help(", ".join(parts) if parts else var)


def _render_path_arguments(ep: Endpoint) -> list[str]:
    """The `typer.Argument(...)` lines for an endpoint's path variables.

    One helper for all six render paths, which carried six byte-identical
    copies of this loop before the help text became worth building.
    """
    lines = []
    for var in ep.path_vars:
        if _skip_injected_path_var(var, ep):
            continue
        param = _path_var_to_param(var)
        lines.append(
            f'    {param}: str = typer.Argument(help="{_argument_help(ep, var)}"),')
    return lines


def _flag_value(field: EndpointField) -> str:
    """The value token to show after a required flag in the example."""
    if field.enum_values:
        return _dedup_enum_values([str(v) for v in field.enum_values])[0]
    return _safe_param_name(field.python_name).upper()


def _flagless_required_body_fields(ep: Endpoint) -> list[EndpointField]:
    """Required body fields for which this command renders no flag.

    Two structural causes, both of which leave --json-body as the only way to
    supply the value:

    * object/array-typed fields are never rendered as flags (every render path
      skips `field_type in ("object", "array")`);
    * a field whose CLI name is already claimed by a path or query parameter is
      dropped as a flag to avoid a duplicate function argument (issue #19).
    """
    used_names = _used_param_names(ep)
    return [
        bf for bf in ep.body_fields
        if bf.required
        and (bf.field_type in ("object", "array")
             or _safe_param_name(bf.python_name) in used_names)
    ]


def _example_json_body(ep: Endpoint) -> str | None:
    """The body the runnable example must carry, or None if flags suffice.

    The MINIMAL skeleton, not the full one: the full one is what
    --generate-json-body prints and what the `Example --json-body:` line shows,
    and on a create it includes server-assigned fields (`id`, `version`,
    `createdTime`) that an agent pasting the example would send back.
    """
    if not _flagless_required_body_fields(ep):
        return None
    return (getattr(ep, "json_body_minimal_example", None)
            or ep.json_body_example)


def _render_example(ep: Endpoint) -> str | None:
    """One copy-pasteable invocation, or None when Usage already shows it.

    Emitted only for commands that take a positional or a required option.
    For anything else the example would read `wxcli people list` against a
    Usage line of `wxcli people list [OPTIONS]` — the same string, costing
    tokens on exactly the screens that already scored well.

    Opaque ids appear as their metavar rather than the spec's example value: a
    real base64 Spark id is ~90 characters, would not exist in the reader's org
    anyway, and the argument's own help now says which command produces one.
    Enum and word-ish values ARE pasted literally, because those are correct
    as-is.

    When a REQUIRED body field has no flag (see _flagless_required_body_fields)
    the flag list cannot express the call at all, so the example switches to
    `--json-body '<skeleton>'` and drops the scalar flags entirely. Dropping
    them is not cosmetic: the generated code is `if json_body: body =
    load_json_body(json_body) else: <build from flags>`, so an example showing
    both would teach that the flags still apply when in fact --json-body
    replaces the whole body. Keeping the skeleton inline rather than pointing at
    --generate-json-body is deliberate — an agent reads this line and issues the
    call in the same turn, and a pointer costs it a round trip.
    """
    tokens: list[str] = []
    for var in ep.path_vars:
        if _skip_injected_path_var(var, ep):
            continue
        _, literal = _value_shape((ep.path_var_meta or {}).get(var))
        tokens.append(literal or _path_var_to_param(var).upper())
    for qp in ep.query_params:
        if not qp.required:
            continue
        if ep.command_type == "list" and qp.name in _SUPPRESS_SPEC_PAGING_NAMES:
            continue
        tokens.append(f"--{qp.python_name} {_flag_value(qp)}")
    body_via_json = _example_json_body(ep)
    if not body_via_json:
        used_names = _used_param_names(ep)
        for bf in ep.body_fields:
            if not bf.required or bf.field_type in ("object", "array"):
                continue
            if _safe_param_name(bf.python_name) in used_names:
                continue
            if bf.field_type == "bool":
                tokens.append(f"--{bf.python_name}")
            else:
                tokens.append(f"--{bf.python_name} {_flag_value(bf)}")
    if not tokens and not body_via_json:
        return None
    head = " ".join(p for p in ("wxcli", _active_cli_name, ep.command_name) if p)
    line = _escape_help(" ".join([head, *tokens]))
    if body_via_json:
        # Appended after _escape_help so the skeleton reads in source exactly as
        # it does on the `Example --json-body:` line, which is unescaped too.
        line += f" --json-body '{body_via_json}'"
    return line


def _render_query_params(ep: Endpoint) -> tuple[list[str], list[str]]:
    """Render query param options and param-building lines for non-list commands.

    Returns (param_defs, param_build_lines). Skips rendering if no query params.
    """
    if not ep.query_params:
        return [], []
    param_defs = []
    for qp in ep.query_params:
        param = _safe_param_name(qp.python_name)
        help_text = _enum_help(qp)
        if qp.required:
            param_defs.append(f'    {param}: str = typer.Option(..., "--{qp.python_name}", help="{help_text}"),')
        else:
            param_defs.append(f'    {param}: str = typer.Option(None, "--{qp.python_name}", help="{help_text}"),')
    param_build = ["    params = {}"]
    for qp in ep.query_params:
        param = _safe_param_name(qp.python_name)
        param_build.append(f'    if {param} is not None:\n        params["{qp.name}"] = {param}')
    return param_defs, param_build


def _used_param_names(ep: Endpoint) -> set[str]:
    """CLI parameter names already claimed by path vars and query params.

    Body fields colliding with these are not rendered as flags (they would be
    duplicate function arguments — SyntaxError); --json-body still sets them.
    Seen first on CC Flows create-import: query param flowType + body field
    flowType in the same operation.
    """
    used = {_path_var_to_param(v) for v in ep.path_vars
            if not _skip_injected_path_var(v, ep)}
    used.update(_safe_param_name(qp.python_name) for qp in ep.query_params)
    return used


def _check_reserved_collisions(ep: Endpoint) -> None:
    """Raise ReservedParamCollisionError if a spec-derived parameter that
    would actually be rendered as a CLI flag collides with a CLI option the
    renderer injects unconditionally (see _RESERVED_OUTPUT_PARAM_NAMES).

    Spec-declared pagination names (limit/max/start/offset) are exempt —
    those are already handled by _SUPPRESS_SPEC_PAGING_NAMES, which folds
    them into the renderer's own --limit/--offset flags with equivalent
    semantics (see that constant's docstring for why --fields/--output
    can't use the same trick). Object/array-typed body fields are also
    exempt — they are never rendered as flags (--json-body only), and body
    fields already dropped as flags because they collide with a path/query
    param name (_used_param_names, issue #19) can't collide here either,
    since they never reach the flag-rendering step.
    """
    used_names = _used_param_names(ep)
    candidates: list[tuple[str, str, str]] = []
    for var in ep.path_vars:
        if _skip_injected_path_var(var, ep):
            continue
        candidates.append(("path parameter", var, _path_var_to_param(var)))
    for qp in ep.query_params:
        if qp.name in _SUPPRESS_SPEC_PAGING_NAMES:
            continue
        candidates.append(("query parameter", qp.name, _safe_param_name(qp.python_name)))
    for bf in ep.body_fields:
        if bf.field_type in ("object", "array"):
            continue
        python_name = _safe_param_name(bf.python_name)
        if python_name in used_names:
            continue
        candidates.append(("body field", bf.name, python_name))

    for kind, spec_name, python_name in candidates:
        if python_name in _RESERVED_OUTPUT_PARAM_NAMES:
            raise ReservedParamCollisionError(
                f"{ep.method} {ep.url_path} (command {ep.command_name!r}) "
                f"declares {kind} {spec_name!r}, whose CLI parameter name "
                f"({python_name!r}) collides with the --{python_name} option "
                f"the renderer adds to every command. Generating this "
                f"endpoint would produce a function with a duplicate "
                f"argument (SyntaxError at import time). Add a rename for "
                f"this parameter (field_overrides.yaml / cli_name_overrides) "
                f"before regenerating."
            )


# Types that render as one readable table cell. A dict or list renders as a
# Python repr — never useful in a column, and output.py's auto_columns skips
# them for the same reason.
_SCALAR_RESPONSE_TYPES = {"string", "integer", "number", "boolean"}

# Most preferred human-readable label first. Ordered by what a Webex list
# response actually carries — measured across every list endpoint in the nine
# tracked specs, not guessed.
_LABEL_FIELDS = (
    "name", "displayName", "fileName", "title", "meetingTopic", "topic",
    "label", "scheduleName", "code", "firstName", "email", "phoneNumber",
    "extension",
)

# Identical on every row of an org-scoped response, so it buys no information
# for the width it costs. Still used if the item has nothing else.
_LOW_VALUE_FIELDS = {"orgId"}

# Rendered upper-case in a header rather than title-cased.
_HEADER_ACRONYMS = {
    "id", "url", "uri", "esn", "sip", "pstn", "mwi", "dn", "mac", "ip", "api",
    "cdr", "dect", "uuid", "sso", "dns", "cscf", "ecbn",
}

_MAX_DEFAULT_COLUMNS = 5


def _column_header(name: str) -> str:
    """camelCase response field -> Title Case column header."""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).split()
    return " ".join(
        w.upper() if w.lower() in _HEADER_ACRONYMS else w[:1].upper() + w[1:]
        for w in words
    )


def _derive_default_columns(ep: Endpoint) -> list[tuple[str, str]] | None:
    """Default table columns from the endpoint's own 200 item schema.

    The hardcoded ("ID", "id"), ("Name", "name") pair this replaces is wrong
    for most Webex list endpoints: they return phoneNumber, clusterId,
    displayName, trunkType — and no `id` or `name` at all. The command still
    exited 0 and printed a table, just a blank one (or, when every column
    resolved empty, tripped output.py's auto_columns fallback and ballooned to
    40+ columns). Measured on the tree before this change: 224 of 513 list
    commands named at least one field the API does not return, and all 224 had
    inherited this pair.

    Returns None when no schema resolves, leaving that fallback in place.
    """
    fields = ep.response_item_fields.get(ep.response_list_key or "items")
    if not fields:
        return None
    names = [f.name for f in fields if f.field_type in _SCALAR_RESPONSE_TYPES]
    if not names:
        return None

    chosen: list[str] = []
    if "id" in names:
        chosen.append("id")
    else:
        ident = next((n for n in names
                      if n.endswith("Id") and n not in _LOW_VALUE_FIELDS), None)
        if ident:
            chosen.append(ident)

    label = next((n for n in _LABEL_FIELDS if n in names), None)
    if label is None:
        label = next((n for n in names if n.endswith("Name")), None)
    if label and label not in chosen:
        chosen.append(label)

    for pool in (
        [n for n in names if n not in _LOW_VALUE_FIELDS],
        names,  # second pass: a low-value field beats no column at all
    ):
        for name in pool:
            if len(chosen) >= _MAX_DEFAULT_COLUMNS:
                break
            if name not in chosen:
                chosen.append(name)
        if chosen:
            break
    return [(_column_header(n), n) for n in chosen[:_MAX_DEFAULT_COLUMNS]]


def _render_list_command(ep: Endpoint, folder_overrides: dict) -> str:
    _check_reserved_collisions(ep)
    func_name = _safe_func_name(ep.command_name)
    folder_overrides = folder_overrides or {}
    params = []

    params.extend(_render_path_arguments(ep))

    # Render only non-paging query params as CLI options. Spec-declared paging
    # names (max, start, offset, limit) are suppressed here — the unified
    # --limit/--offset flags below take their place and map into params under
    # whichever spec name the endpoint uses.
    for qp in ep.query_params:
        if qp.name in _SUPPRESS_SPEC_PAGING_NAMES:
            continue
        param = _safe_param_name(qp.python_name)
        help_text = _enum_help(qp)
        if qp.required:
            params.append(f'    {param}: str = typer.Option(..., "--{qp.python_name}", help="{help_text}"),')
        else:
            params.append(f'    {param}: str = typer.Option(None, "--{qp.python_name}", help="{help_text}"),')

    # Determine which spec paging names the endpoint declares, so --limit and
    # --offset map into the right params key. Prefer spec-declared "limit"/
    # "offset" when present; otherwise fall back to "max"/"start" (the Webex
    # default naming used by most cloud-calling list endpoints).
    spec_param_names = {qp.name for qp in ep.query_params}
    has_spec_max = "max" in spec_param_names
    has_spec_limit = "limit" in spec_param_names
    has_spec_start = "start" in spec_param_names
    has_spec_offset = "offset" in spec_param_names

    limit_param_key = "limit" if has_spec_limit else "max"
    offset_param_key = "offset" if has_spec_offset else "start"

    params.extend(_render_output_options("table"))
    params.append('    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),')
    params.append('    offset: int = typer.Option(0, "--offset", help="Start offset"),')
    # Uniform on EVERY list command, including the ones the spec calls
    # unpaginated. An option present on most commands but not all teaches a
    # rule that breaks unpredictably, which costs an agent a failed call plus a
    # --help round trip each time — the same reasoning that closed the
    # --output gap. On an unpaginated endpoint it is simply a no-op.
    params.append('    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),')
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars, method=ep.method)

    param_build = []
    param_build.append("    params = {}")
    for qp in ep.query_params:
        if qp.name in _SUPPRESS_SPEC_PAGING_NAMES:
            continue
        param = _safe_param_name(qp.python_name)
        param_build.append(f'    if {param} is not None:\n        params["{qp.name}"] = {param}')
    param_build.append(f'    if limit > 0:\n        params["{limit_param_key}"] = limit')
    param_build.append(f'    if offset > 0:\n        params["{offset_param_key}"] = offset')

    list_key = ep.response_list_key or "items"

    # Per-command columns take precedence over folder-level list.table_columns
    per_cmd = folder_overrides.get("table_columns", {}).get(ep.command_name)
    if per_cmd:
        col_str = repr([(c[0], c[1]) for c in per_cmd])
    else:
        columns = folder_overrides.get("list", {}).get("table_columns", None)
        if columns:
            col_str = repr([(c[0], c[1]) for c in columns])
        else:
            derived = _derive_default_columns(ep)
            col_str = repr(derived) if derived else '[("ID", "id"), ("Name", "name")]'

    if ep.paginates:
        # Paginating endpoint: use follow_pagination for complete results when
        # --limit=0 (the default). When --limit>0, fall back to a single
        # rest_get with the limit already encoded in params[limit_param_key]
        # (set up above in param_build).
        if has_spec_max or has_spec_limit:
            # Endpoint has its own paging param — don't override page size.
            max_inject = []
        else:
            # No spec paging param — inject max=1000 per page for efficiency.
            max_inject = [
                f'            if "max" not in params:',
                f'                params["max"] = 1000',
            ]
        fetch_block = [
            "    try:",
            f'        if limit > 0 and not all_pages:',
            f'            result = api.session.rest_get(url, params=params)',
            f'            result = result or {{}}',
            f'            items = result.get("{list_key}", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])',
            f'        else:',
            *max_inject,
            f'            items = list(api.session.follow_pagination(url=url, params=params, item_key="{list_key}"))',
        ]
    elif ep.pagination_style in ("link", "page", "scim"):
        # Pages, but the spec never declared a Link header, so `paginates` is
        # False and the DEFAULT stays exactly what it was: one fetch. Only --all
        # walks. This is the 210 — 109 link-shaped (max/start, header
        # undeclared), 96 Contact Center page/pageSize, 5 SCIM.
        walker = {"link": "follow_pagination",
                  "page": "follow_page_param",
                  "scim": "follow_scim"}[ep.pagination_style]
        fetch_block = [
            "    result = None",
            "    try:",
            "        if all_pages:",
            # Assigns `result`, not `items`: this branch shares the non-paginating
            # tail below, which re-derives items from result and would otherwise
            # overwrite them. A list falls through that expression unchanged.
            f'            result = list(api.session.{walker}(url=url, params=params, item_key="{list_key}"))',
            "        else:",
            "            result = api.session.rest_get(url, params=params)",
        ]
    else:
        # Non-paginating endpoint: single call (all results in one response).
        # --all is accepted and inert, so the flag means the same thing on every
        # list command rather than existing on some and not others.
        fetch_block = [
            "    result = None",
            "    try:",
            "        result = api.session.rest_get(url, params=params)",
        ]

    if ep.paginates:
        lines = [
            _command_decorator(ep),
            f"def {func_name}(",
            *params,
            "):",
            _render_docstring(ep),
            "    api = get_api(debug=debug)",
            *_render_path_inject(ep),
            f'    url = f"{url_expr}"',
            *param_build,
            *_render_auto_inject_params(ep),
            *fetch_block,
            _render_error_handler("    "),
            f"    emit(items, output=output, fields=fields, columns={col_str}, limit=limit)",
        ]
    else:
        lines = [
            _command_decorator(ep),
            f"def {func_name}(",
            *params,
            "):",
            _render_docstring(ep),
            "    api = get_api(debug=debug)",
            *_render_path_inject(ep),
            f'    url = f"{url_expr}"',
            *param_build,
            *_render_auto_inject_params(ep),
            *fetch_block,
            _render_error_handler("    "),
            f'    result = result or []',
        f'    items = result.get("{list_key}", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])',
            f"    emit(items, output=output, fields=fields, columns={col_str}, limit=limit)",
        ]
    return "\n".join(lines)


def _render_show_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    _check_reserved_collisions(ep)
    func_name = _safe_func_name(ep.command_name)
    params = []
    params.extend(_render_path_arguments(ep))
    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)
    params.extend(_render_output_options("json"))
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars, method=ep.method)

    # Show/settings-get commands: support --output for table rendering. The
    # dict-in-table auto-detect behaviour is preserved inside emit() (Task 1's
    # dict branch).
    show_output = [
        "    emit(result, output=output, fields=fields)",
    ]

    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)

    if has_params:
        param_init = qp_build if qp_build else ["    params = {}"]
        lines = [
            _command_decorator(ep),
            f"def {func_name}(",
            *params,
            "):",
            _render_docstring(ep),
            "    api = get_api(debug=debug)",
            *_render_path_inject(ep),
            f'    url = f"{url_expr}"',
            *param_init,
            *auto_inject,
            "    try:",
            "        result = api.session.rest_get(url, params=params)",
            _render_error_handler("    "),
            *show_output,
        ]
    else:
        lines = [
            _command_decorator(ep),
            f"def {func_name}(",
            *params,
            "):",
            _render_docstring(ep),
            "    api = get_api(debug=debug)",
            *_render_path_inject(ep),
            f'    url = f"{url_expr}"',
            "    try:",
            "        result = api.session.rest_get(url)",
            _render_error_handler("    "),
            *show_output,
        ]
    return "\n".join(lines)


def _render_create_id_extraction(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    # A destructive POST creates no resource, so there is no id to report and
    # "Created:" would be a lie — report what actually happened instead.
    # The output == "id" branch keeps its per-endpoint id/message logic exactly
    # as before; every other format routes through emit() (Task 3 decision:
    # emit's id branch is data.get("id", ""), which can't handle a non-"id"
    # response_id_key or the destructive-POST message).
    if getattr(ep, "real_semantics", None):
        return "\n".join([
            '    if output == "id":',
            f'        typer.echo("{_success_message(ep, "Created.")}")',
            '    else:',
            '        emit(result, output=output, fields=fields)',
        ])
    # Prefer schema-derived response_id_key, fall back to folder overrides
    id_key = ep.response_id_key or (folder_overrides or {}).get("create", {}).get("id_key")
    lines = ['    if output == "id":']
    if id_key and id_key != "id":
        lines.extend([
            f'        if isinstance(result, dict) and "{id_key}" in result:',
            f'            typer.echo(f"Created: {{result[\'{id_key}\']}}")',
            f'        elif isinstance(result, dict) and "id" in result:',
            f'            typer.echo(f"Created: {{result[\'id\']}}")',
            f'        elif not result or result == {{}}:',
            f'            typer.echo("Created.")',
            f'        else:',
            f'            print_json(result)',
        ])
    else:
        lines.extend([
            '        if isinstance(result, dict) and "id" in result:',
            '            typer.echo(f"Created: {result[\'id\']}")',
            '        elif not result or result == {}:',
            '            typer.echo("Created.")',
            '        else:',
            '            print_json(result)',
        ])
    lines.extend([
        '    else:',
        '        emit(result, output=output, fields=fields)',
    ])
    return "\n".join(lines)


def _render_create_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    _check_reserved_collisions(ep)
    func_name = _safe_func_name(ep.command_name)
    folder_overrides = folder_overrides or {}
    params = []
    params.extend(_render_path_arguments(ep))

    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)

    # All body fields are optional at the CLI level (--json-body bypasses them).
    # Required fields are validated at runtime when --json-body is not used.
    used_names = _used_param_names(ep)
    required_body_field_names = []
    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type == "object" or bf.field_type == "array":
            continue
        if param in used_names:
            continue
        help_text = _enum_help(bf)
        if bf.required:
            required_body_field_names.append(bf.name)
            help_text = f"(required) {help_text}" if help_text else "(required)"
        if bf.field_type == "bool":
            params.append(f'    {param}: bool = typer.Option(None, "--{bf.python_name}/--no-{bf.python_name}", help="{help_text}"),')
        else:
            params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')

    if ep.json_body_example:
        params.append('    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),')
    params.append('    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),')
    params.extend(_render_output_options("id"))
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars, method=ep.method)

    generate_json_body_check = []
    if ep.json_body_example:
        generate_json_body_check = [
            "    if generate_json_body:",
            f"        typer.echo(json.dumps(json.loads(_BODY_SKELETON_{func_name.upper()}), indent=2))",
            "        raise typer.Exit(0)",
        ]

    body_build = ["    if json_body:", "        body = load_json_body(json_body)", "    else:", "        body = {}"]
    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type in ("object", "array"):
            if bf.default is not None:
                body_build.append(f"        body.setdefault({bf.name!r}, {bf.default!r})")
            continue
        if param in used_names:
            continue
        if bf.field_type == "bool":
            body_build.append(f'        if {param} is not None:\n            body["{bf.name}"] = {param}')
        else:
            body_build.append(f'        if {param} is not None:\n            body["{bf.name}"] = {param}')
    # Runtime validation: check required fields when --json-body is not used
    if required_body_field_names:
        req_list = repr(required_body_field_names)
        body_build.append(f'        _missing = [f for f in {req_list} if f not in body or body[f] is None]')
        body_build.append('        if _missing:')
        body_build.append('            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)')
        body_build.append('            raise typer.Exit(1)')

    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    post_call = "result = api.session.rest_post(url, json=body)" if not has_params else "result = api.session.rest_post(url, json=body, params=params)"

    # Render body_defaults: inject required nested defaults after body is built
    # (applies to both --json-body and flag-built bodies)
    body_default_lines: list[str] = []
    bd = (folder_overrides or {}).get("body_defaults", {}).get(ep.command_name, {})
    for key, default_val in bd.items():
        body_default_lines.append(f'    body.setdefault({key!r}, {default_val!r})')

    lines = [
        _command_decorator(ep),
        f"def {func_name}(",
        *params,
        "):",
        _render_docstring(ep),
        *generate_json_body_check,
        "    api = get_api(debug=debug)",
        *_render_path_inject(ep),
        f'    url = f"{url_expr}"',
        *qp_build,
        *auto_inject,
        *body_build,
        *body_default_lines,
        "    try:",
        f"        {post_call}",
        _render_error_handler("    "),
        _render_create_id_extraction(ep, folder_overrides),
    ]
    return "\n".join(lines)


def _render_update_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    _check_reserved_collisions(ep)
    func_name = _safe_func_name(ep.command_name)
    is_json_patch = ep.content_type == "application/json-patch+json"
    params = []
    params.extend(_render_path_arguments(ep))

    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)
    used_names = _used_param_names(ep)

    if is_json_patch:
        # JSON Patch endpoints: --op, --path, --value flags that build a patch array
        for bf in ep.body_fields:
            param = _safe_param_name(bf.python_name)
            if bf.field_type in ("object", "array") or param in used_names:
                continue
            help_text = _enum_help(bf)
            params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')
        params.append('    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),')
    else:
        for bf in ep.body_fields:
            param = _safe_param_name(bf.python_name)
            if bf.field_type in ("object", "array") or param in used_names:
                continue
            help_text = _enum_help(bf)
            if bf.field_type == "bool":
                params.append(f'    {param}: bool = typer.Option(None, "--{bf.python_name}/--no-{bf.python_name}", help="{help_text}"),')
            else:
                params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')

    if ep.json_body_example:
        params.append('    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),')
    params.append('    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),')
    params.extend(_render_output_options("json"))
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars, method=ep.method)

    generate_json_body_check = []
    if ep.json_body_example:
        generate_json_body_check = [
            "    if generate_json_body:",
            f"        typer.echo(json.dumps(json.loads(_BODY_SKELETON_{func_name.upper()}), indent=2))",
            "        raise typer.Exit(0)",
        ]

    if is_json_patch:
        # JSON Patch: --json-body passes through as-is; flags build [{op, path, value}]
        body_build = [
            "    if json_body:",
            "        body = load_json_body(json_body)",
            "    else:",
            "        patch_op = {}",
        ]
        for bf in ep.body_fields:
            param = _safe_param_name(bf.python_name)
            if bf.field_type in ("object", "array") or param in used_names:
                continue
            body_build.append(f'        if {param} is not None:\n            patch_op["{bf.name}"] = {param}')
        body_build.extend([
            '        if value is not None:',
            '            try:',
            '                patch_op["value"] = json.loads(value)',
            '            except json.JSONDecodeError:',
            '                patch_op["value"] = value',
            '        body = [patch_op]',
        ])
    else:
        body_build = ["    if json_body:", "        body = load_json_body(json_body)", "    else:", "        body = {}"]
        for bf in ep.body_fields:
            param = _safe_param_name(bf.python_name)
            if bf.field_type in ("object", "array") or param in used_names:
                continue
            body_build.append(f'        if {param} is not None:\n            body["{bf.name}"] = {param}')

    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    rest_method = "rest_patch" if ep.method == "PATCH" else "rest_put"
    ct_kwarg = ', content_type="application/json-patch+json"' if is_json_patch and rest_method == "rest_patch" else ""
    method_call = f"result = api.session.{rest_method}(url, json=body{ct_kwarg})" if not has_params else f"result = api.session.{rest_method}(url, json=body, params=params{ct_kwarg})"

    lines = [
        _command_decorator(ep),
        f"def {func_name}(",
        *params,
        "):",
        _render_docstring(ep),
        *generate_json_body_check,
        "    api = get_api(debug=debug)",
        *_render_path_inject(ep),
        f'    url = f"{url_expr}"',
        *qp_build,
        *auto_inject,
        *body_build,
        "    try:",
        f"        {method_call}",
        _render_error_handler("    "),
        "    if result:",
        "        emit(result, output=output, fields=fields)",
        '    elif output in ("table", "id") and not fields:',
        f'        typer.echo(f"{_success_message(ep, "Updated.")}")',
        "    else:",
        f"        emit({_no_body_result_expr(ep, 'Updated.')}, output=output, fields=fields)",
    ]
    return "\n".join(lines)


def _url_terminal_segment(url_path: str) -> str:
    """The last non-empty segment of a spec path template, e.g.
    'workspaces/{workspaceId}/features/outgoingPermission/accessCodes' -> 'accessCodes'."""
    return url_path.rstrip("/").split("/")[-1]


def _humanize_path_segment(segment: str) -> str:
    """'accessCodes' / 'dial-number' -> 'Access Codes' / 'Dial Number'.

    Best-effort label for a literal URL segment so a confirm prompt can name
    the sub-resource actually being deleted, when that resource is not
    identified by any single path variable.
    """
    spaced = segment.replace("-", " ").replace("_", " ")
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", spaced)
    words = [w for w in spaced.split() if w]
    return " ".join(w[:1].upper() + w[1:] for w in words) if words else segment


def _delete_confirm_subject(ep: Endpoint, id_var: str) -> str:
    """The f-string body for a delete command's confirmation prompt.

    Known issue #7: the prompt used to always name the last path variable
    (`Delete {id}?`), which is only true when that id IS the resource being
    deleted. Many deletes are scoped BY an id but delete a named sub-resource
    UNDER it (e.g. a workspace's access codes) — naming the id there asks the
    operator to confirm deleting the wrong thing. Only claim the id itself is
    the target when the URL's terminal segment actually is that path
    variable; otherwise name the real terminal resource, honestly, from the
    URL. Where no resource noun can be derived (empty/odd segment), fall back
    to a generic prompt rather than a specific but unjustified one.
    """
    last_declared = ep.path_vars[-1]
    terminal = _url_terminal_segment(ep.url_path)
    if terminal == "{" + last_declared + "}":
        return f"Delete {{{id_var}}}?"
    if terminal.lower() in DESTRUCTIVE_SEMANTICS:
        # The terminal segment is itself an action verb (e.g. .../unassign),
        # not a resource noun -- "Delete Unassign ...?" would misdescribe it.
        verb = terminal[:1].upper() + terminal[1:]
        return f"{verb} {{{id_var}}}?"
    label = _humanize_path_segment(terminal)
    if not label:
        return f"Delete this resource (scoped by {{{id_var}}})?"
    return f"Delete {label} for {{{id_var}}}?"


def _render_delete_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    _check_reserved_collisions(ep)
    func_name = _safe_func_name(ep.command_name)
    params = []
    params.extend(_render_path_arguments(ep))
    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)

    # 10 Webex DELETE operations carry a request body, and on 5 of them the body
    # is what SCOPES the delete (`supervisorIds`, `phoneNumbers`, `items`,
    # `backgroundImages`, `handsetIds`). This branch used to skip bodies
    # entirely, which made those 5 commands inert: verified live against
    # /telephony/config/supervisors — 400, errorCode 25024, "Required request
    # body is missing". They could never have worked.
    used_names = _used_param_names(ep)
    has_body = bool(ep.body_fields)
    # The flag and its early-exit block below must share this exact condition —
    # never test ep.json_body_example alone here. json_body_example is normally
    # only set when body_fields is non-empty (openapi_parser only populates it
    # for body-bearing ops), but the renderer must not assume its own caller's
    # invariant: an Endpoint built with json_body_example set and body_fields=[]
    # (e.g. directly in a test) previously rendered `if generate_json_body:`
    # with no such parameter declared — a NameError at runtime.
    emits_generate_flag = has_body and bool(ep.json_body_example)
    if has_body:
        for bf in ep.body_fields:
            param = _safe_param_name(bf.python_name)
            if bf.field_type in ("object", "array") or param in used_names:
                continue  # arrays/objects can only be expressed via --json-body
            help_text = _enum_help(bf)
            if bf.field_type == "bool":
                params.append(f'    {param}: bool = typer.Option(None, "--{bf.python_name}/--no-{bf.python_name}", help="{help_text}"),')
            else:
                params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')
        if emits_generate_flag:
            params.append('    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),')
        params.append('    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),')

    has_spec_force = any(qp.name == "force" for qp in ep.query_params)
    if not has_spec_force:
        params.append('    force: bool = typer.Option(False, "--force", help="Skip confirmation"),')
    params.extend(_render_output_options("json"))
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars, method=ep.method)

    if ep.path_vars:
        id_var = _path_var_to_param(ep.path_vars[-1])
        subject = _delete_confirm_subject(ep, id_var)
        confirm_line = f'        typer.confirm(f"{subject}", abort=True)'
        echo_line = f'        typer.echo(f"Deleted: {{{id_var}}}")'
    else:
        confirm_line = '        typer.confirm("Delete this resource?", abort=True)'
        echo_line = '        typer.echo("Deleted.")'

    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]

    generate_json_body_check = []
    if emits_generate_flag:
        generate_json_body_check = [
            "    if generate_json_body:",
            f"        typer.echo(json.dumps(json.loads(_BODY_SKELETON_{func_name.upper()}), indent=2))",
            "        raise typer.Exit(0)",
        ]

    body_build: list[str] = []
    if has_body:
        body_build = ["    if json_body:", "        body = load_json_body(json_body)",
                      "    else:", "        body = {}"]
        for bf in ep.body_fields:
            param = _safe_param_name(bf.python_name)
            if bf.field_type in ("object", "array") or param in used_names:
                continue
            body_build.append(f'        if {param} is not None:\n            body["{bf.name}"] = {param}')
        required = [bf.name for bf in ep.body_fields if bf.required]
        if required:
            # Fail HERE, not at the API. A scoped delete whose scope is missing
            # is the one shape that must never reach the wire: these endpoints
            # gate delete-everything behind an explicit `deleteAll`, so a body
            # that merely omits the targets is a mistake, not a request.
            body_build.extend([
                f"    missing = [f for f in {required!r} if f not in body]",
                "    if missing:",
                '        typer.echo(f"Error: required body field(s) missing: {\', \'.join(missing)}. '
                'Pass them via --json-body — this delete needs to know what to delete.", err=True)',
                "        raise typer.Exit(1)",
            ])

    # `body or None` preserves the no-body wire format when nothing was supplied,
    # so the 5 metadata-body deletes (reason/comment on recordings) behave exactly
    # as they do today rather than newly sending `{}`.
    if has_body:
        delete_call = ("result = api.session.rest_delete(url, json=body or None)" if not has_params
                       else "result = api.session.rest_delete(url, json=body or None, params=params)")
    else:
        delete_call = "result = api.session.rest_delete(url)" if not has_params else "result = api.session.rest_delete(url, params=params)"

    lines = [
        _command_decorator(ep),
        f"def {func_name}(",
        *params,
        "):",
        _render_docstring(ep),
        *generate_json_body_check,
        "    api = get_api(debug=debug)",
        *_render_path_inject(ep),
        "    if not force:",
        confirm_line,
        f'    url = f"{url_expr}"',
        *qp_build,
        *auto_inject,
        *body_build,
        "    try:",
        f"        {delete_call}",
        _render_error_handler("    "),
        "    if result:",
        "        emit(result, output=output, fields=fields)",
        '    elif output in ("table", "id") and not fields:',
        echo_line,
        "    else:",
        f"        emit({_no_body_result_expr(ep, 'Deleted.')}, output=output, fields=fields)",
    ]
    return "\n".join(lines)


def _render_action_command(ep: Endpoint, folder_overrides: dict | None = None) -> str:
    _check_reserved_collisions(ep)
    func_name = _safe_func_name(ep.command_name)
    params = []
    params.extend(_render_path_arguments(ep))

    qp_defs, qp_build = _render_query_params(ep)
    params.extend(qp_defs)
    used_names = _used_param_names(ep)

    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type in ("object", "array") or param in used_names:
            continue
        help_text = _enum_help(bf)
        params.append(f'    {param}: str = typer.Option(None, "--{bf.python_name}", help="{help_text}"),')

    if ep.json_body_example:
        params.append('    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),')
    params.append('    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),')
    params.extend(_render_output_options("json"))
    params.append('    debug: bool = typer.Option(False, "--debug"),')

    url_expr = _render_url_expr(ep.url_path, ep.path_vars, method=ep.method)

    generate_json_body_check = []
    if ep.json_body_example:
        generate_json_body_check = [
            "    if generate_json_body:",
            f"        typer.echo(json.dumps(json.loads(_BODY_SKELETON_{func_name.upper()}), indent=2))",
            "        raise typer.Exit(0)",
        ]

    body_build = ["    if json_body:", "        body = load_json_body(json_body)", "    else:", "        body = {}"]
    for bf in ep.body_fields:
        param = _safe_param_name(bf.python_name)
        if bf.field_type in ("object", "array") or param in used_names:
            continue
        body_build.append(f'        if {param} is not None:\n            body["{bf.name}"] = {param}')

    has_params = bool(qp_build) or bool(_render_auto_inject_params(ep))
    auto_inject = _render_auto_inject_params(ep)
    if not qp_build and has_params:
        qp_build = ["    params = {}"]
    post_call = "result = api.session.rest_post(url, json=body)" if not has_params else "result = api.session.rest_post(url, json=body, params=params)"

    lines = [
        _command_decorator(ep),
        f"def {func_name}(",
        *params,
        "):",
        _render_docstring(ep),
        *generate_json_body_check,
        "    api = get_api(debug=debug)",
        *_render_path_inject(ep),
        f'    url = f"{url_expr}"',
        *qp_build,
        *auto_inject,
        *body_build,
        "    try:",
        f"        {post_call}",
        _render_error_handler("    "),
        "    emit(result, output=output, fields=fields)",
    ]
    return "\n".join(lines)


RENDERERS = {
    "list": _render_list_command,
    "show": _render_show_command,
    "create": _render_create_command,
    "update": _render_update_command,
    "delete": _render_delete_command,
    "settings-get": _render_show_command,
    "settings-update": _render_update_command,
    "action": _render_action_command,
}


def _infer_missing_path_vars(endpoints: list[Endpoint]) -> None:
    """Backfill a spec bug where one operation's `parameters` omits a path
    variable that its own URL template still requires, while a sibling
    operation on the identical url_path declares it correctly.

    Verified live: webex-meetings.json's PUT
    /admin/meeting/config/trackingCodes/{trackingCodeId} has an empty
    `parameters` array — so `ep.path_vars` was `[]` — while the GET and
    DELETE on that exact same path both declare `trackingCodeId`. Rather
    than special-casing that one endpoint, borrow the var from whichever
    sibling shares its url_path; if no sibling has it either, path_vars is
    left as the spec declared it, and `_render_url_expr`'s
    UnboundUrlPlaceholderError guard fires instead of shipping a runtime
    NameError. Mutates each Endpoint's path_vars in place.
    """
    vars_by_path: dict[str, set[str]] = {}
    for ep in endpoints:
        vars_by_path.setdefault(ep.url_path, set()).update(ep.path_vars)
    for ep in endpoints:
        for name in _URL_PLACEHOLDER_RE.findall(ep.url_path):
            if name not in ep.path_vars and name in vars_by_path.get(ep.url_path, ()):
                ep.path_vars.append(name)


class CommandHelpNoteError(Exception):
    """A `command_help_notes` entry names a command this tag does not render.

    Same contract as `verb_semantics_ack` and `param_name_overrides`: the entry
    is re-validated on every generation, so a note cannot quietly outlive the
    command it was written for and go on reassuring people about nothing.
    """


def _apply_command_help_notes(endpoints: list[Endpoint], folder_overrides: dict) -> None:
    """Attach a hand-written caveat to a command's --help.

    For the case the spec cannot express: a command whose response is
    technically accurate but will be READ as a stronger guarantee than it is.
    The first user is `location-settings safe-delete-check`, which answers
    "can I delete this?" with UNBLOCKED on a location the API then refuses to
    delete — every dependency count it can see really is 0, and the blocker
    (the location is Webex-Calling-enabled) is not a dependency it can see.
    """
    notes = (folder_overrides or {}).get("command_help_notes") or {}
    if not notes:
        return
    rendered = {ep.command_name for ep in endpoints}
    unknown = sorted(set(notes) - rendered)
    if unknown:
        raise CommandHelpNoteError(
            f"command_help_notes names command(s) this tag does not render: "
            f"{', '.join(unknown)}. Rendered here: {', '.join(sorted(rendered))}"
        )
    for ep in endpoints:
        if ep.command_name in notes:
            ep.help_note = " ".join(str(notes[ep.command_name]).split())


def render_command_file(
    folder_name: str, endpoints: list[Endpoint], folder_overrides: dict,
    base_url_override: str | None = None,
) -> str:
    _infer_missing_path_vars(endpoints)
    _apply_command_help_notes(endpoints, folder_overrides)
    _, cli_name = folder_name_to_module(folder_name)
    needs_org_id_query = any(
        "orgId" in getattr(ep, "auto_inject_params", [])
        for ep in endpoints
    )
    needs_org_id_path = any(
        any(v.lower() == "orgid" for v in getattr(ep, "auto_inject_path_params", []))
        for ep in endpoints
    )
    needs_org_id = needs_org_id_query or needs_org_id_path
    global _active_base_url_override, _active_cli_name
    _active_base_url_override = base_url_override
    _active_cli_name = cli_name
    needs_cc_url = base_url_override == BASE_URL_CC
    needs_fs_url = base_url_override == BASE_URL_FS
    needs_fs_project_id = needs_fs_url and any(
        "projectId" in getattr(ep, "auto_inject_path_params", [])
        for ep in endpoints
    )
    needs_cc_org_id = (needs_cc_url or needs_fs_url) and needs_org_id
    # Detect product area from CLI name prefix
    if cli_name.startswith("cc-"):
        product = "Webex Contact Center"
    elif cli_name.startswith("fs-"):
        product = "WxCC Flow Store"
    elif cli_name.startswith("meeting"):
        product = "Webex Meetings"
    else:
        product = "Webex Calling"
    sections = [
        _render_imports(include_org_id=needs_org_id_query, include_org_id_path=needs_org_id_path,
                        include_cc_url=needs_cc_url, include_cc_org_id=needs_cc_org_id,
                        include_fs_url=needs_fs_url, include_fs_project_id=needs_fs_project_id),
        f'app = typer.Typer(help="Manage {product} {cli_name}.")\n',
    ]

    # Before any renderer runs: a rename must be visible to every render path
    # and to _check_reserved_collisions alike.
    _apply_param_name_overrides(endpoints, folder_overrides)

    for ep in endpoints:
        renderer = RENDERERS.get(ep.command_type)
        if renderer is None:
            sections.append(f"# SKIPPED: {ep.name} — unknown command type {ep.command_type}\n")
            continue
        if ep.json_body_example:
            func_name = _safe_func_name(ep.command_name)
            sections.append(f"_BODY_SKELETON_{func_name.upper()} = {ep.json_body_example!r}")
        sections.append(renderer(ep, folder_overrides))
        sections.append("")

    return "\n\n".join(sections) + "\n"
