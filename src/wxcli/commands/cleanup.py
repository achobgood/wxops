"""Batch-delete Webex Calling resources in dependency-safe order."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import click
import typer
from rich.console import Console
from wxc_sdk.rest import RestError

# Location-delete retry tuning: after the initial 90s disable-calling
# propagation wait, 17-location orgs have been observed to still 409 on
# first attempt. 5 attempts × 60s = 5 min worst case per laggard location,
# which fits under typical agent/bash tool timeouts and covers the trailing
# edge of async disable-calling propagation without masking real failures.
LOCATION_DELETE_MAX_ATTEMPTS = 5
LOCATION_DELETE_RETRY_SLEEP = 60

# Signature of the CCP-integrated PSTN backend gate. When a delete fails with
# this error code, the org uses Cisco Calling Plan and the resource is managed
# by the Webex backend — no API action on our side can unblock it.
CCP_INTEGRATED_ERROR_CODE = "ERR.V.TRM.TMN60004"

from wxcli.auth import get_api
from wxcli.config import get_org_id

logger = logging.getLogger(__name__)
console = Console()

BASE = "https://webexapis.com/v1"

app = typer.Typer(
    name="cleanup",
    help="Batch-delete Webex Calling resources in dependency-safe order.",
    no_args_is_help=True,
)


@dataclass
class ResourceType:
    """Definition of a Webex resource type for cleanup."""
    name: str
    list_url: str
    item_key: str
    delete_url: str
    location_scoped_list: bool = False
    supports_location_filter: bool = False
    id_field: str = "id"
    name_field: str = "name"
    extra_delete_fields: list[str] = field(default_factory=list)


RESOURCE_TYPES: dict[str, ResourceType] = {
    "dial_plans": ResourceType(
        name="Dial Plans",
        list_url="/telephony/config/premisePstn/dialPlans",
        item_key="dialPlans",
        delete_url="/telephony/config/premisePstn/dialPlans/{id}",
    ),
    "route_lists": ResourceType(
        name="Route Lists",
        list_url="/telephony/config/premisePstn/routeLists",
        item_key="routeLists",
        delete_url="/telephony/config/premisePstn/routeLists/{id}",
    ),
    "route_groups": ResourceType(
        name="Route Groups",
        list_url="/telephony/config/premisePstn/routeGroups",
        item_key="routeGroups",
        delete_url="/telephony/config/premisePstn/routeGroups/{id}",
    ),
    "translation_patterns": ResourceType(
        name="Translation Patterns",
        list_url="/telephony/config/callRouting/translationPatterns",
        item_key="translationPatterns",
        delete_url="/telephony/config/callRouting/translationPatterns/{id}",
    ),
    "trunks": ResourceType(
        name="Trunks",
        list_url="/telephony/config/premisePstn/trunks",
        item_key="trunks",
        delete_url="/telephony/config/premisePstn/trunks/{id}",
    ),
    "hunt_groups": ResourceType(
        name="Hunt Groups",
        list_url="/telephony/config/huntGroups",
        item_key="huntGroups",
        delete_url="/telephony/config/locations/{location_id}/huntGroups/{id}",
        supports_location_filter=True,
    ),
    "auto_attendants": ResourceType(
        name="Auto Attendants",
        list_url="/telephony/config/autoAttendants",
        item_key="autoAttendants",
        delete_url="/telephony/config/locations/{location_id}/autoAttendants/{id}",
        supports_location_filter=True,
    ),
    "call_queues": ResourceType(
        name="Call Queues",
        list_url="/telephony/config/queues",
        item_key="queues",
        delete_url="/telephony/config/locations/{location_id}/queues/{id}",
        supports_location_filter=True,
    ),
    "paging_groups": ResourceType(
        name="Paging Groups",
        list_url="/telephony/config/paging",
        item_key="locationPaging",
        delete_url="/telephony/config/locations/{location_id}/paging/{id}",
        supports_location_filter=True,
    ),
    "call_parks": ResourceType(
        name="Call Parks",
        list_url="/telephony/config/locations/{location_id}/callParks",
        item_key="callParks",
        delete_url="/telephony/config/locations/{location_id}/callParks/{id}",
        location_scoped_list=True,
    ),
    "call_pickups": ResourceType(
        name="Call Pickups",
        list_url="/telephony/config/locations/{location_id}/callPickups",
        item_key="callPickups",
        delete_url="/telephony/config/locations/{location_id}/callPickups/{id}",
        location_scoped_list=True,
    ),
    "operating_modes": ResourceType(
        name="Operating Modes",
        list_url="/telephony/config/operatingModes",
        item_key="operatingModes",
        delete_url="/telephony/config/operatingModes/{id}",
    ),
    "schedules": ResourceType(
        name="Schedules",
        list_url="/telephony/config/locations/{location_id}/schedules",
        item_key="schedules",
        delete_url="/telephony/config/locations/{location_id}/schedules/{type}/{id}",
        location_scoped_list=True,
        extra_delete_fields=["type"],
    ),
    "virtual_lines": ResourceType(
        name="Virtual Lines",
        list_url="/telephony/config/virtualLines",
        item_key="virtualLines",
        delete_url="/telephony/config/virtualLines/{id}",
    ),
    "devices": ResourceType(
        name="Devices",
        list_url="/devices",
        item_key="items",
        delete_url="/devices/{id}",
    ),
    "workspaces": ResourceType(
        name="Workspaces",
        list_url="/workspaces",
        item_key="items",
        delete_url="/workspaces/{id}",
        supports_location_filter=True,
    ),
    "users": ResourceType(
        name="Users",
        list_url="/people",
        item_key="items",
        delete_url="/people/{id}",
        name_field="displayName",
    ),
    "numbers": ResourceType(
        name="Numbers",
        list_url="/telephony/config/numbers",
        item_key="phoneNumbers",
        delete_url="/telephony/config/locations/{location_id}/numbers",
    ),
    "locations": ResourceType(
        name="Locations",
        list_url="/locations",
        item_key="items",
        delete_url="/locations/{id}",
    ),
}

# Deletion proceeds in this order (reverse of creation).
# Within each layer, all deletions run in parallel.
DELETION_LAYERS: list[list[str]] = [
    ["dial_plans"],                      # Layer 1: reference route lists/groups
    ["route_lists"],                     # Layer 2: reference route groups
    ["route_groups"],                    # Layer 3: reference trunks
    ["translation_patterns"],            # Layer 4: org-level or location-level
    ["trunks"],                          # Layer 5: reference locations
    ["call_queues", "hunt_groups", "auto_attendants", "paging_groups", "call_parks", "call_pickups"],  # Layer 6
    ["operating_modes", "schedules"],    # Layer 7: were referenced by AAs
    ["virtual_lines"],                   # Layer 8
    ["devices"],                         # Layer 9
    ["workspaces"],                      # Layer 10: must delete before disable-calling
    ["users"],                           # Layer 11: opt-in via --include-users
    ["numbers"],                         # Layer 12: remove numbers before location deletion
    ["locations"],                       # Layer 13: disable calling first, then delete
]


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def list_resources(
    api,
    rt: ResourceType,
    org_id: str | None,
    location_ids: list[str] | None,
    scope_filter: bool = True,
) -> list[dict]:
    """List all resources of a given type, respecting scope.

    Args:
        scope_filter: When True, filter supports_location_filter resources by
            location_ids. Set False for org-wide cleanup so resources without
            a locationId are not silently excluded.
    """
    params = {}
    if org_id:
        params["orgId"] = org_id

    if rt.location_scoped_list:
        # Must iterate per location
        if not location_ids:
            return []
        all_items = []
        for loc_id in location_ids:
            url = f"{BASE}{rt.list_url.format(location_id=loc_id)}"
            try:
                items = list(api.session.follow_pagination(
                    url=url, params=dict(params), item_key=rt.item_key,
                ))
                # Tag each item with its location_id for delete
                for item in items:
                    item.setdefault("locationId", loc_id)
                all_items.extend(items)
            except RestError as e:
                logger.warning("Failed to list %s in location %s: %s", rt.name, loc_id, e)
        return all_items

    # Org-scoped list
    url = f"{BASE}{rt.list_url}"
    try:
        items = list(api.session.follow_pagination(
            url=url, params=params, item_key=rt.item_key,
        ))
    except RestError as e:
        logger.warning("Failed to list %s: %s", rt.name, e)
        return []

    # Filter by location scope if requested and items have locationId
    if scope_filter and location_ids and rt.supports_location_filter:
        loc_set = set(location_ids)
        items = [i for i in items if i.get("locationId") in loc_set]

    return items


def build_inventory(
    api,
    org_id: str | None,
    location_ids: list[str] | None,
    include_users: bool,
    include_locations: bool,
    scope_filter: bool = True,
) -> dict[str, list[dict]]:
    """Build a full inventory of resources to delete."""
    inventory: dict[str, list[dict]] = {}

    for layer in DELETION_LAYERS:
        for key in layer:
            if key == "users" and not include_users:
                continue
            if key == "locations" and not include_locations:
                continue
            if key == "numbers":
                continue  # numbers populated separately by build_number_inventory

            rt = RESOURCE_TYPES[key]
            items = list_resources(api, rt, org_id, location_ids, scope_filter=scope_filter)
            if items:
                inventory[key] = items

    return inventory


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

@dataclass
class DeleteResult:
    """Result of a single delete operation."""
    resource_type: str
    resource_id: str
    resource_name: str
    success: bool
    error: str | None = None
    # True when a failure was classified as a CCP-integrated PSTN backend
    # gate (e.g. Webex async-releasing trunk references). These aren't real
    # failures the operator can act on — the final summary reports them
    # separately and the process exits 0.
    ccp_blocked: bool = False


def delete_resource(
    api,
    rt: ResourceType,
    item: dict,
    org_id: str | None,
) -> DeleteResult:
    """Delete a single resource. Returns a DeleteResult."""
    resource_id = item.get(rt.id_field, "unknown")
    resource_name = item.get(rt.name_field, "unnamed")

    # Build delete URL
    fmt_kwargs = {"id": resource_id}
    if "{location_id}" in rt.delete_url:
        fmt_kwargs["location_id"] = item.get("locationId", "")
    for field_name in rt.extra_delete_fields:
        fmt_kwargs[field_name] = item.get(field_name, "")

    url = f"{BASE}{rt.delete_url.format(**fmt_kwargs)}"
    params = {}
    if org_id:
        params["orgId"] = org_id

    try:
        api.session.rest_delete(url, params=params)
        return DeleteResult(
            resource_type=rt.name,
            resource_id=resource_id,
            resource_name=resource_name,
            success=True,
        )
    except Exception as e:
        return DeleteResult(
            resource_type=rt.name,
            resource_id=resource_id,
            resource_name=resource_name,
            success=False,
            error=str(e),
        )


def execute_layer(
    api,
    layer_keys: list[str],
    inventory: dict[str, list[dict]],
    org_id: str | None,
    max_concurrent: int = 5,
) -> list[DeleteResult]:
    """Execute all deletions in a layer in parallel."""
    # Collect all (rt, item) pairs for this layer
    work: list[tuple[ResourceType, dict]] = []
    for key in layer_keys:
        if key not in inventory:
            continue
        rt = RESOURCE_TYPES[key]
        for item in inventory[key]:
            work.append((rt, item))

    if not work:
        return []

    results: list[DeleteResult] = []
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {
            executor.submit(delete_resource, api, rt, item, org_id): (rt, item)
            for rt, item in work
        }
        for future in as_completed(futures):
            results.append(future.result())

    return results


# ---------------------------------------------------------------------------
# Location-specific deletion
# ---------------------------------------------------------------------------

def disable_location_calling(
    api,
    location_id: str,
    org_id: str | None,
) -> DeleteResult:
    """Disable Webex Calling on a location (prerequisite to deletion)."""
    url = f"{BASE}/telephony/config/locations/{location_id}"
    params = {}
    if org_id:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
        return DeleteResult(
            resource_type="Location Calling",
            resource_id=location_id,
            resource_name=f"disable-calling:{location_id}",
            success=True,
        )
    except RestError as e:
        return DeleteResult(
            resource_type="Location Calling",
            resource_id=location_id,
            resource_name=f"disable-calling:{location_id}",
            success=False,
            error=str(e),
        )


def _is_ccp_integrated_error(err: str) -> bool:
    """True if an error message carries the CCP-integrated PSTN signature.

    Webex returns ``ERR.V.TRM.TMN60004`` (or a variant message referencing
    "non-integrated CCP") whenever an API caller tries to delete a resource
    whose lifecycle is owned by the Cisco Calling Plan backend. This signature
    has been observed for number deletes; it can also bleed into downstream
    409s on location delete when the backend is still releasing internal
    trunk references asynchronously.
    """
    if not err:
        return False
    if CCP_INTEGRATED_ERROR_CODE in err:
        return True
    lowered = err.lower()
    return "non-integrated ccp" in lowered


def _is_ccp_backend_gate(
    err: str, local_dependencies_clear: bool,
) -> bool:
    """Classify a 409 on location delete as a CCP backend-cleanup gate.

    The gate fires when either:
      * the explicit CCP error code appears in the body, OR
      * the message says "being referenced" AND a prior pre-check has
        confirmed no local-visible dependencies remain.

    When the gate fires there is nothing the caller can do to speed things
    up — Webex's internal PSTN backend is async-releasing trunk references
    and typically takes 1-4 hours in dCloud/CCP orgs.
    """
    if not err:
        return False
    if _is_ccp_integrated_error(err):
        return True
    lowered = err.lower()
    if local_dependencies_clear and "being referenced" in lowered:
        return True
    return False


def _location_has_local_dependencies(
    api, location_id: str, org_id: str | None,
) -> bool:
    """Probe for visible dependencies at a location.

    Returns True if any users, workspaces, devices, features (AA/CQ/HG/paging/
    parks/pickups), trunks, or route groups still resolve at the location.
    When False, a 409 "being referenced" is almost certainly a backend gate
    rather than a real blocker.
    """
    probes: list[tuple[str, dict]] = [
        ("/people", {"locationId": location_id}),
        ("/workspaces", {"locationId": location_id}),
        ("/devices", {"locationId": location_id}),
        ("/telephony/config/huntGroups", {"locationId": location_id}),
        ("/telephony/config/autoAttendants", {"locationId": location_id}),
        ("/telephony/config/queues", {"locationId": location_id}),
        ("/telephony/config/paging", {"locationId": location_id}),
        (f"/telephony/config/locations/{location_id}/callParks", {}),
        (f"/telephony/config/locations/{location_id}/callPickups", {}),
        ("/telephony/config/premisePstn/trunks", {"locationId": location_id}),
        ("/telephony/config/premisePstn/routeGroups", {}),
    ]
    params_base: dict = {}
    if org_id:
        params_base["orgId"] = org_id
    for path, extra in probes:
        params = {**params_base, **extra}
        try:
            result = api.session.rest_get(f"{BASE}{path}", params=params)
        except Exception:
            # Probe failures shouldn't mask the gate; treat as "clear".
            continue
        if not isinstance(result, dict):
            continue
        for values in result.values():
            if isinstance(values, list) and values:
                # Route groups have no locationId filter — only count them
                # if at least one references this location.
                if path.endswith("/routeGroups"):
                    if any(
                        rg.get("location", {}).get("id") == location_id
                        for rg in values
                    ):
                        return True
                    continue
                return True
    return False


def _extract_blocker(err: str) -> str | None:
    """Extract a blocking resource hint from a 409 error body if the API surfaces one."""
    if not err:
        return None
    lowered = err.lower()
    for kw in (
        "device", "user", "workspace", "virtual line", "trunk",
        "route group", "route list", "dial plan", "hunt group",
        "call queue", "auto attendant", "number",
    ):
        if kw in lowered:
            return kw
    return None


def delete_location(
    api,
    item: dict,
    org_id: str | None,
    max_attempts: int = LOCATION_DELETE_MAX_ATTEMPTS,
    retry_sleep: int = LOCATION_DELETE_RETRY_SLEEP,
) -> DeleteResult:
    """Delete a location (must have calling disabled first).

    Retries up to ``max_attempts`` times with ``retry_sleep`` seconds between
    attempts. The 90-second disable-calling propagation wait in the caller
    often isn't enough on larger orgs — the backend may still 409 for several
    minutes. Each attempt emits a stdout line via ``click.echo`` (flushed)
    so an observing parent process sees liveness and never has to hand-roll
    an external polling loop.
    """
    location_id = item.get("id", "")
    name = item.get("name", "unnamed")
    url = f"{BASE}/locations/{location_id}"
    params = {}
    if org_id:
        params["orgId"] = org_id

    last_error: str = ""
    ccp_blocked = False
    for attempt in range(1, max_attempts + 1):
        try:
            api.session.rest_delete(url, params=params)
            click.echo(f"[location={name}] deleted", nl=True)
            try:
                click.get_text_stream("stdout").flush()
            except Exception:
                pass
            return DeleteResult(
                resource_type="Locations",
                resource_id=location_id,
                resource_name=name,
                success=True,
            )
        except RestError as e:
            last_error = str(e)
            is_conflict = "409" in last_error or "conflict" in last_error.lower()

            # CCP backend-gate short-circuit: retrying this is pointless —
            # only the Webex backend can clear it, on the order of hours.
            # The explicit error code is a hard signal on its own; the
            # "being referenced" path requires confirming no local-visible
            # deps remain before we call it a gate.
            explicit_ccp = _is_ccp_integrated_error(last_error)
            if explicit_ccp:
                ccp_blocked = True
                break
            if is_conflict and "being referenced" in last_error.lower():
                local_clear = not _location_has_local_dependencies(
                    api, location_id, org_id,
                )
                if _is_ccp_backend_gate(last_error, local_clear):
                    ccp_blocked = True
                    break

            if attempt < max_attempts and is_conflict:
                click.echo(
                    f"[location={name}] attempt {attempt}/{max_attempts}: "
                    f"409 — retrying in {retry_sleep}s",
                    nl=True,
                )
                try:
                    click.get_text_stream("stdout").flush()
                except Exception:
                    pass
                time.sleep(retry_sleep)
                continue
            # Non-409 error, or exhausted attempts: stop retrying.
            break

    if ccp_blocked:
        final_msg = (
            f"[location={name}] blocked by CCP-integrated PSTN backend "
            f"cleanup — Webex backend has not yet released internal trunk "
            f"references. This typically clears in 1-4 hours for dCloud/CCP "
            f"orgs. Re-run `wxcli cleanup run` later (it is idempotent) to "
            f"retry. No action you can take to speed this up."
        )
        click.echo(final_msg, nl=True)
        try:
            click.get_text_stream("stdout").flush()
        except Exception:
            pass
        return DeleteResult(
            resource_type="Locations",
            resource_id=location_id,
            resource_name=name,
            success=False,
            error=final_msg,
            ccp_blocked=True,
        )

    blocker = _extract_blocker(last_error)
    if blocker:
        final_msg = (
            f"delete failed after {max_attempts} attempt(s); "
            f"blocked by {blocker}: {last_error}"
        )
    else:
        final_msg = (
            f"delete failed after {max_attempts} attempt(s): {last_error}"
        )
    click.echo(f"[location={name}] {final_msg}", nl=True)
    try:
        click.get_text_stream("stdout").flush()
    except Exception:
        pass
    return DeleteResult(
        resource_type="Locations",
        resource_id=location_id,
        resource_name=name,
        success=False,
        error=final_msg,
    )


# ---------------------------------------------------------------------------
# Number removal
# ---------------------------------------------------------------------------

def list_location_numbers(
    api,
    location_id: str,
    org_id: str | None,
) -> list[dict]:
    """List phone numbers assigned to a location."""
    url = f"{BASE}/telephony/config/numbers"
    params = {"locationId": location_id}
    if org_id:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
        if isinstance(result, dict):
            return result.get("phoneNumbers", [])
        return result if isinstance(result, list) else []
    except RestError as e:
        logger.warning("Failed to list numbers for location %s: %s", location_id, e)
        return []


def delete_location_numbers(
    api,
    location_id: str,
    phone_numbers: list[str],
    org_id: str | None,
) -> list[DeleteResult]:
    """Delete phone numbers from a location in batches of 5 (API limit)."""
    results: list[DeleteResult] = []
    url = f"{BASE}/telephony/config/locations/{location_id}/numbers"
    params = {}
    if org_id:
        params["orgId"] = org_id

    # API allows max 5 numbers per request
    for i in range(0, len(phone_numbers), 5):
        batch = phone_numbers[i:i + 5]
        try:
            api.session.rest_delete(url, params=params, json={"phoneNumbers": batch})
            for num in batch:
                results.append(DeleteResult(
                    resource_type="Numbers",
                    resource_id=num,
                    resource_name=num,
                    success=True,
                ))
        except RestError as e:
            err_str = str(e)
            # CCP-integrated PSTN: number lifecycle is managed via the PSTN
            # portal, not the API. Log and skip — don't treat as a failure.
            if _is_ccp_integrated_error(err_str):
                for num in batch:
                    click.echo(
                        f"[number={num}] skipped — CCP-integrated, "
                        f"managed via PSTN portal",
                        nl=True,
                    )
                    try:
                        click.get_text_stream("stdout").flush()
                    except Exception:
                        pass
                    results.append(DeleteResult(
                        resource_type="Numbers",
                        resource_id=num,
                        resource_name=num,
                        success=True,
                        error=None,
                        ccp_blocked=True,
                    ))
                continue
            for num in batch:
                results.append(DeleteResult(
                    resource_type="Numbers",
                    resource_id=num,
                    resource_name=num,
                    success=False,
                    error=err_str,
                ))
    return results


def build_number_inventory(
    api,
    location_ids: list[str],
    org_id: str | None,
) -> dict[str, list[str]]:
    """Build a map of location_id -> [phone_numbers] for cleanup.

    Returns only locations that have numbers to remove.
    """
    inventory: dict[str, list[str]] = {}
    for loc_id in location_ids:
        numbers = list_location_numbers(api, loc_id, org_id)
        phone_nums = []
        ext_only = 0
        for n in numbers:
            # Extension-only records have no phoneNumber field — they are
            # extension owners (person/workspace/virtual line), not PSTN
            # number resources, and get released when the owner is deleted.
            if not n.get("phoneNumber"):
                ext_only += 1
                continue
            if n.get("mainNumber") is True:
                continue
            phone_nums.append(n["phoneNumber"])
        if ext_only:
            logger.info(
                "location %s: skipped %d extension-only record(s) "
                "(extension owners, not phone numbers)",
                loc_id, ext_only,
            )
        if phone_nums:
            inventory[loc_id] = phone_nums
    return inventory


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_dry_run(inventory: dict[str, list[dict]]) -> str:
    """Format the inventory as a dry-run report."""
    lines = ["", "=== DRY RUN — Resources that would be deleted ===", ""]
    total = 0
    for layer in DELETION_LAYERS:
        for key in layer:
            if key not in inventory:
                continue
            items = inventory[key]
            rt = RESOURCE_TYPES[key]
            lines.append(f"  {rt.name:<25s} {len(items):>4d}")
            for item in items[:5]:
                name = item.get(rt.name_field, item.get("displayName", "unnamed"))
                rid = item.get(rt.id_field, "?")
                lines.append(f"    - {name} ({rid[:12]}...)")
            if len(items) > 5:
                lines.append(f"    ... and {len(items) - 5} more")
            total += len(items)

    lines.append("")
    lines.append(f"  {'TOTAL':<25s} {total:>4d}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI Command
# ---------------------------------------------------------------------------

def _resolve_location_ids(
    api, scope: str | None, org_id: str | None,
) -> list[str] | None:
    """Resolve --scope names/IDs to location IDs. Returns None for all."""
    if not scope:
        return None

    # Fetch all locations
    params = {}
    if org_id:
        params["orgId"] = org_id
    all_locs = list(api.session.follow_pagination(
        url=f"{BASE}/locations", params=params, item_key="items",
    ))

    # Build name->id and id->id maps
    name_map = {loc["name"]: loc["id"] for loc in all_locs}
    id_set = {loc["id"] for loc in all_locs}

    requested = [s.strip() for s in scope.split(",")]
    resolved = []
    for r in requested:
        if r in id_set:
            resolved.append(r)
        elif r in name_map:
            resolved.append(name_map[r])
        else:
            console.print(f"[yellow]Warning: Location '{r}' not found, skipping[/yellow]")

    if not resolved:
        console.print("[red]No valid locations found for the given scope.[/red]")
        raise typer.Exit(1)

    return resolved


@app.command("run")
def cleanup_run(
    scope: str = typer.Option(
        None, "--scope",
        help="Comma-separated location names or IDs to limit cleanup scope.",
    ),
    all_resources: bool = typer.Option(
        False, "--all",
        help="Clean up the entire org (required if --scope not given).",
    ),
    include_users: bool = typer.Option(
        False, "--include-users",
        help="Also delete users (destructive — disabled by default).",
    ),
    include_locations: bool = typer.Option(
        False, "--include-locations",
        help="Also delete locations (destructive — disabled by default).",
    ),
    exclude_user_domains: str = typer.Option(
        None, "--exclude-user-domains",
        help="Comma-separated email domains to exclude from user deletion (e.g. 'wbx.ai,corp.com').",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be deleted without actually deleting.",
    ),
    max_concurrent: int = typer.Option(
        5, "--max-concurrent",
        help="Max parallel deletions per layer.",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Skip confirmation prompt.",
    ),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Webex Calling resources in dependency-safe order.

    Examples:
      wxcli cleanup run --scope "HQ,Branch" --dry-run
      wxcli cleanup run --scope "HQ" --include-users --force
      wxcli cleanup run --all --include-locations --force
      wxcli cleanup run --all --include-users --exclude-user-domains "wbx.ai,corp.com"
    """
    if not scope and not all_resources:
        console.print(
            "[red]Must specify --scope or --all.[/red]\n"
            "Use --dry-run to preview what would be deleted."
        )
        raise typer.Exit(1)

    api = get_api(debug=debug)
    org_id = get_org_id()

    # Resolve location scope
    console.print("[bold]Resolving scope...[/bold]")
    location_ids = _resolve_location_ids(api, scope, org_id)

    if location_ids:
        console.print(f"  Scoped to {len(location_ids)} location(s)")
    else:
        console.print("  Org-wide cleanup")

    # For location-scoped listing, we always need location IDs
    # If --all and no scope, fetch all locations for per-location listing
    if location_ids is None:
        params = {}
        if org_id:
            params["orgId"] = org_id
        all_locs = list(api.session.follow_pagination(
            url=f"{BASE}/locations", params=params, item_key="items",
        ))
        all_location_ids = [loc["id"] for loc in all_locs]
    else:
        all_location_ids = location_ids

    # Build inventory — always pass all_location_ids so location-scoped types get enumerated
    # scope_filter=False for --all mode: don't exclude resources missing locationId
    is_scoped = scope is not None
    console.print("[bold]Building inventory...[/bold]")
    inventory = build_inventory(
        api, org_id, location_ids=all_location_ids,
        include_users=include_users, include_locations=include_locations,
        scope_filter=is_scoped,
    )

    # Filter users by excluded domains
    if exclude_user_domains and "users" in inventory:
        excluded = {d.strip().lower() for d in exclude_user_domains.split(",")}
        before = len(inventory["users"])

        def _user_matches_excluded(user: dict) -> bool:
            # People API returns emails as a list
            emails = user.get("emails", [])
            if not emails:
                return False
            primary = emails[0].lower() if isinstance(emails, list) else str(emails).lower()
            domain = primary.split("@")[-1]
            return any(domain == d or domain.endswith(f".{d}") for d in excluded)

        inventory["users"] = [u for u in inventory["users"] if not _user_matches_excluded(u)]
        filtered = before - len(inventory["users"])
        if filtered:
            console.print(f"  Excluded {filtered} users matching domains: {', '.join(sorted(excluded))}")
        if not inventory["users"]:
            del inventory["users"]

    # Build number inventory for locations (needed for Layer 12)
    number_inventory: dict[str, list[str]] = {}
    if include_locations:
        console.print("[bold]Checking for phone numbers on locations...[/bold]")
        number_inventory = build_number_inventory(api, all_location_ids, org_id)
        total_nums = sum(len(v) for v in number_inventory.values())
        if total_nums:
            console.print(f"  Found {total_nums} number(s) across {len(number_inventory)} location(s)")
            # Add to inventory for dry-run display
            inventory["numbers"] = [
                {"id": num, "name": num, "locationId": loc_id}
                for loc_id, nums in number_inventory.items()
                for num in nums
            ]

    if not inventory:
        console.print("[green]Nothing to delete — org is clean.[/green]")
        return

    # Dry run
    console.print(format_dry_run(inventory))

    if dry_run:
        console.print("[yellow]Dry run complete. No resources were deleted.[/yellow]")
        return

    # Confirmation
    total = sum(len(v) for v in inventory.values())
    if not force:
        typer.confirm(
            f"\nDelete {total} resources? This cannot be undone",
            abort=True,
        )

    # Execute layer by layer
    all_results: list[DeleteResult] = []
    for i, layer_keys in enumerate(DELETION_LAYERS):
        # Check if this layer has any work
        has_work = any(k in inventory for k in layer_keys)
        if not has_work:
            continue

        # Skip users/locations/numbers layers if not included
        if "users" in layer_keys and not include_users:
            continue
        if "locations" in layer_keys and not include_locations:
            continue
        if "numbers" in layer_keys and not include_locations:
            continue

        layer_names = [RESOURCE_TYPES[k].name for k in layer_keys if k in inventory]
        console.print(f"\n[bold]Layer {i + 1}:[/bold] {', '.join(layer_names)}")

        # Special handling for numbers: delete per-location with batched body
        if "numbers" in layer_keys and number_inventory:
            for loc_id, phone_nums in number_inventory.items():
                console.print(f"  Removing {len(phone_nums)} number(s) from location {loc_id[:12]}...")
                num_results = delete_location_numbers(api, loc_id, phone_nums, org_id)
                all_results.extend(num_results)
                ok = sum(1 for r in num_results if r.success)
                fail = sum(1 for r in num_results if not r.success)
                console.print(f"    {ok} removed, {fail} failed")
            continue

        # Special handling for locations: disable calling first, then wait, then delete
        if "locations" in layer_keys and "locations" in inventory:
            loc_items = inventory["locations"]
            # Phase 1: disable calling (best-effort — may already be off)
            console.print("  Disabling calling on locations...")
            disable_results = []
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {
                    executor.submit(
                        disable_location_calling, api, item["id"], org_id,
                    ): item
                    for item in loc_items
                }
                for future in as_completed(futures):
                    disable_results.append(future.result())

            disabled_ok = [r for r in disable_results if r.success]
            console.print(f"  Disabled calling on {len(disabled_ok)}/{len(loc_items)} locations")

            # Phase 2: wait only if any disables actually succeeded
            if disabled_ok:
                console.print("  Waiting 90s for backend propagation...")
                time.sleep(90)

            # Phase 3: attempt to delete ALL locations with bounded retry.
            # Each delete_location call runs up to LOCATION_DELETE_MAX_ATTEMPTS
            # attempts with LOCATION_DELETE_RETRY_SLEEP between retries, and
            # emits its own per-attempt stdout lines (click.echo, flushed).
            total_locs = len(loc_items)
            layer_num = i + 1
            console.print(
                f"  Deleting locations (up to "
                f"{LOCATION_DELETE_MAX_ATTEMPTS} attempts × "
                f"{LOCATION_DELETE_RETRY_SLEEP}s per location)..."
            )
            console.print(
                f"  Layer {layer_num} (location): 0/{total_locs} deleted, "
                f"0 retrying, {total_locs} waiting"
            )
            deleted = 0
            failed = 0
            completed = 0
            loc_results: list[DeleteResult] = []
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {
                    executor.submit(delete_location, api, item, org_id): item
                    for item in loc_items
                }
                for future in as_completed(futures):
                    res = future.result()
                    loc_results.append(res)
                    all_results.append(res)
                    completed += 1
                    if res.success:
                        deleted += 1
                    else:
                        failed += 1
                    # The remaining in-flight futures are the ones still
                    # looping through retry attempts; the rest are "waiting"
                    # in the executor queue (only meaningful when
                    # max_concurrent < total_locs).
                    in_flight = min(
                        max_concurrent, total_locs - completed,
                    )
                    waiting = max(0, total_locs - completed - in_flight)
                    console.print(
                        f"  Layer {layer_num} (location): "
                        f"{deleted}/{total_locs} deleted, "
                        f"{in_flight} retrying, {waiting} waiting"
                    )
            console.print(f"  Done: {deleted} deleted, {failed} failed")
            continue

        results = execute_layer(api, layer_keys, inventory, org_id, max_concurrent)

        successes = sum(1 for r in results if r.success)
        failures = sum(1 for r in results if not r.success)
        console.print(f"  Done: {successes} deleted, {failures} failed")

    # Final summary
    console.print(format_results_summary(all_results))


def format_results_summary(results: list[DeleteResult]) -> str:
    """Format a summary of deletion results."""
    successes = [r for r in results if r.success]
    real_failures = [r for r in results if not r.success and not r.ccp_blocked]
    ccp_blocked = [r for r in results if r.ccp_blocked]
    ccp_blocked_locations = [
        r for r in ccp_blocked if r.resource_type == "Locations"
    ]

    lines = ["", "=== Cleanup Results ===", ""]
    lines.append(f"  Deleted:  {len(successes)}")
    lines.append(f"  Failed:   {len(real_failures)}")
    if ccp_blocked:
        lines.append(f"  CCP-blocked: {len(ccp_blocked)}")

    if real_failures:
        lines.append("")
        lines.append("  Failures:")
        for f in real_failures:
            lines.append(f"    - {f.resource_type} {f.resource_name} ({f.resource_id}): {f.error}")

    if ccp_blocked_locations:
        lines.append("")
        lines.append(
            f"  NOTE: {len(ccp_blocked_locations)} location(s) blocked by "
            f"CCP backend — retry in a few hours:"
        )
        for r in ccp_blocked_locations:
            lines.append(f"    - {r.resource_name} ({r.resource_id})")
        lines.append(
            "  Re-run `wxcli cleanup run` later; the command is idempotent."
        )

    lines.append("")
    return "\n".join(lines)
