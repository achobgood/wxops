"""Shared static-analysis helpers behind drift checks 23-30.

Checks 23-30 all ask a question of the same two artifacts: a generated command
block (what the CLI sends) and the spec operation it renders (what the API
declares). These helpers are the single reader for both, so a parsing bug shows
up here once instead of as eight subtly different false zeros later.

Modules are string templates written to tmp_path, not files read off disk, so a
regen cannot quietly change what a test believes a command looks like. No test
imports wxcli or a generated module, and none touches the network.
"""

import json

from tools import drift_check as dc


EXPORT = '''
import typer

app = typer.Typer()


@app.command("list-export", hidden=True)
@app.command("export", short_help="Export a Flow or Subflow.")
def export(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="24-char hex id"),
    version: str = typer.Option(None, "--version", help="Version to export."),
):
    """Export a Flow or Subflow."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/flows/{flow_id}:export"
    params = {}
    if version is not None:
        params["version"] = version
    result = api.session.rest_get(url, params=params)
    emit(result, output=output, fields=fields)
'''

LIST_NODES = '''
@app.command("list")
def list_nodes(
    from_param: str = typer.Option(None, "--from", help="UTC date. See --to."),
    to: str = typer.Option(
        None,
        "--to",
        help="End (inclusive), e.g. foo(bar).",
    ),
    max_param: int = typer.Option(10, "--max"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page. Overrides --limit."),
):
    """List nodes."""
    url = f"https://webexapis.com/v1/hybrid/nodes"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    params["max"] = str(max_param)
    if all_pages:
        result = list(api.session.follow_pagination(url=url, params=params, item_key="nodes"))
    else:
        result = api.session.rest_get(url, params=params)
    items = result.get("nodes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])


@app.command("show")
def show_node(node_id: str = typer.Argument(help="id")):
    """Show a node."""
    url = f"https://webexapis.com/v1/hybrid/nodes/{node_id}"
    result = api.session.rest_get(url)
    emit(result, output=output, fields=fields)


@app.command("delete")
def delete_node(node_id: str = typer.Argument(help="id")):
    """Delete a node."""
    url = f"https://webexapis.com/v1/hybrid/nodes/{node_id}"
    api.session.rest_delete(url)


@app.command("walk-only")
def walk_only():
    """Only a page walker, no rest_* call."""
    url = f"https://analytics-calling.webexapis.com/v1/cdr_feed"
    items = list(api.session.fetch_from_offset(url, params={}, offset=0))


@app.command("no-url")
def no_url():
    """Hand-written seam: no url assignment."""
    do_something_local()
'''


def _write(dirpath, name, text):
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / name).write_text(text)


# ---------------------------------------------------------- iter_command_blocks

def test_iter_command_blocks_parses_name_method_path(tmp_path):
    cmds = tmp_path / "commands"
    _write(cmds, "cc_flow.py", EXPORT)
    blocks = dc.iter_command_blocks(commands_dir=cmds)
    # The hidden-alias decorator splits into its own block with no URL, so it
    # is dropped: one command, one block.
    assert len(blocks) == 1, blocks
    b = blocks[0]
    assert isinstance(b, dc.CommandBlock)
    assert b.module == "cc_flow"
    assert b.group == "cc-flow"
    assert b.command == "export"
    assert b.method == "GET"
    assert b.npath.endswith("/flows/{}:export"), b.npath
    assert not b.npath.startswith("{cc_base_url}")
    assert "rest_get" in b.text


def test_iter_command_blocks_methods_bases_and_drops(tmp_path):
    cmds = tmp_path / "commands"
    _write(cmds, "hybrid_nodes.py", LIST_NODES)
    _write(cmds, "_lazy.py", EXPORT)   # private module: never scanned
    (cmds / "binary.py").write_bytes(b"\xff\xfe\xfa\x00\x81")  # undecodable
    got = {(b.module, b.command): (b.method, b.npath)
           for b in dc.iter_command_blocks(commands_dir=cmds)}
    assert got == {
        ("hybrid_nodes", "list"): ("GET", "/hybrid/nodes"),
        ("hybrid_nodes", "show"): ("GET", "/hybrid/nodes/{}"),
        ("hybrid_nodes", "delete"): ("DELETE", "/hybrid/nodes/{}"),
        # walker only => GET; analytics base stripped, /v1 normalized away
        ("hybrid_nodes", "walk-only"): ("GET", "/cdr_feed"),
    }


def test_iter_command_blocks_missing_dir_is_empty(tmp_path):
    assert dc.iter_command_blocks(commands_dir=tmp_path / "nope") == []


# -------------------------------------------------------------- spec_ops_by_key

def _spec(paths, components=None):
    return {"openapi": "3.0.0", "paths": paths,
            "components": components or {}}


def test_blocks_skip_modules_without_spec_ops(tmp_path):
    """A hand-written / alias module whose URL no spec declares must have no
    key in the index — consumers skip such blocks rather than flag them."""
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    _write(cmds, "cc_flow.py", EXPORT)
    _write(specs, "webex-probe.json", json.dumps(_spec({
        "/v1/hybrid/nodes": {"get": {"responses": {}}},
    })))
    _write(specs, "notes.json", json.dumps(_spec({"/v1/x": {"get": {}}})))
    index = dc.spec_ops_by_key(specs_dir=specs)
    block = dc.iter_command_blocks(commands_dir=cmds)[0]
    assert (block.method, block.npath) not in index
    assert ("GET", "/hybrid/nodes") in index
    assert ("GET", "/x") not in index   # not a webex-*.json spec


def test_spec_ops_by_key_keeps_every_declaring_spec(tmp_path):
    specs = tmp_path / "specs"
    get_a = {"operationId": "a", "responses": {}}
    get_b = {"operationId": "b", "responses": {}}
    _write(specs, "webex-a.json", json.dumps(_spec({
        "/v1/things/{thingId}": {"get": get_a, "parameters": [],
                                 "x-vendor": {"get": "not an op"}},
    })))
    _write(specs, "webex-b.json", json.dumps(_spec({
        "/things/{id}/": {"get": get_b, "delete": {"responses": {}}},
    })))
    _write(specs, "webex-bad.json", "{ not json")      # unreadable: skipped
    _write(specs, "webex-list.json", json.dumps([1, 2]))  # wrong shape: skipped
    index = dc.spec_ops_by_key(specs_dir=specs)
    ops = index[("GET", "/things/{}")]
    assert [(o.spec_file, o.path, o.method, o.op["operationId"]) for o in ops] == [
        ("webex-a.json", "/v1/things/{thingId}", "GET", "a"),
        ("webex-b.json", "/things/{id}/", "GET", "b"),
    ]
    assert isinstance(ops[0], dc.SpecOp)
    assert isinstance(ops[0].spec, dict) and "paths" in ops[0].spec
    assert ("DELETE", "/things/{}") in index
    assert set(index) == {("GET", "/things/{}"), ("DELETE", "/things/{}")}


def test_spec_ops_by_key_merges_overlay_beside_specs_dir(tmp_path):
    specs = tmp_path / "specs"
    _write(specs, "webex-a.json", json.dumps(_spec({"/v1/a": {"get": {}}})))
    _write(specs / "overlays", "webex-a.overlay.json", json.dumps(
        {"paths": {"/v1/extra/{id}": {"x-wxcli-overlay": {}, "put": {}}}}))
    index = dc.spec_ops_by_key(specs_dir=specs)
    assert ("PUT", "/extra/{}") in index
    assert ("GET", "/a") in index


def test_spec_ops_by_key_sees_a_rewritten_spec(tmp_path):
    """Any caching must not hand back a stale index after the file changes."""
    specs = tmp_path / "specs"
    _write(specs, "webex-a.json", json.dumps(_spec({"/v1/a": {"get": {}}})))
    assert ("GET", "/a") in dc.spec_ops_by_key(specs_dir=specs)
    _write(specs, "webex-a.json", json.dumps(_spec({"/v1/bb": {"get": {}}})))
    index = dc.spec_ops_by_key(specs_dir=specs)
    assert ("GET", "/bb") in index and ("GET", "/a") not in index


# ------------------------------------------------------------ query_param_names

def test_query_param_names_resolves_refs(tmp_path):
    specs = tmp_path / "specs"
    op = {"parameters": [
        {"$ref": "#/components/parameters/size"},
        {"name": "flowId", "in": "path", "required": True},
        {"name": "X-Header", "in": "header"},
        {"$ref": "#/components/parameters/missing"},   # dangling: ignored
        "garbage",
    ]}
    spec = _spec(
        {"/v1/flows/{flowId}": {
            "parameters": [{"name": "orgId", "in": "query"}],
            "get": op}},
        {"parameters": {"size": {"name": "size", "in": "query"}}})
    _write(specs, "webex-a.json", json.dumps(spec))
    sop = dc.spec_ops_by_key(specs_dir=specs)[("GET", "/flows/{}")][0]
    assert dc.query_param_names(sop.op, sop.spec) == {"size", "orgId"}


def test_query_param_names_on_odd_input():
    assert dc.query_param_names({}, {}) == set()
    assert dc.query_param_names({"parameters": None}, {"paths": None}) == set()
    assert dc.query_param_names("not a dict", "nor this") == set()


# --------------------------------------------------------- response_array_props

def _op_200(content):
    return {"responses": {"200": {"content": content}}}


def test_response_array_props_any_media_type():
    spec = {"components": {"schemas": {
        "Page": {"type": "object", "properties": {
            "resources": {"type": "array", "items": {}},
            "meta": {"type": "object"}}},
    }}}
    wildcard = _op_200({"*/*": {"schema": {"$ref": "#/components/schemas/Page"}}})
    assert dc.response_array_props(wildcard, spec) == {"resources"}

    bare = _op_200({"application/json": {"schema": {
        "type": "array", "items": {"type": "object"}}}})
    assert dc.response_array_props(bare, spec) is None


def test_response_array_props_allof_and_property_refs():
    spec = {"components": {
        "schemas": {
            "Base": {"properties": {"items": {"type": "array"}}},
            "NodeList": {"type": "array", "items": {}},
            "Wrapped": {"allOf": [
                {"$ref": "#/components/schemas/Base"},
                {"properties": {"nodes": {"$ref": "#/components/schemas/NodeList"},
                                "count": {"type": "integer"}}}]},
        },
        "responses": {"Ok": {"content": {"application/json;charset=UTF-8": {
            "schema": {"$ref": "#/components/schemas/Wrapped"}}}}},
    }}
    op = {"responses": {"200": {"$ref": "#/components/responses/Ok"}}}
    assert dc.response_array_props(op, spec) == {"items", "nodes"}


def test_response_array_props_on_odd_input():
    assert dc.response_array_props({}, {}) == set()
    assert dc.response_array_props({"responses": {"204": {}}}, {}) == set()
    assert dc.response_array_props(_op_200(None), {}) == set()
    assert dc.response_array_props(_op_200({"*/*": {"schema": "x"}}), {}) == set()
    assert dc.response_array_props("nope", None) == set()
    cyclic = {"components": {"schemas": {
        "A": {"$ref": "#/components/schemas/A"}}}}
    assert dc.response_array_props(
        _op_200({"*/*": {"schema": {"$ref": "#/components/schemas/A"}}}),
        cyclic) == set()


# ------------------------------------------------------------ list_extractor_key

def test_list_extractor_key():
    blocks = LIST_NODES.split("\n@app.command")
    list_block = blocks[1]
    show_block = blocks[2]
    assert dc.list_extractor_key(list_block) == "nodes"
    assert dc.list_extractor_key(show_block) is None
    assert dc.list_extractor_key(
        'items = result.get("items", result.get("data", []))') == "items"


# ---------------------------------------------------------------- flag_query_map

def test_flag_query_map():
    block = '''
def f(
    from_param: str = typer.Option(None, "--from", help="x"),
):
    if from_param is not None:
        params["from"] = from_param
'''
    assert dc.flag_query_map(block) == {"--from": "from"}


def test_flag_query_map_multiline_str_and_unmapped():
    list_block = LIST_NODES.split("\n@app.command")[1]
    assert dc.flag_query_map(list_block) == {
        "--from": "from", "--to": "to", "--max": "max"}
    # an option that never reaches params, and a param fed by no option
    block = '''
    debug: bool = typer.Option(False, "--debug"),
    params["orgId"] = get_cc_org_id(api.session)
    body["name"] = name
'''
    assert dc.flag_query_map(block) == {}
    assert dc.flag_query_map("") == {}


def test_response_array_props_composed_property():
    """A property wrapping an array in allOf/oneOf/anyOf — directly or via a
    $ref — is an array; a composition with no array member is not."""
    spec = {"components": {"schemas": {
        "Ids": {"type": "array", "items": {"type": "string"}},
        "Name": {"type": "string"},
    }}}
    op = _op_200({"application/json": {"schema": {"type": "object", "properties": {
        "a": {"allOf": [{"$ref": "#/components/schemas/Ids"}]},
        "b": {"oneOf": [{"type": "null"}, {"type": "array", "items": {}}]},
        "c": {"anyOf": [{"$ref": "#/components/schemas/Name"},
                        {"allOf": [{"$ref": "#/components/schemas/Ids"}]}]},
        "d": {"oneOf": [{"$ref": "#/components/schemas/Name"}, {"type": "integer"}]},
        "e": {"allOf": "not a list"},
    }}}})
    assert dc.response_array_props(op, spec) == {"a", "b", "c"}


# ------------------------------------------------------------------ HELPER_SKIPS

def test_helper_skips_name_what_could_not_be_parsed(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    half = '''
@app.command("odd")
def odd():
    url = f"https://webexapis.com/v1/odd"
    httpx.get(url)
'''
    _write(cmds, "mod.py", EXPORT + half)
    (cmds / "binary.py").write_bytes(b"\xff\xfe\xfa\x00\x81")
    dc.iter_command_blocks(commands_dir=cmds)
    assert dc.HELPER_SKIPS["modules"] == ["binary"]
    # the hidden-alias block (name, no url, no call) is NOT a skip
    assert dc.HELPER_SKIPS["blocks"] == ["mod odd"]

    _write(specs, "webex-ok.json", json.dumps(_spec({"/v1/a": {"get": {}}})))
    _write(specs, "webex-bad.json", "{ not json")
    _write(specs, "webex-nopaths.json", json.dumps({"paths": []}))
    dc.spec_ops_by_key(specs_dir=specs)
    assert sorted(dc.HELPER_SKIPS["specs"]) == ["webex-bad.json", "webex-nopaths.json"]
    dc.spec_ops_by_key(specs_dir=specs)   # served from cache: still reported
    assert sorted(dc.HELPER_SKIPS["specs"]) == ["webex-bad.json", "webex-nopaths.json"]


# -------------------------------------------------------------- live-tree tripwire

def test_live_tree_helpers_are_not_blind():
    """Tripwire for checks 23-30. If a regen changes the `url = f"…"` line or
    the rest_*/walker call style, every block would drop silently and those
    checks would report a vacuous 0. src/ and specs/ are tracked, so this
    holds in a clean clone. Measured 2026-10-13: 2004 blocks, 2002 matched."""
    blocks = dc.iter_command_blocks()
    index = dc.spec_ops_by_key()
    assert len(blocks) >= 1500, len(blocks)
    matched = sum((b.method, b.npath) in index for b in blocks)
    assert matched / len(blocks) >= 0.95, (matched, len(blocks))
    assert dc.HELPER_SKIPS["modules"] == []
    # 2 today, both hand-written: cleanup run, cucm execute
    assert len(dc.HELPER_SKIPS["blocks"]) <= 10, dc.HELPER_SKIPS["blocks"]
    assert dc.HELPER_SKIPS["specs"] == []
