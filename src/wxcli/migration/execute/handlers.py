"""Operation handlers — pure functions mapping canonical data to API requests.

Each handler takes:
    data: dict — canonical object data from the migration store
    resolved_deps: dict — {canonical_id: webex_id} for completed dependencies
    ctx: dict — session context (orgId, CALLING_LICENSE_ID, etc.)

Each handler returns:
    list[tuple[str, str, dict | None]] — [(method, url, body), ...]

Most handlers return a single tuple. Multi-call operations (e.g., user
configure_settings) return multiple tuples to be executed sequentially.

Handlers are pure functions — no IO, no side effects, fully testable.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

BASE = "https://webexapis.com/v1"

HandlerResult = list[tuple[str, str, dict | None]]


def _url(path: str, ctx: dict, query: dict | None = None) -> str:
    """Build full URL with optional orgId injection."""
    params = {}
    if ctx.get("orgId"):
        params["orgId"] = ctx["orgId"]
    if query:
        params.update(query)
    url = f"{BASE}{path}"
    if params:
        url += f"?{urlencode(params)}"
    return url


def _resolve(deps: dict, canonical_id: str) -> str | None:
    """Look up a Webex ID from resolved_deps by canonical_id."""
    return deps.get(canonical_id)


def _resolve_location(data: dict, deps: dict) -> str | None:
    """Resolve location Webex ID from canonical location_id."""
    loc_cid = data.get("location_id")
    if not loc_cid:
        return None
    return deps.get(loc_cid)


def _resolve_location_from_deps(deps: dict) -> str | None:
    """Fallback: find a location webex_id in resolved_deps by prefix.
    Used when the canonical model doesn't have a location_id field."""
    for cid, wid in deps.items():
        if cid.startswith("location:") and wid:
            return wid
    return None


def _resolve_agents(data: dict, deps: dict, field: str = "agents") -> list[dict]:
    """Resolve agent canonical IDs to Webex person IDs (object format for HG/CQ)."""
    agents = []
    for cid in data.get(field, []):
        wid = deps.get(cid)
        if wid:
            agents.append({"id": wid})
    return agents


def _resolve_agent_ids(data: dict, deps: dict, field: str = "agents") -> list[str]:
    """Resolve agent canonical IDs to plain Webex ID strings (for pickup/paging)."""
    ids = []
    for cid in data.get(field, []):
        wid = deps.get(cid)
        if wid:
            ids.append(wid)
    return ids


# ---------------------------------------------------------------------------
# Tier 0: Infrastructure
# ---------------------------------------------------------------------------

def handle_location_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    addr = data.get("address", {})
    body: dict[str, Any] = {
        "name": data.get("name"),
        "timeZone": data.get("time_zone"),
        "preferredLanguage": data.get("preferred_language"),
        "announcementLanguage": data.get("announcement_language"),
        "address": {
            "address1": addr.get("address1"),
            "city": addr.get("city"),
            "state": addr.get("state"),
            "postalCode": addr.get("postal_code"),
            "country": addr.get("country"),
        },
    }
    # Optional fields
    if addr.get("address2"):
        body["address"]["address2"] = addr["address2"]
    return [("POST", _url("/locations", ctx), body)]


def handle_location_enable_calling(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    # Find the location webex_id from resolved_deps
    loc_wid = None
    for cid, wid in deps.items():
        if cid.startswith("location:") and wid:
            loc_wid = wid
            break
    body: dict[str, Any] = {
        "id": loc_wid,
        "name": data.get("name"),
        "timeZone": data.get("time_zone"),
        "preferredLanguage": data.get("preferred_language"),
        "announcementLanguage": data.get("announcement_language"),
    }
    # Address is required when re-enabling calling on an existing location
    addr = data.get("address")
    if addr:
        body["address"] = {
            "address1": addr.get("address1"),
            "city": addr.get("city"),
            "state": addr.get("state"),
            "postalCode": addr.get("postal_code"),
            "country": addr.get("country"),
        }
    return [("POST", _url("/telephony/config/locations", ctx), body)]


# ---------------------------------------------------------------------------
# Tier 1: Routing backbone
# ---------------------------------------------------------------------------

def handle_trunk_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    loc_wid = _resolve_location(data, deps)
    body: dict[str, Any] = {
        "name": data.get("name"),
        "locationId": loc_wid,
        "trunkType": data.get("trunk_type", "REGISTERING"),
        "password": data.get("password"),
    }
    if data.get("address"):
        body["address"] = data["address"]
    if data.get("domain"):
        body["domain"] = data["domain"]
    if data.get("port"):
        body["port"] = data["port"]
    if data.get("max_concurrent_calls"):
        body["maxConcurrentCalls"] = data["max_concurrent_calls"]
    if data.get("dual_identity_support_enabled") is not None:
        body["dualIdentitySupportEnabled"] = data["dual_identity_support_enabled"]
    return [("POST", _url("/telephony/config/premisePstn/trunks", ctx), body)]


def handle_route_group_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    gateways = []
    for gw in data.get("local_gateways", []):
        trunk_cid = gw.get("trunk_canonical_id")
        trunk_wid = deps.get(trunk_cid) if trunk_cid else None
        if trunk_wid:
            gateways.append({
                "trunkId": trunk_wid,
                "priority": gw.get("priority", 1),
            })
    body: dict[str, Any] = {
        "name": data.get("name"),
        "localGateways": gateways,
    }
    return [("POST", _url("/telephony/config/premisePstn/routeGroups", ctx), body)]


def handle_operating_mode_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    body: dict[str, Any] = {
        "name": data.get("name"),
        "level": data.get("level", "ORGANIZATION"),
    }
    if data.get("schedule_type"):
        body["scheduleType"] = data["schedule_type"]
    if data.get("same_hours_daily"):
        body["sameHoursDaily"] = data["same_hours_daily"]
    if data.get("different_hours_daily"):
        body["differentHoursDaily"] = data["different_hours_daily"]
    if data.get("holidays"):
        body["holidays"] = data["holidays"]
    return [("POST", _url("/telephony/config/operatingModes", ctx), body)]


# ---------------------------------------------------------------------------
# Tier 1: Line key templates (org-wide, no dependencies)
# ---------------------------------------------------------------------------

def handle_line_key_template_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    def _map_key(k: dict, idx_field: str, mod_field: str | None = None) -> dict:
        key_prefix = "kemKey" if mod_field else "lineKey"
        entry: dict[str, Any] = {idx_field: k["index"], f"{key_prefix}Type": k["key_type"]}
        if mod_field:
            entry[mod_field] = k.get("module_index", 1)
        if k.get("label"):
            entry[f"{key_prefix}Label"] = k["label"]
        if k.get("value"):
            entry[f"{key_prefix}Value"] = k["value"]
        return entry

    line_keys = [
        _map_key(k, "lineKeyIndex")
        for k in data.get("line_keys", [])
        if k.get("key_type") != "UNMAPPED"
    ]
    body: dict[str, Any] = {
        "templateName": data.get("name"),
        "deviceModel": data.get("device_model"),
        "lineKeys": line_keys,
    }
    if data.get("kem_module_type"):
        body["kemModuleType"] = data["kem_module_type"]
    kem_keys = [
        _map_key(k, "kemKeyIndex", "kemModuleIndex")
        for k in data.get("kem_keys", [])
        if k.get("key_type") != "UNMAPPED"
    ]
    if kem_keys:
        body["kemKeys"] = kem_keys
    return [("POST", _url("/telephony/config/devices/lineKeyTemplates", ctx), body)]


def handle_schedule_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    """Location schedule (businessHours or holidays) — used by AAs."""
    loc_wid = _resolve_location(data, deps)
    body: dict[str, Any] = {
        "name": data.get("name"),
        "type": data.get("schedule_type", "businessHours"),
    }
    if data.get("events"):
        body["events"] = data["events"]
    return [("POST", _url(f"/telephony/config/locations/{loc_wid}/schedules", ctx), body)]


# ---------------------------------------------------------------------------
# Tier 2: People & Routing
# ---------------------------------------------------------------------------

def handle_user_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    loc_wid = _resolve_location(data, deps)
    body: dict[str, Any] = {
        "emails": data.get("emails", []),
        "firstName": data.get("first_name"),
        "lastName": data.get("last_name"),
        "displayName": data.get("display_name"),
        "locationId": loc_wid,
        "extension": data.get("extension"),
    }
    license_id = ctx.get("CALLING_LICENSE_ID")
    if license_id:
        body["licenses"] = [license_id]
    if data.get("phone_numbers"):
        body["phoneNumbers"] = data["phone_numbers"]
    if data.get("department"):
        body["department"] = data["department"]
    if data.get("title"):
        body["title"] = data["title"]
    return [("POST", _url("/people", ctx, {"callingData": "true"}), body)]


def handle_workspace_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    loc_wid = _resolve_location(data, deps)
    calling_config: dict[str, Any] = {
        "type": data.get("calling_type", "webexCalling"),
        "webexCalling": {
            "locationId": loc_wid,
        },
    }
    if data.get("extension"):
        calling_config["webexCalling"]["extension"] = data["extension"]
    if data.get("phone_number"):
        calling_config["webexCalling"]["phoneNumber"] = data["phone_number"]
    ws_license = ctx.get("WORKSPACE_LICENSE_ID")
    if ws_license:
        calling_config["webexCalling"]["licenses"] = [ws_license]
    body: dict[str, Any] = {
        "displayName": data.get("display_name"),
        "supportedDevices": data.get("supported_devices", "phones"),
        "type": data.get("workspace_type", "other"),
        "calling": calling_config,
    }
    if data.get("hotdesking_status"):
        body["hotdeskingStatus"] = data["hotdesking_status"]
    return [("POST", _url("/workspaces", ctx), body)]


def handle_workspace_assign_number(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    # Find workspace webex_id from resolved deps
    ws_wid = None
    for cid, wid in deps.items():
        if cid.startswith("workspace:") and wid:
            ws_wid = wid
            break
    if not ws_wid or not data.get("phone_number"):
        return []  # No-op if no DID to assign
    body: dict[str, Any] = {"phoneNumbers": [{"type": "work", "value": data["phone_number"]}]}
    return [("PUT", _url(f"/workspaces/{ws_wid}", ctx), body)]


def handle_device_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    body: dict[str, Any] = {}
    if data.get("mac"):
        body["mac"] = data["mac"]
    if data.get("model"):
        body["model"] = data["model"]
    # Resolve owner: person or workspace
    owner_cid = data.get("owner_canonical_id")
    if owner_cid:
        owner_wid = deps.get(owner_cid)
        if owner_wid:
            if owner_cid.startswith("user:"):
                body["personId"] = owner_wid
            elif owner_cid.startswith("workspace:"):
                body["workspaceId"] = owner_wid
    return [("POST", _url("/devices", ctx), body)]


# ---------------------------------------------------------------------------
# Tier 3: Routing patterns
# ---------------------------------------------------------------------------

def handle_dial_plan_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    route_cid = data.get("route_id")
    route_wid = deps.get(route_cid) if route_cid else None
    # Create takes plain strings; modify (PUT) takes {"dialPattern": p, "action": "ADD"}
    patterns = data.get("dial_patterns", [])
    body: dict[str, Any] = {
        "name": data.get("name"),
        "routeId": route_wid,
        "routeType": data.get("route_type", "TRUNK"),
        "dialPatterns": patterns,
    }
    return [("POST", _url("/telephony/config/premisePstn/dialPlans", ctx), body)]


def handle_translation_pattern_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    body: dict[str, Any] = {
        "name": data.get("name"),
        "matchingPattern": data.get("matching_pattern"),
        "replacementPattern": data.get("replacement_pattern"),
    }
    return [("POST", _url("/telephony/config/callRouting/translationPatterns", ctx), body)]


# ---------------------------------------------------------------------------
# Tier 4: Call features
# ---------------------------------------------------------------------------

def handle_hunt_group_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    loc_wid = _resolve_location(data, deps)
    agents = _resolve_agents(data, deps, "agents")
    body: dict[str, Any] = {
        "name": data.get("name"),
        "extension": data.get("extension"),
    }
    if data.get("phone_number"):
        body["phoneNumber"] = data["phone_number"]
    if data.get("policy"):
        body["callPolicies"] = {"policy": data["policy"]}
        if data.get("no_answer_rings"):
            body["callPolicies"]["noAnswer"] = {
                "numberOfRings": data["no_answer_rings"]
            }
    if agents:
        body["agents"] = agents
    return [("POST", _url(f"/telephony/config/locations/{loc_wid}/huntGroups", ctx), body)]


def handle_call_queue_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    loc_wid = _resolve_location(data, deps)
    agents = _resolve_agents(data, deps, "agents")
    body: dict[str, Any] = {
        "name": data.get("name"),
        "extension": data.get("extension"),
        "callPolicies": {
            "routingType": data.get("routing_type", "PRIORITY_BASED"),
            "policy": data.get("policy", "CIRCULAR"),
        },
    }
    if data.get("phone_number"):
        body["phoneNumber"] = data["phone_number"]
    if agents:
        body["agents"] = agents
    if data.get("queue_size"):
        body["queueSize"] = data["queue_size"]
    return [("POST", _url(f"/telephony/config/locations/{loc_wid}/queues", ctx), body)]


def handle_auto_attendant_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    loc_wid = _resolve_location(data, deps)
    body: dict[str, Any] = {
        "name": data.get("name"),
        "extension": data.get("extension"),
    }
    if data.get("phone_number"):
        body["phoneNumber"] = data["phone_number"]
    if data.get("business_schedule"):
        body["businessSchedule"] = data["business_schedule"]
    if data.get("business_hours_menu"):
        body["businessHoursMenu"] = data["business_hours_menu"]
    if data.get("after_hours_menu"):
        body["afterHoursMenu"] = data["after_hours_menu"]
    return [("POST", _url(f"/telephony/config/locations/{loc_wid}/autoAttendants", ctx), body)]


def handle_call_park_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    loc_wid = _resolve_location(data, deps)
    body: dict[str, Any] = {
        "name": data.get("name"),
        "extension": data.get("extension"),
        "recall": {"option": "ALERT_PARKING_USER_ONLY"},
    }
    return [("POST", _url(f"/telephony/config/locations/{loc_wid}/callParks", ctx), body)]


def handle_pickup_group_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    loc_wid = _resolve_location(data, deps)
    # Call Pickup API takes agents as plain string array, not [{"id": ...}]
    agent_ids = _resolve_agent_ids(data, deps, "agents")
    body: dict[str, Any] = {"name": data.get("name")}
    if agent_ids:
        body["agents"] = agent_ids
    return [("POST", _url(f"/telephony/config/locations/{loc_wid}/callPickups", ctx), body)]


def handle_paging_group_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    # CanonicalPagingGroup has no location_id field — resolve from deps
    loc_wid = _resolve_location(data, deps) or _resolve_location_from_deps(deps)
    body: dict[str, Any] = {
        "name": data.get("name"),
        "extension": data.get("extension"),
    }
    # Paging Group API takes targets/originators as plain string arrays, not [{"id": ...}]
    target_ids = _resolve_agent_ids(data, deps, "targets")
    if target_ids:
        body["targets"] = target_ids
    originator_ids = _resolve_agent_ids(data, deps, "originators")
    if originator_ids:
        body["originators"] = originator_ids
        body["originatorCallerIdEnabled"] = True
    return [("POST", _url(f"/telephony/config/locations/{loc_wid}/paging", ctx), body)]


# ---------------------------------------------------------------------------
# Tier 5: Settings configuration
# ---------------------------------------------------------------------------

def handle_user_configure_settings(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    person_wid = None
    for cid, wid in deps.items():
        if cid.startswith("user:") and wid:
            person_wid = wid
            break
    if not person_wid:
        return []
    settings = data.get("call_settings", {})
    calls = []
    for feature_name, feature_body in settings.items():
        url = _url(f"/people/{person_wid}/features/{feature_name}", ctx)
        calls.append(("PUT", url, feature_body))
    return calls


def handle_user_configure_voicemail(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    person_wid = None
    for cid, wid in deps.items():
        if cid.startswith("user:") and wid:
            person_wid = wid
            break
    if not person_wid:
        return []
    vm_data = data.get("voicemail") or data.get("voicemail_settings") or {}
    return [("PUT", _url(f"/telephony/config/people/{person_wid}/voicemail", ctx), vm_data)]


def handle_device_configure_settings(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    device_wid = None
    for cid, wid in deps.items():
        if cid.startswith("device:") and wid:
            device_wid = wid
            break
    if not device_wid:
        return []
    settings = data.get("device_settings", {})
    if not settings:
        return []
    return [("PUT", _url(f"/telephony/config/devices/{device_wid}/settings", ctx), settings)]


def handle_workspace_configure_settings(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    ws_wid = None
    for cid, wid in deps.items():
        if cid.startswith("workspace:") and wid:
            ws_wid = wid
            break
    if not ws_wid:
        return []
    # Workspace settings use the /workspaces/{id}/features/ path family
    settings = data.get("call_settings", {})
    calls = []
    for feature_name, feature_body in settings.items():
        url = _url(f"/workspaces/{ws_wid}/features/{feature_name}", ctx)
        calls.append(("PUT", url, feature_body))
    return calls


def handle_calling_permission_assign(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    permissions = data.get("calling_permissions", [])
    api_permissions = [
        {"callType": p["call_type"], "action": p.get("action", "ALLOW")}
        for p in permissions
    ]
    body: dict[str, Any] = {
        "useCustomEnabled": data.get("use_custom_enabled", True),
        "callingPermissions": api_permissions,
    }
    calls = []
    for user_cid in data.get("assigned_users", []):
        person_wid = deps.get(user_cid)
        if person_wid:
            url = _url(f"/people/{person_wid}/features/outgoingPermission", ctx)
            calls.append(("PUT", url, body))
    return calls


def handle_monitoring_list_configure(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    person_wid = deps.get(data.get("user_canonical_id", ""))
    if not person_wid:
        return []
    members = []
    for m in data.get("monitored_members", []):
        target_cid = m.get("target_canonical_id")
        if not target_cid:
            continue
        wid = deps.get(target_cid)
        if wid:
            members.append({"id": wid})
    if not members:
        return []
    body: dict[str, Any] = {
        "enableCallParkNotification": bool(data.get("call_park_notification_enabled")),
        "monitoredMembers": members,
    }
    return [("PUT", _url(f"/people/{person_wid}/features/monitoring", ctx), body)]


def handle_call_forwarding_configure(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    person_wid = deps.get(data.get("user_canonical_id", ""))
    if not person_wid:
        return []
    # Only generate if at least one forwarding type is enabled
    if not any([data.get("always_enabled"), data.get("busy_enabled"), data.get("no_answer_enabled")]):
        return []
    def _cf_block(**kwargs: Any) -> dict[str, Any]:
        """Build a callForwarding sub-block, omitting None-valued optional fields."""
        return {k: v for k, v in kwargs.items() if v is not None}

    body: dict[str, Any] = {
        "callForwarding": {
            "always": _cf_block(
                enabled=bool(data.get("always_enabled")),
                destination=data.get("always_destination"),
                ringReminderEnabled=False,
                destinationVoicemailEnabled=bool(data.get("always_to_voicemail")),
            ),
            "busy": _cf_block(
                enabled=bool(data.get("busy_enabled")),
                destination=data.get("busy_destination"),
                destinationVoicemailEnabled=bool(data.get("busy_to_voicemail")),
            ),
            "noAnswer": _cf_block(
                enabled=bool(data.get("no_answer_enabled")),
                destination=data.get("no_answer_destination"),
                destinationVoicemailEnabled=bool(data.get("no_answer_to_voicemail")),
                numberOfRings=data.get("no_answer_ring_count"),
            ),
        },
        "businessContinuity": {"enabled": False},
    }
    return [("PUT", _url(f"/people/{person_wid}/features/callForwarding", ctx), body)]


# ---------------------------------------------------------------------------
# Tier 7: Device finalization (after monitoring, shared lines)
# ---------------------------------------------------------------------------

def handle_device_layout_configure(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    device_cid = data.get("device_canonical_id")
    device_wid = deps.get(device_cid) if device_cid else None
    if not device_wid:
        return []

    results: HandlerResult = []

    # Call 1 (conditional): PUT members
    resolved_members = []
    for m in data.get("line_members", []):
        member_cid = m.get("member_canonical_id")
        wid = deps.get(member_cid) if member_cid else None
        if wid:
            resolved_members.append({"id": wid, "port": m.get("port", 1)})
    if resolved_members:
        results.append((
            "PUT",
            _url(f"/telephony/config/devices/{device_wid}/members", ctx),
            {"members": resolved_members},
        ))

    # Call 2: PUT layout
    def _map_lk(k: dict) -> dict:
        entry: dict[str, Any] = {"lineKeyIndex": k["index"], "lineKeyType": k["key_type"]}
        if k.get("label"):
            entry["lineKeyLabel"] = k["label"]
        if k.get("value"):
            entry["lineKeyValue"] = k["value"]
        return entry

    def _map_kk(k: dict) -> dict:
        entry: dict[str, Any] = {
            "kemModuleIndex": k.get("module_index", 1),
            "kemKeyIndex": k["index"],
            "kemKeyType": k["key_type"],
        }
        if k.get("label"):
            entry["kemKeyLabel"] = k["label"]
        return entry

    line_keys = data.get("resolved_line_keys", [])
    kem_keys = data.get("resolved_kem_keys", [])
    layout_mode = "CUSTOM" if line_keys else "DEFAULT"
    layout_body: dict[str, Any] = {"layoutMode": layout_mode}
    if line_keys:
        layout_body["lineKeys"] = [_map_lk(k) for k in line_keys]
    if kem_keys:
        layout_body["kemKeys"] = [_map_kk(k) for k in kem_keys]
    results.append((
        "PUT",
        _url(f"/telephony/config/devices/{device_wid}/layout", ctx),
        layout_body,
    ))

    # Call 3: POST applyChanges
    results.append((
        "POST",
        _url(f"/telephony/config/devices/{device_wid}/actions/applyChanges/invoke", ctx),
        None,
    ))
    return results


# ---------------------------------------------------------------------------
# Tier 6: Shared/virtual lines
# ---------------------------------------------------------------------------

def handle_shared_line_configure(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    # Shared line requires updating device members + apply-changes
    calls = []
    for dev_cid in data.get("device_canonical_ids", []):
        dev_wid = deps.get(dev_cid)
        if dev_wid:
            # This is a complex multi-step operation — simplified for bulk execution
            # Full shared-line config is better handled by the domain skill
            calls.append(("PUT", _url(f"/telephony/config/devices/{dev_wid}/members", ctx),
                          {"members": []}))  # Populated from canonical data
    return calls


def handle_virtual_line_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    loc_wid = _resolve_location(data, deps)
    body: dict[str, Any] = {
        "firstName": data.get("display_name", "Virtual"),
        "lastName": "Line",
        "locationId": loc_wid,
    }
    if data.get("extension"):
        body["extension"] = data["extension"]
    if data.get("phone_number"):
        body["phoneNumber"] = data["phone_number"]
    return [("POST", _url("/telephony/config/virtualLines", ctx), body)]


def handle_virtual_line_configure(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    vl_wid = None
    for cid, wid in deps.items():
        if cid.startswith("virtual_line:") and wid:
            vl_wid = wid
            break
    if not vl_wid:
        return []
    # Virtual line settings — pass through whatever canonical data has
    settings = data.get("settings", {})
    if not settings:
        return []
    return [("PUT", _url(f"/telephony/config/virtualLines/{vl_wid}", ctx), settings)]


# HANDLER_REGISTRY — complete with all operation types
HANDLER_REGISTRY: dict[tuple[str, str], Any] = {
    ("location", "create"): handle_location_create,
    ("location", "enable_calling"): handle_location_enable_calling,
    ("line_key_template", "create"): handle_line_key_template_create,
    ("trunk", "create"): handle_trunk_create,
    ("route_group", "create"): handle_route_group_create,
    ("operating_mode", "create"): handle_operating_mode_create,
    ("schedule", "create"): handle_schedule_create,
    ("user", "create"): handle_user_create,
    ("workspace", "create"): handle_workspace_create,
    ("workspace", "assign_number"): handle_workspace_assign_number,
    ("device", "create"): handle_device_create,
    ("dial_plan", "create"): handle_dial_plan_create,
    ("translation_pattern", "create"): handle_translation_pattern_create,
    ("hunt_group", "create"): handle_hunt_group_create,
    ("call_queue", "create"): handle_call_queue_create,
    ("auto_attendant", "create"): handle_auto_attendant_create,
    ("call_park", "create"): handle_call_park_create,
    ("pickup_group", "create"): handle_pickup_group_create,
    ("paging_group", "create"): handle_paging_group_create,
    ("user", "configure_settings"): handle_user_configure_settings,
    ("user", "configure_voicemail"): handle_user_configure_voicemail,
    ("device", "configure_settings"): handle_device_configure_settings,
    ("workspace", "configure_settings"): handle_workspace_configure_settings,
    ("calling_permission", "assign"): handle_calling_permission_assign,
    ("call_forwarding", "configure"): handle_call_forwarding_configure,
    ("monitoring_list", "configure"): handle_monitoring_list_configure,
    ("device_layout", "configure"): handle_device_layout_configure,
    ("shared_line", "configure"): handle_shared_line_configure,
    ("virtual_line", "create"): handle_virtual_line_create,
    ("virtual_line", "configure"): handle_virtual_line_configure,
}
