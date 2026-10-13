"""Drift gate check 23: a list command's `--offset`/`--limit` sent under a name
the endpoint does not read.

Every generated list command carries `--limit` and `--offset`. Before
2026-10-13 the renderer always sent them as `max`/`start` (or `limit`/`offset`
where declared). On the 105 Contact Center page-numbered endpoints — which read
`page`/`pageSize` — both flags were sent, ignored, and the command exited 0 with
page 0 (`cc-queue list --limit 2` -> `?max=2` -> 17 rows). Flag exists, flag
does not work, nothing errors.

The rule fires only when the endpoint DECLARES a name for the concept (an
offset/page name for `--offset`, a page-size name for `--limit`) and the command
sends something else. An endpoint that declares no such name gives the CLI
nothing to translate to; whether an undeclared `start` is honoured there is not
knowable statically, so it is not this check's claim.

Every fire case has a paired no-fire case, written so the check can fail it.
"""

import json

import pytest

from tools import drift_check


LIST_BLOCK = '''
@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o"),
    limit: int = typer.Option(0, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all"),
):
    """List things."""
    url = f"https://webexapis.com/v1/zzProbe"
    params = {}
WRITES
    result = None
    try:
FETCH
    except WebexError as e:
        handle_rest_error(e)
'''

SINGLE_FETCH = "        result = api.session.rest_get(url, params=params)"
VIA_OFFSET = (
    "        if offset > 0:\n"
    "            result = api.session.fetch_from_offset(url=url, params=params, "
    "offset=offset, count=limit, item_key=\"data\")\n"
    "        else:\n"
    "            result = api.session.rest_get(url, params=params)")


def _block(writes, fetch=SINGLE_FETCH):
    return LIST_BLOCK.replace("WRITES", writes).replace("FETCH", fetch)


def _w(param, var):
    return f'    if {var} > 0:\n        params["{param}"] = {var}'


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
        return drift_check.check_inert_window_flags(
            commands_dir=cmds, specs_dir=specs)

    return run


# ------------------------------------------------- page-numbered (CC) endpoints

def test_offset_sent_as_undeclared_start_fires(tree):
    findings = tree(_block(_w("start", "offset")), _spec(["page", "pageSize"]))
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["flag"] == "--offset"
    assert f["sends"] == "start"
    assert f["group"] == "zz-probe" and f["command"] == "list"
    assert f["op"] == "GET /v1/zzProbe"
    assert f["spec"] == "webex-probe.json"


def test_offset_via_fetch_from_offset_passes(tree):
    """The shipped fix: --offset is translated by the runtime walker."""
    findings = tree(_block(_w("pageSize", "limit"), VIA_OFFSET),
                    _spec(["page", "pageSize"]))
    assert findings == []


def test_fetch_from_offset_exempts_offset_even_with_a_stray_write(tree):
    """--offset > 0 always reaches the walker branch, so a leftover write is
    harmless; the flag works."""
    writes = _w("pageSize", "limit") + "\n" + _w("start", "offset")
    findings = tree(_block(writes, VIA_OFFSET), _spec(["page", "pageSize"]))
    assert findings == []


def test_offset_on_page_size_only_endpoint_fires(tree):
    """`cc-tasks list` before dc91c40: /v1/tasks declares only `pageSize` (it
    pages by `page` live), and --offset was sent as `start`."""
    findings = tree(_block(_w("start", "offset")), _spec(["pageSize", "from"]))
    assert [(f["flag"], f["sends"]) for f in findings] == [("--offset", "start")]


def test_offset_on_page_size_only_endpoint_via_fetch_from_offset_passes(tree):
    findings = tree(_block(_w("pageSize", "limit"), VIA_OFFSET),
                    _spec(["pageSize", "from"]))
    assert findings == []


def test_offset_on_size_beside_page_endpoint_fires(tree):
    findings = tree(_block(_w("start", "offset")), _spec(["size", "page"]))
    assert [(f["flag"], f["sends"]) for f in findings] == [("--offset", "start")]


def test_limit_sent_as_undeclared_max_fires(tree):
    findings = tree(_block(_w("max", "limit")), _spec(["page", "pageSize"]))
    assert [(f["flag"], f["sends"]) for f in findings] == [("--limit", "max")]


def test_limit_written_to_declared_page_size_passes(tree):
    findings = tree(_block(_w("pageSize", "limit")), _spec(["page", "pageSize"]))
    assert findings == []


def test_limit_also_written_to_declared_page_size_passes(tree):
    """A stray undeclared write beside the declared one: the flag still works."""
    writes = _w("max", "limit") + "\n" + _w("pageSize", "limit")
    findings = tree(_block(writes), _spec(["page", "pageSize"]))
    assert findings == []


def test_limit_written_to_declared_size_passes(tree):
    """The Flows endpoints spell the page size `size`."""
    findings = tree(_block(_w("size", "limit")), _spec(["page", "size"]))
    assert findings == []


def test_pre_fix_shape_fires_on_both_flags(tree):
    """`cc-queue list` before dc91c40: max/start on a page/pageSize endpoint."""
    writes = _w("max", "limit") + "\n" + _w("start", "offset")
    findings = tree(_block(writes), _spec(["page", "pageSize", "filter"]))
    assert sorted((f["flag"], f["sends"]) for f in findings) == [
        ("--limit", "max"), ("--offset", "start")]


# ------------------------------------------------------------ SCIM endpoints

def test_scim_endpoint_sent_max_and_start_fires(tree):
    """SCIM reads startIndex/count; max/start are ignored."""
    writes = _w("max", "limit") + "\n" + _w("start", "offset")
    findings = tree(_block(writes), _spec(["startIndex", "count", "filter"]))
    assert sorted((f["flag"], f["sends"]) for f in findings) == [
        ("--limit", "max"), ("--offset", "start")]


def test_scim_endpoint_sent_count_and_start_index_passes(tree):
    writes = (_w("count", "limit") + "\n"
              '    if offset > 0:\n        params["startIndex"] = offset + 1')
    findings = tree(_block(writes), _spec(["startIndex", "count"]))
    assert findings == []


# ------------------------------------------------------ link / offset endpoints

def test_link_paged_declared_start_passes(tree):
    writes = _w("max", "limit") + "\n" + _w("start", "offset")
    findings = tree(_block(writes), _spec(["start", "max"]))
    assert findings == []


def test_declared_limit_offset_spelling_passes(tree):
    writes = _w("limit", "limit") + "\n" + _w("offset", "offset")
    findings = tree(_block(writes), _spec(["limit", "offset"]))
    assert findings == []


def test_limit_to_undeclared_max_where_limit_is_declared_fires(tree):
    findings = tree(_block(_w("max", "limit")), _spec(["limit", "offset"]))
    assert [(f["flag"], f["sends"]) for f in findings] == [("--limit", "max")]


# ------------------------------------------- endpoints with no name to translate to

def test_offset_silent_when_endpoint_declares_no_offset_name(tree):
    """`people list` shape: `max` declared, cursor paging via Link. There is no
    declared offset name, so `start` cannot be called the wrong one statically."""
    writes = _w("max", "limit") + "\n" + _w("start", "offset")
    findings = tree(_block(writes), _spec(["max", "displayName"]))
    assert findings == []


def test_silent_when_endpoint_declares_no_paging_names(tree):
    """The spec says this endpoint does not page; the flags are the documented
    uniform no-op (ADR-12)."""
    writes = _w("max", "limit") + "\n" + _w("start", "offset")
    findings = tree(_block(writes), _spec(["name"]))
    assert findings == []


def test_generic_size_without_page_is_not_a_page_size(tree):
    """`size` alone is too generic to be a page size (openapi_parser agrees);
    with no `page` declared there is no page-size name to miss."""
    findings = tree(_block(_w("max", "limit")), _spec(["size"]))
    assert findings == []


# --------------------------------------------------------------------- scope

BLIND = [{"check": "23", "error": "examined 0 list commands — helpers blind? (skipped 1)"}]


def test_skips_block_without_a_spec_op(tree):
    """Skipped and counted. The only block is skipped, so 0 were examined —
    which is itself a failure (record_examined), not a quiet pass."""
    findings = tree(_block(_w("start", "offset")),
                    _spec(["page", "pageSize"], path="/v1/somewhereElse"))
    assert findings == BLIND
    assert drift_check.CHECK_EXAMINED["23"] == {"examined": 0, "skipped": 1}


def test_skips_non_get_blocks(tree):
    """A POST is out of scope; with a GET beside it only the GET is examined."""
    post = _block(_w("start", "offset")).replace(
        "api.session.rest_get(url, params=params)",
        "api.session.rest_post(url, json=body, params=params)").replace(
        '@app.command("list")', '@app.command("create")')
    get = _block(_w("pageSize", "limit"))
    spec = _spec(["page", "pageSize"])
    spec["paths"]["/v1/zzProbe"]["post"] = _spec(
        ["page", "pageSize"], method="post")["paths"]["/v1/zzProbe"]["post"]
    findings = tree(post + "\n" + get, spec)
    assert findings == []
    assert drift_check.CHECK_EXAMINED["23"]["examined"] == 1


def test_zero_examined_fails_visibly(tree):
    """A run that examined nothing must not read as a clean 0."""
    src = _block(_w("start", "offset")).replace(
        "api.session.rest_get(url, params=params)",
        "api.session.rest_post(url, json=body, params=params)")
    findings = tree(src, _spec(["page", "pageSize"], method="post"))
    assert len(findings) == 1 and "examined 0 list commands" in findings[0]["error"]
    assert drift_check.CHECK_EXAMINED["23"]["examined"] == 0


def test_skipped_counts_helper_block_skips(tree):
    """A named block with a URL but no recognisable call (HELPER_SKIPS
    "blocks") is counted in the printed skipped number."""
    odd = _block(_w("pageSize", "limit")).replace(
        "api.session.rest_get(url, params=params)", "do_something_else(url)").replace(
        '@app.command("list")', '@app.command("odd")')
    good = _block(_w("pageSize", "limit"))
    tree(odd + "\n" + good, _spec(["page", "pageSize"]))
    assert drift_check.HELPER_SKIPS["blocks"] == ["zz_probe odd"]
    assert drift_check.CHECK_EXAMINED["23"] == {"examined": 1, "skipped": 1}


def test_examined_count_is_reported(tree):
    tree(_block(_w("pageSize", "limit")), _spec(["page", "pageSize"]))
    assert drift_check.CHECK_EXAMINED["23"] == {"examined": 1, "skipped": 0}


def test_odd_input_never_raises(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()
    (cmds / "zz_probe.py").write_text(_block(_w("start", "offset")))
    (specs / "webex-bad.json").write_text("[not an object")
    (specs / "webex-list.json").write_text("[]")
    (specs / "webex-weird.json").write_text(json.dumps({"paths": {
        "/v1/zzProbe": {"get": {"parameters": "nope"}}}}))
    assert drift_check.check_inert_window_flags(
        commands_dir=cmds, specs_dir=specs) == []
    missing = drift_check.check_inert_window_flags(
        commands_dir=tmp_path / "missing", specs_dir=tmp_path / "missing")
    assert [f["check"] for f in missing] == ["23"] and "error" in missing[0]


# ----------------------------------------------------------------- live tree

def test_live_tree_is_clean():
    assert drift_check.check_inert_window_flags() == []
    # Not blind: the live tree has ~540 GET list blocks carrying the flags.
    assert drift_check.CHECK_EXAMINED["23"]["examined"] >= 400
