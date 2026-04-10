"""Verify every wxcli cucm command shown in the runbook exists in the CLI.

Doesn't actually invoke the commands (would require AXL, OAuth, etc.) — just
parses --help output to confirm each command name is real.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from .conftest import RUNBOOK_DIR

# Match `wxcli cucm <subcmd>` references in fenced code blocks or inline
COMMAND_RE = re.compile(r"wxcli\s+cucm\s+([a-z][a-z0-9-]*)", re.IGNORECASE)


def _help_text() -> str:
    """Cached output of `wxcli cucm --help`."""
    result = subprocess.run(
        ["wxcli", "cucm", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.fixture(scope="module")
def cucm_help() -> str:
    return _help_text()


@pytest.mark.parametrize(
    "doc_name",
    ["operator-runbook.md", "decision-guide.md", "tuning-reference.md"],
)
def test_cited_commands_exist(doc_name, cucm_help):
    path = RUNBOOK_DIR / doc_name
    text = path.read_text(encoding="utf-8")

    cited = {m.group(1) for m in COMMAND_RE.finditer(text)}
    cited.discard("cucm")  # Self-reference

    failures = []
    for cmd in cited:
        if cmd not in cucm_help:
            failures.append(f"{doc_name}: 'wxcli cucm {cmd}' not in `wxcli cucm --help` output")

    assert not failures, "Cited but missing commands:\n  " + "\n  ".join(failures)


@pytest.mark.parametrize(
    "doc_name",
    ["operator-runbook.md", "decision-guide.md", "tuning-reference.md"],
)
def test_each_cited_command_has_help(doc_name):
    """Beyond top-level existence, run --help for each cited subcommand."""
    path = RUNBOOK_DIR / doc_name
    text = path.read_text(encoding="utf-8")

    cited = {m.group(1) for m in COMMAND_RE.finditer(text)}
    cited.discard("cucm")

    failures = []
    for cmd in cited:
        result = subprocess.run(
            ["wxcli", "cucm", cmd, "--help"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            failures.append(f"{doc_name}: 'wxcli cucm {cmd} --help' exited {result.returncode}")

    assert not failures, "Broken cited commands:\n  " + "\n  ".join(failures)


# Pipeline-stage coverage: the inverse direction.
# Spec acceptance §Cross-reference resolution: "every command shown by
# `wxcli cucm --help` at write time has a section in `operator-runbook.md`
# §Pipeline Walkthrough OR is explicitly listed as 'internal-only, not
# operator-facing' in the runbook intro."

# Internal-only commands: not operator-facing OR documented through a
# different mechanism than `wxcli cucm <cmd>`. Update both this set and
# the relevant runbook section if a new entry lands.
INTERNAL_ONLY_COMMANDS: set[str] = {
    # `wxcli cucm config` is a thin wrapper around <project>/config.json
    # (set + show subcommands). The tuning-reference.md teaches direct
    # config.json editing — operators are expected to edit the file rather
    # than use the wrapper. The wrapper is operationally equivalent but
    # not the documented operator surface.
    "config",
}


def test_every_cucm_command_has_a_runbook_section(cucm_help):
    """For each `wxcli cucm <subcmd>` listed by --help, there must be either
    (a) a §Pipeline Walkthrough subsection with that anchor in any of the 3
    runbook files, (b) a `wxcli cucm <cmd>` body reference in any of the 3
    runbook files, or (c) the command is in the internal-only allowlist.

    Coverage is evaluated across all 3 runbook files (operator-runbook.md,
    decision-guide.md, tuning-reference.md) because the runbook system
    intentionally splits operator-facing material across them — `decide`
    is taught in decision-guide.md and tuning-reference.md while
    `wxcli cucm execute` lives in operator-runbook.md.
    """
    runbook_texts = {
        name: (RUNBOOK_DIR / name).read_text(encoding="utf-8")
        for name in ("operator-runbook.md", "decision-guide.md", "tuning-reference.md")
    }
    runbook_text = "\n\n".join(runbook_texts.values())

    # Parse subcommand names from `wxcli cucm --help` output. Click + rich-click
    # uses unicode box-drawing chars; subcommand rows are `│ <name> <description>`
    # with exactly one space after the box char. Continuation lines have many
    # spaces after the box char and would otherwise false-positive (e.g.,
    # "│                   objects" → "objects").
    cmd_re = re.compile(r"^[│|] ([a-z][a-z0-9-]*) ", re.MULTILINE)
    cli_commands = set(cmd_re.findall(cucm_help))

    # Smoke test: cli_commands should be non-empty. If empty, the regex broke.
    assert cli_commands, (
        "cmd_re matched zero commands in `wxcli cucm --help` output — the regex is wrong "
        "or wxcli changed its --help format. Fix the regex before trusting this test."
    )

    # Extract anchors from all 3 runbook files (combined runbook_text already
    # contains all 3 documents joined with newlines).
    anchor_re = re.compile(r"^#{2,4}\s+(.+?)\s*$", re.MULTILINE)
    runbook_anchors = {
        m.group(1).strip().lower().replace(" ", "-").replace("(", "").replace(")", "")
        for m in anchor_re.finditer(runbook_text)
    }
    # Strip trailing punctuation
    runbook_anchors = {a.rstrip("/").rstrip(".") for a in runbook_anchors}

    # Coverage criterion: a command is "documented" if EITHER (a) the runbook
    # has an anchor containing the command name (including substring/prefix
    # match for compound headings), OR (b) the runbook body text references
    # the command directly as `wxcli cucm <cmd>`. The runbook organizes
    # related commands by lifecycle stage rather than 1:1 by command name
    # (e.g., `decide` is covered under §decisions, `next-batch` and `dry-run`
    # are covered under §plan, recovery commands are covered under
    # §Execution & Recovery), so anchor-only coverage would force unnecessary
    # heading proliferation.
    missing = []
    for cmd in cli_commands:
        if cmd in INTERNAL_ONLY_COMMANDS:
            continue
        anchor_match = any(cmd in a or a.startswith(cmd) for a in runbook_anchors)
        body_match = f"wxcli cucm {cmd}" in runbook_text
        if not (anchor_match or body_match):
            missing.append(cmd)

    assert not missing, (
        f"The runbook system is missing coverage for these wxcli cucm "
        f"commands: {sorted(missing)}. The command must either (a) appear "
        f"as an anchor in any of the 3 runbook files, (b) appear as "
        f"`wxcli cucm <cmd>` in any runbook body, or (c) be added to "
        f"INTERNAL_ONLY_COMMANDS in this test file (with a comment "
        f"explaining the alternative documentation path)."
    )
