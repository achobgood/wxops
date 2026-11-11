"""Drift gate check 41: every non-transport `in: header` parameter of a
command's spec operation is sent (audit F4).

`parse_parameters` handled `in: path` and `in: query` only, so a header fell
through both: `meetings list-group-meetings` could not name the host by email
and `cc-agent-wellbeing create` never sent its required `X-ORGANIZATION-ID`.
For every block with a spec op, each header outside the transport set
(Authorization, Content-Type, Accept, Content-Length, TrackingId) must be one
of: written into `headers["<Name>"]` with every session call passing
`headers=`; auto-injected (`X-ORGANIZATION-ID`, required only); or an optional
`X-ORGANIZATION-ID` on one of the two operations named in
`HEADER_OPTIONAL_ORG_EXCEPTIONS`, which the check re-validates.

Every fire case has a paired no-fire case. Synthetic specs and blocks only: no
generated command function is imported or called.
"""

import json

import pytest

from tools import drift_check
from tests.test_drift_check_query_enum import stub_unrelated_checks


PATH = "/things/{thingId}"


def _block(header_lines="", call_kw="", command="show", method_call="rest_get",
           extra_call=""):
    return f'''
@app.command("{command}", short_help="Probe.")
def {command}(
    thing_id: str = typer.Argument(help="thingId"),
    host_email: str = typer.Option(None, "--host-email", help="h"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Probe."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/things/{{thing_id}}"
{header_lines}    try:
        result = api.session.{method_call}(url{call_kw})
{extra_call}    except WebexError as e:
        handle_rest_error(e)
'''


SENT = ('    headers = {}\n'
        '    if host_email is not None:\n'
        '        headers["hostEmail"] = host_email\n')
KW = ", headers=headers or None"
ORG = '    headers = {}\n    headers["X-ORGANIZATION-ID"] = get_cc_org_id(api.session)\n'


def _hp(name, required=False):
    return {"name": name, "in": "header", "required": required,
            "schema": {"type": "string"}}


def _spec(*headers, method="get", path=PATH, path_level=()):
    op = {"tags": ["Probe"], "operationId": "probe",
          "parameters": [{"name": "thingId", "in": "path", "required": True,
                          "schema": {"type": "string"}}, *headers],
          "responses": {"200": {"description": "ok"}}}
    item = {method: op}
    if path_level:
        item["parameters"] = list(path_level)
    return {"components": {"parameters": {"Host": _hp("hostEmail")}},
            "paths": {path: item}}


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(module_src, *spec_list, exceptions=None):
        (cmds / "zz_probe.py").write_text(module_src, encoding="utf-8")
        for f in specs.glob("*.json"):
            f.unlink()
        for i, spec in enumerate(spec_list):
            name = "webex-probe.json" if i == 0 else f"webex-probe{i}.json"
            (specs / name).write_text(json.dumps(spec))
        return drift_check.check_header_params(
            commands_dir=cmds, specs_dir=specs,
            exceptions={} if exceptions is None else exceptions)

    run.cmds, run.specs = cmds, specs
    return run


# ------------------------------------------------- bad block fires, good passes

def test_header_written_and_passed_is_clean(tree):
    assert tree(_block(SENT, KW), _spec(_hp("hostEmail"))) == []
    assert drift_check.CHECK_EXAMINED["41"] == {"examined": 1, "skipped": 0}


def test_dropped_header_fires(tree):
    """meetings list-group-meetings before the fix: no option, never sent."""
    findings = tree(_block(), _spec(_hp("hostEmail")))
    assert len(findings) == 1, findings
    f = findings[0]
    assert (f["group"], f["command"], f["kind"]) == ("zz-probe", "show", "dropped")
    assert f["headers"] == ["hostEmail"] and f["op"] == f"GET {PATH}"


def test_header_built_but_not_passed_fires(tree):
    findings = tree(_block(SENT, ""), _spec(_hp("hostEmail")))
    assert [f["kind"] for f in findings] == ["not-passed"]


def test_one_of_two_calls_without_headers_fires(tree):
    """A walker block calls twice; each call must carry the headers."""
    extra = "        more = api.session.rest_get(url)\n"
    findings = tree(_block(SENT, KW, extra_call=extra), _spec(_hp("hostEmail")))
    assert [f["kind"] for f in findings] == ["not-passed"]
    assert tree(_block(SENT, KW, extra_call=extra.replace("(url)", f"(url{KW})")),
                _spec(_hp("hostEmail"))) == []


def test_ref_and_path_level_headers_are_read(tree):
    spec = _spec({"$ref": "#/components/parameters/Host"})
    assert len(tree(_block(), spec)) == 1
    assert tree(_block(SENT, KW), spec) == []
    spec = _spec(path_level=[_hp("hostEmail")])
    assert len(tree(_block(), spec)) == 1
    assert tree(_block(SENT, KW), spec) == []


def test_transport_headers_are_not_examined(tree):
    spec = _spec(*[_hp(n, required=True) for n in
                   ("Authorization", "content-type", "Accept", "Content-Length",
                    "TrackingId")])
    findings = tree(_block(), spec)
    assert drift_check.CHECK_EXAMINED["41"] == {"examined": 0, "skipped": 0}
    assert findings and "error" in findings[0]          # BLIND: examined 0


def test_every_declaring_spec_must_miss_the_header(tree):
    """Two specs declare the op; only one declares the header. The CLI is
    judged against the reading it satisfies, as checks 37-39 do."""
    assert tree(_block(), _spec(_hp("hostEmail")), _spec()) == []
    assert len(tree(_block(), _spec(_hp("hostEmail")), _spec(_hp("hostEmail")))) == 1


# ------------------------------------------------------ X-ORGANIZATION-ID rules

def test_required_org_header_auto_injected_is_clean(tree):
    spec = _spec(_hp("X-ORGANIZATION-ID", required=True), method="post")
    assert tree(_block(ORG, KW, method_call="rest_post"), spec) == []


def test_required_org_header_dropped_fires(tree):
    """cc-agent-wellbeing create before the fix."""
    spec = _spec(_hp("X-ORGANIZATION-ID", required=True), method="post")
    findings = tree(_block(method_call="rest_post"), spec)
    assert [f["kind"] for f in findings] == ["dropped"]
    assert findings[0]["headers"] == ["X-ORGANIZATION-ID"]


def test_required_org_header_rendered_as_option_is_not_auto_injected(tree):
    lines = ('    headers = {}\n    if host_email is not None:\n'
             '        headers["X-ORGANIZATION-ID"] = host_email\n')
    spec = _spec(_hp("X-ORGANIZATION-ID", required=True), method="post")
    findings = tree(_block(lines, KW, method_call="rest_post"), spec)
    assert [f["kind"] for f in findings] == ["not-injected"]


def test_optional_org_header_named_in_the_exception_is_clean(tree):
    spec = _spec(_hp("X-ORGANIZATION-ID"))
    assert tree(_block(), spec,
                exceptions={("GET", PATH): "live_f4_headers_round3.md"}) == []
    assert drift_check.CHECK_EXAMINED["41"] == {"examined": 1, "skipped": 0}


def test_optional_org_header_outside_the_exception_fires(tree):
    """The exception cannot cover a third operation."""
    spec = _spec(_hp("X-ORGANIZATION-ID"))
    findings = tree(_block(), spec,
                    exceptions={("GET", "/other"): "live_f4_headers_round3.md"})
    kinds = sorted(f["kind"] for f in findings)
    assert kinds == ["dropped", "stale-exception"]


def test_exception_whose_header_became_required_is_stale(tree):
    spec = _spec(_hp("X-ORGANIZATION-ID", required=True), method="post")
    findings = tree(_block(ORG, KW, method_call="rest_post"), spec,
                    exceptions={("POST", PATH): "live_f4_headers_round3.md"})
    assert [f["kind"] for f in findings] == ["stale-exception"]


def test_shipped_exception_names_exactly_the_two_round_3_operations():
    exc = drift_check.HEADER_OPTIONAL_ORG_EXCEPTIONS
    assert set(exc) == {("GET", "/search/v2/meta"), ("PUT", "/v1/data/updateExternal")}
    assert all("live_f4_headers_round3.md" in why for why in exc.values())


# ------------------------------------------------------------ what is skipped

def test_block_with_no_spec_op_is_skipped_and_counted(tree):
    findings = tree(_block(), _spec(_hp("hostEmail"), path="/elsewhere"))
    assert drift_check.CHECK_EXAMINED["41"] == {"examined": 0, "skipped": 1}
    assert len(findings) == 1 and "error" in findings[0]


def test_examined_counts_only_header_bearing_blocks(tree):
    src = _block(SENT, KW) + _block(command="list").replace(
        "things/{thing_id}", "others/{thing_id}")
    spec = _spec(_hp("hostEmail"))
    spec["paths"]["/others/{thingId}"] = _spec()["paths"][PATH]
    assert tree(src, spec) == []
    assert drift_check.CHECK_EXAMINED["41"] == {"examined": 1, "skipped": 0}


# ------------------------------------------------------------ live tree, wiring

def test_live_tree_is_not_blind():
    drift_check.check_header_params()
    assert drift_check.CHECK_EXAMINED["41"]["examined"] >= 30


def test_live_tree_is_clean():
    assert drift_check.check_header_params() == []


def test_registered_for_printing_and_never_raises(capsys):
    assert "41" in drift_check.CHECK_PRINT
    drift_check.CHECK_EXAMINED["41"] = {"examined": 3, "skipped": 0}
    drift_check.print_check_findings("41", [{"bogus": 1}])
    out = capsys.readouterr().out
    assert out.startswith("[41] ") and "FORMAT-ERROR" in out


def test_printed_line_names_the_command_and_the_header(capsys, tree):
    drift_check.print_check_findings("41", tree(_block(), _spec(_hp("hostEmail"))))
    out = capsys.readouterr().out
    assert "zz-probe show" in out and "hostEmail" in out and "dropped" in out


@pytest.mark.parametrize("module_src,expected_exit", [
    (_block(), 1),
    (_block(SENT, KW), 0),
], ids=["planted-defect", "clean"])
def test_enforce_exit_follows_a_planted_defect(monkeypatch, capsys, tree,
                                               module_src, expected_exit):
    stub_unrelated_checks(monkeypatch)
    tree(module_src, _spec(_hp("hostEmail")))      # writes the temp dirs
    real = drift_check.check_header_params

    def planted(*a, **k):
        return real(commands_dir=tree.cmds, specs_dir=tree.specs, exceptions={})

    monkeypatch.setattr(drift_check, "check_header_params", planted)
    for other in ("check_query_enum_help", "check_readonly_flags",
                  "check_composed_property_flags", "check_oneof_bodies",
                  "check_body_shape", "check_positional_order"):
        monkeypatch.setattr(drift_check, other, lambda *a, **k: [])
    assert drift_check.main() == expected_exit
    out = capsys.readouterr().out
    assert "[41] header parameters sent" in out
    assert ("FAIL" if expected_exit else "PASS") in out.splitlines()[-1]
