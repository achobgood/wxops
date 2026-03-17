---
name: wxc-calling-debug
description: |
  Debug a failing Webex Calling API call or configuration. Use when an API
  returns an error, a configuration doesn't apply, a resource is missing,
  or the SDK behaves unexpectedly. Walks through systematic diagnosis.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [symptom-or-error-message]
---

# Webex Calling Debug Workflow

## Step 1: Identify the symptom

Ask the user: **What happened?** Map their answer to one of these categories:

| Category | User says something like... |
|----------|-----------------------------|
| HTTP error from API | "Got a 401/403/404/409", "API returned an error", "RestError" |
| Method returns None | "Got None back", "No return value", "Update didn't return anything" |
| Missing data on object | "location_id is None", "calling_data fields are empty", "no phone number" |
| Resource not found | "Can't find the queue/user/location", "404 on a resource I just created" |
| Permission denied | "403 Forbidden", "insufficient scopes", "not authorized" |
| Rate limited | "429 Too Many Requests", "script is getting throttled" |
| SDK exception | "RestError", "AsRestError", "ValueError on init" |
| Configuration didn't apply | "Changed the setting but nothing happened", "Update succeeded but value is the same" |
| Bulk operation failures | "Some users failed", "partial failures in gather", "exceptions in batch" |
| Async/timeout issue | "Script hangs", "aiohttp error", "session closed" |

## Step 2: Check the obvious first

These are the most common root causes. Check them FIRST before doing anything else:

### 2a. Is the token valid and not expired?

```python
# Quick token check
from wxc_sdk import WebexSimpleApi

try:
    api = WebexSimpleApi()
    me = api.people.me()
    print(f'Token valid. Authenticated as {me.display_name}')
except Exception as e:
    print(f'Token problem: {e}')
```

Token lifetimes:
- **Personal access token**: 12 hours (cannot be refreshed)
- **OAuth integration**: 14 days access / 90 days refresh
- **Service app**: access token via refresh (check `tokens.remaining`)
- **Bot token**: does not expire

If `WEBEX_ACCESS_TOKEN` is not set and no token is passed, the SDK raises:
```
ValueError: if no access token is passed, then a valid access token has to be present in
WEBEX_ACCESS_TOKEN environment variable
```

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

### 2c. Is `calling_data=True` being passed?

If `location_id`, phone numbers, or calling-specific fields are `None` on a `Person` object, the most likely cause is that `calling_data=True` was not passed:

```python
# WRONG -- calling fields will be None
users = list(api.people.list())

# RIGHT -- calling fields populated
users = list(api.people.list(calling_data=True))
```

This also applies to `api.people.details()`:
```python
person = api.people.details(person_id=pid, calling_data=True)
```

## Step 3: Check the specific error

### Enable debug logging

If the error message is unclear, enable SDK debug logging to see full request/response details:

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

### Read RestError details

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

## Step 4: Match symptom to cause and fix

### HTTP Error Codes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| **401 Unauthorized** | Token expired or invalid | Personal token: generate new one at developer.webex.com. OAuth/service app: call `integration.refresh(tokens=tokens)`. Check `tokens.remaining`. |
| **401 immediately after refresh** | Refresh token also expired (>90 days) | Full re-authorization required -- run OAuth flow again or regenerate service app credentials |
| **403 Forbidden** | Token lacks required scope | Check scope table above. For admin endpoints, verify user is a full org admin. For service apps, verify org admin has authorized the app. |
| **404 Not Found** | Resource ID is wrong, resource doesn't exist, or wrong org | Verify the resource ID. List resources first to confirm it exists. Check you're authenticating against the correct org. |
| **409 Conflict** | Duplicate resource (name, extension, phone number) | Check for existing resources with the same name/extension/number. Use `list()` to find conflicts. |
| **429 Too Many Requests** | Rate limited | SDK auto-retries when `retry_429=True` (default). For bulk work, lower `concurrent_requests` or use async with semaphore. |
| **400 Bad Request** | Invalid parameters, wrong data types, missing required fields | Check required fields in the API reference. Verify enum values. Check that IDs are the correct type (Webex base64 ID, not UUID). |
| **502/503 Service Error** | Webex platform issue | Retry after a delay. Check [status.webex.com](https://status.webex.com) for outages. |

### SDK Behavior Issues

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

### Resource/Configuration Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Location not showing as calling-enabled | Location not enabled for Webex Calling | Use `api.telephony.location.enable()` to enable calling on the location |
| Phone number assignment fails | Number not in location inventory | Add number to location first via `api.telephony.location.number.add()` |
| User shows no calling license | License not assigned | Assign via `api.licenses.assign_licenses_to_users()`. See provisioning.md. |
| Feature creation fails with location error | Location doesn't exist or wrong `location_id` | Verify with `list(api.locations.list())` -- confirm the ID matches |
| Hunt group / call queue agent not receiving calls | Agent not assigned to the feature, or not joined | Check agent list via `details()`. Verify `agent.join_enabled` is `True`. |
| Async job timeout | Bulk provisioning job still processing | Check job status via `api.telephony.jobs`. Jobs can take minutes for large orgs. |
| XSI connection fails | XSI not enabled or wrong endpoint | Verify `spark:xsi` scope. Check with Webex TAC if XSI is provisioned for the org. |
| Setting update succeeded but value unchanged | Some settings require specific preconditions | Check if the feature requires a license, an enabled location, or a specific calling plan. Read back the resource to confirm. |
| Extension conflict | Another user/feature already has the extension in that location | List all extensions in the location and pick an unused one |

### Async-Specific Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `RuntimeError: Event loop is closed` | Calling `asyncio.run()` in an already-running loop (Jupyter, etc.) | Use `await main()` directly, or use `nest_asyncio` |
| `aiohttp.ClientError` / session closed | Session used after `async with` block exited | Keep all API calls inside the `async with AsWebexSimpleApi() as api:` block |
| Partial failures in `asyncio.gather` | Some calls failed, rest succeeded | Use `return_exceptions=True` and check each result: `isinstance(result, Exception)` |
| Slow bulk operations | `concurrent_requests` too low (default: 10) | Increase to 40-100 for bulk work: `AsWebexSimpleApi(concurrent_requests=40)` |

## Step 5: Test with a targeted API call

Isolate the issue by making a minimal API call that tests the specific failure:

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.rest import RestError

api = WebexSimpleApi()

# Test 1: Basic auth -- does the token work at all?
try:
    me = api.people.me()
    print(f'Auth OK: {me.display_name}')
except RestError as e:
    print(f'Auth failed: {e.response.status_code} - {e.description}')

# Test 2: Can you read telephony config?
try:
    locations = list(api.locations.list())
    print(f'Locations: {len(locations)}')
except RestError as e:
    print(f'Locations failed: {e.response.status_code} - {e.description}')

# Test 3: Can you read calling-specific data?
try:
    users = list(api.people.list(calling_data=True))
    calling_users = [u for u in users if u.location_id]
    print(f'Calling users: {len(calling_users)}')
except RestError as e:
    print(f'Calling data failed: {e.response.status_code} - {e.description}')
```

If Test 1 fails: token issue (Step 2a).
If Test 1 passes but Test 2 fails: scope issue (Step 2b).
If Tests 1-2 pass but Test 3 fails: calling license or org issue.

For a specific failing resource, test it directly:

```python
# If a queue/HG/AA operation fails, verify the resource exists
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
```

## Step 6: Apply fix and verify

After identifying and applying the fix:

1. **Re-run the failing operation** -- confirm the error is gone
2. **Read back the resource** -- use `details()` to verify the change actually applied (don't trust a `None` return from `configure()`/`update()`)
3. **Check for downstream effects** -- if you changed a location, verify users in that location still work. If you changed a queue, verify agents are still assigned.

If the fix didn't work, return to Step 4 and check the next most likely cause.

---

## Quick Reference: Rate Limit Handling

The SDK handles 429 automatically when `retry_429=True` (default). For custom handling:

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
