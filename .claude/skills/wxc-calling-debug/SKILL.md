---
name: wxc-calling-debug
description: |
  Debug a failing Webex Calling API call or configuration. Use when an API
  returns an error, a configuration doesn't apply, a resource is missing,
  or a wxcli command fails. Walks through systematic diagnosis.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [symptom-or-error-message]
---

<!-- Updated by playbook session 2026-03-18 -->
<!-- Restructured to canonical 8-step template 2026-03-19 -->

# Webex Calling Debug Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What should you check FIRST for any API failure? (Answer: Auth and scope — run `wxcli whoami` and verify token scopes. Auth/scope issues cause 80% of failures.)
2. How do you get raw HTTP details for a failing command? (Answer: Add `--debug` flag to the wxcli command — this shows the full request/response including headers, URL, and body.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Critical Rules

1. **Verify token before any writes** — always run `wxcli whoami` before attempting create/update/delete operations.
2. **Never modify without confirmation** — present the diagnostic plan (Step 5) and get user approval before executing fixes.
3. **Always check auth/scope first** — auth and scope issues cause 80% of failures. Complete Step 2 before investigating anything else.
4. **Never hand-edit generated files** — if the bug is in a generated CLI command file, fix it via `tools/field_overrides.yaml` and regenerate. See CLAUDE.md generator rules.
5. **call-controls requires user-level OAuth** — admin tokens and service-app tokens get 400 "Target user not authorized" on `/telephony/calls/*` endpoints. The user must authenticate with a personal or OAuth token for a specific calling-licensed user.
6. **my-settings requires a calling-licensed user** — all `/people/me/*` endpoints return 404 (error 4008) if the authenticated user does not have a Webex Calling license. Test with a calling user's token, not the admin token.

## Step 1: Load references

Load the reference docs relevant to the reported symptom. Do NOT load all docs — pick 1-2 based on the API area involved.

| Symptom area | Reference docs to load |
|--------------|----------------------|
| Auth / token / scope | `docs/reference/authentication.md` |
| Provisioning (users, locations, licenses) | `docs/reference/provisioning.md` |
| Call features (AA, CQ, HG, paging) | `docs/reference/call-features-major.md`, `docs/reference/call-features-additional.md` |
| Person call settings | `docs/reference/person-call-settings-*.md` (pick the relevant one: handling, media, permissions, behavior) |
| Location call settings | `docs/reference/location-calling-core.md`, `location-calling-media.md`, `location-recording-advanced.md` |
| Routing (trunks, dial plans, PSTN) | `docs/reference/call-routing.md` |
| Devices | `docs/reference/devices-core.md`, `docs/reference/devices-workspaces.md` |
| Call control (dial, hold, transfer) | `docs/reference/call-control.md` |
| Reporting / CDR | `docs/reference/reporting-analytics.md` |
| Webhooks / events | `docs/reference/webhooks-events.md` |
| Emergency services | `docs/reference/emergency-services.md` |
| SDK patterns / async | `docs/reference/wxc-sdk-patterns.md` |

Also load `docs/reference/wxc-sdk-patterns.md` if the user is working with the Python SDK directly.

## Step 2: Verify auth token and scopes

Check authentication and scope access BEFORE investigating any other cause. Auth/scope issues account for the vast majority of failures.

### 2a. Is the token valid and not expired?

```bash
# Quick token check — shows authenticated user, org, and token expiry
wxcli whoami
```

If this fails with an auth error, the token is invalid or expired. Ask the user for a new token and configure it:

```bash
echo "<TOKEN>" | wxcli configure
```

This pipes the token into `wxcli configure` and saves it to `~/.wxcli/config.json`. Do NOT use `export WEBEX_ACCESS_TOKEN=...` — environment variables do not persist across Bash tool calls in Claude Code.

Token lifetimes:
- **Personal access token**: 12 hours (cannot be refreshed)
- **OAuth integration**: 14 days access / 90 days refresh
- **Service app**: access token via refresh (check `tokens.remaining`)
- **Bot token**: does not expire

### 2b. Does the token have the right scopes?

Quick-reference -- common scopes by API area:

| API Area | Read Scope | Write Scope |
|----------|-----------|-------------|
| Telephony config (locations, numbers, queues, HGs, AAs) | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| People / users | `spark-admin:people_read` | `spark-admin:people_write` |
| Call control (dial, hold, transfer) | `spark:calls_read` | `spark:calls_write` |
| Call detail records | `spark-admin:calling_cdr_read` | -- |
| XSI operations | `spark:xsi` | `spark:xsi` |
| WebRTC calling | `spark:webrtc_calling` | -- |

If you get a **403 Forbidden**, the token almost certainly lacks the required scope. Check what scopes the token carries:
- For OAuth tokens: check the `scope` field in your cached tokens YML
- For personal tokens: they carry all scopes your account has -- if you still get 403, you may not be an org admin (required for `spark-admin:` scopes)

### 2c. Scope verification logic

When you know the failing API endpoint, use this logic to verify scope access:

1. **Identify the API area from the symptom** — map the failing endpoint to one of the rows in the scope table above.
2. **Determine read vs write** — `GET`/`LIST` operations need the read scope; `POST`/`PUT`/`PATCH`/`DELETE` need the write scope.
3. **Test scope access** — run a minimal read command for that API area to confirm the scope works:
   ```bash
   # Test telephony_config scope
   wxcli locations list
   # Test people scope
   wxcli users list
   # Test calls scope (requires user-level OAuth — see special cases below)
   wxcli call-controls list
   ```
4. **Diagnose 403s** — if the test command returns 403:
   - Personal token: user may not be a full org admin (required for `spark-admin:` scopes)
   - Service app: org admin must authorize the app in Control Hub
   - OAuth integration: the requested scopes were not included in the authorization URL
   - Bot token: bots cannot access admin-scoped endpoints (`spark-admin:*`)

**Special cases:**

- **call-controls (`/telephony/calls/*`)** — requires **user-level OAuth**, not admin tokens. Admin tokens and service-app tokens get HTTP 400 "Target user not authorized". The authenticated user must be a specific calling-licensed person.
- **my-settings (`/people/me/*`)** — requires the authenticated user to have a **Webex Calling license**. Returns 404 (error 4008) otherwise. Test with a calling user's token, not an admin-only token.
- **XSI operations** — require `spark:xsi` scope AND XSI must be provisioned for the org. If scope is present but calls fail, check with Webex TAC.
- **CDR (`/telephony/callHistory`)** — requires `spark-admin:calling_cdr_read`. This is a separate scope from `telephony_config_read`.

### 2d. Is calling data included?

wxcli handles this automatically -- all user-related commands that need calling data (location_id, phone numbers, calling-specific fields) include it in the API request. You do not need to pass a `calling_data` flag.

If you are using the Python SDK directly (outside wxcli), you must pass `calling_data=True` to `api.people.list()` and `api.people.details()`. See the Advanced SDK Debugging section in Step 6.

## Step 3: Identify the symptom

Ask the user: **What happened?** Map their answer to one of these categories:

| Category | User says something like... |
|----------|-----------------------------|
| HTTP error from API | "Got a 401/403/404/409", "API returned an error", "RestError" |
| CLI command failed | "wxcli returned an error", "command exited with non-zero", "got an error message" |
| Method returns None | "Got None back", "No return value", "Update didn't return anything" |
| Missing data on object | "location_id is None", "calling_data fields are empty", "no phone number" |
| Resource not found | "Can't find the queue/user/location", "404 on a resource I just created" |
| Permission denied | "403 Forbidden", "insufficient scopes", "not authorized" |
| Rate limited | "429 Too Many Requests", "script is getting throttled" |
| SDK exception | "RestError", "AsRestError", "ValueError on init" |
| Configuration didn't apply | "Changed the setting but nothing happened", "Update succeeded but value is the same" |
| Bulk operation failures | "Some users failed", "partial failures in gather", "exceptions in batch" |
| Async/timeout issue | "Script hangs", "aiohttp error", "session closed" |

## Step 4: Check prerequisites

### 4a. Reproduce the failure

Re-run the failing command with `--debug` to capture the full HTTP request/response:

```bash
# Add --debug to the exact command that failed
wxcli <failing-command> --debug
```

The `--debug` flag shows:
- Full request URL, method, and headers
- Request body (for POST/PUT/PATCH)
- Response status code and body
- Tracking ID (for Webex TAC escalation)

### 4b. Verify the resource chain

Many failures happen because a prerequisite resource is missing or misconfigured. Walk up the dependency chain:

```bash
# Does the location exist and is it calling-enabled?
wxcli locations list

# Does the user exist and have a calling license?
wxcli users list --output json | head -20

# Does the parent resource exist? (e.g., for a queue agent, does the queue exist?)
wxcli call-queue show LOCATION_ID QUEUE_ID --output json
```

### 4c. Check known gotchas

Cross-reference the symptom against these common gotchas:

- **Error code 25008**: Missing required field — check which parameters the command requires
- **HTTP 400 with details**: The error body usually includes a `description` explaining what's wrong
- **Tracking ID**: Included in error output — save this for TAC escalation
- **Extension conflict**: Another user/feature already has the extension in that location
- **Number not in location**: Phone number assignment fails if the number isn't in the location's inventory
- **Calling license missing**: User shows no calling features if license isn't assigned
- **Location not calling-enabled**: Features fail if location hasn't been enabled for Webex Calling

Also check the loaded reference doc's Gotchas section (if it has one) for API-area-specific issues.

## Step 5: Build and present diagnostic plan -- [SHOW BEFORE EXECUTING]

Before running any fix commands, present the user with:

1. **Root cause hypothesis** — what you believe is causing the failure and why
2. **Evidence** — the specific error message, HTTP status, or missing data that supports the hypothesis
3. **Proposed fix** — the exact commands you plan to run to resolve the issue
4. **Verification plan** — how you will confirm the fix worked
5. **Risk assessment** — whether the fix modifies any existing resources (creates, updates, or deletes)

Format as a brief numbered plan. Wait for user confirmation before proceeding to Step 6.

## Step 6: Execute diagnostic commands and apply fix

### 6a. Match symptom to cause and fix

#### HTTP Error Codes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| **401 Unauthorized** | Token expired or invalid | Run `wxcli configure` to set a new token. For personal tokens: generate new one at developer.webex.com. |
| **401 immediately after refresh** | Refresh token also expired (>90 days) | Full re-authorization required -- run OAuth flow again or regenerate service app credentials |
| **403 Forbidden** | Token lacks required scope | Check scope table in Step 2b. For admin endpoints, verify user is a full org admin. For service apps, verify org admin has authorized the app. |
| **404 Not Found** | Resource ID is wrong, resource doesn't exist, or wrong org | Verify the resource ID. List resources first to confirm it exists. Check you're authenticating against the correct org. |
| **409 Conflict** | Duplicate resource (name, extension, phone number) | Check for existing resources with the same name/extension/number. Use the corresponding `list` command to find conflicts. |
| **429 Too Many Requests** | Rate limited | SDK auto-retries when `retry_429=True` (default). For bulk work, lower `concurrent_requests` or use async with semaphore. |
| **400 Bad Request** | Invalid parameters, wrong data types, missing required fields | Run the command with `--debug` to see the full error body. Error code 25008 means a required field is missing. Check required fields in the API reference. Verify enum values. Check that IDs are the correct type (Webex base64 ID, not UUID). |
| **400 "Target user not authorized"** | Using admin/service-app token on call-controls endpoint | call-controls requires user-level OAuth. See Critical Rules #5. |
| **404 error 4008 on /people/me/** | Authenticated user lacks Webex Calling license | my-settings endpoints require a calling-licensed user. See Critical Rules #6. |
| **502/503 Service Error** | Webex platform issue | Retry after a delay. Check [status.webex.com](https://status.webex.com) for outages. |

#### CLI Debugging

```bash
# Add --debug flag to any wxcli command for verbose HTTP output
wxcli locations list --debug

# Debug a failing write operation — shows full request/response
wxcli auto-attendant create LOC_ID --name "Test" --extension 9999 --business-schedule "Default" --debug

# Check for errors — wxcli shows HTTP status and error message
wxcli call-queue show LOCATION_ID QUEUE_ID --output json --debug
```

#### SDK Behavior Issues (for Python SDK / agent fallback)

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `configure()` / `update()` returns `None` | This is **normal** -- many update/delete methods return `None` on success | Not a bug. Read back the resource with `details()` to verify the change applied. |
| `calling_data` fields are `None` on Person | Didn't pass `calling_data=True` | Re-fetch: `api.people.list(calling_data=True)` or `api.people.details(id, calling_data=True)` |
| `list()` result missing agents/details | List endpoints return minimal data | Call `details(location_id=..., queue_id=...)` to get the full object including agents, alternate numbers, etc. |
| `ValueError` on `WebexSimpleApi()` | No token in argument or `WEBEX_ACCESS_TOKEN` env var | Set `WEBEX_ACCESS_TOKEN` or pass `tokens=` argument |
| `SafeEnum` warning in logs | API returned an enum value the SDK doesn't know yet | Usually harmless -- SDK auto-adds the new value. Upgrade wxc_sdk if it causes issues. |
| Import error for `Agent` | Wrong import path for the feature type | Hunt groups/call queues: `from wxc_sdk.telephony.hg_and_cq import Agent`. Call park/pickup: `from wxc_sdk.common import PersonPlaceAgent`. Paging: `from wxc_sdk.telephony.paging import PagingAgent`. |
| Import error for `Schedule` | Wrong import path | `from wxc_sdk.common.schedules import Schedule, Event, ScheduleType` -- NOT from `wxc_sdk.telephony.schedules` |
| `PagingApi.update()` wrong parameter order | Model comes before ID in signature | Always use keyword args: `api.telephony.paging.update(location_id=loc, update=paging_obj, paging_id=pg_id)` |
| Generic `.delete()` accepts any ID silently | Used inherited method instead of named delete | Use named methods: `delete_callpark()`, `delete_pickup()`, `delete_paging()`, `delete_huntgroup()`, `delete_queue()`, `delete_auto_attendant()`, `delete_schedule()` |

#### Resource/Configuration Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Location not showing as calling-enabled | Location not enabled for Webex Calling | Enable calling on the location via `wxcli location-settings` or SDK |
| Phone number assignment fails | Number not in location inventory | Add number to location first. Check available numbers: `wxcli numbers list` |
| User shows no calling license | License not assigned | Check licenses: `wxcli licenses list`. Assign via SDK or Control Hub. See provisioning.md. |
| Feature creation fails with location error | Location doesn't exist or wrong `location_id` | Verify with `wxcli locations list` -- confirm the ID matches |
| Hunt group / call queue agent not receiving calls | Agent not assigned to the feature, or not joined | Check agent list: `wxcli call-queue show LOCATION_ID QUEUE_ID --output json`. Verify agent `joinEnabled` is `true`. |
| Async job timeout | Bulk provisioning job still processing | Check job status via SDK `api.telephony.jobs`. Jobs can take minutes for large orgs. |
| XSI connection fails | XSI not enabled or wrong endpoint | Verify `spark:xsi` scope. Check with Webex TAC if XSI is provisioned for the org. |
| Setting update succeeded but value unchanged | Some settings require specific preconditions | Check if the feature requires a license, an enabled location, or a specific calling plan. Read back the resource to confirm. |
| Extension conflict | Another user/feature already has the extension in that location | List all extensions in the location and pick an unused one |

#### Async-Specific Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `RuntimeError: Event loop is closed` | Calling `asyncio.run()` in an already-running loop (Jupyter, etc.) | Use `await main()` directly, or use `nest_asyncio` |
| `aiohttp.ClientError` / session closed | Session used after `async with` block exited | Keep all API calls inside the `async with AsWebexSimpleApi() as api:` block |
| Partial failures in `asyncio.gather` | Some calls failed, rest succeeded | Use `return_exceptions=True` and check each result: `isinstance(result, Exception)` |
| Slow bulk operations | `concurrent_requests` too low (default: 10) | Increase to 40-100 for bulk work: `AsWebexSimpleApi(concurrent_requests=40)` |

### 6b. Test with targeted CLI commands

Isolate the issue by running minimal commands that test the specific failure:

```bash
# Test 1: Basic auth — does the token work at all?
wxcli whoami

# Test 2: Can you read telephony config?
wxcli locations list

# Test 3: Can you read calling-specific user data?
wxcli users list --output json | head -20

# Test 4: Test a specific resource directly
wxcli call-queue show LOCATION_ID QUEUE_ID --output json
```

If Test 1 fails: token issue (Step 2a).
If Test 1 passes but Test 2 fails: scope issue (Step 2b/2c).
If Tests 1-2 pass but Test 3 fails: calling license or org issue.

For a specific failing resource, test it directly with `--debug` for full HTTP details:

```bash
# If a queue/HG/AA operation fails, verify the resource exists
wxcli call-queue show LOCATION_ID QUEUE_ID --debug

# If a create operation fails, check the request body
wxcli auto-attendant create LOC_ID --name "Test" --extension 9999 --business-schedule "Default" --debug

# If a user operation fails, check the user exists and has calling
wxcli users show USER_ID --output json --debug
```

#### Fallback: Quick curl test (for Content-Type or header issues)

If the CLI sends wrong headers (e.g., wrong Content-Type for JSON Patch endpoints), use curl to test the raw request:

```bash
TOKEN=$(python3.11 -c "import json; print(json.load(open('$HOME/.wxcli/config.json'))['profiles']['default']['token'])")
curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  https://webexapis.com/v1/...
```

The config file structure is `profiles.<profile_name>.token` (not a top-level `access_token` key). Default profile is `default`.

#### Fallback: Advanced SDK Debugging (when CLI doesn't give enough detail)

If the `--debug` flag output doesn't reveal the issue, fall back to Python SDK debugging for deeper inspection.

##### Enable debug logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
# Reduce noise from urllib3
logging.getLogger('urllib3').setLevel(logging.INFO)
```

To log REST traffic to a file only:

```python
import logging

logging.basicConfig(level=logging.INFO)

rest_logger = logging.getLogger('wxc_sdk.rest')  # or 'wxc_sdk.as_rest' for async
rest_logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('rest.log', mode='w')
handler.setLevel(logging.DEBUG)
rest_logger.addHandler(handler)
```

The SDK automatically masks tokens in log output (`Bearer ***`).

##### Read RestError details

When the API returns an error, the SDK raises `RestError` (sync) or `AsRestError` (async). Extract the full details:

```python
from wxc_sdk.rest import RestError

try:
    result = api.telephony.callqueue.details(
        location_id=loc_id, queue_id=queue_id
    )
except RestError as e:
    print(f'HTTP {e.response.status_code}')
    print(f'Error code: {e.code}')
    print(f'Description: {e.description}')
    print(f'Tracking ID: {e.detail.tracking_id}')
    # Full error detail
    for err in e.detail.errors:
        print(f'  - {err.description} (code: {err.error_code})')
```

The **tracking ID** is critical for Webex TAC support escalation.

##### Targeted Python SDK test

If CLI commands don't reveal the issue, use a minimal Python script for deeper inspection:

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.rest import RestError

api = WebexSimpleApi()

try:
    queue = api.telephony.callqueue.details(
        location_id='LOCATION_ID',
        queue_id='QUEUE_ID'
    )
    print(f'Queue found: {queue.name}')
except RestError as e:
    if e.response.status_code == 404:
        print('Queue does not exist -- check the ID')
    else:
        print(f'Other error: {e.response.status_code} - {e.description}')
        print(f'Tracking ID: {e.detail.tracking_id}')
        for err in e.detail.errors:
            print(f'  - {err.description} (code: {err.error_code})')
```

## Step 7: Apply fix and verify

After identifying and applying the fix:

1. **Re-run the failing command** -- confirm the error is gone
2. **Read back the resource** -- use the corresponding `show` command with `--output json` to verify the change actually applied
3. **Check for downstream effects** -- if you changed a location, verify users in that location still work. If you changed a queue, verify agents are still assigned.

```bash
# Example: verify a fix applied
wxcli call-queue show LOCATION_ID QUEUE_ID --output json

# Example: verify users in a location after location change
wxcli users list --output json | head -40
```

If the fix didn't work, return to Step 4 and check the next most likely cause.

## Step 8: Report results

Summarize the debugging session for the user:

1. **Symptom** — what the user reported
2. **Root cause** — what was actually wrong (with evidence)
3. **Fix applied** — what commands were run to resolve it
4. **Verification** — confirmation that the fix worked (with command output)
5. **Prevention** — how to avoid this issue in the future (if applicable)

If the issue could not be resolved:
- Document what was tried and ruled out
- Provide the **Tracking ID** from the error for Webex TAC escalation
- Suggest next steps (TAC case, check status.webex.com, etc.)

If a reference doc was wrong or incomplete, update it per the Reference Doc Sync Protocol in CLAUDE.md.

---

## Quick Reference: Rate Limit Handling

wxcli and the SDK handle 429 automatically when `retry_429=True` (default). For custom handling in bulk Python scripts:

```python
from wxc_sdk import WebexSimpleApi

# Automatic retry (default behavior)
api = WebexSimpleApi(retry_429=True)

# For bulk async with controlled concurrency
from wxc_sdk.as_api import AsWebexSimpleApi

async with AsWebexSimpleApi(concurrent_requests=40) as api:
    results = await asyncio.gather(
        *[do_something(item) for item in items],
        return_exceptions=True  # don't stop on individual failures
    )
    failures = [(item, r) for item, r in zip(items, results)
                if isinstance(r, Exception)]
    print(f'{len(failures)} failures out of {len(items)}')
```

The SDK caps retry wait at 60 seconds (`RETRY_429_MAX_WAIT`). If you're still being throttled, reduce `concurrent_requests`.

---

## Quick Reference: Common Scope Requirements

| Operation | Required Scope(s) |
|-----------|--------------------|
| List/read users | `spark-admin:people_read` |
| Create/update/delete users | `spark-admin:people_write` |
| List/read locations, numbers, queues, HGs, AAs, schedules | `spark-admin:telephony_config_read` |
| Create/update/delete queues, HGs, AAs, schedules, numbers | `spark-admin:telephony_config_write` |
| Read call history | `spark:calls_read` |
| Place/control calls | `spark:calls_write` |
| Read CDR records | `spark-admin:calling_cdr_read` |
| XSI operations | `spark:xsi` |
| WebRTC calling | `spark:webrtc_calling` |
| Read licenses | `spark-admin:people_read` (licenses are part of people API) |

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
