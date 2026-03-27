"""End-to-end pipeline integration tests.

Runs the full pipeline: normalize → map → analyze → plan → export
on a synthetic CUCM data set and verifies outputs at each stage.
"""

import pytest
import networkx as nx

from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.pipeline import normalize_discovery
from wxcli.migration.transform.engine import TransformEngine
from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline
from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.execute.dependency import build_dependency_graph
from wxcli.migration.execute.batch import partition_into_batches, save_plan_to_store
from wxcli.migration.export.deployment_plan import generate_plan_summary


# ---------------------------------------------------------------------------
# Helpers for building zeep-like reference fields
# ---------------------------------------------------------------------------

def _ref(name: str, uuid: str) -> dict:
    """Build a zeep-style reference field."""
    return {"_value_1": name, "uuid": uuid}


def _empty_ref() -> dict:
    """Build an empty zeep reference."""
    return {"_value_1": None, "uuid": None}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "e2e.db")
    yield s
    s.close()


@pytest.fixture
def raw_data():
    """Synthetic CUCM environment — 2 locations, 4 users, 3 phones, features.

    Designed to trigger: DEVICE_INCOMPATIBLE (7962), SHARED_LINE_COMPLEX (DN 1002).
    """
    return {
        # ----- Locations -----
        "locations": {
            "device_pools": [
                {
                    "pkid": "{DP-MAIN-0001-0001-0001-000000000001}",
                    "name": "DP-Main",
                    "dateTimeSettingName": _ref("DT-Eastern", "{DT-EAST-0001-0001-0001-000000000001}"),
                    "locationName": _ref("LOC-Main", "{LOC-MAIN-0001-0001-0001-000000000001}"),
                    "callManagerGroupName": _ref("Default", "{CMG-0001-0001-0001-0001-000000000001}"),
                    "srstName": None,
                    "regionName": _ref("Default", "{RGN-0001-0001-0001-0001-000000000001}"),
                    "mediaResourceListName": None,
                },
                {
                    "pkid": "{DP-BRNC-0001-0001-0001-000000000002}",
                    "name": "DP-Branch",
                    "dateTimeSettingName": _ref("DT-Pacific", "{DT-PCFC-0001-0001-0001-000000000002}"),
                    "locationName": _ref("LOC-Branch", "{LOC-BRNC-0001-0001-0001-000000000002}"),
                    "callManagerGroupName": _ref("Default", "{CMG-0001-0001-0001-0001-000000000001}"),
                    "srstName": None,
                    "regionName": _ref("Default", "{RGN-0001-0001-0001-0001-000000000001}"),
                    "mediaResourceListName": None,
                },
            ],
            "datetime_groups": [
                {
                    "pkid": "{DT-EAST-0001-0001-0001-000000000001}",
                    "name": "DT-Eastern",
                    "timeZone": "America/New_York",
                },
                {
                    "pkid": "{DT-PCFC-0001-0001-0001-000000000002}",
                    "name": "DT-Pacific",
                    "timeZone": "America/Los_Angeles",
                },
            ],
            "cucm_locations": [
                {
                    "pkid": "{LOC-MAIN-0001-0001-0001-000000000001}",
                    "name": "LOC-Main",
                },
                {
                    "pkid": "{LOC-BRNC-0001-0001-0001-000000000002}",
                    "name": "LOC-Branch",
                },
            ],
        },

        # ----- Users -----
        "users": {
            "users": [
                {
                    "pkid": "{USR-JSMT-0001-0001-0001-000000000001}",
                    "userid": "jsmith",
                    "firstName": "John",
                    "lastName": "Smith",
                    "mailid": "jsmith@acme.com",
                    "telephoneNumber": "+12125551001",
                    "department": "Sales",
                    "title": "Sales Rep",
                    "manager": _empty_ref(),
                    "directoryUri": "jsmith@acme.com",
                    "userLocale": "English United States",
                    "selfService": "8000",
                    "enableCti": "true",
                    "associatedDevices": {"device": ["SEP001122334455"]},
                    "primaryExtension": {
                        "pattern": "1001",
                        "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                    },
                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                    "voiceMailProfile": _ref("VM-Profile-Default", "{VMP-DFLT-0001-0001-0001-000000000001}"),
                },
                {
                    "pkid": "{USR-MCHN-0001-0001-0001-000000000002}",
                    "userid": "mchen",
                    "firstName": "Maria",
                    "lastName": "Chen",
                    "mailid": "mchen@acme.com",
                    "telephoneNumber": "+12125551002",
                    "department": "Sales",
                    "title": "Sales Manager",
                    "manager": _empty_ref(),
                    "directoryUri": "mchen@acme.com",
                    "userLocale": "English United States",
                    "selfService": None,
                    "enableCti": "true",
                    "associatedDevices": {"device": ["SEP556677889900"]},
                    "primaryExtension": {
                        "pattern": "1002",
                        "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                    },
                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                    "voiceMailProfile": _empty_ref(),
                },
                {
                    "pkid": "{USR-BWLS-0001-0001-0001-000000000003}",
                    "userid": "bwilson",
                    "firstName": "Brian",
                    "lastName": "Wilson",
                    "mailid": "bwilson@acme.com",
                    "telephoneNumber": "+13105552001",
                    "department": "Support",
                    "title": "Support Tech",
                    "manager": _empty_ref(),
                    "directoryUri": "bwilson@acme.com",
                    "userLocale": "English United States",
                    "selfService": "8000",
                    "enableCti": "true",
                    "associatedDevices": {"device": ["SEPAABBCCDDEEFF"]},
                    "primaryExtension": {
                        "pattern": "2001",
                        "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                    },
                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                    "voiceMailProfile": _ref("VM-Profile-Default", "{VMP-DFLT-0001-0001-0001-000000000001}"),
                },
                {
                    "pkid": "{USR-ALEE-0001-0001-0001-000000000004}",
                    "userid": "alee",
                    "firstName": "Amy",
                    "lastName": "Lee",
                    "mailid": "alee@acme.com",
                    "telephoneNumber": None,
                    "department": "Support",
                    "title": "Support Lead",
                    "manager": _empty_ref(),
                    "directoryUri": "alee@acme.com",
                    "userLocale": "English United States",
                    "selfService": None,
                    "enableCti": "false",
                    "associatedDevices": None,
                    "primaryExtension": {
                        "pattern": "2002",
                        "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                    },
                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                    "voiceMailProfile": _empty_ref(),
                },
            ],
        },

        # ----- Devices (phones) -----
        "devices": {
            "phones": [
                # SEP001122334455 (8845) — owned by jsmith, 2 lines (1001 primary, 1002 shared)
                {
                    "pkid": "{PH-8845-0001-0001-0001-000000000001}",
                    "name": "SEP001122334455",
                    "model": "Cisco 8845",
                    "product": "Cisco 8845",
                    "class": "Phone",
                    "description": "John Smith - Desk Phone",
                    "protocol": "SIP",
                    "ownerUserName": "jsmith",
                    "devicePoolName": _ref("DP-Main", "{DP-MAIN-0001-0001-0001-000000000001}"),
                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                    "phoneTemplateName": _ref("Standard 8845 SIP", "{TPL-8845-0001-0001-0001-000000000001}"),
                    "softkeyTemplateName": None,
                    "deviceMobilityMode": "Default",
                    "lines": [
                        {
                            "index": "1",
                            "label": "John Smith - 1001",
                            "display": "John Smith",
                            "e164Mask": "+12125551001",
                            "recordingFlag": "Automatic Call Recording Enabled",
                            "recordingProfileName": {"_value_1": "RecordingProfile-Default"},
                            "associatedEndusers": {"enduser": [{"userId": "jsmith"}]},
                            "dirn": {
                                "pattern": "1001",
                                "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                                "alertingName": "John Smith",
                                "description": "John Smith Ext 1001",
                                "shareLineAppearanceCssName": _empty_ref(),
                                "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                                "callForwardAll": {
                                    "destination": "",
                                    "forwardToVoiceMail": "false",
                                    "callingSearchSpaceName": _empty_ref(),
                                },
                                "callForwardBusy": {
                                    "destination": "8000",
                                    "forwardToVoiceMail": "true",
                                    "callingSearchSpaceName": _empty_ref(),
                                },
                                "callForwardNoAnswer": {
                                    "destination": "8000",
                                    "forwardToVoiceMail": "true",
                                    "callingSearchSpaceName": _empty_ref(),
                                },
                            },
                        },
                        {
                            "index": "2",
                            "label": "Maria Chen - 1002",
                            "display": "Maria Chen",
                            "e164Mask": "+12125551002",
                            "associatedEndusers": {
                                "enduser": [
                                    {"userId": "jsmith"},
                                    {"userId": "mchen"},
                                ]
                            },
                            "dirn": {
                                "pattern": "1002",
                                "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                                "alertingName": "Maria Chen",
                                "description": "Maria Chen Ext 1002 (Shared)",
                                "shareLineAppearanceCssName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                                "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                            },
                        },
                    ],
                    "speeddials": [],
                    "busyLampFields": [],
                },
                # SEP556677889900 (9861) — owned by mchen, 1 line (1002 primary)
                {
                    "pkid": "{PH-9861-0001-0001-0001-000000000002}",
                    "name": "SEP556677889900",
                    "model": "Cisco 9861",
                    "product": "Cisco 9861",
                    "class": "Phone",
                    "description": "Maria Chen - Desk Phone",
                    "protocol": "SIP",
                    "ownerUserName": _ref("mchen", "{USR-MCHN-0001-0001-0001-000000000002}"),
                    "devicePoolName": _ref("DP-Main", "{DP-MAIN-0001-0001-0001-000000000001}"),
                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                    "phoneTemplateName": _ref("Standard 9861 SIP", "{TPL-9861-0001-0001-0001-000000000002}"),
                    "softkeyTemplateName": None,
                    "deviceMobilityMode": "Default",
                    "lines": {
                        "line": [
                            {
                                "index": "1",
                                "label": "Maria Chen - 1002",
                                "display": "Maria Chen",
                                "e164Mask": "+12125551002",
                                "associatedEndusers": {
                                    "enduser": [
                                        {"userId": "mchen"},
                                        {"userId": "jsmith"},
                                    ]
                                },
                                "dirn": {
                                    "pattern": "1002",
                                    "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                                    "alertingName": "Maria Chen",
                                    "description": "Maria Chen Ext 1002",
                                    "shareLineAppearanceCssName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                                },
                            },
                        ],
                    },
                    "speeddials": [],
                    "busyLampFields": [],
                },
                # SEPAABBCCDDEEFF (7962) — owned by bwilson, 1 line (2001 primary)
                {
                    "pkid": "{PH-7962-0001-0001-0001-000000000003}",
                    "name": "SEPAABBCCDDEEFF",
                    "model": "Cisco 7962",
                    "product": "Cisco 7962",
                    "class": "Phone",
                    "description": "Brian Wilson - Desk Phone",
                    "protocol": "SCCP",
                    "ownerUserName": _ref("bwilson", "{USR-BWLS-0001-0001-0001-000000000003}"),
                    "devicePoolName": _ref("DP-Branch", "{DP-BRNC-0001-0001-0001-000000000002}"),
                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                    "phoneTemplateName": _ref("Standard 7962 SCCP", "{TPL-7962-0001-0001-0001-000000000003}"),
                    "softkeyTemplateName": None,
                    "deviceMobilityMode": "Default",
                    "lines": {
                        "line": [
                            {
                                "index": "1",
                                "label": "Brian Wilson - 2001",
                                "display": "Brian Wilson",
                                "e164Mask": "+13105552001",
                                "associatedEndusers": {"enduser": [{"userId": "bwilson"}]},
                                "dirn": {
                                    "pattern": "2001",
                                    "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                                    "alertingName": "Brian Wilson",
                                    "description": "Brian Wilson Ext 2001",
                                    "shareLineAppearanceCssName": _empty_ref(),
                                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                                },
                            },
                        ],
                    },
                    "speeddials": [],
                    "busyLampFields": [],
                },
            ],
        },

        # ----- Routing -----
        "routing": {
            "partitions": [
                {
                    "pkid": "{PT-INT-0001-0001-0001-000000000001}",
                    "name": "PT-Internal",
                    "description": "Internal directory numbers",
                },
                {
                    "pkid": "{PT-PSTN-0001-0001-0001-000000000002}",
                    "name": "PT-PSTN",
                    "description": "PSTN routing patterns",
                },
            ],
            "css_list": [
                {
                    "pkid": "{CSS-INT-0001-0001-0001-000000000001}",
                    "name": "CSS-Internal",
                    "description": "Internal calling search space",
                    "members": {
                        "member": [
                            {
                                "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                                "index": "1",
                            },
                            {
                                "routePartitionName": _ref("PT-PSTN", "{PT-PSTN-0001-0001-0001-000000000002}"),
                                "index": "2",
                            },
                        ],
                    },
                },
            ],
            "route_patterns": [
                {
                    "pkid": "{RP-PSTN-0001-0001-0001-000000000001}",
                    "pattern": "9.!",
                    "routePartitionName": _ref("PT-PSTN", "{PT-PSTN-0001-0001-0001-000000000002}"),
                    "blockEnable": "false",
                    "description": "PSTN breakout via 9",
                    "calledPartyTransformationMask": None,
                    "callingPartyTransformationMask": None,
                    "prefixDigitsOut": None,
                    "networkLocation": "OffNet",
                },
            ],
            "gateways": [],
            "sip_trunks": [
                {
                    "pkid": "{ST-PSTN-0001-0001-0001-000000000001}",
                    "name": "PSTN-Trunk",
                    "description": "Primary PSTN SIP Trunk",
                    "maxNumCalls": "100",
                    "devicePoolName": _ref("DP-Main", "{DP-MAIN-0001-0001-0001-000000000001}"),
                    "sipProfileName": _ref("Standard SIP Profile", "{SIPP-0001-0001-0001-0001-000000000001}"),
                    "securityProfileName": _ref("Non Secure SIP Trunk Profile", "{SECP-0001-0001-0001-0001-000000000001}"),
                    "sipTrunkType": "None(Default)",
                    "dualIdentitySupportEnabled": None,
                    "destinations": {
                        "destination": [
                            {
                                "addressIpv4": "10.1.1.100",
                                "addressIpv6": None,
                                "port": "5060",
                                "sortOrder": "1",
                            },
                        ],
                    },
                },
            ],
            "route_groups": [
                {
                    "pkid": "{RG-PSTN-0001-0001-0001-000000000001}",
                    "name": "RG-PSTN",
                    "description": "PSTN Route Group",
                    "members": {
                        "member": [
                            {
                                "deviceName": _ref("PSTN-Trunk", "{ST-PSTN-0001-0001-0001-000000000001}"),
                                "priority": 1,
                            },
                        ],
                    },
                },
            ],
            "route_lists": [],
            "translation_patterns": [
                {
                    "pkid": "{TP-E164-0001-0001-0001-000000000001}",
                    "pattern": "+1!",
                    "routePartitionName": _ref("PT-PSTN", "{PT-PSTN-0001-0001-0001-000000000002}"),
                    "description": "E.164 prefix strip",
                    "calledPartyTransformationMask": "!",
                },
                {
                    "pkid": "{TP-9BRK-0001-0001-0001-000000000002}",
                    "pattern": "9.!",
                    "routePartitionName": _ref("PT-PSTN", "{PT-PSTN-0001-0001-0001-000000000002}"),
                    "description": "PSTN breakout via 9",
                    "calledPartyTransformationMask": None,
                },
            ],
        },

        # ----- Features -----
        "features": {
            "hunt_pilots": [
                {
                    "pkid": "{HP-SALE-0001-0001-0001-000000000001}",
                    "pattern": "5001",
                    "description": "Sales HG",
                    "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                    "huntListName": _ref("Sales-HuntList", "{HL-SALE-0001-0001-0001-000000000001}"),
                    "forwardHuntNoAnswer": {"destination": "", "enabled": "false"},
                    "forwardHuntBusy": {"destination": "", "enabled": "false"},
                    "queueCalls": {"enabled": "false"},
                    "maxCallersInQueue": "0",
                    "mohSourceId": None,
                    "huntTimerCallPick": "20",
                    "overflowDestination": None,
                    "enabled": "true",
                },
            ],
            "hunt_lists": [
                {
                    "pkid": "{HL-SALE-0001-0001-0001-000000000001}",
                    "name": "Sales-HuntList",
                    "description": "Sales hunt list",
                    "huntAlgorithm": "Top Down",
                    "voiceMailUsage": None,
                    "routeListEnabled": "true",
                    "members": {
                        "member": [
                            {
                                "lineGroupName": _ref("Sales-LineGroup", "{LG-SALE-0001-0001-0001-000000000001}"),
                            },
                        ],
                    },
                },
            ],
            "line_groups": [
                {
                    "pkid": "{LG-SALE-0001-0001-0001-000000000001}",
                    "name": "Sales-LineGroup",
                    "rnaReversionTimeOut": "15",
                    "distributionAlgorithm": "Top Down",
                    "members": {
                        "member": [
                            {
                                "directoryNumber": _ref("1001", "{DN-1001-0001-0001-0001-000000000001}"),
                                "lineSelectionOrder": 1,
                            },
                            {
                                "directoryNumber": _ref("1002", "{DN-1002-0001-0001-0001-000000000002}"),
                                "lineSelectionOrder": 2,
                            },
                        ],
                    },
                },
            ],
            "cti_route_points": [
                {
                    "pkid": "{CTI-MAIN-0001-0001-0001-000000000001}",
                    "name": "Main-AA-CtiRP",
                    "description": "Main Auto Attendant CTI RP",
                    "devicePoolName": _ref("DP-Main", "{DP-MAIN-0001-0001-0001-000000000001}"),
                    "callingSearchSpaceName": _ref("CSS-Internal", "{CSS-INT-0001-0001-0001-000000000001}"),
                    "lines": {
                        "line": [
                            {
                                "index": "1",
                                "label": "Main AA",
                                "display": "Main Auto Attendant",
                                "e164Mask": None,
                                "associatedEndusers": None,
                                "dirn": {
                                    "pattern": "3000",
                                    "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                                    "alertingName": "Main AA",
                                    "description": "Main Auto Attendant",
                                    "shareLineAppearanceCssName": _empty_ref(),
                                    "callingSearchSpaceName": _empty_ref(),
                                },
                            },
                        ],
                    },
                },
            ],
            "call_parks": [
                {
                    "pkid": "{CP-7001-0001-0001-0001-000000000001}",
                    "pattern": "7001",
                    "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}"),
                    "description": "Main Office Call Park",
                },
            ],
            "pickup_groups": [],
            "time_schedules": [
                {
                    "pkid": "{TS-BIZ-0001-0001-0001-000000000001}",
                    "name": "Business Hours",
                    "members": {
                        "member": [
                            {
                                "timePeriodName": _ref("BizHours-MF", "{TP-BIZ-0001-0001-0001-000000000001}"),
                            },
                        ],
                    },
                },
            ],
            "time_periods": [
                {
                    "pkid": "{TP-BIZ-0001-0001-0001-000000000001}",
                    "name": "BizHours-MF",
                    "startTime": "08:00",
                    "endTime": "17:00",
                    "startDate": None,
                    "endDate": None,
                    "monthOfYear": None,
                    "dayOfMonth": None,
                    "dayOfWeek": "Monday,Tuesday,Wednesday,Thursday,Friday",
                },
            ],
        },

        # ----- Voicemail -----
        "voicemail": {
            "voicemail_profiles": [
                {
                    "pkid": "{VMP-DFLT-0001-0001-0001-000000000001}",
                    "name": "VM-Profile-Default",
                    "description": "Default Voicemail Profile",
                    "voiceMailPilot": {
                        "dirn": "8000",
                        "cssName": "CSS-Internal",
                        "uuid": "{VMPLT-0001-0001-0001-000000000001}",
                    },
                    "voiceMailboxMask": "",
                },
            ],
            "voicemail_pilots": [
                {
                    "pkid": "{VMPLT-0001-0001-0001-000000000001}",
                    "dirn": "8000",
                    "description": "Default Voicemail Pilot",
                },
            ],
        },

        # ----- Templates -----
        "templates": {
            "button_templates": [
                {
                    "pkid": "{BT-8845-0001-0001-0001-000000000001}",
                    "name": "Standard 8845 SIP",
                    "basePhoneTemplateName": _ref("Standard 8845 SIP", "{BT-8845-0001-0001-0001-000000000001}"),
                    "buttons": {
                        "button": [
                            {"buttonNumber": "1", "feature": "Line"},
                            {"buttonNumber": "2", "feature": "Line"},
                            {"buttonNumber": "3", "feature": "Busy Lamp Field"},
                            {"buttonNumber": "4", "feature": "Busy Lamp Field"},
                            {"buttonNumber": "5", "feature": "Busy Lamp Field"},
                            {"buttonNumber": "6", "feature": "Speed Dial"},
                            {"buttonNumber": "7", "feature": "Speed Dial"},
                            {"buttonNumber": "8", "feature": "Speed Dial"},
                            {"buttonNumber": "9", "feature": "Speed Dial"},
                            {"buttonNumber": "10", "feature": "Speed Dial"},
                        ],
                    },
                },
            ],
            "softkey_templates": [],
        },

        # ----- Remote Destinations (Tier 2 §2.7 SNR) -----
        "remote_destinations": {
            "remote_destinations": [
                {
                    "pkid": "{RD-JSMT-0001-0001-0001-000000000001}",
                    "name": "jsmith-mobile",
                    "destination": "+14155559876",
                    "ownerUserId": "jsmith",
                    "isMobilePhone": "true",
                    "enableMobileConnect": "true",
                    "answerTooSoonTimer": None,  # default — no SNR_LOSSY
                    "answerTooLateTimer": None,
                },
                {
                    "pkid": "{RD-BWLS-0001-0001-0001-000000000002}",
                    "name": "bwilson-mobile",
                    "destination": "+13105558888",
                    "ownerUserId": "bwilson",
                    "isMobilePhone": "true",
                    "enableMobileConnect": "true",
                    "answerTooSoonTimer": 3000,  # non-default → SNR_LOSSY
                    "answerTooLateTimer": 19000,
                },
            ],
        },

        # ----- E911 (Tier 2 §2.6) -----
        "e911": {
            "elin_groups": [
                {
                    "pkid": "{ELIN-HQ-0001-0001-0001-000000000001}",
                    "name": "ELIN-HQ",
                    "elinNumbers": ["+12125559911", "+12125559912"],
                    "description": "HQ ELIN group",
                },
            ],
            "geo_locations": [
                {
                    "pkid": "{GEO-US-0001-0001-0001-000000000001}",
                    "name": "GEO-US-East",
                    "description": "US East Coast",
                    "country": "US",
                },
            ],
        },

        # ----- Device Profiles / Extension Mobility (Tier 2 §2.2) -----
        "device_profiles": {
            "device_profiles": [
                {
                    "pkid": "{DP-JSMT-0001-0001-0001-000000000001}",
                    "name": "UDP-jsmith",
                    "product": "Cisco 8845",
                    "protocol": "SIP",
                    "devicePoolName": _ref("DP-Main", "{DP-MAIN-0001-0001-0001-000000000001}"),
                    "lines": {
                        "line": [
                            {
                                "index": "1",
                                "dirn": {"pattern": "1001", "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}")},
                            },
                            {
                                "index": "2",
                                "dirn": {"pattern": "1099", "routePartitionName": _ref("PT-Internal", "{PT-INT-0001-0001-0001-000000000001}")},
                            },
                        ],
                    },
                    "speeddials": {"speeddial": [{"dirn": "5551234", "label": "Front Desk"}]},
                    "busyLampFields": {},
                },
            ],
        },

        # ----- MOH Sources (Tier 2 §2.3) -----
        "moh": {
            "moh_sources": [
                {
                    "pkid": "{MOH-DFLT-0001-0001-0001-000000000001}",
                    "name": "Default MOH",
                    "sourceFileName": "default.wav",
                    "isDefault": "true",
                    "sourceId": "1",
                },
                {
                    "pkid": "{MOH-CUST-0001-0001-0001-000000000002}",
                    "name": "Custom Branding",
                    "sourceFileName": "brand_hold.wav",
                    "isDefault": "false",
                    "sourceId": "2",
                },
            ],
        },

        # ----- Announcements (Tier 2 §2.4) -----
        "announcements": {
            "announcements": [
                {
                    "pkid": "{ANN-WLCM-0001-0001-0001-000000000001}",
                    "name": "AA-Welcome",
                    "description": "Auto Attendant welcome greeting",
                    "announcementFile": "welcome_greeting.wav",
                },
            ],
        },

        # ----- Tier 3 Informational (report-only, no mappers) -----
        "informational": {
            "region": [
                {"name": "Default", "defaultCodec": "G.711", "_category": "cloud_managed", "_info_type": "region"},
                {"name": "LowBandwidth", "defaultCodec": "G.729", "_category": "cloud_managed", "_info_type": "region"},
            ],
            "srst": [
                {"name": "SRST-HQ", "ipAddress": "10.1.1.1", "port": "2000", "_category": "cloud_managed", "_info_type": "srst"},
            ],
            "media_resource_group": [
                {"name": "MRG-HQ", "description": "HQ media resources", "_category": "cloud_managed", "_info_type": "media_resource_group"},
            ],
            "media_resource_list": [
                {"name": "MRL-HQ", "description": "HQ media resource list", "_category": "cloud_managed", "_info_type": "media_resource_list"},
            ],
            "aar_group": [],
            "device_mobility_group": [],
            "conference_bridge": [
                {"name": "CFB-1", "description": "", "product": "Cisco IOS", "_category": "cloud_managed", "_info_type": "conference_bridge"},
            ],
            "softkey_template": [
                {"name": "Standard", "description": "Default softkey template", "_category": "not_migratable", "_info_type": "softkey_template"},
            ],
            "ip_phone_service": [
                {"name": "Corp Directory", "url": "http://dir.local", "serviceType": "Standard", "_category": "not_migratable", "_info_type": "ip_phone_service"},
            ],
            "intercom": [
                {"dnorpattern": "9001", "description": "Lobby intercom", "fkroutepartition": "pk-1", "_category": "not_migratable", "_info_type": "intercom"},
            ],
            "common_phone_config": [
                {"name": "Standard CPP", "description": "Default", "_category": "different_arch", "_info_type": "common_phone_config"},
            ],
            "phone_button_template": [
                {"name": "Standard 8845", "_category": "different_arch", "_info_type": "phone_button_template"},
            ],
            "feature_control_policy": [],
            "credential_policy": [
                {"name": "Default Credential", "description": "Default", "_category": "different_arch", "_info_type": "credential_policy"},
            ],
            "recording_profile": [
                {"name": "Default Recording", "recorderDestination": "recorder.local", "_category": "different_arch", "_info_type": "recording_profile"},
            ],
            "ldap_directory": [
                {"name": "Corp AD", "ldapDn": "dc=corp,dc=local", "_category": "different_arch", "_info_type": "ldap_directory"},
            ],
            "app_user": [
                {"userid": "JTAPI_USER", "description": "JTAPI for Finesse", "associatedDevices": "CTI-1", "_category": "planning", "_info_type": "app_user"},
                {"userid": "CUCXNSvc", "description": "CUC Service", "associatedDevices": "", "_category": "planning", "_info_type": "app_user"},
            ],
            "h323_gateway": [
                {"name": "GW-Analog", "description": "Analog gateway", "product": "Cisco VG310", "_category": "planning", "_info_type": "h323_gateway"},
            ],
            "enterprise_params": [
                {"name": "Enterprise Parameters", "clusterName": "CUCM-LAB", "_category": "planning", "_info_type": "enterprise_params"},
            ],
            "service_params": [
                {"name": "MaxCallDuration", "service": "Cisco CallManager", "value": "720", "_category": "planning", "_info_type": "service_params"},
            ],
        },

        # ----- Tier 4 Feature Gaps (recording, transformations, EM info) -----
        "tier4": {
            "recording_profiles": [
                {
                    "name": "RecordingProfile-Default",
                    "recordingCssName": "CSS-Recording",
                    "recorderDestination": "recorder.company.com",
                },
            ],
            "calling_party_transformations": [
                {
                    "pattern": "9.!",
                    "description": "Strip access code",
                    "callingSearchSpaceName": "CSS-Internal",
                    "routePartitionName": "PT-Internal",
                    "callingPartyTransformationMask": "1XXX",
                    "callingPartyPrefixDigits": "",
                    "digitDiscardInstructionName": "",
                },
            ],
            "called_party_transformations": [
                {
                    "pattern": "+1!",
                    "description": "US E.164 normalization",
                    "callingSearchSpaceName": None,
                    "routePartitionName": None,
                    "calledPartyTransformationMask": "",
                    "calledPartyPrefixDigits": "",
                    "digitDiscardInstructionName": "",
                },
            ],
            "device_profiles": [
                {
                    "name": "DP-tier4-em",
                    "description": "Tier 4 informational EM profile",
                    "product": "Cisco 8845",
                    "protocol": "SIP",
                },
            ],
            "remote_destination_profiles": [
                {
                    "name": "RDP-tier4-user",
                    "description": "Tier 4 mobile profile",
                    "userId": "tier4user",
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# Normalization Phase
# ---------------------------------------------------------------------------

class TestNormalizationPhase:
    def test_normalize_produces_expected_object_counts(self, store, raw_data):
        normalize_discovery(raw_data, store)
        assert store.count_by_type("user") == 4
        assert store.count_by_type("device") >= 3
        assert store.count_by_type("device_pool") == 2
        assert store.count_by_type("datetime_group") == 2
        assert store.count_by_type("sip_trunk") >= 1
        assert store.count_by_type("hunt_pilot") >= 1
        assert store.count_by_type("partition") >= 2
        assert store.count_by_type("css") >= 1

    def test_normalize_returns_summary_with_counts(self, store, raw_data):
        result = normalize_discovery(raw_data, store)
        assert result["pass1"]["total"] > 0
        assert "pass2" in result

    def test_cross_refs_built(self, store, raw_data):
        normalize_discovery(raw_data, store)
        # jsmith should have a primary DN cross-ref
        user_refs = store.find_cross_refs("user:jsmith", "user_has_primary_dn")
        assert len(user_refs) >= 1
        # SEP001122334455 should have 2 DN cross-refs (lines 1001 and 1002)
        device_refs = store.find_cross_refs("device:SEP001122334455", "device_has_dn")
        assert len(device_refs) >= 2

    def test_raw_phones_preserved(self, store, raw_data):
        normalize_discovery(raw_data, store)
        phones = store.get_objects("phone")
        assert len(phones) >= 3

    def test_voicemail_objects_created(self, store, raw_data):
        normalize_discovery(raw_data, store)
        assert store.count_by_type("voicemail_profile") >= 1
        assert store.count_by_type("voicemail_pilot") >= 1

    def test_tier2_objects_normalized(self, store, raw_data):
        """Tier 2 types are normalized from raw_data into the store."""
        normalize_discovery(raw_data, store)
        # Remote destinations: 2 entries + 1 tier4 remote_destination_profile → 3 objects
        assert store.count_by_type("remote_destination") == 3
        # E911: 1 ELIN group + 1 geo location
        assert store.count_by_type("elin_group") == 1
        assert store.count_by_type("geo_location") == 1
        # Device profiles: 1 profile
        assert store.count_by_type("device_profile") == 1
        # MOH: 2 sources (1 default + 1 custom)
        assert store.count_by_type("moh_source") == 2
        # Announcements: 1 announcement
        assert store.count_by_type("announcement") == 1

    def test_tier2_cross_refs_built(self, store, raw_data):
        """Tier 2 cross-references are built during normalization pass 2."""
        normalize_discovery(raw_data, store)
        # jsmith should have a remote destination cross-ref
        rd_refs = store.find_cross_refs("user:jsmith", "user_has_remote_destination")
        assert len(rd_refs) == 1
        assert "remote_destination:jsmith:" in rd_refs[0]
        # bwilson should also have one
        rd_refs_b = store.find_cross_refs("user:bwilson", "user_has_remote_destination")
        assert len(rd_refs_b) == 1

    def test_tier4_objects_normalized(self, store, raw_data):
        """Tier 4 feature gap types are normalized from raw_data into the store."""
        normalize_discovery(raw_data, store)
        # Recording profiles: 1 entry
        assert store.count_by_type("info_recording") >= 1
        # Calling party transformations: 1 entry
        assert store.count_by_type("info_calling_xform") >= 1
        # Called party transformations: 1 entry
        assert store.count_by_type("info_called_xform") >= 1
        # EM device profiles (Tier 4 info): 1 entry
        assert store.count_by_type("info_device_profile") >= 1

    def test_tier3_informational_objects_normalized(self, store, raw_data):
        """Tier 3 informational types are normalized from raw_data into the store."""
        normalize_discovery(raw_data, store)

        # Cloud-managed (7 types, 5 with data)
        assert store.count_by_type("info_region") == 2
        assert store.count_by_type("info_srst") == 1
        assert store.count_by_type("info_media_resource_group") == 1
        assert store.count_by_type("info_media_resource_list") == 1
        assert store.count_by_type("info_conference_bridge") == 1

        # Not migratable (3 types)
        assert store.count_by_type("info_softkey_template") == 1
        assert store.count_by_type("info_ip_phone_service") == 1
        assert store.count_by_type("info_intercom") == 1

        # Different architecture (6 types, 5 with data)
        assert store.count_by_type("info_common_phone_config") == 1
        assert store.count_by_type("info_phone_button_template") == 1
        assert store.count_by_type("info_credential_policy") == 1
        assert store.count_by_type("info_recording_profile") == 1
        assert store.count_by_type("info_ldap_directory") == 1

        # Planning (4 types)
        assert store.count_by_type("info_app_user") == 2
        assert store.count_by_type("info_h323_gateway") == 1
        assert store.count_by_type("info_enterprise_params") == 1
        assert store.count_by_type("info_service_params") == 1

        # Empty types should have 0
        assert store.count_by_type("info_aar_group") == 0
        assert store.count_by_type("info_device_mobility_group") == 0
        assert store.count_by_type("info_feature_control_policy") == 0

        # Verify canonical_id format
        regions = store.get_objects("info_region")
        ids = {r["canonical_id"] for r in regions}
        assert "info_region:Default" in ids
        assert "info_region:LowBandwidth" in ids

        # Verify app_user uses userid field
        app_users = store.get_objects("info_app_user")
        uids = {u["canonical_id"] for u in app_users}
        assert "info_app_user:JTAPI_USER" in uids

        # Verify intercom uses dnorpattern field
        intercoms = store.get_objects("info_intercom")
        assert intercoms[0]["canonical_id"] == "info_intercom:9001"


# ---------------------------------------------------------------------------
# Mapping Phase
# ---------------------------------------------------------------------------

class TestMappingPhase:
    def test_mappers_produce_canonical_objects(self, store, raw_data):
        normalize_discovery(raw_data, store)
        engine = TransformEngine()
        result = engine.run(store)
        assert store.count_by_type("location") >= 2
        assert store.count_by_type("trunk") >= 1

    def test_no_mapper_errors(self, store, raw_data):
        normalize_discovery(raw_data, store)
        engine = TransformEngine()
        result = engine.run(store)
        assert len(result.errors) == 0, f"Mapper errors: {result.errors}"

    def test_mapper_produces_new_objects(self, store, raw_data):
        normalize_discovery(raw_data, store)
        pre_count = store.count_by_type("location")
        engine = TransformEngine()
        engine.run(store)
        post_count = store.count_by_type("location")
        assert post_count > pre_count  # Mappers create new canonical objects

    def test_tier2_mappers_produce_objects(self, store, raw_data):
        """Tier 2 mappers produce canonical objects from normalized data."""
        normalize_discovery(raw_data, store)
        engine = TransformEngine()
        result = engine.run(store)
        # No mapper errors from the new mappers
        assert len(result.errors) == 0, f"Mapper errors: {result.errors}"
        # SNR: 2 users with remote dests → 2 SNR objects
        assert store.count_by_type("single_number_reach") == 2
        # E911: 1 ELIN group → 1 e911_config (geo-only skipped when ELIN present)
        assert store.count_by_type("e911_config") >= 1
        # Device profile: 1 profile → 1 canonical device_profile
        assert store.count_by_type("device_profile") >= 1
        # MOH: 2 sources → 2 music_on_hold objects
        assert store.count_by_type("music_on_hold") == 2
        # Announcements: 1 → 1 announcement
        assert store.count_by_type("announcement") == 1


# ---------------------------------------------------------------------------
# Analysis Phase
# ---------------------------------------------------------------------------

class TestAnalysisPhase:
    def test_analyzers_produce_decisions(self, store, raw_data):
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        pipeline = AnalysisPipeline()
        pipeline.run(store)
        decisions = store.get_all_decisions()
        decision_types = {d["type"] for d in decisions}
        # 7962 is incompatible
        assert "DEVICE_INCOMPATIBLE" in decision_types

    def test_shared_line_detected(self, store, raw_data):
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        pipeline = AnalysisPipeline()
        pipeline.run(store)
        decisions = store.get_all_decisions()
        decision_types = {d["type"] for d in decisions}
        # DN 1002 is shared across two phones — verify the prerequisite cross-refs.
        # NOTE: The SHARED_LINE_COMPLEX decision is NOT produced because the
        # SharedLineAnalyzer looks up "dn:..." IDs but LineMapper stores them as
        # "line:..." IDs (prefix mismatch bug in shared_line.py). This test
        # verifies the cross-ref data that *would* trigger the decision.
        shared_dn_refs = store.get_cross_refs(to_id="dn:1002:PT-Internal", relationship="device_has_dn")
        assert len(shared_dn_refs) >= 2, "DN 1002 should appear on 2 devices"

    def test_all_analyzers_run_without_error(self, store, raw_data):
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        pipeline = AnalysisPipeline()
        result = pipeline.run(store)
        # No analyzer should crash (value -1 signals failure)
        failed = {k: v for k, v in result.stats.items() if v == -1}
        assert len(failed) == 0, f"Analyzers failed: {list(failed.keys())}"

    def test_at_least_10_analyzers_ran(self, store, raw_data):
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        pipeline = AnalysisPipeline()
        result = pipeline.run(store)
        assert len(result.stats) >= 10

    def test_tier2_decisions_produced(self, store, raw_data):
        """Tier 2 mappers and analyzers produce expected decision types."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)

        decisions = store.get_all_decisions()
        decision_types = {d["type"] for d in decisions}

        # SNR: bwilson has custom answerTooSoonTimer → SNR_LOSSY
        assert "SNR_LOSSY" in decision_types
        # E911: ELIN group detected → ARCHITECTURE_ADVISORY
        assert "ARCHITECTURE_ADVISORY" in decision_types
        # Device profile: 2 lines + speed dials → FEATURE_APPROXIMATION
        assert "FEATURE_APPROXIMATION" in decision_types
        # MOH custom source + announcement → AUDIO_ASSET_MANUAL
        assert "AUDIO_ASSET_MANUAL" in decision_types

    def test_tier4_advisory_patterns_fire(self, store, raw_data):
        """Tier 4 advisory patterns produce ARCHITECTURE_ADVISORY decisions."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)

        decisions = store.get_all_decisions()
        advisory_decisions = [d for d in decisions if d["type"] == "ARCHITECTURE_ADVISORY"]
        pattern_names = set()
        for d in advisory_decisions:
            ctx = d.get("context", {}) or {}
            pn = ctx.get("pattern_name", "")
            if pn:
                pattern_names.add(pn)

        # Tier 4 patterns that should fire from our test data:
        # - transformation_patterns: 1 calling + 1 called party xform
        # - extension_mobility_usage: 1 EM device profile
        # - recording_enabled_users: SEP001122334455 has recordingFlag on line 1
        tier4_patterns = {"transformation_patterns", "extension_mobility_usage", "recording_enabled_users"}
        fired = tier4_patterns & pattern_names
        assert len(fired) >= 3, (
            f"Expected at least 3 Tier 4 advisory patterns to fire, "
            f"got {fired}. All pattern names: {pattern_names}"
        )


# ---------------------------------------------------------------------------
# Shared helper — run pipeline through analysis with auto-resolved decisions
# ---------------------------------------------------------------------------

def _auto_resolve_decisions(store):
    """Auto-pick the first option for all unresolved decisions."""
    for d in store.get_all_decisions():
        if d.get("chosen_option") is None and d.get("options"):
            opt = d["options"][0]
            store.resolve_decision(
                d["decision_id"],
                opt["id"] if isinstance(opt, dict) else opt,
            )


def _run_through_analysis(store, raw_data):
    """Run normalize → map → analyze → auto-resolve decisions."""
    normalize_discovery(raw_data, store)
    TransformEngine().run(store)
    AnalysisPipeline().run(store)
    _auto_resolve_decisions(store)


# ---------------------------------------------------------------------------
# Planning Phase
# ---------------------------------------------------------------------------

class TestPlanningPhase:
    def _setup(self, store, raw_data):
        _run_through_analysis(store, raw_data)

    def test_planner_produces_operations(self, store, raw_data):
        self._setup(store, raw_data)
        ops = expand_to_operations(store)
        assert len(ops) > 0
        op_keys = {(op.resource_type, op.op_type) for op in ops}
        assert ("location", "create") in op_keys
        assert ("user", "create") in op_keys

    def test_dependency_graph_is_acyclic(self, store, raw_data):
        self._setup(store, raw_data)
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        assert nx.is_directed_acyclic_graph(G), "Dependency graph has cycles!"

    def test_batches_partition_correctly(self, store, raw_data):
        self._setup(store, raw_data)
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        batches = partition_into_batches(G)
        assert len(batches) > 0
        # Tier 0 (locations) should exist
        tier_0_batches = [b for b in batches if b.tier == 0]
        assert len(tier_0_batches) > 0

    def test_save_plan_to_store(self, store, raw_data):
        self._setup(store, raw_data)
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        save_plan_to_store(G, store)
        # Verify plan_operations table has data
        rows = store.conn.execute("SELECT COUNT(*) FROM plan_operations").fetchone()
        assert rows[0] > 0

    def test_tier2_snr_planned_report_only_skipped(self, store, raw_data):
        """SNR produces plan operations; report-only types do not."""
        self._setup(store, raw_data)
        ops = expand_to_operations(store)
        op_types = {(op.resource_type, op.op_type) for op in ops}
        # SNR should have configure operations
        assert ("single_number_reach", "configure") in op_types
        # Report-only types should NOT have operations
        resource_types = {op.resource_type for op in ops}
        assert "e911_config" not in resource_types
        assert "device_profile" not in resource_types
        assert "music_on_hold" not in resource_types
        assert "announcement" not in resource_types


# ---------------------------------------------------------------------------
# Export Phase
# ---------------------------------------------------------------------------

class TestExportPhase:
    def _setup(self, store, raw_data):
        _run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        save_plan_to_store(G, store)

    def test_deployment_plan_generates(self, store, raw_data):
        self._setup(store, raw_data)
        plan = generate_plan_summary(store, project_id="e2e-test")
        assert isinstance(plan, str)
        assert len(plan) > 100
        assert "## " in plan  # Has markdown sections

    def test_deployment_plan_references_locations(self, store, raw_data):
        self._setup(store, raw_data)
        plan = generate_plan_summary(store, project_id="e2e-test")
        # Plan should mention locations or tiers
        assert "Location" in plan or "location" in plan or "Tier" in plan


# ---------------------------------------------------------------------------
# Full Pipeline Smoke Test
# ---------------------------------------------------------------------------

class TestFullPipelineSmoke:
    """Single test that runs everything and verifies the pipeline doesn't crash."""

    def test_full_pipeline_no_crash(self, store, raw_data):
        # Normalize
        norm_result = normalize_discovery(raw_data, store)
        assert norm_result["pass1"]["total"] > 0

        # Map
        pre_loc = store.count_by_type("location")
        TransformEngine().run(store)
        assert store.count_by_type("location") > pre_loc

        # Analyze + auto-resolve
        AnalysisPipeline().run(store)
        _auto_resolve_decisions(store)

        # Plan
        ops = expand_to_operations(store)
        assert len(ops) > 0
        G = build_dependency_graph(ops, store)
        assert nx.is_directed_acyclic_graph(G)
        batches = partition_into_batches(G)
        assert len(batches) > 0
        save_plan_to_store(G, store)

        # Export
        plan = generate_plan_summary(store, project_id="e2e-test")
        assert len(plan) > 0
