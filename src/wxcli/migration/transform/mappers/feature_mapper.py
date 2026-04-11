"""Feature mapper: CUCM call features -> Webex Calling features.

Maps CUCM Hunt Pilots (+ Hunt Lists + Line Groups), CTI Route Points,
Call Park Numbers, Pickup Groups, Paging Groups, and Time Schedules to
their Webex Calling equivalents.

(from 03b-transform-mappers.md §8, feature_mapper)

Cross-ref reads:
    hunt_pilot_has_hunt_list    (#21) — HuntPilot -> HuntList
    hunt_list_has_line_group    (#22) — HuntList -> LineGroup
    line_group_has_members      (#23) — LineGroup -> DN/Line (agent resolution)
    cti_rp_has_script           (#24) — CTI Route Point -> Script (AA approximation)
    schedule_has_time_period    (#25) — Schedule -> TimePeriod (OperatingMode)

Decisions generated:
    FEATURE_APPROXIMATION  — CTI RP with complex script, agent limit exceeded
    MISSING_DATA           — unresolvable hunt pilot DN
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalAutoAttendant,
    CanonicalCallPark,
    CanonicalCallQueue,
    CanonicalHuntGroup,
    CanonicalLocationSchedule,
    CanonicalOperatingMode,
    CanonicalPagingGroup,
    CanonicalPickupGroup,
    DecisionType,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    decision_to_store_dict,
    extract_provenance,
    hash_id,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helper: resolve DN canonical_id → owning user/workspace canonical_id
# (from 03b-transform-mappers.md §8: "each line group member DN → resolve to
# Webex person/workspace/virtual line ID")
# ---------------------------------------------------------------------------

def _resolve_dn_to_owner(store: MigrationStore, dn_canonical_id: str) -> str | None:
    """Resolve a DN canonical_id to its owning user or workspace.

    Chain: DN ← device_has_dn ← device → device_owned_by_user → user
    If no user owner found, check for common-area device → workspace.
    """
    # Find devices that have this DN (reverse lookup: to_id = dn_id)
    device_refs = store.get_cross_refs(to_id=dn_canonical_id, relationship="device_has_dn")
    for ref in device_refs:
        device_id = ref["from_id"]

        # Check if device is owned by a user
        user_refs = store.find_cross_refs(device_id, "device_owned_by_user")
        if user_refs:
            return user_refs[0]  # Return canonical user ID

        # Check if device is a common-area device → workspace
        # Common-area devices don't have device_owned_by_user; the device itself
        # may be associated with a workspace object
        ws_refs = store.get_cross_refs(to_id=device_id, relationship="workspace_has_device")
        if ws_refs:
            return ws_refs[0]["from_id"]

    return None


def _resolve_agents_from_dns(
    store: MigrationStore, dn_ids: list[str]
) -> list[str]:
    """Resolve a list of DN canonical_ids to deduplicated owner canonical_ids.

    Falls back to the raw DN canonical_id when the device→user chain isn't
    available (e.g., cross-refs not yet built). This preserves backward
    compatibility — the command builder handles both user IDs and DN IDs.
    """
    seen: set[str] = set()
    resolved: list[str] = []
    for dn_id in dn_ids:
        owner = _resolve_dn_to_owner(store, dn_id)
        agent_id = owner if owner else dn_id
        if agent_id not in seen:
            seen.add(agent_id)
            resolved.append(agent_id)
    return resolved


def _resolve_feature_location(
    store: MigrationStore,
    agents: list[str],
    provenance: dict | None = None,
) -> str | None:
    """Determine a feature's location from its agents.

    1. Read each agent's location_id from the store
    2. If all agents share the same location → use it
    3. If agents span multiple locations → majority wins
    4. If no agents have location_id → return None

    Note: Features without agents (e.g., call parks) get location_id from
    their pre_migration_state directly. AAs and schedules are location-scoped
    at creation time via the command builder's LOCATION_ID placeholder.
    """
    if not agents:
        return None

    location_counts: dict[str, int] = {}
    for agent_cid in agents:
        agent_obj = store.get_object(agent_cid)
        if agent_obj:
            loc = agent_obj.get("location_id")
            if loc:
                location_counts[loc] = location_counts.get(loc, 0) + 1

    if location_counts:
        # Return the most common location
        return max(location_counts, key=location_counts.get)  # type: ignore[arg-type]

    return None


# Agent limits by Webex policy
# (from 03b-transform-mappers.md §8: "SIMULTANEOUS max 50, WEIGHTED max 100, others max 1000")
_AGENT_LIMITS: dict[str, int] = {
    "SIMULTANEOUS": 50,
    "WEIGHTED": 100,
    "REGULAR": 1000,
    "CIRCULAR": 1000,
    "UNIFORM": 1000,
}

# Paging group target limit
# (from 03b-transform-mappers.md §8: "Webex paging groups support up to 75 targets")
_MAX_PAGING_TARGETS = 75

# Algorithm mapping: CUCM hunt algorithm -> Webex policy
# (from 03b-transform-mappers.md §10: Algorithm Mapping Table)
_ALGORITHM_TO_POLICY: dict[str, str] = {
    "Top Down": "REGULAR",
    "Circular": "CIRCULAR",
    "Longest Idle Time": "UNIFORM",
    "Broadcast": "SIMULTANEOUS",
}


class FeatureMapper(Mapper):
    """Maps CUCM call features to Webex Calling feature objects.

    Produces: CanonicalHuntGroup, CanonicalCallQueue, CanonicalAutoAttendant,
    CanonicalCallPark, CanonicalPickupGroup, CanonicalPagingGroup,
    CanonicalOperatingMode.

    (from 03b-transform-mappers.md §8)
    """

    name = "feature_mapper"
    depends_on = ["location_mapper", "line_mapper", "user_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        """Read CUCM feature objects and produce Webex feature canonical objects."""
        result = MapperResult()

        # Disable FK checks for cross-ref writing — feature_has_agent refs
        # may point to agents (DN IDs) not in the objects table.
        store.conn.execute("PRAGMA foreign_keys=OFF")
        try:
            self._map_hunt_pilots(store, result)
            self._map_cti_route_points(store, result)
            self._map_call_parks(store, result)
            self._map_pickup_groups(store, result)
            self._map_paging_groups(store, result)
            self._map_schedules(store, result)
            self._map_location_schedules(store, result)
        finally:
            store.conn.execute("PRAGMA foreign_keys=ON")

        return result

    # ------------------------------------------------------------------
    # Hunt Pilots: classify -> HG or CQ
    # (from 03b-transform-mappers.md §10: classify_hunt_pilot algorithm)
    # ------------------------------------------------------------------

    def _map_hunt_pilots(self, store: MigrationStore, result: MapperResult) -> None:
        """Map CUCM hunt pilots to Hunt Groups or Call Queues.

        Traverses 3-object chain: hunt_pilot -> hunt_list -> line_group -> members
        """
        # Hoist voicemail_group presence check out of the per-hunt-pilot loop —
        # the answer can't change inside the loop (nothing writes voicemail_group
        # here), so computing it once avoids O(N*M) store queries.
        has_vm_group = any(True for _ in store.get_objects("voicemail_group"))

        for hp_data in store.get_objects("hunt_pilot"):
            hp_id = hp_data["canonical_id"]
            hp_state = hp_data.get("pre_migration_state") or {}

            # --- Resolve hunt list via cross-ref (#21) ---
            hunt_list_refs = store.find_cross_refs(hp_id, "hunt_pilot_has_hunt_list")
            hunt_list_data = None
            if hunt_list_refs:
                hunt_list_data = store.get_object(hunt_list_refs[0])

            hunt_list_state = (hunt_list_data or {}).get("pre_migration_state") or {}

            # --- Resolve line groups via hunt_list -> line_group chain (#22) ---
            line_group_ids: list[str] = []
            if hunt_list_refs:
                for hl_ref in hunt_list_refs:
                    lg_refs = store.find_cross_refs(hl_ref, "hunt_list_has_line_group")
                    line_group_ids.extend(lg_refs)

            # --- Resolve members from all line groups (#23) ---
            member_ids: list[str] = []
            for lg_id in line_group_ids:
                member_refs = store.find_cross_refs(lg_id, "line_group_has_members")
                member_ids.extend(member_refs)

            # Resolve DN references to canonical user/workspace IDs
            # (Fix 1: DN agents → canonical user IDs via device chain)
            unique_members = _resolve_agents_from_dns(store, member_ids)

            # --- Load first line group state for algorithm + rna fields ---
            first_lg_state: dict[str, Any] = {}
            if line_group_ids:
                first_lg_data = store.get_object(line_group_ids[0])
                if first_lg_data:
                    first_lg_state = first_lg_data.get("pre_migration_state") or {}

            # --- Classify hunt pilot ---
            classification, policy = self._classify_hunt_pilot(
                hp_state, hunt_list_state, first_lg_state
            )

            # --- Phase A: voicemail-on-overflow gap detection ---
            # If the hunt list forwards to voicemail but we have no matching
            # voicemail_group object in the store, the shared mailbox was
            # not extracted from Unity Connection. Surface this as a
            # MISSING_DATA decision so the assessment report flags it.
            # (from docs/superpowers/specs/2026-04-10-voicemail-groups.md Phase A)
            vm_usage = hunt_list_state.get("voice_mail_usage", "NONE")
            if vm_usage and vm_usage != "NONE":
                hl_name = hunt_list_state.get("hunt_list_name") or ""
                # Use the already-resolved cross-ref canonical_id instead of
                # recomputing it from the hunt_list_name string — avoids silent
                # breakage if the canonical_id format ever changes.
                hl_id = hunt_list_refs[0] if hunt_list_refs else ""
                if not has_vm_group:
                    gap_decision = self._create_decision(
                        store=store,
                        decision_type=DecisionType.MISSING_DATA,
                        severity="MEDIUM",
                        summary=(
                            f"Hunt list '{hl_name}' forwards unanswered/overflow "
                            f"calls to a shared voicemail mailbox "
                            f"({vm_usage}) — the mailbox configuration was "
                            f"not extracted from Unity Connection and will "
                            f"not be migrated automatically"
                        ),
                        context={
                            "hunt_list_id": hl_id,
                            "hunt_pilot_id": hp_id,
                            "voice_mail_usage": vm_usage,
                            "reason": "shared_voicemail_not_extracted",
                        },
                        options=[
                            accept_option(
                                "Accept loss — rebuild voicemail group manually "
                                "in Webex post-migration"
                            ),
                            manual_option(
                                "Provide Unity Connection credentials and "
                                "re-run discovery to extract shared mailboxes"
                            ),
                        ],
                        affected_objects=[hp_id] + ([hl_id] if hl_id else []),
                    )
                    store.save_decision(decision_to_store_dict(gap_decision))
                    result.decisions.append(gap_decision)

            # --- Extract common fields ---
            name = (
                hp_state.get("name")
                or hp_state.get("description")
                or hp_state.get("pattern")
                or hp_id.split(":", 1)[-1]
            )
            extension = hp_state.get("extension") or hp_state.get("pattern")
            phone_number = hp_state.get("phone_number")

            # --- Ring no-answer ---
            # rnaReversionTimeOut is on LineGroup, not HuntPilot
            # (from 02b-cucm-extraction.md §2.5: rnaReversionTimeOut on LineGroup)
            rna_timeout = first_lg_state.get("rnaReversionTimeOut")
            if rna_timeout is None:
                # Fallback: check other line groups
                for lg_id in line_group_ids:
                    lg_data = store.get_object(lg_id)
                    if lg_data:
                        lg_state = lg_data.get("pre_migration_state") or {}
                        rna_timeout = lg_state.get("rnaReversionTimeOut")
                        if rna_timeout is not None:
                            break

            no_answer_rings = None
            if rna_timeout is not None:
                try:
                    no_answer_rings = max(1, int(rna_timeout) // 6)
                except (ValueError, TypeError):
                    pass

            # --- Check agent limits ---
            agent_limit = _AGENT_LIMITS.get(policy, 1000)
            if len(unique_members) > agent_limit:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity="HIGH",
                    summary=(
                        f"Hunt pilot '{name}' has {len(unique_members)} agents "
                        f"but {policy} policy allows max {agent_limit}"
                    ),
                    context={
                        "hunt_pilot_id": hp_id,
                        "name": name,
                        "policy": policy,
                        "agent_count": len(unique_members),
                        "agent_limit": agent_limit,
                        "reason": "agent_limit_exceeded",
                    },
                    options=[
                        accept_option(
                            f"Truncate to first {agent_limit} agents"
                        ),
                        manual_option(
                            "Admin splits into multiple groups manually"
                        ),
                        skip_option("Feature not migrated"),
                    ],
                    affected_objects=[hp_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            provenance = extract_provenance(hp_data)

            # Fix 3: Resolve feature location from agents
            location_id = _resolve_feature_location(
                store, unique_members, hp_data.get("provenance")
            )

            if classification == "CALL_QUEUE":
                # --- Produce CanonicalCallQueue ---
                # maxCallersInQueue is nested in queueCalls (XCallsQueue)
                # (from 02b-cucm-extraction.md §6: queueCalls complex type)
                queue_calls = hp_state.get("queueCalls") or {}
                queue_size = queue_calls.get("maxCallersInQueue") or 25
                try:
                    queue_size = int(queue_size)
                except (ValueError, TypeError):
                    queue_size = 25

                feature_cid = f"call_queue:{hash_id(hp_id)}"
                cq = CanonicalCallQueue(
                    canonical_id=feature_cid,
                    provenance=provenance,
                    status=MigrationStatus.ANALYZED,
                    name=name,
                    extension=extension,
                    phone_number=phone_number,
                    policy=policy,
                    routing_type="PRIORITY_BASED",
                    agents=unique_members,
                    queue_size=queue_size,
                    enabled=hp_state.get("enabled", True),
                    location_id=location_id,
                )
                store.upsert_object(cq)
                result.objects_created += 1

                # Fix 8: Write feature_has_agent cross-refs
                for agent_cid in unique_members:
                    store.add_cross_ref(feature_cid, agent_cid, "feature_has_agent")

            else:
                # --- Produce CanonicalHuntGroup ---
                feature_cid = f"hunt_group:{hash_id(hp_id)}"
                hg = CanonicalHuntGroup(
                    canonical_id=feature_cid,
                    provenance=provenance,
                    status=MigrationStatus.ANALYZED,
                    name=name,
                    extension=extension,
                    phone_number=phone_number,
                    policy=policy,
                    agents=unique_members,
                    no_answer_rings=no_answer_rings,
                    enabled=hp_state.get("enabled", True),
                    location_id=location_id,
                )
                store.upsert_object(hg)
                result.objects_created += 1

                # Fix 8: Write feature_has_agent cross-refs
                for agent_cid in unique_members:
                    store.add_cross_ref(feature_cid, agent_cid, "feature_has_agent")

            # --- MISSING_DATA if no extension ---
            if not extension:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="HIGH",
                    summary=(
                        f"Hunt pilot '{name}' has no resolvable extension"
                    ),
                    context={
                        "hunt_pilot_id": hp_id,
                        "name": name,
                        "reason": "no_extension",
                    },
                    options=[
                        manual_option("Admin provides extension"),
                        skip_option("Feature not migrated"),
                    ],
                    affected_objects=[hp_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

    def _classify_hunt_pilot(
        self,
        hp_state: dict[str, Any],
        hunt_list_state: dict[str, Any],
        line_group_state: dict[str, Any],
    ) -> tuple[str, str]:
        """Determine Webex object type and policy for a CUCM hunt pilot.

        Returns: (classification, policy) where classification is
        'HUNT_GROUP' or 'CALL_QUEUE', and policy is the Webex callPolicies.policy value.

        (from 03b-transform-mappers.md §10: classify_hunt_pilot algorithm)
        """
        # Step 1: isCtiRp check is handled separately in _map_cti_route_points
        # This method only handles actual hunt pilots.

        # Step 2: Check for queue-style indicators
        # All queue fields are nested in queueCalls (XCallsQueue) on HuntPilot.
        # queueCalls is None when queuing is disabled.
        # voiceMailUsage is on HuntList (from 02b-cucm-extraction.md §6).
        # (from 02b-cucm-extraction.md §6: queueCalls is complex type XCallsQueue)
        queue_calls = hp_state.get("queueCalls") or {}
        has_queue_features = any([
            queue_calls.get("enabled", False),
            (queue_calls.get("maxCallersInQueue") or 0) > 0,
            queue_calls.get("networkHoldMohAudioSourceID") is not None,
            queue_calls.get("queueFullDestination") is not None
            or queue_calls.get("maxWaitTimeDestination") is not None
            or queue_calls.get("noAgentDestination") is not None,
            hunt_list_state.get("voiceMailUsage", "NONE") != "NONE",
        ])

        # Step 3: Map distribution algorithm to Webex policy
        # distributionAlgorithm is on LineGroup, not HuntList
        # (from 02b-cucm-extraction.md §2.5: distributionAlgorithm on LineGroup)
        algorithm = line_group_state.get("distributionAlgorithm", "")
        policy = _ALGORITHM_TO_POLICY.get(algorithm, "CIRCULAR")

        if has_queue_features:
            return "CALL_QUEUE", policy
        return "HUNT_GROUP", policy

    # ------------------------------------------------------------------
    # CTI Route Points -> Auto Attendant
    # (from 03b-transform-mappers.md §8: AA field mapping)
    # ------------------------------------------------------------------

    def _map_cti_route_points(
        self, store: MigrationStore, result: MapperResult
    ) -> None:
        """Map CTI Route Points to CanonicalAutoAttendant objects.

        Always produces a FEATURE_APPROXIMATION decision because IVR scripts
        can't be fully parsed into simple AA menu keys.

        (from 03b-transform-mappers.md §8: CTI RP -> AA mapping)
        """
        for cti_data in store.get_objects("cti_rp"):
            cti_id = cti_data["canonical_id"]
            cti_state = cti_data.get("pre_migration_state") or {}

            name = (
                cti_state.get("name")
                or cti_state.get("description")
                or cti_id.split(":", 1)[-1]
            )
            extension = cti_state.get("extension") or cti_state.get("pattern")

            # --- Check for script reference (#24) ---
            script_refs = store.find_cross_refs(cti_id, "cti_rp_has_script")
            has_script = bool(script_refs)

            # --- Resolve schedule via CSS → partition → timeScheduleIdName ---
            # CTI RP has NO schedule field. Time-based routing uses partition
            # timeScheduleIdName. Resolve: CTI RP callingSearchSpaceName → CSS →
            # partitions → partition's timeScheduleIdName → schedule
            # (from 02b-cucm-extraction.md §2.5: CTI RP has no schedule field)
            business_schedule = None
            css_name = cti_state.get("callingSearchSpaceName")
            if css_name:
                css_id = f"css:{css_name}"
                partition_refs = store.get_cross_refs(
                    from_id=css_id, relationship="css_contains_partition"
                )
                for pt_ref in sorted(partition_refs, key=lambda r: r.get("ordinal") or 0):
                    pt_data = store.get_object(pt_ref["to_id"])
                    if pt_data:
                        pt_state = pt_data.get("pre_migration_state") or {}
                        sched_name = pt_state.get("timeScheduleIdName")
                        if sched_name:
                            business_schedule = sched_name
                            break

            # --- Default AA menus ---
            # (from 03b-transform-mappers.md §8: "AA requires both menus")
            business_hours_menu = {
                "greeting": "DEFAULT",
                "extensionEnabled": True,
                "keyConfigurations": [
                    {"key": "0", "action": "TRANSFER_TO_OPERATOR", "value": "0"},
                ],
            }
            after_hours_menu = {
                "greeting": "DEFAULT",
                "extensionEnabled": True,
                "keyConfigurations": [
                    {"key": "0", "action": "TRANSFER_TO_OPERATOR", "value": "0"},
                ],
            }

            aa = CanonicalAutoAttendant(
                canonical_id=f"auto_attendant:{hash_id(cti_id)}",
                provenance=extract_provenance(cti_data),
                status=MigrationStatus.ANALYZED,
                name=name,
                extension=extension,
                business_schedule=business_schedule,
                business_hours_menu=business_hours_menu,
                after_hours_menu=after_hours_menu,
            )
            store.upsert_object(aa)
            result.objects_created += 1

            # --- FEATURE_APPROXIMATION decision ---
            # (from 03b-transform-mappers.md §8: CTI RP always gets this decision)
            script_detail = "with script reference" if has_script else "without script"
            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.FEATURE_APPROXIMATION,
                severity="HIGH",
                summary=(
                    f"CTI Route Point '{name}' ({script_detail}) mapped to basic "
                    f"Auto Attendant — IVR logic requires manual configuration"
                ),
                context={
                    "cti_rp_id": cti_id,
                    "name": name,
                    "classification": "AUTO_ATTENDANT",
                    "complex_script": has_script,
                    "has_script": has_script,
                    "reason": "cti_rp_to_auto_attendant",
                },
                options=[
                    accept_option(
                        "Create basic AA with default menus; configure manually"
                    ),
                    skip_option("Skip — handle AA creation manually post-migration"),
                    manual_option(
                        "Map to HG/CQ if routing is simple enough"
                    ),
                ],
                affected_objects=[cti_id],
            )
            store.save_decision(decision_to_store_dict(decision))
            result.decisions.append(decision)

    # ------------------------------------------------------------------
    # Call Park: CUCM Call Park Number -> CanonicalCallPark
    # (from 03b-transform-mappers.md §8: simple features)
    # ------------------------------------------------------------------

    def _map_call_parks(self, store: MigrationStore, result: MapperResult) -> None:
        """Map CUCM Call Park numbers to CanonicalCallPark objects."""
        for cp_data in store.get_objects("call_park"):
            cp_id = cp_data["canonical_id"]
            cp_state = cp_data.get("pre_migration_state") or {}

            name = (
                cp_state.get("name")
                or cp_state.get("description")
                or cp_id.split(":", 1)[-1]
            )
            extension = cp_state.get("extension") or cp_state.get("pattern")
            location_id = cp_state.get("location_id")

            cp = CanonicalCallPark(
                canonical_id=f"call_park_ext:{hash_id(cp_id)}",
                provenance=extract_provenance(cp_data),
                status=MigrationStatus.ANALYZED,
                name=name,
                extension=extension,
                location_id=location_id,
            )
            store.upsert_object(cp)
            result.objects_created += 1

    # ------------------------------------------------------------------
    # Pickup Group: CUCM Pickup Group -> CanonicalPickupGroup
    # ------------------------------------------------------------------

    def _map_pickup_groups(self, store: MigrationStore, result: MapperResult) -> None:
        """Map CUCM Pickup Groups to CanonicalPickupGroup objects."""
        for pg_data in store.get_objects("pickup_group"):
            pg_id = pg_data["canonical_id"]
            pg_state = pg_data.get("pre_migration_state") or {}

            name = (
                pg_state.get("name")
                or pg_state.get("description")
                or pg_id.split(":", 1)[-1]
            )
            members = pg_state.get("members") or []
            # Defensive: extract UUID strings if members are still dicts
            # (normalizer should have cleaned these, but handle pre-existing data)
            raw_member_ids = _extract_agent_ids(members)

            # Fix 2: Resolve CUCM UUID/DN refs to canonical user IDs.
            # The normalizer stores member UUIDs which may correspond to DNs.
            # Try to find DN objects by matching CUCM UUID in the store, then
            # resolve DN→user via the same device chain as hunt groups.
            agents = _resolve_pickup_members_to_owners(store, raw_member_ids)

            # Fix 3: Resolve feature location from agents
            location_id = _resolve_feature_location(
                store, agents, pg_data.get("provenance")
            )

            feature_cid = f"pickup_group:{hash_id(pg_id)}"
            pg = CanonicalPickupGroup(
                canonical_id=feature_cid,
                provenance=extract_provenance(pg_data),
                status=MigrationStatus.ANALYZED,
                name=name,
                agents=agents,
                location_id=location_id,
            )
            store.upsert_object(pg)
            result.objects_created += 1

            # Fix 8: Write feature_has_agent cross-refs
            for agent_cid in agents:
                store.add_cross_ref(feature_cid, agent_cid, "feature_has_agent")

    # ------------------------------------------------------------------
    # Paging Group
    # ------------------------------------------------------------------

    def _map_paging_groups(self, store: MigrationStore, result: MapperResult) -> None:
        """Map CUCM paging groups to CanonicalPagingGroup objects.

        Webex paging groups support up to 75 targets. If CUCM exceeds this,
        the mapper splits into multiple groups.
        (from 03b-transform-mappers.md §8: "Paging Group members" edge case)
        """
        for pag_data in store.get_objects("paging_group"):
            pag_id = pag_data["canonical_id"]
            pag_state = pag_data.get("pre_migration_state") or {}

            name = (
                pag_state.get("name")
                or pag_state.get("description")
                or pag_id.split(":", 1)[-1]
            )
            extension = pag_state.get("extension")
            targets = pag_state.get("targets") or []
            originators = pag_state.get("originators") or []

            if len(targets) <= _MAX_PAGING_TARGETS:
                pg = CanonicalPagingGroup(
                    canonical_id=f"paging_group:{hash_id(pag_id)}",
                    provenance=extract_provenance(pag_data),
                    status=MigrationStatus.ANALYZED,
                    name=name,
                    extension=extension,
                    targets=targets,
                    originators=originators,
                )
                store.upsert_object(pg)
                result.objects_created += 1
            else:
                # Split targets into chunks of 75
                for chunk_idx, start in enumerate(
                    range(0, len(targets), _MAX_PAGING_TARGETS)
                ):
                    chunk = targets[start:start + _MAX_PAGING_TARGETS]
                    split_name = f"{name}-{chunk_idx + 1}"
                    pg = CanonicalPagingGroup(
                        canonical_id=f"paging_group:{hash_id(f'{pag_id}-{chunk_idx}')}",
                        provenance=extract_provenance(pag_data),
                        status=MigrationStatus.ANALYZED,
                        name=split_name,
                        extension=extension if chunk_idx == 0 else None,
                        targets=chunk,
                        originators=originators,
                    )
                    store.upsert_object(pg)
                    result.objects_created += 1

    # ------------------------------------------------------------------
    # Schedules: Time Schedule + Time Period -> CanonicalOperatingMode
    # (from 03b-transform-mappers.md §8: schedule -> OperatingMode)
    # ------------------------------------------------------------------

    def _map_schedules(self, store: MigrationStore, result: MapperResult) -> None:
        """Map CUCM Time Schedules (with Time Periods) to CanonicalOperatingMode.

        Reads schedule_has_time_period cross-ref (#25) to join schedules with
        their time period entries.

        (from 03b-transform-mappers.md §8: OperatingMode field mapping)
        """
        for sched_data in store.get_objects("time_schedule"):
            sched_id = sched_data["canonical_id"]
            sched_state = sched_data.get("pre_migration_state") or {}

            name = (
                sched_state.get("name")
                or sched_state.get("description")
                or sched_id.split(":", 1)[-1]
            )

            # --- Resolve time periods via cross-ref (#25) ---
            period_refs = store.find_cross_refs(sched_id, "schedule_has_time_period")
            time_periods: list[dict[str, Any]] = []
            for tp_ref in period_refs:
                tp_data = store.get_object(tp_ref)
                if tp_data:
                    tp_state = tp_data.get("pre_migration_state") or {}
                    time_periods.append(tp_state)

            # --- Determine schedule type ---
            # Heuristic: if any period has a specific date -> HOLIDAY
            # if all periods have same start/end -> SAME_HOURS_DAILY
            # otherwise DIFFERENT_HOURS_DAILY
            schedule_type = sched_state.get("schedule_type")
            if not schedule_type:
                schedule_type = _infer_schedule_type(time_periods)

            # --- Build schedule data based on type ---
            same_hours_daily = None
            different_hours_daily = None
            holidays: list[dict[str, Any]] = []

            if schedule_type == "HOLIDAY":
                holidays = [
                    {
                        "name": tp.get("name", "Holiday"),
                        "date": tp.get("date"),
                        "recurrence": tp.get("recurrence"),
                    }
                    for tp in time_periods
                ]
            elif schedule_type == "SAME_HOURS_DAILY" and time_periods:
                # Use first period's hours for all days
                tp = time_periods[0]
                same_hours_daily = {
                    "startTime": tp.get("start_time"),
                    "endTime": tp.get("end_time"),
                }
            elif schedule_type == "DIFFERENT_HOURS_DAILY" and time_periods:
                different_hours_daily = {
                    (tp.get("day_of_week") or f"day_{i}"): {
                        "startTime": tp.get("start_time"),
                        "endTime": tp.get("end_time"),
                    }
                    for i, tp in enumerate(time_periods)
                }

            om = CanonicalOperatingMode(
                canonical_id=f"operating_mode:{hash_id(sched_id)}",
                provenance=extract_provenance(sched_data),
                status=MigrationStatus.ANALYZED,
                name=name,
                level="ORGANIZATION",
                schedule_type=schedule_type,
                same_hours_daily=same_hours_daily,
                different_hours_daily=different_hours_daily,
                holidays=holidays,
            )
            store.upsert_object(om)
            result.objects_created += 1

    # ------------------------------------------------------------------
    # Location Schedules: create for schedules referenced by AAs
    # (from fix-schedule-mapping-and-skill-gaps.md Fix 2)
    # ------------------------------------------------------------------

    def _map_location_schedules(
        self, store: MigrationStore, result: MapperResult
    ) -> None:
        """Create CanonicalLocationSchedule for schedules referenced by AAs.

        AAs need location schedules (not operating modes) for businessSchedule.
        This second pass finds AA-referenced schedules and creates corresponding
        location schedule objects.
        """
        # Collect schedule names referenced by auto attendants
        # schedule_name -> (location_id, [aa_canonical_ids])
        aa_schedule_refs: dict[str, tuple[str, list[str]]] = {}
        for aa_data in store.get_objects("auto_attendant"):
            aa_state = aa_data.get("pre_migration_state") or {}
            sched = (
                aa_data.get("business_schedule")
                or aa_state.get("business_schedule")
            )
            if not sched:
                continue
            loc_id = aa_data.get("location_id")
            if sched in aa_schedule_refs:
                aa_schedule_refs[sched][1].append(aa_data["canonical_id"])
            elif loc_id:
                aa_schedule_refs[sched] = (loc_id, [aa_data["canonical_id"]])

        if not aa_schedule_refs:
            return

        # For each operating mode, check if it's referenced by an AA
        for om_data in store.get_objects("operating_mode"):
            om_name = om_data.get("name")
            if om_name not in aa_schedule_refs:
                continue

            location_id, aa_cids = aa_schedule_refs[om_name]
            om_cid = om_data["canonical_id"]
            sched_type = _om_type_to_schedule_type(om_data.get("schedule_type"))
            events = _build_schedule_events(om_data)

            sched = CanonicalLocationSchedule(
                canonical_id=f"schedule:{hash_id(om_cid)}",
                provenance=extract_provenance(om_data),
                status=MigrationStatus.ANALYZED,
                name=om_name,
                schedule_type=sched_type,
                location_id=location_id,
                events=events,
                operating_mode_canonical_id=om_cid,
            )
            store.upsert_object(sched)
            result.objects_created += 1

            # Write aa_has_schedule cross-ref (Fix 3a)
            for aa_cid in aa_cids:
                store.add_cross_ref(aa_cid, sched.canonical_id, "aa_has_schedule")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _om_type_to_schedule_type(om_type: str | None) -> str:
    """Map operating mode schedule_type to location schedule type."""
    if om_type == "HOLIDAY":
        return "holidays"
    return "businessHours"


def _build_schedule_events(om_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert operating mode time data to location schedule event format.

    Location schedule API requires recurWeekly recurrence (NOT recurForEver).
    """
    schedule_type = om_data.get("schedule_type")
    events: list[dict[str, Any]] = []

    if schedule_type == "HOLIDAY":
        for holiday in om_data.get("holidays") or []:
            date = holiday.get("date", "2026-01-01")
            events.append({
                "name": holiday.get("name", "Holiday"),
                "startDate": date,
                "endDate": date,
                "startTime": "00:00",
                "endTime": "23:59",
                "allDayEnabled": True,
            })
    elif schedule_type == "SAME_HOURS_DAILY":
        hours = om_data.get("same_hours_daily") or {}
        start = hours.get("startTime", "08:00")
        end = hours.get("endTime", "17:00")
        events.append({
            "name": om_data.get("name", "Business Hours"),
            "startDate": "2026-01-01",
            "endDate": "2030-12-31",
            "startTime": start,
            "endTime": end,
            "recurrence": {
                "recurWeekly": {
                    "sunday": False,
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                    "saturday": False,
                }
            },
        })
    elif schedule_type == "DIFFERENT_HOURS_DAILY":
        day_data = om_data.get("different_hours_daily") or {}
        day_map = {
            "monday": "Monday",
            "tuesday": "Tuesday",
            "wednesday": "Wednesday",
            "thursday": "Thursday",
            "friday": "Friday",
            "saturday": "Saturday",
            "sunday": "Sunday",
        }
        for day_key, day_label in day_map.items():
            day_hours = day_data.get(day_key)
            if not day_hours:
                continue
            recurrence_days = {d: (d == day_key) for d in day_map}
            events.append({
                "name": f"{om_data.get('name', 'Hours')} - {day_label}",
                "startDate": "2026-01-01",
                "endDate": "2030-12-31",
                "startTime": day_hours.get("startTime", "08:00"),
                "endTime": day_hours.get("endTime", "17:00"),
                "recurrence": {"recurWeekly": recurrence_days},
            })
    else:
        # Fallback: all-the-time schedule
        events.append({
            "name": om_data.get("name", "All the time"),
            "startDate": "2026-01-01",
            "endDate": "2030-12-31",
            "startTime": "00:00",
            "endTime": "23:59",
            "recurrence": {
                "recurWeekly": {
                    "sunday": True,
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                    "saturday": True,
                }
            },
        })

    return events


def _infer_schedule_type(time_periods: list[dict[str, Any]]) -> str:
    """Infer Webex OperatingMode schedule type from CUCM time periods.

    Returns one of: SAME_HOURS_DAILY, DIFFERENT_HOURS_DAILY, HOLIDAY
    """
    if not time_periods:
        return "SAME_HOURS_DAILY"

    # Check for holiday indicators
    if any(tp.get("date") or tp.get("is_holiday") for tp in time_periods):
        return "HOLIDAY"

    # Check if all periods have the same start/end time
    times = {(tp.get("start_time"), tp.get("end_time")) for tp in time_periods}
    if len(times) == 1:
        return "SAME_HOURS_DAILY"

    return "DIFFERENT_HOURS_DAILY"


def _build_line_uuid_to_dn(store: MigrationStore) -> dict[str, str]:
    """Build a lookup from CUCM line-level UUIDs to DN canonical IDs.

    Raw phone objects (stored as phone:{name}) contain per-line dirn dicts
    with uuid, pattern, and routePartitionName.  Pickup group members reference
    lines by these UUIDs.  This builds the mapping so UUIDs can resolve to
    dn:{pattern}:{partition} canonical IDs.
    """
    uuid_to_dn: dict[str, str] = {}
    for phone_data in store.get_objects("phone"):
        state = phone_data.get("pre_migration_state") or {}
        lines = state.get("lines") or {}
        line_list = lines if isinstance(lines, list) else lines.get("line", [])
        if isinstance(line_list, dict):
            line_list = [line_list]
        if not isinstance(line_list, list):
            continue
        for line_entry in line_list:
            if not isinstance(line_entry, dict):
                continue
            dirn = line_entry.get("dirn")
            if not isinstance(dirn, dict):
                continue
            uuid = dirn.get("uuid")
            pattern = dirn.get("pattern")
            if not uuid or not pattern:
                continue
            # Extract partition from routePartitionName (zeep ref or string)
            rp = dirn.get("routePartitionName")
            if isinstance(rp, dict):
                partition = rp.get("_value_1") or "<None>"
            elif isinstance(rp, str):
                partition = rp or "<None>"
            else:
                partition = "<None>"
            dn_id = f"dn:{pattern}:{partition}"
            uuid_to_dn[str(uuid)] = dn_id
    return uuid_to_dn


def _resolve_pickup_members_to_owners(
    store: MigrationStore, member_ids: list[str]
) -> list[str]:
    """Resolve pickup group member IDs (CUCM UUIDs) to canonical user/workspace IDs.

    Pickup group members may be:
    - Already canonical IDs (e.g., user:alice) — pass through directly
    - DN canonical IDs (e.g., dn:1002:PT-Internal) — resolve via device chain
    - CUCM UUIDs (e.g., {5782CE0C-...}) — resolve via raw phone line data
    Falls back to the raw member_id if resolution fails.
    """
    # Build one-time lookup: line-level UUID → DN canonical_id from raw phone data
    uuid_to_dn: dict[str, str] | None = None

    seen: set[str] = set()
    resolved: list[str] = []

    for member_id in member_ids:
        owner = None

        if member_id.startswith("user:") or member_id.startswith("workspace:"):
            # Already a canonical user/workspace ID — use directly
            owner = member_id
        elif member_id.startswith("dn:"):
            # DN canonical_id — resolve via device chain
            owner = _resolve_dn_to_owner(store, member_id)
        else:
            # CUCM UUID — resolve via raw phone line data
            if uuid_to_dn is None:
                uuid_to_dn = _build_line_uuid_to_dn(store)

            dn_cid = uuid_to_dn.get(member_id)
            if dn_cid:
                owner = _resolve_dn_to_owner(store, dn_cid)

        agent_id = owner if owner else member_id
        if agent_id not in seen:
            seen.add(agent_id)
            resolved.append(agent_id)

    return resolved


def _extract_agent_ids(members: list) -> list[str]:
    """Extract string IDs from a member list that may contain raw CUCM dicts.

    If members are already strings, they pass through unchanged.  If they are
    dicts (e.g. from pre-existing store data not re-normalized), extract the
    UUID from nested zeep reference fields.
    """
    result: list[str] = []
    for member in members:
        if isinstance(member, str):
            result.append(member)
        elif isinstance(member, dict):
            # Look for UUID in nested reference fields
            uuid_val = None
            for key, val in member.items():
                if key == "priority":
                    continue
                if isinstance(val, dict) and "uuid" in val and val["uuid"] is not None:
                    uuid_val = str(val["uuid"])
                    break
                if isinstance(val, str) and (val.startswith("{") or len(val) == 36):
                    uuid_val = val
                    break
            if uuid_val is None and "uuid" in member:
                uuid_val = str(member["uuid"]) if member["uuid"] is not None else None
            if uuid_val:
                result.append(uuid_val)
            else:
                logger.warning("Could not extract UUID from pickup group member: %s", member)
    return result


