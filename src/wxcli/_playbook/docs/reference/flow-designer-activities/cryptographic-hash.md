## Cryptographic Hash Activity

<!-- ref-tag: fd-act-cryptographic-hash-v1 -->

> **Provenance:** Facts below come from three sources, each labeled: (1) the live prod activity registry (2026-07-11, wxcc-flow describe cryptographic-hash (today `wxcli cc-flow show-activity PROJECT_ID cryptographic-hash`)), (2) Cisco's help article [Build and manage flows with Flow Designer](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer) § Cryptographic Hash (Activities in Utilities), and (3) round-trip-tested FlowIR facts from `flow-designer-flowir.md`. The activity was announced July 10, 2026 in [What's new for administrators in Webex Contact Center](https://help.webex.com/en-us/article/nv7abhz/What's-new-for-administrators-in-Webex-Contact-Center) under "Expanded new flow control node support in Flow Designer": "This release introduces support for Generate OTP, Verify OTP, and Cryptographic Hash activities," enabling "native OTP-based authentication (2FA/MFA) and secure payload-integrity in HTTPS requests."

Generates a one-way hash of a plain string. Cisco help: "Cryptographic hash allows you to generate a one-way hash of a plain string using one of the supported algorithms. You can apply salt as additional security." Registry description: "Generate a one way hash of plain text with your chosen algorithm. Optionally apply a salt value."

Registry metadata: `activityName: cryptographic-hash`, category `core`, group `action`, activityType `action`, `supportedChannelTypes: []` (empty — no channel restriction listed).

### Configuration

Per Cisco help, drag the Cryptographic Hash activity onto the flow canvas, then configure two sections.

**General Settings** (from Cisco help):

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Hash Configuration** (Cisco UI field → registry input name):

| UI Field (Cisco help) | Registry input | Type | Required | Default | Description |
|---|---|---|---|---|---|
| Hashing algorithm | `algorithm` | string | No | `SHA256` | Cisco: "Select a hashing algorithm to generate a hash." Allowed values (registry): `SHA256`, `SHA512`. Cisco: "SHA-256: This algorithm generates a unique, fixed size 256-bit (32-byte) hash. SHA-512: This algorithm generates a unique, fixed size 512-bit (64-byte) hash." |
| Plain Text | `input` | string | Yes | — | Cisco: "Enter an input variable or plain text to be hashed." Accepts `{{variable}}` syntax (flowir.md §7). |
| Apply Salt | `applySalt` | boolean | No | `false` | Cisco: "Select this checkbox if you wish to configure additional security to the encrypted string. Salt is random data that is added to the string before it is passed to the hash function." |
| Salt type | `saltEncoding` | string | No | `TEXT` | Allowed values (registry): `AUTO`, `TEXT`, `BASE64`, `HEX`. Cisco: "Select the type of Salt data you wish to add to the string. Supported salt values include text, base64, and Hex. You can also generate a random value during runtime by selecting Autogenerate Salt." Registry `showOnCondition: applySalt == true`. |
| Salt value | `salt` | string | Yes* | — | Cisco: "Data that must be added to the string to be hashed." Registry `showOnCondition: applySalt == true && saltEncoding != AUTO` — but see the FlowIR gotcha below: the validator treats it as always required. |
| (not in Cisco help) | `flowDecryptAccess` | boolean | No | `false` | Purpose not documented — present in the registry with no description; not mentioned in the Cisco article. |

### Output Variables

From the live activity registry:

| Variable | Type | Registry description |
|---|---|---|
| `HashOutput` | String (isSecure: true) | "The resulting hash value generated from the input plain text." |
| `status` | String | (no description in the registry; possible values not documented) |

Cisco help ("What to do next"): "The standard output variable for the Cryptographic Hash node is CryptographicHash.HashOutput which captures the hash."

**Source discrepancy:** the Cisco article's in-section table lists output variables `hash.output` ("Generated hash is stored in this variable") and `hash.salt` ("The salt value used is stored in this variable"). These names do not match the live registry (`HashOutput`, `status`) or Cisco's own "What to do next" note (`CryptographicHash.HashOutput`). The registry lists no salt output variable. Treat the registry names as authoritative for FlowIR; how the UI surfaces a salt output (if at all) is not verified. A live round-trip (2026-07-12, run then as wxcc-flow create / export, live prod org; today `wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json` and `wxcli cc-flow export PROJECT_ID FLOW_ID --version draft`) confirmed the exported flow definition carries **no per-node output-variable declarations** — output variables are activity-registry-defined, not stored on the node — so import/export cannot confirm or deny a `hash.salt` runtime output. The `HashOutput` encoding (hex vs. Base64) likewise remains runtime-only and unverified.

### Output Paths

From the live activity registry:

| Port | isErrorPath | Notes |
|---|---|---|
| `error` | Yes | Registry label is empty. Cisco's node-outcomes column describes `onError` as "Hash generation failed because of invalid input." |

**Success path:** the registry lists no success port, but `cryptographic-hash` is confirmed to have an implicit `out` success port usable in FlowIR edge conditions (flow-designer-flowir.md § Activities with Implicit `out` Success Port). Cisco's node-outcomes column describes `onSuccess` as "Hash is generated successfully."

### FlowIR (round-trip tested — flow-designer-flowir.md §7/§11)

| Property | Type | Required | Notes |
|---|---|---|---|
| `algorithm` | string | No | `SHA256` (default) or `SHA512` — only two options |
| `input` | string | Yes | Value to hash — can use `{{variable}}` |
| `applySalt` | boolean | No | Default `false` |
| `saltEncoding` | string | No | `AUTO`, `TEXT` (default), `BASE64`, `HEX` |
| `salt` | string | Yes | **Always required and must be non-empty**, regardless of `applySalt`/`saltEncoding` |

**Gotcha (flowir.md §11):** `salt` is always required and must be non-empty, even when `applySalt` is `false` or `saltEncoding` is `AUTO`. The activity definition marks `salt` as `required: true` with `showOnCondition: "applySalt == true && saltEncoding != AUTO"` — the validator enforces the `required` flag and ignores the `showOnCondition`. Omitting `salt` or sending `""` causes an FC1015 error.

### Use Cases

From the Cisco announcement (What's new for administrators, 2026-07-10): security-focused utility node for building "secure and scalable customer interaction flows," enabling "secure payload-integrity in HTTPS requests" (e.g., hashing values passed to an HTTP Request activity). Announced alongside Generate OTP and Verify OTP for native OTP-based authentication (2FA/MFA).

### Not Documented

- `flowDecryptAccess` semantics (registry-only field, no description; absent from the Cisco article)
- `status` output variable values (no registry description; not in the Cisco article)
- Whether a salt output variable exists at runtime (Cisco table says `hash.salt`; the registry lists none)
- Output encoding of `HashOutput` (hex vs. Base64 representation of the digest)
- Behavior of `saltEncoding: AUTO` beyond Cisco's "generate a random value during runtime by selecting Autogenerate Salt"
- Self-loop limit

---
