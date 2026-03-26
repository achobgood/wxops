"""Shared line analyzer — finds DNs shared across multiple device owners.

Detects directory numbers that appear on devices belonging to different users.
These shared-line appearances require a migration decision because Webex Calling
handles multi-user shared lines differently from CUCM (virtual lines, Webex
shared lines, or call park + BLF).

Decision ownership: ANALYZER-OWNED (no mapper produces SHARED_LINE_COMPLEX).

(from 03-conflict-detection-engine.md, shared line detection)
(from 07-idempotency-resumability.md, fingerprint-based identity)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


class SharedLineAnalyzer(Analyzer):
    """Finds DNs shared across multiple device owners.

    CUCM allows a single DN to appear on multiple devices owned by different
    users.  Webex Calling supports simple two-device shared lines natively,
    but more complex arrangements (3+ devices, multiple owners) require
    virtual lines, call park + BLF, or other workarounds.

    Detection: query cross_refs for device_has_dn relationships, group by DN,
    find DNs referenced by 2+ devices, then resolve unique owners.
    """

    name = "shared_lines"
    decision_types = [DecisionType.SHARED_LINE_COMPLEX]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep all device-to-DN cross-refs, find DNs with multiple device owners."""
        decisions: list[Decision] = []

        # Step 1: Find DNs referenced by multiple devices via raw SQL
        rows = store.conn.execute("""
            SELECT cr.to_id AS dn_id, COUNT(DISTINCT cr.from_id) AS device_count
            FROM cross_refs cr
            WHERE cr.relationship = 'device_has_dn'
            GROUP BY cr.to_id
            HAVING COUNT(DISTINCT cr.from_id) > 1
        """).fetchall()

        if not rows:
            return decisions

        # Step 2: For each shared DN, gather details and resolve owners
        for row in rows:
            dn_id: str = row["dn_id"]
            device_count: int = row["device_count"]

            # Get DN data
            dn_data = store.get_object(dn_id)
            if dn_data is None:
                continue

            extension = dn_data.get("extension")
            cucm_pattern = dn_data.get("cucm_pattern")
            route_partition_name = dn_data.get("route_partition_name")

            # Get all devices that reference this DN
            device_refs = store.conn.execute(
                "SELECT from_id FROM cross_refs WHERE to_id = ? AND relationship = 'device_has_dn'",
                (dn_id,),
            ).fetchall()
            device_ids = [r["from_id"] for r in device_refs]

            # Resolve unique owners from each device's data
            owner_set: set[str] = set()
            owner_ids: list[str] = []
            for dev_id in device_ids:
                dev_data = store.get_object(dev_id)
                if dev_data is not None:
                    owner = dev_data.get("owner_canonical_id")
                    if owner and owner not in owner_set:
                        owner_set.add(owner)
                        owner_ids.append(owner)

            # Only flag if there are multiple unique owners
            if len(owner_ids) < 2:
                continue

            unique_owners = len(owner_ids)
            severity = "HIGH" if unique_owners > 2 else "MEDIUM"

            # Build options
            dn_display = extension or cucm_pattern or dn_id

            options = [
                DecisionOption(
                    id="virtual_line",
                    label="Virtual Line",
                    impact=f"1 virtual line + {device_count} line assignments",
                ),
            ]

            if device_count <= 2:
                options.append(
                    DecisionOption(
                        id="shared_line",
                        label="Webex Shared Line",
                        impact="Simple shared line between 2 devices",
                    )
                )

            options.extend([
                DecisionOption(
                    id="call_park",
                    label="Call Park + BLF",
                    impact="Loses real-time shared state",
                ),
                DecisionOption(
                    id="skip",
                    label="Skip",
                    impact="DN migrated only on primary owner's device",
                ),
            ])

            context = {
                "dn": dn_display,
                "partition": route_partition_name,
                "device_count": device_count,
                "owner_ids": sorted(owner_ids),
                "dn_canonical_id": dn_id,
            }

            affected_objects = [dn_id] + sorted(device_ids)

            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.SHARED_LINE_COMPLEX,
                severity=severity,
                summary=(
                    f"DN {dn_display} shared across {device_count} devices "
                    f"with {unique_owners} unique owners"
                ),
                context=context,
                options=options,
                affected_objects=affected_objects,
            )
            decisions.append(decision)

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from DN, partition, owners, and device count.

        Includes:
        - dn (the shared extension or pattern)
        - partition (route partition — scope of the DN)
        - sorted owner_ids (all users who share this DN)
        - device_count (number of devices — change invalidates resolution)

        (from 07-idempotency-resumability.md lines 30-43)
        """
        return self._hash_fingerprint({
            "type": decision_type.value,
            "dn": context.get("dn"),
            "partition": context.get("partition"),
            "owner_ids": sorted(context.get("owner_ids", [])),
            "device_count": context.get("device_count"),
        })
