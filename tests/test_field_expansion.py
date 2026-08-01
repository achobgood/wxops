"""The --calling-data interlock: a request that cannot answer the question asked.

`wxcli people list -o json` omits `extension` and `locationId` entirely unless
`--calling-data true` is passed. The command exits 0 and returns every user, so
"how many users have extensions?" answers 0. Measured live 2026-08-01 on a real
org: `--fields '[].extension' --all` returned `[]` where 15 users have one.

This is the highest-value interlock in the CLI precisely because every other
warning fires on output that LOOKS wrong; this one fires on output that looks
perfectly right.

Scoping is the load-bearing part and every test below has a control: the check
must reach exactly the commands that declare the unlocking param, never a
command whose records carry the field natively.
"""
from pathlib import Path

from wxcli.common import FIELD_UNLOCKS, emit

CMD_DIR = Path(__file__).parent.parent / "src" / "wxcli" / "commands"


def test_warns_when_fields_wants_a_locked_field(capsys):
    emit([{"id": "a"}], output="json", fields="[].extension",
         params={}, expansions=("callingData",))
    err = capsys.readouterr().err
    assert "--calling-data" in err
    assert "extension" in err


def test_silent_when_the_unlocking_param_was_passed(capsys):
    emit([{"id": "a", "extension": "1001"}], output="json", fields="[].extension",
         params={"callingData": "true"}, expansions=("callingData",))
    assert "--calling-data" not in capsys.readouterr().err


def test_silent_on_endpoints_that_do_not_offer_the_flag(capsys):
    """The false-positive guard, and why `expansions` is not optional.

    `virtual-lines list` returns `extension` natively and declares no
    --calling-data. Unscoped, this check would tell its caller to pass a flag
    that does not exist on that command — a warning nobody can act on.
    """
    emit([{"extension": "1001"}], output="json", fields="[].extension",
         params={}, expansions=())
    assert "--calling-data" not in capsys.readouterr().err


def test_silent_when_fields_names_no_locked_field(capsys):
    emit([{"id": "a"}], output="json", fields="[].displayName",
         params={}, expansions=("callingData",))
    assert "--calling-data" not in capsys.readouterr().err


def test_no_fields_means_no_signal_to_read(capsys):
    """A bare `people list` may genuinely not want extensions. Warning on every
    call would train the reader to ignore the note."""
    emit([{"id": "a"}], output="json", fields=None,
         params={}, expansions=("callingData",))
    assert "--calling-data" not in capsys.readouterr().err


def test_the_table_only_carries_field_expanding_params():
    """`--has-cx-essentials` is the same trap but RECORD-expanding: without it
    `call-queue list` omits CX queues entirely. Nothing in a --fields expression
    says "I also wanted CX queues", so there is no signal to check and it must
    not be added here — it would warn on every projection or none.
    """
    assert set(FIELD_UNLOCKS) == {"callingData"}
    assert FIELD_UNLOCKS["callingData"] == frozenset({"extension", "locationId"})


def test_the_generator_wires_it_exactly_where_the_param_exists():
    """Tree-wide, not a spot check. A module gaining the guard without also
    declaring the query param would emit an unactionable warning."""
    carrying = {p.name for p in CMD_DIR.glob("*.py") if "expansions=" in p.read_text()}
    assert carrying == {"people.py"}, f"unexpected modules carry the interlock: {carrying}"
    src = (CMD_DIR / "people.py").read_text()
    # list, create, show, update, show-me -- every command taking --calling-data
    assert src.count("expansions=('callingData',)") == 5
