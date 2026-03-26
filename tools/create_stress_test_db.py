#!/usr/bin/env python3.11
"""Create a stress-test migration database for bulk execution testing.

Simulates a realistic enterprise "GlobalTech Industries" CUCM 14.0 environment
with 500+ objects producing 650+ operations — the kind of complexity you'd find
in a 500-person company with 10 offices.

Constrained to 20 Webex Calling user licenses. Everything else scales to
realistic enterprise levels.

Usage:
    PYTHONPATH=. python3.11 tools/create_stress_test_db.py [project-name]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from wxcli.migration.models import (
    CanonicalAutoAttendant,
    CanonicalCallPark,
    CanonicalCallQueue,
    CanonicalCallingPermission,
    CanonicalDevice,
    CanonicalDialPlan,
    CanonicalHuntGroup,
    CanonicalLocation,
    CanonicalLocationSchedule,
    CanonicalOperatingMode,
    CanonicalPagingGroup,
    CanonicalPickupGroup,
    CanonicalRouteGroup,
    CanonicalSharedLine,
    CanonicalTranslationPattern,
    CanonicalTrunk,
    CanonicalUser,
    CanonicalVirtualLine,
    CanonicalWorkspace,
    CallingPermissionEntry,
    DeviceCompatibilityTier,
    LocationAddress,
    MigrationStatus,
    Provenance,
    TrunkGatewayRef,
)
from wxcli.migration.store import MigrationStore

PROJECT_NAME = sys.argv[1] if len(sys.argv) > 1 else "stress-test"
MIGRATIONS_DIR = Path.home() / ".wxcli" / "migrations"
PROJECT_DIR = MIGRATIONS_DIR / PROJECT_NAME
DB_PATH = PROJECT_DIR / "migration.db"
STATE_PATH = PROJECT_DIR / "state.json"

S = MigrationStatus.ANALYZED
_mac_counter = 0


def _p(sid: str, sname: str) -> Provenance:
    return Provenance(source_system="cucm", source_id=sid, source_name=sname,
                      extracted_at=datetime.now(timezone.utc))


def _mac() -> str:
    global _mac_counter
    _mac_counter += 1
    return f"AABBCC{_mac_counter:06X}"


def main():
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    from wxcli.migration.state import MigrationState, ProjectState
    if STATE_PATH.exists():
        STATE_PATH.unlink()
    ms = MigrationState.create(STATE_PATH, PROJECT_NAME)
    ms.transition(ProjectState.CONNECTED)
    ms.transition(ProjectState.DISCOVERED)
    ms.transition(ProjectState.ANALYZED)
    sd = json.loads(STATE_PATH.read_text())
    sd["completed_stages"] = ["init", "discover", "normalize", "map", "analyze"]
    STATE_PATH.write_text(json.dumps(sd, indent=2))

    current_file = Path.home() / ".wxcli" / "current_project"
    current_file.parent.mkdir(parents=True, exist_ok=True)
    current_file.write_text(PROJECT_NAME)

    if DB_PATH.exists():
        DB_PATH.unlink()
    store = MigrationStore(DB_PATH)
    counts = {}

    # =================================================================
    # LOCATIONS (10)
    # =================================================================
    loc_defs = [
        ("location:hq-nyc", "GlobalTech HQ - New York", "America/New_York",
         "350 Fifth Avenue", "New York", "NY", "10118"),
        ("location:reg-west-la", "GlobalTech West - Los Angeles", "America/Los_Angeles",
         "633 W 5th Street", "Los Angeles", "CA", "90071"),
        ("location:reg-central-chi", "GlobalTech Central - Chicago", "America/Chicago",
         "233 S Wacker Dr", "Chicago", "IL", "60606"),
        ("location:reg-south-dal", "GlobalTech South - Dallas", "America/Chicago",
         "2711 N Haskell Ave", "Dallas", "TX", "75204"),
        ("location:reg-east-bos", "GlobalTech East - Boston", "America/New_York",
         "100 Federal St", "Boston", "MA", "02110"),
        ("location:sat-portland", "GlobalTech Portland", "America/Los_Angeles",
         "1120 NW Couch St", "Portland", "OR", "97209"),
        ("location:sat-denver", "GlobalTech Denver", "America/Denver",
         "1801 California St", "Denver", "CO", "80202"),
        ("location:sat-atlanta", "GlobalTech Atlanta", "America/New_York",
         "191 Peachtree St NE", "Atlanta", "GA", "30303"),
        ("location:dc-ashburn", "GlobalTech DC - Ashburn", "America/New_York",
         "44060 Digital Loudoun Plaza", "Ashburn", "VA", "20147"),
        ("location:remote-wfh", "GlobalTech Remote Workers", "America/New_York",
         "350 Fifth Avenue", "New York", "NY", "10118"),
    ]
    for cid, name, tz, addr, city, state, zip_ in loc_defs:
        store.upsert_object(CanonicalLocation(
            canonical_id=cid, provenance=_p(f"DP_{cid.split(':')[1].upper()}", name),
            name=name, time_zone=tz, preferred_language="en_US",
            announcement_language="en_us",
            address=LocationAddress(address1=addr, city=city, state=state,
                                    postal_code=zip_, country="US"),
            status=S,
        ))
    counts["Locations"] = len(loc_defs)

    # Location lookup helpers
    loc_ids = [l[0] for l in loc_defs]
    main_locs = loc_ids[:5]  # HQ + 4 regional
    all_office_locs = loc_ids[:8]  # everything except DC + remote

    # =================================================================
    # USERS (20) — spread across locations
    # =================================================================
    user_defs = [
        ("user:jcarter", "jcarter@globaltech.com", "Jane", "Carter", "location:hq-nyc", "1001", "CEO", "Executive"),
        ("user:mchen", "mchen@globaltech.com", "Michael", "Chen", "location:hq-nyc", "1002", "CFO", "Executive"),
        ("user:srivera", "srivera@globaltech.com", "Sarah", "Rivera", "location:hq-nyc", "1003", "CTO", "Executive"),
        ("user:dkumar", "dkumar@globaltech.com", "Dev", "Kumar", "location:hq-nyc", "1010", "IT Director", "IT"),
        ("user:lwilson", "lwilson@globaltech.com", "Lisa", "Wilson", "location:hq-nyc", "1011", "Net Admin", "IT"),
        ("user:rpatel", "rpatel@globaltech.com", "Raj", "Patel", "location:hq-nyc", "1012", "Sys Admin", "IT"),
        ("user:tmorris", "tmorris@globaltech.com", "Tom", "Morris", "location:reg-west-la", "2001", "VP Sales", "Sales"),
        ("user:klee", "klee@globaltech.com", "Karen", "Lee", "location:reg-west-la", "2002", "Sales Dir", "Sales"),
        ("user:jgarcia", "jgarcia@globaltech.com", "Juan", "Garcia", "location:reg-west-la", "2003", "Account Exec", "Sales"),
        ("user:mkim", "mkim@globaltech.com", "Min", "Kim", "location:reg-central-chi", "3001", "Sales Rep", "Sales"),
        ("user:cwhite", "cwhite@globaltech.com", "Carol", "White", "location:reg-central-chi", "3002", "Sales Rep", "Sales"),
        ("user:arobinson", "arobinson@globaltech.com", "Alex", "Robinson", "location:reg-central-chi", "3003", "Sales Ops", "Sales"),
        ("user:jthompson", "jthompson@globaltech.com", "Jessica", "Thompson", "location:reg-south-dal", "4001", "Support Mgr", "Support"),
        ("user:rdiaz", "rdiaz@globaltech.com", "Roberto", "Diaz", "location:reg-south-dal", "4002", "Support L2", "Support"),
        ("user:psmith", "psmith@globaltech.com", "Patricia", "Smith", "location:reg-south-dal", "4003", "Support L1", "Support"),
        ("user:nwang", "nwang@globaltech.com", "Nina", "Wang", "location:reg-east-bos", "5001", "Eng Manager", "Engineering"),
        ("user:dhall", "dhall@globaltech.com", "Derek", "Hall", "location:reg-east-bos", "5002", "Sr Engineer", "Engineering"),
        ("user:emartinez", "emartinez@globaltech.com", "Elena", "Martinez", "location:sat-portland", "6001", "Field Sales", "Sales"),
        ("user:bjones", "bjones@globaltech.com", "Brian", "Jones", "location:sat-denver", "7001", "Field Sales", "Sales"),
        ("user:anguyen", "anguyen@globaltech.com", "Amy", "Nguyen", "location:remote-wfh", "8001", "Solutions Arch", "Engineering"),
    ]
    users_by_loc = {}
    for cid, email, first, last, loc, ext, title, dept in user_defs:
        store.upsert_object(CanonicalUser(
            canonical_id=cid, provenance=_p(f"EU_{email.split('@')[0]}", email),
            emails=[email], first_name=first, last_name=last,
            display_name=f"{first} {last}", location_id=loc, extension=ext,
            title=title, department=dept, status=S,
        ))
        store.add_cross_ref(cid, loc, "user_in_location")
        users_by_loc.setdefault(loc, []).append(cid)
    counts["Users"] = len(user_defs)

    # =================================================================
    # WORKSPACES (55) — every conference room, lobby, huddle, break room,
    # kitchen, elevator phone, parking garage, security desk, loading dock
    # =================================================================
    ws_defs = []

    # Per-location standard workspaces
    ws_templates = {
        "location:hq-nyc": [
            ("Main Lobby", "other"), ("Visitor Lobby", "other"),
            ("Board Room", "meetingRoom"), ("Exec Conference", "meetingRoom"),
            ("Conf Room 3A", "meetingRoom"), ("Conf Room 3B", "meetingRoom"),
            ("Conf Room 4A", "meetingRoom"), ("Conf Room 4B", "meetingRoom"),
            ("Huddle 1", "meetingRoom"), ("Huddle 2", "meetingRoom"),
            ("Huddle 3", "meetingRoom"),
            ("Break Room 2F", "other"), ("Break Room 4F", "other"),
            ("Kitchen", "other"), ("Security Desk", "other"),
            ("Parking Garage", "other"), ("Loading Dock", "other"),
            ("Server Room", "other"),
        ],
        "location:reg-west-la": [
            ("Lobby", "other"), ("Conf Room A", "meetingRoom"),
            ("Conf Room B", "meetingRoom"), ("Huddle", "meetingRoom"),
            ("Break Room", "other"), ("Elevator Phone", "other"),
        ],
        "location:reg-central-chi": [
            ("Lobby", "other"), ("Conf Room A", "meetingRoom"),
            ("Conf Room B", "meetingRoom"), ("Huddle", "meetingRoom"),
            ("Break Room", "other"),
        ],
        "location:reg-south-dal": [
            ("Lobby", "other"), ("Training Room", "meetingRoom"),
            ("Conf Room", "meetingRoom"), ("Break Room", "other"),
        ],
        "location:reg-east-bos": [
            ("Lobby", "other"), ("Lab Conf Room", "meetingRoom"),
            ("Conf Room", "meetingRoom"), ("Break Room", "other"),
        ],
        "location:sat-portland": [
            ("Lobby", "other"), ("Conf Room", "meetingRoom"),
        ],
        "location:sat-denver": [
            ("Lobby", "other"), ("Conf Room", "meetingRoom"),
        ],
        "location:sat-atlanta": [
            ("Lobby", "other"), ("Conf Room", "meetingRoom"),
        ],
        "location:dc-ashburn": [
            ("NOC Station 1", "other"), ("NOC Station 2", "other"),
            ("NOC Station 3", "other"), ("Ops Conf Room", "meetingRoom"),
            ("Cage Phone A", "other"), ("Cage Phone B", "other"),
        ],
    }

    ext_counter = {}
    for loc, templates in ws_templates.items():
        tag = loc.split(":")[1].replace("-", "")
        base_ext = {"hq-nyc": 1100, "reg-west-la": 2100, "reg-central-chi": 3100,
                    "reg-south-dal": 4100, "reg-east-bos": 5100,
                    "sat-portland": 6100, "sat-denver": 7100,
                    "sat-atlanta": 7200, "dc-ashburn": 9100}[loc.split(":")[1]]
        for i, (name, wtype) in enumerate(templates):
            loc_tag = loc.split(":")[1].split("-")[-1].upper()[:3]
            cid = f"workspace:{tag}-{i:02d}"
            ext = str(base_ext + i)
            ws_defs.append((cid, f"{loc_tag} {name}", loc, ext, wtype))

    for cid, name, loc, ext, wtype in ws_defs:
        store.upsert_object(CanonicalWorkspace(
            canonical_id=cid, provenance=_p(f"CAP_{cid.split(':')[1]}", name),
            display_name=name, location_id=loc, extension=ext,
            supported_devices="phones", workspace_type=wtype,
            hotdesking_status="off", is_common_area=True, status=S,
        ))
        store.add_cross_ref(cid, loc, "workspace_in_location")
    counts["Workspaces"] = len(ws_defs)

    # =================================================================
    # DEVICES (75) — 19 user phones + 55 workspace phones + 1 spare
    # =================================================================
    dev_list = []

    # User phones
    user_phone_models = {
        "user:jcarter": "Cisco 8865", "user:mchen": "Cisco 8865",
        "user:srivera": "Cisco 8865", "user:dkumar": "Cisco 8865",
        "user:lwilson": "Cisco 8845", "user:rpatel": "Cisco 8845",
        "user:tmorris": "Cisco 8865", "user:klee": "Cisco 8845",
        "user:jgarcia": "Cisco 8845", "user:mkim": "Cisco 8845",
        "user:cwhite": "Cisco 8845", "user:arobinson": "Cisco 8845",
        "user:jthompson": "Cisco 8845", "user:rdiaz": "Cisco 8845",
        "user:psmith": "Cisco 8845", "user:nwang": "Cisco 8865",
        "user:dhall": "Cisco 8845",
        "user:emartinez": "Cisco 8851", "user:bjones": "Cisco 8851",
        # anguyen is softphone-only — no device object
    }
    for user_cid, model in user_phone_models.items():
        loc = next(u[4] for u in user_defs if u[0] == user_cid)
        mac = _mac()
        dev_list.append((f"device:{mac.lower()}", mac, model, user_cid, loc))

    # Workspace phones — ATA for lobbies/utility, 8845 for conf rooms
    for ws_cid, ws_name, ws_loc, _, ws_type in ws_defs:
        if "Lobby" in ws_name or "Security" in ws_name or "Parking" in ws_name \
                or "Loading" in ws_name or "Elevator" in ws_name or "Cage" in ws_name:
            model = "Cisco 192"
        elif "NOC" in ws_name or "Ops" in ws_name or "Server" in ws_name:
            model = "Cisco 8845"
        else:
            model = "Cisco 8845"
        mac = _mac()
        dev_list.append((f"device:{mac.lower()}", mac, model, ws_cid, ws_loc))

    for cid, mac, model, owner_cid, loc_cid in dev_list:
        store.upsert_object(CanonicalDevice(
            canonical_id=cid, provenance=_p(f"SEP{mac}", mac),
            mac=mac, model=model, compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
            display_name=f"{model} ({mac})", owner_canonical_id=owner_cid,
            location_canonical_id=loc_cid, status=S,
        ))
        if owner_cid:
            store.add_cross_ref(cid, owner_cid, "device_owner")
        store.add_cross_ref(cid, loc_cid, "device_in_location")
    counts["Devices"] = len(dev_list)

    # =================================================================
    # TRUNKS (4) + ROUTE GROUPS (3)
    # =================================================================
    trunk_defs = [
        ("trunk:sbc-hq", "HQ Primary SBC", "location:hq-nyc", "REGISTERING"),
        ("trunk:sbc-west", "West Coast SBC", "location:reg-west-la", "REGISTERING"),
        ("trunk:sbc-failover", "Failover SBC", "location:dc-ashburn", "CERTIFICATE_BASED"),
        ("trunk:teams-interop", "Teams Interop Trunk", "location:hq-nyc", "REGISTERING"),
    ]
    for cid, name, loc, ttype in trunk_defs:
        trunk_kwargs = dict(
            canonical_id=cid, provenance=_p(f"GW_{cid.split(':')[1].upper()}", name),
            name=name, location_id=loc, trunk_type=ttype, status=S,
        )
        trunk_kwargs["password"] = "GlobalTech2024Pass"
        if ttype == "CERTIFICATE_BASED":
            trunk_kwargs["address"] = "sbc-failover.globaltech.com"
            trunk_kwargs["domain"] = "globaltech.com"
            trunk_kwargs["max_concurrent_calls"] = 250
        store.upsert_object(CanonicalTrunk(**trunk_kwargs))
        store.add_cross_ref(cid, loc, "trunk_in_location")
    counts["Trunks"] = len(trunk_defs)

    rg_defs = [
        ("route_group:primary-rg", "Primary Route Group",
         [TrunkGatewayRef(trunk_canonical_id="trunk:sbc-hq", priority=1),
          TrunkGatewayRef(trunk_canonical_id="trunk:sbc-west", priority=2)]),
        ("route_group:failover-rg", "Failover Route Group",
         [TrunkGatewayRef(trunk_canonical_id="trunk:sbc-failover", priority=1)]),
        ("route_group:teams-rg", "Teams Interop Route Group",
         [TrunkGatewayRef(trunk_canonical_id="trunk:teams-interop", priority=1)]),
    ]
    for cid, name, gws in rg_defs:
        store.upsert_object(CanonicalRouteGroup(
            canonical_id=cid, provenance=_p(f"RG_{cid.split(':')[1].upper()}", name),
            name=name, local_gateways=gws, status=S,
        ))
    counts["Route Groups"] = len(rg_defs)

    # =================================================================
    # DIAL PLANS (15)
    # =================================================================
    dp_defs = [
        ("dial_plan:us-local", "US Local Calls", ["+1[2-9]XX[2-9]XXXXXX"], "trunk:sbc-hq", "TRUNK"),
        ("dial_plan:us-long-distance", "US Long Distance", ["1[2-9]XX[2-9]XXXXXX"], "route_group:primary-rg", "ROUTE_GROUP"),
        ("dial_plan:international", "International", ["011!"], "route_group:primary-rg", "ROUTE_GROUP"),
        ("dial_plan:emergency-911", "Emergency 911", ["911"], "trunk:sbc-hq", "TRUNK"),
        ("dial_plan:emergency-933", "Emergency 933 Test", ["933"], "trunk:sbc-hq", "TRUNK"),
        ("dial_plan:toll-free-800", "Toll Free 800", ["1800XXXXXXX"], "trunk:sbc-hq", "TRUNK"),
        ("dial_plan:toll-free-888", "Toll Free 888", ["1888XXXXXXX"], "trunk:sbc-hq", "TRUNK"),
        ("dial_plan:toll-free-877", "Toll Free 877", ["1877XXXXXXX"], "trunk:sbc-hq", "TRUNK"),
        ("dial_plan:toll-free-866", "Toll Free 866", ["1866XXXXXXX"], "trunk:sbc-hq", "TRUNK"),
        ("dial_plan:premium-block-900", "Premium Block 900", ["1900XXXXXXX"], "trunk:sbc-hq", "TRUNK"),
        ("dial_plan:premium-block-976", "Premium Block 976", ["1976XXXXXXX"], "trunk:sbc-hq", "TRUNK"),
        ("dial_plan:teams-seattle", "Teams PSTN Seattle", ["+1206!"], "route_group:teams-rg", "ROUTE_GROUP"),
        ("dial_plan:teams-redmond", "Teams PSTN Redmond", ["+1425!"], "route_group:teams-rg", "ROUTE_GROUP"),
        ("dial_plan:site-codes", "Inter-Site Dialing", ["8XXX"], "route_group:primary-rg", "ROUTE_GROUP"),
        ("dial_plan:operator", "Operator Dial 0", ["00"], "trunk:sbc-hq", "TRUNK"),
    ]
    for cid, name, patterns, route, rtype in dp_defs:
        store.upsert_object(CanonicalDialPlan(
            canonical_id=cid, provenance=_p(f"DP_{cid.split(':')[1].upper()}", name),
            name=name, dial_patterns=patterns, route_id=route, route_type=rtype, status=S,
        ))
    counts["Dial Plans"] = len(dp_defs)

    # =================================================================
    # TRANSLATION PATTERNS (60) — realistic CUCM routing complexity
    # =================================================================
    tp_defs = [
        # Access code stripping (5) — fixed replacements (no wildcards in replacement)
        ("strip-9-local", "Strip 9 Local", "91234567890", "1234567890"),
        ("strip-9-ld", "Strip 9 Long Distance", "912125551234", "+12125551234"),
        ("strip-9-intl", "Strip 9 International", "901144201234", "+44201234"),
        ("strip-8-site", "Strip 8 Site Code", "81000", "1000"),
        ("strip-7-vm", "Strip 7 Voicemail", "71000", "1000"),
        # E.164 normalization (10) — fixed E.164 replacements (no wildcards)
        ("e164-10d", "E164 10-Digit", "[2-9]XXXXXXXXX", "+12125550100"),
        ("e164-11d", "E164 11-Digit", "1[2-9]XXXXXXXXX", "+12125550101"),
        ("e164-7d-nyc-212", "E164 7-Digit NYC 212", "212XXXXXXX", "+12120000000"),
        ("e164-7d-nyc-646", "E164 7-Digit NYC 646", "646XXXXXXX", "+16460000000"),
        ("e164-7d-la-310", "E164 7-Digit LA 310", "310XXXXXXX", "+13100000000"),
        ("e164-7d-la-213", "E164 7-Digit LA 213", "213XXXXXXX", "+12130000000"),
        ("e164-7d-chi-312", "E164 7-Digit CHI 312", "312XXXXXXX", "+13120000000"),
        ("e164-7d-chi-773", "E164 7-Digit CHI 773", "773XXXXXXX", "+17730000000"),
        ("e164-7d-dal-214", "E164 7-Digit DAL 214", "214XXXXXXX", "+12140000000"),
        ("e164-7d-bos-617", "E164 7-Digit BOS 617", "617XXXXXXX", "+16170000000"),
        # Site codes (10) — fixed replacements (no wildcards)
        ("site-hq-1", "Site Code HQ 1xxx", "810XX", "+12125551000"),
        ("site-hq-2", "Site Code HQ 1Xxx High", "811XX", "+12125551100"),
        ("site-west", "Site Code West", "820XX", "+13105552000"),
        ("site-central", "Site Code Central", "830XX", "+13125553000"),
        ("site-south", "Site Code South", "840XX", "+12145554000"),
        ("site-east", "Site Code East", "850XX", "+16175555000"),
        ("site-pdx", "Site Code Portland", "860XX", "+15035556000"),
        ("site-den", "Site Code Denver", "870XX", "+17205557000"),
        ("site-atl", "Site Code Atlanta", "872XX", "+14045558000"),
        ("site-dc", "Site Code DC", "890XX", "+17035559000"),
        # Caller ID masking per location (10) — fixed E.164 replacements (no X wildcards)
        ("clid-hq-main", "CallerID HQ Main", "10XX", "+12125551000"),
        ("clid-hq-it", "CallerID HQ IT", "101X", "+12125550000"),
        ("clid-la", "CallerID LA", "20XX", "+13105552000"),
        ("clid-chi", "CallerID CHI", "30XX", "+13125553000"),
        ("clid-dal", "CallerID DAL", "40XX", "+12145554000"),
        ("clid-bos", "CallerID BOS", "50XX", "+16175555000"),
        ("clid-pdx", "CallerID Portland", "60XX", "+15035556000"),
        ("clid-den", "CallerID Denver", "70XX", "+17205557000"),
        ("clid-atl", "CallerID Atlanta", "72XX", "+14045558000"),
        ("clid-dc", "CallerID DC", "90XX", "+17035559000"),
        # ELIN emergency callback numbers per location (10) — unique matching patterns
        ("elin-hq-2f", "ELIN HQ Floor 2", "9331", "+12125559901"),
        ("elin-hq-3f", "ELIN HQ Floor 3", "9332", "+12125559902"),
        ("elin-hq-4f", "ELIN HQ Floor 4", "9333", "+12125559903"),
        ("elin-la", "ELIN LA", "9334", "+13105559911"),
        ("elin-chi", "ELIN CHI", "9335", "+13125559911"),
        ("elin-dal", "ELIN DAL", "9336", "+12145559911"),
        ("elin-bos", "ELIN BOS", "9337", "+16175559911"),
        ("elin-pdx", "ELIN Portland", "9338", "+15035559911"),
        ("elin-den", "ELIN Denver", "9339", "+17205559911"),
        ("elin-dc", "ELIN DC", "9340", "+17035559911"),
        # Special translations (5) — all fixed replacements
        ("operator-0", "Operator Dial 0", "0", "1000"),
        ("dir-411", "Directory 411", "411", "1411"),
        ("intl-plus", "International Plus Prefix", "011XX", "+44200000"),
        ("star-codes-vm", "Star Code Voicemail", "*86", "7999"),
        ("star-codes-park", "Star Code Park", "*68", "1900"),
    ]
    for tag, name, match, replace in tp_defs:
        store.upsert_object(CanonicalTranslationPattern(
            canonical_id=f"translation_pattern:{tag}",
            provenance=_p(f"TP_{tag.upper()}", name),
            name=name, matching_pattern=match, replacement_pattern=replace, status=S,
        ))
    counts["Translation Patterns"] = len(tp_defs)

    # =================================================================
    # SCHEDULES (24) — business hours per region + holidays + special
    # =================================================================
    sched_ids = {}

    biz_scheds = [
        ("biz-eastern-standard", "Eastern Standard Hours", "location:hq-nyc", "08:00", "17:00"),
        ("biz-eastern-extended", "Eastern Extended Hours", "location:hq-nyc", "07:00", "20:00"),
        ("biz-central-standard", "Central Standard Hours", "location:reg-central-chi", "08:00", "17:00"),
        ("biz-mountain-standard", "Mountain Standard Hours", "location:sat-denver", "08:00", "17:00"),
        ("biz-pacific-standard", "Pacific Standard Hours", "location:reg-west-la", "08:00", "17:00"),
        ("biz-pacific-extended", "Pacific Extended Hours", "location:reg-west-la", "07:00", "19:00"),
        ("biz-support-12hr", "Support 12-Hour", "location:reg-south-dal", "07:00", "19:00"),
        ("biz-support-extended", "Support Extended 14hr", "location:reg-south-dal", "06:00", "20:00"),
        ("biz-dc-24x7", "DC 24x7 Operations", "location:dc-ashburn", "00:00", "23:59"),
        ("biz-eastern-bos", "Eastern Standard Hours", "location:reg-east-bos", "08:00", "17:00"),
        ("biz-pacific-pdx", "Pacific Standard Hours", "location:sat-portland", "08:00", "17:00"),
        ("biz-eastern-atl", "Eastern Standard Hours", "location:sat-atlanta", "08:00", "17:00"),
        ("biz-saturday-hq", "Saturday Hours HQ", "location:hq-nyc", "09:00", "13:00"),
        ("biz-saturday-la", "Saturday Hours LA", "location:reg-west-la", "10:00", "14:00"),
    ]
    def _biz_event(name, start, end, days=None):
        """Build a Webex-compatible business hours event with recurrence.

        startDate/endDate define ONE occurrence (same day). The recurrence
        object controls the repeat pattern. Duration must be < recurrence period.
        """
        if days is None:
            days = {"monday": True, "tuesday": True, "wednesday": True,
                    "thursday": True, "friday": True, "saturday": False, "sunday": False}
        return {
            "name": name, "startDate": "2026-01-05", "endDate": "2026-01-05",
            "startTime": start, "endTime": end, "allDayEnabled": False,
            "recurrence": {"recurForEver": True, "recurWeekly": days},
        }

    for tag, name, loc, start, end in biz_scheds:
        cid = f"schedule:{tag}"
        # Saturday schedules get saturday-only recurrence
        if "saturday" in tag:
            days = {"monday": False, "tuesday": False, "wednesday": False,
                    "thursday": False, "friday": False, "saturday": True, "sunday": False}
        else:
            days = None  # defaults to Mon-Fri
        store.upsert_object(CanonicalLocationSchedule(
            canonical_id=cid, provenance=_p(f"TS_{tag.upper()}", name),
            name=name, schedule_type="businessHours", location_id=loc,
            events=[_biz_event("Weekdays", start, end, days)],
            status=S,
        ))
        store.add_cross_ref(cid, loc, "schedule_in_location")
        sched_ids[name] = cid

    us_holidays = [
        {"name": "New Year", "startDate": "2026-01-01", "endDate": "2026-01-01",
         "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
        {"name": "MLK Day", "startDate": "2026-01-19", "endDate": "2026-01-19",
         "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
        {"name": "Presidents Day", "startDate": "2026-02-16", "endDate": "2026-02-16",
         "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
        {"name": "Memorial Day", "startDate": "2026-05-25", "endDate": "2026-05-25",
         "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
        {"name": "Juneteenth", "startDate": "2026-06-19", "endDate": "2026-06-19",
         "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
        {"name": "Independence Day", "startDate": "2026-07-03", "endDate": "2026-07-04",
         "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
        {"name": "Labor Day", "startDate": "2026-09-07", "endDate": "2026-09-07",
         "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
        {"name": "Thanksgiving", "startDate": "2026-11-26", "endDate": "2026-11-27",
         "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
        {"name": "Christmas", "startDate": "2026-12-24", "endDate": "2026-12-25",
         "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
    ]
    holiday_scheds = [
        ("holidays-us-federal", "US Federal Holidays", "location:hq-nyc", us_holidays[:7]),
        ("holidays-us-full", "US Full Holidays", "location:reg-west-la", us_holidays),
        ("holidays-company", "GlobalTech Company Days", "location:hq-nyc",
         [{"name": "Company Day", "startDate": "2026-03-15", "endDate": "2026-03-15",
           "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"},
          {"name": "Summer Friday", "startDate": "2026-08-28", "endDate": "2026-08-28",
           "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"}]),
        ("holidays-winter-break", "Winter Break", "location:hq-nyc",
         [{"name": "Winter Break", "startDate": "2026-12-24", "endDate": "2027-01-02",
           "allDayEnabled": True, "startTime": "00:00", "endTime": "00:00"}]),
    ]
    for tag, name, loc, events in holiday_scheds:
        cid = f"schedule:{tag}"
        store.upsert_object(CanonicalLocationSchedule(
            canonical_id=cid, provenance=_p(f"TS_{tag.upper()}", name),
            name=name, schedule_type="holidays", location_id=loc, events=events, status=S,
        ))
        store.add_cross_ref(cid, loc, "schedule_in_location")
        sched_ids[name] = cid

    _tue_thu = {"monday": False, "tuesday": True, "wednesday": True,
                "thursday": True, "friday": False, "saturday": False, "sunday": False}
    _sun_only = {"monday": False, "tuesday": False, "wednesday": False,
                 "thursday": False, "friday": False, "saturday": False, "sunday": True}
    _sat_only = {"monday": False, "tuesday": False, "wednesday": False,
                 "thursday": False, "friday": False, "saturday": True, "sunday": False}
    _mon_fri = {"monday": True, "tuesday": True, "wednesday": True,
                "thursday": True, "friday": True, "saturday": False, "sunday": False}
    _fri_only = {"monday": False, "tuesday": False, "wednesday": False,
                 "thursday": False, "friday": True, "saturday": False, "sunday": False}
    _wed_only = {"monday": False, "tuesday": False, "wednesday": True,
                 "thursday": False, "friday": False, "saturday": False, "sunday": False}
    _thu_only = {"monday": False, "tuesday": False, "wednesday": False,
                 "thursday": True, "friday": False, "saturday": False, "sunday": False}
    _sat_sun = {"monday": False, "tuesday": False, "wednesday": False,
                "thursday": False, "friday": False, "saturday": True, "sunday": True}

    special_scheds = [
        ("training-block", "Training Block", "location:hq-nyc", "businessHours",
         [_biz_event("Training", "09:00", "12:00", _tue_thu)]),
        ("maintenance-window", "Maintenance Window", "location:dc-ashburn", "businessHours",
         [_biz_event("Maint", "02:00", "06:00", _sun_only)]),
        ("after-hours-support", "After Hours Support", "location:reg-south-dal", "businessHours",
         [_biz_event("After Hours", "19:00", "23:00", _mon_fri)]),
        ("weekend-oncall", "Weekend On-Call", "location:hq-nyc", "businessHours",
         [_biz_event("Weekend", "08:00", "17:00", _sat_sun)]),
        ("quarterly-review", "Quarterly Review Block", "location:hq-nyc", "businessHours",
         [_biz_event("QBR", "13:00", "17:00", _fri_only)]),
        ("sales-blitz", "Sales Blitz Hours", "location:reg-west-la", "businessHours",
         [_biz_event("Blitz", "06:00", "21:00", _mon_fri)]),
        ("eng-quiet-hours", "Engineering Quiet Hours", "location:reg-east-bos", "businessHours",
         [_biz_event("Focus", "09:00", "12:00", _wed_only)]),
        ("noc-shift-change", "NOC Shift Change", "location:dc-ashburn", "businessHours",
         [_biz_event("Handoff", "06:45", "07:15", _mon_fri)]),
        ("allhands-monthly", "Monthly All-Hands", "location:hq-nyc", "businessHours",
         [_biz_event("AllHands", "14:00", "15:00", _thu_only)]),
    ]
    for tag, name, loc, stype, events in special_scheds:
        cid = f"schedule:{tag}"
        store.upsert_object(CanonicalLocationSchedule(
            canonical_id=cid, provenance=_p(f"TS_{tag.upper()}", name),
            name=name, schedule_type=stype, location_id=loc, events=events, status=S,
        ))
        store.add_cross_ref(cid, loc, "schedule_in_location")
        sched_ids[name] = cid
    counts["Schedules"] = len(biz_scheds) + len(holiday_scheds) + len(special_scheds)

    # =================================================================
    # HUNT GROUPS (10)
    # =================================================================
    hg_defs = [
        ("hunt_group:it-helpdesk", "IT HelpDesk", "1500", "CIRCULAR",
         ["user:dkumar", "user:lwilson", "user:rpatel"], "location:hq-nyc", 5),
        ("hunt_group:exec-pool", "Executive Assistant Pool", "1501", "SIMULTANEOUS",
         ["user:lwilson", "user:rpatel"], "location:hq-nyc", 3),
        ("hunt_group:sales-west", "West Sales Team", "2500", "SIMULTANEOUS",
         ["user:tmorris", "user:klee", "user:jgarcia"], "location:reg-west-la", 4),
        ("hunt_group:sales-central", "Central Sales Team", "3500", "CIRCULAR",
         ["user:mkim", "user:cwhite", "user:arobinson"], "location:reg-central-chi", 4),
        ("hunt_group:support-l1", "Support Level 1", "4500", "UNIFORM",
         ["user:psmith", "user:rdiaz"], "location:reg-south-dal", 6),
        ("hunt_group:support-l2", "Support Level 2 Escalation", "4501", "CIRCULAR",
         ["user:jthompson", "user:rdiaz"], "location:reg-south-dal", 8),
        ("hunt_group:engineering", "Engineering On-Call", "5500", "SIMULTANEOUS",
         ["user:nwang", "user:dhall", "user:anguyen"], "location:reg-east-bos", 5),
        ("hunt_group:field-sales", "Field Sales", "6500", "CIRCULAR",
         ["user:emartinez", "user:bjones"], "location:sat-portland", 4),
        ("hunt_group:overflow-all", "Global Overflow", "1599", "UNIFORM",
         ["user:lwilson", "user:rpatel", "user:rdiaz", "user:psmith"], "location:hq-nyc", 10),
        ("hunt_group:after-hours", "After Hours On-Call", "1598", "SIMULTANEOUS",
         ["user:dkumar", "user:jthompson"], "location:hq-nyc", 8),
    ]
    for cid, name, ext, policy, agents, loc, rings in hg_defs:
        store.upsert_object(CanonicalHuntGroup(
            canonical_id=cid, provenance=_p(f"HP_{cid.split(':')[1].upper()}", name),
            name=name, extension=ext, policy=policy, agents=agents,
            no_answer_rings=rings, location_id=loc, status=S,
        ))
        store.add_cross_ref(cid, loc, "hunt_group_in_location")
        for a in agents:
            store.add_cross_ref(cid, a, "feature_has_agent")
    counts["Hunt Groups"] = len(hg_defs)

    # =================================================================
    # CALL QUEUES (8)
    # =================================================================
    cq_defs = [
        ("call_queue:sales-inbound", "Sales Inbound", "2600", "CIRCULAR", "PRIORITY_BASED",
         ["user:klee", "user:jgarcia", "user:mkim", "user:cwhite"], 20, "location:reg-west-la"),
        ("call_queue:support-general", "General Support", "4600", "UNIFORM", "PRIORITY_BASED",
         ["user:rdiaz", "user:psmith"], 15, "location:reg-south-dal"),
        ("call_queue:support-vip", "VIP Support", "4601", "CIRCULAR", "PRIORITY_BASED",
         ["user:jthompson", "user:rdiaz"], 5, "location:reg-south-dal"),
        ("call_queue:billing", "Billing", "4602", "UNIFORM", "PRIORITY_BASED",
         ["user:psmith"], 10, "location:reg-south-dal"),
        ("call_queue:general-inquiry", "General Inquiry", "1600", "CIRCULAR", "PRIORITY_BASED",
         ["user:lwilson", "user:rpatel"], 25, "location:hq-nyc"),
        ("call_queue:callback", "Callback Queue", "1601", "UNIFORM", "SKILL_BASED",
         ["user:rdiaz", "user:psmith", "user:lwilson"], 50, "location:hq-nyc"),
        ("call_queue:eng-escalation", "Engineering Escalation", "5600", "SIMULTANEOUS", "PRIORITY_BASED",
         ["user:nwang", "user:dhall"], 10, "location:reg-east-bos"),
        ("call_queue:sales-overflow", "Sales Overflow", "2601", "CIRCULAR", "PRIORITY_BASED",
         ["user:arobinson", "user:emartinez", "user:bjones"], 30, "location:reg-central-chi"),
    ]
    for cid, name, ext, policy, rtype, agents, qsize, loc in cq_defs:
        store.upsert_object(CanonicalCallQueue(
            canonical_id=cid, provenance=_p(f"CQ_{cid.split(':')[1].upper()}", name),
            name=name, extension=ext, policy=policy, routing_type=rtype,
            agents=agents, queue_size=qsize, location_id=loc, status=S,
        ))
        store.add_cross_ref(cid, loc, "call_queue_in_location")
        for a in agents:
            store.add_cross_ref(cid, a, "feature_has_agent")
    counts["Call Queues"] = len(cq_defs)

    # =================================================================
    # AUTO ATTENDANTS (20) — deep multi-level IVR tree
    # =================================================================
    def _menu(keys):
        return {"greeting": "DEFAULT", "extensionEnabled": True,
                "keyConfigurations": [{"key": k, "action": a, "value": v} for k, a, v in keys]}

    aa_defs = [
        # Main entry points (5)
        ("auto_attendant:main-aa", "GlobalTech Main", "1000", "Eastern Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "1700"), ("2", "TRANSFER_WITH_PROMPT", "1701"),
                ("3", "TRANSFER_WITH_PROMPT", "5500"), ("4", "TRANSFER_WITH_PROMPT", "1411"),
                ("0", "TRANSFER_WITH_PROMPT", "1600")]),
         _menu([("1", "TRANSFER_TO_MAILBOX", "1001"), ("0", "TRANSFER_WITH_PROMPT", "1598")]),
         "location:hq-nyc"),
        ("auto_attendant:west-aa", "West Region", "2000", "Pacific Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "2600"), ("2", "TRANSFER_WITH_PROMPT", "2500"),
                ("3", "TRANSFER_WITH_PROMPT", "2702"), ("0", "TRANSFER_WITH_PROMPT", "2001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "2001")]),
         "location:reg-west-la"),
        ("auto_attendant:central-aa", "Central Region", "3000", "Central Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "3500"), ("2", "TRANSFER_WITH_PROMPT", "3703"),
                ("0", "TRANSFER_WITH_PROMPT", "3001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "3001")]),
         "location:reg-central-chi"),
        ("auto_attendant:south-aa", "South Region", "4000", "Support 12-Hour",
         _menu([("1", "TRANSFER_WITH_PROMPT", "4600"), ("2", "TRANSFER_WITH_PROMPT", "4601"),
                ("3", "TRANSFER_WITH_PROMPT", "4500"), ("4", "TRANSFER_WITH_PROMPT", "4704"),
                ("0", "TRANSFER_WITH_PROMPT", "4001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "4001")]),
         "location:reg-south-dal"),
        ("auto_attendant:east-aa", "East Region", "5000", "Eastern Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "5500"), ("2", "TRANSFER_WITH_PROMPT", "5600"),
                ("0", "TRANSFER_WITH_PROMPT", "5001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "5001")]),
         "location:reg-east-bos"),
        # Sub-menus — department drilldowns (6)
        ("auto_attendant:sales-submenu", "Sales Department", "1700", "Eastern Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "2600"), ("2", "TRANSFER_WITH_PROMPT", "2500"),
                ("3", "TRANSFER_WITH_PROMPT", "3500"), ("4", "TRANSFER_WITH_PROMPT", "6500"),
                ("0", "TRANSFER_WITH_PROMPT", "1000")]),
         _menu([("0", "TRANSFER_WITH_PROMPT", "1000")]),
         "location:hq-nyc"),
        ("auto_attendant:support-submenu", "Support Department", "1701", "Eastern Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "4600"), ("2", "TRANSFER_WITH_PROMPT", "4601"),
                ("3", "TRANSFER_WITH_PROMPT", "4602"), ("4", "TRANSFER_WITH_PROMPT", "5600"),
                ("0", "TRANSFER_WITH_PROMPT", "1000")]),
         _menu([("0", "TRANSFER_WITH_PROMPT", "1000")]),
         "location:hq-nyc"),
        ("auto_attendant:directory-aa", "Company Directory", "1411", "Eastern Standard Hours",
         _menu([("0", "TRANSFER_WITH_PROMPT", "1000")]),
         _menu([("0", "TRANSFER_WITH_PROMPT", "1000")]),
         "location:hq-nyc"),
        ("auto_attendant:la-dept-menu", "LA Department Menu", "2702", "Pacific Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "2500"), ("2", "TRANSFER_WITH_PROMPT", "2600"),
                ("0", "TRANSFER_WITH_PROMPT", "2000")]),
         _menu([("0", "TRANSFER_WITH_PROMPT", "2000")]),
         "location:reg-west-la"),
        ("auto_attendant:chi-dept-menu", "CHI Department Menu", "3703", "Central Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "3500"), ("0", "TRANSFER_WITH_PROMPT", "3000")]),
         _menu([("0", "TRANSFER_WITH_PROMPT", "3000")]),
         "location:reg-central-chi"),
        ("auto_attendant:dal-dept-menu", "DAL Department Menu", "4704", "Support 12-Hour",
         _menu([("1", "TRANSFER_WITH_PROMPT", "4500"), ("2", "TRANSFER_WITH_PROMPT", "4501"),
                ("0", "TRANSFER_WITH_PROMPT", "4000")]),
         _menu([("0", "TRANSFER_WITH_PROMPT", "4000")]),
         "location:reg-south-dal"),
        # Satellite + special purpose (4)
        ("auto_attendant:portland-aa", "Portland Office", "6000", "Pacific Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "6500"), ("0", "TRANSFER_WITH_PROMPT", "6001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "6001")]),
         "location:sat-portland"),
        ("auto_attendant:denver-aa", "Denver Office", "7000", "Mountain Standard Hours",
         _menu([("0", "TRANSFER_WITH_PROMPT", "7001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "7001")]),
         "location:sat-denver"),
        ("auto_attendant:atlanta-aa", "Atlanta Office", "7299", "Eastern Standard Hours",
         _menu([("0", "TRANSFER_WITH_PROMPT", "1000")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "1001")]),
         "location:sat-atlanta"),
        ("auto_attendant:dc-ivr", "Data Center IVR", "9000", "DC 24x7 Operations",
         _menu([("1", "TRANSFER_WITH_PROMPT", "1500"), ("2", "TRANSFER_WITH_PROMPT", "5500"),
                ("0", "TRANSFER_WITH_PROMPT", "1010")]),
         _menu([("0", "TRANSFER_WITH_PROMPT", "1010")]),
         "location:dc-ashburn"),
        # Holiday / after-hours specific (5)
        ("auto_attendant:holiday-main", "Holiday Main Greeting", "1702", "Eastern Standard Hours",
         _menu([("0", "TRANSFER_TO_MAILBOX", "1001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "1001")]),
         "location:hq-nyc"),
        ("auto_attendant:after-hours-main", "After Hours Main", "1703", "Eastern Extended Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "1598"), ("0", "TRANSFER_TO_MAILBOX", "1001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "1001")]),
         "location:hq-nyc"),
        ("auto_attendant:after-hours-support", "After Hours Support", "4703", "After Hours Support",
         _menu([("1", "TRANSFER_WITH_PROMPT", "4601"), ("0", "TRANSFER_TO_MAILBOX", "4001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "4001")]),
         "location:reg-south-dal"),
        ("auto_attendant:after-hours-sales", "After Hours Sales", "2703", "Pacific Extended Hours",
         _menu([("1", "TRANSFER_TO_MAILBOX", "2001"), ("0", "TRANSFER_WITH_PROMPT", "2000")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "2001")]),
         "location:reg-west-la"),
        ("auto_attendant:weekend-aa", "Weekend Greeting", "1704", "Eastern Standard Hours",
         _menu([("1", "TRANSFER_WITH_PROMPT", "1598"), ("0", "TRANSFER_TO_MAILBOX", "1001")]),
         _menu([("0", "TRANSFER_TO_MAILBOX", "1001")]),
         "location:hq-nyc"),
    ]
    for cid, name, ext, sched_name, biz_menu, after_menu, loc in aa_defs:
        store.upsert_object(CanonicalAutoAttendant(
            canonical_id=cid, provenance=_p(f"AA_{cid.split(':')[1].upper()}", name),
            name=name, extension=ext, business_schedule=sched_name,
            business_hours_menu=biz_menu, after_hours_menu=after_menu,
            location_id=loc, status=S,
        ))
        store.add_cross_ref(cid, loc, "aa_in_location")
        if sched_name in sched_ids:
            store.add_cross_ref(cid, sched_ids[sched_name], "aa_has_schedule")
    counts["Auto Attendants"] = len(aa_defs)

    # =================================================================
    # CALL PARKS (40) — 5-8 per major location, realistic floor/zone layout
    # =================================================================
    park_config = [
        ("location:hq-nyc", "HQ", "19", 8),
        ("location:reg-west-la", "LA", "29", 6),
        ("location:reg-central-chi", "CHI", "39", 5),
        ("location:reg-south-dal", "DAL", "49", 5),
        ("location:reg-east-bos", "BOS", "59", 4),
        ("location:sat-portland", "PDX", "69", 3),
        ("location:sat-denver", "DEN", "79", 3),
        ("location:sat-atlanta", "ATL", "72", 3),
        ("location:dc-ashburn", "DC", "99", 3),
    ]
    park_count = 0
    for loc, tag, prefix, n in park_config:
        for i in range(n):
            cid = f"call_park:{tag.lower()}-park-{i+1}"
            store.upsert_object(CanonicalCallPark(
                canonical_id=cid, provenance=_p(f"CP_{tag}_{i+1}", f"{tag} Park {i+1}"),
                name=f"{tag} Call Park {i+1}", extension=f"{prefix}{i:02d}",
                location_id=loc, status=S,
            ))
            store.add_cross_ref(cid, loc, "call_park_in_location")
            park_count += 1
    counts["Call Parks"] = park_count

    # =================================================================
    # PICKUP GROUPS (10)
    # =================================================================
    pg_defs = [
        ("pickup_group:hq-exec", "HQ Executive", ["user:jcarter", "user:mchen", "user:srivera"], "location:hq-nyc"),
        ("pickup_group:hq-it", "HQ IT", ["user:dkumar", "user:lwilson", "user:rpatel"], "location:hq-nyc"),
        ("pickup_group:la-sales", "LA Sales", ["user:tmorris", "user:klee", "user:jgarcia"], "location:reg-west-la"),
        ("pickup_group:chi-sales", "CHI Sales", ["user:mkim", "user:cwhite", "user:arobinson"], "location:reg-central-chi"),
        ("pickup_group:dal-support", "DAL Support", ["user:jthompson", "user:rdiaz", "user:psmith"], "location:reg-south-dal"),
        ("pickup_group:bos-eng", "BOS Engineering", ["user:nwang", "user:dhall"], "location:reg-east-bos"),
        ("pickup_group:pdx-field", "Portland Field", ["user:emartinez"], "location:sat-portland"),
        ("pickup_group:den-field", "Denver Field", ["user:bjones"], "location:sat-denver"),
        ("pickup_group:dc-ops", "DC Operations", [], "location:dc-ashburn"),
        ("pickup_group:remote-eng", "Remote Engineering", ["user:anguyen"], "location:remote-wfh"),
    ]
    for cid, name, agents, loc in pg_defs:
        store.upsert_object(CanonicalPickupGroup(
            canonical_id=cid, provenance=_p(f"PG_{cid.split(':')[1].upper()}", name),
            name=name, agents=agents, location_id=loc, status=S,
        ))
        store.add_cross_ref(cid, loc, "pickup_group_in_location")
        for a in agents:
            store.add_cross_ref(cid, a, "feature_has_agent")
    counts["Pickup Groups"] = len(pg_defs)

    # =================================================================
    # PAGING GROUPS (8)
    # =================================================================
    paging_defs = [
        ("paging_group:hq-allpage", "HQ All Page", "1800",
         users_by_loc.get("location:hq-nyc", []), ["user:dkumar"], "location:hq-nyc"),
        ("paging_group:la-allpage", "LA All Page", "2800",
         users_by_loc.get("location:reg-west-la", []), ["user:tmorris"], "location:reg-west-la"),
        ("paging_group:chi-allpage", "CHI All Page", "3800",
         users_by_loc.get("location:reg-central-chi", []), ["user:mkim"], "location:reg-central-chi"),
        ("paging_group:dal-allpage", "DAL All Page", "4800",
         users_by_loc.get("location:reg-south-dal", []), ["user:jthompson"], "location:reg-south-dal"),
        ("paging_group:bos-allpage", "BOS All Page", "5800",
         users_by_loc.get("location:reg-east-bos", []), ["user:nwang"], "location:reg-east-bos"),
        ("paging_group:emergency-all", "Emergency All-Site", "1900",
         [u[0] for u in user_defs], ["user:jcarter", "user:dkumar"], "location:hq-nyc"),
        ("paging_group:hq-exec-page", "HQ Executive Page", "1801",
         ["user:jcarter", "user:mchen", "user:srivera"], ["user:dkumar"], "location:hq-nyc"),
        ("paging_group:dc-noc-page", "DC NOC Alert", "9800",
         ["user:dkumar", "user:rpatel"], ["user:dkumar"], "location:dc-ashburn"),
    ]
    for cid, name, ext, targets, originators, loc in paging_defs:
        store.upsert_object(CanonicalPagingGroup(
            canonical_id=cid, provenance=_p(f"PAG_{cid.split(':')[1].upper()}", name),
            name=name, extension=ext, targets=targets, originators=originators, status=S,
        ))
        store.add_cross_ref(cid, loc, "paging_group_in_location")
    counts["Paging Groups"] = len(paging_defs)

    # =================================================================
    # VIRTUAL LINES (15)
    # =================================================================
    vl_defs = [
        ("virtual_line:main-reception", "Main Reception", "1099", "location:hq-nyc"),
        ("virtual_line:sales-hotline", "Sales Hotline", "2099", "location:reg-west-la"),
        ("virtual_line:support-hotline", "Support Hotline", "4099", "location:reg-south-dal"),
        ("virtual_line:billing-line", "Billing Line", "4098", "location:reg-south-dal"),
        ("virtual_line:eng-bridge", "Engineering Bridge", "5099", "location:reg-east-bos"),
        ("virtual_line:conf-bridge-1", "Conference Bridge 1", "1090", "location:hq-nyc"),
        ("virtual_line:conf-bridge-2", "Conference Bridge 2", "1091", "location:hq-nyc"),
        ("virtual_line:conf-bridge-3", "Conference Bridge 3", "2090", "location:reg-west-la"),
        ("virtual_line:conf-bridge-4", "Conference Bridge 4", "3090", "location:reg-central-chi"),
        ("virtual_line:dc-monitoring", "DC Monitoring", "9099", "location:dc-ashburn"),
        ("virtual_line:oncall-pager", "On-Call Pager", "1097", "location:hq-nyc"),
        ("virtual_line:fax-hq", "HQ Fax Line", "1095", "location:hq-nyc"),
        ("virtual_line:fax-la", "LA Fax Line", "2095", "location:reg-west-la"),
        ("virtual_line:fax-chi", "CHI Fax Line", "3095", "location:reg-central-chi"),
        ("virtual_line:alarm-line", "Building Alarm", "1094", "location:hq-nyc"),
    ]
    for cid, name, ext, loc in vl_defs:
        store.upsert_object(CanonicalVirtualLine(
            canonical_id=cid, provenance=_p(f"VL_{cid.split(':')[1].upper()}", name),
            display_name=name, extension=ext, location_id=loc, status=S,
        ))
        store.add_cross_ref(cid, loc, "virtual_line_in_location")
    counts["Virtual Lines"] = len(vl_defs)

    # =================================================================
    # SHARED LINES (8)
    # =================================================================
    sl_defs = [
        ("shared_line:ceo-assistant", ["user:jcarter"], []),
        ("shared_line:cfo-assistant", ["user:mchen"], []),
        ("shared_line:cto-assistant", ["user:srivera"], []),
        ("shared_line:reception-hq", ["user:lwilson", "user:rpatel"], []),
        ("shared_line:la-front-desk", ["user:klee", "user:jgarcia"], []),
        ("shared_line:support-supervisor", ["user:jthompson", "user:rdiaz"], []),
        ("shared_line:dc-ops-shared", ["user:dkumar", "user:rpatel"], []),
        ("shared_line:eng-lab-shared", ["user:nwang", "user:dhall"], []),
    ]
    for cid, owners, devices in sl_defs:
        store.upsert_object(CanonicalSharedLine(
            canonical_id=cid, provenance=_p(f"SL_{cid.split(':')[1].upper()}", cid),
            owner_canonical_ids=owners, device_canonical_ids=devices, status=S,
        ))
    counts["Shared Lines"] = len(sl_defs)

    # =================================================================
    # CALLING PERMISSIONS / CSSes (8)
    # =================================================================
    cp_defs = [
        ("calling_permission:unrestricted", [
            ("INTERNAL_CALL", "ALLOW"), ("LOCAL", "ALLOW"), ("NATIONAL", "ALLOW"),
            ("INTERNATIONAL", "ALLOW"), ("PREMIUM_SERVICES_1", "ALLOW"),
            ("PREMIUM_SERVICES_2", "ALLOW"), ("OPERATOR_ASSISTED", "ALLOW"),
        ], ["user:jcarter", "user:mchen", "user:srivera"]),
        ("calling_permission:standard", [
            ("INTERNAL_CALL", "ALLOW"), ("LOCAL", "ALLOW"), ("NATIONAL", "ALLOW"),
            ("INTERNATIONAL", "BLOCK"), ("PREMIUM_SERVICES_1", "BLOCK"),
            ("PREMIUM_SERVICES_2", "BLOCK"), ("OPERATOR_ASSISTED", "ALLOW"),
        ], ["user:dkumar", "user:lwilson", "user:rpatel", "user:tmorris",
            "user:klee", "user:jgarcia", "user:nwang", "user:dhall"]),
        ("calling_permission:domestic-only", [
            ("INTERNAL_CALL", "ALLOW"), ("LOCAL", "ALLOW"), ("NATIONAL", "ALLOW"),
            ("INTERNATIONAL", "BLOCK"), ("PREMIUM_SERVICES_1", "BLOCK"),
            ("PREMIUM_SERVICES_2", "BLOCK"), ("OPERATOR_ASSISTED", "BLOCK"),
        ], ["user:mkim", "user:cwhite", "user:arobinson", "user:rdiaz", "user:psmith"]),
        ("calling_permission:support-agents", [
            ("INTERNAL_CALL", "ALLOW"), ("LOCAL", "ALLOW"), ("NATIONAL", "ALLOW"),
            ("INTERNATIONAL", "AUTH_CODE"), ("PREMIUM_SERVICES_1", "BLOCK"),
        ], ["user:jthompson", "user:rdiaz", "user:psmith"]),
        ("calling_permission:field-workers", [
            ("INTERNAL_CALL", "ALLOW"), ("LOCAL", "ALLOW"), ("NATIONAL", "ALLOW"),
            ("INTERNATIONAL", "ALLOW"), ("PREMIUM_SERVICES_1", "BLOCK"),
        ], ["user:emartinez", "user:bjones", "user:anguyen"]),
        ("calling_permission:restricted-internal", [
            ("INTERNAL_CALL", "ALLOW"), ("LOCAL", "BLOCK"), ("NATIONAL", "BLOCK"),
            ("INTERNATIONAL", "BLOCK"),
        ], []),
        ("calling_permission:emergency-only", [
            ("INTERNAL_CALL", "BLOCK"), ("LOCAL", "BLOCK"), ("NATIONAL", "BLOCK"),
            ("INTERNATIONAL", "BLOCK"),
        ], []),
        ("calling_permission:lobby-phones", [
            ("INTERNAL_CALL", "ALLOW"), ("LOCAL", "ALLOW"), ("NATIONAL", "BLOCK"),
            ("INTERNATIONAL", "BLOCK"),
        ], []),
    ]
    for cid, perms, assigned in cp_defs:
        store.upsert_object(CanonicalCallingPermission(
            canonical_id=cid, provenance=_p(f"CSS_{cid.split(':')[1].upper()}", cid),
            calling_permissions=[CallingPermissionEntry(call_type=ct, action=a) for ct, a in perms],
            assigned_users=assigned, use_custom_enabled=True,
            use_custom_permissions=True, status=S,
        ))
    counts["Calling Permissions"] = len(cp_defs)

    store.close()

    # =================================================================
    # SUMMARY
    # =================================================================
    total = sum(counts.values())
    print(f"\n{'='*60}")
    print(f"Stress test: {DB_PATH}")
    print(f"Project: {PROJECT_NAME}")
    print(f"{'='*60}\n")
    for k, v in counts.items():
        print(f"  {k:<25s} {v:>4d}")
    print(f"  {'─'*30}")
    print(f"  {'TOTAL OBJECTS':<25s} {total:>4d}")
    print(f"""
Next steps:
  1. wxcli cucm plan -p {PROJECT_NAME}
  2. wxcli cucm dry-run -p {PROJECT_NAME}
  3. wxcli cucm execute -p {PROJECT_NAME} --concurrency 15
""")


if __name__ == "__main__":
    main()
