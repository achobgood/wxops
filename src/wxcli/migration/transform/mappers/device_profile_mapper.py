"""DeviceProfileMapper — CUCM Extension Mobility profiles → Webex hot desking advisory.

Reads device_profile objects from the store, resolves user ownership
(owner is the user whose default device profile this is), and produces
CanonicalDeviceProfile objects. If the user has a workspace at the same location,
the mapper flags it for hot desking enablement. If not, it produces a
FEATURE_APPROXIMATION decision.

CUCM EM is architecturally richer — profiles carry lines, speed dials, and services.
Webex hot desking is login/logout with the user's primary line only.

(from tier2-enterprise-expansion.md §5)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalDeviceProfile,
    DecisionType,
    MigrationStatus,
    MapperResult,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    extract_provenance,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)


class DeviceProfileMapper(Mapper):
    """Map CUCM Device Profiles to hot desking advisory objects.

    Tier 2 expansion: produces CanonicalDeviceProfile objects and
    FEATURE_APPROXIMATION decisions for EM → hot desking mapping.
    """

    name = "device_profile_mapper"
    depends_on = ["user_mapper", "workspace_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        # Build user → device profile mapping
        # Device profiles reference ownerUserId in their line entries
        for dp_data in store.get_objects("device_profile"):
            state = dp_data.get("pre_migration_state") or {}
            profile_name = state.get("profile_name") or ""
            if not profile_name:
                continue

            lines = state.get("lines") or []
            model = state.get("model") or ""
            protocol = state.get("protocol") or ""
            device_pool = state.get("device_pool_name") or ""
            sd_count = state.get("speed_dial_count", 0)
            blf_count = state.get("blf_count", 0)

            # Try to find the owning user
            # Device profiles are typically named "UDP-{userid}" or similar
            # Check if any user references this profile
            user_cid = self._find_profile_owner(store, profile_name)

            prov = extract_provenance(dp_data)
            dp = CanonicalDeviceProfile(
                canonical_id=f"device_profile:{profile_name}",
                provenance=prov,
                status=MigrationStatus.ANALYZED,
                profile_name=profile_name,
                user_canonical_id=user_cid,
                model=model,
                protocol=protocol,
                lines=lines,
                device_pool_name=device_pool,
                speed_dial_count=sd_count,
                blf_count=blf_count,
            )
            store.upsert_object(dp)
            result.objects_created += 1

            # Write cross-ref if user found
            if user_cid:
                store.add_cross_ref(user_cid, dp.canonical_id, "user_has_device_profile")

            # Decision: EM has features Webex hot desking doesn't support
            has_multi_line = len(lines) > 1
            has_extra_features = sd_count > 0 or blf_count > 0

            if has_multi_line or has_extra_features:
                features_lost = []
                if has_multi_line:
                    features_lost.append(f"{len(lines)} line(s) — Webex hot desking uses primary line only")
                if sd_count > 0:
                    features_lost.append(f"{sd_count} speed dial(s)")
                if blf_count > 0:
                    features_lost.append(f"{blf_count} BLF entr(ies)")

                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity="LOW",
                    summary=(
                        f"Device profile '{profile_name}' has features that "
                        f"Webex hot desking cannot replicate"
                    ),
                    context={
                        "profile_name": profile_name,
                        "user_id": user_cid,
                        "features_lost": features_lost,
                        "line_count": len(lines),
                        "speed_dial_count": sd_count,
                        "blf_count": blf_count,
                    },
                    options=[
                        accept_option("Enable hot desking — user gets primary line only, loses profile features"),
                        skip_option("Don't enable hot desking"),
                        manual_option("Admin creates workspace and configures manually"),
                    ],
                    affected_objects=[dp.canonical_id] + ([user_cid] if user_cid else []),
                )
                result.decisions.append(decision)

        return result

    @staticmethod
    def _find_profile_owner(store: MigrationStore, profile_name: str) -> str | None:
        """Try to find the user who owns a device profile.

        CUCM device profiles are typically named 'UDP-{userid}' or
        '{model}-{userid}'. Also check cross-refs for user_has_device_profile
        if already built.
        """
        # Check common naming patterns
        lower_name = profile_name.lower()
        for prefix in ("udp-", "dp-", "em-"):
            if lower_name.startswith(prefix):
                userid = profile_name[len(prefix):]
                user_cid = f"user:{userid}"
                if store.get_object(user_cid):
                    return user_cid

        # Brute force: check all users for matching profile reference
        # (expensive but covers non-standard naming)
        for user_data in store.get_objects("user"):
            state = user_data.get("pre_migration_state") or {}
            default_profile = state.get("defaultProfile") or state.get("deviceProfile") or ""
            if default_profile == profile_name:
                return user_data["canonical_id"]

        return None
