"""Drift gate check 35: a documented command's request surface no doc section names.

The hole it closes (2026-11-02): Cisco added CUSTOM_MESSAGING and a required
`messagingPolicy` to `channel create` by the 2026-10-13 sync; the weekly routine
regenerated and released, and contact-center-routing.md § 15 kept listing four
channel types. Checks 19 and 20 both passed: one sees spec deltas, the other whole
groups, and neither asks whether a documented command's new field reached its doc.

Every case is paired so the check can FAIL it: a gap fires, the same gap in the
baseline does not, and a doc mention clears it.
"""

import json
import types
from pathlib import Path

from tools import doc_gap, drift_check

SPEC = {"components": {"schemas": {
    "Kind": {"type": "string", "enum": ["ALPHA", "BETA"]},
    "Dto": {"type": "object", "properties": {
        "name": {"type": "string"},
        "kind": {"$ref": "#/components/schemas/Kind"},
        "createdTime": {"type": "integer"},
        "logoUrl": {"type": "string", "description": "Public URL (read-only, set by server)."},
        "secret": {"type": "string", "readOnly": True},
    }},
    "Bulk": {"type": "object", "properties": {"items": {"type": "array", "items": {
        "type": "object", "properties": {
            "itemIdentifier": {"type": "integer"},
            "requestAction": {"type": "string"},
            "item": {"$ref": "#/components/schemas/Dto"}}}}}},
}}}


def _sop(op, path="/thing", method="POST"):
    return drift_check.SpecOp("webex-probe.json", path, method, op, SPEC)


def _body(ref):
    return {"requestBody": {"content": {"application/json": {"schema": {"$ref": ref}}}}}


def test_request_surface_reads_body_query_and_enums():
    op = _body("#/components/schemas/Dto")
    op["parameters"] = [
        {"in": "query", "name": "mode", "schema": {"type": "string", "enum": ["FAST", "SLOW"]}},
        {"in": "query", "name": "orgId", "schema": {"type": "string"}},
        {"in": "query", "name": "page", "schema": {"type": "integer"}},
        {"in": "path", "name": "id", "schema": {"type": "string"}},
    ]
    got = doc_gap.request_surface(drift_check, _sop(op))
    assert got == {"body:name", "body:kind", "enum:kind=ALPHA", "enum:kind=BETA",
                   "query:mode", "enum:mode=FAST", "enum:mode=SLOW"}
    # server-owned: readOnly, read-only prose, and createdTime are never asked of a doc


def test_bulk_wrapper_is_judged_by_its_item_dto():
    """`channel create` is POST …/channel/bulk; the DTO sits at items[].item."""
    got = doc_gap.request_surface(drift_check, _sop(_body("#/components/schemas/Bulk")))
    assert "body:items" not in got and "body:itemIdentifier" not in got
    assert {"body:name", "enum:kind=ALPHA"} <= got


def test_covered_accepts_the_name_or_its_flag_form():
    assert doc_gap._covered("body:messagingPolicy", "send `--messaging-policy`")
    assert doc_gap._covered("body:messagingPolicy", '{"messagingPolicy": {}}')
    assert not doc_gap._covered("body:messagingPolicy", "a messaging policy")
    assert doc_gap._covered("enum:channelType=CUSTOM_MESSAGING", "CUSTOM_MESSAGING")
    assert not doc_gap._covered("enum:channelType=CUSTOM_MESSAGING", "custom messaging")


def _fake_dc(tmp_path: Path, doc: str):
    ref = tmp_path / "reference"
    ref.mkdir(parents=True)
    (ref / "probe.md").write_text(doc)
    block = drift_check.CommandBlock("probe_mod", "probe-mod", "create", "POST", "/thing", "")
    ns = types.SimpleNamespace(**{k: getattr(drift_check, k) for k in dir(drift_check)
                                  if not k.startswith("__")})
    ns.iter_command_blocks = lambda: [block]
    ns.spec_ops_by_key = lambda: {("POST", "/thing"): [_sop(_body("#/components/schemas/Dto"))]}
    ns.parse_registrations = lambda: {"probe-mod": "probe_mod"}
    ns.REFERENCE_DIR = ref
    return ns, ref


DOC_ALL = ("# Probe\n\n## 1. Probe\n\n```bash\nwxcli probe-mod create --json-body "
           "'{\"name\":\"x\",\"kind\":\"ALPHA\"}'\n```\nKinds: ALPHA, BETA.\n")


def test_a_gap_fires_and_a_doc_mention_clears_it(tmp_path):
    dc, ref = _fake_dc(tmp_path, DOC_ALL.replace("BETA", "(more)"))
    findings, stale = doc_gap.check_doc_gaps(dc, baseline=set(), reference_dir=ref)
    assert [f["key"] for f in findings] == ["POST /thing enum:kind=BETA"]
    assert findings[0]["cmd"] == "probe-mod create"
    dc, ref = _fake_dc(tmp_path / "b", DOC_ALL)
    findings, stale = doc_gap.check_doc_gaps(dc, baseline=set(), reference_dir=ref)
    assert findings == [] and stale == []


def test_the_baseline_suppresses_old_debt_and_reports_closed_entries(tmp_path):
    dc, ref = _fake_dc(tmp_path, DOC_ALL.replace("BETA", "(more)"))
    findings, stale = doc_gap.check_doc_gaps(
        dc, baseline={"POST /thing enum:kind=BETA", "POST /thing body:gone"}, reference_dir=ref)
    assert findings == []
    assert stale == ["POST /thing body:gone"]   # advisory, never gated


def test_a_mention_in_another_section_does_not_count(tmp_path):
    """CUSTOM_MESSAGING listed under Assets must not cover `channel create`."""
    doc = DOC_ALL.replace("BETA", "(more)") + "\n## 2. Elsewhere\n\nBETA is listed here.\n"
    dc, ref = _fake_dc(tmp_path, doc)
    findings, _ = doc_gap.check_doc_gaps(dc, baseline=set(), reference_dir=ref)
    assert [f["key"] for f in findings] == ["POST /thing enum:kind=BETA"]


def test_refresh_is_shrink_only(tmp_path, monkeypatch):
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps({"gaps": ["A", "B"]}))
    monkeypatch.setattr(doc_gap, "current_gaps",
                        lambda *a, **k: ({"A": {"cmd": "x", "docs": set()},
                                          "C": {"cmd": "y", "docs": set()}}, 1, 0))
    assert doc_gap.refresh_baseline(path=path) == 1          # C would be added: refused
    assert json.loads(path.read_text())["gaps"] == ["A", "B"]
    monkeypatch.setattr(doc_gap, "current_gaps",
                        lambda *a, **k: ({"A": {"cmd": "x", "docs": set()}}, 1, 0))
    assert doc_gap.refresh_baseline(path=path) == 0          # B closed: dropped
    assert json.loads(path.read_text())["gaps"] == ["A"]


def test_live_tree_is_not_blind():
    """A loose floor: the reader must still see most documented commands."""
    gaps, examined, skipped = doc_gap.current_gaps()
    assert examined > 1000, (examined, skipped)
    assert doc_gap.BASELINE.is_file()
