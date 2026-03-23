# Partner Multi-Org Support (orgId Injection)

**Date:** 2026-03-23
**Status:** Draft
**Risk level:** Medium — touches the generator pipeline, config layer, and agent auth flow. Potentially breaking if orgId is sent to endpoints that reject unknown params.

---

## Problem

Partner/VAR/MSP administrators hold tokens with access to multiple customer orgs. The Webex API requires `orgId` as a query parameter on most endpoints to target a specific customer org. Without it, requests default to the token owner's org (the partner org) — which is rarely the intended target.

The wxcli generator currently strips `orgId` from all generated commands via a global `omit_query_params: ["orgId"]` setting. This means partner tokens cannot target customer orgs through the CLI at all — making wxcli unusable for the partner use case.

**Undocumented requirement:** When a token has access to more than one org, `orgId` is required — the API does not reliably default to a useful org.

## Scope

**In scope:**
- Config layer: store org_id and org_name per profile
- Detection: identify multi-org tokens at configure time
- Selection: show org list, let partner pick
- Generator: auto-inject orgId from config on endpoints that accept it (804/1,282 endpoints across 4 specs)
- Hand-coded commands: manually add org_id passthrough (4 files)
- CLI commands: `wxcli switch-org`, `wxcli clear-org`
- Agent: blocking org confirmation at session start
- Verification: automated spec-to-code audit test
- `wxcli whoami`: display target org when set

**Out of scope:**
- Multiple profiles (e.g., named profiles for different partners/customers)
- OAuth refresh token flows for partner tokens
- Per-command `--org-id` override flag

---

## Design

### 1. Config Layer

**File:** `src/wxcli/config.py`

Add `get_org_id()` and `get_org_name()` functions. The config JSON shape expands:

```json
{
  "profiles": {
    "default": {
      "token": "...",
      "expires_at": "...",
      "org_id": "Y2lz...",
      "org_name": "Acme Corp"
    }
  }
}
```

Both `org_id` and `org_name` are optional. Absent means single-org mode — no orgId injection. We store `org_name` alongside `org_id` so `whoami` and the agent can display it without an extra API call each time.

New functions:

```python
def get_org_id(path=DEFAULT_CONFIG_PATH) -> str | None:
    config = load_config(path)
    profile = config.get("profiles", {}).get("default", {})
    return profile.get("org_id")

def get_org_name(path=DEFAULT_CONFIG_PATH) -> str | None:
    config = load_config(path)
    profile = config.get("profiles", {}).get("default", {})
    return profile.get("org_name")

def save_org(org_id: str | None, org_name: str | None, path=DEFAULT_CONFIG_PATH) -> None:
    config = load_config(path)
    profile = config.setdefault("profiles", {}).setdefault("default", {})
    if org_id:
        profile["org_id"] = org_id
        profile["org_name"] = org_name
    else:
        profile.pop("org_id", None)
        profile.pop("org_name", None)
    save_config(config, path)
```

### 2. Multi-Org Detection and Selection

**File:** `src/wxcli/commands/configure.py`

After token validation (the existing `api.people.me()` call), add a detection step:

1. Call `GET /v1/organizations` using `api.session.rest_get()`
2. If the response contains **more than one org**, the token has multi-org access
3. Display a numbered list of orgs (display name + orgId) and prompt the user to select one
4. If **exactly one org**, skip — single-org mode, no orgId stored
5. Save the selected `org_id` and `org_name` to config

Example flow for a partner:

```
Validating token...
Authenticated: Jane Partner (jane@partner.example.com)

Multiple organizations detected:

  1. Partner Org Inc          (Y2lz...ABC)
  2. Acme Corp                (Y2lz...DEF)
  3. Globex Industries        (Y2lz...GHI)

Select target org [1-3]: 2

Target org set: Acme Corp (Y2lz...DEF)
Token saved to ~/.wxcli/config.json
```

For single-org admins, the output is unchanged — they see the existing `Authenticated: ...` message and nothing more.

**Edge case:** If `GET /v1/organizations` fails (insufficient scope, etc.), warn and skip — the partner can still use `wxcli switch-org` later to set the orgId manually.

### 3. `wxcli switch-org` Command

**File:** `src/wxcli/commands/switch_org.py` (new, hand-coded)

Standalone command that re-enumerates orgs and lets the partner pick a different one without re-entering their token.

Behavior:
1. Read token from config
2. Call `GET /v1/organizations`
3. If single org: print "Single-org token — no org switching needed" and exit
4. If multi-org: show numbered list, prompt for selection, save to config
5. Also accept `wxcli switch-org <orgId>` as a direct argument to skip the interactive prompt (useful for scripting)

### 4. `wxcli clear-org` Command

**File:** `src/wxcli/commands/clear_org.py` (new, hand-coded)

Removes `org_id` and `org_name` from config, resetting to "own org" mode.

```
$ wxcli clear-org
Cleared target org. Commands will now target your own organization.
```

### 5. `wxcli whoami` Enhancement

**File:** `src/wxcli/main.py`

When `org_id` is set in config, `whoami` displays the target org:

```
User:  Jane Partner (jane@partner.example.com)
Org:   Y2lz...ABC  (Partner Org Inc — your org)
Target: Y2lz...DEF  (Acme Corp)
Token: expires in 8h 23m
```

When no `org_id` is set, output is unchanged.

### 6. Generator: Auto-Inject from Config

**Files:** `tools/generate_commands.py`, `tools/command_renderer.py`

#### 6a. Generator change

In `generate_commands.py`, replace the `omit_query_params` approach:

**Current (line 48):**
```python
omit_qp = list(overrides.get("omit_query_params", ["orgId"]))
```

**New:**
```python
omit_qp = list(overrides.get("omit_query_params", []))
auto_inject_qp = set(overrides.get("auto_inject_from_config", ["orgId"]))
```

The `orgId` param moves from "stripped entirely" to "auto-injected from config." It's still removed from the CLI flags (the user never passes `--org-id` per-command), but the generated code reads it from config and adds it to params.

The existing `keep_query_params` override for audit events is no longer needed since orgId is no longer in the omit list. Remove those overrides from `field_overrides.yaml` to keep it clean.

#### 6b. Parser change

In `tools/openapi_parser.py`, the `parse_tag()` function currently strips params listed in `omit_query_params`. Instead, params in `auto_inject_from_config` should be:
- Removed from the `Endpoint.query_params` list (so they don't become CLI options)
- Tracked in a new `Endpoint.auto_inject_params` list (so the renderer knows to generate config reads)

Add a field to the `Endpoint` dataclass in `tools/postman_parser.py`:

```python
@dataclass
class Endpoint:
    ...
    auto_inject_params: list[str] = field(default_factory=list)
```

#### 6c. Renderer change

In `command_renderer.py`, when an endpoint has `auto_inject_params`, generate the config read and param injection. The renderer needs to:

1. Add `from wxcli.config import get_org_id` to the imports (only when any endpoint in the file has orgId in auto_inject_params)
2. After `params = {}` and the existing query param building, add:

```python
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
```

This goes in `_render_list_command()`, `_render_singleton_get()`, `_render_create_command()`, `_render_update_command()`, `_render_delete_command()`, and any other render function that builds a `params` dict.

The injection is generated **only** when the endpoint's OpenAPI spec declares `orgId` as a parameter. Endpoints without it get no injection.

#### 6d. Impact

- **Calling spec:** 726 endpoints gain orgId injection
- **Admin spec:** 12 endpoints gain orgId injection
- **Device spec:** 65 endpoints gain orgId injection
- **Messaging spec:** 1 endpoint gains orgId injection
- **Total:** 804 endpoints across ~96 generated command files

### 7. Hand-Coded Command Updates

Four hand-coded files need manual updates:

| File | Current pattern | Change needed |
|------|----------------|---------------|
| `commands/locations.py` | `api.session.rest_get(url, params=params)` | Add `get_org_id()` → `params["orgId"]` (same as generated pattern) |
| `commands/users.py` | `api.people.list(**kwargs)` | Add `org_id=get_org_id()` to kwargs |
| `commands/numbers.py` | Needs inspection — likely raw HTTP | Add orgId to params if raw HTTP, or org_id kwarg if SDK |
| `commands/licenses.py` | Needs inspection — likely raw HTTP or SDK | Same as above |

Each file gets the import `from wxcli.config import get_org_id` and the appropriate injection for its call pattern.

### 8. Agent Confirmation (Blocking)

**File:** `.claude/agents/wxc-calling-builder.md`

In the "Authentication" section (step 2 of FIRST-TIME SETUP), after `wxcli whoami` succeeds, add:

> **If the output shows a "Target:" line (multi-org token with orgId set):**
> 1. Display to the user: "You are targeting **[org_name]** (`[org_id]`). All commands in this session will operate on this organization."
> 2. Ask: "Is this the correct target org? (yes/no)"
> 3. If **no**: run `wxcli switch-org` to let them pick a different org, then re-confirm
> 4. If **yes**: proceed to the interview phase
> 5. **Do not proceed until the user confirms the target org.**

> **If no "Target:" line appears:** single-org token, proceed normally.

This makes the confirmation blocking — the agent will not run any provisioning or configuration commands until the partner has confirmed which org they're targeting.

### 9. Verification Test

**File:** `tests/test_org_id_injection.py`

An automated test that ensures spec-to-code consistency:

1. Parse all 4 OpenAPI specs
2. For each endpoint, record whether `orgId` is declared as a query parameter
3. Parse all generated command `.py` files
4. For each command function, check whether it contains `get_org_id()` call
5. Compare: every endpoint with orgId in the spec should have injection in the code, and vice versa
6. Fail with a clear diff on any mismatch

This test runs as part of the normal test suite and catches drift after any regeneration or spec update.

Additionally, a simpler count-based assertion:

```python
def test_org_id_injection_count():
    """Verify the expected number of endpoints have orgId injection."""
    spec_count = count_orgid_endpoints_in_specs()
    code_count = count_orgid_injections_in_generated_code()
    assert spec_count == code_count, (
        f"Spec declares {spec_count} endpoints with orgId, "
        f"but generated code has {code_count} injections"
    )
```

### 10. Backwards Compatibility

**No breaking changes for existing single-org users:**

- Config without `org_id`/`org_name` → all behavior unchanged
- `get_org_id()` returns `None` → generated code skips the injection → identical request to today
- `wxcli configure` with a single-org token → no org prompt shown → same flow as today
- `whoami` without org_id set → same output as today
- Generated commands with no org_id in config → `params["orgId"]` line is never reached → zero behavior change

**For partner users (new behavior):**

- `wxcli configure` detects multi-org → prompts for selection → saves org_id
- All subsequent commands inject orgId → requests target the selected customer org
- `wxcli switch-org` / `wxcli clear-org` available for changing/removing target
- Agent requires confirmation before proceeding

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Endpoint rejects unknown orgId param | Low — Webex APIs generally ignore unknown query params | Medium — command fails for partner users | Only inject on endpoints that declare orgId in the spec (Approach A's core advantage) |
| `organizations list` doesn't return customer orgs for partner token | Medium — undocumented behavior | Low — partner can use `switch-org <orgId>` manually | Fallback to manual orgId entry if detection fails |
| Stale org_id in config targets wrong customer | Medium — human error | High — write operations hit wrong org | Blocking agent confirmation at session start |
| Generator regression after spec update | Low | Medium — orgId injection missing on new endpoints | Verification test catches it automatically |
| Hand-coded commands missed during update | Low — only 4 files | Medium — those commands target partner's own org | Explicit list in this spec; code review checklist |
| Config migration for existing users | None — additive fields | None | `org_id` absent = no injection = unchanged behavior |

## Files Changed

| File | Type | Change |
|------|------|--------|
| `src/wxcli/config.py` | Edit | Add `get_org_id()`, `get_org_name()`, `save_org()` |
| `src/wxcli/commands/configure.py` | Edit | Multi-org detection + org selection prompt |
| `src/wxcli/commands/switch_org.py` | New | `wxcli switch-org` command |
| `src/wxcli/commands/clear_org.py` | New | `wxcli clear-org` command |
| `src/wxcli/main.py` | Edit | Register switch-org/clear-org, enhance whoami |
| `tools/postman_parser.py` | Edit | Add `auto_inject_params` to `Endpoint` dataclass |
| `tools/openapi_parser.py` | Edit | Populate `auto_inject_params` instead of stripping orgId |
| `tools/command_renderer.py` | Edit | Generate `get_org_id()` + injection code for auto-inject params |
| `tools/generate_commands.py` | Edit | Replace `omit_query_params: ["orgId"]` with `auto_inject_from_config: ["orgId"]` |
| `tools/field_overrides.yaml` | Edit | Remove `keep_query_params: [orgId]` from audit event tags (no longer needed) |
| `src/wxcli/commands/locations.py` | Edit | Add orgId injection (raw HTTP pattern) |
| `src/wxcli/commands/users.py` | Edit | Add `org_id=get_org_id()` to SDK calls |
| `src/wxcli/commands/numbers.py` | Edit | Add orgId injection |
| `src/wxcli/commands/licenses.py` | Edit | Add orgId injection |
| `src/wxcli/commands/*.py` (generated) | Regenerate | ~96 files gain orgId injection where spec declares it |
| `.claude/agents/wxc-calling-builder.md` | Edit | Add blocking org confirmation to auth flow |
| `tests/test_org_id_injection.py` | New | Spec-to-code audit test |

## Testing Strategy

1. **Unit: verification test** — spec-to-code consistency (automated, runs in CI)
2. **Unit: config functions** — `get_org_id`/`save_org` round-trip with and without org_id
3. **Integration: configure flow** — mock `organizations list` response with 1 org (no prompt) and 3 orgs (prompt shown)
4. **Integration: generated command injection** — pick one command (e.g., `call-queue list`), mock `get_org_id()` to return a value, verify `orgId` appears in the request params
5. **Manual: live partner token** — requires a partner token to test full flow end-to-end (org enumeration, selection, command targeting). This is the only test that can't be automated without a real partner token.

## Implementation Order

1. Config layer (`config.py`)
2. Generator pipeline (`postman_parser.py` → `openapi_parser.py` → `command_renderer.py` → `generate_commands.py`)
3. Regenerate all commands
4. Verification test — run immediately after regeneration to validate
5. `configure.py` — multi-org detection + selection
6. `switch-org` + `clear-org` commands
7. `whoami` enhancement
8. Hand-coded command updates (4 files)
9. Agent confirmation update
10. Manual testing with partner token (if available)
