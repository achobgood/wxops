# AI Receptionist: AI call answering, intents, and knowledge bases

An **AI Receptionist** answers an inbound call in natural language instead of playing a
menu. It greets the caller, works out why they rang, answers from documents you upload (a
**knowledge base**), and transfers to a person when an **intent** matches. It is a Webex
**Calling** feature, configured per location, and it arrived in the spec on 2026-08-03.

**What this is NOT.** It is not an **Auto Attendant** — that is a DTMF menu ("press 1 for
Sales") with fixed key mappings, documented in
[`call-features-major.md`](call-features-major.md). It is not **Contact Center**: there is
no queue, no agent state, no routing strategy, and none of the `cc-*` command groups touch
it. It is not **Customer Assist**. And despite the tag name you will see in the spec, this
document does **not** cover AI Receptionist call transcripts or sessions — see
[Gotcha 1](#7-gotchas), that surface does not exist yet.

## Sources

- **`specs/webex-cloud-calling.json`**, tag `AI Receptionist for Webex Calling` — 28
  operations, added upstream 2026-08-03. Every field, enum, and required-field claim below
  is read from that spec.
- **`wxcli ai-receptionist --help`** — the rendered CLI, which outranks this doc on command
  names and flags per the Source of Truth Precedence ladder in the root `CLAUDE.md`.
- **Not yet live-tested.** No call in this document has been run against a real org. Nothing
  here is marked `Verified live`, and that absence is deliberate — treat every behavioural
  claim as spec-derived until someone dates it.

## Table of Contents

- [1. How the three resources fit together](#1-how-the-three-resources-fit-together)
- [2. Knowledge bases and documents](#2-knowledge-bases-and-documents)
- [3. The AI Receptionist](#3-the-ai-receptionist)
- [4. Intents](#4-intents)
- [5. Discovery helpers and templates](#5-discovery-helpers-and-templates)
- [6. Command map](#6-command-map)
- [7. Gotchas](#7-gotchas)
- [8. See Also](#8-see-also)

## 1. How the three resources fit together

Three resources, at three different scopes. Build them in this order — each depends on the
one above it.

| Resource | Scope | Why the scope matters |
|----------|-------|-----------------------|
| **Knowledge base** (+ documents) | **Org-wide** — `/telephony/config/knowledgeBases` | Build the FAQ once and point every location's receptionist at the same `knowledgeBaseId`. |
| **AI Receptionist** | **Per location** — `/telephony/config/locations/{locationId}/aiReceptionists` | Each needs its own number or extension, and voice/number availability is a location question. |
| **Intent** | **Per receptionist** — `.../aiReceptionists/{aiReceptionistId}/intents` | An intent is a named reason-for-calling plus where to transfer it. |

One read crosses the grain: `GET /telephony/config/aiReceptionists` (`wxcli ai-receptionist
list`) lists receptionists **across the whole org**, even though create/read/update/delete
are all location-scoped. It is the only way to enumerate them without walking every location.

## 2. Knowledge bases and documents

A knowledge base is a named container; documents hold the actual text the AI answers from.
Both are org-wide.

### CLI Examples

```bash
# Create the container, then read it back
wxcli ai-receptionist create-knowledge-bases --name "Store FAQ" --description "Hours, returns, parking"
wxcli ai-receptionist list-knowledge-bases --all
wxcli ai-receptionist show-knowledge-bases KNOWLEDGE_BASE_ID

# Add a document as inline article text
wxcli ai-receptionist create-documents KNOWLEDGE_BASE_ID \
  --name "Returns policy" \
  --content "Unworn items may be returned within 30 days with a receipt."

wxcli ai-receptionist list-documents KNOWLEDGE_BASE_ID
wxcli ai-receptionist show-documents KNOWLEDGE_BASE_ID DOCUMENT_ID

# Retrieve a document's content (one document, not the whole base)
wxcli ai-receptionist download-documents KNOWLEDGE_BASE_ID DOCUMENT_ID

wxcli ai-receptionist delete-documents KNOWLEDGE_BASE_ID DOCUMENT_ID
wxcli ai-receptionist delete-knowledge-bases KNOWLEDGE_BASE_ID
```

### Key Parameters

`KnowledgeBaseDocumentDetails` declares two enums — the only enums on this surface besides
`contactType`:

| Field | Declared values | Meaning |
|-------|-----------------|---------|
| `knowledgeType` | `article`, `file` | `article` is inline text via `--content`; `file` is an uploaded document. |
| `status` | `pending`, `processing`, `success`, `failed` | Ingestion is **asynchronous** — a document is not answerable the moment it is created. |

### Raw HTTP

```bash
curl -X POST "https://webexapis.com/v1/telephony/config/knowledgeBases" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Store FAQ","description":"Hours, returns, parking"}'

curl "https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledgeBaseId}/documents" \
  -H "Authorization: Bearer $TOKEN"

# File upload — multipart, and the one operation with no wxcli command (Gotcha 3)
curl -X POST \
  "https://webexapis.com/v1/telephony/config/knowledgeBases/{knowledgeBaseId}/documents/actions/upload/invoke" \
  -H "Authorization: Bearer $TOKEN" -F "file=@returns-policy.pdf"
```

## 3. The AI Receptionist

Created per location. `create` and `update` both take deeply nested objects, so in practice
they are `--json-body` commands — see [Gotcha 2](#7-gotchas).

### Data Model

`CreateAiReceptionistRequest` declares four required fields: `name`, `enabled`,
`defaultAction`, `aiAgent`. Plus, from the field descriptions: **either `phoneNumber` or
`extension` is mandatory** — the spec states "at least one is required" on both, but marks
neither `required`, so the CLI cannot enforce it and the API will.

```jsonc
{
  "name": "Front Desk",          // unique across the location
  "enabled": true,
  "phoneNumber": "+14085551000", // this or extension (or both)
  "extension": "1000",
  "defaultAction": {             // what happens when no intent matches
    "actionType": "PLAY_MESSAGE_AND_DISCONNECT",
    "audioMessageSelection": "DEFAULT",
    "audioFileId": "...",
    "transferTo": { "contactType": "PEOPLE", "contactId": "..." }
  },
  "aiAgent": {
    "voice": { "aiEngine": "PRO", "displayName": "...", "languageCode": "en_US" },
    "knowledgeBaseId": "...",    // from section 2
    "guidelines": {
      "welcomeMessage": "Thanks for calling Contoso.",
      "goal": "Answer store questions and route billing to a person.",
      "guideline": "Never quote prices."
    },
    "transparencySettings": { "enabled": true, "message": "You're speaking with an AI." }
  },
  "directLineCallerIdName": { "directLineCallerIdNameSelection": "DISPLAY_NAME" },
  "dialByName": "front desk"     // no % + \ " or Unicode
}
```

> **The string values above are NOT a declared enum.** `PLAY_MESSAGE_AND_DISCONNECT`,
> `DEFAULT`, `PRO`, and `DISPLAY_NAME` come from the spec's **example**, which is also what
> `--generate-json-body` prints. The spec declares `defaultAction` and `aiAgent` as bare
> `object` with no `properties`, so there is no authoritative list of allowed values on
> disk. Do not present these to a user as the complete set.

### CLI Examples

```bash
# Start from the skeleton — do not hand-write the nested objects
wxcli ai-receptionist create LOCATION_ID --generate-json-body > receptionist.json
# edit receptionist.json, then:
wxcli ai-receptionist create LOCATION_ID --json-body file://receptionist.json

wxcli ai-receptionist list --all                          # org-wide
wxcli ai-receptionist show LOCATION_ID AI_RECEPTIONIST_ID # one receptionist
wxcli ai-receptionist update LOCATION_ID AI_RECEPTIONIST_ID --json-body file://changes.json --verify
wxcli ai-receptionist delete LOCATION_ID AI_RECEPTIONIST_ID

# Dry-run the configuration before committing to it
wxcli ai-receptionist validate-ai-receptionist LOCATION_ID --name "Front Desk"
```

### Raw HTTP

```bash
curl "https://webexapis.com/v1/telephony/config/aiReceptionists" -H "Authorization: Bearer $TOKEN"

curl -X POST "https://webexapis.com/v1/telephony/config/locations/{locationId}/aiReceptionists" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d @receptionist.json

curl -X PUT \
  "https://webexapis.com/v1/telephony/config/locations/{locationId}/aiReceptionists/{aiReceptionistId}" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @changes.json
```

## 4. Intents

An intent is a named reason-for-calling and the person or number it transfers to. Scoped to
one receptionist.

### Key Parameters

`transferTo.contactType` is a **declared** enum — unlike most of section 3:

| Value | Transfers to |
|-------|--------------|
| `PEOPLE` | A Webex user, by `contactId` |
| `RESOURCE_GROUP` | A resource group |
| `CONTACT` | An org contact |
| `PHONE_NUMBER` | A raw number, by `phoneNumber` |

`name`, `description`, and `transferTo` are all required. `description` is not decoration —
it is what the AI matches the caller's words against, so write it as the thing a caller
would say, not as an internal label.

### CLI Examples

```bash
# transferTo is nested, so this one needs --json-body too
wxcli ai-receptionist create-intents LOCATION_ID AI_RECEPTIONIST_ID \
  --json-body '{"name":"Billing","description":"Questions about an invoice or refund","transferTo":{"contactType":"PEOPLE","contactId":"Y2lzY29zcGFyazovL3VzL1BFT1BMRS8..."}}'

wxcli ai-receptionist list-intents LOCATION_ID AI_RECEPTIONIST_ID
wxcli ai-receptionist show-intents LOCATION_ID AI_RECEPTIONIST_ID INTENT_ID
wxcli ai-receptionist update-intents LOCATION_ID AI_RECEPTIONIST_ID INTENT_ID --json-body file://intent.json
wxcli ai-receptionist delete-intents LOCATION_ID AI_RECEPTIONIST_ID INTENT_ID
```

### Raw HTTP

```bash
curl -X POST \
  "https://webexapis.com/v1/telephony/config/locations/{locationId}/aiReceptionists/{aiReceptionistId}/intents" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Billing","description":"Questions about an invoice","transferTo":{"contactType":"PHONE_NUMBER","phoneNumber":"+14085552000"}}'
```

## 5. Discovery helpers and templates

Four read-only commands that answer "what can I even put here?" — run these before building.

```bash
# Is AI Receptionist available in this location's country?
wxcli ai-receptionist validate-country --country-code US

# Which voices can the AI use at this location?
wxcli ai-receptionist list-voices LOCATION_ID

# Which numbers are free to assign?
wxcli ai-receptionist list-available-numbers LOCATION_ID

# Starter configurations published by Cisco
wxcli ai-receptionist list-templates
wxcli ai-receptionist show-template TEMPLATE_ID
```

`show-template` returns a **template**, `show` returns a **receptionist**. They are different
resources and the names were pinned to keep them apart — [Gotcha 4](#7-gotchas).

### Raw HTTP

```bash
curl "https://webexapis.com/v1/telephony/config/aiReceptionists/templates" -H "Authorization: Bearer $TOKEN"

curl -X POST "https://webexapis.com/v1/telephony/config/aiReceptionists/actions/validateCountry/invoke" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"countryCode":"US"}'

curl "https://webexapis.com/v1/telephony/config/locations/{locationId}/aiReceptionists/voices" \
  -H "Authorization: Bearer $TOKEN"
```

## 6. Command map

All 27 commands in `wxcli ai-receptionist`, by resource. The 28th spec operation has no
command — see [Gotcha 3](#7-gotchas).

| Resource | Commands |
|----------|----------|
| Receptionist | `list` (org-wide), `show`, `create`, `update`, `delete`, `validate-ai-receptionist` |
| Intents | `list-intents`, `show-intents`, `create-intents`, `update-intents`, `delete-intents` |
| Knowledge bases | `list-knowledge-bases`, `show-knowledge-bases`, `create-knowledge-bases`, `update-knowledge-bases`, `delete-knowledge-bases` |
| Documents | `list-documents`, `show-documents`, `create-documents`, `update-documents`, `delete-documents`, `download-documents` |
| Templates | `list-templates`, `show-template` |
| Discovery | `validate-country`, `list-voices`, `list-available-numbers` |

## 7. Gotchas

1. **The `AI Receptionist` spec tag documents a surface that does not exist.** Upstream
   ships two tags — `AI Receptionist for Webex Calling` ("APIs for managing AI
   Receptionists") and `AI Receptionist` ("retrieving AI Receptionist sessions and
   conversational transcripts, restricted to Full Administrators", carrying the feature
   toggle `calling-air-transcript-api-CALL-205781`). **Both are applied to all 28 management
   operations, and the spec declares zero transcript or session endpoints.** Verified: the
   path+method sets under each tag are identical, and every one of the 28 operation objects
   carries both tags. There is no transcript API to call today, whatever the tag says.
   The two tags are deliberately folded into one CLI group, so `wxcli ai-receptionist` does
   not ship as two identical command sets — and folded in a way that lets the transcript
   endpoints generate normally if they ever ship, rather than being silently swallowed.

2. **`create` and `create-intents` cannot be driven by their flags alone.** Both declare
   required fields that are nested objects — `defaultAction` and `aiAgent` on `create`,
   `transferTo` on `create-intents`. The generator renders a nested object as a plain `TEXT`
   option, so `--ai-agent '{"voice":...}'` sends a JSON *string* where the API expects an
   object. Print the skeleton with `--generate-json-body`, edit it, and pass it back with
   `--json-body` (root `CLAUDE.md` Known Issue #2). `create-knowledge-bases` and
   `create-documents` have no nested required field and work with plain flags.

3. **Document file upload has no CLI command — 27 commands for 28 operations.**
   `POST .../documents/actions/upload/invoke` is `multipart/form-data`, which the generator
   structurally skips, so the drift gate records it as a deliberate gap rather than as
   missing coverage. Add text with `create-documents --content`, or upload a file with the
   raw curl in section 2.

4. **The bare verbs were pinned, because the generated names split one group across two
   resources.** As generated, `show` was
   `GET /telephony/config/aiReceptionists/templates/{templateId}` — a *template* — while
   `update` and `delete` acted on the *receptionist*. `wxcli ai-receptionist show` would have
   returned a template, exited 0, and answered a question nobody asked. The names were
   pinned so that `show` reads the receptionist — matching `update` and `delete` — and the
   template read became `show-template`, alongside `list-templates`. `download-documents`
   was renamed for the same reason: it downloads a document, not a knowledge base, whatever
   the container in its path suggests.

5. **Document ingestion is asynchronous.** `KnowledgeBaseDocumentDetails.status` declares
   `pending`, `processing`, `success`, `failed` — a 2xx on `create-documents` means the
   document was accepted, not that the AI can answer from it. Poll `show-documents` until
   `status` reads `success` before testing a call.

6. **Only three enums on this surface are actually declared.** `contactType` (4 values),
   `knowledgeType` (2), and `status` (4). Everything else visible in
   `--generate-json-body` output — `PLAY_MESSAGE_AND_DISCONNECT`, `PRO`, `DEFAULT`,
   `DISPLAY_NAME` — comes from the spec's *example*, not a declared enum, because
   `defaultAction` and `aiAgent` are typed as bare objects with no `properties`. Treat each
   as one known-good value, not as the allowed set.

7. **Nothing in this document has been live-tested.** The surface landed upstream on
   2026-08-03 and the commands were generated the next day. Required-field claims, enum
   values, and the build order in section 1 are all read from the spec. Before relying on any
   of it in front of a customer, run it and date what you saw — this repo's rule is that a
   spec-derived claim and an observed one must not read alike.

## 8. See Also

- [Call Features: Major](call-features-major.md) — Auto Attendants, the DTMF-menu
  alternative an AI Receptionist replaces. Go there when the caller experience needs fixed
  key-press routing rather than natural language.
- [Location Calling: Core](location-calling-core.md) — a receptionist is created inside a
  location, so location enablement and internal dialing come first.
- [Provisioning](provisioning.md) — number inventory. `list-available-numbers` only surfaces
  what the location already holds; adding numbers happens there.
- [Emergency Services](emergency-services.md) — an AI Receptionist holds a phone number, so
  the location's E911 address obligations cover it like any other number.
- [Contact Center: Core](contact-center-core.md) — the surface this is most often confused
  with. Go there when the requirement involves queues, agent state, or skills-based routing;
  AI Receptionist has none of those.
