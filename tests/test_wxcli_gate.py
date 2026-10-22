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
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / ".claude" / "hooks" / "wxcli-gate.sh"
BUNDLED_GATE = REPO / "wxcli-dist" / "wxcli-gate.bundled.sh"
TEST_TABLE = REPO / ".claude" / "hooks" / "wxcli-gate.test.sh"
# The one agent type the gate exempts besides migration-advisor.
BUILDER = "wxops"
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


def _run_gate(payload: dict, gate: Path = GATE) -> str:
    proc = subprocess.run(
        ["sh", str(gate)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _decide(payload: dict, gate: Path = GATE) -> str:
    """allow | deny | none. `none` = the gate printed nothing, so Claude Code's
    normal permission rules decide (Plan 5, open question 1)."""
    out = _run_gate(payload, gate)
    if not out:
        return "none"
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


def _reason(payload: dict, gate: Path = GATE) -> str:
    out = json.loads(_run_gate(payload, gate))["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny", out
    return out["permissionDecisionReason"]


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
        ({"agent_type": "wxops", "tool_input": {"command": "wxcli people create"}}, "allow"),
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
        ({"tool_input": {"command": "git status"}}, "none"),
        # Other agents get the same read-only treatment as the main session.
        ({"agent_type": "Explore", "tool_input": {"command": "wxcli people list"}}, "allow"),
        ({"agent_type": "Explore", "tool_input": {"command": "wxcli people delete X"}}, "deny"),
    ],
)
def test_gate_decisions(payload, want):
    assert _decide(payload) == want


# ── Plan 5: hook hardening ────────────────────────────────────────────────
# Both shell copies must keep the same policy, so each check runs on both.
BOTH_GATES = pytest.mark.parametrize("gate", [GATE, BUNDLED_GATE], ids=["dev", "bundled"])
TEAMMATE_ID = f"a{BUILDER}-0123456789abcdef"   # a<name>-<16 hex>, measured 2.1.304
SUBAGENT_ID = "a5c80b9d0123456789"             # a<17 hex>: an ordinary subagent


def test_decision_table_script_passes():
    """The decision table runs in CI, not only by hand (Plan 5, M5).

    One table, four gates: the dev copy, the bundled source, the assembled
    copy and the Codex gate. `jq` or `wxcli` missing is a failure, not a skip:
    the table then proves nothing.
    """
    env = dict(os.environ)
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")
    proc = subprocess.run(["sh", str(TEST_TABLE)], capture_output=True, text=True, env=env)
    tail = proc.stdout[-3000:] + proc.stderr[-2000:]
    assert proc.returncode == 0, tail
    assert proc.stdout.count("fail=0") == 4, tail


@BOTH_GATES
def test_deny_inside_subagent_says_do_not_spawn(gate):
    """A denied subagent must stop and report, never spawn (Review Focus 2)."""
    reason = _reason({"agent_type": "general-purpose", "agent_id": SUBAGENT_ID,
                      "tool_input": {"command": "wxcli people delete X"}}, gate)
    assert "do not spawn" in reason.lower()
    assert "Spawn the" not in reason
    assert "wxcli people delete X" in reason
    assert "inside a `general-purpose` subagent" in reason
    # No agent_type (seen in Task 1's run c): the text still reads naturally.
    untyped = _reason({"agent_id": SUBAGENT_ID,
                       "tool_input": {"command": "wxcli people delete X"}}, gate)
    assert "inside a subagent that reports no agent type" in untyped
    assert "do not spawn" in untyped.lower()


@BOTH_GATES
def test_main_session_deny_names_wxops_type_not_name(gate):
    """The main session is told to spawn the builder by TYPE; any name works."""
    reason = _reason({"tool_input": {"command": "wxcli people delete X"}}, gate)
    assert reason.startswith("Only read-only wxcli")
    assert f'subagent_type "{BUILDER}"' in reason
    assert "not its name" in reason
    assert "do not spawn" not in reason.lower()


@BOTH_GATES
@pytest.mark.parametrize("agent", ["", "general-purpose", BUILDER, "migration-advisor"])
@pytest.mark.parametrize("command", [
    "git push origin main", "rm -rf /tmp/p5-x", "ls -la",
    "wxcli people list && rm -rf /tmp/x",
])
def test_unrelated_command_gets_no_decision(gate, agent, command):
    """Anything that is not entirely wxcli gets NO output, so Claude Code's own
    permission rules apply (open question 1). An `allow` here skipped the prompt
    for every command in every folder the gate runs in."""
    assert _run_gate({"agent_type": agent, "tool_input": {"command": command}}, gate) == ""


@BOTH_GATES
def test_exempt_write_joined_to_other_command_gets_no_decision(gate):
    """The builder's write joined to `git push`: the wxcli half is permitted,
    the other half is not ours to approve, so no decision. Anyone else's write
    in the same command is still denied."""
    command = {"command": "wxcli people create X && git push"}
    for agent in (BUILDER, "migration-advisor"):
        assert _run_gate({"agent_type": agent, "tool_input": command}, gate) == ""
    assert _decide({"agent_type": "general-purpose", "tool_input": command}, gate) == "deny"


FLOW = "mcp__wxcc-flow-builder__"
FLOW_READS = ("list_flows", "get_flow", "validate_flow", "get_flow_template",
              "get_activity_definitions", "get_activity_node_schema",
              "describe_activity", "get_choices", "list_event_specifications")


@BOTH_GATES
def test_mcp_flow_writes_gated(gate):
    """Flow Store writes run only inside the builder (open question 2)."""
    def mcp(tool, agent="", agent_id=""):
        p = {"agent_type": agent, "tool_name": FLOW + tool,
             "tool_input": {"flow_id": "x"}}
        if agent_id:
            p["agent_id"] = agent_id
        return p

    for tool in FLOW_READS:
        assert _run_gate(mcp(tool), gate) == "", tool
    for tool in ("create_flow", "save_flow_draft", "patch_flow_draft", "some_new_tool"):
        assert _decide(mcp(tool), gate) == "deny", tool
        assert tool in _reason(mcp(tool), gate)           # names the tool (review m10)
    assert _decide(mcp("create_flow", BUILDER, SUBAGENT_ID), gate) == "allow"
    assert _decide(mcp("create_flow", "migration-advisor"), gate) == "allow"
    sub = _reason(mcp("save_flow_draft", "general-purpose", SUBAGENT_ID), gate)
    assert "do not spawn" in sub.lower()
    assert _decide(mcp("create_flow", BUILDER, TEAMMATE_ID), gate) == "deny"


@BOTH_GATES
def test_teammate_refused_even_when_typed_as_builder(gate):
    """P5-17: with agent teams on, a named spawn becomes a teammate whose
    agent_type is its NAME, so `general-purpose` named like the builder arrived
    as the builder. A caller with a teammate-shaped id is refused, never
    exempted; its reads still pass; an ordinary subagent id is unaffected."""
    write = {"command": "wxcli people delete X"}
    reason = _reason({"agent_type": BUILDER, "agent_id": TEAMMATE_ID, "tool_input": write}, gate)
    assert "agent teams are on" in reason
    assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0" in reason
    assert "do not spawn" in reason.lower()
    gp = {"agent_type": "general-purpose", "agent_id": "ageneral-purpose-0123456789abcdef",
          "tool_input": write}
    assert "agent teams are on" in _reason(gp, gate)
    assert _decide({"agent_type": BUILDER, "agent_id": TEAMMATE_ID,
                    "tool_input": {"command": "wxcli people list"}}, gate) == "allow"
    assert _decide({"agent_type": BUILDER, "agent_id": SUBAGENT_ID, "tool_input": write}, gate) == "allow"
    # The suffix must be exactly 16 hex digits: a near miss is not a teammate.
    for near in (f"a{BUILDER}-0123", f"a{BUILDER}-0123456789abcdeg", f"b{BUILDER}-0123456789abcdef"):
        assert _decide({"agent_type": BUILDER, "agent_id": near, "tool_input": write}, gate) == "allow", near


def _meta_payload(tmp_path, meta: dict | str | None, agent_id: str = SUBAGENT_ID) -> dict:
    """A payload whose transcript_path has the subagents/ meta file beside it."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("")
    if meta is not None:
        d = tmp_path / "session" / "subagents"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"agent-{agent_id}.meta.json").write_text(
            meta if isinstance(meta, str) else json.dumps(meta))
    return {"agent_type": BUILDER, "agent_id": agent_id, "transcript_path": str(transcript),
            "tool_input": {"command": "wxcli people delete X"}}


@BOTH_GATES
def test_teammate_meta_file_refuses_but_never_grants(gate, tmp_path):
    """The meta file's taskKind is the second teammate signal. It is used only
    to DENY, so a missing, unreadable or forged file can never grant anything."""
    teammate = _meta_payload(tmp_path / "t", {"taskKind": "in_process_teammate",
                                             "spawnedAgentType": "general-purpose"})
    assert "agent teams are on" in _reason(teammate, gate)
    for meta in (None, "not json", {"agentType": BUILDER}, {"taskKind": "other"}):
        case = tmp_path / ("m" + str(abs(hash(str(meta)))))
        assert _decide(_meta_payload(case, meta), gate) == "allow", meta
    # A non-exempt caller is denied whatever its meta file says.
    gp = _meta_payload(tmp_path / "g", {"taskKind": "ordinary"})
    gp["agent_type"] = "general-purpose"
    assert _decide(gp, gate) == "deny"
