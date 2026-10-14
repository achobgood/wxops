"""Drift gate check 29: a documented value whose type contradicts the spec.

`contact-center-core.md` documented `wxcli cc-agents list-activities --from
"2026-03-01T00:00:00Z"`, but the spec declares `from` as integer/int64 (epoch
milliseconds), so the example could only fail. Checks 6/10/11 judge flag
names, argument counts and presence; nothing compared a documented VALUE with
the type the spec declares for it.

For each documented invocation, `--flag value` pairs are mapped to query
params through flag_query_map, and top-level keys of an inline `--json-body
'{…}'` are looked up in body_schema. When the spec type is integer/number (or
format int64/int32), the value must be a number. Placeholders never fire
(Review Focus 2).

Every fire case has a paired no-fire case, written so the check can fail it.
"""

import json

import pytest

from tools import drift_check


BLOCK = '''
@app.command("list-activities", short_help="Get Agent Activities.")
def list_activities(
    from_param: int = typer.Option(..., "--from", help="Start time, epoch ms."),
    to: int = typer.Option(..., "--to", help="End time, epoch ms."),
    channel: str = typer.Option(None, "--channel", help="Channel type."),
    output: str = typer.Option("table", "--output", "-o"),
):
    """Get Agent Activities."""
    url = f"https://webexapis.com/v1/zz/agents/activities"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if channel is not None:
        params["channel"] = channel
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    emit(result, output)
'''

BODY_BLOCK = '''
@app.command("update-skill")
def update_skill(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body."),
):
    """Update a skill."""
    url = f"https://webexapis.com/v1/zz/skills"
    body = json.loads(json_body) if json_body else {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
'''

INT64 = {"type": "integer", "format": "int64"}
STR = {"type": "string"}


def _qparam(name, schema):
    return {"name": name, "in": "query", "schema": schema}


def _get_spec(from_schema=INT64, to_schema=INT64, components=None):
    spec = {"paths": {"/zz/agents/activities": {"get": {
        "parameters": [_qparam("from", from_schema), _qparam("to", to_schema),
                       _qparam("channel", STR)],
        "responses": {"200": {"description": "ok"}}}}}}
    if components:
        spec["components"] = {"schemas": components}
    return spec


def _put_spec(props):
    return {"paths": {"/zz/skills": {"put": {
        "requestBody": {"content": {"application/json": {"schema": {
            "type": "object", "properties": props}}}},
        "responses": {"200": {"description": "ok"}}}}}}


def _inv(tokens, command="list-activities", group="zz-probe", line=118):
    return {"file": "docs/reference/zz.md", "line": line, "group": group,
            "command": command, "tokens": tokens, "in_code": True,
            "prefixless": False, "sig": {}}


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(invocations, *spec_list, module_src=BLOCK, registrations=None):
        (cmds / "zz_probe.py").write_text(module_src)
        for i, spec in enumerate(spec_list):
            name = "webex-probe.json" if i == 0 else f"webex-probe{i}.json"
            (specs / name).write_text(json.dumps(spec))
        return drift_check.check_doc_value_types(
            invocations, drift_check.iter_command_blocks(cmds),
            drift_check.spec_ops_by_key(specs),
            registrations=registrations or {})

    return run


# ------------------------------------------------------- the 2026-03 bug

def test_iso_date_for_int64_flag_fires(tree):
    """`cc-agents list-activities --from "2026-03-01T00:00:00Z"` before the
    fix: the spec declares `from` as integer/int64 epoch ms."""
    findings = tree([_inv(["--from", "2026-03-01T00:00:00Z",
                           "--to", "1791849600000"])], _get_spec())
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["where"] == "--from"
    assert f["value"] == "2026-03-01T00:00:00Z"
    assert f["expected"] == "integer (int64)"
    assert (f["file"], f["line"]) == ("docs/reference/zz.md", 118)
    assert (f["group"], f["command"]) == ("zz-probe", "list-activities")


def test_epoch_value_passes(tree):
    """The fix: epoch milliseconds."""
    assert tree([_inv(["--from", "1791763200000", "--to", "1791849600000"])],
                _get_spec()) == []
    assert drift_check.CHECK_EXAMINED["29"] == {"examined": 1, "skipped": 0}


def test_equals_form_fires(tree):
    findings = tree([_inv(["--from=2026-03-01", "--to", "1"])], _get_spec())
    assert [(f["where"], f["value"]) for f in findings] == [
        ("--from", "2026-03-01")]


def test_string_typed_param_passes_an_iso_date(tree):
    """Paired with the fire case: the same value is right when the spec
    declares a string."""
    assert tree([_inv(["--from", "2026-03-01T00:00:00Z"])],
                _get_spec(from_schema=STR)) == []


def test_flag_feeding_a_string_param_never_fires(tree):
    assert tree([_inv(["--channel", "2026-03-01", "--from", "1"])],
                _get_spec()) == []


def test_ref_param_schema_is_resolved(tree):
    spec = _get_spec(from_schema={"$ref": "#/components/schemas/Epoch"},
                     components={"Epoch": INT64})
    findings = tree([_inv(["--from", "2026-03-01"])], spec)
    assert [f["where"] for f in findings] == ["--from"]


@pytest.mark.parametrize("value", [
    "FROM_PARAM", "<epoch-ms>", "$FROM", "...", "{{from}}", "epoch-ms",
    "$(date +%s000)", "`date`"])
def test_placeholders_never_fire(tree, value):
    assert tree([_inv(["--from", value])], _get_spec()) == []
    assert drift_check.CHECK_EXAMINED["29"]["examined"] == 1


@pytest.mark.parametrize("value", ["true", "false", "True"])
def test_literal_boolean_for_integer_flag_fires(tree, value):
    """A literal boolean is a value, never a placeholder — the no-digit
    exemption must not swallow it (`cc-tasks list --limit true`)."""
    findings = tree([_inv(["--from", value])], _get_spec())
    assert [(f["where"], f["value"]) for f in findings] == [("--from", value)]


def test_literal_boolean_for_string_flag_passes(tree):
    assert tree([_inv(["--from", "true"])], _get_spec(from_schema=STR)) == []


def test_two_specs_one_string_does_not_fire(tree):
    """A path two specs declare fires only when no spec types the name as
    non-numeric — under-report rather than fail a command one spec describes
    differently."""
    findings = tree([_inv(["--from", "2026-03-01"])],
                    _get_spec(), _get_spec(from_schema=STR))
    assert findings == []


def test_two_specs_both_numeric_fires(tree):
    findings = tree([_inv(["--from", "2026-03-01"])], _get_spec(), _get_spec())
    assert [f["where"] for f in findings] == ["--from"]


def test_duplicate_citation_on_one_line_reported_once(tree):
    inv = _inv(["--from", "2026-03-01"])
    assert len(tree([inv, dict(inv)], _get_spec())) == 1


# ------------------------------------------------------------ --json-body

def test_json_body_integer_key_with_string_fires(tree):
    findings = tree(
        [_inv(["--json-body", '{"skillValue": "8 points", "name": "x"}'],
              command="update-skill")],
        _put_spec({"skillValue": {"type": "integer"}, "name": STR}),
        module_src=BODY_BLOCK)
    assert len(findings) == 1, findings
    assert findings[0]["where"] == "--json-body skillValue"
    assert findings[0]["value"] == "8 points"
    assert findings[0]["expected"] == "integer"


def test_json_body_integer_key_with_number_passes(tree):
    assert tree(
        [_inv(["--json-body", '{"skillValue": 8, "name": "2026-03-01"}'],
              command="update-skill")],
        _put_spec({"skillValue": {"type": "integer"}, "name": STR}),
        module_src=BODY_BLOCK) == []


@pytest.mark.parametrize("value", ['"8"', '"SKILL_VALUE"', '"<n>"', "null"])
def test_json_body_numeric_string_or_placeholder_passes(tree, value):
    assert tree(
        [_inv(["--json-body", '{"skillValue": %s}' % value],
              command="update-skill")],
        _put_spec({"skillValue": {"type": "integer"}}),
        module_src=BODY_BLOCK) == []


@pytest.mark.parametrize("body", [
    "file://skill.json", "$(cat skill.json)", "@skill.json",
    '{"skillValue": ...}'])
def test_unparseable_json_body_is_skipped_and_counted(tree, body):
    assert tree([_inv(["--json-body", body], command="update-skill")],
                _put_spec({"skillValue": {"type": "integer"}}),
                module_src=BODY_BLOCK) == []
    assert drift_check.CHECK_EXAMINED["29"] == {"examined": 1, "skipped": 1}


def test_json_body_string_boolean_for_integer_key_fires(tree):
    findings = tree(
        [_inv(["--json-body", '{"skillValue": "true"}'], command="update-skill")],
        _put_spec({"skillValue": {"type": "integer"}}), module_src=BODY_BLOCK)
    assert [f["where"] for f in findings] == ["--json-body skillValue"]


@pytest.mark.parametrize("odd", [["not", "a", "dict"], "schema", 7])
def test_non_dict_body_schema_is_skipped_never_raised(tree, monkeypatch, odd):
    """body_schema returning a truthy non-dict must not crash the gate (a
    crash exits 2 and fails the unattended run)."""
    monkeypatch.setattr(drift_check, "body_schema", lambda op, spec: odd)
    assert tree(
        [_inv(["--json-body", '{"skillValue": "x1"}'], command="update-skill")],
        _put_spec({"skillValue": {"type": "integer"}}),
        module_src=BODY_BLOCK) == []
    assert drift_check.CHECK_EXAMINED["29"]["examined"] == 1


# ------------------------------------------------- resolution and blindness

def test_alias_group_resolves_through_registrations(tree):
    findings = tree([_inv(["--from", "2026-03-01"], group="zz-alias")],
                    _get_spec(), registrations={"zz-alias": "zz_probe"})
    assert [f["group"] for f in findings] == ["zz-alias"]


def test_unresolved_invocation_is_skipped_and_counted(tree):
    findings = tree([_inv(["--from", "2026-03-01"], command="no-such"),
                     _inv(["--from", "1"])], _get_spec())
    assert findings == []
    assert drift_check.CHECK_EXAMINED["29"] == {"examined": 1, "skipped": 1}


def test_nothing_examined_is_blind(tree):
    findings = tree([_inv(["--from", "2026-03-01"], command="no-such")],
                    _get_spec())
    assert len(findings) == 1 and "examined 0" in findings[0]["error"]


def test_visible_name_of_stacked_alias_has_a_signature(tmp_path):
    """A renamed command stacks its hidden alias FIRST. The positional
    surface keyed only the first decorator, so `doc_invocations` never saw a
    citation of the visible name (`cc-agents list-activities`)."""
    (tmp_path / "zz_probe.py").write_text(
        BLOCK.replace('@app.command("list-activities"',
                      '@app.command("list", hidden=True)\n'
                      '@app.command("list-activities"'))
    sigs = drift_check.parse_module_signatures("zz_probe", commands_dir=tmp_path)
    assert {"list", "list-activities"} <= set(sigs)
    assert sigs["list-activities"]["flags"]["--from"] is True


# ------------------------------------------- help strings ending in a backslash

# `help="…\\"` closes its string. A scanner that reads every quote after a
# backslash as escaped handed flag_query_map None, and check 29 crashed
# (exit 2) on the block of every resolved invocation.
_BACKSLASH_BLOCK = BLOCK.replace('help="Start time, epoch ms."',
                                 r'help="Start time, epoch ms. C:\\"')


def test_backslash_help_string_does_not_crash_and_still_fires(tree):
    assert r'C:\\"' in _BACKSLASH_BLOCK
    findings = tree([_inv(["--from", "2026-03-01T00:00:00Z", "--to", "1"])],
                    _get_spec(), module_src=_BACKSLASH_BLOCK)
    assert [(f["where"], f["value"]) for f in findings] == [
        ("--from", "2026-03-01T00:00:00Z")]


def test_backslash_help_string_epoch_value_passes(tree):
    assert tree([_inv(["--from", "1791763200000", "--to", "1"])],
                _get_spec(), module_src=_BACKSLASH_BLOCK) == []


# ---------------------------------------------------------------- live tree

def test_live_tree_is_clean():
    surface, _ = drift_check.build_cli_surface()
    positional = drift_check.build_positional_surface()
    findings = drift_check.check_doc_value_types(
        list(drift_check.doc_invocations(surface, positional)),
        drift_check.iter_command_blocks(), drift_check.spec_ops_by_key())
    assert findings == []
    assert drift_check.CHECK_EXAMINED["29"]["examined"] > 1000
