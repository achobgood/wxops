"""Cross-cutting advisory pattern detectors (Layer 2).

Each pattern function takes a MigrationStore and returns list[AdvisoryFinding].
Patterns that don't fire return empty lists.

(from migration-advisory-design.md §4.3, §6)
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from wxcli.migration.store import MigrationStore


@dataclass
class AdvisoryFinding:
    """A single cross-cutting advisory observation."""

    pattern_name: str
    severity: str  # "HIGH", "MEDIUM", "LOW", "INFO", "CRITICAL"
    summary: str
    detail: str
    affected_objects: list[str] = field(default_factory=list)
    recommendation: str = "accept"
    recommendation_reasoning: str = ""
    category: str = ""  # "migrate_as_is" | "rebuild" | "eliminate" | "out_of_scope"

    def __post_init__(self) -> None:
        if not self.recommendation_reasoning:
            self.recommendation_reasoning = self.detail


# ===================================================================
# Helper: read objects by raw SQL (for object types not in Pydantic)
# ===================================================================

def _get_raw_objects(store: MigrationStore, object_type: str) -> list[dict[str, Any]]:
    """Get objects by type, returning parsed JSON data dicts."""
    import json
    rows = store.conn.execute(
        "SELECT data FROM objects WHERE object_type = ?", (object_type,)
    ).fetchall()
    return [json.loads(r["data"]) for r in rows]


# ===================================================================
# Pattern 1: Restriction CSS Consolidation
# ===================================================================

def detect_restriction_css_consolidation(store: MigrationStore) -> list[AdvisoryFinding]:
    """CSSes with only blocking patterns → eliminate.

    (from migration-advisory-design.md §6 Pattern 1)
    """
    csses = _get_raw_objects(store, "calling_search_space")
    if not csses:
        return []

    restriction_csses: list[dict[str, Any]] = []

    for css in csses:
        css_id = css.get("canonical_id", "")
        partitions = store.find_cross_refs(css_id, "css_contains_partition")
        if not partitions:
            continue

        all_blocking = True
        has_patterns = False

        for part_id in partitions:
            patterns = store.find_cross_refs(part_id, "partition_has_pattern")
            for pat_id in patterns:
                has_patterns = True
                pat_obj = store.get_object(pat_id)
                if pat_obj is None:
                    all_blocking = False
                    continue
                pre = pat_obj.get("pre_migration_state", {}) or {}
                # A blocking pattern has blockEnable=True
                if not pre.get("blockEnable", False):
                    all_blocking = False
                    break
            if not all_blocking:
                break

        if all_blocking and has_patterns:
            restriction_csses.append(css)

    if len(restriction_csses) < 2:
        return []

    names = [c.get("name", c.get("canonical_id", "?")) for c in restriction_csses]
    css_ids = [c.get("canonical_id", "") for c in restriction_csses]

    detail = (
        f"These {len(restriction_csses)} CSSes ({', '.join(names)}) exist only to block "
        f"specific call types — they contain no routing patterns. In Webex, outgoing "
        f"calling permissions handle call restriction at the user or location level. "
        f"No dial plan objects are needed. Recommendation: migrate the routing CSSes as "
        f"dial plans. Replace these {len(restriction_csses)} restriction CSSes with calling "
        f"permission policies configured on the affected users/locations."
    )

    return [AdvisoryFinding(
        pattern_name="restriction_css_consolidation",
        severity="HIGH",
        summary=f"{len(restriction_csses)} CSSes are restriction-only — use calling permissions instead",
        detail=detail,
        affected_objects=css_ids,
        category="eliminate",
    )]


# ===================================================================
# Pattern 2: Translation Pattern Elimination — Digit Normalization
# ===================================================================

# Patterns that indicate digit normalization
_PREFIX_STRIP_RE = re.compile(r"^\d+\.")  # e.g., "9.XXXX" — has a prefix digit before "."


def detect_translation_pattern_elimination(store: MigrationStore) -> list[AdvisoryFinding]:
    """Digit normalization patterns → eliminate.

    (from migration-advisory-design.md §6 Pattern 2)
    """
    xlates = store.get_objects("translation_pattern")
    if not xlates:
        return []

    normalization_xlates: list[dict[str, Any]] = []

    for xlate in xlates:
        matching = xlate.get("matching_pattern", "") or ""
        replacement = xlate.get("replacement_pattern", "") or ""
        pre = xlate.get("pre_migration_state", {}) or {}

        is_normalization = False

        # Strips a dial prefix (e.g., 9.XXXX → XXXX)
        if _PREFIX_STRIP_RE.match(matching):
            is_normalization = True

        # Adds country/area code (replacement longer and starts with + or country code)
        if replacement and matching:
            if replacement.startswith("+") or replacement.startswith("\\+"):
                is_normalization = True

        # Strips/adds access codes
        if matching and "." in matching and replacement and "." not in replacement:
            is_normalization = True

        if is_normalization:
            normalization_xlates.append(xlate)

    if len(normalization_xlates) < 2:
        return []

    ids = [x.get("canonical_id", "") for x in normalization_xlates]
    detail = (
        f"These {len(normalization_xlates)} translation patterns handle digit normalization "
        f"(prefix stripping, country code insertion) that Webex Calling performs natively "
        f"at the location level. Migrating them creates redundant routing rules you'll "
        f"have to maintain. Recommendation: configure each location's outside_dial_digit "
        f"and internal dialing settings, then skip these translation patterns."
    )

    return [AdvisoryFinding(
        pattern_name="translation_pattern_elimination",
        severity="MEDIUM",
        summary=f"{len(normalization_xlates)} translation patterns duplicate Webex native digit normalization",
        detail=detail,
        affected_objects=ids,
        category="eliminate",
    )]


# ===================================================================
# Pattern 4: Device Bulk Upgrade Planning
# ===================================================================

def detect_device_bulk_upgrade(store: MigrationStore) -> list[AdvisoryFinding]:
    """3+ devices of same incompatible model → upgrade plan.

    (from migration-advisory-design.md §6 Pattern 4)
    """
    decisions = store.get_all_decisions()

    model_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dec in decisions:
        if dec.get("type") != "DEVICE_INCOMPATIBLE":
            continue
        ctx = dec.get("context", {})
        model = ctx.get("cucm_model", "unknown")
        model_groups[model].append(dec)

    findings: list[AdvisoryFinding] = []
    for model, decs in model_groups.items():
        if len(decs) < 3:
            continue

        affected = []
        for d in decs:
            affected.extend(d.get("affected_objects", []))

        detail = (
            f"You have {len(decs)} {model} phones. These are incompatible with Webex Calling "
            f"and require hardware replacement. Group the replacement order to negotiate "
            f"volume pricing and streamline deployment logistics."
        )
        findings.append(AdvisoryFinding(
            pattern_name="device_bulk_upgrade",
            severity="MEDIUM",
            summary=f"{len(decs)} {model} phones need bulk replacement",
            detail=detail,
            affected_objects=affected,
            category="migrate_as_is",
        ))

    return findings


# ===================================================================
# Pattern 5: Location Consolidation Opportunity
# ===================================================================

def detect_location_consolidation(store: MigrationStore) -> list[AdvisoryFinding]:
    """Multiple locations same tz+region → consolidate.

    (from migration-advisory-design.md §6 Pattern 5)
    """
    locations = store.get_objects("location")
    if not locations:
        return []

    # Group by (timezone, region)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for loc in locations:
        tz = loc.get("time_zone", "") or ""
        pre = loc.get("pre_migration_state", {}) or {}
        region = pre.get("cucm_region_name", "") or ""
        if tz and region:
            groups[(tz, region)].append(loc)

    findings: list[AdvisoryFinding] = []
    for (tz, region), locs in groups.items():
        if len(locs) <= 2:
            continue

        names = [l.get("name", l.get("canonical_id", "?")) for l in locs]
        ids = [l.get("canonical_id", "") for l in locs]

        detail = (
            f"Device pools {', '.join(names)} map to {len(locs)} separate Webex locations "
            f"but share timezone ({tz}) and region ({region}). In CUCM, device pools manage "
            f"media resources, SRST failover, and device defaults — multiple pools per physical "
            f"site is common. In Webex, locations are administrative containers for users and "
            f"numbers. Consider consolidating based on physical office sites."
        )
        findings.append(AdvisoryFinding(
            pattern_name="location_consolidation",
            severity="LOW",
            summary=f"{len(locs)} locations share timezone {tz} and region {region} — consolidate?",
            detail=detail,
            affected_objects=ids,
            category="rebuild",
        ))

    return findings


# ===================================================================
# Pattern 8: Trunk Destination Consolidation
# ===================================================================

def detect_trunk_destination_consolidation(store: MigrationStore) -> list[AdvisoryFinding]:
    """Trunks same destination → consolidate.

    (from migration-advisory-design.md §6 Pattern 8)
    """
    trunks = store.get_objects("trunk")
    if not trunks:
        return []

    # Group by first destination address
    dest_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trunk in trunks:
        pre = trunk.get("pre_migration_state", {}) or {}
        destinations = pre.get("destinations", [])
        addr = trunk.get("address", "") or ""
        if destinations and isinstance(destinations, list) and destinations:
            first = destinations[0]
            if isinstance(first, dict):
                addr = first.get("addressIpv4", "") or first.get("addressIpv6", "") or first.get("host", "") or addr
            elif isinstance(first, str):
                addr = first
        if addr:
            dest_groups[addr].append(trunk)

    findings: list[AdvisoryFinding] = []
    for addr, trunks_at_addr in dest_groups.items():
        if len(trunks_at_addr) < 2:
            continue

        names = [t.get("name", t.get("canonical_id", "?")) for t in trunks_at_addr]
        ids = [t.get("canonical_id", "") for t in trunks_at_addr]

        detail = (
            f"Trunks {', '.join(names)} all point to the same destination ({addr}). "
            f"In CUCM, multiple trunks to the same destination provide call capacity "
            f"distribution and failover. In Webex, a single trunk supports multiple "
            f"destination addresses in a priority/weight configuration. Recommendation: "
            f"consolidate into one Webex trunk with all destination addresses listed."
        )
        findings.append(AdvisoryFinding(
            pattern_name="trunk_destination_consolidation",
            severity="LOW",
            summary=f"{len(trunks_at_addr)} trunks point to {addr} — consolidate to one",
            detail=detail,
            affected_objects=ids,
            category="rebuild",
        ))

    return findings


# ===================================================================
# Pattern 9: Voicemail Pilot Simplification
# ===================================================================

def detect_voicemail_pilot_simplification(store: MigrationStore) -> list[AdvisoryFinding]:
    """Multiple VM pilots → eliminate.

    (from migration-advisory-design.md §6 Pattern 9)
    """
    pilots = _get_raw_objects(store, "voicemail_pilot")
    if len(pilots) <= 1:
        return []

    ids = [p.get("canonical_id", "") for p in pilots]
    detail = (
        f"{len(pilots)} voicemail pilots all route to the same voicemail system. "
        f"In Webex, voicemail is per-user with location-level configuration — voicemail "
        f"pilot objects don't exist as separate migratable entities. Configure Webex "
        f"voicemail settings at the location level. These pilots don't need individual migration."
    )

    return [AdvisoryFinding(
        pattern_name="voicemail_pilot_simplification",
        severity="LOW",
        summary=f"{len(pilots)} voicemail pilots can be eliminated — Webex uses per-user voicemail",
        detail=detail,
        affected_objects=ids,
        category="eliminate",
    )]


# ===================================================================
# Pattern 10: Over-Engineered Dial Plan Detection
# ===================================================================

# Patterns matching internal extension ranges
_EXT_RANGE_RE = re.compile(r"^(\[[\d\-]+\])?X{2,4}$")


def detect_overengineered_dial_plan(store: MigrationStore) -> list[AdvisoryFinding]:
    """Patterns matching extension range → eliminate.

    (from migration-advisory-design.md §6 Pattern 10)
    """
    dial_plans = store.get_objects("dial_plan")
    if not dial_plans:
        return []

    redundant: list[dict[str, Any]] = []
    redundant_patterns: list[str] = []

    for dp in dial_plans:
        patterns = dp.get("dial_patterns", []) or []
        for pat in patterns:
            if _EXT_RANGE_RE.match(pat) or pat == "XXXX":
                if dp not in redundant:
                    redundant.append(dp)
                redundant_patterns.append(pat)

    if len(redundant) < 2:
        return []

    ids = [d.get("canonical_id", "") for d in redundant]
    detail = (
        f"These {len(redundant)} dial plan patterns ({', '.join(set(redundant_patterns))}) "
        f"match Webex's built-in internal extension dialing. Webex automatically routes "
        f"calls to extensions within the location's configured range without explicit "
        f"dial plan entries. Migrating these creates redundant rules. Verify the location's "
        f"extension range covers these patterns, then skip."
    )

    return [AdvisoryFinding(
        pattern_name="overengineered_dial_plan",
        severity="LOW",
        summary=f"{len(redundant)} dial plans duplicate Webex built-in extension routing",
        detail=detail,
        affected_objects=ids,
        category="eliminate",
    )]


# ===================================================================
# Pattern 15: Media Resource Scope Removal
# ===================================================================

def detect_media_resource_scope_removal(store: MigrationStore) -> list[AdvisoryFinding]:
    """Device pools with MRGL → out_of_scope.

    (from migration-advisory-design.md §6 Pattern 15)
    """
    device_pools = _get_raw_objects(store, "device_pool")
    if not device_pools:
        return []

    mrgl_pools: list[dict[str, Any]] = []
    mrgl_names: set[str] = set()

    for dp in device_pools:
        pre = dp.get("pre_migration_state", {}) or {}
        mrgl = pre.get("cucm_media_resource_list")
        if mrgl:
            mrgl_pools.append(dp)
            mrgl_names.add(mrgl)

    if not mrgl_pools:
        return []

    ids = [d.get("canonical_id", "") for d in mrgl_pools]
    detail = (
        f"{len(mrgl_pools)} device pools reference Media Resource Group Lists "
        f"({', '.join(sorted(mrgl_names))}). In CUCM, MRGLs manage conference bridges, "
        f"Music on Hold servers, transcoders, and media termination points. In Webex "
        f"Calling, all media resources are managed by the cloud automatically — there "
        f"are no conference bridge, transcoder, or MTP objects to provision. Remove "
        f"these from your migration scope. The only action needed: verify that Webex's "
        f"default MOH audio meets your requirements (custom MOH can be uploaded per "
        f"location via `wxcli announcements`)."
    )

    return [AdvisoryFinding(
        pattern_name="media_resource_scope_removal",
        severity="INFO",
        summary=f"{len(mrgl_pools)} device pools reference MRGLs — cloud handles media resources",
        detail=detail,
        affected_objects=ids,
        category="out_of_scope",
    )]


# ===================================================================
# Pattern 3: Hunt Pilot Behavioral Reclassification
# ===================================================================

def detect_hunt_pilot_reclassification(store: MigrationStore) -> list[AdvisoryFinding]:
    """HG with queue-like behavior → rebuild as Call Queue.

    (from migration-advisory-design.md §6 Pattern 3)
    """
    hunt_groups = store.get_objects("hunt_group")
    if not hunt_groups:
        return []

    queue_candidates: list[dict[str, Any]] = []

    for hg in hunt_groups:
        pre = hg.get("pre_migration_state", {}) or {}
        signals = []

        # Agent count > 6
        agents = hg.get("agents", []) or []
        if len(agents) > 6:
            signals.append(f"{len(agents)} agents")

        # Multiple line groups
        hg_id = hg.get("canonical_id", "")
        line_groups = store.find_cross_refs(hg_id, "hunt_list_has_line_group")
        if len(line_groups) > 1:
            signals.append(f"{len(line_groups)} line groups")

        # Distribution algorithm suggests queue
        algo = pre.get("distributionAlgorithm", "")
        if algo in ("Circular", "Longest Idle Time"):
            signals.append(f"algorithm={algo}")

        # voiceMailUsage
        vm_usage = pre.get("voiceMailUsage", "NONE")
        if vm_usage and vm_usage != "NONE":
            signals.append(f"voiceMailUsage={vm_usage}")

        if len(signals) >= 2:
            queue_candidates.append((hg, signals))

    if not queue_candidates:
        return []

    ids = [hg.get("canonical_id", "") for hg, _ in queue_candidates]
    all_signals = []
    for _, sigs in queue_candidates:
        all_signals.extend(sigs)

    detail = (
        f"These {len(queue_candidates)} hunt pilots were classified as Hunt Groups "
        f"because CUCM queueCalls was not explicitly enabled. But their behavioral "
        f"signals ({', '.join(set(all_signals))}) indicate call center patterns. "
        f"Call Queues provide queuing, per-agent reporting, overflow management, "
        f"and queue announcements that Hunt Groups lack. Recommendation: rebuild as Call Queues."
    )

    return [AdvisoryFinding(
        pattern_name="hunt_pilot_reclassification",
        severity="HIGH",
        summary=f"{len(queue_candidates)} hunt pilots show queue behavior — rebuild as Call Queues",
        detail=detail,
        affected_objects=ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 6: Shared Line Simplification — Monitoring Only
# ===================================================================

_MONITORING_LABELS = re.compile(r"(?i)(blf|monitor|busy\s*lamp|speed|dss)")


def detect_shared_line_simplification(store: MigrationStore) -> list[AdvisoryFinding]:
    """Monitoring-only secondary appearances → virtual extension.

    (from migration-advisory-design.md §6 Pattern 6)
    """
    decisions = store.get_all_decisions()
    shared_line_decs = [d for d in decisions if d.get("type") == "SHARED_LINE_COMPLEX"]
    if not shared_line_decs:
        return []

    monitoring_only: list[dict[str, Any]] = []
    labels_found: list[str] = []

    for dec in shared_line_decs:
        ctx = dec.get("context", {})
        appearances = ctx.get("appearances", [])
        if not appearances:
            continue

        # Check if secondary appearances (index > 0) are all monitoring
        secondary = appearances[1:] if len(appearances) > 1 else []
        if not secondary:
            continue

        all_monitoring = True
        for app in secondary:
            label = app.get("lineText", "") or app.get("label", "") or ""
            if not _MONITORING_LABELS.search(label):
                all_monitoring = False
                break
            labels_found.append(label)

        if all_monitoring and secondary:
            monitoring_only.append(dec)

    if not monitoring_only:
        return []

    ids = []
    for d in monitoring_only:
        ids.extend(d.get("affected_objects", []))

    detail = (
        f"These {len(monitoring_only)} shared lines appear to be used for BLF/presence "
        f"monitoring rather than call handling. The secondary appearances have monitoring "
        f"labels: {', '.join(set(labels_found))}. Webex virtual extensions provide line "
        f"monitoring and BLF status without consuming a shared line appearance slot. "
        f"Recommendation: use shared lines only for DNs where multiple users answer calls. "
        f"Use virtual extensions for monitoring-only lines."
    )

    return [AdvisoryFinding(
        pattern_name="shared_line_simplification",
        severity="LOW",
        summary=f"{len(monitoring_only)} shared lines are monitoring-only — use virtual extensions",
        detail=detail,
        affected_objects=ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 7: Partition-Based Time Routing → AA Schedule
# ===================================================================

def detect_partition_time_routing(store: MigrationStore) -> list[AdvisoryFinding]:
    """Partitions with time schedules → eliminate.

    (from migration-advisory-design.md §6 Pattern 7)
    """
    partitions = _get_raw_objects(store, "route_partition")
    if not partitions:
        return []

    time_partitions: list[dict[str, Any]] = []

    for part in partitions:
        pre = part.get("pre_migration_state", {}) or {}
        schedule = pre.get("timeScheduleIdName") or pre.get("time_schedule_name")
        if schedule:
            time_partitions.append(part)

    if not time_partitions:
        return []

    ids = [p.get("canonical_id", "") for p in time_partitions]
    names = [p.get("name", p.get("canonical_id", "?")) for p in time_partitions]
    schedules = set()
    for p in time_partitions:
        pre = p.get("pre_migration_state", {}) or {}
        s = pre.get("timeScheduleIdName") or pre.get("time_schedule_name", "")
        if s:
            schedules.add(s)

    detail = (
        f"CUCM uses partition time schedules for time-of-day call routing: "
        f"partitions {', '.join(names)} are active only during specific schedules "
        f"({', '.join(schedules)}). Webex handles time-of-day routing natively through "
        f"Auto Attendant business hours and after-hours menus — no partition/CSS chain "
        f"required. Recommendation: configure the AA's business hours schedule directly. "
        f"Don't migrate the time-schedule→partition→CSS chain as routing objects."
    )

    return [AdvisoryFinding(
        pattern_name="partition_time_routing",
        severity="MEDIUM",
        summary=f"{len(time_partitions)} partitions use time schedules — use AA schedules instead",
        detail=detail,
        affected_objects=ids,
        category="eliminate",
    )]


# ===================================================================
# Pattern 11: Partition Ordering Loss Detection (CRITICAL)
# ===================================================================

def detect_partition_ordering_loss(store: MigrationStore) -> list[AdvisoryFinding]:
    """CSS partition ordering that Webex can't replicate → CRITICAL.

    (from migration-advisory-design.md §6 Pattern 11)
    """
    from wxcli.migration.transform.cucm_pattern import cucm_patterns_overlap

    csses = _get_raw_objects(store, "calling_search_space")
    if not csses:
        return []

    ordering_dependent: list[tuple[dict, list[tuple[str, str, str, str]]]] = []

    for css in csses:
        css_id = css.get("canonical_id", "")

        # Get ordered partitions via cross-refs
        refs = store.get_cross_refs(from_id=css_id, relationship="css_contains_partition")
        if not refs:
            continue

        # Sort by ordinal to get partition order
        refs.sort(key=lambda r: r.get("ordinal", 0) or 0)

        # Build map: pattern_string → [(partition_id, ordinal, destination)]
        pattern_map: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
        partition_patterns: dict[str, list[str]] = defaultdict(list)

        for ref in refs:
            part_id = ref.get("to_id", "")
            ordinal = ref.get("ordinal", 0) or 0
            route_pats = store.find_cross_refs(part_id, "partition_has_pattern")

            for rp_id in route_pats:
                rp_obj = store.get_object(rp_id)
                if rp_obj is None:
                    continue
                pre = rp_obj.get("pre_migration_state", {}) or {}
                pat_str = pre.get("pattern", "")
                dest = pre.get("destination", "") or pre.get("routeDestination", "") or rp_id
                if pat_str:
                    pattern_map[pat_str].append((part_id, ordinal, dest))
                    partition_patterns[part_id].append(pat_str)

        # Find overlapping patterns at different positions with different destinations
        overlaps: list[tuple[str, str, str, str]] = []
        all_patterns = list(pattern_map.keys())

        for i, pat_a in enumerate(all_patterns):
            entries_a = pattern_map[pat_a]
            for pat_b in all_patterns[i:]:
                entries_b = pattern_map[pat_b]

                # Check for same or overlapping patterns
                are_same = pat_a == pat_b
                if not are_same:
                    try:
                        are_overlapping = cucm_patterns_overlap(pat_a, pat_b)
                    except (ValueError, Exception):
                        continue
                else:
                    are_overlapping = True

                if not are_overlapping:
                    continue

                # Check if they appear at different positions with different destinations
                for part_a, ord_a, dest_a in entries_a:
                    for part_b, ord_b, dest_b in entries_b:
                        if part_a == part_b and pat_a == pat_b:
                            continue  # Same entry
                        if dest_a != dest_b and ord_a != ord_b:
                            overlaps.append((pat_a, dest_a, pat_b, dest_b))

        if overlaps:
            ordering_dependent.append((css, overlaps))

    if not ordering_dependent:
        return []

    all_ids: list[str] = []
    css_details: list[str] = []
    for css, overlaps in ordering_dependent:
        css_id = css.get("canonical_id", "")
        css_name = css.get("name", css_id)
        all_ids.append(css_id)
        overlap_desc = "; ".join(
            f"'{a}' → {da} vs '{b}' → {db}" for a, da, b, db in overlaps[:3]
        )
        css_details.append(f"  {css_name}: {overlap_desc}")

    detail = (
        f"CRITICAL: {len(ordering_dependent)} CSSes depend on partition ordering to resolve "
        f"overlapping patterns. Webex Calling uses longest-match routing — partition ordering "
        f"has no equivalent. After migration, calls matching these patterns may route to a "
        f"different destination.\n\nAffected CSSes:\n"
        + "\n".join(css_details)
        + "\n\nRecommendation: resolve each overlap before migration by either (a) making one "
        f"pattern more specific so longest-match produces the correct winner, (b) removing the "
        f"redundant pattern, or (c) consolidating both routes into a single dial plan entry."
    )

    return [AdvisoryFinding(
        pattern_name="partition_ordering_loss",
        severity="CRITICAL",
        summary=f"CRITICAL: {len(ordering_dependent)} CSSes depend on partition ordering — Webex has no equivalent",
        detail=detail,
        affected_objects=all_ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 12: CPN Transformation Chain Mapping (CRITICAL)
# ===================================================================

def detect_cpn_transformation_chain(store: MigrationStore) -> list[AdvisoryFinding]:
    """Route patterns/trunks with CPN transformations → rebuild.

    (from migration-advisory-design.md §6 Pattern 12)
    """
    route_patterns = _get_raw_objects(store, "route_pattern")
    trunks = store.get_objects("trunk")

    caller_id_masking: list[str] = []
    called_party_manip: list[str] = []
    multi_level: list[str] = []

    # Check route patterns
    rp_with_transforms: list[str] = []
    for rp in route_patterns:
        pre = rp.get("pre_migration_state", {}) or {}
        rp_id = rp.get("canonical_id", "")
        has_calling = bool(pre.get("callingPartyTransformationMask") or pre.get("calling_transform_mask"))
        has_called = bool(pre.get("calledPartyTransformationMask") or pre.get("called_transform_mask"))
        has_prefix = bool(pre.get("prefixDigitsOut") or pre.get("prefix_digits_out"))

        if has_calling:
            caller_id_masking.append(rp_id)
            rp_with_transforms.append(rp_id)
        if has_called or has_prefix:
            called_party_manip.append(rp_id)
            if rp_id not in rp_with_transforms:
                rp_with_transforms.append(rp_id)

    # Check trunks
    trunk_with_transforms: list[str] = []
    for trunk in trunks:
        pre = trunk.get("pre_migration_state", {}) or {}
        t_id = trunk.get("canonical_id", "")
        has_transform = bool(
            pre.get("callingPartyTransformationMask")
            or pre.get("calledPartyTransformationMask")
            or pre.get("calling_transform_mask")
            or pre.get("called_transform_mask")
        )
        if has_transform:
            trunk_with_transforms.append(t_id)

    # Multi-level: both RP and trunk have transforms
    if rp_with_transforms and trunk_with_transforms:
        multi_level = rp_with_transforms[:3] + trunk_with_transforms[:3]

    all_affected = list(set(caller_id_masking + called_party_manip + trunk_with_transforms))
    if not all_affected:
        return []

    parts: list[str] = []
    if caller_id_masking:
        parts.append(f"Caller ID masking ({len(caller_id_masking)})")
    if called_party_manip:
        parts.append(f"Called party manipulation ({len(called_party_manip)})")
    if multi_level:
        parts.append(f"Multi-level chains ({len(multi_level)})")

    detail = (
        f"{len(rp_with_transforms)} route patterns and {len(trunk_with_transforms)} trunks "
        f"have calling/called party number transformations configured. CUCM applies these "
        f"transformations in a chain — Webex uses flat caller ID per user/location.\n\n"
        + ". ".join(parts) + ".\n\n"
        f"Note: CUCM CSS-level calling party transformation fields were not extracted. "
        f"If this deployment uses CPN transformation CSSes, those transformations require "
        f"manual review.\n\n"
        f"Recommendation: configure Webex caller ID at the user or location level for "
        f"caller ID masking. Verify Webex location dialing settings handle called party "
        f"manipulation natively. Consolidate multi-level chains to single transformation."
    )

    return [AdvisoryFinding(
        pattern_name="cpn_transformation_chain",
        severity="HIGH",
        summary=f"CPN transformations on {len(all_affected)} objects need flat Webex caller ID mapping",
        detail=detail,
        affected_objects=all_affected,
        category="rebuild",
    )]


# ===================================================================
# Pattern 13: PSTN Connection Type Recommendation (CRITICAL)
# ===================================================================

_SBC_PATTERNS = re.compile(
    r"(?i)(cube|audiocodes|ribbon|oracle|sbc|session.?border|mediant|gateway)",
)


def detect_pstn_connection_type(store: MigrationStore) -> list[AdvisoryFinding]:
    """Trunk topology → PSTN connection type recommendation.

    (from migration-advisory-design.md §6 Pattern 13)
    """
    trunks = store.get_objects("trunk")
    device_pools = _get_raw_objects(store, "device_pool")

    # Check SRST presence across device pools
    has_srst = False
    for dp in device_pools:
        pre = dp.get("pre_migration_state", {}) or {}
        if pre.get("cucm_srst") or pre.get("srstName"):
            has_srst = True
            break

    if not trunks and not device_pools:
        return []

    # Classify trunks
    sbc_trunks: list[dict] = []
    carrier_trunks: list[dict] = []
    gateway_trunks: list[dict] = []

    for trunk in trunks:
        pre = trunk.get("pre_migration_state", {}) or {}
        addr = trunk.get("address", "") or ""
        name = trunk.get("name", "") or ""
        trunk_type = pre.get("sipTrunkType", "") or ""

        if _SBC_PATTERNS.search(name) or _SBC_PATTERNS.search(addr) or _SBC_PATTERNS.search(trunk_type):
            sbc_trunks.append(trunk)
        else:
            carrier_trunks.append(trunk)

    # Check for gateway objects
    gateways = _get_raw_objects(store, "gateway")
    if gateways:
        gateway_trunks = gateways

    # Determine recommendation
    recommendations: list[str] = []
    all_ids: list[str] = [t.get("canonical_id", "") for t in trunks]

    if not trunks and not gateway_trunks:
        recommendations.append(
            "No trunks detected. Recommendation: Cloud Connected PSTN (CCPP) — "
            "pure cloud deployment with no existing PSTN equipment to reuse."
        )
    elif sbc_trunks:
        recommendations.append(
            f"SBC trunks detected ({len(sbc_trunks)}). Recommendation: Local Gateway — "
            f"reuse existing SBC as Webex Local Gateway. Preserves PSTN connectivity"
            + (" and survivability." if has_srst else ".")
        )
    elif gateway_trunks:
        recommendations.append(
            f"PRI/gateway detected ({len(gateway_trunks)}). Recommendation: Local Gateway — "
            f"PRI circuits require local hardware. Convert to CUBE as Webex Local Gateway."
        )
        all_ids.extend(g.get("canonical_id", "") for g in gateway_trunks)
    elif carrier_trunks and has_srst:
        recommendations.append(
            f"Carrier SIP trunks with SRST ({len(carrier_trunks)}). Recommendation: Local "
            f"Gateway — survivability requirement means a local SBC is needed."
        )
    elif carrier_trunks:
        recommendations.append(
            f"Carrier SIP trunks ({len(carrier_trunks)}). Recommendation: Cloud Connected "
            f"PSTN if carrier is a Webex CCPP partner, otherwise Premises-based PSTN with "
            f"a Webex-registered Local Gateway."
        )

    if not recommendations:
        return []

    detail = (
        "Trunk topology analysis:\n\n"
        + "\n".join(f"- {r}" for r in recommendations)
        + f"\n\nSRST/survivability: {'Yes' if has_srst else 'No'}"
        + "\n\nThis drives your Webex trunk and route group design — configure these "
        "before migrating call routing."
    )

    summary_type = "Local Gateway" if (sbc_trunks or gateway_trunks or has_srst) else "Cloud Connected PSTN"

    return [AdvisoryFinding(
        pattern_name="pstn_connection_type",
        severity="HIGH",
        summary=f"PSTN recommendation: {summary_type}",
        detail=detail,
        affected_objects=[i for i in all_ids if i],
        category="rebuild",
    )]


# ===================================================================
# Pattern 14: Globalized vs. Localized Dial Plan Detection
# ===================================================================

_E164_PREFIX = re.compile(r"^\\?\+")


def detect_globalized_vs_localized(store: MigrationStore) -> list[AdvisoryFinding]:
    """>50% E.164 patterns → globalized advisory.

    (from migration-advisory-design.md §6 Pattern 14)
    """
    route_patterns = _get_raw_objects(store, "route_pattern")
    if not route_patterns:
        return []

    e164_count = 0
    total = 0

    for rp in route_patterns:
        pre = rp.get("pre_migration_state", {}) or {}
        pat = pre.get("pattern", "")
        if not pat:
            continue
        total += 1
        if _E164_PREFIX.match(pat):
            e164_count += 1

    if total == 0:
        return []

    ratio = e164_count / total
    ids = [rp.get("canonical_id", "") for rp in route_patterns]

    if ratio > 0.5:
        style = "globalized"
        detail = (
            f"This CUCM deployment uses a globalized dial plan (E.164 with + prefix "
            f"patterns: {e164_count}/{total} = {ratio:.0%}). This maps well to Webex "
            f"Calling, which uses E.164 natively. Translation patterns that convert local "
            f"formats to E.164 are likely redundant — Webex normalizes to E.164 at the "
            f"location level."
        )
    elif ratio < 0.2:
        style = "localized"
        detail = (
            f"This CUCM deployment uses a localized dial plan (site-specific patterns, "
            f"local digit dialing: {e164_count}/{total} = {ratio:.0%} E.164). Webex uses "
            f"E.164 internally but supports local dialing via location settings. Configure "
            f"each Webex location's outside_dial_digit and internal dialing prefix to match "
            f"the local dialing behavior."
        )
    else:
        style = "hybrid"
        detail = (
            f"This CUCM deployment mixes globalized and localized dial plan styles "
            f"({e164_count}/{total} = {ratio:.0%} E.164). This typically indicates a partial "
            f"migration to E.164 or multi-site with inconsistent standards. Review routing "
            f"patterns manually and standardize on E.164 in the Webex deployment."
        )

    return [AdvisoryFinding(
        pattern_name="globalized_vs_localized",
        severity="MEDIUM",
        summary=f"Dial plan style: {style} ({ratio:.0%} E.164)",
        detail=detail,
        affected_objects=ids,
        category="migrate_as_is",
    )]


# ===================================================================
# Pattern 16: E911 / CER Migration Flag
# ===================================================================

_E911_RE = re.compile(r"(?i)(e911|emergency|elin)")


def detect_e911_migration_flag(store: MigrationStore) -> list[AdvisoryFinding]:
    """E911/ELIN patterns → out_of_scope.

    (from migration-advisory-design.md §6 Pattern 16)
    """
    route_patterns = _get_raw_objects(store, "route_pattern")
    partitions = _get_raw_objects(store, "route_partition")
    xlates = store.get_objects("translation_pattern")

    signals: list[str] = []
    affected: list[str] = []

    # Check route patterns in E911 partitions
    for rp in route_patterns:
        pre = rp.get("pre_migration_state", {}) or {}
        part_name = pre.get("routePartitionName", "") or ""
        if _E911_RE.search(part_name):
            signals.append(f"route pattern in partition '{part_name}'")
            affected.append(rp.get("canonical_id", ""))

    # Check partition names
    for part in partitions:
        pre = part.get("pre_migration_state", {}) or {}
        name = pre.get("name", "") or part.get("name", "") or ""
        if _E911_RE.search(name):
            signals.append(f"partition '{name}'")
            if part.get("canonical_id", "") not in affected:
                affected.append(part.get("canonical_id", ""))

    # Check translation patterns with ELIN-like replacement
    for xlate in xlates:
        replacement = xlate.get("replacement_pattern", "") or ""
        name = xlate.get("name", "") or ""
        if _E911_RE.search(name) or _E911_RE.search(replacement):
            signals.append(f"translation pattern '{name}'")
            affected.append(xlate.get("canonical_id", ""))

    if signals:
        detail = (
            f"Emergency services (E911) configuration detected: {'; '.join(signals)}. "
            f"Cisco Emergency Responder integration requires a separate migration "
            f"workstream to Webex E911 (RedSky/Intrado). This includes: ERL mapping "
            f"to Webex locations, ELIN range configuration, floor/zone mapping for "
            f"nomadic users, and compliance verification. This is NOT covered by the "
            f"standard calling migration. Initiate the E911 workstream in parallel."
        )
    else:
        detail = (
            "No explicit E911 configuration detected in the AXL extraction. However, "
            "Cisco Emergency Responder (CER) uses its own database and may not be fully "
            "visible via AXL. If this deployment uses CER, E911 migration requires a "
            "separate workstream. Verify with the CUCM administrator."
        )
        # Still produce an informational advisory
        return [AdvisoryFinding(
            pattern_name="e911_migration_flag",
            severity="HIGH",
            summary="E911: no signals detected but CER data may not be in AXL — verify",
            detail=detail,
            affected_objects=[],
            category="out_of_scope",
        )]

    return [AdvisoryFinding(
        pattern_name="e911_migration_flag",
        severity="HIGH",
        summary=f"E911 configuration detected — requires separate workstream",
        detail=detail,
        affected_objects=affected,
        category="out_of_scope",
    )]


# ===================================================================
# Registry — ALL_ADVISORY_PATTERNS
# ===================================================================

ALL_ADVISORY_PATTERNS: list[Callable[[MigrationStore], list[AdvisoryFinding]]] = [
    detect_restriction_css_consolidation,       # Pattern 1
    detect_translation_pattern_elimination,     # Pattern 2
    detect_hunt_pilot_reclassification,         # Pattern 3
    detect_device_bulk_upgrade,                 # Pattern 4
    detect_location_consolidation,              # Pattern 5
    detect_shared_line_simplification,          # Pattern 6
    detect_partition_time_routing,              # Pattern 7
    detect_trunk_destination_consolidation,     # Pattern 8
    detect_voicemail_pilot_simplification,      # Pattern 9
    detect_overengineered_dial_plan,            # Pattern 10
    detect_partition_ordering_loss,             # Pattern 11
    detect_cpn_transformation_chain,            # Pattern 12
    detect_pstn_connection_type,               # Pattern 13
    detect_globalized_vs_localized,             # Pattern 14
    detect_media_resource_scope_removal,        # Pattern 15
    detect_e911_migration_flag,                 # Pattern 16
]
