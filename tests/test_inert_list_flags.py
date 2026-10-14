"""Hidden, inert `--all` / `--limit` / `--offset` on single-object `list*` reads.

ADR-14 re-renders a `list*`-named GET whose 200 is ONE object as a `show`
(names kept), which would have removed the three paging flags from ~111
commands. Root CLAUDE.md promises `--all` on every list command, "uniform by
design": an agent or script that passes `--all` to a `list*` command must not
get "No such option". Decision (Adam, 2026-10-13): those commands keep the
three flags as HIDDEN options that do nothing — absent from `--help`, never
sent as query params, no effect on output.

Every case renders from synthetic fixtures (an inline spec or a hand-built
Endpoint), so an upstream spec change cannot fail it. The behavioural cases
exec the RENDERED module with stubbed `wxcli` imports — wxcli itself is never
imported, so no generated command can reach the network.
"""

import typer
from typer.testing import CliRunner

from tools.command_renderer import render_command_file
from tools.openapi_parser import parse_tag
from tools.postman_parser import Endpoint, EndpointField


_BOOL = {"type": "boolean"}
_ROWS = {"type": "array", "items": {"type": "object",
                                    "properties": {"id": {"type": "string"}}}}
# A settings object that carries one array: ADR-14's shape
# (`call-queue list-night-service`).
_NIGHT = {"type": "object", "properties": {
    "nightServiceEnabled": _BOOL, "audioFiles": _ROWS}}
_THING = {"type": "object", "properties": {"id": {"type": "string"},
                                           "name": {"type": "string"}}}


def _get(op_id, summary, schema, params=None, headers=None):
    resp = {"description": "ok",
            "content": {"application/json": {"schema": schema}}}
    if headers:
        resp["headers"] = headers
    return {"tags": ["Probe"], "operationId": op_id, "summary": summary,
            "parameters": params or [], "responses": {"200": resp}}


def _path_param(name):
    return {"name": name, "in": "path", "required": True,
            "schema": {"type": "string"}}


def _probe_spec():
    """One tag rendering four commands:
    - `list`               single-object read (settings object + one array)
    - `list-items`         paged collection (declares `max`)
    - `show`               ordinary single-resource GET
    - `create`             POST
    """
    return {"paths": {
        "/queues/{queueId}/nightService": {"get": _get(
            "getNight", "Get Night Service", _NIGHT,
            params=[_path_param("queueId")])},
        "/queues/{queueId}/items": {"get": _get(
            "listItems", "List Items",
            {"type": "object", "properties": {"items": _ROWS}},
            params=[_path_param("queueId"),
                    {"name": "max", "in": "query",
                     "schema": {"type": "integer"}}])},
        "/queues/{queueId}/items/{itemId}": {"get": _get(
            "getItem", "Get Item", _THING,
            params=[_path_param("queueId"), _path_param("itemId")])},
        "/queues/{queueId}/things": {"post": {
            "tags": ["Probe"], "operationId": "createThing",
            "summary": "Create Thing",
            "parameters": [_path_param("queueId")],
            "requestBody": {"content": {"application/json": {
                "schema": {"type": "object",
                           "properties": {"name": {"type": "string"}}}}}},
            "responses": {"201": {"description": "ok", "content": {
                "application/json": {"schema": _THING}}}}}},
    }}


def _render_probe():
    endpoints, _ = parse_tag("Probe", _probe_spec())
    by_name = {ep.command_name: ep for ep in endpoints}
    return by_name, render_command_file("Probe", endpoints, {})


def _block(code: str, command: str) -> str:
    start = code.index(f'@app.command("{command}"')
    nxt = code.find("\n@app.command", start + 1)
    return code[start: nxt if nxt != -1 else len(code)]


class _Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def rest_get(self, url, params=None):
        self.calls.append((url, params))
        return self.response


def _load_app(code: str, response):
    """Exec the rendered module with its `wxcli` imports replaced by stubs."""
    session = _Session(response)
    emitted = []

    class _Api:
        pass

    api = _Api()
    api.session = session

    class _WebexError(Exception):
        pass

    def _emit(value, **kwargs):
        emitted.append(value)
        typer.echo(repr(value))

    namespace = {
        "get_api": lambda debug=False: api,
        "WebexError": _WebexError,
        "handle_rest_error": lambda e: (_ for _ in ()).throw(e),
        "handle_network_error": lambda e: (_ for _ in ()).throw(e),
        "print_table": lambda *a, **k: None,
        "print_json": lambda *a, **k: None,
        "emit": _emit,
        "load_json_body": lambda *a, **k: {},
        "verify_write": lambda *a, **k: None,
    }
    stripped = "\n".join(line for line in code.splitlines()
                         if not line.startswith("from wxcli"))
    exec(compile(stripped, "<rendered>", "exec"), namespace)
    return namespace["app"], session, emitted


class TestRenderedSource:
    def test_single_object_list_declares_the_three_flags_hidden(self):
        by_name, code = _render_probe()
        assert by_name["list"].command_type == "show"   # ADR-14 reclassified
        block = _block(code, "list")
        assert 'typer.Option(False, "--all", hidden=True' in block
        assert 'typer.Option(0, "--limit", hidden=True' in block
        assert 'typer.Option(0, "--offset", hidden=True' in block

    def test_hidden_flags_are_never_sent(self):
        _, code = _render_probe()
        block = _block(code, "list")
        assert "params[" not in block
        for name in ("all_pages", "limit", "offset"):
            # declared once, used nowhere else in the body
            assert block.count(f"{name}:") == 1
            assert f"if {name}" not in block and f"{name} >" not in block

    def test_paged_list_keeps_its_visible_flags(self):
        by_name, code = _render_probe()
        assert by_name["list-items"].command_type == "list"
        block = _block(code, "list-items")
        assert '"--all", help=' in block and '"--limit", help=' in block
        assert "hidden=True" not in block

    def test_non_list_commands_get_no_paging_flags(self):
        _, code = _render_probe()
        for command in ("show", "create"):
            block = _block(code, command)
            for flag in ('"--all"', '"--limit"', '"--offset"'):
                assert flag not in block, (command, flag)

    def test_renamed_command_keyed_on_visible_name_not_alias(self):
        """`cc-flow export` keeps a hidden `list-export` alias; it is not a
        list command, so no paging flags."""
        ep = Endpoint(
            name="Export", method="GET", url_path="flows/{flowId}:export",
            path_vars=["flowId"], query_params=[], body_fields=[],
            command_type="show", command_name="export",
            raw_path=["flows", "{flowId}:export"], response_list_key=None,
            response_id_key=None, deprecated=False, json_body_example=None)
        ep.original_command_name = "list-export"
        code = render_command_file("Probe", [ep], {})
        assert '"--all"' not in code and '"--limit"' not in code

    def test_spec_declared_limit_is_not_shadowed(self):
        """A `list*` show whose spec declares its own `limit` keeps that one
        visible flag; no second `--limit` (two Click options sharing a flag
        string shadow silently)."""
        field = EndpointField(name="limit", python_name="limit",
                              field_type="number", description="Cap",
                              required=False, default=None, enum_values=None)
        ep = Endpoint(
            name="List Thing", method="GET", url_path="thing",
            path_vars=[], query_params=[field], body_fields=[],
            command_type="show", command_name="list-thing",
            raw_path=["thing"], response_list_key=None, response_id_key=None,
            deprecated=False, json_body_example=None)
        code = render_command_file("Probe", [ep], {})
        assert code.count('"--limit"') == 1
        assert '"--limit", hidden=True' not in code
        assert '"--all", hidden=True' in code
        assert '"--offset", hidden=True' in code
        compile(code, "<rendered>", "exec")


class TestRuntimeBehaviour:
    _RESPONSE = {"nightServiceEnabled": True, "audioFiles": []}

    def test_help_does_not_list_them(self):
        _, code = _render_probe()
        app, _, _ = _load_app(code, self._RESPONSE)
        result = CliRunner().invoke(app, ["list", "--help"])
        assert result.exit_code == 0, result.output
        assert "--output" in result.output          # control: help rendered
        for flag in ("--all", "--limit", "--offset"):
            assert flag not in result.output

    def test_flags_accepted_and_change_nothing(self):
        _, code = _render_probe()
        app, session, emitted = _load_app(code, self._RESPONSE)
        runner = CliRunner()
        plain = runner.invoke(app, ["list", "Q1"])
        flagged = runner.invoke(
            app, ["list", "Q1", "--all", "--limit", "5", "--offset", "3"])
        assert plain.exit_code == 0, plain.output
        assert flagged.exit_code == 0, flagged.output
        assert plain.output == flagged.output
        assert session.calls[0] == session.calls[1]
        assert emitted == [self._RESPONSE, self._RESPONSE]

    def test_show_still_rejects_all(self):
        _, code = _render_probe()
        app, _, _ = _load_app(code, {"id": "x"})
        result = CliRunner().invoke(app, ["show", "Q1", "I1", "--all"])
        assert result.exit_code == 2
        assert "No such option" in result.output
