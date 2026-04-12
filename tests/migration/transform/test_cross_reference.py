"""Tests for Pass 2 CrossReferenceBuilder.

Tests verify all 27 relationship types from the manifest, shared line detection,
CSS ordinal preservation, phone model classification, and E.164 normalization.
Uses SQLite in-memory store populated with normalized objects from fixtures.

(from phase-04-normalization.md acceptance criteria)
"""

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalSharedLine,
    DeviceCompatibilityTier,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.cross_reference import (
    CrossReferenceBuilder,
    classify_phone_model,
)
from wxcli.migration.transform.normalizers import (
    normalize_css,
    normalize_cti_route_point,
    normalize_datetime_group,
    normalize_device_pool,
    normalize_hunt_list,
    normalize_hunt_pilot,
    normalize_line_group,
    normalize_partition,
    normalize_phone,
    normalize_route_group,
    normalize_route_pattern,
    normalize_sip_trunk,
    normalize_time_period,
    normalize_time_schedule,
    normalize_translation_pattern,
    normalize_user,
    normalize_voicemail_group,
    normalize_voicemail_profile,
    normalize_workspace,
)
from tests.migration.cucm.fixtures import (
    COMMON_AREA_PHONE_FIXTURE,
    CSS_FIXTURE,
    DATETIME_GROUP_FIXTURE,
    DEVICE_POOL_FIXTURE,
    END_USER_FIXTURE,
    HUNT_PILOT_FIXTURE,
    PHONE_FIXTURE,
    PHONE_FOUR_LINES_FIXTURE,
    ROUTE_PATTERN_FIXTURE,
    VOICEMAIL_PROFILE_FIXTURE,
)


@pytest.fixture
def store():
    """In-memory SQLite store for tests."""
    s = MigrationStore(":memory:")
    yield s
    s.close()


def _populate_basic(store: MigrationStore) -> None:
    """Populate store with a basic inventory for cross-reference tests."""
    # Location infrastructure
    store.upsert_object(normalize_device_pool(DEVICE_POOL_FIXTURE))
    store.upsert_object(normalize_datetime_group(DATETIME_GROUP_FIXTURE))
    store.upsert_object(normalize_partition({
        "pkid": "{PT1}", "name": "Internal-PT", "description": "Internal",
    }))
    store.upsert_object(normalize_partition({
        "pkid": "{PT2}", "name": "Local-PSTN-PT", "description": "Local PSTN",
    }))
    store.upsert_object(normalize_partition({
        "pkid": "{PT3}", "name": "International-Block-PT", "description": "Block",
    }))

    # User
    store.upsert_object(normalize_user(END_USER_FIXTURE))

    # Device (2 lines including shared team line 1050)
    store.upsert_object(normalize_phone(PHONE_FIXTURE))

    # CSS
    store.upsert_object(normalize_css(CSS_FIXTURE))

    # Route pattern
    store.upsert_object(normalize_route_pattern(ROUTE_PATTERN_FIXTURE))

    # Hunt pilot
    store.upsert_object(normalize_hunt_pilot(HUNT_PILOT_FIXTURE))

    # Voicemail profile
    store.upsert_object(normalize_voicemail_profile(VOICEMAIL_PROFILE_FIXTURE))


# ===================================================================
# Cross-ref #1: device_pool_has_datetime_group
# ===================================================================


class TestDevicePoolDateTimeGroup:
    def test_ref_created(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs(
            "device_pool:DP-SanJose-Phones", "device_pool_has_datetime_group"
        )
        assert refs == ["datetime_group:CMLocal"]


# ===================================================================
# Cross-ref #2: device_pool_at_cucm_location
# ===================================================================


class TestDevicePoolAtCUCMLocation:
    def test_ref_created(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs(
            "device_pool:DP-SanJose-Phones", "device_pool_at_cucm_location"
        )
        assert refs == ["cucm_location:SanJose"]


# ===================================================================
# Cross-ref #3, #4: User relationships
# ===================================================================


class TestUserRefs:
    def test_user_has_device(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("user:jdoe", "user_has_device")
        assert "device:SEP001122334455" in refs

    def test_user_has_primary_dn(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("user:jdoe", "user_has_primary_dn")
        assert refs == ["dn:1001:Internal-PT"]


# ===================================================================
# Cross-ref #5: device_has_dn
# ===================================================================


class TestDeviceHasDN:
    def test_refs_created(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.get_cross_refs(
            from_id="device:SEP001122334455", relationship="device_has_dn"
        )
        assert len(refs) == 2
        dn_ids = {r["to_id"] for r in refs}
        assert "dn:1001:Internal-PT" in dn_ids
        assert "dn:1050:Internal-PT" in dn_ids

    def test_ordinal_preserved(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.get_cross_refs(
            from_id="device:SEP001122334455", relationship="device_has_dn"
        )
        ordinals = {r["to_id"]: r["ordinal"] for r in refs}
        assert ordinals["dn:1001:Internal-PT"] == 1
        assert ordinals["dn:1050:Internal-PT"] == 2


# ===================================================================
# Cross-ref #6: dn_in_partition
# ===================================================================


class TestDNInPartition:
    def test_refs_created(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("dn:1001:Internal-PT", "dn_in_partition")
        assert refs == ["partition:Internal-PT"]


# ===================================================================
# Cross-ref #7, #8: device_in_pool, device_owned_by_user
# ===================================================================


class TestDeviceOwnershipRefs:
    def test_device_in_pool(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("device:SEP001122334455", "device_in_pool")
        assert refs == ["device_pool:DP-SanJose-Phones"]

    def test_device_owned_by_user(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("device:SEP001122334455", "device_owned_by_user")
        assert refs == ["user:jdoe"]


# ===================================================================
# Description-based device owner inference
# ===================================================================


class TestDeviceOwnerInference:
    """Test that unowned phones with user-matching descriptions get
    device_owned_by_user cross-refs inferred from the description field.
    A user can own multiple phones — the cross-ref system handles this."""

    def _make_unowned_phone(self, name, description, pool="DP-SanJose-Phones"):
        """Create a CanonicalDevice with no owner but with a description."""
        return normalize_phone({
            "pkid": f"{{test-{name}}}",
            "name": name,
            "model": "Cisco 8845",
            "description": description,
            "ownerUserName": None,
            "devicePoolName": {"_value_1": pool, "uuid": "{DP-TEST}"},
            "protocol": "SIP",
            "callingSearchSpaceName": None,
            "phoneTemplateName": None,
            "softkeyTemplateName": None,
            "product": "Cisco 8845",
            "class": "Phone",
            "lines": None,
        })

    def test_infer_owner_from_full_name(self, store):
        """Phone description 'John Doe - 8845' matches user jdoe."""
        _populate_basic(store)
        phone = self._make_unowned_phone("SEP112233445566", "John Doe - 8845")
        store.upsert_object(phone)
        builder = CrossReferenceBuilder(store)
        builder.build()
        refs = store.find_cross_refs("device:SEP112233445566", "device_owned_by_user")
        assert refs == ["user:jdoe"]

    def test_infer_owner_from_userid(self, store):
        """Phone description that exactly matches a userid."""
        _populate_basic(store)
        phone = self._make_unowned_phone("SEP112233445577", "jdoe")
        store.upsert_object(phone)
        builder = CrossReferenceBuilder(store)
        builder.build()
        refs = store.find_cross_refs("device:SEP112233445577", "device_owned_by_user")
        assert refs == ["user:jdoe"]

    def test_no_match_stays_common_area(self, store):
        """Phone with description 'Lobby Phone' should NOT match any user."""
        _populate_basic(store)
        phone = self._make_unowned_phone("SEP112233445588", "Lobby Phone")
        store.upsert_object(phone)
        builder = CrossReferenceBuilder(store)
        builder.build()
        refs = store.find_cross_refs("device:SEP112233445588", "device_owned_by_user")
        assert refs == []
        refs = store.find_cross_refs("device:SEP112233445588", "common_area_device_in_pool")
        assert refs == ["device_pool:DP-SanJose-Phones"]

    def test_user_can_own_multiple_phones(self, store):
        """Same user matched from two different phones via description."""
        _populate_basic(store)
        phone1 = self._make_unowned_phone("SEP111111111111", "John Doe - Desk")
        phone2 = self._make_unowned_phone("SEP222222222222", "John Doe - Lab")
        store.upsert_object(phone1)
        store.upsert_object(phone2)
        builder = CrossReferenceBuilder(store)
        builder.build()
        refs1 = store.find_cross_refs("device:SEP111111111111", "device_owned_by_user")
        refs2 = store.find_cross_refs("device:SEP222222222222", "device_owned_by_user")
        assert refs1 == ["user:jdoe"]
        assert refs2 == ["user:jdoe"]

    def test_short_description_no_false_positive(self, store):
        """Short descriptions like 'Lab' should not match a user's first name."""
        _populate_basic(store)
        phone = self._make_unowned_phone("SEP112233445599", "Lab")
        store.upsert_object(phone)
        builder = CrossReferenceBuilder(store)
        builder.build()
        refs = store.find_cross_refs("device:SEP112233445599", "device_owned_by_user")
        assert refs == []


# ===================================================================
# Cross-ref #9: common_area_device_in_pool
# ===================================================================


class TestCommonAreaDeviceInPool:
    def test_workspace_ref(self, store):
        _populate_basic(store)
        store.upsert_object(normalize_workspace(COMMON_AREA_PHONE_FIXTURE))
        store.upsert_object(normalize_device_pool({
            "pkid": "{DP444444}",
            "name": "DP-SanJose-CommonArea",
            "dateTimeSettingName": None,
            "locationName": None,
            "callManagerGroupName": None,
            "srstName": None,
            "regionName": None,
            "mediaResourceListName": None,
        }))
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs(
            "workspace:SEP556677889900", "common_area_device_in_pool"
        )
        assert refs == ["device_pool:DP-SanJose-CommonArea"]


# ===================================================================
# Cross-ref #10: route_pattern_in_partition
# ===================================================================


class TestRoutePatternInPartition:
    def test_ref_created(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        rp_id = "route_pattern:9.1[2-9]XXXXXXXXX:Local-PSTN-PT"
        refs = store.find_cross_refs(rp_id, "route_pattern_in_partition")
        assert refs == ["partition:Local-PSTN-PT"]


# ===================================================================
# Cross-ref #13: route_group_has_trunk
# ===================================================================


class TestRouteGroupHasTrunk:
    def test_ref_created(self, store):
        store.upsert_object(normalize_sip_trunk({
            "pkid": "{ST1}", "name": "SBC-Trunk-01",
            "destinationAddress": "sbc.acme.com",
            "devicePoolName": {"_value_1": "DP-SanJose-Phones", "uuid": "{DP1}"},
        }))
        store.upsert_object(normalize_route_group({
            "pkid": "{RG1}", "name": "PSTN-RG",
            "members": {
                "member": [
                    {"deviceName": {"_value_1": "SBC-Trunk-01", "uuid": "{ST1}"}},
                ]
            },
        }))
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("route_group:PSTN-RG", "route_group_has_trunk")
        assert refs == ["sip_trunk:SBC-Trunk-01"]


# ===================================================================
# Cross-ref #14: trunk_at_location
# ===================================================================


class TestTrunkAtLocation:
    def test_ref_created(self, store):
        _populate_basic(store)
        store.upsert_object(normalize_sip_trunk({
            "pkid": "{ST1}", "name": "SBC-Trunk-01",
            "devicePoolName": {"_value_1": "DP-SanJose-Phones", "uuid": "{DP1}"},
        }))
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("sip_trunk:SBC-Trunk-01", "trunk_at_location")
        assert refs == ["device_pool:DP-SanJose-Phones"]


# ===================================================================
# Cross-ref #15: translation_pattern_in_partition
# ===================================================================


class TestTranslationPatternInPartition:
    def test_ref_created(self, store):
        store.upsert_object(normalize_partition({
            "pkid": "{PT1}", "name": "Internal-PT",
        }))
        store.upsert_object(normalize_translation_pattern({
            "pkid": "{TP1}", "pattern": "8XXX",
            "calledPartyTransformationMask": "+1415555XXXX",
            "description": "Internal to E164",
            "routePartitionName": {"_value_1": "Internal-PT", "uuid": "{PT1}"},
        }))
        builder = CrossReferenceBuilder(store)
        builder.build()

        tp_id = "translation_pattern:8XXX:Internal-PT"
        refs = store.find_cross_refs(tp_id, "translation_pattern_in_partition")
        assert refs == ["partition:Internal-PT"]


# ===================================================================
# Cross-ref #16: css_contains_partition (with ordinal)
# ===================================================================


class TestCSSContainsPartition:
    def test_ordinal_preserved(self, store):
        """CSS with 3 partitions → css_contains_partition rows with ordinal 1, 2, 3."""
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.get_cross_refs(
            from_id="css:Standard-Employee-CSS",
            relationship="css_contains_partition",
        )
        assert len(refs) == 3
        ordinals = {r["to_id"]: r["ordinal"] for r in refs}
        assert ordinals["partition:Internal-PT"] == 1
        assert ordinals["partition:Local-PSTN-PT"] == 2
        assert ordinals["partition:International-Block-PT"] == 3


# ===================================================================
# Cross-ref #17: partition_has_pattern
# ===================================================================


class TestPartitionHasPattern:
    def test_route_patterns_and_dns(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        # Internal-PT should contain DNs from the phone
        refs = store.find_cross_refs("partition:Internal-PT", "partition_has_pattern")
        assert len(refs) > 0
        # Should include the DN references
        assert any("dn:" in r for r in refs)

        # Local-PSTN-PT should contain the route pattern
        refs = store.find_cross_refs("partition:Local-PSTN-PT", "partition_has_pattern")
        assert any("route_pattern:" in r for r in refs)


# ===================================================================
# Cross-ref #18: user_has_css
# ===================================================================


class TestUserHasCSS:
    def test_ref_created(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("user:jdoe", "user_has_css")
        assert refs == ["css:Standard-Employee-CSS"]


# ===================================================================
# Cross-ref #19: device_has_css
# ===================================================================


class TestDeviceHasCSS:
    def test_ref_created(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("device:SEP001122334455", "device_has_css")
        assert refs == ["css:Standard-Employee-CSS"]


# ===================================================================
# Cross-ref #20: line_has_css
# ===================================================================


class TestLineHasCSS:
    def test_line_css(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        # Line 1 on PHONE_FIXTURE has line_css = "Line-CSS"
        refs = store.find_cross_refs("dn:1001:Internal-PT", "line_has_css")
        assert refs == ["css:Line-CSS"]


# ===================================================================
# Cross-ref #21: hunt_pilot_has_hunt_list
# ===================================================================


class TestHuntPilotHasHuntList:
    def test_ref_created(self, store):
        _populate_basic(store)
        store.upsert_object(normalize_hunt_list({
            "pkid": "{HL1}", "name": "Sales-HuntList",
            "huntAlgorithm": "Top Down",
            "members": {"member": []},
        }))
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs(
            "hunt_pilot:5001:Internal-PT", "hunt_pilot_has_hunt_list"
        )
        assert refs == ["hunt_list:Sales-HuntList"]


# ===================================================================
# Cross-ref #22: hunt_list_has_line_group
# ===================================================================


class TestHuntListHasLineGroup:
    def test_ref_created(self, store):
        store.upsert_object(normalize_hunt_list({
            "pkid": "{HL1}", "name": "Sales-HuntList",
            "members": {
                "member": [
                    {"lineGroupName": {"_value_1": "Sales-LG", "uuid": "{LG1}"}},
                ]
            },
        }))
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs(
            "hunt_list:Sales-HuntList", "hunt_list_has_line_group"
        )
        assert refs == ["line_group:Sales-LG"]


# ===================================================================
# Cross-ref #23: line_group_has_members
# ===================================================================


class TestLineGroupHasMembers:
    def test_ref_created(self, store):
        store.upsert_object(normalize_line_group({
            "pkid": "{LG1}", "name": "Sales-LG",
            "members": {"member": [{"directoryNumber": "1001"}]},
        }))
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs(
            "line_group:Sales-LG", "line_group_has_members"
        )
        assert len(refs) == 1


# ===================================================================
# Cross-ref #24: cti_rp_has_script
# ===================================================================


class TestCtiRpHasScript:
    def test_ref_created(self, store):
        from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
        from datetime import datetime, timezone
        # Build CTI RP with script field directly in pre_migration_state
        cti = MigrationObject(
            canonical_id="cti_rp:AA-MainMenu",
            provenance=Provenance(
                source_system="cucm", source_id="{CTI1}",
                source_name="AA-MainMenu", extracted_at=datetime.now(timezone.utc),
            ),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "cti_rp_name": "AA-MainMenu",
                "script": "AA-Script-App",
            },
        )
        store.upsert_object(cti)

        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("cti_rp:AA-MainMenu", "cti_rp_has_script")
        assert refs == ["script:AA-Script-App"]

    def test_no_script(self, store):
        """CTI RP without script reference produces no cross-ref."""
        store.upsert_object(normalize_cti_route_point({
            "pkid": "{CTI2}",
            "name": "AA-NoScript",
            "lines": [],
        }))
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("cti_rp:AA-NoScript", "cti_rp_has_script")
        assert refs == []


# ===================================================================
# Cross-ref #25: schedule_has_time_period
# ===================================================================


class TestScheduleHasTimePeriod:
    def test_ref_created(self, store):
        store.upsert_object(normalize_time_schedule({
            "pkid": "{TS1}", "name": "BusinessHours",
            "members": {
                "member": [
                    {"timePeriodName": {"_value_1": "Weekdays", "uuid": "{TP1}"}},
                ]
            },
        }))
        store.upsert_object(normalize_time_period({
            "pkid": "{TP1}", "name": "Weekdays",
            "startTime": "08:00", "endTime": "17:00",
        }))
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs(
            "time_schedule:BusinessHours", "schedule_has_time_period"
        )
        assert refs == ["time_period:Weekdays"]


# ===================================================================
# Cross-ref #26: user_has_voicemail_profile
# ===================================================================


class TestUserHasVoicemailProfile:
    def test_ref_created(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs("user:jdoe", "user_has_voicemail_profile")
        assert refs == ["voicemail_profile:Default-VM-Profile"]


# ===================================================================
# Cross-ref #27: voicemail_profile_settings
# ===================================================================


class TestVoicemailProfileSettings:
    def test_ref_created(self, store):
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        refs = store.find_cross_refs(
            "voicemail_profile:Default-VM-Profile", "voicemail_profile_settings"
        )
        assert len(refs) == 1


# ===================================================================
# Shared Line Detection
# ===================================================================


class TestSharedLineDetection:
    def test_shared_line_on_two_devices(self, store):
        """DN '1050' on PHONE_FIXTURE (line 2) and PHONE_FOUR_LINES_FIXTURE (line 2)
        should be detected as shared.
        """
        _populate_basic(store)
        # Add second phone that also has DN 1050 on line 2
        store.upsert_object(normalize_phone(PHONE_FOUR_LINES_FIXTURE))

        builder = CrossReferenceBuilder(store)
        builder.build()

        # Check shared line objects created
        shared_lines = store.query_by_type("shared_line")
        assert len(shared_lines) >= 1

        # Find the 1050 shared line
        sl_1050 = None
        for sl in shared_lines:
            if isinstance(sl, CanonicalSharedLine) and sl.dn_canonical_id == "dn:1050:Internal-PT":
                sl_1050 = sl
                break
        assert sl_1050 is not None, "Shared line for DN 1050 not found"
        assert len(sl_1050.device_canonical_ids) == 2
        assert "device:SEP001122334455" in sl_1050.device_canonical_ids
        assert "device:SEP112233445566" in sl_1050.device_canonical_ids

    def test_single_device_dn_not_shared(self, store):
        """DN on only one device should NOT be detected as shared."""
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        # DN 1001 is only on PHONE_FIXTURE → not shared
        shared_lines = store.query_by_type("shared_line")
        sl_1001 = [
            sl for sl in shared_lines
            if isinstance(sl, CanonicalSharedLine) and sl.dn_canonical_id == "dn:1001:Internal-PT"
        ]
        assert len(sl_1001) == 0

    def test_shared_line_same_user_two_devices(self, store):
        """Same DN on 2 devices owned by same user (desk + softphone)."""
        _populate_basic(store)
        # Create softphone with same line 1001
        softphone = {
            **PHONE_FIXTURE,
            "pkid": "{PH-SOFT}",
            "name": "CSFJDOE",
            "model": "Cisco Jabber",
            "description": "John Doe - Jabber",
            "lines": {
                "line": [PHONE_FIXTURE["lines"]["line"][0]],  # Same line 1001
            },
        }
        store.upsert_object(normalize_phone(softphone))

        builder = CrossReferenceBuilder(store)
        builder.build()

        shared_lines = store.query_by_type("shared_line")
        sl_1001 = [
            sl for sl in shared_lines
            if isinstance(sl, CanonicalSharedLine) and sl.dn_canonical_id == "dn:1001:Internal-PT"
        ]
        assert len(sl_1001) == 1
        assert len(sl_1001[0].device_canonical_ids) == 2


# ===================================================================
# Phone Model Classification
# ===================================================================


class TestPhoneModelClassification:
    # --- Native MPP: 68xx ---
    def test_native_mpp_68xx(self):
        assert classify_phone_model("Cisco 6841") == DeviceCompatibilityTier.NATIVE_MPP
        assert classify_phone_model("Cisco IP Phone 6861") == DeviceCompatibilityTier.NATIVE_MPP

    # --- Native MPP: 8875 ---
    def test_8875_native_mpp(self):
        assert classify_phone_model("Cisco 8875") == DeviceCompatibilityTier.NATIVE_MPP

    def test_8875_ip_phone_native_mpp(self):
        assert classify_phone_model("Cisco IP Phone 8875") == DeviceCompatibilityTier.NATIVE_MPP

    # --- Native MPP: 9800 series ---
    def test_9811_native_mpp(self):
        assert classify_phone_model("Cisco 9811") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9811_ip_phone_native_mpp(self):
        assert classify_phone_model("Cisco IP Phone 9811") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9821_native_mpp(self):
        assert classify_phone_model("Cisco 9821") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9821_ip_phone_native_mpp(self):
        assert classify_phone_model("Cisco IP Phone 9821") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9841_native_mpp(self):
        assert classify_phone_model("Cisco 9841") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9851_native_mpp(self):
        assert classify_phone_model("Cisco 9851") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9861_native_mpp(self):
        assert classify_phone_model("Cisco 9861") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9871_native_mpp(self):
        assert classify_phone_model("Cisco 9871") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9841_ip_phone_native_mpp(self):
        assert classify_phone_model("Cisco IP Phone 9841") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9851_ip_phone_native_mpp(self):
        assert classify_phone_model("Cisco IP Phone 9851") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9861_ip_phone_native_mpp(self):
        assert classify_phone_model("Cisco IP Phone 9861") == DeviceCompatibilityTier.NATIVE_MPP

    def test_9871_ip_phone_native_mpp(self):
        assert classify_phone_model("Cisco IP Phone 9871") == DeviceCompatibilityTier.NATIVE_MPP

    # --- Convertible: 78xx ---
    def test_7811_convertible(self):
        """7811 IS convertible per Cisco E2M converter (was incorrectly INCOMPATIBLE)."""
        assert classify_phone_model("Cisco 7811") == DeviceCompatibilityTier.CONVERTIBLE

    def test_7821_convertible(self):
        assert classify_phone_model("Cisco 7821") == DeviceCompatibilityTier.CONVERTIBLE

    def test_7832_convertible(self):
        """7832 conference phone is convertible per E2M converter."""
        assert classify_phone_model("Cisco 7832") == DeviceCompatibilityTier.CONVERTIBLE

    def test_7841_convertible(self):
        assert classify_phone_model("Cisco 7841") == DeviceCompatibilityTier.CONVERTIBLE

    def test_7861_convertible(self):
        assert classify_phone_model("Cisco 7861") == DeviceCompatibilityTier.CONVERTIBLE

    # --- Convertible: 88xx audio ---
    def test_8811_convertible(self):
        assert classify_phone_model("Cisco 8811") == DeviceCompatibilityTier.CONVERTIBLE

    def test_8832_convertible(self):
        """8832 conference phone is convertible (requires MPP 12.0.3SR1)."""
        assert classify_phone_model("Cisco 8832") == DeviceCompatibilityTier.CONVERTIBLE

    def test_8841_convertible(self):
        assert classify_phone_model("Cisco 8841") == DeviceCompatibilityTier.CONVERTIBLE

    def test_8851_convertible(self):
        assert classify_phone_model("Cisco 8851") == DeviceCompatibilityTier.CONVERTIBLE

    def test_8851_ip_phone_convertible(self):
        assert classify_phone_model("Cisco IP Phone 8851") == DeviceCompatibilityTier.CONVERTIBLE

    def test_8861_convertible(self):
        assert classify_phone_model("Cisco 8861") == DeviceCompatibilityTier.CONVERTIBLE

    # --- Convertible: 88xx video ---
    def test_8845_convertible(self):
        assert classify_phone_model("Cisco 8845") == DeviceCompatibilityTier.CONVERTIBLE

    def test_8865_convertible(self):
        assert classify_phone_model("Cisco 8865") == DeviceCompatibilityTier.CONVERTIBLE

    # --- Incompatible ---
    def test_incompatible(self):
        assert classify_phone_model("Cisco 7911") == DeviceCompatibilityTier.INCOMPATIBLE
        assert classify_phone_model("Cisco 9971") == DeviceCompatibilityTier.INCOMPATIBLE
        assert classify_phone_model("Cisco 6945") == DeviceCompatibilityTier.INCOMPATIBLE
        assert classify_phone_model(None) == DeviceCompatibilityTier.INCOMPATIBLE

    def test_third_party_incompatible(self):
        """Third-party phones on CUCM fall to INCOMPATIBLE (no firmware path)."""
        assert classify_phone_model("Polycom VVX 450") == DeviceCompatibilityTier.INCOMPATIBLE
        assert classify_phone_model("Yealink T54W") == DeviceCompatibilityTier.INCOMPATIBLE

    # --- MPP suffix ---
    def test_mpp_suffix(self):
        assert classify_phone_model("Cisco 7821 MPP") == DeviceCompatibilityTier.NATIVE_MPP

    def test_7811_mpp_suffix_native(self):
        """7811 with MPP suffix should be NATIVE_MPP (7811 removed from incompatible list)."""
        assert classify_phone_model("Cisco 7811 MPP") == DeviceCompatibilityTier.NATIVE_MPP

    def test_classification_enrichment(self, store):
        """Phone model classification is applied to devices after build()."""
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        builder.build()

        dev = store.get_object_typed("device:SEP001122334455")
        assert isinstance(dev, CanonicalDevice)
        # Cisco 8845 = convertible
        assert dev.compatibility_tier == DeviceCompatibilityTier.CONVERTIBLE


# ===================================================================
# E.164 DN Normalization
# ===================================================================


class TestE164Normalization:
    def test_dns_enriched(self, store):
        """Line appearances should get e164_result after build()."""
        _populate_basic(store)
        builder = CrossReferenceBuilder(store, default_country_code="US")
        builder.build()

        dev = store.get_object_typed("device:SEP001122334455")
        assert isinstance(dev, CanonicalDevice)
        assert len(dev.line_appearances) > 0
        la = dev.line_appearances[0]
        assert "e164_result" in la
        result = la["e164_result"]
        assert result["classification"] in ("EXTENSION", "NATIONAL", "E164", "AMBIGUOUS")


# ===================================================================
# Full build integration
# ===================================================================


class TestFullBuild:
    def test_build_returns_counts(self, store):
        _populate_basic(store)
        store.upsert_object(normalize_phone(PHONE_FOUR_LINES_FIXTURE))
        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        assert isinstance(counts, dict)
        assert counts.get("device_has_dn", 0) > 0
        assert counts.get("css_contains_partition", 0) == 3
        assert counts.get("phones_classified", 0) > 0
        assert counts.get("shared_lines_detected", 0) >= 1

    def test_idempotent_rebuild(self, store):
        """Building twice should produce the same results (clear + rebuild)."""
        _populate_basic(store)
        builder = CrossReferenceBuilder(store)
        counts1 = builder.build()
        counts2 = builder.build()

        # Counts should be identical after clear + rebuild
        assert counts1.get("device_has_dn") == counts2.get("device_has_dn")
        assert counts1.get("css_contains_partition") == counts2.get("css_contains_partition")


# ===================================================================
# Cross-ref: hunt_group_uses_voicemail_group
# (from docs/superpowers/specs/2026-04-10-voicemail-groups.md §Phase 3)
# ===================================================================


class TestHuntGroupUsesVoicemailGroup:
    def test_forward_no_answer_matches(self, store):
        """Hunt pilot fwd-no-answer destination matches a voicemail group extension."""
        store.upsert_object(normalize_hunt_pilot({
            "pkid": "{HP1}", "pattern": "5001",
            "routePartitionName": {"_value_1": "Internal-PT"},
            "huntListName": {"_value_1": "Sales-HuntList"},
            "forwardHuntNoAnswer": {"destination": "9500", "enabled": "true"},
            "forwardHuntBusy": {"destination": "", "enabled": "false"},
        }))
        store.upsert_object(normalize_voicemail_group({
            "DisplayName": "Sales Voicemail",
            "DtmfAccessId": "9500",
            "ObjectId": "{VG1}",
        }))
        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs(
            "hunt_pilot:5001:Internal-PT", "hunt_group_uses_voicemail_group"
        )
        assert refs == ["voicemail_group:Sales Voicemail"]
        assert counts["hunt_group_uses_voicemail_group"] == 1

    def test_overflow_destination_matches(self, store):
        """Hunt pilot overflow destination matches a voicemail group extension."""
        store.upsert_object(normalize_hunt_pilot({
            "pkid": "{HP2}", "pattern": "6001",
            "routePartitionName": {"_value_1": "Internal-PT"},
            "huntListName": {"_value_1": "Support-HuntList"},
            "overflowDestination": "9600",
        }))
        store.upsert_object(normalize_voicemail_group({
            "DisplayName": "Support Voicemail",
            "DtmfAccessId": "9600",
            "ObjectId": "{VG2}",
        }))
        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs(
            "hunt_pilot:6001:Internal-PT", "hunt_group_uses_voicemail_group"
        )
        assert refs == ["voicemail_group:Support Voicemail"]
        assert counts["hunt_group_uses_voicemail_group"] == 1

    def test_no_match_when_no_voicemail_groups(self, store):
        """No cross-ref when store has no voicemail groups."""
        store.upsert_object(normalize_hunt_pilot({
            "pkid": "{HP3}", "pattern": "7001",
            "routePartitionName": {"_value_1": "Internal-PT"},
            "huntListName": {"_value_1": "HuntList-A"},
            "forwardHuntNoAnswer": {"destination": "9999", "enabled": "true"},
        }))
        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs(
            "hunt_pilot:7001:Internal-PT", "hunt_group_uses_voicemail_group"
        )
        assert refs == []
        assert counts["hunt_group_uses_voicemail_group"] == 0

    def test_no_match_when_destination_differs(self, store):
        """No cross-ref when forward destination doesn't match any VM group extension."""
        store.upsert_object(normalize_hunt_pilot({
            "pkid": "{HP4}", "pattern": "8001",
            "routePartitionName": {"_value_1": "Internal-PT"},
            "huntListName": {"_value_1": "HuntList-B"},
            "forwardHuntNoAnswer": {"destination": "1111", "enabled": "true"},
        }))
        store.upsert_object(normalize_voicemail_group({
            "DisplayName": "Other VM",
            "DtmfAccessId": "2222",
            "ObjectId": "{VG3}",
        }))
        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs(
            "hunt_pilot:8001:Internal-PT", "hunt_group_uses_voicemail_group"
        )
        assert refs == []
        assert counts["hunt_group_uses_voicemail_group"] == 0

    def test_forward_busy_matches(self, store):
        """Hunt pilot fwd-busy destination also triggers the cross-ref."""
        store.upsert_object(normalize_hunt_pilot({
            "pkid": "{HP5}", "pattern": "3001",
            "routePartitionName": {"_value_1": "Internal-PT"},
            "huntListName": {"_value_1": "HuntList-C"},
            "forwardHuntNoAnswer": {"destination": "", "enabled": "false"},
            "forwardHuntBusy": {"destination": "9700", "enabled": "true"},
        }))
        store.upsert_object(normalize_voicemail_group({
            "DisplayName": "Busy VM",
            "DtmfAccessId": "9700",
            "ObjectId": "{VG4}",
        }))
        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs(
            "hunt_pilot:3001:Internal-PT", "hunt_group_uses_voicemail_group"
        )
        assert refs == ["voicemail_group:Busy VM"]
        assert counts["hunt_group_uses_voicemail_group"] == 1


# ===================================================================
# Cross-ref #34: feature_uses_moh_source
# (from CLAUDE.md: _build_audio_refs — hunt pilot → music_on_hold)
# ===================================================================


class TestFeatureUsesMohSource:
    """feature_uses_moh_source cross-ref: hunt_pilot → music_on_hold."""

    def _make_moh_object(self, store, name: str, cucm_source_id: str) -> None:
        """Insert a CanonicalMusicOnHold (post-map type) into the store."""
        from datetime import datetime, timezone
        from wxcli.migration.models import (
            CanonicalMusicOnHold,
            MigrationStatus,
            Provenance,
        )
        prov = Provenance(
            source_system="cucm",
            source_id=f"moh-{name}",
            source_name=name,
            extracted_at=datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        store.upsert_object(CanonicalMusicOnHold(
            canonical_id=f"music_on_hold:{name}",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            source_name=name,
            source_file_name=f"{name}.wav",
            is_default=False,
            cucm_source_id=cucm_source_id,
        ))

    def _make_hunt_pilot_with_moh(self, store, pattern: str, moh_source_id: str) -> None:
        """Insert a hunt_pilot MigrationObject with nested queueCalls.networkHoldMohAudioSourceID."""
        from datetime import datetime, timezone
        from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
        prov = Provenance(
            source_system="cucm",
            source_id=f"hp-{pattern}",
            source_name=pattern,
            extracted_at=datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc),
        )
        store.upsert_object(MigrationObject(
            canonical_id=f"hunt_pilot:{pattern}:Internal-PT",
            provenance=prov,
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "pattern": pattern,
                "queueCalls": {
                    "enabled": "true",
                    "networkHoldMohAudioSourceID": moh_source_id,
                },
            },
        ))

    def test_ref_created_when_source_id_matches(self, store):
        """feature_uses_moh_source is created when hunt pilot queueCalls matches a MOH source."""
        self._make_moh_object(store, "SalesMOH", "42")
        self._make_hunt_pilot_with_moh(store, "2001", "42")

        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs(
            "hunt_pilot:2001:Internal-PT", "feature_uses_moh_source"
        )
        assert refs == ["music_on_hold:SalesMOH"]
        assert counts["feature_uses_moh_source"] == 1

    def test_no_ref_when_no_moh_objects(self, store):
        """No cross-ref when store has no music_on_hold objects."""
        self._make_hunt_pilot_with_moh(store, "3001", "99")

        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs(
            "hunt_pilot:3001:Internal-PT", "feature_uses_moh_source"
        )
        assert refs == []
        assert counts["feature_uses_moh_source"] == 0

    def test_no_ref_when_source_id_does_not_match(self, store):
        """No cross-ref when hunt pilot source ID doesn't match any music_on_hold cucm_source_id."""
        self._make_moh_object(store, "OtherMOH", "10")
        self._make_hunt_pilot_with_moh(store, "4001", "99")

        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs = store.find_cross_refs(
            "hunt_pilot:4001:Internal-PT", "feature_uses_moh_source"
        )
        assert refs == []
        assert counts["feature_uses_moh_source"] == 0

    def test_multiple_pilots_same_moh_source(self, store):
        """Multiple hunt pilots can reference the same MOH source."""
        self._make_moh_object(store, "SharedMOH", "7")
        self._make_hunt_pilot_with_moh(store, "5001", "7")
        self._make_hunt_pilot_with_moh(store, "5002", "7")

        builder = CrossReferenceBuilder(store)
        counts = builder.build()

        refs1 = store.find_cross_refs(
            "hunt_pilot:5001:Internal-PT", "feature_uses_moh_source"
        )
        refs2 = store.find_cross_refs(
            "hunt_pilot:5002:Internal-PT", "feature_uses_moh_source"
        )
        assert refs1 == ["music_on_hold:SharedMOH"]
        assert refs2 == ["music_on_hold:SharedMOH"]
        assert counts["feature_uses_moh_source"] == 2
