"""Drift gate check 33: the truncation note must not recommend a flag the
command does not offer.

Live 2026-10-13 (ADR-18): `licenses show ID --include-assigned-to user
--limit 2` printed "Re-run with --all to fetch every page", and `licenses show
… --all` is "No such option"; `people list` advised `--offset 5`, which that
endpoint ignores (the CLI now refuses it). The note is printed by
`rest_get`/`fetch_from_offset`, which name only the `remedies=` their caller
passes. A call with no `remedies=` names the runtime default, read from
`auth.py`'s own signature; a runtime with no such parameter is the pre-fix one,
whose note named `--all` and `--offset` unconditionally.

A block fires when a note-printing call names `--all` and the block has no
visible `--all` that reaches a page walker, or names `--offset` and the block
has no visible `--offset` or refuses it. Static only; synthetic inputs only.
"""

import pytest

from tools import drift_check


AUTH_PRE_FIX = '''
class WebexSession:
    def rest_get(self, url: str, params=None) -> dict:
        pass

    def fetch_from_offset(self, url, params=None, offset=0, count=0,
                          item_key="data", page_param="page",
                          size_param="pageSize") -> list:
        pass
'''

AUTH_FIXED = '''
class WebexSession:
    def rest_get(self, url: str, params=None, *, remedies=()) -> dict:
        pass

    def fetch_from_offset(self, url, params=None, offset=0, count=0,
                          item_key="data", page_param="page",
                          size_param="pageSize", *, remedies=()) -> list:
        pass
'''

SHOW = '''
@app.command("show", short_help="Get License Details.")
def show(
    license_id: str = typer.Argument(help="id"),
    limit: str = typer.Option(None, "--limit", help="A limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get License Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/licenses/{license_id}"
    params = {}
    try:
        result = api.session.rest_get(url, params=params{kw})
    except WebexError as e:
        handle_rest_error(e)
'''

WALKER_LIST = '''
@app.command("list", short_help="List Things.")
def cmd_list(
    limit: int = typer.Option(0, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Things."""
{guard}    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/things"
    params = {}
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params{kw})
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
'''

GUARD = '''    if offset > 0:
        typer.echo("Error: wxcli things list ignores --offset.", err=True)
        raise typer.Exit(2)
'''

UNPAGED_LIST = '''
@app.command("list", short_help="List Things.")
def cmd_list(
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Things."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/things"
    params = {}
    try:
        result = api.session.rest_get(url, params=params{kw})
    except WebexError as e:
        handle_rest_error(e)
'''

SINGLE_OBJECT_LIST = '''
@app.command("list-privacy", short_help="Read Privacy.")
def list_privacy(
    person_id: str = typer.Argument(help="id"),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read Privacy."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/people/{person_id}/features/privacy"
    try:
        result = api.session.rest_get(url{kw})
    except WebexError as e:
        handle_rest_error(e)
'''

PAGE_NUMBERED = '''
@app.command("list", short_help="List Teams.")
def cmd_list(
    limit: int = typer.Option(0, "--limit", help="Max"),
    offset: int = typer.Option(0, "--offset", help="Skip"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Teams."""
    api = get_api(debug=debug)
    url = f"https://api.wxcc-us1.cisco.com/organization/{orgid}/team"
    params = {}
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="data"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="data"{kw})
        else:
            result = api.session.rest_get(url, params=params{kw})
    except WebexError as e:
        handle_rest_error(e)
'''

BOTH = ', remedies=("all", "offset")'


def _fmt(template, kw="", guard=""):
    return template.replace("{guard}", guard).replace("{kw}", kw)

ALL = ', remedies=("all",)'


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    cmds.mkdir()
    auth = tmp_path / "auth.py"

    def run(module_src, auth_src=AUTH_FIXED):
        (cmds / "zz_probe.py").write_text(module_src)
        if auth_src is None:
            if auth.exists():
                auth.unlink()
        else:
            auth.write_text(auth_src)
        return drift_check.check_paging_advice(commands_dir=cmds, auth_py=auth)

    return run


# ------------------------------------------------- the 2026-10-13 instances

def test_pre_fix_show_fires_on_all_and_offset(tree):
    """licenses show: the pre-fix runtime named both remedies on every call."""
    findings = tree(_fmt(SHOW, kw=""), AUTH_PRE_FIX)
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["group"] == "zz-probe" and f["command"] == "show"
    assert f["advises"] == ["--all", "--offset"]
    assert drift_check.CHECK_EXAMINED["33"] == {"examined": 1, "skipped": 0}


def test_fixed_runtime_show_is_clean(tree):
    assert tree(_fmt(SHOW, kw="")) == []
    assert drift_check.CHECK_EXAMINED["33"]["examined"] == 1


def test_show_told_to_advise_all_fires(tree):
    findings = tree(_fmt(SHOW, kw=ALL))
    assert [f["advises"] for f in findings] == [["--all"]]


def test_refused_offset_advised_fires(tree):
    """people list after the fix refuses --offset; advising it is the loop."""
    findings = tree(_fmt(WALKER_LIST, guard=GUARD, kw=BOTH))
    assert [f["advises"] for f in findings] == [["--offset"]]
    assert "refuses" in findings[0]["why"]


def test_refused_offset_with_all_only_is_clean(tree):
    assert tree(_fmt(WALKER_LIST, guard=GUARD, kw=ALL)) == []


# ------------------------------------------------------------- no-fire pairs

def test_walker_list_advising_both_is_clean(tree):
    assert tree(_fmt(WALKER_LIST, guard="", kw=BOTH)) == []


def test_walker_list_on_the_pre_fix_runtime_is_clean(tree):
    """A list that really walks and sends --offset offers both remedies, so
    the pre-fix note was right there."""
    assert tree(_fmt(WALKER_LIST, guard="", kw=""), AUTH_PRE_FIX) == []


def test_page_numbered_list_is_clean(tree):
    assert tree(_fmt(PAGE_NUMBERED, kw=BOTH)) == []


def test_page_numbered_fetch_from_offset_is_judged_too(tree):
    """fetch_from_offset prints the note as well; told to advise --all on a
    block whose --all is hidden it fires."""
    src = _fmt(PAGE_NUMBERED, kw=BOTH).replace(
        'typer.Option(False, "--all", help', 'typer.Option(False, "--all", hidden=True, help')
    findings = tree(src)
    assert [f["advises"] for f in findings] == [["--all"]]


def test_unpaged_list_advising_all_fires(tree):
    """A visible --all that reaches no walker is inert: advising it is wrong."""
    findings = tree(_fmt(UNPAGED_LIST, kw=ALL))
    assert [f["advises"] for f in findings] == [["--all"]]
    assert tree(_fmt(UNPAGED_LIST, kw="")) == []


def test_hidden_all_on_a_single_object_list_does_not_count(tree):
    findings = tree(_fmt(SINGLE_OBJECT_LIST, kw=ALL))
    assert [f["advises"] for f in findings] == [["--all"]]
    assert tree(_fmt(SINGLE_OBJECT_LIST, kw="")) == []


def test_pre_fix_single_object_list_fires(tree):
    findings = tree(_fmt(SINGLE_OBJECT_LIST, kw=""), AUTH_PRE_FIX)
    assert [f["advises"] for f in findings] == [["--all", "--offset"]]


def test_write_block_without_a_note_call_is_not_examined(tree):
    src = '''
@app.command("create", short_help="Create.")
def create(
    debug: bool = typer.Option(False, "--debug"),
):
    """Create."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/things"
    try:
        result = api.session.rest_post(url, json={})
    except WebexError as e:
        handle_rest_error(e)
''' + _fmt(SHOW, kw="")
    assert tree(src) == []
    assert drift_check.CHECK_EXAMINED["33"] == {"examined": 1, "skipped": 0}


# --------------------------------------------------------- what it cannot read

def test_non_literal_remedies_is_skipped_and_counted(tree):
    findings = tree(_fmt(SHOW, kw=", remedies=HINTS") + _fmt(WALKER_LIST, guard="", kw=BOTH))
    assert findings == []
    assert drift_check.CHECK_EXAMINED["33"] == {"examined": 1, "skipped": 1}


def test_missing_runtime_is_blind(tree):
    findings = tree(_fmt(SHOW, kw=""), None)
    assert len(findings) == 1 and "error" in findings[0]
    assert drift_check.CHECK_EXAMINED["33"]["examined"] == 0


def test_runtime_with_non_literal_default_is_blind(tree):
    findings = tree(_fmt(SHOW, kw=""), AUTH_FIXED.replace("remedies=()", "remedies=DEFAULT", 1))
    assert len(findings) == 1 and "error" in findings[0]


def test_nothing_to_examine_is_blind(tree):
    findings = tree("x = 1\n")
    assert len(findings) == 1 and "error" in findings[0]


def test_runtime_defaults_reader():
    assert drift_check.note_remedy_defaults(AUTH_FIXED) == {
        "rest_get": (), "fetch_from_offset": ()}
    assert drift_check.note_remedy_defaults(AUTH_PRE_FIX) == {
        "rest_get": ("all", "offset"), "fetch_from_offset": ("all", "offset")}
    assert drift_check.note_remedy_defaults("def broken(:") is None


def test_registered_for_printing_and_never_raises(capsys):
    assert "33" in drift_check.CHECK_PRINT
    drift_check.CHECK_EXAMINED["33"] = {"examined": 3, "skipped": 0}
    drift_check.print_check_findings("33", [{"bogus": 1}])
    out = capsys.readouterr().out
    assert out.startswith("[33] ") and "FORMAT-ERROR" in out


def test_live_tree_is_not_blind():
    """Loose floor only (ADR-13): catches a render change that hides every
    note-printing call from the reader, not a regression."""
    findings = drift_check.check_paging_advice()
    assert not any("error" in f for f in findings)
    assert drift_check.CHECK_EXAMINED["33"]["examined"] > 500
