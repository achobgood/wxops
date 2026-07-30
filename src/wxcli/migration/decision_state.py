"""Canonical predicates for decision resolution state.

One question — *is this decision actually resolved?* — asked identically
everywhere.

``store.merge_decisions`` invalidates a decision by writing the sentinel
``chosen_option = '__stale__'`` (see ``store.py``). That string is **truthy**,
so the natural-looking ``if d.get("chosen_option")`` counts an invalidated
decision as resolved. Round-3 finding F04 found that exact truthiness bug live
at nine call sites across three report modules, where it rendered
``Incompatible Devices (405) — 405/405 resolved`` with every row labelled
"Auto-resolved" on a dataset where nothing had decided anything.

The three states are mutually exclusive and exhaustive:

===============  ===================  ==========================================
``chosen_option``  state                meaning
===============  ===================  ==========================================
``None``         :func:`is_pending`   live, waiting on a chooser
``'__stale__'``  :func:`is_stale`     invalidated — re-analysis rewrote the
                                      fingerprint, so nothing decided it
anything else    :func:`is_resolved`  something actually chose this option
===============  ===================  ==========================================

Import these rather than comparing against the sentinel by hand. Counting
"resolved" and counting "not stale" are different questions and the difference
is the bug.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

__all__ = [
    "STALE",
    "is_stale",
    "is_resolved",
    "is_pending",
    "live",
    "stale_only",
    "DecisionCounts",
    "count_decisions",
]

#: Sentinel written into ``decisions.chosen_option`` when a decision is
#: invalidated by a later ``merge_decisions`` pass. Truthy — never test a
#: decision's resolution by the truthiness of ``chosen_option``.
STALE = "__stale__"

Decision = Mapping[str, Any]


def is_stale(decision: Decision) -> bool:
    """True when the pipeline invalidated this decision.

    A stale decision is *not* resolved and *not* pending — it no longer
    describes the environment at all. Re-running ``analyze`` after the
    underlying object changed rewrites the decision's fingerprint, and the
    old row is stale-marked rather than deleted so the history survives.
    """
    return decision.get("chosen_option") == STALE


def is_resolved(decision: Decision) -> bool:
    """True only when something actually chose an option.

    An auto-rule, an operator, or a batch resolution. Explicitly False for the
    :data:`STALE` sentinel — "the pipeline threw this away" is not an answer.
    """
    chosen = decision.get("chosen_option")
    return chosen is not None and chosen != STALE


def is_pending(decision: Decision) -> bool:
    """True when this decision is live and still waiting on a chooser."""
    return decision.get("chosen_option") is None


def live(decisions: Iterable[Decision]) -> list[Decision]:
    """The decisions that still describe the environment — everything but stale."""
    return [d for d in decisions if not is_stale(d)]


def stale_only(decisions: Iterable[Decision]) -> list[Decision]:
    """The invalidated population, which callers must be able to report on."""
    return [d for d in decisions if is_stale(d)]


@dataclass(frozen=True)
class DecisionCounts:
    """A decision population split into its three mutually exclusive states.

    ``resolved + pending + stale == total`` always holds, which is what makes a
    headline count and its itemisation reconcilable.
    """

    total: int = 0
    resolved: int = 0
    pending: int = 0
    stale: int = 0

    @property
    def live_total(self) -> int:
        """Decisions that still describe the environment: resolved + pending."""
        return self.resolved + self.pending

    @property
    def resolved_pct(self) -> int:
        """Percent of the *live* population that is resolved (0 when none live)."""
        if self.live_total == 0:
            return 0
        return round(self.resolved / self.live_total * 100)


def count_decisions(decisions: Iterable[Decision]) -> DecisionCounts:
    """Split a decision population into resolved / pending / stale."""
    resolved = pending = stale = 0
    for d in decisions:
        if is_stale(d):
            stale += 1
        elif is_pending(d):
            pending += 1
        else:
            resolved += 1
    return DecisionCounts(
        total=resolved + pending + stale,
        resolved=resolved,
        pending=pending,
        stale=stale,
    )
