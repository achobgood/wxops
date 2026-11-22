"""Drift gate check 41: a command's positional arguments must follow the URL
(audit F5).

The renderer took each operation's positional path IDs in the order the spec
listed its parameters, so `cc-flow publish` read `FLOW_ID PROJECT_ID` while
its URL is `.../project/{project_id}/flows/{flow_id}:publish` and `cc-flow
export` on the same resource read `PROJECT_ID FLOW_ID`. The check is a pure
source check: the `typer.Argument` parameters that also appear as `{name}` in
a `url = f"..."` of the block must keep the order of their placeholders.

Every fire case has a paired no-fire case. Synthetic blocks only: no generated
command function is imported or called.
"""

import pytest

from tools import drift_check
from tests.test_drift_check_query_enum import stub_unrelated_checks


def _block(args, url_tail, command="publish", extra_params="", url2=None):
    sig = "".join(f'    {a}: str = typer.Argument(help="{a}"),\n' for a in args)
    second = f'    url = f"{url2}"\n' if url2 else ""
    return f'''
@app.command("{command}", short_help="Probe.")
def {command}(
{sig}{extra_params}    debug: bool = typer.Option(False, "--debug"),
):
    """Probe."""
    api = get_api(debug=debug)
    org_id = get_cc_org_id(api.session)
    url = f"https://example.invalid/{{org_id}}/{url_tail}"
{second}    result = api.session.rest_post(url, json={{}})
'''


URL = "project/{project_id}/flows/{flow_id}:publish"


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    cmds.mkdir()

    def run(module_src):
        (cmds / "zz_probe.py").write_text(module_src, encoding="utf-8")
        return drift_check.check_positional_order(commands_dir=cmds)

    run.cmds = cmds
    return run


def test_arguments_in_url_order_are_clean(tree):
    assert tree(_block(["project_id", "flow_id"], URL)) == []


def test_arguments_against_url_order_fire(tree):
    found = tree(_block(["flow_id", "project_id"], URL))
    assert len(found) == 1
    assert found[0]["command"] == "publish"
    assert found[0]["arguments"] == ["flow_id", "project_id"]
    assert found[0]["url_order"] == ["project_id", "flow_id"]


def test_three_arguments_with_one_swapped_fire(tree):
    url = "a/{a_id}/b/{b_id}/c/{c_id}"
    assert tree(_block(["a_id", "b_id", "c_id"], url)) == []
    assert len(tree(_block(["a_id", "c_id", "b_id"], url))) == 1


def test_an_injected_org_id_is_not_judged(tree):
    """org_id is in the URL but not an argument: only the two arguments count."""
    found = tree(_block(["flow_id", "project_id"], URL))
    assert "org_id" not in found[0]["arguments"]


def test_argument_not_in_the_url_is_not_judged(tree):
    """A body or query value declared as an argument has no URL position."""
    assert tree(_block(["project_id", "flow_id", "note"], URL)) == []
    assert tree(_block(["note", "project_id", "flow_id"], URL)) == []
    assert len(tree(_block(["note", "flow_id", "project_id"], URL))) == 1


def test_a_paged_walker_with_two_urls_fires_when_either_disagrees(tree):
    src = _block(["project_id", "flow_id"], URL,
                 url2="https://example.invalid/{flow_id}/{project_id}")
    assert len(tree(src)) == 1


def test_single_argument_is_skipped_and_counted(tree):
    drift_check.CHECK_EXAMINED.pop("41", None)
    # alone it examines nothing, which the gate reports as BLIND, never as 0
    found = tree(_block(["flow_id"], "flows/{flow_id}"))
    assert [f.get("check") for f in found] == ["41"] and "error" in found[0]
    assert drift_check.CHECK_EXAMINED["41"]["examined"] == 0
    assert drift_check.CHECK_EXAMINED["41"]["skipped"] >= 1
    # beside one judged command, the single-argument one is skipped, not a finding
    src = (_block(["flow_id"], "flows/{flow_id}", command="show")
           + _block(["project_id", "flow_id"], URL))
    assert tree(src) == []
    assert drift_check.CHECK_EXAMINED["41"] == {
        **drift_check.CHECK_EXAMINED["41"], "examined": 1, "skipped": 1}


def test_examined_counts_judged_commands(tree):
    drift_check.CHECK_EXAMINED.pop("41", None)
    src = (_block(["project_id", "flow_id"], URL, command="publish")
           + _block(["flow_id", "project_id"], URL, command="lock"))
    found = tree(src)
    assert drift_check.CHECK_EXAMINED["41"]["examined"] == 2
    assert [f["command"] for f in found] == ["lock"]


def test_live_tree_is_not_blind():
    """The shipped modules must give the check something to examine."""
    drift_check.check_positional_order()
    assert drift_check.CHECK_EXAMINED["41"]["examined"] > 100


def test_registered_for_printing_and_never_raises(capsys):
    assert "41" in drift_check.CHECK_PRINT
    drift_check.CHECK_EXAMINED["41"] = {"examined": 3, "skipped": 0}
    drift_check.print_check_findings("41", [{"bogus": 1}])
    out = capsys.readouterr().out
    assert out.startswith("[41] ") and "FORMAT-ERROR" in out


def test_printed_line_names_the_command_and_both_orders(capsys, tree):
    drift_check.print_check_findings(
        "41", tree(_block(["flow_id", "project_id"], URL)))
    out = capsys.readouterr().out
    assert "wxcli zz-probe publish" in out
    assert "FLOW_ID PROJECT_ID" in out and "PROJECT_ID FLOW_ID" in out


@pytest.mark.parametrize("module_src,expected_exit", [
    (_block(["flow_id", "project_id"], URL), 1),
    (_block(["project_id", "flow_id"], URL), 0),
], ids=["planted-defect", "clean"])
def test_enforce_exit_follows_a_planted_defect(monkeypatch, capsys, tree,
                                               module_src, expected_exit):
    stub_unrelated_checks(monkeypatch)
    tree(module_src)                    # writes the temp commands dir
    real = drift_check.check_positional_order

    def planted(*a, **k):
        return real(commands_dir=tree.cmds)

    monkeypatch.setattr(drift_check, "check_positional_order", planted)
    for other in ("check_query_enum_help", "check_readonly_flags",
                  "check_composed_property_flags", "check_oneof_bodies",
                  "check_body_shape"):
        monkeypatch.setattr(drift_check, other, lambda *a, **k: [])
    assert drift_check.main() == expected_exit
    out = capsys.readouterr().out
    assert "[41] positional order vs URL" in out
    assert ("FAIL" if expected_exit else "PASS") in out.splitlines()[-1]
