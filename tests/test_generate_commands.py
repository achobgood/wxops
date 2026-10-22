"""Tests for generate_commands.py — the CLI orchestrator that ties parser + renderer together."""

import json
import sys
from pathlib import Path

import pytest

from tools.generate_commands import generate_tag, merge_tags, should_skip_tag, main, resolve_cli_name_overrides, resolve_tag_merge


FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_SPEC = FIXTURES / "mini-openapi.json"


@pytest.fixture
def spec():
    with open(FIXTURE_SPEC) as f:
        return json.load(f)


@pytest.fixture
def overrides():
    return {"omit_query_params": ["orgId"]}


# ── generate_tag ─────────────────────────────────────────────────────────────


class TestGenerateTag:
    def test_generates_file(self, spec, overrides, tmp_path):
        """generate_tag writes a .py file to the output directory."""
        seen = set()
        module, cli, count = generate_tag("Things", spec, overrides, tmp_path, False, seen)
        assert module == "things"
        assert cli == "things"
        assert count > 0
        out_file = tmp_path / "things.py"
        assert out_file.exists()
        assert len(out_file.read_text()) > 100

    def test_dry_run_no_file(self, spec, overrides, tmp_path, capsys):
        """dry_run=True prints info but writes no file."""
        seen = set()
        module, cli, count = generate_tag("Things", spec, overrides, tmp_path, True, seen)
        assert count > 0
        assert not (tmp_path / "things.py").exists()
        captured = capsys.readouterr()
        assert "Things" in captured.out
        assert "things.py" in captured.out

    def test_dry_run_shows_commands(self, spec, overrides, tmp_path, capsys):
        """dry_run output lists each command with method and type."""
        seen = set()
        generate_tag("Things", spec, overrides, tmp_path, True, seen)
        captured = capsys.readouterr()
        assert "GET" in captured.out
        assert "POST" in captured.out
        assert "list" in captured.out

    def test_dry_run_shows_skipped_uploads(self, spec, overrides, tmp_path, capsys):
        """dry_run output shows skipped upload endpoints."""
        seen = set()
        generate_tag("Things", spec, overrides, tmp_path, True, seen)
        captured = capsys.readouterr()
        assert "SKIP" in captured.out
        assert "upload" in captured.out.lower()

    def test_cli_name_override(self, spec, tmp_path):
        """cli_name_overrides in overrides → uses override name."""
        overrides = {
            "omit_query_params": ["orgId"],
            "_resolved_cli_name_overrides": {"Things": "my-things"},
        }
        seen = set()
        module, cli, count = generate_tag("Things", spec, overrides, tmp_path, False, seen)
        assert cli == "my-things"
        assert module == "my_things"
        assert (tmp_path / "my_things.py").exists()

    def test_auto_inject_from_config(self, spec, tmp_path):
        """auto_inject_from_config generates get_org_id() calls instead of CLI flags."""
        overrides = {
            "auto_inject_from_config": ["orgId"],
        }
        seen = set()
        module, cli, count = generate_tag("Things", spec, overrides, tmp_path, False, seen)
        code = (tmp_path / f"{module}.py").read_text()
        # orgId should NOT appear as a CLI flag (--org-id)
        assert "--org-id" not in code
        # But should appear as auto-injected from config
        assert "get_org_id" in code

    def test_seen_op_ids_shared(self, spec, overrides, tmp_path):
        """Seen operation IDs prevent duplicate processing across tags."""
        seen = set()
        _, _, count1 = generate_tag("Things", spec, overrides, tmp_path, True, seen)
        _, _, count2 = generate_tag("Things", spec, overrides, tmp_path, True, seen)
        assert count1 > 0
        assert count2 == 0  # All ops already seen

    def test_endpoint_overrides_applied(self, spec, tmp_path):
        """Folder-level overrides (e.g. table_columns) are applied."""
        overrides = {
            "omit_query_params": ["orgId"],
            "_tag_ovr:Things": {
                "list": {"table_columns": [["Custom", "customField"]]},
            },
        }
        seen = set()
        module, _, _ = generate_tag("Things", spec, overrides, tmp_path, False, seen)
        code = (tmp_path / f"{module}.py").read_text()
        assert "customField" in code

    def test_generated_output_includes_registration_info(self, spec, overrides, tmp_path, capsys):
        """Non-dry-run prints total + registration block."""
        seen = set()
        generate_tag("Things", spec, overrides, tmp_path, False, seen)
        captured = capsys.readouterr()
        assert "Generated:" in captured.out
        assert "things.py" in captured.out


class TestTablelessOverrideGuard:
    """A table override on a command that renders no list is inert:
    `_render_show_command` reads no columns and no list key. Drift check 31
    (2026-10-13) re-rendered 107 list GETs as single-object reads and silently
    retired 11 table_columns entries that way; the generator now refuses one."""

    COLS = [["ID", "id"]]

    @pytest.mark.parametrize("family,cmd", [
        ("table_columns", "show"),
        ("table_columns", "show-settings"),     # settings-get
        ("response_list_keys", "show"),
    ])
    def test_override_on_a_single_object_read_fails(self, spec, tmp_path,
                                                     capsys, family, cmd):
        value = self.COLS if family == "table_columns" else "items"
        overrides = {"omit_query_params": ["orgId"],
                     "_tag_ovr:Things": {family: {cmd: value}}}
        with pytest.raises(SystemExit) as exc:
            generate_tag("Things", spec, overrides, tmp_path, True, set())
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert f"{family} in tag 'Things'" in err and "render no list" in err
        assert cmd in err

    def test_override_on_a_list_passes(self, spec, tmp_path):
        """Control: the same entry on a list command is accepted."""
        overrides = {"omit_query_params": ["orgId"],
                     "_tag_ovr:Things": {"table_columns": {
                         "list": self.COLS, "list-tags": self.COLS}}}
        _, _, count = generate_tag("Things", spec, overrides, tmp_path, True,
                                   set())
        assert count > 0


# ── main() via monkeypatch (in-process, so coverage tracks it) ───────────────


class TestMainCLI:
    """Test main() by monkeypatching sys.argv. Runs in-process for coverage."""

    def _run_main(self, monkeypatch, *args):
        """Patch sys.argv and call main(), catching SystemExit."""
        monkeypatch.setattr(sys, "argv", ["generate_commands", *args])
        try:
            main()
            return 0
        except SystemExit as e:
            return e.code or 0

    def test_list_tags(self, monkeypatch, capsys):
        """--list-tags prints all tags from the fixture spec."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC), "--list-tags")
        assert rc == 0
        assert "Things" in capsys.readouterr().out

    def test_list_folders_alias(self, monkeypatch, capsys):
        """--list-folders is a backward-compat alias for --list-tags."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC), "--list-folders")
        assert rc == 0
        assert "Things" in capsys.readouterr().out

    def test_dry_run_single_tag(self, monkeypatch, capsys, tmp_path):
        """--tag X --dry-run prints info, writes nothing."""
        rc = self._run_main(
            monkeypatch, "--spec", str(FIXTURE_SPEC), "--tag", "Things",
            "--dry-run", "--output", str(tmp_path),
        )
        assert rc == 0
        assert "Things" in capsys.readouterr().out
        assert not list(tmp_path.glob("*.py"))

    def test_generate_single_tag(self, monkeypatch, capsys, tmp_path):
        """--tag X writes a command file."""
        rc = self._run_main(
            monkeypatch, "--spec", str(FIXTURE_SPEC), "--tag", "Things",
            "--output", str(tmp_path),
        )
        assert rc == 0
        assert (tmp_path / "things.py").exists()

    def test_generate_all(self, monkeypatch, capsys, tmp_path):
        """--all generates files for all non-skipped tags."""
        rc = self._run_main(
            monkeypatch, "--spec", str(FIXTURE_SPEC), "--all",
            "--output", str(tmp_path),
        )
        assert rc == 0
        captured = capsys.readouterr().out
        py_files = list(tmp_path.glob("*.py"))
        assert len(py_files) >= 5
        assert "Total:" in captured
        assert "Manifest: _registry.py updated" in captured
        registry = (tmp_path / "_registry.py").read_text()
        assert "GENERATED_GROUPS = [" in registry
        assert '("things", "things"),' in registry

    def test_folder_alias(self, monkeypatch, capsys, tmp_path):
        """--folder is a backward-compat alias for --tag."""
        rc = self._run_main(
            monkeypatch, "--spec", str(FIXTURE_SPEC), "--folder", "Things",
            "--dry-run", "--output", str(tmp_path),
        )
        assert rc == 0
        assert "Things" in capsys.readouterr().out

    def test_missing_spec_exits_1(self, monkeypatch, capsys):
        """Non-existent spec file → exit 1 with error message."""
        rc = self._run_main(monkeypatch, "--spec", "/nonexistent/spec.json", "--list-tags")
        assert rc == 1
        assert "Spec not found" in capsys.readouterr().err

    def test_unknown_tag_exits_1(self, monkeypatch, capsys):
        """Non-existent tag → exit 1 with suggestion."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC), "--tag", "Nonexistent")
        assert rc == 1
        assert "Tag not found" in capsys.readouterr().err

    def test_similar_tag_suggestion(self, monkeypatch, capsys):
        """Misspelled tag → 'Did you mean' suggestion."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC), "--tag", "thing")
        assert rc == 1
        assert "Did you mean" in capsys.readouterr().err

    def test_no_args_shows_help(self, monkeypatch, capsys):
        """No arguments → shows help."""
        rc = self._run_main(monkeypatch, "--spec", str(FIXTURE_SPEC))
        assert rc == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "Generate" in captured.out


# ── resolve_cli_name_overrides ─────────────────────────────────────────────


class TestResolveCliNameOverrides:
    def test_flat_format(self):
        """Legacy flat dict format still works."""
        raw = {"Flow": "cc-flow", "Things": "things-group"}
        result = resolve_cli_name_overrides(raw, "webex-contact-center.json")
        assert result == {"Flow": "cc-flow", "Things": "things-group"}

    def test_per_spec_format(self):
        """Per-spec dict with _global merges correctly."""
        raw = {
            "_global": {"Things": "things-group"},
            "webex-flow-store.json": {"Flow": "fs-flows"},
        }
        result = resolve_cli_name_overrides(raw, "webex-flow-store.json")
        assert result == {"Things": "things-group", "Flow": "fs-flows"}

    def test_per_spec_overrides_global(self):
        """Per-spec entry overrides _global for same tag."""
        raw = {
            "_global": {"Flow": "cc-flow"},
            "webex-flow-store.json": {"Flow": "fs-flows"},
        }
        result = resolve_cli_name_overrides(raw, "webex-flow-store.json")
        assert result["Flow"] == "fs-flows"

    def test_per_spec_no_match_uses_global_only(self):
        """Spec with no dedicated section gets only _global."""
        raw = {
            "_global": {"Flow": "cc-flow"},
            "webex-flow-store.json": {"Flow": "fs-flows"},
        }
        result = resolve_cli_name_overrides(raw, "webex-admin.json")
        assert result == {"Flow": "cc-flow"}

    def test_none_returns_empty(self):
        result = resolve_cli_name_overrides(None, "any.json")
        assert result == {}


# ── resolve_tag_merge ──────────────────────────────────────────────────────


class TestResolveTagMerge:
    def test_flat_format(self):
        """Legacy flat dict format still works."""
        raw = {"User Call Settings": ["User Call Settings (1/2)", "User Call Settings (2/2)"]}
        result = resolve_tag_merge(raw, "webex-cloud-calling.json")
        assert result == raw

    def test_per_spec_format(self):
        """Per-spec dict with _global merges correctly."""
        raw = {
            "_global": {"A": ["A1", "A2"]},
            "webex-flow-store.json": {"Flow": ["Flow APIs"]},
        }
        result = resolve_tag_merge(raw, "webex-flow-store.json")
        assert result == {"A": ["A1", "A2"], "Flow": ["Flow APIs"]}

    def test_per_spec_no_match(self):
        raw = {
            "_global": {"A": ["A1"]},
            "webex-flow-store.json": {"Flow": ["Flow APIs"]},
        }
        result = resolve_tag_merge(raw, "webex-admin.json")
        assert result == {"A": ["A1"]}

    def test_none_returns_empty(self):
        result = resolve_tag_merge(None, "any.json")
        assert result == {}


# ── Activity-catalog carve-out (ADR-11 amendment, 2026-10-13) ───────────────


class TestActivityCatalogCarveOut:
    """The CC spec's "Activities"/"Events" tags render into cc-flow via
    tag_merge; "Templates" stays skipped with the retired Flow Store surface.

    The carve-out is a whole-TAG merge, so its narrowness rests on what those
    two tags contain. This pins it: an upstream addition to either tag (the
    `.../activities/{name}/schema` path, which 404s live, is the obvious
    candidate) fails here and forces a decision, instead of rendering an
    unverified command into cc-flow on the next spec sync.
    """

    REPO = Path(__file__).parent.parent
    CARVED = {
        "Activities": {"listActivityDefinitions", "describeActivity",
                       "getActivityInputChoices"},
        "Events": {"listEventSpecifications"},
    }

    def _ops_by_tag(self):
        spec = json.loads((self.REPO / "specs" / "webex-contact-center.json").read_text())
        out: dict[str, set[str]] = {}
        for methods in spec["paths"].values():
            for op in methods.values():
                if isinstance(op, dict):
                    for tag in op.get("tags", []):
                        out.setdefault(tag, set()).add(op.get("operationId"))
        return out

    def _overrides(self):
        import yaml
        return yaml.safe_load((self.REPO / "tools" / "field_overrides.yaml").read_text())

    def test_carved_tags_hold_exactly_the_live_verified_ops(self):
        ops = self._ops_by_tag()
        for tag, expected in self.CARVED.items():
            assert ops.get(tag) == expected, (
                f"{tag} now carries {sorted(ops.get(tag, set()))}; only "
                f"{sorted(expected)} were verified live on the CC host. Verify "
                f"the new op(s) read-only, then update this test and ADR-11 — "
                f"or exclude them with tag_op_excludes.")

    def test_merged_into_flows_and_templates_rendered_apart(self):
        ovr = self._overrides()
        merge = resolve_tag_merge(ovr["tag_merge"], "webex-contact-center.json")
        assert set(merge.get("Flows", [])) == set(self.CARVED)
        skipped = ovr["skip_tags"]["webex-contact-center.json"]
        # Plan 2 Task 14: the template catalog renders as its own group,
        # cc-flow-templates, never into cc-flow (TEMPLATES_SOURCE = this spec,
        # docs/merge/flow-store-host-map.md § Decision).
        assert "Templates" not in skipped
        assert "Templates" not in merge.get("Flows", [])
        names = resolve_cli_name_overrides(ovr["cli_name_overrides"],
                                           "webex-contact-center.json")
        assert names.get("Templates") == "cc-flow-templates"
        assert not set(self.CARVED) & set(skipped), (
            "a carved tag is also skipped — after tag_merge it would render, "
            "but drift check 1 (which reads raw tags) would call it a deliberate gap")

    def test_shipped_cc_flow_carries_the_catalog_and_keeps_flow_names(self):
        src = (self.REPO / "src" / "wxcli" / "commands" / "cc_flow.py").read_text()
        for name in ("list-activities", "show-activity", "list-activity-choices",
                     "list-event-specifications"):
            assert f'@app.command("{name}", short_help=' in src
        # The swap must hand the bare names back to the flow operations.
        list_fn = src[src.index('@app.command("list", short_help='):]
        assert "/flows\"" in list_fn.split("\n@app.command")[0]
        assert "/templates" not in src

    # The flowType/checkUiEnabled/activityName options (Plan 2 Task 14,
    # docs/merge/activities-flowtype-check.md). They drive the SHIPPED
    # cc_flow.py through CliRunner, exec'd with its wxcli imports stubbed
    # (TestOperationOverrides._load_app), so wxcli is never imported and no
    # call can reach the network.
    def _cc_flow_app(self, monkeypatch):
        code = (self.REPO / "src" / "wxcli" / "commands" / "cc_flow.py").read_text()
        return TestOperationOverrides._load_app(code, monkeypatch, response=[])

    ACTIVITY_READS = (
        ["list-activities", "P"],
        ["show-activity", "P", "queue-contact"],
        ["list-activity-choices", "P", "queue-contact", "channelType"],
    )

    def test_activity_reads_send_flow_type(self, monkeypatch):
        from typer.testing import CliRunner
        for argv in self.ACTIVITY_READS:
            app, calls = self._cc_flow_app(monkeypatch)
            r = CliRunner().invoke(app, argv + ["--flow-type", "SUBFLOW"])
            assert r.exit_code == 0, (argv, r.output)
            assert len(calls) == 1 and calls[0][0] == "rest_get", argv
            assert calls[0][2]["params"]["flowType"] == "SUBFLOW", argv
            # Without the flag nothing is sent: the server default (FLOW)
            # applies, which verdict #3 measured equal to FLOW.
            app, calls = self._cc_flow_app(monkeypatch)
            r = CliRunner().invoke(app, argv)
            assert r.exit_code == 0, (argv, r.output)
            assert "flowType" not in (calls[0][2].get("params") or {}), argv

    def test_activity_list_omits_unproven_params(self, monkeypatch):
        from typer.testing import CliRunner
        app, calls = self._cc_flow_app(monkeypatch)
        r = CliRunner().invoke(app, ["list-activities", "--help"],
                               env={"COLUMNS": "400", "TERM": "dumb"})
        assert r.exit_code == 0, r.output
        # searchBy: the gateway ignored it (#4), so it gets no flag.
        assert "--search-by" not in r.output
        r = CliRunner().invoke(app, ["list-activities", "P", "--check-ui-enabled", "true"])
        assert r.exit_code == 0, r.output
        assert calls[-1][2]["params"]["checkUiEnabled"] == "true"
        r = CliRunner().invoke(app, ["list-activities", "P", "--activity-name", "queue-contact"])
        assert r.exit_code == 0, r.output
        assert calls[-1][2]["params"]["activityName"] == "queue-contact"


# ── cc-flow-templates list filter (Plan 2 Task 15c) ──────────────────────────


class TestFlowTemplatesFilter:
    """`cc-flow-templates list` filters on `flowType`, not the CC spec's `type`.

    Measured live 2026-10-19 on the sandbox tenant: `type=subflow` returned
    all 39 templates (Task 15b, docs/merge/e2e-flow-lifecycle.md row 7c);
    `flowType=SUBFLOW` returned only the 8 SUBFLOW ones
    (GTWY_2e46669b-621a-412f-96bb-5502e41e6d86). The table column reads
    `flowType` too: `type` is null on every template.
    """

    REPO = Path(__file__).parent.parent

    def _app(self, monkeypatch):
        code = (self.REPO / "src" / "wxcli" / "commands" / "cc_flow_templates.py").read_text()
        return TestOperationOverrides._load_app(code, monkeypatch, response=[])

    def test_list_sends_flow_type(self, monkeypatch):
        from typer.testing import CliRunner
        app, calls = self._app(monkeypatch)
        r = CliRunner().invoke(app, ["list", "--flow-type", "SUBFLOW"])
        assert r.exit_code == 0, r.output
        assert calls[-1][2]["params"] == {"flowType": "SUBFLOW"}
        app, calls = self._app(monkeypatch)
        r = CliRunner().invoke(app, ["list"])
        assert r.exit_code == 0, r.output
        assert "flowType" not in (calls[-1][2].get("params") or {})

    def test_list_has_no_ignored_type_option(self, monkeypatch):
        from typer.testing import CliRunner
        app, _ = self._app(monkeypatch)
        r = CliRunner().invoke(app, ["list", "--type", "subflow"])
        assert r.exit_code == 2, r.output

    def test_type_column_reads_flow_type(self):
        src = (self.REPO / "src" / "wxcli" / "commands" / "cc_flow_templates.py").read_text()
        assert "('Type', 'flowType')" in src
        assert "('Type', 'type')" not in src


class TestDropQueryParams:
    """`drop_query_params`: {command: {wire name: evidence}} removes a spec
    query parameter the server ignores, so no flag renders for it."""

    def _ep(self):
        from tools.postman_parser import Endpoint, EndpointField
        return Endpoint(name="List", method="GET", url_path="templates", path_vars=[],
                        query_params=[EndpointField(name="type", python_name="type",
                                                    field_type="str", description="")],
                        body_fields=[], command_type="list", command_name="list")

    def test_drops_the_named_param(self):
        from tools.postman_parser import apply_endpoint_overrides
        ep = self._ep()
        apply_endpoint_overrides(ep, {"drop_query_params": {"list": {"type": "ignored live"}}})
        assert [qp.name for qp in ep.query_params] == []

    def test_unknown_param_raises(self):
        from tools.postman_parser import apply_endpoint_overrides
        ep = self._ep()
        with pytest.raises(ValueError, match="drop_query_params"):
            apply_endpoint_overrides(ep, {"drop_query_params": {"list": {"kind": "x"}}})

    def test_is_command_keyed(self):
        from tools.generate_commands import COMMAND_KEYED_OVERRIDES
        assert "drop_query_params" in COMMAND_KEYED_OVERRIDES


# ── operation_overrides (Plan 2 Task 8) ──────────────────────────────────────


class TestOperationOverrides:
    """`operation_overrides`: skip / blocked / warn per operation, keyed by a
    unique operationId or "METHOD /path", plus the Flow Store base URL.

    The behavioural cases exec the RENDERED module with stubbed `wxcli`
    imports (the tests/test_query_body_param.py pattern), so wxcli itself is
    never imported and no command can reach the network.
    """

    FS_FIXTURE = Path(__file__).parent / "wxcc" / "fixtures" / "mini_flow_store.json"
    SPEC_NAME = "webex-cc-flow-store.json"
    PATCH_KEY = "PATCH /{orgId}/project/{projectId}/widgets/{widgetId}"

    def _fs_spec(self):
        return json.loads(self.FS_FIXTURE.read_text())

    def _generate(self, tmp_path, monkeypatch, op_overrides: dict,
                  tag: str = "Widgets", spec: dict | None = None) -> str:
        """Run main() on the fixture (or `spec`) saved under the Flow Store
        spec name, for one tag, and return that tag's module."""
        import yaml
        spec_path = tmp_path / self.SPEC_NAME
        spec_path.write_text(json.dumps(spec) if spec is not None
                             else self.FS_FIXTURE.read_text())
        ovr_path = tmp_path / "overrides.yaml"
        ovr_path.write_text(yaml.safe_dump({
            "auto_inject_from_config": ["orgId"],
            "operation_overrides": {self.SPEC_NAME: op_overrides},
        }))
        out = tmp_path / "out"
        monkeypatch.setattr(sys, "argv", [
            "generate_commands", "--spec", str(spec_path), "--overrides",
            str(ovr_path), "--output", str(out), "--tag", tag])
        main()
        return (out / f"{tag.lower()}.py").read_text()

    @staticmethod
    def _load_app(code: str, monkeypatch, response=None):
        """Exec a rendered module with every wxcli import stubbed. Any HTTP
        attempt — through the session stub or httpx itself — fails the test."""
        import httpx
        import typer

        def _no_http(*a, **k):
            raise AssertionError("an HTTP call was attempted")

        monkeypatch.setattr(httpx.Client, "send", _no_http)
        calls = []

        class _Session:
            def __getattr__(self, name):
                if name.startswith("rest_"):
                    def _record(url, *a, **k):
                        calls.append((name, url, k))
                        return {"id": "W1"} if response is None else response
                    return _record
                raise AttributeError(name)

        class _Api:
            session = _Session()

        class _WebexError(Exception):
            pass

        namespace = {
            "get_api": lambda debug=False: _Api(),
            "WebexError": _WebexError,
            "handle_rest_error": lambda e: (_ for _ in ()).throw(e),
            "handle_network_error": lambda e: (_ for _ in ()).throw(e),
            "print_table": lambda *a, **k: None,
            "print_json": lambda v, *a, **k: typer.echo(repr(v)),
            "emit": lambda v, **k: typer.echo(repr(v)),
            "load_json_body": lambda raw: json.loads(raw),
            "verify_write": lambda *a, **k: None,
            "get_org_id": lambda *a, **k: "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi9v",
            "resolve_org_id": lambda *a, **k: "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi9v",
            "get_cc_base_url": lambda *a, **k: "https://cc.test",
            "get_cc_org_id": lambda *a, **k: "org-uuid",
            "get_flow_store_base_url": lambda *a, **k: "https://fs.test/flow-store",
        }
        stripped = "\n".join(line for line in code.splitlines()
                             if not line.startswith("from wxcli"))
        exec(compile(stripped, "<rendered>", "exec"), namespace)
        return namespace["app"], calls

    def test_skip_drops_the_command(self, tmp_path, monkeypatch):
        code = self._generate(tmp_path, monkeypatch, {
            "deleteWidget": {"skip": "fate (a): served by cc-flow delete — EQUAL, Plan 2 T5"}})
        assert '@app.command("delete"' not in code
        assert "rest_delete" not in code
        # Every other operation still renders.
        for name in ("show", "create", "show-widgets", "update", "create-refresh"):
            assert f'@app.command("{name}"' in code

    def test_blocked_stub_exits_2_without_http(self, tmp_path, monkeypatch):
        from typer.testing import CliRunner
        msg = "a verified silent no-op; use: wxcli cc-flow update P F"
        code = self._generate(tmp_path, monkeypatch, {"mergeWidget": {"blocked": msg}})
        app, calls = self._load_app(code, monkeypatch)
        # Whatever the caller types — the right arguments, extra flags, or
        # nothing — the answer is the message and exit 2, never a request.
        for argv in (["update", "P", "W1"],
                     ["update", "P", "W1", "--json-body", '{"name": "x"}'],
                     ["update"]):
            r = CliRunner().invoke(app, argv)
            assert r.exit_code == 2, (argv, r.output)
            assert msg in r.output
        assert calls == []
        r = CliRunner().invoke(app, ["update", "--help"], env={"COLUMNS": "200", "TERM": "dumb"})
        assert r.exit_code == 0 and msg in r.output
        assert '@app.command("update"' in code   # visible, not hidden

    def test_warn_banner_precedes_call(self, tmp_path, monkeypatch):
        from typer.testing import CliRunner
        msg = "lists only the latest version of each flow"
        code = self._generate(tmp_path, monkeypatch, {"getWidget": {"warn": msg}})
        app, calls = self._load_app(code, monkeypatch)
        r = CliRunner().invoke(app, ["show-widgets", "P", "W1"])
        assert r.exit_code == 0, r.output
        assert f"Warning: {msg}" in r.output
        assert len(calls) == 1 and calls[0][0] == "rest_get"
        # The banner is emitted before the request line in the source.
        fn = code[code.index('@app.command("show-widgets"'):].split("\n@app.command")[0]
        assert fn.index(f"Warning: {msg}") < fn.index("rest_get(")
        # And only on the warned operation.
        assert code.count("Warning: ") == 1

    def test_flow_store_base_url_and_uuid_org(self, tmp_path, monkeypatch):
        from typer.testing import CliRunner
        code = self._generate(tmp_path, monkeypatch, {})
        assert "get_flow_store_base_url()" in code
        assert "get_cc_org_id(" in code
        # No call sends the base64 org id (the import line matches CC modules).
        assert "resolve_org_id(" not in code and "get_cc_base_url" not in code
        assert "https://webexapis.com" not in code
        app, calls = self._load_app(code, monkeypatch)
        r = CliRunner().invoke(app, ["show-widgets", "P", "W1"])
        assert r.exit_code == 0, r.output
        assert calls[0][1] == "https://fs.test/flow-store/org-uuid/project/P/widgets/W1"

    def test_flow_store_query_org_id_is_uuid(self):
        """The CC orgId branch of _render_auto_inject_params applies on the
        Flow Store base too: a query-param orgId is the bare UUID."""
        from tools.command_renderer import BASE_URL_FS, render_command_file
        from tools.openapi_parser import parse_tag
        spec = {"openapi": "3.0.1", "paths": {"/things": {"get": {
            "tags": ["Things"], "operationId": "listThings", "summary": "List things",
            "parameters": [{"name": "orgId", "in": "query", "schema": {"type": "string"}}],
            "responses": {"200": {"description": "ok", "content": {"application/json": {
                "schema": {"type": "array", "items": {"type": "object"}}}}}}}}}}
        eps, _ = parse_tag("Things", spec, auto_inject_params={"orgId"})
        code = render_command_file("Things", eps, {}, base_url_override=BASE_URL_FS,
                                   spec_filename=self.SPEC_NAME)
        assert 'params["orgId"] = get_cc_org_id(api.session)' in code
        assert 'params["orgId"] = org_id' not in code
        assert "fs_base_url = get_flow_store_base_url()" in code

    def test_ambiguous_opid_raises(self):
        from tools.generate_commands import OperationOverrideError, resolve_operation_overrides
        spec = self._fs_spec()
        # The CC spec reuses opIds across paths (tools/CLAUDE.md known issue 16).
        spec["paths"]["/{orgId}/project/{projectId}/widgets:refresh"]["post"]["operationId"] = "getWidget"
        with pytest.raises(OperationOverrideError) as exc:
            resolve_operation_overrides(
                {self.SPEC_NAME: {"getWidget": {"warn": "x"}}}, spec, self.SPEC_NAME)
        text = str(exc.value)
        assert self.SPEC_NAME in text and "getWidget" in text and "ambiguous" in text
        # It names both operations so the reader can pick a METHOD /path key.
        assert "GET /{orgId}/project/{projectId}/widgets/{widgetId}" in text
        assert "POST /{orgId}/project/{projectId}/widgets:refresh" in text

    def test_unknown_operation_raises(self):
        from tools.generate_commands import OperationOverrideError, resolve_operation_overrides
        for key in ("noSuchOperation", "GET /no/such/path",
                    "PUT /{orgId}/project/{projectId}/widgets"):
            with pytest.raises(OperationOverrideError) as exc:
                resolve_operation_overrides(
                    {self.SPEC_NAME: {key: {"skip": "x"}}}, self._fs_spec(), self.SPEC_NAME)
            assert self.SPEC_NAME in str(exc.value) and key in str(exc.value)

    def test_unknown_inner_key_raises(self):
        from tools.generate_commands import OperationOverrideError, resolve_operation_overrides
        for block in ({"getWidget": {"skipp": "x"}}, {"_all": {"warn": "x"}}):
            with pytest.raises(OperationOverrideError) as exc:
                resolve_operation_overrides({self.SPEC_NAME: block}, self._fs_spec(), self.SPEC_NAME)
            text = str(exc.value)
            assert self.SPEC_NAME in text and ("skipp" in text or "warn" in text)
        # Task 10's keys are accepted (validated here, rendered there).
        resolved = resolve_operation_overrides({self.SPEC_NAME: {
            "_all": {"param_help": {"flowType": "FLOW or SUBFLOW"}},
            "importWidget": {"multipart": True, "param_help": {"overwrite": "true or false"}},
            "createWidget": {"body_transform": "json-string"},
            "refreshWidgets": {"exit_code_from": {"json_key": "isUnique", "invert": True}},
        }}, self._fs_spec(), self.SPEC_NAME)
        assert resolved[("POST", "/{orgId}/project/{projectId}/widgets:import")]["multipart"] is True

    def test_method_path_key_matches(self, tmp_path, monkeypatch):
        from tools.generate_commands import resolve_operation_overrides
        resolved = resolve_operation_overrides(
            {self.SPEC_NAME: {self.PATCH_KEY: {"blocked": "use cc-flow update"}}},
            self._fs_spec(), self.SPEC_NAME)
        assert resolved == {("PATCH", "/{orgId}/project/{projectId}/widgets/{widgetId}"):
                            {"blocked": "use cc-flow update"}}
        # Another spec's block is not applied to this one.
        assert resolve_operation_overrides(
            {"webex-contact-center.json": {"x": {"skip": "y"}}}, self._fs_spec(),
            self.SPEC_NAME) == {}
        code = self._generate(tmp_path, monkeypatch,
                              {self.PATCH_KEY: {"blocked": "use cc-flow update"}})
        fn = code[code.index('@app.command("update"'):].split("\n@app.command")[0]
        assert "use cc-flow update" in fn and "raise typer.Exit(2)" in fn
        assert "rest_patch" not in fn


class TestOperationOverridesRender:
    """Plan 2 Task 10: rendering the `operation_overrides` keys Task 8 only
    validated — `multipart`, `param_help` (per operation and `_all`),
    `body_transform: json-string`, `exit_code_from` — plus the check that a
    DELETE whose request body is an array takes `--json-body '[...]'`.

    Same harness as TestOperationOverrides: the rendered module is exec'd with
    stubbed `wxcli` imports, so no command can reach the network.
    """

    FS_FIXTURE = TestOperationOverrides.FS_FIXTURE
    SPEC_NAME = TestOperationOverrides.SPEC_NAME
    IMPORT_PATH = "/{orgId}/project/{projectId}/widgets:import"
    TAGS_PATH = "/{orgId}/project/{projectId}/widgets/{widgetId}/tags"
    _fs_spec = TestOperationOverrides._fs_spec
    _generate = TestOperationOverrides._generate
    _load_app = staticmethod(TestOperationOverrides._load_app)

    @staticmethod
    def _fn(code: str, name: str) -> str:
        return code[code.index(f'@app.command("{name}"'):].split("\n@app.command")[0]

    @staticmethod
    def _invoke(app, argv):
        from typer.testing import CliRunner
        return CliRunner().invoke(app, argv)

    def test_multipart_renders_file_option_and_call(self, tmp_path, monkeypatch):
        code = self._generate(tmp_path, monkeypatch, {"importWidget": {"multipart": True}})
        fn = self._fn(code, "create-import")
        assert 'typer.Option(..., "--file"' in fn
        # The spec's {file} body describes the part, not a JSON body.
        assert "--json-body" not in fn and "--generate-json-body" not in fn
        assert "_BODY_SKELETON_CREATE_IMPORT" not in code
        assert ('api.session.rest_post_multipart(url, files={"file": (Path(file).name, '
                'Path(file).read_bytes(), "application/json")}, params=params)') in fn
        assert "--file FILE" in fn          # the runnable example names the required option
        upload = tmp_path / "flow.json"
        upload.write_bytes(b'{"name": "f"}')
        app, calls = self._load_app(code, monkeypatch)
        r = self._invoke(app, ["create-import", "P", "--file", str(upload), "--flow-type", "FLOW"])
        assert r.exit_code == 0, r.output
        assert len(calls) == 1
        name, url, kw = calls[0]
        assert name == "rest_post_multipart"
        assert url == "https://fs.test/flow-store/org-uuid/project/P/widgets:import"
        assert kw["files"] == {"file": ("flow.json", b'{"name": "f"}', "application/json")}
        # The spec's spaced query param "Flow Type" is the flag --flow-type and
        # goes out under its wire name.
        assert kw["params"] == {"Flow Type": "FLOW"}
        # --file is required, and a missing file fails before any request.
        assert self._invoke(app, ["create-import", "P"]).exit_code == 2
        assert self._invoke(app, ["create-import", "P", "--file", str(tmp_path / "no.json")]).exit_code == 2
        assert len(calls) == 1

    def test_multipart_form_data_upload_and_part_name(self, tmp_path, monkeypatch):
        spec = self._fs_spec()
        spec["paths"][self.IMPORT_PATH]["post"]["requestBody"] = {"content": {"multipart/form-data": {
            "schema": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}}}}
        # Without `multipart`, a form-data upload is still skipped by the parser.
        code = self._generate(tmp_path, monkeypatch, {}, spec=spec)
        assert '@app.command("create-import"' not in code
        code = self._generate(tmp_path, monkeypatch,
                              {"importWidget": {"multipart": {"field": "upload"}}}, spec=spec)
        assert 'rest_post_multipart(url, files={"upload": (Path(file).name, ' in self._fn(code, "create-import")

    def test_multipart_misuse_raises(self, tmp_path, monkeypatch):
        from tools.command_renderer import OperationOverrideRenderError
        for block in ({"deleteWidget": {"multipart": True}},                       # not a POST
                      {"importWidget": {"multipart": True, "body_transform": "json-string"}}):
            with pytest.raises(OperationOverrideRenderError) as exc:
                self._generate(tmp_path, monkeypatch, block)
            assert "multipart" in str(exc.value)

    def test_param_help_wins_over_spec(self, tmp_path, monkeypatch):
        code = self._generate(tmp_path, monkeypatch, {
            "mergeWidget": {"param_help": {"expectedVersion": "The version from show-widgets"}},
            "findWidgets": {"param_help": {"kind": "A for active, B for archived"}},
            "createWidget": {"param_help": {"name": "Unique within the project"}}})
        fn = self._fn(code, "update")
        assert '"--expected-version", help="The version from show-widgets"' in fn
        assert "Optimistic-lock version" not in fn
        # It wins over enum choices too, and covers list query params and body flags.
        assert '"--kind", help="A for active, B for archived"' in code
        assert "Choices: A, B" not in code
        assert '"--name", help="(required) Unique within the project"' in self._fn(code, "create")

    def test_param_help_naming_no_flag_raises(self, tmp_path, monkeypatch):
        from tools.command_renderer import OperationOverrideRenderError
        # An unknown name, an auto-injected param (no flag) and a path param
        # (a positional argument, not a flag) would all be inert.
        for wire in ("noSuchParam", "orgId", "widgetId"):
            with pytest.raises(OperationOverrideRenderError) as exc:
                self._generate(tmp_path, monkeypatch, {"getWidget": {"param_help": {wire: "x"}}})
            assert wire in str(exc.value) and "param_help" in str(exc.value)

    def test_global_param_help_fills_only_empty(self, tmp_path, monkeypatch):
        code = self._generate(tmp_path, monkeypatch, {
            "_all": {"param_help": {"flowType": "FLOW or SUBFLOW (server default: FLOW)",
                                    "expectedVersion": "MUST NOT REPLACE SPEC TEXT",
                                    "kind": "MUST NOT REPLACE ENUM CHOICES",
                                    "overwrite": "from _all"}},
            "importWidget": {"param_help": {"overwrite": "per-op wins"}}})
        fn = self._fn(code, "update")
        assert '"--flow-type", help="FLOW or SUBFLOW (server default: FLOW)"' in fn
        assert '"--expected-version", help="Optimistic-lock version"' in fn
        assert "MUST NOT REPLACE" not in code
        assert "Choices: A, B" in code
        assert '"--overwrite", help="per-op wins"' in self._fn(code, "create-import")
        assert "from _all" not in code

    def test_json_string_body(self, tmp_path, monkeypatch):
        code = self._generate(tmp_path, monkeypatch, {"createWidget": {"body_transform": "json-string"}})
        app, calls = self._load_app(code, monkeypatch)
        r = self._invoke(app, ["create", "P", "--json-body", '{"name": "w", "spec": {"a": [1]}}'])
        assert r.exit_code == 0, r.output
        sent = calls[0][2]["json"]
        assert isinstance(sent, str) and json.loads(sent) == {"name": "w", "spec": {"a": [1]}}
        # A body built from flags is sent the same way.
        r = self._invoke(app, ["create", "P", "--name", "w", "--count", "3"])
        assert r.exit_code == 0, r.output
        sent = calls[1][2]["json"]
        assert isinstance(sent, str) and json.loads(sent) == {"name": "w", "count": "3"}
        # Only the transformed operation changes.
        assert code.count("json.dumps(body)") == 1

    def test_exit_code_from_inverts(self, tmp_path, monkeypatch):
        code = self._generate(tmp_path, monkeypatch, {
            "refreshWidgets": {"exit_code_from": {"json_key": "isUnique", "invert": True}}})
        for response, want in (({"isUnique": True}, 0), ({"isUnique": False}, 1), ({}, 1)):
            app, _ = self._load_app(code, monkeypatch, response=response)
            r = self._invoke(app, ["create-refresh", "P"])
            assert r.exit_code == want, (response, r.output)
            if response:
                assert "isUnique" in r.output       # printed before the exit
        # Without invert, a true value exits 1.
        code = self._generate(tmp_path, monkeypatch, {
            "refreshWidgets": {"exit_code_from": {"json_key": "hasErrors"}}})
        for response, want in (({"hasErrors": True}, 1), ({"hasErrors": False}, 0)):
            app, _ = self._load_app(code, monkeypatch, response=response)
            assert self._invoke(app, ["create-refresh", "P"]).exit_code == want, response
        # Only the operation that asks for it reads the response for its exit code.
        assert code.count("bool(result.get(") == 1
        assert "bool(result.get('hasErrors')) != False" in self._fn(code, "create-refresh")

    def test_delete_array_body_via_json_body(self, tmp_path, monkeypatch):
        # The fixture declares the body as a JSON array of strings; the real
        # Flow Store spec declares its preferences DELETE body as SeqString
        # (an object of two booleans). Both must send the list as given.
        seq_string = self._fs_spec()
        seq_string["paths"][self.TAGS_PATH]["delete"]["requestBody"]["content"]["application/json"]["schema"] = {
            "type": "object", "properties": {"empty": {"type": "boolean"},
                                             "traversableAgain": {"type": "boolean"}}}
        for spec in (None, seq_string):
            code = self._generate(tmp_path, monkeypatch, {}, tag="WidgetTags", spec=spec)
            assert '"--json-body"' in self._fn(code, "delete")
            # The group has one command, and Typer runs a one-command app as
            # that command, so argv starts at its arguments.
            app, calls = self._load_app(code, monkeypatch)
            r = self._invoke(app, ["P", "W1", "--json-body", '["a", "b"]', "--force"])
            assert r.exit_code == 0, r.output
            assert calls[0][0] == "rest_delete" and calls[0][2]["json"] == ["a", "b"]
            # No --json-body, no body on the wire.
            r = self._invoke(app, ["P", "W1", "--force"])
            assert r.exit_code == 0, r.output
            assert calls[1][2].get("json") is None

# =============================================================================
# Plan 2 Task 14 generator settings
# =============================================================================
# Plan 2 Task 14 (2026-10-19, Adam's decisions 1, 3 and 4): three generator
# settings the Flow Store groups needed.
#
# 1. `producer: {<command>: false}` keeps a list command out of the argument-help
#    producer index. `cc-flow-projects list` (GET /{orgId}/project) does not list
#    the system project every `PROJECT_ID` argument takes (host map row
#    `findProject`, 404 "Project with id 5e5c9ad6… not found"), so pointing 47
#    arguments at it would be a wrong hint.
# 2. A rename keeps its old name as a hidden alias only when that name SHIPPED:
#    visible in tools/command_name_lock.json, or already a hidden alias in the
#    shipped module. A brand-new group (not in the lock) gets none — a hidden
#    `cc-flow-store list` that runs /health was never a name anyone scripted.
# 3. `paging: {<command>: {page: page, size: <name>}}` puts a list whose render
#    spec declares no paging onto the page-number walker (ADR-12), for an
#    endpoint measured to honour it (`cc-flow-templates list`, GET /templates).
from tools import generate_commands as gc  # noqa: E402


# ── 1. producer: false ───────────────────────────────────────────────────────


class TestProducerOptOut:
    @staticmethod
    def _spec():
        def get(op, path, params=()):
            return {"get": {
                "tags": ["Zz Parents"], "operationId": op, "summary": op,
                "parameters": [{"name": p, "in": "path", "required": True,
                                "schema": {"type": "string"}} for p in params],
                "responses": {"200": {"description": "ok", "content": {
                    "application/json": {"schema": {
                        "type": "array", "items": {"type": "object",
                        "properties": {"id": {"type": "string"}}}}}}}}}}
        return {"openapi": "3.0.0", "info": {"title": "p", "version": "1"},
                "paths": {"/zzparents": get("listParents", "/zzparents"),
                          "/zzparents/{parentId}/kids": get(
                              "listKids", "/zzparents/{parentId}/kids", ["parentId"])}}

    def _index(self, tmp_path, monkeypatch, tag_block):
        from tools import command_renderer as cr
        from tools import postman_parser, spec_overlay
        monkeypatch.setattr(postman_parser, "load_overrides", lambda path: {
            "tag_overrides": {"webex-messaging.json": {"Zz Parents": tag_block}}})
        monkeypatch.setattr(spec_overlay, "OVERLAY_DIR", tmp_path / "no-overlays")
        (tmp_path / "webex-messaging.json").write_text(json.dumps(self._spec()))
        return cr.build_producer_index(specs_dir=tmp_path)["by_path"]

    def test_control_list_is_a_producer(self, tmp_path, monkeypatch):
        assert self._index(tmp_path, monkeypatch, {}).get("zzparents") == "zz-parents list"

    def test_producer_false_keeps_it_out(self, tmp_path, monkeypatch):
        by_path = self._index(tmp_path, monkeypatch, {"producer": {"list": False}})
        assert "zzparents" not in by_path
        # Only the named command leaves the index.
        assert by_path.get("zzparents/{parentId}/kids") == "zz-parents list-kids"

    def test_keyed_on_the_renamed_name(self, tmp_path, monkeypatch):
        by_path = self._index(tmp_path, monkeypatch, {
            "command_name_overrides": {"list": "list-parents"},
            "producer": {"list-parents": False}})
        assert "zzparents" not in by_path

    def test_stale_key_refused(self, spec, tmp_path):
        ov = {"_tag_ovr:Things": {"producer": {"no-such-command": False}}}
        with pytest.raises(SystemExit):
            generate_tag("Things", spec, ov, tmp_path, True, set())

    def test_value_other_than_false_refused(self, spec, tmp_path, capsys):
        ov = {"_tag_ovr:Things": {"producer": {"list": True}}}
        with pytest.raises(SystemExit):
            generate_tag("Things", spec, ov, tmp_path, True, set())
        assert "producer" in capsys.readouterr().err

    def test_shipped_cc_flow_project_args_name_no_projects_list(self):
        src = (Path(__file__).parent.parent / "src" / "wxcli" / "commands"
               / "cc_flow.py").read_text()
        assert "cc-flow-projects list" not in src


# ── 2. hidden aliases only for names that shipped ────────────────────────────


class TestHiddenAliasOnlyForShippedNames:
    RENAME = {"command_name_overrides": {"create": "make"}}

    def _render(self, spec, tmp_path, monkeypatch, lock_modules, shipped_src=None):
        lock = tmp_path / "lock.json"
        lock.write_text(json.dumps({"modules": lock_modules}))
        cmds = tmp_path / "shipped"
        cmds.mkdir()
        if shipped_src is not None:
            (cmds / "things.py").write_text(shipped_src)
        monkeypatch.setattr(gc, "NAME_LOCK_PATH", lock)
        monkeypatch.setattr(gc, "SHIPPED_COMMANDS_DIR", cmds)
        out = tmp_path / "out"
        out.mkdir()
        generate_tag("Things", spec, {"_tag_ovr:Things": dict(self.RENAME)},
                     out, False, set())
        return (out / "things.py").read_text()

    def test_new_group_gets_no_alias(self, spec, tmp_path, monkeypatch):
        code = self._render(spec, tmp_path, monkeypatch, {"other": {"x": []}})
        assert '@app.command("make"' in code
        assert '@app.command("create", hidden=True)' not in code

    def test_old_name_locked_visible_gets_alias(self, spec, tmp_path, monkeypatch):
        code = self._render(spec, tmp_path, monkeypatch,
                            {"things": {"create": ["POST /things"]}})
        assert '@app.command("create", hidden=True)' in code

    def test_existing_hidden_alias_is_kept(self, spec, tmp_path, monkeypatch):
        shipped = ('@app.command("create", hidden=True)\n'
                   '@app.command("make", short_help="x")\n')
        code = self._render(spec, tmp_path, monkeypatch,
                            {"things": {"make": ["POST /things"]}}, shipped)
        assert '@app.command("create", hidden=True)' in code

    def test_never_shipped_name_in_shipped_group_gets_none(self, spec, tmp_path, monkeypatch):
        code = self._render(spec, tmp_path, monkeypatch,
                            {"things": {"list": ["GET /things"]}}, "")
        assert '@app.command("create", hidden=True)' not in code

    def test_rename_still_counts_as_applied(self, spec, tmp_path, monkeypatch):
        # Dropping the alias must not make the stale-override guard think
        # the command_name_overrides key matched nothing.
        code = self._render(spec, tmp_path, monkeypatch, {})
        assert '@app.command("make"' in code

    def test_no_lock_file_keeps_every_alias(self, spec, tmp_path, monkeypatch):
        monkeypatch.setattr(gc, "NAME_LOCK_PATH", tmp_path / "absent.json")
        monkeypatch.setattr(gc, "SHIPPED_COMMANDS_DIR", tmp_path)
        generate_tag("Things", spec, {"_tag_ovr:Things": dict(self.RENAME)},
                     tmp_path, False, set())
        assert '@app.command("create", hidden=True)' in (tmp_path / "things.py").read_text()

    def test_shipped_new_groups_carry_no_hidden_alias(self):
        cmd_dir = Path(__file__).parent.parent / "src" / "wxcli" / "commands"
        stems = ("cc_flow_store", "cc_flow_versions", "cc_flow_tracing",
                 "cc_flow_prefs", "cc_flow_projects", "cc_flow_connectors",
                 "cc_flow_templates")
        hits = [s for s in stems if "hidden=True)" in
                "".join(l for l in (cmd_dir / f"{s}.py").read_text().splitlines(True)
                        if l.startswith("@app.command("))]
        assert not hits, hits


# ── 3. paging: put an undeclared-paging list on the page walker ──────────────


class TestPagingOverride:
    def _ep(self, **kw):
        from tools.postman_parser import Endpoint
        base = dict(name="List", method="GET", url_path="templates", path_vars=[],
                    query_params=[], body_fields=[], command_type="list",
                    command_name="list", raw_path=["templates"],
                    response_list_key="items", response_id_key=None,
                    deprecated=False, json_body_example=None)
        base.update(kw)
        return Endpoint(**base)

    def test_sets_page_style_and_size_name(self):
        from tools.postman_parser import apply_endpoint_overrides
        ep = self._ep()
        apply_endpoint_overrides(ep, {"paging": {"list": {"page": "page", "size": "size"}}})
        assert (ep.pagination_style, ep.page_size_param) == ("page", "size")

    def test_renders_the_page_walker(self):
        from tools.postman_parser import apply_endpoint_overrides
        from tools.command_renderer import _render_list_command
        ep = self._ep()
        apply_endpoint_overrides(ep, {"paging": {"list": {"page": "page", "size": "size"}}})
        code = _render_list_command(ep, {})
        assert 'follow_page_param(url=url, params=params, item_key="items", size_param="size")' in code
        assert '"--all", help="Fetch every page' in code
        assert 'params["max"]' not in code and 'params["start"]' not in code

    @pytest.mark.parametrize("cfg", [{"page": "currentPage", "size": "size"},
                                     {"page": "page", "size": "count"},
                                     {"page": "page"}])
    def test_unsupported_shape_raises(self, cfg):
        from tools.postman_parser import apply_endpoint_overrides
        with pytest.raises(ValueError, match="paging"):
            apply_endpoint_overrides(self._ep(), {"paging": {"list": cfg}})

    def test_refused_on_a_command_that_renders_no_list(self, spec, tmp_path):
        ov = {"_tag_ovr:Things": {"paging": {"show": {"page": "page", "size": "size"}}}}
        with pytest.raises(SystemExit):
            generate_tag("Things", spec, ov, tmp_path, True, set())


# ── Task 14 fix pass: single reads, and the Scala-Seq request body ───────────


class TestFlowStoreSingleReads:
    """Four Flow Store GETs answer one object or a text body, while their
    specs declare `{}`, `string` or no schema, so the parser rendered them as
    lists and the extractor printed `[]` (review B1). `command_type_overrides:
    show` pins them; these drive the SHIPPED modules through the stubbed-exec
    harness (TestOperationOverrides._load_app), so no call can leave."""

    COMMANDS = Path(__file__).parent.parent / "src" / "wxcli" / "commands"
    SINGLE_READS = (("cc_flow_projects.py", "show-user-preferences"),
                    ("cc_flow_store.py", "show-build-info"),
                    ("cc_flow_store.py", "show-health"),
                    ("cc_flow_tracing.py", "show-analytics"))

    @staticmethod
    def _fn(code: str, name: str) -> str:
        return code[code.index(f'@app.command("{name}"'):].split("\n@app.command")[0]

    def test_user_preferences_reaches_emit_whole(self, monkeypatch):
        from typer.testing import CliRunner
        code = (self.COMMANDS / "cc_flow_projects.py").read_text()
        prefs = {"orgId": "o", "projectId": "5e5c9ad6d61f870d6d778c1b",
                 "id": "u1", "username": "a@b.c"}
        app, calls = TestOperationOverrides._load_app(code, monkeypatch, response=prefs)
        r = CliRunner().invoke(app, ["show-user-preferences", "-o", "json"])
        assert r.exit_code == 0, r.output
        assert calls[0][0] == "rest_get"
        assert "5e5c9ad6d61f870d6d778c1b" in r.output, r.output

    @pytest.mark.parametrize("module,name", SINGLE_READS)
    def test_rendered_as_single_reads(self, module, name):
        fn = self._fn((self.COMMANDS / module).read_text(), name)
        assert "emit(result," in fn
        for flag in ('"--all"', '"--limit"', '"--offset"'):
            assert flag not in fn, (name, flag)


class TestScalaSeqRequestBody:
    """springfox renders a Scala `Seq` request body as an object of two
    booleans, `{empty, traversableAgain}`. The wire is a JSON array, so the
    two "fields" are not options and not the example (review B2)."""

    @staticmethod
    def _spec(body_ref: str, schemas: dict) -> dict:
        return {"openapi": "3.0.0", "info": {"title": "t", "version": "1"},
                "components": {"schemas": schemas},
                "paths": {"/things/{id}/prefs": {"post": {
                    "tags": ["Things"], "operationId": "createPrefs",
                    "summary": "createPrefs",
                    "parameters": [{"name": "id", "in": "path", "required": True,
                                    "schema": {"type": "string"}}],
                    "requestBody": {"content": {"application/json": {
                        "schema": {"$ref": f"#/components/schemas/{body_ref}"}}}},
                    "responses": {"200": {"description": "ok"}}}}}}

    SEQ = {"type": "object", "properties": {"empty": {"type": "boolean"},
                                            "traversableAgain": {"type": "boolean"}}}

    def _ep(self, body_ref, schemas):
        from tools.openapi_parser import parse_operation
        spec = self._spec(body_ref, schemas)
        path = "/things/{id}/prefs"
        return parse_operation("post", path, spec["paths"][path]["post"], spec)

    def test_seq_of_strings_is_an_array_of_strings(self):
        ep = self._ep("SeqString", {"SeqString": self.SEQ})
        assert ep.body_fields == []
        assert ep.declares_json_body
        assert json.loads(ep.json_body_example) == ["..."]

    def test_seq_of_records_is_an_array(self):
        ep = self._ep("SeqFlowPreference", {"SeqFlowPreference": self.SEQ})
        assert ep.body_fields == []
        assert json.loads(ep.json_body_example) == [{}]

    def test_a_third_property_keeps_the_fields(self):
        three = {"type": "object", "properties": {
            **self.SEQ["properties"], "name": {"type": "string"}}}
        ep = self._ep("SeqThing", {"SeqThing": three})
        assert {f.name for f in ep.body_fields} == {"empty", "traversableAgain", "name"}
        assert json.loads(ep.json_body_example) == {
            "empty": True, "traversableAgain": True, "name": "..."}

    def test_shipped_prefs_writes_take_an_array(self):
        src = (TestFlowStoreSingleReads.COMMANDS / "cc_flow_prefs.py").read_text()
        assert "--empty" not in src and "--traversable-again" not in src
        assert "traversableAgain" not in src
        for name in ("create", "update", "delete"):
            fn = TestFlowStoreSingleReads._fn(src, name)
            assert '"--json-body"' in fn and '"--generate-json-body"' in fn
            assert "JSON array" in fn, name
