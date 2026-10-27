"""wxcc's generator tests, retargeted to the one generator (Plan 2 Task 17).

Pure-local: no API calls, no cost. Every case drives wxops' generator —
`tools/generate_commands.py` (`main`, `resolve_operation_overrides`) and
`tools/command_renderer.py` — on `tests/wxcc/fixtures/mini_flow_store.json`
saved under the Flow Store spec name, or on `specs/webex-cc-flow-store.json`
with the shipped `tools/field_overrides.yaml`. wxcc's forked generator is not
used.

A rendered module is exec'd with every `from wxcli` import stripped and its
names stubbed (the tests/test_generate_commands.py `TestOperationOverrides`
pattern), so wxcli itself is never imported and no command can reach the
network.

Each class keeps its wxcc name. A case whose wxcc subject has no counterpart in
wxops pins the replacement the plan's "Generator carry-over" table names; its
docstring says which row. Some replacements are drift-gate checks
(`tools/drift_check.py`, pointed at temp files) or facts read as text from the
shipped sources (`cc_flow.py`, `_registry.py`, `_lazy.py`). Two wxcc lint
cases have no counterpart at all; they are strict xfails labelled "gap".
"""
import ast
import collections
import json
import re
import sys
import tempfile
import types
from pathlib import Path

import pytest
import yaml

from tools import drift_check
from tools import generate_commands as gc
from tools.command_renderer import OperationOverrideRenderError, ParamNameOverrideError
from tools.openapi_parser import load_spec, parse_tag
from tests import test_command_naming_residue as naming

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "mini_flow_store.json"
REAL_SPEC = REPO / "specs" / "webex-cc-flow-store.json"
SPEC_NAME = "webex-cc-flow-store.json"
WIDGETS = "/{orgId}/project/{projectId}/widgets"
FS_BASE = "https://fs.test/flow-store"


def mini_overrides() -> dict:
    """wxcc's mini overrides, in wxops form (carry-over table row per key).

    * groups `{widgets: [Widgets]}` -> nothing: one tag renders one group
      (EXISTS: tag_merge + cli_name_overrides).
    * auto_inject_from_config `[orgId, projectId]` -> `[orgId]`: projectId is
      NOT NEEDED (P2-2, PROJECT_ID stays positional).
    * blocked_endpoints / warn_endpoints / request_overrides.multipart ->
      `operation_overrides` blocked / warn / multipart (PORT, Tasks 8, 10).
    * param_cli_names `Flow Type: flow-type` -> nothing: the parser already
      derives `--flow-type` from the spaced name.
    * pagination / table_columns on findWidgets -> nothing: the fixture's
      findWidgets declares a bare object, which wxops renders as a single
      read (`show`, ADR-14), so it has no table and no page walker. The
      list-shaped variant is `paged_spec()`.
    * command_names -> `command_name_overrides`, keyed on the derived name.
      findWidgets keeps its derived `show` (it is a single read here).
    """
    return {
        "auto_inject_from_config": ["orgId"],
        "skip_tags": {SPEC_NAME: ["admin-widget-controller"]},
        "operation_overrides": {SPEC_NAME: {
            "mergeWidget": {"blocked": "no-op; use update"},
            "refreshWidgets": {"warn": "may be slow on big orgs"},
            "importWidget": {"multipart": True},
        }},
        "tag_overrides": {SPEC_NAME: {"Widgets": {"command_name_overrides": {
            "show-widgets": "get", "update": "merge-patch",
            "create-import": "import", "create-refresh": "refresh",
        }}}},
    }


def fixture_spec() -> dict:
    return json.loads(FIXTURE.read_text())


def paged_spec() -> dict:
    """The fixture with findWidgets answering a page of records, the shape
    wxcc's `pagination: {page, size, item_key: widgets}` described."""
    spec = fixture_spec()
    spec["paths"][WIDGETS]["get"]["responses"]["200"]["content"]["application/json"]["schema"] = {
        "type": "object", "properties": {"widgets": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "string"},
                                             "name": {"type": "string"}}}}}}
    return spec


def _op(ovr: dict) -> dict:
    """The fixture's operation_overrides block, for editing in a test."""
    return ovr.setdefault("operation_overrides", {}).setdefault(SPEC_NAME, {})


def _tag(ovr: dict, tag: str = "Widgets") -> dict:
    """The fixture's tag_overrides block for `tag`, for editing in a test."""
    return ovr.setdefault("tag_overrides", {}).setdefault(SPEC_NAME, {}).setdefault(tag, {})


def generate(base: Path, overrides: dict, spec: dict | None = None, *argv: str) -> Path:
    """Run generate_commands.main() on the fixture (or `spec`) saved as the
    Flow Store spec, and return the output directory (fresh per call)."""
    work = Path(tempfile.mkdtemp(dir=base))
    spec_path = work / SPEC_NAME
    spec_path.write_text(json.dumps(spec) if spec is not None else FIXTURE.read_text())
    ovr_path = work / "overrides.yaml"
    ovr_path.write_text(yaml.safe_dump(overrides))
    out = work / "out"
    saved = sys.argv
    sys.argv = ["generate_commands", "--spec", str(spec_path), "--overrides",
                str(ovr_path), "--output", str(out), *(argv or ("--all",))]
    try:
        gc.main()
    finally:
        sys.argv = saved
    return out


def widgets(base: Path, overrides: dict | None = None, spec: dict | None = None) -> str:
    """The rendered Widgets module."""
    ovr = mini_overrides() if overrides is None else overrides
    return (generate(base, ovr, spec, "--tag", "Widgets") / "widgets.py").read_text()


def fn(code: str, name: str) -> str:
    """One command's source, from its decorator to the next one."""
    return code[code.index(f'@app.command("{name}"'):].split("\n@app.command")[0]


def load_app(code: str, monkeypatch, response=None):
    """Exec a rendered module with every wxcli import stubbed.

    Returns (app, calls, emitted). `calls` records every session method as
    (name, url, kwargs); `emitted` records every value handed to emit(). Any
    HTTP attempt through httpx itself fails the test.
    """
    import httpx
    import typer

    def _no_http(*a, **k):
        raise AssertionError("an HTTP call was attempted")

    monkeypatch.setattr(httpx.Client, "send", _no_http)
    calls, emitted = [], []

    class _Session:
        def __getattr__(self, name):
            def _record(*a, **k):
                calls.append((name, a[0] if a else k.get("url"), k))
                if name.startswith("follow_"):
                    return iter(response or [])
                return {"id": "W1"} if response is None else response
            return _record

    def _emit(value, **k):
        emitted.append(value)
        typer.echo(repr(value))

    namespace = {
        "get_api": lambda debug=False: types.SimpleNamespace(session=_Session()),
        "WebexError": type("WebexError", (Exception,), {}),
        "handle_rest_error": lambda e: (_ for _ in ()).throw(e),
        "handle_network_error": lambda e: (_ for _ in ()).throw(e),
        "print_table": lambda *a, **k: None,
        "print_json": lambda v, *a, **k: typer.echo(repr(v)),
        "emit": _emit,
        "load_json_body": lambda raw: json.loads(raw),
        "verify_write": lambda *a, **k: None,
        "get_org_id": lambda *a, **k: "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi9v",
        "resolve_org_id": lambda *a, **k: "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi9v",
        "get_cc_base_url": lambda *a, **k: "https://cc.test",
        "get_cc_org_id": lambda *a, **k: "org-uuid",
        "get_flow_store_base_url": lambda *a, **k: FS_BASE,
    }
    stripped = "\n".join(line for line in code.splitlines()
                         if not line.startswith("from wxcli"))
    exec(compile(stripped, "<rendered>", "exec"), namespace)
    return namespace["app"], calls, emitted


def invoke(app, *argv):
    from typer.testing import CliRunner
    return CliRunner().invoke(app, list(argv), env={"COLUMNS": "400", "TERM": "dumb"})


@pytest.fixture
def spec():
    return load_spec(str(FIXTURE))


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """specs/webex-cc-flow-store.json regenerated with the shipped YAML into a
    temp folder. `.dir` is that folder; `.src` maps module stem -> source,
    "_registry" included."""
    out = tmp_path_factory.mktemp("real")
    saved = sys.argv
    sys.argv = ["generate_commands", "--spec", str(REAL_SPEC), "--all", "--output", str(out)]
    try:
        gc.main()
    finally:
        sys.argv = saved
    return types.SimpleNamespace(dir=out, src={p.stem: p.read_text() for p in out.glob("*.py")})


def inert_findings(base: Path, monkeypatch, overrides: dict) -> list[dict]:
    """Drift check 15 (`check_inert_overrides`) run with the fixture as the only
    spec on disk and `overrides` as field_overrides.yaml."""
    specs = Path(tempfile.mkdtemp(dir=base))
    (specs / SPEC_NAME).write_text(FIXTURE.read_text())
    ovr_path = specs / "overrides.yaml"
    ovr_path.write_text(yaml.safe_dump(overrides))
    monkeypatch.setattr(drift_check, "SPECS_DIR", specs)
    monkeypatch.setattr(drift_check, "OVERRIDES", ovr_path)
    findings, _stale = drift_check.check_inert_overrides()
    return findings


# The Flow Store groups and their visible commands, from the plan's command
# fate table (fate (b) rows; (a) and (c) rows are served elsewhere).
FATE_TABLE_SURFACE = {
    "cc_flow_store": {
        "show-metadata", "update-metadata", "map-variables", "check-name", "copy",
        "consume", "consume-template", "revert", "list-usages",
        "list-global-variables", "show-flow-template", "test-expression",
        "show-build-info", "show-health", "show-current-user"},
    "cc_flow_versions": {"list", "show", "show-latest", "show-draft", "list-all",
                         "list-all-latest"},
    "cc_flow_tracing": {"show-interaction", "list-traces", "list-traces-decrypted",
                        "show-analytics", "list-interactions"},
    "cc_flow_prefs": {"list", "create", "update", "delete", "list-tags",
                      "list-tag-history"},
    "cc_flow_connectors": {"show", "list"},
    "cc_flow_projects": {"list-resource-collections", "show", "list",
                         "show-user-preferences"},
}


# Every @app.command name. Wider than test_command_naming_residue.DECORATOR,
# which needs `)` right after short_help and so misses a blocked stub (its
# decorator also carries context_settings).
DECORATOR = re.compile(r'@app\.command\("([^"]+)"(, hidden=True)?')


def visible_commands(code: str) -> set[str]:
    return {name for name, hidden in DECORATOR.findall(code) if not hidden}


def parse_widgets(spec: dict) -> dict:
    """The fixture's Widgets endpoints, keyed by derived command name."""
    endpoints, _skipped = parse_tag("Widgets", spec, auto_inject_params={"orgId"})
    return {ep.command_name: ep for ep in endpoints}


def upload(base: Path) -> Path:
    path = base / "flow.json"
    path.write_bytes(b'{"name": "f"}')
    return path


# ── parser ───────────────────────────────────────────────────────────────────

class TestParser:
    def test_dedup_and_endpoint_count(self, spec):
        """7 Widgets operations (the admin op carries another tag), 7 unique
        names; a second pass with the same seen-set adds nothing, because
        dedup keys on (operationId, path)."""
        seen: set = set()
        endpoints, _ = parse_tag("Widgets", spec, auto_inject_params={"orgId"},
                                 seen_operation_ids=seen)
        assert len(endpoints) == 7
        assert len({e.command_name for e in endpoints}) == 7
        again, _ = parse_tag("Widgets", spec, auto_inject_params={"orgId"},
                             seen_operation_ids=seen)
        assert again == []

    def test_safe_param_name_spaces(self, spec, tmp_path):
        """A spaced spec name ("Flow Type") yields a valid identifier and a
        dash flag."""
        imp = parse_widgets(spec)["create-import"]
        ft = next(q for q in imp.query_params if q.name == "Flow Type")
        assert ft.python_name == "flow-type"
        code = fn(widgets(tmp_path), "import")
        assert 'flow_type: str = typer.Option(None, "--flow-type"' in code
        ast.parse(code)

    def test_typed_scalars(self, spec, tmp_path):
        """An integer query param is recorded as a number. wxcli renders every
        scalar flag as `str` and sends the text (CLAUDE.md: ADR-17's
        string-typed numeric flags), so the flag itself is not int-typed."""
        page = next(q for q in parse_widgets(spec)["show"].query_params if q.name == "page")
        assert page.field_type == "number"
        assert 'page: str = typer.Option(None, "--page"' in widgets(tmp_path)

    def test_orgid_auto_injected_from_path(self, spec, tmp_path):
        """orgId is injected from config; projectId stays a positional argument
        (P2-2), like widgetId."""
        get = parse_widgets(spec)["show-widgets"]
        assert get.auto_inject_path_params == ["orgId"]
        assert get.path_vars == ["orgId", "projectId", "widgetId"]
        code = fn(widgets(tmp_path), "get")
        assert 'project_id: str = typer.Argument(' in code
        assert 'widget_id: str = typer.Argument(' in code
        assert "--org-id" not in code and "--project-id" not in code

    def test_dedup_key_fallback_no_opid(self):
        """Operations with no operationId record no dedup key, so two of them
        in one tag both parse instead of collapsing onto one empty key."""
        def get(summary):
            return {"get": {"tags": ["T"], "summary": summary, "responses": {}}}
        spec = {"paths": {"/x": get("Get x"), "/y": get("Get y")}}
        seen: set = set()
        endpoints, _ = parse_tag("T", spec, seen_operation_ids=seen)
        assert len(endpoints) == 2
        assert seen == set()

    def test_no_v1_strip(self, spec, tmp_path, monkeypatch):
        """The Flow Store path has no v1 segment to strip: the endpoint keeps
        it whole, and the request goes to the Flow Store base with the bare
        org UUID."""
        assert parse_widgets(spec)["show-widgets"].url_path == \
            "{orgId}/project/{projectId}/widgets/{widgetId}"
        app, calls, _ = load_app(widgets(tmp_path), monkeypatch)
        r = invoke(app, "get", "P", "W1")
        assert r.exit_code == 0, r.output
        assert calls == [("rest_get", f"{FS_BASE}/org-uuid/project/P/widgets/W1", {})]


# ── generate orchestrator ────────────────────────────────────────────────────

ADMIN_ACK = {SPEC_NAME: {"POST /admin/widgets/purge": "purge"}}


class TestGenerate:
    def test_dry_run_command_count(self, tmp_path, capsys):
        out = generate(tmp_path, mini_overrides(), None, "--all", "--dry-run")
        text = capsys.readouterr().out
        assert "Widgets -> widgets.py (widgets)" in text
        assert "7 commands, 0 skipped uploads" in text
        assert list(out.glob("*.py")) == []      # a dry run writes nothing

    def test_skip_tags_admin_excluded(self, tmp_path):
        """admin-widget-controller is a per-spec skip_tag: no module, and its
        operation renders nowhere."""
        out = generate(tmp_path, mini_overrides())
        assert {p.stem for p in out.glob("*.py")} == {"widgets", "widgettags", "_registry"}
        assert not any("admin/widgets/purge" in p.read_text() for p in out.glob("*.py"))
        # Control: without the skip the admin operation does render.
        ovr = mini_overrides()
        del ovr["skip_tags"]
        ovr["verb_semantics_ack"] = ADMIN_ACK
        out = generate(tmp_path, ovr)
        assert any("admin/widgets/purge" in p.read_text() for p in out.glob("*.py"))

    def test_skip_endpoint_dropped(self, tmp_path):
        ovr = mini_overrides()
        _op(ovr)["refreshWidgets"] = {"skip": "not needed"}
        del _tag(ovr)["command_name_overrides"]["create-refresh"]
        code = widgets(tmp_path, ovr)
        assert "widgets:refresh" not in code
        assert visible_commands(code) == {"show", "create", "get", "merge-patch",
                                          "delete", "import"}

    def test_command_names_override(self, tmp_path):
        """command_name_overrides, keyed on the derived name."""
        assert visible_commands(widgets(tmp_path)) == {
            "show", "create", "get", "merge-patch", "delete", "import", "refresh"}
        ovr = mini_overrides()
        del ovr["tag_overrides"]
        assert visible_commands(widgets(tmp_path, ovr)) == {
            "show", "create", "show-widgets", "update", "delete", "create-import",
            "create-refresh"}

    def test_collision_lint_raises(self, tmp_path, monkeypatch):
        """wxcc refused a rename onto a taken name. The wxops generator renders
        it; the guard is the tree-wide invariant in
        tests/test_command_naming_residue.py (no module registers a name twice),
        which a regen into src/ must pass. Pinned firing on this render."""
        ovr = mini_overrides()
        _tag(ovr)["command_name_overrides"]["show-widgets"] = "show"
        out = generate(tmp_path, ovr, None, "--tag", "Widgets")
        code = (out / "widgets.py").read_text()
        counts = collections.Counter(n for n, _hid in DECORATOR.findall(code))
        assert {n: c for n, c in counts.items() if c > 1} == {"show": 2}
        monkeypatch.setattr(naming, "_modules", lambda: [out / "widgets.py"])
        with pytest.raises(AssertionError, match=r"registers \{'show': 2\}"):
            naming.test_no_hidden_alias_shadows_a_visible_command()


# ── lint (wxcc lint_overrides) ───────────────────────────────────────────────

class TestLint:
    def test_unknown_opid_fails(self, tmp_path, capsys):
        ovr = mini_overrides()
        _op(ovr)["notARealOp"] = {"blocked": "x"}
        with pytest.raises(SystemExit) as exc:
            generate(tmp_path, ovr)
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "notARealOp" in err and "no operation has this operationId" in err

    def test_unknown_group_tag_fails(self, tmp_path, monkeypatch):
        """wxcc `groups` = tag_merge + cli_name_overrides. A group name keyed on
        a tag no spec declares is drift check 15's finding. (tag_merge sources
        are deliberately not flagged: an absent source is a no-op by design,
        per check_inert_overrides' docstring.)"""
        ovr = mini_overrides()
        ovr["cli_name_overrides"] = {SPEC_NAME: {"Widgets": "widgets"}}
        assert inert_findings(tmp_path, monkeypatch, ovr) == []
        ovr["cli_name_overrides"][SPEC_NAME]["Gadgets"] = "gadgets"
        found = inert_findings(tmp_path, monkeypatch, ovr)
        assert [(f["kind"], f["where"], f["tag"]) for f in found] == [
            ("tag", "cli_name_overrides", "Gadgets")]

    @pytest.mark.xfail(strict=True, reason=(
        "gap (Plan 2 T17 finding): a skip_tags pattern that matches no tag is "
        "accepted silently; wxcc's lint refused it, and neither the generator "
        "nor drift check 15 does"))
    def test_skip_tag_matching_nothing_fails(self, tmp_path, capsys):
        ovr = mini_overrides()
        ovr["skip_tags"] = {SPEC_NAME: ["no-such-controller"]}
        # Ack the admin op so the only possible refusal is the unmatched skip.
        ovr["verb_semantics_ack"] = ADMIN_ACK
        with pytest.raises(SystemExit):
            generate(tmp_path, ovr)
        assert "no-such-controller" in capsys.readouterr().err

    def test_unknown_section_key_fails(self, tmp_path, monkeypatch):
        """A mistyped section name (`skip_endpoint`) must not silently drop its
        payload. In wxops it reads as a top-level tag block, and drift check 15
        reports a block naming no tag."""
        ovr = mini_overrides()
        assert inert_findings(tmp_path, monkeypatch, ovr) == []
        ovr["skip_endpoint"] = {"refreshWidgets": "typo'd section"}
        found = inert_findings(tmp_path, monkeypatch, ovr)
        assert [(f["kind"], f["where"], f["tag"]) for f in found] == [
            ("tag", "top-level block", "skip_endpoint")]


# ── renderer capabilities ────────────────────────────────────────────────────

class TestRenderer:
    def test_all_modules_ast_parse(self, tmp_path):
        out = generate(tmp_path, mini_overrides())
        for path in out.glob("*.py"):
            ast.parse(path.read_text())      # raises on a syntax error

    def test_blocked_stub(self, tmp_path, monkeypatch):
        """blocked: a visible stub that exits 2 with the message, whatever the
        arguments, and never makes a request."""
        code = widgets(tmp_path)
        stub = fn(code, "merge-patch")
        assert "raise typer.Exit(2)" in stub and "BLOCKED: no-op; use update" in stub
        assert "merge-patch" in visible_commands(code)
        app, calls, _ = load_app(code, monkeypatch)
        for argv in (["merge-patch", "P", "W1"], ["merge-patch", "P", "W1", "--json-body", "{}"],
                     ["merge-patch"]):
            r = invoke(app, *argv)
            assert r.exit_code == 2, (argv, r.output)
            assert "no-op; use update" in r.output
        assert calls == []

    def test_warn_banner(self, tmp_path, monkeypatch):
        code = widgets(tmp_path)
        app, calls, _ = load_app(code, monkeypatch)
        r = invoke(app, "refresh", "P")
        assert r.exit_code == 0, r.output
        assert "Warning: may be slow on big orgs" in r.output
        assert [c[0] for c in calls] == ["rest_post"]
        body = fn(code, "refresh")
        assert body.index("Warning: may be slow on big orgs") < body.index("rest_post(")

    def test_multipart_render(self, tmp_path, monkeypatch):
        code = widgets(tmp_path)
        assert 'file: Path = typer.Option(..., "--file"' in fn(code, "import")
        app, calls, _ = load_app(code, monkeypatch)
        r = invoke(app, "import", "P", "--file", str(upload(tmp_path)))
        assert r.exit_code == 0, r.output
        name, url, kw = calls[0]
        assert (name, url) == ("rest_post_multipart", f"{FS_BASE}/org-uuid/project/P/widgets:import")
        assert kw["files"] == {"file": ("flow.json", b'{"name": "f"}', "application/json")}

    def test_spaced_param_flag_and_wire(self, tmp_path, monkeypatch):
        """The flag is --flow-type; the wire name stays "Flow Type"."""
        app, calls, _ = load_app(widgets(tmp_path), monkeypatch)
        r = invoke(app, "import", "P", "--file", str(upload(tmp_path)), "--flow-type", "FLOW")
        assert r.exit_code == 0, r.output
        assert calls[0][2]["params"] == {"Flow Type": "FLOW"}

    def test_pagination_loop(self, tmp_path, monkeypatch):
        """wxcc's page/size loop -> the ADR-12 page walker (carry-over row
        `pagination`, VERIFY Task 14): a findWidgets that answers a page of
        records renders `list`, whose --all walks page by page with the size
        name the spec declares; the default stays one request."""
        code = widgets(tmp_path, {"auto_inject_from_config": ["orgId"]}, paged_spec())
        listing = fn(code, "list")
        assert ('follow_page_param(url=url, params=params, item_key="widgets", '
                'size_param="size")') in listing
        assert "columns=[('ID', 'id'), ('Name', 'name')]" in listing
        rows = [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}]
        app, calls, emitted = load_app(code, monkeypatch, response=rows)
        r = invoke(app, "list", "P", "--all", "-o", "json")
        assert r.exit_code == 0, r.output
        assert [c[0] for c in calls] == ["follow_page_param"] and emitted == [rows]
        app, calls, _ = load_app(code, monkeypatch, response={"widgets": rows})
        assert invoke(app, "list", "P", "-o", "json").exit_code == 0
        assert [c[0] for c in calls] == ["rest_get"]

    def test_delete_force_rename(self, tmp_path, monkeypatch):
        """wxcc renamed the spec's `force` to --server-force and kept --force
        for the prompt. wxcli has one --force (fate table row 3, as on
        `cc-flow delete`): any value skips the prompt and is sent as `force`;
        without it, the delete asks first."""
        code = widgets(tmp_path)
        body = fn(code, "delete")
        assert body.count('"--force"') == 1 and "--server-force" not in code
        app, calls, _ = load_app(code, monkeypatch, response={})
        r = invoke(app, "delete", "P", "W1", "--force", "yes")
        assert r.exit_code == 0, r.output
        assert calls == [("rest_delete", f"{FS_BASE}/org-uuid/project/P/widgets/W1",
                          {"params": {"force": "yes"}})]
        from typer.testing import CliRunner
        r = CliRunner().invoke(app, ["delete", "P", "W1"], input="n\n")
        assert r.exit_code == 1 and "Delete W1?" in r.output
        assert len(calls) == 1

    def test_enum_help(self, tmp_path):
        assert '"--kind", help="Choices: A, B"' in widgets(tmp_path)

    def test_merge_patch_content_type(self, spec, tmp_path, monkeypatch):
        """The spec gives mergeWidget `application/merge-patch+json`. The wxops
        parser keeps a content type only for json-patch, so an unblocked
        merge-patch PATCH goes out as plain JSON. (The real one,
        mergePatchFlow, is blocked: a verified no-op.)"""
        assert spec["paths"][WIDGETS + "/{widgetId}"]["patch"]["requestBody"]["content"].keys() \
            == {"application/merge-patch+json"}
        assert parse_widgets(spec)["update"].content_type is None
        ovr = mini_overrides()
        del _op(ovr)["mergeWidget"]
        app, calls, _ = load_app(widgets(tmp_path, ovr), monkeypatch)
        r = invoke(app, "merge-patch", "P", "W1", "--json-body", '{"name": "x"}')
        assert r.exit_code == 0, r.output
        assert calls[0][0] == "rest_patch" and calls[0][2] == {"json": {"name": "x"}, "params": {}}

    def test_required_body_field_optional_and_validated_both_branches(self, tmp_path, monkeypatch):
        """A required body scalar renders as an OPTIONAL flag, and a missing one
        exits 1 before any request. wxcc also checked a --json-body; wxcli
        sends a --json-body as given and lets the server judge it (the
        ordinary body rule, tools/CLAUDE.md ADR-16 note)."""
        code = widgets(tmp_path)
        assert 'name: str = typer.Option(None, "--name"' in code
        assert 'typer.Option(..., "--name"' not in code
        app, calls, _ = load_app(code, monkeypatch)
        r = invoke(app, "create", "P", "--count", "2")
        assert r.exit_code == 1 and "Missing required fields: name" in r.output
        assert calls == []
        r = invoke(app, "create", "P", "--json-body", '{"count": 2}')
        assert r.exit_code == 0, r.output
        assert calls[0][2]["json"] == {"count": 2}

    def test_body_defaults_rendered(self, tmp_path, monkeypatch):
        """body_defaults seeds the body with setdefault, after either branch
        builds it, so a --json-body caller gets the default too."""
        ovr = mini_overrides()
        _tag(ovr)["body_defaults"] = {"create": {"kind": "default"}}
        app, calls, _ = load_app(widgets(tmp_path, ovr), monkeypatch)
        for argv, want in ((["--name", "w"], {"name": "w", "kind": "default"}),
                           (["--json-body", '{"name": "w"}'], {"name": "w", "kind": "default"}),
                           (["--json-body", '{"name": "w", "kind": "mine"}'],
                            {"name": "w", "kind": "mine"})):
            r = invoke(app, "create", "P", *argv)
            assert r.exit_code == 0, r.output
            assert calls[-1][2]["json"] == want


# ── manifest + emission ──────────────────────────────────────────────────────

class TestManifest:
    def test_emit_writes_manifest_and_registry(self, tmp_path, capsys):
        """wxcc wrote _manifest.json. wxops writes the _registry.py manifest
        main.py mounts, and --dry-run prints each command's method, type and
        required body fields; blocked/warn status lives in the module itself
        (TestRenderer)."""
        out = generate(tmp_path, mini_overrides())
        registry = (out / "_registry.py").read_text()
        assert '    ("widgets", "widgets"),' in registry
        assert '    ("widgettags", "widgettags"),' in registry
        ast.parse(registry)
        generate(tmp_path, mini_overrides(), None, "--all", "--dry-run")
        text = capsys.readouterr().out
        assert re.search(r"^\s+create\s+POST\s+create\s+required=\['name'\]$", text, re.M)
        assert re.search(r"^\s+get\s+GET\s+show\s+required=\[\]$", text, re.M)

    def test_main_end_to_end(self, tmp_path):
        out = generate(tmp_path, mini_overrides())
        assert (out / "widgets.py").exists() and (out / "widgettags.py").exists()
        for path in out.glob("*.py"):
            ast.parse(path.read_text())


# ── wxcc Phase-B polish features ─────────────────────────────────────────────

class TestPhaseBFeatures:
    def test_global_param_cli_names(self, real, tmp_path):
        """wxcc's global `Flow Type`/`flowType` -> --type is NOT NEEDED: wxcli
        spells it --flow-type, as on cc-flow. No Flow Store command offers
        --type."""
        for module in FATE_TABLE_SURFACE:
            assert '"--type"' not in real.src[module], module
        assert '"--flow-type"' in real.src["cc_flow_store"]
        code = widgets(tmp_path)
        assert '"--flow-type"' in fn(code, "import") and '"--type"' not in code

    def test_per_op_cli_name_wins_over_global(self, tmp_path, monkeypatch):
        """A per-command flag rename: param_name_overrides (keyed on the
        command name) changes the flag and leaves the wire name."""
        ovr = mini_overrides()
        _tag(ovr)["param_name_overrides"] = {"import": {"Flow Type": "zzz"}}
        code = widgets(tmp_path, ovr)
        assert '"--zzz"' in fn(code, "import") and '"--flow-type"' not in fn(code, "import")
        app, calls, _ = load_app(code, monkeypatch)
        r = invoke(app, "import", "P", "--file", str(upload(tmp_path)), "--zzz", "FLOW")
        assert r.exit_code == 0, r.output
        assert calls[0][2]["params"] == {"Flow Type": "FLOW"}

    def test_success_echo(self, tmp_path, monkeypatch):
        """EXISTS: an empty-body mutation prints the renderer's own message —
        prose for table output, a structured result for JSON."""
        app, _calls, emitted = load_app(widgets(tmp_path), monkeypatch, response={})
        r = invoke(app, "delete", "P", "W1", "--force", "yes", "-o", "table")
        assert r.exit_code == 0 and "Deleted: W1" in r.output
        r = invoke(app, "delete", "P", "W1", "--force", "yes", "-o", "json")
        assert r.exit_code == 0 and emitted == [{"status": "deleted", "id": "W1"}]

    def test_promote_to_argument(self, real, tmp_path):
        """NOT NEEDED: wxcli renders query parameters as flags."""
        code = widgets(tmp_path)
        assert 'kind: str = typer.Option(None, "--kind"' in code
        assert "kind: str = typer.Argument(" not in code
        assert 'source_flow_id: str = typer.Option(..., "--source-flow-id"' in \
            fn(real.src["cc_flow_store"], "copy")

    def test_expose_path_param(self, real):
        """NOT NEEDED: PROJECT_ID is already the first positional argument of
        every Flow Store command whose path holds it (P2-2)."""
        seen = 0
        for module in FATE_TABLE_SURFACE:
            assert "--project-id" not in real.src[module]
            for name in visible_commands(real.src[module]):
                body = fn(real.src[module], name)
                if "/project/{project_id}" not in body:
                    continue
                seen += 1
                first = body.split("(\n", 1)[1].lstrip()
                assert first.startswith("project_id: str = typer.Argument("), (module, name)
        assert seen > 20


# ── wxcc top-level promotions -> the group surface ───────────────────────────
# `top_level_commands` is NOT NEEDED: wxcli has no root promotion; groups are
# the namespace. Each case pins that surface on the real regen instead.

# wxcc's top_level_commands names (its flow-store-overrides.yaml).
WXCC_ROOT_NAMES = {
    "get", "prefs", "tags", "tag-history", "user-prefs", "resource-collections",
    "interaction", "analytics", "project", "versions", "templates", "projects",
    "interactions", "lock", "unlock", "delete", "copy", "revert",
    "variable-mapping", "connector-list", "connector", "global-vars",
    "activities", "check", "list", "draft", "export", "export-ui",
    "template-get", "create", "save-draft", "patch", "prefs-set", "prefs-add",
    "prefs-rm", "import-ui", "consume", "consume-template", "publish"}


def real_operations(real, monkeypatch) -> set[tuple[str, str]]:
    """(METHOD, normalized path) of every command in the real regen, read off
    the source by the drift gate's own parser."""
    monkeypatch.setattr(drift_check, "COMMANDS_DIR", real.dir)
    return {op for module in FATE_TABLE_SURFACE
            for ops in drift_check.parse_module_commands(module).values() for op in ops}


class TestPromotions:
    def test_build_promotions_maps_opid_to_command(self, real):
        """The real groups expose exactly the fate table's (b) surface."""
        assert set(real.src) - {"_registry"} == set(FATE_TABLE_SURFACE)
        for module, commands in FATE_TABLE_SURFACE.items():
            assert visible_commands(real.src[module]) == commands, module

    def test_promote_blocked_op_fails(self, real, monkeypatch):
        """A blocked operation is a visible stub in its own group (fate row 2:
        `cc-flow-store update-metadata` exits 2 and points to cc-flow update)."""
        code = real.src["cc_flow_store"]
        assert "update-metadata" in visible_commands(code)
        app, calls, _ = load_app(code, monkeypatch)
        r = invoke(app, "update-metadata", "P", "F")
        assert r.exit_code == 2 and "wxcli cc-flow update" in r.output
        assert calls == []

    def test_promote_skipped_op_fails(self, real, monkeypatch):
        """Every operation operation_overrides skips is absent from every
        group, while a rendered operation is found (control). A skipped
        trailing-slash duplicate (copyFlow_1) normalizes onto its rendered twin
        (copyFlow), so it is compared by its unskipped twin's absence only."""
        raw = yaml.safe_load((REPO / "tools" / "field_overrides.yaml").read_text())
        spec = json.loads(REAL_SPEC.read_text())
        resolved = gc.resolve_operation_overrides(raw["operation_overrides"], spec, SPEC_NAME)
        skip_keys = {k for k, v in resolved.items() if "skip" in v}
        kept = {(m.upper(), drift_check.normalize_path(p))
                for p, path_obj in spec["paths"].items() for m in path_obj
                if (m.upper(), p) not in skip_keys}
        skipped = {(m, drift_check.normalize_path(p)) for m, p in skip_keys} - kept
        assert len(skipped) >= 30
        rendered = real_operations(real, monkeypatch)
        assert ("GET", "/{}/project/{}/flows/{}") in rendered        # findFlowById
        assert skipped & rendered == set()

    def test_promote_duplicate_name_fails(self, real):
        """No Flow Store module registers one name twice."""
        for module in FATE_TABLE_SURFACE:
            counts = collections.Counter(n for n, _hid in DECORATOR.findall(real.src[module]))
            assert {n: c for n, c in counts.items() if c > 1} == {}, module

    def test_render_init_emits_promotion_scaffold(self, real):
        """The emitted manifest is _registry.py: one (module, cc- group) pair per
        Flow Store group, and nothing else."""
        registry = real.src["_registry"]
        pairs = re.findall(r'^    \("(\w+)", "([\w-]+)"\),$', registry, re.M)
        assert sorted(pairs) == sorted((m, m.replace("_", "-")) for m in FATE_TABLE_SURFACE)
        assert "_PROMOTIONS" not in registry

    def test_manifest_annotates_top_level(self):
        """None of wxcc's root-promoted names is a root command of wxcli."""
        _surface, top_level = drift_check.build_cli_surface()
        assert "whoami" in top_level                                  # control
        assert top_level & WXCC_ROOT_NAMES == set()


# ── wxcc Phase-C parity features ─────────────────────────────────────────────

CC_FLOW = (REPO / "src" / "wxcli" / "commands" / "cc_flow.py").read_text()


def unblocked() -> dict:
    """mini_overrides with mergeWidget rendered as a real PATCH (merge-patch)."""
    ovr = mini_overrides()
    del _op(ovr)["mergeWidget"]
    return ovr


class TestPhaseCFeatures:
    def test_auto_resolve_renders_prefetch(self, tmp_path, monkeypatch):
        """NOT NEEDED (`auto_resolve_params`: both users are fate (a)). The
        expected version is a plain flag, sent only when given, in one request
        with no pre-fetch; `cc-flow create-flows` and `cc-flow update` take
        --expected-version (P2-3)."""
        app, calls, _ = load_app(widgets(tmp_path, unblocked()), monkeypatch)
        r = invoke(app, "merge-patch", "P", "W1", "--json-body", "{}")
        assert r.exit_code == 0, r.output
        r = invoke(app, "merge-patch", "P", "W1", "--json-body", "{}", "--expected-version", "3")
        assert r.exit_code == 0, r.output
        assert [(c[0], c[2]["params"]) for c in calls] == [
            ("rest_patch", {}), ("rest_patch", {"expectedVersion": "3"})]
        for name in ("create-flows", "update"):
            assert '"--expected-version"' in fn(CC_FLOW, name), name

    def test_auto_resolve_lint_rejects_non_query_param(self, tmp_path):
        """An override naming a parameter the command does not declare is
        refused: param_name_overrides raises ParamNameOverrideError."""
        ovr = mini_overrides()
        _tag(ovr)["param_name_overrides"] = {"import": {"notAParam": "zzz"}}
        with pytest.raises(ParamNameOverrideError, match="notAParam"):
            widgets(tmp_path, ovr)

    def test_auto_resolve_lint_requires_field(self, tmp_path, capsys):
        """A malformed operation override is refused: exit_code_from needs
        json_key."""
        ovr = mini_overrides()
        _op(ovr)["refreshWidgets"] = {"exit_code_from": {"invert": True}}
        with pytest.raises(SystemExit) as exc:
            generate(tmp_path, ovr)
        assert exc.value.code == 1
        assert "exit_code_from must be {json_key" in capsys.readouterr().err

    def test_param_defaults_setdefault_after_query_build(self, tmp_path, monkeypatch):
        """NOT NEEDED (`param_defaults`: both users are fate (a)). Nothing is
        sent unless the caller passes it; the command map passes `cc-flow
        export --version draft`. (It also passed `cc-flow publish
        --skip-validation true` until upstream dropped the skipValidation query
        parameter on 2026-10-26; publish now always validates.)"""
        app, calls, _ = load_app(widgets(tmp_path), monkeypatch)
        assert invoke(app, "show", "P").exit_code == 0
        assert invoke(app, "show", "P", "--kind", "A").exit_code == 0
        assert [c[2]["params"] for c in calls] == [{}, {"kind": "A"}]
        assert '"--version"' in fn(CC_FLOW, "export")
        assert '"--skip-validation"' not in fn(CC_FLOW, "publish")

    def test_require_some_body_guard(self):
        """NOT NEEDED: wxcc's only `require_some_body` user was the `update`
        clone (extra_commands, fate row 24), served by `cc-flow update
        --json-body`."""
        assert '"--json-body"' in fn(CC_FLOW, "update")
        assert 'short_help="Patch a Flow or Subflow Draft."' in fn(CC_FLOW, "update")

    def test_body_positional_list_and_confirm_message(self, tmp_path, monkeypatch):
        """`body_positional_list` -> VERIFY Task 10: the array DELETE body goes
        through --json-body. `confirm_message` -> EXISTS: command_confirms."""
        code = (generate(tmp_path, mini_overrides(), None, "--tag", "WidgetTags")
                / "widgettags.py").read_text()
        app, calls, _ = load_app(code, monkeypatch, response={})
        # One-command group: Typer runs it as the app, so argv starts at its arguments.
        r = invoke(app, "P", "W1", "--json-body", '["a", "b"]', "--force")
        assert r.exit_code == 0, r.output
        assert calls[0][0] == "rest_delete" and calls[0][2]["json"] == ["a", "b"]
        ovr = mini_overrides()
        _tag(ovr)["command_confirms"] = {"refresh": "Refresh every widget in the project?"}
        code = widgets(tmp_path, ovr)
        assert 'typer.confirm("Refresh every widget in the project?", abort=True)' in fn(code, "refresh")
        from typer.testing import CliRunner
        app, calls, _ = load_app(code, monkeypatch)
        r = CliRunner().invoke(app, ["refresh", "P"], input="n\n")
        assert r.exit_code == 1 and calls == []
        assert invoke(app, "refresh", "P", "--force").exit_code == 0
        assert [c[0] for c in calls] == ["rest_post"]

    def test_body_positional_list_lint_requires_arg(self, tmp_path, capsys):
        """A command-keyed override naming no command is refused: the generator
        exits 1 naming it, before the renderer's own CommandConfirmError."""
        ovr = mini_overrides()
        _tag(ovr)["command_confirms"] = {"no-such-command": "x"}
        with pytest.raises(SystemExit) as exc:
            widgets(tmp_path, ovr)
        assert exc.value.code == 1
        assert "no-such-command" in capsys.readouterr().err

    def test_value_mapped_bool_flag(self, real, monkeypatch):
        """NOT NEEDED (`param_flag_inversions`): withDraftVersions is a string
        flag whose help carries the trap, and the value goes out as typed."""
        code = real.src["cc_flow_store"]
        assert ('with_draft_versions: str = typer.Option(None, "--with-draft-versions", '
                'help="yes or no (server default: no) — the server treats `true` as no")') in code
        app, calls, _ = load_app(code, monkeypatch)
        r = invoke(app, "list-usages", "P", "--with-draft-versions", "yes")
        assert r.exit_code == 0, r.output
        assert calls[-1][2]["params"]["withDraftVersions"] == "yes"

    def test_file_not_found_guard(self, tmp_path, monkeypatch):
        """A missing upload file fails cleanly (exit 2), before any request."""
        app, calls, _ = load_app(widgets(tmp_path), monkeypatch)
        r = invoke(app, "import", "P", "--file", str(tmp_path / "no-such.json"))
        assert r.exit_code == 2 and "does not exist" in r.output
        assert calls == []

    def test_auto_resolve_after_body_guards(self, tmp_path, monkeypatch):
        """Client-side errors fire before any request: a missing required
        option exits 2, a missing required body field exits 1."""
        app, calls, _ = load_app(widgets(tmp_path), monkeypatch)
        assert invoke(app, "import", "P").exit_code == 2
        assert invoke(app, "create", "P").exit_code == 1
        assert calls == []


# ── flag help: param_help and _all.param_help (Task 10) ──────────────────────

class TestParamHelp:
    """Precedence: per-operation param_help > spec text (description or enum
    choices) > `_all.param_help`, which only fills an empty description."""

    @staticmethod
    def render(base, ops: dict) -> str:
        ovr = unblocked()
        _op(ovr).update(ops)
        return widgets(base, ovr)

    def test_per_op_param_help_lands(self, tmp_path):
        code = self.render(tmp_path, {"mergeWidget": {"param_help": {"flowType": "FLOW or SUBFLOW"}}})
        assert '"--flow-type", help="FLOW or SUBFLOW"' in fn(code, "merge-patch")
        ast.parse(code)

    def test_global_param_help_fills_empty_description(self, tmp_path):
        code = self.render(tmp_path, {"_all": {"param_help": {"flowType": "FLOW or SUBFLOW (default FLOW)"}}})
        assert '"--flow-type", help="FLOW or SUBFLOW (default FLOW)"' in fn(code, "merge-patch")

    def test_spec_description_beats_global(self, tmp_path):
        code = self.render(tmp_path, {"_all": {"param_help": {"expectedVersion": "MUST NOT APPEAR"}}})
        assert "MUST NOT APPEAR" not in code
        assert '"--expected-version", help="Optimistic-lock version"' in code

    def test_enum_choices_beat_global(self, tmp_path):
        code = self.render(tmp_path, {"_all": {"param_help": {"kind": "MUST NOT APPEAR"}}})
        assert "MUST NOT APPEAR" not in code
        assert '"--kind", help="Choices: A, B"' in code

    def test_per_op_beats_spec_description(self, tmp_path):
        code = self.render(tmp_path, {"mergeWidget": {"param_help": {"expectedVersion": "per-op override"}}})
        assert '"--expected-version", help="per-op override"' in code
        assert "Optimistic-lock version" not in code

    def test_per_op_beats_global(self, tmp_path):
        code = self.render(tmp_path, {
            "mergeWidget": {"param_help": {"flowType": "per-op text"}},
            "_all": {"param_help": {"flowType": "global text"}}})
        assert '"--flow-type", help="per-op text"' in code
        assert "global text" not in code       # flowType exists only on mergeWidget

    def test_lint_rejects_unknown_opid(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            self.render(tmp_path, {"notARealOp": {"param_help": {"flowType": "x"}}})
        assert exc.value.code == 1 and "notARealOp" in capsys.readouterr().err

    def test_lint_rejects_unknown_param_name(self, tmp_path):
        with pytest.raises(OperationOverrideRenderError, match="notAParam"):
            self.render(tmp_path, {"mergeWidget": {"param_help": {"notAParam": "x"}}})

    @pytest.mark.xfail(strict=True, reason=(
        "gap (Plan 2 T17 finding): `_all.param_help` naming a parameter no "
        "operation declares is accepted silently; wxcc's lint refused it, and "
        "drift check 15 treats `_all` as never inert"))
    def test_lint_rejects_global_name_on_no_op(self, tmp_path):
        with pytest.raises((SystemExit, OperationOverrideRenderError)):
            self.render(tmp_path, {"_all": {"param_help": {"noSuchParam": "x"}}})


# ── wxcc extra_commands (clones) ─────────────────────────────────────────────
# NOT NEEDED: both clones are fate (a) — `search` is `cc-flow list
# --partial-name-search` (row 5), `update` is `cc-flow update` (row 24). wxops
# renders one command per operation.

class TestExtraCommands:
    def test_clone_renders_alongside_base(self, real):
        """One command per operation: the real regen registers no clone, and
        the clone's job is a flag on `cc-flow list`."""
        names = [n for m in FATE_TABLE_SURFACE for n, _h in DECORATOR.findall(real.src[m])]
        assert "search" not in names
        assert sum(len(c) for c in FATE_TABLE_SURFACE.values()) == len(names)
        assert '"--partial-name-search"' in fn(CC_FLOW, "list")

    def test_clone_clears_inherited_key_with_none(self, tmp_path):
        """warn is per operation, so nothing is inherited to clear: one banner,
        on refresh only."""
        code = widgets(tmp_path)
        assert code.count("Warning: ") == 1
        assert "Warning: may be slow on big orgs" in fn(code, "refresh")

    def test_clone_of_skipped_or_blocked_fails(self, tmp_path, capsys):
        """skip and blocked replace the command, so no other key may sit beside
        them."""
        for inner in ({"skip": "x", "warn": "y"}, {"blocked": "x", "param_help": {"kind": "y"}}):
            ovr = mini_overrides()
            _op(ovr)["findWidgets"] = inner
            with pytest.raises(SystemExit) as exc:
                generate(tmp_path, ovr)
            assert exc.value.code == 1
            assert "replaces the command" in capsys.readouterr().err

    def test_clone_lint_rejects_unknown_override_key(self, tmp_path, capsys):
        ovr = mini_overrides()
        _op(ovr)["findWidgets"] = {"warn_endpoints": "wrong-level key"}
        with pytest.raises(SystemExit) as exc:
            generate(tmp_path, ovr)
        assert exc.value.code == 1
        assert "unknown key(s) warn_endpoints" in capsys.readouterr().err

    def test_clone_promotes_via_top_level(self):
        """The `update` clone's job (rename/describe a draft) is `cc-flow update
        P F --json-body '{"name": …}'`, the command update-metadata's stub
        points to."""
        update = fn(CC_FLOW, "update")
        assert '"--json-body"' in update and "flow_id: str = typer.Argument(" in update

    def test_clone_top_level_name_collision_fails(self, tmp_path, capsys):
        """Two entries naming one operation (by operationId and by
        METHOD /path) are refused."""
        ovr = mini_overrides()
        _op(ovr)["GET " + WIDGETS] = {"warn": "a"}
        _op(ovr)["findWidgets"] = {"warn": "b"}
        with pytest.raises(SystemExit) as exc:
            generate(tmp_path, ovr)
        assert exc.value.code == 1
        assert "both name GET " + WIDGETS in capsys.readouterr().err


# ── wxcc generated.register() guard -> GROUP_EXTENSIONS (Task 11) ────────────

LAZY = (REPO / "src" / "wxcli" / "commands" / "_lazy.py").read_text()


class TestPromotionRuntime:
    def test_collision_raises_when_hand_command_present(self):
        """wxcc refused, at register time, a promotion onto a hand command's
        name. wxcli mounts hand-written commands onto a generated group
        (GROUP_EXTENSIONS) with no runtime guard, so the invariant is pinned
        statically: no extension command shares a name with its group's
        generated commands."""
        extensions = drift_check.parse_extension_commands()
        assert ("cc-flow", "show-node-template") in extensions          # control
        for group, module in drift_check.parse_registrations().items():
            path = REPO / "src" / "wxcli" / "commands" / f"{module}.py"
            if not path.exists():
                continue
            generated = {n for n, _h in DECORATOR.findall(path.read_text())}
            mounted = {cmd for g, cmd in extensions if g == group}
            assert generated & mounted == set(), group

    def test_register_promotes_when_clean(self, real):
        """The shipped manifest mounts the six Flow Store groups exactly as the
        regen writes them, and cc-flow's hand-written commands are declared as
        an extension."""
        registrations = drift_check.parse_registrations()
        for module in FATE_TABLE_SURFACE:
            assert registrations[module.replace("_", "-")] == module
        shipped = (REPO / "src" / "wxcli" / "commands" / "_registry.py").read_text()
        for line in real.src["_registry"].splitlines():
            if line.startswith('    ("'):
                assert line in shipped, line
        assert '("cc-flow", "cc_flow_authoring")' in LAZY
