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
