"""Drift gate checks 19 and 20 — spec-delta acknowledgment, reference-doc coverage.

Check 19 exists because of three real changes that landed on 2026-08-03 with the
gate reporting PASS. Each one is reproduced verbatim at the bottom of this file
from `git diff 27f3e28 a898c76 -- specs/`, inlined rather than read out of git so
the proof survives a shallow CI checkout:

  1. `selectiveCallRecordingSettings` — a whole new capability arriving as
     request-BODY fields on three call-recording PUTs. Check 1 detects missing
     operations; this added no operation.
  2. `cc-dial-number --location` — the description changed from "the NAME of the
     location" to "the ID of the location". The flag existed before and after,
     so every existing check passed.
  3. `update-person` — two API constraints added to the operation description,
     which the CLI structurally cannot carry (openapi_parser reads `summary`).

Every case below is written so the check can FAIL it. The paired
does-not-fire / does-fire assertions are the point: a check reading 0 because it
is looking at nothing is indistinguishable from a clean tree, and that is how
check 9 and check 2 both shipped a confident 0 while broken.
"""

import json

import pytest

from tools import drift_check as dc


def _spec(path="/v1/zzProbe", method="put", tag="Probe", summary="Do a thing",
          description="", params=None, body=None, components=None):
    """One-operation spec. A literal, not a fixture pulled off disk: a spec
    refresh must not be able to change what this test believes an operation is."""
    op = {"tags": [tag], "summary": summary}
    if description:
        op["description"] = description
    if params:
        op["parameters"] = params
    if body is not None:
        op["requestBody"] = {"content": {"application/json": {"schema": body}}}
    spec = {"paths": {path: {method: op}}}
    if components:
        spec["components"] = {"schemas": components}
    return spec


def sem(spec, name="webex-probe.json", skip_tags=None):
    return dc.spec_semantics({name: spec}, skip_tags=skip_tags or {})


def fields_of(snapshot, name="webex-probe.json", op="PUT /zzProbe"):
    return snapshot[name][op]["fields"]


def diff(old_spec, new_spec, **kw):
    return dc.diff_spec_semantics(sem(old_spec, **kw), sem(new_spec, **kw))


# ------------------------------------------------------------ the encoding

@pytest.mark.parametrize("required,desc,enum,expected", [
    (False, "", (), ""),
    (True, "", (), "!"),
    (False, "Plain words.", (), "#" ),
    (False, "The ID of the location.", (), "~id#"),
    (False, "The name of the location.", (), "~name#"),
    (False, "It must be unique.", (), "#"),
])
def test_encoding_carries_each_attribute(required, desc, enum, expected):
    value = dc.encode_field(required, desc, enum)
    assert value.startswith(expected), value


def test_encoding_round_trips():
    value = dc.encode_field(True, "The ID of the thing. It must be unique.",
                            ("A", "B"))
    parts = dc.decode_field(value)
    assert parts["required"] is True
    assert parts["kind"] == "id"
    assert parts["desc"] and parts["constraints"]
    assert parts["enum"] == "A|B"
    assert parts["malformed"] is None


def test_enum_values_may_contain_the_delimiters_used_by_the_prefix():
    """Enum is encoded LAST precisely so an API token containing `#` or `~`
    cannot be mistaken for a hash or a kind marker."""
    parts = dc.decode_field(dc.encode_field(False, "", ("a#b", "c~d")))
    assert parts["enum"] == "a#b|c~d"
    assert parts["desc"] is None and parts["kind"] is None


def test_malformed_value_is_reported_not_read_as_empty():
    """A hand-edited snapshot must fail loudly. Reading an unparseable entry as
    "no attributes" would silently disable the comparison for that field."""
    assert dc.decode_field("!!not-an-encoding")["malformed"] == "!!not-an-encoding"


def test_hash_is_reflow_invariant():
    """The 2026-08-03 refresh rewrote 22,328 lines of webex-cloud-calling.json
    while changing four operations. A hash over raw bytes would have reported
    the whole spec as changed and taught everyone to ignore check 19."""
    a = dc.encode_field(False, "One two three.", ())
    b = dc.encode_field(False, "One\n  two\tthree.", ())
    assert a == b


def test_constraint_set_is_reflow_invariant():
    a = dc.constraint_sentences("The id must be unique. It cannot change.")
    b = dc.constraint_sentences("The id must be\nunique. It cannot\nchange.")
    assert a == b and len(a) == 2


def test_bullets_stay_separate_constraints():
    """`Update a Person` states its rules as `* …` bullets with no blank line
    between them once whitespace is collapsed. Collapsing without splitting on
    the marker would fuse four rules into one and hide the addition of a fifth."""
    text = "**NOTE**: * It must be A. * It cannot be B."
    assert len(dc.constraint_sentences(text)) == 2


# ------------------------------------------------------- the kind detector

@pytest.mark.parametrize("old,new,flips", [
    ("The name of the location.", "The ID of the location.", True),
    ("The ID of the location.", "The name of the location.", True),
    ("", "Name.", False),                       # measured false positive of the
    ("Retrieve a list of Team(s).", "Retrieve a list of Teams.", False),  # loose
    ("The identifier of the queue.", "The name of the queue.", True),
])
def test_kind_flip_is_anchored_on_the_phrase_not_the_words(old, new, flips):
    """The loose form ("does the text mention id/name at all") fires 26 times on
    one historical refresh, nearly all of them `"" -> "Name."`. The anchored
    form fires 3 times across 8 refreshes and all 3 are the real defect."""
    a, b = dc.describe_kind(old), dc.describe_kind(new)
    assert bool(a and b and a != b) is flips


# ------------------------------------------------------- what is in scope

def test_skipped_tag_is_not_recorded():
    """Scope matches load_spec_ops: a deliberate gap is not a surface whose
    meaning anyone maintains."""
    kept = sem(_spec(tag="Probe"))
    skipped = sem(_spec(tag="Probe"), skip_tags={"_global": ["Probe"]})
    assert kept and skipped == {}


def test_untagged_operation_is_not_recorded():
    spec = _spec()
    del spec["paths"]["/v1/zzProbe"]["put"]["tags"]
    assert sem(spec) == {}


def test_multipart_upload_is_not_recorded():
    spec = _spec()
    spec["paths"]["/v1/zzProbe"]["put"]["requestBody"] = {
        "content": {"multipart/form-data": {"schema": {}}}}
    assert sem(spec) == {}


def test_the_same_operation_in_two_specs_is_kept_per_spec():
    """`Update a Person` is declared in three tracked specs and maintained in
    exactly one — People is in skip_tags for admin and messaging. Unioning is
    how check 9's predecessor reported a confident 0 over a broken command."""
    both = dc.spec_semantics(
        {"webex-a.json": _spec(tag="People"), "webex-b.json": _spec(tag="People")},
        skip_tags={"webex-b.json": ["People"]})
    assert set(both) == {"webex-a.json"}


# --------------------------------------------------------- the body walker

def test_nested_object_fields_are_recorded_by_dotted_path():
    """The selectiveCallRecordingSettings shape. A walker that stopped at the
    top level would record the new object and miss its four toggles — which is
    the whole content of the capability."""
    body = {"type": "object", "properties": {
        "enabled": {"type": "boolean"},
        "selective": {"type": "object", "required": ["inbound"], "properties": {
            "inbound": {"type": "boolean"}, "outbound": {"type": "boolean"}}}}}
    got = fields_of(sem(_spec(body=body)))
    assert "body:selective.inbound" in got
    assert got["body:selective.inbound"].startswith("!")
    assert "body:selective.outbound" in got


def test_ref_is_resolved():
    """Most Webex bodies are a $ref. A walker reading only inline properties
    would report almost the entire spec surface as fieldless."""
    body = {"$ref": "#/components/schemas/Thing"}
    comps = {"Thing": {"type": "object", "properties": {"a": {"type": "string"}}}}
    assert "body:a" in fields_of(sem(_spec(body=body, components=comps)))


def test_array_items_get_a_bracket_segment():
    body = {"type": "object", "properties": {"items": {
        "type": "array", "items": {"type": "object",
                                   "properties": {"item": {"type": "string"}}}}}}
    got = fields_of(sem(_spec(body=body)))
    assert "body:items[].item" in got


def test_allof_is_flattened():
    body = {"allOf": [{"type": "object", "properties": {"a": {"type": "string"}}},
                      {"type": "object", "properties": {"b": {"type": "string"}}}]}
    got = fields_of(sem(_spec(body=body)))
    assert {"body:a", "body:b"} <= set(got)


def test_a_self_referential_schema_terminates():
    body = {"$ref": "#/components/schemas/Node"}
    comps = {"Node": {"type": "object", "properties": {
        "name": {"type": "string"}, "child": {"$ref": "#/components/schemas/Node"}}}}
    got = fields_of(sem(_spec(body=body, components=comps)))
    assert "body:name" in got and "body:child" in got


def test_a_reused_schema_expands_under_both_parents():
    """Cycle protection is per-BRANCH. A global `seen` would expand Addr under
    `home` and silently record `work` as an empty object."""
    body = {"type": "object", "properties": {
        "home": {"$ref": "#/components/schemas/Addr"},
        "work": {"$ref": "#/components/schemas/Addr"}}}
    comps = {"Addr": {"type": "object", "properties": {"city": {"type": "string"}}}}
    got = fields_of(sem(_spec(body=body, components=comps)))
    assert {"body:home.city", "body:work.city"} <= set(got)


def test_query_and_path_parameters_are_recorded_with_their_location():
    params = [{"name": "orgId", "in": "query", "required": True,
               "description": "The ID of the organization."},
              {"name": "personId", "in": "path", "required": True}]
    got = fields_of(sem(_spec(params=params)))
    assert got["query:orgId"].startswith("!~id#")
    assert got["path:personId"] == "!"


def test_parameter_enum_is_recorded():
    params = [{"name": "state", "in": "query",
               "schema": {"type": "string", "enum": ["b", "a"]}}]
    assert fields_of(sem(_spec(params=params)))["query:state"] == "=a|b"


# ------------------------------------------------- the three-tier classifier

def _kinds(rows):
    return sorted(r["kind"] for r in rows)


def test_identical_specs_produce_no_deltas():
    """The control. Without it every assertion below could pass for the wrong
    reason — a differ that reports everything as changed."""
    s, f, p = diff(_spec(body={"type": "object",
                               "properties": {"a": {"type": "string"}}}),
                   _spec(body={"type": "object",
                               "properties": {"a": {"type": "string"}}}))
    assert (s, f, p) == ([], [], [])


def test_added_and_removed_fields_are_structural():
    one = {"type": "object", "properties": {"a": {"type": "string"}}}
    two = {"type": "object", "properties": {"b": {"type": "string"}}}
    s, f, p = diff(_spec(body=one), _spec(body=two))
    assert _kinds(s) == ["field_added", "field_removed"]
    assert [r["field"] for r in s if r["kind"] == "field_added"] == ["body:b"]
    assert (f, p) == ([], [])


def test_requiredness_change_is_structural():
    loose = {"type": "object", "properties": {"a": {"type": "string"}}}
    strict = dict(loose, required=["a"])
    s, _, _ = diff(_spec(body=loose), _spec(body=strict))
    assert _kinds(s) == ["required_added"]
    s, _, _ = diff(_spec(body=strict), _spec(body=loose))
    assert _kinds(s) == ["required_removed"]


def test_enum_change_is_structural_and_names_both_sides():
    old = {"type": "object", "properties": {"a": {"enum": ["X", "Y"]}}}
    new = {"type": "object", "properties": {"a": {"enum": ["X"]}}}
    s, _, _ = diff(_spec(body=old), _spec(body=new))
    assert _kinds(s) == ["enum_changed"]
    assert s[0]["detail"] == "X|Y -> X"


def test_operation_added_and_removed_are_structural():
    """A whole spec appearing or vanishing is reported once, not once per
    operation: an empty snapshot must read as "nothing was ever recorded", not
    as 1,883 unrelated findings."""
    s, _, _ = dc.diff_spec_semantics({}, sem(_spec()))
    assert _kinds(s) == ["spec_added"]
    s, _, _ = dc.diff_spec_semantics(sem(_spec()), {})
    assert _kinds(s) == ["spec_removed"]
    s, _, _ = dc.diff_spec_semantics(
        sem(_spec(path="/v1/zzOne")),
        dc.spec_semantics({"webex-probe.json": {"paths": {
            "/v1/zzOne": {"put": {"tags": ["Probe"], "summary": "s"}},
            "/v1/zzTwo": {"put": {"tags": ["Probe"], "summary": "s"}}}}},
            skip_tags={}))
    assert _kinds(s) == ["operation_added"]


def test_a_retagged_operation_is_structural():
    """A tag change moves the operation into a different CLI group. That is a
    rename of the command path, not a wording change."""
    s, _, p = diff(_spec(tag="Probe"), _spec(tag="Other"))
    assert _kinds(s) == ["tag_changed"]
    assert p == []


def test_summary_change_is_advisory_only():
    s, f, p = diff(_spec(summary="Do a thing"), _spec(summary="Do the thing"))
    assert (s, f) == ([], [])
    assert _kinds(p) == ["summary_changed"]


def test_id_kind_flip_is_gated_and_does_not_double_report_as_prose():
    old = {"type": "object", "properties": {
        "location": {"description": "The name of the location."}}}
    new = {"type": "object", "properties": {
        "location": {"description": "The ID of the location."}}}
    s, f, p = diff(_spec(body=old), _spec(body=new))
    assert s == [] and p == []
    assert _kinds(f) == ["kind_flip"]
    assert f[0]["field"] == "body:location"
    assert f[0]["detail"] == "description called it name, now calls it id"


def test_a_kind_appearing_where_there_was_none_is_advisory():
    """One-sided: nothing was contradicted, so there is nothing mechanical to
    decide. Gating this is what takes the flip detector from 3 hits to 26."""
    old = {"type": "object", "properties": {"a": {"description": "A thing."}}}
    new = {"type": "object", "properties": {
        "a": {"description": "The ID of a thing."}}}
    s, f, p = diff(_spec(body=old), _spec(body=new))
    assert (s, f) == ([], [])
    assert _kinds(p) == ["kind_stated"]


def test_constraint_change_is_advisory_and_named_apart_from_wording():
    s, f, p = diff(_spec(description="Update a person."),
                   _spec(description="Update a person. A license must exist."))
    assert (s, f) == ([], [])
    assert _kinds(p) == ["constraint_changed"]
    assert p[0]["field"] == "(operation)"


def test_plain_rewording_is_advisory():
    s, f, p = diff(_spec(description="Update a person."),
                   _spec(description="Updates a person."))
    assert (s, f) == ([], [])
    assert _kinds(p) == ["wording_changed"]


def test_prose_alone_never_reaches_a_gated_bucket():
    """The tier contract in one assertion: no combination of summary,
    description or constraint text can fail the build."""
    old = _spec(summary="A", description="Does a thing.",
                body={"type": "object", "properties": {
                    "a": {"description": "One."}}})
    new = _spec(summary="B", description="Does a thing. It must be enabled.",
                body={"type": "object", "properties": {
                    "a": {"description": "Two."}}})
    s, f, p = diff(old, new)
    assert (s, f) == ([], [])
    assert len(p) == 3


def test_whitespace_only_reflow_produces_no_delta_at_all():
    """The volume argument. Upstream reflows constantly; if reflow registered,
    every refresh would report thousands of deltas and the check would be off
    within a month."""
    s, f, p = diff(_spec(description="One two three."),
                   _spec(description="One\n  two\tthree."))
    assert (s, f, p) == ([], [], [])


# ------------------------------------------- the three real 2026-08-03 cases
#
# Content below is verbatim from `git diff 27f3e28 a898c76 -- specs/`, inlined
# so a shallow CI checkout can still run it. Each case is the SHAPE that got
# through, not a paraphrase of it.

CALL_RECORDING_BEFORE = {
    "type": "object",
    "properties": {
        "enabled": {"type": "boolean"},
        "record": {"type": "string",
                   "enum": ["Always", "Never", "On Demand with User Initiated Start"]},
        "recordVoicemailEnabled": {"type": "boolean"},
    },
}
CALL_RECORDING_AFTER = json.loads(json.dumps(CALL_RECORDING_BEFORE))
CALL_RECORDING_AFTER["properties"]["selectiveCallRecordingSettings"] = {
    "type": "object",
    "description": "Selective call recording settings. Applicable when "
                   "`recordingMode` is set to either `Always` or `Always with "
                   "Pause/Resume`.",
    "required": ["recordInboundInternalCallsEnabled",
                 "recordInboundExternalCallsEnabled",
                 "recordOutboundInternalCallsEnabled",
                 "recordOutboundExternalCallsEnabled"],
    "properties": {
        "recordInboundInternalCallsEnabled": {
            "type": "boolean",
            "description": "If `true`, inbound internal calls are recorded."},
        "recordInboundExternalCallsEnabled": {
            "type": "boolean",
            "description": "If `true`, inbound external calls are recorded."},
        "recordOutboundInternalCallsEnabled": {
            "type": "boolean",
            "description": "If `true`, outbound internal calls are recorded."},
        "recordOutboundExternalCallsEnabled": {
            "type": "boolean",
            "description": "If `true`, outbound external calls are recorded."},
    },
}


def test_case_1_a_new_capability_arriving_as_body_fields_fires():
    """`selectiveCallRecordingSettings`: four independent record toggles, no new
    operation, so check 1 could not see it. It reached the CLI only as
    --generate-json-body skeleton content and no doc mentions it to this day."""
    s, f, p = diff(_spec(path="/v1/people/{personId}/features/callRecording",
                         body=CALL_RECORDING_BEFORE),
                   _spec(path="/v1/people/{personId}/features/callRecording",
                         body=CALL_RECORDING_AFTER))
    added = sorted(r["field"] for r in s if r["kind"] == "field_added")
    assert added == [
        "body:selectiveCallRecordingSettings",
        "body:selectiveCallRecordingSettings.recordInboundExternalCallsEnabled",
        "body:selectiveCallRecordingSettings.recordInboundInternalCallsEnabled",
        "body:selectiveCallRecordingSettings.recordOutboundExternalCallsEnabled",
        "body:selectiveCallRecordingSettings.recordOutboundInternalCallsEnabled",
    ]
    assert all(r["kind"] == "field_added" for r in s)
    # every one of the four toggles is spec-REQUIRED, and the encoding says so
    assert sum(r["detail"].startswith("!") for r in s) == 4


DIAL_NUMBER_BEFORE = {"type": "object", "properties": {"location": {
    "type": "string",
    "description": "The name of the location as configured on Webex "
                   "Calling(applicable only for Webex Calling).",
    "example": "7cbd4aad-0c3b-4de4-a15a-33cf05b9bf8j"}}}
DIAL_NUMBER_AFTER = {"type": "object", "properties": {"location": {
    "type": "string",
    "description": "The ID of the location as configured on Webex "
                   "Calling(applicable only for Webex Calling).",
    "example": "7cbd4aad-0c3b-4de4-a15a-33cf05b9bf8j"}}}


def test_case_2_an_id_kind_flip_in_a_description_fires_and_is_gated():
    """cc-dial-number `--location`. The flag existed before and after, so every
    check the gate had passed. Had a doc said "pass the location name", nothing
    would have caught it."""
    s, f, p = diff(_spec(path="/v1/organization/{orgId}/dial-number",
                         method="post", body=DIAL_NUMBER_BEFORE),
                   _spec(path="/v1/organization/{orgId}/dial-number",
                         method="post", body=DIAL_NUMBER_AFTER))
    assert s == [] and p == []      # structurally identical — only meaning moved
    assert len(f) == 1
    assert f[0]["field"] == "body:location"
    assert f[0]["kind"] == "kind_flip"


UPDATE_PERSON_BEFORE = (
    "Update details for a person, by ID.\n\n**NOTE**:\n\n"
    "* The `locationId` can only be set when assigning a calling license to a "
    "user. It cannot be changed if a user is already an existing calling user.\n\n"
    "* The `extension` field should be used to update the Webex Calling "
    "extension for a person.")
UPDATE_PERSON_AFTER = (
    "Update details for a person, by ID.\n\n**NOTE**:\n\n"
    "* When assigning a Webex Calling license, either a telephone number or "
    "extension must already be assigned to the person or provided in the "
    "request payload.\n\n"
    "* When `callingData` is set to `true`, a Webex Calling license must be "
    "included in the `licenses` array.\n\n"
    "* The `locationId` can only be set when assigning a calling license to a "
    "user. It cannot be changed if a user is already an existing calling user.\n\n"
    "* The `extension` field should be used to update the Webex Calling "
    "extension for a person.")


def test_case_3_new_api_constraints_in_a_description_fire():
    """update-person gained two rules an admin needs. The CLI structurally
    cannot carry them — openapi_parser reads `summary`, and an operation's
    `description` is rendered nowhere — so their only home is a reference doc.

    ADVISORY on purpose: roughly half the constraint sentences in the worst
    historical refresh are restatements, and deciding which is which is exactly
    the judgement call rule 3 says must not fail a build. It is reported by
    name on every run until the snapshot is refreshed, and the refresh prints
    it, so it cannot vanish unseen."""
    s, f, p = diff(_spec(description=UPDATE_PERSON_BEFORE),
                   _spec(description=UPDATE_PERSON_AFTER))
    assert (s, f) == ([], [])
    assert [r["kind"] for r in p] == ["constraint_changed"]
    assert p[0]["field"] == "(operation)"
    new_rules = set(dc.constraint_sentences(UPDATE_PERSON_AFTER)) - set(
        dc.constraint_sentences(UPDATE_PERSON_BEFORE))
    assert len(new_rules) == 2


def test_case_3_is_invisible_to_the_summary_the_cli_actually_renders():
    """The premise of case 3, asserted rather than assumed: both revisions carry
    the same summary, which is the only prose the generator puts in --help."""
    before = sem(_spec(description=UPDATE_PERSON_BEFORE))
    after = sem(_spec(description=UPDATE_PERSON_AFTER))
    assert (before["webex-probe.json"]["PUT /zzProbe"]["summary"]
            == after["webex-probe.json"]["PUT /zzProbe"]["summary"])


# --------------------------------------------------- check 19 on the live tree

def test_live_snapshot_matches_the_specs_on_disk():
    structural, flips, _ = dc.check_spec_semantics()
    assert structural == [], structural[:5]
    assert flips == [], flips


def test_live_snapshot_is_not_empty():
    """A check reading 0 deserves more suspicion than one reporting many. Pin
    that the snapshot actually covers the surface, so the assertion above
    cannot pass because both sides are empty."""
    snap = dc.load_spec_snapshot()
    ops = sum(len(v) for v in snap["specs"].values())
    fields = sum(len(op["fields"]) for v in snap["specs"].values()
                 for op in v.values())
    assert len(snap["specs"]) == 9, sorted(snap["specs"])
    assert ops > 1800, ops
    assert fields > 10000, fields


def test_live_snapshot_entries_all_parse():
    """Every value is machine-written, so any malformed one is a bug in the
    encoder rather than a hand edit — and would silently disable comparison
    for that field."""
    snap = dc.load_spec_snapshot()
    bad = [(spec, op, f, v)
           for spec, ops in snap["specs"].items()
           for op, rec in ops.items()
           for f, v in rec["fields"].items()
           if dc.decode_field(v)["malformed"] is not None]
    assert bad == [], bad[:5]


def test_dropping_one_snapshot_field_fails_the_gate():
    """Mutation, both directions: the live tree is clean, and a single deleted
    entry is enough to fail it."""
    snap = json.loads(json.dumps(dc.load_spec_snapshot()))
    ops = snap["specs"]["webex-cloud-calling.json"]
    victim = ops["PUT /people/{}/features/callRecording"]["fields"]
    victim.pop("body:selectiveCallRecordingSettings")
    structural, _, _ = dc.check_spec_semantics(snapshot=snap)
    assert [r["kind"] for r in structural] == ["field_added"]
    assert structural[0]["field"] == "body:selectiveCallRecordingSettings"


def test_reverting_a_snapshot_kind_marker_fails_the_gate():
    """The cc-dial-number defect replayed against the real snapshot: put the
    pre-refresh `~name` back and check 19 fires on the live specs."""
    snap = json.loads(json.dumps(dc.load_spec_snapshot()))
    fields = snap["specs"]["webex-contact-center.json"][
        "POST /organization/{}/dial-number"]["fields"]
    fields["body:location"] = fields["body:location"].replace("~id", "~name")
    structural, flips, _ = dc.check_spec_semantics(snapshot=snap)
    assert structural == []
    assert [r["field"] for r in flips] == ["body:location"]


# ----------------------------------------------------------------- check 20

DOCS = {"docs/reference/thing.md": "See `zz-thing` for details.\n"}


def _sets(**kw):
    return kw


def test_fires_on_a_command_set_no_reference_doc_mentions():
    found = dc.check_reference_doc_coverage(
        sets=_sets(zz_other=["zz-other"]), doc_texts=DOCS, declared=set())
    assert [f["groups"] for f in found] == [["zz-other"]]


def test_silent_when_a_reference_doc_backticks_the_group():
    found = dc.check_reference_doc_coverage(
        sets=_sets(zz_thing=["zz-thing"]), doc_texts=DOCS, declared=set())
    assert found == []


def test_silent_when_a_reference_doc_cites_wxcli_group():
    found = dc.check_reference_doc_coverage(
        sets=_sets(zz_other=["zz-other"]),
        doc_texts={"d.md": "run wxcli zz-other list\n"}, declared=set())
    assert found == []


def test_an_alias_counts_as_coverage_for_its_command_set():
    """customer-assist / cx-essentials share one Typer app, and
    call-features-additional.md documents the pair under the alias. Keying on
    the group NAME reports one of them uncovered while the reader is holding
    its documentation."""
    found = dc.check_reference_doc_coverage(
        sets=_sets(zz_thing=["zz-thing", "zz-alias"]),
        doc_texts={"d.md": "use `zz-alias`\n"}, declared=set())
    assert found == []


def test_out_of_scope_declaration_is_the_escape_hatch():
    found = dc.check_reference_doc_coverage(
        sets=_sets(zz_other=["zz-other"]), doc_texts=DOCS,
        declared={"zz-other"})
    assert found == []


def test_out_of_scope_declaration_accepts_a_glob():
    """check 4 matches its declarations with fnmatch; check 20 must read the
    same list the same way or the two disagree about what is declared."""
    found = dc.check_reference_doc_coverage(
        sets=_sets(zz_other=["zz-other"]), doc_texts=DOCS, declared={"zz-*"})
    assert found == []


def test_live_tree_is_covered_not_blind():
    """0 findings today. Assert that is because every set is either documented
    or declared — not because the check cannot see anything."""
    assert dc.check_reference_doc_coverage() == []
    raw = dc.check_reference_doc_coverage(declared=set())
    groups = sorted(g for f in raw for g in f["groups"])
    assert groups == ["broadworks-billing-reports", "broadworks-enterprises",
                      "broadworks-subscribers", "broadworks-workspaces",
                      "cc-legacy-flows", "ucm-profile",
                      "wholesale-billing-reports", "wholesale-provisioning"], groups


def test_command_sets_are_keyed_by_module_and_cover_the_whole_cli():
    sets = dc.command_sets()
    assert len(sets) == dc.distinct_command_sets()
    assert sets["hot_desking_members"] == ["hot-desking-members"]


# ------------------------------------------------------ the refresh contract

def test_a_missing_snapshot_reports_every_spec_rather_than_passing():
    """Fail closed. With nothing recorded, nothing was reviewed — a check that
    treated an absent snapshot as "no deltas" would pass green forever."""
    structural, _, _ = dc.check_spec_semantics(snapshot={})
    assert len(structural) == 9
    assert {r["kind"] for r in structural} == {"spec_added"}


def test_refresh_writes_a_snapshot_that_reads_clean_and_is_idempotent(tmp_path):
    path = tmp_path / "snap.json"
    dc.refresh_spec_snapshot(path)
    first = path.read_text()
    structural, flips, prose = dc.check_spec_semantics(
        snapshot=json.loads(first))
    assert (structural, flips, prose) == ([], [], [])
    dc.refresh_spec_snapshot(path)
    assert path.read_text() == first


def test_refresh_keeps_the_capture_date_when_nothing_moved(tmp_path):
    """`captured` records when the surface last CHANGED, not when someone last
    ran the command — otherwise a no-op refresh writes a diff and the file
    stops meaning anything."""
    path = tmp_path / "snap.json"
    path.write_text(json.dumps({"captured": "1999-01-01",
                                "specs": dc.spec_semantics()}))
    dc.refresh_spec_snapshot(path)
    assert json.loads(path.read_text())["captured"] == "1999-01-01"


def test_check_19_has_no_ack_list():
    """Deliberate: the snapshot is a COMPLETE mirror, re-validated in both
    directions every run, so an entry for a vanished operation is a finding
    rather than a line nobody re-reads. A second ack mechanism layered on top
    would reintroduce exactly the blind spot the snapshot removes."""
    overrides = dc.load_overrides()
    assert "spec_semantics_ack" not in overrides
    assert "ack" not in dc.check_spec_semantics.__code__.co_varnames
