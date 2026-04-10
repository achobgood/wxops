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
# Pattern 1: Restriction CSS Consolidation
# ===================================================================

def detect_restriction_css_consolidation(store: MigrationStore) -> list[AdvisoryFinding]:
    """CSSes with only blocking patterns → eliminate.

    (from migration-advisory-design.md §6 Pattern 1)
    """
    csses = store.get_objects("calling_search_space")
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

    # Include any dial_plan objects the css_mapper created from these CSSes
    # (spec §6 Pattern 1: "Affected objects: CSS canonical_ids + any dial_plan objects")
    affected = list(css_ids)
    for css_id in css_ids:
        mapped_dps = store.find_cross_refs(css_id, "css_mapped_to_dial_plan")
        affected.extend(mapped_dps)

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
        affected_objects=affected,
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
    """Multiple VM pilots pointing to the same system → eliminate.

    Only fires when all pilots share the same voicemail system (same
    pilot number prefix or same CSS). Deployments with genuinely
    independent voicemail systems are left alone.

    (from migration-advisory-design.md §6 Pattern 9)
    """
    pilots = store.get_objects("voicemail_pilot")
    if len(pilots) <= 1:
        return []

    # Group by voicemail system indicator: pilot number prefix (first 3 digits)
    # or CSS name as a proxy for which Unity Connection handles the pilot.
    def _vm_system_key(p: dict) -> str:
        pre = p.get("pre_migration_state", {}) or {}
        number = pre.get("voice_mail_pilot_number", "") or ""
        css = pre.get("css_name", "") or ""
        # Use first 3 digits of pilot number as grouping key, fall back to CSS
        prefix = number[:3] if len(number) >= 3 else number
        return f"{prefix}|{css}"

    keys = {_vm_system_key(p) for p in pilots}

    # Only fire if all pilots point to the same system (single key)
    if len(keys) > 1:
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
    device_pools = store.get_objects("device_pool")
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
    partitions = store.get_objects("route_partition")
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

    csses = store.get_objects("calling_search_space")
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
        overlaps: list[tuple[str, str, str, str, str, str]] = []  # (pat_a, dest_a, pat_b, dest_b, part_a, part_b)
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
                    except ValueError:
                        import logging
                        logging.getLogger(__name__).debug(
                            "cucm_patterns_overlap failed for %r vs %r", pat_a, pat_b,
                        )
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
                            overlaps.append((pat_a, dest_a, pat_b, dest_b, part_a, part_b))

        if overlaps:
            ordering_dependent.append((css, overlaps))

    if not ordering_dependent:
        return []

    # Collect CSS + partition + route pattern IDs involved in overlaps
    # (spec §6 Pattern 11: "Affected objects: CSS + partition + route pattern canonical_ids")
    all_ids: list[str] = []
    involved_partitions: set[str] = set()
    css_details: list[str] = []
    for css, overlaps in ordering_dependent:
        css_id = css.get("canonical_id", "")
        css_name = css.get("name", css_id)
        all_ids.append(css_id)
        for _, _, _, _, part_a, part_b in overlaps:
            involved_partitions.add(part_a)
            involved_partitions.add(part_b)
        overlap_desc = "; ".join(
            f"'{a}' → {da} vs '{b}' → {db}" for a, da, b, db, _, _ in overlaps[:3]
        )
        css_details.append(f"  {css_name}: {overlap_desc}")

    # Add partition IDs
    all_ids.extend(sorted(involved_partitions))

    # Add route pattern IDs from those partitions
    for part_id in involved_partitions:
        rp_ids = store.find_cross_refs(part_id, "partition_has_pattern")
        all_ids.extend(rp_ids)

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
    route_patterns = store.get_objects("route_pattern")
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
    device_pools = store.get_objects("device_pool")

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
    gateways = store.get_objects("gateway")
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
    route_patterns = store.get_objects("route_pattern")
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
    route_patterns = store.get_objects("route_pattern")
    partitions = store.get_objects("route_partition")
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
# Pattern 17: Recording-Enabled Users (Tier 4 Item 1)
# ===================================================================

def detect_recording_enabled_users(store: MigrationStore) -> list[AdvisoryFinding]:
    """Users with call recording enabled in CUCM need Webex recording config.

    Scans raw phone objects for lines with recordingFlag set to anything
    other than "Call Recording Disabled".
    """
    phones = store.get_objects("phone")
    if not phones:
        return []

    recording_users: set[str] = set()
    recording_phones: list[str] = []

    for phone in phones:
        pre = phone.get("pre_migration_state", {}) or {}
        lines = pre.get("lines", []) or []
        owner_raw = pre.get("ownerUserName", "")
        if isinstance(owner_raw, dict):
            owner = owner_raw.get("_value_1", "")
        else:
            owner = owner_raw or ""

        for line in lines:
            if not isinstance(line, dict):
                continue
            flag = line.get("recordingFlag", "Call Recording Disabled")
            if flag and flag != "Call Recording Disabled":
                if owner:
                    recording_users.add(owner)
                recording_phones.append(phone.get("canonical_id", ""))
                break

    if not recording_users:
        return []

    detail = (
        f"{len(recording_users)} user{'s' if len(recording_users) != 1 else ''} have call recording "
        f"enabled in CUCM across {len(recording_phones)} phone{'s' if len(recording_phones) != 1 else ''}. "
        f"The migration pipeline will set the org recording vendor to the value of the "
        f"'recording_vendor' config key (default: Webex). Webex Calling includes built-in "
        f"call recording at no extra cost. Per-user recording settings are enabled automatically "
        f"during execution. To use a different vendor, set recording_vendor in config.json "
        f"before running export (e.g., 'Dubber', 'Imagicle')."
    )

    return [AdvisoryFinding(
        pattern_name="recording_enabled_users",
        severity="LOW",
        summary=f"{len(recording_users)} users have call recording enabled — enable Webex recording per-user during migration",
        detail=detail,
        affected_objects=list(recording_phones),
        category="migrate_as_is",
    )]


# ===================================================================
# Pattern 18: SNR / Remote Destinations (Tier 4 Item 2)
# ===================================================================

def detect_snr_configured_users(store: MigrationStore) -> list[AdvisoryFinding]:
    """Remote destination profiles indicate Single Number Reach usage."""
    rdps = store.get_objects("remote_destination")
    if not rdps:
        return []

    owners = set()
    ids = []
    for rdp in rdps:
        pre = rdp.get("pre_migration_state", {}) or {}
        owner = pre.get("ownerUserId", "")
        if owner:
            owners.add(owner)
        ids.append(rdp.get("canonical_id", ""))

    detail = (
        f"{len(rdps)} remote destination profile{'s' if len(rdps) != 1 else ''} configured "
        f"for {len(owners)} user{'s' if len(owners) != 1 else ''}. CUCM Single Number Reach "
        f"controls (timer settings, answer-too-soon/too-late thresholds) do not have direct "
        f"Webex equivalents. Webex SNR is simpler — simultaneous ring to configured numbers "
        f"without timer controls. Manual setup required per user."
    )

    return [AdvisoryFinding(
        pattern_name="snr_configured_users",
        severity="MEDIUM",
        summary=f"{len(rdps)} remote destinations for {len(owners)} users — Webex SNR is simpler, manual setup required",
        detail=detail,
        affected_objects=ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 19: Calling/Called Party Transformation Patterns (Tier 4 Item 4)
# ===================================================================

def detect_transformation_patterns(store: MigrationStore) -> list[AdvisoryFinding]:
    """Calling/Called party transformations need manual review."""
    calling = store.get_objects("info_calling_xform")
    called = store.get_objects("info_called_xform")
    total = len(calling) + len(called)

    if total == 0:
        return []

    ids = [o.get("canonical_id", "") for o in calling] + [o.get("canonical_id", "") for o in called]

    detail = (
        f"{len(calling)} calling party and {len(called)} called party transformation "
        f"pattern{'s' if total != 1 else ''} found. CUCM uses these to manipulate caller ID "
        f"(ANI/CLI) for outbound calls. Webex handles caller ID transformation differently — "
        f"location-level outbound caller ID settings and per-user caller ID configuration. "
        f"Each pattern requires manual review to determine the Webex equivalent."
    )

    return [AdvisoryFinding(
        pattern_name="transformation_patterns",
        severity="MEDIUM",
        summary=f"{total} caller ID transformation patterns require manual review",
        detail=detail,
        affected_objects=ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 20: Extension Mobility Usage (Tier 4 Item 6)
# ===================================================================

def detect_extension_mobility_usage(store: MigrationStore) -> list[AdvisoryFinding]:
    """Extension Mobility device profiles indicate hot desking needs.

    Severity escalation: MEDIUM when profiles have multi-line or BLF configs
    (feature loss during hot desk sessions). LOW for simple single-line profiles.
    """
    profiles = store.get_objects("info_device_profile")
    if not profiles:
        return []

    ids = [p.get("canonical_id", "") for p in profiles]

    # Count feature loss categories from pre_migration_state
    multi_line_count = 0
    sd_count = 0
    blf_count = 0
    for p in profiles:
        pms = p.get("pre_migration_state") or {}
        if pms.get("line_count", 0) > 1:
            multi_line_count += 1
        if pms.get("speed_dial_count", 0) > 0:
            sd_count += 1
        if pms.get("blf_count", 0) > 0:
            blf_count += 1

    # Escalate to MEDIUM when profiles will lose meaningful features
    severity = "MEDIUM" if (multi_line_count > 0 or blf_count > 0) else "LOW"

    detail = (
        f"{len(profiles)} Extension Mobility device profile(s) found. "
        f"{multi_line_count} have multiple lines (will lose secondary lines). "
        f"{sd_count} have speed dials (will lose speed dials during hot desk). "
        f"{blf_count} have BLF entries (will lose BLF during hot desk). "
        f"Migration will enable Webex hoteling for these users and configure "
        f"workspace hot desking on their host devices. Users with multi-line "
        f"profiles will only get their primary line during hot desk sessions."
    )

    return [AdvisoryFinding(
        pattern_name="extension_mobility_usage",
        severity=severity,
        summary=f"{len(profiles)} Extension Mobility profiles — map to Webex hot desking",
        detail=detail,
        affected_objects=ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 21: Mixed CSS Detection (routing + restriction)
# ===================================================================

def detect_mixed_css(store: MigrationStore) -> list[AdvisoryFinding]:
    """CSSes mixing routing and restriction partitions — silent gap in Pattern 1.

    Pattern 1 (restriction_css_consolidation) only fires when ALL partitions
    are blocking. The most common real-world case is a CSS that mixes routing
    partitions with restriction partitions (e.g., allow internal + local but
    block international by omitting a partition). These get no advisory at all.

    (from kb-css-routing.md line 48, DT-CSS-002)
    """
    csses = store.get_objects("calling_search_space")
    if not csses:
        return []

    mixed_csses: list[dict[str, Any]] = []

    for css in csses:
        css_id = css.get("canonical_id", "")
        partitions = store.find_cross_refs(css_id, "css_contains_partition")
        if not partitions:
            continue

        has_blocking = False
        has_routing = False

        for part_id in partitions:
            patterns = store.find_cross_refs(part_id, "partition_has_pattern")
            for pat_id in patterns:
                pat_obj = store.get_object(pat_id)
                if pat_obj is None:
                    continue
                pre = pat_obj.get("pre_migration_state", {}) or {}
                if pre.get("blockEnable", False):
                    has_blocking = True
                else:
                    has_routing = True
            if has_blocking and has_routing:
                break

        if has_blocking and has_routing:
            mixed_csses.append(css)

    if not mixed_csses:
        return []

    names = [c.get("name", c.get("canonical_id", "?")) for c in mixed_csses]
    css_ids = [c.get("canonical_id", "") for c in mixed_csses]

    names_str = ", ".join(names[:5])
    if len(names) > 5:
        names_str += f" +{len(names) - 5} more"

    detail = (
        f"{len(mixed_csses)} CSS(es) ({names_str}) mix routing partitions with "
        f"blocking partitions. "
        f"This is the most common CUCM pattern — users can dial internal and local "
        f"but are restricted from international by partition omission or blocking rules. "
        f"In Webex, the routing partitions become dial plan entries while the blocking "
        f"partitions become calling permission policies. These must be decomposed into "
        f"two separate Webex constructs. Without this decomposition, either the routing "
        f"patterns are missed or the restrictions are lost."
    )

    return [AdvisoryFinding(
        pattern_name="mixed_css_routing_restriction",
        severity="HIGH",
        summary=f"{len(mixed_csses)} CSSes mix routing and restriction — decompose into dial plans + calling permissions",
        detail=detail,
        affected_objects=css_ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 22: Cumulative Virtual Line Counter
# ===================================================================

def detect_cumulative_virtual_line_consumption(store: MigrationStore) -> list[AdvisoryFinding]:
    """Count virtual lines recommended across all decisions — warn if approaching limits.

    DN_AMBIGUOUS and SHARED_LINE_COMPLEX decisions independently recommend
    virtual extensions without tracking cumulative consumption. The org-level
    limit is undocumented but finite.

    (from kb-webex-limits.md DT-LIMITS-003)
    """
    decisions = store.get_all_decisions()

    vl_count = 0
    vl_decision_ids: list[str] = []

    for dec in decisions:
        recommendation = dec.get("recommendation", "")
        dec_type = dec.get("type", "")

        # Count decisions recommending virtual extensions/lines
        if recommendation in ("virtual_extension", "virtual_line"):
            vl_count += 1
            vl_decision_ids.append(dec.get("decision_id", ""))

    # Also count existing virtual_line objects already in the store
    existing_vl = store.count_by_type("virtual_line")
    total_vl = vl_count + existing_vl

    if total_vl < 5:
        return []

    severity = "HIGH" if total_vl > 100 else "MEDIUM" if total_vl > 25 else "LOW"

    detail = (
        f"This migration will create approximately {total_vl} virtual lines "
        f"({existing_vl} already mapped + {vl_count} recommended by pending decisions). "
        f"Webex has an org-level virtual line limit that is not published in API documentation. "
        f"Large virtual line counts may hit provisioning failures during execution. "
        f"Recommendation: verify the org's virtual line capacity with Cisco TAC before "
        f"migration, and consider shared lines instead of virtual extensions where "
        f"users genuinely need to answer calls (not just monitor)."
    )

    return [AdvisoryFinding(
        pattern_name="cumulative_virtual_line_consumption",
        severity=severity,
        summary=f"{total_vl} virtual lines projected — verify org capacity before migration",
        detail=detail,
        affected_objects=vl_decision_ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 23: User-OAuth-Required Settings
# ===================================================================

# The 6 settings that only exist at /people/me/ and return 404 on admin tokens
_USER_ONLY_SETTINGS = {
    "simultaneousRing", "sequentialRing", "priorityAlert",
    "callNotify", "anonymousCallReject", "callPolicies",
}


def _resolve_user_canonical_id(store: MigrationStore, cucm_username: str) -> str | None:
    """Resolve a CUCM username to a canonical user ID, or return None."""
    # Try direct lookup first (canonical_id = "user:{username}")
    obj = store.get_object(f"user:{cucm_username}")
    if obj:
        return obj.get("canonical_id")
    # Fall back to scanning user objects for cucm_userid match
    users = store.get_objects("user")
    for user in users:
        if user.get("cucm_userid") == cucm_username:
            return user.get("canonical_id")
    return None


def detect_user_oauth_required(store: MigrationStore) -> list[AdvisoryFinding]:
    """Flag features that require per-user OAuth — admin tokens can't set them.

    These 6 CUCM settings map to Webex endpoints that only exist at
    /telephony/config/people/me/settings/{feature}. Admin tokens get 404.
    The pipeline migrates everything else via admin token — these will
    silently not be set unless the operator configures user-level OAuth.

    (from kb-webex-limits.md lines 151-163, kb-user-settings.md DT-SETTINGS-001)
    """
    affected_user_ids: set[str] = set()

    # Check call settings on users
    users = store.get_objects("user")
    for user in users:
        call_settings = user.get("call_settings", {}) or {}
        for setting_name in _USER_ONLY_SETTINGS:
            if call_settings.get(setting_name):
                affected_user_ids.add(user.get("canonical_id", ""))

    # Check raw phone data for line-level indicators of simRing/seqRing
    phones = store.get_objects("phone")
    for phone in phones:
        pre = phone.get("pre_migration_state", {}) or {}
        lines = pre.get("lines", []) or []
        owner_raw = pre.get("ownerUserName", "")
        if isinstance(owner_raw, dict):
            owner = owner_raw.get("_value_1", "")
        else:
            owner = owner_raw or ""

        if not owner:
            continue

        for line in lines:
            if not isinstance(line, dict):
                continue
            # simultaneousRingNumRingCycles indicates simRing was configured
            if line.get("simultaneousRingNumRingCycles"):
                # Resolve to canonical_id via cross-ref if possible
                owner_id = _resolve_user_canonical_id(store, owner)
                if owner_id:
                    affected_user_ids.add(owner_id)
                break
            # ringSettingIdleBelowRingDuration → seqRing
            if line.get("ringSettingIdleBelowRingDuration"):
                owner_id = _resolve_user_canonical_id(store, owner)
                if owner_id:
                    affected_user_ids.add(owner_id)
                break

    # Also check single_number_reach objects — these map to simultaneousRing
    snr_objects = store.get_objects("single_number_reach")
    for snr in snr_objects:
        user_id = snr.get("user_canonical_id", "")
        if user_id:
            affected_user_ids.add(user_id)

    if not affected_user_ids:
        return []

    detail = (
        f"{len(affected_user_ids)} user(s) have CUCM settings that map to Webex features "
        f"requiring per-user OAuth tokens. The 6 affected settings "
        f"({', '.join(sorted(_USER_ONLY_SETTINGS))}) only exist at "
        f"/telephony/config/people/me/settings/ endpoints — admin tokens get 404. "
        f"These settings will NOT be migrated by the standard admin-token pipeline. "
        f"Options: (a) configure a user-level OAuth integration for batch setting, "
        f"(b) have each user configure these via Webex User Hub post-migration, or "
        f"(c) accept the loss if these features are not business-critical."
    )

    return [AdvisoryFinding(
        pattern_name="user_oauth_required",
        severity="HIGH",
        summary=f"{len(affected_user_ids)} users need per-user OAuth for simRing/seqRing/callPolicies settings",
        detail=detail,
        affected_objects=sorted(affected_user_ids),
        category="out_of_scope",
    )]


# ===================================================================
# Pattern 24: Trunk Type Selection Required
# ===================================================================

_CISCO_CUBE_PATTERNS = re.compile(
    r"(?i)(cube|ios[- ]?xe|\bisr\b|\bcsr\b|c8[0-9]{3}|vedge|catalyst.*voice)",
)
_THIRD_PARTY_SBC_PATTERNS = re.compile(
    r"(?i)(audiocodes|ribbon|oracle|acme.?packet|mediant|sonus|swe.?lite|"
    r"teams.?sbc|microsoft|avaya|genband|net[- ]?border)",
)


def detect_trunk_type_selection(store: MigrationStore) -> list[AdvisoryFinding]:
    """Trunk type (REGISTERING vs CERTIFICATE_BASED) must be chosen pre-creation.

    Trunk type is IMMUTABLE after creation. Choosing wrong means delete and
    recreate, which disrupts routing mid-migration. REGISTERING = Cisco IOS-XE
    CUBE. CERTIFICATE_BASED = third-party SBC (AudioCodes, Ribbon, Oracle).

    (from kb-trunk-pstn.md, kb-webex-limits.md line 54)
    """
    trunks = store.get_objects("trunk")
    if not trunks:
        return []

    needs_type_decision: list[dict[str, Any]] = []
    auto_classified: dict[str, list[str]] = {"REGISTERING": [], "CERTIFICATE_BASED": []}

    for trunk in trunks:
        trunk_type = trunk.get("trunk_type")
        name = trunk.get("name", "") or ""
        addr = trunk.get("address", "") or ""
        pre = trunk.get("pre_migration_state", {}) or {}
        sip_type = pre.get("sipTrunkType", "") or ""
        search_text = f"{name} {addr} {sip_type}"

        # Already explicitly set
        if trunk_type in ("REGISTERING", "CERTIFICATE_BASED"):
            auto_classified[trunk_type].append(trunk.get("canonical_id", ""))
            continue

        # Try to infer from name/address patterns
        if _CISCO_CUBE_PATTERNS.search(search_text):
            auto_classified["REGISTERING"].append(trunk.get("canonical_id", ""))
        elif _THIRD_PARTY_SBC_PATTERNS.search(search_text):
            auto_classified["CERTIFICATE_BASED"].append(trunk.get("canonical_id", ""))
        else:
            needs_type_decision.append(trunk)

    if not needs_type_decision:
        return []

    names = [t.get("name", t.get("canonical_id", "?")) for t in needs_type_decision]
    ids = [t.get("canonical_id", "") for t in needs_type_decision]

    detail = (
        f"{len(needs_type_decision)} trunk(s) ({', '.join(names)}) need an explicit trunk "
        f"type selection before provisioning. Webex trunk type is IMMUTABLE after creation — "
        f"choosing wrong means deleting the trunk and recreating it, which disrupts live "
        f"call routing.\n\n"
        f"- REGISTERING: for Cisco IOS-XE CUBE (ISR, CSR, Catalyst) — uses SIP registration "
        f"with username/password.\n"
        f"- CERTIFICATE_BASED: for third-party SBCs (AudioCodes, Ribbon, Oracle) — uses "
        f"mutual TLS with certificates.\n\n"
        f"Verify which SBC model handles each trunk before migration execution."
    )

    return [AdvisoryFinding(
        pattern_name="trunk_type_selection",
        severity="CRITICAL",
        summary=f"CRITICAL: {len(needs_type_decision)} trunks need immutable type selection (REGISTERING vs CERTIFICATE_BASED)",
        detail=detail,
        affected_objects=ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 25: Inter-Cluster Trunk (ICT) Detection
# ===================================================================

_ICT_PATTERNS = re.compile(
    r"(?i)(inter[- ]?cluster|ict[- ]|ict$|intercluster|"
    r"cluster[- ]?to[- ]?cluster|emcc|extension.?mobility.?cross)",
)


def detect_intercluster_trunks(store: MigrationStore) -> list[AdvisoryFinding]:
    """Detect CUCM inter-cluster trunks — need disposition decision.

    ICTs connect CUCM clusters to each other. During migration they either
    become Local Gateway trunks (if one cluster stays on CUCM) or are
    eliminated entirely (if both clusters migrate to Webex).

    (from kb-trunk-pstn.md lines 65-67)
    """
    trunks = store.get_objects("trunk")
    if not trunks:
        return []

    ict_trunks: list[dict[str, Any]] = []

    for trunk in trunks:
        name = trunk.get("name", "") or ""
        pre = trunk.get("pre_migration_state", {}) or {}
        sip_type = pre.get("sipTrunkType", "") or ""
        description = pre.get("description", "") or ""

        search_text = f"{name} {sip_type} {description}"
        if _ICT_PATTERNS.search(search_text):
            ict_trunks.append(trunk)

    if not ict_trunks:
        return []

    names = [t.get("name", t.get("canonical_id", "?")) for t in ict_trunks]
    ids = [t.get("canonical_id", "") for t in ict_trunks]

    detail = (
        f"{len(ict_trunks)} inter-cluster trunk(s) detected ({', '.join(names)}). "
        f"ICTs connect CUCM clusters to each other for intercluster call routing and "
        f"extension mobility. After migration, these need one of:\n\n"
        f"- **Eliminate:** If both clusters migrate to Webex, ICTs are unnecessary — "
        f"all users are in the same Webex org.\n"
        f"- **Convert to Local Gateway:** If one cluster stays on CUCM during "
        f"coexistence, the ICT becomes a Webex trunk pointing at the remaining CUCM.\n"
        f"- **Replace with Webex-to-Webex routing:** If clusters become separate Webex "
        f"orgs (rare), use Webex inter-org dialing.\n\n"
        f"Decide the disposition before migration planning."
    )

    return [AdvisoryFinding(
        pattern_name="intercluster_trunk_detection",
        severity="HIGH",
        summary=f"{len(ict_trunks)} inter-cluster trunks need disposition decision (eliminate/convert/replace)",
        detail=detail,
        affected_objects=ids,
        category="rebuild",
    )]


# ===================================================================
# Pattern 26: MGCP/H.323 Gateway Protocol Detection
# ===================================================================

_MGCP_PATTERNS = re.compile(r"(?i)(mgcp|vg[0-9]{2,3}|fxs|fxo|analog[- ]?gateway)")
_H323_PATTERNS = re.compile(r"(?i)(h\.?323|gatekeeper|ras[- ]?registration)")


def detect_legacy_gateway_protocols(store: MigrationStore) -> list[AdvisoryFinding]:
    """Detect MGCP and H.323 gateways — need SIP conversion before migration.

    Webex Calling only supports SIP trunks. MGCP and H.323 gateways must be
    converted to SIP (IOS-XE CUBE) or replaced with ATA devices before
    migration.

    (from kb-trunk-pstn.md lines 73-79)
    """
    # Check trunks and gateways
    trunks = store.get_objects("trunk")
    gateways = store.get_objects("gateway")
    devices = store.get_objects("device")

    mgcp_objects: list[dict[str, Any]] = []
    h323_objects: list[dict[str, Any]] = []

    for obj_list in [trunks, gateways]:
        for obj in obj_list:
            name = obj.get("name", "") or ""
            pre = obj.get("pre_migration_state", {}) or {}
            protocol = pre.get("protocol", "") or ""
            obj_type = pre.get("product", "") or pre.get("type", "") or ""
            description = pre.get("description", "") or ""
            search_text = f"{name} {protocol} {obj_type} {description}"

            if _MGCP_PATTERNS.search(search_text):
                mgcp_objects.append(obj)
            elif _H323_PATTERNS.search(search_text):
                h323_objects.append(obj)

    # Also check devices for analog gateway models
    for device in devices:
        model = device.get("model", "") or ""
        pre = device.get("pre_migration_state", {}) or {}
        cucm_protocol = device.get("cucm_protocol", "") or ""
        if _MGCP_PATTERNS.search(f"{model} {cucm_protocol}"):
            mgcp_objects.append(device)

    total = len(mgcp_objects) + len(h323_objects)
    if total == 0:
        return []

    all_ids = [o.get("canonical_id", "") for o in mgcp_objects + h323_objects]

    parts: list[str] = []
    if mgcp_objects:
        parts.append(f"{len(mgcp_objects)} MGCP gateway(s)")
    if h323_objects:
        parts.append(f"{len(h323_objects)} H.323 gateway(s)")

    detail = (
        f"Detected {' and '.join(parts)}. Webex Calling only supports SIP trunks — "
        f"MGCP and H.323 protocols have no migration path.\n\n"
        f"For MGCP gateways (VG series, analog FXS/FXO):\n"
        f"- If the IOS version supports SIP, reconfigure as SIP CUBE trunk\n"
        f"- If not, replace with Cisco ATA 192 for analog endpoints\n"
        f"- VG400-series can run as Local Gateway with SIP\n\n"
        f"For H.323 gateways:\n"
        f"- Convert to SIP trunk registration or certificate-based\n"
        f"- H.323 gatekeepers are eliminated — Webex uses SIP registration\n\n"
        f"This conversion must happen BEFORE the Webex trunk provisioning step."
    )

    return [AdvisoryFinding(
        pattern_name="legacy_gateway_protocols",
        severity="HIGH",
        summary=f"{total} legacy protocol gateway(s) need SIP conversion before migration",
        detail=detail,
        affected_objects=all_ids,
        category="out_of_scope",
    )]


# ===================================================================
# Pattern 27: Voicemail Greeting Re-Recording
# ===================================================================

def detect_voicemail_greeting_rerecording(
    store: MigrationStore,
) -> list[AdvisoryFinding]:
    """Detect users with custom VM greetings that must be re-recorded post-migration.

    Reads MISSING_DATA decisions produced by voicemail_mapper.py (lines 278-308)
    where context.reason == 'custom_greeting_not_extractable'.
    """
    decisions = store.get_all_decisions()
    greeting_decisions = []
    affected = []
    for d in decisions:
        if d.get("type") != "MISSING_DATA":
            continue
        ctx = d.get("context", {})
        if ctx.get("reason") == "custom_greeting_not_extractable":
            greeting_decisions.append(d)
            uid = ctx.get("user_id", "")
            if uid:
                affected.append(uid)

    custom_count = len(greeting_decisions)
    if custom_count == 0:
        return []

    if custom_count <= 10:
        severity = "LOW"
    elif custom_count <= 50:
        severity = "MEDIUM"
    else:
        severity = "HIGH"

    total_vm_users = store.count_by_type("voicemail_profile")
    if total_vm_users == 0:
        total_vm_users = custom_count

    detail = (
        f"{custom_count} of {total_vm_users} voicemail-enabled users have custom "
        f"voicemail greetings that will revert to system defaults after migration.\n\n"
        f"Voicemail greetings are personal recordings stored in Unity Connection. "
        f"They cannot be automatically migrated to Webex Calling. Each user must "
        f"re-record their greeting after migration.\n\n"
        f"REQUIRED ACTION: Send a user communication at least 1 week before "
        f"migration day informing affected users:\n"
        f"1. Their voicemail greeting will reset to the system default\n"
        f"2. After migration, re-record via: Webex App > Settings > Calling > "
        f"Voicemail > Greeting, or dial the voicemail access number\n"
        f"3. If they have a script for their greeting, have it ready\n\n"
        f"This is a high-visibility issue — users notice immediately when their "
        f"personalized greeting is replaced by a generic one."
    )

    return [AdvisoryFinding(
        pattern_name="voicemail_greeting_rerecording",
        severity=severity,
        summary=(
            f"{custom_count} users must re-record voicemail greetings after migration"
        ),
        detail=detail,
        affected_objects=affected,
        category="out_of_scope",
    )]


# ===================================================================
# Pattern 28: Custom Audio Assets
# ===================================================================

def detect_custom_audio_assets(store: MigrationStore) -> list[AdvisoryFinding]:
    """Custom MoH sources and announcements requiring manual migration.

    (Pattern 28)
    """
    moh_sources = store.get_objects("music_on_hold")
    announcements = store.get_objects("announcement")

    custom_moh = [m for m in moh_sources if not m.get("is_default", False)]
    moh_count = len(custom_moh)
    ann_count = len(announcements)
    total = moh_count + ann_count

    if total == 0:
        return []

    if total >= 21:
        severity = "CRITICAL"
    elif total >= 6:
        severity = "HIGH"
    else:
        severity = "MEDIUM"

    affected = (
        [m.get("canonical_id", "") for m in custom_moh]
        + [a.get("canonical_id", "") for a in announcements]
    )

    detail = (
        f"This environment has {total} custom audio assets requiring manual migration:\n"
        f"- {moh_count} custom Music on Hold source(s)\n"
        f"- {ann_count} announcement file(s)\n\n"
        "CUCM audio files cannot be automatically transferred to Webex. Each must be:\n"
        "1. Downloaded from CUCM server filesystem (SFTP to /usr/local/cm/tftp/)\n"
        "2. Converted to WAV format if needed (Webex requires WAV, max 8 MB)\n"
        "3. Uploaded to Webex announcement repository via API or Control Hub\n"
        "4. Assigned to the appropriate location (MoH) or feature (AA/CQ greeting)\n\n"
        "Action required BEFORE migration day: Download all custom audio files from "
        "CUCM and have them ready for upload. MoH and AA greetings are customer-facing "
        "-- losing them on cutover day is a P1 experience issue."
    )

    return [AdvisoryFinding(
        pattern_name="custom_audio_assets",
        severity=severity,
        summary=f"{total} custom audio assets require manual migration ({moh_count} MoH, {ann_count} announcements)",
        detail=detail,
        affected_objects=affected,
        recommendation="accept",
        recommendation_reasoning=(
            "Custom audio assets must be manually downloaded from CUCM and uploaded to Webex."
        ),
        category="migrate_as_is",
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
    detect_recording_enabled_users,            # Pattern 17 (Tier 4)
    detect_snr_configured_users,               # Pattern 18 (Tier 4)
    detect_transformation_patterns,            # Pattern 19 (Tier 4)
    detect_extension_mobility_usage,           # Pattern 20 (Tier 4)
    detect_mixed_css,                          # Pattern 21 (Gap: silent on hybrid CSSes)
    detect_cumulative_virtual_line_consumption, # Pattern 22 (Gap: no VL limit tracking)
    detect_user_oauth_required,                # Pattern 23 (Gap: user-only settings undetected)
    detect_trunk_type_selection,               # Pattern 24 (Gap: immutable trunk type)
    detect_intercluster_trunks,                # Pattern 25 (Gap: ICT disposition)
    detect_legacy_gateway_protocols,           # Pattern 26 (Gap: MGCP/H.323 undetected)
    detect_voicemail_greeting_rerecording,     # Pattern 27 (User action: VM greeting re-recording)
    detect_custom_audio_assets,                # Pattern 28 (Audio: MoH + announcements)
]
