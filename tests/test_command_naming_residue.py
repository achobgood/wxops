"""Guards for the three naming-residue fixes landed 2026-07-29.

All three shared one failure mode: the command ran, exited 0, returned plausible
data, and answered a different question than the one asked. Each test below is
paired -- a does-fire case and a does-not-fire case -- because the check-9 suite
once had 6 of 8 cases passing without ever reaching the code they tested.

Deliberately free of any tests/conftest.py dependency so it can be tracked.
"""
from __future__ import annotations

import collections
import re
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
COMMANDS = REPO / "src" / "wxcli" / "commands"
SPECS = REPO / "specs"

DECORATOR = re.compile(
    r'@app\.command\("([^"]+)"(, hidden=True)?'
    r'(?:, short_help="((?:[^"\\]|\\.)*)")?\)'
)
QUALIFIER = re.compile(
    r" \((Calling|Devices|Messaging|Meetings|Admin|Contact Center|UCM"
    r"|BroadWorks|Wholesale)\)$"
)


def _modules():
    return [f for f in sorted(COMMANDS.glob("*.py")) if not f.name.startswith("_")]


def _decorators(path: Path):
    """(command_name, is_hidden, short_help) for one module."""
    return [(m.group(1), bool(m.group(2)), m.group(3))
            for m in DECORATOR.finditer(path.read_text())]


def _visible_help(group_stem: str) -> dict[str, str | None]:
    return {n: h for n, hid, h in _decorators(COMMANDS / f"{group_stem}.py")
            if not hid}


# ---------------------------------------------------------------------------
# 1. cc-agents list returned agent ACTIVITIES, not the roster
# ---------------------------------------------------------------------------

def test_cc_agents_has_no_bare_list_and_activities_is_named_for_itself():
    decs = _decorators(COMMANDS / "cc_agents.py")
    visible = {n for n, hid, _ in decs if not hid}
    hidden = {n for n, hid, _ in decs if hid}
    assert "list" not in visible, (
        "a bare `list` is back in cc-agents; the roster is `cc-users list`, so "
        "any bare `list` here answers a different question with exit 0"
    )
    assert "list-activities" in visible
    assert "list" in hidden, "the old name must keep working as a hidden alias"


def test_cc_users_list_is_reachable_as_the_roster():
    """The command the docs now point at must exist -- a doc fix that cites a
    non-existent command is worse than the trap it replaces."""
    assert "list" in _visible_help("cc_users")


# ---------------------------------------------------------------------------
# 2. teams list and cc-team list carried byte-identical help
# ---------------------------------------------------------------------------

def test_teams_and_cc_team_list_no_longer_share_help():
    teams = _visible_help("teams")["list"]
    cc_team = _visible_help("cc_team")["list"]
    assert teams != cc_team, "the collision this fix exists for is back"
    assert teams == "List Teams. (Messaging)"
    assert cc_team == "List Teams. (Contact Center)"


def test_no_short_help_is_shared_across_products():
    """The general invariant, not just the two commands that surfaced it."""
    from tools.command_renderer import build_producer_index

    index = build_producer_index()
    product = index["group_product"]
    shared = collections.defaultdict(set)
    for path in _modules():
        for name, hidden, help_text in _decorators(path):
            if hidden or not help_text:
                continue
            shared[help_text].add(path.stem.replace("_", "-"))
    offenders = {
        h: groups for h, groups in shared.items()
        if len({product[g] for g in groups if g in product}) > 1
    }
    assert not offenders, f"short_help shared across products: {offenders}"


def test_every_cross_product_summary_is_actually_qualified():
    """The test above only catches an IDENTICAL pair, so it stays green if just
    one side loses its qualifier (proven by mutation: stripping `(Messaging)`
    from `teams list` alone leaves it passing). This one asks the index which
    summaries must be qualified and checks each one was, which catches that."""
    from tools.command_renderer import build_producer_index

    index = build_producer_index()
    product = index["group_product"]
    expected = {
        summary for summary, groups in index["summary_groups"].items()
        if len({product[g] for g in groups if g in product}) > 1
    }
    assert expected, "the collision index is empty -- it is not being built"
    missing = []
    for path in _modules():
        group = path.stem.replace("_", "-")
        if group not in product:
            continue
        for name, hidden, help_text in _decorators(path):
            if hidden or not help_text:
                continue
            bare = QUALIFIER.sub("", help_text)
            if bare in expected and not QUALIFIER.search(help_text):
                missing.append(f"{group} {name}: {help_text!r}")
    assert not missing, f"cross-product summaries shipped unqualified: {missing}"


def test_same_product_collisions_are_deliberately_left_unqualified():
    """The paired does-NOT-fire case. `my-call-settings` and `user-settings` are
    both Calling and both describe voicemail settings identically; a product
    label there would be noise, so the rule must not fire on it."""
    mine = _visible_help("my_call_settings")["show-voicemail-settings"]
    admin = _visible_help("user_settings")["show-voicemail"]
    assert mine == admin == "Read Voicemail Settings for a Person."
    assert not QUALIFIER.search(mine)


def test_dev_only_flow_store_contributes_no_qualifier():
    """fs-* modules are gitignored and absent from a fresh clone, so letting
    webex-flow-store.json into the collision index would make generated help
    differ between this machine and a clone -- drift check 8's premise."""
    from tools.command_renderer import SPEC_PRODUCT

    assert SPEC_PRODUCT["webex-flow-store.json"] is None
    for path in COMMANDS.glob("fs_*.py"):
        for name, hidden, help_text in _decorators(path):
            if help_text:
                assert not QUALIFIER.search(help_text), f"{path.stem} {name}"


def test_every_spec_on_disk_declares_a_product():
    from tools.command_renderer import SPEC_PRODUCT

    on_disk = {p.name for p in SPECS.glob("webex-*.json")
               if not p.name.endswith(".overlay.json")}
    missing = sorted(on_disk - set(SPEC_PRODUCT))
    assert not missing, (
        f"specs with no SPEC_PRODUCT entry: {missing}. Without one they cannot "
        f"silently inherit the dev-only exemption -- name the product."
    )


def test_unknown_spec_raises_rather_than_being_skipped(tmp_path):
    """Mutation-proven both ways: absent entry raises, present entry does not."""
    import tools.command_renderer as cr

    probe = tmp_path / "specs"
    probe.mkdir()
    shutil.copy(SPECS / "webex-ucm.json", probe / "webex-probe.json")
    cr._producer_index = None
    try:
        with pytest.raises(cr.UnknownSpecProductError):
            cr.build_producer_index(probe)
        cr.SPEC_PRODUCT["webex-probe.json"] = "Probe"
        cr._producer_index = None
        cr.build_producer_index(probe)          # control: no raise
    finally:
        cr.SPEC_PRODUCT.pop("webex-probe.json", None)
        cr._producer_index = None


def test_normalise_summary_matches_what_the_decorator_emits():
    """If these two drift the index keys on one string and the emitter ships
    another, and every qualifier silently disappears."""
    from tools.command_renderer import _normalise_summary

    assert _normalise_summary("  List   Teams  ") == "List Teams."
    assert _normalise_summary("List Teams.") == "List Teams."
    assert _normalise_summary("") == ""
    assert _normalise_summary(None) == ""


# ---------------------------------------------------------------------------
# 3. call-settings-for-me-phase-5 was a build-milestone label as a command path
# ---------------------------------------------------------------------------

def test_phase_5_group_is_gone():
    from wxcli.commands._registry import GENERATED_GROUPS

    groups = {g for _, g in GENERATED_GROUPS}
    assert "call-settings-for-me-phase-5" not in groups
    assert not (COMMANDS / "call_settings_for_me_phase_5.py").exists()


def test_phase_5_operations_landed_in_my_call_settings_named_for_their_resource():
    visible = _visible_help("my_call_settings")
    for name, expected in [
        ("show-personal-assistant", "Get Personal Assistant Settings."),
        ("update-personal-assistant", "Update Personal Assistant Settings."),
        ("show-voicemail-rules", "Get Person's Voicemail Rules."),
        ("update-voicemail-pin", "Update Voicemail PIN."),
        ("show-hoteling-guest", "Get Hoteling Guest Settings."),
        ("update-hoteling-guest", "Update Hoteling Guest Settings."),
        ("list-available-hosts", "Get Available Hoteling Hosts."),
    ]:
        assert visible.get(name) == expected, name


def test_the_merge_did_not_repurpose_the_bare_names():
    """The whole reason the fold needed pinning. Unpinned, `show` and `update`
    move from preferredAnswerEndpoint to personalAssistant -- both read fine and
    both answer a different question."""
    visible = _visible_help("my_call_settings")
    assert visible["show"] == "Get Preferred Answer Endpoint."
    assert visible["update"] == "Modify Preferred Answer Endpoint."
    assert visible["list"] == "Get List Available Preferred Answer Endpoints."
    # And the secondaryLines pair kept the names the skill cites.
    assert "show-preferred-answer-endpoint" in visible
    assert "update-preferred-answer-endpoint" in visible


def test_no_hidden_alias_shadows_a_visible_command():
    """Registering one name twice on a Typer app makes the last decorator win,
    so an alias that collides silently repurposes the command it lands on.
    generate_commands.py suppresses those; this asserts the result tree-wide."""
    for path in _modules():
        counts = collections.Counter(n for n, _, _ in _decorators(path))
        dupes = {n: c for n, c in counts.items() if c > 1}
        assert not dupes, f"{path.name} registers {dupes} more than once"
