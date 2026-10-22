"""Drift gate checks 11a, 11b and 12 — the three added on 2026-07-28.

Each test here covers a decision that a future edit could quietly undo:

* 11a must read the RENDERED command, never the spec. `auto_inject_from_config`
  supplies orgId from saved config, so 12 operations declare a required query
  parameter that legitimately never appears in `--help`; a spec-driven version
  reports all 12 as missing flags.
* 11b tier 1 must stay off arguments whose declared kind contradicts their own
  parameter name. 79 of the 1049 kind-carrying arguments are mislabelled
  (`location_id` help-typed "Webex PEOPLE id"), and comparing a doc placeholder
  against a wrong label reports CORRECT docs as defects — 240 of them, measured,
  before the exclusion went in.
* 12's acknowledgement list must ratchet: new debt fails, and an ack that stops
  describing reality fails rather than silently covering a name nobody reviewed.
"""

import pytest

from tools import drift_check as dc


# ------------------------------------------------------------------ check 12

def _finding(**kw):
    base = {"group": "video-mesh", "command": "list", "kind": "resource-mismatch",
            "op": "GET /v1/videoMesh/clusters/availability", "severity": "HIGH",
            "summary": "List Clusters Availability.", "url": "https://x/y",
            "loc": "video_mesh.py:1", "proposed": "list-availability", "why": "w"}
    return {**base, **kw}


def _ack(command="video-mesh list", severity="HIGH",
         key="resource-mismatch GET /v1/videoMesh/clusters/availability"):
    return {key: {"command": command, "severity": severity}}


def test_acked_finding_does_not_fail():
    unacked, stale, _ = dc.check_naming([_finding()], _ack())
    assert unacked == [] and stale == []


def test_new_debt_with_no_ack_fails():
    """The whole point of the ratchet: an unacknowledged HIGH stops the build."""
    unacked, stale, _ = dc.check_naming([_finding()], {})
    assert len(unacked) == 1 and stale == []


def test_ack_goes_stale_when_the_command_is_renamed():
    """Renaming is the FIX. The ack must then be revisited, not silently
    inherited by whatever name now sits on that operation."""
    unacked, stale, _ = dc.check_naming(
        [_finding(command="list-availability")], _ack())
    assert unacked == [] and len(stale) == 1
    assert "renamed" in stale[0]["reason"]


def test_ack_goes_stale_when_the_severity_changes():
    unacked, stale, _ = dc.check_naming([_finding(severity="CRITICAL")], _ack())
    assert len(stale) == 1 and "CRITICAL" in stale[0]["reason"]


def test_ack_for_a_vanished_operation_goes_stale():
    """A fixed or deleted command leaves its ack behind; that ack is a permanent
    blind spot unless the gate makes deleting it mandatory."""
    _unacked, stale, _ = dc.check_naming([], _ack())
    assert len(stale) == 1 and "delete this ack" in stale[0]["reason"]


def test_medium_is_reported_but_never_gated():
    """CRITICAL+HIGH fails (Adam, 2026-07-28); MEDIUM is advisory. A gate that
    fails on the long tail gets switched off within a week."""
    unacked, stale, advisory = dc.check_naming([_finding(severity="MEDIUM")], {})
    assert unacked == [] and stale == [] and len(advisory) == 1


def test_numeric_suffix_findings_skip_hidden_rename_aliases():
    """A hidden `-N` alias is the compatibility shim left behind BY a rename —
    the fix for this defect, not an instance of it."""
    from tools import verb_naming as vn
    visible = vn.Cmd("g", "m", "list-1", 1, "s", "https://x/v1/things", "GET")
    alias = vn.Cmd("g", "m", "list-2", 1, "s", "https://x/v1/things", "GET",
                   hidden=True)
    names = [f["command"] for f in vn.numeric_suffix_findings([visible, alias])]
    assert names == ["list-1"]


def test_flow_store_base_is_not_a_path_segment():
    """Flow Store modules build URLs on `{fs_base_url}` (BASE_URL_FS) as CC
    modules do on `{cc_base_url}`; left in, it reads as a resource segment."""
    from tools import verb_naming as vn
    rest = "/{org_id}/project/{project_id}/widgets"
    assert vn.url_path("{fs_base_url}" + rest) == vn.url_path("{cc_base_url}" + rest)
    assert vn.url_path("{fs_base_url}" + rest) == [
        "{org_id}", "project", "{project_id}", "widgets"]
    assert "{fs_base_url}" in vn.SKIP_SEG


def test_the_live_tree_has_no_unacked_or_stale_names():
    """Zero here means every shipping name is either honest or acknowledged."""
    unacked, stale, _ = dc.check_naming(
        dc.build_naming_findings(),
        dc.load_overrides().get("naming_ack") or {})
    assert unacked == [], (
        f"{len(unacked)} unacknowledged name(s): "
        + ", ".join(f"{u['group']} {u['command']}" for u in unacked[:10]))
    assert stale == [], (
        f"{len(stale)} stale ack(s): "
        + ", ".join(f"{s['op']} {s['reason']}" for s in stale[:5]))


# ----------------------------------------------------------------- check 11a

def test_required_options_read_ellipsis_not_the_spec():
    """`typer.Option(...)` is required; `typer.Option(None, ...)` is not. Read
    off the rendered file so config-injected parameters stay invisible."""
    req = dc.parse_module_required_options("video_mesh")
    assert {"--from"} <= {n for names in req["show"] for n in names}
    assert req["show-clusters"] == []


def test_no_required_option_is_a_request_body_field():
    """Measured 0 of 158 on 2026-07-28. If this ever fails, `--json-body` CAN
    supply a required option and check 11a needs a body-aware exemption."""
    import ast
    from pathlib import Path
    body_backed = []
    for group, module in dc.parse_registrations().items():
        if module not in dc.module_state()["countable"]:
            continue
        path = Path(dc.COMMANDS_DIR) / f"{module}.py"
        if not path.exists():
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.FunctionDef):
                continue
            required = {p.arg for p, d in zip(
                node.args.args,
                [None] * (len(node.args.args) - len(node.args.defaults))
                + list(node.args.defaults))
                if (d is not None and dc._typer_call(d, "Option") is not None
                    and d.args and isinstance(d.args[0], ast.Constant)
                    and d.args[0].value is ...)}
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Assign)
                        and isinstance(sub.targets[0], ast.Subscript)
                        and isinstance(sub.targets[0].value, ast.Name)
                        and sub.targets[0].value.id == "body"
                        and isinstance(sub.value, ast.Name)
                        and sub.value.id in required):
                    body_backed.append(f"{group} {sub.value.id}")
    assert body_backed == []


# ----------------------------------------------------------------- check 11b

def test_synonyms_stop_person_and_workspace_false_positives():
    """PERSON_ID against `Webex PEOPLE id`, and WORKSPACE_ID against
    `Webex PLACE id`, are the repo's own conventions — not defects."""
    assert dc._tokens("PERSON_ID") & dc._tokens("PEOPLE")
    assert dc._tokens("WORKSPACE_ID") & dc._tokens("PLACE")
    assert dc._tokens("USER_ID") & dc._tokens("PEOPLE")
    # ... but genuinely different resources still do not match
    assert not (dc._tokens("PERSON_ID") & dc._tokens("HUNT_GROUP"))


# ------------------------------------------------- 11a/11b: stacked aliases

# A renamed command stacks its hidden deprecated alias FIRST and the visible
# name second (102 functions, measured 2026-10-13). Keying either surface on the
# first decorator alone made every documented citation of the VISIBLE name
# invisible to 11a and 11b — `cc-agents list-activities` cited without `--from`
# passed silently.
STACKED_PROBE = '''"""Probe module."""
import typer

app = typer.Typer()


@app.command("list", hidden=True)
@app.command("list-activities")
def list_activities(
    from_: str = typer.Option(..., "--from"),
    to: str = typer.Option(..., "--to"),
    output: str = typer.Option("table", "--output", "-o"),
):
    """Probe: renamed command with required flags."""


@app.command("show", hidden=True)
@app.command("show-site")
def show_site(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli probe-group list-sites"),
    output: str = typer.Option("json", "--output", "-o"),
):
    """Probe: renamed command with a kind-carrying argument."""


@app.command("show-owner", hidden=True)
@app.command("show-person")
def show_person(
    person_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli probe-group list-people"),
):
    """Probe: a second kind, so a PERSON_ID placeholder names a KNOWN kind."""


@app.command("show-bad", hidden=True)
@app.command("show-mislabelled")
def show_mislabelled(
    location_id: str = typer.Argument(help="Webex PEOPLE id"),
):
    """Probe: a label its own parameter name contradicts."""
'''


def _stacked(tmp_path):
    (tmp_path / "zz_probe.py").write_text(STACKED_PROBE)
    sig = dc.parse_module_signatures("zz_probe", commands_dir=tmp_path)
    surface = {"probe-group": {name: [] for name in sig}}
    return surface, {"probe-group": sig}


def _scan(tmp_path, monkeypatch, doc_text):
    doc = tmp_path / "fixture.md"
    doc.write_text(doc_text)
    monkeypatch.setattr(
        dc, "tracked_files",
        lambda pattern: [str(doc)] if pattern == "docs/reference/**" else [])


def test_required_options_key_every_decorator_name(tmp_path):
    (tmp_path / "zz_probe.py").write_text(STACKED_PROBE)
    req = dc.parse_module_required_options("zz_probe", commands_dir=tmp_path)
    for name in ("list", "list-activities"):
        assert {"--from"} in req[name] and {"--to"} in req[name]


@pytest.mark.parametrize("cited, expected", [
    ("wxcli probe-group list-activities --output json", [["--from", "--to"]]),
    ("wxcli probe-group list-activities --from 1 --to 2", []),
    ("wxcli probe-group list --output json", [["--from", "--to"]]),
])
def test_renamed_command_missing_a_required_flag_fires_11a(
        tmp_path, monkeypatch, cited, expected):
    surface, positional = _stacked(tmp_path)
    required = {"probe-group": dc.parse_module_required_options(
        "zz_probe", commands_dir=tmp_path)}
    _scan(tmp_path, monkeypatch, f"```bash\n{cited}\n```\n")
    findings, _bare = dc.check_required_flags(surface, positional, required)
    assert [f["missing"] for f in findings] == expected


def test_arg_kinds_key_every_decorator_name(tmp_path):
    (tmp_path / "zz_probe.py").write_text(STACKED_PROBE)
    kinds = dc.parse_module_arg_kinds("zz_probe", commands_dir=tmp_path)
    for name in ("show", "show-site"):
        assert [a["kind"] for a in kinds[name]] == ["LOCATION"]


@pytest.mark.parametrize("placeholder, fires", [
    ("PERSON_ID", True), ("LOCATION_ID", False)])
def test_renamed_command_with_a_wrong_placeholder_fires_11b(
        tmp_path, monkeypatch, placeholder, fires):
    surface, positional = _stacked(tmp_path)
    kinds = {"probe-group": dc.parse_module_arg_kinds(
        "zz_probe", commands_dir=tmp_path)}
    _scan(tmp_path, monkeypatch,
          f"```bash\nwxcli probe-group show-site {placeholder}\n```\n")
    mismatches, _adv, _mis = dc.check_arg_kinds(surface, positional, kinds)
    assert [m["cmd"] for m in mismatches] == (
        ["probe-group show-site"] if fires else [])


def test_mislabelled_argument_is_reported_once_under_its_visible_name(
        tmp_path, monkeypatch):
    """Widening the surface to every name must not double-report a CLI-side
    defect, nor report it under a name `--help` does not show."""
    surface, positional = _stacked(tmp_path)
    kinds = {"probe-group": dc.parse_module_arg_kinds(
        "zz_probe", commands_dir=tmp_path)}
    _scan(tmp_path, monkeypatch, "")
    _mm, _adv, mislabelled = dc.check_arg_kinds(surface, positional, kinds)
    assert [(m["command"], m["arg"]) for m in mislabelled] == [
        ("show-mislabelled", "location_id")]


# --------------------------- checks 6 / 9 / 11b siblings: stacked aliases

def test_flags_key_every_decorator_name(tmp_path, monkeypatch):
    (tmp_path / "zz_probe.py").write_text(STACKED_PROBE)
    monkeypatch.setattr(dc, "COMMANDS_DIR", tmp_path)
    flags = dc.parse_module_flags("zz_probe")
    for name in ("list", "list-activities"):
        assert {"--from", "--to", "--output"} <= flags[name]


@pytest.mark.parametrize("cited, dead", [
    ("wxcli probe-group list-activities --from 1 --to 2 --bogus", ["--bogus"]),
    ("wxcli probe-group list-activities --from 1 --to 2", []),
    ("wxcli probe-group list --from 1 --to 2 --bogus", ["--bogus"]),
])
def test_renamed_command_citing_a_flag_it_lacks_fires_6(
        tmp_path, monkeypatch, cited, dead):
    """`check_flags` read a missing flag-surface entry as "a mounted
    sub-typer" and skipped it, so every flag cited on the visible name of a
    renamed command went unchecked."""
    surface, _positional = _stacked(tmp_path)
    monkeypatch.setattr(dc, "COMMANDS_DIR", tmp_path)
    flag_surface = {"probe-group": dc.parse_module_flags("zz_probe")}
    _scan(tmp_path, monkeypatch, f"```bash\n{cited}\n```\n")
    assert [d["flag"] for d in dc.check_flags(surface, flag_surface)] == dead


COLUMNS_PROBE = '''"""Probe module."""
import typer

app = typer.Typer()


@app.command("list-old", hidden=True)
@app.command("list-things")
def list_things():
    """Probe."""
    url = f"https://webexapis.com/v1/things"
    result = api.session.rest_get(url)
    items = result.get("items", [])
    emit(items, columns=[("Name", "name")])
'''


def test_column_findings_carry_the_visible_name(tmp_path):
    (tmp_path / "zz_probe.py").write_text(COLUMNS_PROBE)
    rows = dc.parse_module_columns("zz_probe", tmp_path)
    assert [r[0] for r in rows] == ["list-things"]


SIBLING_PROBE = '''"""Probe module."""
import typer

app = typer.Typer()


@app.command("show-gadget", hidden=True)
@app.command("show-widget")
def show_widget(
    widget_id: str = typer.Argument(help="UUID, from: wxcli probe-group list"),
):
    """Probe: renamed; the hidden alias's name matches the placeholder."""
'''

SIBLING_REAL = '''

@app.command("show-gadget-config")
def show_gadget_config(
    gadget_id: str = typer.Argument(help="UUID, from: wxcli probe-group list"),
):
    """Probe: a genuinely different command named for the placeholder."""
'''


@pytest.mark.parametrize("extra, siblings", [
    ("", []), (SIBLING_REAL, ["show-gadget-config"])])
def test_11b_advisory_never_names_a_commands_own_alias_as_sibling(
        tmp_path, monkeypatch, extra, siblings):
    (tmp_path / "zz_probe.py").write_text(SIBLING_PROBE + extra)
    sig = dc.parse_module_signatures("zz_probe", commands_dir=tmp_path)
    surface = {"probe-group": {name: [] for name in sig}}
    kinds = {"probe-group": dc.parse_module_arg_kinds(
        "zz_probe", commands_dir=tmp_path)}
    _scan(tmp_path, monkeypatch,
          "```bash\nwxcli probe-group show-widget GADGET_ID\n```\n")
    _mm, advisories, _mis = dc.check_arg_kinds(
        surface, {"probe-group": sig}, kinds)
    assert [a["sibling"] for a in advisories] == siblings


def test_all_hidden_function_falls_back_to_its_first_name(tmp_path):
    (tmp_path / "zz_probe.py").write_text('''"""Probe."""
import typer

app = typer.Typer()


@app.command("old-a", hidden=True)
@app.command("old-b", hidden=True)
def gone(location_id: str = typer.Argument(help="Webex PEOPLE id")):
    """Probe: every name hidden."""
''')
    kinds = dc.parse_module_arg_kinds("zz_probe", commands_dir=tmp_path)
    assert kinds["old-a"][0]["visible"] == "old-a"
    assert kinds["old-b"][0]["visible"] == "old-a"
