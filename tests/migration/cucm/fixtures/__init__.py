"""CUCM AXL response fixture dicts for extractor tests.

All fixtures are recorded AXL response dicts from the extraction design spec
(docs/plans/cucm-pipeline/02b-cucm-extraction.md). They represent what zeep
returns from AXL SOAP calls, using the _value_1/uuid reference pattern.

Edge-case fixtures (USER_NO_EMAIL_FIXTURE, PHONE_FOUR_LINES_FIXTURE, etc.)
are realistic variations based on the patterns in the spec.
"""

# ---------------------------------------------------------------------------
# §2.1 — Device Pool
# ---------------------------------------------------------------------------

DEVICE_POOL_FIXTURE = {
    'pkid': '{B1234567-ABCD-1234-ABCD-123456789012}',
    'name': 'DP-SanJose-Phones',
    'dateTimeSettingName': {
        '_value_1': 'CMLocal',
        'uuid': '{D1111111-1111-1111-1111-111111111111}',
    },
    'locationName': {
        '_value_1': 'SanJose',
        'uuid': '{L2222222-2222-2222-2222-222222222222}',
    },
    'callManagerGroupName': {
        '_value_1': 'Default',
        'uuid': '{C3333333-3333-3333-3333-333333333333}',
    },
    'srstName': {
        '_value_1': 'SRST-SanJose',
        'uuid': '{S4444444-4444-4444-4444-444444444444}',
    },
    'regionName': {
        '_value_1': 'SanJose-Region',
        'uuid': '{R5555555-5555-5555-5555-555555555555}',
    },
    'mediaResourceListName': None,
}


# ---------------------------------------------------------------------------
# §2.1 — DateTime Group
# ---------------------------------------------------------------------------

DATETIME_GROUP_FIXTURE = {
    'pkid': '{D1111111-1111-1111-1111-111111111111}',
    'name': 'CMLocal',
    'timeZone': 'America/Los_Angeles',
}


# ---------------------------------------------------------------------------
# §2.2 — End User
# ---------------------------------------------------------------------------

END_USER_FIXTURE = {
    'pkid': '{A1234567-ABCD-1234-ABCD-123456789012}',
    'firstName': 'John',
    'lastName': 'Doe',
    'mailid': 'jdoe@acme.com',
    'userid': 'jdoe',
    'telephoneNumber': '+14155551234',
    'department': 'Engineering',
    'title': 'Software Engineer',
    'manager': {
        '_value_1': 'msmith',
        'uuid': '{M7777777-7777-7777-7777-777777777777}',
    },
    'directoryUri': 'jdoe@acme.com',
    'userLocale': 'English United States',
    'selfService': '8000',
    'associatedDevices': {'device': ['SEP001122334455', 'CSFJDOE']},
    'enableCti': 'true',
    'primaryExtension': {
        'pattern': '1001',
        'routePartitionName': {
            '_value_1': 'Internal-PT',
            'uuid': '{P8888888-8888-8888-8888-888888888888}',
        },
    },
    'callingSearchSpaceName': {
        '_value_1': 'Standard-Employee-CSS',
        'uuid': '{CSS99999-9999-9999-9999-999999999999}',
    },
    'voiceMailProfile': {
        '_value_1': 'Default-VM-Profile',
        'uuid': '{V0000000-0000-0000-0000-000000000000}',
    },
}


# ---------------------------------------------------------------------------
# §2.3 — Phone (2 lines: primary + shared team line)
# ---------------------------------------------------------------------------

PHONE_FIXTURE = {
    'pkid': '{PH123456-ABCD-1234-ABCD-123456789012}',
    'name': 'SEP001122334455',
    'model': 'Cisco 8845',
    'description': 'John Doe - Desk Phone',
    'ownerUserName': {
        '_value_1': 'jdoe',
        'uuid': '{A1234567-ABCD-1234-ABCD-123456789012}',
    },
    'devicePoolName': {
        '_value_1': 'DP-SanJose-Phones',
        'uuid': '{B1234567-ABCD-1234-ABCD-123456789012}',
    },
    'protocol': 'SIP',
    'callingSearchSpaceName': {
        '_value_1': 'Standard-Employee-CSS',
        'uuid': '{CSS99999-9999-9999-9999-999999999999}',
    },
    'phoneTemplateName': {
        '_value_1': 'Standard 8845 SIP',
        'uuid': '{T1111111-1111-1111-1111-111111111111}',
    },
    'softkeyTemplateName': None,
    'deviceMobilityMode': 'Default',
    'product': 'Cisco 8845',
    'class': 'Phone',
    'lines': {
        'line': [
            {
                'index': '1',
                'label': 'John Doe - 1001',
                'display': 'John Doe',
                'e164Mask': '+14155551001',
                'associatedEndusers': {'enduser': [{'userId': 'jdoe'}]},
                'dirn': {
                    'pattern': '1001',
                    'routePartitionName': {
                        '_value_1': 'Internal-PT',
                        'uuid': '{P8888888-8888-8888-8888-888888888888}',
                    },
                    'alertingName': 'John Doe',
                    'description': 'John Doe Ext 1001',
                    'shareLineAppearanceCssName': None,
                    'callingSearchSpaceName': {
                        '_value_1': 'Line-CSS',
                        'uuid': '{LCSS1111-1111-1111-1111-111111111111}',
                    },
                },
            },
            {
                'index': '2',
                'label': 'Team Line - 1050',
                'display': 'Engineering Team',
                'e164Mask': None,
                'associatedEndusers': {
                    'enduser': [{'userId': 'jdoe'}, {'userId': 'asmith'}],
                },
                'dirn': {
                    'pattern': '1050',
                    'routePartitionName': {
                        '_value_1': 'Internal-PT',
                        'uuid': '{P8888888-8888-8888-8888-888888888888}',
                    },
                    'alertingName': 'Engineering Team',
                    'description': 'Shared Team Line',
                    'shareLineAppearanceCssName': {
                        '_value_1': 'SharedLine-CSS',
                        'uuid': '{SLCSS222-2222-2222-2222-222222222222}',
                    },
                    'callingSearchSpaceName': None,
                },
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# §2.4 — CSS (3 ordered partition members)
# ---------------------------------------------------------------------------

CSS_FIXTURE = {
    'pkid': '{CSS12345-ABCD-1234-ABCD-123456789012}',
    'name': 'Standard-Employee-CSS',
    'description': 'Standard employee calling search space',
    'members': {
        'member': [
            {
                'routePartitionName': {
                    '_value_1': 'Internal-PT',
                    'uuid': '{PT111111-1111-1111-1111-111111111111}',
                },
                'index': '1',
            },
            {
                'routePartitionName': {
                    '_value_1': 'Local-PSTN-PT',
                    'uuid': '{PT222222-2222-2222-2222-222222222222}',
                },
                'index': '2',
            },
            {
                'routePartitionName': {
                    '_value_1': 'International-Block-PT',
                    'uuid': '{PT333333-3333-3333-3333-333333333333}',
                },
                'index': '3',
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# §2.4 — Route Pattern
# ---------------------------------------------------------------------------

ROUTE_PATTERN_FIXTURE = {
    # Verified against live CUCM 15.0 (2026-03-23):
    # - 'destination' is NOT a valid returnedTag for listRoutePattern
    # - 'networkLocation' returns values like 'OnNet', 'OffNet'
    'pkid': '{RP123456-ABCD-1234-ABCD-123456789012}',
    'pattern': '9.1[2-9]XXXXXXXXX',
    'routePartitionName': {
        '_value_1': 'Local-PSTN-PT',
        'uuid': '{PT222222-2222-2222-2222-222222222222}',
    },
    'blockEnable': 'false',
    'description': 'North American long distance',
    'calledPartyTransformationMask': '',
    'callingPartyTransformationMask': '',
    'prefixDigitsOut': None,
    'networkLocation': 'OffNet',
}

# SIP trunk fixture — from real CUCM 15.0 response structure
# destinations is a nested array, NOT flat destinationAddress/destinationPort
SIP_TRUNK_FIXTURE = {
    'pkid': '{5F98AA6B-FDF8-7AB6-EF55-020F870F1CDE}',
    'name': 'sip-trunk-to-lab-cucm',
    'description': 'sip-trunk-to-lab-cucm',
    'sipProfileName': {
        '_value_1': 'Standard SIP Profile with ping',
        'uuid': '{A141E06C-8B60-035F-3073-074DE6900B88}',
    },
    'securityProfileName': {
        '_value_1': 'Non Secure SIP Trunk Profile',
        'uuid': '{0FD98C54-30BA-4BFD-83E7-EACFE1A2BEAE}',
    },
    'devicePoolName': {
        '_value_1': 'Default',
        'uuid': '{1B1B9EB6-7803-11D3-BDF0-00108302EAD1}',
    },
    'sipTrunkType': 'None(Default)',
    'destinations': {
        'destination': [
            {
                'addressIpv4': '10.201.33.100',
                'addressIpv6': None,
                'port': '5060',
                'sortOrder': '1',
            },
            {
                'addressIpv4': '10.201.33.102',
                'addressIpv6': None,
                'port': '5060',
                'sortOrder': '2',
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# §2.5 — Hunt Pilot
# ---------------------------------------------------------------------------

HUNT_PILOT_FIXTURE = {
    'pkid': '{HP123456-ABCD-1234-ABCD-123456789012}',
    'pattern': '5001',
    'description': 'Sales Hunt Group',
    'routePartitionName': {
        '_value_1': 'Internal-PT',
        'uuid': '{PT111111-1111-1111-1111-111111111111}',
    },
    'huntListName': {
        '_value_1': 'Sales-HuntList',
        'uuid': '{HL111111-1111-1111-1111-111111111111}',
    },
    'forwardHuntNoAnswer': {'destination': '5999', 'enabled': 'true'},
    'forwardHuntBusy': {'destination': '', 'enabled': 'false'},
    'queueCalls': {'enabled': 'false'},
    'maxCallersInQueue': '0',
    'mohSourceId': None,
    'huntTimerCallPick': '20',
    'overflowDestination': None,
    'enabled': 'true',
}


# ---------------------------------------------------------------------------
# §2.6 — Voicemail Profile
# ---------------------------------------------------------------------------

VOICEMAIL_PROFILE_FIXTURE = {
    'pkid': '{VM123456-ABCD-1234-ABCD-123456789012}',
    'name': 'Default-VM-Profile',
    'description': 'Default voicemail profile for all users',
    # Verified via live CUCM: voiceMailPilot is a complex type {dirn, cssName, uuid},
    # NOT the simple {_value_1, uuid} reference pattern.
    'voiceMailPilot': {
        'dirn': '8000',
        'cssName': 'VM-CSS',
        'uuid': '{VMP11111-1111-1111-1111-111111111111}',
    },
    'voiceMailboxMask': '',
}


# ---------------------------------------------------------------------------
# §2.8 — Common-Area Phone (ownerUserName=None)
# ---------------------------------------------------------------------------

COMMON_AREA_PHONE_FIXTURE = {
    'pkid': '{WS123456-ABCD-1234-ABCD-123456789012}',
    'name': 'SEP556677889900',
    'model': 'Cisco 8841',
    'description': 'Lobby Phone - Building A',
    'ownerUserName': None,
    'devicePoolName': {
        '_value_1': 'DP-SanJose-CommonArea',
        'uuid': '{DP444444-4444-4444-4444-444444444444}',
    },
    'protocol': 'SIP',
    'callingSearchSpaceName': {
        '_value_1': 'Lobby-CSS',
        'uuid': '{LCSS3333-3333-3333-3333-333333333333}',
    },
    'phoneTemplateName': {
        '_value_1': 'Standard 8841 SIP',
        'uuid': '{T2222222-2222-2222-2222-222222222222}',
    },
    'product': 'Cisco 8841',
    'class': 'Phone',
    'lines': {
        'line': [
            {
                'index': '1',
                'label': 'Lobby',
                'display': 'Lobby - Bldg A',
                'e164Mask': None,
                'associatedEndusers': None,
                'dirn': {
                    'pattern': '1099',
                    'routePartitionName': {
                        '_value_1': 'Internal-PT',
                        'uuid': '{P8888888-8888-8888-8888-888888888888}',
                    },
                    'alertingName': 'Lobby',
                    'description': 'Lobby Phone',
                    'shareLineAppearanceCssName': None,
                    'callingSearchSpaceName': None,
                },
            },
        ],
    },
}


# ===========================================================================
# Edge-Case Fixtures
# ===========================================================================

# ---------------------------------------------------------------------------
# Edge case: User with no email (mailid=None)
# From §2.2 edge case: "Users with no mailid. Common in legacy CUCM
# deployments."  user_mapper handles with MISSING_DATA decision, checking
# if userid is email-format as fallback.
# ---------------------------------------------------------------------------

USER_NO_EMAIL_FIXTURE = {
    'pkid': '{A2222222-BBBB-2222-BBBB-222222222222}',
    'firstName': 'Legacy',
    'lastName': 'User',
    'mailid': None,
    'userid': 'legacyuser',
    'telephoneNumber': '+14155559999',
    'department': 'Operations',
    'title': None,
    'manager': None,
    'directoryUri': None,
    'userLocale': None,
    'selfService': None,
    'associatedDevices': {'device': ['SEP112233445566']},
    'enableCti': 'false',
    'primaryExtension': {
        'pattern': '2001',
        'routePartitionName': {
            '_value_1': 'Internal-PT',
            'uuid': '{P8888888-8888-8888-8888-888888888888}',
        },
    },
    'callingSearchSpaceName': {
        '_value_1': 'Standard-Employee-CSS',
        'uuid': '{CSS99999-9999-9999-9999-999999999999}',
    },
    'voiceMailProfile': None,
}


# ---------------------------------------------------------------------------
# Edge case: Phone with 4 lines including shared line scenario
# Exercises multi-line handling and mixed line-level CSS assignment.
# Based on patterns in §2.3 (phone fixture) and §2.7 (shared line detection).
# ---------------------------------------------------------------------------

PHONE_FOUR_LINES_FIXTURE = {
    'pkid': '{PH444444-ABCD-4444-ABCD-444444444444}',
    'name': 'SEP112233445566',
    'model': 'Cisco 8865',
    'description': 'Alice Smith - Executive Phone',
    'ownerUserName': {
        '_value_1': 'asmith',
        'uuid': '{A3333333-CCCC-3333-CCCC-333333333333}',
    },
    'devicePoolName': {
        '_value_1': 'DP-SanJose-Phones',
        'uuid': '{B1234567-ABCD-1234-ABCD-123456789012}',
    },
    'protocol': 'SIP',
    'callingSearchSpaceName': {
        '_value_1': 'Executive-CSS',
        'uuid': '{ECSS5555-5555-5555-5555-555555555555}',
    },
    'phoneTemplateName': {
        '_value_1': 'Standard 8865 SIP',
        'uuid': '{T3333333-3333-3333-3333-333333333333}',
    },
    'softkeyTemplateName': None,
    'deviceMobilityMode': 'Default',
    'product': 'Cisco 8865',
    'class': 'Phone',
    'lines': {
        'line': [
            # Line 1: primary personal extension
            {
                'index': '1',
                'label': 'Alice Smith - 2001',
                'display': 'Alice Smith',
                'e164Mask': '+14155552001',
                'associatedEndusers': {'enduser': [{'userId': 'asmith'}]},
                'dirn': {
                    'pattern': '2001',
                    'routePartitionName': {
                        '_value_1': 'Internal-PT',
                        'uuid': '{P8888888-8888-8888-8888-888888888888}',
                    },
                    'alertingName': 'Alice Smith',
                    'description': 'Alice Smith Ext 2001',
                    'shareLineAppearanceCssName': None,
                    'callingSearchSpaceName': {
                        '_value_1': 'Line-CSS',
                        'uuid': '{LCSS1111-1111-1111-1111-111111111111}',
                    },
                },
            },
            # Line 2: shared team line (same DN 1050 as PHONE_FIXTURE line 2)
            {
                'index': '2',
                'label': 'Team Line - 1050',
                'display': 'Engineering Team',
                'e164Mask': None,
                'associatedEndusers': {
                    'enduser': [{'userId': 'jdoe'}, {'userId': 'asmith'}],
                },
                'dirn': {
                    'pattern': '1050',
                    'routePartitionName': {
                        '_value_1': 'Internal-PT',
                        'uuid': '{P8888888-8888-8888-8888-888888888888}',
                    },
                    'alertingName': 'Engineering Team',
                    'description': 'Shared Team Line',
                    'shareLineAppearanceCssName': {
                        '_value_1': 'SharedLine-CSS',
                        'uuid': '{SLCSS222-2222-2222-2222-222222222222}',
                    },
                    'callingSearchSpaceName': None,
                },
            },
            # Line 3: executive direct line with dedicated line CSS
            {
                'index': '3',
                'label': 'Direct - 2099',
                'display': 'Alice Smith Direct',
                'e164Mask': '+14155552099',
                'associatedEndusers': {'enduser': [{'userId': 'asmith'}]},
                'dirn': {
                    'pattern': '2099',
                    'routePartitionName': {
                        '_value_1': 'Executive-PT',
                        'uuid': '{PT444444-4444-4444-4444-444444444444}',
                    },
                    'alertingName': 'Alice Smith Direct',
                    'description': 'Executive Direct Line',
                    'shareLineAppearanceCssName': None,
                    'callingSearchSpaceName': {
                        '_value_1': 'Executive-Line-CSS',
                        'uuid': '{ELCSS666-6666-6666-6666-666666666666}',
                    },
                },
            },
            # Line 4: shared receptionist overflow line (no line-level CSS)
            {
                'index': '4',
                'label': 'Reception Overflow',
                'display': 'Reception',
                'e164Mask': None,
                'associatedEndusers': {
                    'enduser': [
                        {'userId': 'asmith'},
                        {'userId': 'receptionist1'},
                    ],
                },
                'dirn': {
                    'pattern': '1000',
                    'routePartitionName': {
                        '_value_1': 'Internal-PT',
                        'uuid': '{P8888888-8888-8888-8888-888888888888}',
                    },
                    'alertingName': 'Main Reception',
                    'description': 'Reception Overflow Line',
                    'shareLineAppearanceCssName': {
                        '_value_1': 'SharedLine-CSS',
                        'uuid': '{SLCSS222-2222-2222-2222-222222222222}',
                    },
                    'callingSearchSpaceName': None,
                },
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Edge case: CSS with 5 partitions
# Tests deeper partition ordering — exercises the CSS decomposition algorithm
# (04-css-decomposition.md) with more granular routing tiers.
# ---------------------------------------------------------------------------

CSS_FIVE_PARTITIONS_FIXTURE = {
    'pkid': '{CSS55555-ABCD-5555-ABCD-555555555555}',
    'name': 'Executive-Full-CSS',
    'description': 'Executive CSS with full domestic and international access',
    'members': {
        'member': [
            {
                'routePartitionName': {
                    '_value_1': 'Internal-PT',
                    'uuid': '{PT111111-1111-1111-1111-111111111111}',
                },
                'index': '1',
            },
            {
                'routePartitionName': {
                    '_value_1': 'Local-PSTN-PT',
                    'uuid': '{PT222222-2222-2222-2222-222222222222}',
                },
                'index': '2',
            },
            {
                'routePartitionName': {
                    '_value_1': 'Long-Distance-PT',
                    'uuid': '{PT555555-5555-5555-5555-555555555555}',
                },
                'index': '3',
            },
            {
                'routePartitionName': {
                    '_value_1': 'International-PT',
                    'uuid': '{PT666666-6666-6666-6666-666666666666}',
                },
                'index': '4',
            },
            {
                'routePartitionName': {
                    '_value_1': 'Premium-Rate-PT',
                    'uuid': '{PT777777-7777-7777-7777-777777777777}',
                },
                'index': '5',
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Edge case: Device pool with no datetime group
# From §2.1 edge case: "Device pools without datetime groups. Some device
# pools inherit the datetime group from the cluster default. If
# dateTimeSettingName is None, the normalizer should use the cluster default
# timezone from migration config."
# ---------------------------------------------------------------------------

DEVICE_POOL_NO_DATETIME_FIXTURE = {
    'pkid': '{B9999999-ABCD-9999-ABCD-999999999999}',
    'name': 'DP-Default-Inherited',
    'dateTimeSettingName': None,
    'locationName': {
        '_value_1': 'Hub_None',
        'uuid': '{L8888888-8888-8888-8888-888888888888}',
    },
    'callManagerGroupName': {
        '_value_1': 'Default',
        'uuid': '{C3333333-3333-3333-3333-333333333333}',
    },
    'srstName': None,
    'regionName': {
        '_value_1': 'Default',
        'uuid': '{R0000000-0000-0000-0000-000000000000}',
    },
    'mediaResourceListName': None,
}
