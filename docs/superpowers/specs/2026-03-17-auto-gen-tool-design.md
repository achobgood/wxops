# wxcli Auto-Generation Tool — Design Spec

**Date:** 2026-03-17
**Status:** Draft
**Author:** Adam Hobgood + Claude
**Depends on:** wxcli v2 (shipped, live-tested), Postman collections (downloaded)

## Problem

wxcli has 69 hand-coded commands covering ~6% of the 1,079 Webex Calling API endpoints. Hand-coding v2's 55 commands took a full session and produced 10 bugs that required iterative live-testing to find. At this rate, covering the remaining ~1,000 endpoints would take 15+ sessions.

## Solution

A Python code generator that reads the Postman collection JSON and produces complete wxcli command files. Each generated file follows the same Typer pattern as existing commands but uses raw HTTP via the SDK session instead of SDK method wrappers.

## Goals

- Generate production-quality command files from Postman spec
- Use `api.session.rest_get/post/put/delete` for HTTP — keeps auth, retry, rate-limiting from wxc_sdk
- Don't touch existing v1/v2 commands — they work
- Handle the required-fields problem via an override file maintained from live testing
- Skip beta/duplicate folders automatically
- Output should need minimal human review before working

## Non-Goals

- Replacing existing v1/v2 SDK-based commands
- Auto-detecting which fields are required (the API only tells you one-at-a-time via 25008 errors)
- Generating tests (live testing is a separate step)
- Full CLI for all 1,079 endpoints in one shot — we generate folder-by-folder as needed

## Architecture

```
tools/
  generate_commands.py    # Main generator script
  postman_parser.py       # Parse Postman JSON → normalized endpoint list
  command_renderer.py     # Render endpoints → Typer command .py files
  field_overrides.yaml    # Known required fields, defaults, skip patterns
```

### Component 1: Postman Parser (`postman_parser.py`)

Reads the Postman collection JSON and produces a normalized list of `Endpoint` objects.

**Postman JSON structure:**
The file wraps everything under a `collection` key:
```python
data = json.load(f)
folders = data["collection"]["item"]  # list of folders
```

Each folder has `name` and `item` (list of requests). Each request has:
```python
request["request"]["method"]        # "GET", "POST", "PUT", "DELETE"
request["request"]["url"]["raw"]    # "{{baseUrl}}/telephony/config/..."
request["request"]["url"]["path"]   # ["telephony", "config", "locations", ":locationId", ...]
request["request"]["url"]["variable"]  # path vars: [{"key": "locationId", "description": "..."}]
request["request"]["url"]["query"]     # query params: [{"key": "orgId", "value": "<string>", "description": "..."}]
request["request"]["body"]["raw"]      # JSON string with placeholder values
```

**Body parsing strategy:**
The Postman body is a raw JSON string with placeholder values like `"<string>"`, `"<boolean>"`, `"<number>"`. The parser:

1. Parses the raw JSON string
2. Walks top-level keys to extract field names
3. Infers types from placeholder values:
   - `"<string>"` → `string`
   - `"<boolean>"` → `bool`
   - `"<number>"` → `number`
   - A value matching a known enum pattern (ALL_CAPS_WITH_UNDERSCORES like `"ALERT_HUNT_GROUP_ONLY"`) → `string` with that value noted as an enum example
   - An object `{...}` → `object` (not flattened, handled via overrides or `--json-body`)
   - An array `[...]` → `array`
4. Values that are NOT placeholders (no angle brackets) and match enum patterns are preserved as helpful defaults/examples in the `--help` text

```python
@dataclass
class EndpointField:
    name: str           # camelCase from Postman (e.g., "businessSchedule")
    python_name: str    # kebab-case for CLI option (e.g., "business-schedule")
    field_type: str     # "string", "bool", "number", "object", "array"
    description: str    # From Postman
    required: bool      # From override file, default False
    default: Any        # From override file, or None
    enum_example: str | None  # If the Postman value was an enum-like string

@dataclass
class Endpoint:
    name: str               # Human name from Postman (e.g., "Create a Call Park")
    method: str             # GET, POST, PUT, DELETE
    url_path: str           # e.g., "telephony/config/locations/{locationId}/callParks"
    path_vars: list[str]    # e.g., ["locationId", "callParkId"]
    query_params: list[EndpointField]
    body_fields: list[EndpointField]  # Top-level only
    command_type: str       # Derived: "list", "show", "create", "update", "delete", etc.
    command_name: str       # Derived: CLI command name
    response_list_key: str | None  # For list commands: the key to unwrap (e.g., "callParks")
```

**Command type derivation logic:**

The primary rule: **if the URL ends with a path variable (`:id`), it targets a specific resource; if it ends with a collection name, it targets the collection.**

| Method | URL ends with | Type |
|--------|--------------|------|
| GET | collection name (no trailing `:id`) | `list` |
| GET | path variable (`:someId`) | `show` |
| POST | collection name | `create` |
| PUT | path variable | `update` |
| DELETE | path variable | `delete` |

Refinements applied after the primary rule:
- GET where the Postman name contains "Settings", "Service", "Forwarding", "Music", or "Night" → `settings-get`
- PUT matching the same → `settings-update`
- POST where path contains "actions" or "invoke" → `action`
- POST where Postman name contains "Selective" or "Rule" → `create-rule` (sub-resource)

**Command name derivation:**
- Primary CRUD: `list`, `show`, `create`, `update`, `delete`
- When multiple commands of the same type exist in a folder, append the sub-resource: `list-extensions`, `show-forwarding`, `create-rule`, `delete-announcement`
- The sub-resource name is derived from the last non-variable path segment

**Response list key derivation (for list commands):**
Derived from the last path segment (the collection name). Examples:
- `/callParks` → `"callParks"`
- `/autoAttendants` → `"autoAttendants"`
- `/trunks/:trunkId/usageDialPlan` → check override, fallback to first array key in response

This is stored on the Endpoint and used by the renderer to unwrap list responses.

**Folder filtering:**
Skip folders matching these patterns:
- Names starting with "Beta"
- Names containing "(2/2)" or "Phase2" or "Phase3" or "Phase4" (duplicates with different scopes)
- Explicit skip list in override file

### Component 2: Command Renderer (`command_renderer.py`)

Takes a list of `Endpoint` objects for one folder and produces a complete `.py` file.

**URL construction:**
```python
BASE_URL = "https://webexapis.com/v1"
# Path variables use Postman's :varName notation, converted to Python f-string:
# ":locationId" in path → {location_id} in f-string
url = f"{BASE_URL}/telephony/config/locations/{location_id}/callParks/{callpark_id}"
```

The `BASE_URL` is a constant at the top of each generated file. The wxc_sdk session's `rest_get` etc. accept a full URL string.

**Template for a list command:**
```python
@app.command("list")
def list_items(
    location_id: str = typer.Argument(help="Location ID"),
    name: str = typer.Option(None, "--name", help="Filter by name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List call parks for a location."""
    api = get_api(debug=debug)
    url = f"{BASE_URL}/telephony/config/locations/{location_id}/callParks"
    params = {}
    if name is not None:
        params["name"] = name
    if limit > 0:
        params["max"] = limit
    result = api.session.rest_get(url, params=params)
    items = result.get("callParks", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[...], limit=limit)
```

**Template for a create command:**
```python
@app.command("create")
def create_item(
    location_id: str = typer.Argument(help="Location ID"),
    name: str = typer.Option(..., "--name", help="Name (required)"),
    extension: str = typer.Option(None, "--extension", help="Extension number"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a call park."""
    api = get_api(debug=debug)
    url = f"{BASE_URL}/telephony/config/locations/{location_id}/callParks"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if extension is not None:
            body["extension"] = extension
        # Apply defaults from override file for nested required objects
        body.setdefault("recall", {"option": "ALERT_PARKING_USER_ONLY"})
    result = api.session.rest_post(url, json=body)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)
```

**Template for a delete command:**
```python
@app.command("delete")
def delete_item(
    location_id: str = typer.Argument(help="Location ID"),
    callpark_id: str = typer.Argument(help="Call Park ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a call park."""
    if not force:
        typer.confirm(f"Delete {callpark_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"{BASE_URL}/telephony/config/locations/{location_id}/callParks/{callpark_id}"
    api.session.rest_delete(url)
    typer.echo(f"Deleted: {callpark_id}")
```

**Output defaults:**
- `list` commands: `--output` defaults to `"table"`
- `show` and all other commands: `--output` defaults to `"json"`

**Table columns for list commands:**
The renderer selects columns from the Postman response body (if a response example exists) or falls back to the request body's top-level string/boolean fields. The override file can specify exact columns per folder:

```yaml
"Features:  Call Park":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]
```

**Pagination:**
Generated list commands are single-page by default. They pass `max` (from `--limit`) and `start` (from `--offset`, default 0) to the API. The SDK session does NOT handle pagination for raw HTTP calls. Full iteration is a future enhancement; for now, `--limit 1000` gets most use cases. The override file can mark specific list endpoints as needing iteration.

**Error handling:**
All generated commands wrap the API call in a try/except:
```python
from wxc_sdk.rest import RestError

try:
    result = api.session.rest_post(url, json=body)
except RestError as e:
    if "25008" in str(e):
        typer.echo(f"Error: Missing required field. {e}", err=True)
        typer.echo("Tip: Check field_overrides.yaml or use --json-body for full control.", err=True)
    else:
        typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(1)
```

**File upload endpoints:**
Endpoints with `body.mode = "formdata"` (e.g., Announcement Repository uploads) are skipped during generation with a comment:
```python
# SKIPPED: upload_announcement — requires multipart file upload (not auto-generated)
# Use: api.session.rest_post(url, files={"file": open(path, "rb")})
```

### Component 3: Field Overrides (`field_overrides.yaml`)

A YAML file mapping folder names to field-level overrides. This is where we encode what we learned from live testing.

```yaml
# === Known required fields and defaults (from v2 live testing) ===

"Features:  Call Queue":
  create:
    required_fields: [name, callPolicies]
    defaults:
      callPolicies:
        routingType: PRIORITY_BASED
        policy: CIRCULAR

"Features:  Call Park":
  create:
    required_fields: [name, recall]
    defaults:
      recall:
        option: ALERT_PARKING_USER_ONLY

"Features:  Auto Attendant":
  create:
    required_fields: [name, extension, businessHoursMenu, afterHoursMenu]
    defaults:
      businessHoursMenu:
        greeting: DEFAULT
        extensionEnabled: true
        keyConfigurations:
          - key: "0"
            action: EXIT
      afterHoursMenu:
        greeting: DEFAULT
        extensionEnabled: true
        keyConfigurations:
          - key: "0"
            action: EXIT

  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]
      - ["Extension", "extension"]
      - ["Enabled", "enabled"]

# === Global settings ===

skip_folders:
  - "Beta *"
  - "* (2/2)"
  - "* Phase2"
  - "* Phase3"
  - "* Phase4"
  - "Call Settings For Me *"
  - "Read the Contact Center Extensions"

# Query params to always omit (handled by SDK session or not useful for CLI)
omit_query_params:
  - orgId
```

### Component 4: Main Script (`generate_commands.py`)

CLI interface to the generator:

```bash
# Generate commands for a specific folder
python tools/generate_commands.py --folder "Call Routing" --output src/wxcli/commands/

# Generate commands for all non-skipped folders
python tools/generate_commands.py --all --output src/wxcli/commands/

# Dry run — show what would be generated without writing
python tools/generate_commands.py --folder "Call Routing" --dry-run

# List all folders with endpoint counts (for planning)
python tools/generate_commands.py --list-folders
```

**Output per folder:**
1. A `.py` command file in the output directory
2. A registration snippet printed to stdout:
   ```python
   from wxcli.commands.call_routing import app as call_routing_app
   app.add_typer(call_routing_app, name="call-routing")
   ```
3. A summary: N commands generated, M fields marked required, K defaults applied, J skipped (file uploads)

## Generated File Naming

Postman folder names → Python module names:

| Postman Folder | Module | CLI Group |
|---|---|---|
| `Call Routing` | `call_routing.py` | `call-routing` |
| `DECT Devices Settings` | `dect_devices.py` | `dect-devices` |
| `Emergency Services Settings` | `emergency_services.py` | `emergency-services` |
| `Features: Announcement Playlist` | `announcement_playlist.py` | `announcement-playlist` |

**Collision with existing v2 commands:**
For folders where we already have v2 commands (Call Park, Call Queue, Auto Attendant, etc.), the generator writes to a `_generated.py` suffix (e.g., `call_park_generated.py`). The human then diffs against the existing file and decides:
- Keep the v2 version (if it's better due to SDK model use)
- Replace with generated version
- Cherry-pick new endpoints (sub-resource commands, settings, forwarding) into the v2 file

The override file pre-populates all v2 knowledge (required fields, defaults) so generated versions start with the same fixes.

## Handling Edge Cases

1. **Multiple GETs in one folder**: Each becomes a separate command. The primary list/show use short names; extras get descriptive names derived from the Postman request name (e.g., "Get available agents" → `available-agents`).

2. **Sub-resources** (e.g., Call Park Extensions): Commands prefixed with sub-resource name: `create-extension`, `list-extensions`.

3. **Duplicate query params**: Deduplicate, keep first occurrence.

4. **orgId query param**: Always omitted — the SDK session handles org context.

5. **start/max pagination params**: Converted to `--limit` and `--offset` CLI options. Single-page only (see Pagination above).

6. **Settings endpoints** (GET/PUT pairs): Become `show-{name}` and `update-{name}`.

7. **Non-orgId query params on write endpoints**: Become CLI options. Example: `hasCxEssentials` on CQ create becomes `--has-cx-essentials`.

8. **PATCH methods**: Treated same as PUT (→ update command).

## What Gets Generated for v3

The roadmap's v3 scope maps to these Postman folders:

| Roadmap Item | Postman Folder(s) | Endpoints |
|---|---|---|
| Call Routing | Call Routing | 46 |
| Devices | Device Call Settings | 48 |
| DECT | DECT Devices Settings | 23 |
| Announcements | Features: Announcement Repository | 11 |
| Playlists | Features: Announcement Playlist | 7 |
| Location Settings (core) | Location Call Settings | 38 |
| Location Settings (handling) | Location Call Settings: Call Handling | 19 |
| Location Settings (schedules) | Location Call Settings: Schedules | 9 |
| Location Settings (voicemail) | Location Call Settings: Voicemail | 13 |

**Total: ~214 endpoints across 9 folders.**

## Success Criteria

1. Generator produces valid Python files that pass `python -c "import module"`
2. Generated `list` commands work against live API with no changes
3. Generated `create` commands work with field overrides applied for known-required fields
4. Generated files follow the exact same Typer pattern as existing commands
5. A new folder can be generated in under 5 seconds
6. Field override file is the single source of truth for required-fields knowledge
7. `--json-body` escape hatch works for any endpoint the generator can't handle cleanly

## Testing Strategy

After generation:
1. `python -c "import ..."` for each generated file (syntax check)
2. Run each `list` command against live API (they should work out of the box)
3. Run create/delete lifecycle for each group (will surface missing required fields)
4. Add discovered required fields to `field_overrides.yaml`
5. Regenerate and re-test until create works

This is the same iterative pattern we used for v2, but the generator makes each iteration seconds instead of hours.
