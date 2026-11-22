"""Drift gate check 38: a composed object/array body property rendered as a text flag.

`parse_request_body` typed a property declared only by composition
(`allOf: [{$ref: <object>}]`) as "string", so `ai-receptionist create` offered
`--default-action DEFAULT_ACTION` and wrote the text where the API wants an
object (audit F2). For every `body["<name>"] = <option>` write whose option is a
scalar `typer.Option`, the spec property is resolved through `$ref`, `allOf`,
`oneOf` and `anyOf`; one that resolves to an object or an array fires. A
resolved enum missing from the option's help is an ADVISORY line, never a
failure. Every fire case has a paired no-fire case. Synthetic specs and blocks
only; nothing here reads today's upstream content.
"""

import json

import pytest

from tools import drift_check
from tests.test_drift_check_query_enum import stub_unrelated_checks


PATH = "/org/{orgid}/thing"

BAD = '''
@app.command("create", short_help="Create a new Thing.")
def create(
    name: str = typer.Option(None, "--name", help="(required) The name."),
    default_action: str = typer.Option(None, "--default-action", help="(required) Default action configuration."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Thing."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/org/{orgid}/thing"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if default_action is not None:
            body["defaultAction"] = default_action
    result = api.session.rest_post(url, json=body)
'''

GOOD = BAD.replace(
    '    default_action: str = typer.Option(None, "--default-action", help="(required) Default action configuration."),\n',
    "").replace(
    '        if default_action is not None:\n            body["defaultAction"] = default_action\n', "")


def _spec(prop, method="post", path=PATH, schemas=None, extra_props=None):
    props = {"name": {"type": "string"}, "defaultAction": prop}
    props.update(extra_props or {})
    op = {"tags": ["Probe"], "operationId": "createThing",
          "parameters": [{"name": "orgid", "in": "path", "required": True,
                          "schema": {"type": "string"}}],
          "requestBody": {"content": {"application/json": {"schema": {
              "type": "object", "properties": props}}}},
          "responses": {"200": {"description": "ok"}}}
    schemas = {"Obj": {"type": "object", "properties": {"a": {"type": "string"}}},
               "Arr": {"type": "array", "items": {"type": "string"}},
               "Mode": {"type": "string", "enum": ["ONE", "TWO"]},
               **(schemas or {})}
    return {"components": {"schemas": schemas}, "paths": {path: {method: op}}}


ALLOF_OBJ = {"description": "d", "allOf": [{"$ref": "#/components/schemas/Obj"}]}


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
        return drift_check.check_composed_property_flags(
            commands_dir=cmds, specs_dir=specs)

    run.cmds, run.specs = cmds, specs
    return run


# ------------------------------------------------- bad block fires, good passes

def test_allof_object_flag_fires(tree):
    findings = tree(BAD, _spec(ALLOF_OBJ))
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["group"] == "zz-probe" and f["command"] == "create"
    assert f["field"] == "defaultAction" and f["flag"] == "--default-action"
    assert f["shape"] == "object" and f["op"] == f"POST {PATH}"
    assert drift_check.CHECK_EXAMINED["38"] == {"examined": 2, "skipped": 0}


def test_flagless_block_is_clean(tree):
    assert tree(GOOD, _spec(ALLOF_OBJ)) == []
    assert drift_check.CHECK_EXAMINED["38"]["examined"] == 1


@pytest.mark.parametrize("prop,shape", [
    ({"$ref": "#/components/schemas/Obj"}, "object"),
    ({"allOf": [{"$ref": "#/components/schemas/Obj"}]}, "object"),
    ({"oneOf": [{"$ref": "#/components/schemas/Obj"},
                {"$ref": "#/components/schemas/Obj"}]}, "object"),
    ({"anyOf": [{"$ref": "#/components/schemas/Obj"}]}, "object"),
    ({"$ref": "#/components/schemas/Arr"}, "array"),
    ({"allOf": [{"$ref": "#/components/schemas/Arr"}]}, "array"),
    ({"type": "array", "items": {"type": "string"}}, "array"),
    ({"type": "object", "properties": {"a": {"type": "string"}}}, "object"),
])
def test_object_or_array_through_any_composition_fires(tree, prop, shape):
    findings = tree(BAD, _spec(prop))
    assert [f["shape"] for f in findings] == [shape]


@pytest.mark.parametrize("prop", [
    {"type": "string"},
    {"$ref": "#/components/schemas/Mode"},
    {"allOf": [{"$ref": "#/components/schemas/Mode"}], "description": "d"},
    {"oneOf": [{"type": "string"}, {"type": "integer"}]},
])
def test_scalar_through_any_composition_is_clean(tree, prop):
    assert tree(BAD, _spec(prop)) == []


def test_property_declared_in_a_oneof_body_branch_is_found(tree):
    spec = _spec({"type": "string"})
    body = spec["paths"][PATH]["post"]["requestBody"]["content"]["application/json"]
    body["schema"] = {"oneOf": [
        {"type": "object", "properties": {"name": {"type": "string"}}},
        {"type": "object", "properties": {"defaultAction": ALLOF_OBJ}}]}
    assert [f["field"] for f in tree(BAD, spec)] == ["defaultAction"]


def test_put_and_patch_are_examined(tree):
    for method, call in (("put", "rest_put"), ("patch", "rest_patch")):
        findings = tree(BAD.replace("rest_post", call), _spec(ALLOF_OBJ, method=method))
        assert len(findings) == 1, (method, findings)


# ---------------------------------------------------- what must NOT fire

def test_get_blocks_are_not_examined(tree):
    findings = tree(BAD.replace("rest_post(url, json=body)", "rest_get(url)"),
                    _spec(ALLOF_OBJ, method="get"))
    assert findings and "error" in findings[0]          # BLIND: examined 0
    assert drift_check.CHECK_EXAMINED["38"]["examined"] == 0


def test_block_with_no_spec_op_is_skipped_and_counted(tree):
    findings = tree(BAD, _spec(ALLOF_OBJ, path="/elsewhere"))
    assert drift_check.CHECK_EXAMINED["38"] == {"examined": 0, "skipped": 1}
    assert len(findings) == 1 and "error" in findings[0]


def test_disagreeing_specs_do_not_fire(tree):
    """Fires only when every declaring spec reads the property as an object."""
    assert tree(BAD, _spec(ALLOF_OBJ), _spec({"type": "string"})) == []
    assert len(tree(BAD, _spec(ALLOF_OBJ), _spec(ALLOF_OBJ))) == 1


def test_a_write_of_a_property_the_spec_lacks_is_counted_not_fired(tree):
    spec = _spec({"type": "string"})
    spec["paths"][PATH]["post"]["requestBody"]["content"]["application/json"][
        "schema"]["properties"].pop("defaultAction")
    assert tree(BAD, spec) == []
    assert drift_check.CHECK_EXAMINED["38"]["examined"] == 1


# ------------------------------------------------- the enum advisory

def test_enum_missing_from_help_is_an_advisory_not_a_failure(tree):
    spec = _spec({"allOf": [{"$ref": "#/components/schemas/Mode"}]})
    assert tree(BAD, spec) == []
    adv = drift_check.CHECK_ADVISORIES["38"]
    assert len(adv) == 1
    assert adv[0]["flag"] == "--default-action" and adv[0]["missing"] == ["ONE", "TWO"]


def test_enum_listed_in_help_has_no_advisory(tree):
    spec = _spec({"allOf": [{"$ref": "#/components/schemas/Mode"}]})
    block = BAD.replace("Default action configuration.", "Choices: one, TWO")
    assert tree(block, spec) == []
    assert drift_check.CHECK_ADVISORIES["38"] == []


def test_plain_inline_enum_is_not_part_of_the_advisory(tree):
    spec = _spec({"type": "string", "enum": ["ONE"]})
    assert tree(BAD, spec) == []
    assert drift_check.CHECK_ADVISORIES["38"] == []


# ------------------------------------------------ field_shape resolves composition

def test_field_shape_resolves_allof_oneof_anyof():
    spec = _spec(ALLOF_OBJ)
    op = spec["paths"][PATH]["post"]
    assert drift_check.field_shape(op, spec, "defaultAction") == "object"
    for key, member in (("oneOf", "Obj"), ("anyOf", "Arr")):
        op["requestBody"]["content"]["application/json"]["schema"][
            "properties"]["defaultAction"] = {
                key: [{"$ref": f"#/components/schemas/{member}"}]}
        want = "object" if member == "Obj" else "array"
        assert drift_check.field_shape(op, spec, "defaultAction") == want
    op["requestBody"]["content"]["application/json"]["schema"]["properties"][
        "defaultAction"] = {"allOf": [{"$ref": "#/components/schemas/Mode"}]}
    assert drift_check.field_shape(op, spec, "defaultAction") == "scalar"


# --------------------------------------------------------- registered + safe

def test_registered_for_printing_and_never_raises(capsys):
    assert "38" in drift_check.CHECK_PRINT
    drift_check.CHECK_EXAMINED["38"] = {"examined": 3, "skipped": 0}
    drift_check.print_check_findings("38", [{"bogus": 1}])
    out = capsys.readouterr().out
    assert out.startswith("[38] ") and "FORMAT-ERROR" in out


def test_printed_line_names_the_command_and_flag(capsys, tree):
    drift_check.print_check_findings("38", tree(BAD, _spec(ALLOF_OBJ)))
    out = capsys.readouterr().out
    assert "wxcli zz-probe create" in out and "--default-action" in out


# ------------------------------------------- --enforce exits 1 on a planted defect

@pytest.mark.parametrize("module_src,expected_exit", [(BAD, 1), (GOOD, 0)],
                         ids=["planted-defect", "clean"])
def test_enforce_exit_follows_a_planted_defect(monkeypatch, capsys, tree,
                                               module_src, expected_exit):
    stub_unrelated_checks(monkeypatch)
    tree(module_src, _spec(ALLOF_OBJ))      # writes the temp commands dir and specs
    real = drift_check.check_composed_property_flags

    def planted(*a, **k):
        return real(commands_dir=tree.cmds, specs_dir=tree.specs)

    monkeypatch.setattr(drift_check, "check_composed_property_flags", planted)
    for other in ("check_query_enum_help", "check_readonly_flags", "check_oneof_bodies"):
        monkeypatch.setattr(drift_check, other, lambda *a, **k: [])
    assert drift_check.main() == expected_exit
    out = capsys.readouterr().out
    assert "[38] composed body properties rendered as a text flag" in out
    assert ("FAIL" if expected_exit else "PASS") in out.splitlines()[-1]
