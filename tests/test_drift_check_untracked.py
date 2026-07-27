"""Drift gate: module inclusion is an ignore test, not an index-membership test.

Regression cover for the bug where a freshly generated command module, present
on disk but not yet `git add`ed, was treated as absent — freezing the published
command-set count and reporting its endpoints as phantom "spec->CLI missing".
"""

import sys

import pytest

from tools import drift_check


COMMANDS = drift_check.COMMANDS_DIR
PROBE_BODY = '''"""Test probe module."""
import typer

app = typer.Typer()


@app.command("list")
def list_things():
    """Probe."""
    url = f"https://webexapis.com/v1/telephony/config/zzTestProbe"
    result = api.session.rest_get(url)
    return result
'''


@pytest.fixture(autouse=True)
def _reset_caches():
    """drift_check memoizes both git lookups; clear them between cases."""
    drift_check._MODULE_STATE = None
    drift_check._IGNORE_CACHE.clear()
    yield
    drift_check._MODULE_STATE = None
    drift_check._IGNORE_CACHE.clear()


@pytest.fixture
def probes():
    """Two structurally identical untracked modules: one gitignored, one not."""
    ignored = COMMANDS / "fs_zz_test_probe.py"      # matches .gitignore fs_*.py
    plain = COMMANDS / "zz_test_probe.py"           # matches no ignore rule
    ignored.write_text(PROBE_BODY)
    plain.write_text(PROBE_BODY)
    try:
        yield ignored, plain
    finally:
        ignored.unlink(missing_ok=True)
        plain.unlink(missing_ok=True)


def test_ignored_files_reports_only_the_gitignored_probe(probes):
    ignored, plain = probes
    rel = [f"src/wxcli/commands/{p.name}" for p in (ignored, plain)]
    assert drift_check.ignored_files(rel) == {rel[0]}


def test_ignored_files_never_reports_a_tracked_path():
    """git check-ignore consults the index, so tracked files can't be dropped.

    tests/test_field_overrides.py is tracked but sits under an ignored dir —
    the exact shape that would break counts if the index were bypassed.
    """
    paths = ["tests/test_field_overrides.py", "tests/definitely_not_tracked.py"]
    assert drift_check.ignored_files(paths) == {"tests/definitely_not_tracked.py"}


def test_ignored_files_handles_no_match_exit_code():
    """git check-ignore exits 1 when nothing matches; that is not an error."""
    assert drift_check.ignored_files(["src/wxcli/main.py"]) == set()


def test_ignored_files_is_batched_and_cached(probes, monkeypatch):
    calls = []
    real_run = drift_check.subprocess.run

    def counting_run(cmd, **kw):
        calls.append(cmd)
        return real_run(cmd, **kw)

    monkeypatch.setattr(drift_check.subprocess, "run", counting_run)
    drift_check.module_state()
    drift_check.module_state()
    checks = [c for c in calls if c[:2] == ["git", "check-ignore"]]
    assert len(checks) == 1, "expected one batched check-ignore call, got %d" % len(checks)


def test_countable_excludes_ignored_but_includes_untracked(probes):
    state = drift_check.module_state()
    assert "fs_zz_test_probe" not in state["countable"], "gitignored dev-only must stay out"
    assert "zz_test_probe" in state["countable"], "present + not ignored must count"


def test_untracked_state_is_reported_separately(probes):
    state = drift_check.module_state()
    assert state["untracked"] == {"zz_test_probe"}
    modules = {u["module"] for u in drift_check.check_untracked_modules()}
    assert modules == {"zz_test_probe"}


def test_untracked_check_is_empty_on_a_clean_tree():
    """The not-firing half — a probe that cannot pass proves nothing."""
    assert drift_check.check_untracked_modules() == []
    assert drift_check.module_state()["untracked"] == set()


def test_tracked_modules_are_still_countable():
    assert "people" in drift_check.module_state()["countable"]
    assert "people" not in drift_check.module_state()["untracked"]


@pytest.mark.parametrize("untracked,expected_exit", [([], 0), ([{"module": "zz", "registered": True}], 1)])
def test_enforce_exit_code_follows_check_8(monkeypatch, capsys, untracked, expected_exit):
    """Isolate check 8: every other check reports clean, only check 8 varies."""
    monkeypatch.setattr(drift_check, "load_overrides",
                        lambda: {"skip_tags": {}, "skip_reasons": {}, "keep_endpoints": []})
    monkeypatch.setattr(drift_check, "load_spec_ops", lambda _skip: ({}, {}))
    monkeypatch.setattr(drift_check, "build_cli_surface", lambda: ({}, set()))
    monkeypatch.setattr(drift_check, "build_flag_surface", lambda: {})
    monkeypatch.setattr(drift_check, "distinct_command_sets", lambda: 0)
    monkeypatch.setattr(drift_check, "check_parity",
                        lambda *a: {"missing_from_cli": [], "cli_ahead_of_spec": []})
    monkeypatch.setattr(drift_check, "check_references", lambda *a: ([], {}))
    monkeypatch.setattr(drift_check, "check_counts", lambda *a: [])
    monkeypatch.setattr(drift_check, "check_unreferenced", lambda *a: [])
    monkeypatch.setattr(drift_check, "check_overlays", lambda: [])
    monkeypatch.setattr(drift_check, "check_flags", lambda *a: [])
    monkeypatch.setattr(drift_check, "check_prose_flags", lambda *a: [])
    monkeypatch.setattr(drift_check, "check_untracked_modules", lambda: untracked)
    monkeypatch.setattr(sys, "argv", ["drift_check.py", "--enforce"])

    assert drift_check.main() == expected_exit
    out = capsys.readouterr().out
    assert f"[8] untracked modules present but not staged: {len(untracked)}" in out
    assert ("FAIL" if untracked else "PASS") in out.splitlines()[-1]
