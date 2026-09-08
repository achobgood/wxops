"""update-specs.py must not report a partial refresh as success.

Verified 2026-09-08 (spec §1): fetch errors were appended to a list and printed,
and the only non-zero exit was --check's "specs are stale". A run in which 6 of
7 downloads failed exited 0, so a caller proceeded with mixed-vintage specs.
"""
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "update-specs.py"


def _load(tmp_specs: Path):
    spec = importlib.util.spec_from_file_location("update_specs", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.SPECS_DIR = tmp_specs
    return mod


def _run(mod, monkeypatch, argv, fetch):
    monkeypatch.setattr(mod, "fetch", fetch)
    monkeypatch.setattr("sys.argv", ["update-specs.py", *argv])
    with pytest.raises(SystemExit) as e:
        mod.main()
        raise SystemExit(0)
    return e.value.code


def test_one_failed_download_exits_2(tmp_path, monkeypatch, capsys):
    mod = _load(tmp_path)
    good = json.dumps({"paths": {"/a": {}}}).encode()
    for local in mod.SPEC_MAP.values():
        (tmp_path / local).write_bytes(good)

    def fetch(url):
        if "webex-device" in url:
            raise OSError("502 Bad Gateway")
        return good

    assert _run(mod, monkeypatch, [], fetch) == 2
    out = capsys.readouterr()
    assert "webex-device.json: fetch failed" in out.out
    assert "partial refresh" in out.err


def test_clean_run_exits_0_and_points_at_spec_sync(tmp_path, monkeypatch, capsys):
    mod = _load(tmp_path)
    old = json.dumps({"paths": {"/a": {}}}).encode()
    new = json.dumps({"paths": {"/a": {}, "/b": {}}}).encode()
    for local in mod.SPEC_MAP.values():
        (tmp_path / local).write_bytes(old)
    assert _run(mod, monkeypatch, [], lambda url: new) == 0
    out = capsys.readouterr().out
    assert "tools/spec_sync.py --skip-update" in out
    assert "make regen" not in out


def test_check_mode_still_means_stale_not_broken(tmp_path, monkeypatch):
    mod = _load(tmp_path)
    old = json.dumps({"paths": {"/a": {}}}).encode()
    new = json.dumps({"paths": {"/a": {}, "/b": {}}}).encode()
    for local in mod.SPEC_MAP.values():
        (tmp_path / local).write_bytes(old)
    assert _run(mod, monkeypatch, ["--check"], lambda url: new) == 1
