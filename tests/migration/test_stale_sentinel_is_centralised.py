"""The `__stale__` sentinel must be spelled in exactly one module.

`"__stale__"` is a **truthy** string, so `if d.get("chosen_option")` counts an
invalidated decision as resolved. That bug shipped at nine sites across five
files, and it shipped because the sentinel was hand-written in 23 places with
no single definition to reason about — every site was an independent chance to
get the predicate wrong.

`migration/decision_state.py` now owns the spelling and the four predicates.
This test keeps it that way: a new `== "__stale__"` anywhere else fails here
rather than three months later in a customer-facing count.

Scanned via AST rather than grep so that SQL strings such as
`UPDATE decisions SET chosen_option = '__stale__'` are caught (the literal is a
substring there, not the whole value), while docstrings and comments that
*discuss* the sentinel are not.
"""

from __future__ import annotations

import ast
from pathlib import Path

SENTINEL = "__stale__"
SRC = Path(__file__).resolve().parents[2] / "src" / "wxcli"
OWNER = SRC / "migration" / "decision_state.py"


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """id() of every Constant node that is a module/class/function docstring."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _offending_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(), filename=str(path))
    skip = _docstring_nodes(tree)
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and SENTINEL in node.value
        and id(node) not in skip
    ]


def test_decision_state_is_the_only_module_that_spells_the_sentinel():
    offenders: dict[str, list[int]] = {}
    for path in sorted(SRC.rglob("*.py")):
        if path == OWNER:
            continue
        lines = _offending_lines(path)
        if lines:
            offenders[str(path.relative_to(SRC))] = lines

    assert offenders == {}, (
        "`__stale__` must only be spelled in migration/decision_state.py — "
        "use STALE / is_stale / is_resolved / is_pending instead. Found: "
        f"{offenders}"
    )


def test_the_owner_module_really_does_define_it():
    """Guards the test above from passing because the sentinel vanished."""
    lines = _offending_lines(OWNER)
    assert lines, "decision_state.py no longer defines the sentinel"

    from wxcli.migration.decision_state import STALE

    assert STALE == SENTINEL


def test_the_predicates_disagree_with_plain_truthiness():
    """The bug in one assertion: the sentinel is truthy, so `if chosen_option`
    reads an invalidated decision as resolved."""
    from wxcli.migration.decision_state import (
        STALE, is_pending, is_resolved, is_stale,
    )

    stale = {"chosen_option": STALE}
    assert bool(stale["chosen_option"]) is True  # the trap
    assert is_stale(stale) is True
    assert is_resolved(stale) is False
    assert is_pending(stale) is False

    resolved = {"chosen_option": "skip"}
    assert is_resolved(resolved) is True
    assert is_stale(resolved) is False

    pending = {"chosen_option": None}
    assert is_pending(pending) is True
    assert is_resolved(pending) is False
