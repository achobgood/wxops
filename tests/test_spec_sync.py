"""spec_sync.py is the ONE regeneration entry point (spec §4 Part 1).

Two properties pinned here. (1) The step list is the contract's mechanical
list, in order, and the check-19 delta is written to disk BEFORE the snapshot
is rewritten — refreshing unattended is a blanket acknowledgment, and the only
thing that makes it auditable is that the delta lands in the run record.
(2) Published counts are repaired mechanically from the gate's own harvester,
so check 3 cannot fail after a regen for want of a hand edit.
"""
import re
from pathlib import Path

import pytest

from tools import spec_sync

REPO = Path(spec_sync.REPO)


def test_step_order_is_the_contract(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(spec_sync, "run", lambda cmd, **kw: calls.append(" ".join(str(c) for c in cmd)))
    monkeypatch.setattr(spec_sync, "tracked_specs", lambda: ["webex-cloud-calling.json", "webex-device.json"])
    monkeypatch.setattr(spec_sync, "repair_published_counts", lambda: [])
    monkeypatch.setattr("sys.argv", ["spec_sync.py", "--run-dir", str(tmp_path)])
    spec_sync.main()
    heads = [re.sub(r"^\S+ ", "", c) for c in calls]  # drop the interpreter path
    assert heads[0] == "tools/update-specs.py"
    assert heads[1] == "tools/generate_commands.py --spec specs/webex-cloud-calling.json --all"
    assert heads[2] == "tools/generate_commands.py --spec specs/webex-device.json --all"
    assert heads[3] == "-m tools.drift_check --refresh-name-lock"
    assert heads[4] == "-m tools.drift_check --refresh-spec-snapshot"
    assert heads[5] == "wxcli-dist/assemble.py"
    assert heads[6] == "-m tools.drift_check --write-gaps"
    assert "tools/drift_check.py" not in " ".join(heads), "module form only"


def test_skip_update_drops_the_pull(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(spec_sync, "run", lambda cmd, **kw: calls.append(" ".join(str(c) for c in cmd)))
    monkeypatch.setattr(spec_sync, "tracked_specs", lambda: ["webex-ucm.json"])
    monkeypatch.setattr(spec_sync, "repair_published_counts", lambda: [])
    monkeypatch.setattr("sys.argv", ["spec_sync.py", "--skip-update", "--run-dir", str(tmp_path)])
    spec_sync.main()
    assert not any("update-specs" in c for c in calls)


def test_run_dir_receives_the_three_records(monkeypatch, tmp_path):
    def fake_run(cmd, **kw):
        if "tee" in kw:
            kw["tee"].write_text("fake output\n")
    monkeypatch.setattr(spec_sync, "run", fake_run)
    monkeypatch.setattr(spec_sync, "tracked_specs", lambda: [])
    monkeypatch.setattr(spec_sync, "repair_published_counts", lambda: [])
    monkeypatch.setattr("sys.argv", ["spec_sync.py", "--skip-update", "--run-dir", str(tmp_path)])
    spec_sync.main()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["gate.txt", "name-lock.txt", "spec-delta.txt"]


def test_repair_counts_rewrites_only_the_number(tmp_path, monkeypatch):
    from tools import drift_check as dc
    claude = tmp_path / "CLAUDE.md"; readme = tmp_path / "README.md"
    claude.write_text("The wxcli CLI has 178 command groups covering calling.\n")
    readme.write_text("- **178 CLI command groups** — provision\nSee all 178 groups via wxcli --help.\n")
    monkeypatch.setattr(dc, "REPO", tmp_path)
    changed = spec_sync.repair_published_counts(measured=180)
    assert sorted(Path(c).name for c in changed) == ["CLAUDE.md", "README.md"]
    assert claude.read_text() == "The wxcli CLI has 180 command groups covering calling.\n"
    assert readme.read_text() == "- **180 CLI command groups** — provision\nSee all 180 groups via wxcli --help.\n"


def test_repair_counts_is_a_noop_when_correct(tmp_path, monkeypatch):
    from tools import drift_check as dc
    (tmp_path / "CLAUDE.md").write_text("178 command groups\n")
    (tmp_path / "README.md").write_text("178 command groups\n")
    monkeypatch.setattr(dc, "REPO", tmp_path)
    assert spec_sync.repair_published_counts(measured=178) == []
