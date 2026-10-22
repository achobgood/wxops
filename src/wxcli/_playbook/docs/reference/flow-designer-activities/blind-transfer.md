## Blind Transfer Activity

<!-- ref-tag: fd-act-blind-transfer-v1 -->

Transfers a call to an external DN. The call leaves Webex Contact Center entirely — **terminal node** with no output edges. You cannot transfer variables with this transfer. Use the **GoTo** activity to move contacts within Webex Contact Center (such as between entry points or flows). Use variable mapping to seamlessly transfer data along with the contact.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Transfer Dial Number | Specific number or `{{variable}}` — the destination DN. **Variable Dial Number accepts String variables only.** |
| Add Header | Optional SIP X-Headers (up to 20, LGW only) |

**SIP header PII warning:** Do not include the following sensitive PII in SIP headers:

- Full names of individuals
- Social Security Numbers (any part)
- Physical addresses (home or work)
- Financial information (credit card numbers, bank account details)
- Health information (health-related details or data that could be considered PHI)

**Reserved SIP header patterns (Blind Transfer):** The following 16 header patterns are reserved for internal use and must not be passed as custom headers. Any headers matching these patterns are dropped and not passed to Webex Contact Center:

- `X-Address`
- `X-ADD-DIVERSION`
- `X-BNR-State`
- `X-BNR-Original-Codec`
- `X-BNR-Bypassed`
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

### Output Variables

None. Blind Transfer is a terminal node with no downstream processing.

### Output Paths

**None.** Blind Transfer is terminal — the flow ends here. The only error path is the global Undefined Error event flow.

### Failure Codes

| Code | Description |
|---|---|
| 48 | Can't transfer after queueing or agent assigned |
| 6 | System error |

### Restrictions

- Cannot be used inside a Consult interaction
- Cannot be added in Event flows
- Self-loop limit: 10

### Caller Experience

The caller hears silence after the transfer until the destination answers. Use a **Play Message** before the Blind Transfer to fill the gap (e.g., "Connecting you now").

---

