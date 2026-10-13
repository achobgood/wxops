"""Drift gate check 26: a Contact Center command sending the base64 org id.

The saved org id is the base64 Webex id (`Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8…`).
The Contact Center host wants the bare UUID and answered 401 `Token does not
have access to OrgId:Y2lz…` to 14 commands in 6 groups that sent it as
`?orgId=` (`cc-queue-stats list`, `cc-agents list-statistics`/
`list-activities`, `cc-ewt show`, `cc-search create`, `cc-subscriptions` x8,
`cc-tasks list`; live 2026-10-13). `_render_auto_inject_params` now emits
`get_cc_org_id(api.session)` under the CC host; this check keeps it that way.

A block that builds its URL on `get_cc_base_url()` fires when it sends, as the
`orgId` query param or inside the URL, a variable assigned from
`get_org_id()` / `resolve_org_id(…)` (both return the base64 id) and never
from `get_cc_org_id(…)` / `decode_webex_id(…)`. Calling-host blocks send the
base64 id correctly and are out of scope. Needs no spec.

Every fire case has a paired no-fire case, written so the check can fail it.
"""

from tools import drift_check


CC_QUERY_BLOCK = '''
@app.command("CMD")
def cmd(
    output: str = typer.Option("table", "--output", "-o"),
):
    """Get Queue Statistics."""
    api = get_api(debug=debug)
    BASE_LINE
    url = f"URL"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = WRITE
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    emit(result, output=output)
'''

CC_PATH_BLOCK = '''
@app.command("CMD")
def cmd(
    output: str = typer.Option("table", "--output", "-o"),
):
    """List Site(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = SOURCE
    url = f"{cc_base_url}/organization/{orgid}/site"
    params = {}
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    emit(result, output=output)
'''

CC_BASE = "cc_base_url = get_cc_base_url()"
CC_URL = "{cc_base_url}/v1/queues/statistics"
CALLING_URL = "https://webexapis.com/v1/telephony/config/queues"


def _query(cmd="list", write="org_id", base=CC_BASE, url=CC_URL):
    return (CC_QUERY_BLOCK.replace("CMD", cmd).replace("BASE_LINE", base)
            .replace("URL", url).replace("WRITE", write))


def _path(cmd="list", source="get_cc_org_id(api.session)"):
    return CC_PATH_BLOCK.replace("CMD", cmd).replace("SOURCE", source)


def _run(tmp_path, *modules):
    cmds = tmp_path / "commands"
    cmds.mkdir(exist_ok=True)
    for i, src in enumerate(modules):
        (cmds / f"cc_probe{i}.py").write_text(src)
    return drift_check.check_cc_base64_org_id(commands_dir=cmds)


# ------------------------------------------------- the 2026-10-13 bug (query)

def test_cc_block_with_get_org_id_fires(tmp_path):
    findings = _run(tmp_path, _query())
    assert findings == [{"group": "cc-probe0", "command": "list",
                         "op": "GET /v1/queues/statistics"}]


def test_cc_block_with_get_cc_org_id_passes(tmp_path):
    assert _run(tmp_path, _query(write="get_cc_org_id(api.session)")) == []


def test_calling_block_with_get_org_id_passes(tmp_path):
    # A clean CC module beside it, so the run is not BLIND.
    assert _run(tmp_path, _query(base="", url=CALLING_URL), _path()) == []


def test_decoded_query_value_passes(tmp_path):
    assert _run(tmp_path, _query(write="decode_webex_id(org_id)")) == []


def test_inline_get_org_id_call_fires(tmp_path):
    assert len(_run(tmp_path, _query(write="get_org_id()"))) == 1


def test_inline_get_cc_org_id_call_passes(tmp_path):
    assert _run(tmp_path, _query(write="get_cc_org_id(api.session)")) == []


def test_reassigned_from_get_cc_org_id_passes(tmp_path):
    src = _query().replace(
        "    if org_id is not None:",
        "    org_id = get_cc_org_id(api.session)\n    if org_id is not None:")
    assert _run(tmp_path, src) == []


def test_resolve_org_id_query_fires(tmp_path):
    src = _query().replace("org_id = get_org_id()",
                           "org_id = resolve_org_id(api.session)")
    assert len(_run(tmp_path, src)) == 1


def test_walrus_assigned_get_org_id_fires(tmp_path):
    src = _query().replace(
        "    org_id = get_org_id()\n    if org_id is not None:",
        "    if (org_id := get_org_id()) is not None:")
    assert len(_run(tmp_path, src)) == 1


def test_walrus_assigned_get_cc_org_id_passes(tmp_path):
    src = _query().replace(
        "    org_id = get_org_id()\n    if org_id is not None:",
        "    if (org_id := get_cc_org_id(api.session)) is not None:")
    assert _run(tmp_path, src) == []


def test_cc_base_url_called_with_an_argument_is_examined(tmp_path):
    findings = _run(tmp_path, _query(base="cc_base_url = get_cc_base_url(region)"))
    assert drift_check.CHECK_EXAMINED["26"]["examined"] == 1
    assert len(findings) == 1


def test_other_query_param_from_get_org_id_passes(tmp_path):
    src = _query().replace('params["orgId"] = org_id',
                           'params["owner"] = org_id')
    assert _run(tmp_path, src) == []


# ------------------------------------------------------- path injection

def test_cc_path_with_resolve_org_id_fires(tmp_path):
    findings = _run(tmp_path, _path(source="resolve_org_id(api.session)"))
    assert findings == [{"group": "cc-probe0", "command": "list",
                         "op": "GET /organization/{orgid}/site"}]


def test_cc_path_with_get_org_id_fires(tmp_path):
    assert len(_run(tmp_path, _path(source="get_org_id()"))) == 1


def test_cc_path_with_get_cc_org_id_passes(tmp_path):
    assert _run(tmp_path, _path()) == []


def test_cc_path_with_inline_resolve_org_id_fires(tmp_path):
    src = _path().replace("/organization/{orgid}/",
                          "/organization/{resolve_org_id(api.session)}/")
    assert len(_run(tmp_path, src)) == 1


def test_cc_path_with_suffix_named_helper_passes(tmp_path):
    src = _path().replace("/organization/{orgid}/",
                          "/organization/{my_get_org_id(api.session)}/")
    assert _run(tmp_path, src) == []


def test_cc_path_with_inline_get_cc_org_id_passes(tmp_path):
    src = _path().replace("/organization/{orgid}/",
                          "/organization/{get_cc_org_id(api.session)}/")
    assert _run(tmp_path, src) == []


def test_calling_path_with_resolve_org_id_passes(tmp_path):
    src = (_path(source="resolve_org_id(api.session)")
           .replace("    cc_base_url = get_cc_base_url()\n", "")
           .replace("{cc_base_url}", "https://webexapis.com/v1"))
    assert _run(tmp_path, src, _path()) == []


def test_base64_var_used_elsewhere_in_cc_block_passes(tmp_path):
    src = _path().replace(
        '    params = {}',
        '    params = {}\n    saved = get_org_id()\n    print(saved)')
    assert _run(tmp_path, src) == []


def test_query_and_path_in_one_block_fire_once(tmp_path):
    src = _path(source="get_org_id()").replace(
        "    params = {}",
        '    params = {}\n    params["orgId"] = orgid')
    assert len(_run(tmp_path, src)) == 1


def test_post_block_reports_its_method(tmp_path):
    src = _query(cmd="create").replace("rest_get(url, params=params)",
                                       "rest_post(url, params=params, json={})")
    assert _run(tmp_path, src)[0]["op"] == "POST /v1/queues/statistics"


# ------------------------------------------------- counting and robustness

def test_examined_counts_cc_blocks_only(tmp_path):
    _run(tmp_path, _query(), _path(cmd="sites"),
         _query(cmd="calling", base="", url=CALLING_URL))
    assert drift_check.CHECK_EXAMINED["26"]["examined"] == 2


def test_no_cc_blocks_is_blind(tmp_path):
    findings = _run(tmp_path, _query(base="", url=CALLING_URL))
    assert [f.get("check") for f in findings] == ["26"]


def test_odd_input_never_raises(tmp_path):
    cmds = tmp_path / "commands"
    cmds.mkdir()
    (cmds / "cc_probe.py").write_text(_query())
    (cmds / "cc_tail.py").write_text(
        '@app.command("tail")\ndef t():\n    cc_base_url = get_cc_base_url()\n'
        '    url = f"{cc_base_url}/v1/x"\n    org_id = get_org_id(\n'
        '    params["orgId"] = (org_id')
    (cmds / "cc_bin.py").write_bytes(b"\xff\xfe\x00bad")
    findings = drift_check.check_cc_base64_org_id(commands_dir=cmds)
    assert all(isinstance(f, dict) for f in findings)
    assert drift_check.CHECK_EXAMINED["26"]["skipped"] >= 1
    missing = drift_check.check_cc_base64_org_id(commands_dir=tmp_path / "no")
    assert [f.get("check") for f in missing] == ["26"]


def test_live_tree_is_clean():
    assert drift_check.check_cc_base64_org_id() == []
    # A floor that catches blindness only (~470 CC blocks today); zero is
    # BLIND anyway. A tight floor would fail the weekly job on retirements.
    assert drift_check.CHECK_EXAMINED["26"]["examined"] >= 20


def test_check_26_line_format(capsys, monkeypatch):
    monkeypatch.setitem(drift_check.CHECK_EXAMINED, "26",
                        {"examined": 470, "skipped": 0})
    f = {"group": "cc-queue-stats", "command": "list",
         "op": "GET /v1/queues/statistics"}
    drift_check.print_check_findings("26", [f])
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "[26] Contact Center commands sending the base64 Webex org id as "
        "orgId: 1   (examined 470 Contact Center commands, skipped 0)",
        "      wxcli cc-queue-stats list  GET /v1/queues/statistics",
    ]
