"""Device compatibility analyzer — finds incompatible devices.

Mapper-owned decision type: device_mapper may already produce DEVICE_INCOMPATIBLE
decisions. This analyzer backfills any devices the mapper missed (e.g., devices
added after initial mapping).

Convertible devices are NOT surfaced as decisions. Convertibility is a phone
model classification (``compatibility_tier == 'convertible'``), not an operator
choice — the planner unconditionally emits an activation-code op for those.

(from 03-conflict-detection-engine.md, device compatibility linter)
(from phase-06-analyzers.md, Decision Ownership Table — mapper-owned)
"""

from __future__ import annotations

from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


class DeviceCompatibilityAnalyzer(Analyzer):
    """Detects devices that are incompatible with Webex Calling.

    Sweeps all device objects and checks ``compatibility_tier``:
    - ``incompatible`` -> DEVICE_INCOMPATIBLE decision
    - ``convertible``  -> no decision (planner emits conversion op unconditionally)
    - ``native_mpp``   -> no decision needed

    Skips devices that already have a mapper-produced decision for the same type.
    """

    name = "device_compatibility"
    decision_types = [DecisionType.DEVICE_INCOMPATIBLE]
    depends_on: list[str] = []

    def analyze(self, store: MigrationStore) -> list[Decision]:
        decisions: list[Decision] = []

        # Get existing mapper-produced decisions indexed by affected object canonical_id
        existing_incompatible = self._get_existing_decisions_for_type(
            store, DecisionType.DEVICE_INCOMPATIBLE
        )

        devices = store.get_objects("device")

        for device in devices:
            canonical_id = device.get("canonical_id", "")
            tier = device.get("compatibility_tier")

            if tier in ("webex_app", "infrastructure", "dect", "convertible"):
                # Software phones transition to Webex App; infrastructure devices
                # (CTI, CER, gateways) are CUCM-only; DECT is handled via DECT network
                # provisioning; convertible devices always convert (no operator choice).
                continue

            elif tier == "incompatible":
                # Skip if mapper already produced this decision for this device
                if canonical_id in existing_incompatible:
                    continue
                decisions.append(self._build_incompatible_decision(store, device))

            # native_mpp and None — no decision needed

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        return self._hash_fingerprint({
            "canonical_id": context.get("canonical_id", ""),
            "model": context.get("model", ""),
            "compatibility_tier": context.get("compatibility_tier", ""),
        })

    # ------------------------------------------------------------------
    # Decision builders
    # ------------------------------------------------------------------

    def _build_incompatible_decision(
        self, store: MigrationStore, device: dict[str, Any]
    ) -> Decision:
        canonical_id = device.get("canonical_id", "")
        model = device.get("model", "unknown")
        mac = device.get("mac", "")
        cucm_device_name = device.get("cucm_device_name", "")
        owner_canonical_id = device.get("owner_canonical_id", "")

        context = {
            "canonical_id": canonical_id,
            "model": model,
            "mac": mac,
            "cucm_device_name": cucm_device_name,
            "owner_canonical_id": owner_canonical_id,
            "compatibility_tier": "incompatible",
        }
        options = [
            DecisionOption(
                id="skip",
                label="Skip device",
                impact=f"Device {model} ({cucm_device_name}) will not be migrated",
            ),
            DecisionOption(
                id="manual",
                label="Handle manually",
                impact=f"Device {model} ({cucm_device_name}) flagged for manual replacement",
            ),
        ]
        affected = [canonical_id]
        if owner_canonical_id:
            affected.append(owner_canonical_id)

        return self._create_decision(
            store=store,
            decision_type=DecisionType.DEVICE_INCOMPATIBLE,
            severity="MEDIUM",
            summary=f"Device {model} ({cucm_device_name}) is incompatible with Webex Calling",
            context=context,
            options=options,
            affected_objects=affected,
        )

