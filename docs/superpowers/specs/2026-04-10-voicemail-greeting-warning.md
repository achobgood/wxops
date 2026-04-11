# Voicemail Greeting Warning -- User Action Required

**Date:** 2026-04-10
**Status:** Spec
**Scope:** CUCM migration pipeline -- voicemail greeting re-recording communication

---

## 1. Problem Statement

Voicemail greetings are personal audio recordings that live inside Unity Connection. When users migrate from CUCM to Webex Calling, their voicemail greetings do not come with them. Every user with a custom voicemail greeting must re-record it on the Webex side after migration.

This is not a technical limitation we can engineer around:
- Unity Connection stores greetings internally and does not expose a download API via CUPI for individual user greetings in a migration-friendly format
- Webex DOES have admin-path APIs for uploading voicemail greetings (`POST /people/{personId}/features/voicemail/actions/uploadBusyGreeting/invoke` and `uploadNoAnswerGreeting/invoke`), but the source audio is not extractable from Unity Connection at scale
- Even if individual greetings could be extracted, the personalization and context ("Hi, you've reached John in Sales...") means users typically prefer to re-record anyway

The problem is not technical -- it is **communication**. Users need to know BEFORE migration day that:
1. Their voicemail greeting will revert to the system default
2. They need to re-record their greeting after migration
3. How to re-record (Webex App or phone keypad)

If this is not communicated proactively, the migration team gets flooded with helpdesk tickets on day one: "My voicemail greeting is gone!"

### What Already Exists

The voicemail mapper (`voicemail_mapper.py`) already detects custom greetings and creates `MISSING_DATA` decisions (lines 278-308):

```python
has_custom_greeting = (
    merged_profile.get("customBusyGreeting")
    or merged_profile.get("customNoAnswerGreeting")
    or unity_vm_state.get("customBusyGreeting")
    or unity_vm_state.get("customNoAnswerGreeting")
)
```

When detected, it creates a `MISSING_DATA` decision with summary: "Custom greeting audio for user '{name}' can't be extracted from Unity Connection."

**What is missing:**
1. No aggregate count in the assessment report ("147 of 230 users have custom voicemail greetings")
2. No "User Action Required" section in the report with communication template
3. No advisory pattern that flags the scale of greeting re-recording effort
4. The per-user `MISSING_DATA` decision is correct but buried among other missing data items -- it doesn't stand out as a high-visibility user communication issue

---

## 2. Webex Voicemail Greeting APIs (Verification)

### 2.1 Admin-Path Greeting Upload (EXISTS but not useful for migration)

The Webex API does have admin-path endpoints for uploading voicemail greetings:

| Endpoint | Scope | Notes |
|----------|-------|-------|
| `POST /people/{personId}/features/voicemail/actions/uploadBusyGreeting/invoke` | `spark-admin:people_write` | Multipart/form-data, WAV, max 5 MB |
| `POST /people/{personId}/features/voicemail/actions/uploadNoAnswerGreeting/invoke` | `spark-admin:people_write` | Multipart/form-data, WAV, max 5 MB |
| `POST /telephony/config/people/me/settings/voicemail/actions/busyGreetingUpload/invoke` | `spark:telephony_config_write` | User self-service (Phase 4) |
| `POST /telephony/config/people/me/settings/voicemail/actions/noAnswerGreetingUpload/invoke` | `spark:telephony_config_write` | User self-service (Phase 4) |

These endpoints exist but are not useful for migration because the **source** greetings cannot be extracted from Unity Connection at scale. Unity Connection's CUPI API (`/vmrest/users/{id}/greetings`) returns greeting metadata but not the audio binary in a bulk-extractable way. The call handler data in `unity_connection.py` captures greeting type metadata (line 184: `busy_greeting_type`) but not the audio file content.

### 2.2 User Self-Service Re-Recording

Users can re-record their greetings via:
1. **Webex App:** Settings > Calling > Voicemail > Greeting > Record
2. **Phone keypad:** Dial voicemail access number, follow prompts to record greeting
3. **User Hub:** hub.webex.com > My Call Settings > Voicemail

This is the recommended path for migration. The assessment report should include these instructions.

---

## 3. Proposed Changes

### 3.1 New Advisory Pattern: `detect_voicemail_greeting_rerecording`

**File:** `src/wxcli/migration/advisory/advisory_patterns.py`

Add as Pattern 28 to `ALL_ADVISORY_PATTERNS`.

**Logic:**
1. Count users with voicemail profiles: `store.get_objects("voicemail_profile")`
2. Count users with custom greetings: check `MISSING_DATA` decisions where `context.reason == "custom_greeting_not_extractable"`
3. If custom greeting count > 0, produce an `AdvisoryFinding`

**Severity:**
- 1-10 users with custom greetings: `LOW`
- 11-50 users: `MEDIUM`
- 51+ users: `HIGH`

**Category:** `"out_of_scope"` (this is a user communication task, not a technical migration task)

**Detail template:**
```
{custom_count} of {total_vm_users} voicemail-enabled users have custom
voicemail greetings that will revert to system defaults after migration.

Voicemail greetings are personal recordings stored in Unity Connection.
They cannot be automatically migrated to Webex Calling. Each user must
re-record their greeting after migration.

REQUIRED ACTION: Send a user communication at least 1 week before
migration day informing affected users:
1. Their voicemail greeting will reset to the system default
2. After migration, re-record via: Webex App > Settings > Calling >
   Voicemail > Greeting, or dial the voicemail access number
3. If they have a script for their greeting, have it ready

This is a high-visibility issue -- users notice immediately when their
personalized greeting is replaced by a generic one.
```

### 3.2 Report: "User Action Required" Section

**File:** `src/wxcli/migration/report/appendix.py`

Add a new section to the appendix (or to the executive summary as a callout box):

**"User Action Required" section content:**

| Action | Affected Users | Timing | Instructions |
|--------|---------------|--------|--------------|
| Re-record voicemail greeting | {N} users with custom greetings | After migration, day 1 | Webex App > Settings > Calling > Voicemail > Greeting |

**Communication template paragraph** (included in the report for the admin to copy/paste into an email):

> Subject: Action Required -- Re-record Your Voicemail Greeting After Migration
>
> As part of our phone system migration to Webex Calling, your voicemail
> greeting will reset to the system default. After the migration is complete,
> please re-record your personalized greeting:
>
> - Open the Webex App
> - Go to Settings > Calling > Voicemail
> - Select "Greeting" and record your new greeting
>
> Alternatively, dial [voicemail access number] from your desk phone and
> follow the prompts to record a new greeting.
>
> If you have a script for your greeting, please have it ready before
> re-recording. We recommend completing this within the first day after
> migration.

### 3.3 Report: Executive Summary Callout

**File:** `src/wxcli/migration/report/executive.py`

Add a "User Actions" line to the executive summary:
- "Voicemail Greeting Re-recording: {N} users must re-record after migration"

This should be visually distinct (warning color, icon) to ensure it is not overlooked.

### 3.4 Enhanced Greeting Count in Voicemail Appendix

**File:** `src/wxcli/migration/report/appendix.py` (existing section H)

The existing Voicemail Analysis section (Appendix H) shows voicemail profiles. Add a row:
- "Users with Custom Greetings: {N} (must re-record after migration)"

---

## 4. Pipeline Integration

### 4.1 Detection (Already Built)

The voicemail mapper at `voicemail_mapper.py:278-308` already detects custom greetings and creates `MISSING_DATA` decisions with `context.reason == "custom_greeting_not_extractable"`. No changes needed to the detection logic.

### 4.2 Advisory Pattern (New)

`detect_voicemail_greeting_rerecording` in `advisory_patterns.py`. Reads existing `MISSING_DATA` decisions to count custom greetings. Does not add new mappers or analyzers.

### 4.3 Report Changes

Three additions:
1. New "User Action Required" appendix section with communication template
2. Executive summary callout with greeting count
3. Enhanced Appendix H with greeting count row

### 4.4 No Changes to Extraction or Normalization

The voicemail extractor and normalizer already capture the data needed. The Unity Connection client already reads greeting type metadata.

---

## 5. Documentation Updates Required

| File | Change |
|------|--------|
| `src/wxcli/migration/advisory/CLAUDE.md` | Add Pattern 28 (voicemail greeting re-recording) to pattern list. Update pattern count from 26 to 28 (27 from MoH spec + 28 from this spec). |
| `src/wxcli/migration/report/CLAUDE.md` | Document "User Action Required" appendix section and executive summary greeting count. |
| `docs/runbooks/cucm-migration/operator-runbook.md` | Add "User Communication" section to pre-migration checklist: send voicemail greeting re-recording notice 1 week before cutover. |
| `docs/runbooks/cucm-migration/decision-guide.md` | Enhance `MISSING_DATA` entry for `custom_greeting_not_extractable` reason: add user communication guidance. |
| `docs/knowledge-base/migration/kb-user-settings.md` | Add section on voicemail greeting migration gap: greetings don't transfer, users must re-record, include self-service instructions. |

---

## 6. Test Strategy

### 6.1 Advisory Pattern Tests

**File:** `tests/migration/advisory/test_advisory_patterns.py`

| Test | Description |
|------|-------------|
| `test_vm_greeting_no_custom` | No custom greetings in store -> no finding |
| `test_vm_greeting_few_users` | 5 users with custom greetings -> LOW finding |
| `test_vm_greeting_medium_scale` | 30 users -> MEDIUM finding |
| `test_vm_greeting_large_scale` | 100 users -> HIGH finding |
| `test_vm_greeting_detail_includes_instructions` | Verify detail text includes re-recording instructions and communication guidance |
| `test_vm_greeting_count_accuracy` | Verify custom count matches actual MISSING_DATA decisions with greeting reason |

### 6.2 Report Tests

| Test | Description |
|------|-------------|
| `test_user_action_section_renders` | Store with custom greetings -> "User Action Required" section present in report HTML |
| `test_user_action_section_empty` | No custom greetings -> section omitted or shows "no user actions required" |
| `test_communication_template_present` | Verify email template text appears in report |
| `test_executive_greeting_count` | Verify executive summary includes greeting re-recording count |

**Estimated test count:** 8-10 tests.

---

## 7. Implementation Order

1. **Advisory pattern** (advisory_patterns.py) -- detection and messaging
2. **Report "User Action Required" section** (appendix.py) -- highest communication value
3. **Executive summary callout** (executive.py) -- ensures visibility
4. **Appendix H enhancement** (appendix.py) -- greeting count in voicemail section
5. **Documentation updates** -- after implementation

### Estimated Effort

- Advisory pattern: 30 minutes
- Report sections: 1.5 hours
- Tests: 1 hour
- Documentation: 30 minutes
- **Total: 3.5 hours**

---

## 8. Open Questions

1. **Should we tag individual users for greeting re-recording in the report?** Currently the per-user `MISSING_DATA` decision exists but is grouped with other missing data. We could add a dedicated column to the User/Device Map appendix (F) showing "Custom Greeting: Yes/No". This would let the admin generate a targeted email list. Low effort to add.

2. **Should we provide a Webex API script for bulk greeting upload?** If an admin can obtain the WAV files through some other means (e.g., users email their greeting recordings), we could provide a script that bulk-uploads them via the admin-path API endpoints. This is a nice-to-have tool, not part of the core pipeline.

3. **Auto Attendant greetings vs. personal voicemail greetings.** This spec covers personal voicemail greetings only. AA greetings are professional recordings that fall under the MoH/Announcements spec (Spec 1). The distinction matters: personal greetings are re-recorded by users, AA greetings are re-recorded by the business and uploaded by admins.
