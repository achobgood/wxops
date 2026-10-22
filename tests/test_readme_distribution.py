import re
from pathlib import Path

README = (Path(__file__).resolve().parent.parent / "README.md").read_text()


def test_trademark_disclaimer_present():
    assert "Unofficial community CLI — not affiliated with or endorsed by Cisco." in README


def test_pipx_install_is_the_lead():
    assert "pipx install wxcli" in README
    assert "pip install wxcli" in README


# test_from_source_subsection_retained removed: f28624b deliberately dropped the
# "From source" clone section so pipx install -> wxcli init is the only onramp.
# The test asserted the section was *retained*; its premise was reversed on
# purpose, so there is nothing left for it to guard.


def test_updating_section_exists():
    assert "## Updating" in README
    assert "wxcli update" in README
    assert "--check" in README
    # --migrate is intentionally undocumented here: it migrates a source/clone
    # install to pipx, and f28624b removed the source path from the README. The
    # flag still exists in update.py for anyone who already has a clone.


# Plan 6 Task 1: the README opens per spec §2 and states the §8 MCP rule.
# SETUP_HEADING is the one section where a person types commands (install,
# init, the token paste); every `wxcli configure` must sit inside it.
SETUP_HEADING = "## Setup — the only commands you type"


def test_readme_opens_per_spec_2():
    order = [
        "# Webex Ops",
        "You never type a command",
        "Unofficial community CLI — not affiliated with or endorsed by Cisco.",
        "Why commands, not MCP",
        "pipx install wxcli",
    ]
    positions = [README.index(s) for s in order]
    assert positions == sorted(positions), list(zip(order, positions))
    assert README.index("You never type a command") < 1500


def test_readme_hands_no_command_outside_setup():
    # The `/agents` slash command, not a path such as `.claude/agents/`.
    assert re.findall(r"(?<![\w.])/agents\b", README) == []
    start = README.index(SETUP_HEADING)
    end = README.index("\n## ", start + len(SETUP_HEADING))
    outside = [README.count("\n", 0, m.start()) + 1
               for m in re.finditer(r"wxcli configure", README)
               if not start < m.start() < end]
    assert outside == [], f"README lines outside {SETUP_HEADING!r}: {outside}"


def test_readme_mcp_claim_is_dated():
    assert "load eagerly, every turn" not in README
    assert "2026-06-30" in README
    for s in ("writes included", "tested live", "same or fewer tokens"):
        assert s in README, s
