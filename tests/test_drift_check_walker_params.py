"""Drift gate check 24: a page walker sending a page/size parameter the
endpoint does not declare — plus the shared print helper checks 23-30 use.

`follow_page_param` always sent `pageSize`. The Contact Center Flows endpoints
declare `size`, ignored the unknown name, and returned their default 10 — which
the walker's short-page stop read as the end (`cc-flow list --all`: 10 of 56,
2026-10-13). The renderer now passes `size_param="size"` there; this check reads
each walker call's `page_param=`/`size_param=` (defaults copied from
src/wxcli/auth.py, never imported) and `follow_scim`'s fixed
`startIndex`/`count`, and compares them with the spec op's query params.

The rule fires only when the endpoint DECLARES a name for that concept (a page
or offset name for the page param, a page-size name for the size param) and the
walker sends a different one. `/v1/tasks` declares only `pageSize` yet pages by
`page` live, so a declared-nothing concept is not this check's claim.

Every fire case has a paired no-fire case, written so the check can fail it.
"""

import json

import pytest

from tools import drift_check


BLOCK = '''
@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o"),
    all_pages: bool = typer.Option(False, "--all"),
):
    """List things."""
    url = f"https://webexapis.com/v1/zzProbe"
    params = {}
    result = None
    try:
        if all_pages:
            result = list(api.session.WALKER)
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
'''


def _block(walker):
    return BLOCK.replace("WALKER", walker)


def _spec(query_params, path="/v1/zzProbe", method="get"):
    return {"paths": {path: {method: {
        "tags": ["Probe"],
        "parameters": [{"name": n, "in": "query", "schema": {"type": "string"}}
                       for n in query_params],
        "responses": {"200": {"description": "ok"}},
    }}}}


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(module_src, spec, module="zz_probe.py"):
        (cmds / module).write_text(module_src)
        (specs / "webex-probe.json").write_text(json.dumps(spec))
        return drift_check.check_undeclared_walker_params(
            commands_dir=cmds, specs_dir=specs)

    return run


DEFAULT_WALK = 'follow_page_param(url=url, params=params, item_key="data")'


# ------------------------------------------------------- the 2026-10-13 bug

def test_default_page_size_on_size_endpoint_fires(tree):
    """`cc-flow list` before the fix: the Flows endpoint declares page/size,
    the walker sent its default `pageSize`."""
    findings = tree(_block(DEFAULT_WALK), _spec(["page", "size"]))
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["param"] == "pageSize"
    assert f["walker"] == "follow_page_param"
    assert f["group"] == "zz-probe" and f["command"] == "list"
    assert f["op"] == "GET /v1/zzProbe"
    assert f["spec"] == "webex-probe.json"


def test_explicit_size_param_passes(tree):
    """The shipped fix: the renderer passes the declared size name."""
    walk = ('follow_page_param(url=url, params=params, item_key="data", '
            'size_param="size")')
    assert tree(_block(walk), _spec(["page", "size"])) == []


def test_default_names_on_page_size_endpoint_pass(tree):
    assert tree(_block(DEFAULT_WALK), _spec(["page", "pageSize"])) == []


def test_fetch_from_offset_default_size_fires(tree):
    walk = ("fetch_from_offset(url=url, params=params, offset=offset, "
            'count=limit, item_key="data")')
    findings = tree(_block(walk), _spec(["page", "size"]))
    assert [(f["walker"], f["param"]) for f in findings] == [
        ("fetch_from_offset", "pageSize")]


def test_fetch_from_offset_explicit_size_passes(tree):
    walk = ("fetch_from_offset(url=url, params=params, offset=offset, "
            'count=limit, item_key="data", size_param="size")')
    assert tree(_block(walk), _spec(["page", "size"])) == []


def test_both_walkers_in_one_block_each_report(tree):
    walk = (DEFAULT_WALK + ")\n            x = (api.session.fetch_from_offset("
            "url=url, params=params, offset=offset, count=limit, "
            'item_key="data")')
    findings = tree(_block(walk), _spec(["page", "size"]))
    assert sorted(f["walker"] for f in findings) == [
        "fetch_from_offset", "follow_page_param"]


def test_explicit_page_param_reaches_declared_name(tree):
    walk = ('follow_page_param(url=url, params=params, item_key="data", '
            'page_param="pageNumber", size_param="size")')
    findings = tree(_block(walk), _spec(["page", "size"]))
    assert [(f["param"]) for f in findings] == ["pageNumber"]
    assert tree(_block(walk), _spec(["pageNumber", "page", "size"])) == []


def test_kwargs_inside_nested_parens_are_read(tree):
    walk = ('follow_page_param(url=url, params=dict(params), item_key="data", '
            'size_param="size")')
    assert tree(_block(walk), _spec(["page", "size"])) == []


# --------------------------------------------- the concept must be declared

def test_page_name_silent_when_endpoint_declares_no_page_name(tree):
    """`cc-tasks list`: /v1/tasks declares only `pageSize` and pages by `page`
    live (2026-10-13). The spec names no page concept, so nothing to compare."""
    assert tree(_block(DEFAULT_WALK), _spec(["pageSize", "from"])) == []


def test_wrong_page_name_fires_when_endpoint_declares_another(tree):
    """A page walker on an offset/limit endpoint sends neither declared name."""
    findings = tree(_block(DEFAULT_WALK), _spec(["offset", "limit"]))
    assert sorted(f["param"] for f in findings) == ["page", "pageSize"]


def test_generic_size_without_page_is_not_a_page_size(tree):
    """`size` alone is too generic a word (as in check 23): no size concept."""
    assert tree(_block(DEFAULT_WALK), _spec(["size"])) == []


def test_silent_when_endpoint_declares_no_paging_names(tree):
    assert tree(_block(DEFAULT_WALK), _spec(["from", "to"])) == []


# ------------------------------------------------------------------- SCIM

SCIM_WALK = 'follow_scim(url=url, params=params, item_key="Resources")'


def test_scim_defaults_on_scim_endpoint_pass(tree):
    assert tree(_block(SCIM_WALK), _spec(["startIndex", "count", "filter"])) == []


def test_scim_walker_on_page_endpoint_fires(tree):
    findings = tree(_block(SCIM_WALK), _spec(["page", "pageSize"]))
    assert sorted((f["walker"], f["param"]) for f in findings) == [
        ("follow_scim", "count"), ("follow_scim", "startIndex")]


# ------------------------------------------------------------- exemptions

def test_follow_pagination_is_exempt(tree):
    """Link-header walking sends no page/size name of its own."""
    walk = 'follow_pagination(url=url, params=params, item_key="items")'
    findings = tree(_block(walk) + "\n" + _block(DEFAULT_WALK).replace(
        '"list"', '"list-two"'), _spec(["page", "pageSize"]))
    assert findings == []
    assert drift_check.CHECK_EXAMINED["24"]["examined"] == 1


def test_non_literal_kwarg_is_skipped_not_guessed(tree):
    """`size_param=name` cannot be decided statically: counted, never fired."""
    walk = ('follow_page_param(url=url, params=params, item_key="data", '
            'size_param=size_name)')
    good = _block(DEFAULT_WALK).replace('"list"', '"list-two"')
    findings = tree(_block(walk) + "\n" + good, _spec(["page", "size"]))
    assert [f["command"] for f in findings] == ["list-two"]
    assert drift_check.CHECK_EXAMINED["24"]["examined"] == 1
    assert drift_check.CHECK_EXAMINED["24"]["skipped"] == 1


# -------------------------------------------------------- coverage / blind

def test_skips_block_without_a_spec_op(tree):
    findings = tree(_block(DEFAULT_WALK), _spec(["page", "size"], path="/v1/other"))
    assert [f.get("check") for f in findings] == ["24"]
    assert "examined 0" in findings[0]["error"]
    assert drift_check.CHECK_EXAMINED["24"] == {"examined": 0, "skipped": 1}


def test_examined_count_is_reported(tree):
    tree(_block(DEFAULT_WALK), _spec(["page", "pageSize"]))
    assert drift_check.CHECK_EXAMINED["24"] == {"examined": 1, "skipped": 0}


def test_odd_input_never_raises(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()
    (cmds / "zz_probe.py").write_text(_block(
        'follow_page_param(url=url, params=params, item_key="data"'))  # unclosed
    (cmds / "zz_tail.py").write_text(
        '@app.command("tail")\ndef t():\n    url = f"https://webexapis.com/v1/zzProbe"\n'
        '    r = api.session.follow_page_param(url=url, params=(params')
    (specs / "webex-probe.json").write_text("not json")
    (specs / "webex-other.json").write_text("[1, 2]")
    findings = drift_check.check_undeclared_walker_params(
        commands_dir=cmds, specs_dir=specs)
    assert [f.get("check") for f in findings] == ["24"]
    missing = drift_check.check_undeclared_walker_params(
        commands_dir=tmp_path / "nope", specs_dir=tmp_path / "nope")
    assert [f.get("check") for f in missing] == ["24"]


def test_live_tree_is_clean():
    assert drift_check.check_undeclared_walker_params() == []
    assert drift_check.CHECK_EXAMINED["24"]["examined"] >= 100


# ------------------------------------------- shared print helper (23-30)

def _fmt(f):
    return f"wxcli {f['group']} {f['command']}"


@pytest.fixture
def probe_print(monkeypatch):
    monkeypatch.setitem(drift_check.CHECK_PRINT, "99",
                        ("probe label", "things", _fmt))
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "99",
                        {"examined": 1, "skipped": 0})


def test_print_helper_renders_blind_finding_without_keyerror(capsys, probe_print):
    """A blind finding carries only {check, error}: a formatter reading
    f['group'] would KeyError and crash the unattended gate (exit 2)."""
    blind = drift_check.record_examined("99", [], 0, 4, "things")
    drift_check.print_check_findings("99", blind)
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "[99] probe label: 1   (examined 0 things, skipped 4)"
    assert out[1] == "      BLIND  examined 0 things \u2014 helpers blind? (skipped 4)"


def test_print_helper_survives_a_formatter_that_raises(capsys, probe_print):
    drift_check.print_check_findings("99", [{"odd": 1}])
    out = capsys.readouterr().out.splitlines()
    assert out[1] == "      {'odd': 1}"


def test_print_helper_caps_detail_lines(capsys, probe_print, monkeypatch):
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "99",
                        {"examined": 30, "skipped": 0})
    findings = [{"group": "g", "command": f"c{i}"} for i in range(23)]
    drift_check.print_check_findings("99", findings)
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "[99] probe label: 23   (examined 30 things, skipped 0)"
    assert out[1] == "      wxcli g c0"
    assert len(out) == 22
    assert out[-1] == "      ... and 3 more (--json for all)"


def test_print_helper_without_recorded_stats_or_label_never_raises(capsys):
    drift_check.CHECK_EXAMINED.pop("98", None)
    drift_check.CHECK_PRINT.pop("98", None)
    drift_check.print_check_findings("98", [{"group": "g"}])
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "[98] check 98: 1   (examined 0 items, skipped 0)"
    assert out[1] == "      {'group': 'g'}"


def test_check_23_line_is_unchanged_through_the_helper(capsys, monkeypatch):
    """The retrofit must keep [23]'s exact bytes (header + detail line)."""
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "23",
                        {"examined": 544, "skipped": 3})
    f = {"group": "cc-queue", "command": "list", "op": "GET /v1/x",
         "flag": "--offset", "sends": "start", "spec": "webex-contact-center.json"}
    drift_check.print_check_findings("23", [f])
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "[23] list flags (--offset/--limit) sent as a query param the endpoint "
        "does not declare: 1   (examined 544 list commands, skipped 3)",
        "      wxcli cc-queue list  --offset -> start  GET /v1/x  "
        "(webex-contact-center.json)",
    ]


def test_check_24_line_format(capsys, monkeypatch):
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "24",
                        {"examined": 107, "skipped": 3})
    f = {"group": "cc-flow", "command": "list", "op": "GET /v1/f",
         "walker": "follow_page_param", "param": "pageSize",
         "spec": "webex-contact-center.json"}
    drift_check.print_check_findings("24", [f])
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "[24] page walkers using a page/size parameter the endpoint does not "
        "declare: 1   (examined 107 page-walker commands, skipped 3)",
        "      wxcli cc-flow list  follow_page_param sends pageSize  GET /v1/f  "
        "(webex-contact-center.json)",
    ]


def test_helper_skip_count_takes_reader_keys(monkeypatch):
    monkeypatch.setitem(drift_check.HELPER_SKIPS, "modules", ["a"])
    monkeypatch.setitem(drift_check.HELPER_SKIPS, "blocks", ["b", "c"])
    monkeypatch.setitem(drift_check.HELPER_SKIPS, "specs", ["d", "e", "f"])
    assert drift_check.helper_skip_count() == 6
    assert drift_check.helper_skip_count("modules", "blocks") == 3
    assert drift_check.helper_skip_count("specs") == 3
    assert drift_check.helper_skip_count("nonsense") == 0
