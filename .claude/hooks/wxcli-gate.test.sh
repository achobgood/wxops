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

# Reads a hook payload on stdin, prints allow|deny (or a marker that fails).
decision() {
  if [ "$KIND" != codex ]; then
    sh "$HOOK" | jq -r '.hookSpecificOutput.permissionDecision'
    return
  fi
  out=$(eval "$HOOK" 2>/dev/null)
  [ -n "$out" ] || { echo allow; return; }
  # Codex refuses a deny carrying an empty reason ("PreToolUse hook returned
  # permissionDecision:deny without a non-empty permissionDecisionReason") and
  # falls OPEN, so a reasonless deny is a FAILURE, not a deny.
  reason=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecisionReason // ""')
  [ -n "$reason" ] || { echo deny-without-reason; return; }
  printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // "no-decision"'
}

# check <expected> <agent_type> <command>
check() {
  exp=$1; agent=$2; cmd=$3
  got=$(jq -nc --arg a "$agent" --arg c "$cmd" \
        '{agent_type:$a,tool_input:{command:$c}}' | decision)
  if [ "$got" = "$exp" ]; then
    pass=$((pass+1)); printf '  ok   %-6s %s\n' "$got" "$cmd"
  else
    fail=$((fail+1)); printf '  FAIL want=%-5s got=%-5s %s\n' "$exp" "$got" "$cmd"
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
check allow wxc-calling-builder 'wxcli organizations delete Y2lz'
check allow wxc-calling-builder 'wxcli cleanup run --force'
check allow migration-advisor   '/opt/homebrew/bin/wxcli locations delete Y2lz'

# The exemption is a fixed two-name list, and nothing here asserted that it is
# CLOSED. Found by mutation: widening the case to a third agent left the whole
# table green. An allowlist nobody tests for over-breadth is not an allowlist.
echo "== every other agent gets no exemption =="
check deny  some-other-agent    'wxcli locations delete Y2lz'
check deny  general-purpose     'wxcli cleanup run --force'
check deny  Explore             'wxcli organizations delete Y2lz'
check allow some-other-agent    'wxcli people list'

echo "== the Python import side door stays shut =="
check deny  "" 'python -c "import wxcli"'
check deny  "" 'python3 -c "from wxcli.commands import organizations"'
check deny  "" 'PYTHONPATH=src python -c "import src.wxcli"'

echo "== unrelated commands are none of our business =="
check allow "" 'ls -la'
check allow "" 'git status'
check allow "" 'python tools/drift_check.py --enforce'
check allow "" 'cat wxcli-quality-loop-prompt-v2.md'
check allow "" 'grep -rn wxcli docs/'
check allow "" 'ls docs/superpowers/quality-loop/artifacts/round3'

echo "== compound and nested forms =="
check deny  "" 'wxcli people list && wxcli locations delete Y2lz'
check deny  "" 'wxcli people list || wxcli organizations delete Y2lz'
check deny  "" 'sh -c "cd /tmp && /opt/homebrew/bin/wxcli cleanup run --force"'
check deny  "" 'sudo -u admin wxcli locations delete Y2lz'
check deny  "" 'nice -n 10 env FOO=1 ./wxcli people delete Y2lz'
check allow "" 'wxcli people list && wxcli locations list'
check allow "" 'wxcli locations list | jq -r ".[].id"'

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
