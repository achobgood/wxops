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

# Resolve wxcli by RESOLVED BASENAME, in every segment of a compound command.
#
# 2026-07-28: the previous version did `first=$(awk '{print $1}')` and then
# `[ "$first" = "wxcli" ] || allow` — string equality on token 1, falling open.
# Measured, 14 of 15 spellings walked straight past it: `/opt/homebrew/bin/wxcli
# organizations delete`, `./wxcli`, `env wxcli`, `bash -c "wxcli ..."`,
# `cd /tmp && wxcli ...`, `true; wxcli ...`, `xargs wxcli ...`, `"wxcli"`,
# `\wxcli`, `command wxcli`, `nohup wxcli ...`.  Worst of all, this repo's own
# audit prompt instructs subagents to invoke the FULL PATH, because a bare
# `wxcli` is frequently not on a subagent's PATH — so the recommended
# invocation was exactly the one that disabled the gate, and it had been inert
# for every subagent that followed instructions.
#
# awk splits on ; && || | and newline so each segment is judged on its own —
# `wxcli people list && wxcli locations delete X` is not a read — unquotes and
# de-backslashes each token, takes the basename, and applies the read-only
# policy itself.  It prints DENY for any state-changing invocation and FOUND if
# it saw any wxcli invocation at all.
verdict=$(printf '%s' "$cmd" | awk '
  function clean(t) { gsub(/^\\+/,"",t); gsub(/^["'"'"']+/,"",t); gsub(/["'"'"']+$/,"",t); return t }
  function base(t)  { sub(/^.*\//,"",t); return t }
  { line = line $0 "\n" }
  END {
    gsub(/\|\|/,"\n",line); gsub(/&&/,"\n",line); gsub(/;/,"\n",line); gsub(/\|/,"\n",line)
    # Wrappers that take another command as an argument.  Only inside one of
    # these do we scan past the command position — otherwise `grep -rn wxcli
    # docs/` reads as an invocation, and denying an ordinary grep is its own bug.
    split("env command nohup nice time xargs sudo stdbuf setsid sh bash zsh", w, " ")
    for (k in w) wrap[w[k]] = 1
    n = split(line, segs, "\n")
    for (i = 1; i <= n; i++) {
      m = split(segs[i], tok, /[ \t]+/)
      j = 1
      # Skip blank fields (splitting on the delimiters leaves a leading empty
      # token on every segment after the first) and VAR=val prefixes.
      while (j <= m && (clean(tok[j]) == "" || clean(tok[j]) ~ /^[A-Za-z_][A-Za-z0-9_]*=/)) j++
      if (j > m) continue
      idx = 0
      if (base(clean(tok[j])) == "wxcli") idx = j
      else if (base(clean(tok[j])) in wrap)
        for (k = j+1; k <= m; k++) if (base(clean(tok[k])) == "wxcli") { idx = k; break }
      if (!idx) continue
      found = 1
      # --help anywhere is inert: it prints and exits before any API call, and
      # the playbook REQUIRES agents to run it before first use of a command.
      # The old gate denied `wxcli <group> <cmd> --help`; that never surfaced
      # only because the full-path bypass was carrying every such call.
      help = 0
      for (k = idx+1; k <= m; k++) if (clean(tok[k]) == "--help" || clean(tok[k]) == "-h") help = 1
      if (help) continue
      g = (idx+1 <= m) ? clean(tok[idx+1]) : ""
      s = (idx+2 <= m) ? clean(tok[idx+2]) : ""
      if (g == "" || substr(g,1,1) == "-" || g == "whoami") continue   # wxcli / --version / whoami
      if (s == "") { print "DENY"; continue }  # bare `wxcli configure` mutates state
      verb = s; sub(/-.*$/,"",verb)            # show-call-forwarding -> show
      if (verb != "list" && verb != "show") print "DENY"
    }
    if (found) print "FOUND"
  }
')

# Matched on a resolved token, never a substring, so `cat wxcli-notes.md` and
# `python tools/drift_check.py` stay allowed.  Residual, stated rather than
# papered over: a token this cannot resolve statically — `$(echo wxcli) ...`,
# or a shell alias — is still invisible here.  A hook sees only the command
# string; this is a guard rail, not a proof.
case "$verdict" in
  *DENY*) deny "$cmd" ;;
  *)      allow ;;
esac
