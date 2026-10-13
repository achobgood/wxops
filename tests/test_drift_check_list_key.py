"""Drift gate check 27: a list command whose extractor cannot reach the array.

The seven Contact Center bulk exports declare their 200 response only under
`*/*`. `_get_response_schema` read JSON content types only, so
`extract_response_list_key` never saw the `resources` array and the renderer
fell back to `result.get("items", result.get("data", …))` — `cc-global-vars
list` printed 0 of 9 rows, exit 0, plus a false "more pages" note
(2026-10-13). `cc-user-profiles list-acl` (a single object with six arrays)
extracted `items` the same way and printed `[]`.

A GET block that extracts `result.get("<key>", result.get("data", …))` fires
when the spec's 200 response declares at least one array property and none of
them is `<key>` or `data` (the extractor's fallback). A response with several
arrays passes when ANY one is reachable — the command may intentionally emit
one. A response that declares object properties but NO array fails too: the
extractor drops every field (`user-settings list-outbound-billing-plan`
printed `[]` for `{"enabled": true}`, live 2026-10-13 — the 200 was a
response-level `$ref` the parser never resolved, so it defaulted to a list).
A bare-array response has no key to extract and passes; a response that
declares no properties at all is skipped (nothing to judge, never guessed).

Every fire case has a paired no-fire case, written so the check can fail it.
"""

import json

import pytest

from tools import drift_check


LIST_BLOCK = '''
@app.command("CMD")
def cmd(
    output: str = typer.Option("table", "--output", "-o"),
):
    """List things."""
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
    output: str = typer.Option("json", "--output", "-o"),
):
    """Show a thing."""
    url = f"https://webexapis.com/v1/PATH"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    emit(result, output)
'''

EXPORT_PATH = "/zz/organization/{orgid}/cad-variable/bulk-export"
EXPORT_URL = "zz/organization/{org_id}/cad-variable/bulk-export"


def _block(template, cmd="list", path=EXPORT_URL, key="items"):
    return (template.replace("CMD", cmd).replace("PATH", path)
            .replace("KEY", key))


def _obj(props):
    return {"type": "object", "properties": props}


ARR = {"type": "array", "items": {"type": "object"}}
STR = {"type": "string"}
INT = {"type": "integer"}
EXPORT = _obj({"resources": ARR, "totalResources": INT, "pageNumber": INT})


def _spec(schema, path=EXPORT_PATH, method="get", media="*/*",
          components=None):
    content = {media: {"schema": schema}} if schema is not None else None
    resp = {"description": "ok"}
    if content is not None:
        resp["content"] = content
    spec = {"paths": {path: {method: {
        "tags": ["Probe"], "responses": {"200": resp}}}}}
    if components:
        spec["components"] = {"schemas": components}
    return spec


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
        return drift_check.check_unreachable_list_key(
            commands_dir=cmds, specs_dir=specs)

    return run


# ------------------------------------------------------- the 2026-10-13 bug

def test_star_media_type_resources_missed_fires(tree):
    """`cc-global-vars list` before the fix: `*/*` declares `resources`, the
    extractor reads `items` then `data` — neither exists, 0 rows printed."""
    findings = tree(_block(LIST_BLOCK), _spec(EXPORT))
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["group"] == "zz-probe" and f["command"] == "list"
    assert f["op"] == f"GET {EXPORT_PATH}"
    assert f["extracts"] == "items"
    assert f["spec_arrays"] == ["resources"]
    assert f["drops"] == ["pageNumber", "resources", "totalResources"]
    assert f["spec"] == "webex-probe.json"


def test_matching_key_passes(tree):
    """The fix: the extractor names `resources`."""
    assert tree(_block(LIST_BLOCK, key="resources"), _spec(EXPORT)) == []
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 1, "skipped": 0}


def test_data_fallback_passes(tree):
    """CC v2 lists return `{data: [...]}`; `items` misses, `data` is reached."""
    spec = _spec(_obj({"data": ARR, "meta": _obj({})}),
                 media="application/json")
    assert tree(_block(LIST_BLOCK, key="items"), spec) == []
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 1, "skipped": 0}


def test_data_only_response_without_data_key_fires(tree):
    """Paired with the fallback case: `data` reaches only a `data` array."""
    spec = _spec(_obj({"records": ARR, "meta": _obj({})}),
                 media="application/json")
    findings = tree(_block(LIST_BLOCK, key="items"), spec)
    assert [f["spec_arrays"] for f in findings] == [["records"]]


def test_bare_array_response_passes(tree):
    """A bare list has no key to extract: the extractor's own `result if
    isinstance(result, list)` branch emits it."""
    assert tree(_block(LIST_BLOCK), _spec(ARR)) == []
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 1, "skipped": 0}


def test_json_media_type_fires_too(tree):
    findings = tree(_block(LIST_BLOCK),
                    _spec(EXPORT, media="application/json"))
    assert [f["spec_arrays"] for f in findings] == [["resources"]]


# -------------------------------------------- several arrays in one response

ACL = _obj({"resources": ARR, "permissions": ARR, "viewableFolderIds": ARR,
            "name": STR})


def test_several_arrays_none_reachable_fires_naming_all(tree):
    """`cc-user-profiles list-acl` before the fix: six arrays, extracts
    `items`, printed `[]`."""
    findings = tree(_block(LIST_BLOCK, cmd="list-acl"), _spec(ACL))
    assert len(findings) == 1
    assert findings[0]["spec_arrays"] == [
        "permissions", "resources", "viewableFolderIds"]


def test_several_arrays_one_reachable_passes(tree):
    """A command that deliberately extracts one of several arrays is not this
    check's business — only an extractor that reaches NONE is."""
    assert tree(_block(LIST_BLOCK, cmd="list-acl", key="permissions"),
                _spec(ACL)) == []
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 1, "skipped": 0}


# ------------------------------------------------- composed and $ref schemas

def test_ref_and_allof_resolved_fires(tree):
    components = {
        "Page": _obj({"totalResources": INT}),
        "Export": {"allOf": [{"$ref": "#/components/schemas/Page"},
                             _obj({"resources": {"$ref":
                                   "#/components/schemas/Rows"}})]},
        "Rows": ARR,
    }
    spec = _spec({"$ref": "#/components/schemas/Export"},
                 components=components)
    findings = tree(_block(LIST_BLOCK), spec)
    assert [f["spec_arrays"] for f in findings] == [["resources"]]


def test_ref_and_allof_resolved_matching_key_passes(tree):
    components = {
        "Export": {"allOf": [_obj({"resources": {"$ref":
                                   "#/components/schemas/Rows"}})]},
        "Rows": ARR,
    }
    spec = _spec({"$ref": "#/components/schemas/Export"},
                 components=components)
    assert tree(_block(LIST_BLOCK, key="resources"), spec) == []


# ------------------------------------------- an object with no array at all

BILLING_PATH = "/zz/people/{personId}/outboundBillingPlan"
BILLING_URL = "zz/people/{person_id}/outboundBillingPlan"


def test_object_without_array_fires(tree):
    """`user-settings list-outbound-billing-plan` before the fix: `{enabled}`
    rendered through the list extractor printed `[]`."""
    spec = _spec(_obj({"enabled": {"type": "boolean"}}), path=BILLING_PATH,
                 media="application/json")
    findings = tree(_block(LIST_BLOCK, cmd="list-outbound-billing-plan",
                           path=BILLING_URL), spec)
    assert len(findings) == 1, findings
    assert findings[0]["spec_arrays"] == []
    assert findings[0]["drops"] == ["enabled"]
    assert findings[0]["op"] == f"GET {BILLING_PATH}"


def test_object_without_array_rendered_as_show_passes(tree):
    """The fix: the same op rendered as a single-object read."""
    good = _block(LIST_BLOCK, cmd="list-two", path="zz/two", key="resources")
    spec = _spec(_obj({"enabled": {"type": "boolean"}}), path=BILLING_PATH,
                 media="application/json")
    spec["paths"]["/zz/two"] = _spec(EXPORT)["paths"][EXPORT_PATH]
    findings = tree(_block(SHOW_BLOCK, cmd="list-outbound-billing-plan",
                           path=BILLING_URL) + "\n" + good, spec)
    assert findings == []
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 1, "skipped": 0}


def test_response_level_ref_object_fires(tree):
    """The 200 itself is `{"$ref": "#/components/responses/…"}`."""
    spec = _spec(None, path=BILLING_PATH)
    spec["paths"][BILLING_PATH]["get"]["responses"]["200"] = {
        "$ref": "#/components/responses/Billing"}
    spec["components"] = {"responses": {"Billing": {
        "description": "ok", "content": {"application/json": {"schema": {
            "$ref": "#/components/schemas/Plan"}}}}},
        "schemas": {"Plan": _obj({"enabled": {"type": "boolean"}})}}
    findings = tree(_block(LIST_BLOCK, path=BILLING_URL), spec)
    assert [f["drops"] for f in findings] == [["enabled"]]


def test_text_plain_object_without_array_fires(tree):
    """`guest-management list` (`/guests/count`) declares its object under
    `text/plain` only; the list extractor drops it all the same."""
    spec = _spec(_obj({"112": {"type": "number"}}), path="/zz/guests/count",
                 media="text/plain")
    findings = tree(_block(LIST_BLOCK, path="zz/guests/count"), spec)
    assert [f["drops"] for f in findings] == [["112"]]


def test_object_whose_key_names_a_non_array_property_passes(tree):
    """`{data: {...}}`: the `data` fallback emits that sub-object — something
    real is printed, so it is not this check's class."""
    spec = _spec(_obj({"data": _obj({"task": STR}), "meta": STR}),
                 media="application/json")
    assert tree(_block(LIST_BLOCK), spec) == []
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 1, "skipped": 0}


# -------------------------------------------------------------- scope rules

def test_response_without_properties_is_skipped_and_counted(tree):
    """An object schema declaring no property: nothing to judge."""
    good = _block(LIST_BLOCK, cmd="list-two", path="zz/two", key="resources")
    spec = _spec({"type": "object"})
    spec["paths"]["/zz/two"] = _spec(EXPORT)["paths"][EXPORT_PATH]
    findings = tree(_block(LIST_BLOCK) + "\n" + good, spec)
    assert findings == []
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 1, "skipped": 1}


def test_response_without_a_schema_is_skipped_and_counted(tree):
    good = _block(LIST_BLOCK, cmd="list-two", path="zz/two", key="resources")
    spec = _spec(None)
    spec["paths"]["/zz/two"] = _spec(EXPORT)["paths"][EXPORT_PATH]
    findings = tree(_block(LIST_BLOCK) + "\n" + good, spec)
    assert findings == []
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 1, "skipped": 1}


def test_block_without_list_extractor_is_not_examined(tree):
    """A show-rendered block is not a list command: out of scope."""
    good = _block(LIST_BLOCK, cmd="list-two", path="zz/two", key="resources")
    spec = _spec(EXPORT)
    spec["paths"]["/zz/two"] = spec["paths"][EXPORT_PATH]
    findings = tree(_block(SHOW_BLOCK, cmd="show") + "\n" + good, spec)
    assert findings == []
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 1, "skipped": 0}


def test_non_get_block_is_ignored(tree):
    post = _block(LIST_BLOCK, cmd="create").replace(
        "rest_get(url, params=params)", "rest_post(url, json={})")
    bad = _block(LIST_BLOCK, cmd="list")
    spec = _spec(EXPORT)
    spec["paths"][EXPORT_PATH]["post"] = spec["paths"][EXPORT_PATH]["get"]
    findings = tree(post + "\n" + bad, spec)
    assert [f["command"] for f in findings] == ["list"]


def test_page_walker_block_is_judged(tree):
    """`--all` renders a walker beside rest_get; the block is still a GET."""
    walker = _block(LIST_BLOCK).replace(
        "result = api.session.rest_get(url, params=params)",
        "result = list(api.session.follow_page_param(url=url, params=params, "
        "item_key=\"items\"))")
    findings = tree(walker, _spec(EXPORT))
    assert [f["command"] for f in findings] == ["list"]


def test_skips_block_without_a_spec_op(tree):
    findings = tree(_block(LIST_BLOCK), _spec(EXPORT, path="/zz/other"))
    assert [f.get("check") for f in findings] == ["27"]
    assert "examined 0" in findings[0]["error"]
    assert drift_check.CHECK_EXAMINED["27"] == {"examined": 0, "skipped": 1}


# ------------------------------------------------ a path several specs declare

def test_two_specs_one_reachable_passes(tree):
    """Under-report rather than fail a correct command (as checks 9/23-25)."""
    other = _spec(_obj({"items": ARR}), media="application/json")
    assert tree(_block(LIST_BLOCK), _spec(EXPORT), other) == []


def test_two_specs_one_bare_array_passes(tree):
    assert tree(_block(LIST_BLOCK), _spec(EXPORT), _spec(ARR)) == []


def test_two_specs_both_unreachable_fire_once_naming_both(tree):
    other = _spec(_obj({"rows": ARR}), media="application/json")
    findings = tree(_block(LIST_BLOCK), _spec(EXPORT), other)
    assert len(findings) == 1
    assert findings[0]["spec"] == "webex-probe.json, webex-probe1.json"
    assert findings[0]["spec_arrays"] == ["resources", "rows"]


def test_two_specs_one_arrayless_other_unreachable_fires(tree):
    """A spec that declares nothing says nothing; the other one still judges."""
    findings = tree(_block(LIST_BLOCK), _spec(None), _spec(EXPORT))
    assert [f["spec_arrays"] for f in findings] == [["resources"]]


# ------------------------------------------------------------------- safety

def test_odd_input_never_raises(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()
    (cmds / "zz_probe.py").write_text(_block(LIST_BLOCK))
    (cmds / "zz_tail.py").write_text(
        '@app.command("tail")\ndef t():\n    url = f"https://webexapis.com/v1/zz/x"\n'
        '    r = api.session.rest_get(url, params=(params')
    (specs / "webex-probe.json").write_text(json.dumps({"paths": {
        EXPORT_PATH: {"get": {"responses": {"200": {"content": {
            "application/json": {"schema": {"properties": "nope"}},
            "*/*": "nope"}}}}},
        "/zz/x": {"get": {"responses": ["not", "a", "dict"]}}}}))
    (specs / "webex-other.json").write_text("not json")
    findings = drift_check.check_unreachable_list_key(
        commands_dir=cmds, specs_dir=specs)
    assert all(isinstance(f, dict) for f in findings)
    missing = drift_check.check_unreachable_list_key(
        commands_dir=tmp_path / "nope", specs_dir=tmp_path / "nope")
    assert [f.get("check") for f in missing] == ["27"]


def test_live_tree_is_clean():
    assert drift_check.check_unreachable_list_key() == []
    # A floor that catches blindness only (~540 today); zero is BLIND anyway.
    # A tight floor would fail the weekly job when upstream retires endpoints.
    assert drift_check.CHECK_EXAMINED["27"]["examined"] >= 20


def test_check_27_line_format(capsys, monkeypatch):
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "27",
                        {"examined": 540, "skipped": 4})
    f = {"group": "cc-global-vars", "command": "list",
         "op": "GET /organization/{orgid}/cad-variable/bulk-export",
         "extracts": "items", "spec_arrays": ["resources"],
         "drops": ["resources", "totalResources"],
         "spec": "webex-contact-center.json"}
    drift_check.print_check_findings("27", [f])
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "[27] list commands whose extractor cannot reach the response's "
        "array: 1   (examined 540 list commands, skipped 4)",
        "      wxcli cc-global-vars list  extracts items  spec arrays: "
        "resources  GET /organization/{orgid}/cad-variable/bulk-export  "
        "(webex-contact-center.json)",
    ]


def test_check_27_line_format_no_array(capsys, monkeypatch):
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "27",
                        {"examined": 540, "skipped": 4})
    f = {"group": "user-settings", "command": "list-outbound-billing-plan",
         "op": "GET /telephony/config/people/{personId}/outboundBillingPlan",
         "extracts": "items", "spec_arrays": [], "drops": ["enabled"],
         "spec": "webex-cloud-calling.json"}
    drift_check.print_check_findings("27", [f])
    out = capsys.readouterr().out.splitlines()
    assert out[1] == (
        "      wxcli user-settings list-outbound-billing-plan  extracts items  "
        "no array, drops: enabled  "
        "GET /telephony/config/people/{personId}/outboundBillingPlan  "
        "(webex-cloud-calling.json)")


def test_main_wires_check_27():
    """Gated, under its results key, and printed through CHECK_PRINT."""
    import inspect
    src = inspect.getsource(drift_check.main)
    assert '"27_unreachable_list_key": unreachable_list_keys' in src
    assert "or unreachable_list_keys" in src
    assert 'print_check_findings("27", unreachable_list_keys)' in src
    assert "27" in drift_check.CHECK_PRINT
