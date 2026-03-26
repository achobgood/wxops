# Deployment Plan: Nova Thornberry + Cosmic Comics Call Queue

Created: 2026-03-20
Agent: wxc-calling-builder

---

## 1. Objective

Provision a new Webex Calling user "Nova Thornberry" at the HQ location with extension 3001, and create a new call queue "Cosmic Comics Hotline" at extension 3700 — making Nova the first agent in the queue.

---

## 2. Prerequisites

| # | Prerequisite | Status |
|---|-------------|--------|
| 1 | Auth token valid | CONFIRMED — admin@ahobgood.wbx.ai, 11h remaining |
| 2 | HQ location exists and is calling-enabled | CONFIRMED — ID: Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ |
| 3 | Extension 3001 is free at HQ | CONFIRMED — not in current extension list |
| 4 | Extension 3700 is free at HQ | CONFIRMED — not in current extension list |
| 5 | Webex Calling - Professional license available | CONFIRMED — 22 available (8/30 consumed) |
| 6 | Email achobgood+nova@gmail.com does not exist yet | Checking at execution time |

**Blockers found:** None

---

## 3. Execution Steps

| Step | Operation | Command | Expected Result |
|------|-----------|---------|----------------|
| 1 | Create user Nova Thornberry | `wxcli users create` | Person ID returned |
| 2 | Assign Calling Pro license + HQ location + extension 3001 | `wxcli licenses-api update` with JSON body | 200/Updated |
| 3 | Verify user creation | `wxcli users show PERSON_ID` | User shows ext 3001 at HQ |
| 4 | Create call queue "Cosmic Comics Hotline" at ext 3700 | `wxcli call-queue create` | Queue ID returned |
| 5 | Add Nova as agent to the queue | `wxcli call-queue update` with agents JSON | 200 |
| 6 | Verify queue | `wxcli call-queue show` | Queue shows agent Nova |

---

## 4. Resources to Create

| Resource Type | Name / Identifier | Action | Details |
|--------------|------------------|--------|---------|
| Person | Nova Thornberry (achobgood+nova@gmail.com) | Create | New Webex user |
| Calling License | Webex Calling - Professional | Assign | At HQ, extension 3001 |
| Call Queue | Cosmic Comics Hotline | Create | HQ, extension 3700, CIRCULAR routing |
| Queue Agent | Nova Thornberry | Add | Agent in Cosmic Comics Hotline |

---

## 5. Rollback Plan

| Trigger | Rollback Action |
|---------|----------------|
| License assignment fails after user created | Delete Nova: `wxcli users delete PERSON_ID` |
| Queue creation fails | Delete Nova if desired: `wxcli users delete PERSON_ID` |
| Agent add fails | Queue still usable with no agents; delete queue if desired |

---

## 6. Estimated Impact

| What Changes | Details |
|-------------|---------|
| Users added | 1 (Nova Thornberry) |
| Licenses consumed | 1 Webex Calling Professional (9/30 after) |
| Call queues added | 1 (Cosmic Comics Hotline, ext 3700) |
| No change to | All existing users, queues, hunt groups, auto attendants |

---

## 7. Key Values

| Item | Value |
|------|-------|
| HQ Location ID | Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OLzJiZTBjZjQwLTA3ZDgtNDZjOS1hYjc5LWQ3MTY2OWE3ZWY3NQ |
| Calling Pro License ID | Y2lzY29zcGFyazovL3VzL0xJQ0VOU0UvYTk1MjdkNjAtZTc4Yy00MzMwLTljNTMtODMzMWEwYzVhYTdiOkJDU1REX2NjYzg4ZDQyLWYyYjYtNDViMS1hMTAwLTEzMjZmNzVhMTczZg |
| Nova's email | achobgood+nova@gmail.com |
| Nova's Person ID | Y2lzY29zcGFyazovL3VzL1BFT1BMRS9kNjIwZDU2Yy1hOTI0LTRkOTMtYWUxNC1iZTYxOWFkMDBlMTY |
| Nova's extension | 3001 |
| Queue ID | Y2lzY29zcGFyazovL3VzL0NBTExfUVVFVUUvZTQxZDI5MmMtNTliOS00YWJkLWJhNTItNjQ5ZTg3NmUyYjll |
| Queue extension | 3700 |
| Queue routing policy | CIRCULAR |
| AA Name | Galactic Guest Services |
| AA ID | Y2lzY29zcGFyazovL3VzL0FVVE9fQVRURU5EQU5UL2UxYjRmOWQyLTc2MTQtNGNhZS1iODBmLWE2MTg2MmIxYTgzNQ |
| AA extension | 3800 |

---

## 8. Build-Out Execution Report (2026-03-20)

### Summary

Full call center build-out executed after initial provisioning. 7 execution steps completed.

### Step Results

| Step | Operation | Status | Notes |
|------|-----------|--------|-------|
| 1 | Queue settings update (size, overflow, MoH, wait msg) | PARTIAL | queueSize=15 applied. overflow.sendToVoicemail, overflowAfterWait, waitMessage.enabled, mohMessage, welcomeMessage.alwaysEnabled silently ignored by API — confirmed gotcha. |
| 2 | Create AA "Galactic Guest Services" ext 3800 | DONE | ID: Y2lzY29zcGFyazovL3VzL0FVVE9fQVRURU5EQU5UL2UxYjRmOWQyLTc2MTQtNGNhZS1iODBmLWE2MTg2MmIxYTgzNQ |
| 3 | AA business-hours menu (Key 1=3700, Key 2=Nova VM, Key 0=repeat) | DONE | Confirmed via show |
| 4 | AA after-hours menu (Key 0=3700 voicemail) | DONE | Confirmed via show |
| 5 | Nova's voicemail (5 rings, email copy to achobgood+nova@gmail.com) | DONE | Confirmed via show |
| 6 | Nova's caller ID (LOCATION_NUMBER, "Nova Thornberry") | DONE | DIRECT_LINE rejected — Nova has no DID, LOCATION_NUMBER used instead |
| 7 | Nova's call waiting enabled | DONE | Confirmed |
| 8 | Nova's call forwarding (busy+no-answer -> 3700 VM) | DONE | Both busy and no-answer forward to ext 3700 voicemail after 5 rings |

### Known Gotcha (documented 2026-03-20)

The call queue `queueSettings.overflow.sendToVoicemail`, `overflowAfterWaitEnabled`, `overflowAfterWaitTime`, `waitMessage.enabled`, `mohMessage.normalSource.enabled`, and `welcomeMessage.alwaysEnabled` fields are silently ignored on PUT even though the API returns 200 "Updated". The fields that did apply: `queueSize`, `callOfferToneEnabled`, `comfortMessage` (partially), `whisperMessage`. These fields may require calling plan entitlements or location-level settings to unlock.

### Resources Created in This Session

| Resource | Name | Extension | ID |
|----------|------|-----------|-----|
| Auto Attendant | Galactic Guest Services | 3800 | Y2lzY29zcGFyazovL3VzL0FVVE9fQVRURU5EQU5UL2UxYjRmOWQyLTc2MTQtNGNhZS1iODBmLWE2MTg2MmIxYTgzNQ |

### Follow-Up Items

1. **Phone number (DID) for queue**: All 40 numbers at HQ are assigned. To give the Cosmic Comics Hotline an external DID, a new number must be purchased and added to the HQ location inventory, then assigned to the queue.
2. **Phone number for Nova**: Same constraint — needs a new DID purchase if she needs an external direct line.
3. **Queue overflow/MoH/wait msg**: These settings appear to be locked at the API level for this org/plan. Configurable via Control Hub UI if needed.
4. **Custom AA greetings**: Recordings for "Galactic Guest Services" menus must be uploaded via Control Hub (API audio upload not supported).
</content>
</invoke>