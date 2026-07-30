"""Drift gate check 16: a list command whose `--all` cannot walk anything.

`--all` ships on 507 generated list commands and reaches a pager on only 264 of
them. That split is correct by design — the flag is uniform so an agent learns
one rule — but it rests entirely on the spec being right about which endpoints
page. Where a spec under-declares, `--all` is accepted, does nothing, and the
command returns page one: flag exists, flag does not work.

Every case below is written so the check can FAIL it. The paired
does-not-fire/does-fire assertions are the point: a check reading 0 because it is
looking at nothing is indistinguishable from a clean tree, and that is how the
six inert override blocks behind check 15 survived for months.

The two real findings on the tree (`archive-users list`, `org-contacts list`) are
acked in field_overrides.yaml with their evidence; `test_live_tree_is_acked`
pins that the live gate stays at 0 through them rather than through blindness.
"""

import json

import pytest

from tools import drift_check


# A generated list command in each of the three fetch branches. These are string
# templates rather than fixtures pulled off disk so a regen cannot quietly change
# what the test believes an inert command looks like.
INERT = '''
@app.command("list")
def list_things(
    output: str = typer.Option("table", "--output", "-o"),
    limit: int = typer.Option(0, "--limit"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
):
    """List things."""
    url = f"https://webexapis.com/v1/zzProbe"
    result = api.session.rest_get(url, params=params)
'''

WALKS_VIA_ALL = INERT.replace(
    "    result = api.session.rest_get(url, params=params)",
    "    if all_pages:\n"
    "        result = list(api.session.follow_pagination(url=url, params=params, item_key='items'))\n"
    "    else:\n"
    "        result = api.session.rest_get(url, params=params)")

WALKS_BY_DEFAULT = INERT.replace(
    "    result = api.session.rest_get(url, params=params)",
    "    if limit > 0 and not all_pages:\n"
    "        result = api.session.rest_get(url, params=params)\n"
    "    else:\n"
    "        items = list(api.session.follow_pagination(url=url, params=params, item_key='items'))")

NO_ALL_FLAG = INERT.replace(
    '    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),\n',
    "")


def _spec(path="/v1/zzProbe", props=None):
    props = {"items": {"type": "array"}} if props is None else props
    return {"paths": {path: {"get": {
        "tags": ["Probe"],
        "responses": {"200": {"content": {"application/json": {
            "schema": {"type": "object", "properties": props}}}}},
    }}}}


@pytest.fixture
def tree(tmp_path):
    """(commands_dir, specs_dir) writers. Returns a run() taking module+spec."""
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(module_src, spec, acks=None, module="zz_probe.py",
            spec_name="webex-probe.json"):
        (cmds / module).write_text(module_src)
        (specs / spec_name).write_text(json.dumps(spec))
        return drift_check.check_undeclared_paging(
            acks=acks or {}, commands_dir=cmds, specs_dir=specs)

    return run


# --------------------------------------------------------------- the oracle

def test_fires_on_inert_command_whose_response_declares_a_total(tree):
    findings, stale = tree(INERT, _spec(props={"total": {"type": "integer"}}))
    assert len(findings) == 1, findings
    assert findings[0]["op"] == "GET /zzProbe"
    assert findings[0]["commands"] == ["zz-probe list"]
    assert findings[0]["declares"] == ["total"]
    assert stale == []


@pytest.mark.parametrize("total", sorted(drift_check.PAGING_TOTALS))
def test_every_paging_total_spelling_fires(tree, total):
    """The four keys src/wxcli/auth.py's _body_says_more reads at runtime. If the
    static check knew fewer, it would be silent on exactly the endpoints the
    runtime warning fires for."""
    findings, _ = tree(INERT, _spec(props={total: {"type": "integer"}}))
    assert [f["declares"] for f in findings] == [[total]]


def test_silent_when_response_declares_no_total(tree):
    """The control. Without it every assertion above could pass for the wrong
    reason — a check that fires on any inert command at all."""
    findings, _ = tree(INERT, _spec())
    assert findings == []


def test_silent_when_all_reaches_a_walker(tree):
    """The rendered command is the oracle: `--all` works here, so the spec's
    under-declaration (if any) has already been compensated for."""
    findings, _ = tree(WALKS_VIA_ALL, _spec(props={"total": {"type": "integer"}}))
    assert findings == []


def test_silent_when_the_default_already_walks(tree):
    findings, _ = tree(WALKS_BY_DEFAULT,
                       _spec(props={"totalRecords": {"type": "integer"}}))
    assert findings == []


def test_silent_on_a_command_with_no_all_flag(tree):
    """show/create/update carry no `--all`; only list commands are in scope."""
    findings, _ = tree(NO_ALL_FLAG, _spec(props={"total": {"type": "integer"}}))
    assert findings == []


def test_resolves_a_ref_to_the_component_schema(tree):
    """Most Webex 200s are a $ref, not an inline schema. A check that only read
    inline properties would report 0 on nearly the whole spec surface."""
    spec = _spec()
    spec["paths"]["/v1/zzProbe"]["get"]["responses"]["200"]["content"][
        "application/json"]["schema"] = {"$ref": "#/components/schemas/Page"}
    spec["components"] = {"schemas": {"Page": {
        "type": "object",
        "properties": {"totalResults": {"type": "integer"}}}}}
    findings, _ = tree(INERT, spec)
    assert [f["declares"] for f in findings] == [["totalResults"]]


# ------------------------------------------------- the measured exclusions

def test_count_endpoints_are_excluded(tree):
    """5 of the 7 raw hits on the real tree are `.../availableMembers/count`,
    where the total IS the answer. Measured exclusion, not a defensive one."""
    module = INERT.replace("/v1/zzProbe", "/v1/zzProbe/count")
    findings, _ = tree(module, _spec(path="/v1/zzProbe/count",
                                     props={"total": {"type": "integer"}}))
    assert findings == []


def test_removing_the_count_exclusion_would_fire(tree, monkeypatch):
    """Proves the exclusion is load-bearing rather than dead code — without it
    the same input reports a finding."""
    module = INERT.replace("/v1/zzProbe", "/v1/zzProbe/count")
    real = drift_check.normalize_path
    monkeypatch.setattr(drift_check, "normalize_path",
                        lambda p: real(p) + "X" if real(p).endswith("/count")
                        else real(p))
    findings, _ = tree(module, _spec(path="/v1/zzProbe/count",
                                     props={"total": {"type": "integer"}}))
    assert len(findings) == 1


def test_totalcount_is_not_a_paging_total():
    """`totalCount` is what the /count endpoints return. Including it in
    PAGING_TOTALS is the single change that would re-admit all five."""
    assert "totalCount" not in drift_check.PAGING_TOTALS


# -------------------------------------------------------------- ack contract

def test_ack_suppresses_the_finding(tree):
    findings, stale = tree(INERT, _spec(props={"total": {"type": "integer"}}),
                           acks={"GET /zzProbe": "reviewed"})
    assert findings == []
    assert stale == []


def test_ack_for_an_operation_that_does_not_qualify_is_stale(tree):
    findings, stale = tree(INERT, _spec(),
                           acks={"GET /zzProbe": "reviewed"})
    assert findings == []
    assert [s["op"] for s in stale] == ["GET /zzProbe"]


def test_ack_goes_stale_once_the_command_starts_walking(tree):
    """The ratchet: fixing the generator retires the ack instead of leaving it
    to rot as a permanent allowlist entry."""
    findings, stale = tree(WALKS_VIA_ALL,
                           _spec(props={"total": {"type": "integer"}}),
                           acks={"GET /zzProbe": "reviewed"})
    assert findings == []
    assert [s["op"] for s in stale] == ["GET /zzProbe"]


# ------------------------------------------------------------- the live tree

def test_live_tree_is_acked_not_blind():
    """The gate reads 0 here. Assert it reads 0 because both real findings are
    acked — not because the check cannot see them."""
    unacked, stale = drift_check.check_undeclared_paging()
    assert unacked == [], unacked
    assert stale == [], stale

    raw, _ = drift_check.check_undeclared_paging(acks={})
    ops = sorted(f["op"] for f in raw)
    assert ops == ["GET /contacts/organizations/{}/contacts/search",
                   "GET /identity/organizations/{}/v1/ArchivedUser"], ops
