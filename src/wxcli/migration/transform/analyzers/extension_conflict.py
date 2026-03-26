"""Extension conflict analyzer — finds DNs sharing the same extension within a location.

Detects lines that would collide in Webex Calling because they share the same
extension number within the same location.  CUCM allows this via partitions,
but Webex Calling enforces unique extensions per location.

Decision ownership: ANALYZER-OWNED (no mapper produces EXTENSION_CONFLICT).

(from 03-conflict-detection-engine.md, extension conflict detection)
(from 07-idempotency-resumability.md, fingerprint-based identity)
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


class ExtensionConflictAnalyzer(Analyzer):
    """Finds extension conflicts within the same Webex Calling location.

    CUCM allows multiple DNs with the same pattern in different partitions.
    Webex Calling requires unique extensions per location.  This analyzer
    groups lines by (extension, location) and flags collisions.

    Location resolution: line → device (via device_has_dn cross-ref) →
    device.location_canonical_id.
    """

    name = "extension_conflict"
    decision_types = [DecisionType.EXTENSION_CONFLICT]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep all lines, group by (extension, location), flag conflicts."""
        decisions: list[Decision] = []

        # Step 1: Load all lines and build a map of canonical_id → line data
        lines = store.get_objects("line")
        if not lines:
            return decisions

        line_by_id: dict[str, dict[str, Any]] = {}
        for line in lines:
            cid = line.get("canonical_id", "")
            if cid:
                line_by_id[cid] = line

        # Step 2: For each line, resolve its location via:
        #   line ←(device_has_dn)← device → device.location_canonical_id
        # Query cross_refs where relationship='device_has_dn' and to_id is a line
        line_location: dict[str, str] = {}  # line canonical_id → location canonical_id

        device_rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'device_has_dn'"
        ).fetchall()

        # Build line → device(s) mapping
        line_to_devices: dict[str, list[str]] = defaultdict(list)
        for row in device_rows:
            line_to_devices[row["to_id"]].append(row["from_id"])

        # Load all devices once for location lookups
        devices = store.get_objects("device")
        device_location: dict[str, str] = {}
        for dev in devices:
            dev_cid = dev.get("canonical_id", "")
            loc_cid = dev.get("location_canonical_id", "")
            if dev_cid and loc_cid:
                device_location[dev_cid] = loc_cid

        # Resolve each line's location via its owning device
        for line_cid in line_by_id:
            owning_devices = line_to_devices.get(line_cid, [])
            for dev_cid in owning_devices:
                loc = device_location.get(dev_cid)
                if loc:
                    line_location[line_cid] = loc
                    break  # use the first device that has a location

        # Step 3: Group lines by (extension, location)
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for line_cid, line_data in line_by_id.items():
            ext = line_data.get("extension")
            loc = line_location.get(line_cid)
            if ext and loc:
                groups[(ext, loc)].append(line_cid)

        # Step 4: Produce decisions for groups with 2+ lines
        for (ext, loc_cid), conflicting_ids in sorted(groups.items()):
            if len(conflicting_ids) < 2:
                continue

            severity = "HIGH" if len(conflicting_ids) >= 3 else "MEDIUM"

            # Build context with details about each conflicting line
            line_details = []
            for cid in sorted(conflicting_ids):
                ld = line_by_id.get(cid, {})
                line_details.append({
                    "canonical_id": cid,
                    "cucm_pattern": ld.get("cucm_pattern"),
                    "route_partition_name": ld.get("route_partition_name"),
                })

            context = {
                "extension": ext,
                "location_canonical_id": loc_cid,
                "conflict_count": len(conflicting_ids),
                "conflicting_lines": line_details,
            }

            options = [
                DecisionOption(
                    id="renumber",
                    label="Renumber Extension",
                    impact=f"Change extension for {len(conflicting_ids) - 1} of "
                           f"{len(conflicting_ids)} conflicting lines",
                ),
                DecisionOption(
                    id="virtual_line",
                    label="Use Virtual Line",
                    impact=f"Create virtual line(s) for {len(conflicting_ids) - 1} "
                           f"conflicting appearances",
                ),
                DecisionOption(
                    id="skip",
                    label="Skip",
                    impact=f"Leave {len(conflicting_ids)} lines unresolved — "
                           f"manual intervention required",
                ),
            ]

            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.EXTENSION_CONFLICT,
                severity=severity,
                summary=(
                    f"Extension {ext} used by {len(conflicting_ids)} lines "
                    f"in location {loc_cid}"
                ),
                context=context,
                options=options,
                affected_objects=sorted(conflicting_ids),
            )
            decisions.append(decision)

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from extension, location, and affected line IDs.

        Includes:
        - extension (the triggering condition)
        - location_canonical_id (scope of the conflict)
        - sorted canonical_ids of all conflicting lines (affected objects)

        (from 07-idempotency-resumability.md lines 30-43)
        """
        conflicting_ids = sorted(
            line.get("canonical_id", "")
            for line in context.get("conflicting_lines", [])
        )
        return self._hash_fingerprint({
            "type": decision_type.value,
            "extension": context.get("extension"),
            "location_canonical_id": context.get("location_canonical_id"),
            "conflicting_line_ids": conflicting_ids,
        })
