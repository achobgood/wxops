"""EcbnMapper — produce per-entity ECBN configuration for E911 execution.

Reads CanonicalUser and CanonicalWorkspace objects and classifies each
entity's ECBN eligibility. No new AXL queries — uses existing cross-refs
and canonical line data.

Classification logic (from 2026-04-10-e911-ecbn-execution.md §4.1):
  1. Entity has exactly one DID  -> DIRECT_LINE (auto-configured)
  2. Entity has multiple DIDs    -> E911_ECBN_AMBIGUOUS decision
  3. Entity has zero DIDs        -> LOCATION_ECBN (auto-configured)
  4. User location differs from device location -> E911_LOCATION_MISMATCH
"""

from __future__ import annotations

import logging

from wxcli.migration.models import (
    CanonicalEcbnConfig,
    DecisionOption,
    DecisionType,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    extract_provenance,
)

logger = logging.getLogger(__name__)


class EcbnMapper(Mapper):
    """Classify each user/workspace by ECBN eligibility.

    Depends on UserMapper, WorkspaceMapper, LocationMapper, LineMapper,
    DeviceMapper — must run after all entity mappers have populated the store.
    """

    name = "ecbn_mapper"
    depends_on = [
        "user_mapper",
        "workspace_mapper",
        "location_mapper",
        "line_mapper",
        "device_mapper",
    ]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        # Process users
        for user_data in store.get_objects("user"):
            status = user_data.get("status")
            if status in (MigrationStatus.SKIPPED.value, "skipped"):
                continue
            self._process_user(store, user_data, result)

        # Process workspaces
        for ws_data in store.get_objects("workspace"):
            status = ws_data.get("status")
            if status in (MigrationStatus.SKIPPED.value, "skipped"):
                continue
            self._process_workspace(store, ws_data, result)

        return result

    # ------------------------------------------------------------------
    # User processing
    # ------------------------------------------------------------------

    def _process_user(
        self,
        store: MigrationStore,
        user_data: dict,
        result: MapperResult,
    ) -> None:
        user_cid = user_data["canonical_id"]
        user_location = user_data.get("location_id")

        # Collect all DIDs (E.164 numbers) from devices -> DNs -> lines
        dids, device_locations = self._collect_user_dids(store, user_cid)
        primary_did = dids[0] if dids else None

        # Determine ECBN selection
        if len(dids) >= 1:
            selection = "DIRECT_LINE"
            needs_loc = False
        else:
            selection = "LOCATION_ECBN"
            needs_loc = True

        cfg = CanonicalEcbnConfig(
            canonical_id=f"ecbn_config:{user_cid}",
            provenance=extract_provenance(user_data),
            status=MigrationStatus.ANALYZED,
            entity_type="user",
            entity_canonical_id=user_cid,
            location_canonical_id=user_location,
            ecbn_selection=selection,
            did_numbers=dids,
            primary_did=primary_did,
            needs_location_ecbn=needs_loc,
        )
        store.upsert_object(cfg)
        result.objects_created += 1

        # Multi-DID → ambiguous decision
        if len(dids) >= 2:
            options = [
                DecisionOption(
                    id=f"did_{d}",
                    label=f"Use {d}",
                    impact=f"ECBN set to {d} (DIRECT_LINE)",
                )
                for d in dids
            ]
            options.append(DecisionOption(
                id="location_ecbn",
                label="Use location ECBN",
                impact="ECBN set to LOCATION_ECBN",
            ))
            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.E911_ECBN_AMBIGUOUS,
                severity="HIGH",
                summary=f"User {user_cid} has {len(dids)} DIDs — which is the ECBN?",
                context={
                    "user_canonical_id": user_cid,
                    "did_numbers": dids,
                    "primary_did": primary_did,
                    "user_location": user_location,
                },
                options=options,
                affected_objects=[cfg.canonical_id, user_cid],
            )
            result.decisions.append(decision)

        # Location mismatch detection
        if user_location and device_locations:
            distinct_device_locs = {loc for loc in device_locations if loc}
            if distinct_device_locs and user_location not in distinct_device_locs:
                dev_loc = next(iter(distinct_device_locs))
                options = [
                    DecisionOption(
                        id="use_user_location",
                        label=f"Use user's assigned location ({user_location})",
                        impact="ECBN resolves to user_location",
                    ),
                    DecisionOption(
                        id="use_device_location",
                        label=f"Use device's physical location ({dev_loc})",
                        impact="ECBN resolves to device_location",
                    ),
                    DecisionOption(
                        id="manual",
                        label="Operator must verify physical location",
                        impact="Requires manual verification",
                    ),
                ]
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.E911_LOCATION_MISMATCH,
                    severity="HIGH",
                    summary=f"User {user_cid} location differs from device location",
                    context={
                        "user_canonical_id": user_cid,
                        "user_location": user_location,
                        "device_location": dev_loc,
                    },
                    options=options,
                    affected_objects=[cfg.canonical_id, user_cid],
                )
                result.decisions.append(decision)

    def _collect_user_dids(
        self,
        store: MigrationStore,
        user_cid: str,
    ) -> tuple[list[str], list[str]]:
        """Walk user -> devices -> DNs -> lines to collect DID numbers.

        Returns (did_numbers, device_location_canonical_ids).
        Dedupes DIDs (same DID on multiple devices counts once).
        """
        dids: list[str] = []
        seen: set[str] = set()
        device_locations: list[str] = []

        device_cids = store.find_cross_refs(user_cid, "user_has_device")
        for dev_cid in device_cids:
            dev_data = store.get_object(dev_cid)
            if dev_data:
                dev_loc = dev_data.get("location_canonical_id")
                if dev_loc:
                    device_locations.append(dev_loc)

            dn_cids = store.find_cross_refs(dev_cid, "device_has_dn")
            for dn_cid in dn_cids:
                if not dn_cid.startswith("dn:"):
                    continue
                line_cid = "line:" + dn_cid[len("dn:"):]
                line = store.get_object(line_cid)
                if not line:
                    continue
                e164 = line.get("e164")
                if e164 and e164 not in seen:
                    dids.append(e164)
                    seen.add(e164)

        return dids, device_locations

    # ------------------------------------------------------------------
    # Workspace processing
    # ------------------------------------------------------------------

    def _process_workspace(
        self,
        store: MigrationStore,
        ws_data: dict,
        result: MapperResult,
    ) -> None:
        ws_cid = ws_data["canonical_id"]
        phone_number = ws_data.get("phone_number")
        location = ws_data.get("location_id")

        if phone_number:
            selection = "DIRECT_LINE"
            dids = [phone_number]
            primary = phone_number
            needs_loc = False
        else:
            selection = "LOCATION_ECBN"
            dids = []
            primary = None
            needs_loc = True

        cfg = CanonicalEcbnConfig(
            canonical_id=f"ecbn_config:{ws_cid}",
            provenance=extract_provenance(ws_data),
            status=MigrationStatus.ANALYZED,
            entity_type="workspace",
            entity_canonical_id=ws_cid,
            location_canonical_id=location,
            ecbn_selection=selection,
            did_numbers=dids,
            primary_did=primary,
            needs_location_ecbn=needs_loc,
        )
        store.upsert_object(cfg)
        result.objects_created += 1
