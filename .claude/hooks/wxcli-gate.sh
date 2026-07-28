#!/bin/sh
# PreToolUse gate for raw `wxcli` Bash calls.  Dev-only: assemble.py substitutes
# settings.bundled.json and does not bundle .claude/hooks, so this never ships.
#
# Policy:
#   - Agents carrying the playbook rules (wxc-calling-builder, migration-advisor)
#     may run anything.
#   - Anyone else (main session, other agents) may run READ-ONLY wxcli only.
#     Reads are `list*` / `show*` / `whoami` / help.  Everything else is denied
#     and redirected to the builder agent.
#   - Unknown verbs deny (fail closed).
#
# `get*` is deliberately NOT a read: all four get-* commands issue rest_post
# (get-domain-verification, get-customer-device, get-location-device,
# get-device-dynamic).  Verified against src/wxcli/commands/ — a read-sounding
# name is not evidence of a read.

set -u

allow() {
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
  exit 0
}

deny() {
  jq -nc --arg c "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:("Only read-only wxcli (list*/show*/whoami) may run outside an agent. This command changes state or is unrecognized. REQUIRED ACTION: Do NOT run wxcli directly again. Spawn the wxc-calling-builder agent (subagent_type=\"wxc-calling-builder\") and pass it this intent: " + $c + " — The agent handles auth, planning, execution, and verification.")}}'
  exit 0
}

deny_import() {
  jq -nc '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"Importing wxcli from Python bypasses this gate, the read-only verb policy, and the confirm prompt — those live above the Python layer. Functions in src/wxcli/commands/ make REAL HTTP calls to the live org, and a Typer default is an OptionInfo (truthy), so force=False does not mean what it reads like. REQUIRED ACTION: read the code instead of running it. The confirm string, URL, method and docstring are all literals in the file — use Read/Grep, or parse it with ast (reading a file is fine, importing it is not). If a layer genuinely must be exercised, monkeypatch the HTTP layer first, or ask Adam. `wxcli <cmd> --help` is safe."}}'
  exit 0
}

input=$(cat)
agent=$(printf '%s' "$input" | jq -r '.agent_type // ""')
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')

# The side door.  Everything below only inspects commands whose first token is
# `wxcli`, so Python that imports the CLI walks straight past it.  2026-07-28: a
# subagent imported four generated delete functions to see whether they crash;
# the OptionInfo-is-truthy trap skipped the confirm prompt and four unconfirmed
# DELETEs reached the live org, one of them DELETE /v1/organizations/{id}.  Only
# Cisco refusing them saved it.
#
# Matched on an IMPORT of wxcli, not on the string `wxcli/commands`: reading
# those files — Read, grep, ast.parse on the source — is the sanctioned way to
# answer questions about them and must stay unblocked.  Checked before the agent
# exemption below: the builder is trusted to run wxcli, not to bypass it.
# Limit, stated: a hook sees only the command string, so a .py file on disk that
# imports wxcli is invisible here.  That is why `python tools/drift_check.py`
# and pytest keep working, and why this is a guard rail, not a proof.
case "$cmd" in
  *python*|*PYTHONPATH*)
    case "$cmd" in
      *"import wxcli"*|*"from wxcli"*|*"import src.wxcli"*|*"from src.wxcli"*)
        deny_import ;;
      *import_module*wxcli*)
        deny_import ;;
    esac
    ;;
esac

# Agents that carry the playbook rules run unrestricted.
case "$agent" in
  wxc-calling-builder|migration-advisor) allow ;;
esac

# Strip leading VAR=val prefixes so `FOO=1 wxcli ...` still resolves to wxcli.
stripped=$(printf '%s' "$cmd" | sed -E 's/^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]+[[:space:]]+)*//')
first=$(printf '%s' "$stripped" | awk '{print $1}')

# Not our binary — none of our business.
[ "$first" = "wxcli" ] || allow

group=$(printf '%s' "$stripped" | awk '{print $2}')
sub=$(printf '%s' "$stripped" | awk '{print $3}')

# `wxcli`, `wxcli --help`, `wxcli --version`
case "$group" in
  "" | -*) allow ;;
  whoami)  allow ;;
esac

case "$sub" in
  -*) allow ;;   # `wxcli <group> --help`
  "") deny "$cmd" ;;   # bare `wxcli configure` / `switch-org` / `clear-org` mutate state
esac

# Leading verb before the first hyphen: show-call-forwarding -> show
verb=${sub%%-*}
case "$verb" in
  list|show) allow ;;
  *)         deny "$cmd" ;;
esac
