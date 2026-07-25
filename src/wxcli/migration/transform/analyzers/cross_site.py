"""Cross-site dependency analyzer — constructs whose members span Webex locations.

A CUCM cluster is one flat dial plan; a Webex org is a set of locations. Any CUCM
construct whose members, owners, watchers, or destinations resolve to more than one
future Webex location cannot be migrated one site at a time without a human deciding
what happens to the members on the other side of the boundary.

This analyzer is **detection only**. It does not change how a construct's location was
chosen (``feature_mapper._resolve_feature_location`` majority vote), and it does not
add or remove members. It raises one ``CROSS_SITE_DEPENDENCY`` decision per straddling
construct, which the planner treats as a hard gate until an operator resolves it.

Design: the sweep is driven by ``CROSS_SITE_RULES``. Adding a construct is a new row in
that table, never a new branch in the sweep. Per-kind behaviour lives in the collector
registry (``_COLLECTORS``), keyed by ``member_ref`` — that is the extensible axis.

(from docs/prompts/cross-site-dependency-detection.md)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule table — the single source of truth for what counts as cross-site
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CrossSiteRule:
    """One construct whose members may live in another location.

    ``member_field``  — field name, or comma-separated field names for multi-field kinds.
    ``member_ref``    — collector kind; must exist in ``_COLLECTORS``.
    ``home_location`` — ``field:<name>`` | ``owner:<field>`` | ``vote``.
    ``webex_constraint`` — documented Webex behaviour, or ``"unverified"``. Never invent one.
    """

    object_type: str
    relation: str
    member_field: str
    member_ref: str
    home_location: str
    webex_constraint: str


# Class A — membership: the construct has a location, members may be elsewhere.
# Class B — relationships: no location of their own; inherit the owner's.
# Class C — destinations: a target extension that resolves to another location.
# Class D — line identity: a DN appearing on devices owned in different locations.
CROSS_SITE_RULES: list[CrossSiteRule] = [
    # --- Class A -----------------------------------------------------------
    CrossSiteRule(
        "hunt_group", "membership", "agents", "id_list", "field:location_id",
        "Hunt group agents are not documented as location-restricted "
        "(call-features-major.md:1074) — cross-location membership unverified.",
    ),
    CrossSiteRule(
        "call_queue", "membership", "agents", "id_list", "field:location_id",
        "Call queue agents are not documented as location-restricted "
        "(call-features-major.md:1070) — cross-location membership unverified.",
    ),
    CrossSiteRule(
        "pickup_group", "membership", "agents", "id_list", "field:location_id",
        "Webex discovers eligible pickup members per location "
        "(call-features-additional.md:314) and a user may belong to only one pickup "
        "group (error 4471). Cross-location membership unverified.",
    ),
    CrossSiteRule(
        "paging_group", "membership", "targets,originators", "id_list_multi", "vote",
        "CanonicalPagingGroup carries no location — the site is derived from its "
        "members, so a split group lands wherever the majority is.",
    ),
    CrossSiteRule(
        "dect_network", "membership", "handset_assignments", "dict_list:user_canonical_id",
        "field:location_canonical_id",
        "DECT networks are created under one location "
        "(devices-dect.md) — a handset owner at another site is a design question.",
    ),
    # --- Class B -----------------------------------------------------------
    CrossSiteRule(
        # MonitoringMapper writes {target_canonical_id, display_label} entries —
        # not member_canonical_id (that key belongs to device_layout.line_members).
        "monitoring_list", "monitoring", "monitored_members",
        "dict_list:target_canonical_id", "owner:user_canonical_id",
        "Monitoring (BLF) members are resolved per person "
        "(person-call-settings-behavior.md:996) — cross-location monitoring unverified.",
    ),
    CrossSiteRule(
        "receptionist_config", "monitoring", "monitored_members", "id_list",
        "field:location_canonical_id",
        "Receptionist client monitored lines "
        "(person-call-settings-behavior.md) — cross-location monitoring unverified.",
    ),
    CrossSiteRule(
        "executive_assistant", "delegation", "assistant_canonical_ids", "id_list",
        "owner:executive_canonical_id",
        "Executive/assistant pairing is a person setting "
        "(person-call-settings-permissions.md) — cross-location pairing unverified.",
    ),
    CrossSiteRule(
        "device_layout", "line_appearance", "line_members",
        "dict_list:member_canonical_id", "owner:owner_canonical_id",
        "Webex DOES accept a device member from another location — verified live "
        "2026-07-24 (HTTP 200, GET reports the member's own foreign location; see "
        "devices-core.md members gotcha). The cross-site problem is ordering, not "
        "capability: during a phased cutover the remote member does not exist yet "
        "when the device is configured.",
    ),
    CrossSiteRule(
        "device", "device_placement", "owner_canonical_id", "owner_compare",
        "field:location_canonical_id",
        "A device's Webex location follows its owner (devices-core.md) — a phone "
        "physically at another site cannot be modelled separately.",
    ),
    CrossSiteRule(
        "device_profile", "device_placement", "host_device_canonical_ids", "id_list",
        "owner:user_canonical_id",
        "Hot desking host devices are location-scoped "
        "(devices-workspaces.md) — roaming between sites needs a host at each.",
    ),
    # --- Class C -----------------------------------------------------------
    CrossSiteRule(
        "hunt_group", "destination",
        "forward_always_destination,forward_busy_destination,"
        "forward_no_answer_destination",
        "destination", "field:location_id",
        "Forwarding destinations are dialled through the org dial plan "
        "(call-routing.md:55 — dial plans are org-wide, not per-location).",
    ),
    CrossSiteRule(
        "call_queue", "destination",
        "forward_always_destination,queue_full_destination,"
        "max_wait_time_destination,no_agent_destination,"
        "holiday_transfer_number,night_transfer_number",
        "destination", "field:location_id",
        "Overflow and after-hours destinations are dialled through the org dial plan "
        "(call-routing.md:55).",
    ),
    CrossSiteRule(
        "auto_attendant", "destination", "forward_always_destination", "destination",
        "field:location_id",
        "Auto attendant transfer targets are dialled through the org dial plan "
        "(call-routing.md:55).",
    ),
    CrossSiteRule(
        "auto_attendant", "destination",
        "business_hours_menu,after_hours_menu", "destination_menu", "field:location_id",
        "Auto attendant menu keys transfer to an extension "
        "(call-features-major.md — keyConfigurations.value).",
    ),
    CrossSiteRule(
        "call_forwarding", "destination",
        "always_destination,busy_destination,no_answer_destination,"
        "busy_internal_destination,no_answer_internal_destination,"
        "no_coverage_destination,on_failure_destination,not_registered_destination",
        "destination", "owner:user_canonical_id",
        "Per-person forwarding to an extension at another site survives migration only "
        "once that extension exists in Webex.",
    ),
    CrossSiteRule(
        "voicemail_group", "destination", "transfer_to_number", "destination_dict",
        "field:location_id",
        "Voicemail group transfer-out target "
        "(call-features-additional.md — Voicemail Groups).",
    ),
    # --- Class D -----------------------------------------------------------
    CrossSiteRule(
        "__crossref__", "line_appearance", "device_has_dn", "crossref_dn_owners", "vote",
        "A DN appearing on devices at two sites has no cross-system shared-line "
        "equivalent — the appearances cannot be split across migration waves.",
    ),
]


# ---------------------------------------------------------------------------
# Location resolution — the field name differs per canonical type
# ---------------------------------------------------------------------------

# Direct location fields, in priority order.
_LOCATION_FIELDS = ("location_id", "location_canonical_id")

# Owner fields to fall back on when the object carries no location of its own.
_OWNER_FIELDS = (
    "owner_canonical_id",
    "user_canonical_id",
    "executive_canonical_id",
    "entity_canonical_id",
)


def resolve_entity_location(
    store: MigrationStore,
    canonical_id: str,
    cache: dict[str, str | None] | None = None,
    _seen: frozenset[str] = frozenset(),
) -> str | None:
    """Resolve the Webex location canonical_id for any entity.

    Tries the object's own location field first (the name varies by type), then
    inherits from its owner. Returns ``None`` when the location cannot be determined
    — callers must treat that as a data gap, never as a cross-site dependency.
    """
    if cache is not None and canonical_id in cache:
        return cache[canonical_id]

    result: str | None = None
    obj = store.get_object(canonical_id)
    if obj is not None:
        for field_name in _LOCATION_FIELDS:
            value = obj.get(field_name)
            if value:
                result = value
                break
        if result is None:
            for field_name in _OWNER_FIELDS:
                owner = obj.get(field_name)
                if owner and owner not in _seen and owner != canonical_id:
                    result = resolve_entity_location(
                        store, owner, cache, _seen | {canonical_id}
                    )
                    if result:
                        break

    if cache is not None:
        cache[canonical_id] = result
    return result


def _display_name(obj: dict[str, Any] | None, canonical_id: str) -> str:
    """Human-readable label for a construct or member."""
    if not obj:
        return canonical_id.split(":", 1)[-1]
    for field_name in ("name", "display_name", "network_name", "profile_name"):
        value = obj.get(field_name)
        if value:
            return str(value)
    emails = obj.get("emails") or []
    if emails:
        return str(emails[0])
    for field_name in ("extension", "cucm_device_name", "mac"):
        value = obj.get(field_name)
        if value:
            return str(value)
    return canonical_id.split(":", 1)[-1]


# ---------------------------------------------------------------------------
# Extension index — Class C destinations resolve through this
# ---------------------------------------------------------------------------

# Types whose extensions/numbers a destination string can legitimately point at.
_EXTENSION_INDEX_TYPES = (
    "user",
    "workspace",
    "virtual_line",
    "hunt_group",
    "call_queue",
    "auto_attendant",
    "voicemail_group",
)


def _build_extension_index(store: MigrationStore) -> dict[str, str]:
    """Map extension / phone number → canonical_id of the entity that owns it.

    Only entities that exist in the migration inventory are indexed. A destination
    that misses this index is external (PSTN, another system) and is NOT a cross-site
    dependency.
    """
    index: dict[str, str] = {}
    for object_type in _EXTENSION_INDEX_TYPES:
        for obj in store.get_objects(object_type):
            cid = obj.get("canonical_id")
            if not cid:
                continue
            for field_name in ("extension", "phone_number", "e164"):
                value = obj.get(field_name)
                if value:
                    index.setdefault(str(value).strip(), cid)
    return index


# ---------------------------------------------------------------------------
# Collectors — one per member_ref kind. This is the extensible axis.
# ---------------------------------------------------------------------------

# A collector returns the member canonical_ids referenced by one construct.
Collector = Callable[[dict[str, Any], CrossSiteRule, dict[str, str]], list[str]]


def _collect_id_list(obj: dict[str, Any], rule: CrossSiteRule, _ext: dict[str, str]) -> list[str]:
    return [str(v) for v in (obj.get(rule.member_field) or []) if v]


def _collect_id_list_multi(
    obj: dict[str, Any], rule: CrossSiteRule, _ext: dict[str, str]
) -> list[str]:
    members: list[str] = []
    for field_name in rule.member_field.split(","):
        members.extend(str(v) for v in (obj.get(field_name.strip()) or []) if v)
    return members


def _collect_dict_list(
    obj: dict[str, Any], rule: CrossSiteRule, _ext: dict[str, str]
) -> list[str]:
    key = rule.member_ref.split(":", 1)[1]
    members: list[str] = []
    for entry in obj.get(rule.member_field) or []:
        if isinstance(entry, dict) and entry.get(key):
            members.append(str(entry[key]))
    return members


def _collect_owner_compare(
    obj: dict[str, Any], rule: CrossSiteRule, _ext: dict[str, str]
) -> list[str]:
    owner = obj.get(rule.member_field)
    return [str(owner)] if owner else []


def _collect_destination(
    obj: dict[str, Any], rule: CrossSiteRule, ext_index: dict[str, str]
) -> list[str]:
    members: list[str] = []
    for field_name in rule.member_field.split(","):
        value = obj.get(field_name.strip())
        if not value:
            continue
        target = ext_index.get(str(value).strip())
        if target and target != obj.get("canonical_id"):
            members.append(target)
    return members


def _collect_destination_dict(
    obj: dict[str, Any], rule: CrossSiteRule, ext_index: dict[str, str]
) -> list[str]:
    entry = obj.get(rule.member_field)
    if not isinstance(entry, dict):
        return []
    if not entry.get("enabled", True):
        return []
    value = entry.get("destination") or entry.get("phoneNumber")
    if not value:
        return []
    target = ext_index.get(str(value).strip())
    return [target] if target and target != obj.get("canonical_id") else []


def _collect_destination_menu(
    obj: dict[str, Any], rule: CrossSiteRule, ext_index: dict[str, str]
) -> list[str]:
    """Auto attendant menu keys: {menu: {keyConfigurations: [{key, action, value}]}}."""
    members: list[str] = []
    for field_name in rule.member_field.split(","):
        menu = obj.get(field_name.strip())
        if not isinstance(menu, dict):
            continue
        for entry in menu.get("keyConfigurations") or []:
            if not isinstance(entry, dict):
                continue
            value = entry.get("value")
            if not value:
                continue
            target = ext_index.get(str(value).strip())
            if target and target != obj.get("canonical_id"):
                members.append(target)
    return members


def _collect_synthetic(
    obj: dict[str, Any], _rule: CrossSiteRule, _ext: dict[str, str]
) -> list[str]:
    """Members were already resolved by the construct source (see _iter_constructs)."""
    return list(obj.get("_members") or [])


_COLLECTORS: dict[str, Collector] = {
    "id_list": _collect_id_list,
    "id_list_multi": _collect_id_list_multi,
    "owner_compare": _collect_owner_compare,
    "destination": _collect_destination,
    "destination_dict": _collect_destination_dict,
    "destination_menu": _collect_destination_menu,
    "crossref_dn_owners": _collect_synthetic,
}


def _resolve_collector(member_ref: str) -> Collector | None:
    if member_ref.startswith("dict_list:"):
        return _collect_dict_list
    return _COLLECTORS.get(member_ref)


# ---------------------------------------------------------------------------
# Construct sources
# ---------------------------------------------------------------------------


def _iter_dn_appearances(store: MigrationStore) -> list[dict[str, Any]]:
    """Synthesize one construct per DN that appears on 2+ devices.

    Members are the **devices**, not their owners — one person with a phone at each
    of two sites is a cross-site line appearance even though there is only one owner.
    Read from ``cross_refs`` because no ``shared_line:`` canonical object is ever
    created by the pipeline.
    """
    rows = store.conn.execute(
        """SELECT to_id AS dn_id, COUNT(DISTINCT from_id) AS device_count
           FROM cross_refs
           WHERE relationship = 'device_has_dn'
           GROUP BY to_id
           HAVING COUNT(DISTINCT from_id) > 1"""
    ).fetchall()

    constructs: list[dict[str, Any]] = []
    for row in rows:
        dn_id = row["dn_id"]
        dn_obj = store.get_object(dn_id)
        device_rows = store.conn.execute(
            "SELECT DISTINCT from_id FROM cross_refs "
            "WHERE to_id = ? AND relationship = 'device_has_dn'",
            (dn_id,),
        ).fetchall()
        label = None
        if dn_obj:
            label = dn_obj.get("extension") or dn_obj.get("cucm_pattern")
        constructs.append({
            "canonical_id": f"dn_appearance:{dn_id}",
            "name": label or dn_id.split(":", 1)[-1],
            "_members": [r["from_id"] for r in device_rows],
            "_dn_canonical_id": dn_id,
        })
    return constructs


def _iter_constructs(store: MigrationStore, rule: CrossSiteRule) -> list[dict[str, Any]]:
    if rule.object_type == "__crossref__":
        return _iter_dn_appearances(store)
    return store.get_objects(rule.object_type)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class CrossSiteAnalyzer(Analyzer):
    """Flags every construct whose members span more than one Webex location.

    Detection only — never mutates objects. One decision per construct, carrying the
    full remote-member list so the operator reviews the whole picture at once.
    """

    name = "cross_site"
    decision_types = [DecisionType.CROSS_SITE_DEPENDENCY]
    depends_on: list[str] = []

    def analyze(self, store: MigrationStore) -> list[Decision]:
        cache: dict[str, str | None] = {}
        ext_index = _build_extension_index(store)
        location_names = {
            loc.get("canonical_id", ""): _display_name(loc, loc.get("canonical_id", ""))
            for loc in store.get_objects("location")
        }

        decisions: list[Decision] = []
        unresolved_members = 0

        for rule in CROSS_SITE_RULES:
            collector = _resolve_collector(rule.member_ref)
            if collector is None:
                logger.warning(
                    "cross_site: no collector for member_ref '%s' (%s) — rule skipped",
                    rule.member_ref, rule.object_type,
                )
                continue

            for obj in _iter_constructs(store, rule):
                cid = obj.get("canonical_id")
                if not cid:
                    continue

                member_ids: list[str] = []
                for member in collector(obj, rule, ext_index):
                    if member != cid and member not in member_ids:
                        member_ids.append(member)
                if not member_ids:
                    continue

                member_locations: dict[str, str] = {}
                for member in member_ids:
                    loc = resolve_entity_location(store, member, cache)
                    if loc is None:
                        unresolved_members += 1
                    else:
                        member_locations[member] = loc
                if not member_locations:
                    continue

                home = self._resolve_home(store, rule, obj, member_locations, cache)
                if home is None:
                    continue

                remote = {m: loc for m, loc in member_locations.items() if loc != home}
                if not remote:
                    continue

                decisions.append(
                    self._build_decision(
                        store, rule, obj, home, member_locations, remote, location_names
                    )
                )

        if unresolved_members:
            logger.info(
                "cross_site: %d member reference(s) had no resolvable location — "
                "counted as a data gap, not flagged as cross-site",
                unresolved_members,
            )

        return decisions

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _vote(member_locations: dict[str, str]) -> tuple[str | None, dict[str, int]]:
        counts: dict[str, int] = {}
        for loc in member_locations.values():
            counts[loc] = counts.get(loc, 0) + 1
        if not counts:
            return None, {}
        winner = max(sorted(counts), key=lambda k: counts[k])
        return winner, counts

    def _resolve_home(
        self,
        store: MigrationStore,
        rule: CrossSiteRule,
        obj: dict[str, Any],
        member_locations: dict[str, str],
        cache: dict[str, str | None],
    ) -> str | None:
        """Where the construct itself will be created."""
        if rule.home_location.startswith("field:"):
            value = obj.get(rule.home_location.split(":", 1)[1])
            if value:
                return str(value)
        elif rule.home_location.startswith("owner:"):
            owner = obj.get(rule.home_location.split(":", 1)[1])
            if owner:
                resolved = resolve_entity_location(store, str(owner), cache)
                if resolved:
                    return resolved
        # "vote", or a field/owner that did not resolve — fall back to the members.
        winner, _counts = self._vote(member_locations)
        return winner

    @staticmethod
    def _severity(
        rule: CrossSiteRule,
        home: str,
        member_locations: dict[str, str],
        remote: dict[str, str],
    ) -> str:
        """HIGH when the construct cannot be reasoned about site-by-site.

        - 3+ locations involved: no single wave contains it.
        - Line appearances: no cross-system shared-line equivalent exists.
        - Membership where the home location is not the strict majority: the
          construct landed away from most of its members (the majority-vote trap).
        """
        distinct = {home} | set(member_locations.values())
        if len(distinct) >= 3:
            return "HIGH"
        if rule.relation == "line_appearance":
            return "HIGH"
        if rule.relation == "membership":
            local_count = len(member_locations) - len(remote)
            if local_count <= len(remote):
                return "HIGH"
        return "MEDIUM"

    def _build_decision(
        self,
        store: MigrationStore,
        rule: CrossSiteRule,
        obj: dict[str, Any],
        home: str,
        member_locations: dict[str, str],
        remote: dict[str, str],
        location_names: dict[str, str],
    ) -> Decision:
        cid = obj["canonical_id"]
        name = _display_name(obj, cid)

        def loc_name(loc_cid: str) -> str:
            return location_names.get(loc_cid, loc_cid.split(":", 1)[-1])

        remote_members = sorted(
            (
                {
                    "canonical_id": member,
                    "display_name": _display_name(store.get_object(member), member),
                    "location_canonical_id": loc,
                    "location_name": loc_name(loc),
                }
                for member, loc in remote.items()
            ),
            key=lambda entry: entry["canonical_id"],
        )

        remote_counts: dict[str, int] = {}
        for loc in remote.values():
            remote_counts[loc] = remote_counts.get(loc, 0) + 1
        remote_locations = sorted(
            (
                {
                    "location_canonical_id": loc,
                    "location_name": loc_name(loc),
                    "member_count": count,
                }
                for loc, count in remote_counts.items()
            ),
            key=lambda entry: entry["location_canonical_id"],
        )

        _winner, vote = self._vote(member_locations)
        severity = self._severity(rule, home, member_locations, remote)

        context = {
            "relation": rule.relation,
            "object_type": rule.object_type,
            "construct_id": cid,
            "object_name": name,
            "home_location": home,
            "home_location_name": loc_name(home),
            "remote_locations": remote_locations,
            "remote_members": remote_members,
            "member_field": rule.member_field,
            "location_vote": vote,
            "webex_constraint": rule.webex_constraint,
        }
        if obj.get("_dn_canonical_id"):
            context["dn_canonical_id"] = obj["_dn_canonical_id"]

        site_list = ", ".join(entry["location_name"] for entry in remote_locations)
        summary = (
            f"{_RELATION_SUMMARY.get(rule.relation, 'references')} — "
            f"'{name}' is built at {loc_name(home)} but has "
            f"{len(remote_members)} member(s) at {site_list}"
        )

        options = [
            DecisionOption(
                id="migrate_together",
                label="Migrate all members in one wave",
                impact=(
                    f"Move the {len(remote_members)} member(s) at {site_list} in the "
                    f"same wave as {loc_name(home)}; the construct is created complete"
                ),
            ),
            DecisionOption(
                id="proceed_partial",
                label="Create now with local members only",
                impact=(
                    f"{len(remote_members)} member(s) are excluded at creation and must "
                    "be added manually after their site migrates (no reconcile "
                    "operation exists)"
                ),
            ),
            DecisionOption(
                id="reassign_home",
                label="Create in a different location",
                impact=(
                    "Answer with a location canonical id (not 'reassign_home') — e.g. "
                    f"'{remote_locations[0]['location_canonical_id']}'. "
                    "The planner then builds the construct at that location instead of "
                    f"{loc_name(home)} and moves it into that site's batch. "
                    "List the ids with `wxcli cucm inventory --type location`"
                ),
            ),
            DecisionOption(
                id="skip",
                label="Do not migrate this construct",
                impact="Not provisioned to Webex — rebuild manually",
            ),
        ]

        affected = [cid] + [entry["canonical_id"] for entry in remote_members]

        return self._create_decision(
            store=store,
            decision_type=DecisionType.CROSS_SITE_DEPENDENCY,
            severity=severity,
            summary=summary,
            context=context,
            options=options,
            affected_objects=affected,
        )

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Causal data only — construct, its members, and where it lands.

        Excludes display names, vote tallies, and counts so an unrelated re-analyze
        does not stale a decision the operator already reviewed.
        """
        members = sorted(
            entry.get("canonical_id", "")
            for entry in context.get("remote_members", [])
        )
        return self._hash_fingerprint({
            "type": decision_type.value,
            "relation": context.get("relation"),
            "object_type": context.get("object_type"),
            "construct_id": context.get("construct_id"),
            "member_field": context.get("member_field"),
            "home_location": context.get("home_location"),
            "remote_members": members,
        })


_RELATION_SUMMARY = {
    "membership": "Cross-site membership",
    "monitoring": "Cross-site monitoring",
    "delegation": "Cross-site delegation",
    "destination": "Cross-site destination",
    "device_placement": "Device at a different site than its owner",
    "line_appearance": "Line appears at more than one site",
}

