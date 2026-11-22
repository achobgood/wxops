"""Drift gate check 40: the top-level JSON type a command's flag path sends must
be the type the spec's request body declares (audit F1).

`openapi_parser.parse_operation` chose the patch-array renderer from the media
type alone, so `meetings update-meetings --title X` sent `[{"title": "X"}]` for a
body declared as an object (HTTP 400 live, 2026-11-10) and `cc-journey
delete-person-id-workspace-id --value id1` sent `[{"value": "id1"}]` for an
array of strings. The check reads the type the rendered block builds
(`body = {}` is an object, `body = [patch_op]` an array, the "JSON array"
refusal an array that only `--json-body` can supply) and the type of the
PARSER's resolved schema, and fires when they differ. Exempt, and counted as
skipped: one JSON Patch operation (`op`, which the wire wraps in an array), a
string body, an untyped body. For an array of patch operations it also fires
when a required item key has no flag.

Every fire case has a paired no-fire case. Synthetic specs and blocks only.
"""

import json

import pytest

from tools import drift_check
from tests.test_drift_check_query_enum import stub_unrelated_checks


PATH = "/things/{thingId}"

OBJECT = {"type": "object", "properties": {"title": {"type": "string"}}}
STRINGS = {"type": "array", "items": {"type": "string"}}
PATCH_OP = {"type": "object", "required": ["op", "path"], "properties": {
    "op": {"type": "string"}, "path": {"type": "string"},
    "value": {"type": "string"}}}
OP_ARRAY = {"type": "array", "items": PATCH_OP}

_ARRAY_REFUSAL = ("This command's body is a JSON array; "
                  "pass it with --json-body '[…]'")

_FLAG_PATHS = {
    "object": '        body = {}\n        if title is not None:\n            body["title"] = title\n',
    "patch": ('        patch_op = {}\n'
              '        if op is not None:\n            patch_op["op"] = op\n'
              '        if path is not None:\n            patch_op["path"] = path\n'
              '        body = [patch_op]\n'),
    "patch_op_only": ('        patch_op = {}\n'
                      '        if path is not None:\n            patch_op["path"] = path\n'
                      '        body = [patch_op]\n'),
    "array_refusal": f'        typer.echo("{_ARRAY_REFUSAL}", err=True)\n        raise typer.Exit(1)\n',
    "none": "        pass\n",
}


def _block(flag_path="object", method_call="rest_patch", command="update"):
    return f'''
@app.command("{command}", short_help="Probe.")
def {command}(
    thing_id: str = typer.Argument(help="thingId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Probe."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/things/{{thing_id}}"
    if json_body:
        body = load_json_body(json_body)
    else:
{_FLAG_PATHS[flag_path]}    result = api.session.{method_call}(url, json=body)
'''


def _spec(schema, method="patch", path=PATH,
          content_type="application/json-patch+json"):
    op = {"tags": ["Probe"], "operationId": "probe",
          "parameters": [{"name": "thingId", "in": "path", "required": True,
                          "schema": {"type": "string"}}],
          "requestBody": {"content": {content_type: {"schema": schema}}},
          "responses": {"200": {"description": "ok"}}}
    return {"components": {"schemas": {}}, "paths": {path: {method: op}}}


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(module_src, *spec_list):
        (cmds / "zz_probe.py").write_text(module_src, encoding="utf-8")
        for i, spec in enumerate(spec_list):
            name = "webex-probe.json" if i == 0 else f"webex-probe{i}.json"
            (specs / name).write_text(json.dumps(spec))
        return drift_check.check_body_shape(commands_dir=cmds, specs_dir=specs)

    run.cmds, run.specs = cmds, specs
    return run


# ------------------------------------------------- bad block fires, good passes

def test_object_body_built_as_object_is_clean(tree):
    assert tree(_block("object"), _spec(OBJECT)) == []
    assert drift_check.CHECK_EXAMINED["40"] == {"examined": 1, "skipped": 0}


def test_object_body_wrapped_in_an_array_fires(tree):
    """meetings update-meetings before the fix."""
    findings = tree(_block("patch"), _spec(OBJECT))
    assert len(findings) == 1, findings
    f = findings[0]
    assert (f["group"], f["command"], f["kind"]) == ("zz-probe", "update", "type")
    assert f["declared"] == "object" and f["sent"] == "array"
    assert f["op"] == f"PATCH {PATH}"


def test_array_of_strings_wrapped_as_a_patch_op_fires(tree):
    """cc-journey delete-person-id-workspace-id before the fix: the top-level
    type (array) matches, but the elements are `{"value": ...}` objects where
    the spec declares strings, so the wrapped patch op is a finding of its own."""
    findings = tree(_block("patch"), _spec(STRINGS))
    assert len(findings) == 1, findings
    assert findings[0]["kind"] == "item" and findings[0]["fields"] == ["patch_op"]


def test_array_body_refusing_without_json_body_is_clean(tree):
    assert tree(_block("array_refusal"), _spec(STRINGS)) == []
    assert drift_check.CHECK_EXAMINED["40"] == {"examined": 1, "skipped": 0}


def test_array_body_built_as_an_object_fires(tree):
    findings = tree(_block("object"), _spec(STRINGS))
    assert len(findings) == 1 and findings[0]["declared"] == "array"
    assert findings[0]["sent"] == "object"


def test_object_body_that_refuses_for_an_array_fires(tree):
    findings = tree(_block("array_refusal"), _spec(OBJECT))
    assert len(findings) == 1 and findings[0]["sent"] == "array"


def test_declared_type_comes_from_the_resolved_schema_not_the_raw_one(tree):
    """A `$ref` to the body; the raw requestBody schema has no type."""
    spec = _spec({"$ref": "#/components/schemas/Body"})
    spec["components"]["schemas"]["Body"] = OBJECT
    assert tree(_block("object"), spec) == []
    assert len(tree(_block("patch"), spec)) == 1


# --------------------------------------------------------- op_array item keys

def test_op_array_with_every_required_item_key_flagged_is_clean(tree):
    assert tree(_block("patch"), _spec(OP_ARRAY)) == []
    assert drift_check.CHECK_EXAMINED["40"] == {"examined": 1, "skipped": 0}


def test_op_array_whose_required_item_key_has_no_flag_fires(tree):
    """cc-journey update before the fix: only --value could be set."""
    findings = tree(_block("patch_op_only"), _spec(OP_ARRAY))
    assert len(findings) == 1, findings
    assert findings[0]["kind"] == "item"
    assert findings[0]["fields"] == ["op"]


def test_op_array_flag_path_that_builds_an_object_fires_the_type_rule(tree):
    findings = tree(_block("object"), _spec(OP_ARRAY))
    assert [f["kind"] for f in findings] == ["type"]


# ------------------------------------------------------------ what is exempt

def test_single_patch_op_is_skipped_and_counted(tree):
    findings = tree(_block("patch"), _spec(PATCH_OP))
    assert drift_check.CHECK_EXAMINED["40"] == {"examined": 0, "skipped": 1}
    assert findings and "error" in findings[0]          # BLIND: examined 0


def test_string_and_untyped_bodies_are_skipped_and_counted(tree):
    for schema in ({"type": "string"}, {}):
        tree(_block("object", method_call="rest_post", command="create"),
             _spec(schema, method="post", content_type="application/json"))
        assert drift_check.CHECK_EXAMINED["40"] == {"examined": 0, "skipped": 1}, schema


def test_block_with_no_recognised_flag_path_is_skipped(tree):
    tree(_block("none"), _spec(OBJECT))
    assert drift_check.CHECK_EXAMINED["40"] == {"examined": 0, "skipped": 1}


def test_block_with_no_spec_op_is_skipped_and_counted(tree):
    findings = tree(_block("object"), _spec(OBJECT, path="/elsewhere"))
    assert drift_check.CHECK_EXAMINED["40"] == {"examined": 0, "skipped": 1}
    assert len(findings) == 1 and "error" in findings[0]


def test_operation_with_no_body_is_not_examined(tree):
    spec = _spec(OBJECT)
    del spec["paths"][PATH]["patch"]["requestBody"]
    findings = tree(_block("patch"), spec)
    assert findings and "error" in findings[0]
    assert drift_check.CHECK_EXAMINED["40"] == {"examined": 0, "skipped": 0}


def test_get_blocks_are_not_examined(tree):
    findings = tree(_block("object", method_call="rest_get"), _spec(OBJECT, method="get"))
    assert findings and "error" in findings[0]
    assert drift_check.CHECK_EXAMINED["40"]["examined"] == 0


def test_put_post_and_delete_are_examined(tree):
    for method, call in (("put", "rest_put"), ("post", "rest_post"),
                         ("delete", "rest_delete")):
        findings = tree(_block("patch", method_call=call), _spec(OBJECT, method=method))
        assert len(findings) == 1, (method, findings)


def test_two_specs_that_disagree_do_not_fire(tree):
    """A finding needs every declaring spec's reading to fail."""
    assert tree(_block("object"), _spec(OBJECT), _spec(STRINGS)) == []


# --------------------------------------------------------- registered + safe

def test_registered_for_printing_and_never_raises(capsys):
    assert "40" in drift_check.CHECK_PRINT
    drift_check.CHECK_EXAMINED["40"] = {"examined": 3, "skipped": 0}
    drift_check.print_check_findings("40", [{"bogus": 1}])
    out = capsys.readouterr().out
    assert out.startswith("[40] ") and "FORMAT-ERROR" in out


def test_printed_line_names_the_command_and_both_types(capsys, tree):
    drift_check.print_check_findings("40", tree(_block("patch"), _spec(OBJECT)))
    out = capsys.readouterr().out
    assert "wxcli zz-probe update" in out
    assert "object" in out and "array" in out


# ------------------------------------------- --enforce exits 1 on a planted defect

@pytest.mark.parametrize("module_src,expected_exit", [
    (_block("patch"), 1),
    (_block("object"), 0),
], ids=["planted-defect", "clean"])
def test_enforce_exit_follows_a_planted_defect(monkeypatch, capsys, tree,
                                               module_src, expected_exit):
    stub_unrelated_checks(monkeypatch)
    tree(module_src, _spec(OBJECT))     # writes the temp commands dir and specs
    real = drift_check.check_body_shape

    def planted(*a, **k):
        return real(commands_dir=tree.cmds, specs_dir=tree.specs)

    monkeypatch.setattr(drift_check, "check_body_shape", planted)
    for other in ("check_query_enum_help", "check_readonly_flags",
                  "check_composed_property_flags", "check_oneof_bodies"):
        monkeypatch.setattr(drift_check, other, lambda *a, **k: [])
    assert drift_check.main() == expected_exit
    out = capsys.readouterr().out
    assert "[40] request body shape" in out
    assert ("FAIL" if expected_exit else "PASS") in out.splitlines()[-1]
