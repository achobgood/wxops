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
    """Resolve agent canonical IDs to Webex person IDs."""
    agents = []
    for cid in data.get(field, []):
        wid = deps.get(cid)
        if wid:
            agents.append({"id": wid})
    return agents


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


# HANDLER_REGISTRY placeholder — populated fully in Task 2 and 3
HANDLER_REGISTRY: dict[tuple[str, str], Any] = {
    ("location", "create"): handle_location_create,
    ("location", "enable_calling"): handle_location_enable_calling,
    ("trunk", "create"): handle_trunk_create,
    ("route_group", "create"): handle_route_group_create,
    ("operating_mode", "create"): handle_operating_mode_create,
    ("schedule", "create"): handle_schedule_create,
}
