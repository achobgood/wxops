# Dual-Call Paging Playbook

## Overview

This playbook covers the pattern for triggering two near-simultaneous calls from a single IVR menu press: one to page the store's overhead PA system with a TTS announcement, and one to transfer the caller to the department phone. Flow Designer is sequential and cannot spawn parallel calls natively — this pattern uses the WxCC Create Task API to trigger an independent outbound paging call while the inbound flow continues.

## Architecture

```
INBOUND FLOW (caller's call):
  Menu (press 1) → Set Variable (dept info) → HTTP Request (Create Task API) → Play Message ("Please hold") → Blind Transfer (dept phone)

OUTBOUND PAGING FLOW (independent call, spawned by Create Task API):
  NewPhoneContact → Bridged Transfer (paging extension) → Play Message TTS ("Attention Electronics...") → Disconnect
```

The HTTP Request fires the Create Task API asynchronously. The API returns in ~200ms, and the inbound flow continues to the Blind Transfer. The outbound paging flow runs independently on a separate call channel.

## Step 1 — Call the Create Task API from the inbound flow

> **Owner: `wxcc-platform.md` § Create Task API.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

**Endpoint:** `POST https://api.wxcc-{region}.cisco.com/v1/tasks`

**Headers:**
- `Authorization: Bearer {token}`
- `Content-Type: application/json`
- `Accept: application/json`

**Request body:**
```json
{
  "outboundType": "OUTDIAL",
  "destination": "+1XXXXXXXXXX",
  "entryPointId": "{outbound-entry-point-uuid}",
  "mediaType": "telephony",
  "origin": "+1XXXXXXXXXX",
  "attributes": {
    "dept_name": "Electronics"
  }
}
```

| Field | Description |
|---|---|
| `outboundType` | `OUTDIAL` for outbound voice calls. `EXECUTE_FLOW` creates a task but does not place an outbound call — the flow starts but stops at NewPhoneContact because no media channel exists. `CALLBACK` requires callback-specific entry point configuration. |
| `destination` | The number to dial. Accepts E.164 (`+12095551234`) and extensions (`1613`). |
| `entryPointId` | UUID of an **outbound** entry point. `OUTDIAL` requires an outbound EP. `EXECUTE_FLOW` requires an inbound EP. |
| `mediaType` | `telephony` for voice calls. |
| `origin` | Outdial ANI in E.164 format. **Must include `+` prefix** — without it the API returns "Invalid origin." Must be configured as an Outdial ANI in Control Hub. |
| `attributes` | Key-value pairs passed to the triggered flow. Use to pass department name, paging extension, or other dynamic data. |

### `outboundType` Comparison

| Type | Entry Point | Places call? | Flow runs? | Use case |
|---|---|---|---|---|
| `OUTDIAL` | Outbound EP | Yes | Yes | Agent-assisted or automated outbound calls |
| `EXECUTE_FLOW` | Inbound EP | No | Partial (stops at start) | Digital channel flows, not telephony |
| `CALLBACK` | Callback-configured EP | Yes | Yes | Web callbacks to customers |

Two choices are yours at this step:

**Which `outboundType`?** Use **`OUTDIAL`**. It is the only one that both places the call and runs a flow on it — the whole point of the pattern. `EXECUTE_FLOW` looks right and is the most common wrong answer: it creates the task record, the flow starts, then stops dead at NewPhoneContact because no media channel was ever created. Nobody is paged and nothing errors.

**What goes in `attributes`?** Whatever the paging flow needs to say. For a department page that is the department name, which the paging flow reads back as `{{dept_name}}`. Keep it to values you already have in the inbound flow — this is a fire-and-forget call, so there is no response to enrich it from.

⚠ The `origin` value **must carry the `+` prefix** or the API returns "Invalid origin". This is the most common failure on first build, and the error message does not point at the missing character.

## Step 2 — Provision the outbound entry point first

The outbound entry point needs all of these configured or the Create Task API returns a **500 Analyzer error** — and that error does not name what is missing. Build all four before the first API call.

> **Owner: `wxcc-platform.md` § OUTDIAL Entry Point Requirements.**

- [ ] **Outdial queue** created and associated with the outbound entry point
- [ ] **Team** assigned to the outdial queue
- [ ] **Flow** published and assigned to the outbound entry point
- [ ] **Outdial ANI** configured in Control Hub (Contact Center → Outdial ANI)

For the click-path to create each of these, see `wxcc-setup.md`. To create them programmatically instead, see `wxcc-provisioning-api.md`.

## Paging Flow Design

The outbound paging flow plays TTS and optionally transfers to the paging extension:

```
NewPhoneContact → Play Message (TTS: "Attention {{dept_name}}, you have a caller holding") → Disconnect
```

If the Create Task API's OUTDIAL type places the call directly to the paging extension, Play Message delivers the TTS to the connected call. If additional routing is needed, add a Bridged Transfer before the Play Message.

**TTS tips for paging:**
- Set speaking rate to 0.9 (slightly slower for noisy environments)
- Increase volume gain to +2 dB
- Repeat the message twice in the TTS text
- Use `{{dept_name}}` variable interpolation for department-specific announcements

## Known Gaps

| Issue | Status |
|---|---|
| `EXECUTE_FLOW` does not place outbound telephony calls | Confirmed — creates task record only, no media channel |
| `OUTDIAL` returns Analyzer 500 even with queue/team/flow/ANI configured | Unresolved — may require routing strategy or additional Analyzer configuration |
| Passing `attributes` to flow variables | Unverified — how attributes map to flow variables in the outbound flow needs testing |
| Play Message during Bridged Transfer | Unconfirmed — whether TTS audio transmits through a bridge to the far end |

## References

- [Create Task API](https://developer.webex.com/webex-contact-center/docs/api/v1/tasks-call-control/create-task)
- [Manage Outdial ANI](https://help.webex.com/en-us/article/nb8hvk3/Manage-Outdial-ANI)
- [Configure Voice Outbound Campaign Modes](https://help.webex.com/en-us/article/nqu2kub/Configure-Voice-Outbound-Campaign-Modes-in-Webex-Contact-Center)
