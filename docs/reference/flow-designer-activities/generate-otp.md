## Generate OTP Activity

<!-- ref-tag: fd-act-generate-otp-v1 -->

> **Provenance:** Documented from three sources, attributed per fact: (1) the live prod activity registry (wxcc-flow describe generate-otp -o json (today `wxcli cc-flow show-activity PROJECT_ID generate-otp -o json`), 2026-07-11); (2) Cisco's official article [Build and manage flows with Flow Designer](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer), § Generate OTP under "Activities in Utilities" — the article changelog records "Added the following activities: Cryptographic Hash, Generate OTP, Verify OTP." on 2026-06-29; (3) round-trip-tested FlowIR facts from `flow-designer-flowir.md` § 7b / § 11.

Cisco description: "The Generate OTP activity generates a one-time password (OTP) for user authentication scenarios such as two factor authentication, multi-factor authentication. You can use OTPs in multiple scenarios like confirming the identity of the user, checking the validity of accounts for business, securing information, and many more."

Registry description (from the live activity registry): "Define one-time password (OTP) generation logic that generates a unique OTP and stores it in an output variable."

**Companion activity:** [Verify OTP](verify-otp.md). Cisco: "The Generate OTP and Verify OTP activities are often used in conjunction to set up user authentication flows such as two-factor authentication." The Verify OTP section of the same Cisco article adds that verification metadata "includes the correlation ID (the transaction reference passed in Generate OTP)".

Registry metadata (from the live activity registry): `activityName: generate-otp`, category `core`, group `action`, activityType `action`, `supportedChannelTypes` is an empty list.

### Configuration (Cisco UI documentation)

The activity appears in the Flow Designer activity palette under **Utilities** (the Cisco article groups it in "Activities in Utilities" alongside BRE Request, Business Hours, Cryptographic Hash, HTTP Request, Parse, Set Variable, and Verify OTP). Cisco's steps: "Drag and drop the Generate OTP activity onto the flow canvas," then configure:

**General Settings:**

| Field | Description (Cisco) |
|---|---|
| Activity Label | "enter a name for the activity" |
| Activity Description | "(Optional) ... enter a description for the activity" |

**OTP Generation Logic:**

| Field | Description (Cisco, quoted) |
|---|---|
| OTP format | "Select an OTP Format. The default format is Alphanumeric. Webex Connect supports the following OTP formats: Alphanumeric - a string that contains a combination of alphabetic and numeric characters, for example Pq1ANQ, D345SdrQ. Alphabetic - a string that contains a combination of lower case and upper case alphabetic characters, for example BPmFxV, GhrtYwd. Numeric - a string that contains numeric characters, for example 675468, 4321, 4572." |
| OTP Length | "Enter the OTP Length. The default length is six characters. The minimum OTP length is 4 and the maximum length is 64." |

**Additional OTP Settings:**

| Field | Description (Cisco, quoted) |
|---|---|
| OTP Validity | "Define OTP Validity (in minutes). The OTP expires after this duration. On resend OTP request, the validity is reset. The default validity period of the OTP is 30 minutes." |
| On resend OTP request | "Select the action for On resend OTP request, either Generate new OTP or Re-use current OTP. The OTP validity is reset for either of the actions." |
| Transaction reference | "Enter a Transaction reference or select a variable that contains this value. This is a unique reference code tied to the generated OTP that is used to validate it." |

### FlowIR Properties (from the live activity registry, 2026-07-11)

| Input | Type | Required | Default | Notes |
|---|---|---|---|---|
| `pinFormat` | string | Yes | `ALPHANUMERIC` | RadioGroup — set the value directly, no `:radioName` suffix fields; `wxcli cc-flow list-activity-choices` returns a 400 naming the RadioGroup component. Values `ALPHANUMERIC`, `NUMERIC`, `ALPHA` per flowir.md § 7b (✅ round-trip tested) |
| `pinLength` | string | Yes | `"6"` | String, not integer. Valid range 4-64, regex `^(0*(?:[4-9]|[1-5][0-9]|6[0-4]))$` per flowir.md § 7b — matches Cisco's documented min 4 / max 64 |
| `pinValidity` | string | Yes | — | String, not integer. **Unit conflict — see Gotchas** |
| `pinResend` | string | Yes | `GENERATE_NEW` | Registry `allowedValues`: `GENERATE_NEW`, `REUSE_SAME` (RadioGroup per flowir.md § 7b) |
| `transactionReference` | string | Yes | — | Can use `{{variable}}` (e.g. `{{NewPhoneContact.ANI}}`) per flowir.md § 7b |
| `flowDecryptAccess` | boolean | No | `false` | Purpose not documented (not in the Cisco article or flowir.md) |

flowir.md § 7b additionally lists `extraParameters` (object, optional, "Additional key-value pairs") as a round-trip-tested property, but the live registry (2026-07-11) does not list it among the inputs. The Cisco Verify OTP section references "the key-value pairs that were set in the generate OTP node in the form of Key and Value" — the corresponding Generate OTP UI field is not shown in the Cisco Generate OTP section text.

### Output Variables

| Variable | Type | Source and description |
|---|---|---|
| `OTP` | String (**secure** — registry `isSecure: true`) | From the live activity registry: "The one-time password generated each time this activity runs." Cisco: "The standard output variable for the generate OTP node is generateOTP.OTP This captures the generated OTP." (i.e. referenced as `{{ActivityLabel.OTP}}` — Cisco shows the default label `generateOTP`) |
| `status` | String | Listed in the live activity registry with no description; not mentioned in the Cisco article |

### Output Paths

| Port | isErrorPath | Source |
|---|---|---|
| `out` (success) | No | **Implicit** — not reported by the live registry, but validated and round-tripped [flow-designer-flowir.md § 11 Implicit Output Ports, § 12 Activities with Implicit `out` Success Port] |
| `error` | Yes | From the live activity registry (the only port it lists; label is empty) |

For FlowIR builds, wire the success edge with condition `out` even though `wxcli cc-flow show-activity` does not list it — flowir.md § 8 registry table records the effective ports as `out`, `error`.

### Gotchas

- **`pinValidity` unit conflict:** the Cisco UI documentation says "Define OTP Validity (in minutes)" with a default of 30 minutes, but flowir.md § 7b describes the FlowIR value as "Validity duration in seconds as string (e.g. `"300"`)". The registry gives no default and no unit. A live round-trip on 2026-07-12 (run then as wxcc-flow create / export, live prod org; today `wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json` and `wxcli cc-flow export PROJECT_ID FLOW_ID --version draft`) confirmed the API **stores the value verbatim as a string** — `"300"` imported and exported unchanged — but this proves nothing about the unit. Which unit the API value actually uses is **still not verified** — confirm in the Flow Designer UI before relying on a value.
- `pinLength` and `pinValidity` are strings, not integers [flow-designer-flowir.md § 7b].
- `pinFormat` uses RadioGroup (not RadioGroupWithValue) — set the value directly without suffix fields [flow-designer-flowir.md § 7b, § 11 RadioGroup Pattern].
- The `OTP` output is a secure variable (registry `isSecure: true`) — from the live activity registry.
- On resend, the OTP validity resets regardless of whether you chose Generate new OTP or Re-use current OTP (Cisco, quoted above).

### Not Documented

- The unit of the FlowIR `pinValidity` value (minutes per Cisco UI vs. seconds per flowir.md § 7b — unresolved)
- `flowDecryptAccess` semantics
- The `status` output variable's possible values
- What triggers the `error` port (the Cisco article section does not describe error handling for this activity)
- Whether an Extra Parameters field exists in the Generate OTP UI (referenced only from the Verify OTP section)
- Self-loop limit
- Any minimum/maximum for OTP Validity

---
