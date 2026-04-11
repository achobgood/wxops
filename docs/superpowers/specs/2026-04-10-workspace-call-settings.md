# Workspace Call Settings Mapper

**Date:** 2026-04-10
**Status:** Spec
**Priority:** HIGH -- common-area phones lose all call handling settings during migration

---

## Problem Statement

Common-area phones (conference rooms, lobby phones, break room phones) lose **all call settings**
during CUCM-to-Webex migration. The `WorkspaceMapper` creates `CanonicalWorkspace` objects with
correct identity data (display name, location, extension, workspace type, license tier) but
populates **zero call settings**. The planner always emits a `workspace:configure_settings`
operation, and the handler (`handle_workspace_configure_settings` in `handlers.py`) is wired up
and ready to iterate over a `call_settings` dict -- but the mapper never populates that dict.

**Result:** Every migrated workspace gets Webex platform defaults. A lobby phone that forwarded
unanswered calls to reception after 4 rings now rings forever. A conference room phone with DND
scheduled outside business hours now accepts calls at 2 AM. A break room phone with restricted
outbound dialing (local only) now has full international dialing. A common-area phone with
voicemail disabled (most are) now has voicemail enabled by default.

**Scale:** In a typical 500-user CUCM environment with 40-80 common-area phones, every one
of those phones loses its call handling configuration. The migration report shows workspace
creation as successful, masking the settings gap.

---

## CUCM Source Data

Common-area phones are CUCM `Phone` objects where `ownerUserName` is null (no associated end
user). The normalizer flags these with `is_common_area=True`. The raw phone dict preserved in
the store (as `phone:{devicename}`) contains all the settings we need:

### Per-Line Settings (from `lines` array on the phone)

| CUCM Field | Description | Webex Equivalent |
|------------|-------------|------------------|
| `callForwardAll.destination` | Forward all calls destination | Call forwarding always |
| `callForwardBusy.destination` | Forward on busy | Call forwarding busy |
| `callForwardNoAnswer.destination` | Forward on no answer | Call forwarding no answer |
| `callForwardNoAnswer.duration` | Ring timeout in seconds | numberOfRings (seconds / 6) |
| `callForwardNoCoverage.destination` | Forward on no coverage | Selective forward criteria |
| `callForwardNotRegistered.destination` | Forward when unregistered | Not available (gap) |
| `display` | Line display name | Caller ID display |
| `externalPhoneNumberMask` | External caller ID mask | Caller ID external number |

### Device-Level Settings (from phone root)

| CUCM Field | Description | Webex Equivalent |
|------------|-------------|------------------|
| `dndStatus` | DND enabled/disabled | doNotDisturb |
| `dndOption` | "Call Reject" or "Ringer Off" | doNotDisturb (enabled only, no ringer-off) |
| `callingSearchSpaceName` | Outbound dialing permissions | outgoingPermission (via CSS mapper) |
| `privacy` | Privacy/barge-in control | privacy, bargeIn |

### Voicemail Association

| CUCM Field | Description | Webex Equivalent |
|------------|-------------|------------------|
| `voiceMailProfile` on line | VM profile reference | voicemail (workspace-level) |
| `forwardToVoiceMail` on cfwdBusy/cfwdNoAnswer | VM as forward target | sendBusyCalls, sendUnansweredCalls |

Most common-area phones have voicemail **disabled** on CUCM. This is important -- Webex
defaults voicemail to enabled, so we must explicitly disable it during migration.

---

## Webex Target APIs

All workspace call settings live under `/telephony/config/workspaces/{workspaceId}/`. The
existing handler incorrectly builds URLs as `/workspaces/{id}/features/{name}` -- this is
**wrong** and must be fixed. The correct pattern is `/telephony/config/workspaces/{id}/{name}`.

### License Gating

Two license tiers gate API access:

- **Common Area (basic):** Only `doNotDisturb` and `musicOnHold` return 200. All other
  settings return 405 Method Not Allowed.
- **Professional Workspace:** Full access to all 22+ settings endpoints.

The `WorkspaceMapper` already produces a `WORKSPACE_LICENSE_TIER` decision. This spec's
mapper must check the inferred license tier and only populate settings that match the tier.

### Workspace Call Settings Endpoints (Professional License Required)

| # | Endpoint Path Suffix | Method | Purpose | Migration Priority |
|---|---------------------|--------|---------|-------------------|
| 1 | `anonymousCallReject` | GET/PUT | Block anonymous callers | LOW |
| 2 | `bargeIn` | GET/PUT | Barge-in settings (enabled, tone) | MEDIUM |
| 3 | `doNotDisturb` | GET/PUT | DND (enabled, ringSplash) | HIGH |
| 4 | `callBridge` | GET/PUT | Call bridge/warning tone | LOW |
| 5 | `pushToTalk` | GET/PUT | Push-to-talk config | LOW |
| 6 | `privacy` | GET/PUT | Privacy settings | MEDIUM |
| 7 | `voicemail` | GET/PUT | Full voicemail config | HIGH |
| 8 | `callPolicies` | GET/PUT | Call policy settings | LOW |
| 9 | `sequentialRing` | GET/PUT | Sequential ring criteria | LOW |
| 10 | `simultaneousRing` | GET/PUT | Simultaneous ring criteria | LOW |
| 11 | `selectiveReject` | GET/PUT | Selective call rejection | LOW |
| 12 | `selectiveAccept` | GET/PUT | Selective call acceptance | LOW |
| 13 | `selectiveForward` | GET/PUT | Selective call forwarding | LOW |
| 14 | `priorityAlert` | GET/PUT | Priority alert criteria | LOW |
| 15 | `musicOnHold` | GET/PUT | Music on hold | LOW |
| 16 | `callForwarding` | GET/PUT | Call forwarding rules | HIGH |
| 17 | `outgoingPermission/digitPatterns` | GET/POST | Outgoing digit pattern rules | MEDIUM |
| 18 | `features/callRecordings` | GET/PUT | Call recording settings | LOW |
| 19 | `features/intercept` | GET/PUT | Call intercept | LOW |
| 20 | `emergencyCallbackNumber` | GET/PUT | ECBN config | MEDIUM |
| 21 | `numbers` | GET | Number assignment (read-only here) | N/A |
| 22 | `devices/settings` | GET/PUT | Device telephony settings | LOW |

### Common Area License Endpoints (No Professional Required)

| # | Endpoint Path Suffix | Method | Notes |
|---|---------------------|--------|-------|
| 1 | `doNotDisturb` | GET/PUT | Available for common area AND professional |
| 2 | `musicOnHold` | GET/PUT | Available for common area AND professional |

**All other endpoints return 405 for common area licensed workspaces.**

---

## Pipeline Integration

### 1. Fix Handler URL Pattern (Bug)

The existing `handle_workspace_configure_settings` handler builds URLs as:
```python
url = _url(f"/workspaces/{ws_wid}/features/{feature_name}", ctx)
```

This is wrong. The correct URL pattern is:
```python
url = _url(f"/telephony/config/workspaces/{ws_wid}/{feature_name}", ctx)
```

This is a pre-existing bug -- even if the mapper populated `call_settings`, the handler
would send requests to the wrong URL and get 404s. Fix this in `handlers.py`.

### 2. Enhance WorkspaceMapper (New Logic)

Add call settings extraction to `WorkspaceMapper.map()`, after the workspace object is
created. The pattern mirrors `CallSettingsMapper` but operates on common-area phones
instead of user-owned phones.

**New method:** `_extract_workspace_call_settings(state, line_state, license_tier)`

Returns a `dict[str, dict]` where keys are endpoint path suffixes (e.g., `"doNotDisturb"`,
`"voicemail"`) and values are the PUT request body for that endpoint.

**Settings to extract (priority order):**

1. **doNotDisturb** -- from `state.dndStatus` + `state.dndOption`
   - `{"enabled": True/False, "ringSplashEnabled": False}`
   - Both license tiers support this.

2. **voicemail** -- from line `forwardToVoiceMail` flags + voicemail profile
   - Most common-area phones have VM disabled. Explicitly set `{"enabled": False}`.
   - If VM is enabled, map `sendBusyCalls`, `sendUnansweredCalls`, `numberOfRings`.
   - Professional license required.

3. **callForwarding** -- from line `callForwardAll`, `callForwardBusy`, `callForwardNoAnswer`
   - Map CUCM forward destinations to Webex forwarding rules.
   - Common pattern: forward unanswered to reception after N rings.
   - Professional license required.

4. **privacy** -- from `state.privacy`
   - `{"enabled": True/False}`
   - Professional license required.

5. **bargeIn** -- inferred from privacy settings
   - `{"enabled": True/False, "toneEnabled": True/False}`
   - Professional license required.

6. **emergencyCallbackNumber** -- from location ECBN or phone ECBN override
   - Professional license required.

**License tier gating logic:**
```python
if license_tier == "Workspace":
    # Only include doNotDisturb and musicOnHold
    settings = {k: v for k, v in settings.items() if k in ("doNotDisturb", "musicOnHold")}
```

### 3. Populate call_settings on CanonicalWorkspace

The `CanonicalWorkspace` model does NOT currently have a `call_settings` field. However,
`CanonicalUser` does (added for `CallSettingsMapper`). Two options:

**Option A (Recommended):** Add `call_settings: dict[str, Any] | None = None` to
`CanonicalWorkspace` in `models.py`. This mirrors `CanonicalUser` exactly.

**Option B:** Store settings in `pre_migration_state` and have the handler extract them.
This is messier and inconsistent with the user pattern.

### 4. Planner Change

The planner already generates `workspace:configure_settings` for every workspace
unconditionally (see `_expand_workspace` in `planner.py`). This is correct -- the handler
already gracefully returns `[]` if `call_settings` is empty. Once the mapper populates the
field, the handler will produce API calls.

**Optional optimization:** Make the planner conditional (like user settings):
```python
if obj.get("call_settings"):
    ops.append(_op(cid, "configure_settings", "workspace", ...))
```

This avoids no-op operations in the dependency graph. Not required for correctness.

### 5. Decision Generation

Add a new decision type or reuse existing types:

- **WORKSPACE_SETTINGS_PROFESSIONAL_REQUIRED** -- when a common-area phone has settings
  (forwarding, voicemail, privacy) that require Professional Workspace license but the
  inferred tier is basic Workspace. Severity: MEDIUM. Options: upgrade to Professional
  Workspace license, accept loss of settings, manual post-migration config.

- Reuse **FEATURE_APPROXIMATION** for settings that don't map exactly (e.g., DND "Ringer
  Off" mode has no Webex equivalent -- Webex DND always rejects the call).

---

## Handler Fix Detail

Current code in `handlers.py` lines 601-615:

```python
def handle_workspace_configure_settings(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    ws_wid = None
    for cid, wid in deps.items():
        if cid.startswith("workspace:") and wid:
            ws_wid = wid
            break
    if not ws_wid:
        return []
    settings = data.get("call_settings", {})
    calls = []
    for feature_name, feature_body in settings.items():
        url = _url(f"/workspaces/{ws_wid}/features/{feature_name}", ctx)
        calls.append(("PUT", url, feature_body))
    return calls
```

**Fix:** Change the URL pattern to:
```python
url = _url(f"/telephony/config/workspaces/{ws_wid}/{feature_name}", ctx)
```

---

## Which Settings Matter Most for Common-Area Phones

Ranked by real-world impact from CUCM migration field experience:

### Tier 1 -- Must Fix (breaks expected behavior)

1. **Voicemail: disabled** -- Most common-area phones have VM disabled. Webex defaults to
   enabled. Users will hear a voicemail greeting when calling the conference room phone
   and no one answers. This is the most frequently reported post-migration complaint for
   common-area phones.

2. **Call forwarding: CFNA to reception** -- Lobby and break room phones commonly forward
   unanswered calls to the front desk after 4-6 rings. Without this, calls ring
   indefinitely.

3. **DND: schedule-based** -- Conference room phones often have DND enabled outside
   business hours to prevent ringing during off-hours. Without this, the phone rings at
   any time.

### Tier 2 -- Should Fix (security/compliance)

4. **Outgoing call restrictions** -- Common-area phones are often restricted to internal
   calls or local calls only. Without restrictions, anyone can place international calls
   from a lobby phone.

5. **Privacy/barge-in** -- Conference room phones typically have privacy enabled to prevent
   other phones from seeing line status or barging in.

### Tier 3 -- Nice to Have

6. **Caller ID display name** -- The display name shown when the workspace phone calls
   out (e.g., "Conf Room 3A" vs the default workspace name).

7. **Music on hold** -- Custom MOH for common-area phones (rare, but exists).

8. **Emergency callback number** -- ECBN override when the workspace phone's location
   doesn't match its physical E911 address.

---

## Documentation Updates Required

1. **`docs/reference/devices-workspaces.md`** -- Add a "Gotchas" section noting:
   - Workspace settings URL pattern is `/telephony/config/workspaces/{id}/` not `/workspaces/{id}/features/`
   - Common Area license only supports DND and MOH settings
   - All other settings return 405 on basic Workspace license

2. **`src/wxcli/migration/transform/mappers/CLAUDE.md`** -- Update WorkspaceMapper entry to
   note it now populates `call_settings`.

3. **`docs/runbooks/cucm-migration/decision-guide.md`** -- Add entry for
   `WORKSPACE_SETTINGS_PROFESSIONAL_REQUIRED` decision type if a new type is added.

4. **`docs/knowledge-base/migration/kb-user-settings.md`** -- Add section on workspace
   call settings differences from user call settings (same API surface, different license
   gating, typically simpler config).

---

## Test Strategy

### Unit Tests

1. **WorkspaceMapper with DND enabled phone:**
   - Input: raw phone with `dndStatus=True`, `is_common_area=True`
   - Assert: `call_settings["doNotDisturb"]["enabled"]` is True on output workspace

2. **WorkspaceMapper with voicemail disabled:**
   - Input: raw phone with no voicemail profile, `is_common_area=True`
   - Assert: `call_settings["voicemail"]["enabled"]` is False

3. **WorkspaceMapper with call forwarding:**
   - Input: raw phone with `callForwardNoAnswer.destination=1000` on line 1
   - Assert: `call_settings` includes forwarding config with correct destination

4. **License tier gating:**
   - Input: phone with DND + forwarding, license_tier="Workspace"
   - Assert: only `doNotDisturb` in `call_settings` (forwarding stripped)

5. **License tier gating (Professional):**
   - Input: phone with DND + forwarding, license_tier="Professional Workspace"
   - Assert: both `doNotDisturb` and call forwarding in `call_settings`

6. **Handler URL fix:**
   - Input: workspace with `call_settings={"doNotDisturb": {"enabled": True}}`
   - Assert: handler returns PUT to `/telephony/config/workspaces/{id}/doNotDisturb`
   - Assert: NOT `/workspaces/{id}/features/doNotDisturb`

7. **Handler empty settings:**
   - Input: workspace with no `call_settings`
   - Assert: handler returns empty list

8. **Decision for settings requiring Professional license:**
   - Input: phone with forwarding + privacy, inferred tier=Workspace
   - Assert: WORKSPACE_SETTINGS_PROFESSIONAL_REQUIRED or FEATURE_APPROXIMATION decision

### Integration Tests

9. **Full pipeline test (normalize -> map -> analyze -> plan):**
   - Fixture: 3 common-area phones (1 basic, 1 with DND+forwarding, 1 with full settings)
   - Assert: correct `configure_settings` ops in plan with correct data payloads

10. **Planner conditional generation:**
    - Fixture: workspace with no call_settings vs workspace with call_settings
    - Assert: ops differ appropriately (if conditional planner optimization is implemented)

---

## Implementation Checklist

- [ ] Add `call_settings` field to `CanonicalWorkspace` in `models.py`
- [ ] Add `_extract_workspace_call_settings()` method to `WorkspaceMapper`
- [ ] Add license tier gating logic in the extraction method
- [ ] Fix handler URL pattern in `handle_workspace_configure_settings`
- [ ] Add decision for settings requiring Professional license upgrade
- [ ] Write unit tests for mapper extraction (5 tests)
- [ ] Write unit test for handler URL fix (1 test)
- [ ] Write integration test for full pipeline (1 test)
- [ ] Update `models.py` and mapper CLAUDE.md docs
- [ ] Update reference doc gotchas
