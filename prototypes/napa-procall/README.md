# NAPA PROCall — WxCC Integration Prototype

A working mockup of the customer's PROCall screen, wired so the Webex Contact
Center SDK drops into a single seam. Run `./serve.sh` and open
`http://localhost:8099/` in Chrome, Edge, or Firefox — WebRTC needs a secure
context, so `file://` will not work. Click **Simulate Call** to run the whole
lifecycle.

## Fetching the SDK bundle

`vendor/` is **gitignored** — 8.2 MB of minified SDK plus sourcemap. Re-fetch it
before first run:

```bash
mkdir -p vendor
curl -L -o vendor/contact-center.min.js \
  https://unpkg.com/@webex/contact-center@3.12.0/umd/contact-center.min.js
curl -L -o vendor/contact-center.min.js.map \
  https://unpkg.com/@webex/contact-center@3.12.0/umd/contact-center.min.js.map
```

Verified 2026-08-01: both files come back **byte-identical** to what was vendored
here (sha256 `6679c036…9d293` and `d7af49b3…7ba6c` respectively). `index.html`
loads the bundle with a plain `<script src="vendor/contact-center.min.js">`; it is
a UMD build that exposes a global `Webex`, so there is no build step.

**Pin the `3.12.0` in those URLs.** It is the current `latest` — there is nothing
to upgrade to — and the package publishes ~10 live dist-tags including feature
branches. The sourcemap is not optional: it carries `sourcesContent` for 1015
modules, which is the only way to read the SDK's actual TypeScript. That is what
`docs/reference/contact-center-agent-sdk.md` was written from.

Built from the seven screenshots in `~/Documents/napa-pro-call` (dashboard →
screen pop → order entry → store dropdown → catalog → transfer → after-call work).

## The one architectural fact that shapes everything

**The call bar is persistent chrome, not part of a page.** In the customer's
screenshots it survives navigation from order entry into the parts catalog. So
the WxCC session lives *above* the router, at app shell level. Mount the SDK
once at boot; never tie it to a screen's lifecycle. Get this wrong and the call
drops when the cashier opens the catalog.

## The seam

Every call action routes through the `Wxcc` object in `index.html`. Each method
carries a `>>> LIVE <<<` comment with the real call to make. The UI never talks
to the SDK directly, so going live touches only that object.

The floating **WxCC SDK trace** panel prints the exact SDK call each click maps
to — use it to confirm the mapping before writing any real integration code.

## Control map — NAPA UI → `@webex/contact-center`

| PROCall control | SDK call | Event back |
|---|---|---|
| (app boot) | `webex.cc.register()` | — |
| (agent signs in) | `stationLogin({teamId, loginOption:'BROWSER'})` | `agent:stationLoginSuccess` |
| Incoming-call pop | — (inbound) | `task:incoming` |
| **Accept** | `task.accept()` | `task:assigned`, `task:media` |
| **Decline** | `task.decline()` | — |
| **Hold / Resume** | `task.hold()` / `task.resume()` | `task:hold`, `task:resume` |
| Transfer → Warm | `task.consult({to, destinationType})` | `task:consultCreated` |
| Transfer → Cold | `task.transfer({to, destinationType})` | `task:end` |
| **End** | `task.end()` | `task:end` |
| Consult → Complete Transfer | `task.consultTransfer()` | `task:end` |
| Consult → Conference All | `task.consultConference()` | `task:conferencing` |
| After Call Work → Save | `task.wrapup({auxCodeId, wrapUpReason})` | `task:wrappedup` |
| State pill (Ready/Idle) | `setAgentState({state, auxCodeId})` | `agent:stateChange` |
| Customer phone (click-to-dial) | `webex.cc.startOutdial(destination, origin)` — two positional strings, not an object (`cc.ts:1490`); `origin` is the outdial ANI | `task:incoming` (see #13) |
| **Pause Rec** (PCI) | `task.pauseRecording()` | `task:recordingPaused` |
| **Resume Rec** | `task.resumeRecording({autoResumed:false})` | `task:recordingResumed` |
| Order line added / changed | *no SDK path* — backend `PATCH /v1/tasks/{id}` | — |

Transfer destination mapping: **Store** → `destinationType:'queue'`,
**Call Agent** → `'agent'`, **Phone Number** → `'dialNumber'`.

Audio: `task.on('task:media', track => audioEl.srcObject = new MediaStream([track]))`.
That is the whole WebRTC leg — no desk phone required.

## Real tenant values already wired in

Pulled live 2026-07-31; see the `TENANT` constant.

| | |
|---|---|
| Main Team (AGENT) | `5f06fe30-ac3c-46e4-9d6b-751262769ea1` |
| MemberServices_Team (AGENT) | `c6b84493-527d-47d6-ad24-63ea006e3eb4` |
| Agent-Profile — **has** `BROWSER` | `27d1bede-90d2-447a-a383-bd88b4075a1d` |
| Agent-Profile (Auto WrapUp) — **no** `BROWSER` | `f6c21a48-cc2d-4244-9bf6-7784d785ec49` |

## Wrap-up codes — done

All 12 dispositions now map to a real wrap-up code. The 11 `PROCall - *` codes
were created in the tenant on 2026-07-31, named to match the disposition strings
exactly so WxCC reporting lines up with what the cashier picks. `Resolved -
Order Placed` maps to the pre-existing `Sale` code, which is still the tenant
default and was left untouched.

| Disposition | auxCodeId |
|---|---|
| Billing - Invoice Copies | `a9528b44-46ae-45b2-a931-ef33f5e1a4c0` |
| Delivery Status - Tracking | `9df355f6-e35b-49ab-955d-a27edd33c384` |
| Order Cancellation | `aa824967-cce5-486c-b154-2436d291e960` |
| Order Pending - Quote | `e906ca41-5a93-4a13-893a-a9f21f0babf3` |
| Order Status | `44f73287-45ee-4bfc-a410-b3d48ced8117` |
| Product Information | `985ff9c1-4853-488d-9fa1-187ccbbe40b6` |
| Promotions - Price Match | `fc60ae55-6a40-44f5-9522-57628a0542ac` |
| Requires Follow-up | `b11e4554-e2e0-476a-afe5-a20bc8d9628f` |
| Resolved - Order Placed | `355e8a91-…` (existing `Sale`) |
| Spam | `ef3f8f42-6b36-4b67-9ce6-884a7f0a4dd9` |
| Store Hours and Location | `688d19f6-bd28-40ba-ba08-12792247a563` |
| Wrong Number - Not Interested | `a9f1fa53-2f6d-41ed-a363-53d4256a01a3` |

One naming note: mapping *Resolved - Order Placed* onto a code literally named
`Sale` will read oddly in WxCC reports. Creating a 12th code with the matching
name and repointing it is a one-liner if that matters.

## Remaining blocker

**The second profile can't do browser audio.** `loginVoiceOptions` on
`Agent-Profile (Auto WrapUp)` is `["EXTENSION","AGENT_DN"]` — no `BROWSER`. Any
cashier on that profile fails `stationLogin({loginOption:'BROWSER'})` with
everything else correct. Note also that its `autoWrapUp` setting will fight a
custom ACW screen: the platform may close wrap-up under the cashier.

## Live integration gotchas (found the hard way, 2026-07-31)

All three cost real debugging time against the live tenant. None is discoverable
from the SDK's TypeScript definitions.

**1. `Team` types don't match the wire format.** The shipped `.d.ts` declares
`Team = {teamId, teamName, desktopLayoutId?}`. The runtime payload from
`register()` is `{id, name, teamType, teamStatus, active, siteId, siteName, …}`.
Reading `profile.teams[0].teamId` yields `undefined`, `stationLogin` then goes out
with no team, and the only symptom is a bare `Error while performing stationLogin`.
Read `.id`, fall back to `.teamId`, then to `profile.currentTeamId`.

**2. Going Available requires `auxCodeId: '0'`.** `setAgentState({state:'Available'})`
fails with `Error while performing setAgentState`. The platform returns an idle code
literally named `"Available"` whose `id` is the string `"0"`; that is what the
Available state expects. `{state:'Available', auxCodeId:'0'}` succeeds. `StateChange` *is* exported
(`index.ts:147`) and does mark `auxCodeId` required — but nothing anywhere reveals the
magic value, so it is not discoverable statically. Filter the `id === '0'` entry out of
any idle-reason menu — it is not a real idle reason.

**3. An existing station session must be dropped, not adopted.** If
`profile.isAgentLoggedIn` is true, skipping `stationLogin` *appears* to work —
`register()` succeeds and Idle state changes are accepted — but the WebRTC endpoint
belongs to whichever page did the original login, so your page has no media and the
platform refuses to make the agent Available. Call `stationLogout({logoutReason})`
first, then `stationLogin`. `allowMultiLogin` defaults to `false`, so logging in
alongside the old session is not an option either.

**4. The ANI lives at `callProcessingDetails`, not `callAssociatedDetails`.** Full
path: `task.data.interaction.callProcessingDetails.ani` (siblings: `displayAni`,
`dnis`, `QueueId`, `vteamId`). The plausible-sounding `callAssociatedDetails` does
not exist, and reading it yields `undefined` — so the screen pop silently shows
"Unknown caller" on every real call while looking perfectly healthy. Compare the
last 10 digits when matching so `+1…`, `1…` and bare 10-digit all resolve.

**5. One Webex instance per page — reconnect by reloading.** Calling `Webex.init()`
a second time in the same page without disposing the first leaves orphaned
websockets and WebRTC device registrations. After a few reconnects the SDK starts
failing in a cascade that looks like a platform outage but is entirely local:

1. `service-interceptor: 'wcc-api-gateway' is not a known service` — service
   discovery never populates. (Both u2c catalogs return 200 from curl and
   `wcc-api-gateway` is present in the full catalog, so it is not an outage.)
2. Fix the disposal order and you get `Error while performing silentRelogin` —
   because `deregister()` deliberately leaves the agent *logged in*; only
   `stationLogout()` ends the station session.
3. Fix that and `stationLogin` itself starts failing on the third cycle.

Chasing a clean in-place reconnect is not worth it. `goLive()` now stashes the
token in `sessionStorage` and reloads; the page auto-resumes on load. Boring and
reliable. `beforeunload` also deregisters so a manual refresh doesn't orphan a
device (Webex caps users at 5).

**6. The mode badge must never lie.** The mock defaults the state pill to
"Ready (Voice,VM)". After a reload with no session that reads as a live, ready
agent — which is exactly how a dead connection went unnoticed during testing.
The header now always shows `○ MOCK` or `● LIVE`, set from real session state.

**7. One session per agent, full stop.** An agent can hold exactly one station
session. A second page trying to connect as the same agent gets
`AGENT_SESSION_ALREADY_EXISTS`, and the teardown's `stationLogout` fails with
`AGENT_HAS_ASSIGNED_CONTACTS` if a call is assigned — so the second page cannot
force its way in either. Two browsers open on this prototype will fight over the
agent and the loser silently sits in mock mode. Keep exactly one tab open.

**13. `startOutdial()` does not return a Task.** Its return type is
`TaskResponse = AgentContact | Error | void` — an AQM response with an
`interactionId`, with no `.on()` and no `.wrapup()`. The usable `ITask` is
delivered separately through `cc.on('task:incoming')`, because the dialer binds
its success notification to `AGENT_OFFER_CONTACT`. Two consequences:

- Binding call controls to whatever `startOutdial` resolves to leaves you with no
  task handle, so hold/end/wrapup silently fail later.
- An outbound call therefore arrives on the **same event as an inbound one** and
  will pop the "Incoming Call" Accept/Decline dialog for a call the agent just
  placed, unless you track a pending-outbound flag and branch on it.

**14. Surface wrap-up failures in the dialog, not the trace.** `saveWrapup()`
dereferenced `DISPOSITIONS[selectedDisp]` before its try block, so a null
selection threw uncaught: no save, no close, no error anywhere the operator could
see. Every failure path (no disposition, no mapped code, no live task, platform
rejection) now writes a visible message into the ACW footer.

**12. `destinationType` values are camelCase, not the enum key names.** The
shipped types declare `DESTINATION_TYPE` members only as `string`, so the values
are invisible statically. They are:

```js
QUEUE: 'queue'   DIALNUMBER: 'dialNumber'   AGENT: 'agent'   ENTRYPOINT: 'entryPoint'
```

Sending `'QUEUE'` / `'AGENT'` (the key names) does not raise an obvious error —
**the call simply never moves.** Silent failure. `entryPoint` is consult-only, so
a cold transfer to a store must use `queue`.

**9. Wrap-up is not dismissable, so the UI must not let you dismiss it.** WxCC
holds the agent in wrap-up until a disposition is submitted. The ACW dialog
originally had an `×` and a "Back to Call" button; closing it left the agent
visibly in Wrap Up with no way back to Ready and no way to reopen the dialog.
Now: once the task ends, both dismiss controls are hidden, `closeModal()` refuses
to close the ACW dialog while `state === 'WRAPUP'`, a required-banner appears, and
clicking the state pill reopens the dialog as an escape hatch. Note the ordering
trap this creates — `saveWrapup()` must clear `WRAPUP` *before* calling
`closeModal()`, or it deadlocks against its own guard.

**10. Show the real ANI, not the account's stored number.** When a call matches a
customer via an alternate number, displaying the primary number on file is
actively misleading — the agent cannot tell which line rang. The pop now shows the
actual calling number, with "primary on file …" underneath when they differ.

**11. `?mock=1` suppresses auto-connect.** Because of gotcha #7, opening a second
tab normally would fight the live session. Use `http://localhost:8099/?mock=1` to
exercise the UI without touching the tenant.

**8. Serve with `Cache-Control: no-store`.** The browser will happily reuse a
cached `live.js` and you will debug code that is not the code on disk. `serve.sh`
sets no-store headers for this reason; a hard reload was required before that.

**Settled while testing:** a Personal Access Token *does* carry `cjp:user` — the
agent's PAT drove `register()`, `stationLogin()` and `setAgentState()` against the
live tenant. Our project docs claim PATs never work for Contact Center; that is at
minimum incomplete, and applies to config scopes rather than the agent runtime.

## Going live

1. `npm i @webex/contact-center` (Node ≥20).
2. OAuth integration with `cjp:config_read`, `cjp:config_write`, **`cjp:user`**,
   `spark:webrtc_calling`, `spark:calls_read`, `spark:calls_write`, `spark:kms`.
3. Broker tokens from a backend — never ship an org-wide admin token to a POS
   terminal. `cjp:user` is the per-agent runtime scope.
4. Replace the `>>> LIVE <<<` bodies. Leave the UI alone.

## Constraints worth re-checking before rollout

- **VDI does not support WebRTC.** Confirmed not applicable here, but re-check
  per site before assuming browser audio for every store.
- Chrome, Edge, Firefox only — **Safari is not supported**. Matters if any
  terminal is an iPad.
- Max 7 conference participants; wrap-up must complete before the next task;
  `allowMultiLogin` defaults to `false`.

## What else is wired

Beyond the screenshot flow, these exist because they're the integration points
that carry the business case:

- **Order lines.** Type a part number (autocompletes — try `NAPA 1515`,
  `NBH 25060`, `NAPA 7565`) or hit the magnifier. Live availability per store,
  cross-store NAPA XPress sourcing when the serving store is short, editable
  quantities, computed extended price and subtotal.
- **Store Stock Check** populates as you type a part number, per the screenshots'
  empty-state hint.
- **CAD variables — NOT wired, and not wireable from the browser.** Joining
  "which call produced which order" is still the payoff for the whole
  integration, but `@webex/contact-center` v3.12.0 has **no CAD-write API**.
  Verified against the TypeScript sources shipped inside
  `vendor/contact-center.min.js.map` (1015 modules with `sourcesContent`): zero
  hits for `updateCad`, `cadVariable`, `callAssociatedData`,
  `setInteractionVariables`, `flowVariables` or `globalVariables`. The Task's
  entire public surface is 16 methods and none of them writes variables.
  The only variable-shaped thing in the SDK is `callVariablesSuppressed`, a
  read-only tenant flag (`services/config/types.ts:647`) — check it on the
  tenant, because if it is true nothing reaches the desktop at all.
  **The route that does exist** is server-side: `PATCH /v1/tasks/{interactionId}`
  with `{"attributes":{…}}` (`wxcli cc-tasks update`), called from a NAPA backend
  with the `interactionId` the browser already holds. Never from the POS terminal.
  The variable must first exist org-wide as a Global Variable
  (`wxcli cc-global-vars`, `/organization/{orgid}/cad-variable`).
- **Reading** flow data, by contrast, needs no new API — see the flow probe below.
- **Call notes** are captured but have nowhere to go for the same reason. When
  the backend PATCH exists, the write must happen *before* `wrapup()`: wrapup
  ends the task and a write against an ended task is rejected.
- **Warm transfer completion.** Consult puts the customer on hold and raises a
  second amber bar with *Conference All* / *Complete Transfer* →
  `consultConference()` / `consultTransfer()`.
- **Agent state menu** on the state pill, listing the tenant's real idle codes
  (Meeting, WellbeingBreak, Agent_Busy, Agent_Unavailable) with their live IDs.
- **Click-to-dial** on any customer phone number → `startOutdial()`.
- **F9** toggles the catalog, **F2** completes the invoice — the shortcuts the
  customer's own UI advertises.

## Recording pause/resume (PCI)

Wired against `Task.pauseRecording()` / `Task.resumeRecording({autoResumed})`
(SDK sources `services/task/index.ts:968` and `:1060`; events at
`services/task/types.ts:300-324`). **Not yet exercised against a live recorded
call** — the queue needs recording plus pause/resume enabled in Control Hub first.

Three things this design gets right and a naive one would not:

1. **The button follows the event, never the click.** WxCC auto-resumes after the
   tenant's `pauseDuration` and announces it with the same `task:recordingResumed`
   a manual resume produces. A local boolean drifts and ends up showing "paused"
   over a live recording.
2. **"Cannot pause" and "not paused" look different.** The four fields
   `pauseResumeEnabled`, `isPaused`, `recordInProgress`, `recordingStarted` live on
   `callProcessingDetails` (`types.ts:605-614`) and are **strings**, not booleans.
   If the queue has pause/resume off the button reads `Pause N/A` and is disabled.
3. **A failed pause shouts.** It writes into the call bar (`cbAlert`), not the
   trace panel: the agent asked for silence, did not get it, and is about to read
   a card number onto the recording. A resolved promise only means the platform
   *accepted* the request — that is why there is no optimistic UI here.

Server-side equivalents exist if you ever need them out-of-band:
`wxcli cc-tasks create-pause <taskId>` / `create-resume`.

## Reading flow variables — `interaction.callFlowParams`

**This is the container. It is declared, it is typed, and it takes arbitrary
keys by design** (`services/task/types.ts:736-751`):

```ts
callFlowParams: Record<string, {
  name: string; qualifier: string; description: string;
  valueDataType: string; value: string;
}>
```

"Parameters passed through the call flow." Anything a Flow Designer **Set
Variable** node marked *Agent Viewable* produces should land here — a
`Record<string, …>`, so custom names are expected rather than a surprise. Both
UI panels read it and mark every entry ★.

A second, lesser source: any key on `callProcessingDetails` that the SDK type
does *not* declare is also flow-set, so those get ★ too. That type is a closed
set with no index signature, but it has already been caught lying about the wire
format twice here (`Team.teamId` vs `.id`; `StateChange` not exported), so
undeclared keys are displayed rather than filtered.

**Version drift worth knowing — and do NOT "just upgrade."** The published
typedoc at `web-sdk.webex.com/wxcc` gives `Interaction` 27 top-level keys
including `callAssociatedData` and `callAssociatedDetails`. The vendored build
declares 19 and neither. That typedoc is built from the **`next` prerelease**:

| npm dist-tag | version |
|---|---|
| `latest` | **3.12.0** ← what `vendor/` already is |
| `next` | 3.12.0-next.96 ← what the typedoc documents |

So there is nothing to upgrade *to*. Those two fields do not exist in any
shipping release, and taking them means putting a prerelease on a POS terminal.
The package also publishes ~10 live dist-tags, several of them feature branches
(`task-refactor`, `mobius-socket`, `webex-services-ready`) — "just update the
SDK" can easily land somewhere unintended. Pin the version.

`probeFlowData()` console-logs both fields anyway, because the wire payload is
not bounded by the shipped types. If they arrive populated on 3.12.0, that is
worth knowing — but it is a Cisco conversation, not a version bump.

This also qualifies gotcha #4 below: `callAssociatedDetails` is absent from this
build *and from stable*, not merely undiscovered.

Two things to confirm before trusting an empty result: variables must be marked
**Agent Viewable** in Flow Designer, and the tenant's `callVariablesSuppressed`
must be false.

`callProcessingDetails` also carries useful flow-set values for free —
`customerName`, `customerNumber`, `category`, `reason`, `reasonCode`, `IvrPath`,
`pathId`, `sourceNumber`, `appUser`, `convIvrTranscript`.

**Terminology check that will otherwise cost weeks:** if "NAPA hunt group" means
a *Webex Calling* hunt group, there is no Contact Center task, no
`callProcessingDetails` and no CAD — only CDR after the fact. Everything above
assumes a *WxCC* flow fronting a queue.

## Fidelity notes

Faithful to the screenshots: layout, colours, the 12 disposition strings, the 8
stores (DM009 shows TAMS red = store POS offline), badges, delivery options,
totals, and the catalog's Top 10 list. Icons are emoji stand-ins for NAPA's icon
set. Parts/pricing tables are intentionally empty — the screenshots show no line
items, and inventing part numbers and prices would put fake data in front of the
customer.
