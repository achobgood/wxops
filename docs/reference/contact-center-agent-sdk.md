# Contact Center: Agent Desktop SDK (`@webex/contact-center`)

Reference for the **JavaScript SDK a custom agent desktop runs on** — the browser-side
runtime an agent uses to log into a station, receive tasks, take WebRTC audio, control a
live call, and wrap up. This is a different surface from every other Contact Center doc in
this repo, which covers *administering* WxCC over REST.

| | The rest of `contact-center-*.md` | This doc |
|---|---|---|
| What | Administering WxCC — create queues, agents, layouts | An agent *handling a call* in a browser |
| How | `wxcli cc-*` → REST over `api.wxcc-{region}.cisco.com` | `webex.cc.*` / `task.*` over websocket + WebRTC |
| Truth | `wxcli --help`, `specs/webex-contact-center.json` | The SDK's own TypeScript sources + live observation |
| Scope | `cjp:config_read` / `cjp:config_write` | `cjp:user` |

> **"Desktop" is overloaded — read this before anything else.** In
> [contact-center-core.md](contact-center-core.md) §13, *Desktop Layout* (`cc-desktop-layout`)
> means a JSON document that configures **Cisco's own Agent Desktop** — which widgets appear
> where inside a Cisco-hosted web app. That is not this. This doc is about **replacing** that
> app with your own, built on `@webex/contact-center`. A custom desktop built this way
> ignores desktop layouts entirely: you render your own UI, and nothing in
> `cc-desktop-layout` affects it.

## Sources

- **The SDK's own TypeScript sources**, at version **3.12.0**. Every `file:line` citation
  below points into `sourcesContent` inside the sourcemap the package publishes —
  `umd/contact-center.min.js.map`, 1015 modules, 41 of them from the SDK's own source tree.
  Fetch it from the registry, not from anywhere in this repo:
  `npm pack @webex/contact-center@3.12.0`, or
  `curl -L https://unpkg.com/@webex/contact-center@3.12.0/umd/contact-center.min.js.map`
  (both verified 2026-08-01). **Pin the version** — these line numbers are 3.12.0's and will
  not survive a bump.
- **Live observation against a live tenant on 2026-07-31**, driving a working custom desktop.
  This is the origin of Gotchas 1–14 and the source of every place below where the wire
  format contradicts the declared type.
- [`web-sdk.webex.com/wxcc`](https://web-sdk.webex.com/wxcc) — Cisco's published typedoc.
  **Built from the `next` prerelease, not from the shipping release.** See §11.
- [`npmjs.com/package/@webex/contact-center`](https://www.npmjs.com/package/@webex/contact-center)
- `specs/webex-contact-center.json` — for the REST route that writes call variables (§8).

---

## Source of Truth for This Surface

The project-wide precedence ladder in `CLAUDE.md` tops out at `wxcli --help`. **That ladder
does not apply here** — `wxcli` has no visibility into a JavaScript SDK, and no `wxcli`
command can tell you anything about `webex.cc`. For `@webex/contact-center` the order is:

1. **Live observation against a real tenant** — the wire format is not the declared type. Proven
   repeatedly below.
2. **The SDK's own TypeScript sources** (`sourcesContent` inside the `.map`) — the code that
   actually ships.
3. **The published typedoc** — documents `next`, so it is *ahead of* stable and describes
   members that do not exist in any shipping release.
4. **Training data** — least reliable.

**Never conclude "field X does not exist" by grepping the minified bundle.** TypeScript types
are erased at compile time, so a type-only field never appears in the `.js`. That exact error
once produced a confident, wrong "the SDK has no call-variable API" here; the real field is
`callFlowParams`, a name nobody guessed. A keyword grep can only confirm names you already
thought of — **enumerate a type's members** from the `.map` sources instead. Grepping the
bundle *is* valid evidence for runtime values: method names, event-name string literals,
exported constants.

---

## Table of Contents

1. [Install, initialize, session lifecycle](#1-install-initialize-session-lifecycle)
2. [`ContactCenter` (`webex.cc`) surface](#2-contactcenter-webexcc-surface)
3. [`Task` / `ITask` surface](#3-task--itask-surface)
4. [Events — three families, two emitters](#4-events--three-families-two-emitters)
5. [Data model: `Interaction`, `TaskData`, `Profile`](#5-data-model-interaction-taskdata-profile)
6. [Strings that mean booleans](#6-strings-that-mean-booleans)
7. [Reading flow variables](#7-reading-flow-variables)
8. [Writing call variables (CAD)](#8-writing-call-variables-cad)
9. [Recording pause and resume](#9-recording-pause-and-resume)
10. [Authentication: runtime scope vs config scope](#10-authentication-runtime-scope-vs-config-scope)
11. [Version drift: shipping 3.12.0 vs the `next` typedoc](#11-version-drift-shipping-3120-vs-the-next-typedoc)
12. [Worked example](#12-worked-example)
13. [Gotchas](#13-gotchas)
14. [See Also](#14-see-also)

---

## 1. Install, initialize, session lifecycle

```bash
npm i @webex/contact-center   # Node >= 20
```

The package registers itself as a plugin on the core Webex SDK under the namespace `cc`
(`index.ts:233`). You never construct `ContactCenter` yourself — you read `webex.cc`.

```js
const webex = Webex.init({credentials: {access_token: token}});
const cc = webex.cc;
const profile = await cc.register();          // opens the websocket, returns Profile
await cc.stationLogin({teamId, loginOption: 'BROWSER'});
```

### The two-step that is easy to get wrong

`register()` and `stationLogin()` are **not** the same operation and do not undo each other.

| Call | What it does | What it does *not* do |
|---|---|---|
| `register()` | Opens the websocket, fetches `Profile` | Does not log the agent into a station |
| `stationLogin()` | Claims the station session and the media endpoint | — |
| `deregister()` | Closes the websocket | **Deliberately leaves the agent logged in** |
| `stationLogout()` | Ends the station session | Does not close the websocket |

The asymmetry on the bottom two rows is the source of a whole class of failures: tearing down
with `deregister()` alone leaves a live station session that the next page cannot claim. See
Gotchas #3 and #5.

### Login options

`LoginOption` is `'AGENT_DN' | 'EXTENSION' | 'BROWSER'` (`services/config/types.ts:876`).
`BROWSER` is the WebRTC path — no desk phone, audio arrives as a `MediaStreamTrack` on the
`task:media` event. `AGENT_DN` and `EXTENSION` additionally require `dialNumber`.

**`BROWSER` is a per-agent-profile capability, not an org-wide one.** The gate is
`profile.loginVoiceOptions`, an array on the `Profile` returned by `register()`. If it reads
`["EXTENSION","AGENT_DN"]`, `stationLogin({loginOption:'BROWSER'})` fails with everything else
correct. Check `loginVoiceOptions` before offering browser audio in your UI — and note the
matching admin-side field is on the **desktop profile** (`cc-desktop-profile`), not on the
agent, the team, or the site.

### Browser support

Chrome, Edge, Firefox. **Safari is not supported**, and VDI does not support WebRTC — both
matter if terminals are iPads or thin clients. (Cisco platform constraints, carried forward
from the prototype's rollout notes; re-check per site before assuming browser audio.)

---

## 2. `ContactCenter` (`webex.cc`) surface

Complete public surface of the shipping build, from `cc.ts`. Thirteen methods, three
properties.

### Methods

| Method | Signature | Returns | Source |
|---|---|---|---|
| `register` | `()` | `Promise<Profile>` | `cc.ts:485` |
| `deregister` | `()` | `Promise<void>` | `cc.ts:566` |
| `getBuddyAgents` | `(data: BuddyAgents)` | `Promise<BuddyAgentsResponse>` | `cc.ts:669` |
| `stationLogin` | `(data: AgentLogin)` | `Promise<StationLoginResponse>` | `cc.ts:811` |
| `stationLogout` | `(data: Logout)` | `Promise<StationLogoutResponse>` | `cc.ts:929` |
| `setAgentState` | `(data: StateChange)` | `Promise<SetStateResponse>` | `cc.ts:1039` |
| `startOutdial` | `(destination: string, origin: string)` | `Promise<TaskResponse>` | `cc.ts:1490` |
| `acceptPreviewContact` | `(payload: PreviewContactPayload)` | `Promise<TaskResponse>` | `cc.ts:1572` |
| `getOutdialAniEntries` | `(params: OutdialAniParams)` | `Promise<OutdialAniEntriesResponse>` | `cc.ts:1667` |
| `uploadLogs` | `()` | `Promise<UploadLogsResponse>` | `cc.ts:1763` |
| `updateAgentProfile` | `(data: AgentProfileUpdate)` | `Promise<UpdateDeviceTypeResponse>` | `cc.ts:1795` |
| `getEntryPoints` | `(params?: EntryPointSearchParams)` | `Promise<EntryPointListResponse>` | `cc.ts:1871` |
| `getQueues` | `(params?: ContactServiceQueueSearchParams)` | `Promise<ContactServiceQueuesResponse>` | `cc.ts:1882` |

Properties: `addressBook: AddressBook` (`cc.ts:303`), `apiAIAssistant: ApiAIAssistant`
(`cc.ts:335`), `LoggerProxy` (`cc.ts:343`).

**`startOutdial` takes two positional strings, not an options object.** `origin` is the
outdial ANI — get a valid one from `getOutdialAniEntries({outdialANI: profile.outdialANIId})`.
The internal payload is built at `cc.ts:1502` and the entry point comes from
`profile.outDialEp`; you do not pass it.

### Key request types

```ts
AgentLogin  = {teamId: string; loginOption: LoginOption; dialNumber?: string}   // types.ts:497
Logout      = {logoutReason?: 'User requested logout' | 'Inactivity Logout'
                            | 'User requested agent profile update'}            // agent/types.ts:257
StateChange = {state: AgentState; auxCodeId: string;
               lastStateChangeReason?: string; agentId?: string}                // agent/types.ts:281
BuddyAgents = {mediaType: 'telephony'|'chat'|'social'|'email';
               state?: 'Available'|'Idle'}                                      // types.ts:555
```

`AgentState` is `'Available' | 'Idle' | 'RONA' | string` — the trailing `| string` widens it to
useless, so the type gives you no protection. Note `auxCodeId` is **required** on `StateChange`,
including for `Available`; see Gotcha #2 for the value it wants.

### Paginated getters return an envelope, not an array

`getQueues()` returns `PaginatedResponse<ContactServiceQueue>`, and `getEntryPoints()` /
`addressBook.getEntries()` follow the same shape. Cisco's own JSDoc example inside `cc.ts`
(lines 1473–1481) treats the result as a bare array *and* reads `.queueId` off the element —
both wrong. `ContactServiceQueue` declares `id`, not `queueId` (`types.ts:708-712`), and the
same example passes `destinationType: 'QUEUE'`, an invalid value (Gotcha #12). Treat inline
JSDoc examples in this SDK as illustrative prose, not as tested code.

---

## 3. `Task` / `ITask` surface

`ITask` (`services/task/types.ts:1190`) is the exported public contract and is what a
`task:incoming` handler receives. It extends `EventEmitter`, so `task.on(...)` is available.
The `Task` class (`services/task/index.ts`) implements it exactly — 19 public methods, no
extras, no omissions.

### Properties

| Property | Type | Source |
|---|---|---|
| `data` | `TaskData` | `types.ts:1196` |
| `webCallMap` | `Record<TaskId, CallId>` | `types.ts:1201` |
| `autoWrapup?` | `AutoWrapup` | `types.ts:1208` |

### Methods

All return `Promise<TaskResponse>` unless noted. `TaskResponse = AgentContact | Error | void`
(`types.ts:1184`) — **a union that includes `Error` and `void`**, so a resolved promise is not
proof of success and the resolved value may be nothing at all. Follow the event, not the
return value.

| Method | Signature | Source (`services/task/index.ts`) |
|---|---|---|
| `accept` | `()` | `:336` |
| `decline` | `()` | `:469` |
| `hold` | `(mediaResourceId?: string)` | `:555` |
| `resume` | `(mediaResourceId?: string)` | `:654` |
| `end` | `()` | `:768` |
| `wrapup` | `(wrapupPayload: WrapupPayLoad)` | `:864` |
| `pauseRecording` | `()` | `:968` |
| `resumeRecording` | `(payload: ResumeRecordingPayload)` | `:1060` |
| `consult` | `(consultPayload: ConsultPayload)` | `:1155` |
| `endConsult` | `(consultEndPayload: ConsultEndPayload)` | `:1250` |
| `transfer` | `(transferPayload: TransferPayLoad)` | `:1338` |
| `consultTransfer` | `(payload?: ConsultTransferPayLoad)` | `:1442` |
| `consultConference` | `()` | `:1544` |
| `exitConference` | `()` | `:1650` |
| `transferConference` | `()` | `:1736` |
| `toggleMute` | `()` → `Promise<void>` | `:429` |
| `updateTaskData` | `(newData: TaskData)` → `ITask` | `:267` |
| `cancelAutoWrapupTimer` | `()` → `void` | `:223` |
| `unregisterWebCallListeners` | `()` → `void` | `:252` |

The last three are lifecycle plumbing rather than call actions; **16 of the 19 are things an
agent does to a call.** There is no `mute()`/`unmute()` pair — only the `toggleMute()` toggle,
so you must track mute state yourself.

### Payload types

```ts
WrapupPayLoad          = {wrapUpReason: string; auxCodeId: string}          // :1104
TransferPayLoad        = {to: string; destinationType: DestinationType}     // :1000
ConsultPayload         = {to: string | undefined; destinationType: DestinationType;
                          holdParticipants?: boolean}                        // :1022
ConsultTransferPayLoad = {to: string;
                          destinationType: ConsultTransferDestinationType}   // :1011
ConsultEndPayload      = {isConsult: boolean; taskId: string;
                          isSecondaryEpDnAgent?: boolean; queueId?: string}  // :1035
ResumeRecordingPayload = {autoResumed: boolean}                              // :991
PreviewContactPayload  = {interactionId: string; campaignId: string}         // :1136
```

### Destination types — the values are camelCase, and they are not exported

```ts
DESTINATION_TYPE = {                    // services/task/types.ts:23
  QUEUE:      'queue',
  DIALNUMBER: 'dialNumber',
  AGENT:      'agent',
  ENTRYPOINT: 'entryPoint',             // consult-only
}
```

`CONSULT_TRANSFER_DESTINATION_TYPE` (`:46`) carries the same four values with `entryPoint`
permitted. Sending the **key** name (`'QUEUE'`) instead of the value (`'queue'`) does not raise
an error — the call simply never moves. See Gotcha #12.

### What the package does not export

`index.ts` re-exports a long list of types, but these are **absent** from it, so you cannot
`import` them and TypeScript gives you nothing:

| Missing from `index.ts` | Declared at | Consequence |
|---|---|---|
| `DESTINATION_TYPE`, `DestinationType` | `services/task/types.ts:23`, `:39` | The four legal values are invisible; hand-write the string literals |
| `CONSULT_TRANSFER_DESTINATION_TYPE` | `services/task/types.ts:46` | Same |
| `MEDIA_CHANNEL` | `services/task/types.ts:69` | `interaction.mediaType` values are invisible |
| `Team` | `types.ts:473` *and* `services/config/types.ts:882` | `Profile.teams` references an unimportable type — see below |
| `TaskId` | `services/task/types.ts:10` | `webCallMap` keys untypeable |

`TASK_EVENTS`, `AGENT_EVENTS`, `CC_EVENTS`, `CC_TASK_EVENTS`, `CC_AGENT_EVENTS`, `IDLE_CODE`
and `WRAP_UP_CODE` **are** exported as runtime values — prefer them over string literals.

**Two conflicting `Team` types ship in the same package**, and this is the root of Gotcha #1:

```ts
// types.ts:473 — matches the wire
export type Team = {id: string; name: string; desktopLayoutId?: string};
// services/config/types.ts:882 — what Profile.teams is typed as
export type Team = {teamId: string; teamName: string; desktopLayoutId?: string};
```

`Profile.teams: Team[]` (`services/config/types.ts:987`) resolves to the **second** one, while
`register()` delivers the first shape. Reading `profile.teams[0].teamId` yields `undefined`.

---

## 4. Events — three families, two emitters

There are **three** distinct event namespaces, and knowing which object emits which is the
difference between a working desktop and dead handlers.

| Family | Example | Emitted on | Exported constant |
|---|---|---|---|
| Agent lifecycle | `agent:stateChange` | `cc` | `AGENT_EVENTS` |
| Task lifecycle | `task:assigned` | **the task**, mostly | `TASK_EVENTS` |
| Raw wire names | `AgentContactAssigned` | `cc` **and** the task | `CC_EVENTS` |

### `agent:*` — 10 events, all on `cc`

From `AGENT_EVENTS` (`services/agent/types.ts:410`), all emitted on the `cc` object:

`agent:stateChange`, `agent:multiLogin`, `agent:stationLoginSuccess`,
`agent:stationLoginFailed`, `agent:logoutSuccess`, `agent:logoutFailed`,
`agent:dnRegistered`, `agent:reloginSuccess`, `agent:stateChangeSuccess`,
`agent:stateChangeFailed`.

### `task:*` — 38 events, and only four reach `cc`

`TASK_EVENTS` (`services/task/types.ts:98`) declares 38 names. They are emitted by an internal
`TaskManager`, which forwards **exactly four** of them onto `cc` (`cc.ts:439-447`):

| On `cc` | Why |
|---|---|
| `task:incoming` | A new task is offered — this is where you get your `ITask` handle |
| `task:hydrate` | An existing task is restored after reconnect |
| `task:merged` | Tasks combined (EPDN merge/transfer) |
| `task:campaignPreviewReservation` | Campaign preview offered |

Everything else is emitted **on the task object**, so you must bind handlers inside your
`task:incoming` callback. Binding `cc.on('task:assigned', …)` compiles, runs, and never fires.

Emitted on the task (`services/task/TaskManager.ts`, plus `task:media` from
`services/task/index.ts:238`):

`task:media`, `task:assigned`, `task:unassigned`, `task:end`, `task:hold`, `task:resume`,
`task:wrapup`, `task:wrappedup`, `task:rejected`, `task:outdialFailed`, `task:autoAnswered`,
`task:consulting`, `task:consultCreated`, `task:consultAccepted`, `task:consultEnd`,
`task:offerConsult`, `task:consultQueueCancelled`, `task:consultQueueFailed`,
`task:recordingPaused`, `task:recordingPauseFailed`, `task:recordingResumed`,
`task:recordingResumeFailed`, `task:conferenceEstablishing`, `task:conferenceStarted`,
`task:conferenceFailed`, `task:conferenceEnded`, `task:conferenceEndFailed`,
`task:conferenceTransferred`, `task:conferenceTransferFailed`, `task:participantJoined`,
`task:participantLeft`, `task:participantLeftFailed`, `task:postCallActivity`.

**`task:offerContact` is declared but unreachable.** It is emitted on the `TaskManager`
(`TaskManager.ts:234`), which is neither forwarded to `cc` nor emitted on a task. `TaskManager`
is TypeScript-`private` on `cc`, and TypeScript privacy is erased at runtime, so
`webex.cc.taskManager` does exist as a property (verified: the name survives minification) —
but reaching for it is undocumented internals, not API.

### Raw wire names — an undocumented escape hatch that does work

Two places re-emit the **raw platform event name** alongside the friendly one:

- `cc.ts:1104-1106` — every non-keepalive websocket message is re-emitted on `cc` under
  `eventData.data.type`, i.e. its `CC_EVENTS` name.
- `TaskManager.ts:565-569` — for any event that resolves to a known task, the raw name is
  re-emitted **on that task** with the raw payload.

So `cc.on('AgentStateChangeSuccess', …)` and `task.on('AgentContactHeld', …)` both fire, and
carry the unwrapped server payload. `CC_EVENTS` (`services/config/types.ts:174`) is the full
list — 59 `CC_TASK_EVENTS` plus 18 `CC_AGENT_EVENTS`. This is the only way to observe wire
fields the friendly path drops, and the only way to see events with no `task:*` equivalent
(`AgentCtqCancelFailed`, `CampaignPreviewAcceptFailed`, `REAL_TIME_TRANSCRIPTION`, …).

It is undocumented, so treat it as a diagnostic tool rather than a foundation.

### Four events Cisco documents that do not exist

`cc.ts:126-128` and the JSDoc example at `cc.ts:1425-1447` tell you to listen for:

```
task:established    task:ended    task:error    task:ringing
```

**None of the four exists.** They are absent from `TASK_EVENTS`, absent from every emit site,
and `grep -c` over the shipped `contact-center.min.js` returns **0** for each — and because
these are event-name string literals (runtime values, not erased types), a zero count here is
real evidence. Handlers bound to them never fire and never error. The prototype bound all four
before this was caught.

Use instead: `task:assigned` (connected), `task:end` (ended). There is no general task error
event — failures surface as per-operation `*Failed` events, or as a rejected promise.

---

## 5. Data model: `Interaction`, `TaskData`, `Profile`

The call lives at `task.data.interaction`. `TaskData` (`services/task/types.ts:759`) is the
envelope; `Interaction` (`:564`) is the call.

### `Interaction` — 19 top-level keys in the shipping build

```
isFcManaged  isTerminated  mediaType  previousVTeams  state  currentVTeam  participants
interactionId  orgId  createdTimestamp?  isWrapUpAssist?  callProcessingDetails
mainInteractionId?  media  owner  mediaChannel  contactDirection  outboundType?
callFlowParams
```

`participants` is declared `any` with a literal `// TODO: Define specific participant type`
comment at `:578` — the SDK does not know its own shape here. `media` is
`Record<string, {mediaResourceId, mediaType, mediaMgr, participants, mType, isHold,
holdTimestamp}>` (`:709-727`), and `isHold` there **is** a real boolean, unlike its
`callProcessingDetails` counterparts (§6).

The typedoc shows 27 keys. Those extra 8 are `next`-only — see §11.

### `callProcessingDetails` — where the caller actually lives

The ANI is at **`task.data.interaction.callProcessingDetails.ani`**. The plausible-sounding
`callAssociatedDetails` does not exist in the shipping build; reading it yields `undefined`,
which renders as a healthy-looking "Unknown caller" on every real call (Gotcha #4).

Useful siblings, all declared at `:588-705`:

| Field | Meaning |
|---|---|
| `ani`, `displayAni`, `dnis` | Calling number, display form, dialed number |
| `QueueId`, `vteamId`, `virtualTeamName` | Queue the call came from |
| `customerName`, `customerNumber` | Flow-set customer identity |
| `category`, `reason`, `reasonCode` | Flow-set classification |
| `IvrPath`, `pathId`, `convIvrTranscript` | IVR journey and transcript |
| `sourceNumber`, `sourcePage`, `appUser`, `fromAddress` | Origin metadata |
| `ronaTimeout`, `pauseDuration` | Timers (as strings) |
| `workflowName`, `workflowId`, `EP_ID`, `ROUTING_TYPE` | Flow/routing identity |
| `parentInteractionId`, `childInteractionId`, `relationshipType` | Consult/transfer linkage |
| `parent_ANI`, `parent_DNIS`, `parent_Agent_DN`, `parent_Agent_Name`, `parent_Agent_TeamName` | The other leg |

**The declared type is a closed set, but the wire is not.** `TaskManager.ts:155-159` builds
every task with a raw spread — `{...payload.data}` — with no whitelist and no validation. Any
key the platform sends arrives on the object whether or not TypeScript knows about it. That is
why undeclared keys on `callProcessingDetails` are worth displaying rather than filtering: a
key here that the type does not declare is almost always flow-set (§7).

### `TaskData` — the envelope

Beyond `interaction`, the fields you will actually read:

| Field | Type | Note |
|---|---|---|
| `interactionId` | `string` | The task ID for the REST route in §8 |
| `mediaResourceId` | `string` | What `hold()`/`resume()` optionally take |
| `agentId`, `destAgentId`, `consultingAgentId` | `string` | |
| `wrapUpRequired?` | `boolean` | Real boolean. Gate your ACW screen on it |
| `isConsulted?`, `isConferencing`, `isConferenceInProgress?` | `boolean` | Real booleans |
| `isWebCallMute?` | `boolean` | Mute state, since `toggleMute()` returns nothing |
| `autoResumed?` | `boolean` | Set when the platform auto-resumed recording |
| `queueName?`, `type`, `owner`, `queueMgr` | `string` | |
| `reasonCode?` | `string \| number` | Union — normalize before comparing |
| `agentsPendingWrapUp?` | `string[]` | |

### `Profile` — returned by `register()`

`services/config/types.ts:971`. The fields that drive a custom desktop:

| Field | Why it matters |
|---|---|
| `agentId`, `agentName`, `agentMailId`, `agentDbId` | Identity |
| `teams: Team[]` | **Wire shape is `{id, name}`, not the declared `{teamId, teamName}`** — Gotcha #1 |
| `currentTeamId?` | Third fallback for resolving a team |
| `loginVoiceOptions?: LoginOption[]` | The real gate on `BROWSER` audio |
| `webRtcEnabled` | Org/agent WebRTC flag |
| `isAgentLoggedIn?` | True means a station session already exists — Gotcha #3 |
| `deviceType?` | Which login option the existing session used |
| `idleCodes: Entity[]`, `organizationIdleCodes?` | Idle reasons; `Entity = {id, name, isSystem, isDefault}` |
| `wrapupCodes: Entity[]`, `defaultWrapupCode`, `wrapUpData` | Wrap-up codes and auto-wrapup config |
| `outdialANIId?`, `outDialEp`, `isOutboundEnabledForAgent` | Outdial prerequisites |
| `isEndCallEnabled`, `isEndConsultEnabled`, `allowConsultToQueue` | Feature gates — honor them in your UI |
| `isRecordingManagementEnabled?` | Whether pause/resume is offered at all |
| `lostConnectionRecoveryTimeout` | Reconnect budget, in ms |
| `maskSensitiveData?`, `privacyShieldVisible` | Privacy flags |

---

## 6. Strings that mean booleans

**Every recording and state flag on `callProcessingDetails` is declared `string`, not
`boolean`.** The platform sends `"true"` / `"false"`, and `if (x)` is therefore true for
**both** — including the string `"false"`. This silently inverts logic and produces UI that
confidently shows the wrong state.

| Field | Declared | Actual meaning | Source |
|---|---|---|---|
| `pauseResumeEnabled?` | `string` | boolean | `:606` |
| `isPaused?` | `string` | boolean | `:610` |
| `recordInProgress?` | `string` | boolean | `:612` |
| `recordingStarted?` | `string` | boolean | `:614` |
| `ctqInProgress?` | `string` | boolean | `:616` |
| `outdialTransferToQueueEnabled?` | `string` | boolean | `:618` |
| `taskToBeSelfServiced` | `string` | boolean | `:592` |
| `isConferencing?` | `string` | boolean | `:668` |
| `isParked?` | `string` | boolean | `:692` |
| `monitoringInvisibleMode?` | `string` | boolean | `:676` |
| `CONTINUE_RECORDING_ON_TRANSFER?` | `string` | boolean | `:684` |
| `fceRegisteredEvents?` | `string` | list, serialized | `:690` |
| `pauseDuration?` | `string` | number (seconds) | `:608` |
| `ronaTimeout` | `string` | number (seconds) | `:626` |
| `participantInviteTimeout?` | `string` | number | `:680` |
| `priority?` | `string` | number | `:694` |

Two fields in the same object break the pattern, which is worse than if none did:

| Field | Declared | Note |
|---|---|---|
| `BLIND_TRANSFER_IN_PROGRESS?` | `boolean` | A genuine boolean sitting among the strings |
| `consultDestinationAgentJoined?` | `boolean \| string` | A union — can arrive as either |

So you cannot apply one rule to the whole object. Normalize explicitly per field:

```js
const truthy = v => v === true || v === 'true';
if (truthy(cpd.pauseResumeEnabled) && !truthy(cpd.isPaused)) { /* offer Pause */ }
```

By contrast, the booleans on `TaskData` (`wrapUpRequired`, `isConferencing`,
`isConferenceInProgress`, `isConsulted`, `isWebCallMute`, `autoResumed`) and on
`interaction.media[*].isHold` are declared `boolean` and behave as such.

---

## 7. Reading flow variables

**The declared container is `interaction.callFlowParams`** (`services/task/types.ts:736-751`):

```ts
callFlowParams: Record<string, {
  name: string; qualifier: string; description: string;
  valueDataType: string; value: string;
}>
```

It is an **open record**, so arbitrary keys are by design — a variable named by a Flow Designer
**Set Variable** node lands here as its own key, and a custom name is expected rather than a
surprise. Note the value is always `string`; `valueDataType` tells you what it was meant to be.

A second, lesser source: any key on `callProcessingDetails` that the declared type does not
list. Because of the raw spread at `TaskManager.ts:155-159` those arrive untouched, and in
practice they are flow-set. Display them rather than filtering them.

### Three things to check before concluding "there are no variables"

1. **`callVariablesSuppressed`** — a read-only **tenant** flag
   (`services/config/types.ts:647`). If true, nothing reaches the desktop regardless of flow
   config. Check this first.
2. **Agent Viewable** — the variable must be marked so in Flow Designer.
3. **Is this even a Contact Center call?** If "the hunt group" is a *Webex Calling* hunt group
   rather than a WxCC flow fronting a queue, there is no task, no `callProcessingDetails`, and
   no call variables at all — only CDR after the fact. This terminology collision costs weeks;
   settle it before debugging anything else.

---

## 8. Writing call variables (CAD)

**There is no call-variable write API on `Task` or on `cc`.** All 19 `ITask` methods are listed
in §3; none writes variables, and the enumeration was done from the type members, not by
grepping for guessed names.

The route that does exist is REST:

```
PATCH /v1/tasks/{taskId}
{"attributes": {"orderNumber": "SO-11482"}}
```

From `specs/webex-contact-center.json` (`PatchTaskRoute`):

| Property | Value |
|---|---|
| Scope | **`cjp:user`** or `cloud-contact-center:pod_conv` |
| Body | `attributes` — required, schema-free key/value tuples |
| Limits | Max **30 tuples**; key ≤ 200 bytes; value ≤ 1024 bytes (UTF-8) |
| `taskId` | The `interactionId` your browser already holds |
| CLI | `wxcli cc-tasks update` |

**`cjp:user` is the agent-runtime scope** — the same scope the browser already holds to run
`stationLogin()`. So a browser can technically call this directly; putting it behind a backend
is a security preference (don't ship broad tokens to a POS terminal), not a technical
requirement.

> **Unverified:** this PATCH has **not** been exercised against a live task from this project.
> The scope, limits, and body shape are read from the OpenAPI spec; the round trip is not
> confirmed. Treat "a browser holding `cjp:user` can write CAD" as spec-derived, not observed.

Two ordering constraints:

- **Write before `wrapup()`.** `wrapup()` ends the task; a write against an ended task is
  rejected.
- **The variable must already exist org-wide** as a Global Variable (`wxcli cc-global-vars`,
  `/organization/{orgid}/cad-variable`) before a flow or a PATCH can populate it usefully. See
  [contact-center-core.md](contact-center-core.md) §20, and note its gotchas #21 (`variableType`
  is title case) and #22 (`desktopLabel` required when `agentViewable` is true).

---

## 9. Recording pause and resume

For PCI or any moment where the agent takes a card number.

| Call | Events it can produce |
|---|---|
| `task.pauseRecording()` | `task:recordingPaused`, `task:recordingPauseFailed` |
| `task.resumeRecording({autoResumed: false})` | `task:recordingResumed`, `task:recordingResumeFailed` |

Three rules, in order of how expensive they are to learn the hard way:

1. **Drive UI state from the event, never from the click.** The platform auto-resumes after the
   tenant's `pauseDuration` and announces it with **the same `task:recordingResumed`** a manual
   resume produces. A local boolean drifts and ends up displaying "paused" over a live
   recording. `TaskData.autoResumed` distinguishes the two after the fact.
2. **"Cannot pause" and "not paused" are different states.** `pauseResumeEnabled` is a queue
   capability; `isPaused` is current state. Both are strings (§6). If pause/resume is off for
   the queue, disable the control and say so — do not render it as available-and-not-paused.
3. **Surface failures loudly, in the call bar.** A resolved promise means the platform
   *accepted* the request, not that recording stopped — `TaskResponse` includes `Error` and
   `void`. The agent asked for silence, may not have gotten it, and is about to read a card
   number onto the recording. No optimistic UI here.

Out-of-band server-side equivalents exist if you need them: `wxcli cc-tasks create-pause
<taskId>` / `create-resume`.

---

## 10. Authentication: runtime scope vs config scope

Contact Center has **two scope families**, and this repo previously documented only one of
them. Conflating them produces both false "this is impossible" conclusions and real 403s.

| | Config scopes | Runtime scope |
|---|---|---|
| Scopes | `cjp:config_read`, `cjp:config_write` | **`cjp:user`** |
| Used by | `wxcli cc-*`, the REST config API | `@webex/contact-center`, `PATCH /v1/tasks/{taskId}` |
| Acts as | An administrator of the tenant | **One specific agent, at their station** |
| Typical holder | Service App, admin OAuth integration | The agent's own browser session |

### A Personal Access Token does carry `cjp:user`

**Verified live, 2026-07-31:** an agent's PAT from developer.webex.com successfully drove
`register()`, `stationLogin()` and `setAgentState()` against a live tenant.

This qualifies — it does not overturn — two existing statements in this repo:

- [contact-center-core.md](contact-center-core.md) **gotcha #23** ("Personal access tokens lack
  CC scopes") is correct about **config** scopes: a PAT carries neither `cjp:config_read` nor
  `cjp:config_write`, so `wxcli cc-*` still needs an OAuth integration or a Service App. Its
  heading generalizes further than its own body does.
- `CLAUDE.md` **Known Issue #11** says the same thing for `cc-*` CLI commands, and is likewise
  correct for the config surface.

Neither is a statement about the agent runtime. A PAT works for `webex.cc`; it does not work
for `wxcli cc-queue create`.

### Scopes for a production OAuth integration

For a real custom desktop (rather than a PAT-driven prototype), the integration needs:

```
cjp:user                                       # agent runtime — the one that matters here
spark:webrtc_calling                           # browser audio
spark:calls_read  spark:calls_write            # call control
spark:kms                                      # key management for media
cjp:config_read  cjp:config_write              # only if the app also reads/writes CC config
```

`spark:kms` and `spark:applications_token` are the two CC-related scopes that do **not** work
with Service Apps — see [contact-center-core.md](contact-center-core.md) gotcha #23. A custom
desktop needs `spark:kms`, so **broker per-agent tokens from a backend OAuth flow; a Service
App cannot stand in for it.** Never ship an org-wide admin token to a terminal.

---

## 11. Version drift: shipping 3.12.0 vs the `next` typedoc

**The published typedoc documents a prerelease.** Verified against the npm registry:

| dist-tag | Version | |
|---|---|---|
| `latest` | **3.12.0** | What you get from `npm i @webex/contact-center` |
| `next` | **3.12.0-next.96** | What [`web-sdk.webex.com/wxcc`](https://web-sdk.webex.com/wxcc) is built from |

The package publishes **10 live dist-tags**, several of them feature branches —
`task-refactor` (3.12.0-task-refactor.13), `mobius-socket` (3.12.0-mobius-socket.24),
`webex-services-ready` (3.12.0-webex-services-ready.3), `multi-llms`, `set-bitrate`,
`wxc-disconnect`, and others. "Just update the SDK" can easily land somewhere unintended.

**Recommendation: pin, do not chase.** `latest` is already 3.12.0 — there is nothing to upgrade
*to*. Everything in the drift tables below is reachable only by putting a prerelease into
production.

### `Interaction` — 19 keys shipping, 27 in `next`

Present only in `next`:

| Member | Type in `next` |
|---|---|
| `callAssociatedData?` | `CallAssociatedData` |
| `callAssociatedDetails?` | `CallAssociatedDetails` |
| `flowProperties?` | `Record<string, unknown> \| null` |
| `mediaProperties?` | `Record<string, unknown> \| null` |
| `workflowManager?` | `string \| null` |
| `queuedTimestamp?` | `number \| null` |
| `isMediaForked?` | `boolean` |
| `parentInteractionId?` | `string` |

Type changes on members present in both:

| Member | Shipping 3.12.0 | `next` |
|---|---|---|
| `participants` | `any` (with a `// TODO` comment) | `InteractionParticipants` |
| `mediaChannel` | `MEDIA_CHANNEL` | `string` (widened) |
| `callFlowParams` | required | optional (`?`) |
| `media` | inline object literal | `Record<string, MediaEntry>` |

`callAssociatedDetails` being `next`-only is why Gotcha #4 bites: it is not merely undiscovered
in the shipping build, it is genuinely absent from it and from `latest`.

> **A caution on how this was measured.** These are *type-only* members, so their absence from
> the minified bundle proves nothing about the wire (see the trap noted in Source of Truth
> above). The claim here is precisely that **the shipping build does not declare them** — not
> that the platform never sends them. If they arrive populated on 3.12.0, that is worth knowing
> and is a Cisco conversation, not a version bump. Log the raw payload if you want to find out.

### `Task` — 19 methods shipping, 22 in `next`

Methods present only in `next`. All three return **0 occurrences** in the shipped
`contact-center.min.js`, so this drift is real at runtime, not just in the types:

| Method | Note |
|---|---|
| `holdResume()` | Distinct from the existing `resume()` |
| `switchCall()` | Multi-call handling |
| `sendStateMachineEvent(event)` | Part of a state machine absent from shipping |

Signature changes on methods present in both:

| Method | Shipping 3.12.0 | `next` |
|---|---|---|
| *(all)* | `Promise<TaskResponse>` = `AgentContact \| Error \| void` | `Promise<AgentContact>` |
| `hold` | `(mediaResourceId?: string)` | `(payload)` |
| `resume` | `(mediaResourceId?: string)` | `()` |
| `end` | `()` | `(payload?)` |
| `endConsult` | `(consultEndPayload: ConsultEndPayload)` | `()` |
| `consultConference` | `()` | `(data)` |
| `updateTaskData` | returns `ITask` | returns `void` |
| `webCallMap` | `Record<TaskId, CallId>` | `Map` |

The return-type row is the one that changes how you write code: on shipping you **must** handle
`Error | void`; on `next` you would not.

`next` also introduces two subsystems with no shipping counterpart — a **state machine**
(`state`, `stateMachineService`, `lastState`, `sendStateMachineEvent`) and **UI controls**
(`currentUiControls`, `uiControlConfig`, the `uiControls` accessor) — and changes the `Task`
constructor from `(contact, webCallingService, data, wrapupData, agentId)` to
`(contact, data, uiControlConfig, wrapupData?, agentId?)`. `webCallingService` is gone. Code
written against `next`'s architecture will not port back.

### `ContactCenter` — 13 methods shipping, 15 in `next`

| Member | Kind | Note |
|---|---|---|
| `skipPreviewContact(payload)` | method | `next` only — 0 hits in shipped bundle |
| `removePreviewContact(payload)` | method | `next` only — 0 hits in shipped bundle |
| `userPreference` | property | `next` only — an entire service absent from shipping |
| `entryPoint`, `queue` | property | `private` in shipping, public in `next` |
| `namespace` | property | Public in `next` |

Shipping has `acceptPreviewContact` but neither `skip` nor `remove` — so on 3.12.0 a campaign
preview contact can be accepted but not declined through the SDK.

---

## 12. Worked example

Register, log in, take a call, read flow variables, pause recording, wrap up. Real method and
event names only.

```js
// ── Boot: mount ONCE at app-shell level, above your router. ────────────────
// The call must survive navigation; tying the session to a screen's lifecycle
// drops the call when the agent navigates. See Gotcha #5.
const webex = Webex.init({credentials: {access_token: token}});
const cc = webex.cc;

// 1. register() — opens the websocket, returns the agent profile.
const profile = await cc.register();

// 2. Resolve the team. The wire sends {id}, the type declares {teamId}. Gotcha #1.
const t0 = profile.teams?.[0] || {};
const teamId = t0.id || t0.teamId || profile.currentTeamId;

// 3. Browser audio is a per-profile capability, not an org setting.
if (!profile.loginVoiceOptions?.includes('BROWSER')) {
  throw new Error('This agent profile cannot use browser audio');
}

// 4. An existing station session must be DROPPED, not adopted. Gotcha #3.
if (profile.isAgentLoggedIn) {
  await cc.stationLogout({logoutReason: 'User requested logout'});
  await new Promise(r => setTimeout(r, 1500));
}

await cc.stationLogin({teamId, loginOption: 'BROWSER'});

// 5. Go Available. auxCodeId '0' is required — '0' IS the Available code. Gotcha #2.
await cc.setAgentState({state: 'Available', auxCodeId: '0'});

// ── Only four task events reach `cc`. Everything else binds on the task. §4 ──
cc.on('task:incoming', async (task) => {
  const audioEl = document.getElementById('remoteAudio');

  // Bind BEFORE accept(). task:media can arrive immediately after.
  task.on('task:media', (track) => {
    audioEl.srcObject = new MediaStream([track]);   // the whole WebRTC leg
  });

  task.on('task:assigned', () => showCallBar(task));
  task.on('task:end',      () => showWrapupScreen(task));

  // Recording UI follows the EVENT, never the click — the platform
  // auto-resumes with the same event a manual resume produces. §9.
  task.on('task:recordingPaused',       () => setRecordingUi('paused'));
  task.on('task:recordingResumed',      () => setRecordingUi('recording'));
  task.on('task:recordingPauseFailed',  (e) => alertInCallBar('Pause FAILED', e));
  task.on('task:recordingResumeFailed', (e) => alertInCallBar('Resume failed', e));

  await task.accept();

  // ── Screen pop: the ANI is on callProcessingDetails. Gotcha #4. ──────────
  const cpd = task.data.interaction.callProcessingDetails;
  const ani = cpd.ani;                       // NOT callAssociatedDetails
  popCustomer(ani, cpd.customerName, cpd.dnis, cpd.QueueId);

  // ── Flow variables: an open Record, arbitrary keys by design. §7. ────────
  const params = task.data.interaction.callFlowParams || {};
  for (const [key, v] of Object.entries(params)) {
    renderVariable(v.name || key, v.value, v.valueDataType);
  }

  // ── Pause recording for a card number. Strings, not booleans. §6. ────────
  const truthy = v => v === true || v === 'true';
  const canPause = truthy(cpd.pauseResumeEnabled);
  document.getElementById('pauseRec').disabled = !canPause;
  document.getElementById('pauseRec').onclick = async () => {
    if (!canPause) return;
    await task.pauseRecording();     // resolved != stopped; wait for the event
  };
  document.getElementById('resumeRec').onclick =
    () => task.resumeRecording({autoResumed: false});

  // ── Transfer: values are camelCase, NOT the enum key names. Gotcha #12. ──
  document.getElementById('transferToQueue').onclick =
    () => task.transfer({to: queueId, destinationType: 'queue'});   // not 'QUEUE'

  // ── Wrap-up. Not dismissable; write CAD BEFORE this. Gotchas #9, §8. ─────
  document.getElementById('saveWrapup').onclick = async () => {
    try {
      await task.wrapup({wrapUpReason: 'Order Status', auxCodeId: theCodeId});
      closeWrapupScreen();
    } catch (e) {
      showWrapupError(e);            // never swallow this — Gotcha #14
    }
  };
});

// Outbound: two positional strings, and the usable handle arrives on
// task:incoming, not from the return value. Gotcha #13.
let pendingOutbound = false;
async function dial(number) {
  pendingOutbound = true;
  const anis = await cc.getOutdialAniEntries({outdialANI: profile.outdialANIId});
  await cc.startOutdial(number, anis[0].number);   // (destination, origin)
}

// Deregister on unload so a refresh does not orphan a device. Gotcha #5.
window.addEventListener('beforeunload', () => { cc.deregister(); });
```

---

## 13. Gotchas

Numbers 1–14 were each found the hard way against a live tenant on 2026-07-31; numbers 15+
were established from the SDK sources on 2026-08-01. The numbering is stable — cite a gotcha
by its number. **None is discoverable from the TypeScript definitions alone.**

1. **The `Team` type does not match the wire format.** `Profile.teams` is typed
   `{teamId, teamName, desktopLayoutId?}` (`services/config/types.ts:882`); the runtime payload
   from `register()` is `{id, name, teamType, teamStatus, active, siteId, siteName, …}`. The
   package ships *two* conflicting `Team` types and `Profile` points at the wrong one (§3).
   Reading `profile.teams[0].teamId` yields `undefined`, `stationLogin` then goes out with no
   team, and the only symptom is a bare `Error while performing stationLogin`. Read `.id`, fall
   back to `.teamId`, then to `profile.currentTeamId`.

2. **Going Available requires `auxCodeId: '0'`.** `setAgentState({state:'Available'})` fails
   with `Error while performing setAgentState`. The platform returns an idle code literally
   named `"Available"` whose `id` is the **string** `"0"`, and that is what the Available state
   expects. `{state:'Available', auxCodeId:'0'}` succeeds. Filter the `id === '0'` entry out of
   any idle-reason menu — it is not a real idle reason. `StateChange` *is* exported and does
   mark `auxCodeId` required, but nothing tells you the magic value.

3. **An existing station session must be dropped, not adopted.** If `profile.isAgentLoggedIn`
   is true, skipping `stationLogin` *appears* to work — `register()` succeeds and Idle state
   changes are accepted — but the WebRTC endpoint belongs to whichever page did the original
   login, so your page has no media and the platform refuses to make the agent Available. Call
   `stationLogout({logoutReason})` first, then `stationLogin`. `allowMultiLogin` defaults to
   `false`, so logging in alongside the old session is not an option either. One exception:
   if `stationLogout` fails with `AGENT_HAS_ASSIGNED_CONTACTS` (almost always an unfinished
   wrap-up) the platform will refuse both logout *and* a fresh login, so adopt the existing
   session and let the agent finish the wrap-up rather than locking them out.

4. **The ANI lives at `callProcessingDetails`, not `callAssociatedDetails`.** Full path:
   `task.data.interaction.callProcessingDetails.ani` (siblings `displayAni`, `dnis`, `QueueId`,
   `vteamId`). The plausible-sounding `callAssociatedDetails` does not exist in the shipping
   build (§11 — it is `next`-only), so reading it yields `undefined` and the screen pop shows
   "Unknown caller" on every real call while looking perfectly healthy. Compare the last 10
   digits when matching, so `+1…`, `1…` and bare 10-digit all resolve.

5. **One Webex instance per page — reconnect by reloading.** Calling `Webex.init()` a second
   time in the same page without disposing the first leaves orphaned websockets and WebRTC
   device registrations. After a few reconnects the SDK fails in a cascade that looks like a
   platform outage but is entirely local: first
   `service-interceptor: 'wcc-api-gateway' is not a known service` (service discovery never
   populates — the u2c catalogs return 200 and do contain `wcc-api-gateway`, so it is not an
   outage); fix the disposal order and you get `Error while performing silentRelogin`, because
   `deregister()` deliberately leaves the agent logged in and only `stationLogout()` ends the
   station session; fix that and `stationLogin` itself starts failing on the third cycle.
   Chasing a clean in-place reconnect is not worth it — stash the token in `sessionStorage`,
   reload, and auto-resume. Also `deregister()` on `beforeunload` so a manual refresh does not
   orphan a device: **Webex caps a user at 5 registered devices.**

6. **Never let the UI default to a "connected" look.** A state pill hard-coded to
   "Ready" reads, after a reload with no session, as a live and ready agent — which is exactly
   how a dead connection goes unnoticed in testing. Render an explicit MOCK/LIVE indicator
   driven by real session state, and default it to disconnected.

7. **One session per agent, full stop.** An agent can hold exactly one station session. A
   second page connecting as the same agent gets `AGENT_SESSION_ALREADY_EXISTS`, and its
   teardown's `stationLogout` fails with `AGENT_HAS_ASSIGNED_CONTACTS` if a call is assigned —
   so the second page cannot force its way in either. Two tabs will fight over the agent and
   the loser silently sits in a non-functional state.

8. **Serve your dev build with `Cache-Control: no-store`.** The browser will happily reuse a
   cached bundle and you will debug code that is not the code on disk. This costs an
   embarrassing amount of time before it is diagnosed.

9. **Wrap-up is not dismissable, so the UI must not offer to dismiss it.** WxCC holds the agent
   in wrap-up until a disposition is submitted. A closable ACW dialog leaves the agent visibly
   in Wrap Up with no way back to Ready and no way to reopen the dialog. Hide dismiss controls
   once the task ends, refuse to close while in wrap-up, and give an escape hatch that reopens
   the dialog. Note the ordering trap this creates: clear the wrap-up state *before* calling
   your close routine, or it deadlocks against its own guard.

10. **Show the real ANI, not the account's stored number.** When a call matches a customer via
    an alternate number, displaying the primary number on file is actively misleading — the
    agent cannot tell which line rang. Show the actual calling number, with the number on file
    as secondary when they differ.

11. **Keep a mock mode that suppresses auto-connect.** Because of #7, a second tab opened for UI
    work will fight the live session. A query-string flag that skips connection lets you
    exercise the UI without touching the tenant.

12. **`destinationType` values are camelCase, not the enum key names.** The values are
    `'queue'`, `'dialNumber'`, `'agent'`, `'entryPoint'` (`services/task/types.ts:23`). Sending
    `'QUEUE'` or `'AGENT'` raises no obvious error — **the call simply never moves.** Silent
    failure. `entryPoint` is consult-only, so a cold transfer to a queue must use `'queue'`.
    The constant is not exported (§3), and Cisco's own JSDoc example uses `'QUEUE'`.

13. **`startOutdial()` does not return a Task.** Its return type is
    `TaskResponse = AgentContact | Error | void` — an AQM response carrying an `interactionId`,
    with no `.on()` and no `.wrapup()`. The usable `ITask` arrives separately on
    `cc.on('task:incoming')`, because the dialer binds its success notification to
    `AGENT_OFFER_CONTACT`. Two consequences: binding call controls to whatever `startOutdial`
    resolves to leaves you with no task handle, so hold/end/wrapup silently fail later; and an
    outbound call arrives on the **same event as an inbound one**, so it will pop your
    "Incoming Call" Accept/Decline dialog for a call the agent just placed unless you track a
    pending-outbound flag and branch on it.

14. **Surface wrap-up failures where the operator can see them.** Dereferencing a disposition
    before the `try` block makes a null selection throw uncaught: no save, no close, and no
    error anywhere visible. Every failure path — no disposition, no mapped code, no live task,
    platform rejection — needs a visible message in the wrap-up UI, not only in a console.

15. **Four events Cisco documents do not exist.** `cc.ts:126-128` and the JSDoc example at
    `cc.ts:1425-1447` name `task:established`, `task:ended`, `task:error` and `task:ringing`.
    None appears in `TASK_EVENTS`, at any emit site, or anywhere in the shipped bundle. Handlers
    bound to them never fire and never error. Use `task:assigned` and `task:end`; there is no
    general task error event.

16. **Only four `task:*` events reach `cc`.** `task:incoming`, `task:hydrate`, `task:merged`,
    `task:campaignPreviewReservation` (`cc.ts:439-447`). All 34 others are emitted on the task
    object, so they must be bound inside your `task:incoming` handler. `cc.on('task:assigned', …)`
    compiles, runs, and never fires. A fifth, `task:offerContact`, is emitted only on the
    internal `TaskManager` and is unreachable from the public API entirely.

17. **Recording and state flags are strings, not booleans.** `pauseResumeEnabled`, `isPaused`,
    `recordInProgress` and a dozen more are declared `string` and arrive as `"true"` /
    `"false"` — so `if (x)` is true for **both**. Two fields in the same object break the
    pattern, so no single rule covers it. Full table in §6.

18. **`TaskResponse` includes `Error` and `void`.** Every `Task` method resolves to
    `AgentContact | Error | void` (`services/task/types.ts:1184`). A resolved promise means the
    platform *accepted* the request, not that the thing happened, and the resolved value may be
    nothing at all. Drive UI from events; do not build optimistic UI on a resolution.

19. **`startOutdial(destination, origin)` takes two positional strings**, not an options object
    (`cc.ts:1490`). `origin` is the outdial ANI, from
    `getOutdialAniEntries({outdialANI: profile.outdialANIId})`. The entry point comes from
    `profile.outDialEp` and is not a parameter.

20. **The declared types do not bound the wire payload.** `TaskManager.ts:155-159` constructs
    every task with a raw `{...payload.data}` spread — no whitelist, no validation — so any key
    the platform sends arrives on the object regardless of the closed `callProcessingDetails`
    type. Where a type and a live observation disagree, **the observation wins.**

21. **Several needed types are not exported.** `DESTINATION_TYPE`, `DestinationType`,
    `CONSULT_TRANSFER_DESTINATION_TYPE`, `MEDIA_CHANNEL`, `Team` and `TaskId` are declared but
    absent from `index.ts`, so they cannot be imported. Hand-write the literals from §3.
    `TASK_EVENTS`, `AGENT_EVENTS` and `CC_EVENTS` *are* exported — use them.

22. **Treat the SDK's inline JSDoc examples as prose, not tested code.** In one example
    (`cc.ts:1471-1481`) Cisco reads `.queueId` off a queue that declares `id`, treats a
    paginated envelope as an array, and passes `destinationType: 'QUEUE'` — three separate
    errors, one of which fails silently. The event list in the same file names four events that
    do not exist (#15).

23. **Empty `callFlowParams` has three causes before it has a bug.** `callVariablesSuppressed`
    — a read-only tenant kill switch (`services/config/types.ts:647`) that blocks every variable
    regardless of flow config; the variable not being marked **Agent Viewable** in Flow
    Designer; or the call not being a Contact Center call at all. On that last one: if the
    "queue" fronting the call is a *Webex Calling* hunt group rather than a WxCC flow, there is
    no task, no `callProcessingDetails`, no call variables, and none of this SDK applies — only
    CDR after the fact. Settle that terminology before building anything.

24. **Constraints to re-check per site before rollout.** Chrome/Edge/Firefox only —
    **Safari is unsupported**. **VDI does not support WebRTC.** Max 7 conference participants.
    Wrap-up must complete before the next task is offered. `allowMultiLogin` defaults to
    `false`.

---

## 14. See Also

- [Contact Center: Core](contact-center-core.md) — Administering WxCC: agents, queues, teams,
  aux codes, **desktop layouts** (a different meaning of "desktop" — see the note at the top of
  this doc), and Global Variables (§20) which must exist before a flow or a PATCH can set them.
- [Contact Center: Routing](contact-center-routing.md) — Flows, entry points, dial numbers,
  campaigns. Flow Designer is where a **Set Variable** node marks a variable Agent Viewable,
  which is what makes it appear in `callFlowParams`.
- [Contact Center: Analytics](contact-center-analytics.md) — `cc-tasks`, including
  `wxcli cc-tasks update` (the `PATCH /v1/tasks/{taskId}` route in §8) and the server-side
  recording pause/resume commands.
- [Authentication](authentication.md) — OAuth integrations, scopes, and token setup.
- [Call Control](call-control.md) — The **Webex Calling** call control API. Different product,
  different tasks, different events; not interchangeable with this SDK.
- [`web-sdk.webex.com/wxcc`](https://web-sdk.webex.com/wxcc) — Cisco's typedoc for the happy
  path. Built from the `next` prerelease; read §11 before trusting any member it lists.
- [`npmjs.com/package/@webex/contact-center`](https://www.npmjs.com/package/@webex/contact-center)
  — the package itself. §11 lists the dist-tags, several of which are feature branches.
