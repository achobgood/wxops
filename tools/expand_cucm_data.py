#!/usr/bin/env python3
"""Expand dcloud-fresh CUCM raw data to 4x complexity for pipeline stress testing."""

import json
import uuid
import random
import os
from pathlib import Path

random.seed(42)

RAW_DATA_PATH = Path.home() / ".wxcli/migrations/dcloud-fresh/raw_data.json"

# --- Cisco OUI prefixes (verified against IEEE database) ---
CISCO_OUIS = [
    "001B54", "58BC27", "B07D47", "D46D50", "F872EA",
    "64AE0C", "FC5B39", "885A92", "E4AA5D", "002290",
    "A4934C", "5C5015", "E80AB9", "F4CFE2", "1CDEA7",
]

# --- Realistic name pools ---
FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Dorothy", "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna",
    "Kenneth", "Michelle", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon", "Helen",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Raymond", "Christine", "Gregory", "Debra",
    "Frank", "Rachel", "Alexander", "Carolyn", "Patrick", "Janet", "Jack", "Catherine",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales",
    "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson",
    "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward",
    "Richardson", "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray",
    "Mendoza", "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel",
    "Myers", "Long", "Ross", "Foster", "Jimenez", "Powell",
]

DEPARTMENTS = [
    "Engineering", "Sales", "Support", "Finance", "HR",
    "Marketing", "Legal", "IT", "Operations", "Executive",
]

# --- Location definitions ---
LOCATIONS = [
    {"code": "NYC", "name": "New York Office", "dp": "DP-NYC-Phones",
     "addr": "375 Hudson Street", "city": "New York", "state": "NY", "zip": "10014",
     "tz": "America/New_York", "area_code": "212", "ext_start": 3000},
    {"code": "CHI", "name": "Chicago Branch", "dp": "DP-CHI-Phones",
     "addr": "225 W Randolph St", "city": "Chicago", "state": "IL", "zip": "60606",
     "tz": "America/Chicago", "area_code": "312", "ext_start": 4000},
    {"code": "SJC", "name": "San Jose HQ", "dp": "DP-SJC-Phones",
     "addr": "170 W Tasman Dr", "city": "San Jose", "state": "CA", "zip": "95134",
     "tz": "America/Los_Angeles", "area_code": "408", "ext_start": 5000},
    {"code": "ATL", "name": "Atlanta DC", "dp": "DP-ATL-Phones",
     "addr": "3399 Peachtree Rd NE", "city": "Atlanta", "state": "GA", "zip": "30326",
     "tz": "America/New_York", "area_code": "404", "ext_start": 6100},
    {"code": "DEN", "name": "Denver Remote", "dp": "DP-DEN-Phones",
     "addr": "1801 California St", "city": "Denver", "state": "CO", "zip": "80202",
     "tz": "America/Denver", "area_code": "303", "ext_start": 7000},
]

# Phone models with line capacity and distribution weight
PHONE_MODELS = [
    {"model": "Cisco 8845", "product": "Cisco 8845", "lines": 5, "weight": 30, "buttons": 10},
    {"model": "Cisco 8861", "product": "Cisco 8861", "lines": 10, "weight": 15, "buttons": 10},
    {"model": "Cisco 7841", "product": "Cisco 7841", "lines": 4, "weight": 20, "buttons": 4},
    {"model": "Cisco 7821", "product": "Cisco 7821", "lines": 2, "weight": 15, "buttons": 2},
    {"model": "Cisco 8832", "product": "Cisco 8832", "lines": 1, "weight": 5, "buttons": 1},
    {"model": "Cisco 9841", "product": "Cisco 9841", "lines": 8, "weight": 10, "buttons": 10},
    {"model": "Cisco ATA 192", "product": "Cisco ATA 192", "lines": 2, "weight": 5, "buttons": 2},
]


def cucm_uuid():
    """Generate a CUCM-format UUID with curly braces."""
    return "{" + str(uuid.uuid4()).upper() + "}"


def ref(name, uid=None):
    """Create a CUCM-style object reference."""
    return {"_value_1": name, "uuid": uid or cucm_uuid()}


def null_ref():
    """Create a null CUCM reference."""
    return {"_value_1": None, "uuid": None}


def generate_mac(oui_index, seq):
    """Generate a unique Cisco MAC address."""
    oui = CISCO_OUIS[oui_index % len(CISCO_OUIS)]
    suffix = f"{seq:06X}"
    return oui + suffix


_used_macs = set()


def unique_mac():
    """Generate a unique MAC not yet used."""
    while True:
        oui_idx = random.randint(0, len(CISCO_OUIS) - 1)
        seq = random.randint(0, 0xFFFFFF)
        mac = generate_mac(oui_idx, seq)
        if mac not in _used_macs:
            _used_macs.add(mac)
            return mac


def pick_model():
    """Weighted random phone model selection."""
    weights = [m["weight"] for m in PHONE_MODELS]
    return random.choices(PHONE_MODELS, weights=weights, k=1)[0]


def generate_name_pair(used_names):
    """Generate a unique first/last name pair."""
    for _ in range(1000):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        userid = f"{first.lower()}.{last.lower()}"
        if userid not in used_names:
            used_names.add(userid)
            return first, last, userid
    # Fallback with numeric suffix
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    suffix = random.randint(100, 999)
    userid = f"{first.lower()}.{last.lower()}{suffix}"
    used_names.add(userid)
    return first, last, userid


# ============================================================
# INFRASTRUCTURE GENERATORS
# ============================================================

def generate_infrastructure():
    """Generate locations, device pools, partitions, CSS, datetime groups."""
    cucm_locations = []
    device_pools = []
    datetime_groups = []
    partitions = []
    css_list = []

    # Store UUIDs for cross-referencing
    loc_refs = {}   # code -> ref dict
    dp_refs = {}    # code -> ref dict
    pt_refs = {}    # code -> ref dict
    css_refs = {}   # code -> ref dict

    # Shared partitions
    internal_pt_uuid = cucm_uuid()
    emergency_pt_uuid = cucm_uuid()
    partitions.append({
        "name": "Internal_PT",
        "description": "Internal extensions only",
        "uuid": internal_pt_uuid,
    })
    partitions.append({
        "name": "Emergency_PT",
        "description": "Emergency 911 routing",
        "uuid": emergency_pt_uuid,
    })
    pt_refs["Internal"] = ref("Internal_PT", internal_pt_uuid)
    pt_refs["Emergency"] = ref("Emergency_PT", emergency_pt_uuid)

    for loc in LOCATIONS:
        code = loc["code"]

        # CUCM Location
        loc_uuid = cucm_uuid()
        cucm_locations.append({
            "name": f"{code}_Location",
            "id": None,
            "withinAudioBandwidth": "0",
            "withinVideoBandwidth": "0",
            "withinImmersiveKbits": None,
            "uuid": loc_uuid,
        })
        loc_refs[code] = ref(f"{code}_Location", loc_uuid)

        # DateTime Group
        dt_uuid = cucm_uuid()
        datetime_groups.append({
            "name": f"{code}_DTG",
            "timeZone": loc["tz"],
            "separator": "-",
            "dateformat": "M/D/Y",
            "uuid": dt_uuid,
        })

        # Device Pool
        dp_uuid = cucm_uuid()
        device_pools.append({
            "name": loc["dp"],
            "dateTimeSettingName": ref(f"{code}_DTG", dt_uuid),
            "locationName": ref(f"{code}_Location", loc_uuid),
            "callManagerGroupName": ref("dCloud_CMGroup"),
            "mediaResourceListName": null_ref(),
            "regionName": ref(f"{code}_Region"),
            "srstName": null_ref(),
            "uuid": dp_uuid,
        })
        dp_refs[code] = ref(loc["dp"], dp_uuid)

        # Location partition
        pt_uuid = cucm_uuid()
        partitions.append({
            "name": f"{code}_PT",
            "description": f"Partition for {loc['name']}",
            "uuid": pt_uuid,
        })
        pt_refs[code] = ref(f"{code}_PT", pt_uuid)

        # Location CSS (local PT + Internal + Emergency + dCloud_PT)
        css_uuid = cucm_uuid()
        css_members = [
            {"routePartitionName": ref(f"{code}_PT", pt_uuid), "index": 1, "uuid": cucm_uuid()},
            {"routePartitionName": ref("Internal_PT", internal_pt_uuid), "index": 2, "uuid": cucm_uuid()},
            {"routePartitionName": ref("Emergency_PT", emergency_pt_uuid), "index": 3, "uuid": cucm_uuid()},
            {"routePartitionName": ref("dCloud_PT"), "index": 4, "uuid": cucm_uuid()},
        ]
        css_list.append({
            "name": f"{code}_CSS",
            "description": f"CSS for {loc['name']}",
            "clause": f"{code}_PT:Internal_PT:Emergency_PT:dCloud_PT",
            "members": css_members,
            "uuid": css_uuid,
        })
        css_refs[code] = ref(f"{code}_CSS", css_uuid)

    # Cross-site unrestricted CSS (all location PTs + shared)
    unr_uuid = cucm_uuid()
    unr_members = []
    for i, loc in enumerate(LOCATIONS):
        unr_members.append({
            "routePartitionName": pt_refs[loc["code"]],
            "index": i + 1,
            "uuid": cucm_uuid(),
        })
    unr_members.append({"routePartitionName": pt_refs["Internal"], "index": len(LOCATIONS) + 1, "uuid": cucm_uuid()})
    unr_members.append({"routePartitionName": pt_refs["Emergency"], "index": len(LOCATIONS) + 2, "uuid": cucm_uuid()})
    css_list.append({
        "name": "Unrestricted_CSS",
        "description": "Cross-site unrestricted dialing",
        "clause": ":".join(f"{l['code']}_PT" for l in LOCATIONS) + ":Internal_PT:Emergency_PT",
        "members": unr_members,
        "uuid": unr_uuid,
    })
    css_refs["Unrestricted"] = ref("Unrestricted_CSS", unr_uuid)

    # Internal-only CSS
    int_css_uuid = cucm_uuid()
    css_list.append({
        "name": "Internal_Only_CSS",
        "description": "Internal extensions only",
        "clause": "Internal_PT",
        "members": [{"routePartitionName": pt_refs["Internal"], "index": 1, "uuid": cucm_uuid()}],
        "uuid": int_css_uuid,
    })
    css_refs["Internal_Only"] = ref("Internal_Only_CSS", int_css_uuid)

    return {
        "cucm_locations": cucm_locations,
        "device_pools": device_pools,
        "datetime_groups": datetime_groups,
        "partitions": partitions,
        "css_list": css_list,
        "loc_refs": loc_refs,
        "dp_refs": dp_refs,
        "pt_refs": pt_refs,
        "css_refs": css_refs,
    }


# ============================================================
# USER + PHONE + LINE GENERATORS
# ============================================================

def generate_call_forwarding(fwd_type, ext_range_start, loc_code, pt_ref, css_ref):
    """Generate call forwarding config based on complexity type."""
    base = {
        "callForwardAll": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
        "callForwardBusy": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
        "callForwardBusyInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
        "callForwardNoAnswer": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None, "duration": None},
        "callForwardNoAnswerInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None, "duration": None},
        "callForwardNoCoverage": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
        "callForwardNoCoverageInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
        "callForwardNotRegistered": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
        "callForwardNotRegisteredInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
        "callForwardOnFailure": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
    }

    rand_ext = str(ext_range_start + random.randint(0, 899))

    if fwd_type == "A":
        # CFA to voicemail, CFNA to extension, CFB to external
        base["callForwardAll"]["forwardToVoiceMail"] = "true"
        base["callForwardNoAnswer"]["destination"] = rand_ext
        base["callForwardNoAnswer"]["callingSearchSpaceName"] = css_ref
        base["callForwardNoAnswer"]["duration"] = 20
        base["callForwardBusy"]["destination"] = "+19725551234"
        base["callForwardBusy"]["callingSearchSpaceName"] = css_ref
    elif fwd_type == "B":
        # CFA to external, CFNA to hunt pilot, CFB to voicemail
        base["callForwardAll"]["destination"] = "+13125559876"
        base["callForwardAll"]["callingSearchSpaceName"] = css_ref
        base["callForwardNoAnswer"]["destination"] = rand_ext
        base["callForwardNoAnswer"]["callingSearchSpaceName"] = css_ref
        base["callForwardNoAnswer"]["duration"] = 15
        base["callForwardBusy"]["forwardToVoiceMail"] = "true"
    elif fwd_type == "C":
        # No CFA, CFNA/CFB/CFNC all different destinations + CSS
        base["callForwardNoAnswer"]["destination"] = rand_ext
        base["callForwardNoAnswer"]["callingSearchSpaceName"] = css_ref
        base["callForwardNoAnswer"]["duration"] = 25
        base["callForwardBusy"]["destination"] = str(ext_range_start + random.randint(0, 899))
        base["callForwardBusy"]["callingSearchSpaceName"] = css_ref
        base["callForwardNoCoverage"]["destination"] = str(ext_range_start + random.randint(0, 899))
        base["callForwardNoCoverage"]["callingSearchSpaceName"] = css_ref
        base["callForwardBusyInt"]["destination"] = str(ext_range_start + random.randint(0, 899))
        base["callForwardBusyInt"]["callingSearchSpaceName"] = css_ref
        base["callForwardNoAnswerInt"]["destination"] = str(ext_range_start + random.randint(0, 899))
        base["callForwardNoAnswerInt"]["callingSearchSpaceName"] = css_ref
        base["callForwardNoAnswerInt"]["duration"] = 30
    elif fwd_type == "D":
        # ALL 10 types set (maximum complexity)
        for key in base:
            if "duration" in base[key]:
                base[key]["duration"] = random.choice([10, 15, 20, 25, 30])
            base[key]["destination"] = str(ext_range_start + random.randint(0, 899))
            base[key]["callingSearchSpaceName"] = css_ref
            if random.random() < 0.3:
                base[key]["forwardToVoiceMail"] = "true"
                base[key]["destination"] = None

    return base


def generate_users_and_phones(infra):
    """Generate 225 users, 700 physical phones, 100 software phones, lines with forwarding."""
    dp_refs = infra["dp_refs"]
    pt_refs = infra["pt_refs"]
    css_refs = infra["css_refs"]
    loc_refs = infra["loc_refs"]

    users = []
    phones = []
    used_names = set()
    shared_line_pool = {}  # ext -> dirn uuid, for creating shared lines

    users_per_loc = 45

    for loc in LOCATIONS:
        code = loc["code"]
        ext_base = loc["ext_start"]
        ext_counter = 0

        loc_users = []

        # Generate 45 users per location
        for u_idx in range(users_per_loc):
            first, last, userid = generate_name_pair(used_names)
            ext = ext_base + ext_counter
            ext_counter += 1
            ext_str = str(ext)

            user = {
                "pkid": cucm_uuid(),
                "userid": userid,
                "firstName": first,
                "lastName": last,
                "mailid": f"{userid}@dcloud.cisco.com",
                "telephoneNumber": f"+1{loc['area_code']}{ext_str[-7:].zfill(7)}",
                "department": random.choice(DEPARTMENTS),
                "title": f"{first} {last}",
                "directoryUri": f"{userid}@dcloud.cisco.com",
                "enableCti": "t",
                "associatedDevices": [],
                "primaryExtension": null_ref(),
                "callingSearchSpaceName": null_ref(),
                "voiceMailProfile": None,
                "selfService": None,
                "userLocale": None,
                "manager": None,
                "_extracted_via": "sql",
            }
            loc_users.append((user, ext_str, first, last, userid))

        # Generate physical phones for this location (140 per loc = 700 total)
        phones_per_loc = 140
        for p_idx in range(phones_per_loc):
            model_info = pick_model()
            mac = unique_mac()
            phone_name = f"SEP{mac}"

            # Assign to a user (round-robin, some users get multiple phones)
            user_data = loc_users[p_idx % users_per_loc]
            user_obj, user_ext, first, last, userid = user_data

            # Add device to user's associated devices
            if phone_name not in user_obj["associatedDevices"]:
                user_obj["associatedDevices"].append(phone_name)

            # Determine line count
            max_lines = model_info["lines"]
            if p_idx % 10 < 3 and max_lines >= 2:
                # 30% get multi-line
                num_lines = min(random.randint(2, 4), max_lines)
            else:
                num_lines = 1

            # Build lines
            lines = []
            line_ext = user_ext

            # Decide forwarding complexity
            fwd_roll = random.random()
            if fwd_roll < 0.15:
                fwd_type = "A"
            elif fwd_roll < 0.25:
                fwd_type = "B"
            elif fwd_roll < 0.35:
                fwd_type = "C"
            elif fwd_roll < 0.40:
                fwd_type = "D"
            else:
                fwd_type = None

            # Check if this should be a shared line
            is_shared = (p_idx % 20 == 0) and ext_counter > 5
            if is_shared:
                # Use a previously created extension
                shared_ext_str = str(ext_base + random.randint(0, min(ext_counter - 1, 40)))
                if shared_ext_str in shared_line_pool:
                    dirn_uuid = shared_line_pool[shared_ext_str]
                else:
                    dirn_uuid = cucm_uuid()
                    shared_line_pool[shared_ext_str] = dirn_uuid
                line_ext = shared_ext_str
            else:
                dirn_uuid = cucm_uuid()

            fwd = generate_call_forwarding(
                fwd_type, ext_base, code, pt_refs[code], css_refs[code]
            ) if fwd_type else {
                "callForwardAll": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                "callForwardBusy": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                "callForwardBusyInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                "callForwardNoAnswer": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None, "duration": None},
                "callForwardNoAnswerInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None, "duration": None},
                "callForwardNoCoverage": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                "callForwardNoCoverageInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                "callForwardNotRegistered": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                "callForwardNotRegisteredInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                "callForwardOnFailure": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
            }

            line1 = {
                "index": 1,
                "label": None,
                "display": f"{first} {last} - X{line_ext}",
                "dirn": {
                    "pattern": line_ext,
                    "routePartitionName": pt_refs[code],
                    "uuid": dirn_uuid,
                },
                "e164Mask": f"+1{loc['area_code']}555{line_ext[-4:]}",
                "associatedEndusers": {"enduser": [{"userId": userid}]},
                **fwd,
            }
            lines.append(line1)

            # Additional lines (BLF or secondary extensions)
            for li in range(1, num_lines):
                extra_ext = str(ext_base + ext_counter)
                ext_counter += 1
                extra_line = {
                    "index": li + 1,
                    "label": f"Line {li + 1}" if random.random() < 0.5 else None,
                    "display": f"{first} {last} - X{extra_ext}",
                    "dirn": {
                        "pattern": extra_ext,
                        "routePartitionName": pt_refs[code],
                        "uuid": cucm_uuid(),
                    },
                    "e164Mask": f"+1{loc['area_code']}555{extra_ext[-4:]}",
                    "associatedEndusers": {"enduser": [{"userId": userid}]},
                    "callForwardAll": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardBusy": {"forwardToVoiceMail": "true", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardBusyInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardNoAnswer": {"forwardToVoiceMail": "true", "callingSearchSpaceName": null_ref(), "destination": None, "duration": 15},
                    "callForwardNoAnswerInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None, "duration": None},
                    "callForwardNoCoverage": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardNoCoverageInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardNotRegistered": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardNotRegisteredInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardOnFailure": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                }
                lines.append(extra_line)

            # Determine CSS - 15% get unrestricted cross-site CSS
            phone_css = css_refs["Unrestricted"] if random.random() < 0.15 else css_refs[code]

            phone = {
                "name": phone_name,
                "description": f"{first} {last} - X{line_ext} - {model_info['model']}",
                "product": model_info["product"],
                "model": model_info["model"],
                "class": "Phone",
                "protocol": "SIP",
                "protocolSide": "User",
                "devicePoolName": dp_refs[code],
                "callingSearchSpaceName": phone_css,
                "locationName": loc_refs[code],
                "phoneTemplateName": null_ref(),
                "lines": {"line": lines},
                "uuid": cucm_uuid(),
            }
            phones.append(phone)

        # Software phones (20 per location = 100 total)
        for s_idx in range(20):
            user_data = loc_users[s_idx % users_per_loc]
            user_obj, user_ext, first, last, userid = user_data

            # Jabber mobile
            if s_idx < 10:
                sw_name = f"TCT{userid.upper()}"
                sw_product = "Cisco Dual Mode for iPhone"
                sw_model = "Cisco Dual Mode for iPhone"
            else:
                sw_name = f"CSF{userid.upper()}"
                sw_product = "Cisco Unified Client Services Framework"
                sw_model = "Cisco Unified Client Services Framework"

            if sw_name not in user_obj["associatedDevices"]:
                user_obj["associatedDevices"].append(sw_name)

            sw_phone = {
                "name": sw_name,
                "description": f"{first} {last} - X{user_ext} - {'Jabber Mobile' if s_idx < 10 else 'Jabber Desktop'}",
                "product": sw_product,
                "model": sw_model,
                "class": "Phone",
                "protocol": "SIP",
                "protocolSide": "User",
                "devicePoolName": dp_refs[code],
                "callingSearchSpaceName": css_refs[code],
                "locationName": loc_refs[code],
                "phoneTemplateName": null_ref(),
                "lines": {"line": [{
                    "index": 1,
                    "label": None,
                    "display": f"{first} {last} - X{user_ext}",
                    "dirn": {
                        "pattern": user_ext,
                        "routePartitionName": pt_refs[code],
                        "uuid": cucm_uuid(),
                    },
                    "e164Mask": f"+1{loc['area_code']}555{user_ext[-4:]}",
                    "associatedEndusers": {"enduser": [{"userId": userid}]},
                    "callForwardAll": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardBusy": {"forwardToVoiceMail": "true", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardBusyInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardNoAnswer": {"forwardToVoiceMail": "true", "callingSearchSpaceName": null_ref(), "destination": None, "duration": 15},
                    "callForwardNoAnswerInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None, "duration": None},
                    "callForwardNoCoverage": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardNoCoverageInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardNotRegistered": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardNotRegisteredInt": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                    "callForwardOnFailure": {"forwardToVoiceMail": "false", "callingSearchSpaceName": null_ref(), "destination": None},
                }]},
                "uuid": cucm_uuid(),
            }
            phones.append(sw_phone)

        # Add users to the main list
        for user_obj, _, _, _, _ in loc_users:
            users.append(user_obj)

    return users, phones, shared_line_pool


# ============================================================
# FEATURE GENERATORS
# ============================================================

def generate_features(infra):
    """Generate hunt groups, pickup groups, call parks, line groups."""
    pt_refs = infra["pt_refs"]
    hunt_pilots = []
    hunt_lists = []
    line_groups = []
    pickup_groups = []
    call_parks = []

    for loc in LOCATIONS:
        code = loc["code"]
        ext_base = loc["ext_start"]

        # 2 hunt groups per location (10 total)
        for hg_idx in range(2):
            pilot_ext = str(ext_base + 900 + hg_idx)

            # Line group with 5-10 members
            lg_uuid = cucm_uuid()
            lg_members = []
            for m in range(random.randint(5, 10)):
                member_ext = str(ext_base + random.randint(0, 44))
                lg_members.append({
                    "lineSelectionOrder": m + 1,
                    "directoryNumber": {
                        "pattern": member_ext,
                        "routePartitionName": pt_refs[code],
                    },
                    "uuid": cucm_uuid(),
                })

            line_groups.append({
                "name": f"{code}_LG_{hg_idx + 1}",
                "description": f"{loc['name']} Line Group {hg_idx + 1}",
                "distributionAlgorithm": random.choice([
                    "Top Down", "Circular", "Longest Idle Time", "Broadcast"
                ]),
                "rnaReversionTimeOut": random.choice([10, 15, 20]),
                "huntAlgorithmNoAnswer": "Try next member; then, try next group in Hunt List",
                "huntAlgorithmBusy": "Try next member; then, try next group in Hunt List",
                "huntAlgorithmNotAvailable": "Try next member; then, try next group in Hunt List",
                "members": {"member": lg_members},
                "uuid": lg_uuid,
            })

            # Hunt list
            hl_uuid = cucm_uuid()
            hunt_lists.append({
                "name": f"{code}_HL_{hg_idx + 1}",
                "description": f"{loc['name']} Hunt List {hg_idx + 1}",
                "callManagerGroupName": ref("dCloud_CMGroup"),
                "routeListEnabled": "true",
                "voiceMailUsage": "false",
                "members": {"member": [{
                    "lineGroupName": ref(f"{code}_LG_{hg_idx + 1}", lg_uuid),
                    "selectionOrder": 1,
                    "uuid": cucm_uuid(),
                }]},
                "uuid": hl_uuid,
            })

            # Hunt pilot
            hunt_pilots.append({
                "pattern": pilot_ext,
                "description": f"{loc['name']} Hunt Pilot {hg_idx + 1}",
                "usage": "Hunt Pilot",
                "routePartitionName": pt_refs[code],
                "huntListName": ref(f"{code}_HL_{hg_idx + 1}", hl_uuid),
                "queueCalls": {
                    "maxCallersInQueue": random.choice([5, 10, 15, 20]),
                    "queueFullDestination": str(ext_base),
                    "maxWaitTimeInQueue": random.choice([30, 60, 120]),
                    "noAgentDestination": str(ext_base + 1),
                    "networkHoldMohAudioSourceID": 1,
                },
                "uuid": cucm_uuid(),
            })

        # 3 pickup groups per location (15 total)
        for pg_idx in range(3):
            pg_uuid = cucm_uuid()
            pg_name = f"{code}_PG_{pg_idx + 1}"
            pickup_groups.append({
                "pattern": str(ext_base + 950 + pg_idx),
                "description": f"{loc['name']} Pickup Group {pg_idx + 1}",
                "usage": "Call Pick Up Group",
                "routePartitionName": pt_refs[code],
                "name": pg_name,
                "members": {"member": [{
                    "priority": 1,
                    "pickupGroupName": ref(pg_name, pg_uuid),
                    "uuid": cucm_uuid(),
                }]},
                "uuid": pg_uuid,
            })

        # 1 call park per location with 10 slots (5 total)
        call_parks.append({
            "pattern": f"{ext_base + 800}[0-9]",
            "description": f"{loc['name']} Call Park",
            "routePartitionName": pt_refs[code],
            "uuid": cucm_uuid(),
        })

    return {
        "hunt_pilots": hunt_pilots,
        "hunt_lists": hunt_lists,
        "line_groups": line_groups,
        "pickup_groups": pickup_groups,
        "call_parks": call_parks,
    }


def generate_routing(infra):
    """Generate route patterns, translation patterns, SIP trunks, route groups, route lists."""
    pt_refs = infra["pt_refs"]
    dp_refs = infra["dp_refs"]

    route_patterns = []
    translation_patterns = []
    sip_trunks = []
    route_groups = []
    route_lists = []

    # Per-location SIP trunks + route patterns
    for i, loc in enumerate(LOCATIONS):
        code = loc["code"]

        # SIP trunk per location
        trunk_uuid = cucm_uuid()
        sip_trunks.append({
            "name": f"{code}_SIP_Trunk",
            "description": f"SIP Trunk for {loc['name']}",
            "product": "SIP Trunk",
            "model": "SIP Trunk",
            "class": "Trunk",
            "protocol": "SIP",
            "protocolSide": "Network",
            "devicePoolName": dp_refs[code],
            "callingSearchSpaceName": ref(f"{code}_CSS"),
            "sipProfileName": ref("Standard SIP Profile"),
            "securityProfileName": ref("Non Secure SIP Trunk Profile"),
            "destinations": [{"addressIpv4": f"10.1.{i + 10}.1", "port": 5060, "sortOrder": 1}],
            "uuid": trunk_uuid,
        })

        # Route group per location
        rg_uuid = cucm_uuid()
        route_groups.append({
            "name": f"{code}_RG",
            "description": f"Route Group for {loc['name']}",
            "distributionAlgorithm": "Top Down",
            "members": {"member": [{
                "deviceName": ref(f"{code}_SIP_Trunk", trunk_uuid),
                "deviceSelectionOrder": 1,
                "port": 0,
                "uuid": cucm_uuid(),
            }]},
            "uuid": rg_uuid,
        })

        # Local PSTN breakout route patterns
        route_patterns.append({
            "pattern": f"9.1{loc['area_code']}NXXXXXX",
            "description": f"{loc['name']} local PSTN",
            "usage": None,
            "routePartitionName": pt_refs[code],
            "blockEnable": "false",
            "destination": ref(f"{code}_RG", rg_uuid),
            "uuid": cucm_uuid(),
        })

        # Inter-site dial prefix (8 + site code)
        route_patterns.append({
            "pattern": f"8{i + 1}XXXX",
            "description": f"Inter-site to {loc['name']}",
            "usage": None,
            "routePartitionName": pt_refs["Internal"],
            "blockEnable": "false",
            "uuid": cucm_uuid(),
        })

        # Translation patterns for emergency
        translation_patterns.append({
            "pattern": f"9911",
            "description": f"{loc['name']} E911 translation",
            "routePartitionName": pt_refs[code],
            "calledPartyTransformationMask": "911",
            "callingPartyTransformationMask": None,
            "uuid": cucm_uuid(),
        })

        # Translation pattern for short-code dialing
        translation_patterns.append({
            "pattern": f"0",
            "description": f"{loc['name']} operator shortcode",
            "routePartitionName": pt_refs[code],
            "calledPartyTransformationMask": str(loc["ext_start"]),
            "callingPartyTransformationMask": None,
            "uuid": cucm_uuid(),
        })

    # Global route patterns
    route_patterns.append({
        "pattern": "9.011!",
        "description": "International dialing",
        "usage": None,
        "routePartitionName": pt_refs["Internal"],
        "blockEnable": "false",
        "uuid": cucm_uuid(),
    })
    route_patterns.append({
        "pattern": "9.1NXXNXXXXXX",
        "description": "North American long distance",
        "usage": None,
        "routePartitionName": pt_refs["Internal"],
        "blockEnable": "false",
        "uuid": cucm_uuid(),
    })
    route_patterns.append({
        "pattern": "9.411",
        "description": "Directory assistance",
        "usage": None,
        "routePartitionName": pt_refs["Internal"],
        "blockEnable": "false",
        "uuid": cucm_uuid(),
    })
    route_patterns.append({
        "pattern": "9.911",
        "description": "Emergency services",
        "usage": None,
        "routePartitionName": pt_refs["Emergency"],
        "blockEnable": "false",
        "uuid": cucm_uuid(),
    })
    route_patterns.append({
        "pattern": "9.511",
        "description": "Traffic/weather info",
        "usage": None,
        "routePartitionName": pt_refs["Internal"],
        "blockEnable": "false",
        "uuid": cucm_uuid(),
    })

    # Route lists (failover patterns)
    for i in range(0, len(LOCATIONS) - 1, 2):
        loc1 = LOCATIONS[i]
        loc2 = LOCATIONS[i + 1]
        rl_uuid = cucm_uuid()
        route_lists.append({
            "name": f"RL_{loc1['code']}_{loc2['code']}_Failover",
            "description": f"Failover: {loc1['name']} → {loc2['name']}",
            "callManagerGroupName": ref("dCloud_CMGroup"),
            "routeListEnabled": "true",
            "members": {"member": [
                {"routeGroupName": ref(f"{loc1['code']}_RG"), "selectionOrder": 1, "uuid": cucm_uuid()},
                {"routeGroupName": ref(f"{loc2['code']}_RG"), "selectionOrder": 2, "uuid": cucm_uuid()},
            ]},
            "uuid": rl_uuid,
        })

    return {
        "route_patterns": route_patterns,
        "translation_patterns": translation_patterns,
        "sip_trunks": sip_trunks,
        "route_groups": route_groups,
        "route_lists": route_lists,
    }


def generate_templates():
    """Generate button templates for each phone model."""
    button_templates = []

    templates_def = [
        ("8845_BT", "Cisco 8845 Template", [
            ("Line", 1), ("Line", 2), ("BLF Speed Dial", 3), ("BLF Speed Dial", 4),
            ("Speed Dial", 5), ("Speed Dial", 6), ("Speed Dial", 7), ("Speed Dial", 8),
            ("Speed Dial", 9), ("Speed Dial", 10),
        ]),
        ("8861_BT", "Cisco 8861 Template", [
            ("Line", 1), ("Line", 2), ("Line", 3), ("Line", 4),
            ("BLF Speed Dial", 5), ("BLF Speed Dial", 6),
            ("Speed Dial", 7), ("Speed Dial", 8), ("Speed Dial", 9), ("Speed Dial", 10),
        ]),
        ("7841_BT", "Cisco 7841 Template", [
            ("Line", 1), ("Line", 2), ("Speed Dial", 3), ("Speed Dial", 4),
        ]),
        ("7821_BT", "Cisco 7821 Template", [
            ("Line", 1), ("Speed Dial", 2),
        ]),
        ("9841_BT", "Cisco 9841 Template", [
            ("Line", 1), ("Line", 2), ("Line", 3),
            ("BLF Speed Dial", 4), ("BLF Speed Dial", 5), ("BLF Speed Dial", 6),
            ("Speed Dial", 7), ("Speed Dial", 8), ("Speed Dial", 9), ("Speed Dial", 10),
        ]),
        ("8832_BT", "Cisco 8832 Conference Template", [
            ("Line", 1),
        ]),
        ("ATA192_BT", "Cisco ATA 192 Template", [
            ("Line", 1), ("Line", 2),
        ]),
        ("Jabber_BT", "Jabber Desktop Template", [
            ("Line", 1), ("Line", 2), ("BLF Speed Dial", 3), ("BLF Speed Dial", 4),
            ("Speed Dial", 5), ("Speed Dial", 6),
        ]),
        ("Exec_BT", "Executive Phone Template", [
            ("Line", 1), ("Line", 2), ("Line", 3), ("Line", 4),
            ("BLF Speed Dial", 5), ("BLF Speed Dial", 6), ("BLF Speed Dial", 7), ("BLF Speed Dial", 8),
            ("Speed Dial", 9), ("Speed Dial", 10),
        ]),
        ("Lobby_BT", "Lobby Phone Template", [
            ("Line", 1), ("Speed Dial", 2), ("Speed Dial", 3), ("Speed Dial", 4),
        ]),
    ]

    for tpl_name, tpl_desc, buttons in templates_def:
        btn_list = []
        for feature, btn_num in buttons:
            btn_list.append({
                "feature": feature,
                "label": f"{feature} {btn_num}",
                "buttonNumber": btn_num,
                "isFixedFeature": "true" if feature == "Line" and btn_num == 1 else "false",
                "uuid": cucm_uuid(),
            })
        button_templates.append({
            "name": tpl_name,
            "description": tpl_desc,
            "isUserModifiable": "false",
            "buttons": {"button": btn_list},
            "uuid": cucm_uuid(),
        })

    return button_templates


def generate_tier4(infra):
    """Generate recording profiles, remote destinations, device profiles, transforms."""
    recording_profiles = []
    remote_dest_profiles = []
    device_profiles = []
    calling_party_transforms = []
    called_party_transforms = []

    for loc in LOCATIONS:
        code = loc["code"]

        # Recording profile per location
        recording_profiles.append({
            "name": f"{code}_Recording",
            "description": f"Call recording for {loc['name']}",
            "recorderDestination": f"10.1.{LOCATIONS.index(loc) + 10}.50",
            "recordingCssName": ref(f"{code}_CSS"),
            "uuid": cucm_uuid(),
        })

        # CPN transformation per location
        calling_party_transforms.append({
            "pattern": f"+1{loc['area_code']}555XXXX",
            "description": f"{loc['name']} CPN normalization",
            "callingPartyTransformationMask": f"+1{loc['area_code']}555XXXX",
            "routePartitionName": ref(f"{code}_PT"),
            "uuid": cucm_uuid(),
        })

        # Called party transformation
        called_party_transforms.append({
            "pattern": f"9.{loc['area_code']}NXXXXXX",
            "description": f"{loc['name']} called party strip 9",
            "calledPartyTransformationMask": f"1{loc['area_code']}NXXXXXX",
            "routePartitionName": ref(f"{code}_PT"),
            "uuid": cucm_uuid(),
        })

    # Remote destination profiles (30 total, 6 per location)
    for loc in LOCATIONS:
        code = loc["code"]
        for rd_idx in range(6):
            mobile = f"+1{loc['area_code']}{random.randint(2000000, 9999999)}"
            remote_dest_profiles.append({
                "name": f"{code}_RDP_{rd_idx + 1}",
                "description": f"Remote dest profile {rd_idx + 1} for {loc['name']}",
                "destinations": [{
                    "name": f"{code}_mobile_{rd_idx + 1}",
                    "destination": mobile,
                    "isMobilePhone": "true",
                    "enableMobileConnect": "true",
                    "lineAssociation": None,
                    "uuid": cucm_uuid(),
                }],
                "uuid": cucm_uuid(),
            })

    # Extension mobility device profiles (30 total, 6 per location)
    for loc in LOCATIONS:
        code = loc["code"]
        dp_ref = infra["dp_refs"][code]
        for dp_idx in range(6):
            device_profiles.append({
                "name": f"{code}_EM_{dp_idx + 1}",
                "description": f"Extension Mobility profile {dp_idx + 1} for {loc['name']}",
                "product": "Cisco 8845",
                "model": "Cisco 8845",
                "class": "Device Profile",
                "protocol": "SIP",
                "devicePoolName": dp_ref,
                "lines": {"line": [{
                    "index": 1,
                    "dirn": {
                        "pattern": str(loc["ext_start"] + dp_idx + 960),
                        "routePartitionName": infra["pt_refs"][code],
                        "uuid": cucm_uuid(),
                    },
                    "display": f"EM User {dp_idx + 1} - {loc['name']}",
                    "e164Mask": f"+1{loc['area_code']}555{str(loc['ext_start'] + dp_idx + 960)[-4:]}",
                }]},
                "uuid": cucm_uuid(),
            })

    return {
        "recording_profiles": recording_profiles,
        "remote_destination_profiles": remote_dest_profiles,
        "device_profiles": device_profiles,
        "calling_party_transformations": calling_party_transforms,
        "called_party_transformations": called_party_transforms,
    }


def generate_voicemail():
    """Generate voicemail profiles and pilots per location."""
    profiles = []
    pilots = []

    for loc in LOCATIONS:
        code = loc["code"]
        pilot_uuid = cucm_uuid()
        pilots.append({
            "name": f"{code}_VM_Pilot",
            "description": f"Voicemail pilot for {loc['name']}",
            "dirn": str(loc["ext_start"] + 999),
            "cssName": ref(f"{code}_CSS"),
            "isDefault": "false",
            "uuid": pilot_uuid,
        })
        profiles.append({
            "name": f"{code}_VM_Profile",
            "description": f"Voicemail profile for {loc['name']}",
            "isDefault": "false",
            "voiceMailboxMask": None,
            "voiceMailPilot": {
                "dirn": str(loc["ext_start"] + 999),
                "cssName": ref(f"{code}_CSS"),
                "uuid": pilot_uuid,
            },
            "uuid": cucm_uuid(),
        })

    return profiles, pilots


def generate_schedules():
    """Generate time schedules and time periods."""
    schedules = []
    periods = []

    # Business hours per timezone
    for loc in LOCATIONS:
        code = loc["code"]
        period_uuid = cucm_uuid()
        periods.append({
            "name": f"{code}_BusinessHours",
            "description": f"Business hours for {loc['name']}",
            "startTime": "08:00",
            "endTime": "18:00",
            "startDay": "Monday",
            "endDay": "Friday",
            "uuid": period_uuid,
        })
        schedules.append({
            "name": f"{code}_Schedule",
            "description": f"Business schedule for {loc['name']}",
            "scheduleType": "Business Hours",
            "members": {"member": [{
                "timePeriodName": ref(f"{code}_BusinessHours", period_uuid),
                "uuid": cucm_uuid(),
            }]},
            "uuid": cucm_uuid(),
        })

    # After-hours schedule
    ah_period_uuid = cucm_uuid()
    periods.append({
        "name": "AfterHours_Period",
        "description": "After hours - all sites",
        "startTime": "18:00",
        "endTime": "08:00",
        "startDay": "Monday",
        "endDay": "Friday",
        "uuid": ah_period_uuid,
    })
    schedules.append({
        "name": "AfterHours_Schedule",
        "description": "After hours routing schedule",
        "scheduleType": "Holiday",
        "members": {"member": [{
            "timePeriodName": ref("AfterHours_Period", ah_period_uuid),
            "uuid": cucm_uuid(),
        }]},
        "uuid": cucm_uuid(),
    })

    return schedules, periods


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"Reading {RAW_DATA_PATH}...")
    with open(RAW_DATA_PATH) as f:
        data = json.load(f)

    # Count existing
    existing_phones = len(data["devices"]["phones"])
    existing_users = len(data["users"]["users"])
    print(f"Existing: {existing_users} users, {existing_phones} phones")

    # Generate infrastructure
    print("Generating infrastructure (5 locations, device pools, partitions, CSS)...")
    infra = generate_infrastructure()

    # Generate users and phones
    print("Generating 225 users + 800 phones with lines and forwarding...")
    new_users, new_phones, shared_lines = generate_users_and_phones(infra)

    # Generate features
    print("Generating features (hunt groups, pickup groups, call parks)...")
    features = generate_features(infra)

    # Generate routing
    print("Generating routing (trunks, route groups, route patterns, translations)...")
    routing = generate_routing(infra)

    # Generate templates
    print("Generating 10 button templates...")
    templates = generate_templates()

    # Generate tier4
    print("Generating tier4 (recording, remote dest, device profiles, transforms)...")
    tier4 = generate_tier4(infra)

    # Generate voicemail
    print("Generating voicemail profiles and pilots...")
    vm_profiles, vm_pilots = generate_voicemail()

    # Generate schedules
    print("Generating schedules and time periods...")
    schedules, periods = generate_schedules()

    # === MERGE INTO EXISTING DATA ===
    print("\nMerging into existing data...")

    # Locations group
    data["locations"]["cucm_locations"].extend(infra["cucm_locations"])
    data["locations"]["device_pools"].extend(infra["device_pools"])
    data["locations"]["datetime_groups"].extend(infra["datetime_groups"])

    # Users
    data["users"]["users"].extend(new_users)

    # Devices
    data["devices"]["phones"].extend(new_phones)

    # Routing
    data["routing"]["partitions"].extend(infra["partitions"])
    data["routing"]["css_list"].extend(infra["css_list"])
    data["routing"]["route_patterns"].extend(routing["route_patterns"])
    data["routing"]["translation_patterns"].extend(routing["translation_patterns"])
    data["routing"]["sip_trunks"].extend(routing["sip_trunks"])
    data["routing"]["route_groups"].extend(routing["route_groups"])
    data["routing"]["route_lists"].extend(routing["route_lists"])

    # Features
    data["features"]["hunt_pilots"].extend(features["hunt_pilots"])
    data["features"]["hunt_lists"].extend(features["hunt_lists"])
    data["features"]["line_groups"].extend(features["line_groups"])
    data["features"]["pickup_groups"].extend(features["pickup_groups"])
    data["features"]["call_parks"].extend(features["call_parks"])
    data["features"]["time_schedules"].extend(schedules)
    data["features"]["time_periods"].extend(periods)

    # Templates
    data["templates"]["button_templates"].extend(templates)

    # Voicemail
    data["voicemail"]["voicemail_profiles"].extend(vm_profiles)
    data["voicemail"]["voicemail_pilots"].extend(vm_pilots)

    # Tier4
    data["tier4"]["recording_profiles"].extend(tier4["recording_profiles"])
    data["tier4"]["remote_destination_profiles"].extend(tier4["remote_destination_profiles"])
    data["tier4"]["device_profiles"].extend(tier4["device_profiles"])
    data["tier4"]["calling_party_transformations"].extend(tier4["calling_party_transformations"])
    data["tier4"]["called_party_transformations"].extend(tier4["called_party_transformations"])

    # Write back
    print(f"Writing expanded data to {RAW_DATA_PATH}...")
    with open(RAW_DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)

    # Summary
    final_phones = len(data["devices"]["phones"])
    final_users = len(data["users"]["users"])
    print(f"\n{'='*60}")
    print(f"EXPANSION COMPLETE")
    print(f"{'='*60}")
    print(f"Users:     {existing_users} → {final_users} (+{final_users - existing_users})")
    print(f"Phones:    {existing_phones} → {final_phones} (+{final_phones - existing_phones})")
    print(f"Locations: +{len(infra['cucm_locations'])} new")
    print(f"Device Pools: +{len(infra['device_pools'])} new")
    print(f"Partitions: +{len(infra['partitions'])} new")
    print(f"CSS: +{len(infra['css_list'])} new")
    print(f"Hunt Pilots: +{len(features['hunt_pilots'])} new")
    print(f"Hunt Lists: +{len(features['hunt_lists'])} new")
    print(f"Line Groups: +{len(features['line_groups'])} new")
    print(f"Pickup Groups: +{len(features['pickup_groups'])} new")
    print(f"Call Parks: +{len(features['call_parks'])} new")
    print(f"Route Patterns: +{len(routing['route_patterns'])} new")
    print(f"Translation Patterns: +{len(routing['translation_patterns'])} new")
    print(f"SIP Trunks: +{len(routing['sip_trunks'])} new")
    print(f"Route Groups: +{len(routing['route_groups'])} new")
    print(f"Route Lists: +{len(routing['route_lists'])} new")
    print(f"Button Templates: +{len(templates)} new")
    print(f"Recording Profiles: +{len(tier4['recording_profiles'])} new")
    print(f"Remote Dest Profiles: +{len(tier4['remote_destination_profiles'])} new")
    print(f"Device Profiles: +{len(tier4['device_profiles'])} new")
    print(f"CPN Transforms: +{len(tier4['calling_party_transformations'])} new")
    print(f"Called Party Transforms: +{len(tier4['called_party_transformations'])} new")
    print(f"VM Profiles: +{len(vm_profiles)} new")
    print(f"VM Pilots: +{len(vm_pilots)} new")
    print(f"Schedules: +{len(schedules)} new")
    print(f"Time Periods: +{len(periods)} new")
    print(f"Shared Lines: {len(shared_lines)} extensions shared across multiple phones")
    print(f"\nFile size: {RAW_DATA_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
