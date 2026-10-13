"""Drift gate check 30: a documented --json-body with keys the request does
not accept.

`contact-center-routing.md` documented `wxcli cc-captures create --json-body
'{"from": …, "to": …, "filters": …}'`; the spec (and the live API) take
`{"query": {"taskIds": [...]}}`, so the example could only fail. Checks
6/10/11 judge flag names and arguments, and check 29 judges the types of keys
the schema declares; nothing compared the documented keys with the schema.

Unparseable bodies are counted, never fired or raised (Review Focus 3); open
or unjudgeable schemas are skipped, and `$ref`/`allOf` are resolved (Review
Focus 4). Every fire case has a paired no-fire case, written so the check
can fail it.
"""

import json

import pytest

from tools import drift_check


BLOCK = '''
@app.command("create")
def create(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body."),
):
    """Create a capture."""
    url = f"https://webexapis.com/v1/zz/captures/query"
    body = json.loads(json_body) if json_body else {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
'''

QUERY = {"query": {"type": "object"}}


def _post_spec(schema, components=None):
    spec = {"paths": {"/zz/captures/query": {"post": {
        "requestBody": {"content": {"application/json": {"schema": schema}}},
        "responses": {"200": {"description": "ok"}}}}}}
    if components:
        spec["components"] = {"schemas": components}
    return spec


def _obj(props, **extra):
    return {"type": "object", "properties": props, **extra}


def _inv(body, group="zz-probe", command="create", line=644, flag="--json-body"):
    tokens = [flag, body] if body is not None else []
    return {"file": "docs/reference/zz.md", "line": line, "group": group,
            "command": command, "tokens": tokens, "in_code": True,
            "prefixless": False, "sig": {}}


def _fired(findings):
    """Real findings only — a body the check skips leaves nothing examined,
    and record_examined then adds its BLIND finding, which is not a fire."""
    return [f for f in findings if "unknown" in f]


@pytest.fixture
def tree(tmp_path):
    cmds = tmp_path / "commands"
    specs = tmp_path / "specs"
    cmds.mkdir()
    specs.mkdir()

    def run(invocations, *spec_list, registrations=None):
        (cmds / "zz_probe.py").write_text(BLOCK)
        for i, spec in enumerate(spec_list):
            name = "webex-probe.json" if i == 0 else f"webex-probe{i}.json"
            (specs / name).write_text(json.dumps(spec))
        return drift_check.check_doc_body_keys(
            invocations, drift_check.iter_command_blocks(cmds),
            drift_check.spec_ops_by_key(specs),
            registrations=registrations or {})

    return run


# ------------------------------------------------------- the 2026-03 bug

def test_unknown_top_level_key_fires(tree):
    """`cc-captures create` before the fix: `from`/`to`/`filters` against a
    schema that takes only `query`."""
    findings, unparseable = tree(
        [_inv('{"from": 1791763200000, "filters": {"queue": "q1"}}')],
        _post_spec(_obj(QUERY)))
    assert unparseable == 0
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["unknown"] == ["filters", "from"]
    assert f["allowed"] == ["query"]
    assert (f["file"], f["line"]) == ("docs/reference/zz.md", 644)
    assert (f["group"], f["command"]) == ("zz-probe", "create")


def test_known_keys_pass(tree):
    """The fix: `{"query": {"taskIds": [...]}}`. Nested keys are not judged."""
    findings, _ = tree([_inv('{"query": {"taskIds": ["t1"], "zz": 1}}')],
                       _post_spec(_obj(QUERY)))
    assert findings == []
    assert drift_check.CHECK_EXAMINED["30"] == {"examined": 1, "skipped": 0}


def test_partial_body_passes(tree):
    """A deliberately partial (PATCH-style) body is fine — only keys that
    exist are required, never all of them."""
    schema = _obj({"name": {"type": "string"}, "active": {"type": "boolean"},
                   "query": {"type": "object"}}, required=["name", "query"])
    assert tree([_inv('{"active": false}')], _post_spec(schema))[0] == []


def test_equals_form_fires(tree):
    inv = _inv(None) | {"tokens": ['--json-body={"filters": 1}']}
    findings, _ = tree([inv], _post_spec(_obj(QUERY)))
    assert [f["unknown"] for f in findings] == [["filters"]]


def test_duplicate_citation_on_one_line_reported_once(tree):
    inv = _inv('{"filters": 1}')
    findings, _ = tree([inv, dict(inv)], _post_spec(_obj(QUERY)))
    assert len(findings) == 1


def test_invocation_without_json_body_is_not_counted(tree):
    findings, unparseable = tree([_inv(None), _inv('{"query": {}}')],
                                 _post_spec(_obj(QUERY)))
    assert (findings, unparseable) == ([], 0)
    assert drift_check.CHECK_EXAMINED["30"]["examined"] == 1


# ------------------------------------------- Review Focus 3: unparseable

@pytest.mark.parametrize("body", [
    "$(cat f.json)", "file://x.json", "{not json", "@f.json", "-",
    '{"filters": ...}', "{...}", "'{\"filters\": 1}'", "JSON"])
def test_unparseable_bodies_counted_not_flagged(tree, body):
    findings, unparseable = tree([_inv(body), _inv('{"query": {}}')],
                                 _post_spec(_obj(QUERY)))
    assert findings == []
    assert unparseable == 1
    assert drift_check.CHECK_EXAMINED["30"] == {"examined": 1, "skipped": 0}


def test_top_level_array_body_is_skipped(tree):
    """A JSON array parses but has no top-level keys to judge."""
    findings, unparseable = tree([_inv('[{"filters": 1}]'), _inv('{"query": {}}')],
                                 _post_spec(_obj(QUERY)))
    assert (findings, unparseable) == ([], 0)
    assert drift_check.CHECK_EXAMINED["30"] == {"examined": 1, "skipped": 1}


# --------------------------------------- Review Focus 4: schema shapes

@pytest.mark.parametrize("extra", [
    {"additionalProperties": True}, {"additionalProperties": {}},
    {"additionalProperties": {"type": "string"}}])
def test_open_schema_skipped(tree, extra):
    findings, _ = tree([_inv('{"filters": 1}')], _post_spec(_obj(QUERY, **extra)))
    assert _fired(findings) == []
    assert drift_check.CHECK_EXAMINED["30"] == {"examined": 0, "skipped": 1}


def test_closed_schema_with_additional_properties_false_fires(tree):
    findings, _ = tree([_inv('{"filters": 1}')],
                       _post_spec(_obj(QUERY, additionalProperties=False)))
    assert [f["unknown"] for f in findings] == [["filters"]]


@pytest.mark.parametrize("schema", [
    {"type": "object"}, {"type": "array", "items": {"type": "string"}}, {}])
def test_schema_without_properties_skipped(tree, schema):
    findings, _ = tree([_inv('{"filters": 1}'), _inv('{"filters": 2}', line=7)],
                       _post_spec(schema))
    assert _fired(findings) == []
    assert drift_check.CHECK_EXAMINED["30"] == {"examined": 0, "skipped": 2}


def test_op_without_request_body_skipped(tree):
    spec = {"paths": {"/zz/captures/query": {"post": {
        "responses": {"200": {"description": "ok"}}}}}}
    findings, _ = tree([_inv('{"filters": 1}'), _inv('{"x": 1}', line=7)], spec)
    assert _fired(findings) == []
    assert drift_check.CHECK_EXAMINED["30"] == {"examined": 0, "skipped": 2}


def test_allof_ref_schema_resolved(tree):
    """`$ref` to an `allOf` of two `$ref`d parts, one of them itself an
    allOf: keys from every part pass, a key from none fires."""
    components = {
        "Capture": {"allOf": [{"$ref": "#/components/schemas/Base"},
                              {"$ref": "#/components/schemas/Nested"}]},
        "Base": _obj({"query": {"type": "object"}}),
        "Nested": {"allOf": [_obj({"deep": {"type": "string"}})]},
    }
    spec = _post_spec({"$ref": "#/components/schemas/Capture"}, components)
    assert tree([_inv('{"query": {}, "deep": "x"}')], spec)[0] == []
    findings, _ = tree([_inv('{"query": {}, "filters": 1}')], spec)
    assert [f["unknown"] for f in findings] == [["filters"]]
    assert findings[0]["allowed"] == ["deep", "query"]


def test_allof_with_open_part_skipped(tree):
    components = {"Open": {"type": "object", "additionalProperties": True}}
    spec = _post_spec({"allOf": [_obj(QUERY),
                                 {"$ref": "#/components/schemas/Open"}]},
                      components)
    assert _fired(tree([_inv('{"filters": 1}')], spec)[0]) == []


@pytest.mark.parametrize("combiner", ["oneOf", "anyOf"])
def test_composed_schema_of_closed_branches_judged_against_their_union(
        tree, combiner):
    """`cc-agent-summaries create` (SummaryListRequest): a key no branch
    declares is rejected whichever branch the server picks."""
    spec = _post_spec({combiner: [_obj({"orgId": {}, "searchType": {}}),
                                  _obj({"orgId": {}, "agentCiUserId": {}})]})
    assert tree([_inv('{"searchType": "AGENT", "agentCiUserId": "u"}')],
                spec)[0] == []
    findings, _ = tree([_inv('{"filter": {"agentId": "a"}}')], spec)
    assert [f["unknown"] for f in findings] == [["filter"]]


@pytest.mark.parametrize("branch", [
    {"type": "object", "additionalProperties": True},
    {"type": "object"},
    {"$ref": "#/components/schemas/Missing"}])
def test_composed_schema_with_an_unjudgeable_branch_skipped(tree, branch):
    spec = _post_spec({"oneOf": [_obj(QUERY), branch]}, {"Other": {}})
    assert _fired(tree([_inv('{"filters": 1}')], spec)[0]) == []
    assert drift_check.CHECK_EXAMINED["30"]["skipped"] == 1


def test_discriminator_without_alternatives_skipped(tree):
    """A discriminator base names only the shared keys; subtypes add more."""
    spec = _post_spec(_obj(QUERY, discriminator={"propertyName": "kind"}))
    assert _fired(tree([_inv('{"filters": 1}')], spec)[0]) == []


def test_two_specs_union_and_veto(tree):
    """A path two specs declare accepts a key either declares; one spec that
    cannot be judged skips the body rather than guessing."""
    a = _post_spec(_obj(QUERY))
    b = _post_spec(_obj({"filters": {}}))
    assert tree([_inv('{"query": {}, "filters": 1}')], a, b)[0] == []
    findings, _ = tree([_inv('{"from": 1}')], a, b)
    assert [f["unknown"] for f in findings] == [["from"]]
    open_b = _post_spec(_obj({"filters": {}}, additionalProperties=True))
    assert _fired(tree([_inv('{"from": 1}')], a, open_b)[0]) == []


@pytest.mark.parametrize("where", ["media", "examples", "schema"])
def test_key_in_the_specs_own_request_example_passes(tree, where):
    """`PATCH /groups/{groupId}`: the schema says `{schemas, Operations}`, its
    example (and the docs) send `{members: [...]}`. A doc matching the spec's
    own example does not contradict the spec; a key in neither still fires."""
    schema = _obj({"schemas": {}, "Operations": {}})
    example = {"displayName": "Sales", "members": [{"id": "p", "operation": "add"}]}
    spec = _post_spec(dict(schema, example=example) if where == "schema" else schema)
    node = spec["paths"]["/zz/captures/query"]["post"]["requestBody"]["content"][
        "application/json"]
    if where == "media":
        node["example"] = example
    elif where == "examples":
        node["examples"] = {"one": {"summary": "s", "value": example}}
    assert tree([_inv('{"members": [{"id": "p", "operation": "add"}]}')],
                spec)[0] == []
    findings, _ = tree([_inv('{"memberIds": ["p"]}')], spec)
    assert [f["unknown"] for f in findings] == [["memberIds"]]
    assert "members" in findings[0]["allowed"]


def test_key_listed_as_patchable_in_the_op_description_passes(tree):
    """`PATCH …/channel/{id}`: ChannelPatchDTO omits `name`, but the
    operation's description says "Patchable fields: name, description, …"."""
    spec = _post_spec(_obj({"description": {}, "logoType": {}}))
    spec["paths"]["/zz/captures/query"]["post"]["description"] = (
        "Partially update a channel. Patchable fields: name, description, "
        "logoType (MOMENTUM only), logoIconName. logoUrl cannot be changed.")
    assert tree([_inv('{"name": "Web Chat EU", "logoIconName": "chat"}')],
                spec)[0] == []
    findings, _ = tree([_inv('{"logoUrl": "x"}')], spec)
    assert [f["unknown"] for f in findings] == [["logoUrl"]]


def test_key_merely_mentioned_in_the_op_description_still_fires(tree):
    """Only an explicit `<…able> fields:` list widens the keys — a word in
    prose does not (`cc-contact-list update-status` mentions "status")."""
    spec = _post_spec(_obj({"contactListStatus": {}}))
    spec["paths"]["/zz/captures/query"]["post"]["description"] = (
        "Updates the status of a contact list (e.g., EXPIRED).")
    findings, _ = tree([_inv('{"status": "ACTIVE"}')], spec)
    assert [f["unknown"] for f in findings] == [["status"]]


def test_json_value_schema_is_open(tree):
    """The CC spec's `JsonValue` (properties: only `valueType`) is a
    serialized Jackson JsonNode — any JSON at all (`asset update-asset`)."""
    components = {"JsonValue": _obj({"valueType": {
        "type": "string", "enum": ["ARRAY", "OBJECT", "STRING"]}})}
    spec = _post_spec({"$ref": "#/components/schemas/JsonValue"}, components)
    assert _fired(tree([_inv('{"description": "Migrated"}')], spec)[0]) == []
    assert drift_check.CHECK_EXAMINED["30"] == {"examined": 0, "skipped": 1}
    closed = _post_spec(_obj({"valueType": {}, "name": {}}))
    findings, _ = tree([_inv('{"description": "Migrated"}')], closed)
    assert [f["unknown"] for f in findings] == [["description"]]


def test_example_keys_never_open_a_schema_that_cannot_be_judged(tree):
    spec = _post_spec(_obj(QUERY, additionalProperties=True))
    spec["paths"]["/zz/captures/query"]["post"]["requestBody"]["content"][
        "application/json"]["example"] = {"filters": 1}
    assert _fired(tree([_inv('{"from": 1}')], spec)[0]) == []
    assert drift_check.CHECK_EXAMINED["30"]["examined"] == 0


@pytest.mark.parametrize("odd", [["not", "a", "dict"], "schema", 7])
def test_odd_body_schema_is_skipped_never_raised(tree, monkeypatch, odd):
    monkeypatch.setattr(drift_check, "body_schema", lambda op, spec: odd)
    findings, _ = tree([_inv('{"filters": 1}')], _post_spec(_obj(QUERY)))
    assert len(findings) == 1 and "examined 0" in findings[0]["error"]


def test_raising_schema_reader_is_skipped_never_raised(tree, monkeypatch):
    def boom(op, spec):
        raise RuntimeError("odd upstream shape")
    monkeypatch.setattr(drift_check, "body_schema", boom)
    findings, _ = tree([_inv('{"filters": 1}')], _post_spec(_obj(QUERY)))
    assert len(findings) == 1 and "examined 0" in findings[0]["error"]


# ------------------------------------------------- resolution and blindness

def test_alias_group_resolves_through_registrations(tree):
    findings, _ = tree([_inv('{"filters": 1}', group="zz-alias")],
                       _post_spec(_obj(QUERY)),
                       registrations={"zz-alias": "zz_probe"})
    assert [f["group"] for f in findings] == ["zz-alias"]


def test_unresolved_invocation_is_skipped_and_counted(tree):
    findings, _ = tree([_inv('{"filters": 1}', command="no-such"),
                        _inv('{"query": {}}')], _post_spec(_obj(QUERY)))
    assert findings == []
    assert drift_check.CHECK_EXAMINED["30"] == {"examined": 1, "skipped": 1}


def test_nothing_examined_is_blind(tree):
    findings, _ = tree([_inv('{"filters": 1}', command="no-such")],
                       _post_spec(_obj(QUERY)))
    assert len(findings) == 1 and "examined 0" in findings[0]["error"]


# -------------------------------------------------------------------- print

def test_print_renders_unparseable_count(tree, capsys):
    findings, unparseable = tree(
        [_inv('{"filters": 1}'), _inv("file://x.json", line=9)],
        _post_spec(_obj(QUERY)))
    drift_check.print_check_findings(
        "30", findings, note=f"({unparseable} unparseable, not checked)")
    out = capsys.readouterr().out.splitlines()
    assert out[0] == (
        "[30] documented --json-body examples with keys the request does not "
        "accept: 1   (examined 1 documented --json-body examples, skipped 0)"
        "   (1 unparseable, not checked)")
    assert "wxcli zz-probe create  --json-body filters  (accepts: query)" in out[1]


# ---------------------------------------------------------------- live tree

def test_live_tree_is_clean():
    surface, _ = drift_check.build_cli_surface()
    positional = drift_check.build_positional_surface()
    findings, unparseable = drift_check.check_doc_body_keys(
        list(drift_check.doc_invocations(surface, positional)),
        drift_check.iter_command_blocks(), drift_check.spec_ops_by_key())
    assert findings == []
    assert drift_check.CHECK_EXAMINED["30"]["examined"] > 100
    assert unparseable > 0
