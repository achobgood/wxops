"""
CUCM Lab Test Bed Provisioner — Enterprise Migration Validation

Provisions a complete enterprise test dataset on CUCM 15.0 via raw AXL SOAP
POST calls. This script creates every object defined in build-testbed.md and
exercises all 27 cross-reference relationships used by the migration tool.

Connection:
    Host:  10.201.123.107:8443
    Auth:  admin / c1sco123
    AXL:   v15.0, raw SOAP POST (no zeep/WSDL)

Usage:
    PYTHONPATH=. python3.11 tests/migration/cucm/provision_testbed.py

Objects created (by phase):

  Phase 1 — Infrastructure
    DateTimeGroups:    DT-Eastern, DT-Pacific
    CUCM Locations:    HQ, Branch-Austin
    Regions:           HQ-Region, Branch-Region
    Device Pools:      DP-HQ-Phones, DP-HQ-Softphones, DP-Branch-Phones, DP-CommonArea
    Partitions:        Internal-PT, Local-PSTN-PT, LongDistance-PT, International-PT, Block-Premium-PT
    CSSes:             Standard-Employee-CSS (4 PT), Executive-CSS (5 PT),
                       Restricted-CSS (2 PT), Lobby-CSS (2 PT), Line-CSS (2 PT)

  Phase 2 — Lines / Directory Numbers
    DNs: 1001-1005, 1050, 1051, 1099, 5001, 5002, 6001, 7001-7003 (all in Internal-PT)

  Phase 3 — End Users
    Users: jdoe, jsmith, bwilson, achen, msmith, legacyuser01 (no email), adminonly

  Phase 4 — Phones
    Update existing: SEP001122334455 (8845), SEP74A2E69EE6D0 (8851),
                     ATA001144778888 (ATA 191), AN0011223344080 (Analog)
    Create new:      SEPBBCCDDEE1122 (7841), SEPAABBCCDDEEFF (8845),
                     CSFjdoe (Jabber), CSFjsmith (Jabber), SEP112233445566 (8845, no lines)

  Phase 5 — Routing
    Route Group:        RG-PSTN-Primary
    Route List:         RL-PSTN
    Route Patterns:     9.1[2-9]XXXXXXXXX, 9.011!, 9.1900XXXXXXX (blocked), 0 (operator)
    Translation Pats:   8XXX, 7X

  Phase 6 — Features
    Line Groups:        Sales-LG, Support-LG
    Hunt Lists:         Sales-HL, Support-HL
    Hunt Pilots:        5001 (standard), 5002 (queue-style)
    Call Park:          7001, 7002, 7003
    Pickup Group:       Engineering-Pickup
    CTI Route Point:    CTIAA-MainMenu (DN 6001)
    Time Periods:       Business-Hours-Period, After-Hours-Period
    Time Schedule:      Business-Hours-Schedule

  Phase 7 — Voicemail
    VM Pilot:           8000
    VM Profile:         Default (updated to reference pilot 8000)
    User VM:            jdoe, jsmith, achen get Default profile

  Phase 8 — User-Device Associations
    Device associations and user CSS assignments
"""

from __future__ import annotations

import re
import sys
import textwrap
import urllib3

import requests
from requests.auth import HTTPBasicAuth

# Suppress InsecureRequestWarning for self-signed lab cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Connection details
# ---------------------------------------------------------------------------
HOST = "10.201.123.107"
URL = f"https://{HOST}:8443/axl/"
HEADERS = {"Content-Type": "text/xml", "SOAPAction": "CUCM:DB ver=15.0"}
AUTH = HTTPBasicAuth("admin", "c1sco123")

# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
results: list[tuple[str, str, bool]] = []  # (phase, object_desc, success)


def axl_request(soap_body: str) -> tuple[bool, str]:
    """Send a raw AXL SOAP request. Returns (success, response_text)."""
    # Strip indentation from the body to avoid XML parsing issues
    clean_body = textwrap.dedent(soap_body).strip()
    soap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:ns="http://www.cisco.com/AXL/API/15.0">'
        f'<soapenv:Body>{clean_body}</soapenv:Body>'
        '</soapenv:Envelope>'
    )
    try:
        resp = requests.post(URL, data=soap, headers=HEADERS, auth=AUTH,
                             verify=False, timeout=30)
        is_fault = "Fault" in resp.text
        is_duplicate = "already exists" in resp.text or "A DN exists with the same" in resp.text
        success = (resp.status_code == 200 and not is_fault) or is_duplicate
        return success, resp.text
    except requests.RequestException as exc:
        return False, str(exc)


def log(phase: str, description: str, success: bool, detail: str = "") -> None:
    """Log a result and append to the tracking list."""
    results.append((phase, description, success))
    icon = "OK" if success else "FAIL"
    line = f"  [{icon}] {description}"
    if not success and detail:
        # Extract AXL fault message if present
        match = re.search(r"<faultstring>(.*?)</faultstring>", detail)
        if match:
            line += f"  — {match.group(1)}"
        else:
            # Truncate raw detail
            line += f"  — {detail[:120]}"
    print(line)


def is_duplicate_error(text: str) -> bool:
    """Check if the AXL fault is a duplicate/already-exists error."""
    return ("already exists" in text.lower()
            or "unique constraint" in text.lower()
            or "duplicate value" in text.lower()
            or "cannot be inserted" in text.lower()
            or "Could not insert new row" in text)


# ===================================================================
# Phase 1: Infrastructure
# ===================================================================
def phase_1_infrastructure() -> None:
    """Create DateTimeGroups, Locations, Regions, DevicePools, Partitions, CSSes."""
    phase = "Phase 1"
    print(f"\n{'='*60}")
    print(f"{phase}: Infrastructure")
    print(f"{'='*60}")

    # --- DateTimeGroups ---
    for name, tz in [("DT-Eastern", "America/New_York"),
                     ("DT-Pacific", "America/Los_Angeles")]:
        body = f"""<ns:addDateTimeGroup><dateTimeGroup>
            <name>{name}</name>
            <timeZone>{tz}</timeZone>
            <separator>-</separator>
            <dateformat>M-D-Y</dateformat>
            <timeFormat>12-hour</timeFormat>
        </dateTimeGroup></ns:addDateTimeGroup>"""
        ok, text = axl_request(body)
        if not ok and is_duplicate_error(text):
            log(phase, f"DateTimeGroup {name}", True, "(already exists)")
        else:
            log(phase, f"DateTimeGroup {name}", ok, text)

    # --- Locations (CAC) ---
    for name in ["HQ", "Branch-Austin"]:
        body = f"""<ns:addLocation><location>
            <name>{name}</name>
            <withinAudioBandwidth>0</withinAudioBandwidth>
            <withinVideoBandwidth>0</withinVideoBandwidth>
            <withinImmersiveKbits>0</withinImmersiveKbits>
        </location></ns:addLocation>"""
        ok, text = axl_request(body)
        if not ok and is_duplicate_error(text):
            log(phase, f"Location {name}", True, "(already exists)")
        else:
            log(phase, f"Location {name}", ok, text)

    # --- Regions ---
    for name in ["HQ-Region", "Branch-Region"]:
        body = f"""<ns:addRegion><region>
            <name>{name}</name>
        </region></ns:addRegion>"""
        ok, text = axl_request(body)
        if not ok and is_duplicate_error(text):
            log(phase, f"Region {name}", True, "(already exists)")
        else:
            log(phase, f"Region {name}", ok, text)

    # --- Device Pools ---
    device_pools = [
        ("DP-HQ-Phones", "DT-Eastern", "HQ-Region", "HQ"),
        ("DP-HQ-Softphones", "DT-Eastern", "HQ-Region", "HQ"),
        ("DP-Branch-Phones", "DT-Pacific", "Branch-Region", "Branch-Austin"),
        ("DP-CommonArea", "DT-Eastern", "Default", "HQ"),
    ]
    for dp_name, dt, region, loc in device_pools:
        body = f"""<ns:addDevicePool><devicePool>
            <name>{dp_name}</name>
            <dateTimeSettingName>{dt}</dateTimeSettingName>
            <callManagerGroupName>Default</callManagerGroupName>
            <regionName>{region}</regionName>
            <locationName>{loc}</locationName>
        </devicePool></ns:addDevicePool>"""
        ok, text = axl_request(body)
        if not ok and is_duplicate_error(text):
            log(phase, f"DevicePool {dp_name}", True, "(already exists)")
        else:
            log(phase, f"DevicePool {dp_name}", ok, text)

    # --- Partitions ---
    partitions = [
        ("Internal-PT", "Internal extensions"),
        ("Local-PSTN-PT", "Local/national PSTN"),
        ("LongDistance-PT", "Long distance"),
        ("International-PT", "International dialing"),
        ("Block-Premium-PT", "Blocked premium rate numbers"),
    ]
    for pt_name, desc in partitions:
        body = f"""<ns:addRoutePartition><routePartition>
            <name>{pt_name}</name>
            <description>{desc}</description>
        </routePartition></ns:addRoutePartition>"""
        ok, text = axl_request(body)
        if not ok and is_duplicate_error(text):
            log(phase, f"Partition {pt_name}", True, "(already exists)")
        else:
            log(phase, f"Partition {pt_name}", ok, text)

    # --- Calling Search Spaces ---
    css_defs = [
        ("Standard-Employee-CSS", "Standard employee dialing",
         [("Internal-PT", 1), ("Local-PSTN-PT", 2), ("LongDistance-PT", 3), ("E911", 4)]),
        ("Executive-CSS", "Executive dialing with international",
         [("Internal-PT", 1), ("Local-PSTN-PT", 2), ("LongDistance-PT", 3),
          ("International-PT", 4), ("E911", 5)]),
        ("Restricted-CSS", "Restricted dialing — internal and E911 only",
         [("Internal-PT", 1), ("E911", 2)]),
        ("Lobby-CSS", "Lobby phone dialing",
         [("Internal-PT", 1), ("E911", 2)]),
        ("Line-CSS", "Line-level CSS for override testing",
         [("Internal-PT", 1), ("Local-PSTN-PT", 2)]),
    ]
    for css_name, desc, members in css_defs:
        member_xml = ""
        for pt, idx in members:
            member_xml += f"""<member>
                <routePartitionName>{pt}</routePartitionName>
                <index>{idx}</index>
            </member>"""
        body = f"""<ns:addCss><css>
            <name>{css_name}</name>
            <description>{desc}</description>
            <members>{member_xml}</members>
        </css></ns:addCss>"""
        ok, text = axl_request(body)
        if not ok and is_duplicate_error(text):
            log(phase, f"CSS {css_name}", True, "(already exists)")
        else:
            log(phase, f"CSS {css_name}", ok, text)


# ===================================================================
# Phase 2: Lines / Directory Numbers
# ===================================================================
def phase_2_lines() -> None:
    """Create directory numbers in Internal-PT."""
    phase = "Phase 2"
    print(f"\n{'='*60}")
    print(f"{phase}: Lines / Directory Numbers")
    print(f"{'='*60}")

    dns = [
        ("1001", "Internal-PT", "John Doe"),
        ("1002", "Internal-PT", "Jane Smith"),
        ("1003", "Internal-PT", "Bob Wilson"),
        ("1004", "Internal-PT", "Alice Chen"),
        ("1005", "Internal-PT", "Admin Only User"),
        ("1050", "Internal-PT", "Shared Team Line"),
        ("1051", "Internal-PT", "Shared Executive Line"),
        ("1099", "Internal-PT", "Lobby Phone"),
        ("5001", "Internal-PT", "Sales Hunt Pilot"),
        ("5002", "Internal-PT", "Support Hunt Pilot"),
        ("6001", "Internal-PT", "CTI Route Point"),
        ("7001", "Internal-PT", "Call Park 7001"),
        ("7002", "Internal-PT", "Call Park 7002"),
        ("7003", "Internal-PT", "Call Park 7003"),
    ]
    for pattern, pt, desc in dns:
        body = f"""<ns:addLine><line>
            <pattern>{pattern}</pattern>
            <routePartitionName>{pt}</routePartitionName>
            <description>{desc}</description>
            <usage>Device</usage>
            <shareLineAppearanceCssName></shareLineAppearanceCssName>
        </line></ns:addLine>"""
        ok, text = axl_request(body)
        if not ok and is_duplicate_error(text):
            log(phase, f"Line {pattern} in {pt}", True, "(already exists)")
        else:
            log(phase, f"Line {pattern} in {pt}", ok, text)


# ===================================================================
# Phase 3: End Users
# ===================================================================
def phase_3_users() -> None:
    """Create end users."""
    phase = "Phase 3"
    print(f"\n{'='*60}")
    print(f"{phase}: End Users")
    print(f"{'='*60}")

    users = [
        {
            "userid": "msmith",
            "firstName": "Mike",
            "lastName": "Smith",
            "mailid": "msmith@acme.com",
            "department": "Engineering",
            "title": "Engineering Manager",
            "enableCti": "true",
            "manager": "",
        },
        {
            "userid": "jdoe",
            "firstName": "John",
            "lastName": "Doe",
            "mailid": "jdoe@acme.com",
            "department": "Engineering",
            "title": "Software Engineer",
            "enableCti": "true",
            "manager": "msmith",
        },
        {
            "userid": "jsmith",
            "firstName": "Jane",
            "lastName": "Smith",
            "mailid": "jsmith@acme.com",
            "department": "Sales",
            "title": "Account Executive",
            "enableCti": "true",
            "manager": "",
        },
        {
            "userid": "bwilson",
            "firstName": "Bob",
            "lastName": "Wilson",
            "mailid": "bwilson@acme.com",
            "department": "Engineering",
            "title": "Support Engineer",
            "enableCti": "false",
            "manager": "jdoe",
        },
        {
            "userid": "achen",
            "firstName": "Alice",
            "lastName": "Chen",
            "mailid": "achen@acme.com",
            "department": "Branch-Austin",
            "title": "Field Engineer",
            "enableCti": "false",
            "manager": "",
        },
        {
            "userid": "legacyuser01",
            "firstName": "Legacy",
            "lastName": "User",
            "mailid": "",  # no email — edge case
            "department": "",
            "title": "",
            "enableCti": "false",
            "manager": "",
        },
        {
            "userid": "adminonly",
            "firstName": "Admin",
            "lastName": "Account",
            "mailid": "admin@acme.com",
            "department": "IT",
            "title": "System Administrator",
            "enableCti": "false",
            "manager": "",
        },
    ]

    for u in users:
        # Build optional fields
        fields = f"""<userid>{u['userid']}</userid>
            <firstName>{u['firstName']}</firstName>
            <lastName>{u['lastName']}</lastName>
            <password>Test1234!</password>
            <pin>123456</pin>
            <enableCti>{u['enableCti']}</enableCti>
            <presenceGroupName>Standard Presence group</presenceGroupName>"""

        if u["mailid"]:
            fields += f"\n            <mailid>{u['mailid']}</mailid>"
        if u["department"]:
            fields += f"\n            <department>{u['department']}</department>"
        if u["title"]:
            fields += f"\n            <title>{u['title']}</title>"
        if u["manager"]:
            fields += f"\n            <manager>{u['manager']}</manager>"

        body = f"""<ns:addEndUser><endUser>
            {fields}
        </endUser></ns:addEndUser>"""
        ok, text = axl_request(body)
        display = f"{u['userid']} ({u['firstName']} {u['lastName']})"
        if not ok and is_duplicate_error(text):
            log(phase, f"EndUser {display}", True, "(already exists)")
        else:
            log(phase, f"EndUser {display}", ok, text)


# ===================================================================
# Phase 4: Phones
# ===================================================================
def phase_4_phones() -> None:
    """Update existing phones and create new phones with line assignments."""
    phase = "Phase 4"
    print(f"\n{'='*60}")
    print(f"{phase}: Phones")
    print(f"{'='*60}")

    # ---- Update existing phones ----

    # SEP001122334455 — existing 8845, assign to jdoe, 4 lines
    body = """<ns:updatePhone>
        <name>SEP001122334455</name>
        <ownerUserName>jdoe</ownerUserName>
        <devicePoolName>DP-HQ-Phones</devicePoolName>
        <callingSearchSpaceName>Standard-Employee-CSS</callingSearchSpaceName>
        <lines>
            <line>
                <index>1</index>
                <dirn><pattern>1001</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>John Doe - 1001</label>
                <display>John Doe</display>
                <e164Mask>+14085551001</e164Mask>
                <lineAppearanceAssociatedCallingSearchSpaceName>Line-CSS</lineAppearanceAssociatedCallingSearchSpaceName>
                <associatedEndusers><enduser><userId>jdoe</userId></enduser></associatedEndusers>
                <callInfoDisplay>
                    <callerName>true</callerName>
                    <callerNumber>true</callerNumber>
                    <redirectedNumber>false</redirectedNumber>
                    <dialedNumber>true</dialedNumber>
                </callInfoDisplay>
            </line>
            <line>
                <index>2</index>
                <dirn><pattern>1050</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Team Line</label>
                <display>Team</display>
            </line>
            <line>
                <index>3</index>
                <dirn><pattern>1051</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Exec Line</label>
                <display>Exec</display>
            </line>
        </lines>
    </ns:updatePhone>"""
    ok, text = axl_request(body)
    log(phase, "Update SEP001122334455 (8845, jdoe, 3 lines + Line-CSS)", ok, text)

    # SEP74A2E69EE6D0 — existing 8851, assign to jsmith, 2 lines
    body = """<ns:updatePhone>
        <name>SEP74A2E69EE6D0</name>
        <ownerUserName>jsmith</ownerUserName>
        <devicePoolName>DP-HQ-Phones</devicePoolName>
        <callingSearchSpaceName>Standard-Employee-CSS</callingSearchSpaceName>
        <lines>
            <line>
                <index>1</index>
                <dirn><pattern>1002</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Jane Smith - 1002</label>
                <display>Jane Smith</display>
                <e164Mask>+14085551002</e164Mask>
                <associatedEndusers><enduser><userId>jsmith</userId></enduser></associatedEndusers>
            </line>
            <line>
                <index>2</index>
                <dirn><pattern>1050</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Team Line</label>
                <display>Team</display>
            </line>
        </lines>
    </ns:updatePhone>"""
    ok, text = axl_request(body)
    log(phase, "Update SEP74A2E69EE6D0 (8851, jsmith, 2 lines)", ok, text)

    # ATA001144778888 — existing ATA 191, no owner, common area
    body = """<ns:updatePhone>
        <name>ATA001144778888</name>
        <devicePoolName>DP-CommonArea</devicePoolName>
        <callingSearchSpaceName>Lobby-CSS</callingSearchSpaceName>
        <lines>
            <line>
                <index>1</index>
                <dirn><pattern>1099</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Lobby</label>
                <display>Lobby</display>
            </line>
        </lines>
    </ns:updatePhone>"""
    ok, text = axl_request(body)
    log(phase, "Update ATA001144778888 (ATA 191, lobby)", ok, text)

    # AN0011223344080 — existing Analog, no owner, Default pool
    body = """<ns:updatePhone>
        <name>AN0011223344080</name>
        <devicePoolName>Default</devicePoolName>
    </ns:updatePhone>"""
    ok, text = axl_request(body)
    log(phase, "Update AN0011223344080 (Analog SCCP, default pool)", ok, text)

    # ---- Create new phones ----

    # SEPBBCCDDEE1122 — Cisco 7841, bwilson, 2 lines + shared team line
    body = """<ns:addPhone><phone>
        <name>SEPBBCCDDEE1122</name>
        <product>Cisco 7841</product>
        <model>Cisco 7841</model>
        <class>Phone</class>
        <protocol>SIP</protocol>
        <protocolSide>User</protocolSide>
        <devicePoolName>DP-HQ-Phones</devicePoolName>
        <callingSearchSpaceName>Standard-Employee-CSS</callingSearchSpaceName>
        <commonPhoneConfigName>Standard Common Phone Profile</commonPhoneConfigName>
        <phoneTemplateName>Standard 7841 SIP</phoneTemplateName>
        <ownerUserName>bwilson</ownerUserName>
        <lines>
            <line>
                <index>1</index>
                <dirn><pattern>1003</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Bob Wilson - 1003</label>
                <display>Bob Wilson</display>
                <e164Mask>+14085551003</e164Mask>
                <associatedEndusers><enduser><userId>bwilson</userId></enduser></associatedEndusers>
            </line>
            <line>
                <index>2</index>
                <dirn><pattern>1050</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Team Line</label>
                <display>Team</display>
            </line>
        </lines>
    </phone></ns:addPhone>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "Phone SEPBBCCDDEE1122 (7841, bwilson)", True, "(already exists)")
    else:
        log(phase, "Phone SEPBBCCDDEE1122 (7841, bwilson)", ok, text)

    # SEPAABBCCDDEEFF — Cisco 8845, achen, branch, 1 line
    body = """<ns:addPhone><phone>
        <name>SEPAABBCCDDEEFF</name>
        <product>Cisco 8845</product>
        <model>Cisco 8845</model>
        <class>Phone</class>
        <protocol>SIP</protocol>
        <protocolSide>User</protocolSide>
        <devicePoolName>DP-Branch-Phones</devicePoolName>
        <callingSearchSpaceName>Standard-Employee-CSS</callingSearchSpaceName>
        <commonPhoneConfigName>Standard Common Phone Profile</commonPhoneConfigName>
        <phoneTemplateName>Standard 8845 SIP</phoneTemplateName>
        <ownerUserName>achen</ownerUserName>
        <lines>
            <line>
                <index>1</index>
                <dirn><pattern>1004</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Alice Chen - 1004</label>
                <display>Alice Chen</display>
                <e164Mask>+14085551004</e164Mask>
                <associatedEndusers><enduser><userId>achen</userId></enduser></associatedEndusers>
            </line>
        </lines>
    </phone></ns:addPhone>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "Phone SEPAABBCCDDEEFF (8845, achen)", True, "(already exists)")
    else:
        log(phase, "Phone SEPAABBCCDDEEFF (8845, achen)", ok, text)

    # CSFjdoe — Jabber CSF, jdoe, shared line 1001
    body = """<ns:addPhone><phone>
        <name>CSFjdoe</name>
        <product>Cisco Unified Client Services Framework</product>
        <model>Cisco Unified Client Services Framework</model>
        <class>Phone</class>
        <protocol>SIP</protocol>
        <protocolSide>User</protocolSide>
        <devicePoolName>DP-HQ-Softphones</devicePoolName>
        <callingSearchSpaceName>Standard-Employee-CSS</callingSearchSpaceName>
        <commonPhoneConfigName>Standard Common Phone Profile</commonPhoneConfigName>
        <phoneTemplateName>Standard Client Services Framework</phoneTemplateName>
        <ownerUserName>jdoe</ownerUserName>
        <lines>
            <line>
                <index>1</index>
                <dirn><pattern>1001</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>John Doe - 1001</label>
                <display>John Doe</display>
            </line>
            <line>
                <index>2</index>
                <dirn><pattern>1051</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Exec Line</label>
                <display>Exec</display>
            </line>
        </lines>
    </phone></ns:addPhone>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "Phone CSFjdoe (Jabber, jdoe, 2 lines)", True, "(already exists)")
    else:
        log(phase, "Phone CSFjdoe (Jabber, jdoe, 2 lines)", ok, text)

    # CSFjsmith — Jabber CSF, jsmith, shared line 1002
    body = """<ns:addPhone><phone>
        <name>CSFjsmith</name>
        <product>Cisco Unified Client Services Framework</product>
        <model>Cisco Unified Client Services Framework</model>
        <class>Phone</class>
        <protocol>SIP</protocol>
        <protocolSide>User</protocolSide>
        <devicePoolName>DP-HQ-Softphones</devicePoolName>
        <callingSearchSpaceName>Standard-Employee-CSS</callingSearchSpaceName>
        <commonPhoneConfigName>Standard Common Phone Profile</commonPhoneConfigName>
        <phoneTemplateName>Standard Client Services Framework</phoneTemplateName>
        <ownerUserName>jsmith</ownerUserName>
        <lines>
            <line>
                <index>1</index>
                <dirn><pattern>1002</pattern><routePartitionName>Internal-PT</routePartitionName></dirn>
                <label>Jane Smith - 1002</label>
                <display>Jane Smith</display>
            </line>
        </lines>
    </phone></ns:addPhone>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "Phone CSFjsmith (Jabber, jsmith)", True, "(already exists)")
    else:
        log(phase, "Phone CSFjsmith (Jabber, jsmith)", ok, text)

    # SEP112233445566 — Cisco 8845, unprovisioned, NO owner, NO lines
    body = """<ns:addPhone><phone>
        <name>SEP112233445566</name>
        <product>Cisco 8845</product>
        <model>Cisco 8845</model>
        <class>Phone</class>
        <protocol>SIP</protocol>
        <protocolSide>User</protocolSide>
        <devicePoolName>DP-HQ-Phones</devicePoolName>
        <commonPhoneConfigName>Standard Common Phone Profile</commonPhoneConfigName>
        <phoneTemplateName>Standard 8845 SIP</phoneTemplateName>
    </phone></ns:addPhone>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "Phone SEP112233445566 (8845, unprovisioned)", True, "(already exists)")
    else:
        log(phase, "Phone SEP112233445566 (8845, unprovisioned)", ok, text)


# ===================================================================
# Phase 5: Routing
# ===================================================================
def phase_5_routing() -> None:
    """Create route groups, route lists, route patterns, translation patterns."""
    phase = "Phase 5"
    print(f"\n{'='*60}")
    print(f"{phase}: Routing")
    print(f"{'='*60}")

    # --- Route Group ---
    body = """<ns:addRouteGroup><routeGroup>
        <name>RG-PSTN-Primary</name>
        <distributionAlgorithm>Top Down</distributionAlgorithm>
        <members>
            <member>
                <deviceName>sip-trunk-to-lab-cucm</deviceName>
                <port>0</port>
                <deviceSelectionOrder>1</deviceSelectionOrder>
            </member>
        </members>
    </routeGroup></ns:addRouteGroup>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "RouteGroup RG-PSTN-Primary", True, "(already exists)")
    else:
        log(phase, "RouteGroup RG-PSTN-Primary", ok, text)

    # --- Route List ---
    body = """<ns:addRouteList><routeList>
        <name>RL-PSTN</name>
        <callManagerGroupName>Default</callManagerGroupName>
        <routeListEnabled>true</routeListEnabled>
        <members>
            <member>
                <routeGroupName>RG-PSTN-Primary</routeGroupName>
                <selectionOrder>1</selectionOrder>
            </member>
        </members>
    </routeList></ns:addRouteList>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "RouteList RL-PSTN", True, "(already exists)")
    else:
        log(phase, "RouteList RL-PSTN", ok, text)

    # --- Route Patterns ---

    # 9.1[2-9]XXXXXXXXX — local/national via route list
    body = """<ns:addRoutePattern><routePattern>
        <pattern>9.1[2-9]XXXXXXXXX</pattern>
        <routePartitionName>Local-PSTN-PT</routePartitionName>
        <description>Local/National PSTN via Route List</description>
        <networkLocation>OffNet</networkLocation>
        <blockEnable>false</blockEnable>
        <destination>
            <routeListName>RL-PSTN</routeListName>
        </destination>
    </routePattern></ns:addRoutePattern>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "RoutePattern 9.1[2-9]XXXXXXXXX", True, "(already exists)")
    else:
        log(phase, "RoutePattern 9.1[2-9]XXXXXXXXX", ok, text)

    # 9.011! — international via route list
    body = """<ns:addRoutePattern><routePattern>
        <pattern>9.011!</pattern>
        <routePartitionName>International-PT</routePartitionName>
        <description>International via Route List</description>
        <networkLocation>OffNet</networkLocation>
        <blockEnable>false</blockEnable>
        <destination>
            <routeListName>RL-PSTN</routeListName>
        </destination>
    </routePattern></ns:addRoutePattern>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "RoutePattern 9.011!", True, "(already exists)")
    else:
        log(phase, "RoutePattern 9.011!", ok, text)

    # 9.1900XXXXXXX — blocked premium rate
    body = """<ns:addRoutePattern><routePattern>
        <pattern>9.1900XXXXXXX</pattern>
        <routePartitionName>Block-Premium-PT</routePartitionName>
        <description>Blocked premium rate numbers</description>
        <blockEnable>true</blockEnable>
    </routePattern></ns:addRoutePattern>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "RoutePattern 9.1900XXXXXXX (blocked)", True, "(already exists)")
    else:
        log(phase, "RoutePattern 9.1900XXXXXXX (blocked)", ok, text)

    # 0 — operator, direct to trunk
    body = """<ns:addRoutePattern><routePattern>
        <pattern>0</pattern>
        <routePartitionName>Internal-PT</routePartitionName>
        <description>Operator — direct to SIP trunk</description>
        <networkLocation>OffNet</networkLocation>
        <blockEnable>false</blockEnable>
        <destination>
            <gatewayName>sip-trunk-to-lab-cucm</gatewayName>
        </destination>
    </routePattern></ns:addRoutePattern>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "RoutePattern 0 (operator)", True, "(already exists)")
    else:
        log(phase, "RoutePattern 0 (operator)", ok, text)

    # --- Translation Patterns ---

    # 8XXX → +1408555XXXX
    body = """<ns:addTransPattern><transPattern>
        <pattern>8XXX</pattern>
        <routePartitionName>Internal-PT</routePartitionName>
        <description>4-digit to E.164 translation</description>
        <calledPartyTransformationMask>+1408555XXXX</calledPartyTransformationMask>
        <usage>Translation</usage>
    </transPattern></ns:addTransPattern>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "TransPattern 8XXX", True, "(already exists)")
    else:
        log(phase, "TransPattern 8XXX", ok, text)

    # 7X → 170X (short dial)
    body = """<ns:addTransPattern><transPattern>
        <pattern>7X</pattern>
        <routePartitionName>Internal-PT</routePartitionName>
        <description>Short dial to 4-digit translation</description>
        <calledPartyTransformationMask>170X</calledPartyTransformationMask>
        <usage>Translation</usage>
    </transPattern></ns:addTransPattern>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "TransPattern 7X", True, "(already exists)")
    else:
        log(phase, "TransPattern 7X", ok, text)


# ===================================================================
# Phase 6: Features
# ===================================================================
def phase_6_features() -> None:
    """Create hunt groups, call park, pickup groups, CTI RP, schedules."""
    phase = "Phase 6"
    print(f"\n{'='*60}")
    print(f"{phase}: Features")
    print(f"{'='*60}")

    # --- Line Groups ---
    # Sales-LG: members 1002 (jsmith), 1003 (bwilson)
    body = """<ns:addLineGroup><lineGroup>
        <name>Sales-LG</name>
        <distributionAlgorithm>Top Down</distributionAlgorithm>
        <rnaReversionTimeOut>16</rnaReversionTimeOut>
        <huntAlgorithmNoAnswer>Try next member; then, try next group in Hunt List</huntAlgorithmNoAnswer>
        <huntAlgorithmBusy>Try next member; then, try next group in Hunt List</huntAlgorithmBusy>
        <huntAlgorithmNotAvailable>Try next member; then, try next group in Hunt List</huntAlgorithmNotAvailable>
        <members>
            <member>
                <lineSelectionOrder>1</lineSelectionOrder>
                <directoryNumber>
                    <pattern>1002</pattern>
                    <routePartitionName>Internal-PT</routePartitionName>
                </directoryNumber>
            </member>
            <member>
                <lineSelectionOrder>2</lineSelectionOrder>
                <directoryNumber>
                    <pattern>1003</pattern>
                    <routePartitionName>Internal-PT</routePartitionName>
                </directoryNumber>
            </member>
        </members>
    </lineGroup></ns:addLineGroup>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "LineGroup Sales-LG", True, "(already exists)")
    else:
        log(phase, "LineGroup Sales-LG", ok, text)

    # Support-LG: members 1001 (jdoe), 1004 (achen)
    body = """<ns:addLineGroup><lineGroup>
        <name>Support-LG</name>
        <distributionAlgorithm>Longest Idle Time</distributionAlgorithm>
        <rnaReversionTimeOut>16</rnaReversionTimeOut>
        <huntAlgorithmNoAnswer>Try next member; then, try next group in Hunt List</huntAlgorithmNoAnswer>
        <huntAlgorithmBusy>Try next member; then, try next group in Hunt List</huntAlgorithmBusy>
        <huntAlgorithmNotAvailable>Try next member; then, try next group in Hunt List</huntAlgorithmNotAvailable>
        <members>
            <member>
                <lineSelectionOrder>1</lineSelectionOrder>
                <directoryNumber>
                    <pattern>1001</pattern>
                    <routePartitionName>Internal-PT</routePartitionName>
                </directoryNumber>
            </member>
            <member>
                <lineSelectionOrder>2</lineSelectionOrder>
                <directoryNumber>
                    <pattern>1004</pattern>
                    <routePartitionName>Internal-PT</routePartitionName>
                </directoryNumber>
            </member>
        </members>
    </lineGroup></ns:addLineGroup>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "LineGroup Support-LG", True, "(already exists)")
    else:
        log(phase, "LineGroup Support-LG", ok, text)

    # --- Hunt Lists ---
    body = """<ns:addHuntList><huntList>
        <name>Sales-HL</name>
        <callManagerGroupName>Default</callManagerGroupName>
        <routeListEnabled>true</routeListEnabled>
        <members>
            <member>
                <lineGroupName>Sales-LG</lineGroupName>
                <selectionOrder>1</selectionOrder>
            </member>
        </members>
    </huntList></ns:addHuntList>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "HuntList Sales-HL", True, "(already exists)")
    else:
        log(phase, "HuntList Sales-HL", ok, text)

    body = """<ns:addHuntList><huntList>
        <name>Support-HL</name>
        <callManagerGroupName>Default</callManagerGroupName>
        <routeListEnabled>true</routeListEnabled>
        <members>
            <member>
                <lineGroupName>Support-LG</lineGroupName>
                <selectionOrder>1</selectionOrder>
            </member>
        </members>
    </huntList></ns:addHuntList>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "HuntList Support-HL", True, "(already exists)")
    else:
        log(phase, "HuntList Support-HL", ok, text)

    # --- Hunt Pilots ---

    # 5001 — standard hunt pilot, forward no answer to 1099
    body = """<ns:addHuntPilot><huntPilot>
        <pattern>5001</pattern>
        <routePartitionName>Internal-PT</routePartitionName>
        <description>Sales Hunt Pilot</description>
        <huntListName>Sales-HL</huntListName>
        <forwardHuntNoAnswer>
            <usePersonalPreferences>false</usePersonalPreferences>
            <destination>1099</destination>
        </forwardHuntNoAnswer>
        <forwardHuntBusy>
            <usePersonalPreferences>false</usePersonalPreferences>
            <destination>1099</destination>
        </forwardHuntBusy>
    </huntPilot></ns:addHuntPilot>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "HuntPilot 5001 (standard)", True, "(already exists)")
    else:
        log(phase, "HuntPilot 5001 (standard)", ok, text)

    # 5002 — queue-style hunt pilot
    body = """<ns:addHuntPilot><huntPilot>
        <pattern>5002</pattern>
        <routePartitionName>Internal-PT</routePartitionName>
        <description>Support Hunt Pilot (Queue-Style)</description>
        <huntListName>Support-HL</huntListName>
        <queueCalls>
            <enabled>true</enabled>
            <maxCallersInQueue>10</maxCallersInQueue>
            <queueFullDestination>1099</queueFullDestination>
            <maxWaitTimeInQueue>120</maxWaitTimeInQueue>
            <maxWaitTimeDestination>1099</maxWaitTimeDestination>
            <noAgentDestination>1099</noAgentDestination>
            <callerIdDisplayTransformationCssName></callerIdDisplayTransformationCssName>
        </queueCalls>
        <forwardHuntNoAnswer>
            <usePersonalPreferences>false</usePersonalPreferences>
            <destination>1099</destination>
        </forwardHuntNoAnswer>
        <forwardHuntBusy>
            <usePersonalPreferences>false</usePersonalPreferences>
            <destination>1099</destination>
        </forwardHuntBusy>
    </huntPilot></ns:addHuntPilot>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "HuntPilot 5002 (queue-style)", True, "(already exists)")
    else:
        log(phase, "HuntPilot 5002 (queue-style)", ok, text)

    # --- Call Park ---
    for park_num in ["7001", "7002", "7003"]:
        body = f"""<ns:addCallPark><callPark>
            <pattern>{park_num}</pattern>
            <routePartitionName>Internal-PT</routePartitionName>
            <description>Call Park {park_num}</description>
            <callManagerName>CallManager</callManagerName>
        </callPark></ns:addCallPark>"""
        ok, text = axl_request(body)
        if not ok and is_duplicate_error(text):
            log(phase, f"CallPark {park_num}", True, "(already exists)")
        else:
            log(phase, f"CallPark {park_num}", ok, text)

    # --- Call Pickup Group ---
    body = """<ns:addCallPickupGroup><callPickupGroup>
        <name>Engineering-Pickup</name>
        <pattern>7777</pattern>
        <routePartitionName>Internal-PT</routePartitionName>
        <members>
            <member>
                <directoryNumber>
                    <pattern>1001</pattern>
                    <routePartitionName>Internal-PT</routePartitionName>
                </directoryNumber>
            </member>
            <member>
                <directoryNumber>
                    <pattern>1003</pattern>
                    <routePartitionName>Internal-PT</routePartitionName>
                </directoryNumber>
            </member>
        </members>
    </callPickupGroup></ns:addCallPickupGroup>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "CallPickupGroup Engineering-Pickup", True, "(already exists)")
    else:
        log(phase, "CallPickupGroup Engineering-Pickup", ok, text)

    # --- CTI Route Point ---
    body = """<ns:addCtiRoutePoint><ctiRoutePoint>
        <name>CTIAA-MainMenu</name>
        <product>CTI Route Point</product>
        <model>CTI Route Point</model>
        <class>CTI Route Point</class>
        <protocol>SIP</protocol>
        <protocolSide>User</protocolSide>
        <devicePoolName>DP-HQ-Phones</devicePoolName>
        <callingSearchSpaceName>Standard-Employee-CSS</callingSearchSpaceName>
        <lines>
            <line>
                <index>1</index>
                <dirn>
                    <pattern>6001</pattern>
                    <routePartitionName>Internal-PT</routePartitionName>
                </dirn>
                <label>Main Menu AA</label>
                <display>Auto Attendant</display>
            </line>
        </lines>
    </ctiRoutePoint></ns:addCtiRoutePoint>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "CtiRoutePoint CTIAA-MainMenu", True, "(already exists)")
    else:
        log(phase, "CtiRoutePoint CTIAA-MainMenu", ok, text)

    # --- Time Periods ---

    # Business-Hours-Period: Mon-Fri 08:00-17:00
    body = """<ns:addTimePeriod><timePeriod>
        <name>Business-Hours-Period</name>
        <startTime>08:00</startTime>
        <endTime>17:00</endTime>
        <startDay>Mon</startDay>
        <endDay>Fri</endDay>
        <monthOfYear>None</monthOfYear>
        <dayOfMonth>0</dayOfMonth>
    </timePeriod></ns:addTimePeriod>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "TimePeriod Business-Hours-Period", True, "(already exists)")
    else:
        log(phase, "TimePeriod Business-Hours-Period", ok, text)

    # After-Hours-Period: Mon-Fri 17:00-08:00
    body = """<ns:addTimePeriod><timePeriod>
        <name>After-Hours-Period</name>
        <startTime>17:00</startTime>
        <endTime>08:00</endTime>
        <startDay>Mon</startDay>
        <endDay>Fri</endDay>
        <monthOfYear>None</monthOfYear>
        <dayOfMonth>0</dayOfMonth>
    </timePeriod></ns:addTimePeriod>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "TimePeriod After-Hours-Period", True, "(already exists)")
    else:
        log(phase, "TimePeriod After-Hours-Period", ok, text)

    # --- Time Schedule ---
    body = """<ns:addTimeSchedule><timeSchedule>
        <name>Business-Hours-Schedule</name>
        <members>
            <member>
                <timePeriodName>Business-Hours-Period</timePeriodName>
            </member>
            <member>
                <timePeriodName>After-Hours-Period</timePeriodName>
            </member>
        </members>
    </timeSchedule></ns:addTimeSchedule>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "TimeSchedule Business-Hours-Schedule", True, "(already exists)")
    else:
        log(phase, "TimeSchedule Business-Hours-Schedule", ok, text)


# ===================================================================
# Phase 7: Voicemail
# ===================================================================
def phase_7_voicemail() -> None:
    """Create voicemail pilot, update VM profile, assign to users."""
    phase = "Phase 7"
    print(f"\n{'='*60}")
    print(f"{phase}: Voicemail")
    print(f"{'='*60}")

    # --- Voicemail Pilot ---
    body = """<ns:addVoiceMailPilot><voiceMailPilot>
        <dirn>8000</dirn>
        <description>Main VM Pilot</description>
        <callingSearchSpaceName>Standard-Employee-CSS</callingSearchSpaceName>
    </voiceMailPilot></ns:addVoiceMailPilot>"""
    ok, text = axl_request(body)
    if not ok and is_duplicate_error(text):
        log(phase, "VoiceMailPilot 8000", True, "(already exists)")
    else:
        log(phase, "VoiceMailPilot 8000", ok, text)

    # --- Update Default VM Profile to reference pilot 8000 ---
    body = """<ns:updateVoiceMailProfile>
        <name>Default</name>
        <voiceMailPilot>8000</voiceMailPilot>
    </ns:updateVoiceMailProfile>"""
    ok, text = axl_request(body)
    if not ok:
        # If "Default" doesn't exist, try "NoVoiceMail" (some CUCM installs)
        body_alt = """<ns:updateVoiceMailProfile>
            <name>NoVoiceMail</name>
            <voiceMailPilot>8000</voiceMailPilot>
        </ns:updateVoiceMailProfile>"""
        ok2, text2 = axl_request(body_alt)
        if ok2:
            log(phase, "Update VM Profile (NoVoiceMail) → pilot 8000", True, "")
        else:
            log(phase, "Update Default VM Profile → pilot 8000", False, text)
    else:
        log(phase, "Update Default VM Profile → pilot 8000", True, "")

    # --- Set voicemail profile on user primary DNs ---
    # In AXL the voiceMailProfile is a line-level setting, not user-level.
    for pattern, userid in [("1001", "jdoe"), ("1002", "jsmith"), ("1004", "achen")]:
        body = f"""<ns:updateLine>
            <pattern>{pattern}</pattern>
            <routePartitionName>Internal-PT</routePartitionName>
            <voiceMailProfileName>Default</voiceMailProfileName>
        </ns:updateLine>"""
        ok, text = axl_request(body)
        log(phase, f"Line {pattern} VM profile → Default ({userid})", ok, text)


# ===================================================================
# Phase 8: User-Device Associations
# ===================================================================
def phase_8_associations() -> None:
    """Associate devices to users and set user CSSes."""
    phase = "Phase 8"
    print(f"\n{'='*60}")
    print(f"{phase}: User-Device Associations")
    print(f"{'='*60}")

    # --- Associate devices to users ---
    user_devices = [
        ("jdoe", ["SEP001122334455", "CSFjdoe"]),
        ("jsmith", ["SEP74A2E69EE6D0", "CSFjsmith"]),
        ("bwilson", ["SEPBBCCDDEE1122"]),
        ("achen", ["SEPAABBCCDDEEFF"]),
    ]

    for userid, devices in user_devices:
        device_xml = "".join(f"<device>{d}</device>" for d in devices)
        body = f"""<ns:updateEndUser>
            <userid>{userid}</userid>
            <associatedDevices>{device_xml}</associatedDevices>
            <primaryExtension>
                <pattern>{_user_primary_dn(userid)}</pattern>
                <routePartitionName>Internal-PT</routePartitionName>
            </primaryExtension>
        </ns:updateEndUser>"""
        ok, text = axl_request(body)
        device_list = ", ".join(devices)
        log(phase, f"Associate {userid} → [{device_list}]", ok, text)

    # --- Set user CSSes ---
    user_css = [
        ("jdoe", "Executive-CSS"),
        ("jsmith", "Standard-Employee-CSS"),
        ("bwilson", "Standard-Employee-CSS"),
        ("achen", "Standard-Employee-CSS"),
        ("legacyuser01", "Restricted-CSS"),
    ]

    for userid, css in user_css:
        body = f"""<ns:updateEndUser>
            <userid>{userid}</userid>
            <callingSearchSpaceName>{css}</callingSearchSpaceName>
        </ns:updateEndUser>"""
        ok, text = axl_request(body)
        log(phase, f"User {userid} CSS → {css}", ok, text)


def _user_primary_dn(userid: str) -> str:
    """Map a userid to its primary directory number."""
    return {
        "jdoe": "1001",
        "jsmith": "1002",
        "bwilson": "1003",
        "achen": "1004",
    }[userid]


# ===================================================================
# Summary
# ===================================================================
def print_summary() -> None:
    """Print final summary of all operations."""
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    total = len(results)
    passed = sum(1 for _, _, ok in results if ok)
    failed = total - passed

    # Group by phase
    phases: dict[str, list[tuple[str, bool]]] = {}
    for phase, desc, ok in results:
        phases.setdefault(phase, []).append((desc, ok))

    for phase, items in phases.items():
        phase_ok = sum(1 for _, ok in items if ok)
        phase_fail = len(items) - phase_ok
        status = "ALL PASS" if phase_fail == 0 else f"{phase_fail} FAILED"
        print(f"  {phase}: {phase_ok}/{len(items)} passed ({status})")

    print(f"\n  TOTAL: {passed}/{total} passed, {failed} failed")

    if failed > 0:
        print(f"\n  Failed operations:")
        for phase, desc, ok in results:
            if not ok:
                print(f"    [{phase}] {desc}")


# ===================================================================
# Main
# ===================================================================
def main() -> None:
    """Run all phases in dependency order."""
    print("CUCM Lab Test Bed Provisioner")
    print(f"Target: {HOST}:8443 (AXL v15.0)")
    print(f"{'='*60}")

    # Quick connectivity check
    print("\nConnectivity check...")
    ok, text = axl_request("""<ns:getCCMVersion></ns:getCCMVersion>""")
    if ok:
        match = re.search(r"<version>(.*?)</version>", text)
        ver = match.group(1) if match else "unknown"
        print(f"  Connected to CUCM version {ver}")
    else:
        print(f"  WARNING: Could not verify CUCM version. Proceeding anyway...")
        print(f"  Response: {text[:200]}")

    phase_1_infrastructure()
    phase_2_lines()
    phase_3_users()
    phase_4_phones()
    phase_5_routing()
    phase_6_features()
    phase_7_voicemail()
    phase_8_associations()

    print_summary()

    # Exit with error code if anything failed
    failed = sum(1 for _, _, ok in results if not ok)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
