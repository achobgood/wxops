"""Drift gate check 39: a `oneOf`/`anyOf` request body read as if it were `allOf`.

`_resolve_schema_node` merged the branches of a top-level `oneOf` body with
`dict.update` and concatenated their `required` lists, so `cc-agent-summaries
create` demanded `--interaction-id` AND `--agent-ci-user-id` together and its
`--search-type` offered only the last branch's value (audit F3). For a write
whose request body is a top-level `oneOf`/`anyOf`:

  (a) the rendered `_missing = [...]` must be a subset of the INTERSECTION of
      the branches' required fields;
  (b) every enum that varies by branch must be fully listed in the option's help;
  (c) the skeleton and the `Example: ... --json-body '<minimal>'` must equal
      `_schema_to_example` of the FIRST branch, never a mix.

Every fire case has a paired no-fire case. Synthetic specs and blocks only.
"""

import json

import pytest

from tools import drift_check
from tests.test_drift_check_query_enum import stub_unrelated_checks


PATH = "/org/{orgid}/search"

FULL = {"orgId": "...", "searchType": "ORGANIZATION", "note": "..."}
MINIMAL = {"orgId": "...", "searchType": "ORGANIZATION"}


def _block(missing=("orgId", "searchType"),
           help_text="(required) Choices: ORGANIZATION, INTERACTION, AGENT",
           skeleton=FULL, example=MINIMAL, method_call="rest_post"):
    """One rendered module: skeleton constant, then the command, laid out the
    way the renderer writes it (the docstring's newlines are the two characters
    backslash-n in the source)."""
    ex = ("" if example is None else
          "\\n\\n\\b\\nExample: wxcli zz-probe create --json-body '"
          + json.dumps(example, separators=(",", ":")) + "'")
    return f'''
_BODY_SKELETON_CREATE = '{json.dumps(skeleton, separators=(",", ":"))}'

@app.command("create", short_help="Search.")
def create(
    org_id: str = typer.Option(None, "--org-id", help="(required) The org."),
    search_type: str = typer.Option(None, "--search-type", help="{help_text}"),
    interaction_id: str = typer.Option(None, "--interaction-id", help="The interaction."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search.{ex}"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/org/{{orgid}}/search"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {{}}
        if org_id is not None:
            body["orgId"] = org_id
        if search_type is not None:
            body["searchType"] = search_type
        if interaction_id is not None:
            body["interactionId"] = interaction_id
        _missing = [f for f in {list(missing)!r} if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    result = api.session.{method_call}(url, json=body)
'''


def _branch(extra_required, search_type, extra_props=None):
    props = {"orgId": {"type": "string"},
             "searchType": {"type": "string", "enum": [search_type]}}
    props.update({e: {"type": "string"} for e in extra_required})
    props.update(extra_props or {})
    return {"type": "object",
            "required": ["orgId", *extra_required, "searchType"],
            "properties": props}


def _spec(key="oneOf", method="post", path=PATH, branches=None):
    schemas = {
        "Org": _branch([], "ORGANIZATION", {"note": {"type": "string"}}),
        "Inter": _branch(["interactionId"], "INTERACTION"),
        "Agent": _branch(["agentCiUserId"], "AGENT"),
    }
    members = branches or [{"$ref": f"#/components/schemas/{n}"}
                           for n in ("Org", "Inter", "Agent")]
    op = {"tags": ["Probe"], "operationId": "search",
          "parameters": [{"name": "orgid", "in": "path", "required": True,
                          "schema": {"type": "string"}}],
          "requestBody": {"content": {"application/json": {"schema": {key: members}}}},
          "responses": {"200": {"description": "ok"}}}
    return {"components": {"schemas": schemas}, "paths": {path: {method: op}}}


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
        return drift_check.check_oneof_bodies(commands_dir=cmds, specs_dir=specs)

    run.cmds, run.specs = cmds, specs
    return run


# ------------------------------------------------- bad block fires, good passes

def test_correct_block_is_clean(tree):
    assert tree(_block(), _spec()) == []
    assert drift_check.CHECK_EXAMINED["39"] == {"examined": 1, "skipped": 0}


def test_required_union_fires_a(tree):
    """The pre-fix list: every field any branch requires."""
    findings = tree(_block(missing=("orgId", "searchType", "interactionId")), _spec())
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["group"] == "zz-probe" and f["command"] == "create"
    assert f["kind"] == "required" and f["fields"] == ["interactionId"]
    assert f["op"] == f"POST {PATH}"


def test_narrowed_enum_fires_b(tree):
    findings = tree(_block(help_text="(required) Choices: AGENT"), _spec())
    assert [(f["kind"], f["fields"]) for f in findings] == [
        ("enum", ["searchType: ORGANIZATION, INTERACTION"])]


def test_enum_comparison_ignores_case(tree):
    assert tree(_block(help_text="Choices: organization, interaction, agent"),
                _spec()) == []


def test_example_from_the_last_branch_fires_c(tree):
    mixed = {"orgId": "...", "searchType": "AGENT", "agentCiUserId": "..."}
    findings = tree(_block(example=mixed), _spec())
    assert [f["kind"] for f in findings] == ["example"]


def test_skeleton_from_a_mix_of_branches_fires_c(tree):
    mixed = {**FULL, "interactionId": "...", "agentCiUserId": "..."}
    findings = tree(_block(skeleton=mixed), _spec())
    assert [f["kind"] for f in findings] == ["skeleton"]


def test_block_without_a_json_body_example_checks_the_skeleton_only(tree):
    assert tree(_block(example=None), _spec()) == []


def test_missing_a_shared_required_field_is_fine(tree):
    """a is a SUBSET rule: demanding less than the intersection is allowed."""
    assert tree(_block(missing=("orgId",)), _spec()) == []


def test_anyof_is_examined_like_oneof(tree):
    assert tree(_block(), _spec(key="anyOf")) == []
    assert len(tree(_block(missing=("orgId", "interactionId")),
                    _spec(key="anyOf"))) == 1


def test_oneof_behind_a_ref_is_examined(tree):
    spec = _spec()
    schema = spec["paths"][PATH]["post"]["requestBody"]["content"][
        "application/json"]["schema"]
    spec["components"]["schemas"]["Req"] = dict(schema)
    spec["paths"][PATH]["post"]["requestBody"]["content"]["application/json"][
        "schema"] = {"$ref": "#/components/schemas/Req"}
    assert len(tree(_block(missing=("orgId", "interactionId")), spec)) == 1


def test_put_and_patch_are_examined(tree):
    for method, call in (("put", "rest_put"), ("patch", "rest_patch")):
        findings = tree(_block(missing=("orgId", "interactionId"), method_call=call),
                        _spec(method=method))
        assert len(findings) == 1, (method, findings)


# ---------------------------------------------------- what must NOT fire

def test_allof_body_is_not_examined(tree):
    spec = _spec()
    schema = spec["paths"][PATH]["post"]["requestBody"]["content"][
        "application/json"]["schema"]
    schema["allOf"] = schema.pop("oneOf")
    findings = tree(_block(missing=("orgId", "interactionId")), spec)
    assert findings and "error" in findings[0]          # BLIND: examined 0
    assert drift_check.CHECK_EXAMINED["39"]["examined"] == 0


def test_get_blocks_are_not_examined(tree):
    findings = tree(_block(method_call="rest_get"), _spec(method="get"))
    assert findings and "error" in findings[0]
    assert drift_check.CHECK_EXAMINED["39"]["examined"] == 0


def test_block_with_no_spec_op_is_skipped_and_counted(tree):
    findings = tree(_block(), _spec(path="/elsewhere"))
    assert drift_check.CHECK_EXAMINED["39"] == {"examined": 0, "skipped": 1}
    assert len(findings) == 1 and "error" in findings[0]


def test_enum_that_does_not_vary_is_not_required_in_help(tree):
    spec = _spec()
    for n in ("Inter", "Agent"):
        spec["components"]["schemas"][n]["properties"]["searchType"]["enum"] = [
            "ORGANIZATION"]
    assert tree(_block(help_text="(required) Choices: ORGANIZATION"), spec) == []


# --------------------------------------------------------- registered + safe

def test_registered_for_printing_and_never_raises(capsys):
    assert "39" in drift_check.CHECK_PRINT
    drift_check.CHECK_EXAMINED["39"] = {"examined": 3, "skipped": 0}
    drift_check.print_check_findings("39", [{"bogus": 1}])
    out = capsys.readouterr().out
    assert out.startswith("[39] ") and "FORMAT-ERROR" in out


def test_printed_line_names_the_command_and_kind(capsys, tree):
    drift_check.print_check_findings(
        "39", tree(_block(missing=("orgId", "interactionId")), _spec()))
    out = capsys.readouterr().out
    assert "wxcli zz-probe create" in out and "required" in out


# ------------------------------------------- --enforce exits 1 on a planted defect

@pytest.mark.parametrize("module_src,expected_exit", [
    (_block(missing=("orgId", "searchType", "interactionId")), 1),
    (_block(), 0),
], ids=["planted-defect", "clean"])
def test_enforce_exit_follows_a_planted_defect(monkeypatch, capsys, tree,
                                               module_src, expected_exit):
    stub_unrelated_checks(monkeypatch)
    tree(module_src, _spec())      # writes the temp commands dir and specs
    real = drift_check.check_oneof_bodies

    def planted(*a, **k):
        return real(commands_dir=tree.cmds, specs_dir=tree.specs)

    monkeypatch.setattr(drift_check, "check_oneof_bodies", planted)
    for other in ("check_query_enum_help", "check_readonly_flags",
                  "check_composed_property_flags"):
        monkeypatch.setattr(drift_check, other, lambda *a, **k: [])
    assert drift_check.main() == expected_exit
    out = capsys.readouterr().out
    assert "[39] oneOf/anyOf request bodies" in out
    assert ("FAIL" if expected_exit else "PASS") in out.splitlines()[-1]
