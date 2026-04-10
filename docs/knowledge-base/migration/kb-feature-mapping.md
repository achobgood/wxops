# Call Features: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

> **Audience:** Migration advisor agent (Opus) and cold-context Claude sessions looking up dissent triggers, decision context, and Webex constraints for hunt group / call queue / shared line / auto attendant / voicemail mapping decisions.
> **Reading mode:** Reference. Grep by `DT-FEAT-NNN` ID for dissent triggers, OR read `## Decision Framework` end-to-end when the migration-advisor agent loads this doc during analysis.
> **See also:** [Operator Runbook](../../runbooks/cucm-migration/operator-runbook.md) · [Decision Guide](../../runbooks/cucm-migration/decision-guide.md) · [Tuning Reference](../../runbooks/cucm-migration/tuning-reference.md)

## Decision Framework

### Hunt Group vs Call Queue

The core migration question for CUCM Hunt Pilots and Hunt Lists: does this map to a Webex Hunt Group or a Webex Call Queue?

**Hunt Group characteristics:**
- Rings agents directly by policy (CIRCULAR, REGULAR/top-down, SIMULTANEOUS, UNIFORM/longest-idle, WEIGHTED)
- No queuing -- if no agent answers, call follows no-answer/busy redirect rules
- No agent-level reporting, no queue announcements, no comfort messages, no whisper, no music-on-hold
- No agent join/unjoin control
- Max agents: 50 (SIMULTANEOUS), 100 (WEIGHTED), 1,000 (CIRCULAR/REGULAR/UNIFORM)
- `call_policies` field is optional on create (defaults to CIRCULAR)
- `waiting_enabled` controls "advance when busy" (skip busy agents) -- not true queuing
<!-- Source: docs/reference/call-features-major.md lines 760-819, Appendix Feature Comparison lines 1266-1287 -->

**Call Queue characteristics:**
- Holds calls in queue with configurable queue_size and overflow behavior
- Agent-level reporting, skill-based routing, weight-based distribution
- Comfort messages, wait-time/position announcements, whisper message to agent, music on hold
- Agent join/unjoin, call bounce settings, forced forward, stranded call handling
- Max agents: 50 (SIMULTANEOUS), 100 (WEIGHTED), 1,000 (CIRCULAR/REGULAR/UNIFORM)
- `call_policies` with `routing_type` and `policy` is **required** on create -- API returns error without it
- Holiday service, night service, stranded calls, forced forward all via policy sub-API
<!-- Source: docs/reference/call-features-major.md lines 274-466, verified comment line 329 -->

**Decision factors from CUCM config (from `recommend_feature_approximation` in recommendation_rules.py):**

| Signal | Maps to | Reasoning |
|--------|---------|-----------|
| `has_queue_features=True` (voicemailUsage, overflow destination, maxCallersInQueue>1, non-top-down algorithm) | Call Queue | Queue indicators preserve queuing, overflow, agent reporting, wait-time management |
| `agent_count > 50` | Split into multiple CQs | Exceeds simultaneous distribution limit |
| `agent_count > 8` (no explicit queue features) | Call Queue | At scale, CQ provides reporting and overflow even without explicit queue config |
| `agent_count <= 4`, algorithm in (Top Down, undefined) | Hunt Group | Small ring-group pattern -- HG maps directly |
| `agent_count 5-8`, no queue features, non-top-down | Ambiguous (returns None) | Genuinely uncertain -- needs human review |

### AA Mapping from CTI Route Points

CTI Route Points with IVR scripts map to Webex Auto Attendants. The `recommend_feature_approximation` rule handles this:
- `classification == "AUTO_ATTENDANT"` + no `complex_script` flag: recommend "accept" (direct AA mapping)
- `complex_script` flag set: returns None (ambiguous -- needs human review for multi-level IVR logic)

**AA structure and limits:**
- Two menus: `business_hours_menu` and `after_hours_menu` (both required on create, along with `business_schedule`)
- Keys 0-9, *, # -- each mapped to an action (10 possible actions including TRANSFER_WITHOUT_PROMPT, TRANSFER_WITH_PROMPT, NAME_DIALING, EXTENSION_DIALING, REPEAT_MENU, EXIT, TRANSFER_TO_MAILBOX, TRANSFER_TO_OPERATOR, RETURN_TO_PREVIOUS_MENU, PLAY_ANNOUNCEMENT)
- No `holidayMenu` field -- after-hours menu applies to both after-hours and holiday periods. Different holiday routing requires a separate AA.
- `keyConfigurations.value` is mandatory in PUT even for non-destination actions (use `""`)
<!-- Source: docs/reference/call-features-major.md lines 25-155, gotchas lines 1250-1261 -->
<!-- AA max per location: not documented in reference docs. From training, needs verification -->

### Shared Line vs Virtual Extension Semantics

CUCM shared line appearances have two distinct use cases that map differently in Webex:
- **True shared line** (multiple users actively answering the same line): Webex shared line, supports up to 35 appearances
- **Monitoring-only** (BLF/speed dial/busy lamp appearances): Virtual extension with BLF monitoring

The `recommend_shared_line_complex` rule in recommendation_rules.py checks secondary appearance labels for monitoring keywords (BLF, Monitor, Busy Lamp, Speed, DSS). If ALL secondary appearances match monitoring labels, it recommends virtual extension. Otherwise, if appearance_count <= 10, it recommends shared line. High count with mixed usage returns None (ambiguous).
<!-- Source: recommendation_rules.py lines 284-317 -->

### CX Essentials Boundary

**Customer Assist (formerly CX Essentials)** is a Webex Calling add-on, NOT Webex Contact Center. It adds:
- Screen Pop (URL pop on agent call receipt)
- Queue Call Recording (hosted recording for quality/compliance)
- Wrap-Up Reasons (post-call categorization codes)
- Enhanced agent licensing and supervisor management

**When a queue needs Customer Assist:**
- Queue requires screen pop, wrap-up reasons, or queue-level call recording
- Agents must have Customer Assist license
- CX queues are **hidden from default `call-queue list`** -- must pass `--has-cx-essentials true`
- CX queue creation requires `callPolicies` via `--json-body`
- Error 28018 ("CX Essentials is not enabled for this Call center") means the queue is not a Customer Assist queue
<!-- Source: docs/reference/call-features-additional.md lines 1344-1422, CLAUDE.md known issue #8 -->

### Call Park, Pickup, Paging Group Mapping

- **Call Park**: CUCM call park patterns map to Webex Call Park with designated recall hunt group
- **Call Pickup**: CUCM call pickup groups map to Webex Call Pickup groups (per-location)
- **Paging Groups**: CUCM paging with multicast maps to Webex Paging Groups (unicast, up to 75 targets per group)
<!-- Source: docs/reference/call-features-additional.md -->

---

## Edge Cases & Exceptions

### Hunt pilot with maxCallersInQueue=1

**THE canonical dissent case.** CUCM defaults `maxCallersInQueue` to 1 on hunt pilots. Most admins never change this value. When the FEATURE_APPROXIMATION rule detects queue features (because voicemailUsage is set or algorithm is non-top-down), it may recommend Call Queue -- but maxCallersInQueue=1 means the admin never intended actual queuing. This combination signals a Hunt Group, not a Call Queue.

### Hunt pilot with voiceMailUsage set but no actual VM pilot configured

CUCM allows `voiceMailUsage` to be set on a hunt pilot without a corresponding voicemail pilot actually existing. The `has_queue_features` flag will fire (voiceMailUsage != NONE), but the feature is not operationally used. The `detect_hunt_pilot_reclassification` pattern in advisory_patterns.py uses voiceMailUsage as one of its 4 behavioral signals, requiring >= 2 signals to fire -- so voiceMailUsage alone won't trigger reclassification.

### Hunt list with multiple line groups but <= 4 total agents

The `detect_hunt_pilot_reclassification` pattern counts "multiple line groups" as one signal and agent count > 6 as another signal. With <= 4 agents, the agent count signal won't fire. Multiple line groups alone (1 signal) is below the >= 2 threshold. However, if the algorithm is also Circular or Longest Idle Time, that's 2 signals and the pattern fires -- which may be overly aggressive for 4 agents. The per-decision `recommend_feature_approximation` rule would separately recommend Hunt Group for <= 4 agents with top-down algorithm.

### CTI Route Point with trivial script

A CTI Route Point running a script that simply answers and transfers (no menu, no IVR logic) is classified as AUTO_ATTENDANT by the mapper but doesn't need the AA's menu structure. The `recommend_feature_approximation` rule accepts it as a direct AA mapping if `complex_script` is false. In practice, a simple transfer could also be a Hunt Group with 1 agent -- but the AA classification from the mapper takes precedence.

---

## Real-World Patterns

### The "receptionist ring" pattern
3-5 receptionists, Top Down algorithm, no queue features. Classic Hunt Group: calls ring the first available receptionist in order. Agent count <= 4 triggers the definitive HG recommendation in `recommend_feature_approximation`. At 5 agents with top-down, the rule returns None (ambiguous zone) -- but the behavioral pattern clearly fits HG.

### The "sales overflow" pattern
8+ agents, queue announcements configured, after-hours voicemail. Call Queue is correct: the scale requires agent reporting, and the comfort messages + overflow behavior are CQ-only features. The `has_queue_features` flag fires, and agent_count > 8 independently also recommends CQ.

### The "backup coverage" pattern
CUCM hunt pilot chains: Hunt Pilot A overflows to Hunt Pilot B overflows to voicemail. In Webex, this maps to Call Queue A with overflow destination set to Call Queue B, or Hunt Group A with no-answer redirect to Hunt Group B. No native "hunt list" concept exists in Webex -- chaining must be done via forwarding/overflow settings.

### The "department menu" pattern
AA with 4-8 key options, each transferring to a department Hunt Group or Call Queue. Maps directly to Webex AA with key configurations pointing to HG/CQ extensions. Gotcha: `keyConfigurations.value` must be present even for non-transfer actions.

---

## Webex Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| HG max agents (SIMULTANEOUS) | 50 | call-features-major.md Appendix line 1282 |
| HG max agents (WEIGHTED) | 100 | call-features-major.md Policy enum line 346 |
| HG max agents (CIRCULAR/REGULAR/UNIFORM) | 1,000 | call-features-major.md Policy enum lines 342-345 |
| CQ max agents (SIMULTANEOUS) | 50 | call-features-major.md Policy enum line 344 |
| CQ max agents (WEIGHTED) | 100 | call-features-major.md Policy enum line 346 |
| CQ max agents (CIRCULAR/REGULAR/UNIFORM) | 1,000 | call-features-major.md Policy enum lines 342-345 |
| CQ requires `call_policies` on create | Yes (with `routing_type` + `policy`) | call-features-major.md verified comment line 329 |
| AA requires `business_schedule` on create | Yes | call-features-major.md verified comment line 68 |
| AA requires both menus on create | Yes (`business_hours_menu` + `after_hours_menu`) | call-features-major.md verified comment line 68 |
| AA max per location | Not documented in reference docs | <!-- From training, needs verification --> |
| CX queues hidden from default list | Must pass `--has-cx-essentials true` | CLAUDE.md known issue #8 |
| No hunt list concept in Webex | Chaining via overflow/forwarding | call-features-major.md line 764 |
| Shared line max appearances | 35 | recommendation_rules.py line 312 |
| AA key actions | 10 total (0-9, *, #) | call-features-major.md lines 91-110 |
| No `holidayMenu` on AA | After-hours menu covers both | call-features-major.md gotcha line 1258 |

---

## Dissent Triggers

### DT-FEAT-001: Queue indicators fire on default CUCM values

- **Condition:** FEATURE_APPROXIMATION recommends Call Queue AND `maxCallersInQueue == 1` AND no overflow destination AND algorithm is Top Down
- **Why static rule fails:** `maxCallersInQueue=1` is the CUCM default, never intentionally configured. The `has_queue_features` flag fires on voicemailUsage or non-top-down algorithm, but the combination of default maxCallersInQueue + Top Down + no overflow means the admin never intended queuing behavior.
- **Advisor should:** Recommend Hunt Group instead. The queue indicators are artifacts of CUCM defaults, not intentional configuration.
- **Confidence:** MEDIUM
- **Test:** Create a FEATURE_APPROXIMATION decision with `has_queue_features=True`, `agent_count=6`, `algorithm="Top Down"`, add context field `maxCallersInQueue=1`, `overflow_destination=None`. Verify the static rule recommends CQ but the dissent condition is met.

### DT-FEAT-002: Agent count >8 but hunt pilot behavior is broadcast ring

- **Condition:** FEATURE_APPROXIMATION recommends Call Queue (because `agent_count > 8`) AND algorithm is Broadcast (maps to SIMULTANEOUS in Webex) AND no voicemailUsage AND no overflow destination
- **Why static rule fails:** The >8 agent threshold in `recommend_feature_approximation` doesn't check algorithm. Broadcast/simultaneous ring is fundamentally a Hunt Group behavior -- all phones ring at once, first to answer gets the call. No queuing, no agent reporting needed.
- **Advisor should:** Recommend Hunt Group with SIMULTANEOUS distribution if agent count <= 50 (the simultaneous policy limit). If > 50, the CQ recommendation stands because HG can't handle it.
- **Confidence:** MEDIUM
- **Test:** Create context with `agent_count=12`, `has_queue_features=False`, `algorithm="Broadcast"`. Static rule returns `("call_queue", ...)`. Dissent fires when algorithm is broadcast-like and no queue features present.

### DT-FEAT-003: hunt_pilot_reclassification fires but only on agent count + algorithm

- **Condition:** `detect_hunt_pilot_reclassification` fires with exactly 2 signals: `agent_count > 6` + `algorithm in (Circular, Longest Idle Time)`. No voicemailUsage, no multiple line groups.
- **Why static fires weakly:** 2 signals is the minimum threshold for the pattern. Agent count > 6 is a soft indicator (6 is not a large group), and Circular algorithm is the CUCM default for hunt groups. These two signals together represent default CUCM configuration, not intentional queue behavior.
- **Advisor should:** Note weak signal strength in the advisory detail. If agent count is <= 50 (within HG simultaneous limit) or <= 1,000 (within HG circular limit), HG may suffice. Only with additional signals (voicemailUsage, multiple line groups) does CQ become clearly correct.
- **Confidence:** LOW
- **Test:** Create a hunt_group object with 8 agents, `distributionAlgorithm="Circular"`, `voiceMailUsage="NONE"`, 1 line group. Verify `detect_hunt_pilot_reclassification` fires (2 signals: >6 agents + Circular algorithm). Verify the advisory detail reflects the weak signal.
- **Source:** advisory_patterns.py lines 478-540 (the 4 signals: >6 agents, >1 line groups, algorithm in Circular/Longest Idle Time, voiceMailUsage != NONE; threshold >= 2)

### DT-FEAT-004: voicemail-pilot-simplification eliminates a language-localized pilot tree

- **Condition:** `detect_voicemail_pilot_simplification` (advisory_patterns.py:329) fires — 2+ pilots share the same grouping key (`first-3-digits-of-pilot-number | css_name`) — AND one or more pilot names or descriptions contain a language indicator (e.g., `_EN`, `_ES`, `_FR`, locale codes, or explicit language labels).
- **Why static rule fails:** The grouping key uses pilot number prefix + CSS name as a proxy for "same Unity Connection cluster." This correctly identifies redundant pilots that all resolve to the same system — but it cannot distinguish between pilots that happen to share a prefix because they're truly equivalent versus pilots that represent different language-localized greeting trees (e.g., `VM_Pilot_HQ_EN` at 55500 and `VM_Pilot_HQ_ES` at 55501 may share the `555` prefix and same CSS, yet serve Spanish-speaking callers with a separate Unity Connection greeting tree). Eliminating the second pilot collapses the language localization.
- **Webex model gap:** Webex Calling voicemail does not have per-pilot language assignment. Voicemail language is per-user via the user's preferred language setting (`person-call-settings-media.md` — Voicemail section). There is no location-level mechanism to route callers to a language-specific voicemail greeting tree the way CUCM's voicemail pilot → Unity Connection call handler mapping does. This is a functional gap, not a configuration simplification.
- **Advisor should:** When the simplification advisory fires, scan pilot names for language markers before accepting the recommendation. If language-differentiated pilots are detected, warn that consolidation onto a single Webex location-level voicemail configuration discards the per-language greeting path. Recommend operator confirmation: either (a) accept and document the language gap as a known degradation, or (b) retain the calling flow with a language-selection Auto Attendant upstream of voicemail.
- **Confidence:** MEDIUM (pilot name-based language detection is heuristic; false positives are possible on orgs that use language codes as site abbreviations)
- **Source:** advisory_patterns.py:329-373 (`detect_voicemail_pilot_simplification`); recommendation_rules.py:480 (`recommend_voicemail_incompatible`); `docs/reference/person-call-settings-media.md` (Voicemail section — per-user preferred language)

### DT-FEAT-005: shared-line-simplification label regex false-positives on active shared lines

- **Condition:** `detect_shared_line_simplification` (advisory_patterns.py:550) fires on a `SHARED_LINE_COMPLEX` decision — ALL secondary appearances match `_MONITORING_LABELS = r"(?i)(blf|monitor|busy\s*lamp|speed|dss)"` — AND one or more of those matching labels actually represents an active call-handling line (not a monitoring-only button).
- **Why static rule fails:** The regex `_MONITORING_LABELS` pattern-matches on appearance label text without access to whether the line is ever used to answer calls. A label like `Speed Dial - Reception` matches `speed` — but if the receptionist uses that appearance to actively handle overflow calls, it is a shared line, not a BLF button. Similarly, a team phone labelled `Busy Lamp - Sales` may ring for inbound calls (shared line behavior) even though the label name looks monitoring-only. The regex cannot distinguish passive observation from active call handling.
- **Webex distinction:** Virtual extensions (`virtual-lines.md`) provide presence and BLF status without consuming a shared-line slot. Shared lines (`call-features-additional.md` — Shared Line Appearances section) allow multiple devices to ring and answer the same DN. Migrating an active shared line as a virtual extension causes silent call-handling loss — the user can see the line busy but cannot pick it up. This is a functional regression, not a simplification.
- **Advisor should:** When this pattern fires, present the matched labels and warn that label-based monitoring detection has a known false-positive rate. Recommend the operator review each matched secondary appearance against real call history (CDR data or CUCM line usage) before accepting the virtual-extension recommendation. For appearances with ambiguous labels, default to preserving the shared line and re-evaluating after migration.
- **Confidence:** MEDIUM (label content is heuristic; correct in the majority of BLF-heavy EA/executive deployments but unreliable for organically-labelled lines)
- **Source:** advisory_patterns.py:550-608 (`detect_shared_line_simplification`, `_MONITORING_LABELS`); recommendation_rules.py:337 (`recommend_shared_line_complex`); `docs/reference/call-features-additional.md` (Shared Line Appearances); `docs/reference/virtual-lines.md`

---

## Verification Log

| # | Claim | Verified | Source | Finding |
|---|-------|----------|--------|---------|
| 1 | HG max 20 agents | **Corrected** | `call-features-major.md` lines 1282-1284 | HG max is 50 (SIMULTANEOUS), 100 (WEIGHTED), 1,000 (CIRCULAR/REGULAR/UNIFORM). Plan's "max 20" was wrong. Doc uses correct per-policy limits. |
| 2 | CQ max 50 simultaneous / 525 non-simultaneous | **Partially corrected** | `call-features-major.md` line 344, lines 1282-1284 | CQ SIMULTANEOUS limit of 50 confirmed. "525 non-simultaneous" not found — actual limits are 100 (WEIGHTED) and 1,000 (CIRCULAR/REGULAR/UNIFORM). HG and CQ share the same Policy enum with identical per-policy agent caps. |
| 3 | CQ requires call_policies in create | Yes | `call-features-major.md` line 329 (verified comment); `customer-assist/SKILL.md` line 442 | Both regular CQ and CX queues require `callPolicies` with `routingType` at create time. |
