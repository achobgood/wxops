"""Live Flow Store host probe (Webex Ops merge, Plan 2 Task 3).

Answers one question per GET operation in the Flow Store spec: which base URL
actually routes it?  Four bases are tried for every GET --

    FS    https://flow-store.produs1.ciscoccservice.com/flow-store
    GW    the wxcli Contact Center gateway (cc_region in ~/.wxcli/config.json)
    GWFS  GW + "/flow-store"

-- plus one probe each of ADR-11's two hosts (intgus1, us1).

The ``get`` mode (Plan 3 Task 1) is one GET of one URL, for Plan 3's live probes:
the URL's host must be on ``GET_HOSTS`` and the request goes through
``GetOnlyClient``; it writes the status, the TrackingID header and the body to
``--out`` and never prints the token.

The ``hosts`` mode is GET-only by construction: every request goes through
``GetOnlyClient``, which raises before sending anything that is not a GET.
Task 5 added two POST modes, both through ``PostProbeClient``, whose URL comes
from the fixed ``POST_OPS`` list: ``import-ui`` (one v1 multipart import,
refused unless the flow name in the file starts with ``CLITest_WebexOps_``) and
``write-probes`` (exactly the three POSTs that persist nothing).  Imports nothing from wxcli
(the safety hook denies Python imports of wxcli); the token is read in wxcli's
order and never printed.

Usage:
    python tools/flow_store_host_probe.py selftest
    python tools/flow_store_host_probe.py get URL --out FILE
    python tools/flow_store_host_probe.py hosts --spec specs/webex-cc-flow-store.json --out hosts.json
    python tools/flow_store_host_probe.py render --in hosts.json
    python tools/flow_store_host_probe.py dns --config src/wxcli/config.py
    python tools/flow_store_host_probe.py import-ui --file ui.json --base GWFS --out import.json
    python tools/flow_store_host_probe.py write-probes --base GWFS --flow-name CLITest_WebexOps_x \\
        --current-flow-id A --hand-off-flow-id B --out probes.json
"""
from __future__ import annotations

import argparse
import ast
import base64
import json
import os
import re
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

FS = "https://flow-store.produs1.ciscoccservice.com/flow-store"
ADR11_HOSTS = {
    "INTGUS1": "https://flow-store.intgus1.ciscoccservice.com",
    "US1": "https://flow-store.us1.ciscoccservice.com",
}
# Copied from src/wxcli/config.py CC_REGIONS (not imported: see module docstring).
CC_REGIONS = {
    "us1": "https://api.wxcc-us1.cisco.com",
    "eu1": "https://api.wxcc-eu1.cisco.com",
    "eu2": "https://api.wxcc-eu2.cisco.com",
    "anz1": "https://api.wxcc-anz1.cisco.com",
    "ca1": "https://api.wxcc-ca1.cisco.com",
    "jp1": "https://api.wxcc-jp1.cisco.com",
    "sg1": "https://api.wxcc-sg1.cisco.com",
}
WXCLI_CONFIG = Path.home() / ".wxcli" / "config.json"
# Frozen copy of wxcc's generated `_manifest.json`, kept when `wxcc/` was removed (Plan 6).
MANIFEST = Path("tests/wxcc/fixtures/wxcc_flow_manifest.json")
DUMMY_ID = "0123456789abcdef01234567"  # 24-hex, never a real object
OOPS = "Oops... Something broke"

# Fate per manifest row, from the plan's Command fate table.
FATE_A = {3, 4, 5, 12, 14, 15, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31}
FATE_C = {8, 17}

# Classes
ROUTED, ERRORED, UNROUTED, AUTH = "ROUTED", "ERRORED", "UNROUTED", "AUTH"


class NotAGet(RuntimeError):
    pass


class HostNotAllowed(RuntimeError):
    pass


# Hosts the ``get`` mode may call: the Contact Center gateway (us1) and the
# JDS read host.  Exact hostnames, https only.
GET_HOSTS = ("api.wxcc-us1.cisco.com", "api-jds.prod-useast1.ciscowxdap.com")


class GetOnlyClient:
    """The only door to the network.  Anything but GET raises before sending."""

    def __init__(self, token: str, timeout: float = 30.0):
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=timeout,
        )

    def request(self, method: str, url: str, **kw) -> httpx.Response:
        if method.upper() != "GET":
            raise NotAGet(f"refusing {method} {url}: this probe is GET-only")
        return self._client.request("GET", url, **kw)

    def get(self, url: str, **kw) -> httpx.Response:
        return self.request("GET", url, **kw)


def check_get_url(url: str) -> str:
    """Raise HostNotAllowed unless url is https on an exact GET_HOSTS host.
    Runs before a client is built, so a refused URL sends nothing."""
    u = urlparse(url)
    if u.scheme != "https" or u.hostname not in GET_HOSTS or u.username or u.password:
        raise HostNotAllowed(f"refusing GET {u.scheme}://{u.hostname}: host is not one of {list(GET_HOSTS)}")
    return url


def get_url(client: GetOnlyClient, url: str) -> httpx.Response:
    """One GET of one allowlisted URL.  Redirects are not followed."""
    return client.get(check_get_url(url))


NAME_PREFIX = "CLITest_WebexOps_"  # every Task 5 test flow carries it (spec §10.5)


class NotAllowed(RuntimeError):
    pass


# Task 5's only POSTs, as path templates.  "import-ui" persists a flow, so it is
# gated on the flow name inside the file; the other three are the write probes,
# which persist nothing (advisor review S1).  Rows from the plan's fate table.
POST_OPS = {
    "import-ui": "/{orgId}/project/{projectId}/flows:import",                 # row 8
    "unique-name": "/{orgId}/project/{projectId}/flows:unique-name",          # row 7
    "expression-test": "/expressionTest",                                     # row 57
    "variable-mapping": "/{orgId}/project/{projectId}/flows:variable-mapping",  # row 6
}
WRITE_PROBES = ("unique-name", "expression-test", "variable-mapping")


class PostProbeClient:
    """The only door for Task 5's POSTs.  The URL is built here from POST_OPS,
    so an operation outside that list raises before anything is sent."""

    def __init__(self, token: str, timeout: float = 60.0, http=None):
        self._http = http or httpx.Client(
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=timeout,
        )

    def send(self, op: str, base: str, v: dict, **kw) -> httpx.Response:
        if op not in POST_OPS:
            raise NotAllowed(f"refusing POST {op!r}: not one of {sorted(POST_OPS)}")
        path = re.sub(r"\{(\w+)\}", lambda m: str(v[m.group(1)]), POST_OPS[op])
        return self._http.request("POST", base + path, **kw)


def import_ui(client: PostProbeClient, base: str, v: dict, file: Path) -> httpx.Response:
    """One multipart POST of a v1 (UI-shape) flow file, as wxcc-flow import-ui sends it."""
    content = Path(file).read_bytes()
    name = json.loads(content).get("name") or ""
    if not name.startswith(NAME_PREFIX):
        raise NotAllowed(f"refusing import-ui: flow name {name!r} does not start with {NAME_PREFIX}")
    return client.send("import-ui", base, v,
                       files={"file": (Path(file).name, content, "application/json")})


def write_probe_requests(v: dict) -> list[tuple[str, dict]]:
    """Exactly the three non-persisting POSTs of Task 5 Step 2b, in order."""
    if not str(v.get("flowName", "")).startswith(NAME_PREFIX):
        raise NotAllowed(f"refusing unique-name: {v.get('flowName')!r} does not start with {NAME_PREFIX}")
    return [
        ("unique-name", {"params": {"flowName": v["flowName"]}}),
        ("expression-test", {"json": {"expr": "{{ foo }}", "variables": {"foo": "bar"}}}),
        ("variable-mapping", {"params": {"orgId": v["orgId"], "currentFlowId": v["currentFlowId"],
                                         "handOffFlowId": v["handOffFlowId"]}}),
    ]


def _json_body(resp: httpx.Response):
    try:
        return resp.json()
    except Exception:
        return None


def tracking_id(resp: httpx.Response) -> str:
    """The service's own trackingId if its body carries one, else the header's."""
    body = _json_body(resp)
    if isinstance(body, dict):
        for k in ("trackingId", "trackingID", "TrackingID"):
            if body.get(k):
                return str(body[k])
    return resp.headers.get("TrackingID") or resp.headers.get("trackingid") or ""


def classify(resp: httpx.Response) -> str:
    code = resp.status_code
    if 200 <= code < 300:
        return ROUTED
    if code in (401, 403):
        return AUTH
    text = resp.text or ""
    tid = tracking_id(resp)
    if not text.strip():
        return UNROUTED
    if tid.startswith("GTWY_"):
        return UNROUTED
    body = _json_body(resp)
    if 500 <= code < 600:
        return ERRORED if (body is not None or OOPS in text) else UNROUTED
    if 400 <= code < 500:
        return ROUTED if body is not None else UNROUTED
    return UNROUTED


def selftest() -> int:
    req = httpx.Request("GET", "https://example.invalid/x")
    cases = [
        ("JSON 404", httpx.Response(404, json={"error": {"key": 404, "message": ["Flow not found"]},
                                               "trackingId": "abc-123"}, request=req), ROUTED),
        ("empty 404 + GTWY_", httpx.Response(404, content=b"", headers={"TrackingID": "GTWY_1234"},
                                             request=req), UNROUTED),
        ("200", httpx.Response(200, json={"ok": True}, request=req), ROUTED),
        ("500 Oops", httpx.Response(500, content=b"Oops... Something broke...", request=req), ERRORED),
        ("403", httpx.Response(403, json={"message": "no"}, request=req), AUTH),
    ]
    bad = 0
    for name, resp, want in cases:
        got = classify(resp)
        ok = got == want
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:20s} -> {got} (want {want})")
    try:
        GetOnlyClient("x").request("POST", "https://example.invalid/x")
        print("FAIL  POST was not refused")
        bad += 1
    except NotAGet:
        print("PASS  POST refused before sending")
    guards = _selftest_post_guards()
    bad += guards
    bad += _selftest_get_guards()
    total = 5 + 1 + 6 + 5
    print(f"{total - bad}/{total} passed")
    return 1 if bad else 0


class _RecordingHttp:
    """Stands in for httpx.Client in the selftest: records, never sends."""

    def __init__(self):
        self.calls = []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        return httpx.Response(200, json={"ok": True}, request=httpx.Request(method, url))


def _selftest_post_guards() -> int:
    """Task 5 guards: the import-ui name check and the write-probe allow-list."""
    import tempfile

    bad = 0

    def check(name, ok):
        nonlocal bad
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    vars_ = {"orgId": "org", "projectId": "proj"}
    with tempfile.TemporaryDirectory() as d:
        prod = Path(d) / "prod.json"
        prod.write_text(json.dumps({"name": "Prod_Main_IVR", "process": {}}))
        test = Path(d) / "test.json"
        test.write_text(json.dumps({"name": NAME_PREFIX + "P2_ui_1", "process": {}}))

        c = PostProbeClient("x", http=_RecordingHttp())
        try:
            import_ui(c, "https://example.invalid/fs", vars_, prod)
            check("import-ui refuses a non-test flow name", False)
        except NotAllowed:
            check("import-ui refuses a non-test flow name", not c._http.calls)

        c = PostProbeClient("x", http=_RecordingHttp())
        import_ui(c, "https://example.invalid/fs", vars_, test)
        calls = c._http.calls
        check("import-ui sends one multipart POST to flows:import",
              len(calls) == 1 and calls[0][0] == "POST"
              and calls[0][1] == "https://example.invalid/fs/org/project/proj/flows:import"
              and "file" in calls[0][2].get("files", {}))

    c = PostProbeClient("x", http=_RecordingHttp())
    try:
        c.send("copy", "https://example.invalid/fs", vars_)
        check("an operation outside the allow-list is refused", False)
    except NotAllowed:
        check("an operation outside the allow-list is refused", not c._http.calls)
    check("write-probes allow-list is exactly the three non-persisting POSTs",
          sorted(WRITE_PROBES) == ["expression-test", "unique-name", "variable-mapping"])
    try:
        write_probe_requests({"orgId": "o", "projectId": "p", "flowName": "Prod_X",
                              "currentFlowId": "a", "handOffFlowId": "b"})
        check("write-probes refuse a unique-name check on a non-test name", False)
    except NotAllowed:
        check("write-probes refuse a unique-name check on a non-test name", True)
    return bad


def _selftest_get_guards() -> int:
    """Plan 3 Task 1: the ``get`` mode refuses before any request is sent."""
    bad = 0

    def check(name, ok):
        nonlocal bad
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    def client():
        c = GetOnlyClient("x")
        c._client = _RecordingHttp()
        return c

    c = client()
    try:
        get_url(c, "https://example.invalid/x")
        check("get refuses a host off the allowlist", False)
    except HostNotAllowed:
        check("get refuses a host off the allowlist before any request", not c._client.calls)

    c = client()
    try:
        get_url(c, "https://api.wxcc-us1.cisco.com.evil.invalid/x")
        check("get refuses a lookalike host", False)
    except HostNotAllowed:
        check("get refuses a lookalike host before any request", not c._client.calls)

    c = client()
    try:
        get_url(c, "http://api.wxcc-us1.cisco.com/x")
        check("get refuses http", False)
    except HostNotAllowed:
        check("get refuses http before any request", not c._client.calls)

    c = client()
    try:
        c.request("POST", "https://api.wxcc-us1.cisco.com/x")
        check("get path refuses a non-GET method", False)
    except NotAGet:
        check("get path refuses a non-GET method before any request", not c._client.calls)

    c = client()
    get_url(c, "https://api.wxcc-us1.cisco.com/x")
    check("get sends exactly one GET to an allowlisted host",
          len(c._client.calls) == 1 and c._client.calls[0][0] == "GET")
    return bad


def resolve_token() -> str:
    for var in ("WEBEX_ACCESS_TOKEN", "WEBEX_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    cfg = json.loads(WXCLI_CONFIG.read_text())
    tok = cfg.get("profiles", {}).get("default", {}).get("token")
    if not tok:
        sys.exit("no token: run `wxcli configure`")
    return tok


def bare_org(raw: str) -> str:
    if re.fullmatch(r"[0-9a-f-]{36}", raw):
        return raw
    pad = "=" * (-len(raw) % 4)
    return base64.b64decode(raw + pad).decode().rsplit("/", 1)[-1]


def resolve_org(client: GetOnlyClient) -> str:
    cfg = json.loads(WXCLI_CONFIG.read_text())
    raw = cfg.get("profiles", {}).get("default", {}).get("org_id")
    if not raw:
        raw = client.get("https://webexapis.com/v1/people/me").json()["orgId"]
    return bare_org(raw)


def gateway_base() -> str:
    cfg = json.loads(WXCLI_CONFIG.read_text())
    region = cfg.get("profiles", {}).get("default", {}).get("cc_region", "us1")
    return CC_REGIONS.get(region, CC_REGIONS["us1"])


def _items(body):
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for k in ("data", "items", "content", "flows", "versions", "templates", "connectors",
                  "specifications"):
            if isinstance(body.get(k), list):
                return body[k]
    return []


def discover_vars(client: GetOnlyClient, org: str) -> dict:
    """Fill path variables from the first real objects, all read from FS."""
    v = {"orgId": org, "activityName": "queue-contact", "inputName": "channelType",
         "interactionId": DUMMY_ID, "connectorId": DUMMY_ID, "id": DUMMY_ID,
         "versionId": DUMMY_ID, "flowId": DUMMY_ID}
    prefs = client.get(f"{FS}/{org}/userPreferences").json()
    v["projectId"] = prefs["projectId"]
    proj = f"{FS}/{org}/project/{v['projectId']}"
    flows = _items(client.get(f"{proj}/flows", params={"size": "50"}).json())
    if flows:
        v["flowId"] = flows[0]["id"]
    for f in flows:  # first flow that has a published version
        vers = _items(client.get(f"{proj}/flows/{f['id']}/versions").json())
        if vers:
            v["flowId"], v["versionId"] = f["id"], vers[0]["id"]
            v["flowName"] = f.get("name", "")
            break
    tpls = _items(client.get(f"{FS}/templates").json())
    if tpls:
        v["id"] = tpls[0].get("id", DUMMY_ID)
    conns = _items(client.get(f"{proj}/connector").json())
    if conns:
        v["connectorId"] = conns[0].get("id", DUMMY_ID)
    return v


def spec_gets(spec_path: Path) -> list[dict]:
    spec = json.loads(spec_path.read_text())
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    row_of = {}
    for i, m in enumerate(manifest, 1):
        row_of.setdefault(m["operationId"], []).append(i)
    out = []
    for path, ops in spec["paths"].items():
        op = ops.get("get")
        if not op:
            continue
        rows = row_of.get(op.get("operationId"), [])
        fates = sorted({"a" if r in FATE_A else "c" if r in FATE_C else "b" for r in rows})
        out.append({"path": path, "operationId": op.get("operationId"), "rows": rows,
                    "fate": "/".join(fates) or "-"})
    return out


# A GET whose name says it may create: never point it at a real flow.
DUMMY_FLOW_OPS = {"getOrCreateDraft"}


def fill(path: str, v: dict, op_id: str) -> str:
    vv = dict(v)
    if op_id in DUMMY_FLOW_OPS:
        vv["flowId"] = DUMMY_ID
    return re.sub(r"\{(\w+)\}", lambda m: str(vv.get(m.group(1), DUMMY_ID)), path)


def probe(client: GetOnlyClient, url: str) -> dict:
    try:
        r = client.get(url)
    except httpx.ConnectError as e:  # DNS failure / refused
        return {"status": None, "class": UNROUTED, "trackingId": "", "detail": f"connect: {e}"[:160]}
    except httpx.HTTPError as e:
        return {"status": None, "class": UNROUTED, "trackingId": "", "detail": f"{type(e).__name__}: {e}"[:160]}
    text = (r.text or "").replace("\n", " ")
    return {"status": r.status_code, "class": classify(r), "trackingId": tracking_id(r),
            "server": r.headers.get("server", ""), "detail": text[:160]}


def cmd_hosts(args) -> int:
    client = GetOnlyClient(resolve_token())
    org = resolve_org(client)
    gw = gateway_base()
    bases = {"FS": FS, "GW": gw, "GWFS": gw + "/flow-store"}
    v = discover_vars(client, org)
    rows = []
    for op in spec_gets(Path(args.spec)):
        rel = fill(op["path"], v, op["operationId"])
        cells = {name: probe(client, base + rel) for name, base in bases.items()}
        rows.append({**op, "probed": rel.replace(org, "{org}"), "cells": cells})
        print(f"{op['operationId']:40s} " + " ".join(f"{k}={c['status']}/{c['class']}" for k, c in cells.items()),
              file=sys.stderr)
    adr11 = {name: probe(client, f"{host}/{org}/userPreferences") for name, host in ADR11_HOSTS.items()}
    out = {"org": org, "bases": bases, "vars": {k: (val if k != "orgId" else "{org}") for k, val in v.items()},
           "rows": rows, "adr11": adr11}
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {args.out}: {len(rows)} GET operations", file=sys.stderr)
    return 0


def decide(data: dict) -> dict:
    ok = (ROUTED, ERRORED)
    b_rows = [r for r in data["rows"] if "b" in r["fate"].split("/")]
    fs_bad = [r["operationId"] for r in b_rows if r["cells"]["FS"]["class"] not in ok]
    gwfs_bad = [r["operationId"] for r in b_rows if r["cells"]["GWFS"]["class"] not in ok]
    tpl = next((r for r in data["rows"] if r["path"] == "/templates"), None)
    tpl_gw = tpl["cells"]["GW"]["class"] if tpl else "missing"
    return {
        "b_fate_gets": len(b_rows),
        "fs_not_routed": fs_bad,
        "FLOW_STORE_DEFAULT_URL": FS if not fs_bad else "STOP, ask Adam",
        "GWFS_CANDIDATE": "yes" if not gwfs_bad else "no",
        "gwfs_not_routed": gwfs_bad,
        "TEMPLATES_SOURCE": "webex-contact-center.json" if tpl_gw == ROUTED else "webex-cc-flow-store.json",
        "templates_on_GW": tpl_gw,
    }


def cmd_render(args) -> int:
    data = json.loads(Path(args.inp).read_text())
    print("| Operation | Path | Fate (rows) | FS | GW | GWFS |")
    print("|---|---|---|---|---|---|")
    for r in data["rows"]:
        cells = " | ".join(f"{c['class']} {c['status']}" for c in (r["cells"][k] for k in ("FS", "GW", "GWFS")))
        rows = ",".join(map(str, r["rows"])) or "-"
        print(f"| `{r['operationId']}` | `{r['path']}` | {r['fate']} ({rows}) | {cells} |")
    print()
    for name, c in data["adr11"].items():
        print(f"- ADR-11 host {name}: {c['class']} {c['status']} — {c['detail'][:100]}")
    print()
    print(json.dumps(decide(data), indent=2))
    return 0


def cmd_dns(args) -> int:
    tree = ast.parse(Path(args.config).read_text())
    urls = {}
    for node in ast.walk(tree):
        # wxcc's config.py named its region table API_BASE_URLS; wxcli's is CC_REGIONS.
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") in ("API_BASE_URLS", "CC_REGIONS")
                                                for t in node.targets):
            urls = ast.literal_eval(node.value)
    for key, url in urls.items():
        host = urlparse(url).hostname
        try:
            addrs = sorted({a[4][0] for a in socket.getaddrinfo(host, 443)})
            print(f"{key}\t{host}\tRESOLVES\t{addrs[0]}")
        except socket.gaierror as e:
            print(f"{key}\t{host}\tNXDOMAIN\t{e}")
    return 0


def _load(path: Path):
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"__unparsed__": text[:300]}


def _key_of(item):
    if isinstance(item, dict):
        for k in ("id", "activityName", "name", "eventSpecificationName", "value"):
            if k in item:
                return f"{k}={item[k]}"
    return json.dumps(item, sort_keys=True)


def _canonical(x):
    if isinstance(x, dict):
        return {k: _canonical(v) for k, v in x.items()}
    if isinstance(x, list):
        return sorted((_canonical(v) for v in x), key=lambda v: json.dumps(v, sort_keys=True))
    return x


def compare(a, b) -> tuple[str, str]:
    """EQUAL/DIFFERENT plus one evidence line.

    Identical JSON (sorted keys) is EQUAL.  Otherwise, when either side is a
    list (or both wrap one), compare the set of item keys plus the count.
    """
    ja, jb = json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True)
    if ja == jb:
        return "EQUAL", f"identical JSON ({len(ja)} bytes, sorted keys)"
    if _canonical(a) == _canonical(b):  # e.g. validate results come back in any order
        return "EQUAL", f"same JSON once list order is ignored ({len(ja)} bytes)"
    la = a if isinstance(a, list) else _items(a)
    lb = b if isinstance(b, list) else _items(b)
    if isinstance(a, list) or isinstance(b, list) or (la and lb):
        ka, kb = sorted(map(_key_of, la)), sorted(map(_key_of, lb))
        if ka == kb:
            return "EQUAL", f"{len(ka)} items, same keys (item bodies not compared)"
        only_a, only_b = sorted(set(ka) - set(kb)), sorted(set(kb) - set(ka))
        return "DIFFERENT", f"count {len(ka)} vs {len(kb)}; only-left {only_a[:5]}; only-right {only_b[:5]}"
    if isinstance(a, dict) and isinstance(b, dict):
        diff = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
        return "DIFFERENT", f"keys differing: {diff[:10]}"
    return "DIFFERENT", f"{type(a).__name__} vs {type(b).__name__}"


def cmd_compare(args) -> int:
    d = Path(args.dir)
    for left in sorted(d.glob("*.w.json")):
        name = left.name[: -len(".w.json")]
        right = d / f"{name}.x.json"
        rcs = [(d / f"{name}.{s}.rc").read_text().strip() for s in ("w", "x")]
        verdict, ev = compare(_load(left), _load(right))
        print(f"{name}\trc={rcs[0]}/{rcs[1]}\t{verdict}\t{ev}")
    return 0


def cmd_get(args) -> int:
    check_get_url(args.url)  # refuse before the token is even read
    r = get_url(GetOnlyClient(resolve_token()), args.url)
    body = _json_body(r)
    text = json.dumps(body, indent=2) if body is not None else r.text
    Path(args.out).write_text(
        f"status: {r.status_code}\nTrackingID: {r.headers.get('TrackingID', '')}\n\n{text}\n")
    print(f"get {urlparse(args.url).hostname}{urlparse(args.url).path}: HTTP {r.status_code} "
          f"bytes={len(r.content)} -> {args.out}", file=sys.stderr)
    return 0


def _post_bases() -> dict:
    gw = gateway_base()
    return {"FS": FS, "GWFS": gw + "/flow-store"}


def _record(op: str, base_name: str, r: httpx.Response) -> dict:
    body = _json_body(r)
    return {"op": op, "base": base_name, "url": str(r.request.url).split("?")[0],
            "status": r.status_code, "class": classify(r), "trackingId": tracking_id(r),
            "gatewayTrackingId": r.headers.get("TrackingID", ""), "server": r.headers.get("server", ""),
            "bytes": len(r.content), "body": body if body is not None else r.text}


def _post_vars(token: str) -> dict:
    """org and projectId, read as in ``hosts`` (projectId from FS userPreferences)."""
    reader = GetOnlyClient(token)
    org = resolve_org(reader)
    return {"orgId": org, "projectId": reader.get(f"{FS}/{org}/userPreferences").json()["projectId"]}


def cmd_import_ui(args) -> int:
    token = resolve_token()
    v = _post_vars(token)
    base = _post_bases()[args.base]
    r = import_ui(PostProbeClient(token), base, v, Path(args.file))
    rec = _record("import-ui", args.base, r)
    Path(args.out).write_text(json.dumps(rec, indent=2))
    created = rec["body"].get("id") if isinstance(rec["body"], dict) else None
    print(f"import-ui {args.base}: HTTP {rec['status']} {rec['class']} bytes={rec['bytes']} "
          f"gatewayTrackingId={rec['gatewayTrackingId'] or '-'} created_id={created or '-'}", file=sys.stderr)
    return 0


def cmd_write_probes(args) -> int:
    token = resolve_token()
    v = {**_post_vars(token), "flowName": args.flow_name,
         "currentFlowId": args.current_flow_id, "handOffFlowId": args.hand_off_flow_id}
    base = _post_bases()[args.base]
    client = PostProbeClient(token)
    recs = []
    for op, kw in write_probe_requests(v):
        rec = _record(op, args.base, client.send(op, base, v, **kw))
        recs.append(rec)
        print(f"{op} {args.base}: HTTP {rec['status']} {rec['class']} bytes={rec['bytes']}", file=sys.stderr)
    Path(args.out).write_text(json.dumps(recs, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    h = sub.add_parser("hosts")
    h.add_argument("--spec", required=True)
    h.add_argument("--out", required=True)
    r = sub.add_parser("render")
    r.add_argument("--in", dest="inp", required=True)
    g = sub.add_parser("get", help="one GET of an allowlisted URL; writes status, TrackingID and body")
    g.add_argument("url")
    g.add_argument("--out", required=True)
    d = sub.add_parser("dns")
    d.add_argument("--config", default="src/wxcli/config.py")
    c = sub.add_parser("compare", help="compare NAME.w.json (wxcc-flow) with NAME.x.json (wxcli) in DIR")
    c.add_argument("--dir", required=True)
    iu = sub.add_parser("import-ui", help="one multipart v1 import of a CLITest_WebexOps_ flow file")
    iu.add_argument("--file", required=True)
    iu.add_argument("--base", choices=("FS", "GWFS"), required=True)
    iu.add_argument("--out", required=True)
    wp = sub.add_parser("write-probes", help="the three non-persisting POSTs of Task 5 Step 2b")
    wp.add_argument("--base", choices=("FS", "GWFS"), required=True)
    wp.add_argument("--flow-name", required=True)
    wp.add_argument("--current-flow-id", required=True)
    wp.add_argument("--hand-off-flow-id", required=True)
    wp.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    return {"selftest": lambda a: selftest(), "hosts": cmd_hosts, "render": cmd_render, "get": cmd_get, "dns": cmd_dns,
            "compare": cmd_compare, "import-ui": cmd_import_ui,
            "write-probes": cmd_write_probes}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
