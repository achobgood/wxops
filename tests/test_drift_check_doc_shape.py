"""Drift gate check 18: structural conformance of docs/reference/**.

Checks 2/6/7/10/11 read a reference doc only as a carrier of wxcli commands.
Nothing read it as a DOCUMENT — so devices-core.md shipped a contents list
pointing at `#5-raw-http` and `#6-gotchas` while the headings had long since
become `## 6.` and `## 7.`, and four links landed nowhere with every check
reporting the file clean. It was hand-repaired once (a016cea) and drifted
straight back, which is why the rule now belongs to a machine.

Every case below is written so the check can FAIL it, and the gated rules are
paired does-not-fire / does-fire. A check reading 0 because it is looking at
nothing is indistinguishable from a clean tree — that is how the six inert
override blocks behind check 15 survived for months.

The live-tree test at the bottom pins the real docs at 0 GATED findings, so
this suite cannot pass while the thing it protects is broken.
"""

import pytest

from tools import drift_check


# A minimal doc that satisfies every gated rule. Written as a string rather
# than copied off disk so an edit to a real doc cannot quietly change what this
# suite believes a conforming document looks like.
CLEAN = """# Probe Doc

Intro line.

## Sources

- OpenAPI spec: `specs/webex-probe.json`

## Table of Contents

1. [First Thing](#1-first-thing)
2. [Gotchas](#gotchas)

## 1. First Thing

Body.

## Gotchas

1. **Something.** Detail.

## See Also

- [Other](other.md)
"""


@pytest.fixture
def docs(tmp_path):
    """Writer returning check_reference_doc_shape() over a temp doc tree."""
    root = tmp_path / "reference"
    root.mkdir()

    def run(**files):
        for name, text in files.items():
            (root / name.replace("_", "-")).write_text(text)
        return drift_check.check_reference_doc_shape(reference_dir=root)

    return run


# ------------------------------------------------------------- the control

def test_silent_on_a_conforming_doc(docs):
    """The control. Without it every assertion below could pass for the wrong
    reason — a check that fires on any document at all."""
    failures, advisories = docs(**{"probe.md": CLEAN})
    assert failures == []
    assert advisories == []


# ------------------------------------------------- gated rule: dead anchors

def test_fires_on_an_anchor_matching_no_heading(docs):
    """The rule with teeth, and the exact devices-core.md defect: a contents
    entry that survives a heading renumber and silently points nowhere."""
    broken = CLEAN.replace("[First Thing](#1-first-thing)",
                           "[First Thing](#2-first-thing)")
    failures, _ = docs(**{"probe.md": broken})
    assert [f["kind"] for f in failures] == ["dead anchor"]
    assert "#2-first-thing" in failures[0]["detail"]
    # The contents entry, not the heading — a dead link is reported where the
    # link is, so a repair lands on the line that needs editing.
    assert failures[0]["line"] == 11


def test_reports_every_dead_anchor_not_just_the_first(docs):
    """devices-core.md had four. Stopping at the first would have left three
    live after a repair that looked complete."""
    broken = CLEAN.replace("#1-first-thing", "#nope-one").replace(
        "#gotchas", "#nope-two")
    failures, _ = docs(**{"probe.md": broken})
    assert len(failures) == 2, failures


def test_an_anchor_inside_a_fenced_block_is_sample_text_not_a_link(docs):
    """Fences must be stripped before harvesting links. A doc demonstrating
    markdown syntax would otherwise fail on its own example."""
    fenced = CLEAN.replace("Body.", "```md\n[see](#not-a-real-heading)\n```")
    failures, _ = docs(**{"probe.md": fenced})
    assert failures == []


def test_a_hash_comment_in_a_bash_block_is_not_a_heading(docs):
    """The inverse, and the reason the fence stripper is load-bearing in both
    directions: every reference doc is full of `# comment` lines inside bash
    examples, and counting those as headings would mint anchors that do not
    exist and hide real dead links."""
    fenced = CLEAN.replace("Body.", "```bash\n# First Thing\nwxcli x y\n```")
    failures, _ = docs(**{"probe.md": fenced.replace("#1-first-thing",
                                                     "#first-thing")})
    assert [f["kind"] for f in failures] == ["dead anchor"]


def test_a_repeated_heading_gets_githubs_numbered_suffix(docs):
    """GitHub mints `slug`, `slug-1`, `slug-2` for repeated heading text. A
    slugger that did not would fail a doc whose links are correct."""
    dup = CLEAN.replace("## 1. First Thing",
                        "## Notes\n\nA.\n\n## Notes").replace(
        "1. [First Thing](#1-first-thing)", "1. [Second Notes](#notes-1)")
    failures, _ = docs(**{"probe.md": dup})
    assert failures == []


# --------------------------------------------- gated rule: trailing newline

def test_fires_on_extra_trailing_newlines(docs):
    failures, _ = docs(**{"probe.md": CLEAN + "\n\n\n"})
    assert [f["kind"] for f in failures] == ["trailing newlines"]
    assert "4 newline(s)" in failures[0]["detail"]


def test_fires_on_a_missing_trailing_newline(docs):
    failures, _ = docs(**{"probe.md": CLEAN.rstrip("\n")})
    assert [f["kind"] for f in failures] == ["trailing newlines"]
    assert "0 newline(s)" in failures[0]["detail"]


# ------------------------------------------------ gated rule: See Also exists

def test_fires_when_see_also_is_absent(docs):
    """See Also is how the Sync Protocol in tools/CLAUDE.md tells a maintainer
    to find the related doc. A doc without one is a dead end."""
    failures, _ = docs(**{"probe.md": CLEAN.replace("## See Also", "## Links")})
    assert [f["kind"] for f in failures] == ["missing section"]


# ---------------------------------------------------------------- advisories

def test_see_also_not_last_is_advisory_never_gated(docs):
    """call-features-major.md legitimately ends with migration notes. Failing
    that would be a gate failing on a judgement call."""
    trailing = CLEAN + "\n## Migration Notes\n\nDetail.\n"
    failures, advisories = docs(**{"probe.md": trailing})
    assert failures == []
    assert any("not the last section" in a["detail"] for a in advisories)


@pytest.mark.parametrize("drop,phrase", [
    ("## Sources", "no `## Sources` section"),
    ("## Gotchas", "no `## Gotchas` section"),
    ("## Table of Contents", "no contents list"),
])
def test_missing_conventional_sections_are_advisory(docs, drop, phrase):
    """Each has real exceptions on disk — a doc may have no gotchas to record,
    and a short one needs no contents list."""
    text = CLEAN.replace(drop, "## Something Else")
    if drop == "## Table of Contents":
        text = text.replace("1. [First Thing](#1-first-thing)\n", "").replace(
            "2. [Gotchas](#gotchas)\n", "")
    if drop == "## Gotchas":
        # Renaming the heading orphans the contents entry pointing at it. Drop
        # that too, or this case fails on the dead anchor and never reaches the
        # advisory it exists to assert.
        text = text.replace("2. [Gotchas](#gotchas)\n", "")
    failures, advisories = docs(**{"probe.md": text})
    assert failures == []
    assert any(phrase in a["detail"] for a in advisories)


# ------------------------------------------------------------- the exemptions

@pytest.mark.parametrize("name", sorted(drift_check.NON_REFERENCE_DOCS))
def test_non_reference_files_are_exempt(docs, name):
    """CLAUDE.md, TODO.md and the migration spec TEMPLATE live in the same
    directory and are not API reference docs. Holding them to the shape rules
    would force a fake See Also onto a TODO list."""
    failures, advisories = docs(**{name.replace("-", "_"): "# Not a ref doc\n\n\n"})
    assert failures == []
    assert advisories == []


# ---------------------------------------------------------------- live tree

def test_live_tree_has_no_gated_findings():
    """Pins the real docs/reference/** at 0 GATED findings. Without this the
    suite could pass green over a tree with four dead anchors in it — which is
    exactly the state this check was written to end."""
    failures, _ = drift_check.check_reference_doc_shape()
    assert failures == [], failures
