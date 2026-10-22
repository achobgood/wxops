<!-- ref-tag: custom-functions-v2 -->

# Custom Functions (WxCC)

Platform knowledge for the **Custom Functions API** — user-authored JavaScript or
Python that a Flow Designer flow calls to transform data (parse a JSON payload,
normalize a phone number, format a value for TTS).

Two different things share the word "function" in this project:

| Thing | What it is | Where it is documented |
|---|---|---|
| **Custom Function** | The code asset itself — source, inputs, outputs, runtime, tags | This file |
| **Functions Activity** | The Flow Designer activity that *calls* a published Custom Function from inside a flow | `flow-designer-activities/functions-activity.md`, `functions-setup.md` |

This file covers the API and the `wxcli cc-functions` commands. For creating and
testing a function in the Control Hub UI, use `docs/playbooks/functions-setup.md`.

## The Host Is Different From Every Other Flow Endpoint

Custom Functions are served by the **regional Webex CC gateway**, not by the Flow
Store host that the rest of the `cc-flow*` commands talk to. This is not interchangeable —
verified live 2026-07-25:

| Request | `flow-store.produs1.ciscoccservice.com` | `api.wxcc-us1.cisco.com` |
|---|---|---|
| `GET /v1/{orgId}/functions` | 404 (no `/flow-store` prefix) / 500 (with it) | **200** |
| `GET /{orgId}/project/{projectId}/v2/flow-template` | **200** | 404 |
| `GET /{orgId}/project/{projectId}/flows/global-variables` | **200** | 404 |

The gateway carries only the publicly documented subset of the flow surface, so
the CLI keeps both base URLs rather than moving everything to the gateway.

Function paths have **no `{projectId}` segment** — they are org-scoped:
`/v1/{orgId}/functions`, not `/{orgId}/project/{projectId}/…`.

### Regional gateways

| Region | Base URL |
|---|---|
| US | `https://api.wxcc-us1.cisco.com` |
| ANZ | `https://api.wxcc-anz1.cisco.com` |
| UK | `https://api.wxcc-eu1.cisco.com` |
| EU (Frankfurt) | `https://api.wxcc-eu2.cisco.com` |
| Japan | `https://api.wxcc-jp1.cisco.com` |
| Canada | `https://api.wxcc-ca1.cisco.com` |
| Singapore | `https://api.wxcc-sg1.cisco.com` |
| India | `https://api.wxcc-in1.cisco.com` |

All 8 host names resolve in DNS (2026-10-19); only `us1` has been used live. Cisco's
Salesforce-integration help page (fetched 2026-10-19) names 7 region codes — every row
above except India; Cisco's Architecture page lists an India data center but no code
[owner: `contact-center-core.md` § API Base and Authentication].

> **Unverified:** the India row comes from the Flow Orchestration guide's region table
> on developer.webex.com, which could not be fetched on 2026-10-19 to re-check it.

The CLI defaults to US. `wxcli` reads the region from `profiles.default.cc_region`
in `~/.wxcli/config.json`; `wxcli set-cc-region` offers the 7 rows other than India
(no `in1`).

### Authentication

Same bearer token as every other `wxcli` call:
`Authorization: Bearer <YOUR_ACCESS_TOKEN>`.

Scopes: `cjp:config_read` to list, get, and export; `cjp:config_write` to create,
update, test, publish, lock, unlock, and import.

## The `handle` Contract

A function exports exactly one entry point named `handle`. It reads its declared
inputs from `request.inputs`, writes its result to `response.data`, and returns
the `response`:

```js
export const handle = async (request, response) => {
  const phoneDigits = String(request.inputs.contact.phone).replace(/\D/g, "");
  response.data = {
    phoneDigits,
    areaCode: phoneDigits.slice(0, 3)
  };
  return response;
};
```

Whatever you assign to `response.data` is what the flow receives.

This contract is reproduced (with a different example body) in
`flow-designer-activities/functions-activity.md` § Function Signature (JavaScript)
and § Function Signature (Python), and in `docs/playbooks/functions-setup.md`
§ Step 3. **This file wins on any disagreement about the signature.** The Python
spelling is inferred rather than published by Cisco and carries a hedge in both
of those copies — keep it there.

## Function Definition Fields

The create (`POST`) and update (`PUT`) bodies take the same shape:

| Field | Type | Notes |
|---|---|---|
| `name` | string | Must be unique **within the organization** — a duplicate returns `409 Conflict`. |
| `description` | string | Human-readable description. |
| `language` | enum | `js` or `py`. |
| `selectedRuntime` | string | **Case-sensitive.** Defaults to the highest supported runtime for the language — `nodejs22.x` for `js`, `python3.13` for `py`. |
| `timeoutInSec` | integer | Caps execution time. ⚠ **UNRESOLVED** how this relates to the flat "5 second execution time limit" documented for the Functions activity — see `flow-designer-activities/functions-activity.md` § Runtime for both readings. Do not assume 5 s is a ceiling *or* that any value is accepted. |
| `sourceCode` | string | The function source, sent as an escaped string. |
| `inputs` | array | One entry per declared input — see below. |
| `outputs` | string | A **stringified** JSON object mapping each output name to a sample value, e.g. `"{\"phoneDigits\":\"4155550132\",\"areaCode\":\"415\"}"`. |

### `inputs[]` entries

| Field | Notes |
|---|---|
| `name` | Input name. This is the key the code reads from `request.inputs`. |
| `dataType` | One of exactly six values: `boolean`, `datetime`, `decimal`, `integer`, `json`, `string`. ⚠ Casing is **UNRESOLVED** — see below. |
| `value` | A sample value. For `json`, a stringified JSON object. |

> ⚠ **UNRESOLVED — `dataType` casing.** Two spellings exist in this repo and nothing here settles which the server accepts:
>
> - **This doc:** lowercase — `boolean`, `datetime`, `decimal`, `integer`, `json`, `string`.
> - **`docs/examples/format-store-hours.json`** (a committed example carrying full source code; whether it was ever accepted by the server is not recorded): `"dataType": "String"` — capitalized, matching the UI's type labels. `docs/examples/function-import.json` leaves the field empty, so it settles nothing.
>
> The two files describe different layers — this table is the **create/update** body (`inputs[]` entries carry `name`, `dataType`, `value`), while both example files are the **export/import** shape (`inputs[]` entries carry `name`, `dataType`, `description`, `defaultValue`) — so the casing may legitimately differ by layer, or one of them may simply be wrong. The FlowIR layer uses a third spelling for a *different* field: `fnInputVariables[].type: "STRING"`, upper-case [`flow-designer-flowir.md` § 7. Activity Reference — fn-activity (Function)]. No live API evidence in the repo resolves this. **Do not normalize the copies to match.** Resolve against the live API, then update this table, the examples, and `functions-setup.md` § Step 4 together.

The **max input variables (10)** and the other activity-side limits are owned by
`flow-designer-activities/functions-activity.md` § Runtime.

### Server-managed metadata

Responses wrap the source and metadata as `{ "fnCode": "...", "fnMetadata": { ... } }`.
`fnMetadata` carries `id`, `orgId`, `name`, `description`, `language`,
`selectedRuntime`, `status` (`Draft` / `Published`), `timeoutInSec`,
`tagVersionMap`, `lockedBy`, `lockedDate`, `createdBy`, `createdDate`,
`lastModifiedBy`, and `lastModifiedDate`. Do not set these on create.

## Lifecycle

| Operation | Method + path | CLI |
|---|---|---|
| List | `GET /v1/{orgId}/functions` | `wxcli cc-functions list` |
| Get | `GET /v1/{orgId}/functions/{id}` | `wxcli cc-functions show ID -o json` |
| Create | `POST /v1/{orgId}/functions` | `wxcli cc-functions create --json-body file://fn.json` |
| Update draft | `PUT /v1/{orgId}/functions/{id}` | `wxcli cc-functions update ID --json-body file://fn.json` |
| Test | `POST /v1/{orgId}/functions/{id}:test` | `wxcli cc-functions test ID --json-body '{"inputs":{…}}'` |
| Publish | `POST /v1/{orgId}/functions/{id}:publish` | `wxcli cc-functions publish ID --json-body '{"tags":["Live"],"comment":"…"}'` |
| Export | `POST /v1/{orgId}/functions/{id}:export` | `wxcli cc-functions export ID -o json` |
| Import | `POST /v1/{orgId}/functions:import` | `wxcli cc-functions import --file PATH` |
| Lock | `POST /v1/{orgId}/functions/{id}:lock` | `wxcli cc-functions lock ID` |
| Unlock | `POST /v1/{orgId}/functions/{id}:unlock` | `wxcli cc-functions unlock ID` |
| Delete | `DELETE /v1/{orgId}/functions/{id}` | `wxcli cc-functions delete ID --force` |

`list` returns `{ "data": [...], "pageInfo": {...} }`. `lock` and `unlock` both
return the JSON string `"OK"`.

### Publishing and tags

Publish a draft under one or more of four tags — `Dev`, `Test`, `Latest`, `Live`
— to make that version addressable:

```bash
wxcli cc-functions publish 64f1b2c3d4e5f6a7b8c9d0e1 --json-body '{"tags":["Live"],"comment":"Initial release."}'
```

The response is the same `{ "fnCode", "fnMetadata" }` envelope, with the new tag
reflected in `fnMetadata.tagVersionMap` (e.g. `{"Latest": "1"}`). Only a
published function can be referenced from a flow.

### Export / import between environments

`:export` returns the definition as a plain JSON object — `name`, `language`,
`runtime`, `description`, `sourceCode`, `inputs`, `outputs` — and `:import`
accepts that object as a **multipart file upload**. Together they move a function
between orgs or environments.

**The import/export shape is not the create/update shape.** Two field-level
differences, both visible in the committed examples
(`docs/examples/function-import.json`, `docs/examples/format-store-hours.json`):

| | Create / update (`POST`, `PUT`) | Export / import |
|---|---|---|
| Runtime field | `selectedRuntime` | `runtime` |
| `inputs[]` entry fields | `name`, `dataType`, `value` | `name`, `dataType`, `description`, `defaultValue` |

`timeoutInSec` does not appear in either example file. Whether `:import` accepts
it is untested — do not assert either way.

⚠️ `:export` is a **POST**, not a GET. A `GET …:export` returns 404 (verified live
2026-07-25).

## Gotchas

| Gotcha | Detail |
|---|---|
| Wrong host | `/v1/{orgId}/functions` is 404 on the Flow Store host. Use the regional gateway. |
| No project segment | Function paths are org-scoped. Do not insert `/project/{projectId}/`. |
| `:export` is a POST | GET returns 404. |
| `outputs` is a string | It is a stringified JSON object, not a JSON object. Same for a `json` input's `value`. |
| `selectedRuntime` is case-sensitive | `nodejs22.x`, not `Nodejs22.X`. |
| Name collisions are org-wide | A duplicate `name` returns `409 Conflict` even across projects. |
| `:test` implicitly publishes | The test call publishes the latest draft before running, so it always executes your most recent source. |
| `:test` currently returns 400 in some orgs | `{"status":400,...,"description":"Failed to test custom fn, received unexpected response"}`. The request shape is correct — `{"inputs": {...}}` and `{}` both parse while `{"inputs": []}` returns "request body is not readable" — and it reproduces on a no-input function returning a constant, so the failure is in the execution backend. Verified live 2026-07-25. Publish and exercise the function from a flow instead. |
| `fnName` drops on flow round-trips | Separately from this API, exporting a flow can drop `fnName` on `fn-activity` nodes, breaking re-import. See `flow-designer-flowir.md` § 11. |

## Related — who owns what

| File | Owns |
|---|---|
| **This file** | The API layer: `/v1/{orgId}/functions` endpoints and hosts, the `handle` contract, definition fields, runtimes, `dataType` values, tags, lifecycle, the `wxcli cc-functions` commands |
| `docs/reference/flow-designer-activities/functions-activity.md` | The Flow Designer activity that calls a published function: input/output wiring, output paths, limits (200/org, 128 MB, 10 inputs, ~5,000 lines, execution time), the Functions-vs-other-options table |
| `docs/playbooks/functions-setup.md` | The sequence — create → test → publish → use in a flow — and the judgment about when to reach for a Function at all. It reproduces values from both reference docs with inline owner citations |
| `docs/reference/flow-designer-flowir.md` | `fn-activity` node properties and ports for programmatic flow building |

## See Also

- [functions-activity.md](flow-designer-activities/functions-activity.md) — the Flow Designer activity that calls a published function
- [flow-designer-flowir.md](flow-designer-flowir.md) — the FlowIR shape of a Functions activity node
- [functions-setup.md](../playbooks/functions-setup.md) — the create, test, publish and use sequence
