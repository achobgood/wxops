"""Offline doc-consistency invariants (default suite; no token needed).

These are the Task 9 "final gate": after editing docs they prove the situational
activity index still matches the files on disk. (The byte-identical check on the
frozen wxcc `_playbook` mirror was retired in Plan 3 Task 1; see the end of file.)
Kept OUT of the `live` tier so a plain `pytest` runs them with zero API calls.
"""
from __future__ import annotations

import re
from pathlib import Path

from tests.wxcc.conftest import REPO

ACT_DIR = REPO / "docs" / "reference" / "flow-designer-activities"


def _index_linked_files():
    text = (ACT_DIR / "_index.md").read_text()
    return set(re.findall(r"\]\(([a-z0-9-]+\.md)\)", text))


def test_index_rows_match_files_on_disk():
    linked = _index_linked_files()
    on_disk = {p.name for p in ACT_DIR.glob("*.md") if p.name != "_index.md"}
    missing_file = sorted(linked - on_disk)
    unlisted = sorted(on_disk - linked)
    assert not missing_file, f"_index.md links files that do not exist: {missing_file}"
    assert not unlisted, f"activity files not listed in _index.md: {unlisted}"


# Retired by Plan 3 Task 1 (P3-1): wxcc/src/wxcc_flow/_playbook is frozen and
# nothing ships it; Plan 3 rewrites its source docs in place, so a byte-mirror
# check cannot pass. Replaced in Task 3 by test_wxcc_docs_ship_in_wxcli_bundle,
# which checks the shipped copy, src/wxcli/_playbook.


def test_top_level_reference_docs_pass_shape():
    """Plan 3 Task 2A: wxcc's top-level reference docs meet check 18 (See Also,
    one trailing newline, no dead in-doc anchor). The SDK copy is Task 6's."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "drift_check_for_shape", Path(__file__).resolve().parents[2] / "tools" / "drift_check.py")
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    failures, _ = mod.check_reference_doc_shape(REPO / "docs" / "reference")
    failures = [f for f in failures if not f["file"].endswith("contact-center-agent-sdk.md")]
    assert not failures, failures


def _load_drift_check():
    import importlib.util
    import sys

    name = "drift_check_for_p3_move"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, REPO / "tools" / "drift_check.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_wxcc_docs_ship_in_wxcli_bundle():
    """Replaces test_playbook_mirror_is_byte_identical (Plan 2). Its subject,
    wxcc/src/wxcc_flow/_playbook, is frozen by Plan 3 P3-1; the shipped copy is
    now the wxcli bundle.

    Every doc the bundle ships under src/wxcli/_playbook/docs must exist at the
    same path under docs/ and be byte-identical to it.
    """
    shipped_root = REPO / "src" / "wxcli" / "_playbook" / "docs"
    checked, bad = 0, []
    for shipped in sorted(shipped_root.rglob("*")):
        if not shipped.is_file():
            continue
        rel = shipped.relative_to(shipped_root)
        src = REPO / "docs" / rel
        checked += 1
        if not src.is_file():
            bad.append(f"no source: docs/{rel}")
        elif shipped.read_bytes() != src.read_bytes():
            bad.append(f"differs: docs/{rel}")
    assert checked > 0, "the bundle ships no docs"
    assert not bad, bad[:20]


def test_moved_docs_keep_ref_tags():
    """Proof-of-read tags (Review Focus 4): 89 moved docs keep their
    `<!-- ref-tag: ... -->` line, and the merged SDK doc carries the 90th."""
    import json

    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "plan3_ref_tags.json").read_text())
    assert len(fixture) == 90
    bad = []
    for rel, tag in fixture.items():
        p = REPO / rel
        if not p.is_file():
            bad.append(f"missing: {rel}")
        elif tag not in p.read_text(encoding="utf-8"):
            bad.append(f"tag lost: {rel}")
    assert not bad, bad


def test_rewritten_flow_commands_keep_wxcc_defaults():
    """Review Focus 1: a rewritten flow command must keep what wxcc's did.
    cc-flow export gives the published version unless --version is passed;
    cc-flow publish validates unless --skip-validation; cc-flow delete takes
    the server's --force unless told."""
    import subprocess

    mod = _load_drift_check()
    wxcc_skills = ("build-action", "build-digital-inbound", "build-flow-designer",
                   "build-flow-programmatic", "build-notification",
                   "build-outbound-flow", "build-scripted-fulfillment",
                   "build-solution-docs", "build-spec-diagram",
                   "configure-ai-agent", "configure-scripted-agent", "design-flow",
                   "design-scripted-agent", "wxcc-debug")
    roots = ("docs/reference", "docs/playbooks", "docs/templates",
             "docs/examples",
             ".claude/rules/doc-placement.md",
             ".claude/rules/flowir-mcp-verification.md",
             ".claude/rules/large-operation-batching.md",
             *(f".claude/skills/{n}" for n in wxcc_skills))
    files = [f for f in subprocess.check_output(
        ["git", "ls-files", *roots], cwd=REPO, text=True).splitlines()
        if f.endswith(".md")]
    assert files
    assert ".claude/skills/build-flow-programmatic/SKILL.md" in files
    legacy, export, publish, delete = [], [], [], []
    for rel in files:
        text = (REPO / rel).read_text(encoding="utf-8")
        lines = text.splitlines()
        for lineno, span in mod.code_spans(text):
            for m in mod.LEGACY_CLI_TOKEN.finditer(span):
                legacy.append(f"{rel}:{lineno} {m.group(0)}")
            where = f"{rel}:{lineno}"
            if "cc-flow export " in span and "--version" not in span:
                export.append(where)
            if "cc-flow publish " in span and "--skip-validation" not in span:
                near = " ".join(lines[max(lineno - 1, 0):lineno + 3]).lower()
                if "validat" not in near:
                    publish.append(where)
            if ("cc-flow delete " in span and "--force yes" not in span
                    and "--force no" not in span):
                delete.append(where)
    assert not legacy, legacy[:20]
    assert not export, ("cc-flow export without --version", export[:20])
    assert not publish, ("cc-flow publish without --skip-validation", publish[:20])
    assert not delete, ("cc-flow delete without --force yes|no", delete[:20])
