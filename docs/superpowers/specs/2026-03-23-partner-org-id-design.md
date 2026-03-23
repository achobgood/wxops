# Partner Multi-Org Support (orgId Injection)

**Date:** 2026-03-23
**Status:** Draft (v3 — post spec-review round 2)
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
- Hand-coded commands: manually add org_id passthrough (4 files, all methods)
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

**Critical prerequisite:** The current `configure.py` replaces the entire config dict on save (constructs a fresh dict at line 27-34). This must change to a **load-then-merge** pattern so that reconfiguring with a new token preserves existing `org_id`/`org_name` settings. Without this fix, running `wxcli configure` with a refreshed token would silently destroy the org targeting.

**New configure flow:**

```python
# Load existing config, merge token into it
config = load_config()
profile = config.setdefault("profiles", {}).setdefault("default", {})
profile["token"] = token
profile["expires_at"] = expires_at
# org_id and org_name preserved if already set
save_config(config)
```

After token validation (the existing `api.people.me()` call), add a detection step:

1. Call `GET /v1/organizations` using `api.session.rest_get()`
2. If the response contains **more than one org**, the token has multi-org access
3. Display a numbered list of orgs (display name + orgId) and prompt the user to select one
4. If **exactly one org**, skip — single-org mode, no orgId stored
5. Save the selected `org_id` and `org_name` to config via `save_org()`

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

**Registration pattern:** These are simple single-action commands. Register them as `@app.command()` decorators directly on the main app in `main.py`, following the same pattern as `whoami` — not as separate Typer subgroups.

**Implementation:** Add `switch_org()` and `clear_org()` functions directly in `main.py` (or in a small `commands/org_targeting.py` imported into `main.py` if preferred for organization).

Behavior:
1. Use `resolve_token()` from `auth.py` (not read directly from config) so the org enumeration uses the same token that commands will use — this prevents token/orgId source mismatch when tokens come from env vars
2. Call `GET /v1/organizations`
3. If single org: print "Single-org token — no org switching needed" and exit
4. If multi-org: show numbered list, prompt for selection, save to config via `save_org()`
5. Also accept `wxcli switch-org <orgId>` as a direct argument to skip the interactive prompt (useful for scripting)

### 4. `wxcli clear-org` Command

Registered as `@app.command("clear-org")` on the main app (same pattern as `whoami`).

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

**Files:** `tools/generate_commands.py`, `tools/command_renderer.py`, `tools/openapi_parser.py`, `tools/postman_parser.py`

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

Pass `auto_inject_qp` through to the parser alongside `omit_qp`. The `orgId` param moves from "stripped entirely" to "auto-injected from config." It's still removed from the CLI flags (the user never passes `--org-id` per-command), but the generated code reads it from config and adds it to params.

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

#### 6c. Renderer change — critical: conditional branching

The renderer has **6 render functions** mapped via the `RENDERERS` dict (line 510):

| Function | Command types |
|----------|--------------|
| `_render_list_command` | `list` |
| `_render_show_command` | `show`, `settings-get` |
| `_render_create_command` | `create` |
| `_render_update_command` | `update`, `settings-update` |
| `_render_delete_command` | `delete` |
| `_render_action_command` | `action` |

**All 6 must be updated.** The key implementation hazard is that 4 of these functions (`_render_show_command`, `_render_create_command`, `_render_update_command`, `_render_delete_command`) have **conditional branches** where `params = {}` is NOT created when there are no query params. They conditionally choose between `rest_get(url)` and `rest_get(url, params=params)` based on whether `qp_build` is non-empty.

When orgId is moved from `query_params` to `auto_inject_params`, an endpoint where orgId was the **only query param** will have an empty `qp_build`, triggering the no-params branch. The injection code would then reference an undefined `params` variable.

**The fix:** Each of the 6 render functions must check `ep.auto_inject_params` alongside `qp_build` to decide whether to create `params = {}` and pass `params=params`. Specifically:

1. When `ep.auto_inject_params` is non-empty, **always** emit `params = {}` (even if `qp_build` is empty)
2. **Always** use `params=params` in the REST call (even if there are no other query params)
3. After the existing query param building lines and before the REST call, emit the injection:

```python
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
```

A new helper function `_render_auto_inject_params(ep)` can encapsulate this logic and be called from each renderer:

```python
def _render_auto_inject_params(ep: Endpoint) -> list[str]:
    """Return lines to inject auto-inject params from config."""
    lines = []
    if "orgId" in ep.auto_inject_params:
        lines.append("    org_id = get_org_id()")
        lines.append('    if org_id is not None:')
        lines.append('        params["orgId"] = org_id')
    return lines
```

4. Add `from wxcli.config import get_org_id` to the imports via `_render_imports()` — but only when any endpoint in the file has orgId in `auto_inject_params`. The `render_command_file()` function should check this and conditionally add the import.

#### 6d. Impact

- **Calling spec:** 726 endpoints gain orgId injection
- **Admin spec:** 12 endpoints gain orgId injection
- **Device spec:** 65 endpoints gain orgId injection
- **Messaging spec:** 1 endpoint gains orgId injection
- **Total:** 804 endpoints across ~96 generated command files

**Note:** Generated files like `locations_api.py`, `numbers_api.py`, and `licenses_api.py` exist alongside the hand-coded `locations.py`, `numbers.py`, `licenses.py` as separate command groups (e.g., `wxcli locations` vs `wxcli locations-api`). The generated files will be handled automatically by the generator. The hand-coded files need manual updates (Section 7).

### 7. Hand-Coded Command Updates

Four hand-coded files need manual updates.

**Important: wxc_sdk method signatures.** Not all wxc_sdk methods accept `org_id`. Only list-type methods do. For detail/create/update/delete methods, the resource ID (person_id, license_id) already encodes the org — orgId is unnecessary and the SDK methods don't accept it. Passing `org_id` to a method that doesn't accept it would raise `TypeError`.

| File | Call pattern | Methods needing orgId | Methods already org-scoped (no change) | Change |
|------|-------------|----------------------|---------------------------------------|--------|
| `commands/users.py` | wxc_sdk methods | `list_users` (`api.people.list`) | `show_user` (person_id scoped), `create_user`, `update_user`, `delete_user` | Add `org_id=get_org_id()` to `list` call only |
| `commands/licenses.py` | wxc_sdk methods | `list_licenses` (`api.licenses.list`) | `show_license` (license_id scoped) | Add `org_id=get_org_id()` to `list` call only |
| `commands/locations.py` | Raw HTTP (`api.session.rest_get`) | All 5 commands (list, show, create, update, delete) | — | Add `params["orgId"]` injection (same pattern as generated commands) |
| `commands/numbers.py` | Raw HTTP (`api.session.rest_*`) | All 10 commands: `create`, `update`, `delete`, `validate-phone-numbers`, `list`, `list-manage-numbers`, `create-manage-numbers`, `show`, `pause-the-manage`, `resume-the-manage`, `list-errors` | — | Add `params["orgId"]` injection; for methods without existing `params` dict (create, update, delete, validate, create-manage, pause, resume), create `params = {}` and pass `params=params` |

Each file gets the import `from wxcli.config import get_org_id`.

**Note on `users.py` create:** `api.people.create()` does not accept `org_id`. For partners creating users in a customer org, the org may be inferred from the token + org context. If live testing reveals that user creation targets the wrong org without orgId, the create method can be converted to raw HTTP as a follow-up. This is an acceptable gap for v1 since user creation through the CLI is uncommon compared to list/show operations.

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

**Note:** CLI-only users (not using the agent) don't get this blocking confirmation. Their safety relies on `whoami` showing the target org and `clear-org` being available. This is an acceptable trade-off for v1 since the primary partner use case is agent-driven.

### 9. Verification Test

**File:** `tests/test_org_id_injection.py`

An automated test that ensures spec-to-code consistency:

1. Parse all 4 OpenAPI specs
2. For each endpoint, record whether `orgId` is declared as a query parameter
3. Parse all generated command `.py` files
4. For each command function, check whether it contains the exact pattern `get_org_id()` as a standalone call
5. Compare: every endpoint with orgId in the spec should have injection in the code, and vice versa
6. Fail with a clear diff on any mismatch

This test runs as part of the normal test suite and catches drift after any regeneration or spec update.

Additionally, a simpler count-based assertion (the more robust approach):

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
| Hand-coded commands missed during update | Low — only 4 files | Medium — those commands target partner's own org | Explicit method-level list in this spec; code review checklist |
| Config overwrite destroys org settings | Was high — now mitigated | High — silent loss of org targeting | configure.py changed to load-then-merge (Section 2) |
| Token/orgId source mismatch (env var token + config org) | Medium | Medium — cryptic API errors | switch-org uses `resolve_token()` from auth.py; whoami shows both token owner and target org |

## Files Changed

| File | Type | Change |
|------|------|--------|
| `src/wxcli/config.py` | Edit | Add `get_org_id()`, `get_org_name()`, `save_org()` |
| `src/wxcli/commands/configure.py` | Edit | Change to load-then-merge config; add multi-org detection + selection |
| `src/wxcli/main.py` | Edit | Add `switch-org` + `clear-org` commands (same pattern as `whoami`); enhance `whoami` |
| `tools/postman_parser.py` | Edit | Add `auto_inject_params` to `Endpoint` dataclass |
| `tools/openapi_parser.py` | Edit | Populate `auto_inject_params` instead of stripping orgId |
| `tools/command_renderer.py` | Edit | Add `_render_auto_inject_params()` helper; update all 6 render functions to handle conditional branching; conditional `get_org_id` import |
| `tools/generate_commands.py` | Edit | Replace `omit_query_params: ["orgId"]` with `auto_inject_from_config: ["orgId"]` |
| `tools/field_overrides.yaml` | Edit | Remove `keep_query_params: [orgId]` from audit event tags (no longer needed) |
| `src/wxcli/commands/locations.py` | Edit | Add orgId injection to all commands (raw HTTP pattern) |
| `src/wxcli/commands/users.py` | Edit | Add `org_id=get_org_id()` to `list` call (only SDK method that accepts it) |
| `src/wxcli/commands/numbers.py` | Edit | Add orgId injection to all 10 commands (raw HTTP pattern; create params dict where needed) |
| `src/wxcli/commands/licenses.py` | Edit | Add `org_id=get_org_id()` to `list` call (only SDK method that accepts it) |
| `src/wxcli/commands/*.py` (generated) | Regenerate | ~96 files gain orgId injection where spec declares it |
| `.claude/agents/wxc-calling-builder.md` | Edit | Add blocking org confirmation to auth flow |
| `tests/test_org_id_injection.py` | New | Spec-to-code audit test |

## Testing Strategy

1. **Unit: verification test** — spec-to-code consistency (automated, runs in CI)
2. **Unit: config functions** — `get_org_id`/`save_org` round-trip with and without org_id; verify `save_org(None, None)` removes fields
3. **Unit: configure merge** — verify that `wxcli configure` with a new token preserves existing org_id/org_name
4. **Integration: configure flow** — mock `organizations list` response with 1 org (no prompt) and 3 orgs (prompt shown)
5. **Integration: generated command injection** — pick one command (e.g., `call-queue list`), mock `get_org_id()` to return a value, verify `orgId` appears in the request params
6. **Integration: conditional branching** — test a generated command where orgId was the only query param (no other query params) to verify `params` dict is created and passed correctly
7. **Manual: live partner token** — requires a partner token to test full flow end-to-end (org enumeration, selection, command targeting). This is the only test that can't be automated without a real partner token.

## Implementation Order

1. Config layer (`config.py`)
2. Fix `configure.py` config overwrite (load-then-merge)
3. Generator pipeline (`postman_parser.py` → `openapi_parser.py` → `command_renderer.py` with all 6 render functions → `generate_commands.py`)
4. Regenerate all commands
5. Verification test — run immediately after regeneration to validate
6. `configure.py` — multi-org detection + selection
7. `switch-org` + `clear-org` commands (in `main.py`)
8. `whoami` enhancement
9. Hand-coded command updates (4 files, all methods)
10. Agent confirmation update
11. Manual testing with partner token (if available)

---

## Review History

### Spec Review (v1 → v2)

10 issues identified by spec-document-reviewer, 4 blocking:

1. **[FIXED] Renderer conditional branching** — endpoints where orgId is the only query param would crash (no `params` dict). Spec now describes the branching fix across all 6 render functions with `_render_auto_inject_params()` helper.
2. **[FIXED] Wrong function names** — `_render_singleton_get()` doesn't exist (→ `_render_show_command()`); `_render_action_command()` was missing. Spec now lists all 6 correct function names.
3. **[FIXED] Hand-coded file patterns** — `locations.py` and `numbers.py` use raw HTTP (not SDK); `users.py` and `licenses.py` use SDK methods. Spec now shows exact pattern and all methods per file.
4. **[FIXED] Config overwrite** — `configure.py` replaces entire config. Now specifies load-then-merge as a prerequisite.
5. **[FIXED] Command registration** — `switch-org`/`clear-org` registered as `@app.command()` on main app (like `whoami`), not as Typer subgroups.
6. **[FIXED] Token source mismatch** — `switch-org` now uses `resolve_token()` from `auth.py`.
7. **[FIXED] All methods need org_id** — Section 7 now lists every method per file.
8. **[NOTED] `_render_query_params` interaction** — addressed via the `_render_auto_inject_params()` helper approach.
9. **[NOTED] Verification test brittleness** — count-based assertion noted as more robust; exact pattern matching specified.
10. **[NOTED] Generated API variants exist** — `locations_api.py` etc. noted in Section 6d.

### Seven Advisors Council (v2)

Key findings:
- **Critic:** Config overwrite and token/orgId mismatch are real data-loss and silent-failure risks → both now mitigated
- **Stakeholder:** CLI-only users lack blocking confirmation → accepted for v1, documented in Section 8
- **Innovator:** Manifest-based approach could decouple injection from generation → flagged but approach A already approved
- **Advocate:** Layered safety model (confirmation + whoami + clear-org) is strong for agent use case
- **Analyst:** First time generated code has a runtime config dependency — conceptual shift worth acknowledging

### Spec Review Round 2 (v2 → v3)

2 new issues found after v2 fixes:

1. **[FIXED] wxc_sdk method signatures** — `people.details()`, `people.create()`, `people.update()`, `people.delete_person()`, and `licenses.details()` do NOT accept `org_id`. Only `people.list()` and `licenses.list()` do. Section 7 now specifies exactly which methods get org_id and which are already org-scoped via resource ID.
2. **[FIXED] numbers.py incomplete method list** — Section 7 now lists all 10 commands in `numbers.py`, noting which need a new `params` dict created.
