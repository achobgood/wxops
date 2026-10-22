"""Regression tests for the Codex PreToolUse gate (src/wxcli/codex_gate.py).

The POLICY is exercised by .claude/hooks/wxcli-gate.test.sh, which runs one
decision table across all four copies of the gate (dev shell, bundled shell,
assembled shell, and this module) so they cannot drift apart. What lives here
is the part a shell table cannot express: the OUTPUT PROTOCOL and the wiring,
both of which are version-dependent and both of which fail SILENTLY OPEN when
they are wrong.

Everything asserted below was measured against Codex 0.147.0 on 2026-08-10 by
running `codex exec` with a probe hook and observing the status line and
whether the guarded side effect actually happened:

    gate stdout                          status line                 cmd runs?
    -----------------------------------  --------------------------  ---------
    (empty), exit 0                      hook: PreToolUse Completed   yes
    deny + non-empty reason              hook: PreToolUse Blocked     NO
    permissionDecision "allow"           hook: PreToolUse Failed      yes
    unparseable / cannot execute         hook: PreToolUse Failed      yes

Re-measured on Codex 0.163.0 on 2026-10-20 (headless, marker file as the
control): the gate's deny blocked the command; `allow`, an empty-reason deny
and silence all let it run. `codex exec` prints no status lines, so that
column is still 0.147.0's.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from wxcli import codex_gate as G

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_JSON = REPO_ROOT / "wxcli-dist" / "codex" / "hooks.json"


def _payload(command: str, agent: str = "", agent_id: str = "") -> dict:
    payload = {"agent_type": agent, "tool_input": {"command": command}}
    if agent_id:
        payload["agent_id"] = agent_id
    return payload


def _decision(raw_stdout: str) -> str:
    """allow|deny as the harness sees it: silence IS the permit."""
    if raw_stdout == "":
        return "allow"
    return json.loads(raw_stdout)["hookSpecificOutput"]["permissionDecision"]


# ── the output protocol ────────────────────────────────────────────────────

def test_permit_emits_nothing_not_an_allow_decision():
    """`allow` is an UNSUPPORTED PreToolUse decision on 0.147.0.

    The binary carries `PreToolUse hook returned unsupported
    permissionDecision:allow` next to the `:ask` one, and a probe emitting a
    well-formed allow produced the same `Failed` line as a broken hook. Silence
    is the only permit shape that yields `Completed`, which is what keeps
    `Failed` meaning "this gate did not run" instead of being the normal case
    on every single Bash call.
    """
    import io
    buf = io.StringIO()
    G.emit(None, stream=buf)
    assert buf.getvalue() == ""


def test_deny_carries_a_non_empty_reason():
    """Codex rejects `permissionDecision:deny without a non-empty
    permissionDecisionReason` and then falls OPEN, so a reasonless deny is not
    a weaker deny — it is no deny at all."""
    import io
    for reason in (G.DENY_WRITE, G.DENY_WRITE_SUBAGENT, G.DENY_IMPORT, G.DENY_UNREADABLE):
        buf = io.StringIO()
        G.emit(reason.format(command="x", who="a `probe` subagent") if "{command}" in reason else reason,
               stream=buf)
        out = json.loads(buf.getvalue())["hookSpecificOutput"]
        assert out["hookEventName"] == "PreToolUse"
        assert out["permissionDecision"] == "deny"
        assert out["permissionDecisionReason"].strip()


def test_deny_reason_explains_the_undocumented_agent_type_failure():
    """`agent_type` is documented for SubagentStart/SubagentStop only. If a
    Codex release stops sending it on PreToolUse, every caller is anonymous,
    the BUILDER is denied along with everyone else, and every write workflow
    stops. That is safe but unreadable unless the deny says so."""
    reason = G.DENY_WRITE.format(command="wxcli locations delete X")
    assert "agent_type" in reason
    assert "wxops" in reason
    assert G.CODEX_VERIFIED_VERSION in reason
    assert ".codex/hooks.json" in reason        # names the way out


def test_gate_never_exits_non_zero_even_on_garbage(tmp_path):
    """A non-zero exit reads as `Failed`, which fails OPEN. Every failure path
    must still produce a decision rather than a traceback."""
    for raw in ("", "not json", "[]", "null", '{"tool_input": 7}', '{"a":1}'):
        proc = subprocess.run(
            ["wxcli", "--no-update-check", "codex-gate"],
            input=raw, capture_output=True, text=True,
        )
        assert proc.returncode == 0, (raw, proc.stderr)
        if proc.stdout.strip():
            json.loads(proc.stdout)


def test_unparseable_payload_fails_closed_only_for_wxcli():
    """Mirrors the shell gate's no-jq branch. Denying every Bash command would
    be its own outage; silently allowing wxcli would be worse than shipping no
    gate, because the operator would believe one was running."""
    assert G.evaluate("this is not json") is None
    assert G.evaluate("garbage wxcli organizations delete") == G.DENY_UNREADABLE
    assert G.evaluate("") is None


# ── policy spot-checks (the full table lives in wxcli-gate.test.sh) ────────

@pytest.mark.parametrize("agent,command,expected", [
    ("", "wxcli people list", "allow"),
    ("", "wxcli organizations delete Y2lz", "deny"),
    ("wxops", "wxcli organizations delete Y2lz", "allow"),
    ("migration-advisor", "wxcli cleanup run --force", "allow"),
    ("general-purpose", "wxcli cleanup run --force", "deny"),
    # The 2026-08-10 bypass: a global option before the group used to be read
    # AS the group, so this was allowed.
    ("", "wxcli --no-update-check organizations delete Y2lz", "deny"),
    ("", "wxcli --no-update-check people list", "allow"),
    ("", "wxcli --version", "allow"),
    # The builder is trusted to run wxcli, not to bypass it.
    ("wxops", 'python -c "import wxcli"', "deny"),
])
def test_policy(agent, command, expected):
    import io
    buf = io.StringIO()
    G.emit(G.decide(_payload(command, agent)), stream=buf)
    assert _decision(buf.getvalue().strip()) == expected


# Codex 0.163.0 (Plan 5 Task 1 Step 9): a subagent's shell call now reaches
# PreToolUse with its definition type in `agent_type` and an `agent_id`; the
# main session's payload carries neither.
SUB_ID = "01a15a0c-4333-7000-8000-000000000000"


def test_subagent_deny_says_do_not_spawn():
    """A denied subagent must stop and report, never spawn another agent —
    the recursion the Claude gate's P5-1 fix closes."""
    reason = G.decide(_payload("wxcli people delete X", "default", SUB_ID))
    assert reason is not None
    assert "do not spawn" in reason.lower()
    assert "wxcli people delete X" in reason
    assert "Ask Codex to use" not in reason
    # The trusted agent's subagent call is still permitted (silence).
    assert G.decide(_payload("wxcli people delete X", G.TRUSTED_AGENTS[0], SUB_ID)) is None


def test_main_session_deny_names_type_and_the_spawn_name_rule():
    """Codex rejects hyphens in a spawn name (`agent_name must use only
    lowercase letters, digits, and underscores`, measured 0.163.0), so the
    main-session deny says how to name the spawn as well as which type."""
    reason = G.decide(_payload("wxcli people delete X"))
    assert reason is not None and reason.startswith("Only read-only wxcli")
    assert f'agent_type: "{G.TRUSTED_AGENTS[0]}"' in reason
    assert "lowercase letters, digits and underscores" in reason
    assert "do not spawn" not in reason.lower()
    assert "MAIN session only" not in reason


def test_agent_id_without_agent_type_is_not_trusted():
    """Seen on Claude Code (run c): an agent_id with no agent_type. It is a
    subagent nobody can identify, so it gets the subagent deny."""
    payload = {"agent_id": SUB_ID, "tool_input": {"command": "wxcli people delete X"}}
    reason = G.decide(payload)
    assert "do not spawn" in reason.lower()
    assert "a subagent that reports no agent type" in reason   # review R1 m3


@pytest.mark.parametrize("command", [
    # Review R1 T4-B1: a lone `&` separates commands.
    "wxcli people list & wxcli people delete X",
    "wxcli people list 2>&1 & wxcli people delete X",
    # Review R1 T4-B2: keywords, exec/eval and grouping do not hide a write.
    "for i in A B; do wxcli people delete $i; done",
    "if true; then wxcli people delete X; fi",
    "while read i; do wxcli people delete $i; done < ids.txt",
    "! wxcli people delete X",
    "exec wxcli people delete X",
    'eval "wxcli people delete X"',
    "(wxcli people delete X)",
    "{ wxcli people delete X; }",
])
def test_hidden_writes_are_denied(command):
    assert G.denies_wxcli_write(command), command


@pytest.mark.parametrize("command", [
    "wxcli people list 2>&1", "wxcli people list >&2", "(wxcli people list)",
    "wxcli people list & rm -rf /tmp/x",
])
def test_fd_duplication_and_grouped_reads_are_not_writes(command):
    assert not G.denies_wxcli_write(command), command


# ── the wiring ─────────────────────────────────────────────────────────────

def test_hooks_json_wires_the_gate_with_the_keys_codex_actually_reads():
    """Event keys are CamelCase. A snake_case key PARSES WITHOUT ERROR and
    matches nothing — a config that is inert has no error to find, which is
    exactly how this was mis-diagnosed three times before it was measured."""
    doc = json.loads(HOOKS_JSON.read_text())
    assert set(doc["hooks"]) == {"PreToolUse"}
    entries = doc["hooks"]["PreToolUse"]
    # The shell tool is `Bash`; `exec` is only the tool_use_id prefix.
    assert [e["matcher"] for e in entries] == ["^Bash$"]
    handlers = [h for e in entries for h in e["hooks"]]
    assert [h["type"] for h in handlers] == ["command"]
    assert all(h["timeout"] > 0 for h in handlers)

    command = handlers[0]["command"]
    assert "wxcli --no-update-check codex-gate" in command
    # --no-update-check matters: without it every Bash tool call would carry a
    # once-a-day PyPI check into the hook's latency budget.
    assert "codex-gate" in command and "--no-update-check" in command
    # No absolute or relative path anywhere: an unresolved path is a silent
    # no-gate on Codex, so the handler must resolve nothing but PATH.
    assert ".codex/hooks/" not in command and "$CODEX_HOME" not in command


def test_hooks_json_fallback_fails_closed_without_wxcli():
    """If wxcli is off PATH the gate cannot run, and Codex fails open. The
    inline fallback is the whole guard in that case, so it is executed here
    rather than eyeballed."""
    doc = json.loads(HOOKS_JSON.read_text())
    command = doc["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

    def run(payload_command: str) -> str:
        payload = json.dumps(_payload(payload_command))
        # PATH without wxcli reproduces the failure the fallback exists for.
        out = subprocess.run(
            ["sh", "-c", command], input=payload, capture_output=True,
            text=True, env={"PATH": "/usr/bin:/bin"},
        )
        assert out.returncode == 0, out.stderr
        return out.stdout.strip()

    denied = run("wxcli organizations delete Y2lz")
    body = json.loads(denied)["hookSpecificOutput"]
    assert body["permissionDecision"] == "deny"
    assert body["permissionDecisionReason"].strip()
    # No gate ran, so the fallback cannot tell a subagent from the main
    # session: one sentence must be safe for both (never "spawn" alone).
    assert "if you are already an agent, stop and report" in body["permissionDecisionReason"]
    assert "do not spawn" in body["permissionDecisionReason"]
    # Denying every Bash command would be its own outage.
    assert run("ls -la") == ""


@pytest.mark.skipif(shutil.which("wxcli") is None, reason="wxcli not on PATH")
def test_hooks_json_command_runs_the_real_gate_end_to_end():
    """The handler string as shipped, driven exactly as Codex drives it."""
    doc = json.loads(HOOKS_JSON.read_text())
    command = doc["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

    def run(payload: dict) -> str:
        out = subprocess.run(["sh", "-c", command], input=json.dumps(payload),
                             capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        return out.stdout.strip()

    assert _decision(run(_payload("wxcli people list"))) == "allow"
    assert _decision(run(_payload("wxcli organizations delete Y2lz"))) == "deny"
    assert _decision(
        run(_payload("wxcli organizations delete Y2lz", "wxops"))
    ) == "allow"
