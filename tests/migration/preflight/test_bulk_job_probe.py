"""The bulk-device-job probe must be able to run, and its failure must stop the gate.

Phase 6 §5 / Phase 5. Check 10 of 10 — the one that verifies the org supports
the jobs that touch *every device in the org* — had never returned PASS or FAIL
in its life. Three defects in a chain:

1. `_build_bulk_job_probe` called `api.session.ep(...)` and `api.session.get(...)`,
   methods of `wxc_sdk`'s `WebexSimpleApi`. `wxc_sdk` was dropped as a dependency
   in `e4dfb22` (2026-04-17); `WebexSession` defines neither (`auth.py:215-367`).
   Every invocation raised `AttributeError`.
2. `checks.py`'s `except Exception` downgraded that to `WARN`.
3. `WARN` is below the gate threshold, so the check passed — and
   `commands/cucm.py`'s exit branch fired only on `FAIL`, so even `INCOMPLETE`
   would have exited 0.

**Why the defect survived: the seam that made the check testable made the
factory untestable.** All eight tests of `check_bulk_device_job_support` inject a
lambda for `probe_fn`; `_build_bulk_job_probe`, which builds the broken closure,
was referenced nowhere in `tests/`. Coverage confirmed the twelve lines had never
executed (`07-testability.md` §2.4). So the first test below is the one that
matters: it constructs the real factory.

Tracked deliberately — `tests/migration/**` is re-included at `.gitignore:56-57`.
A guard pinned by an untracked test is a guard pinned by nothing.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from wxcli.errors import WebexError
from wxcli.migration.preflight import CheckStatus
from wxcli.migration.preflight.runner import PreflightRunner

runner_cli = CliRunner()


class _FakeSession:
    """Records what the probe actually calls. Deliberately exposes ONLY the
    methods `WebexSession` really has — an `ep`/`get` regression fails here
    with AttributeError instead of being swallowed into a WARN."""

    def __init__(self, raise_exc: Exception | None = None):
        self.calls: list[tuple[str, dict | None]] = []
        self._raise = raise_exc

    def rest_get(self, url, params=None):
        self.calls.append((url, params))
        if self._raise is not None:
            raise self._raise
        return {"items": []}


class _FakeApi:
    def __init__(self, session):
        self.session = session


def _probe_with(session, config=None, org_id_from_config=None):
    """Build the real probe closure against a fake session."""
    runner = PreflightRunner(config=config or {})
    with patch("wxcli.auth.get_api", return_value=_FakeApi(session)), \
         patch("wxcli.config.get_org_id", return_value=org_id_from_config):
        probe = runner._build_bulk_job_probe()
        assert probe is not None, "probe factory returned None despite auth"
        return probe()


class TestTheProbeCanActuallyRun:
    def test_it_calls_rest_get_on_the_real_endpoint(self):
        session = _FakeSession()
        status, err = _probe_with(session)

        assert status == 200
        assert err == ""
        assert len(session.calls) == 1
        url, params = session.calls[0]
        assert url == (
            "https://webexapis.com/v1"
            "/telephony/config/jobs/devices/callDeviceSettings"
        )
        assert params["max"] == "1"

    def test_a_webex_error_surfaces_its_status(self):
        """The check branches on the HTTP status (403/404 → FAIL), so the
        status has to survive. `WebexError` carries it (`errors.py:17`)."""
        session = _FakeSession(
            raise_exc=WebexError("Forbidden", status_code=403, body={})
        )
        status, err = _probe_with(session)
        assert status == 403
        assert "Forbidden" in err

    def test_a_transport_failure_returns_the_zero_sentinel(self):
        session = _FakeSession(raise_exc=OSError("Connection refused"))
        status, err = _probe_with(session)
        assert status == 0
        assert "Connection refused" in err

    def test_project_config_org_id_wins(self):
        session = _FakeSession()
        _probe_with(session, config={"orgId": "org-from-project"},
                    org_id_from_config="org-from-wxcli")
        assert session.calls[0][1]["orgId"] == "org-from-project"

    def test_falls_back_to_the_cli_org_id(self):
        """Unscoped, the probe answers about whatever org the token defaults
        to — which on a partner token is not the migration target."""
        session = _FakeSession()
        _probe_with(session, config={}, org_id_from_config="org-from-wxcli")
        assert session.calls[0][1]["orgId"] == "org-from-wxcli"

    def test_no_org_id_anywhere_omits_the_param(self):
        session = _FakeSession()
        _probe_with(session, config={}, org_id_from_config=None)
        assert "orgId" not in session.calls[0][1]

    def test_no_auth_yields_no_probe(self):
        """`get_api` raises `typer.Exit` when no token is configured — the
        check then SKIPs rather than reporting a verdict."""
        import typer

        runner = PreflightRunner()
        with patch("wxcli.auth.get_api", side_effect=typer.Exit(1)):
            assert runner._build_bulk_job_probe() is None


@pytest.fixture()
def tmp_migrations_dir(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    monkeypatch.setattr("wxcli.commands.cucm.MIGRATIONS_DIR", migrations_dir)
    monkeypatch.setattr(
        "wxcli.commands.cucm.CURRENT_PROJECT_FILE", tmp_path / "current"
    )
    return migrations_dir


def _seed_up_to_plan(migrations_dir, name="p1") -> None:
    path = migrations_dir / name / "state.json"
    data = json.loads(path.read_text())
    data["completed_stages"] = [
        "init", "discover", "normalize", "map", "analyze", "plan",
    ]
    path.write_text(json.dumps(data))


class TestIncompleteStopsTheGate:
    """`gate_ok` already excluded INCOMPLETE; the exit code did not.

    Two consumers of one verdict disagreeing is worse than either being wrong:
    the stage was left unmarked *and* `$?` said success. The skill calls
    preflight MANDATORY, NOT SKIPPABLE.
    """

    def _run_preflight_with_overall(self, tmp_migrations_dir, overall):
        from wxcli.commands.cucm import app
        from wxcli.migration.preflight import CheckResult, PreflightResult

        runner_cli.invoke(app, ["init", "p1"])
        _seed_up_to_plan(tmp_migrations_dir)

        result = PreflightResult(
            overall=overall,
            checks=[
                CheckResult(name=n, status=overall, detail="x")
                for n in PreflightRunner.registered_check_names()
            ],
        )
        with patch(
            "wxcli.migration.preflight.runner.PreflightRunner.run",
            return_value=result,
        ):
            return runner_cli.invoke(app, ["preflight"])

    def test_incomplete_exits_non_zero(self, tmp_migrations_dir):
        res = self._run_preflight_with_overall(
            tmp_migrations_dir, CheckStatus.INCOMPLETE
        )
        assert res.exit_code == 1, res.output

    def test_incomplete_does_not_mark_the_stage(self, tmp_migrations_dir):
        self._run_preflight_with_overall(
            tmp_migrations_dir, CheckStatus.INCOMPLETE
        )
        state = json.loads(
            (tmp_migrations_dir / "p1" / "state.json").read_text()
        )
        assert "preflight" not in state.get("completed_stages", [])

    def test_fail_still_exits_non_zero(self, tmp_migrations_dir):
        res = self._run_preflight_with_overall(
            tmp_migrations_dir, CheckStatus.FAIL
        )
        assert res.exit_code == 1, res.output

    def test_pass_still_exits_zero_and_marks_the_stage(self, tmp_migrations_dir):
        res = self._run_preflight_with_overall(
            tmp_migrations_dir, CheckStatus.PASS
        )
        assert res.exit_code == 0, res.output
        state = json.loads(
            (tmp_migrations_dir / "p1" / "state.json").read_text()
        )
        assert "preflight" in state.get("completed_stages", [])
