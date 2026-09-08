"""Drift gate check 22 — a command name never silently changes what it targets.

Why: check 1 proves every spec op HAS a command; nothing proved an existing
name still points where it pointed last week. Measured 2026-09-08: the pending
Meetings regen moves `meetings create` from POST /meetings to
POST /group/meetings/controls and the gate reads PASS. Every case below is
paired does-not-fire / does-fire so a check reading 0 over nothing cannot pass.
"""
import json
from pathlib import Path

import pytest

from tools import drift_check as dc

LOCKED = {"meetings": {"create": ["POST /meetings"], "list": ["GET /meetings"]},
          "call_park": {"show": ["GET /telephony/config/locations/{}/callParks/{}"]}}


def test_identical_surface_fires_nothing():
    r = dc.check_name_lock(current=LOCKED, locked=LOCKED)
    assert r == {"retargeted": [], "removed": [], "removed_modules": [], "unlocked": []}


def test_retargeted_name_fires_and_names_the_holder():
    now = {"meetings": {"create": ["POST /group/meetings/controls"],
                        "create-meetings": ["POST /meetings"], "list": ["GET /meetings"]},
           "call_park": LOCKED["call_park"]}
    r = dc.check_name_lock(current=now, locked=LOCKED)
    assert [x["command"] for x in r["retargeted"]] == ["create"]
    assert r["retargeted"][0]["locked"] == ["POST /meetings"]
    assert r["retargeted"][0]["now"] == ["POST /group/meetings/controls"]
    assert r["retargeted"][0]["now_held_by"] == "create-meetings"
    assert [x["command"] for x in r["unlocked"]] == ["create-meetings"]


def test_removed_command_and_removed_module_fire():
    now = {"meetings": {"list": ["GET /meetings"]}}
    r = dc.check_name_lock(current=now, locked=LOCKED)
    assert [x["command"] for x in r["removed"]] == ["create"]
    assert [x["module"] for x in r["removed_modules"]] == ["call_park"]


def test_no_url_commands_compare_as_equal_empty_lists():
    lock = {"cucm": {"discover": []}}
    assert dc.check_name_lock(current=lock, locked=lock)["retargeted"] == []


def test_build_name_lock_reads_visible_names_and_urls(tmp_path):
    (tmp_path / "probe.py").write_text('''
import typer
app = typer.Typer()

@app.command("old-name", hidden=True)
@app.command("show")
def show(x: str):
    url = f"https://webexapis.com/v1/probe/{x}"
    rest_get(url)

@app.command("create")
def create():
    url = f"https://webexapis.com/v1/probe"
    rest_post(url)
''')
    lock = dc.build_name_lock(commands_dir=tmp_path, modules=["probe"])
    assert lock == {"probe": {"create": ["POST /probe"], "show": ["GET /probe/{}"]}}
    # hidden alias is NOT locked — it is a compatibility shim for a rename
    assert "old-name" not in lock["probe"]


def test_refresh_refuses_on_retarget_without_force(tmp_path, monkeypatch):
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps({"modules": {"probe": {"show": ["GET /other"]}}}))
    (tmp_path / "probe.py").write_text('''
import typer
app = typer.Typer()
@app.command("show")
def show():
    url = f"https://webexapis.com/v1/probe"
    rest_get(url)
''')
    rc = dc.refresh_name_lock(path=lock_path, commands_dir=tmp_path, modules=["probe"])
    assert rc == 1
    assert json.loads(lock_path.read_text())["modules"]["probe"]["show"] == ["GET /other"]
    rc = dc.refresh_name_lock(path=lock_path, force=True, commands_dir=tmp_path, modules=["probe"])
    assert rc == 0
    assert json.loads(lock_path.read_text())["modules"]["probe"]["show"] == ["GET /probe"]


def test_refresh_is_additive_when_nothing_moved(tmp_path):
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps({"modules": {"probe": {"show": ["GET /probe"]}}}))
    (tmp_path / "probe.py").write_text('''
import typer
app = typer.Typer()
@app.command("show")
def show():
    url = f"https://webexapis.com/v1/probe"
    rest_get(url)
@app.command("create")
def create():
    url = f"https://webexapis.com/v1/probe"
    rest_post(url)
''')
    assert dc.refresh_name_lock(path=lock_path, commands_dir=tmp_path, modules=["probe"]) == 0
    assert json.loads(lock_path.read_text())["modules"]["probe"] == {
        "create": ["POST /probe"], "show": ["GET /probe"]}


def test_docstring_and_ci_name_check_22():
    doc = dc.__doc__
    assert "\n  21. " in doc and "\n  22. " in doc, "checks 21 and 22 must be listed in the header"
    ci = (Path(dc.REPO) / ".github" / "workflows" / "ci.yml").read_text()
    assert r"^\[22\]" in ci, "CI completion assertion must name the last check"


# ------------------------------------------------------------- live tree

def test_live_tree_matches_the_committed_lock():
    """Pins the real tree at zero. Fails until Task 1 step 6 seeds the lock,
    and fails again the moment a regen moves a name — which is the point."""
    r = dc.check_name_lock()
    assert r["retargeted"] == [], r["retargeted"][:5]
    assert r["removed"] == [], r["removed"][:5]
    assert r["removed_modules"] == [], r["removed_modules"][:5]
    assert r["unlocked"] == [], r["unlocked"][:5]


def test_live_lock_is_not_empty():
    modules = dc.load_name_lock()["modules"]
    assert len(modules) >= 170, len(modules)
    assert sum(len(v) for v in modules.values()) > 1800
