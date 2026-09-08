"""PreToolUse safety gate for Codex — the twin of .claude/hooks/wxcli-gate.sh.

Same POLICY as the Claude Code gate, a different DELIVERY MECHANISM and a
different OUTPUT PROTOCOL, both forced by measured Codex behaviour.

Why this is a CLI subcommand and not a shell script
---------------------------------------------------
Claude Code hands a hook `$CLAUDE_PROJECT_DIR`, so its gate can be wired as
`sh "$CLAUDE_PROJECT_DIR/.claude/hooks/wxcli-gate.sh"`. Codex exposes no
equivalent (only CODEX_HOME), and a Codex hook that cannot execute **fails
open** — the command runs and the only trace is a `hook: PreToolUse Failed`
line. An unresolved path is therefore a silent no-gate, not an error, which
makes path resolution a safety property rather than a packaging detail.

Routing the hook through the installed binary removes path resolution from the
gate entirely: `wxcli` is found on PATH, and the policy travels inside the
package that the playbook already requires. Codex runs a hook command via
`$SHELL -lc` (measured: the literal `SHELL` / `-lc` pair lives in
hooks/src/engine/command_runner.rs), i.e. a LOGIN shell, so the hook inherits
the same PATH the operator installed wxcli into. The one residual — wxcli not
on PATH at all — is covered by a fail-closed fallback inlined in
.codex/hooks.json, which needs no binary and no file of its own.

The output protocol, measured on Codex 0.147.0 (2026-08-10)
-----------------------------------------------------------
Verified by running `codex exec` against a probe hook and reading both the
status line and whether the guarded side effect happened:

    gate stdout                              status line                cmd runs?
    ---------------------------------------  -------------------------  ---------
    (empty), exit 0                          hook: PreToolUse Completed  yes
    permissionDecision "deny" + reason       hook: PreToolUse Blocked    NO
    permissionDecision "allow"               hook: PreToolUse Failed     yes
    unparseable / hook cannot execute        hook: PreToolUse Failed     yes

**`allow` is NOT a supported PreToolUse decision on 0.147.0.** The binary
carries the error string `PreToolUse hook returned unsupported
permissionDecision:allow` alongside the `:ask` one, and a probe emitting a
well-formed `allow` produced the same `Failed` line as a broken hook. So the
permit path here emits NOTHING. That is not a cosmetic choice: silence is the
only permit shape that yields a distinguishable `Completed`, which keeps
`Failed` meaning "this gate did not run" instead of being the normal case on
every Bash call — the difference between a visible outage and an invisible one.

`deny` additionally requires a NON-EMPTY reason (`PreToolUse hook returned
permissionDecision:deny without a non-empty permissionDecisionReason`), so
every deny path below carries one.

WHAT THIS GATE DOES NOT COVER — measured, not assumed
------------------------------------------------------
**PreToolUse fires only for the MAIN session. A spawned subagent's tool calls
never reach it.** Measured twice on 0.147.0 with a catch-all (`matcher: ".*"`)
logging handler, once from project `.codex/hooks.json` and once from global
`$CODEX_HOME/hooks.json`: the parent's `Bash`, `collaborationspawn_agent` and
`collaborationwait_agent` calls were all captured, and the subagent's own `Bash`
call produced NO hook invocation at all. A control confirmed the subagent really
did run its command. So on Codex today, anything running inside a subagent is
ungated, and this gate guards the main session only. That is narrower than the
Claude Code twin, where subagent tool calls do reach the hook.

The one place the boundary is visible is the spawn itself: the parent's
`collaborationspawn_agent` payload carries the target agent in
`tool_input.agent_type`. Refusing spawns is NOT done here — it would block
ordinary delegation for non-wxcli work, and delegating to the builder is exactly
what every deny message asks for.

`agent_type` — the field the trusted-caller branch keys on — was NOT observed on
any PreToolUse payload in this environment, present or empty, for the main
session or otherwise. It appears only as `tool_input.agent_type` on the spawn
call. The TRUSTED_AGENTS branch is therefore forward-looking rather than
load-bearing today: the builder is unrestricted because the hook never sees it,
not because the gate allows it. Keeping the branch costs nothing and is already
correct if a release starts delivering the field.

What is version-pinned, and what breaks if it moves
---------------------------------------------------
See CODEX_VERIFIED_VERSION. Two behaviours are undocumented and version-bound:

1. `agent_type` on the PreToolUse payload. Official Codex hook docs list it for
   SubagentStart/SubagentStop only. If a release starts sending it and a later
   one drops it again, every caller looks anonymous, the builder is denied along
   with everyone else, and every write workflow stops — safe, but unreadable
   unless the deny says so. It does; see DENY_WRITE.
2. Hyphenated custom-agent names. 0.144.1 silently ignored them, so
   `wxc-calling-builder` never loaded there at all; 0.147.0 accepts them.
   assemble.py validates the name at build time.

tests/test_codex_gate.py pins the protocol, and .claude/hooks/wxcli-gate.test.sh
runs one decision table across BOTH gates so the two cannot drift apart.
"""
from __future__ import annotations

import json
import re
import sys

# The Codex release every measurement in this module was taken on. Behaviour
# here is version-dependent (0.144.1 differs materially), so the number is
# recorded rather than implied.
CODEX_VERIFIED_VERSION = "0.147.0"

# Agents that carry the playbook rules run unrestricted. They are the reason
# this gate exists: the rules that make a wxcli call correct travel with the
# agent, not with the caller.
TRUSTED_AGENTS = ("wxc-calling-builder", "migration-advisor")

# Wrappers that take another command as an argument. Only inside one of these
# is anything past the command position scanned — otherwise `grep -rn wxcli
# docs/` reads as an invocation, and denying an ordinary grep is its own bug.
WRAPPERS = frozenset(
    "env command nohup nice time xargs sudo stdbuf setsid sh bash zsh".split()
)

# `get*` is deliberately NOT a read: all four get-* commands issue a POST
# (get-domain-verification, get-customer-device, get-location-device,
# get-device-dynamic). A read-sounding name is not evidence of a read.
READ_VERBS = ("list", "show")

_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_LEADING_BACKSLASH = re.compile(r"^\\+")
_LEADING_QUOTE = re.compile(r"^[\"']+")
_TRAILING_QUOTE = re.compile(r"[\"']+$")
_SPLIT_TOKENS = re.compile(r"[ \t]+")

# Matched on an IMPORT of wxcli, not on the string `wxcli/commands`: reading
# command source as text is fine and must stay unblocked.
_IMPORT_FORMS = ("import wxcli", "from wxcli", "import src.wxcli", "from src.wxcli")
_IMPORT_MODULE = re.compile(r"import_module.*wxcli")


def _clean(token: str) -> str:
    """Strip shell quoting a static reader can see through."""
    token = _LEADING_BACKSLASH.sub("", token)
    token = _LEADING_QUOTE.sub("", token)
    return _TRAILING_QUOTE.sub("", token)


def _base(token: str) -> str:
    """Basename, so /opt/homebrew/bin/wxcli and ./wxcli resolve to `wxcli`."""
    return token.rsplit("/", 1)[-1]


def _segments(command: str) -> list[str]:
    """Split a compound command so each segment is judged on its own.

    `wxcli people list && wxcli locations delete X` is not a read.
    """
    for sep in ("||", "&&", ";", "|"):
        command = command.replace(sep, "\n")
    return command.split("\n")


def imports_wxcli_from_python(command: str) -> bool:
    """The side door: Python that imports the CLI instead of invoking it.

    2026-07-28: a subagent imported four generated delete functions to see
    whether they crash; a Typer default is an OptionInfo (truthy), so the
    confirm prompt was skipped and three unconfirmed DELETEs reached the live
    org, one of them DELETE /v1/organizations/{id}. Only the API refusing them
    saved it. Checked BEFORE the trusted-agent exemption: the builder is
    trusted to run wxcli, not to bypass it.
    """
    if "python" not in command and "PYTHONPATH" not in command:
        return False
    return any(form in command for form in _IMPORT_FORMS) or bool(
        _IMPORT_MODULE.search(command)
    )


def denies_wxcli_write(command: str) -> bool:
    """True if any segment invokes wxcli in a way that is not a plain read.

    Resolves wxcli by RESOLVED BASENAME in every segment. The Claude gate's
    first version compared only token 1 for string equality and fell open on 14
    of 15 spellings — `/usr/local/bin/wxcli organizations delete`, `./wxcli`,
    `env wxcli`, `bash -c "wxcli ..."`, `cd /tmp && wxcli ...`, `true; wxcli`,
    `xargs wxcli`, `"wxcli"`, `\\wxcli`, `command wxcli`, `nohup wxcli ...`. A
    full-path invocation is common for subagents (a bare `wxcli` is frequently
    not on a subagent's PATH), so the usual invocation was exactly the one that
    disabled the gate.

    Residual, stated rather than papered over: a token this cannot resolve
    statically — `$(echo wxcli) ...`, or a shell alias — is invisible here. A
    hook sees only the command string.
    """
    for segment in _segments(command):
        tokens = [_clean(t) for t in _SPLIT_TOKENS.split(segment)]
        # Skip blank fields (splitting on the delimiters leaves a leading empty
        # token on every segment after the first) and VAR=val prefixes.
        first = 0
        while first < len(tokens) and (
            tokens[first] == "" or _ASSIGNMENT.match(tokens[first])
        ):
            first += 1
        if first >= len(tokens):
            continue

        idx = -1
        if _base(tokens[first]) == "wxcli":
            idx = first
        elif _base(tokens[first]) in WRAPPERS:
            for k in range(first + 1, len(tokens)):
                if _base(tokens[k]) == "wxcli":
                    idx = k
                    break
        if idx < 0:
            continue

        rest = tokens[idx + 1:]
        # --help anywhere is inert: it prints and exits before any API call,
        # and the playbook REQUIRES agents to run it before first use.
        if any(t in ("--help", "-h") for t in rest):
            continue
        # Skip LEADING GLOBAL OPTIONS before judging the group. Treating
        # "starts with a dash" as inert fell open on `wxcli --no-update-check
        # organizations delete Y2lz` — the gate read --no-update-check as the
        # group and waved a real org delete through. All four top-level options
        # (--version, --no-update-check, --install-completion,
        # --show-completion) are boolean flags, so none consumes a following
        # value and skipping is unambiguous.
        p = 0
        while p < len(rest) and (rest[p] == "" or rest[p].startswith("-")):
            p += 1
        group = rest[p] if p < len(rest) else ""
        sub = rest[p + 1] if p + 1 < len(rest) else ""
        # bare `wxcli`, `wxcli --version`, `wxcli whoami`
        if group == "" or group == "whoami":
            continue
        if sub == "":
            return True              # bare `wxcli configure` mutates state
        verb = sub.split("-", 1)[0]  # show-call-forwarding -> show
        if verb not in READ_VERBS:
            return True
    return False


# ── Deny reasons ──────────────────────────────────────────────────────────
# Codex requires a NON-EMPTY permissionDecisionReason on every deny, and the
# reason is the only thing the caller sees, so each one names the recovery.

DENY_WRITE = (
    "Only read-only wxcli (list*/show*/whoami/--help) may run outside the "
    "wxc-calling-builder agent. This command changes state or is unrecognized. "
    "REQUIRED ACTION: do NOT run wxcli directly again. Ask Codex to use the "
    "wxc-calling-builder agent and give it this intent: {command} — the agent "
    "handles auth, planning, execution and verification. "
    "SCOPE, measured on Codex "
    + CODEX_VERIFIED_VERSION
    + ": PreToolUse fires for the MAIN session only — a spawned subagent's "
    "shell calls never reach it — so delegating is both the intended route and "
    "the one that works. IF YOU ARE ALREADY THE BUILDER AND STILL SEE THIS, "
    "the gate has failed closed rather than misfired: it identifies the caller "
    "from the hook payload's `agent_type`, which is NOT a documented PreToolUse "
    "field (Codex documents it for SubagentStart/SubagentStop only) and was not "
    "observed on any PreToolUse payload when this shipped. If a release starts "
    "sending it and a later one stops, every caller looks anonymous, the "
    "builder is denied along with everyone else, and every write workflow "
    "stops. To confirm, dump the hook payload and look for `agent_type`; to "
    "unblock, remove the PreToolUse entry from .codex/hooks.json and accept "
    "that this leaves every wxcli call in the main session unguarded."
)

DENY_IMPORT = (
    "Importing wxcli from Python bypasses this gate, the read-only verb policy "
    "and the confirm prompt — those all live above the Python layer. The "
    "command functions in the installed wxcli package make REAL HTTP calls to "
    "the live org, and a Typer default is an OptionInfo (truthy), so "
    "force=False does not mean what it reads like. REQUIRED ACTION: do not "
    "call command functions directly. Use `wxcli <command> --help` to inspect "
    "a command, or ask Codex to run the work through the wxc-calling-builder "
    "agent. If a layer genuinely must be exercised, monkeypatch the HTTP layer "
    "first."
)

DENY_UNREADABLE = (
    "The wxcli safety gate could not parse the Codex hook payload, so this "
    "call could not be evaluated. Rather than allow an unchecked wxcli "
    "invocation it is refused; unrelated commands are unaffected. REQUIRED "
    "ACTION: ask Codex to run this work through the wxc-calling-builder agent, "
    "or report the malformed payload — the gate expects a JSON object with "
    "`tool_input.command`."
)


def decide(payload: dict) -> str | None:
    """The deny reason, or None to permit. None is emitted as SILENCE."""
    tool_input = payload.get("tool_input")
    command = ""
    if isinstance(tool_input, dict):
        command = str(tool_input.get("command") or "")
    agent = str(payload.get("agent_type") or "")

    if imports_wxcli_from_python(command):
        return DENY_IMPORT
    if agent in TRUSTED_AGENTS:
        return None
    if denies_wxcli_write(command):
        return DENY_WRITE.format(command=command)
    return None


def evaluate(raw: str) -> str | None:
    """Decide from raw stdin, failing CLOSED on anything wxcli-shaped.

    A payload we cannot read must not fall open on a wxcli call. Denying every
    Bash command would be its own outage, so the fail-closed branch is scoped
    the same way the Claude gate scopes its no-jq branch: refuse anything
    mentioning wxcli, pass everything else through.
    """
    try:
        payload = json.loads(raw)
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        return DENY_UNREADABLE if "wxcli" in raw else None
    return decide(payload)


def emit(reason: str | None, stream=None) -> None:
    """Write the decision. Permit is silence — see the module docstring."""
    if reason is None:
        return
    out = stream if stream is not None else sys.stdout
    out.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }) + "\n")


def main() -> int:
    """stdin -> decision on stdout. ALWAYS exits 0.

    A non-zero exit reads to Codex as `hook: PreToolUse Failed`, which fails
    OPEN. So every failure path here still produces a decision rather than a
    traceback.
    """
    raw = ""
    try:
        raw = sys.stdin.read()
        emit(evaluate(raw))
    except Exception:
        try:
            if "wxcli" in raw:
                emit(DENY_UNREADABLE)
        except Exception:
            pass
    return 0
