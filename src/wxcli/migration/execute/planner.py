"""Execution planner — expand canonical objects into migration operations.

Each canonical object type has a deterministic expansion pattern that produces
one or more MigrationOp nodes for the dependency DAG. The planner only expands
objects at status 'analyzed' (all decisions resolved). Objects at
'needs_decision' are skipped.

(from 05-dependency-graph.md — expand_to_operations lines 38-75)

Silent-skip visibility (2026-04-15):
  Every short-circuit path that drops a canonical entity from plan_operations
  must emit a ``logger.warning`` and record into ``PlannerSkipReport``. The
  aggregate summary is logged at the end of ``expand_to_operations`` so
  operators can see the full roll-up of skipped entities. This guards
  against the ``DEVICE_FIRMWARE_CONVERTIBLE`` class of bug where a stale
  decision silently dropped 611 convertible phones from the plan.
"""

from __future__ import annotations

import contextvars
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from wxcli.migration.execute import (
    API_CALL_ESTIMATES,
    BULK_DEVICE_THRESHOLD_DEFAULT,
    MigrationOp,
    ORG_WIDE_TYPES,
    TIER_ASSIGNMENTS,
)
from wxcli.migration.decision_state import is_stale
from wxcli.migration.execute.handlers import RECONCILE_RULES
from wxcli.migration.store import MigrationStore

# The location field name differs per canonical type (``location_id`` on some,
# ``location_canonical_id`` on others). Reuse the analyzer's ordering instead of
# hardcoding one name. Import direction is execute → transform; transform never
# imports execute, so there is no cycle.
from wxcli.migration.transform.analyzers.cross_site import (
    _LOCATION_FIELDS,
    resolve_entity_location,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Silent-skip visibility (2026-04-15)
# ---------------------------------------------------------------------------

@dataclass
class PlannerSkipEntry:
    """One skip event — identifies the entity, reason, and consequence."""
    canonical_id: str
    entity_type: str
    reason: str                       # short machine-readable reason code
    decision_type: str | None = None  # DecisionType if skip was decision-gated
    decision_state: str | None = None # "stale" | "pending" | "skip" | "virtual_line" | None
    consequence: str = ""             # human-readable consequence (one sentence)
    # True when nothing SHOULD have been built — a line consumed by user:create,
    # a softphone user moving to the Webex App, a forwarding object with every
    # type disabled. False means an entity that should exist will not.
    # Recorded at the call site rather than inferred from `reason`, so the
    # classification cannot drift away from a hand-maintained name list.
    by_design: bool = False


@dataclass
class PlannerSkipReport:
    """Aggregate report of all entities skipped by the planner.

    Populated by ``expand_to_operations`` and every per-expander short-circuit.
    Callers inspect ``entries`` for the full list and ``counts`` for a
    by-reason roll-up. ``has_unresolved_skips`` flips True when any entry has
    decision_state in {stale, pending} — the ``--fail-on-unresolved`` gate
    keys off this flag.

    ``needs_decision_counts`` is populated by ``expand_to_operations`` at the
    end of a run. Entities with ``status='needs_decision'`` never reach
    expansion (they have pending operator input) so they never appear in
    ``entries``; the summary is needed separately so operators can see what
    the plan is holding back. Keyed by ``DecisionType``, value is the count of
    distinct entities held back by at least one pending decision of that type.
    """
    entries: list[PlannerSkipEntry] = field(default_factory=list)
    needs_decision_counts: dict[str, int] = field(default_factory=dict)
    anomalies: list[PlannerSkipEntry] = field(default_factory=list)
    stranded_counts: dict[str, int] = field(default_factory=dict)

    def record(
        self,
        canonical_id: str,
        entity_type: str,
        reason: str,
        consequence: str,
        decision_type: str | None = None,
        decision_state: str | None = None,
        by_design: bool = False,
    ) -> None:
        self.entries.append(PlannerSkipEntry(
            canonical_id=canonical_id,
            entity_type=entity_type,
            reason=reason,
            decision_type=decision_type,
            decision_state=decision_state,
            consequence=consequence,
            by_design=by_design,
        ))

    def record_anomaly(
        self,
        canonical_id: str,
        entity_type: str,
        reason: str,
        consequence: str,
        decision_type: str | None = None,
        decision_state: str | None = None,
    ) -> None:
        """Record something wrong about an entity that WAS still expanded.

        Separate from ``entries`` because the aggregate roll-up, the
        ``--fail-on-unresolved`` gate and ``PlannerUnresolvedError``'s wording all
        say *skipped*. Measured on director-demo-2026-04-15: 766 of 1129
        "Planner skip:" lines described entities that are in ``plan_operations``
        (finding F09). The observation is worth keeping — a stale decision on
        something about to be provisioned is a smell — but it is not a skip.
        """
        self.anomalies.append(PlannerSkipEntry(
            canonical_id=canonical_id,
            entity_type=entity_type,
            reason=reason,
            decision_type=decision_type,
            decision_state=decision_state,
            consequence=consequence,
        ))

    @property
    def counts(self) -> dict[str, int]:
        """Group count by ``reason`` (or decision_type when decision-gated)."""
        out: dict[str, int] = {}
        for e in self.entries:
            key = e.decision_type or e.reason
            out[key] = out.get(key, 0) + 1
        return out

    @property
    def by_design_entries(self) -> list[PlannerSkipEntry]:
        """Entries where nothing should have been built."""
        return [e for e in self.entries if e.by_design]

    @property
    def gap_entries(self) -> list[PlannerSkipEntry]:
        """Entries where something that should exist will not.

        This is the population an operator has to act on. Measured on
        director-demo-2026-04-15: 360 of 1384, i.e. the headline
        "Planner skipped 1384 entities" over-reported the actionable set by
        3.8x. The other 1024 are lines consumed by user:create, softphone
        users moving to the Webex App, and CTI ports.
        """
        return [e for e in self.entries if not e.by_design]

    @staticmethod
    def _group(entries: list[PlannerSkipEntry]) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in entries:
            key = e.decision_type or e.reason
            out[key] = out.get(key, 0) + 1
        return out

    @property
    def anomaly_counts(self) -> dict[str, int]:
        """Group anomaly count by ``reason`` (or decision_type when decision-gated)."""
        out: dict[str, int] = {}
        for a in self.anomalies:
            key = a.decision_type or a.reason
            out[key] = out.get(key, 0) + 1
        return out

    @property
    def has_unresolved_skips(self) -> bool:
        """True if anything is genuinely missing from the plan.

        Two sources, both meaning "an entity that should be in the plan is not":
        a skip entry caused by an unresolved decision, or an object that never
        reached ``analyzed`` so expansion never saw it (finding F08 — 23 of 300
        users, invisible to every existing signal).

        Anomalies are deliberately excluded: those entities ARE in the plan.
        """
        return bool(self.stranded_counts) or any(
            e.decision_state in ("stale", "pending")
            for e in self.entries
        )

    def unresolved_entries(self) -> list[PlannerSkipEntry]:
        """Entries whose skip was caused by an unresolved (stale/pending) decision."""
        return [e for e in self.entries if e.decision_state in ("stale", "pending")]


def _warn_skip(
    report: PlannerSkipReport,
    canonical_id: str,
    entity_type: str,
    reason: str,
    consequence: str,
    decision_type: str | None = None,
    decision_state: str | None = None,
) -> None:
    """Emit a WARN and record into the report.

    Keeping WARN + record in one helper ensures every silent-skip site has
    identical observability (log + report entry).
    """
    tag = decision_type or reason
    logger.warning(
        "Planner skip: %s %s (reason=%s%s) — %s",
        entity_type,
        canonical_id,
        tag,
        f", state={decision_state}" if decision_state else "",
        consequence,
    )
    report.record(
        canonical_id=canonical_id,
        entity_type=entity_type,
        reason=reason,
        consequence=consequence,
        decision_type=decision_type,
        decision_state=decision_state,
    )


def _warn_anomaly(
    report: PlannerSkipReport,
    canonical_id: str,
    entity_type: str,
    reason: str,
    consequence: str,
    decision_type: str | None = None,
    decision_state: str | None = None,
) -> None:
    """Emit a WARN for an entity that was expanded anyway, and record it apart.

    The log prefix is deliberately NOT "Planner skip:" — that string is what made
    the skip report untrustworthy, because it was attached to 766 entities that
    were planned (finding F09).

    DEBUG, not WARNING (finding F16). Reclassifying these from skips to
    anomalies was correct but did not shrink the output: 769 "Planner anomaly:"
    lines simply replaced 766 "Planner skip:" ones, measured on
    director-demo-2026-04-15 at 1153 stderr lines either way. The per-entity
    line is redundant with ``_log_anomaly_summary``, which already reports the
    count and the by-type breakdown, and these entities ARE in the plan — a
    per-entity warning for something that was provisioned successfully is the
    definition of noise. The record is kept in full on the report, so
    ``--fail-on-unresolved`` and the roll-up are unaffected; -v recovers the
    per-entity lines.
    """
    tag = decision_type or reason
    logger.debug(
        "Planner anomaly: %s %s (reason=%s%s) — still planned; %s",
        entity_type,
        canonical_id,
        tag,
        f", state={decision_state}" if decision_state else "",
        consequence,
    )
    report.record_anomaly(
        canonical_id=canonical_id,
        entity_type=entity_type,
        reason=reason,
        consequence=consequence,
        decision_type=decision_type,
        decision_state=decision_state,
    )


class PlannerUnresolvedError(RuntimeError):
    """Raised when fail-on-unresolved is enabled and unresolved skips were recorded."""


# Per-task current report. Set by ``expand_to_operations`` while it runs
# and cleared on exit. Expanders call ``_current_report()`` to access it;
# callers should NOT set this directly. This keeps the expander signatures
# small while still capturing every silent-skip site loudly.
#
# Backed by ``contextvars.ContextVar`` so concurrent planner runs (threads or
# asyncio tasks) see their own report, not a neighbor's. ``_set_current_report``
# returns the ``Token`` from ``set()`` so the caller can reset the variable to
# its prior value on exit — critical for correctness under nested / concurrent
# calls (reassigning to ``None`` would clobber an outer scope's report).
_CURRENT_REPORT: contextvars.ContextVar[PlannerSkipReport | None] = (
    contextvars.ContextVar("planner_current_report", default=None)
)


def _current_report() -> PlannerSkipReport | None:
    """Return the active planner skip report (or None if the planner is not running)."""
    return _CURRENT_REPORT.get()


def _set_current_report(
    report: PlannerSkipReport | None,
) -> contextvars.Token[PlannerSkipReport | None]:
    """Set the active planner skip report for the current context.

    Returns a ``contextvars.Token`` that the caller should pass to
    ``_CURRENT_REPORT.reset(token)`` once expansion is complete. Using the
    token-based reset correctly restores the prior value under nested
    expand_to_operations() calls, instead of unconditionally nuking the
    ContextVar to ``None``.
    """
    return _CURRENT_REPORT.set(report)

# Decision types where chosen_option="skip" means "don't expand this object".
# (from phase-07-planning.md lines 26-27)
#
# Note: DEVICE_FIRMWARE_CONVERTIBLE is NOT in this set — as of 2026-04-15
# convertibility is a model classification, not a decision, and convertible
# devices always produce a create_activation_code op.
_SKIP_DECISION_TYPES = {
    "DEVICE_INCOMPATIBLE",
    "EXTENSION_CONFLICT",
    "LOCATION_AMBIGUOUS",
    "MISSING_DATA",
    "WORKSPACE_LICENSE_TIER",
    "DUPLICATE_USER",
    "VOICEMAIL_INCOMPATIBLE",
}

# The only decision type that gates on *pending* rather than on a resolved
# 'skip'. See the cross-site gate in expand_to_operations().
# (from docs/prompts/cross-site-dependency-detection.md §5.5)
_CROSS_SITE_TYPE = "CROSS_SITE_DEPENDENCY"


# ---------------------------------------------------------------------------
# Decision-aware helpers
# ---------------------------------------------------------------------------

def _build_decisions_index(store: MigrationStore) -> dict[str, list[dict[str, Any]]]:
    """Build a canonical_id → decisions index from all non-stale decisions.

    Called once per expand_to_operations() run to avoid O(objects * decisions)
    repeated queries.
    """
    all_decisions = store.get_all_decisions()
    index: dict[str, list[dict[str, Any]]] = {}
    for d in all_decisions:
        if is_stale(d):
            continue
        context = d.get("context", {})
        for cid in context.get("_affected_objects", []):
            index.setdefault(cid, []).append(d)
    return index


def _build_stale_decisions_index(store: MigrationStore) -> dict[str, list[dict[str, Any]]]:
    """Build a canonical_id → stale decisions index.

    Stale decisions (``chosen_option='__stale__'``) are normally invisible to
    the planner. If an analyzed object has a stale decision attached, that
    often means an upstream analyzer changed output between runs but the
    object still carries a decision state the planner cannot interpret. The
    ``DEVICE_FIRMWARE_CONVERTIBLE`` bug (2026-04-15) lived here — 611 devices
    had stale decisions, the planner dropped them without logging.

    Callers use this index to emit WARN events when a stale decision is
    present alongside an analyzed object so the skip is loud, not silent.
    """
    all_decisions = store.get_all_decisions()
    index: dict[str, list[dict[str, Any]]] = {}
    for d in all_decisions:
        if not is_stale(d):
            continue
        context = d.get("context", {})
        for cid in context.get("_affected_objects", []):
            index.setdefault(cid, []).append(d)
    return index


#: Statuses an object passes through before it is eligible for planning.
#: ``discovered`` is excluded from the stranded report on purpose — an object that
#: has not been through normalize yet was never a candidate for this plan.
_STRANDED_STATUSES = ("normalized",)


def _plannable_types() -> frozenset[str]:
    """Object types this planner could actually turn into operations.

    Anything else at ``status='normalized'`` is a CUCM-side source or
    intermediate type that was never going to produce an operation — ``phone``
    normalizes into ``device``, ``hunt_pilot`` into ``hunt_group``,
    ``button_template`` into ``line_key_template``, and the ``info_*`` family is
    reference data. Counting those as "absent from the plan" reported 2005
    entities on director-demo when 67 were real, which is the same
    by-design-vs-genuine error the F03 fix had to be corrected for.

    ``_DATA_ONLY_TYPES`` are excluded too: ``line`` and ``voicemail_profile`` are
    consumed by ``user:create`` and produce no operations by design.
    """
    return frozenset(_EXPANDERS) - frozenset(_DATA_ONLY_TYPES)


def _count_stranded_by_type(store: MigrationStore) -> dict[str, int]:
    """Count objects that stopped advancing before the planner could see them.

    ``expand_to_operations`` queries ``status='analyzed'`` only, and
    ``_count_needs_decision_by_type`` counts ``status='needs_decision'`` only, so
    an object left at ``normalized`` is invisible to every existing signal.
    Finding F08: 23 of 300 users on both real projects sit exactly there — absent
    from ``plan_operations``, absent from all 1370 lines of plan output, and not
    covered by the "held back awaiting your decision" roll-up. 7.7% of the user
    population dropped silently.

    Returns ``{object_type: count}``; empty when everything advanced.
    """
    # Counted in SQL rather than via query_by_status(): the object_type column is
    # authoritative, and there is no reason to deserialize hundreds of Pydantic
    # models to produce a count. Mirrors query_by_status's exclusion of the
    # synthetic bulk-op placeholder rows, which are FK anchors, not real objects.
    plannable = _plannable_types()
    if not plannable:
        return {}
    status_slots = ",".join("?" * len(_STRANDED_STATUSES))
    type_slots = ",".join("?" * len(plannable))
    plannable_ordered = sorted(plannable)
    rows = store.conn.execute(
        f"SELECT object_type, COUNT(*) AS cnt FROM objects "
        f"WHERE status IN ({status_slots}) "
        f"AND object_type IN ({type_slots}) "
        f"GROUP BY object_type",
        (*_STRANDED_STATUSES, *plannable_ordered),
    ).fetchall()
    return {r["object_type"]: r["cnt"] for r in rows}


def _build_pending_decisions_index(store: MigrationStore) -> dict[str, list[dict[str, Any]]]:
    """Build a canonical_id → pending (unresolved) decisions index.

    A pending decision has ``chosen_option is None``. The planner only
    expands objects at ``status='analyzed'`` and pending decisions should
    have pushed the object to ``status='needs_decision'``, but the planner
    still checks so any drift (e.g. analyzer emitted non-blocking decision
    but marked blocking, or status-update bug) is caught loudly.
    """
    all_decisions = store.get_all_decisions()
    index: dict[str, list[dict[str, Any]]] = {}
    for d in all_decisions:
        if d.get("chosen_option") is not None:
            continue
        context = d.get("context", {})
        for cid in context.get("_affected_objects", []):
            index.setdefault(cid, []).append(d)
    return index


def _count_needs_decision_by_type(store: MigrationStore) -> dict[str, int]:
    """Count entities at status='needs_decision' grouped by DecisionType.

    Entities at ``needs_decision`` never reach expansion — they're held back
    waiting for operator input. The aggregate skip summary would otherwise
    hide them because no ``PlannerSkipEntry`` is ever recorded.

    Each entity is counted once per pending decision type that references it
    in ``context._affected_objects``. An entity held back by decisions of two
    different types increments both buckets.

    Returns a ``{decision_type: count}`` dict; empty dict if no entities are
    at ``needs_decision``.
    """
    needs_decision_objects = store.query_by_status("needs_decision")
    if not needs_decision_objects:
        return {}
    held_back_ids = {o.canonical_id for o in needs_decision_objects}

    counts: dict[str, int] = {}
    # One entity held by two pending decisions of the same type still counts
    # as one in that bucket.
    seen: dict[str, set[str]] = {}
    for d in store.get_all_decisions():
        if d.get("chosen_option") is not None:
            continue
        dtype = d.get("type")
        if not dtype:
            continue
        affected = d.get("context", {}).get("_affected_objects", [])
        for cid in affected:
            if cid not in held_back_ids:
                continue
            if cid in seen.setdefault(dtype, set()):
                continue
            seen[dtype].add(cid)
            counts[dtype] = counts.get(dtype, 0) + 1
    return counts


def _find_skip_decision(decisions: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the first decision in _SKIP_DECISION_TYPES resolved as 'skip'."""
    for d in decisions:
        if d.get("type") in _SKIP_DECISION_TYPES and d.get("chosen_option") == "skip":
            return d
    return None


def _any_skip_decision(decisions: list[dict[str, Any]]) -> bool:
    """Check if any decision in _SKIP_DECISION_TYPES is resolved as 'skip'."""
    for d in decisions:
        if d.get("type") in _SKIP_DECISION_TYPES and d.get("chosen_option") == "skip":
            return True
    return False


def _decision_chosen(decisions: list[dict[str, Any]], decision_type: str) -> str | None:
    """Get the chosen option for a specific decision type, if resolved."""
    for d in decisions:
        if d.get("type") == decision_type and d.get("chosen_option") is not None:
            return d["chosen_option"]
    return None


def _location_canonical_ids(store: MigrationStore) -> set[str]:
    """Every ``location:`` canonical_id in the store.

    Built once per expansion run so the cross-site location patch can tell an
    operator-chosen location apart from one of the four literal option ids.
    """
    return {
        loc["canonical_id"]
        for loc in store.get_objects("location")
        if loc.get("canonical_id")
    }


def _cross_site_location_choice(
    decisions: list[dict[str, Any]],
    canonical_id: str,
    location_ids: set[str],
) -> str | None:
    """The location this construct's own cross-site decision was reassigned to.

    ``wxcli cucm decide`` stores whatever the operator typed, so a
    ``CROSS_SITE_DEPENDENCY`` answered with a location canonical_id means
    "build it at that location instead" (the ``reassign_home`` option documents
    the intent; the location id carries the target). Anything that is not a
    known location — including the four literal option ids — returns ``None``.

    Scoped to ``context["construct_id"] == canonical_id`` so resolving a
    construct's decision never relocates one of its remote members, which are
    also listed in ``affected_objects``.
    """
    for d in decisions:
        if d.get("type") != _CROSS_SITE_TYPE:
            continue
        if (d.get("context") or {}).get("construct_id") != canonical_id:
            continue
        chosen = d.get("chosen_option")
        if chosen and chosen in location_ids:
            return str(chosen)
    return None


# ---------------------------------------------------------------------------
# Bulk optimization pass
# (from docs/superpowers/specs/2026-04-10-bulk-operations.md §3b)
# ---------------------------------------------------------------------------

def _optimize_for_bulk(
    ops: list[MigrationOp],
    store: MigrationStore,
    threshold: int,
    skip_rebuild_phones: bool = False,
) -> list[MigrationOp]:
    """Replace per-device operations with bulk submissions.

    When the number of unique devices being created meets or exceeds
    ``threshold``, replaces:

    - ``device:configure_settings`` ops  → ``bulk_device_settings:submit``
      (one per location)
    - ``device_layout:configure`` ops    → ``bulk_line_key_template:submit``
      (one per (template_id, location))
    - ``softkey_config:configure`` ops   → ``bulk_dynamic_settings:submit``
      (one per location)
    - (post-all)                         → ``bulk_rebuild_phones:submit``
      (one per location, tier 8)

    ``device:create`` ops are never replaced — there is no bulk device
    create API.

    Below the threshold, the input list is returned unchanged.
    """
    device_creates = [o for o in ops if o.resource_type == "device" and o.op_type == "create"]
    if len(device_creates) < threshold:
        return ops

    logger.info(
        "Bulk optimization: device count %d >= threshold %d — rewriting ops",
        len(device_creates), threshold,
    )

    result: list[MigrationOp] = []
    # Track which locations needed bulk ops (for tier 8 rebuild phones later).
    device_settings_locations: set[str] = set()
    # Track covered device canonical_ids per location for fallback context.
    device_settings_covered: dict[str, list[str]] = {}

    for op in ops:
        if op.resource_type == "device" and op.op_type == "configure_settings":
            loc = op.batch or "org-wide"
            device_settings_locations.add(loc)
            device_settings_covered.setdefault(loc, []).append(op.canonical_id)
            continue  # drop the per-device op
        result.append(op)

    # Emit one bulk_device_settings:submit per location, at tier 5,
    # dependent on all device:create ops in that location.
    for loc in sorted(device_settings_locations):
        dep_node_ids = [
            _node_id(o.canonical_id, "create")
            for o in ops
            if o.resource_type == "device"
            and o.op_type == "create"
            and (o.batch or "org-wide") == loc
        ]
        bulk_cid = f"bulk_device_settings:{loc}"
        result.append(MigrationOp(
            canonical_id=bulk_cid,
            op_type="submit",
            resource_type="bulk_device_settings",
            tier=TIER_ASSIGNMENTS[("bulk_device_settings", "submit")],
            batch=loc if loc != "org-wide" else None,
            api_calls=API_CALL_ESTIMATES["bulk_device_settings:submit"],
            description=f"Bulk apply device settings at {loc}",
            depends_on=dep_node_ids,
            payload={
                "location_canonical_id": loc,
                "customizations": {},
                "covered_canonical_ids": device_settings_covered.get(loc, []),
                "fallback_handler_key": ["device", "configure_settings"],
            },
        ))

    # ---- Line key template aggregation ----
    # Group device_layout:configure ops by (template_canonical_id, location_canonical_id).
    lkt_groups: dict[tuple[str, str], list[str]] = {}  # (template, loc) → device_cids
    lkt_layout_cids: dict[tuple[str, str], list[str]] = {}  # (template, loc) → layout canonical_ids
    layout_ops_to_remove: set[str] = set()
    members_ops: list[MigrationOp] = []

    for op in ops:
        if op.resource_type != "device_layout" or op.op_type != "configure":
            continue
        layout_obj = store.get_object(op.canonical_id)
        if not layout_obj:
            continue
        data = layout_obj.model_dump() if hasattr(layout_obj, "model_dump") else layout_obj
        template_cid = data.get("template_canonical_id") or ""
        device_cid = data.get("device_canonical_id") or ""
        if not template_cid or not device_cid:
            continue
        device_obj = store.get_object(device_cid)
        if not device_obj:
            continue
        dev_data = device_obj.model_dump() if hasattr(device_obj, "model_dump") else device_obj
        loc_cid = dev_data.get("location_canonical_id") or "org-wide"

        lkt_groups.setdefault((template_cid, loc_cid), []).append(device_cid)
        lkt_layout_cids.setdefault((template_cid, loc_cid), []).append(op.canonical_id)
        layout_ops_to_remove.add(op.canonical_id)
        # The bulk job applies the line key TEMPLATE only — there is no bulk API
        # for device members, so keep a per-device members op. Without this,
        # every shared line silently stops being configured above the bulk
        # threshold, which is where real migrations live.
        if data.get("line_members"):
            members_ops.append(_op(
                op.canonical_id, "configure_members", "device_layout",
                f"Assign device members for {device_cid}",
                depends_on=[_node_id(device_cid, "create")],
                batch=op.batch,
            ))

    # Filter out the replaced layout ops from result.
    result = [
        o for o in result
        if not (o.resource_type == "device_layout"
                and o.op_type == "configure"
                and o.canonical_id in layout_ops_to_remove)
    ]
    result.extend(members_ops)

    # Emit bulk_line_key_template submissions.
    for (template_cid, loc_cid), device_cids in sorted(lkt_groups.items()):
        bulk_cid = f"bulk_line_key_template:{template_cid.split(':', 1)[-1]}:{loc_cid}"
        dep_node_ids = [_node_id(template_cid, "create")]
        dep_node_ids.extend(_node_id(dc, "create") for dc in device_cids)
        result.append(MigrationOp(
            canonical_id=bulk_cid,
            op_type="submit",
            resource_type="bulk_line_key_template",
            tier=TIER_ASSIGNMENTS[("bulk_line_key_template", "submit")],
            batch=loc_cid if loc_cid != "org-wide" else None,
            api_calls=API_CALL_ESTIMATES["bulk_line_key_template:submit"],
            description=f"Bulk apply line key template {template_cid} at {loc_cid}",
            depends_on=dep_node_ids,
            payload={
                "template_canonical_id": template_cid,
                "location_canonical_ids": [loc_cid],
                "covered_canonical_ids": lkt_layout_cids.get((template_cid, loc_cid), []),
                "fallback_handler_key": ["device_layout", "configure"],
            },
        ))

    # ---- Dynamic device settings (PSK) aggregation ----
    psk_groups: dict[str, list[str]] = {}  # location_cid → device_cids
    psk_softkey_cids: dict[str, list[str]] = {}  # location_cid → softkey canonical_ids
    softkey_ops_to_remove: set[str] = set()

    for op in ops:
        if op.resource_type != "softkey_config" or op.op_type != "configure":
            continue
        sk_obj = store.get_object(op.canonical_id)
        if not sk_obj:
            continue
        sk_data = sk_obj.model_dump() if hasattr(sk_obj, "model_dump") else sk_obj
        if not sk_data.get("is_psk_target"):
            continue
        device_cid = sk_data.get("device_canonical_id") or ""
        if not device_cid:
            continue
        device_obj = store.get_object(device_cid)
        if not device_obj:
            continue
        dev_data = device_obj.model_dump() if hasattr(device_obj, "model_dump") else device_obj
        loc_cid = dev_data.get("location_canonical_id") or "org-wide"
        psk_groups.setdefault(loc_cid, []).append(device_cid)
        psk_softkey_cids.setdefault(loc_cid, []).append(op.canonical_id)
        softkey_ops_to_remove.add(op.canonical_id)

    result = [
        o for o in result
        if not (o.resource_type == "softkey_config"
                and o.op_type == "configure"
                and o.canonical_id in softkey_ops_to_remove)
    ]

    for loc_cid, device_cids in sorted(psk_groups.items()):
        bulk_cid = f"bulk_dynamic_settings:{loc_cid}"
        dep_node_ids = [_node_id(dc, "create") for dc in device_cids]
        result.append(MigrationOp(
            canonical_id=bulk_cid,
            op_type="submit",
            resource_type="bulk_dynamic_settings",
            tier=TIER_ASSIGNMENTS[("bulk_dynamic_settings", "submit")],
            batch=loc_cid if loc_cid != "org-wide" else None,
            api_calls=API_CALL_ESTIMATES["bulk_dynamic_settings:submit"],
            description=f"Bulk apply PSK/dynamic settings at {loc_cid}",
            depends_on=dep_node_ids,
            payload={
                "location_canonical_id": loc_cid,
                "tags": [],
                "covered_canonical_ids": psk_softkey_cids.get(loc_cid, []),
                "fallback_handler_key": ["softkey_config", "configure"],
            },
        ))

    # ---- Rebuild phones (tier 8) ----
    # One rebuild per location touched by any bulk op. Depends on every
    # bulk op in that location so it runs strictly after them.
    if skip_rebuild_phones:
        logger.info("skip_rebuild_phones=True — omitting bulk_rebuild_phones ops")
        return result

    rebuild_locations: dict[str, list[str]] = {}

    for op in result:
        if op.resource_type not in {"bulk_device_settings",
                                      "bulk_line_key_template",
                                      "bulk_dynamic_settings"}:
            continue
        loc = op.batch or "org-wide"
        rebuild_locations.setdefault(loc, []).append(
            _node_id(op.canonical_id, op.op_type)
        )

    for loc, bulk_node_ids in sorted(rebuild_locations.items()):
        bulk_cid = f"bulk_rebuild_phones:{loc}"
        result.append(MigrationOp(
            canonical_id=bulk_cid,
            op_type="submit",
            resource_type="bulk_rebuild_phones",
            tier=TIER_ASSIGNMENTS[("bulk_rebuild_phones", "submit")],
            batch=loc if loc != "org-wide" else None,
            api_calls=API_CALL_ESTIMATES["bulk_rebuild_phones:submit"],
            description=f"Bulk rebuild phones at {loc}",
            depends_on=bulk_node_ids,
            payload={
                "location_canonical_id": loc,
            },
        ))

    return result


# ---------------------------------------------------------------------------
# Operation builder helpers
# ---------------------------------------------------------------------------

def _op(
    canonical_id: str,
    op_type: str,
    resource_type: str,
    description: str,
    depends_on: list[str] | None = None,
    batch: str | None = None,
    payload: dict | None = None,
) -> MigrationOp:
    """Build a MigrationOp with tier and api_calls looked up from constants.

    ``payload`` carries handler data for ops whose canonical object is not
    shaped like the resource being created (see the virtual-line-from-shared-line
    expansion). ``runtime.get_next_batch`` prefers it over the store lookup.
    """
    tier = TIER_ASSIGNMENTS.get((resource_type, op_type), 0)
    api_key = f"{resource_type}:{op_type}"
    api_calls = API_CALL_ESTIMATES.get(api_key, 1)
    if batch is None and resource_type in ORG_WIDE_TYPES:
        batch = "org-wide"
    return MigrationOp(
        canonical_id=canonical_id,
        op_type=op_type,
        resource_type=resource_type,
        tier=tier,
        batch=batch,
        api_calls=api_calls,
        description=description,
        depends_on=depends_on or [],
        payload=payload,
    )


def _node_id(canonical_id: str, op_type: str) -> str:
    """Consistent node ID format: 'canonical_id:op_type'.

    To parse back: use rsplit(":", 1) — canonical_id may contain colons.
    """
    return f"{canonical_id}:{op_type}"


# ---------------------------------------------------------------------------
# Per-type expansion patterns
# (from 05-dependency-graph.md lines 41-74 — user and location examples)
# Other types follow the same deterministic pattern.
# ---------------------------------------------------------------------------

def _expand_location(obj: dict[str, Any]) -> list[MigrationOp]:
    """Location → 2 ops: create + enable_calling (tier 0).

    Fix 13: Creating a location does NOT enable Webex Calling on it.
    A separate POST /v1/telephony/config/locations is required.
    (from 05-dependency-graph.md lines 68-70, updated by Phase 12a Fix 13)
    """
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    return [
        _op(cid, "create", "location", f"Create location {name}"),
        _op(cid, "enable_calling", "location", f"Enable Webex Calling on {name}",
            depends_on=[_node_id(cid, "create")]),
    ]


def _expand_trunk(obj: dict[str, Any]) -> list[MigrationOp]:
    """Trunk → 1 op: create (tier 1)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    return [_op(cid, "create", "trunk", f"Create trunk {name}")]


def _expand_route_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Route group → 1 op: create (tier 1). Depends on its trunks."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    deps = []
    for gw in obj.get("local_gateways", []):
        trunk_cid = gw.get("trunk_canonical_id")
        if trunk_cid:
            deps.append(_node_id(trunk_cid, "create"))
    return [_op(cid, "create", "route_group", f"Create route group {name}", depends_on=deps)]


def _expand_route_list(obj: dict[str, Any]) -> list[MigrationOp]:
    """Route list → 1-2 ops: create (tier 1) + optional configure_numbers.
    Depends on its route group.
    """
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    deps = []
    rg_cid = obj.get("route_group_id")
    if rg_cid:
        deps.append(_node_id(rg_cid, "create"))
    ops = [_op(cid, "create", "route_list", f"Create route list {name}", depends_on=deps)]
    numbers = obj.get("numbers", [])
    if numbers:
        ops.append(_op(
            cid, "configure_numbers", "route_list",
            f"Assign {len(numbers)} numbers to route list {name}",
            depends_on=[_node_id(cid, "create")],
        ))
    return ops


def _expand_operating_mode(obj: dict[str, Any]) -> list[MigrationOp]:
    """Operating mode (schedule) → 1 op: create (tier 1)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    return [_op(cid, "create", "operating_mode", f"Create operating mode {name}")]


def _expand_schedule(obj: dict[str, Any]) -> list[MigrationOp]:
    """Location schedule → 1 op: create (tier 1)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = obj.get("location_id")
    return [_op(cid, "create", "schedule", f"Create location schedule {name}",
                batch=loc_id)]


def _expand_user(obj: dict[str, Any]) -> list[MigrationOp]:
    """User → 1-3 ops: create (always), configure_settings (if custom), configure_voicemail (if custom).

    Fix 12: extension and license are included at creation time — the Webex
    People API requires extension when callingData=true, and wxcli users create
    has --license (not available on update).
    Only generates configure_settings/configure_voicemail ops if the user has
    non-default settings data to apply.
    (from 05-dependency-graph.md lines 46-66, updated by Phase 12a Fix 12)
    """
    cid = obj["canonical_id"]
    email = (obj.get("emails") or ["unknown"])[0]
    loc_id = obj.get("location_id")
    batch = loc_id if loc_id else None

    ops = [_op(cid, "create", "user", f"Create person {email}", batch=batch)]

    # Only generate settings op if user has custom call settings
    settings = obj.get("call_settings") or obj.get("forwarding") or obj.get("call_forwarding")
    if settings:
        ops.append(_op(cid, "configure_settings", "user",
                       f"Configure call settings for {email}",
                       depends_on=[_node_id(cid, "create")], batch=batch))

    # Only generate voicemail op if user has custom voicemail config
    vm = obj.get("voicemail") or obj.get("voicemail_settings") or obj.get("voicemail_profile_id")
    if vm:
        ops.append(_op(cid, "configure_voicemail", "user",
                       f"Configure voicemail for {email}",
                       depends_on=[_node_id(cid, "create")], batch=batch))

    return ops


def _expand_workspace(obj: dict[str, Any]) -> list[MigrationOp]:
    """Workspace → 3 ops: create, assign_number, configure_settings."""
    cid = obj["canonical_id"]
    name = obj.get("display_name", cid)
    loc_id = obj.get("location_id")
    batch = loc_id if loc_id else None

    return [
        _op(cid, "create", "workspace", f"Create workspace {name}", batch=batch),
        _op(cid, "assign_number", "workspace",
            f"Assign number to workspace {name}",
            depends_on=[_node_id(cid, "create")], batch=batch),
        _op(cid, "configure_settings", "workspace",
            f"Configure settings for workspace {name}",
            depends_on=[_node_id(cid, "assign_number")], batch=batch),
    ]


_NON_WEBEX_DEVICE_MODELS = {
    "Cisco Unified Client Services Framework",
    "Analog Phone",
    "Cisco ATA 191",
}


def _expand_device(
    obj: dict[str, Any],
    decisions: list[dict[str, Any]],
    config: dict | None = None,
) -> list[MigrationOp]:
    """Device → 1 op (CONVERTIBLE activation-code path) or 2 ops (MAC-based path).

    - NATIVE_MPP / default: create (MAC-based POST /devices) + configure_settings
    - CONVERTIBLE, default: single create_activation_code op, no configure_settings
      (the phone auto-configures after registering). Emitted unconditionally —
      convertibility is a model classification, not an operator choice.
    - CONVERTIBLE, when config["convertible_provisioning"] == "mac" AND mac present:
      same 2-op MAC path as NATIVE_MPP.  Use this when CUCM→MPP firmware
      conversion will auto-register the device against Webex by MAC so that
      no end-user activation step is needed.
    - webex_app / infrastructure / dect / non-Webex models: no ops
    - MAC-based path (NATIVE_MPP/default, or CONVERTIBLE+mac) without a mac: no ops
      (logged skip — POST /devices requires a MAC, so there's nothing to create)

    Skip decisions handled generically in expand_to_operations.
    (from 05-dependency-graph.md — device:create at tier 3, api_calls=2)
    """
    cid = obj["canonical_id"]
    # Skip devices with non-Webex models (CSF soft phones, analog, ATA)
    tier = obj.get("compatibility_tier")
    model = obj.get("model")
    if tier in ("webex_app", "infrastructure", "dect") or model in _NON_WEBEX_DEVICE_MODELS:
        report = _current_report()
        # `tier` arrives from model_dump() as a DeviceCompatibilityTier member,
        # and a (str, Enum) formats as `DeviceCompatibilityTier.WEBEX_APP` — a
        # Python repr leaking into operator-facing text. Use the value.
        tier_name = getattr(tier, "value", tier)
        reason = (
            f"compatibility_tier={tier_name}"
            if tier in ("webex_app", "infrastructure", "dect")
            else f"non_webex_model={model}"
        )
        logger.info(
            "Planner skip (expected): device %s (%s) — no plan ops produced",
            cid, reason,
        )
        if report is not None:
            report.record(
                canonical_id=cid,
                entity_type="device",
                reason=reason,
                consequence=(
                    "device will not be provisioned to Webex "
                    f"(model/tier classified as {reason})"
                ),
                by_design=True,
            )
        return []
    name = obj.get("display_name") or obj.get("mac") or cid
    owner_cid = obj.get("owner_canonical_id")
    loc_cid = obj.get("location_canonical_id")
    batch = loc_cid if loc_cid else None

    deps_create: list[str] = []
    if owner_cid:
        deps_create.append(_node_id(owner_cid, "create"))

    if obj.get("compatibility_tier") == "convertible":
        # Check whether the operator wants MAC-based provisioning for convertibles.
        # Requires config["convertible_provisioning"] == "mac" AND a MAC on the device.
        use_mac = (
            (config or {}).get("convertible_provisioning") == "mac"
            and bool(obj.get("mac"))
        )
        if not use_mac:
            return [
                _op(cid, "create_activation_code", "device",
                    f"Generate activation code for {name}",
                    depends_on=deps_create, batch=batch),
            ]
        # Fall through to the MAC-based 2-op path below.

    if not obj.get("mac"):
        report = _current_report()
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="device",
                reason="missing_mac",
                consequence=(
                    "device will not be provisioned to Webex "
                    "(MAC-based create requires a MAC address)"
                ),
            )
        return []

    return [
        _op(cid, "create", "device", f"Create device {name}",
            depends_on=deps_create, batch=batch),
        _op(cid, "configure_settings", "device", f"Configure device {name}",
            depends_on=[_node_id(cid, "create")], batch=batch),
    ]


def _expand_dial_plan(obj: dict[str, Any]) -> list[MigrationOp]:
    """Dial plan → 1 op: create (tier 2, org-wide)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    deps = []
    route_id = obj.get("route_id")
    if route_id:
        deps.append(_node_id(route_id, "create"))
    return [_op(cid, "create", "dial_plan", f"Create dial plan {name}", depends_on=deps)]


def _expand_translation_pattern(obj: dict[str, Any]) -> list[MigrationOp]:
    """Translation pattern → 1 op: create (tier 2, org-wide)."""
    cid = obj["canonical_id"]
    name = obj.get("name") or obj.get("matching_pattern") or cid
    return [_op(cid, "create", "translation_pattern", f"Create translation pattern {name}")]


def _expand_calling_permission(obj: dict[str, Any]) -> list[MigrationOp]:
    """Calling permission → 0-1 ops: assign op per assigned user (tier 5).

    No standalone create op — Webex permissions are per-user, not standalone
    resources. Only generates an assign op if there are users to apply to.
    """
    cid = obj["canonical_id"]
    assigned_users = obj.get("assigned_users", [])
    if not assigned_users:
        report = _current_report()
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="calling_permission",
                reason="no_assigned_users",
                consequence=(
                    "calling permission will not be assigned "
                    "(assigned_users list is empty — no user will inherit this permission)"
                ),
            )
        return []

    api_calls = len(assigned_users)
    return [MigrationOp(
        canonical_id=cid,
        op_type="assign",
        resource_type="calling_permission",
        tier=TIER_ASSIGNMENTS[("calling_permission", "assign")],
        batch="org-wide",
        api_calls=api_calls,
        description=f"Assign calling permissions to {api_calls} users",
        depends_on=[_node_id(uid, "create") for uid in assigned_users],
    )]


def _expand_hunt_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Hunt group → 1-2 ops: create (tier 4) + optional configure_forwarding (tier 5)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    deps = [_node_id(uid, "create") for uid in obj.get("agents", [])]
    ops = [_op(cid, "create", "hunt_group", f"Create hunt group {name}",
               depends_on=deps, batch=loc_id)]

    has_forwarding = any([
        obj.get("forward_always_enabled"),
        obj.get("forward_busy_enabled"),
        obj.get("forward_no_answer_enabled"),
    ])
    if has_forwarding:
        ops.append(_op(
            cid, "configure_forwarding", "hunt_group",
            f"Configure forwarding for hunt group {name}",
            depends_on=[_node_id(cid, "create")], batch=loc_id,
        ))
    return ops


def _expand_call_queue(obj: dict[str, Any]) -> list[MigrationOp]:
    """Call queue → 1-5 ops: create (tier 4) + optional configure_* (tier 5)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    deps = [_node_id(uid, "create") for uid in obj.get("agents", [])]
    ops = [_op(cid, "create", "call_queue", f"Create call queue {name}",
               depends_on=deps, batch=loc_id)]

    create_dep = [_node_id(cid, "create")]

    has_forwarding = any([
        obj.get("forward_always_enabled"),
        obj.get("queue_full_destination"),
        obj.get("max_wait_time_destination"),
    ])
    if has_forwarding:
        ops.append(_op(
            cid, "configure_forwarding", "call_queue",
            f"Configure forwarding for call queue {name}",
            depends_on=create_dep, batch=loc_id,
        ))

    if obj.get("holiday_service_enabled"):
        ops.append(_op(
            cid, "configure_holiday_service", "call_queue",
            f"Configure holiday service for call queue {name}",
            depends_on=create_dep, batch=loc_id,
        ))

    if obj.get("night_service_enabled"):
        ops.append(_op(
            cid, "configure_night_service", "call_queue",
            f"Configure night service for call queue {name}",
            depends_on=create_dep, batch=loc_id,
        ))

    if obj.get("no_agent_destination"):
        ops.append(_op(
            cid, "configure_stranded_calls", "call_queue",
            f"Configure stranded calls for call queue {name}",
            depends_on=create_dep, batch=loc_id,
        ))

    return ops


def _expand_auto_attendant(obj: dict[str, Any]) -> list[MigrationOp]:
    """Auto attendant → 1-2 ops: create (tier 4) + optional configure_forwarding (tier 5)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    ops = [_op(cid, "create", "auto_attendant", f"Create auto attendant {name}",
               batch=loc_id)]

    if obj.get("forward_always_enabled"):
        ops.append(_op(
            cid, "configure_forwarding", "auto_attendant",
            f"Configure forwarding for auto attendant {name}",
            depends_on=[_node_id(cid, "create")], batch=loc_id,
        ))

    return ops


def _expand_call_park(obj: dict[str, Any]) -> list[MigrationOp]:
    """Call park → 1 op: create (tier 4)."""
    cid = obj["canonical_id"]
    name = obj.get("name") or obj.get("extension") or cid
    loc_id = obj.get("location_id")
    return [_op(cid, "create", "call_park", f"Create call park {name}",
                batch=loc_id)]


def _expand_pickup_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Pickup group → 1 op: create (tier 4)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    deps = [_node_id(uid, "create") for uid in obj.get("agents", [])]
    return [_op(cid, "create", "pickup_group", f"Create pickup group {name}",
                depends_on=deps, batch=loc_id)]


def _expand_paging_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Paging group → 1 op: create (tier 4)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    deps = [_node_id(uid, "create") for uid in obj.get("targets", [])]
    return [_op(cid, "create", "paging_group", f"Create paging group {name}",
                depends_on=deps, batch=loc_id)]


def _expand_voicemail_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Voicemail group -> 1 op: create.

    Depends on the location's calling having been enabled. The batch
    partitioner groups this with other features in the same location.
    (from docs/superpowers/specs/2026-04-10-voicemail-groups.md)
    """
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = obj.get("location_id")
    deps: list[str] = []
    if loc_id:
        deps.append(_node_id(loc_id, "enable_calling"))
    return [_op(
        cid,
        "create",
        "voicemail_group",
        f"Create voicemail group {name}",
        depends_on=deps,
        batch=loc_id,
    )]


def _virtual_line_ops_from_shared_line(
    obj: dict[str, Any],
    store: MigrationStore | None,
) -> list[MigrationOp]:
    """Emit virtual_line create + configure straight from a shared-line object.

    No ``CanonicalVirtualLine`` is ever produced by the pipeline, so an earlier
    version of this branch returned ``[]`` and logged that the ops "will come
    from a CanonicalVirtualLine" — they never did, and choosing ``virtual_line``
    silently produced nothing. Building the objects in a new pipeline stage is
    the wrong fix: the decision is resolved *after* analyze, so the planner is
    the only place that knows the answer.

    The op carries a ``payload`` because the canonical object behind
    ``canonical_id`` is a ``CanonicalSharedLine`` — it has no extension,
    location, or display name of its own. ``runtime.get_next_batch`` prefers an
    inline payload over the store lookup, so the handler receives virtual-line
    shaped data.
    (from docs/prompts/cross-site-phase-2.md §6.3)
    """
    cid = obj["canonical_id"]
    owner_ids = [o for o in obj.get("owner_canonical_ids", []) if o]

    # dn_canonical_id is "dn:{pattern}:{partition}" — the pattern is the extension.
    dn_cid = obj.get("dn_canonical_id") or ""
    dn_parts = dn_cid.split(":", 2)
    extension = dn_parts[1] if len(dn_parts) > 1 else None
    if not extension:
        report = _current_report()
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="shared_line",
                reason="virtual_line_no_extension",
                decision_type="SHARED_LINE_COMPLEX",
                decision_state="virtual_line",
                consequence=(
                    "operator chose 'virtual_line' but the shared line carries no "
                    "resolvable DN — no virtual line will be created"
                ),
            )
        return []

    # The virtual line lands at its owners' site. resolve_entity_location is the
    # only correct way to read a location — the field name varies by type.
    loc_cid = None
    if store is not None:
        for owner in owner_ids:
            loc_cid = resolve_entity_location(store, owner)
            if loc_cid:
                break

    payload = {
        "canonical_id": cid,
        "display_name": f"Shared {extension}",
        "extension": extension,
        "location_id": loc_cid,
        "dn_canonical_id": dn_cid or None,
        "settings": {},
    }

    deps = [_node_id(uid, "create") for uid in owner_ids]
    if loc_cid:
        deps.append(_node_id(loc_cid, "create"))

    logger.info(
        "Planner: shared_line %s → virtual line ext %s at %s",
        cid, extension, loc_cid or "<unresolved location>",
    )
    return [
        _op(cid, "create", "virtual_line",
            f"Create virtual line {extension} (from shared line)",
            depends_on=deps, batch=loc_cid, payload=payload),
        _op(cid, "configure", "virtual_line",
            f"Configure virtual line {extension}",
            depends_on=[_node_id(cid, "create")], batch=loc_cid, payload=payload),
    ]


def _expand_shared_line(
    obj: dict[str, Any],
    decisions: list[dict[str, Any]],
    store: MigrationStore | None = None,
) -> list[MigrationOp]:
    """Shared line → 1 op: configure (tier 6).
    Decision SHARED_LINE_COMPLEX can change expansion:
      - 'virtual_line' → virtual_line create + configure (see helper above)
      - 'skip' → no operations
    """
    choice = _decision_chosen(decisions, "SHARED_LINE_COMPLEX")
    cid = obj["canonical_id"]
    report = _current_report()
    if choice == "skip":
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="shared_line",
                reason="shared_line_complex_skip",
                decision_type="SHARED_LINE_COMPLEX",
                decision_state="skip",
                consequence=(
                    "shared line appearances will not be configured "
                    "(operator chose 'skip' for SHARED_LINE_COMPLEX)"
                ),
            )
        return []
    if choice == "virtual_line":
        return _virtual_line_ops_from_shared_line(obj, store)

    cid = obj["canonical_id"]
    owner_ids = obj.get("owner_canonical_ids", [])
    deps = [_node_id(uid, "create") for uid in owner_ids]
    # Batch assignment deferred — shared lines span users which may be in
    # different sites. The batch partitioner handles unassigned ops as org-wide.
    return [_op(cid, "configure", "shared_line",
                f"Configure shared line appearances for {cid}",
                depends_on=deps)]


def _expand_virtual_line(obj: dict[str, Any]) -> list[MigrationOp]:
    """Virtual line → 2 ops: create (tier 6), configure (tier 6)."""
    cid = obj["canonical_id"]
    name = obj.get("display_name") or obj.get("extension") or cid
    loc_id = obj.get("location_id")
    return [
        _op(cid, "create", "virtual_line", f"Create virtual line {name}",
            batch=loc_id),
        _op(cid, "configure", "virtual_line", f"Configure virtual line {name}",
            depends_on=[_node_id(cid, "create")], batch=loc_id),
    ]


def _expand_line_key_template(obj: dict[str, Any]) -> list[MigrationOp]:
    """Line key template → 1 op: create (tier 1, org-wide).
    Skip if phones_using == 0 (dead template — nothing will reference it).
    """
    cid = obj["canonical_id"]
    if obj.get("phones_using", 0) == 0:
        report = _current_report()
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="line_key_template",
                reason="dead_template_zero_phones",
                consequence=(
                    "line key template will not be created "
                    "(phones_using=0 — no device references this template)"
                ),
            )
        return []
    name = obj.get("name") or cid
    return [_op(cid, "create", "line_key_template", f"Create line key template {name}")]


def _expand_call_forwarding(obj: dict[str, Any]) -> list[MigrationOp]:
    """Call forwarding → 0-1 ops: configure (tier 5).
    Skip if all forwarding types are disabled.
    batch=None — the batch partitioner assigns unassigned ops as org-wide.
    """
    cid = obj["canonical_id"]
    if not any([
        obj.get("always_enabled"),
        obj.get("busy_enabled"),
        obj.get("no_answer_enabled"),
    ]):
        # Expected no-op: forwarding object exists but all types disabled.
        # INFO only — no entity would be created for empty forwarding state.
        report = _current_report()
        logger.info(
            "Planner skip (expected): call_forwarding %s — all forwarding "
            "types disabled, no configure op needed", cid,
        )
        if report is not None:
            report.record(
                canonical_id=cid,
                entity_type="call_forwarding",
                reason="all_forwarding_disabled",
                consequence=(
                    "no forwarding ops emitted (all always/busy/no_answer disabled)"
                ),
                by_design=True,
            )
        return []
    user_cid = obj.get("user_canonical_id")
    deps = [_node_id(user_cid, "create")] if user_cid else []
    return [_op(cid, "configure", "call_forwarding",
                f"Configure call forwarding for {cid}",
                depends_on=deps)]


def _expand_ecbn_config(obj: dict[str, Any]) -> list[MigrationOp]:
    """ECBN config → 1 op: configure (tier 5).

    Depends on the underlying entity (user/workspace/virtual_line) being created.
    (from 2026-04-10-e911-ecbn-execution.md §4.5)
    """
    cid = obj["canonical_id"]
    entity_cid = obj.get("entity_canonical_id", "")
    loc_cid = obj.get("location_canonical_id")
    batch = loc_cid if loc_cid else None

    deps: list[str] = []
    if entity_cid:
        deps.append(_node_id(entity_cid, "create"))

    return [_op(
        canonical_id=cid,
        op_type="configure",
        resource_type="ecbn_config",
        description=f"Configure ECBN for {entity_cid}",
        depends_on=deps,
        batch=batch,
    )]


def _expand_single_number_reach(obj: dict[str, Any]) -> list[MigrationOp]:
    """Single Number Reach → 0-1 ops: configure (tier 5).
    Skip if no numbers.
    """
    cid = obj["canonical_id"]
    if not obj.get("numbers"):
        report = _current_report()
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="single_number_reach",
                reason="no_numbers",
                consequence=(
                    "SNR will not be configured for user "
                    "(numbers list is empty on the canonical object)"
                ),
            )
        return []
    user_cid = obj.get("user_canonical_id")
    deps = [_node_id(user_cid, "create")] if user_cid else []
    return [_op(cid, "configure", "single_number_reach",
                f"Configure SNR for {cid}",
                depends_on=deps)]


def _expand_monitoring_list(obj: dict[str, Any]) -> list[MigrationOp]:
    """Monitoring list → 0-1 ops: configure (tier 6).
    Skip if no monitored_members.
    batch=None — the batch partitioner assigns unassigned ops as org-wide.
    """
    cid = obj["canonical_id"]
    if not obj.get("monitored_members"):
        report = _current_report()
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="monitoring_list",
                reason="no_monitored_members",
                consequence=(
                    "BLF/monitoring list will not be configured "
                    "(no resolved monitored_members on the canonical object)"
                ),
            )
        return []
    user_cid = obj.get("user_canonical_id")
    deps = [_node_id(user_cid, "create")] if user_cid else []
    for m in obj.get("monitored_members", []):
        target_cid = m.get("target_canonical_id")
        if target_cid:
            deps.append(_node_id(target_cid, "create"))
    return [_op(cid, "configure", "monitoring_list",
                f"Configure monitoring list for {cid}",
                depends_on=deps)]


def _expand_device_layout(obj: dict[str, Any]) -> list[MigrationOp]:
    """Device layout → 0-1 ops: configure (tier 7).
    Skip if no resolved_line_keys and no template referenced.
    batch=None — the batch partitioner assigns unassigned ops as org-wide.
    """
    cid = obj["canonical_id"]
    resolved_keys = obj.get("resolved_line_keys", [])
    template_cid = obj.get("template_canonical_id")
    if not resolved_keys and not template_cid:
        report = _current_report()
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="device_layout",
                reason="no_layout_content",
                consequence=(
                    "device layout will not be configured "
                    "(no resolved_line_keys and no template_canonical_id)"
                ),
            )
        return []
    deps = []
    device_cid = obj.get("device_canonical_id")
    if device_cid:
        deps.append(_node_id(device_cid, "create"))
    if template_cid:
        deps.append(_node_id(template_cid, "create"))
    owner_cid = obj.get("owner_canonical_id")
    if owner_cid:
        deps.append(_node_id(owner_cid, "create"))
    for m in obj.get("line_members", []):
        member_cid = m.get("member_canonical_id")
        if member_cid:
            deps.append(_node_id(member_cid, "create"))
    return [_op(cid, "configure", "device_layout",
                f"Configure layout for {cid}",
                depends_on=deps)]


def _expand_softkey_config(obj: dict[str, Any]) -> list[MigrationOp]:
    """Softkey config → 0-1 ops: configure (tier 7).
    Only per-device objects (is_psk_target=True) produce ops.
    Template-level objects (is_psk_target=False) are report-only.
    batch=None — the batch partitioner assigns unassigned ops as org-wide.
    """
    cid = obj["canonical_id"]
    report = _current_report()
    if not obj.get("is_psk_target"):
        # Template-level objects are deliberately report-only; INFO only.
        logger.info(
            "Planner skip (expected): softkey_config %s — template-level "
            "(is_psk_target=False, report-only)", cid,
        )
        if report is not None:
            report.record(
                canonical_id=cid,
                entity_type="softkey_config",
                reason="template_level_report_only",
                consequence=(
                    "no PSK ops emitted (template-level softkey config is "
                    "report-only, not per-device)"
                ),
                by_design=True,
            )
        return []
    device_cid = obj.get("device_canonical_id")
    if not device_cid:
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="softkey_config",
                reason="no_device_canonical_id",
                consequence=(
                    "PSK softkeys will not be configured "
                    "(is_psk_target=True but device_canonical_id missing)"
                ),
            )
        return []
    return [_op(cid, "configure", "softkey_config",
                f"Configure PSK softkeys for {cid}",
                depends_on=[_node_id(device_cid, "create")])]


def _expand_device_settings_template(
    obj: dict[str, Any], decisions: list,
) -> list[MigrationOp]:
    """device_settings_template → location settings + per-device overrides."""
    cid = obj["canonical_id"]
    settings = obj.get("settings") or {}
    phones_using = obj.get("phones_using", 0)
    if not settings or phones_using == 0:
        report = _current_report()
        if report is not None:
            reason = "no_settings" if not settings else "zero_phones_using"
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="device_settings_template",
                reason=reason,
                consequence=(
                    "device settings template will not be applied "
                    f"({reason} — nothing to apply or no phones to apply it to)"
                ),
            )
        return []

    family = obj.get("model_family", "unknown")
    loc_id = obj.get("location_canonical_id", "unknown")
    ops = [
        _op(cid, "apply_location_settings", "device_settings_template",
            f"Apply {family} device settings at {loc_id}"),
    ]

    for override in obj.get("per_device_overrides", []):
        dev_cid = override.get("device_canonical_id", "")
        ops.append(_op(
            cid, "apply_device_override", "device_settings_template",
            f"Override device settings for {dev_cid}",
            depends_on=[_node_id(cid, "apply_location_settings")],
        ))

    return ops


def _expand_device_profile(obj: dict[str, Any]) -> list[MigrationOp]:
    """Device profile → 1-2 ops: enable_hoteling_guest (tier 5), enable_hoteling_host (tier 5).
    Guest op requires user_canonical_id. Host op requires host_device_canonical_ids.
    """
    cid = obj["canonical_id"]
    name = obj.get("profile_name") or cid
    user_cid = obj.get("user_canonical_id")
    ops: list[MigrationOp] = []

    if obj.get("hoteling_guest_enabled") and user_cid:
        ops.append(_op(cid, "enable_hoteling_guest", "device_profile",
                        f"Enable hoteling guest for {name}",
                        depends_on=[_node_id(user_cid, "create")]))

    host_cids = obj.get("host_device_canonical_ids") or []
    if host_cids and user_cid:
        deps = [_node_id(user_cid, "create")]
        for hcid in host_cids:
            deps.append(_node_id(hcid, "create"))
        ops.append(_op(cid, "enable_hoteling_host", "device_profile",
                        f"Configure hoteling host for {name}",
                        depends_on=deps))

    return ops


def _expand_hoteling_location(obj: dict[str, Any]) -> list[MigrationOp]:
    """Hoteling location → 1 op: enable_hotdesking (tier 0).
    Enables voice portal hot desk sign-in at a location with EM phones.
    """
    cid = obj["canonical_id"]
    state = obj.get("pre_migration_state") or {}
    loc_cid = state.get("location_canonical_id", "")
    deps = [_node_id(loc_cid, "enable_calling")] if loc_cid else []
    return [_op(cid, "enable_hotdesking", "hoteling_location",
                f"Enable hot desking at {loc_cid}",
                depends_on=deps)]


def _expand_dect_network(obj: dict[str, Any]) -> list[MigrationOp]:
    """DECT network → 3 ops: create_dect_network, create_base_stations, assign_handsets.

    Dependency chain:
      create_dect_network  → depends on location:create
      create_base_stations → depends on create_dect_network
      assign_handsets      → depends on create_base_stations + each owner user:create/workspace:create

    Handset assignments are stored as-is in the op data; the handler is
    responsible for batching API calls if the DECT API imposes per-request limits.
    (from spec §5d — _expand_dect_network requirements)
    """
    cid = obj["canonical_id"]
    name = obj.get("display_name") or obj.get("network_name") or cid
    loc_cid = obj.get("location_canonical_id")
    batch = loc_cid if loc_cid else None

    # Op 1: create the DECT network
    create_deps: list[str] = []
    if loc_cid:
        create_deps.append(_node_id(loc_cid, "create"))

    op_create = _op(
        cid, "create", "dect_network",
        f"Create DECT network {name}",
        depends_on=create_deps,
        batch=batch,
    )

    # Op 2: register base stations (depends on network existing)
    op_base_stations = _op(
        cid, "create_base_stations", "dect_network",
        f"Register base stations for DECT network {name}",
        depends_on=[_node_id(cid, "create")],
        batch=batch,
    )

    # Op 3: assign handsets (depends on base stations + all owner entities)
    handset_deps: list[str] = [_node_id(cid, "create_base_stations")]
    handset_assignments = obj.get("handset_assignments") or []
    for handset in handset_assignments:
        owner_cid = handset.get("user_canonical_id")
        if owner_cid:
            if owner_cid.startswith("user:"):
                handset_deps.append(_node_id(owner_cid, "create"))
            elif owner_cid.startswith("workspace:"):
                handset_deps.append(_node_id(owner_cid, "create"))
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_handset_deps: list[str] = []
    for dep in handset_deps:
        if dep not in seen:
            seen.add(dep)
            unique_handset_deps.append(dep)

    op_assign_handsets = _op(
        cid, "assign_handsets", "dect_network",
        f"Assign handsets to DECT network {name}",
        depends_on=unique_handset_deps,
        batch=batch,
    )

    return [op_create, op_base_stations, op_assign_handsets]


def _expand_music_on_hold(obj: dict[str, Any]) -> list[MigrationOp]:
    """Music on hold → 1 op: configure (tier 5).

    Phase A: the handler is a no-op placeholder. The op exists so operators
    see music_on_hold tracked in the deployment plan; the MOHMapper's
    AUDIO_ASSET_MANUAL decisions still gate custom audio. Real per-location
    PUT /telephony/config/locations/{id}/musicOnHold calls + custom audio
    upload are deferred to a future Phase B that adds multipart support to
    execute/engine.py.
    """
    cid = obj["canonical_id"]
    name = obj.get("source_name") or cid
    return [_op(cid, "configure", "music_on_hold",
                f"Track MoH source {name} (Phase A: no-op)")]


def _expand_announcement(obj: dict[str, Any]) -> list[MigrationOp]:
    """Announcement → 1 op: upload (tier 1).

    Phase A: the handler is a no-op placeholder. The AnnouncementMapper
    always creates AUDIO_ASSET_MANUAL decisions for every announcement,
    so operators already know to manually download and upload audio. The
    op is emitted so the deployment plan shows announcements as tracked.
    Real multipart POST /telephony/config/locations/{id}/announcements is
    deferred to Phase B.
    """
    cid = obj["canonical_id"]
    name = obj.get("name") or cid
    return [_op(cid, "upload", "announcement",
                f"Track announcement {name} (Phase A: manual upload required)")]


# ---------------------------------------------------------------------------
# Types that don't produce standalone operations
# ---------------------------------------------------------------------------

_DATA_ONLY_TYPES = {
    "line": "Data consumed by user:create (extension) / workspace:assign_number",
    "voicemail_profile": "Data consumed by user:configure_voicemail",
    "e911_config": "Advisory only — ECBN handled by user:configure_settings, RedSky civic addresses are a separate workstream",
}


# ---------------------------------------------------------------------------
# Location helper
# ---------------------------------------------------------------------------

def _expand_reconcile_members(
    obj: dict[str, Any],
    canonical_id: str,
    obj_type: str,
    decisions: list[dict[str, Any]],
) -> list[MigrationOp]:
    """One ``reconcile_members`` op for a ``proceed_partial`` cross-site group.

    The op is what makes ``proceed_partial`` an honest choice: the group is
    created in wave 1 with whoever exists, and this rewrites the full membership
    once the last member has been provisioned. Its hard member edges come from
    ``feature_has_agent`` in ``dependency.py`` — nothing here tracks waves.
    """
    rule = RECONCILE_RULES.get(obj_type)
    if rule is None:
        return []

    chosen = next(
        (
            d.get("chosen_option")
            for d in decisions
            if d.get("type") == _CROSS_SITE_TYPE
            and (d.get("context") or {}).get("construct_id") == canonical_id
        ),
        None,
    )
    if chosen != "proceed_partial":
        return []

    # Nothing to reconcile if the construct has no members at all.
    if not any(obj.get(field) for field, _key in rule.member_fields):
        return []

    name = obj.get("name", canonical_id)
    return [_op(
        canonical_id, "reconcile_members", obj_type,
        f"Reconcile full membership for {obj_type.replace('_', ' ')} {name}",
        depends_on=[_node_id(canonical_id, "create")],
        batch=_location_from_provenance(obj),
    )]


def _location_from_provenance(obj: dict[str, Any]) -> str | None:
    """Extract location_id from object data. Features may store it differently."""
    return obj.get("location_id")


# ---------------------------------------------------------------------------
# Expansion dispatch
# All expanders take (obj_data, decisions) for uniformity.
# ---------------------------------------------------------------------------



def _expand_receptionist_config(obj: dict) -> list:
    """Receptionist config -> 0-1 ops: configure (tier 6)."""
    cid = obj["canonical_id"]
    user_cid = obj.get("user_canonical_id")
    deps = [_node_id(user_cid, "create")] if user_cid else []
    for member_cid in obj.get("monitored_members", []):
        if member_cid:
            deps.append(_node_id(member_cid, "create"))
    loc_cid = obj.get("location_canonical_id")
    if loc_cid:
        deps.append(_node_id(loc_cid, "create"))
    return [_op(cid, "configure", "receptionist_config",
                f"Configure receptionist client for {cid}",
                depends_on=deps)]


def _expand_executive_assistant(obj: dict[str, Any]) -> list[MigrationOp]:
    """Executive/assistant pairing → up to 7 ops.

    Execution order (from spec §3g):
    1. assign_executive_type  — depends on executive user:create
    2. assign_assistant_type  — depends on all assistant user:create
    3. assign_assistants      — depends on steps 1 + 2 (both type ops)
    4-7. configure_alert, configure_filtering, configure_screening,
         configure_assistant_settings — each depends on step 3

    If the executive or all assistants are unresolved, the pairing has no
    users to act on and produces no ops. Individual unresolved assistants are
    silently skipped at handler time.
    (from 2026-04-10-executive-assistant-migration.md §4e)
    """
    cid = obj["canonical_id"]
    exec_cid = obj.get("executive_canonical_id")
    asst_cids = obj.get("assistant_canonical_ids") or []

    if not exec_cid and not asst_cids:
        report = _current_report()
        if report is not None:
            _warn_skip(
                report,
                canonical_id=cid,
                entity_type="executive_assistant",
                reason="no_exec_no_assistants",
                consequence=(
                    "exec/assistant pairing skipped (both executive and "
                    "assistant lists are empty)"
                ),
            )
        return []

    # Build dependencies for type-assignment ops
    exec_user_dep = [_node_id(exec_cid, "create")] if exec_cid else []
    asst_user_deps = [_node_id(a, "create") for a in asst_cids if a]

    # Step 1: assign executive type
    assign_exec_type_node = _node_id(cid, "assign_executive_type")
    ops = [_op(cid, "assign_executive_type", "executive_assistant",
               f"Set EXECUTIVE type for {exec_cid or cid}",
               depends_on=exec_user_dep)]

    # Step 2: assign assistant types (one op covers all assistants in the handler)
    assign_asst_type_node = _node_id(cid, "assign_assistant_type")
    ops.append(_op(cid, "assign_assistant_type", "executive_assistant",
                   f"Set EXECUTIVE_ASSISTANT type for assistants of {cid}",
                   depends_on=asst_user_deps))

    # Step 3: pair assistants to executive — depends on both type assignments
    assign_assistants_node = _node_id(cid, "assign_assistants")
    ops.append(_op(cid, "assign_assistants", "executive_assistant",
                   f"Assign assistants to executive {exec_cid or cid}",
                   depends_on=[assign_exec_type_node, assign_asst_type_node]))

    # Steps 4-7: post-pairing configuration — all depend on step 3
    post_deps = [assign_assistants_node]

    ops.append(_op(cid, "configure_alert", "executive_assistant",
                   f"Configure executive alert settings for {exec_cid or cid}",
                   depends_on=post_deps))

    if obj.get("filter_enabled"):
        ops.append(_op(cid, "configure_filtering", "executive_assistant",
                       f"Configure executive call filtering for {exec_cid or cid}",
                       depends_on=post_deps))

    if obj.get("screening_enabled"):
        ops.append(_op(cid, "configure_screening", "executive_assistant",
                       f"Configure executive call screening for {exec_cid or cid}",
                       depends_on=post_deps))

    if asst_cids:
        ops.append(_op(cid, "configure_assistant_settings", "executive_assistant",
                       f"Configure assistant settings for {cid}",
                       depends_on=post_deps))

    return ops


_EXPANDERS: dict[str, Any] = {
    "location": lambda obj, _: _expand_location(obj),
    "trunk": lambda obj, _: _expand_trunk(obj),
    "route_group": lambda obj, _: _expand_route_group(obj),
    "route_list": lambda obj, _: _expand_route_list(obj),
    "operating_mode": lambda obj, _: _expand_operating_mode(obj),
    "schedule": lambda obj, _: _expand_schedule(obj),
    "user": lambda obj, _: _expand_user(obj),
    "workspace": lambda obj, _: _expand_workspace(obj),
    "device": lambda obj, decs: _expand_device(obj, decs),
    "dial_plan": lambda obj, _: _expand_dial_plan(obj),
    "translation_pattern": lambda obj, _: _expand_translation_pattern(obj),
    "calling_permission": lambda obj, _: _expand_calling_permission(obj),
    "hunt_group": lambda obj, _: _expand_hunt_group(obj),
    "call_queue": lambda obj, _: _expand_call_queue(obj),
    "auto_attendant": lambda obj, _: _expand_auto_attendant(obj),
    "call_park": lambda obj, _: _expand_call_park(obj),
    "pickup_group": lambda obj, _: _expand_pickup_group(obj),
    "paging_group": lambda obj, _: _expand_paging_group(obj),
    "voicemail_group": lambda obj, _: _expand_voicemail_group(obj),
    "shared_line": lambda obj, decs: _expand_shared_line(obj, decs),
    "virtual_line": lambda obj, _: _expand_virtual_line(obj),
    "line_key_template": lambda obj, _: _expand_line_key_template(obj),
    "call_forwarding": lambda obj, _: _expand_call_forwarding(obj),
    "single_number_reach": lambda obj, _: _expand_single_number_reach(obj),
    "ecbn_config": lambda obj, _: _expand_ecbn_config(obj),
    "monitoring_list": lambda obj, _: _expand_monitoring_list(obj),
    "receptionist_config": lambda obj, _: _expand_receptionist_config(obj),
    "device_layout": lambda obj, _: _expand_device_layout(obj),
    "softkey_config": lambda obj, _: _expand_softkey_config(obj),
    "device_settings_template": lambda obj, d: _expand_device_settings_template(obj, d),
    "device_profile": lambda obj, _: _expand_device_profile(obj),
    "hoteling_location": lambda obj, _: _expand_hoteling_location(obj),
    "dect_network": lambda obj, _: _expand_dect_network(obj),
    "music_on_hold": lambda obj, _: _expand_music_on_hold(obj),
    "announcement": lambda obj, _: _expand_announcement(obj),
    "executive_assistant": lambda obj, _: _expand_executive_assistant(obj),
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def expand_to_operations(
    store: MigrationStore,
    bulk_device_threshold: int | None = None,
    skip_rebuild_phones: bool = False,
    config: dict | None = None,
    report: PlannerSkipReport | None = None,
    fail_on_unresolved: bool | None = None,
) -> list[MigrationOp]:
    """Expand each analyzed canonical object into its constituent API operations.

    Only objects at status 'analyzed' are expanded. Objects at 'needs_decision'
    are skipped — they have pending decisions that must be resolved first.

    Generic skip: any object with a resolved "skip" decision of type
    DEVICE_INCOMPATIBLE, EXTENSION_CONFLICT, or LOCATION_AMBIGUOUS is
    suppressed entirely (no ops produced).

    Special handling: SHARED_LINE_COMPLEX decisions are checked inside
    the shared_line expander (supports "virtual_line" option in addition
    to "skip").

    Silent-skip visibility (2026-04-15): every short-circuit path emits a
    ``logger.warning`` AND records a ``PlannerSkipEntry`` into ``report`` (or
    a local report, if ``report`` is None). The aggregate summary is logged
    before returning. This guards against the ``DEVICE_FIRMWARE_CONVERTIBLE``
    class of bug where a stale decision silently excluded entities from the
    plan.

    Args:
        store: The migration store to read analyzed objects from.
        bulk_device_threshold: When the number of unique devices being created
            meets or exceeds this value, replace per-device settings/layout/
            softkey ops with bulk submission ops via ``_optimize_for_bulk``.
            When ``None``, uses ``BULK_DEVICE_THRESHOLD_DEFAULT``.
        config: Project config dict (from config.json). When present, consulted
            by device expander for ``convertible_provisioning`` mode.
        report: Optional caller-supplied ``PlannerSkipReport``. When omitted,
            a local report is created; callers that want to inspect the
            roll-up pass one in and read it after the call returns.
        fail_on_unresolved: When True, raise ``PlannerUnresolvedError`` at
            the end of expansion if any entity was skipped due to a stale
            or pending decision. When ``None`` (default), consults the
            ``WXCLI_PLAN_FAIL_ON_UNRESOLVED`` environment variable (any
            truthy string enables the gate).

    (from 05-dependency-graph.md lines 38-75,
     phase-07-planning.md lines 26-27)
    """
    # Resolve fail_on_unresolved from env if caller left it unset.
    if fail_on_unresolved is None:
        env = os.environ.get("WXCLI_PLAN_FAIL_ON_UNRESOLVED", "").strip().lower()
        fail_on_unresolved = env in ("1", "true", "yes", "on")

    # Install the skip report for the duration of this call so expanders
    # can call _current_report() without threading it through every kwarg.
    # ContextVar.set() returns a Token that we pass to reset() in finally —
    # this restores the prior context value (supports nested calls / threads /
    # asyncio tasks without clobbering).
    if report is None:
        report = PlannerSkipReport()
    _ctx_token = _set_current_report(report)

    analyzed_objects = store.query_by_status("analyzed")
    all_ops: list[MigrationOp] = []
    skipped_data_only = 0
    skipped_by_decision = 0

    # Build decision indexes once (avoids O(objects * decisions) repeated queries)
    decisions_index = _build_decisions_index(store)
    stale_index = _build_stale_decisions_index(store)
    pending_index = _build_pending_decisions_index(store)
    # Known locations — used to recognise a cross-site decision that was
    # resolved by naming a location instead of one of the literal option ids.
    location_ids = _location_canonical_ids(store)

    try:
        for obj in analyzed_objects:
            obj_data = obj.model_dump()
            cid = obj_data["canonical_id"]
            # Derive object_type from canonical_id prefix (e.g., "user:0001" → "user")
            obj_type = cid.split(":")[0] if ":" in cid else "unknown"

            # Data-only types don't produce operations — log per-object so
            # operators can see exactly which lines / voicemail profiles / etc.
            # were consumed elsewhere vs. dropped by accident.
            if obj_type in _DATA_ONLY_TYPES:
                skipped_data_only += 1
                logger.debug(
                    "Planner skip (expected): %s %s — data-only type (%s)",
                    obj_type, cid, _DATA_ONLY_TYPES[obj_type],
                )
                report.record(
                    canonical_id=cid,
                    entity_type=obj_type,
                    reason="data_only_type",
                    consequence=_DATA_ONLY_TYPES[obj_type],
                    by_design=True,
                )
                continue

            expander = _EXPANDERS.get(obj_type)
            if expander is None:
                # Unknown expander — loud WARN, record so summary shows it.
                _warn_skip(
                    report,
                    canonical_id=cid,
                    entity_type=obj_type,
                    reason="no_expander_registered",
                    consequence=(
                        f"no planner expansion pattern for type '{obj_type}' — "
                        "entity will NOT be provisioned (add to _EXPANDERS)"
                    ),
                )
                continue

            # Stale decisions on an analyzed object are the DEVICE_FIRMWARE_CONVERTIBLE
            # bug pattern — analyzer rewrote fingerprints, the old decision got
            # stale-marked, and the planner previously dropped the entity without
            # logging. Detect and WARN so this class of bug is loud going forward.
            stale_decisions = stale_index.get(cid, [])
            for sd in stale_decisions:
                _warn_anomaly(
                    report,
                    canonical_id=cid,
                    entity_type=obj_type,
                    reason="stale_decision_attached",
                    decision_type=sd.get("type"),
                    decision_state="stale",
                    consequence=(
                        f"{obj_type} has a stale {sd.get('type')} decision — "
                        "re-running analyze may have invalidated this decision; "
                        "inspect with `wxcli cucm decisions --status stale` and "
                        "re-resolve if needed"
                    ),
                )

            # Pending decisions on an analyzed object indicate a status-update
            # bug (the object should be at 'needs_decision', not 'analyzed').
            # WARN loudly so this drift is caught.
            pending_decisions = pending_index.get(cid, [])
            for pd in pending_decisions:
                if pd.get("type") == _CROSS_SITE_TYPE:
                    continue  # handled by the cross-site gate below
                _warn_anomaly(
                    report,
                    canonical_id=cid,
                    entity_type=obj_type,
                    reason="pending_decision_on_analyzed_object",
                    decision_type=pd.get("type"),
                    decision_state="pending",
                    consequence=(
                        f"{obj_type} is status=analyzed but has a pending "
                        f"{pd.get('type')} decision — fix analyzer status logic "
                        "and re-run `wxcli cucm plan`"
                    ),
                )

            # Cross-site gate. This is the ONE decision type that blocks on
            # *pending*: a construct whose members straddle a site boundary must
            # not be planned until a human has chosen what happens to the members
            # on the other side. Every other type keeps its existing behaviour.
            # Scoped to the construct itself: a cross-site decision also lists its
            # remote members in affected_objects (so the report can link them), but
            # gating those users would block provisioning real people.
            # decisions_index already holds every non-stale decision (pending and
            # resolved), so it is the single source here — concatenating
            # pending_decisions would double-count.
            cross_site = [
                d
                for d in decisions_index.get(cid, [])
                if d.get("type") == _CROSS_SITE_TYPE
                and (d.get("context") or {}).get("construct_id") == cid
            ]
            cross_site_pending = [d for d in cross_site if not d.get("chosen_option")]
            cross_site_skip = [d for d in cross_site if d.get("chosen_option") == "skip"]

            if cross_site_pending or cross_site_skip:
                skipped_by_decision += 1
                unreviewed = bool(cross_site_pending)
                for d in cross_site_pending or cross_site_skip:
                    ctx = d.get("context") or {}
                    sites = ", ".join(
                        str(entry.get("location_name", ""))
                        for entry in ctx.get("remote_locations", [])
                        if entry.get("location_name")
                    )
                    _warn_skip(
                        report,
                        canonical_id=cid,
                        entity_type=obj_type,
                        reason="cross_site_unreviewed" if unreviewed else "decision_skip",
                        decision_type=_CROSS_SITE_TYPE,
                        decision_state="pending" if unreviewed else "skip",
                        consequence=(
                            f"{obj_type} has members at {sites or 'another site'} and "
                            "has not been reviewed — it will NOT be provisioned. "
                            "Resolve with `wxcli cucm decide` before planning"
                        )
                        if unreviewed
                        else (
                            f"{obj_type} will not be provisioned to Webex "
                            "(operator chose 'skip' for CROSS_SITE_DEPENDENCY)"
                        ),
                    )
                continue

            decisions = decisions_index.get(cid, [])

            # Generic skip: any _SKIP_DECISION_TYPES resolved as "skip" → suppress object
            skip_decision = _find_skip_decision(decisions)
            if skip_decision is not None:
                skipped_by_decision += 1
                _warn_skip(
                    report,
                    canonical_id=cid,
                    entity_type=obj_type,
                    reason="decision_skip",
                    decision_type=skip_decision.get("type"),
                    decision_state="skip",
                    consequence=(
                        f"{obj_type} will not be provisioned to Webex "
                        f"(operator chose 'skip' for {skip_decision.get('type')})"
                    ),
                )
                continue

            # Patch location_id from resolved LOCATION_AMBIGUOUS decision
            # (e.g., trunk with no device pool where user picked a location)
            loc_choice = _decision_chosen(decisions, "LOCATION_AMBIGUOUS")
            if loc_choice and loc_choice != "skip" and not obj_data.get("location_id"):
                obj_data["location_id"] = loc_choice
                # Persist the patched location_id back to the store object
                if hasattr(obj, "location_id"):
                    obj.location_id = loc_choice
                    store.upsert_object(obj)

            # Patch the construct's location from a resolved CROSS_SITE_DEPENDENCY
            # whose chosen_option is a known location canonical_id. Unlike the
            # LOCATION_AMBIGUOUS patch above, this one OVERRIDES an existing value —
            # that is the entire point of 'reassign_home'. It changes which batch the
            # construct lands in, so log old → new at INFO.
            # (from docs/prompts/cross-site-phase-2.md §5)
            site_choice = _cross_site_location_choice(decisions, cid, location_ids)
            if site_choice:
                loc_field = next(
                    (f for f in _LOCATION_FIELDS if f in obj_data), _LOCATION_FIELDS[0]
                )
                previous = obj_data.get(loc_field)
                if previous != site_choice:
                    obj_data[loc_field] = site_choice
                    logger.info(
                        "Cross-site reassignment: %s %s moved %s → %s (%s)",
                        obj_type, cid, previous or "<unset>", site_choice, loc_field,
                    )
                    # Persist so re-planning and the report see the same location.
                    # Types with no location field of their own (e.g. paging_group)
                    # are patched in-memory only — the batch still follows.
                    if hasattr(obj, loc_field):
                        setattr(obj, loc_field, site_choice)
                        store.upsert_object(obj)

            # Device expander takes an optional config dict for convertible_provisioning mode.
            if obj_type == "device":
                ops = _expand_device(obj_data, decisions, config=config)
            elif obj_type == "shared_line":
                # Needs the store to resolve the owners' location when the
                # operator chose 'virtual_line' (§6.3).
                ops = _expand_shared_line(obj_data, decisions, store=store)
            else:
                ops = expander(obj_data, decisions)
            all_ops.extend(ops)

            # Membership reconcile — only for a construct the operator chose to
            # create with local members only. migrate_together needs none
            # (everyone lands in the same wave); skip and reassign_home do not
            # apply. (from docs/prompts/cross-site-phase-2.md §7.3)
            all_ops.extend(_expand_reconcile_members(obj_data, cid, obj_type, decisions))

        # ---- Aggregate summary ----
        logger.info(
            "Expanded %d analyzed objects into %d operations "
            "(%d data-only skipped, %d skipped by decision)",
            len(analyzed_objects) - skipped_data_only - skipped_by_decision,
            len(all_ops),
            skipped_data_only,
            skipped_by_decision,
        )

        # Entities at status='needs_decision' never reach expansion above,
        # so they don't appear in ``report.entries``. Attach a separate
        # count-by-decision-type summary so operators can see what's held
        # back awaiting their input.
        report.needs_decision_counts = _count_needs_decision_by_type(store)

        # Objects that never reached 'analyzed' are invisible to everything
        # above: expansion queries 'analyzed', needs_decision_counts queries
        # 'needs_decision'. Finding F08's 23 users live in that blind spot.
        report.stranded_counts = _count_stranded_by_type(store)

        _log_skip_summary(report)
        _log_anomaly_summary(report)
        _log_stranded_summary(report)
        _log_needs_decision_summary(report)

        # Post-expansion bulk optimization pass.
        if bulk_device_threshold is None:
            bulk_device_threshold = BULK_DEVICE_THRESHOLD_DEFAULT
        all_ops = _optimize_for_bulk(all_ops, store, bulk_device_threshold,
                                     skip_rebuild_phones=skip_rebuild_phones)

        # Loud-fail gate: raise if requested and anything is genuinely missing
        # from the plan. Anomalies are excluded — those entities are IN the plan,
        # and firing on them aborted correct plans citing 766 entities that were
        # all present (finding F09).
        if fail_on_unresolved and report.has_unresolved_skips:
            unresolved = report.unresolved_entries()
            reasons = sorted({e.decision_type or e.reason for e in unresolved})
            parts: list[str] = []
            if unresolved:
                parts.append(
                    f"{len(unresolved)} entities skipped due to unresolved "
                    f"decisions ({', '.join(reasons)})"
                )
            if report.stranded_counts:
                total = sum(report.stranded_counts.values())
                detail = ", ".join(
                    f"{t}: {n}"
                    for t, n in sorted(
                        report.stranded_counts.items(),
                        key=lambda kv: kv[1],
                        reverse=True,
                    )
                )
                parts.append(
                    f"{total} entities never reached the planner ({detail})"
                )
            raise PlannerUnresolvedError(
                f"Planner aborted: {'; '.join(parts)}. "
                "Re-run `wxcli cucm decisions` to resolve, or rerun `wxcli cucm plan` "
                "without `--fail-on-unresolved` to accept the gaps."
            )

        return all_ops
    finally:
        _CURRENT_REPORT.reset(_ctx_token)


def _log_skip_summary(report: PlannerSkipReport) -> None:
    """Log an aggregate roll-up of every planner skip.

    Example output::

        Planner skipped 23 entities due to unresolved decisions:
          DEVICE_INCOMPATIBLE: 15 skipped (decision=skip)
          USER_EXTENSION_CONFLICT: 5 unresolved (decision=stale)
          HUNT_GROUP_MISSING_OWNER: 3 unresolved (decision=pending)
        Review with: wxcli cucm decisions --type <type> -p <project>
    """
    if not report.entries:
        return

    by_design = report.by_design_entries
    gaps = report.gap_entries
    logger.warning(
        "Planner skipped %d entities (%d by design, %d gaps):",
        len(report.entries), len(by_design), len(gaps),
    )

    def _emit(entries: list[PlannerSkipEntry], verb: str) -> None:
        groups: dict[tuple[str, str], int] = {}
        for e in entries:
            key = (e.decision_type or e.reason, e.decision_state or "no_decision")
            groups[key] = groups.get(key, 0) + 1
        for (key, state), cnt in sorted(groups.items()):
            note = (
                f"decision={state}" if state != "no_decision"
                else "expander short-circuit"
            )
            logger.warning("    %s: %d %s (%s)", key, cnt, verb, note)

    if by_design:
        logger.warning(
            "  %d need no operation by design — nothing is missing:",
            len(by_design),
        )
        _emit(by_design, "skipped")
    if gaps:
        logger.warning(
            "  %d are gaps — an entity that should have been built was not:",
            len(gaps),
        )
        _emit(gaps, "skipped")

    # Gate the advice on whether any SKIP has a decision behind it. It used to
    # key on `has_unresolved_skips`, which is also True when entities were
    # stranded before analyze — a different population, reported in its own
    # section. On director-demo every one of the 1384 groups printed
    # "expander short-circuit", i.e. no decision existed anywhere in this
    # roll-up, and it still told the operator to go review decisions.
    if report.unresolved_entries():
        logger.warning(
            "  Review unresolved decisions with: "
            "wxcli cucm decisions --type <type> -p <project>"
        )


def _log_anomaly_summary(report: PlannerSkipReport) -> None:
    """Log an aggregate roll-up of entities that were planned despite a problem.

    Aggregate only — no per-entity line. On director-demo the per-entity form of
    this was 766 of the 1129 "Planner skip:" lines, describing entities that are
    all in the plan (findings F09 and F16). The count and the breakdown are the
    useful part; 766 individual sentences are not.
    """
    if not report.anomalies:
        return

    logger.warning(
        "Planner planned %d entities that carry an unresolved decision:",
        len(report.anomalies),
    )
    groups: dict[tuple[str, str], int] = {}
    for a in report.anomalies:
        key = (a.decision_type or a.reason, a.decision_state or "no_decision")
        groups[key] = groups.get(key, 0) + 1
    for (key, state), cnt in sorted(groups.items()):
        logger.warning("  %s: %d planned anyway (decision=%s)", key, cnt, state)
    logger.warning(
        "  These ARE in the plan. Inspect with: "
        "wxcli cucm decisions --status stale -p <project>"
    )


def _log_stranded_summary(report: PlannerSkipReport) -> None:
    """Log objects that stopped advancing before the planner could see them.

    Finding F08: 23 of 300 users sat at ``status='normalized'`` and appeared in
    none of the 1370 lines of plan output, in no roll-up, and in no report. The
    only hint anywhere was ``user-diff.html`` printing "277 users included" with
    no denominator.
    """
    if not report.stranded_counts:
        return

    total = sum(report.stranded_counts.values())
    logger.warning(
        "Planner never saw %d entities — they stopped advancing before analyze "
        "completed and are ABSENT from this plan:",
        total,
    )
    for obj_type, cnt in sorted(
        report.stranded_counts.items(), key=lambda kv: kv[1], reverse=True
    ):
        logger.warning("  %s: %d never reached status=analyzed", obj_type, cnt)
    logger.warning(
        "  Investigate with: wxcli cucm decisions --status stale -p <project>"
    )


def _log_needs_decision_summary(report: PlannerSkipReport) -> None:
    """Log entities held back at status='needs_decision' by decision type.

    These entities don't appear in ``_log_skip_summary`` because they never
    reach the planner's expansion loop — they're held back waiting for
    operator input. This surfaces them so operators know the plan isn't
    the full picture.

    Silent if ``report.needs_decision_counts`` is empty.

    Example output::

        17 entities held back awaiting your decision:
          DEVICE_LABEL_CONFLICT: 12 entities
          USER_EXTENSION_CONFLICT: 5 entities
          Review with: wxcli cucm decisions --status pending -p <project>
    """
    counts = report.needs_decision_counts
    if not counts:
        return
    total = sum(counts.values())
    logger.warning("%d entities held back awaiting your decision:", total)
    for dtype, cnt in sorted(counts.items()):
        logger.warning("  %s: %d entities", dtype, cnt)
    logger.warning(
        "  Review with: wxcli cucm decisions --status pending -p <project>"
    )
