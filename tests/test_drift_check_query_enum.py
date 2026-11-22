"""Drift gate check 36: a query option whose --help omits a spec enum value.

`parse_parameters` read `enum` off the raw schema, so the choices of a query
parameter behind a `$ref` (`pstn list-available-numbers --action`) or under
`items` (`cc-tasks list --channel-types`) never reached `--help`, and a list of
more than 12 values was replaced by "(use --help for choices)" (audit F7).

A block fires when a spec op it renders declares a query parameter whose schema
resolves (through `$ref`, and `items` for an array) to an enum, the block has an
option for it, and the option's help lacks one of the values. An option a
per-operation `param_help` override replaces is skipped and counted, never a
finding. Every fire case has a paired no-fire case, written so the check can
fail it. Synthetic specs and blocks only; nothing here reads today's upstream
content.
"""

import json
import sys

import pytest

from tools import drift_check


def _block(help_text, flag="--action", name="action", extra=""):
    return f'''
@app.command("list", short_help="List things.")
def list_things(
    {name}: str = typer.Option(None, "{flag}", help="{help_text}"),
{extra}    debug: bool = typer.Option(False, "--debug"),
):
    """List things."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/things"
    params = {{}}
    if {name} is not None:
        params["{name}"] = {name}
    result = api.session.rest_get(url, params=params)
'''


PATH = "/things"
ENUM3 = ["modifyElin", "modifyStandard", "modifyService"]


def _param(name="action", schema=None, **extra):
    return {"name": name, "in": "query",
            "schema": schema if schema is not None
            else {"$ref": "#/components/schemas/Action"}, **extra}


def _spec(params=None, path=PATH, method="get", enum=None):
    op = {"tags": ["Probe"], "operationId": "listThings",
          "summary": "List things",
          "parameters": params if params is not None else [_param()],
          "responses": {"200": {"description": "ok"}}}
    return {"components": {"schemas": {"Action": {
        "type": "string", "enum": enum or ENUM3}}},
            "paths": {path: {method: op}}}


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(module_src, *spec_list, overrides=None):
        (cmds / "zz_probe.py").write_text(module_src)
        for i, spec in enumerate(spec_list):
            name = "webex-probe.json" if i == 0 else f"webex-probe{i}.json"
            (specs / name).write_text(json.dumps(spec))
        return drift_check.check_query_enum_help(
            commands_dir=cmds, specs_dir=specs,
            operation_overrides={} if overrides is None else overrides)

    run.cmds, run.specs = cmds, specs
    return run


# ------------------------------------------------- bad block fires, good passes

def test_ref_enum_missing_from_help_fires(tree):
    findings = tree(_block("Action type for modifiable numbers."), _spec())
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["group"] == "zz-probe" and f["command"] == "list"
    assert f["op"] == f"GET {PATH}" and f["param"] == "action"
    assert f["missing"] == ENUM3 and f["array"] is False
    assert drift_check.CHECK_EXAMINED["36"] == {"examined": 1, "skipped": 0}


def test_ref_enum_listed_in_help_is_clean(tree):
    assert tree(_block("Choices: " + ", ".join(ENUM3)), _spec()) == []
    assert drift_check.CHECK_EXAMINED["36"]["examined"] == 1


def test_one_missing_value_fires_and_names_only_it(tree):
    findings = tree(_block("Choices: modifyElin, modifyStandard"), _spec())
    assert [f["missing"] for f in findings] == [["modifyService"]]


def test_items_enum_fires_and_is_marked_array(tree):
    spec = _spec(params=[_param(name="channelTypes", schema={
        "type": "array", "items": {"enum": ["email", "chat"]}})])
    block = _block("Channel types.", flag="--channel-types", name="channel_types")
    findings = tree(block, spec)
    assert len(findings) == 1
    assert findings[0]["array"] is True and findings[0]["missing"] == ["email", "chat"]


def test_items_enum_listed_comma_separated_is_clean(tree):
    spec = _spec(params=[_param(name="channelTypes", schema={
        "type": "array", "items": {"enum": ["email", "chat"]}})])
    block = _block("Choices (comma-separated): email, chat",
                   flag="--channel-types", name="channel_types")
    assert tree(block, spec) == []


def test_inline_enum_counts_too(tree):
    spec = _spec(params=[_param(schema={"type": "string", "enum": ["a", "b"]})])
    assert len(tree(_block("Pick one."), spec)) == 1
    assert tree(_block("Choices: a, b"), spec) == []


def test_over_twelve_values_must_all_be_listed(tree):
    values = [f"value{i}" for i in range(13)]
    spec = _spec(enum=values)
    old_style = _block("Some words. (use --help for choices)")
    assert len(tree(old_style, spec)[0]["missing"]) == 13
    assert tree(_block("Some words. Choices: " + ", ".join(values)), spec) == []


def test_comparison_ignores_case(tree):
    """The renderer folds case variants of one value into one; the check must
    not call that a missing choice."""
    spec = _spec(enum=["Active", "ACTIVE", "inactive"])
    assert tree(_block("Choices: Active, inactive"), spec) == []


def test_help_with_escaped_quote_is_read(tree):
    spec = _spec(enum=['say "hi"'])
    assert tree(_block('Choices: say \\"hi\\"'), spec) == []


# ---------------------------------------------------- what is out of population

def test_param_without_an_option_is_not_examined(tree):
    """An auto-injected or paging parameter has no option; nothing to judge."""
    spec = _spec(params=[_param(), _param(name="other", schema={
        "type": "string", "enum": ["x"]})])
    assert tree(_block("Choices: " + ", ".join(ENUM3)), spec) == []
    assert drift_check.CHECK_EXAMINED["36"]["examined"] == 1


def test_param_without_an_enum_is_not_examined(tree):
    spec = _spec(params=[_param(schema={"type": "string"}), _param(
        name="b", schema={"type": "array", "items": {"type": "string"}})])
    findings = tree(_block("Anything."), spec)
    assert findings and "error" in findings[0]          # BLIND: examined 0
    assert drift_check.CHECK_EXAMINED["36"]["examined"] == 0


def test_param_help_override_is_skipped_and_counted(tree):
    """`param_help` replaces the help by design: never a finding."""
    extra = ('    kind: str = typer.Option(None, "--kind", '
             'help="Choices: a, b"),\n')
    spec = _spec(params=[_param(), _param(
        name="kind", schema={"type": "string", "enum": ["a", "b"]})])
    overrides = {"webex-probe.json": {
        f"GET {PATH}": {"param_help": {"action": "Plain words, by design."}}}}
    findings = tree(_block("Plain words, by design.", extra=extra), spec,
                    overrides=overrides)
    assert findings == []
    assert drift_check.CHECK_EXAMINED["36"] == {"examined": 1, "skipped": 1}


def test_without_the_override_the_same_block_fires(tree):
    extra = ('    kind: str = typer.Option(None, "--kind", '
             'help="Choices: a, b"),\n')
    spec = _spec(params=[_param(), _param(
        name="kind", schema={"type": "string", "enum": ["a", "b"]})])
    findings = tree(_block("Plain words, by design.", extra=extra), spec)
    assert [f["param"] for f in findings] == ["action"]


def test_block_with_no_spec_op_is_skipped_and_counted(tree):
    findings = tree(_block("x"), _spec(path="/elsewhere"))
    assert drift_check.CHECK_EXAMINED["36"] == {"examined": 0, "skipped": 1}
    assert len(findings) == 1 and "error" in findings[0]   # blind, gated


def test_any_satisfied_spec_passes(tree):
    """A path two specs declare passes when one spec's reading is satisfied
    (under-report rather than fail a correct command)."""
    wide = _spec(enum=ENUM3)
    narrow = _spec(enum=["modifyElin"])
    assert tree(_block("Choices: modifyElin"), wide, narrow) == []
    assert len(tree(_block("Words."), wide, narrow)) == 1


# --------------------------------------------------------- registered + safe

def test_registered_for_printing_and_never_raises(capsys):
    assert "36" in drift_check.CHECK_PRINT
    drift_check.CHECK_EXAMINED["36"] = {"examined": 3, "skipped": 0}
    drift_check.print_check_findings("36", [{"bogus": 1}])
    out = capsys.readouterr().out
    assert out.startswith("[36] ") and "FORMAT-ERROR" in out


def test_printed_line_names_the_command_flag_and_values(capsys, tree):
    findings = tree(_block("Words."), _spec())
    drift_check.print_check_findings("36", findings)
    out = capsys.readouterr().out
    assert "wxcli zz-probe list --action" in out and "modifyElin" in out


# ------------------------------------------- --enforce exits 1 on a planted defect

def stub_unrelated_checks(monkeypatch):
    """Everything main() runs that these tests have no opinion about, stubbed
    the way tests/test_drift_check_untracked.py does, so `--enforce` varies
    only with the check under test. Also used by test_drift_check_readonly.py."""
    monkeypatch.setattr(drift_check, "load_overrides",
                        lambda: {"skip_tags": {}, "skip_reasons": {}, "keep_endpoints": []})
    monkeypatch.setattr(drift_check, "load_spec_ops", lambda _skip: ({}, {}))
    monkeypatch.setattr(drift_check, "build_cli_surface", lambda: ({}, set()))
    monkeypatch.setattr(drift_check, "build_flag_surface", lambda: {})
    monkeypatch.setattr(drift_check, "distinct_command_sets", lambda: 0)
    monkeypatch.setattr(drift_check, "check_parity",
                        lambda *a: {"missing_from_cli": [], "cli_ahead_of_spec": []})
    monkeypatch.setattr(drift_check, "check_references", lambda *a: ([], {}, 0))
    monkeypatch.setattr(drift_check, "check_counts", lambda *a: [])
    monkeypatch.setattr(drift_check, "check_unreferenced", lambda *a: [])
    monkeypatch.setattr(drift_check, "check_overlays", lambda: [])
    monkeypatch.setattr(drift_check, "check_flags", lambda *a: [])
    monkeypatch.setattr(drift_check, "check_prose_flags", lambda *a: [])
    monkeypatch.setattr(drift_check, "check_untracked_modules", lambda: [])
    monkeypatch.setattr(drift_check, "check_table_columns", lambda **_: ([], [], []))
    monkeypatch.setattr(drift_check, "build_positional_surface", lambda: {})
    monkeypatch.setattr(drift_check, "check_positionals", lambda *a: ([], []))
    monkeypatch.setattr(drift_check, "build_required_surface", lambda: {})
    monkeypatch.setattr(drift_check, "check_required_flags", lambda *a: ([], []))
    monkeypatch.setattr(drift_check, "build_arg_kind_surface", lambda: {})
    monkeypatch.setattr(drift_check, "check_arg_kinds", lambda *a: ([], [], []))
    monkeypatch.setattr(drift_check, "build_naming_findings", lambda: [])
    monkeypatch.setattr(drift_check, "check_naming", lambda *a: ([], [], []))
    monkeypatch.setattr(drift_check, "check_generated_help", lambda: ([], []))
    monkeypatch.setattr(drift_check, "check_inert_overrides", lambda: ([], []))
    monkeypatch.setattr(drift_check, "check_undeclared_paging", lambda: ([], []))
    monkeypatch.setattr(drift_check, "check_registry_counts", lambda: [])
    monkeypatch.setattr(drift_check, "check_reference_doc_shape", lambda: ([], []))
    monkeypatch.setattr(drift_check, "check_spec_semantics", lambda: ([], [], []))
    monkeypatch.setattr(drift_check, "check_reference_doc_coverage", lambda: [])
    monkeypatch.setattr(drift_check, "check_doc_value_types", lambda *a, **k: [])
    monkeypatch.setattr(drift_check, "check_doc_body_keys", lambda *a, **k: ([], 0))
    monkeypatch.setattr(drift_check, "check_command_map", lambda *a, **k: [])
    monkeypatch.setattr(sys, "argv", ["drift_check.py", "--enforce"])


@pytest.mark.parametrize("module_src,expected_exit", [
    (_block("Action type for modifiable numbers."), 1),
    (_block("Choices: " + ", ".join(ENUM3)), 0),
])
def test_enforce_exit_follows_a_planted_defect(monkeypatch, capsys, tree,
                                               module_src, expected_exit):
    stub_unrelated_checks(monkeypatch)
    tree(module_src, _spec())      # writes the temp commands dir and specs

    real = drift_check.check_query_enum_help

    def planted(*a, **k):
        return real(commands_dir=tree.cmds, specs_dir=tree.specs,
                    operation_overrides={})

    monkeypatch.setattr(drift_check, "check_query_enum_help", planted)
    monkeypatch.setattr(drift_check, "check_readonly_flags", lambda *a, **k: [])
    assert drift_check.main() == expected_exit
    out = capsys.readouterr().out
    assert "[36] query options whose --help omits a choice" in out
    assert ("FAIL" if expected_exit else "PASS") in out.splitlines()[-1]
