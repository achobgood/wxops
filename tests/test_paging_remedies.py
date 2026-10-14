"""The truncation note names only remedies the invoking command really offers.

Two defects, both measured live 2026-10-13 (ADR-18):

1. `people list --offset 2 --limit 3` returned items 0-2: `/v1/people` ignores
   the `start` the CLI sends (its Link header carries a `cursor=`). The note
   nonetheless said "... or --offset 5 for just the next one", so following
   it looped back to page one. `licenses list` ignores `start` and `max`.
2. `licenses show ID --include-assigned-to user --limit 2` printed "Re-run
   with --all to fetch every page"; `licenses show ... --all` is "No such
   option". Every generated command calls `rest_get`, which printed the same
   advice whatever the command offered.

The fix: `rest_get`/`fetch_from_offset` take `remedies=` (default: none), and
the generator passes exactly the flags the command offers; a command in the
declared, measured `offset_ignored` set refuses `--offset` (exit 2) instead of
sending it. Synthetic fixtures only; no generated module is imported.
"""

import pytest
import typer
from typer.testing import CliRunner

from tools.command_renderer import render_command_file, _render_list_command
from tools.postman_parser import Endpoint, EndpointField

from wxcli.auth import WebexSession, _more_pages_note, _warn_if_more_pages


# ── runtime: what the note says for each remedy set ─────────────────────────


class _Resp:
    content = b"x"
    is_success = True
    status_code = 200
    text = ""

    def __init__(self, link="", items=0):
        self.headers = {"Link": link} if link else {}
        self._items = items

    def json(self):
        return {"items": [{"id": i} for i in range(self._items)]}


NEXT = '<https://webexapis.com/v1/x?cursor=abc>; rel="next"'


@pytest.fixture(autouse=True)
def _note_on(monkeypatch):
    monkeypatch.delenv("WXCLI_NO_PAGE_WARN", raising=False)


def _err(capsys, remedies, params=None):
    _warn_if_more_pages(_Resp(NEXT, 3), params, remedies)
    return capsys.readouterr().err


def test_both_remedies_keep_the_old_wording(capsys):
    err = _err(capsys, ("all", "offset"), {"start": 2})
    assert "Re-run with --all to fetch every page, or --offset 5 for just the next one." in err


def test_all_only_never_names_an_offset_to_follow(capsys):
    """people list: the hint `--offset 5` looped back to page one."""
    err = _err(capsys, ("all",), {"start": 2})
    assert "Re-run with --all to fetch every page" in err
    assert "--offset 5" not in err and "for just the next one" not in err
    assert "ignores --offset" in err


def test_no_remedies_never_names_all_or_offset(capsys):
    """licenses show: there is no --all to re-run with."""
    err = _err(capsys, ())
    assert "more pages" in err
    assert "Re-run with --all" not in err and "--offset" not in err
    assert "--help" in err


def test_offset_only(capsys):
    err = _err(capsys, ("offset",), {"start": 2})
    assert "--offset 5" in err and "--all" not in err


def test_private_helpers_require_remedies():
    """No default at all: a future direct caller cannot silently bring back
    the old advice, which check 33 would not see (it reads only the
    rest_get/fetch_from_offset defaults)."""
    with pytest.raises(TypeError):
        _warn_if_more_pages(_Resp(NEXT, 3), {"start": 2})
    with pytest.raises(TypeError):
        _more_pages_note(3, 5)


def test_more_pages_note_honours_remedies(capsys):
    _more_pages_note(3, 5, ())
    err = capsys.readouterr().err
    assert "more pages" in err and "--all" not in err and "--offset" not in err


class _OneShot(WebexSession):
    def __init__(self, resp):
        self.resp = resp

    def _request(self, method, url, params=None, **kw):  # type: ignore[override]
        return self.resp


def test_rest_get_names_nothing_unless_told(capsys):
    """The default is the safe direction: a caller that declares nothing (a
    show command, a hand-written command, raw Python) is never told to use a
    flag nobody checked it has."""
    _OneShot(_Resp(NEXT, 3)).rest_get("u", params={"start": 2})
    err = capsys.readouterr().err
    assert "more pages" in err and "--all" not in err and "--offset" not in err


def test_rest_get_passes_remedies_through(capsys):
    _OneShot(_Resp(NEXT, 3)).rest_get("u", params={"start": 2},
                                      remedies=("all", "offset"))
    assert "--offset 5 " in capsys.readouterr().err


def test_rest_get_remedies_is_keyword_only():
    with pytest.raises(TypeError):
        _OneShot(_Resp()).rest_get("u", {}, ("all",))


class _Paged(WebexSession):
    def __init__(self, total):
        self.records = [{"id": i} for i in range(total)]

    def _request(self, method, url, params=None, **kw):  # type: ignore[override]
        size = int(params.get("pageSize") or 10)
        page = int(params.get("page") or 0)
        body = {"data": self.records[page * size:(page + 1) * size],
                "meta": {"totalRecords": len(self.records)}}

        class _R:
            is_success = True
            content = b"x"
            headers: dict = {}

            def json(self_inner):
                return body

        return _R()


def test_fetch_from_offset_default_names_nothing(capsys):
    _Paged(56).fetch_from_offset("u", offset=25, count=10)
    err = capsys.readouterr().err
    assert "more pages" in err and "--offset" not in err


def test_fetch_from_offset_passes_remedies_through(capsys):
    _Paged(56).fetch_from_offset("u", offset=25, count=10,
                                 remedies=("all", "offset"))
    assert "--offset 35 " in capsys.readouterr().err


# ── renderer: each generated shape passes what it offers ────────────────────


def _qp(name, typ="integer"):
    return EndpointField(name=name, python_name=name, field_type=typ,
                         description="", required=False, default=None,
                         enum_values=None)


def _ep(**kw):
    base = dict(name="List Things", method="GET", url_path="things",
                path_vars=[], query_params=[_qp("max")], body_fields=[],
                command_type="list", command_name="list", raw_path=["things"],
                response_list_key="items", response_id_key=None,
                deprecated=False, json_body_example=None)
    base.update(kw)
    return Endpoint(**base)


BOTH = 'remedies=("all", "offset")'
ALL_ONLY = 'remedies=("all",)'
IGNORED = {"offset_ignored": {"list": "measured live"}}


def test_paginating_list_offers_both():
    code = _render_list_command(_ep(paginates=True, pagination_style="link"), {})
    assert f"api.session.rest_get(url, params=params, {BOTH})" in code


def test_link_walker_list_offers_both():
    code = _render_list_command(_ep(pagination_style="link"), {})
    assert f"api.session.rest_get(url, params=params, {BOTH})" in code


def test_page_numbered_list_offers_both_on_both_calls():
    ep = _ep(pagination_style="page", query_params=[_qp("page"), _qp("pageSize")])
    code = _render_list_command(ep, {})
    assert f"api.session.rest_get(url, params=params, {BOTH})" in code
    assert f'item_key="items", {BOTH})' in code   # fetch_from_offset


def test_unpaged_list_names_no_remedy():
    """`--all` is visible but inert on a list the spec says does not page, so
    advising it would be the licenses-show defect in another shape."""
    code = _render_list_command(_ep(), {})
    assert "api.session.rest_get(url, params=params)" in code
    assert "remedies=" not in code


def test_offset_ignored_paginating_list():
    code = _render_list_command(_ep(paginates=True, pagination_style="link"), IGNORED)
    assert f"api.session.rest_get(url, params=params, {ALL_ONLY})" in code
    assert 'params["start"] = offset' not in code
    assert "raise typer.Exit(2)" in code
    # The refusal comes before authentication.
    assert code.index("raise typer.Exit(2)") < code.index("get_api(")


def test_offset_ignored_unpaged_list_refuses_offset_too():
    code = _render_list_command(_ep(), IGNORED)
    assert 'params["start"] = offset' not in code
    assert "raise typer.Exit(2)" in code
    assert "remedies=" not in code


def test_offset_ignored_on_a_translated_list_is_refused():
    """A page-numbered or SCIM list translates --offset; declaring it ignored
    there contradicts the translation, so the renderer refuses the entry."""
    ep = _ep(pagination_style="page", query_params=[_qp("page"), _qp("pageSize")])
    with pytest.raises(ValueError, match="offset_ignored"):
        _render_list_command(ep, IGNORED)


def test_generator_exits_1_with_a_clear_error_when_a_declared_list_gains_paging(
        tmp_path, capsys):
    """Upstream adds `page`/`pageSize` to a list in the set: the weekly regen
    must stop with a readable ERROR (exit 1), not a traceback — a human
    re-measures live and edits the override (spec-sync contract §6)."""
    from tools.generate_commands import generate_tag
    rows = {"type": "array", "items": {"type": "object",
                                       "properties": {"id": {"type": "string"}}}}
    spec = {"paths": {"/things": {"get": {
        "tags": ["Probe"], "operationId": "listThings", "summary": "List Things",
        "parameters": [{"name": "page", "in": "query", "schema": {"type": "integer"}},
                       {"name": "pageSize", "in": "query", "schema": {"type": "integer"}}],
        "responses": {"200": {"description": "ok", "content": {"application/json": {
            "schema": {"type": "object", "properties": {"data": rows}}}}}}}}}}
    overrides = {"_tag_ovr:Probe": {"offset_ignored": {"list": "measured"}}}
    with pytest.raises(SystemExit) as exc:
        generate_tag("Probe", spec, overrides, tmp_path, False, set())
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "ERROR: offset_ignored" in err and "re-measure" in err.lower()


def test_show_command_names_no_remedy():
    ep = _ep(command_type="show", command_name="show", query_params=[_qp("limit", "string")])
    code = render_command_file("Things", [ep], {})
    assert "remedies=" not in code


# ── behaviour: exec the rendered module with stubs ──────────────────────────


class _StubSession:
    def __init__(self):
        self.calls = []

    def rest_get(self, url, params=None, **kw):
        self.calls.append(("rest_get", dict(params or {}), kw))
        return {"items": [{"id": 1}]}

    def follow_pagination(self, url, params=None, item_key="items"):
        self.calls.append(("follow_pagination", dict(params or {}), {}))
        return iter([{"id": 1}])


def _app(code):
    session = _StubSession()

    class _Api:
        pass

    api = _Api()
    api.session = session
    ns = {
        "get_api": lambda debug=False: api,
        "WebexError": type("WebexError", (Exception,), {}),
        "handle_rest_error": lambda e: None,
        "handle_network_error": lambda e: None,
        "print_table": lambda *a, **k: None,
        "print_json": lambda *a, **k: None,
        "emit": lambda value, **k: typer.echo(repr(value)),
        "load_json_body": lambda *a, **k: {},
        "verify_write": lambda *a, **k: None,
        "get_org_id": lambda: None,
    }
    src = "\n".join(l for l in code.splitlines() if not l.startswith("from wxcli"))
    exec(compile(src, "<rendered>", "exec"), ns)
    return ns["app"], session


def _render(ep, ovr):
    return render_command_file("Things", [ep], ovr)


def test_offset_on_an_ignored_command_exits_2_and_sends_nothing():
    app, session = _app(_render(_ep(paginates=True, pagination_style="link"), IGNORED))
    result = CliRunner().invoke(app, ["--offset", "2", "--limit", "3"])
    assert result.exit_code == 2
    assert session.calls == []
    assert "ignores --offset" in result.output
    assert "Drop --offset" in result.output
    assert "--all --fields '[2:5]'" in result.output


def test_walker_refusal_with_all_already_passed_does_not_say_use_all():
    """`people list --all --offset 2`: refusing is right (honouring --all
    would silently start at record 0), but the user already passed --all."""
    app, session = _app(_render(_ep(paginates=True, pagination_style="link"), IGNORED))
    result = CliRunner().invoke(app, ["--all", "--offset", "2"])
    assert result.exit_code == 2 and session.calls == []
    assert "Drop --offset" in result.output
    assert "--fields '[2:5]'" in result.output
    assert "--all --fields" not in result.output and "Use --all" not in result.output


def test_unpaged_refusal_never_points_at_all():
    """`licenses list`: no walker, so --all does nothing; the endpoint returns
    every record. Say drop --offset and slice, never "--all" or "first page"."""
    code = _render(_ep(), IGNORED)
    app, session = _app(code)
    result = CliRunner().invoke(app, ["--offset", "3"])
    assert result.exit_code == 2 and session.calls == []
    assert "ignores --offset" in result.output and "Drop --offset" in result.output
    assert "--fields '[2:5]'" in result.output
    assert "--all" not in result.output and "first page" not in result.output
    help_line = next(l for l in code.splitlines() if '"--offset"' in l)
    assert "--all" not in help_line


def test_ignored_command_without_offset_still_runs_and_advises_all_only():
    app, session = _app(_render(_ep(paginates=True, pagination_style="link"), IGNORED))
    result = CliRunner().invoke(app, ["--limit", "3"])
    assert result.exit_code == 0, result.output
    name, params, kw = session.calls[0]
    assert name == "rest_get" and "start" not in params
    assert kw == {"remedies": ("all",)}


def test_offset_zero_is_not_refused():
    app, session = _app(_render(_ep(), IGNORED))
    assert CliRunner().invoke(app, ["--offset", "0"]).exit_code == 0
    assert session.calls


def test_ordinary_command_still_sends_offset():
    app, session = _app(_render(_ep(paginates=True, pagination_style="link"), {}))
    result = CliRunner().invoke(app, ["--offset", "2", "--limit", "3"])
    assert result.exit_code == 0, result.output
    name, params, kw = session.calls[0]
    assert params["start"] == 2 and kw == {"remedies": ("all", "offset")}


# ── generator: the declared set is validated like every command-keyed key ──


def test_offset_ignored_is_a_command_keyed_override():
    from tools.generate_commands import COMMAND_KEYED_OVERRIDES
    assert "offset_ignored" in COMMAND_KEYED_OVERRIDES


def test_declared_set_is_exactly_the_two_measured_commands():
    """ADR-18: a declared, measured set — not a guess. Adding a command here
    needs a live measurement (`--offset 2 --limit 3` vs items 2-4 of `--all`)."""
    import yaml
    from pathlib import Path
    ovr = yaml.safe_load((Path(__file__).resolve().parent.parent
                          / "tools" / "field_overrides.yaml").read_text())
    declared = {(tag, cmd) for tag, block in ovr.items()
                if isinstance(block, dict)
                for cmd in (block.get("offset_ignored") or {})}
    declared |= {(tag, cmd) for spec in (ovr.get("tag_overrides") or {}).values()
                 for tag, block in (spec or {}).items()
                 for cmd in ((block or {}).get("offset_ignored") or {})}
    assert declared == {("People", "list"), ("Licenses", "list")}
