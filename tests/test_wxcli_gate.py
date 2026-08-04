"""Guards for the dev-only wxcli PreToolUse gate (.claude/hooks/wxcli-gate.sh).

The gate lets non-agent callers (main session, /query-live) run read-only wxcli
while blocking anything that mutates the org.  It decides using the command's
leading verb: `list*` and `show*` are reads, everything else is denied.

That shortcut is only safe while the verb tells the truth.  The CLI is generated
from API specs, so a future spec could add a `show-*`/`list-*` command that POSTs
and the gate would silently wave a write through.  test_read_verbs_never_write
pins that invariant: if the generator ever adds a lying command, this fails loudly
instead of quietly opening a hole.

`get*` is excluded from the read set on purpose -- all four get-* commands POST.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / ".claude" / "hooks" / "wxcli-gate.sh"
CMD_DIR = REPO / "src" / "wxcli" / "commands"

READ_VERBS = {"list", "show"}
WRITE_CALL = re.compile(r"rest_(post|put|patch|delete)|\.(post|put|patch|delete)\(")
# Must not require the closing paren right after the name.  command_renderer
# emits `@app.command("name", short_help=...)` and `@app.command("name",
# hidden=True)` for aliases; a pattern anchored on `"name")` matched neither and
# silently reduced the scan below to 86 of 1961 commands, so the read-verb
# invariant was passing on 4% of the surface.  Stop at the closing quote.
DECORATOR = re.compile(r'(@app\.command\(\s*"([a-z0-9-]+)")')


def _commands():
    """Yield (file, command_name, function_body) for every generated command."""
    for path in sorted(CMD_DIR.glob("*.py")):
        parts = DECORATOR.split(path.read_text())
        for i in range(1, len(parts) - 1, 3):
            yield path.name, parts[i + 1], parts[i + 2]


# Every assertion below is over whatever _commands() happens to yield, so a
# decorator-shape change that stops the regex matching turns them all green
# while checking nothing.  That is not hypothetical: it is exactly how this file
# came to be scanning 86 commands.  Pin a floor well under the real count
# (1961 at the time of writing) so the scan cannot quietly collapse again.
MIN_COMMANDS = 1500


def test_scan_actually_sees_the_command_surface():
    """Guards every other test here: they are vacuous if the scan comes up empty."""
    found = sum(1 for _ in _commands())
    assert found >= MIN_COMMANDS, (
        f"only {found} commands matched DECORATOR, expected >= {MIN_COMMANDS}. "
        "The @app.command(...) shape probably changed, which makes the read-verb "
        "invariant below pass without inspecting anything. Fix the regex."
    )


def _decide(payload: dict) -> str:
    proc = subprocess.run(
        ["sh", str(GATE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]


def test_gate_script_exists_and_is_wired():
    """The hook fails OPEN: a bad path means every command is silently allowed.

    So assert the path baked into settings.json actually resolves.  This catches
    the repo being moved/cloned elsewhere, which would otherwise disable the gate
    with no error.
    """
    assert GATE.is_file(), "gate script missing"
    settings = json.loads((REPO / ".claude" / "settings.json").read_text())
    hook = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert "wxcli-gate.sh" in hook

    wired = next(
        (tok.strip('"') for tok in hook.split() if tok.strip('"').endswith("wxcli-gate.sh")),
        None,
    )
    assert wired, f"could not find gate path in hook command: {hook!r}"

    # The wired path is written against $CLAUDE_PROJECT_DIR so the hook survives
    # the repo being cloned elsewhere -- which is the very thing this test
    # guards.  Claude Code sets that variable to the project root at hook time;
    # expand it the same way rather than stat-ing the literal string.
    resolved = Path(
        wired.replace("${CLAUDE_PROJECT_DIR}", str(REPO))
             .replace("$CLAUDE_PROJECT_DIR", str(REPO))
    )
    assert "$" not in str(resolved), (
        f"gate path {wired!r} contains a variable this test cannot expand, so it "
        "cannot prove the hook resolves. Teach the test the new variable."
    )
    assert resolved.is_file(), (
        f"settings.json points the gate at {wired!r} (-> {resolved}), which does "
        "not exist. The hook fails open, so the gate is silently disabled. Fix the path."
    )
    assert resolved.resolve() == GATE.resolve(), (
        f"settings.json wires {resolved}, not the gate script at {GATE}."
    )


def test_read_verbs_never_write():
    """A command named list*/show* must never issue a write.

    This is the gate's load-bearing assumption.  If this fails, either fix the
    command name or remove that verb from READ_VERBS in the gate script -- do
    NOT just update this test.
    """
    liars = [
        f"{fname}:{cmd}"
        for fname, cmd, body in _commands()
        if cmd.split("-")[0] in READ_VERBS and WRITE_CALL.search(body)
    ]
    assert not liars, (
        "read-named wxcli commands that actually write: "
        f"{liars}. The gate would let these through from the main session."
    )


def test_get_verb_still_writes_so_stays_excluded():
    """Documents why `get` is not a read verb.  If this ever fails, get-* became
    safe and could be added to the gate's read set."""
    writers = [
        cmd
        for _, cmd, body in _commands()
        if cmd.split("-")[0] == "get" and WRITE_CALL.search(body)
    ]
    assert writers, "no get-* command writes anymore -- reconsider excluding `get`"


@pytest.mark.parametrize(
    "payload,want",
    [
        # Agents carrying the playbook rules are unrestricted.
        ({"agent_type": "wxc-calling-builder", "tool_input": {"command": "wxcli people create"}}, "allow"),
        ({"agent_type": "migration-advisor", "tool_input": {"command": "wxcli cucm decide 1 accept"}}, "allow"),
        # Main session: reads pass.
        ({"tool_input": {"command": "wxcli people list"}}, "allow"),
        ({"tool_input": {"command": "wxcli user-settings show-call-forwarding X"}}, "allow"),
        ({"tool_input": {"command": "wxcli whoami"}}, "allow"),
        ({"tool_input": {"command": "wxcli --help"}}, "allow"),
        ({"tool_input": {"command": "wxcli people --help"}}, "allow"),
        ({"tool_input": {"command": "FOO=1 wxcli people list"}}, "allow"),
        # Main session: writes blocked.
        ({"tool_input": {"command": "wxcli people create --email x"}}, "deny"),
        ({"tool_input": {"command": "wxcli people delete X"}}, "deny"),
        ({"tool_input": {"command": "wxcli cleanup run --force"}}, "deny"),
        ({"tool_input": {"command": "wxcli switch-org"}}, "deny"),
        ({"tool_input": {"command": "wxcli configure"}}, "deny"),
        ({"tool_input": {"command": "FOO=1 wxcli people create"}}, "deny"),
        # Read-sounding but POSTs.
        ({"tool_input": {"command": "wxcli domains get-domain-verification X"}}, "deny"),
        # Unknown verb fails closed.
        ({"tool_input": {"command": "wxcli people frobnicate"}}, "deny"),
        # Not our binary.
        ({"tool_input": {"command": "git status"}}, "allow"),
        # Other agents get the same read-only treatment as the main session.
        ({"agent_type": "Explore", "tool_input": {"command": "wxcli people list"}}, "allow"),
        ({"agent_type": "Explore", "tool_input": {"command": "wxcli people delete X"}}, "deny"),
    ],
)
def test_gate_decisions(payload, want):
    assert _decide(payload) == want
