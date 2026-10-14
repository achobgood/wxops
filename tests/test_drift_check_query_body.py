"""Drift gate check 32: a request body the spec declares as a query parameter.

The Contact Center spec declares the DTO of six writes (POST/PUT of
`/organization/{orgid}/team[/{id}]`, `/skill-profile[/{id}]`,
`/agent-profile[/{id}]`) as a required QUERY parameter whose schema is an
object, with no `requestBody`. Rendered literally, `cc-team create` demanded
`--team-dto` even beside `--json-body` (exit 2), sent the DTO as
`?teamDTO=%7B…`, sent an empty body, and had no `--generate-json-body`
(live 2026-10-13: 400 "siteId: should not be null or blank").

A POST/PUT/PATCH block fires when a spec op it renders declares no
requestBody and a query parameter whose schema is an object (a `$ref` to an
object schema, or `type: object`; `style: deepObject` excluded) — the spec put
the body in the query — AND the block still treats it as a query param: it
writes `params["<name>"]`, declares the option required, sends no body, or
offers no `--generate-json-body` for a schema with properties.

Every fire case has a paired no-fire case, written so the check can fail it.
Synthetic specs and blocks only — nothing here reads today's upstream content.
"""

import json

import pytest

from tools import drift_check


# The block shape the generator emitted before ADR-16 (cc_team.py at 5f6550b).
PRE_FIX = '''
@app.command("create", short_help="Create a new Thing.")
def create(
    thing_dto: str = typer.Option(..., "--thing-dto", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Thing."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/org/{orgid}/thing"
    params = {}
    if thing_dto is not None:
        params["thingDTO"] = thing_dto
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
'''

# The block shape after ADR-16: body flags, skeleton, hidden inert option.
FIXED = '''
_BODY_SKELETON_CREATE = '{"name":"..."}'

@app.command("create", short_help="Create a new Thing.")
def create(
    name: str = typer.Option(None, "--name", help="(required)"),
    thing_dto: str = typer.Option(None, "--thing-dto", hidden=True, help="Accepted and ignored."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Thing."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/org/{orgid}/thing"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
'''

PATH = "/org/{orgid}/thing"
DTO = {"type": "object", "required": ["name"],
       "properties": {"name": {"type": "string"}}}


def _param(name="thingDTO", schema=None, where="query", **extra):
    return {"name": name, "in": where, "required": True,
            "schema": schema if schema is not None
            else {"$ref": "#/components/schemas/ThingDTO"}, **extra}


def _spec(params=None, method="post", body=None, path=PATH,
          path_params=None):
    op = {"tags": ["Probe"], "summary": "Create a new Thing",
          "parameters": [{"name": "orgid", "in": "path", "required": True,
                          "schema": {"type": "string"}}]
          + (params if params is not None else [_param()]),
          "responses": {"200": {"description": "ok"}}}
    if body is not None:
        op["requestBody"] = {"content": {"application/json": {
            "schema": body}}}
    item = {method: op}
    if path_params:
        item["parameters"] = path_params
    return {"components": {"schemas": {"ThingDTO": DTO}},
            "paths": {path: item}}


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(module_src, *spec_list):
        (cmds / "zz_probe.py").write_text(module_src)
        for i, spec in enumerate(spec_list):
            name = "webex-probe.json" if i == 0 else f"webex-probe{i}.json"
            (specs / name).write_text(json.dumps(spec))
        return drift_check.check_query_body_params(
            commands_dir=cmds, specs_dir=specs)

    return run


# ------------------------------------------------------- the 2026-10-13 bug

def test_prefix_block_fires_with_every_defect(tree):
    findings = tree(PRE_FIX, _spec())
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["group"] == "zz-probe" and f["command"] == "create"
    assert f["op"] == f"POST {PATH}"
    assert f["param"] == "thingDTO"
    assert set(f["defects"]) == {"sent as query param", "required option",
                                 "no --generate-json-body"}
    assert drift_check.CHECK_EXAMINED["32"] == {"examined": 1, "skipped": 0}


def test_fixed_block_is_clean(tree):
    assert tree(FIXED, _spec()) == []
    assert drift_check.CHECK_EXAMINED["32"]["examined"] == 1


@pytest.mark.parametrize("defect,mutate", [
    ("sent as query param", lambda s: s.replace(
        "    try:\n", '    params = {}\n    params["thingDTO"] = thing_dto\n'
        "    try:\n", 1)),
    ("required option", lambda s: s.replace(
        'typer.Option(None, "--thing-dto", hidden=True',
        'typer.Option(..., "--thing-dto", hidden=True')),
    ("no --generate-json-body", lambda s: s.replace(
        '"--generate-json-body"', '"--gen-body"')),
    ("no request body", lambda s: s.replace(
        "rest_post(url, json=body)", "rest_post(url)")),
])
def test_each_defect_alone_fires(tree, defect, mutate):
    block = mutate(FIXED)
    assert block != FIXED
    findings = tree(block, _spec())
    assert [f["defects"] for f in findings] == [[defect]], findings


# ------------------------------------------------------------ the spec side

def test_inline_object_schema_counts(tree):
    inline = {"type": "object", "properties": {"name": {"type": "string"}}}
    assert len(tree(PRE_FIX, _spec(params=[_param(schema=inline)]))) == 1


def test_path_level_query_param_counts(tree):
    assert len(tree(PRE_FIX, _spec(params=[], path_params=[_param()]))) == 1


def test_scalar_query_param_is_not_the_class(tree):
    """A required scalar query param on a POST is ordinary."""
    scalar = PRE_FIX
    assert tree(scalar, _spec(params=[_param(schema={"type": "string"})])) == []
    assert drift_check.CHECK_EXAMINED["32"]["examined"] == 1


def test_ref_to_a_scalar_schema_is_not_the_class(tree):
    spec = _spec()
    spec["components"]["schemas"]["ThingDTO"] = {"type": "string",
                                                 "enum": ["A"]}
    assert tree(PRE_FIX, spec) == []


def test_op_with_a_request_body_is_not_the_class(tree):
    """An object query param beside a real body: the body is not in the
    query, so there is nothing to lift."""
    assert tree(PRE_FIX, _spec(body=DTO)) == []


def test_deep_object_is_a_real_query_param(tree):
    assert tree(PRE_FIX, _spec(params=[_param(style="deepObject")])) == []


def test_header_object_param_is_not_the_class(tree):
    assert tree(PRE_FIX, _spec(params=[_param(where="header")])) == []


def test_two_object_params_fire_when_sent(tree):
    """The parser lifts only a single object param; with two it leaves both
    in the query, and this check sends that to a human."""
    findings = tree(PRE_FIX, _spec(params=[_param(), _param(name="otherDTO")]))
    assert len(findings) == 1
    assert findings[0]["param"] == "otherDTO, thingDTO"


def test_get_blocks_are_not_examined(tree):
    get_block = PRE_FIX.replace("rest_post(url, json=body, params=params)",
                                "rest_get(url, params=params)")
    findings = tree(get_block, _spec(method="get"))
    assert findings and "error" in findings[0]          # BLIND: examined 0
    assert drift_check.CHECK_EXAMINED["32"]["examined"] == 0


def test_put_and_patch_are_examined(tree):
    for method, call in (("put", "rest_put"), ("patch", "rest_patch")):
        block = PRE_FIX.replace("rest_post", call)
        findings = tree(block, _spec(method=method))
        assert len(findings) == 1, (method, findings)
        assert findings[0]["op"] == f"{method.upper()} {PATH}"


def test_block_with_no_spec_op_is_skipped_and_counted(tree):
    findings = tree(PRE_FIX, _spec(path="/elsewhere"))
    assert drift_check.CHECK_EXAMINED["32"] == {"examined": 0, "skipped": 1}
    assert len(findings) == 1 and "error" in findings[0]   # blind, gated


def test_any_clean_declaring_spec_passes(tree):
    """A path two specs declare passes if any declares a real body."""
    assert tree(PRE_FIX, _spec(), _spec(body=DTO)) == []


def test_examined_counts_every_write_block(tree):
    """The examined population is every POST/PUT/PATCH block with a spec op,
    so an upstream spec that fixes the defect reads 0 findings — never
    BLIND."""
    assert tree(FIXED, _spec(params=[])) == []
    assert drift_check.CHECK_EXAMINED["32"] == {"examined": 1, "skipped": 0}


# --------------------------------------------- shared helper and its users

def _op(spec, method="post", path=PATH):
    return spec["paths"][path][method]


def test_query_body_param_helper():
    spec = _spec()
    assert drift_check.query_body_param(_op(spec), spec)[0] == "thingDTO"
    two = _spec(params=[_param(), _param(name="otherDTO")])
    assert drift_check.query_body_param(_op(two), two) is None
    get = _spec(method="get")
    assert drift_check.query_body_param(_op(get, "get"), get) is None
    with_body = _spec(body=DTO)
    assert drift_check.query_body_param(_op(with_body), with_body) is None


def test_body_readers_see_the_lifted_body():
    """Checks 13/14/29/30 judge the body the generator renders, so a lifted
    DTO is the op's body and its query param is no longer a required query
    param."""
    spec = _spec()
    op = _op(spec)
    assert drift_check.body_schema(op, spec)["properties"] == DTO["properties"]
    assert drift_check.required_body_fields(op, spec) == ["name"]
    assert drift_check.required_query_params(op, spec) == []
    plain = _spec(params=[_param(schema={"type": "string"})])
    assert drift_check.required_query_params(_op(plain), plain) == ["thingDTO"]
    assert drift_check.body_schema(_op(plain), plain) is None


def test_parser_and_gate_agree_on_the_rule():
    """The gate keeps its own copy of the rule (an independent oracle); this
    pins the two copies to the same answers on every synthetic shape."""
    from tools.openapi_parser import parse_operation
    cases = [
        _spec(), _spec(params=[_param(), _param(name="otherDTO")]),
        _spec(body=DTO), _spec(params=[_param(style="deepObject")]),
        _spec(params=[_param(schema={"type": "string"})]),
        _spec(params=[_param(schema={"type": "object", "properties": {
            "a": {"type": "string"}}})]),
    ]
    for spec in cases:
        op = _op(spec)
        ep = parse_operation("post", PATH, op, spec)
        gate = drift_check.query_body_param(op, spec)
        assert bool(ep.lifted_query_params) == (gate is not None), spec


def test_registered_for_printing_and_never_raises(capsys):
    assert "32" in drift_check.CHECK_PRINT
    drift_check.CHECK_EXAMINED["32"] = {"examined": 3, "skipped": 0}
    drift_check.print_check_findings("32", [{"bogus": 1}])
    out = capsys.readouterr().out
    assert out.startswith("[32] ") and "FORMAT-ERROR" in out
