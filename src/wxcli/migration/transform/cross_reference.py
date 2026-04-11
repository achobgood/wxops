"""Pass 2: CrossReferenceBuilder — builds indexes and enriches objects using full inventory.

After all objects are in SQLite (from pass 1 normalizers), this class sweeps the
inventory to build the cross_refs table, detect shared lines, classify phone models,
normalize DNs to E.164, and build the CSS partition graph.

(from 02-normalization-architecture.md, Pass 2 specification)
(from 02-normalization-architecture.md, Complete Cross-Reference Manifest — 27 rows)

Note: Relationship `device_pool_to_location` (#note in manifest) is NOT built here —
it is written by location_mapper during the transform pass.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalSharedLine,
    DeviceCompatibilityTier,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.e164 import E164Result, normalize_dn

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Phone model compatibility table (four-tier classification)
# (from cucm-wxc-migration.md lines 363-369)
# ---------------------------------------------------------------------------

# DECT handset models — wireless handsets that need DECT network provisioning,
# NOT desk phones. Checked before _NATIVE_MPP_PATTERNS to prevent false classification.
_DECT_PATTERNS = {
    "Cisco 6823", "Cisco 6825", "Cisco 6825ip",
    "Cisco IP Phone 6823", "Cisco IP Phone 6825", "Cisco IP Phone 6825ip",
}

# Native MPP: phones that ship with or run MPP/PhoneOS firmware natively
# Phase 12c: expanded from original 68xx-only list after web search verification
# Sources: help.webex.com/qkwt4j, Cisco 9800 data sheet, 8875 landing page
_NATIVE_MPP_PATTERNS = {
    # 6800 series — MPP firmware
    "Cisco 6821", "Cisco 6841", "Cisco 6851", "Cisco 6861", "Cisco 6871",
    "Cisco IP Phone 6821", "Cisco IP Phone 6841", "Cisco IP Phone 6851",
    "Cisco IP Phone 6861", "Cisco IP Phone 6871",
    # 8875 — PhoneOS video phone
    "Cisco 8875", "Cisco IP Phone 8875",
    # 9800 series — PhoneOS, native MPP, no firmware conversion needed
    "Cisco 9811", "Cisco 9821", "Cisco 9841", "Cisco 9851", "Cisco 9861", "Cisco 9871",
    "Cisco IP Phone 9811", "Cisco IP Phone 9821",
    "Cisco IP Phone 9841", "Cisco IP Phone 9851",
    "Cisco IP Phone 9861", "Cisco IP Phone 9871",
}

# Firmware Convertible: Enterprise phones eligible for E2M conversion to MPP
# Source: Cisco E2M converter (upgrade.cisco.com/e2m_converter_wxc),
#         help.webex.com/nl9j09w (Enterprise-to-MPP migration guide)
# Phase 12c: added 7811, 7832, 8811, 8832, 8841 per Cisco conversion guide
_CONVERTIBLE_PATTERNS = {
    # 7800 series — all eligible per E2M converter
    "Cisco 7811", "Cisco 7821", "Cisco 7832", "Cisco 7841", "Cisco 7861",
    "Cisco IP Phone 7811", "Cisco IP Phone 7821", "Cisco IP Phone 7832",
    "Cisco IP Phone 7841", "Cisco IP Phone 7861",
    # 8800 series audio
    "Cisco 8811", "Cisco 8832", "Cisco 8841", "Cisco 8851", "Cisco 8861",
    "Cisco IP Phone 8811", "Cisco IP Phone 8832", "Cisco IP Phone 8841",
    "Cisco IP Phone 8851", "Cisco IP Phone 8861",
    # 8800 series video
    "Cisco 8845", "Cisco 8865",
    "Cisco IP Phone 8845", "Cisco IP Phone 8865",
}

# Software phones / soft clients — these transition to Webex App, not incompatible.
# Users keep their number/extension and use Webex App for calling.
_WEBEX_APP_KEYWORDS = [
    "jabber", "dual mode", "client services framework",
    "ip communicator", "softphone", "soft phone",
    # Video endpoints that transition to Webex Desk / RoomOS
    "telepresence", "dx70", "dx80", "dx650",
]

# Infrastructure devices — CUCM-only, not user phones, not migrated.
# Noted in reports but don't generate decisions or migration operations.
_INFRASTRUCTURE_KEYWORDS = [
    "cti port", "cti route point", "cti remote device",
    "cer ", "analog phone", "media termination point",
    "conference bridge", "music on hold", "mtp",
    "route point", "gateway",
]

# Everything else is incompatible
# (79xx, 99xx, 69xx, 39xx series, third-party phones)


def classify_phone_model(model: str | None) -> DeviceCompatibilityTier:
    """Classify a CUCM phone model into the five-tier compatibility system.

    (from cucm-wxc-migration.md lines 363-369, Phone Model Compatibility table)
    """
    if not model:
        return DeviceCompatibilityTier.INCOMPATIBLE

    # Check DECT handsets first (6823/6825/6825ip are wireless, not desk phones)
    if model in _DECT_PATTERNS:
        return DeviceCompatibilityTier.DECT

    # Check native MPP first
    if model in _NATIVE_MPP_PATTERNS:
        return DeviceCompatibilityTier.NATIVE_MPP

    # Check convertible
    if model in _CONVERTIBLE_PATTERNS:
        return DeviceCompatibilityTier.CONVERTIBLE

    model_lower = model.lower()

    # Check for infrastructure devices (CTI ports, gateways, media resources)
    if any(kw in model_lower for kw in _INFRASTRUCTURE_KEYWORDS):
        return DeviceCompatibilityTier.INFRASTRUCTURE

    # Check for software phones / soft clients → Webex App transition
    if any(kw in model_lower for kw in _WEBEX_APP_KEYWORDS):
        return DeviceCompatibilityTier.WEBEX_APP

    # Check for MPP suffix pattern (some models include "MPP" in the name).
    # Exclude known-incompatible models that might have MPP firmware loaded.
    # 7811 removed Phase 12c — it IS convertible per Cisco E2M converter.
    _INCOMPATIBLE_WITH_MPP = {"7911", "7912", "7940", "7941", "7942",
                              "7945", "7960", "7961", "7962", "7965", "7970",
                              "7971", "7975", "3905", "3911", "3951"}
    if "MPP" in model.upper():
        # Check if the model number indicates an incompatible device
        model_nums = [s for s in model.split() if s.isdigit() or s.replace("-", "").isdigit()]
        if not any(n in _INCOMPATIBLE_WITH_MPP for n in model_nums):
            return DeviceCompatibilityTier.NATIVE_MPP

    return DeviceCompatibilityTier.INCOMPATIBLE


class CrossReferenceBuilder:
    """Pass 2: builds indexes and enriches objects using full inventory.

    (from 02-normalization-architecture.md, CrossReferenceBuilder class)
    """

    def __init__(
        self,
        store: MigrationStore,
        default_country_code: str = "US",
        site_prefix_rules: list[dict] | None = None,
    ) -> None:
        self.store = store
        self.default_country_code = default_country_code
        self.site_prefix_rules = site_prefix_rules or []

    def build(self) -> dict[str, int]:
        """Build all cross-references and enrichments.

        Returns a summary dict with counts per relationship type built.

        (from 02-normalization-architecture.md: CrossReferenceBuilder.build())
        """
        # Clear existing cross-refs for clean rebuild
        # (from 07-idempotency-resumability.md lines 183-187)
        self.store.clear_cross_refs()

        # Disable FK checks during cross-ref building. Cross-refs reference
        # virtual IDs (DNs, partitions, CSS names) that may not exist as
        # stored objects — they're graph edges for traversal, not strict
        # FK relationships.
        self.store.conn.execute("PRAGMA foreign_keys=OFF")

        try:
            counts: dict[str, int] = {}

            # Order matters: some steps depend on earlier cross-refs.
            # Each method is wrapped individually so one failure doesn't
            # prevent the remaining cross-refs from being built.
            for method in [
                self._build_device_pool_refs,
                self._build_user_refs,
                self._build_device_dn_refs,
                self._build_device_ownership_refs,
                self._build_css_partition_graph,
                self._build_css_assignment_refs,
                self._build_routing_refs,
                self._build_feature_refs,
                self._build_voicemail_refs,
                self._build_template_refs,
                self._build_remote_destination_refs,
                self._build_intercept_refs,
                self._build_audio_refs,
                self._build_executive_assistant_refs,
            ]:
                try:
                    counts.update(method())
                except Exception as exc:
                    logger.warning("Cross-reference %s failed: %s", method.__name__, exc)

            # Enrichment steps (depend on cross-refs above)
            for name, method in [
                ("shared_lines_detected", self._detect_shared_lines),
                ("phones_classified", self._classify_phone_models),
                ("dns_normalized", self._normalize_dns_to_e164),
            ]:
                try:
                    counts[name] = method()
                except Exception as exc:
                    logger.warning("Cross-reference %s failed: %s", method.__name__, exc)

            return counts
        finally:
            # Re-enable FK checks even if build() throws
            self.store.conn.execute("PRAGMA foreign_keys=ON")

    # ------------------------------------------------------------------
    # Cross-ref #1, #2: Device Pool relationships
    # ------------------------------------------------------------------

    def _build_device_pool_refs(self) -> dict[str, int]:
        """Build device_pool_has_datetime_group (#1) and
        device_pool_at_cucm_location (#2).

        (from 02-normalization-architecture.md manifest rows 1-2)
        """
        counts = {"device_pool_has_datetime_group": 0, "device_pool_at_cucm_location": 0}
        for dp_data in self.store.get_objects("device_pool"):
            dp_id = dp_data["canonical_id"]
            state = dp_data.get("pre_migration_state") or {}

            # #1: device_pool → datetime_group
            dtg_name = state.get("cucm_datetime_group")
            if dtg_name:
                dtg_id = f"datetime_group:{dtg_name}"
                if self.store.get_object(dtg_id):
                    self.store.add_cross_ref(dp_id, dtg_id, "device_pool_has_datetime_group")
                    counts["device_pool_has_datetime_group"] += 1

            # #2: device_pool → cucm_location
            loc_name = state.get("cucm_location_name")
            if loc_name:
                # CUCM location entities may not exist as separate objects in our store.
                # Store the ref with the name-based ID regardless, for location_mapper.
                loc_id = f"cucm_location:{loc_name}"
                self.store.add_cross_ref(dp_id, loc_id, "device_pool_at_cucm_location")
                counts["device_pool_at_cucm_location"] += 1

        return counts

    # ------------------------------------------------------------------
    # Cross-ref #3, #4: User relationships
    # ------------------------------------------------------------------

    def _build_user_refs(self) -> dict[str, int]:
        """Build user_has_device (#3) and user_has_primary_dn (#4).

        (from 02-normalization-architecture.md manifest rows 3-4)
        """
        counts = {"user_has_device": 0, "user_has_primary_dn": 0}
        for user_data in self.store.get_objects("user"):
            user_id = user_data["canonical_id"]
            state = user_data.get("pre_migration_state") or {}

            # #3: user → devices
            for dev_name in state.get("associated_devices", []):
                dev_id = f"device:{dev_name}"
                if self.store.get_object(dev_id):
                    self.store.add_cross_ref(user_id, dev_id, "user_has_device")
                    counts["user_has_device"] += 1

            # #4: user → primary DN
            ext = user_data.get("extension")
            partition = state.get("primary_partition")
            if ext and partition:
                dn_id = f"dn:{ext}:{partition}"
                self.store.add_cross_ref(user_id, dn_id, "user_has_primary_dn")
                counts["user_has_primary_dn"] += 1

        return counts

    # ------------------------------------------------------------------
    # Cross-ref #5, #6, #20: Device → DN, DN → Partition, Line → CSS
    # ------------------------------------------------------------------

    def _build_device_dn_refs(self) -> dict[str, int]:
        """Build device_has_dn (#5), dn_in_partition (#6), and line_has_css (#20).

        Iterates all devices (including common-area/workspace devices stored as
        CanonicalDevice) and creates DN cross-refs from line appearances.

        (from 02-normalization-architecture.md manifest rows 5, 6, 20)
        """
        counts = {"device_has_dn": 0, "dn_in_partition": 0, "line_has_css": 0}

        for dev_data in self.store.get_objects("device"):
            dev_id = dev_data["canonical_id"]
            for la in dev_data.get("line_appearances", []):
                dn = la.get("dn")
                partition = la.get("partition") or "<None>"
                if not dn:
                    continue

                dn_id = f"dn:{dn}:{partition}"
                line_index = la.get("line_index", 0)

                # #5: device → DN (with ordinal = line index)
                self.store.add_cross_ref(dev_id, dn_id, "device_has_dn", ordinal=line_index)
                counts["device_has_dn"] += 1

                # #6: DN → partition
                if partition != "<None>":
                    pt_id = f"partition:{partition}"
                    self.store.add_cross_ref(dn_id, pt_id, "dn_in_partition")
                    counts["dn_in_partition"] += 1

                # #20: line → CSS (line-level CSS, higher priority than device CSS)
                line_css = la.get("line_css")
                if line_css:
                    css_id = f"css:{line_css}"
                    self.store.add_cross_ref(dn_id, css_id, "line_has_css")
                    counts["line_has_css"] += 1

        return counts

    # ------------------------------------------------------------------
    # Cross-ref #7, #8, #9: Device → Pool, Device → Owner, Common-area
    # ------------------------------------------------------------------

    def _build_user_lookup(self) -> dict[str, str]:
        """Build a lookup table for matching device descriptions to users.

        Returns {lowercase_key: canonical_id} for multiple match strategies:
        - userid (e.g., "amckenzie")
        - "firstname lastname" (e.g., "adam mckenzie")
        - "lastname, firstname" (e.g., "mckenzie, adam")
        - "firstname" if unique across all users

        A user can own multiple phones — this lookup just identifies the user,
        the cross-ref system handles multi-device naturally.
        """
        lookup: dict[str, str] = {}
        first_name_counts: dict[str, int] = {}
        users_by_first: dict[str, str] = {}

        for user_data in self.store.get_objects("user"):
            cid = user_data["canonical_id"]
            userid = (user_data.get("cucm_userid") or "").lower()
            first = (user_data.get("first_name") or "").lower().strip()
            last = (user_data.get("last_name") or "").lower().strip()

            if userid:
                lookup[userid] = cid
            if first and last:
                lookup[f"{first} {last}"] = cid
                lookup[f"{last}, {first}"] = cid
                lookup[f"{last} {first}"] = cid
            if first:
                first_name_counts[first] = first_name_counts.get(first, 0) + 1
                users_by_first[first] = cid

        # Only add first-name-only matches if the name is unique
        for first, count in first_name_counts.items():
            if count == 1:
                lookup[first] = users_by_first[first]

        return lookup

    def _match_description_to_user(
        self, description: str, user_lookup: dict[str, str]
    ) -> str | None:
        """Try to match a device description to a user.

        Tries exact match first, then checks if any user key appears as a
        substring in the description (handles "Adam McKenzie - 8845" style).
        """
        if not description:
            return None
        desc_lower = description.lower().strip()

        # Exact match
        if desc_lower in user_lookup:
            return user_lookup[desc_lower]

        # Substring match — check if a user's full name appears in the description
        # Only match on names with 2+ parts to avoid false positives on short strings
        best_match: str | None = None
        best_len = 0
        for key, cid in user_lookup.items():
            if len(key) < 4 or " " not in key:
                continue  # Skip short keys and single-word keys for substring matching
            if key in desc_lower and len(key) > best_len:
                best_match = cid
                best_len = len(key)

        return best_match

    def _build_device_ownership_refs(self) -> dict[str, int]:
        """Build device_in_pool (#7), device_owned_by_user (#8),
        and common_area_device_in_pool (#9).

        For devices without an explicit CUCM owner, attempts to match the
        device description to a known user (handles "Adam McKenzie - 8845"
        style descriptions). A user can own multiple phones.

        (from 02-normalization-architecture.md manifest rows 7-9)
        """
        counts = {
            "device_in_pool": 0,
            "device_owned_by_user": 0,
            "common_area_device_in_pool": 0,
            "device_owner_inferred": 0,
        }

        user_lookup = self._build_user_lookup()

        for dev_data in self.store.get_objects("device"):
            dev_id = dev_data["canonical_id"]
            state = dev_data.get("pre_migration_state") or {}
            dp_name = state.get("cucm_device_pool")
            owner = state.get("cucm_owner_user")

            # Fallback: try to infer owner from device description
            if not owner:
                description = dev_data.get("display_name", "")
                matched_user = self._match_description_to_user(
                    description, user_lookup
                )
                if matched_user:
                    owner = matched_user.removeprefix("user:")
                    counts["device_owner_inferred"] += 1
                    logger.info(
                        "Inferred owner for %s from description '%s' → %s",
                        dev_id, description, matched_user,
                    )

            if dp_name:
                dp_id = f"device_pool:{dp_name}"

                if owner:
                    # #7: user-owned device → pool
                    self.store.add_cross_ref(dev_id, dp_id, "device_in_pool")
                    counts["device_in_pool"] += 1

                    # #8: device → owner
                    user_id = f"user:{owner}"
                    self.store.add_cross_ref(dev_id, user_id, "device_owned_by_user")
                    counts["device_owned_by_user"] += 1

                    # Mirror from phone:{name} for mappers that read raw phone objects
                    # (CallForwardingMapper, MonitoringMapper, DeviceLayoutMapper)
                    device_name = dev_id.removeprefix("device:")
                    phone_id = f"phone:{device_name}"
                    self.store.add_cross_ref(phone_id, user_id, "device_owned_by_user")
                else:
                    # #9: common-area device → pool
                    self.store.add_cross_ref(dev_id, dp_id, "common_area_device_in_pool")
                    counts["common_area_device_in_pool"] += 1

        # Also handle workspace objects
        for ws_data in self.store.get_objects("workspace"):
            ws_id = ws_data["canonical_id"]
            state = ws_data.get("pre_migration_state") or {}
            dp_name = state.get("cucm_device_pool")
            if dp_name:
                dp_id = f"device_pool:{dp_name}"
                self.store.add_cross_ref(ws_id, dp_id, "common_area_device_in_pool")
                counts["common_area_device_in_pool"] += 1

        return counts

    # ------------------------------------------------------------------
    # Cross-ref #16, #17: CSS → Partition graph
    # ------------------------------------------------------------------

    def _build_css_partition_graph(self) -> dict[str, int]:
        """Build css_contains_partition (#16) and partition_has_pattern (#17).

        CSS partition ordering is CRITICAL — ordinal preserves partition priority.

        (from 02-normalization-architecture.md manifest rows 16-17)
        (from 04-css-decomposition.md: "ordinal values preserving partition priority")
        """
        counts = {"css_contains_partition": 0, "partition_has_pattern": 0}

        # #16: CSS → partitions (with ordinal)
        for css_data in self.store.get_objects("css"):
            css_id = css_data["canonical_id"]
            state = css_data.get("pre_migration_state") or {}
            for pt in state.get("partitions", []):
                pt_name = pt.get("partition_name")
                ordinal = pt.get("index", 0)
                if pt_name:
                    pt_id = f"partition:{pt_name}"
                    self.store.add_cross_ref(
                        css_id, pt_id, "css_contains_partition", ordinal=ordinal
                    )
                    counts["css_contains_partition"] += 1

        # #17: partition → patterns (reverse index built from route patterns and DNs)
        # Route patterns
        for rp_data in self.store.get_objects("route_pattern"):
            rp_id = rp_data["canonical_id"]
            state = rp_data.get("pre_migration_state") or {}
            partition = state.get("partition")
            if partition:
                pt_id = f"partition:{partition}"
                self.store.add_cross_ref(pt_id, rp_id, "partition_has_pattern")
                counts["partition_has_pattern"] += 1

        # DNs in partitions (already have dn_in_partition refs, build reverse)
        dn_refs = self.store.get_cross_refs(relationship="dn_in_partition")
        for ref in dn_refs:
            # ref: from_id=dn_id, to_id=partition_id
            self.store.add_cross_ref(ref["to_id"], ref["from_id"], "partition_has_pattern")
            counts["partition_has_pattern"] += 1

        return counts

    # ------------------------------------------------------------------
    # Cross-ref #18, #19: CSS assignments (user, device)
    # ------------------------------------------------------------------

    def _build_css_assignment_refs(self) -> dict[str, int]:
        """Build user_has_css (#18) and device_has_css (#19).

        (from 02-normalization-architecture.md manifest rows 18-19)
        """
        counts = {"user_has_css": 0, "device_has_css": 0}

        # #18: user → CSS
        for user_data in self.store.get_objects("user"):
            user_id = user_data["canonical_id"]
            state = user_data.get("pre_migration_state") or {}
            css_name = state.get("cucm_css")
            if css_name:
                css_id = f"css:{css_name}"
                self.store.add_cross_ref(user_id, css_id, "user_has_css")
                counts["user_has_css"] += 1

        # #19: device → CSS
        for dev_data in self.store.get_objects("device"):
            dev_id = dev_data["canonical_id"]
            state = dev_data.get("pre_migration_state") or {}
            css_name = state.get("cucm_css")
            if css_name:
                css_id = f"css:{css_name}"
                self.store.add_cross_ref(dev_id, css_id, "device_has_css")
                counts["device_has_css"] += 1

        return counts

    # ------------------------------------------------------------------
    # Cross-ref #10-15: Routing relationships
    # ------------------------------------------------------------------

    def _build_routing_refs(self) -> dict[str, int]:
        """Build routing cross-refs #10-15.

        (from 02-normalization-architecture.md manifest rows 10-15)
        """
        counts = {
            "route_pattern_in_partition": 0,
            "route_pattern_uses_gateway": 0,
            "route_pattern_uses_route_list": 0,
            "route_group_has_trunk": 0,
            "trunk_at_location": 0,
            "translation_pattern_in_partition": 0,
        }

        # #10: route_pattern → partition
        # #11: route_pattern → gateway (if destination is a gateway)
        # #12: route_pattern → route_list (if destination is a route list)
        for rp_data in self.store.get_objects("route_pattern"):
            rp_id = rp_data["canonical_id"]
            state = rp_data.get("pre_migration_state") or {}
            partition = state.get("partition")
            if partition:
                pt_id = f"partition:{partition}"
                self.store.add_cross_ref(rp_id, pt_id, "route_pattern_in_partition")
                counts["route_pattern_in_partition"] += 1

            # #11/#12: destination data comes from getRoutePattern detail.
            # The normalizer stores target_type and target_name if available.
            target_type = state.get("target_type")
            target_name = state.get("target_name")
            if target_name and target_type:
                if target_type in ("gateway", "trunk"):
                    target_id = f"sip_trunk:{target_name}"
                    if not self.store.get_object(target_id):
                        target_id = f"gateway:{target_name}"
                    self.store.add_cross_ref(
                        rp_id, target_id, "route_pattern_uses_gateway"
                    )
                    counts["route_pattern_uses_gateway"] += 1
                elif target_type in ("route_list", "routeList"):
                    target_id = f"route_list:{target_name}"
                    self.store.add_cross_ref(
                        rp_id, target_id, "route_pattern_uses_route_list"
                    )
                    counts["route_pattern_uses_route_list"] += 1

        # #13: route_group → trunks
        for rg_data in self.store.get_objects("route_group"):
            rg_id = rg_data["canonical_id"]
            state = rg_data.get("pre_migration_state") or {}
            for trunk in state.get("trunks", []):
                trunk_name = trunk.get("trunk_name")
                if trunk_name:
                    # Try sip_trunk first, then gateway
                    trunk_id = f"sip_trunk:{trunk_name}"
                    if not self.store.get_object(trunk_id):
                        trunk_id = f"gateway:{trunk_name}"
                    self.store.add_cross_ref(rg_id, trunk_id, "route_group_has_trunk")
                    counts["route_group_has_trunk"] += 1

        # #14: trunk → device_pool → location chain
        for trunk_type in ("sip_trunk", "gateway"):
            for trunk_data in self.store.get_objects(trunk_type):
                trunk_id = trunk_data["canonical_id"]
                state = trunk_data.get("pre_migration_state") or {}
                dp_name = state.get("cucm_device_pool")
                if dp_name:
                    dp_id = f"device_pool:{dp_name}"
                    self.store.add_cross_ref(trunk_id, dp_id, "trunk_at_location")
                    counts["trunk_at_location"] += 1

        # #15: translation_pattern → partition
        for tp_data in self.store.get_objects("translation_pattern"):
            tp_id = tp_data["canonical_id"]
            state = tp_data.get("pre_migration_state") or {}
            partition = state.get("partition")
            if partition:
                pt_id = f"partition:{partition}"
                self.store.add_cross_ref(tp_id, pt_id, "translation_pattern_in_partition")
                counts["translation_pattern_in_partition"] += 1

        return counts

    # ------------------------------------------------------------------
    # Cross-ref #21-25: Feature relationships
    # ------------------------------------------------------------------

    def _build_feature_refs(self) -> dict[str, int]:
        """Build feature cross-refs #21-25.

        (from 02-normalization-architecture.md manifest rows 21-25)
        """
        counts = {
            "hunt_pilot_has_hunt_list": 0,
            "hunt_list_has_line_group": 0,
            "line_group_has_members": 0,
            "cti_rp_has_script": 0,
            "schedule_has_time_period": 0,
        }

        # #21: hunt_pilot → hunt_list
        for hp_data in self.store.get_objects("hunt_pilot"):
            hp_id = hp_data["canonical_id"]
            state = hp_data.get("pre_migration_state") or {}
            hl_name = state.get("hunt_list_name")
            if hl_name:
                hl_id = f"hunt_list:{hl_name}"
                self.store.add_cross_ref(hp_id, hl_id, "hunt_pilot_has_hunt_list")
                counts["hunt_pilot_has_hunt_list"] += 1

        # #22: hunt_list → line_groups
        for hl_data in self.store.get_objects("hunt_list"):
            hl_id = hl_data["canonical_id"]
            state = hl_data.get("pre_migration_state") or {}
            for lg_name in state.get("line_groups", []):
                lg_id = f"line_group:{lg_name}"
                self.store.add_cross_ref(hl_id, lg_id, "hunt_list_has_line_group")
                counts["hunt_list_has_line_group"] += 1

        # #23: line_group → members (DN/line references)
        for lg_data in self.store.get_objects("line_group"):
            lg_id = lg_data["canonical_id"]
            state = lg_data.get("pre_migration_state") or {}
            for member in state.get("members", []):
                # Members may be DN references — structure varies by CUCM version.
                # Extract both DN number and partition for accurate canonical_id.
                #
                # Live AXL returns nested dicts:
                #   {"lineSelectionOrder": 1,
                #    "directoryNumber": {"pattern": "1002",
                #        "routePartitionName": {"_value_1": "Internal-PT", "uuid": None},
                #        "uuid": "{537A119B-...}"},
                #    "uuid": "{50051150-...}"}
                dn_num = None
                partition = "<None>"
                if isinstance(member, dict):
                    dn_ref = member.get("directoryNumber") or member.get("pattern")
                    if isinstance(dn_ref, dict):
                        # Nested AXL dict — extract pattern and partition from inside
                        dn_num = dn_ref.get("pattern")
                        rp = dn_ref.get("routePartitionName")
                        if isinstance(rp, dict):
                            partition = rp.get("_value_1") or "<None>"
                        elif isinstance(rp, str) and rp:
                            partition = rp
                    elif isinstance(dn_ref, str):
                        # Flat string — directoryNumber is already the pattern
                        dn_num = dn_ref
                        rp = member.get("routePartitionName")
                        if isinstance(rp, dict):
                            partition = rp.get("_value_1") or "<None>"
                        elif isinstance(rp, str) and rp:
                            partition = rp
                elif isinstance(member, str):
                    dn_num = member
                if dn_num:
                    member_id = f"dn:{dn_num}:{partition}"
                    self.store.add_cross_ref(lg_id, member_id, "line_group_has_members")
                    counts["line_group_has_members"] += 1

        # #24: cti_rp → script/application
        for cti_data in self.store.get_objects("cti_rp"):
            cti_id = cti_data["canonical_id"]
            state = cti_data.get("pre_migration_state") or {}
            # Script/app reference is typically external — store if available
            script = state.get("script") or state.get("application")
            if script:
                script_id = f"script:{script}"
                self.store.add_cross_ref(cti_id, script_id, "cti_rp_has_script")
                counts["cti_rp_has_script"] += 1

        # #25: schedule → time_periods
        for sched_data in self.store.get_objects("time_schedule"):
            sched_id = sched_data["canonical_id"]
            state = sched_data.get("pre_migration_state") or {}
            for tp_name in state.get("time_periods", []):
                tp_id = f"time_period:{tp_name}"
                self.store.add_cross_ref(sched_id, tp_id, "schedule_has_time_period")
                counts["schedule_has_time_period"] += 1

        return counts

    # ------------------------------------------------------------------
    # Cross-ref #26, #27: Voicemail relationships
    # ------------------------------------------------------------------

    def _build_voicemail_refs(self) -> dict[str, int]:
        """Build user_has_voicemail_profile (#26) and voicemail_profile_settings (#27).

        (from 02-normalization-architecture.md manifest rows 26-27)
        """
        counts = {"user_has_voicemail_profile": 0, "voicemail_profile_settings": 0}

        # #26: user → voicemail_profile
        for user_data in self.store.get_objects("user"):
            user_id = user_data["canonical_id"]
            state = user_data.get("pre_migration_state") or {}
            vm_profile = state.get("cucm_voicemail_profile")
            if vm_profile:
                vm_id = f"voicemail_profile:{vm_profile}"
                self.store.add_cross_ref(user_id, vm_id, "user_has_voicemail_profile")
                counts["user_has_voicemail_profile"] += 1

        # #27: voicemail_profile → settings
        # Settings are stored in the voicemail profile object's pre_migration_state.
        # The cross-ref links profile to itself with settings for the voicemail_mapper.
        for vm_data in self.store.get_objects("voicemail_profile"):
            vm_id = vm_data["canonical_id"]
            state = vm_data.get("pre_migration_state") or {}
            if state:
                self.store.add_cross_ref(vm_id, vm_id, "voicemail_profile_settings")
                counts["voicemail_profile_settings"] += 1

        return counts

    # ------------------------------------------------------------------
    # Cross-refs: Phone → Button Template, Phone → Softkey Template
    # (from tier2-phase2-phone-config-design.md §2.4)
    # ------------------------------------------------------------------

    def _build_template_refs(self) -> dict[str, int]:
        """Build phone_uses_button_template, phone_uses_softkey_template, and
        phone_uses_common_phone_config cross-references.

        Raw phone objects store AXL zeep dicts in pre_migration_state.
        Template names are in phoneTemplateName/softkeyTemplateName as
        zeep ref dicts: {"_value_1": "Template Name", "uuid": "..."}.
        Common phone config name may be a zeep ref dict or a plain string
        (already normalized by normalize_phone).
        """
        bt_count = 0
        sk_count = 0
        cpc_count = 0

        for phone in self.store.get_objects("phone"):
            phone_id = phone["canonical_id"]
            state = phone.get("pre_migration_state") or {}

            # Button template: raw AXL field is phoneTemplateName (zeep ref dict)
            bt_raw = state.get("phoneTemplateName")
            bt_name = self._ref_value(bt_raw)
            if bt_name:
                bt_id = f"button_template:{bt_name}"
                self.store.add_cross_ref(phone_id, bt_id, "phone_uses_button_template")
                bt_count += 1

            # Softkey template: raw AXL field is softkeyTemplateName (zeep ref dict)
            sk_raw = state.get("softkeyTemplateName")
            sk_name = self._ref_value(sk_raw)
            if sk_name:
                sk_id = f"softkey_template:{sk_name}"
                self.store.add_cross_ref(phone_id, sk_id, "phone_uses_softkey_template")
                sk_count += 1

            # Common phone config: raw AXL field or normalized field
            cpc_raw = state.get("commonPhoneConfigName")
            cpc_name = self._ref_value(cpc_raw)
            if not cpc_name:
                cpc_name = state.get("cucm_common_phone_config")
            if cpc_name:
                cpc_id = f"info_common_phone_config:{cpc_name}"
                self.store.add_cross_ref(phone_id, cpc_id, "phone_uses_common_phone_config")
                cpc_count += 1

        return {
            "phone_uses_button_template": bt_count,
            "phone_uses_softkey_template": sk_count,
            "phone_uses_common_phone_config": cpc_count,
        }

    def _build_executive_assistant_refs(self) -> dict[str, int]:
        """Build executive/assistant relationship cross-refs.

        (from executive-assistant-migration spec §4b)
        """
        counts = {
            "executive_has_assistant": 0,
            "assistant_serves_executive": 0,
            "user_is_executive": 0,
            "user_is_assistant": 0,
        }
        for pair_data in self.store.get_objects("exec_asst_pair"):
            state = pair_data.get("pre_migration_state") or {}
            exec_userid = state.get("executive_userid")
            asst_userid = state.get("assistant_userid")
            if not exec_userid or not asst_userid:
                continue
            self.store.add_cross_ref(
                f"user:{exec_userid}", f"user:{asst_userid}", "executive_has_assistant"
            )
            counts["executive_has_assistant"] += 1
            self.store.add_cross_ref(
                f"user:{asst_userid}", f"user:{exec_userid}", "assistant_serves_executive"
            )
            counts["assistant_serves_executive"] += 1

        for setting_data in self.store.get_objects("exec_setting"):
            state = setting_data.get("pre_migration_state") or {}
            userid = state.get("userid")
            role = state.get("role")
            if not userid:
                continue
            setting_id = setting_data["canonical_id"]
            user_id = f"user:{userid}"
            if role == "EXECUTIVE":
                self.store.add_cross_ref(user_id, setting_id, "user_is_executive")
                counts["user_is_executive"] += 1
            elif role == "EXECUTIVE_ASSISTANT":
                self.store.add_cross_ref(user_id, setting_id, "user_is_assistant")
                counts["user_is_assistant"] += 1
        return counts

    def _build_remote_destination_refs(self) -> dict[str, int]:
        """Build user → remote_destination cross-refs for SNR.

        (from tier2-enterprise-expansion.md §4: user_has_snr)
        """
        count = 0
        for rd in self.store.get_objects("remote_destination"):
            state = rd.get("pre_migration_state") or {}
            owner_userid = state.get("ownerUserId") or ""
            if not owner_userid:
                continue
            user_cid = f"user:{owner_userid}"
            if self.store.get_object(user_cid):
                self.store.add_cross_ref(user_cid, rd["canonical_id"], "user_has_remote_destination")
                count += 1
        return {"user_has_remote_destination": count}

    def _build_intercept_refs(self) -> dict[str, int]:
        """Build user -> intercept_candidate cross-refs."""
        count = 0
        for ic in self.store.get_objects("intercept_candidate"):
            state = ic.get("pre_migration_state") or {}
            userid = state.get("userid") or ""
            if not userid:
                continue
            user_cid = f"user:{userid}"
            if self.store.get_object(user_cid):
                self.store.add_cross_ref(user_cid, ic["canonical_id"], "user_has_intercept_signal")
                count += 1
        return {"user_has_intercept_signal": count}

    # ------------------------------------------------------------------
    # Cross-ref #33: Feature → MoH audio source
    # ------------------------------------------------------------------

    def _build_audio_refs(self) -> dict[str, int]:
        """Build feature → MoH source cross-refs.

        Hunt pilots with networkHoldMohAudioSourceID reference a CUCM MoH
        audio source by numeric ID. Resolve to the canonical_id of the
        music_on_hold object so the report can show which features use
        which custom MoH sources.
        """
        counts = {"feature_uses_moh_source": 0}

        # Build lookup: cucm_source_id → canonical_id
        moh_lookup: dict[str, str] = {}
        for moh in self.store.get_objects("music_on_hold"):
            source_id = moh.get("cucm_source_id")
            if source_id:
                moh_lookup[str(source_id)] = moh.get("canonical_id", "")

        if not moh_lookup:
            return counts

        # Hunt pilots → MoH source
        for hp_data in self.store.get_objects("hunt_pilot"):
            hp_id = hp_data["canonical_id"]
            state = hp_data.get("pre_migration_state") or {}
            queue_calls = state.get("queueCalls") or {}
            moh_source_id = queue_calls.get("networkHoldMohAudioSourceID")
            if moh_source_id and str(moh_source_id) in moh_lookup:
                moh_canonical = moh_lookup[str(moh_source_id)]
                self.store.add_cross_ref(hp_id, moh_canonical, "feature_uses_moh_source")
                counts["feature_uses_moh_source"] += 1

        return counts

    @staticmethod
    def _ref_value(field: Any) -> str | None:
        """Extract display value from a zeep reference field or plain string."""
        if field is None:
            return None
        if isinstance(field, str):
            return field or None
        if isinstance(field, dict):
            val = field.get("_value_1")
            return val if val else None
        return None

    # ------------------------------------------------------------------
    # Enrichment: Shared line detection
    # ------------------------------------------------------------------

    def _detect_shared_lines(self) -> int:
        """Detect DNs that appear on multiple devices, create CanonicalSharedLine objects.

        (from 02-normalization-architecture.md, _detect_shared_lines)
        (from 02b-cucm-extraction.md §2.7, shared line detection)
        """
        rows = self.store.conn.execute("""
            SELECT cr.to_id as dn_id, COUNT(DISTINCT cr.from_id) as device_count
            FROM cross_refs cr
            WHERE cr.relationship = 'device_has_dn'
            GROUP BY cr.to_id
            HAVING COUNT(DISTINCT cr.from_id) > 1
        """).fetchall()

        count = 0
        for row in rows:
            dn_id = row["dn_id"]
            device_count = row["device_count"]

            # Find all devices with this DN
            device_refs = self.store.get_cross_refs(
                to_id=dn_id, relationship="device_has_dn"
            )

            # Build device list with owner info
            device_canonical_ids = []
            owner_canonical_ids = []
            for ref in device_refs:
                dev_id = ref["from_id"]
                device_canonical_ids.append(dev_id)

                # Find owner via device_owned_by_user
                owner_refs = self.store.find_cross_refs(dev_id, "device_owned_by_user")
                for owner_id in owner_refs:
                    if owner_id not in owner_canonical_ids:
                        owner_canonical_ids.append(owner_id)

            # Extract DN pattern from dn_id (format: "dn:pattern:partition")
            parts = dn_id.split(":", 2)
            dn_pattern = parts[1] if len(parts) > 1 else dn_id

            shared_line = CanonicalSharedLine(
                canonical_id=f"shared_line:{dn_id.replace('dn:', '')}",
                provenance=Provenance(
                    source_system="cucm",
                    source_id=dn_id,
                    source_name=dn_pattern,
                    extracted_at=_now(),
                ),
                status=MigrationStatus.NORMALIZED,
                dn_canonical_id=dn_id,
                owner_canonical_ids=owner_canonical_ids,
                device_canonical_ids=device_canonical_ids,
            )
            self.store.upsert_object(shared_line)
            count += 1
            logger.info(
                "Shared line detected: %s on %d devices", dn_id, device_count
            )

        return count

    # ------------------------------------------------------------------
    # Enrichment: Phone model classification
    # ------------------------------------------------------------------

    def _classify_phone_models(self) -> int:
        """Classify all devices by model compatibility tier.

        (from 02-normalization-architecture.md: "apply the four-tier firmware
         compatibility table")
        (from cucm-wxc-migration.md lines 363-369)
        """
        count = 0
        for dev_obj in self.store.query_by_type("device"):
            if not isinstance(dev_obj, CanonicalDevice):
                continue
            tier = classify_phone_model(dev_obj.model)
            if dev_obj.compatibility_tier != tier:
                dev_obj.compatibility_tier = tier
                self.store.upsert_object(dev_obj)
                count += 1

        return count

    # ------------------------------------------------------------------
    # Enrichment: E.164 DN normalization
    # ------------------------------------------------------------------

    def _normalize_dns_to_e164(self) -> int:
        """Normalize all DNs to E.164 using the e164 module.

        For each device's line appearances, apply E.164 normalization using
        the device's resolved location (and therefore country code from config).

        (from 02-normalization-architecture.md: "apply E.164 normalization")
        """
        count = 0
        for dev_obj in self.store.query_by_type("device"):
            if not isinstance(dev_obj, CanonicalDevice):
                continue

            updated = False
            for la in dev_obj.line_appearances:
                dn = la.get("dn")
                if not dn:
                    continue

                result = normalize_dn(
                    dn, self.default_country_code, self.site_prefix_rules
                )
                la["e164_result"] = {
                    "e164": result.e164,
                    "extension": result.extension,
                    "classification": result.classification,
                }
                updated = True

            if updated:
                self.store.upsert_object(dev_obj)
                count += 1

        return count
