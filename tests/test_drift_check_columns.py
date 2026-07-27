"""Drift gate check 9: a list command's table columns must exist on the response.

Regression cover for a defect an operator cannot see. Every generated `list`
renders a Rich table from a hardcoded `columns=[(header, accessor)]` list; when
an accessor names a field the API does not return, the command still exits 0
and prints a table — with blank columns, or, when every column resolves empty,
with output.py's auto_columns fallback ballooning it to 40+ auto-detected ones.
`-o json` was always correct; only the table lied. 215 of 513 list commands
were in that state before the renderer began deriving defaults from the schema.

Three classes must never be flagged, and each has its own case below:
  - dotted accessors, which output.py:_resolve_accessor supports;
  - operations declared in more than one spec (151 of them), where the
    generator rendered from one and the other declares different fields;
  - responses whose extracted item has no scalar field at all — the payload
    nests deeper than the extractor reaches, so no column list can fix them.
"""

import json
import textwrap

import pytest

from tools import drift_check


STRING = {"type": "string"}
PROBE_PATH = "/v1/zzProbe"


def _probe_module(columns: str, item_key: str) -> str:
    return textwrap.dedent(f'''\
        """Probe module."""
        import typer

        app = typer.Typer()


        @app.command("list")
        def list_things(output: str = typer.Option("table", "--output")):
            """Probe."""
            url = f"https://webexapis.com{PROBE_PATH}"
            params = {{}}
            items = list(api.session.follow_pagination(url=url, params=params, item_key="{item_key}"))
            emit(items, output=output, fields=None, columns={columns}, limit=0)
        ''')


def _probe_spec(properties: dict, item_key: str) -> dict:
    return {"paths": {PROBE_PATH: {"get": {"responses": {"200": {"content": {
        "application/json": {"schema": {"type": "object", "properties": {
            item_key: {"type": "array",
                       "items": {"type": "object", "properties": properties}},
        }}}}}}}}}}


@pytest.fixture(autouse=True)
def _reset_caches():
    drift_check._MODULE_STATE = None
    drift_check._IGNORE_CACHE.clear()
    yield
    drift_check._MODULE_STATE = None
    drift_check._IGNORE_CACHE.clear()


@pytest.fixture
def check(tmp_path, monkeypatch):
    """Run check 9 over one probe module and a fixture spec.

    parse_registrations() reads the real _registry.py, so the probe borrows the
    name of a module the manifest already registers — only the body is fixture.
    It must be both registered AND countable or check 9 skips it and every case
    here passes vacuously (`__init__` sorts first among countable stems and is
    registered by nothing — that mistake made 6 of these tests prove nothing).
    tracked_specs() is patched to absolute paths, which `REPO / rel` returns
    unchanged, so no repo file is read.
    """
    def run(columns, *, properties, item_key="items", extra_specs=None,
            components=None):
        module = sorted(set(drift_check.parse_registrations().values())
                        & drift_check.module_state()["countable"])[0]
        (tmp_path / f"{module}.py").write_text(_probe_module(columns, item_key))
        spec = _probe_spec(properties, item_key)
        if components:
            spec["components"] = {"schemas": components}
        specs = {"probe.json": spec, **(extra_specs or {})}
        paths = set()
        for name, body in specs.items():
            (tmp_path / name).write_text(json.dumps(body))
            paths.add(str(tmp_path / name))
        monkeypatch.setattr(drift_check, "tracked_specs", lambda: paths)
        return drift_check.check_table_columns(commands_dir=tmp_path)

    return run


def test_flags_an_accessor_the_response_cannot_have(check):
    """The whole point: id/name on a response that returns neither."""
    findings, _ = check('[("ID", "id"), ("Name", "name")]',
                        properties={"phoneNumber": STRING, "state": STRING})
    assert [f["missing"] for f in findings] == [["id", "name"]]
    assert findings[0]["available"] == ["phoneNumber", "state"]


def test_passes_when_every_accessor_exists(check):
    findings, _ = check("[('Phone Number', 'phoneNumber'), ('State', 'state')]",
                        properties={"phoneNumber": STRING, "state": STRING})
    assert findings == []


def test_ignores_dotted_accessors(check):
    """output.py:_resolve_accessor walks dots; this check cannot follow them,
    so flagging one is a false positive (3 of the first 67 triaged were)."""
    findings, _ = check("[('Owner Type', 'owner.type')]",
                        properties={"owner": {"type": "object"}})
    assert findings == []


def test_unions_specs_that_both_declare_the_operation(check):
    """151 operations live in two specs with different item schemas, and the
    generator rendered from exactly one. Flagging a field the other spec
    declares would fail a correct command — it did, on device-settings
    list-errors, whose `item` exists in webex-cloud-calling.json and not in
    webex-device.json."""
    findings, _ = check("[('Item', 'item')]",
                        properties={"itemNumber": {"type": "number"}},
                        extra_specs={"other.json": _probe_spec({"item": STRING}, "items")})
    assert findings == []


def test_excludes_wrapper_shaped_responses_instead_of_flagging_them(check):
    """Video Mesh nests its payload at items[].items — one level deeper than
    the extractor reaches. No column list fixes that; nested extraction was
    cut deliberately, so these are reported separately, not failed."""
    findings, wrapper_only = check(
        '[("ID", "id"), ("Name", "name")]',
        properties={"clusters": {"type": "array", "items": {"type": "object"}}})
    assert findings == []
    assert [w["command"] for w in wrapper_only] == ["list"]


def test_resolves_refs_and_allof(check):
    """Cisco $refs or allOf-composes most item schemas; leaving one unresolved
    looks like an empty schema and would silently skip the command."""
    findings, _ = check(
        "[('Name', 'name'), ('State', 'state')]",
        properties={"name": STRING},
        item_key="items",
        components={"Extra": {"type": "object", "properties": {"state": STRING}}},
        extra_specs={"reffed.json": {
            "paths": {PROBE_PATH: {"get": {"responses": {"200": {"content": {
                "application/json": {"schema": {"allOf": [
                    {"$ref": "#/components/schemas/Wrapper"},
                ]}}}}}}}},
            "components": {"schemas": {
                "Wrapper": {"type": "object", "properties": {
                    "items": {"type": "array",
                              "items": {"$ref": "#/components/schemas/Item"}}}},
                "Item": {"type": "object", "properties": {"state": STRING}},
            }}}})
    assert findings == []


def test_says_nothing_about_an_endpoint_with_no_declared_item_schema(check):
    """Absence of a schema is not evidence the columns are wrong."""
    findings, wrapper_only = check('[("ID", "id"), ("Name", "name")]', properties={})
    assert findings == [] and wrapper_only == []


def test_the_live_tree_has_no_column_drift():
    """The gate's real assertion, run against the shipped tree so it cannot
    regress at the next spec refresh."""
    findings, _ = drift_check.check_table_columns()
    assert findings == [], f"{len(findings)} list commands render blank columns"
