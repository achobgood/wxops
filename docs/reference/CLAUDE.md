# docs/reference — Webex API Reference Docs

Webex API reference docs grounded in the Webex OpenAPI specs and live API behavior. Each doc covers wxcli CLI examples and raw HTTP fallback. These docs serve the CLI, the playbook agent, and the CUCM migration tool's mapper/executor designs.

## Doc Families

- **Person call settings** (5): `person-call-settings-{handling,media,permissions,behavior}.md`, `self-service-call-settings.md`
- **Location calling** (3): `location-calling-core.md`, `location-calling-media.md`, `location-recording-advanced.md`
- **Devices** (4): `devices-{core,dect,workspaces,platform}.md`
- **Admin** (7): `admin-{org-management,identity-scim,licensing,audit-security,hybrid,partner,apps-data}.md`
- **Meetings** (4): `meetings-{core,content,settings,infrastructure}.md`
- **Messaging** (2): `messaging-{spaces,bots}.md`
- **Contact Center** (5): `contact-center-{core,routing,analytics,journey}.md` + `contact-center-agent-sdk.md` (the `@webex/contact-center` **JS SDK** for a custom agent desktop — a browser runtime surface, not REST/`wxcli`; grounded in the SDK's own TypeScript sources rather than an OpenAPI spec)
- **Standalone** (10): `authentication.md`, `provisioning.md`, `call-features-major.md`, `call-features-additional.md`, `call-routing.md`, `call-control.md`, `webhooks-events.md`, `reporting-analytics.md`, `virtual-lines.md`, `emergency-services.md`

## Consumers

- **Mapper design** (pipeline doc 03b) — field-level CUCM-to-Webex mappings
- **Executor design** (pipeline doc 05b) — API call sequences and error handling
- **Build sessions** — implementation reference for CLI and agent work

## Document Shape

Every doc in this directory follows the same skeleton, in this order. A reader who
learns it once can navigate any of the 40 without re-orienting, and the agent's
Mandatory Grounding Rule sends it here before it answers anything — so a doc that
files its gotchas somewhere unexpected costs a real answer, not just tidiness.

```
# <Surface>: <what it covers>          <- one H1, first line

<intro paragraph — what this surface is, and what it is NOT>

## Sources                             <- where the facts come from, most authoritative first
## Table of Contents                   <- numbered, linking `#N-section-slug`
## 1. <Section>                        <- numbered H2s, matching the contents list
   ### Data Models / Key Parameters    <-   optional: schemas, enums, required fields
   ### CLI Examples                    <-   ```bash wxcli … ```
   ### Raw HTTP                        <-   the curl / rest_* fallback
## N. Gotchas                          <- numbered list, **bold lead sentence.** then detail
## N. See Also                         <- sibling docs, each with WHY you would go there
```

**Counts, so you can tell a convention from one doc's habit** (40 docs, measured
2026-08-02): `## Sources` 38, `## Gotchas` 38, `## See Also` 40, a contents list 30,
`### Raw HTTP` per section 33, `### CLI Examples` 24.

**A contents entry must never imply a number the section does not have.** Markdown renumbers
an ordered list from 1 regardless of what you type, so a doc with unnumbered preamble
sections (`## Required Scopes`, `## Prerequisites`) ends up listing "2. Detailed Call History"
above a heading that reads `## 1.`. Use an ordered list only when the Nth entry really is
section N; otherwise use a bulleted list and keep each section's own number inside the label.
10 of the 40 docs take the bulleted form for exactly this reason.

**Raw HTTP has two accepted placements — pick one per doc and hold it.** 33 docs put a
`### Raw HTTP` inside each numbered section, next to the CLI examples for the same
operations; 6 collect everything into one `## Raw HTTP` or `## Raw HTTP Endpoint Table`
near the end. Per-section is the default and the better choice when a reader arrives at
one feature and wants both forms of the same call side by side. Consolidated suits a doc
whose sections are short enough that a single endpoint table reads as a reference card
(`contact-center-journey.md`, `webhooks-events.md`).

**An `### Endpoints` table is NOT the house style**, despite appearances — it is
`contact-center-core.md`'s own convention (20 of the 4 docs that use the heading at all),
and exactly 1 doc of 40 gives that table a *CLI Command* column. Do not add one to a new
doc for consistency's sake; there is nothing to be consistent with. Where the endpoint
list is genuinely worth tabulating, put it in the consolidated Raw HTTP section.

**Three rules the drift gate enforces** as its check 18 (tested in
`tests/test_drift_check_doc_shape.py`). These are gated because every doc already
satisfies them and a machine can judge them with no taste involved:

1. **Every `](#anchor)` lands on a real heading in the same file.** This is the rule
   with teeth. `devices-core.md`'s contents list pointed at `#5-raw-http` and
   `#6-gotchas` long after those headings became `## 6.` and `## 7.` — four links to
   nowhere, invisible to every other check, hand-repaired once in `a016cea` and drifted
   straight back. **Renumbering a section means renumbering what points at it.**
2. **The file ends with exactly one newline.**
3. **A `## See Also` section exists.** It is how the Sync Protocol tells a maintainer to
   find the related doc; without one the doc is a dead end.

**Conventions the gate reports but never fails**, because each has a legitimate exception
on disk: a `## Sources` section, a `## Gotchas` section, a contents list, and `## See Also`
being the last section. A short doc needs no contents list and a surface may have no
gotchas worth recording — a gate that fails on a judgement call is a gate someone switches
off. Run the drift gate and read its `[18] ADVISORY` line before adding a new doc: if you
are about to skip one of these, make sure it is a decision.

**Beyond the shape, four content rules that are not mechanically checkable:**

- **Say what the surface is NOT, in the intro.** Every skill description in the root
  `CLAUDE.md` carries a `NOT for:` line for the same reason: the expensive failure in this
  repo is answering a different question convincingly, and the Calling-vs-Contact-Center
  vocabulary collides constantly (queue, team, site, dial plan, recording, desktop).
- **A gotcha leads with its claim in bold, then explains.** `**`desktopLabel` required when
  `agentViewable` is true.** Creating or updating a Global Variable …` — scannable, and
  greppable when another doc needs to cite "gotcha #22".
- **Date anything verified live, and label anything that is not.** `Verified live,
  2026-07-31:` and `> **Unverified:** …` are both in use and both carry more weight than
  a confident sentence. A spec-derived claim and an observed one must not read alike.
- **Cross-reference with a reason.** `- [Contact Center: Routing](contact-center-routing.md)
  — Flow Designer is where a **Set Variable** node marks a variable Agent Viewable, which is
  what makes it appear in `callFlowParams`` beats a bare title. Reciprocal linking is *not*
  a rule here — measured at 48% of 127 links, and forcing it would add noise, not signal.

**When a doc covers something other than the REST/`wxcli` surface**, say so at the top and
state its own source-of-truth order. `contact-center-agent-sdk.md` is the worked example:
it documents a browser JavaScript SDK, so the project-wide ladder ending at `wxcli --help`
cannot apply — no `wxcli` command can see `webex.cc`. It opens with a table contrasting
itself against its four siblings and a `## Source of Truth for This Surface` section that
replaces the ladder. Copy that pattern rather than forcing a non-REST surface into the
Endpoints/CLI/Raw-HTTP skeleton.

## Maintenance

Update these docs when you discover new gotchas, API behavior changes, or scope/permission corrections. See the Sync Protocol in the project root `CLAUDE.md` for the full workflow.
