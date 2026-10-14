"""Drift gate check 31: a non-paging list command that drops part of one object.

A GET that returns ONE settings object which happens to contain an array was
classified `list` by `detect_command_type` (any array property -> list), so the
renderer emitted only `result.get("<array>", …)` and threw the rest away.
Measured live 2026-10-13: `call-queue list-night-service` printed `[]` while
the server returned 236 bytes (the night-service switch, its action, its
schedule — `[]` reads as "service off"); `user-settings list-privacy` and
`list-simultaneous-ring` printed `[]` for objects whose scalars carry the
whole setting. Check 27 passed every one of them, because the extractor key
DID name a declared array.

A GET block that extracts `result.get("<key>", result.get("data", …))` and
calls no page walker fires when every spec declaring its path describes the
200 as an object that, after removing paging metadata (`_LIST_ENVELOPE_KEYS`),
declares something besides the one property the extractor emits — a scalar
sibling, or a second array. A paged collection (the block calls
follow_pagination / follow_page_param / fetch_from_offset / follow_scim) is a
collection by declaration — rendering it as one object would cost `--all` —
so it fires only when the extractor emits an array of scalars while an array
of objects (the records) is dropped: `device-dynamic-settings list` took
`upgradeChannelList` and dropped `devices`. An extractor that reaches NOTHING
is check 27's class, not this one's.

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

NIGHT_PATH = "/zz/locations/{locationId}/queues/{queueId}/nightService"
NIGHT_URL = "zz/locations/{location_id}/queues/{queue_id}/nightService"


def _block(template, cmd="list-night-service", path=NIGHT_URL,
           key="audioFiles"):
    return (template.replace("CMD", cmd).replace("PATH", path)
            .replace("KEY", key))


def _walker(block, walker="follow_pagination"):
    """The same block with an `--all` branch, as the renderer emits it for an
    endpoint whose spec declares paging."""
    return block.replace(
        "result = api.session.rest_get(url, params=params)",
        "if all_pages:\n            items = list(api.session."
        f"{walker}(url=url, params=params, item_key=\"x\"))\n"
        "        result = api.session.rest_get(url, params=params)")


def _obj(props):
    return {"type": "object", "properties": props}


ARR = {"type": "array", "items": {"type": "object"}}
STR = {"type": "string"}
INT = {"type": "integer"}
BOOL = {"type": "boolean"}
NIGHT = _obj({"nightServiceEnabled": BOOL, "action": STR,
              "audioFiles": ARR, "businessHourSchedules": ARR})


def _spec(schema, path=NIGHT_PATH, method="get", media="application/json",
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
        return drift_check.check_list_drops_object_fields(
            commands_dir=cmds, specs_dir=specs)

    return run


# ------------------------------------------------------- the 2026-10-13 bug

def test_settings_object_with_scalars_and_arrays_fires(tree):
    """`call-queue list-night-service` before the fix: extracts `audioFiles`,
    drops the switch, the action and the second array."""
    findings = tree(_block(LIST_BLOCK), _spec(NIGHT))
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["group"] == "zz-probe" and f["command"] == "list-night-service"
    assert f["op"] == f"GET {NIGHT_PATH}"
    assert f["extracts"] == "audioFiles"
    assert f["drops"] == ["action", "businessHourSchedules",
                          "nightServiceEnabled"]
    assert f["spec"] == "webex-probe.json"
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 1, "skipped": 0}


def test_same_op_rendered_as_show_passes(tree):
    """The fix: a single-object read emits the whole response. A show block
    is not a list command, so it is not examined at all."""
    good = _block(LIST_BLOCK, cmd="list", path="zz/things", key="items")
    spec = _spec(NIGHT)
    spec["paths"]["/zz/things"] = _spec(_obj({"items": ARR}))["paths"][NIGHT_PATH]
    assert tree(_block(SHOW_BLOCK) + "\n" + good, spec) == []
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 1, "skipped": 0}


def test_one_array_and_one_scalar_fires(tree):
    """`user-settings list-privacy`: `monitoringAgents` + four booleans. One
    scalar sibling is enough — that scalar IS the setting."""
    spec = _spec(_obj({"monitoringAgents": ARR,
                       "aaExtensionDialingEnabled": BOOL}))
    findings = tree(_block(LIST_BLOCK, key="monitoringAgents"), spec)
    assert [f["drops"] for f in findings] == [["aaExtensionDialingEnabled"]]


def test_two_arrays_no_scalar_fires(tree):
    """`device-dynamic-settings list`: `upgradeChannelList` and `devices`; the
    extractor emits one array and drops the other."""
    spec = _spec(_obj({"upgradeChannelList": ARR, "devices": ARR}))
    findings = tree(_block(LIST_BLOCK, key="upgradeChannelList"), spec)
    assert [f["drops"] for f in findings] == [["devices"]]


def test_single_array_only_passes(tree):
    """A pure collection: the one array is everything there is."""
    spec = _spec(_obj({"audioFiles": ARR}))
    assert tree(_block(LIST_BLOCK), spec) == []
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 1, "skipped": 0}


# ------------------------------------------------- paging metadata is not data

@pytest.mark.parametrize("envelope", [
    {"meta": _obj({})},                                     # CC v2 lists
    {"totalResources": INT, "pageNumber": INT, "pageSize": INT, "rel": STR},
    {"totalResults": INT, "schemas": {"type": "array", "items": STR}},  # SCIM
    {"start": INT, "limit": INT, "total": INT},             # org-contacts
    {"count": STR},                                         # backgroundImages
])
def test_array_plus_paging_metadata_passes(tree, envelope):
    spec = _spec(_obj({"rows": ARR, **envelope}))
    assert tree(_block(LIST_BLOCK, key="rows"), spec) == []
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 1, "skipped": 0}


def test_array_plus_metadata_plus_data_fires(tree):
    """Paired: metadata is subtracted, a real sibling still counts."""
    spec = _spec(_obj({"rows": ARR, "meta": _obj({}), "enabled": BOOL}))
    findings = tree(_block(LIST_BLOCK, key="rows"), spec)
    assert [f["drops"] for f in findings] == [["enabled"]]


def test_data_fallback_is_what_is_emitted(tree):
    """`items` misses, the `data` fallback is emitted: what is dropped is
    everything except `data`."""
    spec = _spec(_obj({"data": ARR, "meta": _obj({}), "state": STR}))
    findings = tree(_block(LIST_BLOCK, key="items"), spec)
    assert [(f["extracts"], f["drops"]) for f in findings] == [
        ("items", ["state"])]


# ------------------------------------------------------- paged collections

@pytest.mark.parametrize("walker", ["follow_pagination", "follow_page_param",
                                    "fetch_from_offset", "follow_scim"])
def test_paged_collection_may_drop_siblings(tree, walker):
    """`people list` (`items` + `notFoundIds`), `groups list-members`: the
    spec declares paging, the command walks pages, so it is a collection by
    declaration — rendering it as one object would lose `--all`. Its
    siblings are per-page context, not a finding."""
    findings = tree(_walker(_block(LIST_BLOCK), walker), _spec(NIGHT))
    assert findings == []
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 1, "skipped": 0}


STR_ARR = {"type": "array", "items": {"type": "string"}}
DEVICES = _obj({"upgradeChannelList": STR_ARR, "devices": ARR})


def test_paged_collection_extracting_scalars_beside_records_fires(tree):
    """`device-dynamic-settings list` before the fix: a Link-paged endpoint
    whose 200 declares `upgradeChannelList` (strings) before `devices`
    (objects); the extractor took the strings and every device was dropped,
    under a table that asked for model/displayName/type."""
    findings = tree(_walker(_block(LIST_BLOCK, cmd="list",
                                   key="upgradeChannelList")),
                    _spec(DEVICES))
    assert [(f["extracts"], f["drops"]) for f in findings] == [
        ("upgradeChannelList", ["devices"])]


def test_paged_collection_extracting_the_records_passes(tree):
    findings = tree(_walker(_block(LIST_BLOCK, cmd="list", key="devices")),
                    _spec(DEVICES))
    assert findings == []
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 1, "skipped": 0}


def test_paged_collection_extracting_records_beside_scalars_passes(tree):
    """`people list`: `items` (objects) beside `notFoundIds` (strings)."""
    spec = _spec(_obj({"items": ARR, "notFoundIds": STR_ARR}))
    assert tree(_walker(_block(LIST_BLOCK, cmd="list", key="items")),
                spec) == []


def test_paged_scalar_list_with_scalar_siblings_passes(tree):
    """Only a dropped array of RECORDS makes a paged command a finding."""
    spec = _spec(_obj({"names": STR_ARR, "other": STR_ARR, "mode": STR}))
    assert tree(_walker(_block(LIST_BLOCK, cmd="list", key="names")),
                spec) == []


# ------------------------------------------------ check 27's class, not 31's

def test_extractor_that_reaches_nothing_is_left_to_check_27(tree):
    """`items` and `data` are both absent: everything is dropped, which is
    check 27's finding. Check 31 judges only an extractor that emits SOME
    declared property and drops the rest — one defect, one check."""
    spec = _spec(_obj({"rows": ARR, "enabled": BOOL}))
    assert tree(_block(LIST_BLOCK, key="items"), spec) == []
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 1, "skipped": 0}


def test_bare_array_response_passes(tree):
    assert tree(_block(LIST_BLOCK), _spec(ARR)) == []
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 1, "skipped": 0}


# ------------------------------------------------- composed and $ref schemas

def test_ref_and_allof_resolved_fires(tree):
    components = {
        "Base": _obj({"enabled": BOOL}),
        "Night": {"allOf": [{"$ref": "#/components/schemas/Base"},
                            _obj({"audioFiles": {"$ref":
                                  "#/components/schemas/Rows"}})]},
        "Rows": ARR,
    }
    spec = _spec({"$ref": "#/components/schemas/Night"},
                 components=components)
    findings = tree(_block(LIST_BLOCK), spec)
    assert [f["drops"] for f in findings] == [["enabled"]]


def test_response_level_ref_fires(tree):
    spec = _spec(None)
    spec["paths"][NIGHT_PATH]["get"]["responses"]["200"] = {
        "$ref": "#/components/responses/Night"}
    spec["components"] = {"responses": {"Night": {
        "description": "ok", "content": {"application/json": {
            "schema": NIGHT}}}}}
    findings = tree(_block(LIST_BLOCK), spec)
    assert [f["command"] for f in findings] == ["list-night-service"]


def test_star_media_type_fires(tree):
    findings = tree(_block(LIST_BLOCK), _spec(NIGHT, media="*/*"))
    assert [f["command"] for f in findings] == ["list-night-service"]


def test_one_clean_media_type_passes(tree):
    """Several media types: any one describing a pure collection passes
    (under-report rather than fail a correct command)."""
    spec = _spec(NIGHT)
    spec["paths"][NIGHT_PATH]["get"]["responses"]["200"]["content"][
        "text/plain"] = {"schema": _obj({"audioFiles": ARR})}
    assert tree(_block(LIST_BLOCK), spec) == []


# -------------------------------------------------------------- scope rules

def test_response_without_properties_is_skipped_and_counted(tree):
    good = _block(LIST_BLOCK, cmd="list", path="zz/two", key="items")
    spec = _spec({"type": "object"})
    spec["paths"]["/zz/two"] = _spec(_obj({"items": ARR}))["paths"][NIGHT_PATH]
    assert tree(_block(LIST_BLOCK) + "\n" + good, spec) == []
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 1, "skipped": 1}


def test_block_without_a_spec_op_is_skipped_and_blind(tree):
    findings = tree(_block(LIST_BLOCK), _spec(NIGHT, path="/zz/other"))
    assert [f.get("check") for f in findings] == ["31"]
    assert "examined 0" in findings[0]["error"]
    assert drift_check.CHECK_EXAMINED["31"] == {"examined": 0, "skipped": 1}


def test_non_get_block_is_ignored(tree):
    post = _block(LIST_BLOCK, cmd="create").replace(
        "rest_get(url, params=params)", "rest_post(url, json={})")
    spec = _spec(NIGHT)
    spec["paths"][NIGHT_PATH]["post"] = spec["paths"][NIGHT_PATH]["get"]
    findings = tree(post + "\n" + _block(LIST_BLOCK), spec)
    assert [f["command"] for f in findings] == ["list-night-service"]


# ------------------------------------------------ a path several specs declare

def test_two_specs_one_clean_passes(tree):
    assert tree(_block(LIST_BLOCK), _spec(NIGHT),
                _spec(_obj({"audioFiles": ARR}))) == []


def test_two_specs_both_drop_fire_once_naming_both(tree):
    other = _spec(_obj({"audioFiles": ARR, "mode": STR}))
    findings = tree(_block(LIST_BLOCK), _spec(NIGHT), other)
    assert len(findings) == 1
    assert findings[0]["spec"] == "webex-probe.json, webex-probe1.json"
    assert findings[0]["drops"] == ["action", "businessHourSchedules",
                                    "mode", "nightServiceEnabled"]


def test_two_specs_one_shapeless_other_drops_fires(tree):
    findings = tree(_block(LIST_BLOCK), _spec(None), _spec(NIGHT))
    assert [f["command"] for f in findings] == ["list-night-service"]


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
        NIGHT_PATH: {"get": {"responses": {"200": {"content": {
            "application/json": {"schema": {"properties": "nope"}},
            "*/*": "nope"}}}}},
        "/zz/x": {"get": {"responses": ["not", "a", "dict"]}}}}))
    (specs / "webex-other.json").write_text("not json")
    findings = drift_check.check_list_drops_object_fields(
        commands_dir=cmds, specs_dir=specs)
    assert all(isinstance(f, dict) for f in findings)
    missing = drift_check.check_list_drops_object_fields(
        commands_dir=tmp_path / "nope", specs_dir=tmp_path / "nope")
    assert [f.get("check") for f in missing] == ["31"]


def test_live_tree_is_clean():
    assert drift_check.check_list_drops_object_fields() == []
    # A floor that catches blindness only; zero is BLIND anyway. A tight
    # floor would fail the weekly job when upstream retires endpoints.
    assert drift_check.CHECK_EXAMINED["31"]["examined"] >= 20


def test_check_31_line_format(capsys, monkeypatch):
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "31",
                        {"examined": 300, "skipped": 4})
    f = {"group": "call-queue", "command": "list-night-service",
         "op": "GET /telephony/config/locations/{locationId}/queues/"
               "{queueId}/nightService",
         "extracts": "audioFiles", "drops": ["action", "nightServiceEnabled"],
         "spec": "webex-cloud-calling.json"}
    drift_check.print_check_findings("31", [f])
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "[31] list commands that drop part of the response object: 1   "
        "(examined 300 list commands, skipped 4)",
        "      wxcli call-queue list-night-service  extracts audioFiles  "
        "drops: action, nightServiceEnabled  GET /telephony/config/locations/"
        "{locationId}/queues/{queueId}/nightService  "
        "(webex-cloud-calling.json)",
    ]


def test_main_wires_check_31_last():
    """Gated, under its results key, printed through CHECK_PRINT, and printed
    after check 30 — CI asserts the LAST check's line to prove the gate ran
    to completion."""
    import inspect
    src = inspect.getsource(drift_check.main)
    assert '"31_list_drops_object_fields": list_drops_object_fields' in src
    assert "or list_drops_object_fields" in src
    printed = 'print_check_findings("31", list_drops_object_fields)'
    assert printed in src
    assert src.index(printed) > src.index('print_check_findings("30"')
    assert "31" in drift_check.CHECK_PRINT


def test_envelope_key_lists_stay_in_sync():
    """The parser decides list-vs-object at generation time and drift check 31 gates
    the same decision from the rendered command; two copies of the paging-metadata
    key set that drift apart would let the generator and the gate disagree."""
    from tools import openapi_parser
    assert openapi_parser._LIST_ENVELOPE_KEYS == drift_check._LIST_ENVELOPE_KEYS
