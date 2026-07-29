"""The gate must see the whole CLI surface, including the parts main.py no
longer mounts itself.

Regression cover for a failure that looked like a catastrophe and was actually
the gate going blind. Lazy-loading (2026-07-27) moved every
`app.add_typer(...)` call out of main.py and into commands/_lazy.py. The gate
found the hand-written seams and the aliases by regex-matching those literal
call sites in main.py, so it stopped seeing 5 groups and 3 aliases at once:

    178 command sets -> 173, and check 2 reported 274 dead references
    (`wxcli configure`, `wxcli cucm`, `wxcli cleanup`, `wxcli users`, ...)

Every one of those commands worked perfectly the entire time — verified by
building the click command tree directly, which listed all 197 top-level
commands. Only the parser was wrong.

The lesson these tests encode: the gate reads DECLARATIONS
(`HAND_WRITTEN_GROUPS`, `ALIASES`), not call syntax. A list of tuples cannot
drift from the mounting order the way a regex over call sites can.
"""

import pytest

from tools import drift_check


# The 5 hand-written seams are not generated, so nothing in _registry.py
# mentions them; if the gate cannot see them, every `wxcli <seam> ...`
# citation across the skills and docs becomes a phantom dead reference.
HAND_WRITTEN = ["configure", "cucm", "cleanup", "org-health", "update"]

# An alias is a second top-level name for an already-registered group. It
# resolves to the SAME module as its base, which is what makes check 2 accept
# `wxcli users people list` and check 3 exclude it from the group count.
ALIASES = {"users": "people", "licenses-api": "licenses",
           "cx-essentials": "customer_assist"}


@pytest.fixture(autouse=True)
def _reset_caches():
    drift_check._MODULE_STATE = None
    drift_check._IGNORE_CACHE.clear()
    yield
    drift_check._MODULE_STATE = None
    drift_check._IGNORE_CACHE.clear()


@pytest.mark.parametrize("group", HAND_WRITTEN)
def test_hand_written_seams_are_registered(group):
    assert group in drift_check.parse_registrations(), (
        f"{group!r} vanished from the gate's view of the CLI. It is declared in "
        f"commands/_lazy.py HAND_WRITTEN_GROUPS. If mounting moved again, point "
        f"parse_registrations at the new declaration — do not regex call sites."
    )


@pytest.mark.parametrize("alias,base_module", sorted(ALIASES.items()))
def test_aliases_resolve_to_their_base_module(alias, base_module):
    assert drift_check.parse_registrations().get(alias) == base_module


def test_alias_never_counts_as_its_own_command_set():
    """Aliases share a Typer app, so they are extra NAMES, not extra groups.
    Counting them would inflate the published 'N command groups' claim that
    check 3 verifies against CLAUDE.md and README.md."""
    reg = drift_check.parse_registrations()
    assert len(reg) - drift_check.distinct_command_sets() == len(ALIASES)


def test_the_surface_is_not_silently_smaller_than_the_manifest():
    """The generated manifest is the floor: every _registry.py entry plus the
    hand-written seams and aliases must survive parsing. A partial surface makes
    check 10 skip unresolved citations, so the gate reports FEWER problems —
    it fails open, which is the direction that hides bugs."""
    reg = drift_check.parse_registrations()
    registry_src = (drift_check.COMMANDS_DIR / "_registry.py").read_text()
    manifest = {g for _, g in
                __import__("re").findall(r'\("(\w+)", "([\w-]+)"\)', registry_src)}
    assert manifest <= set(reg)
    assert len(reg) >= len(manifest) + len(HAND_WRITTEN) + len(ALIASES)
