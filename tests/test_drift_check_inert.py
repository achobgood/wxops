"""Drift gate check 15: override config in field_overrides.yaml that cannot apply.

The quietest defect in that file. A tag block keyed on a tag no spec declares, a
per-command key naming a command its tag does not render, or a family declared in
both a top-level block and a `tag_overrides` entry: each parses, passes every
other test, and does nothing. Six blocks were inert that way from whenever they
were written until 2026-07-29 — and the shadowed-block class was, by accident,
the only thing holding check 9 at 0 on call-queue, so "the gate is green" was
itself downstream of the bug.

Every case here is written so the check can FAIL it. The paired
does-not-fire/does-fire assertions matter more than usual: a check that reads 0
because it is looking at nothing is indistinguishable from a clean tree, which is
exactly how these six survived.
"""

import json
import textwrap

import pytest
import yaml

from tools import drift_check


TAG = "Probe Tag"
OTHER_TAG = "Probe Tag Two"


def _spec(tags=(TAG,), extra_paths=None):
    """A spec whose every tag renders exactly one `list` command."""
    paths = {}
    for i, tag in enumerate(tags):
        paths[f"/v1/zzProbe{i}"] = {"get": {
            "tags": [tag],
            "summary": f"List {tag}.",
            "responses": {"200": {"content": {"application/json": {"schema": {
                "type": "object", "properties": {"items": {
                    "type": "array", "items": {"type": "object", "properties": {
                        "id": {"type": "string"}}}}}}}}}},
        }}
    paths.update(extra_paths or {})
    return {"openapi": "3.0.0", "info": {"title": "probe", "version": "1"},
            "paths": paths}


@pytest.fixture
def check(tmp_path, monkeypatch):
    """Run check 15 over a fixture overrides file and fixture specs on disk.

    SPECS_DIR and OVERRIDES are both module constants the check reads directly,
    so patching them redirects it entirely into tmp_path — no repo file is read
    and no repo state can make a case pass vacuously.
    """
    def run(overrides: dict, specs: dict | None = None):
        specs = specs if specs is not None else {"probe.json": _spec()}
        for name, body in specs.items():
            (tmp_path / name).write_text(json.dumps(body))
        ovr_path = tmp_path / "field_overrides.yaml"
        ovr_path.write_text(yaml.safe_dump(overrides, sort_keys=False))
        monkeypatch.setattr(drift_check, "SPECS_DIR", tmp_path)
        monkeypatch.setattr(drift_check, "OVERRIDES", ovr_path)
        return drift_check.check_inert_overrides()

    return run


def _kinds(findings):
    return [(f["kind"], f["tag"]) for f in findings]


# ── the check can see a clean tree ───────────────────────────────────────────


def test_a_block_on_a_real_tag_is_not_flagged(check):
    findings, stale = check({TAG: {"table_columns": {"list": [["ID", "id"]]}}})
    assert findings == []
    assert stale == []


def test_a_command_key_naming_a_rendered_command_is_not_flagged(check):
    """Paired with the next test: proves the probe really renders `list`, so a
    passing result below means the key matched, not that nothing was inspected."""
    findings, _ = check({TAG: {"table_columns": {"list": [["ID", "id"]]}}})
    assert findings == []


# ── tag-keyed config that cannot resolve ─────────────────────────────────────


def test_flags_a_top_level_block_on_an_unknown_tag(check):
    findings, _ = check({"No Such Tag": {"table_columns": {"list": []}}})
    assert _kinds(findings) == [("tag", "No Such Tag")]
    assert findings[0]["where"] == "top-level block"


def test_flags_a_block_keyed_on_the_pre_merge_tag_name(check):
    """tag_merge folds source tags into the merged name BEFORE overrides
    resolve, so a block keyed on a source is inert. Three of the 26 Wave 3
    renames shipped in exactly this state."""
    findings, _ = check(
        {"tag_merge": {"_global": {"Merged Probe": [TAG]}},
         TAG: {"table_columns": {"list": []}}})
    assert _kinds(findings) == [("tag", TAG)]


def test_the_merged_name_is_what_resolves(check):
    findings, _ = check(
        {"tag_merge": {"_global": {"Merged Probe": [TAG]}},
         "Merged Probe": {"table_columns": {"list": []}}})
    assert findings == []


def test_flags_a_block_on_a_skipped_tag(check):
    """A skipped tag generates nothing, so a block for it is inert even though
    the tag exists in the spec."""
    findings, _ = check({"skip_tags": {"_global": [TAG]},
                         TAG: {"table_columns": {"list": []}}})
    assert _kinds(findings) == [("tag", TAG)]


def test_flags_cli_name_overrides_on_an_unknown_tag(check):
    """The live instance: `Features: Customer Experience Essentials` still
    mapped to a CLI name after upstream renamed the tag."""
    findings, _ = check({"cli_name_overrides": {"_global": {"Gone Tag": "gone"}}})
    assert _kinds(findings) == [("tag", "Gone Tag")]
    assert findings[0]["detail"] == "-> 'gone'"


def test_flags_tag_overrides_on_a_tag_that_spec_does_not_declare(check):
    findings, _ = check(
        {"tag_overrides": {"probe.json": {"Absent": {"command_name_overrides": {}}}}})
    assert _kinds(findings) == [("tag", "Absent")]


def test_a_section_for_a_spec_not_on_disk_is_out_of_scope(check):
    """webex-flow-store.json is untracked and absent from a fresh clone. Its
    entries are not inert there — they are simply not in play, and reading them
    as defects would make the check fail on a clean checkout."""
    findings, _ = check(
        {"tag_overrides": {"absent-spec.json": {"Whatever": {"table_columns": {}}}},
         "cli_name_overrides": {"absent-spec.json": {"Whatever": "whatever"}}})
    assert findings == []


# ── command-keyed config that cannot resolve ─────────────────────────────────


def test_flags_a_per_command_key_naming_no_command(check):
    findings, _ = check({TAG: {"table_columns": {"list-nope": [["ID", "id"]]}}})
    assert _kinds(findings) == [("command", TAG)]
    assert findings[0]["detail"] == "no command 'list-nope' in this tag"


def test_flags_every_command_keyed_family_not_just_table_columns(check):
    """command_name_overrides had this guard since 2026-07-27; the other nine
    families did not, and three of them had a live stale key."""
    findings, _ = check({TAG: {"response_list_keys": {"list-nope": "items"},
                               "make_optional": {"list-nope": ["x"]}}})
    assert {f["where"] for f in findings} == {"response_list_keys", "make_optional"}


def test_a_key_on_the_pre_rename_name_is_inert(check):
    """Overrides are applied by the name the command SHIPS under. The hidden
    alias still answers to the old name, which is exactly why keying an override
    on it looks reasonable and does nothing."""
    findings, _ = check({TAG: {"command_name_overrides": {"list": "list-probes"},
                               "table_columns": {"list": [["ID", "id"]]}}})
    assert _kinds(findings) == [("command", TAG)]
    findings, _ = check({TAG: {"command_name_overrides": {"list": "list-probes"},
                               "table_columns": {"list-probes": [["ID", "id"]]}}})
    assert findings == []


# ── the shallow-merge clash ──────────────────────────────────────────────────


def test_flags_one_family_declared_in_both_forms(check):
    """The original defect one level down: the merge is shallow, so the
    tag_overrides copy wins and the top-level one is dropped whole."""
    findings, _ = check(
        {TAG: {"table_columns": {"list": [["ID", "id"]]}},
         "tag_overrides": {"probe.json": {
             TAG: {"table_columns": {"list": [["Other", "id"]]}}}}})
    assert ("clash", TAG) in _kinds(findings)


def test_different_families_in_the_two_forms_merge_cleanly(check):
    findings, _ = check(
        {TAG: {"table_columns": {"list": [["ID", "id"]]}},
         "tag_overrides": {"probe.json": {
             TAG: {"command_name_overrides": {"list": "list-probes"}}}}})
    assert [f for f in findings if f["kind"] == "clash"] == []


# ── acknowledgements, and their expiry ───────────────────────────────────────


def test_an_ack_suppresses_a_tag_finding(check):
    findings, stale = check({"inert_tag_ack": {"Gone Tag": "removed upstream"},
                             "cli_name_overrides": {"_global": {"Gone Tag": "gone"}}})
    assert findings == []
    assert stale == []


def test_an_ack_whose_tag_resolves_again_is_stale(check):
    """The ack list cannot decay into an allowlist: when the tag comes back, the
    ack fails instead of sitting there excusing nothing."""
    findings, stale = check({"inert_tag_ack": {TAG: "acked but present"},
                             TAG: {"table_columns": {"list": [["ID", "id"]]}}})
    assert findings == []
    assert [s["tag"] for s in stale] == [TAG]


def test_an_ack_never_suppresses_a_command_finding(check):
    """Acks are about tags. A stale per-command key is always a defect — there is
    no dormant-because-upstream story for a command name inside a live tag."""
    findings, _ = check({"inert_tag_ack": {TAG: "acked"},
                         TAG: {"table_columns": {"list-nope": []}}})
    assert _kinds(findings) == [("command", TAG)]


# ── the real file ────────────────────────────────────────────────────────────


def test_the_shipped_overrides_file_has_no_inert_config():
    """Not a unit test — the live tree. Reads 0 as of 2026-07-29, after six
    shadowed blocks, five stale tag keys and three stale command keys were
    resolved."""
    findings, stale = drift_check.check_inert_overrides()
    assert findings == [], f"inert override config: {findings}"
    assert stale == [], f"stale inert_tag_ack entries: {stale}"
