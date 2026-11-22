"""Drift gate check 37: a server-assigned (`readOnly`) body field offered as a flag.

`parse_request_body` ignored `readOnly: true`, so `createdTime` and
`lastUpdatedTime` of a shared Contact Center DTO became flags on 22 commands
and keys of every `--generate-json-body` skeleton; the server ignores them
(audit F6, live 2026-11-10: `cc-work-types create --created-time 1000` came
back with the server's own clock).

A POST/PUT/PATCH block fires when a spec op it renders declares a TOP-LEVEL
request property that resolves `readOnly: true` (its own schema or a `$ref`)
and the block writes `body["<name>"]` or its `_BODY_SKELETON_<FUNCTION>`
carries the name as a top-level key. Every fire case has a paired no-fire case.
Synthetic specs and blocks only; nothing here reads today's upstream content.
"""

import json

import pytest

from tools import drift_check
from tests.test_drift_check_query_enum import stub_unrelated_checks


PATH = "/org/{orgid}/thing"

# What the generator emitted before the fix: a flag, a body write, a skeleton key.
PRE_FIX = '''
_BODY_SKELETON_CREATE = '{"name":"...","createdTime":0}'

@app.command("create", short_help="Create a new Thing.")
def create(
    name: str = typer.Option(None, "--name", help="(required) The name."),
    created_time: str = typer.Option(None, "--created-time", help="Creation time."),
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
        if created_time is not None:
            body["createdTime"] = created_time
    result = api.session.rest_post(url, json=body)
'''

FIXED = '''
_BODY_SKELETON_CREATE = '{"name":"..."}'

@app.command("create", short_help="Create a new Thing.")
def create(
    name: str = typer.Option(None, "--name", help="(required) The name."),
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
    result = api.session.rest_post(url, json=body)
'''


def _body(extra=None):
    props = {"name": {"type": "string"},
             "createdTime": {"type": "integer", "readOnly": True}}
    props.update(extra or {})
    return {"type": "object", "properties": props}


def _spec(body=None, method="post", path=PATH, schemas=None):
    op = {"tags": ["Probe"], "operationId": "createThing",
          "parameters": [{"name": "orgid", "in": "path", "required": True,
                          "schema": {"type": "string"}}],
          "requestBody": {"content": {"application/json": {
              "schema": body if body is not None else _body()}}},
          "responses": {"200": {"description": "ok"}}}
    return {"components": {"schemas": schemas or {}},
            "paths": {path: {method: op}}}


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
        return drift_check.check_readonly_flags(
            commands_dir=cmds, specs_dir=specs)

    run.cmds, run.specs = cmds, specs
    return run


# ------------------------------------------------- bad block fires, good passes

def test_prefix_block_fires_with_both_defects(tree):
    findings = tree(PRE_FIX, _spec())
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["group"] == "zz-probe" and f["command"] == "create"
    assert f["op"] == f"POST {PATH}" and f["props"] == ["createdTime"]
    assert f["defects"] == ["flag write", "skeleton key"]
    assert drift_check.CHECK_EXAMINED["37"] == {"examined": 1, "skipped": 0}


def test_fixed_block_is_clean(tree):
    assert tree(FIXED, _spec()) == []
    assert drift_check.CHECK_EXAMINED["37"]["examined"] == 1


def test_flag_write_alone_fires(tree):
    block = PRE_FIX.replace('{"name":"...","createdTime":0}', '{"name":"..."}')
    findings = tree(block, _spec())
    assert [f["defects"] for f in findings] == [["flag write"]]


def test_skeleton_key_alone_fires(tree):
    block = FIXED.replace('{"name":"..."}', '{"name":"...","createdTime":0}')
    findings = tree(block, _spec())
    assert [f["defects"] for f in findings] == [["skeleton key"]]


def test_readonly_through_ref_fires(tree):
    spec = _spec(body=_body({"stamp": {"$ref": "#/components/schemas/Stamp"}}),
                 schemas={"Stamp": {"type": "integer", "readOnly": True}})
    block = FIXED.replace('{"name":"..."}', '{"name":"...","stamp":0}')
    findings = tree(block, spec)
    assert [f["props"] for f in findings] == [["stamp"]]


def test_body_through_ref_is_read(tree):
    spec = _spec(body={"$ref": "#/components/schemas/ThingDTO"},
                 schemas={"ThingDTO": _body()})
    assert len(tree(PRE_FIX, spec)) == 1


def test_put_and_patch_are_examined(tree):
    for method, call in (("put", "rest_put"), ("patch", "rest_patch")):
        block = PRE_FIX.replace("rest_post", call)
        findings = tree(block, _spec(method=method))
        assert len(findings) == 1, (method, findings)
        assert findings[0]["op"] == f"{method.upper()} {PATH}"


# ---------------------------------------------------- what must NOT fire

def test_nested_readonly_property_is_not_the_class(tree):
    """Top level only: a nested readOnly property belongs to an object the
    caller may be echoing back."""
    spec = _spec(body={"type": "object", "properties": {
        "name": {"type": "string"},
        "inner": {"type": "object", "properties": {
            "createdTime": {"type": "integer", "readOnly": True}}}}})
    block = PRE_FIX.replace('{"name":"...","createdTime":0}',
                            '{"name":"...","inner":{"createdTime":0}}')
    # drop the top-level createdTime flag write: the spec no longer has one
    block = block.replace(
        '        if created_time is not None:\n'
        '            body["createdTime"] = created_time\n', "")
    assert tree(block, spec) == []
    assert drift_check.CHECK_EXAMINED["37"]["examined"] == 1


def test_readonly_false_is_not_the_class(tree):
    spec = _spec(body=_body())
    spec["paths"][PATH]["post"]["requestBody"]["content"]["application/json"][
        "schema"]["properties"]["createdTime"]["readOnly"] = False
    assert tree(PRE_FIX, spec) == []


def test_writable_property_is_not_the_class(tree):
    spec = _spec(body={"type": "object", "properties": {
        "name": {"type": "string"}, "createdTime": {"type": "integer"}}})
    assert tree(PRE_FIX, spec) == []


def test_get_blocks_are_not_examined(tree):
    block = PRE_FIX.replace("rest_post(url, json=body)", "rest_get(url)")
    findings = tree(block, _spec(method="get"))
    assert findings and "error" in findings[0]          # BLIND: examined 0
    assert drift_check.CHECK_EXAMINED["37"]["examined"] == 0


def test_block_with_no_spec_op_is_skipped_and_counted(tree):
    findings = tree(PRE_FIX, _spec(path="/elsewhere"))
    assert drift_check.CHECK_EXAMINED["37"] == {"examined": 0, "skipped": 1}
    assert len(findings) == 1 and "error" in findings[0]   # blind, gated


def test_property_readonly_in_only_one_of_two_specs_is_not_the_class(tree):
    """Both declaring specs must agree (under-report rather than fail a
    correct command)."""
    writable = _spec(body={"type": "object", "properties": {
        "name": {"type": "string"}, "createdTime": {"type": "integer"}}})
    assert tree(PRE_FIX, _spec(), writable) == []
    assert len(tree(PRE_FIX, _spec(), _spec())) == 1


def test_a_spec_that_drops_the_marker_reads_a_clean_zero(tree):
    """Examined counts every write block with a body, so an upstream spec that
    removes `readOnly` is clean, never BLIND."""
    spec = _spec(body={"type": "object", "properties": {
        "name": {"type": "string"}}})
    assert tree(FIXED, spec) == []
    assert drift_check.CHECK_EXAMINED["37"] == {"examined": 1, "skipped": 0}


# --------------------------------------------------------- registered + safe

def test_registered_for_printing_and_never_raises(capsys):
    assert "37" in drift_check.CHECK_PRINT
    drift_check.CHECK_EXAMINED["37"] = {"examined": 3, "skipped": 0}
    drift_check.print_check_findings("37", [{"bogus": 1}])
    out = capsys.readouterr().out
    assert out.startswith("[37] ") and "FORMAT-ERROR" in out


def test_printed_line_names_the_command_and_property(capsys, tree):
    drift_check.print_check_findings("37", tree(PRE_FIX, _spec()))
    out = capsys.readouterr().out
    assert "wxcli zz-probe create" in out and "createdTime" in out


# ------------------------------------------- --enforce exits 1 on a planted defect

@pytest.mark.parametrize("module_src,expected_exit", [
    (PRE_FIX, 1),
    (FIXED, 0),
])
def test_enforce_exit_follows_a_planted_defect(monkeypatch, capsys, tree,
                                               module_src, expected_exit):
    import sys
    stub_unrelated_checks(monkeypatch)
    tree(module_src, _spec())      # writes the temp commands dir and specs
    real = drift_check.check_readonly_flags

    def planted(*a, **k):
        return real(commands_dir=tree.cmds, specs_dir=tree.specs)

    monkeypatch.setattr(drift_check, "check_readonly_flags", planted)
    monkeypatch.setattr(drift_check, "check_query_enum_help", lambda *a, **k: [])
    monkeypatch.setattr(sys, "argv", ["drift_check.py", "--enforce"])
    assert drift_check.main() == expected_exit
    out = capsys.readouterr().out
    assert "[37] write commands that offer a readOnly" in out
    assert ("FAIL" if expected_exit else "PASS") in out.splitlines()[-1]
