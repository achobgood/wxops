# wxcli — Webex Calling CLI

**Date:** 2026-03-16
**Status:** Reviewed
**Author:** Adam Hobgood + Claude

## Problem

Webex Calling has REST APIs and two Python SDKs (`wxc-sdk`, `wxcadm`), but no CLI. This forces users into either the Control Hub GUI or writing Python scripts for every operation. Claude Code can't iterate on Webex Calling configurations the way it can with AWS (where `aws connect ...` provides instant feedback loops).

## Solution

A CLI tool called `wxcli` that wraps `wxc-sdk` and exposes Webex Calling operations as terminal commands. Think `aws` CLI but for Webex Calling.

## Goals

- **v1:** Locations, users, numbers, licenses — the "day 1" provisioning operations
- **Long-term:** Full coverage of everything `wxc-sdk` supports
- **Primary users:** Adam and Claude Code (power users), with open-source polish later

## Non-Goals (v1)

- Call features (auto attendants, hunt groups, call queues) — v2
- Person/workspace call settings — v2
- Call control (dial, answer, transfer) — v2
- Real-time webhooks — v2
- Devices — v2
- Number assign/unassign — deferred to v1.1 (complex read-modify-write via SDK, risk of wiping existing numbers)
- OAuth refresh flow — v1.1
- GUI or TUI

## Architecture

### Package Structure

```
wxcli/
├── pyproject.toml              # Package config, entry point, dependencies
├── src/
│   └── wxcli/
│       ├── __init__.py
│       ├── main.py             # Top-level Typer app, entry point, --version
│       ├── auth.py             # Token resolution: env var → config file → error
│       ├── config.py           # Read/write ~/.wxcli/config.json (profiles)
│       ├── output.py           # Table/JSON formatting helpers, --limit support
│       └── commands/
│           ├── __init__.py
│           ├── configure.py    # wxcli configure
│           ├── locations.py    # wxcli locations {list,show,create,update,enable-calling,delete}
│           ├── users.py        # wxcli users {list,show,create,update,delete}
│           ├── numbers.py      # wxcli numbers {list}
│           └── licenses.py     # wxcli licenses {list,show}
```

### Dependencies

- `typer[all]` — CLI framework (built on Click, uses type hints, includes Rich for tables)
- `wxc-sdk` — Webex Calling API wrapper
- No other runtime dependencies

### Entry Point

`pyproject.toml` defines `[project.scripts] wxcli = "wxcli.main:app"` so after `pip install -e .` the `wxcli` command is available system-wide.

## Authentication

### Token Resolution Order

1. `WEBEX_ACCESS_TOKEN` environment variable (matches wxc-sdk convention)
2. `WEBEX_TOKEN` as fallback env var (common alias)
3. `~/.wxcli/config.json` — `profiles.default.token`
4. Error: `No token found. Run 'wxcli configure' or set WEBEX_ACCESS_TOKEN.`

### Config File Structure

```json
{
  "profiles": {
    "default": {
      "token": "...",
      "expires_at": "2026-03-17T04:00:00Z"
    }
  }
}
```

Structured for future multi-profile support (dev org / prod org) even though v1 only uses "default."

### `wxcli configure`

Interactive prompt: asks for token, validates it by calling `people.me()`, saves to `~/.wxcli/config.json` with `expires_at` (dev tokens expire in 12 hours). Prints org name and user email on success.

### Token Validation

Every command calls `auth.get_api()` which returns a configured `WebexSimpleApi` instance or exits with a clear error. Checks `expires_at` proactively — warns if token expires within 2 hours. Token expiry caught and surfaced as "Token expired. Run 'wxcli configure' to refresh."

**v1.1:** `wxcli configure --oauth` for full OAuth integration flow with refresh tokens (90-day lifetime). Uses `wxc-sdk`'s built-in `Integration` class.

## Commands (v1)

### Global Options

- `--output table|json` — default `table` for humans, `json` for scripting/Claude
- `--debug` — set `wxc_sdk` logger to DEBUG level (dumps full HTTP request/response)
- `--limit N` — limit list output to N rows (default 50, `--limit 0` for all)
- `--version` — print version and exit

### `wxcli whoami`

Show current authenticated user and org.

```
$ wxcli whoami
User:  Adam Hobgood (ahobgood@example.com)
Org:   Hobgood Labs (org-abc123)
Roles: Full Administrator
Token: expires in 8h 23m
```

### `wxcli locations list`

```
$ wxcli locations list
ID            NAME              ADDRESS                    CALLING
loc-abc123    Wilmington Main   123 Main St, Wilmington    Enabled
loc-def456    Raleigh Office    456 Oak Ave, Raleigh       Disabled
```

Options: `--calling-only` (filter to calling-enabled locations via `TelephonyLocationApi.list()`)

### `wxcli locations show <id>`

Full detail dump of a single location, including call settings if calling-enabled.

### `wxcli locations create`

```
$ wxcli locations create --name "Wilmington Main" \
    --timezone "America/New_York" \
    --address "123 Main St" \
    --city "Wilmington" --state "NC" --zip "28401" --country "US"
Created: loc-abc123 (Wilmington Main)
```

Required: `--name`, `--timezone`, `--address`, `--city`, `--state`, `--zip`, `--country`
Optional: `--language` (default: `en_US`, sets both `preferred_language` and `announcement_language`)

Note: `LocationsApi.create()` requires `preferred_language` and `announcement_language` as positional args. The `--language` flag sets both. Override individually with `--preferred-language` / `--announcement-language` if needed.

### `wxcli locations update <id>`

Update location fields. Only changed flags are applied.

```
$ wxcli locations update loc-abc123 --name "Wilmington HQ"
Updated: loc-abc123
```

### `wxcli locations enable-calling <id>`

Enable Webex Calling on an existing location. Separate from create because the Webex API treats these as two operations.

Implementation note: internally calls `LocationsApi.details(id)` first to get the full Location object, then passes it to `TelephonyLocationApi.enable_for_calling()`. Requires `spark-admin:telephony_config_write` scope.

### `wxcli locations delete <id>`

Delete with confirmation prompt. `--force` to skip.

### `wxcli users list`

```
$ wxcli users list --calling-enabled
ID            NAME              EMAIL                    LOCATION          EXT
user-abc123   Adam Hobgood      ahobgood@example.com     Wilmington Main   1001
user-def456   Jane Smith        jsmith@example.com       Raleigh Office    2001
```

Options: `--calling-enabled`, `--location <id>`, `--email <pattern>`, `--limit N`

### `wxcli users show <id>`

Full detail including calling data (extension, phone number, location, calling features).

### `wxcli users create`

```
$ wxcli users create --email "jsmith@example.com" \
    --first "Jane" --last "Smith" \
    --location loc-abc123 --license <calling-license-id>
Created: user-def456 (Jane Smith)
```

Required: `--email`, `--first`, `--last`
Optional: `--location`, `--license` (use `wxcli licenses list` to find calling license IDs)

Note: creating a user without `--license` creates a Webex user but does NOT enable calling. The CLI warns: "User created without calling license. Use 'wxcli licenses list' to find a calling license, then update the user."

### `wxcli users update <id>`

Update user fields (name, location, license).

### `wxcli users delete <id>`

Delete with confirmation prompt. `--force` to skip.

### `wxcli licenses list`

```
$ wxcli licenses list
ID              NAME                          TOTAL    CONSUMED
lic-abc123      Webex Calling - Professional  100      42
lic-def456      Webex Calling - Basic         50       12
lic-ghi789      Webex Meetings               100      85
```

Options: `--calling-only` (filter to calling-related licenses)

### `wxcli licenses show <id>`

Full license details including assigned users count.

### `wxcli numbers list`

```
$ wxcli numbers list --location loc-abc123
NUMBER          TYPE     ASSIGNED TO        LOCATION
+19105551234    DID      Adam Hobgood       Wilmington Main
+19105551235    DID      (unassigned)       Wilmington Main
```

Options: `--location <id>`, `--available` (unassigned only), `--limit N`

Note: `numbers assign` and `numbers unassign` are deferred to v1.1. The SDK's number assignment is a read-modify-write operation on `person_settings.numbers` that risks wiping existing numbers if done wrong. Needs careful implementation with `--dry-run` support.

## Output Formatting

### Table Mode (default)

Uses Rich tables via Typer. Clean, colored, aligned columns. Truncates long values.

### JSON Mode

`--output json` prints Pydantic model data serialized with `model_dump(by_alias=True)` for camelCase matching the Webex API schema. Pipeable to `jq`.

### Pagination

List commands default to `--limit 50`. Use `--limit 0` for all results. The SDK handles API pagination internally via generators; `--limit` controls how many results are displayed.

## Error Handling

### API Errors

```
$ wxcli locations create --name "Test"
Error: 400 Bad Request
  POST /v1/locations
  Missing required field: timezone
```

Always shows: HTTP status, method + path, error message from Webex API. No Python stack traces unless `--debug`.

### Auth Errors

```
$ wxcli locations list
Error: No token found. Run 'wxcli configure' or set WEBEX_ACCESS_TOKEN.
```

```
$ wxcli locations list
Error: 401 Unauthorized — token expired. Run 'wxcli configure' to refresh.
```

### Debug Mode

`--debug` sets the `wxc_sdk` Python logger to DEBUG level, which dumps full HTTP request/response natively. No custom debug code needed.

## Extensibility

Adding a new command group (e.g., `wxcli hunt-groups`) for full coverage:

1. Create `src/wxcli/commands/hunt_groups.py` with a Typer sub-app
2. Import and register in `main.py`: `app.add_typer(hunt_groups.app, name="hunt-groups")`
3. Done

Each command file is independent. No shared state beyond auth.

## Testing Strategy

- **Manual testing first** — we're building for us, not shipping to PyPI yet
- **Smoke tests** — a script that runs `wxcli whoami`, `wxcli locations list`, etc. and checks exit codes
- **Unit tests later** — mock the SDK responses, test output formatting

## Success Criteria

1. `wxcli configure` saves a token and validates it
2. `wxcli whoami` shows user, org, and token expiry
3. `wxcli locations list` shows locations in a readable table
4. `wxcli locations create ...` creates a location via API and prints the result
5. `wxcli licenses list` shows available licenses
6. `wxcli users list --calling-enabled` shows calling users
7. `wxcli numbers list` shows phone numbers
8. Claude Code can use `wxcli --output json` to drive Webex Calling iteratively
9. Error messages are clear enough to fix without looking up docs

## Review Notes (2026-03-16)

Issues addressed from spec review:
- **Fixed:** Env var changed to `WEBEX_ACCESS_TOKEN` to match SDK convention (with `WEBEX_TOKEN` fallback)
- **Fixed:** `locations create` now includes `--language` flag for required `preferred_language`/`announcement_language` params
- **Deferred:** `numbers assign/unassign` moved to v1.1 (complex read-modify-write, needs `--dry-run`)
- **Added:** `licenses` command group (was in v1 scope but missing from spec)
- **Added:** `locations update`, `users update`, `users delete` commands
- **Added:** `--limit` flag for list pagination
- **Added:** `--version` flag
- **Fixed:** Config file structured for future multi-profile support
- **Fixed:** `--output json` uses `model_dump(by_alias=True)` for API-compatible camelCase
- **Fixed:** `--debug` leverages SDK's built-in logging instead of custom code
- **Added:** Token expiry tracking in config + proactive warning in `whoami`
- **Noted:** `enable-calling` requires two SDK calls internally (get location object, then enable)
