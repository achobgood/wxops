"""Batch-delete Webex Calling resources in dependency-safe order."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import typer
from rich.console import Console
from wxc_sdk.rest import RestError

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
    ["locations"],                       # Layer 12: disable calling first, then delete
]


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def list_resources(
    api,
    rt: ResourceType,
    org_id: str | None,
    location_ids: list[str] | None,
) -> list[dict]:
    """List all resources of a given type, respecting scope."""
    params = {}
    if org_id:
        params["orgId"] = org_id

    if rt.location_scoped_list:
        # Must iterate per location
        if not location_ids:
            return []
        all_items = []
        for loc_id in location_ids:
            url = rt.list_url.format(location_id=loc_id)
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
    url = rt.list_url
    try:
        items = list(api.session.follow_pagination(
            url=url, params=params, item_key=rt.item_key,
        ))
    except RestError as e:
        logger.warning("Failed to list %s: %s", rt.name, e)
        return []

    # Filter by location scope if requested and items have locationId
    if location_ids and rt.supports_location_filter:
        loc_set = set(location_ids)
        items = [i for i in items if i.get("locationId") in loc_set]

    return items


def build_inventory(
    api,
    org_id: str | None,
    location_ids: list[str] | None,
    include_users: bool,
    include_locations: bool,
) -> dict[str, list[dict]]:
    """Build a full inventory of resources to delete."""
    inventory: dict[str, list[dict]] = {}

    for layer in DELETION_LAYERS:
        for key in layer:
            if key == "users" and not include_users:
                continue
            if key == "locations" and not include_locations:
                continue

            rt = RESOURCE_TYPES[key]
            items = list_resources(api, rt, org_id, location_ids)
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

    url = rt.delete_url.format(**fmt_kwargs)
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
    except (RestError, Exception) as e:
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


def delete_location(
    api,
    item: dict,
    org_id: str | None,
) -> DeleteResult:
    """Delete a location (must have calling disabled first)."""
    location_id = item.get("id", "")
    name = item.get("name", "unnamed")
    url = f"{BASE}/locations/{location_id}"
    params = {}
    if org_id:
        params["orgId"] = org_id
    try:
        api.session.rest_delete(url, params=params)
        return DeleteResult(
            resource_type="Locations",
            resource_id=location_id,
            resource_name=name,
            success=True,
        )
    except RestError as e:
        return DeleteResult(
            resource_type="Locations",
            resource_id=location_id,
            resource_name=name,
            success=False,
            error=str(e),
        )


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
      wxcli cleanup run --all --force
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
    console.print("[bold]Building inventory...[/bold]")
    inventory = build_inventory(
        api, org_id, location_ids=all_location_ids,
        include_users=include_users, include_locations=include_locations,
    )

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

        # Skip users/locations layers if not included
        if "users" in layer_keys and not include_users:
            continue
        if "locations" in layer_keys and not include_locations:
            continue

        layer_names = [RESOURCE_TYPES[k].name for k in layer_keys if k in inventory]
        console.print(f"\n[bold]Layer {i + 1}:[/bold] {', '.join(layer_names)}")

        # Special handling for locations: disable calling first, then wait, then delete
        if "locations" in layer_keys and "locations" in inventory:
            loc_items = inventory["locations"]
            # Phase 1: disable calling
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

            if disabled_ok:
                console.print("  Waiting 90s for backend propagation...")
                time.sleep(90)

            # Phase 2: delete locations
            console.print("  Deleting locations...")
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {
                    executor.submit(delete_location, api, item, org_id): item
                    for item in loc_items
                    if any(r.resource_id == item["id"] and r.success for r in disable_results)
                }
                for future in as_completed(futures):
                    all_results.append(future.result())
            continue

        results = execute_layer(api, layer_keys, inventory, org_id, max_concurrent)
        all_results.extend(results)

        successes = sum(1 for r in results if r.success)
        failures = sum(1 for r in results if not r.success)
        console.print(f"  Done: {successes} deleted, {failures} failed")

    # Final summary
    console.print(format_results_summary(all_results))


def format_results_summary(results: list[DeleteResult]) -> str:
    """Format a summary of deletion results."""
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    lines = ["", "=== Cleanup Results ===", ""]
    lines.append(f"  Deleted:  {len(successes)}")
    lines.append(f"  Failed:   {len(failures)}")

    if failures:
        lines.append("")
        lines.append("  Failures:")
        for f in failures:
            lines.append(f"    - {f.resource_type} {f.resource_name} ({f.resource_id}): {f.error}")

    lines.append("")
    return "\n".join(lines)
