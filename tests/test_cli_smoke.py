"""CLI smoke tests — verify command registration and --help without hitting live API."""

import pytest
from wxcli.main import app


# All command group names registered in main.py
COMMAND_GROUPS = [
    # Hand-coded
    "configure", "locations", "users", "numbers", "licenses",
    # Calling spec
    "call-controls", "cq-playlists", "call-routing", "caller-reputation",
    "calling-service", "client-settings", "conference", "converged-recordings",
    "dect-devices", "device-settings", "device-dynamic-settings", "devices",
    "emergency-services", "external-voicemail", "auto-attendant", "call-park",
    "call-pickup", "call-queue", "hunt-group", "paging-group",
    "announcement-playlists", "announcements", "call-recording",
    "cx-essentials", "hot-desking-portal", "operating-modes",
    "single-number-reach", "virtual-extensions", "hot-desk",
    "location-settings", "location-schedules", "location-voicemail",
    "location-call-handling", "mode-management",
    "pstn", "partner-reports", "people",
    "recording-report", "reports", "cdr", "user-settings",
    "virtual-line-settings", "workspace-settings", "workspaces",
    # Admin spec
    "domains", "audit-events", "archive-users", "authorizations",
    "scim-bulk", "classifications", "data-sources", "events", "groups",
    "guest-management", "analytics", "hybrid-clusters", "hybrid-connectors",
    "identity-org", "licenses-api", "live-monitoring", "meeting-qualities",
    "org-contacts", "organizations", "partner-admins", "partner-tags",
    "admin-recordings", "report-templates", "resource-group-memberships",
    "resource-groups", "roles", "scim-groups", "scim-schemas", "scim-users",
    "security-audit", "activation-email", "service-apps", "org-settings",
    "workspace-locations", "workspace-metrics",
    # Device spec
    "device-configurations", "workspace-personalization", "xapi",
    # Messaging spec
    "attachment-actions", "ecm", "hds", "memberships", "messages",
    "room-tabs", "rooms", "team-memberships", "teams", "webhooks",
]


class TestMainApp:
    """Test the top-level wxcli app."""

    def test_main_help(self, runner):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "wxcli" in result.output.lower()

    def test_version_flag(self, runner):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "wxcli" in result.output

    def test_no_args_shows_help(self, runner):
        result = runner.invoke(app, [])
        # no_args_is_help=True causes exit code 0 on some typer versions, 2 on others
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "wxcli" in result.output.lower()


class TestCommandGroupRegistration:
    """Verify every command group is registered and responds to --help."""

    @pytest.mark.parametrize("group", COMMAND_GROUPS)
    def test_group_help(self, runner, group):
        result = runner.invoke(app, [group, "--help"])
        assert result.exit_code == 0, (
            f"{group} --help failed (exit {result.exit_code}): {result.output}"
        )
        assert "Usage" in result.output or "Options" in result.output, (
            f"{group} --help produced unexpected output: {result.output[:200]}"
        )


class TestCommandGroupCount:
    """Verify the expected number of command groups are registered."""

    def test_expected_group_count(self):
        # main.py registers command groups via add_typer + the 'whoami' command
        # Count the registered typer sub-apps
        registered = [
            g.name for g in getattr(app, "registered_groups", [])
            if g.name
        ]
        # Should have ~100 groups; fail if we drop below 90 (regression guard)
        assert len(registered) >= 90, (
            f"Only {len(registered)} command groups registered, expected 90+. "
            f"Check main.py imports."
        )


import pytest
from typer.testing import CliRunner
from wxcli.main import app

BOX_CHARS = set("─━│┃┌┏┐┓└┗┘┛├┡┣┤┩┫┬┳┴┻┼╇╋╭╮╯╰╴╵╶╷")
runner = CliRunner()


def test_help_has_no_box_characters_when_captured():
    """CliRunner captures stdout, so this is exactly the agent's view."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    leaked = set(result.output) & BOX_CHARS
    assert not leaked, f"help still draws boxes: {sorted(leaked)}"


def test_help_still_lists_the_commands():
    """Plain formatting must not cost content."""
    result = runner.invoke(app, ["--help"])
    for expected in ("whoami", "locations", "call-queue"):
        assert expected in result.output


def test_group_help_has_no_box_characters():
    result = runner.invoke(app, ["call-queue", "--help"])
    assert not (set(result.output) & BOX_CHARS)


def test_command_help_still_shows_options():
    result = runner.invoke(app, ["call-queue", "list", "--help"])
    assert "--output" in result.output


# ---------------------------------------------------------------------------
# Task 6: hand-written commands get the same --output/--fields surface.
# ---------------------------------------------------------------------------

# Commands that gain BOTH flags — verified 2026-07-25 as having no --output today
GAP_COMMANDS = ["whoami", "switch-org", "clear-org"]

# Commands where --output already means a filesystem path. They gain --fields
# only; adding a format flag would make one name mean two things.
#
# Corrected from the original brief: `cucm assess` does not exist (exit 2).
# The report writer's CLI name is `report` — a bare @app.command() on
# `def report` in cucm.py. Verified via `wxcli cucm report --help` (exit 0)
# vs `wxcli cucm assess --help` (exit 2).
PATH_VALUED = [["org-health", "analyze"], ["cucm", "report"]]


@pytest.mark.parametrize("cmd", GAP_COMMANDS)
def test_gap_command_accepts_output(cmd):
    result = runner.invoke(app, [cmd, "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output, f"{cmd} still lacks --output"


@pytest.mark.parametrize("cmd", [[c] for c in GAP_COMMANDS] + PATH_VALUED)
def test_every_touched_command_accepts_fields(cmd):
    """--fields is the genuinely universal one — it is free tree-wide.

    Corrected from the original brief: this parametrized over the bare group
    names ("org-health", "cucm") and invoked `[group, "--help"]`, which lists
    a group's subcommands and never a subcommand's own flags — the assertion
    could never fail regardless of whether --fields was actually wired up.
    Fixed by invoking the full subcommand path (`cmd + ["--help"]`) for both
    the GAP commands (each wrapped in its own list) and the PATH_VALUED pairs.
    """
    result = runner.invoke(app, cmd + ["--help"])
    assert result.exit_code == 0, f"{cmd} --help failed: {result.output}"
    assert "--fields" in result.output, f"{cmd} still lacks --fields"


@pytest.mark.parametrize("cmd", PATH_VALUED)
def test_path_valued_output_keeps_its_meaning(cmd):
    """Regression guard: org-health/cucm --output is a path, not a format.

    If this ever starts saying 'Output format', someone has collided two
    meanings onto one flag — the exact bug --fields was chosen to avoid.
    """
    result = runner.invoke(app, cmd + ["--help"])
    assert result.exit_code == 0
    assert "Output format" not in result.output, f"{cmd} --output was repurposed"


def test_interactive_commands_are_exempt_on_purpose():
    """configure/init prompt; they are documented exemptions, not oversights."""
    for cmd in ("configure", "init"):
        assert runner.invoke(app, [cmd, "--help"]).exit_code == 0


def test_bucket_c_fields_takes_effect_on_table_output(monkeypatch, tmp_path):
    """Fix round 1, Finding 2: --fields must not be silently ignored when
    -o table (the default) is in effect on the bucket-C cucm commands.

    A --fields projection changes the data's shape, so the bespoke Rich
    table (decisions' "Migration Decisions:" summary line and "Filters:"
    hint) cannot render it — emit()'s projection-driven table is the correct
    renderer, and it must fire even though --output was never set to json.
    Companion assertion: with no --fields, table rendering is byte-for-byte
    the same bespoke output as before this fix.
    """
    import wxcli.commands.cucm as cucm_mod

    migrations_dir = tmp_path / "migrations"
    monkeypatch.setattr(cucm_mod, "MIGRATIONS_DIR", migrations_dir)

    init_result = runner.invoke(app, ["cucm", "init", "proj-fields-test"])
    assert init_result.exit_code == 0, init_result.output

    store = cucm_mod._open_store(migrations_dir / "proj-fields-test")
    store.save_decision({
        "decision_id": "D0001",
        "type": "MISSING_DATA",
        "severity": "HIGH",
        "summary": "Missing voicemail PIN",
        "context": {},
        "options": [],
        "chosen_option": None,
        "fingerprint": "fp1",
        "run_id": "run1",
    })
    store.close()

    # No --fields: bespoke rendering is unchanged (default -o, i.e. table).
    default_result = runner.invoke(app, ["cucm", "decisions", "-p", "proj-fields-test"])
    assert default_result.exit_code == 0
    assert "Migration Decisions:" in default_result.output
    assert "Filters:" in default_result.output

    # --fields supplied, -o never set to json: the projected field must
    # appear, and the bespoke decorations must not — --fields silently
    # doing nothing here is exactly the failure this fix prevents.
    fields_result = runner.invoke(
        app, ["cucm", "decisions", "-p", "proj-fields-test", "--fields", "[].{id:decision_id}"],
    )
    assert fields_result.exit_code == 0
    assert "D0001" in fields_result.output
    assert "Migration Decisions:" not in fields_result.output
    assert "Filters:" not in fields_result.output


def test_inventory_summary_fields_takes_effect_on_table_output(monkeypatch, tmp_path):
    """Hardening C: `cucm inventory`'s no---type summary-counts branch accepted
    --output/--fields but silently ignored both — an advertised flag that does
    nothing is worse than a flag that doesn't exist.

    A --fields projection changes the data's shape (object-type -> count), so
    the bespoke Rich table below can't render it — emit()'s projection-driven
    table (or JSON fallback for a scalar) is what --fields needs, even though
    --output was never set to json. Companion assertion: with no --fields,
    the summary-counts table rendering is byte-for-byte the same bespoke
    output as before this fix.
    """
    import wxcli.commands.cucm as cucm_mod
    from datetime import datetime, timezone
    from wxcli.migration.models import (
        CanonicalDevice, CanonicalLocation, MigrationStatus, Provenance,
    )

    migrations_dir = tmp_path / "migrations"
    monkeypatch.setattr(cucm_mod, "MIGRATIONS_DIR", migrations_dir)

    init_result = runner.invoke(app, ["cucm", "init", "proj-inventory-fields-test"])
    assert init_result.exit_code == 0, init_result.output

    store = cucm_mod._open_store(migrations_dir / "proj-inventory-fields-test")
    prov = Provenance(
        source_system="cucm", source_id="pk-test",
        source_name="test", extracted_at=datetime.now(timezone.utc),
    )
    store.upsert_object(CanonicalLocation(
        canonical_id="location:hq", provenance=prov,
        status=MigrationStatus.DISCOVERED, name="HQ",
    ))
    store.upsert_object(CanonicalLocation(
        canonical_id="location:branch", provenance=prov,
        status=MigrationStatus.DISCOVERED, name="Branch",
    ))
    store.upsert_object(CanonicalDevice(
        canonical_id="device:SEP001122AABBCC", provenance=prov,
        status=MigrationStatus.DISCOVERED, mac="001122AABBCC",
    ))
    store.close()

    # No --fields: bespoke rendering is unchanged (default -o, i.e. table).
    default_result = runner.invoke(
        app, ["cucm", "inventory", "-p", "proj-inventory-fields-test"],
    )
    assert default_result.exit_code == 0
    assert "Migration Inventory" in default_result.output
    assert "location" in default_result.output
    assert "TOTAL" in default_result.output

    # --fields supplied, -o never set to json: the projected count must
    # appear, and the bespoke table title must not — --fields silently
    # doing nothing here is exactly the failure this fix prevents.
    fields_result = runner.invoke(
        app,
        ["cucm", "inventory", "-p", "proj-inventory-fields-test", "--fields", "location"],
    )
    assert fields_result.exit_code == 0
    assert "2" in fields_result.output
    assert "Migration Inventory" not in fields_result.output


# ---------------------------------------------------------------------------
# Final code review Task 23, Defect A: `cleanup run` declared --fields but
# only routed through emit() when -o was explicitly "json" — the default
# table mode silently ignored it. Its --dry-run path also returned before
# reaching any emit() call, leaving stdout completely empty for
# `-o json`/--fields. Same class of bug as the bucket-C cucm fixes above.
# ---------------------------------------------------------------------------


def _make_cleanup_api_mock():
    from unittest.mock import MagicMock
    api = MagicMock()
    api.session.follow_pagination.return_value = iter([])
    return api


def _patch_cleanup_single_layer(monkeypatch, cleanup_mod, items):
    """Wire cleanup_run's dependencies so inventory is exactly ``items``
    under the 'dial_plans' key — a single, non-special-cased layer — and
    execute_layer reports every item deleted successfully."""
    monkeypatch.setattr(cleanup_mod, "get_api", lambda debug=False: _make_cleanup_api_mock())
    monkeypatch.setattr(cleanup_mod, "get_org_id", lambda: None)
    monkeypatch.setattr(
        cleanup_mod, "_resolve_location_ids",
        lambda api, scope, org_id, unresolved=None: None,
    )
    monkeypatch.setattr(
        cleanup_mod, "build_inventory",
        lambda *a, **kw: {"dial_plans": items},
    )
    monkeypatch.setattr(cleanup_mod, "build_number_inventory", lambda *a, **kw: {})
    monkeypatch.setattr(
        cleanup_mod, "execute_layer",
        lambda api, layer_keys, inventory, org_id, max_concurrent: (
            [
                cleanup_mod.DeleteResult(
                    "Dial Plans", it["id"], it["name"], success=True,
                )
                for it in items
            ]
            if "dial_plans" in layer_keys else []
        ),
    )


def test_cleanup_run_fields_takes_effect_on_default_table_output(monkeypatch):
    """Defect A (final review 23): `cleanup run` declared --fields but only
    routed through emit() when -o was explicitly "json" — in the default
    table mode the flag did nothing at all (Rich summary to stderr, nothing
    on stdout, exit 0). --fields must now project the result and reach
    stdout via emit() even though -o stays at its "table" default.
    Companion assertion: with no --fields, table-mode rendering is
    unchanged — still nothing on stdout, bespoke summary on stderr, exactly
    as the module's pre-existing Console(stderr=True) fix already made it.
    """
    import wxcli.commands.cleanup as cleanup_mod

    _patch_cleanup_single_layer(
        monkeypatch, cleanup_mod, [{"id": "dp-1", "name": "DP One"}],
    )

    # No --fields: unchanged — bespoke summary on stderr, nothing on stdout.
    plain_result = runner.invoke(app, ["cleanup", "run", "--all", "--force"])
    assert plain_result.exit_code == 0, plain_result.output
    assert plain_result.stdout == ""
    assert "=== Cleanup Results ===" in plain_result.stderr
    assert "Deleted:  1" in plain_result.stderr

    # --fields supplied, -o never set to json: the projected result must
    # reach stdout via emit() — silently doing nothing (today's bug) is
    # exactly the failure this fix prevents.
    fields_result = runner.invoke(
        app,
        [
            "cleanup", "run", "--all", "--force",
            "--fields", "{deleted: deleted, failed: failed}",
        ],
    )
    assert fields_result.exit_code == 0, fields_result.output
    assert fields_result.stdout.strip(), "cleanup run --fields produced nothing on stdout"
    assert "deleted" in fields_result.stdout.lower()
    assert "1" in fields_result.stdout
    # The bespoke prose summary must not have printed at all — --fields
    # skips the whole else-branch, on both streams.
    assert "=== Cleanup Results ===" not in fields_result.stdout
    assert "=== Cleanup Results ===" not in fields_result.stderr


def test_cleanup_run_dry_run_emits_machine_readable_result(monkeypatch):
    """Defect A part 2 (final review 23): `cleanup run --all --dry-run -o
    json` returned before reaching any emit() call — with progress on
    stderr, stdout was completely empty and `| jq` failed on empty input.
    Dry-run must now emit a machine-readable result on stdout when -o json
    (or --fields) is given. Companion assertion: with neither flag, the
    human dry-run message is unchanged (stderr, stdout stays empty).
    """
    import json
    import wxcli.commands.cleanup as cleanup_mod

    _patch_cleanup_single_layer(
        monkeypatch, cleanup_mod, [{"id": "dp-1", "name": "DP One"}],
    )

    # -o json: stdout must carry a parseable, non-empty JSON result.
    json_result = runner.invoke(app, ["cleanup", "run", "--all", "--dry-run", "-o", "json"])
    assert json_result.exit_code == 0, json_result.output
    assert json_result.stdout.strip(), "dry-run -o json produced nothing on stdout"
    parsed = json.loads(json_result.stdout)
    assert parsed["dryRun"] is True
    assert parsed["wouldDelete"] == 1
    assert parsed["resources"] == {"Dial Plans": 1}

    # Neither flag: human rendering is unchanged — stderr message, stdout
    # still empty (byte-identical to before this fix).
    plain_result = runner.invoke(app, ["cleanup", "run", "--all", "--dry-run"])
    assert plain_result.exit_code == 0, plain_result.output
    assert plain_result.stdout == ""
    assert "Dry run complete. No resources were deleted." in plain_result.stderr


# ---------------------------------------------------------------------------
# Final code review Task 23, Defect B: cucm's three report writers
# (report/user-diff/user-notice) interleaved Rich prose with their JSON on
# stdout, so `| jq` failed. Route taken: scope the stderr redirect to a
# dedicated report_console used only by those three commands' prose — NOT a
# blanket module-console redirect, because the seven bucket-C read-only
# commands (preflight/decisions/inventory/next-batch/execution-status/
# rollback-ops/dry-run) render their `-o table` result as
# console.print(<rich Table>) on that SAME module console; redirecting it
# wholesale would silently empty `wxcli cucm decisions -o table > file.txt`.
# ---------------------------------------------------------------------------


def _mark_analyze_complete(project_dir):
    """Flag 'analyze' complete in state.json directly, bypassing
    ProjectState transition validation — these tests only need the
    prerequisite-stage gate on report/user-diff/user-notice to pass."""
    import json as _json
    state_path = project_dir / "state.json"
    state = _json.loads(state_path.read_text())
    stages = state.setdefault("completed_stages", [])
    if "analyze" not in stages:
        stages.append("analyze")
    state_path.write_text(_json.dumps(state))


def test_cucm_report_writers_put_only_json_on_stdout(monkeypatch, tmp_path):
    """The three report writers must land ONLY parseable JSON on stdout —
    their "X generated:" prose (and PDF prose) must not appear there. Each
    still prints its prose somewhere (stderr), so a human watching the
    terminal loses nothing — only stdout gets cleaned for `| jq`.
    """
    import json
    import wxcli.commands.cucm as cucm_mod

    migrations_dir = tmp_path / "migrations"
    monkeypatch.setattr(cucm_mod, "MIGRATIONS_DIR", migrations_dir)

    init_result = runner.invoke(app, ["cucm", "init", "proj-report-test"])
    assert init_result.exit_code == 0, init_result.output
    project_dir = migrations_dir / "proj-report-test"
    _mark_analyze_complete(project_dir)

    # report: mock assemble_report so no real analyzed data is needed.
    monkeypatch.setattr(
        "wxcli.migration.report.assembler.assemble_report",
        lambda store, **kw: "<html>fake report</html>",
    )
    report_result = runner.invoke(
        app,
        ["cucm", "report", "-p", "proj-report-test", "--brand", "Acme", "--prepared-by", "Alice"],
    )
    assert report_result.exit_code == 0, report_result.output
    parsed = json.loads(report_result.stdout)
    assert parsed["brand"] == "Acme"
    assert "Report generated:" not in report_result.stdout
    assert "Report generated:" in report_result.stderr

    # user-diff: mock build_user_diffs/render_html so no real data needed.
    monkeypatch.setattr(
        "wxcli.migration.report.user_diff.build_user_diffs",
        lambda store, **kw: [],
    )
    monkeypatch.setattr(
        "wxcli.migration.report.user_diff.render_html",
        lambda records, **kw: "<html>fake diff</html>",
    )
    diff_result = runner.invoke(app, ["cucm", "user-diff", "-p", "proj-report-test"])
    assert diff_result.exit_code == 0, diff_result.output
    parsed = json.loads(diff_result.stdout)
    assert parsed["userCount"] == 0
    assert "User diff generated:" not in diff_result.stdout
    assert "User diff generated:" in diff_result.stderr

    # user-notice: mock generate_user_notice so no real data needed.
    monkeypatch.setattr(
        "wxcli.migration.report.user_notice.generate_user_notice",
        lambda store, **kw: "fake notice",
    )
    notice_result = runner.invoke(
        app,
        [
            "cucm", "user-notice", "-p", "proj-report-test",
            "--brand", "Acme", "--migration-date", "2026-08-01",
            "--helpdesk", "helpdesk@acme.com",
        ],
    )
    assert notice_result.exit_code == 0, notice_result.output
    parsed = json.loads(notice_result.stdout)
    assert parsed["brand"] == "Acme"
    assert "User notice generated:" not in notice_result.stdout
    assert "User notice generated:" in notice_result.stderr


def test_cucm_read_commands_still_print_tables_to_stdout(monkeypatch, tmp_path):
    """Regression guard for the route taken on Defect B: the bucket-C
    read commands' `-o table` (default) rendering must still land on
    stdout — proving the module `console` was NOT redirected wholesale
    when the three report writers' prose was moved to stderr.
    """
    import wxcli.commands.cucm as cucm_mod

    migrations_dir = tmp_path / "migrations"
    monkeypatch.setattr(cucm_mod, "MIGRATIONS_DIR", migrations_dir)

    init_result = runner.invoke(app, ["cucm", "init", "proj-table-stdout-test"])
    assert init_result.exit_code == 0, init_result.output

    store = cucm_mod._open_store(migrations_dir / "proj-table-stdout-test")
    store.save_decision({
        "decision_id": "D0002",
        "type": "MISSING_DATA",
        "severity": "HIGH",
        "summary": "Missing voicemail PIN",
        "context": {},
        "options": [],
        "chosen_option": None,
        "fingerprint": "fp2",
        "run_id": "run1",
    })
    store.close()

    result = runner.invoke(app, ["cucm", "decisions", "-p", "proj-table-stdout-test"])
    assert result.exit_code == 0, result.output
    # The bold summary line and the Rich table's row content (some columns
    # get truncated to "…" under CliRunner's narrow captured terminal, so
    # assert on content that survives — Type and Summary) must be on stdout.
    assert "Migration Decisions:" in result.stdout
    assert "MISSING_DATA" in result.stdout
    assert "Missing voicemail PIN" in result.stdout
    # And none of it leaked to stderr — this command's whole output is a
    # single stream, unlike the three report writers.
    assert "Migration Decisions:" not in result.stderr
