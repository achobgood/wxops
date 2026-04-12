"""Tests for Pass 1 normalizers.

Each test verifies that a normalizer function correctly maps a raw CUCM dict
(from fixtures) into the expected canonical model with correct field values
and unresolved foreign key strings.

(from phase-04-normalization.md acceptance criteria)
"""

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalTranslationPattern,
    CanonicalUser,
    CanonicalVoicemailProfile,
    CanonicalWorkspace,
    MigrationObject,
    MigrationStatus,
)
from wxcli.migration.transform.normalizers import (
    NORMALIZER_REGISTRY,
    is_common_area_device,
    normalize_call_park,
    normalize_css,
    normalize_cti_route_point,
    normalize_datetime_group,
    normalize_device_pool,
    normalize_gateway,
    normalize_hunt_list,
    normalize_hunt_pilot,
    normalize_line_group,
    normalize_partition,
    normalize_phone,
    normalize_pickup_group,
    normalize_route_group,
    normalize_route_list,
    normalize_route_pattern,
    normalize_sip_trunk,
    normalize_time_period,
    normalize_time_schedule,
    normalize_translation_pattern,
    normalize_user,
    normalize_voicemail_profile,
    normalize_workspace,
)
from tests.migration.cucm.fixtures import (
    COMMON_AREA_PHONE_FIXTURE,
    CSS_FIVE_PARTITIONS_FIXTURE,
    CSS_FIXTURE,
    DATETIME_GROUP_FIXTURE,
    DEVICE_POOL_FIXTURE,
    DEVICE_POOL_NO_DATETIME_FIXTURE,
    END_USER_FIXTURE,
    HUNT_PILOT_FIXTURE,
    PHONE_FIXTURE,
    PHONE_FOUR_LINES_FIXTURE,
    ROUTE_PATTERN_FIXTURE,
    USER_NO_EMAIL_FIXTURE,
    VOICEMAIL_PROFILE_FIXTURE,
)


# ===================================================================
# Device Pool
# ===================================================================


class TestNormalizeDevicePool:
    def test_basic(self):
        result = normalize_device_pool(DEVICE_POOL_FIXTURE)
        assert isinstance(result, MigrationObject)
        assert result.canonical_id == "device_pool:DP-SanJose-Phones"
        assert result.status == MigrationStatus.NORMALIZED
        assert result.provenance.source_system == "cucm"
        assert result.provenance.source_id == "{B1234567-ABCD-1234-ABCD-123456789012}"
        state = result.pre_migration_state
        assert state["device_pool_name"] == "DP-SanJose-Phones"
        assert state["cucm_datetime_group"] == "CMLocal"
        assert state["cucm_location_name"] == "SanJose"
        assert state["cucm_cm_group"] == "Default"
        assert state["cucm_srst"] == "SRST-SanJose"
        assert state["cucm_region"] == "SanJose-Region"
        assert state["cucm_media_resource_list"] is None

    def test_no_datetime_group(self):
        result = normalize_device_pool(DEVICE_POOL_NO_DATETIME_FIXTURE)
        assert result.canonical_id == "device_pool:DP-Default-Inherited"
        state = result.pre_migration_state
        assert state["cucm_datetime_group"] is None
        assert state["cucm_srst"] is None


# ===================================================================
# DateTime Group
# ===================================================================


class TestNormalizeDateTimeGroup:
    def test_basic(self):
        result = normalize_datetime_group(DATETIME_GROUP_FIXTURE)
        assert isinstance(result, MigrationObject)
        assert result.canonical_id == "datetime_group:CMLocal"
        state = result.pre_migration_state
        assert state["datetime_group_name"] == "CMLocal"
        assert state["timezone"] == "America/Los_Angeles"


# ===================================================================
# End User
# ===================================================================


class TestNormalizeUser:
    def test_basic(self):
        result = normalize_user(END_USER_FIXTURE)
        assert isinstance(result, CanonicalUser)
        assert result.canonical_id == "user:jdoe"
        assert result.status == MigrationStatus.NORMALIZED
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.display_name == "John Doe"
        assert result.emails == ["jdoe@acme.com"]
        assert result.extension == "1001"
        assert result.department == "Engineering"
        assert result.title == "Software Engineer"
        assert result.cucm_manager_user_id == "msmith"
        assert result.cucm_userid == "jdoe"
        assert result.cucm_mailid == "jdoe@acme.com"
        # Pre-migration state (unresolved foreign keys)
        state = result.pre_migration_state
        assert state["associated_devices"] == ["SEP001122334455", "CSFJDOE"]
        assert state["enable_cti"] is True
        assert state["primary_partition"] == "Internal-PT"
        assert state["cucm_css"] == "Standard-Employee-CSS"
        assert state["cucm_voicemail_profile"] == "Default-VM-Profile"

    def test_no_email(self):
        result = normalize_user(USER_NO_EMAIL_FIXTURE)
        assert result.canonical_id == "user:legacyuser"
        assert result.emails == []
        assert result.cucm_mailid is None
        assert result.title is None
        assert result.cucm_manager_user_id is None
        state = result.pre_migration_state
        assert state["enable_cti"] is False
        assert state["cucm_voicemail_profile"] is None

    def test_single_device_string(self):
        """associatedDevices may be a single string, not a list."""
        raw = {**END_USER_FIXTURE, "associatedDevices": {"device": "SEP001122334455"}}
        result = normalize_user(raw)
        assert result.pre_migration_state["associated_devices"] == ["SEP001122334455"]

    def test_no_associated_devices(self):
        raw = {**END_USER_FIXTURE, "associatedDevices": None}
        result = normalize_user(raw)
        assert result.pre_migration_state["associated_devices"] == []

    def test_email_lowercase(self):
        raw = {**END_USER_FIXTURE, "mailid": "JDoe@Acme.COM"}
        result = normalize_user(raw)
        assert result.emails == ["jdoe@acme.com"]

    def test_sql_extracted_user(self):
        """SQL-extracted users have flat associatedDevices and no UUID wrappers."""
        raw = {
            "pkid": "{A-SQL}",
            "firstName": "SQL",
            "lastName": "User",
            "mailid": "sqluser@acme.com",
            "userid": "sqluser",
            "telephoneNumber": None,
            "department": None,
            "title": None,
            "manager": None,
            "_extracted_via": "sql",
            # SQL: associatedDevices is already flat list
            "associatedDevices": ["SEP111111111111"],
            # SQL: primaryExtension without UUID wrapper
            "primaryExtension": {
                "pattern": "3001",
                "routePartitionName": "Internal-PT",
            },
            "enableCti": True,  # SQL may return bool not str
            # SQL: these are None
            "callingSearchSpaceName": None,
            "voiceMailProfile": None,
            "selfService": None,
            "userLocale": None,
        }
        result = normalize_user(raw)
        assert result.canonical_id == "user:sqluser"
        assert result.extension == "3001"
        assert result.pre_migration_state["associated_devices"] == ["SEP111111111111"]
        assert result.pre_migration_state["primary_partition"] == "Internal-PT"
        assert result.pre_migration_state["enable_cti"] is True
        assert result.pre_migration_state["extracted_via_sql"] is True
        assert result.pre_migration_state["cucm_css"] is None

    def test_empty_reference_fields(self):
        """Empty references are {'_value_1': None, 'uuid': None}, not plain None."""
        raw = {
            **END_USER_FIXTURE,
            "callingSearchSpaceName": {"_value_1": None, "uuid": None},
            "voiceMailProfile": {"_value_1": None, "uuid": None},
            "manager": {"_value_1": None, "uuid": None},
        }
        result = normalize_user(raw)
        assert result.pre_migration_state["cucm_css"] is None
        assert result.pre_migration_state["cucm_voicemail_profile"] is None
        assert result.cucm_manager_user_id is None


# ===================================================================
# Phone (→ CanonicalDevice)
# ===================================================================


class TestNormalizePhone:
    def test_basic(self):
        result = normalize_phone(PHONE_FIXTURE)
        assert isinstance(result, CanonicalDevice)
        assert result.canonical_id == "device:SEP001122334455"
        assert result.mac == "001122334455"
        assert result.model == "Cisco 8845"
        assert result.display_name == "John Doe - Desk Phone"
        assert result.cucm_protocol == "SIP"
        assert result.cucm_device_name == "SEP001122334455"
        assert result.status == MigrationStatus.NORMALIZED
        # Foreign keys in pre_migration_state
        state = result.pre_migration_state
        assert state["cucm_device_pool"] == "DP-SanJose-Phones"
        assert state["cucm_css"] == "Standard-Employee-CSS"
        assert state["cucm_owner_user"] == "jdoe"

    def test_line_appearances(self):
        result = normalize_phone(PHONE_FIXTURE)
        assert len(result.line_appearances) == 2
        line1 = result.line_appearances[0]
        assert line1["line_index"] == 1
        assert line1["dn"] == "1001"
        assert line1["partition"] == "Internal-PT"
        assert line1["e164_mask"] == "+14155551001"
        assert line1["line_css"] == "Line-CSS"
        assert line1["shared_line_css"] is None
        assert line1["associated_endusers"] == ["jdoe"]
        line2 = result.line_appearances[1]
        assert line2["line_index"] == 2
        assert line2["dn"] == "1050"
        assert line2["shared_line_css"] == "SharedLine-CSS"
        assert "jdoe" in line2["associated_endusers"]
        assert "asmith" in line2["associated_endusers"]

    def test_four_lines(self):
        result = normalize_phone(PHONE_FOUR_LINES_FIXTURE)
        assert len(result.line_appearances) == 4
        assert result.line_appearances[0]["line_index"] == 1
        assert result.line_appearances[3]["line_index"] == 4
        assert result.line_appearances[2]["partition"] == "Executive-PT"

    def test_no_lines(self):
        raw = {**PHONE_FIXTURE, "lines": None}
        result = normalize_phone(raw)
        assert result.line_appearances == []

    def test_empty_lines(self):
        raw = {**PHONE_FIXTURE, "lines": {}}
        result = normalize_phone(raw)
        assert result.line_appearances == []

    def test_single_line_dict(self):
        """lines.line may be a single dict instead of a list."""
        single_line = PHONE_FIXTURE["lines"]["line"][0]
        raw = {**PHONE_FIXTURE, "lines": {"line": single_line}}
        result = normalize_phone(raw)
        assert len(result.line_appearances) == 1
        assert result.line_appearances[0]["dn"] == "1001"

    def test_non_sep_device_no_mac(self):
        raw = {**PHONE_FIXTURE, "name": "CSFJDOE"}
        result = normalize_phone(raw)
        assert result.mac is None
        assert result.canonical_id == "device:CSFJDOE"

    def test_description_fallback_to_name(self):
        raw = {**PHONE_FIXTURE, "description": None}
        result = normalize_phone(raw)
        assert result.display_name == "SEP001122334455"

    def test_call_forwarding_fields(self):
        """Verified via live CUCM: call forwarding fields are on each line's dirn."""
        import copy
        raw = copy.deepcopy(PHONE_FIXTURE)
        raw["lines"]["line"][0]["dirn"]["callForwardAll"] = {
            "destination": "8000",
            "forwardToVoiceMail": "true",
            "callingSearchSpaceName": {"_value_1": "VM-CSS", "uuid": "{CSS-VM}"},
        }
        raw["lines"]["line"][0]["dirn"]["callForwardBusy"] = {
            "destination": "",
            "forwardToVoiceMail": "false",
        }
        result = normalize_phone(raw)
        la = result.line_appearances[0]
        assert la["call_forward_all"] is not None
        assert la["call_forward_all"]["destination"] == "8000"
        assert la["call_forward_all"]["forward_to_voicemail"] == "true"
        assert la["call_forward_all"]["calling_search_space"] == "VM-CSS"
        assert la["call_forward_busy"]["forward_to_voicemail"] == "false"
        # Fields not present should be None
        assert la["call_forward_no_answer"] is None

    def test_index_as_int(self):
        """Verified via live CUCM: zeep with WSDL returns index as int, not str."""
        import copy
        raw = copy.deepcopy(PHONE_FIXTURE)
        raw["lines"]["line"][0]["index"] = 1  # int not str
        raw["lines"]["line"][1]["index"] = 2
        result = normalize_phone(raw)
        assert result.line_appearances[0]["line_index"] == 1
        assert result.line_appearances[1]["line_index"] == 2


# ===================================================================
# Common-Area Phone (→ CanonicalWorkspace)
# ===================================================================


class TestNormalizeWorkspace:
    def test_is_common_area(self):
        assert is_common_area_device(COMMON_AREA_PHONE_FIXTURE) is True
        assert is_common_area_device(PHONE_FIXTURE) is False

    def test_not_common_area_wrong_class(self):
        raw = {**COMMON_AREA_PHONE_FIXTURE, "class": "CTI Port"}
        assert is_common_area_device(raw) is False

    def test_common_area_empty_ref_owner(self):
        """Zeep returns empty ownerUserName as {'_value_1': None, 'uuid': None}."""
        raw = {
            **COMMON_AREA_PHONE_FIXTURE,
            "ownerUserName": {"_value_1": None, "uuid": None},
        }
        assert is_common_area_device(raw) is True

    def test_basic(self):
        result = normalize_workspace(COMMON_AREA_PHONE_FIXTURE)
        assert isinstance(result, CanonicalWorkspace)
        assert result.canonical_id == "workspace:SEP556677889900"
        assert result.display_name == "Lobby Phone - Building A"
        assert result.extension == "1099"
        assert result.is_common_area is True
        state = result.pre_migration_state
        assert state["cucm_device_pool"] == "DP-SanJose-CommonArea"
        assert state["cucm_model"] == "Cisco 8841"


# ===================================================================
# CSS
# ===================================================================


class TestNormalizeCSS:
    def test_basic(self):
        result = normalize_css(CSS_FIXTURE)
        assert isinstance(result, MigrationObject)
        assert result.canonical_id == "css:Standard-Employee-CSS"
        state = result.pre_migration_state
        parts = state["partitions"]
        assert len(parts) == 3
        assert parts[0] == {"partition_name": "Internal-PT", "index": 1}
        assert parts[1] == {"partition_name": "Local-PSTN-PT", "index": 2}
        assert parts[2] == {"partition_name": "International-Block-PT", "index": 3}

    def test_five_partitions(self):
        result = normalize_css(CSS_FIVE_PARTITIONS_FIXTURE)
        state = result.pre_migration_state
        parts = state["partitions"]
        assert len(parts) == 5
        # Verify ordering preserved
        assert [p["index"] for p in parts] == [1, 2, 3, 4, 5]
        assert parts[4]["partition_name"] == "Premium-Rate-PT"

    def test_empty_members(self):
        raw = {"pkid": "x", "name": "Empty-CSS", "members": None}
        result = normalize_css(raw)
        assert result.pre_migration_state["partitions"] == []


# ===================================================================
# Route Pattern
# ===================================================================


class TestNormalizeRoutePattern:
    def test_basic(self):
        result = normalize_route_pattern(ROUTE_PATTERN_FIXTURE)
        assert isinstance(result, MigrationObject)
        assert result.canonical_id == "route_pattern:9.1[2-9]XXXXXXXXX:Local-PSTN-PT"
        state = result.pre_migration_state
        assert state["pattern"] == "9.1[2-9]XXXXXXXXX"
        assert state["partition"] == "Local-PSTN-PT"
        assert state["action"] == "ROUTE"
        assert state["network_location"] == "OffNet"

    def test_block_pattern(self):
        raw = {**ROUTE_PATTERN_FIXTURE, "blockEnable": "true", "pattern": "011!"}
        result = normalize_route_pattern(raw)
        assert result.pre_migration_state["action"] == "BLOCK"

    def test_null_partition(self):
        raw = {**ROUTE_PATTERN_FIXTURE, "routePartitionName": None}
        result = normalize_route_pattern(raw)
        assert ":<None>" in result.canonical_id

    def test_gateway_target(self):
        """Route pattern with gatewayName populates target_type/target_name."""
        raw = {
            **ROUTE_PATTERN_FIXTURE,
            "gatewayName": {
                "_value_1": "PSTN-GW-01",
                "uuid": "{GW111111-1111-1111-1111-111111111111}",
            },
        }
        result = normalize_route_pattern(raw)
        state = result.pre_migration_state
        assert state["target_type"] == "gateway"
        assert state["target_name"] == "PSTN-GW-01"

    def test_route_list_target(self):
        """Route pattern with routeListName populates target_type/target_name."""
        raw = {
            **ROUTE_PATTERN_FIXTURE,
            "routeListName": {
                "_value_1": "RL-PSTN-Primary",
                "uuid": "{RL222222-2222-2222-2222-222222222222}",
            },
        }
        result = normalize_route_pattern(raw)
        state = result.pre_migration_state
        assert state["target_type"] == "route_list"
        assert state["target_name"] == "RL-PSTN-Primary"

    def test_no_target(self):
        """Route pattern without gateway or route list has None target fields."""
        result = normalize_route_pattern(ROUTE_PATTERN_FIXTURE)
        state = result.pre_migration_state
        assert state["target_type"] is None
        assert state["target_name"] is None


# ===================================================================
# Translation Pattern
# ===================================================================


class TestNormalizeTranslationPattern:
    def test_basic(self):
        raw = {
            "pkid": "{TP111111}",
            "pattern": "8XXX",
            "calledPartyTransformationMask": "+1415555XXXX",
            "description": "Internal to E164",
            "routePartitionName": {
                "_value_1": "Internal-PT",
                "uuid": "{PT111111-1111-1111-1111-111111111111}",
            },
        }
        result = normalize_translation_pattern(raw)
        assert isinstance(result, CanonicalTranslationPattern)
        assert result.matching_pattern == "8XXX"
        assert result.replacement_pattern == "+1415555XXXX"
        assert result.name == "Internal to E164"
        assert result.pre_migration_state["partition"] == "Internal-PT"


# ===================================================================
# Hunt Pilot
# ===================================================================


class TestNormalizeHuntPilot:
    def test_basic(self):
        result = normalize_hunt_pilot(HUNT_PILOT_FIXTURE)
        assert isinstance(result, MigrationObject)
        assert result.canonical_id == "hunt_pilot:5001:Internal-PT"
        state = result.pre_migration_state
        assert state["pattern"] == "5001"
        assert state["hunt_list_name"] == "Sales-HuntList"
        assert state["forward_no_answer_destination"] == "5999"
        assert state["forward_no_answer_enabled"] is True
        assert state["forward_busy_enabled"] is False
        assert state["queue_calls_enabled"] is False
        assert state["enabled"] is True
        assert state["hunt_timer_call_pick"] == "20"

    def test_queue_style_detection(self):
        raw = {
            **HUNT_PILOT_FIXTURE,
            "queueCalls": {"enabled": "true"},
            "maxCallersInQueue": "10",
            "mohSourceId": "some-moh-id",
        }
        result = normalize_hunt_pilot(raw)
        state = result.pre_migration_state
        assert state["queue_calls_enabled"] is True
        assert state["max_callers_in_queue"] == "10"
        assert state["moh_source_id"] == "some-moh-id"


# ===================================================================
# Voicemail Profile
# ===================================================================


class TestNormalizeVoicemailProfile:
    def test_basic(self):
        result = normalize_voicemail_profile(VOICEMAIL_PROFILE_FIXTURE)
        assert isinstance(result, CanonicalVoicemailProfile)
        assert result.canonical_id == "voicemail_profile:Default-VM-Profile"
        assert result.cucm_voicemail_profile_name == "Default-VM-Profile"
        state = result.pre_migration_state
        # Verified via live CUCM: voiceMailPilot is {dirn, cssName, uuid}
        assert state["voicemail_pilot"] == "8000"
        assert state["voicemail_pilot_css"] == "VM-CSS"

    def test_legacy_value_1_format(self):
        """Fallback: handle design-spec {_value_1, uuid} format if encountered."""
        raw = {
            "pkid": "{VM2}",
            "name": "Legacy-VM",
            "voiceMailPilot": {"_value_1": "9000", "uuid": "{VMP2}"},
        }
        result = normalize_voicemail_profile(raw)
        assert result.pre_migration_state["voicemail_pilot"] == "9000"
        assert result.pre_migration_state["voicemail_pilot_css"] is None


# ===================================================================
# Additional normalizers
# ===================================================================


class TestNormalizePartition:
    def test_basic(self):
        raw = {"pkid": "{PT1}", "name": "Internal-PT", "description": "Internal"}
        result = normalize_partition(raw)
        assert result.canonical_id == "partition:Internal-PT"
        assert result.pre_migration_state["partition_name"] == "Internal-PT"


class TestNormalizeHuntList:
    def test_basic(self):
        raw = {
            "pkid": "{HL1}",
            "name": "Sales-HuntList",
            "description": "Sales",
            "huntAlgorithm": "Top Down",
            "voiceMailUsage": "NONE",
            "routeListEnabled": "true",
            "members": {
                "member": [
                    {"lineGroupName": {"_value_1": "Sales-LG", "uuid": "{LG1}"}},
                ]
            },
        }
        result = normalize_hunt_list(raw)
        assert result.canonical_id == "hunt_list:Sales-HuntList"
        state = result.pre_migration_state
        assert state["hunt_algorithm"] == "Top Down"
        assert state["line_groups"] == ["Sales-LG"]


class TestNormalizeLineGroup:
    def test_basic(self):
        raw = {
            "pkid": "{LG1}",
            "name": "Sales-LG",
            "rnaReversionTimeOut": "20",
            "distributionAlgorithm": "Top Down",
            "members": {"member": [{"directoryNumber": "1001"}]},
        }
        result = normalize_line_group(raw)
        assert result.canonical_id == "line_group:Sales-LG"
        state = result.pre_migration_state
        assert state["rna_reversion_timeout"] == "20"


class TestNormalizeCtiRoutePoint:
    def test_basic(self):
        raw = {
            "pkid": "{CTI1}",
            "name": "AA-MainMenu",
            "description": "Main Auto Attendant",
            "devicePoolName": {"_value_1": "DP-SanJose-Phones", "uuid": "{DP1}"},
            "callingSearchSpaceName": {"_value_1": "AA-CSS", "uuid": "{CSS1}"},
            "lines": {
                "line": [
                    {
                        "index": "1",
                        "dirn": {
                            "pattern": "9000",
                            "routePartitionName": {
                                "_value_1": "Internal-PT",
                                "uuid": "{PT1}",
                            },
                        },
                    }
                ]
            },
        }
        result = normalize_cti_route_point(raw)
        assert result.canonical_id == "cti_rp:AA-MainMenu"
        state = result.pre_migration_state
        assert state["cucm_device_pool"] == "DP-SanJose-Phones"
        assert len(state["lines"]) == 1
        assert state["lines"][0]["dn"] == "9000"


class TestNormalizeCallPark:
    def test_basic(self):
        raw = {
            "pkid": "{CP1}",
            "pattern": "7001",
            "description": "Park Slot 1",
            "routePartitionName": {"_value_1": "Internal-PT", "uuid": "{PT1}"},
        }
        result = normalize_call_park(raw)
        assert result.canonical_id == "call_park:7001:Internal-PT"


class TestNormalizePickupGroup:
    def test_basic(self):
        raw = {"pkid": "{PG1}", "name": "Sales-Pickup", "members": None}
        result = normalize_pickup_group(raw)
        assert result.canonical_id == "pickup_group:Sales-Pickup"

    def test_members_as_dicts_extracts_uuids(self):
        """CUCM AXL returns pickup group members as dicts with nested UUID refs."""
        raw = {
            "pkid": "{PG2}",
            "name": "Lobby-Pickup",
            "members": {
                "member": [
                    {"priority": 1, "pickupGroupLineMember": {"_value_1": "SEP001", "uuid": "{A1B2C3D4-0915-1718-87C7-AF59E74F0001}"}},
                    {"priority": 2, "pickupGroupLineMember": {"_value_1": "SEP002", "uuid": "{A1B2C3D4-0915-1718-87C7-AF59E74F0002}"}},
                ],
            },
        }
        result = normalize_pickup_group(raw)
        members = result.pre_migration_state["members"]
        assert len(members) == 2
        assert all(isinstance(m, str) for m in members), f"Expected strings, got {members}"
        assert "{A1B2C3D4-0915-1718-87C7-AF59E74F0001}" in members
        assert "{A1B2C3D4-0915-1718-87C7-AF59E74F0002}" in members

    def test_members_as_flat_list_of_dicts(self):
        """Extractor pre-flattens member list — dicts still need UUID extraction."""
        raw = {
            "pkid": "{PG3}",
            "name": "Eng-Pickup",
            "members": [
                {"priority": 1, "pickupGroupLineMember": {"_value_1": "Line1", "uuid": "{UUID-001}"}},
            ],
        }
        result = normalize_pickup_group(raw)
        members = result.pre_migration_state["members"]
        assert members == ["{UUID-001}"]

    def test_members_as_strings_pass_through(self):
        """Already-clean string members should pass through unchanged."""
        raw = {
            "pkid": "{PG4}",
            "name": "Clean-Pickup",
            "members": ["user:alice", "user:bob"],
        }
        result = normalize_pickup_group(raw)
        members = result.pre_migration_state["members"]
        assert members == ["user:alice", "user:bob"]


class TestNormalizeTimeSchedule:
    def test_basic(self):
        raw = {
            "pkid": "{TS1}",
            "name": "BusinessHours",
            "members": {
                "member": [
                    {"timePeriodName": {"_value_1": "Weekdays", "uuid": "{TP1}"}},
                    {"timePeriodName": {"_value_1": "Saturday", "uuid": "{TP2}"}},
                ]
            },
        }
        result = normalize_time_schedule(raw)
        assert result.canonical_id == "time_schedule:BusinessHours"
        state = result.pre_migration_state
        assert state["time_periods"] == ["Weekdays", "Saturday"]


class TestNormalizeTimePeriod:
    def test_basic(self):
        raw = {
            "pkid": "{TP1}",
            "name": "Weekdays",
            "startTime": "08:00",
            "endTime": "17:00",
            "dayOfWeek": "Mon-Fri",
        }
        result = normalize_time_period(raw)
        assert result.canonical_id == "time_period:Weekdays"
        state = result.pre_migration_state
        assert state["start_time"] == "08:00"
        assert state["day_of_week"] == "Mon-Fri"


class TestNormalizeGateway:
    def test_basic(self):
        raw = {
            "pkid": "{GW1}",
            "domainName": "gw01.acme.com",
            "description": "HQ Gateway",
            "product": "Cisco IOS Enhanced Gateway",
            "protocol": "H.323",
            "devicePoolName": {"_value_1": "DP-SanJose-Phones", "uuid": "{DP1}"},
        }
        result = normalize_gateway(raw)
        assert result.canonical_id == "gateway:gw01.acme.com"
        assert result.pre_migration_state["protocol"] == "H.323"


class TestNormalizeSipTrunk:
    def test_live_cucm_format(self):
        """Verified via live CUCM: destinations is a list of dicts."""
        raw = {
            "pkid": "{ST1}",
            "name": "SBC-Trunk-01",
            "maxNumCalls": "100",
            "devicePoolName": {"_value_1": "DP-SanJose-Phones", "uuid": "{DP1}"},
            "sipProfileName": {"_value_1": "Standard SIP", "uuid": "{SP1}"},
            "securityProfileName": {"_value_1": "TLS-Profile", "uuid": "{SEC1}"},
            "destinations": {
                "destination": [
                    {"addressIpv4": "10.1.1.1", "addressIpv6": None, "port": "5060", "sortOrder": "1"},
                    {"addressIpv4": "10.1.1.2", "addressIpv6": None, "port": "5060", "sortOrder": "2"},
                ],
            },
        }
        result = normalize_sip_trunk(raw)
        assert result.canonical_id == "sip_trunk:SBC-Trunk-01"
        state = result.pre_migration_state
        assert len(state["destinations"]) == 2
        assert state["destinations"][0]["address"] == "10.1.1.1"
        assert state["destinations"][1]["sort_order"] == "2"
        assert state["max_num_calls"] == "100"

    def test_flat_fallback(self):
        """Fallback: handle design-spec flat destinationAddress/destinationPort."""
        raw = {
            "pkid": "{ST1}",
            "name": "SBC-Trunk-01",
            "destinationAddress": "sbc.acme.com",
            "destinationPort": "5061",
            "devicePoolName": {"_value_1": "DP-SanJose-Phones", "uuid": "{DP1}"},
        }
        result = normalize_sip_trunk(raw)
        state = result.pre_migration_state
        assert len(state["destinations"]) == 1
        assert state["destinations"][0]["address"] == "sbc.acme.com"
        assert state["destinations"][0]["port"] == "5061"


class TestNormalizeRouteGroup:
    def test_basic(self):
        raw = {
            "pkid": "{RG1}",
            "name": "PSTN-RG",
            "description": "PSTN Route Group",
            "members": {
                "member": [
                    {"deviceName": {"_value_1": "SBC-Trunk-01", "uuid": "{ST1}"}},
                ]
            },
        }
        result = normalize_route_group(raw)
        assert result.canonical_id == "route_group:PSTN-RG"
        trunks = result.pre_migration_state["trunks"]
        assert len(trunks) == 1
        assert trunks[0]["trunk_name"] == "SBC-Trunk-01"


class TestNormalizeRouteList:
    def test_basic(self):
        raw = {
            "pkid": "{RL1}",
            "name": "PSTN-RL",
            "description": "PSTN Route List",
            "members": {
                "member": [
                    {"routeGroupName": {"_value_1": "PSTN-RG", "uuid": "{RG1}"}},
                ]
            },
        }
        result = normalize_route_list(raw)
        assert result.canonical_id == "route_list:PSTN-RL"
        assert result.pre_migration_state["route_groups"] == ["PSTN-RG"]


# ===================================================================
# Extractor-format fixtures (Phase 03 reconciliation)
# New normalizers (added during reconciliation)
# ===================================================================


class TestNormalizeVoicemailPilot:
    def test_basic(self):
        from wxcli.migration.transform.normalizers import normalize_voicemail_pilot
        raw = {"pkid": "{VP1}", "dirn": "8000", "description": "Main pilot"}
        result = normalize_voicemail_pilot(raw)
        assert result.canonical_id == "voicemail_pilot:8000"
        assert result.provenance.source_name == "8000"
        state = result.pre_migration_state
        assert state["dirn"] == "8000"
        assert state["uuid"] == "{VP1}"
        assert state["description"] == "Main pilot"

    def test_empty_dirn(self):
        from wxcli.migration.transform.normalizers import normalize_voicemail_pilot
        raw = {"pkid": "{VP2}", "dirn": "", "description": "Empty"}
        result = normalize_voicemail_pilot(raw)
        # Falls back to pkid for canonical_id when dirn is empty
        assert result.canonical_id == "voicemail_pilot:{VP2}"


class TestNormalizeCucmLocation:
    def test_basic(self):
        from wxcli.migration.transform.normalizers import normalize_cucm_location
        raw = {
            "pkid": "{LOC1}",
            "name": "HQ",
            "withinAudioBandwidth": None,
            "withinVideoBandwidth": None,
        }
        result = normalize_cucm_location(raw)
        assert result.canonical_id == "cucm_location:HQ"
        assert result.provenance.source_name == "HQ"
        assert result.pre_migration_state["cucm_location_name"] == "HQ"


class TestNormalizeUnityVmSettings:
    def test_basic(self):
        from wxcli.migration.transform.normalizers import normalize_unity_vm_settings
        settings = {
            "uc_object_id": "uc-obj-1",
            "vm_enabled": True,
            "call_handler_id": "ch-1",
            "notification_enabled": True,
            "notification_destination": "user@acme.com",
            "send_all_calls": False,
            "send_busy_calls": True,
            "send_unanswered_calls": True,
            "unanswered_rings": 4,
            "busy_greeting_type": "DEFAULT",
            "storage_type": "INTERNAL",
            "mwi_enabled": True,
            "external_email": None,
            "email_copy_enabled": False,
            "transfer_to_zero_enabled": True,
            "transfer_to_zero_destination": "0",
            "fax_enabled": False,
            "fax_number": None,
        }
        result = normalize_unity_vm_settings("jdoe", settings)
        assert result.canonical_id == "unity_vm:jdoe"
        assert result.provenance.source_system == "unity_connection"
        state = result.pre_migration_state
        assert state["userid"] == "jdoe"
        assert state["vm_enabled"] is True
        assert state["notification_destination"] == "user@acme.com"
        assert state["send_busy_calls"] is True
        assert state["transfer_to_zero_enabled"] is True
        assert state["fax_enabled"] is False

    def test_minimal_settings(self):
        from wxcli.migration.transform.normalizers import normalize_unity_vm_settings
        result = normalize_unity_vm_settings("sparse", {})
        assert result.canonical_id == "unity_vm:sparse"
        state = result.pre_migration_state
        assert state["vm_enabled"] is False
        assert state["notification_enabled"] is False


class TestProvenanceSourceName:
    """Verify source_name is populated for all normalizer types."""

    def test_user_source_name(self):
        result = normalize_user(END_USER_FIXTURE)
        assert result.provenance.source_name == "jdoe"

    def test_gateway_source_name(self):
        from wxcli.migration.transform.normalizers import normalize_gateway
        raw = {"pkid": "{GW1}", "domainName": "gw.acme.com"}
        result = normalize_gateway(raw)
        assert result.provenance.source_name == "gw.acme.com"

    def test_voicemail_pilot_source_name(self):
        from wxcli.migration.transform.normalizers import normalize_voicemail_pilot
        raw = {"pkid": "{VP1}", "dirn": "8000"}
        result = normalize_voicemail_pilot(raw)
        assert result.provenance.source_name == "8000"


# ===================================================================
# Extractors pre-normalize zeep lists via to_list() — flat lists,
# not nested dicts with wrapper keys.
# ===================================================================


class TestExtractorFormat:
    """Verify normalizers handle Phase 03 extractor output format."""

    def test_phone_flat_lines(self):
        """Extractor returns lines as flat list, not {'line': [...]}."""
        raw = {
            "pkid": "{PH-EXT}",
            "name": "SEP001122334455",
            "model": "Cisco 8845",
            "description": "Extractor format",
            "ownerUserName": {"_value_1": "jdoe", "uuid": "{U1}"},
            "devicePoolName": {"_value_1": "DP-HQ", "uuid": "{DP1}"},
            "protocol": "SIP",
            "product": "Cisco 8845",
            "class": "Phone",
            # Extractor format: flat list
            "lines": [
                {
                    "index": 1,  # int not str (finding #2)
                    "label": "John Doe",
                    "display": "John Doe",
                    "e164Mask": None,
                    "associatedEndusers": ["jdoe"],  # flat string list
                    "dirn": {
                        "pattern": "1001",
                        "routePartitionName": {
                            "_value_1": "Internal-PT",
                            "uuid": "{PT1}",
                        },
                        "alertingName": "John Doe",
                        "description": "Ext 1001",
                        "shareLineAppearanceCssName": None,
                        "callingSearchSpaceName": None,
                    },
                },
            ],
        }
        result = normalize_phone(raw)
        assert len(result.line_appearances) == 1
        assert result.line_appearances[0]["dn"] == "1001"
        assert result.line_appearances[0]["associated_endusers"] == ["jdoe"]
        assert result.line_appearances[0]["line_index"] == 1

    def test_css_flat_members(self):
        """Extractor returns CSS members as flat list."""
        raw = {
            "pkid": "{CSS-EXT}",
            "name": "Employee-CSS",
            "description": "Test",
            # Extractor format: flat list
            "members": [
                {
                    "routePartitionName": {
                        "_value_1": "Internal-PT",
                        "uuid": "{PT1}",
                    },
                    "index": "1",
                },
                {
                    "routePartitionName": {
                        "_value_1": "PSTN-PT",
                        "uuid": "{PT2}",
                    },
                    "index": "2",
                },
            ],
        }
        result = normalize_css(raw)
        parts = result.pre_migration_state["partitions"]
        assert len(parts) == 2
        assert parts[0]["partition_name"] == "Internal-PT"
        assert parts[1]["partition_name"] == "PSTN-PT"

    def test_user_flat_devices(self):
        """Extractor returns associatedDevices as flat list."""
        raw = {
            **END_USER_FIXTURE,
            "associatedDevices": ["SEP001122334455", "CSFJDOE"],
        }
        result = normalize_user(raw)
        assert result.pre_migration_state["associated_devices"] == [
            "SEP001122334455", "CSFJDOE"
        ]

    def test_sip_trunk_flat_destinations(self):
        """Extractor returns destinations as flat list."""
        raw = {
            "pkid": "{ST-EXT}",
            "name": "Trunk-01",
            "devicePoolName": {"_value_1": "DP-HQ", "uuid": "{DP1}"},
            # Extractor format: flat list
            "destinations": [
                {"addressIpv4": "10.1.1.1", "port": "5060", "sortOrder": "1"},
                {"addressIpv4": "10.1.1.2", "port": "5060", "sortOrder": "2"},
            ],
        }
        result = normalize_sip_trunk(raw)
        dests = result.pre_migration_state["destinations"]
        assert len(dests) == 2
        assert dests[0]["address"] == "10.1.1.1"

    def test_hunt_list_with_user_or_device_name(self):
        """Extractor uses userOrDeviceName, not lineGroupName."""
        raw = {
            "pkid": "{HL-EXT}",
            "name": "Sales-HL",
            "members": [
                {
                    "userOrDeviceName": {
                        "_value_1": "Sales-LG",
                        "uuid": "{LG1}",
                    },
                    "index": "1",
                },
            ],
        }
        result = normalize_hunt_list(raw)
        assert result.pre_migration_state["line_groups"] == ["Sales-LG"]

    def test_route_group_with_sip_trunk_name(self):
        """Extractor uses sipTrunkName, not deviceName."""
        raw = {
            "pkid": "{RG-EXT}",
            "name": "PSTN-RG",
            "members": [
                {
                    "sipTrunkName": {
                        "_value_1": "SBC-Trunk",
                        "uuid": "{ST1}",
                    },
                    "index": "1",
                },
            ],
        }
        result = normalize_route_group(raw)
        trunks = result.pre_migration_state["trunks"]
        assert len(trunks) == 1
        assert trunks[0]["trunk_name"] == "SBC-Trunk"

    def test_empty_ref_value_none(self):
        """Empty refs are {'_value_1': None, 'uuid': None}, not plain None."""
        raw = {
            **PHONE_FIXTURE,
            "callingSearchSpaceName": {"_value_1": None, "uuid": None},
            "ownerUserName": {"_value_1": None, "uuid": None},
        }
        result = normalize_phone(raw)
        assert result.pre_migration_state["cucm_css"] is None
        assert result.pre_migration_state["cucm_owner_user"] is None


# ===================================================================
# Registry
# ===================================================================


class TestNormalizerRegistry:
    def test_all_normalizers_registered(self):
        expected_types = {
            "device_pool", "datetime_group", "cucm_location",
            "user", "phone", "workspace",
            "css", "partition", "route_pattern", "translation_pattern",
            "hunt_pilot", "hunt_list", "line_group", "cti_route_point",
            "call_park", "pickup_group", "time_schedule", "time_period",
            "gateway", "sip_trunk", "route_group", "route_list",
            "voicemail_profile", "voicemail_pilot",
            "button_template", "softkey_template",
            "remote_destination",
            "elin_group", "geo_location",
            "device_profile",
            "moh_source", "announcement",
            # Tier 3: Informational types
            "info_region", "info_srst", "info_media_resource_group",
            "info_media_resource_list", "info_aar_group",
            "info_device_mobility_group", "info_conference_bridge",
            "info_softkey_template", "info_ip_phone_service", "info_intercom",
            "info_common_phone_config", "info_phone_button_template",
            "info_feature_control_policy", "info_credential_policy",
            "info_recording_profile", "info_ldap_directory",
            "info_app_user", "info_h323_gateway",
            "info_enterprise_params", "info_service_params",
            # Tier 4: Feature gap normalizers
            "recording_profile", "calling_party_xform",
            "called_party_xform", "info_device_profile",
            "intercept_candidate",
            # Executive/Assistant
            "executive_assistant_pair", "executive_settings",
            # Unity Connection shared mailboxes
            "voicemail_group",
        }
        assert set(NORMALIZER_REGISTRY.keys()) == expected_types

    def test_all_normalizers_callable(self):
        for name, fn in NORMALIZER_REGISTRY.items():
            assert callable(fn), f"{name} is not callable"


# ===================================================================
# normalize_dect_group — post-normalization grouping
# ===================================================================


class TestNormalizeDectGroup:
    """Spec §5b: normalize_dect_group() groups DECT handsets by device pool."""

    def _make_dect_device(self, name: str, pool: str, cluster: str = "lab") -> CanonicalDevice:
        from datetime import datetime, timezone
        from wxcli.migration.models import DeviceCompatibilityTier, Provenance
        return CanonicalDevice(
            canonical_id=f"device:{name}",
            provenance=Provenance(
                source_system="cucm",
                source_id=f"pk-{name}",
                source_name=name,
                cluster=cluster,
                extracted_at=datetime.now(timezone.utc),
            ),
            status=MigrationStatus.NORMALIZED,
            model="Cisco 6823",
            compatibility_tier=DeviceCompatibilityTier.DECT,
            cucm_device_name=name,
            pre_migration_state={"cucm_device_pool": pool},
        )

    def _make_non_dect_device(self, name: str, pool: str) -> CanonicalDevice:
        from datetime import datetime, timezone
        from wxcli.migration.models import DeviceCompatibilityTier, Provenance
        return CanonicalDevice(
            canonical_id=f"device:{name}",
            provenance=Provenance(
                source_system="cucm",
                source_id=f"pk-{name}",
                source_name=name,
                cluster="lab",
                extracted_at=datetime.now(timezone.utc),
            ),
            status=MigrationStatus.NORMALIZED,
            model="Cisco 8845",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
            cucm_device_name=name,
            pre_migration_state={"cucm_device_pool": pool},
        )

    def test_normalize_dect_group_creates_networks(self):
        """Spec §10b test 1: 5 DECT in DP-Warehouse + 3 in DP-Lobby → 2 networks."""
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.transform.normalizers import normalize_dect_group

        store = MigrationStore(":memory:")
        for i in range(5):
            store.upsert_object(self._make_dect_device(f"DECT-WH-{i}", "DP-Warehouse"))
        for i in range(3):
            store.upsert_object(self._make_dect_device(f"DECT-LB-{i}", "DP-Lobby"))

        networks = normalize_dect_group(store)

        assert len(networks) == 2
        pool_names = {n.pre_migration_state["cucm_device_pool"] for n in networks}
        assert pool_names == {"DP-Warehouse", "DP-Lobby"}

    def test_normalize_dect_group_empty_when_no_dect(self):
        """Spec §10b test 2: no DECT devices → empty list."""
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.transform.normalizers import normalize_dect_group

        store = MigrationStore(":memory:")
        # Add only non-DECT devices
        for i in range(3):
            store.upsert_object(self._make_non_dect_device(f"SEP-MPP-{i}", "DP-Lobby"))

        networks = normalize_dect_group(store)

        assert networks == []

    def test_normalize_dect_group_handset_assignments(self):
        """Spec §10b test 3: each network has correct handset_assignments list."""
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.models import CanonicalDECTNetwork
        from wxcli.migration.transform.normalizers import normalize_dect_group

        store = MigrationStore(":memory:")
        device_names = ["DECT-WH-0", "DECT-WH-1", "DECT-WH-2"]
        for name in device_names:
            store.upsert_object(self._make_dect_device(name, "DP-Warehouse"))

        networks = normalize_dect_group(store)

        assert len(networks) == 1
        network = networks[0]
        assert isinstance(network, CanonicalDECTNetwork)
        assert len(network.handset_assignments) == 3
        assigned_device_ids = {a["device_canonical_id"] for a in network.handset_assignments}
        assert assigned_device_ids == {f"device:{n}" for n in device_names}
        # Verify network is also persisted in the store
        stored = store.get_object("dect_network:DP-Warehouse")
        assert stored is not None
        assert stored["pre_migration_state"]["handset_count"] == 3
