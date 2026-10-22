## Bridged Transfer Activity

<!-- ref-tag: fd-act-bridged-transfer-v2 -->

Temporarily transfers a call to an external destination while **retaining flow control**. When the third party hangs up (or on failure), the call returns to the flow for further handling.

**Dequeue enhancement:** Bridged Transfer is enhanced to dequeue the contact when sending a contact to a third-party interactive voice response (IVR) or automatic call distribution (ACD). If the contact is not handled in the third-party system, it can be taken back to the original queue. For example, a contact center with both Webex Contact Center agents and agents on an external call center/PBX can queue a call against Webex Contact Center agents for a brief period (say 60 seconds). If no agent is available during that period, the call can be bridge transferred (with an implicit dequeue) to the external call center for handling to improve the response time.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Transfer Dial Number | Specific number or `{{variable}}` — the destination DN |
| Timeout | 1–120 seconds (default 10) — how long to wait for answer |
| Send Output Digits | Optional DTMF outpulsing after answer (up to 32 chars: 0-9, A-D, *, #, comma for 1s delay) |
| Add Header | Optional SIP X-Headers (up to 20, LGW only) |

**SIP header PII warning:** Do not include the following sensitive PII in SIP headers:

- Full names of individuals
- Social Security Numbers (any part)
- Physical addresses (home or work)
- Financial information (credit card numbers, bank account details)
- Health information (health-related details or data that could be considered PHI)

**Reserved SIP header patterns (Bridged Transfer):** The following 11 header patterns are reserved for internal use and must not be passed as custom headers. Any headers matching these patterns are dropped and not passed to Webex Contact Center:

- `X-BroadWorks-Correlation-Info`
- `X-FS-Support`
- `X-Path`
- `X-RTMS-CID`
- `X-RTMS-OID`
- `X-RTMS-CONFID`
- `X-RTMS-AGENT-LEGID`
- `X-RTMS-ENTER-SOUND`
- `X-RTMS-APP-PREFIX`
- `X-RTMS-No-Lookup`
- `X-VPOP-DOMAIN`

### Output Paths

The live registry exposes a **single `failure` output port** — wxcc-flow describe bridged-transfer (today `wxcli cc-flow show-activity PROJECT_ID bridged-transfer`) and wxcc-flow schema bridged-transfer (today `wxcli cc-flow show-node-template PROJECT_ID bridged-transfer -o json`) both returned `outputPorts: [{condition: failure, isErrorPath: true}]`, and flow-designer-flowir.md § 8 lists only `failure`. Verified 2026-07-23 by building a `Queue Contact → Play Music (60s) → Bridged Transfer` overflow flow that wired **only** the `failure` port and validated clean. There is no implicit `out`/`default` port (flow-designer-flowir.md § "implicit out ports" does not list bridged-transfer). On the `failure` port you branch on `FailureCode`.

**Cisco documents that the flow retains control and continues after the third party ends the call.** Verbatim: "The Bridged Transfer activity allows a call to be temporarily transferred with a flow to an external destination while retaining control of the call. The external destination can be an external bridge or an Interactive Voice Response service (IVR). When the third-party ends the call, the call flow continues and reengages as required, such as queuing the call to an agent." [source: https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer]

> **UNRESOLVED — Cisco's documented behavior vs. the live port structure.** Cisco documents that control returns to the flow and the call flow continues once the third party ends the call, yet the live registry exposes **no success port** — only `failure` (verified 2026-07-23, see above). Both can be true if the continuation is **implicit** (the flow resumes on its own) rather than a wired edge you author. Only a live call in your own tenant settles it. Until then: treat `failure` as the only **wireable** output. The older guidance "wire one output edge and branch on `FailureCode == 0` for success" is inconsistent with the single-`failure`-port structure — do not use it unless a live call confirms a wireable success continuation.

### Output Variables

| Variable | Description |
|---|---|
| `BridgedTransfer_dxm.FailureCode` | Error/status code (0 = success) |
| `BridgedTransfer_dxm.FailureDescription` | Human-readable failure description |
| `BridgedTransfer.Headers` | SIP headers from BYE message (JSON) |

### Failure Codes

| Code | Description | Typical handling |
|---|---|---|
| 1 | Invalid number | Play error → Disconnect |
| 2 | Busy | Play "line is busy" → Disconnect or retry |
| 3 | No answer (timeout) | Play "no answer" → Disconnect or queue to fallback |
| 6 | System error | Play error → Disconnect |
| 48 | Can't transfer after queueing or agent assigned | Play error → Disconnect |

**Cisco documents exactly five failure codes for Bridged Transfer** — 1 `Invalid_Number`, 2 `Busy`, 3 `No answer`, 48 `Unsupported flow activity`, and 6 `System_Error` [source: https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer]. Cisco's verbatim descriptions:

- 1 `Invalid_Number` — "The dialed external directory number (DN) is invalid."
- 2 `Busy` — "The external DN is either engaged or has rejected incoming calls."
- 3 `No answer` — "The external DN failed to answer the call within the preset timeout duration."
- 48 `Unsupported flow activity` — "The flow can't run the Bridged Transfer activity post-queueing or once an agent has been assigned to the call."
- 6 `System_Error` — "This code represents miscellaneous errors that don't fall into the above defined categories."

> **Project observation with NO Cisco source — do not build from this.** An earlier revision of this file listed a sixth code in the table above: `5 — Unsupported DN (EP-DN or agent's own DN)`. A search of the full Cisco Flow Designer article (3.6 MB of raw HTML, checked 2026-07-27) found **zero occurrences** of the string "Unsupported DN", and Cisco's failure table has exactly the five rows listed above. Code 5 is retained here only as an unsourced project observation; it is not Cisco's and must not be relied on.

### Wiring Pattern

```
Play Message ("Connecting you to...") → Bridged Transfer ({{Extension}}, timeout: 30s)
  │
  └── failure (only wireable port) → Play Message (error) → Disconnect Contact / fallback queue
```

Cisco documents that the transfer is temporary and that "when the third-party ends the call, the call flow continues and reengages as required" [source: https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer]. The activity nonetheless exposes **only a `failure` output port** (verified — see § Output Paths), so `failure` is the only edge you can wire; that tension is UNRESOLVED (see § Output Paths). Wire the `failure` port to your error/fallback handling and branch on `FailureCode` there if you need to distinguish busy (2) / no-answer (3) / code-48 (queued-or-assigned).

> The older `FailureCode == 0` "TRUE (connected) → Disconnect" branch shown in earlier docs assumed a success-continuation edge that does not exist in the port structure. Do not rely on it unless a live call in your tenant confirms a post-success return.

### Restrictions

- Cannot be added to the Queue Contact activity
- Do not introduce a Bridged Transfer activity later in the flow for contacts that are parked, queued, or assigned to an agent. This may lead to an unsupported flow error.
- Cannot be used in outbound call flows
- Cannot be added in Event flows
- Available on VPOP and Webex Calling platforms only
- Self-loop limit: 75

### Dequeue Behavior

Bridged Transfer has an implicit dequeue enhancement. From Cisco docs:

> "Bridged Transfer is enhanced to dequeue the contact when sending a contact to a third-party interactive voice response (IVR) or automatic call distribution (ACD). If the contact is not handled in the third-party system, it can be taken back to the original queue."

**Example use case:** Queue a call against WxCC agents for a brief period (e.g., 60 seconds). If no agent is available, Bridged Transfer (with implicit dequeue) sends the call to an external call center.

**Contradiction with Restrictions:** The dequeue enhancement describes a queue-then-transfer use case, but the Restrictions section warns "Do not introduce a Bridged Transfer activity later in the flow for contacts that are parked, queued, or assigned to an agent. This may lead to an unsupported flow error." These statements conflict — the dequeue enhancement explicitly supports post-queue usage, but the restriction warns against it. Test this behavior in your environment before relying on it.

### Blind Transfer vs Bridged Transfer

| Aspect | Blind Transfer | Bridged Transfer |
|---|---|---|
| Flow control retained? | No — call leaves system | Yes per Cisco — the transfer is temporary and "the call flow continues and reengages as required" when the third party ends the call; on failure it returns via the `failure` port. ⚠ No success port exists in the live registry — UNRESOLVED, see § Output Paths |
| Output paths | Terminal (none) | One `failure` port only — no success/continuation port (verified; see § Output Paths) |
| Timeout setting | None | 1–120 seconds |
| Failure codes | 2 (codes 48, 6) | 5 (codes 1, 2, 3, 48, 6) |
| DTMF output digits | No | Yes (up to 32 chars) |
| Use after queueing? | No (code 48) | No (code 48) |

---

