# Webex Calling Paging Integration Playbook

<!-- ref-tag: webex-calling-paging-v1 -->

## ⚠ Scope — this repo owns the seam, not Webex Calling

**Webex Calling is a different product with its own toolkit.** Paging groups, the
Call Controls Dial API, device compatibility and multicast/PA hardware are
**Webex Calling** platform facts, and they are already owned — at greater depth,
including data models, required fields, character limits and raw HTTP — by:

> `docs/reference/call-features-additional.md` § Paging Groups in
> **[achobgood/wxops](https://github.com/achobgood/wxops)** (the `wxcli` toolkit)

**What this repo legitimately owns** is the *integration seam*: how a Webex
Connect flow reaches a paging group, and what breaks at that boundary. That is
sections 2, 4, 6 (the TTS limitation specifically), 8 and 9.

**Sections 1, 3, 5, 7 are a convenience mirror, not the owner.** They are kept so
a zero-experience user is not forced across repos mid-build, and they were
corrected against help.webex.com on 2026-04-17 — but where they disagree with
`wxops`, **`wxops` wins.** Do not extend them; add Webex Calling facts there.

⚠ Maintaining this mirror has already cost real errors: the April 2026 vetting
(`docs/tests/findings/webex-calling-paging-findings.md`) found **13 discrepancies,
3 of them Error-severity**, all in the mirrored half — a field that does not
exist (`Caller ID Display`), an undocumented device claim, and an auto-answer
model that was wrong in four of five cases. All are fixed; the lesson is that a
second copy of another product's docs decays silently.

---

## Overview

This playbook covers how to route outbound calls from Webex Connect to Webex Calling paging groups — the pattern for automated announcements like "Order ORD-4521 is ready for pickup" broadcast over phones or PA systems.

**Architecture:**
```
DB (order ready) → Webhook → Connect Flow → Call User (dials paging group DID via PSTN) → Webex Calling Paging Group → Auto-answer on target phones/speakers
```

---

## 1. Webex Calling Paging Groups

Paging groups provide **one-way audio broadcast** from an originator to up to 75 target phones.

### How It Works

1. Originator dials the paging group's extension or DID
2. Originator hears one short beep, then a "Paging System Ready" announcement
3. Originator speaks — audio broadcasts to all targets simultaneously
4. Target phones **auto-answer on speaker** (microphone muted, one-way)
5. When originator hangs up, page ends

### Configure in Control Hub

1. Navigate to **Services > Calling > Features** and select the **Paging Group** card
2. Click **Add New**
3. Configure:

| Field | Details |
|-------|---------|
| **Name** | Descriptive name (e.g., "Warehouse Paging") |
| **Location** | Assign to a Webex Calling location |
| **Extension** | Internal dial code (e.g., `7500`) |
| **Phone Number** | **Required for Connect integration** — assign a DID so external systems can reach it via PSTN |
| **Paging Originators** | Users/groups allowed to initiate pages |
| **Paging Targets** | Users/workspaces that receive pages (up to 75) |
| **Direct line caller ID name** | Options: **Display name** or **Other direct line caller ID name** |
| **Language** | Language for the paging announcement prompt |

### Device Compatibility

Paging auto-answer works on:
- Cisco IP Phone 6800, 7800, 8800, 8875, 9800 Series
- Analog Telephone Adapters (ATAs) 191 and 192
- Third-party SIP speakers registered as Customer Managed Devices (not listed in official compatibility docs — paging-specific compatibility is unconfirmed; see section 7)

**Does NOT work on:**
- Webex App soft client (phones only)
- Shared devices — only primary devices

---

## 2. Routing from Connect via PSTN

The viable path is: **Connect dials the paging group's DID via PSTN.**

There is **no direct SIP trunk** between Webex Connect and Webex Calling. These are separate platforms with separate voice infrastructure. Connect's outbound calls route through its own PSTN carrier network.

### Architecture

```
Connect Call User node → PSTN → Webex Calling → resolves DID → Paging Group → auto-answer on targets
```

### Requirements

1. **Paging group must have a DID assigned** — extensions are internal to Webex Calling and not reachable from external PSTN. This is the constraint that decides the whole design: no DID, no integration
2. **Connect Call User node** dials the DID in E.164 format (e.g., `+15557500`). Node fields and exit paths: `webex-connect-advanced.md` § Call User Node (Initiates the Call)
3. **From Number** must be a Connect-provisioned voice-enabled number [`webex-connect-advanced.md` § Call User Node → Required Fields]

### Connect Flow Pattern

After the Call User node answers (`onAnswer`), control enters the Voice Node Group where a Play node delivers the TTS message:

```
Start (Webhook) → HTTP Request (fetch order details) → Call User (dial paging DID)
  → onAnswer → Voice Node Group [ Play (TTS: "Order 4521 is ready") ] → End
```

The paging group receives the TTS audio and broadcasts it to all target phones.

---

## 3. Auto-Answer Behavior

Auto-answer is **built into the paging group feature** — not a per-phone setting you configure separately.

| Scenario | Behavior |
|----------|----------|
| Target phone is idle | Auto-answers on speaker, mic muted; target hears three beeps; "Incoming page message and mute notification appear on the phone screen" |
| Target phone is on a call | Depends on configurable priority level: **Top** = active call held automatically, page received; **Default** = hears mix of active call and page; **Lower** = alerted, answers page after ending active call; **Lowest** = phone ignores page |
| Target has Don't Disturb on | Page is NOT delivered |
| Target has Call Forwarding | Does NOT apply — forwarding destinations are not dialed for paging calls |
| Target has Simultaneous Ring | Does NOT apply to paging calls |

The page **cannot be declined** by the target. When the originator hangs up, the page ends on all targets.

---

## 4. Originator Enforcement — Key Unknown

**This is the single biggest question to test before building the integration.**

Paging groups have a defined list of **Originators** (users allowed to initiate pages). When a Connect flow dials the paging group's DID via PSTN, the originator is the Connect phone number, not a configured Webex Calling user.

**What needs testing:**
- Does an inbound PSTN call to a paging group DID trigger the page if the caller is not a configured originator?
- Or does Webex Calling reject the call / silently drop it?

**Workarounds if originator enforcement blocks PSTN:**
1. Add the Connect phone number as an originator (if the system accepts external numbers)
2. Use the Webex Calling Dial API (see section 6) to place the call "as" a configured originator user
3. Route through a Webex Calling Auto Attendant that transfers to the paging group extension

**Recommendation:** Test this with a real paging group before building the full integration.

---

## 5. TTS Message for Paging

Since the paging system broadcasts whatever audio it receives, the Connect flow's TTS message IS the page announcement.

### Example SSML for Order Notification

```xml
<speak>
  Attention.
  <break time="500ms"/>
  Order number <say-as interpret-as="characters">$(n3.order_number)</say-as>
  is ready for pickup.
  <break time="300ms"/>
  Customer name: $(n3.customer_name).
  <break time="500ms"/>
  Repeating. Order number <say-as interpret-as="characters">$(n3.order_number)</say-as>
  is ready for pickup.
</speak>
```

### Tips for Paging TTS

- **Repeat the message** — paging environments are noisy; say it twice
- **Use `<break>` tags** — give listeners time to focus before the key information
- **Spell out order numbers** — use `<say-as interpret-as="characters">` so "ORD-4521" reads as "O-R-D-four-five-two-one" instead of "ord four thousand five hundred twenty-one"
- **Keep it under 30 seconds** — paging messages should be brief
- **Use `<prosody rate="slow">`** for critical information to ensure clarity

---

## 6. Alternative: Webex Calling Dial API

Instead of PSTN, Connect's HTTP Request node could call the Webex Calling **Call Controls Dial API** to trigger the page programmatically.

### API Endpoint

```
POST https://webexapis.com/v1/telephony/calls/dial
```

### Body

```json
{
  "destination": "7500",
  "endpointId": "{device_id}"
}
```

Where `7500` is the paging group extension.

### Complications

This API operates in **user context** — it requires:

| Requirement | Details |
|-------------|---------|
| **Dedicated Webex Calling user** | A "service user" whose token the flow uses |
| **OAuth token** | `spark:calls_write` scope. Requires OAuth refresh token flow or service app token. |
| **User as originator** | The user must be listed as an Originator in the paging group |
| **Registered device** | The API needs an `endpointId` — the user must have a registered device |

**Important:** There is no dedicated "trigger a page" API in the Webex Calling API. The Paging Group APIs (`/v1/telephony/config/locations/{locationId}/paging`) are administrative/provisioning only — they configure paging groups but do NOT trigger a page. The Dial API is the only programmatic way to initiate a page.

**Verdict:** The PSTN path is simpler. Use the Dial API only if originator enforcement blocks PSTN calls to the paging group DID.

### Dial API Audio Limitation

The Webex Calling Dial API (`POST /v1/telephony/calls/dial`) can reach extensions — the destination field accepts simple extensions like `1613` or `7500`. However, it connects two endpoints (a user's device and the destination) without any mechanism to inject TTS or play audio into the call. The API has no `playAnnouncement` or media injection capability. If the use case requires TTS audio delivered to the paging extension (e.g., "Attention Electronics, you have a caller holding"), the Dial API alone is insufficient. See `docs/playbooks/dual-call-paging.md` for an alternative using the WxCC Create Task API with a Flow Designer flow that has Play Message TTS capability.

---

## 7. Multicast Paging / PA Systems

Webex Calling does **not natively support multicast paging**. Third-party SIP hardware bridges the gap.

### How It Works

1. Register a third-party SIP paging device as a **Customer Managed Device** in Control Hub
2. Device gets SIP credentials and registers to Webex Calling
3. Add the device's workspace to the paging group as a target
4. Paging group sends SIP INVITE to the speaker → speaker auto-answers → audio plays over loudspeaker

### Compatible Devices

| Vendor | Device | Use Case |
|--------|--------|----------|
| CyberData | IP Speakers, IP-to-Analog adapters | Overhead speakers, PA amplifier bridge |
| Algo | 8301 Paging Adapter, IP speakers | PA systems, analog amplifier bridge |
| Grandstream | SIP speakers | Direct IP speakers (paging-specific compatibility not confirmed) |

### Multicast Scaling

For more than 75 devices (paging group limit):
- One SIP-registered "master" speaker receives the page from Webex Calling
- Master re-broadcasts via **local network multicast** to additional speakers on the LAN
- CyberData speakers support 10 multicast paging groups for this purpose (vendor-specified)
- Multicast is handled entirely at the device/network level, not by Webex Calling

### Customer Managed Device Registration

1. Control Hub > **Management > Devices > Add device**, then select "Customer Managed Devices" from the dropdown
2. Choose workspace to assign the device to
3. Select "Generic SIP Phone" or "Generic SIP Gateway" profile
4. Device receives SIP username, password, and outbound proxy
5. Device must support **SIP-TLS 1.2** and **SRTP** (SRTP requirement not independently verified from official docs)
6. Add the device's workspace to the paging group as a target

---

## 8. End-to-End Integration: Connect → Paging Group

### Prerequisites Checklist

- [ ] Webex Calling paging group created with DID assigned
- [ ] Paging targets configured (phones and/or SIP speakers)
- [ ] Connect tenant with voice-enabled phone number provisioned
- [ ] Database/application configured to fire webhook on order status change
- [ ] **Originator enforcement tested** — confirm PSTN calls to paging DID trigger the page

### Complete Flow

```
Start (Webhook: order_id)
  |
  v
HTTP Request (GET /orders?id=eq.$(n1.inboundWebhook.order_id))
  → Parse: order_number, customer_name, location_name
  |
  v
Call User (destination: +1555PAGINGDID, from: Connect number)
  |
  |--- onAnswer ---> Voice Node Group
  |                      |
  |                      v
  |                  Play (SSML TTS with order details, repeated twice)
  |                      |
  |                      v
  |                  End
  |
  |--- onbusy ----------> [Log error] → End
  |--- onnoanswer ------> [Log error / retry] → End
  |--- onError ---------> [Log error] → End
  |--- oncallfail ------> [Log error] → End
  |--- onreject --------> [Log error] → End
  |--- onPolicyFail ----> [Log error] → End
  |--- onExpiry --------> [Log error] → End
```

---

## 9. Known Gotchas

| Issue | Fix |
|-------|-----|
| Call to paging DID gets "number not in service" | DID not assigned to paging group — check Control Hub configuration |
| Call connects but no audio on target phones | Originator enforcement may be blocking — test with a known originator first |
| Page only reaches some phones | Targets on active calls (depending on priority level) or Don't Disturb won't receive pages — this is by design |
| SIP speakers don't register | Must support SIP-TLS 1.2 and SRTP — check device firmware |
| Multicast doesn't reach all speakers | Multicast is LAN-level — check IGMP snooping settings on network switches |
| Page audio is too quiet | Adjust speaker volume at the device level, not in Connect |
| TTS plays too fast for paging | Use `<prosody rate="slow">` in SSML and add `<break>` tags between key information |
| Paging group at 75-device limit | Use multicast via a master SIP speaker to scale beyond the limit |

---

## References

- [Configure a Paging Group](https://help.webex.com/en-us/article/jqejtd/Configure-a-paging-group-in-Control-Hub)
- [Make and Answer a Paging Call](https://help.webex.com/en-us/article/lv5lcc/Make-and-answer-a-paging-call)
- [Paging Group API](https://developer.webex.com/docs/api/v1/features-paging-group)
- [Call Controls - Dial API](https://developer.webex.com/docs/api/v1/call-controls/dial)
- [Add Customer Managed Device](https://help.webex.com/en-us/article/nemh93t/Add-your-customer-managed-device)
- [CyberData Webex Calling IP Paging](https://www.cyberdata.net/collections/cisco-webex-calling-ip-paging)
- [Algo Webex Compatibility](https://www.algosolutions.com/solutions/compatibility/webex/)
- [Call User Node (Connect)](https://help.webexconnect.io/docs/voice-call-user)
