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
pass=0; fail=0

# check <expected> <agent_type> <command>
check() {
  exp=$1; agent=$2; cmd=$3
  got=$(jq -nc --arg a "$agent" --arg c "$cmd" \
        '{agent_type:$a,tool_input:{command:$c}}' \
        | sh "$HOOK" | jq -r '.hookSpecificOutput.permissionDecision')
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
fi
