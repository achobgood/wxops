## Verify OTP Activity

<!-- ref-tag: fd-act-verify-otp-v1 -->

> **Provenance:** Added to Flow Designer in mid-2026 — the help article changelog entry (2026-06-29) reads "Added the following activities: Cryptographic Hash, Generate OTP, Verify OTP," and the July 10, 2026 What's-new announcement says "Flow Designer now supports additional security-focused utility nodes" enabling "native OTP-based authentication (2FA/MFA) and secure payload-integrity in HTTPS requests" ([What's new for administrators in Webex Contact Center](https://help.webex.com/en-us/article/nv7abhz/What's-new-for-administrators-in-Webex-Contact-Center)). Sources below: the live prod activity registry (wxcc-flow describe verify-otp (today `wxcli cc-flow show-activity PROJECT_ID verify-otp`), 2026-07-11), Cisco's [Build and manage flows with Flow Designer](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer#validate-otp-node) § Verify OTP (section id `validate-otp-node`), and round-trip-tested FlowIR facts from `flow-designer-flowir.md` § 7.

"The Verify OTP activity allows you to validate the user-provided OTP using the transaction reference captured during OTP generation" (Cisco, § Verify OTP). Cisco lists it under **Activities in Utilities** alongside BRE Request, Business Hours, Cryptographic Hash, Generate OTP, HTTP Request, Parse, and Set Variable. It is the companion of the **Generate OTP** activity (see [generate-otp.md](generate-otp.md)) — "The Generate OTP and Verify OTP activities are often used in conjunction to set up user authentication flows such as two-factor authentication" (Cisco, § Generate OTP).

Registry metadata (from the live activity registry): `activityName: verify-otp`, displayName `Verify OTP`, category `core`, group `action`, activityType `action`, no channel-type restriction (`supportedChannelTypes` is empty).

### Configuration

To add the activity: "Drag and drop the Verify OTP activity onto the flow canvas" (Cisco, § Verify OTP).

**General Settings** (Cisco, § Verify OTP):

| Field | Description |
|---|---|
| Activity Label | "enter a name for the activity" |
| Activity Description | "(Optional) ... enter a description for the activity" |

**OTP Details** (Cisco, § Verify OTP):

| Field | Description (Cisco, quoted) |
|---|---|
| OTP | "Enter the variable name that contains the OTP entered by the user." |
| Transaction reference | "The unique reference which the node uses to verify the OTP obtained in step 1." Must match the transaction reference used in Generate OTP. |
| OTP Prefix / OTP Suffix | "(optional): Enter the prefix and/or suffix of the OTP, which needs to be removed before verifying the OTP." |

**Advanced Settings** (Cisco, § Verify OTP):

| Field | Description (Cisco, quoted) |
|---|---|
| Notify URL | "(Optional): Configure an endpoint to receive success/failure notifications. The notification payload includes the correlation ID (the transaction reference passed in Generate OTP), the status in the description field, the OTP verification timestamp, and related metadata." |
| Extra Parameters | "enter the key-value pairs that were set in the generate OTP node in the form of Key and Value. Repeat this step to add multiple parameters." |

Notify URL sample payload (Cisco, § Verify OTP):

```json
{
  "code": "0",
  "transid": "f7ff05a4-cab7-663a-bt24-74568e4ff297",
  "description": "SUCCESS",
  "correlationid": "c6464f3e-38a3-456t-87ea-a118565677a5",
  "time": "2026-05-19T10:02:41.234Z",
  "api": "verify",
  "txn_log_level": 0
}
```

### FlowIR Properties (live registry + flow-designer-flowir.md § 7 ✅ TESTED)

| Property | Type | Required | Default | Source / notes |
|---|---|---|---|---|
| `pin` | string | Yes | — | Live registry (`isSecure: true`). Variable containing the OTP to verify, e.g. `{{otpCode}}` (flowir.md § 7). Maps to the **OTP** UI field. |
| `transactionReference` | string | Yes | — | Live registry. Must match the generate-otp transaction reference (flowir.md § 7). |
| `pinFormatPrefix` | string | No | — | Live registry. Maps to **OTP Prefix** — stripped before verification (Cisco, § Verify OTP). |
| `pinFormatSuffix` | string | No | — | Live registry. Maps to **OTP Suffix** — stripped before verification (Cisco, § Verify OTP). |
| `flowDecryptAccess` | boolean | No | `false` | Live registry only. Purpose not documented in Cisco docs or flowir.md. |
| `notifyURL` | string | No | — | flowir.md § 7 (round-trip tested) — NOT in the live `describe` output. Corroborated by the **Notify URL** UI field (Cisco). |
| `resendCommand` | string | No | — | flowir.md § 7 (round-trip tested) — NOT in the live `describe` output and not in Cisco's UI field list. Semantics not documented. |
| `extraParameters` | object | No | — | flowir.md § 7 (round-trip tested) — NOT in the live `describe` output. Corroborated by the **Extra Parameters** UI section (Cisco). |

"Minimal required set is just `pin` and `transactionReference`" (flowir.md § 7 gotcha).

**Round-trip re-verified 2026-07-12** (run then as wxcc-flow create → export against live prod; today `wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json` → `wxcli cc-flow export PROJECT_ID FLOW_ID --version draft`): `notifyURL`, `resendCommand`, and `extraParameters` all survive import/export intact even though they are absent from the `describe` output — confirming the flowir.md § 7 finding on the current prod build. Their runtime semantics remain not documented.

**Registry/doc discrepancy:** the live `describe` output (2026-07-11) lists exactly five inputs (`pin`, `transactionReference`, `pinFormatPrefix`, `pinFormatSuffix`, `flowDecryptAccess`), while flowir.md § 7 round-trip tested three additional properties (`notifyURL`, `resendCommand`, `extraParameters`) and does not list `flowDecryptAccess`. Cisco's UI documentation covers Notify URL and Extra Parameters, supporting their validity despite absence from `describe`.

### Output Variables

| Variable | Type | Notes |
|---|---|---|
| `status` | String | From the live activity registry (no description provided). Values are not documented — Cisco's § Verify OTP does not document output variables. |

### Output Paths

From the live activity registry (2026-07-11) — matches flowir.md § 8 registry table exactly:

| Port | isErrorPath | Notes |
|---|---|---|
| `error` | Yes | Trigger semantics not documented |
| `failure` | Yes | Trigger semantics not documented |
| `resend` | Yes | "use the `resend` port to loop back to `generate-otp`" (flowir.md § 7 gotcha) |

The `error`, `failure`, and `resend` ports were confirmed to **round-trip on 2026-07-12** — a live flow wiring all three imported and exported intact (run then as wxcc-flow create / export, live prod org; today `wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json` and `wxcli cc-flow export PROJECT_ID FLOW_ID --version draft`).

The registry lists no success port. flowir.md § Implicit Output Ports lists `generate-otp` and `screen-pop` as having implicit `out` success ports but does NOT list `verify-otp` — whether an implicit `out` success edge applies here is **still not verified** (the 2026-07-12 round-trip flow did not wire an `out` edge from verify-otp, so its acceptance was not tested). General flowir.md guidance: "if an activity logically continues to the next step, try the `out` condition even if the registry doesn't list it."

### Use Cases

- Two-factor authentication: Generate OTP → deliver the code to the caller → Collect Input → Verify OTP (pairing per Cisco, § Generate OTP; wiring of the delivery/collection steps is not prescribed by Cisco's OTP sections)
- "Native OTP-based authentication (2FA/MFA)" (What's-new announcement, July 10, 2026)

### Not Documented

- Possible values of the `status` output variable, and which port fires on which verification outcome (success vs. wrong PIN vs. expired)
- Exact trigger semantics of the `error`, `failure`, and `resend` ports
- Whether an implicit `out` success port exists (not verified for this activity)
- `flowDecryptAccess` purpose and UI exposure
- `resendCommand` semantics (present in flowir.md § 7 tested table only)
- Maximum verification attempts, rate limits, or lockout behavior
- Self-loop limit

---
