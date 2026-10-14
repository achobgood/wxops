"""A request body the spec declares as a query parameter is rendered as the body.

The Contact Center spec declares the DTO of six writes (POST/PUT of
`/organization/{orgid}/team[/{id}]`, `/skill-profile[/{id}]`,
`/agent-profile[/{id}]`) as a REQUIRED QUERY PARAMETER whose schema is an
object, with no `requestBody`. Live 2026-10-13 the DTO is the request body:
`cc-team create` required `--team-dto` even beside `--json-body` (exit 2,
"Missing option '--team-dto'"), sent it as `?teamDTO=%7B…`, and offered no
`--generate-json-body`. Passing the real JSON only via `--team-dto` gave 400
because the body was empty; `--team-dto x --json-body '{…}'` worked.

ADR-16: on a POST/PUT/PATCH with no requestBody and exactly ONE query parameter
whose schema is an object (not `style: deepObject`), the parser moves that
schema into the request body. The query parameter is not rendered, not
required and not sent; `--json-body` and `--generate-json-body` work; the body
flags come from the DTO. A hidden, ignored `--<param>` option is kept so
existing scripts (`--team-dto x --json-body …`) do not get "No such option".

Every case renders from synthetic fixtures, so an upstream spec change cannot
fail it. The behavioural cases exec the RENDERED module with stubbed `wxcli`
imports — wxcli itself is never imported, so no command can reach the network.
"""

import json

import typer
from typer.testing import CliRunner

from tools.command_renderer import render_command_file
from tools.openapi_parser import parse_tag


_THING_DTO = {
    "type": "object",
    "required": ["name", "active"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "active": {"type": "boolean"},
        "kind": {"type": "string", "enum": ["AGENT", "CAPACITY"]},
        "userIds": {"type": "array", "items": {"type": "string"}},
    },
}
_COMPONENTS = {"schemas": {"ThingDTO": _THING_DTO}}
_RESP = {"200": {"description": "ok", "content": {"application/json": {
    "schema": {"$ref": "#/components/schemas/ThingDTO"}}}}}


def _path_param(name):
    return {"name": name, "in": "path", "required": True,
            "schema": {"type": "string"}}


def _dto_query(name="thingDTO", schema=None, **extra):
    return {"name": name, "in": "query", "required": True,
            "schema": schema or {"$ref": "#/components/schemas/ThingDTO"},
            **extra}


def _write(op_id, summary, params, body=None):
    op = {"tags": ["Probe"], "operationId": op_id, "summary": summary,
          "parameters": params, "responses": _RESP}
    if body is not None:
        op["requestBody"] = {"content": {"application/json": {"schema": body}}}
    return op


def _spec(post_params=None, put_params=None, post_body=None):
    """POST /org/{orgid}/thing and PUT /org/{orgid}/thing/{id}, the DTO in
    the query unless overridden."""
    return {
        "components": _COMPONENTS,
        "paths": {
            "/org/{orgid}/thing": {"post": _write(
                "createThing", "Create a new Thing",
                post_params if post_params is not None
                else [_path_param("orgid"), _dto_query()], post_body)},
            "/org/{orgid}/thing/{id}": {"put": _write(
                "updateThing", "Update specific Thing by ID",
                put_params if put_params is not None
                else [_path_param("orgid"), _path_param("id"), _dto_query()])},
        },
    }


def _endpoints(spec):
    endpoints, _ = parse_tag("Probe", spec)
    return {ep.command_name: ep for ep in endpoints}


def _render(spec):
    endpoints, _ = parse_tag("Probe", spec)
    return render_command_file("Probe", endpoints, {})


def _block(code: str, command: str) -> str:
    start = code.index(f'@app.command("{command}"')
    nxt = code.find("\n@app.command", start + 1)
    return code[start: nxt if nxt != -1 else len(code)]


# ------------------------------------------------------------------ parser

class TestParser:
    def test_query_dto_becomes_the_request_body(self):
        eps = _endpoints(_spec())
        for name in ("create", "update"):
            ep = eps[name]
            assert [qp.name for qp in ep.query_params] == [], name
            assert {bf.name for bf in ep.body_fields} == set(
                _THING_DTO["properties"]), name
            required = {bf.name for bf in ep.body_fields if bf.required}
            assert required == {"name", "active"}, name
            assert ep.json_body_example, name
            assert json.loads(ep.json_body_example)["name"] == "..."
            assert ep.lifted_query_params == ["thing-dto"], name

    def test_inline_object_schema_is_lifted_too(self):
        inline = {"type": "object", "properties": {"name": {"type": "string"}}}
        eps = _endpoints(_spec(post_params=[_path_param("orgid"),
                                            _dto_query(schema=inline)]))
        assert eps["create"].query_params == []
        assert [bf.name for bf in eps["create"].body_fields] == ["name"]

    def test_scalar_query_params_stay_in_the_query(self):
        eps = _endpoints(_spec(post_params=[
            _path_param("orgid"), _dto_query(),
            {"name": "dryRun", "in": "query", "schema": {"type": "boolean"}}]))
        ep = eps["create"]
        assert [qp.name for qp in ep.query_params] == ["dryRun"]
        assert ep.lifted_query_params == ["thing-dto"]

    def test_op_with_a_request_body_is_untouched(self):
        """An object query param beside a real body is not the defect."""
        body = {"type": "object", "properties": {"other": {"type": "string"}}}
        eps = _endpoints(_spec(post_body=body))
        ep = eps["create"]
        assert [qp.name for qp in ep.query_params] == ["thingDTO"]
        assert [bf.name for bf in ep.body_fields] == ["other"]
        assert ep.lifted_query_params == []

    def test_two_object_query_params_are_not_guessed(self):
        """Only one schema can be the body; with two the parser leaves both in
        the query and drift check 32 sends it to a human."""
        eps = _endpoints(_spec(post_params=[
            _path_param("orgid"), _dto_query(), _dto_query(name="otherDTO")]))
        ep = eps["create"]
        assert {qp.name for qp in ep.query_params} == {"thingDTO", "otherDTO"}
        assert ep.body_fields == [] and ep.lifted_query_params == []

    def test_deep_object_query_param_is_a_real_query_param(self):
        eps = _endpoints(_spec(post_params=[
            _path_param("orgid"), _dto_query(style="deepObject")]))
        assert [qp.name for qp in eps["create"].query_params] == ["thingDTO"]
        assert eps["create"].lifted_query_params == []

    def test_get_with_object_query_param_is_untouched(self):
        spec = {"components": _COMPONENTS, "paths": {"/org/{orgid}/thing": {
            "get": {"tags": ["Probe"], "operationId": "getThing",
                    "summary": "Get Thing",
                    "parameters": [_path_param("orgid"), _dto_query()],
                    "responses": _RESP}}}}
        (ep,) = parse_tag("Probe", spec)[0]
        assert [qp.name for qp in ep.query_params] == ["thingDTO"]
        assert ep.body_fields == [] and ep.lifted_query_params == []

    def test_path_level_query_dto_is_lifted(self):
        """OpenAPI path-item parameters apply to the operation too."""
        spec = _spec(post_params=[_path_param("orgid")])
        spec["paths"]["/org/{orgid}/thing"]["parameters"] = [_dto_query()]
        ep = _endpoints(spec)["create"]
        assert ep.query_params == [] and ep.lifted_query_params == ["thing-dto"]

    def test_spec_is_not_mutated(self):
        spec = _spec()
        before = json.dumps(spec, sort_keys=True)
        _endpoints(spec)
        assert json.dumps(spec, sort_keys=True) == before


# -------------------------------------------------------- rendered source

class TestRenderedSource:
    def test_dto_is_never_sent_as_a_query_param(self):
        code = _render(_spec())
        for command in ("create", "update"):
            block = _block(code, command)
            assert 'params["thingDTO"]' not in block, command
            assert "?thingDTO" not in block, command

    def test_hidden_inert_option_is_kept(self):
        code = _render(_spec())
        for command in ("create", "update"):
            block = _block(code, command)
            assert ('thing_dto: str = typer.Option(None, "--thing-dto", '
                    'hidden=True') in block, command
            assert 'typer.Option(..., "--thing-dto"' not in block, command
            # declared once, read nowhere
            assert block.count("thing_dto") == 1, command

    def test_generate_json_body_and_body_flags_are_rendered(self):
        code = _render(_spec())
        create = _block(code, "create")
        assert '"--generate-json-body"' in create
        assert '"--name"' in create and '"--active/--no-active"' in create
        update = _block(code, "update")
        assert '"--generate-json-body"' in update
        assert '"--name"' in update


# --------------------------------------------------------------- behaviour

class _Session:
    def __init__(self):
        self.calls = []

    def _record(self, method, url, json=None, params=None, **kw):
        self.calls.append((method, url, json, params))
        return {"id": "new-id"}

    def rest_post(self, url, json=None, params=None, **kw):
        return self._record("POST", url, json, params)

    def rest_put(self, url, json=None, params=None, **kw):
        return self._record("PUT", url, json, params)


def _load_app(code: str):
    session = _Session()

    class _Api:
        pass

    api = _Api()
    api.session = session

    class _WebexError(Exception):
        pass

    namespace = {
        "get_api": lambda debug=False: api,
        "WebexError": _WebexError,
        "handle_rest_error": lambda e: (_ for _ in ()).throw(e),
        "handle_network_error": lambda e: (_ for _ in ()).throw(e),
        "print_table": lambda *a, **k: None,
        "print_json": lambda v, *a, **k: typer.echo(repr(v)),
        "emit": lambda v, **k: typer.echo(repr(v)),
        "load_json_body": lambda raw: json.loads(raw),
        "verify_write": lambda *a, **k: None,
        "get_org_id": lambda *a, **k: "ORG",
    }
    stripped = "\n".join(line for line in code.splitlines()
                         if not line.startswith("from wxcli"))
    exec(compile(stripped, "<rendered>", "exec"), namespace)
    return namespace["app"], session


_BODY = '{"name": "T1", "active": true}'


class TestBehaviour:
    def test_bare_json_body_create_runs_and_sends_the_body(self):
        app, session = _load_app(_render(_spec()))
        r = CliRunner().invoke(app, ["create", "ORG", "--json-body", _BODY])
        assert r.exit_code == 0, r.output
        ((method, url, body, params),) = session.calls
        assert method == "POST" and body == {"name": "T1", "active": True}
        assert not params or "thingDTO" not in params

    def test_old_workaround_still_runs_and_ignores_the_dto_flag(self):
        app, session = _load_app(_render(_spec()))
        r = CliRunner().invoke(
            app, ["create", "ORG", "--thing-dto", "x", "--json-body", _BODY])
        assert r.exit_code == 0, r.output
        ((_, _, body, params),) = session.calls
        assert body == {"name": "T1", "active": True}
        assert not params or "thingDTO" not in params

    def test_update_with_bare_json_body(self):
        app, session = _load_app(_render(_spec()))
        r = CliRunner().invoke(app, ["update", "ORG", "ID1", "--json-body",
                                     '{"id": "ID1", "name": "T2", "active": true}'])
        assert r.exit_code == 0, r.output
        ((method, url, body, params),) = session.calls
        assert method == "PUT" and url.endswith("/thing/ID1")
        assert body["id"] == "ID1"
        assert not params or "thingDTO" not in params

    def test_generate_json_body_prints_the_dto_skeleton(self):
        app, session = _load_app(_render(_spec()))
        r = CliRunner().invoke(app, ["create", "ORG", "--generate-json-body"])
        assert r.exit_code == 0, r.output
        skel = json.loads(r.output)
        assert {"name", "active", "kind"} <= set(skel)
        assert session.calls == []

    def test_help_hides_the_dto_flag(self):
        app, _ = _load_app(_render(_spec()))
        r = CliRunner().invoke(app, ["create", "--help"],
                               env={"COLUMNS": "200", "TERM": "dumb"})
        assert r.exit_code == 0, r.output
        assert "--thing-dto" not in r.output
        assert "--json-body" in r.output

    def test_flags_without_required_fields_fail_as_on_every_create(self):
        """Required DTO fields are checked at runtime when --json-body is not
        used (exit 1), never as required Click options (exit 2)."""
        app, session = _load_app(_render(_spec()))
        r = CliRunner().invoke(app, ["create", "ORG", "--name", "T1"])
        assert r.exit_code == 1, r.output
        assert "Missing required fields: active" in r.output
        assert session.calls == []

    def test_flags_build_the_body(self):
        app, session = _load_app(_render(_spec()))
        r = CliRunner().invoke(app, ["create", "ORG", "--name", "T1",
                                     "--active"])
        assert r.exit_code == 0, r.output
        ((_, _, body, params),) = session.calls
        assert body == {"name": "T1", "active": True}
