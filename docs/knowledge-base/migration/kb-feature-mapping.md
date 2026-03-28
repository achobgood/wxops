# Call Features: Migration Knowledge Base
<!-- Last verified: 2026-03-28 -->

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
