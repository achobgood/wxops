"""Tier 1 — read-only live suite for wxcc's Flow Store surface, driven through `wxcli` (`-m live`).

Codifies the 2026-07-11 fix-spec §8 command contracts + the Phase-C command
splits as repeatable pytest, plus the live doc-consistency invariants (registry
count, every registry activity has a doc home, flowir §8 port table vs the
live outputPorts). Offline doc invariants (_index ↔ files, playbook byte-parity)
live in tests/wxcc/test_doc_consistency.py so they run in the default suite.

Plan 2 Task 20 (2026-10-19): every `wxcc-flow` call is translated through
docs/merge/wxcc-flow-command-map.md; the row is named next to each call.

Run:  pytest tests/wxcc/test_live_readonly.py -m live                      # full Tier 1
      pytest tests/wxcc/test_live_readonly.py -m "live and not portaudit"  # skip the port audit
Auto-skips when no token resolves. Every contract verified live on produs1
(the sandbox org) 2026-07-12 through wxcc-flow, and in the sandbox tenant
2026-10-19 through wxcli.
"""
from __future__ import annotations

import json
import re

import pytest

from tests.wxcc.conftest import (
    REPO,
    READ_ONLY,
    WXCLI_READ,
    API_TOLERATE_404,
    API_WARN,
    API_SKIP_INTERACTION,
    run_cli,
)

pytestmark = pytest.mark.live

FLOWIR = REPO / "docs" / "reference" / "flow-designer-flowir.md"


# ========================================================= Task 1a: porcelain
def test_list_paginates_past_ten(flows):
    # org has 57 flows; the old GET /flows size=10 default silently truncated.
    # Map row 4: `cc-flow list P --all` walks every page, as wxcc's `list` did.
    assert len(flows) > 10, f"expected >10 flows (pagination proof); got {len(flows)}"


def test_search_case_insensitive_substring(flows, a_flow_id, project_id):
    name = next(f["name"] for f in flows if f["id"] == a_flow_id)
    token = next((w for w in re.split(r"[-_ ]", name) if len(w) >= 4), None)
    if not token:
        pytest.skip(f"no usable substring in flow name {name!r}")
    # Map row 5: `search TEXT` -> `cc-flow list P --partial-name-search TEXT --all`.
    lower = run_cli("cc-flow", "list", project_id, "--partial-name-search", token.lower(),
                    "--all", "-o", "json")
    upper = run_cli("cc-flow", "list", project_id, "--partial-name-search", token.upper(),
                    "--all", "-o", "json")
    assert lower.code == 0 and upper.code == 0, (lower.err, upper.err)
    lo, up = json.loads(lower.out), json.loads(upper.out)
    assert lo and up, f"case-insensitive substring {token!r} returned nothing"
    assert {f["id"] for f in lo} == {f["id"] for f in up}, "case sensitivity leaked"


def test_describe_flat_shape(project_id):
    # Map row 30: `describe NAME` -> `cc-flow show-activity P NAME`.
    r = run_cli("cc-flow", "show-activity", project_id, "cryptographic-hash", "-o", "json")
    assert r.code == 0, r.err
    d = json.loads(r.out)
    assert {"inputs", "outputPorts", "activityType"} <= set(d), sorted(d)
    assert isinstance(d["inputs"], list) and len(d["inputs"]) > 0, "inputs should render"
    assert isinstance(d["outputPorts"], list), "outputPorts should render as a list"
    assert not ({"inputGroups", "component", "shapeProperties"} & set(d)), (
        "prod uses the FLAT definition shape (no inputGroups/component/shapeProperties)"
    )


def test_schema_renders_template(project_id):
    # Map row H4: `schema ACTIVITY` -> `cc-flow show-node-template P ACTIVITY`.
    r = run_cli("cc-flow", "show-node-template", project_id, "cryptographic-hash")
    assert r.code == 0, r.err
    assert any(t in r.out for t in ("cryptographic-hash", "HashOutput", "error")), r.out[:200]


def test_choices_static_input(project_id):
    # Map row 31: `choices ACT INPUT` -> `cc-flow list-activity-choices P ACT INPUT`.
    r = run_cli("cc-flow", "list-activity-choices", project_id, "queue-contact", "channelType",
                "-o", "json")
    assert r.code == 0, r.err
    d = json.loads(r.out)
    assert d.get("choices") and d.get("count", 0) > 0, d


def test_choices_cascading_requires_parent(project_id):
    r = run_cli("cc-flow", "list-activity-choices", project_id, "queue-contact", "destination",
                "-o", "json")
    assert r.code != 0, "a cascading input queried without its parent should error"
    assert "parent" in r.combined.lower(), r.combined[:200]


def test_choices_cascading_with_parent(project_id):
    # Map row 31: `--parent-input` -> `--parent-input-name`.
    r = run_cli(
        "cc-flow", "list-activity-choices", project_id, "queue-contact", "destination",
        "--parent-input-name", "channelType", "--parent-value", "TELEPHONY", "-o", "json",
    )
    assert r.code == 0, r.err
    d = json.loads(r.out)
    assert d.get("source") == "dynamic" and "choices" in d, d


def test_test_expr_sends_expr_field():
    # Map row 57: `test-expr --expr X` -> `cc-flow-store test-expression --json-body`
    # with the expression in the body and `variables` as a map.
    r = run_cli("cc-flow-store", "test-expression",
                "--json-body", json.dumps({"expr": "{{ 1 + 1 }}", "variables": {}}),
                "-o", "json")
    assert r.code == 0, r.err
    d = json.loads(r.out)
    assert d.get("isValid") is True and d.get("generatedValue") == "2", d


def test_export_round_trips(a_flow_id, project_id):
    # Map row 26: wxcc's `export` defaulted to the draft; `cc-flow export` defaults to
    # the published version (P2-3), so the draft needs `--version draft`.
    r = run_cli("cc-flow", "export", project_id, a_flow_id, "--version", "draft", "-o", "json")
    assert r.code == 0, r.err
    d = json.loads(r.out)
    assert "nodes" in d and "edges" in d, sorted(d)


def test_global_vars_returns_metadata(project_id):
    # Map row 18: `global-vars` -> `cc-flow-store list-global-variables P`. wxcc
    # unwrapped the list; wxcli prints the whole {isSearchEnabled, variables} object
    # (measured 2026-10-19), so `--fields variables` gives wxcc's shape.
    r = run_cli("cc-flow-store", "list-global-variables", project_id,
                "--fields", "variables", "-o", "json")
    assert r.code == 0, r.err
    d = json.loads(r.out)
    assert isinstance(d, list) and d and {"name", "type"} <= set(d[0]), d[:1]


def test_version_draft_renders(a_flow_id, project_id):
    # Map row 35: `version-draft F` -> `cc-flow-versions show-draft P F`.
    r = run_cli("cc-flow-versions", "show-draft", project_id, a_flow_id, "-o", "json")
    assert r.code == 0, r.err
    d = json.loads(r.out)
    assert d.get("flowId") == a_flow_id and "id" in d, sorted(d)


def test_version_latest_and_by_id(pub_version, project_id):
    fid, vid = pub_version
    # Map rows 34 and 33.
    latest = run_cli("cc-flow-versions", "show-latest", project_id, fid, "-o", "json")
    assert latest.code == 0, latest.err
    assert "id" in json.loads(latest.out)
    byid = run_cli("cc-flow-versions", "show", project_id, fid, vid, "-o", "json")
    assert byid.code == 0, byid.err
    assert json.loads(byid.out).get("id") == vid


def test_validate_id_wires_up(a_flow_id, project_id):
    # Map row 25: `validate-id F` -> `cc-flow list-validate P F`. On some drafts the
    # server 500s ("Oops... Something broke...") — tolerated. wxcc's FLOW-only warn
    # banner is not carried. A CLI crash (Traceback) is never tolerated.
    r = run_cli("cc-flow", "list-validate", project_id, a_flow_id, "--version-id", "draft",
                "-o", "json")
    assert "Traceback" not in r.combined, r.combined[:300]
    if r.code == 0:
        json.loads(r.out)
    else:
        assert "500" in r.combined, f"exit {r.code} without a server 500: {r.combined[:300]}"


def test_all_versions_latest_answers_or_500s(project_id):
    # Map row 37: `all-versions-latest` -> `cc-flow-versions list-all-latest P`. The
    # server 500s org-wide on this project (host map § Expected service errors);
    # wxcc printed a warn banner first, wxcli does not.
    r = run_cli("cc-flow-versions", "list-all-latest", project_id, "-o", "json")
    assert "Traceback" not in r.combined, r.combined[:300]
    if r.code == 0:
        json.loads(r.out)
    else:
        assert "500" in r.combined, f"exit {r.code} without a server 500: {r.combined[:300]}"


def test_events_lists_event_specifications(project_id):
    # Map rows 28/H6: `events` -> `cc-flow list-event-specifications P --fields
    # specifications`. wxcc's test asserted the fallback text pointing to eventFlows;
    # the endpoint now answers (host map `events` row: 20 specifications), so the
    # fallback is not carried and the test asserts the list instead.
    r = run_cli("cc-flow", "list-event-specifications", project_id,
                "--fields", "specifications", "-o", "json")
    assert r.code == 0, r.err
    specs = json.loads(r.out)
    assert isinstance(specs, list) and specs, specs
    assert all("eventSpecificationName" in s for s in specs), specs[:1]


# ===================================================== Task 1a2: api namespace
def _resolve_argv(entry, *, project_id, flow_id, version_id, template_id):
    """wxcli argv (list) for a read-only wxcc operation, or (None, skip_reason)."""
    key = (entry["group"], entry["command"])
    if key == ("tracing", "interactions"):
        return None, ("runnable and unmeasured through wxcli: `cc-flow-tracing list-interactions P F` "
                      "needs no interaction ID (host map getInteractions measured ROUTED 200); "
                      "lift this skip on a later live run")
    if key in API_SKIP_INTERACTION:
        return None, "needs real interaction data (no live call routed to a flow)"
    if key == ("connectors", "get"):
        return None, "connector-controller 404s on system project; no valid id"
    values = {"P": project_id, "F": flow_id, "V": version_id, "T": template_id}
    argv = []
    for a in WXCLI_READ[key]:
        if a in values:
            if values[a] is None:
                return None, f"no value available for {a}"
            argv.append(values[a])
        else:
            argv.append(a)
    return argv + ["-o", "json"], None


@pytest.mark.parametrize("entry", READ_ONLY, ids=lambda e: f"{e['group']}.{e['command']}")
def test_api_readonly_returns_or_parses(entry, a_flow_id, project_id, request):
    rp = entry.get("required_params") or []
    key = (entry["group"], entry["command"])
    # Commands that read a PUBLISHED version must use a known-published flow, not
    # flows[0] (whose publish state is non-deterministic). `versions latest`
    # returns the latest published version and 404s on a never-published flow;
    # `versions list` returns [] there — route both through pub_version.
    if "<versionId>" in rp:  # a versionId must pair with ITS OWN parent flow
        flow_id, version_id = request.getfixturevalue("pub_version")
    elif key in {("versions", "latest"), ("versions", "list")}:
        flow_id, version_id = request.getfixturevalue("pub_version")[0], None
    else:
        flow_id, version_id = a_flow_id, None
    template_id = (
        request.getfixturevalue("a_template_id") if key == ("templates", "get") else None
    )
    argv, skip = _resolve_argv(
        entry, project_id=project_id, flow_id=flow_id, version_id=version_id,
        template_id=template_id,
    )
    if skip:
        pytest.skip(skip)
    r = run_cli(*argv)
    assert "Traceback" not in r.combined, f"{argv}: {r.combined[:300]}"
    if key in API_TOLERATE_404:
        assert r.code != 0 and "404" in r.combined, (
            f"expected the documented system-project 404: {r.combined[:200]}"
        )
        return
    if key in API_WARN and r.code != 0:
        assert "500" in r.combined, f"{argv} -> exit {r.code}: {r.combined[:300]}"
        return  # may 500 (tolerated)
    assert r.code == 0, f"{argv} -> exit {r.code}: {r.combined[:300]}"
    if r.out.strip()[:1] in "{[":
        json.loads(r.out)  # emitted JSON parses


# ================================================ Task 1b: doc-consistency (live)
def _flowir_registry_ports():
    """Map activityName -> set of backtick-quoted port tokens from flowir §8."""
    text = FLOWIR.read_text()
    seg = text.split("## 8. Complete Activity Registry", 1)[1].split("## 9.", 1)[0]
    out = {}
    for line in seg.splitlines():
        cells = [c.strip() for c in line.split("|")]
        # rows: | `name` | Display | `group` | ports... |  -> cells[1]=name, cells[4]=ports
        if len(cells) >= 6 and cells[1].startswith("`") and cells[1].endswith("`"):
            out[cells[1].strip("`")] = set(re.findall(r"`([^`]+)`", cells[4]))
    return out


# D15 (spec): wxcc counted 52 on 2026-07-12; Plan 2 Task 3 measured 54 FLOW
# activities on 2026-10-19 (docs/merge/flow-store-host-map.md § Data for Plan 3).
# flowir §8 says 54 since Plan 3 Task 4 (re-measured 54 live on 2026-10-19).
REGISTRY_COUNT, REGISTRY_COUNT_DATE = 54, "2026-10-19"


def test_registry_count_is_54(activities):
    assert len(activities) == REGISTRY_COUNT, (
        f"live registry has {len(activities)} activities; Task 3 measured "
        f"{REGISTRY_COUNT} on {REGISTRY_COUNT_DATE}. If Cisco changed it, update this "
        "test, flowir.md §8 and the CLAUDE.md count, and flag it loudly."
    )


def test_every_registry_activity_has_a_doc_home(activity_names):
    documented = set(_flowir_registry_ports())
    missing = [a for a in activity_names if a not in documented]
    assert not missing, f"registry activities absent from the flowir §8 table: {missing}"


# Ports the API leaves IMPLICIT (out/default), or that are dynamic per config —
# flowir §8 documents them, so they are exempt from the live-vs-doc check.
_DYNAMIC_PORT_ACTIVITIES = {"case-statement", "percent-allocation", "ivr-menu"}


@pytest.mark.portaudit
def test_flowir_port_table_documents_live_ports(activities):
    """Every EXPLICIT live output port appears in flowir §8. Implicit success
    ports (out/default) are documented but absent from the API's outputPorts
    array, so the reverse is intentionally NOT asserted."""
    doc = _flowir_registry_ports()
    problems = []
    for e in activities:
        name = e["activityName"]
        if name in _DYNAMIC_PORT_ACTIVITIES or name not in doc:
            continue
        live = {p["condition"] for p in (e.get("outputPorts") or [])}
        undocumented = live - doc[name]
        if undocumented:
            problems.append(
                f"{name}: live ports {sorted(undocumented)} not in flowir §8 {sorted(doc[name])}"
            )
    assert not problems, "\n".join(problems)
