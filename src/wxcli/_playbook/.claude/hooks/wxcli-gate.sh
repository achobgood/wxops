#!/bin/sh
# PreToolUse gate for raw `wxcli` Bash calls — SHIPPED copy.
#
# assemble.py substitutes this file for .claude/hooks/wxcli-gate.sh in the
# bundle, the same way it substitutes settings.bundled.json for
# .claude/settings.json.  The development copy cites repo paths that do not
# exist in an installed playbook; this one is written for a machine that has
# the wxcli package installed and no source checkout.  Keep the POLICY here
# identical to the development copy — only the guidance text differs.
#
# Policy:
#   - Agents carrying the playbook rules (wxc-calling-builder, migration-advisor)
#     may run anything.  They are the reason this gate exists: the rules that
#     make a wxcli call correct travel with the agent, not with the caller.
#   - Anyone else (main session, other agents) may run READ-ONLY wxcli only.
#     Reads are `list*` / `show*` / `whoami` / help.  Everything else is denied
#     and redirected to the builder agent.
#   - Unknown verbs deny (fail closed).
#
# `get*` is deliberately NOT a read: all four get-* commands issue a POST
# (get-domain-verification, get-customer-device, get-location-device,
# get-device-dynamic).  A read-sounding name is not evidence of a read.

set -u

allow() {
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
  exit 0
}

# Emitted when jq is unavailable, so the gate cannot parse its input.  A hook
# that cannot evaluate must not fall open on a wxcli call: this is a fixed
# literal precisely so it needs no jq to build.
deny_nojq() {
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"The wxcli safety gate requires the `jq` command and it is not on PATH, so this call cannot be evaluated. Rather than allow an unchecked wxcli invocation, it is refused. REQUIRED ACTION: install jq (macOS: it ships at /usr/bin/jq on recent versions, otherwise `brew install jq`; Debian/Ubuntu: `apt install jq`), or run this work through the wxc-calling-builder agent."}}'
  exit 0
}

deny() {
  jq -nc --arg c "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:("Only read-only wxcli (list*/show*/whoami) may run outside an agent. This command changes state or is unrecognized. REQUIRED ACTION: Do NOT run wxcli directly again. Spawn the wxc-calling-builder agent (subagent_type=\"wxc-calling-builder\") and pass it this intent: " + $c + " — The agent handles auth, planning, execution, and verification.")}}'
  exit 0
}

deny_import() {
  jq -nc '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"Importing wxcli from Python bypasses this gate, the read-only verb policy, and the confirm prompt — those live above the Python layer. The command functions in the installed wxcli package make REAL HTTP calls to the live org, and a Typer default is an OptionInfo (truthy), so force=False does not mean what it reads like. REQUIRED ACTION: do not call command functions directly. Use `wxcli <command> --help` to inspect a command, or run the work through the wxc-calling-builder agent. If a layer genuinely must be exercised, monkeypatch the HTTP layer first."}}'
  exit 0
}

input=$(cat)

# No jq: refuse wxcli calls, pass everything else through.  Denying every Bash
# command would be its own outage; silently allowing wxcli would be worse than
# shipping no gate at all, because the operator would believe one was running.
if ! command -v jq >/dev/null 2>&1; then
  case "$input" in
    *wxcli*) deny_nojq ;;
    *) allow ;;
  esac
fi

agent=$(printf '%s' "$input" | jq -r '.agent_type // ""')
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')

# The side door.  Everything below only inspects commands whose first token is
# `wxcli`, so Python that imports the CLI walks straight past it.  2026-07-28: a
# subagent imported four generated delete functions to see whether they crash;
# the OptionInfo-is-truthy trap skipped the confirm prompt and three unconfirmed
# DELETEs reached the live org, one of them DELETE /v1/organizations/{id}.  Only
# the API refusing them saved it.
#
# Matched on an IMPORT of wxcli, not on the string `wxcli/commands`: reading
# command source as text is fine and must stay unblocked.  Checked before the
# agent exemption below: the builder is trusted to run wxcli, not to bypass it.
# Limit, stated: a hook sees only the command string, so a .py file on disk that
# imports wxcli is invisible here.  This is a guard rail, not a proof.
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

# Agents that carry the playbook rules run unrestricted.  This `allow` is what
# lets the bundle drop a blanket Bash(wxcli:*) permission: a PreToolUse allow
# satisfies the permission layer, so the agent is never prompted.
case "$agent" in
  wxc-calling-builder|migration-advisor) allow ;;
esac

# Resolve wxcli by RESOLVED BASENAME, in every segment of a compound command.
#
# An earlier version compared only token 1 for string equality and fell open on
# 14 of 15 spellings: `/usr/local/bin/wxcli organizations delete`, `./wxcli`,
# `env wxcli`, `bash -c "wxcli ..."`, `cd /tmp && wxcli ...`, `true; wxcli ...`,
# `xargs wxcli ...`, `"wxcli"`, `\wxcli`, `command wxcli`, `nohup wxcli ...`.
# A full-path invocation is common for subagents, because a bare `wxcli` is
# frequently not on a subagent's PATH — so the usual invocation was exactly the
# one that disabled the gate.
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
      help = 0
      for (k = idx+1; k <= m; k++) if (clean(tok[k]) == "--help" || clean(tok[k]) == "-h") help = 1
      if (help) continue
      # Skip LEADING GLOBAL OPTIONS before judging the group.  Treating "starts
      # with a dash" as inert fell open on `wxcli --no-update-check
      # organizations delete Y2lz`: the gate read --no-update-check as the group
      # and waved a real org delete through.  All four top-level options
      # (--version, --no-update-check, --install-completion, --show-completion)
      # are boolean flags, so none consumes a following value and skipping is
      # unambiguous.  A trailing-only flag run (`wxcli --version`) leaves g
      # empty and is still inert.
      p = idx + 1
      while (p <= m && (clean(tok[p]) == "" || substr(clean(tok[p]),1,1) == "-")) p++
      g = (p <= m) ? clean(tok[p]) : ""
      s = (p+1 <= m) ? clean(tok[p+1]) : ""
      if (g == "" || g == "whoami") continue   # wxcli / --version / whoami
      if (s == "") { print "DENY"; continue }  # bare `wxcli configure` mutates state
      verb = s; sub(/-.*$/,"",verb)            # show-call-forwarding -> show
      if (verb != "list" && verb != "show") print "DENY"
    }
    if (found) print "FOUND"
  }
')

# Matched on a resolved token, never a substring, so `cat wxcli-notes.md` stays
# allowed.  Residual, stated rather than papered over: a token this cannot
# resolve statically — `$(echo wxcli) ...`, or a shell alias — is still
# invisible here.  A hook sees only the command string.
case "$verdict" in
  *DENY*) deny "$cmd" ;;
  *)      allow ;;
esac
