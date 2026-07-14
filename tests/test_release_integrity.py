"""Regression coverage for the release-integrity CI contract."""
from pathlib import Path

import pytest

from wxcli.commands import update as update_command


class _SuccessfulRun:
    returncode = 0


@pytest.mark.parametrize(
    ("profiles", "expected"),
    [
        (("claude",), ["wxcli", "init", "--force", "--claude-only"]),
        (("codex",), ["wxcli", "init", "--force", "--codex-only"]),
        (("claude", "codex"), ["wxcli", "init", "--force"]),
    ],
    ids=("claude-only", "codex-only", "dual-profile"),
)
def test_refresh_playbook_preserves_installed_profiles(tmp_path, profiles, expected):
    for profile in profiles:
        manifest = tmp_path / f".{profile}" / ".wxops-manifest.json"
        manifest.parent.mkdir()
        manifest.write_text("{}")
    calls = []

    update_command.refresh_playbook(
        "9.9.9",
        yes=True,
        cwd=tmp_path,
        run=lambda command, **_: calls.append(command) or _SuccessfulRun(),
    )

    assert calls == [expected + [str(tmp_path)]]


def test_pull_requests_and_releases_run_wheel_integrity_contract():
    root = Path(__file__).resolve().parent.parent
    ci = (root / ".github/workflows/ci.yml").read_text()
    release = (root / ".github/workflows/release.yml").read_text()
    assert "pull_request:" in ci
    assert "release-integrity:" in ci
    # The playbook bundle is rebuilt before the wheel is built, so the smoke
    # test below exercises a fresh bundle rather than whatever was committed.
    # CI pins the interpreter with actions/setup-python and then invokes bare
    # `python`; asserting a `python3.11` spelling tracked neither.
    assert "python wxcli-dist/assemble.py" in ci
    assert "tools/wheel_playbook_smoke.py dist/wxcli-*.whl" in ci
    assert "tools/wheel_playbook_smoke.py dist/wxcli-*.whl" in release
