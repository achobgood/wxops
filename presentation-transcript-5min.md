# wxops — 5 Minute Presentation Transcript

**Format:** teleprompter read over GitHub, then a walkthrough of a **pre-run** agent session, verified in Control Hub.

**Pacing — measured, not estimated.** Your real delivery rate is **94 wpm** including pauses and screen switches (derived from your run: 502 words took 5:20). Budget for 5:00 is **471 words**. This script is **451** — about **4:48**, with 12s of margin.

> **Do not add words to this script.** At your measured pace every 16 words costs 10 seconds. If you want to say something new, cut something first.

**Word budget per section — check yourself against these:**

| Section | Words | Cumulative | You should be at |
|---|---|---|---|
| Open | 37 | 37 | 0:24 |
| What's in it | 54 | 91 | 0:58 |
| Why it's trustworthy | 103 | 194 | 2:04 |
| The demo | 144 | 338 | 3:36 |
| Why it matters | 71 | 409 | 4:21 |
| Close | 42 | 451 | 4:48 |

**The checkpoint that matters: leaving the architecture beat at 2:04.** That's where you were 1:50 over last time. If the clock says 2:30 there, jump straight to the demo and use the rescue cuts below.

---

## Prep

The advance run is already done, so there's nothing left to de-risk. Just stage the three tabs:

**Tab 1** GitHub at **How It Works** · **Tab 2** the completed session, scrolled to the top · **Tab 3** Control Hub showing the finished result.

Have the scroll positions for the four demo beats found *before* you start — plan, `--help` call, hunt group, device work. Hunting for them on screen is the easiest way to blow the 4:50.

---

## Numbers — provenance

| Claim | Status |
|---|---|
| 177 command groups · 18 org-health checks | Project README / CLAUDE.md |
| 24 skills | **Verified** — 24 tracked `SKILL.md` files |
| "over forty" reference docs | **Verified** — 42 tracked |
| "four thousand tests" | **Verified** — 4,179 collected, 2026-07-31 |
| `CIRCULAR` is the real routing value | **Verified** — `src/wxcli/commands/hunt_group.py:117` |
| "Shared line" is rejected; real value is `SHARED_CALL_APPEARANCE` | **Verified** — `docs/reference/devices-core.md:698` |
| "competitor is their existing CUCM" | Positioning opinion — your call |

---

# THE SCRIPT

---

### [0:00 – 0:24] OPEN — *38 words*
**SCREEN:** GitHub repo landing page.

> Webex Calling has an enormous configuration surface — users, locations, call features, routing, devices, contact center. Today that means Control Hub, one click at a time.
>
> This is wxops. You describe what you want; it builds it.

---

### [0:24 – 1:00] WHAT'S IN IT — *56 words*
**SCREEN:** Scroll the README past the command groups.

> A hundred and seventy-seven command groups cover the whole API estate — calling, admin, devices, messaging, meetings, contact center. On top sit the workflows: a CUCM-to-Webex migration pipeline that discovers a live cluster and produces a customer-ready assessment report, and an org health audit — eighteen automated checks across security, routing, and device health.

---

### [1:00 – 2:07] WHY IT'S TRUSTWORTHY — *105 words*
**SCREEN:** Stop on **How It Works**. Leave the three-layer table up for this whole beat.

> Now the part that makes it trustworthy.
>
> Most "AI plus API" tools hand a model an OpenAPI spec and hope. That breaks at this scale. The model invents field names, and doesn't know a hunt group can't exist before the people in it do. Specs describe endpoints. They don't describe outcomes.
>
> So it's three layers. **Over forty reference docs** are ground truth — it answers from documented behavior, never training data. **Twenty-four skills** encode procedure — prerequisites, ordering, known landmines. **And a tested CLI executes**, four thousand tests behind it.
>
> The AI only does what it's good at: understanding the ask, and orchestrating.

---

### [2:07 – 3:36] THE DEMO — *139 words*
**SCREEN:** Tab 2 — the completed session. Say up front it's pre-run.

> Here's what that buys you. One prompt I ran earlier, plain English: five users with extensions, DIDs for two, a hunt group with circular routing, a business-hours schedule — and reconfigure a phone that's already deployed.

*[scroll to the plan]*

> It planned first. Users before the hunt group — you can't add people who don't exist.

*[scroll to a `--help` call]*

> There, it's checking its own command syntax before building anything. It doesn't trust its memory about flags; it asks the tool.

*[scroll to the hunt group]*

> "Circular routing" — I said it in English, it wrote the exact setting.

*[scroll to the device work]*

> And the phone. To share a line, you'd reach for the setting called "shared line" — that one gets rejected. The value that actually works is named something else entirely. It knew, because somebody hit that wall and wrote it down.

**SCREEN:** Tab 3 — Control Hub.

> And here it is in Control Hub. Exactly what I asked for, and every step written down.

---

### [3:36 – 4:22] WHY IT MATTERS — *72 words*
**SCREEN:** Control Hub, or back to the repo.

> For customers: configuration labor is what gates a rollout, and this collapses it — a morning of clicking becomes a sentence.
>
> For Cisco: every hour a TSA spends in Control Hub is an hour not in front of a customer. And in most calling deals the competitor isn't another vendor — it's the CUCM they already have and don't want to touch. Anything that makes moving *boring* is worth real money.

---

### [4:22 – 4:50] CLOSE — *45 words*
**SCREEN:** Terminal or repo.

> It's built entirely on Cisco's public APIs — nothing internal, nothing forked. And the AI is optional; the CLI runs on its own, in scripts and in CI.
>
> `pipx install wxcli`, `wxcli init`, and it's running in under two minutes. Thank you.

---

## Live rescue — if you're behind at the 2:07 mark

You're over budget. Cut in this order, mid-flight:

1. **Drop the migration + org-health sentence** at 0:24 (the demo implies breadth anyway) — **saves 36s**
2. **Drop the CUCM line** in *Why It Matters* — **saves 33s**
3. **Drop "And the AI is optional…"** in the close — **saves 18s**

**Never cut:** the three-layer beat (1:00) or the shared-line beat (3:05). The first makes the claim; the second is the only moment that proves it.

---

## What got removed to hit 5:00 — and why

Cut from the previous draft: the "one token across customer orgs" partner line, the Codex portability mention, the "auditable decision trail" migration detail, "live org, live API calls," and the demo's full restatement of the prompt. All true, none of them load-bearing — each was costing 10–25 seconds against the two beats that actually carry the argument.

**Honest framing:** this material is a comfortable 7-minute talk. At 5:00 you are choosing breadth *or* depth. This draft picks depth — one prompt, shown properly — and buys the breadth back with a single 56-word sentence.
