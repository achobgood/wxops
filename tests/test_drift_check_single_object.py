"""Drift gate check 25: a single-resource GET rendered through the list extractor.

`detect_command_type`'s "path ends in `{param}` -> show" rule could not see
`{flowId}:export`, so the array-property heuristic made it a list and the
renderer emitted only `result["nodes"]` — a flow export that cannot be
re-imported. Same shape: `cc-flow list-validate` dropped `valid: false`, and
`cc-legacy-flows list` (also an export) emitted only `associatedChannels`
(2026-10-13). `parse_tag` now reclassifies these to `show`; this check keeps
it that way.

A GET block whose path ends in `{}` or `{}:<action>` and that extracts
`result.get("<key>", result.get("data", …))` fires when the spec's 200 object
declares a property the extractor would drop — anything besides the extracted
key and a paging envelope (`meta`, totals, SCIM/bulk-export page fields). A
genuine collection keyed by a path id (`…/workspace-id/{workspaceId}` ->
`{data, meta}`, `…/availability/{clusterId}` -> `{items}`) drops nothing and
passes; a bare-array response has no key to extract and passes.

Every fire case has a paired no-fire case, written so the check can fail it.
"""

import json

import pytest

from tools import drift_check


LIST_BLOCK = '''
@app.command("CMD")
def cmd(
    flow_id: str = typer.Argument(help="flow id"),
    output: str = typer.Option("table", "--output", "-o"),
):
    """Do a thing."""
    url = f"https://webexapis.com/v1/PATH"
    params = {}
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    result = result or {}
    items = result.get("KEY", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output)
'''

SHOW_BLOCK = '''
@app.command("CMD")
def cmd(
    flow_id: str = typer.Argument(help="flow id"),
    output: str = typer.Option("json", "--output", "-o"),
):
    """Do a thing."""
    url = f"https://webexapis.com/v1/PATH"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    emit(result, output)
'''

EXPORT_PATH = "/zz/project/{projectId}/v2/flows/{flowId}:export"
EXPORT_URL = "zz/project/{project_id}/v2/flows/{flow_id}:export"


def _block(template, cmd="export", path=EXPORT_URL, key="nodes"):
    return (template.replace("CMD", cmd).replace("PATH", path)
            .replace("KEY", key))


def _obj(props, required=None):
    return {"type": "object", "properties": props}


ARR = {"type": "array", "items": {"type": "object"}}
STR = {"type": "string"}
FLOW = _obj({"nodes": ARR, "edges": ARR, "variables": ARR, "name": STR})


def _spec(schema, path=EXPORT_PATH, method="get", media="application/json"):
    content = {media: {"schema": schema}} if schema is not None else None
    resp = {"description": "ok"}
    if content is not None:
        resp["content"] = content
    return {"paths": {path: {method: {
        "tags": ["Probe"], "responses": {"200": resp}}}}}


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(module_src, *spec_list, module="zz_probe.py"):
        (cmds / module).write_text(module_src)
        for i, spec in enumerate(spec_list):
            name = "webex-probe.json" if i == 0 else f"webex-probe{i}.json"
            (specs / name).write_text(json.dumps(spec))
        return drift_check.check_single_object_list_render(
            commands_dir=cmds, specs_dir=specs)

    return run


# ------------------------------------------------------- the 2026-10-13 bug

def test_action_on_id_with_list_extractor_fires(tree):
    """`cc-flow export` before the fix: `{flowId}:export` extracted `nodes`."""
    findings = tree(_block(LIST_BLOCK), _spec(FLOW))
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["group"] == "zz-probe" and f["command"] == "export"
    assert f["op"] == f"GET {EXPORT_PATH}"
    assert f["extracts"] == "nodes"
    assert f["spec"] == "webex-probe.json"


def test_action_on_id_rendered_as_show_passes(tree):
    """The shipped fix: the same op rendered as `show` emits the object."""
    assert tree(_block(SHOW_BLOCK), _spec(FLOW)) == []
    assert drift_check.CHECK_EXAMINED["25"]["examined"] == 1


def test_collection_path_with_list_extractor_passes(tree):
    """`…/flows` is a collection; extracting from it is what a list does."""
    spec = _spec(FLOW)
    spec["paths"]["/zz/project/{projectId}/v2/flows"] = {"get": {
        "responses": {"200": {"description": "ok", "content": {
            "application/json": {"schema": _obj({"data": ARR, "name": STR})}}}}}}
    findings = tree(
        _block(LIST_BLOCK, cmd="list", path="zz/project/{project_id}/v2/flows",
               key="data") + "\n" + _block(SHOW_BLOCK), spec)
    assert findings == []
    assert drift_check.CHECK_EXAMINED["25"] == {"examined": 1, "skipped": 0}


def test_id_path_returning_bare_array_passes(tree):
    """A bare array has no key to extract: the extractor's fallback returns it."""
    assert tree(_block(LIST_BLOCK), _spec(ARR)) == []


def test_validate_drops_the_verdict_fires(tree):
    """`cc-flow list-validate`: `{valid, results[]}` -> only `results`."""
    path = "/zz/project/{projectId}/v2/flows/{flowId}:validate"
    findings = tree(
        _block(LIST_BLOCK, cmd="list-validate",
               path="zz/project/{project_id}/v2/flows/{flow_id}:validate",
               key="results"),
        _spec(_obj({"results": ARR, "valid": {"type": "boolean"}}), path=path))
    assert [(f["command"], f["extracts"]) for f in findings] == [
        ("list-validate", "results")]


def test_validate_shape_rendered_as_show_passes(tree):
    path = "/zz/project/{projectId}/v2/flows/{flowId}:validate"
    assert tree(
        _block(SHOW_BLOCK, cmd="validate",
               path="zz/project/{project_id}/v2/flows/{flow_id}:validate"),
        _spec(_obj({"results": ARR, "valid": {"type": "boolean"}}),
              path=path)) == []


# ------------------------------------------------- bare `{id}` terminations

def test_bare_id_path_with_list_extractor_fires(tree):
    path = "/zz/things/{thingId}"
    findings = tree(
        _block(LIST_BLOCK, cmd="list-thing", path="zz/things/{thing_id}",
               key="tags"),
        _spec(_obj({"tags": ARR, "orgName": STR}), path=path))
    assert [f["command"] for f in findings] == ["list-thing"]


def test_id_keyed_collection_wrapper_passes(tree):
    """`…/workspace-id/{workspaceId}` -> `{data, meta}` is a collection keyed
    by a path id (17 such ops at HEAD). Listing it drops nothing."""
    path = "/zz/person/workspace-id/{workspaceId}"
    findings = tree(
        _block(LIST_BLOCK, cmd="list", path="zz/person/workspace-id/{workspace_id}",
               key="data"),
        _spec(_obj({"data": ARR, "meta": _obj({"orgId": STR})}), path=path))
    assert findings == []


def test_id_keyed_collection_with_extra_field_fires(tree):
    """Same path, but the object also carries a field the list would drop."""
    path = "/zz/person/workspace-id/{workspaceId}"
    findings = tree(
        _block(LIST_BLOCK, cmd="list", path="zz/person/workspace-id/{workspace_id}",
               key="data"),
        _spec(_obj({"data": ARR, "meta": STR, "valid": {"type": "boolean"}}),
              path=path))
    assert [f["extracts"] for f in findings] == ["data"]


def test_items_only_wrapper_passes(tree):
    """`/videoMesh/clusters/availability/{clusterId}` -> `{items}` only."""
    path = "/zz/availability/{clusterId}"
    assert tree(
        _block(LIST_BLOCK, cmd="list", path="zz/availability/{cluster_id}",
               key="items"),
        _spec(_obj({"items": ARR}), path=path)) == []


@pytest.mark.parametrize("envelope", [
    "meta", "totalResources", "pageSize", "pageNumber", "rel", "totalResults",
    "itemsPerPage", "startIndex", "schemas", "total", "totalCount",
    "totalRecords", "count", "pageInfo", "links", "_links"])
def test_paging_envelope_siblings_pass(tree, envelope):
    path = "/zz/availability/{clusterId}"
    assert tree(
        _block(LIST_BLOCK, cmd="list", path="zz/availability/{cluster_id}",
               key="items"),
        _spec(_obj({"items": ARR, envelope: STR}), path=path)) == []


def test_extracted_key_absent_from_a_single_object_fires(tree):
    """A single object without the extracted key prints `[]` — every field
    dropped (the `cc-user-profiles list-acl` shape)."""
    path = "/zz/things/{thingId}"
    findings = tree(
        _block(LIST_BLOCK, cmd="list", path="zz/things/{thing_id}", key="items"),
        _spec(_obj({"editableFolderIds": ARR, "name": STR}), path=path))
    assert [f["extracts"] for f in findings] == ["items"]


def test_allof_and_ref_schemas_are_resolved(tree):
    spec = _spec({"$ref": "#/components/schemas/Flow"})
    spec["components"] = {"schemas": {
        "Base": _obj({"name": STR}),
        "Flow": {"allOf": [{"$ref": "#/components/schemas/Base"},
                           _obj({"nodes": ARR})]}}}
    findings = tree(_block(LIST_BLOCK), spec)
    assert [f["extracts"] for f in findings] == ["nodes"]


def test_wildcard_media_type_is_read(tree):
    """CC exports declare only `*/*`; a JSON-only reader would see nothing."""
    findings = tree(_block(LIST_BLOCK), _spec(FLOW, media="*/*"))
    assert [f["extracts"] for f in findings] == ["nodes"]


def test_hyphenated_action_suffix_is_in_scope(tree):
    path = "/zz/flows/{flowId}:dry-run"
    findings = tree(
        _block(LIST_BLOCK, cmd="list-dry-run", path="zz/flows/{flow_id}:dry-run"),
        _spec(FLOW, path=path))
    assert [f["command"] for f in findings] == ["list-dry-run"]


# ---------------------------------------------------------- scope / skips

def test_literal_after_id_is_out_of_scope(tree):
    """`…/{id}/members` is a sub-collection, not a single resource."""
    spec = _spec(FLOW)
    spec["paths"]["/zz/things/{thingId}/members"] = spec["paths"][EXPORT_PATH]
    findings = tree(
        _block(LIST_BLOCK, cmd="list", path="zz/things/{thing_id}/members")
        + "\n" + _block(SHOW_BLOCK), spec)
    assert findings == []
    assert drift_check.CHECK_EXAMINED["25"] == {"examined": 1, "skipped": 0}


def test_non_get_block_is_ignored(tree):
    post = _block(LIST_BLOCK).replace("rest_get(url, params=params)",
                                      "rest_post(url, json={})")
    good = _block(LIST_BLOCK, cmd="export-two")
    spec = _spec(FLOW)
    spec["paths"][EXPORT_PATH]["post"] = spec["paths"][EXPORT_PATH]["get"]
    findings = tree(post + "\n" + good, spec)
    assert [f["command"] for f in findings] == ["export-two"]


def test_response_without_a_schema_is_skipped_and_counted(tree):
    """No declared properties: nothing to judge — never guessed."""
    good = _block(SHOW_BLOCK, cmd="show-two")
    findings = tree(_block(LIST_BLOCK) + "\n" + good, _spec(None))
    assert findings == []
    assert drift_check.CHECK_EXAMINED["25"] == {"examined": 1, "skipped": 1}


def test_skips_block_without_a_spec_op(tree):
    findings = tree(_block(LIST_BLOCK), _spec(FLOW, path="/zz/other/{id}"))
    assert [f.get("check") for f in findings] == ["25"]
    assert "examined 0" in findings[0]["error"]
    assert drift_check.CHECK_EXAMINED["25"] == {"examined": 0, "skipped": 1}


def test_examined_count_is_reported(tree):
    tree(_block(SHOW_BLOCK), _spec(FLOW))
    assert drift_check.CHECK_EXAMINED["25"] == {"examined": 1, "skipped": 0}


def test_two_specs_one_collection_shaped_passes(tree):
    """A path two specs declare: if either describes a drop-nothing collection,
    under-report rather than fail a correct command (as checks 9/23/24 do)."""
    findings = tree(_block(LIST_BLOCK), _spec(FLOW),
                    _spec(_obj({"nodes": ARR, "meta": STR})))
    assert findings == []


def test_two_specs_one_bare_array_passes(tree):
    assert tree(_block(LIST_BLOCK), _spec(FLOW), _spec(ARR)) == []


def test_two_specs_both_single_objects_fire_once_naming_both(tree):
    findings = tree(_block(LIST_BLOCK), _spec(FLOW), _spec(FLOW))
    assert len(findings) == 1
    assert findings[0]["spec"] == "webex-probe.json, webex-probe1.json"


def test_odd_input_never_raises(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()
    (cmds / "zz_probe.py").write_text(_block(LIST_BLOCK))
    (cmds / "zz_tail.py").write_text(
        '@app.command("tail")\ndef t():\n    url = f"https://webexapis.com/v1/zz/x/{a}"\n'
        '    r = api.session.rest_get(url, params=(params')
    (specs / "webex-probe.json").write_text(json.dumps({"paths": {
        EXPORT_PATH: {"get": {"responses": {"200": {"content": {
            "application/json": {"schema": {"properties": "nope"}},
            "text/plain": "nope"}}}}},
        "/zz/x/{a}": {"get": {"responses": ["not", "a", "dict"]}}}}))
    (specs / "webex-other.json").write_text("not json")
    findings = drift_check.check_single_object_list_render(
        commands_dir=cmds, specs_dir=specs)
    assert all(isinstance(f, dict) for f in findings)
    missing = drift_check.check_single_object_list_render(
        commands_dir=tmp_path / "nope", specs_dir=tmp_path / "nope")
    assert [f.get("check") for f in missing] == ["25"]


def test_live_tree_is_clean():
    assert drift_check.check_single_object_list_render() == []
    # A floor that catches blindness only (~230 today); zero is BLIND anyway.
    # A tight floor would fail the weekly job when upstream retires endpoints.
    assert drift_check.CHECK_EXAMINED["25"]["examined"] >= 20


def test_check_25_line_format(capsys, monkeypatch):
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "25",
                        {"examined": 230, "skipped": 3})
    f = {"group": "cc-flow", "command": "export", "op": "GET /v1/f/{id}:export",
         "extracts": "nodes", "spec": "webex-contact-center.json"}
    drift_check.print_check_findings("25", [f])
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "[25] single-resource GETs rendered through the list extractor: 1"
        "   (examined 230 single-resource GETs, skipped 3)",
        "      wxcli cc-flow export  extracts nodes  GET /v1/f/{id}:export  "
        "(webex-contact-center.json)",
    ]
