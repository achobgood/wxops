"""Drift gate: `operation_overrides` skip / blocked are deliberate gaps (Plan 2 Task 9).

`operation_overrides.<op>.skip` drops an operation before the generator names
anything; `blocked` renders a visible stub that refuses to run and carries no
URL. Either way the operation has no working command ON PURPOSE, so check 1
(spec <-> CLI parity) must not report it missing, and `docs/arch/
deliberate-gaps.md` must say why, under `## <spec> — operation_overrides skip
(<n> ops)`.

Check 15 gains the other direction: an override on an operation the generator
never renders (its tag is skipped, it is a multipart upload, the key no longer
resolves) parses, passes, and does nothing — inert config.

Every module here is produced by the real generator, in a subprocess, from
`tests/wxcc/fixtures/mini_flow_store.json` saved under the Flow Store spec
name. Nothing generated is imported; the checks read it as text.
"""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tools import drift_check

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "mini_flow_store.json"
SPEC_NAME = "webex-cc-flow-store.json"
DELETE_KEY = ("DELETE", "/{}/project/{}/widgets/{}")
IMPORT_KEY = ("POST", "/{}/project/{}/widgets:import")

# Most tests skip importWidget so they render the module set they were
# written against; the multipart tests at the end render it. The purge op
# needs a verb ack to render.
BASE_OVERRIDES = {
    "auto_inject_from_config": ["orgId"],
    "verb_semantics_ack": {SPEC_NAME: {"POST /admin/widgets/purge": "purge"}},
}
IMPORT_SKIP = {"skip": "spaced 'Flow Type' param; Task 14 VERIFY"}
DELETE_SKIP = {"skip": "fate (a): served by cc-flow delete — EQUAL, Plan 2 T5"}
DELETE_BLOCK = {"blocked": "Refused: this PATCH is a measured no-op."}


def _spec() -> dict:
    return json.loads(FIXTURE.read_text())


def _generate(tmp_path: Path, op_overrides: dict, spec: dict | None = None) -> Path:
    """Render every tag of the fixture (or `spec`) with the real generator;
    return the output directory."""
    spec_path = tmp_path / SPEC_NAME
    spec_path.write_text(json.dumps(spec) if spec else FIXTURE.read_text())
    ovr = tmp_path / "gen_overrides.yaml"
    ovr.write_text(yaml.safe_dump(
        {**BASE_OVERRIDES, "operation_overrides": {SPEC_NAME: op_overrides}}))
    out = tmp_path / "out"
    r = subprocess.run(
        [sys.executable, "tools/generate_commands.py", "--spec", str(spec_path),
         "--overrides", str(ovr), "--output", str(out), "--all"],
        cwd=REPO, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(REPO)})
    assert r.returncode == 0, r.stdout + r.stderr
    return out


def _surface(out: Path, monkeypatch) -> dict:
    monkeypatch.setattr(drift_check, "COMMANDS_DIR", out)
    return {p.stem: drift_check.parse_module_commands(p.stem)
            for p in sorted(out.glob("*.py")) if not p.stem.startswith("_")}


def _parity(tmp_path, monkeypatch, rendered_with: dict, gate_reads: dict,
            spec: dict | None = None):
    """Check 1 over modules rendered with `rendered_with`, while the gate
    reads `gate_reads` as the operation_overrides block."""
    surface = _surface(_generate(tmp_path, rendered_with, spec), monkeypatch)
    ops, skipped = drift_check.load_spec_ops(
        {}, specs={SPEC_NAME: spec or _spec()},
        operation_overrides={SPEC_NAME: gate_reads})
    return drift_check.check_parity(surface, ops, skipped, []), skipped


def _gaps(skipped: dict) -> str:
    return drift_check.gaps_doc_text(
        skipped, {"skip_tags": {}, "skip_reasons": {}, "keep_endpoints": []})


# ------------------------------------------------------------ check 1: skip

def test_operation_skip_is_deliberate_not_missing(tmp_path, monkeypatch):
    block = {"importWidget": IMPORT_SKIP, "deleteWidget": DELETE_SKIP}
    parity, skipped = _parity(tmp_path, monkeypatch, block, block)
    assert parity == {"missing_from_cli": [], "cli_ahead_of_spec": []}
    assert skipped[DELETE_KEY][:2] == (SPEC_NAME, "operation_overrides skip")
    text = _gaps(skipped)
    assert f"## {SPEC_NAME} — operation_overrides skip (2 ops)" in text
    assert ("- `DELETE /{}/project/{}/widgets/{}` — fate (a): served by "
            "cc-flow delete — EQUAL, Plan 2 T5") in text
    assert "spaced 'Flow Type' param; Task 14 VERIFY" in text


def test_dropping_a_skip_entry_makes_check_1_fire(tmp_path, monkeypatch):
    # The mutation: the module was rendered WITH the skip, the gate reads a
    # copy of the overrides with that one entry deleted.
    block = {"importWidget": IMPORT_SKIP, "deleteWidget": DELETE_SKIP}
    mutated = copy.deepcopy(block)
    del mutated["deleteWidget"]
    parity, _ = _parity(tmp_path, monkeypatch, block, mutated)
    assert [(m["method"], m["path"]) for m in parity["missing_from_cli"]] == [DELETE_KEY]


# --------------------------------------------- check 1: blocked (T8 Minor 2)

def test_blocked_stub_is_deliberate_not_missing(tmp_path, monkeypatch):
    block = {"importWidget": IMPORT_SKIP, "deleteWidget": DELETE_BLOCK}
    parity, skipped = _parity(tmp_path, monkeypatch, block, block)
    assert parity["missing_from_cli"] == []
    assert skipped[DELETE_KEY][:2] == (SPEC_NAME, "operation_overrides blocked")
    text = _gaps(skipped)
    assert f"## {SPEC_NAME} — operation_overrides blocked (1 ops)" in text
    assert "Refused: this PATCH is a measured no-op." in text


def test_blocked_stub_carries_no_url(tmp_path, monkeypatch):
    # Why blocked must be classified: the stub is a visible command whose
    # body has no request, so the CLI surface maps it to nothing.
    block = {"importWidget": IMPORT_SKIP, "deleteWidget": DELETE_BLOCK}
    surface = _surface(_generate(tmp_path, block), monkeypatch)
    assert surface["widgets"]["delete"] == []


def test_warn_is_not_a_gap(tmp_path, monkeypatch):
    # warn still renders the call, so it covers its op like any command.
    block = {"importWidget": IMPORT_SKIP, "deleteWidget": {"warn": "slow"}}
    parity, skipped = _parity(tmp_path, monkeypatch, block, block)
    assert parity["missing_from_cli"] == []
    assert DELETE_KEY not in skipped


def test_an_unresolvable_block_does_not_crash_check_1():
    # Check 15 reports the resolver's error; check 1 just ignores the block.
    ops, skipped = drift_check.load_spec_ops(
        {}, specs={SPEC_NAME: _spec()},
        operation_overrides={SPEC_NAME: {"noSuchOp": {"skip": "x"}}})
    assert IMPORT_KEY in ops and not skipped


# ------------------------------------------ check 15: inert (T8 Minor 1)

@pytest.fixture
def inert(tmp_path, monkeypatch):
    def run(op_overrides: dict, spec: dict | None = None, **extra) -> list[dict]:
        (tmp_path / SPEC_NAME).write_text(
            json.dumps(spec) if spec else FIXTURE.read_text())
        ovr = tmp_path / "field_overrides.yaml"
        ovr.write_text(yaml.safe_dump({
            **BASE_OVERRIDES, **extra,
            "operation_overrides": {SPEC_NAME: op_overrides}}))
        monkeypatch.setattr(drift_check, "SPECS_DIR", tmp_path)
        monkeypatch.setattr(drift_check, "OVERRIDES", ovr)
        findings, _stale = drift_check.check_inert_overrides()
        return [f for f in findings if f["kind"] == "operation"]
    return run


def test_overrides_on_rendered_ops_are_not_inert(inert):
    assert inert({"importWidget": IMPORT_SKIP, "deleteWidget": DELETE_BLOCK,
                  "findWidgets": {"warn": "slow"},
                  "_all": {"param_help": {"flowType": "FLOW or SUBFLOW"}}}) == []


def test_override_on_an_op_in_a_skipped_tag_is_inert(inert):
    found = inert({"importWidget": IMPORT_SKIP, "purgeWidgets": {"warn": "x"}},
                  skip_tags={SPEC_NAME: ["admin-widget-controller"]})
    assert [(f["tag"], f["detail"]) for f in found] == [
        ("purgeWidgets", "POST /admin/widgets/purge is not rendered by any tag")]


def test_a_skip_on_an_op_that_would_not_render_anyway_is_inert(inert):
    found = inert({"importWidget": IMPORT_SKIP, "purgeWidgets": {"skip": "x"}},
                  skip_tags={SPEC_NAME: ["admin-widget-controller"]})
    assert [f["tag"] for f in found] == ["purgeWidgets"]


def test_override_on_an_excluded_path_is_inert(inert):
    found = inert({"importWidget": IMPORT_SKIP, "removeWidgetTags": {"warn": "x"}},
                  tag_op_excludes={SPEC_NAME: {
                      "WidgetTags": ["/{orgId}/project/{projectId}/widgets/*/tags"]}})
    assert [f["tag"] for f in found] == ["removeWidgetTags"]


def test_an_unresolvable_key_is_a_finding_not_a_crash(inert):
    found = inert({"noSuchOp": {"warn": "x"}})
    assert len(found) == 1
    assert "noSuchOp" in found[0]["detail"]
    assert "no operation has this operationId" in found[0]["detail"]


# ------------- check 15 names commands the way the generator does after a skip
#
# The generator drops skipped ops BEFORE naming: with findWidgets skipped,
# getWidget takes `show` instead of `show-widgets`. Check 15's command-keyed
# reader must derive the same names, or it accepts a key the generator
# rejects and rejects one the generator applies.

@pytest.fixture
def command_keyed(tmp_path, monkeypatch):
    def run(notes: dict) -> list[dict]:
        (tmp_path / SPEC_NAME).write_text(FIXTURE.read_text())
        ovr = tmp_path / "field_overrides.yaml"
        ovr.write_text(yaml.safe_dump({
            **BASE_OVERRIDES,
            "operation_overrides": {SPEC_NAME: {
                "importWidget": IMPORT_SKIP, "findWidgets": {"skip": "x"}}},
            "Widgets": {"command_help_notes": notes}}))
        monkeypatch.setattr(drift_check, "SPECS_DIR", tmp_path)
        monkeypatch.setattr(drift_check, "OVERRIDES", ovr)
        findings, _stale = drift_check.check_inert_overrides()
        return [f for f in findings if f["kind"] == "command"]
    return run


def test_a_key_on_the_name_a_skip_frees_is_live(command_keyed):
    assert command_keyed({"show": "Get one widget."}) == []


def test_a_key_on_the_pre_skip_name_is_inert(command_keyed):
    found = command_keyed({"show-widgets": "Get one widget."})
    assert [f["detail"] for f in found] == ["no command 'show-widgets' in this tag"]


# ---------------- multipart uploads (Task 9b: Task 9 and Task 10 reviews)
#
# An `operation_overrides` `multipart` entry renders an upload as a command
# that calls `rest_post_multipart(...)`. Two spec shapes reach it, both
# measured by the reviews: a JSON-labelled upload (Flow Store
# importFlowVersion_1, like the fixture's own importWidget) and a
# `multipart/form-data` one (CC importFn). For each, the gate must see the
# command, must not list the op as a deliberate gap, and must not call the
# override inert.

MULTIPART = {"multipart": True}
UPLOAD_SHAPES = ["json-labelled", "form-data"]
FORM_DATA_BODY = {"content": {"multipart/form-data": {"schema": {
    "type": "object", "required": ["file"],
    "properties": {"file": {"type": "string", "format": "binary"}}}}}}


def _upload_spec(shape: str) -> dict:
    spec = _spec()
    if shape == "form-data":
        spec["paths"]["/{orgId}/project/{projectId}/widgets:import"]["post"][
            "requestBody"] = copy.deepcopy(FORM_DATA_BODY)
    return spec


@pytest.mark.parametrize("shape", UPLOAD_SHAPES)
def test_rendered_upload_is_on_the_cli_surface(tmp_path, monkeypatch, shape):
    out = _generate(tmp_path, {"importWidget": MULTIPART}, _upload_spec(shape))
    assert "rest_post_multipart(" in (out / "widgets.py").read_text()
    surface = _surface(out, monkeypatch)
    assert surface["widgets"]["create-import"] == [IMPORT_KEY]


@pytest.mark.parametrize("shape", UPLOAD_SHAPES)
def test_rendered_upload_is_covered_not_a_gap(tmp_path, monkeypatch, shape):
    block = {"importWidget": MULTIPART}
    parity, skipped = _parity(tmp_path, monkeypatch, block, block,
                              spec=_upload_spec(shape))
    assert parity == {"missing_from_cli": [], "cli_ahead_of_spec": []}
    assert IMPORT_KEY not in skipped
    assert "[multipart upload]" not in _gaps(skipped)


def test_form_data_upload_without_the_override_is_still_a_gap(tmp_path, monkeypatch):
    # Control: the classification is conditional on the override, not gone.
    block = {"deleteWidget": {"warn": "slow"}}
    parity, skipped = _parity(tmp_path, monkeypatch, block, block,
                              spec=_upload_spec("form-data"))
    assert parity == {"missing_from_cli": [], "cli_ahead_of_spec": []}
    assert skipped[IMPORT_KEY] == (SPEC_NAME, "Widgets [multipart upload]")


@pytest.mark.parametrize("shape", UPLOAD_SHAPES)
def test_multipart_override_on_a_rendered_upload_is_not_inert(inert, shape):
    assert inert({"importWidget": MULTIPART}, spec=_upload_spec(shape)) == []


@pytest.mark.parametrize("shape", UPLOAD_SHAPES)
def test_block_reader_sees_the_upload_call(tmp_path, shape):
    # iter_command_blocks feeds checks 23-33; a URL with no recognised call
    # is a half-parsed block (HELPER_SKIPS), not a command.
    out = _generate(tmp_path, {"importWidget": MULTIPART}, _upload_spec(shape))
    blocks = {b.command: b for b in drift_check.iter_command_blocks(out)
              if b.module == "widgets"}
    assert drift_check.HELPER_SKIPS["blocks"] == []
    assert (blocks["create-import"].method,
            blocks["create-import"].npath) == IMPORT_KEY


@pytest.mark.parametrize("shape", UPLOAD_SHAPES)
def test_command_facts_read_the_upload_url(tmp_path, shape):
    out = _generate(tmp_path, {"importWidget": MULTIPART}, _upload_spec(shape))
    facts = {f.node.name: f for f in drift_check.parse_module_facts(
        "widgets", "widgets", out)}
    assert facts["create_import"].urls == [IMPORT_KEY]
