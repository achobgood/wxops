"""The drift gate must be able to say "I did not run" — guards for exit code 2.

Why this file exists, precisely. `import yaml` at check 15 was unavailable in
CI's drift-gate job (which deliberately installed nothing), so the gate died
before check 1 and verified NOTHING. An unhandled traceback exits 1 — and 1 is
also "ran, found problems" — so a dead gate and a working one produced the same
red X. Four consecutive red builds were read as "we know why that's failing".
Nothing was actually checked between 2026-07-25 and 2026-08-04.

The fix has two halves and BOTH are load-bearing, so both are pinned here:
  1. drift_check.py exits 2 on an unexpected exception, and says CRASHED on the
     same `result:` line a reader already greps for.
  2. ci.yml treats 2 as its own failure AND asserts the run reached the end,
     which catches a partial run that somehow still exits 0.

The three-state behaviour itself (0 clean / 1 findings / 2 crashed) was proven by
mutation when it landed: removing PyYAML from a venv reproduced the original
outage and returned 2 rather than 1; a planted dead `wxcli` reference returned 1
with `[2] dead wxcli references: 1`; reverting it returned 0. That proof is not
repeated here because reproducing it costs a fresh venv and a full ~40s gate run
per state. What IS cheap, and what actually regressed in the real incident, is
the WIRING — so that is what these tests hold.
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "tools" / "drift_check.py"
CI = REPO / ".github" / "workflows" / "ci.yml"


def _main_guard() -> ast.If:
    """The `if __name__ == "__main__":` block, as an AST node."""
    tree = ast.parse(GATE.read_text())
    for node in tree.body:
        if (isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"):
            return node
    raise AssertionError("drift_check.py has no `if __name__ == '__main__':` block")


def test_crash_is_caught_and_exits_2():
    """A traceback must not exit 1, because 1 already means "found problems"."""
    guard = _main_guard()
    handlers = [h for n in ast.walk(guard) if isinstance(n, ast.Try) for h in n.handlers]
    assert handlers, (
        "drift_check.py's __main__ block does not catch anything. An unhandled "
        "exception exits 1, which is indistinguishable from a findings failure — "
        "the exact condition that hid an 11-day gate outage."
    )
    exits = [
        int(n.args[0].value)
        for h in handlers
        for n in ast.walk(h)
        if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "exit"
        and n.args and isinstance(n.args[0], ast.Constant)
        and isinstance(n.args[0].value, int)
    ]
    assert 2 in exits, f"crash handler must sys.exit(2), found exits {exits}"


def test_crash_handler_does_not_swallow_ctrl_c():
    """KeyboardInterrupt/SystemExit are BaseException — catching those would both
    report Ctrl-C as a gate crash and intercept main()'s own exit code."""
    guard = _main_guard()
    caught = [
        h.type.id
        for n in ast.walk(guard) if isinstance(n, ast.Try)
        for h in n.handlers
        if isinstance(h.type, ast.Name)
    ]
    assert "BaseException" not in caught, (
        "catching BaseException swallows KeyboardInterrupt and SystemExit; "
        f"catch Exception instead (currently catches {caught})"
    )
    assert caught, "crash handler must name an exception type, not a bare except"


def test_crash_says_so_on_the_result_line():
    """`result:` is the line every reader and the CI assertion greps for, so a
    crash has to speak there — a stderr-only traceback is what got missed."""
    body = GATE.read_text()
    assert "result: CRASHED" in body, (
        "the crash path must print a `result: CRASHED` line; a reader greps "
        "`result:` and would otherwise see nothing at all"
    )


def test_ci_distinguishes_a_crash_and_asserts_completion():
    """Half the fix lives in the workflow. If someone reduces this step back to a
    bare `python -m tools.drift_check --enforce`, a crash silently reads as
    findings again and a truncated run reads as a pass."""
    ci = CI.read_text()
    assert "-m tools.drift_check" in ci, (
        "CI must invoke the gate as a module — the script form puts tools/ on "
        "sys.path instead of the repo root and fails on `from tools.…` imports"
    )
    assert '"$status" -eq 2' in ci or "status\" -eq 2" in ci, (
        "CI must treat exit 2 (crashed) as its own outcome, not as findings"
    )
    assert r"^\[18\]" in ci and "^result: (PASS|FAIL)" in ci, (
        "CI must assert the gate REACHED THE END (last check present + a verdict "
        "line), which is what catches a partial run that still exits 0"
    )
    # Match the DIRECTIVE on its own line, not the phrase anywhere in the file —
    # a substring check passes on the explanatory comment alone, which a mutation
    # probe caught doing exactly that.
    assert any(line.strip() == "set +e" for line in ci.splitlines()), (
        "Actions runs `run:` under `bash -e`, so without `set +e` a non-zero gate "
        "aborts the step before `status=$?` and none of the branches above ever "
        "execute — the crash annotation and completion assertions become dead code"
    )
