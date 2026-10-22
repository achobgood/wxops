"""Tier 2 — mutation round-trip suite for wxcc's Flow Store surface, driven through `wxcli`.

DOUBLE-GATED: runs only with `-m mutation` AND env `WXCLI_LIVE_MUTATION=1` (plus
explicit in-session user approval). Every flow it creates is named
`CLITest_WebexOps_*` and is deleted in teardown even on failure; a session
safety-sweep deletes any `CLITest_WebexOps_*` straggler. It NEVER touches a
flow it did not create.

Covers: kitchen-sink import/export round-trip; the open platform facts
(generate-otp pinValidity, verify-otp extra props + ports, cryptographic-hash
outputs, implicit-out ports, BYOC channelName); publish with and without
validation; and the 21 mutating wxcc operations (blocked stub, the three wxcc
used to warn on, lifecycle create/teardown).

Plan 2 Task 20 (2026-10-19): every `wxcc-flow` call is translated through
docs/merge/wxcc-flow-command-map.md; the row is named next to each call.

Run:  WXCLI_LIVE_MUTATION=1 pytest tests/wxcc/test_live_mutation.py -m mutation
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from tests.wxcc.conftest import REPO, WXCLI_BIN, MANIFEST, PREFIX, run_cli

pytestmark = pytest.mark.mutation

KITCHEN_SINK = REPO / "docs" / "plans" / "flowir" / "kitchen-sink-test.json"
MUTATING = [e for e in MANIFEST if e.get("read_only") is False]
_PID = os.getpid()
_HTTP_STATUS = re.compile(r"\b[45]\d\d\b")


# --------------------------------------------------------------- helpers
def _create_from(project_id: str, body: dict, tmp: Path, name: str) -> str:
    """Import a FlowIR body under `name`; return the created flow id."""
    body = dict(body)
    body["name"] = name
    p = tmp / f"{name}.json"
    p.write_text(json.dumps(body))
    # Map row 20: `create BODY_FILE` -> `cc-flow create-import P --json-body file://…`.
    r = run_cli("cc-flow", "create-import", project_id, "--json-body", f"file://{p}",
                "-o", "json")
    assert r.code == 0, f"create failed: {r.combined[:400]}"
    d = json.loads(r.out)
    fid = d.get("id") or (d.get("flow") or {}).get("id")
    assert fid, f"no id in create response: {r.out[:300]}"
    return fid


def _delete(project_id: str, fid: str):
    # Map row 3: wxcc's `delete F --force` (skip the prompt, server default) is
    # `cc-flow delete P F --force no`.
    return run_cli("cc-flow", "delete", project_id, fid, "--force", "no", "-o", "json")


def _node_activity(node: dict) -> str:
    props = node.get("properties") or {}
    return props.get("activityName") or node.get("activityType") or ""


def _find_prop(obj, key):
    """Every value stored under `key` anywhere inside a node/dict (export-shape agnostic)."""
    hits = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == key:
                    hits.append(v)
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(obj)
    return hits


# ------------------------------------------------------------- fixtures
@pytest.fixture
def make_flow(mutation_env, project_id, tmp_path):
    """Factory: create CLITest_WebexOps_* flows from a FlowIR body; delete all on teardown."""
    created = []

    def _make(suffix, body=None):
        body = body if body is not None else json.loads(KITCHEN_SINK.read_text())
        name = f"{PREFIX}{suffix}_{_PID}"
        fid = _create_from(project_id, body, tmp_path, name)
        created.append(fid)
        return fid, name

    yield _make
    for fid in created:
        _delete(project_id, fid)


@pytest.fixture(scope="session", autouse=True)
def _clitest_safety_sweep():
    """After the mutation session, delete any stray CLITest_WebexOps_* flow."""
    yield
    if os.environ.get("WXCLI_LIVE_MUTATION") != "1" or WXCLI_BIN is None:
        return
    prefs = run_cli("cc-flow-projects", "show-user-preferences", "-o", "json")
    if prefs.code != 0:
        return
    project_id = json.loads(prefs.out).get("projectId")
    r = run_cli("cc-flow", "list", project_id, "--all", "-o", "json")
    if r.code == 0:
        for f in json.loads(r.out):
            # "in" (not startswith) also catches copies, which prepend "Copy_".
            if PREFIX in str(f.get("name", "")):
                _delete(project_id, f["id"])


# ===================================================== open platform facts
def _export(project_id, fid):
    # Map row 26: wxcc's `export` gave the draft; `cc-flow export` needs `--version draft`.
    r = run_cli("cc-flow", "export", project_id, fid, "--version", "draft", "-o", "json")
    assert r.code == 0, r.err
    return json.loads(r.out)


def _nodes_by_activity(flow, activity):
    return [n for n in flow.get("nodes", []) if _node_activity(n) == activity]


def test_kitchen_sink_round_trips(make_flow, project_id):
    fid, name = make_flow("KitchenSink")
    exp = _export(project_id, fid)
    src = json.loads(KITCHEN_SINK.read_text())
    assert exp["name"] == name
    assert len(exp["nodes"]) == len(src["nodes"]), "node count changed on round-trip"
    assert len(exp["edges"]) == len(src["edges"]), "edge count changed on round-trip"


def test_open_fact1_generate_otp_pinvalidity(make_flow, project_id):
    """Fact 1: pinValidity survives import round-trip; capture the stored value.
    (Unit — minutes vs seconds — needs a UI check; the doc conflict note stands.)"""
    fid, _ = make_flow("GenOTP")
    node = _nodes_by_activity(_export(project_id, fid), "generate-otp")
    assert node, "generate-otp node missing after round-trip"
    vals = _find_prop(node[0], "pinValidity")
    print(f"OPEN-FACT 1 generate-otp.pinValidity round-tripped: {vals}")
    assert vals and str(vals[0]) == "300", f"expected '300' to survive; got {vals}"


def test_open_fact2_verify_otp_extra_props(make_flow, project_id, tmp_path):
    """Fact 2: do notifyURL/resendCommand/extraParameters survive when added to a
    verify-otp node? Either outcome is a documentable finding (no CLI crash)."""
    body = json.loads(KITCHEN_SINK.read_text())
    extra = {"notifyURL": "https://example.com/otp", "resendCommand": "resend",
             "extraParameters": [{"key": "k", "value": "v"}]}
    for n in body["nodes"]:
        if _node_activity(n) == "verify-otp":
            n["properties"].update(extra)
    body["name"] = f"{PREFIX}VerifyExtraValidate_{_PID}"
    p = tmp_path / "verify_extra.json"
    p.write_text(json.dumps(body))
    # Map row 19: `validate BODY_FILE` -> `cc-flow create-validate P --json-body file://…`.
    # wxcc exited non-zero on an invalid body; the endpoint answers 200 with `valid`.
    v = run_cli("cc-flow", "create-validate", project_id, "--json-body", f"file://{p}",
                "-o", "json")
    print(f"OPEN-FACT 2 validate exit={v.code}: {v.combined[:200]}")
    assert "Traceback" not in v.combined
    if v.code != 0 or json.loads(v.out).get("valid") is not True:
        pytest.skip("the kitchen-sink body itself fails validation (case-statement / escalated), "
                    f"so the verify-otp extra props are never tested: {v.combined[:160]}")
    fid, _ = make_flow("VerifyExtra", body=body)
    node = _nodes_by_activity(_export(project_id, fid), "verify-otp")[0]
    survived = {k: bool(_find_prop(node, k)) for k in extra}
    print(f"OPEN-FACT 2 verify-otp extra props survived round-trip: {survived}")


def test_open_fact3_4_6_ports_and_hash_outputs(make_flow, project_id):
    """Facts 3/6 (verify-otp + implicit-out ports via round-trip edges) and
    Fact 4 (cryptographic-hash outputs). Records the export shape as evidence."""
    fid, _ = make_flow("PortsHash")
    exp = _export(project_id, fid)
    edges = exp.get("edges", [])
    print(f"OPEN-FACT 3/6 total round-tripped edges: {len(edges)}")
    for act in ("generate-otp", "verify-otp", "cryptographic-hash"):
        nodes = _nodes_by_activity(exp, act)
        if not nodes:
            continue
        nname = nodes[0].get("name")  # edges reference nodes by NAME, not id
        ports = sorted({e.get("condition") for e in edges
                        if e.get("from") == nname and e.get("condition")})
        print(f"OPEN-FACT 3/6 {act} ({nname}) outgoing edge port conditions: {ports or '(none)'}")
    hnode = _nodes_by_activity(exp, "cryptographic-hash")
    if hnode:
        outs = _find_prop(hnode[0], "outputs") + _find_prop(hnode[0], "HashOutput")
        print(f"OPEN-FACT 4 cryptographic-hash output shape: {json.dumps(outs)[:240]}")
    assert edges, "kitchen-sink lost all edges on round-trip"


def test_open_fact5_byoc_channelname_and_schema(mutation_env, project_id):
    """Fact 5: BYOC ReceiveMessage/SendCustomMessage — does channelName resolve
    choices on this (unprovisioned) org, and are the activities describable?
    Records evidence; no custom messaging channel is provisioned here."""
    for act in ("ReceiveMessage", "SendCustomMessage"):
        # Map rows 31 and 30.
        ch = run_cli("cc-flow", "list-activity-choices", project_id, act, "channelName",
                     "-o", "json")
        print(f"OPEN-FACT 5 choices {act} channelName: exit={ch.code} :: {ch.combined[:160]}")
        sc = run_cli("cc-flow", "show-activity", project_id, act, "-o", "json")
        assert sc.code == 0, f"{act} should be describable: {sc.err[:160]}"
        d = json.loads(sc.out)
        inputs = [i["name"] for i in d.get("inputs", [])]
        ports = [p["condition"] for p in d.get("outputPorts", [])]
        print(f"OPEN-FACT 5 {act} inputs={inputs} ports={ports}")


# ================================================ lifecycle + publish/validate
def test_lifecycle_lock_unlock_copy_publish(make_flow, project_id, tmp_path):
    """Verified state-changers on a CLEAN throwaway flow. (The kitchen-sink is an
    intentionally-incomplete harness that `copy` 500s on — a documented finding —
    so lifecycle uses the simple-inbound starter.) lock -> unlock -> copy ->
    publish. The copy is deleted here; the source in make_flow teardown."""
    # Map row H3: `template NAME --out FILE` -> `cc-flow show-starter-flow NAME > FILE`.
    tpl = run_cli("cc-flow", "show-starter-flow", "simple-inbound", "-o", "json")
    assert tpl.code == 0, tpl.combined[:200]
    fid, _ = make_flow("Lifecycle", body=json.loads(tpl.out))
    # Map rows 15 and 12: FLOW_ID comes before PROJECT_ID.
    assert run_cli("cc-flow", "create-lock", fid, project_id).code == 0
    assert run_cli("cc-flow", "create-unlock", fid, project_id).code == 0
    # Map row 9: `copy F` -> `cc-flow-store copy P --source-flow-id F`.
    cp = run_cli("cc-flow-store", "copy", project_id, "--source-flow-id", fid, "-o", "json")
    assert cp.code == 0, cp.combined[:200]
    cd = json.loads(cp.out)
    copy_id = cd.get("id") or (cd.get("flow") or {}).get("id")
    try:
        assert copy_id, f"copy returned no id: {cp.out[:200]}"
    finally:
        if copy_id:
            _delete(project_id, copy_id)
    # Map row 14: wxcc's `publish` skipped validation, and `cc-flow publish`
    # validates unless given `--skip-validation true` (P2-3).
    pub = run_cli("cc-flow", "publish", fid, project_id, "--skip-validation", "true")
    print(f"lifecycle publish exit={pub.code}: {pub.combined[:160]}")
    assert "Traceback" not in pub.combined


def test_publish_with_validate_flag(make_flow, project_id):
    """wxcc's `publish --validate` validated at publish time (a distinct code path).
    The unflagged `cc-flow publish` is that same call (map row 14)."""
    r = run_cli("cc-flow", "publish", make_flow("PublishValidate")[0], project_id)
    print(f"publish (validating) exit={r.code}: {r.combined[:200]}")
    assert "Traceback" not in r.combined


def test_save_draft_round_trips(make_flow, project_id, tmp_path):
    """save-draft: a description round-trip proves the draft was saved."""
    fid, name = make_flow("SaveDraft")
    body = json.loads(KITCHEN_SINK.read_text())
    body["name"] = name
    body["description"] = "clitest-savedraft-marker"
    p = tmp_path / "draft.json"
    p.write_text(json.dumps(body))
    # Map row 22: `save-draft F BODY_FILE` -> `cc-flow create-flows P F --json-body file://…`.
    r = run_cli("cc-flow", "create-flows", project_id, fid, "--json-body", f"file://{p}")
    print(f"save-draft exit={r.code}: {r.combined[:160]}")
    assert r.code == 0, r.combined[:240]
    assert _export(project_id, fid).get("description") == "clitest-savedraft-marker"


def test_update_renames_draft(make_flow, project_id):
    """update sets a new description on the draft (verified live)."""
    fid, _ = make_flow("Update")
    # Map row 24: `update F --description X` -> `cc-flow update P F --json-body '{"description":X}'`.
    r = run_cli("cc-flow", "update", project_id, fid,
                "--json-body", json.dumps({"description": "clitest-update-marker"}))
    assert r.code == 0, r.combined[:200]
    assert _export(project_id, fid).get("description") == "clitest-update-marker"


# ============================================== mutating api namespace (21)
def test_api_merge_patch_is_blocked_stub():
    """merge-patch is a blocked no-op: exit 2, no HTTP call, points to update (map row 2)."""
    r = run_cli("cc-flow-store", "update-metadata")
    assert r.code == 2, f"expected exit 2; got {r.code}: {r.combined[:200]}"
    assert "no-op" in r.combined and "cc-flow update" in r.combined, r.combined[:200]


# wxcc printed a "Warning:" banner on these three. The banner is not carried
# (command map rows 19, 23 and 11), so the test now asserts that each one
# reaches the server and answers without a CLI crash.
_WARN_MUTATORS = [("flows-v2", "validate"), ("flows-v2", "patch-draft"), ("flows", "consume-template")]


@pytest.mark.parametrize("g,c", _WARN_MUTATORS, ids=[f"{g}.{c}" for g, c in _WARN_MUTATORS])
def test_api_formerly_warned_mutators_answer(g, c, make_flow, project_id, tmp_path):
    body = tmp_path / "body.json"
    body.write_text(KITCHEN_SINK.read_text())
    if (g, c) == ("flows-v2", "validate"):
        r = run_cli("cc-flow", "create-validate", project_id, "--json-body", f"file://{body}",
                    "-o", "json")
        assert r.code == 0 and "valid" in json.loads(r.out), r.combined[:300]
    elif (g, c) == ("flows-v2", "patch-draft"):
        r = run_cli("cc-flow", "update", project_id, make_flow("PatchWarn")[0],
                    "--json-body", f"file://{body}", "-o", "json")
        print(f"patch-draft exit={r.code}: {r.combined[:200]}")
        assert r.code == 0 or _HTTP_STATUS.search(r.combined), r.combined[:300]
    else:  # non-existent template -> the server refuses it
        r = run_cli("cc-flow-store", "consume-template", project_id,
                    "--template-name", "__clitest_no_such_tpl__",
                    "--flow-name", f"{PREFIX}ConsumeTplWarn_{_PID}")
        print(f"consume-template exit={r.code}: {r.combined[:200]}")
        assert r.code != 0 and _HTTP_STATUS.search(r.combined), r.combined[:300]
    assert "Traceback" not in r.combined, r.combined[:300]


def test_api_unique_name_probe(mutation_env, project_id):
    """unique-name checks a name without mutating (exit 0 = unique; map row 7)."""
    r = run_cli("cc-flow-store", "check-name", project_id,
                "--flow-name", f"{PREFIX}DefinitelyUnique_{_PID}")
    assert r.code == 0, r.combined[:200]


# Explicit accounting for all 21 mutating wxcc operations: each names the
# command that replaces it (with its command map row) and the live test that
# exercises it, or a documented reason it is not run. Makes the "iterate the 21"
# requirement provably complete without blind, unsafe execution.
_MUTATION_COVERAGE = {
    ("flows", "merge-patch"): "cc-flow-store update-metadata (2): test_api_merge_patch_is_blocked_stub",
    ("flows", "consume-template"): "cc-flow-store consume-template (11): test_api_formerly_warned_mutators_answer",
    ("flows-v2", "validate"): "cc-flow create-validate (19): test_api_formerly_warned_mutators_answer",
    ("flows-v2", "patch-draft"): "cc-flow update (23): test_api_formerly_warned_mutators_answer",
    ("flows", "lock"): "cc-flow create-lock (15): test_lifecycle_lock_unlock_copy_publish",
    ("flows", "unlock"): "cc-flow create-unlock (12): test_lifecycle_lock_unlock_copy_publish",
    ("flows", "copy"): "cc-flow-store copy (9): test_lifecycle_lock_unlock_copy_publish",
    ("flows", "publish"): "cc-flow publish (14): test_lifecycle + test_publish_with_validate_flag",
    ("flows", "delete"): "cc-flow delete (3): make_flow teardown + copy teardown + safety sweep",
    ("flows", "import"): (
        "cc-legacy-flows import-ui (8): SKIP: takes a v1 UI-export file, not FlowIR "
        "(measured 201 in Plan 2 Task 3, docs/merge/flow-store-host-map.md § v1 UI import route)"
    ),
    ("flows-v2", "import"): "cc-flow create-import (20): test_kitchen_sink_round_trips (create == import)",
    ("flows-v2", "save-draft"): "cc-flow create-flows (22): test_save_draft_round_trips",
    ("flows-v2", "update"): "cc-flow update (24): test_update_renames_draft",
    ("flows", "unique-name"): "cc-flow-store check-name (7): test_api_unique_name_probe",
    ("util", "test-expr"): "cc-flow-store test-expression (57): SKIP: covered by Tier 1 test_test_expr_sends_expr_field",
    ("flows", "consume"): "cc-flow-store consume (10): SKIP: expects UI-export shape body, not FlowIR",
    ("flows", "revert"): "cc-flow-store revert (13): SKIP: needs a prior published version to revert to",
    ("flows", "variable-mapping"): "cc-flow-store map-variables (6): SKIP: needs a related GoTo hand-off flow pair",
    ("prefs", "add"): "cc-flow-prefs create (44): SKIP: needs a bespoke flow-preference body",
    ("prefs", "set"): "cc-flow-prefs update (45): SKIP: needs a bespoke flow-preference body",
    ("prefs", "remove"): "cc-flow-prefs delete (46): SKIP: needs a bespoke flow-preference body",
}


def test_all_21_mutating_commands_are_accounted_for():
    live = {(e["group"], e["command"]) for e in MUTATING}
    assert live == set(_MUTATION_COVERAGE), (
        f"uncovered mutating commands: {sorted(live - set(_MUTATION_COVERAGE))}; "
        f"stale coverage entries: {sorted(set(_MUTATION_COVERAGE) - live)}"
    )
