#!/bin/sh
# PreToolUse gate for raw `wxcli` Bash calls.  Dev-only: assemble.py substitutes
# settings.bundled.json and does not bundle .claude/hooks, so this never ships.
#
# Policy (order matters):
#   1. Python that imports wxcli is refused, for every caller.
#   2. Agents carrying the playbook rules (wxops,
#      migration-advisor) may run any wxcli command — unless the caller is an
#      agent-team teammate (see is_teammate), which is never exempt.
#   3. Anyone else (main session, other agents) may run READ-ONLY wxcli only.
#      Reads are `list*` / `show*` / `whoami` / help.  Everything else is denied:
#      the main session is sent to the builder agent, a subagent is told to stop
#      and report (never to spawn another agent).
#   4. Unknown verbs deny (fail closed).
#   5. `allow` only when EVERY segment of the command is a wxcli call this
#      caller may run.  Anything else — `ls`, `git push`, a wxcli read joined to
#      `rm` — gets NO output, so Claude Code's normal permission rules decide.
#      Until Plan 5 this gate answered `allow` there, which skipped the prompt.
#      P5-19: such wxcli calls piped ONLY into grep head tail jq wc sort cut
#      also allow (no file redirect, no sort -o, no jq -f); any other pipe
#      target, or a non-pipe join to a command that is not wxcli, does not.
#   6. Flow Store MCP tools (mcp__wxcc-flow-builder__*): the nine read tools
#      get no output; every other tool of that server runs only inside the
#      builder (unknown tools refused: fail closed).
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

BUILDER=wxops

# deny <what was refused> <first sentence for the main session>
# The reason depends on who is asking.  A caller with an agent_id is a subagent:
# telling it to spawn the builder is how the 2026-07-31 failure recursed, so it
# is told to stop and report instead.  Only the main session is told to spawn.
deny() {
  if [ "$teammate" = 1 ]; then
    reason="You are an agent-team teammate, not the $BUILDER agent this gate exempts: agent teams are on, so a named spawn became a teammate the safety lock cannot identify: spawn the $BUILDER agent without a name, or turn agent teams off (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0). Do not spawn another agent yourself. Stop and tell your caller exactly that, with this step: $1"
  elif [ -n "$agent_id" ]; then
    if [ -n "$agent" ]; then who="a \`$agent\` subagent"; else who="a subagent that reports no agent type"; fi
    reason="You are inside $who, and only the $BUILDER agent may change the org. Do not spawn another agent. Stop and tell your caller that this step needs the $BUILDER agent: $1"
  else
    reason="$2 REQUIRED ACTION: Do NOT run it directly again. Spawn the $BUILDER agent (subagent_type \"$BUILDER\") — any name you give it is fine; this gate matches the agent's type, not its name — and pass it this intent: $1 — The agent handles auth, planning, execution, and verification."
  fi
  jq -nc --arg r "$reason" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

deny_import() {
  jq -nc '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"Importing wxcli from Python bypasses this gate, the read-only verb policy, and the confirm prompt — those live above the Python layer. Functions in src/wxcli/commands/ make REAL HTTP calls to the live org, and a Typer default is an OptionInfo (truthy), so force=False does not mean what it reads like. REQUIRED ACTION: read the code instead of running it. The confirm string, URL, method and docstring are all literals in the file — use Read/Grep, or parse it with ast (reading a file is fine, importing it is not). If a layer genuinely must be exercised, monkeypatch the HTTP layer first, or ask Adam. `wxcli <cmd> --help` is safe."}}'
  exit 0
}

# Plan 5 (P5-17).  With agent teams on, Claude Code turns a NAMED spawn into an
# in-process teammate, and a teammate's hook agent_type is its spawn NAME, not
# its definition — so a general-purpose agent named like the builder arrived as
# the builder (measured, interactive, Claude Code 2.1.304; headless never makes
# teammates).  Two undocumented signals, used ONLY to deny, so when they drift
# the lock fails closed and never open:
#   - the id shape a<agent_type>-<16 hex> (ordinary subagent ids are a<17 hex>);
#   - the meta file beside the session transcript, taskKind in_process_teammate.
is_teammate() {
  [ -n "$agent_id" ] || return 1
  if [ -n "$agent" ]; then
    case "$agent_id" in
      "a$agent-"*)
        hex=${agent_id#"a$agent-"}
        if [ "${#hex}" -eq 16 ]; then
          case "$hex" in *[!0-9a-f]*) ;; *) return 0 ;; esac
        fi
        ;;
    esac
  fi
  case "$agent_id" in */*) return 1 ;; esac
  [ -n "$transcript" ] || return 1
  meta="${transcript%.jsonl}/subagents/agent-$agent_id.meta.json"
  [ -f "$meta" ] || return 1
  [ "$(jq -r '.taskKind // ""' "$meta" 2>/dev/null)" = in_process_teammate ]
}

input=$(cat)
agent=$(printf '%s' "$input" | jq -r '.agent_type // ""')
agent_id=$(printf '%s' "$input" | jq -r '.agent_id // ""')
tool=$(printf '%s' "$input" | jq -r '.tool_name // ""')
transcript=$(printf '%s' "$input" | jq -r '.transcript_path // ""')
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')

teammate=0
is_teammate && teammate=1
exempt=0
case "$agent" in
  wxops|migration-advisor) [ "$teammate" = 1 ] || exempt=1 ;;
esac

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

# Flow Store MCP tools have no command string, so the tool name is what is
# judged and what the deny quotes.  The read tools get no decision (the
# permission rules already pre-allow them); a new tool the server grows is
# refused until someone classifies it.
case "$tool" in
  mcp__wxcc-flow-builder__*)
    case "${tool#mcp__wxcc-flow-builder__}" in
      list_flows|get_flow|validate_flow|get_flow_template|get_activity_definitions|\
      get_activity_node_schema|describe_activity|get_choices|list_event_specifications)
        exit 0 ;;
    esac
    [ "$exempt" = 1 ] && allow
    deny "the Flow Store tool $tool" "Only the Flow Store's read tools may run outside the $BUILDER agent; $tool changes flows or is unrecognized."
    ;;
esac

# The trusted-agent exemption is applied below, to wxcli segments only.  Until
# Plan 5 an early `allow` here approved EVERY command a trusted agent ran,
# `git push --force` included.

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
# policy itself.  It prints four counts: non-blank segments, segments that
# invoke wxcli, wxcli segments that are not a read for a non-exempt caller,
# and whether a redirect to a file is left once fd duplications are removed.
# That scan ignores quotes, so it can only ever see MORE commands than the
# shell will run: right for a deny.  The allow decision needs the opposite, so
# qscan below reads the same command WITH its quotes (P5-19).
verdict=$(printf '%s' "$cmd" | awk '
  function clean(t) { gsub(/^[({]+/,"",t); gsub(/[)}]+$/,"",t); gsub(/^\\+/,"",t); gsub(/^["'"'"']+/,"",t); gsub(/["'"'"']+$/,"",t); return t }
  function base(t)  { sub(/^.*\//,"",t); return t }
  # A token that is wxcli and nothing else: a quoted token may hold spaces and
  # a whole script ("rm -rf x; /bin/wxcli"), whose basename would be wxcli.
  function iswx(t)  { return t !~ /[ \t\n;|&<>`$(){}*?]/ && base(t) == "wxcli" }
  function qpush()  { if (intok || cur != "") { qn[nq]++; qt[nq, qn[nq]] = cur }; cur = ""; intok = 0 }
  function qcut(np) { qpush(); if (np) qsep = 1; nq++; qn[nq] = 0 }
  # P5-19: an approved pipe target, named bare as the FIRST token of its
  # segment (no path, no VAR= prefix: LD_PRELOAD=… runs code).  Its arguments
  # are data, except those that write a file, run a program or read a script.
  function okpipe(q, m,   name, k, a) {
    name = qt[q,1]
    if (!(name in pipeok)) return 0
    for (k = 2; k <= m; k++) {
      a = qt[q,k]
      if (name == "jq" && (a ~ /^-[A-Za-z]*f/ || a ~ /^--(from-file|rawfile|slurpfile)/)) return 0
      # sort -o FILE writes; GNU long options take any unambiguous prefix
      # (--out=, --comp…), and --compress-program runs a program.
      if (name == "sort" && (a ~ /^-[A-Za-z]*o/ || a ~ /^--(o|co)/)) return 0
    }
    return 1
  }
  # P5-19.  Split on UNQUOTED | |& || && ; & and newline into qt[segment,
  # token] with the quotes removed.  qsep: anything but a pipe joined two
  # segments.  qred: an unquoted redirect to a file (not /dev/null, not an fd
  # duplication).  qerr: something this cannot read safely, so no allow: an
  # unquoted # (a comment can hide a quote from this reader but not from the
  # shell), an open quote, <( or <>.
  function qscan(s,   n, i, c, sq, j, y) {
    sq = "'"'"'"; nq = 1; qn[1] = 0; cur = ""; intok = 0; st = 0
    n = length(s)
    for (i = 1; i <= n; i++) {
      c = substr(s, i, 1)
      if (st == 1) { if (c == sq) st = 0; else cur = cur c; continue }
      if (st == 2) {
        if (c == "\\" && i < n) { i++; cur = cur substr(s, i, 1); continue }
        if (c == "\"") st = 0; else cur = cur c
        continue
      }
      if (c == "\\" && i < n) { i++; if (substr(s, i, 1) != "\n") cur = cur substr(s, i, 1); intok = 1; continue }
      if (c == sq) { st = 1; intok = 1; continue }
      if (c == "\"") { st = 2; intok = 1; continue }
      if (c == " " || c == "\t") { qpush(); continue }
      if (c == "#" && !intok && cur == "") { qerr = 1; continue }
      if (c == "<") {
        if (substr(s, i+1, 1) == ">" || substr(s, i+1, 1) == "(") qerr = 1
        if (cur ~ /^[0-9]+$/) cur = ""
        qpush()
        if (substr(s, i+1, 1) == "&") { i++; while (substr(s, i+1, 1) ~ /[0-9-]/) i++ }
        continue
      }
      if (c == ">" || (c == "&" && substr(s, i+1, 1) == ">")) {
        if (c == "&") i++
        else if (cur ~ /^[0-9]+$/) cur = ""
        qpush()
        if (substr(s, i+1, 1) == "&") {
          # `>&N` (one or more digits) and `>&-` (blanks allowed before either),
          # then a word boundary, duplicate or close an fd and write no file.
          # Any other word sends stdout and stderr to the FILE `word`, the same
          # as `&>word`. That includes `-5`, `--`, `2-5` and the bash move form
          # `N-` (`>&2-`), which zsh may read as a filename: fail-safe, no allow.
          i++
          while (substr(s, i+1, 1) ~ /[ \t]/) i++
          j = i
          while (substr(s, j+1, 1) ~ /[0-9]/) j++
          if (j == i && substr(s, i+1, 1) == "-") j++
          y = substr(s, j+1, 1)
          if (j > i && (y == "" || y ~ /[ \t\n;|&<>()]/)) { i = j; continue }
          x = substr(s, i+10, 1)
          if (substr(s, i+1, 9) == "/dev/null" && (x == "" || x ~ /[ \t\n;|&]/)) { i += 9; continue }
          qred = 1
          continue
        }
        if (substr(s, i+1, 1) == ">" || substr(s, i+1, 1) == "|") i++
        while (substr(s, i+1, 1) ~ /[ \t]/) i++
        x = substr(s, i+10, 1)
        if (substr(s, i+1, 9) == "/dev/null" && (x == "" || x ~ /[ \t\n;|&]/)) i += 9
        else qred = 1
        continue
      }
      if (c == "|") {
        if (substr(s, i+1, 1) == "|") { i++; qcut(1); continue }
        if (substr(s, i+1, 1) == "&") i++
        qcut(0); continue
      }
      if (c == "&") { if (substr(s, i+1, 1) == "&") i++; qcut(1); continue }
      if (c == ";" || c == "\n") { qcut(1); continue }
      cur = cur c; intok = 1
    }
    qpush()
    if (st != 0) qerr = 1
  }
  { line = line $0 "\n" }
  END {
    raw = line; sub(/\n+$/, "", raw)
    # fd duplications (2>&1, >&2, <&0, >&-) are not command separators and
    # write no file; `&>` / `&>>` redirect to a file.  Then a lone `&` (run
    # in background) separates commands like `;` does: `<read> & <write>`
    # is two commands.  A redirect to /dev/null writes nothing.
    gsub(/[0-9]*[<>]&[0-9-]+/," ",line); gsub(/&>>?/," >",line)
    gsub(/[0-9]*>>?[ \t]*\/dev\/null/," ",line)
    redir = (line ~ />/)
    gsub(/\|\|/,"\n",line); gsub(/&&/,"\n",line); gsub(/;/,"\n",line); gsub(/\|/,"\n",line)
    gsub(/&/,"\n",line)
    # Wrappers that take another command as an argument.  Only inside one of
    # these do we scan past the command position — otherwise `grep -rn wxcli
    # docs/` reads as an invocation, and denying an ordinary grep is its own bug.
    split("env command nohup nice time xargs sudo stdbuf setsid sh bash zsh exec eval", w, " ")
    # Shell keywords that put a command after them: `for …; do <cmd>`,
    # `if …; then <cmd>`, `! <cmd>`.  Skipped at command position like VAR=.
    split("do then else elif if while until !", kw, " ")
    for (k in kw) skipkw[kw[k]] = 1
    for (k in w) wrap[w[k]] = 1
    n = split(line, segs, "\n")
    for (i = 1; i <= n; i++) {
      m = split(segs[i], tok, /[ \t]+/)
      j = 1
      # Skip blank fields (splitting on the delimiters leaves a leading empty
      # token on every segment after the first) and VAR=val prefixes.
      # Every segment with any text counts, assignment-only ones included:
      # `wxcli people list; X=$(rm -rf /tmp/y)` is not all wxcli.
      blank = 1
      for (k = 1; k <= m; k++) if (tok[k] != "") blank = 0
      if (blank) continue
      nseg++
      while (j <= m && (clean(tok[j]) == "" || clean(tok[j]) ~ /^[A-Za-z_][A-Za-z0-9_]*=/ || clean(tok[j]) in skipkw)) j++
      if (j > m) continue
      idx = 0
      if (base(clean(tok[j])) == "wxcli") idx = j
      else if (base(clean(tok[j])) in wrap)
        for (k = j+1; k <= m; k++) if (base(clean(tok[k])) == "wxcli") { idx = k; break }
      if (!idx) continue
      nwx++
      # --help anywhere is inert: it prints and exits before any API call, and
      # the playbook REQUIRES agents to run it before first use of a command.
      # The old gate denied `wxcli <group> <cmd> --help`; that never surfaced
      # only because the full-path bypass was carrying every such call.
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
      if (s == "") { ndeny++; continue }  # bare `wxcli configure` mutates state
      verb = s; sub(/-.*$/,"",verb)            # show-call-forwarding -> show
      if (verb != "list" && verb != "show") ndeny++
    }
    # P5-19: the same command read with its quotes, for the allow decision.
    # qwx: segments that are a wxcli call — wxcli itself, or a wrapper whose
    # following tokens are only options, numbers, VAR=val or more wrappers up
    # to wxcli (so `env rm -rf X wxcli` is NOT one).  qdeny: those that are
    # not a read.  qbad: the other segments that are not an approved pipe
    # target (okpipe).
    split("grep head tail jq wc sort cut", r, " ")
    for (k in r) pipeok[r[k]] = 1
    qscan(raw)
    for (q = 1; q <= nq; q++) {
      m = qn[q]
      if (m == 0) continue
      qseg++
      j = 1
      while (j <= m && (clean(qt[q,j]) == "" || clean(qt[q,j]) ~ /^[A-Za-z_][A-Za-z0-9_]*=/ || clean(qt[q,j]) in skipkw)) j++
      if (j > m) { qbad++; continue }
      idx = 0
      if (iswx(clean(qt[q,j]))) idx = j
      else if (base(clean(qt[q,j])) in wrap)
        for (k = j+1; k <= m; k++) {
          a = clean(qt[q,k])
          if (iswx(a)) { idx = k; break }
          if (a ~ /^-/ || a ~ /^[0-9]+$/ || a ~ /^[A-Za-z_][A-Za-z0-9_]*=/ || base(a) in wrap) continue
          break
        }
      if (!idx) { if (!okpipe(q, m)) qbad++; continue }
      qwx++
      help = 0
      for (k = idx+1; k <= m; k++) if (clean(qt[q,k]) == "--help" || clean(qt[q,k]) == "-h") help = 1
      if (help) continue
      p = idx + 1
      while (p <= m && (clean(qt[q,p]) == "" || substr(clean(qt[q,p]),1,1) == "-")) p++
      g = (p <= m) ? clean(qt[q,p]) : ""
      v = (p+1 <= m) ? clean(qt[q,p+1]) : ""
      if (g == "" || g == "whoami") continue
      if (v == "") { qdeny++; continue }
      sub(/-.*$/,"",v)
      if (v != "list" && v != "show") qdeny++
    }
    print nseg+0, nwx+0, ndeny+0, redir+0, qseg+0, qwx+0, qdeny+0, qbad+0, qsep+0, qred+0, qerr+0
  }
')

# Matched on a resolved token, never a substring, so `cat wxcli-notes.md` and
# `python tools/drift_check.py` stay allowed.  Residual, stated rather than
# papered over: a token this cannot resolve statically — `$(echo wxcli) ...`,
# or a shell alias — is still invisible here.  A hook sees only the command
# string; this is a guard rail, not a proof.
set -- $verdict
# nseg nwx redir: the quote-blind scan (only ndeny decides anything now).
nseg=$1 nwx=$2 ndeny=$3 redir=$4
qseg=$5 qwx=$6 qdeny=$7 qbad=$8 qsep=$9 qred=${10} qerr=${11}

# `allow` skips Claude Code's permission prompt, so it is given only when the
# whole command is wxcli calls this caller may run — or (P5-19, Adam
# 2026-10-20) wxcli calls joined only by pipes to grep head tail jq wc sort
# cut (okpipe).  A command substitution hides a second
# command inside a segment, and a redirect to a file writes that file, so
# neither ever earns an allow.
pure=0
if [ "$qwx" -gt 0 ] && [ "$qred" = 0 ] && [ "$qerr" = 0 ] &&
   { [ "$qwx" -eq "$qseg" ] || { [ "$qsep" = 0 ] && [ "$qbad" = 0 ]; }; }; then
  case "$cmd" in
    *'$('*|*'`'*|*'<('*) ;;
    *) pure=1 ;;
  esac
fi

if [ "$exempt" = 1 ]; then
  [ "$pure" = 1 ] && allow
  exit 0
fi
[ "$ndeny" -gt 0 ] && deny "$cmd" "Only read-only wxcli (list*/show*/whoami/--help) may run outside the $BUILDER agent. This command changes state or is unrecognized."
[ "$pure" = 1 ] && [ "$qdeny" = 0 ] && allow
exit 0
